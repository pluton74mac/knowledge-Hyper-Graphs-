"""The shared row layout and the instant guard (DESIGN §3, §3.6; ruling 4)."""
from __future__ import annotations

import pytest

from khg_contracts.record import NEG_INF, POS_INF, normalize
from khg_contracts.store import MemoryStore

from khg_bakeoff.rows import (INT64_HELD, NEG, POS, assemble, entity_row, instant, native_binding, numeric_instant,
                              prepare, query_instant, record_of, split, unheld_instants, value_from_identity)


def stored(record):
    return dict(normalize(record), version=1, recorded_at="2026-10-01T00:00:00Z", recorded_by="load")


def test_split_and_assemble_are_inverse_on_every_fixture_fact(schema, fixture_doc):
    for r in fixture_doc["records"]:
        if r["kind"] != "hyperedge":
            continue
        rec = stored(r)
        fact, rows = split(rec, schema, 5)
        assert fact["tx_from"] == 5 and fact["tx_to"] is None and fact["n_bindings"] == len(rows)
        assert assemble(fact, reversed(rows)) == rec == record_of(fact, rows)  # binding order is restored
        for row, b in zip(rows, rec["bindings"], strict=True):
            native = native_binding(dict(row, value_json="not read"))  # R-09: never from value_json
            assert {k: v for k, v in native.items() if k not in ("value", "ident")} == \
                {k: v for k, v in b.items() if k != "value"}
            assert native["ident"] == row["ident"]
            time = b["value"].get("literal", {}).get("datatype") == "time"
            if time or "unbound" in b["value"]:  # the identity does not give the value as written
                assert "value" not in native
            else:
                assert native["value"] == b["value"]


def test_record_of_is_the_one_row_to_record_function(schema, fixture_doc):
    """R-06: an entity row or a fact row with its binding rows gives the record back."""
    for r in fixture_doc["records"]:
        rec = stored(r)
        if r["kind"] == "entity":
            assert record_of(entity_row(rec, 3)) == rec
        else:
            assert record_of(*split(rec, schema, 3)) == rec


def test_value_from_identity():
    lang = {"literal": {"datatype": "lang_string", "value": "Tokyo Station", "lang": "en"}}
    time = {"literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11,
                        "calendar": "gregorian"}}
    from khg_contracts.record import identity_key

    assert value_from_identity(identity_key(lang)) == lang
    assert value_from_identity(identity_key({"special": "novalue"})) == {"special": "novalue"}
    assert value_from_identity(identity_key(time)) is None and value_from_identity(None) is None


def test_the_fact_row_holds_what_the_reads_filter_on(schema, fixture_doc):
    king = stored(next(r for r in fixture_doc["records"] if r["id"] == "f:king-14"))
    fact, rows = split(king, schema, 1)
    assert fact["key_digest"] == "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96"
    assert fact["rel_kind"] == "fact" and fact["s_hi"] < fact["e_lo"]
    by_role = {r["role"]: r for r in rows}
    assert by_role["holder"]["ref"] == "ex:LouisXIV" and by_role["holder"]["ident"] is not None
    assert by_role["start_time"]["value_kind"] == "literal" and by_role["start_time"]["ref"] is None
    sup = stored(next(r for r in fixture_doc["records"] if r["id"] == "m:sup-1"))
    assert split(sup, schema, 1)[0]["rel_kind"] == "lifecycle"


def test_instants_in_an_int64_backend():
    assert instant(NEG_INF) == NEG == -(2 ** 62) and instant(POS_INF) == POS == 2 ** 62
    assert instant(INT64_HELD) == INT64_HELD and instant(-INT64_HELD) == -INT64_HELD
    for bad in (INT64_HELD + 1, -INT64_HELD - 1, 315569520000148699584000):
        with pytest.raises(ValueError):
            instant(bad)
    assert query_instant(10 ** 30) == 2 ** 62 - 1 and query_instant(-(10 ** 30)) == -(2 ** 62) + 1
    assert query_instant(123) == 123


@pytest.mark.parametrize("stored_value", [NEG, -INT64_HELD, -5, 0, 7, INT64_HELD, POS])
@pytest.mark.parametrize("t", [-(10 ** 30), -(2 ** 62), -INT64_HELD - 1, -5, 0, 7, INT64_HELD + 1, 2 ** 62, 10 ** 30])
def test_a_clamped_query_compares_as_the_exact_one(stored_value, t):
    exact = {NEG: NEG_INF, POS: POS_INF}.get(stored_value, stored_value)
    c = query_instant(t)
    assert (stored_value <= c) == (exact <= t)
    assert (c < stored_value) == (t < exact)


def test_numeric_instants_are_exact():
    assert str(numeric_instant(POS_INF)) == "Infinity" and str(numeric_instant(NEG_INF)) == "-Infinity"
    assert int(numeric_instant(315569520000148699584000)) == 315569520000148699584000


def test_unheld_instants(edge_schema, edge_doc):
    far = next(r for r in edge_doc["records"] if r["id"] == "f:far-future")
    assert unheld_instants(far, edge_schema) == [315569520000148668048000, 315569520000148699584000]
    others = [r for r in edge_doc["records"] if r["id"] != "f:far-future"]
    assert all(unheld_instants(r, edge_schema) == [] for r in others)


def test_patterns_are_refused_as_the_reference_refuses(schema):
    ms = MemoryStore(schema)
    for bad in ("x", {"role": "a"}, [{"role": "agent"}], [{"role": "agent", "value": {"entity": "x"}, "extra": 1}],
                [{"role": "agent", "value": {"entity": "x"}, "position": 0}],
                [{"role": "agent", "value": {"entity": "x"}, "position": True}],
                [{"role": "agent", "value": {"entity": "x"}, "position": None}]):
        with pytest.raises((TypeError, ValueError)) as mine:
            prepare(bad)
        with pytest.raises((TypeError, ValueError)) as ref:
            ms.find("co_administration_causes", bad)
        assert type(mine.value) is type(ref.value), bad
    pats = prepare([{"role": "stop", "value": {"entity": "ex:YYZ"}, "position": 3},
                    {"role": "agent", "value": {"any": True}}, {"role": "holder", "value": {"any_unbound": True}}])
    assert [(p.role, p.position, p.kind) for p in pats] == [("stop", 3, "value"), ("agent", None, "any"),
                                                            ("holder", None, "any_unbound")]
