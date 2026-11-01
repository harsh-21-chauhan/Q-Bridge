import numpy as np
from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel
from qbridge.bayes import BetaPrior, DEFAULT_PRIORS, BayesianPlanner
from qbridge.experiment import run_experiment


def test_beta_update():
    post = BetaPrior(2, 8).updated(3, 20)
    assert post == BetaPrior(5, 25)
    assert abs(post.mean - 1/6) < 1e-12


def test_quadrature_matches_point_probability_limit():
    model = PlacementModel(make_circuit(6, "layered"))
    planner = BayesianPlanner(model)
    p = (0.02, 0.04, 0.08)
    # High concentration priors approximate deterministic probabilities.
    priors = tuple(BetaPrior(v * 100000, (1-v) * 100000) for v in p)
    assert np.allclose(planner.expected_losses(priors), model.losses(p), atol=1e-5)


def test_evsi_not_negative():
    planner = BayesianPlanner(PlacementModel(make_circuit(6, "layered")))
    scores = planner.evsi(DEFAULT_PRIORS, 20)
    assert len(scores) == 3
    assert min(scores.values()) >= -1e-8


def test_posterior_and_regret():
    model = PlacementModel(make_circuit(6, "layered"))
    rec = run_experiment(model, (0.04, 0.01, 0.10), shots=30, seed=7)
    assert 0 <= rec.observed_failures <= 30
    assert len(rec.chosen_placement) == 6
    assert rec.decision_regret >= -1e-12
