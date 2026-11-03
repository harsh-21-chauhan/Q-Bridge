"""Sequential calibration with a STRICT, auditable measurement-shot budget.

The same hidden simulator parameters produce binary measurements. The planner
never receives those true parameters: it only sees 0/1 failure counts. EVSI
and placement recommendations depend exclusively on current posterior beliefs.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property, lru_cache
import numpy as np
from .bayes import BetaPrior, BayesianPlanner, DEFAULT_PRIORS, _nodes
from .circuits import CircuitSpec
from .loss import PlacementModel, GROUPS
from .robust_priors import BetaMixture, as_mixture, robust_priors

Posterior = tuple[BetaMixture, BetaMixture, BetaMixture]


class MixturePlanner(BayesianPlanner):
    """Existing Bayesian planner extended to mixture priors.

    PERFORMANCE: instead of evaluating a Beta quadrature independently for
    every (placement, observable), evaluate the distinct (n1,n2) channel
    counts once and gather them back. This matters with 924 placements.
    """

    @cached_property
    def _patterns(self):
        data = []
        for g in range(3):
            pairs = self.counts[:, :, g, :].reshape(-1, 2)
            unique, inverse = np.unique(pairs, axis=0, return_inverse=True)
            data.append((unique, inverse.reshape(self.counts.shape[:2])))
        return data

    @lru_cache(maxsize=1024)
    def _beta_moment(self, group: int, prior: BetaPrior) -> np.ndarray:
        patterns, indices = self._patterns[group]
        p, weights = _nodes(prior.alpha, prior.beta, self.degree)
        attenuation = (
            (1.0 - p[None, :]) ** patterns[:, 0, None]
            * (1.0 - 2.0 * p[None, :]) ** patterns[:, 1, None]
        )
        return (attenuation @ weights)[indices]

    def _moment(self, group: int, prior: BetaMixture) -> np.ndarray:
        return sum(w * self._beta_moment(group, p)
                   for w, p in zip(prior.weights, prior.components))

    def evsi(self, priors: Posterior, shots: int) -> dict[str, float]:
        """Compute decision-EVSI for every possible next calibration.

        Integrate against the outcome probabilities (NOT hidden truth).
        Only the selected parameter's posterior changes with each outcome.
        """
        if not 1 <= shots <= 1000:
            raise ValueError("EVSI supports 1..1000 shots")
        moments = [self._moment(g, p) for g, p in enumerate(priors)]
        initial = ((1.0 - moments[0] * moments[1] * moments[2]) / 2.0).mean(axis=1)
        before = float(initial.min())
        values = {}
        for group, name in enumerate(GROUPS):
            other = np.ones_like(moments[0])
            for j in range(3):
                if j != group:
                    other *= moments[j]
            after_expected = 0.0
            probabilities = priors[group].predictive(shots)
            for failures, probability in enumerate(probabilities):
                if probability < 1e-13:
                    continue
                posterior = priors[group].updated(failures, shots)
                moment = self._moment(group, posterior)
                candidate_loss = ((1.0 - other * moment) / 2.0).mean(axis=1)
                after_expected += float(probability) * float(candidate_loss.min())
            values[name] = float(max(0.0, before - after_expected))
        return values


@dataclass(frozen=True)
class CalibrationStep:
    stage: str
    group: str
    shots: int
    failures: int
    posterior_mean: float
    evsi_at_choice: dict[str, float] | None = None

    def to_dict(self) -> dict:
        return {
            "stage": self.stage, "group": self.group,
            "shots": self.shots, "failures": self.failures,
            "posterior_mean": self.posterior_mean,
            "evsi_at_choice": self.evsi_at_choice,
        }


def split_budget(budget: int) -> tuple[list[int], list[int]]:
    """10% A + 10% B + 20% link pilot; remaining budget in two batches.

    This split is a TESTABLE design choice, not a known optimum.
    """
    if not 20 <= budget <= 1000:
        raise ValueError("budget must be between 20 and 1000")
    a, b, link = max(1, budget // 10), max(1, budget // 10), max(1, budget // 5)
    remaining = budget - a - b - link
    batches = [remaining // 2, remaining - remaining // 2]
    assert sum((a, b, link, *batches)) == budget and min(batches) > 0
    return [a, b, link], batches


def posterior_means(priors: Posterior) -> tuple[float, float, float]:
    return tuple(p.mean for p in priors)


def calibration_from_stream(stream: np.ndarray, used: list[int], group: int, shots: int) -> int:
    """Consume the NEXT shots for one parameter, never reuse a shot in a policy.

    The benchmark shares the same pre-generated per-group random streams across
    policies (common random numbers) so comparisons have less variance.
    """
    if shots <= 0 or not 0 <= group <= 2:
        raise ValueError("invalid calibration request")
    begin = used[group]
    end = begin + shots
    if end > stream.shape[1]:
        raise ValueError("calibration exceeded available shot stream")
    failures = int(np.count_nonzero(stream[group, begin:end]))
    used[group] = end
    return failures


def run_sequential(
    model: PlacementModel,
    stream: np.ndarray,
    budget: int = 100,
    *,
    priors: Posterior | None = None,
) -> dict:
    """Pilot -> posterior updates -> two adaptive EVSI batches -> placement.

    `stream` is the BENCHMARK's private generated binary outcomes. In a real
    deployment it would be replaced by a measurement tool. No ground truth
    error values or oracle placements are passed to this function.
    """
    if stream.shape != (3, budget):
        raise ValueError("expect three binary shot streams of length budget")
    beliefs: Posterior = priors if priors is not None else robust_priors()
    planner = MixturePlanner(model)
    pilot, batches = split_budget(budget)
    used = [0, 0, 0]
    trace: list[CalibrationStep] = []

    for group, shots in enumerate(pilot):
        k = calibration_from_stream(stream, used, group, shots)
        next_beliefs = list(beliefs)
        next_beliefs[group] = beliefs[group].updated(k, shots)
        beliefs = tuple(next_beliefs)
        trace.append(CalibrationStep("pilot", GROUPS[group], shots, k, beliefs[group].mean))

    for shots in batches:
        group, scores = planner.select(beliefs, shots)
        k = calibration_from_stream(stream, used, group, shots)
        next_beliefs = list(beliefs)
        next_beliefs[group] = beliefs[group].updated(k, shots)
        beliefs = tuple(next_beliefs)
        trace.append(CalibrationStep("adaptive", GROUPS[group], shots, k,
                                     beliefs[group].mean, scores))

    chosen, expected_loss = planner.recommend(beliefs)
    assert sum(used) == budget
    return {
        "chosen_index": chosen,
        "expected_loss": expected_loss,
        "posterior": beliefs,
        "posterior_means": posterior_means(beliefs),
        "used_shots": tuple(used),
        "total_shots": sum(used),
        "trace": [step.to_dict() for step in trace],
        "pilot_shots": pilot,
        "adaptive_batches": batches,
    }


def default_as_mixtures() -> Posterior:
    """Ablation: adaptive measurements, original NON-robust priors."""
    return tuple(as_mixture(p) for p in DEFAULT_PRIORS)
