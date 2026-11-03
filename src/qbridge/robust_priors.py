"""Robust priors: a small probability that yesterday's calibration is stale.

Each error probability has a mixture of two Beta distributions:
- concentrated: what M1 believes about this hardware;
- diffuse: the same mean, but much less confidence.

This does NOT assume that errors must be high. Under contradictory observations,
Bayes' rule can automatically increase the posterior weight of the diffuse prior.
Everything remains a valid probability distribution with explicit likelihoods.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
import numpy as np
from scipy.special import logsumexp
from scipy.stats import betabinom
from .bayes import BetaPrior, DEFAULT_PRIORS


@dataclass(frozen=True)
class BetaMixture:
    components: tuple[BetaPrior, ...]
    weights: tuple[float, ...]

    def __post_init__(self):
        if not self.components or len(self.components) != len(self.weights):
            raise ValueError("provide matching nonempty components and weights")
        if not all(isfinite(w) and w >= 0 for w in self.weights):
            raise ValueError("weights must be finite nonnegative numbers")
        if not np.isclose(sum(self.weights), 1.0, atol=1e-9):
            raise ValueError("weights must sum to 1")
        if sum(self.weights) <= 0:
            raise ValueError("at least one positive weight is required")

    @property
    def mean(self) -> float:
        return float(sum(w * p.mean for w, p in zip(self.weights, self.components)))

    def predictive(self, shots: int) -> np.ndarray:
        """Probability of each possible count of failures 0..shots."""
        if shots < 0:
            raise ValueError("shots must be nonnegative")
        k = np.arange(shots + 1)
        mass = sum(w * betabinom.pmf(k, shots, p.alpha, p.beta)
                   for w, p in zip(self.weights, self.components))
        mass = np.maximum(mass, 0.0)
        return mass / mass.sum()

    def updated(self, failures: int, shots: int) -> "BetaMixture":
        """Update BOTH Beta components AND our trust in each component.

        P(component | data) is proportional to prior component weight times
        Beta-Binomial marginal likelihood of observed failure COUNT.
        """
        if shots < 0 or not (0 <= failures <= shots):
            raise ValueError("require 0 <= failures <= shots")
        log_weights = np.array([
            np.log(w) + betabinom.logpmf(failures, shots, p.alpha, p.beta)
            if w > 0 else -np.inf
            for w, p in zip(self.weights, self.components)
        ], dtype=float)
        probs = np.exp(log_weights - logsumexp(log_weights))
        new_components = tuple(p.updated(failures, shots) for p in self.components)
        return BetaMixture(new_components, tuple(float(x) for x in probs))

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        """Draw noise probabilities from our POSTERIOR (not simulator truth)."""
        index = rng.choice(len(self.weights), p=self.weights, size=size)
        samples = np.empty(size, dtype=float)
        for i, p in enumerate(self.components):
            selected = index == i
            if np.any(selected):
                samples[selected] = rng.beta(p.alpha, p.beta, size=int(selected.sum()))
        return samples


def as_mixture(prior: BetaPrior) -> BetaMixture:
    """One-component representation reproduces the original Beta prior exactly."""
    return BetaMixture((prior,), (1.0,))


def robust_priors(trust_weight: float = 0.75, diffuse_strength: float = 20.0) -> tuple[BetaMixture, ...]:
    """Construct illustrative, explicitly configurable robust priors.

    Diffuse component preserves original mean; only effective prior sample
    size changes.  This is NOT empirically fitted to quantum hardware.
    """
    if not (0.0 <= trust_weight <= 1.0):
        raise ValueError("trust_weight must be in [0,1]")
    if diffuse_strength <= 0:
        raise ValueError("diffuse_strength must be positive")
    return tuple(
        BetaMixture(
            (p, BetaPrior(p.mean * diffuse_strength, (1 - p.mean) * diffuse_strength)),
            (trust_weight, 1.0 - trust_weight),
        ) for p in DEFAULT_PRIORS
    )
