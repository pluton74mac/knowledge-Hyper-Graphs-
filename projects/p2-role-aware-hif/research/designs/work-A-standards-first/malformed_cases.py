"""Malformed-case list of design A, executed against the prototype layers (run with venv-hif). Offline.

Layers, in order: J strict JSON -> H vendored HIF schema (HIF inputs) -> P profile schemas + profile
structure checks -> S semantic checks against the relation-type schema; D for schema documents; Q for
queue streams. For each case the FIRST failing layer must be the expected one; for Python-checked
layers (P010-P013, S, D002+, Q003+) the expected code must also be among the reported codes.
Also checks that the unmodified fixture, schema and queue stream pass every layer.
"""
import copy
import json
import os
import re
import sys

import jsonschema
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proto  # noqa: E402
import semantic_proto  # noqa: E402

PROBES = "/home/user/knowledge-Hyper-Graphs-/projects/p2-role-aware-hif/research/probes"
HIF = json.load(open(os.path.join(PROBES, "hif-schema", "hif_schema_v0.1.0.json")))
S = {n: json.load(open(os.path.join(HERE, "schemas", n))) for n in os.listdir(os.path.join(HERE, "schemas"))}
REG = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))
V = {k: jsonschema.Draft7Validator(v, registry=REG) for k, v in
     {"H": HIF, "P-hif": S["khg-hif-profile-1.0.0.json"], "P-c1": S["khg-document-1.0.0.json"],
      "D": S["khg-schema-1.0.0.json"], "Q": S["khg-queue-1.0.0.json"]}.items()}
BUILTIN = json.load(open(os.path.join(HERE, "builtin.schema.json")))
GATE_SCHEMA = json.load(open(os.path.join(HERE, "gate-demo.schema.json")))
FIX = json.load(open(os.path.join(HERE, "gate-fixture.khg.json")))
SCHEMA = proto.Schema(BUILTIN, GATE_SCHEMA)
HIFDOC = proto.to_hif(FIX, SCHEMA)
TEXTS = {"doc:pmid-0000001": open(os.path.join(HERE, "doc-pmid-0000001.txt"), encoding="utf-8").read()}


# ---------------------------------------------------------------- layer J
def layer_j(text):
    try:
        if not text.strip():
            return ["KHG-J001"]
        obj = proto.strict_loads(text)
    except proto.StrictJSONError as e:
        return [str(e).split()[0]]
    except ValueError:
        return ["KHG-J001"]
    codes = []

    def walk(x):
        if isinstance(x, str):
            if re.search("[\ud800-\udfff]", x):
                codes.append("KHG-J004")
        elif isinstance(x, bool):
            pass
        elif isinstance(x, int) and abs(x) > 2 ** 53 - 1:
            codes.append("KHG-J005")
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(k)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    return codes or obj


# ---------------------------------------------------------------- layer P (python part, HIF inputs)
def profile_structure(h):
    codes = []
    nodes, edges = {}, {}
    for n in h.get("nodes", []):
        if n["node"] in nodes:
            codes.append("KHG-P011")
        nodes[n["node"]] = n
    for e in h["edges"]:
        if e["edge"] in edges:
            codes.append("KHG-P011")
        edges[e["edge"]] = e
    seen = set()
    for i in h["incidences"]:
        if i["edge"] not in edges or (i["node"].startswith("_:") and i["node"] not in nodes):
            codes.append("KHG-P012")
        k = (i["edge"], i["node"], i["attrs"]["role"], i["attrs"].get("position"))
        if k in seen:
            codes.append("KHG-P013")
        seen.add(k)
    for nid, n in nodes.items():
        a = n.get("attrs", {})
        if "literal" in a and nid != proto.literal_node_id(a["literal"]):
            codes.append("KHG-P010")
        if "edge" in a and nid != proto.edge_node_id(a["edge"]):
            codes.append("KHG-P010")
    return codes


# ---------------------------------------------------------------- layer D (python part)
def schema_structure(sd):
    codes = []
    roles, types = set(sd.get("roles", {})) | set(BUILTIN["roles"]), set(sd.get("types", {}))
    rels = set(sd["relations"]) | set(BUILTIN["relations"])
    if not sd["khg-schema"].startswith("khg/"):
        for name in list(sd["relations"]) + list(sd.get("roles", {})) + list(sd.get("types", {})):
            if name.startswith("khg:"):
                codes.append("KHG-D006")
    for r, rel in sd["relations"].items():
        for ro, u in rel["roles"].items():
            if ro not in roles or any(t not in types for t in u.get("types", [])) or \
                    any(x != "*" and x not in rels for x in u.get("edges", [])):
                codes.append("KHG-D002")
            if u.get("max", 1) is not None and u.get("min", 0) > u.get("max", 1):
                codes.append("KHG-D004")
            if ro in sd.get("valid-roles", {}).values():
                codes.append("KHG-D005")
        if "key" in rel and any(k not in rel["roles"] for k in rel["key"]["roles"]):
            codes.append("KHG-D003")
    return codes


# ---------------------------------------------------------------- layer Q (python part)
def queue_structure(lines, schema):
    codes, items, state, open_violations = [], {}, {}, {}
    if not lines or "metadata" not in lines[0] or any("metadata" in ln for ln in lines[1:]):
        codes.append("KHG-Q002")
    for ln in lines:
        if "item" in ln and "payload" in ln:
            items[ln["item"]] = ln
            e = copy.deepcopy(ln["payload"])
            want = {"content": proto.content_key(e, schema), "core": proto.content_key(e, schema, "core"),
                    "events": sorted(proto.event_key(e, ev, schema) for ev in e.get("evidence", [])
                                     if ev["type"] in ("extracted", "inferred"))}
            if ln["keys"] != want:
                codes.append("KHG-Q003")
            state[ln["item"]] = "pending"
        elif "log" in ln:
            it = ln["item"]
            if it not in items:
                codes.append("KHG-Q004")
                continue
            a = ln["action"]
            if a == "flag" and ln["severity"] == "violation":
                open_violations.setdefault(it, set()).add(ln["rule"])
            if a == "fix":
                open_violations.get(it, set()).discard(ln["rule"])
            if a in ("accept", "merge", "reject"):
                if state[it] in ("accepted", "merged", "rejected"):
                    codes.append("KHG-Q005")
                if a in ("accept", "merge") and open_violations.get(it):
                    codes.append("KHG-Q006")
                state[it] = {"accept": "accepted", "merge": "merged", "reject": "rejected"}[a]
            if a == "review":
                state[it] = "needs-review"
    return codes


# ---------------------------------------------------------------- run one input through its layers
def run(kind, obj):
    """Return (layer, codes) of the first failing layer, or ('pass', [])."""
    if kind.startswith("text-"):
        r = layer_j(obj)
        if isinstance(r, list):
            return "J", r
        kind, obj = kind[5:], r
    if kind == "hif":
        if list(V["H"].iter_errors(obj)):
            return "H", []
        if list(V["P-hif"].iter_errors(obj)):
            return "P", []
        c = profile_structure(obj)
        if c:
            return "P", c
        return run("c1", proto.from_hif(obj, None))
    if kind == "c1":
        if list(V["P-c1"].iter_errors(obj)):
            return "P", []
        sch = SCHEMA
        c = [x[0] for x in semantic_proto.validate(obj, sch, TEXTS)]
        return ("S", c) if c else ("pass", [])
    if kind == "schema":
        if list(V["D"].iter_errors(obj)):
            return "D", []
        c = schema_structure(obj)
        return ("D", c) if c else ("pass", [])
    if kind == "queue":
        for ln in obj:
            if list(V["Q"].iter_errors(ln)):
                return "Q", []
        c = queue_structure(obj, SCHEMA)
        return ("Q", c) if c else ("pass", [])
    raise ValueError(kind)


def edge(doc, eid):
    return [e for e in doc["edges"] if e["edge"] == eid][0]


def hedge(h, eid):
    return [e for e in h["edges"] if e["edge"] == eid][0]


def c1(f):
    d = copy.deepcopy(FIX)
    f(d)
    return d


def hf(f):
    h = copy.deepcopy(HIFDOC)
    f(h)
    return h


def sd(f):
    d = copy.deepcopy(GATE_SCHEMA)
    f(d)
    return d


# ---------------------------------------------------------------- the queue stream (valid baseline)
def queue_stream():
    """The C3 example of the design (queue-example.json): accept, then a duplicate merged as new evidence."""
    return json.load(open(os.path.join(HERE, "queue-example.json"), encoding="utf-8"))


def qs(f):
    q = copy.deepcopy(queue_stream())
    f(q)
    return q


def _set(d, k, v):
    d[k] = v


def _dup_key_text():
    t = json.dumps(HIFDOC, ensure_ascii=False)
    return t.replace('"attrs": {"role": "treatment"}', '"attrs": {"role": "treatment", "role": "agent"}', 1)


CASES = [
    # id, description, kind, input, expected layer, expected code (schema layers: the code the package's
    # x-khg-code annotation assigns; checked here only for the layer)
    ("M01", "zero-byte file", "text-hif", "", "J", "KHG-J001"),
    ("M02", "NaN in incidence attrs (not strict JSON)", "text-hif",
     json.dumps(HIFDOC, ensure_ascii=False).replace('"role": "treatment"', '"role": "treatment", "score": NaN', 1), "J", "KHG-J003"),
    ("M03", "duplicate key inside one attrs object", "text-hif", _dup_key_text(), "J", "KHG-J002"),
    ("M04", "lone surrogate escape in a label", "text-c1",
     json.dumps(FIX, ensure_ascii=False).replace('"label": "TP53"', '"label": "TP53\\ud800"', 1), "J", "KHG-J004"),
    ("M05", "integer beyond 2^53-1 (HIF id)", "text-hif",
     json.dumps(HIFDOC, ensure_ascii=False).replace('"node": "ex:MYC"', '"node": 9007199254740993', 2), "J", "KHG-J005"),
    ("M06", "no incidences array", "hif", hf(lambda h: h.pop("incidences")), "H", "KHG-H001"),
    ("M07", "top-level 'version' key", "hif", hf(lambda h: _set(h, "version", "1.0")), "H", "KHG-H002"),
    ("M08", "top-level 'roles' vocabulary block", "hif", hf(lambda h: _set(h, "roles", {"treatment": "treatment"})), "H", "KHG-H002"),
    ("M09", "top-level '$schema' key", "hif", hf(lambda h: _set(h, "$schema", "x")), "H", "KHG-H002"),
    ("M10", "record-level 'role' on an incidence", "hif", hf(lambda h: _set(h["incidences"][0], "role", "condition")), "H", "KHG-H002"),
    ("M11", "record-level 'relation' on an edge", "hif", hf(lambda h: _set(h["edges"][0], "relation", "treats")), "H", "KHG-H002"),
    ("M12", "record-level 'type' on a node", "hif", hf(lambda h: _set(h["nodes"][0], "type", "Organisation")), "H", "KHG-H002"),
    ("M13", "incidence attrs is a string", "hif", hf(lambda h: _set(h["incidences"][0], "attrs", "condition")), "H", "KHG-H003"),
    ("M14", "direction holds a role name", "hif", hf(lambda h: _set(h["incidences"][0], "direction", "treatment")), "H", "KHG-H004"),
    ("M15", "network-type outside the enum", "hif", hf(lambda h: _set(h, "network-type", "knowledge-hypergraph")), "H", "KHG-H004"),
    ("M16", "id 1.5 (non-integral number)", "hif", hf(lambda h: _set(h["incidences"][0], "node", 1.5)), "H", "KHG-H003"),
    ("M17", "id null", "hif", hf(lambda h: _set(h["incidences"][0], "edge", None)), "H", "KHG-H003"),
    ("M18", "incidence without node", "hif", hf(lambda h: h["incidences"][0].pop("node")), "H", "KHG-H001"),
    ("M19", "no role-convention / khg-profile declaration", "hif",
     hf(lambda h: [h["metadata"].pop(k) for k in ("role-convention", "khg-profile")]), "P", "KHG-P001"),
    ("M20", "hif-schema is the moving 'latest' URL (as in the KB sample)", "hif",
     hf(lambda h: _set(h["metadata"], "hif-schema", "https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json")), "P", "KHG-P001"),
    ("M21", "integer ids (valid HIF, not the profile)", "hif",
     hf(lambda h: [_set(i, "node", 7) for i in h["incidences"] if i["node"] == "ex:MYC"]), "P", "KHG-P003"),
    ("M22", "empty-string id", "hif", hf(lambda h: _set(h["incidences"][0], "node", "")), "P", "KHG-P003"),
    ("M23", "entity id with the reserved '_:' prefix", "c1",
     c1(lambda d: _set(d["nodes"][0], "node", "_:ADA")), "P", "KHG-P003"),
    ("M24", "incidence without attrs.role", "hif", hf(lambda h: h["incidences"][0]["attrs"].pop("role")), "P", "KHG-P004"),
    ("M25", "list-valued role (legacy shape, profile mode)", "hif",
     hf(lambda h: _set(h["incidences"][0]["attrs"], "role", ["condition", "target"])), "P", "KHG-P004"),
    ("M26", "directed file, incidence without direction", "hif", hf(lambda h: h["incidences"][0].pop("direction")), "P", "KHG-P005"),
    ("M27", "network-type 'asc'", "hif", hf(lambda h: _set(h, "network-type", "asc")), "P", "KHG-P006"),
    ("M28", "metadata.default_attrs (HyperNetX would invent values)", "hif",
     hf(lambda h: _set(h["metadata"], "default_attrs", {"incidences": {"attrs": {"role": "participant"}}})), "P", "KHG-P007"),
    ("M29", "derived node without its value attrs", "hif",
     hf(lambda h: [n.pop("attrs") for n in h["nodes"] if n["node"].startswith("_:lit:")][:1]), "P", "KHG-P008"),
    ("M30", "edge record without status", "hif", hf(lambda h: h["edges"][0]["attrs"].pop("status")), "P", "KHG-P009"),
    ("M31", "binding with two values (node and literal)", "c1",
     c1(lambda d: _set(edge(d, "f2")["bindings"][0], "literal", {"datatype": "string", "value": "x"})), "P", "KHG-P014"),
    ("M32", "edge with no bindings", "c1", c1(lambda d: _set(edge(d, "f2"), "bindings", [])), "P", "KHG-P014"),
    ("M33", "quantity without unit", "c1", c1(lambda d: edge(d, "f6")["bindings"][0]["literal"].pop("unit")), "P", "KHG-P015"),
    ("M34", "time literal with month 13", "c1", c1(lambda d: _set(edge(d, "f6")["bindings"][3]["literal"], "value", "2019-13")), "P", "KHG-P015"),
    ("M35", "text literal without language tag", "c1", c1(lambda d: edge(d, "f6")["bindings"][1]["literal"].pop("lang")), "P", "KHG-P015"),
    ("M36", "status 'superseded' without superseded-by", "c1", c1(lambda d: edge(d, "f10").pop("superseded-by")), "P", "KHG-P016"),
    ("M37", "status outside the enum ('disputed')", "c1", c1(lambda d: _set(edge(d, "f2"), "status", "disputed")), "P", "KHG-P016"),
    ("M38", "probability confidence above 1", "c1",
     c1(lambda d: _set(edge(d, "f1")["evidence"][1]["confidence"], "value", 8.2)), "P", "KHG-P017"),
    ("M39", "bare-number confidence (no scale)", "c1", c1(lambda d: _set(edge(d, "f1")["evidence"][1], "confidence", 0.82)), "P", "KHG-P017"),
    ("M40", "span offsets without a document digest", "c1", c1(lambda d: edge(d, "f1")["evidence"][1].pop("digest")), "P", "KHG-P017"),
    ("M41", "stored arity field (arity is derived, never stored)", "c1", c1(lambda d: _set(edge(d, "f2"), "arity", 3)), "P", "KHG-P018"),
    ("M42", "reserved key inside opaque edge attrs", "c1", c1(lambda d: _set(edge(d, "f2"), "attrs", {"status": "asserted"})), "P", "KHG-P019"),
    ("M43", "literal node id does not match its value", "hif",
     hf(lambda h: [_set(n["attrs"]["literal"], "value", "AC 124") for n in h["nodes"]
                   if n.get("attrs", {}).get("literal", {}).get("value") == "AC 123"]), "P", "KHG-P010"),
    ("M44", "node declared twice", "hif", hf(lambda h: h["nodes"].append(copy.deepcopy(h["nodes"][0]))), "P", "KHG-P011"),
    ("M45", "incidence names an undeclared edge", "hif", hf(lambda h: _set(h["incidences"][0], "edge", "f99")), "P", "KHG-P012"),
    ("M46", "exact duplicate incidence (edge, node, role)", "hif",
     hf(lambda h: h["incidences"].append(copy.deepcopy(h["incidences"][0]))), "P", "KHG-P013"),
    ("M47", "unknown relation", "c1", c1(lambda d: _set(edge(d, "f2"), "relation", "causes")), "S", "KHG-S001"),
    ("M48", "role not declared for the relation", "c1", c1(lambda d: _set(edge(d, "f2")["bindings"][2], "role", "outcome")), "S", "KHG-S002"),
    ("M49", "required role missing on an asserted fact", "c1", c1(lambda d: edge(d, "f1")["bindings"].pop(3)), "S", "KHG-S003"),
    ("M50", "role bound more often than max", "c1",
     c1(lambda d: edge(d, "f3")["bindings"].append({"role": "target", "node": "ex:MYC", "direction": "head"})), "S", "KHG-S004"),
    ("M51", "literal where an entity is expected", "c1",
     c1(lambda d: edge(d, "f2")["bindings"].__setitem__(2, {"role": "effect", "literal": {"datatype": "string", "value": "hypo"}, "direction": "head"})), "S", "KHG-S005"),
    ("M52", "entity of the wrong type", "c1", c1(lambda d: _set(edge(d, "f2")["bindings"][2], "node", "ex:TP53")), "S", "KHG-S006"),
    ("M53", "literal value outside the declared values", "c1",
     c1(lambda d: _set(edge(d, "s1")["bindings"][0]["literal"], "value", "update")), "S", "KHG-S007"),
    ("M54", "unbound slot on an asserted fact", "c1", c1(lambda d: _set(edge(d, "g1"), "status", "asserted") or
                                                       _set(edge(d, "g1"), "evidence", [{"id": "e1", "type": "curated"}])), "S", "KHG-S008"),
    ("M55", "novalue and a value for the same role", "c1",
     c1(lambda d: edge(d, "f8")["bindings"].append({"role": "catalyst", "node": "ex:TP53", "direction": "head"})), "S", "KHG-S009"),
    ("M56", "ordered role without position", "c1", c1(lambda d: edge(d, "f5")["bindings"][2].pop("position")), "S", "KHG-S010"),
    ("M57", "direction contradicts the declared direction", "c1", c1(lambda d: _set(edge(d, "f2")["bindings"][2], "direction", "tail")), "S", "KHG-S011"),
    ("M58", "duplicate binding (same role and value)", "c1",
     c1(lambda d: edge(d, "f2")["bindings"].append({"role": "agent", "node": "ex:insulin", "direction": "tail"})), "S", "KHG-S012"),
    ("M59", "dangling hyperedge reference", "c1", c1(lambda d: _set(edge(d, "f9")["bindings"][1], "edge", "f99")), "S", "KHG-S013"),
    ("M60", "nesting cycle", "c1", c1(lambda d: (
        edge(d, "f9").__setitem__("relation", "asserts"),
        d["edges"].append({"edge": "f12", "relation": "asserts", "status": "asserted",
                           "bindings": [{"role": "asserter", "node": "ex:ADA", "direction": "tail"},
                                        {"role": "statement", "edge": "f13", "direction": "head"}],
                           "evidence": [{"id": "e1", "type": "curated"}]}),
        d["edges"].append({"edge": "f13", "relation": "asserts", "status": "asserted",
                           "bindings": [{"role": "asserter", "node": "ex:ADA", "direction": "tail"},
                                        {"role": "statement", "edge": "f12", "direction": "head"}],
                           "evidence": [{"id": "e1", "type": "curated"}]}))), "S", "KHG-S014"),
    ("M61", "reference to an edge of a disallowed relation", "c1", c1(lambda d: _set(edge(d, "f9")["bindings"][1], "edge", "f2")), "S", "KHG-S015"),
    ("M62", "asserted fact without evidence", "c1", c1(lambda d: edge(d, "f2").pop("evidence")), "S", "KHG-S016"),
    ("M63", "binding cites an unknown evidence id", "c1", c1(lambda d: _set(edge(d, "f1")["bindings"][1], "evidence", ["e9"])), "S", "KHG-S017"),
    ("M64", "span text does not match the source", "c1", c1(lambda d: _set(edge(d, "f1")["evidence"][1], "start", 195) or
                                                          _set(edge(d, "f1")["evidence"][1], "end", 211)), "S", "KHG-S018"),
    ("M65", "extracted evidence without a run id", "c1", c1(lambda d: edge(d, "f10")["evidence"][0].pop("run")), "S", "KHG-S019"),
    ("M66", "valid interval reversed", "c1", c1(lambda d: _set(edge(d, "f1"), "valid", {"from": "2024-01-01", "until": "2023"})), "S", "KHG-S020"),
    ("M67", "score confidence outside its range", "c1",
     c1(lambda d: _set(edge(d, "f1")["evidence"][1], "confidence", {"value": 11, "scale": "score", "min": 0, "max": 10})), "S", "KHG-S021"),
    ("M68", "superseded fact with no khg:supersedes record", "c1", c1(lambda d: d["edges"].remove(edge(d, "s1"))), "S", "KHG-S022"),
    ("M69", "supersession across different key bindings", "c1",
     c1(lambda d: _set(edge(d, "f10")["bindings"][0], "node", "ex:air-canada")), "S", "KHG-S023"),
    ("M70", "time role used as a binding (must be lifted into valid)", "c1",
     c1(lambda d: edge(d, "f11")["bindings"].append({"role": "start-time", "literal": {"datatype": "time", "value": "2019-05"}})), "S", "KHG-S024"),
    ("M71", "unknown schema id", "c1", c1(lambda d: _set(d["metadata"], "khg-schema", "other/1.0.0")), "S", "KHG-S025"),
    ("M72", "edge record duplicated (same id, same recorded)", "c1",
     c1(lambda d: d["edges"].append(copy.deepcopy(edge(d, "f2")))), "S", "KHG-S026"),
    ("M73", "id not in NFC (decomposed e-acute)", "c1", c1(lambda d: _set(d["nodes"][8], "node", "ex:Zürich")), "S", "KHG-S027"),
    ("M74", "relation with no roles", "schema", sd(lambda s: _set(s["relations"]["treats"], "roles", {})), "D", "KHG-D001"),
    ("M75", "schema id without a semantic version", "schema", sd(lambda s: _set(s, "khg-schema", "gate-demo")), "D", "KHG-D001"),
    ("M76", "unknown datatype", "schema", sd(lambda s: _set(s["relations"]["treats"]["roles"]["dosage"], "datatypes", ["float"])), "D", "KHG-D001"),
    ("M77", "end-older policy on a non-temporal key", "schema",
     sd(lambda s: _set(s["relations"]["chief-executive"]["key"], "temporal", False)), "D", "KHG-D001"),
    ("M78", "usage names an undeclared type", "schema", sd(lambda s: _set(s["relations"]["treats"]["roles"]["treatment"], "types", ["Medicine"])), "D", "KHG-D002"),
    ("M79", "key names a role the relation does not use", "schema",
     sd(lambda s: _set(s["relations"]["treats"]["key"], "roles", ["treatment", "dose"])), "D", "KHG-D003"),
    ("M80", "min greater than max", "schema", sd(lambda s: _set(s["relations"]["flight"]["roles"]["stop"], "max", 1)), "D", "KHG-D004"),
    ("M81", "valid-time role also used in a relation", "schema",
     sd(lambda s: _set(s["relations"]["chief-executive"]["roles"], "start-time", {"slot": "qualifier", "datatypes": ["time"]})), "D", "KHG-D005"),
    ("M82", "domain schema uses the reserved khg: prefix", "schema",
     sd(lambda s: _set(s["roles"], "khg:mine", {"label": "x"})), "D", "KHG-D006"),
    ("M83", "queue payload not in status candidate", "queue", qs(lambda q: _set(q[1]["payload"], "status", "asserted")), "Q", "KHG-Q001"),
    ("M84", "log action outside the vocabulary", "queue", qs(lambda q: _set(q[2], "action", "delete")), "Q", "KHG-Q001"),
    ("M85", "recorded keys differ from recomputed keys", "queue",
     qs(lambda q: _set(q[1]["keys"], "core", "sha256:" + "0" * 64)), "Q", "KHG-Q003"),
    ("M86", "log entry names a missing item", "queue", qs(lambda q: _set(q[3], "item", "q9")), "Q", "KHG-Q004"),
    ("M87", "decision after a terminal decision", "queue",
     qs(lambda q: q.append({"log": "l4", "at": "2026-09-23T10:06:00Z", "item": "q1", "actor": {"agent": "person:reviewer-2"},
                            "action": "reject", "reason": "changed my mind"})), "Q", "KHG-Q005"),
    ("M89", "stream does not start with its header line", "queue", qs(lambda q: q.insert(0, q.pop(1))), "Q", "KHG-Q002"),
    ("M90", "unsupported khg-profile major version", "c1", c1(lambda d: _set(d["metadata"], "khg-profile", "2.0.0")), "P", "KHG-P002"),
    ("M88", "accept while a violation is open", "queue",
     qs(lambda q: q.insert(3, {"log": "l1b", "at": "2026-09-23T10:00:02Z", "item": "q1", "actor": {"agent": "khg-lint", "version": "1.0.0"},
                               "action": "flag", "rule": "KHG-S003", "severity": "violation", "path": "/bindings", "message": "x"})), "Q", "KHG-Q006"),
]

if __name__ == "__main__":
    print("baselines:")
    for kind, obj in (("c1", FIX), ("hif", HIFDOC), ("schema", GATE_SCHEMA), ("schema", BUILTIN), ("queue", queue_stream())):
        layer, codes = run(kind, copy.deepcopy(obj))
        print(f"  {kind:6} -> {layer} {codes}")
        assert layer == "pass", (kind, codes)
    bad = 0
    python_checked = re.compile(r"KHG-(J|P01[0-3]|S|D00[2-6]|Q00[3-6])")
    for cid, desc, kind, obj, want_layer, want_code in CASES:
        layer, codes = run(kind, copy.deepcopy(obj))
        ok = layer == want_layer and (not python_checked.match(want_code) or want_code in codes)
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {cid} {want_code:9} {layer} {sorted(set(codes))} {desc}")
    print(f"{len(CASES)} cases, {bad} failures")
    sys.exit(1 if bad else 0)
