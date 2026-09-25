"""P6 probe: the HyperBench hypertree-width baseline, recomputed from the published run data.

Source: Gottlob, Lanzinger, Okulmus, Pichler, "Experimental Data for log-k-decomp", Zenodo 10.5281/zenodo.7180787
(v4, CC BY 4.0), file parseddata_csv.zip -> Run.csv (one row per decomposition run: Graph, Algorithm, Version, K,
Timeout, Correct) and Type_of.csv (Graph, Type). All algorithms in Run.csv compute hypertree decompositions (DetK,
NewDetK, LogKDecomp, LogKHybrid, htdLEO, htdSMT), so for each graph:
  upper bound = smallest K with Correct = True;   lower bound = 1 + largest K with Correct = False and Timeout = False.
hw is exact when the bounds meet. Nothing is downloaded here; pass the unpacked directory.

Usage:  python hyperbench_baseline.py <dir containing Run.csv and Type_of.csv> [<dir of the .hg instances>]
        (writes out/hyperbench_hw.json; with the instance directory, from Zenodo's hyperbench.zip, it also reports how
        exactness of hw depends on the number of edges)
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    d = sys.argv[1]
    ub: dict[str, int] = {}
    lb: dict[str, int] = defaultdict(lambda: 1)
    algos = Counter()
    for r in csv.DictReader(open(os.path.join(d, "Run.csv"), newline="")):
        g, k = r["Graph"], int(r["K"])
        algos[r["Algorithm"]] += 1
        if r["Timeout"] == "True":
            continue
        if r["Correct"] == "True":
            ub[g] = min(ub.get(g, 10 ** 9), k)
        elif r["Correct"] == "False":
            lb[g] = max(lb[g], k + 1)
    types: dict[str, set[str]] = defaultdict(set)
    for r in csv.DictReader(open(os.path.join(d, "Type_of.csv"), newline="")):
        types[r["Graph"]].add(r["Type"])
    graphs = set(types) - {"Graph"}
    conflicts = [g for g in graphs if g in ub and lb[g] > ub[g]]
    groups = ["CQ", "SPARQL", "SQLShare", "CQ Random", "CSP Application", "CSP Random", "CSP Other"]
    out: dict = {"source": "Zenodo 10.5281/zenodo.7180787 v4, parseddata_csv.zip (Run.csv, Type_of.csv)",
                 "graphs": len(graphs), "runs_by_algorithm": dict(algos), "bound_conflicts": len(conflicts), "groups": {}}
    for grp in groups:
        members = [g for g in graphs if grp in types[g]]
        exact = Counter()
        upper_only = Counter()
        unknown = 0
        for g in members:
            if g in ub and lb[g] == ub[g]:
                exact[ub[g]] += 1
            elif g in ub:
                upper_only[ub[g]] += 1
            else:
                unknown += 1
        n = len(members)
        le = lambda c: sum(v for k, v in exact.items() if k <= c) + sum(v for k, v in upper_only.items() if k <= c)
        out["groups"][grp] = {
            "n": n,
            "exact_hw": dict(sorted(exact.items())),
            "upper_bound_only": dict(sorted(upper_only.items())),
            "no_upper_bound": unknown,
            "share_hw_le_2": round(le(2) / n, 4) if n else None,
            "share_hw_le_3": round(le(3) / n, 4) if n else None,
            "share_hw_le_5": round(le(5) / n, 4) if n else None,
            "max_exact_hw": max(exact) if exact else None,
        }
    if len(sys.argv) > 2:
        sizes = {}
        for f in os.listdir(sys.argv[2]):
            text = "\n".join(line.split("%", 1)[0] for line in open(os.path.join(sys.argv[2], f), errors="replace"))
            es = re.findall(r"([^\s(),.][^\s(),]*)\s*\(([^)]*)\)", text)
            vs = {v.strip() for _, body in es for v in body.split(",") if v.strip()}
            rank = max((len([v for v in body.split(",") if v.strip()]) for _, body in es), default=0)
            sizes[f] = (len(es), len(vs), rank)
        bins = [(0, 50), (50, 100), (100, 150), (150, 300), (300, 1000), (1000, 10 ** 9)]
        table = {}
        for lo, hi in bins:
            gs = [g for g in graphs if g in sizes and lo <= sizes[g][0] < hi]
            ex = [g for g in gs if g in ub and lb[g] == ub[g]]
            table[f"{lo}-{hi if hi < 10 ** 9 else 'inf'} edges"] = {"graphs": len(gs), "exact_hw": len(ex),
                                                                     "max_exact_hw": max((ub[g] for g in ex), default=None)}
        big = sorted(((g, *sizes[g], lb[g], ub.get(g)) for g in graphs if g in sizes and sizes[g][0] >= 300),
                     key=lambda r: -r[1])
        out["exactness_by_edges"] = table
        out["largest_instances"] = [{"graph": g, "edges": e, "vertices": v, "rank": r, "hw_lb": lo, "hw_ub": hi}
                                    for g, e, v, r, lo, hi in big[:15]]
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "out", "hyperbench_hw.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
