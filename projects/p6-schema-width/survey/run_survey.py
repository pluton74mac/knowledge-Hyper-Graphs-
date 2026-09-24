"""The P6 schema width survey (DESIGN §6): generate the schema files, run the rows, build the table.

    python run_survey.py generate [--p3a-counts PATH] [--only wikidata|biolink] [--out RESULTS]
    python run_survey.py run [--rows SELECTION] [--jobs N] [--time-limit 600] [--solver auto] [--out RESULTS]
    python run_survey.py table [--out RESULTS]

``generate`` verifies the dataset manifests (a sha256 mismatch stops it), generates into a temporary directory and
installs the result into ``--out`` (``install``: identical files are left untouched; SQID-based observed files
replaced by P3a-based ones move to ``superseded/`` with their reports; any other difference needs
``--new-snapshot``; the rows of installed files are listed in ``pending-rerun.json``). It writes

- the 6 Wikidata files ``p6-wikidata-<table>-<naming>.json.gz`` (canonical JSON, deterministic gzip with mtime 0;
  3 tables x wd-roles r1 / relation-local), plus the 4 slice files when P3a's counts are given (and the dump-scope
  observed files are then built from P3a's counts too), and ``p3a-crosscheck.json``;
- the 3 Biolink files ``p6-biolink-<qualifiers>-<naming>.json`` (plain canonical JSON);
- ``<name>.provenance.json`` beside each: input hashes, naming version, count source, scope and date, thresholds,
  generator version and source hashes, and the git commit.

``run`` runs ``khg-width FILE --slots ... --time-limit T --solver S --json`` per row into ``reports/<row>.json.gz``
(compact JSON in deterministic gzip, ruling Q6)
(``--jobs N`` rows at a time; each solver call uses ``-cpu 2``). ``--rows`` takes row ids, fnmatch patterns or the
groups ``wikidata``, ``biolink``, ``declared``, ``observed``, ``slice``, ``controls``, ``headline``, ``all``.

``table`` writes ``survey.csv``, ``survey.md``, ``survey.json``, ``figure-data.csv``, ``solver-log.jsonl`` and
``machine.json`` from the reports and ``hyperbench-baseline.json``.

Rows (DESIGN §6.3): 12 Wikidata rows (declared, observed-robust, observed-all; wd-roles r1 and relation-local;
core,qualifier and core,qualifier,time), 8 slice rows when P3a's counts were used, 3 Biolink rows (global formal,
global formal + domain, relation-local formal; core,qualifier) and the HyperBench baseline row.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import fnmatch
import gzip
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
P6 = HERE.parent
REPO = P6.parent.parent
RESULTS = P6 / "results"
WD_DIR = REPO / "datasets" / "knowledge-bases" / "wikidata-property-schemas"
BL_DIR = REPO / "datasets" / "knowledge-bases" / "biolink-model"
SLOTS = {"cq": "core,qualifier", "cqt": "core,qualifier,time"}
SQID_DUMP_DATE = "2026-08-10"
DELTABOT_DATE = "2026-09-23"
WDQS_DATE = "2026-09-24"


# ------------------------------------------------------------------------------------------------ rows
def rows(out: Path) -> list[dict]:
    """Every row the survey knows; slice rows only when their schema files exist."""
    from khg_width.sources import biolink, wikidata

    out_rows = []
    for table in wikidata.TABLES:
        for naming in wikidata.NAMINGS:
            for sk in SLOTS:
                out_rows.append({"row_id": f"wd-{table}-{naming}-{sk}", "group": "wikidata", "table": table,
                                 "naming": naming, "slots": SLOTS[sk], "slice": False,
                                 "file": f"schemas/{wikidata.schema_id(table, naming)}.json.gz",
                                 "control": naming == "relation-local"})
    for table in ("observed-robust", "observed-all"):
        for naming in wikidata.NAMINGS:
            for sk in SLOTS:
                f = f"schemas/{wikidata.schema_id(table, naming, slice_scope=True)}.json.gz"
                if (out / f).exists():
                    out_rows.append({"row_id": f"wd-{table}-slice-{naming}-{sk}", "group": "wikidata",
                                     "table": table, "naming": naming, "slots": SLOTS[sk], "slice": True, "file": f,
                                     "control": naming == "relation-local"})
    for q, n in (("formal", "global"), ("formal-domain", "global"), ("formal", "relation-local")):
        out_rows.append({"row_id": f"biolink-{q}-{n}-cq", "group": "biolink", "table": q, "naming": n,
                         "slots": SLOTS["cq"], "slice": False, "file": f"schemas/{biolink.schema_id(q, n)}.json",
                         "control": n == "relation-local"})
    return out_rows


def select(all_rows: list[dict], spec: str) -> list[dict]:
    if spec in ("", "all"):
        return all_rows
    groups = {
        "wikidata": lambda r: r["group"] == "wikidata", "biolink": lambda r: r["group"] == "biolink",
        "declared": lambda r: r["table"] == "declared", "observed": lambda r: r["table"].startswith("observed"),
        "slice": lambda r: r["slice"], "controls": lambda r: r["control"], "headline": lambda r: not r["control"],
    }
    chosen = []
    for part in spec.split(","):
        part = part.strip()
        for r in all_rows:
            if (part in groups and groups[part](r)) or fnmatch.fnmatch(r["row_id"], part):
                if r not in chosen:
                    chosen.append(r)
    return chosen


# ------------------------------------------------------------------------------------------------ generate
def _git_describe() -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), "describe", "--always", "--dirty", "--abbrev=12"],
                              capture_output=True, text=True, timeout=30).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _source_hashes(*modules: str) -> dict[str, str]:
    import khg_width

    base = Path(khg_width.__file__).parent
    out = {}
    for m in modules:
        p = base / m
        out[f"khg_width/{m}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _write_schema(doc: dict, path: Path, compress: bool) -> tuple[str, str]:
    """Canonical JSON (gzip with mtime 0 when ``compress``); returns (file sha256, C1 schema sha256)."""
    from khg_contracts import jsonio
    from khg_contracts.schema import Schema, check_schema

    findings = check_schema(doc)
    if findings:
        raise SystemExit(f"{doc['id']}: generated schema has findings: {findings[:3]}")
    text = jsonio.canonical(doc)
    data = text.encode("utf-8") if isinstance(text, str) else text
    blob = gzip.compress(data, compresslevel=9, mtime=0) if compress else data + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest(), Schema(doc).sha256


def generate(out: Path, *, p3a: str | None, only: str | None) -> dict[str, Any]:
    from khg_width import __version__
    from khg_width.sources import biolink, manifest, wikidata

    written: dict[str, Any] = {}
    commit = _git_describe()
    if only in (None, "wikidata"):
        hashes = manifest.verify(WD_DIR, wikidata.RAW_FILES)
        raw = wikidata.load(WD_DIR / "raw")
        counts = {}
        if p3a:
            p3a_path = Path(p3a)
            p3a_sha = hashlib.sha256(p3a_path.read_bytes()).hexdigest()
            counts = {"dump": wikidata.read_counts(p3a_path, scope="dump"),
                      "slice": wikidata.read_counts(p3a_path, scope="slice")}
            cc = wikidata.crosscheck_p3a(counts["dump"], raw)
            cc["slice"] = wikidata.crosscheck_p3a(counts["slice"], raw)["mismatches"]
            (out / "p3a-crosscheck.json").write_text(json.dumps(cc, indent=1) + "\n")
        jobs = [(t, n, None) for t in wikidata.TABLES for n in wikidata.NAMINGS]
        if counts:
            jobs = [(t, n, counts["dump"] if t != "declared" else None) for t in wikidata.TABLES
                    for n in wikidata.NAMINGS]
            jobs += [(t, n, counts["slice"]) for t in ("observed-robust", "observed-all") for n in wikidata.NAMINGS]
        for table, naming, c in jobs:
            doc, notes = wikidata.build(None, table, naming, counts=c, raw=raw)
            path = out / "schemas" / f"{doc['id']}.json.gz"
            fsha, ssha = _write_schema(doc, path, compress=True)
            observed = table != "declared"
            prov = {
                "schema_id": doc["id"], "version": doc["version"], "file": f"schemas/{path.name}",
                "file_sha256": fsha, "schema_sha256": ssha, "source": "wikidata", "table": table,
                "naming": naming, "naming_version": wikidata.NAMING_VERSION,
                "scope": (c.scope if c is not None else "dump") if observed else None,
                "counts_source": ("P3a" if c is not None else "SQID") if observed else None,
                "counts_date": ((c.date if c is not None else f"{SQID_DUMP_DATE} (SQID qs); {DELTABOT_DATE} "
                                 f"(DeltaBot main statements)") if observed else None),
                "constraints_date": f"{WDQS_DATE} (WDQS)",
                "thresholds": ({"robust_min_uses": wikidata.ROBUST_MIN_USES,
                                "robust_min_share": wikidata.ROBUST_MIN_SHARE} if table == "observed-robust"
                               else {"min_uses": 1} if table == "observed-all" else None),
                "inputs": {f"datasets/knowledge-bases/wikidata-property-schemas/{k}": v for k, v in hashes.items()},
                "generator": {"khg_width": __version__,
                              "sources": _source_hashes("sources/wikidata.py", "data/wd-roles-r1.json")},
                "commit": commit, "notes": notes,
                "licence": "CC0-1.0 (Wikidata structured data); only numbers are taken from the DeltaBot templates",
            }
            if c is not None:
                prov["inputs"][str(Path(p3a).resolve().relative_to(REPO)) if Path(p3a).resolve().is_relative_to(
                    REPO) else str(p3a)] = p3a_sha
            (out / "schemas" / f"{doc['id']}.provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
            written[doc["id"]] = {"file_sha256": fsha, "schema_sha256": ssha, "relations": notes["relations"],
                                  "roles": notes["roles"]}
            print(f"generate {doc['id']}: {notes['relations']} relations, {notes['roles']} roles, file {fsha[:12]}",
                  file=sys.stderr)
    if only in (None, "biolink"):
        hashes = manifest.verify(BL_DIR, biolink.RAW_FILES)
        rows_ = biolink.extract(BL_DIR / "raw" / "biolink-model.yaml")
        for q, n in (("formal", "global"), ("formal-domain", "global"), ("formal", "relation-local")):
            doc = biolink.build(None, q, n, rows=rows_)
            path = out / "schemas" / f"{doc['id']}.json"
            fsha, ssha = _write_schema(doc, path, compress=False)
            prov = {
                "schema_id": doc["id"], "version": doc["version"], "file": f"schemas/{path.name}",
                "file_sha256": fsha, "schema_sha256": ssha, "source": "biolink", "table": q, "naming": n,
                "naming_version": f"Biolink Model {biolink.VERSION} slot names", "scope": None,
                "counts_source": None, "counts_date": None,
                "biolink": {"version": biolink.VERSION, "commit": biolink.COMMIT},
                "inputs": {f"datasets/knowledge-bases/biolink-model/{k}": v for k, v in hashes.items()},
                "generator": {"khg_width": __version__, "sources": _source_hashes("sources/biolink.py")},
                "commit": commit,
                "licence": "Biolink Model: CC0-1.0 (the model's license field); repository Apache-2.0; credited "
                           "by name and version",
            }
            (out / "schemas" / f"{doc['id']}.provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
            written[doc["id"]] = {"file_sha256": fsha, "schema_sha256": ssha, "relations": len(doc["relations"]),
                                  "roles": len(doc["roles"])}
            print(f"generate {doc['id']}: {len(doc['relations'])} relations, file {fsha[:12]}", file=sys.stderr)
    return written


PENDING = "pending-rerun.json"


def load_pending(out: Path) -> dict[str, str]:
    """Rows whose report is known stale (their schema file changed, or the checker changed under them) and must be
    re-run: ``{row_id: reason}``. ``run`` clears a row when it re-runs it; the file goes when it is empty."""
    p = out / PENDING
    return json.loads(p.read_text())["rows"] if p.exists() else {}


def _save_pending(out: Path, pend: dict[str, str]) -> None:
    p = out / PENDING
    if pend:
        p.write_text(json.dumps({"note": "rows to re-run with run_survey.py run; see IMPLEMENTATION-NOTES.md",
                                 "rows": dict(sorted(pend.items()))}, indent=1) + "\n")
    elif p.exists():
        p.unlink()


def add_pending(out: Path, rows_: dict[str, str]) -> None:
    pend = load_pending(out)
    pend.update(rows_)
    _save_pending(out, pend)


def clear_pending(out: Path, row_ids: list[str]) -> None:
    pend = load_pending(out)
    for r in row_ids:
        pend.pop(r, None)
    _save_pending(out, pend)


def _rows_of(out: Path, schema_id: str) -> list[str]:
    return [r["row_id"] for r in rows(out) if Path(r["file"]).name.split(".json")[0] == schema_id]


def install(src: Path, out: Path, *, new_snapshot: bool = False) -> dict[str, list[str]]:
    """Install the schema files generated into ``src`` into the results ``out`` (DESIGN §6.6; review F3, F4):

    - identical to the committed file (file and C1 schema sha256): nothing is touched, provenance included (F4);
    - a new file: installed;
    - an SQID-based observed file replaced by a P3a-based one (P3a's counts landed): expected; the SQID-based schema,
      its provenance and the reports of its rows move to ``out/superseded/`` (F3);
    - any other difference: refused (nothing is touched) unless ``new_snapshot``, which replaces it.

    Every row whose schema file is installed is listed in ``pending-rerun.json``."""
    plan: list[tuple[str, dict, dict | None]] = []
    summary: dict[str, list[str]] = {"unchanged": [], "new": [], "superseded": [], "replaced": []}
    refused = []
    for prov in sorted((src / "schemas").glob("*.provenance.json")):
        p = json.loads(prov.read_text())
        old = out / "schemas" / prov.name
        if not old.exists():
            plan.append(("new", p, None))
            continue
        q = json.loads(old.read_text())
        if (q["file_sha256"], q["schema_sha256"]) == (p["file_sha256"], p["schema_sha256"]):
            summary["unchanged"].append(p["schema_id"])
        elif q.get("counts_source") == "SQID" and p.get("counts_source") == "P3a":
            plan.append(("superseded", p, q))
        elif new_snapshot:
            plan.append(("replaced", p, q))
        else:
            refused.append(p["schema_id"])
    if refused:
        raise SystemExit("generated schemas differ from the committed ones: " + ", ".join(refused)
                         + "\n(rerun with --new-snapshot to replace them)")
    (out / "schemas").mkdir(parents=True, exist_ok=True)
    sup = out / "superseded"
    pending: dict[str, str] = {}
    for action, p, q in plan:
        sid = p["schema_id"]
        if action == "superseded":
            sup.mkdir(parents=True, exist_ok=True)
            for rid in _rows_of(out, sid):
                for f in (out / "reports").glob(f"{rid}.*"):
                    shutil.move(str(f), str(sup / f.name))
            for f in (out / q["file"], out / "schemas" / f"{sid}.provenance.json"):
                if f.exists():
                    shutil.move(str(f), str(sup / f.name))
        for f in (src / p["file"], src / "schemas" / f"{sid}.provenance.json"):
            shutil.copy2(f, out / "schemas" / f.name)
        summary[action].append(sid)
        reason = {"new": "new schema file", "superseded": "rebuilt from P3a's counts (the SQID-based row moved to "
                  "superseded/)", "replaced": "schema file replaced (--new-snapshot)"}[action]
        for rid in _rows_of(out, sid):
            pending[rid] = reason
    if (src / "p3a-crosscheck.json").exists():
        shutil.copy2(src / "p3a-crosscheck.json", out / "p3a-crosscheck.json")
    add_pending(out, pending)
    return summary


# ------------------------------------------------------------------------------------------------ run
def write_report(path: Path, rep: dict) -> None:
    """Ruling Q6: a report is compact JSON (keys in the report's order) in deterministic gzip (mtime 0, level 9)."""
    data = (json.dumps(rep, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(gzip.compress(data, compresslevel=9, mtime=0))


def read_report(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))


def run_row(row: dict, out: Path, *, time_limit: float, solver: str) -> dict:
    rep_dir = out / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "khg_width", str(out / row["file"]), "--slots", row["slots"], "--time-limit",
           str(time_limit), "--solver", solver, "--json"]
    t0 = time.monotonic()
    r = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.monotonic() - t0
    (rep_dir / f"{row['row_id']}.log").write_text("$ " + " ".join(cmd[1:]) + "\n" + r.stderr)
    if r.returncode != 0:
        return {"row_id": row["row_id"], "status": r.returncode, "wall_seconds": wall, "error": r.stderr[-2000:]}
    rep = json.loads(r.stdout)
    rep["survey"] = {"row_id": row["row_id"], "command": ["khg-width"] + cmd[3:], "wall_seconds": round(wall, 3)}
    write_report(rep_dir / f"{row['row_id']}.json.gz", rep)
    return {"row_id": row["row_id"], "status": 0, "wall_seconds": wall}


def run(out: Path, spec: str, *, jobs: int, time_limit: float, solver: str) -> list[dict]:
    chosen = select(rows(out), spec)
    missing = [r["row_id"] for r in chosen if not (out / r["file"]).exists()]
    if missing:
        raise SystemExit(f"schema files missing for {missing}: run `run_survey.py generate` first")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = {ex.submit(run_row, r, out, time_limit=time_limit, solver=solver): r for r in chosen}
        for f in concurrent.futures.as_completed(futs):
            res = f.result()
            results.append(res)
            print(f"row {res['row_id']}: status {res['status']}, {res['wall_seconds']:.1f} s", file=sys.stderr)
    clear_pending(out, [r["row_id"] for r in results if r["status"] == 0])
    return results


# ------------------------------------------------------------------------------------------------ table
MEASURES = ("hw", "ghw", "fhw", "tw")
COLUMNS = (["row_id", "source", "scope", "counts_source", "counts_date", "naming", "naming_version", "slots",
            "schema_id", "schema_sha256", "file", "file_sha256",
            "relations", "roles", "rank", "max_degree", "bip", "duplicate_groups", "universal_roles", "components",
            "class", "first_failed", "witness_kind", "witness_size", "core_roles", "core_relations"]
           + [f"{m}_{x}" for m in MEASURES for x in ("lower", "upper", "exact", "method")]
           + ["validated", "disagreements", "tools", "solver_attempts", "solver_seconds", "time_limit",
              "wall_seconds"])


def _witness_size(w: dict | None) -> int | str:
    if not w:
        return ""
    if w["kind"] in ("berge_cycle", "beta_cycle"):
        return len(w["value"]) // 2
    if w["kind"] == "gamma_triangle":
        return 3
    return len(w["value"])


def table_row(row: dict, rep: dict, prov: dict) -> dict:
    st, acy, ws = rep["stats"], rep["acyclicity"], rep["widths"]
    out = {
        "row_id": row["row_id"], "source": prov.get("source"), "scope": prov.get("scope") or "",
        "counts_source": prov.get("counts_source") or "", "counts_date": prov.get("counts_date") or "",
        "naming": row["naming"], "naming_version": prov.get("naming_version"), "slots": row["slots"],
        "schema_id": rep["schema"]["id"], "schema_sha256": rep["schema"]["sha256"], "file": row["file"],
        "file_sha256": rep["schema"]["file_sha256"],
        "relations": st["relations"], "roles": st["roles"], "rank": st["rank"], "max_degree": st["max_degree"],
        "bip": st["bip"], "duplicate_groups": len(st["duplicate_groups"]),
        "universal_roles": ";".join(st["universal_roles"]), "components": st["components"],
        "class": acy["class"], "first_failed": acy["first_failed"] or "",
        "witness_kind": (acy["witness"] or {}).get("kind", ""), "witness_size": _witness_size(acy["witness"]),
        "core_roles": st.get("core_roles", 0), "core_relations": st.get("core_relations", 0),
        "validated": all((ws[m]["validation"] or {}).get("ok") for m in MEASURES),
        "disagreements": len(rep["disagreements"]),
        "tools": ";".join(f"{k}:{(v.get('commit') or '')[:7]}" for k, v in rep["tools"].items()
                          if isinstance(v, dict) and "sha256" in v) or "python",
        "solver_attempts": len(rep.get("solver_attempts", [])),
        "solver_seconds": (rep.get("solver_budget") or {}).get("used_seconds", 0),
        "time_limit": rep["time_limit"], "wall_seconds": rep.get("survey", {}).get("wall_seconds",
                                                                                 rep["wall_seconds"]),
    }
    for m in MEASURES:
        w = ws[m]
        out[f"{m}_lower"] = w["lower"] if not w["lower_exclusive"] else f">{w['lower']}"
        out[f"{m}_upper"] = w["upper"]
        out[f"{m}_exact"] = w["exact"]
        out[f"{m}_method"] = w["upper_method"] if w["exact"] else f"{w['lower_method']}/{w['upper_method']}"
    return out


def _show(r: dict, m: str) -> str:
    if r[f"{m}_exact"] in (True, "True"):
        return str(r[f"{m}_upper"])
    lo = str(r[f"{m}_lower"])
    return f"({lo[1:]}, {r[f'{m}_upper']}]" if lo.startswith(">") else f"[{lo}, {r[f'{m}_upper']}]"


def table(out: Path) -> list[dict]:
    trs = []
    reports = {}
    for row in rows(out):
        rp = out / "reports" / f"{row['row_id']}.json.gz"
        if not rp.exists():
            continue
        rep = read_report(rp)
        prov = json.loads((out / "schemas" / f"{rep['schema']['id']}.provenance.json").read_text())
        reports[row["row_id"]] = rep
        trs.append(table_row(row, rep, prov))
    with open(out / "survey.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in trs:
            w.writerow(r)
    hb = None
    if (out / "hyperbench-baseline.json").exists():
        hb = json.loads((out / "hyperbench-baseline.json").read_text())
    md = ["# P6 schema width survey", "",
          "| row | source | naming | slots | relations / roles | class (witness) | core (relations / roles) "
          "| hw | ghw | fhw | tw |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in trs:
        wit = f"{r['witness_kind']} {r['witness_size']}".strip() or "join tree"
        md.append(f"| {r['row_id']} | {r['source']}{' ' + r['scope'] if r['scope'] else ''} | {r['naming']} "
                  f"| {r['slots']} | {r['relations']} / {r['roles']} | {r['class']} ({wit}) "
                  f"| {r['core_relations']} / {r['core_roles']} | {_show(r, 'hw')} | {_show(r, 'ghw')} "
                  f"| {_show(r, 'fhw')} | {_show(r, 'tw')} |")
    if hb:
        cq = hb["groups"]["CQ"]
        md.append(f"| hyperbench-cq | HyperBench (Zenodo 10.5281/zenodo.7180787) | n/a | n/a | {cq['n']} CQs | "
                  f"selected to be cyclic | n/a | hw 1 / 2 / 3 = "
                  f"{' / '.join(str(cq['exact_hw'].get(str(k), 0)) for k in (1, 2, 3))} | | | |")
    md += ["", "Values are exact (`2`) or bounds (`[2, 4]`, `(1, 3/2]` for fhw > 1). The HyperBench row counts "
           "non-random CQs, which were selected to be cyclic; compare by structural parameter and hw (R01 §3.6)."]
    (out / "survey.md").write_text("\n".join(md) + "\n")
    (out / "survey.json").write_text(json.dumps({"rows": trs, "hyperbench": hb}, indent=1) + "\n")
    # figure data
    with open(out / "figure-data.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["row_id", "group", "table", "naming", "slots", "control", "hw_lower", "hw_upper", "hw_exact",
                    "residue_relations", "residue_roles"])
        for row in rows(out):
            rep = reports.get(row["row_id"])
            if rep is None:
                continue
            res = rep["acyclicity"].get("gyo_residue_size") or {"relations": 0, "roles": 0}
            hwv = rep["widths"]["hw"]
            w.writerow([row["row_id"], row["group"], row["table"] + ("-slice" if row["slice"] else ""),
                        row["naming"], row["slots"], row["control"], hwv["lower"], hwv["upper"], hwv["exact"],
                        res["relations"], res["roles"]])
        if hb:
            for k, v in sorted(hb["groups"]["CQ"]["exact_hw"].items()):
                w.writerow([f"hyperbench-cq-hw{k}", "hyperbench", "CQ", "", "", False, k, k, True, v, ""])
    # solver log and machine
    with open(out / "solver-log.jsonl", "w", encoding="utf-8") as fh:
        for rid, rep in sorted(reports.items()):
            for a in rep.get("solver_attempts", []):
                fh.write(json.dumps({"row_id": rid, "record": "attempt", **a}, ensure_ascii=False) + "\n")
            for d in rep["disagreements"]:
                fh.write(json.dumps({"row_id": rid, "record": "disagreement", **d}, ensure_ascii=False) + "\n")
    machine = {"platform": platform.platform(), "python": platform.python_version(), "cpus": os.cpu_count(),
               "processor": platform.processor() or platform.machine(),
               "tools": next((rep["tools"] for rep in reports.values()), {})}
    (out / "machine.json").write_text(json.dumps(machine, indent=1) + "\n")
    return trs


# ------------------------------------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--p3a-counts", default=None)
    g.add_argument("--only", choices=("wikidata", "biolink"))
    g.add_argument("--out", default=str(RESULTS))
    g.add_argument("--new-snapshot", action="store_true", dest="new_snapshot",
                   help="replace committed schema files that differ (a new WDQS snapshot)")
    ins = sub.add_parser("install")
    ins.add_argument("--from", dest="src", required=True)
    ins.add_argument("--out", default=str(RESULTS))
    ins.add_argument("--new-snapshot", action="store_true", dest="new_snapshot")
    pe = sub.add_parser("pending")
    pe.add_argument("--out", default=str(RESULTS))
    pe.add_argument("--add", default="", help="rows (ids, patterns or groups) to mark for a re-run")
    pe.add_argument("--reason", default="")
    r = sub.add_parser("run")
    r.add_argument("--rows", default="all")
    r.add_argument("--jobs", type=int, default=1)
    r.add_argument("--time-limit", type=float, default=600.0)
    r.add_argument("--solver", default="auto", choices=("auto", "python", "balancedgo", "logk"))
    r.add_argument("--out", default=str(RESULTS))
    t = sub.add_parser("table")
    t.add_argument("--out", default=str(RESULTS))
    ls = sub.add_parser("rows")
    ls.add_argument("--out", default=str(RESULTS))
    ls.add_argument("--rows", default="all")
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.cmd == "generate":
        import tempfile

        with tempfile.TemporaryDirectory(prefix="p6-generate-") as tmp:
            written = generate(Path(tmp), p3a=a.p3a_counts, only=a.only)
            summary = install(Path(tmp), out, new_snapshot=a.new_snapshot)
        print(json.dumps({"generated": written, "install": summary}, indent=1))
    elif a.cmd == "install":
        print(json.dumps(install(Path(a.src), out, new_snapshot=a.new_snapshot), indent=1))
    elif a.cmd == "pending":
        if a.add:
            add_pending(out, {r: a.reason for r in [x["row_id"] for x in select(rows(out), a.add)]})
        print(json.dumps(load_pending(out), indent=1))
    elif a.cmd == "run":
        res = run(out, a.rows, jobs=a.jobs, time_limit=a.time_limit, solver=a.solver)
        print(json.dumps(sorted(res, key=lambda x: x["row_id"]), indent=1))
        return 0 if all(x["status"] == 0 for x in res) else 1
    elif a.cmd == "table":
        trs = table(out)
        print(f"{len(trs)} rows -> {out / 'survey.csv'}", file=sys.stderr)
    else:
        for row in select(rows(out), a.rows):
            print(row["row_id"], row["file"], row["slots"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
