"""M2B regression tests: mathematical correctness + no hidden-truth shortcuts."""
import numpy as np
import pytest
from scipy.stats import betabinom
from qbridge.bayes import DEFAULT_PRIORS, BayesianPlanner
from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel
from qbridge.robust_priors import BetaMixture, as_mixture, robust_priors
from qbridge.adaptive_calibration import (
    MixturePlanner, calibration_from_stream, default_as_mixtures,
    run_sequential, split_budget,
)
from qbridge.robust_decision import guarded_placement, _losses_for_two
from qbridge.robustness_benchmark import evaluate


def model():
    return PlacementModel(make_circuit(6, "layered"))


def test_mixture_predictions_and_evidence_update():
    m = BetaMixture((DEFAULT_PRIORS[0], DEFAULT_PRIORS[2]), (0.4, 0.6))
    pmf = m.predictive(15)
    assert pmf.sum() == pytest.approx(1)
    k = 4
    posterior = m.updated(k, 15)
    marginal = np.array([betabinom.pmf(k, 15, p.alpha, p.beta) for p in m.components])
    weights = marginal * np.array(m.weights)
    weights /= weights.sum()
    assert posterior.weights == pytest.approx(weights)
    assert sum(posterior.weights) == pytest.approx(1)


def test_robust_prior_preserves_means_but_has_diffuse_component():
    m = robust_priors()
    assert [v.mean for v in m] == pytest.approx([p.mean for p in DEFAULT_PRIORS])
    assert len(m[2].components) == 2
    assert m[2].components[1].alpha + m[2].components[1].beta == pytest.approx(20)


def test_one_component_planner_matches_existing_bayesian():
    base = BayesianPlanner(model())
    new = MixturePlanner(model())
    prior = default_as_mixtures()
    assert np.allclose(new.expected_losses(prior), base.expected_losses(DEFAULT_PRIORS), atol=1e-12)
    assert new.evsi(prior, 20) == pytest.approx(base.evsi(DEFAULT_PRIORS, 20), abs=1e-10)


def test_sequential_budget_trace_and_reproducibility():
    m = model()
    stream = np.random.default_rng(3).random((3, 100)) < np.array([.02, .05, .15])[:, None]
    result = run_sequential(m, stream, budget=100)
    other = run_sequential(m, stream, budget=100)
    assert result["total_shots"] == 100
    assert sum(result["used_shots"]) == 100
    assert result["trace"] == other["trace"]
    assert [s["shots"] for s in result["trace"][:3]] == [10, 10, 20]
    assert [s["shots"] for s in result["trace"][3:]] == [30, 30]
    assert result["trace"][3]["evsi_at_choice"] is not None


def test_stream_consumption_never_reuses_shots():
    stream = np.zeros((3, 12), dtype=bool)
    stream[2, 0:4] = [True, False, True, False]
    stream[2, 4:8] = [False, True, True, True]
    used = [0, 0, 0]
    assert calibration_from_stream(stream, used, 2, 4) == 2
    assert calibration_from_stream(stream, used, 2, 4) == 3
    assert used == [0, 0, 8]
    with pytest.raises(ValueError):
        calibration_from_stream(stream, used, 2, 5)


def test_budget_ranges():
    for budget in (20, 50, 100, 200, 500, 1000):
        pilot, batches = split_budget(budget)
        assert sum(pilot + batches) == budget
        assert all(x > 0 for x in pilot + batches)
    with pytest.raises(ValueError):
        split_budget(10)


def test_guard_loss_samples_match_scalar_model():
    m = model()
    params = np.array([[.02, .03, .15], [.10, .01, .01]])
    result = _losses_for_two(m, (0, 4), params)
    for i in range(2):
        exact = m.losses(tuple(params[i]))
        assert result[i, 0] == pytest.approx(exact[0], abs=1e-12)
        assert result[i, 1] == pytest.approx(exact[4], abs=1e-12)


def test_guard_uses_only_posterior_and_can_reject():
    m = model()
    posterior = robust_priors()
    planner = MixturePlanner(m)
    incumbent = planner.recommend(posterior)[0]
    x = guarded_placement(m, posterior, incumbent, minimum_probability=.75, seed=30)
    assert x["chosen_index"] == incumbent
    assert not x["switched"]
    assert 0 <= x["posterior_probability_better"] <= 1


def test_benchmark_is_paired_deterministic_and_budget_fair():
    m = model()
    a, rows = evaluate(m, runs=3, shots=50, seed=123, truth_mode="link_shift", guard_draws=64)
    b, rows2 = evaluate(m, runs=3, shots=50, seed=123, truth_mode="link_shift", guard_draws=64)
    assert a["policies"] == b["policies"]
    assert a["paired_comparisons"] == b["paired_comparisons"]
    assert rows == rows2
    assert len(rows) == 3*7
    assert all(r["shots_spent"] == (0 if r["policy"] == "no_calibration" else 50) for r in rows)
