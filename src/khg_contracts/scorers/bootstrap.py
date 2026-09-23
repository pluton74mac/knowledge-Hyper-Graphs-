"""The percentile bootstrap of the C5 scorers (DESIGN §9.1), with a fixed procedure:

- ``rng = random.Random(seed)``; each resample draws n indices as ``int(rng.random() * n)``;
- the interval is the sorted resample statistics at positions ⌊(α/2)·R⌋ and ⌊(1 − α/2)·R⌋ − 1 (for the defaults,
  1,000 resamples, seed 0 and α = 0.05: positions 25 and 974);
- the paired bootstrap reuses one index sequence for both systems.

Python guarantees the sequence of ``random()`` across versions (``choices()`` is not used). Means are summed with
``math.fsum``, which is correctly rounded, so the numbers do not depend on the platform. On
``[0, 1, 1, 0, 1, 1, 1, 0, 1, 1]`` the interval is [0.4, 1.0].
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Iterator, Sequence, TypeVar

__all__ = ["Bootstrap", "resample_indices", "percentile_positions", "interval", "mean", "mean_interval", "paired"]

T = TypeVar("T")
Statistic = Callable[[Sequence[T]], "float | Fraction | int | None"]


@dataclass(frozen=True)
class Bootstrap:
    """The dispersion settings of a scorer: ``resamples`` (0 turns the bootstrap off), ``seed`` and ``alpha``."""

    resamples: int = 1000
    seed: int = 0
    alpha: float = 0.05

    def __post_init__(self) -> None:
        if isinstance(self.resamples, bool) or not isinstance(self.resamples, int) or self.resamples < 0:
            raise ValueError(f"resamples must be an integer >= 0, not {self.resamples!r}")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError(f"seed must be an integer, not {self.seed!r}")
        if isinstance(self.alpha, bool) or not isinstance(self.alpha, (int, float)) or not 0 < self.alpha < 1:
            raise ValueError(f"alpha must lie in (0, 1), not {self.alpha!r}")

    def as_dict(self) -> dict[str, Any]:
        return {"resamples": self.resamples, "seed": self.seed, "alpha": self.alpha}


def resample_indices(n: int, config: Bootstrap = Bootstrap()) -> Iterator[list[int]]:
    """The ``config.resamples`` index lists of the procedure, each of length ``n``."""
    rng = random.Random(config.seed)
    for _ in range(config.resamples):
        yield [int(rng.random() * n) for _ in range(n)]


def percentile_positions(count: int, alpha: float) -> tuple[int, int]:
    """The 0-based positions ⌊(α/2)·R⌋ and ⌊(1 − α/2)·R⌋ − 1 in R sorted statistics (exact arithmetic)."""
    a = Fraction(repr(alpha)) if isinstance(alpha, float) else Fraction(alpha)
    lo = math.floor(a / 2 * count)
    hi = math.floor((1 - a / 2) * count) - 1
    return lo, max(lo, hi)


def _interval(stats: list[float], alpha: float) -> list[float] | None:
    if not stats:
        return None
    stats.sort()
    lo, hi = percentile_positions(len(stats), alpha)
    return [stats[lo], stats[hi]]


def _as_float(x: Any) -> float | None:
    return None if x is None else float(x)


def interval(units: Sequence[T], statistic: Statistic, config: Bootstrap = Bootstrap()) -> list[float] | None:
    """The percentile interval of ``statistic`` over resamples of ``units``; None when the bootstrap is off, there
    are no units, or the statistic is undefined (None) on every resample. Resamples on which it is undefined are
    left out before the positions are taken."""
    if config.resamples == 0 or not units:
        return None
    stats = []
    for idx in resample_indices(len(units), config):
        v = _as_float(statistic([units[i] for i in idx]))
        if v is not None:
            stats.append(v)
    return _interval(stats, config.alpha)


def mean(values: Sequence[float | Fraction | int]) -> float | None:
    """The correctly rounded mean of ``values`` (None when empty)."""
    return math.fsum(float(v) for v in values) / len(values) if values else None


def mean_interval(values: Sequence[float | Fraction | int], config: Bootstrap = Bootstrap()) -> list[float] | None:
    """The percentile interval of the mean of ``values`` (the per-unit scores)."""
    floats = [float(v) for v in values]
    if config.resamples == 0 or not floats:
        return None
    n = len(floats)
    stats = [math.fsum(floats[i] for i in idx) / n for idx in resample_indices(n, config)]
    return _interval(stats, config.alpha)


def paired(units_a: Sequence[T], units_b: Sequence[T], statistic: Statistic,
           config: Bootstrap = Bootstrap()) -> dict[str, Any] | None:
    """The paired bootstrap of two systems scored on the same units (in the same order): one index sequence for
    both. Returns the interval of each system, of the difference b − a, and ``b_better``, the share of resamples in
    which b's statistic exceeds a's (Koehn 2004)."""
    if len(units_a) != len(units_b):
        raise ValueError(f"paired units differ in number: {len(units_a)} and {len(units_b)}")
    if config.resamples == 0 or not units_a:
        return None
    sa: list[float] = []
    sb: list[float] = []
    sd: list[float] = []
    wins = 0
    for idx in resample_indices(len(units_a), config):
        a = _as_float(statistic([units_a[i] for i in idx]))
        b = _as_float(statistic([units_b[i] for i in idx]))
        if a is None or b is None:
            continue
        sa.append(a)
        sb.append(b)
        sd.append(b - a)
        wins += b > a
    n = len(sd)
    return {"a": _interval(sa, config.alpha), "b": _interval(sb, config.alpha),
            "difference": _interval(sd, config.alpha), "b_better": wins / n if n else None, "resamples_used": n}
