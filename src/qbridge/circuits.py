"""Deterministic Clifford circuits with an explicitly specified logical-qubit layout.

Circuits here use H on qubit 0 followed by CNOT gates. Therefore each
initial |0> stabilizer stays either X-only or Z-only, and no phase tracking
is necessary for our stabilizer-generator calculations.
"""
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Gate:
    name: str
    control: int
    target: int = -1


@dataclass(frozen=True)
class CircuitSpec:
    n_qubits: int
    family: str
    gates: tuple[Gate, ...]

    @property
    def cx_count(self) -> int:
        return sum(g.name == "cx" for g in self.gates)


def make_circuit(n_qubits: int = 6, family: str = "layered") -> CircuitSpec:
    if n_qubits < 4 or n_qubits % 2:
        raise ValueError("n_qubits must be even and at least 4")
    if family not in {"ghz", "layered", "star"}:
        raise ValueError("family must be 'ghz', 'layered', or 'star'")

    gates: list[Gate] = [Gate("h", 0)]
    if family == "star":
        edges = [(0, i) for i in range(1, n_qubits)]
        # Nontrivial extra gates make the interaction graph differ from GHZ chain.
        edges += [(i, i + 1) for i in range(1, n_qubits - 1, 2)]
    else:
        edges = [(i, i + 1) for i in range(n_qubits - 1)]
        if family == "layered":
            # Deterministic long-range interactions; no hidden randomness.
            edges += [(i, i + n_qubits // 2) for i in range(n_qubits // 2)]
            edges += [(i, i + 2) for i in range(0, n_qubits - 2, 2)]
    gates.extend(Gate("cx", c, t) for c, t in edges)
    return CircuitSpec(n_qubits, family, tuple(gates))


def placements(n_qubits: int) -> list[tuple[int, ...]]:
    """All labelled A/B mappings with n//2 logical qubits on QPU A.

    0 denotes A, 1 denotes B. This is exhaustive for small circuits only.
    """
    if n_qubits % 2:
        raise ValueError("equal-sized QPUs require an even qubit count")
    result = []
    for a_qubits in combinations(range(n_qubits), n_qubits // 2):
        a = set(a_qubits)
        result.append(tuple(0 if i in a else 1 for i in range(n_qubits)))
    return result


def _conjugate(x: int, z: int, gate: Gate) -> tuple[int, int]:
    """Conjugate Pauli masks by H or CX, ignoring phase (safe here)."""
    if gate.name == "h":
        bit = 1 << gate.control
        x0 = bool(x & bit)
        z0 = bool(z & bit)
        if x0 != z0:
            x ^= bit
            z ^= bit
        return x, z
    if gate.name == "cx":
        c, t = gate.control, gate.target
        if (x >> c) & 1:
            x ^= 1 << t
        if (z >> t) & 1:
            z ^= 1 << c
        return x, z
    raise ValueError(f"unsupported gate: {gate.name}")


def stabilizer_generators(circuit: CircuitSpec) -> list[tuple[int, int]]:
    """Images of Z_i stabilizers of |0...0> under the ideal Clifford circuit."""
    generators = []
    for i in range(circuit.n_qubits):
        x, z = 0, 1 << i
        for gate in circuit.gates:
            x, z = _conjugate(x, z, gate)
        # With exactly one initial H and then CXs, generators are X-only or Z-only.
        assert not (x & z), "unexpected Y factor; update the sign-tracking algorithm"
        generators.append((x, z))
    return generators


def pauli_label(x: int, z: int, n_qubits: int) -> str:
    """Qiskit labels are ordered from highest to lowest qubit index."""
    label = []
    for i in reversed(range(n_qubits)):
        xi, zi = (x >> i) & 1, (z >> i) & 1
        label.append("Y" if xi and zi else "X" if xi else "Z" if zi else "I")
    return "".join(label)
