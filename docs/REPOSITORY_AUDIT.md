# Repository audit and cleanup record

Date: 4 November 2026. Research baseline: `50fa52dbfa28dd7bee2088a9fd422fabdd8bd852`. Working branch: `codex/hackathon-app`.

This is a maintenance record: what was inspected, what cleanup changed, and what still needs attention. The root [README](../README.md) is the project introduction; the [research index](../research/README.md) is the evidence catalog. This file does not duplicate either or serve as a new scientific report.

## Inspection findings

The baseline contained 211 tracked files: 16 scientific modules, nine test modules, five research scripts, seven scientific/history documents, README and packaging configuration, four ZIP archives, 130 expanded JSON/CSV artifacts, and 38 generated files.

All 38 scientific tests passed in the existing Python 3.11 qbridge Conda environment, including both optional Qiskit Aer checks. The default shell Python did not contain pytest. No dependencies were installed or changed during cleanup.

All original ZIPs passed CRC checks and all 129 members exactly matched expanded files. All 67 JSON and 63 CSV files parsed. Full M2C metrics recomputed from 32,000 policy rows matched the per-case and aggregate summaries. There were 991 distinct simulated noise triples across the full benchmark. Quick M2C trials overlap full trials; their summaries are not independent evidence.

## Approved cleanup completed

The user approved cleanup and requested that duplicate content not remain in the repository. The earlier plan to keep local expanded duplicates was therefore replaced with canonical storage:

- Preserved all scientific source, tests, five research runners/summarizers, dependency configuration and seven historical documents unchanged.
- Removed 38 tracked generated files and the local pytest cache; added `.gitignore`. The existing external Conda environment was preserved.
- Repacked three evidence archives with unchanged research-record bytes. Summaries and examples are stored separately and omitted from those archives.
- Removed the redundant quick M2C archive after preserving its six unique JSON summaries and aggregate CSV summary.
- Removed seven quick-run CSV copies after verifying that each was an exact byte prefix of its corresponding full CSV: six M2C cases and the M2B quick check. Their exact original bytes remain reconstructable.
- Replaced 130 expanded research artifacts with 123 canonical content records and seven verified prefix references. Removed expanded copies from `results/`.
- Added the evidence verifier and one authoritative [provenance manifest](../research/provenance.json). Removed superseded file-plan/tree appendices to avoid maintaining parallel inventories.
- Updated the root README to reflect completed research and clearly identify application development as pending.

Archive container checksums changed because duplicated members were removed. Every research artifact's original content checksum is retained in the provenance manifest; the original ZIPs remain recoverable from the baseline Git commit. No Git history was rewritten.

Before cleanup, a verified recovery snapshot of all 211 original tracked files and the audit documents was saved outside the repository at `/private/tmp/qbridge-pre-cleanup-50fa52d.zip`. It also preserves the pre-existing local change to `docs/.DS_Store`. This is a temporary local recovery aid, not a durable evidence location; Git history and the canonical research records are the durable sources.

## Validation

Run from the repository root:

```bash
python3 scripts/verify_research_evidence.py
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
```

Use the qbridge environment for the second command. Verification checks archive/container hashes, all 130 recoverable artifact hashes, exact member coverage and absence of duplicate canonical record contents. Restoration to a fresh directory was also checked against the original artifact checksums. The final scientific regression run passed all 38 tests.

## Deferred to development

No scientific behavior or application code was changed in this cleanup. The next work is a production wrapper explicitly using original priors and a 60% guard, followed by FastAPI, persistence, React and Meta tool integration.

Known integration issues remain: `run_sequential()` defaults to mixture priors; the guard reports a placeholder `0.5` when no meaningful switch is proposed; M2C currently converts that value unconditionally to float. Correcting reporting requires a coordinated source/test change. The production output also needs complete posterior snapshots, same-posterior placement comparisons and a separate simulator-evaluation section. What-if comparisons must preserve measurement-stream prefixes, not just reuse a seed.

No Meta credentials were present in the inspected environment, and no real model call or billing change was made. Account access and a successful tool-calling round trip remain unverified. The finalized scientific policy and its limitations remain documented in [the original M2C decision](QBridge-M2C-final-decision.md).
