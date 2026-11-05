import { useEffect, useState } from 'react';
import { Sparkles, Send, Pause, Play, Settings2, FileText, RefreshCw } from 'lucide-react';
import AssistantEvidence from './AssistantEvidence';
import { Panel, Note } from './UI';
import { request } from '../lib/api';

const prompts = [
  'Why was this placement selected?',
  'Which calibration measurements were most useful, and why?',
  'What uncertainty and limitations should I report?',
];

export default function ResearchAssistant({ record }) {
  const [status, setStatus] = useState(null);
  const [question, setQuestion] = useState(prompts[0]);
  const [budget, setBudget] = useState('');
  const [answer, setAnswer] = useState(null);
  const [local, setLocal] = useState(null);
  const [busy, setBusy] = useState(false);
  const [localBusy, setLocalBusy] = useState(false);
  const [controlBusy, setControlBusy] = useState(false);
  const [error, setError] = useState('');
  const [localError, setLocalError] = useState('');

  async function refresh() {
    setStatus(await request('/assistant/status'));
  }
  useEffect(() => {
    let active = true;
    // Status is local and free. A backend restart must not leave a stale
    // disabled button on screen; these checks never submit a model request.
    const check = () =>
      request('/assistant/status')
        .then((value) => {
          if (active) setStatus(value);
        })
        .catch(() => {
          if (active) setStatus(null);
        });
    check();
    window.addEventListener('focus', check);
    const timer = window.setInterval(check, 15000);
    return () => {
      active = false;
      window.removeEventListener('focus', check);
      window.clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    setAnswer(null);
    setLocal(null);
    setError('');
    setLocalError('');
  }, [record?.experiment_id]);

  const ready =
    status?.mode === 'live' &&
    status.live_authorized &&
    status.credential_configured &&
    !status.disabled;
  const stateLabel = !status
    ? 'Checking connection'
    : status.disabled
      ? 'Paused'
      : ready
        ? 'Live enabled'
        : 'Live not enabled';

  async function ask(event) {
    event.preventDefault();
    if (!ready) return;
    setBusy(true);
    setError('');
    setAnswer(null);
    try {
      const response = await request('/assistant/ask', {
        experiment_id: record.experiment_id,
        question,
        compare_shots: budget ? Number(budget) : null,
      });
      // Never label a mock response as Muse Spark if server settings changed.
      if (response.mode !== 'live')
        throw new Error('The server is not in live mode. Use the local explanation below.');
      setAnswer({ ...response, question });
      setStatus(response.usage);
    } catch (e) {
      setError(e.message);
      try {
        await refresh();
      } catch {
        /* Preserve the original request error. */
      }
    } finally {
      setBusy(false);
    }
  }
  async function control() {
    setControlBusy(true);
    setError('');
    try {
      setStatus(await request(status.disabled ? '/assistant/resume' : '/assistant/disable', {}));
    } catch (e) {
      setError(e.message);
    } finally {
      setControlBusy(false);
    }
  }
  async function explainLocally() {
    setLocalBusy(true);
    setLocalError('');
    try {
      setLocal(await request('/assistant/explain', { experiment_id: record.experiment_id }));
    } catch (e) {
      setLocalError(e.message);
    } finally {
      setLocalBusy(false);
    }
  }

  return (
    <>
      <div className="page-intro assistant-intro">
        <div>
          <span className="eyebrow">Q-Bridge × Meta</span>
          <h1>
            <Sparkles size={28} /> Muse Spark research assistant
          </h1>
          <p>
            Understand your placement, explore calibration choices, and compare measurement budgets.
          </p>
        </div>
        <div className="assistant-controls">
          <span className="badge">{stateLabel}</span>
          <button
            className="icon-button"
            onClick={control}
            disabled={!status || controlBusy || (status.disabled && busy)}
            aria-label={status?.disabled ? 'Resume assistant' : 'Pause model requests'}
            title={
              status?.disabled ? 'Resume assistant — keeps all limits' : 'Pause model requests'
            }
          >
            {status?.disabled ? <Play size={17} /> : <Pause size={17} />}
          </button>
        </div>
      </div>
      {status?.disabled && (
        <Note>
          Model requests are paused. Use the play icon to resume; your budget and authorization
          settings stay unchanged. An already-sent request may still finish.
        </Note>
      )}
      {error && (
        <div className="error" role="alert">
          {error} You can use the local explanation at the bottom without a model request.
        </div>
      )}
      {!record ? (
        <Panel title="Select an experiment first">
          <p>Run a calibration or open a saved experiment, then return here.</p>
        </Panel>
      ) : (
        <Panel
          title="Explore this experiment"
          subtitle={`${record.configuration?.family?.toUpperCase() || 'Saved experiment'} · ${record.configuration?.qubits || '—'} qubits · ${record.configuration?.shots || '—'} shots`}
        >
          <p className="caption break">Evidence source: {record.experiment_id}</p>
          <form onSubmit={ask}>
            <fieldset disabled={busy}>
              <div className="assistant-prompts">
                {prompts.map((p) => (
                  <button type="button" key={p} onClick={() => setQuestion(p)}>
                    {p}
                  </button>
                ))}
              </div>
              <label>
                Your research question
                <textarea
                  required
                  maxLength={1500}
                  rows={4}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
              </label>
              <div className="assistant-submit">
                <label>
                  Budget comparison
                  <select value={budget} onChange={(e) => setBudget(e.target.value)}>
                    <option value="">Explain this experiment</option>
                    {[50, 100, 200].map((n) => (
                      <option key={n} value={n}>
                        Compare with {n} shots
                      </option>
                    ))}
                  </select>
                </label>
                <button type="submit" className="primary" disabled={!ready || busy}>
                  <Send size={16} />
                  {busy ? 'Reviewing the evidence…' : 'Ask Muse Spark'}
                </button>
              </div>
              <p className="caption">
                {budget
                  ? 'This request also runs and saves one Python simulation using the recorded seed and scenario.'
                  : 'Answers are grounded in recorded Python evidence.'}{' '}
                {!ready && 'Live access is not enabled. Check Connection & usage below.'}
              </p>
            </fieldset>
          </form>
        </Panel>
      )}
      {answer && (
        <Panel
          title="Muse Spark’s analysis"
          subtitle={answer.question}
          action={<Sparkles size={20} />}
        >
          <div className="assistant-answer">
            {answer.answer
              .split(/\n\s*\n/)
              .filter(Boolean)
              .map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))}
          </div>
          <p className="caption">
            AI explanation · verify against the scientific evidence below. Python computes all
            decisions.
          </p>
          {answer.trace.map((step, i) => (
            <AssistantEvidence key={i} step={step} />
          ))}
        </Panel>
      )}
      <section className="panel assistant-utilities">
        <details>
          <summary>
            <Settings2 size={15} /> Connection & usage
          </summary>
          {status && (
            <>
              <p>
                Model: {status.model || 'muse-spark-1.3'} · Backend key:{' '}
                {status.credential_configured ? 'configured' : 'not configured'} · Live permission:{' '}
                {status.live_authorized ? 'enabled' : 'off'} · Server mode: {status.mode}
              </p>
              <p>
                Reported tokens: {status.input_tokens ?? 0} input / {status.output_tokens ?? 0}{' '}
                output · Usage estimate: ${(status.reported_usage_estimate_usd ?? 0).toFixed(4)}
              </p>
              <p>
                Reserved application allowance: ${status.reserved_usd.toFixed(2)} / $
                {status.budget_usd.toFixed(2)} · {status.provider_calls} model requests.
              </p>
              <p className="caption">
                The dollar allowance is a cost control, not a token count or your Meta credit
                balance. Estimates may omit missing usage. Limits remain enforced by the backend;
                they cannot guarantee zero card charges. Resume does not reset usage or enable live
                permission.
              </p>
              {status.server_disabled && (
                <p>
                  The server disable switch is on. Set QBRIDGE_ASSISTANT_DISABLED=false in the
                  backend terminal and restart before resuming.
                </p>
              )}
            </>
          )}
          <button onClick={() => refresh().catch((e) => setError(e.message))}>
            <RefreshCw size={14} />
            Refresh status
          </button>
        </details>
        <details>
          <summary>
            <FileText size={15} /> Model unavailable? Read a local explanation
          </summary>
          <p>
            A brief explanation from recorded Python results. This is not a Muse Spark response and
            makes no model call. It remains available while model requests are paused.
          </p>
          <button disabled={!record || localBusy} onClick={explainLocally}>
            {localBusy ? 'Reading evidence…' : 'Explain placement locally'}
          </button>
          {!record && <p className="caption">Select an experiment first.</p>}
          {localError && <p role="alert">{localError}</p>}
          {local && (
            <div className="assistant-answer">
              <h3>Local explanation · Python evidence</h3>
              <p>{local.answer}</p>
              <details>
                <summary>Inspect supporting evidence</summary>
                {local.trace.map((step, i) => (
                  <AssistantEvidence key={i} step={step} />
                ))}
              </details>
            </div>
          )}
        </details>
      </section>
    </>
  );
}
