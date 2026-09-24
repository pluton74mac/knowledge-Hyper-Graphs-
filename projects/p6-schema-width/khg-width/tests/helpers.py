"""Shared helpers of the khg-width tests (paths, the expected fixture table, the brute-force oracle)."""
from __future__ import annotations

import csv
import itertools
import json
import os
import random
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
RECORDED = HERE / "recorded"
MINI = HERE / "mini"
PACKAGE = HERE.parent
P6 = PACKAGE.parent
#: the survey results the ``survey`` tests read (KHG_WIDTH_SURVEY_RESULTS points them at another run)
RESULTS = Path(os.environ.get("KHG_WIDTH_SURVEY_RESULTS") or P6 / "results")
REPO = P6.parent.parent
SLOTS = {"cq": ("core", "qualifier"), "cqt": ("core", "qualifier", "time")}
SEED = 20260924


def fixture_path(source: str) -> str:
    """``p2:fixture/cyclic.relation-schema.json`` (packaged with khg-contracts) or a file name in fixtures/."""
    if source.startswith("p2:"):
        from khg_contracts import data

        return str(data.path(source[3:]))
    return str(FIXTURES / source)


def value(measure: str, text: str):
    return Fraction(text) if measure == "fhw" else int(text)


def fixture_rows() -> list[dict]:
    with open(FIXTURES / "expected.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["path"] = fixture_path(r["source"])
        r["slot_tuple"] = SLOTS[r["slots"]]
    return rows


def residue_value(text: str) -> list[list[str]]:
    """``a,b|b,c`` -> [["a", "b"], ["b", "c"]]."""
    return [e.split(",") for e in text.split("|")] if text else []


def solvers_found() -> dict:
    from khg_width.solvers import find_solvers

    return find_solvers()



# ------------------------------------------------------------------------------------------------ random hypergraphs
def random_hypergraph(rng: random.Random, n: int, m: int) -> dict[str, list[str]]:
    """R01's generator (probe_theory.py): m edges over n vertices, sizes drawn from 1, 2, 2, 2, 3, 3, 4."""
    verts = [f"v{i}" for i in range(n)]
    edges = {}
    for j in range(m):
        k = rng.choice([1, 2, 2, 2, 3, 3, 4])
        edges[f"e{j}"] = rng.sample(verts, min(k, n))
    return edges


def random_set(count: int = 400, seed: int = SEED) -> list[dict[str, list[str]]]:
    """The 400 seeded random hypergraphs of R01 §1.4 (3-7 vertices, 2-7 edges)."""
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        n = rng.randint(3, 7)
        m = rng.randint(2, 7)
        out.append(random_hypergraph(rng, n, m))
    return out


# ------------------------------------------------------------------------------------------------ brute-force oracle
def _induced(h: set, keep: set) -> set:
    return {e & keep for e in h if e & keep}


def _cycle_free(h: set) -> bool:
    verts = sorted(set().union(*h)) if h else []
    for r in range(3, len(verts) + 1):
        for s in itertools.combinations(verts, r):
            s = set(s)
            m = _induced(h, s)
            m = {e for e in m if not any(e < f for f in m)}
            if all(len(e) == 2 for e in m) and len(m) == len(s):
                deg = {v: sum(v in e for e in m) for v in s}
                if all(d == 2 for d in deg.values()):
                    start = next(iter(s))
                    seen, todo = {start}, [start]
                    while todo:
                        x = todo.pop()
                        for e in m:
                            if x in e:
                                for y in e:
                                    if y not in seen:
                                        seen.add(y)
                                        todo.append(y)
                    if seen == s:
                        return False
    return True


def _conformal(h: set) -> bool:
    verts = sorted(set().union(*h)) if h else []
    nb = {v: set() for v in verts}
    for e in h:
        for a, b in itertools.combinations(e, 2):
            nb[a].add(b)
            nb[b].add(a)
    for r in range(3, len(verts) + 1):
        for s in itertools.combinations(verts, r):
            if all(b in nb[a] for a, b in itertools.combinations(s, 2)) and not any(set(s) <= e for e in h):
                return False
    return True


def _gamma_triangle(h: set) -> bool:
    verts = sorted(set().union(*h)) if h else []
    for x, y, z in itertools.permutations(verts, 3):
        tr = {e & {x, y, z} for e in h}
        if {x, y} in tr and {y, z} in tr and {x, y, z} in tr:
            return True
    return False


def _berge_acyclic(edges: dict) -> bool:
    """The incidence graph of the multi-hypergraph is a forest: #incidences = #nodes - #components."""
    nodes = [("E", n) for n in edges] + [("V", v) for v in set().union(*map(set, edges.values()))]
    parent = {x: x for x in nodes}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for n, e in edges.items():
        for v in set(e):
            a, b = find(("E", n)), find(("V", v))
            if a == b:
                return False
            parent[a] = b
    return True


def brute_force_class(edges: dict) -> str:
    """The definitions as stated by Brault-Baron (alpha1a, beta1b, gamma1a) and Berge's incidence-graph one
    (R01's probe_theory oracle)."""
    edges = {k: frozenset(v) for k, v in edges.items() if v}
    h = set(edges.values())
    alpha = _conformal(h) and _cycle_free(h)
    beta = all(_cycle_free(set(sub)) for r in range(1, len(h) + 1) for sub in itertools.combinations(h, r))
    gamma = beta and not _gamma_triangle(h)
    berge = _berge_acyclic(edges)
    return "berge" if berge else "gamma" if gamma else "beta" if beta else "alpha" if alpha else "cyclic"


# ------------------------------------------------------------------------------------------------ named instances
def grid(n: int) -> dict[str, list[str]]:
    """The n x n grid graph as binary relations (R01's instances.py)."""
    edges: dict[str, list[str]] = {}
    for r in range(n):
        for c in range(n):
            if c + 1 < n:
                edges[f"h{r}_{c}"] = [f"r{r}c{c}", f"r{r}c{c + 1}"]
            if r + 1 < n:
                edges[f"v{r}_{c}"] = [f"r{r}c{c}", f"r{r + 1}c{c}"]
    return edges


def clique(n: int) -> dict[str, list[str]]:
    return {f"e{i}_{j}": [f"x{i}", f"x{j}"] for i, j in itertools.combinations(range(1, n + 1), 2)}


def grohe_marx(n: int) -> dict[str, list[str]]:
    """Grohe and Marx (TALG 2014), Example 4.2 (R01's instances.py)."""
    subsets = list(itertools.combinations(range(1, 2 * n + 1), n))

    def name(s: tuple) -> str:
        return "s" + "_".join(map(str, s))

    return {f"e{i}": [name(s) for s in subsets if i in s] for i in range(1, 2 * n + 1)}


ADLER = {"E1": ["V1", "V2", "V9"], "E2": ["V2", "V3", "V10"], "E3": ["V3", "V4"], "E4": ["V4", "V5", "V9"],
         "E5": ["V5", "V6", "V10"], "E6": ["V6", "V7", "V9"], "E7": ["V7", "V8", "V10"], "E8": ["V8", "V1"]}


def named_set() -> dict[str, dict[str, list[str]]]:
    """R01's named instances with hw 2 to 3 (§2.2 and §4.4)."""
    return {"b_triangle": clique(3), "k5": clique(5), "adler": dict(ADLER), "c_grid4": grid(4), "c_grid5": grid(5),
            "grohe_marx_3": grohe_marx(3)}


def dense_set(count: int = 150, seed: int = SEED + 1) -> list[dict[str, list[str]]]:
    """Denser random hypergraphs (6-9 roles, 8-14 relations of 2-4 roles), where hw 3 occurs."""
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        n = rng.randint(6, 9)
        m = rng.randint(8, 14)
        verts = [f"v{i}" for i in range(n)]
        out.append({f"e{j}": rng.sample(verts, rng.choice([2, 2, 3, 3, 4])) for j in range(m)})
    return out


# ------------------------------------------------------------------------------------------------ independent oracles (F2)
def _solve(rows: list, rhs: list) -> list | None:
    """Solve a square system over Fractions; None when singular."""
    n = len(rows)
    a = [list(r) + [b] for r, b in zip(rows, rhs)]
    for c in range(n):
        p = next((r for r in range(c, n) if a[r][c] != 0), None)
        if p is None:
            return None
        a[c], a[p] = a[p], a[c]
        pv = a[c][c]
        a[c] = [x / pv for x in a[c]]
        for r in range(n):
            if r != c and a[r][c] != 0:
                f = a[r][c]
                a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [a[r][n] for r in range(n)]


def rho_star_oracle(bag: frozenset, edges: list) -> Fraction:
    """rho*(bag): the dual LP (max sum y, sum over each trace <= 1, y >= 0) solved exactly by enumerating its
    vertices: every choice of |bag| tight constraints, solved over Fractions, kept when feasible."""
    verts = sorted(bag)
    n = len(verts)
    if n == 0:
        return Fraction(0)
    trs = {frozenset(e & bag) for e in edges if e & bag}
    trs = [t for t in trs if not any(t < u for u in trs)]
    if any(t == frozenset(bag) for t in trs):
        return Fraction(1)
    cons = [[Fraction(1) if v in t else Fraction(0) for v in verts] for t in trs]  # sum_{v in t} y_v <= 1
    zero = [[Fraction(1) if j == i else Fraction(0) for j in range(n)] for i in range(n)]  # y_i >= 0 (tight: = 0)
    best = Fraction(0)
    allc = [(r, Fraction(1)) for r in cons] + [(r, Fraction(0)) for r in zero]
    for choice in itertools.combinations(range(len(allc)), n):
        y = _solve([allc[i][0] for i in choice], [allc[i][1] for i in choice])
        if y is None or any(v < 0 for v in y):
            continue
        if any(sum((y[j] for j in range(n) if row[j]), Fraction(0)) > 1 for row in cons):
            continue
        best = max(best, sum(y, Fraction(0)))
    return best


def rho_oracle(bag: frozenset, edges: list) -> int:
    """rho(bag) by trying every set of 1, 2, ... traces."""
    if not bag:
        return 0
    es = list({e & bag for e in edges if e & bag})
    for k in range(1, len(es) + 1):
        for comb in itertools.combinations(es, k):
            if frozenset().union(*comb) >= bag:
                return k
    raise ValueError


def widths_by_orderings(edges: list) -> tuple[int, int, Fraction]:
    """(tw, ghw, fhw) of a small set hypergraph by brute force over ALL elimination orderings of its roles: each
    ordering gives the bags {v} + v's later neighbours in the filled primal graph; the width is the minimum over
    orderings of the maximum bag cost |B| - 1, rho(B), rho*(B) (Moll, Tazari and Thurley 2012). Independent of
    khg_width: for the random set (at most 7 roles)."""
    verts = sorted({v for e in edges for v in e})
    n = len(verts)
    idx = {v: i for i, v in enumerate(verts)}
    adj0 = [0] * n
    for e in edges:
        m = sum(1 << idx[v] for v in e)
        for v in e:
            adj0[idx[v]] |= m & ~(1 << idx[v])
    best = [None, None, None]
    cost_cache = {}

    def costs(mask):
        c = cost_cache.get(mask)
        if c is None:
            b = frozenset(verts[i] for i in range(n) if mask >> i & 1)
            c = (len(b) - 1, rho_oracle(b, edges), rho_star_oracle(b, edges))
            cost_cache[mask] = c
        return c

    for order in itertools.permutations(range(n)):
        adj = list(adj0)
        alive = (1 << n) - 1
        worst = [0, 0, Fraction(0)]
        for v in order:
            nb = adj[v] & alive
            bag = nb | (1 << v)
            c = costs(bag)
            worst = [max(a, b) for a, b in zip(worst, c)]
            x = nb
            while x:
                lb = x & -x
                u = lb.bit_length() - 1
                adj[u] |= nb & ~lb
                x ^= lb
            alive &= ~(1 << v)
        best = [w if b is None else min(b, w) for b, w in zip(best, worst)]
    return best[0], max(1, best[1]), max(Fraction(1), best[2])


def recorded_hw() -> dict:
    """``fixtures/random-hw.json``: hw recorded with BalancedGo -exact -det and log-k-decomp -exact
    (tests/record_random_hw.py) for random_set(), dense_set() and named_set()."""
    return json.loads((FIXTURES / "random-hw.json").read_text())


# ------------------------------------------------------------------------------------------------ lower-bound witnesses (F9)
def primal_of(edges) -> dict[str, set]:
    nb: dict[str, set] = {}
    for e in edges:
        for v in e:
            nb.setdefault(v, set()).update(e)
    for v, s in nb.items():
        s.discard(v)
    return nb


def min_degree_minor_bound(adj: dict[str, set]) -> int:
    """Minor-min-width, written again here (contract a minimum-degree vertex into its minimum-degree neighbour;
    the bound is the largest minimum degree met). tw(G) >= min degree of any minor of G."""
    nb = {v: set(s) for v, s in adj.items()}
    best = 0
    while nb:
        v = min(nb, key=lambda x: (len(nb[x]), x))
        best = max(best, len(nb[v]))
        ns = nb.pop(v)
        if not ns:
            continue
        u = min(ns, key=lambda w: (len(nb[w]), w))
        for w in ns:
            nb[w].discard(v)
        for w in ns:
            if w != u:
                nb[u].add(w)
                nb[w].add(u)
    return best


def check_lower_witness(h, measure: str, w: dict, acyclicity: dict) -> str:
    """Check a report's ``widths.<measure>.lower_witness`` against H cheaply; returns the method checked.
    A clique must be a clique of H's primal graph; a fractional dual must be feasible on every relation of H."""
    from khg_width.covers import rho

    lw = w["lower_witness"]
    assert lw is not None and lw["method"] == w["lower_method"], (measure, lw, w["lower_method"])
    lower = Fraction(str(w["lower"])) if measure == "fhw" else int(w["lower"])
    edges = [e for _, e in h.edges]
    adj = primal_of(edges)
    method = lw["method"]

    def is_clique(roles) -> bool:
        return all(b in adj.get(a, ()) for a, b in itertools.combinations(roles, 2))

    if method == "join-tree":
        assert acyclicity["class"] != "cyclic" and lower == 1 and h.edges
    elif method == "empty":
        assert not h.edges and lower == 0
    elif method == "cyclic":
        assert acyclicity["class"] == "cyclic"
        assert (lower, w["lower_exclusive"]) == ((Fraction(1), True) if measure == "fhw" else (2, False))
    elif method == "clique" and measure == "ghw":
        k = frozenset(lw["roles"])
        assert is_clique(k) and lw["rho"] == lower
        # a clique lies in one bag of every GHD, so ghw >= rho(K); the checker may have used the cheaper
        # ceil(|K| / largest trace) <= rho(K) on cliques with more than 60 traces
        assert rho(k, list(h.edges))[0] >= lower
    elif method == "clique" and measure == "fhw":
        k = frozenset(lw["roles"])
        y = {v: Fraction(x) for v, x in lw["dual"].items()}
        assert is_clique(k) and set(y) <= k and all(x >= 0 for x in y.values())
        assert all(sum((y.get(v, Fraction(0)) for v in e & k), Fraction(0)) <= 1 for e in edges)
        assert sum(y.values(), Fraction(0)) == Fraction(lw["rho_star"]) == lower
    elif method in ("rank", "simplicial"):
        k = lw["clique"]
        assert measure == "tw" and is_clique(k) and len(k) - 1 == lower
    elif method == "minor-min-width":
        blk = set(lw["block"])
        sub = {v: adj[v] & blk for v in blk}
        assert not blk & set(lw["universal"]) and len(lw["universal"]) == lw["offset"]
        assert all(u in adj and set(adj[u]) >= set(adj) - {u} for u in lw["universal"])
        assert min_degree_minor_bound(sub) == lw["value"] and lower == lw["value"] + lw["offset"]
    elif method in ("induced-dp", "induced-hd-search"):
        assert set(lw["roles"]) <= set(adj) and len(lw["roles"]) <= 18
    elif method.startswith("refutation:") or method == "hd-search":
        assert lower == lw["refuted_k"] + 1
    elif method == "inequality":
        assert lw["from"] in ("hw", "ghw", "fhw") and lw["rule"]
    elif method == "dp":
        pass  # an exact procedure: the value is the DP's; its certificate is the validated decomposition
    else:
        raise AssertionError(f"unknown lower-bound method {method}")
    return method
