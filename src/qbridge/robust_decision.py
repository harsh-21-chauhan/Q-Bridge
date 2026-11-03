"""Guard an uncertain placement switch without inspecting hidden truth.

We retain the prior (incumbent) placement unless posterior evidence favors
switching strongly enough. This deliberately trades a chance of missing an
improvement for fewer potentially harmful switches. It MUST be benchmarked.
"""
from __future__ import annotations
import numpy as np
from .adaptive_calibration import MixturePlanner, Posterior
from .loss import PlacementModel


def _losses_for_two(model: PlacementModel, indices: tuple[int, int], params: np.ndarray) -> np.ndarray:
    """Vectorized exact parity loss for two placements across posterior draws.

    params shape (draws, 3); returns (draws, 2). Each draw represents
    uncertainty about noise, NOT a new physical quantum measurement.
    """
    counts = model.counts[list(indices)]  # (2, n_stabilizers, 3, 2)
    attenuation = np.ones((len(params), 2, model.circuit.n_qubits))
    for g in range(3):
        one = counts[:, :, g, 0][None, :, :]
        two = counts[:, :, g, 1][None, :, :]
        p = params[:, g, None, None]
        attenuation *= (1 - p) ** one * (1 - 2 * p) ** two
    return ((1 - attenuation) / 2).mean(axis=2)


def guarded_placement(
    model: PlacementModel,
    posterior: Posterior,
    incumbent_index: int,
    *,
    minimum_probability: float = 0.75,
    posterior_draws: int = 512,
    seed: int = 2026,
) -> dict:
    """Use expected task loss + uncertainty about a potential switch.

    Bayesian best is always computed by expected loss. If it differs from
    incumbent, accept only when sampled P(new loss < incumbent loss) exceeds
    threshold. Decision never accesses simulated truth; regret is external.
    """
    if not 0.5 <= minimum_probability <= 1.0:
        raise ValueError("minimum_probability must be in [0.5, 1]")
    if posterior_draws < 64:
        raise ValueError("posterior_draws must be >=64")
    planner = MixturePlanner(model)
    expected_losses = planner.expected_losses(posterior)
    candidate_index = int(np.argmin(expected_losses))
    prior_loss = float(expected_losses[incumbent_index])
    candidate_loss = float(expected_losses[candidate_index])

    if candidate_index == incumbent_index or prior_loss - candidate_loss <= 1e-10:
        return {
            "chosen_index": int(incumbent_index), "candidate_index": candidate_index,
            "switched": False, "posterior_probability_better": 0.5,
            "expected_gain": max(0., prior_loss - candidate_loss),
            "reason": "No clear positive expected-loss improvement",
        }

    rng = np.random.default_rng(seed)
    params = np.column_stack([p.sample(rng, posterior_draws) for p in posterior])
    two_losses = _losses_for_two(model, (incumbent_index, candidate_index), params)
    # For equal-loss draws, do not count a win for the new placement.
    p_better = float(np.mean(two_losses[:, 1] < two_losses[:, 0] - 1e-12))
    switch = p_better >= minimum_probability
    return {
        "chosen_index": int(candidate_index if switch else incumbent_index),
        "candidate_index": candidate_index,
        "switched": bool(switch),
        "posterior_probability_better": p_better,
        "expected_gain": prior_loss - candidate_loss,
        "reason": "Switch supported by posterior" if switch else "Uncertain switch: retain incumbent",
    }
