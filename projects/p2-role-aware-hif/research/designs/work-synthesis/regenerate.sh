#!/bin/sh
# Regenerates every design example into $1 (default: ../../../design-examples) and validates them, offline.
# Needs two venvs: $PYHIF (jsonschema, fastjsonschema) and $PYLIBS (xgi 0.10.2, hypernetx 2.4.3, pandas, jsonschema).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$HERE/../../../design-examples}
mkdir -p "$OUT"
cd "$HERE"
$PYHIF build_examples.py "$OUT"          # fixture, schema, HIF, slice, derived, history, smoke base and queue, samples
$PYHIF make_schemas.py "$OUT"            # draft-07 schemas with x-khg-code
$PYHIF build_c4.py "$OUT"                # C4 items (memory gold by derive_memory_gold) and C5 system outputs
$PYHIF make_registry.py "$OUT"           # error-codes.json
$PYHIF make_role_convention.py "$OUT"    # the upstream fixture-PR files
$PYHIF make_scenarios.py "$OUT"          # conformance scenarios and index
$PYHIF make_malformed.py "$OUT"          # malformed cases, checked mechanically against the G2 rule
$PYLIBS g1_chain.py "$OUT" | $PYHIF -c "import json,sys; d=json.load(sys.stdin); open(sys.argv[1],'w').write(json.dumps({'format':'khg-golden/1.0.0','chain':'C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1','digests':d},indent=1)+'\n')" "$OUT/golden-sha256.json"
$PYLIBS native_ops.py "$OUT" > /dev/null 2>&1
$PYLIBS run_evidence.py "$OUT" > /dev/null 2>&1
$PYLIBS r03_cases.py "$OUT" > /dev/null 2>&1
$PYHIF validate_examples.py "$OUT" schema
$PYLIBS validate_examples.py "$OUT" libs
