#!/usr/bin/env bash
# Reruns every check behind design-B-semantics-first.md. No network is used (sockets are blocked in the chain scripts).
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-/tmp/claude-0/-home-user-knowledge-Hyper-Graphs-/9b58e6a1-1989-5ed1-ae3b-676a337fca40/scratchpad/venv-libs/bin/python}
$PY build_fixture.py
$PY run_gate.py 2>/dev/null        | tee gate-output.txt
$PY run_evidence.py 2>/dev/null    | tee evidence-output.txt
$PY run_smoke.py 2>/dev/null       | tee smoke-output.txt          # also regenerates queue-examples.json
$PY run_malformed.py 2>/dev/null   > malformed-output.txt; tail -3 malformed-output.txt
$PY khg_codes.py                   | tee codes-output.txt
$PY run_code_probes.py             | tee code-probes-output.txt
$PY schema-refactor-check/diff_schemas.py | tee schema-refactor-output.txt
$PY run_identity.py                | tee identity-output.txt
$PY migrate_sample.py 2>/dev/null  | tee migrate-output.txt
$PY run_scenarios.py               | tee scenarios-output.txt
