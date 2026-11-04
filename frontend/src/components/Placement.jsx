import { Panel, DataTable } from './UI';
import { percent, number } from '../lib/format';
export default function Placement({ result }) {
  const { placements, decision, loss } = result;
  return (
    <Panel
      title="From evidence to placement"
      subtitle="A balanced allocation across two labeled processors."
    >
      <div className="placement-grid">
        {['initial', 'candidate', 'final'].map((key) => (
          <div className={`placement ${key === 'final' ? 'selected' : ''}`} key={key}>
            <div className="row">
              <h3>
                {key === 'initial'
                  ? '01 · Initial'
                  : key === 'candidate'
                    ? '02 · Candidate'
                    : '03 · Final decision'}
              </h3>
              {key === 'final' && <span className="badge">Selected</span>}
            </div>
            {['a', 'b'].map((qpu) => (
              <div className={`qpu ${qpu}`} key={qpu}>
                <span>QPU {qpu.toUpperCase()}</span>
                <div>
                  {placements[key][`qpu_${qpu}`].map((q) => (
                    <b key={q}>q{q}</b>
                  ))}
                </div>
              </div>
            ))}
            <p className="caption">
              {placements[key].cx_counts.remote} remote · {placements[key].cx_counts.local_a} local
              A · {placements[key].cx_counts.local_b} local B CNOTs
            </p>
            <code>Mapping: {placements[key].assignment.join('')}</code>
          </div>
        ))}
      </div>
      <div className="decision-box">
        <span className="eyebrow">
          {decision.guard_enabled ? 'Posterior guard' : 'Expected-loss mode'}
        </span>
        <h3>{decision.switched ? 'Placement updated' : 'Initial placement retained'}</h3>
        <p>{decision.reason}.</p>
        <div className="decision-values">
          <span>
            Probability candidate is better{' '}
            <strong>{percent(decision.posterior_probability_better)}</strong>
          </span>
          <span>
            Acceptance threshold{' '}
            <strong>
              {decision.guard_enabled ? percent(decision.guard_threshold, 0) : 'Guard disabled'}
            </strong>
          </span>
          <span>
            Posterior draws used <strong>{decision.posterior_draws_used}</strong>
          </span>
        </div>
        <small>
          {decision.probability_interpretation}. This is model-based uncertainty, not a hardware
          guarantee.
        </small>
      </div>
      <details>
        <summary>Expected-loss comparison & decision details</summary>
        <DataTable headers={['Placement', 'Expected task loss', 'Belief used']}>
          {['initial', 'candidate', 'final'].map((key) => (
            <tr key={key}>
              <td>{key}</td>
              <td className="mono">{number(loss[`${key}_under_posterior`])}</td>
              <td>Same final posterior</td>
            </tr>
          ))}
        </DataTable>
        <p>
          Candidate expected improvement: <code>{number(loss.candidate_expected_improvement)}</code>
          . Accepted improvement: <code>{number(loss.accepted_expected_improvement)}</code>.
        </p>
        <p>
          Initial expected loss under the original prior:{' '}
          <code>{number(loss.initial_under_prior)}</code>. Do not subtract this from a posterior
          loss to claim a placement benefit. Assignment 0 = A, 1 = B. Status:{' '}
          <code>{decision.status}</code>.
        </p>
      </details>
    </Panel>
  );
}
