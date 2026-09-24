"""Writes <examples>/malformed-cases.json (the v1 malformed-case list, khg-malformed-cases/1.0.0) and checks every case
mechanically against the full G2 rule with the validator prototype (khg_validate_proto):

- the input is the named base plus an RFC 6902 patch (or input_text for layer J); it must differ from the base;
- a schema_patch (RFC 6902 on fixture.relation-schema.json) is applied first, and the harness re-stamps the base's
  schema digest so that D009 does not fire;
- expect_target pins what each indexed patch path points at in the base (a record id, an incidence (edge, bid), a
  node or edge id, a relation id, a line kind), so regenerated fixtures cannot silently shift a patch;
- validation (engine jsonschema, stop at the first erroring step): the first rejecting layer is the listed layer and
  the listed code is among the error codes; fastjsonschema's codes at that step are contained in jsonschema's;
- every unpatched base validates with no error finding.
usage: make_malformed.py <examples dir>   (run with the venv that has jsonschema and fastjsonschema)"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import khg_synth as K  # noqa: E402
import khg_engines_proto as EN  # noqa: E402
import khg_validate_proto as VP  # noqa: E402

EX = Path(sys.argv[1])
load = lambda n: json.loads((EX / n).read_text(encoding="utf-8"))
lines_of = lambda n: {"lines": [json.loads(x) for x in (EX / n).read_text(encoding="utf-8").splitlines() if x.strip()]}
HIF, DSL, C1, SCH = load("fixture.hif.json"), load("fixture.directed-slice.hif.json"), load("fixture.c1.json"), \
    load("fixture.relation-schema.json")
HIST, QUEUE, C4 = load("fixture.history.c1.json"), lines_of("smoke-queue.khg-queue.jsonl"), lines_of("c4-items.jsonl")
TEXTS = {k: v["text"] for k, v in load("fixture.doc-texts.json")["texts"].items()}
H, D, C, S, Q, HI, I4 = ("fixture.hif.json", "fixture.directed-slice.hif.json", "fixture.c1.json",
                         "fixture.relation-schema.json", "smoke-queue.khg-queue.jsonl", "fixture.history.c1.json",
                         "c4-items.jsonl")
BASES = {H: HIF, D: DSL, C: C1, S: SCH, Q: QUEUE, HI: HIST, I4: C4}
KIND = {H: "hif", D: "hif", C: "c1", S: "relation-schema", Q: "queue", HI: "c1", I4: "c4"}


# ------------------------------------------------------------------ lookups by identity (never by hand-typed index)
def inc(doc, edge, bid):
    return next(i for i, x in enumerate(doc["incidences"]) if x["edge"] == edge and x["attrs"]["khg-bid"] == bid)


def node(doc, nid):
    return next(i for i, x in enumerate(doc["nodes"]) if x["node"] == nid)


def edge(doc, eid):
    return next(i for i, x in enumerate(doc["edges"]) if x["edge"] == eid)


def rec(rid, doc=C1, version=None):
    return next(i for i, x in enumerate(doc["records"]) if x.get("id") == rid and
                (version is None or x.get("version") == version))


def bnd(rid, bid, doc=C1, version=None):
    i = rec(rid, doc, version)
    j = next(j for j, b in enumerate(doc["records"][i]["bindings"]) if b["bid"] == bid)
    return f"/records/{i}/bindings/{j}"


def evi(rid, eid, doc=C1, version=None):
    i = rec(rid, doc, version)
    j = next(j for j, e in enumerate(doc["records"][i]["evidence"]) if e["id"] == eid)
    return f"/records/{i}/evidence/{j}"


def rel(rid):
    return next(i for i, x in enumerate(SCH["relations"]) if x["id"] == rid)


def usage(rid, role):
    r = SCH["relations"][rel(rid)]
    return f"/relations/{rel(rid)}/roles/{next(j for j, u in enumerate(r['roles']) if u['role'] == role)}"


def line(doc, kind, qid=None):
    return next(i for i, x in enumerate(doc["lines"]) if x.get("kind") == kind and (qid is None or x.get("qid") == qid
                                                                                  or x.get("lid") == qid))


R = lambda path: {"op": "remove", "path": path}
A = lambda path, v: {"op": "add", "path": path, "value": v}
P = lambda path, v: {"op": "replace", "path": path, "value": v}
reg1 = inc(HIF, "f:reg-1", "b2")
ent_node = node(HIF, "ex:TP53")
lit_n = node(HIF, HIF["incidences"][inc(HIF, "f:pop-łódź-2019", "b2")]["node"])
sv_n = node(HIF, HIF["incidences"][inc(HIF, "f:born-scribe", "b2")]["node"])
ref_n = node(HIF, "_:ref:f:born-louis14-paris")
king14 = rec("f:king-14")
CUR = {"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:x"}}

cases = []
n = iter(range(1, 1000))


def case(desc, layer, code, base=None, patch=None, *, text=None, source="", note=None, schema_patch=None,
         doc_text=None):
    c = {"id": f"MC{next(n):03d}", "description": desc, "layer": layer, "code": code}
    if text is not None:
        c["kind"] = "json"
        c["input_text"] = text
    else:
        c["kind"] = KIND[base]
        c["base"] = base
        c["patch"] = patch
    if schema_patch:
        c["schema_patch"] = schema_patch
    if doc_text:
        c["doc_text"] = doc_text
    c["source"] = source
    if note:
        c["note"] = note
    cases.append(c)


# ================================================================== J: strict JSON
case("zero-byte file", "J", "KHG-J001", text="", source="R02 case 34")
case("truncated JSON document", "J", "KHG-J001", text='{"incidences": [', source="R02 case 34 (variant)")
case("UTF-8 byte-order mark before the document", "J", "KHG-J002", text="﻿{\"incidences\": []}", source="RFC 8259 §8.1")
case("duplicate key role inside one attrs object", "J", "KHG-J003",
     text='{"incidences": [{"edge": "f:1", "node": "ex:a", "attrs": {"role": "x", "role": "y"}}]}', source="R02 case 36")
case("NaN literal in attrs", "J", "KHG-J004", text='{"incidences": [{"edge": "f:1", "node": "ex:a", "attrs": {"w": NaN}}]}',
     source="R02 case 35; R03 c22; R01 V19")
case("lone surrogate escape in a label", "J", "KHG-J005",
     text='{"incidences": [], "nodes": [{"node": "ex:a", "attrs": {"label": "\\ud800"}}]}', source="RFC 8259 §8.2")
case("integer 2^53+1 (as a HIF id or a value)", "J", "KHG-J006",
     text='{"incidences": [{"edge": 9007199254740993, "node": 1}]}', source="R02 case 22; R03 c23; A M05")
case("top level (or one JSONL line) is an array, not an object", "J", "KHG-J007", text='[]', source="C J-NOT-OBJECT")
# ================================================================== V: version gate
case("C1 header format khg-record/2.0.0 (unknown major)", "V", "KHG-V001", C, [P("/header/format", "khg-record/2.0.0")],
     source="R01 V41; A M90")
case("HIF khg-profile khg-hif/1.9.0 (a minor newer than the reader)", "V", "KHG-V001", H,
     [P("/metadata/khg-profile", "khg-hif/1.9.0")], source="PLAN §7; B §11.2")
# ================================================================== H: vendored HIF schema
case("no incidences key", "H", "KHG-H001", H, [R("/incidences")], source="R01 V01; R02 case 31")
case("top-level version key", "H", "KHG-H002", H, [A("/version", "1.0.0")], source="R02 case 04")
case("top-level roles vocabulary block", "H", "KHG-H002", H, [A("/roles", {"regulator": "regulator"})],
     source="R01 V02; R02 case 05")
case("top-level $schema key", "H", "KHG-H002", H, [A("/$schema", "https://json-schema.org/draft-07/schema")],
     source="R02 case 06")
case("record-level role on an incidence (outside attrs)", "H", "KHG-H003", H, [A(f"/incidences/{reg1}/role", "regulator")],
     source="R01 V03; R02 case 11")
case("record-level relation on an edge", "H", "KHG-H003", H, [A(f"/edges/{edge(HIF, 'f:reg-1')}/relation", "regulates")],
     source="R02 case 13")
case("record-level type on a node", "H", "KHG-H003", H, [A(f"/nodes/{ent_node}/type", "Gene")], source="R02 case 14")
case("incidence attrs is a string", "H", "KHG-H004", H, [P(f"/incidences/{reg1}/attrs", "regulator")], source="R02 case 10")
case("direction 'treatment'", "H", "KHG-H005", H, [P(f"/incidences/{reg1}/direction", "treatment")],
     source="R01 V05; R02 case 12")
case("incidence without node", "H", "KHG-H006", H, [R(f"/incidences/{reg1}/node")], source="R01 V04")
case("node id of type float 1.5", "H", "KHG-H007", H, [P(f"/nodes/{ent_node}/node", 1.5)], source="R02 case 18")
case("node id of type boolean", "H", "KHG-H007", H, [P(f"/nodes/{ent_node}/node", True)], source="R02 case 19")
case("node id null", "H", "KHG-H007", H, [P(f"/nodes/{ent_node}/node", None)], source="R02 case 20")
case("network-type 'knowledge-hypergraph'", "H", "KHG-H008", H, [P("/network-type", "knowledge-hypergraph")],
     source="R02 case 26")
case("incidences is an object, not an array", "H", "KHG-H009", H, [P("/incidences", {})], source="B H009")
# ================================================================== R: role-convention 1.0.0
case("metadata without the role-convention declaration", "R", "KHG-R003", H, [R("/metadata/role-convention")],
     source="R01 V07; F15; critique UPSTREAM")
case("an incidence of a role-carrying edge without a role", "R", "KHG-R001", H, [R(f"/incidences/{reg1}/attrs/role")],
     source="R01 V08")
case("list-valued role", "R", "KHG-R001", H, [P(f"/incidences/{reg1}/attrs/role", ["regulator", "target"])],
     source="R01 V09; R02 case 09")
case("empty role string", "R", "KHG-R001", H, [P(f"/incidences/{reg1}/attrs/role", "")], source="R01 V09")
case("an incidence record repeated exactly (same edge, node, role and role-position)", "R", "KHG-R002", H,
     [A("/incidences/-", copy.deepcopy(HIF["incidences"][reg1]))], source="R01 V10/V11 (as ruled)")
case("role-position 0", "R", "KHG-R004", H, [P(f"/incidences/{inc(HIF, 'f:route-1', 'b2')}/attrs/role-position", 0)],
     source="rule 4 of role-convention 1.0.0")
# ================================================================== P: khg-hif profile
case("metadata without khg-profile (validated as khg-hif: no foreign fallback)", "P", "KHG-P001", H,
     [R("/metadata/khg-profile")], source="R01 V07; critique GL-02")
case("metadata without khg-document-id", "P", "KHG-P001", H, [R("/metadata/khg-document-id")], source="§4.5")
case("integer node id (valid HIF, outside the profile)", "P", "KHG-P002", H,
     [P(f"/nodes/{ent_node}/node", 53), P(f"/incidences/{reg1}/node", 53)], source="R02 cases 15-17; F10")
case("empty-string id", "P", "KHG-P003", H, [P(f"/nodes/{ent_node}/node", ""), P(f"/incidences/{reg1}/node", "")],
     source="R02 case 21")
long_ref = "_:ref:f:" + "x" * 511
case("a _:ref: node id of 519 code points (its fact id has 513)", "P", "KHG-P003", H,
     [P(f"/nodes/{ref_n}/node", long_ref), P(f"/nodes/{ref_n}/attrs/khg-ref", long_ref[6:]),
      P(f"/incidences/{inc(HIF, 'f:claim-1', 'b2')}/node", long_ref)], source="critique GL-16 (518 is the limit)")
case("incidence without khg-bid", "P", "KHG-P005", H, [R(f"/incidences/{reg1}/attrs/khg-bid")], source="§4.3")
case("legacy roles key next to role", "P", "KHG-P014", H, [A(f"/incidences/{reg1}/attrs/roles", ["regulator"])],
     source="R01 V20")
case("network-type asc", "P", "KHG-P007", H, [P("/network-type", "asc")], source="R03 D8, c04")
case("metadata.default_attrs", "P", "KHG-P008", H, [A("/metadata/default_attrs", {"incidences": {"role": "member"}})],
     source="R03 D7, c20, row 23")
case("unknown khg-* metadata key", "P", "KHG-P008", H, [A("/metadata/khg-colour", "blue")], source="§4.5")
case("hif-schema is the moving main URL (as in the KB sample)", "P", "KHG-P009", H,
     [P("/metadata/hif-schema", "https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json")],
     source="R01 PF-01; R02 §10 item 5")
case("hif-schema-sha256 is not the vendored hash", "P", "KHG-P009", H, [P("/metadata/hif-schema-sha256", "sha256:" + "0" * 64)],
     source="F2")
case("khg-literal-nodes outside shared and per_binding", "P", "KHG-P009", H, [P("/metadata/khg-literal-nodes", "hub")],
     source="critique CONS-15")
case("directed document, one incidence without direction", "P", "KHG-P010", D,
     [R(f"/incidences/{inc(DSL, 'f:reg-1', 'b2')}/direction")], source="R01 V12; R02 case 23; R03 c14, D4")
case("directed slice written as undirected (every incidence has a direction)", "P", "KHG-P011", D,
     [P("/network-type", "undirected")], source="§4.2 direction rule")
case("edge without relation", "P", "KHG-P012", H, [R(f"/edges/{edge(HIF, 'f:reg-1')}/attrs/relation")], source="R01 V14")
case("edge without khg-status", "P", "KHG-P012", H, [R(f"/edges/{edge(HIF, 'f:reg-1')}/attrs/khg-status")],
     source="R01 V40 (as revised)")
case("node without khg-kind", "P", "KHG-P013", H, [R(f"/nodes/{ent_node}/attrs/khg-kind")], source="§4.3")
case("literal node without khg-literal", "P", "KHG-P013", H, [R(f"/nodes/{lit_n}/attrs/khg-literal")], source="R01 C1-R68")
case("unknown khg-* key in incidence attrs", "P", "KHG-P014", H, [A(f"/incidences/{reg1}/attrs/khg-colour", "red")],
     source="§4.3")
case("entity node id using the reserved _: prefix", "P", "KHG-P004", H,
     [P(f"/nodes/{ent_node}/node", "_:TP53"), P(f"/incidences/{reg1}/node", "_:TP53")], source="R02 rec. 7")
case("somevalue node whose id lacks the _:sv: prefix", "P", "KHG-P004", H,
     [P(f"/nodes/{sv_n}/node", "ex:unknown"), P(f"/incidences/{inc(HIF, 'f:born-scribe', 'b2')}/node", "ex:unknown")],
     source="§4.2")
case("two incidence records of one edge share a khg-bid", "P", "KHG-P016", H,
     [P(f"/incidences/{inc(HIF, 'f:reg-1', 'b3')}/attrs/khg-bid", "b2")], source="§4.3; B S025")
case("khg-external fact reference outside a slice", "P", "KHG-P017", H, [A(f"/nodes/{ref_n}/attrs/khg-external", True)],
     source="critique CONS-14")
# ================================================================== D: decoding
case("node declared twice", "D", "KHG-D001", H, [A("/nodes/-", copy.deepcopy(HIF["nodes"][ent_node]))],
     source="R01 V16; R03 c19, D5")
case("edge declared twice", "D", "KHG-D001", H, [A("/edges/-", copy.deepcopy(HIF["edges"][edge(HIF, 'f:reg-1')]))],
     source="R01 V16")
case("incidence names an undeclared node", "D", "KHG-D002", H, [P(f"/incidences/{reg1}/node", "ex:MDM2")],
     source="R01 V17; R02 case 28")
case("incidence names an undeclared edge", "D", "KHG-D003", H, [P(f"/incidences/{reg1}/edge", "f:reg-9")], source="R02 case 29")
case("literal node id does not match its value", "D", "KHG-D005", H,
     [P(f"/nodes/{lit_n}/attrs/khg-literal/amount", "+679942")], source="R01 D-09")
case("special node id does not match (record id, bid)", "D", "KHG-D005", H,
     [P(f"/incidences/{inc(HIF, 'f:born-scribe', 'b2')}/attrs/khg-bid", "b9")], source="§4.2")
case("khg-schema-sha256 does not match the relation-type schema", "D", "KHG-D009", H,
     [P("/metadata/khg-schema-sha256", "sha256:" + "0" * 64)], source="R01 V41")
case("incidence direction contradicts the role's declared direction (reported while decoding)", "S", "KHG-S016", H,
     [P(f"/incidences/{reg1}/direction", "head")], source="R01 V38; critique GL-02 (a step may emit another layer's code)")
case("fact-ref node pointing at a missing edge", "D", "KHG-D002", H,
     [P(f"/nodes/{ref_n}/attrs/khg-ref", "f:born-louis14-lyon"), P(f"/nodes/{ref_n}/node", "_:ref:f:born-louis14-lyon"),
      P(f"/incidences/{inc(HIF, 'f:claim-1', 'b2')}/node", "_:ref:f:born-louis14-lyon")], source="R01 V18")
# ================================================================== C: record schema
case("binding value with two kinds (entity and literal)", "C", "KHG-C001", C,
     [A(bnd("f:reg-1", "b1") + "/value/literal", {"datatype": "string", "value": "HeLa"})], source="R01 C1-R06")
case("status outside the lifecycle enum", "C", "KHG-C002", C, [P(f"/records/{rec('f:reg-1')}/status", "believed")],
     source="R01 V36")
case("confidence as a bare number", "C", "KHG-C003", C, [P(f"/records/{rec('f:coadmin-1')}/confidence", 0.9)],
     source="R01 V32; C1-R49")
case("quantity without unit", "C", "KHG-C004", C, [R(bnd("f:pop-łódź-2019", "b2") + "/value/literal/unit")], source="R01 V26")
case("time precision 15", "C", "KHG-C004", C, [P(bnd("f:king-14", "b3") + "/value/literal/precision", 15)], source="R01 V26")
case("calendar 'islamic'", "C", "KHG-C004", C, [P(bnd("f:claim-1", "b3") + "/value/literal/calendar", "islamic")],
     source="graft U10")
case("unbound value in an asserted hyperedge", "C", "KHG-C005", C,
     [P(bnd("f:king-14", "b5") + "/value", {"unbound": {"var": "who"}})], source="R01 V34")
case("status superseded without status_ref", "C", "KHG-C006", C,
     [R(f"/records/{rec('f:born-skłodowska-kraków')}/status_ref")], source="R01 V37; F8")
case("status_ref on an asserted fact", "C", "KHG-C006", C, [A(f"/records/{rec('f:reg-1')}/status_ref", "m:sup-1")],
     source="critique SEM-10")
case("extracted evidence without selectors and activity", "C", "KHG-C007", C,
     [R(evi("f:king-14", "e2") + "/selectors"), R(evi("f:king-14", "e2") + "/activity")], source="R01 V47")
case("position selector with a negative start", "C", "KHG-C007", C,
     [P(evi("f:king-14", "e2") + "/selectors/1/start", -1)], source="F11")
case("selectors without doc_sha256", "C", "KHG-C007", C, [R(evi("f:king-14", "e2") + "/source/doc_sha256")],
     source="F11; R04 O8")
case("inferred evidence with an empty from and no model", "C", "KHG-C007", C,
     [A(f"/records/{rec('f:reg-1')}/evidence/-", {"id": "e2", "type": "inferred", "mode": "automatic",
                                                  "source": {"doc_id": "doc:x"}, "inference": {"rule": "transitivity", "from": []}})],
     source="critique CONS-29")
case("rank deprecated without rank_reason", "C", "KHG-C008", C, [R(f"/records/{rec('f:pop-łódź-2019-dep')}/rank_reason")],
     source="R04 M5")
case("record-level field outside the format (stored arity)", "C", "KHG-C009", C, [A(f"/records/{rec('f:coadmin-1')}/arity", 3)],
     source="R01 V15; A M41")
case("hyperedge without relation", "C", "KHG-C010", C, [R(f"/records/{rec('f:reg-1')}/relation")], source="R01 V14")
case("bid with a space", "C", "KHG-C011", C, [P(bnd("f:reg-1", "b1") + "/bid", "b 1")], source="§2.1")
case("reason on a non-lifecycle hyperedge", "C", "KHG-C012", C, [A(f"/records/{rec('f:reg-1')}/reason", "correction")],
     source="§2.2")
case("lifecycle record without reason", "C", "KHG-C012", C, [R(f"/records/{rec('m:sup-1')}/reason")], source="R04 M5")
case("a goal block on an asserted fact", "C", "KHG-C012", C, [A(f"/records/{rec('f:reg-1')}/goal", {"brief": "why?"})],
     source="critique SEM-18 (7)")
# ================================================================== S: the relation-type schema
case("relation not declared", "S", "KHG-S001", C, [P(f"/records/{rec('f:reg-1')}/relation", "inhibits")], source="R01 V21")
case("role not allowed for the relation", "S", "KHG-S002", C, [P(bnd("f:reg-1", "b1") + "/role", "tissue")], source="R01 V22")
case("required role missing on an asserted fact", "S", "KHG-S003", C, [R(bnd("f:king-14", "b2"))], source="R01 V23")
case("role bound more often than max", "S", "KHG-S004", C,
     [A(f"/records/{rec('f:reg-1')}/bindings/-", {"bid": "b4", "role": "context", "value": {"entity": "ex:TP53"}})],
     source="R01 V24")
case("entity of the wrong type", "S", "KHG-S005", C, [P(bnd("f:reg-1", "b1") + "/value", {"entity": "ex:insulin"})],
     source="R01 V25")
case("literal where an entity is expected", "S", "KHG-S005", C,
     [P(bnd("f:reg-1", "b1") + "/value", {"literal": {"datatype": "string", "value": "HeLa"}})], source="R01 V25")
case("fact reference in a role that takes no facts", "S", "KHG-S005", C, [P(bnd("f:reg-1", "b1") + "/value", {"fact": "f:king-14"})],
     source="R01 V29 (nestable)")
case("somevalue where the usage forbids it", "S", "KHG-S005", C, [P(bnd("f:claim-1", "b2") + "/value", {"special": "somevalue"})],
     source="R01 C1-R08")
case("time literal with month 13", "S", "KHG-S006", C,
     [P(bnd("f:king-14", "b3") + "/value/literal/time", "+1643-13-14T00:00:00Z")], source="R01 V26")
case("day set below year precision", "S", "KHG-S006", C,
     [P(bnd("f:pop-łódź-2019", "b3") + "/value/literal/time", "+2019-00-05T00:00:00Z")], source="R01 V26")
case("29 February 1700 in the Gregorian calendar (valid only in the Julian)", "S", "KHG-S006", C,
     [P(bnd("f:king-14", "b3") + "/value/literal/time", "+1700-02-29T00:00:00Z")], source="graft U10")
case("year 0 (historical numbering has none)", "S", "KHG-S006", C,
     [P(bnd("f:claim-1", "b3") + "/value/literal/time", "+0000-00-00T00:00:00Z")], source="critique CONS-01 (Wikibase JSON)")
case("a date before 1583 without a calendar", "S", "KHG-S006", C,
     [P(bnd("f:married-curie", "b3") + "/value/literal", {"datatype": "time", "time": "+1500-01-01T00:00:00Z", "precision": 11})],
     source="critique CONS-12 (Wikidata Help:Dates)")
case("hyperedge with no bindings", "S", "KHG-S007", C, [P(f"/records/{rec('f:reg-1')}/bindings", []), R(evi("f:reg-1", "e1") + "/supports")],
     source="R01 V27")
case("valid time starts after it ends", "S", "KHG-S009", C,
     [P(bnd("f:king-14", "b4") + "/value/literal/time", "+1600-01-01T00:00:00Z")], source="R01 V30")
case("confidence scale not declared", "S", "KHG-S010", C, [P(evi("f:coadmin-1", "e1") + "/confidence/scale", "llm-1-5")],
     source="R01 V32")
case("confidence outside its scale", "S", "KHG-S010", C, [P(evi("f:coadmin-1", "e1") + "/confidence/value", 11)],
     source="R01 V32")
case("asserted fact with no evidence", "S", "KHG-S011", C, [R(f"/records/{rec('f:reg-1')}/evidence")], source="R01 V33")
case("novalue and a concrete value in one role", "S", "KHG-S013", C,
     [A(f"/records/{rec('f:cat-7')}/bindings/-", {"bid": "b3", "role": "catalyst", "value": {"entity": "ex:R-hydrolysis-7"}})],
     source="R01 V35")
case("the same filler twice in an unordered role", "S", "KHG-S014", C,
     [P(bnd("f:coadmin-1", "b1") + "/value", {"entity": "ex:metformin"})], source="R01 C1-R14")
case("ordered role with a gap in positions", "S", "KHG-S015", C, [P(bnd("f:route-1", "b4") + "/position", 4)],
     source="R01 C1-R15")
case("position on an unordered role", "S", "KHG-S015", C, [A(bnd("f:coadmin-1", "b1") + "/position", 1)], source="R01 C1-R15")
case("direction on a binding whose usage declares one", "S", "KHG-S016", C, [A(bnd("f:reg-1", "b2") + "/direction", "head")],
     source="R01 V38")
case("goal omits a required role instead of leaving it unbound", "S", "KHG-S018", C, [R(bnd("g:who-1774", "b1"))],
     source="R01 C1-R72; P11")
case("one unbound variable used twice in a goal", "S", "KHG-S019", C,
     [P(bnd("g:who-1774", "b2") + "/value", {"unbound": {"var": "who"}})], source="§2.4")
case("id not in Unicode NFC (decomposed e with acute)", "S", "KHG-S020", C,
     [P(f"/records/{rec('f:reg-1')}/id", "f:rég-1")], source="R03 c13; F11")
case("quote differs from text[start:end] (code points, NFC)", "S", "KHG-S021", C,
     [P(evi("f:king-14", "e2") + "/selectors/1/start", 1), P(evi("f:king-14", "e2") + "/selectors/1/end", 42)],
     source="F11; R04 M6", doc_text={"doc:louis-bio": TEXTS["doc:louis-bio"]})
case("evidence supports an unknown bid", "S", "KHG-S022", C, [P(evi("f:king-14", "e2") + "/supports", ["b1", "b9"])],
     source="R01 C1-R36")
case("precision below the usage's precision_min", "S", "KHG-S023", C,
     [P(bnd("f:pop-łódź-2019", "b3") + "/value/literal", {"datatype": "time", "time": "+2010-00-00T00:00:00Z", "precision": 8,
                                                         "calendar": "gregorian"})], source="R04 M2")
case("unit not allowed for the role", "S", "KHG-S023", C, [P(bnd("f:pop-łódź-2019", "b2") + "/value/literal/unit", "wd:Q11573")],
     source="R04 M2")
case("must_differ violated where the schema says error", "S", "KHG-S024", C, None,
     schema_patch=[P(f"/relations/{rel('flies_between')}/constraints/0/severity", "error")],
     source="R01 C1-R34; R04 M1; critique GL-01", note="the unpatched fixture reports it as a warning")
case("the same bid twice in one hyperedge", "S", "KHG-S025", C, [P(bnd("f:reg-1", "b3") + "/bid", "b2")], source="§2.1")
case("lifecycle reason outside the relation's reasons", "S", "KHG-S026", C, [P(f"/records/{rec('m:sup-1')}/reason", "update")],
     source="F7; A M53")
# ================================================================== D: cross-record and container
case("nesting cycle (a claim about itself; the schema lets claims take claims)", "D", "KHG-D008", C,
     [P(bnd("f:claim-1", "b2") + "/value", {"fact": "f:claim-1"})],
     schema_patch=[P(usage("claims", "claim") + "/fillers", [{"fact": ["born_in", "claims"]}])],
     source="R01 V28; critique GL-01, SEM-03")
case("status_ref points at a record of the wrong relation", "D", "KHG-D010", C,
     [P(f"/records/{rec('f:born-skłodowska-kraków')}/status_ref", "f:king-14")], source="R01 V37")
case("status_ref names no record (dangling)", "D", "KHG-D010", C,
     [P(f"/records/{rec('f:reg-1')}/status", "disputed"), A(f"/records/{rec('f:reg-1')}/status_ref", "m:none")],
     source="critique SEM-18 (6)")
case("superseded fact not named by its supersession record", "D", "KHG-D010", C,
     [P(bnd("m:sup-1", "b2") + "/value", {"fact": "f:born-scribe"})], source="F8")
case("supersession cycle", "D", "KHG-D012", C,
     [A("/records/-", {"kind": "hyperedge", "id": "m:sup-2", "relation": "khg:supersedes", "status": "asserted",
                       "reason": "correction",
                       "bindings": [{"bid": "b1", "role": "khg:superseding", "value": {"fact": "f:born-skłodowska-kraków"}},
                                    {"bid": "b2", "role": "khg:superseded", "value": {"fact": "f:born-skłodowska-warszawa"}}],
                       "evidence": [dict(CUR, supports=["b1", "b2"])]})], source="R01 V37")
case("correction between facts of different relations", "D", "KHG-D011", C, [P(bnd("m:sup-1", "b1") + "/value", {"fact": "f:king-14"})],
     source="R01 V37")
case("correction across key digests (the superseding fact is about someone else)", "D", "KHG-D011", C,
     [P(bnd("m:sup-1", "b1") + "/value", {"fact": "f:born-scribe"})], source="critique SEM-18 (5); R01 V37 third clause")
case("reason duplicate between facts with different content keys", "D", "KHG-D011", C,
     [P(f"/records/{rec('m:sup-1')}/reason", "duplicate")], source="critique SEM-18 (4), SEM-20")
case("two asserted facts, same key, overlapping definite valid time", "D", "KHG-D016", C,
     [P(bnd("f:king-14", "b3") + "/value/literal/time", "+1640-01-01T00:00:00Z")], source="R01 V42")
case("two preferred facts on one non-temporal key", "D", "KHG-D016", C,
     [A(f"/records/{rec('f:pop-łódź-2019')}/rank", "preferred"), P(f"/records/{rec('f:pop-łódź-2019-dep')}/rank", "preferred"),
      R(f"/records/{rec('f:pop-łódź-2019-dep')}/rank_reason")], source="critique SEM-18 (1)")
case("a second asserted birthplace for one person", "D", "KHG-D016", C,
     [A("/records/-", {"kind": "hyperedge", "id": "f:born-skłodowska-paris", "relation": "born_in", "status": "asserted",
                       "bindings": [{"bid": "b1", "role": "person", "value": {"entity": "ex:Maria_Skłodowska"}},
                                    {"bid": "b2", "role": "birthplace", "value": {"entity": "ex:Paris"}}],
                       "evidence": [dict(CUR, supports=["b1", "b2"])]})], source="critique SEM-18 (2)")
case("an open-ended holder (end novalue) overlapping its successor", "D", "KHG-D016", C,
     [P(bnd("f:king-13", "b4") + "/value", {"special": "novalue"})], source="critique SEM-18 (3), as ruled by §2.6")
case("stored derived block disagrees with the bindings", "D", "KHG-D015", C,
     [A(f"/records/{rec('f:reg-1')}/derived", {"arity": 4})], source="R01 V15")
case("a candidate inside a store document", "D", "KHG-D017", C, [P(f"/records/{rec('f:reg-1')}/status", "candidate")],
     source="F9; R01 D-18")
case("entity referenced but not declared in a complete document", "D", "KHG-D002", C, [R(f"/records/{rec('ex:HeLa')}")],
     source="R01 V17")
case("one id names both an entity and a hyperedge", "D", "KHG-D007", C, [P(f"/records/{rec('f:reg-1')}/id", "ex:TP53")],
     source="§2.2")
case("header schema sha256 differs from the schema document", "D", "KHG-D009", C,
     [P("/header/schema/sha256", "sha256:" + "0" * 64)], source="R01 V41")
case("a value names an entity that has redirect_to", "D", "KHG-D020", C,
     [A(f"/records/{rec('ex:Paris')}/redirect_to", "ex:Warszawa")], source="critique SEM-16 (R01 I10)")
# ================================================================== D: history containers
k13v2 = rec("f:king-13", HIST, 2)
case("history: version 2 changes a core binding (not a refinement)", "D", "KHG-D013", HI,
     [P(bnd("f:king-13", "b1", HIST, 2) + "/value", {"entity": "ex:LouisXIV"})],
     source="R01 §6.4; A S031; judge probe (Bob for Alice); critique SEM-02")
case("history: version 2 rewrites earlier evidence", "D", "KHG-D013", HI,
     [P(evi("f:king-13", "e1", HIST, 2) + "/source/doc_id", "doc:other")], source="B S013; critique SEM-02")
case("history: a retracted fact asserted again in a later version", "D", "KHG-D014", HI,
     [P("/header/as_at", "2026-10-01T00:00:06Z"),
      A("/records/-", dict(copy.deepcopy(HIST["records"][rec("f:reg-1", HIST, 2)]), version=3, status="asserted",
                           recorded_at="2026-10-01T00:00:06Z")),
      R(f"/records/{len(HIST['records'])}/status_ref")],
     source="B S014; A S030; critique SEM-02")
case("history: a version recorded before the previous version of its id", "D", "KHG-D018", HI,
     [P(f"/records/{k13v2}/recorded_at", "2026-10-01T00:00:01Z")], source="A S032; C C-TX-ORDER; critique SEM-14")
# ================================================================== M: schema documents
case("relation with no roles", "M", "KHG-M001", S, [P(f"/relations/{rel('regulates')}/roles", [])], source="R01 V43")
case("a role used twice in one relation", "M", "KHG-M002", S,
     [A(f"/relations/{rel('regulates')}/roles/-", SCH["relations"][rel('regulates')]["roles"][0])], source="R01 V44")
case("key names a role the relation does not use", "M", "KHG-M003", S, [P(f"/relations/{rel('born_in')}/key/roles", ["holder"])],
     source="R01 V44")
case("key built on a time-slot role", "M", "KHG-M003", S,
     [P(f"/relations/{rel('position_held')}/key/roles", ["start_time"])], source="R04 O12")
case("schema version not semver", "M", "KHG-M004", S, [P("/version", "1.0")], source="R01 V45")
case("unknown entity type in a filler", "M", "KHG-M005", S, [P(usage("regulates", "context") + "/fillers/0/entity", ["Tissue"])],
     source="R01 V46")
case("unknown datatype", "M", "KHG-M006", S, [P(usage("population", "quantity") + "/fillers/0/literal", "float")],
     source="R01 V46")
case("time model names a role that is not a time slot", "M", "KHG-M007", S,
     [P(f"/relations/{rel('position_held')}/time/start", "replaces")], source="§3")
case("time model 'unstated' (the pre-revision name of timeless)", "M", "KHG-M007", S,
     [P(f"/relations/{rel('claims')}/time", {"model": "unstated"})], source="critique SEM-15")
case("user schema declares a relation in the reserved khg: namespace", "M", "KHG-M008", S,
     [P(f"/relations/{rel('regulates')}/id", "khg:regulates")], source="§3")
case("usage of a role missing from the global vocabulary", "M", "KHG-M009", S, [P(usage("regulates", "context") + "/role", "tissue")],
     source="F4")
case("max < min", "M", "KHG-M010", S, [P(usage("co_administration_causes", "agent") + "/max", 1)], source="§3")
case("temporal key on a relation without an interval time model", "M", "KHG-M011", S,
     [P(f"/relations/{rel('born_in')}/key/temporal", True)], source="§2.5")
case("primary names a non-core role", "M", "KHG-M012", S, [P(f"/relations/{rel('position_held')}/primary/object", "replaces")],
     source="R01 V44")
case("duplicate relation id", "M", "KHG-M013", S, [A("/relations/-", SCH["relations"][rel('born_in')])], source="§3")
case("complete on an optional role", "M", "KHG-M014", S, [A(usage("regulates", "context") + "/complete", True)], source="§2.4")
case("constraint severity 'violation' (the enum is error and warning)", "M", "KHG-M015", S,
     [P(f"/relations/{rel('flies_between')}/constraints/0/severity", "violation")], source="critique GL-01 (old MC107)")
case("entity-type parents cycle", "M", "KHG-M016", S, [A("/entity_types/0/parents", ["Person"])], source="§3",
     note="entity type Agent gets parent Person, whose parent is Agent")
case("on_collision supersede on a temporal key", "M", "KHG-M017", S,
     [P(f"/relations/{rel('position_held')}/key/on_collision", "supersede")], source="critique SEM-04")
# ================================================================== Q: queue files (patch paths address /lines/<n>)
qi, ql, qa = line(QUEUE, "queue-item"), line(QUEUE, "log-entry", "l:p2-smoke.000001"), line(QUEUE, "log-entry", "l:p2-smoke.000002")
case("hyperedge item without run.run_id", "Q", "KHG-Q001", Q, [R(f"/lines/{qi}/run/run_id")], source="R01 V47")
case("run without order_id", "Q", "KHG-Q001", Q, [R(f"/lines/{qi}/run/order_id")], source="PLAN §4 (P9 3 runs x 2 orders)")
case("candidate payload without evidence", "Q", "KHG-Q001", Q, [R(f"/lines/{qi}/payload/evidence")], source="R01 V47")
case("candidate payload with status asserted", "Q", "KHG-Q002", Q, [P(f"/lines/{qi}/payload/status", "asserted")], source="F9")
case("candidate payload id outside cand:<queue_id>.<seq>", "Q", "KHG-Q002", Q, [P(f"/lines/{qi}/payload/id", "f:king-14")],
     source="C Q03")
case("unknown item_kind", "Q", "KHG-Q003", Q, [P(f"/lines/{qi}/item_kind", "binding")], source="R01 V48")
case("log action outside the v1 vocabulary (merge comes in 1.1)", "Q", "KHG-Q003", Q, [P(f"/lines/{qa}/action", "merge")],
     source="R01 V48; critique SCOPE-F13")
case("lint entry without findings", "Q", "KHG-Q004", Q, [R(f"/lines/{ql}/findings")], source="R04 M7")
case("state_before does not follow the fold (accept from pending)", "Q", "KHG-Q005", Q, [P(f"/lines/{qa}/state_before", "pending")],
     source="R01 V48; C3-R05")
case("replay recomputes a different decision_hash", "Q", "KHG-Q006", Q, [P(f"/lines/{qa}/decision_hash", "sha256:" + "1" * 64)],
     source="R01 V49; C3-R11")
case("log entry names a missing item", "Q", "KHG-Q007", Q, [P(f"/lines/{qa}/target", "q:p2-smoke.000009")], source="R01 V48")
case("queue file without its header line", "Q", "KHG-Q008", Q, [R("/lines/0")], source="C3-R12")
case("extracted evidence points at another document than the item", "Q", "KHG-Q009", Q,
     [P(f"/lines/{qi}/doc/doc_sha256", "sha256:" + "2" * 64)], source="C Q-DOC-HASH")
case("item keys disagree with the payload", "Q", "KHG-Q010", Q, [P(f"/lines/{qi}/keys/core_key", "sha256:" + "3" * 64)],
     source="A M85; C3-R04")
pl = QUEUE["lines"][qi]["payload"]
e2 = next(j for j, e in enumerate(pl["evidence"]) if e["id"] == "e2")
case("an evidence event_hash disagrees with recomputation from the payload", "Q", "KHG-Q010", Q,
     [P(f"/lines/{qi}/payload/evidence/{e2}/event_hash", "sha256:" + "4" * 64)], source="critique SEM-12 (was a D015 case)")
b5 = next(j for j, b in enumerate(pl["bindings"]) if b["bid"] == "b5")
case("a payload entity that neither item.entities nor the base resolves", "Q", "KHG-Q011", Q,
     [P(f"/lines/{qi}/payload/bindings/{b5}/value", {"entity": "ex:LouisXII"})], source="critique CONS-10")
case("the header's base does not match the base supplied for replay", "Q", "KHG-Q012", Q,
     [P("/lines/0/base/sha256", "sha256:" + "5" * 64)], source="critique G3-ACCEPT-REPLAY")
# ================================================================== I: C4 items (patch paths address /lines/<n>)
mq = line(C4, "c4-memory-question", "mq:king-1700")
rq = line(C4, "c4-retrieval-question")
xd = line(C4, "c4-extraction-doc")
case("unknown C4 item kind", "I", "KHG-I001", I4, [P(f"/lines/{rq}/kind", "c4-trivia-question")], source="§9")
case("retrieval question without its read (where)", "I", "KHG-I002", I4, [R(f"/lines/{rq}/where")], source="critique CONS-04")
case("extraction gold with a role the relation does not allow", "I", "KHG-I003", I4,
     [P(f"/lines/{xd}/gold/0/bindings/3/role", "successor")], source="critique CONS-02")
case("memory question without stale_values", "I", "KHG-I004", I4, [R(f"/lines/{mq}/stale_values")],
     source="R05 §5.5 item 1; D-C5-15")
case("memory question whose gold disagrees with derive_memory_gold", "I", "KHG-I005", I4,
     [P(f"/lines/{mq}/answer/values", [{"entity": "ex:LouisXIII"}])], source="critique SEM-07, CONS-03")


# ================================================================== patch machinery and the mechanical check
def resolve(doc, path):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in path.split("/")[1:]]
    cur = doc
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur, parts[-1]


def apply(doc, patch):
    doc = copy.deepcopy(doc)
    for op in patch or []:
        parent, last = resolve(doc, op["path"])
        if op["op"] == "remove":
            if isinstance(parent, list):
                parent.pop(int(last))
            else:
                del parent[last]
        elif op["op"] == "replace":
            if isinstance(parent, list):
                parent[int(last)] = copy.deepcopy(op["value"])
            else:
                assert last in parent, op["path"]
                parent[last] = copy.deepcopy(op["value"])
        elif op["op"] == "add":
            if isinstance(parent, list):
                parent.append(copy.deepcopy(op["value"])) if last == "-" else parent.insert(int(last), copy.deepcopy(op["value"]))
            else:
                parent[last] = copy.deepcopy(op["value"])
    return doc


IDX_KEYS = {"records": lambda x: x.get("id") if x.get("version") is None else [x.get("id"), x.get("version")],
            "nodes": lambda x: x.get("node"), "edges": lambda x: x.get("edge"),
            "incidences": lambda x: [x.get("edge"), (x.get("attrs") or {}).get("khg-bid")],
            "relations": lambda x: x.get("id"), "lines": lambda x: [x.get("kind"), x.get("qid") or x.get("lid") or x.get("id")],
            "entity_types": lambda x: x.get("id")}


def targets(base_doc, patch):
    """expect_target: what each indexed path of the patch points at in the base."""
    out = {}
    for op in patch or []:
        parts = op["path"].split("/")[1:]
        if len(parts) >= 2 and parts[0] in IDX_KEYS and parts[1].isdigit() and int(parts[1]) < len(base_doc[parts[0]]):
            out[f"/{parts[0]}/{parts[1]}"] = IDX_KEYS[parts[0]](base_doc[parts[0]][int(parts[1])])
    return out


def restamp(doc, kind, sch_doc):
    d = K.digest("khg-schema/1", sch_doc)
    if kind == "c1":
        doc["header"]["schema"]["sha256"] = d
    elif kind == "hif":
        doc["metadata"]["khg-schema-sha256"] = d
    return doc


def run_case(V, c):
    if c["kind"] == "json":
        return V.validate(c["input_text"], "hif", schema_doc=SCH), None
    base = BASES[c["base"]]
    sch = apply(SCH, c.get("schema_patch")) if c.get("schema_patch") else SCH
    doc = apply(base, c.get("patch"))
    if c.get("schema_patch"):
        doc = restamp(doc, c["kind"], sch)
    texts = dict(c.get("doc_text") or {})
    obj = doc["lines"] if c["kind"] in ("queue", "c4") else doc
    if c["kind"] == "relation-schema":
        return V.validate(obj, "relation-schema"), doc
    return V.validate(obj, c["kind"], schema_doc=sch, doc_texts=texts,
                      bases={"p2-smoke-base": load("smoke-base.c1.json")}), doc


for c in cases:
    if c.get("base"):
        t = targets(BASES[c["base"]], c.get("patch"))
        if t:
            c["expect_target"] = t
bad, fast_bad = [], []
with EN.no_network():
    Vj = VP.Validator(EX / "schemas", engine="jsonschema")
    Vf = VP.Validator(EX / "schemas", engine="fastjsonschema")
    # base self-check: every unpatched base validates with no error finding
    for b, kind in KIND.items():
        obj = BASES[b]["lines"] if kind in ("queue", "c4") else BASES[b]
        for V in (Vj, Vf):
            errs = VP.errors(V.validate(obj, kind, schema_doc=None if kind == "relation-schema" else SCH, doc_texts=TEXTS,
                                        bases={"p2-smoke-base": load("smoke-base.c1.json")}, stop="all"))
            if errs:
                bad.append(("BASE", b, V.engine, errs[:2]))
    for c in cases:
        if c.get("base"):
            patched = apply(BASES[c["base"]], c.get("patch"))
            sch_changed = bool(c.get("schema_patch"))
            if patched == BASES[c["base"]] and not sch_changed:
                bad.append((c["id"], "input equals its base"))
                continue
            for pth, want in (c.get("expect_target") or {}).items():
                if targets(BASES[c["base"]], [{"path": pth + "/x"}]).get(pth) != want:
                    bad.append((c["id"], "expect_target"))
        fs, _ = run_case(Vj, c)
        kind = "hif" if c["kind"] == "json" else c["kind"]
        fl = VP.first_layer(fs, kind if kind != "relation-schema" else "relation-schema")
        codes = {f["code"] for f in VP.errors(fs)}
        if fl != c["layer"] or c["code"] not in codes:
            bad.append((c["id"], c["code"], "first layer", fl, "codes", sorted(codes)[:6]))
            continue
        ff, _ = run_case(Vf, c)
        fcodes = {f["code"] for f in VP.errors(ff)}
        if VP.first_layer(ff, kind) != fl or not fcodes <= codes | {c["code"]}:
            fast_bad.append((c["id"], sorted(fcodes), sorted(codes)))
        c["reported"] = sorted(codes)

reg = json.loads((EX / "error-codes.json").read_text(encoding="utf-8"))
active = {x["code"] for x in reg["codes"] if x["status"] == "active" and x["layer"] not in ("L", "F")}
listed = {c["code"] for c in cases}
EXCEPTIONS = {"KHG-D019": "S-PUT-006 (expect is a store call argument, not document content)"}
missing = sorted(active - listed - set(EXCEPTIONS))
out = {"format": "khg-malformed-cases/1.0.0",
       "rule": "a case passes when its first rejecting layer (the earliest code letter, in the input kind's pipeline "
               "order, among the error findings) is the listed layer and the listed code is among the error codes; "
               "patches are RFC 6902 against the named base in design-examples/ (queue and C4 patches address "
               "/lines/<n>); a schema_patch applies to fixture.relation-schema.json and the harness re-stamps the "
               "base's schema digest; expect_target pins what each indexed path points at in the base",
       "pipelines": {"json": "J", "c1": "J V C S D", "hif": "J V H R P D C S", "relation-schema": "J V M",
                     "queue": "J V Q C S D", "c4": "J V I"},
       "harness": {"engine": "jsonschema (full report); fastjsonschema codes must be contained in jsonschema's",
                   "self_checks": ["every patch applies", "the input differs from its base",
                                   "expect_target resolves", "every unpatched base has no error finding"],
                   "context": {"doc_texts": "fixture.doc-texts.json for bases; a case's doc_text only for itself",
                               "queue_base": "smoke-base.c1.json (the queue header's base)"}},
       "coverage_exceptions": EXCEPTIONS,
       "bases": sorted({c["base"] for c in cases if c.get("base")}),
       "count": len(cases), "cases": cases}
(EX / "malformed-cases.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
by = {}
for c in cases:
    by[c["layer"]] = by.get(c["layer"], 0) + 1
print(len(cases), "cases", by)
print("failures:", len(bad), bad[:12])
print("engine containment failures:", len(fast_bad), fast_bad[:8])
print("active codes not listed by any case:", missing)
