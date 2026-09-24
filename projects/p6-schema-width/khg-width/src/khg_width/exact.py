"""Exact procedures (DESIGN §3.3).

- ``dp_width``: the subset DP over elimination orderings (Moll, Tazari and Thurley 2012; R01 §4.6),
  F(S) = min_v max(F(S \\ v), f({v} ∪ Q(S \\ v, v))), where Q(S, v) is the set of roles outside S ∪ {v} reachable
  from v through S. With f = |B| - 1 it gives tw, with f = rho(B) ghw, with f = rho*(B) fhw. The ordering it
  returns becomes a tree decomposition by ``elimination_tree``. Roles are bits of an int.
- ``hd_search``: the det-k-decomp-style search over normal-form hypertree decompositions of width <= k (GLS 2002
  k-decomp; Gottlob and Samer 2008). The state is a [chi]-component C with connector N(C); a separator is any set of
  <= k relations meeting C ∪ N(C) that covers N(C) and meets C, with chi = ∪lambda ∩ (C ∪ N(C)). Failed components
  are memoised. A "no" is exhaustive: a refutation of hw <= k. It runs on H as given (never reduced).
"""
from __future__ import annotations

import itertools
from fractions import Fraction
from typing import Any, Callable, Mapping, Sequence

from .covers import rho_star
from .decomposition import Decomposition, Tree
from .hypergraph import Hypergraph
from .steps import Budget, Deadline

__all__ = ["dp_width", "elimination_tree", "rho_cost", "rho_star_cost", "hd_search", "DP_LIMIT", "DP_LIMIT_FHW",
           "HD_SEARCH_RELATIONS", "HD_SEARCH_BUDGET"]

DP_LIMIT = 20
DP_LIMIT_FHW = 16
HD_SEARCH_RELATIONS = 60
HD_SEARCH_BUDGET = 3_000_000


def dp_width(verts: Sequence[str], adj: Mapping[str, set], cost: Callable[[int], Any],
             deadline: Deadline | None = None) -> tuple[Any, list[str]]:
    """min over elimination orderings of the max bag cost; returns (width, ordering, first eliminated first).
    ``cost`` takes a bag as a bitmask over ``verts``."""
    verts = list(verts)
    n = len(verts)
    if n == 0:
        return 0, []
    idx = {v: i for i, v in enumerate(verts)}
    nbm = [0] * n
    for v in verts:
        m = 0
        for u in adj.get(v, ()):
            j = idx.get(u)
            if j is not None:
                m |= 1 << j
        nbm[idx[v]] = m
    size = 1 << n
    best_w: list[Any] = [None] * size
    best_v = [0] * size
    memo: dict[int, Any] = {}
    tick = deadline.tick if deadline is not None else (lambda: None)
    for s in range(1, size):
        tick()
        cand = None
        cv = -1
        m = s
        while m:
            low = m & -m
            m ^= low
            prev = s ^ low
            fp = best_w[prev]
            if cand is not None and fp is not None and fp >= cand:
                continue
            # Q(prev, v): roles outside prev ∪ {v} reachable from v through prev
            comp = low
            frontier = low
            reach = 0
            while frontier:
                nxt = 0
                f = frontier
                while f:
                    lb = f & -f
                    nxt |= nbm[lb.bit_length() - 1]
                    f ^= lb
                reach |= nxt
                frontier = nxt & prev & ~comp
                comp |= frontier
            bag = (reach & ~prev & ~low) | low
            c = memo.get(bag)
            if c is None:
                c = cost(bag)
                memo[bag] = c
            w = c if fp is None or c >= fp else fp
            if cand is None or w < cand:
                cand = w
                cv = low.bit_length() - 1
        best_w[s] = cand
        best_v[s] = cv
    seq: list[str] = []
    s = size - 1
    while s:
        v = best_v[s]
        seq.append(verts[v])
        s &= ~(1 << v)
    return best_w[size - 1], seq[::-1]


def elimination_tree(order: Sequence[str], adj: Mapping[str, set], *, deadline: Deadline | None = None) -> Tree:
    """The tree decomposition of an elimination ordering: bag(v) = {v} ∪ its later neighbours in the filled graph,
    whose parent is the bag of the earliest-eliminated of them."""
    pos = {v: i for i, v in enumerate(order)}
    nb = {v: {u for u in adj.get(v, ()) if u in pos} for v in order}
    t = Tree()
    node: dict[str, int] = {}
    pending: list[tuple[int, str | None]] = []
    for v in order:
        if deadline is not None:
            deadline.tick()
        nbrs = nb.pop(v)
        i = t.add(nbrs | {v}, None, None)
        node[v] = i
        for a in nbrs:
            s = nb[a]
            s |= nbrs
            s.discard(a)
            s.discard(v)
        pending.append((i, min(nbrs, key=pos.__getitem__) if nbrs else None))
    for i, u in pending:
        if u is not None:
            t.parent[i] = node[u]
    return t


def _mask(verts: Sequence[str]) -> Callable[[int], frozenset]:
    vs = list(verts)

    def unmask(m: int) -> frozenset:
        out = []
        while m:
            lb = m & -m
            out.append(vs[lb.bit_length() - 1])
            m ^= lb
        return frozenset(out)

    return unmask


def rho_cost(verts: Sequence[str], edges: Sequence[tuple[str, frozenset]],
             deadline: Deadline | None = None) -> Callable[[int], int]:
    """rho(bag) on bitmasks by exact search over maximal traces (iterative deepening), memoised by the DP."""
    idx = {v: i for i, v in enumerate(verts)}
    ems = []
    for _, e in edges:
        m = 0
        for v in e:
            if v in idx:
                m |= 1 << idx[v]
        if m:
            ems.append(m)
    ems = sorted(set(ems), key=lambda m: -m.bit_count())

    def cost(bag: int) -> int:
        if not bag:
            return 0
        ts = []
        for m in ems:
            t = m & bag
            if t and not any(t & ~u == 0 for u in ts):
                ts.append(t)
        ts = [t for t in ts if not any(t != u and t & ~u == 0 for u in ts)]
        if any(t == bag for t in ts):
            return 1
        maxlen = max(t.bit_count() for t in ts)
        need = bag.bit_count()
        k = max(2, -(-need // maxlen))
        while True:
            if deadline is not None:
                deadline.tick()
            if _covers_in(bag, ts, k):
                return k
            k += 1

    return cost


def _covers_in(bag: int, ts: list[int], k: int) -> bool:
    maxlen = max(t.bit_count() for t in ts)
    stack = [(bag, 0)]
    while stack:
        left, used = stack.pop()
        if not left:
            return True
        room = k - used
        if room <= 0 or left.bit_count() > room * maxlen:
            continue
        low = left & -left
        for t in ts:
            if t & low:
                stack.append((left & ~t, used + 1))
    return False


def rho_star_cost(verts: Sequence[str], edges: Sequence[tuple[str, frozenset]],
                  deadline: Deadline | None = None) -> Callable[[int], Fraction]:
    """rho*(bag) on bitmasks by the exact rational simplex."""
    unmask = _mask(verts)
    es = list(edges)

    def cost(bag: int) -> Fraction:
        if not bag:
            return Fraction(0)
        return rho_star(unmask(bag), es, deadline=deadline).value

    return cost


# ------------------------------------------------------------------------------------------------ hw search
def hd_search(h: Hypergraph, k: int, *, budget: Budget | None = None, deadline: Deadline | None = None
              ) -> Decomposition | None:
    """A normal-form hypertree decomposition of width <= k of ``h`` (use the set hypergraph), or None when none
    exists. Raises ``BudgetExhausted`` / ``StepTimeout`` (from ``steps``) when the search is cut short."""
    names = list(h.names)
    verts = list(h.vertices)
    vidx = {v: i for i, v in enumerate(verts)}
    em: list[int] = []
    for _, e in h.edges:
        m = 0
        for v in e:
            m |= 1 << vidx[v]
        em.append(m)
    full = (1 << len(verts)) - 1
    v_edges: list[list[int]] = [[] for _ in verts]
    for j, m in enumerate(em):
        x = m
        while x:
            lb = x & -x
            v_edges[lb.bit_length() - 1].append(j)
            x ^= lb
    failed: set[int] = set()
    solved: dict[int, tuple] = {}
    spend = budget.spend if budget is not None else (lambda n=1: None)
    tick = deadline.tick if deadline is not None else (lambda: None)

    def neighbourhood(c: int) -> int:
        out = 0
        x = c
        while x:
            lb = x & -x
            for j in v_edges[lb.bit_length() - 1]:
                out |= em[j]
            x ^= lb
        return out & ~c

    def components(c: int, chi: int) -> list[int]:
        rest = c & ~chi
        out = []
        while rest:
            start = rest & -rest
            comp = start
            frontier = start
            rest &= ~start
            while frontier:
                nxt = 0
                x = frontier
                while x:
                    lb = x & -x
                    for j in v_edges[lb.bit_length() - 1]:
                        nxt |= em[j]
                    x ^= lb
                nxt &= rest
                rest &= ~nxt
                comp |= nxt
                frontier = nxt
            out.append(comp)
        return out

    def frame(c: int):
        """Solve component c: yields child components to solve and receives their results (a trampoline, so deep
        decompositions need no Python recursion)."""
        conn = neighbourhood(c)
        scope = c | conn
        cands = [j for j in range(len(em)) if em[j] & scope]
        for r in range(1, k + 1):
            for sep in itertools.combinations(cands, r):
                tick()
                spend()
                lv = 0
                for j in sep:
                    lv |= em[j]
                if conn & ~lv or not lv & c:
                    continue
                chi = lv & scope
                kids = components(c, chi)
                children = []
                for d in kids:
                    sub = yield d
                    if sub is None:
                        break
                    children.append(sub)
                else:
                    node = (sep, chi, tuple(children))
                    solved[c] = node
                    return node
        failed.add(c)
        return None

    def decomp(root_c: int) -> tuple | None:
        stack = [frame(root_c)]
        value = None
        while stack:
            try:
                d = stack[-1].send(value)
            except StopIteration as stop:
                stack.pop()
                value = stop.value
                continue
            if d in solved:
                value = solved[d]
            elif d in failed:
                value = None
            else:
                stack.append(frame(d))
                value = None
        return value

    if not em:
        return Decomposition()
    root = decomp(full)
    if root is None:
        return None
    t = Tree()
    todo: list[tuple[tuple, int | None]] = [(root, None)]
    while todo:
        (sep, chi, kids), p = todo.pop()
        bag = [verts[i] for i in range(len(verts)) if chi >> i & 1]
        i = t.add(bag, [names[j] for j in sep], p)
        todo.extend((kid, i) for kid in kids)
    return t.freeze()
