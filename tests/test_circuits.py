import pytest
from qbridge.circuits import make_circuit, placements, stabilizer_generators, pauli_label


def test_six_qubit_placement_count():
    assert len(placements(6)) == 20
    assert all(p.count(0) == 3 and p.count(1) == 3 for p in placements(6))


def test_ghz_generators_include_phase_check():
    circuit = make_circuit(6, "ghz")
    labels = [pauli_label(x, z, 6) for x, z in stabilizer_generators(circuit)]
    assert "XXXXXX" in labels
    assert len(labels) == 6
    assert all(label != "IIIIII" for label in labels)


def test_invalid_circuits():
    with pytest.raises(ValueError):
        make_circuit(5)
