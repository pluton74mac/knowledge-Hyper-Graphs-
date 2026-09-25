"""The ``khg-bakeoff`` command (DESIGN §6)."""
from __future__ import annotations

import json

import pytest

from khg_bakeoff.cli import main


def test_conformance_and_fidelity_on_sqlite(tmp_path, capsys):
    conf = tmp_path / "conformance"
    assert main(["conformance", "sqlite", "--out", str(conf)]) == 0
    assert "sqlite: applicable 114, passed 114, failed 0" in capsys.readouterr().out
    earl = json.loads((conf / "sqlite.earl.json").read_text(encoding="utf-8"))
    assert earl["summary"]["passed"] == 114 and earl["subject"]["title"] == "sqlite"
    summary = json.loads((conf / "summary.json").read_text(encoding="utf-8"))
    b = summary["backends"]["sqlite"]
    assert (b["applicable"], b["passed"], b["inapplicable"], b["passes"]) == (114, 114, 0, True)
    assert summary["provenance"]["contracts"]["C2"] == "khg-store/1.0.0"
    assert "| sqlite | SQLite" in (conf / "summary.md").read_text(encoding="utf-8")
    assert main(["fidelity", "sqlite", "--out", str(tmp_path), "--conformance", str(conf / "summary.json")]) == 0
    fid = json.loads((tmp_path / "fidelity.json").read_text(encoding="utf-8"))
    s = fid["backends"]["sqlite"]
    assert s["conformance"]["applicable"] == 114 and s["datasets"]["edge"]["round_trip"]["skipped"] == 1
    md = (tmp_path / "fidelity.md").read_text(encoding="utf-8")
    assert "| sqlite | SQLite" in md and "`f:far-future` skipped" in md


def test_usage_errors_exit_2(capsys):
    with pytest.raises(SystemExit) as e:
        main(["conformance", "nosuch"])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        main(["frobnicate"])
    assert e.value.code == 2
