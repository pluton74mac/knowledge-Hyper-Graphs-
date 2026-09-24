#!/usr/bin/env python3
"""Does the approach in role_loaders_sketch.py keep roles (and everything else) intact? (P2, 2026-09-23)

1. Every case in lib-cases/ goes HIF -> XGI -> HIF and HIF -> HyperNetX -> HIF through the sketch
   adapters, twice (idempotence), and along the gate's chain HIF -> XGI -> HIF -> HyperNetX -> HIF.
   Inputs are parsed as strict JSON (NaN/Infinity rejected), as the P2 validator would.
2. Native operations are applied to the library objects between load and export, and the exported
   roles are checked: kept (same (edge, node, role) as the input), wrong (a role on a pair that did
   not have it), stale (records dropped because their membership is gone), unlabelled (memberships
   exported without a record). For XGI two placements of the incidence records are compared:
   A = context/side table keyed by ids (the sketch), B = a list of records stored in each edge's attrs.

No network access is needed: neither library's HIF module is used.

Outputs: out/rolepreserving-summary.json, out/rolepreserving-ops.json, out/rolepreserving/<case>.<lib>.out.hif.json
"""
from __future__ import annotations

import copy
import json
import os
import sys
import traceback
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from probe_common import OUT_DIR, build_cases, case_path, diff_hif, dump, env_info  # noqa: E402
import role_loaders_sketch as rl  # noqa: E402

import xgi  # noqa: E402
import hypernetx as hnx  # noqa: E402
from hypernetx import hif as hnx_hif  # noqa: E402

OUT = os.path.join(OUT_DIR, "rolepreserving")


def strict_load(path):
    def bad(c):
        raise ValueError(f"non-standard JSON constant {c}")
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read(), parse_constant=bad)


def exact(s):
    """True when a diff summary shows nothing lost, added or altered."""
    ok = s["pairs_lost"] == 0 and s["pairs_new"] == 0 and s["pairs_count_changed"] == 0
    ok &= s["weights_added_on_incidences"] == 0 and s["id_type_changes"] == 0
    ok &= s["network_type"].startswith("preserved") and s["metadata"] == "preserved"
    for k in ("nodes", "edges"):
        ok &= not s[k]["missing_out"] and not s[k]["attrs_not_preserved"] and not s[k]["weight_not_preserved"]
        ok &= not s[k]["new_out"]
    for k in ("role_records_kept", "direction_records_kept", "incidence_weight_records_kept",
              "incidence_attrs_records_kept"):
        a, b = s[k].split("/")
        ok &= a == b
    return bool(ok)


def not_exact_because(s):
    why = []
    for k in ("pairs_lost", "pairs_new", "pairs_count_changed", "weights_added_on_incidences", "id_type_changes"):
        if s[k]:
            why.append(f"{k}={s[k]}")
    if not s["network_type"].startswith("preserved"):
        why.append(f"network-type {s['network_type']}")
    if s["metadata"] != "preserved":
        why.append(f"metadata {s['metadata']}")
    for k in ("nodes", "edges"):
        for f in ("missing_out", "attrs_not_preserved", "weight_not_preserved", "new_out"):
            if s[k][f]:
                why.append(f"{k}.{f}={s[k][f]}")
    for k in ("role_records_kept", "direction_records_kept", "incidence_weight_records_kept",
              "incidence_attrs_records_kept"):
        a, b = s[k].split("/")
        if a != b:
            why.append(f"{k}={s[k]}")
    return why


def roundtrip(doc, to, frm):
    H, ctx = to(copy.deepcopy(doc))
    out = json.loads(json.dumps(frm(H, ctx), allow_nan=False))
    return out, ctx


def run_cases():
    res = {}
    os.makedirs(OUT, exist_ok=True)
    libs = {"xgi": (rl.to_xgi, rl.from_xgi), "hnx": (rl.to_hnx, rl.from_hnx)}
    for name, case in build_cases().items():
        r = {"description": case["description"]}
        try:
            doc = strict_load(case_path(name))
        except ValueError as e:
            r["input"] = f"rejected at parse: {e}"
            res[name] = r
            continue
        for lib, (to, frm) in libs.items():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    out, ctx = roundtrip(doc, to, frm)
                    s = diff_hif(doc, out)["summary"]
                    out2, _ = roundtrip(out, to, frm)
                    s2 = diff_hif(out, out2)["summary"]
                    with open(os.path.join(OUT, f"{name}.{lib}.out.hif.json"), "w", encoding="utf-8") as f:
                        json.dump(out, f, ensure_ascii=False, indent=1)
                    r[lib] = {"exact": exact(s), "roles": s["role_records_kept"],
                              "direction": s["direction_records_kept"],
                              "not_exact_because": not_exact_because(s), "idempotent": exact(s2),
                              "reconcile_report": {k: len(v) for k, v in ctx.report.items()}}
                except rl.HIFError as e:
                    r[lib] = {"rejected": str(e)[:200]}
                except Exception as e:
                    tb = traceback.extract_tb(e.__traceback__)[-1]
                    r[lib] = {"error": f"{type(e).__name__}: {str(e)[:200]} @ {os.path.basename(tb.filename)}:{tb.lineno}"}
        # the gate's chain: HIF -> XGI -> HIF -> HNX -> HIF
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                mid, _ = roundtrip(doc, rl.to_xgi, rl.from_xgi)
                end, _ = roundtrip(mid, rl.to_hnx, rl.from_hnx)
                s = diff_hif(doc, end)["summary"]
                r["chain HIF->XGI->HIF->HNX->HIF"] = {"exact": exact(s), "roles": s["role_records_kept"],
                                                      "not_exact_because": not_exact_because(s)}
            except rl.HIFError as e:
                r["chain HIF->XGI->HIF->HNX->HIF"] = {"rejected": str(e)[:200]}
            except Exception as e:
                r["chain HIF->XGI->HIF->HNX->HIF"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        res[name] = r
    return res


# --------------------------------------------------------------------------------------------
# native operations between load and export
# --------------------------------------------------------------------------------------------

def triples(doc, swap=False):
    out = []
    for r in doc["incidences"]:
        role = (r.get("attrs") or {}).get("role")
        if role is None:
            continue
        e, n = (r["node"], r["edge"]) if swap else (r["edge"], r["node"])
        out.append((json.dumps(e), json.dumps(n), role))
    return out


def role_check(doc_in, doc_out, ctx_report=None, swap=False, edge_map=None, node_map=None, expected_new=()):
    """edge_map/node_map translate output ids back to input ids for ops that rename or renumber;
    expected_new lists (edge, node, role) triples the op added on purpose."""
    tin = triples(doc_in, swap=swap)
    em = {json.dumps(k): json.dumps(v) for k, v in (edge_map or {}).items()}
    nm = {json.dumps(k): json.dumps(v) for k, v in (node_map or {}).items()}
    tout = [(em.get(e, e), nm.get(n, n), r) for e, n, r in triples(doc_out)]
    exp = {(json.dumps(e), json.dumps(n), r) for e, n, r in expected_new}
    sin = set(tin)
    kept = sum(1 for t in tout if t in sin)
    wrong = [t for t in tout if t not in sin and t not in exp]
    unl = sum(1 for r in doc_out["incidences"] if (r.get("attrs") or {}).get("role") is None)
    res = {"input_role_records": len(tin), "output_role_records": len(tout), "kept": kept,
           "wrong (role on a pair that did not have it)": wrong[:6], "wrong_count": len(wrong),
           "output_records_without_role": unl, "id_mapping_applied": bool(edge_map or node_map)}
    if ctx_report is not None:
        res["stale_records_dropped"] = len(ctx_report.get("stale_records_dropped", []))
    return res


STASH = "khg:incidences"


def to_xgi_edge_stash(doc):
    """Strategy B: the incidence records of each edge are kept in that edge's attrs."""
    H, ctx = rl.to_xgi(doc)
    by_edge = {}
    for r in doc["incidences"]:
        by_edge.setdefault(rl._k(r["edge"]), []).append({k: v for k, v in r.items() if k != "edge"})
    for e in H.edges:
        H.set_edge_attributes({e: {STASH: copy.deepcopy(by_edge.get(rl._k(e), []))}})
    return H, ctx


def from_xgi_edge_stash(H, ctx):
    directed = isinstance(H, xgi.DiHypergraph)
    stash = {}
    for e in H.edges:
        stash[e] = H.edges[e].get(STASH, []) if STASH in H.edges[e] else []
    # strip the stash before the generic export, then rebuild incidences from it
    H2 = H.copy()
    for e in H2.edges:
        if STASH in H2.edges[e]:
            del H2._edge_attr[e][STASH]
    ctx2 = copy.copy(ctx)
    ctx2.incidences = [dict(edge=e, **r) for e in stash for r in stash[e]]
    out = rl.from_xgi(H2, ctx2)
    ctx.report = ctx2.report
    return out


def xgi_ops():
    ops = []
    for case in ("c00-sample-directed", "c01-sample-undirected", "c05-two-roles-same-direction"):
        doc = strict_load(case_path(case))
        directed = doc.get("network-type") == "directed"
        members = {r["edge"]: None for r in doc["incidences"]}
        first_edge = next(iter(members))
        nodes_first_edge = [r["node"] for r in doc["incidences"] if r["edge"] == first_edge]
        last_edge = list(members)[-1]
        some_nodes = sorted({r["node"] for r in doc["incidences"] if r["edge"] == last_edge}
                            | {nodes_first_edge[0]})

        def label_maps(H2):
            return ({e: H2.edges[e].get("label") for e in H2.edges if "label" in H2.edges[e]},
                    {n: H2.nodes[n].get("label") for n in H2.nodes if "label" in H2.nodes[n]})

        def lshift(H):
            old = list(H.edges)
            H2 = H << xgi.Hypergraph([["x1", "x2"]])
            return H2, {i: e for i, e in enumerate(old)}, None

        def relabel(H):
            H2 = xgi.convert_labels_to_integers(H)
            em, nm = label_maps(H2)
            return H2, em, nm

        def op_list():
            L = [("copy()", lambda H: H.copy(), False),
                 (f"remove_node({nodes_first_edge[-1]!r}) weak", lambda H: (H.remove_node(nodes_first_edge[-1]), H)[1], False),
                 (f"remove_node({nodes_first_edge[0]!r}, strong=True)",
                  lambda H: (H.remove_node(nodes_first_edge[0], strong=True), H)[1], False),
                 ("add_edge(new edge)", lambda H: (H.add_edge(((nodes_first_edge[:1], nodes_first_edge[1:2]) if directed
                                                              else nodes_first_edge[:2]), idx="new-edge"), H)[1], False),
                 ("convert_labels_to_integers() [ids mapped back via the 'label' attr]", relabel, False)]
            if not directed:
                L += [(f"subhypergraph(nodes={some_nodes})", lambda H: xgi.subhypergraph(H, nodes=some_nodes), False),
                      ("dual()", lambda H: H.dual(), True),
                      ("add copy of first edge, merge_duplicate_edges()",
                       lambda H: (H.add_edge(H.edges.members(first_edge), idx="zz-copy"), H.merge_duplicate_edges(), H)[2],
                       False),
                      ("H << H2 [edge ids mapped back by position]", lshift, False)]
            return L

        for label, fn, swap in op_list():
            row = {"case": case, "op": label}
            for strat, (to, frm) in {"A: side table (sketch)": (rl.to_xgi, rl.from_xgi),
                                     "B: records in edge attrs": (to_xgi_edge_stash, from_xgi_edge_stash)}.items():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        H, ctx = to(copy.deepcopy(doc))
                        res = fn(H)
                        H2, em, nm = res if isinstance(res, tuple) else (res, None, None)
                        out = json.loads(json.dumps(frm(H2, ctx)))
                        row[strat] = role_check(doc, out, ctx.report, swap=swap, edge_map=em, node_map=nm)
                    except Exception as e:
                        tb = traceback.extract_tb(e.__traceback__)[-1]
                        row[strat] = {"error": f"{type(e).__name__}: {str(e)[:160]} @ "
                                               f"{tb.filename.split('site-packages/')[-1]}:{tb.lineno}"}
            ops.append(row)
    return ops


def hnx_ops():
    ops = []
    for case in ("c00-sample-directed", "c05-two-roles-same-direction"):
        doc = strict_load(case_path(case))
        e0 = doc["incidences"][0]["edge"]
        n0 = doc["incidences"][0]["node"]
        nodes = sorted({r["node"] for r in doc["incidences"]})
        maps = {f"rename(nodes={{{n0!r}: 'renamed'}})": (None, {"renamed": n0}, ()),
                f"add_incidence({e0!r}, 'new-node', role='added', direction='tail')": (None, None, [(e0, "new-node", "added")])}
        L = [("clone()", lambda H: H.clone(), False),
             (f"restrict_to_nodes({nodes[:3]})", lambda H: H.restrict_to_nodes(nodes[:3]), False),
             (f"remove_nodes({nodes[-1]!r})", lambda H: H.remove_nodes(nodes[-1], inplace=False), False),
             (f"remove_incidences(({e0!r}, {n0!r}))", lambda H: H.remove_incidences((e0, n0), inplace=False), False),
             (f"rename(nodes={{{n0!r}: 'renamed'}})", lambda H: H.rename(nodes={n0: "renamed"}, inplace=False), False),
             ("dual()", lambda H: H.dual(), True),
             ("collapse_nodes()", lambda H: H.collapse_nodes(), False),
             (f"add_incidence({e0!r}, 'new-node', role='added', direction='tail')",
              lambda H: H.add_incidence(e0, "new-node", role="added", direction="tail", inplace=False), False)]
        for label, fn, swap in L:
            row = {"case": case, "op": label}
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    H, ctx = rl.to_hnx(copy.deepcopy(doc))
                    H2 = fn(H)
                    out = json.loads(json.dumps(rl.from_hnx(H2, ctx)))
                    em, nm, exp = maps.get(label, (None, None, ()))
                    row["roles"] = role_check(doc, out, swap=swap, edge_map=em, node_map=nm, expected_new=exp)
                    row["hif_schema_errors"] = []
                    from probe_common import validate_hif
                    row["hif_schema_errors"] = validate_hif(out)
                except Exception as e:
                    tb = traceback.extract_tb(e.__traceback__)[-1]
                    row["error"] = f"{type(e).__name__}: {str(e)[:160]} @ {tb.filename.split('site-packages/')[-1]}:{tb.lineno}"
            ops.append(row)
    return ops


def main():
    # prove that no network is needed: make any use of hnx.hif's requests fail loudly
    def boom(*a, **k):
        raise RuntimeError("network used")
    hnx_hif.requests.get = boom
    env = env_info(("xgi", "hypernetx"))
    cases = run_cases()
    dump({"env": env, "cases": cases}, os.path.join(OUT_DIR, "rolepreserving-summary.json"))
    for n, r in cases.items():
        cells = []
        for lib in ("xgi", "hnx", "chain HIF->XGI->HIF->HNX->HIF"):
            v = r.get(lib, {})
            if "exact" in v:
                cells.append(f"{lib[:5]}: exact={v['exact']} roles={v['roles']}" +
                             (f" idem={v['idempotent']}" if "idempotent" in v else "") +
                             (f" WHY={v['not_exact_because']}" if not v["exact"] else ""))
            else:
                cells.append(f"{lib[:5]}: {v or r.get('input')}"[:90])
        print(f"{n:42s} " + " | ".join(cells))
    ops = {"xgi": xgi_ops(), "hnx": hnx_ops()}
    dump({"env": env, "ops": ops}, os.path.join(OUT_DIR, "rolepreserving-ops.json"))
    for lib, rows in ops.items():
        for row in rows:
            print(lib, row["case"][:12], row["op"][:48], json.dumps({k: v for k, v in row.items() if k not in ("case", "op")})[:300])


if __name__ == "__main__":
    main()
