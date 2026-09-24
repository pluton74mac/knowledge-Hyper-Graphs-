"""W8: ``MemoryStore`` construction, ``info``, ``put`` and the reads (DESIGN §6.1-§6.3)."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import CONTRACTS, data, record
from khg_contracts.errors import (CapabilityMissing, ConcurrencyError, KeyCollision, KHGError, ValidationError,
                                  VersionError)
from khg_contracts.store import (ALL_FLAGS, MemoryStore, ScenarioClock, Store, SystemClock, Where,
                                 memory_factory)

KING = [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}]


def ids(records):
    return [r["id"] for r in records]


# ------------------------------------------------------------------------------------------------ construction


def test_construction_and_info(schema):
    s = MemoryStore(schema)
    assert isinstance(s, Store) and isinstance(s.clock, SystemClock)
    info = s.info()
    assert info == {"interface_version": "khg-store/1.0.0", "record_format": "khg-record/1.0.0",
                    "capabilities": ALL_FLAGS, "store_id": "memory", "header": None, "contracts": dict(CONTRACTS)}
    assert isinstance(info["capabilities"], frozenset)
    limited = MemoryStore(schema, capabilities=["goals"], store_id="p1-sqlite")
    assert limited.info()["capabilities"] == frozenset({"goals"}) and limited.info()["store_id"] == "p1-sqlite"
    with pytest.raises(ValueError):
        MemoryStore(schema, capabilities=["goals", "teleport"])
    with pytest.raises(TypeError):
        MemoryStore(schema, capabilities="goals")
    with pytest.raises(ValueError):
        MemoryStore(schema, store_id="has space")


def test_the_schema_may_be_a_document(schema):
    s = MemoryStore(schema.doc)
    assert s.schema == schema


def test_memory_factory_uses_the_clock(schema):
    clock = ScenarioClock("2030-01-01T00:00:00Z")
    s = memory_factory(schema, clock)
    assert isinstance(s, MemoryStore) and s.clock is clock and s.capabilities == ALL_FLAGS


# ------------------------------------------------------------------------------------------------ put


def test_put_writes_versions_with_store_fields(ms, entities, rec):
    receipt = ms.put(entities, actor="t")
    assert receipt["at"] == "2026-10-01T00:00:00Z" and receipt["warnings"] == []
    assert receipt["records"][0] == ("ex:AirCanada", 1, "created") and len(receipt["records"]) == 22
    receipt = ms.put(rec("f:reg-1"), actor="curator")
    assert receipt == {"records": [("f:reg-1", 1, "created")], "at": "2026-10-01T00:00:01Z", "warnings": []}
    got = ms.get("f:reg-1")
    assert (got["version"], got["recorded_at"], got["recorded_by"]) == (1, "2026-10-01T00:00:01Z", "curator")
    assert got["rank"] == "normal" and got["visibility"] == "visible"  # canonical form


def test_an_identical_put_is_a_noop_and_does_not_tick(ms, entities, rec):
    ms.put(entities + [rec("f:reg-1")], actor="t")
    receipt = ms.put([rec("f:reg-1"), rec("ex:TP53")], actor="t")
    assert receipt == {"records": [("ex:TP53", 1, "noop"), ("f:reg-1", 1, "noop")], "at": "2026-10-01T00:00:01Z",
                       "warnings": []}
    assert ms.clock.now() == "2026-10-01T00:00:01Z"
    stored = ms.get("f:reg-1")
    stored["recorded_by"] = "someone else"  # store fields do not make content
    assert ms.put(stored, actor="t")["records"] == [("f:reg-1", 1, "noop")]


def test_put_is_all_or_nothing(ms, entities, rec):
    ms.put(entities, actor="t")
    bad = rec("f:coadmin-1", set={"relation": "inhibits"})
    with pytest.raises(ValidationError) as e:
        ms.put([rec("f:reg-1"), bad], actor="t")
    assert e.value.codes == ("KHG-S001",) and ms.get("f:reg-1") is None
    assert e.value.info["findings"][0]["path"] == "/records/1/relation"


@pytest.mark.parametrize("patch,code,cls", [
    ({"set": {"status": "candidate"}}, "KHG-D017", ValidationError),
    ({"set": {"status": "retracted", "status_ref": "m:ret-1"}}, "KHG-D014", VersionError),
    ({"drop_bindings": ["b2"]}, "KHG-S003", ValidationError),
    ({"set_binding": {"b1": {"entity": "ex:Nobody"}}}, "KHG-D002", ValidationError),
    ({"set_binding": {"b1": {"literal": {"datatype": "time", "time": "+1600-00-00T00:00:00Z", "precision": 9}}}},
     "KHG-S005", ValidationError),
    ({"set_evidence": {"e1": {"mode": "telepathic"}}}, "KHG-C002", ValidationError),
    ({"drop": ["evidence"]}, "KHG-S011", ValidationError),
])
def test_put_reports_the_codes_of_the_checks(ms, entities, rec, patch, code, cls):
    ms.put(entities, actor="t")
    with pytest.raises(cls) as e:
        ms.put(rec("f:king-14", **patch), actor="t")
    assert code in e.value.codes and ms.get("f:king-14") is None


def test_put_refuses_other_kinds_duplicates_and_lifecycle_records(ms, entities, rec):
    with pytest.raises(ValidationError) as e:
        ms.put({"kind": "relation-schema", "id": "x"}, actor="t")
    assert e.value.codes == ("KHG-C002",)
    with pytest.raises(ValidationError) as e:
        ms.put({"kind": "entity"}, actor="t")
    assert "KHG-C010" in e.value.codes
    with pytest.raises(ValidationError) as e:
        ms.put(["not a record"], actor="t")
    assert e.value.codes == ("KHG-C010",)
    with pytest.raises(TypeError):
        ms.put("f:reg-1", actor="t")
    with pytest.raises(ValidationError) as e:
        ms.put([entities[0], entities[0]], actor="t")
    assert e.value.codes == ("KHG-D001",)
    ms.put(entities, actor="t")
    with pytest.raises(VersionError) as e:
        ms.put(rec("m:sup-1"), actor="t")
    assert e.value.codes == ("KHG-D014",)
    for actor in ("", None, 3):
        with pytest.raises(ValidationError):
            ms.put(entities[0], actor=actor)


def test_a_new_version_follows_the_version_rule(ms, entities, rec, cur, T):
    ms.put(entities + [rec("f:king-13", drop_bindings=["b4"])], actor="t")
    with pytest.raises(VersionError) as e:  # the Bob-for-Alice probe: a core value is not refined
        ms.put(rec("f:king-13", set_binding={"b1": {"entity": "ex:LouisXIV"}}), actor="t")
    assert e.value.codes == ("KHG-D013",)
    receipt = ms.put(rec("f:king-13", set_evidence={"e1": {"supports": ["b1", "b2", "b3"]}},
                         add_evidence=[dict(cur, supports=["b4"])]), actor="t")
    assert receipt["records"] == [("f:king-13", 2, "versioned")]
    with pytest.raises(VersionError):  # an entity's types only grow
        ms.put(dict(entities[5], types=["Agent"]), actor="t")
    with pytest.raises(VersionError):  # a kind never changes
        ms.put({"kind": "entity", "id": "f:king-13", "types": ["Person"]}, actor="t")


def test_carried_evidence_without_supports_keeps_what_it_supported(ms, entities):
    """§2.8.1: a new version that carries evidence without ``supports`` keeps what the evidence supported where it
    was first written; normalising the version alone would widen e1 to the new bid b4, which the version rule refuses
    as a rewrite (D013)."""
    history = data.load_json("fixture/fixture.history.c1.json")
    v1, v2 = [{k: v for k, v in r.items() if k not in ("version", "recorded_at", "recorded_by")}
              for r in history["records"] if r["id"] == "f:king-13"]
    for v in (v1, v2):
        del v["evidence"][0]["supports"]  # e1
    ms.put(entities + [v1], actor="t")
    assert ms.put(v2, actor="t")["records"] == [("f:king-13", 2, "versioned")]
    assert [(e["id"], e["supports"]) for e in ms.get("f:king-13")["evidence"]] == \
        [("e1", ["b1", "b2", "b3"]), ("e2", ["b4"])]
    assert ms.put(v2, actor="t")["records"] == [("f:king-13", 2, "noop")]
    assert sorted(record.supported_values(ms.history("f:king-13"), "e1")) == ["b1", "b2", "b3"]


def test_put_cannot_move_a_status_ref(ms, entities, rec, cur):
    """§2.7: ``status_ref`` is on the belief axis, which only events move (D014). A put that re-pointed a disputed
    fact's ``status_ref`` left the store breaking the pointer rule (D010), and later undos of the dispute failed."""
    ms.put(entities + [rec("f:born-skłodowska-warszawa")], actor="t")
    ms.apply({"op": "transition", "targets": ["f:born-skłodowska-warszawa"], "to": "disputed",
              "records": [rec("f:born-skłodowska-kraków", set={"status": "asserted"}, drop=["status_ref"])],
              "id": "m:dis-1", "reason": "key_conflict", "evidence": [cur]}, actor="t")
    held = {k: v for k, v in ms.get("f:born-skłodowska-warszawa").items()
            if k not in ("version", "recorded_at", "recorded_by")}
    for ref in ("m:nothing", "f:born-skłodowska-kraków", None):
        moved = copy.deepcopy(held)
        if ref is None:
            del moved["status_ref"]
        else:
            moved["status_ref"] = ref
        with pytest.raises(VersionError) as e:
            ms.put(moved, actor="t")
        assert e.value.codes == ("KHG-D014",) and e.value.info["problems"][0]["pointer"] == "/status_ref"
    assert ms.get("f:born-skłodowska-warszawa")["version"] == 2
    assert ms.put(held, actor="t")["records"] == [("f:born-skłodowska-warszawa", 2, "noop")]
    edited = dict(held, extensions={"ex:note": "checked"})  # the editable fields still change by put
    assert ms.put(edited, actor="t")["records"] == [("f:born-skłodowska-warszawa", 3, "versioned")]
    ms.put(rec("f:reg-1"), actor="t")
    with pytest.raises(VersionError) as e:  # an asserted fact cannot gain one either
        ms.put(dict(rec("f:reg-1"), status_ref="m:dis-1"), actor="t")
    assert e.value.codes == ("KHG-D014",)


def test_expect_gives_optimistic_concurrency(ms, entities, rec, cur):
    ms.put(entities + [rec("f:reg-1")], actor="t")
    with pytest.raises(ConcurrencyError) as e:
        ms.put(rec("f:reg-1", add_evidence=[cur]), actor="t", expect={"f:reg-1": 2, "f:new": 0})
    assert e.value.codes == ("KHG-D019",)
    assert e.value.info == {"expected": {"f:reg-1": 2, "f:new": 0}, "found": {"f:reg-1": 1, "f:new": 0},
                            "stale": ["f:reg-1"]}
    receipt = ms.put(rec("f:reg-1", add_evidence=[cur]), actor="t", expect={"f:reg-1": 1, "f:new": 0})
    assert receipt["records"] == [("f:reg-1", 2, "versioned")]


def test_at_pins_the_transaction_time_forward(ms, entities, rec, cur):
    ms.put(entities, actor="t", at="2026-10-01T00:00:05Z")
    assert ms.clock.now() == "2026-10-01T00:00:06Z"
    with pytest.raises(VersionError) as e:
        ms.put(rec("f:reg-1"), actor="t", at="2026-10-01T00:00:05Z")
    assert e.value.codes == ("KHG-D018",) and e.value.info["latest"] == "2026-10-01T00:00:05Z"
    with pytest.raises(ValidationError) as e:
        ms.put(rec("f:reg-1"), actor="t", at="yesterday")
    assert e.value.codes == ("KHG-C011",)
    assert ms.put(rec("f:reg-1"), actor="t", at="2026-10-01T00:00:05.5Z")["at"] == "2026-10-01T00:00:05.5Z"
    assert ms.put(rec("f:reg-1", add_evidence=[cur]), actor="t")["at"] == "2026-10-01T00:00:07Z"  # 6 s, ticked


def test_a_clock_set_back_never_breaks_the_order(ms, entities, rec):
    ms.put(entities, actor="t", at="2026-10-01T00:00:05Z")
    ms.clock.set("2026-10-01T00:00:00Z")
    receipt = ms.put(rec("f:reg-1"), actor="t")
    assert receipt["at"] == "2026-10-01T00:00:05.000001Z"


def test_put_needs_the_flags_of_its_records(schema, entities, rec):
    for rid, flag in (("f:king-14", "literal_values"), ("f:cat-7", "special_values"), ("f:claim-1", "nesting"),
                      ("g:who-1774", "goals"), ("f:route-1", "ordered_roles")):
        s = MemoryStore(schema, clock=ScenarioClock(), capabilities=ALL_FLAGS - {flag})
        s.put(entities + [rec("f:born-louis14-paris")], actor="t")
        with pytest.raises(CapabilityMissing) as e:
            s.put(rec(rid), actor="t")
        assert e.value.flag == flag and s.get(rid) is None
    single = MemoryStore(schema, clock=ScenarioClock(), capabilities=[])
    with pytest.raises(CapabilityMissing) as e:
        single.put(entities[:2], actor="t")
    assert e.value.flag == "atomic_writes"
    assert single.put(entities[0], actor="t")["records"] == [("ex:AirCanada", 1, "created")]
    assert single.put([entities[1]], actor="t")["records"] == [("ex:Chronicler_Ødegård", 1, "created")]


def test_the_disputed_key_rule_and_the_key_invariant(ms, entities, rec, cur):
    ms.put(entities + [rec("f:born-skłodowska-warszawa")], actor="t")
    krakow = rec("f:born-skłodowska-kraków", set={"status": "asserted"}, drop=["status_ref"])
    with pytest.raises(KeyCollision) as e:
        ms.put(krakow, actor="t")
    assert e.value.codes == ("KHG-D016",)
    [collision] = e.value.info["collisions"]
    assert (collision["record"], collision["policy"], collision["conflicts"][0]["id"]) == \
        ("f:born-skłodowska-kraków", "dispute", "f:born-skłodowska-warszawa")
    assert ms.get("f:born-skłodowska-kraków") is None


def test_keys_need_the_key_constraint_and_temporal_keys_valid_time(schema, entities, rec, T):
    king14b = rec("f:king-14", set={"id": "f:king-14b"}, set_binding={"b3": T("+1640-01-01T00:00:00Z")})
    krakow = rec("f:born-skłodowska-kraków", set={"status": "asserted"}, drop=["status_ref"])
    no_keys = MemoryStore(schema, clock=ScenarioClock(), capabilities=ALL_FLAGS - {"key_constraint"})
    no_time = MemoryStore(schema, clock=ScenarioClock(), capabilities=ALL_FLAGS - {"valid_time"})
    for s in (no_keys, no_time):
        s.put(entities + [rec("f:king-13"), rec("f:born-skłodowska-warszawa")], actor="t")
        assert s.put(king14b, actor="t")["records"] == [("f:king-14b", 1, "created")]
    assert no_keys.put(krakow, actor="t")["records"] == [("f:born-skłodowska-kraków", 1, "created")]
    with pytest.raises(KeyCollision):  # a non-temporal key is still checked without valid_time
        no_time.put(krakow, actor="t")
    handover = [rec("f:king-14", set={"id": "f:king-14x"})]
    assert no_time.put(handover, actor="t")["warnings"] == []  # L008 needs valid_time


def test_the_invariant_is_checked_without_an_incoming_fact(ms, entities, rec, cur):
    """A write that leaves two normal facts holding together on one key raises, though no asserted fact comes in
    (the gap W5 left to the store): here a dispute takes away the preferred fact."""
    pop = rec("f:pop-łódź-2019")
    ms.put(entities + [dict(pop, rank="preferred"), dict(pop, id="f:pop-b", rank="normal"),
                       dict(pop, id="f:pop-c", rank="normal")], actor="t")
    event = {"op": "transition", "targets": ["f:pop-łódź-2019"], "to": "retracted", "id": "m:ret-1",
             "reason": "withdrawn", "evidence": [cur]}
    with pytest.raises(KeyCollision) as e:
        ms.apply(event, actor="t")
    assert e.value.info["collisions"] == []
    [violation] = e.value.info["violations"]
    assert (violation["relation"], violation["ids"], violation["temporal"]) == \
        ("population", ["f:pop-b", "f:pop-c"], False)
    assert ms.get("f:pop-łódź-2019")["status"] == "asserted" and ms.get("m:ret-1") is None


def test_a_write_is_not_blamed_for_what_is_left_of_a_loaded_violation(schema, fixture_doc, entities, rec, cur):
    """A trusted load may hold three normal facts on one key (D016). Retracting or deprecating one leaves two of
    them, a part of the violation that was there, not a new one. A new version of one of them that stays asserted
    still takes part in it, and is refused as before."""
    pop = rec("f:pop-łódź-2019")
    doc = {"header": fixture_doc["header"], "records": entities + [dict(pop, id=i)
                                                                    for i in ("f:pop-a", "f:pop-b", "f:pop-c")]}
    for write in (lambda s: s.apply({"op": "transition", "targets": ["f:pop-a"], "to": "retracted", "id": "m:r1",
                                     "reason": "withdrawn", "evidence": [cur]}, actor="t"),
                  lambda s: s.put(dict(pop, id="f:pop-a", rank="deprecated", rank_reason=["wd:Q41755623"]),
                                  actor="t")):
        s = MemoryStore(schema, clock=ScenarioClock())
        s.load(copy.deepcopy(doc))
        assert write(s)["records"][0][:2] == ("f:pop-a", 2)
    s = MemoryStore(schema, clock=ScenarioClock())
    s.load(copy.deepcopy(doc))
    with pytest.raises(KeyCollision):
        s.apply({"op": "add_evidence", "target": "f:pop-a", "evidence": [cur]}, actor="t")


def _cites(rid, target):
    return {"kind": "hyperedge", "id": rid, "relation": "cites", "status": "asserted",
            "bindings": [{"bid": "b1", "role": "cited", "value": {"fact": target}}],
            "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:t"}}]}


def test_nesting_cycles_are_refused(schema, entities, rec):
    """The fixture schema cannot express a cycle (claims only take born_in facts); ``cites`` takes any fact."""
    doc = copy.deepcopy(schema.doc)
    doc["roles"].append({"id": "cited", "label": "cited"})
    doc["relations"].append({"id": "cites", "roles": [{"role": "cited", "slot": "core", "fillers": [{"fact": []}],
                                                       "min": 1, "max": 1}]})
    s = MemoryStore(doc, clock=ScenarioClock())
    s.put(entities + [rec("f:born-louis14-paris")], actor="t")
    with pytest.raises(ValidationError) as e:
        s.put([_cites("f:a", "f:b"), _cites("f:b", "f:a")], actor="t")
    assert e.value.codes == ("KHG-D008",)
    with pytest.raises(ValidationError) as e:
        s.put(_cites("f:self", "f:self"), actor="t")
    assert e.value.codes == ("KHG-D008",)
    with pytest.raises(ValidationError) as e:  # a reference to a fact the store does not hold
        s.put(_cites("f:a", "f:missing"), actor="t")
    assert e.value.codes == ("KHG-D002",)
    chain = [_cites("f:c1", "f:born-louis14-paris"), _cites("f:c2", "f:c1")]
    assert s.put(chain, actor="t")["records"] == [("f:c1", 1, "created"), ("f:c2", 1, "created")]


# ------------------------------------------------------------------------------------------------ the check order
# §6.2: capability, NotFound, D014, record validation, references and pointers, D008, D016 with the disputed-key
# rule, D011, D012, D018. Each write below breaks two rules; the earlier one is reported.

KRAKOW = {"set": {"status": "asserted"}, "drop": ["status_ref"]}


def test_the_key_invariant_comes_before_transaction_time(ms, entities, rec):
    ms.put(entities + [rec("f:born-skłodowska-warszawa")], actor="t", at="2026-10-01T00:00:05Z")
    with pytest.raises(KeyCollision) as e:  # D016, though at is not after the latest either (D018)
        ms.put(rec("f:born-skłodowska-kraków", **KRAKOW), actor="t", at="2026-10-01T00:00:01Z")
    assert e.value.codes == ("KHG-D016",)


def test_nesting_comes_before_the_key_invariant(schema, entities, rec):
    doc = copy.deepcopy(schema.doc)
    doc["roles"].append({"id": "cited", "label": "cited"})
    doc["relations"].append({"id": "cites", "roles": [{"role": "cited", "slot": "core", "fillers": [{"fact": []}],
                                                       "min": 1, "max": 1}]})
    s = MemoryStore(doc, clock=ScenarioClock())
    s.put(entities + [rec("f:born-skłodowska-warszawa")], actor="t")
    with pytest.raises(ValidationError) as e:  # D008, though Kraków collides with Warszawa too (D016)
        s.put([_cites("f:a", "f:b"), _cites("f:b", "f:a"), rec("f:born-skłodowska-kraków", **KRAKOW)], actor="t")
    assert e.value.codes == ("KHG-D008",)


def test_the_key_invariant_comes_before_supersession_constraints(ms, entities, rec):
    from khg_contracts.store import conformance

    suite = conformance.suite()
    scenario = suite.scenarios["S-LIFE-014"]
    conformance.run_given(ms, scenario["given"], suite, ms.capabilities)
    ms.put(rec("f:born-skłodowska-warszawa"), actor="t")
    moved = suite.resolve(scenario["when"][0]["args"]["records"][0])  # a key literal refined away: D011
    with pytest.raises(VersionError) as e:
        ms.put([moved], actor="t")
    assert e.value.codes == ("KHG-D011",)
    with pytest.raises(KeyCollision):  # with a collision in the same batch, D016 comes first
        ms.put([moved, rec("f:born-skłodowska-kraków", **KRAKOW)], actor="t")


def test_a_missing_capability_comes_before_not_found(schema, cur, T):
    s = MemoryStore(schema, clock=ScenarioClock(), capabilities=ALL_FLAGS - {"atomic_writes", "valid_time"})
    for event, flag in (({"op": "supersede", "id": "m:s", "superseded": ["f:nope"], "reason": "other",
                          "evidence": [cur]}, "atomic_writes"),
                        ({"op": "transition", "targets": ["f:nope"], "to": "disputed", "id": "m:d",
                          "evidence": [cur]}, "atomic_writes"),
                        ({"op": "transition", "targets": ["m:nope"], "to": "retracted", "id": "m:r",
                          "evidence": [cur]}, "atomic_writes"),
                        ({"op": "end_validity", "target": "f:nope", "end": T("+1700-01-01T00:00:00Z"),
                          "evidence": [cur]}, "valid_time")):
        with pytest.raises(CapabilityMissing) as e:
            s.apply(event, actor="t")
        assert e.value.flag == flag


def test_a_status_rule_comes_before_record_validation(ms, entities, rec):
    ms.put(entities, actor="t")
    for status in ("retracted", "candidate"):
        bad = rec("f:born-skłodowska-warszawa", set={"status": status, "status_ref": "m:x", "rank": "sky-high"})
        with pytest.raises(KHGError) as e:  # D014 (D017), though the rank is not in the vocabulary (C002)
            ms.put(bad, actor="t")
        assert e.value.codes == (("KHG-D014",) if status == "retracted" else ("KHG-D017",))


def test_a_redirected_entity_is_refused_only_where_it_is_written(ms, entities, rec, cur):
    ms.put(entities + [rec("f:born-louis14-paris")], actor="t")
    ms.put(dict(entities[9], redirect_to="ex:Warszawa"), actor="t")  # ex:Paris
    with pytest.raises(ValidationError) as e:
        ms.put(rec("f:born-louis14-paris", set={"id": "f:x"}), actor="t")
    assert e.value.codes == ("KHG-D020",)
    receipt = ms.put(rec("f:born-louis14-paris", add_evidence=[cur]), actor="t")  # the value was there before
    assert receipt["records"] == [("f:born-louis14-paris", 2, "versioned")]


# ------------------------------------------------------------------------------------------------ reads


def test_get_history_and_versions(ms, entities, rec, cur):
    ms.put(entities, actor="t", at="2026-10-01T00:00:01Z")
    ms.put(rec("f:reg-1"), actor="t", at="2026-10-01T00:00:02Z")
    ms.put(rec("f:reg-1", add_evidence=[cur]), actor="t", at="2026-10-01T00:00:03Z")
    assert ms.get("f:reg-1")["version"] == 2 and ms.get("f:nope") is None
    assert ms.get("f:reg-1", as_at="2026-10-01T00:00:02Z")["version"] == 1
    assert ms.get("f:reg-1", as_at="2026-10-01T00:00:01Z") is None
    assert ms.get("f:reg-1", version=1)["evidence"][0]["id"] == "e1"
    assert ms.get("f:reg-1", version=2, as_at="2026-10-01T00:00:02Z") is None
    assert ms.get("f:reg-1", version=3) is None
    assert [v["version"] for v in ms.history("f:reg-1")] == [1, 2] and ms.history("f:nope") == []


def test_reads_hand_out_copies(loaded):
    got = loaded.get("f:reg-1")
    got["bindings"].clear()
    loaded.incident("ex:TP53")[0]["status"] = "retracted"
    list(loaded.iter_records())[0]["id"] = "changed"
    assert len(loaded.get("f:reg-1")["bindings"]) == 3 and loaded.get("f:reg-1")["status"] == "asserted"
    assert next(loaded.iter_records())["id"] == "ex:AirCanada"


def test_incident_order_filters_and_pagination(loaded):
    assert ids(loaded.incident("ex:KingOfFrance")) == ["f:king-13", "f:king-14"]
    assert ids(loaded.incident("ex:KingOfFrance", role="position", relation="position_held")) == \
        ["f:king-13", "f:king-14"]
    assert ids(loaded.incident("ex:KingOfFrance", role="holder")) == []
    both = Where(status=frozenset({"asserted", "goal"}))
    assert ids(loaded.incident("ex:KingOfFrance", where=both, limit=2)) == ["f:king-13", "f:king-14"]
    assert ids(loaded.incident("ex:KingOfFrance", where=both, after="f:king-14")) == ["g:who-1774"]
    assert ids(loaded.incident("ex:KingOfFrance", where=both, limit=0)) == []
    assert ids(loaded.incident("ex:Mazarin")) == [] and ids(loaded.incident("wd:Q11573")) == []
    for bad in ({"limit": -1}, {"limit": True}, {"limit": "2"}):
        with pytest.raises(ValueError):
            loaded.incident("ex:YYZ", **bad)
    with pytest.raises(TypeError):
        loaded.incident("ex:YYZ", after=3)
    with pytest.raises(ValidationError):
        loaded.incident("ex:YYZ", relation="flies_to")
    assert loaded.degree("ex:YYZ") == 2 and loaded.degree("ex:YYZ", role="stop") == 1


def test_where_takes_a_mapping_and_filters_every_axis(loaded):
    everything = {"status": ["asserted", "superseded", "quoted", "goal"], "rank": ["preferred", "normal",
                                                                                   "deprecated"]}
    assert ids(loaded.incident("ex:Maria_Skłodowska", where=everything)) == \
        ["f:born-skłodowska-kraków", "f:born-skłodowska-warszawa", "f:married-curie"]
    assert ids(loaded.incident("ex:Łódź", where=everything)) == ["f:pop-łódź-2019", "f:pop-łódź-2019-dep"]
    assert ids(loaded.incident("ex:Łódź", where={"visibility": ["suppressed"]})) == []
    assert ids(loaded.incident("f:born-skłodowska-kraków", where={"kinds": ["lifecycle"]})) == ["m:sup-1"]
    assert ids(loaded.incident("f:born-skłodowska-kraków", where={"kinds": ["fact", "lifecycle"],
                                                                   "status": ["asserted"]})) == ["m:sup-1"]


def test_find_matches_multisets_positions_and_unbound_slots(loaded):
    agent = {"role": "agent", "value": {"entity": "ex:insulin"}}
    assert ids(loaded.find("co_administration_causes", [agent])) == ["f:coadmin-1"]
    assert ids(loaded.find("co_administration_causes", [agent, agent])) == []
    assert ids(loaded.find("co_administration_causes", [agent, {"role": "agent", "value": {"any": True}}])) == \
        ["f:coadmin-1"]
    assert ids(loaded.find("co_administration_causes", [agent], match="exact")) == []
    assert ids(loaded.find("flight_route", [{"role": "stop", "value": {"entity": "ex:YYZ"}, "position": 3}])) == \
        ["f:route-1"]
    goals = Where(status=frozenset({"goal"}))
    assert ids(loaded.find("position_held", [{"role": "holder", "value": {"any_unbound": True}}], where=goals)) \
        == ["g:who-1774"]
    assert ids(loaded.find("position_held", [{"role": "holder", "value": {"any": True}}], where=goals)) == \
        ["g:who-1774"]
    assert ids(loaded.find("position_held", [], limit=1, after="f:king-13")) == ["f:king-14"]


def test_find_pairs_many_patterns_without_a_frame_per_binding(schema, fixture_doc):
    """``find`` pairs patterns with bindings through the refinement matcher, which keeps its own stack: here under a
    recursion limit 60 frames above the caller, which a search recursing once per binding exceeded."""
    import sys

    doc = copy.deepcopy(fixture_doc)
    coadmin = next(r for r in doc["records"] if r["id"] == "f:coadmin-1")
    n = 150
    coadmin["bindings"] = [b for b in coadmin["bindings"] if b["role"] != "agent"] + [
        {"bid": f"b{10 + k}", "role": "agent", "value": {"entity": "ex:insulin"}} for k in range(n)]
    s = MemoryStore(schema, clock=ScenarioClock())
    s.load(doc)  # trusted: 150 agents of one entity
    any_agent = {"role": "agent", "value": {"any": True}}
    depth, f = 0, sys._getframe()
    while f is not None:
        depth, f = depth + 1, f.f_back
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(depth + 60)
    try:
        found = ids(s.find("co_administration_causes", [any_agent] * n))
        too_many = s.find("co_administration_causes", [any_agent] * (n + 1))
    finally:
        sys.setrecursionlimit(old)
    assert found == ["f:coadmin-1"] and too_many == []


def test_find_refuses_malformed_patterns(loaded):
    for bad in ([{"role": "agent"}], [{"value": {"entity": "x"}}], [{"role": "agent", "value": {"entity": "x"},
                                                                     "extra": 1}],
                [{"role": "stop", "value": {"entity": "x"}, "position": 0}]):
        with pytest.raises(ValueError):
            loaded.find("co_administration_causes", bad)
    with pytest.raises(TypeError):
        loaded.find("co_administration_causes", {"role": "agent", "value": {"any": True}})
    with pytest.raises(ValidationError) as e:
        loaded.find("co_administration_causes", [{"role": "agent", "value": {"colour": "red"}}])
    assert e.value.codes == ("KHG-C002",)
    with pytest.raises(ValueError):
        loaded.find("co_administration_causes", [], match="most")
    with pytest.raises(ValidationError):
        loaded.find("no_such_relation", [])


def test_reads_need_their_flags(schema, fixture_doc):
    core_flags = ["literal_values", "nesting", "atomic_writes"]
    s = MemoryStore(schema, clock=ScenarioClock(), capabilities=core_flags)
    s.load(fixture_doc, on_missing="skip")
    for call, flag in (
            (lambda: s.incident("ex:KingOfFrance", where=Where(as_of="+1700-01-01T00:00:00Z")), "valid_time"),
            (lambda: s.incident("ex:KingOfFrance", where=Where(valid_mode="possible")), "valid_time"),
            (lambda: s.incident("ex:KingOfFrance", where=Where(as_at="2026-10-01T00:00:00Z")), "transaction_time"),
            (lambda: s.incident("ex:KingOfFrance", where=Where(status=frozenset({"goal"}))), "goals"),
            (lambda: s.find("position_held", [{"role": "holder", "value": {"any_unbound": True}}]), "goals"),
            (lambda: s.find("flight_route", [{"role": "stop", "value": {"entity": "ex:YYZ"}, "position": 1}]),
             "ordered_roles"),
            (lambda: s.find("catalysed_by", [{"role": "catalyst", "value": {"special": "novalue"}}]),
             "special_values"),
            (lambda: s.get("f:reg-1", version=1), "transaction_time"),
            (lambda: s.iter_records(content="history"), "history_export"),
            (lambda: s.iter_records(as_at="2026-10-01T00:00:00Z"), "transaction_time")):
        with pytest.raises(CapabilityMissing) as e:
            call()
        assert e.value.flag == flag
    assert ids(s.incident("f:born-louis14-paris")) == ["f:claim-1"]  # incident(fact id) is nesting
    no_nesting = MemoryStore(schema, clock=ScenarioClock(), capabilities=["literal_values"])
    no_nesting.load(fixture_doc, on_missing="skip")
    with pytest.raises(CapabilityMissing) as e:
        no_nesting.incident("f:born-louis14-paris")
    assert e.value.flag == "nesting"


def test_iter_records_snapshot_history_and_as_at(ms, entities, rec, cur):
    ms.put(entities[:1], actor="t")
    ms.put(entities[1:] + [rec("f:reg-1")], actor="t")
    ms.put(rec("f:reg-1", add_evidence=[cur]), actor="t")
    snapshot = list(ms.iter_records())
    assert ids(snapshot) == sorted(ids(snapshot)) and len(snapshot) == 23
    history = [(r["id"], r["version"]) for r in ms.iter_records(content="history")]
    assert history[-2:] == [("f:reg-1", 1), ("f:reg-1", 2)] and len(history) == 24
    assert len(list(ms.iter_records(as_at="2026-10-01T00:00:00Z"))) == 1
    assert [r["version"] for r in ms.iter_records(content="history", as_at="2026-10-01T00:00:01Z")
            if r["id"] == "f:reg-1"] == [1]
    with pytest.raises(ValueError):
        ms.iter_records(content="all")
    copied = copy.deepcopy(snapshot)
    assert copied == list(ms.iter_records())


def test_find_by_key_binds_exactly_the_key_roles(loaded, T):
    assert ids(loaded.find_by_key("position_held", KING)) == ["f:king-13", "f:king-14"]
    assert ids(loaded.find_by_key("position_held", KING, where=Where(as_of="+1620-01-01T00:00:00Z"))) == \
        ["f:king-13"]
    lodz = [{"role": "place", "value": {"entity": "ex:Łódź"}},
            {"role": "point_in_time", "value": T("+2019-00-00T00:00:00Z", 9)}]
    assert ids(loaded.find_by_key("population", lodz)) == ["f:pop-łódź-2019"]
    julian = [lodz[0], {"role": "point_in_time", "value": T("+2019-06-30T00:00:00Z")}]
    assert loaded.find_by_key("population", julian) == []  # precision takes part in key identity
    somevalue = [{"role": "person", "value": {"special": "somevalue"}}]
    assert loaded.find_by_key("born_in", somevalue) == []  # a special value names no key group
    for bad in ([], lodz[:1], lodz + [{"role": "quantity", "value": {"entity": "x"}}],
                [{"role": "position", "value": {"any": True}}]):
        with pytest.raises(ValueError):
            loaded.find_by_key("population" if bad is not KING else "position_held", bad)
    with pytest.raises(ValueError):
        loaded.find_by_key("regulates", [{"role": "regulator", "value": {"entity": "ex:TP53"}}])


def test_get_many_is_sorted_and_skips_missing_ids(loaded):
    got = loaded.get_many(["f:reg-1", "ex:TP53", "f:nope", "ex:HeLa", "f:reg-1"])
    assert list(got) == ["ex:HeLa", "ex:TP53", "f:reg-1"] and got["f:reg-1"]["relation"] == "regulates"
    with pytest.raises(TypeError):
        loaded.get_many("f:reg-1")
