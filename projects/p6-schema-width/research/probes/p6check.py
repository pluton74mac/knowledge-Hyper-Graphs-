"""P6 probe: a pure-Python reference for the schema checker (acyclicity class, witnesses, exact widths on small cores).

This is a research prototype, not the P6 checker. It exists to (1) pin down the algorithms the report recommends,
(2) cross-check them against brute-force definitions and against the external solvers, and (3) run the packaged P2
schemas end to end. Standard library only, except ``scipy`` for the fractional edge cover LP (optional).

Hypergraph input: a mapping ``{edge_name: iterable_of_vertices}`` (the shape of ``schema_hypergraph(...)["hyperedges"]``).

Acyclicity (Fagin 1983; characterisations as re-derived by Brault-Baron 2016, arXiv:1403.7076):
- Berge:  the incidence graph (vertices + named edges) is a forest.                         -> witness: a cycle
- gamma:  D'Atri-Moscarini reduction (singleton vertex removal, singleton edge removal,
          linearization) empties the hypergraph (Brault-Baron, Def. 8 and the DM characterisation).
                                                                                             -> witness: residue, gamma triangle
- beta:   repeated removal of beta leaves (nest points: the edges through x form a chain)
          empties the hypergraph (Brault-Baron, Def. 4 and Corollary 10).                    -> witness: residue, beta cycle
- alpha:  GYO reduction empties it (Graham 1979; Yu and Ozsoyoglu 1979).                     -> witness: residue; join tree if acyclic

Widths:
- tw     treewidth of the primal (Gaifman) graph,     exact by the subset DP over elimination orderings
- ghw    generalised hypertree width,                 same DP with bag cost rho(B)   (Moll, Tazari, Thurley 2012)
- fhw    fractional hypertree width,                  same DP with bag cost rho*(B)  (LP; needs scipy)
- hw     hypertree width,                             det-k-decomp-style search over normal-form HDs (Gottlob, Leone,
                                                       Scarcello 2002, k-decomp; Gottlob and Samer 2008), k = 1, 2, ...
ghw and fhw are computed on the reduced core (degree-1 vertices, subsumed edges and twin vertices removed), which
preserves both widths when they are >= 1 (argument in the report, section 5.2). hw is computed on the input as given.
"""
from __future__ import annotations

import itertools
import json
import sys
from fractions import Fraction
from functools import lru_cache
from typing import Iterable, Mapping

Edges = dict[str, frozenset]


# ----------------------------------------------------------------------------------------------------------- helpers
def normalise(hg: Mapping[str, Iterable[str]] | Mapping) -> Edges:
    if "hyperedges" in hg and isinstance(hg["hyperedges"], Mapping):  # schema_hypergraph output
        hg = hg["hyperedges"]
    return {str(k): frozenset(map(str, v)) for k, v in hg.items() if len(list(v)) > 0}


def as_set_hypergraph(edges: Edges) -> set[frozenset]:
    return {e for e in edges.values() if e}


def induced(H: set[frozenset], keep: set) -> set[frozenset]:
    return {e & keep for e in H if e & keep}


# ----------------------------------------------------------------------------------------------------------- Berge
def berge(edges: Edges) -> tuple[bool, list[str]]:
    """Incidence graph of the multi-hypergraph (each named edge is its own node). Returns (acyclic, cycle)."""
    parent: dict = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    adj: dict = {}
    for name, e in edges.items():
        en = ("E", name)
        for v in sorted(e):
            vn = ("V", v)
            if find(en) == find(vn):  # closing a cycle: path vn ~> en in the forest, plus this link
                path = _forest_path(adj, vn, en)
                return False, [n[1] for n in path]
            parent[find(en)] = find(vn)
            adj.setdefault(en, set()).add(vn)
            adj.setdefault(vn, set()).add(en)
    return True, []


def _forest_path(adj, a, b):
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


# ----------------------------------------------------------------------------------------------------------- alpha
def gyo(edges: Edges) -> tuple[bool, list[list[str]], list[tuple[str, str]]]:
    """GYO by ear removal. Returns (acyclic, residue as sorted vertex lists, join-tree links (child, parent)).

    An edge e is an ear when the vertices e shares with the other edges all lie in one other edge f (its witness).
    Removing ears until one edge per connected component remains is Graham's reduction; the (ear, witness) pairs
    form a join forest. Duplicate edges are ears of each other."""
    live = dict(edges)
    links: list[tuple[str, str]] = []
    changed = True
    while changed and len(live) > 1:
        changed = False
        for name in sorted(live):
            e = live[name]
            others = [g for g in live if g != name]
            shared = e & frozenset().union(*(live[g] for g in others)) if others else frozenset()
            if not shared:
                continue  # isolated edge: a component on its own, handled at the end
            for g in sorted(others):
                if shared <= live[g]:
                    links.append((name, g))
                    del live[name]
                    changed = True
                    break
            if changed:
                break
    # what is left: pairwise-disjoint edges are acyclic (a forest of single-node trees); anything else is cyclic
    rest = list(live.values())
    disjoint = all(not (a & b) for a, b in itertools.combinations(rest, 2))
    if disjoint:
        return True, [], links
    # residue in the sense of vertex-and-edge GYO (as khg_contracts.schema.is_alpha_acyclic reports it)
    return False, _gyo_residue(edges), links


def _gyo_residue(edges: Edges) -> list[list[str]]:
    es = [set(e) for e in edges.values() if e]
    changed = True
    while changed:
        changed = False
        count: dict = {}
        for e in es:
            for v in e:
                count[v] = count.get(v, 0) + 1
        for e in es:
            lone = {v for v in e if count[v] == 1}
            if lone:
                e -= lone
                changed = True
        keep = []
        for i, e in enumerate(es):
            if not e or any(j != i and e <= f and (e != f or j < i) for j, f in enumerate(es)):
                changed = True
                continue
            keep.append(e)
        es = keep
    return [sorted(e) for e in es]


def check_join_tree(edges: Edges, links: list[tuple[str, str]]) -> bool:
    """Running-intersection check: for each vertex, the tree nodes containing it are connected."""
    adj: dict[str, set[str]] = {n: set() for n in edges}
    for a, b in links:
        adj[a].add(b)
        adj[b].add(a)
    for v in set().union(*edges.values()) if edges else ():
        nodes = {n for n, e in edges.items() if v in e}
        start = next(iter(nodes))
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


# ----------------------------------------------------------------------------------------------------------- beta
def beta(edges: Edges) -> tuple[bool, list[list[str]]]:
    """Beta-leaf (nest point) elimination. Returns (acyclic, residue)."""
    H = as_set_hypergraph(edges)
    while H:
        V = set().union(*H)
        leaf = None
        for x in sorted(V):
            star = sorted((e for e in H if x in e), key=len)
            if all(a <= b for a, b in zip(star, star[1:])):
                leaf = x
                break
        if leaf is None:
            return False, sorted(sorted(e) for e in H)
        H = induced(H, V - {leaf})
    return True, []


def beta_cycle(edges: Edges, budget: int = 200_000) -> list[str] | None:
    """A chordless cycle of length >= 6 in the incidence graph of the set hypergraph, read as (x1, E1, ..., xk, Ek),
    k >= 3, where each xi lies in E(i-1) and Ei and in no other edge of the cycle. Such a cycle exists iff the
    hypergraph is not beta-acyclic (beta-acyclic iff the incidence graph is chordal bipartite; Tarjan and Yannakakis
    1984, as stated by Ordyniak, Paulusma and Szeider 2013, Prop. 2). Depth-first search for an induced cycle with
    canonical start (smallest node); ``budget`` bounds the number of extensions tried."""
    names: dict = {}
    for n, e in edges.items():
        names.setdefault(e, n)  # set hypergraph, keep the first name
    H = list(names)
    V = sorted(set().union(*H)) if H else []
    nodes = [("V", v) for v in V] + [("E", names[e]) for e in H]
    idx = {x: i for i, x in enumerate(nodes)}
    adj = [set() for _ in nodes]
    for e in H:
        ei = idx[("E", names[e])]
        for v in e:
            vi = idx[("V", v)]
            adj[ei].add(vi)
            adj[vi].add(ei)
    steps = [0]

    def extend(path: list[int], on: set[int], cap: int) -> list[int] | None:
        last = path[-1]
        for nxt in sorted(adj[last]):
            steps[0] += 1
            if steps[0] > budget:
                return None
            if nxt <= path[0] or nxt in on:
                continue
            # induced: nxt may touch only `last` among path[1:-1]; touching path[0] closes the cycle
            if any(p in adj[nxt] for p in path[1:-1]):
                continue
            if len(path) >= 2 and path[0] in adj[nxt]:
                if len(path) + 1 >= 6:
                    return path + [nxt]
                continue
            if len(path) + 1 >= cap:
                continue
            on.add(nxt)
            got = extend(path + [nxt], on, cap)
            on.discard(nxt)
            if got:
                return got
        return None

    for cap in range(6, len(nodes) + 1, 2):  # shortest witness first (iterative deepening on the cycle length)
        for s in range(len(nodes)):
            if nodes[s][0] != "V":
                continue
            got = extend([s], {s}, cap)
            if got:
                return [nodes[i][1] for i in got]
        if steps[0] > budget:
            return None
    return None


# ----------------------------------------------------------------------------------------------------------- gamma
def gamma(edges: Edges) -> tuple[bool, list[list[str]]]:
    """D'Atri-Moscarini reduction on the set hypergraph. Returns (acyclic, residue)."""
    H = as_set_hypergraph(edges)
    while H:
        V = set().union(*H)
        star = {x: frozenset(e for e in H if x in e) for x in V}
        # singleton vertex removal
        x = next((x for x in sorted(V) if len(star[x]) == 1), None)
        if x is not None:
            H = induced(H, V - {x})
            continue
        # singleton edge removal
        e = next((e for e in H if len(e) == 1), None)
        if e is not None:
            H = H - {e}
            continue
        # linearization: two vertices in exactly the same edges
        seen: dict = {}
        twin = None
        for x in sorted(V):
            if star[x] in seen:
                twin = x
                break
            seen[star[x]] = x
        if twin is not None:
            H = induced(H, V - {twin})
            continue
        return False, sorted(sorted(e) for e in H)
    return True, []


def gamma_triangle(edges: Edges) -> list[str] | None:
    """x, y, z with {x,y}, {y,z}, {x,y,z} all in H[{x,y,z}] (Brault-Baron's (gamma1a) pattern)."""
    H = as_set_hypergraph(edges)
    V = sorted(set().union(*H)) if H else []
    for x, y, z in itertools.permutations(V, 3):
        if x > z:
            continue
        tr = {e & {x, y, z} for e in H}
        if {x, y} in tr and {y, z} in tr and {x, y, z} in tr:
            return [x, y, z]
    return None


# ----------------------------------------------------------------------------------------------------------- class
def classify(edges: Edges) -> dict:
    edges = normalise(edges)
    b_ok, b_cycle = berge(edges)
    g_ok, g_res = gamma(edges)
    be_ok, be_res = beta(edges)
    a_ok, a_res, links = gyo(edges)
    cls = "berge" if b_ok else "gamma" if g_ok else "beta" if be_ok else "alpha" if a_ok else "cyclic"
    # the hierarchy must be monotone
    assert (not b_ok or g_ok) and (not g_ok or be_ok) and (not be_ok or a_ok), (b_ok, g_ok, be_ok, a_ok)
    out = {"class": cls, "berge": b_ok, "gamma": g_ok, "beta": be_ok, "alpha": a_ok}
    if not b_ok:
        out["berge_cycle"] = b_cycle
    if not g_ok and be_ok:
        out["gamma_triangle"] = gamma_triangle(edges)
    if not be_ok:
        out["beta_residue"] = be_res
        out["beta_cycle"] = beta_cycle(edges)
    if a_ok:
        out["join_tree"] = links
        assert check_join_tree(edges, links) or len({e for e in edges.values()}) < len(edges)
    else:
        out["gyo_residue"] = a_res
    return out


# ----------------------------------------------------------------------------------------------------------- brute force
def _cycle_free(H: set[frozenset]) -> bool:
    V = sorted(set().union(*H)) if H else []
    for r in range(3, len(V) + 1):
        for S in itertools.combinations(V, r):
            S = set(S)
            M = induced(H, S)
            M = {e for e in M if not any(e < f for f in M)}
            if all(len(e) == 2 for e in M) and len(M) == len(S):
                deg = {v: sum(v in e for e in M) for v in S}
                if all(d == 2 for d in deg.values()):
                    # connected?
                    start = next(iter(S))
                    seen, todo = {start}, [start]
                    while todo:
                        x = todo.pop()
                        for e in M:
                            if x in e:
                                for y in e:
                                    if y not in seen:
                                        seen.add(y)
                                        todo.append(y)
                    if seen == S:
                        return False
    return True


def _conformal(H: set[frozenset]) -> bool:
    V = sorted(set().union(*H)) if H else []
    nb = {v: set() for v in V}
    for e in H:
        for a, b in itertools.combinations(e, 2):
            nb[a].add(b)
            nb[b].add(a)
    for r in range(3, len(V) + 1):
        for S in itertools.combinations(V, r):
            if all(b in nb[a] for a, b in itertools.combinations(S, 2)) and not any(set(S) <= e for e in H):
                return False
    return True


def brute_force_class(edges: Edges) -> str:
    """Definitions as stated by Brault-Baron (alpha1a, beta1b, gamma1a) and Berge's incidence-graph definition."""
    edges = normalise(edges)
    H = as_set_hypergraph(edges)
    alpha_ = _conformal(H) and _cycle_free(H)
    beta_ = all(_cycle_free(set(sub)) for r in range(1, len(H) + 1) for sub in itertools.combinations(H, r))
    gamma_ = beta_ and gamma_triangle(edges) is None
    berge_ = berge(edges)[0]  # the definition itself
    return "berge" if berge_ else "gamma" if gamma_ else "beta" if beta_ else "alpha" if alpha_ else "cyclic"


# ----------------------------------------------------------------------------------------------------------- widths
def reduce_core(edges: Edges) -> Edges:
    """Remove degree-1 vertices, subsumed/duplicate edges and twin vertices until none is left. Preserves ghw and fhw
    (when >= 1); not claimed for hw."""
    live = dict(edges)
    changed = True
    while changed:
        changed = False
        V = set().union(*live.values()) if live else set()
        deg = {v: [n for n, e in live.items() if v in e] for v in V}
        for v in sorted(V):
            if len(deg[v]) == 1:
                n = deg[v][0]
                live[n] = live[n] - {v}
                changed = True
        live = {n: e for n, e in live.items() if e}
        names = sorted(live, key=lambda n: (-len(live[n]), n))
        for i, n in enumerate(names):
            if n in live and any(m in live and m != n and live[n] <= live[m] and (live[n] != live[m] or names.index(m) < i)
                                 for m in names):
                del live[n]
                changed = True
        V = set().union(*live.values()) if live else set()
        star: dict = {}
        for v in sorted(V):
            s = frozenset(n for n, e in live.items() if v in e)
            if s in star:
                for n in s:
                    live[n] = live[n] - {v}
                changed = True
            else:
                star[s] = v
    return live


def rho(B: frozenset, edges: list[frozenset]) -> int:
    """Integral edge cover number of B by the given edges (brute force by increasing size)."""
    if not B:
        return 0
    parts = {e & B for e in edges if e & B}
    parts = [p for p in parts if not any(p < q for q in parts)]
    for k in range(1, len(parts) + 1):
        for comb in itertools.combinations(parts, k):
            if frozenset().union(*comb) == B:
                return k
    raise ValueError("B not coverable")


def rho_star(B: frozenset, edges: list[frozenset]) -> Fraction:
    """Fractional edge cover number of B (LP via scipy HiGHS), returned as a Fraction with small denominator."""
    if not B:
        return Fraction(0)
    from scipy.optimize import linprog
    parts = list({e & B for e in edges if e & B})
    parts = [p for p in parts if not any(p < q for q in parts)]
    vs = sorted(B)
    A = [[-1.0 if v in p else 0.0 for p in parts] for v in vs]
    res = linprog(c=[1.0] * len(parts), A_ub=A, b_ub=[-1.0] * len(vs), bounds=[(0, None)] * len(parts), method="highs")
    assert res.status == 0, res.message
    return Fraction(res.fun).limit_denominator(1000)


def f_width(edges: Edges, cost, limit: int = 20):
    """min over elimination orderings of max cost(bag); subset DP (Bodlaender et al.'s treewidth recurrence with a
    monotone bag cost, as in Moll, Tazari and Thurley 2012). Returns (width, ordering)."""
    V = sorted(set().union(*edges.values())) if edges else []
    n = len(V)
    if n == 0:
        return 0, []
    if n > limit:
        raise ValueError(f"{n} vertices exceeds the exact-DP limit {limit}")
    idx = {v: i for i, v in enumerate(V)}
    adj = [0] * n
    for e in edges.values():
        m = 0
        for v in e:
            m |= 1 << idx[v]
        for v in e:
            adj[idx[v]] |= m & ~(1 << idx[v])
    full = (1 << n) - 1
    bagcost: dict[int, object] = {}

    def cost_of(mask: int):
        if mask not in bagcost:
            bagcost[mask] = cost(frozenset(V[i] for i in range(n) if mask >> i & 1))
        return bagcost[mask]

    def Q(S: int, v: int) -> int:
        """vertices outside S and v reachable from v through S"""
        comp = 1 << v
        frontier = comp
        reach = 0
        while frontier:
            nxt = 0
            m = frontier
            while m:
                low = m & -m
                i = low.bit_length() - 1
                nxt |= adj[i]
                m ^= low
            reach |= nxt
            frontier = nxt & S & ~comp
            comp |= frontier
        return reach & ~S & ~(1 << v)

    best: dict[int, tuple] = {0: (None, None)}
    order = sorted(range(1 << n), key=lambda m: bin(m).count("1"))
    for S in order[1:]:
        cand = None
        m = S
        while m:
            low = m & -m
            v = low.bit_length() - 1
            m ^= low
            prev = S & ~low
            w_prev = best[prev][0]
            bag = Q(prev, v) | (1 << v)
            w = cost_of(bag)
            w = w if w_prev is None or w >= w_prev else w_prev
            if cand is None or w < cand[0]:
                cand = (w, v)
        best[S] = cand
    # recover an ordering
    seq, S = [], full
    while S:
        v = best[S][1]
        seq.append(V[v])
        S &= ~(1 << v)
    return best[full][0], seq[::-1]


def treewidth(edges: Edges, limit: int = 20):
    """Treewidth of the primal graph. Simplicial vertices are eliminated first (safe: for simplicial v of degree d,
    tw(G) = max(d, tw(G - v)), since N[v] is a clique that some bag must hold and a bag N[v] can be hung on any bag
    holding N(v)); the exact DP runs on what is left."""
    V = set().union(*edges.values()) if edges else set()
    nb = {v: set() for v in V}
    for e in edges.values():
        for a, b in itertools.combinations(e, 2):
            nb[a].add(b)
            nb[b].add(a)
    lb, order = 0, []
    changed = True
    while changed:
        changed = False
        for v in sorted(nb):
            N = nb[v]
            if all(b in nb[a] for a, b in itertools.combinations(N, 2)):
                lb = max(lb, len(N))
                for u in N:
                    nb[u].discard(v)
                del nb[v]
                order.append(v)
                changed = True
                break
    rest = {f"{a}~{b}": frozenset((a, b)) for a in nb for b in nb[a] if a < b}
    rest.update({f"{a}~": frozenset((a,)) for a in nb if not nb[a]})
    w, tail = f_width(rest, lambda B: len(B) - 1, limit) if rest else (0, [])
    return max(lb, w), order + tail


def ghw(edges: Edges, limit: int = 20):
    core = reduce_core(edges)
    if not core:
        return 1, []
    es = list(normalise(edges).values())
    w, order = f_width(core, lambda B: rho(B, es), limit)
    return max(1, w), order


def fhw(edges: Edges, limit: int = 20):
    core = reduce_core(edges)
    if not core:
        return Fraction(1), []
    es = list(normalise(edges).values())
    w, order = f_width(core, lambda B: rho_star(B, es), limit)
    return max(Fraction(1), w), order


# ----------------------------------------------------------------------------------------------------------- hw
def hd_search(edges: Edges, k: int, budget: int = 2_000_000):
    """Search a normal-form hypertree decomposition of width <= k (k-decomp / det-k-decomp scheme).
    Returns a tree {"lambda": [...], "chi": [...], "children": [...]} or None. Raises RuntimeError past ``budget``
    separator trials (so a caller can report a bound instead of hanging)."""
    names = sorted(edges)
    E = [edges[n] for n in names]
    V = frozenset().union(*E) if E else frozenset()
    seps = [c for r in range(1, k + 1) for c in itertools.combinations(range(len(E)), r)]
    sep_vars = {c: frozenset().union(*(E[i] for i in c)) for c in seps}
    failed: set = set()
    trials = [0]

    def components(C: frozenset, chi: frozenset) -> list[frozenset]:
        rest = set(C - chi)
        out = []
        while rest:
            start = rest.pop()
            comp, todo = {start}, [start]
            while todo:
                x = todo.pop()
                for e in E:
                    if x in e:
                        for y in e - chi:
                            if y in rest:
                                rest.discard(y)
                                comp.add(y)
                                todo.append(y)
            out.append(frozenset(comp))
        return out

    def neighbourhood(C: frozenset) -> frozenset:
        return frozenset().union(*(e for e in E if e & C)) - C

    def decomp(C: frozenset):
        if C in failed:
            return None
        conn = neighbourhood(C)
        for c in seps:
            trials[0] += 1
            if trials[0] > budget:
                raise RuntimeError("budget exhausted")
            lv = sep_vars[c]
            if not conn <= lv or not (lv & C):
                continue
            chi = lv & (C | conn)
            kids = []
            for D in components(C, chi):
                sub = decomp(D)
                if sub is None:
                    break
                kids.append(sub)
            else:
                return {"lambda": [names[i] for i in c], "chi": sorted(chi), "children": kids}
        failed.add(C)
        return None

    return decomp(V)


def validate_hd(edges: Edges, tree: dict) -> dict:
    """Check the four hypertree decomposition conditions (Gottlob, Leone, Scarcello 2002, Def. 4.1)."""
    nodes = []

    def walk(t, parent):
        i = len(nodes)
        nodes.append((t, parent))
        for ch in t["children"]:
            walk(ch, i)

    walk(tree, None)
    chi = [frozenset(t["chi"]) for t, _ in nodes]
    lam = [frozenset().union(*(edges[n] for n in t["lambda"])) for t, _ in nodes]
    kids = {i: [j for j, (_, p) in enumerate(nodes) if p == i] for i in range(len(nodes))}

    def subtree(i):
        out = set(chi[i])
        for j in kids[i]:
            out |= subtree(j)
        return out

    c1 = all(any(e <= b for b in chi) for e in edges.values())
    c2 = True
    for v in set().union(*edges.values()):
        holders = {i for i in range(len(nodes)) if v in chi[i]}
        # connected in the tree iff exactly one holder has its parent outside the holder set
        roots = [i for i in holders if nodes[i][1] not in holders]
        c2 &= len(roots) == 1
    c3 = all(chi[i] <= lam[i] for i in range(len(nodes)))
    c4 = all(lam[i] & subtree(i) <= chi[i] for i in range(len(nodes)))
    width = max(len(t["lambda"]) for t, _ in nodes)
    return {"covers": c1, "connected": c2, "chi_in_lambda": c3, "special": c4, "width": width, "nodes": len(nodes)}


def hw(edges: Edges, kmax: int = 6, budget: int = 2_000_000):
    """(hw, decomposition) with hw exact when found below kmax; (None, None) if kmax is exceeded."""
    edges = normalise(edges)
    for k in range(1, kmax + 1):
        t = hd_search(edges, k, budget)
        if t is not None:
            return k, t
    return None, None


# ----------------------------------------------------------------------------------------------------------- cli
def report(edges, limit: int = 20, kmax: int = 6) -> dict:
    edges = normalise(edges)
    out = classify(edges)
    core = reduce_core(edges)
    out["vertices"] = len(set().union(*edges.values())) if edges else 0
    out["edges"] = len(edges)
    out["core"] = {"vertices": len(set().union(*core.values())) if core else 0, "edges": len(core)}
    try:
        out["tw_primal"] = treewidth(edges, limit)[0]
    except ValueError as e:
        out["tw_primal"] = f"skipped: {e}"
    try:
        out["ghw"] = ghw(edges, limit)[0]
    except ValueError as e:
        out["ghw"] = f"skipped: {e}"
    try:
        w = fhw(edges, limit)[0]
        out["fhw"] = str(w)
    except (ValueError, ImportError) as e:
        out["fhw"] = f"skipped: {e}"
    try:
        k, t = hw(edges, kmax)
        out["hw"] = k
        if t is not None:
            out["hd_check"] = validate_hd(edges, t)
            out["hd"] = t
    except RuntimeError as e:
        out["hw"] = f"skipped: {e}"
    return out


if __name__ == "__main__":
    data = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else json.load(sys.stdin)
    json.dump(report(data), sys.stdout, indent=1, default=str)
    print()
