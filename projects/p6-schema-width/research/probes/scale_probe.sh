#!/usr/bin/env bash
# P6 probe: how the solvers scale on large HyperBench instances (the size class of the Wikidata GYO residues).
# Usage:  P6_TOOLS=<builds> P6_HB=<unpacked HyperBench dir> bash scale_probe.sh
# Output: out/scale/<instance>.<run>.txt (first line = command) and out/scale/summary.tsv
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
T="${P6_TOOLS:?}"; HB="${P6_HB:?}"; TO="${P6_TIMEOUT:-600}"
OUT="$HERE/out/scale"; mkdir -p "$OUT"
SUM="$OUT/summary.tsv"; [ -f "$SUM" ] || printf 'instance\trun\tresult\tseconds\tstatus\n' > "$SUM"
# P6_FLAGS: extra preprocessing flags, e.g. "-t -h -g -heuristic 1" (type collapse, hinge tree, GYO reduct, vertex-degree
# edge ordering: the flags of the published log-k-decomp runs); runs are then suffixed with _flags.
FL="${P6_FLAGS:-}"; SFX=""; [ -n "$FL" ] && SFX="_flags"
one() {  # one <instance> <run-name> <cmd...>
  local inst="$1" name="$2"; shift 2
  local f="$OUT/$inst.$name.txt" t0 t1 res
  t0=$(date +%s.%N)
  { echo "\$ $*"; timeout "$TO" "$@" 2>&1 | tail -40; echo "[exit ${PIPESTATUS[0]}]"; } > "$f"
  t1=$(date +%s.%N)
  if grep -q "exit 124" "$f"; then res=timeout
  elif grep -q "Correct:  true" "$f"; then res="width $(grep -m1 '^Width:' "$f" | awk '{print $2}')"
  elif grep -q "Correct:  false" "$f"; then res=no
  else res="$(grep -E '^[0-9]+$' "$f" | tail -1)"; fi
  printf '%s\t%s\t%s\t%.1f\t%s\n' "$inst" "$name" "$res" "$(echo "$t1 - $t0" | bc)" "$(tail -1 "$f")" >> "$SUM"
}
# bridge_99: 893 edges, hw 2 (exact in the log-k-decomp data); NewSystem4: 418 edges, hw 4;
# s1423: 731 edges, hw in [4, 25] per the same data (exact value unknown).
for inst in ${P6_INSTANCES:-bridge_99 NewSystem4 s1423}; do
  g="$HB/$inst.hg"
  case $inst in bridge_99) k=2;; NewSystem4) k=4;; s1423) k=4;; esac
  one "$inst" "logk_width$k$SFX" "$T/log-k-decomp/log-k-decomp" -graph "$g" -width "$k" $FL -bench
  one "$inst" "balgo_detk_width$k$SFX" "$T/BalancedGo/BalancedGo" -graph "$g" -width "$k" -det $FL -bench
  [ -z "$FL" ] && one "$inst" "balgo_approx60" "$T/BalancedGo/BalancedGo" -graph "$g" -approx 60 -balDet 1 -bench
done
cat "$SUM"
