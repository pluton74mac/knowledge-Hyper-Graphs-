"""W9: ``make_candidate(record, *, queue_id, seq, schema)`` (DESIGN §7, §2.9).

It sets ``cand:<queue_id>.<seq>`` and status ``candidate``, assigns missing bids b1… in listed order, and stamps
``event_hash`` once, at extraction, from the candidate's ``content_key``. The fixture's ``f:king-14`` becomes the
smoke item's payload exactly.
"""
from __future__ import annotations

import copy

import pytest

from khg_contracts import record
from khg_contracts.errors import ValidationError
from khg_contracts.queue import make_candidate
from khg_contracts.queue.checks import item_keys


def test_king_14_becomes_the_smoke_payload(king14, smoke_lines, schema):
    item = smoke_lines[1]
    before = copy.deepcopy(king14)
    cand = make_candidate(king14, queue_id="p2-smoke", seq=1, schema=schema)
    assert cand == item["payload"]
    assert king14 == before  # the input is not changed
    assert item_keys(cand, schema) == item["keys"]
    assert item["keys"] == {"content_key": record.content_key(king14, schema),
                            "core_key": record.core_key(king14, schema),
                            "key_digest": record.key_digest(king14, schema)}


def test_the_event_hash_is_stamped_from_the_candidate_content_key(king14, schema):
    stored = next(e for e in king14["evidence"] if e["id"] == "e2")["event_hash"]
    for e in king14["evidence"]:
        e.pop("event_hash", None)
    cand = make_candidate(king14, queue_id="p2-smoke", seq=1, schema=schema)
    e1, e2 = cand["evidence"]
    assert e2["event_hash"] == stored == record.event_hash(record.content_key(cand, schema), e2)
    assert "event_hash" not in e1  # curated evidence has none
    kept = copy.deepcopy(king14)
    kept["evidence"][1]["event_hash"] = "sha256:" + "4" * 64
    assert make_candidate(kept, queue_id="p2-smoke", seq=1, schema=schema)["evidence"][1]["event_hash"] == \
        "sha256:" + "4" * 64  # a stored event hash is never replaced (the linter reports Q010)


def test_missing_bids_are_assigned_in_listed_order(king14, schema):
    rec = copy.deepcopy(king14)
    order = [b["role"] for b in rec["bindings"]]
    for b in rec["bindings"]:
        if b["role"] != "position":
            del b["bid"]
    for e in rec["evidence"]:
        e.pop("supports")
        e.pop("event_hash", None)
    cand = make_candidate(rec, queue_id="p2-smoke", seq=1, schema=schema)
    bids = {b["role"]: b["bid"] for b in cand["bindings"]}
    assert bids["position"] == "b2"  # kept; the others take b1, b3, b4, b5 in the order they were listed
    listed = [r for r in order if r != "position"]
    assert [bids[r] for r in listed] == ["b1", "b3", "b4", "b5"]
    assert all(e["supports"] == ["b1", "b2", "b3", "b4", "b5"] for e in cand["evidence"])  # the default: every bid
    assert cand == record.normalize(cand, schema)  # canonical form: bindings sorted by role


def test_store_fields_and_derived_are_dropped(king14, schema):
    stored = copy.deepcopy(king14)
    stored.update(version=3, recorded_at="2026-10-01T00:00:09Z", recorded_by="p9",
                  derived=record.derive(king14, schema))
    stored["evidence"][0]["recorded_at"] = "2026-10-01T00:00:09Z"
    stored["status"] = "disputed"
    cand = make_candidate(stored, queue_id="run-1.o1", seq=12, schema=schema)
    assert cand["id"] == "cand:run-1.o1.000012" and cand["status"] == "candidate"
    assert not {"version", "recorded_at", "recorded_by", "derived"} & set(cand)
    assert all("recorded_at" not in e for e in cand["evidence"])
    assert cand == make_candidate(king14, queue_id="run-1.o1", seq=12, schema=schema)


def test_what_make_candidate_refuses(king14, schema):
    entity = {"kind": "entity", "id": "ex:LouisXIV", "types": ["Person"]}
    with pytest.raises(ValidationError) as exc:
        make_candidate(entity, queue_id="p2-smoke", seq=1, schema=schema)
    assert exc.value.codes == ("KHG-C002",)
    for queue_id, seq in (("p2 smoke", 1), ("p2-smoke", 0), ("p2-smoke", -3), ("p2-smoke", 1.0)):
        with pytest.raises(ValueError):
            make_candidate(king14, queue_id=queue_id, seq=seq, schema=schema)
    unknown = copy.deepcopy(king14)
    unknown["relation"] = "reigned"
    unknown["evidence"][1].pop("event_hash")
    with pytest.raises(ValidationError) as exc:  # the event hash needs the content key, which needs the relation
        make_candidate(unknown, queue_id="p2-smoke", seq=1, schema=schema)
    assert exc.value.codes == ("KHG-S001",)
    no_evidence = copy.deepcopy(king14)
    del no_evidence["evidence"]
    assert "evidence" not in make_candidate(no_evidence, queue_id="p2-smoke", seq=1, schema=schema)  # Q001 later
