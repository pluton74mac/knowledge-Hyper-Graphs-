"""P6 probe: the test hypergraphs, written in the three solver input formats.

Run:  python instances.py            (writes instances/<name>.{hg,pace.hgr,htd.hgr} and instances/index.json)

Formats written (each checked against the reader of the tool that consumes it, see ../01-theory-and-solvers.md):
- ``.hg``        HyperBench format, ``E1 (a, b), E2 (b, c).``  -- BalancedGo, log-k-decomp, NewDetKDecomp, det-k-decomp,
                 HtdLEO (``Hypergraph.from_file(..., fischl_format=True)``)
- ``.pace.hgr``  PACE 2019 hypertree format, ``p htd <n> <m>`` then ``<edge-id> <v> <v> ...`` -- BalancedGo ``-pace``
- ``.htd.hgr``   the ``hgr`` input of htd_main (``p tw <n> <m>`` then one line of vertex ids per edge, no edge id)

Every instance carries its expected values where they are known from the literature or from hand proof; the
``expected`` dict is what the probes compare against. ``None`` means "not asserted here".
"""
from __future__ import annotations

import itertools
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "instances")


def grid(n: int) -> dict[str, list[str]]:
    """The n x n grid graph as a hypergraph of binary edges (vertex rXcY)."""
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
    """Grohe and Marx (TALG 2014), Example 4.2: one vertex per n-subset S of {1..2n}, one edge e_i = {v_S : i in S}.
    rho*(H_n) = 2 while hw(H_n) = n (their claim), so fhw <= 2 < ghw for n >= 3."""
    subsets = list(itertools.combinations(range(1, 2 * n + 1), n))
    name = lambda s: "s" + "_".join(map(str, s))
    return {f"e{i}": [name(s) for s in subsets if i in s] for i in range(1, 2 * n + 1)}


def read_hg(path: str) -> dict[str, list[str]]:
    """Minimal HyperBench-format reader (comments start with %)."""
    text = "\n".join(line.split("%", 1)[0] for line in open(path, encoding="utf-8"))
    edges: dict[str, list[str]] = {}
    for m in re.finditer(r"([^\s(),.][^\s(),]*)\s*\(([^)]*)\)", text):
        edges[m.group(1)] = [v.strip() for v in m.group(2).split(",") if v.strip()]
    return edges


# name -> (edges, expected, note).  Expected class is the most restrictive of berge < gamma < beta < alpha that holds,
# "cyclic" when not even alpha. Widths: hw, ghw, fhw (fhw as a string fraction when not an integer).
INSTANCES: dict[str, tuple[dict[str, list[str]], dict, str]] = {
    "berge_path": ({"E1": ["a", "b"], "E2": ["b", "c"]},
                   {"class": "berge", "hw": 1, "ghw": 1, "fhw": "1"},
                   "a path: Berge-acyclic, so acyclic in every degree"),
    "berge_triangle": ({"E1": ["x", "y"], "E2": ["x", "y", "z"]},
                       {"class": "gamma", "hw": 1, "ghw": 1, "fhw": "1"},
                       "Brault-Baron's 'Berge triangle' {{x,y},{x,y,z}}: gamma-acyclic, not Berge-acyclic"),
    "gamma_triangle": ({"E1": ["x", "y"], "E2": ["y", "z"], "E3": ["x", "y", "z"]},
                       {"class": "beta", "hw": 1, "ghw": 1, "fhw": "1"},
                       "Brault-Baron's 'gamma triangle': beta-acyclic, not gamma-acyclic"),
    "a_triangle_cover": ({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"], "E4": ["a", "b", "c"]},
                         {"class": "alpha", "hw": 1, "ghw": 1, "fhw": "1"},
                         "gate case (a); Brault-Baron's 'beta triangle': alpha-acyclic, not beta-acyclic; hw 1"),
    "b_triangle": ({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"]},
                   {"class": "cyclic", "hw": 2, "ghw": 2, "fhw": "3/2"},
                   "gate case (b): the triangle, alpha-cyclic; hw 2, fhw 3/2"),
    "c_grid4": (grid(4), {"class": "cyclic", "hw": None, "ghw": None, "fhw": None}, "gate case (c): 4x4 grid graph"),
    "c_grid5": (grid(5), {"class": "cyclic", "hw": None, "ghw": None, "fhw": None}, "gate case (c): 5x5 grid graph"),
    "k5": (clique(5), {"class": "cyclic", "hw": 3, "ghw": 3, "fhw": "5/2"},
           "K5 as binary edges: rho*(K5) = 5/2 bounds fhw from above; ghw = hw = 3 is asserted by the probes, not by a source"),
    "adler": ({"E1": ["V1", "V2", "V9"], "E2": ["V2", "V3", "V10"], "E3": ["V3", "V4"], "E4": ["V4", "V5", "V9"],
               "E5": ["V5", "V6", "V10"], "E6": ["V6", "V7", "V9"], "E7": ["V7", "V8", "V10"], "E8": ["V8", "V1"]},
              {"class": "cyclic", "hw": 3, "ghw": 2, "fhw": None},
              "Adler's example (hg_adlerexample.txt in NewDetKDecomp; HyperBench id 1 lists hw = 3, ghw <= 2)"),
    "grohe_marx_3": (grohe_marx(3), {"class": "cyclic", "hw": 3, "ghw": None, "fhw": "2"},
                     "Grohe-Marx Example 4.2 with n = 3: rho* = 2 (so fhw <= 2), hw = 3 claimed by the source"),
}


SAMER = os.environ.get("P6_GRID2D")  # path to grid2d_10.txt from github.com/daajoe/detkdecomp (benchmarks/Grid2D);
# not copied into the repository (that repository carries no licence file); its derived files go to P6_SCRATCH.
SCRATCH = os.environ.get("P6_SCRATCH")


def load_all() -> dict[str, tuple[dict[str, list[str]], dict, str]]:
    out = dict(INSTANCES)
    samer = SAMER
    if samer and os.path.exists(samer):
        out["c_grid2d_10"] = (read_hg(samer), {"class": "cyclic", "hw": None, "ghw": None, "fhw": None},
                              "gate case (c), harder: Samer's Grid2D grid2d_10 (det-k-decomp benchmarks, also in HyperBench)")
    return out


def to_hg(edges: dict[str, list[str]]) -> str:
    names = list(edges)
    return ",\n".join(f"{e} ({', '.join(edges[e])})" for e in names) + ".\n"


def numbering(edges: dict[str, list[str]]) -> tuple[list[str], dict[str, int]]:
    verts = sorted({v for vs in edges.values() for v in vs})
    return verts, {v: i + 1 for i, v in enumerate(verts)}


def to_pace(edges: dict[str, list[str]]) -> str:
    verts, num = numbering(edges)
    lines = [f"p htd {len(verts)} {len(edges)}"]
    for i, e in enumerate(edges, 1):
        lines.append(f"{i} " + " ".join(str(num[v]) for v in edges[e]))
    return "\n".join(lines) + "\n"


def to_htd_hgr(edges: dict[str, list[str]]) -> str:
    verts, num = numbering(edges)
    lines = [f"p tw {len(verts)} {len(edges)}"]
    for e in edges:
        lines.append(" ".join(str(num[v]) for v in edges[e]))
    return "\n".join(lines) + "\n"


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    index = {}
    for name, (edges, expected, note) in load_all().items():
        where = OUT
        if name == "c_grid2d_10":
            if not SCRATCH:
                continue
            where = SCRATCH
            os.makedirs(where, exist_ok=True)
        open(os.path.join(where, f"{name}.hg"), "w").write(to_hg(edges))
        open(os.path.join(where, f"{name}.pace.hgr"), "w").write(to_pace(edges))
        open(os.path.join(where, f"{name}.htd.hgr"), "w").write(to_htd_hgr(edges))
        index[name] = {"vertices": len({v for vs in edges.values() for v in vs}), "edges": len(edges),
                       "expected": expected, "note": note}
    json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=1)
    json.dump(index, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
