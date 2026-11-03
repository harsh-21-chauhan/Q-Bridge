# Q-Bridge

**Decision-aware Bayesian calibration for distributed quantum circuit placement.**

Q-Bridge investigates how to spend a limited calibration budget before assigning a quantum circuit's qubits to two processors. Python computes which error sources to measure, updates Bayesian beliefs, and evaluates placements under uncertainty.

**Simulation-only research prototype.** M1, M2A, M2B and M2C research and the scientific production interface are complete. The selected method is adaptive EVSI with the original Beta priors and an optional 60% placement-switch guard. FastAPI and React are next; hosted Meta Muse Spark integration is deferred until those stages are complete and real-call testing is explicitly authorized.

## Selected scientific method

1. Start with illustrative error priors: Beta(2,98) for local A, Beta(3,97) for local B, and Beta(4,76) for remote operations.
2. Explore all three error groups. At 100 shots, allocate 10 to A, 10 to B and 20 to the remote link.
3. Use updated expected value of sample information (EVSI) to choose two further calibration batches, updating the posterior after each. At 100 shots, each batch has 30 shots. Existing budget functions support 20–1000 shots.
4. Choose the placement with the lowest posterior expected task loss.
5. Optionally accept a change only when its expected improvement is positive and its sampled posterior probability of improvement is at least 60%.

The production wrapper in `src/qbridge/production.py` implements the finalized `adaptive_original_guard60` policy using existing scientific functions and explicitly selects the original priors. It returns complete calibration evidence and keeps simulator evaluation separate. The historical M2B demo uses mixture priors and a 75% guard; it is not the selected product default. See the [scientific interface contract](docs/SCIENTIFIC_INTERFACE.md) for Python usage, output fields and validation.

See the [final scientific decision](docs/QBridge-M2C-final-decision.md) for the rationale and limitations.

## Run the existing research code

Python 3.10 or newer is required. From a fresh checkout:

```bash
git clone https://github.com/harsh-21-chauhan/Q-Bridge.git
cd Q-Bridge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

On Windows, activate with `.venv\Scripts\activate`. If you already use the project's Conda environment, run `conda activate qbridge` instead of creating another environment.

Run a complete final-method experiment (optional output must be a new file):

```bash
python -m qbridge.production --family layered --qubits 6 --shots 100 --seed 42 --output results/production/seed42.json
```

Add `--unguarded` to disable the placement guard, or omit `--output` to print JSON only. The output includes initial/candidate/final placements, stage-by-stage Bayesian updates and EVSI choices, shot accounting, guard evidence and a separate simulator-only evaluation. No model or API key is needed.

Inspect the circuit and run a small historical M2C comparison:

```bash
python -m qbridge.cli inspect --family layered --qubits 6
python -m qbridge.m2c_validation --family layered --qubits 6 --truth-mode shifted --shots 100 --runs 3 --seed 42 --output-prefix results/m2c/smoke
```

This is a functional smoke test, not enough trials for a performance claim. For the historical one-experiment M1 demonstration:

```bash
python -m qbridge.cli demo --family layered --qubits 6 --shots 100 --seed 42
```

Optional independent Qiskit Aer validation:

```bash
python -m pip install -e '.[aer,dev]'
python -m qbridge.cli validate-aer --family layered --qubits 6
python -m pytest -q
```

The cleanup baseline passed all 38 tests, including both Aer checks. The production suite adds archived M2C equivalence checks, exact budget/posterior checks, truthful guard reporting, reproducibility and simulator-truth isolation. Without the optional Aer dependencies, the two Aer tests are skipped.

## Repository layout

```text
Q-Bridge/
├── src/qbridge/              Scientific engine and historical policy implementations
├── tests/                    Scientific regression and independent validation tests
├── scripts/                  Research runners, summarizers and evidence verification
├── research/
│   ├── evidence/             Three archives containing canonical research records
│   ├── summaries/            Browsable summaries, including distinct quick-run reports
│   ├── examples/             Historical M1 and M2B examples
│   └── provenance.json      Checksums and original-to-canonical artifact mapping
├── results/                  Ignored generated runs; only its README is versioned
├── docs/                     Preserved research guides, final decision and cleanup record
├── pyproject.toml
└── README.md
```

The scientific modules remain separate: circuit construction and loss evaluation; Bayesian inference and EVSI; adaptive calibration and placement guards; research benchmarks and diagnostics; NumPy reference simulation and optional Aer validation. No mathematical core was rewritten for cleanup.

## Research evidence

The [research index](research/README.md) links the canonical archives, summaries and examples. Raw evidence is stored once. Summaries and examples are not repeated inside archives. Seven quick-run CSVs were verified to be exact byte prefixes of full-run CSVs; their distinct summaries remain, and the original quick CSVs can be reconstructed exactly from the provenance manifest.

Verify all evidence without installing scientific dependencies:

```bash
python3 scripts/verify_research_evidence.py
```

The full M2C benchmark contains 40 configurations × 100 trials × eight policies. The selected 60% guard has observed mean regret approximately **0.001299** and a **4.45%** harmful-switch rate across all trials. Its regret advantage over unguarded adaptive EVSI is small and not statistically established as universal. The quick runs overlap the full runs, and simulated environments are shared across some configurations; do not count them as independent replications. Use the [full summary](research/summaries/m2c-final-summary.csv) and [decision report](docs/QBridge-M2C-final-decision.md) for interpretation.

Historical guides remain available: [M1 walkthrough](docs/M1_WALKTHROUGH.md), [M1 setup](docs/STEP_BY_STEP.md), [scientific specification](docs/SPEC.md), [M2 diagnostics](docs/M2_DIAGNOSTICS.md), [M2B](docs/M2B_GUIDE.md), and [M2C](docs/M2C_GUIDE.md). Their milestone-specific defaults and instructions describe the research at that time. Scripts still write disposable outputs to `results/`; see its [usage notes](results/README.md).

## Scientific boundaries

- Two labeled processors, A/B, each holding half the qubits; deterministic GHZ, layered and star Clifford circuits.
- Three effective error probabilities. After a CNOT, the modeled channel applies identity with probability `1-p`, X on the target with `p/2`, or Z on the control with `p/2`.
- Task loss is mean incorrect stabilizer-generator parity probability, **not full quantum state fidelity**.
- Exact placement enumeration is limited to 12 qubits: 20 placements at 6 qubits, 924 at 12.
- Remote operations use a simplified error channel, not physical teleportation, entanglement-generation or network-timing simulation.
- Binary calibration observations assume idealized diagnostics; no real quantum hardware is connected.
- Hidden simulator truth generates observations and grades results. It must never influence recommendations or be presented as observed calibration evidence to an assistant.
- The guard describes uncertainty under the assumed posterior. It cannot guarantee beneficial decisions under a wrong model or prior.

## Next development stage

The scientific production wrapper is implemented. Next add FastAPI/local experiment persistence, then the React research dashboard. Hosted Meta Muse Spark integration follows those stages, using Python tools to retrieve, compare and explain scientific results. Real API calls require explicit testing authorization. See the [development order and saved Meta requirements](docs/DEVELOPMENT_PLAN.md); no Meta integration or real model call has been implemented or performed.

The [repository audit](docs/REPOSITORY_AUDIT.md) is a maintenance record of inspection and cleanup, not a second project README. Further research ideas and application architecture will be documented as development proceeds.
