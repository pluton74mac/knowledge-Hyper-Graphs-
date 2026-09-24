"""Validate the design-C examples and run the gate chain through the probe's loader sketch.

Run with the venv that has xgi, hypernetx, jsonschema (venv-libs); fastjsonschema is imported from venv-hif
if available on sys.path. No network: requests.get is patched to raise.
"""
from __future__ import annotations

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/knowledge-Hyper-Graphs-"
PROBES = os.path.join(REPO, "projects/p2-role-aware-hif/research/probes")
VENDORED = os.path.join(PROBES, "hif-schema/hif_schema_v0.1.0.json")
sys.path.insert(0, HERE)
sys.path.insert(0, PROBES)

import requests  # noqa: E402


def _no_network(*a, **k):
    raise RuntimeError("network disabled in design checks")


requests.get = _no_network

import jsonschema  # noqa: E402
from referencing import Registry, Resource  # noqa: E402

import c1  # noqa: E402
import gate_fixture  # noqa: E402
import hif_codec  # noqa: E402

RESULTS = {}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


HIF_SCHEMA = load(VENDORED)
REC_SCHEMA = load(os.path.join(HERE, "khg-record-1.0.0.schema.json"))
META_SCHEMA = load(os.path.join(HERE, "khg-relation-schema-1.0.0.schema.json"))
PROFILE_SCHEMA = load(os.path.join(HERE, "khg-hif-1.0.0.schema.json"))
REGISTRY = Registry().with_resource(HIF_SCHEMA["$id"], Resource.from_contents(HIF_SCHEMA))

V_HIF = jsonschema.Draft7Validator(HIF_SCHEMA)
V_REC = jsonschema.Draft7Validator(REC_SCHEMA)
V_META = jsonschema.Draft7Validator(META_SCHEMA)
V_PROFILE = jsonschema.Draft7Validator(PROFILE_SCHEMA, registry=REGISTRY)


def errs(v, doc, n=5):
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message[:160]}" for e in v.iter_errors(doc)][:n]


def fast_validate(schema, doc, handlers=None):
    try:
        import fastjsonschema
    except ImportError:
        return "fastjsonschema not importable"
    try:
        fastjsonschema.compile(schema, handlers=handlers or {})(doc)
        return "valid"
    except fastjsonschema.JsonSchemaException as e:
        return f"invalid: {e.message[:160]}"


def same(a, b):
    return c1.cjson(a) == c1.cjson(b)


def main():
    records = gate_fixture.build()
    c1.dump_jsonl(records, os.path.join(HERE, "gate.khg.jsonl"))
    # 1. C1 lines against the record schema, the schema record against the meta-schema
    rec_errors = {}
    for r in records:
        if r["kind"] == "relation-schema":
            e = errs(V_META, r)
        else:
            e = errs(V_REC, r)
        if e:
            rec_errors[r.get("id", r["kind"])] = e
    RESULTS["c1_record_schema_errors"] = rec_errors
    # literal lexical checks (python layer) on every literal in the fixture
    lit_errs = {}
    for r in records:
        for b in r.get("bindings", []):
            if "literal" in b["value"]:
                e = c1.literal_errors(b["value"])
                if e:
                    lit_errs[f"{r['id']}/{b['bid']}"] = e
    RESULTS["literal_errors"] = lit_errs

    # 2. HIF export: full fixture and the directed slice
    full = hif_codec.to_hif(records)
    directed_rel = {"compared_in_trial", "regulates", "co_administration_causes", "chief_executive", "reported_in"}
    sliced = hif_codec.to_hif(records, relations=directed_rel)
    for name, doc in (("full", full), ("directed", sliced)):
        with open(os.path.join(HERE, f"gate-{name}.hif.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        RESULTS[f"hif_{name}"] = {
            "network-type": doc["network-type"],
            "counts": {k: len(doc[k]) for k in ("nodes", "edges", "incidences")},
            "vendored_hif_schema_jsonschema": errs(V_HIF, doc) or "valid",
            "vendored_hif_schema_fastjsonschema": fast_validate(HIF_SCHEMA, doc),
            "profile_schema_jsonschema": errs(V_PROFILE, doc) or "valid",
            "profile_schema_fastjsonschema": fast_validate(
                PROFILE_SCHEMA, doc, {"https": lambda uri: HIF_SCHEMA}),
            "repeated_pairs": sum(1 for _ in _repeated(doc)),
        }
    # 3. HIF -> C1 import equals the original container (full) / the sliced container (directed)
    back = hif_codec.from_hif(full)
    RESULTS["hif_full_import_equals_original"] = same(back, records)
    if not RESULTS["hif_full_import_equals_original"]:
        RESULTS["diff_first"] = _first_diff(back, records)
    back_d = hif_codec.from_hif(sliced)
    RESULTS["hif_directed_reexport_equal"] = same(hif_codec.to_hif(back_d, relations=directed_rel), sliced)

    # 4. The gate chains through the probe loader sketch (no library HIF functions)
    import role_loaders_sketch as rl
    for name, doc in (("full", full), ("directed", sliced)):
        H, ctx = rl.to_xgi(copy.deepcopy(doc))
        via_xgi = rl.from_xgi(H, ctx)
        G, gctx = rl.to_hnx(via_xgi)
        via_hnx = rl.from_hnx(G, gctx)
        c_xgi_hnx = hif_codec.canonical_hif(via_hnx)
        G2, g2 = rl.to_hnx(copy.deepcopy(doc))
        via_hnx2 = rl.from_hnx(G2, g2)
        H2, h2 = rl.to_xgi(via_hnx2)
        via_xgi2 = rl.from_xgi(H2, h2)
        c_hnx_xgi = hif_codec.canonical_hif(via_xgi2)
        chain = {
            "xgi_class": type(H).__name__,
            "xgi_report": {k: len(v) for k, v in ctx.report.items()},
            "HIF->XGI->HIF->HNX->HIF equals input (structural)": same(c_xgi_hnx, hif_codec.canonical_hif(doc)),
            "HIF->HNX->HIF->XGI->HIF equals input (structural)": same(c_hnx_xgi, hif_codec.canonical_hif(doc)),
        }
        try:
            c1_back = hif_codec.from_hif(c_xgi_hnx)
            chain["C1 after chain equals C1 before"] = same(
                c1_back, records if name == "full" else hif_codec.from_hif(doc))
        except Exception as e:  # noqa: BLE001
            chain["C1 after chain"] = f"{type(e).__name__}: {e}"
        # where the roles are, natively
        if name == "directed":
            chain["xgi_TP53_in_tail_and_head"] = ("gene:TP53" in H.edges.dimembers("khg:f03-regulates")[0]
                                                 and "gene:TP53" in H.edges.dimembers("khg:f03-regulates")[1])
        chain["hnx_cell_role_f02_metformin"] = G2.get_cell_properties("khg:f02-trial", "drug:metformin", "role")
        extra = G2.get_cell_properties("khg:f02-trial", "drug:metformin", rl.EXTRA)
        chain["hnx_extra_records_f02_metformin"] = [r["attrs"]["role"] for r in (extra or [])]
        RESULTS[f"chain_{name}"] = chain
    # 5. Library evidence: what the libraries' own HIF functions do to the fixture (offline)
    RESULTS["library_evidence"] = library_evidence(full, sliced)
    # 6. The sample's C1 migration sanity: its attrs.role incidences are already single-role records
    print(json.dumps(RESULTS, ensure_ascii=False, indent=1))


def _repeated(doc):
    seen = {}
    for i in doc["incidences"]:
        k = (i["edge"], i["node"])
        seen[k] = seen.get(k, 0) + 1
    for k, n in seen.items():
        if n > 1:
            yield k


def _first_diff(a, b):
    for x, y in zip(a, b):
        if not same(x, y):
            return {"got": x, "want": y}
    return {"len": [len(a), len(b)]}


def library_evidence(full, sliced):
    import tempfile
    import xgi
    import hypernetx as hnx
    from hypernetx import hif as hnx_hif

    class _Resp:
        def __init__(self, data):
            self._d = data

        def json(self):
            return self._d

        @property
        def text(self):
            return json.dumps(self._d)
    hnx_hif.requests.get = lambda url, *a, **k: _Resp(copy.deepcopy(HIF_SCHEMA))  # offline, vendored bytes
    out = {}
    for name, doc in (("full", full), ("directed", sliced)):
        n_roles = len(doc["incidences"])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "in.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False)
            H = xgi.read_hif(p)
            q = os.path.join(d, "xgi.json")
            xgi.write_hif(H, q)
            xo = load(q)
            xgi_roles = sum(1 for i in xo["incidences"] if "role" in (i.get("attrs") or {}))
            G = hnx.from_hif(doc)
            ho = hnx.to_hif(G, network_type=doc["network-type"]) if G is not None else None
            hnx_roles = sum(1 for i in ho["incidences"] if "role" in (i.get("attrs") or {})) if ho else None
            out[name] = {
                "input_incidence_records_with_role": n_roles,
                "xgi.read_hif->write_hif: records with role": xgi_roles,
                "xgi: incidence records out": len(xo["incidences"]),
                "xgi: metadata keys kept": sorted((xo.get("metadata") or {}).keys()) == sorted(doc["metadata"].keys()),
                "hnx.from_hif->to_hif: returned": None if ho is None else "dict",
                "hnx: records with role": hnx_roles,
                "hnx: incidence records out": None if ho is None else len(ho["incidences"]),
                "hnx: metadata keys out": None if ho is None else sorted((ho.get("metadata") or {}).keys()),
            }
            if ho is not None and doc["network-type"] == "directed":
                G2 = hnx.from_hif(ho)
                ho2 = hnx.to_hif(G2, network_type="directed") if G2 is not None else None
                out[name]["hnx second generation to_hif returned"] = None if ho2 is None else "dict"
    return out


if __name__ == "__main__":
    main()
