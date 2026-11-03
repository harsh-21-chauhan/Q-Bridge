"""M2C: held-out comparison of calibration and placement-guard policies.

Run with: python -m qbridge.m2c_validation --help

No original M1/M2A/M2B algorithm is altered by this module. The sole new
candidate is adaptive calibration using ORIGINAL priors, followed by a
moderate 60% posterior guard. A 75% original-prior guard is also evaluated.

IMPORTANT: All 'true' noise rates are simulator-only grading variables.
Policies see only shot outcomes and posterior beliefs, never hidden truth.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .adaptive_calibration import default_as_mixtures, run_sequential
from .bayes import BayesianPlanner, DEFAULT_PRIORS
from .circuits import make_circuit
from .diagnostics import sample_truth, _bootstrap_mean_ci
from .loss import GROUPS, PlacementModel
from .robust_decision import guarded_placement
from .robust_priors import robust_priors

# Predeclare policies BEFORE seeing held-out data. Don't tune thresholds on
# these test results, or the test will cease to be a proper holdout.
POLICIES = (
    "no_calibration",                 # Zero-shot diagnostic reference, not an equal-budget policy
    "original_evsi",                 # M1: all shots on one EVSI-selected group
    "random_calibration",             # Random group, full shot budget
    "fixed_split",                    # Half on EVSI's choice, half on link
    "adaptive_original",              # M2B adaptive, original Bayesian prior, no guard
    "adaptive_original_guard60",      # M2C NEW proposed final policy
    "adaptive_original_guard75",      # Control: same data, stricter guard
    "adaptive_robust_guard75",        # M2B existing mixture prior + 75% guard
)


def evaluate(
    model: PlacementModel,
    *,
    runs: int = 100,
    shots: int = 100,
    seed: int = 20261104,
    truth_mode: str = "shifted",
    guard_draws: int = 512,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run paired, equal-shot calibration comparisons on NEW simulated cases.

    Each trial has one hidden hardware-noise vector and a common Bernoulli
    measurement stream. Policies that calibrate a given group receive the
    SAME early shot outcomes. Only no_calibration spends zero shots.

    The 60% and 75% original-prior guards share EXACTLY the same posterior
    and posterior Monte Carlo draws. This isolates the threshold effect.
    """
    if runs < 2:
        raise ValueError("runs must be at least 2")
    if not 20 <= shots <= 1000:
        raise ValueError("shot budget must be in [20, 1000]")
    if truth_mode not in ("prior", "shifted", "link_shift", "local_shift"):
        raise ValueError("Unknown truth mode")
    if guard_draws < 64:
        raise ValueError("At least 64 posterior draws required")

    planner = BayesianPlanner(model)
    incumbent, _ = planner.recommend(DEFAULT_PRIORS)
    best_group, evsi = planner.select(DEFAULT_PRIORS, shots)
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []

    for trial in range(runs):
        # Hidden truth is used only for simulated shots and grading.
        truth = sample_truth(rng, truth_mode)
        actual = model.losses(truth)
        oracle = float(actual.min())
        streams = rng.random((3, shots)) < np.asarray(truth)[:, None]

        # M1: original EVSI, all shots from one physical experiment.
        one_posterior = list(DEFAULT_PRIORS)
        k = int(np.count_nonzero(streams[best_group]))
        one_posterior[best_group] = one_posterior[best_group].updated(k, shots)
        one_index, _ = planner.recommend(tuple(one_posterior))

        # Fair stochastic baseline: one randomly chosen experiment, same budget.
        random_group = int(rng.integers(0, 3))
        random_posterior = list(DEFAULT_PRIORS)
        random_posterior[random_group] = random_posterior[random_group].updated(
            int(np.count_nonzero(streams[random_group])), shots
        )
        random_index, _ = planner.recommend(tuple(random_posterior))

        # Fixed split: full budget, split over two relevant parameters.
        other = 2 if best_group != 2 else 1
        split = [0, 0, 0]
        split[best_group] = shots // 2
        split[other] = shots - split[best_group]
        split_posterior = list(DEFAULT_PRIORS)
        for group, num in enumerate(split):
            if num:
                split_posterior[group] = split_posterior[group].updated(
                    int(np.count_nonzero(streams[group, :num])), num
                )
        split_index, _ = planner.recommend(tuple(split_posterior))

        # Proposed policy: same pilot/adaptive allocation, ORIGINAL priors.
        adaptive = run_sequential(model, streams, shots, priors=default_as_mixtures())

        # Guard probability is estimated once, on the SAME posterior draws.
        # This makes the guard60-vs-guard75 comparison mathematically paired.
        guard60 = guarded_placement(
            model, adaptive["posterior"], incumbent,
            minimum_probability=0.60, posterior_draws=guard_draws,
            seed=seed * 100_003 + trial,
        )
        candidate = int(guard60["candidate_index"])
        prob = float(guard60["posterior_probability_better"])
        gain = float(guard60["expected_gain"])
        can_switch = candidate != incumbent and gain > 1e-10
        idx75 = candidate if (can_switch and prob >= 0.75) else incumbent

        # Original M2B fully-robust baseline. Same simulated shots, different
        # prior and resulting allocation, with identical risk threshold 75%.
        robust = run_sequential(model, streams, shots, priors=robust_priors())
        robust_guard = guarded_placement(
            model, robust["posterior"], incumbent,
            minimum_probability=0.75, posterior_draws=guard_draws,
            seed=seed * 100_003 + trial + 1_000_000,
        )

        decisions = {
            "no_calibration": incumbent,
            "original_evsi": one_index,
            "random_calibration": random_index,
            "fixed_split": split_index,
            "adaptive_original": int(adaptive["chosen_index"]),
            "adaptive_original_guard60": int(guard60["chosen_index"]),
            "adaptive_original_guard75": int(idx75),
            "adaptive_robust_guard75": int(robust_guard["chosen_index"]),
        }
        # Exclude numerical ties from help/harm counts.
        base_loss = float(actual[incumbent])
        for policy, index in decisions.items():
            loss = float(actual[index])
            rows.append({
                "trial": trial,
                "policy": policy,
                "family": model.circuit.family,
                "qubits": model.circuit.n_qubits,
                "truth_mode": truth_mode,
                "shot_budget": shots,
                "shots_spent": 0 if policy == "no_calibration" else shots,
                "regret": max(0.0, loss - oracle),
                "task_loss": loss,
                "oracle_loss": oracle,
                "switched": int(index != incumbent),
                "helped": int(loss < base_loss - 1e-10),
                "harmed": int(loss > base_loss + 1e-10),
                "placement": "".join(map(str, model.mappings[index])),
                "true_local_a": float(truth[0]),
                "true_local_b": float(truth[1]),
                "true_remote": float(truth[2]),
                # 0.5 from current guard when no switch is proposed is a
                # placeholder: omit it instead of calling it '50% evidence'.
                "posterior_probability_better": (
                    prob if (can_switch and policy in {
                        "adaptive_original_guard60", "adaptive_original_guard75"}) else None
                ),
                "expected_gain": gain if (can_switch and policy in {
                    "adaptive_original_guard60", "adaptive_original_guard75"}) else None,
                "calibration_trace": (
                    json.dumps(adaptive["trace"]) if policy in {
                        "adaptive_original", "adaptive_original_guard60",
                        "adaptive_original_guard75"} else
                    json.dumps(robust["trace"]) if policy == "adaptive_robust_guard75"
                    else None
                ),
            })

    # All methods share aligned trial order, so paired bootstrap is valid.
    series = {name: [r for r in rows if r["policy"] == name] for name in POLICIES}
    policy_stats: dict[str, Any] = {}
    for i, name in enumerate(POLICIES):
        subset = series[name]
        reg = np.array([r["regret"] for r in subset])
        policy_stats[name] = {
            "mean_regret": float(reg.mean()),
            "regret_95ci": _bootstrap_mean_ci(reg, seed + 100 + i),
            "mean_task_loss": float(np.mean([r["task_loss"] for r in subset])),
            "switch_rate": float(np.mean([r["switched"] for r in subset])),
            "help_rate": float(np.mean([r["helped"] for r in subset])),
            "harm_rate": float(np.mean([r["harmed"] for r in subset])),
        }

    # Positive reduction means proposed guard60 had LOWER regret.
    candidate_reg = np.array([r["regret"] for r in series["adaptive_original_guard60"]])
    paired: dict[str, Any] = {}
    for i, name in enumerate(POLICIES):
        if name == "adaptive_original_guard60":
            continue
        reference = np.array([r["regret"] for r in series[name]])
        reduction = reference - candidate_reg
        paired[name] = {
            "mean_regret_reduction_vs_candidate": float(reduction.mean()),
            "paired_95ci": _bootstrap_mean_ci(reduction, seed + 200 + i),
        }

    return {
        "description": "Held-out SIMULATED benchmark; not evidence from physical quantum hardware",
        "settings": {
            "family": model.circuit.family,
            "qubits": model.circuit.n_qubits,
            "runs": runs,
            "shots": shots,
            "seed": seed,
            "truth_mode": truth_mode,
            "guard_draws": guard_draws,
            "candidate": "adaptive_original_guard60",
            "fixed_split_groups": {GROUPS[i]: n for i, n in enumerate(split) if n},
            "initial_evsi_choice": GROUPS[best_group],
        },
        "policies": policy_stats,
        "paired_comparisons": paired,
    }, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["ghz", "layered", "star"], default="layered")
    parser.add_argument("--qubits", type=int, choices=[6, 12], default=6)
    parser.add_argument("--truth-mode", choices=["prior", "shifted", "local_shift", "link_shift"], default="shifted")
    parser.add_argument("--shots", type=int, default=100)
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--guard-draws", type=int, default=512)
    parser.add_argument("--output-prefix", default="results/m2c/single")
    args = parser.parse_args()
    result, rows = evaluate(
        PlacementModel(make_circuit(args.qubits, args.family)),
        shots=args.shots, runs=args.runs, seed=args.seed,
        truth_mode=args.truth_mode, guard_draws=args.guard_draws,
    )
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with prefix.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {prefix.with_suffix('.json')} and {prefix.with_suffix('.csv')}")
    print("Policy                  Mean regret     Harm rate")
    for name, stat in result["policies"].items():
        print(f"{name:<26}{stat['mean_regret']:.7f}      {stat['harm_rate']:.1%}")
    print("Paired improvements of candidate (positive is better):")
    for name, entry in result["paired_comparisons"].items():
        print(f"  versus {name:<25} {entry['mean_regret_reduction_vs_candidate']:+.7f}  {entry['paired_95ci']}")


if __name__ == "__main__":
    main()
