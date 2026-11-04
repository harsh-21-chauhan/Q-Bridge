import { DataTable, Metric, Note } from './UI';
import { groups, names, number, percent, scientific } from '../lib/format';

// These cards render backend values directly. Model prose never supplies metrics.
function EvidenceRun({ data, title }) {
  return (
    <section className="assistant-evidence">
      <h3>
        {title} · {data.shots} shots
      </h3>
      <p className="caption break">Source: {data.experiment_id}</p>
      <div className="metrics">
        <Metric
          label="Placement"
          value={data.decision.switched ? 'Updated' : 'Retained'}
          note={data.decision.status}
        />
        <Metric
          label="Expected task loss"
          value={number(data.loss.final_under_posterior)}
          note="Stabilizer parity error, not fidelity"
        />
        <Metric
          label="Accepted improvement"
          value={number(data.loss.accepted_expected_improvement)}
          note="Same final posterior"
        />
        <Metric
          label="Switch probability"
          value={percent(data.decision.posterior_probability_better)}
          note="Not estimated means no calculation"
        />
      </div>
      <p>{data.decision.reason}</p>
      <details>
        <summary>Noise estimates and uncertainty</summary>
        <DataTable headers={['Noise group', 'Posterior mean', '95% credible interval']}>
          {groups.map((g) => (
            <tr key={g}>
              <td>{names[g]}</td>
              <td>{percent(data.posterior[g].mean)}</td>
              <td>{data.posterior[g].credible_interval_95.map((v) => percent(v)).join(' – ')}</td>
            </tr>
          ))}
        </DataTable>
      </details>
      <details>
        <summary>Calibration choices and EVSI</summary>
        <DataTable
          headers={[
            'Stage',
            'Measured group',
            'Shots',
            'Failures',
            'EVSI · A',
            'EVSI · B',
            'EVSI · link',
          ]}
        >
          {data.stages.map((s) => (
            <tr key={s.step}>
              <td>
                {s.step} · {s.stage}
              </td>
              <td>{names[s.group]}</td>
              <td>{s.shots}</td>
              <td>{s.failures}</td>
              {groups.map((g) => (
                <td key={g}>{scientific(s.evsi_at_choice?.[g])}</td>
              ))}
            </tr>
          ))}
        </DataTable>
        <p className="caption">
          Pilot allocations are predetermined. Adaptive EVSI uses beliefs before the selected batch.
        </p>
      </details>
      <details>
        <summary>QPU assignments</summary>
        <DataTable headers={['Placement', 'QPU A', 'QPU B', 'Remote CNOTs']}>
          {['initial', 'candidate', 'final'].map((p) => (
            <tr key={p}>
              <td>{p}</td>
              <td>{data.placements[p].qpu_a.map((q) => `q${q}`).join(', ')}</td>
              <td>{data.placements[p].qpu_b.map((q) => `q${q}`).join(', ')}</td>
              <td>{data.placements[p].cx_counts.remote}</td>
            </tr>
          ))}
        </DataTable>
      </details>
    </section>
  );
}
export default function AssistantEvidence({ step }) {
  const data = step.evidence;
  return (
    <>
      {step.tool === 'compare_budget' ? (
        <>
          <Note>{data.interpretation}</Note>
          <EvidenceRun data={data.previous} title="Original experiment" />
          <EvidenceRun data={data.current} title="Budget alternative" />
        </>
      ) : (
        <EvidenceRun data={data} title="Recorded evidence" />
      )}
      <details>
        <summary>Technical tool record · {step.tool}</summary>
        <pre>{JSON.stringify(data, null, 2)}</pre>
      </details>
    </>
  );
}
