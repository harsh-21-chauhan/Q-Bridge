import importlib.util
import pytest
from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel
from qbridge.aer_validation import compare_aer_to_analytical, validate_calibration

pytestmark = pytest.mark.skipif(importlib.util.find_spec("qiskit_aer") is None,
                                reason="optional Qiskit Aer not installed")


def test_aer_density_matrix_equals_exact_parity_loss():
    assert compare_aer_to_analytical(PlacementModel(make_circuit(6, "layered")))["pass"]


def test_aer_bell_diagnostic_agrees_with_binomial_model():
    assert validate_calibration()["pass"]
