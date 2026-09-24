"""P6 probe: check p6check.py against brute-force definitions and against known widths.

Run:  python probe_theory.py [n_random]   (writes out/probe_theory.json; needs scipy for fhw)

1. Class-boundary instances: the classifier returns the expected Fagin class and a witness.
2. Random small hypergraphs (seeded): the polynomial tests agree with the brute-force definitions of
   Berge / gamma / beta / alpha acyclicity, and the hierarchy is monotone.
3. Width sanity on the same random hypergraphs: fhw <= ghw <= hw <= 3 ghw + 1, ghw <= tw + 1, hw = 1 iff alpha,
   and every hypertree decomposition found passes the four-condition validator.
4. Widths of the named instances, compared with the values in instances.INSTANCES.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from collections import Counter
from fractions import Fraction

import instances
import p6check as pc

HERE = os.path.dirname(os.path.abspath(__file__))


def random_hypergraph(rng: random.Random, n: int, m: int) -> dict[str, list[str]]:
    V = [f"v{i}" for i in range(n)]
    edges = {}
    for j in range(m):
        k = rng.choice([1, 2, 2, 2, 3, 3, 4])
        edges[f"e{j}"] = rng.sample(V, min(k, n))
    return edges


def main() -> None:
    n_random = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    out: dict = {"boundary": {}, "random": {}, "widths": {}}

    # 1. boundary instances
    for name in ["berge_path", "berge_triangle", "gamma_triangle", "a_triangle_cover", "b_triangle"]:
        edges, exp, _ = instances.INSTANCES[name]
        c = pc.classify(edges)
        out["boundary"][name] = {"class": c["class"], "expected": exp["class"], "brute_force": pc.brute_force_class(pc.normalise(edges)),
                                 **{k: c[k] for k in ("berge_cycle", "gamma_triangle", "beta_cycle", "gyo_residue", "join_tree") if k in c}}
        assert c["class"] == exp["class"] == out["boundary"][name]["brute_force"], (name, c)

    # 2 and 3. random cross-check
    rng = random.Random(20260924)
    classes = Counter()
    mismatches = []
    width_viol = []
    widths_seen = Counter()
    t0 = time.time()
    for i in range(n_random):
        n = rng.randint(3, 7)
        m = rng.randint(2, 7)
        hg = pc.normalise(random_hypergraph(rng, n, m))
        fast = pc.classify(hg)["class"]
        slow = pc.brute_force_class(hg)
        classes[fast] += 1
        if fast != slow:
            mismatches.append({"hg": {k: sorted(v) for k, v in hg.items()}, "fast": fast, "slow": slow})
        g, _ = pc.ghw(hg)
        f, _ = pc.fhw(hg)
        h, t = pc.hw(hg, kmax=6)
        tw, _ = pc.treewidth(hg)
        ok = t is not None and all(v for k, v in pc.validate_hd(hg, t).items() if k not in ("width", "nodes"))
        ok &= pc.validate_hd(hg, t)["width"] == h
        ok &= f <= g <= h <= 3 * g + 1 and g <= tw + 1
        ok &= (h == 1) == (fast != "cyclic") and (g == 1) == (h == 1) and (f == 1) == (g == 1)
        widths_seen[(str(f), g, h)] += 1
        if not ok:
            width_viol.append({"hg": {k: sorted(v) for k, v in hg.items()}, "fhw": str(f), "ghw": g, "hw": h, "tw": tw})
    out["random"] = {"n": n_random, "seed": 20260924, "classes": dict(classes), "class_mismatches": mismatches,
                     "width_violations": width_viol,
                     "width_triples_fhw_ghw_hw": {f"{a}|{b}|{c}": v for (a, b, c), v in sorted(widths_seen.items())},
                     "hw_gt_ghw": sum(v for (a, b, c), v in widths_seen.items() if c > b),
                     "fhw_lt_ghw": sum(v for (a, b, c), v in widths_seen.items() if Fraction(a) < b),
                     "seconds": round(time.time() - t0, 1)}

    # 4. named instances
    for name, (edges, exp, note) in instances.load_all().items():
        e = pc.normalise(edges)
        row: dict = {"vertices": len(set().union(*e.values())), "edges": len(e), "expected": exp}
        t1 = time.time()
        try:
            row["tw_primal"] = pc.treewidth(e, limit=18)[0]
        except ValueError as err:
            row["tw_primal"] = f"skipped: {err}"
        try:
            row["ghw"] = pc.ghw(e, limit=18)[0]
        except ValueError as err:
            row["ghw"] = f"skipped: {err}"
        try:
            row["fhw"] = str(pc.fhw(e, limit=18)[0])
        except ValueError as err:
            row["fhw"] = f"skipped: {err}"
        try:
            h, t = pc.hw(e, kmax=5, budget=3_000_000)
            row["hw"] = h
            if t is not None:
                row["hd_valid"] = pc.validate_hd(e, t)
        except RuntimeError as err:
            row["hw"] = f"skipped: {err}"
        row["seconds"] = round(time.time() - t1, 2)
        out["widths"][name] = row
        print(name, {k: v for k, v in row.items() if k != "expected"}, flush=True)

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "out", "probe_theory.json"), "w"), indent=1, default=str)
    print(json.dumps(out["random"], indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
