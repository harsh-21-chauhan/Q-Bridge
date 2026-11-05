# Q-Bridge demo: recording script and component guide

Prepared for the three-minute submission video on 5 November 2026. Read only the quoted narration in the timed script during recording. Actions and reference notes are for preparation.

## Organizer requirements and submission status

The organizer replies supplied by the project owner require: a video of **3:00 or less**, understandable in English, **no slides**, and the working product on screen. Show only features, code and functionality built during the hackathon. State where Meta models are used in both the video and README. On-screen model credits and a code walkthrough are not required. The first spoken line must disclose what existed before kickoff and what was built during the event.

The [official event page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) lists Indie-track judging priorities as creativity, technical ambition and whether it works. It lists the submission deadline as 4 November at 9:00 PM ET, which is **5 November 2026 at 7:30 AM IST**. That time has passed. The supplied organizer reply says no edits are allowed afterward. A replacement video or README push after the deadline is not proof that judges will accept the change.

Once the video exists, test it in a signed-out private window, including audio and duration. If the existing submission remains editable under an authorized extension, replace its link and save. Otherwise, request an organizer-approved correction with the submission identifier and new link. Do not create a duplicate submission or assume late acceptance. The supplied example about missing audio is someone else's situation unless the project owner confirms the same issue.

## Research origin and verified scope

The owner identifies NS-QPEFT as earlier research that motivated Q-Bridge. The local NS-QPEFT history includes July/August 2026 commits, before the announced 26 October kickoff. Q-Bridge's recorded commits begin on 1 November, with its scientific interface, dashboard and Meta integration developed afterward. Commit history supports the sequence but is not a claim that every idea originated during the event.

**Earlier work:** NS-QPEFT explores prediction of simulated quantum-circuit behavior using circuit and link features in a PyTorch model. Its architecture includes two encoders, feature fusion, residual blocks, a Bell-conditioned adapter and a seven-output prediction head. Its stored summary records 4,095 samples, mean MAE 0.010447, RMSE 0.018884 and R² 0.783236 across five seeds. Attribution accuracy is recorded as 59.39%. These are stored simulation results, not measurements independently reproduced during this review. No publication or peer-review status is claimed.

**Q-Bridge:** a separate Bayesian decision-support workflow for allocating measurements and selecting balanced circuit placements. The local application/scientific code and dependencies do not import NS-QPEFT or PyTorch. Its contribution builds on the research question, not the earlier trained model. Do not say Q-Bridge improves that network or compare its regret against NS-QPEFT prediction metrics.

The useful narrative is **earlier prediction research → uncertainty about what to measure → limited-budget placement decisions → adaptive calibration and guarded switching → inspectable results with Meta explanations**. Keep NS-QPEFT attribution spoken while the Q-Bridge dashboard is visible. Do not spend video time showing the older repository, training plots or code.

The current Experiment, Benchmarks, Saved experiments and Research guide pages were inspected in the running app, and the default experiment was executed. Browser access became disabled before the assistant inspection finished. Its controls were checked against current code and the previously verified live response. A subsequent local API check confirmed a healthy backend, the saved demo result and live assistant configuration. No new Meta call or research experiment was needed for this background review.

Sources reviewed:

- [NS-QPEFT repository](https://github.com/harsh-21-chauhan/NS-QPEFT) (`improve/ns_qpeft.py`), dataset summary, five-seed metrics and attribution files in the local NS-QPEFT checkout. The web fetch was unavailable, so this verification used the local repository.
- [Q-Bridge final method decision](QBridge-M2C-final-decision.md), [robustness diagnostics](M2_DIAGNOSTICS.md), scientific implementation, current React assistant and [live verification record](ASSISTANT_WALKTHROUGH.md).

## Before recording

1. Keep the frontend and backend running. If they are already working, do not start duplicate servers.
2. Open the dashboard in a full-width browser window. Keep text readable and close unrelated tabs. Hide terminals and credentials from the recording.
3. Use the exact settings below. The expected numbers in this guide apply to these settings and the current runtime, not arbitrary experiments.
4. Check **Research assistant → Connection & usage** before recording. Live permission must be enabled, the backend key configured, the server in live mode, and the assistant unpaused. Leave enough application allowance for two provider calls: currently $0.50 of reservation per completed two-call question. This reservation is not the actual token cost or a Meta credit balance. Do not clear the ledger.
5. Return to Experiment for the start of the recording. Rehearse the scrolling and narration without submitting paid questions repeatedly.
6. Use a screen recording of the actual product throughout. Do not add title slides or presentation slides.
7. Record one genuine Muse Spark request in the final segment. If editing out a long wait, label that edit “Response wait shortened.” Do not substitute a local explanation while calling it a live Meta answer.

If the services need starting, use two VS Code terminals:

```bash
# Terminal 1
cd /Users/harshchauhan/Desktop/Q-Bridge
conda activate qbridge
python -m backend.run --live
```

```bash
# Terminal 2
cd /Users/harshchauhan/Desktop/Q-Bridge/frontend
npm run dev
```

Open <http://127.0.0.1:5173>. Enter a requested API key privately in Terminal 1 before recording. Starting the server makes no model call.

| Control | Demo setting |
|---|---|
| Circuit family | Layered Clifford |
| Logical qubits | 6 qubits · 20 placements |
| Calibration budget | 100 |
| Simulation scenario | Local + link shift |
| Reproducibility seed | 42 |
| Placement guard | Enabled |
| Advanced settings | Keep defaults: threshold 0.60, 512 posterior draws |

## Read-aloud script: approximately three minutes

Aim for a calm 135–145 words per minute. The timings are recording/editing targets, not a promise of API response speed. Rehearse once with a timer. If a real model response takes too long, shorten only the waiting period transparently if edits are permitted. Keep the final export under 3:00, including any introductory silence.

### 0:00–0:33 — Earlier research, new question and hackathon contribution

**Show:** Q-Bridge's Experiment page and setup throughout. Do not show NS-QPEFT code or slides. The first sentence is the required pre-event disclosure.

> “Before this hackathon, I studied quantum noise through NS-QPEFT. During the event, I built Q-Bridge’s calibration workflow, dashboard and Meta Muse Spark assistant.”
>
> “Our earlier work explored predicting noisy circuit behavior. But prediction does not tell us what to measure next. With only one hundred measurements, should we investigate processor A, processor B, or their connecting link? Q-Bridge chooses measurements by their expected value for the placement decision.”

### 0:33–0:50 — Execute a reproducible experiment

**Do:** Point to Layered Clifford, 6 qubits, 100 shots, Local + link shift, seed 42 and the enabled guard. Click **Run calibration** once and scroll to the result cards.

> “This is a simulated six-qubit circuit with one hundred calibration shots and a fixed seed. Python updates the noise estimates and evaluates twenty balanced placements. The guard requires evidence before accepting a change.”

### 0:50–1:08 — Explain the outcome and placement

**Do:** Show the result cards, then scroll through **Quantum circuit** and **From evidence to placement**. Point to local/remote colors and the equal initial/candidate/final mappings.

> “All shots were used. Expected task loss is about zero-point-zero-seven-five, measuring stabilizer parity error, not quantum state fidelity. The candidate matches the original placement, so it is retained. The circuit and processor mappings show exactly what that decision means.”

### 1:08–1:31 — Show adaptivity and the research discovery

**Do:** In **Calibration journey**, click **04 Adaptive EVSI · Local · QPU A**. Point to the EVSI values, then scroll to **What the measurements changed**.

> “Our early experiments showed that inaccurate prior beliefs could make calibration trigger harmful placement changes. The final method first explores each noise group, then updates its beliefs between adaptive batches. Here, both batches target processor A. These intervals show what remains uncertain.”

**Understand, but do not add to the spoken script:** This example did not change placement. The general research finding comes from the benchmark and diagnostics, not this single run. The remote link has the highest posterior mean, but A has the highest estimated decision value at the chosen stages.

### 1:31–1:47 — Show the scientific findings

**Do:** Click **Benchmarks**, keep **All 40 configurations**, and show the policy table. Point to the Harm column for Adaptive unguarded and Adaptive 60% guard.

> “Across forty configurations, the sixty-percent guard reduced observed harmful switches from about seven-point-four to four-point-five percent compared with unguarded adaptive calibration. That is a useful trade-off, not evidence that the guard always performs better.”

### 1:47–1:58 — Saved records and explanations

**Do:** Click **Saved experiments**, then **Research guide**. Point briefly to the saved 100-shot layered record and the limitations section. Do not open a different experiment.

> “Saved experiments preserve the evidence. The research guide explains the method and its limits, including simplified noise and no physical hardware connection.”

### 1:58–2:43 — Execute Muse Spark and inspect its tool result

**Do:** Click **Research assistant**. Confirm **LAYERED · 6 qubits · 100 shots** and **Live enabled**. Leave **Budget comparison → Explain this experiment**. Use the suggested **Why was this placement selected?** question and click **Ask Muse Spark** once.

**Say while it loads:**

> “Now I’m asking Meta’s Muse Spark why this placement was selected. It calls a validated FastAPI tool to retrieve the recorded experiment. Python owns the Bayesian calculations and placement decision. Muse Spark turns that evidence into a research explanation.”

**After success:** Show **Muse Spark’s analysis**, the **Recorded evidence · 100 shots** cards, and briefly expand **Technical tool record · get_experiment_evidence**. Collapse raw JSON before closing. Check the returned content before describing it.

> “The answer sits beside the actual Python results. We can inspect the measurements, uncertainty and function-call evidence. The model explains the computation rather than inventing the numerical result.”

Do not leave this page or refresh after receiving the answer: assistant conversations are not persisted across page changes. The experiment itself remains saved. Keep Connection & usage and the local fallback collapsed in the short demo. Their purpose is covered in the reference table below.

### 2:43–2:58 — Close on the contribution

**Show:** The completed model answer and evidence cards together.

> “Q-Bridge advances our research from predicting noise toward deciding which measurements are worth making. It combines adaptive calibration, transparent placement decisions and Meta-powered explanations in a working simulation research prototype.”

## Understand each component before recording

These are reference notes, not extra narration to squeeze into three minutes. The important execution is real: **Run calibration**, **select an adaptive stage**, and **Ask Muse Spark**. The rest demonstrates why the output is useful and trustworthy.

### Experiment page

| Component | Simple meaning and what to say if asked |
|---|---|
| Circuit family | A different pattern of quantum operations. The prototype supports layered, GHZ and star circuits. |
| Logical qubits | Wires that must be divided evenly between A and B. Six qubits have 20 balanced assignments. Twelve have 924. |
| Calibration budget | The total number of diagnostic measurements. A shot returns a binary success/failure observation. It is not an API token budget. |
| Simulation scenario | Chooses the hidden synthetic conditions that generate observations. The planner never receives those hidden rates. |
| Seed | Reproduces the simulation’s random choices under the same settings/runtime. It does not make a generative model’s wording deterministic. |
| Placement guard | A proposed switch needs positive expected improvement and sufficient posterior support. A 60% threshold is a rule, not a guaranteed success rate. |
| Advanced settings | The threshold and posterior sampling count. The default 512 draws are only used when a qualifying candidate switch needs assessment. This demo uses zero guard draws because the candidate equals the incumbent. |
| Expected task loss | Model-averaged stabilizer parity error under the updated beliefs. Lower is better. It is not full-state fidelity, hardware accuracy or benchmark regret. |
| Accepted expected improvement | Initial loss minus final loss under the same final posterior. Zero here means the accepted placement did not change. |
| Measurement budget | Confirms all 100 permitted shots are accounted for. |
| Placement decision | “Retained” is meaningful. Do not say the guard rejected a worse candidate in this run: there was no different candidate to evaluate. |
| Quantum circuit | H and CNOT gates in order. Colors show operations on A, on B or across the link. Horizontal spacing is not hardware execution time. The dropdown changes which placement supplies the colors. |
| Gate list and stabilizers | Full operation details and the observables used to define the loss. Keep collapsed for the short recording. |
| Initial / candidate / final | Initial is selected from prior beliefs. Candidate minimizes updated expected loss. Final is the accepted outcome after the decision rules. They coincide in this run. |
| Calibration journey | Three exploratory allocations, then two adaptive batches. Click a stage to see the observations and before/after beliefs. EVSI uses the beliefs from before the chosen batch. |
| Posterior chart and table | Updated error estimates plus 95% credible intervals under the assumed Bayesian model. The bars show means, not confidence scores. |
| Explore the budget | Runs and saves a paired Python alternative. Different budgets produce different posteriors, so subtracting their expected losses is not a direct improvement measure. More shots need not help a particular trial. |
| Simulation evaluation | Hidden truth, actual loss, oracle and regret grade the completed decision. They are excluded from the planner and assistant evidence tools. Keep this collapsed in the main demo. |
| Reproducibility / export | Settings, seeds, versions and complete JSON for inspection. The full export deliberately includes the separately labeled simulator evaluation. |

### Exact default-run facts

Use these to understand the result, not to read a long list of decimals aloud:

| Result | Observed value |
|---|---|
| Final expected task loss | 0.075165, approximately 7.52% parity-error probability |
| Accepted expected improvement | 0.000000 |
| Budget used | 100 / 100 shots |
| Placement | Retained |
| Switch probability | Not estimated, not 0% and not 60% |
| QPU A | q0, q2, q3 |
| QPU B | q1, q4, q5 |
| CNOT operations | 10 total: 3 local A, 2 local B, 5 remote |
| Pilot measurements | A: 10 shots / 0 failures; B: 10 / 0; link: 20 / 3 |
| Adaptive measurements | A: 30 shots / 1 failure, then A: 30 / 0 |
| Final allocation | A: 70 shots; B: 10; link: 20 |
| A posterior | 1.76% mean, 0.37%–4.21% credible interval |
| B posterior | 2.73% mean, 0.57%–6.47% credible interval |
| Link posterior | 7.00% mean, 2.89%–12.73% credible interval |

The useful insight is that the link has the highest estimated error, but A receives the adaptive measurements. **Q-Bridge asks which measurement could improve the placement decision, not merely which group looks noisiest.** This does not prove that A was the best choice under hidden truth or that this one experiment improved placement.

### Benchmarks page

- **Counts:** 40 configurations, 100 trials per configuration and eight policies produce 4,000 trial/configuration pairs and 32,000 policy outcomes. Some environments are shared, so do not call these 32,000 independent experiments.
- **Regret:** the selected placement’s loss minus the best possible placement’s loss under simulator truth. Lower is better. The chart multiplies regret by 1,000 for readability.
- **Task loss:** simulator-evaluated loss in the benchmark table. Unlike the individual experiment’s posterior expected loss, this is retrospective grading.
- **Harm / help / switch:** fractions of all trials, not just trials that switched. The selected guard’s harm rate is 4.45% across all trials.
- **Scenario filter:** restricts the comparison to one circuit, size, scenario and budget. Any paired uncertainty interval belongs to that scenario, not an overall significance claim.
- **Source & integrity:** identifies the preserved benchmark summary and checksum. These charts read existing evidence and do not launch thousands of new experiments when opened.

### Saved experiments and Research guide

Saved runs are ordered by stable identifier, not most-recent-first. Repeated identical settings/runtime share a record. For the demo’s 100-shot layered run, the identifier starts `qb_4d088...`; use it privately to locate the row, not in spoken narration. Opening a different run changes the assistant’s selected experiment.

The Research guide covers circuit placement, priors, EVSI, the guard, missing probabilities and loss. Its limitations are part of the scientific explanation: this prototype uses small circuits and three static independent error groups. The broader motivation is adaptive calibration, but this implementation does not model every kind of quantum hardware noise.

### Research assistant page

| Component | Meaning / action |
|---|---|
| Live enabled badge | Configuration is ready. It is not proof that the next request will succeed. |
| Pause / play icon | Pauses subsequent model requests or resumes them without clearing spending limits. Do not toggle during the recorded question. |
| Explore this experiment | Shows the currently selected circuit, qubits and budget. Check this before submitting. |
| Suggested questions | Fill the text field. Only pressing Ask Muse Spark submits a request. |
| Budget selector | “Explain this experiment” retrieves existing evidence. A comparison selection authorizes one additional Python experiment, whose data can be interpreted by the model. |
| Ask Muse Spark | Starts genuine hosted-model tool calling. At most two provider calls in one workflow: tool selection, then final explanation. |
| Muse Spark’s analysis | Model text, requested in short Decision / Evidence / Uncertainty sections. The exact wording can vary. |
| Recorded evidence cards | Python-derived placement, expected loss, accepted improvement and switch probability. Model prose cannot overwrite them. |
| Noise estimates and uncertainty | Exact backend means and credible intervals. |
| Calibration choices and EVSI | Measurements and the prospective values used at each adaptive choice. |
| QPU assignments | Initial, candidate and final mappings with remote CNOT counts. |
| Technical tool record | The actual returned evidence and function name. This is the clearest inspectable demonstration of tool use. |
| Connection & usage | Readiness, model name, reported token counts, estimated usage and reserved application allowance. Never describe this as the Meta credit balance. |
| Local explanation | A separate Python fallback, not a Muse Spark answer. It remains available while model requests are paused. |

Keep the final demo to the verified retrieval/explanation path. The live model-driven budget comparison has not been verified and should not become a last-minute dependency. If you later demonstrate it successfully, say that different posterior losses are not directly comparable improvements.

## What to emphasize for reviewers

The [official event page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) names three Indie-track priorities. No numerical weights were shown. The following are our presentation choices for addressing them:

- **Creativity:** connect limited calibration measurements to placement decisions, then make the evidence explorable through a model-backed research interface.
- **Technical ambition:** demonstrate EVSI, Bayesian uncertainty, the placement guard and genuine Meta function calling. Attribute only event-built work as your hackathon contribution.
- **Whether it works:** show an actual calibration completing and a genuine model answer with its returned tool evidence.

Supporting evidence to show:

| Priority | Evidence to show |
|---|---|
| Clear problem and value | Limited measurements, uncertain noise and an inspectable placement decision. |
| Technical contribution | Adaptive EVSI, Bayesian updates and the placement guard. Explain the decision relevance of measurements. |
| Meaningful Meta integration | Submit a real question, show the completed answer and `get_experiment_evidence` tool record. |
| Working implementation | A real Python run, saved results, connected React/FastAPI interface and functioning assistant. |
| Research credibility | Benchmark trade-offs, uncertainty, reproducibility and explicit simulator limitations. |
| Usability | Clear answer sections, meaningful metrics and expandable evidence instead of a raw JSON-only experience. |

Do not claim real hardware validation, state-fidelity improvement, universal benchmark superiority, zero billing risk, autonomous laboratory control or a verified live comparison that has not been tested. No such claim is needed to make the existing project valuable.

## Recording and failure handling

- Keep the pointer still while speaking. Scroll one section at a time and pause on each result before moving on.
- Do not read every number, dropdown option or raw JSON field. A component-by-component deep dive belongs in a longer walkthrough, not a three-minute submission.
- The model may take longer than the slot allows. Record the real request and response, then shorten only the wait if editing is allowed. Never describe an edited wait as instantaneous performance.
- If a model request fails, do not repeatedly retry. Read the displayed error and check Connection & usage. A local fallback can be demonstrated honestly, but does not establish live Meta success.
- If the assistant answer disagrees with a metric, trust the Python evidence and investigate before recording the claim.
- After recording, watch the full video once for readable text, audible narration, a visible completed model answer and absence of credentials. Check that it is at most 3:00 and plays with audio while signed out. Follow the organizer-approved correction route if submission editing is locked.

## Repository handoff

The README now describes the research origin, event-built Q-Bridge workflow, current startup, meaningful Meta integration, research evidence and verification boundaries. This document replaces the outdated pre-Meta demo narrative in the dashboard walkthrough. No application code changes or additional paid calls were needed for this documentation task.

Review and commit these documentation files explicitly, rather than using `git add .`. A post-deadline push may not be part of the judged submission:

```bash
git diff -- README.md docs/FRONTEND_WALKTHROUGH.md
git add README.md docs/DEMO_SCRIPT.md docs/FRONTEND_WALKTHROUGH.md
git commit -m "docs: prepare hackathon README and demo walkthrough"
git push
```

The new script is untracked until added, so open it directly during review. Confirm that the current branch and remote are the intended submission destination before pushing. Add the real video URL to the README once it is available.
