"""Builds the P2 gate fixture: relation-type schema + directed and undirected C1 documents."""
import hashlib
import json
import unicodedata
from pathlib import Path

HERE = Path(__file__).parent


def T(time, p):
    return {"literal": {"datatype": "time", "time": time, "precision": p}}


def E(i):
    return {"entity": i}


def doc_hash(text):
    t = unicodedata.normalize("NFC", text)
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


def span(text, quote, **rest):
    t = unicodedata.normalize("NFC", text)
    s = t.index(quote)  # Python str indexes are code points
    return [{"type": "quote", "exact": quote, "prefix": t[max(0, s - 12):s], "suffix": t[s + len(quote):s + len(quote) + 12]},
            {"type": "position", "start": s, "end": s + len(quote)}]


# --------------------------------------------------------------------------------------------
# Relation-type schema (language khg-schema/1.0.0)
# --------------------------------------------------------------------------------------------

def U(role, slot, fillers, mn, mx, **kw):
    u = {"role": role, "slot": slot, "fillers": fillers, "min": mn, "max": mx}
    u.update(kw)
    return u


TIME = [{"literal": "time"}]
SCHEMA = {
    "khg_schema": "khg-schema/1.0.0",
    "id": "p2-gate",
    "version": "1.0.0",
    "label": "P2 gate fixture schema",
    "entity_types": [{"id": t} for t in ["Agent", "Airline", "Airport", "CellLine", "Chemical", "Drug", "Gene", "Outcome",
                                         "Place", "Position", "Reaction", "Station"]]
                    + [{"id": "Person", "parents": ["Agent"]}, {"id": "Organisation", "parents": ["Agent"]}],
    "confidence_scales": [{"id": "llm-0-10", "kind": "bounded", "min": 0, "max": 10,
                           "description": "self-reported extractor score, not a probability"}],
    "roles": [{"id": r} for r in ["regulator", "target", "context", "agent", "effect", "carrier", "stop", "origin",
                                  "destination", "holder", "position", "replaces", "place", "quantity", "person",
                                  "birthplace", "reaction", "catalyst", "claimant", "claim", "station", "name", "code",
                                  "elevation", "opened", "active", "homepage", "location", "spouse"]]
             + [{"id": "start_time", "label": "start time", "mappings": {"wikidata": "P580"}},
                {"id": "end_time", "label": "end time", "mappings": {"wikidata": "P582"}},
                {"id": "point_in_time", "label": "point in time", "mappings": {"wikidata": "P585"}}],
    "relations": [
        {"id": "regulates", "time": {"model": "invariant"},
         "roles": [U("regulator", "core", [{"entity": ["Gene"]}], 1, 1, direction="tail"),
                   U("target", "core", [{"entity": ["Gene"]}], 1, 1, direction="head"),
                   U("context", "qualifier", [{"entity": ["CellLine"]}], 0, 1, direction="tail")]},
        {"id": "co_administration_causes",
         "roles": [U("agent", "core", [{"entity": ["Drug"]}], 2, None, direction="tail"),
                   U("effect", "core", [{"entity": ["Outcome"]}], 1, 1, direction="head")]},
        {"id": "flight_route",
         "roles": [U("carrier", "core", [{"entity": ["Airline"]}], 1, 1, direction="tail"),
                   U("stop", "core", [{"entity": ["Airport"]}], 2, None, ordered=True, complete=True, direction="head")]},
        {"id": "flies_between",
         "roles": [U("carrier", "core", [{"entity": ["Airline"]}], 1, 1),
                   U("origin", "core", [{"entity": ["Airport"]}], 1, 1),
                   U("destination", "core", [{"entity": ["Airport"]}], 1, 1)],
         "constraints": [{"type": "must_differ", "roles": ["origin", "destination"], "severity": "warning"}]},
        {"id": "position_held", "mappings": {"wikidata": "P39"},
         "primary": {"subject": "holder", "object": "position"},
         "time": {"model": "interval", "start": "start_time", "end": "end_time"},
         "key": {"roles": ["position"], "temporal": True, "on_collision": "close_older"},
         "roles": [U("holder", "core", [{"entity": ["Person"]}], 1, 1, direction="tail"),
                   U("position", "core", [{"entity": ["Position"]}], 1, 1, direction="head"),
                   U("start_time", "time", TIME, 0, 1, direction="tail"),
                   U("end_time", "time", TIME, 0, 1, direction="tail"),
                   U("replaces", "qualifier", [{"entity": ["Person"]}], 0, None, direction="tail")]},
        {"id": "married", "time": {"model": "interval", "start": "start_time", "end": "end_time"},
         "roles": [U("spouse", "core", [{"entity": ["Person"]}], 2, 2, complete=True),
                   U("start_time", "time", TIME, 0, 1),
                   U("end_time", "time", TIME, 0, 1)]},
        {"id": "population", "mappings": {"wikidata": "P1082"}, "time": {"model": "invariant"},
         "key": {"roles": ["place", "point_in_time"], "temporal": False, "on_collision": "dispute"},
         "roles": [U("place", "core", [{"entity": ["Place"]}], 1, 1, direction="tail"),
                   U("quantity", "core", [{"literal": "quantity", "units": ["1"]}], 1, 1, direction="head"),
                   U("point_in_time", "qualifier", [{"literal": "time", "precision_min": 9}], 0, 1, direction="tail")]},
        {"id": "station_profile",
         "roles": [U("station", "core", [{"entity": ["Station"]}], 1, 1, direction="tail"),
                   U("name", "qualifier", [{"literal": "lang_string"}], 0, None, direction="head"),
                   U("code", "qualifier", [{"literal": "string"}], 0, 1, direction="head"),
                   U("elevation", "qualifier", [{"literal": "quantity", "units": ["wd:Q11573"]}], 0, 1, direction="head"),
                   U("opened", "qualifier", [{"literal": "time"}], 0, 1, direction="head"),
                   U("active", "qualifier", [{"literal": "boolean"}], 0, 1, direction="head"),
                   U("homepage", "qualifier", [{"literal": "iri"}], 0, 1, direction="head"),
                   U("location", "qualifier", [{"literal": "geo"}], 0, 1, direction="head")]},
        {"id": "born_in", "mappings": {"wikidata": "P19"}, "time": {"model": "invariant"},
         "key": {"roles": ["person"], "temporal": False, "on_collision": "dispute"},
         "roles": [U("person", "core", [{"entity": ["Person"]}], 1, 1, direction="tail"),
                   U("birthplace", "core", [{"entity": ["Place"]}], 1, 1, direction="head")]},
        {"id": "claims", "time": {"model": "invariant"},
         "roles": [U("claimant", "core", [{"entity": ["Agent"]}], 1, 1, direction="tail"),
                   U("claim", "core", [{"fact": ["born_in"]}], 1, 1, direction="head", somevalue=False, novalue=False),
                   U("point_in_time", "qualifier", [{"literal": "time"}], 0, 1, direction="tail")]},
        {"id": "catalysed_by",
         "roles": [U("reaction", "core", [{"entity": ["Reaction"]}], 1, 1, direction="tail"),
                   U("catalyst", "core", [{"entity": ["Chemical"]}], 1, None, direction="head")]},
    ],
}

# --------------------------------------------------------------------------------------------
# Texts used as evidence (NFC); offsets are Unicode code points, half-open
# --------------------------------------------------------------------------------------------

TXT_ROUTE = "🛫 Air Canada flies Toronto → Montréal → Toronto every day."
TXT_COADMIN = "Metformin taken together with insulin can cause hypoglycaemia."
TXT_LOUIS = "Louis XIV succeeded his father Louis XIII as King of France on 14 May 1643."
TXT_CURIE_WRONG = "Maria Skłodowska was born in Kraków."

ACT = {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}


def ev_curated(i="e1", supports=None, doc="doc:curation-notes"):
    e = {"id": i, "type": "curated", "mode": "manual", "source": {"doc_id": doc}}
    if supports:
        e["supports"] = supports
    return e


def ENT(i, types, label):
    return {"kind": "entity", "id": i, "types": types, "label": label}


HDR = lambda did: {"kind": "header", "khg": "khg-record/1.0.0", "document_id": did,
                   "schema": {"id": "p2-gate", "version": "1.0.0", "sha256": None},
                   "snapshot": "current", "complete": True}

DIRECTED = {
    "header": HDR("p2-gate-fixture-directed"),
    "records": [
        ENT("ex:TP53", ["Gene"], "TP53"), ENT("ex:HeLa", ["CellLine"], "HeLa"),
        ENT("ex:metformin", ["Drug"], "metformin"), ENT("ex:insulin", ["Drug"], "insulin"),
        ENT("ex:hypoglycaemia", ["Outcome"], "hypoglycaemia"),
        ENT("ex:AirCanada", ["Airline"], "Air Canada"), ENT("ex:YYZ", ["Airport"], "Toronto Pearson"),
        ENT("ex:YUL", ["Airport"], "Montréal–Trudeau"),
        ENT("ex:LouisXIII", ["Person"], "Louis XIII"), ENT("ex:LouisXIV", ["Person"], "Louis XIV"),
        ENT("ex:KingOfFrance", ["Position"], "King of France"), ENT("ex:Paris", ["Place"], "Paris"),
        ENT("ex:Chronicler_Ødegård", ["Person"], "Ødegård the chronicler"),
        ENT("ex:Łódź", ["Place"], "Łódź"), ENT("ex:東京駅", ["Station"], "Tokyo Station"),
        ENT("ex:Maria_Skłodowska", ["Person"], "Maria Skłodowska"), ENT("ex:Kraków", ["Place"], "Kraków"),
        ENT("ex:Warszawa", ["Place"], "Warszawa"), ENT("ex:anonymous_scribe", ["Person"], "an anonymous scribe"),
        ENT("ex:R-hydrolysis-7", ["Reaction"], "hydrolysis reaction 7"),
        # node in two roles, tail and head, plus a qualifier
        {"kind": "fact", "id": "f:reg-1", "relation": "regulates", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "context", "value": E("ex:HeLa")},
                      {"bid": "b2", "role": "regulator", "value": E("ex:TP53")},
                      {"bid": "b3", "role": "target", "value": E("ex:TP53")}],
         "evidence": [ev_curated(doc="doc:review-p53")]},
        # repeated unordered role; evidence on a subset of bindings
        {"kind": "fact", "id": "f:coadmin-1", "relation": "co_administration_causes", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "agent", "value": E("ex:insulin")},
                      {"bid": "b2", "role": "agent", "value": E("ex:metformin")},
                      {"bid": "b3", "role": "effect", "value": E("ex:hypoglycaemia")}],
         "evidence": [{"id": "e1", "type": "extracted", "mode": "automatic",
                       "source": {"doc_id": "doc:coadmin-note", "doc_sha256": doc_hash(TXT_COADMIN)},
                       "selectors": span(TXT_COADMIN, "Metformin taken together with insulin can cause hypoglycaemia"),
                       "activity": ACT, "confidence": {"value": 7.5, "scale": "llm-0-10"}},
                      ev_curated("e2", supports=["b1", "b3"], doc="doc:insulin-label")],
         "confidence": {"value": 0.9, "scale": "probability", "scorer": {"name": "fixture-belief", "version": "0"}}},
        # ordered complete role with the same node at positions 1 and 3; span over astral text
        {"kind": "fact", "id": "f:route-1", "relation": "flight_route", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "carrier", "value": E("ex:AirCanada")},
                      {"bid": "b2", "role": "stop", "position": 1, "value": E("ex:YYZ")},
                      {"bid": "b3", "role": "stop", "position": 2, "value": E("ex:YUL")},
                      {"bid": "b4", "role": "stop", "position": 3, "value": E("ex:YYZ")}],
         "evidence": [{"id": "e1", "type": "extracted", "mode": "automatic",
                       "source": {"doc_id": "doc:route-note", "doc_sha256": doc_hash(TXT_ROUTE)},
                       "selectors": span(TXT_ROUTE, "Toronto → Montréal → Toronto"), "activity": ACT}],
         "text": TXT_ROUTE},
        # keyed relation, two facts on one key timeline; binding-level evidence
        {"kind": "fact", "id": "f:king-13", "relation": "position_held", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "holder", "value": E("ex:LouisXIII")},
                      {"bid": "b2", "role": "position", "value": E("ex:KingOfFrance")},
                      {"bid": "b3", "role": "start_time", "value": T("+1610-05-14T00:00:00Z", 11)},
                      {"bid": "b4", "role": "end_time", "value": T("+1643-05-14T00:00:00Z", 11)}],
         "evidence": [ev_curated(doc="doc:regnal-list")]},
        {"kind": "fact", "id": "f:king-14", "relation": "position_held", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "holder", "value": E("ex:LouisXIV")},
                      {"bid": "b2", "role": "position", "value": E("ex:KingOfFrance")},
                      {"bid": "b3", "role": "start_time", "value": T("+1643-05-14T00:00:00Z", 11)},
                      {"bid": "b4", "role": "end_time", "value": T("+1715-09-01T00:00:00Z", 11)},
                      {"bid": "b5", "role": "replaces", "value": E("ex:LouisXIII")}],
         "evidence": [ev_curated("e1", supports=["b1", "b2", "b3", "b4"], doc="doc:regnal-list"),
                      {"id": "e2", "type": "extracted", "mode": "automatic",
                       "source": {"doc_id": "doc:louis-bio", "doc_sha256": doc_hash(TXT_LOUIS)},
                       "selectors": span(TXT_LOUIS, "Louis XIV succeeded his father Louis XIII"),
                       "activity": ACT, "supports": ["b1", "b5"]}]},
        # typed literals with precision and units; non-ASCII ids
        {"kind": "fact", "id": "f:pop-łódź-2019", "relation": "population", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "place", "value": E("ex:Łódź")},
                      {"bid": "b2", "role": "quantity", "value": {"literal": {"datatype": "quantity", "amount": "+679941", "unit": "1"}}},
                      {"bid": "b3", "role": "point_in_time", "value": T("+2019-00-00T00:00:00Z", 9)}],
         "evidence": [{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:stat-yearbook-2020"},
                       "reference": [{"role": "point_in_time", "value": T("+2020-00-00T00:00:00Z", 9)}]}]},
        {"kind": "fact", "id": "f:station-東京", "relation": "station_profile", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "station", "value": E("ex:東京駅")},
                      {"bid": "b2", "role": "name", "value": {"literal": {"datatype": "lang_string", "value": "東京駅", "lang": "ja"}}},
                      {"bid": "b3", "role": "name", "value": {"literal": {"datatype": "lang_string", "value": "Tokyo Station", "lang": "en"}}},
                      {"bid": "b4", "role": "code", "value": {"literal": {"datatype": "string", "value": "TYO"}}},
                      {"bid": "b5", "role": "elevation", "value": {"literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573", "lower": "+3", "upper": "+4"}}},
                      {"bid": "b6", "role": "opened", "value": T("+1914-12-20T00:00:00Z", 11)},
                      {"bid": "b7", "role": "active", "value": {"literal": {"datatype": "boolean", "value": True}}},
                      {"bid": "b8", "role": "homepage", "value": {"literal": {"datatype": "iri", "value": "https://www.tokyostationcity.com/"}}},
                      {"bid": "b9", "role": "location", "value": {"literal": {"datatype": "geo", "lat": "+35.6812", "lon": "+139.7671", "precision": "+0.0001", "globe": "wd:Q2"}}}],
         "evidence": [ev_curated(doc="doc:station-guide")]},
        # nesting: an asserted claim about a quoted (not asserted) fact
        {"kind": "fact", "id": "f:born-louis14-paris", "relation": "born_in", "status": "quoted",
         "bindings": [{"bid": "b1", "role": "person", "value": E("ex:LouisXIV")},
                      {"bid": "b2", "role": "birthplace", "value": E("ex:Paris")}]},
        {"kind": "fact", "id": "f:claim-1", "relation": "claims", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "claimant", "value": E("ex:Chronicler_Ødegård")},
                      {"bid": "b2", "role": "claim", "value": {"fact": "f:born-louis14-paris"}},
                      {"bid": "b3", "role": "point_in_time", "value": T("+1700-00-00T00:00:00Z", 9)}],
         "evidence": [ev_curated(doc="doc:chronicle-1700")]},
        # superseded pair (belief revision) with its supersession record
        {"kind": "fact", "id": "f:born-skłodowska-kraków", "relation": "born_in", "status": "superseded", "version": 2,
         "status_ref": "m:sup-1",
         "bindings": [{"bid": "b1", "role": "person", "value": E("ex:Maria_Skłodowska")},
                      {"bid": "b2", "role": "birthplace", "value": E("ex:Kraków")}],
         "evidence": [{"id": "e1", "type": "extracted", "mode": "automatic",
                       "source": {"doc_id": "doc:curie-wrong", "doc_sha256": doc_hash(TXT_CURIE_WRONG)},
                       "selectors": span(TXT_CURIE_WRONG, "Maria Skłodowska was born in Kraków"), "activity": ACT}]},
        {"kind": "fact", "id": "f:born-skłodowska-warszawa", "relation": "born_in", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "person", "value": E("ex:Maria_Skłodowska")},
                      {"bid": "b2", "role": "birthplace", "value": E("ex:Warszawa")}],
         "evidence": [ev_curated(doc="doc:biography")]},
        {"kind": "meta", "id": "m:sup-1", "relation": "khg:supersedes", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "khg:superseding", "value": {"fact": "f:born-skłodowska-warszawa"}},
                      {"bid": "b2", "role": "khg:superseded", "value": {"fact": "f:born-skłodowska-kraków"}}],
         "meta": {"reason": "correction", "note": "birthplace is Warsaw, per the curated biography"},
         "evidence": [ev_curated(doc="doc:biography")]},
        # somevalue and novalue
        {"kind": "fact", "id": "f:born-scribe", "relation": "born_in", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "person", "value": E("ex:anonymous_scribe")},
                      {"bid": "b2", "role": "birthplace", "value": {"special": "somevalue"}}],
         "evidence": [ev_curated(doc="doc:scriptorium-notes")]},
        {"kind": "fact", "id": "f:cat-7", "relation": "catalysed_by", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "reaction", "value": E("ex:R-hydrolysis-7")},
                      {"bid": "b2", "role": "catalyst", "value": {"special": "novalue"}}],
         "evidence": [ev_curated(doc="doc:lab-notebook-7")]},
        # goal with an unbound slot
        {"kind": "goal", "id": "g:who-1774", "relation": "position_held", "status": "open",
         "bindings": [{"bid": "b1", "role": "holder", "value": {"unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}},
                      {"bid": "b2", "role": "position", "value": E("ex:KingOfFrance")},
                      {"bid": "b3", "role": "start_time", "value": T("+1774-05-10T00:00:00Z", 11)}],
         "goal": {"brief": "Who became King of France on 10 May 1774?", "owner": "agent:history-desk"}},
    ],
}

UNDIRECTED = {
    "header": HDR("p2-gate-fixture-undirected"),
    "records": [
        ENT("ex:Maria_Skłodowska", ["Person"], "Maria Skłodowska"), ENT("ex:Pierre_Curie", ["Person"], "Pierre Curie"),
        ENT("ex:AirCanada", ["Airline"], "Air Canada"), ENT("ex:YYZ", ["Airport"], "Toronto Pearson"),
        # symmetric role
        {"kind": "fact", "id": "f:married-curie", "relation": "married", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "spouse", "value": E("ex:Maria_Skłodowska")},
                      {"bid": "b2", "role": "spouse", "value": E("ex:Pierre_Curie")},
                      {"bid": "b3", "role": "start_time", "value": T("+1895-07-26T00:00:00Z", 11)},
                      {"bid": "b4", "role": "end_time", "value": T("+1906-04-19T00:00:00Z", 11)}],
         "evidence": [ev_curated(doc="doc:biography")]},
        # one node in two roles without direction (lint warning must_differ, still valid)
        {"kind": "fact", "id": "f:loop-yyz", "relation": "flies_between", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "carrier", "value": E("ex:AirCanada")},
                      {"bid": "b2", "role": "destination", "value": E("ex:YYZ")},
                      {"bid": "b3", "role": "origin", "value": E("ex:YYZ")}],
         "evidence": [ev_curated(doc="doc:sightseeing-flight")]},
    ],
}

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    from khg_proto import Schema

    sh = Schema(SCHEMA).sha256()
    for d in (DIRECTED, UNDIRECTED):
        d["header"]["schema"]["sha256"] = sh
    (HERE / "p2-gate.schema.json").write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=1))
    (HERE / "fixture-directed.khg.json").write_text(json.dumps(DIRECTED, ensure_ascii=False, indent=1))
    (HERE / "fixture-undirected.khg.json").write_text(json.dumps(UNDIRECTED, ensure_ascii=False, indent=1))
    print("schema sha256", sh)
