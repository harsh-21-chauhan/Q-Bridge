"""Simulated calibration data and reproducible placement decisions."""
from dataclasses import dataclass, asdict
import numpy as np
from .bayes import BetaPrior, DEFAULT_PRIORS, BayesianPlanner
from .loss import PlacementModel, GROUPS


@dataclass(frozen=True)
class ExperimentRecord:
    circuit_family: str
    n_qubits: int
    shots: int
    selected_calibration: str
    observed_failures: int
    prior_means: tuple[float, float, float]
    posterior_means: tuple[float, float, float]
    chosen_placement: tuple[int, ...]
    prior_expected_loss: float
    posterior_expected_loss: float
    evsi: dict[str, float]
    # SIMULATOR-ONLY evaluation, intentionally not used by the decision engine:
    oracle_loss: float
    actual_selected_loss: float
    decision_regret: float
    calibration_backend: str

    def to_dict(self) -> dict:
        return asdict(self)


def measure_binomial(true_probability: float, shots: int, rng: np.random.Generator) -> int:
    """Idealized calibration observable: failure is a Bernoulli channel error."""
    if not (0 <= true_probability <= 1) or shots < 0:
        raise ValueError("invalid true probability or budget")
    return int(rng.binomial(shots, true_probability))


def run_experiment(model: PlacementModel, true_parameters: tuple[float, float, float],
                   shots: int = 100, seed: int = 42,
                   priors: tuple[BetaPrior, BetaPrior, BetaPrior] = DEFAULT_PRIORS,
                   forced_group: int | None = None,
                   calibration_backend: str = "binomial") -> ExperimentRecord:
    planner = BayesianPlanner(model)
    group, scores = planner.select(priors, shots) if forced_group is None else (forced_group, {})
    if group not in range(3):
        raise ValueError("calibration group must be 0, 1, or 2")
    rng = np.random.default_rng(seed)
    if calibration_backend == "binomial":
        k = measure_binomial(true_parameters[group], shots, rng)
    elif calibration_backend == "aer":
        from .aer_validation import calibration_shots
        k = calibration_shots(true_parameters[group], shots, seed)
    else:
        raise ValueError("calibration_backend must be 'binomial' or 'aer'")
    updated = list(priors)
    updated[group] = updated[group].updated(k, shots)
    chosen_idx, posterior_loss = planner.recommend(tuple(updated))
    _, oracle_loss = model.best_placement(true_parameters)
    actual_loss = float(model.losses(true_parameters)[chosen_idx])
    return ExperimentRecord(
        circuit_family=model.circuit.family, n_qubits=model.circuit.n_qubits,
        shots=shots, selected_calibration=GROUPS[group], observed_failures=k,
        prior_means=tuple(p.mean for p in priors),
        posterior_means=tuple(p.mean for p in updated),
        chosen_placement=model.mappings[chosen_idx],
        prior_expected_loss=planner.recommend(priors)[1],
        posterior_expected_loss=posterior_loss, evsi=scores,
        oracle_loss=oracle_loss, actual_selected_loss=actual_loss,
        decision_regret=max(0.0, actual_loss - oracle_loss),
        calibration_backend=calibration_backend)
