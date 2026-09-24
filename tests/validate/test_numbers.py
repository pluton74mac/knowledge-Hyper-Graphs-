"""Review fixes b-validate-02 and b-validate-04: an integral float is its integer (F10, DESIGN §2.1).

Both engines accept ``1.0`` as a JSON Schema integer, and canonical JSON writes it as ``1``, so a document that
writes an integer as an integral float is canonically equal to the one that writes the integer. It gets the same
verdict: layer S reads positions, selector offsets, precisions and versions through their integral value, layer D
reads versions the same way, and a relation-type schema whose cardinalities or ``precision_min`` are integral floats
is the schema with integers (``Schema`` and the M checks normalise them; its digest was already the same).
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

import pytest

from khg_contracts import data, hif, jsonio
from khg_contracts.schema import Schema, check_schema, load_schema
from khg_contracts.validate import run, validate
from khg_contracts.validate.layers.s import latest_records, record_findings

ENGINES = ("jsonschema", "fastjsonschema")
SCHEMA_DOC = data.load_json("fixture/fixture.relation-schema.json")
SCHEMA = load_schema(SCHEMA_DOC)
FIXTURE = data.load_json("fixture/fixture.c1.json")
HIF = data.load_json("fixture/fixture.hif.json")
HISTORY = data.load_json("fixture/fixture.history.c1.json")
TEXTS = data.load_json("fixture/fixture.doc-texts.json")


def floats(value: Any, keys: Iterable[str]) -> Any:
    """A copy of ``value`` with every integer under one of ``keys`` written as a float."""
    keys = set(keys)

    def walk(x: Any, key: Any = None) -> Any:
        if isinstance(x, dict):
            return {k: walk(v, k) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v, key) for v in x]
        if key in keys and isinstance(x, int) and not isinstance(x, bool):
            return float(x)
        return x
    return walk(value)


def _index(doc: dict[str, Any], rid: str) -> int:
    return next(i for i, r in enumerate(doc["records"]) if r.get("id") == rid)


def _found(result: Any) -> list[tuple[str, str, str]]:
    findings = result["findings"] if isinstance(result, dict) else result.findings
    return [(f["code"], f["severity"], f["path"]) for f in findings]


def _same_verdict(float_doc: Any, int_doc: Any, **kwargs: Any) -> None:
    assert jsonio.canonical(float_doc) == jsonio.canonical(int_doc)
    for engine in ENGINES:
        assert _found(validate(float_doc, engine=engine, **kwargs)) == \
            _found(validate(int_doc, engine=engine, **kwargs)), engine


# ------------------------------------------------------------------------------------------------ b-validate-02


def test_ordered_positions_written_as_floats_are_the_same_positions():
    doc = copy.deepcopy(FIXTURE)
    i = _index(doc, "f:route-1")
    doc["records"][i] = floats(doc["records"][i], ["position"])
    assert doc["records"][i]["bindings"][1]["position"] == 1.0
    _same_verdict(doc, FIXTURE, schema=SCHEMA)
    assert validate(doc, schema=SCHEMA)["ok"]


def test_a_gap_in_float_positions_is_still_s015():
    doc = copy.deepcopy(FIXTURE)
    i = _index(doc, "f:route-1")
    doc["records"][i] = floats(doc["records"][i], ["position"])
    doc["records"][i]["bindings"][3]["position"] = 4.0  # MC105 with a float
    assert ("KHG-S015", "error", f"/records/{i}") in _found(validate(doc, schema=SCHEMA))
    doc["records"][i]["bindings"][3]["position"] = 2.5
    assert "KHG-C010" in [c for c, _, _ in _found(validate(doc, schema=SCHEMA))]  # not an integer: layer C


def test_selector_offsets_written_as_floats_are_the_same_span():
    doc = copy.deepcopy(FIXTURE)
    i = _index(doc, "f:king-14")
    doc["records"][i] = floats(doc["records"][i], ["start", "end"])
    assert doc["records"][i]["evidence"][1]["selectors"][1]["start"] == 0.0
    _same_verdict(doc, FIXTURE, schema=SCHEMA, doc_texts=TEXTS)
    assert validate(doc, schema=SCHEMA, doc_texts=TEXTS)["ok"]
    shifted = doc["records"][i]["evidence"][1]["selectors"][1]
    shifted["start"], shifted["end"] = 1.0, 42.0  # MC111 with floats
    assert ("KHG-S021", "error", f"/records/{i}/evidence/1") in \
        _found(validate(doc, schema=SCHEMA, doc_texts=TEXTS))


def test_a_hif_file_with_float_role_positions_decodes_and_validates_as_the_int_one():
    doc = floats(HIF, ["role-position"])
    assert any(isinstance(x["attrs"].get("role-position"), float) for x in doc["incidences"])
    _same_verdict(doc, HIF, schema=SCHEMA)
    assert validate(doc, schema=SCHEMA)["ok"]
    decoded = hif.from_hif(doc, SCHEMA)
    assert validate(decoded, schema=SCHEMA)["ok"]


def test_float_versions_in_a_history_container_are_the_same_versions():
    doc = floats(HISTORY, ["version"])
    _same_verdict(doc, HISTORY, schema=SCHEMA)
    assert validate(doc, schema=SCHEMA)["ok"]


def test_a_duplicate_version_written_as_a_float_is_the_same_fault():
    """The reviewer's floats6.py: version 2 of f:king-13 twice, once written as 2.0."""
    i = next(k for k, r in enumerate(HISTORY["records"]) if r.get("id") == "f:king-13" and r.get("version") == 2)
    as_int = copy.deepcopy(HISTORY)
    as_int["records"].insert(i + 1, copy.deepcopy(as_int["records"][i]))
    as_float = copy.deepcopy(as_int)
    as_float["records"][i + 1]["version"] = 2.0
    _same_verdict(as_float, as_int, schema=SCHEMA)
    assert "KHG-D013" not in [c for c, _, _ in _found(validate(as_float, schema=SCHEMA))]


def test_latest_records_reads_float_versions():
    records = floats(HISTORY["records"], ["version"])
    latest = latest_records(records)
    assert latest["f:king-13"]["version"] == 2 and latest["f:reg-1"]["status"] == "retracted"


# ------------------------------------------------------------------------------------------------ b-validate-04


def _float_schema() -> dict[str, Any]:
    doc = floats(SCHEMA_DOC, ["min", "max", "precision_min"])
    assert doc["relations"][0]["roles"][0]["min"] == 1.0 and isinstance(doc["relations"][0]["roles"][0]["min"], float)
    return doc


def test_a_schema_with_float_cardinalities_is_the_schema_with_integers():
    doc = _float_schema()
    assert check_schema(doc) == [] and check_schema(doc, engine="fastjsonschema") == []
    schema = load_schema(doc)
    assert schema == SCHEMA and schema.sha256 == SCHEMA.sha256
    usage = schema.usage("position_held", "holder")
    assert usage == SCHEMA.usage("position_held", "holder") and usage["min"] == 1 and usage["max"] == 1
    assert type(usage["min"]) is int and type(usage["max"]) is int
    assert type(Schema(doc).usage("population", "point_in_time")["fillers"][0]["precision_min"]) is int
    assert doc["relations"][0]["roles"][0]["min"] == 1.0 and isinstance(doc["relations"][0]["roles"][0]["min"],
                                                                         float)  # the caller's document is kept


def _king14() -> dict[str, Any]:
    return copy.deepcopy(next(r for r in FIXTURE["records"] if r["id"] == "f:king-14"))


def _without_position(king: dict[str, Any]) -> dict[str, Any]:
    """f:king-14 without its required position binding (and without its bid in the evidence's supports)."""
    king = copy.deepcopy(king)
    king["bindings"] = [b for b in king["bindings"] if b["role"] != "position"]
    kept = {b["bid"] for b in king["bindings"]}
    for e in king["evidence"]:
        if "supports" in e:
            e["supports"] = [x for x in e["supports"] if x in kept]
    return king


def _s(record: Any, schema: Schema) -> list[tuple[str, str, str]]:
    ents = {r["id"]: r for r in FIXTURE["records"] if r["kind"] == "entity"}
    return [(f["code"], f["severity"], f["path"]) for f in record_findings(record, schema, entities=ents)]


@pytest.mark.parametrize("schema_of", [lambda d: Schema(d), load_schema])
def test_float_cardinalities_still_bind_min_max_and_precision_min(schema_of):
    floaty = schema_of(_float_schema())
    king = _without_position(_king14())
    assert _s(king, floaty) == _s(king, SCHEMA) == [("KHG-S003", "error", "")]
    king = _king14()
    holder = next(b for b in king["bindings"] if b["role"] == "holder")
    king["bindings"].append(dict(copy.deepcopy(holder), bid="b9", value={"entity": "ex:LouisXIII"}))
    assert _s(king, floaty) == _s(king, SCHEMA) == [("KHG-S004", "error", "")]
    pop = copy.deepcopy(next(r for r in FIXTURE["records"] if r["id"] == "f:pop-łódź-2019"))
    b = next(b for b in pop["bindings"] if b["role"] == "point_in_time")
    b["value"]["literal"] = {"datatype": "time", "time": "+2010-00-00T00:00:00Z", "precision": 8,
                             "calendar": "gregorian"}  # MC113
    assert _s(pop, floaty) == _s(pop, SCHEMA) == [("KHG-S023", "error", f"/bindings/{pop['bindings'].index(b)}")]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_float_max_below_a_float_min_is_m010(engine):
    doc = copy.deepcopy(SCHEMA_DOC)
    usage = next(u for r in doc["relations"] if r["id"] == "catalysed_by" for u in r["roles"]
                 if u["role"] == "catalyst")
    usage.update(min=2.0, max=1.0)
    found = [(f["code"], f["path"]) for f in check_schema(doc, engine=engine)]
    usage.update(min=2, max=1)
    assert found == [(f["code"], f["path"]) for f in check_schema(doc, engine=engine)]
    assert [c for c, _ in found] == ["KHG-M010"]


def test_a_container_run_with_a_float_schema_gives_the_int_schemas_verdict():
    doc = copy.deepcopy(FIXTURE)
    i = _index(doc, "f:king-14")
    doc["records"][i] = _without_position(doc["records"][i])
    floaty = _float_schema()
    with_int = run(doc, kind="container", schema=SCHEMA)
    with_float = run(doc, kind="container", schema=floaty)
    assert [(f["code"], f["path"]) for f in with_float.errors] == [(f["code"], f["path"]) for f in with_int.errors]
    assert ("KHG-S003", f"/records/{i}") in [(f["code"], f["path"]) for f in with_float.errors]
