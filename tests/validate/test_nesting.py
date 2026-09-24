"""Review fix b-validate-01, X-04 and b-validate-11: one nesting limit for every input form (DESIGN §8.1, §10.2).

Layer J refuses nesting deeper than ``layers.j.MAX_DEPTH`` levels with J001, whether the input is an object in
memory, bytes or a file, and whatever the caller's stack depth. The limit is within what every later layer (and the
package's recursive walkers: canonical JSON, ``normalize``, ``to_hif``, the store) can process, so ``validate`` never
raises on deep input: at the deepest accepted level every kind runs to the end, and past it the answer is J001.
"""
from __future__ import annotations

import copy
import json
from typing import Any, Callable

import pytest

from khg_contracts import data, hif, record
from khg_contracts.schema import load_schema
from khg_contracts.store import MemoryStore, ScenarioClock
from khg_contracts.validate import layers, run, validate
from khg_contracts.validate.layers import j

ENGINES = ("jsonschema", "fastjsonschema")
SCHEMA_DOC = data.load_json("fixture/fixture.relation-schema.json")
SCHEMA = load_schema(SCHEMA_DOC)
FIXTURE = data.load_json("fixture/fixture.c1.json")
BASES = {"p2-smoke-base": data.load_json("fixture/smoke-base.c1.json")}


def nested(levels: int) -> Any:
    """A value of ``levels`` nested objects (0: a number)."""
    value: Any = 1
    for _ in range(levels):
        value = {"a": value}
    return value


def nested_text(levels: int) -> str:
    """The JSON text of ``nested(levels)``, written without a recursive encoder."""
    return '{"a":' * levels + "1" + "}" * levels


def depth(doc: Any) -> int:
    """The number of nested objects and arrays on the deepest path (a scalar is 0); for the lines of a JSONL file
    (a list of objects), that of the deepest line, since each line is a document of its own."""
    if isinstance(doc, list) and doc and all(isinstance(x, dict) for x in doc):
        return max(depth(x) for x in doc)
    deepest, stack = 0, [(doc, 1)]
    while stack:
        value, d = stack.pop()
        if isinstance(value, dict):
            deepest = max(deepest, d)
            stack.extend((v, d + 1) for v in value.values())
        elif isinstance(value, list):
            deepest = max(deepest, d)
            stack.extend((v, d + 1) for v in value)
    return deepest


# ------------------------------------------------------------------------------------------------ the inputs
# Each builder puts ``nested(levels)`` somewhere a later layer reads: (a) a record with a derived block (layer D
# normalises it), (b) an embedded relation-schema record (layer M through the run's schema), (c) a HIF incidence's
# khg-extensions (decoding), (d) a queue payload (replay), (e) a container (layers C, S, D), (f) a C4 trace (replay).


def _record(levels: int) -> dict[str, Any]:
    doc = data.load_json("fixture/fixture.with-derived.c1.json")
    rec = next(r for r in doc["records"] if r.get("kind") == "hyperedge" and "derived" in r)
    rec["extensions"] = {"ex:deep": nested(levels)}
    return rec


def _embedded_schema(levels: int) -> dict[str, Any]:
    doc = copy.deepcopy(FIXTURE)
    schema = copy.deepcopy(SCHEMA_DOC)
    schema["relations"][0]["label"] = nested(levels)
    doc["records"].insert(0, schema)
    return doc


def _hif(levels: int) -> dict[str, Any]:
    doc = data.load_json("fixture/fixture.hif.json")
    doc["incidences"][0]["attrs"]["khg-extensions"] = {"ex:deep": nested(levels)}
    return doc


def _queue(levels: int) -> list[dict[str, Any]]:
    lines = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    lines[1]["payload"].setdefault("extensions", {})["ex:deep"] = nested(levels)
    return lines


def _container(levels: int) -> dict[str, Any]:
    doc = copy.deepcopy(FIXTURE)
    doc["records"][35].setdefault("extensions", {})["ex:deep"] = nested(levels)
    return doc


def _items(levels: int) -> list[dict[str, Any]]:
    lines = data.load_jsonl("fixture/c4-items.jsonl")
    trace = next(x for x in lines if x["kind"] == "c4-memory-trace")
    put = next(ev for ev in trace["events"] if ev.get("put"))["put"][0]
    put.setdefault("extensions", {})["ex:deep"] = nested(levels)
    return lines


CASES: dict[str, tuple[Callable[[int], Any], str, dict[str, Any]]] = {
    "a-record-with-derived": (_record, "record", {"schema": SCHEMA}),
    "b-embedded-schema": (_embedded_schema, "container", {}),
    "c-hif-incidence": (_hif, "hif", {"schema": SCHEMA}),
    "d-queue-payload": (_queue, "queue", {"schema": SCHEMA, "bases": BASES}),
    "e-container": (_container, "container", {"schema": SCHEMA}),
    "f-c4-trace": (_items, "item", {"schema": SCHEMA}),
}


def deepest_accepted(build: Callable[[int], Any]) -> int:
    """The largest ``levels`` whose input is within ``MAX_DEPTH``."""
    above = depth(build(10)) - 10  # the containers above the nested value
    return j.MAX_DEPTH - above


MARKER = '"__deep__"'


def as_bytes(build: Callable[[int], Any], levels: int) -> bytes:
    """The input as JSON text (JSONL for lines), with the nested value spliced in as text."""
    def mark(x: Any) -> Any:  # the nested value of build(0) is the number 1 under ex:deep or label
        if isinstance(x, dict):
            return {k: ("__deep__" if k in ("ex:deep", "label") and x[k] == 1 else mark(v)) for k, v in x.items()}
        return [mark(v) for v in x] if isinstance(x, list) else x

    marked = mark(build(0))
    text = "\n".join(json.dumps(x, ensure_ascii=False) for x in marked) if isinstance(marked, list) else \
        json.dumps(marked, ensure_ascii=False)
    assert text.count(MARKER) == 1
    return text.replace(MARKER, nested_text(levels)).encode("utf-8")


def _j001(report: Any) -> list[tuple[str, str]]:
    return [(f["code"], f["path"]) for f in report.findings if f["code"] == "KHG-J001"]


# ------------------------------------------------------------------------------------------------ the tests


def test_the_limit_is_well_inside_the_interpreter_limit():
    import sys

    from khg_contracts import jsonio
    assert 2 * j.MAX_DEPTH + 200 < sys.getrecursionlimit()  # two frames a level, and room for the caller
    assert getattr(jsonio, "MAX_DEPTH", j.MAX_DEPTH) == j.MAX_DEPTH  # one limit, where the parser has its own too


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case", sorted(CASES))
def test_the_deepest_accepted_input_runs_every_layer_without_raising(case, engine):
    build, kind, kwargs = CASES[case]
    levels = deepest_accepted(build)
    doc = build(levels)
    assert depth(doc) == j.MAX_DEPTH
    for source in (doc, as_bytes(build, levels)):
        report = run(source, kind=kind, engine=engine, **kwargs)
        assert _j001(report) == [] and report.skipped == [], (case, report.findings[:3], report.skipped)
        assert [name for name, _ in report.steps] == list(layers.PIPELINES[kind]), report.steps


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case", sorted(CASES))
def test_one_level_deeper_is_j001_as_an_object_and_as_text(case, engine):
    build, kind, kwargs = CASES[case]
    levels = deepest_accepted(build) + 1
    for source in (build(levels), as_bytes(build, levels)):
        report = run(source, kind=kind, engine=engine, **kwargs)
        assert [f["code"] for f in report.findings] == ["KHG-J001"] and report.stopped == "j"
        assert f"deeper than {j.MAX_DEPTH} levels" in report.findings[0]["message"]


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case", sorted(CASES))
def test_inputs_nested_500_deep_are_j001_not_a_recursion_error(case, engine):
    """The review's inputs: 500 levels as objects (under the old limit of 512) and 980 as text (under the parser's
    own limit), which used to raise RecursionError out of ``validate``."""
    build, kind, kwargs = CASES[case]
    for source in (build(500), as_bytes(build, 980)):
        result = validate(source, kind=kind, engine=engine, **kwargs)
        assert result["ok"] is False and [f["code"] for f in result["findings"]] == ["KHG-J001"]


def test_the_finding_points_at_the_first_value_too_deep():
    levels = deepest_accepted(_container)
    doc = _container(levels + 1)
    found = validate(doc, schema=SCHEMA)["findings"]
    path = "/records/35/extensions/ex:deep" + "/a" * levels
    assert [(f["code"], f["path"]) for f in found] == [("KHG-J001", path)]
    assert validate(as_bytes(_container, levels + 1), schema=SCHEMA)["findings"] == found


def test_jsonl_lines_are_limited_one_by_one_in_either_form():
    doc = _container(j.MAX_DEPTH)  # deeper than any line may be
    lines = [doc["header"], *doc["records"]]
    text = "\n".join(json.dumps(x, ensure_ascii=False) for x in lines).encode("utf-8")
    as_text = validate(text, kind="container", schema=SCHEMA)["findings"]
    assert [f["code"] for f in as_text] == ["KHG-J001"]
    assert as_text[0]["path"] == "/lines/36/extensions/ex:deep" + "/a" * (j.MAX_DEPTH - 2)
    assert validate(lines, kind="container", schema=SCHEMA)["findings"] == as_text


def test_the_verdict_does_not_depend_on_the_callers_stack():
    """b-validate-11: the text parser's own limit shrinks as the caller's stack grows; J's does not."""
    text = as_bytes(_container, 300)

    def deeper(n: int) -> Any:
        return validate(text, schema=SCHEMA) if n == 0 else deeper(n - 1)

    shallow = validate(text, schema=SCHEMA)
    assert [f["code"] for f in shallow["findings"]] == ["KHG-J001"]
    assert deeper(400) == shallow


def test_a_container_at_the_limit_survives_the_package_walkers():
    """X-04: what the validator accepts, ``to_hif``, ``container_sha256`` and the store process."""
    doc = _container(deepest_accepted(_container))
    assert validate(doc, schema=SCHEMA)["ok"]
    hif.to_hif(doc, SCHEMA)
    assert record.container_sha256(doc).startswith("sha256:")
    store = MemoryStore(SCHEMA, clock=ScenarioClock())
    store.load(doc)
    store.export()


def test_a_recursion_error_in_a_later_step_is_j001_and_stops_the_run(monkeypatch):
    module = layers.module("s")

    def overflow(ctx: Any) -> Any:
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(module, "run", overflow)
    report = run(FIXTURE, kind="container", schema=SCHEMA)
    assert [(f["code"], f["path"]) for f in report.findings] == [("KHG-J001", "")]
    assert "nesting too deep" in report.findings[0]["message"]
    assert report.stopped == "s" and [name for name, _ in report.steps] == ["j", "v", "c", "s"]
    assert report.skipped == [] and report.first_layer == "J"
