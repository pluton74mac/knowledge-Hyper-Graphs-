"""Writes <examples>/conformance-scenarios/: the v1 C2 conformance scenarios (khg-scenario/1.0.0) and index.json.
Records are referenced symbolically ("@<id>" = the fixture record of that id) and derived with small patches.
Every scenario is then executed against the prototype store (khg_store_proto) by run_scenarios.py."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import khg_synth as K  # noqa: E402

EX = Path(sys.argv[1])
OUT = EX / "conformance-scenarios"
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("*.json"):
    old.unlink()
FIX = json.loads((EX / "fixture.c1.json").read_text(encoding="utf-8"))
SCH = K.Schema(json.loads((EX / "fixture.relation-schema.json").read_text(encoding="utf-8")))
REC = {r["id"]: r for r in FIX["records"]}
ENTITIES = [r for r in FIX["records"] if r["kind"] == "entity"]


def T(t, p=11, cal=None):
    lit = {"datatype": "time", "time": t, "precision": p}
    if cal:
        lit["calendar"] = cal
    return {"literal": lit}


def ts(s):
    return f"2026-10-01T00:00:{s:02d}Z"


CUR = {"id": "e9", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:scenario"}}
ENT = "@entities"
SC = []


def sc(sid, title, given, when, precedent, extra_requires=()):
    SC.append({"format": "khg-scenario/1.0.0", "id": sid, "title": title, "requires": sorted(extra_requires),
               "schema": "fixture.relation-schema.json", "fixture": "fixture.c1.json", "given": given,
               "when": when, "precedent": precedent})


def put(*records, at=None):
    s = {"put": list(records)}
    if at:
        s["at"] = at
    return s


def op(name, then, at=None, **args):
    s = {"op": name, "args": args, "then": then}
    if at:
        s["at"] = at
    return s


def ev(event, then, at=None):
    return op("apply", then, at=at, event=event)


EQ = lambda sel, v: {"select": sel, "equals": v}
ERR = lambda code, **info: ({"error": code, "info": info} if info else {"error": code})
LOAD = {"load": "@fixture"}
IGN = ["version", "recorded_at", "recorded_by"]
K13 = {"@": "f:king-13", "drop_bindings": ["b4"]}          # Louis XIII, no end yet
KRA = {"@": "f:born-skłodowska-kraków", "set": {"status": "asserted"}, "drop": ["status_ref"]}
SUP = {"op": "supersede", "id": "m:sup-1", "superseded": ["f:born-skłodowska-kraków"],
       "records": ["@f:born-skłodowska-warszawa"], "reason": "correction",
       "note": "birthplace is Warsaw, per the curated biography", "evidence": [CUR]}
END13 = {"op": "end_validity", "target": "f:king-13", "end": T("+1643-05-14T00:00:00Z"), "evidence": [CUR]}
DISPUTE = {"op": "transition", "targets": ["f:born-skłodowska-warszawa"], "to": "disputed", "records": [KRA],
           "id": "m:dis-1", "reason": "key_conflict", "evidence": [CUR]}
KEYPOS = [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}]
KEYMARIA = [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}]
KEYLODZ = [{"role": "place", "value": {"entity": "ex:Łódź"}}, {"role": "point_in_time", "value": T("+2019-00-00T00:00:00Z", 9)}]
LOUIS16 = {"kind": "entity", "id": "ex:LouisXVI", "types": ["Person"], "label": "Louis XVI"}
BOUND = {"@": "g:who-1774", "set_binding": {"b1": {"entity": "ex:LouisXVI"}},
         "add_evidence": [{"id": "e1", "type": "agent_bound", "mode": "automatic", "source": {"doc_id": "doc:regnal-list"},
                           "activity": {"agent": "agent:history-desk"}, "supports": ["b1"]}]}
PARIS_MARIA = {"@": "f:born-skłodowska-warszawa", "set": {"id": "f:born-skłodowska-paris"},
               "set_binding": {"b2": {"entity": "ex:Paris"}}}


def coll(record, policy, *conflicts):
    return {"collisions": [{"record": record, "policy": policy, "conflicts": list(conflicts)}]}


def cf(i, shape, cls, action, in_batch=False):
    return {"id": i, "in_batch": in_batch, "shape": shape, "class": cls, "action": action}


# ------------------------------------------------ writes ------------------------------------------------
sc("S-PUT-001", "put then get returns the record",
   [put(ENT, "@f:reg-1")], [op("get", EQ("canonical", "@f:reg-1"), id="f:reg-1")],
   ["A C2-01 passed", "B S001"])
sc("S-PUT-002", "an identical put is a no-op",
   [put(ENT, "@f:reg-1")],
   [op("put", EQ("receipt.records", [["f:reg-1", 1, "noop"]]), records=["@f:reg-1"]),
    op("get", EQ("version", 1), id="f:reg-1")],
   ["A C2-02 passed", "C S-PUT-001 passed", "B S002"])
sc("S-PUT-003", "one invalid record in a batch writes nothing",
   [put(ENT)],
   [op("put", ERR("KHG-S001"), records=["@f:reg-1", {"@": "f:coadmin-1", "set": {"relation": "inhibits"}}]),
    op("get", EQ("record", None), id="f:reg-1")],
   ["B S003", "A §6.2 validate-all-then-write"])
sc("S-PUT-004", "a candidate never enters a store",
   [put(ENT)], [op("put", ERR("KHG-D017"), records=[{"@": "f:reg-1", "set": {"status": "candidate"}}])],
   ["A C2-17 passed", "C S-PUT-003 passed", "B S004"])
sc("S-PUT-005", "put reports the validator's code",
   [put(ENT)], [op("put", ERR("KHG-S003"), records=[{"@": "f:king-14", "drop_bindings": ["b2"]}])],
   ["B S005", "C S-PUT-005"])
sc("S-PUT-006", "optimistic concurrency: a stale expect is refused",
   [put(ENT, "@f:reg-1")],
   [op("put", ERR("KHG-D019"), records=[{"@": "f:reg-1", "add_evidence": [CUR]}], expect={"f:reg-1": 2}),
    op("put", EQ("receipt.records", [["f:reg-1", 2, "versioned"]]), records=[{"@": "f:reg-1", "add_evidence": [CUR]}],
       expect={"f:reg-1": 1})],
   ["B S006"])
sc("S-PUT-007", "unbound is accepted in a goal and refused elsewhere",
   [put(ENT)],
   [op("put", EQ("receipt.records", [["g:who-1774", 1, "created"]]), records=["@g:who-1774"]),
    op("put", ERR("KHG-C005"), records=[{"@": "g:who-1774", "set": {"id": "f:who-bad", "status": "asserted"},
                                          "drop": ["goal"], "add_evidence": [CUR]}])],
   ["C S-PUT-004 passed"])
sc("S-PUT-008", "put cannot change the status of an existing id",
   [put(ENT, "@f:reg-1")], [op("put", ERR("KHG-D014"), records=[{"@": "f:reg-1", "set": {"status": "quoted"}}])],
   ["C S-PUT-006"])
sc("S-PUT-009", "a reference to an entity the store does not hold is refused",
   [put("@ex:TP53")], [op("put", ERR("KHG-D002"), records=["@f:reg-1"])], ["C S-PUT-007"])
sc("S-PUT-010", "a value naming a redirected entity is refused (redirects are rewritten in 1.2)",
   [put(ENT, {"kind": "entity", "id": "ex:Louis-XIV-dup", "types": ["Person"], "label": "Louis XIV",
              "redirect_to": "ex:LouisXIV"})],
   [op("put", ERR("KHG-D020"), records=[{"@": "f:king-14", "set_binding": {"b1": {"entity": "ex:Louis-XIV-dup"}}}])],
   ["critique SEM-16 (R01 I10)"])
# ------------------------------------------------ versions ------------------------------------------------
sc("S-VER-001", "each write makes a version; get(as_at) returns the older one",
   [put(ENT, at=ts(1)), put(K13, at=ts(2))],
   [ev(END13, EQ("receipt.records", [["f:king-13", 2, "versioned"]]), at=ts(3)),
    op("get", EQ("version", 1), id="f:king-13", as_at=ts(2)),
    op("get", EQ("version", 2), id="f:king-13"),
    op("history", EQ("versions", [1, 2]), id="f:king-13")],
   ["A C2-03 passed", "C S-PUT-002 passed", "B S010"], ["transaction_time"])
sc("S-VER-002", "add_evidence makes a new version with the same content",
   [put(ENT, "@f:reg-1")],
   [ev({"op": "add_evidence", "target": "f:reg-1", "evidence": [CUR]}, EQ("receipt.records", [["f:reg-1", 2, "versioned"]])),
    op("get", EQ("evidence.ids", ["e1", "e9"]), id="f:reg-1")],
   ["B S011", "C S-LIFE-003"])
sc("S-VER-003", "adding an end date is a refinement; changing a core binding is refused",
   [put(ENT, K13)],
   [op("put", EQ("receipt.records", [["f:king-13", 2, "versioned"]]),
       records=[{"@": "f:king-13", "set_evidence": {"e1": {"supports": ["b1", "b2", "b3"]}},
                 "add_evidence": [dict(CUR, supports=["b4"])]}]),
    op("put", ERR("KHG-D013"), records=[{"@": "f:king-13", "set_binding": {"b1": {"entity": "ex:LouisXIV"}},
                                          "set_evidence": {"e1": {"supports": ["b1", "b2", "b3"]}},
                                          "add_evidence": [dict(CUR, supports=["b4"])]}])],
   ["B C2-S012 passed", "A C2-18 passed", "judge probe: C accepted Bob for Alice as version 2"])
sc("S-VER-004", "a new version that rewrites earlier evidence is refused",
   [put(ENT, "@f:reg-1")],
   [op("put", ERR("KHG-D013"), records=[{"@": "f:reg-1", "set_evidence": {"e1": {"source": {"doc_id": "doc:other"}}}}])],
   ["B S013"])
sc("S-VER-005", "a transition outside the table (retracted to disputed) is refused",
   [put(ENT, "@f:reg-1"),
    {"apply": {"op": "transition", "targets": ["f:reg-1"], "to": "retracted", "id": "m:ret-1", "reason": "withdrawn",
               "evidence": [CUR]}}],
   [ev({"op": "transition", "targets": ["f:reg-1"], "to": "disputed", "id": "m:dis-1", "reason": "curator",
        "evidence": [CUR]}, ERR("KHG-D014"))],
   ["B S014", "A C2-16 passed"])
sc("S-VER-006", "superseded content is frozen",
   [LOAD], [ev({"op": "add_evidence", "target": "f:born-skłodowska-kraków", "evidence": [CUR]}, ERR("KHG-D013"))],
   ["B S015"])
sc("S-VER-007", "a somevalue binding refined to a value keeps its bid",
   [put(ENT, "@f:born-scribe")],
   [op("put", EQ("receipt.records", [["f:born-scribe", 2, "versioned"]]),
       records=[{"@": "f:born-scribe", "set_binding": {"b2": {"entity": "ex:Paris"}}, "add_evidence": [dict(CUR, supports=["b2"])]}]),
    op("get", EQ("binding.b2.value", {"entity": "ex:Paris"}), id="f:born-scribe")],
   ["B §2.16 (R01 I12)"])
sc("S-VER-008", "entity versions: labels may change, types only grow, redirect_to is set once",
   [put(ENT)],
   [op("put", EQ("receipt.records", [["ex:LouisXIV", 2, "versioned"]]),
       records=[{"@": "ex:LouisXIV", "set": {"label": "Louis XIV of France", "aliases": ["the Sun King"]}}]),
    op("put", ERR("KHG-D013"), records=[{"@": "ex:LouisXIV", "set": {"types": ["Agent"], "label": "Louis XIV of France",
                                                                       "aliases": ["the Sun King"]}}]),
    op("put", EQ("receipt.records", [["ex:Paris", 2, "versioned"]]), records=[{"@": "ex:Paris", "set": {"redirect_to": "ex:Warszawa"}}]),
    op("put", ERR("KHG-D013"), records=[{"@": "ex:Paris", "set": {"redirect_to": "ex:Kraków"}}])],
   ["critique CONS-28"])
sc("S-VER-009", "end_validity may replace a novalue end (a world change): the status stays asserted",
   [put(ENT, {"@": "f:king-13", "set_binding": {"b4": {"special": "novalue"}}})],
   [ev({"op": "end_validity", "target": "f:king-13", "end": T("+1643-05-14T00:00:00Z"),
        "end_cause": {"entity": "ex:LouisXIV"}, "evidence": [CUR]},
       EQ("receipt.records", [["f:king-13", 2, "versioned"]])),
    op("get", EQ("status", "asserted"), id="f:king-13"),
    op("get", EQ("binding.b4.value", T("+1643-05-14T00:00:00Z", 11, "gregorian")), id="f:king-13"),
    op("get", EQ("binding.b5.role", "khg:end_cause"), id="f:king-13"),
    op("get", EQ("evidence.e9.supports", ["b4", "b5"]), id="f:king-13")],
   ["critique SEM-01, SEM-06 (R04 M4 end_cause)"], ["valid_time"])
# ------------------------------------------------ reads ------------------------------------------------
sc("S-READ-001", "incident is complete and in id order; goals are not asserted",
   [LOAD], [op("incident", EQ("ids", ["f:king-13", "f:king-14"]), node="ex:KingOfFrance")],
   ["A C2-04 passed", "C S-INC-001 passed"])
sc("S-READ-002", "a node in two roles returns the fact once; the role filter",
   [LOAD],
   [op("incident", EQ("ids", ["f:reg-1"]), node="ex:TP53"),
    op("incident", EQ("ids", ["f:reg-1"]), node="ex:TP53", role="target"),
    op("incident", EQ("ids", ["f:loop-yyz", "f:route-1"]), node="ex:YYZ"),
    op("incident", EQ("ids", ["f:loop-yyz"]), node="ex:YYZ", role="origin")],
   ["A C2-05 passed", "C S-INC-002 passed", "B S020/S021"])
sc("S-READ-003", "default reads hide superseded, quoted, deprecated, goal and lifecycle records",
   [LOAD],
   [op("incident", EQ("ids", ["f:born-skłodowska-warszawa", "f:married-curie"]), node="ex:Maria_Skłodowska"),
    op("incident", EQ("ids", ["f:king-14"]), node="ex:LouisXIV"),
    op("incident", EQ("ids", ["f:pop-łódź-2019"]), node="ex:Łódź")],
   ["A C2-06 passed", "C S-INC-007", "B S022"])
sc("S-READ-004", "the status filter can include superseded facts",
   [LOAD],
   [op("incident", EQ("ids", ["f:born-skłodowska-kraków", "f:born-skłodowska-warszawa", "f:married-curie"]),
       node="ex:Maria_Skłodowska", where={"status": ["asserted", "superseded"]})],
   ["A C2-07 passed"])
sc("S-READ-005", "incident on a fact id finds nesting and lifecycle records",
   [LOAD],
   [op("incident", EQ("ids", ["f:claim-1"]), node="f:born-louis14-paris"),
    op("incident", EQ("ids", ["m:sup-1"]), node="f:born-skłodowska-kraków", where={"kinds": ["lifecycle"]})],
   ["A C2-22 passed", "C S-INC-003 passed", "B S023"])
sc("S-READ-006", "keyset pagination is stable",
   [LOAD],
   [op("incident", EQ("ids", ["f:king-13"]), node="ex:KingOfFrance", where={"status": ["asserted", "goal"]}, limit=1),
    op("incident", EQ("ids", ["f:king-14"]), node="ex:KingOfFrance", where={"status": ["asserted", "goal"]}, limit=1,
       after="f:king-13"),
    op("incident", EQ("ids", ["g:who-1774"]), node="ex:KingOfFrance", where={"status": ["asserted", "goal"]}, limit=1,
       after="f:king-14"),
    op("incident", EQ("ids", []), node="ex:KingOfFrance", where={"status": ["asserted", "goal"]}, limit=1,
       after="g:who-1774")],
   ["A C2-20 passed", "C S-INC-004 passed", "B S024"])
sc("S-READ-007", "degree equals the length of incident",
   [LOAD], [op("degree", EQ("value", 2), node="ex:YYZ"), op("degree", EQ("value", 1), node="ex:YYZ", role="stop")],
   ["C S-INC-008", "B S025"])
sc("S-READ-008", "find at_least matches a multiset; a repeated role needs distinct bindings",
   [LOAD],
   [op("find", EQ("ids", ["f:coadmin-1"]), relation="co_administration_causes",
       pattern=[{"role": "agent", "value": {"entity": "ex:insulin"}}]),
    op("find", EQ("ids", []), relation="co_administration_causes",
       pattern=[{"role": "agent", "value": {"entity": "ex:insulin"}}, {"role": "agent", "value": {"entity": "ex:insulin"}}]),
    op("find", EQ("ids", ["f:coadmin-1"]), relation="co_administration_causes",
       pattern=[{"role": "agent", "value": {"entity": "ex:insulin"}}, {"role": "agent", "value": {"entity": "ex:metformin"}}])],
   ["A C2-09 passed", "C S-FIND-001 passed", "B S026"])
sc("S-READ-009", "find exact needs the whole binding multiset",
   [LOAD],
   [op("find", EQ("ids", []), relation="co_administration_causes", match="exact",
       pattern=[{"role": "agent", "value": {"entity": "ex:insulin"}}, {"role": "agent", "value": {"entity": "ex:metformin"}}]),
    op("find", EQ("ids", ["f:coadmin-1"]), relation="co_administration_causes", match="exact",
       pattern=[{"role": "agent", "value": {"entity": "ex:insulin"}}, {"role": "agent", "value": {"entity": "ex:metformin"}},
                {"role": "effect", "value": {"entity": "ex:hypoglycaemia"}}])],
   ["A C2-10 passed", "C S-FIND-002 passed", "B S027"])
sc("S-READ-010", "find by a time literal: precision takes part in equality; the calendar does not",
   [LOAD],
   [op("find", EQ("ids", ["f:pop-łódź-2019"]), relation="population",
       pattern=[{"role": "point_in_time", "value": T("+2019-00-00T00:00:00Z", 9)}]),
    op("find", EQ("ids", []), relation="population",
       pattern=[{"role": "point_in_time", "value": T("+2019-01-01T00:00:00Z", 11)}]),
    op("find", EQ("ids", ["f:married-curie"]), relation="married",
       pattern=[{"role": "start_time", "value": T("+1895-07-14T00:00:00Z", 11, "julian")}])],
   ["C S-FIND-003 passed", "B S028", "critique CONS-12 (Julian 1895-07-14 is Gregorian 1895-07-26)"])
sc("S-READ-011", "quantities match with unit and bounds",
   [LOAD],
   [op("find", EQ("ids", ["f:station-東京"]), relation="station_profile",
       pattern=[{"role": "elevation", "value": {"literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573",
                                                             "lower": "+3", "upper": "+4"}}}]),
    op("find", EQ("ids", []), relation="station_profile",
       pattern=[{"role": "elevation", "value": {"literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573"}}}])],
   ["C S-FIND-004"])
sc("S-READ-012", "ordered roles match by position; a pattern without a position matches any position",
   [LOAD],
   [op("find", EQ("ids", ["f:route-1"]), relation="flight_route",
       pattern=[{"role": "stop", "value": {"entity": "ex:YYZ"}, "position": 3}]),
    op("find", EQ("ids", []), relation="flight_route", pattern=[{"role": "stop", "value": {"entity": "ex:YYZ"}, "position": 2}]),
    op("find", EQ("ids", ["f:route-1"]), relation="flight_route", pattern=[{"role": "stop", "value": {"entity": "ex:YUL"}}])],
   ["C S-FIND-005", "critique CONS-25"])
sc("S-READ-013", "an any_unbound pattern finds goals, which appear only when asked for",
   [LOAD],
   [op("find", EQ("ids", []), relation="position_held", pattern=[{"role": "holder", "value": {"any_unbound": True}}]),
    op("find", EQ("ids", ["g:who-1774"]), relation="position_held", pattern=[{"role": "holder", "value": {"any_unbound": True}}],
       where={"status": ["goal"]})],
   ["A C2-21 passed", "C S-FIND-006", "B S029", "critique CONS-25 (pattern grammar)"])
sc("S-READ-014", "find matches novalue",
   [LOAD], [op("find", EQ("ids", ["f:cat-7"]), relation="catalysed_by",
               pattern=[{"role": "catalyst", "value": {"special": "novalue"}}])],
   ["C S-FIND-007"])
sc("S-READ-015", "get ignores the Where filters",
   [LOAD], [op("get", EQ("status", "superseded"), id="f:born-skłodowska-kraków"),
            op("get", EQ("status", "goal"), id="g:who-1774")],
   ["standards ruling (store defaults)"])
sc("S-READ-016", "get_many returns every requested record in one call",
   [LOAD], [op("get_many", EQ("ids", ["ex:HeLa", "ex:TP53", "f:reg-1"]), ids=["f:reg-1", "ex:TP53", "ex:HeLa"])],
   ["C §1.4 (P10)"])
sc("S-READ-017", "timeless relations pass every as_of filter, in both modes",
   [LOAD],
   [op("incident", EQ("ids", ["f:loop-yyz", "f:route-1"]), node="ex:AirCanada", where={"as_of": "+1700-01-01T00:00:00Z"}),
    op("incident", EQ("ids", ["f:loop-yyz", "f:route-1"]), node="ex:AirCanada",
       where={"as_of": "+1700-01-01T00:00:00Z", "valid_mode": "possible"})],
   ["critique SEM-15"])
sc("S-READ-018", "an empty pattern lists the relation's facts, paginated",
   [LOAD],
   [op("find", EQ("ids", ["f:king-13"]), relation="position_held", pattern=[], limit=1),
    op("find", EQ("ids", ["f:king-14"]), relation="position_held", pattern=[], limit=1, after="f:king-13")],
   ["critique CONS-25"])
sc("S-READ-019", "vocabulary ids (units, globes, rank reasons) are not nodes: incident finds nothing",
   [LOAD],
   [op("incident", EQ("ids", []), node="wd:Q11573"),
    op("incident", EQ("ids", []), node="wd:Q2"),
    op("incident", EQ("ids", []), node="wd:Q41755623", where={"rank": ["preferred", "normal", "deprecated"]})],
   ["critique FIXTURE-VOCAB-REFS"])
# ------------------------------------------------ time ------------------------------------------------
sc("S-TIME-001", "as_of filters by valid time; an ended fact stays asserted",
   [LOAD],
   [op("incident", EQ("ids", ["f:king-13"]), node="ex:KingOfFrance", where={"as_of": "+1620-01-01T00:00:00Z"}),
    op("incident", EQ("ids", ["f:king-14"]), node="ex:KingOfFrance", where={"as_of": "+1700-01-01T00:00:00Z"}),
    op("incident", EQ("ids", []), node="ex:KingOfFrance", where={"as_of": "+1720-01-01T00:00:00Z"}),
    op("get", EQ("status", "asserted"), id="f:king-13")],
   ["A C2-08 passed", "C S-INC-005"])
sc("S-TIME-002", "as_at before a supersession sees the older belief; so does the walk",
   [put(ENT, at=ts(1)), put(KRA, at=ts(2)), {"apply": SUP, "at": ts(3)}],
   [op("get", EQ("status", "asserted"), id="f:born-skłodowska-kraków", as_at=ts(2)),
    op("get", EQ("status", "superseded"), id="f:born-skłodowska-kraków"),
    op("supersession_walk", EQ("terminal.ids", ["f:born-skłodowska-warszawa"]), id="f:born-skłodowska-kraków"),
    op("supersession_walk", EQ("terminal.ids", ["f:born-skłodowska-kraków"]), id="f:born-skłodowska-kraków", as_at=ts(2))],
   ["B C2-S031 passed", "C S-SUP-004"], ["transaction_time"])
sc("S-TIME-003", "definite and possible readings at year precision",
   [put(ENT, {"@": "f:king-13", "set_binding": {"b4": T("+1643-00-00T00:00:00Z", 9)}},
        {"@": "f:king-14", "set_binding": {"b3": T("+1643-00-00T00:00:00Z", 9)}})],
   [op("incident", EQ("ids", []), node="ex:KingOfFrance", where={"as_of": "+1643-06-01T00:00:00Z"}),
    op("incident", EQ("ids", ["f:king-13", "f:king-14"]), node="ex:KingOfFrance",
       where={"as_of": "+1643-06-01T00:00:00Z", "valid_mode": "possible"})],
   ["B S032", "B identity case X1"], ["valid_time"])
sc("S-TIME-004", "as_of and as_at compose",
   [put(ENT, at=ts(1)), put(K13, at=ts(2)), {"apply": END13, "at": ts(3)}],
   [op("incident", EQ("ids", ["f:king-13"]), node="ex:KingOfFrance", where={"as_of": "+1700-01-01T00:00:00Z", "as_at": ts(2)}),
    op("incident", EQ("ids", []), node="ex:KingOfFrance", where={"as_of": "+1700-01-01T00:00:00Z"})],
   ["B S033", "C S-INC-006"], ["valid_time", "transaction_time"])
sc("S-TIME-005", "an undated fact: definite reads skip it, possible reads and reads without as_of keep it",
   [put(ENT, {"@": "f:married-curie", "drop_bindings": ["b3", "b4"]})],
   [op("incident", EQ("ids", []), node="ex:Pierre_Curie", where={"as_of": "+1900-01-01T00:00:00Z"}),
    op("incident", EQ("ids", ["f:married-curie"]), node="ex:Pierre_Curie",
       where={"as_of": "+1900-01-01T00:00:00Z", "valid_mode": "possible"}),
    op("incident", EQ("ids", ["f:married-curie"]), node="ex:Pierre_Curie")],
   ["B C2-S034 passed"], ["valid_time"])
sc("S-TIME-006", "end_validity keeps the status and adds the end binding",
   [put(ENT, K13)],
   [ev(END13, EQ("receipt.records", [["f:king-13", 2, "versioned"]])),
    op("get", EQ("status", "asserted"), id="f:king-13"),
    op("get", EQ("binding.b4.role", "end_time"), id="f:king-13"),
    op("get", EQ("derived.valid_time.kind", "period"), id="f:king-13"),
    op("get", EQ("evidence.e9.supports", ["b4"]), id="f:king-13")],
   ["C S-TIME-001 passed", "C S-TIME-002", "critique SEM-21"], ["valid_time"])
sc("S-TIME-007", "a Julian date is compared on the proleptic Gregorian line",
   [put(ENT, {"@": "f:king-13", "set_binding": {"b4": T("+1643-05-04T00:00:00Z", 11, "julian")}})],
   [op("incident", EQ("ids", ["f:king-13"]), node="ex:KingOfFrance", where={"as_of": "+1643-05-13T00:00:00Z"}),
    op("incident", EQ("ids", []), node="ex:KingOfFrance", where={"as_of": "+1643-05-14T12:00:00Z"})],
   ["graft U10 (calendar field)"], ["valid_time"])
sc("S-TIME-008", "an end-only (until) fact has no definite validity: the start is unknown",
   [put(ENT, {"@": "f:king-13", "drop_bindings": ["b3"]})],
   [op("incident", EQ("ids", []), node="ex:KingOfFrance", where={"as_of": "+1620-01-01T00:00:00Z"}),
    op("incident", EQ("ids", ["f:king-13"]), node="ex:KingOfFrance",
       where={"as_of": "+1620-01-01T00:00:00Z", "valid_mode": "possible"}),
    op("get", EQ("derived.valid_time.kind", "until"), id="f:king-13")],
   ["critique SEM-08"], ["valid_time"])
sc("S-TIME-009", "a somevalue end (ended, date unknown) has no definite validity after the start window",
   [put(ENT, {"@": "f:king-13", "set_binding": {"b4": {"special": "somevalue"}}})],
   [op("incident", EQ("ids", []), node="ex:KingOfFrance", where={"as_of": "+1620-01-01T00:00:00Z"}),
    op("incident", EQ("ids", ["f:king-13"]), node="ex:KingOfFrance",
       where={"as_of": "+1620-01-01T00:00:00Z", "valid_mode": "possible"}),
    op("get", EQ("derived.valid_time.kind", "ended"), id="f:king-13"),
    op("get", EQ("derived.valid_time.definite", None), id="f:king-13")],
   ["critique SEM-01"], ["valid_time"])
sc("S-TIME-010", "precision 7 is an ordinal century: +1900/7 is 1801-1900",
   [put(ENT, {"@": "f:married-curie", "set_binding": {"b3": T("+1900-00-00T00:00:00Z", 7)}, "drop_bindings": ["b4"]})],
   [op("get", EQ("derived.valid_time.possible", ["+1801-01-01T00:00:00Z", None]), id="f:married-curie"),
    op("get", EQ("derived.valid_time.definite", ["+1901-01-01T00:00:00Z", None]), id="f:married-curie"),
    op("incident", EQ("ids", []), node="ex:Pierre_Curie", where={"as_of": "+1900-06-01T00:00:00Z"}),
    op("incident", EQ("ids", ["f:married-curie"]), node="ex:Pierre_Curie", where={"as_of": "+1901-06-01T00:00:00Z"})],
   ["critique CONS-01 (Wikidata Help:Dates, precision 7)"], ["valid_time"])
sc("S-TIME-011", "precision 6 is an ordinal millennium; precision 8 is a decade",
   [put(ENT, {"@": "f:married-curie", "set_binding": {"b3": T("+2000-00-00T00:00:00Z", 6), "b4": T("+2025-00-00T00:00:00Z", 8)}})],
   [op("get", EQ("derived.valid_time.possible", ["+1001-01-01T00:00:00Z", "+2030-01-01T00:00:00Z"]), id="f:married-curie"),
    op("get", EQ("derived.valid_time.definite", ["+2001-01-01T00:00:00Z", "+2020-01-01T00:00:00Z"]), id="f:married-curie")],
   ["critique CONS-01 (precision 6 and 8)"], ["valid_time"])
sc("S-TIME-012", "a BCE Julian date: historical year -44 is astronomical -43, and Julian 15 March is Gregorian 13 March",
   [put(ENT, {"kind": "entity", "id": "ex:Caesar", "types": ["Person"], "label": "Gaius Julius Caesar"},
        {"kind": "entity", "id": "ex:Dictator", "types": ["Position"], "label": "Roman dictator"},
        {"@": "f:king-13", "set": {"id": "f:caesar-dictator"},
         "set_binding": {"b1": {"entity": "ex:Caesar"}, "b2": {"entity": "ex:Dictator"},
                         "b3": T("-0049-00-00T00:00:00Z", 9, "julian"), "b4": T("-0044-03-15T00:00:00Z", 11, "julian")}})],
   [op("get", EQ("derived.valid_time.possible", ["-0049-12-30T00:00:00Z", "-0043-03-14T00:00:00Z"]), id="f:caesar-dictator"),
    op("incident", EQ("ids", ["f:caesar-dictator"]), node="ex:Caesar", where={"as_of": "-0043-03-12T00:00:00Z"}),
    op("incident", EQ("ids", []), node="ex:Caesar", where={"as_of": "-0043-03-13T12:00:00Z"})],
   ["critique CONS-01 (Wikibase: BCE years use historical numbering)"], ["valid_time"])
# ------------------------------------------------ keys ------------------------------------------------
sc("S-KEY-001", "a put that breaks the key invariant raises KeyCollision and writes nothing",
   [put(ENT, "@f:king-13")],
   [op("put", ERR("KHG-D016", **coll("f:king-14b", "close_older", cf("f:king-13", "overlap_after_end", "distinct", "dispute"))),
       records=[{"@": "f:king-14", "set": {"id": "f:king-14b"}, "set_binding": {"b3": T("+1640-01-01T00:00:00Z")}}]),
    op("get", EQ("record", None), id="f:king-14b"),
    op("find_by_key", EQ("ids", ["f:king-13"]), relation="position_held", key=KEYPOS)],
   ["B C2-S040 passed", "C S-KEY-002 passed", "A C2-12 passed", "critique SEM-04 (X2 shape)"],
   ["key_constraint", "valid_time"])
sc("S-KEY-002", "find_by_key without as_of returns the key's timeline in id order",
   [LOAD], [op("find_by_key", EQ("ids", ["f:king-13", "f:king-14"]), relation="position_held", key=KEYPOS)],
   ["B S041"])
sc("S-KEY-003", "find_by_key with as_of returns the holder at that time",
   [LOAD], [op("find_by_key", EQ("ids", ["f:king-14"]), relation="position_held", key=KEYPOS,
               where={"as_of": "+1700-01-01T00:00:00Z"})],
   ["C S-KEY-001 passed", "B S042"], ["valid_time"])
sc("S-KEY-004", "one preferred fact may stand beside normal ones on a key",
   [put(ENT)],
   [op("put", EQ("receipt.records", [["f:pop-łódź-2019", 1, "created"], ["f:pop-łódź-2019-dep", 1, "created"]]),
       records=[{"@": "f:pop-łódź-2019", "set": {"rank": "preferred"}},
                {"@": "f:pop-łódź-2019-dep", "set": {"rank": "normal"}, "drop": ["rank_reason"]}]),
    op("find_by_key", EQ("ids", ["f:pop-łódź-2019", "f:pop-łódź-2019-dep"]), relation="population", key=KEYLODZ)],
   ["B S043 (Wikidata single-best-value)"], ["key_constraint", "atomic_writes"])
sc("S-KEY-005", "a deprecated fact never collides and is hidden by default",
   [put(ENT, "@f:pop-łódź-2019", "@f:pop-łódź-2019-dep")],
   [op("find_by_key", EQ("ids", ["f:pop-łódź-2019"]), relation="population", key=KEYLODZ),
    op("find_by_key", EQ("ids", ["f:pop-łódź-2019", "f:pop-łódź-2019-dep"]), relation="population", key=KEYLODZ,
       where={"rank": ["preferred", "normal", "deprecated"]})],
   ["standards and consumers rulings (rank-aware invariant)"], ["key_constraint"])
sc("S-KEY-006", "a non-temporal key collides whatever the dates",
   [put(ENT, "@f:born-skłodowska-warszawa")],
   [op("put", ERR("KHG-D016", **coll("f:born-skłodowska-kraków", "dispute",
                                     cf("f:born-skłodowska-warszawa", None, "distinct", "dispute"))), records=[KRA])],
   ["B S046", "C S-KEY-004"], ["key_constraint"])
sc("S-KEY-007", "close_older on a succession: the caller ends the older fact at the newer start, then puts",
   [put(ENT, K13)],
   [op("put", ERR("KHG-D016", **coll("f:king-14", "close_older", cf("f:king-13", "succession", "distinct", "close_older"))),
       records=["@f:king-14"]),
    ev({"op": "end_validity", "target": "f:king-13", "end": T("+1643-05-14T00:00:00Z"),
        "evidence": [{"id": "e9", "type": "inferred", "mode": "automatic", "source": {"doc_id": "doc:regnal-list"},
                      "inference": {"rule": "close_older", "from": ["f:king-14"]}}]},
       EQ("receipt.records", [["f:king-13", 2, "versioned"]])),
    op("put", EQ("receipt.records", [["f:king-14", 1, "created"]]), records=["@f:king-14"]),
    op("find_by_key", EQ("ids", ["f:king-14"]), relation="position_held", key=KEYPOS,
       where={"as_of": "+1700-01-01T00:00:00Z"})],
   ["B S044", "A C2-11 passed (reported, not rewritten)", "C §1.4 (P7)", "critique SEM-04"], ["key_constraint", "valid_time"])
sc("S-KEY-008", "dispute: one transition writes the new fact, both statuses and the khg:disputes record",
   [put(ENT, "@f:born-skłodowska-warszawa")],
   [ev(DISPUTE, EQ("receipt.records", [["f:born-skłodowska-kraków", 1, "created"], ["f:born-skłodowska-warszawa", 2, "versioned"],
                                       ["m:dis-1", 1, "created"]])),
    op("get", EQ("status_ref", "m:dis-1"), id="f:born-skłodowska-kraków"),
    op("find_by_key", EQ("ids", []), relation="born_in", key=KEYMARIA),
    op("find_by_key", EQ("ids", ["f:born-skłodowska-kraków", "f:born-skłodowska-warszawa"]), relation="born_in", key=KEYMARIA,
       where={"status": ["disputed"]})],
   ["B S045", "C S-LIFE (transition)", "critique SEM-10"], ["key_constraint"])
sc("S-KEY-009", "a year-precision handover is a succession, not a collision; the possible overlap is a warning",
   [put(ENT)],
   [op("put", EQ("receipt.warnings", [{"code": "KHG-L008", "ids": ["f:king-13", "f:king-14"]}]),
       records=[{"@": "f:king-13", "set_binding": {"b4": T("+1643-00-00T00:00:00Z", 9)}},
                {"@": "f:king-14", "set_binding": {"b3": T("+1643-00-00T00:00:00Z", 9)}}])],
   ["B identity case X1", "C S-KEY-003"], ["key_constraint", "valid_time"])
sc("S-KEY-010", "a transition back to asserted drops status_ref and re-checks the key",
   [put(ENT, "@f:born-skłodowska-warszawa"), {"apply": DISPUTE}],
   [ev({"op": "transition", "targets": ["f:born-skłodowska-warszawa"], "to": "asserted", "evidence": [CUR]},
       EQ("receipt.records", [["f:born-skłodowska-warszawa", 3, "versioned"]])),
    op("get", EQ("status_ref", None), id="f:born-skłodowska-warszawa"),
    ev({"op": "transition", "targets": ["f:born-skłodowska-kraków"], "to": "asserted", "evidence": [CUR]},
       ERR("KHG-D016", **coll("f:born-skłodowska-kraków", "dispute",
                              cf("f:born-skłodowska-warszawa", None, "distinct", "dispute"))))],
   ["C S-KEY-005", "critique SEM-10"], ["key_constraint"])
sc("S-KEY-011", "a special value in a key role gives no key digest and never collides",
   [put(ENT)],
   [op("put", EQ("receipt.records", [["f:born-x1", 1, "created"], ["f:born-x2", 1, "created"]]),
       records=[{"@": "f:born-scribe", "set": {"id": "f:born-x1"},
                 "set_binding": {"b1": {"special": "somevalue"}, "b2": {"entity": "ex:Paris"}}},
                {"@": "f:born-scribe", "set": {"id": "f:born-x2"},
                 "set_binding": {"b1": {"special": "somevalue"}, "b2": {"entity": "ex:Kraków"}}}])],
   ["B §2.17", "judge re-run: C's digest made two somevalue keys collide"], ["key_constraint"])
sc("S-KEY-012", "an undated fact beside a dated one on a temporal key: no collision, a possible-overlap warning",
   [put(ENT, "@f:king-14")],
   [op("put", EQ("receipt.warnings", [{"code": "KHG-L008", "ids": ["f:king-13", "f:king-14"]}]),
       records=[{"@": "f:king-13", "drop_bindings": ["b3", "b4"]}])],
   ["critique SEM-08, CONS-11 (open question X3, ruled)"], ["key_constraint", "valid_time"])
sc("S-KEY-013", "two undated facts on one temporal key: no collision, a possible-overlap warning",
   [put(ENT, {"@": "f:king-14", "drop_bindings": ["b3", "b4"]})],
   [op("put", EQ("receipt.warnings", [{"code": "KHG-L008", "ids": ["f:king-13", "f:king-14"]}]),
       records=[{"@": "f:king-13", "drop_bindings": ["b3", "b4"]}])],
   ["critique CONS-11"], ["key_constraint", "valid_time"])
sc("S-KEY-014", "same start (R01 case 3b): close_older does not apply, the action is dispute",
   [put(ENT, {"@": "f:king-13", "set_binding": {"b3": T("+1643-05-14T00:00:00Z")}, "drop_bindings": ["b4"]})],
   [op("put", ERR("KHG-D016", **coll("f:king-14", "close_older", cf("f:king-13", "same_start", "distinct", "dispute"))),
       records=[{"@": "f:king-14", "drop_bindings": ["b4"]}])],
   ["critique SEM-04 (3b)", "B identity table 3b"], ["key_constraint", "valid_time"])
sc("S-KEY-015", "backfill (X4): the incoming fact is the older one, so it is the one closed",
   [put(ENT, {"@": "f:king-14", "drop_bindings": ["b4"]})],
   [op("put", ERR("KHG-D016", **coll("f:king-13", "close_older", cf("f:king-14", "backfill", "distinct", "close_incoming"))),
       records=[K13]),
    op("put", EQ("receipt.records", [["f:king-13", 1, "created"]]), records=["@f:king-13"])],
   ["critique SEM-04 (X4)", "B identity table X4"], ["key_constraint", "valid_time"])
sc("S-KEY-016", "a refining claim on the same key is a merge: it becomes a new version of the stored fact",
   [put(ENT, {"@": "f:king-14", "drop_bindings": ["b4"], "set_evidence": {"e1": {"supports": ["b1", "b2", "b3"]}}})],
   [op("put", ERR("KHG-D016", **coll("f:king-14b", "close_older", cf("f:king-14", "same_start", "refines", "merge"))),
       records=[{"@": "f:king-14", "set": {"id": "f:king-14b"}}]),
    op("put", EQ("receipt.records", [["f:king-14", 2, "versioned"]]),
       records=[{"@": "f:king-14", "set_evidence": {"e1": {"supports": ["b1", "b2", "b3"]}},
                 "add_evidence": [dict(CUR, supports=["b4"])]}])],
   ["critique SEM-05 (R01 case 1, C3-R10)"], ["key_constraint", "valid_time"])
sc("S-KEY-017", "a new claim on a disputed key joins the dispute",
   [put(ENT, "@f:born-skłodowska-warszawa"), {"apply": DISPUTE}],
   [op("put", ERR("KHG-D016", **coll("f:born-skłodowska-paris", "dispute",
                                     cf("f:born-skłodowska-kraków", None, "distinct", "dispute"),
                                     cf("f:born-skłodowska-warszawa", None, "distinct", "dispute"))),
       records=[PARIS_MARIA]),
    ev({"op": "transition", "targets": ["f:born-skłodowska-kraków", "f:born-skłodowska-warszawa"], "to": "disputed",
        "records": [PARIS_MARIA], "id": "m:dis-2", "reason": "key_conflict", "evidence": [CUR]},
       EQ("receipt.records", [["f:born-skłodowska-kraków", 2, "versioned"], ["f:born-skłodowska-paris", 1, "created"],
                              ["f:born-skłodowska-warszawa", 3, "versioned"], ["m:dis-2", 1, "created"]])),
    op("get", EQ("status_ref", "m:dis-2"), id="f:born-skłodowska-warszawa")],
   ["critique SEM-09"], ["key_constraint", "atomic_writes"])
sc("S-KEY-018", "one put spanning two relations reports every collision with its own policy",
   [put(ENT, "@f:king-13", "@f:born-skłodowska-warszawa")],
   [op("put", ERR("KHG-D016", collisions=[
       {"record": "f:born-skłodowska-kraków", "policy": "dispute",
        "conflicts": [cf("f:born-skłodowska-warszawa", None, "distinct", "dispute")]},
       {"record": "f:king-14b", "policy": "close_older",
        "conflicts": [cf("f:king-13", "overlap_after_end", "distinct", "dispute")]}]),
       records=[{"@": "f:king-14", "set": {"id": "f:king-14b"}, "set_binding": {"b3": T("+1640-01-01T00:00:00Z")}}, KRA])],
   ["critique CONS-13"], ["key_constraint", "valid_time", "atomic_writes"])
sc("S-KEY-019", "key literals compare exactly: 2019 at year precision and 30 June 2019 are different keys",
   [put(ENT, "@f:pop-łódź-2019")],
   [op("put", EQ("receipt.records", [["f:pop-łódź-2019-q2", 1, "created"]]),
       records=[{"@": "f:pop-łódź-2019", "set": {"id": "f:pop-łódź-2019-q2"},
                 "set_binding": {"b3": T("+2019-06-30T00:00:00Z"),
                                 "b2": {"literal": {"datatype": "quantity", "amount": "+682000", "unit": "1"}}}}])],
   ["critique SEM-13"], ["key_constraint"])
# ------------------------------------------------ lifecycle ------------------------------------------------
sc("S-LIFE-001", "supersede is one event; the walk forward ends at the current belief",
   [put(ENT, KRA)],
   [ev(SUP, EQ("receipt.records", [["f:born-skłodowska-kraków", 2, "versioned"], ["f:born-skłodowska-warszawa", 1, "created"],
                                   ["m:sup-1", 1, "created"]])),
    op("get", EQ("status_ref", "m:sup-1"), id="f:born-skłodowska-kraków"),
    op("supersession_walk", EQ("terminal", [{"id": "f:born-skłodowska-warszawa", "status": "asserted"}]),
       id="f:born-skłodowska-kraków"),
    op("find_by_key", EQ("ids", ["f:born-skłodowska-warszawa"]), relation="born_in", key=KEYMARIA)],
   ["A C2-13 passed", "C S-SUP-001 passed"])
sc("S-LIFE-002", "the walk runs backward",
   [put(ENT, KRA), {"apply": SUP}],
   [op("supersession_walk", EQ("terminal.ids", ["f:born-skłodowska-kraków"]), id="f:born-skłodowska-warszawa", direction="backward")],
   ["A C2-14 passed", "B S051"])
sc("S-LIFE-003", "the walk branches on conflation",
   [put(ENT, {"kind": "entity", "id": "ex:lactic_acidosis", "types": ["Outcome"], "label": "lactic acidosis"},
        {"@": "f:coadmin-1", "set": {"id": "f:coadmin-0"}, "drop": ["confidence"]})],
   [ev({"op": "supersede", "id": "m:sup-9", "superseded": ["f:coadmin-0"],
        "records": ["@f:coadmin-1", {"@": "f:coadmin-1", "set": {"id": "f:coadmin-2", "evidence": [dict(CUR, supports=["b1", "b2", "b3"])]},
                                     "drop": ["confidence"], "set_binding": {"b3": {"entity": "ex:lactic_acidosis"}}}],
        "reason": "conflation", "evidence": [CUR]},
       EQ("receipt.records", [["f:coadmin-0", 2, "versioned"], ["f:coadmin-1", 1, "created"], ["f:coadmin-2", 1, "created"],
                              ["m:sup-9", 1, "created"]])),
    op("supersession_walk", EQ("terminal.ids", ["f:coadmin-1", "f:coadmin-2"]), id="f:coadmin-0")],
   ["B S050", "C S-SUP-002"])
sc("S-LIFE-004", "a superseding fact must be asserted when the event runs, so events cannot form a cycle",
   [put(ENT, KRA), {"apply": SUP}],
   [ev({"op": "supersede", "id": "m:sup-2", "superseded": ["f:born-skłodowska-warszawa"],
        "superseding": ["f:born-skłodowska-kraków"], "reason": "correction", "evidence": [CUR]}, ERR("KHG-D011"))],
   ["B S053 (cycle, KHG-D012 stays a container check)", "C S-SUP-003", "critique SEM-11"])
sc("S-LIFE-005", "put cannot create a record in status superseded",
   [put(ENT, "@f:born-skłodowska-warszawa")], [op("put", ERR("KHG-D014"), records=["@f:born-skłodowska-kraków"])],
   ["A C2-15 passed"])
sc("S-LIFE-006", "retraction writes khg:retracts; a retracted fact does not come back",
   [put(ENT, "@f:reg-1")],
   [ev({"op": "transition", "targets": ["f:reg-1"], "to": "retracted", "id": "m:ret-1", "reason": "withdrawn",
        "evidence": [CUR]}, EQ("receipt.records", [["f:reg-1", 2, "versioned"], ["m:ret-1", 1, "created"]])),
    op("get", EQ("status_ref", "m:ret-1"), id="f:reg-1"),
    ev({"op": "transition", "targets": ["f:reg-1"], "to": "asserted", "evidence": [CUR]}, ERR("KHG-D014"))],
   ["A C2-16 passed"])
sc("S-LIFE-007", "retracting a supersession record restores the superseded fact (undo) and drops its status_ref",
   [put(ENT, {"kind": "entity", "id": "ex:MDM2", "types": ["Gene"], "label": "MDM2"}, "@f:reg-1"),
    {"apply": {"op": "supersede", "id": "m:sup-3", "superseded": ["f:reg-1"],
               "records": [{"@": "f:reg-1", "set": {"id": "f:reg-2"}, "set_binding": {"b3": {"entity": "ex:MDM2"}}}],
               "reason": "correction", "evidence": [CUR]}}],
   [ev({"op": "transition", "targets": ["m:sup-3"], "to": "retracted", "id": "m:ret-3", "reason": "withdrawn", "evidence": [CUR]},
       EQ("receipt.records", [["f:reg-1", 3, "versioned"], ["m:ret-3", 1, "created"], ["m:sup-3", 2, "versioned"]])),
    op("get", EQ("status", "asserted"), id="f:reg-1"),
    op("get", EQ("status_ref", None), id="f:reg-1"),
    op("get", EQ("status", "asserted"), id="f:reg-2")],
   ["B S052", "critique SEM-10"])
sc("S-LIFE-008", "binding a goal slot is a new version with the same bid",
   [put(ENT, LOUIS16, "@g:who-1774")],
   [op("put", EQ("receipt.records", [["g:who-1774", 2, "versioned"]]), records=[BOUND]),
    op("get", EQ("derived.n_unbound", 0), id="g:who-1774")],
   ["A C2-19 passed", "B S070"])
sc("S-LIFE-009", "a fully bound goal becomes asserted by a transition that drops the goal block",
   [put(ENT, LOUIS16, "@f:king-14", BOUND)],
   [ev({"op": "transition", "targets": ["g:who-1774"], "to": "asserted", "evidence": [CUR]},
       EQ("receipt.records", [["g:who-1774", 2, "versioned"]])),
    op("get", EQ("goal", None), id="g:who-1774"),
    op("find_by_key", EQ("ids", ["g:who-1774"]), relation="position_held", key=KEYPOS, where={"as_of": "+1780-01-01T00:00:00Z"})],
   ["C S-LIFE-002"], ["key_constraint", "valid_time"])
sc("S-LIFE-010", "a goal with an unbound slot cannot become asserted",
   [put(ENT, "@g:who-1774")],
   [ev({"op": "transition", "targets": ["g:who-1774"], "to": "asserted", "evidence": [CUR]}, ERR("KHG-C005"))],
   ["C S-LIFE-002"])
sc("S-LIFE-011", "an asserted fact cannot become a goal",
   [put(ENT, "@f:reg-1")],
   [ev({"op": "transition", "targets": ["f:reg-1"], "to": "goal", "evidence": [CUR]}, ERR("KHG-D014"))],
   ["C S-LIFE-001 passed"])
sc("S-LIFE-012", "a supersession chain A -> B -> C: the walk's terminal is C, whose predecessors stay superseded",
   [put(ENT, KRA), {"apply": SUP}],
   [ev({"op": "supersede", "id": "m:sup-2", "superseded": ["f:born-skłodowska-warszawa"], "records": [PARIS_MARIA],
        "reason": "correction", "evidence": [CUR]},
       EQ("receipt.records", [["f:born-skłodowska-paris", 1, "created"], ["f:born-skłodowska-warszawa", 2, "versioned"],
                              ["m:sup-2", 1, "created"]])),
    op("supersession_walk", EQ("terminal", [{"id": "f:born-skłodowska-paris", "status": "asserted"}]),
       id="f:born-skłodowska-kraków"),
    op("supersession_walk", EQ("steps.count", 2), id="f:born-skłodowska-kraków")],
   ["critique SEM-11"])
sc("S-LIFE-013", "undoing a keyed correction must resolve the superseding fact, here by a dispute",
   [put(ENT, KRA), {"apply": SUP}],
   [ev({"op": "transition", "targets": ["m:sup-1"], "to": "retracted", "id": "m:ret-9", "reason": "withdrawn", "evidence": [CUR]},
       ERR("KHG-D016")),
    ev({"op": "transition", "targets": ["m:sup-1"], "to": "retracted", "id": "m:ret-9", "reason": "withdrawn",
        "resolve_superseding": "dispute", "dispute_id": "m:dis-9", "evidence": [CUR]},
       EQ("receipt.records", [["f:born-skłodowska-kraków", 3, "versioned"], ["f:born-skłodowska-warszawa", 2, "versioned"],
                              ["m:dis-9", 1, "created"], ["m:ret-9", 1, "created"], ["m:sup-1", 2, "versioned"]])),
    op("get", EQ("status", "disputed"), id="f:born-skłodowska-kraków"),
    op("get", EQ("status_ref", "m:dis-9"), id="f:born-skłodowska-warszawa")],
   ["critique SEM-19"], ["key_constraint"])
POPA = {"@": "f:pop-łódź-2019", "set": {"id": "f:pop-a"}}
POPB = {"@": "f:pop-łódź-2019", "set": {"id": "f:pop-b"},
        "set_binding": {"b2": {"literal": {"datatype": "quantity", "amount": "+680000", "unit": "1"}}}}
sc("S-LIFE-014", "a new version of a superseding fact must keep the correction's key digest",
   [put(ENT, POPA),
    {"apply": {"op": "supersede", "id": "m:sup-p", "superseded": ["f:pop-a"], "records": [POPB], "reason": "correction",
               "evidence": [CUR]}}],
   [op("put", ERR("KHG-D011"),
       records=[dict(POPB, set_binding={"b2": {"literal": {"datatype": "quantity", "amount": "+680000", "unit": "1"}},
                                        "b3": T("+2019-06-30T00:00:00Z")}, add_evidence=[dict(CUR, supports=["b3"])])]),
    op("get", EQ("version", 1), id="f:pop-b")],
   ["critique SEM-11 (put runs D011 on new versions of superseding facts)"], ["key_constraint"])
# ------------------------------------------------ export ------------------------------------------------
sc("S-EXP-001", "load then export khg-json gives the fixture back, header included",
   [LOAD], [op("export", {"container_equals": "@fixture", "ignore": IGN}, format="khg-json")],
   ["C S-EXP-002 passed", "B S060", "critique STORE-HEADER"])
sc("S-EXP-002", "the fixture rebuilt through put and one supersede event exports equal to it (given its header)",
   [put(ENT), put(*[f"@{i}" for i in sorted(REC) if i.startswith(("f:", "g:"))
                    and i not in ("f:born-skłodowska-kraków", "f:born-skłodowska-warszawa")]),
    put(KRA), {"apply": dict(SUP, evidence="@m:sup-1.evidence")}],
   [op("export", {"container_equals": "@fixture", "ignore": IGN}, format="khg-json", header="@fixture.header")],
   ["C S-EXP-001 passed"])
sc("S-EXP-003", "the HIF export validates and equals fixture.hif.json",
   [LOAD], [op("export", {"hif_valid": True, "equals_file": "fixture.hif.json",
                          "ignore": ["khg-version", "khg-recorded-at", "khg-recorded-by"]}, format="hif")],
   ["B S061", "A C2-23", "C S-EXP-004"])
sc("S-EXP-004", "export as_at reconstructs an earlier snapshot",
   [put(ENT, at=ts(1)), put(KRA, at=ts(2)), {"apply": SUP, "at": ts(3)}],
   [op("export", EQ("record.f:born-skłodowska-kraków.status", "asserted"), format="khg-json", as_at=ts(2))],
   ["B S062"], ["transaction_time"])
sc("S-EXP-005", "a history export holds every version and reloads to the same store",
   [put(ENT, at=ts(1)), put(K13, at=ts(2)), {"apply": END13, "at": ts(3)}],
   [op("export", {"select": "versions.f:king-13", "equals": [1, 2], "reload_equal": True}, format="khg-jsonl", content="history")],
   ["B S063", "A C2-24", "C S-EXP-003"], ["history_export", "transaction_time"])
sc("S-EXP-006", "a directed slice exports as a directed HIF file",
   [LOAD], [op("export", {"hif_valid": True, "equals_file": "fixture.directed-slice.hif.json",
                          "ignore": ["khg-version", "khg-recorded-at", "khg-recorded-by"]}, format="hif",
               relations=["born_in", "catalysed_by", "claims", "co_administration_causes", "flight_route", "population",
                          "position_held", "regulates", "station_profile"])],
   ["C §4.3 E12 (directed slice)"])
sc("S-EXP-007", "the same writes on two fresh stores give byte-identical exports",
   [LOAD], [op("export", {"deterministic": True}, format="khg-jsonl")], ["B S080", "A PYTHONHASHSEED check passed"])
sc("S-EXP-008", "a write whose transaction time precedes the store's latest is refused",
   [put(ENT, "@f:reg-1", at=ts(5))],
   [op("apply", ERR("KHG-D018"), at=ts(4), event={"op": "add_evidence", "target": "f:reg-1", "evidence": [CUR]})],
   ["A C2-25", "C C-TX-ORDER"], ["transaction_time"])
sc("S-EXP-009", "a store filled only by put exports its own document id",
   [put(ENT, "@f:reg-1")],
   [op("export", EQ("header.document_id", "store:{store_id}"), format="khg-json"),
    op("export", EQ("header.complete", True), format="khg-json")],
   ["critique STORE-HEADER"])
sc("S-EXP-010", "transaction time increases per store: a new id cannot be written before another id's latest",
   [put(ENT, "@f:reg-1", at=ts(5))],
   [op("put", ERR("KHG-D018"), at=ts(4), records=["@f:coadmin-1"])],
   ["critique SEM-14"], ["transaction_time"])
sc("S-EXP-011", "a slice of claims alone keeps its fact reference as an external node and is not complete",
   [LOAD],
   [op("export", {"hif_valid": True, "select": "metadata.khg-complete", "equals": False}, format="hif", relations=["claims"]),
    op("export", EQ("node._:ref:f:born-louis14-paris.attrs.khg-external", True), format="hif", relations=["claims"])],
   ["critique CONS-14, GL-17"])

# ======================================== core variants (CONS-05) ========================================
DATA_FLAGS_FULL = ["goals", "literal_values", "nesting", "ordered_roles", "special_values"]
CORE_DROP = {"f:route-1", "f:born-scribe", "f:cat-7", "g:who-1774"}  # need ordered_roles, special_values or goals
CORE_VARIANTS = ["S-READ-001", "S-READ-002", "S-READ-003", "S-READ-004", "S-READ-005", "S-READ-007", "S-READ-008",
                 "S-READ-009", "S-READ-010", "S-READ-011", "S-READ-015", "S-READ-016", "S-READ-017", "S-READ-018",
                 "S-TIME-001", "S-KEY-002", "S-KEY-003", "S-EXP-001", "S-EXP-007", "S-VER-006"]


def core_variant(s):
    v = copy.deepcopy(s)
    v["id"] = s["id"] + "c"
    v["title"] = s["title"] + " (capability-limited fixture @fixture[core])"
    v["given"] = [{"load": "@fixture[core]"} if g == LOAD else g for g in v["given"]]
    for st in v["when"]:
        th = st["then"]
        if th.get("select") == "ids":
            th["equals"] = [i for i in th["equals"] if i not in CORE_DROP]
        if st["op"] == "degree" and st["args"].get("node") == "ex:YYZ":
            th["equals"] = 1 if st["args"].get("role") is None else 0
        if st["op"] == "get" and st["args"].get("id") in CORE_DROP:
            st["then"] = EQ("record", None)
        if th.get("container_equals") == "@fixture":
            th["container_equals"] = "@fixture[core]"
    v["precedent"] = [f"core variant of {s['id']}"]
    return v


for sid in CORE_VARIANTS:
    SC.append(core_variant(next(s for s in SC if s["id"] == sid)))

# ======================================== requires (CONS-05) ========================================


def op_flags(s):
    fl = set(s["requires"])
    steps = s["given"] + s["when"]
    for st in steps:
        a = st.get("args", {})
        w = a.get("where", {})
        if "as_of" in w or "valid_mode" in w:
            fl.add("valid_time")
        if "as_at" in w or "as_at" in a or "version" in a:
            fl.add("transaction_time")
        if st.get("op") == "export" and a.get("content") == "history":
            fl.add("history_export")
        if "load" in st and st["load"] == "@fixture":
            fl.update(DATA_FLAGS_FULL)
        if "load" in st and st["load"] == "@fixture[core]":
            fl.update(["literal_values", "nesting"])
        ev = st.get("apply") or a.get("event")
        if ev:
            if ev["op"] in ("supersede",) or (ev["op"] == "transition" and ("id" in ev or ev.get("records"))):
                fl.add("atomic_writes")
            if ev["op"] == "end_validity":
                fl.add("valid_time")
    return sorted(fl)


def resolve(x):
    """@-references and patches resolved to plain records, for the static data-flag pass."""
    if isinstance(x, str) and x.startswith("@"):
        if x == "@entities":
            return copy.deepcopy(ENTITIES)
        rid, _, path = x[1:].partition(".")
        return copy.deepcopy(REC[rid][path]) if path else copy.deepcopy(REC[rid])
    if isinstance(x, dict) and "@" in x:
        r = resolve("@" + x["@"])
        for k, v in x.get("set", {}).items():
            r[k] = v
        bids = {b["bid"]: b for b in r.get("bindings", [])}
        for bid, val in x.get("set_binding", {}).items():
            bids[bid]["value"] = val
        return r
    return x


def data_flags(rec):
    fl = set()
    if not isinstance(rec, dict) or rec.get("kind") != "hyperedge":
        return fl
    if rec.get("status") == "goal":
        fl.add("goals")
    for b in rec.get("bindings", []):
        k = K.vkind(b["value"])
        fl |= {"literal": {"literal_values"}, "special": {"special_values"}, "unbound": {"goals"}}.get(k, set())
        if k == "fact" and not rec["relation"].startswith("khg:"):
            fl.add("nesting")
        if "position" in b:
            fl.add("ordered_roles")
    return fl


for s in SC:
    fl = set(op_flags(s))
    for st in s["given"] + s["when"]:
        items = st.get("put") or (st.get("args", {}).get("records") if st.get("op") == "put" else None) or []
        n_records = sum(len(r) if isinstance(r, list) else 1 for r in (resolve(it) for it in items))
        if n_records > 1 and (st.get("op") == "put" or "at" in st):
            fl.add("atomic_writes")  # a timed multi-record given step cannot be split into several calls
        for it in items:
            rr = resolve(it)
            for r in (rr if isinstance(rr, list) else [rr]):
                fl |= data_flags(r)
        ev = st.get("apply") or st.get("args", {}).get("event")
        if ev:
            for it in ev.get("records", []) or []:
                fl |= data_flags(resolve(it))
    s["requires"] = sorted(fl)

ids = [s["id"] for s in SC]
assert len(ids) == len(set(ids)), "duplicate scenario ids"
for s in SC:
    (OUT / f"{s['id']}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
index = {
    "format": "khg-scenario-index/1.0.0",
    "runner": "khg_contracts.store.conformance.run(factory, *, only=None, capabilities=None) -> EARL-shaped report "
              "(passed, failed, inapplicable, cantTell per scenario)",
    "factory": "factory(schema: Schema, clock: Clock) -> a fresh, empty Store",
    "clock": {"start": "2026-10-01T00:00:00Z", "step_seconds": 1,
              "rule": "one tick per write call; a step's 'at' sets the clock; later ticks continue from it"},
    "requires": "the capabilities a scenario needs: those of the operations and assertions under test (valid_time for "
                "as_of, valid_mode or end_validity; transaction_time for as_at or get(version); history_export for "
                "content history; atomic_writes for a multi-record write), plus the data flags of the records it "
                "writes or loads (literal_values, special_values, goals, nesting, ordered_roles). A scenario that "
                "loads @fixture needs all five data flags; its core variant (id suffix c) loads @fixture[core] and "
                "needs only literal_values and nesting. A store lacking a flag gets 'inapplicable', never 'failed'.",
    "given": "put steps run one call each (one record per call, in the listed order, for a store without "
             "atomic_writes); apply steps run one event; load loads a container into the empty store",
    "references": {"@<id>": "the fixture record with that id", "@entities": "every entity record of the fixture",
                   "@fixture": "the whole fixture container",
                   "@fixture[core]": "the fixture without the records that need ordered_roles, special_values or goals "
                                     "(f:route-1, f:born-scribe, f:cat-7, g:who-1774)",
                   "@<id>.<field>": "that field of the fixture record", "@fixture.header": "the fixture's header"},
    "patch_keys": {"set": "replace or add fields", "drop": "remove fields",
                   "set_binding": "replace the value of the binding with that bid",
                   "drop_bindings": "remove bindings by bid, and those bids from every evidence supports list",
                   "add_evidence": "append evidence records", "set_evidence": "change fields of the evidence record with that id"},
    "pattern": "find patterns are [{role, value, position?}] where value is a C1 value, {\"any\": true} or "
               "{\"any_unbound\": true}; a missing position matches any position; [] matches every fact of the relation",
    "then": {"select + equals": "a projection of the result equals the value (ids, value, version, versions, status, "
                                "status_ref, goal, record, canonical, receipt.records, receipt.warnings, evidence.ids, "
                                "evidence.<id>.<field>, binding.<bid>.<field>, derived.<field>, terminal, terminal.ids, "
                                "steps.count, record.<id>.<field>, versions.<id>, header.<field>, metadata.<field>, "
                                "node.<id>.<path>); '{store_id}' in an expected string is the store's id",
             "error + info": "the call raises; the code is among the error's codes; info matches as a subset "
                             "(objects: listed keys; lists: same length, element-wise)",
             "container_equals": "the export equals that container (header without created_at and generator; records "
                                 "in canonical form), ignoring the listed store-assigned fields",
             "hif_valid": "the export passes the vendored HIF schema and the khg-hif profile",
             "equals_file": "the export equals that file, ignoring the listed attrs keys",
             "reload_equal": "loading the export into a fresh store and exporting again gives the same bytes",
             "deterministic": "two fresh runs give byte-identical output"},
    "projections": {"canonical": "the record in canonical form without version, recorded_at, recorded_by",
                    "derived.<field>": "computed by the runner from the returned record (derived is an optional cache)",
                    "receipt.records": "[id, version, outcome] per written record, sorted by id; outcome created, "
                                       "versioned or noop",
                    "receipt.warnings": "[{code, ids}] lint findings of the write (KHG-L008 possible overlaps)"},
    "count": len(SC),
    "scenarios": [{"id": s["id"], "title": s["title"], "requires": s["requires"], "precedent": s["precedent"]} for s in SC],
}
(OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
by = {}
for s in SC:
    a = s["id"].split("-")[1]
    by[a] = by.get(a, 0) + 1
print(len(SC), "scenarios", by)
