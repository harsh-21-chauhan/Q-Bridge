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
| Research assistant | Explicitly deferred; no model client, key or API calls. |

## Important interpretation rules

- Task loss is mean stabilizer-generator parity error, **not quantum state fidelity**. Accepted improvement compares initial and final placements under the same final posterior.
- “Not estimated” means the guard probability was not calculated. It must not become 0%, 50% or an invented confidence score.
- Retaining the initial placement can be correct. Seed 42 is reproducible; the interface does not manufacture a successful switch for the demo.
- EVSI is prospective expected decision benefit. Its values at a stage use beliefs **before** that stage's measurements.
- Budget alternatives preserve the simulator's measurement prefix per group, but produce different posteriors. Subtracting their displayed expected losses does not directly measure improvement. More shots need not help one particular trial.
- Benchmark harm/help rates are across all trials, not conditional on switching. Quick trials overlap the full evidence and are excluded. Scenario bootstrap intervals are not an overall significance claim.
- Simulation scenario selection controls hidden data generation. Truth is never supplied to the planner. Exported full records intentionally include separate post-hoc evaluation; future assistant tools must use evidence-only responses for decision explanations.

## Follow one button through the code

1. `src/components/ExperimentForm.jsx` keeps controls typed and validates basic input bounds. On submit it passes settings to `App.jsx`.
2. `src/App.jsx` calls `api.run()`, disables conflicting run controls and retains the previous record while waiting.
3. `src/lib/api.js` sends one JSON POST to `/api/experiments`. There are no automatic retries or background experiments.
4. `vite.config.js` proxies `/api` to local FastAPI. Python validates the request, calculates and saves the result.
5. On success, React replaces the displayed record. On failure it shows the error; old results keep their original configuration label.
6. The result components receive that record as read-only props. The circuit's local/remote classification is only for coloring, not decision-making.

`components/UI.jsx` holds small shared panels/tables; `lib/format.js` holds labels and number formatting; `index.css` defines the responsive visual system. `Calibration.jsx` contains the journey and noise chart; `Placement.jsx`, `CircuitViewer.jsx` and `Benchmarks.jsx` handle their named sections. The package lock pins the installed dependency tree. `npm run format` formats source for readability.

## A three-minute walkthrough of the current application

This is a walkthrough of the completed local simulation app, not the later Meta-integrated final demo.

| Time | Show and explain |
|---|---|
| 0:00–0:25 | “Q-Bridge chooses what to calibrate before assigning a circuit across two processors. This is a simulator with three effective error groups.” |
| 0:25–0:50 | Run the default experiment. Point to the budget, loss definition and placement decision. |
| 0:50–1:20 | Show the circuit and QPU assignments. Explain that remote operations use a different effective error group. |
| 1:20–1:50 | Select an adaptive stage. Explain EVSI and show how failures/successes update the Beta beliefs. |
| 1:50–2:15 | Show guard evidence and credible intervals. Explain that uncertainty is conditional on the model and a retained placement is valid. |
| 2:15–2:40 | Open Benchmarks, filter one scenario, and distinguish observed regret from universal superiority. |
| 2:40–3:00 | Reopen a saved run, show provenance/export, and state the simulator's limitations. The Meta assistant is still deferred. |

## Verification and remaining review

`npm test` checks typed submissions, invalid budgets, truthful null probabilities, circuit recoloring, EVSI stage selection, API errors, preservation of previous results and paired-budget settings. Python tests remain responsible for mathematical correctness. `npm run build` checks production compilation.

Implementation checks on 4 November 2026: all 11 frontend tests and 176 Python tests passed; the production build passed; npm reported zero known dependency vulnerabilities; the research evidence verifier passed. A local request through the Vite proxy created/retrieved the default experiment, and all scientific result components plus the benchmark view rendered from real API responses. The Python suite reports one existing Starlette/HTTPX deprecation warning.

Local browser automation was disabled in Work settings during implementation, so desktop/mobile visual inspection is pending. Open the dashboard on your laptop, then narrow the browser window to review the stacked layout. Automated component checks and successful compilation do not substitute for a visual check.
