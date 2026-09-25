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

**The rulings on review 01** (README): R-06, what "native reads" means for timing, lands in §2 and §6.1; R-07, the
public table interface, in §2. Every fix of the review is listed in IMPLEMENTATION-NOTES §8.

**First-half gate columns.** For each backend: engine and version, embedded or client–server, the conformance
counts (applicable, passed, inapplicable as losses by flag) and the fidelity numbers. Load time and query latency
wait for P3a's slice (second half).

## 2. Adapter architecture

Every adapter is three layers ([R01] D2):

```text
  C2 reads   get, history, incident, find, find_by_key, iter_records,  ── NativeReads: filters, limit and counts in
             get_many, degree, supersession_walk                          the engine; the records of one call in a
                                                                          bounded number of queries (§6.1), rebuilt
                                                                          by rows.record_of
             export ─────────────────────────────────────────────────── StoreBase, over iter_records (one scan)
  C2 writes  put, apply, load ─── TableStore (khg-contracts store.table): the checks of P2 §6.2, the events,
                                  keys and transaction time, over the version table
  storage    the version table (13 members and the optional prefetch, ruling 17 and its addition) ── the backend's
             own layout (§3); each write one transaction
```

- **The write path is shared, not copied.** `TableStore` is `MemoryStore`'s write path and reads parameterised by a
  version table. A backend gives a table class with the 13 members (`current`, `entries`, `entry_at`, `latest`,
  `latest_version`, `add`, `by_node`, `by_relation`, `by_key`, `by_ref`, `ids`, `__contains__`, `__len__`) over its
  own storage. The conformance suite then measures the stores, not five copies of the checks.
- **One transaction per write.** `TableStore.transaction()` wraps each `put`, `apply` and `load`. The table must
  read its own uncommitted writes inside it: SQL and Neo4j run every table query in the write's transaction,
  TypeDB in its write transaction, Oxigraph through an in-memory overlay that one `Store.update` commits, and HIF
  rebuilds its index from the file.
- **Native reads** (the director's ruling on review 01, R-06).
  - `NativeReads` checks arguments, flags and the relation in `TableStore`'s order, so a refusal is the same error.
  - Every read pushes its filters, `after`, `limit` and counts into the engine where the engine can express them.
    The ids come from one native query ([R01] §2.3, §3.3, §4.3, §5.4).
  - The injective multiset match of `find` runs in the engine:
    - SQL, SPARQL and Cypher use `k` joins with pairwise distinct bindings (`b_i.bid <> b_j.bid`,
      `FILTER(?b_i != ?b_j)`).
    - TypeQL links each value's player or owned attribute, and gives each `any` one more binding of its role (the
      branches split the `any` between players and literals). This is exact because TypeDB holds no fact with two
      bindings of one role and one value identity (`cannot_hold`, §3.4).
  - `degree` is a native count.
  - The records of one call are fetched in a bounded number of queries, never one query per record: one or two per
    chunk of ids (§6.1). `get_many` is one batched read, and `iter_records` and `export` are one scan.
  - One shared function, `rows.record_of`, rebuilds every record from the rows an engine returns (a fact row with
    its binding rows, or an entity row). The Python work per row is therefore the same on every backend, and the
    engine part is what differs.
  - `supersession_walk` is `StoreBase`'s breadth-first walk with one native lookup and one batched read per level,
    not one `find` per fact. A recursive CTE would repeat a node reached at two depths ([R01] §2.3).
  - HIF is a file format: its reads are `TableStore`'s over the index rebuilt from the file, labelled
    "file, read in memory".
- **Native bulk load** (review 01, R-01, R-02). `load` keeps `TableStore`'s trusted checks (V001, D018).
  - Its checks read no record on its own. `TableStore.load` first calls the table's `prefetch(records)`, the
    optional member of the addition to ruling 17. The table then reads the loaded ids' versions in one query per
    table and chunk, or none at all when the store is empty, and answers the checks from memory.
  - It then writes in bulk:
    - `executemany` in SQLite and `COPY … FROM STDIN` in PostgreSQL, with the previous versions closed in one
      statement per chunk;
    - `bulk_extend` into an empty Oxigraph store (not transactional: on a failure the store is cleared and its own
      triples put back), and one transactional `update` otherwise;
    - `UNWIND` batches of 500 in Neo4j;
    - batched inserts in TypeDB's one write transaction: a pipeline of guarded `match`–`insert` stages per 200 facts;
    - one file write for HIF.
- **Refusals.** `cannot_hold(record)` (ruling 17) names what a backend cannot hold:
  - an instant beyond the int64 guard (§3.6);
  - TypeDB's cases (§3.4), among them, in a load, a fact whose player is neither held nor loaded (review 01, R-03);
  - a record whose bindings the row layout cannot split (only a trusted load can bring one).

  `put` and `apply` refuse such a record after every C2 check, with a `ValidationError` that has **no code** and
  `info["cannot_hold"]`. `load(on_missing="skip")` skips it and the records that reference it, and lists them in
  `LoadReport.skipped`. With `on_missing="raise"`, `load` raises the same error. No existing code fits (§9 Q1).
- **Public names only.** The adapters import `khg_contracts.store.table` and other public modules; nothing from
  `store._table`, `_writes` or `_events` ([R01] §9 risk 1). They persist and restore the kept header through its
  public accessors, `kept_header` and `kept_documents`. `TableStore` restores both when a write fails (the addition
  to ruling 17; review 01, R-07).
- **Round trips are counted.** Each adapter counts the calls it makes to its engine (`shared.Trips`), at the one
  place it makes them; `khg-bakeoff trips` reports them per operation (§6.1).

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
  - code-point order whatever the locale (review 01, R-05):
    - every text column is `COLLATE "C"`;
    - one schema per store, in a database created with `LOCALE_PROVIDER libc LOCALE 'C'` from `template0`, because
      an ICU cluster would otherwise give it the ICU provider;
    - opening reads the database's locale provider as well as its collation. It refuses anything but libc `C` (or
      builtin `C`), and checks the order of three pairs of ids that ICU orders the other way ([R01] §7);
  - `COPY` for bulk loads.
- **The PostgreSQL key guard** ([R01] §2.3):
  - `key_period(relation, key_digest, valid int8range, fact_id)` with
    `PRIMARY KEY (relation, key_digest, valid WITHOUT OVERLAPS)`, which needs `btree_gist`;
  - it holds the definite window of each current, asserted, **preferred** fact on a key; a non-temporal key holds
    `(,)`, all time;
  - under D016 two preferred facts never hold together on one key, so the database states that part of the key
    invariant itself; the rank exceptions and the rest of D016 stay in the shared write path;
  - instants beyond int8 are clamped into the range, which can only miss an overlap, never invent one;
  - a write changes the guard once, at its end: it deletes the rows of every fact it touched, then inserts the new
    ones. A batch that moves `preferred` from one fact to another is therefore accepted in either order
    (review 01, R-04);
  - if the guard still refuses a write the write path accepted, the caller gets `KeyCollision` with code KHG-D016,
    never a psycopg error;
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
percent-encoding would change the order ([R01] §3.2). A read fetches the versions of its ids in one `SELECT` per
chunk of 500 (`VALUES ?f { … }`), one solution per binding, which `rows.record_of` rebuilds.

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
- **Writes** are buffered and written in `UNWIND` batches when the write ends. The rows that close a stored version
  go first, partitioned in one pass (review 01, R-15).

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
  - two bindings of one role with one value identity: players and owned attributes are sets. The TypeQL `find` is
    exact because no held fact has such a pair;
  - an undeclared relation, type or role;
  - in a load, a fact whose entity or fact player is neither held nor brought by the load. Build ruling Q4 and P2
    ruling 18: `on_missing="skip"` skips and counts it, with the facts that nest it (review 01, R-03). A load of a
    slice that is not `complete` therefore loads the rest. The write refuses a missing player again, as a guard.
- **Writes** are buffered until the next read or the commit, and written entities first, then each fact after the
  facts it binds.
  - New instances are inserted in batches: 200 entities per `insert`, and 200 facts per query as a pipeline of
    guarded `match`–`insert` stages. Each stage checks the count of the stage before it, so a fact whose players
    are missing fails the batch instead of vanishing.
  - A new version of a held instance is rewritten in place: its attributes by one pipeline of guarded `update`
    stages per 200 records, and its players or literals by their own queries only when they changed.
- **Reads** run in one read transaction per call.
  - Ids are grouped with `reduce … groupby`: in TypeDB CE 3.13.6, `distinct` keeps duplicate rows across
    disjunction branches that bind different variables.
  - The records of a call come from one `fetch` per 100 ids.

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
- **Reads** are `TableStore`'s logic over the in-memory index: rows labelled "file, read in memory" (R-06).
- **A write is decoded before it replaces the file.** A snapshot HIF cannot hold fails the write and leaves the file
  as it was. An example is a fact on an entity the store does not hold, which gives an incidence on an undeclared
  node (KHG-D002 in `from_hif`). Such a slice therefore cannot be loaded whole (§9 Q5).

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
     `cannot_hold`, or a reference to a skipped record) and those lost silently.
   - `compare_containers` ignores the store fields, so they are compared separately, against `MemoryStore` holding
     the same records. A record whose store fields differ is a silent loss too (review 01, R-08): the HIF format
     drops an entity's `recorded_by`.
2. **Structural fidelity of the native layer.** Each held fact's bindings are rebuilt from the layout's native
   structure alone: rows, binding triples, `BINDS` edges and their targets, role players and owned attributes, HIF
   incidences.
   - No JSON copy of a record or of a value is read: not `payload` or TypeDB's `khg-bindings`, and not the
     per-binding `value_json` or `khg:valueJSON` either (review 01, R-09). This is [R01] D5 as written ("without
     payload or JSON copies"). The first half had read literals from `value_json`, which narrowed D5 without saying
     so.
   - A literal is rebuilt from the value identity the layout stores: `ident` in SQL, RDF and Neo4j (the key the
     engine compares on), and the owned attribute in TypeDB. That identity is the canonical literal for every
     datatype but time, whose identity is its window and precision. A time literal therefore counts as lost as
     written in every layout but HIF, whose literal nodes carry the literal as written.
   - Counted per binding: bids, positions, directions, extensions and literals as written that survive. Counted per
     fact: whether the role–identity multiset survives, from the stored identities.
3. **Answer fidelity.** A query set is compared with `MemoryStore`'s answers: ids in order for lists, the record for
   `get`, steps and terminals for walks, the count for `degree`.
   - A refusal counts as the same answer when the reference refuses alike.
   - The reference has the backend's flags and holds the container minus what the backend skipped, so only the
     queries are compared.
   - Some queries touch what the backend skipped or lacks: their reference answer differs from that of a full
     reference, which has every flag and holds the whole container. They are not compared and are shown as n/a
     (review 01, R-10). Otherwise such a query would compare empty with empty, or a refusal with the same refusal.
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

### 6.1 Round trips per operation and adapter (measured)

The director's ruling on review 01 (R-06) asks for this table before any timing. It is measured, not estimated:
- **How.** Every adapter counts the calls it makes to its engine at the one place it makes them (`shared.Trips`).
  `khg-bakeoff trips` runs these operations in this order on P2's gate fixture, one store per backend
  ([results/roundtrips.md](results/roundtrips.md), `.json`, at khg-contracts `914b810`).
- **What counts as a call.** A SQL statement, SPARQL query or update, `bulk_extend`, Cypher query or TypeQL query,
  and the begin and commit of each write transaction (and of TypeDB's read transaction).
- **Where the calls go.** SQLite's and Oxigraph's calls are in-process. HIF counts the file writes and reads; its
  reads are its in-memory index ("file, read in memory"), so they make none.
- **`put` and `load`.** `put` is listed apart from `load` ([R01] D2). Its reads are the write path's checks of P2 §6.2:
  the current version of each id, the references, the key groups and the supersessions.

| Operation | SQLite | PostgreSQL | Oxigraph | Neo4j | TypeDB | HIF |
|---|---|---|---|---|---|---|
| `load` of the fixture into an empty store (40 records) | 10 | 11 | 4 | 7 | 9 | 1 |
| `get` a fact (`f:king-14`) | 2 | 2 | 1 | 1 | 2 | 0 |
| `get` an entity (`ex:Paris`) | 2 | 2 | 1 | 1 | 3 | 0 |
| `get_many` of 10 ids | 3 | 3 | 1 | 1 | 3 | 0 |
| `history` of `f:king-14` | 2 | 2 | 1 | 1 | 2 | 0 |
| `incident(ex:KingOfFrance)`, 2 answers | 4 | 4 | 3 | 3 | 4 | 0 |
| `incident(ex:KingOfFrance, limit=1)` | 4 | 4 | 3 | 3 | 4 | 0 |
| `degree(ex:KingOfFrance)` | 2 | 2 | 2 | 2 | 3 | 0 |
| `find(position_held, [position KingOfFrance])` | 3 | 3 | 2 | 2 | 3 | 0 |
| `find(position_held, [])` | 3 | 3 | 2 | 2 | 3 | 0 |
| `find_by_key(position_held, KingOfFrance)` | 3 | 3 | 2 | 2 | 3 | 0 |
| `supersession_walk(f:born-skłodowska-kraków)`, 2 levels | 6 | 6 | 4 | 4 | 5 | 0 |
| `export("khg-json")` of the store | 3 | 3 | 1 | 1 | 3 | 0 |
| `put` of one new version (`f:king-14`) | 34 | 39 | 11 | 26 | 16 | 1 |
| `put` of two new records (an entity and a fact) | 43 | 45 | 8 | 25 | 15 | 1 |
| `load` of the fixture again (40 held ids, new versions) | 15 | 17 | 4 | 8 | 11 | 1 |

**How the calls break down.**
- **Reads.** The id query, one check where the read has one (is the node a fact, for `incident` and `degree`), then
  the records:
  - SQL: fact rows, their binding rows, and entity rows for the other ids, per chunk of 500 ids.
  - Oxigraph and Neo4j: one query per chunk of 500 ids.
  - TypeDB: one `fetch` for facts and one for entities per 100 ids, plus the read transaction.
- **A load into an empty store.** The emptiness check and the latest time, then the bulk writes (one per table in
  SQL), the header and the commit. It reads no record on its own (R-02).
- **A load into a store that holds its ids.** It adds one prefetch per table and chunk (three in SQL, one in
  Oxigraph and Neo4j, two in TypeDB), and one batched close of the previous versions.

**Growth with the store.** The same operations were run on 40 and 440 records: the fixture plus 200 people born in
`ex:Paris`.
- Unchanged:
  - a load into an empty store, except on TypeDB (one more insert per 200 entities and per 200 facts);
  - the export and `degree`;
  - `get_many` of every id, except on TypeDB (two queries per 100 ids);
  - a load of held ids, except on TypeDB.
- `incident(ex:Paris)` with 200 answers adds the one or two record queries of the new chunk.
- `tests/test_loads.py` and `tests/test_reads.py` hold these bounds.

## 7. Deferred to the second half

- **Timing** ([R01] D7): load time and query latency through `store.Timed`, embedded and client–server rows
  labelled ("file, read in memory" for HIF), peak RSS and disk after load.
  - `put` is timed apart from `load` ([R01] D2). L1 is `Timed`'s `load` calls alone. A `put` runs the full write
    path of P2 §6.2 and its per-record checks, so it gets its own row and is never folded into L1.
  - The round trips of §6.1 are recorded beside each time.
- **Ablations** ([R01] D9): `role` as an edge property against one relationship type per role in Neo4j; binding
  nodes against binding nodes plus role-predicate shortcuts in RDF.
- **The frozen query set** (§6), number 3 on it, and the four numbers on P3a's slice.
- **Native one-query walks**: the recursive CTE with minimum-depth de-duplication, Neo4j's quantified path, TypeQL's
  recursive function.
- **LadybugDB** 0.20.4, if a second embedded property-graph row is wanted (ruling 1).
- **Slices that are not `complete`.** TypeDB skips and counts a fact whose player it does not hold (build ruling
  Q4, R-03). The HIF store cannot load such a slice at all (§3.5, §9 Q5).

## 8. Package, tests, CI

- **Package.** `khg-bakeoff/` (MIT): `rows`, `native`, `shared`, `sql`, `sqlite`, `postgres`, `oxigraph`, `neo4j`,
  `typedb`, `hif`, `backends`, `conformance`, `fidelity`, `trips`, `provenance` and `cli`
  (`khg-bakeoff conformance|fidelity|trips`). The clients are pinned as extras.
- **Licences.** The engines and clients are listed with their licences in
  [khg-bakeoff/README.md](khg-bakeoff/README.md#licences) and the header of `start-servers.sh` (R-12).
- **Tests.** The embedded backends run the full suite and the fidelity checks. The server backends run when
  `KHG_BAKEOFF_POSTGRES`, `KHG_BAKEOFF_NEO4J` or `KHG_BAKEOFF_TYPEDB` names an endpoint, and skip otherwise.
- **CI.** Job `khg-bakeoff`: Python 3.10, `.[oxigraph,postgres,dev]`, and a `postgres:18.6` service container
  (pinned, R-14), so PostgreSQL runs in CI too; an ICU database is created on it for the collation test. A step
  imports the Neo4j and TypeDB adapters without their clients, and `tests/test_offline.py` checks their pure-Python
  parts without servers.

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

Q1 to Q4 were ruled (README, the director's rulings on the build). New, from the fixes of review 01:

- **Q5. The HIF store and slices that are not `complete`.**
  - For a fact on an entity the container does not hold, `to_hif` writes an incidence on a node the file does not
    declare, and `from_hif` refuses that file (KHG-D002).
  - The HIF store therefore cannot load such a slice at all. It now fails the load cleanly and keeps its file (§3.5).
  - The analogue of build ruling Q4 would skip and count such a fact through `cannot_hold`. That would be a HIF loss,
    like TypeDB's. The alternative, declaring the node, is P2's `to_hif`, whose contract this is.
