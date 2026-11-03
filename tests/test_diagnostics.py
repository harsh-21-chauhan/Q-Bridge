"""M2 checks: no changes to the original M1 tests are required."""
import numpy as np
import pytest
from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel
from qbridge.diagnostics import diagnose, sample_truth, _distinct_margin


def test_distinct_margin_reports_ties():
    margin, tied = _distinct_margin(np.array([0.2, 0.1, 0.1, 0.3]))
    assert margin == pytest.approx(0.1)
    assert tied == 2


def test_truth_modes_are_bounded():
    for mode in ("prior", "shifted", "link_shift", "local_shift"):
        truth = sample_truth(np.random.default_rng(42), mode)
        assert len(truth) == 3
        assert all(0 <= p <= 1 for p in truth)


def test_diagnostics_pairs_same_environments_and_keeps_no_calibration_fixed():
    model = PlacementModel(make_circuit(6, "layered"))
    report, rows = diagnose(model, runs=8, shots=(20, 50), seed=2, truth_mode="prior")
    assert len(rows) == 8 * 2 * 5
    assert set(report["budgets"]) == {"20", "50"}
    for b in (20, 50):
        per_budget = [r for r in rows if r["shots"] == b]
        assert len(per_budget) == 8 * 5
        for run in range(8):
            per_run = [r for r in per_budget if r["run"] == run]
            assert len({(r["true_local_a"], r["true_local_b"], r["true_remote"]) for r in per_run}) == 1
            baseline = next(r for r in per_run if r["policy"] == "no_calibration")
            assert baseline["switched"] == 0
            assert baseline["gain_vs_no_cal"] == pytest.approx(0)
            for r in per_run:
                assert r["regret"] >= 0
                assert r["shots"] == b
                assert r["gain_vs_no_cal"] == pytest.approx(baseline["regret"] - r["regret"])
        # Pairwise paired comparisons use policy differences, not separate means.
        evsi = np.array([r["regret"] for r in per_budget if r["policy"] == "evsi"])
        random = np.array([r["regret"] for r in per_budget if r["policy"] == "random"])
        assert report["budgets"][str(b)]["paired_comparisons"]["evsi_minus_random"]["mean_regret_difference"] == pytest.approx(np.mean(evsi - random))
