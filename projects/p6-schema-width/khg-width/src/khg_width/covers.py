"""Edge covers of a bag (DESIGN §3.3, §3.4).

- ``rho(bag, edges)``: the integral edge cover number, by exact search over the maximal traces e & bag
  (iterative deepening with the most constrained role first). Returns ``(k, names)``.
- ``rho_star(bag, edges)``: the fractional edge cover number by an **exact rational simplex**. The dual
  (max sum y_v subject to sum_{v in e} y_v <= 1, y >= 0) starts feasible at 0, so no phase 1 is needed; Bland's rule
  guarantees termination. The primal cover x is read off the final tableau. Both are checked: x covers every role at
  least once, y satisfies every edge constraint, and sum x = sum y (so each certifies the other's optimality).
  Returns a ``FractionalCover``.
- ``rho_star_scipy``: SciPy's HiGHS LP (the ``fast`` extra, imported lazily), rounded up to an exactly feasible
  rational cover: an upper bound, not an exact value.
- ``greedy_cover``: a greedy integral cover (an upper bound for rho and rho*).
- ``fractional_cover``: exact when the bag is small, else SciPy, else greedy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping, Sequence

from .steps import Deadline

__all__ = ["rho", "rho_star", "rho_star_scipy", "greedy_cover", "fractional_cover", "FractionalCover", "traces",
           "EXACT_LP_ROLES", "EXACT_LP_EDGES", "scipy_available"]

#: Bags up to this many roles (and traces) get the exact rational simplex; larger ones SciPy or the greedy cover.
EXACT_LP_ROLES = 40
EXACT_LP_EDGES = 160

Edges = Sequence[tuple[str, frozenset]]


def traces(bag: frozenset, edges: Edges, *, maximal: bool = True) -> list[tuple[str, frozenset]]:
    """The distinct traces e & bag, one name per trace (the first), largest first; with ``maximal`` only the
    inclusion-maximal ones."""
    seen: dict[frozenset, str] = {}
    for n, e in edges:
        t = e & bag
        if t and t not in seen:
            seen[t] = n
    ts = sorted(seen, key=lambda t: (-len(t), sorted(t)))
    if not maximal:
        return [(seen[t], t) for t in ts]
    out: list[tuple[str, frozenset]] = []
    by_vertex: dict[str, list[frozenset]] = {}
    for t in ts:
        # t is maximal unless a kept (not smaller) trace through its rarest role contains it
        rare = min(t, key=lambda v: len(by_vertex.get(v, ())))
        if any(t < u for u in by_vertex.get(rare, ())):
            continue
        out.append((seen[t], t))
        for v in t:
            by_vertex.setdefault(v, []).append(t)
    return out


def greedy_cover(bag: frozenset, edges: Edges) -> list[str]:
    """Largest new coverage first (ties: the earlier trace). Raises ValueError when the bag cannot be covered."""
    left = set(bag)
    ts = traces(frozenset(bag), edges, maximal=False)
    out: list[str] = []
    while left:
        best_i, best_n = -1, 0
        for i, (_, t) in enumerate(ts):
            if len(t) <= best_n:
                break  # traces are sorted by size: none further can beat best_n
            n = len(t & left)
            if n > best_n:
                best_i, best_n = i, n
        if best_i < 0:
            raise ValueError("the bag cannot be covered by the edges")
        out.append(ts[best_i][0])
        left -= ts[best_i][1]
    return out


def rho(bag: frozenset, edges: Edges, *, deadline: Deadline | None = None, upper: int | None = None
        ) -> tuple[int, list[str]]:
    """Exact integral edge cover number of ``bag``; returns (k, cover names)."""
    bag = frozenset(bag)
    if not bag:
        return 0, []
    ts = traces(bag, edges)
    greedy = greedy_cover(bag, edges)
    best = (len(greedy), greedy)
    if len(ts) == 1 or best[0] == 1:
        return best
    by_vertex: dict[str, list[int]] = {v: [] for v in bag}
    for i, (_, t) in enumerate(ts):
        for v in t:
            by_vertex[v].append(i)
    if any(not c for c in by_vertex.values()):
        raise ValueError("the bag cannot be covered by the edges")
    maxlen = max(len(t) for _, t in ts)
    for k in range(max(1, -(-len(bag) // maxlen)), best[0]):
        found = _cover_k(bag, ts, by_vertex, k, deadline)
        if found is not None:
            return k, [ts[i][0] for i in found]
    return best


def _cover_k(bag: frozenset, ts: list, by_vertex: dict, k: int, deadline: Deadline | None) -> list[int] | None:
    maxlen = max(len(t) for _, t in ts)
    stack: list[tuple[frozenset, list[int]]] = [(bag, [])]
    while stack:
        if deadline is not None:
            deadline.tick()
        left, chosen = stack.pop()
        if not left:
            return chosen
        room = k - len(chosen)
        if room <= 0 or len(left) > room * maxlen:
            continue
        v = min(left, key=lambda u: (len(by_vertex[u]), u))
        for i in reversed(by_vertex[v]):
            stack.append((left - ts[i][1], chosen + [i]))
    return None


@dataclass(frozen=True)
class FractionalCover:
    """``value`` = sum of ``weights`` (relation -> Fraction); ``exact`` when optimal (``dual`` then holds the
    dual certificate, role -> Fraction); ``method`` names how it was found."""

    value: Fraction
    weights: dict = field(default_factory=dict)
    exact: bool = True
    method: str = "exact-simplex"
    dual: dict = field(default_factory=dict)


def _check_primal(bag: frozenset, ts: Sequence[tuple[str, frozenset]], x: Mapping[str, Fraction]) -> bool:
    cov = {v: Fraction(0) for v in bag}
    for n, t in ts:
        w = x.get(n, Fraction(0))
        if w < 0:
            return False
        for v in t:
            cov[v] += w
    return all(c >= 1 for c in cov.values())


def rho_star(bag: frozenset, edges: Edges, *, deadline: Deadline | None = None) -> FractionalCover:
    """Exact fractional edge cover number of ``bag`` with primal and dual certificates."""
    bag = frozenset(bag)
    if not bag:
        return FractionalCover(Fraction(0))
    ts = traces(bag, edges)
    if len(ts) == 1:
        return FractionalCover(Fraction(1), {ts[0][0]: Fraction(1)}, True, "exact-simplex",
                               {min(bag): Fraction(1)})
    verts = sorted(bag)
    m, n = len(ts), len(verts)
    col = {v: j for j, v in enumerate(verts)}
    # dual LP in standard form: maximise sum_j y_j subject to A y <= 1 (one row per trace), y >= 0.
    # tableau rows: m constraints with slack s_i; columns 0..n-1 = y, n..n+m-1 = s, last = rhs.
    width = n + m + 1
    rows: list[list[Fraction]] = []
    for i, (_, t) in enumerate(ts):
        r = [Fraction(0)] * width
        for v in t:
            r[col[v]] = Fraction(1)
        r[n + i] = Fraction(1)
        r[-1] = Fraction(1)
        rows.append(r)
    # objective row z - sum y = 0 stored as reduced costs c_j (maximise: enter while some c_j < 0)
    obj = [Fraction(0)] * width
    for j in range(n):
        obj[j] = Fraction(-1)
    basis = [n + i for i in range(m)]
    while True:
        if deadline is not None:
            deadline.check()
        enter = next((j for j in range(n + m) if obj[j] < 0), None)  # Bland: smallest index
        if enter is None:
            break
        best = None
        for i in range(m):
            a = rows[i][enter]
            if a > 0:
                ratio = rows[i][-1] / a
                if best is None or ratio < best[0] or (ratio == best[0] and basis[i] < basis[best[1]]):
                    best = (ratio, i)
        if best is None:
            raise ArithmeticError("unbounded dual: a role lies in no edge")
        r = best[1]
        piv = rows[r][enter]
        if piv != 1:
            rows[r] = [a / piv for a in rows[r]]
        pr = rows[r]
        for i in range(m):
            if i != r:
                f = rows[i][enter]
                if f:
                    ri = rows[i]
                    rows[i] = [a - f * b for a, b in zip(ri, pr)]
        f = obj[enter]
        if f:
            obj = [a - f * b for a, b in zip(obj, pr)]
        basis[r] = enter
    value = obj[-1]
    y = {verts[j]: Fraction(0) for j in range(n)}
    for i, b in enumerate(basis):
        if b < n:
            y[verts[b]] = rows[i][-1]
    # primal x_i = reduced cost of slack i
    x = {ts[i][0]: obj[n + i] for i in range(m)}
    x = {k: w for k, w in x.items() if w}
    # certificates
    if not _check_primal(bag, ts, x):
        raise ArithmeticError("simplex primal cover is infeasible")
    for _, t in ts:
        if sum((y[v] for v in t), Fraction(0)) > 1:
            raise ArithmeticError("simplex dual is infeasible")
    if any(w < 0 for w in y.values()):
        raise ArithmeticError("simplex dual is negative")
    if sum(x.values(), Fraction(0)) != value or sum(y.values(), Fraction(0)) != value:
        raise ArithmeticError("simplex primal and dual values differ")
    return FractionalCover(value, x, True, "exact-simplex", {k: w for k, w in y.items() if w})


def scipy_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("scipy") is not None
    except (ImportError, ValueError):
        return False


def rho_star_scipy(bag: frozenset, edges: Edges) -> FractionalCover:
    """SciPy HiGHS on the primal, rounded to fractions and scaled up until every role is covered exactly: an upper
    bound on rho*. Raises ImportError without SciPy."""
    from scipy.optimize import linprog  # the `fast` extra

    bag = frozenset(bag)
    ts = traces(bag, edges)
    verts = sorted(bag)
    a_ub = [[-1.0 if v in t else 0.0 for _, t in ts] for v in verts]
    res = linprog(c=[1.0] * len(ts), A_ub=a_ub, b_ub=[-1.0] * len(verts), bounds=[(0, None)] * len(ts),
                  method="highs")
    if res.status != 0:
        raise ArithmeticError(f"linprog failed: {res.message}")
    x = {ts[i][0]: Fraction(float(w)).limit_denominator(10_000) for i, w in enumerate(res.x) if w > 1e-12}
    cov = {v: Fraction(0) for v in verts}
    for n, t in ts:
        w = x.get(n, Fraction(0))
        for v in t:
            cov[v] += w
    low = min(cov.values())
    if low <= 0:
        raise ArithmeticError("rounded cover leaves a role uncovered")
    if low < 1:
        x = {k: w / low for k, w in x.items()}
    assert _check_primal(bag, ts, x)
    return FractionalCover(sum(x.values(), Fraction(0)), x, False, "scipy-rounded")


def fractional_cover(bag: frozenset, edges: Edges, *, deadline: Deadline | None = None,
                     exact_roles: int = EXACT_LP_ROLES, exact_edges: int = EXACT_LP_EDGES) -> FractionalCover:
    """rho*(bag): exact on small bags, else SciPy rounded up, else the greedy integral cover."""
    bag = frozenset(bag)
    if not bag:
        return FractionalCover(Fraction(0))
    ts = traces(bag, edges)
    if len(bag) <= exact_roles and len(ts) <= exact_edges:
        return rho_star(bag, edges, deadline=deadline)
    if scipy_available():
        try:
            return rho_star_scipy(bag, edges)
        except ArithmeticError:
            pass
    g = greedy_cover(bag, edges)
    return FractionalCover(Fraction(len(g)), {k: Fraction(1) for k in g}, False, "greedy")
