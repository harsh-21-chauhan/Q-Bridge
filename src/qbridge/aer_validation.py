"""Independent Qiskit Aer density-matrix checks, run with `pip install -e '.[aer]'`."""
import numpy as np
from .circuits import pauli_label, stabilizer_generators


def _imports():
    try:
        from qiskit import QuantumCircuit
        from qiskit.quantum_info import DensityMatrix, Pauli
        from qiskit_aer import AerSimulator
        from qiskit_aer.noise import pauli_error
    except ImportError as exc:
        raise RuntimeError("Install Qiskit dependencies first: pip install -e '.[aer,dev]'") from exc
    return QuantumCircuit, DensityMatrix, Pauli, AerSimulator, pauli_error


def _error(p, pauli_error):
    # Qiskit Pauli labels are right-to-left in qubit index; on qargs [control,target],
    # XI means X(target); IZ means Z(control).
    return pauli_error([("II", 1.0 - p), ("XI", p / 2), ("IZ", p / 2)])


def compare_aer_to_analytical(model, parameters=(0.045, 0.012, 0.085), index=0):
    QuantumCircuit, DensityMatrix, Pauli, AerSimulator, pauli_error = _imports()
    if model.circuit.n_qubits > 8:
        raise ValueError("density-matrix validation limited to <=8 qubits")
    mapping = model.mappings[index]
    qc = QuantumCircuit(model.circuit.n_qubits)
    for gate in model.circuit.gates:
        if gate.name == "h":
            qc.h(gate.control)
        else:
            c, t = gate.control, gate.target
            qc.cx(c, t)
            g = 2 if mapping[c] != mapping[t] else mapping[c]
            qc.append(_error(parameters[g], pauli_error).to_instruction(), [c, t])
    qc.save_density_matrix()
    sim = AerSimulator(method="density_matrix")
    rho = DensityMatrix(sim.run(qc).result().data(0)["density_matrix"])
    observed = []
    for x, z in stabilizer_generators(model.circuit):
        pauli = Pauli(pauli_label(x, z, model.circuit.n_qubits))
        observed.append((1 - float(np.real(rho.expectation_value(pauli)))) / 2)
    result_loss = float(np.mean(observed))
    analytical = float(model.losses(parameters)[index])
    return {"aer_loss": result_loss, "analytical_loss": analytical,
            "absolute_difference": abs(result_loss - analytical),
            "pass": abs(result_loss - analytical) < 1e-7}


def calibration_shots(p=0.075, shots=8192, seed=42):
    """Actual Aer-simulated binary calibration of the effective CX channel."""
    QuantumCircuit, _, _, AerSimulator, pauli_error = _imports()
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.append(_error(p, pauli_error).to_instruction(), [0, 1])
    qc.cx(0, 1)
    qc.h(0)
    qc.measure([0, 1], [0, 1])
    counts = AerSimulator().run(qc, shots=shots, seed_simulator=seed).result().get_counts()
    return shots - counts.get("00", 0)


def validate_calibration(p=0.075, shots=8192):
    failures = calibration_shots(p, shots, seed=42)
    estimate = failures / shots
    return {"expected_p": p, "observed_failure_frequency": estimate,
            "shots": shots, "pass": abs(estimate - p) < 0.025}
