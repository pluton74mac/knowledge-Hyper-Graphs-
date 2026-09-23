"""Builds the design examples of DESIGN.md (revised): the relation-type schema, the adversarial gate fixture (C1),
its HIF export and directed slice, the derived test vectors, a history container, the smoke-test base, one queue
item and its action-log entries, the extra schemas (cyclic, Wikidata-shaped, R05 test schema) and the migrated
KB sample. C4 items are built by build_c4.py, which needs the prototype store."""
import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import khg_synth as K  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
REPO = HERE.parents[4]


def T(time, p, cal=None):
    lit = {"datatype": "time", "time": time, "precision": p}
    if cal:
        lit["calendar"] = cal
    return {"literal": lit}


def E(i):
    return {"entity": i}


def doc_hash(text):
    t = unicodedata.normalize("NFC", text)
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


def span(text, quote):
    t = unicodedata.normalize("NFC", text)
    s = t.index(quote)  # Python str indexes are code points
    return [{"type": "quote", "exact": quote, "prefix": t[max(0, s - 12):s], "suffix": t[s + len(quote):s + len(quote) + 12]},
            {"type": "position", "start": s, "end": s + len(quote)}]


def U(role, slot, fillers, mn, mx, **kw):
    u = {"role": role, "slot": slot, "fillers": fillers, "min": mn, "max": mx}
    u.update(kw)
    return u


TIME = [{"literal": "time"}]
SCHEMA = {
    "kind": "relation-schema",
    "format": "khg-relation-schema/1.0.0",
    "id": "p2-gate",
    "version": "1.0.0",
    "label": "P2 gate fixture schema",
    "entity_types": [{"id": t} for t in ["Agent", "Airline", "Airport", "CellLine", "Chemical", "Drug", "Gene",
                                         "Outcome", "Place", "Position", "Reaction", "Station"]]
    + [{"id": "Person", "parents": ["Agent"]}, {"id": "Organisation", "parents": ["Agent"]}],
    "confidence_scales": [{"id": "llm-0-10", "kind": "bounded", "min": 0, "max": 10}],
    "roles": [{"id": r} for r in ["regulator", "target", "context", "agent", "effect", "carrier", "stop", "origin",
                                  "destination", "holder", "position", "replaces", "place", "quantity", "person",
                                  "birthplace", "reaction", "catalyst", "claimant", "claim", "station", "name",
                                  "code", "elevation", "opened", "active", "homepage", "location", "spouse"]]
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
                   U("stop", "core", [{"entity": ["Airport"]}], 2, None, ordered=True, complete=True,
                     direction="head")]},
        {"id": "flies_between",
         "constraints": [{"type": "must_differ", "roles": ["origin", "destination"], "severity": "warning"}],
         "roles": [U("carrier", "core", [{"entity": ["Airline"]}], 1, 1),
                   U("origin", "core", [{"entity": ["Airport"]}], 1, 1),
                   U("destination", "core", [{"entity": ["Airport"]}], 1, 1)]},
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
                   U("point_in_time", "qualifier", [{"literal": "time", "precision_min": 9}], 0, 1,
                     direction="tail")]},
        {"id": "station_profile",
         "roles": [U("station", "core", [{"entity": ["Station"]}], 1, 1, direction="tail"),
                   U("name", "qualifier", [{"literal": "lang_string"}], 0, None, direction="head"),
                   U("code", "qualifier", [{"literal": "string"}], 0, 1, direction="head"),
                   U("elevation", "qualifier", [{"literal": "quantity", "units": ["wd:Q11573"]}], 0, 1,
                     direction="head"),
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
                   U("claim", "core", [{"fact": ["born_in"]}], 1, 1, direction="head", somevalue=False,
                     novalue=False),
                   U("point_in_time", "qualifier", [{"literal": "time"}], 0, 1, direction="tail")]},
        {"id": "catalysed_by",
         "roles": [U("reaction", "core", [{"entity": ["Reaction"]}], 1, 1, direction="tail"),
                   U("catalyst", "core", [{"entity": ["Chemical"]}], 1, None, direction="head")]},
    ],
}

TXT_ROUTE = "Note by 𠮷田: Air Canada flies Toronto → Montréal → Toronto every day."
TXT_COADMIN = "Metformin taken together with insulin can cause hypoglycaemia."
TXT_LOUIS = "Louis XIV succeeded his father Louis XIII as King of France on 14 May 1643."
TXT_CURIE_WRONG = "Maria Skłodowska was born in Kraków."
TEXTS = {"doc:route-note": TXT_ROUTE, "doc:coadmin-note": TXT_COADMIN, "doc:louis-bio": TXT_LOUIS,
         "doc:curie-wrong": TXT_CURIE_WRONG}

ACT = {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}


def ev_curated(i="e1", doc="doc:curation-notes", supports=None):
    e = {"id": i, "type": "curated", "mode": "manual", "source": {"doc_id": doc}}
    if supports:
        e["supports"] = supports
    return e


def ENT(i, types, label, **kw):
    r = {"kind": "entity", "id": i, "types": types, "label": label}
    r.update(kw)
    return r


def H(i, rel, bindings, status="asserted", **kw):
    r = {"kind": "hyperedge", "id": i, "relation": rel, "status": status, "bindings": bindings}
    r.update(kw)
    return r


def B(bid, role, value, **kw):
    b = {"bid": bid, "role": role, "value": value}
    b.update(kw)
    return b


HEADER = {"kind": "header", "format": "khg-record/1.0.0", "document_id": "p2-gate-fixture",
          "schema": {"id": "p2-gate", "version": "1.0.0", "sha256": None}, "content": "snapshot",
          "complete": True, "extensions": {"hif:metadata": {"title": "P2 gate fixture (adversarial)"}}}

RECORDS = [
    # a node weight (entity extensions hif:weight becomes the HIF node weight, integral)
    ENT("ex:TP53", ["Gene"], "TP53", extensions={"hif:weight": 3}), ENT("ex:HeLa", ["CellLine"], "HeLa"),
    ENT("ex:metformin", ["Drug"], "metformin"), ENT("ex:insulin", ["Drug"], "insulin"),
    ENT("ex:hypoglycaemia", ["Outcome"], "hypoglycaemia"),
    ENT("ex:AirCanada", ["Airline"], "Air Canada"), ENT("ex:YYZ", ["Airport"], "Toronto Pearson"),
    ENT("ex:YUL", ["Airport"], "Montréal–Trudeau"),
    ENT("ex:LouisXIII", ["Person"], "Louis XIII"), ENT("ex:LouisXIV", ["Person"], "Louis XIV"),
    ENT("ex:KingOfFrance", ["Position"], "King of France"), ENT("ex:Paris", ["Place"], "Paris"),
    ENT("ex:Chronicler_Ødegård", ["Person"], "Ødegård the chronicler"),
    ENT("ex:Łódź", ["Place"], "Łódź"), ENT("ex:東京駅", ["Station"], "Tokyo Station"),
    ENT("ex:Maria_Skłodowska", ["Person"], "Maria Skłodowska"), ENT("ex:Pierre_Curie", ["Person"], "Pierre Curie"),
    ENT("ex:Kraków", ["Place"], "Kraków"), ENT("ex:Warszawa", ["Place"], "Warszawa"),
    ENT("ex:anonymous_scribe", ["Person"], "an anonymous scribe"),
    ENT("ex:R-hydrolysis-7", ["Reaction"], "hydrolysis reaction 7"),
    # an entity no fact references: an isolated HIF node (GL-08)
    ENT("ex:Mazarin", ["Person"], "Jules Mazarin"),
    # a node in two roles (tail and head), plus a qualifier; a non-integral edge weight; nested binding extensions
    H("f:reg-1", "regulates", [B("b1", "context", E("ex:HeLa")), B("b2", "regulator", E("ex:TP53")),
                               B("b3", "target", E("ex:TP53"),
                                 extensions={"ex:curation": {"checked": True, "by": ["curator:a", "curator:b"]}})],
      evidence=[ev_curated(doc="doc:review-p53")], extensions={"hif:weight": 0.5}),
    # repeated interchangeable role; evidence on a subset of bindings; two confidence carriers; an incidence weight
    H("f:coadmin-1", "co_administration_causes",
      [B("b1", "agent", E("ex:insulin"), extensions={"hif:weight": 0.25}), B("b2", "agent", E("ex:metformin")),
       B("b3", "effect", E("ex:hypoglycaemia"))],
      evidence=[{"id": "e1", "type": "extracted", "mode": "automatic",
                 "source": {"doc_id": "doc:coadmin-note", "doc_sha256": doc_hash(TXT_COADMIN)},
                 "selectors": span(TXT_COADMIN, "Metformin taken together with insulin can cause hypoglycaemia"),
                 "activity": ACT, "confidence": {"value": 7.5, "scale": "llm-0-10"}},
                ev_curated("e2", doc="doc:insulin-label", supports=["b1", "b3"])],
      confidence={"value": 0.9, "scale": "probability", "scorer": {"name": "fixture-belief", "version": "0"}}),
    # ordered complete role with the same node at positions 1 and 3; code-point span over astral text; an integral
    # edge weight
    H("f:route-1", "flight_route",
      [B("b1", "carrier", E("ex:AirCanada")), B("b2", "stop", E("ex:YYZ"), position=1),
       B("b3", "stop", E("ex:YUL"), position=2), B("b4", "stop", E("ex:YYZ"), position=3)],
      evidence=[{"id": "e1", "type": "extracted", "mode": "automatic",
                 "source": {"doc_id": "doc:route-note", "doc_sha256": doc_hash(TXT_ROUTE)},
                 "selectors": span(TXT_ROUTE, "Toronto → Montréal → Toronto"), "activity": ACT}],
      source_text=TXT_ROUTE, extensions={"hif:weight": 2}),
    # a temporal key timeline (adjacent periods, day precision), binding-level evidence
    H("f:king-13", "position_held",
      [B("b1", "holder", E("ex:LouisXIII")), B("b2", "position", E("ex:KingOfFrance")),
       B("b3", "start_time", T("+1610-05-14T00:00:00Z", 11)), B("b4", "end_time", T("+1643-05-14T00:00:00Z", 11))],
      evidence=[ev_curated(doc="doc:regnal-list")]),
    H("f:king-14", "position_held",
      [B("b1", "holder", E("ex:LouisXIV")), B("b2", "position", E("ex:KingOfFrance")),
       B("b3", "start_time", T("+1643-05-14T00:00:00Z", 11)), B("b4", "end_time", T("+1715-09-01T00:00:00Z", 11)),
       B("b5", "replaces", E("ex:LouisXIII"))],
      evidence=[ev_curated("e1", doc="doc:regnal-list", supports=["b1", "b2", "b3", "b4"]),
                {"id": "e2", "type": "extracted", "mode": "automatic",
                 "source": {"doc_id": "doc:louis-bio", "doc_sha256": doc_hash(TXT_LOUIS)},
                 "selectors": span(TXT_LOUIS, "Louis XIV succeeded his father Louis XIII"),
                 "activity": ACT, "supports": ["b1", "b5"]}]),
    # quantity with unit, year precision, a non-temporal two-role key; a deprecated alternative on the same key
    H("f:pop-łódź-2019", "population",
      [B("b1", "place", E("ex:Łódź")),
       B("b2", "quantity", {"literal": {"datatype": "quantity", "amount": "+679941", "unit": "1"}}),
       B("b3", "point_in_time", T("+2019-00-00T00:00:00Z", 9))],
      evidence=[{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:stat-yearbook-2020"},
                 "reference": [{"role": "point_in_time", "value": T("+2020-00-00T00:00:00Z", 9)}]}]),
    H("f:pop-łódź-2019-dep", "population",
      [B("b1", "place", E("ex:Łódź")),
       B("b2", "quantity", {"literal": {"datatype": "quantity", "amount": "+685285", "unit": "1"}}),
       B("b3", "point_in_time", T("+2019-00-00T00:00:00Z", 9))],
      rank="deprecated", rank_reason=["wd:Q41755623"],
      evidence=[{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:old-estimate"}}]),
    # every other literal datatype, with precision, units and bounds; non-ASCII ids
    H("f:station-東京", "station_profile",
      [B("b1", "station", E("ex:東京駅")),
       B("b2", "name", {"literal": {"datatype": "lang_string", "value": "東京駅", "lang": "ja"}}),
       B("b3", "name", {"literal": {"datatype": "lang_string", "value": "Tokyo Station", "lang": "en"}}),
       B("b4", "code", {"literal": {"datatype": "string", "value": "TYO"}}),
       B("b5", "elevation", {"literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573",
                                          "lower": "+3", "upper": "+4"}}),
       B("b6", "opened", T("+1914-12-20T00:00:00Z", 11)),
       B("b7", "active", {"literal": {"datatype": "boolean", "value": True}}),
       B("b8", "homepage", {"literal": {"datatype": "iri", "value": "https://www.tokyostationcity.com/"}}),
       B("b9", "location", {"literal": {"datatype": "geo", "lat": "+35.6812", "lon": "+139.7671",
                                         "precision": "+0.0001", "globe": "wd:Q2"}})],
      evidence=[ev_curated(doc="doc:station-guide")]),
    # nesting: an asserted claim about a quoted (not asserted) fact; a Julian-calendar date
    H("f:born-louis14-paris", "born_in", [B("b1", "person", E("ex:LouisXIV")), B("b2", "birthplace", E("ex:Paris"))],
      status="quoted"),
    H("f:claim-1", "claims",
      [B("b1", "claimant", E("ex:Chronicler_Ødegård")), B("b2", "claim", {"fact": "f:born-louis14-paris"}),
       B("b3", "point_in_time", T("+1700-00-00T00:00:00Z", 9, "julian"))],
      evidence=[ev_curated(doc="doc:chronicle-1700")]),
    # a superseded pair (belief revision) and its lifecycle record
    H("f:born-skłodowska-kraków", "born_in",
      [B("b1", "person", E("ex:Maria_Skłodowska")), B("b2", "birthplace", E("ex:Kraków"))],
      status="superseded", status_ref="m:sup-1",
      evidence=[{"id": "e1", "type": "extracted", "mode": "automatic",
                 "source": {"doc_id": "doc:curie-wrong", "doc_sha256": doc_hash(TXT_CURIE_WRONG)},
                 "selectors": span(TXT_CURIE_WRONG, "Maria Skłodowska was born in Kraków"), "activity": ACT}]),
    H("f:born-skłodowska-warszawa", "born_in",
      [B("b1", "person", E("ex:Maria_Skłodowska")), B("b2", "birthplace", E("ex:Warszawa"))],
      evidence=[ev_curated(doc="doc:biography")]),
    H("m:sup-1", "khg:supersedes",
      [B("b1", "khg:superseding", {"fact": "f:born-skłodowska-warszawa"}),
       B("b2", "khg:superseded", {"fact": "f:born-skłodowska-kraków"})],
      reason="correction", note="birthplace is Warsaw, per the curated biography",
      evidence=[ev_curated(doc="doc:biography")]),
    # somevalue and novalue
    H("f:born-scribe", "born_in",
      [B("b1", "person", E("ex:anonymous_scribe")), B("b2", "birthplace", {"special": "somevalue"})],
      evidence=[ev_curated(doc="doc:scriptorium-notes")]),
    H("f:cat-7", "catalysed_by",
      [B("b1", "reaction", E("ex:R-hydrolysis-7")), B("b2", "catalyst", {"special": "novalue"})],
      evidence=[ev_curated(doc="doc:lab-notebook-7")]),
    # a goal with an unbound slot (status goal; no evidence needed)
    H("g:who-1774", "position_held",
      [B("b1", "holder", {"unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}),
       B("b2", "position", E("ex:KingOfFrance")), B("b3", "start_time", T("+1774-05-10T00:00:00Z", 11))],
      status="goal", goal={"brief": "Who became King of France on 10 May 1774?", "owner": "agent:history-desk"}),
    # undirected relations: a symmetric role, and one node in two roles with no direction
    H("f:married-curie", "married",
      [B("b1", "spouse", E("ex:Maria_Skłodowska")), B("b2", "spouse", E("ex:Pierre_Curie")),
       B("b3", "start_time", T("+1895-07-26T00:00:00Z", 11)), B("b4", "end_time", T("+1906-04-19T00:00:00Z", 11))],
      evidence=[ev_curated(doc="doc:biography")]),
    H("f:loop-yyz", "flies_between",
      [B("b1", "carrier", E("ex:AirCanada")), B("b2", "destination", E("ex:YYZ")), B("b3", "origin", E("ex:YYZ"))],
      evidence=[ev_curated(doc="doc:sightseeing-flight")]),
]

DIRECTED_SLICE = ["regulates", "co_administration_causes", "flight_route", "position_held", "population",
                  "station_profile", "born_in", "claims", "catalysed_by"]


def dump(obj, path, compact_records=None):
    """Pretty but compact: one record per line inside the listed arrays."""
    if compact_records is None:
        text = json.dumps(obj, ensure_ascii=False, indent=1)
    else:
        parts = ["{"]
        keys = list(obj.keys())
        for i, k in enumerate(keys):
            v = obj[k]
            sep = "," if i < len(keys) - 1 else ""
            if k in compact_records and isinstance(v, list):
                parts.append(f' "{k}": [')
                for j, x in enumerate(v):
                    parts.append("  " + json.dumps(x, ensure_ascii=False, separators=(", ", ": "))
                                 + ("," if j < len(v) - 1 else ""))
                parts.append(" ]" + sep)
            else:
                parts.append(f' "{k}": ' + json.dumps(v, ensure_ascii=False, separators=(", ", ": ")) + sep)
        parts.append("}")
        text = "\n".join(parts)
    path.write_text(text + "\n", encoding="utf-8")
    return text


def dump_item(item, path):
    """One top-level key per line; the payload's bindings and evidence one record per line."""
    c = lambda v: json.dumps(v, ensure_ascii=False, separators=(", ", ": "))
    lines, keys = ["{"], list(item)
    for i, k in enumerate(keys):
        sep, v = ("," if i < len(keys) - 1 else ""), item[k]
        if k != "payload":
            lines.append(f' "{k}": ' + c(v) + sep)
            continue
        lines.append(' "payload": {')
        pk = list(v)
        for j, kk in enumerate(pk):
            s2, vv = ("," if j < len(pk) - 1 else ""), v[kk]
            if isinstance(vv, list) and vv and isinstance(vv[0], dict):
                lines.append(f'  "{kk}": [')
                lines += ["   " + c(x) + ("," if m < len(vv) - 1 else "") for m, x in enumerate(vv)]
                lines.append("  ]" + s2)
            else:
                lines.append(f'  "{kk}": ' + c(vv) + s2)
        lines.append(" }" + sep)
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def gyo_acyclic(hyperedges):
    """GYO reduction: alpha-acyclic iff the reduction empties the hypergraph. Returns (acyclic, residue)."""
    es = [set(e) for e in hyperedges.values() if e]
    changed = True
    while changed:
        changed = False
        # remove vertices that occur in one hyperedge only
        count = {}
        for e in es:
            for v in e:
                count[v] = count.get(v, 0) + 1
        for e in es:
            lone = {v for v in e if count[v] == 1}
            if lone:
                e -= lone
                changed = True
        # remove empty edges and edges contained in another edge
        keep = []
        for i, e in enumerate(es):
            if not e:
                changed = True
                continue
            if any(j != i and e <= f and (e != f or j < i) for j, f in enumerate(es)):
                changed = True
                continue
            keep.append(e)
        es = keep
    return (not es), [sorted(e) for e in es]


def schema_hypergraph(doc, slots=("core", "qualifier")):
    rel = {}
    for r in doc["relations"]:
        roles = sorted({u["role"] for u in r["roles"] if u["slot"] in slots})
        if roles:
            rel[r["id"]] = roles
    return {"vertices": sorted({v for e in rel.values() for v in e}), "hyperedges": rel}


CYCLIC = {
    "kind": "relation-schema", "format": "khg-relation-schema/1.0.0", "id": "p2-cyclic", "version": "1.0.0",
    "label": "A constructed cyclic schema: three relations whose role sets form a triangle",
    "entity_types": [{"id": "Agent"}],
    "roles": [{"id": "buyer"}, {"id": "seller"}, {"id": "broker"}],
    "relations": [
        {"id": "sale", "roles": [U("buyer", "core", [{"entity": ["Agent"]}], 1, 1),
                                 U("seller", "core", [{"entity": ["Agent"]}], 1, 1)]},
        {"id": "brokerage", "roles": [U("seller", "core", [{"entity": ["Agent"]}], 1, 1),
                                      U("broker", "core", [{"entity": ["Agent"]}], 1, 1)]},
        {"id": "referral", "roles": [U("broker", "core", [{"entity": ["Agent"]}], 1, 1),
                                     U("buyer", "core", [{"entity": ["Agent"]}], 1, 1)]},
    ],
}

WD_SHAPED = {
    "kind": "relation-schema", "format": "khg-relation-schema/1.0.0", "id": "wd-shaped", "version": "1.0.0",
    "label": "Wikidata-shaped schema: global qualifier roles (P580, P582, P585, P1545) shared across relations",
    "entity_types": [{"id": "Agent"}, {"id": "Person", "parents": ["Agent"]}, {"id": "Organisation", "parents": ["Agent"]},
                     {"id": "Position"}, {"id": "Award"}, {"id": "Team"}],
    "roles": [{"id": r} for r in ["holder", "position", "recipient", "award", "conferrer", "member", "team", "replaces"]]
    + [{"id": "start_time", "mappings": {"wikidata": "P580"}}, {"id": "end_time", "mappings": {"wikidata": "P582"}},
       {"id": "point_in_time", "mappings": {"wikidata": "P585"}}, {"id": "series_ordinal", "mappings": {"wikidata": "P1545"}}],
    "relations": [
        {"id": "position_held", "mappings": {"wikidata": "P39"}, "time": {"model": "interval", "start": "start_time", "end": "end_time"},
         "roles": [U("holder", "core", [{"entity": ["Person"]}], 1, 1), U("position", "core", [{"entity": ["Position"]}], 1, 1),
                   U("start_time", "time", TIME, 0, 1), U("end_time", "time", TIME, 0, 1),
                   U("replaces", "qualifier", [{"entity": ["Person"]}], 0, None),
                   U("series_ordinal", "qualifier", [{"literal": "string"}], 0, 1)]},
        {"id": "award_received", "mappings": {"wikidata": "P166"}, "time": {"model": "invariant"},
         "roles": [U("recipient", "core", [{"entity": ["Agent"]}], 1, 1), U("award", "core", [{"entity": ["Award"]}], 1, 1),
                   U("point_in_time", "qualifier", TIME, 0, 1), U("conferrer", "qualifier", [{"entity": ["Organisation"]}], 0, 1),
                   U("series_ordinal", "qualifier", [{"literal": "string"}], 0, 1)]},
        {"id": "member_of_sports_team", "mappings": {"wikidata": "P54"},
         "time": {"model": "interval", "start": "start_time", "end": "end_time"},
         "roles": [U("member", "core", [{"entity": ["Person"]}], 1, 1), U("team", "core", [{"entity": ["Team"]}], 1, 1),
                   U("start_time", "time", TIME, 0, 1), U("end_time", "time", TIME, 0, 1),
                   U("point_in_time", "qualifier", TIME, 0, 1), U("replaces", "qualifier", [{"entity": ["Person"]}], 0, None)]},
    ],
}

R05_SCHEMA = {
    "kind": "relation-schema", "format": "khg-relation-schema/1.0.0", "id": "r05-tables", "version": "1.0.0",
    "label": "The relations of the R05 unit-test tables, mapped to C1 (tests/scorers)",
    "entity_types": [{"id": "Thing"}],
    "roles": [{"id": x} for x in ["A", "B", "C", "D", "E", "Q"]],
    "relations": [
        {"id": "r", "key": {"roles": ["A", "B"], "temporal": False, "on_collision": "dispute"},
         "roles": [U("A", "core", [{"entity": ["Thing"]}], 0, 1), U("B", "core", [{"entity": ["Thing"]}], 0, 1),
                   U("C", "qualifier", [{"entity": ["Thing"]}], 0, 1), U("D", "qualifier", [{"entity": ["Thing"]}], 0, 1),
                   U("E", "qualifier", [{"entity": ["Thing"]}], 0, 1), U("Q", "qualifier", [{"entity": ["Thing"]}], 0, 1)]},
        {"id": "s", "roles": [U("A", "core", [{"entity": ["Thing"]}], 0, 1), U("B", "core", [{"entity": ["Thing"]}], 0, 1)]},
        {"id": "r2", "roles": [U("A", "core", [{"entity": ["Thing"]}], 1, 1), U("B", "core", [{"entity": ["Thing"]}], 1, 1)]},
        {"id": "r4", "roles": [U("A", "core", [{"entity": ["Thing"]}], 1, 1), U("B", "core", [{"entity": ["Thing"]}], 1, 1),
                               U("C", "core", [{"entity": ["Thing"]}], 1, 1), U("D", "core", [{"entity": ["Thing"]}], 1, 1)]},
    ],
}


def history_container(schema_sha):
    """A small history container (every version of every id) for the D013, D014 and D018 container cases."""
    t = lambda s: f"2026-10-01T00:00:{s:02d}Z"
    st = lambda r, v, s: dict(r, version=v, recorded_at=t(s), recorded_by="p2-fixture")
    ents = [st(ENT(i, ty, lab), 1, 1) for i, ty, lab in (("ex:HeLa", ["CellLine"], "HeLa"),
                                                           ("ex:KingOfFrance", ["Position"], "King of France"),
                                                           ("ex:LouisXIII", ["Person"], "Louis XIII"),
                                                           ("ex:LouisXIV", ["Person"], "Louis XIV"),
                                                           ("ex:TP53", ["Gene"], "TP53"))]
    k13v1 = st(H("f:king-13", "position_held",
                 [B("b1", "holder", E("ex:LouisXIII")), B("b2", "position", E("ex:KingOfFrance")),
                  B("b3", "start_time", T("+1610-05-14T00:00:00Z", 11))],
                 evidence=[ev_curated(doc="doc:regnal-list", supports=["b1", "b2", "b3"])]), 1, 2)
    k13v2 = copy.deepcopy(k13v1)
    k13v2.update(version=2, recorded_at=t(4))
    k13v2["bindings"].append(B("b4", "end_time", T("+1643-05-14T00:00:00Z", 11)))
    k13v2["evidence"].append(dict(ev_curated("e2", doc="doc:regnal-list", supports=["b4"])))
    reg1 = st(H("f:reg-1", "regulates", [B("b1", "context", E("ex:HeLa")), B("b2", "regulator", E("ex:TP53")),
                                         B("b3", "target", E("ex:TP53"))],
                evidence=[ev_curated(doc="doc:review-p53")]), 1, 3)
    reg1v2 = copy.deepcopy(reg1)
    reg1v2.update(version=2, recorded_at=t(5), status="retracted", status_ref="m:ret-1")
    ret = st(H("m:ret-1", "khg:retracts", [B("b1", "khg:retracted", {"fact": "f:reg-1"})], reason="withdrawn",
               evidence=[ev_curated(doc="doc:retraction-notice")]), 1, 5)
    hdr = {"kind": "header", "format": "khg-record/1.0.0", "document_id": "p2-history-example",
           "schema": {"id": "p2-gate", "version": "1.0.0", "sha256": schema_sha}, "content": "history",
           "as_at": t(5), "complete": True}
    return {"header": hdr, "records": ents + [k13v1, k13v2, reg1, reg1v2, ret]}


def migrate_sample(sample):
    """schemas/sample.hif.json (v0) -> khg-record/1.0.0 by the pinned rules of DESIGN §11."""
    report = []
    rel_of = {e["edge"]: e["attrs"]["relation"] for e in sample["edges"]}
    obs = {}  # relation -> role -> list of (edge, node, direction)
    for i in sample["incidences"]:
        obs.setdefault(rel_of[i["edge"]], {}).setdefault(i["attrs"]["role"], []).append(i)
    ntype = {n["node"]: n["attrs"]["type"] for n in sample["nodes"]}
    edges_of = {}
    for e in sample["edges"]:
        edges_of.setdefault(e["attrs"]["relation"], []).append(e["edge"])
    roles, relations = set(), []
    for rel in sorted(obs):
        usages = []
        for role in sorted(obs[rel]):
            incs = obs[rel][role]
            per_edge = {}
            for i in incs:
                per_edge[i["edge"]] = per_edge.get(i["edge"], 0) + 1
            dirs = {i.get("direction") for i in incs}
            u = U(role, "core", [{"entity": sorted({ntype[i["node"]] for i in incs})}],
                  1 if set(per_edge) == set(edges_of[rel]) else 0, None if max(per_edge.values()) > 1 else 1)
            if len(dirs) == 1 and None not in dirs:
                u["direction"] = dirs.pop()
            usages.append(u)
            roles.add(role)
        r = {"id": rel, "roles": usages}
        if any("valid-from" in e["attrs"] for e in sample["edges"] if e["attrs"]["relation"] == rel):
            r["time"] = {"model": "interval", "start": "start_time", "end": "end_time"}
            r["roles"] += [U("start_time", "time", TIME, 0, 1, direction="tail"),
                           U("end_time", "time", TIME, 0, 1, direction="tail")]
            roles |= {"start_time", "end_time"}
        relations.append(r)
    schema = {"kind": "relation-schema", "format": "khg-relation-schema/1.0.0", "id": "kb-sample", "version": "1.0.0",
              "label": "Generated from schemas/sample.hif.json (v0)",
              "entity_types": [{"id": t} for t in sorted(set(ntype.values()))],
              "roles": [{"id": r} for r in sorted(roles)], "relations": relations}
    S = K.Schema(schema)
    recs = []
    for n in sample["nodes"]:
        recs.append(ENT(n["node"], [n["attrs"]["type"]], n["attrs"]["label"]))
    for e in sample["edges"]:
        a = e["attrs"]
        bs = [B(None, i["attrs"]["role"], E(i["node"])) for i in sample["incidences"] if i["edge"] == e["edge"]]
        if "valid-from" in a:
            bs.append(B(None, "start_time", T(f"+{a['valid-from']}T00:00:00Z", 11)))
            report.append({"code": "KHG-F017", "edge": e["edge"], "message": "valid-from became a start_time binding"})
        bs.sort(key=K.bsortkey)
        for n, b in enumerate(bs, 1):
            b["bid"] = f"b{n}"
        h = H(e["edge"], a["relation"], bs,
              evidence=[{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": a["source"]}}])
        if "weight" in e:
            h["extensions"] = {"hif:weight": e["weight"]}
            report.append({"code": "KHG-F006", "edge": e["edge"], "message": "weight kept as extensions hif:weight"})
        d = K.derived(S, h)
        if d["arity"] != a.get("arity"):
            raise SystemExit(f"arity mismatch on {e['edge']}")
        report.append({"code": "KHG-F015", "edge": e["edge"], "message": f"stored arity {a['arity']} checked and dropped"})
        recs.append(h)
    md = sample["metadata"]
    report.append({"code": "KHG-F016", "message": "metadata schema and conventions replaced by the declaration block"})
    hdr = {"kind": "header", "format": "khg-record/1.0.0", "document_id": "kb-sample",
           "schema": {"id": "kb-sample", "version": "1.0.0", "sha256": S.sha256()}, "content": "snapshot", "complete": True,
           "extensions": {"hif:metadata": {k: md[k] for k in ("title", "description", "created", "kb-section")}}}
    return schema, K.canonical_doc({"header": hdr, "records": recs}), report


def main():
    S = K.Schema(SCHEMA)
    HEADER["schema"]["sha256"] = S.sha256()
    recs = copy.deepcopy(RECORDS)
    for r in recs:
        if r["kind"] == "hyperedge" and r["status"] != "goal":
            K.stamp_event_hashes(S, r)
    doc = {"header": HEADER, "records": recs}
    canon = K.canonical_doc(doc)
    dump(SCHEMA, OUT / "fixture.relation-schema.json", compact_records=["entity_types", "roles", "relations"])
    dump(canon, OUT / "fixture.c1.json", compact_records=["records"])
    with open(OUT / "fixture.c1.jsonl", "w", encoding="utf-8") as fh:
        for line in [canon["header"]] + canon["records"]:
            fh.write(K.cjson(line) + "\n")
    hif = K.c1_to_hif(canon, S)
    dump(hif, OUT / "fixture.hif.json", compact_records=["nodes", "edges", "incidences"])
    sl = K.c1_to_hif(canon, S, relations=DIRECTED_SLICE)
    dump(sl, OUT / "fixture.directed-slice.hif.json", compact_records=["nodes", "edges", "incidences"])
    wd = K.with_derived(canon, S)
    (OUT / "fixture.with-derived.c1.json").write_text(json.dumps(wd, ensure_ascii=False, indent=1) + "\n",
                                                        encoding="utf-8")
    hist = history_container(S.sha256())
    dump(K.canonical_doc(hist), OUT / "fixture.history.c1.json", compact_records=["records"])
    (OUT / "fixture.doc-texts.json").write_text(json.dumps(
        {"format": "khg-doc-texts/1.0.0", "texts": {k: {"text": v, "sha256": doc_hash(v)} for k, v in sorted(TEXTS.items())}},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # ---------------- smoke-test base, queue item and action-log entries (C3) ----------------
    base = {"header": {"kind": "header", "format": "khg-record/1.0.0", "document_id": "p2-smoke-base",
                       "schema": copy.deepcopy(HEADER["schema"]), "content": "snapshot", "complete": True},
            "records": [r for r in canon["records"] if r["kind"] == "entity"]}
    base = K.canonical_doc(base)
    dump(base, OUT / "smoke-base.c1.json", compact_records=["records"])
    king = copy.deepcopy(next(r for r in canon["records"] if r.get("id") == "f:king-14"))
    king["id"] = "cand:p2-smoke.000001"
    king["status"] = "candidate"
    d = K.derived(S, {**king, "status": "asserted"})
    e2 = next(e for e in king["evidence"] if e["id"] == "e2")
    item = {
        "kind": "queue-item", "qid": "q:p2-smoke.000001", "item_kind": "hyperedge",
        "submitted_at": "2026-10-01T00:00:03Z", "submitted_by": "p2-fixture-extractor/0.0.1",
        "run": {"run_id": "fixture-run-1", "order_id": "o1", "position": 0, "seed": 0, "temperature": 0},
        "doc": {"doc_id": e2["source"]["doc_id"], "doc_sha256": e2["source"]["doc_sha256"]},
        "payload": king,
        "keys": {"content_key": d["content_key"], "core_key": d["core_key"], "key_digest": d["key_digest"]},
    }
    stored = copy.deepcopy(king)
    stored["id"] = "f:king-14"
    stored["status"] = "asserted"
    written = [{"id": "f:king-14", "version": 1, "record": K.decision_view(stored)}]
    qhdr = {"kind": "queue-header", "format": "khg-queue/1.0.0", "queue_id": "p2-smoke",
            "record_format": "khg-record/1.0.0", "schema": copy.deepcopy(HEADER["schema"]),
            "base": {"document_id": "p2-smoke-base", "sha256": K.container_sha256(base)},
            "created_at": "2026-10-01T00:00:00Z"}
    lint = {"kind": "log-entry", "lid": "l:p2-smoke.000001", "parent": None, "target": "q:p2-smoke.000001",
            "action": "lint", "state_before": "pending", "state_after": "linted",
            "actor": {"type": "linter", "id": "khg-lint", "version": "1.0.0"}, "mode": "automatic",
            "at": "2026-10-01T00:00:05Z", "rule_set": {"id": "structural", "version": "1.0.0"}, "findings": [],
            "outcome": "pass"}
    entry = {
        "kind": "log-entry", "lid": "l:p2-smoke.000002", "parent": "l:p2-smoke.000001",
        "target": "q:p2-smoke.000001", "action": "accept", "state_before": "linted", "state_after": "accepted",
        "actor": {"type": "person", "id": "curator:smoke"}, "mode": "manual", "at": "2026-10-01T00:00:07Z",
        "reason": "the regnal list and the biography sentence support every binding",
        "before": [], "after": [{"id": "f:king-14", "version": 1}],
        "decision_hash": K.digest("khg-decision/1", written),
    }
    dump_item(item, OUT / "queue-item.json")
    dump(entry, OUT / "action-log.json", compact_records=[])
    (OUT / "smoke-queue.khg-queue.jsonl").write_text("".join(K.cjson(x) + "\n" for x in (qhdr, item, lint, entry)),
                                                    encoding="utf-8")
    # ---------------- extra schemas ----------------
    for name, sch in (("cyclic.relation-schema.json", CYCLIC), ("wikidata-shaped.relation-schema.json", WD_SHAPED),
                      ("r05.relation-schema.json", R05_SCHEMA)):
        dump(sch, OUT / name, compact_records=["entity_types", "roles", "relations"])
    # ---------------- the KB sample, migrated ----------------
    sample = json.loads((REPO / "schemas" / "sample.hif.json").read_text(encoding="utf-8"))
    ssch, sdoc, srep = migrate_sample(sample)
    dump(ssch, OUT / "sample.relation-schema.json", compact_records=["entity_types", "roles", "relations"])
    dump(sdoc, OUT / "sample.khg.json", compact_records=["records"])
    dump(K.c1_to_hif(sdoc, K.Schema(ssch)), OUT / "sample.khg.hif.json", compact_records=["nodes", "edges", "incidences"])
    (OUT / "sample.migration-report.json").write_text(json.dumps({"format": "khg-migration-report/1.0.0",
                                                                    "from": "v0-sample", "findings": srep},
                                                                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # ---------------- evidence printed for DESIGN.md ----------------
    print("schema sha256", S.sha256())
    print("king-14 derived", json.dumps(K.derived(S, next(r for r in canon["records"] if r.get("id") == "f:king-14")),
                                        ensure_ascii=False))
    for nm, sch in (("fixture", SCHEMA), ("cyclic", CYCLIC), ("wikidata-shaped", WD_SHAPED)):
        for slots in (("core", "qualifier"), ("core", "qualifier", "time")):
            hg = schema_hypergraph(sch, slots)
            ac, res = gyo_acyclic(hg["hyperedges"])
            print(f"schema_hypergraph {nm} slots={slots}: {len(hg['vertices'])} vertices, "
                  f"{len(hg['hyperedges'])} hyperedges, alpha-acyclic={ac}, residue={res}")
    print("decision_hash", entry["decision_hash"], "| base sha256", qhdr["base"]["sha256"])
    print("sample migration report", [f["code"] for f in srep])


if __name__ == "__main__":
    main()
