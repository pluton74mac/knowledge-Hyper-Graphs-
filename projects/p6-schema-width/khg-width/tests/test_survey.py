"""G1: the survey table (DESIGN §1, §6). Marked ``survey``: skipped until results/survey.csv exists.

- ``test_wikidata_rows``: the 12 dump-scope rows are present, and the 8 slice rows exactly when the counts came from
  P3a; every schema file's sha256 matches the table and its provenance; the class and the core are recomputed; the
  stored certificates re-validate on H; the bounds are consistent; the naming version is wd-roles r1.
- ``test_biolink_rows``: the 3 Biolink rows are recomputed with ``--solver python``.
- ``test_hyperbench_row``: the baseline row is the published one (n = 1,113; hw 1/2/3 = 673/432/8).
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from fractions import Fraction

import pytest

from helpers import RESULTS
from khg_width import Decomposition, check, classify, hypergraph, validate
from khg_width.reduce import core
from khg_width.report import fmt_value

pytestmark = pytest.mark.survey
KIND = {"hw": "hd", "ghw": "ghd", "fhw": "fhd", "tw": "td"}


def table() -> dict[str, dict]:
    with open(RESULTS / "survey.csv", newline="", encoding="utf-8") as fh:
        return {r["row_id"]: r for r in csv.DictReader(fh)}


def report(row_id: str) -> dict:
    """Ruling Q6: reports are gzip-compressed JSON written with mtime 0."""
    raw = (RESULTS / "reports" / f"{row_id}.json.gz").read_bytes()
    assert raw[4:8] == b"\x00\x00\x00\x00"  # the gzip header's mtime
    return json.loads(gzip.decompress(raw))


def num(m: str, x):
    return Fraction(str(x).lstrip(">")) if m == "fhw" else int(str(x).lstrip(">"))


def check_row(row: dict, *, recompute_widths: bool = False) -> None:
    f = RESULTS / row["file"]
    assert hashlib.sha256(f.read_bytes()).hexdigest() == row["file_sha256"]
    prov = json.loads((RESULTS / "schemas" / f"{row['schema_id']}.provenance.json").read_text())
    assert prov["file_sha256"] == row["file_sha256"] and prov["schema_sha256"] == row["schema_sha256"]
    rep = report(row["row_id"])
    assert rep["schema"]["sha256"] == row["schema_sha256"]
    # ruling Q8: the solver attempts stay within the budget, and only runs without preprocessing are lower bounds
    sb = rep["solver_budget"]
    assert sum(a["seconds"] for a in rep["solver_attempts"]) <= sb["budget_seconds"] + 5 * len(rep["solver_attempts"])
    assert all(not a["used_as"].startswith("lower") for a in rep["solver_attempts"] if a["flags"])
    slots = row["slots"].split(",")
    h = hypergraph(str(f), slots=slots)
    a = classify(h)
    assert a.cls == row["class"] == rep["acyclicity"]["class"]
    assert (a.first_failed or "") == row["first_failed"]
    c = core(h) if a.cls == "cyclic" else None
    assert (c.summary["core_roles"] if c else 0) == int(row["core_roles"])
    assert (c.summary["core_relations"] if c else 0) == int(row["core_relations"])
    jt = rep["acyclicity"].get("join_tree")
    for m in ("hw", "ghw", "fhw", "tw"):
        w = rep["widths"][m]
        cert = w["certificate"]
        assert cert is not None, (row["row_id"], m)
        d = Decomposition.from_json(jt if "ref" in cert else cert)
        v = validate(h, d, kind=KIND[m])
        assert v.ok, (row["row_id"], m, v.failures)
        assert num(m, v.width) == num(m, w["upper"])
        lo, hi = num(m, w["lower"]), num(m, w["upper"])
        assert lo < hi if w["lower_exclusive"] else lo <= hi
        assert w["exact"] == (not w["lower_exclusive"] and lo == hi)
        assert str(w["upper"]) == str(row[f"{m}_upper"])
    if recompute_widths:  # rows that are exact in Python alone (Biolink): the same values again
        again = check(str(f), slots=slots, solver="python", time_limit=float(row["time_limit"]))
        for m in ("hw", "ghw", "fhw", "tw"):
            assert again.widths[m].exact and row[f"{m}_exact"] == "True", (row["row_id"], m)
            assert str(fmt_value(m, again.widths[m].upper)) == row[f"{m}_upper"]


def test_wikidata_rows():
    t = table()
    tables = ("declared", "observed-robust", "observed-all")
    namings = ("wd-roles-r1", "relation-local")
    dump = [f"wd-{tb}-{n}-{s}" for tb in tables for n in namings for s in ("cq", "cqt")]
    assert set(dump) <= set(t), sorted(set(dump) - set(t))
    p3a = {t[r]["counts_source"] for r in dump if r.startswith("wd-observed")} == {"P3a"}
    slice_rows = [f"wd-{tb}-slice-{n}-{s}" for tb in tables[1:] for n in namings for s in ("cq", "cqt")]
    assert (set(slice_rows) <= set(t)) == p3a and (not p3a) == set(slice_rows).isdisjoint(t)
    for rid in dump + (slice_rows if p3a else []):
        row = t[rid]
        assert row["naming_version"] == "wd-roles r1"
        assert row["source"] == "wikidata"
        if "observed" in rid:
            assert row["counts_source"] in ("P3a", "SQID") and row["counts_date"]
            assert row["scope"] == ("slice" if "-slice-" in rid else "dump")
        check_row(row)
        if "relation-local" in rid:
            assert row["class"] == "berge"  # the control: pairwise disjoint relations
            assert all(row[f"{m}_upper"] in ("1", "1/1") for m in ("hw", "ghw", "fhw"))


def test_biolink_rows():
    t = table()
    rows = ["biolink-formal-global-cq", "biolink-formal-domain-global-cq", "biolink-formal-relation-local-cq"]
    assert set(rows) <= set(t)
    for rid in rows:
        check_row(t[rid], recompute_widths=True)
        assert t[rid]["naming_version"].startswith("Biolink Model v4.4.5")


def test_hyperbench_row():
    hb = json.loads((RESULTS / "hyperbench-baseline.json").read_text())
    cq = hb["groups"]["CQ"]
    assert cq["n"] == 1113 and cq["exact_hw"] == {"1": 673, "2": 432, "3": 8}
