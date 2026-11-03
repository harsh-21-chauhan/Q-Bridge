# Milestone 2C: Final algorithm-selection test

## What is new, and why?

**No original Q-Bridge files are replaced.** This patch adds a held-out benchmark of the following policies:

| Policy | Simple meaning |
| --- | --- |
| `original_evsi` | Spend all shots on the single measurement predicted most valuable before calibrating |
| `random_calibration` | Choose a calibration experiment randomly; use all shots |
| `fixed_split` | Split shots between EVSI's chosen calibration and another group |
| `adaptive_original` | Probe A/B/link, then allocate remaining shots using updated EVSI (current strong baseline) |
| `adaptive_original_guard60` | Same measurements, but change placement only when posterior probability of benefit is **at least 60%** (new candidate) |
| `adaptive_original_guard75` | Same data with a stricter 75% decision rule; isolates the effect of guard strength |
| `adaptive_robust_guard75` | Older adaptive algorithm with mixture priors and strict guard |
| `no_calibration` | Use initial placement, no new measurements; 0-shot reference only |

**Critical fairness rule:** All policies except no-calibration have the same number of simulated calibration shots, and the same true simulated hardware case. They share random measurement streams. The 60% and 75% original-prior guards are computed from the **same posterior samples**, not separately drawn samples.

This is a **fresh-seed test**, so we should not change 60% to a newly tuned threshold *after* seeing these results and still call this a held-out evaluation.

## Exact directory layout

```text
Q-Bridge/
├── src/qbridge/m2c_validation.py    <-- NEW: all policy comparisons
├── scripts/run_m2c_suite.py         <-- NEW: run scenarios + produce ZIP
├── tests/test_m2c.py                <-- NEW: correctness and fairness checks
└── docs/M2C_GUIDE.md                <-- NEW: this guide
```

Nothing else needs editing. Run from the **repository root** with Conda active.

## Installation

```bash
conda activate qbridge
unzip -o ~/Downloads/QBridge-M2C-Final-Validation.zip -d .
python -m pytest -q
```

Expect all your previous tests plus **4 new tests**. You previously had 34 passing tests after M2B, so a fully installed Qiskit Aer environment should show **38 passed**.

## Run a single small validation (fast)

```bash
python -m qbridge.m2c_validation \
  --family layered --qubits 6 --truth-mode shifted \
  --shots 100 --runs 30 --seed 20261104 \
  --output-prefix results/m2c/single_smoke
```

It prints mean regret and harm rate and creates a CSV of each simulated case plus a JSON summary.

## Run the six-case quick suite first

```bash
python scripts/run_m2c_suite.py --mode quick --runs 30 --seed 20261104
```

Quick suite covers all three circuit families at 6q (prior) and 12q (shifted), at 100 shots. It creates `results/QBridge-M2C-quick-runs30.zip`.

## Run the final held-out validation

```bash
python scripts/run_m2c_suite.py --mode full --runs 100 --seed 20261104
```

This tests **40 combinations**: GHZ/layered/star, 6/12 qubits, matched/shifted noise, budgets of 50/100/200 shots, plus 12-qubit layered link-only/local-only shift stress tests. The script reuses matching completed cases if interrupted.

When it finishes, upload **`results/QBridge-M2C-full-runs100.zip`** to ChatGPT.

If you need fewer runs for an early smoke test, the quick suite is sufficient. For final scientific comparisons, use at least 100 held-out simulated cases/scenario and look at **paired** confidence intervals.

## How to interpret results (simple)

- `mean_regret`: how much worse our chosen placement is than a simulator-only oracle. **Lower is better**.
- `harm_rate`: frequency of switching to a placement that is **actually worse** than the pre-calibration choice. Lower is safer, but zero harm alone does not prove useful calibration.
- `help_rate`: frequency of switching to a **better** placement. Higher can be good.
- `switch_rate`: how frequently the placement changes at all.
- `mean_task_loss`: expected execution error for the selected placement under hidden true simulated noise.
- `paired_95ci`: interval for a **paired difference between policies under the same noise conditions**. For `candidate_minus_policy_improvement`, positive values mean the new 60% candidate has lower regret than that competitor. A CI crossing zero is inconclusive.

Our decision should balance prior-matched and prior-shifted scenarios, not just select the smallest regret in one case. Don't erase baselines that beat the new method.

## The scientific limitation

The current 6/12-qubit experiments still assume exactly three effective noise groups, a simplified stochastic Pauli gate channel and known stabilizer-based task loss. A smaller regret is meaningful **inside this model**, not direct evidence of better performance on physical distributed quantum processors. The Meta agent must present results as *simulated*.

## After this benchmark

1. Freeze the selected default algorithm and retain alternatives as comparison options.
2. Build `FastAPI /run` returning calibration trace, placement, expected loss and uncertainty.
3. Build a focused React screen with circuit, budget, timeline of measurements, candidate placements and side-by-side comparison.
4. Integrate an eligible Meta model for **real tool calls and evidence-based Q&A**, not calculations invented by an LLM.
5. Record the 3-minute demo and submit on time. **No further large-scale research features for the hackathon MVP.**
