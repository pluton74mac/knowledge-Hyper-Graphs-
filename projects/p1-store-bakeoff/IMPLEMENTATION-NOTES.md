---
title: "P1 implementation notes: decisions and deviations (first half)"
type: project
status: draft
created: 2026-09-25
---

# P1 implementation notes (first half)

What was built against [DESIGN.md](DESIGN.md), [research 01](research/01-backends.md) ([R01]) and the director's
rulings on it ([README](README.md)), and every place where the build had to choose. Where the rulings or [R01] are
specific they were followed; each deviation below has its reason.

## 1. What exists

| Deliverable | Where | State |
|---|---|---|
| 1. The public version-table interface (ruling 17) | `src/khg_contracts/store/table.py`, `memory.py` (`TableStore`), `_writes.py` (step 8); `tests/store/test_table.py`; P2 DESIGN §14 ruling 17 | done; P2's suite green |
| 2. Design | [DESIGN.md](DESIGN.md) | done |
| 3. Package `khg-bakeoff` (MIT) | [khg-bakeoff/](khg-bakeoff/): six adapters, the conformance and fidelity runners, the CLI | done |
| 4. Conformance runs | [results/conformance/](results/conformance/): one EARL report per backend, `summary.json`, `summary.md` | all six pass |
| 5. Fidelity | [results/fidelity.json](results/fidelity.json), [results/fidelity.md](results/fidelity.md); the edge container [fixtures/](fixtures/) | done (number 3 on the hand queries) |
| 6. Servers and README | [start-servers.sh](start-servers.sh); README Results and Log | done |
| 7. Tests and CI | `khg-bakeoff/tests/` (11 files since review 01); job `khg-bakeoff` in `.github/workflows/ci.yml` | done; CI simulated locally |
| 8. Corrections ([R01] §11) | P2 DESIGN §6.5 amendments A1–A4; four notes in `kb/04-storage-and-formats/` | done; KB validator clean |
| 9. These notes | this file | |
| 10. Fixes from review 01 | §8 below; [results/roundtrips.md](results/roundtrips.md); DESIGN §6.1 | all 15 fixed |

## 2. khg-contracts: ruling 17

- **Where the base lives.** `store.table` exports `VersionTableProtocol` (a `runtime_checkable` Protocol with the
  13 members; `MEMBERS` names them), `Entry`, `VersionTable`, `bound_nodes` and `TableStore`.
  - `TableStore` is the former body of `MemoryStore`. `MemoryStore` is now `TableStore` over `VersionTable`, with
    the same constructor, `repr`, `store_id` default and behaviour. `store.__all__` is unchanged (C2's namespace).
  - `TableStore(schema, *, table=None, …)` takes a **function of the resolved `Schema`** that returns the table.
    A table usually needs the schema and a connection; a factory keeps one form.
- **The transaction hook wraps the whole write**, not only `_commit` as the SQLite probe did ([R01] §1). The
  checks of `put` before `_commit` (validation, D013, references) and the write then see one snapshot of the
  backend.
- **The addition on review 01** (P2 DESIGN §14, under ruling 17):
  - the public header accessors `kept_header` and `kept_documents`;
  - `writing()` restores them when a write fails;
  - the optional table member `prefetch(records)`, which `load` calls before its checks (§8, R-02 and R-07).
  - `writing()` is the re-entrant form the store uses, so an adapter can add its header row to a load's
    transaction.
  - The default, `contextlib.nullcontext()`, leaves `MemoryStore` as it was.
- **`cannot_hold(record)` goes beyond the ruling's text.** Ruling 4 wants a refused instant reported through the
  existing error and report model, and ruling 2 wants adapters to import public names only. A hook in the base was
  the only way to do both without overriding private methods.
  - It runs as step 8 of the write path, after D018 and before anything is written. In `load` it runs after the
    flag check, record by record.
  - The refusal is a `ValidationError` without a code: no new code (§5 Q1).
- **Tests.** 13 in `tests/store/test_table.py`, and 3 more for the addition on review 01 (§8):
  - the protocol and its members;
  - a JSON-text table (`JournalTable`, which builds a fresh `Entry` on every read) that passes all 114 scenarios
    under `TableStore`;
  - one transaction per write, rollback of a batch that fails in the middle of the backend's writes, and
    re-entrancy;
  - refusals in `put` and in `load` (`raise` and `skip`), and a missing flag checked before a refusal.
- **P2's full suite:** 5,910 passed, 1 skipped, against a baseline of 5,897 passed and 1 skipped before the
  change. It ran from the repository root with the dev venv (editable install with every extra, as CI's
  `gate-3.11`). `test_table.py` and `test_memory_store.py` also pass on Python 3.10 and 3.13.

## 3. The adapters: decisions

**Shared (`rows`, `native`, `shared`).**
- `NativeReads` repeats `TableStore`'s argument, flag and relation checks in the same order, so a refusal raises
  the same error.
- `find_by_key` follows `StoreBase`'s order: the digest first; a key with a special value returns `[]` before any
  flag check.
- A pattern's `position: null` is refused as the reference refuses it (tested against `MemoryStore`).

**SQL (SQLite, PostgreSQL).**
- `payload`, `value_json`, `extensions` and entity records are `text`, not `jsonb`. `jsonb` rewrites numbers:
  `1e+21` comes back as an integer, and canonical JSON would change.
- Each store's entries are cached within one write and forgotten at its end, so the cache never outlives a rollback.
- Rows are buffered and written when the write ends, or before a query that scans the tables. A query about one id
  flushes only when that id is buffered.
- A load prefetches its ids, three queries per 500 ids and none on an empty store. The versions it closes are updated
  in one statement per table and chunk, `executemany` in SQLite and `unnest` in PostgreSQL.
- PostgreSQL keeps one schema per store in one database. That is faster than a database per scenario.
  - Every text column is `COLLATE "C"`, so ids order by code point whatever the database's locale.
  - The database is created with `LOCALE_PROVIDER libc`, and opening refuses any other provider (R-05).

**The PostgreSQL key guard (deviation).**
- [R01] §2.2 sketched `key_period` as a guard for "the plain key invariant". Over every asserted fact it would
  refuse legal states: a preferred fact beside two overlapping normal ones satisfies D016.
- The guard therefore holds only current, asserted, **preferred** facts. No two of those hold together on one key,
  under D016, whatever the ranks of the others.
- It is a cross-check, and it must never refuse what the write path accepts.
  - The first half's guard did refuse such a write: a batch that moved `preferred` from one fact to another failed
    whenever the new preferred fact came first. It changed the rows statement by statement (review 01, R-04).
  - A write now changes the guard once, at its end. It deletes the rows of every fact it touched, then inserts the
    new ones.
  - If the guard still refuses, the error is `KeyCollision` with code KHG-D016, never a psycopg error.
- Instants beyond int8 are clamped into the range. That can hide an overlap but never invent one.
- A trusted load whose data already break the rule suspends the guard for that store (ruling 12 keeps such data),
  instead of failing the load.
- Tested:
  - the database refuses a second preferred window inserted directly;
  - a store loaded with two overlapping preferred facts reports `key_guard == "suspended"` and holds all 40
    records.

**Oxigraph.**
- pyoxigraph 0.5.11 has no transaction handle. A write collects its versions in an in-memory `VersionTable`
  overlay, which the table reads through, and commits them with one `Store.update`.
- A multi-operation update is atomic: an update whose second operation failed left the store unchanged, in two
  checks (a failing `LOAD`, a repeated `CREATE GRAPH`).
- `bulk_extend` is used only for a load into an empty store. A failure clears the store and puts the store's own
  triples back.
  - In the first half the flag that chose it was reset before the commit read it, so every load was one
    `INSERT DATA` text (review 01, R-01).

**Neo4j.**
- The adapter's indexes are named `khg_*` and include `BINDS(role)` as well as `BINDS(role, ident)`.
- The research probe's indexes (`binds_role`, `version_id`, `version_key`, `node_id`, `literal_ident`) were dropped
  from the local server first: an equivalent index under another name would collide.
- Binding kinds are written with `FOREACH` in one `UNWIND` query, so an empty list of one kind does not end the
  row.
- Versions are buffered and flushed in `UNWIND` batches. The rows that close a stored version are partitioned from
  the others in one pass (R-15).

**TypeDB.**
- **Labels (deviation).** [R01]'s `name()` replaced every character outside `[A-Za-z0-9_-]` with `-`, which can map
  two names to one label (`a:b`, `a-b`). The adapter's labels are injective (`-<hex>-`) and prefixed (`ent-`,
  `rel-`, `role-`, `lit-`), so a schema name that is a TypeQL keyword cannot break the schema.
- **Special values and goals (deviation).** [R01] generated `special-<role>` and `unbound-<role>` attributes. The
  natural mapping declares both flags absent, so no record ever needs them, and they are left out.
- **Literal-only relations (new finding).** TypeDB refuses to define a relation type that relates no role
  (`[SVL41] Non abstract relation type … must relate at least one role`). Such a relation is left out of the
  schema, and its facts are refused with that reason.
- **Updates and write order.** A new version is written in place, and the write order is entities, then facts
  after the facts they bind. A fact of a batch may bind another fact of the same batch.
- **Batched writes (review 01, R-02).** Planning a `match` with hundreds of keyed variables was slow in TypeDB CE
  3.13.6: 300 facts in one query took 21.7 s, against 0.57 s one query per fact.
  - Batches are therefore pipelines: one `match`–`insert` per fact, each followed by `reduce $c = count`, so that
    variables do not accumulate. 300 facts then took 0.37 s.
  - Each stage checks that the count of the stage before it is 1, so a missing player fails the batch instead of
    being dropped. A pipeline has at most 1,000 stages, hence 200 records per query.
- **`distinct` keeps duplicates** across disjunction branches that bind different variables (3.13.6). Ids are
  therefore grouped with `reduce … groupby $id` before `sort` and `limit`.
- **The TypeQL `find`** (R-06). Each value is a linked player or an owned attribute. Each `any` is one more binding
  of its role, with the `any` split between players and literals in branches: a variable cannot be both an
  attribute and an object.
  - This is exact because `cannot_hold` now refuses a fact with two bindings of one role and one value identity,
    which TypeDB would collapse. Valid C1 never has one (S014).
- **Deleting databases (deviation from immediate cleanup).** In one full test run, TypeDB CE 3.13.6 panicked and
  stopped while deleting a database right after a transaction on it closed: "Cannot get exclusive ownership of
  inner of Arc<QueryCache>", `database.rs:527`. The panic did not recur in an isolated run, so it is a race. A
  closed store's database is now deleted `GRACE` = 5 s later, or at exit. The next full run (107 tests with every
  server) had no panic.

**HIF.**
- **Bookkeeping.** The store keeps two facts HIF has no place for in `hif:metadata` key `p1-store`: whether a header
  is kept, and the latest transaction time. The probe re-read the header from the file after every write. A store
  without a kept header then froze the computed header, including `complete`, at its first write.
- **Writes.** The file is rewritten only when a write changed something (a no-op `put` writes nothing). A failed
  write rebuilds the index from the file.
  - Since the fixes, the new file's text is decoded (`from_hif`) before it replaces the old one.
  - Before, a write that HIF could not hold replaced the file and then failed to read it back. That left an invalid
    file and an index holding the failed write (found while testing R-03; §8).

## 4. Deviations from [R01] or the rulings, and why

1. **Edge container items** (ruling 5; [R01] D5).
   - "One filler repeated in one unordered role" is dropped: C1 refuses it (KHG-S014, "duplicate filler in an
     unordered role"). Its ordered form is P2's `f:route-1`.
   - "Two equal literals in one role" is kept in the only valid form, an ordered literal role (`alias_list`).
   - The literal-only fact needs a relation without an entity role, which the fixture schema lacks. The container
     therefore has its own schema, `p1-edge`: the fixture schema plus `measured_constant` and `alias_list`.
2. **The key guard** covers preferred facts only (§3).
3. **TypeDB labels** are injective and prefixed (§3).
4. **`load(on_missing="skip")` also skips what `cannot_hold` refuses** (ruling 4 through LoadReport). P2 §6.2
   defines `skip` for missing flags only (§5 Q2).
5. **Number 1 adds store fields.** `compare_containers` ignores `version`, `recorded_at` and `recorded_by`, which
   hid a real loss. The round trip is therefore also compared, with store fields, against `MemoryStore` holding the
   same records.
6. **Number 3's reference** is `MemoryStore` with the backend's flags, holding the container minus the records the
   backend skipped. A skipped record is a number-1 loss; number 3 compares only the queries.
7. **The history fixture** is exported with its header's `as_at`, so the round trip compares like with like. Without
   it every store differed by `/header/as_at`.
8. **No native one-query walk.** `supersession_walk` stays `StoreBase`'s (one `find` per level), as [R01] §2.3
   advised. The native forms wait for the second half's timing.

## 5. Findings of the build

- **HIF drops an entity's `recorded_by`.**
  - The profile's entity node carries `khg-version` and `khg-recorded-at` but not `khg-recorded-by` (P2 DESIGN §4.2,
    entity row; `hif/profile.py` `ENTITY_FIELDS`). Edges carry all three.
  - The HIF store therefore answers `get(entity)` without `recorded_by`: 22 of 22 fixture entities and 20 of 20 edge
    entities; one edge query differs.
  - `compare_containers` does not see it, and no conformance scenario reads an entity's `recorded_by` after a
    reload.
- **TypeDB cannot define a relation type without roles** (SVL41). A literal-only relation has no TypeQL form, which
  is stronger than "a relation without players is deleted at commit".
- **TypeDB CE 3.13.6 can panic when a database is deleted** right after use (§3).
- **Neo4j 2026.09.0 answers a role lookup with an index seek.** `EXPLAIN MATCH (v)-[e:BINDS]->() WHERE e.role = $r`
  plans a `DirectedRelationshipIndexSeek` on `khg_binds_role`: evidence for the KB correction.
- **No database layout keeps a time literal as written outside a JSON copy** (found by the fix of R-09). The
  layouts compare values by their identity (`record.identity_key`), which is the canonical literal for every
  datatype but time: a time literal's identity is its window and precision. Of the fixture's 20 literals, 11 are
  time literals.
- **TypeDB CE 3.13.6's `distinct` keeps duplicate rows** after `select`, across disjunction branches that bind
  different variables; `reduce … groupby` groups them (§3).
- **TypeDB CE 3.13.6 plans a `match` of many keyed variables slowly**, super-linearly in their number. Pipelines of
  small stages separated by `reduce` do not accumulate them (§3).
- **The HIF store cannot load a slice that is not `complete`** (found while testing R-03): `to_hif` writes an
  incidence on a node the file does not declare and `from_hif` refuses it (KHG-D002), so the whole load fails (§7
  Q5). Before the fixes, the failure also left an invalid file and an index holding the failed load (§3, HIF).
- **What valid C1 can bring to TypeDB.** Under S014 no valid record repeats a filler in an unordered role, so
  TypeDB's collapse of repeated players is reached only through ordered roles, which it declares absent, or through
  a trusted load of invalid data. With the natural mapping, the four numbers show every TypeDB loss as a skipped
  record or a native-layer count, and every read agrees with the reference: 13/13 on the fixture, 24/24 on the
  edge container.

## 6. Verification (final runs after the fixes of review 01, 2026-09-25)

| What | Where | Result |
|---|---|---|
| P2's full suite, as CI's gate-3.11 | repository root, dev venv (Python 3.11, every extra), `pytest -q -m "not evidence"` | 5,908 passed, 1 skipped, 5 deselected (5,905 before: 3 new tests of the addition to ruling 17) |
| P2's evidence tests, as CI's `evidence` job | the same venv, `pytest -q -m evidence` | 5 passed |
| P2's core jobs, as CI's core-3.10 and core-3.13 | fresh venvs, `pip install ".[dev]"`, `pytest -q` | 5,556 passed, 21 skipped on each |
| `MemoryStore` against `eb672d0` | review 01's differential (`diff_ops.py`, its two op files, re-run for both sides) | identical: 900 sequences, 40,634 operations, every result, error, `info`, message, final state and clock |
| khg-bakeoff, every backend | venv from the package's pins (Python 3.11), PostgreSQL 18.6, Neo4j 2026.09.0, TypeDB CE 3.13.6 running | 184 passed, 3 skipped (the refusal test skips where a backend holds the 16-digit year or lacks the flags) |
| khg-bakeoff, the CI job | Python 3.10 venv, `pip install . "./projects/p1-store-bakeoff/khg-bakeoff[oxigraph,postgres,dev]"`, PostgreSQL only; the import check of the Neo4j and TypeDB adapters | 154 passed, 33 skipped; the adapters import without their clients |
| khg-bakeoff, no server | the same venv, no endpoint | 134 passed, 53 skipped |
| The regression tests before the fixes | the new tests against the sources of `e41338f` (khg-contracts and khg-bakeoff), and `test_deliverables.py` against its files | every regression test of §8 fails; each passes after the fixes |
| KB validator | `python3 tools/validate_kb.py` | 123 files, 0 errors, 0 warnings |
| Edge container | `test_the_edge_container_is_valid_and_reproducible` | valid, 0 warnings; byte-identical |

- **CI.** At first GitHub Actions started no job for `914b810`: an account-level limit, which the director
  reported. Once the repository was public, the re-queued run passed all eight jobs (run 36099239085), among them
  `khg-bakeoff` on the `postgres:18.6` service image with the import step. The checks above are the CI jobs'
  commands, run here as well.
- **PostgreSQL.** The local runs used the PostgreSQL 18.6 build, which has ICU, with the same environment variable
  as CI.
- **Reproduction.** The six EARL reports are byte-identical after the fixes. `summary.json` and `summary.md` differ
  only in the khg-contracts commit and HIF's kind, "file, read in memory".

## 7. Open questions for the director

- **Q1.** A registered code for "the backend cannot hold this valid record" (DESIGN §9). Now: `ValidationError`
  without a code, `info["cannot_hold"]`.
- **Q2.** Does `on_missing="skip"` cover what `cannot_hold` refuses (DESIGN §9)?
- **Q3.** Add `khg-recorded-by` to the HIF profile's entity node (a minor profile version, P2)?
- **Q4.** TypeDB and slices that are not `complete`. A P3a slice will bind entities it does not hold. SQL, RDF and
  Neo4j store the reference as it is, but TypeDB needs a player instance, and the adapter now refuses such a fact
  (`player_not_held`). Should the second half give TypeDB stub instances (typed by the usage's first filler type),
  or count those facts as TypeDB losses?

Q1 to Q4 were ruled (README, the director's rulings on the build). New, from the fixes of review 01:

- **Q5. The HIF store and slices that are not `complete`.** For a fact on an entity the slice does not hold,
  `to_hif` writes an incidence on a node the file does not declare, and `from_hif` refuses the file (KHG-D002). The
  HIF store therefore cannot load such a slice at all; it now fails the load cleanly and keeps its old file
  (`test_the_hif_store_cannot_load_a_container_that_is_not_complete`). There are two ways out:
  - the analogue of build ruling Q4: skip and count such a fact through `cannot_hold`, a HIF loss, as TypeDB does;
  - P2's `to_hif` declares the node, a `khg-hif` question.

  Neither was done without a ruling.

## 8. Fixes from review 01 (2026-09-25)

[Review 01](review/review-01.md) found 15 defects; the director's rulings on it (README) settled R-06 and R-07.
All 15 are fixed.
- **Commits.** The code and its tests are commit `914b810`. The regenerated results, README, DESIGN and these notes
  are the commit after it, "P1: results, README and notes of the fixes from review 01".
- **The regression tests.** Each finding has one. Every test named below was run against the code and files of
  `e41338f`, the commit before the fixes, and fails there; each passes now.
  - For R-02 and R-07 the tests include P2's `tests/store/test_table.py`, run against `e41338f`'s khg-contracts.
  - For the documents (R-08, R-11 to R-14), `tests/test_deliverables.py` was run against `e41338f`'s files.

| Finding | What changed | Regression test(s) | Commit |
|---|---|---|---|
| R-01 (high) | `OxigraphStore.load` sets its bulk flag before `writing()` and resets it after the commit, so a load into an empty store writes with `bulk_extend`; a failure clears the store and puts its own triples back | `test_loads.py::test_r01_oxigraph_loads_an_empty_store_with_bulk_extend`, `::test_r01_a_failed_bulk_load_leaves_the_store_as_it_was` | `914b810` |
| R-02 (high) | `TableStore.load` calls the table's optional `prefetch(records)` (addition to ruling 17); the SQL, Oxigraph, Neo4j and TypeDB tables read the loaded ids in one query per table and chunk, none on an empty store; the emptiness check is one `EXISTS`, not a count; closes, guard rows and TypeDB inserts and updates are batched | `test_loads.py::test_r02_a_load_reads_no_record_on_its_own` (five backends); P2 `test_table.py::test_load_prefetches_its_ids_before_reading_them` | `914b810` |
| R-03 (high) | during a load, TypeDB's `cannot_hold` refuses a fact whose entity or fact player is neither held nor loaded (`player_not_held`), so `on_missing="skip"` skips and counts it and the facts that nest it; the write keeps the check as a guard | `test_loads.py::test_r03_typedb_skips_and_counts_a_fact_whose_player_it_does_not_hold` | `914b810` |
| R-04 (medium) | the PostgreSQL key guard changes once per write, at its end: the rows of every touched fact are deleted, then the new rows inserted (a query in the middle of the write leaves them buffered); a refusal is `KeyCollision` KHG-D016 | `test_adapters.py::test_r04_postgres_accepts_a_batch_that_moves_preferred_between_facts`, `::test_r04_a_refusal_of_the_key_guard_is_the_c2_error` | `914b810` |
| R-05 (medium) | `COLLATE "C"` on every text column; `CREATE DATABASE … LOCALE_PROVIDER libc LOCALE 'C'`; opening reads `datlocprovider` and `datlocale` (libc `C`/`POSIX` or builtin `C`/`C.UTF-8` only) and probes three pairs of ids ICU orders the other way | `test_adapters.py::test_r05_every_text_column_orders_by_code_point`, `::test_r05_an_icu_database_is_refused_and_the_columns_order_by_code_point_in_it` (creates an ICU database on the server; skips with the reason where the build has no ICU) | `914b810` |
| R-06 (medium) | per the ruling: `degree` is a native count; `get_many` one batched read; `supersession_walk` one lookup and one batched read per level; `iter_records`/`export` one scan; Oxigraph reads by `VALUES` blocks, TypeDB by `fetch` blocks in one read transaction per call; TypeDB's `find` matches, groups and limits in TypeQL; every record rebuilt by `rows.record_of`; HIF labelled "file, read in memory"; round trips measured (`khg_bakeoff.trips`, DESIGN §6.1) | `test_reads.py::test_r06_the_records_of_one_call_come_in_a_bounded_number_of_queries`, `::test_r06_degree_is_counted_by_the_engine`, `::test_r06_every_backend_rebuilds_its_records_with_one_function`, `::test_r06_the_hif_store_is_labelled_a_file_read_in_memory`; parity: `::test_every_read_equals_the_reference_on_random_queries`, `test_offline.py::test_typedb_find_matches_in_typeql` | `914b810` |
| R-07 (medium) | per the ruling: `TableStore.kept_header` and `kept_documents` (public, copies, settable); `writing()` restores both when the outermost write fails; the adapters use only these; recorded as an addition to ruling 17 (P2 DESIGN §14) | P2 `test_table.py::test_the_kept_header_and_documents_are_public`, `::test_a_failed_load_rolls_the_header_back`; `test_adapters.py::test_r07_the_adapters_use_the_public_header_accessors_only`, `::test_r07_a_failed_load_rolls_the_header_back` | `914b810` |
| R-08 (medium) | fidelity number 1 counts a record whose store fields differ as a silent loss (`silent`, `silent_ids`); README gate table and finding 2 state HIF's loss | `test_fidelity.py::test_r08_number_1_counts_the_silent_loss_of_hifs_entity_recorded_by`; `test_deliverables.py::test_r08_the_readme_gate_table_states_what_fidelity_measured` | `914b810`, and the docs commit |
| R-09 (low) | number 2 reads no `value_json`/`khg:valueJSON`: a literal is rebuilt from the stored identity (`rows.value_from_identity`), and the multiset compares stored identities; what the identity does not determine (a time literal) is lost | `test_fidelity.py::test_r09_number_2_reads_literals_from_the_native_structure_only`; `test_rows.py::test_split_and_assemble_are_inverse_on_every_fixture_fact` (native bindings never read `value_json`) | `914b810` |
| R-10 (low) | number 3 compares a query only when the reference with the backend's flags and skips answers as a full reference does; the others are n/a, out of the denominator | `test_fidelity.py::test_r10_number_3_leaves_out_the_queries_that_touch_what_was_skipped` | `914b810` |
| R-11 (low) | P2 DESIGN §6.5: the incidence row and A1 keep the constraint to current asserted preferred facts, the rest of D016 in code (citing §3 here); A4 adds SVL41 | `test_deliverables.py::test_r11_p2_design_65_keeps_the_key_constraint_to_preferred_facts` | `914b810` |
| R-12 (low) | a licence table in `khg-bakeoff/README.md`, from the clients' package metadata, and a licence header in `start-servers.sh` | `test_deliverables.py::test_r12_every_engine_and_client_has_its_licence_stated` | `914b810` |
| R-13 (low) | `start-servers.sh` writes `monitoring: enabled: false` (the port has no listen address); the local TypeDB was restarted with it and listens on 127.0.0.1 only | `test_deliverables.py::test_r13_typedb_listens_on_the_loopback_address_only` | `914b810` |
| R-14 (low) | CI's service image is `postgres:18.6`; a CI step imports the Neo4j and TypeDB adapters without their clients; `tests/test_offline.py` tests their pure-Python parts | `test_deliverables.py::test_r14_ci_pins_postgres_and_imports_every_adapter`; `test_offline.py` (5 tests) | `914b810` |
| R-15 (low) | Neo4j's flush partitions its rows in one pass (`neo4j.partition`) | `test_loads.py::test_r15_neo4j_partitions_its_buffer_in_one_pass` (counts equality tests: 0) | `914b810` |

**The numbers that changed, and why** (results regenerated at khg-contracts `914b810`):
- **Conformance.** Unchanged: 114, 114, 114, 114, 70 and 107 applicable, all passed, with the same losses by flag.
  Only HIF's kind now reads "file, read in memory".
- **Number 1 (R-08).** HIF's silent losses were 0 and are now 22 (fixture) and 20 (edge): every entity, without its
  `recorded_by`. The store-field comparison had counted them since the build; the column had not. No other backend
  loses anything silently.
- **Number 2 (R-09).** Literals as written are now read from the value identity each layout stores, not from a JSON
  copy of each value.
  - SQLite, PostgreSQL, Oxigraph and Neo4j go from 20/20 to 9/20 on the fixture. The 11 lost are its time literals,
    whose identity is their window and precision, not the time and calendar as written.
  - On the edge container PostgreSQL goes from 6/6 to 5/6: the far-future time literal, which the others skip.
  - TypeDB goes from 0/19 to 9/19. Its owned attributes hold the same identities, so the first half's 0 counted
    only the missing JSON copy.
  - HIF stays 20/20: its literal nodes carry the literal as written.
  - Bids, positions, extensions and multisets are unchanged.
- **Number 3 (R-10).** A query that touches what the backend skipped or lacks is no longer counted as agreement.
  - SQLite, Oxigraph and Neo4j: the three far-future edge queries are n/a (21/21, 3 n/a).
  - TypeDB: 12/12 with 1 n/a on the fixture (the positioned `find`, which both sides refused) and 14/14 with 10 n/a
    on the edge container (the two it refused on both sides among them).
  - PostgreSQL and HIF: no n/a. HIF's 23/24 is unchanged: `get ex:Dual` lacks `recorded_by` (finding 5).
- **Round trips (new, DESIGN §6.1).** A load of the fixture into an empty store now takes 4 to 11 engine calls on the
  five database backends (HIF writes its file once). Review 01 had counted 41 to 165 queries (R-02). The count is the
  same at 440 records, but for one more TypeDB insert batch.

**Checked, and not changed** (outside the rulings, or not a defect):
- **R-07's other two points.**
  - `NativeReads` still repeats `TableStore`'s argument and flag checks in the same order; conformance and the
    random parity test hold them equal. Public check helpers would widen the published interface beyond the ruling.
  - `Entry.__module__` is still `khg_contracts.store._table`: only a name in reprs.
- **`put` still reads id by id.** Its checks are P2 §6.2's and read the current version of each id, its references
  and the key groups: 34 to 45 calls for a `put` of one or two records on SQL, 25 to 26 on Neo4j, 8 to 16 on
  Oxigraph and TypeDB. That is why `put` is measured apart from `load` (DESIGN §6.1, §7). Its writes are now
  buffered and written once per write.
- **TypeDB rewrites a held instance in place.** Its attributes are batched (R-02). Its players and literals get
  queries of their own when they changed: a delete per role they had and one insert. Unchanged ones get none, as in
  the second load of the fixture.

**Hygiene.**
- The TypeDB server was cleaned: `khg-25695-3-32f362`, `khg-31374-2-b1fc5f`, `probe` and `lists` were dropped.
- TypeDB was restarted with monitoring off: 1729 and 8000 on 127.0.0.1, nothing on 4104. PostgreSQL 18.6, Neo4j
  2026.09.0 and TypeDB 3.13.6 are running.
- `put` is timed apart from `load`. `store.Timed` already records each method apart, and L1 is its `load` calls
  (DESIGN §7). `khg_bakeoff.trips` counts round trips per operation, `put` and `load` apart.
- No timing claim is made.
