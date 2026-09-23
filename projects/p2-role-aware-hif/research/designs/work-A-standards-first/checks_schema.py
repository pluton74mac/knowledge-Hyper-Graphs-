"""Schema-level checks for design A (run with venv-hif: jsonschema 4.26.0 + fastjsonschema 2.22.2). Offline.

1. relation-type schemas validate against the meta-schema
2. the gate fixture validates against the C1 document schema
3. to_hif(fixture) validates against the vendored HIF schema (blob e2105bb) and the KHG HIF profile
4. from_hif(to_hif(fixture)) == canonical(fixture)
5. identity keys, arity, participants per edge; P6 hypergraph of the gate schema
Writes gate-fixture.hif.json.
"""
import hashlib
import json
import os
import sys

import fastjsonschema
import jsonschema
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proto  # noqa: E402

PROBES = "/home/user/knowledge-Hyper-Graphs-/projects/p2-role-aware-hif/research/probes"
HIF_PATH = os.path.join(PROBES, "hif-schema", "hif_schema_v0.1.0.json")


def load(p):
    with open(p, encoding="utf-8") as f:
        return proto.strict_loads(f.read())


hif_bytes = open(HIF_PATH, "rb").read()
assert hashlib.sha256(hif_bytes).hexdigest() == proto.HIF_SHA256, "vendored HIF schema hash"
HIF = json.loads(hif_bytes)
S = {n: load(os.path.join(HERE, "schemas", n)) for n in os.listdir(os.path.join(HERE, "schemas"))}
registry = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))


def check(name, schema, instance):
    v = jsonschema.Draft7Validator(schema, registry=registry)
    errs = sorted(v.iter_errors(instance), key=lambda e: list(e.absolute_path))
    fast = fastjsonschema.compile(schema, handlers={"https": lambda uri: HIF})
    try:
        fast(instance)
        fok = True
    except fastjsonschema.JsonSchemaException as e:
        fok, ferr = False, e.message
    ok = not errs
    print(f"  {'OK ' if ok else 'ERR'} jsonschema / {'OK ' if fok else 'ERR'} fastjsonschema : {name}")
    for e in errs[:5]:
        print("      ", "/".join(map(str, e.absolute_path)), "->", e.message[:160])
    if not fok:
        print("       fast:", ferr[:200])
    assert ok == fok, "validators disagree"
    return ok


print("meta-schemas are valid draft-07:")
for n, s in sorted(S.items()):
    jsonschema.Draft7Validator.check_schema(s)
    print("  OK", n)

gate_schema = load(os.path.join(HERE, "gate-demo.schema.json"))
builtin = load(os.path.join(HERE, "builtin.schema.json"))
fixture = load(os.path.join(HERE, "gate-fixture.khg.json"))

print("1. relation-type schema documents:")
assert check("gate-demo.schema.json", S["khg-schema-1.0.0.json"], gate_schema)
assert check("builtin.schema.json", S["khg-schema-1.0.0.json"], builtin)

print("2. C1 document:")
assert check("gate-fixture.khg.json", S["khg-document-1.0.0.json"], fixture)

schema = proto.Schema(builtin, gate_schema)
hif = proto.to_hif(fixture, schema)
with open(os.path.join(HERE, "gate-fixture.hif.json"), "w", encoding="utf-8") as f:
    json.dump(hif, f, ensure_ascii=False, indent=1)
    f.write("\n")

print("3. HIF export:")
assert check("gate-fixture.hif.json vs vendored HIF 0.1.0", HIF, hif)
assert check("gate-fixture.hif.json vs KHG HIF profile", S["khg-hif-profile-1.0.0.json"], hif)
print(f"   network-type={hif['network-type']} nodes={len(hif['nodes'])} edges={len(hif['edges'])} "
      f"incidences={len(hif['incidences'])}")
pairs = {}
for i in hif["incidences"]:
    pairs.setdefault((i["edge"], i["node"]), []).append(i["attrs"]["role"])
print("   repeated (edge,node) pairs:", {f"{k[0]}|{k[1]}": v for k, v in pairs.items() if len(v) > 1})

print("4. fold/unfold round trip:")
back = proto.from_hif(hif, schema)
canon = proto.canonical_doc(fixture, schema)
print("   from_hif(to_hif(doc)) == canonical(doc):", back == canon)
assert back == canon
assert proto.to_hif(back, schema) == hif, "unfold is deterministic"

print("5. identity keys, arity (C1 definition) and distinct participants:")
for e in canon["edges"]:
    kd = proto.key_digest(e, schema)
    evs = [proto.event_key(e, ev, schema)[:19] for ev in e.get("evidence", []) if ev["type"] == "extracted"]
    print(f"   {e['edge']:4} {e['relation']:25} arity={proto.arity(e, schema)} "
          f"participants={proto.participants(e, schema)} content={proto.content_key(e, schema)[:19]} "
          f"core={proto.content_key(e, schema, 'core')[:19]} key={(kd or '-')[:19]} events={evs}")
print("P6 hypergraph (core+qualifier, domain relations):")
for r, roles in schema.hypergraph().items():
    print("  ", r, sorted(roles))
