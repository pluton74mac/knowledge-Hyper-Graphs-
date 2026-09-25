#!/usr/bin/env bash
# P6 probe: run the external hypertree-decomposition tools on the probe instances and keep the raw output.
#
# Usage:  P6_TOOLS=<dir with the builds> P6_VENV=<python venv> bash run_solvers.sh [instance ...]
# Output: out/solvers/<tool>/<instance>.txt (raw stdout+stderr, first line = the exact command) and
#         out/solvers/summary.tsv (tool, instance, measure, value, seconds, status).
# Builds expected under $P6_TOOLS (see ../01-theory-and-solvers.md section 4 for the build steps):
#   BalancedGo/BalancedGo  log-k-decomp/log-k-decomp  newdetkdecomp/bin/*  detkdecomp/sources/detkdecomp
#   htd/build/bin/htd_main-1.2.0  htdleo/htdleo  htdsmt  frasmt
# Instances: instances/<name>.hg (HyperBench format), .pace.hgr (PACE 2019), .htd.hgr (htd "p tw" hgr);
# c_grid2d_10 is read from $P6_SCRATCH (not committed; see instances.py).
# Optional: P6_TIMEOUT (seconds per run, default 300), P6_GHW_KMAX (largest k tried with BalancedGo -global, default 5),
# P6_SKIP (extended regex over "<tool> <instance> <measure>"; matching runs are skipped).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
T="${P6_TOOLS:?set P6_TOOLS}"
PY="${P6_VENV:?set P6_VENV}/bin/python"
INST="$HERE/instances"
OUT="$HERE/out/solvers"
TO="${P6_TIMEOUT:-300}"
mkdir -p "$OUT"
SUM="$OUT/summary.tsv"
[ -f "$SUM" ] || printf 'tool\tinstance\tmeasure\tvalue\tseconds\tstatus\n' > "$SUM"

names=("$@")
[ ${#names[@]} -eq 0 ] && names=(berge_path berge_triangle gamma_triangle a_triangle_cover b_triangle k5 adler c_grid4 c_grid5 grohe_marx_3 c_grid2d_10)

src() {  # path of an instance file, repo first, then scratch
  if [ -f "$INST/$1$2" ]; then echo "$INST/$1$2"; else echo "${P6_SCRATCH:-/nonexistent}/$1$2"; fi
}

run() {  # run <tool> <instance> <measure> <cmd...>; records raw output and wall time
  local tool="$1" inst="$2" measure="$3"; shift 3
  if [ -n "${P6_SKIP:-}" ] && echo "$tool $inst $measure" | grep -Eq "$P6_SKIP"; then return; fi
  mkdir -p "$OUT/$tool"
  local f="$OUT/$tool/$inst.$measure.txt"
  local t0 t1 st
  t0=$(date +%s.%N)
  { echo "\$ $*"; timeout "$TO" "$@" 2>&1; echo "[exit $?]"; } > "$f"
  t1=$(date +%s.%N)
  st=$(tail -1 "$f")
  echo "$f" > /dev/null
  printf '%s\t%s\t%s\t%s\t%.2f\t%s\n' "$tool" "$inst" "$measure" "$(extract "$tool" "$measure" "$f")" "$(echo "$t1 - $t0" | bc)" "$st" >> "$SUM"
}

extract() {  # pull the width out of each tool's output
  local tool="$1" measure="$2" f="$3"
  if tail -1 "$f" | grep -q "exit 124"; then echo "timeout"; return; fi
  case "$tool" in
    balancedgo|logk) if grep -q "Correct:  true" "$f"; then grep -m1 "^Width:" "$f" | awk '{print $2}'; else echo "no"; fi ;;
    ndk|detk1)
      if grep -q "fractional-hypertree-width" "$f"; then grep -o "fractional-hypertree-width: [0-9.]*" "$f" | awk '{print $2}';
      elif grep -q "GML output written" "$f"; then echo "yes"; elif grep -q "not found" "$f"; then echo "no"; else echo "?"; fi ;;
    htd) if [ "$measure" = "tw" ]; then echo $(( $(grep -E '^[0-9]+$' "$f" | tail -1) - 1 )); else
           awk '/NODE/{if(n>m)m=n;n=0} /HYPEREDGE/{n++} END{if(n>m)m=n; print m}' "$f"; fi ;;
    htdleo|htdsmt) grep -o "Result: [0-9]*" "$f" | awk '{print $2}' ;;
    frasmt) grep -o '"width": [0-9.]*' "$f" | tail -1 | awk '{print $2}' ;;
    *) echo "?" ;;
  esac
}

for n in "${names[@]}"; do
  hg="$(src "$n" .hg)"; pace="$(src "$n" .pace.hgr)"; hgr="$(src "$n" .htd.hgr)"
  [ -f "$hg" ] || { echo "missing $hg"; continue; }
  # hw, exact: DetK and log-k-decomp both iterate k = 1, 2, ... (-exact)
  run balancedgo "$n" hw_detk_exact "$T/BalancedGo/BalancedGo" -graph "$hg" -exact -det
  run balancedgo "$n" hw_detk_exact_pace "$T/BalancedGo/BalancedGo" -graph "$pace" -pace -exact -det
  run logk "$n" hw_exact "$T/log-k-decomp/log-k-decomp" -graph "$hg" -exact
  # ghw: BalancedGo global BalSep (subedges computed for the given width), k = 1..5; first "yes" is ghw
  for k in $(seq 1 "${P6_GHW_KMAX:-5}"); do
    run balancedgo "$n" "ghw_global_k$k" "$T/BalancedGo/BalancedGo" -graph "$hg" -width "$k" -global
    grep -q "Correct:  true" "$OUT/balancedgo/$n.ghw_global_k$k.txt" 2>/dev/null && break
  done
  # NewDetKDecomp: hw (detkdecomp), ghw (balsepkdecomp), fhw upper bound (fracimprovehd) -- run in a temp dir, they write .gml next to the input
  wd="$(mktemp -d)"; cp "$hg" "$wd/$n.hg"
  for k in 1 2 3 4 5; do
    (cd "$wd" && run ndk "$n" "hw_detk_k$k" "$T/newdetkdecomp/bin/detkdecomp" "$k" "$n.hg")
    grep -q "GML output written" "$OUT/ndk/$n.hw_detk_k$k.txt" && break
  done
  for k in 1 2 3 4 5; do
    (cd "$wd" && run ndk "$n" "ghw_balsep_k$k" "$T/newdetkdecomp/bin/balsepkdecomp" "$k" "$n.hg")
    grep -q "GML output written" "$OUT/ndk/$n.ghw_balsep_k$k.txt" && break
  done
  (cd "$wd" && run ndk "$n" stats "$T/newdetkdecomp/bin/hg-stats" "$n.hg")
  (cd "$wd" && run detk1 "$n" hw_k3 "$T/detkdecomp/sources/detkdecomp" 3 "$n.hg")
  rm -rf "$wd"
  # htd: heuristic tree decomposition width (primal graph) and heuristic GHD width (covers of the TD bags)
  run htd "$n" tw "$T/htd/build/bin/htd_main-1.2.0" --input hgr --output width --opt width --iterations 50 -s 1 --instance "$hgr"
  run htd "$n" ghw_ub "$T/htd/build/bin/htd_main-1.2.0" --input hgr --type hypertree --output human -s 1 --instance "$hgr"
  # SAT: HtdLEO (Zenodo snapshot) and htdsmt (GitHub), hw and ghw (-g)
  run htdleo "$n" hw "$PY" "$HERE/run_htdleo.py" "$T/htdleo/htdleo" "$hg"
  run htdleo "$n" ghw "$PY" "$HERE/run_htdleo.py" "$T/htdleo/htdleo" "$hg" -g
  run htdsmt "$n" hw "$PY" "$HERE/run_htdleo.py" "$T/htdsmt" "$hg"
  # SMT: fraSMT, fhw
  run frasmt "$n" fhw "$PY" "$HERE/run_frasmt.py" "$T/frasmt" -s "$(dirname "$PY")/z3" -f "$hg"
done
cat "$SUM"
