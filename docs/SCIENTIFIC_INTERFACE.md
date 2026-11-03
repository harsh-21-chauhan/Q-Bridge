# Scientific production interface

`src/qbridge/production.py` exposes the finalized adaptive-original-prior method without FastAPI, UI, model calls, or persistence dependencies. It reuses the existing calibration engine, Bayesian updates, loss calculations and guard. The output is JSON-safe and versioned with schema `1.0` and algorithm `adaptive-original-v1`.

## Run one simulated experiment

With the existing environment active, from the repository root:

```bash
conda activate qbridge
python -m qbridge.production --family layered --qubits 6 --shots 100 --seed 42 --output results/production/seed42.json
```

The command prints the full JSON record and optionally writes it to a **new** file. Existing output files are not overwritten. Omit `--output` to print only. Add `--unguarded` to select the minimum posterior expected-loss placement without a probability guard. `--guard-threshold` defaults to 0.60 and `--guard-draws` to 512. Historical M1 and M2B commands keep their original algorithm choices.

Programmatic use:

```python
from qbridge.production import SimulationConfig, run_experiment

record = run_experiment(SimulationConfig(
    family="layered", qubits=12, shots=100, seed=42,
    truth_mode="shifted", guard_enabled=True, guard_threshold=0.60,
))
evidence = record["result"]
print(record["experiment_id"])
print(evidence["placements"]["final"]["assignment"])
print(evidence["decision"])
```

Only the finalized adaptive method is exposed in this interface. Historical baseline policies remain in the research modules; future API comparisons must use the appropriate existing policy, not relabel an adaptive run as a baseline.

## Separate decision and simulator boundaries

`calibrate_measurements(CalibrationConfig(...), stream, guard_seed=...)` is the measurement-only entry point. It accepts no truth parameters, oracle information or simulation-scenario settings. `stream` has shape `(3, shots)`, in `local_a`, `local_b`, `remote` order, with only boolean or numeric 0/1 values. The engine consumes exactly the configured total budget across those three reservoirs; unused outcomes do not influence the recommendation and are not exposed in the result. Input arrays are not modified.

`run_experiment(SimulationConfig(...))` generates measurements, calls that decision interface, and only then evaluates the completed decision against hidden simulator truth. Its record has these sections:

| Field | Meaning |
|---|---|
| `experiment_id` | Deterministic `qb_` identifier based on normalized configuration, schema/algorithm version, seed scheme and runtime versions |
| `mode` | Always `simulation` |
| `configuration` | Simulation configuration, including seed and scenario |
| `metadata` | Schema/algorithm/seed versions and Python, NumPy, SciPy and Q-Bridge versions |
| `result` | Measurement and posterior-based decision evidence only |
| `evaluation` | Clearly labeled hidden true rates, oracle placement/loss, actual losses, regret and actual improvement |

Future explanatory tools should receive `result` plus the experiment ID and an explicit simulation label, not the whole stored record. Scenario selections are assumptions, not observed calibration results. Mathematical calculations remain in Python.

## Result contract

- `configuration`, `guard_seed`, `algorithm`, and `schema_version` identify the decision calculation.
- `circuit` contains gates, stabilizer labels, CNOT count and exhaustive placement count. Gate indices follow the existing circuit representation: H uses `control` as its qubit and `target=-1`; CNOT uses both indices.
- `initial_priors` and `final_posterior` contain each group's Beta alpha/beta parameters, mean and equal-tail 95% credible interval.
- `calibration` contains pilot allocation, two adaptive batch sizes, total/group shot counts, failure counts and five trace steps. Each step includes all-group posterior snapshots before/after, cumulative shot counts and the original engine's EVSI scores. Pilot EVSI is `null` because the pilot allocation is predetermined.
- `placements.initial`, `.candidate`, and `.final` contain placement indices, 0/1 assignments, QPU qubit lists and local/remote CNOT counts. The candidate is the unguarded posterior optimum; final is the accepted decision.
- `loss` distinguishes the initial placement's prior expected loss from the initial/candidate/final expected losses under the **same final posterior**. Candidate improvement can be positive even if the guard rejects it; accepted improvement is zero when the initial placement is retained.
- `decision` reports switched status, a reason, guard settings, estimated probability when computed, and the number of posterior draws actually used. Status is `unchanged`, `no_positive_gain`, `accepted`, `rejected`, or `unguarded`.

The probability is `null` when the guard is disabled, candidate equals incumbent, or expected improvement is no greater than the existing numerical tolerance. `posterior_draws_used` is then zero. A rejected switch can still have a genuine numeric probability. A posterior probability is evidence under the model, not a guarantee against real-world harm. Credible intervals describe model uncertainty, not hardware validation.

## Frozen scientific behavior

The wrapper explicitly passes `default_as_mixtures()` to `run_sequential()`: these are one-component representations of the original Beta(2,98), Beta(3,97), Beta(4,76) priors. It does not use the adaptive engine's historical mixture-prior default. The existing budget function produces a 10/10/20-shot pilot and two 30-shot adaptive stages at a 100-shot budget.

The incumbent uses `BayesianPlanner.recommend(DEFAULT_PRIORS)` exactly as M2C. The guard retains M2C's `expected_gain > 1e-10` check, strict sampled loss improvement tolerance `1e-12`, original posterior sampling implementation and threshold comparison `>=`. Disabling the guard uses the engine's candidate directly, including its existing tie behavior.

The shared guard now returns `None` instead of a placeholder 0.5 for uncomputed evidence. M2C's nullable handling and the associated historical test were updated together; placement decisions and archived research artifacts are unchanged. The historical guard function's 75% default remains; production explicitly passes 60%.

## Validation and reproducibility

Supported public configuration: families `ghz`, `layered`, `star`; qubits 6 or 12; integer shots 20–1000; finite guard threshold 0.5–1.0; integer guard draws 64–16,384; integer simulation seed 0 through `2**32-1`; truth mode `prior`, `shifted`, `local_shift`, or `link_shift`. The direct decision sampling seed supports integers 0 through `2**63-1`. Invalid booleans-as-integers, nonfinite values, unsupported sizes, malformed streams and nonbinary observations are rejected.

Simulation uses the versioned `seedsequence-truth-and-three-groups-v1` scheme: one independent RNG for hidden truth and one per measurement group. Keeping seed and scenario fixed while changing budget preserves the true environment and every group's measurement prefix. The guard uses `seed * 100_003`. Future what-if records can therefore reuse configuration with only `shots` changed, while retaining the original record and its lineage in the backend.

This simulator seed scheme differs from the historical benchmark's sequential RNG. The same user seed alone does not reproduce a historical trial. The direct decision interface permits replay using the actual historical streams and guard seed `seed * 100_003 + trial`. Version changes should update algorithm/schema/seed identifiers as appropriate; IDs do not include timestamps, and repeat runs in the same runtime are identical. Runtime versions are included in IDs because library changes can affect numerical reproducibility.

```bash
python -m pytest -q
python3 scripts/verify_research_evidence.py
```

Tests compare three recorded trials from **each of all 40 full M2C configurations** with archived placements, probabilities, calibration traces and task losses. This checks 120 historical trial/configuration combinations without rerunning or modifying the whole benchmark. Additional tests cover original priors, complete posterior updates, odd/boundary budgets, guard acceptance/rejection/disable/no-switch behavior, JSON serialization, deterministic IDs, paired budget prefixes, and simulator-truth/unused-measurement isolation.
