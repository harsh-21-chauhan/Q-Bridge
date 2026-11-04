"""Readable API contracts: reject invalid inputs before running any science.

These models also describe requests and responses on FastAPI's /docs page.
The scientific output keeps the field names used by qbridge.production.
"""
from dataclasses import asdict
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qbridge.production import SimulationConfig

ExperimentId = Annotated[str, Field(pattern=r"^qb_[0-9a-f]{32}$")]
Probability = Annotated[float, Field(ge=0, le=1)]
Count = Annotated[int, Field(ge=0)]
Group = Literal["local_a", "local_b", "remote"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class ExperimentRequest(StrictModel):
    family: Literal["ghz", "layered", "star"] = "layered"
    qubits: int = Field(default=6, description="Equal-capacity placement: 6 or 12 qubits")
    shots: int = Field(default=100, ge=20, le=1000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    truth_mode: Literal["prior", "shifted", "local_shift", "link_shift"] = "shifted"
    method: Literal["adaptive_evsi"] = "adaptive_evsi"
    guard_enabled: bool = True
    guard_threshold: float = Field(default=0.60, ge=0.5, le=1.0)
    guard_draws: int = Field(default=512, ge=64, le=16384)

    @field_validator("qubits")
    @classmethod
    def supported_qubits(cls, value: int) -> int:
        if value not in (6, 12):
            raise ValueError("qubits must be 6 or 12")
        return value

    def to_scientific_config(self) -> SimulationConfig:
        # The method is fixed by the public interface, not a new algorithm input.
        return SimulationConfig(**self.model_dump(exclude={"method"}))


class Posterior(StrictModel):
    alpha: float = Field(gt=0)
    beta: float = Field(gt=0)
    mean: Probability
    credible_interval_95: list[Probability] = Field(min_length=2, max_length=2)


class NoiseEstimates(StrictModel):
    local_a: Posterior
    local_b: Posterior
    remote: Posterior


class GroupCounts(StrictModel):
    local_a: Count
    local_b: Count
    remote: Count


class GroupValues(StrictModel):
    local_a: Probability
    local_b: Probability
    remote: Probability


class CalibrationStep(StrictModel):
    stage: Literal["pilot", "adaptive"]
    group: Group
    shots: int = Field(gt=0)
    failures: Count
    posterior_mean: Probability
    evsi_at_choice: GroupValues | None
    step: int = Field(ge=1, le=5)
    posteriors_before: NoiseEstimates
    posteriors_after: NoiseEstimates
    cumulative_shots: Count
    cumulative_shots_by_group: GroupCounts

    @model_validator(mode="after")
    def failures_fit_budget(self) -> "CalibrationStep":
        if self.failures > self.shots:
            raise ValueError("failures cannot exceed shots")
        return self


class Calibration(StrictModel):
    pilot_shots: GroupCounts
    adaptive_batches: list[int] = Field(min_length=2, max_length=2)
    shots_by_group: GroupCounts
    failures_by_group: GroupCounts
    total_shots: int = Field(ge=20, le=1000)
    trace: list[CalibrationStep] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def exact_accounting(self) -> "Calibration":
        if sum(self.shots_by_group.model_dump().values()) != self.total_shots:
            raise ValueError("group allocations do not match total shots")
        if sum(step.shots for step in self.trace) != self.total_shots:
            raise ValueError("trace does not match total shots")
        for group in ("local_a", "local_b", "remote"):
            steps = [step for step in self.trace if step.group == group]
            if sum(step.shots for step in steps) != getattr(self.shots_by_group, group):
                raise ValueError("trace and group shot allocation disagree")
            if sum(step.failures for step in steps) != getattr(self.failures_by_group, group):
                raise ValueError("trace and group failures disagree")
        return self


class Gate(StrictModel):
    name: Literal["h", "cx"]
    control: Count
    target: int


class Circuit(StrictModel):
    family: Literal["ghz", "layered", "star"]
    qubits: int
    gates: list[Gate]
    cx_count: Count
    placement_count: int = Field(gt=0)
    stabilizers: list[str]


class Placement(StrictModel):
    index: Count
    assignment: list[Literal[0, 1]]
    qpu_a: list[int]
    qpu_b: list[int]
    cx_counts: GroupCounts


class Placements(StrictModel):
    initial: Placement
    candidate: Placement
    final: Placement


class Loss(StrictModel):
    objective: Literal["mean_stabilizer_generator_parity_error"]
    initial_under_prior: Probability
    initial_under_posterior: Probability
    candidate_under_posterior: Probability
    final_under_posterior: Probability
    candidate_expected_improvement: float
    accepted_expected_improvement: float


class Decision(StrictModel):
    switched: bool
    status: Literal["unchanged", "no_positive_gain", "accepted", "rejected", "unguarded"]
    reason: str
    guard_enabled: bool
    guard_threshold: Probability
    posterior_probability_better: Probability | None
    posterior_draws_used: Count
    probability_interpretation: str


class Algorithm(StrictModel):
    method: Literal["adaptive_evsi"]
    version: str
    prior_model: Literal["original_beta"]


class ScientificResult(StrictModel):
    schema_version: str
    algorithm: Algorithm
    configuration: dict
    guard_seed: Count
    circuit: Circuit
    initial_priors: NoiseEstimates
    calibration: Calibration
    final_posterior: NoiseEstimates
    placements: Placements
    loss: Loss
    decision: Decision


class Evaluation(StrictModel):
    label: str
    true_error_rates: GroupValues
    oracle_placement: Placement
    oracle_loss: Probability
    initial_actual_loss: Probability
    candidate_actual_loss: Probability
    final_actual_loss: Probability
    regret: Probability
    actual_improvement: float


class ExperimentRecord(StrictModel):
    experiment_id: ExperimentId
    mode: Literal["simulation"]
    configuration: dict
    metadata: dict
    result: ScientificResult
    evaluation: Evaluation

    @model_validator(mode="after")
    def matching_configuration(self) -> "ExperimentRecord":
        # Detect malformed saved records without rerunning the experiment.
        config = SimulationConfig(**self.configuration)
        if self.result.configuration != asdict(config.calibration_config()):
            raise ValueError("saved decision and simulation configurations disagree")
        if self.result.calibration.total_shots != config.shots:
            raise ValueError("saved budget and configuration disagree")
        return self


class ExperimentEvidence(StrictModel):
    """Only this projection is suitable for later decision-explanation tools."""
    experiment_id: ExperimentId
    mode: Literal["simulation"]
    result: ScientificResult


class ExperimentSummary(StrictModel):
    experiment_id: ExperimentId
    configuration: dict
    status: str
    switched: bool


class ExperimentList(StrictModel):
    experiments: list[ExperimentSummary]
    next_offset: int | None
    total: Count


class PolicyMetrics(StrictModel):
    policy: str
    mean_regret: Probability
    mean_task_loss: Probability
    switch_rate: Probability
    help_rate: Probability
    harm_rate: Probability


class ScenarioPolicy(PolicyMetrics):
    # These intervals belong to an individual scenario, not the overall mean.
    regret_reduction_vs_guard60: float
    paired_ci_95: list[float] | None


class BenchmarkScenario(StrictModel):
    family: str
    qubits: int
    truth_mode: str
    shots: int
    runs: int
    seed: int
    policies: list[ScenarioPolicy]


class BenchmarkSummary(StrictModel):
    mode: Literal["simulation"]
    source: str
    source_sha256: str
    configuration_count: int
    trial_configuration_count: int
    policy_outcome_count: int
    aggregation: str
    metric_notes: list[str]
    policies: list[PolicyMetrics]
    scenarios: list[BenchmarkScenario]
