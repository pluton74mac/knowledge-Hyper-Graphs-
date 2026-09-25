"""G1: the survey table (DESIGN §1, §6). Marked ``survey``: skipped until results/survey.csv exists.

- ``test_wikidata_rows``: the 12 dump-scope rows are present, and the 8 slice rows exactly when the counts came from
  P3a; every schema file's sha256 matches the table and its provenance; the class and the core are recomputed; the
  stored certificates re-validate on H; the bounds are consistent; the naming version is wd-roles r1.
- ``test_biolink_rows``: the 3 Biolink rows are recomputed with ``--solver python``.
- ``test_hyperbench_row``: the baseline row is the published one (n = 1,113; hw 1/2/3 = 673/432/8).

Every checked row also has each lower, upper, exact and method cell equal to its report, and its survey.md line equal
to one rendered here from the report (F5); reports of format ``khg-width-report/0.2.0`` carry a witness for every
lower bound, each checked on H (F9). Rows listed in ``results/pending-rerun.json`` (their schema file or the checker
changed after they ran; ``run_survey.py run`` clears them) are not checked until they re-run.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from fractions import Fraction

import pytest

from helpers import RESULTS, check_lower_witness
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


def pending() -> dict[str, str]:
    p = RESULTS / "pending-rerun.json"
    return json.loads(p.read_text())["rows"] if p.exists() else {}


def md_lines() -> dict[str, str]:
    lines = (RESULTS / "survey.md").read_text(encoding="utf-8").splitlines()
    return {ln.split("|")[1].strip(): ln for ln in lines if ln.startswith("| ") and not ln.startswith("| row ")}


def show(m: str, w: dict) -> str:
    """A width as survey.md shows it, rendered here from the report: 3, [2, 4] or (1, 3/2]."""
    if w["exact"]:
        return str(w["upper"])
    return f"({w['lower']}, {w['upper']}]" if w["lower_exclusive"] else f"[{w['lower']}, {w['upper']}]"


def expected_md(row: dict, rep: dict) -> str:
    st, acy = rep["stats"], rep["acyclicity"]
    wk = acy["witness"]
    if wk is None:
        wit = "join tree"
    else:
        size = len(wk["value"]) // 2 if wk["kind"] in ("berge_cycle", "beta_cycle") else (
            3 if wk["kind"] == "gamma_triangle" else len(wk["value"]))
        wit = f"{wk['kind']} {size}"
    source = row["source"] + (f" {row['scope']}" if row["scope"] else "")
    cells = [row["row_id"], source, row["naming"], ",".join(rep["slots"]), f"{st['relations']} / {st['roles']}",
             f"{acy['class']} ({wit})", f"{st.get('core_relations', 0)} / {st.get('core_roles', 0)}"]
    cells += [show(m, rep["widths"][m]) for m in ("hw", "ghw", "fhw", "tw")]
    return "| " + " | ".join(cells) + " |"


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
        # F5: every width cell of the table is the report's
        assert str(w["upper"]) == row[f"{m}_upper"]
        assert (f">{w['lower']}" if w["lower_exclusive"] else str(w["lower"])) == row[f"{m}_lower"]
        assert str(w["exact"]) == row[f"{m}_exact"]
        want = w["upper_method"] if w["exact"] else f"{w['lower_method']}/{w['upper_method']}"
        assert want == row[f"{m}_method"], (row["row_id"], m)
        # F9: the witness of every lower bound checks out on H (reports that record them)
        if rep["format"] >= "khg-width-report/0.2.0":
            check_lower_witness(h, m, w, rep["acyclicity"])
        else:
            assert rep["format"] == "khg-width-report/0.1.0" and "lower_witness" not in w
    for col, key in (("relations", "relations"), ("roles", "roles"), ("rank", "rank"), ("bip", "bip"),
                     ("max_degree", "max_degree"), ("components", "components")):
        assert row[col] == str(rep["stats"][key]), (row["row_id"], col)
    assert md_lines()[row["row_id"]] == expected_md(row, rep)
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
    pend = pending()
    assert set(dump) - set(pend) <= set(t), sorted(set(dump) - set(t))
    p3a = {t[r]["counts_source"] for r in dump if r.startswith("wd-observed")} == {"P3a"}
    slice_rows = [f"wd-{tb}-slice-{n}-{s}" for tb in tables[1:] for n in namings for s in ("cq", "cqt")]
    assert (set(slice_rows) <= set(t)) == p3a and (not p3a) == set(slice_rows).isdisjoint(t)
    for rid in dump + (slice_rows if p3a else []):
        if rid in pend:
            assert pend[rid], rid  # listed with its reason; checked once it re-runs
            continue
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
    pend = pending()
    assert set(rows) - set(pend) <= set(t)
    for rid in (r for r in rows if r not in pend):
        check_row(t[rid], recompute_widths=True)
        assert t[rid]["naming_version"].startswith("Biolink Model v4.4.5")


def test_hyperbench_row():
    hb = json.loads((RESULTS / "hyperbench-baseline.json").read_text())
    cq = hb["groups"]["CQ"]
    assert cq["n"] == 1113 and cq["exact_hw"] == {"1": 673, "2": 432, "3": 8}
