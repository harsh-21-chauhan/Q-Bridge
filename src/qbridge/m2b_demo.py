"""Single-example teaching demo of M2B, with an audit-friendly JSON trace.

Run: python -m qbridge.m2b_demo --family layered --qubits 6 --shots 100
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from .bayes import DEFAULT_PRIORS, BayesianPlanner
from .circuits import make_circuit
from .loss import PlacementModel
from .diagnostics import sample_truth
from .robust_priors import robust_priors
from .adaptive_calibration import run_sequential
from .robust_decision import guarded_placement


def demonstrate(family: str, n_qubits: int, shots: int, seed: int, truth_mode: str) -> dict:
    rng = np.random.default_rng(seed)
    model = PlacementModel(make_circuit(n_qubits, family))
    # Hidden simulated truth is used to generate measurement outcomes only.
    truth = sample_truth(rng, truth_mode)
    stream = rng.random((3, shots)) < np.array(truth)[:, None]
    original = BayesianPlanner(model)
    incumbent, _ = original.recommend(DEFAULT_PRIORS)
    beliefs = robust_priors()
    experiment = run_sequential(model, stream, shots, priors=beliefs)
    decision = guarded_placement(model, experiment["posterior"], incumbent, seed=seed)
    # All oracle information below is for grading, AFTER decision is selected.
    actual = model.losses(truth)
    oracle = float(actual.min())
    selected_idx = decision["chosen_index"]
    return {
        "mode": "SIMULATED quantum calibration (not real hardware)",
        "circuit": family, "qubits": n_qubits, "budget": shots, "seed": seed,
        "initial_means": [float(p.mean) for p in DEFAULT_PRIORS],
        "calibration_trace": experiment["trace"],
        "final_posterior_means": list(experiment["posterior_means"]),
        "used_shots_by_group": list(experiment["used_shots"]),
        "original_placement": list(model.mappings[incumbent]),
        "unguarded_placement": list(model.mappings[experiment["chosen_index"]]),
        "guarded_placement": list(model.mappings[selected_idx]),
        "switch_analysis": {k: v for k, v in decision.items() if k not in {"chosen_index", "candidate_index"}},
        "simulator_only_grading": {
            "true_error_rates": list(truth),
            "oracle_loss": oracle,
            "selected_actual_loss": float(actual[selected_idx]),
            "decision_regret": max(0., float(actual[selected_idx]) - oracle),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["ghz", "layered", "star"], default="layered")
    parser.add_argument("--qubits", type=int, default=6)
    parser.add_argument("--shots", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--truth-mode", choices=["prior", "shifted", "link_shift", "local_shift"], default="shifted")
    parser.add_argument("--output", default="results/m2b/single_demo.json")
    args = parser.parse_args()
    answer = demonstrate(args.family, args.qubits, args.shots, args.seed, args.truth_mode)
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(answer, indent=2), encoding="utf-8")
    print(json.dumps(answer, indent=2))
    print(f"Saved: {dest}")

if __name__ == "__main__":
    main()
