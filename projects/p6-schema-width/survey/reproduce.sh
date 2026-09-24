#!/usr/bin/env bash
# Reproduce the P6 schema width survey (DESIGN §6.6). Run from anywhere; results go to projects/p6-schema-width/results/.
#
#   survey/reproduce.sh [--p3a-counts PATH] [--new-snapshot] [--jobs N] [--time-limit SECONDS] [--rows SELECTION]
#                       [--solver auto|python] [--out DIR]
#
# 1. Check the venv (khg-width[survey,fast] installed with khg-contracts) and the solvers (optional: without them
#    the run is Python-only and still valid; build them with khg-width/scripts/build-solvers.sh).
# 2. Verify the dataset manifests. A missing raw file gets its fetch command: Biolink and Zenodo return identical
#    bytes; WDQS returns a *new* snapshot (then regenerate with --new-snapshot).
# 3. Generate the schemas (from P3a's counts when --p3a-counts is given, else from SQID) into a temporary directory
#    and install them (run_survey.py install): files identical to the committed ones (file sha256 and C1 schema
#    sha256) are left untouched; SQID-based observed files replaced by P3a-based ones move, with their reports, to
#    results/superseded/ (DESIGN §6.6); any other difference stops the run unless --new-snapshot.
# 4. Run the rows, then the HyperBench baseline, then the table and the figure.
#
# Run time on 4 cores at the default 600 s per step: generation ~2.5 min; Biolink and control rows under a minute
# each; each wd-roles row ~30-36 min (Python steps plus the 20-minute solver budget of ruling Q8); all dump-scope
# rows with --jobs 3: ~1.25-1.5 h.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
P6="$(dirname "$HERE")"
REPO="$(cd "$P6/../.." && pwd)"
OUT="$P6/results"
P3A=""; NEW=0; JOBS=3; LIMIT=600; ROWS=all; SOLVER=auto
while [ $# -gt 0 ]; do
  case "$1" in
    --p3a-counts) P3A="$2"; shift 2 ;;
    --new-snapshot) NEW=1; shift ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --time-limit) LIMIT="$2"; shift 2 ;;
    --rows) ROWS="$2"; shift 2 ;;
    --solver) SOLVER="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    *) echo "reproduce: unknown option $1" >&2; exit 2 ;;
  esac
done
PY="${PYTHON:-python}"

echo "== 1. environment"
"$PY" - <<'PYEOF'
import importlib.util, sys
missing = [m for m in ("khg_contracts", "khg_width", "linkml_runtime", "yaml", "matplotlib", "scipy")
           if importlib.util.find_spec(m) is None]
if missing:
    sys.exit("missing: " + ", ".join(missing) + "\ninstall: pip install . './projects/p6-schema-width/khg-width[survey,fast]'")
from khg_width import find_solvers
found = find_solvers()
for t in ("balancedgo", "logk"):
    print(f"  {t}: {found[t].path} ({found[t].commit[:12]})" if t in found else f"  {t}: not found (Python-only hw)")
PYEOF

echo "== 2. manifests"
"$PY" - "$REPO" <<'PYEOF'
import json, sys
from pathlib import Path
from khg_width.sources import manifest
repo = Path(sys.argv[1])
bad = 0
for d in ("datasets/knowledge-bases/wikidata-property-schemas", "datasets/knowledge-bases/biolink-model",
          "datasets/hypergraph-benchmarks/hyperbench"):
    try:
        n = len(manifest.verify(repo / d))
        print(f"  {d}: {n} files verified")
    except manifest.ManifestError as e:
        bad += 1
        print(f"  {d}: {e}")
        m = json.loads((repo / d / "MANIFEST.json").read_text())
        for f in m["files"]:
            if not (repo / d / f["path"]).exists():
                how = "WDQS: a new snapshot (python projects/p6-schema-width/research/probes/wd_fetch.py)" \
                    if "query.wikidata.org" in f.get("source_url", "") else f"curl -L -o {d}/{f['path']} '{f.get('source_url')}'"
                print(f"    fetch {f['path']}: {how}")
sys.exit(1 if bad else 0)
PYEOF

echo "== 3. schemas"
GEN=("$PY" "$HERE/run_survey.py" generate --out "$OUT")
[ -n "$P3A" ] && GEN+=(--p3a-counts "$P3A")
[ "$NEW" = 1 ] && GEN+=(--new-snapshot)
# generates into a temporary directory, then installs: identical files are left as they are; with P3a's counts the
# SQID-based observed files and their reports move to superseded/ (expected); any other difference stops the run
# unless --new-snapshot. Rows whose files were installed are listed in pending-rerun.json.
"${GEN[@]}" > /dev/null
"$PY" "$HERE/run_survey.py" pending --out "$OUT"

echo "== 4. rows, baseline, table, figure"
"$PY" "$HERE/run_survey.py" run --out "$OUT" --rows "$ROWS" --jobs "$JOBS" --time-limit "$LIMIT" --solver "$SOLVER"
"$PY" "$HERE/hyperbench_baseline.py" --out "$OUT"
"$PY" "$HERE/run_survey.py" table --out "$OUT"
"$PY" "$HERE/make_figure.py" --out "$OUT"
echo "done: $OUT/survey.md"
