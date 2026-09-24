"""Reductions, each serving only the measures DESIGN §3.2 (and ruling Q3) allow, with lifting back to H.

=====================  ===================  =========================================  ====  ==========================
reduction              ghw, fhw             tw                                         hw    lifting
=====================  ===================  =========================================  ====  ==========================
lonely role (1 edge)   sound                only as the simplicial rule                no    a leaf, bag e, guard {e}
subsumed edge          sound                sound (primal graph unchanged)             no    none
twin merge             sound                **not used** (K_n has tw n-1)              no    add the twin beside it
universal role         sound                exact, +1 per role                         no    add it to every bag
block split            max over blocks      max over blocks                            no    join at the cut role
=====================  ===================  =========================================  ====  ==========================

hw is never reduced (F1). ``core(h)`` gives the ghw/fhw core: the set hypergraph after GYO, twin merging and
universal-role removal to a fixpoint, split into the blocks (biconnected components) of its primal graph.
``tw_reduce(h)`` removes the universal roles of H, applies the lonely-role (simplicial) rule through GYO, then the
general simplicial rule, and splits what is left into blocks. ``lift_core`` and ``lift_tw`` turn per-block
decompositions into a decomposition of H, which the caller validates on H: no certificate rests on a reduction
theorem.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Mapping, Sequence

from .acyclicity import gyo
from .decomposition import Decomposition, Tree
from .hypergraph import Hypergraph
from .steps import Deadline

__all__ = ["Core", "TwReduced", "core", "tw_reduce", "lift_core", "lift_tw", "blocks", "primal", "reroot"]

ONE = Fraction(1)


# ------------------------------------------------------------------------------------------------ graphs
def primal(edges: Mapping[str, frozenset] | Sequence[tuple[str, frozenset]]) -> dict[str, set]:
    """The primal (Gaifman) graph: role -> neighbours."""
    items = edges.items() if isinstance(edges, Mapping) else edges
    nb: dict[str, set] = {}
    for _, e in items:
        for v in e:
            s = nb.setdefault(v, set())
            s.update(e)
    for v, s in nb.items():
        s.discard(v)
    return nb


def blocks(adj: Mapping[str, set]) -> list[frozenset]:
    """The blocks (biconnected components) of a graph, isolated vertices as blocks of one, iteratively
    (Hopcroft-Tarjan). Deterministic: vertices in sorted order."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    out: list[frozenset] = []
    counter = 0
    for root in sorted(adj):
        if root in index:
            continue
        if not adj[root]:
            index[root] = counter
            counter += 1
            out.append(frozenset([root]))
            continue
        index[root] = low[root] = counter
        counter += 1
        edge_stack: list[tuple[str, str]] = []
        stack: list[tuple[str, str | None, Any]] = [(root, None, iter(sorted(adj[root])))]
        while stack:
            v, parent, it = stack[-1]
            advanced = False
            for w in it:
                if w == parent:
                    continue
                if w not in index:
                    edge_stack.append((v, w))
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append((w, v, iter(sorted(adj[w]))))
                    advanced = True
                    break
                if index[w] < index[v]:
                    edge_stack.append((v, w))
                    low[v] = min(low[v], index[w])
            if advanced:
                continue
            stack.pop()
            if parent is not None:
                low[parent] = min(low[parent], low[v])
                if low[v] >= index[parent]:
                    comp: set = set()
                    while edge_stack:
                        a, b = edge_stack.pop()
                        comp.add(a)
                        comp.add(b)
                        if (a, b) == (parent, v):
                            break
                    out.append(frozenset(comp))
    return out


def reroot(t: Tree, new_root: int) -> None:
    """Make ``new_root`` the root of its tree in ``t`` by reversing the parent links on its path to the root."""
    prev = None
    cur: int | None = new_root
    while cur is not None:
        nxt = t.parent[cur]
        t.parent[cur] = prev
        prev, cur = cur, nxt


def _find_node(t: Tree, index: dict[str, list[int]], roles: set) -> int | None:
    """A node whose bag holds ``roles`` (an empty set: the first root)."""
    if not roles:
        return t.roots()[0] if len(t) else None
    rare = min(roles, key=lambda v: len(index.get(v, ())))
    for i in index.get(rare, ()):
        if roles <= t.bags[i]:
            return i
    return None


def _index(t: Tree) -> dict[str, list[int]]:
    idx: dict[str, list[int]] = {}
    for i, b in enumerate(t.bags):
        for v in b:
            idx.setdefault(v, []).append(i)
    return idx


def glue(parts: Sequence[tuple[frozenset, Tree]]) -> Tree:
    """Join per-block decompositions into one tree: blocks sharing a cut role are linked through nodes holding it
    (block-cut tree order); blocks of different components stay separate roots (they share no role)."""
    t = Tree()
    offsets: list[int] = []
    for _, sub in parts:
        off = len(t)
        offsets.append(off)
        for b, c, p in zip(sub.bags, sub.covers, sub.parent):
            t.bags.append(set(b))
            t.covers.append(dict(c))
            t.parent.append(None if p is None else p + off)
    # each block's own nodes form one tree: its root is the node with parent None within its range
    ranges = [(offsets[i], offsets[i] + len(parts[i][1])) for i in range(len(parts))]
    by_role: dict[str, list[int]] = {}
    for i, (blk, _) in enumerate(parts):
        for v in blk:
            by_role.setdefault(v, []).append(i)
    idx = _index(t)
    seen = [False] * len(parts)
    for start in range(len(parts)):
        if seen[start]:
            continue
        seen[start] = True
        queue = [start]
        while queue:
            b = queue.pop(0)
            for v in sorted(parts[b][0]):
                for other in by_role.get(v, ()):
                    if seen[other]:
                        continue
                    seen[other] = True
                    lo, hi = ranges[b]
                    here = next(i for i in idx[v] if lo <= i < hi)
                    lo2, hi2 = ranges[other]
                    there = next(i for i in idx[v] if lo2 <= i < hi2)
                    reroot(t, there)
                    t.parent[there] = here
                    queue.append(other)
    return t


# ------------------------------------------------------------------------------------------------ ghw/fhw core
@dataclass
class Core:
    """The ghw/fhw core: ``edges`` (relation -> roles, names of the set hypergraph), its ``blocks`` (role sets),
    the reduction ``steps`` in order, and a ``summary`` for the report."""

    edges: dict[str, frozenset]
    blocks: list[frozenset]
    steps: list[tuple] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    @property
    def roles(self) -> frozenset:
        return frozenset(v for e in self.edges.values() for v in e)

    def block_edges(self, blk: frozenset) -> list[tuple[str, frozenset]]:
        """The core edges restricted to a block (non-empty traces, names kept)."""
        return [(n, e & blk) for n, e in self.edges.items() if e & blk]


def core(h: Hypergraph) -> Core:
    """GYO, twin merging and universal-role removal on the set hypergraph until none applies; then blocks."""
    d = h.distinct()
    order = list(d.names)
    cur: dict[str, frozenset] = dict(d.edges)
    steps: list[tuple] = []
    summary = {"gyo_roles": 0, "gyo_relations": 0, "twins": 0, "universal": 0}
    while True:
        changed = False
        g = gyo([(n, cur[n]) for n in order if n in cur])
        if g.steps:
            changed = True
            steps.extend(g.steps)
            summary["gyo_roles"] += sum(len(s[2]) for s in g.steps if s[0] == "lonely")
            summary["gyo_relations"] += sum(1 for s in g.steps if s[0] in ("subsumed", "empty"))
        cur = dict(g.residue)
        if not cur:
            break
        # twins: roles in exactly the same relations; keep the first in sorted order
        star: dict[str, set] = {}
        for n, e in cur.items():
            for v in e:
                star.setdefault(v, set()).add(n)
        groups: dict[frozenset, list[str]] = {}
        for v in sorted(star):
            groups.setdefault(frozenset(star[v]), []).append(v)
        for sig, vs in groups.items():
            for y in vs[1:]:
                steps.append(("twin", y, vs[0], tuple(sorted(sig, key=order.index))))
                summary["twins"] += 1
                for n in sig:
                    cur[n] = cur[n] - {y}
                changed = True
        # universal roles: in every relation left (two or more)
        if len(cur) >= 2:
            common = frozenset.intersection(*cur.values())
            for u in sorted(common):
                steps.append(("universal", u, tuple(n for n in order if n in cur)))
                summary["universal"] += 1
                for n in list(cur):
                    cur[n] = cur[n] - {u}
                changed = True
        for n in [n for n in order if n in cur and not cur[n]]:
            steps.append(("empty", n))
            del cur[n]
        if not changed:
            break
    edges = {n: cur[n] for n in order if n in cur}
    blks = [b for b in blocks(primal(edges))] if edges else []
    summary["blocks"] = len(blks)
    summary["core_roles"] = len({v for e in edges.values() for v in e})
    summary["core_relations"] = len(edges)
    return Core(edges=edges, blocks=blks, steps=steps, summary=summary)


def lift_core(h: Hypergraph, c: Core, parts: Sequence[tuple[frozenset, Tree]]) -> Decomposition:
    """Glue per-block decompositions of the core (covers over core relations) and undo every reduction step, last
    first: the result is a decomposition of H whose covers name relations of H."""
    t = glue(parts) if parts else Tree()
    if not len(t):
        t.add([], None, None)
    cur: dict[str, set] = {n: set(e) for n, e in c.edges.items()}
    idx = _index(t)
    node_of: dict[str, int] = {}
    root = t.roots()[0]
    for n, e in cur.items():
        found = _find_node(t, idx, e)
        if found is None:
            raise ValueError(f"core relation {n} lies in no bag of the block decompositions")
        node_of[n] = found
    for step in reversed(c.steps):
        kind = step[0]
        if kind == "universal":
            _, u, names = step
            first = names[0]
            for i in range(len(t)):
                t.bags[i].add(u)
                if not t.covers[i]:
                    t.covers[i] = {first: ONE}
            for n in names:
                cur.setdefault(n, set()).add(u)
        elif kind == "twin":
            _, y, x, names = step
            for i in range(len(t)):
                if x in t.bags[i]:
                    t.bags[i].add(y)
            for n in names:
                cur.setdefault(n, set()).add(y)
        elif kind == "subsumed":
            _, n, f, roles = step
            cur[n] = set(roles)
            node_of[n] = node_of[f]
        elif kind == "empty":
            _, n = step
            cur[n] = set()
            node_of[n] = root
        elif kind == "lonely":
            _, n, vs = step
            bag = cur[n] | set(vs)
            leaf = t.add(bag, {n: ONE}, node_of[n])
            cur[n] = bag
            node_of[n] = leaf
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown step {kind}")
    return t.freeze()


# ------------------------------------------------------------------------------------------------ tw
@dataclass
class TwReduced:
    """The tw reduction: ``offset`` universal roles removed (tw + offset), the GYO ``steps`` (lonely roles as the
    simplicial rule, subsumed edges), the general ``simplicial`` eliminations (role, neighbourhood), the remaining
    graph ``adj`` and its ``blocks``, and ``lower`` = the largest neighbourhood eliminated (a tw lower bound before
    the offset)."""

    offset: int
    universal: tuple[str, ...]
    steps: list[tuple]
    residue_edges: dict[str, frozenset]
    simplicial: list[tuple[str, frozenset]]
    adj: dict[str, set]
    blocks: list[frozenset]
    lower: int
    complete: bool = True  # False when the simplicial pass stopped at the deadline
    summary: dict[str, int] = field(default_factory=dict)


def tw_reduce(h: Hypergraph, *, deadline: Deadline | None = None, max_degree: int = 1000) -> TwReduced:
    """Universal roles out (+1 each), lonely roles by GYO (simplicial: tw >= |e| - 1), then simplicial roles of
    degree <= ``max_degree`` in the primal graph, then blocks."""
    d = h.distinct()
    uni = tuple(h.universal_roles)
    if uni and set(uni) == set(h.vertices):
        # tw(G + a universal role) = tw(G) + 1 needs G non-empty: when every role is universal (one role set),
        # keep one of them, so tw = (|U| - 1) + tw(a single role) = |U| - 1
        uni = uni[:-1]
    su = set(uni)
    edges = [(n, e - su) for n, e in d.edges]
    edges = [(n, e) for n, e in edges if e]
    g = gyo(edges)
    lower = 0
    # the bag of a lonely batch is the edge before the batch: replay to get its size
    cur = {n: set(e) for n, e in edges}
    for s in g.steps:
        if s[0] == "lonely":
            lower = max(lower, len(cur[s[1]]) - 1)
            cur[s[1]] -= s[2]
        elif s[0] in ("subsumed", "empty"):
            cur.pop(s[1], None)
    adj = primal(g.residue)
    simplicial: list[tuple[str, frozenset]] = []
    complete = True
    # general simplicial rule with a worklist; a simplicial role stays simplicial when a neighbour goes
    queue = sorted(adj)
    known: set = set()
    try:
        while queue:
            nxt: list[str] = []
            for v in queue:
                if v not in adj:
                    continue
                if deadline is not None:
                    deadline.tick()
                nbrs = adj[v]
                if len(nbrs) > max_degree:
                    continue
                if v not in known:
                    if not all(len(nbrs - adj[a]) == 1 for a in nbrs):
                        continue
                known.add(v)
                lower = max(lower, len(nbrs))
                simplicial.append((v, frozenset(nbrs)))
                for a in nbrs:
                    adj[a].discard(v)
                    if a not in known:
                        nxt.append(a)
                del adj[v]
            queue = sorted(set(nxt))
    except Exception as e:  # StepTimeout: keep what was eliminated
        if type(e).__name__ != "StepTimeout":
            raise
        complete = False
    blks = blocks(adj) if adj else []
    summary = {"universal": len(uni), "simplicial": sum(len(s[2]) for s in g.steps if s[0] == "lonely")
               + len(simplicial), "blocks": len(blks), "remaining_roles": len(adj)}
    return TwReduced(offset=len(uni), universal=uni, steps=g.steps, residue_edges=dict(g.residue),
                     simplicial=simplicial, adj=adj, blocks=blks, lower=lower, complete=complete, summary=summary)


def lift_tw(h: Hypergraph, r: TwReduced, parts: Sequence[tuple[frozenset, Tree]]) -> Decomposition:
    """Glue per-block tree decompositions, re-insert the simplicial roles (a leaf N ∪ {v} under a bag holding N),
    undo the GYO steps (a leaf per lonely batch) and add the universal roles to every bag."""
    t = glue(parts) if parts else Tree()
    if not len(t):
        t.add([], None, None)
    idx = _index(t)
    for v, nbrs in reversed(r.simplicial):
        at = _find_node(t, idx, set(nbrs))
        if at is None:
            raise ValueError(f"no bag holds the neighbourhood of simplicial role {v}")
        leaf = t.add(set(nbrs) | {v}, None, at)
        for u in t.bags[leaf]:
            idx.setdefault(u, []).append(leaf)
    cur: dict[str, set] = {n: set(e) for n, e in r.residue_edges.items()}
    node_of: dict[str, int] = {}
    root = t.roots()[0]
    for n, e in cur.items():
        found = _find_node(t, idx, e)
        if found is None:
            raise ValueError(f"residue relation {n} lies in no bag")
        node_of[n] = found
    for step in reversed(r.steps):
        kind = step[0]
        if kind == "subsumed":
            _, n, f, roles = step
            cur[n] = set(roles)
            node_of[n] = node_of[f]
        elif kind == "empty":
            _, n = step
            cur[n] = set()
            node_of[n] = root
        elif kind == "lonely":
            _, n, vs = step
            bag = cur[n] | set(vs)
            leaf = t.add(bag, None, node_of[n])
            cur[n] = bag
            node_of[n] = leaf
    for u in r.universal:
        for b in t.bags:
            b.add(u)
    return t.freeze()
