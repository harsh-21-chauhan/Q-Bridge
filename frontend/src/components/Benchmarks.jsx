import { useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import { Panel, Metric, Note, DataTable } from './UI';
import { policyNames, scenarios, percent, number } from '../lib/format';
export default function Benchmarks({ report, error, loading, reload }) {
  const [selection, setSelection] = useState('all');
  if (!report)
    return (
      <Panel title="Research benchmarks">
        <p>
          {loading ? 'Loading verified evidence…' : error || 'Benchmark evidence has not loaded.'}
        </p>
        <button onClick={reload} disabled={loading}>
          Reload benchmarks
        </button>
      </Panel>
    );
  const scenario = selection === 'all' ? null : report.scenarios[Number(selection)];
  const policies = scenario ? scenario.policies : report.policies;
  const chart = [...policies]
    .sort((a, b) => a.mean_regret - b.mean_regret)
    .map((p) => ({ ...p, label: policyNames[p.policy], scaled: p.mean_regret * 1000 }));
  return (
    <>
      <div className="page-intro">
        <div>
          <span className="eyebrow">Research evidence</span>
          <h1>Every decision has a trade-off.</h1>
          <p>Compare calibration policies across controlled, simulated conditions.</p>
        </div>
      </div>
      <div className="metrics metrics-three">
        <Metric
          label="Configurations"
          value={report.configuration_count}
          note="Three circuit families · 6 & 12 qubits"
        />
        <Metric
          label="Trial/configuration pairs"
          value={report.trial_configuration_count.toLocaleString()}
          note="100 trials per configuration. Environments are shared."
        />
        <Metric
          label="Policy outcomes"
          value={report.policy_outcome_count.toLocaleString()}
          note="Eight policies per trial"
        />
      </div>
      <Panel
        title="Policy comparison"
        subtitle={scenario ? 'One configuration · 100 paired trials' : report.aggregation}
        action={
          <label className="filter-label">
            Scenario
            <select
              aria-label="Benchmark scenario"
              value={selection}
              onChange={(e) => setSelection(e.target.value)}
            >
              <option value="all">All 40 configurations</option>
              {report.scenarios.map((s, i) => (
                <option key={i} value={i}>
                  {s.family} {s.qubits}q · {scenarios[s.truth_mode]} · {s.shots} shots
                </option>
              ))}
            </select>
          </label>
        }
      >
        <p className="caption">
          Regret is the gap between the selected placement and the best placement under simulator
          truth. Lower is better. Values are multiplied by 1,000 for readability.
        </p>
        <div
          className="benchmark-chart"
          role="img"
          aria-label="Policy regret comparison, with all exact values in the table below"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={chart}
              margin={{ left: 0, right: 35, top: 10, bottom: 10 }}
            >
              <CartesianGrid stroke="#243140" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#a4b3c5', fontSize: 12 }} />
              <YAxis
                type="category"
                dataKey="label"
                width={192}
                tick={{ fill: '#bdcad8', fontSize: 11 }}
              />
              <Tooltip
                formatter={(v) => [Number(v).toFixed(4), 'Mean regret × 1,000']}
                contentStyle={{ background: '#172231', border: '1px solid #3c5066' }}
              />
              <Bar dataKey="scaled" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                {chart.map((p) => (
                  <Cell
                    key={p.policy}
                    fill={p.policy === 'adaptive_original_guard60' ? '#5ee4ca' : '#667b98'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <DataTable headers={['Policy', 'Regret × 1,000', 'Task loss', 'Harm', 'Help', 'Switch']}>
          {chart.map((p) => (
            <tr
              key={p.policy}
              className={p.policy === 'adaptive_original_guard60' ? 'highlight' : ''}
            >
              <td>{policyNames[p.policy]}</td>
              <td>{(p.mean_regret * 1000).toFixed(4)}</td>
              <td>{number(p.mean_task_loss)}</td>
              <td>{percent(p.harm_rate)}</td>
              <td>{percent(p.help_rate)}</td>
              <td>{percent(p.switch_rate)}</td>
            </tr>
          ))}
        </DataTable>
        <Note>
          The 60% guard had the lowest observed overall mean regret, but its small advantage over
          unguarded adaptive EVSI is not established as universal. A guard can reject helpful
          switches as well as harmful ones.
        </Note>
        {scenario && (
          <details>
            <summary>Paired comparison intervals for this scenario</summary>
            <p>
              A positive reduction means the 60% guard had lower regret than the comparison policy.
              If the interval includes zero, the difference is inconclusive. Each interval applies
              only to this scenario. No adjustment was made for testing multiple comparisons.
            </p>
            <DataTable headers={['Comparator', 'Mean reduction', 'Paired 95% interval']}>
              {policies
                .filter((p) => p.paired_ci_95)
                .map((p) => (
                  <tr key={p.policy}>
                    <td>{policyNames[p.policy]}</td>
                    <td>{number(p.regret_reduction_vs_guard60)}</td>
                    <td>{p.paired_ci_95.map(number).join(' to ')}</td>
                  </tr>
                ))}
            </DataTable>
          </details>
        )}
      </Panel>
      <Panel title="Read the evidence responsibly">
        <ul className="readable-list">
          {report.metric_notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        <details>
          <summary>Source & integrity</summary>
          <code className="break">{report.source}</code>
          <p>
            SHA-256: <code className="break">{report.source_sha256}</code>
          </p>
        </details>
      </Panel>
    </>
  );
}
