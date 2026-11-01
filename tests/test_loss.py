import numpy as np
from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel


def test_no_noise_has_zero_task_loss():
    model = PlacementModel(make_circuit(6, "layered"))
    assert np.allclose(model.losses((0, 0, 0)), 0)


def test_task_loss_bounded():
    model = PlacementModel(make_circuit(6, "star"))
    loss = model.losses((0.025, 0.04, 0.08))
    assert np.all((loss >= 0) & (loss <= 1))


def test_link_error_changes_some_placement_scores():
    model = PlacementModel(make_circuit(6, "layered"))
    a = model.losses((0.02, 0.03, 0.01))
    b = model.losses((0.02, 0.03, 0.18))
    assert np.max(np.abs(a - b)) > 0.04
