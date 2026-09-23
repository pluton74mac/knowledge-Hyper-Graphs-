"""Maximum-weight 1:1 alignment: the Hungarian algorithm in pure Python, with SciPy as an optional backend
(the ``[fast]`` extra; DESIGN §9.1, R05 D-C5-17).

``solve(weights)`` takes a matrix of non-negative integers, rows and columns already in id order, and returns the
aligned pairs ``(i, j)``, those of a maximum-weight assignment with a positive weight. Ties break
lexicographically by id: among the maximum-weight alignments, row 0 takes the first column it can take in one of
them, then row 1 given that, and so on, and a row left unaligned ranks after every alignment of it. The answer is
therefore unique, and both backends return it:

- ``python`` solves one assignment problem whose integer weights encode the rule exactly
  (w·(m+1)^n + (m − j)·(m+1)^(n−1−i) for a positive w), with the O(n²m) shortest-augmenting-path algorithm;
- ``scipy`` finds the optimum with ``scipy.optimize.linear_sum_assignment`` and then fixes rows one at a time,
  checking each earlier column against the optimum of the remaining problem.

``auto`` (the default) uses SciPy only when it is installed and the matrix is large. SciPy is imported only then.
"""
from __future__ import annotations

import importlib.util
from typing import Sequence

__all__ = ["solve", "total", "BACKENDS"]

BACKENDS = ("auto", "python", "scipy")
#: ``auto`` hands matrices whose smaller side reaches this size to SciPy, when it is installed
SCIPY_MIN_SIDE = 48

Pairs = list[tuple[int, int]]


def _matrix(weights: Sequence[Sequence[int]]) -> list[list[int]]:
    rows = [list(r) for r in weights]
    if rows and any(len(r) != len(rows[0]) for r in rows):
        raise ValueError("the weight matrix is not rectangular")
    for r in rows:
        for w in r:
            if isinstance(w, bool) or not isinstance(w, int) or w < 0:
                raise ValueError(f"weights are non-negative integers, not {w!r}")
    return rows


def total(weights: Sequence[Sequence[int]], pairs: Pairs) -> int:
    """The weight of an alignment."""
    return sum(weights[i][j] for i, j in pairs)


def solve(weights: Sequence[Sequence[int]], *, backend: str = "auto") -> Pairs:
    """The aligned pairs ``(i, j)`` (sorted) of the tie-broken maximum-weight 1:1 alignment of ``weights``."""
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {BACKENDS}, not {backend!r}")
    w = _matrix(weights)
    n = len(w)
    m = len(w[0]) if n else 0
    if n == 0 or m == 0 or not any(any(r) for r in w):
        return []
    if backend == "auto":
        big = min(n, m) >= SCIPY_MIN_SIDE and importlib.util.find_spec("scipy") is not None
        backend = "scipy" if big else "python"
    return _scipy(w, n, m) if backend == "scipy" else _python(w, n, m)


# ------------------------------------------------------------------------------------------------ pure Python


def _python(w: list[list[int]], n: int, m: int) -> Pairs:
    base = m + 1
    scale = base ** n
    power = [base ** (n - 1 - i) for i in range(n)]
    p = [[w[i][j] * scale + (m - j) * power[i] if w[i][j] > 0 else 0 for j in range(m)] for i in range(n)]
    if n <= m:
        cols = _assign([[-x for x in row] for row in p])
        pairs = [(i, j) for i, j in enumerate(cols)]
    else:
        rows = _assign([[-p[i][j] for i in range(n)] for j in range(m)])
        pairs = [(i, j) for j, i in enumerate(rows)]
    return sorted((i, j) for i, j in pairs if w[i][j] > 0)


def _assign(cost: list[list[int]]) -> list[int]:
    """Minimum-cost assignment of every row of an n x m cost matrix (n <= m) to its own column, by shortest
    augmenting paths with potentials (Kuhn-Munkres, O(n²m)). Returns the column of each row."""
    n, m = len(cost), len(cost[0])
    inf = float("inf")
    u = [0] * (n + 1)
    v = [0] * (m + 1)
    owner = [0] * (m + 1)  # owner[j]: the row (1-based) holding column j, 0 when free
    way = [0] * (m + 1)
    for i in range(1, n + 1):
        owner[0] = i
        j0 = 0
        minv: list[float] = [inf] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = owner[j0]
            row = cost[i0 - 1]
            ui0 = u[i0]
            delta: float = inf
            j1 = 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = row[j - 1] - ui0 - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[owner[j]] += delta  # type: ignore[assignment]
                    v[j] -= delta  # type: ignore[assignment]
                else:
                    minv[j] -= delta
            j0 = j1
            if owner[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            owner[j0] = owner[j1]
            j0 = j1
    out = [-1] * n
    for j in range(1, m + 1):
        if owner[j]:
            out[owner[j] - 1] = j - 1
    return out


# ------------------------------------------------------------------------------------------------ SciPy


def _scipy(w: list[list[int]], n: int, m: int) -> Pairs:
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    a = np.asarray(w, dtype=np.float64)

    def best(rows: list[int], cols: list[int]) -> tuple[int, dict[int, int]]:
        if not rows or not cols:
            return 0, {}
        sub = a[np.ix_(rows, cols)]
        r, c = linear_sum_assignment(sub, maximize=True)
        value = int(round(float(sub[r, c].sum())))
        return value, {rows[x]: cols[y] for x, y in zip(r.tolist(), c.tolist(), strict=True)}

    free = list(range(m))
    remaining, current = best(list(range(n)), free)
    pairs: Pairs = []
    for i in range(n):
        rest = list(range(i + 1, n))
        held = current.get(i)
        held = held if held is not None and w[i][held] > 0 else None
        chosen = None
        for j in free:  # in column order; the column row i holds in the current optimum needs no check
            if w[i][j] <= 0:
                continue
            if j == held:
                chosen = j
                break
            value, assignment = best(rest, [c for c in free if c != j])
            if w[i][j] + value == remaining:
                chosen, current = j, assignment
                break
        if chosen is None:
            continue  # row i stays unaligned; the current assignment stays optimal for the rest
        pairs.append((i, chosen))
        remaining -= w[i][chosen]
        free.remove(chosen)
    return pairs
