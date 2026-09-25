"""G2: the checker reports class and width for a given schema file (DESIGN §1, §4.3, §5.1).

``test_fixture_table`` runs ``khg-width FILE --json --solver python`` on every row of fixtures/expected.csv and
checks the class, the first failed test, the witness and the four exact widths, each with a certificate that the
report says validated. ``test_exit_codes`` covers 0, 1 (every error finding printed) and 2.
"""
from __future__ import annotations

import gzip
import json
import shutil
from fractions import Fraction

import pytest

from helpers import FIXTURES, fixture_rows, residue_value, value
from khg_width.cli import main

ROWS = fixture_rows()


def run_cli(capsys, *args: str) -> tuple[int, str, str]:
    status = main(list(args))
    out = capsys.readouterr()
    return status, out.out, out.err


@pytest.mark.parametrize("row", ROWS, ids=[f"{r['fixture']}-{r['slots']}" for r in ROWS])
def test_fixture_table(row, capsys):
    status, out, err = run_cli(capsys, row["path"], "--json", "--solver", "python", "--slots",
                               ",".join(row["slot_tuple"]))
    assert status == 0, err
    rep = json.loads(out)
    assert rep["format"] == "khg-width-report/0.2.0"
    assert rep["slots"] == list(row["slot_tuple"])
    acy = rep["acyclicity"]
    assert acy["class"] == row["class"]
    assert acy["first_failed"] == (row["first_failed"] or None)
    w = acy["witness"]
    if row["witness_kind"]:
        assert w["kind"] == row["witness_kind"] and w["complete"] is True
        if row["witness_kind"] == "gyo_residue":
            assert w["value"] == residue_value(row["witness"])
        else:
            assert w["value"] == row["witness"].split(";")
    else:
        assert w is None
        assert acy["join_tree"] is not None and len(acy["join_tree"]["nodes"]) >= 1
    # the tests from alpha down stop at the first failure: later ones are implied (None)
    order = ["alpha", "beta", "gamma", "berge"]
    if row["first_failed"]:
        i = order.index(row["first_failed"])
        assert all(acy["tests"][t] is True for t in order[:i])
        assert acy["tests"][order[i]] is False
        assert all(acy["tests"][t] is None for t in order[i + 1:])
    else:
        assert all(acy["tests"][t] is True for t in order)
    for m in ("hw", "ghw", "fhw", "tw"):
        got = rep["widths"][m]
        want = value(m, row[m])
        assert got["exact"] is True, (m, got)
        assert (Fraction(got["upper"]) if m == "fhw" else got["upper"]) == want, (m, got)
        assert (Fraction(got["lower"]) if m == "fhw" else got["lower"]) == want
        assert got["validation"]["ok"] is True
        assert got["validation"]["kind"] == {"hw": "hd", "ghw": "ghd", "fhw": "fhd", "tw": "td"}[m]
        assert got["certificate"] is not None
    # identity block
    assert rep["schema"]["sha256"].startswith("sha256:") and len(rep["schema"]["file_sha256"]) == 64


def test_text_smoke(capsys):
    status, out, _ = run_cli(capsys, str(FIXTURES / "p6-qualifier-k5.relation-schema.json"), "--solver", "python")
    assert status == 0
    lines = out.splitlines()
    assert lines[0].startswith("schema      p6-qualifier-k5/0.1.0  sha256:")
    assert "slots core,qualifier" in lines[0]
    assert lines[1] == "class       cyclic (alpha fails)  witness: GYO residue, 10 relations on 5 roles"
    assert lines[2].startswith("hw   3      exact") and "k=2 no, k=3 yes" in lines[2] and "HD validated" in lines[2]
    assert lines[3].startswith("ghw  3      exact")
    assert lines[4].startswith("fhw  5/2    exact")
    assert lines[5].startswith("tw   4      exact")
    assert lines[6].startswith("reductions  gyo -20 roles")


def test_exit_codes(capsys, tmp_path):
    # 1: an invalid schema prints every error finding
    status, out, _ = run_cli(capsys, str(FIXTURES / "bad-m002.json"))
    assert status == 1
    assert "KHG-M002" in out and "role 'buyer' is used twice" in out
    status, out, _ = run_cli(capsys, str(FIXTURES / "bad-json.json"))
    assert status == 1
    assert "KHG-J001" in out
    # 2: usage and I/O errors
    ok = str(FIXTURES / "p6-berge-path.relation-schema.json")
    status, _, err = run_cli(capsys, str(tmp_path / "missing.json"))
    assert status == 2 and "cannot read" in err
    status, _, err = run_cli(capsys, ok, "--slots", "core,meta")
    assert status == 2 and "meta slot is refused" in err
    status, _, err = run_cli(capsys, ok, "--slots", "qualifier")
    assert status == 2 and "must contain core" in err
    status, _, err = run_cli(capsys, ok, "--time-limit", "-3")
    assert status == 2 and "positive" in err
    status, _, err = run_cli(capsys, ok, "--time-limit", "soon")
    assert status == 2 and "not a number" in err
    status, _, err = run_cli(capsys, ok, "--solver", "nope")
    assert status == 2
    # 0 on a cyclic schema: the class flags it, the exit status does not
    status, out, _ = run_cli(capsys, str(FIXTURES / "p6-adler.relation-schema.json"), "--solver", "python")
    assert status == 0 and "class       cyclic" in out


def test_missing_requested_solver(capsys, monkeypatch, tmp_path):
    for var in ("KHG_WIDTH_BALANCEDGO", "KHG_WIDTH_LOGK", "KHG_WIDTH_SOLVERS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setenv("PATH", str(tmp_path))
    status, _, err = run_cli(capsys, str(FIXTURES / "p6-berge-path.relation-schema.json"), "--solver", "balancedgo")
    assert status == 2 and "balancedgo was not found" in err
    status, _, err = run_cli(capsys, str(FIXTURES / "p6-berge-path.relation-schema.json"), "--solver", "logk")
    assert status == 2 and "logk was not found" in err


def test_json_gz(capsys, tmp_path):
    """Ruling Q5: .json.gz files are read like .json; a corrupt gzip file is an I/O error."""
    src = FIXTURES / "p6-adler.relation-schema.json"
    gz = tmp_path / "p6-adler.relation-schema.json.gz"
    gz.write_bytes(gzip.compress(src.read_bytes(), mtime=0))
    s1, o1, _ = run_cli(capsys, str(src), "--json", "--solver", "python")
    s2, o2, _ = run_cli(capsys, str(gz), "--json", "--solver", "python")
    assert s1 == s2 == 0
    r1, r2 = json.loads(o1), json.loads(o2)
    assert r1["schema"]["sha256"] == r2["schema"]["sha256"]
    assert r1["schema"]["file_sha256"] != r2["schema"]["file_sha256"]
    assert {m: r2["widths"][m]["upper"] for m in r2["widths"]} == {"hw": 3, "ghw": 2, "fhw": "2", "tw": 4}
    bad = tmp_path / "broken.json.gz"
    bad.write_bytes(gzip.compress(src.read_bytes())[:40])
    s3, _, err = run_cli(capsys, str(bad))
    assert s3 == 2 and "gzip" in err
    # an invalid document inside a .json.gz is still exit 1 with its findings
    badm = tmp_path / "bad-m002.json.gz"
    badm.write_bytes(gzip.compress((FIXTURES / "bad-m002.json").read_bytes()))
    s4, out, _ = run_cli(capsys, str(badm))
    assert s4 == 1 and "KHG-M002" in out


def test_python_module_entry(tmp_path):
    import subprocess
    import sys

    shutil.copy(FIXTURES / "p6-berge-path.relation-schema.json", tmp_path / "s.json")
    r = subprocess.run([sys.executable, "-m", "khg_width", str(tmp_path / "s.json"), "--solver", "python"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0
    assert "class       berge  witness: none (join tree)" in r.stdout
