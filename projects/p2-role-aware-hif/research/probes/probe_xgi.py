#!/usr/bin/env python3
"""What XGI does with HIF, and with role-labelled incidences in particular (P2 research, 2026-09-23).

For every case in lib-cases/ (c00 is schemas/sample.hif.json itself):

1. load with the library's own reader, ``xgi.read_hif(path)``;
2. report where each HIF field ended up in the XGI object (and search the whole object state for
   the role strings, to show whether they are stored anywhere at all);
3. write back with ``xgi.write_hif(H, path)``;
4. diff input vs output structurally (probe_common.diff_hif);
5. read the output again and write it again (second generation) to test idempotence.

Then run native operations that might drop attributes (copy, subhypergraph, add edge, remove node,
dual, merge duplicate edges, cleanup, relabel, <<, to_hypergraph) and re-export.

Outputs: out/xgi/<case>.json (full report), out/xgi/<case>.out.hif.json (library output, verbatim),
out/xgi-summary.json, out/xgi-ops.json.

Run:  <venv>/bin/python probe_xgi.py
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
import traceback
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from probe_common import (ABSENT, OUT_DIR, REPO, build_cases, case_path, deep_find_strings, diff_hif,  # noqa: E402
                          dump, env_info, idkey, is_strict_json_text, jsonable, roles_of, sha256_file,
                          validate_hif)

import xgi  # noqa: E402
from xgi.convert import from_hif_dict, to_hif_dict  # noqa: E402

LIB_OUT = os.path.join(OUT_DIR, "xgi")
SITE = os.path.dirname(os.path.dirname(xgi.__file__))


def err_info(e):
    tb = traceback.extract_tb(e.__traceback__)
    frames = [f for f in tb if "site-packages" in f.filename]
    loc = None
    if frames:
        f = frames[-1]
        loc = f"{f.filename.split('site-packages/')[-1]}:{f.lineno} in {f.name}: {f.line}"
    lib = [f for f in frames if "site-packages/xgi/" in f.filename]
    lib_loc = None
    if lib:
        f = lib[-1]
        lib_loc = f"{f.filename.split('site-packages/')[-1]}:{f.lineno} in {f.name}: {f.line}"
    return {"type": type(e).__name__, "message": str(e)[:400], "raised_at": loc, "library_frame": lib_loc}


def run(fn):
    """Call fn(); return (value, error_info, warnings)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            val = fn()
            err = None
        except Exception as e:  # report, never hide
            val, err = None, err_info(e)
    ws = [f"{x.category.__name__}: {str(x.message).replace(REPO, '<repo>')[:200]} "
          f"({os.path.basename(x.filename)}:{x.lineno})" for x in w]
    return val, err, ws


def members_of(H):
    out = {}
    for e in H.edges:
        if isinstance(H, xgi.DiHypergraph):
            out[idkey(e)] = {"tail": sorted(map(idkey, H.edges.tail(e))),
                             "head": sorted(map(idkey, H.edges.head(e)))}
        else:
            out[idkey(e)] = {"members": sorted(map(idkey, H.edges.members(e)))}
    return out


def placement(H, doc):
    p = {"class": type(H).__name__, "num_nodes": H.num_nodes, "num_edges": H.num_edges}
    p["net_attr (H._net_attr)"] = dict(H._net_attr)
    p["node_attrs (H.nodes[n])"] = {idkey(n): dict(H.nodes[n]) for n in H.nodes}
    p["edge_attrs (H.edges[e])"] = {idkey(e): dict(H.edges[e]) for e in H.edges}
    p["edge_members"] = members_of(H)
    state = H.__getstate__()
    roles = roles_of(doc)
    hits = deep_find_strings(state, set(roles))
    p["role_strings_in_object_state"] = {r: hits.get(r, []) for r in roles}
    # numeric weights: look for the exact non-integral weight values of the input in the object state
    wvals = set()
    for kind in ("nodes", "edges", "incidences"):
        for r in doc.get(kind, []) or []:
            w = r.get("weight")
            if isinstance(w, float) and not float(w).is_integer():
                wvals.add(w)
    p["record_weight_values_in_object_state"] = sorted(v for v in wvals if _find_number(state, v))
    p["record_weight_values_searched"] = sorted(wvals)
    return p


def _find_number(obj, val, depth=0):
    if depth > 12:
        return False
    if isinstance(obj, float):
        return obj == val
    if isinstance(obj, dict):
        return any(_find_number(k, val, depth + 1) or _find_number(v, val, depth + 1) for k, v in obj.items())
    if isinstance(obj, (list, tuple, set, frozenset)):
        return any(_find_number(v, val, depth + 1) for v in obj)
    return False


def field_locations(H, doc, p):
    """One line per HIF field: where it lives in the XGI object (derived from `placement`)."""
    loc = {}
    roles = roles_of(doc)
    found = [r for r in roles if p["role_strings_in_object_state"].get(r)]
    loc["incidence.attrs (role)"] = (f"found for {len(found)}/{len(roles)} role strings" if roles else "n/a")
    has_dir = any("direction" in r for r in doc.get("incidences", []))
    if has_dir:
        loc["incidence.direction"] = ("DiHypergraph edge 'in' (tail) / 'out' (head) member sets"
                                      if isinstance(H, xgi.DiHypergraph) else f"dropped ({type(H).__name__})")
    else:
        loc["incidence.direction"] = "n/a"
    wv = p["record_weight_values_searched"]
    loc["record-level weight values"] = (f"{len(p['record_weight_values_in_object_state'])}/{len(wv)} found"
                                         if wv else "n/a")
    loc["network-type"] = f"class {type(H).__name__}"
    md = doc.get("metadata") or {}
    loc["metadata"] = ("H._net_attr: " + ("all keys" if set(md) <= set(H._net_attr) else
                                          f"missing {sorted(set(md) - set(H._net_attr))}")) if md else "n/a"
    return loc


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def probe_case(name, case):
    path = case_path(name)
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    rep = {"case": name, "description": case["description"], "input": os.path.relpath(path, HERE),
           "lib": "xgi", "lib_version": xgi.__version__}

    H, err, ws = run(lambda: xgi.read_hif(path))
    rep["load"] = {"api": "xgi.read_hif(path)", "ok": err is None, "error": err, "warnings": ws,
                   "class": type(H).__name__ if H is not None else None}
    if H is None:
        # does the dict-level reader behave the same?
        _, err2, _ = run(lambda: from_hif_dict(copy.deepcopy(doc)))
        rep["load"]["from_hif_dict_error"] = err2
        return rep

    rep["placement"] = placement(H, doc)
    rep["field_locations"] = field_locations(H, doc, rep["placement"])

    out_path = os.path.join(LIB_OUT, name + ".out.hif.json")
    os.makedirs(LIB_OUT, exist_ok=True)
    _, err, ws = run(lambda: xgi.write_hif(H, out_path))
    rep["export"] = {"api": "xgi.write_hif(H, path)", "ok": err is None, "error": err, "warnings": ws,
                     "output": os.path.relpath(out_path, HERE) if err is None else None}
    if err is not None:
        return rep
    text = read_text(out_path)
    strict, why = is_strict_json_text(text)
    out = json.loads(text)
    rep["export"]["strict_json"] = strict if strict else why
    rep["export"]["schema_errors"] = validate_hif(out)
    rep["export"]["top_level_keys"] = sorted(out)
    rep["export"]["n_node_records"] = len(out.get("nodes", []))
    rep["export"]["n_edge_records"] = len(out.get("edges", []))
    # the in-memory dict path, for comparison
    d, err_d, _ = run(lambda: json.loads(json.dumps(to_hif_dict(H), allow_nan=True, default=str)))
    rep["export"]["to_hif_dict_equals_file"] = (err_d is None and json.dumps(d, sort_keys=True, default=str)
                                                == json.dumps(out, sort_keys=True, default=str))
    rep["diff"] = diff_hif(doc, out)

    # second generation
    H2, err, _ = run(lambda: xgi.read_hif(out_path))
    rep["gen2"] = {"load_error": err}
    if H2 is not None:
        out2_path = os.path.join(LIB_OUT, name + ".out2.hif.json")
        _, err, _ = run(lambda: xgi.write_hif(H2, out2_path))
        rep["gen2"]["export_error"] = err
        if err is None:
            out2 = json.loads(read_text(out2_path))
            d12 = diff_hif(out, out2)["summary"]
            rep["gen2"]["idempotent (gen1 == gen2 structurally)"] = _summary_is_identity(d12)
            rep["gen2"]["diff_gen1_gen2_summary"] = d12
    return rep


def _summary_is_identity(s):
    ok = s["pairs_lost"] == 0 and s["pairs_new"] == 0 and s["pairs_count_changed"] == 0
    ok &= s["network_type"].startswith("preserved") and s["metadata"] == "preserved"
    for k in ("nodes", "edges"):
        ok &= not s[k]["missing_out"] and not s[k]["attrs_not_preserved"] and not s[k]["weight_not_preserved"]
    for k in ("role_records_kept", "direction_records_kept", "incidence_weight_records_kept",
              "incidence_attrs_records_kept"):
        a, b = s[k].split("/")
        ok &= a == b
    return bool(ok)


# --------------------------------------------------------------------------------------------
# Native operations
# --------------------------------------------------------------------------------------------

def attr_survival(before, after):
    """Compare node/edge attr dicts of objects that exist in both (by id)."""
    res = {"compared": 0, "identical": 0, "changed": {}, "missing_ids": []}
    for k, a in before.items():
        if k not in after:
            res["missing_ids"].append(k)
            continue
        res["compared"] += 1
        if json.dumps(jsonable(a), sort_keys=True) == json.dumps(jsonable(after[k]), sort_keys=True):
            res["identical"] += 1
        else:
            res["changed"][k] = {"before": a, "after": after[k]}
    return res


def snapshot(H):
    return {
        "class": type(H).__name__,
        "nodes": {idkey(n): dict(H.nodes[n]) for n in H.nodes},
        "edges": {idkey(e): dict(H.edges[e]) for e in H.edges},
        "net": dict(H._net_attr),
        "members": members_of(H),
    }


def op_report(label, base_snap, fn, doc):
    res, err, ws = run(fn)
    r = {"op": label, "ok": err is None, "error": err, "warnings": ws}
    if err is not None or res is None:
        return r
    s = snapshot(res)
    r["class"] = s["class"]
    r["num_nodes"], r["num_edges"] = len(s["nodes"]), len(s["edges"])
    r["node_attrs"] = attr_survival(base_snap["nodes"], s["nodes"])
    r["edge_attrs"] = attr_survival(base_snap["edges"], s["edges"])
    r["net_attrs_identical"] = (json.dumps(jsonable(base_snap["net"]), sort_keys=True)
                                == json.dumps(jsonable(s["net"]), sort_keys=True))
    r["new_node_ids"] = sorted(set(s["nodes"]) - set(base_snap["nodes"]))[:12]
    r["new_edge_ids"] = sorted(set(s["edges"]) - set(base_snap["edges"]))[:12]
    # members of edges that survived under the same id
    same = {}
    for k, m in s["members"].items():
        if k in base_snap["members"]:
            same[k] = "same" if m == base_snap["members"][k] else {"before": base_snap["members"][k], "after": m}
    r["members_of_surviving_edges"] = same
    # re-export with the library writer
    tmp = os.path.join(LIB_OUT, "ops", re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("_")[:80] + ".out.hif.json")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    _, err2, _ = run(lambda: xgi.write_hif(res, tmp))
    r["write_hif_ok"] = err2 is None
    r["write_hif_error"] = err2
    if err2 is None:
        out = json.loads(read_text(tmp))
        r["export_summary_vs_input"] = diff_hif(doc, out)["summary"]
    return r


def run_ops():
    cases = build_cases()
    ops = []

    def fresh(name):
        return xgi.read_hif(case_path(name))

    # undirected Hypergraph from the sample
    und = "c01-sample-undirected"
    doc_u = json.load(open(case_path(und), encoding="utf-8"))
    base = snapshot(fresh(und))
    ops.append(op_report("Hypergraph.copy()", base, lambda: fresh(und).copy(), doc_u))
    ops.append(op_report("xgi.subhypergraph(H, nodes=[metformin, T2DM, insulin, hypoglycemia])", base,
                         lambda: xgi.subhypergraph(fresh(und), nodes=["drug:metformin", "disease:T2DM",
                                                                      "drug:insulin", "effect:hypoglycemia"]),
                         doc_u))
    ops.append(op_report("xgi.subhypergraph(H, edges=[f1, f3])", base,
                         lambda: xgi.subhypergraph(fresh(und), edges=["f1", "f3"]), doc_u))

    def add_edge():
        H = fresh(und)
        H.add_edge(["drug:metformin", "disease:T2DM"], idx="f4", relation="new-fact")
        return H
    ops.append(op_report("Hypergraph.add_edge(members, idx='f4', relation=...)", base, add_edge, doc_u))

    def add_node_to_edge():
        H = fresh(und)
        H.add_node_to_edge("f1", "pop:children")
        return H
    ops.append(op_report("Hypergraph.add_node_to_edge('f1', 'pop:children')", base, add_node_to_edge, doc_u))

    def rm_weak():
        H = fresh(und)
        H.remove_node("dose:500mg-bid")
        return H
    ops.append(op_report("Hypergraph.remove_node('dose:500mg-bid') (weak)", base, rm_weak, doc_u))

    def rm_strong():
        H = fresh(und)
        H.remove_node("drug:metformin", strong=True)
        return H
    ops.append(op_report("Hypergraph.remove_node('drug:metformin', strong=True)", base, rm_strong, doc_u))
    ops.append(op_report("Hypergraph.dual()", base, lambda: fresh(und).dual(), doc_u))

    def merge():
        H = fresh(und)
        H.add_edge(H.edges.members("f1"), idx="f1-copy", relation="treats-duplicate", extra="only-on-copy")
        H.merge_duplicate_edges()
        return H
    r = op_report("Hypergraph.merge_duplicate_edges() after adding a copy of f1", base, merge, doc_u)
    Hm = merge()
    r["edge_ids_after"] = sorted(map(idkey, Hm.edges))
    r["attrs_of_surviving_f1"] = dict(Hm.edges["f1"]) if "f1" in Hm.edges else None
    ops.append(r)

    def cleanup_default():
        H = fresh(und)
        return H.cleanup(in_place=False)
    ops.append(op_report("Hypergraph.cleanup(in_place=False) (defaults)", base, cleanup_default, doc_u))
    r = op_report("xgi.convert_labels_to_integers(H)", base, lambda: xgi.convert_labels_to_integers(fresh(und)), doc_u)
    Hl = xgi.convert_labels_to_integers(fresh(und))
    r["node_label_attr_before_after"] = {str(Hl.nodes[i]["label"]): base["nodes"][idkey(Hl.nodes[i]["label"])].get("label")
                                         for i in list(Hl.nodes)[:3]}
    ops.append(r)

    def lshift():
        H = fresh(und)
        H2 = xgi.Hypergraph()
        H2.add_edge(["drug:metformin", "effect:lactic-acidosis"], idx="f9", relation="causes")
        return H << H2
    ops.append(op_report("H << H2 (Hypergraph.__lshift__)", base, lshift, doc_u))

    # directed DiHypergraph from the sample
    dct = "c00-sample-directed"
    doc_d = json.load(open(case_path(dct), encoding="utf-8"))
    based = snapshot(fresh(dct))
    ops.append(op_report("DiHypergraph.copy()", based, lambda: fresh(dct).copy(), doc_d))
    ops.append(op_report("xgi.subhypergraph(DH, nodes=[metformin, T2DM]) (no edge is a subset)", based,
                         lambda: xgi.subhypergraph(fresh(dct), nodes=["drug:metformin", "disease:T2DM"]), doc_d))
    ops.append(op_report("xgi.subhypergraph(DH, nodes=[org:ADA, doc:guideline-2024]) (f3 is a subset)", based,
                         lambda: xgi.subhypergraph(fresh(dct), nodes=["org:ADA", "doc:guideline-2024"]), doc_d))

    def dadd():
        H = fresh(dct)
        H.add_edge((["drug:metformin"], ["disease:T2DM"]), idx="f4", relation="new-fact")
        return H
    ops.append(op_report("DiHypergraph.add_edge((tail, head), idx='f4', relation=...)", based, dadd, doc_d))

    def drm():
        H = fresh(dct)
        H.remove_node("dose:500mg-bid")
        return H
    ops.append(op_report("DiHypergraph.remove_node('dose:500mg-bid') (weak)", based, drm, doc_d))
    ops.append(op_report("DiHypergraph.dual()", based, lambda: fresh(dct).dual(), doc_d))
    ops.append(op_report("xgi.convert_labels_to_integers(DH)", based,
                         lambda: xgi.convert_labels_to_integers(fresh(dct)), doc_d))
    ops.append(op_report("xgi.Hypergraph(DH) (to undirected)", based, lambda: xgi.Hypergraph(fresh(dct)), doc_d))

    # asc: does metadata survive the Hypergraph -> SimplicialComplex conversion inside from_hif_dict?
    asc = "c04-asc"
    doc_a = json.load(open(case_path(asc), encoding="utf-8"))
    Ha = fresh(asc)
    ops.append({"op": "read_hif(asc file): metadata and subfaces",
                "class": type(Ha).__name__, "net_attr": dict(Ha._net_attr),
                "metadata_keys_in_file": sorted(doc_a.get("metadata", {})),
                "num_edges_in_file": len({r['edge'] for r in doc_a['incidences']}),
                "num_edges_loaded": Ha.num_edges,
                "edges_with_attrs_loaded": sum(1 for e in Ha.edges if Ha.edges[e])})
    return ops


def main():
    os.makedirs(LIB_OUT, exist_ok=True)
    env = env_info()
    env["xgi"] = xgi.__version__
    import locale
    env["preferred_encoding"] = locale.getpreferredencoding(False)
    env["source_sha256"] = {p: sha256_file(os.path.join(SITE, p)) for p in (
        "xgi/convert/hif_dict.py", "xgi/readwrite/hif.py", "xgi/core/hypergraph.py", "xgi/core/dihypergraph.py",
        "xgi/core/globalviews.py", "xgi/utils/utilities.py", "xgi/convert/bipartite_edges.py",
        "xgi/convert/higher_order_network.py")}
    summary = {"env": env, "cases": {}}
    for name, case in build_cases().items():
        rep = probe_case(name, case)
        dump(rep, os.path.join(LIB_OUT, name + ".json"))
        s = {"load": "ok" if rep["load"]["ok"] else f"ERROR {rep['load']['error']['type']}: "
             f"{rep['load']['error']['message'][:80]} @ {rep['load']['error']['raised_at']}",
             "class": rep["load"].get("class")}
        if "export" in rep:
            s["export"] = "ok" if rep["export"]["ok"] else f"ERROR {rep['export']['error']}"
            s["schema_valid_output"] = not rep["export"].get("schema_errors")
            s["strict_json_output"] = rep["export"].get("strict_json")
        if "diff" in rep:
            s["diff"] = rep["diff"]["summary"]
        if "field_locations" in rep:
            s["field_locations"] = rep["field_locations"]
        if "gen2" in rep:
            s["gen2_idempotent"] = rep["gen2"].get("idempotent (gen1 == gen2 structurally)")
        summary["cases"][name] = s
        print(f"{name:40s} load={s['load'][:60]:60s} roles={s.get('diff', {}).get('role_records_kept')}"
              f" dir={s.get('diff', {}).get('direction_records_kept')}")
    dump(summary, os.path.join(OUT_DIR, "xgi-summary.json"))
    ops = run_ops()
    dump({"env": env, "ops": ops}, os.path.join(OUT_DIR, "xgi-ops.json"))
    for o in ops:
        print(f"OP {o['op'][:70]:70s} ok={o.get('ok', '-')} err={(o.get('error') or {}).get('type')}")


if __name__ == "__main__":
    main()
