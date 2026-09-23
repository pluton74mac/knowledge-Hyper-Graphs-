"""Build the P2 gate fixture (design C): relation-type schema + C1 snapshot container.

Writes gate-schema.json and gate.khg.jsonl next to this file. Deterministic.
"""
from __future__ import annotations

import os
import unicodedata

import c1

HERE = os.path.dirname(os.path.abspath(__file__))
T0 = "2026-09-23T10:00:00Z"
T1 = "2026-09-23T11:00:00Z"
BY = "p2-gate-fixture/1.0.0"


def U(role, slot, fillers, lo, hi, direction=None, ordered=False):
    u = {"role": role, "slot": slot, "fillers": fillers, "min": lo, "max": hi}
    if ordered:
        u["ordered"] = True
    if direction:
        u["direction"] = direction
    return u


E = lambda *ts: {"entity_types": list(ts)}          # noqa: E731
D = lambda *ds, **kw: {"datatypes": list(ds), **kw}  # noqa: E731

SCHEMA = {
    "kind": "relation-schema",
    "format": c1.SCHEMA_FORMAT,
    "id": "p2-gate",
    "version": "1.0.0",
    "label": "P2 gate fixture schema",
    "entity_types": [{"id": "Thing", "label": "thing"}] + [
        {"id": t, "label": l, "parents": [p]} for t, l, p in [
            ("Drug", "drug", "Thing"), ("Disease", "disease", "Thing"), ("Outcome", "outcome", "Thing"),
            ("Population", "population", "Thing"), ("AdverseEffect", "adverse effect", "Thing"),
            ("Gene", "gene", "Thing"), ("CellLine", "cell line", "Thing"),
            ("Organisation", "organisation", "Thing"), ("Airline", "airline", "Organisation"),
            ("Person", "person", "Thing"), ("Position", "position", "Thing"), ("Airport", "airport", "Thing"),
            ("Place", "place", "Thing"), ("Document", "document", "Thing"), ("Reaction", "reaction", "Thing"),
            ("Chemical", "chemical", "Thing")]],
    "confidence_scales": [
        {"id": "probability", "kind": "probability", "min": 0, "max": 1},
        {"id": "llm-1-10", "kind": "bounded", "min": 1, "max": 10},
    ],
    "time_model": {"from_role": "start_time", "to_role": "end_time", "point_role": "point_in_time"},
    "roles": [{"id": r, "label": r.replace("_", " ")} for r in sorted([
        "treatment", "condition", "dose", "population", "hba1c_change",
        "intervention", "background_therapy", "comparator", "outcome",
        "regulator", "target", "context", "agent", "effect",
        "operator", "stop", "flight_number", "holder", "position", "start_time", "end_time", "point_in_time",
        "place", "count", "publisher", "publication", "title", "url", "open_access", "page_count",
        "partner", "reaction", "catalyst", "organisation", "person", "statement", "report"])],
    "relations": [
        {"id": "treats", "label": "treats", "kind": "fact", "nestable": True,
         "aliases": ["is used to treat"],
         "primary": {"subject": "treatment", "object": "condition"},
         "roles": [U("treatment", "core", E("Drug"), 1, 1, "tail"),
                   U("condition", "core", E("Disease"), 1, 1, "head"),
                   U("dose", "qualifier", D("quantity"), 0, 1),
                   U("population", "qualifier", E("Population"), 0, 1),
                   U("hba1c_change", "qualifier", D("decimal"), 0, 1)]},
        {"id": "compared_in_trial", "label": "compared in trial", "kind": "fact", "nestable": True,
         "roles": [U("intervention", "core", E("Drug"), 1, 1, "tail"),
                   U("background_therapy", "core", E("Drug"), 0, 1, "tail"),
                   U("comparator", "core", E("Drug"), 1, 1, "tail"),
                   U("outcome", "core", E("Outcome"), 1, 1, "head")]},
        {"id": "regulates", "label": "regulates", "kind": "fact",
         "roles": [U("regulator", "core", E("Gene"), 1, 1, "tail"),
                   U("target", "core", E("Gene"), 1, 1, "head"),
                   U("context", "qualifier", E("CellLine"), 0, 1, "tail")]},
        {"id": "co_administration_causes", "label": "co-administration causes", "kind": "fact",
         "roles": [U("agent", "core", E("Drug"), 2, None, "tail"),
                   U("effect", "core", E("AdverseEffect"), 1, 1, "head")]},
        {"id": "flight_route", "label": "flight route", "kind": "fact",
         "roles": [U("operator", "core", E("Airline"), 1, 1),
                   U("stop", "core", E("Airport"), 2, None, ordered=True),
                   U("flight_number", "qualifier", D("string"), 0, 1)]},
        {"id": "position_held", "label": "position held", "kind": "fact",
         "key": {"roles": ["position"], "temporal": True, "on_collision": "close_older"},
         "roles": [U("holder", "core", E("Person"), 1, 1),
                   U("position", "core", E("Position"), 1, 1),
                   U("start_time", "time", D("time"), 0, 1),
                   U("end_time", "time", D("time"), 0, 1)]},
        {"id": "population_count", "label": "population count", "kind": "fact",
         "key": {"roles": ["place"], "temporal": True, "on_collision": "reject"},
         "roles": [U("place", "core", E("Place"), 1, 1),
                   U("count", "core", D("quantity", units=["1"]), 1, 1),
                   U("point_in_time", "time", D("time", precisions=["year", "month", "day"]), 1, 1)]},
        {"id": "publishes", "label": "publishes", "kind": "fact",
         "roles": [U("publisher", "core", E("Organisation"), 1, 1),
                   U("publication", "core", E("Document"), 1, 1),
                   U("title", "qualifier", D("lang-string"), 0, 1),
                   U("url", "qualifier", D("iri"), 0, 1),
                   U("open_access", "qualifier", D("boolean"), 0, 1),
                   U("page_count", "qualifier", D("integer"), 0, 1)]},
        {"id": "married", "label": "married", "kind": "fact",
         "constraints": [{"type": "must_differ", "roles": ["partner"]}],
         "roles": [U("partner", "core", E("Person"), 2, 2),
                   U("start_time", "time", D("time"), 0, 1)]},
        {"id": "catalysed_by", "label": "catalysed by", "kind": "fact",
         "roles": [U("reaction", "core", E("Reaction"), 1, 1),
                   U("catalyst", "core", E("Chemical"), 1, None)]},
        {"id": "chief_executive", "label": "chief executive", "kind": "fact",
         "key": {"roles": ["organisation"], "temporal": True, "on_collision": "supersede"},
         "roles": [U("organisation", "core", E("Organisation"), 1, 1, "tail"),
                   U("person", "core", E("Person"), 1, 1, "head")]},
        {"id": "reported_in", "label": "reported in", "kind": "meta",
         "roles": [U("statement", "core", {"hyperedge": {"relations": ["compared_in_trial", "treats"]}}, 1, 1, "head"),
                   U("report", "core", E("Document"), 1, 1, "tail")]},
    ],
}

ENTITIES = [
    ("drug:metformin", ["Drug"], "metformin"), ("drug:insulin", ["Drug"], "insulin"),
    ("disease:T2DM", ["Disease"], "type 2 diabetes mellitus"),
    ("disease:T1DM", ["Disease"], "type 1 diabetes mellitus"),
    ("outcome:HbA1c", ["Outcome"], "glycated haemoglobin (HbA1c)"),
    ("pop:adults", ["Population"], "adults"), ("effect:hypoglycaemia", ["AdverseEffect"], "hypoglycaemia"),
    ("gene:TP53", ["Gene"], "TP53"), ("cell:HeLa", ["CellLine"], "HeLa"),
    ("x:air-canada", ["Airline"], "Air Canada"), ("x:YYZ", ["Airport"], "Toronto Pearson"),
    ("x:ORD", ["Airport"], "Chicago O'Hare"), ("x:Louis_XIV", ["Person"], "Louis XIV"),
    ("x:Roi_de_France", ["Position"], "roi de France"), ("x:Zürich", ["Place"], "Zürich"),
    ("org:ADA", ["Organisation"], "American Diabetes Association"),
    ("doc:soc-2024", ["Document"], "Standards of Care in Diabetes—2024"),
    ("doc:trial-report-1998", ["Document"], "Trial report (1998)"),
    ("x:Zoë", ["Person"], "Zoë"), ("x:R1", ["Reaction"], "reaction R1"),
    ("org:Acme", ["Organisation"], "Acme Corp."), ("x:Alice", ["Person"], "Alice"), ("x:Bob", ["Person"], "Bob"),
    ("x:Москва", ["Place"], "Москва"),   # isolated: no fact uses it (exercises isolated-node export)
]

DOC_SOC = ("Metformin is the preferred initial pharmacologic agent for the treatment of type 2 diabetes "
           "in adults. The usual starting dose is 500 mg once or twice daily.")
DOC_ZH = "Die Stadt Zürich zählte Ende 2023 443 037 Einwohnerinnen und Einwohner."


def ent(i):
    return {"entity": i}


def lit(lx, dt, **kw):
    return {"literal": lx, "datatype": dt, **kw}


def B(bid, role, value, position=None):
    b = {"bid": bid, "role": role, "value": value}
    if position is not None:
        b["position"] = position
    return b


def sel(text, exact):
    text = unicodedata.normalize("NFC", text)
    start = text.index(exact)
    return [{"type": "quote", "exact": exact}, {"type": "position", "start": start, "end": start + len(exact)}]


def curated(eid, doc, agent="curator:reviewer-1"):
    return {"eid": eid, "type": "curated", "mode": "manual", "source": {"doc": doc},
            "activity": {"agent": agent}}


def H(i, relation, bindings, *, status="asserted", evidence=None, version=1, at=T0, change=None, **extra):
    r = {"kind": "hyperedge", "id": i, "version": version, "recorded_at": at, "recorded_by": BY,
         "change": change or {"op": "put"}, "relation": relation, "status": status, "bindings": bindings}
    if evidence is not None:
        r["evidence"] = evidence
    r.update(extra)
    return r


def build():
    schema = c1.Schema(SCHEMA)
    soc_sha = c1.sha256_text(DOC_SOC)
    zh_sha = c1.sha256_text(DOC_ZH)
    hyperedges = [
        H("khg:f01-treats", "treats",
          [B("b1", "treatment", ent("drug:metformin")), B("b2", "condition", ent("disease:T2DM")),
           B("b3", "dose", lit("500", "quantity", unit="wd:Q3241121")),
           B("b4", "population", ent("pop:adults")), B("b5", "hba1c_change", lit("-1.12", "decimal"))],
          valid_time={"from": "2024-01-01"}, confidence={"value": 0.95, "scale": "probability"},
          evidence=[
              {"eid": "ev1", "type": "extracted", "mode": "automatic",
               "source": {"doc": "doc:soc-2024", "doc_sha256": soc_sha},
               "selectors": sel(DOC_SOC, "Metformin is the preferred initial pharmacologic agent for the "
                                         "treatment of type 2 diabetes in adults."),
               "activity": {"agent": "p9-extractor/0.1.0", "model": "model-y/2026-08", "run": "r1",
                            "prompt": "treats-skill/1.2.0", "params": {"seed": 13, "temperature": 0}},
               "confidence": {"value": 0.9, "scale": "probability"}},
              {"eid": "ev2", "type": "curated", "mode": "manual",
               "source": {"doc": "doc:soc-2024", "doc_sha256": soc_sha},
               "selectors": sel(DOC_SOC, "The usual starting dose is 500 mg"),
               "activity": {"agent": "curator:reviewer-1"}, "binding_refs": ["b3"]}]),
        H("khg:f02-trial", "compared_in_trial",
          [B("b1", "intervention", ent("drug:metformin")), B("b2", "background_therapy", ent("drug:metformin")),
           B("b3", "comparator", ent("drug:insulin")), B("b4", "outcome", ent("outcome:HbA1c"))],
          evidence=[curated("ev1", "doc:trial-report-1998")]),
        H("khg:f03-regulates", "regulates",
          [B("b1", "regulator", ent("gene:TP53")), B("b2", "target", ent("gene:TP53")),
           B("b3", "context", ent("cell:HeLa"))],
          evidence=[curated("ev1", "doc:tp53-review")]),
        H("khg:f04-coadmin", "co_administration_causes",
          [B("b1", "agent", ent("drug:metformin")), B("b2", "agent", ent("drug:insulin")),
           B("b3", "effect", ent("effect:hypoglycaemia"))],
          confidence={"value": 7, "scale": "llm-1-10"},
          evidence=[curated("ev1", "doc:soc-2024")]),
        H("khg:f05-route", "flight_route",
          [B("b1", "operator", ent("x:air-canada")), B("b2", "stop", ent("x:YYZ"), 0),
           B("b3", "stop", ent("x:ORD"), 1), B("b4", "stop", ent("x:YYZ"), 2),
           B("b5", "flight_number", lit("AC 857", "string"))],
          evidence=[curated("ev1", "doc:timetable-2026")]),
        H("khg:f06-louis", "position_held",
          [B("b1", "holder", ent("x:Louis_XIV")), B("b2", "position", ent("x:Roi_de_France")),
           B("b3", "start_time", lit("1643-05-14", "time", precision="day")),
           B("b4", "end_time", lit("1715-09-01", "time", precision="day"))],
          evidence=[curated("ev1", "doc:encyclopaedia")]),
        H("khg:f07-zurich", "population_count",
          [B("b1", "place", ent("x:Zürich")),
           B("b2", "count", lit("443037", "quantity", unit="1", lower="443000", upper="443100")),
           B("b3", "point_in_time", lit("2023", "time", precision="year"))],
          rank="preferred",
          evidence=[
              {"eid": "ev1", "type": "imported", "mode": "automatic", "source": {"doc": "wd:Q72"},
               "reference": [{"prop": "wd:P248", "value": ent("x:stat-zurich-2023")},
                             {"prop": "wd:P813", "value": lit("2026-09-20", "time", precision="day")}],
               "activity": {"agent": "p3a-builder/0.1.0", "run": "dump-2026-09-15"}},
              {"eid": "ev2", "type": "extracted", "mode": "automatic",
               "source": {"doc": "doc:zh-stat-2023", "doc_sha256": zh_sha},
               "selectors": sel(DOC_ZH, "Zürich zählte Ende 2023 443 037"),
               "activity": {"agent": "p9-extractor/0.1.0", "model": "model-y/2026-08", "run": "r1"}}]),
        H("khg:f08-publishes", "publishes",
          [B("b1", "publisher", ent("org:ADA")), B("b2", "publication", ent("doc:soc-2024")),
           B("b3", "title", lit("Standards of Care in Diabetes—2024", "lang-string", lang="en")),
           B("b4", "url", lit("https://diabetesjournals.org/care/issue/47/Supplement_1", "iri")),
           B("b5", "open_access", lit("true", "boolean")), B("b6", "page_count", lit("320", "integer"))],
          evidence=[curated("ev1", "doc:soc-2024")]),
        H("khg:f09-married", "married",
          [B("b1", "partner", ent("x:Zoë")), B("b2", "partner", {"special": "somevalue"}),
           B("b3", "start_time", lit("1990", "time", precision="year"))],
          rank="deprecated", rank_reason="wd:Q25895909",
          evidence=[curated("ev1", "doc:register-extract")]),
        H("khg:f10-catalysis", "catalysed_by",
          [B("b1", "reaction", ent("x:R1")), B("b2", "catalyst", {"special": "novalue"})],
          evidence=[curated("ev1", "doc:lab-notebook-7")]),
        H("khg:f11-ceo-alice", "chief_executive",
          [B("b1", "organisation", ent("org:Acme")), B("b2", "person", ent("x:Alice"))],
          status="superseded", version=2, at=T1, change={"op": "supersede", "ref": "khg:s01"},
          superseded_by=["khg:f12-ceo-bob"], valid_time={"from": "2019-01-01"},
          evidence=[curated("ev1", "doc:acme-pr-2019")]),
        H("khg:f12-ceo-bob", "chief_executive",
          [B("b1", "organisation", ent("org:Acme")), B("b2", "person", ent("x:Bob"))],
          at=T1, valid_time={"from": "2019-01-01"},
          evidence=[curated("ev1", "doc:acme-pr-2021")]),
        H("khg:f13-reported", "reported_in",
          [B("b1", "statement", {"hyperedge": "khg:f02-trial"}), B("b2", "report", ent("doc:trial-report-1998"))],
          evidence=[curated("ev1", "doc:trial-report-1998")]),
        H("khg:f14-goal", "treats",
          [B("b1", "treatment", {"special": "unbound", "expects": {"entity_types": ["Drug"]}}),
           B("b2", "condition", ent("disease:T1DM"))],
          status="goal"),
    ]
    hyperedges = [c1.normalise(h, schema) for h in hyperedges]
    supersessions = [{
        "kind": "supersession", "id": "khg:s01", "superseded": "khg:f11-ceo-alice",
        "superseding": "khg:f12-ceo-bob", "reason": "incorrect",
        "reason_detail": "the 2019 press release named the wrong person; corrected in 2021",
        "recorded_at": T1, "recorded_by": BY,
        "evidence": [curated("ev1", "doc:acme-pr-2021")]}]
    entities = [{"kind": "entity", "id": i, "types": t, "label": l} for i, t, l in ENTITIES]
    schema_sha = c1.sha256_hex(SCHEMA)
    header = {"kind": "header", "format": c1.RECORD_FORMAT, "content": "snapshot", "as_at": "2026-09-23T12:00:00Z",
              "created_at": "2026-09-23T12:00:00Z", "created_by": BY,
              "title": "P2 gate fixture (adversarial)",
              "schemas": [{"id": "p2-gate", "version": "1.0.0", "sha256": schema_sha}]}
    records = ([header, SCHEMA] + sorted(entities, key=lambda r: r["id"])
               + sorted(hyperedges, key=lambda r: (r["id"], r["version"]))
               + sorted(supersessions, key=lambda r: r["id"]))
    return records


if __name__ == "__main__":
    recs = build()
    c1.dump_jsonl(recs, os.path.join(HERE, "gate.khg.jsonl"))
    import json
    with open(os.path.join(HERE, "gate-schema.json"), "w", encoding="utf-8") as f:
        json.dump(SCHEMA, f, ensure_ascii=False, indent=1)
    print(len(recs), "records written")
