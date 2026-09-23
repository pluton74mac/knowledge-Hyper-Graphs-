"""W12: ``khg-validate PATH`` (DESIGN §10.4) prints the ``validate()`` result, as lines or ``--json``, and exits 0
without an error finding, 1 with one, and 2 on a usage or I/O error."""
from __future__ import annotations

import copy
import io
import json
import sys

import pytest

from khg_contracts import cli, data, validate

FIXTURE = "fixture/fixture.c1.json"
SCHEMA = "fixture/fixture.relation-schema.json"
#: The fixture's two designed warnings (§1.4): S024 on f:loop-yyz, L008 on f:king-13 and f:king-14.
WARNINGS = [("KHG-S024", "warning", "/records/31"), ("KHG-L008", "warning", "/records/29")]


def _summary(result):
    return [(f["code"], f["severity"], f["path"]) for f in result["findings"]]


def _lines(path, result):
    """The text output ``khg-validate`` gives for ``result`` (without the verdict)."""
    return [f"{path}: {f['severity']} {f['code']}" + (f" at {f['path']}" if f["path"] else "") + f": {f['message']}"
            for f in result["findings"]]


def test_khg_validate_smoke(run_cli, packaged):
    """The console script on the packaged fixture, as the CI wheel job runs it: valid, with the two warnings."""
    fixture, schema = packaged(FIXTURE), packaged(SCHEMA)
    r = run_cli("khg-validate", fixture, "--kind", "container", "--schema", schema, "--json")
    assert r.returncode == 0, r.stderr
    result = json.loads(r.stdout)
    assert result == validate.validate(fixture, kind="container", schema=schema)
    assert result["ok"] is True and _summary(result) == WARNINGS
    assert r.stderr == ""


def test_the_text_output_is_a_line_per_finding_then_the_verdict(packaged, capsys):
    fixture, schema = str(packaged(FIXTURE)), str(packaged(SCHEMA))
    assert cli.validate_main([fixture, "--schema", schema]) == 0
    out = capsys.readouterr()
    result = validate.validate(fixture, schema=schema)
    assert out.out.splitlines() == _lines(fixture, result) + [f"{fixture}: valid (container; 0 errors, 2 warnings)"]
    assert out.out.splitlines()[0].startswith(f"{fixture}: warning KHG-S024 at /records/31: ")
    assert out.err == ""


@pytest.mark.parametrize("rel, extra, verdict", [
    (SCHEMA, [], "valid (schema; 0 errors, 0 warnings)"),
    ("role-convention/two-roles.hif.json", [], "valid (role-convention; 0 errors, 0 warnings)"),
    ("fixture/fixture.hif.json", ["--schema", SCHEMA], "valid (hif; 0 errors, 2 warnings)"),
    ("fixture/fixture.c1.jsonl", ["--schema", SCHEMA], "valid (container; 0 errors, 2 warnings)"),
    ("fixture/smoke-queue.khg-queue.jsonl", ["--schema", SCHEMA, "--base", "fixture/smoke-base.c1.json"],
     "valid (queue; 0 errors, 0 warnings)"),
])
def test_the_kind_is_told_from_the_content(packaged, capsys, rel, extra, verdict):
    path = str(packaged(rel))
    args = [str(packaged(a)) if a.endswith(".json") else a for a in extra]
    assert cli.validate_main([path, *args]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == f"{path}: {verdict}"


def test_an_error_finding_exits_1_and_the_json_is_the_validate_result(packaged, capsys):
    path = str(packaged("fixture/fixture.c1.jsonl"))  # no schema given and none embedded: D009
    assert cli.validate_main([path, "--json"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result == validate.validate(path)
    assert result["ok"] is False and _summary(result) == [("KHG-D009", "error", "/header/schema")]
    assert cli.validate_main([path]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == f"{path}: invalid (container; 1 error, 0 warnings)"


def test_a_queue_is_checked_against_the_base_it_names(packaged, capsys):
    queue, schema = str(packaged("fixture/smoke-queue.khg-queue.jsonl")), str(packaged(SCHEMA))
    base = str(packaged("fixture/smoke-base.c1.json"))
    assert cli.validate_main([queue, "--kind", "queue", "--schema", schema, "--base", base, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "findings": []}
    assert cli.validate_main([queue, "--kind", "queue", "--schema", schema, "--json"]) == 1
    codes = [f["code"] for f in json.loads(capsys.readouterr().out)["findings"]]
    assert codes == ["KHG-Q012", "KHG-Q011", "KHG-Q011", "KHG-Q011"]


def test_the_kind_option_forces_a_pipeline(packaged, capsys):
    path = str(packaged(SCHEMA))
    assert cli.validate_main([path, "--kind", "container", "--json"]) == 1
    assert json.loads(capsys.readouterr().out) == validate.validate(path, kind="container")


def test_a_document_that_is_not_json_is_invalid(tmp_path, capsys):
    path = tmp_path / "dup.json"
    path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    assert cli.validate_main([str(path)]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith(f"{path}: error KHG-J003")
    assert lines[-1] == f"{path}: invalid (unknown kind; 1 error, 0 warnings)"


def test_both_engines(packaged, capsys):
    fixture, schema = str(packaged(FIXTURE)), str(packaged(SCHEMA))
    assert cli.validate_main([fixture, "--schema", schema, "--engine", "fastjsonschema", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == validate.validate(fixture, schema=schema, engine="fastjsonschema")
    assert _summary(result) == WARNINGS


def test_doc_texts_feed_the_span_check(packaged, tmp_path, capsys):
    fixture, schema = str(packaged(FIXTURE)), str(packaged(SCHEMA))
    texts = str(packaged("fixture/fixture.doc-texts.json"))
    assert cli.validate_main([fixture, "--schema", schema, "--doc-texts", texts, "--json"]) == 0
    assert _summary(json.loads(capsys.readouterr().out)) == WARNINGS
    wrong = data.load_json("fixture/fixture.doc-texts.json")
    wrong["texts"]["doc:coadmin-note"]["text"] = "Something else entirely, of a similar length: sixty-one chars."
    path = tmp_path / "wrong.doc-texts.json"
    path.write_text(json.dumps(wrong), encoding="utf-8")
    assert cli.validate_main([fixture, "--schema", schema, "--doc-texts", str(path), "--json"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert [f["code"] for f in result["findings"] if f["severity"] == "error"] == ["KHG-S021"]


def test_output_that_stdout_cannot_encode_is_escaped(packaged, tmp_path, monkeypatch):
    """An ASCII stdout gets backslash escapes in the lines and ``\\u`` escapes in the JSON (still the result)."""
    container = copy.deepcopy(data.load_json(FIXTURE))
    for r in container["records"]:
        if r.get("id") == "f:pop-łódź-2019":
            r["bindings"][0]["value"] = {"entity": "ex:Łódź-nowhere"}
    path = tmp_path / "łódź.khg.json"
    path.write_text(json.dumps(container, ensure_ascii=False), encoding="utf-8")
    schema = str(packaged(SCHEMA))
    for extra in ([], ["--json"]):
        buffer = io.BytesIO()
        monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buffer, encoding="ascii", newline="\n"))
        assert cli.validate_main([str(path), "--schema", schema, *extra]) == 1
        sys.stdout.flush()
        text = buffer.getvalue().decode("ascii")
        if extra:
            assert json.loads(text) == validate.validate(path, schema=schema)
            assert "ex:\\u0141\\u00f3d\\u017a-nowhere" in text
        else:
            assert "error KHG-D002 at /records/33/bindings/0/value: entity ex:\\u0141\\xf3d\\u017a-nowhere" in text
            assert text.splitlines()[-1].endswith("\\u0142\\xf3d\\u017a.khg.json: invalid (container; 1 error, "
                                                  "2 warnings)")


# ------------------------------------------------------------------------------------------------ exit 2


def test_an_unreadable_path_exits_2(tmp_path, capsys):
    assert cli.validate_main([str(tmp_path / "missing.json")]) == 2
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == f"khg-validate: cannot read {tmp_path / 'missing.json'}: No such file or directory\n"
    assert cli.validate_main([str(tmp_path)]) == 2  # a directory
    assert capsys.readouterr().err.startswith(f"khg-validate: cannot read {tmp_path}: ")


@pytest.mark.parametrize("argv, message", [
    ([], "the following arguments are required: PATH"),
    (["x.json", "--kind", "c1"], "argument --kind: invalid choice: 'c1'"),
    (["x.json", "--engine", "ajv"], "argument --engine: invalid choice: 'ajv'"),
    (["x.json", "--schem", "s.json"], "unrecognized arguments: --schem s.json"),
])
def test_usage_errors_exit_2(capsys, argv, message):
    assert cli.validate_main(argv) == 2
    err = capsys.readouterr().err
    assert err.startswith("usage: khg-validate") and message in err


def test_argument_files_that_cannot_be_used_exit_2(packaged, tmp_path, capsys):
    fixture, schema = str(packaged(FIXTURE)), str(packaged(SCHEMA))
    assert cli.validate_main([fixture, "--schema", fixture]) == 2  # a container is not a relation-type schema
    err = capsys.readouterr().err.splitlines()
    assert err[0].startswith(f"khg-validate: {fixture}: error KHG-V001")
    assert err[-1] == f"khg-validate: --schema: {fixture} is not a valid relation-type schema"
    missing = str(tmp_path / "missing.json")
    for option in ("--schema", "--doc-texts"):
        assert cli.validate_main([fixture, "--schema", schema, option, missing]) == 2
        assert capsys.readouterr().err == f"khg-validate: {option}: cannot read {missing}: No such file or directory\n"
    queue = str(packaged("fixture/smoke-queue.khg-queue.jsonl"))
    assert cli.validate_main([queue, "--schema", schema, "--base", missing]) == 2
    assert capsys.readouterr().err == f"khg-validate: --base: cannot read {missing}: No such file or directory\n"
    assert cli.validate_main([queue, "--schema", schema, "--base", schema]) == 2
    assert capsys.readouterr().err.splitlines()[-1] == f"khg-validate: --base: {schema} is not a C1 container"
    texts = tmp_path / "texts.json"
    texts.write_text('{"texts": {}, "texts": {}}', encoding="utf-8")
    assert cli.validate_main([fixture, "--schema", schema, "--doc-texts", str(texts)]) == 2
    assert capsys.readouterr().err.splitlines() == [
        f"khg-validate: {texts}: error KHG-J003: duplicate key 'texts'",
        f"khg-validate: --doc-texts: {texts} is not a JSON object"]


def test_help_exits_0(capsys):
    assert cli.validate_main(["--help"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: khg-validate")
    epilog = "Exit status: 0 on success, 1 when a finding is an error, 2 on a usage or I/O error."
    assert epilog in " ".join(out.split())
