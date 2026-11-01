"""Independent small-qubit density-matrix simulator written with NumPy.

Used to test the analytical stabilizer-loss engine without relying on an
external quantum SDK. Deliberately limited to <=6 qubits (unit tests only).
"""
import numpy as np
from .circuits import stabilizer_generators

_I = np.eye(2, dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Z = np.diag([1, -1]).astype(complex)
_H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def _operator(n, index, op):
    out = np.array([[1.0]], dtype=complex)
    for i in reversed(range(n)):
        out = np.kron(out, op if i == index else _I)
    return out


def density_reference_loss(model, parameters=(0.045, 0.012, 0.085), index=0):
    n = model.circuit.n_qubits
    if n > 6:
        raise ValueError("NumPy independent check is limited to <=6 qubits")
    dim = 1 << n
    rho = np.zeros((dim, dim), dtype=complex)
    rho[0, 0] = 1
    mapping = model.mappings[index]
    basis = np.arange(dim)
    for gate in model.circuit.gates:
        if gate.name == "h":
            h = _operator(n, gate.control, _H)
            rho = h @ rho @ h.conj().T
            continue
        c, t = gate.control, gate.target
        # CNOT permutation, old computational basis index j -> perm[j].
        perm = basis ^ (((basis >> c) & 1) << t)
        rho = rho[np.ix_(perm, perm)]
        group = 2 if mapping[c] != mapping[t] else mapping[c]
        p = parameters[group]
        xperm = basis ^ (1 << t)
        sign = np.where((basis >> c) & 1, -1, 1)
        x_rho = rho[np.ix_(xperm, xperm)]
        z_rho = sign[:, None] * rho * sign[None, :]
        rho = (1 - p) * rho + (p / 2) * (x_rho + z_rho)

    losses = []
    for x, z in stabilizer_generators(model.circuit):
        pauli = np.array([[1.0]], dtype=complex)
        for i in reversed(range(n)):
            op = _X if (x >> i) & 1 else _Z if (z >> i) & 1 else _I
            pauli = np.kron(pauli, op)
        exp = np.real(np.trace(rho @ pauli))
        losses.append((1 - exp) / 2)
    return float(np.mean(losses))
