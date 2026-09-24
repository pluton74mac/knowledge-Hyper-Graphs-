"""Declarative C2 conformance scenarios (khg-store-scenario/1.0.0) and a runner. Prototype for design C, §6.4.

A scenario: {"id", "title", "requires": [capabilities], "given": [steps], "when": {"op", "args"},
             "then": {...}, "side_effects": [{"op", "args", "then"}]}
Steps: {"fixture": [ids] | "all"} puts those records (entities first, as the store's put_many does), with
supersessions replayed as supersede events; {"put": record}; {"apply": event}; {"load": "fixture:gate" | [records]}
bulk-loads a container as it is (Store.load).
Then: {"ids": [...]}, {"result": {...}} (subset match), {"count": n}, {"error": code, "info"?, "codes"?},
{"container_equals": "fixture:gate"} (the export parses to the fixture container, header provenance fields aside).
Outcomes (EARL-shaped): passed | failed | inapplicable (a required capability is missing).
"""
from __future__ import annotations

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c1  # noqa: E402
import store as st  # noqa: E402

FIX = {r.get("id", r["kind"]): r for r in c1.load_jsonl(os.path.join(HERE, "gate.khg.jsonl"))}
SCHEMA = next(r for r in FIX.values() if r["kind"] == "relation-schema")


def fixture_input(i):
    """A fixture hyperedge as a writer would put it: store-assigned and derived fields stripped."""
    r = copy.deepcopy(FIX[i])
    if r["kind"] != "hyperedge":
        return r
    for f in ("version", "recorded_at", "recorded_by", "change", "arity", "keys", "superseded_by"):
        r.pop(f, None)
    if r["status"] == "superseded":
        r["status"] = "asserted"
    for b in r["bindings"]:
        b.pop("slot", None)
    for e in r.get("evidence", []):
        e.pop("event_hash", None)
    return r


ENT = [i for i, r in FIX.items() if r.get("kind") == "entity"]
CEO_EV = [{"eid": "ev1", "type": "curated", "mode": "manual", "source": {"doc": "doc:acme-pr-2021"},
           "activity": {"agent": "curator:reviewer-1"}}]

SCENARIOS = [
    {"id": "S-PUT-001", "title": "put of an identical record is a no-op",
     "given": [{"fixture": ENT + ["khg:f02-trial"]}],
     "when": {"op": "put", "args": {"record": "fixture:khg:f02-trial"}},
     "then": {"result": {"created": False, "version": 1}}},
    {"id": "S-PUT-002", "title": "put of changed content appends an immutable version; get(as_at) sees the old one",
     "requires": ["temporal_tx", "special_values", "literal_values"],
     "given": [{"fixture": ENT + ["khg:f09-married"]},
               {"put": {"patch": "khg:f09-married", "set": {"rank": "normal"}, "drop": ["rank_reason"]}}],
     "when": {"op": "get", "args": {"id": "khg:f09-married", "as_at": "2026-09-23T10:00:00Z"}},
     "then": {"result": {"version": 1, "rank": "deprecated"}},
     "side_effects": [{"op": "get", "args": {"id": "khg:f09-married"}, "then": {"result": {"version": 2, "rank": "normal"}}}]},
    {"id": "S-PUT-003", "title": "a candidate cannot be put into the store",
     "given": [{"fixture": ENT}],
     "when": {"op": "put", "args": {"record": {"patch": "khg:f02-trial", "set": {"status": "candidate"}}}},
     "then": {"error": "TRANSITION"}},
    {"id": "S-PUT-004", "title": "an unbound value is accepted in a goal and rejected in an asserted fact",
     "requires": ["special_values"],
     "given": [{"fixture": ENT + ["khg:f14-goal"]}],
     "when": {"op": "put", "args": {"record": {"patch": "khg:f14-goal", "set": {"id": "khg:f15", "status": "asserted",
                                                                               "evidence": CEO_EV}}}},
     "then": {"error": "VALIDATION", "codes": ["S-UNBOUND"]}},
    {"id": "S-INC-001", "title": "incident: every hyperedge in which the node fills a role, ordered by id, default filter",
     "requires": ["special_values", "literal_values"],
     "given": [{"fixture": ENT + ["khg:f01-treats", "khg:f02-trial", "khg:f04-coadmin", "khg:f14-goal"]}],
     "when": {"op": "incident", "args": {"node": "drug:metformin"}},
     "then": {"ids": ["khg:f01-treats", "khg:f02-trial", "khg:f04-coadmin"]}},
    {"id": "S-INC-002", "title": "incident with a role filter; a node in two roles of one fact is returned once",
     "given": [{"fixture": ENT + ["khg:f02-trial", "khg:f04-coadmin"]}],
     "when": {"op": "incident", "args": {"node": "drug:metformin", "role": "background_therapy"}},
     "then": {"ids": ["khg:f02-trial"]}},
    {"id": "S-INC-003", "title": "incident on a hyperedge id returns the facts that reference it (nesting)",
     "requires": ["nesting"],
     "given": [{"fixture": ENT + ["khg:f02-trial", "khg:f13-reported"]}],
     "when": {"op": "incident", "args": {"node": "khg:f02-trial"}},
     "then": {"ids": ["khg:f13-reported"]}},
    {"id": "S-INC-004", "title": "incident with where.status includes goals; pagination is stable",
     "requires": ["special_values", "literal_values"],
     "given": [{"fixture": ENT + ["khg:f01-treats", "khg:f14-goal"]}],
     "when": {"op": "incident", "args": {"node": "disease:T1DM", "where": {"status": ["asserted", "goal"]}, "limit": 1}},
     "then": {"ids": ["khg:f14-goal"]}},
    {"id": "S-FIND-001", "title": "find at_least: a repeated role is matched as a multiset",
     "given": [{"fixture": ENT + ["khg:f04-coadmin", "khg:f02-trial"]}],
     "when": {"op": "find", "args": {"relation": "co_administration_causes", "pattern": [
         {"role": "agent", "value": {"entity": "drug:insulin"}}, {"role": "agent", "value": {"entity": "drug:metformin"}}]}},
     "then": {"ids": ["khg:f04-coadmin"]}},
    {"id": "S-FIND-002", "title": "find exact: the pattern must equal the whole binding multiset",
     "given": [{"fixture": ENT + ["khg:f04-coadmin"]}],
     "when": {"op": "find", "args": {"relation": "co_administration_causes", "match": "exact", "pattern": [
         {"role": "agent", "value": {"entity": "drug:insulin"}}, {"role": "agent", "value": {"entity": "drug:metformin"}}]}},
     "then": {"ids": []}},
    {"id": "S-FIND-003", "title": "find on a typed literal compares datatype and precision",
     "requires": ["literal_values"],
     "given": [{"fixture": ENT + ["khg:f07-zurich"]}],
     "when": {"op": "find", "args": {"relation": "population_count", "pattern": [
         {"role": "point_in_time", "value": {"literal": "2023", "datatype": "time", "precision": "day"}}]}},
     "then": {"ids": []}},
    {"id": "S-KEY-001", "title": "find_by_key with as_of returns the fact valid at that instant",
     "requires": ["temporal_valid", "key_index", "literal_values"],
     "given": [{"fixture": ENT + ["khg:f06-louis"]}],
     "when": {"op": "find_by_key", "args": {"relation": "position_held",
                                            "key": [{"role": "position", "value": {"entity": "x:Roi_de_France"}}],
                                            "where": {"as_of": "1700"}}},
     "then": {"ids": ["khg:f06-louis"]},
     "side_effects": [{"op": "find_by_key", "args": {"relation": "position_held", "key": [
         {"role": "position", "value": {"entity": "x:Roi_de_France"}}], "where": {"as_of": "1715-09-01"}},
         "then": {"ids": []}}]},
    {"id": "S-KEY-002", "title": "a key collision is never resolved silently: KeyCollision with the declared policy",
     "requires": ["key_index"],
     "given": [{"fixture": ENT + ["khg:f12-ceo-bob"]}],
     "when": {"op": "put", "args": {"record": "fixture:khg:f11-ceo-alice"}},
     "then": {"error": "KEY_COLLISION", "info": {"conflicts": ["khg:f12-ceo-bob"], "suggested": "supersede"}}},
    {"id": "S-SUP-001", "title": "supersede is atomic: record, status, pointer; the walk terminates at the current belief",
     "requires": ["atomic_events", "key_index"],
     "given": [{"fixture": ENT + ["khg:f11-ceo-alice"]},
               {"apply": {"op": "supersede", "id": "khg:s01", "superseded": ["khg:f11-ceo-alice"],
                          "record": "fixture:khg:f12-ceo-bob", "reason": "incorrect", "evidence": CEO_EV,
                          "actor": "curator:reviewer-1"}}],
     "when": {"op": "supersession_walk", "args": {"id": "khg:f11-ceo-alice"}},
     "then": {"result": {"terminal": ["khg:f12-ceo-bob"]}},
     "side_effects": [
         {"op": "get", "args": {"id": "khg:f11-ceo-alice"}, "then": {"result": {"status": "superseded", "version": 2,
                                                                                 "superseded_by": ["khg:f12-ceo-bob"]}}},
         {"op": "find_by_key", "args": {"relation": "chief_executive",
                                        "key": [{"role": "organisation", "value": {"entity": "org:Acme"}}]},
          "then": {"ids": ["khg:f12-ceo-bob"]}},
         {"op": "supersession_walk", "args": {"id": "khg:f12-ceo-bob", "direction": "backward"},
          "then": {"result": {"terminal": ["khg:f11-ceo-alice"]}}}]},
    {"id": "S-TIME-001", "title": "end_validity closes valid time in a new version; status stays asserted (world change, not supersession)",
     "requires": ["temporal_valid", "temporal_tx", "key_index"],
     "given": [{"fixture": ENT + ["khg:f12-ceo-bob"]},
               {"apply": {"op": "end_validity", "target": "khg:f12-ceo-bob", "to": "2025-12-31",
                          "end_cause": "wd:Q24637", "actor": "curator:reviewer-1"}}],
     "when": {"op": "find_by_key", "args": {"relation": "chief_executive",
                                            "key": [{"role": "organisation", "value": {"entity": "org:Acme"}}],
                                            "where": {"as_of": "2026-06-01"}}},
     "then": {"ids": []},
     "side_effects": [{"op": "get", "args": {"id": "khg:f12-ceo-bob"},
                       "then": {"result": {"status": "asserted", "version": 2,
                                           "valid_time": {"from": "2019-01-01", "to": "2025-12-31", "end_cause": "wd:Q24637"}}}}]},
    {"id": "S-LIFE-001", "title": "the transition table forbids asserted -> goal",
     "given": [{"fixture": ENT + ["khg:f02-trial"]}],
     "when": {"op": "apply", "args": {"event": {"op": "transition", "target": "khg:f02-trial", "to": "goal"}}},
     "then": {"error": "TRANSITION"}},
    {"id": "S-EXP-001", "title": "the gate fixture rebuilt through put and one supersede event exports equal to it",
     "requires": ["atomic_events", "history_export", "key_index", "literal_values", "nesting", "ordered_roles", "special_values", "temporal_tx", "temporal_valid"],
     "given": [{"fixture": "all"}],
     "when": {"op": "export", "args": {"format": "khg-jsonl"}},
     "then": {"container_equals": "fixture:gate"}},
    {"id": "S-EXP-002", "title": "load keeps versions and transaction times: load of the gate container exports equal to it",
     "requires": ["literal_values", "nesting", "ordered_roles", "special_values"],
     "given": [{"load": "fixture:gate"}],
     "when": {"op": "export", "args": {"format": "khg-jsonl"}},
     "then": {"container_equals": "fixture:gate"},
     "side_effects": [
         {"op": "get", "args": {"id": "khg:f11-ceo-alice"},
          "then": {"result": {"version": 2, "status": "superseded", "recorded_at": "2026-09-23T11:00:00Z",
                              "change": {"op": "supersede", "ref": "khg:s01"}}}},
         {"op": "supersession_walk", "args": {"id": "khg:f11-ceo-alice"}, "then": {"result": {"terminal": ["khg:f12-ceo-bob"]}}},
         {"op": "incident", "args": {"node": "gene:TP53"}, "then": {"ids": ["khg:f03-regulates"]}}]},
]


def resolve(x):
    if isinstance(x, str) and x.startswith("fixture:"):
        return fixture_input(x[len("fixture:"):])
    if isinstance(x, dict) and "patch" in x:
        r = fixture_input(x["patch"])
        r.update(copy.deepcopy(x.get("set", {})))
        for f in x.get("drop", []):
            r.pop(f, None)
        return r
    if isinstance(x, dict):
        return {k: resolve(v) for k, v in x.items()}
    if isinstance(x, list):
        return [resolve(v) for v in x]
    return x


def load_all(s):
    """The whole fixture: entities and hyperedges in id order, Alice asserted, then the supersession event."""
    ids = sorted(i for i, r in FIX.items() if r.get("kind") == "hyperedge")
    s.put_many([resolve(f"fixture:{i}") for i in ENT])
    for i in ids:
        if i == "khg:f12-ceo-bob":
            continue
        s.put(resolve(f"fixture:{i}"), actor="p2-gate-fixture/1.0.0",
              at=FIX[i]["recorded_at"] if FIX[i]["status"] != "superseded" else "2026-09-23T10:00:00Z")
    sup = FIX["khg:s01"]
    s.apply({"op": "supersede", "id": "khg:s01", "superseded": ["khg:f11-ceo-alice"],
             "record": resolve("fixture:khg:f12-ceo-bob"), "reason": sup["reason"], "reason_detail": sup["reason_detail"],
             "evidence": sup["evidence"], "at": sup["recorded_at"]}, actor="p2-gate-fixture/1.0.0")


def call(s, op, args):
    a = resolve(args)
    if op == "put":
        return s.put(a["record"])
    if op == "get":
        return s.get(a["id"], as_at=a.get("as_at"))
    if op == "incident":
        return s.incident(a["node"], role=a.get("role"), where=st.Where.from_json(a.get("where")), limit=a.get("limit"))
    if op == "find":
        return s.find(a["relation"], a["pattern"], match=a.get("match", "at_least"), where=st.Where.from_json(a.get("where")))
    if op == "find_by_key":
        return s.find_by_key(a["relation"], a["key"], where=st.Where.from_json(a.get("where")))
    if op == "supersession_walk":
        return s.supersession_walk(a["id"], direction=a.get("direction", "forward"))
    if op == "apply":
        return s.apply(a["event"])
    if op == "export":
        return s.export(a.get("format", "khg-jsonl"))
    raise ValueError(op)


PROVENANCE = ("as_at", "created_at", "created_by", "title", "description")


def container_lines(x):
    if x == "fixture:gate":
        return c1.load_jsonl(os.path.join(HERE, "gate.khg.jsonl"))
    if isinstance(x, str):
        return [json.loads(ln) for ln in x.splitlines() if ln.strip()]
    return list(x)


def same_container(a, b):
    """Structural equality of two containers (F10), ignoring the header's provenance fields."""
    a, b = container_lines(a), container_lines(b)
    strip = lambda h: {k: v for k, v in h.items() if k not in PROVENANCE}  # noqa: E731
    return len(a) == len(b) and c1.cjson(strip(a[0])) == c1.cjson(strip(b[0])) and \
        all(c1.cjson(x) == c1.cjson(y) for x, y in zip(a[1:], b[1:]))


def subset(want, got):
    if isinstance(want, dict):
        return isinstance(got, dict) and all(k in got and subset(v, got[k]) for k, v in want.items())
    return want == got


def check(then, got=None, err=None):
    if "error" in then:
        if err is None or err.code != then["error"]:
            return False
        if "info" in then and not subset(then["info"], err.info):
            return False
        if "codes" in then:
            codes = {f["code"] for f in err.info.get("findings", [])}
            return set(then["codes"]) <= codes
        return True
    if err is not None:
        return False
    if "container_equals" in then:
        return same_container(got, then["container_equals"])
    if "count" in then:
        return len(got) == then["count"]
    if "ids" in then:
        return [r["id"] for r in got] == then["ids"]
    if "result" in then:
        return subset(then["result"], got)
    return False


def run(factory=st.MemoryStore, *, capabilities=None):
    """factory(schemas, clock) -> an empty store; capabilities default to the store's own flags."""
    report = []
    for sc in SCENARIOS:
        s = factory([SCHEMA], st.TickClock())
        caps = s.capabilities if capabilities is None else frozenset(capabilities)
        if not set(sc.get("requires", [])) <= caps:
            report.append({"test": sc["id"], "outcome": "inapplicable"})
            continue
        for g in sc["given"]:
            if "fixture" in g:
                if g["fixture"] == "all":
                    load_all(s)
                else:
                    s.put_many([resolve(f"fixture:{i}") for i in g["fixture"]])
            elif "put" in g:
                s.put(resolve(g["put"]))
            elif "apply" in g:
                s.apply(resolve(g["apply"]))
            elif "load" in g:
                s.load(container_lines(g["load"]))
        got = err = None
        try:
            got = call(s, sc["when"]["op"], sc["when"]["args"])
        except st.StoreError as e:
            err = e
        ok = check(sc["then"], got, err)
        for se in sc.get("side_effects", []):
            try:
                ok &= check(se["then"], call(s, se["op"], se["args"]))
            except st.StoreError as e:
                ok &= check(se["then"], None, e)
        report.append({"test": sc["id"], "outcome": "passed" if ok else "failed", "title": sc["title"],
                       **({} if ok else {"got": repr(got)[:300], "error": repr(err)})})
    return report


if __name__ == "__main__":
    rep = run()
    for r in rep:
        print(r["outcome"].ljust(12), r["test"], r.get("title", ""), r.get("got", ""), r.get("error", ""))
    print(sum(r["outcome"] == "passed" for r in rep), "passed of", len(rep))
    rep2 = run(capabilities=frozenset({"literal_values", "nesting"}))  # a backend without temporal/key/atomic/history capabilities
    print("capability-limited backend:", {o: sum(r["outcome"] == o for r in rep2) for o in ("passed", "failed", "inapplicable")})
    with open(os.path.join(HERE, "conformance-results.json"), "w", encoding="utf-8") as f:
        json.dump({"full": rep, "limited": {"capabilities": ["literal_values", "nesting"], "results": rep2}}, f, indent=1)
    with open(os.path.join(HERE, "conformance-scenarios.json"), "w", encoding="utf-8") as f:
        json.dump({"format": "khg-store-scenario/1.0.0", "scenarios": SCENARIOS}, f, ensure_ascii=False, indent=1)
