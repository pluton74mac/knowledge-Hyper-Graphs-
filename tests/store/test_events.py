"""W8: the four atomic events of ``apply`` (DESIGN §2.7, §2.8.1, §6.2): what each writes, the records it makes,
the codes it raises and that a refused event writes nothing."""
from __future__ import annotations

import copy

import pytest

from khg_contracts.errors import CapabilityMissing, KeyCollision, NotFound, ValidationError, VersionError
from khg_contracts.record import normalize
from khg_contracts.store import ALL_FLAGS, MemoryStore, ScenarioClock, Where

KRAKOW = {"set": {"status": "asserted"}, "drop": ["status_ref"]}


def snapshot(s):
    return [(r["id"], r.get("version")) for r in s.iter_records(content="history")]


@pytest.fixture()
def maria(ms, entities, rec):
    """The store holding the entities and the wrong (Kraków) birthplace, asserted."""
    ms.put(entities, actor="t")
    ms.put(rec("f:born-skłodowska-kraków", **KRAKOW), actor="t")
    return ms


def supersede(rec, cur, **extra):
    return {"op": "supersede", "id": "m:sup-1", "superseded": ["f:born-skłodowska-kraków"],
            "records": [rec("f:born-skłodowska-warszawa")], "reason": "correction",
            "note": "birthplace is Warsaw, per the curated biography", "evidence": [cur], **extra}


# ------------------------------------------------------------------------------------------------ supersede


def test_supersede_writes_the_fixture_lifecycle_record(maria, rec, cur, fixture_doc):
    event = supersede(rec, cur, evidence=copy.deepcopy(rec("m:sup-1")["evidence"]))
    receipt = maria.apply(event, actor="curator")
    assert receipt["records"] == [("f:born-skłodowska-kraków", 2, "versioned"),
                                  ("f:born-skłodowska-warszawa", 1, "created"), ("m:sup-1", 1, "created")]
    stored = {k: v for k, v in maria.get("m:sup-1").items() if k not in ("version", "recorded_at", "recorded_by")}
    assert stored == normalize(rec("m:sup-1"))  # bids b1 (superseding) and b2 (superseded), supports defaulted
    old = maria.get("f:born-skłodowska-kraków")
    assert (old["status"], old["status_ref"]) == ("superseded", "m:sup-1")
    assert maria.get("f:born-skłodowska-warszawa")["status"] == "asserted"


def test_supersede_checks_its_preconditions(maria, rec, cur):
    before = snapshot(maria)
    with pytest.raises(NotFound) as e:
        maria.apply(supersede(rec, cur, superseded=["f:nope"]), actor="t")
    assert e.value.codes == ("KHG-D002",) and e.value.info == {"id": "f:nope"}
    with pytest.raises(VersionError) as e:  # the event record exists already
        maria.apply(supersede(rec, cur, records=[rec("f:born-skłodowska-kraków", **KRAKOW)],
                              superseded=["f:born-skłodowska-kraków"]), actor="t")
    assert e.value.codes == ("KHG-D014",)
    with pytest.raises(VersionError) as e:  # a records entry must arrive as asserted
        maria.apply(supersede(rec, cur, records=[rec("f:born-skłodowska-warszawa", set={"status": "quoted"})]),
                    actor="t")
    assert e.value.codes == ("KHG-D014",)
    other_person = rec("f:born-skłodowska-warszawa", set={"id": "f:born-x"},
                       set_binding={"b1": {"entity": "ex:Pierre_Curie"}})
    with pytest.raises(VersionError) as e:  # a correction keeps the key
        maria.apply(supersede(rec, cur, records=[other_person]), actor="t")
    assert e.value.codes == ("KHG-D011",)
    with pytest.raises(ValidationError) as e:  # the reason is outside the relation's list
        maria.apply(supersede(rec, cur, reason="whim"), actor="t")
    assert e.value.codes == ("KHG-S026",)
    with pytest.raises(ValidationError) as e:
        maria.apply(supersede(rec, cur, superseded=[]), actor="t")
    assert e.value.codes == ("KHG-C010",)
    assert snapshot(maria) == before


def test_a_superseded_fact_is_frozen_and_cannot_supersede(maria, rec, cur):
    maria.apply(supersede(rec, cur), actor="t")
    with pytest.raises(VersionError) as e:
        maria.apply({"op": "add_evidence", "target": "f:born-skłodowska-kraków", "evidence": [cur]}, actor="t")
    assert e.value.codes == ("KHG-D013",)
    with pytest.raises(VersionError) as e:
        maria.apply({"op": "supersede", "id": "m:sup-2", "superseded": ["f:born-skłodowska-warszawa"],
                     "superseding": ["f:born-skłodowska-kraków"], "reason": "correction", "evidence": [cur]},
                    actor="t")
    assert e.value.codes == ("KHG-D011",)
    with pytest.raises(VersionError) as e:  # the event id is taken
        maria.apply(supersede(rec, cur, records=[rec("f:born-skłodowska-warszawa", set={"id": "f:w2"})]),
                    actor="t")
    assert e.value.codes == ("KHG-D014",)


def test_events_need_atomic_writes(schema, entities, rec, cur):
    s = MemoryStore(schema, clock=ScenarioClock(), capabilities=ALL_FLAGS - {"atomic_writes"})
    for e in entities:
        s.put(e, actor="t")
    s.put(rec("f:born-skłodowska-kraków", **KRAKOW), actor="t")
    for event in (supersede(rec, cur),
                  {"op": "transition", "targets": ["f:born-skłodowska-kraków"], "to": "retracted", "id": "m:r",
                   "reason": "withdrawn", "evidence": [cur]},
                  {"op": "transition", "targets": ["f:born-skłodowska-kraków"], "to": "disputed", "id": "m:d",
                   "reason": "curator", "evidence": [cur], "records": [rec("f:born-skłodowska-warszawa")]}):
        with pytest.raises(CapabilityMissing) as e:
            s.apply(event, actor="t")
        assert e.value.flag == "atomic_writes"
    receipt = s.apply({"op": "add_evidence", "target": "f:born-skłodowska-kraków", "evidence": [cur]}, actor="t")
    assert receipt["records"] == [("f:born-skłodowska-kraków", 2, "versioned")]


# ------------------------------------------------------------------------------------------------ transition


def test_a_dispute_binds_its_facts_and_a_new_claim_joins_it(ms, entities, rec, cur):
    ms.put(entities + [rec("f:born-skłodowska-warszawa")], actor="t")
    event = {"op": "transition", "targets": ["f:born-skłodowska-warszawa"], "to": "disputed",
             "records": [rec("f:born-skłodowska-kraków", **KRAKOW)], "id": "m:dis-1", "reason": "key_conflict",
             "evidence": [cur]}
    receipt = ms.apply(event, actor="t")
    assert receipt["records"] == [("f:born-skłodowska-kraków", 1, "created"),
                                  ("f:born-skłodowska-warszawa", 2, "versioned"), ("m:dis-1", 1, "created")]
    dispute = ms.get("m:dis-1")
    assert [(b["bid"], b["role"], b["value"]["fact"]) for b in dispute["bindings"]] == \
        [("b2", "khg:disputed", "f:born-skłodowska-kraków"), ("b1", "khg:disputed", "f:born-skłodowska-warszawa")]
    assert dispute["reason"] == "key_conflict" and dispute["evidence"][0]["supports"] == ["b1", "b2"]
    assert {ms.get(i)["status_ref"] for i in ("f:born-skłodowska-kraków", "f:born-skłodowska-warszawa")} == \
        {"m:dis-1"}
    with pytest.raises(ValidationError) as e:  # a dispute binds at least two facts
        ms.apply({"op": "transition", "targets": ["f:born-skłodowska-warszawa"], "to": "disputed", "id": "m:dis-2",
                  "reason": "curator", "evidence": [cur]}, actor="t")
    assert e.value.codes == ("KHG-S003",)
    with pytest.raises(ValidationError) as e:
        ms.apply(dict(event, id=None), actor="t")
    assert e.value.codes == ("KHG-C010",)


def test_retraction_and_its_terminal_status(ms, entities, rec, cur):
    ms.put(entities + [rec("f:reg-1")], actor="t")
    retract = {"op": "transition", "targets": ["f:reg-1"], "to": "retracted", "id": "m:ret-1", "reason": "withdrawn",
               "evidence": [cur]}
    with pytest.raises(ValidationError) as e:  # a retraction names its khg:retracts record
        ms.apply({k: v for k, v in retract.items() if k != "id"}, actor="t")
    assert e.value.codes == ("KHG-C010",)
    assert ms.apply(retract, actor="t")["records"] == [("f:reg-1", 2, "versioned"), ("m:ret-1", 1, "created")]
    for to in ("retracted", "asserted", "disputed"):
        with pytest.raises(VersionError) as e:
            ms.apply(dict(retract, id="m:ret-2", to=to, records=[]), actor="t")
        assert e.value.codes == ("KHG-D014",)
    with pytest.raises(VersionError) as e:  # a khg:retracts record is never retracted
        ms.apply(dict(retract, targets=["m:ret-1"], id="m:ret-3"), actor="t")
    assert e.value.codes == ("KHG-D014",)
    with pytest.raises(ValidationError) as e:
        ms.apply(dict(retract, id="m:ret-4", resolve_superseding="ignore"), actor="t")
    assert e.value.codes == ("KHG-C002",)


def test_undo_restores_the_superseded_fact(maria, rec, cur):
    maria.apply(supersede(rec, cur), actor="t")
    with pytest.raises(KeyCollision):  # the restored fact collides with its correction (S-LIFE-013)
        maria.apply({"op": "transition", "targets": ["m:sup-1"], "to": "retracted", "id": "m:ret-1",
                     "reason": "withdrawn", "evidence": [cur]}, actor="t")
    receipt = maria.apply({"op": "transition", "targets": ["m:sup-1"], "to": "retracted", "id": "m:ret-1",
                           "reason": "withdrawn", "resolve_superseding": "retract", "evidence": [cur]}, actor="t")
    assert receipt["records"] == [("f:born-skłodowska-kraków", 3, "versioned"),
                                  ("f:born-skłodowska-warszawa", 2, "versioned"), ("m:ret-1", 1, "created"),
                                  ("m:sup-1", 2, "versioned")]
    krakow = maria.get("f:born-skłodowska-kraków")
    assert krakow["status"] == "asserted" and "status_ref" not in krakow
    assert maria.get("f:born-skłodowska-warszawa")["status_ref"] == "m:ret-1"
    retracts = maria.get("m:ret-1")
    assert [b["value"]["fact"] for b in retracts["bindings"]] == ["f:born-skłodowska-warszawa", "m:sup-1"]
    assert maria.supersession_walk("f:born-skłodowska-kraków")["steps"] == []


def test_a_resolving_dispute_needs_its_id(maria, rec, cur):
    maria.apply(supersede(rec, cur), actor="t")
    with pytest.raises(ValidationError) as e:
        maria.apply({"op": "transition", "targets": ["m:sup-1"], "to": "retracted", "id": "m:ret-1",
                     "reason": "withdrawn", "resolve_superseding": "dispute", "evidence": [cur]}, actor="t")
    assert e.value.codes == ("KHG-C010",)


def test_assert_from_quoted_disputed_and_goal(ms, entities, rec, cur):
    louis16 = {"kind": "entity", "id": "ex:LouisXVI", "types": ["Person"], "label": "Louis XVI"}
    ms.put(entities + [louis16, rec("f:born-louis14-paris"), rec("g:who-1774")], actor="t")
    receipt = ms.apply({"op": "transition", "targets": ["f:born-louis14-paris"], "to": "asserted",
                        "evidence": [cur]}, actor="t")
    assert receipt["records"] == [("f:born-louis14-paris", 2, "versioned")]
    fact = ms.get("f:born-louis14-paris")
    assert fact["status"] == "asserted" and fact["evidence"][-1] == dict(cur, supports=[])
    with pytest.raises(ValidationError) as e:  # an unbound slot stays unbound
        ms.apply({"op": "transition", "targets": ["g:who-1774"], "to": "asserted", "evidence": [cur]}, actor="t")
    assert e.value.codes == ("KHG-C005",)
    ms.put(rec("g:who-1774", set_binding={"b1": {"entity": "ex:LouisXVI"}}), actor="t")
    ms.apply({"op": "transition", "targets": ["g:who-1774"], "to": "asserted", "evidence": [cur]}, actor="t")
    goal = ms.get("g:who-1774")
    assert goal["status"] == "asserted" and "goal" not in goal and goal["version"] == 3
    with pytest.raises(VersionError) as e:  # already asserted
        ms.apply({"op": "transition", "targets": ["g:who-1774"], "to": "asserted", "evidence": [cur]}, actor="t")
    assert e.value.codes == ("KHG-D014",)
    with pytest.raises(VersionError) as e:
        ms.apply({"op": "transition", "targets": ["f:born-louis14-paris"], "to": "goal", "evidence": [cur]},
                 actor="t")
    assert e.value.codes == ("KHG-D014",)
    with pytest.raises(VersionError) as e:  # evidence ids are never reused
        ms.apply({"op": "add_evidence", "target": "f:born-louis14-paris", "evidence": [cur]}, actor="t")
    assert e.value.codes == ("KHG-D013",)


# ------------------------------------------------------------------------------------------------ one fact


def test_end_validity_adds_the_end_and_its_cause(ms, entities, rec, cur, T):
    ms.put(entities + [rec("f:king-13", set_binding={"b4": {"special": "novalue"}})], actor="t")
    receipt = ms.apply({"op": "end_validity", "target": "f:king-13", "end": T("+1643-05-14T00:00:00Z"),
                        "end_cause": {"entity": "ex:LouisXIV"}, "evidence": [cur]}, actor="t")
    assert receipt["records"] == [("f:king-13", 2, "versioned")] and receipt["warnings"] == []
    king = ms.get("f:king-13")
    by_bid = {b["bid"]: b for b in king["bindings"]}
    assert by_bid["b4"]["value"] == T("+1643-05-14T00:00:00Z", 11, "gregorian")
    assert by_bid["b5"] == {"bid": "b5", "role": "khg:end_cause", "value": {"entity": "ex:LouisXIV"}}
    assert king["status"] == "asserted" and king["evidence"][-1]["supports"] == ["b4", "b5"]
    with pytest.raises(VersionError) as e:  # a literal end is only refined
        ms.apply({"op": "end_validity", "target": "f:king-13", "end": T("+1650-01-01T00:00:00Z"),
                  "evidence": [dict(cur, id="e10")]}, actor="t")
    assert e.value.codes == ("KHG-D013",)


def test_end_validity_refuses_what_it_cannot_end(schema, ms, entities, rec, cur, T):
    ms.put(entities + [rec("f:reg-1"), rec("f:born-louis14-paris")], actor="t")
    end = {"op": "end_validity", "end": T("+1700-01-01T00:00:00Z"), "evidence": [cur]}
    with pytest.raises(ValidationError) as e:  # regulates is invariant: it has no end role
        ms.apply(dict(end, target="f:reg-1"), actor="t")
    assert e.value.codes == ("KHG-S002",)
    with pytest.raises(VersionError) as e:  # a quoted fact
        ms.apply(dict(end, target="f:born-louis14-paris"), actor="t")
    assert e.value.codes == ("KHG-D014",)
    with pytest.raises(NotFound):
        ms.apply(dict(end, target="f:nope"), actor="t")
    with pytest.raises(ValidationError) as e:
        ms.apply({"op": "end_validity", "target": "f:reg-1", "evidence": [cur]}, actor="t")
    assert e.value.codes == ("KHG-C010",)
    no_time = MemoryStore(schema, clock=ScenarioClock(), capabilities=ALL_FLAGS - {"valid_time"})
    with pytest.raises(CapabilityMissing) as e:
        no_time.apply(dict(end, target="f:king-13"), actor="t")
    assert e.value.flag == "valid_time"


def test_add_evidence_appends(ms, entities, rec, cur):
    ms.put(entities + [rec("f:reg-1")], actor="t")
    receipt = ms.apply({"op": "add_evidence", "target": "f:reg-1", "evidence": [cur]}, actor="t")
    assert receipt["records"] == [("f:reg-1", 2, "versioned")]
    assert [(e["id"], e["supports"]) for e in ms.get("f:reg-1")["evidence"]] == \
        [("e1", ["b1", "b2", "b3"]), ("e9", ["b1", "b2", "b3"])]
    with pytest.raises(ValidationError) as e:
        ms.apply({"op": "add_evidence", "target": "f:reg-1", "evidence": []}, actor="t")
    assert e.value.codes == ("KHG-C010",)
    with pytest.raises(ValidationError) as e:
        ms.apply({"op": "add_evidence", "target": "f:reg-1", "evidence": [{"id": "e10"}]}, actor="t")
    assert e.value.codes == ("KHG-C007",) and ms.get("f:reg-1")["version"] == 2


def test_unknown_and_malformed_events(ms, entities):
    ms.put(entities, actor="t")
    with pytest.raises(ValidationError) as e:
        ms.apply({"op": "merge"}, actor="t")
    assert e.value.codes == ("KHG-C002",)
    with pytest.raises(ValidationError) as e:
        ms.apply({"target": "x"}, actor="t")
    assert e.value.codes == ("KHG-C010",)
    with pytest.raises(ValidationError) as e:
        ms.apply(["supersede"], actor="t")
    assert e.value.codes == ("KHG-C010",)
    with pytest.raises(ValidationError) as e:
        ms.apply({"op": "transition", "targets": ["ex:Paris", "ex:Paris"], "to": "asserted", "evidence": []},
                 actor="t")
    assert e.value.codes == ("KHG-D001",)


def test_the_p7_resolution_loop(schema, entities, rec, cur):
    """The P7 sequence of DESIGN §1.3: a put raises KeyCollision, and the caller follows each conflict's action:
    close_older ends the stored fact at the newcomer's start, dispute joins both in one transition."""
    ms = MemoryStore(schema)
    ms.put(entities, actor="p7")
    ms.put([rec("f:king-13", drop_bindings=["b4"]), rec("f:born-skłodowska-warszawa")], actor="p7")
    king14 = rec("f:king-14")
    krakow = rec("f:born-skłodowska-kraków", **KRAKOW)
    actions = []
    for new in (king14, krakow):
        try:
            ms.put(new, actor="p7")
        except KeyCollision as e:
            for coll in e.info["collisions"]:
                for c in coll["conflicts"]:
                    old = ms.get_many([c["id"]])[c["id"]]
                    actions.append((coll["record"], c["action"], old["id"]))
                    if c["action"] == "close_older":
                        start = next(b["value"] for b in new["bindings"] if b["role"] == "start_time")
                        ms.apply({"op": "end_validity", "target": c["id"], "end": start, "evidence": [cur]},
                                 actor="p7")
                        ms.put(new, actor="p7")
                    elif c["action"] == "dispute":
                        ms.apply({"op": "transition", "targets": [c["id"]], "to": "disputed", "records": [new],
                                  "id": "m:dis-7", "reason": "key_conflict", "evidence": [cur]}, actor="p7")
    assert actions == [("f:king-14", "close_older", "f:king-13"),
                       ("f:born-skłodowska-kraków", "dispute", "f:born-skłodowska-warszawa")]
    key = [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}]
    current = ms.find_by_key("position_held", key, where=Where(as_of="+1700-01-01T00:00:00Z"))
    assert [r["id"] for r in current] == ["f:king-14"]
    assert ms.get("f:king-13")["status"] == "asserted" and len(ms.history("f:king-13")) == 2
    assert {ms.get(i)["status"] for i in ("f:born-skłodowska-kraków", "f:born-skłodowska-warszawa")} == {"disputed"}
    maria = [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}]
    assert ms.find_by_key("born_in", maria) == []

