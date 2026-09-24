"""Shared helpers of the khg-width tests (paths, the expected fixture table, the brute-force oracle)."""
from __future__ import annotations

import csv
import itertools
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
