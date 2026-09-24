#!/bin/sh
# Reproduces every check quoted in design-A-standards-first.md (offline). Venvs from the P2 research session.
set -e
export PYTHONDONTWRITEBYTECODE=1   # never write bytecode into the repository's probes directory
cd "$(dirname "$0")"
V=../../venv-hif/bin/python      # jsonschema 4.26.0 + fastjsonschema 2.22.2
L=../../venv-libs/bin/python     # xgi 0.10.2, hypernetx 2.4.3, pandas 2.3.3
python3 build_schemas.py
python3 make_span.py >/dev/null
$V checks_schema.py        # schemas, fixture, HIF export vs vendored HIF + profile, fold/unfold, keys
$V malformed_cases.py      # 88 malformed cases + baselines
$L checks_libs.py          # XGI / HNX / chain round trips, determinism, library evidence
$V scenarios_and_smoke.py  # 22 C2 scenarios + queue -> lint -> store -> export smoke test
$V migrate_sample.py       # schemas/sample.hif.json -> 1.0.0
$V legacy_proto.py         # legacy import of the KB sample and R03's 27 library cases
