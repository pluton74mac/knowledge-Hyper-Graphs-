"""One-off: annotate the four P2-owned JSON Schemas with x-khg-code and replace oneOf/anyOf dispatch
by key/datatype dispatch (if/then), so every failure lands on the subschema that owns it.
Accepted documents are unchanged (checked afterwards by re-running every positive and negative case).
Applied once; the originals are in original/."""
import copy, json, sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent  # the work folder (already applied: do not run again)


def load(n):
    return json.loads((W / n).read_text(encoding="utf-8"))


def save(n, d):
    (W / n).write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ptr(d, p):
    for part in p.strip("/").split("/"):
        d = d[int(part)] if isinstance(d, list) else d[part.replace("~1", "/").replace("~0", "~")]
    return d


def ann(d, p, code):
    node = ptr(d, p)
    assert isinstance(node, dict), p
    assert "x-khg-code" not in node, f"already annotated: {p}"
    node["x-khg-code"] = code


def dispatch(branches, key):
    """oneOf branches that each fix `key` by const -> (enum of consts, allOf of if/then)."""
    consts, parts = [], []
    for b in branches:
        b = copy.deepcopy(b)
        c = b["properties"][key]["const"]
        consts.append(c)
        b["properties"][key] = {}
        b.pop("type", None)
        parts.append({"if": {"properties": {key: {"const": c}}, "required": [key]}, "then": b})
    return consts, parts


# ---------------- khg-record-1.0.0 (layer C) ----------------
R = load("khg-record-1.0.0.schema.json")
D = R["definitions"]
assert "oneOf" in D["value"] and "oneOf" in D["literal"] and "oneOf" in D["selector"], "already transformed?"

D["value"] = {
    "type": "object", "minProperties": 1, "maxProperties": 1,
    "propertyNames": {"enum": ["entity", "literal", "fact", "special", "unbound"]},
    "not": {"required": ["unbound"]},
    "properties": {"entity": {"$ref": "#/definitions/id"}, "literal": {"$ref": "#/definitions/literal"},
                   "fact": {"$ref": "#/definitions/id"}, "special": {"enum": ["somevalue", "novalue"]}},
    "x-khg-code": {"type": "KHG-C001", "minProperties": "KHG-C001", "maxProperties": "KHG-C001",
                   "propertyNames": "KHG-C001", "not": "KHG-C005"},
}
consts, parts = dispatch(D["literal"]["oneOf"], "datatype")
D["literal"] = {"type": "object", "required": ["datatype"], "properties": {"datatype": {"enum": consts}},
                "allOf": parts, "x-khg-code": "KHG-C004"}
consts, parts = dispatch(D["selector"]["oneOf"], "type")
D["selector"] = {"type": "object", "required": ["type"], "properties": {"type": {"enum": consts}}, "allOf": parts}
gv = D["goal_binding"]["properties"]["value"]
assert gv == {"anyOf": [{"$ref": "#/definitions/value"}, {"$ref": "#/definitions/unbound"}]}, gv
D["goal_binding"]["properties"]["value"] = {"if": {"type": "object", "required": ["unbound"]},
                                            "then": {"$ref": "#/definitions/unbound"},
                                            "else": {"$ref": "#/definitions/value"}}
ann(R, "/definitions/confidence", "KHG-C003")
ann(R, "/definitions/evidence", "KHG-C007")
ann(R, "/definitions/record_common/allOf/0/then", "KHG-C008")
ann(R, "/definitions/fact/allOf/1/then", "KHG-C006")
ann(R, "/definitions/goal/allOf/1/then", "KHG-C006")
ann(R, "/definitions/goal/allOf/2/then", "KHG-C006")
save("khg-record-1.0.0.schema.json", R)

# ---------------- khg-hif-1.0.0 (layer P) ----------------
P = load("khg-hif-1.0.0.schema.json")
PD = P["definitions"]
body = P["allOf"][1]
# types already fixed by the vendored schema (allOf[0]) are not repeated: the profile constrains attrs and metadata only
body.pop("type")
for k in ("nodes", "edges", "incidences"):
    body["properties"][k].pop("type")
for k in ("metadata", "node", "edge", "incidence"):
    PD[k].pop("type")
for k in ("node", "edge", "incidence"):
    PD[k]["properties"]["attrs"].pop("type")
assert PD["id"] == {"type": "string", "pattern": "^(?!_:)[^\\s\\x00-\\x1f\\x7f]{1,512}$"}, PD["id"]
PD["id"] = {"type": "string", "pattern": "^[^\\s\\x00-\\x1f\\x7f]{1,512}$", "not": {"type": "string", "pattern": "^_:"},
            "x-khg-code": {"type": "KHG-P002", "pattern": "KHG-P003", "not": "KHG-P004"}}
ann(P, "/allOf/1", {"required": "KHG-P001"})
ann(P, "/allOf/1/properties/network-type", "KHG-P007")
ann(P, "/allOf/1/then", "KHG-P010")
ann(P, "/allOf/1/else", "KHG-P011")
ann(P, "/definitions/metadata", {"required": "KHG-P001", "propertyNames": "KHG-P008", "properties": "KHG-P009"})
# nodes
ann(P, "/definitions/node", {"required": "KHG-P013"})
ann(P, "/definitions/node/properties/node", {"type": "KHG-P002", "pattern": "KHG-P003"})
ann(P, "/definitions/node/properties/attrs", {"required": "KHG-P013", "propertyNames": "KHG-P014"})
ann(P, "/definitions/node/properties/attrs/properties/khg:kind", "KHG-P013")
ann(P, "/definitions/node/allOf/0/else/properties/node", "KHG-P004")
for i in range(1, 6):
    ann(P, f"/definitions/node/allOf/{i}/then/properties/node", "KHG-P004")
    if "attrs" in ptr(P, f"/definitions/node/allOf/{i}/then/properties"):
        ann(P, f"/definitions/node/allOf/{i}/then/properties/attrs", "KHG-P013")
# edges
ann(P, "/definitions/edge", {"required": "KHG-P012"})
ea = PD["edge"]["properties"]["attrs"]
assert ea["required"] == ["khg:kind", "khg:relation", "khg:status"], ea["required"]
ea["required"] = ["khg:relation", "khg:status"]
ea["allOf"] = [{"required": ["khg:kind"], "x-khg-code": "KHG-P013"}]
ann(P, "/definitions/edge/properties/attrs", {"required": "KHG-P012", "properties": "KHG-P012", "propertyNames": "KHG-P014"})
ann(P, "/definitions/edge/properties/attrs/properties/khg:kind", "KHG-P013")
# incidences
ann(P, "/definitions/incidence", {"required": "KHG-P005"})
ann(P, "/definitions/incidence/properties/node", {"type": "KHG-P002", "pattern": "KHG-P003"})
ann(P, "/definitions/incidence/properties/attrs", {"required": "KHG-P005", "propertyNames": "KHG-P014"})
ann(P, "/definitions/incidence/properties/attrs/properties/role", "KHG-P006")
ann(P, "/definitions/incidence/properties/attrs/properties/role-position", "KHG-P015")
ann(P, "/definitions/incidence/properties/attrs/properties/khg:bid", "KHG-P005")
ann(P, "/definitions/incidence/properties/attrs/properties/khg:direction", "KHG-P011")
save("khg-hif-1.0.0.schema.json", P)

# ---------------- khg-schema-1.0.0 (layer M) ----------------
M = load("khg-schema-1.0.0.schema.json")
MD = M["definitions"]
f_entity, f_literal, f_fact = MD["filler"]["oneOf"]
lit_props = copy.deepcopy(f_literal["properties"])
lit_props["literal"]["x-khg-code"] = "KHG-M006"
MD["filler"] = {
    "type": "object",
    "propertyNames": {"enum": ["entity", "literal", "fact", "precision_min", "units"]},
    "anyOf": [{"required": ["entity"]}, {"required": ["literal"]}, {"required": ["fact"]}],
    "allOf": [
        {"if": {"required": ["entity"]}, "then": {"additionalProperties": False, "properties": copy.deepcopy(f_entity["properties"])}},
        {"if": {"required": ["literal"]}, "then": {"additionalProperties": False, "properties": lit_props}},
        {"if": {"required": ["fact"]}, "then": {"additionalProperties": False, "properties": copy.deepcopy(f_fact["properties"])}},
    ],
}
c_roles, c_req = MD["constraint"]["oneOf"]
roles_then = copy.deepcopy(c_roles); roles_then.pop("type"); roles_then["properties"]["type"] = {}
roles_then["required"] = [x for x in roles_then["required"] if x != "type"]
req_then = copy.deepcopy(c_req); req_then.pop("type"); req_then["properties"]["type"] = {}
req_then["required"] = [x for x in req_then["required"] if x != "type"]
MD["constraint"] = {
    "type": "object", "required": ["type"],
    "properties": {"type": {"enum": c_roles["properties"]["type"]["enum"] + ["requires"]}},
    "allOf": [{"if": {"properties": {"type": {"const": "requires"}}, "required": ["type"]}, "then": req_then, "else": roles_then}],
}
t_int, t_other = MD["relation"]["properties"]["time"]["oneOf"]
int_then = copy.deepcopy(t_int); int_then.pop("type"); int_then["properties"]["model"] = {}
int_then["required"] = [x for x in int_then["required"] if x != "model"]
oth_else = copy.deepcopy(t_other); oth_else.pop("type"); oth_else["properties"]["model"] = {}
oth_else.pop("required")
MD["relation"]["properties"]["time"] = {
    "type": "object", "required": ["model"],
    "properties": {"model": {"enum": ["interval"] + t_other["properties"]["model"]["enum"]}},
    "allOf": [{"if": {"properties": {"model": {"const": "interval"}}, "required": ["model"]}, "then": int_then, "else": oth_else}],
    "x-khg-code": "KHG-M007",
}
ann(M, "/properties/version", "KHG-M004")
ann(M, "/definitions/relation/properties/roles", {"minItems": "KHG-M001"})
ann(M, "/definitions/usage/allOf/0/then", "KHG-M014")
ann(M, "/definitions/usage/allOf/1/then", "KHG-M007")
save("khg-schema-1.0.0.schema.json", M)

# ---------------- khg-queue-1.0.0 (layer Q) ----------------
Q = load("khg-queue-1.0.0.schema.json")
ann(Q, "/properties/kind", "KHG-Q003")
ann(Q, "/definitions/item/properties/item_kind", "KHG-Q003")
ann(Q, "/definitions/item/properties/extraction", {"required": "KHG-Q001"})
ann(Q, "/definitions/item/properties/extraction/properties/extractor", {"required": "KHG-Q001"})
ann(Q, "/definitions/item/properties/extraction/properties/doc", {"required": "KHG-Q001"})
ann(Q, "/definitions/item/allOf/0/then/properties/payload/properties/status", "KHG-Q002")
ann(Q, "/definitions/log_entry/properties/action", "KHG-Q003")
ann(Q, "/definitions/log_entry/allOf/0/then", "KHG-Q004")
save("khg-queue-1.0.0.schema.json", Q)
print("annotated and restructured: khg-record, khg-hif, khg-schema, khg-queue")
