# Work directory for design C (consumer-first)

Research prototypes that execute the rules written in `../design-C-consumer-first.md`, so that every JSON
example in the design is produced and checked by code. Not the package. No network is used
(`run_checks.py` patches `requests.get` to raise; the HyperNetX evidence path is served the vendored schema).

Run with the probe virtualenvs (Python 3.11.15; xgi 0.10.2, hypernetx 2.4.3, pandas 2.3.3, jsonschema 4.26.0,
fastjsonschema 2.22.2):

```bash
V=../../venv-libs/bin/python
$V gate_fixture.py      # writes gate-schema.json and gate.khg.jsonl (the adversarial gate fixture, 41 lines)
$V run_checks.py        # record/meta schemas; HIF export (full + directed slice); vendored HIF schema and profile
                        # schema under jsonschema and fastjsonschema; HIF->C1 import; both gate chains through
                        # research/probes/role_loaders_sketch.py; library evidence (xgi/hnx own HIF functions)
$V malformed.py         # 86 malformed cases M01..M99 through the layered validator (writes malformed-results.json)
$V queue_c3.py          # smoke test: queue -> structural lint -> store -> export; duplicate merge; reject; replay
$V queue_cases.py       # 10 queue-level malformed cases Q01..Q10
$V conformance.py       # 18 declarative C2 scenarios against the reference MemoryStore (+ a capability-limited run)
$V migrate_sample.py    # schemas/sample.hif.json -> C1 1.0.0 (legacy attrs.role; weight dropped unless flagged)
$V fast_check.py        # every valid artefact under fastjsonschema (offline $ref to the vendored HIF schema)
$V pretty_hif.py        # gate-full.hif.json in the design's reading layout (gate-full.hif.pretty.json)
$V assemble.py          # fills the placeholders of doc-0..doc-6.md and writes ../design-C-consumer-first.md
```

| File | What |
|---|---|
| `c1.py` | canonical JSON, the four identifiers, literals, time bounds, arity, `normalise()` |
| `gate_fixture.py` | relation-type schema `p2-gate/1.0.0` and the gate fixture |
| `hif_codec.py` | C1 container <-> khg-hif/1.0.0 (to_hif, from_hif, canonical_hif) |
| `semantic.py` | layer-3 checks (R-, S-, C-, D- codes) |
| `store.py` | reference in-memory C2 store (Where, put, load, get, history, incident, find, find_by_key, apply, walk, export) |
| `conformance.py` | scenario format khg-store-scenario/1.0.0, 18 scenarios, runner with capability gating |
| `queue_c3.py` | C3 queue (append-only JSONL), linter, accept/merge, replay, smoke test |
| `migrate_sample.py` | legacy-HIF migration of the KB sample |
| `khg-record-1.0.0.schema.json` | draft-07 schema of C1 container lines |
| `khg-relation-schema-1.0.0.schema.json` | draft-07 meta-schema of relation-type schema documents |
| `khg-hif-1.0.0.schema.json` | draft-07 HIF profile schema (`allOf` the vendored HIF schema by its `$id`) |
| `khg-queue-1.0.0.schema.json` | draft-07 schema of C3 queue lines |
| `khg-c4-items-0.1.0.schema.json` | draft-07 schema of the C4 item shapes C5 reads (a draft for P3a) |
| `pretty_hif.py`, `assemble.py`, `doc-0.md`..`doc-6.md` | the design text with placeholders and the script that fills them from the artefacts |
| outputs | `gate.khg.jsonl`, `gate-full.hif.json`, `gate-full.hif.pretty.json`, `gate-directed.hif.json`, `sample-migrated.*`, `smoke.queue.jsonl`, `run_checks.out.json`, `smoke.out.json`, `malformed-results.json`, `conformance-scenarios.json` |
