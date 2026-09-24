#!/usr/bin/env python3
"""Shared cases, structural HIF diff and helpers for the XGI / HyperNetX HIF probes (P2, 2026-09-23).

Nothing in here imports XGI or HyperNetX. The probe scripts (`probe_xgi.py`, `probe_hnx.py`,
`probe_rolepreserving.py`) import this module.

    python probe_common.py            # (re)writes lib-cases/*.hif.json from build_cases()

The diff compares two HIF documents *structurally*:

* ids are compared with their JSON type (the integer 1 and the string "1" are different ids);
* incidences are grouped by (edge, node) and compared as multisets, so two records for the same
  pair (a node playing two roles in one edge) are counted separately;
* `attrs: {}` and a missing `attrs` are treated as the same thing (HIF makes attrs optional);
  a missing `weight` and `weight: 1` are *not* treated as the same thing (HIF defines no default).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import platform
import sys
from collections import Counter, OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SAMPLE = os.path.join(REPO, "schemas", "sample.hif.json")
CASES_DIR = os.path.join(HERE, "lib-cases")
OUT_DIR = os.path.join(HERE, "out")
HIF_SCHEMA = os.path.join(HERE, "hif-schema", "hif_schema.json")  # vendored, see hif-schema/README.md

ABSENT = "<absent>"  # marker for "field not present" in comparisons and reports


# --------------------------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------------------------

def _sample():
    with open(SAMPLE, encoding="utf-8") as f:
        return json.load(f)


def _strip_direction(doc):
    d = copy.deepcopy(doc)
    for r in d["incidences"]:
        r.pop("direction", None)
    return d


def _mini(network_type="directed", **extra):
    """A small role-labelled directed fact used as the base of several cases."""
    doc = {
        "network-type": network_type,
        "metadata": {"title": "mini"},
        "nodes": [
            {"node": "drug:metformin", "attrs": {"type": "Drug"}},
            {"node": "disease:T2DM", "attrs": {"type": "Disease"}},
        ],
        "edges": [{"edge": "f1", "attrs": {"relation": "treats"}}],
        "incidences": [
            {"edge": "f1", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "treatment"}},
            {"edge": "f1", "node": "disease:T2DM", "direction": "head", "attrs": {"role": "condition"}},
        ],
    }
    if network_type != "directed":
        doc = _strip_direction(doc)
    doc.update(extra)
    return doc


def build_cases():
    """Return an ordered mapping name -> {description, doc, strict_json}."""
    cases = OrderedDict()

    def add(name, description, doc, strict_json=True):
        cases[name] = {"description": description, "doc": doc, "strict_json": strict_json}

    s = _sample()
    add("c00-sample-directed",
        "schemas/sample.hif.json verbatim: directed, 8 nodes with attrs, 3 weighted edges with attrs, "
        "9 role-labelled incidences with direction, nested metadata", s)

    d = _strip_direction(s)
    d["network-type"] = "undirected"
    add("c01-sample-undirected", "the sample with network-type undirected and every direction field removed", d)

    d = copy.deepcopy(s)
    d["network-type"] = "undirected"
    add("c02-undirected-with-direction", "the sample with network-type undirected but direction fields kept", d)

    d = copy.deepcopy(s)
    del d["network-type"]
    add("c03-no-network-type", "the sample with the network-type key removed (direction fields kept)", d)

    d = _strip_direction(s)
    d["network-type"] = "asc"
    add("c04-asc", "the sample declared as an abstract simplicial complex (network-type asc), direction removed", d)

    add("c05-two-roles-same-direction",
        "one node plays two roles in one directed edge, both on the tail: two incidence records for "
        "the same (edge, node) pair with different roles and different incidence weights",
        {
            "network-type": "directed",
            "nodes": [{"node": "drug:metformin"}, {"node": "drug:insulin"}, {"node": "outcome:HbA1c"}],
            "edges": [{"edge": "t1", "attrs": {"relation": "compared-in-trial"}}],
            "incidences": [
                {"edge": "t1", "node": "drug:metformin", "direction": "tail", "weight": 0.7,
                 "attrs": {"role": "intervention"}},
                {"edge": "t1", "node": "drug:metformin", "direction": "tail", "weight": 0.3,
                 "attrs": {"role": "background-therapy"}},
                {"edge": "t1", "node": "drug:insulin", "direction": "tail", "attrs": {"role": "comparator"}},
                {"edge": "t1", "node": "outcome:HbA1c", "direction": "head", "attrs": {"role": "outcome"}},
            ],
        })

    add("c06-two-roles-different-direction",
        "one node plays two roles in one directed edge, once on the tail (regulator) and once on the "
        "head (target): gene autoregulation",
        {
            "network-type": "directed",
            "edges": [{"edge": "r1", "attrs": {"relation": "regulates"}}],
            "incidences": [
                {"edge": "r1", "node": "gene:TP53", "direction": "tail", "attrs": {"role": "regulator"}},
                {"edge": "r1", "node": "gene:TP53", "direction": "head", "attrs": {"role": "target"}},
                {"edge": "r1", "node": "cell:HeLa", "direction": "tail", "attrs": {"role": "context"}},
            ],
        })

    d = _strip_direction(cases["c05-two-roles-same-direction"]["doc"])
    d["network-type"] = "undirected"
    add("c07-two-roles-undirected", "c05 in an undirected network (no direction fields)", d)

    d = _mini()
    d["nodes"] += [{"node": "iso:with-attrs", "attrs": {"type": "Orphan"}}, {"node": "iso:bare"}]
    add("c08-isolated-nodes", "two declared nodes that occur in no incidence, one with attrs and one without", d)

    d = _mini()
    d["edges"] += [{"edge": "e:empty-with-attrs", "attrs": {"relation": "retracted-fact"}}, {"edge": "e:empty-bare"}]
    add("c09-empty-edges", "two declared edges that have no incidences, one with attrs and one without", d)

    add("c10-nested-fact",
        "a nested fact: edge id f1 is also used as a node id, a participant of edge m1 (an assertion about f1)",
        {
            "network-type": "directed",
            "nodes": [
                {"node": "f1", "attrs": {"type": "Statement"}},
                {"node": "org:ADA", "attrs": {"type": "Organisation"}},
            ],
            "edges": [
                {"edge": "f1", "attrs": {"relation": "treats"}},
                {"edge": "m1", "attrs": {"relation": "asserts"}},
            ],
            "incidences": [
                {"edge": "f1", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "treatment"}},
                {"edge": "f1", "node": "disease:T2DM", "direction": "head", "attrs": {"role": "condition"}},
                {"edge": "m1", "node": "org:ADA", "direction": "tail", "attrs": {"role": "asserter"}},
                {"edge": "m1", "node": "f1", "direction": "head", "attrs": {"role": "statement"}},
            ],
        })

    add("c11-integer-ids",
        "integer node and edge ids; edge id 0 equals node id 0",
        {
            "network-type": "directed",
            "nodes": [{"node": i, "attrs": {"label": f"n{i}"}} for i in range(4)],
            "edges": [{"edge": 0, "attrs": {"relation": "r0"}}, {"edge": 1, "attrs": {"relation": "r1"}}],
            "incidences": [
                {"edge": 0, "node": 0, "direction": "tail", "attrs": {"role": "agent"}},
                {"edge": 0, "node": 1, "direction": "head", "attrs": {"role": "patient"}},
                {"edge": 1, "node": 2, "direction": "tail", "attrs": {"role": "agent"}},
                {"edge": 1, "node": 3, "direction": "head", "attrs": {"role": "patient"}},
            ],
        })

    add("c12-mixed-int-str-ids",
        "the integer 1 and the string \"1\" used as two different node ids, and as two different edge ids",
        {
            "network-type": "undirected",
            "nodes": [{"node": 1, "attrs": {"kind": "int"}}, {"node": "1", "attrs": {"kind": "str"}}],
            "edges": [{"edge": 1, "attrs": {"kind": "int"}}, {"edge": "1", "attrs": {"kind": "str"}}],
            "incidences": [
                {"edge": 1, "node": 1, "attrs": {"role": "int-in-int"}},
                {"edge": 1, "node": "1", "attrs": {"role": "str-in-int"}},
                {"edge": "1", "node": 1, "attrs": {"role": "int-in-str"}},
                {"edge": "1", "node": "x", "attrs": {"role": "x-in-str"}},
            ],
        })

    add("c13-unicode-ids",
        "non-ASCII node, edge and role strings; NFC and NFD spellings of 'e-acute' as two distinct nodes",
        {
            "network-type": "directed",
            "nodes": [
                {"node": "药物:二甲双胍", "attrs": {"label": "métformine"}},
                {"node": "é", "attrs": {"form": "NFC"}},
                {"node": "é", "attrs": {"form": "NFD"}},
            ],
            "edges": [{"edge": "事实-1", "attrs": {"relation": "traite"}}],
            "incidences": [
                {"edge": "事实-1", "node": "药物:二甲双胍", "direction": "tail", "attrs": {"role": "治疗"}},
                {"edge": "事实-1", "node": "maladie:diabète type 2", "direction": "head", "attrs": {"role": "état"}},
                {"edge": "事实-1", "node": "🧪 sample #42", "direction": "tail", "attrs": {"role": "échantillon"}},
                {"edge": "事实-1", "node": "é", "direction": "tail", "attrs": {"role": "nfc"}},
                {"edge": "事实-1", "node": "é", "direction": "tail", "attrs": {"role": "nfd"}},
            ],
        })

    d = _mini()
    d["incidences"].append({"edge": "f1", "node": "pop:adults", "attrs": {"role": "population"}})
    add("c14-directed-missing-direction",
        "network-type directed but one incidence has no direction field (schema-valid)", d)

    d = _mini()
    d["incidences"] = [
        {"edge": "f1", "node": "drug:metformin", "direction": "tail", "attrs": {"role": "treatment"}},
        {"edge": "f1", "node": "disease:T2DM", "direction": "head", "attrs": {}},
        {"edge": "f1", "node": "pop:adults", "direction": "tail"},
    ]
    add("c15-incidence-attrs-absent-or-empty",
        "incidences with attrs {role}, with attrs {} and with no attrs key", d)

    shapes = {
        "evidence": ["pmid:1", "pmid:2"],
        "qualifiers": {"since": "2020", "certainty": 0.9, "nested": {"deep": [1, {"x": None}]}},
        "note": None,
        "flag": True,
        "label": "Überprüfung – 検証",
        "empty_list": [],
        "empty_obj": {},
        "big": 9007199254740993,
        "tiny": 1e-300,
        "zero": 0,
    }
    d = _mini()
    d["metadata"] = {"title": "attr shapes", **copy.deepcopy(shapes)}
    for r in d["nodes"] + d["edges"]:
        r["attrs"].update(copy.deepcopy(shapes))
    for r in d["incidences"]:
        r["attrs"].update(copy.deepcopy(shapes))
    add("c16-attr-value-shapes",
        "attrs (on nodes, edges, incidences and metadata) holding lists, nested dicts, null, booleans, "
        "non-ASCII text, empty list/object, an integer above 2^53 and a tiny float", d)

    d = _mini()
    for r in d["nodes"]:
        r["weight"] = 2.5
    for r in d["edges"]:
        r["weight"] = 0.5
    d["incidences"][0]["weight"] = 0.25
    d["incidences"][1]["weight"] = 0.75
    add("c17-weights-everywhere", "record-level weight on nodes, edges and incidences", d)

    d = _mini()
    d["nodes"][0]["attrs"]["weight"] = 7
    d["edges"][0]["attrs"]["weight"] = 9
    d["incidences"][0]["attrs"]["weight"] = 5
    add("c18-weight-key-inside-attrs",
        "no record-level weight anywhere, but a key named 'weight' inside node, edge and incidence attrs", d)

    add("c19-duplicate-node-edge-records",
        "node n1 and edge e1 each declared twice with different attrs (upstream calls this HIF-compliant)",
        {
            "network-type": "undirected",
            "nodes": [
                {"node": "n1", "attrs": {"label": "first", "a": 1}},
                {"node": "n1", "attrs": {"label": "second", "b": 2}},
            ],
            "edges": [
                {"edge": "e1", "attrs": {"relation": "r-first"}},
                {"edge": "e1", "attrs": {"relation": "r-second", "c": 3}},
            ],
            "incidences": [
                {"edge": "e1", "node": "n1", "attrs": {"role": "subject"}},
                {"edge": "e1", "node": "n2", "attrs": {"role": "object"}},
            ],
        })

    d = _mini()
    d["metadata"] = {
        "title": "reserved keys",
        "name": "kb-sample",
        "default_attrs": {"incidences": {"weight": 1, "attrs": {}, "role": "participant"}},
    }
    d["incidences"].append({"edge": "f1", "node": "pop:adults", "direction": "tail", "attrs": {"note": "no role"}})
    add("c20-hnx-reserved-metadata-keys",
        "metadata carries the keys HyperNetX interprets (name, default_attrs with a default 'role'); "
        "one incidence has no role", d)

    d = _mini()
    d["nodes"].append({"node": "iso:shadow", "attrs": {"node": "shadow-value"}})
    add("c21-node-attr-key-equals-python-parameter",
        "an isolated node whose attrs contain the key 'node' (the name of the XGI add_node parameter)", d)

    d = _mini()
    d["nodes"][0]["attrs"]["score"] = float("nan")
    d["incidences"][0]["attrs"]["score"] = float("nan")
    add("c22-nan-in-attrs", "a NaN value in node and incidence attrs (not strict JSON; Python's json accepts it)",
        d, strict_json=False)

    add("c23-big-int-ids",
        "integer ids at and beyond 2^53 and 2^63",
        {
            "network-type": "undirected",
            "incidences": [
                {"edge": 9223372036854775807, "node": 9007199254740993, "attrs": {"role": "a"}},
                {"edge": 9223372036854775807, "node": 18446744073709551621, "attrs": {"role": "b"}},
                {"edge": 9223372036854775808, "node": 9007199254740993, "attrs": {"role": "c"}},
            ],
        })

    add("c24-empty-incidences", "the smallest valid HIF document: incidences is an empty array",
        {"incidences": []})

    d = _mini()
    d["edges"].append({"edge": "e:shadow", "attrs": {"members": ["x"], "idx": 3}})
    add("c26-edge-attr-key-equals-python-parameter",
        "an empty edge whose attrs contain the keys 'members' and 'idx' (XGI add_edge parameter names)", d)

    add("c25-plain-no-attrs", "an undirected hypergraph with no attrs, weights, nodes or edges arrays",
        {
            "network-type": "undirected",
            "incidences": [
                {"edge": "e1", "node": "a"}, {"edge": "e1", "node": "b"},
                {"edge": "e2", "node": "b"}, {"edge": "e2", "node": "c"},
            ],
        })
    return cases


def case_path(name):
    """Path the probes read. c00 is read from schemas/sample.hif.json itself, not from a copy."""
    if name == "c00-sample-directed":
        return SAMPLE
    return os.path.join(CASES_DIR, name + ".hif.json")


def write_cases():
    os.makedirs(CASES_DIR, exist_ok=True)
    for name, c in build_cases().items():
        if name == "c00-sample-directed":
            continue  # read in place from schemas/sample.hif.json
        with open(case_path(name), "w", encoding="utf-8") as f:
            json.dump(c["doc"], f, ensure_ascii=False, indent=1, allow_nan=True)
            f.write("\n")
    with open(os.path.join(CASES_DIR, "INDEX.json"), "w", encoding="utf-8") as f:
        json.dump({n: {"description": c["description"], "strict_json": c["strict_json"]}
                   for n, c in build_cases().items()}, f, ensure_ascii=False, indent=1)
        f.write("\n")


def load_case(name):
    with open(case_path(name), encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------------------------
# JSON helpers
# --------------------------------------------------------------------------------------------

def jsonable(x, _depth=0):
    """Convert library objects into something json.dumps can write without losing the point."""
    if _depth > 50:
        return repr(x)
    try:
        import numpy as np  # noqa: F401
        if isinstance(x, np.generic):
            x = x.item()
        elif isinstance(x, np.ndarray):
            x = x.tolist()
    except ImportError:
        pass
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return f"<float {x}>"
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    if isinstance(x, dict):
        return {(k if isinstance(k, str) else f"<{type(k).__name__}> {k!r}"): jsonable(v, _depth + 1)
                for k, v in x.items()}
    if isinstance(x, (set, frozenset)):
        return {"<set>": sorted((jsonable(v, _depth + 1) for v in x), key=lambda v: json.dumps(v, default=str))}
    if isinstance(x, tuple):
        return {"<tuple>": [jsonable(v, _depth + 1) for v in x]}
    if isinstance(x, list):
        return [jsonable(v, _depth + 1) for v in x]
    return f"<{type(x).__name__}> {x!r}"


def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jsonable(obj), f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")


def canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, allow_nan=True, default=repr)


def is_strict_json_text(text):
    """True if the text parses without NaN/Infinity constants."""
    def bad(c):
        raise ValueError(f"non-standard JSON constant {c}")
    try:
        json.loads(text, parse_constant=bad)
        return True, None
    except ValueError as e:
        return False, str(e)


def validate_hif(doc):
    """Validate against the vendored HIF schema with jsonschema (Draft 7). Returns list of messages."""
    import jsonschema
    with open(HIF_SCHEMA, encoding="utf-8") as f:
        schema = json.load(f)
    v = jsonschema.Draft7Validator(schema)
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in v.iter_errors(doc)][:10]


def env_info(extra_modules=()):
    info = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    from importlib import metadata
    for m in ("jsonschema", "pandas", "numpy", "fastjsonschema", "requests") + tuple(extra_modules):
        try:
            info[m] = metadata.version(m)
        except Exception as e:  # pragma: no cover
            info[m] = f"not installed: {e}"
    return info


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# --------------------------------------------------------------------------------------------
# Structural diff
# --------------------------------------------------------------------------------------------

def idkey(x):
    return f"{type(x).__name__}:{x}"


def _attrs(r):
    a = r.get("attrs", ABSENT)
    if a == {}:
        return ABSENT
    return a


def _role(r):
    a = r.get("attrs")
    if isinstance(a, dict) and "role" in a:
        return a["role"]
    return ABSENT


def _cmp(vin, vout):
    """Compare two lists of values as multisets."""
    cin, cout = Counter(canon(v) for v in vin), Counter(canon(v) for v in vout)
    if cin == cout:
        return "preserved"
    absent = canon(ABSENT)
    if cout and all(k == absent for k in cout) and any(k != absent for k in cin):
        return "lost"
    if cin and all(k == absent for k in cin) and any(k != absent for k in cout):
        return "added"
    if sum(cout.values()) < sum(cin.values()) and not (cout - cin):
        return "partial"
    return "altered"


def index_doc(doc):
    nodes, edges, inc = defaultdict(list), defaultdict(list), defaultdict(list)
    ids = {}
    for r in doc.get("nodes", []) or []:
        nodes[idkey(r.get("node"))].append(r)
        ids[idkey(r.get("node"))] = r.get("node")
    for r in doc.get("edges", []) or []:
        edges[idkey(r.get("edge"))].append(r)
        ids[idkey(r.get("edge"))] = r.get("edge")
    for r in doc.get("incidences", []) or []:
        inc[(idkey(r.get("edge")), idkey(r.get("node")))].append(r)
        ids[idkey(r.get("edge"))] = r.get("edge")
        ids[idkey(r.get("node"))] = r.get("node")
    inodes = {idkey(r.get("node")) for r in doc.get("incidences", []) or []}
    iedges = {idkey(r.get("edge")) for r in doc.get("incidences", []) or []}
    return nodes, edges, inc, inodes, iedges, ids


def _count_triples(inc_in, inc_out, field):
    """How many input incidence records keep (edge, node, <field>) in the output (multiset)."""
    kept = total = 0
    for key, rin in inc_in.items():
        vin = [field(r) for r in rin]
        vin = [v for v in vin if v != ABSENT]
        total += len(vin)
        vout = [field(r) for r in inc_out.get(key, [])]
        c = Counter(canon(v) for v in vin) & Counter(canon(v) for v in vout)
        kept += sum(c.values())
    return kept, total


def diff_hif(inp, out):
    """Structural diff of two HIF documents. Returns a JSON-able dict."""
    if out is None:
        return {"output": None}
    n_in, e_in, i_in, inodes_in, iedges_in, ids_in = index_doc(inp)
    n_out, e_out, i_out, inodes_out, iedges_out, ids_out = index_doc(out)

    res = OrderedDict()

    # top level
    top = OrderedDict()
    top["network-type"] = {"in": inp.get("network-type", ABSENT), "out": out.get("network-type", ABSENT)}
    top["network-type"]["status"] = _cmp([top["network-type"]["in"]], [top["network-type"]["out"]])
    min_, mout = inp.get("metadata", {}) or {}, out.get("metadata", {}) or {}
    top["metadata"] = {
        "keys_lost": sorted(set(min_) - set(mout)),
        "keys_added": sorted(set(mout) - set(min_)),
        "keys_changed": sorted(k for k in set(min_) & set(mout) if canon(min_[k]) != canon(mout[k])),
    }
    top["metadata"]["status"] = ("preserved" if not any(top["metadata"].values()) else
                                 "lost" if min_ and set(min_) - set(mout) == set(min_) else "altered")
    top["other_top_level_keys_out"] = sorted(set(out) - {"network-type", "metadata", "nodes", "edges", "incidences"})
    res["top"] = top

    # incidences
    pairs = OrderedDict()
    for key in list(i_in) + [k for k in i_out if k not in i_in]:
        rin, rout = i_in.get(key, []), i_out.get(key, [])
        p = OrderedDict(edge=key[0], node=key[1], count_in=len(rin), count_out=len(rout))
        if not rout:
            p["status"] = "lost"
        elif not rin:
            p["status"] = "new"
        else:
            p["role"] = _cmp([_role(r) for r in rin], [_role(r) for r in rout])
            p["direction"] = _cmp([r.get("direction", ABSENT) for r in rin], [r.get("direction", ABSENT) for r in rout])
            p["weight"] = _cmp([r.get("weight", ABSENT) for r in rin], [r.get("weight", ABSENT) for r in rout])
            p["attrs"] = _cmp([_attrs(r) for r in rin], [_attrs(r) for r in rout])
            if p["count_out"] != p["count_in"]:
                p["status"] = "count-changed"
            else:
                p["status"] = "present"
        p["roles_in"] = [_role(r) for r in rin]
        p["roles_out"] = [_role(r) for r in rout]
        p["directions_in"] = [r.get("direction", ABSENT) for r in rin]
        p["directions_out"] = [r.get("direction", ABSENT) for r in rout]
        p["weights_in"] = [r.get("weight", ABSENT) for r in rin]
        p["weights_out"] = [r.get("weight", ABSENT) for r in rout]
        if any(_attrs(r) != ABSENT for r in rin + rout):
            p["attrs_in"] = [_attrs(r) for r in rin]
            p["attrs_out"] = [_attrs(r) for r in rout]
        pairs[f"{key[0]} | {key[1]}"] = p
    res["incidences"] = pairs

    # nodes and edges (declared records, plus presence via incidences)
    def objects(decl_in, decl_out, implied_in, implied_out):
        objs = OrderedDict()
        for k in list(decl_in) + [k for k in implied_in if k not in decl_in]:
            rin, rout = decl_in.get(k, []), decl_out.get(k, [])
            o = OrderedDict(declared_in=len(rin), declared_out=len(rout),
                            present_out=(k in decl_out or k in implied_out))
            o["attrs"] = _cmp([_attrs(r) for r in rin] or [ABSENT], [_attrs(r) for r in rout] or [ABSENT])
            if len(rin) > 1 and len(rout) == 1:
                merged = {}
                for r in rin:
                    merged.update(r.get("attrs") or {})
                outa = rout[0].get("attrs") or {}
                o["attrs"] = ("merged: later declarations update earlier ones" if canon(outa) == canon(merged)
                              else "first declaration kept" if canon(outa) == canon(rin[0].get("attrs") or {})
                              else "last declaration kept" if canon(outa) == canon(rin[-1].get("attrs") or {})
                              else "altered")
            win = {canon(r["weight"]) for r in rin if "weight" in r}
            wout = {canon(r["weight"]) for r in rout if "weight" in r}
            o["weight"] = ("preserved" if win == wout else "lost" if win and not wout
                           else "added" if wout and not win else "altered")
            if any(_attrs(r) != ABSENT for r in rin + rout):
                o["attrs_in"] = [_attrs(r) for r in rin]
                o["attrs_out"] = [_attrs(r) for r in rout]
            if any("weight" in r for r in rin + rout):
                o["weights_in"] = [r.get("weight", ABSENT) for r in rin]
                o["weights_out"] = [r.get("weight", ABSENT) for r in rout]
            objs[k] = o
        for k in list(decl_out) + list(implied_out):
            if k not in objs:
                objs[k] = OrderedDict(declared_in=0, declared_out=len(decl_out.get(k, [])), present_out=True,
                                      status="new")
        return objs

    res["nodes"] = objects(n_in, n_out, inodes_in, inodes_out)
    res["edges"] = objects(e_in, e_out, iedges_in, iedges_out)

    # id types: an id missing in output while str(id) exists with another type
    id_changes = []
    str_out = defaultdict(set)
    for k, v in ids_out.items():
        str_out[str(v)].add(type(v).__name__)
    for k, v in ids_in.items():
        if k not in ids_out and str(v) in str_out:
            id_changes.append({"id": str(v), "type_in": type(v).__name__, "types_out": sorted(str_out[str(v)])})
    res["id_type_changes"] = id_changes

    # summary counts
    summ = OrderedDict()
    n_rec_in = sum(len(v) for v in i_in.values())
    n_rec_out = sum(len(v) for v in i_out.values())
    summ["incidence_records"] = f"{n_rec_in} -> {n_rec_out}"
    k, t = _count_triples(i_in, i_out, _role)
    summ["role_records_kept"] = f"{k}/{t}"
    k, t = _count_triples(i_in, i_out, lambda r: r.get("direction", ABSENT))
    summ["direction_records_kept"] = f"{k}/{t}"
    k, t = _count_triples(i_in, i_out, lambda r: r.get("weight", ABSENT))
    summ["incidence_weight_records_kept"] = f"{k}/{t}"
    k, t = _count_triples(i_in, i_out, _attrs)
    summ["incidence_attrs_records_kept"] = f"{k}/{t}"
    summ["pairs_lost"] = sum(1 for p in pairs.values() if p["status"] == "lost")
    summ["pairs_new"] = sum(1 for p in pairs.values() if p["status"] == "new")
    summ["pairs_count_changed"] = sum(1 for p in pairs.values() if p["status"] == "count-changed")
    summ["weights_added_on_incidences"] = sum(1 for p in pairs.values() if p.get("weight") == "added")

    def objsumm(objs):
        declared = {k: o for k, o in objs.items() if o.get("declared_in")}
        with_attrs = {k: o for k, o in declared.items() if o.get("attrs") != "preserved" or o.get("attrs_in")}
        return OrderedDict(
            declared_in=len(declared),
            missing_out=sorted(k for k, o in objs.items() if o.get("declared_in") and not o["present_out"]),
            attrs_not_preserved={k: o["attrs"] for k, o in objs.items() if o.get("attrs") not in (None, "preserved")},
            weight_not_preserved={k: o["weight"] for k, o in objs.items() if o.get("weight") not in (None, "preserved")},
            new_out=sorted(k for k, o in objs.items() if o.get("status") == "new"),
        )
    summ["nodes"] = objsumm(res["nodes"])
    summ["edges"] = objsumm(res["edges"])
    summ["network_type"] = top["network-type"]["status"] + f" ({top['network-type']['in']} -> {top['network-type']['out']})"
    summ["metadata"] = top["metadata"]["status"]
    summ["metadata_keys_lost"] = top["metadata"]["keys_lost"]
    summ["metadata_keys_added"] = top["metadata"]["keys_added"]
    summ["id_type_changes"] = len(id_changes)
    res["summary"] = summ
    return res


def deep_find_strings(obj, needles, _seen=None, _path="", _depth=0, _hits=None):
    """Search an arbitrary Python object graph for exact string values; return {needle: [paths]}."""
    if _hits is None:
        _hits = defaultdict(list)
    if _seen is None:
        _seen = set()
    if _depth > 12 or id(obj) in _seen:
        return _hits
    if isinstance(obj, str):
        if obj in needles:
            _hits[obj].append(_path or "<root>")
        return _hits
    if isinstance(obj, (int, float, bool, type(None))):
        return _hits
    _seen.add(id(obj))
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            for col in obj.columns:
                deep_find_strings(list(obj[col].values), needles, _seen, f"{_path}[{col!r}]", _depth + 1, _hits)
            deep_find_strings(list(obj.index), needles, _seen, f"{_path}.index", _depth + 1, _hits)
            return _hits
        if isinstance(obj, pd.Series):
            deep_find_strings(list(obj.values), needles, _seen, f"{_path}.values", _depth + 1, _hits)
            return _hits
    except ImportError:
        pass
    if isinstance(obj, dict):
        for k, v in obj.items():
            deep_find_strings(k, needles, _seen, f"{_path}.<key>", _depth + 1, _hits)
            deep_find_strings(v, needles, _seen, f"{_path}[{k!r}]", _depth + 1, _hits)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for i, v in enumerate(obj):
            deep_find_strings(v, needles, _seen, f"{_path}[{i}]", _depth + 1, _hits)
    elif hasattr(obj, "__dict__"):
        for k, v in vars(obj).items():
            if k.startswith("__"):
                continue
            deep_find_strings(v, needles, _seen, f"{_path}.{k}", _depth + 1, _hits)
    return _hits


def roles_of(doc):
    return sorted({r["attrs"]["role"] for r in doc.get("incidences", [])
                   if isinstance(r.get("attrs"), dict) and isinstance(r["attrs"].get("role"), str)})


if __name__ == "__main__":
    write_cases()
    for n, c in build_cases().items():
        print(f"{n:45s} {c['description'][:90]}")
