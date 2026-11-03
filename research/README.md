# Research evidence

This directory preserves the M1–M2C evidence without storing the same record twice. Historical source code, tests and guides remain in `src/`, `tests/`, `scripts/` and `docs/`.

## Canonical artifacts

| Milestone | Trial records and reports | Browsable summary |
|---|---|---|
| M2A robustness diagnostics | [Archive](evidence/QBridge-M2-Diagnostic-Results.zip), 18 records | [24-row summary](summaries/m2-diagnostics-summary.csv) |
| M2B adaptive/mixture/guard comparison | [Archive](evidence/QBridge-M2B-Results.zip), 13 records | [49-row summary](summaries/m2b-summary.csv) |
| M2C final comparison | [Archive](evidence/QBridge-M2C-full-runs100.zip), 80 records | [320-row full summary](summaries/m2c-final-summary.csv) |
| M2C quick subset | [Six case reports](summaries/m2c-quick/) | [48-row quick summary](summaries/m2c-quick-summary.csv) |

The archives contain JSON reports and trial CSVs; the M2A archive also includes terminal reports. The M2B archive retains its distinct quick-check JSON report. Summaries in this table are not repeated inside the archives.

Historical examples:

- [M1, seed 42](examples/m1-demo-seed42.json): original single-experiment EVSI.
- [M2B mixture-prior/75% guard example](examples/m2b-mixture-guard75-demo.json): historical experimental behavior, including its old placeholder probability. It is not a final-method example.

The [M2C decision report](../docs/QBridge-M2C-final-decision.md) explains why original-prior adaptive EVSI with an optional 60% guard was selected. No scientific result was rewritten to reflect that later choice.

## Interpretation

Use the full M2C summary for final policy comparisons. Its 40 configurations each have 100 trials and eight policies. The six quick M2C trial CSVs exactly repeat the first 30 trials of corresponding full cases; their distinct summaries are retained above. The M2B quick CSV similarly repeats the first 20 trials of `layered6_shifted.csv`, and the M2B summary includes that quick case as seven additional rows. Do not pool either quick set with its full counterpart as independent evidence.

Harm/help rates use all trials as their denominator. No-calibration uses zero shots; other policies spend the configured budget. Regret uses simulator-only truth and is not directly observed hardware accuracy. Shared simulated environments across configurations also limit independence. A lower aggregate mean does not establish universal superiority.

The historical M2C column `candidate_minus_policy_improvement` actually records comparator regret minus candidate regret: a positive value favors guard60. Its paired confidence intervals are scenario-specific, not an aggregate confidence interval.

## Verify or restore

The [provenance manifest](provenance.json) maps all 130 original JSON/CSV artifacts to canonical files, archive members or exact prefix references. It records original and current checksums, including the original ZIP hashes and baseline Git commit. There are 123 unique stored content records plus seven prefix references.

From the repository root, with Python's standard library only:

```bash
python3 scripts/verify_research_evidence.py
```

To reconstruct all original JSON/CSV paths under a **new, non-existent directory**:

```bash
python3 scripts/verify_research_evidence.py --restore-dir /tmp/qbridge-evidence-restored
```

The output will contain `/tmp/qbridge-evidence-restored/results/...`, including the seven original quick CSVs reconstructed byte for byte. The script refuses an existing destination and verifies evidence before writing. This avoids overwriting newer results. Original ZIP container bytes are available from Git commit `50fa52dbfa28dd7bee2088a9fd422fabdd8bd852`; current archives were repacked to remove duplicated members, so their ZIP hashes intentionally differ.

New research runs should write to the ignored `results/` directory. Treat this directory as a frozen evidence snapshot: do not overwrite its archives or summaries during routine runs. Any future curated dataset needs explicit provenance and verification.
