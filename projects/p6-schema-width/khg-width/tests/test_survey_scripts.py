"""The survey scripts' file handling (review findings F3 and F4), on a synthetic results directory.

F3: when P3a's counts land, the SQID-based observed schema files and their rows' reports move to
``results/superseded/`` (DESIGN §6.6) and the P3a-based files are installed; this is expected, not a mismatch.
F4: a regenerated schema identical to the committed one leaves the committed files untouched (provenance included).
"""
from __future__ import annotations

import importlib.util
import json
import os

import pytest

from helpers import P6

_spec = importlib.util.spec_from_file_location("run_survey", P6 / "survey" / "run_survey.py")
run_survey = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_survey)

SID = "p6-wikidata-observed-robust-wd-roles-r1"


def schema(root, sid: str, content: bytes, counts: str | None, commit: str = "c1", suffix: str = ".json.gz") -> None:
    d = root / "schemas"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}{suffix}").write_bytes(content)
    prov = {"schema_id": sid, "file": f"schemas/{sid}{suffix}", "file_sha256": "f-" + content.decode(),
            "schema_sha256": "s-" + content.decode(), "counts_source": counts, "commit": commit}
    (d / f"{sid}.provenance.json").write_text(json.dumps(prov))


def report(root, row_id: str) -> None:
    d = root / "reports"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{row_id}.json.gz").write_bytes(b"old report")
    (d / f"{row_id}.log").write_text("old log")


def test_p3a_counts_supersede_sqid_files_and_reports(tmp_path):
    out, src = tmp_path / "results", tmp_path / "generated"
    schema(out, SID, b"sqid", "SQID")
    report(out, "wd-observed-robust-wd-roles-r1-cq")
    report(out, "wd-observed-robust-wd-roles-r1-cqt")
    schema(out, "p6-wikidata-declared-wd-roles-r1", b"decl", None)
    report(out, "wd-declared-wd-roles-r1-cq")
    schema(src, SID, b"p3a", "P3a", commit="c2")
    schema(src, "p6-wikidata-declared-wd-roles-r1", b"decl", None, commit="c2")
    slice_id = "p6-wikidata-observed-robust-slice-wd-roles-r1"
    schema(src, slice_id, b"slice", "P3a", commit="c2")
    summary = run_survey.install(src, out)
    assert summary == {"unchanged": ["p6-wikidata-declared-wd-roles-r1"], "new": [slice_id],
                       "superseded": [SID], "replaced": []}
    sup = out / "superseded"
    assert (sup / f"{SID}.json.gz").read_bytes() == b"sqid"
    assert json.loads((sup / f"{SID}.provenance.json").read_text())["counts_source"] == "SQID"
    assert {p.name for p in sup.iterdir()} >= {"wd-observed-robust-wd-roles-r1-cq.json.gz",
                                                "wd-observed-robust-wd-roles-r1-cqt.json.gz",
                                                "wd-observed-robust-wd-roles-r1-cq.log"}
    assert not (out / "reports" / "wd-observed-robust-wd-roles-r1-cq.json.gz").exists()
    assert (out / "reports" / "wd-declared-wd-roles-r1-cq.json.gz").exists()  # untouched
    assert (out / "schemas" / f"{SID}.json.gz").read_bytes() == b"p3a"
    assert (out / "schemas" / f"{slice_id}.json.gz").read_bytes() == b"slice"
    pend = run_survey.load_pending(out)
    assert set(pend) == {"wd-observed-robust-wd-roles-r1-cq", "wd-observed-robust-wd-roles-r1-cqt",
                         "wd-observed-robust-slice-wd-roles-r1-cq", "wd-observed-robust-slice-wd-roles-r1-cqt"}
    run_survey.clear_pending(out, list(pend))
    assert not (out / run_survey.PENDING).exists()


def test_identical_schemas_are_left_untouched(tmp_path):
    out, src = tmp_path / "results", tmp_path / "generated"
    schema(out, SID, b"same", "SQID", commit="old-commit")
    schema(src, SID, b"same", "SQID", commit="new-commit")
    prov = out / "schemas" / f"{SID}.provenance.json"
    os.utime(prov, (1_000_000, 1_000_000))
    before = prov.read_bytes()
    assert run_survey.install(src, out)["unchanged"] == [SID]
    assert prov.read_bytes() == before and prov.stat().st_mtime == 1_000_000  # F4: provenance not rewritten
    assert run_survey.load_pending(out) == {}


def test_other_differences_need_a_new_snapshot(tmp_path):
    out, src = tmp_path / "results", tmp_path / "generated"
    schema(out, SID, b"v1", "SQID")
    report(out, "wd-observed-robust-wd-roles-r1-cq")
    schema(src, SID, b"v2", "SQID")
    with pytest.raises(SystemExit, match="differ from the committed ones"):
        run_survey.install(src, out)
    assert (out / "schemas" / f"{SID}.json.gz").read_bytes() == b"v1"  # nothing touched
    summary = run_survey.install(src, out, new_snapshot=True)
    assert summary["replaced"] == [SID] and (out / "schemas" / f"{SID}.json.gz").read_bytes() == b"v2"
    # the stale report stays in place and the rows are listed for a re-run
    assert set(run_survey.load_pending(out)) == {"wd-observed-robust-wd-roles-r1-cq",
                                                 "wd-observed-robust-wd-roles-r1-cqt"}


def test_reproduce_installs_through_run_survey():
    text = (P6 / "survey" / "reproduce.sh").read_text()
    assert 'run_survey.py" generate --out "$OUT"' in text and "shutil.copy2" not in text
