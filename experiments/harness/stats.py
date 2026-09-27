"""Small stats helpers so experiment scripts don't each reimplement mean/
stdev/confidence-interval math. Stdlib only (statistics.NormalDist) - no
scipy/numpy dependency for this repo.

The confidence interval uses a normal approximation (z=1.96 for 95%), which
is standard for large samples but only approximate for the small trial
counts (n < 10-20) several of these experiments run under the free-tier
Gemini quota. Report it, but don't over-read precision from a narrow-looking
interval built on a handful of trials - say so in any write-up."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist, mean, pstdev, stdev


@dataclass
class SummaryStats:
    n: int
    mean: float
    stdev: float
    ci95_low: float
    ci95_high: float

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "mean": self.mean,
            "stdev": self.stdev,
            "ci95_low": self.ci95_low,
            "ci95_high": self.ci95_high,
        }


def summarize(values: list[float]) -> SummaryStats:
    n = len(values)
    if n == 0:
        return SummaryStats(n=0, mean=float("nan"), stdev=float("nan"), ci95_low=float("nan"), ci95_high=float("nan"))
    if n == 1:
        return SummaryStats(n=1, mean=values[0], stdev=0.0, ci95_low=values[0], ci95_high=values[0])

    m = mean(values)
    s = stdev(values)  # sample stdev (n-1 denominator)
    margin = 1.96 * s / (n**0.5)
    return SummaryStats(n=n, mean=m, stdev=s, ci95_low=m - margin, ci95_high=m + margin)


def rate(successes: int, total: int) -> float:
    return successes / total if total else float("nan")


def wilson_ci95(successes: int, total: int) -> tuple[float, float]:
    """95% CI for a proportion (Wilson score interval) - better-behaved than
    the normal approximation near 0 or 1, which plain success-rate CIs
    often are given small trial counts."""
    if total == 0:
        return (float("nan"), float("nan"))
    z = NormalDist().inv_cdf(0.975)
    p = successes / total
    denom = 1 + z**2 / total
    center = p + z**2 / (2 * total)
    spread = z * ((p * (1 - p) / total + z**2 / (4 * total**2)) ** 0.5)
    return ((center - spread) / denom, (center + spread) / denom)


def confusion_matrix(pairs: list[tuple[str, str]], labels: list[str]) -> dict[str, dict[str, int]]:
    """pairs: list of (expected, actual). Returns {expected: {actual: count}}."""
    matrix = {expected: {actual: 0 for actual in labels} for expected in labels}
    for expected, actual in pairs:
        matrix.setdefault(expected, {actual: 0 for actual in labels})
        matrix[expected][actual] = matrix[expected].get(actual, 0) + 1
    return matrix


def accuracy(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return float("nan")
    correct = sum(1 for expected, actual in pairs if expected == actual)
    return correct / len(pairs)


def population_stdev(values: list[float]) -> float:
    """Population (not sample) stdev - used when the 'trials' are the
    entire population being described rather than a sample of a larger one."""
    return pstdev(values) if len(values) > 1 else 0.0
