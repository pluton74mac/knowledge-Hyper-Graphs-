"""Top-1 calibration measures (DESIGN §9.3, §9.7; R05 C-M7): expected calibration error with equal-width and
equal-mass bins, the reliability table and the Brier score. Computed exactly: a float confidence is read by its
shortest decimal form (0.95 is 19/20), so the hand values of §9.7 come out exactly.

- **Equal width**: M bins (i/M, (i+1)/M] for i = 0 … M − 1, with 0 in the first bin.
- **Equal mass** (normative): sort by confidence; B = min(M, the number of distinct confidences); for
  i = 1 … B − 1 the i-th cut is the end of the run of equal confidences that contains position ⌈i·n/B⌉; ties are
  never split and empty bins are dropped.
- ECE = Σ_b (|b|/n)·|acc(b) − conf(b)|; Brier = mean (conf − correct)².
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import Any, Sequence

from ._common import frac

__all__ = ["BINNINGS", "bins", "ece", "brier", "reliability"]

BINNINGS = ("equal_width", "equal_mass")
Pair = tuple[Fraction, int]


def _pairs(confidences: Sequence[Any], correct: Sequence[Any]) -> list[Pair]:
    if len(confidences) != len(correct):
        raise ValueError(f"{len(confidences)} confidences but {len(correct)} correctness values")
    out = []
    for c, y in zip(confidences, correct, strict=True):
        cf = frac(c)
        if not 0 <= cf <= 1:
            raise ValueError(f"a confidence lies in [0, 1], not {c!r}")
        if y not in (0, 1, True, False):
            raise ValueError(f"correctness is 0 or 1, not {y!r}")
        out.append((cf, int(y)))
    return out


def bins(confidences: Sequence[Any], correct: Sequence[Any], *, m: int = 15,
         binning: str = "equal_width") -> list[list[Pair]]:
    """The non-empty bins, each a list of ``(confidence, correct)`` in confidence order."""
    if binning not in BINNINGS:
        raise ValueError(f"binning must be one of {BINNINGS}, not {binning!r}")
    if isinstance(m, bool) or not isinstance(m, int) or m < 1:
        raise ValueError(f"the number of bins is a positive integer, not {m!r}")
    items = sorted(_pairs(confidences, correct), key=lambda x: x[0])
    n = len(items)
    if not n:
        return []
    if binning == "equal_width":
        by: dict[int, list[Pair]] = {}
        for c, y in items:
            i = max(0, min(m - 1, math.ceil(c * m) - 1))
            by.setdefault(i, []).append((c, y))
        return [by[i] for i in sorted(by)]
    b = min(m, len({c for c, _ in items}))
    cuts = set()
    for i in range(1, b):
        pos = -(-i * n // b)  # the 1-based position ceil(i*n/B)
        end = pos
        while end < n and items[end][0] == items[pos - 1][0]:
            end += 1  # to the end of the run of equal confidences
        cuts.add(end)
    out, start = [], 0
    for c in sorted(cuts | {n}):
        if c > start:
            out.append(items[start:c])
            start = c
    return out


def ece(confidences: Sequence[Any], correct: Sequence[Any], *, m: int = 15, binning: str = "equal_width") -> Fraction:
    """The expected calibration error (exact); 0 for no items."""
    groups = bins(confidences, correct, m=m, binning=binning)
    n = sum(len(g) for g in groups)
    total = Fraction(0)
    for g in groups:
        acc = Fraction(sum(y for _, y in g), len(g))
        conf = sum((c for c, _ in g), Fraction(0)) / len(g)
        total += Fraction(len(g), n) * abs(acc - conf)
    return total


def brier(confidences: Sequence[Any], correct: Sequence[Any]) -> Fraction | None:
    """The top-1 Brier score, mean (conf − correct)² (exact); None for no items."""
    items = _pairs(confidences, correct)
    if not items:
        return None
    return sum(((c - y) ** 2 for c, y in items), Fraction(0)) / len(items)


def reliability(confidences: Sequence[Any], correct: Sequence[Any], *, m: int = 15,
                binning: str = "equal_width") -> list[dict[str, Any]]:
    """The reliability table: per non-empty bin its count, accuracy, mean confidence and confidence range (floats)."""
    out = []
    for g in bins(confidences, correct, m=m, binning=binning):
        out.append({"n": len(g), "accuracy": float(Fraction(sum(y for _, y in g), len(g))),
                    "confidence": float(sum((c for c, _ in g), Fraction(0)) / len(g)),
                    "min_confidence": float(g[0][0]), "max_confidence": float(g[-1][0])})
    return out
