"""W12: ``khg-convert IN OUT --to hif|khg-json|khg-jsonl`` (DESIGN §10.4) validates IN, then writes it converted:
the packaged HIF files and the JSONL fixture come back byte for byte. Exit 1 when IN fails validation or cannot be
converted (nothing is written then), 2 on a usage or I/O error."""
from __future__ import annotations

import copy
import json

import pytest

from khg_contracts import cli, data, hif, jsonio, record
from khg_contracts.migrate import LAYOUT, dumps
from khg_contracts.schema import load_schema

FIXTURE = "fixture/fixture.c1.json"
SCHEMA = "fixture/fixture.relation-schema.json"
SLICE = "fixture/fixture.directed-slice.hif.json"


def _slice_relations():
    return data.load_json(SLICE)["metadata"]["khg-slice"]["relations"]


def _files(directory):
    return sorted(p.name for p in directory.iterdir())


def test_khg_convert_smoke(run_cli, packaged, tmp_path):
    """The console script writes the packaged fixture's HIF file byte for byte; the input's two warnings go to
    stderr."""
    out = tmp_path / "fixture.hif.json"
    r = run_cli("khg-convert", packaged(FIXTURE), out, "--to", "hif", "--schema", packaged(SCHEMA))
    assert r.returncode == 0, r.stderr
    assert out.read_bytes() == data.read_bytes("fixture/fixture.hif.json")
    assert r.stdout == ""
    err = r.stderr.splitlines()
    assert [line.split(": ", 2)[2].split(":")[0] for line in err[:2]] == [
        "warning KHG-S024 at /records/31", "warning KHG-L008 at /records/29"]
    assert err[2] == f"khg-convert: wrote {out} (hif from the container {packaged(FIXTURE)})"
    assert _files(tmp_path) == ["fixture.hif.json"]


def test_the_directed_slice(packaged, tmp_path):
    out = tmp_path / "slice.hif.json"
    assert cli.convert_main([str(packaged(FIXTURE)), str(out), "--to", "hif", "--schema", str(packaged(SCHEMA)),
                             "--relations", ",".join(_slice_relations())]) == 0
    assert out.read_bytes() == data.read_bytes(SLICE)


def test_hif_to_a_container_and_back(packaged, tmp_path):
    schema = str(packaged(SCHEMA))
    lines, doc = tmp_path / "fixture.khg.jsonl", tmp_path / "fixture.khg.json"
    assert cli.convert_main([str(packaged("fixture/fixture.hif.json")), str(lines), "--to", "khg-jsonl",
                             "--schema", schema]) == 0
    assert lines.read_bytes() == data.read_bytes("fixture/fixture.c1.jsonl")
    assert cli.convert_main([str(packaged("fixture/fixture.hif.json")), str(doc), "--to", "khg-json",
                             "--schema", schema]) == 0
    fixture = record.read_container(data.path(FIXTURE))
    assert doc.read_text(encoding="utf-8") == record.serialize(fixture, format="json")
    assert jsonio.canonical(record.read_container(doc)) == jsonio.canonical(record.canonical_container(fixture))
    back = tmp_path / "back.hif.json"
    assert cli.convert_main([str(doc), str(back), "--to", "hif", "--schema", schema]) == 0
    # the canonical container sorts the keys of the values that to_hif copies, so only the canonical forms agree
    assert jsonio.canonical(jsonio.load(back)) == jsonio.canonical(data.load_json("fixture/fixture.hif.json"))


def test_a_container_changes_form(packaged, tmp_path):
    out = tmp_path / "fixture.khg.jsonl"
    assert cli.convert_main([str(packaged(FIXTURE)), str(out), "--to", "khg-jsonl",
                             "--schema", str(packaged(SCHEMA))]) == 0
    assert out.read_bytes() == data.read_bytes("fixture/fixture.c1.jsonl")


def test_a_hif_file_is_sliced(packaged, tmp_path):
    out = tmp_path / "slice.hif.json"
    assert cli.convert_main([str(packaged("fixture/fixture.hif.json")), str(out), "--to", "hif",
                             "--schema", str(packaged(SCHEMA)), "--relations", ",".join(_slice_relations())]) == 0
    assert out.read_bytes() == data.read_bytes(SLICE)


def test_per_binding_literals_and_the_inlined_schema(packaged, tmp_path):
    """``--literal-nodes per_binding --schema-document`` give ``to_hif``'s file, which then converts back without
    ``--schema``."""
    out, back = tmp_path / "pb.hif.json", tmp_path / "pb.khg.jsonl"
    assert cli.convert_main([str(packaged(FIXTURE)), str(out), "--to", "hif", "--schema", str(packaged(SCHEMA)),
                             "--literal-nodes", "per_binding", "--schema-document"]) == 0
    fixture, schema = data.load_json(FIXTURE), load_schema(data.load_json(SCHEMA))
    want = hif.to_hif(fixture, schema, literal_nodes="per_binding", schema_document=True)
    assert out.read_text(encoding="utf-8") == dumps(want, compact=LAYOUT["hif"])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["metadata"]["khg-literal-nodes"] == "per_binding"
    assert doc["metadata"]["khg-schema-document"] == data.load_json(SCHEMA)
    assert any(n["node"].startswith("_:litb:") for n in doc["nodes"])
    assert cli.convert_main([str(out), str(back), "--to", "khg-jsonl"]) == 0
    assert back.read_bytes() == data.read_bytes("fixture/fixture.c1.jsonl")


def test_a_container_that_embeds_its_schema(tmp_path):
    container = data.load_json(FIXTURE)
    container["records"].insert(0, data.load_json(SCHEMA))
    path, out = tmp_path / "embedded.khg.json", tmp_path / "embedded.hif.json"
    path.write_text(json.dumps(container, ensure_ascii=False), encoding="utf-8")
    assert cli.convert_main([str(path), str(out), "--to", "hif"]) == 0
    assert out.read_bytes() == data.read_bytes("fixture/fixture.hif.json")


def test_an_existing_output_is_replaced(packaged, tmp_path):
    out = tmp_path / "fixture.khg.jsonl"
    out.write_text("old\n", encoding="utf-8")
    assert cli.convert_main([str(packaged(FIXTURE)), str(out), "--to", "khg-jsonl",
                             "--schema", str(packaged(SCHEMA))]) == 0
    assert out.read_bytes() == data.read_bytes("fixture/fixture.c1.jsonl")
    assert _files(tmp_path) == ["fixture.khg.jsonl"]  # no temporary file is left behind


# ------------------------------------------------------------------------------------------------ exit 1


def test_hif_without_a_schema_exits_1(packaged, tmp_path, capsys):
    path, out = str(packaged("fixture/fixture.hif.json")), tmp_path / "x.khg.json"
    assert cli.convert_main([path, str(out), "--to", "khg-json"]) == 1
    assert capsys.readouterr().err.splitlines() == [
        f"khg-convert: {path}: error KHG-D009 at /metadata/khg-schema: no relation-type schema supplied and none "
        f"embedded",
        f"khg-convert: {path}: invalid (hif; 1 error, 0 warnings); nothing written"]
    assert _files(tmp_path) == []


def test_an_invalid_container_is_not_converted(packaged, tmp_path, capsys):
    container = copy.deepcopy(data.load_json(FIXTURE))
    for r in container["records"]:
        if r.get("id") == "f:reg-1":
            r["status"] = "bogus"
    path, out = tmp_path / "bogus.khg.json", tmp_path / "bogus.hif.json"
    path.write_text(json.dumps(container, ensure_ascii=False), encoding="utf-8")
    out.write_text("kept\n", encoding="utf-8")
    assert cli.convert_main([str(path), str(out), "--to", "hif", "--schema", str(packaged(SCHEMA))]) == 1
    err = capsys.readouterr().err.splitlines()
    assert [line for line in err if " error " in line] == [
        line for line in err if line.startswith(f"khg-convert: {path}: error KHG-C002 at /records/35/status: ")]
    assert len(err) == 4  # the error, the two warnings and the verdict
    assert err[-1] == f"khg-convert: {path}: invalid (container; 1 error, 2 warnings); nothing written"
    assert out.read_text(encoding="utf-8") == "kept\n"  # the old output is untouched


def test_a_file_of_another_schema_exits_1(packaged, tmp_path, capsys):
    path = str(packaged("sample/sample.khg.hif.json"))
    assert cli.convert_main([path, str(tmp_path / "x.khg.json"), "--to", "khg-json",
                             "--schema", str(packaged(SCHEMA))]) == 1
    err = capsys.readouterr().err
    assert f"{path}: error KHG-D009 at /metadata/khg-schema:" in err
    assert _files(tmp_path) == []


def test_foreign_hif_is_refused(packaged, tmp_path, capsys):
    """A role-convention file without the profile is P001: importing foreign HIF comes in 1.1 (§4.3)."""
    path = str(packaged("role-convention/basic.hif.json"))
    assert cli.convert_main([path, str(tmp_path / "x.khg.json"), "--to", "khg-json"]) == 1
    err = capsys.readouterr().err.splitlines()
    assert f"khg-convert: {path}: error KHG-P001 at /metadata: 'khg-profile' is a required property" in err
    assert err[-1].startswith(f"khg-convert: {path}: invalid (hif; ")
    assert _files(tmp_path) == []


@pytest.mark.parametrize("rel, what", [(SCHEMA, "a schema"), ("fixture/c4-items.jsonl", "an item")],
                         ids=["schema", "c4-items"])
def test_an_input_of_another_kind_exits_1(packaged, tmp_path, capsys, rel, what):
    path = str(packaged(rel))
    assert cli.convert_main([path, str(tmp_path / "x.hif.json"), "--to", "hif"]) == 1
    assert capsys.readouterr().err == (f"khg-convert: {path} is {what} file: khg-convert reads a C1 container or "
                                       f"a khg-hif file\n")
    assert _files(tmp_path) == []


# ------------------------------------------------------------------------------------------------ exit 2


@pytest.mark.parametrize("out, extra, message", [
    ("x.khg.json", ["--to", "khg-json", "--relations", "regulates"], "--relations: only with --to hif"),
    ("x.khg.json", ["--to", "khg-json", "--literal-nodes", "shared"], "--literal-nodes: only with --to hif"),
    ("x.khg.jsonl", ["--to", "khg-jsonl", "--schema-document"], "--schema-document: only with --to hif"),
    ("x.khg.json", ["--to", "khg-jsonl"], "does not fit --to khg-jsonl"),
    ("x.khg.jsonl", ["--to", "khg-json"], "does not fit --to khg-json"),
    ("x.hif.jsonl", ["--to", "hif"], "does not fit --to hif"),
    ("x.hif.json", ["--to", "hif", "--relations", "regulates,,claims"], "argument --relations: 'regulates,,claims'"),
    ("x.hif.json", ["--to", "hif", "--relations", "regulates,marries"], "--relations: marries not declared in "
                                                                        "p2-gate/1.0.0"),
    ("x.hif.json", ["--to", "xgi"], "argument --to: invalid choice: 'xgi'"),
    ("x.hif.json", [], "the following arguments are required: --to"),
])
def test_usage_errors_exit_2_and_write_nothing(packaged, tmp_path, capsys, out, extra, message):
    argv = [str(packaged(FIXTURE)), str(tmp_path / out), "--schema", str(packaged(SCHEMA)), *extra]
    assert cli.convert_main(argv) == 2
    err = capsys.readouterr().err
    assert "usage: khg-convert" in err and message in err
    assert _files(tmp_path) == []


def test_io_errors_exit_2(packaged, tmp_path, capsys):
    missing = tmp_path / "missing.khg.json"
    assert cli.convert_main([str(missing), str(tmp_path / "x.hif.json"), "--to", "hif"]) == 2
    assert capsys.readouterr().err == f"khg-convert: cannot read {missing}: No such file or directory\n"
    out = tmp_path / "no-such-dir" / "x.hif.json"
    assert cli.convert_main([str(packaged(FIXTURE)), str(out), "--to", "hif", "--schema", str(packaged(SCHEMA))]) == 2
    assert capsys.readouterr().err.splitlines()[-1] == f"khg-convert: cannot write {out}: No such file or directory"
    assert cli.convert_main([str(packaged(FIXTURE)), str(tmp_path / "x.hif.json"), "--to", "hif",
                             "--schema", str(missing)]) == 2
    assert capsys.readouterr().err == f"khg-convert: --schema: cannot read {missing}: No such file or directory\n"


def test_a_failed_write_leaves_no_temporary_file(packaged, tmp_path, capsys):
    out = tmp_path / "taken"
    out.mkdir()  # the rename onto a directory fails after the temporary file was written
    assert cli.convert_main([str(packaged(FIXTURE)), str(out), "--to", "hif", "--schema", str(packaged(SCHEMA))]) == 2
    assert capsys.readouterr().err.splitlines()[-1].startswith(f"khg-convert: cannot write {out}: ")
    assert _files(tmp_path) == ["taken"] and _files(out) == []
