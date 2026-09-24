"""Review fixes b-validate-05, F4, b-validate-06 and b-validate-08: what the generated schemas accept and the codes
both engines name (DESIGN §2.1, §4.2, §8.1).

- **End anchors.** jsonschema evaluates ``pattern`` with Python's ``re.search``, where ``$`` also matches before a
  final newline; fastjsonschema rewrites ``$`` to ``\\Z``. The generator therefore ends every pattern with
  ``(?!\\n)$``, which means the end of the string in Python and in ECMA-262 alike, so an id, bid, hash, version,
  decimal or tag that ends in a newline is refused by both engines with one code.
- **A value with an unknown kind** (``{"entitiy": ...}``) is C002 under both engines (jsonschema reads the
  ``propertyNames`` child, fastjsonschema the parent).
- **The khg-* edge attributes** of the profile have their shapes, so a malformed one is P012 at the edge
  (§4.2 lists them; the registry's P012 is "a malformed khg-* edge attribute"), not a C code in the decoded container.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Callable

import pytest

from khg_contracts import data, hif
from khg_contracts.errors import ValidationError
from khg_contracts.schema import check_schema, codegen, load_schema
from khg_contracts.validate import run, validate
from khg_contracts.validate.runner import Report

ENGINES = ("jsonschema", "fastjsonschema")
SCHEMA_DOC = data.load_json("fixture/fixture.relation-schema.json")
SCHEMA = load_schema(SCHEMA_DOC)
FIXTURE = data.load_json("fixture/fixture.c1.json")
HIF = data.load_json("fixture/fixture.hif.json")
ITEMS = data.load_jsonl("fixture/c4-items.jsonl")


def _rec(doc: dict[str, Any], rid: str) -> tuple[int, dict[str, Any]]:
    return next((i, r) for i, r in enumerate(doc["records"]) if r.get("id") == rid)


def _errors(report: Report) -> list[tuple[str, str]]:
    return [(f["code"], f["path"]) for f in report.errors]


# ------------------------------------------------------------------------------------------------ b-validate-05, F4


def test_every_generated_pattern_ends_at_the_end_of_the_string():
    checked = 0
    for name, schema in codegen.build_all().items():  # the C5 schema has none of its own
        for p in codegen.patterns(schema):
            checked += 1
            assert not p.endswith("$") or p.endswith(codegen.END), (name, p)
    assert checked > 30 and codegen.END == "(?!\\n)$"


def _c1(mutate: Callable[[dict[str, Any]], str]) -> tuple[dict[str, Any], str]:
    doc = copy.deepcopy(FIXTURE)
    return doc, mutate(doc)


def _document_id(doc: dict[str, Any]) -> str:
    doc["header"]["document_id"] += "\n"
    return "/header/document_id"


def _entity_id(doc: dict[str, Any]) -> str:
    i, r = _rec(doc, "ex:Mazarin")  # the isolated entity: no value names it
    r["id"] += "\n"
    return f"/records/{i}/id"


def _amount(doc: dict[str, Any]) -> str:
    i, r = _rec(doc, "f:pop-łódź-2019")
    j = next(j for j, b in enumerate(r["bindings"]) if b["role"] == "quantity")
    r["bindings"][j]["value"]["literal"]["amount"] += "\n"
    return f"/records/{i}/bindings/{j}/value/literal/amount"


def _lang(doc: dict[str, Any]) -> str:
    i, r = _rec(doc, "f:station-東京")
    j = next(j for j, b in enumerate(r["bindings"]) if b["bid"] == "b2")
    r["bindings"][j]["value"]["literal"]["lang"] += "\n"
    return f"/records/{i}/bindings/{j}/value/literal/lang"


def _iri(doc: dict[str, Any]) -> str:
    i, r = _rec(doc, "f:station-東京")
    j = next(j for j, b in enumerate(r["bindings"]) if b["role"] == "homepage")
    r["bindings"][j]["value"]["literal"]["value"] += "\n"
    return f"/records/{i}/bindings/{j}/value/literal/value"


def _doc_sha256(doc: dict[str, Any]) -> str:
    i, r = _rec(doc, "f:king-14")
    r["evidence"][1]["source"]["doc_sha256"] += "\n"
    return f"/records/{i}/evidence/1/source/doc_sha256"


def _evidence_id(doc: dict[str, Any]) -> str:
    i, r = _rec(doc, "f:reg-1")
    r["evidence"][0]["id"] += "\n"
    return f"/records/{i}/evidence/0/id"


def _schema_version(doc: dict[str, Any]) -> str:
    doc["header"]["schema"]["version"] += "\n"
    return "/header/schema/version"


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize(("mutate", "code"), [
    (_document_id, "KHG-C011"), (_entity_id, "KHG-C011"), (_amount, "KHG-C004"), (_lang, "KHG-C004"),
    (_iri, "KHG-C004"), (_doc_sha256, "KHG-C011"), (_evidence_id, "KHG-C011"), (_schema_version, "KHG-C011"),
], ids=lambda x: getattr(x, "__name__", x))
def test_a_trailing_newline_is_refused_by_both_engines_in_a_container(mutate, code, engine):
    doc, path = _c1(mutate)
    report = run(doc, kind="container", schema=SCHEMA, engine=engine)
    assert report.first_layer == "C"
    assert [(f["code"], f["path"]) for f in dict(report.steps)["c"]] == [(code, path)]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_bid_with_a_trailing_newline_is_c011_first(engine):
    doc = copy.deepcopy(FIXTURE)
    i, r = _rec(doc, "f:reg-1")
    r["bindings"][0]["bid"] = "b1\n"
    report = run(doc, kind="container", schema=SCHEMA, engine=engine)
    assert report.first_layer == "C"
    assert ("KHG-C011", f"/records/{i}/bindings/0/bid") in _errors(report)


@pytest.mark.parametrize("engine", ENGINES)
def test_a_schema_version_or_role_with_a_trailing_newline_is_refused(engine):
    doc = copy.deepcopy(SCHEMA_DOC)
    doc["version"] = "1.0.0\n"
    assert [(f["code"], f["path"]) for f in check_schema(doc, engine=engine)] == [("KHG-M004", "/version")]
    with pytest.raises(ValidationError) as exc:
        load_schema(doc)
    assert exc.value.codes == ("KHG-M004",)
    doc = copy.deepcopy(SCHEMA_DOC)
    doc["roles"][0]["id"] += "\n"
    assert "KHG-M015" in [f["code"] for f in check_schema(doc, engine=engine)]


@pytest.mark.parametrize("engine", ENGINES)
def test_a_hif_node_id_with_a_trailing_newline_is_p003(engine):
    """F4: the profile's id grammar under the default engine."""
    doc = copy.deepcopy(HIF)
    k = next(k for k, n in enumerate(doc["nodes"]) if n["node"] == "ex:Paris")
    doc["nodes"][k]["node"] = "ex:Paris\n"
    for inc in doc["incidences"]:
        if inc["node"] == "ex:Paris":
            inc["node"] = "ex:Paris\n"
    report = run(doc, kind="hif", schema=SCHEMA, engine=engine)
    assert report.first_layer == "P" and ("KHG-P003", f"/nodes/{k}/node") in _errors(report)
    with pytest.raises(ValidationError) as exc:
        hif.from_hif(doc, SCHEMA)
    assert "KHG-P003" in exc.value.codes


@pytest.mark.parametrize("engine", ENGINES)
def test_a_khg_bid_with_a_trailing_newline_is_p005_first(engine):
    doc = copy.deepcopy(HIF)
    n = next(n for n, x in enumerate(doc["incidences"]) if x["edge"] == "f:reg-1" and x["attrs"]["khg-bid"] == "b1")
    doc["incidences"][n]["attrs"]["khg-bid"] = "b1\n"
    report = run(doc, kind="hif", schema=SCHEMA, engine=engine)
    assert report.first_layer == "P"
    assert ("KHG-P005", f"/incidences/{n}/attrs/khg-bid") in _errors(report)


@pytest.mark.parametrize("engine", ENGINES)
def test_a_c4_qid_with_a_trailing_newline_is_i003(engine):
    lines = copy.deepcopy(ITEMS)
    n = next(n for n, x in enumerate(lines) if x["kind"] == "c4-memory-question")
    lines[n]["qid"] += "\n"
    report = run(lines, kind="item", schema=SCHEMA, engine=engine)
    assert report.first_layer == "I" and ("KHG-I003", f"/lines/{n}/qid") in _errors(report)


@pytest.mark.parametrize("engine", ENGINES)
def test_a_queue_qid_with_a_trailing_newline_is_q008(engine):
    """The queue schema is generated by ``queue.codegen``; the jsonschema registry reads its patterns with the same
    end anchor."""
    lines = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    qid = lines[1]["qid"]
    for line in lines[1:]:
        for key in ("qid", "target"):
            if line.get(key) == qid:
                line[key] = qid + "\n"
    report = run(lines, kind="queue", schema=SCHEMA, bases=[data.load_json("fixture/smoke-base.c1.json")],
                 engine=engine)
    assert report.first_layer == "Q" and ("KHG-Q008", "/lines/1/qid") in _errors(report)


def test_the_jsonschema_registry_reads_every_packaged_pattern_to_the_end_of_the_string():
    from khg_contracts.validate import engines

    for sid, doc in data.schema_documents().items():
        for p in codegen.patterns(engines._end_anchored(doc)):
            assert not p.endswith("$") or p.endswith(codegen.END), (sid, p)
        if sid != engines.TAG + "khg-queue/1.0.0":
            assert engines._end_anchored(doc) == doc, sid  # the generated files already end so


def test_the_anchor_keeps_every_valid_value_valid():
    """The anchored patterns accept what the plain ones accepted without a trailing newline (the packaged files
    already pass test_engines; this checks the rewrite itself on a few values)."""
    for pattern, good in (("^b[1-9][0-9]*$", "b12"), ("^(?!_:)[^\\s\\x00-\\x1f\\x7f]{1,512}$", "ex:東京駅"),
                          ("^(1|(?!_:)[^\\s\\x00-\\x1f\\x7f]{1,512})$", "1")):
        anchored = codegen.anchor(pattern)
        assert anchored.endswith(codegen.END)
        assert re.search(anchored, good) and not re.search(anchored, good + "\n")
        assert re.search(pattern, good + "\n")  # what the plain pattern let through in Python
    assert codegen.anchor("^khg:") == "^khg:" and codegen.anchor("^a\\$") == "^a\\$"
    assert codegen.anchor(codegen.anchor("^a$")) == codegen.anchor("^a$")


# ------------------------------------------------------------------------------------------------ b-validate-06


@pytest.mark.parametrize("engine", ENGINES)
def test_a_value_of_an_unknown_kind_is_c002_under_both_engines(engine):
    doc = copy.deepcopy(FIXTURE)
    i, r = _rec(doc, "f:reg-1")
    r["bindings"][0]["value"] = {"entitiy": "ex:HeLa"}
    report = run(doc, kind="container", schema=SCHEMA, engine=engine)
    assert report.first_layer == "C"
    assert [(f["code"], f["path"]) for f in dict(report.steps)["c"]] == \
        [("KHG-C002", f"/records/{i}/bindings/0/value")]


# ------------------------------------------------------------------------------------------------ b-validate-08

EDGE = next(k for k, e in enumerate(HIF["edges"]) if e["edge"] == "f:reg-1")


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize(("key", "value"), [
    ("khg-rank", "top"), ("khg-visibility", 3), ("khg-confidence", 0.9), ("khg-confidence", {"value": 0.9}),
    ("khg-status-ref", 7), ("khg-status-ref", "m:ret 1"), ("khg-typed-under", "x y"), ("khg-evidence", {}),
    ("khg-evidence", "none"), ("khg-evidence", [3]), ("khg-rank-reason", []), ("khg-rank-reason", ["a b"]),
    ("khg-goal", "find it"), ("khg-goal", {"owner": "x"}), ("khg-version", 0), ("khg-version", "2"),
    ("khg-recorded-at", "yesterday"), ("khg-recorded-by", ""), ("khg-reason", 5), ("khg-note", 5),
    ("khg-source-text", ["x"]), ("khg-extensions", {"no namespace": 1}), ("khg-extensions", []),
])
def test_a_malformed_khg_edge_attribute_is_p012_at_the_edge(key, value, engine):
    doc = copy.deepcopy(HIF)
    doc["edges"][EDGE]["attrs"][key] = value
    report = run(doc, kind="hif", schema=SCHEMA, engine=engine)
    assert report.first_layer == "P", report.findings
    step = dict(report.steps)["p"]
    assert step and all(f["code"] == "KHG-P012" for f in step)
    assert all(f["path"].startswith(f"/edges/{EDGE}/attrs/{key}") for f in step), step
    with pytest.raises(ValidationError) as exc:
        hif.from_hif(doc, SCHEMA)
    assert "KHG-P012" in exc.value.codes


@pytest.mark.parametrize("engine", ENGINES)
def test_well_formed_khg_edge_attributes_pass_the_profile(engine):
    """Every attribute §4.2 lists, well formed, passes layer P (the packaged HIF files pass it: test_engines)."""
    assert validate(HIF, schema=SCHEMA, engine=engine)["ok"]
    doc = copy.deepcopy(HIF)
    doc["edges"][EDGE]["attrs"].update({
        "khg-confidence": {"value": 0.9, "scale": "probability", "scorer": {"name": "s", "version": "1"}},
        "khg-source-text": "TP53 regulates itself in HeLa cells.", "khg-note": "a note",
        "khg-typed-under": "p2-gate/1.0.0", "khg-version": 1, "khg-recorded-at": "2026-09-01T00:00:00Z",
        "khg-recorded-by": "curator:a"})
    assert [f for f in run(doc, kind="hif", schema=SCHEMA, engine=engine).findings if f["layer"] == "P"] == []


# ------------------------------------------------------------------------------------------------ ruling 7 (§14)


def _question(mutate: Callable[[dict[str, Any]], Any]) -> tuple[list[dict[str, Any]], int]:
    lines = copy.deepcopy(ITEMS)
    n = next(n for n, x in enumerate(lines) if x["kind"] == "c4-memory-question")
    mutate(lines[n])
    return lines, n


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize(("mutate", "code"), [
    (lambda q: q.pop("stale_values"), "KHG-I004"),
    (lambda q: q.pop("future_values"), "KHG-I004"),
    (lambda q: q.pop("text"), "KHG-I002"),
    (lambda q: q.pop("answerable"), "KHG-I002"),
    (lambda q: q["key"][0].pop("role"), "KHG-I002"),
    (lambda q: q.update(stale_values="none"), "KHG-I002"),
    (lambda q: q.update(future_values={}), "KHG-I002"),
    (lambda q: q.update(stale_values=[{"value": {"entity": "ex:LouisXIII"}}]), "KHG-I002"),
], ids=["no-stale", "no-future", "no-text", "no-answerable", "key-without-role", "stale-not-array",
        "future-not-array", "stale-without-kind"])
def test_i004_is_only_a_memory_question_without_stale_or_future_values(mutate, code, engine):
    """Ruling 7: I004 means only a memory question without ``stale_values`` or ``future_values``; any other missing
    required field, or a malformed one, is the draft structure's I002."""
    lines, n = _question(mutate)
    report = run(lines, kind="item", schema=SCHEMA, engine=engine)
    assert report.first_layer == "I"
    step = [(f["code"], f["path"]) for f in dict(report.steps)["i"] if f["severity"] == "error"]
    assert step and {c for c, _ in step} == {code}, step


# ------------------------------------------------------------------------------------------------ year digits
# Review integration (group ad's request 5): the packaged record schema bounds the digits of a year as
# ``record.windows`` does. A time literal's year has 4 to 16 digits (Wikibase's bound; C004), an instant's 4 to 17
# (C011; one more, for the upper window bound of the largest literal year). Layer C reports a longer year; before,
# only the S step's time parse did.


def test_the_record_schema_bounds_a_year_as_record_windows_does():
    from khg_contracts.record import windows

    assert (codegen.YEAR_DIGITS, codegen.INSTANT_YEAR_DIGITS) == (windows.YEAR_DIGITS, windows.INSTANT_YEAR_DIGITS)
    found = list(codegen.patterns(data.load_json("schemas/khg-record-1.0.0.schema.json")))
    assert codegen.anchor(codegen.TIME_PATTERN) in found and codegen.anchor(codegen.INSTANT_PATTERN) in found
    assert not [p for p in found if "{4,}" in p]
    for digits, ok in ((4, True), (16, True), (17, False)):
        text = "+" + "1" * digits + "-00-00T00:00:00Z"
        assert bool(re.search(codegen.anchor(codegen.TIME_PATTERN), text)) is ok
    for digits, ok in ((4, True), (17, True), (18, False)):
        text = "-" + "1" * digits + "-01-01T00:00:00Z"
        assert bool(re.search(codegen.anchor(codegen.INSTANT_PATTERN), text)) is ok


@pytest.mark.parametrize("engine", ENGINES)
def test_a_literal_year_beyond_16_digits_is_c004_from_layer_c(engine):
    doc = copy.deepcopy(FIXTURE)
    i, r = _rec(doc, "f:king-14")
    j = next(j for j, b in enumerate(r["bindings"]) if b["role"] == "end_time")
    lit = r["bindings"][j]["value"]["literal"]
    lit.update(time="+" + "9" * 16 + "-00-00T00:00:00Z", precision=9)
    assert dict(run(doc, schema=SCHEMA, engine=engine).steps)["c"] == []
    for digits in (17, 4301):
        lit["time"] = "+" + "1" * digits + "-00-00T00:00:00Z"
        report = run(doc, schema=SCHEMA, engine=engine)
        at = f"/records/{i}/bindings/{j}/value/literal"
        assert [(f["code"], f["path"]) for f in dict(report.steps)["c"]] == [("KHG-C004", f"{at}/time")]
        assert report.first_layer == "C" and ("KHG-C004", at) in _errors(report)  # the S step's time parse agrees


@pytest.mark.parametrize("engine", ENGINES)
def test_an_as_of_year_beyond_17_digits_is_refused_by_the_item_structure(engine):
    """A C4 ``where.as_of`` is the record schema's instant: an 18-digit year is the item structure's I002 at the
    field, as any other malformed ``as_of`` is (it was I003 from the replay, with C011 nested)."""
    lines, n = _question(lambda q: q["where"].update(as_of="+" + "1" * 18 + "-01-01T00:00:00Z"))
    report = run(lines, kind="item", schema=SCHEMA, engine=engine)
    assert report.first_layer == "I" and ("KHG-I002", f"/lines/{n}/where/as_of") in _errors(report)
    lines[n]["where"]["as_of"] = "+" + "1" * 17 + "-01-01T00:00:00Z"
    assert f"/lines/{n}/where/as_of" not in [p for _, p in _errors(run(lines, kind="item", schema=SCHEMA,
                                                                          engine=engine))]
