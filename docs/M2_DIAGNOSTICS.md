# Q-Bridge Milestone 2 — Robustness diagnosis

## Goal
Understand **why** EVSI succeeds or fails, before changing priors or algorithms.
This diagnostic is a simulation-only experiment. It does not modify any M1 scientific code.

## Files you add
- `src/qbridge/diagnostics.py` — main diagnostic and CLI (`python -m qbridge.diagnostics`).
- `tests/test_diagnostics.py` — tests for paired benchmarking, data integrity, and diagnostics.
- `docs/M2_DIAGNOSTICS.md` — this explanation.

## Run
Execute commands at the repository root with your `(qbridge)` Conda environment activated.

```bash
python -m pytest -q
python -m qbridge.diagnostics --family layered --qubits 6 --truth-mode prior --runs 300 --shots 50 100 200 500 --seed 123 --output-prefix results/diagnostics/layered6_prior
python -m qbridge.diagnostics --family layered --qubits 6 --truth-mode shifted --runs 300 --shots 50 100 200 500 --seed 123 --output-prefix results/diagnostics/layered6_shifted
python -m qbridge.diagnostics --family layered --qubits 12 --truth-mode prior --runs 300 --shots 50 100 200 500 --seed 123 --output-prefix results/diagnostics/layered12_prior
python -m qbridge.diagnostics --family layered --qubits 12 --truth-mode shifted --runs 300 --shots 50 100 200 500 --seed 123 --output-prefix results/diagnostics/layered12_shifted
```

To isolate WHERE the prior breaks, also run:

```bash
python -m qbridge.diagnostics --family layered --qubits 12 --truth-mode link_shift --runs 300 --shots 50 100 200 500 --seed 123 --output-prefix results/diagnostics/layered12_link_shift
python -m qbridge.diagnostics --family layered --qubits 12 --truth-mode local_shift --runs 300 --shots 50 100 200 500 --seed 123 --output-prefix results/diagnostics/layered12_local_shift
```

To check whether the effect is circuit-dependent, replace `--family layered` with `--family ghz` or `--family star`, and use a distinct `--output-prefix`.

## Interpret the output
- `prior_mismatch.mean_abs_z_score`: larger means true parameter differs more from the assumed Beta distribution. A *simulation* diagnostic, since real ground-truth noise is unknown.
- `prior_mismatch.outside_prior_95_percent_rate`: portion of simulated worlds outside the stated 95% prior interval.
- `placement_geometry.no_calibration_oracle_optimal_rate`: how often prior-only placement was already optimal. If high, calibration has little room to help and can hurt.
- `placement_geometry.mean_margin_to_next_distinct_loss`: task-loss difference between the best and next *distinct* loss. We explicitly count ties because there may be equally good placements.
- `perfect_one_parameter_counterfactual`: uses oracle knowledge of ONE true error parameter in a point-estimate decision. This is NOT a feasible calibration policy; it is an ablation showing whether knowing one parameter could change a placement.
- `evsi_selected`: EVSI's recommended calibration parameter before shots. This does not change between independent environments under identical priors/circuit/budget.
- `evsi_switch_rate`: fraction of scenarios where calibration changed placement relative to the no-calibration decision.
- `evsi_helped_rate / harmed_rate`: fraction where calibration decreased / increased true regret relative to doing nothing. These are evaluated with hidden simulation truth, not known to Q-Bridge.
- `evsi_unexpected_calibration_outcome_rate`: fraction of EVSI calibration outcomes with approximate two-sided prior-predictive tail probability below 0.05. This is only a warning flag (not a calibrated statistical hypothesis test).
- `evsi_minus_no_cal.mean_regret_difference`: **negative** = EVSI better; positive = EVSI worse. Its `ci95` is a paired bootstrap interval over simulated hardware worlds. If the interval includes zero, the evidence is inconclusive.
- `evsi_minus_random`: same comparison against random calibration; random receives identical shots and the same underlying hardware worlds.

## Scientific boundaries
1. These experiments use **effective Pauli channels** (not full quantum teleportation, real QPU data, or realistic link scheduling).
2. We calibrate one of only **three grouped noise probabilities**. Extension to more parameters is a separate milestone.
3. The scoring uses analytically computed expected task error under hidden simulation truth; we do not pay additional execution shots to estimate it. Therefore the experiment tests calibration-shot budgeting, not full end-to-end experimental cost.
4. This code purposely exposes hidden truth *only to diagnostic grading*. Policies cannot use it in calibration or placement selection.
5. Paired 95% bootstrap intervals capture finite-run sampling variation within a specified simulation population; they do not imply correctness for physical hardware.
6. The shifted scenarios are **synthetic stress tests**, not measured hardware distributions. The original M1 `shifted` sampler consumes a different random sequence, so the exact 300-run summary values may not match prior M1 results even with the same seed.
7. The report may be long. Send the six `.json` summaries (or a zip with the JSON and CSV files) for cross-scenario analysis.

## Run the complete suite with ONE command

```bash
bash scripts/run_m2_suite.sh
```

This tests layered 6/12 qubits × prior/shifted, then separates the local-only
and link-only shifts at 12 qubits. It creates a `results/QBridge-M2-Diagnostic-Results.zip`
archive and `results/diagnostics/summary.csv` for quick review. **Upload that
results archive back to ChatGPT** for analysis. Your original scientific source
files remain untouched.

You can also regenerate the compact summary any time:

```bash
python scripts/summarize_m2.py
```
