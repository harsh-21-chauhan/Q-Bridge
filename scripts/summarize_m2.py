"""Summarize all completed diagnostic JSON reports as one compact table."""
import csv
import json
from pathlib import Path

root = Path("results/diagnostics")
rows = []
for path in sorted(root.glob("*.json")):
    if path.name.endswith(".terminal.json"):
        continue
    data = json.loads(path.read_text())
    settings = data["settings"]
    for budget, stats in data["budgets"].items():
        pol = stats["policies"]
        diff = stats["paired_comparisons"]["evsi_minus_no_calibration"]
        rows.append({
            "circuit": settings["family"],
            "qubits": settings["qubits"],
            "truth_mode": settings["truth_mode"],
            "shots": int(budget),
            "evsi_calibration": stats["evsi_selected_calibration"],
            "evsi_regret": round(pol["evsi"]["mean_regret"], 7),
            "random_regret": round(pol["random"]["mean_regret"], 7),
            "no_cal_regret": round(pol["no_calibration"]["mean_regret"], 7),
            "evsi_minus_no_cal": round(diff["mean_regret_difference"], 7),
            "evsi_vs_no_cal_ci_low": round(diff["ci95"][0], 7),
            "evsi_vs_no_cal_ci_high": round(diff["ci95"][1], 7),
            "evsi_switch_rate": round(pol["evsi"]["placement_switch_rate"], 3),
            "evsi_helped_rate": round(pol["evsi"]["helped_rate"], 3),
            "evsi_harmed_rate": round(pol["evsi"]["harmed_rate"], 3),
        })
if not rows:
    raise SystemExit("No diagnostic JSON reports found in results/diagnostics/")
out = root / "summary.csv"
with out.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"Saved {len(rows)} comparison rows to {out}")
for r in rows:
    if r["shots"] == 100:
        label = f"{r['qubits']}q {r['circuit']} {r['truth_mode']}"
        print(f"{label:27} EVSI={r['evsi_regret']:.6f} random={r['random_regret']:.6f} no_cal={r['no_cal_regret']:.6f} "
              f"switch={r['evsi_switch_rate']:.2f} help={r['evsi_helped_rate']:.2f} harm={r['evsi_harmed_rate']:.2f}")
