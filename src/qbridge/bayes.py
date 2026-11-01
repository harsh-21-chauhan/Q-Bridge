"""Decision-aware one-experiment Bayesian calibration selection.

Uses a truly conjugate Beta-Binomial model for an *idealized* Bernoulli
channel diagnostic. Exact integration of polynomial parity loss is via
Gauss-Jacobi quadrature; this is not LLM-estimated or fitted.
"""
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
from scipy.linalg import eigh_tridiagonal
from scipy.stats import betabinom
from .loss import PlacementModel, GROUPS


@dataclass(frozen=True)
class BetaPrior:
    alpha: float
    beta: float

    def __post_init__(self):
        if self.alpha <= 0 or self.beta <= 0:
            raise ValueError("Beta shape parameters must be positive")

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def updated(self, failures: int, shots: int) -> "BetaPrior":
        if shots < 0 or not (0 <= failures <= shots):
            raise ValueError("require 0 <= failures <= shots")
        return BetaPrior(self.alpha + failures, self.beta + shots - failures)


# Order: (QPU-A local error, QPU-B local error, remote-operation error).
# For Beta(alpha,beta), prior mean error = alpha / (alpha+beta).
# These illustrative priors mean (2%, 3%, 5%), NOT measured hardware facts.
DEFAULT_PRIORS = (BetaPrior(2, 98), BetaPrior(3, 97), BetaPrior(4, 76))


@lru_cache(maxsize=20000)
def _nodes(alpha: float, beta: float, degree: int) -> tuple[np.ndarray, np.ndarray]:
    """Stable Gauss-Jacobi quadrature for normalized Beta weights.

    Direct scipy.special.roots_jacobi weights overflow when alpha+beta is
    large. Golub-Welsch computes *normalized* weights via the first row of
    the orthogonal eigenvector matrix, avoiding beta-function normalization.
    """
    n = max(12, (degree + 2) // 2)
    a, b = beta - 1.0, alpha - 1.0  # Jacobi weight on [-1,1]
    diag = np.empty(n, dtype=float)
    for j in range(n):
        if j == 0:
            diag[j] = (b - a) / (a + b + 2.0)
        else:
            den = 2 * j + a + b
            diag[j] = (b * b - a * a) / (den * (den + 2.0))
    off = np.empty(n - 1, dtype=float)
    for j in range(1, n):
        u = 2 * j + a + b
        off[j - 1] = np.sqrt(4 * j * (j + a) * (j + b) * (j + a + b) / (u * u * (u * u - 1.0)))
    x, vectors = eigh_tridiagonal(diag, off)
    weights = vectors[0, :] ** 2
    return (x + 1.0) / 2.0, weights


class BayesianPlanner:
    def __init__(self, model: PlacementModel):
        self.model = model
        self.counts = model.counts
        self.degree = int(self.counts.sum(axis=(2, 3)).max())

    def _moment(self, group: int, prior: BetaPrior) -> np.ndarray:
        # shape placements x observables
        p, w = _nodes(prior.alpha, prior.beta, self.degree)
        one = self.counts[:, :, group, 0][..., None]
        two = self.counts[:, :, group, 1][..., None]
        factors = (1.0 - p) ** one * (1.0 - 2.0 * p) ** two
        return np.sum(factors * w, axis=-1)

    def expected_losses(self, priors: tuple[BetaPrior, BetaPrior, BetaPrior]) -> np.ndarray:
        """Expected parity-error loss of EACH placement under our uncertainty."""
        factors = np.ones(self.counts.shape[:2], dtype=float)
        for g, prior in enumerate(priors):
            factors *= self._moment(g, prior)
        return ((1.0 - factors) / 2.0).mean(axis=1)

    def recommend(self, priors: tuple[BetaPrior, BetaPrior, BetaPrior]) -> tuple[int, float]:
        """Return (index of best placement, its expected loss)."""
        risks = self.expected_losses(priors)
        index = int(np.argmin(risks))
        return index, float(risks[index])

    def evsi(self, priors: tuple[BetaPrior, BetaPrior, BetaPrior], shots: int) -> dict[str, float]:
        if not (1 <= shots <= 1000):
            raise ValueError("EVSI exact enumeration supports 1..1000 shots")
        # Baseline: smallest expected task loss if we do NOT measure anything.
        before = self.recommend(priors)[1]
        answer: dict[str, float] = {}
        for group, name in enumerate(GROUPS):
            # Consider every possible measurement outcome: 0,1,...,shots failures.
            # A Beta-Binomial predictive probability weights each outcome.
            probs = betabinom.pmf(np.arange(shots + 1), shots, priors[group].alpha, priors[group].beta)
            probs = probs / np.sum(probs)
            after = 0.0
            for failures, probability in enumerate(probs):
                if probability < 1e-13:
                    continue
                updated = list(priors)
                # Pretend we got this outcome, update the posterior, then
                # see which placement would be chosen with that new knowledge.
                updated[group] = priors[group].updated(failures, shots)
                after += float(probability) * self.recommend(tuple(updated))[1]
            # How much better should our placement decision get ON AVERAGE?
            value = before - after
            # Numerical roundoff can cause very small negative values.
            answer[name] = float(max(value, 0.0)) if value > -1e-9 else float(value)
        return answer

    def select(self, priors: tuple[BetaPrior, BetaPrior, BetaPrior], shots: int) -> tuple[int, dict[str, float]]:
        values = self.evsi(priors, shots)
        chosen = max(range(3), key=lambda g: (values[GROUPS[g]], -g))
        return chosen, values
