# The Q-Bridge dashboard, explained

React is the display and interaction layer. FastAPI passes requests to the validated Python engine. React never recomputes Bayesian posteriors, EVSI, placement losses or the switching decision. It formats backend values and draws diagrams. Start both services using [SETUP.md](SETUP.md).

## How the interface is organized

The dark research workspace uses teal for QPU A, violet for QPU B and amber for the remote link. The first view answers “what happened?”; expandable tables answer “how and why?”. Charts always have numerical tables. Narrow layouts stack panels and let wide circuits/tables scroll horizontally.

| Area | What to inspect |
|---|---|
| Experiment setup | Circuit family, qubits, budget, scenario, seed and optional guard; threshold/draw count are advanced settings. |
| Decision summary | Final posterior expected loss, accepted expected improvement, exact shots used and whether placement changed. |
| Quantum circuit | Every H/CNOT gate in order; switch between initial/candidate/final placement colors. Expand to see gates and stabilizer labels. |
| Placement | Side-by-side initial, candidate and final assignments; local/remote CNOT counts, guard evidence and loss comparisons. |
| Calibration journey | Select each pilot/adaptive stage to see measurements, before/after beliefs and the EVSI values used for the choice. |
| Noise beliefs | Prior/posterior means, equal-tail 95% credible intervals, failures/shots and exact Beta parameters. |
| Budget exploration | Run 50/100/200 shots with the recorded seed/scenario and compare the previous and current records. |
| Simulation evaluation | Collapsed, explicitly labeled hidden truth, actual losses, oracle and regret, used only to grade the completed decision. |
| Provenance/export | Experiment ID, versions, runtime and seeds; export the complete record, including its separate evaluation section. |
| Benchmarks | All eight policies, full aggregate and 40 scenario filters, scenario-specific paired intervals and source checksum. |
| Saved experiments | Paginated local records, stable ID order, reopen a completed experiment. |
| Research guide | Plain-language explanations and model limitations. |
| Research assistant | Hosted Muse Spark explanations through scoped Python tools, with a separate local fallback. The live retrieval/explanation flow was verified. See [assistant guide](ASSISTANT_WALKTHROUGH.md). |

## Important interpretation rules

- Task loss is mean stabilizer-generator parity error, **not quantum state fidelity**. Accepted improvement compares initial and final placements under the same final posterior.
- “Not estimated” means the guard probability was not calculated. It must not become 0%, 50% or an invented confidence score.
- Retaining the initial placement can be correct. Seed 42 is reproducible; the interface does not manufacture a successful switch for the demo.
- EVSI is prospective expected decision benefit. Its values at a stage use beliefs **before** that stage's measurements.
- Budget alternatives preserve the simulator's measurement prefix per group, but produce different posteriors. Subtracting their displayed expected losses does not directly measure improvement. More shots need not help one particular trial.
- Benchmark harm/help rates are across all trials, not conditional on switching. Quick trials overlap the full evidence and are excluded. Scenario bootstrap intervals are not an overall significance claim.
- Simulation scenario selection controls hidden data generation. Truth is never supplied to the planner. Exported full records intentionally include separate post-hoc evaluation; assistant tools use evidence-only responses for decision explanations.

## Follow one button through the code

1. `src/components/ExperimentForm.jsx` keeps controls typed and validates basic input bounds. On submit it passes settings to `App.jsx`.
2. `src/App.jsx` calls `api.run()`, disables conflicting run controls and retains the previous record while waiting.
3. `src/lib/api.js` sends one JSON POST to `/api/experiments`. There are no automatic retries or background experiments.
4. `vite.config.js` proxies `/api` to local FastAPI. Python validates the request, calculates and saves the result.
5. On success, React replaces the displayed record. On failure it shows the error; old results keep their original configuration label.
6. The result components receive that record as read-only props. The circuit's local/remote classification is only for coloring, not decision-making.

`components/UI.jsx` holds small shared panels/tables; `lib/format.js` holds labels and number formatting; `index.css` defines the responsive visual system. `Calibration.jsx` contains the journey and noise chart; `Placement.jsx`, `CircuitViewer.jsx` and `Benchmarks.jsx` handle their named sections. The package lock pins the installed dependency tree. `npm run format` formats source for readability.

## Submission demo

Use the [current three-minute script and component guide](DEMO_SCRIPT.md). It includes exact default settings, verified outputs, page-by-page actions and the genuine Muse Spark interaction. It replaces the earlier pre-Meta demo narrative.

## Verification and remaining review

`npm test` checks typed submissions, invalid budgets, truthful null probabilities, circuit recoloring, EVSI stage selection, API errors, preservation of previous results and paired-budget settings. Python tests remain responsible for mathematical correctness. `npm run build` checks production compilation.

Latest local checks on 5 November 2026: all 24 frontend tests and 204 Python tests passed, and the production build passed. The Python suite reports one existing Starlette/HTTPX deprecation warning. Desktop and narrow-screen layouts have been reviewed. The experiment, benchmark, saved-run and guide pages were inspected again while preparing the demo.

A genuine Muse Spark evidence-retrieval and explanation flow was verified separately. Live model-driven budget comparison remains unverified. Automated tests use local/fake-provider paths and do not establish external service availability. See the [assistant verification record](ASSISTANT_WALKTHROUGH.md).
