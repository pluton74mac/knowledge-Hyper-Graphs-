---
title: "P1 design: the store adapters, their conformance and their fidelity (first half)"
type: project
status: draft
created: 2026-09-25
---

# P1 design: the store adapters, their conformance and their fidelity (first half)

This is the design for the first half of P1 ([README](README.md); [PLAN §3–§5](../PLAN.md)). It rests on
[research 01](research/01-backends.md), cited as [R01], and follows the director's rulings on it (README, 2026-09-25)
exactly. It consumes C1 `khg-record/1.0.0` and C2 `khg-store/1.0.0` ([P2 DESIGN §2, §6](../p2-role-aware-hif/DESIGN.md))
and the version-table interface that P2 DESIGN §14 ruling 17 made public. The implementation is the package
[khg-bakeoff](khg-bakeoff/); decisions and deviations are in [IMPLEMENTATION-NOTES.md](IMPLEMENTATION-NOTES.md).

## 1. The rulings and what this half delivers

| Ruling on [R01] §10 | Where it lands |
|---|---|
| 1. Backends: PostgreSQL 18.6, Oxigraph (pyoxigraph 0.5.11), Neo4j Community 2026.09.0, TypeDB CE 3.13.6, HIF; SQLite 3.45.1 as the embedded control; no LadybugDB now | the six adapters (§3) |
| 2. Code sharing: the write path over a backend version table, native reads; the interface public in khg-contracts (ruling 17) | §2 |
| 3. Versions and transaction time as [R01] D3; TypeDB and HIF declare `transaction_time` and `history_export` absent | §3 |
| 4. Instants: `numeric` in PostgreSQL, an int64 guard at ±2^62 elsewhere, `int8range` for key ranges; a refused instant is a fidelity loss through the existing error and report model | §3.6 |
| 5. The four fidelity numbers and the edge-case container are the fidelity columns | §5 |
| 6. The query set is a draft until the second half | §6 |
| 7. No timing claims in the first half | nothing here is timed |
| 8. TypeDB: the natural mapping only (70 applicable) | §3.4 |
| 9. Ablations in the second half | §7 |
| 10. `start-servers.sh` with pinned versions and checksums; engines and data outside the repository | [start-servers.sh](start-servers.sh) |

**First-half gate columns.** For each backend: engine and version, embedded or client–server, the conformance
counts (applicable, passed, inapplicable as losses by flag) and the fidelity numbers. Load time and query latency
wait for P3a's slice (second half).

## 2. Adapter architecture

Every adapter is three layers ([R01] D2):

```text
  C2 reads   get, history, incident, find, find_by_key, iter_records ── NativeReads: one native query each
             get_many, degree, supersession_walk, export ──────────────── StoreBase, over the reads above
  C2 writes  put, apply, load ─── TableStore (khg-contracts store.table): the checks of P2 §6.2, the events,
                                  keys and transaction time, over the version table
  storage    the version table (13 members, ruling 17) ── the backend's own layout (§3); each write one transaction
```

- **The write path is shared, not copied.** `TableStore` is `MemoryStore`'s write path and reads parameterised by a
  version table. A backend gives a table class with the 13 members (`current`, `entries`, `entry_at`, `latest`,
  `latest_version`, `add`, `by_node`, `by_relation`, `by_key`, `by_ref`, `ids`, `__contains__`, `__len__`) over its
  own storage. The conformance suite then measures the stores, not five copies of the checks.
- **One transaction per write.** `TableStore.transaction()` wraps each `put`, `apply` and `load`. The table must
  read its own uncommitted writes inside it: SQL and Neo4j run every table query in the write's transaction,
  TypeDB in its write transaction, Oxigraph through an in-memory overlay that one `Store.update` commits, and HIF
  rebuilds its index from the file.
- **Native reads.** `NativeReads` checks arguments, flags and the relation in `TableStore`'s order, so a refusal is
  the same error. It then answers with one native query ([R01] §2.3, §3.3, §4.3, §5.4). The injective multiset
  match of `find` is `k` joins with pairwise distinct bindings (SQL `b_i.bid <> b_j.bid`, SPARQL
  `FILTER(?b_i != ?b_j)`, Cypher `b_i.bid <> b_j.bid`). TypeDB collapses a repeated player, so its `find` narrows
  by value in TypeQL and checks the multiset on the kept bindings. `supersession_walk` stays `StoreBase`'s: one
  indexed `find` per level. A recursive CTE would repeat a node reached at two depths ([R01] §2.3).
- **Native bulk load.** `load` keeps `TableStore`'s trusted checks (V001, D018) and writes in bulk:
  - `executemany` in SQLite and `COPY … FROM STDIN` in PostgreSQL;
  - `bulk_extend` into an empty Oxigraph store (cleared on a failure, since it is not transactional);
  - `UNWIND` batches of 500 in Neo4j;
  - one write transaction in TypeDB;
  - one file write for HIF.
- **Refusals.** `cannot_hold(record)` (ruling 17) names what a backend cannot hold:
  - an instant beyond the int64 guard (§3.6);
  - TypeDB's cases (§3.4);
  - a record whose bindings the row layout cannot split (only a trusted load can bring one).

  `put` and `apply` refuse such a record after every C2 check, with a `ValidationError` that has **no code** and
  `info["cannot_hold"]`. `load(on_missing="skip")` skips it and the records that reference it, and lists them in
  `LoadReport.skipped`. With `on_missing="raise"`, `load` raises the same error. No existing code fits (§9 Q1).
- **Public names only.** The adapters import `khg_contracts.store.table` and other public modules; nothing from
  `store._table`, `_writes` or `_events` ([R01] §9 risk 1).

## 3. Per-backend layout

The row layout is shared ([R01] §1, `khg_bakeoff.rows`). A hyperedge version is one fact row and one binding row
per binding; an entity version is its record as canonical JSON. The fact row holds relation, relation kind,
status, `status_ref`, rank, visibility, key digest, the four bound-table instants `s_lo`, `s_hi`, `e_lo`, `e_hi`,
the number of bindings, the store fields, and `payload`, the canonical JSON of every other field. The binding row
holds bid, role, position, direction, value kind, `ref`, `ident` (C1 value identity), `value_json` and extensions.
Query parameters go through the same identity and bounds functions, so equality in a backend is C1's value
identity.

### 3.1 Incidence table: SQLite 3.45.1 and PostgreSQL 18.6

```sql
meta(k PRIMARY KEY, v)                          -- latest transaction time, kept header, embedded documents
entity_version(id, version, tx_from, tx_to, recorded_at, recorded_by, record,  PRIMARY KEY (id, version))
fact_version(id, version, tx_from, tx_to, recorded_at, recorded_by, relation, rel_kind, status, status_ref, rank,
             visibility, key_digest, s_lo, s_hi, e_lo, e_hi, n_bindings, payload,  PRIMARY KEY (id, version))
binding(fact_id, version, bid, role, position, direction, value_kind, ref, ident, value_json, extensions,
        PRIMARY KEY (fact_id, version, bid))    -- bid, not (fact, entity, role): repeated fillers and literals
INDEX binding (ref, role); binding (role, ident); fact_version (relation, key_digest); (relation, id); (status_ref)
```

- **Versions** are immutable rows. A new version sets `tx_to` of its predecessor, a system-time period
  `[tx_from, tx_to)` in µs. `as_at` reads `tx_from <= t AND (tx_to IS NULL OR tx_to > t)`.
- **SQLite:** instants `BIGINT` with the guard (§3.6); `BINARY` collation (UTF-8 bytes, so code-point order); a
  database in memory or in a file, reopened with its kept header.
- **PostgreSQL:**
  - instants are `numeric` with ±Infinity for the unbounded sides;
  - payloads are `text`, not `jsonb`, so the canonical JSON comes back byte for byte;
  - one schema per store in a database created with `LOCALE 'C'` from `template0`; opening refuses any other
    collation ([R01] §7);
  - `COPY` for bulk loads.
- **The PostgreSQL key guard** ([R01] §2.3):
  - `key_period(relation, key_digest, valid int8range, fact_id)` with
    `PRIMARY KEY (relation, key_digest, valid WITHOUT OVERLAPS)`, which needs `btree_gist`;
  - it holds the definite window of each current, asserted, **preferred** fact on a key; a non-temporal key holds
    `(,)`, all time;
  - under D016 two preferred facts never hold together on one key, so the database states that part of the key
    invariant itself; the rank exceptions and the rest of D016 stay in the shared write path;
  - instants beyond int8 are clamped into the range, which can only miss an overlap, never invent one;
  - a trusted load whose data already break the rule (ruling 12 keeps such data) suspends the guard for that store
    instead of refusing the load.

  [R01] proposed the guard over every asserted fact. That would refuse legal states, such as a preferred fact
  beside two normal ones.

### 3.2 Reified RDF: Oxigraph through pyoxigraph 0.5.11

**One named graph per version**, `<urn:khg:<id>/v<n>>`. A hyperedge version's graph holds P2's
`project.rdf_relation_instance` of that version, plus the filter triples of [R01] §3.2: `khg:id`, rank,
visibility, relation kind, `statusRef`, `keyDigest`, the four instants as `xsd:integer`, `nBindings`, `payload`,
and per binding `khg:ident`, `valueKind` and `extensions`. An entity version's graph holds its record. The
default graph holds each version's metadata (`versionOf`, `version`, `txFrom`, `txTo`, `recordedAt`,
`recordedBy`) and the store's own (`<urn:khg:store>`: latest, header, documents). The store is on disk
(`Store(path)`). No triple term is needed (RDF 1.1 plus named graphs). Reads filter on the plain `khg:id` literal:
percent-encoding would change the order ([R01] §3.2).

### 3.3 Bipartite property graph: Neo4j Community 2026.09.0

```text
(:Node {id, kind})  (:Version {…fact row or entity row…})-[:VERSION_OF]->(:Node)  (:Meta {latest, header, documents})
(:Version)-[:BINDS {bid, role, position, direction, value_kind, ref, ident, value_json, extensions}]->(target)
    target = the (:Node) of an entity or fact | a shared (:Literal {ident}) | a per-binding (:Special {key})
```

- **Versions are nodes**, so transaction time is kept. Bindings point at identity nodes, so a new version of a
  nested fact does not orphan its referrers.
- **Namespaces.** Every node of a store carries the store's namespace label, because Community holds one user
  database and the runner opens two stores at once.
- **Indexes.** Range indexes on `:Version(id)`, `:Version(relation, key_digest)`, `:Version(relation)`,
  `:Node(id)`, `:Literal(ident)`, and on the relationship property `BINDS(role)` and `BINDS(role, ident)`.

### 3.4 TypeDB CE 3.13.6: the natural mapping (ruling 8)

- **The schema is generated** from the relation-type schema ([R01] §5.3), and every label is an injective
  encoding of the schema name:
  - entity types `sub` their first parent;
  - `khg-fact` owns the header attributes and `khg-tx`, the transaction time;
  - a usage with entity or fact fillers is a scoped role, played by each filler type and by any subtype that
    does not inherit it through the first-parent chain;
  - a usage with literal fillers is an owned attribute holding the value identity;
  - `khg-bindings` keeps the bindings as canonical JSON. Bids, positions, directions, binding extensions and the
    literals as written have no other home, and a repeated player or an equal literal in one role collapses.
    Reads reassemble records from it. `native_bindings` rebuilds them without it (§5, number 2).
- **Flags declared absent:** `ordered_roles`, `special_values`, `goals`, `transaction_time`, `history_export`
  ([R01] §5.5); 70 of 114 scenarios apply.
- **One instance per id.** A new version rewrites its instance in place: attributes by `update`, players and
  literals by `delete` and `insert`. Referrers keep pointing at it.
- **`cannot_hold`** refuses:
  - an entity with other than one type, or whose type would change;
  - a fact with no entity or fact binding: TypeDB deletes a relation without players at commit, and a relation
    type with no role cannot even be defined (SVL41), so a literal-only relation has no TypeQL form;
  - a special, unbound or positioned binding;
  - an undeclared relation, type or role.

  A fact whose player is not held is refused when it is written.
- **Writes** are buffered until the next read or the commit, and written entities first, then each fact after the
  facts it binds.

### 3.5 HIF file

- **The durable state is one role-aware HIF file** (`khg-hif/1.0.0`), written by `to_hif` to a temporary file and
  swapped in with `os.replace` at the end of each write. The in-memory index is then **rebuilt from the file** with
  `from_hif` ([R01] §6), so every read is served from what HIF kept. A failed write rebuilds the index from the
  file as it was.
- **Flags declared absent:** `transaction_time` and `history_export`; 107 of 114 scenarios apply.
- **Bookkeeping.** Two facts HIF has no place for travel in `hif:metadata` key `p1-store`: whether a document
  header is kept (without one the header is computed, S-EXP-009) and the latest transaction time.
- **Write cost.** Every write rewrites the whole file: O(size), the KB's anti-pattern for a system of record, kept
  as the interchange baseline.

### 3.6 Instants (ruling 4)

- **Units.** Valid-time instants are integer seconds on the proleptic Gregorian line (`record.bounds`);
  transaction time is integer µs.
- **PostgreSQL** stores `numeric`: exact at any C1 year, with ±Infinity; no guard.
- **Every other backend** stores int64, Oxigraph included (its `xsd:integer` comparisons fail beyond int64, [R01]
  §7):
  - −∞ and +∞ are the sentinels −2^62 and 2^62;
  - a finite instant must satisfy |x| ≤ 2^62 − 2;
  - an `as_of` parameter is clamped to ±(2^62 − 1). Every comparison with a stored value then gives the answer the
    exact value gives (tested exhaustively at the boundaries).
- **A record with an instant beyond the guard** is refused through `cannot_hold`, as §2 describes. It counts as a
  fidelity loss (number 1). The edge container's 16-digit year (3.2 × 10^23 s) is such a record.
- **Key ranges** are `int8range` (PostgreSQL's key guard), never `tstzrange`, which stops at 4713 BC.

## 4. Conformance

Each adapter runs khg-contracts' own runner (`store.conformance.run`) on the full 114-scenario suite, with a
factory that gives a fresh, empty store: a new in-memory database, directory, file, schema, namespace label or
database per call. `khg-bakeoff conformance` writes the EARL report per backend and a summary to
`results/conformance/`. A backend passes when no applicable scenario fails (PLAN §7). Every inapplicable scenario is
listed as a fidelity loss under the flag that made it inapplicable (P2 DESIGN §14 ruling 1).

## 5. Fidelity (ruling 5)

### 5.1 The four numbers

For each backend, on P2's `fixture.c1.json` and `fixture.history.c1.json` and on the edge container (§5.2):

1. **Container round trip.** `load(on_missing="skip")` → `export("khg-json")` (with the container's `content` and
   `as_at`) → `compare_containers` against the input.
   - It counts the records that differ, split into those the store skipped (with the reason: a missing flag,
     `cannot_hold`, or a reference to a skipped record) and any other difference (a silent loss).
   - `compare_containers` ignores the store fields, so they are compared separately, against `MemoryStore` holding
     the same records.
2. **Structural fidelity of the native layer.** Each held fact's bindings are rebuilt from the layout's per-binding
   structure alone, without the record-level copies: rows, binding triples, `BINDS` edges and their targets, role
   players and owned attributes, HIF incidences. `payload` and TypeDB's `khg-bindings` are left out. Counted:
   - per binding: bids, positions, directions, extensions and literals as written that survive;
   - per fact: whether the role–value multiset survives.
3. **Answer fidelity.** A query set is compared with `MemoryStore`'s answers: ids in order for lists, the record for
   `get`, steps and terminals for walks, the count for `degree`.
   - A refusal counts as the same answer when the reference refuses alike.
   - The reference has the backend's flags and holds the container minus what the backend skipped, so only the
     queries are compared.
   - First half: [R01]'s 13 hand queries on the fixture, its 85 transaction-time checks on the history fixture,
     and 24 edge queries. The full query set comes with P3a's slice.
4. **Inapplicable scenarios** by flag, from the conformance run.

Results: [results/fidelity.json](results/fidelity.json) and [results/fidelity.md](results/fidelity.md), with the
engine versions, the contract versions and the khg-contracts commit.

### 5.2 The edge-case container

[fixtures/edge.c1.json](fixtures/edge.c1.json) (41 records) under [fixtures/edge.relation-schema.json](fixtures/edge.relation-schema.json):
P2's fixture schema with the id `p1-edge` and two relations added. `measured_constant` takes literals only, since no
fixture relation admits a fact without an entity. `alias_list` has an ordered literal role. The builder
[fixtures/make_edge.py](fixtures/make_edge.py) regenerates both files byte for byte, and `khg-validate` reports
0 errors and 0 warnings.

| [R01] D5 item | Records | Aimed at |
|---|---|---|
| astral and full-width ids | `ex:𠮷` bound by `f:a`, `f:Z`, `f:é`, `f:ł`, `f:東京`, `f:ｚ`, `f:\ufffd`, `f:𠮷`; `ex:ｚ` | code-point order and keyset pagination ([R01] §7) |
| a 16-digit-year literal | `f:far-future`, a `position_held` from year 9999999999999999 | instants beyond int64 (§3.6) |
| two equal literals in one role | `f:aliases-twice`: `alias` "Tokyo Station"@en at positions 1 and 2 | owned attributes are sets in TypeDB |
| a multi-typed entity | `ex:Dual` (Place, Station), bound by `f:dual-profile` | one type per TypeDB instance |
| an all-unbound goal | `g:who-what` | a relation without players |
| a literal-only fact | `f:constant-c` (`measured_constant`) | a relation without players; a relation type without roles |
| a diamond of supersessions | `f:dia-a` → `f:dia-b`, `f:dia-c` (`m:dia-1`, conflation) → `f:dia-d` (`m:dia-2`, `m:dia-3`) | a walk that reaches one fact twice ([R01] §2.3) |

**Dropped:** "one filler repeated in one unordered role". C1 refuses it (KHG-S014, "duplicate filler in an
unordered role"). Its ordered form is already P2's `f:route-1` (`stop` YYZ at positions 1 and 3). "Two equal
literals in one role" is refused by S014 in an unordered role for the same reason, so it is written in an
ordered one.

## 6. Draft query set (D6; a draft, frozen in the second half against P3a's slice)

[R01] D6 unchanged:
- **Parameters** are drawn with fixed seeds, stratified by degree (1–5, 6–100, hubs) and arity bin (0–1, 2, 3, 4,
  5+).
- **Runs:** warm (median and p95 of 20) and cold (first run after a restart).

| Id | Call | Stresses |
|---|---|---|
| L1 | `load` of the slice (trusted bulk) | load time |
| Q1 | `get(id)` × 1,000 | point lookup and reassembly |
| Q2 | `get(id, as_at=t)` on a history slice | version selection |
| Q3 | `incident(e)`, low degree | the incidence index |
| Q4 | `incident(hub, limit=100, after=…)` to the end | pagination on hubs |
| Q5 | `incident(e, role=r, relation=R)` | role and relation filters |
| Q6 | `incident(e, where=Where(as_of=t))`, definite and possible | valid-time filter |
| Q7 | `find(R, [one entity pattern])` | a single-role lookup |
| Q8 | `find(R, [entity, qualifier time literal])` | a join with literal identity |
| Q9 | `find(R, full multiset, match="exact")` | exact match |
| Q10 | `find(R, [])` paged through | relation scan |
| Q11 | `find_by_key(R, key, where=Where(as_of=t))` | the key index with valid time |
| Q12 | `degree(hub)` | counting |
| Q13 | `supersession_walk(id)`, chains of 1–5 | recursion |
| Q14 | two-hop neighbourhood through the fact layer | traversal |
| X1, X2 | `export("khg-jsonl")`, `export("hif")` | export |

## 7. Deferred to the second half

- **Timing** ([R01] D7): load time and query latency through `store.Timed`, embedded and client–server rows
  labelled, peak RSS and disk after load.
- **Ablations** ([R01] D9): `role` as an edge property against one relationship type per role in Neo4j; binding
  nodes against binding nodes plus role-predicate shortcuts in RDF.
- **The frozen query set** (§6), number 3 on it, and the four numbers on P3a's slice.
- **Native one-query walks**: the recursive CTE with minimum-depth de-duplication, Neo4j's quantified path, TypeQL's
  recursive function.
- **LadybugDB** 0.20.4, if a second embedded property-graph row is wanted (ruling 1).
- **TypeDB players outside the store.** A slice that is not `complete` binds entities it does not hold, and TypeDB
  needs a player instance. Stub instances are a second-half decision.

## 8. Package, tests, CI

- **Package.** `khg-bakeoff/` (MIT): `rows`, `native`, `shared`, `sql`, `sqlite`, `postgres`, `oxigraph`, `neo4j`,
  `typedb`, `hif`, `backends`, `conformance`, `fidelity`, `provenance` and `cli` (`khg-bakeoff conformance|fidelity`).
  The clients are pinned as extras.
- **Tests.** The embedded backends run the full suite and the fidelity checks. The server backends run when
  `KHG_BAKEOFF_POSTGRES`, `KHG_BAKEOFF_NEO4J` or `KHG_BAKEOFF_TYPEDB` names an endpoint, and skip otherwise.
- **CI.** Job `khg-bakeoff`: Python 3.10, `.[oxigraph,postgres,dev]`, and a `postgres:18` service container, so
  PostgreSQL runs in CI too.

## 9. Open questions (for the director)

- **Q1. A code for "the backend cannot hold this valid record".** No registered code fits. C010 is a layer-C
  finding about the record itself; `MemoryStore.load` uses it only for what it cannot index. So the refusal is a
  `ValidationError` without a code, like ruling 5's `ConcurrencyError`. A code (a 1.1 candidate) would let callers
  tell a backend's limit from an invalid record.
- **Q2. `on_missing="skip"` for refusals.** P2 §6.2 defines `skip` for records that need a missing flag. P1 also
  skips what `cannot_hold` refuses, so that a load reports its losses instead of failing whole. Does the contract
  read so?
- **Q3. HIF drops an entity's `recorded_by`.** The profile's entity node has `khg-version` and `khg-recorded-at`
  but no `khg-recorded-by` (P2 DESIGN §4.2); edges have all three. The HIF store therefore answers `get(entity)`
  without it (number 3; 22 of 22 fixture entities, number 1 store fields). Adding `khg-recorded-by` to entity nodes
  would be a minor profile change.
