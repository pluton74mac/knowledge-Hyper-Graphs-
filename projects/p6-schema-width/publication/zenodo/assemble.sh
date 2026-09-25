#!/usr/bin/env bash
# assemble.sh: stage the P6 Zenodo deposit in a directory outside git. It uploads nothing.
#
#   projects/p6-schema-width/publication/zenodo/assemble.sh [--dest DIR] [--with-sqid] [--with-deltabot]
#                                                          [--final] [--force] [--list]
#
#   --dest DIR       staging directory; must be outside the git working tree (default /tmp/khg-p6-zenodo)
#   --with-sqid      also deposit raw/sqid-properties.json and raw/sqid-statistics.json. SQID states no licence for
#                    these data files, and DESIGN §6.1 says they are used, not redistributed (RELEASE.md, D1)
#   --with-deltabot  also deposit the three DeltaBot template snapshots (Wikidata Template namespace, recorded in
#                    DESIGN §6.1 as CC BY-SA 3.0, so not CC0) (RELEASE.md, D1)
#   --final          refuse, instead of warning, when the deposit would be provisional: an observed row still on SQID
#                    counts, rows pending a re-run, or a deposited tracked file that differs from HEAD or is untracked
#   --force          replace a staging directory this script made earlier
#   --list           print the files the script expects, and exit
#
# What it deposits (paths relative to the repository root):
#   1. raw snapshots, from the gitignored raw/ folders, each verified against the sha256 in its MANIFEST.json:
#      - datasets/knowledge-bases/wikidata-property-schemas/raw/: the 33 WDQS result files (CC0);
#        with --with-deltabot the 3 DeltaBot templates; with --with-sqid the 2 SQID files;
#      - datasets/knowledge-bases/biolink-model/raw/: biolink-model.yaml, attributes.yaml, LICENSE (v4.4.5);
#   2. the manifests: wikidata-property-schemas, biolink-model, wikidata (the 2026-09-22 dump; file not deposited),
#      hypergraph-benchmarks/hyperbench (the HyperBench run data; files not deposited, CC BY 4.0, on Zenodo);
#   3. every tracked file under projects/p6-schema-width/results/ except results/superseded/: the generated schema
#      files with provenance, the per-row reports and logs, survey.{csv,md,json}, the figure, the baseline, the logs;
#   4. projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json, when it is tracked (after the P3a-count re-run);
#   5. README.md (from this folder, with the commit filled in), PROVENANCE.txt and SHA256SUMS, generated here.
# Not deposited: GO-CAM (placeholder licence, not in the survey), the 103 GB Wikidata dump, the HyperBench zips,
# sqid-properties.headers.txt (not in the manifest), processed/ folders, and results/superseded/.
#
# Output:
#   DEST/files/khg-p6-deposit/   the deposit tree (for inspection)
#   DEST/upload/                 the two files to upload: README.md and khg-p6-schema-width-deposit.zip
#                                (the zip holds khg-p6-deposit/ with every file above; deterministic order and dates)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
DEST="/tmp/khg-p6-zenodo"
WITH_SQID=0; WITH_DELTABOT=0; FINAL=0; FORCE=0; LIST=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dest) DEST="${2:?assemble: --dest needs a directory}"; shift 2 ;;
    --with-sqid) WITH_SQID=1; shift ;;
    --with-deltabot) WITH_DELTABOT=1; shift ;;
    --final) FINAL=1; shift ;;
    --force) FORCE=1; shift ;;
    --list) LIST=1; shift ;;
    -h|--help) sed -n '2,38p' "$0"; exit 0 ;;
    *) echo "assemble: unknown option $1 (see --help)" >&2; exit 2 ;;
  esac
done
command -v python3 >/dev/null || { echo "assemble: python3 is required" >&2; exit 2; }
export HERE REPO DEST WITH_SQID WITH_DELTABOT FINAL FORCE LIST
exec python3 - <<'PYEOF'
import csv
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(os.environ["REPO"]).resolve()
HERE = Path(os.environ["HERE"]).resolve()
DEST = Path(os.path.abspath(os.path.expanduser(os.environ["DEST"])))
OPT = {k: os.environ[k] == "1" for k in ("WITH_SQID", "WITH_DELTABOT", "FINAL", "FORCE", "LIST")}

REPO_URL = "https://github.com/pluton74mac/knowledge-Hyper-Graphs-"
P6 = "projects/p6-schema-width"
WD = "datasets/knowledge-bases/wikidata-property-schemas"
BL = "datasets/knowledge-bases/biolink-model"
TOP = "khg-p6-deposit"
ZIP_NAME = "khg-p6-schema-width-deposit.zip"
P3A_COUNTS = "projects/p3a-clean-nary-corpus/qualifier-usage-20260922.json"
MANIFESTS = [f"{WD}/MANIFEST.json", f"{BL}/MANIFEST.json", "datasets/knowledge-bases/wikidata/MANIFEST.json",
             "datasets/hypergraph-benchmarks/hyperbench/MANIFEST.json"]

# The raw files this script expects, by group. Every file in the Wikidata manifest must be in exactly one group.
WDQS = [f"raw/{n}.srj.json" for n in (
    "allowed_qualifiers", "properties", "property_instance_of", "property_scope", "qualifier_classes",
    "required_qualifiers", "subject_type_constraints", "value_type_constraints")] + [
    f"raw/usage_{p}_{part}.srj.json" for p in ("P39", "P69", "P108", "P166", "P54")
    for part in ("statements", "slice0", "slice450000", "slice900000", "slice1350000")]
DELTABOT = ["raw/usage_main_statements.wikitext", "raw/usage_as_qualifier.wikitext", "raw/usage_in_references.wikitext"]
SQID = ["raw/sqid-properties.json", "raw/sqid-statistics.json"]
BIOLINK = ["raw/biolink-model.yaml", "raw/attributes.yaml", "raw/LICENSE"]
GROUPS = [  # (label, dataset dir, files, included?)
    ("WDQS query results of 2026-09-24 (CC0-1.0)", WD, WDQS, True),
    ("DeltaBot count templates, revisions of 2026-09-23 (CC BY-SA 3.0; --with-deltabot)", WD, DELTABOT,
     OPT["WITH_DELTABOT"]),
    ("SQID statistics, dump of 2026-08-10 (licence not stated; --with-sqid)", WD, SQID, OPT["WITH_SQID"]),
    ("Biolink Model v4.4.5 sources (model CC0-1.0; repository LICENSE Apache-2.0)", BL, BIOLINK, True),
]


def die(msg: str, code: int = 1) -> None:
    print(f"assemble: {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str) -> None:
    print(f"assemble: WARNING: {msg}", file=sys.stderr)


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked(prefix: str) -> list[str]:
    return sorted(p for p in git("ls-files", "-z", "--", prefix).split("\0") if p)


# ---- 1. what is expected -------------------------------------------------------------------------------------
results = [p for p in tracked(f"{P6}/results") if not p.startswith(f"{P6}/results/superseded/")]
p3a = [P3A_COUNTS] if tracked(P3A_COUNTS) else []

if OPT["LIST"]:
    for label, d, files, inc in GROUPS:
        print(f"{'deposit' if inc else 'skip   '}  {label}: {len(files)} files in {d}/")
        for f in files:
            print(f"           {d}/{f}")
    print(f"deposit  manifests: {len(MANIFESTS)}")
    for m in MANIFESTS:
        print(f"           {m}")
    print(f"deposit  tracked results under {P6}/results/ (without superseded/): {len(results)} files")
    print(f"{'deposit' if p3a else 'absent '}  P3a qualifier-usage counts: {P3A_COUNTS}")
    print("deposit  README.md (from publication/zenodo/), PROVENANCE.txt, SHA256SUMS (generated)")
    sys.exit(0)

# ---- 2. manifests: every expected file listed; every listed file expected; raw files present and matching -----
manifest = {}
for d in (WD, BL):
    try:
        manifest[d] = {f["path"]: f for f in json.loads((REPO / d / "MANIFEST.json").read_text())["files"]}
    except (OSError, ValueError, KeyError) as e:
        die(f"cannot read {d}/MANIFEST.json: {e}")
expected = {WD: WDQS + DELTABOT + SQID, BL: BIOLINK}
for d, names in expected.items():
    if set(names) - set(manifest[d]):
        die(f"{d}/MANIFEST.json does not list: {', '.join(sorted(set(names) - set(manifest[d])))}")
    if set(manifest[d]) - set(names):
        die(f"{d}/MANIFEST.json lists files this script does not classify: "
            f"{', '.join(sorted(set(manifest[d]) - set(names)))}; update the groups in assemble.sh")
for m in MANIFESTS:
    if not (REPO / m).is_file():
        die(f"missing manifest {m}")

raw = []  # (repo-relative path, manifest sha256)
problems = []
for label, d, files, inc in GROUPS:
    if not inc:
        continue
    for f in files:
        entry = manifest[d][f]
        p = REPO / d / f
        if not p.is_file():
            problems.append(f"{d}/{f}: missing (fetch: {entry.get('source_url', 'see the manifest')})")
        elif sha256(p) != entry.get("sha256"):
            problems.append(f"{d}/{f}: sha256 differs from the manifest's {entry.get('sha256')}")
        else:
            raw.append((f"{d}/{f}", entry["sha256"]))
if problems:
    die("raw files do not match their manifests:\n  " + "\n  ".join(problems))
print(f"assemble: {len(raw)} raw files verified against their manifests")

# ---- 3. is this the final state? ------------------------------------------------------------------------------
reasons = []
survey_csv = REPO / P6 / "results" / "survey.csv"
rows = list(csv.DictReader(survey_csv.open())) if survey_csv.is_file() else []
if not rows:
    die(f"{P6}/results/survey.csv is missing or empty")
sqid_rows = [r["row_id"] for r in rows if r.get("counts_source") == "SQID"]
p3a_rows = [r["row_id"] for r in rows if r.get("counts_source") == "P3a"]
slice_rows = [r["row_id"] for r in rows if r.get("scope") == "slice"]
if sqid_rows:
    reasons.append(f"{len(sqid_rows)} observed rows still use SQID counts (provisional until the P3a-count re-run)")
if p3a_rows and not slice_rows:
    reasons.append("observed rows use P3a's counts but survey.csv has no slice rows")
if (REPO / P6 / "results" / "pending-rerun.json").exists():
    reasons.append("results/pending-rerun.json lists rows waiting for a re-run")
if p3a_rows and not p3a:
    reasons.append(f"observed rows use P3a's counts but {P3A_COUNTS} is not tracked")
readme_rel = str((HERE / "README.md").relative_to(REPO))
deposited_tracked = MANIFESTS + results + p3a + [readme_rel]
dirty = [line[3:] for line in git("status", "--porcelain", "--untracked-files=all", "--", *deposited_tracked,
                                  str(HERE / "README.md")).splitlines() if line.strip()]
if dirty:
    reasons.append(f"{len(dirty)} deposited file(s) differ from HEAD or are untracked: {', '.join(sorted(set(dirty)))}")
untracked_results = [p for p in git("ls-files", "--others", "--exclude-standard", "--", f"{P6}/results").splitlines()
                     if p]
if untracked_results:
    warn(f"untracked files under results/ are not deposited: {', '.join(untracked_results)}")
for r in reasons:
    (die if OPT["FINAL"] else warn)(("not final: " if OPT["FINAL"] else "provisional: ") + r)
status = "final" if not reasons else "DRAFT (" + "; ".join(reasons) + ")"

# ---- 4. the staging directory ---------------------------------------------------------------------------------
if DEST == Path("/") or DEST == Path.home() or str(DEST) in ("", "."):
    die(f"refusing --dest {DEST}")
try:
    DEST.relative_to(REPO)
    die(f"--dest {DEST} is inside the git working tree {REPO}; choose a directory outside it", 2)
except ValueError:
    pass
marker = DEST / ".khg-p6-deposit"
if DEST.exists() and any(DEST.iterdir()):
    if not marker.is_file():
        die(f"{DEST} exists, is not empty and was not made by this script")
    if not OPT["FORCE"]:
        die(f"{DEST} exists; pass --force to replace it")
    for sub in ("files", "upload"):
        shutil.rmtree(DEST / sub, ignore_errors=True)
DEST.mkdir(parents=True, exist_ok=True)
marker.write_text("staging directory of projects/p6-schema-width/publication/zenodo/assemble.sh\n")
tree = DEST / "files" / TOP
upload = DEST / "upload"
tree.mkdir(parents=True)
upload.mkdir(parents=True)

# ---- 5. copy, re-verify, describe ----------------------------------------------------------------------------
copied = {}  # tree-relative path -> sha256
for rel, want in raw:
    dst = tree / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / rel, dst)
    got = sha256(dst)
    if got != want:
        die(f"copy of {rel} does not match the manifest")
    copied[rel] = got
for rel in MANIFESTS + results + p3a:
    dst = tree / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / rel, dst)
    copied[rel] = sha256(dst)

head = git("rev-parse", "HEAD").strip()
head_date = git("show", "-s", "--format=%cI", "HEAD").strip()
branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
optional = [n for n, on in (("SQID statistics (2 files)", OPT["WITH_SQID"]),
                            ("DeltaBot templates (3 files)", OPT["WITH_DELTABOT"])) if on]
banner = "" if not reasons else (
    "> **DRAFT STAGING COPY: DO NOT UPLOAD.** It was assembled without `--final` and is provisional: "
    + "; ".join(reasons) + ".\n")
readme = (HERE / "README.md").read_text(encoding="utf-8")
for key, val in (("@STATUS_BANNER@", banner), ("@COMMIT@", head),
                 ("@OPTIONAL@", ", ".join(optional) if optional else "none (assembled without --with-sqid and "
                                                                    "--with-deltabot)")):
    readme = readme.replace(key, val)
readme = readme.lstrip("\n")
(tree / "README.md").write_text(readme, encoding="utf-8")
copied["README.md"] = sha256(tree / "README.md")

counts = {"SQID": len(sqid_rows), "P3a": len(p3a_rows)}
prov = [
    "deposit: P6 schema width survey (projects/p6-schema-width)",
    f"repository: {REPO_URL}",
    f"commit: {head} ({head_date}), branch {branch}",
    f"assembled: {datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()}",
    f"status: {status}",
    f"options: --with-sqid={'yes' if OPT['WITH_SQID'] else 'no'} --with-deltabot={'yes' if OPT['WITH_DELTABOT'] else 'no'}"
    f" --final={'yes' if OPT['FINAL'] else 'no'}",
    f"observed rows by count source: SQID {counts['SQID']}, P3a {counts['P3a']}; slice rows {len(slice_rows)}",
    f"raw files verified against manifests: {len(raw)}",
    f"P3a qualifier-usage counts: {'included' if p3a else 'not present at this commit'}",
    "not deposited: GO-CAM schema; Wikidata dump 2026-09-22 (manifest only); HyperBench zips (manifest only, "
    "https://doi.org/10.5281/zenodo.7180787); sqid-properties.headers.txt; processed/; results/superseded/",
]
(tree / "PROVENANCE.txt").write_text("\n".join(prov) + "\n", encoding="utf-8")
copied["PROVENANCE.txt"] = sha256(tree / "PROVENANCE.txt")
(tree / "SHA256SUMS").write_text("".join(f"{h}  {p}\n" for p, h in sorted(copied.items())), encoding="utf-8")

# exactly the listed files, nothing else
on_disk = sorted(str(p.relative_to(tree)) for p in tree.rglob("*") if p.is_file())
if on_disk != sorted(list(copied) + ["SHA256SUMS"]):
    die("the staging tree does not hold exactly the listed files")

# ---- 6. the upload: README.md and one deterministic zip -------------------------------------------------------
STORED = (".gz", ".png", ".zip")
with zipfile.ZipFile(upload / ZIP_NAME, "w") as z:
    for rel in on_disk:
        info = zipfile.ZipInfo(f"{TOP}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_STORED if rel.endswith(STORED) else zipfile.ZIP_DEFLATED
        z.writestr(info, (tree / rel).read_bytes(), compresslevel=9 if info.compress_type else None)
with zipfile.ZipFile(upload / ZIP_NAME) as z:
    bad = z.testzip()
    if bad:
        die(f"zip check failed at {bad}")
shutil.copyfile(tree / "README.md", upload / "README.md")

# ---- 7. report -----------------------------------------------------------------------------------------------
total = 0
print(f"assemble: deposit tree {tree}")
for rel in on_disk:
    size = (tree / rel).stat().st_size
    total += size
    print(f"  {size:>12,}  {rel}")
zsize = (upload / ZIP_NAME).stat().st_size
print(f"assemble: {len(on_disk)} files, {total:,} bytes ({total / 1e6:.1f} MB) in the tree")
print(f"assemble: upload these 2 files from {upload}: README.md ({(upload / 'README.md').stat().st_size:,} bytes), "
      f"{ZIP_NAME} ({zsize:,} bytes, {zsize / 1e6:.1f} MB)")
print(f"assemble: status {status}")
PYEOF
