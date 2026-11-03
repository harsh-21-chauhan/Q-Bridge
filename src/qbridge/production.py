"""Production interface to the frozen original-prior adaptive EVSI policy.

`calibrate_measurements` sees binary outcomes only. `run_experiment` owns the
simulator and adds hidden-truth evaluation AFTER the recommendation. Neither
function performs networking or persistence; the optional CLI writes JSON.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import math
from pathlib import Path
import platform

import numpy as np
import scipy
from scipy.stats import beta as beta_distribution

from . import __version__
from .adaptive_calibration import MixturePlanner, default_as_mixtures, run_sequential
from .bayes import BayesianPlanner, BetaPrior, DEFAULT_PRIORS
from .circuits import make_circuit, pauli_label, stabilizer_generators
from .diagnostics import sample_truth
from .loss import GROUPS, PlacementModel
from .robust_decision import guarded_placement

SCHEMA_VERSION = "1.0"
ALGORITHM_VERSION = "adaptive-original-v1"
SEED_SCHEME = "seedsequence-truth-and-three-groups-v1"
FAMILIES = ("ghz", "layered", "star")
TRUTH_MODES = ("prior", "shifted", "local_shift", "link_shift")


def _integer(name: str, value: int, minimum: int, maximum: int) -> None:
    # Reject booleans, floats and implicit coercion at the public boundary.
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")


@dataclass(frozen=True)
class CalibrationConfig:
    """Only settings available to the decision engine; original priors are fixed."""

    family: str = "layered"
    qubits: int = 6
    shots: int = 100
    guard_enabled: bool = True
    guard_threshold: float = 0.60
    guard_draws: int = 512

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(f"family must be one of {FAMILIES}")
        if type(self.qubits) is not int or self.qubits not in (6, 12):
            raise ValueError("qubits must be 6 or 12")
        _integer("shots", self.shots, 20, 1000)
        _integer("guard_draws", self.guard_draws, 64, 16384)
        if type(self.guard_enabled) is not bool:
            raise ValueError("guard_enabled must be a boolean")
        if (type(self.guard_threshold) not in (int, float)
                or not math.isfinite(self.guard_threshold)
                or not 0.5 <= self.guard_threshold <= 1.0):
            raise ValueError("guard_threshold must be finite and in [0.5, 1]")
        object.__setattr__(self, "guard_threshold", float(self.guard_threshold))


@dataclass(frozen=True)
class SimulationConfig(CalibrationConfig):
    """Simulation settings, kept outside the measurement-only interface."""

    seed: int = 42
    truth_mode: str = "shifted"

    def __post_init__(self) -> None:
        super().__post_init__()
        _integer("seed", self.seed, 0, 2**32 - 1)
        if self.truth_mode not in TRUTH_MODES:
            raise ValueError(f"truth_mode must be one of {TRUTH_MODES}")

    def calibration_config(self) -> CalibrationConfig:
        return CalibrationConfig(**{
            field.name: getattr(self, field.name) for field in fields(CalibrationConfig)
        })


def _posterior_snapshot(priors: tuple[BetaPrior, ...]) -> dict:
    """Credible intervals describe model uncertainty, not hardware guarantees."""
    return {
        group: {
            "alpha": float(prior.alpha), "beta": float(prior.beta),
            "mean": float(prior.mean),
            "credible_interval_95": beta_distribution.ppf(
                [0.025, 0.975], prior.alpha, prior.beta
            ).tolist(),
        }
        for group, prior in zip(GROUPS, priors)
    }


def _placement(model: PlacementModel, index: int) -> dict:
    assignment = model.mappings[index]
    counts = dict.fromkeys(GROUPS, 0)
    for gate in model.circuit.gates:
        if gate.name == "cx":
            a, b = assignment[gate.control], assignment[gate.target]
            counts[GROUPS[2 if a != b else a]] += 1
    return {
        "index": int(index), "assignment": list(assignment),
        "qpu_a": [q for q, label in enumerate(assignment) if label == 0],
        "qpu_b": [q for q, label in enumerate(assignment) if label == 1],
        "cx_counts": counts,
    }


def calibrate_measurements(
    config: CalibrationConfig,
    stream: np.ndarray,
    *,
    guard_seed: int = 2026,
) -> dict:
    """Return JSON-safe evidence using ONLY allocated binary measurements.

    `stream` contains three available outcome streams in local_a/local_b/remote
    order, each of length `shots`. The existing engine consumes exactly `shots`
    in total across groups, never the entire 3*shots reservoir. Unused outcomes
    are not returned. Pass the M2C sampling seed explicitly for exact replay.
    """
    if type(config) is not CalibrationConfig:
        raise ValueError("Pass a CalibrationConfig without simulation settings")
    _integer("guard_seed", guard_seed, 0, 2**63 - 1)
    observations = np.asarray(stream)
    if (observations.shape != (3, config.shots)
            or observations.dtype.kind not in "biuf"
            or not np.all((observations == 0) | (observations == 1))):
        raise ValueError("stream must have shape (3, shots) and contain only binary 0/1 values")
    observations = observations.astype(bool, copy=True)
    model = PlacementModel(make_circuit(config.qubits, config.family))
    # Preserve M2C's incumbent calculation and deterministic tie ordering.
    incumbent, prior_loss = BayesianPlanner(model).recommend(DEFAULT_PRIORS)
    adaptive = run_sequential(
        model, observations, config.shots, priors=default_as_mixtures()
    )
    candidate = int(adaptive["chosen_index"])
    expected = MixturePlanner(model).expected_losses(adaptive["posterior"])

    if config.guard_enabled:
        guarded = guarded_placement(
            model, adaptive["posterior"], incumbent,
            minimum_probability=config.guard_threshold,
            posterior_draws=config.guard_draws, seed=guard_seed,
        )
        final = int(guarded["chosen_index"])
        probability = guarded["posterior_probability_better"]
        reason = guarded["reason"]
        if candidate == incumbent:
            status = "unchanged"
        elif probability is None:
            status = "no_positive_gain"
        else:
            status = "accepted" if guarded["switched"] else "rejected"
    else:
        final, probability = candidate, None
        status = "unguarded" if candidate != incumbent else "unchanged"
        reason = ("Guard disabled: use the posterior expected-loss optimum"
                  if candidate != incumbent else
                  "Candidate is the incumbent; no switch is proposed")

    # Enrich the engine's trace by replaying its observed counts through the
    # existing conjugate update. No re-planning or altered scientific math.
    beliefs = DEFAULT_PRIORS
    used = dict.fromkeys(GROUPS, 0)
    failures = dict.fromkeys(GROUPS, 0)
    trace = []
    for number, step in enumerate(adaptive["trace"], 1):
        before = _posterior_snapshot(beliefs)
        group = step["group"]
        index = GROUPS.index(group)
        updated = list(beliefs)
        updated[index] = beliefs[index].updated(step["failures"], step["shots"])
        beliefs = tuple(updated)
        used[group] += step["shots"]
        failures[group] += step["failures"]
        trace.append({
            **step, "step": number,
            "posteriors_before": before,
            "posteriors_after": _posterior_snapshot(beliefs),
            "cumulative_shots": sum(used.values()),
            "cumulative_shots_by_group": dict(used),
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "algorithm": {"method": "adaptive_evsi", "version": ALGORITHM_VERSION,
                      "prior_model": "original_beta"},
        "configuration": asdict(config),
        "guard_seed": guard_seed,
        "circuit": {
            "family": config.family, "qubits": config.qubits,
            "gates": [asdict(gate) for gate in model.circuit.gates],
            "cx_count": model.circuit.cx_count,
            "placement_count": len(model.mappings),
            "stabilizers": [pauli_label(x, z, config.qubits)
                            for x, z in stabilizer_generators(model.circuit)],
        },
        "initial_priors": _posterior_snapshot(DEFAULT_PRIORS),
        "calibration": {
            "pilot_shots": dict(zip(GROUPS, adaptive["pilot_shots"])),
            "adaptive_batches": adaptive["adaptive_batches"],
            "shots_by_group": used, "failures_by_group": failures,
            "total_shots": adaptive["total_shots"], "trace": trace,
        },
        "final_posterior": _posterior_snapshot(beliefs),
        "placements": {"initial": _placement(model, incumbent),
                       "candidate": _placement(model, candidate),
                       "final": _placement(model, final)},
        "loss": {
            "objective": "mean_stabilizer_generator_parity_error",
            "initial_under_prior": float(prior_loss),
            "initial_under_posterior": float(expected[incumbent]),
            "candidate_under_posterior": float(expected[candidate]),
            "final_under_posterior": float(expected[final]),
            "candidate_expected_improvement": float(expected[incumbent] - expected[candidate]),
            "accepted_expected_improvement": float(expected[incumbent] - expected[final]),
        },
        "decision": {
            "switched": final != incumbent, "status": status, "reason": reason,
            "guard_enabled": config.guard_enabled,
            "guard_threshold": config.guard_threshold,
            "posterior_probability_better": probability,
            "posterior_draws_used": config.guard_draws if probability is not None else 0,
            "probability_interpretation": (
                "Sampled posterior probability that the candidate improves on the initial placement"
                if probability is not None else
                "Not estimated: guard disabled or no positive expected-loss switch proposed"
            ),
        },
    }


def _simulate_observations(config: SimulationConfig) -> tuple[tuple, np.ndarray]:
    # Independent RNGs keep truth and every group's measurement prefixes fixed
    # as the budget changes. This seed scheme differs from the historical suite;
    # policy equivalence is defined on identical outcomes and guard samples.
    children = np.random.SeedSequence(config.seed).spawn(4)
    truth = sample_truth(np.random.default_rng(children[0]), config.truth_mode)
    stream = np.stack([
        np.random.default_rng(child).random(config.shots) < probability
        for child, probability in zip(children[1:], truth)
    ])
    return truth, stream


def run_experiment(config: SimulationConfig | None = None) -> dict:
    """Simulate one experiment; keep oracle evaluation outside decision evidence."""
    if config is None:
        config = SimulationConfig()
    if type(config) is not SimulationConfig:
        raise ValueError("config must be a SimulationConfig")
    truth, stream = _simulate_observations(config)
    result = calibrate_measurements(
        config.calibration_config(), stream, guard_seed=config.seed * 100_003
    )

    # Only the simulator sees truth. Grade the already completed decision.
    model = PlacementModel(make_circuit(config.qubits, config.family))
    actual = model.losses(truth)
    oracle = int(np.argmin(actual))
    initial = result["placements"]["initial"]["index"]
    candidate = result["placements"]["candidate"]["index"]
    final = result["placements"]["final"]["index"]
    metadata = {
        "schema_version": SCHEMA_VERSION, "algorithm_version": ALGORITHM_VERSION,
        "seed_scheme": SEED_SCHEME,
        "runtime": {"qbridge": __version__, "python": platform.python_version(),
                    "numpy": np.__version__, "scipy": scipy.__version__},
    }
    identity = json.dumps({"configuration": asdict(config), **metadata},
                          sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {
        "experiment_id": "qb_" + hashlib.sha256(identity.encode()).hexdigest()[:32],
        "mode": "simulation", "configuration": asdict(config), "metadata": metadata,
        "result": result,
        "evaluation": {
            "label": "Simulator-only evaluation; unavailable to the recommendation engine",
            "true_error_rates": dict(zip(GROUPS, truth)),
            "oracle_placement": _placement(model, oracle),
            "oracle_loss": float(actual[oracle]),
            "initial_actual_loss": float(actual[initial]),
            "candidate_actual_loss": float(actual[candidate]),
            "final_actual_loss": float(actual[final]),
            "regret": max(0.0, float(actual[final] - actual[oracle])),
            "actual_improvement": float(actual[initial] - actual[final]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=FAMILIES, default="layered")
    parser.add_argument("--qubits", type=int, choices=(6, 12), default=6)
    parser.add_argument("--shots", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--truth-mode", choices=TRUTH_MODES, default="shifted")
    parser.add_argument("--unguarded", action="store_true")
    parser.add_argument("--guard-threshold", type=float, default=0.60)
    parser.add_argument("--guard-draws", type=int, default=512)
    parser.add_argument("--output", type=Path, help="Optional new JSON file; existing files are not overwritten")
    args = parser.parse_args()
    try:
        config = SimulationConfig(
            family=args.family, qubits=args.qubits, shots=args.shots, seed=args.seed,
            truth_mode=args.truth_mode, guard_enabled=not args.unguarded,
            guard_threshold=args.guard_threshold, guard_draws=args.guard_draws,
        )
        rendered = json.dumps(run_experiment(config), indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        print(rendered, end="")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
