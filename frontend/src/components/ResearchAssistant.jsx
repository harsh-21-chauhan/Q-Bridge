import AssistantEvidence from './AssistantEvidence';
import { useEffect, useState } from 'react';
import { Panel, Note } from './UI';
import { request } from '../lib/api';

export default function ResearchAssistant({ record }) {
  const [status, setStatus] = useState(null);
  const [question, setQuestion] = useState(
    'Why was this placement selected? Explain the calibration choices.',
  );
  const [budget, setBudget] = useState('');
  const [answer, setAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    request('/assistant/status')
      .then(setStatus)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    setAnswer(null);
  }, [record?.experiment_id]);
  async function ask(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setAnswer(null);
    try {
      const response = await request('/assistant/ask', {
        experiment_id: record.experiment_id,
        question,
        compare_shots: budget ? Number(budget) : null,
      });
      setAnswer(response);
      setStatus(response.usage);
    } catch (e) {
      setError(e.message);
      try {
        setStatus(await request('/assistant/status'));
      } catch {
        /* Keep original error. */
      }
    } finally {
      setBusy(false);
    }
  }
  async function disable() {
    try {
      setStatus(await request('/assistant/disable', {}));
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <>
      <div className="page-intro">
        <div>
          <span className="eyebrow">Evidence-grounded explanations</span>
          <h1>Your research assistant.</h1>
          <p>Python computes. The assistant explains. Every answer exposes its tool evidence.</p>
        </div>
      </div>
      <Panel
        title={
          status?.mode === 'live' ? 'Muse Spark · live mode' : 'Mock assistant · no model calls'
        }
      >
        <Note>
          {status?.mode === 'live'
            ? 'Live answers use Muse Spark and may consume API credits. Check the Python evidence below each answer.'
            : 'Mock answers are deterministic walkthroughs, not AI-generated responses to your question. Local scientific tools still run; no model calls are made.'}
        </Note>
        {status && (
          <p>
            Reserved application budget: ${status.reserved_usd.toFixed(2)} / $
            {status.budget_usd.toFixed(2)} · {status.provider_calls} provider requests. Reservations
            are conservative allowances, not your Meta bill or remaining credits.
          </p>
        )}
        {status && (
          <p className="caption">
            Backend key: {status.credential_configured ? 'configured' : 'not configured'} · Live
            permission: {status.live_authorized ? 'enabled' : 'off'} · Reported usage estimate: $
            {(status.reported_usage_estimate_usd ?? 0).toFixed(4)}. This is not a billing balance;
            missing usage may be excluded.
          </p>
        )}
        <button onClick={disable} disabled={status?.disabled}>
          Emergency stop{status?.disabled ? ' · disabled' : ''}
        </button>
        <p className="caption">
          Stops subsequent requests, including the next model step. It cannot cancel a request
          already sent. Re-enabling requires a local administrator.
        </p>
      </Panel>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!record ? (
        <Panel title="Select an experiment first">
          <p>Run a calibration or open a saved experiment, then return here.</p>
        </Panel>
      ) : (
        <Panel title="Ask about the selected experiment" subtitle={record.experiment_id}>
          <form onSubmit={ask}>
            <fieldset
              disabled={
                busy ||
                !status ||
                status.disabled ||
                (status.mode === 'live' &&
                  (!status.live_authorized || !status.credential_configured))
              }
            >
              <label>
                Your question
                <textarea
                  required
                  maxLength={1500}
                  rows={4}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
              </label>
              <label>
                Optional what-if calculation
                <select value={budget} onChange={(e) => setBudget(e.target.value)}>
                  <option value="">Explain existing evidence only</option>
                  {[50, 100, 200].map((n) => (
                    <option key={n} value={n}>
                      Compare with {n} shots
                    </option>
                  ))}
                </select>
              </label>
              <p className="caption">
                Selecting a budget authorizes one local Python simulation with the saved
                seed/scenario. It is saved in experiment history.
              </p>
              <button type="submit" className="primary">
                {busy
                  ? 'Working…'
                  : status?.mode === 'live'
                    ? 'Ask Muse Spark'
                    : 'Run mock walkthrough'}
              </button>
            </fieldset>
          </form>
        </Panel>
      )}
      {answer && (
        <Panel title={answer.mode === 'mock' ? 'Mock walkthrough' : 'Muse Spark explanation'}>
          <p style={{ whiteSpace: 'pre-wrap' }}>{answer.answer}</p>
          <Note>
            Model explanations can be mistaken. Check the evidence; mathematical decisions remain in
            Python.
          </Note>
          {answer.trace.map((step, i) => (
            <AssistantEvidence key={i} step={step} />
          ))}
        </Panel>
      )}
    </>
  );
}
