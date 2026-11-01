# Build / test Q-Bridge (Mac + VS Code)

This is a **scientific Milestone 1**, not the final research dashboard. Execute each step in the same terminal. Expected numeric values will vary with `--seed` and true noise settings.

## Step 0 — Download source

If the repository files have been committed:

```bash
git clone https://github.com/harsh-21-chauhan/Q-Bridge.git
cd Q-Bridge
code .
```

If using the provided ZIP instead, unzip into a directory called `Q-Bridge`, then `cd Q-Bridge`.

## Step 1 — Environment

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Expected: no package installation errors; `python -c 'import numpy, scipy, qbridge; print(qbridge.__version__)'` displays `0.1.0`.

## Step 2 — Confirm the circuit and placements

```bash
python -m qbridge.cli inspect --family layered --qubits 6
```

Expected: `placement_count: 20`, multiple CNOT gates, six stabilizer labels including at least one X-only label and some Z-only labels.

## Step 3 — Independently verify the loss function (no Qiskit required)

```bash
python -m qbridge.cli check-loss --family layered --qubits 6
python -m pytest -q
```

Expected: `pass: true`, loss discrepancy close to zero; all pure-Python tests pass. The two optional Aer tests are skipped until you install Aer.

## Step 4 — Rank calibration choices with Bayesian EVSI

```bash
python -m qbridge.cli rank --family layered --qubits 6 --shots 100
```

Expected: three numeric EVSI values and exactly one chosen experiment. They are *expected reductions in task loss*, not measured quantum fidelities.

## Step 5 — Run an end-to-end simulated decision

```bash
python -m qbridge.cli demo --family layered --qubits 6 --shots 100 --seed 42 --output results/demo_seed42.json
```

Expected: `results/demo_seed42.json` is created; measured `observed_failures` between 0 and 100, changed posterior for one parameter, recommended 0/1 placement array, nonnegative oracle-based decision regret. The true noise parameters are provided to the simulated world, **not** the Bayesian decision rule.

You can change the hidden synthetic environment:

```bash
python -m qbridge.cli demo --family star --qubits 6 --shots 50 --seed 5 --truth-a 0.015 --truth-b 0.07 --truth-link 0.13
```

## Step 6 — Evaluate against baselines

```bash
python -m qbridge.cli benchmark --family layered --qubits 6 --shots 100 --runs 100 --seed 123
python -m qbridge.cli benchmark --family layered --qubits 6 --shots 100 --runs 100 --seed 123 --truth-mode shifted
```

Expected: mean regret and mean task loss for EVSI, random, fixed A, maximum prior variance, and no calibration. **Do not expect EVSI to beat every policy in every run.** The comparison is paired on the same hidden worlds and shot budget.

## Step 7 — Run independent Qiskit Aer checks

```bash
python -m pip install -e '.[aer,dev]'
python -m qbridge.cli validate-aer --family layered --qubits 6
python -m qbridge.cli demo --family layered --qubits 6 --shots 100 --calibration-backend aer
python -m pytest -q
```

Expected: `pass: true` for both Aer checks, and **zero skipped tests** in `pytest` if Aer installs successfully. If the two Aer checks fail, stop: share the complete terminal traceback and Qiskit versions before going on to benchmarks/UI.

## Step 8 — Share results / push to GitHub

```bash
git status
git add .
git commit -m "Implement Q-Bridge scientific M1 and validation"
git push origin main
```

**Only run the commit/push commands if you are working from the ZIP or have made changes that are not already committed.** If files were created in the repository, there is no need to re-push them.

## Later milestones (not in this initial commit)

- M2: larger circuits, hardware-rich noise models, approximate candidate placement search, performance scaling, and broader task-based observables.
- M3: FastAPI server, experiment logging, React UI.
- M4: Muse Spark agent with deterministic tool routing, rigorous grounding and API spending safeguards.

**Research limitation:** This first version uses an effective remote CNOT noise model; it neither implements the full teleportation protocol nor operates on actual quantum hardware.
