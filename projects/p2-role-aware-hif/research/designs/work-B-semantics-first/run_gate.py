"""Validates the design's artefacts and runs the gate chain on both fixtures (no network)."""
import json, sys, copy, socket
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

# --- no network: any socket use fails ---------------------------------------------------------
class _NoNet(socket.socket):
    def connect(self, *a, **k): raise OSError("network disabled in gate tests")
socket.socket = _NoNet

import jsonschema, fastjsonschema
from referencing import Registry, Resource
from khg_proto import Schema, c1_to_hif, hif_to_c1, canonical_doc, strict_loads, cjson
import role_loaders_sketch as sk

HIF = json.loads((HERE / "hif_schema_v0.1.0.json").read_text())
REC = json.loads((HERE / "khg-record-1.0.0.schema.json").read_text())
LANG = json.loads((HERE / "khg-schema-1.0.0.schema.json").read_text())
PROF = json.loads((HERE / "khg-hif-1.0.0.schema.json").read_text())
reg = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))

def js(schema, inst):
    v = jsonschema.Draft7Validator(schema, registry=reg)
    return sorted(f"{list(e.absolute_path)}: {e.message}"[:200] for e in v.iter_errors(inst))

def fjs(schema, inst):
    f = fastjsonschema.compile(schema, handlers={"https": lambda uri: HIF})
    try:
        f(inst); return []
    except fastjsonschema.JsonSchemaException as e:
        return [str(e)[:200]]

def both(name, schema, inst):
    a, b = js(schema, inst), fjs(schema, inst)
    ok = (not a) and (not b)
    print(f"  {'OK ' if ok else 'ERR'} {name}: jsonschema={len(a)} errors, fastjsonschema={'pass' if not b else 'fail'}")
    for e in a[:5]: print("       ", e)
    for e in b[:2]: print("       ", e)
    return ok

schema_doc = strict_loads((HERE / "p2-gate.schema.json").read_text())
S = Schema(schema_doc)
print("meta-schemas are themselves valid draft-07:")
for n, s in (("record", REC), ("lang", LANG), ("profile", PROF)):
    jsonschema.Draft7Validator.check_schema(s); print("  OK", n)
print("schema document:")
both("p2-gate.schema.json vs khg-schema/1.0.0", LANG, schema_doc)
allok = True
for fx in ("fixture-directed", "fixture-undirected"):
    print(f"== {fx}")
    doc = strict_loads((HERE / f"{fx}.khg.json").read_text())
    allok &= both("C1 doc vs khg-record/1.0.0", REC, doc)
    canon0 = canonical_doc(doc, S)
    allok &= both("canonical C1 doc vs khg-record/1.0.0", REC, canon0)
    hif = c1_to_hif(doc, S)
    (HERE / f"{fx}.hif.json").write_text(json.dumps(hif, ensure_ascii=False, indent=1))
    allok &= both("HIF vs vendored hif_schema_v0.1.0 (blob e2105bb)", HIF, hif)
    allok &= both("HIF vs khg-hif/1.0.0 profile (allOf vendored)", PROF, hif)
    # gate chain: C1 -> HIF -> XGI -> HIF -> HNX -> HIF -> C1
    H, ctx = sk.to_xgi(copy.deepcopy(hif)); hif_x = sk.from_xgi(H, ctx)
    print("   xgi class:", type(H).__name__, "| stale:", len(ctx.report["stale_records_dropped"]), "unlabelled:", len(ctx.report["unlabelled_memberships_exported_bare"]))
    G, ctx2 = sk.to_hnx(copy.deepcopy(hif_x)); hif_xh = sk.from_hnx(G, ctx2)
    allok &= both("HIF after XGI and HNX vs profile", PROF, hif_xh)
    back = hif_to_c1(hif_xh, S)
    canon1 = canonical_doc(back, S)
    same = cjson(canon0) == cjson(canon1)
    print(f"   chain C1->HIF->XGI->HIF->HNX->HIF->C1 canonical equality: {same}")
    # per-library chains too
    H2, c2 = sk.to_hnx(copy.deepcopy(hif)); only_h = hif_to_c1(sk.from_hnx(H2, c2), S)
    H3, c3 = sk.to_xgi(copy.deepcopy(hif)); only_x = hif_to_c1(sk.from_xgi(H3, c3), S)
    print("   XGI-only equal:", cjson(canonical_doc(only_x, S)) == cjson(canon0), "| HNX-only equal:", cjson(canonical_doc(only_h, S)) == cjson(canon0))
    nb = sum(len(r.get("bindings", [])) for r in doc["records"])
    print(f"   records={len(doc['records'])} bindings={nb} incidences={len(hif['incidences'])} nodes={len(hif['nodes'])} edges={len(hif['edges'])} network-type={hif['network-type']}")
    allok &= same
    (HERE / f"{fx}.canonical.khg.json").write_text(json.dumps(canon0, ensure_ascii=False, indent=1))
print("ALL OK" if allok else "FAILURES")
