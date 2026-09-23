"""W3: the canonical form: normalize, canonical order and decision_view (DESIGN §2.1, §2.2, §2.8.1, §7)."""
from __future__ import annotations

import copy
import unicodedata

from khg_contracts import data, jsonio, record
from khg_contracts.schema import load_schema

S = load_schema(data.path("fixture/fixture.relation-schema.json"))
C1 = data.load_json("fixture/fixture.c1.json")
HISTORY = data.load_json("fixture/fixture.history.c1.json")
FACTS = {r["id"]: r for r in C1["records"] if r["kind"] == "hyperedge"}


def test_the_fixture_is_in_canonical_form():
    for r in C1["records"]:
        assert record.normalize(r, S) == r, r["id"]
    assert record.canonical_container(C1) == C1
    assert record.canonical_container(HISTORY) == HISTORY


def test_normalize_fills_the_defaults_and_sorts():
    raw = {"kind": "hyperedge", "id": "f:k", "relation": "position_held", "status": "asserted",
           "bindings": [{"bid": "b3", "role": "start_time",
                         "value": {"literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11}}},
                        {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}},
                        {"bid": "b1", "role": "holder", "value": {"entity": "ex:LouisXIV"}}],
           "evidence": [{"id": "e2", "type": "curated", "mode": "manual", "source": {"doc_id": "d2"}},
                        {"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "d1"},
                         "supports": ["b3", "b1"]}],
           "derived": {"arity": 2}}
    out = record.normalize(raw, S)
    assert [b["role"] for b in out["bindings"]] == ["holder", "position", "start_time"]
    assert out["bindings"][2]["value"]["literal"]["calendar"] == "gregorian"
    assert [e["id"] for e in out["evidence"]] == ["e1", "e2"]
    assert out["evidence"][0]["supports"] == ["b1", "b3"]
    assert out["evidence"][1]["supports"] == ["b1", "b2", "b3"]  # every bid, what put writes
    assert (out["rank"], out["visibility"]) == ("normal", "visible")
    assert "derived" not in out
    assert "derived" in raw and "rank" not in raw  # the input is not changed


def test_canonical_binding_order_is_role_position_value():
    route = copy.deepcopy(FACTS["f:route-1"])
    route["bindings"].reverse()
    assert [b["bid"] for b in record.normalize(route)["bindings"]] == ["b1", "b2", "b3", "b4"]
    names = copy.deepcopy(FACTS["f:station-東京"])
    names["bindings"].reverse()
    got = [b["bid"] for b in record.normalize(names)["bindings"] if b["role"] == "name"]
    assert got == ["b3", "b2"]  # "en" sorts before "ja" in the canonical value
    assert record.binding_sort_key({"role": "stop", "position": 2, "value": {"entity": "ex:YUL"}}) == \
        ("stop", 2, '{"entity":"ex:YUL"}')


def test_normalize_writes_nfc_and_lower_case_language_tags():
    raw = {"kind": "hyperedge", "id": unicodedata.normalize("NFD", "f:é"), "relation": "station_profile",
           "status": "asserted", "source_text": unicodedata.normalize("NFD", "Łódź"),
           "bindings": [{"bid": "b1", "role": "name",
                         "value": {"literal": {"datatype": "lang_string", "value": "x", "lang": "PL"}}}]}
    out = record.normalize(raw)
    assert out["id"] == "f:\u00e9" and out["source_text"] == unicodedata.normalize("NFC", "Łódź")
    assert out["bindings"][0]["value"]["literal"]["lang"] == "pl"


def test_normalize_keeps_the_written_calendar_and_invents_none_before_1583():
    julian = {"datatype": "time", "time": "+1700-00-00T00:00:00Z", "precision": 9, "calendar": "julian"}
    early = {"datatype": "time", "time": "+1500-01-01T00:00:00Z", "precision": 11}
    raw = {"kind": "hyperedge", "id": "f:c", "relation": "claims", "status": "asserted",
           "bindings": [{"bid": "b1", "role": "point_in_time", "value": {"literal": julian}},
                        {"bid": "b2", "role": "point_in_time", "value": {"literal": early}}]}
    lits = [b["value"]["literal"] for b in record.normalize(raw)["bindings"]]
    assert julian in lits and early in lits  # S006 is left for the validator


def test_normalize_does_not_check():
    raw = {"kind": "hyperedge", "id": "f:bad", "relation": "no_such_relation", "status": "believed",
           "bindings": [{"bid": "b1", "role": "x", "value": {"entity": "ex:a", "fact": "f:b"}},
                        {"bid": "b2", "role": "y", "value": {"literal": {"datatype": "decimal", "value": 1}}},
                        "not a binding"],
           "evidence": [{"id": "e1", "supports": ["b9", 7]}, "not evidence"]}
    out = record.normalize(raw)
    assert out["relation"] == "no_such_relation" and out["status"] == "believed"
    assert len(out["bindings"]) == 3 and len(out["evidence"]) == 2


def test_normalize_is_idempotent():
    for r in C1["records"] + HISTORY["records"]:
        shuffled = copy.deepcopy(r)
        if r["kind"] == "hyperedge":
            shuffled["bindings"].reverse()
            for e in shuffled.get("evidence", []):
                e.pop("supports", None)
        once = record.normalize(shuffled)
        assert record.normalize(once) == once


def test_entities_are_kept_as_they_are():
    tp53 = next(r for r in C1["records"] if r.get("id") == "ex:TP53")
    assert record.normalize(tp53) == tp53 and "rank" not in record.normalize(tp53)


def test_canonical_container_order():
    shuffled = {"header": C1["header"], "records": list(reversed(C1["records"]))}
    shuffled["records"].insert(3, {"kind": "relation-schema", "id": "p2-gate", **{k: v for k, v in S.doc.items()
                                                                                    if k not in ("kind", "id")}})
    out = record.canonical_container(shuffled)
    kinds = [r["kind"] for r in out["records"]]
    assert kinds[0] == "relation-schema" and kinds[1:23] == ["entity"] * 22 and kinds[23:] == ["hyperedge"] * 18
    assert out["records"][1:] == C1["records"]
    assert [r["id"] for r in out["records"][1:23]] == sorted(r["id"] for r in out["records"][1:23])  # code points


def test_history_containers_order_versions():
    shuffled = {"header": HISTORY["header"], "records": list(reversed(HISTORY["records"]))}
    out = record.canonical_container(shuffled)
    assert [(r["id"], r.get("version")) for r in out["records"]] == \
        [(r["id"], r.get("version")) for r in HISTORY["records"]]
    assert [(r["id"], r["version"]) for r in out["records"] if r["kind"] == "hyperedge"] == \
        [("f:king-13", 1), ("f:king-13", 2), ("f:reg-1", 1), ("f:reg-1", 2), ("m:ret-1", 1)]


def test_decision_view_reproduces_the_smoke_decision_hash():
    item = data.load_json("fixture/queue-item.json")
    entry = data.load_json("fixture/action-log.json")
    stored = dict(copy.deepcopy(item["payload"]), id="f:king-14", status="asserted")
    stored.update(version=1, recorded_at="2026-10-01T00:00:07Z", recorded_by="curator:smoke")
    stored["evidence"][0]["recorded_at"] = "2026-10-01T00:00:07Z"
    stored["derived"] = record.derive(stored, S)
    view = record.decision_view(stored)
    assert not set(view) & {"version", "recorded_at", "recorded_by", "derived"}
    assert "recorded_at" not in view["evidence"][0] and "event_hash" in view["evidence"][1]
    assert view == record.normalize(FACTS["f:king-14"])  # accept writes the fixture's f:king-14
    written = [{"id": "f:king-14", "version": 1, "record": view}]
    assert jsonio.digest("khg-decision/1", written) == entry["decision_hash"]
