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
| 7. Tests and CI | `khg-bakeoff/tests/` (6 files); job `khg-bakeoff` in `.github/workflows/ci.yml` | done; CI simulated locally |
| 8. Corrections ([R01] §11) | P2 DESIGN §6.5 amendments A1–A4; four notes in `kb/04-storage-and-formats/` | done; KB validator clean |
| 9. These notes | this file | |

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
  - `writing()` is the re-entrant form the store uses, so an adapter can add its header row to a load's
    transaction.
  - The default, `contextlib.nullcontext()`, leaves `MemoryStore` as it was.
- **`cannot_hold(record)` goes beyond the ruling's text.** Ruling 4 wants a refused instant reported through the
  existing error and report model, and ruling 2 wants adapters to import public names only. A hook in the base was
  the only way to do both without overriding private methods.
  - It runs as step 8 of the write path, after D018 and before anything is written. In `load` it runs after the
    flag check, record by record.
  - The refusal is a `ValidationError` without a code: no new code (§5 Q1).
- **Tests.** 13 in `tests/store/test_table.py`:
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
- A bulk load into an empty store skips the `UPDATE … SET tx_to` per record, since there is nothing to close.
- PostgreSQL keeps one schema per store in one database. That is faster than a database per scenario, and the
  database-level `LOCALE 'C'` covers every schema.

**The PostgreSQL key guard (deviation).**
- [R01] §2.2 sketched `key_period` as a guard for "the plain key invariant". Over every asserted fact it would
  refuse legal states: a preferred fact beside two overlapping normal ones satisfies D016.
- The guard therefore holds only current, asserted, **preferred** facts. No two of those hold together on one key,
  under D016, whatever the ranks of the others. It never refuses what the write path accepts, and it is a
  cross-check: if it ever fired on a `put`, the write would fail and the conformance run would show it.
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
- `bulk_extend` is used only for a load into an empty store, and a failure clears the store back to empty.

**Neo4j.**
- The adapter's indexes are named `khg_*` and include `BINDS(role)` as well as `BINDS(role, ident)`.
- The research probe's indexes (`binds_role`, `version_id`, `version_key`, `node_id`, `literal_ident`) were dropped
  from the local server first: an equivalent index under another name would collide.
- Binding kinds are written with `FOREACH` in one `UNWIND` query, so an empty list of one kind does not end the
  row.

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
- **What valid C1 can bring to TypeDB.** Under S014 no valid record repeats a filler in an unordered role, so
  TypeDB's collapse of repeated players is reached only through ordered roles, which it declares absent, or through
  a trusted load of invalid data. With the natural mapping, the four numbers show every TypeDB loss as a skipped
  record or a native-layer count, and every read agrees with the reference: 13/13 on the fixture, 24/24 on the
  edge container.

## 6. Verification (final runs, 2026-09-25)

| What | Where | Result |
|---|---|---|
| P2's full suite | repository root, dev venv (Python 3.11, every extra) | 5,910 passed, 1 skipped |
| khg-bakeoff, every backend | venv from the package's pins (Python 3.11), PostgreSQL 18.6, Neo4j 2026.09.0, TypeDB CE 3.13.6 running | 107 passed, 3 skipped (the refusal test skips where a backend holds the 16-digit year or lacks the flags) |
| khg-bakeoff, the CI job | fresh Python 3.10 venv, `pip install . "./projects/p1-store-bakeoff/khg-bakeoff[oxigraph,postgres,dev]"`, PostgreSQL only | 97 passed, 13 skipped |
| KB validator | `python3 tools/validate_kb.py` | 123 files, 0 errors, 0 warnings |
| Edge container | `khg-validate edge.c1.json --kind container --schema edge.relation-schema.json`; `make_edge.py` into a fresh directory | valid, 0 warnings; byte-identical |
| Pinned downloads | `curl -I` on the three URLs; the pinned TypeDB URL fetched and hashed | 200; sha256 3411c72a…8913, as [R01] |

The CI job's PostgreSQL service container (`postgres:18`) was not run here (no Docker daemon). The job was
simulated against the local PostgreSQL 18.6 build with the same environment variable. `pip download` confirmed
cp310 wheels for psycopg-binary 3.3.6 and pyoxigraph 0.5.11.

## 7. Open questions for the director

- **Q1.** A registered code for "the backend cannot hold this valid record" (DESIGN §9). Now: `ValidationError`
  without a code, `info["cannot_hold"]`.
- **Q2.** Does `on_missing="skip"` cover what `cannot_hold` refuses (DESIGN §9)?
- **Q3.** Add `khg-recorded-by` to the HIF profile's entity node (a minor profile version, P2)?
- **Q4.** TypeDB and slices that are not `complete`. A P3a slice will bind entities it does not hold. SQL, RDF and
  Neo4j store the reference as it is, but TypeDB needs a player instance, and the adapter now refuses such a fact
  (`player_not_held`). Should the second half give TypeDB stub instances (typed by the usage's first filler type),
  or count those facts as TypeDB losses?
