"""Probe: parse Wikidata "allowed qualifiers" constraints into a schema hypergraph.

Question (P2 research report 04, section on the schema language, and decision D-04 of report 01):
does the way Wikidata's main-snak roles are named change the acyclicity class that P6 would
measure? Each property P becomes one relation schema (hyperedge). Its attributes (vertices) are
the subject role, the main-value role and the properties listed as allowed qualifiers of P
(constraint Q21510851, parameter P2306). Five naming conventions are compared:

  A generic   : {subject, value} + Q(P)
  B typed     : {subject, value@P} + Q(P)
  C local     : {subject@P, value@P} + Q(P)
  D rel-local : {P:subject, P:value} + {P:q for q in Q(P)}   (roles scoped to the relation,
                                                              as TypeDB scopes role types)
  E role=prop : {subject, P} + Q(P)   (the main value's role is the property itself, so a
                                       property used as a main property and as a qualifier
                                       is one attribute)

For each convention it reports alpha-acyclicity (GYO reduction) and beta-acyclicity
(nest-point elimination, Duris 2012 / Brouwer-Kolen characterisation), vertex count and the
most shared attributes. Output: JSON and Markdown next to this file.

Data: Special:EntityData/<P>.json, fetched once with a 1.5 s delay and cached under
/tmp (not committed). Only the extracted allowed-qualifier lists are written to the output.

Run: python wikidata_schema_hypergraph_probe.py [--cache DIR]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

PROPS = [
    "P39", "P26", "P1082", "P166", "P69", "P108", "P54", "P463", "P1411", "P6",
    "P35", "P1435", "P2046", "P1128", "P2139", "P361", "P793", "P106", "P27", "P1448",
]
ALLOWED_QUALIFIERS = "Q21510851"
UA = "khg-kb-research/0.1 (knowledge-hypergraph literature survey; low volume)"
HERE = Path(__file__).resolve().parent


def fetch(pid: str, cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{pid}.json"
    if not path.exists() or path.stat().st_size < 200:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{pid}.json"
        subprocess.run(["curl", "-sS", "-A", UA, "-o", str(path), url], check=True)
        time.sleep(1.5)
    data = json.loads(path.read_text())
    return list(data["entities"].values())[0]


def allowed_qualifiers(entity: dict) -> tuple[list[str] | None, bool]:
    """Union of P2306 values over all allowed-qualifiers constraint statements.

    Returns (list or None if no such constraint, novalue_flag)."""
    found = False
    novalue = False
    quals: set[str] = set()
    for st in entity.get("claims", {}).get("P2302", []):
        dv = st["mainsnak"].get("datavalue", {}).get("value", {})
        if not isinstance(dv, dict) or dv.get("id") != ALLOWED_QUALIFIERS:
            continue
        found = True
        for q in st.get("qualifiers", {}).get("P2306", []):
            if q["snaktype"] == "novalue":
                novalue = True
            elif q["snaktype"] == "value":
                quals.add(q["datavalue"]["value"]["id"])
    return (sorted(quals) if found else None), novalue


def gyo_alpha_acyclic(edges: list[frozenset]) -> bool:
    """Graham / Yu-Ozsoyoglu reduction. True iff the hypergraph is alpha-acyclic."""
    es = [set(e) for e in edges if e]
    changed = True
    while changed:
        changed = False
        count = Counter(v for e in es for v in e)
        for e in es:  # rule 1: drop vertices that occur in exactly one edge
            lonely = {v for v in e if count[v] == 1}
            if lonely:
                e -= lonely
                changed = True
        es = [e for e in es if e]
        # rule 2: drop an edge contained in another edge (keep one copy of duplicates)
        keep: list[set] = []
        for i, e in enumerate(es):
            dominated = any(
                (e < f) or (e == f and j < i) for j, f in enumerate(es) if j != i
            )
            if dominated:
                changed = True
            else:
                keep.append(e)
        es = keep
    return len(es) <= 1


def beta_acyclic(edges: list[frozenset]) -> bool:
    """Nest-point elimination: a hypergraph is beta-acyclic iff repeatedly deleting a vertex
    whose incident edges form a chain under inclusion empties the vertex set."""
    es = [set(e) for e in edges if e]
    verts = set().union(*es) if es else set()
    while verts:
        nest = None
        for v in sorted(verts):
            inc = sorted((e for e in es if v in e), key=len)
            if all(inc[i] <= inc[i + 1] for i in range(len(inc) - 1)):
                nest = v
                break
        if nest is None:
            return False
        for e in es:
            e.discard(nest)
        es = [e for e in es if e]
        verts.discard(nest)
    return True


def gyo_residue(edges: list[frozenset]) -> tuple[int, int]:
    """Number of hyperedges and vertices left after GYO reduction (0 or 1 edge = acyclic)."""
    es = [set(e) for e in edges if e]
    changed = True
    while changed:
        changed = False
        count = Counter(v for e in es for v in e)
        for e in es:
            lonely = {v for v in e if count[v] == 1}
            if lonely:
                e -= lonely
                changed = True
        es = [e for e in es if e]
        keep: list[set] = []
        for i, e in enumerate(es):
            if any((e < f) or (e == f and j < i) for j, f in enumerate(es) if j != i):
                changed = True
            else:
                keep.append(e)
        es = keep
    return len(es), len(set().union(*es)) if es else 0


# Qualifier classes used for the filtered variants. The class assignment is this probe's reading
# of each property's English description (fetched 2026-09-23), not a Wikidata classification.
STATEMENT_META = {
    "P2241",  # reason for deprecated rank
    "P7452",  # reason for preferred rank
    "P5102",  # nature of statement
    "P1480",  # sourcing circumstances
    "P3680",  # statement supported by
    "P1310",  # statement disputed by
    "P805",   # statement is subject of
    "P1810",  # subject named as
    "P1932",  # object named as
}
TEMPORAL = {
    "P580", "P582", "P585",   # start time, end time, point in time
    "P1319", "P1326",         # earliest date, latest date
    "P8554", "P8555", "P12506",  # earliest end date, latest start date, latest end date
    "P1264",                  # valid in period
    "P1534",                  # end cause
    "P13883", "P13884",       # start work, end work (fictional)
}


def build(convention: str, table: dict[str, list[str]]) -> list[frozenset]:
    out = []
    for p, qs in table.items():
        if convention == "A_generic":
            e = {"subject", "value"} | set(qs)
        elif convention == "B_typed":
            e = {"subject", f"value@{p}"} | set(qs)
        elif convention == "C_local":
            e = {f"subject@{p}", f"value@{p}"} | set(qs)
        elif convention == "D_rel_local":
            e = {f"{p}:subject", f"{p}:value"} | {f"{p}:{q}" for q in qs}
        elif convention == "E_role_is_property":
            e = {"subject", p} | set(qs)
        else:
            raise ValueError(convention)
        out.append(frozenset(e))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.environ.get("WD_CACHE", "/tmp/wd_schema_probe_cache"))
    args = ap.parse_args()
    cache = Path(args.cache)

    table: dict[str, list[str]] = {}
    meta: dict[str, dict] = {}
    for pid in PROPS:
        ent = fetch(pid, cache)
        quals, novalue = allowed_qualifiers(ent)
        meta[pid] = {
            "label": ent.get("labels", {}).get("en", {}).get("value"),
            "modified": ent.get("modified"),
            "has_allowed_qualifiers_constraint": quals is not None,
            "novalue": novalue,
            "n_allowed": len(quals or []),
        }
        if quals is not None and not novalue:
            table[pid] = quals

    variants = {
        "all qualifiers": table,
        "without statement-metadata qualifiers": {
            p: [q for q in qs if q not in STATEMENT_META] for p, qs in table.items()
        },
        "without statement-metadata and temporal qualifiers": {
            p: [q for q in qs if q not in STATEMENT_META | TEMPORAL] for p, qs in table.items()
        },
    }
    results = {}
    for vname, vtable in variants.items():
        for conv in ["A_generic", "B_typed", "C_local", "D_rel_local", "E_role_is_property"]:
            edges = build(conv, vtable)
            deg = Counter(v for e in edges for v in e)
            res_e, res_v = gyo_residue(edges)
            results[f"{vname} | {conv}"] = {
                "hyperedges": len(edges),
                "vertices": len(deg),
                "alpha_acyclic": gyo_alpha_acyclic(edges),
                "beta_acyclic": beta_acyclic(edges),
                "gyo_residue_edges": res_e,
                "gyo_residue_vertices": res_v,
                "top_shared_attributes": deg.most_common(8),
            }

    # Main properties that also occur as allowed qualifiers of another property in the sample
    as_qual = {q for qs in table.values() for q in qs}
    dual_use = sorted(p for p in table if p in as_qual)

    out = {
        "fetched_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "properties": meta,
        "allowed_qualifiers": table,
        "properties_used_both_as_main_and_as_allowed_qualifier": dual_use,
        "results": results,
    }
    (HERE / "wikidata_schema_hypergraph_results.json").write_text(json.dumps(out, indent=1))

    lines = [
        "# Wikidata allowed-qualifier schema hypergraph: results",
        "",
        f"Fetched {out['fetched_utc']} from Special:EntityData. Script: "
        "`wikidata_schema_hypergraph_probe.py`.",
        "",
        "| Property | Label | Allowed-qualifiers constraint | Allowed qualifiers | Entity modified |",
        "|---|---|---|---|---|",
    ]
    for pid, m in meta.items():
        lines.append(
            f"| {pid} | {m['label']} | {'yes' if m['has_allowed_qualifiers_constraint'] else 'no'}"
            f"{' (novalue)' if m['novalue'] else ''} | {m['n_allowed']} | {m['modified']} |"
        )
    lines += [
        "",
        f"Properties in the sample that are also allowed qualifiers of another sampled property: "
        f"{', '.join(dual_use) or 'none'}.",
        "",
        "| Qualifier set and convention | Hyperedges | Vertices | alpha-acyclic | beta-acyclic "
        "| GYO residue (edges / vertices) | Most shared attributes |",
        "|---|---|---|---|---|---|---|",
    ]
    for conv, r in results.items():
        top = ", ".join(f"{v} ({n})" for v, n in r["top_shared_attributes"][:4])
        lines.append(
            f"| {conv} | {r['hyperedges']} | {r['vertices']} | {r['alpha_acyclic']} | "
            f"{r['beta_acyclic']} | {r['gyo_residue_edges']} / {r['gyo_residue_vertices']} | {top} |"
        )
    (HERE / "wikidata_schema_hypergraph_results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
