"""Held-out M2B comparison with fair budgets and paired simulated environments.

This file is separate from M1/M2A: neither existing algorithms nor tests
are replaced. Run using `python -m qbridge.robustness_benchmark ...`.

IMPORTANT: hidden simulator truth is ONLY used for generating binary shots and
for evaluating final loss/regret, never as an input to any decision policy.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import time
import numpy as np
from .bayes import DEFAULT_PRIORS, BayesianPlanner
from .adaptive_calibration import MixturePlanner, default_as_mixtures, run_sequential
from .robust_priors import robust_priors
from .robust_decision import guarded_placement
from .circuits import make_circuit
from .loss import GROUPS, PlacementModel
from .diagnostics import sample_truth, _bootstrap_mean_ci

POLICIES = (
    "no_calibration", "original_evsi", "random_calibration", "fixed_split",
    "adaptive_original_priors", "adaptive_robust_priors", "adaptive_robust_guard",
)


def _update_simple(priors, stream: np.ndarray, allocations: list[int]):
    """All groups get EXACTLY their allocated prefix shots, if allocated."""
    updated = list(priors)
    for g, shots in enumerate(allocations):
        if shots:
            failures = int(np.count_nonzero(stream[g, :shots]))
            updated[g] = priors[g].updated(failures, shots)
    return tuple(updated)


def evaluate(
    model: PlacementModel,
    *,
    runs: int = 100,
    shots: int = 100,
    seed: int = 4567,
    truth_mode: str = "shifted",
    guard_threshold: float = 0.75,
    guard_draws: int = 512,
    trust_weight: float = 0.75,
) -> tuple[dict, list[dict]]:
    """Return complete summary and policy results, paired by scenario.

    Each simulated environment is new. All policies use a shared binary
    stream for each parameter; a policy may only consume up to its budget.
    Common random numbers reduce variance in policy comparisons.
    """
    if runs < 2 or not 20 <= shots <= 1000:
        raise ValueError("runs >=2, shots between 20 and 1000 required")
    if truth_mode not in {"prior", "shifted", "link_shift", "local_shift"}:
        raise ValueError("invalid truth mode")
    if not 0.5 <= guard_threshold <= 1.0:
        raise ValueError("guard_threshold must be in [0.5,1]")

    rng = np.random.default_rng(seed)
    original_planner = BayesianPlanner(model)
    mixture_planner = MixturePlanner(model)
    original_mix = default_as_mixtures()
    robust = robust_priors(trust_weight=trust_weight)
    incumbent_index, _ = original_planner.recommend(DEFAULT_PRIORS)
    best_exp, evsi = original_planner.select(DEFAULT_PRIORS, shots)
    rows = []
    start = time.perf_counter()
    for run in range(runs):
        truth = sample_truth(rng, truth_mode)
        oracle = float(model.losses(truth).min())
        # Measurement randomness shared across methods. A failure is one shot
        # outcome; generated under hidden true parameters, not supplied to model.
        streams = rng.random((3, shots)) < np.asarray(truth)[:, None]
        random_group = int(rng.integers(0, 3))

        # Original EVSI and random both get the FULL budget for one parameter.
        old_update = list(DEFAULT_PRIORS)
        old_update[best_exp] = old_update[best_exp].updated(int(streams[best_exp].sum()), shots)
        original_idx, _ = original_planner.recommend(tuple(old_update))

        rand_update = list(DEFAULT_PRIORS)
        rand_update[random_group] = rand_update[random_group].updated(int(streams[random_group].sum()), shots)
        random_idx, _ = original_planner.recommend(tuple(rand_update))

        # Fixed 50/50 two-parameter policy: the original EVSI preference
        # plus the LINK (or local B if link was already preferred).
        other_group = 2 if best_exp != 2 else 1
        allocations = [0, 0, 0]
        allocations[best_exp] = shots // 2
        allocations[other_group] = shots - shots // 2
        split_post = _update_simple(DEFAULT_PRIORS, streams, allocations)
        split_idx, _ = original_planner.recommend(split_post)

        # First ablation: adaptively allocate shots, but use ORIGINAL priors.
        adaptive_standard = run_sequential(model, streams, shots, priors=original_mix)
        # Second: adaptively allocate shots, using the BROADER mixture priors.
        adaptive_robust = run_sequential(model, streams, shots, priors=robust)
        # Final: same exact measurements/posteriors, plus guarded placement.
        guarded = guarded_placement(
            model, adaptive_robust["posterior"], incumbent_index,
            minimum_probability=guard_threshold, posterior_draws=guard_draws,
            seed=seed * 1_000_003 + run,
        )

        decisions = {
            "no_calibration": incumbent_index,
            "original_evsi": original_idx,
            "random_calibration": random_idx,
            "fixed_split": split_idx,
            "adaptive_original_priors": adaptive_standard["chosen_index"],
            "adaptive_robust_priors": adaptive_robust["chosen_index"],
            "adaptive_robust_guard": guarded["chosen_index"],
        }
        actual = model.losses(truth)
        for policy, idx in decisions.items():
            decision_loss = float(actual[idx])
            rows.append({
                "run": run, "policy": policy, "truth_mode": truth_mode,
                "qubits": model.circuit.n_qubits, "family": model.circuit.family,
                "shots_budget": shots, "shots_spent": 0 if policy == "no_calibration" else shots,
                "regret": max(0.0, decision_loss - oracle),
                "task_loss": decision_loss, "oracle_loss": oracle,
                "switched_from_original": int(idx != incumbent_index),
                "helped_vs_no_calibration": int(decision_loss < float(actual[incumbent_index]) - 1e-10),
                "harmed_vs_no_calibration": int(decision_loss > float(actual[incumbent_index]) + 1e-10),
                "placement": "".join(map(str, model.mappings[idx])),
                "true_local_a": truth[0], "true_local_b": truth[1], "true_remote": truth[2],
                "guard_probability_better": guarded["posterior_probability_better"] if policy == "adaptive_robust_guard" else None,
                "calibration_trace": (
                    json.dumps(adaptive_standard["trace"]) if policy == "adaptive_original_priors" else
                    json.dumps(adaptive_robust["trace"]) if policy in {"adaptive_robust_priors", "adaptive_robust_guard"} else None
                ),
            })

    policy_rows = {policy: [r for r in rows if r["policy"] == policy] for policy in POLICIES}
    summary_policies = {}
    for i, name in enumerate(POLICIES):
        r = policy_rows[name]
        regrets = np.asarray([x["regret"] for x in r])
        summary_policies[name] = {
            "mean_regret": float(regrets.mean()),
            "regret_95ci": _bootstrap_mean_ci(regrets, seed + i),
            "mean_task_loss": float(np.mean([x["task_loss"] for x in r])),
            "switch_rate": float(np.mean([x["switched_from_original"] for x in r])),
            "help_rate": float(np.mean([x["helped_vs_no_calibration"] for x in r])),
            "harm_rate": float(np.mean([x["harmed_vs_no_calibration"] for x in r])),
        }

    base = np.asarray([r["regret"] for r in policy_rows["original_evsi"]])
    comparisons = {}
    for i, name in enumerate(POLICIES):
        if name == "original_evsi":
            continue
        competitor = np.asarray([r["regret"] for r in policy_rows[name]])
        delta = base - competitor  # positive means the NEW policy is better.
        comparisons[name] = {
            "mean_regret_reduction_vs_original_evsi": float(delta.mean()),
            "paired_95ci": _bootstrap_mean_ci(delta, seed + i + 101),
        }

    return {
        "description": "M2B controlled simulator comparison, not physical hardware evidence",
        "settings": {
            "family": model.circuit.family, "qubits": model.circuit.n_qubits,
            "runs": runs, "shots": shots, "seed": seed,
            "truth_mode": truth_mode, "guard_threshold": guard_threshold,
            "guard_draws": guard_draws, "robust_prior_trust_weight": trust_weight,
            "original_evsi_selection": GROUPS[best_exp],
            "fixed_split_groups": {GROUPS[i]: n for i, n in enumerate(allocations) if n},
            "elapsed_seconds": float(time.perf_counter() - start),
        },
        "policies": summary_policies,
        "paired_comparisons": comparisons,
    }, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["ghz", "layered", "star"], default="layered")
    parser.add_argument("--qubits", type=int, default=6)
    parser.add_argument("--shots", type=int, default=100)
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=4567)
    parser.add_argument("--truth-mode", choices=["prior", "shifted", "link_shift", "local_shift"], default="shifted")
    parser.add_argument("--guard-threshold", type=float, default=0.75)
    parser.add_argument("--guard-draws", type=int, default=512)
    parser.add_argument("--trust-weight", type=float, default=0.75)
    parser.add_argument("--output-prefix", default="results/m2b/layered6_shifted")
    args = parser.parse_args()
    model = PlacementModel(make_circuit(args.qubits, args.family))
    report, rows = evaluate(
        model, runs=args.runs, shots=args.shots, seed=args.seed,
        truth_mode=args.truth_mode, guard_threshold=args.guard_threshold,
        guard_draws=args.guard_draws, trust_weight=args.trust_weight,
    )
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with prefix.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report, indent=2))
    print(f"\nSaved: {prefix.with_suffix('.json')} and {prefix.with_suffix('.csv')}")


if __name__ == "__main__":
    main()
