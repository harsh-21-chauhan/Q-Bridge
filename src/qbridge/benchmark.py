"""Evaluate calibration choices across many *simulated* hardware environments.

Each run is one imaginary hardware environment with hidden error probabilities.
Every calibration policy receives the same circuit, priors and shot budget.
The no-calibration policy is an additional zero-shot diagnostic baseline.
"""
from dataclasses import dataclass
import numpy as np
from .bayes import DEFAULT_PRIORS, BayesianPlanner
from .loss import PlacementModel
from .experiment import measure_binomial

POLICIES = ("evsi", "random", "fixed_a", "max_prior_variance", "no_calibration")


def _variance(a, b):
    """Uncertainty of Beta(a,b); higher variance means a less certain estimate."""
    return a * b / ((a + b) ** 2 * (a + b + 1))


def benchmark(model: PlacementModel, runs: int = 30, shots: int = 100, seed: int = 123,
              truth_mode: str = "prior") -> dict:
    if runs < 1:
        raise ValueError("runs must be >=1")
    if truth_mode not in {"prior", "shifted"}:
        raise ValueError("truth_mode must be 'prior' or 'shifted'")
    # All methods share the exact SAME placement-evaluation code.
    # Only the choice of which parameter to measure differs.
    planner = BayesianPlanner(model)
    # EVSI = expected improvement in the final placement decision if we measure
    # one noise group. With a fixed circuit/prior/budget, this choice is fixed
    # across runs. M1 does NOT learn between independent simulated worlds.
    evsi_group, evsi_scores = planner.select(DEFAULT_PRIORS, shots)
    variances = [_variance(p.alpha, p.beta) for p in DEFAULT_PRIORS]
    variance_group = int(np.argmax(variances))
    rng = np.random.default_rng(seed)
    regrets = {name: [] for name in POLICIES}
    task_losses = {name: [] for name in POLICIES}
    selected_groups = {name: [0, 0, 0] for name in POLICIES}
    for run in range(runs):
        # Ground-truth noise parameters exist only in the simulator.
        # Real calibration algorithms must infer them from measured data.
        if truth_mode == "prior":
            truth = tuple(float(rng.beta(p.alpha, p.beta)) for p in DEFAULT_PRIORS)
        else:
            # An explicit out-of-prior stress test, not evidence of hardware accuracy.
            truth = tuple(float(x) for x in rng.uniform([0.005, 0.015, 0.07], [0.05, 0.075, 0.20]))
        # "Oracle" uses the hidden true errors to find the best placement.
        # It is ONLY used to grade policies, NEVER to choose calibration.
        oracle = model.best_placement(truth)[1]
        # Common random numbers: same binomial observation whenever a policy
        # chooses the same calibration group in this scenario.
        calibration_seeds = rng.integers(0, 2**31, size=3)
        observations = [measure_binomial(truth[g], shots, np.random.default_rng(int(calibration_seeds[g]))) for g in range(3)]
        # Random baseline chooses one of A / B / remote for this one scenario.
        random_group = int(rng.integers(0, 3))
        for policy in POLICIES:
            # Start every policy from identical priors. Then update only the
            # parameter that policy chose to measure, using the same shot count.
            # This makes policy comparisons meaningful.
            if policy == "no_calibration":
                posterior = DEFAULT_PRIORS
            else:
                group = {"evsi": evsi_group, "random": random_group,
                         "fixed_a": 0, "max_prior_variance": variance_group}[policy]
                selected_groups[policy][group] += 1
                updated = list(DEFAULT_PRIORS)
                updated[group] = updated[group].updated(observations[group], shots)
                posterior = tuple(updated)
            # Choose the placement minimizing EXPECTED task loss with the
            # current Bayesian beliefs, not with the hidden true parameters.
            chosen = planner.recommend(posterior)[0]
            task_loss = float(model.losses(truth)[chosen])
            task_losses[policy].append(task_loss)
            # Regret measures the cost of choosing a suboptimal placement.
            # Regret is zero if the policy matches the oracle's best task loss.
            regrets[policy].append(max(0, task_loss - oracle))
    return {
        "circuit": model.circuit.family, "n_qubits": model.circuit.n_qubits,
        "runs": runs, "shots": shots, "truth_mode": truth_mode,
        "evsi": evsi_scores,
        "policies": {p: {
            "mean_regret": float(np.mean(regrets[p])),
            "mean_task_loss": float(np.mean(task_losses[p])),
            "regret_std": float(np.std(regrets[p], ddof=1)) if runs > 1 else 0.0,
            "calibration_counts": dict(zip(("local_a", "local_b", "remote"), selected_groups[p]))
        } for p in POLICIES}
    }
