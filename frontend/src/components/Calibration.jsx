import { useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Panel, DataTable } from './UI';
import { groups, names, colors, percent, scientific } from '../lib/format';
export function CalibrationTimeline({ result }) {
  const [index, setIndex] = useState(0);
  const calibration = result.calibration,
    step = calibration.trace[index];
  return (
    <Panel
      title="Calibration journey"
      subtitle="Explore all three groups, then follow the expected value of information."
    >
      <div className="timeline">
        {calibration.trace.map((s, i) => (
          <button
            key={i}
            type="button"
            aria-pressed={i === index}
            onClick={() => setIndex(i)}
            className={i === index ? 'active' : ''}
          >
            <span className="step-number">0{i + 1}</span>
            <small>{s.stage === 'pilot' ? 'Explore' : 'Adaptive EVSI'}</small>
            <strong style={{ color: colors[s.group] }}>{names[s.group]}</strong>
            <span>
              {s.shots} shots · {s.failures} failures
            </span>
            <div className="step-track">
              <i
                style={{
                  background: colors[s.group],
                  width: `${(100 * s.cumulative_shots) / calibration.total_shots}%`,
                }}
              />
            </div>
          </button>
        ))}
      </div>
      <div className="stage-detail">
        <div className="row">
          <h3>
            Stage {step.step} · {names[step.group]}
          </h3>
          <span className="badge">
            {step.cumulative_shots} / {calibration.total_shots} shots used
          </span>
        </div>
        <p>
          {step.stage === 'pilot'
            ? 'Predetermined exploration; EVSI is not calculated for this allocation.'
            : 'The group with the highest EVSI was chosen using beliefs before this batch. EVSI predicts expected placement benefit, not measured fidelity.'}
        </p>
        {step.evsi_at_choice && (
          <div className="evsi-grid">
            {groups.map((g) => (
              <div key={g} className={g === step.group ? 'chosen' : ''}>
                <small>
                  {names[g]} {g === step.group ? '· chosen' : ''}
                </small>
                <code>{scientific(step.evsi_at_choice[g])}</code>
              </div>
            ))}
          </div>
        )}
        <DataTable
          headers={[
            'Noise group',
            'Before mean',
            'After mean',
            'After Beta(α, β)',
            'Cumulative shots',
          ]}
        >
          {groups.map((g) => (
            <tr key={g}>
              <td>{names[g]}</td>
              <td>{percent(step.posteriors_before[g].mean)}</td>
              <td>{percent(step.posteriors_after[g].mean)}</td>
              <td className="mono">
                {step.posteriors_after[g].alpha}, {step.posteriors_after[g].beta}
              </td>
              <td>{step.cumulative_shots_by_group[g]}</td>
            </tr>
          ))}
        </DataTable>
      </div>
    </Panel>
  );
}
export function NoiseComparison({ result }) {
  const data = groups.map((g) => ({
    name: names[g],
    prior: result.initial_priors[g].mean * 100,
    posterior: result.final_posterior[g].mean * 100,
  }));
  return (
    <Panel
      title="What the measurements changed"
      subtitle="Prior and posterior mean error probability · lower is better"
    >
      <div
        className="chart"
        role="img"
        aria-label="Prior and posterior noise means; exact means and credible intervals are in the table below"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 12, right: 15, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#243140" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: '#a4b3c5', fontSize: 11 }} />
            <YAxis unit="%" tick={{ fill: '#a4b3c5', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#172231', border: '1px solid #3c5066', color: '#fff' }}
              formatter={(v, n) => [`${Number(v).toFixed(3)}%`, n]}
            />
            <Bar
              dataKey="prior"
              name="Prior"
              fill="#55667e"
              radius={[3, 3, 0, 0]}
              isAnimationActive={false}
            />
            <Bar
              dataKey="posterior"
              name="Posterior"
              fill="#5ee4ca"
              radius={[3, 3, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="legend">
        <span>
          <i style={{ background: '#55667e' }} />
          Prior
        </span>
        <span>
          <i style={{ background: '#5ee4ca' }} />
          Posterior
        </span>
      </div>
      <DataTable
        headers={[
          'Group',
          'Prior mean',
          'Posterior mean',
          '95% credible interval',
          'Failures / shots',
        ]}
      >
        {groups.map((g) => (
          <tr key={g}>
            <td>
              <span style={{ color: colors[g] }}>{names[g]}</span>
            </td>
            <td>{percent(result.initial_priors[g].mean)}</td>
            <td>{percent(result.final_posterior[g].mean)}</td>
            <td>
              {result.final_posterior[g].credible_interval_95.map((v) => percent(v)).join(' – ')}
            </td>
            <td>
              {result.calibration.failures_by_group[g]} / {result.calibration.shots_by_group[g]}
            </td>
          </tr>
        ))}
      </DataTable>
      <p className="caption">
        Equal-tail 95% Bayesian credible intervals describe uncertainty under the assumed model. The
        bars show means, not confidence or measured hardware truth.
      </p>
      <details>
        <summary>Inspect prior & posterior parameters</summary>
        <DataTable headers={['Group', 'Prior α, β', 'Posterior α, β']}>
          {groups.map((g) => (
            <tr key={g}>
              <td>{names[g]}</td>
              <td>
                {result.initial_priors[g].alpha}, {result.initial_priors[g].beta}
              </td>
              <td>
                {result.final_posterior[g].alpha}, {result.final_posterior[g].beta}
              </td>
            </tr>
          ))}
        </DataTable>
        <p>
          For each measured group: α increases by failures; β increases by successful shots. The
          original prior means are illustrative assumptions.
        </p>
      </details>
    </Panel>
  );
}
