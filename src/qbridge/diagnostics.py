"""Milestone 2: explain *why* calibration helps or harms placement choices.

Research-only diagnostics. This does NOT modify Bayesian planning or the
experiment algorithm. Hidden true noise and the oracle are used ONLY for
benchmark grading, never by the calibration-selection policies.

Run: python -m qbridge.diagnostics --family layered --qubits 12 \
       --truth-mode shifted --runs 300 --shots 50 100 200 500 \
       --output-prefix results/diagnostics/layered12_shifted
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_dist
from scipy.stats import betabinom

from .bayes import DEFAULT_PRIORS, BayesianPlanner
from .benchmark import POLICIES, _variance
from .circuits import make_circuit
from .loss import GROUPS, PlacementModel

# This is an ANALYSIS setting, not a physical error threshold.
EPS = 1e-10


def sample_truth(rng: np.random.Generator, mode: str) -> tuple[float, float, float]:
    """Draw hidden simulated hardware errors; never show these to the planner.

    Prior: hardware matches our stated beliefs.
    Link/local/both shift: controlled tests of wrong prior assumptions.
    """
    prior = np.array([rng.beta(p.alpha, p.beta) for p in DEFAULT_PRIORS], dtype=float)
    if mode in {"local_shift", "shifted"}:
        prior[0:2] = rng.uniform([0.005, 0.015], [0.05, 0.075])
    if mode in {"link_shift", "shifted"}:
        prior[2] = rng.uniform(0.07, 0.20)
    return tuple(float(x) for x in prior)


def _bootstrap_mean_ci(values: np.ndarray, seed: int, repetitions: int = 1200) -> list[float]:
    """Percentile bootstrap CI over independent simulated hardware scenarios.

    For policy comparisons pass paired, per-scenario regret differences.
    The interval describes simulation sampling variability, not hardware validity.
    """
    arr = np.asarray(values, dtype=float)
    if len(arr) == 1:
        return [float(arr[0]), float(arr[0])]
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(arr), size=(repetitions, len(arr)))
    means = arr[indices].mean(axis=1)
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def _distinct_margin(losses: np.ndarray) -> tuple[float, int]:
    """Gap to next DISTINCT placement loss; report number of tied bests too.

    A normal top-two gap can be zero just because several mappings tie.
    """
    minimum = float(np.min(losses))
    delta = np.asarray(losses) - minimum
    distinct = delta[delta > EPS]
    gap = float(np.min(distinct)) if len(distinct) else 0.0
    tied = int(np.count_nonzero(delta <= EPS))
    return gap, tied


def _mean(rows: list[dict], field: str) -> float:
    return float(np.mean([r[field] for r in rows]))


def diagnose(
    model: PlacementModel,
    *,
    runs: int = 300,
    shots: tuple[int, ...] = (50, 100, 200, 500),
    seed: int = 123,
    truth_mode: str = "prior",
) -> tuple[dict, list[dict]]:
    """Return an aggregate JSON-friendly summary and raw trial rows.

    Every shot budget sees the SAME underlying hardware scenario and uses a
    prefix of the SAME random Bernoulli samples. The policies see exactly the
    same calibration outcomes when they choose the same noise parameter.
    """
    if runs < 2:
        raise ValueError("runs must be >= 2 for meaningful uncertainty intervals")
    if truth_mode not in {"prior", "shifted", "link_shift", "local_shift"}:
        raise ValueError("invalid truth_mode")
    if not shots or any(s < 1 or s > 1000 for s in shots):
        raise ValueError("shot budgets must be 1..1000")
    shot_budgets = tuple(sorted(set(shots)))

    planner = BayesianPlanner(model)
    prior_means = np.array([p.mean for p in DEFAULT_PRIORS])
    prior_stds = np.sqrt([_variance(p.alpha, p.beta) for p in DEFAULT_PRIORS])
    prior_intervals = np.array([
        beta_dist.ppf([0.025, 0.975], p.alpha, p.beta) for p in DEFAULT_PRIORS
    ])
    # Run calibration rankings once per budget: fixed priors and circuit.
    evsi = {str(b): planner.select(DEFAULT_PRIORS, b) for b in shot_budgets}
    variance_group = int(np.argmax(prior_stds))
    no_cal_idx, _ = planner.recommend(DEFAULT_PRIORS)
    no_cal_mapping = model.mappings[no_cal_idx]
    rng = np.random.default_rng(seed)
    raw: list[dict] = []
    cases: list[dict] = []

    for run in range(runs):
        truth = np.array(sample_truth(rng, truth_mode))
        actual_losses = model.losses(tuple(truth))
        oracle_loss = float(np.min(actual_losses))
        prior_loss = float(actual_losses[no_cal_idx])
        prior_regret = max(0.0, prior_loss - oracle_loss)
        true_margin, n_tied = _distinct_margin(actual_losses)
        z = (truth - prior_means) / prior_stds
        outside = (truth < prior_intervals[:, 0]) | (truth > prior_intervals[:, 1])

        # Counterfactual DIAGNOSTIC ONLY (not accessible to Q-Bridge):
        # If one true noise parameter were revealed, how would a point-estimate
        # placement change? This isolates which noise parameter matters.
        sensitivity = []
        for g in range(3):
            point = prior_means.copy()
            point[g] = truth[g]
            hypothetical_idx = int(np.argmin(model.losses(tuple(point))))
            hypothetical_regret = max(0.0, float(actual_losses[hypothetical_idx]) - oracle_loss)
            sensitivity.append({
                "changed": int(hypothetical_idx != no_cal_idx),
                "regret_gain": prior_regret - hypothetical_regret,
            })

        # Simulate INDIVIDUAL Bernoulli shots so larger budgets reuse the
        # previous shots, rather than changing the simulated world.
        # Each noise group has its own independent stream.
        uniforms = rng.random((3, max(shot_budgets)))
        failures = np.cumsum(uniforms < truth[:, None], axis=1)
        random_group = int(rng.integers(0, 3))

        cases.append({
            "run": run,
            "prior_regret": prior_regret,
            "oracle_loss": oracle_loss,
            "margin": true_margin,
            "tied": n_tied,
            "z": z.tolist(),
            "outside": outside.tolist(),
            "sensitivity": sensitivity,
        })
        for b in shot_budgets:
            observed = failures[:, b - 1].astype(int)
            chosen_groups = {
                "evsi": evsi[str(b)][0],
                "random": random_group,
                "fixed_a": 0,
                "max_prior_variance": variance_group,
                "no_calibration": -1,
            }
            for policy in POLICIES:
                group = chosen_groups[policy]
                if group == -1:
                    selected_idx = no_cal_idx
                    k = -1
                    predictive_tail = None
                else:
                    k = int(observed[group])
                    # Standard Bayesian update: failures and successes modify
                    # only the experimentally observed group's Beta posterior.
                    posterior = list(DEFAULT_PRIORS)
                    posterior[group] = posterior[group].updated(k, b)
                    selected_idx, _ = planner.recommend(tuple(posterior))
                    # Diagnostic: was the observation surprising under the
                    # CURRENT stated prior? Not itself a formal model test.
                    p = DEFAULT_PRIORS[group]
                    lower = betabinom.cdf(k, b, p.alpha, p.beta)
                    upper = betabinom.sf(k - 1, b, p.alpha, p.beta)
                    predictive_tail = float(min(1.0, 2.0 * min(lower, upper)))

                selected_loss = float(actual_losses[selected_idx])
                regret = max(0.0, selected_loss - oracle_loss)
                gain = prior_regret - regret  # positive means measurement helped
                raw.append({
                    "run": run,
                    "family": model.circuit.family,
                    "n_qubits": model.circuit.n_qubits,
                    "truth_mode": truth_mode,
                    "shots": b,
                    "policy": policy,
                    "calibration": GROUPS[group] if group >= 0 else "none",
                    "failures": k,
                    "posterior_predictive_p": predictive_tail,
                    "true_local_a": float(truth[0]),
                    "true_local_b": float(truth[1]),
                    "true_remote": float(truth[2]),
                    "prior_z_local_a": float(z[0]),
                    "prior_z_local_b": float(z[1]),
                    "prior_z_remote": float(z[2]),
                    "oracle_loss": oracle_loss,
                    "prior_loss": prior_loss,
                    "actual_selected_loss": selected_loss,
                    "prior_regret": prior_regret,
                    "regret": regret,
                    "gain_vs_no_cal": gain,
                    "true_margin_to_next_distinct": true_margin,
                    "number_tied_oracle_placements": n_tied,
                    "switched": int(selected_idx != no_cal_idx),
                    "helped": int(gain > EPS),
                    "harmed": int(gain < -EPS),
                    "chosen_placement": "".join(str(v) for v in model.mappings[selected_idx]),
                    "prior_placement": "".join(str(v) for v in no_cal_mapping),
                })

    report = {
        "description": "M2 diagnostic; simulated noise, NOT evidence of real hardware accuracy",
        "settings": {
            "family": model.circuit.family,
            "qubits": model.circuit.n_qubits,
            "cx_gates": model.circuit.cx_count,
            "placements": len(model.mappings),
            "runs": runs,
            "seed": seed,
            "shots": list(shot_budgets),
            "truth_mode": truth_mode,
            "prior_means": dict(zip(GROUPS, map(float, prior_means))),
        },
        "diagnostics": {
            "prior_mismatch": {
                GROUPS[g]: {
                    "mean_abs_z_score": float(np.mean([abs(c["z"][g]) for c in cases])),
                    "outside_prior_95_percent_rate": float(np.mean([c["outside"][g] for c in cases])),
                } for g in range(3)
            },
            "placement_geometry": {
                "no_calibration_oracle_optimal_rate": float(np.mean([c["prior_regret"] <= EPS for c in cases])),
                "mean_oracle_regret_no_calibration": float(np.mean([c["prior_regret"] for c in cases])),
                "mean_margin_to_next_distinct_loss": float(np.mean([c["margin"] for c in cases])),
                "fraction_multiple_tied_oracle_placements": float(np.mean([c["tied"] > 1 for c in cases])),
            },
            "perfect_one_parameter_counterfactual": {
                GROUPS[g]: {
                    "placement_change_rate": float(np.mean([c["sensitivity"][g]["changed"] for c in cases])),
                    "mean_regret_gain_vs_no_cal": float(np.mean([c["sensitivity"][g]["regret_gain"] for c in cases])),
                } for g in range(3)
            },
        },
        "budgets": {},
    }

    # Aggregation: compare policies ON THE SAME environments (paired analysis).
    for b in shot_budgets:
        by_policy = {p: [r for r in raw if r["shots"] == b and r["policy"] == p] for p in POLICIES}
        selected, scores = evsi[str(b)]
        result = {"evsi_selected_calibration": GROUPS[selected], "evsi_predicted_value": scores, "policies": {}, "paired_comparisons": {}}
        for i, policy in enumerate(POLICIES):
            subset = by_policy[policy]
            regret = np.array([r["regret"] for r in subset])
            result["policies"][policy] = {
                "mean_regret": float(regret.mean()),
                "regret_ci95": _bootstrap_mean_ci(regret, seed + 10000 * b + i),
                "mean_task_loss": _mean(subset, "actual_selected_loss"),
                "oracle_optimal_rate": float(np.mean(regret <= EPS)),
                "placement_switch_rate": _mean(subset, "switched"),
                "helped_rate": _mean(subset, "helped"),
                "harmed_rate": _mean(subset, "harmed"),
                "mean_gain_vs_no_cal": _mean(subset, "gain_vs_no_cal"),
                "unexpected_calibration_outcome_rate": float(np.mean([
                    r["posterior_predictive_p"] < 0.05 for r in subset
                ])) if policy != "no_calibration" else None,
            }
        for i, comparator in enumerate(("random", "fixed_a", "max_prior_variance", "no_calibration")):
            difference = np.array([a["regret"] - c["regret"] for a, c in zip(by_policy["evsi"], by_policy[comparator])])
            result["paired_comparisons"][f"evsi_minus_{comparator}"] = {
                "mean_regret_difference": float(difference.mean()),
                "ci95": _bootstrap_mean_ci(difference, seed + 10000 * b + 100 + i),
                "interpretation": "negative favors EVSI; interval crossing 0 is inconclusive",
            }
        report["budgets"][str(b)] = result
    return report, raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose Q-Bridge calibration robustness (simulation only)")
    parser.add_argument("--family", choices=("ghz", "layered", "star"), default="layered")
    parser.add_argument("--qubits", choices=(6, 12), type=int, default=6)
    parser.add_argument("--truth-mode", choices=("prior", "link_shift", "local_shift", "shifted"), default="prior")
    parser.add_argument("--shots", nargs="+", type=int, default=[50, 100, 200, 500])
    parser.add_argument("--runs", type=int, default=300)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--output-prefix", type=str, default="results/diagnostics/experiment")
    args = parser.parse_args()

    model = PlacementModel(make_circuit(args.qubits, args.family))
    report, rows = diagnose(model, runs=args.runs, shots=tuple(args.shots), seed=args.seed, truth_mode=args.truth_mode)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = prefix.with_suffix(".json"), prefix.with_suffix(".csv")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # Compact terminal output: easier to share than hundreds of trial rows.
    compact = {
        "settings": report["settings"],
        "prior_mismatch": report["diagnostics"]["prior_mismatch"],
        "placement_geometry": report["diagnostics"]["placement_geometry"],
        "perfect_one_parameter_counterfactual": report["diagnostics"]["perfect_one_parameter_counterfactual"],
        "budgets": {
            b: {
                "evsi_selected": v["evsi_selected_calibration"],
                "mean_regret": {p: round(s["mean_regret"], 7) for p, s in v["policies"].items()},
                "evsi_switch_rate": v["policies"]["evsi"]["placement_switch_rate"],
                "evsi_helped_rate": v["policies"]["evsi"]["helped_rate"],
                "evsi_harmed_rate": v["policies"]["evsi"]["harmed_rate"],
                "evsi_unexpected_calibration_outcome_rate": v["policies"]["evsi"]["unexpected_calibration_outcome_rate"],
                "evsi_minus_no_cal": v["paired_comparisons"]["evsi_minus_no_calibration"],
                "evsi_minus_random": v["paired_comparisons"]["evsi_minus_random"],
            } for b, v in report["budgets"].items()
        },
        "full_json": str(json_path),
        "trial_csv": str(csv_path),
    }
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
