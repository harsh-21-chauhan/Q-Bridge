# Q-Bridge Milestone 2B — Adaptive + Robust Bayesian Calibration

## What this milestone does

**Research question:** Can we make calibration-driven placement decisions less fragile when our starting error estimates are wrong, without hurting decisions when the estimates are correct?

The original `bayes.py`, `experiment.py`, `benchmark.py`, `loss.py`, and M2A diagnostics remain unchanged. The implementation is a research extension rather than a claimed fix.

Our simulated QPUs have three error parameters: errors for local two-qubit gates on processor A, local two-qubit gates on processor B, and distributed/remote gates. Every calibration shot is a binary diagnostic measurement of one parameter. The hidden truth is used **only** to create the measurement outcomes and evaluate final regret. No real quantum hardware is accessed.

## What each NEW file does

| File | Role | Why this file exists |
|---|---|---|
| `src/qbridge/robust_priors.py` | `BetaMixture` Bayesian priors | Some of our initial hardware estimates might be stale; this provides a *testable* fallback to broader uncertainty. It updates both the parameter estimate and our trust in its original calibration. |
| `src/qbridge/adaptive_calibration.py` | `MixturePlanner`, `run_sequential` | First measure A/B/link, then use updated EVSI for two later calibration decisions. Every shot is accounted for. |
| `src/qbridge/robust_decision.py` | `guarded_placement` | Check whether a proposed switch has sufficient posterior evidence; otherwise retain the original placement. It may be too conservative, so we benchmark it. |
| `src/qbridge/robustness_benchmark.py` | policy comparison and CSV/JSON | Uses paired simulated environments so we can see exactly which additional component helps. |
| `src/qbridge/m2b_demo.py` | One readable experiment | Prints the calibration choices and what was learned at each step, before showing simulator-only grading. |
| `tests/test_m2b.py` | nine focused tests | Checks Bayesian consistency, stream consumption, exact budget accounting and reproducibility. |
| `scripts/run_m2b_suite.sh` | six controlled scenarios | Generates reproducible experiment files without manual repetition. |
| `scripts/summarize_m2b.py` | readable scorecard | Consolidates the results for analysis. |

## The complete workflow, in ordinary language

1. We start with a quantum circuit and several placements. Each placement has a different mix of local and remote gates.
2. We have rough estimates of how often A, B and the quantum link make errors. The robust-prior method also allows for the possibility that those estimates are outdated.
3. If the budget is 100 shots, we initially spend 10 on A, 10 on B and 20 on the link. These proportions are experimental settings, not proven optimal.
4. From these **simulated measurement counts**, the program updates our three Bayesian error estimates.
5. Of the 60 remaining shots, it chooses the most decision-useful experiment using EVSI, spends 30 shots, updates, and repeats for the last 30.
6. It calculates expected task loss for each placement and picks the best one. The optional risk guard checks whether switching away from the original placement is sufficiently supported by our *updated* beliefs.
7. **Only after the decision** does the benchmark reveal simulator-hidden truth to compute actual loss and regret. Every method gets the same shot budget, except the explicitly labeled no-calibration reference.

## Which methods we compare

- `original_evsi`: Original single choice; full budget on one parameter (M1).
- `random_calibration`: Full budget on one randomly chosen parameter.
- `fixed_split`: Half budget on original EVSI choice; half on the link (or local B if EVSI chose link).
- `adaptive_original_priors`: Exploratory calibration and later EVSI choices; **original** priors. Isolates the effect of sequential allocation.
- `adaptive_robust_priors`: Same algorithm with broad-tail mixture priors. Isolates effect of prior flexibility.
- `adaptive_robust_guard`: Same exact measurements/posterior as previous, with guard. Isolates the effect of the final placement risk rule.
- `no_calibration`: Zero-shot reference; **not** an equal-shot calibration baseline.

Note that adding experimental stages cannot guarantee better results. The 75% guard threshold is a hypothesis, not a statistically calibrated real-world safety threshold. A confident wrong posterior can still cause bad decisions.

## Code installation (Mac / Conda)

1. In Terminal, `cd` into your cloned `Q-Bridge` repository and run `conda activate qbridge`.
2. Extract the ZIP **into that repo root**:

   ```bash
   unzip -o ~/Downloads/QBridge-M2B-Adaptive-Calibration.zip -d .
   ```

3. Run all tests:

   ```bash
   python -m pytest -q
   ```

   If you installed M2A and Qiskit Aer, you should see **34 tests pass**. (M1 22 + M2A 3 + M2B 9 = 34.)

4. Run a SINGLE example first to understand the complete flow:

   ```bash
   python -m qbridge.m2b_demo --family layered --qubits 6 --shots 100 --seed 42 --truth-mode shifted
   ```

   Open `results/m2b/single_demo.json`. The `calibration_trace` shows pilot measurements and adaptive choices. The `simulator_only_grading` section is not accessible to the placement decision.

5. Run a QUICK comparison first:

   ```bash
   python -m qbridge.robustness_benchmark --family layered --qubits 6 --truth-mode shifted --shots 100 --runs 20 --seed 271828 --output-prefix results/m2b/quick_check
   ```

   This saves `results/m2b/quick_check.json` and `.csv`.

6. Run the full six-case suite, by default 100 simulated environments per case:

   ```bash
   bash scripts/run_m2b_suite.sh
   ```

   Or specify environments and budget explicitly:

   ```bash
   bash scripts/run_m2b_suite.sh 150 100 271828
   ```

7. Upload **`results/QBridge-M2B-Results.zip`** back into ChatGPT for an independent analysis.

**Caution:** The new method recalculates EVSI multiple times per simulated run. A full 12-qubit suite can require minutes depending on your Mac. Start with the quick comparison and tests. Do not run 1000+ environments before checking the results.

## How to read the output

- `mean_regret`: Average gap between chosen placement's actual model loss and hidden-truth best placement. **Lower is better**.
- `paired_comparisons`: Original EVSI regret minus new policy regret on the exact same simulated environments. **Positive means the new policy improves over original EVSI**.
- `paired_95ci`: Bootstrap confidence interval for that paired difference. If it spans zero, our simulated evidence is inconclusive for an advantage.
- `harm_rate`: Fraction of cases where a strategy's placement was worse than the uncalibrated placement.
- `switch_rate`: How often calibration changed the original placement.
- `calibration_trace`: A JSON string in trial-level CSV showing *which calibration received how many shots and how many failures appeared*.
- `guard_probability_better`: Estimated probability that switching to candidate placement is beneficial, **according to current posterior**, not a guaranteed real-world probability.

## Scientific limitations and evaluation discipline

- The simulator has three *grouped* error parameters. It does not represent a realistically large hardware noise parameterization.
- The remote gate uses an *effective* Pauli channel, not a physical entanglement-assisted gate protocol.
- The diagnostic likelihood is idealized Bernoulli/Beta-Binomial; it ignores measurement SPAM, correlated errors and drift during the calibration itself.
- Exact placement enumeration stops at 12 qubits. This is not a scalable general-purpose placement optimizer.
- The mixture prior, exploratory shot split and guard threshold are **untuned hypotheses**. Do **not** tune them on the same scenarios you later report as held-out tests.
- This benchmark currently uses the *same* mathematical noise family to generate truth and calculate loss. It tests **parameter-prior mismatch**, not general model-form mismatch or hardware validity.
- If EVSI's result is lower regret only for a few chosen environments, it is not evidence of a universal advantage. We should compare all circuit families and new random seeds.

## Next decision

If M2B reduces shifted-noise regret without sacrificing the prior-matched cases, freeze the scientific core and prioritize the Muse Spark integration and interface. If results are mixed, keep original EVSI as a supported baseline and demonstrate the diagnostic limitations clearly; do not delay the hackathon interface to chase a perfect algorithm.
