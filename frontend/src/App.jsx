import ResearchAssistant from './components/ResearchAssistant';
import { useEffect, useRef, useState } from 'react';
import {
  Atom,
  FlaskConical,
  ChartNoAxesCombined,
  History,
  BookOpen,
  Download,
  ArrowUpRight,
  Sparkles,
  RefreshCw,
  ChevronRight,
} from 'lucide-react';
import ExperimentForm, { defaults } from './components/ExperimentForm';
import CircuitViewer from './components/CircuitViewer';
import Placement from './components/Placement';
import { CalibrationTimeline, NoiseComparison } from './components/Calibration';
import Benchmarks from './components/Benchmarks';
import { Panel, Metric, Note, DataTable } from './components/UI';
import { api, downloadJSON } from './lib/api';
import { percent, number, scenarios, groups, names } from './lib/format';

export default function App() {
  // Inputs and completed records are separate: only a successful API response
  // replaces the evidence shown below the form.
  const [page, setPage] = useState('experiment'),
    [config, setConfig] = useState(defaults);
  const [record, setRecord] = useState(null),
    [comparison, setComparison] = useState(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [history, setHistory] = useState(null),
    [offset, setOffset] = useState(0);
  const [historyError, setHistoryError] = useState(''),
    [historyLoading, setHistoryLoading] = useState(false);
  const [health, setHealth] = useState('checking');
  const historyRequest = useRef(0);
  const [report, setReport] = useState(null),
    [reportError, setReportError] = useState(''),
    [reportLoading, setReportLoading] = useState(false);
  async function refreshHistory(position = offset) {
    // Ignore a slower, older page request if a newer refresh has started.
    const requestId = ++historyRequest.current;
    setHistoryLoading(true);
    setHistoryError('');
    try {
      const next = await api.history(position);
      if (requestId === historyRequest.current) {
        setHistory(next);
        setOffset(position);
      }
    } catch (e) {
      if (requestId === historyRequest.current) setHistoryError(e.message);
    } finally {
      if (requestId === historyRequest.current) setHistoryLoading(false);
    }
  }
  async function checkHealth() {
    try {
      await api.health();
      setHealth('online');
    } catch {
      setHealth('offline');
    }
  }
  useEffect(() => {
    checkHealth();
    refreshHistory(0);
  }, []);
  async function loadBenchmarks() {
    setReportLoading(true);
    setReportError('');
    try {
      setReport(await api.benchmarks());
    } catch (e) {
      setReportError(e.message);
    } finally {
      setReportLoading(false);
    }
  }
  async function navigate(next) {
    setPage(next);
    if (next === 'benchmarks' && !report && !reportLoading) loadBenchmarks();
  }
  async function openRun(id) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const saved = await api.get(id);
      setRecord(saved);
      setConfig(saved.configuration);
      setComparison(null);
      setPage('experiment');
      setNotice('Saved experiment loaded. Results below reflect this recorded configuration.');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function run(next, compare = false) {
    setBusy(true);
    setError('');
    setNotice('');
    // Keep the displayed record unchanged until the server succeeds. A failed
    // request must not relabel old results with the new input controls.
    const previous = record;
    try {
      const saved = await api.run(next);
      setRecord(saved);
      setConfig(saved.configuration);
      setComparison(compare ? previous : null);
      setHealth('online');
      setNotice('Calibration complete. The experiment is saved locally.');
      refreshHistory(0);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const result = record?.result;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate('experiment');
          }}
        >
          <span className="brand-symbol">
            <Atom size={27} />
          </span>
          <span className="brand-copy">
            <strong>Q-Bridge</strong>
            <small>Research workspace</small>
          </span>
        </a>
        <div className="workspace-label">Research tools</div>
        <nav aria-label="Main navigation">
          {[
            ['experiment', FlaskConical, 'Experiment'],
            ['benchmarks', ChartNoAxesCombined, 'Benchmarks'],
            ['history', History, 'Saved experiments'],
            ['guide', BookOpen, 'Research guide'],
            ['assistant', Sparkles, 'Research assistant'],
          ].map(([key, Icon, label]) => (
            <button
              key={key}
              className={page === key ? 'active' : ''}
              aria-current={page === key ? 'page' : undefined}
              onClick={() => navigate(key)}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <p>
            Adaptive calibration
            <br />
            with AI research support
          </p>
          <span className="badge">Placement guard</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Research <ChevronRight size={13} />
            <span>
              {
                {
                  experiment: 'Experiment',
                  benchmarks: 'Benchmarks',
                  history: 'Saved experiments',
                  guide: 'Research guide',
                  assistant: 'Research assistant',
                }[page]
              }
            </span>
          </div>
          <div className="top-actions">
            <span className="simulation-badge">SIMULATED DATA</span>
            <button className="connection" onClick={checkHealth} title="Check backend connection">
              <i className={`dot ${health}`} />
              {health === 'online'
                ? 'Backend connected'
                : health === 'checking'
                  ? 'Connecting…'
                  : 'Backend offline'}
              <RefreshCw size={12} />
            </button>
          </div>
        </header>
        <main id="main-content">
          {error && (
            <div className="error" role="alert">
              {error}
              <button onClick={() => setError('')}>Dismiss</button>
            </div>
          )}
          {page === 'experiment' && (
            <>
              <div className="page-intro">
                <div>
                  <span className="eyebrow">Bayesian calibration</span>
                  <h1>
                    Measure with purpose.
                    <br className="mobile-break" /> Place with evidence.
                  </h1>
                </div>
              </div>
              <ExperimentForm config={config} setConfig={setConfig} busy={busy} onRun={run} />
              <div role="status" aria-live="polite" className="status-line">
                {busy ? 'Calculating with the validated Python engine…' : notice}
              </div>
              {!record ? (
                <Panel title="Your next decision starts here" className="empty-state">
                  <div className="empty-visual">
                    <span className="qpu-chip">A</span>
                    <i />
                    <Atom size={28} />
                    <i />
                    <span className="qpu-chip purple">B</span>
                  </div>
                  <p>
                    Run a calibration to see the circuit, measurement journey and placement
                    recommendation.
                  </p>
                  <small>No example measurements are presented as live results.</small>
                  {history?.experiments.length > 0 && (
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() => openRun(history.experiments[0].experiment_id)}
                    >
                      Open a saved experiment <ArrowUpRight size={15} />
                    </button>
                  )}
                </Panel>
              ) : (
                <>
                  <div className="result-heading">
                    <div>
                      <span className="eyebrow">Recorded result</span>
                      <h2>
                        {record.configuration.family.toUpperCase()} · {record.configuration.qubits}{' '}
                        qubits · {record.configuration.shots} shots
                      </h2>
                      <p>
                        {scenarios[record.configuration.truth_mode]} · seed{' '}
                        {record.configuration.seed} ·{' '}
                        {record.configuration.guard_enabled
                          ? `${percent(record.configuration.guard_threshold, 0)} guard`
                          : 'Unguarded'}
                      </p>
                    </div>
                    <button onClick={() => downloadJSON(record)}>
                      <Download size={16} />
                      Export full JSON
                    </button>
                  </div>
                  <div className="metrics">
                    <Metric
                      label="Final expected task loss"
                      value={number(result.loss.final_under_posterior)}
                      note="Parity-error probability · final posterior"
                      accent="teal"
                    />
                    <Metric
                      label="Accepted expected improvement"
                      value={number(result.loss.accepted_expected_improvement)}
                      note="Initial minus final · same posterior"
                    />
                    <Metric
                      label="Measurement budget"
                      value={`${result.calibration.total_shots} / ${record.configuration.shots}`}
                      note="Exact shot accounting"
                    />
                    <Metric
                      label="Placement decision"
                      value={result.decision.switched ? 'Updated' : 'Retained'}
                      note={`${result.circuit.placement_count} equal-capacity candidates`}
                      accent="teal"
                    />
                  </div>
                  <Note>
                    <strong>
                      {result.decision.switched
                        ? 'The evidence supports a placement change.'
                        : 'The initial placement was retained.'}
                    </strong>{' '}
                    {result.decision.reason}. Task loss measures stabilizer parity error. It is not
                    full quantum state fidelity.
                  </Note>
                  <CircuitViewer key={record.experiment_id} result={result} />
                  <Placement result={result} />
                  <CalibrationTimeline key={`trace-${record.experiment_id}`} result={result} />
                  <NoiseComparison result={result} />
                  <Panel
                    title="Explore the budget"
                    subtitle="Same seed and scenario; each group's measurement prefix is preserved."
                  >
                    <div className="row wrap">
                      <p>Run a paired budget alternative. The original record stays saved.</p>
                      <div className="button-group">
                        {[50, 100, 200].map((shots) => (
                          <button
                            key={shots}
                            disabled={busy || shots === record.configuration.shots}
                            onClick={() => run({ ...record.configuration, shots }, true)}
                          >
                            {shots} shots <ArrowUpRight size={14} />
                          </button>
                        ))}
                      </div>
                    </div>
                    {comparison && (
                      <>
                        <DataTable
                          headers={[
                            'Recorded run',
                            'Budget',
                            'Expected loss',
                            'Accepted improvement',
                            'Decision',
                          ]}
                        >
                          {[comparison, record].map((r, i) => (
                            <tr key={i}>
                              <td>{i === 0 ? 'Previous' : 'Current'}</td>
                              <td>{r.configuration.shots}</td>
                              <td>{number(r.result.loss.final_under_posterior)}</td>
                              <td>{number(r.result.loss.accepted_expected_improvement)}</td>
                              <td>{r.result.decision.status}</td>
                            </tr>
                          ))}
                        </DataTable>
                        <Note>
                          Each run has a different posterior. Differences between these expected
                          losses are not a direct measure of decision improvement. More shots need
                          not improve every individual result.
                        </Note>
                      </>
                    )}
                  </Panel>
                  <section className="panel evaluation">
                    <details>
                      <summary>
                        Simulation evaluation{' '}
                        <span className="badge amber">Hidden truth · post-decision only</span>
                      </summary>
                      <p>
                        The following information was used to generate measurements and grade the
                        completed decision. It was not available to the placement planner.
                      </p>
                      <DataTable headers={['Parameter', 'Simulator truth']}>
                        {groups.map((g) => (
                          <tr key={g}>
                            <td>{names[g]}</td>
                            <td>{percent(record.evaluation.true_error_rates[g])}</td>
                          </tr>
                        ))}
                      </DataTable>
                      <DataTable headers={['Evaluation metric', 'Value']}>
                        {[
                          'initial_actual_loss',
                          'candidate_actual_loss',
                          'final_actual_loss',
                          'oracle_loss',
                          'regret',
                          'actual_improvement',
                        ].map((k) => (
                          <tr key={k}>
                            <td>{k.replaceAll('_', ' ')}</td>
                            <td>{number(record.evaluation[k])}</td>
                          </tr>
                        ))}
                      </DataTable>
                      <p>
                        Oracle assignment:{' '}
                        <code>{record.evaluation.oracle_placement.assignment.join('')}</code>.
                        Regret is final actual loss minus oracle loss; neither is full state
                        fidelity.
                      </p>
                    </details>
                  </section>
                  <section className="panel">
                    <details>
                      <summary>Reproducibility & provenance</summary>
                      <p>
                        Experiment ID: <code className="break">{record.experiment_id}</code>
                      </p>
                      <p>
                        Algorithm: {record.metadata.algorithm_version} · schema{' '}
                        {record.metadata.schema_version}
                      </p>
                      <p>
                        Seed scheme: <code>{record.metadata.seed_scheme}</code> · guard seed:{' '}
                        {result.guard_seed}
                      </p>
                      <pre>{JSON.stringify(record.metadata.runtime, null, 2)}</pre>
                      <p>
                        Identical settings and runtime reproduce this record. Historical M2C used a
                        different simulator seed sequence; equivalence is tested on identical
                        measurements and posterior draws.
                      </p>
                    </details>
                  </section>
                </>
              )}
            </>
          )}
          {page === 'benchmarks' && (
            <Benchmarks
              report={report}
              error={reportError}
              loading={reportLoading}
              reload={loadBenchmarks}
            />
          )}
          {page === 'history' && (
            <>
              <div className="page-intro">
                <div>
                  <span className="eyebrow">Local experiment library</span>
                  <h1>Return to the evidence.</h1>
                  <p>
                    Saved JSON records, ordered by ID. Repeated identical runs share one record.
                  </p>
                </div>
              </div>
              <Panel
                title="Saved experiments"
                action={
                  <button disabled={historyLoading} onClick={() => refreshHistory()}>
                    <RefreshCw size={15} />
                    Refresh
                  </button>
                }
              >
                {historyError && (
                  <p role="alert" className="error">
                    {historyError}
                  </p>
                )}
                {historyLoading && <p role="status">Loading history…</p>}
                {history && (
                  <>
                    <DataTable
                      headers={['Experiment', 'Circuit', 'Budget', 'Scenario', 'Decision', '']}
                    >
                      {history.experiments.map((r) => (
                        <tr key={r.experiment_id}>
                          <td>
                            <code title={r.experiment_id}>{r.experiment_id.slice(0, 15)}…</code>
                          </td>
                          <td>
                            {r.configuration.family} · {r.configuration.qubits}q
                          </td>
                          <td>{r.configuration.shots}</td>
                          <td>{scenarios[r.configuration.truth_mode]}</td>
                          <td>{r.status}</td>
                          <td>
                            <button disabled={busy} onClick={() => openRun(r.experiment_id)}>
                              Open <ArrowUpRight size={14} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </DataTable>
                    {history.total === 0 && (
                      <p>No saved experiments yet. Run a calibration to create one.</p>
                    )}
                    <div className="row">
                      <span>{history.total} saved experiments</span>
                      <div className="button-group">
                        <button
                          disabled={historyLoading || offset === 0}
                          onClick={() => refreshHistory(Math.max(0, offset - 10))}
                        >
                          Previous
                        </button>
                        <button
                          disabled={historyLoading || history.next_offset == null}
                          onClick={() => refreshHistory(history.next_offset)}
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </Panel>
            </>
          )}
          {page === 'guide' && (
            <>
              <div className="page-intro">
                <div>
                  <span className="eyebrow">A guide to the experiment</span>
                  <h1>Understand the decision.</h1>
                  <p>The interface explains the evidence. Python performs the science.</p>
                </div>
              </div>
              <div className="guide-grid">
                {[
                  [
                    '01',
                    'Circuit & placement',
                    'A circuit is a sequence of H and CNOT gates. Each qubit is assigned to A or B, with exactly half on each processor. We enumerate 20 placements at 6 qubits and 924 at 12.',
                  ],
                  [
                    '02',
                    'Calibration & priors',
                    'Each shot is a binary diagnostic measurement. Illustrative Beta priors begin at mean error rates of 2%, 3% and 5%. Observed failures update alpha; successes update beta.',
                  ],
                  [
                    '03',
                    'Adaptive EVSI',
                    'Expected value of sample information predicts how useful measuring each error group will be for the placement decision. It is not a prediction of physical fidelity.',
                  ],
                  [
                    '04',
                    'The switching guard',
                    'The candidate minimizes posterior expected loss. The 60% guard accepts a change only when expected improvement is positive and sampled posterior support meets the threshold.',
                  ],
                  [
                    '05',
                    'Read null correctly',
                    '“Not estimated” means no switch probability was calculated. It is not zero confidence or 50% evidence. An unchanged placement can be the right recommendation.',
                  ],
                  [
                    '06',
                    'Loss & uncertainty',
                    'Task loss is mean stabilizer-generator parity error, not state fidelity. Credible intervals express uncertainty under the assumed Bayesian model.',
                  ],
                ].map(([n, title, text]) => (
                  <Panel key={n} title={title} action={<span className="eyebrow">{n}</span>}>
                    <p>{text}</p>
                  </Panel>
                ))}
              </div>
              <Panel title="What this simulation does not claim">
                <ul className="readable-list">
                  <li>
                    No physical QPU connection, teleportation protocol, Bell-pair generation or
                    network timing model.
                  </li>
                  <li>
                    Only three independent, static effective Pauli-error groups. No readout error,
                    coherent noise, drift or correlations.
                  </li>
                  <li>
                    Small deterministic Clifford circuits; exact placement is bounded to 12 qubits.
                  </li>
                  <li>
                    The guard can still make a confidently wrong choice if the prior or likelihood
                    is wrong.
                  </li>
                  <li>
                    Benchmark outcomes are simulated. The quick subset is not independent
                    replication.
                  </li>
                </ul>
              </Panel>
            </>
          )}
          {page === 'assistant' && <ResearchAssistant record={record} />}
          <footer>
            <span>Q-BRIDGE / SIMULATION RESEARCH</span>
            <span>Observable evidence. Reproducible decisions.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
