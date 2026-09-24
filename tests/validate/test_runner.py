"""W4: the layer runner, the layer rule and the ``validate`` API (DESIGN §8.1, §10.2)."""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
from collections import OrderedDict

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError, make_finding
from khg_contracts.schema import load_schema
from khg_contracts.validate import (first_rejecting_layer, layers, run, validate, validate_container, validate_hif,
                                    validate_item, validate_queue, validate_record)

SCHEMA = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
FIXTURE = data.load_json("fixture/fixture.c1.json")
KING14 = next(r for r in FIXTURE["records"] if r.get("id") == "f:king-14")


def _codes(result):
    return [f["code"] for f in result["findings"] if f["severity"] == "error"]


def _record(rid):
    return copy.deepcopy(next(r for r in FIXTURE["records"] if r.get("id") == rid))


# ------------------------------------------------------------------------------------------------ the layer rule


def test_the_first_rejecting_layer_follows_the_pipeline_order_not_the_step():
    f = make_finding
    decoding = [f("KHG-S016", "/incidences/3"), f("KHG-D016", "")]
    assert first_rejecting_layer(decoding, "hif") == "D"  # D precedes S in J V H R P D C S
    assert first_rejecting_layer(decoding, "container") == "S"  # S precedes D in J V C S D
    assert first_rejecting_layer([f("KHG-S004", ""), f("KHG-C009", "")], "c1") == "C"
    assert first_rejecting_layer([f("KHG-S024", "", severity="warning")], "container") is None
    assert first_rejecting_layer([f("KHG-L008", "", severity="warning"), f("KHG-D016", "")], "container") == "D"
    assert first_rejecting_layer([], "hif") is None


def test_letters_outside_the_pipeline_rank_after_it_in_registry_order():
    f = make_finding
    assert first_rejecting_layer([f("KHG-M003", "/records/0"), f("KHG-D002", "")], "container") == "D"
    assert first_rejecting_layer([f("KHG-M003", "/records/0"), f("KHG-I002", "")], "container") == "M"
    assert first_rejecting_layer([f("KHG-Q001", ""), f("KHG-J003", "")], "json") == "J"


# ------------------------------------------------------------------------------------------------ the result


def test_validate_returns_ok_and_findings_only():
    result = validate(data.path("fixture/fixture.c1.json"), schema=SCHEMA)
    assert set(result) == {"ok", "findings"} and result["ok"] is True
    for finding in result["findings"]:
        assert set(finding) == {"code", "severity", "layer", "path", "message"}
        assert finding["layer"] == finding["code"][4]


def test_the_report_keeps_each_steps_findings():
    bad = copy.deepcopy(FIXTURE)
    bad["records"][35]["status"] = "believed"  # C002 on f:reg-1
    bad["records"][35]["bindings"][0]["role"] = "tissue"  # S002
    report = run(bad, kind="container", schema=SCHEMA)
    assert [name for name, _ in report.steps] == ["j", "v", "c", "s", "d_container"]
    assert {name: [f["code"] for f in found if f["severity"] == "error"] for name, found in report.steps} == \
        {"j": [], "v": [], "c": ["KHG-C002"], "s": ["KHG-S002"], "d_container": []}
    assert report.first_layer == "C" and report.first_rejecting_step == "c"
    assert [f["code"] for f in report.until_first_rejection()] == ["KHG-C002"]
    first = run(bad, kind="container", schema=SCHEMA, stop="first")
    assert first.stopped == "c" and first.findings == report.until_first_rejection()


def test_j_and_v_stop_the_run():
    bad = copy.deepcopy(FIXTURE)
    bad["header"]["format"] = "khg-record/1.1.0"  # a minor newer than the reader
    bad["records"][35]["status"] = "believed"
    report = run(bad, kind="container", schema=SCHEMA)
    assert [f["code"] for f in report.findings] == ["KHG-V001"] and report.stopped == "v"
    assert [name for name, _ in report.steps] == ["j", "v"]
    report = run(b'{"header": {}, "records": [}', kind="container")
    assert [f["code"] for f in report.findings] == ["KHG-J001"] and report.stopped == "j"


def test_steps_restrict_the_run_and_j_always_runs():
    report = run(FIXTURE, kind="container", schema=SCHEMA, steps=("v",))
    assert [name for name, _ in report.steps] == ["j", "v"]
    with pytest.raises(ValueError):
        run(FIXTURE, kind="container", steps=("x",))


# ------------------------------------------------------------------------------------------------ layer J


@pytest.mark.parametrize(("value", "code", "path"), [
    (math.nan, "KHG-J004", "/records/0/extensions/ex:w"),
    (math.inf, "KHG-J004", "/records/0/extensions/ex:w"),
    ("\ud800", "KHG-J005", "/records/0/extensions/ex:w"),
    (2 ** 53, "KHG-J006", "/records/0/extensions/ex:w"),
    ({1, 2}, "KHG-J001", "/records/0/extensions/ex:w"),
    (object(), "KHG-J001", "/records/0/extensions/ex:w"),
    ({3: "x"}, "KHG-J001", "/records/0/extensions/ex:w"),
])
def test_layer_j_checks_objects_in_memory(value, code, path):
    doc = copy.deepcopy(FIXTURE)
    doc["records"][0]["extensions"] = {"ex:w": value}
    result = validate(doc, schema=SCHEMA)
    assert [(f["code"], f["path"]) for f in result["findings"]] == [(code, path)]


def test_layer_j_refuses_a_top_level_that_is_not_an_object_and_deep_or_cyclic_nesting():
    assert _codes(validate([1, 2], kind="record")) == ["KHG-J007"]
    assert _codes(validate(42)) == ["KHG-J007"] and _codes(validate(None, kind="schema")) == ["KHG-J007"]
    assert [(f["code"], f["path"]) for f in validate([{"kind": "header"}, 3], kind="queue")["findings"]] == \
        [("KHG-J007", "/lines/1")]
    deep: dict = {}
    node = deep
    for _ in range(600):
        node["x"] = {}
        node = node["x"]
    assert _codes(validate(deep, kind="record")) == ["KHG-J001"]
    cyclic: dict = {"kind": "entity"}
    cyclic["self"] = cyclic
    assert _codes(validate(cyclic, kind="record")) == ["KHG-J001"]
    assert _codes(validate([], kind="queue")) == ["KHG-J001"]


def test_tuples_and_other_mappings_are_read_as_json():
    doc = copy.deepcopy(FIXTURE)
    doc["records"][0] = OrderedDict(doc["records"][0])
    doc["records"][0]["types"] = tuple(doc["records"][0]["types"])
    report = run(doc, kind="container", schema=SCHEMA)
    assert report.ok and [f["code"] for f in report.findings] == ["KHG-S024", "KHG-L008"]  # the designed warnings
    assert isinstance(doc["records"][0]["types"], tuple)  # the caller's object is not changed


@pytest.mark.parametrize(("text", "code"), [
    (b"", "KHG-J001"), (b"\xef\xbb\xbf{}", "KHG-J002"), (b'{"a": 1, "a": 2}', "KHG-J003"),
    (b'{"a": NaN}', "KHG-J004"), (b'{"a": "\\ud800"}', "KHG-J005"), (b'{"a": 9007199254740993}', "KHG-J006"),
    (b"[]", "KHG-J007"), (b"\xff", "KHG-J002"),
])
def test_layer_j_parses_bytes_strictly(text, code):
    assert _codes(validate(text)) == [code]


def test_a_text_with_several_values_is_read_as_jsonl():
    lines = data.read_bytes("fixture/fixture.c1.jsonl")
    report = run(lines, schema=SCHEMA)
    assert report.kind == "container" and report.ok
    assert [f["code"] for f in report.findings] == ["KHG-S024", "KHG-L008"]  # the designed warnings
    bad = lines.replace(b'"status":"asserted"', b'"status":asserted', 1)
    found = validate(bad, schema=SCHEMA)["findings"]
    assert [f["code"] for f in found] == ["KHG-J001"] and found[0]["path"].startswith("/lines/")


def test_an_unreadable_path_raises_but_a_bad_file_does_not(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate(str(tmp_path / "missing.khg.json"))
    p = tmp_path / "bad.khg.json"
    p.write_bytes(b'{"header": {"kind": "header"}, "records": [], "records": []}')
    assert _codes(validate(p)) == ["KHG-J003"]


# ------------------------------------------------------------------------------------------------ kinds


@pytest.mark.parametrize(("rel", "kind"), [
    ("fixture/fixture.c1.json", "container"), ("fixture/fixture.c1.jsonl", "container"),
    ("fixture/fixture.hif.json", "hif"), ("role-convention/ordered.hif.json", "role-convention"),
    ("fixture/fixture.relation-schema.json", "schema"), ("fixture/smoke-queue.khg-queue.jsonl", "queue"),
    ("fixture/c4-items.jsonl", "item"), ("sample/sample.khg.hif.json", "hif"),
])
def test_auto_picks_the_kind_of_a_file(rel, kind):
    assert run(data.path(rel), schema=SCHEMA).kind == kind


def test_auto_picks_the_kind_of_an_object():
    assert run(KING14, schema=SCHEMA).kind == "record"
    assert run(data.load_json("fixture/fixture.relation-schema.json")).kind == "schema"
    assert run(SCHEMA, kind="schema").ok  # a Schema is read as its document
    assert run({"incidences": []}).kind == "hif"
    assert run({"incidences": [], "metadata": {"role-convention": "1.0.0"}}).kind == "role-convention"
    assert run(data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl"), schema=SCHEMA).kind == "queue"
    lines = [FIXTURE["header"], *FIXTURE["records"]]
    report = run(lines, schema=SCHEMA)
    assert report.kind == "container" and [f["path"] for f in report.findings] == ["/records/31", "/records/29"]


@pytest.mark.parametrize(("rel", "kind"), [("fixture/smoke-queue.khg-queue.jsonl", "queue"),
                                           ("fixture/c4-items.jsonl", "item"),
                                           ("fixture/fixture.c1.jsonl", "container")])
def test_auto_reads_a_lone_header_line_as_a_file_of_one_line(rel, kind):
    """b-validate-12: a JSONL file of its header line only (a fresh queue, as ``Queue.create`` writes it) parses to
    one object; auto reads it as the file it is, as the explicit kinds do."""
    header = data.load_jsonl(rel)[0]
    bases = [data.load_json("fixture/smoke-base.c1.json")]  # the queue header names it
    for source in (header, (json.dumps(header, ensure_ascii=False) + "\n").encode("utf-8"), [header]):
        report = run(source, schema=SCHEMA, bases=bases)
        assert report.kind == kind and report.ok, (source, report.findings)
        assert report.findings == run([header], kind=kind, schema=SCHEMA, bases=bases).findings


def test_auto_tells_a_lone_header_from_other_objects():
    assert run({"incidences": [], "kind": ["header"]}).kind == "hif"  # an unhashable kind is not a header's
    doc = dict(copy.deepcopy(FIXTURE), kind="header")  # a container object, whatever else it carries
    report = run(doc, schema=SCHEMA)
    assert report.kind == "container" and [f["code"] for f in report.errors] == ["KHG-C009"]


@pytest.mark.parametrize("obj", [{"a": 1}, {"kind": "claim"}, [{"kind": "line"}], {"records": []}])
def test_auto_reports_v001_when_it_cannot_tell_the_kind(obj):
    report = run(obj)
    assert report.kind is None and report.stopped == "v"
    assert [(f["code"], f["layer"]) for f in report.findings] == [("KHG-V001", "V")]
    assert report.first_layer == "V"


@pytest.mark.parametrize(("kind", "patch", "path"), [
    ("container", {"header": {"format": "khg-record/2.0.0"}}, "/header/format"),
    ("container", {"header": {"format": "khg-record/1.0"}}, "/header/format"),
    ("hif", {"metadata": {"khg-profile": "khg-hif/1.9.0"}}, "/metadata/khg-profile"),
    ("hif", {"metadata": {"khg-profile": "khg-hif/1.0.0", "khg-record": "khg-record/2.1.0"}}, "/metadata/khg-record"),
    ("schema", {"format": "khg-relation-schema/1.1.0"}, "/format"),
])
def test_layer_v_gates_each_format(kind, patch, path):
    base = {"container": FIXTURE, "hif": data.load_json("fixture/fixture.hif.json"),
            "schema": data.load_json("fixture/fixture.relation-schema.json")}[kind]
    doc = copy.deepcopy(base)
    for key, value in patch.items():
        doc[key].update(value) if isinstance(value, dict) else doc.update({key: value})
    report = run(doc, kind=kind, schema=SCHEMA if kind != "schema" else None)
    assert [(f["code"], f["path"]) for f in report.findings] == [("KHG-V001", path)]


def test_layer_v_gates_queue_and_c4_headers():
    queue = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    queue[0]["format"] = "khg-queue/2.0.0"
    assert [(f["code"], f["path"]) for f in validate_queue(queue, schema=SCHEMA)["findings"]] == \
        [("KHG-V001", "/lines/0/format")]
    items = data.load_jsonl("fixture/c4-items.jsonl")
    items[0]["format"] = "khg-c4-items/0.2.0"
    assert _codes(validate_item(items, schema=SCHEMA)) == ["KHG-V001"]
    items[0]["format"] = "khg-c4-items/0.1.7"
    assert validate_item(items, schema=SCHEMA)["ok"]


@pytest.mark.parametrize("engine", ["jsonschema", "fastjsonschema"])
@pytest.mark.parametrize("stamp", ["khg-record/1.1.0", "khg-record/2.0.0", "khg-record/1.0", "khg-hif/1.0.0", 7])
def test_layer_v_gates_the_record_format_of_a_queue_header(stamp, engine):
    """Review integration (group ex's request, §8.1, §11.2): a queue header's ``record_format`` that this reader does
    not accept is V001 from step v, and the run stops there. It came from the Q step, and C, S and D ran after it."""
    queue = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    base = data.load_json("fixture/smoke-base.c1.json")
    queue[0]["record_format"] = stamp
    report = run(queue, kind="queue", schema=SCHEMA, bases=[base], engine=engine)
    assert [(f["code"], f["path"]) for f in report.findings] == [("KHG-V001", "/lines/0/record_format")]
    assert report.stopped == "v" and report.first_rejecting_step == "v" and report.first_layer == "V"
    assert [name for name, _ in report.steps] == ["j", "v"]
    queue[0]["record_format"] = "khg-record/1.0.9"  # another patch is read
    assert run(queue, kind="queue", schema=SCHEMA, bases=[base], engine=engine).ok


def test_a_hif_file_without_khg_profile_passes_v():
    hif = data.load_json("role-convention/basic.hif.json")
    report = run(hif, kind="hif", schema=SCHEMA)
    assert [f for f in report.findings if f["layer"] == "V"] == []
    assert [name for name, _ in report.steps][:3] == ["j", "v", "h"]


def test_the_wrappers_fix_the_kind():
    assert validate_record(KING14, schema=SCHEMA) == {"ok": True, "findings": []}
    assert _codes(validate_record(FIXTURE, schema=SCHEMA)) == ["KHG-C010"]  # a container is not a record
    assert validate_container(data.path("fixture/fixture.c1.jsonl"), schema=SCHEMA)["ok"]
    assert validate_hif(data.path("fixture/fixture.hif.json"), schema=SCHEMA)["ok"]
    assert validate_queue(data.path("fixture/smoke-queue.khg-queue.jsonl"), schema=SCHEMA,
                          bases=[data.path("fixture/smoke-base.c1.json")])["ok"]
    assert validate_item(data.path("fixture/c4-items.jsonl"), schema=SCHEMA)["ok"]
    with pytest.raises(TypeError):
        validate_queue(data.path("fixture/smoke-queue.khg-queue.jsonl"))  # type: ignore[call-arg]


# ------------------------------------------------------------------------------------------------ arguments


def test_the_schema_argument_is_a_schema_a_document_or_a_path(examples_dir):
    for schema in (SCHEMA, data.load_json("fixture/fixture.relation-schema.json"),
                   examples_dir / "fixture.relation-schema.json", str(examples_dir / "fixture.relation-schema.json"),
                   data.path("fixture/fixture.relation-schema.json")):
        assert validate_record(KING14, schema=schema) == {"ok": True, "findings": []}
    bad = data.load_json("fixture/fixture.relation-schema.json")
    bad["version"] = "1.0"
    with pytest.raises(ValidationError) as exc:
        validate_record(KING14, schema=bad)
    assert exc.value.codes == ("KHG-M004",)


def test_doc_texts_are_a_mapping_a_doc_texts_document_or_a_path(examples_dir):
    doc = copy.deepcopy(FIXTURE)
    evidence = doc["records"][30]["evidence"][1]  # f:king-14 e2, doc:louis-bio
    evidence["selectors"][1]["start"] = 1
    texts = data.load_json("fixture/fixture.doc-texts.json")
    flat = {k: v["text"] for k, v in texts["texts"].items()}
    for doc_texts in (texts, flat, data.path("fixture/fixture.doc-texts.json"),
                      str(examples_dir / "fixture.doc-texts.json")):
        assert "KHG-S021" in _codes(validate(doc, schema=SCHEMA, doc_texts=doc_texts))
    assert validate(doc, schema=SCHEMA)["ok"]  # no text, no span check
    with pytest.raises(TypeError):
        validate(doc, schema=SCHEMA, doc_texts=["doc:louis-bio"])


def test_bases_are_a_mapping_a_container_or_an_iterable():
    queue = data.path("fixture/smoke-queue.khg-queue.jsonl")
    base = data.load_json("fixture/smoke-base.c1.json")
    for bases in ({"p2-smoke-base": base}, base, [base], [data.path("fixture/smoke-base.c1.json")],
                  data.path("fixture/smoke-base.c1.json"), {"p2-smoke-base": data.path("fixture/smoke-base.c1.json")}):
        report = run(queue, kind="queue", schema=SCHEMA, bases=bases)
        assert report.ok
    with pytest.raises(TypeError):
        run(queue, kind="queue", schema=SCHEMA, bases=[42])


@pytest.mark.parametrize("name", ["base.txt", "base.c1", "base.JSON"])
def test_a_base_path_whose_suffix_is_not_a_containers_is_a_value_error(tmp_path, name):
    """Review integration (group ad's request; ruling 4): ``record.read_container`` reads ``.json`` and ``.jsonl``
    only, so a base path with another suffix is ``ValueError``, as ``run``'s docstring now says; it is an argument
    error, not a finding (not ``ValidationError``, which is also a ``ValueError``)."""
    queue = data.path("fixture/smoke-queue.khg-queue.jsonl")
    base = tmp_path / name
    base.write_bytes(data.read_bytes("fixture/smoke-base.c1.json"))
    with pytest.raises(ValueError) as exc:
        run(queue, kind="queue", schema=SCHEMA, bases=[base])
    assert not isinstance(exc.value, ValidationError)
    renamed = base.rename(tmp_path / "base.json")
    assert run(queue, kind="queue", schema=SCHEMA, bases=[renamed]).ok


@pytest.mark.parametrize("kwargs", [{"kind": "c1"}, {"engine": "ajv"}, {"stop": "never"}])
def test_bad_options_are_value_errors(kwargs):
    with pytest.raises(ValueError):
        run(FIXTURE, **kwargs)


# ------------------------------------------------------------------------------------------------ robustness

GARBAGE = [None, 0, 1.5, True, "", [], [None], [[]], {}, {"header": 3}, {"records": "x"},
           {"header": {"format": "khg-record/1.0.0"}, "records": [1, "a", None, [], {}, {"kind": "hyperedge"},
                                                                  {"kind": "hyperedge", "relation": 3,
                                                                   "bindings": "x"},
                                                                  {"kind": "hyperedge", "relation": "regulates",
                                                                   "bindings": [None, 3, {"role": 5},
                                                                                {"role": "regulator",
                                                                                 "value": [1]},
                                                                                {"role": "target",
                                                                                 "value": {"literal": 4}}],
                                                                   "evidence": [3, {"supports": 4,
                                                                                    "selectors": 5,
                                                                                    "confidence": 7}],
                                                                   "confidence": {"scale": 3}}]},
           {"incidences": 3, "metadata": []}, {"kind": "relation-schema", "format": 3},
           [{"kind": "queue-header", "format": "khg-queue/1.0.0"}, {"kind": "queue-item", "payload": [3]},
            {"kind": "queue-item", "payload": {"kind": "hyperedge", "relation": "born_in", "bindings": [{}]},
             "entities": 3}]]


@pytest.mark.parametrize("engine", ("jsonschema", "fastjsonschema"))
@pytest.mark.parametrize("kind", ("auto", *layers.KINDS))
def test_validate_never_raises_on_bad_input(kind, engine):
    for obj in GARBAGE:
        if isinstance(obj, str):
            continue  # a str is a path
        report = run(obj, kind=kind, schema=SCHEMA, engine=engine)
        assert report.skipped == [], (kind, obj, report.skipped)
        assert isinstance(report.ok, bool)
    assert not run(GARBAGE[11], kind="container", schema=SCHEMA, engine=engine).ok


def test_a_step_that_fails_after_an_error_is_skipped_and_one_without_raises(monkeypatch):
    module = layers.module("d_container")

    def boom(ctx):
        raise KeyError("a later layer could not read the input")

    monkeypatch.setattr(module, "run", boom)
    bad = copy.deepcopy(FIXTURE)
    bad["records"][35]["status"] = "believed"
    report = run(bad, kind="container", schema=SCHEMA)
    assert report.skipped == [("d_container", "KeyError: 'a later layer could not read the input'")]
    assert [f["code"] for f in report.errors] == ["KHG-C002"]
    with pytest.raises(KeyError):
        run(FIXTURE, kind="container", schema=SCHEMA)


def test_importing_the_validator_loads_no_engine_until_a_run_needs_one():
    code = (
        "import json, sys\n"
        "from khg_contracts import data, validate\n"
        "before = sorted(m for m in ('jsonschema', 'fastjsonschema') if m in sys.modules)\n"
        "validate.validate(data.path('fixture/fixture.relation-schema.json'), engine='fastjsonschema')\n"
        "mid = sorted(m for m in ('jsonschema', 'fastjsonschema') if m in sys.modules)\n"
        "print(json.dumps([before, mid]))\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == [[], ["fastjsonschema"]]
