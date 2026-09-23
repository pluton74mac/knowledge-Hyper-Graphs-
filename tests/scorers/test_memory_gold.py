"""W11a: the memory gold of DESIGN §9.5 (normative), through ``memory.derive_memory_gold``.

M9 replays the three memory questions of ``c4-items.jsonl`` and checks the hand-checked table of §9.5; the other
tests take the table row by row on traces built from the gate fixture's records: ``expired``, ``revised`` (a
supersession, a retraction, a deprecation with an incorrect reason), V_fut, ``disputed`` and ``answerable``, the
preferred-only rule, V_cur subtracted from the other sets, the expired-over-revised rule, ``as_of`` null, the
"no current value" gold of a year-precision handover, the replay itself, and the errors.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import data, jsonio
from khg_contracts.errors import KHGError, ValidationError
from khg_contracts.scorers import memory

LINES = data.load_jsonl("fixture/c4-items.jsonl")
TRACES = {x["trace_id"]: x for x in LINES if x["kind"] == "c4-memory-trace"}
QUESTIONS = {x["qid"]: x for x in LINES if x["kind"] == "c4-memory-question"}
FIXTURE = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"] if "id" in r}
EVIDENCE = [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}}]
KING = [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}]
MARIA = [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}]
LODZ = [{"role": "place", "value": {"entity": "ex:Łódź"}},
        {"role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z",
                                                        "precision": 9, "calendar": "gregorian"}}}]
XIII, XIV = {"entity": "ex:LouisXIII"}, {"entity": "ex:LouisXIV"}
KRAKOW, WARSZAWA = {"entity": "ex:Kraków"}, {"entity": "ex:Warszawa"}


def qty(amount: str) -> dict[str, Any]:
    return {"literal": {"datatype": "quantity", "amount": amount, "unit": "1"}}


def year(y: int) -> dict[str, Any]:
    return {"literal": {"datatype": "time", "time": f"+{y}-00-00T00:00:00Z", "precision": 9, "calendar": "gregorian"}}


def rec(rid: str, **changes: Any) -> dict[str, Any]:
    """A fixture record as a trace writes it: without store fields and ``status_ref``, asserted."""
    r = copy.deepcopy(FIXTURE[rid])
    for f in ("version", "recorded_at", "recorded_by", "status_ref"):
        r.pop(f, None)
    r["status"] = "asserted"
    r.update(changes)
    return r


def held(fid: str, holder: dict[str, Any], start: dict[str, Any], end: dict[str, Any] | None) -> dict[str, Any]:
    """A ``position_held`` fact on the King of France."""
    r = rec("f:king-13", id=fid, evidence=copy.deepcopy(EVIDENCE))
    r["bindings"] = [{"bid": "b1", "role": "holder", "value": holder}, {"bid": "b2", "role": "position",
                                                                        "value": {"entity": "ex:KingOfFrance"}},
                     {"bid": "b3", "role": "start_time", "value": start}]
    if end is not None:
        r["bindings"].append({"bid": "b4", "role": "end_time", "value": end})
    return r


def entities(*ids: str) -> list[dict[str, Any]]:
    return [copy.deepcopy(FIXTURE[i]) for i in ids]


def trace(tid: str, ents: list[dict[str, Any]], *events: tuple[str, Any]) -> dict[str, Any]:
    """A ``c4-memory-trace``: event i is step i at 2026-10-01T00:00:0iZ."""
    return {"kind": "c4-memory-trace", "id": "c4:" + tid.replace(":", "-"), "qset": "w11a", "split": "test",
            "trace_id": tid, "entities": ents,
            "events": [{"step": i, "tx_time": f"2026-10-01T00:00:{i:02d}Z", kind: body}
                       for i, (kind, body) in enumerate(events, 1)]}


def ask(tr: dict[str, Any], step: int, relation: str, key: list[dict[str, Any]], role: str, as_of: str | None, *,
        mode: str = "definite", rank: tuple[str, ...] = ("preferred", "normal"),
        status: tuple[str, ...] = ("asserted",)) -> dict[str, Any]:
    """The question fields ``derive_memory_gold`` reads."""
    return {"kind": "c4-memory-question", "trace_id": tr["trace_id"], "ask_after_step": step, "relation": relation,
            "key": key, "target_role": role,
            "where": {"as_of": as_of, "valid_mode": mode, "rank": list(rank), "status": list(status)}}


def gold(tr: dict[str, Any], q: dict[str, Any], schema: Any, **kw: Any) -> dict[str, Any]:
    return memory.derive_memory_gold(tr, q, schema=schema, **kw)


def sets(g: dict[str, Any]) -> tuple[list[Any], list[Any], list[Any], list[Any], bool]:
    return (g["answer"]["values"], [(s["kind"], s["value"]) for s in g["stale_values"]], g["future_values"],
            g["disputed_values"], g["answerable"])


KINGS_1700 = "+1700-01-01T00:00:00Z"


# ------------------------------------------------------------------------------------------------ M9


def test_m9_the_three_replays_equal_the_stored_items(fixture_schema):
    """The three memory questions of ``c4-items.jsonl`` store exactly their replayed gold."""
    assert sorted(QUESTIONS) == ["mq:king-1620", "mq:king-1700", "mq:maria-birthplace"]
    for q in QUESTIONS.values():
        g = gold(TRACES[q["trace_id"]], q, fixture_schema)
        for field in memory.GOLD_FIELDS:
            assert jsonio.canonical(g[field]) == jsonio.canonical(q[field]), (q["qid"], field)
        assert g["as_at"] == "2026-10-01T00:00:02Z"  # τ: the tx_time of ask_after_step 2


def test_m9_the_hand_checked_table(fixture_schema):
    """§9.5: t:kings as of 1700 and as of 1620, and t:maria with as_of null."""
    kings = TRACES["t:kings"]
    assert sets(gold(kings, QUESTIONS["mq:king-1700"], fixture_schema)) == ([XIV], [("expired", XIII)], [], [], True)
    assert sets(gold(kings, QUESTIONS["mq:king-1620"], fixture_schema)) == ([XIII], [], [XIV], [], True)
    assert sets(gold(TRACES["t:maria"], QUESTIONS["mq:maria-birthplace"], fixture_schema)) == \
        ([WARSZAWA], [("revised", KRAKOW)], [], [], True)


def test_the_first_item_as_section_9_5_prints_it():
    line = next(x for x in data.read_text("fixture/c4-items.jsonl").splitlines() if '"mq:king-1700"' in x)
    assert line == ('{"answer":{"values":[{"entity":"ex:LouisXIV"}]},"answerable":true,"ask_after_step":2,'
                    '"disputed_values":[],"future_values":[],"id":"c4:mq-king-1700","key":[{"role":"position",'
                    '"value":{"entity":"ex:KingOfFrance"}}],"kind":"c4-memory-question","qid":"mq:king-1700",'
                    '"qset":"p2-fixture-qset","relation":"position_held","split":"test","stale_values":[{"kind":'
                    '"expired","value":{"entity":"ex:LouisXIII"}}],"subtype":"current_value","support":['
                    '"f:king-14"],"target_role":"holder","text":"Who was King of France on 1 January 1700?",'
                    '"trace_id":"t:kings","where":{"as_of":"+1700-01-01T00:00:00Z","rank":["preferred","normal"],'
                    '"status":["asserted"],"valid_mode":"definite"}}')


# ------------------------------------------------------------------------------------------------ the table


def test_asked_after_step_1_the_second_king_is_not_yet_known(fixture_schema):
    kings = TRACES["t:kings"]
    g = gold(kings, ask(kings, 1, "position_held", KING, "holder", KINGS_1700), fixture_schema)
    assert sets(g) == ([], [("expired", XIII)], [], [], True) and g["as_at"] == "2026-10-01T00:00:01Z"
    g = gold(kings, ask(kings, 1, "position_held", KING, "holder", "+1620-01-01T00:00:00Z"), fixture_schema)
    assert sets(g) == ([XIII], [], [], [], True)


def test_as_of_null_reads_the_current_belief_without_expired_or_future_values(fixture_schema):
    kings = TRACES["t:kings"]
    assert sets(gold(kings, ask(kings, 2, "position_held", KING, "holder", None), fixture_schema)) == \
        ([XIII, XIV], [], [], [], True)


def test_a_retracted_fact_is_revised_and_leaves_no_current_value(fixture_schema):
    tr = trace("t:ret", entities("ex:Kraków", "ex:Maria_Skłodowska", "ex:Warszawa"),
               ("put", [rec("f:born-skłodowska-kraków")]),
               ("apply", {"op": "transition", "targets": ["f:born-skłodowska-kraków"], "to": "retracted",
                          "id": "m:ret-9", "reason": "withdrawn", "evidence": EVIDENCE}))
    assert sets(gold(tr, ask(tr, 2, "born_in", MARIA, "birthplace", None), fixture_schema)) == \
        ([], [("revised", KRAKOW)], [], [], True)
    # asked after step 1 the fact is still asserted: current, not revised
    assert sets(gold(tr, ask(tr, 1, "born_in", MARIA, "birthplace", None), fixture_schema)) == \
        ([KRAKOW], [], [], [], True)


def _disputed() -> dict[str, Any]:
    return trace("t:dis", entities("ex:Kraków", "ex:Maria_Skłodowska", "ex:Warszawa"),
                 ("put", [rec("f:born-skłodowska-kraków")]),
                 ("apply", {"op": "transition", "targets": ["f:born-skłodowska-kraków"], "to": "disputed",
                            "id": "m:dis-9", "reason": "key_conflict", "records": [rec("f:born-skłodowska-warszawa")],
                            "evidence": EVIDENCE}))


def test_disputed_values_with_no_current_value_make_the_question_unanswerable(fixture_schema):
    tr = _disputed()
    assert sets(gold(tr, ask(tr, 2, "born_in", MARIA, "birthplace", None), fixture_schema)) == \
        ([], [], [], [KRAKOW, WARSZAWA], False)
    # a where that reads disputed facts makes them current, and V_cur is subtracted from the disputed set
    q = ask(tr, 2, "born_in", MARIA, "birthplace", None, status=("asserted", "disputed"))
    assert sets(gold(tr, q, fixture_schema)) == ([KRAKOW, WARSZAWA], [], [], [], True)


def test_a_deprecated_fact_with_an_incorrect_reason_is_revised(fixture_schema):
    """``f:pop-łódź-2019-dep`` is deprecated with ``wd:Q41755623`` (incorrect value), the default reason."""
    tr = trace("t:pop", entities("ex:Łódź"), ("put", [rec("f:pop-łódź-2019"), rec("f:pop-łódź-2019-dep")]))
    q = ask(tr, 1, "population", LODZ, "quantity", None)
    assert sets(gold(tr, q, fixture_schema)) == ([qty("+679941")], [("revised", qty("+685285"))], [], [], True)
    assert memory.INCORRECT_REASONS == frozenset({"wd:Q41755623"})
    # the reasons are a parameter (ruling 3): without that reason the deprecated value is no stale value
    assert sets(gold(tr, q, fixture_schema, incorrect_reasons=frozenset())) == ([qty("+679941")], [], [], [], True)
    assert sets(gold(tr, q, fixture_schema, incorrect_reasons=["wd:Q1", "wd:Q41755623"]))[1] == \
        [("revised", qty("+685285"))]
    # a where that reads deprecated facts makes the value current, so it is no longer stale
    q = ask(tr, 1, "population", LODZ, "quantity", None, rank=("preferred", "normal", "deprecated"))
    assert sets(gold(tr, q, fixture_schema)) == ([qty("+679941"), qty("+685285")], [], [], [], True)


def test_only_the_preferred_facts_count_when_one_of_them_is_preferred(fixture_schema):
    other = rec("f:pop-łódź-2019-dep", rank="normal")
    other.pop("rank_reason")
    tr = trace("t:pref", entities("ex:Łódź"), ("put", [rec("f:pop-łódź-2019", rank="preferred"), other]))
    assert sets(gold(tr, ask(tr, 1, "population", LODZ, "quantity", None), fixture_schema)) == \
        ([qty("+679941")], [], [], [], True)
    tr = trace("t:pref", entities("ex:Łódź"), ("put", [rec("f:pop-łódź-2019"), rec("f:pop-łódź-2019-dep")]))
    q = ask(tr, 1, "population", LODZ, "quantity", None, rank=("normal", "deprecated"))
    assert gold(tr, q, fixture_schema)["answer"]["values"] == [qty("+679941"), qty("+685285")]


def test_a_value_both_expired_and_revised_is_listed_as_expired(fixture_schema):
    """LouisXIII holds an ended asserted fact (expired) and a superseded one (revised); LouisXIV holds the
    correction, which ended too."""
    ended = held("f:a", XIII, year(1610), year(1643))
    early = held("f:b", XIII, year(1600), year(1605))
    fixed = held("f:c", XIV, year(1600), year(1605))
    tr = trace("t:both", entities("ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV"), ("put", [ended]),
               ("put", [early]),
               ("apply", {"op": "supersede", "id": "m:sup-9", "superseded": ["f:b"], "records": [fixed],
                          "reason": "correction", "evidence": EVIDENCE}))
    g = gold(tr, ask(tr, 3, "position_held", KING, "holder", KINGS_1700), fixture_schema)
    assert sets(g) == ([], [("expired", XIII), ("expired", XIV)], [], [], True)


def test_a_fact_that_ended_and_was_later_superseded_is_revised(fixture_schema):
    """``expired`` needs an asserted fact: the superseded LouisXIII is revised, the correction (ended) expired."""
    tr = trace("t:ended", entities("ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV"),
               ("put", [held("f:a", XIII, year(1610), year(1643))]),
               ("apply", {"op": "supersede", "id": "m:sup-9", "superseded": ["f:a"],
                          "records": [held("f:a2", XIV, year(1610), year(1643))], "reason": "correction",
                          "evidence": EVIDENCE}))
    g = gold(tr, ask(tr, 2, "position_held", KING, "holder", KINGS_1700), fixture_schema)
    assert sets(g) == ([], [("expired", XIV), ("revised", XIII)], [], [], True)


def test_a_definite_read_inside_a_year_precision_handover_has_no_current_value(fixture_schema):
    """§9.5: an empty V_cur with nothing disputed is a valid "no current value" gold; a possible read sees both."""
    tr = trace("t:handover", entities("ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV"),
               ("put", [held("f:a", XIII, year(1610), year(1643)), held("f:b", XIV, year(1643), year(1715))]))
    mid = "+1643-06-01T00:00:00Z"
    assert sets(gold(tr, ask(tr, 1, "position_held", KING, "holder", mid), fixture_schema)) == \
        ([], [], [], [], True)
    assert sets(gold(tr, ask(tr, 1, "position_held", KING, "holder", mid, mode="possible"), fixture_schema)) == \
        ([XIII, XIV], [], [], [], True)
    # before the handover year LouisXIV is future; after it LouisXIII is expired
    assert sets(gold(tr, ask(tr, 1, "position_held", KING, "holder", "+1620-01-01T00:00:00Z"), fixture_schema)) \
        == ([XIII], [], [XIV], [], True)
    assert sets(gold(tr, ask(tr, 1, "position_held", KING, "holder", KINGS_1700), fixture_schema)) == \
        ([XIV], [("expired", XIII)], [], [], True)


# ------------------------------------------------------------------------------------------------ the replay


def test_the_replay_puts_the_entities_one_second_before_step_1_as_the_trace_actor(fixture_schema):
    rp = memory.replay_trace(TRACES["t:maria"], fixture_schema)
    assert rp.times == {1: "2026-10-01T00:00:01Z", 2: "2026-10-01T00:00:02Z"} and rp.position is None
    entity = rp.store.get("ex:Kraków")
    assert (entity["recorded_at"], entity["recorded_by"]) == ("2026-10-01T00:00:00Z", "trace:t:maria")
    kr = rp.store.history("f:born-skłodowska-kraków")
    assert [(v["status"], v["recorded_at"]) for v in kr] == [("asserted", "2026-10-01T00:00:01Z"),
                                                            ("superseded", "2026-10-01T00:00:02Z")]
    assert rp.store.get("m:sup-1")["recorded_by"] == "trace:t:maria"
    assert sorted(rp.entities()) == ["ex:Kraków", "ex:Maria_Skłodowska", "ex:Warszawa"]


def test_reading_a_full_replay_at_tau_equals_the_replay_up_to_the_step(fixture_schema):
    """``derive_memory_gold`` replays up to ``ask_after_step``; layer I replays a trace once and reads at τ."""
    for tr in TRACES.values():
        full = memory.replay_trace(tr, fixture_schema)
        for step in (1, 2):
            for as_of in (None, "+1620-01-01T00:00:00Z", KINGS_1700):
                key, role, rel = (KING, "holder", "position_held") if tr["trace_id"] == "t:kings" else \
                    (MARIA, "birthplace", "born_in")
                q = ask(tr, step, rel, key, role, as_of)
                assert memory.read_gold(full, q) == gold(tr, q, fixture_schema)


def test_events_run_in_step_order_whatever_the_list_order(fixture_schema):
    tr = copy.deepcopy(TRACES["t:kings"])
    tr["events"].reverse()
    assert sets(gold(tr, QUESTIONS["mq:king-1700"], fixture_schema)) == ([XIV], [("expired", XIII)], [], [], True)


def test_the_store_refusal_of_a_trace_propagates(fixture_schema):
    """A lifecycle record in a put is D014 (§9.5); the replay names the event that failed."""
    tr = trace("t:bad", entities("ex:Kraków", "ex:Maria_Skłodowska", "ex:Warszawa"),
               ("put", [rec("f:born-skłodowska-kraków")]), ("put", [rec("m:sup-1")]))
    with pytest.raises(KHGError) as e:
        gold(tr, ask(tr, 2, "born_in", MARIA, "birthplace", None), fixture_schema)
    assert e.value.codes == ("KHG-D014",)
    rp = memory.Replay(tr, fixture_schema)
    with pytest.raises(KHGError):
        rp.run()
    assert rp.position == 1  # the index of the failing event in trace["events"]
    [f] = memory.replay_findings(e.value, path="/lines/4/events/1")
    assert (f["code"], f["path"], f["nested"]["code"]) == ("KHG-I003", "/lines/4/events/1", "KHG-D014")


# ------------------------------------------------------------------------------------------------ errors


def test_questions_the_replay_cannot_answer(fixture_schema):
    kings = TRACES["t:kings"]
    with pytest.raises(ValueError, match="no step 3"):
        gold(kings, ask(kings, 3, "position_held", KING, "holder", None), fixture_schema)
    with pytest.raises(ValueError, match="names trace"):
        gold(kings, dict(ask(kings, 2, "position_held", KING, "holder", None), trace_id="t:maria"), fixture_schema)
    with pytest.raises(ValidationError) as e:
        gold(kings, ask(kings, 2, "reigned", KING, "holder", None), fixture_schema)
    assert e.value.codes == ("KHG-S001",)
    with pytest.raises(ValidationError) as e:
        gold(kings, ask(kings, 2, "position_held", KING, "monarch", None), fixture_schema)
    assert e.value.codes == ("KHG-S002",)
    with pytest.raises(ValueError, match="exactly the key roles"):  # holder is a role, not the key
        gold(kings, ask(kings, 2, "position_held", [{"role": "holder", "value": XIV}], "position", None),
             fixture_schema)
    with pytest.raises(ValueError, match="declares no key"):
        gold(kings, ask(kings, 2, "regulates", [{"role": "regulator", "value": XIV}], "target", None),
             fixture_schema)
    with pytest.raises(ValueError, match="needs 'ask_after_step'"):
        q = ask(kings, 2, "position_held", KING, "holder", None)
        del q["ask_after_step"]
        gold(kings, q, fixture_schema)
    with pytest.raises(TypeError):
        gold(kings, QUESTIONS["mq:king-1700"], fixture_schema, incorrect_reasons="wd:Q41755623")


def test_the_schema_argument_is_a_schema_a_document_or_a_path(fixture_schema):
    q = QUESTIONS["mq:king-1700"]
    want = gold(TRACES["t:kings"], q, fixture_schema)
    assert gold(TRACES["t:kings"], q, data.load_json("fixture/fixture.relation-schema.json")) == want
    assert gold(TRACES["t:kings"], q, data.path("fixture/fixture.relation-schema.json")) == want
    with pytest.raises(ValueError):
        gold(TRACES["t:kings"], q, None)
