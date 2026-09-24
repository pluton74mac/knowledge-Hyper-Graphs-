"""Fagin's acyclicity classes with witnesses (DESIGN §3.1; R01 §1).

Berge ⊂ gamma ⊂ beta ⊂ alpha. ``classify`` runs the tests from alpha down and stops at the first failure:

1. **alpha** by ``khg_contracts.schema.is_alpha_acyclic`` (the C1 GYO). If it fails, the class is ``cyclic`` and the
   witness is the GYO residue; the stricter tests are implied false and not run (``None`` in ``tests``). An indexed
   ear removal (``gyo``) must agree, and when H is alpha-acyclic its links give the join tree, checked for running
   intersection: the width-1 HD.
2. **beta** by indexed nest-point elimination. If it fails, the class is ``alpha`` and the witness is a beta-cycle
   (a chordless incidence cycle x1 E1 ... xk Ek, k >= 3) searched with a budget in the beta residue; a cycle of
   H[residue] lifts to H. When the budget runs out, the residue is the witness, flagged incomplete.
3. **gamma** by the indexed D'Atri-Moscarini reduction. If it fails, the class is ``beta`` and the witness is a
   gamma-triangle (x, y, z: {x,y}, {y,z}, {x,y,z} in H[{x,y,z}]) searched in the DM residue.
4. **Berge** by union-find on the incidence graph of the named multi-hypergraph. If it fails, the class is ``gamma``
   and the witness is the cycle v1 R1 ... vk Rk. Otherwise the class is ``berge``.

Every witness is verified against its definition on H; a contradiction raises ``InternalError``.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .decomposition import Decomposition, join_tree_decomposition
from .hypergraph import Hypergraph

__all__ = ["Acyclicity", "Witness", "InternalError", "classify", "gyo", "GYO", "berge", "beta_reduce", "beta_cycle",
           "dm_reduce", "gamma_triangle", "CLASSES", "verify_witness", "running_intersection"]

CLASSES = ("berge", "gamma", "beta", "alpha", "cyclic")
TESTS = ("alpha", "beta", "gamma", "berge")


class InternalError(RuntimeError):
    """A result contradicts the hierarchy or a witness fails its definition: the run stops."""


@dataclass(frozen=True)
class Witness:
    """``kind``: ``gyo_residue`` (list of role lists), ``beta_cycle`` / ``berge_cycle`` (alternating role and
    relation names), ``gamma_triangle`` (three roles), ``beta_residue`` / ``dm_residue`` (role lists, when the
    search budget ran out). ``complete`` is False for a residue given because a search ran out of budget."""

    kind: str
    value: Any
    complete: bool = True

    def to_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "value": self.value, "complete": self.complete}


@dataclass(frozen=True)
class Acyclicity:
    """``cls`` in ``CLASSES``; ``tests`` maps alpha, beta, gamma, berge to True, False or None (implied false, not
    run); ``first_failed`` names the first failing test; ``join_tree`` is the width-1 HD when alpha-acyclic."""

    cls: str
    tests: dict = field(default_factory=dict)
    first_failed: str | None = None
    witness: Witness | None = None
    join_tree: Decomposition | None = None
    residue_size: tuple[int, int] | None = None  # GYO residue (relations, roles) when cyclic

    def to_json(self, *, with_join_tree: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {"class": self.cls, "tests": dict(self.tests), "first_failed": self.first_failed,
                               "witness": self.witness.to_json() if self.witness else None}
        if self.residue_size is not None:
            out["gyo_residue_size"] = {"relations": self.residue_size[0], "roles": self.residue_size[1]}
        if with_join_tree:
            out["join_tree"] = self.join_tree.to_json() if self.join_tree is not None else None
        return out


# ------------------------------------------------------------------------------------------------ alpha (GYO)
@dataclass
class GYO:
    """The result of an indexed GYO run: ``residue`` (name -> roles left), the join links (child, parent) of the
    edges removed as contained, the ``roots`` (edges emptied) and the ``steps`` in order, for lifting:
    ``("lonely", edge, roles)``, ``("subsumed", edge, by, roles_at_removal)``, ``("empty", edge)``."""

    residue: dict[str, frozenset]
    links: list[tuple[str, str]]
    roots: list[str]
    steps: list[tuple]

    @property
    def acyclic(self) -> bool:
        return not self.residue


def gyo(edges: Sequence[tuple[str, frozenset]] | Mapping[str, Any]) -> GYO:
    """GYO by ear removal with a role -> relations index: remove roles in one relation (lonely) and relations
    contained in another (of two equal ones, the later in order goes). A contained relation is linked to the first
    relation in order that contains it. Each role's relations are kept in an insertion-ordered dict, so that first
    superset is found by an early-exit scan of the rarest role's relations."""
    items = list(edges.items()) if isinstance(edges, Mapping) else list(edges)
    order = {n: i for i, (n, _) in enumerate(items)}
    cur: dict[str, set] = {n: set(e) for n, e in items}
    inc: dict[str, dict] = {}
    for n, e in items:
        for v in e:
            inc.setdefault(v, {})[n] = None
    steps: list[tuple] = []
    links: list[tuple[str, str]] = []
    roots: list[str] = []
    dirty_v: set = set(inc)
    dirty_e: set = set(cur)
    while dirty_v or dirty_e:
        lonely: dict[str, set] = {}
        for v in dirty_v:
            s = inc.get(v)
            if s is not None and len(s) == 1:
                lonely.setdefault(next(iter(s)), set()).add(v)
        dirty_v = set()
        for n in sorted(lonely, key=order.__getitem__):
            vs = lonely[n]
            cur[n] -= vs
            for v in vs:
                del inc[v]
            steps.append(("lonely", n, frozenset(vs)))
            dirty_e.add(n)
        while dirty_e:
            batch = sorted(dirty_e, key=order.__getitem__)
            dirty_e = set()
            for n in batch:
                if n not in cur:
                    continue
                e = cur[n]
                if not e:
                    del cur[n]
                    steps.append(("empty", n))
                    roots.append(n)
                    continue
                rare = min(e, key=lambda v: (len(inc[v]), v))
                size, on = len(e), order[n]
                f = None
                for m in inc[rare]:
                    if m != n:
                        cm = cur[m]
                        if (len(cm) > size or order[m] < on) and e <= cm:
                            f = m
                            break
                if f is None:
                    continue
                links.append((n, f))
                steps.append(("subsumed", n, f, frozenset(e)))
                del cur[n]
                for v in e:
                    s = inc[v]
                    del s[n]
                    if len(s) == 1:
                        dirty_v.add(v)
        # lonely roles found above feed the next round
    residue = {n: frozenset(cur[n]) for n, _ in items if n in cur}
    return GYO(residue=residue, links=links, roots=roots, steps=steps)


def running_intersection(h: Hypergraph, links: Sequence[tuple[str, str]]) -> bool:
    """For each role, the relations holding it are connected in the join forest given by ``links``."""
    adj: dict[str, set] = {n: set() for n in h.names}
    for a, b in links:
        adj[a].add(b)
        adj[b].add(a)
    holders: dict[str, list[str]] = {}
    for n, e in h.edges:
        for v in e:
            holders.setdefault(v, []).append(n)
    for v, ns in holders.items():
        nodes = set(ns)
        start = ns[0]
        seen, todo = {start}, [start]
        while todo:
            x = todo.pop()
            for y in adj[x]:
                if y in nodes and y not in seen:
                    seen.add(y)
                    todo.append(y)
        if seen != nodes:
            return False
    return True


# ------------------------------------------------------------------------------------------------ Berge
def berge(h: Hypergraph) -> tuple[bool, list[str]]:
    """Union-find on the incidence graph of the multi-hypergraph (each named relation its own node), relations in
    order and roles sorted within each. Returns (acyclic, cycle as [v1, R1, ..., vk, Rk])."""
    parent: dict[tuple, tuple] = {}

    def find(x: tuple) -> tuple:
        parent.setdefault(x, x)
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    adj: dict[tuple, list] = {}
    for name, e in h.edges:
        en = ("E", name)
        for v in sorted(e):
            vn = ("V", v)
            if find(en) == find(vn):
                path = _forest_path(adj, vn, en)
                return False, [n[1] for n in path]
            parent[find(en)] = find(vn)
            adj.setdefault(en, []).append(vn)
            adj.setdefault(vn, []).append(en)
    return True, []


def _forest_path(adj: dict, a: tuple, b: tuple) -> list:
    prev = {a: None}
    todo = [a]
    while todo:
        x = todo.pop()
        if x == b:
            break
        for y in adj.get(x, ()):
            if y not in prev:
                prev[y] = x
                todo.append(y)
    out = [b]
    while out[-1] != a:
        out.append(prev[out[-1]])
    return out[::-1]


# ------------------------------------------------------------------------------------------------ beta
def _is_chain(sets: list) -> bool:
    ss = sorted(sets, key=len)
    return all(a <= b for a, b in zip(ss, ss[1:]))


def beta_reduce(h: Hypergraph) -> frozenset:
    """Nest-point (beta-leaf) elimination on the set hypergraph with a worklist: a role whose relations form a chain
    under inclusion is removed. Returns the roles left (empty iff beta-acyclic)."""
    d = h.distinct()
    cur: dict[str, set] = {n: set(e) for n, e in d.edges}
    inc: dict[str, set] = {}
    for n, e in d.edges:
        for v in e:
            inc.setdefault(v, set()).add(n)
    heap = list(inc)
    heapq.heapify(heap)
    queued = set(heap)
    while heap:
        x = heapq.heappop(heap)
        queued.discard(x)
        if x not in inc:
            continue
        if not _is_chain([cur[n] for n in inc[x]]):
            continue
        for n in inc.pop(x):
            e = cur[n]
            e.discard(x)
            if not e:
                del cur[n]
                continue
            for y in e:
                if y not in queued:
                    queued.add(y)
                    heapq.heappush(heap, y)
    return frozenset(inc)


def beta_cycle(h: Hypergraph, budget: int = 200_000) -> list[str] | None:
    """A chordless cycle of length >= 6 in the incidence graph of the set hypergraph, as [x1, E1, ..., xk, Ek]
    (each xi in E(i-1) and Ei and in no other cycle edge). Iterative depth-first search with canonical start,
    shortest cycles first; None when ``budget`` extensions are used up or there is none."""
    names: dict[frozenset, str] = {}
    for n, e in h.edges:
        names.setdefault(e, n)
    edges = list(names)
    verts = sorted({v for e in edges for v in e})
    nodes = [("V", v) for v in verts] + [("E", names[e]) for e in edges]
    idx = {x: i for i, x in enumerate(nodes)}
    adj: list[set] = [set() for _ in nodes]
    for e in edges:
        ei = idx[("E", names[e])]
        for v in e:
            vi = idx[("V", v)]
            adj[ei].add(vi)
            adj[vi].add(ei)
    sadj = [sorted(a) for a in adj]
    steps = 0
    for cap in range(6, len(nodes) + 1, 2):
        for s in range(len(verts)):
            path = [s]
            on = {s}
            iters = [iter(sadj[s])]
            while iters:
                it = iters[-1]
                advanced = False
                for nxt in it:
                    steps += 1
                    if steps > budget:
                        return None
                    if nxt <= path[0] or nxt in on:
                        continue
                    an = adj[nxt]
                    if any(p in an for p in path[1:-1]):
                        continue
                    if len(path) >= 2 and path[0] in an:
                        if len(path) + 1 >= 6:
                            return [nodes[i][1] for i in path + [nxt]]
                        continue
                    if len(path) + 1 >= cap:
                        continue
                    path.append(nxt)
                    on.add(nxt)
                    iters.append(iter(sadj[nxt]))
                    advanced = True
                    break
                if not advanced:
                    iters.pop()
                    on.discard(path.pop())
    return None


# ------------------------------------------------------------------------------------------------ gamma
def dm_reduce(h: Hypergraph) -> list[frozenset]:
    """The D'Atri-Moscarini reduction on the set hypergraph: singleton vertex removal (a role in one relation),
    singleton edge removal (a relation of one role) and linearization (a role with the same relations as another),
    until none applies. Returns the residue's role sets (empty iff gamma-acyclic)."""
    d = h.distinct()
    cur: dict[int, set] = {}
    key: dict[frozenset, int] = {}
    inc: dict[str, set] = {}
    for i, (_, e) in enumerate(d.edges):
        cur[i] = set(e)
        key[frozenset(e)] = i
        for v in e:
            inc.setdefault(v, set()).add(i)

    def drop_edge(i: int) -> set:
        e = cur.pop(i)
        key.pop(frozenset(e), None)
        for v in e:
            inc[v].discard(i)
        return e

    def shrink(i: int, v: str) -> None:
        """Remove v from edge i; merge with an equal edge, drop an empty one."""
        e = cur[i]
        key.pop(frozenset(e), None)
        e.discard(v)
        inc[v].discard(i)
        if not e:
            del cur[i]
            return
        k = frozenset(e)
        if k in key and key[k] != i:
            for u in e:
                inc[u].discard(i)
            del cur[i]
            return
        key[k] = i

    while True:
        changed = True
        while changed:
            changed = False
            for v in sorted(inc):
                s = inc.get(v)
                if s is None:
                    continue
                if not s:
                    del inc[v]
                    changed = True
                elif len(s) == 1:
                    (i,) = s
                    shrink(i, v)
                    del inc[v]
                    changed = True
            for i in sorted(cur):
                if i in cur and len(cur[i]) == 1:
                    drop_edge(i)
                    changed = True
        if not cur:
            return []
        # linearization: keep the first role of each group with the same relations
        groups: dict[frozenset, list[str]] = {}
        for v in sorted(inc):
            groups.setdefault(frozenset(inc[v]), []).append(v)
        twins = [v for g in groups.values() for v in g[1:]]
        if not twins:
            return sorted((frozenset(e) for e in cur.values()), key=lambda e: sorted(e))
        for v in twins:
            for i in sorted(inc[v]):
                shrink(i, v)
            del inc[v]


def gamma_triangle(h: Hypergraph, budget: int = 200_000) -> list[str] | None:
    """The first (x, y, z), in lexicographic order of sorted roles with x < z, such that {x,y}, {y,z} and {x,y,z}
    are traces of H on {x,y,z} (Brault-Baron's gamma1a pattern). None past ``budget`` triples."""
    d = h.distinct()
    inc: dict[str, set] = {}
    nb: dict[str, set] = {}
    for i, (_, e) in enumerate(d.edges):
        for v in e:
            inc.setdefault(v, set()).add(i)
            nb.setdefault(v, set()).update(e)
    verts = sorted(inc)
    tried = 0
    for x in verts:
        for y in verts:
            if y == x or y not in nb[x]:
                continue
            xy = inc[x] & inc[y]
            for z in verts:
                if z <= x or z == y or z not in nb[y]:
                    continue
                tried += 1
                if tried > budget:
                    return None
                iz = inc[z]
                if not (xy - iz):
                    continue
                if not (xy & iz):
                    continue
                yz = inc[y] & iz
                if yz - inc[x]:
                    return [x, y, z]
    return None


# ------------------------------------------------------------------------------------------------ verification
def verify_witness(h: Hypergraph, w: Witness) -> bool:
    """Check a complete witness against its definition on H (the multi-hypergraph for Berge, the set hypergraph
    otherwise)."""
    if not w.complete:
        return True
    if w.kind == "berge_cycle":
        c = w.value
        if len(c) < 4 or len(c) % 2:
            return False
        vs, es = c[0::2], c[1::2]
        if len(set(vs)) != len(vs) or len(set(es)) != len(es) or any(e not in h for e in es):
            return False
        k = len(vs)
        return all(vs[i] in h.edge(es[i]) and vs[(i + 1) % k] in h.edge(es[i]) for i in range(k))
    if w.kind == "beta_cycle":
        c = w.value
        if len(c) < 6 or len(c) % 2:
            return False
        vs, es = c[0::2], c[1::2]
        if len(set(vs)) != len(vs) or len(set(es)) != len(es) or any(e not in h for e in es):
            return False
        k = len(vs)
        sets = [h.edge(e) for e in es]
        if len(set(sets)) != k:
            return False
        for i, v in enumerate(vs):
            for j in range(k):
                want = j in (i, (i - 1) % k)
                if (v in sets[j]) != want:
                    return False
        return True
    if w.kind == "gamma_triangle":
        x, y, z = w.value
        t = {x, y, z}
        traces = {frozenset(e & t) for _, e in h.edges}
        return {frozenset((x, y)), frozenset((y, z)), frozenset(t)} <= traces
    if w.kind == "gyo_residue":
        return bool(w.value)
    return False


# ------------------------------------------------------------------------------------------------ classify
def classify(h: Hypergraph, *, budget: int = 200_000) -> Acyclicity:
    """The acyclicity class of H with its witness (module docstring)."""
    from khg_contracts.schema import is_alpha_acyclic

    tests: dict[str, bool | None] = {t: None for t in TESTS}
    if h.is_empty():
        tests = {t: True for t in TESTS}
        return Acyclicity("berge", tests, None, None, Decomposition())
    ok, residue = is_alpha_acyclic(h.as_dict())
    g = gyo(h.edges)
    mine = sorted(sorted(e) for e in g.residue.values())
    if ok != g.acyclic or (not ok and sorted(residue) != mine):
        raise InternalError("the indexed GYO disagrees with khg_contracts.schema.is_alpha_acyclic")
    tests["alpha"] = ok
    if not ok:
        roles = len({v for e in residue for v in e})
        w = Witness("gyo_residue", residue)
        return Acyclicity("cyclic", tests, "alpha", w, None, (len(residue), roles))
    if not running_intersection(h, g.links):
        raise InternalError("the join tree fails the running intersection property")
    jt = join_tree_decomposition(h, g.links)
    # beta
    rest = beta_reduce(h)
    tests["beta"] = not rest
    if rest:
        sub = h.distinct().induced(rest).distinct()
        cyc = beta_cycle(sub, budget)
        if cyc is None:
            w = Witness("beta_residue", sorted(sorted(e) for _, e in sub.edges), complete=False)
        else:
            w = Witness("beta_cycle", cyc)  # relation names of H already: traces keep their relation's name
        _verify(h, w)
        return Acyclicity("alpha", tests, "beta", w, jt)
    # gamma
    res = dm_reduce(h)
    tests["gamma"] = not res
    if res:
        sub = Hypergraph(tuple((f"D{i}", e) for i, e in enumerate(res)))
        tri = gamma_triangle(sub, budget)
        if tri is None:
            w = Witness("dm_residue", [sorted(e) for e in res], complete=False)
        else:
            w = Witness("gamma_triangle", tri)
        _verify(h, w)
        return Acyclicity("beta", tests, "gamma", w, jt)
    # Berge
    ok_b, cyc = berge(h)
    tests["berge"] = ok_b
    if not ok_b:
        w = Witness("berge_cycle", cyc)
        _verify(h, w)
        return Acyclicity("gamma", tests, "berge", w, jt)
    if any(len(h.edge(g[0])) >= 2 for g in h.duplicate_groups):
        raise InternalError("a Berge-acyclic multi-hypergraph cannot hold two relations on the same two roles")
    return Acyclicity("berge", tests, None, None, jt)


def _verify(h: Hypergraph, w: Witness) -> None:
    target = h if w.kind == "berge_cycle" else h.distinct()
    if not verify_witness(target, w):
        raise InternalError(f"the {w.kind} witness fails its definition on H: {w.value!r}")
