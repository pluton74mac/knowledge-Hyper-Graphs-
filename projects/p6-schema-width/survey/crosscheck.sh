#!/usr/bin/env bash
# Manual cross-checks of khg-width results with the SAT/SMT tools that P6 does not depend on (DESIGN §3.5):
# HtdLEO and htdsmt (exact hw and ghw by SAT) and fraSMT (exact fhw). They are GPL-3 / CC BY research code and
# fraSMT needs IBM CPLEX: install them yourself (research/01-theory-and-solvers.md §4.2) and point P6_TOOLS at them.
#
#   P6_TOOLS=<dir with htdleo/, htdsmt/, frasmt/> P6_VENV=<venv with their deps> \
#     survey/crosscheck.sh SCHEMA_FILE [--slots core,qualifier] [--timeout 600]
#
# Writes results/crosschecks/<schema>.<slots>.{hg,map.json} (neutral ids, as khg-width gives the solvers) and one raw
# output per tool (first line: the command). Compare by hand with the report's hw, ghw and fhw; record any
# disagreement in the note. The shims run_htdleo.py and run_frasmt.py are R01's (research/probes/).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
P6="$(dirname "$HERE")"
SCHEMA="${1:?schema file}"; shift
SLOTS="core,qualifier"; TO=600
while [ $# -gt 0 ]; do
  case "$1" in --slots) SLOTS="$2"; shift 2 ;; --timeout) TO="$2"; shift 2 ;; *) echo "unknown $1" >&2; exit 2 ;; esac
done
T="${P6_TOOLS:?set P6_TOOLS}"; PY="${P6_VENV:?set P6_VENV}/bin/python"
OUT="$P6/results/crosschecks"; mkdir -p "$OUT"
STEM="$(basename "$SCHEMA" | sed -e 's/\.json\.gz$//' -e 's/\.json$//' -e 's/\.relation-schema$//').${SLOTS//,/-}"
python - "$SCHEMA" "$SLOTS" "$OUT/$STEM" <<'PYEOF'
import json, sys
from khg_width import hypergraph
h = hypergraph(sys.argv[1], slots=sys.argv[2].split(",")).distinct()
n = h.neutral
open(sys.argv[3] + ".hg", "w").write(n.text)
json.dump({"relations": n.relations, "roles": n.roles}, open(sys.argv[3] + ".map.json", "w"), indent=1)
PYEOF
run() {  # run <name> <cmd...>
  local f="$OUT/$STEM.$1.txt"; shift
  { echo "\$ $*"; timeout "$TO" "$@" 2>&1; echo "[exit $?]"; } > "$f"
  echo "  $(basename "$f"): $(tail -1 "$f")"
}
run htdleo-hw "$PY" "$P6/research/probes/run_htdleo.py" "$T/htdleo/htdleo" "$OUT/$STEM.hg"
run htdleo-ghw "$PY" "$P6/research/probes/run_htdleo.py" "$T/htdleo/htdleo" "$OUT/$STEM.hg" -g
run htdsmt-hw "$PY" "$P6/research/probes/run_htdleo.py" "$T/htdsmt" "$OUT/$STEM.hg"
run frasmt-fhw "$PY" "$P6/research/probes/run_frasmt.py" "$T/frasmt" -s "$(dirname "$PY")/z3" -f "$OUT/$STEM.hg"
echo "fraSMT: check that the '#hyperedges' it echoes equals $(grep -c '(' "$OUT/$STEM.hg") (R01 §4.3)"
