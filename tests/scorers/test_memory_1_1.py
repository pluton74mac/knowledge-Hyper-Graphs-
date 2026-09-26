"""P2 ruling 21 (a, b): the memory gold of ``khg-scorers`` 1.1.0 (DESIGN §9.5), from P3a's proposal (part B; P3a
ruling 7) as P7 confirmed it (P7 DESIGN §7.2; P7 ruling 5).

- **``outranked``**, a third stale kind: the target values of facts on the question's key that are asserted, of rank
  ``normal``, and hold at t under the question's ``valid_mode`` (every fact holds when ``as_of`` is null), while an
  asserted ``preferred`` fact on the key holds at t; V_cur is subtracted, and ``expired`` and ``revised`` come first.
- **The incorrect reasons** that make a deprecated value ``revised``: P3a's nine plus Q189203 "anachronism", without
  Q42727519 "less precision".
- **The rules are versioned with the C4 draft** (ruling 3: a change of the reasons is a minor release of the draft):
  a ``khg-c4-items/0.1.x`` file is replayed with the 0.1 rules (Q41755623 only, no ``outranked``), so a valid 0.1.0
  file stays valid; a 0.2.x file, and the scorer's defaults, use the 0.2 rules.
"""
from __future__ import annotations

import copy
import dataclasses
from typing import Any

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError
from khg_contracts.scorers import memory
from khg_contracts.scorers.bootstrap import Bootstrap
from khg_contracts.validate import ENGINES, run, validate_item

FIXTURE = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"] if "id" in r}
SCHEMA = data.load_json("fixture/fixture.relation-schema.json")
EVIDENCE = [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}}]
KING = [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}]
MARIA = [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}]
LODZ = [{"role": "place", "value": {"entity": "ex:Łódź"}},
        {"role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z",
                                                        "precision": 9, "calendar": "gregorian"}}}]
XIII, MAZARIN = {"entity": "ex:LouisXIII"}, {"entity": "ex:Mazarin"}
KRAKOW, WARSZAWA = {"entity": "ex:Kraków"}, {"entity": "ex:Warszawa"}
NINE = {"wd:Q41755623", "wd:Q29998666", "wd:Q25895909", "wd:Q21655367", "wd:Q14946528", "wd:Q28091153",
        "wd:Q35773207", "wd:Q22979588", "wd:Q110646418"}
RULES_0_1 = {"incorrect_reasons": frozenset({"wd:Q41755623"}), "outranked": False}


def qty(amount: str) -> dict[str, Any]:
    return {"literal": {"datatype": "quantity", "amount": amount, "unit": "1"}}


def year(y: int) -> dict[str, Any]:
    return {"literal": {"datatype": "time", "time": f"+{y}-00-00T00:00:00Z", "precision": 9, "calendar": "gregorian"}}


def rec(rid: str, **changes: Any) -> dict[str, Any]:
    r = copy.deepcopy(FIXTURE[rid])
    for f in ("version", "recorded_at", "recorded_by", "status_ref"):
        r.pop(f, None)
    r["status"] = "asserted"
    r.update(changes)
    return r


def pop(fid: str, amount: str, rank: str = "normal", reasons: list[str] | None = None) -> dict[str, Any]:
    r = rec("f:pop-łódź-2019", id=fid, rank=rank, evidence=copy.deepcopy(EVIDENCE))
    r["bindings"][2]["value"] = qty(amount)
    if reasons is not None:
        r["rank_reason"] = reasons
    return r


def held(fid: str, holder: dict[str, Any], start: int, end: int, rank: str = "normal") -> dict[str, Any]:
    r = rec("f:king-13", id=fid, rank=rank, evidence=copy.deepcopy(EVIDENCE))
    r["bindings"] = [{"bid": "b1", "role": "holder", "value": holder},
                     {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}},
                     {"bid": "b3", "role": "start_time", "value": year(start)},
                     {"bid": "b4", "role": "end_time", "value": year(end)}]
    return r


def born(fid: str, place: dict[str, Any], rank: str = "normal", reasons: list[str] | None = None) -> dict[str, Any]:
    r = rec("f:born-skłodowska-warszawa", id=fid, rank=rank, evidence=copy.deepcopy(EVIDENCE))
    r["bindings"][0]["value"] = place
    if reasons is not None:
        r["rank_reason"] = reasons
    return r


def trace(tid: str, ents: list[str], *puts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"kind": "c4-memory-trace", "id": "c4:" + tid.replace(":", "-"), "qset": "r21", "split": "test",
            "trace_id": tid, "entities": [copy.deepcopy(FIXTURE[e]) for e in ents],
            "events": [{"step": i, "tx_time": f"2026-10-01T00:00:{i:02d}Z", "put": p} for i, p in enumerate(puts, 1)]}


def ask(tr: dict[str, Any], relation: str, key: list[dict[str, Any]], role: str, as_of: str | None, *,
        qid: str = "mq:r21", mode: str = "definite") -> dict[str, Any]:
    return {"kind": "c4-memory-question", "id": "c4:" + qid.replace(":", "-"), "qset": "r21", "split": "test",
            "qid": qid, "trace_id": tr["trace_id"], "ask_after_step": len(tr["events"]), "subtype": "current_value",
            "text": "?", "relation": relation, "key": key, "target_role": role, "support": [],
            "where": {"as_of": as_of, "valid_mode": mode, "rank": ["preferred", "normal"], "status": ["asserted"]}}


def stale(tr: dict[str, Any], q: dict[str, Any], **rules: Any) -> tuple[list[Any], list[tuple[str, Any]]]:
    g = memory.derive_memory_gold(tr, q, schema=SCHEMA, **rules)
    return g["answer"]["values"], [(s["kind"], s["value"]) for s in g["stale_values"]]


def stored(tr: dict[str, Any], q: dict[str, Any], **rules: Any) -> dict[str, Any]:
    """The question with the gold the replay derives under ``rules``, as a writer stores it."""
    out = copy.deepcopy(q)
    out.update({k: v for k, v in memory.derive_memory_gold(tr, q, schema=SCHEMA, **rules).items()
                if k in memory.GOLD_FIELDS})
    return out


# ------------------------------------------------------------------------------------------------ the defaults


def test_the_default_incorrect_reasons_are_p3a_s_nine_and_anachronism():
    assert memory.INCORRECT_REASONS == frozenset(NINE | {"wd:Q189203"})
    assert "wd:Q42727519" not in memory.INCORRECT_REASONS  # less precision: a generalisation, not an error
    assert memory.INCORRECT_REASONS_0_1 == frozenset({"wd:Q41755623"})
    config = memory.MemoryConfig()
    assert config.incorrect_reasons == memory.INCORRECT_REASONS and config.outranked is True
    assert {f.name for f in dataclasses.fields(memory.MemoryConfig)} == {"mode", "incorrect_reasons", "outranked",
                                                                         "bootstrap"}


@pytest.mark.parametrize(("stamp", "rules"), [
    ("khg-c4-items/0.1.0", RULES_0_1), ("khg-c4-items/0.1.9", RULES_0_1), ("khg-c4-items/0.0.3", RULES_0_1),
    ("khg-c4-items/0.2.0", {"incorrect_reasons": memory.INCORRECT_REASONS, "outranked": True}),
    (None, {"incorrect_reasons": memory.INCORRECT_REASONS, "outranked": True})])
def test_the_rules_follow_the_c4_stamp(stamp, rules):
    assert memory.gold_rules(stamp) == rules
    assert memory.MemoryConfig(**memory.gold_rules(stamp)).outranked is rules["outranked"]


def test_a_stamp_the_reader_does_not_take_has_no_rules():
    for stamp in ("khg-c4-items/0.3.0", "khg-c4-items/1.0.0", "khg-queue/1.0.0", 7):
        with pytest.raises(ValueError):
            memory.gold_rules(stamp)


@pytest.mark.parametrize(("reason", "revised"), [
    *[(r, True) for r in sorted(NINE)], ("wd:Q189203", True),
    ("wd:Q42727519", False), ("wd:Q107356532", False), ("unspecified", False)])
def test_which_deprecation_reasons_make_a_value_revised(reason, revised):
    tr = trace("t:maria", ["ex:Maria_Skłodowska", "ex:Kraków", "ex:Warszawa"],
               [born("f:b1", KRAKOW, "deprecated", [reason]), born("f:b2", WARSZAWA)])
    q = ask(tr, "born_in", MARIA, "birthplace", None)
    assert stale(tr, q) == ([WARSZAWA], [("revised", KRAKOW)] if revised else [])
    # under the 0.1 rules only "incorrect value" does
    assert stale(tr, q, **RULES_0_1) == ([WARSZAWA], [("revised", KRAKOW)] if reason == "wd:Q41755623" else [])


# ------------------------------------------------------------------------------------------------ outranked


def test_last_years_value_is_outranked_by_the_preferred_one():
    """P3a's series case on a non-temporal key: the normal value holds (as_of null) beside a preferred one."""
    tr = trace("t:pop", ["ex:Łódź"], [pop("f:p1", "+679941")], [pop("f:p2", "+679900", "preferred")])
    q = ask(tr, "population", LODZ, "quantity", None)
    assert stale(tr, q) == ([qty("+679900")], [("outranked", qty("+679941"))])
    assert stale(tr, q, outranked=False) == ([qty("+679900")], [])
    assert stale(tr, q, **RULES_0_1) == ([qty("+679900")], [])


def test_without_a_preferred_fact_nothing_is_outranked():
    tr = trace("t:pop", ["ex:Łódź"], [pop("f:p1", "+679941")], [pop("f:p2", "+679900", "deprecated", ["wd:Q1"])])
    assert stale(tr, ask(tr, "population", LODZ, "quantity", None)) == ([qty("+679941")], [])


def test_outranked_needs_both_facts_to_hold_at_t():
    """On a temporal key: Louis XIII (normal, 1610-1643) and Mazarin (preferred, 1640-1650) hold together only from
    1640 to 1643."""
    tr = trace("t:kings", ["ex:KingOfFrance", "ex:LouisXIII", "ex:Mazarin"],
               [held("f:k1", XIII, 1610, 1643)], [held("f:k2", MAZARIN, 1640, 1650, "preferred")])
    key = ("position_held", KING, "holder")
    assert stale(tr, ask(tr, *key, "+1641-06-01T00:00:00Z")) == ([MAZARIN], [("outranked", XIII)])
    g = memory.derive_memory_gold(tr, ask(tr, *key, "+1620-06-01T00:00:00Z"), schema=SCHEMA)
    assert (g["answer"]["values"], g["stale_values"], g["future_values"]) == ([XIII], [], [MAZARIN])
    assert stale(tr, ask(tr, *key, "+1645-06-01T00:00:00Z")) == ([MAZARIN], [("expired", XIII)])
    # a possible read at the start year of the preferred fact: both hold possibly
    assert stale(tr, ask(tr, *key, "+1640-01-01T00:00:00Z", mode="possible")) == ([MAZARIN], [("outranked", XIII)])


def test_expired_and_revised_come_before_outranked():
    """Louis XIII holds an ended fact (expired at t) and a normal one that a preferred fact outranks at t: expired."""
    tr = trace("t:kings", ["ex:KingOfFrance", "ex:LouisXIII", "ex:Mazarin"],
               [held("f:k1", XIII, 1600, 1605)], [held("f:k3", XIII, 1630, 1650)],
               [held("f:k2", MAZARIN, 1640, 1650, "preferred")])
    assert stale(tr, ask(tr, "position_held", KING, "holder", "+1641-06-01T00:00:00Z")) == \
        ([MAZARIN], [("expired", XIII)])
    tr = trace("t:pop", ["ex:Łódź"], [pop("f:p1", "+679941"), pop("f:p3", "+679941", "deprecated", ["wd:Q41755623"])],
               [pop("f:p2", "+679900", "preferred")])
    assert stale(tr, ask(tr, "population", LODZ, "quantity", None)) == ([qty("+679900")],
                                                                        [("revised", qty("+679941"))])


def test_an_outranked_answer_is_stale_not_wrong():
    gold = {"answer": {"values": [qty("+679900")]}, "stale_values": [{"kind": "outranked", "value": qty("+679941")}],
            "future_values": [], "disputed_values": [], "answerable": True}
    old = memory.classify([(memory.identity_key(qty("+679941")), qty("+679941"))], False, gold)
    assert (old["outcome"], old["stale_kind"], old["strict"], old["lenient"]) == ("stale", "outranked", 0, 0)
    assert old["hits"]["outranked"] == 1
    both = memory.classify([(memory.identity_key(v), v) for v in (qty("+679900"), qty("+679941"))], False, gold)
    assert (both["outcome"], both["lenient"]) == ("hedged", 1)


def test_the_report_splits_the_stale_rate_three_ways():
    tr = trace("t:pop", ["ex:Łódź"], [pop("f:p1", "+679941"), pop("f:p3", "+685285", "deprecated", ["wd:Q41755623"])],
               [pop("f:p2", "+679900", "preferred")])
    qs = [stored(tr, ask(tr, "population", LODZ, "quantity", None, qid=f"mq:{n}")) for n in ("a", "b", "c")]
    assert [s["kind"] for s in qs[0]["stale_values"]] == ["revised", "outranked"]

    def response(qid: str, value: Any) -> dict[str, Any]:
        return {"kind": "memory-response", "qid": qid, "answer": {"values": [value], "abstained": False}}

    rs = [response("mq:a", qty("+679941")), response("mq:b", qty("+685285")), response("mq:c", qty("+679900"))]
    rep = memory.score(qs, rs, traces=[tr], schema=SCHEMA, config=memory.MemoryConfig(bootstrap=Bootstrap(0)))
    agg = rep["aggregate"]
    assert rep["items"]["mq:a"]["stale_kind"] == "outranked" and rep["items"]["mq:b"]["stale_kind"] == "revised"
    assert (agg["stale_rate"], agg["stale_expired_rate"], agg["stale_revised_rate"], agg["stale_outranked_rate"]) == \
        (2 / 3, 0.0, 1 / 3, 1 / 3)
    # scored with the 0.1 rules, the stored 0.2 gold disagrees with the replay: I005
    with pytest.raises(ValidationError) as e:
        memory.score(qs, rs, traces=[tr], schema=SCHEMA, config=memory.MemoryConfig(**RULES_0_1))
    assert e.value.codes == ("KHG-I005",)


# ------------------------------------------------------------------------------------------------ layer I: the stamp


def c4_file(stamp: str, question: dict[str, Any], tr: dict[str, Any]) -> list[dict[str, Any]]:
    head = {"kind": "c4-header", "format": stamp, "qset": "r21", "record_format": "khg-record/1.0.0",
            "schema": {"id": "p2-gate", "version": "1.0.0",
                       "sha256": "sha256:cadd01cd3d37e09337d2fe70bd5572a32dff4a7d6f4a0ac26845c6c27d0e194d"}}
    return [head, tr, question]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_0_1_file_is_replayed_by_the_0_1_rules(engine):
    """A 0.1.0 writer stored this gold with the 0.1 rules (no outranked value, no conflation). It stays valid; the
    same lines stamped 0.2.0 disagree with the 0.2 replay (I005)."""
    tr = trace("t:mix", ["ex:Maria_Skłodowska", "ex:Kraków", "ex:Warszawa"],
               [born("f:b1", KRAKOW, "deprecated", ["wd:Q14946528"]), born("f:b2", WARSZAWA)])
    q = stored(tr, ask(tr, "born_in", MARIA, "birthplace", None), **RULES_0_1)
    assert q["stale_values"] == []
    assert validate_item(c4_file("khg-c4-items/0.1.0", q, tr), schema=SCHEMA, engine=engine)["ok"]
    rep = run(c4_file("khg-c4-items/0.2.0", q, tr), kind="item", schema=SCHEMA, engine=engine)
    assert [(f["code"], f["path"]) for f in rep.findings] == [("KHG-I005", "/lines/2/stale_values")]
    # and a 0.2 writer's gold is valid stamped 0.2.0 and refused stamped 0.1.0
    q2 = stored(tr, ask(tr, "born_in", MARIA, "birthplace", None))
    assert q2["stale_values"] == [{"kind": "revised", "value": KRAKOW}]
    assert validate_item(c4_file("khg-c4-items/0.2.0", q2, tr), schema=SCHEMA, engine=engine)["ok"]
    rep = run(c4_file("khg-c4-items/0.1.0", q2, tr), kind="item", schema=SCHEMA, engine=engine)
    assert [(f["code"], f["path"]) for f in rep.findings] == [("KHG-I005", "/lines/2/stale_values")]


def test_an_outranked_kind_in_a_0_1_file_is_i005_not_a_schema_error():
    tr = trace("t:pop", ["ex:Łódź"], [pop("f:p1", "+679941")], [pop("f:p2", "+679900", "preferred")])
    q = stored(tr, ask(tr, "population", LODZ, "quantity", None))
    assert q["stale_values"] == [{"kind": "outranked", "value": qty("+679941")}]
    assert validate_item(c4_file("khg-c4-items/0.2.0", q, tr), schema=SCHEMA)["ok"]
    rep = run(c4_file("khg-c4-items/0.1.0", q, tr), kind="item", schema=SCHEMA)
    assert [(f["code"], f["path"]) for f in rep.findings] == [("KHG-I005", "/lines/2/stale_values")]


def test_the_packaged_0_1_file_has_the_same_gold_under_both_rules():
    """The fixture's memory questions depend on neither change: the default configuration still scores them."""
    lines = data.load_jsonl("fixture/c4-items.jsonl")
    traces = {x["trace_id"]: x for x in lines if x["kind"] == "c4-memory-trace"}
    for q in (x for x in lines if x["kind"] == "c4-memory-question"):
        a = memory.derive_memory_gold(traces[q["trace_id"]], q, schema=SCHEMA)
        b = memory.derive_memory_gold(traces[q["trace_id"]], q, schema=SCHEMA, **RULES_0_1)
        assert a == b


@pytest.mark.parametrize("engine", ENGINES)
def test_the_0_2_example_shows_both_changes(engine):
    lines = data.load_jsonl("fixture/c4-items-0.2.0.jsonl")
    qs = {q["qid"]: q for q in lines if q["kind"] == "c4-memory-question"}
    assert [s["kind"] for s in qs["mq:lodz-2019"]["stale_values"]] == ["revised", "outranked"]
    assert [s["kind"] for s in qs["mq:maria-conflation"]["stale_values"]] == ["revised"]
    rep = run(lines, kind="item", schema=SCHEMA, engine=engine)
    assert rep.findings == []
    lines[0]["format"] = "khg-c4-items/0.1.0"  # read by the 0.1 rules, both questions disagree with their replay
    rep = run(lines, kind="item", schema=SCHEMA, engine=engine)
    n = {q["qid"]: i for i, q in enumerate(lines) if q["kind"] == "c4-memory-question"}
    assert sorted((f["code"], f["path"]) for f in rep.findings) == sorted(
        [("KHG-I005", f"/lines/{n['mq:lodz-2019']}/stale_values"),
         ("KHG-I005", f"/lines/{n['mq:maria-conflation']}/stale_values")])
