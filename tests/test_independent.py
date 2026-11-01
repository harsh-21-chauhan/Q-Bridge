import pytest
from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel
from qbridge.reference_sim import density_reference_loss


@pytest.mark.parametrize("family", ["ghz", "layered", "star"])
@pytest.mark.parametrize("index", [0, 9, 19])
def test_analytical_matches_independent_numpy_density_matrix(family, index):
    model = PlacementModel(make_circuit(6, family))
    independent = density_reference_loss(model, (0.035, 0.015, 0.11), index=index)
    analytical = model.losses((0.035, 0.015, 0.11))[index]
    assert abs(independent - analytical) < 1e-10
