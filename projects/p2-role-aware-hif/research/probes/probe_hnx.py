#!/usr/bin/env python3
"""What HyperNetX does with HIF, and with role-labelled incidences in particular (P2 research, 2026-09-23).

For every case in lib-cases/ (c00 is schemas/sample.hif.json itself):

1. load with the library's own reader, ``hnx.from_hif(filename=path)``;
2. report where each HIF field ended up (incidence / edge / node property stores, the accessor
   ``H.get_cell_properties``, the constructor arguments HNX keeps on the object);
3. write back with ``hnx.to_hif(H, filename=path, network_type=<input network-type or 'undirected'>)``,
   and once more with the default ``hnx.to_hif(H)``;
4. diff input vs output structurally (probe_common.diff_hif). When ``to_hif`` returns None (it does
   that instead of raising when its own output fails the schema), the probe calls it again with
   validation disabled to capture what it would have written, and validates that with jsonschema;
5. read the output again and write it again (second generation) to test idempotence.

Then: what happens without network access, and native operations that might drop cell properties
(clone, restrict, add/remove, dual, collapse, rename, sum, setting a cell property).

HyperNetX fetches its JSON Schema from raw.githubusercontent.com on *every* from_hif/to_hif call,
so this probe needs network access (except for the offline test, which simulates its absence).

Outputs: out/hnx/<case>.json, out/hnx/<case>.out.hif.json (library output, verbatim), out/hnx-summary.json,
out/hnx-ops.json, out/hnx-offline.json.

Run:  <venv>/bin/python probe_hnx.py
"""
from __future__ import annotations

import contextlib
import copy
import json
import os
import re
import sys
import time
import traceback
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from probe_common import (ABSENT, OUT_DIR, REPO, build_cases, case_path, deep_find_strings, diff_hif,  # noqa: E402
                          dump, env_info, idkey, is_strict_json_text, jsonable, roles_of, sha256_file,
                          validate_hif)

import pandas as pd  # noqa: E402
import requests  # noqa: E402
import hypernetx as hnx  # noqa: E402
from hypernetx import hif as hnx_hif  # noqa: E402

LIB_OUT = os.path.join(OUT_DIR, "hnx")
SITE = os.path.dirname(os.path.dirname(hnx.__file__))


def err_info(e):
    tb = traceback.extract_tb(e.__traceback__)
    frames = [f for f in tb if "site-packages" in f.filename]
    loc = None
    if frames:
        f = frames[-1]
        loc = f"{f.filename.split('site-packages/')[-1]}:{f.lineno} in {f.name}: {f.line}"
    lib = [f for f in frames if "site-packages/hypernetx/" in f.filename]
    lib_loc = None
    if lib:
        f = lib[-1]
        lib_loc = f"{f.filename.split('site-packages/')[-1]}:{f.lineno} in {f.name}: {f.line}"
    return {"type": type(e).__name__, "message": str(e)[:400], "raised_at": loc, "library_frame": lib_loc}


def run(fn):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            val, err = fn(), None
        except Exception as e:  # report, never hide
            val, err = None, err_info(e)
    ws = sorted({f"{x.category.__name__}: {str(x.message).replace(REPO, '<repo>')[:160]} "
                 f"({os.path.basename(x.filename)}:{x.lineno})" for x in w})
    return val, err, ws


@contextlib.contextmanager
def validation_disabled():
    """Make hnx.hif's fastjsonschema.compile return a no-op validator (to capture would-be output)."""
    orig = hnx_hif.fastjsonschema.compile
    hnx_hif.fastjsonschema.compile = lambda schema: (lambda doc: doc)
    try:
        yield
    finally:
        hnx_hif.fastjsonschema.compile = orig


@contextlib.contextmanager
def network_disabled():
    orig = hnx_hif.requests.get

    def boom(*a, **k):
        raise requests.ConnectionError("probe: network disabled")
    hnx_hif.requests.get = boom
    try:
        yield
    finally:
        hnx_hif.requests.get = orig


def frame_records(df, level):
    out = {}
    for idx, row in df.iterrows():
        key = f"{idkey(idx[0])} | {idkey(idx[1])}" if level == 2 else idkey(idx)
        out[key] = {c: row[c] for c in df.columns}
    return out


def placement(H, doc):
    p = {"class": type(H).__name__, "H.name": H.name}
    inc = H.incidences.to_dataframe
    p["incidence_columns (H.incidences.to_dataframe)"] = list(inc.columns)
    p["incidence_index_names"] = list(inc.index.names)
    p["incidences"] = frame_records(inc, 2)
    cells = {}
    for (e, n) in inc.index:
        cells[f"{idkey(e)} | {idkey(n)}"] = {
            "H.get_cell_properties(e, n)": H.get_cell_properties(e, n),
            "H.get_cell_properties(e, n, 'role')": H.get_cell_properties(e, n, "role"),
        }
    p["cell_accessors"] = cells
    nd = H.nodes.to_dataframe
    ed = H.edges.to_dataframe
    p["node_columns"] = list(nd.columns)
    p["nodes"] = frame_records(nd, 0)
    p["edge_columns"] = list(ed.columns)
    p["edges"] = frame_records(ed, 0)
    ps_nodes = set(H.nodes.property_store.properties.index)
    ps_edges = set(H.edges.property_store.properties.index)
    p["node_ids_in_property_store_but_not_in_H.nodes"] = sorted(map(idkey, ps_nodes - set(H.nodes)))
    p["edge_ids_in_property_store_but_not_in_H.edges"] = sorted(map(idkey, ps_edges - set(H.edges)))
    roles = roles_of(doc)
    hits = deep_find_strings(H, set(roles))
    p["role_strings_found_at"] = {r: sorted(set(hits.get(r, []))) for r in roles}
    md = doc.get("metadata") or {}
    mstr = {v for v in md.values() if isinstance(v, str)}
    mhits = deep_find_strings(H, mstr) if mstr else {}
    p["metadata_string_values_found_at"] = {v: sorted(set(mhits.get(v, []))) for v in mstr}
    p["constructor_args_kept_on_object"] = sorted(k for k in vars(H) if not k.startswith("_"))
    return p


def field_locations(H, doc, p):
    loc = {}
    roles = roles_of(doc)
    live = [r for r in roles if any("_E._property_store._data" in path for path in p["role_strings_found_at"][r])]
    loc["incidence.attrs (role)"] = (f"cell property store H.incidences.property_store (misc_properties): "
                                     f"{len(live)}/{len(roles)} role strings" if roles else "n/a")
    has_dir = any("direction" in r for r in doc.get("incidences", []))
    cols = p["incidence_columns (H.incidences.to_dataframe)"]
    loc["incidence.direction"] = (("cell property column 'direction'" if "direction" in cols else "dropped")
                                  if has_dir else "n/a")
    loc["incidence.weight"] = "cell property column 'weight' (default 1 when absent)"
    loc["node/edge attrs"] = "misc_properties column of H.nodes / H.edges property stores"
    loc["network-type"] = "not read (hif.py from_hif never looks at it)"
    md = doc.get("metadata") or {}
    loc["metadata"] = (("only 'name' -> H.name and 'default_attrs' are used; other keys: "
                        + ("not stored" if not any(p["metadata_string_values_found_at"].get(v)
                                                   for v in p["metadata_string_values_found_at"]) else
                           "found only in " + ", ".join(sorted({path.split('[')[0] for v in
                                                                 p['metadata_string_values_found_at'].values()
                                                                 for path in v}))))
                       if md else "n/a")
    return loc


def export(H, path, network_type):
    """to_hif with validation on; if it returns None, capture the unvalidated output as well."""
    res = {"api": f"hnx.to_hif(H, filename=..., network_type={network_type!r})"}
    out, err, ws = run(lambda: hnx.to_hif(H, filename=path, network_type=network_type))
    res.update(ok=(err is None and out is not None), returned=type(out).__name__, error=err, warnings=ws)
    doc = out
    if out is None and err is None:
        with validation_disabled():
            raw, err2, _ = run(lambda: hnx.to_hif(H, network_type=network_type))
        res["unvalidated_error"] = err2
        if raw is not None:
            raw_path = path.replace(".hif.json", ".unvalidated.hif.json")
            text = json.dumps(raw, indent=1, allow_nan=True, default=str)
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(text)
            res["unvalidated_output"] = os.path.relpath(raw_path, HERE)
            doc = json.loads(text)
            res["why_invalid (jsonschema on unvalidated output)"] = validate_hif(doc)
    elif out is not None:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        strict, why = is_strict_json_text(text)
        res["file_written"] = os.path.relpath(path, HERE)
        res["strict_json"] = strict if strict else why
        doc = json.loads(text)
        res["schema_errors (jsonschema)"] = validate_hif(doc)
    return res, doc


def probe_case(name, case):
    path = case_path(name)
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    rep = {"case": name, "description": case["description"], "input": os.path.relpath(path, HERE),
           "lib": "hypernetx", "lib_version": hnx.__version__}
    t0 = time.perf_counter()
    H, err, ws = run(lambda: hnx.from_hif(filename=path))
    rep["load"] = {"api": "hnx.from_hif(filename=path)", "ok": err is None and H is not None,
                   "returned": type(H).__name__, "error": err, "warnings": ws,
                   "seconds": round(time.perf_counter() - t0, 3)}
    if H is None:
        return rep
    rep["placement"] = placement(H, doc)
    rep["field_locations"] = field_locations(H, doc, rep["placement"])

    os.makedirs(LIB_OUT, exist_ok=True)
    nt = doc.get("network-type", "undirected")
    out_path = os.path.join(LIB_OUT, name + ".out.hif.json")
    rep["export"], out = export(H, out_path, nt)
    if nt != "undirected":
        rep["export_default_call"], out_def = export(H, os.path.join(LIB_OUT, name + ".out-default.hif.json"),
                                                     "undirected")
        rep["export_default_call"]["network-type written"] = (out_def or {}).get("network-type")
    if out is not None:
        rep["diff"] = diff_hif(doc, out)
    if rep["export"]["ok"]:
        H2, err, _ = run(lambda: hnx.from_hif(filename=out_path))
        rep["gen2"] = {"load_error": err, "load_returned": type(H2).__name__}
        if H2 is not None:
            rep["gen2"]["export"], out2 = export(H2, os.path.join(LIB_OUT, name + ".out2.hif.json"), nt)
            if out2 is not None:
                d12 = diff_hif(out, out2)
                rep["gen2"]["diff_gen1_gen2_summary"] = d12["summary"]
                rep["gen2"]["diff_input_gen2_summary"] = diff_hif(doc, out2)["summary"]
                rep["gen2"]["gen2_incidence_columns"] = list(H2.incidences.to_dataframe.columns)
    return rep


# --------------------------------------------------------------------------------------------
# Offline behaviour
# --------------------------------------------------------------------------------------------

def run_offline():
    doc = json.load(open(case_path("c00-sample-directed"), encoding="utf-8"))
    res = {}
    with network_disabled():
        _, err, _ = run(lambda: hnx.from_hif(hif=doc))
        res["hnx.from_hif(hif=doc) with network disabled"] = err
    H = hnx.from_hif(hif=doc)
    with network_disabled():
        _, err, _ = run(lambda: hnx.to_hif(H))
        res["hnx.to_hif(H) with network disabled"] = err
    # the public constructor does not touch the network
    with network_disabled():
        df = pd.DataFrame(doc["incidences"])
        H3, err, _ = run(lambda: hnx.Hypergraph(df, edge_col="edge", node_col="node", cell_weight_col="weight",
                                                misc_cell_properties_col="attrs"))
        res["hnx.Hypergraph(DataFrame(incidences), ...) with network disabled"] = (
            err or {"ok": True, "role of (f1, drug:metformin)": H3.get_cell_properties("f1", "drug:metformin", "role")})
    # time one networked call
    t0 = time.perf_counter()
    hnx.from_hif(hif=doc)
    res["seconds for one networked from_hif(hif=sample)"] = round(time.perf_counter() - t0, 3)
    t0 = time.perf_counter()
    for _ in range(3):
        hnx_hif.requests.get(hnx_hif.schema_url)
    res["seconds per schema GET (mean of 3)"] = round((time.perf_counter() - t0) / 3, 3)
    res["schema_url"] = hnx_hif.schema_url
    # a fresh interpreter whose proxy variables point at a closed local port: can hypernetx be imported,
    # and what does from_hif do? (issue #171 reports a failure at import time)
    import subprocess
    code = ("import time; t = time.perf_counter()\n"
            "import warnings; warnings.filterwarnings('ignore')\n"
            "import hypernetx as hnx\n"
            "print('import ok', round(time.perf_counter() - t, 2), 's')\n"
            "try:\n"
            "    hnx.from_hif(hif={'incidences': [{'edge': 'e', 'node': 'n'}]})\n"
            "    print('from_hif returned')\n"
            "except Exception as e:\n"
            "    print('from_hif raised', type(e).__name__)\n")
    env = dict(os.environ)
    for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        env[k] = "http://127.0.0.1:9"
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env, timeout=300)
    res["fresh interpreter, proxy variables -> 127.0.0.1:9 (closed)"] = {
        "returncode": p.returncode, "stdout": p.stdout.decode().strip().splitlines(),
        "stderr_tail": p.stderr.decode().strip().splitlines()[-1:] if p.returncode else []}
    return res


# --------------------------------------------------------------------------------------------
# Native operations
# --------------------------------------------------------------------------------------------

def cells(H):
    df = H.incidences.to_dataframe
    out = {}
    for (e, n), row in df.iterrows():
        mp = row["misc_properties"] if isinstance(row["misc_properties"], dict) else {}
        out[f"{idkey(e)} | {idkey(n)}"] = {"role": mp.get("role", ABSENT),
                                           "direction": row["direction"] if "direction" in df.columns else ABSENT,
                                           "weight": row["weight"]}
    return out


def objs(view):
    df = view.to_dataframe
    return {idkey(i): (row["misc_properties"] if isinstance(row["misc_properties"], dict) else {})
            for i, row in df.iterrows()}


def snapshot(H):
    return {"cells": cells(H), "nodes": objs(H.nodes), "edges": objs(H.edges), "name": H.name}


def compare(before, after):
    res = {"cells_compared": 0, "role_same": 0, "direction_same": 0, "cells_lost": [], "cells_new": [],
           "role_changed": {}, "direction_changed": {}}
    for k, v in before["cells"].items():
        if k not in after["cells"]:
            res["cells_lost"].append(k)
            continue
        res["cells_compared"] += 1
        a = after["cells"][k]
        if jsonable(a["role"]) == jsonable(v["role"]):
            res["role_same"] += 1
        else:
            res["role_changed"][k] = {"before": v["role"], "after": a["role"]}
        if jsonable(a["direction"]) == jsonable(v["direction"]):
            res["direction_same"] += 1
        else:
            res["direction_changed"][k] = {"before": v["direction"], "after": a["direction"]}
    res["cells_new"] = sorted(set(after["cells"]) - set(before["cells"]))
    res["cells_new_detail"] = {k: after["cells"][k] for k in res["cells_new"][:6]}
    for kind in ("nodes", "edges"):
        same = sum(1 for k, v in before[kind].items() if k in after[kind] and
                   json.dumps(jsonable(after[kind][k]), sort_keys=True) == json.dumps(jsonable(v), sort_keys=True))
        res[f"{kind}_attrs_same"] = f"{same}/{sum(1 for k in before[kind] if k in after[kind])} surviving"
        res[f"{kind}_missing"] = sorted(set(before[kind]) - set(after[kind]))[:10]
        res[f"{kind}_new"] = sorted(set(after[kind]) - set(before[kind]))[:10]
    res["name_after"] = after["name"]
    return res


def op_report(label, base_snap, fn, doc, nt="directed"):
    res, err, ws = run(fn)
    r = {"op": label, "ok": err is None, "error": err, "warnings": ws}
    if err is not None or res is None:
        return r
    r["returned"] = type(res).__name__
    r["compare"] = compare(base_snap, snapshot(res))
    path = os.path.join(LIB_OUT, "ops", re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("_")[:80] + ".out.hif.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r["export"], out = export(res, path, nt)
    if out is not None:
        r["export_summary_vs_input"] = diff_hif(doc, out)["summary"]
    return r


def run_ops():
    ops = []
    name = "c00-sample-directed"
    doc = json.load(open(case_path(name), encoding="utf-8"))

    def fresh():
        return hnx.from_hif(hif=copy.deepcopy(doc))
    base = snapshot(fresh())
    ops.append(op_report("H.clone()", base, lambda: fresh().clone(), doc))
    ops.append(op_report("H.restrict_to_nodes([metformin, T2DM, insulin])", base,
                         lambda: fresh().restrict_to_nodes(["drug:metformin", "disease:T2DM", "drug:insulin"]), doc))
    ops.append(op_report("H.restrict_to_edges([f1, f3])", base, lambda: fresh().restrict_to_edges(["f1", "f3"]), doc))

    def add_inc():
        H = fresh()
        return H.add_incidence("f1", "pop:children", role="population")
    ops.append(op_report("H.add_incidence('f1', 'pop:children', role='population')", base, add_inc, doc))

    def add_inc_dir():
        H = fresh()
        return H.add_incidence("f1", "pop:children", role="population", direction="tail")
    ops.append(op_report("H.add_incidence('f1', 'pop:children', role=..., direction='tail')", base, add_inc_dir, doc))

    def add_edge():
        H = fresh()
        return H.add_edge("f4", relation="new-fact")
    ops.append(op_report("H.add_edge('f4', relation=...) (no incidences)", base, add_edge, doc))

    def add_node():
        H = fresh()
        return H.add_node("drug:new", type="Drug")
    ops.append(op_report("H.add_node('drug:new', type=...) (no incidences)", base, add_node, doc))

    def rm_nodes():
        H = fresh()
        return H.remove_nodes("dose:500mg-bid")
    ops.append(op_report("H.remove_nodes('dose:500mg-bid')", base, rm_nodes, doc))

    def rm_edges():
        H = fresh()
        return H.remove_edges("f2")
    ops.append(op_report("H.remove_edges('f2')", base, rm_edges, doc))

    def rm_inc():
        H = fresh()
        return H.remove_incidences(("f1", "dose:500mg-bid"))
    ops.append(op_report("H.remove_incidences(('f1', 'dose:500mg-bid'))", base, rm_inc, doc))
    ops.append(op_report("H.dual()", base, lambda: fresh().dual(), doc))
    ops.append(op_report("H.collapse_nodes()", base, lambda: fresh().collapse_nodes(), doc))
    ops.append(op_report("H.collapse_nodes_and_edges()", base, lambda: fresh().collapse_nodes_and_edges(), doc))

    def collapse_edges():
        d = copy.deepcopy(doc)
        d["edges"].append({"edge": "f1-copy", "attrs": {"relation": "treats-duplicate"}})
        for r in [r for r in doc["incidences"] if r["edge"] == "f1"]:
            r2 = copy.deepcopy(r)
            r2["edge"] = "f1-copy"
            r2["attrs"]["role"] = r2["attrs"]["role"] + "-in-copy"
            d["incidences"].append(r2)
        return hnx.from_hif(hif=d).collapse_edges()
    ops.append(op_report("H.collapse_edges() after adding f1-copy (same members, different roles)", base,
                         collapse_edges, doc))
    ops.append(op_report("H.rename(nodes={'drug:metformin': 'drug:MET'})", base,
                         lambda: fresh().rename(nodes={"drug:metformin": "drug:MET"}, inplace=False), doc))

    def summ():
        H2 = hnx.from_hif(hif={"network-type": "directed", "incidences": [
            {"edge": "f1", "node": "drug:metformin", "direction": "head", "attrs": {"role": "OTHER-ROLE"}},
            {"edge": "f9", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "agent"}}]})
        return fresh().sum(H2)
    ops.append(op_report("H.sum(H2) where H2 has (f1, metformin) with another role", base, summ, doc))

    def set_cell():
        H = fresh()
        H.incidences[("f1", "drug:metformin")].role = "primary-treatment"
        return H
    ops.append(op_report("H.incidences[(e, n)].role = 'primary-treatment'", base, set_cell, doc))

    # duplicates: what does from_hif keep for two records of one (edge, node) pair?
    d5 = json.load(open(case_path("c05-two-roles-same-direction"), encoding="utf-8"))
    H5 = hnx.from_hif(hif=d5)
    ops.append({"op": "from_hif(c05): which of two records for (t1, drug:metformin) is kept",
                "cells": cells(H5)})
    # does the constructor's aggregate_by do anything for duplicate (edge, node) rows?
    df = pd.DataFrame([{"edge": "t1", "node": "m", "weight": 0.7, "attrs": {"role": "intervention"}},
                       {"edge": "t1", "node": "m", "weight": 0.3, "attrs": {"role": "background-therapy"}},
                       {"edge": "t1", "node": "i", "weight": 1.0, "attrs": {"role": "comparator"}}])
    for agg in ("first", {"weight": "sum"}):
        Hd, err, _ = run(lambda: hnx.Hypergraph(df, edge_col="edge", node_col="node", cell_weight_col="weight",
                                                misc_cell_properties_col="attrs", aggregate_by=agg))
        ops.append({"op": f"hnx.Hypergraph(df with a duplicate (edge, node) row, aggregate_by={agg!r})",
                    "error": err, "cells": cells(Hd) if Hd is not None else None})
    return ops


def main():
    os.makedirs(LIB_OUT, exist_ok=True)
    env = env_info(("hypernetx",))
    import locale
    env["preferred_encoding"] = locale.getpreferredencoding(False)
    env["schema_url"] = hnx_hif.schema_url
    env["source_sha256"] = {p: sha256_file(os.path.join(SITE, p)) for p in (
        "hypernetx/hif.py", "hypernetx/classes/hypergraph.py", "hypernetx/classes/factory.py",
        "hypernetx/classes/property_store.py", "hypernetx/classes/hyp_view.py",
        "hypernetx/classes/incidence_store.py")}
    summary = {"env": env, "cases": {}}
    for name, case in build_cases().items():
        rep = probe_case(name, case)
        dump(rep, os.path.join(LIB_OUT, name + ".json"))
        s = {"load": ("ok" if rep["load"]["ok"] else
                      f"returned {rep['load']['returned']}" + (f"; ERROR {rep['load']['error']['type']}: "
                                                               f"{rep['load']['error']['message'][:80]} @ "
                                                               f"{rep['load']['error']['raised_at']}"
                                                               if rep['load']['error'] else ""))}
        if "export" in rep:
            e = rep["export"]
            s["export"] = ("ok" if e["ok"] else f"returned {e['returned']}" +
                           (f"; ERROR {e['error']}" if e.get("error") else "") +
                           (f"; schema errors on unvalidated output: {e.get('why_invalid (jsonschema on unvalidated output)')}"
                            if e.get("unvalidated_output") else ""))
        if "export_default_call" in rep:
            s["export_default_call_network_type"] = rep["export_default_call"].get("network-type written")
            s["export_default_call_ok"] = rep["export_default_call"]["ok"]
        if "diff" in rep:
            s["diff"] = rep["diff"]["summary"]
        if "field_locations" in rep:
            s["field_locations"] = rep["field_locations"]
        if "gen2" in rep:
            g = rep["gen2"]
            s["gen2"] = {"export_ok": (g.get("export") or {}).get("ok"),
                         "gen1_vs_gen2": g.get("diff_gen1_gen2_summary"),
                         "input_vs_gen2_roles": (g.get("diff_input_gen2_summary") or {}).get("role_records_kept"),
                         "input_vs_gen2_direction": (g.get("diff_input_gen2_summary") or {}).get("direction_records_kept")}
        summary["cases"][name] = s
        d = s.get("diff", {})
        print(f"{name:42s} load={s['load'][:40]:40s} export={s.get('export', '-')[:30]:30s} "
              f"roles={d.get('role_records_kept')} dir={d.get('direction_records_kept')}")
    dump(summary, os.path.join(OUT_DIR, "hnx-summary.json"))
    off = run_offline()
    dump({"env": env, "offline": off}, os.path.join(OUT_DIR, "hnx-offline.json"))
    print(json.dumps(jsonable(off), indent=1)[:1500])
    ops = run_ops()
    dump({"env": env, "ops": ops}, os.path.join(OUT_DIR, "hnx-ops.json"))
    for o in ops:
        print(f"OP {o['op'][:75]:75s} ok={o.get('ok', '-')} export={(o.get('export') or {}).get('ok')}")


if __name__ == "__main__":
    main()
