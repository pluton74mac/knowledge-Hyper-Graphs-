# Work folder for design B (semantics-first)

Scratch prototype that checks the design's claims. It is not the P2 package.

| File | What it is |
|---|---|
| `khg-record-1.0.0.schema.json` | C1 document/record JSON Schema (draft-07); like the other three P2 schemas it carries `x-khg-code` annotations and dispatches every shape choice with `if`/`then` |
| `khg-schema-1.0.0.schema.json` | relation-type schema language meta-schema (draft-07) |
| `khg-hif-1.0.0.schema.json` | KHG profile of HIF: `allOf` the vendored HIF schema + attrs/metadata constraints |
| `khg-queue-1.0.0.schema.json` | C3 queue item, action-log entry, verdict |
| `hif_schema_v0.1.0.json` | vendored HIF schema, blob e2105bb (copied from research/probes/hif-schema) |
| `p2-gate.schema.json` | relation-type schema of the gate fixture (11 relations) |
| `fixture-directed.khg.json` / `.hif.json` / `.hif.compact.json` | the adversarial gate fixture, C1 and HIF |
| `fixture-undirected.khg.json` / `.hif.json` | the undirected companion fixture (symmetric role, one node in two roles without direction) |
| `khg_proto.py` | canonical JSON, hashes, literals, precision windows, presumed intervals, derived fields, refinement order, identity classifier, C1<->HIF codec |
| `khg_semantic.py`, `khg_schema_check.py` | semantic validator layers (S/D and M codes) |
| `khg_codes.py` | stable codes for JSON Schema failures (x-khg-code reporter, H table) and `coverage()`; run it to print coverage |
| `proto_store.py` | lean C2 memory store + C3 queue + `fold_check` (Q005/Q007) |
| `run_gate.py` | gate clause 1 on both fixtures, both validators, no network |
| `run_evidence.py` | HIF-level multiset comparison + what the libraries' own HIF functions drop |
| `run_malformed.py` | gate clause 2: 108 malformed cases (expected layer and code) + 5 positives + code coverage |
| `run_code_probes.py` | 28 registry probes, one per §8.2 clause the gate list does not reach |
| `schema-refactor-check/` | `original/` schemas (before annotation and dispatch), the one-off `annotate_schemas_once.py`, and `diff_schemas.py` (old vs new verdicts on 24,013 documents, both validators) |
| `run_identity.py` | classification of every R01 identity case |
| `migrate_sample.py` | migration of `schemas/sample.hif.json` + gate chain |
| `run_smoke.py` | gate clause 3 (queue -> lint -> store -> export) + 18 store checks + 3 C3 checks; writes `queue-examples.json` |
| `run_scenarios.py`, `scenarios/*.json` | declarative C2 conformance scenarios |
| `run_all.sh` | reruns everything |
