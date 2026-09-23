"""W12: ``khg-migrate IN OUT --from v0-sample [--schema-out P] [--report P]`` (DESIGN §10.4, §11.3) writes the
container, the generated schema and the F report; the §11.3 command reproduces the packaged goldens byte for byte.
Exit 1 when the migration refuses IN (nothing is written then), 2 on a usage or I/O error."""
from __future__ import annotations

import json

import pytest

from khg_contracts import cli, data, jsonio, migrate, record

GOLDENS = {"container": "sample/sample.khg.json", "schema": "sample/sample.relation-schema.json",
           "report": "sample/sample.migration-report.json", "hif": "sample/sample.khg.hif.json"}


def _files(directory):
    return sorted(p.name for p in directory.iterdir())


def test_khg_migrate_smoke(run_cli, v0_sample, tmp_path):
    """The §11.3 command, with the report written to a file: the three outputs equal the goldens."""
    r = run_cli("khg-migrate", v0_sample, "sample.khg.json", "--from", "v0-sample",
                "--schema-out", "sample.relation-schema.json", "--report", "sample.migration-report.json", cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    for name in ("container", "schema", "report"):
        rel = GOLDENS[name]
        assert (tmp_path / rel.split("/")[1]).read_bytes() == data.read_bytes(rel), name
    assert r.stdout == ""
    assert r.stderr == ("khg-migrate: wrote sample.khg.json, sample.relation-schema.json, "
                        "sample.migration-report.json\n")
    assert _files(tmp_path) == ["sample.khg.json", "sample.migration-report.json", "sample.relation-schema.json"]


def test_the_fourth_golden_comes_from_khg_convert(v0_sample, tmp_path, capsys):
    """``sample.khg.hif.json`` is the migrated container converted with the generated schema."""
    out, schema, hif = tmp_path / "sample.khg.json", tmp_path / "s.json", tmp_path / "sample.khg.hif.json"
    assert cli.migrate_main([str(v0_sample), str(out), "--from", "v0-sample", "--schema-out", str(schema),
                             "--report", str(tmp_path / "r.json")]) == 0
    assert cli.convert_main([str(out), str(hif), "--to", "hif", "--schema", str(schema)]) == 0
    assert hif.read_bytes() == data.read_bytes(GOLDENS["hif"])
    assert capsys.readouterr().out == ""


def test_without_report_the_report_goes_to_stdout(v0_sample, tmp_path, capsys):
    out = tmp_path / "sample.khg.json"
    assert cli.migrate_main([str(v0_sample), str(out), "--from", "v0-sample"]) == 0
    captured = capsys.readouterr()
    assert captured.out == data.read_text(GOLDENS["report"])
    assert [f["code"] for f in json.loads(captured.out)["findings"]] == [
        "KHG-F017", "KHG-F006", "KHG-F015", "KHG-F006", "KHG-F015", "KHG-F006", "KHG-F015", "KHG-F016"]
    assert captured.err == f"khg-migrate: wrote {out}\n"
    assert _files(tmp_path) == ["sample.khg.json"]  # no schema without --schema-out
    assert out.read_bytes() == data.read_bytes(GOLDENS["container"])


def test_a_jsonl_output_is_the_canonical_container(v0_sample, tmp_path):
    out = tmp_path / "sample.khg.jsonl"
    report = str(tmp_path / "r.json")
    assert cli.migrate_main([str(v0_sample), str(out), "--from", "v0-sample", "--report", report]) == 0
    golden = record.read_container(data.path(GOLDENS["container"]))
    assert out.read_text(encoding="utf-8") == record.serialize(golden, format="jsonl")
    assert jsonio.canonical(record.read_container(out)) == jsonio.canonical(golden)


def test_the_output_equals_the_migration(v0_sample, tmp_path):
    out, schema = tmp_path / "sample.khg.json", tmp_path / "sample.relation-schema.json"
    assert cli.migrate_main([str(v0_sample), str(out), "--from", "v0-sample", "--schema-out", str(schema),
                             "--report", str(tmp_path / "r.json")]) == 0
    m = migrate.MIGRATIONS["v0-sample"](v0_sample)
    assert jsonio.load(out) == m.container and jsonio.load(schema) == m.schema
    assert jsonio.load(tmp_path / "r.json") == m.report


# ------------------------------------------------------------------------------------------------ exit 1


def test_a_disagreeing_arity_is_refused_and_nothing_is_written(v0_sample, tmp_path, capsys):
    v0 = jsonio.load(v0_sample)
    v0["edges"][0]["attrs"]["arity"] = 5  # f1 has four bindings
    path = tmp_path / "in" / "v0.hif.json"
    path.parent.mkdir()
    path.write_text(json.dumps(v0, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    assert cli.migrate_main([str(path), str(out / "s.khg.json"), "--from", "v0-sample",
                             "--schema-out", str(out / "s.json"), "--report", str(out / "r.json")]) == 1
    err = capsys.readouterr().err.splitlines()
    assert err[0].startswith(f"khg-migrate: {path}: error KHG-D015 at /edges/0/attrs/arity: ")
    assert err[-1] == f"khg-migrate: {path} cannot be migrated from v0-sample; nothing written"
    assert _files(out) == []


def test_a_file_that_is_not_json_is_refused(tmp_path, capsys):
    path = tmp_path / "v0.hif.json"
    path.write_text("{", encoding="utf-8")
    assert cli.migrate_main([str(path), str(tmp_path / "s.khg.json"), "--from", "v0-sample"]) == 1
    err = capsys.readouterr().err.splitlines()
    assert err[0].startswith(f"khg-migrate: {path}: error KHG-J001")
    assert _files(tmp_path) == ["v0.hif.json"]


# ------------------------------------------------------------------------------------------------ exit 2


@pytest.mark.parametrize("extra, message", [
    (["--from", "v1-sample"], "argument --from: invalid choice: 'v1-sample'"),
    ([], "the following arguments are required: --from"),
])
def test_usage_errors_exit_2(v0_sample, tmp_path, capsys, extra, message):
    assert cli.migrate_main([str(v0_sample), str(tmp_path / "s.khg.json"), *extra]) == 2
    err = capsys.readouterr().err
    assert err.startswith("usage: khg-migrate") and message in err
    assert _files(tmp_path) == []


def test_io_errors_exit_2(v0_sample, tmp_path, capsys):
    missing = tmp_path / "missing.hif.json"
    assert cli.migrate_main([str(missing), str(tmp_path / "s.khg.json"), "--from", "v0-sample"]) == 2
    assert capsys.readouterr().err == f"khg-migrate: cannot read {missing}: No such file or directory\n"
    out = tmp_path / "no-such-dir" / "s.khg.json"
    assert cli.migrate_main([str(v0_sample), str(out), "--from", "v0-sample"]) == 2
    captured = capsys.readouterr()
    assert captured.err == f"khg-migrate: cannot write {out}: No such file or directory\n"
    assert captured.out == ""  # the report is printed only after every file is written
