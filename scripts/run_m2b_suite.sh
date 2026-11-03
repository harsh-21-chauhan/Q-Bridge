#!/usr/bin/env bash
# M2B reproducible suite; execute from the Q-Bridge repository root.
set -euo pipefail
RUNS="${1:-100}"
SHOTS="${2:-100}"
SEED="${3:-271828}"
mkdir -p results/m2b
run_case() {
  local family="$1" n="$2" mode="$3"
  echo "============================================"
  echo "M2B: ${family}, ${n} qubits, ${mode}, ${RUNS} environments, ${SHOTS} shots"
  python -m qbridge.robustness_benchmark \
    --family "$family" --qubits "$n" --truth-mode "$mode" \
    --shots "$SHOTS" --runs "$RUNS" --seed "$SEED" \
    --output-prefix "results/m2b/${family}${n}_${mode}"
}
run_case layered 6 prior
run_case layered 6 shifted
run_case layered 12 prior
run_case layered 12 shifted
run_case layered 12 link_shift
run_case layered 12 local_shift
python scripts/summarize_m2b.py
python - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
folder = Path('results/m2b')
out = Path('results/QBridge-M2B-Results.zip')
with ZipFile(out, 'w', ZIP_DEFLATED) as z:
    for f in sorted(folder.glob('*')):
        if f.is_file() and f.suffix in {'.csv', '.json'}:
            z.write(f, f.relative_to('results'))
print(f'\nShare this file for scientific review: {out}')
PY
