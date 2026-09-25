---
title: "P1 review 01: the first half (format and store bake-off)"
type: project
status: draft
created: 2026-09-25
---

# P1 review 01: the first half

The one review round of P1's first half. Scope: `12159f8` (khg-contracts, ruling 17), `bb7b4d4` and `39e339b`
(khg-bakeoff, results, CI job, corrections), the checkpoints between them and the rulings commit `123e9ad`; diffs
against `2d9380c` (P1) and `eb672d0` (`src/khg_contracts`). Every finding below was reproduced in this container
against the running PostgreSQL 18.6, Neo4j 2026.09.0 and TypeDB CE 3.13.6, or confirmed from the code; the scripts
are in the reviewer's scratchpad, and each finding gives the commands or code needed to repeat it. The machine-readable
copy is [review-01.json](review-01.json).

## Verdict

**The first half's claims reproduce, but the adapters are not yet fit for the second half's timings.**

- **Ruling 17 is safe.**
  - P2's suite is green.
  - A differential run of the pre-change `MemoryStore` (`eb672d0`) against the new one gave identical outcomes: 900
    random sequences, about 55,000 operations, including every error code, `info` and message, the final state and
    the clock.
- **Conformance and fidelity reproduce byte for byte.**
  - The six EARL reports, `summary.json`/`.md` and `fidelity.json`/`.md` are identical on re-running.
  - The inapplicable counts match the scenarios' `requires`.
  - The edge container regenerates byte-identically and is valid.
- **Three defects block the timing half** (high):
  - R-01: Oxigraph's `load` never reaches `bulk_extend`.
  - R-02: every adapter's `load` issues one to four point queries per record before its bulk write.
  - R-03: TypeDB cannot load a slice that is not `complete`; the whole load fails.
- **Medium findings:**
  - R-04: PostgreSQL's key guard refuses a legal write.
  - R-05: PostgreSQL's collation check misses ICU databases.
  - R-06: read strategies differ between adapters, which timings would measure.
  - R-07: the published interface leaves the header state private.
  - R-08: README finding 2 overclaims.
- The rest are low.

## Findings

| Id | Sev. | Lens | One line | Verdict |
|---|---|---|---|---|
| R-01 | high | 2 | Oxigraph `load` never calls `bulk_extend`; the whole load is one SPARQL `INSERT DATA` text | CONFIRMED |
| R-02 | high | 2 | `load` issues 1–4 point queries per record before the bulk write (TableStore's per-id checks) | CONFIRMED |
| R-03 | high | 3/4 | TypeDB `load(on_missing="skip")` of an incomplete container fails whole (`player_not_held`), contrary to rulings Q4/18 | CONFIRMED |
| R-04 | medium | 4 | PostgreSQL key guard refuses a legal batch that moves `preferred` between two facts (raw `ExclusionViolation`) | CONFIRMED |
| R-05 | medium | 4 | PostgreSQL collation check ignores the locale provider: an ICU database passes and sorts ids wrongly | CONFIRMED |
| R-06 | medium | 2 | Reads are not "one native query each"; round trips and Python work differ by adapter (N+1, `degree`, HIF in-process) | CONFIRMED |
| R-07 | medium | 1 | The public interface is incomplete: header and documents are private `TableStore` state that every adapter touches | CONFIRMED |
| R-08 | medium | 4 | README gate table and finding 2 hide HIF's silent loss of an entity's `recorded_by` | CONFIRMED |
| R-09 | low | 4 | Number 2's "literals as written" is read from a JSON text copy per binding | CONFIRMED |
| R-10 | low | 4 | Number 3 compares empty with empty on skipped hazards (TypeDB edge: 10 of 24) | CONFIRMED |
| R-11 | low | 6 | P2 §6.5 incidence row (A1) still describes a key constraint over every fact | CONFIRMED |
| R-12 | low | 7 | Engine and client licences are not stated in P1's deliverables | CONFIRMED |
| R-13 | low | 7 | The TypeDB config from `start-servers.sh` exposes monitoring on 0.0.0.0:4104 | CONFIRMED |
| R-14 | low | 5 | CI `postgres:18` floats; the Neo4j and TypeDB modules are never imported in CI | CONFIRMED |
| R-15 | low | 2 | Neo4j bulk `flush` partitions rows in O(n²) on a load into a non-empty store | CONFIRMED |

### R-01 (high, lens 2): Oxigraph `load` never uses `bulk_extend`

- **Where.** `khg-bakeoff/src/khg_bakeoff/oxigraph.py:317-324` (`load`), `:297` (the check in `transaction()`).
- **Defect.**
  - `load` sets `self._bulk = True` inside `with self.writing():` and resets it in a `finally` that runs when
    `return` leaves the `try`. That is before the `with` block exits.
  - `transaction()` tests `self._bulk` only after its `yield`, at commit, so it always sees `False`.
  - Every load, into an empty store too, therefore commits one `Store.update` whose text holds every quad as
    `INSERT DATA`.
  - The claims "`bulk_extend` into an empty Oxigraph store (cleared on a failure)" (DESIGN §2, line 63;
    IMPLEMENTATION-NOTES line 95) are false, and the clear-on-failure branch is dead and untested.
- **Evidence.**
  - A proxy on `store` recorded the calls during `OxigraphStore(...).load(fixture)`: `[('update', 116499)]`, one
    update of 116,499 characters, and no `bulk_extend`.
  - The store then held 871 quads.
- **Why it matters.** L1 on Oxigraph would time SPARQL text generation and parsing of a string of hundreds of MB, not
  the native bulk loader.
- **Fix.**
  - Hold the flag for the whole `with`:
    `self._bulk = True; try: with self.writing(): return TableStore.load(...) finally: self._bulk = False`.
  - Add a test that `bulk_extend` is called on a load into an empty store, and that a failed load leaves it empty.

### R-02 (high, lens 2): `load` makes 1–4 point queries per record before its bulk write

- **Where.**
  - khg-contracts: `src/khg_contracts/store/memory.py:220` (`_load`), `:265` (`_carry_loaded` → `table.current` per
    hyperedge id), `:341` (`_versions` → `table.latest_version` + `table.entries` per id).
  - The adapters: `sql.py:258-270`, `neo4j.py:324-339`, `typedb.py:579-586` and `:531` (TypeDB's `_cannot_hold` →
    `table.current` per entity).
- **Defect.**
  - The trusted bulk path first runs TableStore's per-id reads through the version table, and each is a backend round
    trip. This happens even when the store is empty, a fact the SQL and Neo4j adapters already compute
    (`bulk_empty`).
  - Only then do COPY, `executemany`, UNWIND or the TypeDB inserts run.
- **Evidence.** Round trips counted by wrapping each adapter's query function during `load` of P2's 40-record fixture
  into an empty store:

  | Backend | Round trips during the load |
  |---|---|
  | SQLite | 158 SELECTs and 3 `executemany` |
  | PostgreSQL | 159 queries, 3 other statements and 3 COPY |
  | Neo4j | 103 Cypher queries |
  | TypeDB | 120 TypeQL queries (36 records held) |
  | Oxigraph | 41 SPARQL queries |
  | HIF | 0 |

  - On SQLite the statements come from `_versions` (120) and `_carry_loaded` (36): 58 fact-row SELECTs, 58
    entity-row SELECTs and 40 `max(version)` queries.
- **Why it matters.** L1 ("`load` of the slice (trusted bulk)") would measure N client–server round trips per record,
  not the native bulk paths of DESIGN §2. The magnitude is inferred: the first half makes no timings.
- **Fix.**
  - When a bulk load starts on an empty store, let the table answer `current`, `entries` and `latest_version` from
    what it already knows (nothing held, plus its own buffer) without querying.
  - Or prefetch the container's ids in one query per chunk.
  - Or add an optional batched member (for example `prefetch(ids)`) to the version-table interface.
  - Add a test that bounds the round trips of a load.

### R-03 (high, lens 3/4): TypeDB cannot load a container that is not `complete`

- **Where.** `typedb.py:486-490` (the raise in `write_fact`), `:523-557` (`_cannot_hold` does not look at players).
- **Defect.**
  - A fact whose player is neither held nor in the load is refused only at `flush`. The refusal is a
    `ValidationError` with `cannot_hold.reason = player_not_held`, raised inside the write transaction.
  - `_missing` therefore never sees it, and `load(on_missing="skip")` fails as a whole.
  - The director's build ruling 4 (Q4) says such a fact "is refused and counted as a TypeDB loss". P2 ruling 18 says
    `load(..., on_missing="skip")` "skips such a record and counts it in the LoadReport".
- **Evidence.**
  - Container: P2's fixture minus `ex:Paris`, header `complete: false`.
  - `MemoryStore` and SQLite: `{'records': 39, 'versions': 39, 'skipped': []}`.
  - TypeDB: `ValidationError () {'id': 'f:born-louis14-paris', 'cannot_hold': {'reason': 'player_not_held',
    'player': 'ex:Paris'}}`, and 0 records held afterwards.
- **Why it matters.** Every P3a slice that is not `complete` fails to load into TypeDB.
- **Fix.**
  - Before `TableStore.load`, collect the ids and kinds the container brings.
  - In `_cannot_hold`, refuse a fact whose entity or fact players are neither held nor in that set. `_missing` then
    skips it and the facts that reference it.
  - Keep the flush-time check as a guard, and test with an incomplete container.

### R-04 (medium, lens 4): PostgreSQL's key guard refuses a legal write

- **Where.** `postgres.py:196-208` (`_added`) and `:123-124` (DDL). Claims at IMPLEMENTATION-NOTES line 80 ("It never
  refuses what the write path accepts") and DESIGN §3.1.
- **Defect.**
  - The guard row of each version is deleted and inserted statement by statement, in batch order, under a
    non-deferred `PRIMARY KEY … WITHOUT OVERLAPS`.
  - A legal batch that moves `preferred` from fact A to fact B therefore fails whenever B comes first.
  - The error is psycopg's `ExclusionViolation`, not a C2 error.
- **Evidence.**
  - `put(entities)`, then `put([king-14 rank preferred, king-14b = copy with rank normal])`, then
    `put([king-14b → preferred, king-14 → normal])`.
  - `MemoryStore` and SQLite: accepted (`king-14` normal, `king-14b` preferred).
  - PostgreSQL: `ExclusionViolation … conflicting key value violates exclusion constraint "key_period_pkey"`.
  - Conformance does not reach this case.
- **Fix.**
  - Buffer the guard changes of a write and apply them at flush: first delete the rows of every touched fact, then
    insert the new ones.
  - Or make the constraint `DEFERRABLE INITIALLY DEFERRED`, if PostgreSQL 18 allows it for `WITHOUT OVERLAPS`.
  - Add the swap as a test.

### R-05 (medium, lens 4): the collation check ignores the locale provider

- **Where.** `postgres.py:57-69`; `tests/test_adapters.py:180`. The claim in DESIGN §3.1 is "opening refuses any
  other collation".
- **Defect.**
  - The adapter creates its database with `LOCALE 'C' … TEMPLATE template0`, then accepts it when `datcollate` and
    `datctype` are `C`. It never reads `datlocprovider` or `datlocale`.
  - On a cluster initialised with the ICU provider, `LOCALE 'C'` gives an ICU database with locale
    `en-US-u-va-posix` and `datcollate = datctype = 'C'`. The check passes, and `ORDER BY id` and `id > after`
    follow ICU order.
- **Evidence** (reproduced here):
  - **A scratch cluster** (`initdb --locale-provider=icu --icu-locale=en-US --locale=C`, port 5419).
    - The adapter created `khg_bakeoff` as `('i', 'C', 'C', 'en-US-u-va-posix')` and accepted it.
    - 4 of 24 edge queries differed from `MemoryStore`: the order of the eight astral ids, the pages after `f:ł` and
      after `f:東京`, and the `find` on the astral catalyst.
    - That locale sorts the ids `f:Z, f:a, f:é, f:ł, f:ｚ, f:𠮷, f:東京, f:\ufffd`; code-point order is `f:Z, f:a, f:é,
      f:ł, f:東京, f:ｚ, f:\ufffd, f:𠮷`.
  - **A pre-existing ICU database with LC `C`** on the local server: 5 of 24 differed.
  - **The CI case, a libc cluster with a non-C default** (`C.utf8`, port 5420): handled.
    - The adapter's database is libc `C` and 24 of 24 edge answers match.
    - A pre-existing `C.utf8` database is refused.
    - CI's `en_US.utf8` cluster (the director's note) is this case.
- **Would a test catch it?**
  - `test_postgres_collation_and_key_guard` asserts only `datcollate == 'C'`, so it would pass.
  - `test_fidelity[postgres]` compares the edge answers with `MemoryStore`, so it would fail.
- **Fix.**
  - Create the database with `LOCALE_PROVIDER libc LOCALE 'C'`, or `builtin` with `BUILTIN_LOCALE 'C'`.
  - Check `datlocprovider` as well: `'c'` with `datcollate = 'C'`, or `'b'` with `datlocale = 'C'`.
  - Or put `COLLATE "C"` on the id and ref columns.
  - Extend the test with the provider and an ordering probe, for example `SELECT 'f:ｚ' < 'f:𠮷'`.

### R-06 (medium, lens 2): reads are not "one native query each", and differ by adapter

- **Where.** DESIGN §2 line 40; `oxigraph.py:432-438` (`_n_records`); `typedb.py:436-452` (`read`), `:624-702`
  (`_n_get`, `_n_find`); `khg_contracts/store/base.py` (`degree`, `get_many`, `supersession_walk`, `export`);
  `hif.py` (every read).
- **Defect.** The id selection is one native query everywhere except HIF. The rest differs:
  - **Record reassembly.** Batched in SQL (two queries per result set) and Neo4j (one), but one query per record in
    Oxigraph and TypeDB (two for a TypeDB entity).
  - **TypeDB `find`.** It fetches every candidate id with no `limit` pushed down. It reads each candidate record from
    `khg-bindings` to run the injective match in Python, then fetches the answers again.
  - **Derived methods.** `degree` is `len(incident())`, so it rebuilds every incident record to count them.
    `get_many` is one `get` per id, `supersession_walk` one `find` per level, `export` one record at a time.
  - **HIF.** Every read is `MemoryStore` logic over an in-memory index (by design, §3.5).
- **Evidence.**

  | Round trips | SQL | Neo4j | Oxigraph | TypeDB |
  |---|---|---|---|---|
  | `export("khg-json")` of the fixture | 4 | 2 | 41 | 59 (36 records) |
  | `incident(ex:KingOfFrance)`, 2 answers | 4 | 3 | 4 | 4 |
  | `find(position_held, [])`, 2 answers | 3 | 2 | 3 | 5 |
  | `get(f:king-14)` | 2 | 1 | 1 | 1 |

  - Every per-write cache (`SQLTable`, `OxigraphTable`, `Neo4jTable`, `TypeDBTable`) is reset at the end of the
    write, so no read is served from a Python mirror.
- **Why it matters.** Q1–Q14 would partly measure each adapter's strategy and Python loops rather than the engines:
  Q4 and Q10 on TypeDB and Oxigraph, Q12 everywhere, and HIF throughout. This is inferred, since nothing is timed yet.
- **Fix.**
  - Batch reassembly in Oxigraph (`VALUES`) and TypeDB (one fetch per id set).
  - Push `limit` down where TypeQL decides the match.
  - Give `degree` a native count, or report Q12 as "incident + len".
  - Label HIF's reads as in-process.
  - Record the round trips per query in DESIGN §6 before timing.

### R-07 (medium, lens 1): the published interface leaves the header and documents private

- **Where.**
  - `src/khg_contracts/store/table.py` (the docstring) and `memory.py:258-260`.
  - The adapters: `sql.py:273-279`, `oxigraph.py:282-330`, `neo4j.py:310-345`, `typedb.py:566-592`,
    `hif.py:130-182`, `native.py:175`.
- **Defect.**
  - `load` writes the kept header and the embedded documents to `TableStore._header` and `_documents`.
  - The interface offers no hook to persist them and no way to restore them, and its rollback contract covers only
    the table. Every adapter therefore reads, writes and restores these private attributes.
  - `NativeReads` also copies `TableStore`'s check order by hand.
  - The published names are re-exported from the private module: `Entry.__module__` is
    `khg_contracts.store._table`.
  - The imports are public, as ruling 2 asks, but the adapters still depend on private state, which is the risk of
    [R01] §9 risk 1.
- **Evidence.**
  - A `TableStore` subclass written to the documented contract rolls its table back when the commit fails.
  - After a failed `load`, the table holds 0 ids, but `info()["header"]` still reports the failed load's header, and
    the clock moved from `2026-10-01T00:00:00Z` to `…:01Z`.
- **Fix.**
  - Add documented hooks, for example `save_state(header, documents)` called inside the write's transaction and a
    `restore_state()` on rollback.
  - State in `store.table` what `TableStore` does not roll back (header, documents, clock).
  - Expose the read-argument checks as public helpers.

### R-08 (medium, lens 4): the gate table hides HIF's silent loss

- **Where.** `README.md:110-117` (the table) and `:123-124` (finding 2); the commit message of `39e339b` ("no silent
  loss anywhere").
- **Defect.**
  - HIF answers `get(entity)` without `recorded_by`, with no refusal.
  - `fidelity.json` records it as `store_field_differences`: 22 fixture entities and 20 edge entities.
    `fidelity.md` shows "1. Store fields: 22 / – / 20".
  - The README's column 1 shows HIF as "0, 0 / not loaded / 0, 0".
  - Finding 2 says "No backend loses anything silently. Every difference in a round trip is a record the store
    skipped", which contradicts finding 5.
- **Fix.**
  - Add the store-field count to column 1, as `fidelity.md` has it.
  - Qualify finding 2: no record is lost silently, but the HIF format silently drops an entity's `recorded_by`
    (finding 5, ruling 18).

### R-09 (low, lens 4): number 2 reads the literals from a JSON copy

- **Where.** `rows.py:168-182`, `sql.py:459-465`, `oxigraph.py:470-488`, `neo4j.py:466-481`, `fidelity.py:241-246`.
- **Defect.**
  - In the three layouts that score 20/20, the literal as written comes from a canonical-JSON text copy per binding:
    `binding.value_json`, `khg:valueJSON` (P2's projection) and `BINDS.value_json`.
  - Their multiset check also recomputes the identity from that JSON, not from the stored `ident`.
  - [R01] D5 defined number 2 as "without payload or JSON copies". DESIGN §5.1 narrowed it to "without the
    record-level copies" without saying so.
  - So "20/20 against TypeDB's 0/19" measures whether an adapter keeps one JSON string per binding.
- **Fix.**
  - Label the column "literal JSON per binding kept", and note the narrowing of D5 in DESIGN §5.1.
  - Or measure from typed native values.

### R-10 (low, lens 4): number 3 counts empty-against-empty answers

- **Where.** `fidelity.py:362-373`; `README.md:112-117`.
- **Defect.**
  - The reference drops what the backend skipped, so a query aimed at a skipped hazard compares an empty answer, or
    a refusal, with the same.
  - This follows DESIGN §5.1, but the headline "13/13, 24/24" reads as full agreement.
- **Evidence.**
  - Against the full-capability reference, the answer changes for 10 of TypeDB's 24 edge queries and 1 of its 13
    fixture queries.
  - For SQLite, Oxigraph and Neo4j it changes for the three far-future queries.
  - TypeDB's 24/24 includes 2 answers both sides refused, and its 13/13 includes 1.
- **Fix.** Report "same / compared (n touch skipped records, m both refused)".

### R-11 (low, lens 6): P2 §6.5 still describes a key constraint over every fact

- **Where.** `projects/p2-role-aware-hif/DESIGN.md:1604` (the amended incidence row) and A1/A4.
- **Defect.**
  - The row keeps `EXCLUDE … WITH &&` or `WITHOUT OVERLAPS` over all facts, with "rank exceptions are handled in
    code". Code cannot relax a database constraint, and the build found that such a constraint refuses legal D016
    states (IMPLEMENTATION-NOTES §3).
  - A4 omits the build's stronger TypeDB finding, SVL41: a relation type with no role cannot be defined.
- **Fix.** Say that the constraint covers current asserted **preferred** facts only, with the rest of D016 in code, and
  cite IMPLEMENTATION-NOTES §3. Add SVL41 to A4.

### R-12 (low, lens 7): licences not stated

- **Where.** `khg-bakeoff/README.md`, `start-servers.sh`, `README.md` results, `results/*.md`.
- **Defect.** None of P1's deliverables names a licence:
  - Neo4j Community: GPL v3.
  - TypeDB CE: MPL 2.0.
  - PostgreSQL: the PostgreSQL Licence.
  - psycopg: LGPL-3.0.
  - pyoxigraph: MIT or Apache-2.0.
  - The neo4j and typedb drivers: Apache-2.0.
  - SQLite: public domain.

  Only [R01] §2.1 and §9 do, and §9 asks that a report state them.
- **Fix.** Add a licence line per engine and client to `khg-bakeoff/README.md` and to the header of
  `start-servers.sh`.

### R-13 (low, lens 7): TypeDB monitoring listens on every interface

- **Where.** `start-servers.sh:153-155`; the script's comment at `:117` says "listen on 127.0.0.1".
- **Defect.** `diagnostics.monitoring.enabled: true` with port 4104.
- **Evidence.** `/proc/net/tcp` shows `0.0.0.0:4104` listening, on an inode owned by `typedb_server_bin` (PID 1935).
  Ports 1729 and 8000 are on 127.0.0.1.
- **Fix.** `monitoring: enabled: false`, or bind it to the loopback address.

### R-14 (low, lens 5): CI image not pinned; two adapters never imported in CI

- **Where.** `.github/workflows/ci.yml:146`.
- **Defect.**
  - `postgres:18` floats across 18.x. The run got 18.6-1.pgdg13+2 (the director's note), while ruling 10 pins engine
    versions.
  - With the extras `oxigraph,postgres`, `neo4j.py` and `typedb.py` are never imported in CI. Their pure-Python parts
    (`TypeQLSchema`, `label`, `version_row`) could be tested without a server.
  - The pyproject lists Python 3.10–3.13 for every extra.
- **Fix.**
  - Pin `postgres:18.6`, or pin a digest.
  - Add server-free unit tests for those modules, or install their clients in the job.

### R-15 (low, lens 2): quadratic partition in Neo4j's bulk flush

- **Where.** `neo4j.py:210-217`.
- **Defect.** `fresh = [r for r in rows if r not in closing]` tests list membership by dict equality, so it is
  O(n·c). Rows that close a previous version appear only on a load into a non-empty store.
- **Evidence.** The same expression over synthetic rows took 0.08 s, 0.30 s and 1.36 s for 2,000, 4,000 and 8,000
  rows.
- **Fix.** Partition in one pass, for example `closing, fresh = [], []` and append each row to one of them by its
  flag.

## Checked and fine

- **Lens 1: ruling 17.**
  - **P2's suite.**
    - CI gate-3.11's command (`-m "not evidence"`) gives 5,905 passed, 1 skipped and 5 deselected; the evidence
      tests give 5 passed.
    - That makes 5,910, the notes' figure, which counts the evidence tests too.
  - **The differential run.**
    - The pre-change `MemoryStore` came from `git archive eb672d0` and ran in a separate process. The sequences were
      drawn from every `given` and `when` step of the 114 scenarios, plus random reads.
    - It covered random capability subsets and loads with `raise` and `skip`.
    - Two seeds: 300 and 600 sequences, 13,710 and about 41,000 operations. The outputs were identical.
  - **The interface.**
    - `store.__all__` is unchanged.
    - Every table member the write path and the reads use is among the 13 of `MEMBERS`.
    - `_check_held` runs after every check, and all four events go through `_commit`.
    - `writing()` is re-entrant.
- **Lens 3: conformance.**
  - Re-running the full suite on all six adapters reproduced every EARL report and both summaries byte for byte.
  - The inapplicable counts equal those derived from the scenarios' `requires`: TypeDB 70/44 (goals 33,
    ordered_roles 29, special_values 33, transaction_time 7, history_export 1) and HIF 107/7.
  - The declared flags are `ALL_FLAGS` minus the declared absent ones.
  - No absent flag is emulated: positioned, special and unbound bindings are refused by `need()` or `cannot_hold`.
  - `key_constraint` is enforced in Python by the shared write path in every adapter, per ruling 2. It is not a
    backend property.
- **The khg-bakeoff suite** with all three servers: 107 passed, 3 skipped, as the notes say.
- **Lens 4: fidelity.**
  - `fidelity.json` and `fidelity.md` reproduce byte for byte.
  - Number 1 counts one difference per record, and a cascaded skip carries its reason.
  - The edge container:
    - `make_edge.py` regenerates it byte-identically.
    - `khg-validate` gives 0 errors and 0 warnings.
    - Every D5 item is present, and the dropped item is justified by S014.
  - The instant guard:
    - Every int64 adapter (SQLite, Oxigraph, Neo4j, TypeDB) stores `rows.instant` and clamps `as_of` with
      `query_instant`, Oxigraph's SPARQL filters included.
    - PostgreSQL stores `numeric` with ±Infinity.
    - The key ranges are `int8range`, and the clamp is monotone, so it cannot invent an overlap.
    - The boundaries are unit-tested.
  - Positions cannot overflow a typed column for valid C1 (S015, J006).
- **Lens 5: CI.**
  - The service block (image, trust auth, `5432:5432`, `pg_isready` health check) and the job-level endpoint
    variable are correct for a runner-host job.
  - The edge fixtures resolve through `conftest.py`.
  - The khg-bakeoff sources parse under Python 3.10.
  - The director reports the run on `123e9ad` passed: 97 passed, 13 skipped.
- **Lens 6: corrections.**
  - A1–A4 match [R01] §2.3, §3, §4, §5 and §8.
  - The four KB corrections are accurate and cited to the report and the probes.
  - The Neo4j claim was re-checked: `EXPLAIN` plans a `DirectedRelationshipIndexSeek` on `khg_binds_role`, and both
    `BINDS` indexes are `ONLINE`.
  - `tools/validate_kb.py`: 123 files, 0 errors, 0 warnings.
- **Lens 7: reproducibility.**
  - `start-servers.sh` pins every version.
  - The sha256 of the three local downloads matches the pins: `008ee189…`, `cdaa0905…`, `3411c72a…`.
  - Each step is guarded, so the script is idempotent, and it holds no secrets. TypeDB's default `admin`/`password`
    is the driver default.
  - No e-mail address appears in P1's files.
  - The two commits in the range by the repository owner are P3a commits.
  - The owner handle in `LICENSE` and `authors` follows the repository's convention.
  - No binaries or data are committed (the P1 tree is 1.8 MB of text).

## Could not check

- **The GitHub run itself.** There is no Docker here and network APIs were not used, so the director's report of the
  CI outcome is taken as given.
- **A libc `en_US.utf8` cluster.** The container has no such locale. It was simulated with a libc `C.utf8` cluster
  and an ICU cluster (R-05).
- **Other Python versions.**
  - P2's tests on Python 3.10 and 3.13 were not re-run.
  - The Neo4j and TypeDB drivers were not run on Python 3.10.
- **Fresh downloads** of the three engines: the local copies were hashed instead.
- **Oxigraph's atomicity under a crash** during a multi-operation update.
- **Any timing**, per ruling 7. The timing impact in R-01, R-02, R-06 and R-15 is inferred from round-trip counts and
  code.

## For the second half

- **Before any timing,** fix R-01, R-02 and R-03, and decide R-06: reassembly parity, a native `degree`, and HIF
  labelled as in-process.
- **Report `put` separately,** as [R01] D2 says. One `put` costs 31 round trips on SQLite, 35 on PostgreSQL, 24 on
  Neo4j, 17 on TypeDB and 10 on Oxigraph.
- **Clean the TypeDB server first.** It still holds `khg-25695-3-32f362` and `khg-31374-2-b1fc5f` from earlier runs,
  and `probe` and `lists` from the research.
