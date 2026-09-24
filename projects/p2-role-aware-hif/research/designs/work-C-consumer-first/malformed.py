"""Malformed-case harness for design C, section 8. Each case = minimal mutation of the valid gate fixture.

The layered validator: L0 strict JSON -> L1 vendored HIF schema (HIF inputs) -> L2 profile / record / meta-schema
(draft-07, jsonschema) -> L3 semantic (Python). A case passes the harness when the FIRST rejecting layer is
the expected one and its codes include the expected code.
"""
from __future__ import annotations

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jsonschema  # noqa: E402
from referencing import Registry, Resource  # noqa: E402

import c1  # noqa: E402
import hif_codec  # noqa: E402
import semantic  # noqa: E402

VENDORED = "/home/user/knowledge-Hyper-Graphs-/projects/p2-role-aware-hif/research/probes/hif-schema/hif_schema_v0.1.0.json"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


HIF = load(VENDORED)
PROFILE = load(os.path.join(HERE, "khg-hif-1.0.0.schema.json"))
REC = load(os.path.join(HERE, "khg-record-1.0.0.schema.json"))
META = load(os.path.join(HERE, "khg-relation-schema-1.0.0.schema.json"))
REG = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))
V = {"H": jsonschema.Draft7Validator(HIF), "P": jsonschema.Draft7Validator(PROFILE, registry=REG),
     "R": jsonschema.Draft7Validator(REC), "D": jsonschema.Draft7Validator(META)}


# ---------------------------------------------------------------- L0 strict JSON
def strict_parse(text: str):
    def bad(c):
        raise ValueError("J-NAN")

    def pairs(ps):
        d = {}
        for k, v in ps:
            if k in d:
                raise ValueError("J-DUP-KEY")
            d[k] = v
        return d
    if text.strip() == "":
        raise ValueError("J-PARSE")
    try:
        obj = json.loads(text, parse_constant=bad, object_pairs_hook=pairs)
    except ValueError as e:
        if str(e) in ("J-NAN", "J-DUP-KEY"):
            raise
        raise ValueError("J-PARSE")
    if _has_lone_surrogate(obj):
        raise ValueError("J-SURROGATE")
    if not isinstance(obj, dict):
        raise ValueError("J-NOT-OBJECT")
    return obj


def _has_lone_surrogate(x):
    if isinstance(x, str):
        return any(0xD800 <= ord(ch) <= 0xDFFF for ch in x)
    if isinstance(x, dict):
        return any(_has_lone_surrogate(k) or _has_lone_surrogate(v) for k, v in x.items())
    if isinstance(x, list):
        return any(_has_lone_surrogate(v) for v in x)
    return False


ROOTS = {"H": HIF, "P": PROFILE, "R": REC, "D": META}


def schema_codes(layer, doc):
    """Error -> code: the LAST x-khg-code met while walking the error's absolute schema path from the root
    (following local and registered $refs). Context errors (oneOf/anyOf branches) are walked too; the most
    specific code wins. Without any annotation the code is <layer>-SCHEMA."""
    out = []
    for e in V[layer].iter_errors(doc):
        codes = [c for c in (_walk(ROOTS[layer], x) for x in _leaves(e)) if c]
        out.extend(codes or [f"{layer}-SCHEMA"])
    return sorted(set(out))


def _leaves(e):
    if not e.context:
        return [e]
    out = []
    for c in e.context:
        out.extend(_leaves(c))
    return out + [e]


def _deref(root, cur):
    while isinstance(cur, dict) and "$ref" in cur:
        ref = cur["$ref"]
        if ref.startswith("#/"):
            nxt = root
            for part in ref[2:].split("/"):
                nxt = nxt[part]
            cur = nxt
        elif ref == HIF["$id"]:
            return None  # errors inside the vendored HIF schema carry no khg code
        else:
            return None
    return cur


def _walk(root, e):
    """jsonschema omits $ref from absolute_schema_path and continues inside the target: dereference first."""
    cur, code = root, None
    for tok in e.absolute_schema_path:
        cur = _deref(root, cur)
        if cur is None:
            return code
        if isinstance(cur, dict) and "x-khg-code" in cur:
            code = cur["x-khg-code"]
        try:
            cur = cur[tok]
        except (KeyError, IndexError, TypeError):
            return code
    cur = _deref(root, cur)
    if isinstance(cur, dict) and "x-khg-code" in cur:
        code = cur["x-khg-code"]
    return code


def validate_hif_text(text):
    try:
        doc = strict_parse(text)
    except ValueError as e:
        return "L0", [str(e)]
    h = schema_codes("H", doc)
    if h:
        return "L1", ["H-SCHEMA"] + h
    p = schema_codes("P", doc)
    if p:
        return "L2", p
    try:
        recs = hif_codec.from_hif(doc)
    except hif_codec.ImportError_ as e:
        return "L3", [str(e).split()[0]]
    except KeyError as e:
        return "L3", [f"P-MISSING-{e}"]
    f = [x["code"] for x in semantic.check_container(recs) if x["severity"] == "error"]
    return ("L3", sorted(set(f))) if f else ("ok", [])


def validate_container_lines(lines):
    recs = []
    for ln in lines:
        try:
            recs.append(strict_parse(ln))
        except ValueError as e:
            return "L0", [str(e)]
    codes = []
    for r in recs:
        codes += schema_codes("D" if r.get("kind") == "relation-schema" else "R", r)
    if codes:
        return "L2", sorted(set(codes))
    f = [x["code"] for x in semantic.check_container(recs) if x["severity"] == "error"]
    return ("L3", sorted(set(f))) if f else ("ok", [])


# ---------------------------------------------------------------- fixture access
BASE = c1.load_jsonl(os.path.join(HERE, "gate.khg.jsonl"))
BASE_HIF = hif_codec.to_hif(BASE)
DIRECTED_HIF = hif_codec.to_hif(BASE, relations={"compared_in_trial", "regulates", "co_administration_causes",
                                                  "chief_executive", "reported_in"})


def hif_case(mut, base=None):
    d = copy.deepcopy(base or BASE_HIF)
    r = mut(d)
    return r if isinstance(r, str) else json.dumps(d if r is None else r, ensure_ascii=False)


def c1_case(mut, renormalise=False):
    recs = copy.deepcopy(BASE)
    out = mut(recs)
    recs = recs if out is None else out
    return [c1.cjson(r) for r in recs]


def rec(recs, i):
    return next(r for r in recs if r.get("id") == i)


def schema_rec(recs):
    return next(r for r in recs if r["kind"] == "relation-schema")


def inc(d, edge, bid=None, role=None):
    return next(i for i in d["incidences"] if i["edge"] == edge and
                (bid is None or i["attrs"].get("khg-bid") == bid) and (role is None or i["attrs"]["role"] == role))


def resign_schema(recs):
    """After editing the schema record, update the header's sha256 so only the intended defect remains."""
    s = schema_rec(recs)
    recs[0]["schemas"][0]["sha256"] = c1.sha256_hex(s)
    return recs


def renorm(recs, ids):
    S = c1.Schema(schema_rec(recs))
    for k, r in enumerate(recs):
        if r.get("id") in ids:
            for b in r["bindings"]:
                b.pop("slot", None)
                if (r["relation"], b["role"]) in S.usage:
                    b.pop("direction", None)
            for f in ("arity", "keys", "valid_time"):
                if f == "valid_time" and r["relation"] in ("chief_executive", "treats"):
                    continue
                r.pop(f, None)
            for e in r.get("evidence", []):
                e.pop("event_hash", None)
            try:
                recs[k] = c1.normalise(r, S)
            except (KeyError, ValueError):
                pass
    return recs


def setb(r, _bid, **kw):
    b = next(b for b in r["bindings"] if b["bid"] == _bid)
    b.update(kw)
    return b


CASES = []


def case(cid, kind, expect_layer, expect_code, src, what):
    CASES.append((cid, kind, expect_layer, expect_code, src, what))


# ---------------- HIF inputs (import path of the khg-hif profile) ----------------
case("M01", "hif", "L0", "J-PARSE", lambda: "", "zero-byte file")
case("M02", "hif", "L0", "J-NAN", lambda: hif_case(lambda d: json.dumps(d).replace(
    '"khg-slot": "core"', '"khg-slot": "core", "x": NaN', 1)), "NaN literal in attrs")
case("M03", "hif", "L0", "J-DUP-KEY", lambda: hif_case(lambda d: json.dumps(d, ensure_ascii=False).replace(
    '"role": "condition"', '"role": "condition", "role": "treatment"', 1)), "duplicate key inside one attrs object")
case("M04", "hif", "L0", "J-SURROGATE", lambda: hif_case(lambda d: json.dumps(d).replace(
    '"label": "adults"', '"label": "adults\\ud800"', 1)), "lone UTF-16 surrogate escape in a string")
case("M05", "hif", "L1", "H-SCHEMA", lambda: hif_case(lambda d: d.pop("incidences") and None), "no incidences key")
case("M06", "hif", "L1", "H-SCHEMA", lambda: hif_case(lambda d: d.update({"roles": {}})), "extra top-level key (roles)")
case("M07", "hif", "L1", "H-SCHEMA", lambda: hif_case(lambda d: d.update({"version": "1.0.0"})), "top-level version key")
case("M08", "hif", "L1", "H-SCHEMA", lambda: hif_case(lambda d: d["incidences"][0].update({"role": "x"})),
     "record-level role on an incidence (outside attrs)")
case("M09", "hif", "L1", "H-SCHEMA", lambda: hif_case(lambda d: d["incidences"][0].pop("node") and None),
     "incidence without node")
case("M10", "hif", "L1", "H-SCHEMA", lambda: hif_case(lambda d: d["incidences"][0].update({"direction": "treatment"})),
     "direction outside head/tail")
case("M11", "hif", "L1", "H-SCHEMA", lambda: hif_case(lambda d: d["incidences"][0].update({"node": 1.5})),
     "id of the wrong type (float)")
case("M12", "hif", "L2", "P-ID", lambda: hif_case(lambda d: d["incidences"][0].update({"node": 7})),
     "integer id (valid HIF, outside the profile: ids are strings)")
case("M13", "hif", "L2", "P-NETWORK-TYPE", lambda: hif_case(lambda d: d.update({"network-type": "asc"})),
     "network-type asc")
case("M14", "hif", "L2", "P-METADATA", lambda: hif_case(lambda d: d["metadata"].pop("khg-profile") and None),
     "metadata without the profile declaration")
case("M15", "hif", "L2", "P-METADATA", lambda: hif_case(lambda d: d["metadata"].pop("roles-convention") and None),
     "metadata without the roles-convention declaration")
case("M16", "hif", "L2", "P-ROLE", lambda: hif_case(lambda d: d["incidences"][0]["attrs"].pop("role") and None),
     "incidence without a role")
case("M17", "hif", "L2", "P-ROLE", lambda: hif_case(lambda d: d["incidences"][0]["attrs"].update({"role": ""})),
     "empty role string")
case("M18", "hif", "L2", "P-ROLE", lambda: hif_case(lambda d: d["incidences"][0]["attrs"].update({"role": ["a", "b"]})),
     "role list instead of one role per incidence record")
case("M19", "hif", "L2", "P-METADATA", lambda: hif_case(lambda d: d["metadata"].update({"default_attrs": {}})),
     "metadata.default_attrs (HyperNetX would invent values from it)")
case("M20", "hif", "L2", "P-SCHEMA", lambda: hif_case(lambda d: d["edges"][0].update({"weight": 0.95})),
     "record-level weight (the profile never writes or reads weight)")
case("M21", "hif", "L2", "P-DIRECTED-NO-DIRECTION",
     lambda: hif_case(lambda d: d["incidences"][0].pop("direction") and None, DIRECTED_HIF),
     "directed network, one incidence without direction")
case("M22", "hif", "L2", "P-RELATION", lambda: hif_case(lambda d: d["edges"][0]["attrs"].pop("relation") and None),
     "edge without relation")
case("M23", "hif", "L2", "P-SCHEMA", lambda: hif_case(lambda d: d["edges"][0]["attrs"].update({"confidence": 0.9})),
     "edge attr outside relation/khg-* (confidence written as a bare number)")
case("M24", "hif", "L3", "P-DUP-NODE", lambda: hif_case(lambda d: d["nodes"].append(copy.deepcopy(d["nodes"][0]))),
     "node declared twice")
case("M25", "hif", "L3", "P-DUP-BID", lambda: hif_case(lambda d: d["incidences"].append(copy.deepcopy(d["incidences"][0]))),
     "the same incidence record twice (same edge and khg-bid)")
case("M26", "hif", "L3", "P-UNDECLARED-NODE", lambda: hif_case(lambda d: d["incidences"][0].update({"node": "x:nobody"})),
     "incidence names a node with no node record")
case("M27", "hif", "L3", "P-UNDECLARED-EDGE", lambda: hif_case(lambda d: d["incidences"][0].update({"edge": "x:noedge"})),
     "incidence names an edge with no edge record")
case("M28", "hif", "L3", "P-REF-DANGLING", lambda: hif_case(lambda d: next(
    n for n in d["nodes"] if n["attrs"]["khg-kind"] == "hyperedge-ref")["attrs"].update({"khg-ref": "khg:f99-missing"})),
     "hyperedge-reference node pointing at a missing edge")
case("M29", "hif", "L3", "P-LITERAL-ID", lambda: hif_case(lambda d: next(
    n for n in d["nodes"] if n["attrs"]["khg-kind"] == "literal")["attrs"]["khg-literal"].update({"literal": "501"})),
     "literal node whose id is not the hash of its literal")
case("M30", "hif", "L3", "S-ROLE", lambda: hif_case(lambda d: inc(d, "khg:f02-trial", "b2")["attrs"].update(
    {"role": "treatment"})), "role not allowed for the relation (caught after import)")

# ---------------- C1 containers ----------------
case("M40", "c1", "L2", "R-KIND", lambda: c1_case(lambda rs: rs.append({"kind": "fact", "id": "x:a"})), "unknown record kind")
case("M41", "c1", "L2", "R-SCHEMA", lambda: c1_case(lambda rs: rec(rs, "khg:f02-trial").pop("relation") and None),
     "hyperedge without relation")
case("M42", "c1", "L2", "R-ID", lambda: c1_case(lambda rs: rec(rs, "x:Bob").update({"id": "Bob Smith"})),
     "id without namespace and with a space")
case("M43", "c1", "L3", "R-ID-NFC", lambda: c1_case(lambda rs: rec(rs, "x:Zoë").update({"id": "x:Zoë"})),
     "id not in NFC (decomposed e + diaeresis)")
case("M44", "c1", "L3", "R-ID-RESERVED", lambda: c1_case(lambda rs: rec(rs, "x:Bob").update({"id": "khg-lit:bob"})),
     "id in a reserved namespace")
case("M45", "c1", "L2", "R-VALUE", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f02-trial"), "b1",
                                                                   value={"entity": "drug:metformin", "hyperedge": "khg:f01-treats"}) and None),
     "value with two tags")
case("M46", "c1", "L2", "R-LIT-LEXICAL", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f01-treats"), "b5",
                                                                         value={"literal": "-1.120", "datatype": "decimal"}) and None),
     "decimal not in canonical form (trailing zero)")
case("M47", "c1", "L3", "R-LIT-DATE", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f06-louis"), "b3",
                                                                      value={"literal": "1643-02-30", "datatype": "time", "precision": "day"}) and None),
     "impossible calendar date")
case("M48", "c1", "L2", "R-LIT-LEXICAL", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f07-zurich"), "b3",
                                                                         value={"literal": "2023-05", "datatype": "time", "precision": "year"}) and None),
     "time lexical form finer than its declared precision")
case("M49", "c1", "L2", "R-LIT-UNIT", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f01-treats"), "b3",
                                                                      value={"literal": "500", "datatype": "quantity"}) and None),
     "quantity without unit")
case("M50", "c1", "L2", "R-LIT-LANG", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f08-publishes"), "b3",
                                                                      value={"literal": "x", "datatype": "lang-string"}) and None),
     "lang-string without lang")
case("M51", "c1", "L3", "R-LIT-BOUNDS", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f07-zurich"), "b2",
                                                                        value={"literal": "443037", "datatype": "quantity", "unit": "1", "lower": "443040"}) and None),
     "quantity amount below its lower bound")
case("M52", "c1", "L2", "R-STATUS", lambda: c1_case(lambda rs: rec(rs, "khg:f02-trial").update({"status": "valid"})),
     "status outside the lifecycle")
case("M53", "c1", "L3", "R-DUP-BID", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f02-trial"), "b2", bid="b1") and None),
     "two bindings with the same bid")
case("M54", "c1", "L3", "R-EVIDENCE-REF", lambda: c1_case(lambda rs: rec(rs, "khg:f01-treats")["evidence"][1].update(
    {"binding_refs": ["b9"]})), "evidence on a binding that does not exist")
case("M55", "c1", "L2", "R-EVIDENCE-DOC-HASH", lambda: c1_case(lambda rs: rec(rs, "khg:f01-treats")["evidence"][0]["source"].pop(
    "doc_sha256") and None), "text selectors without the document hash")
case("M56", "c1", "L3", "R-SELECTOR-SPAN", lambda: c1_case(lambda rs: rec(rs, "khg:f07-zurich")["evidence"][1]["selectors"][1].update(
    {"end": 34})), "position span disagrees with the quote length (code points)")
case("M57", "c1", "L3", "R-VALID-TIME", lambda: c1_case(lambda rs: rec(rs, "khg:f12-ceo-bob").update(
    {"valid_time": {"from": "2019-01-01", "to": "2018-01-01"}})), "valid_time.from after valid_time.to")
case("M58", "c1", "L3", "R-DERIVED", lambda: c1_case(lambda rs: rec(rs, "khg:f02-trial")["arity"].update({"arity": 3})),
     "declared arity disagrees with the bindings")
case("M59", "c1", "L3", "R-DERIVED", lambda: c1_case(lambda rs: rec(rs, "khg:f06-louis").update(
    {"valid_time": {"from": "1643-05-14"}})), "valid_time disagrees with the time bindings")
case("M60", "c1", "L3", "S-RELATION", lambda: c1_case(lambda rs: rec(rs, "khg:f02-trial").update({"relation": "tested_in"})),
     "relation not declared in the schema")
case("M61", "c1", "L3", "S-ROLE", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f02-trial"), "b2", role="treatment") and None),
     "role not allowed for the relation")
case("M62", "c1", "L3", "S-ROLE-MIN", lambda: c1_case(lambda rs: renorm(rs, {"khg:f02-trial"}) if rec(rs, "khg:f02-trial")["bindings"].pop(3) else rs),
     "required role missing on an asserted fact")
case("M63", "c1", "L3", "S-ROLE-MAX", lambda: c1_case(lambda rs: renorm(rs, {"khg:f02-trial"}) if rec(rs, "khg:f02-trial")["bindings"].append(
    {"bid": "b9", "role": "outcome", "value": {"entity": "disease:T2DM"}}) is None else rs), "role bound more often than max")
case("M64", "c1", "L3", "S-FILLER", lambda: c1_case(lambda rs: renorm(rs, {"khg:f02-trial"}) if setb(
    rec(rs, "khg:f02-trial"), "b3", value={"entity": "gene:TP53"}) else rs), "entity of the wrong type")
case("M65", "c1", "L3", "S-FILLER", lambda: c1_case(lambda rs: renorm(rs, {"khg:f02-trial"}) if setb(
    rec(rs, "khg:f02-trial"), "b3", value={"literal": "insulin", "datatype": "string"}) else rs), "literal where an entity is expected")
case("M66", "c1", "L3", "S-NO-BINDINGS", lambda: c1_case(lambda rs: renorm(rs, {"khg:f10-catalysis"}) if rec(
    rs, "khg:f10-catalysis")["bindings"].clear() is None else rs), "hyperedge with no bindings")
case("M67", "c1", "L3", "C-NESTING-CYCLE", lambda: c1_case(lambda rs: renorm(rs, {"khg:f13-reported"}) if setb(
    rec(rs, "khg:f13-reported"), "b1", value={"hyperedge": "khg:f13-reported"}) else rs), "a hyperedge that references itself")
case("M68", "c1", "L3", "S-NESTING", lambda: c1_case(lambda rs: renorm(rs, {"khg:f13-reported"}) if setb(
    rec(rs, "khg:f13-reported"), "b1", value={"hyperedge": "khg:f03-regulates"}) else rs), "reference to a relation that is not nestable")
case("M69", "c1", "L3", "S-UNBOUND", lambda: c1_case(lambda rs: rec(rs, "khg:f14-goal").update(
    {"status": "asserted", "evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:x"},
                                         "activity": {"agent": "a"}}]})), "unbound value outside a goal")
case("M70", "c1", "L3", "S-NOVALUE-MIXED", lambda: c1_case(lambda rs: renorm(rs, {"khg:f10-catalysis"}) if rec(
    rs, "khg:f10-catalysis")["bindings"].append({"bid": "b3", "role": "catalyst", "value": {"entity": "x:R1"}}) is None else rs),
     "novalue and a concrete value for the same role")
case("M71", "c1", "L3", "S-EVIDENCE-MISSING", lambda: c1_case(lambda rs: rec(rs, "khg:f02-trial").pop("evidence") and None),
     "asserted fact without evidence")
case("M72", "c1", "L3", "S-DIRECTION", lambda: c1_case(lambda rs: setb(rec(rs, "khg:f03-regulates"), "b2", direction="tail") and None),
     "direction contradicting the role usage")
case("M73", "c1", "L3", "S-POSITION", lambda: c1_case(lambda rs: renorm(rs, {"khg:f05-route"}) if setb(
    rec(rs, "khg:f05-route"), "b4", position=3) else rs), "ordered role with a gap in positions")
case("M74", "c1", "L3", "S-DUP-BINDING", lambda: c1_case(lambda rs: renorm(rs, {"khg:f04-coadmin"}) if setb(
    rec(rs, "khg:f04-coadmin"), "b2", value={"entity": "drug:metformin"}) else rs), "the same filler twice in an unordered role")
case("M75", "c1", "L3", "S-CONSTRAINT", lambda: c1_case(lambda rs: renorm(rs, {"khg:f09-married"}) if setb(
    rec(rs, "khg:f09-married"), "b2", value={"entity": "x:Zoë"}) else rs), "must_differ violated")
case("M76", "c1", "L3", "S-CONFIDENCE", lambda: c1_case(lambda rs: rec(rs, "khg:f04-coadmin")["confidence"].update(
    {"value": 11})), "confidence outside its declared scale")
case("M77", "c1", "L3", "C-SUPERSESSION", lambda: c1_case(lambda rs: rec(rs, "khg:s01").update({"superseded": "khg:f99-missing"})),
     "supersession naming a missing record")
case("M78", "c1", "L3", "C-SUPERSESSION", lambda: c1_case(lambda rs: rs.append(
    {"kind": "supersession", "id": "khg:s02", "superseded": "khg:f12-ceo-bob", "superseding": "khg:f11-ceo-alice",
     "reason": "incorrect", "recorded_at": "2026-09-23T11:30:00Z", "recorded_by": "x",
     "evidence": [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:x"}}]})),
     "supersession cycle")
case("M79", "c1", "L3", "C-SUPERSESSION", lambda: c1_case(lambda rs: rec(rs, "khg:f11-ceo-alice").update(
    {"status": "asserted", "superseded_by": None}) or rec(rs, "khg:f11-ceo-alice").pop("superseded_by") and None),
     "status not superseded although a supersession record names it")
case("M80", "c1", "L3", "C-ENTITY-REF", lambda: c1_case(lambda rs: [r for r in rs if r.get("id") != "cell:HeLa"]),
     "entity reference without an entity record")
case("M81", "c1", "L3", "C-DUP-ID", lambda: c1_case(lambda rs: rs.append(
    {"kind": "entity", "id": "khg:f01-treats", "types": [], "label": "clash"})), "entity and hyperedge share an id")
case("M82", "c1", "L2", "R-FORMAT", lambda: c1_case(lambda rs: rs[0].update({"format": "khg-record/2.0.0"})),
     "container of an unknown major version")
case("M83", "c1", "L3", "C-SCHEMA-REF", lambda: c1_case(lambda rs: rec(rs, "khg:f02-trial").update({"schema": "p2-gate/9.9.9"})),
     "record typed under a schema the container does not carry")
case("M84", "c1", "L3", "C-KEY-COLLISION", lambda: c1_case(lambda rs: rec(rs, "khg:f11-ceo-alice").update(
    {"status": "asserted"}) or rec(rs, "khg:f11-ceo-alice").pop("superseded_by") and
    [r for r in rs if r.get("id") != "khg:s01"]), "two current facts with the same key and overlapping valid time")
case("M85", "c1", "L3", "C-STATUS-CANDIDATE", lambda: c1_case(lambda rs: rec(rs, "khg:f02-trial").update({"status": "candidate"})),
     "candidate status in a store container")

# ---------------- relation-type schema documents ----------------
def sch(mut):
    def f():
        rs = copy.deepcopy(BASE)
        mut(schema_rec(rs))
        resign_schema(rs)
        return [c1.cjson(r) for r in rs]
    return f


case("M90", "c1", "L2", "D-SEMVER", sch(lambda s: s.update({"version": "1.0"})), "schema version not semver")
case("M91", "c1", "L2", "D-NO-ROLES", sch(lambda s: s["relations"][0].update({"roles": []})), "relation type with no roles")
case("M92", "c1", "L3", "D-DUP-USAGE", sch(lambda s: s["relations"][0]["roles"].append(copy.deepcopy(s["relations"][0]["roles"][0]))),
     "role used twice in one relation")
case("M93", "c1", "L3", "D-KEY", sch(lambda s: next(r for r in s["relations"] if r["id"] == "chief_executive")["key"].update(
    {"roles": ["organisation", "ceo"]})), "key names a role the relation does not use")
case("M94", "c1", "L3", "D-KEY", sch(lambda s: next(r for r in s["relations"] if r["id"] == "treats").update(
    {"key": {"roles": ["dose"], "temporal": False, "on_collision": "reject"}})), "key role that is not required")
case("M95", "c1", "L3", "D-PRIMARY", sch(lambda s: next(r for r in s["relations"] if r["id"] == "treats")["primary"].update(
    {"object": "dose"})), "primary names a non-core role")
case("M96", "c1", "L3", "D-TYPE", sch(lambda s: s["relations"][0]["roles"][0]["fillers"].update({"entity_types": ["Medicine"]})),
     "unknown entity type in fillers")
case("M97", "c1", "L3", "D-ROLE-UNDECLARED", sch(lambda s: s["relations"][0]["roles"][0].update({"role": "remedy"})),
     "usage of a role missing from the global vocabulary")
case("M98", "c1", "L3", "D-CARDINALITY", sch(lambda s: s["relations"][0]["roles"][0].update({"min": 2, "max": 1})), "min > max")
case("M99", "c1", "L2", "D-SCHEMA", sch(lambda s: s["relations"][0].update({"kind": "event"})), "relation kind outside the enum")


def run():
    rows, bad = [], 0
    for cid, kind, layer, code, src, what in CASES:
        payload = src()
        got_layer, got = validate_hif_text(payload) if kind == "hif" else validate_container_lines(payload)
        ok = got_layer == layer and code in got
        bad += not ok
        rows.append({"id": cid, "input": kind, "what": what, "expect": f"{layer} {code}",
                     "got": f"{got_layer} {' '.join(got[:4])}", "ok": ok})
    return rows, bad


if __name__ == "__main__":
    rows, bad = run()
    for r in rows:
        print(("ok  " if r["ok"] else "FAIL"), r["id"], r["expect"], "|", r["got"], "|", r["what"])
    print(f"{len(rows) - bad}/{len(rows)} cases rejected as expected")
    with open(os.path.join(HERE, "malformed-results.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
