import { useState } from 'react';
import { Panel, DataTable } from './UI';
import { colors, names } from '../lib/format';
export default function CircuitViewer({ result }) {
  const [view, setView] = useState('final');
  const circuit = result.circuit;
  const assignment = result.placements[view].assignment;
  const width = Math.max(700, circuit.gates.length * 40 + 90),
    height = circuit.qubits * 35 + 36;
  // This classification only colors the diagram. All loss calculations and
  // placement choices come from Python, never from this visualization.
  const group = (gate) =>
    gate.name === 'h'
      ? null
      : assignment[gate.control] !== assignment[gate.target]
        ? 'remote'
        : assignment[gate.control] === 0
          ? 'local_a'
          : 'local_b';
  return (
    <Panel
      title="Quantum circuit"
      subtitle={`${circuit.family.toUpperCase()} · ${circuit.qubits} logical qubits · ${circuit.cx_count} CNOT gates`}
      action={
        <select
          aria-label="Circuit placement view"
          value={view}
          onChange={(e) => setView(e.target.value)}
        >
          {['initial', 'candidate', 'final'].map((v) => (
            <option key={v} value={v}>
              {v} placement
            </option>
          ))}
        </select>
      }
    >
      <div className="legend">
        {Object.entries(colors).map(([g, c]) => (
          <span key={g}>
            <i style={{ background: c }} />
            {names[g]}
          </span>
        ))}
      </div>
      <div className="circuit-scroll">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ minWidth: width }}
          role="img"
          aria-label={`${circuit.family} circuit. Gate colors use the ${view} placement. Full gate list follows.`}
        >
          {assignment.map((label, q) => (
            <g key={q}>
              <text x="10" y={30 + q * 35} fill={label === 0 ? colors.local_a : colors.local_b}>
                q{q}
              </text>
              <line x1="45" x2={width - 10} y1={25 + q * 35} y2={25 + q * 35} stroke="#2d3c4d" />
            </g>
          ))}
          {circuit.gates.map((gate, i) => {
            const x = 70 + i * 40,
              y = 25 + gate.control * 35,
              target = 25 + gate.target * 35,
              color = colors[group(gate)] || '#afbdcd';
            return (
              <g key={i}>
                <title>
                  {gate.name === 'h'
                    ? `H on q${gate.control}`
                    : `CNOT q${gate.control} → q${gate.target}, ${names[group(gate)]}`}
                </title>
                {gate.name === 'h' ? (
                  <>
                    <rect
                      x={x - 11}
                      y={y - 11}
                      width="22"
                      height="22"
                      rx="3"
                      fill="#253341"
                      stroke={color}
                    />
                    <text x={x} y={y + 4} textAnchor="middle" fill="#e6eef7">
                      H
                    </text>
                  </>
                ) : (
                  <>
                    <line x1={x} x2={x} y1={y} y2={target} stroke={color} />
                    <circle cx={x} cy={y} r="4" fill={color} />
                    <circle cx={x} cy={target} r="9" stroke={color} fill="#101823" />
                    <path
                      d={`M ${x - 6} ${target} h 12 M ${x} ${target - 6} v 12`}
                      stroke={color}
                    />
                  </>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <p className="caption">
        Left → right is gate order, not execution time. Lines are logical wires; colors describe
        local or remote CNOTs under the selected placement.
      </p>
      <details>
        <summary>Gate list & stabilizer observables</summary>
        <DataTable headers={['#', 'Gate', 'Logical qubits', 'Operation group']}>
          {circuit.gates.map((g, i) => (
            <tr key={i}>
              <td>{i + 1}</td>
              <td>{g.name.toUpperCase()}</td>
              <td>{g.name === 'h' ? `q${g.control}` : `q${g.control} → q${g.target}`}</td>
              <td>{group(g) ? names[group(g)] : 'Single-qubit · ideal'}</td>
            </tr>
          ))}
        </DataTable>
        <p>Generator labels use highest qubit index on the left (Qiskit convention).</p>
        <div className="stabilizers">
          {circuit.stabilizers.map((s, i) => (
            <code key={i}>
              S{i}: {s}
            </code>
          ))}
        </div>
      </details>
    </Panel>
  );
}
