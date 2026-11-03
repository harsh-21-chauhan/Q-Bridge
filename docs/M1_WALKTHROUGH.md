# Q-Bridge M1 — A Beginner-Friendly Code Walkthrough

## What we built, in one paragraph

We create a small quantum circuit and try different assignments of its qubits to two simulated quantum processors. Local and remote gates have uncertain error probabilities. With a limited number of calibration shots, Q-Bridge uses Bayesian **expected value of sample information (EVSI)** to choose *which* error probability to measure. The simulated calibration provides failures and successes; a Beta-Binomial update revises our beliefs. Q-Bridge then chooses the placement with the lowest **expected task loss** under those beliefs. Finally, a benchmark compares its choice to random, fixed, high-uncertainty, and no-calibration strategies using hidden true noise parameters available only to the simulator.

## The exact chain, and where to read the code

| Stage | File in `src/qbridge/` | What to look for |
| --- | --- | --- |
| 1. Circuit | `circuits.py` | `make_circuit` creates H and CX gates; `placements` lists 20 layouts for 6 qubits |
| 2. Error/loss model | `loss.py` | `PlacementModel.counts` tracks which gate errors flip each stabilizer; `losses` computes task loss |
| 3. Bayesian priors | `bayes.py` | `DEFAULT_PRIORS` = 2%, 3%, 5% *prior mean* error rates |
| 4. Choose measurement | `bayes.py` | `evsi` evaluates how each possible calibration could improve the final placement decision; `select` chooses one |
| 5. Simulate calibration | `experiment.py` | `measure_binomial` returns number of failures in `shots` trials, or use Aer backend |
| 6. Update & place | `experiment.py` | `BetaPrior.updated` changes one error distribution; `planner.recommend` chooses placement |
| 7. Grade result | `experiment.py` | Simulator-only oracle computes minimum true loss; `decision_regret = selected loss - oracle loss` |
| 8. Compare policies | `benchmark.py` | Repeats independent worlds with shared seeds and prints mean regret and task loss |
| 9. Verify simulation | `reference_sim.py`, `aer_validation.py` | Check analytical loss against independently simulated quantum channels |
| 10. Terminal commands | `cli.py` | Connects the components above to `inspect`, `rank`, `demo`, `benchmark`, etc. |

## Bayesian update, without unnecessary jargon

Suppose QPU A starts with Beta(2,98), so its mean estimated error is 2%. In 100 simulated diagnostic shots, 6 fail. The posterior becomes Beta(8,192), so the revised expected error is 8/(8+192)=4%. Unlike simply taking 6/100=6%, this estimate combines the observations with the original uncertainty model.

## What are the 20 placements?

Every placement is a vector of six labels, with exactly three A labels (`0`) and three B labels (`1`). Example: `[1,0,1,1,0,0]` assigns logical qubits 0,2,3 to B, and 1,4,5 to A. Different assignments create different amounts of local and remote operations.

## What exactly does 'loss' mean?

M1 uses the average probability of an incorrect parity result across the ideal circuit's stabilizer generators under a specified effective Pauli-noise channel. It is **not** an arbitrary general-circuit fidelity, a full teleportation simulation, or a physical quantum computer measurement. All this is documented in `docs/SPEC.md`.

## Why did EVSI lose in the `shifted` benchmark?

The same Bayesian priors are reused across all 100 simulated worlds. `shifted` deliberately draws hardware parameters from a different distribution (not from those priors). EVSI is optimal *in expectation for its own assumed model* when its predictive probabilities and loss are correct, not necessarily under distribution shift, not in every random sample, and not on unmodeled real hardware. In your shifted output, EVSI picks `local_a` every time and has higher average regret than random/no calibration. That is a robustness limitation to investigate, not a hidden success.

## Why are EVSI and fixed-A identical?

The chosen calibration is `local_a` for this fixed circuit, priors and budget. So both strategies use the same measurements and Bayesian update, then the same placement optimizer. They must have identical results in M1 under these settings.

## Why are max-variance and no-calibration tied in your test?

For these tested worlds, the max-variance strategy's measurements did not change the resulting achieved task loss compared with the prior-only decision. It does **not** prove calibration is never useful.

## Next scientific checks (no code changes required)

Run these from the repository root with `(qbridge)` active:

```bash
python -m pytest -q
python -m qbridge.cli benchmark --family layered --qubits 6 --shots 100 --runs 100 --seed 123 --truth-mode prior
python -m qbridge.cli benchmark --family ghz --qubits 6 --shots 100 --runs 300 --seed 123 --truth-mode prior
python -m qbridge.cli benchmark --family star --qubits 6 --shots 100 --runs 300 --seed 123 --truth-mode shifted
```

Check `mean_regret` (lower is better). Do not infer reliable superiority from one 100-world run. Also inspect whether the recommended calibration differs when the circuit family changes. We will add paired confidence intervals, sensitivity tests, and more realistic noise before claiming benefits.

## What's simplified in Milestone 1?

- Effective remote-gate errors; **no actual gate teleportation**.
- Idealized binary calibration with perfect preparation and readout.
- Three independent, static error groups; no drift/correlation.
- Small Clifford circuits; exact search over only 20 placements.
- One calibration choice per experiment, not multi-round online learning.
- Muse Spark is **not connected** in this milestone.

## How we will deliver subsequent code changes

Each next stage will specify the repository-root-relative file path (e.g., `src/qbridge/bayes.py`), whether to create or replace it, commands to install dependencies, and a passing test before continuing. We will keep comments alongside nontrivial mathematical and scientific logic.
