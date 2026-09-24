"""P7's call sequence (DESIGN §1.3): memory with belief revision.

The sequence puts ``entities`` into a fresh ``MemoryStore``, then a ``new`` fact, and handles the ``KeyCollision`` it
raises with the action §2.5 gives each conflict. For ``put(new)`` to collide, the store must already believe
something on the same key, so ``entities`` holds what P7's memory holds when ``new`` arrives: the fixture's entities
and the facts P7 already believes. The sequence runs twice:

- **dispute**: the memory believes Maria Skłodowska was born in Warszawa (and knows the two reigns of the King of
  France); ``new`` says Kraków. ``born_in`` has a non-temporal key with the default policy ``dispute``, so both facts
  become ``disputed`` under the new ``khg:disputes`` record ``m:dis-7``.
- **close_older**: the memory believes Louis XIII still holds the position (his reign has no end yet); ``new`` is
  Louis XIV's reign from 1643-05-14. ``position_held`` has a temporal key with ``close_older`` and the shape is a
  ``succession``, so the sequence ends the older reign at the newcomer's start and then puts the newcomer (§2.5,
  "end the older fact, then the put"; S-KEY-007).

``questions``, ``traces`` and the first response are the packaged C4 memory items and ``c5-outputs.jsonl``; two more
responses answer the other two questions, one of them with a revised value.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import CONTRACTS, identity, record, store
from khg_contracts.scorers import memory

#: The §2.10 example: ``render_text(f:king-14)``.
KING_14_TEXT = ("position_held(holder: Louis XIV; position: King of France; replaces: Louis XIII) "
                "[+1643-05-14T00:00:00Z/11, +1715-09-01T00:00:00Z/11)")
MARIA = ("f:born-skłodowska-kraków", "f:born-skłodowska-warszawa")


def start_literal(fact: dict[str, Any]) -> dict[str, Any]:
    """The value of a fact's start binding (``start_time`` in the p2-gate schema's interval relations)."""
    return next(b["value"] for b in fact["bindings"] if b["role"] == "start_time")


def p7(S: Any, entities: list[dict[str, Any]], new: dict[str, Any], *, inferred_close: dict[str, Any],
       ev: dict[str, Any], key: list[dict[str, Any]], labels: dict[str, str], questions: list[dict[str, Any]],
       responses: list[dict[str, Any]], traces: list[dict[str, Any]]) -> dict[str, Any]:
    """The P7 sequence; returns its variables."""
    # >>> DESIGN §1.3
    # P7: memory with belief revision
    ms = store.MemoryStore(S)
    ms.put(entities, actor="p7")
    try:
        ms.put(new, actor="p7")
    except store.KeyCollision as e:
        for coll in e.info["collisions"]:                       # §2.5: record, policy, conflicts[{id, shape, class, action}]
            for c in coll["conflicts"]:
                old = ms.get_many([c["id"]])[c["id"]]
                baseline = identity.relate(new, old, schema=S)  # P7 may replace this classifier
                if c["action"] == "close_older":
                    ms.apply({"op": "end_validity", "target": c["id"], "end": start_literal(new),
                              "evidence": [inferred_close]}, actor="p7")
                    ms.put(new, actor="p7")                    # §2.5 close_older: end the older fact, then the put
                elif c["action"] == "dispute":
                    ms.apply({"op": "transition", "targets": [c["id"]], "to": "disputed", "records": [new],
                              "id": "m:dis-7", "reason": "key_conflict", "evidence": [ev]}, actor="p7")
    current = ms.find_by_key("position_held", key, where=store.Where(as_of="+1700-01-01T00:00:00Z"))
    walk = ms.supersession_walk("f:born-skłodowska-kraków")
    prompt = [record.render_text(f, labels, schema=S) for f in current]
    report = memory.score(questions, responses, traces=traces, schema=S)
    # <<< DESIGN §1.3
    return dict(locals())  # the loops leave their last values bound: ``coll`` and ``c`` (one collision here)


@pytest.fixture()
def inputs(labels, c4_items, c5_outputs) -> dict[str, Any]:
    """The free variables the two runs share."""
    responses = [x for x in c5_outputs if x["kind"] == "memory-response"] + [
        {"kind": "memory-response", "qid": "mq:king-1620",
         "answer": {"values": [{"entity": "ex:LouisXIII"}], "text": "Louis XIII", "abstained": False}},
        {"kind": "memory-response", "qid": "mq:maria-birthplace",
         "answer": {"values": [{"entity": "ex:Kraków"}], "text": "Kraków", "abstained": False}}]
    return {
        "inferred_close": {"id": "e2", "type": "inferred", "mode": "automatic", "source": {"doc_id": "p7:memory"},
                           "inference": {"rule": "p7:close_older", "from": ["f:king-14"]}},
        "ev": {"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:p7-review"}},
        "key": [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}],
        "labels": labels,
        "questions": [x for x in c4_items if x["kind"] == "c4-memory-question"],
        "traces": [x for x in c4_items if x["kind"] == "c4-memory-trace"],
        "responses": responses,
    }


def check_memory_report(report: dict[str, Any]) -> None:
    """The memory score of the three packaged questions: two current answers and one revised (stale) value."""
    assert report["scorer"] == "memory" and report["contracts"] == dict(CONTRACTS)
    agg = report["aggregate"]
    assert (agg["n_questions"], agg["n_responses"], agg["n_missing"]) == (3, 3, 0)
    assert agg["headline"] == {"metric": "acc_strict", "value": pytest.approx(2 / 3)}
    assert agg["outcomes"]["current"] == 2 and agg["outcomes"]["stale"] == 1
    assert agg["stale_rate"] == pytest.approx(1 / 3) and agg["stale_revised_rate"] == pytest.approx(1 / 3)
    assert agg["stale_expired_rate"] == 0
    items = report["items"]
    assert {q: items[q]["outcome"] for q in items} == {
        "mq:king-1700": "current", "mq:king-1620": "current", "mq:maria-birthplace": "stale"}
    assert items["mq:maria-birthplace"]["depends_on"] == ["f:born-skłodowska-warszawa"]


def test_p7_sequence_dispute(S, by_id, fixture_entities, inputs):
    entities = fixture_entities + [by_id["f:king-13"], by_id["f:king-14"], by_id["f:born-skłodowska-warszawa"]]
    new = copy.deepcopy(by_id["f:born-skłodowska-kraków"])  # the fixture's superseded fact, arriving as asserted
    new["status"] = "asserted"
    del new["status_ref"]
    out = p7(S, entities, new, **inputs)
    ms = out["ms"]

    # the one collision named its conflict with the policy, shape, class and action (§2.5)
    assert out["coll"] == {
        "record": "f:born-skłodowska-kraków", "relation": "born_in",
        "key_digest": "sha256:951a7bba11cca1f6c84ede16cd78c9502d08b7ab45060ff462b2ba4f0eea045c", "policy": "dispute",
        "conflicts": [{"id": "f:born-skłodowska-warszawa", "in_batch": False, "shape": None, "class": "distinct",
                       "action": "dispute"}]}
    assert out["baseline"] == "key_conflict"
    # the transition wrote the newcomer and the khg:disputes record; both facts are disputed under it
    for fid in MARIA:
        fact = ms.get(fid)
        assert (fact["status"], fact["status_ref"]) == ("disputed", "m:dis-7")
    dispute = ms.get("m:dis-7")
    assert (dispute["relation"], dispute["reason"], dispute["status"]) == ("khg:disputes", "key_conflict", "asserted")
    assert sorted(b["value"]["fact"] for b in dispute["bindings"]) == sorted(MARIA)
    assert ms.find_by_key("born_in", [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}]) == []
    # the reads: Louis XIV reigned on 1 January 1700; Kraków has no supersession, so the walk ends where it starts
    assert [f["id"] for f in out["current"]] == ["f:king-14"]
    assert out["walk"] == {"start": "f:born-skłodowska-kraków", "direction": "forward", "steps": [],
                           "terminal": [{"id": "f:born-skłodowska-kraków", "status": "disputed"}]}
    assert out["prompt"] == [KING_14_TEXT]
    check_memory_report(out["report"])


def test_p7_sequence_close_older(S, by_id, fixture_entities, inputs, monkeypatch):
    open_reign = by_id["f:king-13"]  # Louis XIII's reign, not yet ended
    open_reign["bindings"] = [b for b in open_reign["bindings"] if b["role"] != "end_time"]
    open_reign["evidence"][0]["supports"] = ["b1", "b2", "b3"]
    entities = fixture_entities + [open_reign]
    new = by_id["f:king-14"]
    receipts, put = [], store.MemoryStore.put

    def recorded(self, records, **kw):  # the sequence drops the receipts of its puts: keep them, by store
        receipts.append((self, put(self, records, **kw)))
        return receipts[-1][1]
    monkeypatch.setattr(store.MemoryStore, "put", recorded)
    out = p7(S, entities, new, **inputs)
    ms = out["ms"]

    assert out["coll"] == {
        "record": "f:king-14", "relation": "position_held",
        "key_digest": "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96",
        "policy": "close_older",
        "conflicts": [{"id": "f:king-13", "in_batch": False, "shape": "succession", "class": "distinct",
                       "action": "close_older"}]}
    assert out["baseline"] == "key_conflict"
    # end_validity gave the open reign an end at the newcomer's start; the status is unchanged (a world change, F7)
    closed = ms.get("f:king-13")
    assert (closed["version"], closed["status"]) == (2, "asserted")
    assert [b["value"] for b in closed["bindings"] if b["role"] == "end_time"] == [start_literal(new)]
    assert closed["evidence"][-1]["type"] == "inferred"
    assert record.valid_time(closed, S)["kind"] == "period"
    # §2.5, close_older: "then the put". The newcomer is written, and it holds the position on 1 January 1700
    king14 = ms.get("f:king-14")
    assert (king14["version"], king14["status"]) == (1, "asserted")
    assert record.decision_view(king14) == record.decision_view(new)
    assert [f["id"] for f in out["current"]] == ["f:king-14"]
    assert out["prompt"] == [KING_14_TEXT]
    assert out["walk"] == {"start": "f:born-skłodowska-kraków", "direction": "forward", "steps": [],
                           "terminal": [{"id": "f:born-skłodowska-kraków", "status": None}]}
    check_memory_report(out["report"])
    # the newcomer's put (the first one raised) wrote it; the two reigns meet on 1643-05-14, a possible overlap
    # only (L008)
    written = [r for s, r in receipts if s is ms and any(rid == "f:king-14" for rid, *_ in r["records"])]
    assert [r["records"] for r in written] == [[("f:king-14", 1, "created")]]
    assert [w["code"] for w in written[0]["warnings"]] == ["KHG-L008"]
