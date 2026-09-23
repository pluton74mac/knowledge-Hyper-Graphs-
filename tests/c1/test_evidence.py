"""W3: evidence: event_hash, supported values through history, code-point spans, and entity redirects
(DESIGN §2.2, §2.8, §2.9)."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data, jsonio, record
from khg_contracts.schema import load_schema

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
C1 = data.load_json("fixture/fixture.c1.json")
FACTS = {r["id"]: r for r in C1["records"] if r["kind"] == "hyperedge"}
TEXTS = data.load_json("fixture/fixture.doc-texts.json")["texts"]
EXTRACTED = [(f, e) for f in FACTS.values() for e in f.get("evidence", []) if e["type"] == "extracted"]


# ------------------------------------------------------------------------------------------------ event_hash


def test_the_fixture_has_four_extracted_evidence_records():
    assert sorted((f["id"], e["id"]) for f, e in EXTRACTED) == [
        ("f:born-skłodowska-kraków", "e1"), ("f:coadmin-1", "e1"), ("f:king-14", "e2"), ("f:route-1", "e1")]


@pytest.mark.parametrize("fact, ev", EXTRACTED, ids=[f["id"] for f, _ in EXTRACTED])
def test_stored_event_hashes_equal_recomputation(fact, ev):
    assert record.event_hash(record.content_key(fact, S), ev) == ev["event_hash"]


def test_the_event_hash_payload():
    fact, ev = next((f, e) for f, e in EXTRACTED if f["id"] == "f:route-1")
    payload = {"content_key": record.content_key(fact, S), "doc": ev["source"]["doc_sha256"],
               "selectors": sorted(jsonio.canonical(s) for s in ev["selectors"]),
               "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none"}}
    assert jsonio.digest("khg-event/1", payload) == ev["event_hash"]  # run_id is not hashed


def test_what_changes_an_event_hash():
    fact, ev = next((f, e) for f, e in EXTRACTED if f["id"] == "f:king-14")
    ck = record.content_key(fact, S)
    base = record.event_hash(ck, ev)
    same = copy.deepcopy(ev)
    same["selectors"].reverse()
    same["activity"]["run_id"] = "another-run"
    same["confidence"] = {"value": 0.1, "scale": "probability"}
    same["supports"] = ["b1"]
    assert record.event_hash(ck, same) == base
    for change in ({"activity": dict(ev["activity"], model_version="2")},
                   {"source": {"doc_id": "doc:louis-bio"}},  # no doc_sha256: the doc_id is hashed instead
                   {"reference": [{"role": "point_in_time", "value": {"entity": "ex:x"}}]},
                   {"inference": {"rule": "model", "from": []}}):
        assert record.event_hash(ck, dict(ev, **change)) != base, change
    assert record.event_hash(record.content_key(FACTS["f:king-13"], S), ev) != base


def test_two_references_of_one_statement_hash_differently():
    ev = {"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "wd:Q1"}}
    ck = record.content_key(FACTS["f:pop-łódź-2019"], S)
    a = record.event_hash(ck, dict(ev, reference=[{"role": "point_in_time", "value": {"entity": "wd:Q2"}}]))
    b = record.event_hash(ck, dict(ev, reference=[{"role": "point_in_time", "value": {"entity": "wd:Q3"}}]))
    assert a != b


def test_the_queue_item_keys_and_event_hash_equal_recomputation():
    item = data.load_json("fixture/queue-item.json")
    payload = dict(item["payload"], status="asserted")  # the payload read as asserted
    assert item["keys"] == {"content_key": record.content_key(payload, S), "core_key": record.core_key(payload, S),
                            "key_digest": record.key_digest(payload, S)}
    extracted = [e for e in payload["evidence"] if e["type"] in record.EVENT_TYPES]
    assert extracted and all(e["event_hash"] == record.event_hash(item["keys"]["content_key"], e) for e in extracted)


def test_stamping_computes_missing_hashes_once():
    route = copy.deepcopy(FACTS["f:route-1"])
    stored = route["evidence"][0].pop("event_hash")
    route["evidence"].append({"id": "e2", "type": "curated", "mode": "manual", "source": {"doc_id": "d"}})
    stamped = record.stamp_event_hashes(route, S)
    assert stamped["evidence"][0]["event_hash"] == stored
    assert "event_hash" not in stamped["evidence"][1]  # only extracted and inferred evidence has one
    assert "event_hash" not in route["evidence"][0]  # the input is not changed
    later = copy.deepcopy(stamped)
    later["bindings"][1]["value"] = {"entity": "ex:YUL"}
    assert record.stamp_event_hashes(later, S)["evidence"][0]["event_hash"] == stored  # never recomputed


# ------------------------------------------------------------------------------------------------ supported values


def test_supported_values_read_the_first_version_that_carries_the_evidence():
    history = [r for r in data.load_json("fixture/fixture.history.c1.json")["records"] if r.get("id") == "f:king-13"]
    start = {"literal": {"datatype": "time", "time": "+1610-05-14T00:00:00Z", "precision": 11,
                         "calendar": "gregorian"}}
    assert record.supported_values(history, "e1") == {"b1": {"entity": "ex:LouisXIII"},
                                                      "b2": {"entity": "ex:KingOfFrance"}, "b3": start}
    assert record.supported_values(list(reversed(history)), "e2") == {"b4": history[1]["bindings"][0]["value"]}
    assert record.supported_values(history, "e9") == {}


def test_a_later_refinement_is_not_attributed_to_earlier_evidence():
    v1 = copy.deepcopy(FACTS["f:born-scribe"])
    v1["version"] = 1
    v2 = copy.deepcopy(v1)
    v2["version"] = 2
    v2["bindings"][0]["value"] = {"entity": "ex:Paris"}  # somevalue refined
    v2["evidence"].append({"id": "e2", "type": "curated", "mode": "manual", "source": {"doc_id": "d"},
                           "supports": ["b2"]})
    assert record.supported_values([v2, v1], "e1")["b2"] == {"special": "somevalue"}
    assert record.supported_values([v2, v1], "e2") == {"b2": {"entity": "ex:Paris"}}
    del v1["evidence"][0]["supports"]
    assert set(record.supported_values([v1], "e1")) == {"b1", "b2"}  # no supports: every bid


# ------------------------------------------------------------------------------------------------ spans


def test_the_route_quote_spans_code_points_29_to_57():
    text = TEXTS["doc:route-note"]["text"]
    ev = FACTS["f:route-1"]["evidence"][0]
    quote, position = ev["selectors"]
    assert (position["start"], position["end"]) == (29, 57)
    assert record.selected_text(text, position) == quote["exact"] == "Toronto → Montréal → Toronto"
    # the text holds U+20BB7, outside the Basic Multilingual Plane: UTF-16 would give 30-58
    utf16 = len(text[:29].encode("utf-16-le")) // 2
    assert utf16 == 30 and utf16 + len(quote["exact"].encode("utf-16-le")) // 2 == 58


@pytest.mark.parametrize("fact, ev", EXTRACTED, ids=[f["id"] for f, _ in EXTRACTED])
def test_span_selectors_reproduce_the_fixture(fact, ev):
    doc = TEXTS[ev["source"]["doc_id"]]
    assert record.text_sha256(doc["text"]) == doc["sha256"] == ev["source"]["doc_sha256"]
    quote = ev["selectors"][0]
    assert record.span_selectors(doc["text"], quote["exact"]) == ev["selectors"]


def test_span_helpers_refuse_bad_spans():
    text = "Paris, then Paris again"
    assert record.span_selectors(text, "Paris", occurrence=1)[1] == {"type": "position", "start": 12, "end": 17}
    with pytest.raises(ValueError):
        record.span_selectors(text, "Lyon")
    with pytest.raises(ValueError):
        record.span_selectors(text, "Paris", occurrence=2)
    with pytest.raises(ValueError):
        record.span_selectors(text, "")
    for start, end in ((5, 5), (6, 2), (0, 99), (-1, 3)):
        with pytest.raises(ValueError):
            record.selected_text(text, {"type": "position", "start": start, "end": end})


# ------------------------------------------------------------------------------------------------ redirects


def test_redirects_are_followed_to_the_surviving_entity():
    ents = {"ex:a": {"kind": "entity", "id": "ex:a", "redirect_to": "ex:b"},
            "ex:b": {"kind": "entity", "id": "ex:b", "redirect_to": "ex:c"},
            "ex:c": {"kind": "entity", "id": "ex:c"}}
    assert record.resolve_redirects("ex:a", ents) == "ex:c"
    assert record.resolve_redirects("ex:c", ents) == "ex:c"
    assert record.resolve_redirects("ex:unknown", ents) == "ex:unknown"
    assert record.resolve_redirects("ex:a", list(ents.values())) == "ex:c"
    assert record.resolve_redirects("ex:LouisXIV", [r for r in C1["records"] if r["kind"] == "entity"]) == \
        "ex:LouisXIV"


def test_a_redirect_cycle_ends():
    ents = {"ex:a": {"id": "ex:a", "redirect_to": "ex:b"}, "ex:b": {"id": "ex:b", "redirect_to": "ex:a"}}
    assert record.resolve_redirects("ex:a", ents) == "ex:a"
    assert record.resolve_redirects("ex:b", ents) == "ex:b"
