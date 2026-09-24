"""Review fixes b-validate-03 and b-validate-07: layer S on literals (DESIGN §2.3, §3, §10.2).

- A usage's ``fillers`` are a disjunction (§3): a literal is allowed when any filler of its datatype allows it, so
  S023 (``precision_min``, ``units``) is reported only when none does.
- A time literal whose year has more digits than Python converts to an int is S006 ("out of range for its lexical
  form"), not an exception out of ``validate``.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from khg_contracts import data
from khg_contracts.schema import Schema, check_schema, load_schema
from khg_contracts.validate import validate, validate_item
from khg_contracts.validate.layers.s import record_findings

ENGINES = ("jsonschema", "fastjsonschema")
SCHEMA_DOC = data.load_json("fixture/fixture.relation-schema.json")
SCHEMA = load_schema(SCHEMA_DOC)
FIXTURE = data.load_json("fixture/fixture.c1.json")
ENTITIES = {r["id"]: r for r in FIXTURE["records"] if r["kind"] == "entity"}


def _record(rid: str) -> dict[str, Any]:
    return copy.deepcopy(next(r for r in FIXTURE["records"] if r["id"] == rid))


def _index(rid: str) -> int:
    return next(i for i, r in enumerate(FIXTURE["records"]) if r["id"] == rid)


def _binding(record: dict[str, Any], role: str) -> tuple[int, dict[str, Any]]:
    return next((j, b) for j, b in enumerate(record["bindings"]) if b["role"] == role)


def _schema_with(role: str, fillers: list[dict[str, Any]], relation: str = "station_profile") -> Schema:
    doc = copy.deepcopy(SCHEMA_DOC)
    rel = next(r for r in doc["relations"] if r["id"] == relation)
    next(u for u in rel["roles"] if u["role"] == role)["fillers"] = fillers
    assert check_schema(doc) == [] and check_schema(doc, engine="fastjsonschema") == []
    return load_schema(doc)


def _s(record: Any, schema: Schema) -> list[tuple[str, str]]:
    return [(f["code"], f["path"]) for f in record_findings(record, schema, entities=ENTITIES)]


# ------------------------------------------------------------------------------------------------ b-validate-03


def test_a_unit_that_a_second_quantity_filler_allows_is_accepted():
    schema = _schema_with("elevation", [{"literal": "quantity", "units": ["wd:Q11573"]},
                                        {"literal": "quantity", "units": ["wd:Q3710"]}])
    station = _record("f:station-東京")
    j, b = _binding(station, "elevation")
    assert _s(station, schema) == []
    b["value"]["literal"]["unit"] = "wd:Q3710"
    assert _s(station, schema) == []
    b["value"]["literal"]["unit"] = "wd:Q828224"
    found = record_findings(station, schema, entities=ENTITIES)
    assert [(f["code"], f["path"]) for f in found] == [("KHG-S023", f"/bindings/{j}")]
    assert "wd:Q11573" in found[0]["message"] and "wd:Q3710" in found[0]["message"]


def test_a_filler_without_units_allows_any_unit():
    schema = _schema_with("elevation", [{"literal": "quantity", "units": ["wd:Q11573"]}, {"literal": "quantity"}])
    station = _record("f:station-東京")
    _binding(station, "elevation")[1]["value"]["literal"]["unit"] = "wd:Q828224"
    assert _s(station, schema) == []


def test_a_precision_that_a_second_time_filler_allows_is_accepted():
    schema = _schema_with("opened", [{"literal": "time", "precision_min": 11}, {"literal": "time"}])
    station = _record("f:station-東京")
    j, b = _binding(station, "opened")
    b["value"]["literal"] = {"datatype": "time", "time": "+1914-00-00T00:00:00Z", "precision": 9,
                             "calendar": "gregorian"}
    assert _s(station, schema) == []
    stricter = _schema_with("opened", [{"literal": "time", "precision_min": 11}, {"literal": "time",
                                                                                 "precision_min": 10}])
    found = record_findings(station, stricter, entities=ENTITIES)
    assert [(f["code"], f["path"]) for f in found] == [("KHG-S023", f"/bindings/{j}")]
    assert "precision_min 10" in found[0]["message"]  # the least any filler asks for


@pytest.mark.parametrize("engine", ENGINES)
def test_a_container_run_and_the_designed_cases_still_agree(engine):
    schema = _schema_with("elevation", [{"literal": "quantity", "units": ["wd:Q11573"]},
                                        {"literal": "quantity", "units": ["wd:Q3710"]}])
    doc = copy.deepcopy(FIXTURE)
    i = _index("f:station-東京")
    j, b = _binding(doc["records"][i], "elevation")
    b["value"]["literal"]["unit"] = "wd:Q3710"
    doc["header"]["schema"] = schema.header
    assert validate(doc, schema=schema, engine=engine)["ok"]
    # MC113 and MC114 with the fixture schema: one filler each, so S023 as before
    for rid, role, literal in (
            ("f:pop-łódź-2019", "point_in_time", {"datatype": "time", "time": "+2010-00-00T00:00:00Z", "precision": 8,
                                                  "calendar": "gregorian"}),
            ("f:pop-łódź-2019", "quantity", {"datatype": "quantity", "amount": "+679941", "unit": "wd:Q11573"})):
        doc = copy.deepcopy(FIXTURE)
        i = _index(rid)
        j, b = _binding(doc["records"][i], role)
        b["value"]["literal"] = literal
        found = validate(doc, schema=SCHEMA, engine=engine)["findings"]
        assert ("KHG-S023", f"/records/{i}/bindings/{j}") in [(f["code"], f["path"]) for f in found]


# ------------------------------------------------------------------------------------------------ b-validate-07
# A year of 5000 digits: ``record.parse_time`` refuses it (C004 once it bounds the digits of a year; before that,
# ``int()`` raised a plain ValueError, which layer S now reports as S006). Either way it is an error finding at the
# literal, never an exception out of ``validate``.

HUGE = "+" + "1" * 5000 + "-00-00T00:00:00Z"
REFUSED = {"KHG-C004", "KHG-S006"}


def _huge_king() -> tuple[dict[str, Any], int]:
    king = _record("f:king-14")
    j, b = _binding(king, "start_time")
    b["value"]["literal"] = {"datatype": "time", "time": HUGE, "precision": 9}
    return king, j


def _at(findings: list[dict[str, Any]], path: str) -> set[str]:
    return {f["code"] for f in findings if f["path"] == path and f["severity"] == "error"}


def test_record_findings_report_a_year_too_long_to_convert():
    king, j = _huge_king()
    found = record_findings(king, SCHEMA, entities=ENTITIES)
    assert _at(found, f"/bindings/{j}/value/literal") & REFUSED


def test_a_value_error_from_the_time_parse_is_s006_not_an_exception(monkeypatch):
    """The safety net: whatever ``parse_time`` raises beyond its own findings is S006 at the literal."""
    from khg_contracts.validate.layers import s as layer_s

    def overflow(*args: Any) -> Any:
        raise ValueError("Exceeds the limit (4300 digits) for integer string conversion")

    monkeypatch.setattr(layer_s, "parse_time", overflow)
    king = _record("f:king-14")
    j, _ = _binding(king, "start_time")
    found = record_findings(king, SCHEMA, entities=ENTITIES)
    assert _at(found, f"/bindings/{j}/value/literal") == {"KHG-S006"}


@pytest.mark.parametrize("engine", ENGINES)
def test_a_record_or_container_with_a_year_too_long_to_convert_is_refused(engine):
    king, j = _huge_king()
    result = validate(king, kind="record", schema=SCHEMA, engine=engine)
    assert not result["ok"] and _at(result["findings"], f"/bindings/{j}/value/literal") & REFUSED
    doc = copy.deepcopy(FIXTURE)
    i = _index("f:king-14")
    doc["records"][i] = king
    result = validate(doc, schema=SCHEMA, engine=engine)
    assert not result["ok"] and _at(result["findings"], f"/records/{i}/bindings/{j}/value/literal") & REFUSED


@pytest.mark.parametrize("engine", ENGINES)
def test_a_c4_trace_with_a_year_too_long_to_convert_is_i003_with_the_refusal_nested(engine):
    lines = data.load_jsonl("fixture/c4-items.jsonl")
    n = next(k for k, x in enumerate(lines) if x["kind"] == "c4-memory-trace")
    event = next(ev for ev in lines[n]["events"] if ev.get("put"))
    put = event["put"][0]
    lit = next(b["value"]["literal"] for b in put["bindings"]
               if "literal" in b["value"] and b["value"]["literal"].get("datatype") == "time")
    lit.update(time=HUGE, precision=9)
    lit.pop("calendar", None)
    result = validate_item(lines, schema=SCHEMA, engine=engine)
    assert not result["ok"]
    nested = {f["nested"]["code"] for f in result["findings"] if f["code"] == "KHG-I003" and "nested" in f}
    assert nested & REFUSED


@pytest.mark.parametrize("engine", ENGINES)
def test_a_queue_payload_with_a_year_too_long_to_convert_is_refused(engine):
    lines = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    n = next(k for k, x in enumerate(lines) if x["kind"] == "queue-item")
    j, b = _binding(lines[n]["payload"], "start_time")
    b["value"]["literal"] = {"datatype": "time", "time": HUGE, "precision": 9}
    result = validate(lines, kind="queue", schema=SCHEMA,
                      bases={"p2-smoke-base": data.load_json("fixture/smoke-base.c1.json")}, engine=engine)
    assert not result["ok"] and _at(result["findings"], f"/lines/{n}/payload/bindings/{j}/value/literal") & REFUSED
