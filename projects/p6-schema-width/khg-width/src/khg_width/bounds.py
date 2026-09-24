"""Bounds (DESIGN §3.4).

Lower bounds, each labelled by its method:

- ``cyclic``: hw, ghw >= 2 and fhw > 1 (``lower_exclusive``) when H is not alpha-acyclic;
- ``clique``: ghw >= rho(K) and fhw >= rho*(K) for a primal clique K of the core (Bron-Kerbosch with pivoting):
  a clique lies in one bag of every tree decomposition;
- ``induced-dp`` / ``induced-hd-search``: every measure is monotone under H -> H[X] = {e & X}, so an exact value on a
  small H[X], X grown greedily from high-degree core roles, is a lower bound;
- tw: max(rank - 1, simplicial, minor-min-width), plus the universal offset;
- solver refutations from unflagged runs that no other tool contradicts (``check``).

Upper bounds come from decompositions only: heuristic elimination orderings (min-degree, min-fill; ties broken by a
seeded random order) whose bags give tw, greedy covers ghw and rho* fhw; the hw searches and solvers; and the
trivial one-node HD (hw <= |E|).

``propagate`` passes bounds through fhw <= ghw <= hw <= 3 ghw + 1, ghw <= tw + 1 and ceil(fhw) <= ghw until nothing
changes. Upper bounds move only where the certificate moves with them (an HD is a GHD, a GHD an FHD); hw <= 3 ghw + 1
moves lower bounds only.
"""
from __future__ import annotations

import heapq
import math
import random
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Iterable, Mapping, Sequence

from .covers import rho, rho_star, traces, EXACT_LP_EDGES, EXACT_LP_ROLES
from .steps import Deadline

__all__ = ["min_degree_order", "min_fill_order", "max_cliques", "clique_bounds", "grow_induced", "minor_min_width",
           "Bound", "propagate", "INDUCED_ROLES", "INDUCED_ROLES_FHW"]

INDUCED_ROLES = 18
INDUCED_ROLES_FHW = 16


# ------------------------------------------------------------------------------------------------ orderings
def min_degree_order(adj: Mapping[str, set], *, seed: int, deadline: Deadline | None = None) -> list[str]:
    """Greedy minimum-degree elimination ordering (fill edges added), ties broken by a seeded random key."""
    rng = random.Random(seed)
    nb = {v: set(adj[v]) & adj.keys() for v in adj}
    key = {v: rng.random() for v in sorted(nb)}
    heap = [(len(nb[v]), key[v], v) for v in nb]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        if deadline is not None:
            deadline.tick()
        d, _, v = heapq.heappop(heap)
        if v not in nb or d != len(nb[v]):
            continue
        nbrs = nb.pop(v)
        order.append(v)
        for a in nbrs:
            s = nb[a]
            s.discard(v)
            s |= nbrs
            s.discard(a)
            heapq.heappush(heap, (len(s), key[a], a))
    return order


def min_fill_order(adj: Mapping[str, set], *, seed: int, deadline: Deadline | None = None) -> list[str]:
    """Greedy minimum-fill elimination ordering; the fill of a role's neighbours is recomputed after each step
    (an approximation of exact min-fill bookkeeping: still a valid ordering)."""
    rng = random.Random(seed)
    nb = {v: set(adj[v]) & adj.keys() for v in adj}
    key = {v: rng.random() for v in sorted(nb)}

    def fill(v: str) -> int:
        ns = nb[v]
        missing = 0
        for a in ns:
            missing += len(ns) - 1 - len(ns & nb[a])
        return missing // 2

    cur = {v: fill(v) for v in nb}
    heap = [(cur[v], len(nb[v]), key[v], v) for v in nb]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        if deadline is not None:
            deadline.tick()
        f, _, _, v = heapq.heappop(heap)
        if v not in nb or f != cur[v]:
            continue
        nbrs = nb.pop(v)
        del cur[v]
        order.append(v)
        for a in nbrs:
            s = nb[a]
            s.discard(v)
            s |= nbrs
            s.discard(a)
        for a in nbrs:
            cur[a] = fill(a)
            heapq.heappush(heap, (cur[a], len(nb[a]), key[a], a))
    return order


# ------------------------------------------------------------------------------------------------ cliques
def max_cliques(adj: Mapping[str, set], *, deadline: Deadline | None = None) -> Iterable[frozenset]:
    """Maximal cliques by Bron-Kerbosch with pivoting, iteratively (a generator)."""
    stack: list[tuple[set, set, set]] = [(set(), set(adj), set())]
    while stack:
        if deadline is not None:
            deadline.tick()
        r, p, x = stack.pop()
        if not p and not x:
            yield frozenset(r)
            continue
        if not p:
            continue
        pivot = max(p | x, key=lambda u: (len(adj[u] & p), u))
        for v in sorted(p - adj[pivot]):
            stack.append((r | {v}, p & adj[v], x & adj[v]))
            p = p - {v}
            x = x | {v}


def clique_bounds(adj: Mapping[str, set], edges: Sequence[tuple[str, frozenset]], *, deadline: Deadline,
                  want_fhw: bool = True, max_cover_trace: int = 60) -> tuple[int, Fraction, frozenset | None,
                                                                              frozenset | None, int]:
    """(ghw lower, fhw lower, clique for ghw, clique for fhw, cliques seen) over the maximal cliques of ``adj``.
    rho(K) is exact when K has at most ``max_cover_trace`` traces (else ceil(|K| / largest trace)); rho*(K) is exact
    on small cliques, else the certified dual bound |K| / largest trace."""
    best_g, best_f = 0, Fraction(0)
    kg = kf = None
    seen = 0
    try:
        for k in max_cliques(adj, deadline=deadline):
            seen += 1
            ts = traces(k, edges)
            if len(ts) == 1:
                continue  # inside one edge: rho = 1
            big = max(len(t) for _, t in ts)
            if len(ts) <= max_cover_trace:
                g = rho(k, edges, deadline=deadline)[0]
            else:
                g = -(-len(k) // big)
            if g > best_g:
                best_g, kg = g, k
            if want_fhw:
                if len(k) <= EXACT_LP_ROLES and len(ts) <= EXACT_LP_EDGES:
                    f = rho_star(k, edges, deadline=deadline).value
                else:
                    f = Fraction(len(k), big)
                if f > best_f:
                    best_f, kf = f, k
    except Exception as e:  # a timeout keeps the best found so far
        if type(e).__name__ != "StepTimeout":
            raise
    return best_g, best_f, kg, kf, seen


# ------------------------------------------------------------------------------------------------ induced sets
def grow_induced(adj: Mapping[str, set], degree: Mapping[str, int], size: int, *, start: str | None = None
                 ) -> frozenset:
    """X grown greedily: start from the highest-degree role (or ``start``), then repeatedly add the role with the
    most neighbours in X (ties: higher degree, then name)."""
    if not adj:
        return frozenset()
    if start is None:
        start = max(adj, key=lambda v: (degree.get(v, 0), len(adj[v]), v))
    x = {start}
    score = {u: 1 for u in adj[start]}
    while len(x) < size and score:
        v = max(score, key=lambda u: (score[u], degree.get(u, 0), u))
        x.add(v)
        del score[v]
        for u in adj[v]:
            if u not in x:
                score[u] = score.get(u, 0) + 1
    return frozenset(x)


# ------------------------------------------------------------------------------------------------ tw lower bounds
def minor_min_width(adj: Mapping[str, set], *, deadline: Deadline | None = None) -> int:
    """The minor-min-width lower bound on treewidth (Gogate and Dechter): repeatedly take a minimum-degree role,
    record its degree, contract it into its minimum-degree neighbour."""
    nb = {v: set(s) for v, s in adj.items()}
    lb = 0
    heap = [(len(nb[v]), v) for v in nb]
    heapq.heapify(heap)
    while heap:
        if deadline is not None:
            deadline.tick()
        d, v = heapq.heappop(heap)
        if v not in nb or d != len(nb[v]):
            continue
        lb = max(lb, d)
        nbrs = nb.pop(v)
        if not nbrs:
            continue
        u = min(nbrs, key=lambda w: (len(nb[w]), w))
        for w in nbrs:
            nb[w].discard(v)
        for w in nbrs:
            if w != u:
                nb[u].add(w)
                nb[w].add(u)
        for w in nbrs:
            heapq.heappush(heap, (len(nb[w]), w))
    return lb


# ------------------------------------------------------------------------------------------------ propagation
@dataclass
class Bound:
    """A measure's running bounds while ``check`` works: values with their methods and the upper certificate."""

    measure: str
    lower: Any = 0
    lower_method: str = "trivial"
    lower_exclusive: bool = False
    upper: Any = None
    upper_method: str | None = None
    certificate: Any = None
    certificate_kind: str | None = None
    validation: Any = None
    notes: list = field(default_factory=list)

    def raise_lower(self, value: Any, method: str, *, exclusive: bool = False, prefer: bool = False) -> bool:
        """Raise the lower bound to ``value``; ``prefer`` also relabels an equal bound (an exact procedure)."""
        if value is None:
            return False
        if value > self.lower or (value == self.lower and self.lower_exclusive and not exclusive) or (
                prefer and value == self.lower and not exclusive and not self.lower_exclusive
                and self.lower_method != method):
            self.lower, self.lower_method, self.lower_exclusive = value, method, exclusive
            return True
        return False

    def offer_upper(self, value: Any, method: str, certificate: Any, kind: str, validation: Any) -> bool:
        if self.upper is None or value < self.upper:
            self.upper, self.upper_method = value, method
            self.certificate, self.certificate_kind, self.validation = certificate, kind, validation
            return True
        return False

    @property
    def exact(self) -> bool:
        return self.upper is not None and not self.lower_exclusive and self.lower == self.upper


def propagate(b: Mapping[str, Bound], convert: Callable[[Bound, str], tuple[Any, Any] | None] | None = None
              ) -> None:
    """Pass bounds through the width inequalities until nothing changes. ``convert(src, kind)`` re-validates the
    source certificate as ``kind`` and returns (certificate, validation) or None; an upper bound moves only then."""
    hw, ghw, fhw, tw = b["hw"], b["ghw"], b["fhw"], b["tw"]
    for _ in range(10):
        changed = False
        # lower bounds
        changed |= hw.raise_lower(ghw.lower, "inequality") if not ghw.lower_exclusive else False
        if fhw.lower_exclusive:
            fl = math.floor(fhw.lower) + 1 if Fraction(fhw.lower).denominator == 1 else math.ceil(fhw.lower)
        else:
            fl = math.ceil(fhw.lower)
        changed |= ghw.raise_lower(fl, "inequality")
        if hw.lower:
            changed |= ghw.raise_lower(max(0, math.ceil((hw.lower - 1) / 3)), "inequality")
        if ghw.lower:
            changed |= tw.raise_lower(ghw.lower - 1, "inequality")
        # upper bounds (with certificates)
        if hw.upper is not None and (ghw.upper is None or hw.upper < ghw.upper) and convert is not None:
            got = convert(hw, "ghd")
            if got is not None:
                changed |= ghw.offer_upper(hw.upper, "inequality", got[0], "ghd", got[1])
        if ghw.upper is not None and (fhw.upper is None or ghw.upper < fhw.upper) and convert is not None:
            got = convert(ghw, "fhd")
            if got is not None:
                changed |= fhw.offer_upper(Fraction(ghw.upper), "inequality", got[0], "fhd", got[1])
        if not changed:
            break


# ------------------------------------------------------------------------------------------------ hd repair
def repair_special(edges: Mapping[str, frozenset], bags: list[set], covers: list[dict], parent: list[int | None],
                   *, deadline: Deadline | None = None) -> None:
    """Make a GHD satisfy the special condition, in place, in one pre-order pass: at node t, every role v of
    (U lambda_t) ∩ chi(T_t) missing from chi_t is added to chi_t and to every node below t whose subtree holds v
    (the path to v's subtree, which keeps (2)); each such node gets the guard of t that holds v, so (3) keeps
    holding. Nodes above t are never touched again, so the pass ends with an HD (of possibly larger width); the
    caller validates it."""
    n = len(bags)
    kids: list[list[int]] = [[] for _ in range(n)]
    root = None
    for i, p in enumerate(parent):
        if p is None:
            root = i if root is None else root
        else:
            kids[p].append(i)
    order: list[int] = []
    stack = [root] if root is not None else []
    while stack:
        i = stack.pop()
        order.append(i)
        stack.extend(reversed(kids[i]))
    sub = [set(b) for b in bags]
    for i in reversed(order):
        p = parent[i]
        if p is not None:
            sub[p] |= sub[i]
    for t in order:
        if deadline is not None:
            deadline.tick()
        lam: set = set()
        for g in covers[t]:
            lam |= edges[g]
        viol = (lam & sub[t]) - bags[t]
        if not viol:
            continue
        holder = {v: next(g for g in sorted(covers[t]) if v in edges[g]) for v in viol}
        todo = [t]
        while todo:
            u = todo.pop()
            here = viol & sub[u]
            if not here:
                continue
            new = here - bags[u]
            if new:
                bags[u] |= new
                for v in new:
                    covers[u].setdefault(holder[v], Fraction(1))
            todo.extend(kids[u])
