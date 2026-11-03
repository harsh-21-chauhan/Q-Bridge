#!/usr/bin/env bash
# Run from anywhere; the script switches to the Q-Bridge repository root.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p results/diagnostics

# Each run measures exactly the same scientific questions while controlling
# circuit size and what part of the initial prior is incorrect.
for qubits in 6 12; do
  for mode in prior shifted; do
    name="layered${qubits}_${mode}"
    echo "===== ${name} ====="
    python -m qbridge.diagnostics \
      --family layered --qubits "$qubits" --truth-mode "$mode" \
      --runs 300 --shots 50 100 200 500 --seed 123 \
      --output-prefix "results/diagnostics/${name}" \
      > "results/diagnostics/${name}.terminal.json"
  done
done

# Separately shift just the link or just local errors to identify the driver.
for mode in link_shift local_shift; do
  name="layered12_${mode}"
  echo "===== ${name} ====="
  python -m qbridge.diagnostics \
    --family layered --qubits 12 --truth-mode "$mode" \
    --runs 300 --shots 50 100 200 500 --seed 123 \
    --output-prefix "results/diagnostics/${name}" \
    > "results/diagnostics/${name}.terminal.json"
done

python scripts/summarize_m2.py
# On macOS 'zip' is present by default. JSON and CSV are only the generated data.
( cd results && zip -q -r QBridge-M2-Diagnostic-Results.zip diagnostics )
echo "Results archive: results/QBridge-M2-Diagnostic-Results.zip"
