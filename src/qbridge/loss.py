"""Exact stabilizer-generator parity loss for the selected Pauli-noise model.

After each CX, with group-specific probability p, apply X(target) or
Z(control), each with probability p/2. Otherwise apply identity.
This is an effective gate channel, NOT a full remote teleportation protocol.
"""
from dataclasses import dataclass
from functools import cached_property
import numpy as np
from .circuits import CircuitSpec, _conjugate, placements, stabilizer_generators

GROUPS = ("local_a", "local_b", "remote")


@dataclass(frozen=True)
class PlacementModel:
    circuit: CircuitSpec

    @cached_property
    def mappings(self) -> tuple[tuple[int, ...], ...]:
        # Do not enumerate placements for large circuits: this is intentionally
        # bounded to the exact small-circuit reference experiment.
        if self.circuit.n_qubits > 12:
            raise ValueError("exhaustive placement benchmark limited to <=12 qubits")
        return tuple(placements(self.circuit.n_qubits))

    @cached_property
    def counts(self) -> np.ndarray:
        """Shape (placements, stabilizers, groups, two attenuation types).

        A Pauli generator picks up (1-p) if one of X(target)/Z(control)
        anticommutes; (1-2p) if both anticommute.
        """
        result = np.zeros((len(self.mappings), self.circuit.n_qubits, 3, 2), dtype=np.int16)
        generators = stabilizer_generators(self.circuit)
        for j, mapping in enumerate(self.mappings):
            for i, (x0, z0) in enumerate(generators):
                x, z = x0, z0
                for gate in reversed(self.circuit.gates):
                    if gate.name == "cx":
                        c, t = gate.control, gate.target
                        group = 2 if mapping[c] != mapping[t] else mapping[c]
                        # Compare with the Pauli at the output of the gate;
                        # the stochastic channel is applied after CX.
                        anti_x_target = (z >> t) & 1
                        anti_z_control = (x >> c) & 1
                        anticommuting = anti_x_target + anti_z_control
                        if anticommuting:
                            result[j, i, group, anticommuting - 1] += 1
                    x, z = _conjugate(x, z, gate)
        return result

    def losses(self, parameters: tuple[float, float, float]) -> np.ndarray:
        """Expected probability of incorrect generator parity, per placement."""
        p = np.asarray(parameters, dtype=float)
        if p.shape != (3,) or np.any((p < 0) | (p > 1)):
            raise ValueError("provide three channel error probabilities in [0,1]")
        factors = np.ones(self.counts.shape[:2], dtype=float)
        for g in range(3):
            factor1 = (1.0 - p[g]) ** self.counts[:, :, g, 0]
            factor2 = (1.0 - 2.0 * p[g]) ** self.counts[:, :, g, 1]
            factors *= factor1 * factor2
        return ((1.0 - factors) / 2.0).mean(axis=1)

    def best_placement(self, parameters: tuple[float, float, float]) -> tuple[int, float]:
        values = self.losses(parameters)
        idx = int(np.argmin(values))
        return idx, float(values[idx])
