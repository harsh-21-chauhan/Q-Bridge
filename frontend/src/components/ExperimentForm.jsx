import { Play, SlidersHorizontal } from 'lucide-react';
import { Panel } from './UI';
import { scenarios } from '../lib/format';
export const defaults = {
  family: 'layered',
  qubits: 6,
  shots: 100,
  seed: 42,
  truth_mode: 'shifted',
  guard_enabled: true,
  guard_threshold: 0.6,
  guard_draws: 512,
};
export default function ExperimentForm({ config, setConfig, busy, onRun }) {
  const update = (key, value) => setConfig((previous) => ({ ...previous, [key]: value }));
  return (
    <Panel
      title="Experiment setup"
      subtitle="Define the circuit. Set your measurement budget."
      action={<SlidersHorizontal size={18} />}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onRun(config);
        }}
      >
        <fieldset disabled={busy}>
          <div className="form-grid">
            <label>
              Circuit family
              <select value={config.family} onChange={(e) => update('family', e.target.value)}>
                <option value="layered">Layered Clifford</option>
                <option value="ghz">GHZ chain</option>
                <option value="star">Star + interactions</option>
              </select>
            </label>
            <label>
              Logical qubits
              <select
                value={config.qubits}
                onChange={(e) => update('qubits', Number(e.target.value))}
              >
                <option value={6}>6 qubits · 20 placements</option>
                <option value={12}>12 qubits · 924 placements</option>
              </select>
            </label>
            <label>
              Calibration budget
              <input
                required
                type="number"
                min="20"
                max="1000"
                step="1"
                value={config.shots}
                onChange={(e) =>
                  update('shots', e.target.value === '' ? '' : Number(e.target.value))
                }
              />
              <small>20–1,000 total shots across three groups</small>
            </label>
            <label>
              Simulation scenario
              <select
                value={config.truth_mode}
                onChange={(e) => update('truth_mode', e.target.value)}
              >
                {Object.entries(scenarios).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
              <small>Synthetic conditions, not observed evidence</small>
            </label>
            <label>
              Reproducibility seed
              <input
                required
                type="number"
                min="0"
                max="4294967295"
                step="1"
                value={config.seed}
                onChange={(e) =>
                  update('seed', e.target.value === '' ? '' : Number(e.target.value))
                }
              />
            </label>
            <div className="guard-control">
              <label className="check">
                <input
                  type="checkbox"
                  checked={config.guard_enabled}
                  onChange={(e) => update('guard_enabled', e.target.checked)}
                />
                Placement guard
              </label>
              <small>
                {config.guard_enabled
                  ? 'Require posterior support before switching'
                  : 'Use minimum posterior expected loss'}
              </small>
            </div>
          </div>
          <details className="advanced">
            <summary>Advanced decision settings</summary>
            <div className="form-grid">
              <label>
                Probability threshold
                <input
                  required
                  type="number"
                  min="0.5"
                  max="1"
                  step="0.01"
                  disabled={!config.guard_enabled}
                  value={config.guard_threshold}
                  onChange={(e) =>
                    update('guard_threshold', e.target.value === '' ? '' : Number(e.target.value))
                  }
                />
              </label>
              <label>
                Posterior draws
                <input
                  required
                  type="number"
                  min="64"
                  max="16384"
                  step="1"
                  disabled={!config.guard_enabled}
                  value={config.guard_draws}
                  onChange={(e) =>
                    update('guard_draws', e.target.value === '' ? '' : Number(e.target.value))
                  }
                />
              </label>
            </div>
            <p>
              The validated default is 60% with 512 draws. A custom threshold is a research
              preference, not a new validated optimum.
            </p>
          </details>
          <div className="form-footer">
            <span>
              <i className="dot" /> Adaptive EVSI · original Beta priors
            </span>
            <button className="primary" type="submit">
              <Play size={15} />
              {busy ? 'Running calibration…' : 'Run calibration'}
            </button>
          </div>
        </fieldset>
      </form>
    </Panel>
  );
}
