"""The HyperBench hypertree-width baseline (DESIGN §6.4, D10), recomputed from the published run data.

Source: Gottlob, Lanzinger, Okulmus, Pichler, "Experimental Data for log-k-decomp", Zenodo 10.5281/zenodo.7180787
(v4, CC BY 4.0): ``parseddata_csv.zip`` (``Run.csv``: Graph, Algorithm, K, Timeout, Correct; ``Type_of.csv``:
Graph, Type) and ``hyperbench.zip`` (the instances). Every algorithm in Run.csv computes hypertree decompositions
(DetK, NewDetK, LogKDecomp, LogKHybrid, htdLEO, htdSMT), so per graph:

    upper bound = the smallest K with Correct = True;
    lower bound = 1 + the largest K with Correct = False and Timeout = False.

hw is exact when they meet. Ported from R01's probe (research/probes/hyperbench_baseline.py); it reads the zips
directly after checking them against ``datasets/hypergraph-benchmarks/hyperbench/MANIFEST.json``.

    python hyperbench_baseline.py [--data DIR] [--out RESULTS]      (writes RESULTS/hyperbench-baseline.json)

The survey row is the non-random CQs: n = 1,113, hw 1 / 2 / 3 = 673 / 432 / 8 (R01 §3.5). They were selected to be
cyclic, so the comparison is by structural parameter and hw (R01 §3.6).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / "datasets" / "hypergraph-benchmarks" / "hyperbench"
GROUPS = ["CQ", "SPARQL", "SQLShare", "CQ Random", "CSP Application", "CSP Random", "CSP Other"]


def _csv(zf: zipfile.ZipFile, name: str):
    member = next(n for n in zf.namelist() if n.endswith("/" + name) or n == name)
    with zf.open(member) as fh:
        yield from csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", newline=""))


def baseline(data: Path) -> dict:
    sys.path.insert(0, str(REPO / "projects" / "p6-schema-width" / "khg-width" / "src"))
    from khg_width.sources import manifest

    hashes = manifest.verify(data, ["raw/parseddata_csv.zip", "raw/hyperbench.zip"])
    ub: dict[str, int] = {}
    lb: dict[str, int] = defaultdict(lambda: 1)
    algos: Counter = Counter()
    with zipfile.ZipFile(data / "raw" / "parseddata_csv.zip") as zf:
        for r in _csv(zf, "Run.csv"):
            g, k = r["Graph"], int(r["K"])
            algos[r["Algorithm"]] += 1
            if r["Timeout"] == "True":
                continue
            if r["Correct"] == "True":
                ub[g] = min(ub.get(g, 10**9), k)
            elif r["Correct"] == "False":
                lb[g] = max(lb[g], k + 1)
        types: dict[str, set] = defaultdict(set)
        for r in _csv(zf, "Type_of.csv"):
            types[r["Graph"]].add(r["Type"])
    graphs = set(types) - {"Graph"}
    conflicts = sorted(g for g in graphs if g in ub and lb[g] > ub[g])
    out: dict = {"source": "Zenodo 10.5281/zenodo.7180787 v4 (CC BY 4.0), parseddata_csv.zip (Run.csv, Type_of.csv)",
                 "inputs": {f"datasets/hypergraph-benchmarks/hyperbench/{k}": v for k, v in hashes.items()},
                 "graphs": len(graphs), "runs_by_algorithm": dict(sorted(algos.items())),
                 "bound_conflicts": len(conflicts), "conflicting_graphs": conflicts, "groups": {}}
    for grp in GROUPS:
        members = [g for g in graphs if grp in types[g]]
        exact: Counter = Counter()
        upper_only: Counter = Counter()
        unknown = 0
        for g in members:
            if g in ub and lb[g] == ub[g]:
                exact[ub[g]] += 1
            elif g in ub:
                upper_only[ub[g]] += 1
            else:
                unknown += 1
        n = len(members)

        def le(c: int) -> int:
            return sum(v for k, v in exact.items() if k <= c) + sum(v for k, v in upper_only.items() if k <= c)

        out["groups"][grp] = {
            "n": n, "exact_hw": {str(k): v for k, v in sorted(exact.items())},
            "upper_bound_only": {str(k): v for k, v in sorted(upper_only.items())}, "no_upper_bound": unknown,
            "share_hw_le_2": round(le(2) / n, 4) if n else None, "share_hw_le_3": round(le(3) / n, 4) if n else None,
            "share_hw_le_5": round(le(5) / n, 4) if n else None, "max_exact_hw": max(exact) if exact else None,
        }
    # structural parameters of the instances, and exactness by size
    sizes = {}
    with zipfile.ZipFile(data / "raw" / "hyperbench.zip") as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            text = zf.read(name).decode("utf-8", "replace")
            text = "\n".join(line.split("%", 1)[0] for line in text.splitlines())
            es = re.findall(r"([^\s(),.][^\s(),]*)\s*\(([^)]*)\)", text)
            vs = {v.strip() for _, body in es for v in body.split(",") if v.strip()}
            rank = max((len([v for v in body.split(",") if v.strip()]) for _, body in es), default=0)
            sizes[Path(name).name] = (len(es), len(vs), rank)
    bins = [(0, 50), (50, 100), (100, 150), (150, 300), (300, 1000), (1000, 10**9)]
    table = {}
    for lo, hi in bins:
        gs = [g for g in graphs if g in sizes and lo <= sizes[g][0] < hi]
        ex = [g for g in gs if g in ub and lb[g] == ub[g]]
        table[f"{lo}-{hi if hi < 10**9 else 'inf'} edges"] = {"graphs": len(gs), "exact_hw": len(ex)}
    out["exactness_by_edges"] = table
    cq = [g for g in graphs if "CQ" in types[g] and g in sizes]
    out["cq_structure"] = {"edges_max": max(sizes[g][0] for g in cq), "rank_max": max(sizes[g][2] for g in cq),
                           "instances_with_sizes": len(cq)}
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--data", default=str(DATA))
    p.add_argument("--out", default=str(HERE.parent / "results"))
    a = p.parse_args(argv)
    res = baseline(Path(a.data))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "hyperbench-baseline.json").write_text(json.dumps(res, indent=1) + "\n")
    cq = res["groups"]["CQ"]
    print(f"non-random CQs: n = {cq['n']}, exact hw {cq['exact_hw']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
