"""P6 probe: turn out/solvers/summary.tsv (and out/probe_theory.json) into the markdown table of the report, 4.4.

Run:  python solver_table.py   (prints markdown; also writes out/solver_table.md)
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["berge_path", "berge_triangle", "gamma_triangle", "a_triangle_cover", "b_triangle", "k5", "adler", "c_grid4",
         "c_grid5", "grohe_marx_3", "c_grid2d_10"]


def per_k(rows, prefix):
    """'k:no/yes' sequence for measures named <prefix><k>, ordered by k, plus the first k that says yes."""
    ks = sorted((int(m[len(prefix):]), v, float(s)) for m, (v, s) in rows.items() if m.startswith(prefix))
    if not ks:
        return "–", None
    parts, first = [], None
    for k, v, s in ks:
        tag = {"yes": "yes", "no": "no", "timeout": "t/o"}.get(v, "yes" if v not in ("no", "timeout", "?") else v)
        parts.append(f"{k}:{tag}" + (f" ({s:.0f} s)" if s >= 1 else ""))
        if tag == "yes" and first is None:
            first = k
    return " ".join(parts), first


def cell(rows, m):
    if m not in rows:
        return "–"
    v, s = rows[m]
    s = float(s)
    return f"{v}" + (f" ({s:.0f} s)" if s >= 1 else "")


def main() -> None:
    data: dict[str, dict[str, dict[str, tuple[str, str]]]] = defaultdict(lambda: defaultdict(dict))
    for r in csv.DictReader(open(os.path.join(HERE, "out", "solvers", "summary.tsv")), delimiter="\t"):
        v = "timeout" if "exit 124" in r["status"] else r["value"]
        data[r["instance"]][r["tool"]][r["measure"]] = (v, r["seconds"])
    proto = json.load(open(os.path.join(HERE, "out", "probe_theory.json")))["widths"]
    head = ("| Instance | V/E | p6check tw / ghw / fhw / hw | BalancedGo `-exact -det` (hw) | log-k-decomp `-exact` (hw) "
            "| NewDetKDecomp `detkdecomp` k (hw) | det-k-decomp 1.0, k = 3 | HtdLEO hw / htdsmt hw | BalancedGo `-global` k (ghw) "
            "| NewDetKDecomp `balsepkdecomp` k (ghw) | HtdLEO `-g` (ghw) | fraSMT (fhw) | htd tw / GHD ub |")
    lines = [head, "|" + "---|" * 13]
    for n in ORDER:
        if n not in data:
            continue
        d = data[n]
        p = proto.get(n, {})
        pv = " / ".join(str(p.get(k, "–")).replace("skipped: ", "skip: ")[:12] for k in ("tw_primal", "ghw", "fhw", "hw"))
        bal = cell(d["balancedgo"], "hw_detk_exact")
        pace = d["balancedgo"].get("hw_detk_exact_pace", ("", ""))[0]
        if pace and pace != d["balancedgo"].get("hw_detk_exact", ("", ""))[0]:
            bal += f" (PACE input: {pace})"
        ndk_hw, _ = per_k(d["ndk"], "hw_detk_k")
        ndk_ghw, _ = per_k(d["ndk"], "ghw_balsep_k")
        glob, _ = per_k(d["balancedgo"], "ghw_global_k")
        leo = cell(d["htdleo"], "hw") + " / " + cell(d["htdsmt"], "hw")
        fra = cell(d["frasmt"], "fhw")
        if f"{n}_neutral" in data:  # fraSMT reran on renamed ids after it silently parsed 0 edges (see report 4.3)
            fra = f"{fra} (0 edges parsed); {cell(data[n + '_neutral']['frasmt'], 'fhw')} with neutral ids"
        row = [f"`{n}`", f"{p.get('vertices', '?')}/{p.get('edges', '?')}", pv, bal, cell(d["logk"], "hw_exact"), ndk_hw,
               cell(d["detk1"], "hw_k3"), leo, glob, ndk_ghw, cell(d["htdleo"], "ghw"), fra,
               cell(d["htd"], "tw") + " / " + cell(d["htd"], "ghw_ub")]
        lines.append("| " + " | ".join(row) + " |")
    md = "\n".join(lines)
    open(os.path.join(HERE, "out", "solver_table.md"), "w").write(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
