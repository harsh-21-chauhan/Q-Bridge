"""M2C: tests of fairness, held-out policy logic and reproducibility."""
import numpy as np
import pytest
from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel
from qbridge.m2c_validation import evaluate, POLICIES


def _model(family="layered", qubits=6):
    return PlacementModel(make_circuit(qubits, family))


def test_m2c_paired_shot_accounting_and_reproducible():
    summary, rows = evaluate(_model(), runs=6, shots=50, seed=98771)
    repeat, rows2 = evaluate(_model(), runs=6, shots=50, seed=98771)
    assert rows == rows2
    assert summary == repeat
    assert len(rows) == 6 * len(POLICIES)
    for row in rows:
        assert row["shots_spent"] == (0 if row["policy"] == "no_calibration" else 50)
        assert row["regret"] >= 0
        assert row["task_loss"] >= row["oracle_loss"] - 1e-12
    for trial in range(6):
        batch = [r for r in rows if r["trial"] == trial]
        assert len(batch) == len(POLICIES)
        assert len({r["true_remote"] for r in batch}) == 1
        assert len({r["oracle_loss"] for r in batch}) == 1


def test_moderate_guard_switches_superset_of_strict_guard():
    _, rows = evaluate(_model(), runs=12, shots=50, seed=31337, truth_mode="prior")
    for trial in range(12):
        p60 = next(r for r in rows if r["trial"] == trial and r["policy"] == "adaptive_original_guard60")
        p75 = next(r for r in rows if r["trial"] == trial and r["policy"] == "adaptive_original_guard75")
        assert p75["switched"] <= p60["switched"]
        if p75["switched"]:
            assert p75["placement"] == p60["placement"]
        assert p60["posterior_probability_better"] == p75["posterior_probability_better"]


def test_m2c_multiple_circuits_and_noise_modes():
    for family, truth_mode in (("ghz", "shifted"), ("star", "local_shift")):
        summary, rows = evaluate(_model(family), runs=3, shots=50, seed=456, truth_mode=truth_mode)
        assert set(summary["policies"]) == set(POLICIES)
        assert len(rows) == 3 * len(POLICIES)


def test_m2c_input_validation():
    with pytest.raises(ValueError):
        evaluate(_model(), runs=1)
    with pytest.raises(ValueError):
        evaluate(_model(), shots=10)
    with pytest.raises(ValueError):
        evaluate(_model(), truth_mode="unknown")
