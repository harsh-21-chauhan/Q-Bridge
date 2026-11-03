"""Production policy checks against preserved M2C evidence and measurement data."""
import csv
from dataclasses import replace
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest

from qbridge import production
from qbridge.adaptive_calibration import default_as_mixtures
from qbridge.bayes import DEFAULT_PRIORS
from qbridge.circuits import make_circuit
from qbridge.diagnostics import sample_truth
from qbridge.loss import GROUPS, PlacementModel
from qbridge.production import (
    CalibrationConfig, SimulationConfig, calibrate_measurements, run_experiment,
)
from qbridge.robust_decision import guarded_placement

EVIDENCE = Path(__file__).resolve().parents[1] / "research/evidence/QBridge-M2C-full-runs100.zip"


@pytest.mark.parametrize(("family", "qubits", "shots", "truth_mode"), [
    (family, qubits, shots, mode)
    for family in ("ghz", "layered", "star")
    for qubits in (6, 12)
    for shots in (50, 100, 200)
    for mode in ("prior", "shifted")
] + [
    ("layered", 12, shots, mode)
    for shots in (100, 200)
    for mode in ("local_shift", "link_shift")
])
def test_matches_archived_m2c_policy_on_identical_inputs(family, qubits, shots, truth_mode):
    """Compare to frozen outputs, not just two callers of today's same code."""
    seed = 20261104
    member = f"m2c/{family}{qubits}_{truth_mode}_shots{shots}_runs100_seed{seed}.csv"
    with ZipFile(EVIDENCE) as archive:
        rows = list(csv.DictReader(io.StringIO(archive.read(member).decode())))
    rng = np.random.default_rng(seed)
    for trial in range(3):
        truth = sample_truth(rng, truth_mode)
        stream = rng.random((3, shots)) < np.asarray(truth)[:, None]
        rng.integers(0, 3)  # M2C's random baseline consumes this before the next trial.
        expected = next(r for r in rows if int(r["trial"]) == trial
                        and r["policy"] == "adaptive_original_guard60")
        unguarded = next(r for r in rows if int(r["trial"]) == trial
                         and r["policy"] == "adaptive_original")
        result = calibrate_measurements(
            CalibrationConfig(family=family, qubits=qubits, shots=shots),
            stream, guard_seed=seed * 100_003 + trial,
        )
        placements = result["placements"]
        assert "".join(map(str, placements["final"]["assignment"])) == expected["placement"]
        assert "".join(map(str, placements["candidate"]["assignment"])) == unguarded["placement"]
        assert result["decision"]["switched"] == bool(int(expected["switched"]))
        probability = result["decision"]["posterior_probability_better"]
        assert probability == (float(expected["posterior_probability_better"])
                               if expected["posterior_probability_better"] else None)
        if expected["expected_gain"]:
            assert result["loss"]["candidate_expected_improvement"] == pytest.approx(
                float(expected["expected_gain"]), abs=1e-12
            )
        for old_step, step in zip(json.loads(expected["calibration_trace"]),
                                  result["calibration"]["trace"], strict=True):
            for key, value in old_step.items():
                if isinstance(value, (float, dict)):
                    assert step[key] == pytest.approx(value, abs=1e-12)
                else:
                    assert step[key] == value
        actual = PlacementModel(make_circuit(qubits, family)).losses(truth)
        assert actual[placements["final"]["index"]] == pytest.approx(float(expected["task_loss"]), abs=1e-12)


@pytest.mark.parametrize("shots", [20, 21, 49, 50, 99, 100, 101, 200, 999, 1000])
def test_original_priors_trace_and_exact_budget(shots):
    rng = np.random.default_rng(17)
    stream = rng.random((3, shots)) < np.array([.08, .03, .15])[:, None]
    result = calibrate_measurements(CalibrationConfig(shots=shots), stream)
    calibration = result["calibration"]
    assert calibration["total_shots"] == shots
    assert sum(calibration["shots_by_group"].values()) == shots
    assert sum(s["shots"] for s in calibration["trace"]) == shots
    assert len(calibration["trace"]) == 5
    used = dict.fromkeys(GROUPS, 0)
    beliefs = dict(zip(GROUPS, DEFAULT_PRIORS))
    previous = result["initial_priors"]
    for step in calibration["trace"]:
        group = step["group"]
        start, end = used[group], used[group] + step["shots"]
        k = int(stream[GROUPS.index(group), start:end].sum())
        assert k == step["failures"]
        assert step["posteriors_before"] == previous
        beliefs[group] = beliefs[group].updated(k, step["shots"])
        for name, prior in beliefs.items():
            snapshot = step["posteriors_after"][name]
            assert snapshot["alpha"] == prior.alpha
            assert snapshot["beta"] == prior.beta
            assert snapshot["mean"] == pytest.approx(prior.mean)
            low, high = snapshot["credible_interval_95"]
            assert 0 < low < prior.mean < high < 1
        used[group] = end
        assert step["cumulative_shots"] == sum(used.values())
        assert step["cumulative_shots_by_group"] == used
        if step["stage"] == "pilot":
            assert step["evsi_at_choice"] is None
        else:
            scores = step["evsi_at_choice"]
            assert set(scores) == set(GROUPS)
            assert scores[group] == max(scores.values())
        previous = step["posteriors_after"]
    assert result["final_posterior"] == previous
    for group, prior in zip(GROUPS, DEFAULT_PRIORS):
        assert result["initial_priors"][group]["alpha"] == prior.alpha
        assert result["initial_priors"][group]["beta"] == prior.beta
    if shots == 100:
        assert list(calibration["pilot_shots"].values()) == [10, 10, 20]
        assert calibration["adaptive_batches"] == [30, 30]


def test_no_switch_has_no_placeholder_probability():
    result = calibrate_measurements(CalibrationConfig(), np.zeros((3, 100), bool))
    assert result["placements"]["candidate"] == result["placements"]["initial"]
    assert result["decision"]["status"] == "unchanged"
    assert result["decision"]["posterior_probability_better"] is None
    assert result["decision"]["posterior_draws_used"] == 0
    assert result["loss"]["accepted_expected_improvement"] == 0


def test_guard_accepts_and_rejects_and_unguarded_uses_candidate(monkeypatch):
    certain = np.zeros((3, 100), bool)
    certain[0] = True
    accepted = calibrate_measurements(CalibrationConfig(), certain, guard_seed=7)
    assert accepted["decision"]["status"] == "accepted"
    assert accepted["decision"]["posterior_probability_better"] >= .6
    assert accepted["loss"]["accepted_expected_improvement"] > 0

    stream = np.random.default_rng(42).random((3, 100)) < np.array([.045, .012, .085])[:, None]
    rejected = calibrate_measurements(CalibrationConfig(), stream, guard_seed=42 * 100_003)
    assert rejected["decision"]["status"] == "rejected"
    assert rejected["decision"]["posterior_probability_better"] < .6
    assert rejected["loss"]["candidate_expected_improvement"] > 0
    assert rejected["loss"]["accepted_expected_improvement"] == 0
    assert rejected["placements"]["final"] == rejected["placements"]["initial"]

    def forbidden(*args, **kwargs):
        raise AssertionError("An unguarded decision must not sample a guard probability")
    monkeypatch.setattr(production, "guarded_placement", forbidden)
    unguarded = calibrate_measurements(CalibrationConfig(guard_enabled=False), stream)
    assert unguarded["placements"]["final"] == rejected["placements"]["candidate"]
    assert unguarded["decision"]["posterior_probability_better"] is None
    assert unguarded["calibration"] == rejected["calibration"]
    losses = unguarded["loss"]
    assert losses["accepted_expected_improvement"] == pytest.approx(
        losses["initial_under_posterior"] - losses["final_under_posterior"]
    )


def test_guard_negligible_gain_is_not_fabricated_probability(monkeypatch):
    from qbridge.adaptive_calibration import MixturePlanner
    model = PlacementModel(make_circuit(6, "layered"))
    losses = np.full(20, .2)
    losses[0], losses[1] = .1, .1 + 5e-11
    monkeypatch.setattr(MixturePlanner, "expected_losses", lambda self, posterior: losses)
    decision = guarded_placement(model, default_as_mixtures(), 1)
    assert decision["candidate_index"] == 0
    assert decision["chosen_index"] == 1
    assert decision["posterior_probability_better"] is None
    assert "tolerance" in decision["reason"]


def test_unconsumed_measurements_do_not_affect_recommendation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Decision function must not call simulator/oracle loss evaluation")
    monkeypatch.setattr(PlacementModel, "losses", forbidden)
    stream = np.random.default_rng(8).random((3, 100)) < .05
    before = stream.copy()
    first = calibrate_measurements(CalibrationConfig(), stream)
    np.testing.assert_array_equal(stream, before)
    for group, used in enumerate(first["calibration"]["shots_by_group"].values()):
        stream[group, used:] = ~stream[group, used:]
    assert calibrate_measurements(CalibrationConfig(), stream) == first


@pytest.mark.parametrize("truth_mode", production.TRUTH_MODES)
def test_simulation_reproducibility_evaluation_and_budget_prefixes(truth_mode):
    config = SimulationConfig(truth_mode=truth_mode)
    first = run_experiment(config)
    assert run_experiment(config) == first
    assert json.loads(json.dumps(first, allow_nan=False)) == first
    larger = replace(config, shots=200)
    truth, stream = production._simulate_observations(config)
    truth2, stream2 = production._simulate_observations(larger)
    assert truth == truth2
    np.testing.assert_array_equal(stream, stream2[:, :config.shots])
    assert run_experiment(larger)["experiment_id"] != first["experiment_id"]
    assert run_experiment(replace(config, seed=config.seed + 1))["experiment_id"] != first["experiment_id"]
    assert run_experiment(replace(config, guard_enabled=False))["experiment_id"] != first["experiment_id"]
    serialized = json.dumps(first["result"])
    for private_field in ("true_error_rates", "truth_mode", "oracle", "regret"):
        assert private_field not in serialized
    evaluation = first["evaluation"]
    model = PlacementModel(make_circuit(config.qubits, config.family))
    actual = model.losses(tuple(evaluation["true_error_rates"][g] for g in GROUPS))
    for name in ("initial", "candidate", "final"):
        p = first["result"]["placements"][name]
        assert evaluation[f"{name}_actual_loss"] == pytest.approx(actual[p["index"]])
        assert len(p["qpu_a"]) == len(p["qpu_b"]) == config.qubits // 2
        assert sum(p["cx_counts"].values()) == model.circuit.cx_count
    assert evaluation["regret"] == pytest.approx(evaluation["final_actual_loss"] - min(actual))


def test_changing_evaluation_truth_with_fixed_measurements_cannot_change_decision(monkeypatch):
    stream = np.zeros((3, 100), bool)
    monkeypatch.setattr(production, "_simulate_observations", lambda config: ((.01, .02, .03), stream))
    first = run_experiment()
    monkeypatch.setattr(production, "_simulate_observations", lambda config: ((.2, .3, .4), stream))
    second = run_experiment()
    assert first["result"] == second["result"]
    assert first["evaluation"] != second["evaluation"]


@pytest.mark.parametrize("changes", [
    {"family": "unknown"}, {"qubits": 4}, {"qubits": 14}, {"qubits": 6.0},
    {"qubits": True}, {"shots": 19}, {"shots": 1001}, {"shots": 100.0},
    {"shots": True}, {"guard_enabled": 1}, {"guard_threshold": float("nan")},
    {"guard_threshold": float("inf")}, {"guard_threshold": .49},
    {"guard_threshold": 1.01}, {"guard_threshold": True}, {"guard_threshold": "0.6"},
    {"guard_draws": 63}, {"guard_draws": 16385}, {"guard_draws": 64.0},
    {"seed": -1}, {"seed": True}, {"seed": 2**32}, {"truth_mode": "unknown"},
])
def test_invalid_configuration_rejected(changes):
    with pytest.raises(ValueError):
        SimulationConfig(**changes)


@pytest.mark.parametrize("stream", [
    np.zeros((2, 100)), np.zeros((3, 99)), np.full((3, 100), .5),
    np.full((3, 100), float("nan")), np.full((3, 100), float("inf")),
    np.full((3, 100), "0"), np.full((3, 100), 1j),
])
def test_invalid_measurements_rejected(stream):
    with pytest.raises(ValueError, match="binary"):
        calibrate_measurements(CalibrationConfig(), stream)


def test_simulator_settings_are_not_accepted_by_decision_interface():
    with pytest.raises(ValueError, match="without simulation"):
        calibrate_measurements(SimulationConfig(), np.zeros((3, 100)))
    with pytest.raises(ValueError, match="guard_seed"):
        calibrate_measurements(CalibrationConfig(), np.zeros((3, 100)), guard_seed=-1)
