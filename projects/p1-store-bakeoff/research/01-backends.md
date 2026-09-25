---
title: "P1 research 01: the five backends as they run here, and how each implements C2"
type: survey
status: draft
created: 2026-09-25
---

# P1 research 01: the five backends as they run here, and how each implements C2

This report covers the first half of P1 ([README](../README.md); [PLAN §3–§5](../../PLAN.md)). Every candidate
backend was installed and run in this container, P2's gate fixture was loaded into each in its natural layout, and
the C2 read operations were answered with that backend's own query language. The contract is C2 `khg-store/1.0.0`
([P2 DESIGN §6](../../p2-role-aware-hif/DESIGN.md)), with its records (§2), its projections (§2.10) and the
director's ruling 1 on conformance (§14).

**Evidence labels.** [run] means executed in this container on 2026-09-25, and the probe and output files are
named. [read] means taken from a document or source file named inline. [derived] means reasoned from [run] and
[read] evidence. [unverified] means not checked. The probes are in [probes/](probes/) and their outputs in
[probes/out/](probes/out/).

## Summary

- **Every candidate for the first three layouts answers every C2 read natively on the fixture** [run], DuckPGQ
  aside. SQLite, DuckDB, PostgreSQL 16 and 18, Oxigraph, rdflib, Neo4j, Memgraph, FalkorDB, Kùzu and LadybugDB
  each pass all 46 conformance scenarios that only load the fixture and read. Each also passes 85 of 85 transaction-time checks on
  `fixture.history.c1.json` and exports the fixture with 0 differences.
- **TypeDB CE 3.13.6 runs here.** It passes the 19 of those 46 scenarios that apply to it. The
  other 27 are inapplicable. P2's figure of **70 of 114 applicable is confirmed** for the natural mapping, which lacks
  `ordered_roles`, `special_values`, `goals`, `transaction_time` and `history_export`. Several gaps were probed
  directly [run]:
  - role-player lists are "not yet implemented" (REP254);
  - a relation without role players is deleted at commit;
  - a repeated player in one role collapses to one;
  - bids, positions, directions and binding extensions have no native home.
- **The HIF file store** is `MemoryStore` persisted as one role-aware HIF file and reloaded from that file after
  every write. It passes **107 of 114** scenarios. The other 7 are inapplicable because the file holds no history
  [run].
- **Code sharing works through the version table, not through `StoreBase` alone.** `StoreBase` derives only six
  reads. The write path (checks D002–D020, keys, the four events) lives in `MemoryStore`'s mixins over a
  13-member table interface. Re-implementing that table on SQLite gives a store that passes **114 of 114** [run].
- **Two fidelity hazards lie outside the suite** [run]:
  - A C1 time literal with a 16-digit year has window bounds near 3.2e23 s, which overflows the int64 of every
    backend except PostgreSQL `numeric` and DuckDB `HUGEINT`. FalkorDB silently clamps such a value to 2^63 − 1.
  - Code-point id order holds everywhere except a PostgreSQL column under an ICU collation.
- **Recommended five:**
  - PostgreSQL 18.6, with SQLite 3.45.1 as the embedded control;
  - Oxigraph through pyoxigraph 0.5.11;
  - Neo4j Community 2026.09.0;
  - TypeDB CE 3.13.6 with typedb-driver 3.13.6;
  - HIF through khg-contracts `to_hif`/`from_hif`.
- **Proposed corrections to P2 §6.5** (§11):
  - The RDF and property-graph layouts that §6.5 itself proposes keep transaction time, so 114 scenarios apply to
    each, not 107.
  - The temporal-key exclusion constraint must use `int8range` over the instants, not `tstzrange`, because
    `timestamptz` stops at 4713 BC.

## 0. Method

**The container** [run]:
- Ubuntu 24.04.4 with Python 3.11.15; Python 3.12 and 3.13 are also present.
- OpenJDK 21.0.10 and Go 1.24.7.
- 4 cores, 15 GB of RAM, about 20 GB of free disk.
- The Docker client 29.3.1 is installed, but no daemon runs (`/var/run/docker.sock` is absent), so every server
  runs here as a native binary.
- PyPI, Maven Central, `dist.neo4j.org`, `repo.typedb.com`, `download.memgraph.com`, `apt.postgresql.org` and
  `community-extensions.duckdb.org` were reachable through the proxy.
- `github.com` release pages and the GitHub API returned 403 unless a repository is added to the session. So
  TypeDB, FalkorDB and PostgreSQL 18 came through other channels.

Installs, servers and data are under the session scratchpad (`…/scratchpad/p1/`), never in the repository.

**The probe harness** ([probes/common.py](probes/common.py)).
- Each backend is a `ReadOnlyProbe`, a `StoreBase` subclass.
- Its `load` stages the container through `MemoryStore`'s trusted load (normalisation, versions, transaction times,
  kept header), then writes the versioned records in the backend's own layout.
- `get`, `history`, `incident`, `find`, `find_by_key` and `iter_records` are native queries. `export` and
  `supersession_walk` come from `StoreBase`.
- A backend may add a `native_walk`: the supersession walk as one recursive query.

Three checks run on every backend:

1. **The hand queries** (`HAND`, 13 calls) are the core operations of the brief:
   - `get`;
   - `incident` (default, `as_of`, a node in two roles, a fact node);
   - `find` with `at_least` (a repeated role, an injective miss, a Julian time literal, a position);
   - `find_by_key` (a temporal key, and a key with a superseded fact);
   - `supersession_walk` forward and backward.

   Each is compared with `MemoryStore`'s answer. `export("khg-json")` is compared with the fixture by
   `compare_containers`, and the native walk with `StoreBase`'s walk.
2. **The read-only scenarios.** These are the 46 of the 114 whose `given` only loads `@fixture` or
   `@fixture[core]` and whose `when` steps only read. They run through khg-contracts' own runner
   (`conformance.runner.run_suite`).
3. **Transaction time.** `history_check` makes 85 comparisons on the history fixture (10 versions):
   - `get(as_at)` and `get(version)`;
   - `history`;
   - `incident(as_at)`;
   - snapshot and history exports.

   The read-only scenarios cannot test `as_at` themselves, because making versions needs writes.

The writes of each backend were not probed (§10, D2), with two exceptions: the HIF store and the SQLite table
store, which run all 114 scenarios. Timings at this scale (40 records) mean nothing. The seconds reported below
only show the per-store setup cost of each engine.

## 1. What C2 asks of a backend, and what the reference code gives

**The protocol** [read, DESIGN §6.1–§6.3]:
- 9 core methods: `info`, `put`, `apply`, `load`, `get`, `history`, `incident`, `find`, `iter_records`.
- 6 derived methods: `get_many`, `degree`, `find_by_key`, `supersession_walk`, `export`, `close`.
- 10 capability flags. A missing flag makes the scenarios that need it inapplicable, never passed.

**What `StoreBase` gives.** `StoreBase` (`src/khg_contracts/store/base.py`, 218 lines) derives only the six
derived methods [read]. Its `find_by_key` is `find` plus a key-digest filter in Python, and its
`supersession_walk` is breadth-first over `find` on `khg:supersedes`.

**Where the rest lives.** Everything that makes a write correct is in `MemoryStore`'s mixins:
- `store/_writes.py`, 407 lines: validation, the version rule, references, nesting, the key invariant, supersession
  and transaction time;
- `store/_events.py`, 432 lines: the four events.

These mixins touch the store only through `self._table`, the `VersionTable` interface [read, grep of
`_writes.py`, `_events.py`, `memory.py`]. Its 13 members are `current`, `entries`, `entry_at`, `latest` (read
and set), `latest_version`, `add`, `by_node`, `by_relation`, `by_key`, `by_ref`, `ids`, `__contains__` and
`__len__`.

[probes/table_store_sqlite.py](probes/table_store_sqlite.py) implements that interface on SQLite in about 150
lines. `MemoryStore` with this table, and one SQLite transaction per write, passes **114 of 114** scenarios in
1.2 s [run, out/table-store-sqlite.json]. §10 D2 builds on this.

**The natural layout shared by every probe** [derived from DESIGN §2.10 `incidence_rows`]. A hyperedge version is
one *fact row* plus one *incidence per binding*.
- The **fact row** holds `relation`, `status`, `status_ref`, `rank`, `visibility`, the relation kind
  (`fact`/`lifecycle`), `key_digest`, the four bound-table instants `s_lo`, `s_hi`, `e_lo`, `e_hi`, `n_bindings`,
  the store fields, and a `payload` with the canonical JSON of evidence, confidence, goal, rank reasons and
  extensions.
- The **incidence** holds `bid`, `role`, `position`, `direction`, `value_kind`, `ref` (the entity or fact id),
  `ident` (the value identity), `value_json` (the value as written) and `extensions`.
- `ident` comes from `record.identity_key` and the instants from `record.bounds`. Query parameters are computed with
  the same functions, so equality in the backend is C1's value identity: Julian 1700 equals its Gregorian window,
  and precision takes part.
- Instants are integer seconds on the proleptic Gregorian line. ±∞ become the sentinels ±2^62.

**`find`'s injective multiset match** ("two `agent` patterns need two `agent` bindings", §6.2) is expressible
natively everywhere except TypeDB. Each engine uses its own form: k joins on the incidence table with pairwise
`bid <> bid` (SQL), `FILTER(?b_i != ?b_j)` (SPARQL), or bid inequality within one `MATCH` (Cypher). `exact` adds
`n_bindings = k`.

## 2. Backend 1: the incidence table

### 2.1 Candidates, as run here

| Engine | Version, licence | Kind, how it runs here | Disk, memory |
|---|---|---|---|
| SQLite | 3.45.1, the library the container's Python 3.11 links; public domain | embedded, stdlib `sqlite3` | none extra |
| DuckDB | 1.5.5 (PyPI, 2026-07-22), MIT | embedded, `pip install duckdb==1.5.5` | 58 MB extension module |
| PostgreSQL 16 | 16.13, the Ubuntu `postgresql-16` package that is already installed; PostgreSQL Licence | server, TCP port 5416 | 44 MB; 36 MB RSS idle |
| PostgreSQL 18 | 18.6 from Maven Central `io.zonky.test.postgres:embedded-postgres-binaries-linux-amd64:18.6.0` (jar built 2026-08-26); PostgreSQL Licence | server, TCP port 5418 | 15 MB download, 60 MB unpacked (includes `btree_gist`); 32 MB RSS idle |

**Commands that worked** [run]:

```bash
# PostgreSQL 18.6 (a self-contained build, no apt install)
curl -sS -o pg.jar https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-linux-amd64/18.6.0/embedded-postgres-binaries-linux-amd64-18.6.0.jar
unzip -q pg.jar && mkdir dist && tar xJf postgres-linux-x86_64.txz -C dist
# initdb refuses to run as root; a user namespace maps root to uid 1000 and keeps access to the 0700 scratchpad
unshare --user --map-user=1000 --map-group=1000 dist/bin/initdb -D $P1/pg18/data --locale=C --encoding=UTF8 -U postgres --auth=trust
unshare --user --map-user=1000 --map-group=1000 dist/bin/pg_ctl -D $P1/pg18/data -l $P1/pg18/server.log \
  -o "-p 5418 -c unix_socket_directories='' -c listen_addresses=127.0.0.1 -c shared_buffers=256MB" start
# PostgreSQL 16.13: the same two unshare commands with /usr/lib/postgresql/16/bin/{initdb,pg_ctl}, port 5416
pip install "psycopg[binary]==3.3.6"          # client (LGPL-3.0)
```

Three obstacles came up on the way:
- `runuser -u postgres` did not work, because the harness keeps `/tmp/claude-0` at mode 0700.
- A Unix socket under the scratchpad path exceeds the 107-byte limit, so the servers listen on TCP only.
- The first Maven Central request returned HTTP 429, and a retry succeeded.

Other routes, not needed here:
- `apt.postgresql.org` (`noble-pgdg`) serves `postgresql-18` 18.6-1.pgdg24.04+2 and is reachable [run].
- The pip "server" packages do not fit. `postgresql-wheel` 14.1.2 requires Python below 3.10 (2021), and
  `pixeltable-pgserver` 0.6.0 (2026-07-14) was not tried [unverified].

### 2.2 Schema

This is [sql_incidence.py](probes/sql_incidence.py), with the PostgreSQL-specific choices added as comments:

```sql
CREATE TABLE document (singleton int PRIMARY KEY, header text, documents text);        -- kept header (§6.2)
CREATE TABLE entity_version (id text, version int, tx_from bigint NOT NULL, tx_to bigint,
  recorded_at text, recorded_by text, record text, PRIMARY KEY (id, version));
CREATE TABLE fact_version (id text, version int,
  tx_from bigint NOT NULL, tx_to bigint,              -- transaction time [tx_from, tx_to) in µs; tx_to NULL = current
  recorded_at text, recorded_by text,
  relation text, rel_kind text, status text, status_ref text, rank text, visibility text,
  key_digest text,                                    -- C1 key digest, NULL without a key or with a special value
  s_lo bigint, s_hi bigint, e_lo bigint, e_hi bigint, -- bound table (§2.6); numeric for 16-digit years (§7)
  n_bindings int, payload text,                       -- evidence etc. as canonical JSON (jsonb in PostgreSQL)
  PRIMARY KEY (id, version));
CREATE TABLE binding (fact_id text, version int, bid text, role text, position int, direction text,
  value_kind text, ref text, ident text, value_json text, extensions text,
  PRIMARY KEY (fact_id, version, bid));               -- bid, not (fact, entity, role): repeated fillers
CREATE INDEX binding_ref   ON binding (ref, role);    -- incident
CREATE INDEX binding_ident ON binding (role, ident);  -- find by value
CREATE INDEX fact_key      ON fact_version (relation, key_digest);
CREATE INDEX fact_rel      ON fact_version (relation, id);
-- PostgreSQL: a database created with LOCALE 'C' (or COLLATE "C" on every id column) gives code-point order (§7)
-- PostgreSQL 18, optional guard for the plain key invariant (rank exceptions stay in code):
--   CREATE EXTENSION btree_gist;
--   CREATE TABLE key_period (relation text, key_digest text, valid int8range,
--     PRIMARY KEY (relation, key_digest, valid WITHOUT OVERLAPS));
```

Versions are immutable rows. A new version sets `tx_to` on its predecessor, which is a bookkeeping column only,
as in SQL:2011 system versioning. The fixture is 22 entity rows, 18 fact rows and 59 binding rows.

### 2.3 The operations

| Operation | SQL | Fixture result [run] |
|---|---|---|
| `get(id, as_at?, version?)` | fact row `WHERE id = ? AND tx_to IS NULL` (or `tx_from <= t AND (tx_to IS NULL OR tx_to > t)`, or `version = ?`), then its bindings; entities from `entity_version` | equal to reference |
| `incident(node, role?, relation?, where)` | `SELECT fv.id FROM fact_version fv WHERE EXISTS (SELECT 1 FROM binding b WHERE b.fact_id = fv.id AND b.version = fv.version AND b.ref = ? [AND b.role = ?]) AND <current> AND fv.status IN (…) AND fv.rank IN (…) AND fv.visibility IN (…) AND fv.rel_kind IN (…) [AND fv.s_hi <= t AND t < fv.e_lo] [AND fv.id > after] ORDER BY fv.id [LIMIT n]` | equal |
| `find(…, at_least)` | `SELECT DISTINCT fv.id FROM fact_version fv JOIN binding b1 ON b1.fact_id = fv.id AND b1.version = fv.version AND b1.role = ? AND b1.ident = ? JOIN binding b2 ON … AND b2.bid <> b1.bid WHERE fv.relation = ? AND <current> AND <filters> ORDER BY fv.id` (`any_unbound`: `value_kind = 'unbound'`; `position`: `b.position = ?`) | equal, including the injective miss |
| `find(…, exact)` | the same plus `fv.n_bindings = k` | equal |
| `find_by_key` | `StoreBase`'s argument checks, then `WHERE relation = ? AND key_digest = ? AND <current> AND <filters>` | equal |
| `supersession_walk` | `WITH RECURSIVE walk(depth, via, frm, dst)`: join `binding(role = 'khg:superseded', ref = start)` to an asserted current `khg:supersedes` version, then to its `khg:superseding` binding, and recurse on `dst` (depth ≤ 64) | the same steps as `StoreBase` |
| `export` | `iter_records` (every id, current or at `as_at`, or every version) through `StoreBase.export` | 0 differences |

One caution about the recursive walk. `UNION` removes duplicate rows, but not a node that is reached at two depths.
`StoreBase` expands each fact once (breadth first, a `seen` set). So on a diamond of supersessions the CTE returns
extra steps [derived]. The adapter should keep `StoreBase`'s walk (one indexed query per level) or de-duplicate on
the minimum depth.

**Results** [run, out/sql-{sqlite,duckdb,pg16,pg18}.json]:
- Every engine passes **46 of 46** read-only scenarios and 85 of 85 transaction-time checks.
- The export has 0 differences, and all 13 hand calls equal the reference.
- **The temporal-key constraint.** Both constraints refuse a copy of `f:king-14` that starts in 1640 ("conflicting
  key value violates exclusion constraint"):
  - PostgreSQL 18.6 `PRIMARY KEY (relation, key_digest, valid WITHOUT OVERLAPS)`, which needs `btree_gist` for the
    text columns;
  - the older `EXCLUDE USING gist (relation WITH =, key_digest WITH =, valid WITH &&)`, in both 16 and 18.
- PostgreSQL 16 rejects `WITHOUT OVERLAPS` as a syntax error.

### 2.4 Recommendation

**PostgreSQL 18.6** is the measured incidence backend:
- the KB's system-of-record choice ([format-recommendations](../../../kb/04-storage-and-formats/format-recommendations.md));
- a server, like Neo4j and TypeDB;
- temporal keys can be declared in the schema.

**SQLite 3.45.1** is the embedded control and the development default:
- it needs no install;
- it is the fastest path to the full write path (§1).

DuckDB passed everything, but it adds no layout the other two lack. Keep it for analytics and Parquet export,
outside the five.

## 3. Backend 2: reified RDF, relation-instance pattern

### 3.1 Candidates, as run here

| Engine | Version, licence | Kind | Size |
|---|---|---|---|
| Oxigraph (`pyoxigraph`) | 0.5.11 (PyPI, 2026-09-02), MIT OR Apache-2.0 | embedded Rust store on RocksDB: `Store(path)` on disk; without a path, "a temporary one is created" [read, `Store` docstring] | 21 MB wheel |
| rdflib | 7.6.0 (PyPI, 2026-02-13), BSD-3-Clause | pure Python in-memory `Dataset` | 5 MB |

Install: `pip install pyoxigraph==0.5.11 rdflib==7.6.0` [run].

**Transactions** [read, pyoxigraph 0.5.11 docstrings].
- In Oxigraph, `Store.extend` and `Store.update` run "in a transactional manner: either the full operation
  succeeds, or nothing is written".
- `bulk_extend`, which is the right call for a trusted load, is not transactional.
- rdflib's in-memory store has no transactions, so the adapter's all-or-nothing rests on checking everything before
  it writes [derived].

**Standards status.** RDF 1.2 Concepts and Semantics are Candidate Recommendation Snapshots of 7 April 2026. The
syntaxes and SPARQL 1.2 are Working Drafts, the latest SPARQL 1.2 Query draft being dated 21 September 2026 [read,
[kb rdf-star note](../../../kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md) §1 and P2
research 04 finding 12].

The relation-instance pattern needs **no triple term**. What the probe uses is RDF 1.1 plus named graphs, so it is
valid under the `1.2-basic` label and readable by RDF 1.1 tools [derived; P2 research 04 risk 8].

### 3.2 Layout

This is [rdf_relation_instance.py](probes/rdf_relation_instance.py).

**One named graph per version**, `<urn:khg:<id>/v<n>>`. The name is unambiguous because `/` never occurs in an
encoded id. A hyperedge version's graph holds exactly P2's projection `project.rdf_relation_instance` of that
version: a fact IRI, one node per binding, and `khg:relation`, `khg:status`, `khg:bid`, `khg:role`, `khg:position`,
`khg:direction`, and `khg:value`/`khg:valueKind` or `khg:valueJSON`. It adds the filter triples:

```turtle
<f> khg:id "f:king-14" ; khg:rank "normal" ; khg:visibility "visible" ; khg:relKind "fact" ;
    khg:keyDigest "sha256:…" ; khg:sLo 200559196800 ; khg:sHi … ; khg:eLo … ; khg:eHi … ;
    khg:nBindings 5 ; khg:payload "{…canonical JSON…}" [; khg:statusRef <urn:khg:m%3Asup-1>] .
<f#b3> khg:ident "{\"literal\":{\"datatype\":\"time\",…}}" ; khg:valueKind "literal" .
```

**The default graph** holds the version metadata (`<g> khg:versionOf <f> ; khg:version ; khg:txFrom ; khg:txTo ;
khg:recordedAt ; khg:recordedBy`) and the kept header.

The fixture is 870 quads.

**Order.** `ORDER BY` runs on the plain `khg:id` literal, not the IRI. Percent-encoding changes the order: `/`
(0x2F) becomes `%2F`, which sorts before `.` (0x2E) [derived].

### 3.3 The operations

| Operation | SPARQL | Result [run] |
|---|---|---|
| `get` | find the current graph (`?g khg:versionOf <f> FILTER NOT EXISTS { ?g khg:txTo ?x }`, or `txFrom <= t` and `txTo > t`, or `khg:version n`), then `SELECT ?s ?p ?o { GRAPH <g> { ?s ?p ?o } }` and reassemble | equal |
| `incident` | `SELECT DISTINCT ?id { <current ?g> GRAPH ?g { ?f khg:binding ?b . ?b khg:value <node> [; khg:role "r"] . ?f khg:status ?st ; khg:rank ?rk ; khg:visibility ?vis ; khg:relKind ?k ; khg:id ?id . FILTER(?st IN (…)) … [?f khg:sHi ?lo ; khg:eLo ?hi FILTER(?lo <= t && t < ?hi)] } } ORDER BY ?id` | equal |
| `find` | per pattern `?f khg:binding ?bi . ?bi khg:role "r" ; khg:ident "…"` (or `khg:position "3"`, `khg:valueKind "unbound"`), with `FILTER(?bi != ?bj)` for every earlier pattern; `exact` adds `?f khg:nBindings k` | equal |
| `find_by_key` | `?f khg:relation "r" ; khg:keyDigest "…"` plus the filters | equal |
| `supersession_walk` | one query per level: `?s khg:relation "khg:supersedes" ; khg:status "asserted" ; khg:binding ?b1, ?b2 . ?b1 khg:role "khg:superseded" ; khg:value <f> . ?b2 khg:role "khg:superseding" ; khg:value ?to` | same steps |
| `export` | `iter_records` through `StoreBase.export` | 0 differences |

**Why the walk takes one query per level.** A SPARQL property path cannot test the role of the binding node it
passes through, or the status of the lifecycle record. So the walk cannot be written as one query unless the store
also keeps a shortcut predicate (`<old> khg:supersededBy <new>`). That predicate would then have to be maintained on
retraction [derived].

**Results** [run, out/rdf-{oxigraph,rdflib}.json]:
- Both engines pass **46 of 46** read-only scenarios and 85 of 85 transaction-time checks, with 0 export
  differences.
- The 46 scenarios took 1.3 s on Oxigraph and 12–16 s on rdflib, most of it per-store setup.

### 3.4 Recommendation

**Oxigraph (pyoxigraph 0.5.11)**, on disk through `Store(path)`, with one named graph per version. rdflib is only a
cross-check of the SPARQL; it is about ten times slower here and has no transactions.

## 4. Backend 3: the bipartite property graph

### 4.1 Candidates, as run here

| Engine | Version, licence | Kind, how it runs here | Disk, memory |
|---|---|---|---|
| **Neo4j Community** | 2026.09.0 (Maven Central `org.neo4j:neo4j`, latest, updated 2026-09-22); **GPL v3** (`LICENSE.txt` in the tarball) | Java 21 server, `bin/neo4j console`, Bolt on 127.0.0.1:7687 | 274 MB download, 803 MB unpacked; **1,066 MB RSS** (1 GB maximum heap, 256 MB page cache) plus a 199 MB launcher JVM |
| Memgraph | 3.13.1 (binary dated 2026-09-11); Business Source License 1.1 with an additional use grant, change date 2030, change licence Apache 2.0 (`BSL.txt` in the deb) | C++ server, in-memory (`--storage-mode=IN_MEMORY_TRANSACTIONAL` in the shipped config), Bolt on 7688 | 43.6 MB deb, 140 MB extracted; 77 MB RSS |
| FalkorDB | graph module version 41803 (4.18.3) bundled in `falkordblite` 0.10.0 (PyPI, 2026-05-02); **SSPL v1** ([LICENSE.txt](https://raw.githubusercontent.com/FalkorDB/FalkorDB/master/LICENSE.txt)) | Redis 8.6.2 module, `redis-server --loadmodule falkordb.so` on port 6380 | 67 MB; 42 MB RSS |
| Kùzu | 0.11.3 (PyPI, 2025-10-10), MIT; **archived** (P2 research 04 §9.1) | embedded, `pip install kuzu==0.11.3` | 21 MB |
| LadybugDB | 0.20.4 (PyPI, 2026-09-10), MIT; "The database was formerly known as Kuzu" ([PyPI](https://pypi.org/project/ladybug/)) | embedded, `pip install ladybug==0.20.4` | 23 MB |
| DuckDB + DuckPGQ | DuckDB 1.5.4 with the community extension `duckpgq` f386a6c; the extension's licence [unverified] | embedded SQL/PGQ over the incidence tables | 32 MB extension |

**Commands that worked** [run]:

```bash
# Neo4j Community 2026.09.0 (the version comes from the Maven Central metadata of org.neo4j:neo4j)
curl -sS -o neo4j-community-2026.09.0-unix.tar.gz https://dist.neo4j.org/neo4j-community-2026.09.0-unix.tar.gz
tar xzf neo4j-community-2026.09.0-unix.tar.gz && cd neo4j-community-2026.09.0
cat >> conf/neo4j.conf <<'EOF'
dbms.security.auth_enabled=false
server.default_listen_address=127.0.0.1
server.bolt.listen_address=127.0.0.1:7687
server.http.listen_address=127.0.0.1:7474
server.memory.heap.initial_size=512m
server.memory.heap.max_size=1g
server.memory.pagecache.size=256m
dbms.usage_report.enabled=false
EOF
./bin/neo4j console &            # a repeated key (server.https.enabled) makes the configuration validation fail
# Memgraph 3.13.1: extract the deb (no install); libpython3.so is missing, so point it at the 3.12 shared library
curl -sS -o memgraph_3.13.1-1_amd64.deb https://download.memgraph.com/memgraph/v3.13.1/x86_64-deb/memgraph_3.13.1-1_amd64.deb
dpkg-deb -x memgraph_3.13.1-1_amd64.deb root && mkdir libs && ln -s /usr/lib/x86_64-linux-gnu/libpython3.12.so.1.0 libs/libpython3.so
LD_LIBRARY_PATH=$PWD/libs root/usr/lib/memgraph/memgraph --data-directory=$P1/memgraph/data --log-file=$P1/memgraph/logs/memgraph.log \
  --bolt-address=127.0.0.1 --bolt-port=7688 --telemetry-enabled=false --storage-properties-on-edges=true &
# FalkorDB: falkordblite requires Python >= 3.12; its bundled redis-server and falkordb.so then serve any client
python3.12 -m venv venv312 && venv312/bin/pip install falkordblite==0.10.0
B=venv312/lib/python3.12/site-packages/redislite/bin
$B/redis-server --port 6380 --bind 127.0.0.1 --save '' --appendonly no --loadmodule $B/falkordb.so &
# clients, on Python 3.11
pip install neo4j==6.3.1 falkordb==1.7.1 pymgclient==1.6.0 kuzu==0.11.3 ladybug==0.20.4
# DuckPGQ has no build for DuckDB 1.5.5 (HTTP 404); 1.5.4 has one
python3.11 -m venv venv-duck154 && venv-duck154/bin/pip install duckdb==1.5.4   # then INSTALL duckpgq FROM community
```

Memgraph is reached with the `neo4j` driver (auth `("", "")`). The `neo4j` Python driver is Apache-2.0.

### 4.2 Layout

This is [pg_cypher.py](probes/pg_cypher.py) and [pg_kuzu.py](probes/pg_kuzu.py). Versions are nodes, so
transaction time is kept. Bindings point at identity nodes, so nesting survives a new version of the nested fact.

```text
(:Node {id, kind})                                            one per entity id and per fact id
(:Version {id, version, tx_from, tx_to, kind, relation, rel_kind, status, status_ref, rank, visibility,
           key_digest, s_lo, s_hi, e_lo, e_hi, n_bindings, payload | record})-[:VERSION_OF]->(:Node)
(:Version)-[:BINDS {bid, role, position, direction, value_kind, ref, ident, value_json, extensions}]->(t)
   t = the (:Node) of an entity or fact value | a shared (:Literal {ident}) | a per-binding (:Special {key})
(:Doc {header, documents})
```

- **Size.** The fixture is 102 nodes and 99 edges.
- **Isolation.** Neo4j Community and Memgraph hold one user database. The conformance runner opens a second store
  while the first is open (the reload and determinism checks), so every node also carries a per-store namespace
  label. FalkorDB takes one graph key per store, and Kùzu and LadybugDB one in-memory `Database` per store.
- **Kùzu and LadybugDB need typed DDL.** `CREATE NODE TABLE`, and a `BINDS` relationship table with three
  `FROM … TO …` pairs.
- **Roles are an edge property.** Neo4j 2026.09 builds a relationship-property range index on `BINDS(role,
  ident)`, and it came up `ONLINE` [run, `SHOW INDEXES`].

### 4.3 The operations

| Operation | Cypher | Result [run] |
|---|---|---|
| `get` | `MATCH (v:Version {id: $id}) WHERE v.tx_to IS NULL RETURN properties(v)`, then `MATCH (v)-[e:BINDS]->() RETURN properties(e)` | equal |
| `incident` | `MATCH (v:Version)-[e:BINDS]->(:Node {id: $node}) WHERE <current> AND v.status IN $st AND v.rank IN $rk AND v.visibility IN $vis AND v.rel_kind IN $kinds [AND e.role = $role] [AND v.s_hi <= $asof AND $asof < v.e_lo] [AND v.id > $after] RETURN DISTINCT v.id AS id ORDER BY id [LIMIT n]` | equal |
| `find` | `MATCH (v:Version {relation: $rel}), (v)-[b1:BINDS]->(), (v)-[b2:BINDS]->() WHERE b1.role = $r1 AND b1.ident = $i1 AND b2.role = $r2 AND b2.ident = $i2 AND b2.bid <> b1.bid AND …` | equal |
| `find_by_key` | `MATCH (v:Version {relation: $rel, key_digest: $kd}) WHERE <current> AND <filters>` | equal |
| `supersession_walk`, Neo4j | one query with a quantified path pattern: `MATCH (start:Node {id: $id}) ((a:Node)<-[:BINDS {role: $frm}]-(s:Version WHERE s.relation = 'khg:supersedes' AND s.status = 'asserted' AND s.tx_to IS NULL)-[:BINDS {role: $to}]->(b:Node)){1,64} RETURN [x IN s | x.id], [x IN a | x.id], [x IN b | x.id]` | same steps |
| `supersession_walk`, others | one two-hop query per level on Memgraph, FalkorDB, Kùzu and LadybugDB; whether they accept quantified path patterns was not tested [unverified] | same steps |
| `export` | through `StoreBase.export` | 0 differences |

**Results** [run, out/pg-{neo4j,memgraph,falkordb,kuzu,ladybug}.json]:
- All five engines pass **46 of 46** read-only scenarios and 85 of 85 transaction-time checks, with 0 export
  differences.
- The 46 scenarios took 25–32 s on Neo4j, where every store is created and wiped over Bolt, 2–3 s on Memgraph and
  FalkorDB, and 13–16 s on Kùzu and LadybugDB, where every store builds its own database and DDL.

**DuckPGQ** [run, out/pg-duckpgq.json]:
- `CREATE PROPERTY GRAPH` over the incidence tables works once the labels avoid the reserved word `Node`.
- `GRAPH_TABLE` answers `incident`, the two-pattern `find` and one walk level correctly.
- A variable-length path (`ANY SHORTEST … -[e:binds]-{1,8}`) is refused: "Non-existent/non-unique vertices
  detected". Path-finding needs edges within one vertex table, and the bipartite layout's edges run from version to
  node.

**Two hazards** [run]:
- After `import kuzu`, `ladybug.Database()` fails with "Could not find lbug C API shared library". The two cannot
  share one process.
- FalkorDB stores 315569520000148699584000 as 9223372036854775807 without an error (§7).

### 4.4 Recommendation

**Neo4j Community 2026.09.0**:
- It is the de-facto target of knowledge-hypergraph projects ([kb emulation note](../../../kb/04-storage-and-formats/property-graph-emulation-patterns.md)).
- It is the only property-graph candidate whose walk ran here as one declarative query.
- It indexes the `role` edge property.

Its GPL v3 is no obstacle, because P1 runs it and does not distribute it. It needs about 1.3 GB of RAM at these
settings.

Memgraph (BSL) and FalkorDB (SSPL, with silent integer clamping) are not recommended. Kùzu is archived. **LadybugDB
0.20.4** is the embedded alternative if P1 wants a second, in-process property-graph row.

## 5. Backend 4: TypeDB 3.x

### 5.1 Server and driver, as run here

- **The server is TypeDB CE 3.13.6**, under the MPL 2.0 (the `LICENSE` in the archive).
  - The `latest` download URL of the [install page](https://typedb.com/docs/home/install/ce/) redirected to 3.13.6
    on 2026-09-25 [run]. It is a 33.6 MB archive (sha256 `3411c72a…8913`), 101 MB unpacked.
  - It needs no JVM. RSS is 46 MB idle and 115 MB after the probes.
  - The server's own release date is [unverified]; its archive dates every file 2000-01-01.
- **The driver is `typedb-driver` 3.13.6** (PyPI, 2026-09-21, Apache-2.0), a 24 MB native wheel.
- Docker is not needed.

```bash
curl -sSL -o typedb-all-linux-x86_64.tar.gz \
  https://repo.typedb.com/public/public-release/raw/names/typedb-all-linux-x86_64/versions/latest/download
tar xzf typedb-all-linux-x86_64.tar.gz
# config.yml copied from server/config.yml, then: listen 127.0.0.1:1729 and 127.0.0.1:8000,
# data and log directories under $P1/typedb, diagnostics reporting (metrics, errors) false
typedb-all-linux-x86_64-3.13.6/typedb server --config $P1/typedb/config.yml &
pip install typedb-driver==3.13.6
# TypeDB.driver("127.0.0.1:1729", Credentials("admin", "password"), DriverOptions(DriverTlsConfig.disabled()))
```

### 5.2 What TypeQL 3.13.6 accepts

This is [typedb_features.py](probes/typedb_features.py), [typedb_lists.py](probes/typedb_lists.py) and
out/typedb-features.txt [run].

| Construct | Result |
|---|---|
| a role scoped per relation (`holder` in two relations) | accepted |
| a relation plays a role (nesting) | accepted |
| a relation owns an attribute (a literal as an owned attribute) | accepted |
| an attribute plays a role | **refused**: "the type 'code' of kind 'attribute', which cannot have: 'plays …'" (DEX11) |
| `relates stop[]` (an ordered role list) | **defined**, but inserting a list is a parse error, and reading `links (stop[]: $l)` gives "The language feature is not yet implemented: Lists" (REP254) |
| `owns name[]` | defined; reading gives "List types are not yet implemented" (REP256) |
| a `struct` value type | defined; inserting a value is a parse error. The docs say "Structs are a planned feature and not yet available in TypeDB" ([structs](https://typedb.com/docs/typeql-reference/expressions/structs/)) |
| a relation inserted without role players (owning `@key` fid) | the insert returns a row, but **the relation is gone** after the commit |
| one player inserted twice in one role (`member: $a, member: $a`) | stored as one: `links (member: $x, member: $y)` gives 0 rows, and the member count is 1 |
| an untyped player match (`$p has khg-id "ex:Paris"`) in an insert | refused by type inference (INF4, "Left type 'Agent' … is not compatible with right type 'born_in:birthplace'"), so the loader matches every player with its exact type |

### 5.3 The mapping

[typedb_probe.py](probes/typedb_probe.py) generates the TypeQL schema from `fixture.relation-schema.json`: 93
attribute types, 15 entity types, 15 relation types and 26 `plays`.

```typeql
entity khg-entity @abstract, owns khg-id @key, owns khg-record;
relation khg-fact @abstract, owns khg-id @key, owns khg-status, owns khg-rank, owns khg-visibility,
  owns khg-rel-kind, owns khg-status-ref, owns khg-key-digest, owns khg-s-lo, owns khg-s-hi, owns khg-e-lo,
  owns khg-e-hi, owns khg-n-bindings, owns khg-payload, owns khg-bindings, owns khg-version, …;
entity Person, sub Agent;                              # the schema's DAG (first parent)
relation position_held, sub khg-fact, relates holder @card(0..), relates position @card(0..),
  relates replaces @card(0..), owns lit-start_time @card(0..), owns lit-end_time @card(0..),
  owns special-holder @card(0..), owns unbound-holder @card(0..), …;
Person plays position_held:holder;  born_in plays claims:claim;  khg-fact plays khg-supersedes:khg-superseded;
```

The rules:
- **Entity and fact fillers** play scoped roles.
- **Literal fillers** become an owned `lit-<role>` string holding the value identity.
- **Special and unbound values** become owned marker attributes.
- **Everything the native structure cannot hold** goes into `khg-bindings`, a canonical-JSON copy of the bindings:
  bids, positions, directions, binding extensions, and literals as written (the Julian calendar, the time string).

An insert looks like this (`f:king-14`, abridged):

```typeql
match $p1 isa Person, has khg-id "ex:LouisXIV"; $p2 isa Position, has khg-id "ex:KingOfFrance";
      $p3 isa Person, has khg-id "ex:LouisXIII";
insert $f isa position_held (holder: $p1, position: $p2, replaces: $p3),
  has lit-start_time "{\"literal\":{\"datatype\":\"time\",\"precision\":11,\"window\":[…]}}", …,
  has khg-id "f:king-14", has khg-status "asserted", has khg-s-hi 200559283200, …, has khg-bindings "[…]";
```

The whole load is one write transaction, with nested and lifecycle facts after the facts they bind. The schema and
the 40 records load in 0.35 s.

### 5.4 The operations

| Operation | TypeQL | Result [run] |
|---|---|---|
| `get` | `match $f isa khg-fact, has khg-id "…", has khg-status $st, …; $f isa! $t;` and reassembly from `khg-bindings` | equal |
| `incident` | `match $n has khg-id "ex:KingOfFrance"; $f isa khg-fact, links ($n); $f has khg-id $id, has khg-status $st, …; { $st == "asserted"; }; { $rk == "normal"; } or { $rk == "preferred"; }; …; $f has khg-s-hi $vlo, has khg-e-lo $vhi; $vlo <= 202346467200; $vhi > 202346467200; select $id; sort $id;`; a role filter is a disjunction `{ $f isa R, links (role: $n); } or …` over the relations that use the role | equal |
| `find` | `$f isa R, links (role: $p1); $p1 has khg-id "…"` or `$f has lit-role "<identity>"`, with the multiset check done client-side on `khg-bindings`, because a repeated player or an equal literal collapses | equal |
| `find_by_key` | `$f isa R, has khg-key-digest "…"` plus the filters | equal |
| `supersession_walk` | one query with a **recursive function**: `with fun reach($x: khg-fact) -> { khg-supersedes, khg-fact, khg-fact }: match { $s isa khg-supersedes, links (khg-superseded: $a, khg-superseding: $y), has khg-status "asserted"; $a is $x; } or { $s0 isa khg-supersedes, links (khg-superseded: $x, khg-superseding: $m), has khg-status "asserted"; let $s, $a, $y in reach($m); }; return { $s, $a, $y };` | same steps (the depth is recovered client-side) |
| `export` | from `khg-bindings` and the header attributes | 0 differences |
| `get(as_at)`, history | none: one relation instance per fact | `CapabilityMissing` |

**Results** [run, out/typedb.json]:
- **19 of 19** applicable read-only scenarios pass: the `c` variants on `@fixture[core]`. 27 are inapplicable.
- All 13 hand calls equal the reference, and the export has 0 differences, *through the `khg-bindings` copy*.
- **Rebuilt from the native structure alone** (role players and owned attributes, without `khg-bindings`):
  - 17 of the 18 hyperedges keep their role–value multiset.
  - `f:route-1` loses its second `stop: ex:YYZ` (the repeated player collapses) and its positions.
  - Per binding: 59 of 59 bids have to be regenerated, and 3 positions, 2 binding extensions, 20 literals as
    written (only the identity is kept) and 1 `unbound.expect` are lost.

### 5.5 The gaps, and the capability flags TypeDB lacks

| Gap | Evidence | Flag |
|---|---|---|
| Role-player lists are not implemented | REP254 [run]; P2 research 04 ("not yet available") | **`ordered_roles`** lacking |
| No null or placeholder player: `somevalue`, `novalue` and `unbound` need marker attributes, and a relation left without players is deleted at commit | [run] | **`special_values`** and **`goals`** lacking natively; emulable (below) |
| No reads of an earlier commit. "TypeDB does not currently support temporal range queries … or point-in-time queries" (open issue [typedb/typedb#7554](https://github.com/typedb/typedb/issues/7554), opened 2025-08-20). Versions as instances would break nesting, because players are instances | [read]; [derived] | **`transaction_time`**, **`history_export`** lacking |
| Literals cannot play roles, and owned attributes are sets | DEX11 [run]; the data-model page (P2 research 04 M2) | `literal_values` held as identity attributes; the written form and repeats only in `khg-bindings` |
| `@key` covers one attribute only; composite and temporal keys cannot be declared | P2 research 04 M3 table [read] | `key_constraint` from the shared write path, as for every backend |
| One type per instance, and no type change | [derived from the data model: `isa` gives an instance one type; the probe's loader therefore refuses a multi-typed entity] | a C1 entity with several `types`, or one whose types grow in a new version, has no native form |
| Write transactions are atomic | the whole load commits as one [run] | `atomic_writes` held |

**P2's figure is confirmed.** With `ordered_roles`, `special_values`, `goals`, `transaction_time` and
`history_export` absent, **70 of the 114 scenarios apply**. Computed from the scenarios' `requires`
[run, §8], that is find 5 of 13, incident 13 of 24 and export 3 of 11, as §6.5 says.

Two variants, for §10 D8:
- **78 apply** if P1 emulates `special_values` and `goals`. That means marker attributes plus an anchor role, so
  that a relation whose slots are all unbound keeps a player.
- **107** would also need positions, which could live only in the JSON copy and never in the query.

## 6. Backend 5: HIF files

This is [hif_store.py](probes/hif_store.py).

**The design.** `HifStore` is `MemoryStore` with a durable state of one role-aware HIF file (`khg-hif/1.0.0`).
- After every write (`_commit`, `load`), it writes `export("hif")` and swaps it in with `os.replace`.
- It then **rebuilds its index from the file with `hif.from_hif`**, so every read is served from what HIF kept.
- It declares every flag except `transaction_time` and `history_export`, because HIF holds one version per id.
  `export` also refuses `hif` with `content="history"`.
- It uses khg-contracts 1.0.0.dev0 from this repository and needs no install.

**Results** [run, out/hif.json]:
- The full suite gives **107 passed, 7 inapplicable, 0 failed**.
- The 7 inapplicable are S-EXP-004, S-EXP-005, S-EXP-008, S-EXP-010, S-TIME-002, S-TIME-004 and S-VER-001.
- The fixture file is 24,022 bytes: 46 nodes, 18 edges and 59 incidences. It is valid under `validate_hif`.
- Closing and reopening from the file alone exports the fixture with 0 differences. The store fields (`version`,
  `recorded_at`, `recorded_by`) survive in the HIF attributes.
- An `as_at` read after reopening raises `CapabilityMissing`.

**The write cost.** Every write rewrites the whole file, which is O(size). That is the KB's own anti-pattern for a
system of record ([format-recommendations §5](../../../kb/04-storage-and-formats/format-recommendations.md)). For
the bake-off it is the interchange baseline, and its load, export and read times are the interesting ones.

## 7. Two value-fidelity checks the suite does not make

This is [ordering_probe.py](probes/ordering_probe.py) [run, out/ordering.json].

**Id order.** C2 lists are "in code-point id order". Every engine sorted `f:a`, `f:Z`, `f:é`, `f:ł`, `f:東京`,
`f:ｚ`, `f:\uFFFD` and `f:\U00020BB7` in code-point order, including Neo4j, which here does not sort by UTF-16
code units. The one exception is a PostgreSQL column under `COLLATE "en-x-icu"`, which gave `f:a, f:é, f:ł, f:ｚ,
f:Z, f:𠮷, f:東京, f:\uFFFD`. The PostgreSQL adapter must therefore create its database with `LOCALE 'C'` or put
`COLLATE "C"` on its id columns.

**Instant range.** A valid C1 time literal may have a 16-digit year (C004).
- `+9999999999999999` at precision 0 has the window [3.155694884431967e23, 3.155695200001487e23) s [run,
  `record.window_seconds`]. Wikidata's oldest dates (−13.8 × 10⁹ years) stay near −4.4 × 10¹⁷, inside int64.
- Storing 315569520000148699584000 as an integer gave these results:

| Engine | 2^62 and 2^63 − 1 | 3.2e23 |
|---|---|---|
| SQLite | stored | OverflowError |
| DuckDB | stored | `BIGINT` refused; **`HUGEINT` stored** |
| PostgreSQL | stored | `bigint` out of range; **`numeric` stored** |
| Oxigraph | stored | stored as `xsd:integer`; equality finds it, but **a comparison does not** |
| rdflib | stored | a Python int (unbounded) |
| Neo4j, Memgraph | stored | driver OverflowError |
| FalkorDB | stored | **silently stored as 9223372036854775807** |
| Kùzu, LadybugDB | stored | cast error |
| TypeDB | stored | "integer literal … is out of range" (LIT11) |

So the ±2^62 sentinels and int64 seconds cover every Wikidata date but not the whole C1 grammar. An adapter must
check its instants and report what it cannot hold as a fidelity loss (§10 D4).

## 8. Capability flags per backend, and the scenarios that apply

Each cell names the layout element that carries the flag and its evidence. The count of applicable scenarios is
computed from the `requires` of the 114 scenario files [run].

| Flag | Incidence table (PostgreSQL 18.6; SQLite) | RDF (Oxigraph, named graph per version) | Property graph (Neo4j, version nodes) | TypeDB 3.13.6 (natural mapping) | HIF file |
|---|---|---|---|---|---|
| `literal_values` | yes: `binding.ident` [run] | yes: `khg:ident` [run] | yes: `BINDS.ident`, shared `:Literal` [run] | yes, as identity attributes; the written form only in the JSON copy [run] | yes: literal nodes [run] |
| `special_values` | yes [run] | yes [run] | yes: per-binding `:Special` [run] | **no** (no player; a marker attribute is possible) [run] | yes [run] |
| `goals` | yes [run] | yes [run] | yes [run] | **no** (unbound has no player; a relation without players is deleted) [run] | yes [run] |
| `nesting` | yes: `ref` of kind `fact` [run] | yes [run] | yes: an identity `:Node` per fact [run] | yes: relations play roles [run] | yes [run] |
| `ordered_roles` | yes: `position` [run] | yes: `khg:position` [run] | yes: an edge property [run] | **no** (REP254) [run] | yes [run] |
| `valid_time` | yes: four instant columns [run] | yes [run] | yes [run] | yes: integer attributes [run] | yes [run] |
| `transaction_time` | yes: `tx_from`/`tx_to` (85/85 [run]; the full write path on SQLite, 114/114 [run]) | yes: a graph per version (85/85 [run]) | yes: version nodes (85/85 [run]) | **no** (no as-of reads, #7554) [read] | **no** (a snapshot file) [run] |
| `key_constraint` | yes: the shared write path [run on SQLite]; PostgreSQL 18 `WITHOUT OVERLAPS` as a guard [run] | yes: the shared write path [derived] | yes: the shared write path [derived] | yes: the shared write path (`@key` covers one attribute only) [derived] | yes [run] |
| `atomic_writes` | yes: one DB transaction per write [run on SQLite] | yes: `extend`/`update` are transactional [read] | yes: server transactions [read, not run with writes] | yes: one write transaction [run] | yes: `os.replace` [run] |
| `history_export` | yes [run] | yes [run] | yes [run] | **no** | **no** [run] |
| **Scenarios that apply** | **114** | **114** | **114** | **70** (78 with emulated specials and goals) | **107** (measured: 107 passed) |

The other candidates, on the same layouts:
- **SQL.** SQLite, DuckDB and PostgreSQL 16 match the PostgreSQL 18 column, except that PostgreSQL 16 has no
  `WITHOUT OVERLAPS` and uses `EXCLUDE` instead.
- **RDF.** rdflib matches Oxigraph, but has no transactions.
- **Property graph.** Memgraph, Kùzu and LadybugDB match Neo4j with a walk of one query per level. FalkorDB also
  matches, but its multi-statement transactions are [unverified]: every write would have to be one query.
- **Without versions in the layout.** An RDF layout without named graphs, or a property graph without version nodes,
  loses `transaction_time` and `history_export`, and then 107 scenarios apply. That is the variant §6.5 counted.

## 9. Risks

1. **Private API.** Sharing the write path (§10 D2) means importing `store._table`, `store._writes` and
   `store._events`. These are private modules of khg-contracts 1.0.0.dev0, so a P2 refactor can break every adapter
   at once.
2. **Licences.**
   - Neo4j Community is GPL v3: fine to run and benchmark, and P1 distributes none of its code.
   - Memgraph is BSL 1.1 and FalkorDB is SSPL v1. Both allow internal benchmarking. If they are reported, the
     report should state the licences.
   - TypeDB CE is MPL 2.0, and psycopg is LGPL-3.0.
   - None of these touches P1's release, which is adapters, a query set and measurements.
3. **Memory.**
   - Neo4j takes about 1.3 GB of RSS at a 1 GB heap and a 256 MB page cache. At P3a scale the page cache should
     hold the store, so size it from the corpus.
   - Memgraph keeps the whole graph in RAM.
   - The 15 GB container is ample for the fixture. For the corpus, measure first [unverified].
4. **Runtime pins and blocked channels.**
   - `falkordblite` requires Python 3.12 or later, while the dev venv is 3.11. The workaround is its bundled server.
   - `postgresql-wheel` requires Python below 3.10.
   - DuckPGQ lags DuckDB: it has no 1.5.5 build.
   - Kùzu and LadybugDB cannot share one process.
   - GitHub release downloads are blocked from this session unless a repository is added.
5. **Churn.**
   - Kùzu is archived, and LadybugDB is a 0.x successor.
   - RDF 1.2 and SPARQL 1.2 are still drafts, but the probe's layout does not depend on them.
   - TypeDB's lists and structs are announced but not implemented, so a later TypeDB may close the
     `ordered_roles` gap. The version must be pinned (3.13.6).
6. **Value fidelity outside the suite** (§7):
   - instants beyond int64, with FalkorDB's silent clamp and Oxigraph's failing comparisons;
   - collation;
   - repeated players in TypeDB.
7. **The server starts are fragile.** PostgreSQL needs a user namespace, because `initdb` refuses root and the
   scratchpad is 0700. Neo4j refuses a configuration with a repeated key. Memgraph needs a symlink for
   `libpython3.so`. §10 D10 scripts all three.
8. **Timing fairness.** Embedded engines (SQLite, Oxigraph, HIF) and servers (PostgreSQL, Neo4j, TypeDB) differ by a
   network round trip per call. Neo4j's per-call cost was visible even on the fixture: 25–32 s for 46 scenarios,
   against 1.3 s for Oxigraph.

## 10. Design decisions for P1

**D1. The five backends.**
- **Decision.** Which engine stands for each layout?
- **Recommended:**

  | Layout | Engine |
  |---|---|
  | Incidence table | **PostgreSQL 18.6**, from the zonky binaries, or `postgresql-18` from apt.postgresql.org elsewhere |
  | Reified RDF | **Oxigraph** through **pyoxigraph 0.5.11**, on disk |
  | Bipartite property graph | **Neo4j Community 2026.09.0** |
  | TypeDB | **TypeDB CE 3.13.6** with **typedb-driver 3.13.6** |
  | HIF | **khg-contracts `to_hif`/`from_hif`** over `MemoryStore`, one file |

- **SQLite 3.45.1** as an embedded control row, which costs nothing and separates "relational" from "server".
- Optionally **LadybugDB 0.20.4**, the embedded property-graph row.
- Record every version in the results table.

**D2. How the adapters share code.**
- **Decision.** How much of C2 does each adapter write itself?
- **Recommended:**
  - Build each adapter as **`MemoryStore`'s write path over a backend version table, plus native reads**. The
    table implements the 13-member interface of §1, and an adapter overrides `get`, `history`, `incident`, `find`,
    `find_by_key` and `iter_records` with native queries.
  - Give `load` a native bulk path: `COPY` in PostgreSQL, `bulk_extend` in Oxigraph, `UNWIND` batches in Neo4j,
    one write transaction in TypeDB, one file write for HIF.
  - Wrap `_commit` in one backend transaction. That is how the SQLite table store reached 114 of 114 [run].
- **The ask for P2.** Publish the table interface, for example a documented `store.VersionTableProtocol` and a
  `TableStore` base, in a khg-store minor release. P1 then does not depend on private modules. Until then, pin
  khg-contracts to the commit P1 tested.
- **Why.** `StoreBase` alone would leave each adapter to re-implement about 800 lines of checks five times. Five
  copies would diverge, and conformance failures would measure the copies, not the stores.
- **For timing.** `put` then times Python checks as well as the backend. So P1 times `load` (trusted, V001 and D018
  only; DESIGN §6.2) and the reads, and reports `put` separately.

**D3. Transaction time and immutable versions, per backend.**
- **Decision.** How does each backend keep versions and answer `as_at`?
- **Recommended:**

  | Backend | Versions | `as_at` read |
  |---|---|---|
  | PostgreSQL, SQLite | immutable version rows with a system-time period `[tx_from, tx_to)` in µs; `tx_to` is set when a new version is written (bookkeeping only) | `tx_from <= t AND (tx_to IS NULL OR tx_to > t)` |
  | Oxigraph | one named graph per version, with the metadata in the default graph; a trusted load uses `bulk_extend`, and writes use `extend` or `update` for atomicity | filter on the graph metadata |
  | Neo4j | `(:Version)-[:VERSION_OF]->(:Node)`; bindings point at identity nodes, so a nested fact's new version does not orphan its referrers | the same period on `:Version` |
  | TypeDB | none: declare the flags absent and report the 44 inapplicable scenarios as fidelity losses (ruling 1) | none |
  | HIF | a snapshot only: declare the flags absent | none |

- All five passed `as_at` where declared [run, §2–§4].

**D4. Valid-time instants.**
- **Decision.** How are the bound-table instants stored?
- **Recommended:**
  - Store the four instants as integer seconds, with ±∞ as sentinels (or NULL) and inclusive/exclusive exactly as
    `Bounds.holds_at`.
  - Use `numeric` in PostgreSQL. Elsewhere use int64 guarded by the adapter: an instant beyond ±2^62 is refused at
    load, reported and counted as a fidelity loss. That catches FalkorDB-style clamping before it happens.
  - In PostgreSQL, key ranges are `int8range` or `numrange`, never `tstzrange`: `timestamptz` stops at 4713 BC
    [run].

**D5. Measuring round-trip fidelity beyond the suite.**
- **Decision.** What does "round-trip fidelity" mean in the gate table?
- **Recommended:** report four numbers per backend.
  1. **Container round trip.** `load` → `export("khg-json")` → `compare_containers` on the fixture, the history
     fixture and the P3a slice. It counts differing records (the §1.3 P1 sequence).
  2. **Structural fidelity of the native layer.** Rebuild records from the native structure only, without payload
     or JSON copies. Count, per binding, the bids, role–value multisets, positions, directions, extensions and
     literals as written that survive. §5.4 does this for TypeDB; for the other layouts it should be 100%.
  3. **Answer fidelity.** Every query of the query set (D6) is compared with `MemoryStore`'s answer on the same
     corpus, as ids in order.
  4. **Inapplicable scenarios as fidelity losses** (ruling 1), listed by flag.
- **An edge-case container** should also be run through (1)–(3). It holds:
  - astral and full-width ids;
  - a 16-digit-year literal;
  - one filler repeated in one unordered role;
  - two equal literals in one role;
  - a multi-typed entity;
  - an all-unbound goal;
  - a literal-only fact;
  - a diamond of supersessions.

  Each item is aimed at a hazard found here.

**D6. A first draft of the query set for the timing half.**
- **Decision.** Which queries does the timing table measure?
- **Recommended.** Parameters are drawn from the P3a corpus with fixed seeds and stratified by degree (1–5, 6–100,
  hubs) and arity bin (0–1, 2, 3, 4, 5+). Each query is run warm (median and p95 of 20) and cold (first run after a
  restart).

  | Id | C2 call | What it stresses |
  |---|---|---|
  | L1 | `load` of the corpus (trusted bulk) | load time |
  | Q1 | `get(id)` for 1,000 random facts | point lookup plus reassembly |
  | Q2 | `get(id, as_at=t)` on the history slice | version selection |
  | Q3 | `incident(e)` for low-degree entities | the incidence index |
  | Q4 | `incident(hub, limit=100, after=…)`, paged to the end | pagination on hubs |
  | Q5 | `incident(e, role=r, relation=R)` | role and relation filters |
  | Q6 | `incident(e, where=Where(as_of=t))`, definite and possible | valid-time filter |
  | Q7 | `find(R, [one entity pattern])` | a single-role lookup |
  | Q8 | `find(R, [entity, qualifier time literal])` | a multi-pattern join with literal identity |
  | Q9 | `find(R, full binding multiset, match="exact")` | an exact match |
  | Q10 | `find(R, [])` paged through the whole relation | a relation scan |
  | Q11 | `find_by_key(R, key, where=Where(as_of=t))` ("who held P at t") | the key index plus valid time |
  | Q12 | `degree(hub)` | counting |
  | Q13 | `supersession_walk(id)` on chains of length 1–5 | recursion; synthetic chains if P3a has few |
  | Q14 | a two-hop neighbourhood: `incident(e)`, then `incident` of every co-participant (the P4/P10 walker step), as C2 calls and as one native query where the engine has one | traversal through the fact layer |
  | X1, X2 | `export("khg-jsonl")` and `export("hif")` of the whole store | export |

**D7. The timing protocol.**
- **Decision.** How are the timings taken?
- **Recommended:**
  - One machine and one run order, with servers restarted between backends.
  - Time through `store.Timed` (end to end, which is what a caller sees). Add server-side times where they exist:
    PostgreSQL `EXPLAIN (ANALYZE)`, Neo4j `PROFILE`.
  - Label every row embedded or client–server.
  - Report memory (peak RSS) and disk after load beside the times.

**D8. The scope of TypeDB.**
- **Decision.** Does P1 emulate TypeDB's missing flags?
- **Recommended:**
  - Measure the natural mapping (70 applicable) as the headline row, since ruling 1 does not require emulation.
  - Optionally add a second row with marker attributes and an anchor role (78 applicable), because that emulation
    is cheap.
  - Do not emulate ordered roles or transaction time: both would live only in a JSON copy and never in TypeQL.

**D9. Layout variants worth one ablation each.**
- **Decision.** Which layout choices get an ablation?
- **Recommended:**
  - The property graph: `role` as an edge property with a relationship index (probed) against one relationship
    type per role (the KB's suggestion).
  - RDF: binding nodes only (probed) against binding nodes plus role-predicate shortcut triples
    (`<f> khgr:<role> <v>`), which let SPARQL property paths walk.
  - Anything else stays as probed here.

**D10. Reproducibility.**
- **Decision.** How are the environment and results kept reproducible?
- **Recommended:**
  - Ship a `start-servers.sh` that records the §2–§5 commands, the versions and the sha256 of each download.
  - Keep data under a scratch root, never in the repository.
  - Keep the probes' `common.py` as the seed of the adapters' shared module.
  - Record the contract versions (C1 `khg-record/1.0.0`, C2 `khg-store/1.0.0`) and the khg-contracts commit in
    every results file.

## 11. Corrections proposed (not applied)

| Where | Proposed change | Evidence |
|---|---|---|
| P2 DESIGN §6.5, RDF row | With the layout the row itself names (named graphs per version), `transaction_time` and `history_export` hold, and 114 scenarios apply. 107 is the count for a layout without named graphs | §3, 85/85 `as_at` checks [run] |
| P2 DESIGN §6.5, property-graph row | With version nodes, 114 apply. The row's layout has none, so say so, or add them | §4 [run] |
| P2 DESIGN §6.5, incidence row | The exclusion constraint should use `int8range` (or `numrange`) over the instant seconds: `tstzrange` cannot hold dates before 4713 BC. `WITHOUT OVERLAPS` and `EXCLUDE` both need `btree_gist` for the text columns. Database collation `C` | §2.3, §7 [run] |
| P2 DESIGN §6.5, TypeDB row | Add the reasons: player-less relations are deleted, repeated players collapse, bids and positions have no home, instances have one type. The figure 70 stands | §5 [run] |
| `kb/04-storage-and-formats/relational-and-eav-storage.md` §1b | `PRIMARY KEY (fact_id, entity_id, role)` cannot hold one filler twice in one role (`flight_route` stops YYZ, YUL, YYZ), nor literal or special values. Key on `(fact_id, version, bid)` with `value_kind` and value columns | §2.2 |
| `kb/04-storage-and-formats/property-graph-emulation-patterns.md` §1b and §4 rule 2 | Neo4j 5+ (checked on 2026.09.0) builds range indexes on relationship properties, so "role as a property" is indexable. Qualify "less cheaply" | §4.2 [run] |
| `kb/04-storage-and-formats/hypergraph-databases.md`, the Kùzu row | Kùzu is archived (0.11.3 is final). Its successor is LadybugDB 0.20.4 (2026-09-10, MIT, "formerly known as Kuzu"). The two cannot be imported in one process | §4.1 [run] |
| `kb/04-storage-and-formats/format-recommendations.md` §1 (querying via SQL/PGQ) | DuckPGQ (DuckDB 1.5.4) matches fixed-length patterns over the incidence tables, but refuses variable-length paths over the bipartite layout and has no DuckDB 1.5.5 build | §4.3 [run] |

## Probe index

| File | What it does | Output |
|---|---|---|
| [common.py](probes/common.py) | row layout, `ReadOnlyProbe`, the 46 read-only scenario ids, hand queries, the history check | |
| [sql_incidence.py](probes/sql_incidence.py) | SQLite, DuckDB, PostgreSQL 16 and 18; the temporal-key constraint demo | out/sql-*.json |
| [rdf_relation_instance.py](probes/rdf_relation_instance.py) | Oxigraph and rdflib, a named graph per version | out/rdf-*.json |
| [pg_cypher.py](probes/pg_cypher.py) | Neo4j, Memgraph, FalkorDB | out/pg-{neo4j,memgraph,falkordb}.json |
| [pg_kuzu.py](probes/pg_kuzu.py) | Kùzu, LadybugDB (typed DDL) | out/pg-{kuzu,ladybug}.json |
| [duckpgq_probe.py](probes/duckpgq_probe.py) | SQL/PGQ over the incidence tables | out/pg-duckpgq.json |
| [typedb_features.py](probes/typedb_features.py), [typedb_lists.py](probes/typedb_lists.py) | what TypeQL 3.13.6 accepts | out/typedb-features.txt |
| [typedb_probe.py](probes/typedb_probe.py) | schema generation, load, TypeQL reads, the native-structure rebuild | out/typedb.json |
| [hif_store.py](probes/hif_store.py) | the HIF file store, the full suite, reopen | out/hif.json |
| [table_store_sqlite.py](probes/table_store_sqlite.py) | `MemoryStore`'s write path over a SQLite table, the full suite | out/table-store-sqlite.json |
| [ordering_probe.py](probes/ordering_probe.py) | id order and integer range on every engine | out/ordering.json |

The probes run with a venv that has khg-contracts on its path (a `.pth` file pointing at `src/`) and the pinned
clients. The servers must already be running as described in §2–§5.

## Sources

**Programme and contract (this repository, read 2026-09-25):**
- [projects/PLAN.md](../../PLAN.md) §3, §4, §5, §7; [P1 README](../README.md).
- [P2 DESIGN](../../p2-role-aware-hif/DESIGN.md): §2 (C1), §2.10 (projections), §6 (C2, flags, suite, §6.5) and §14
  (ruling 1; rulings 10–16).
- [P2 research 04](../../p2-role-aware-hif/research/04-prior-art-modelling.md): M2, M3, M9, §11. TypeDB 3.x
  attributes cannot play roles; lists are "not yet available"; Kùzu is archived.
- `src/khg_contracts/store/` (`base.py`, `memory.py`, `_table.py`, `_writes.py`, `_events.py`, `flags.py`,
  `conformance/`), `src/khg_contracts/record/project.py` and `src/khg_contracts/hif/`, all khg-contracts
  1.0.0.dev0; the 114 files in `src/khg_contracts/data/scenarios/`; `fixture.c1.json`,
  `fixture.history.c1.json` and `fixture.relation-schema.json`.

**KB notes:**
- [format-recommendations](../../../kb/04-storage-and-formats/format-recommendations.md)
- [hypergraph-databases](../../../kb/04-storage-and-formats/hypergraph-databases.md)
- [property-graph-emulation-patterns](../../../kb/04-storage-and-formats/property-graph-emulation-patterns.md)
- [relational-and-eav-storage](../../../kb/04-storage-and-formats/relational-and-eav-storage.md)
- [rdf-star-and-semantic-web-serialisations](../../../kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md)

**Engines and packages** (versions as installed; PyPI upload dates from the PyPI JSON API, checked 2026-09-25):
- PostgreSQL 18.6 binaries: `io.zonky.test.postgres:embedded-postgres-binaries-linux-amd64:18.6.0`, jar built
  2026-08-26. https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-linux-amd64/18.6.0/
- PostgreSQL 16.13: the Ubuntu 24.04 package `postgresql-16` 16.13-0ubuntu0.24.04.1, preinstalled.
- The PGDG apt repository for noble, with `postgresql-18` 18.6-1.pgdg24.04+2 listed.
  https://apt.postgresql.org/pub/repos/apt/dists/noble-pgdg/
- psycopg 3.3.6 (2026-09-18, LGPL-3.0). https://pypi.org/project/psycopg/
- DuckDB 1.5.5 (2026-07-22) and 1.5.4. https://pypi.org/project/duckdb/
- The DuckPGQ community extension: `…/v1.5.4/linux_amd64/duckpgq.duckdb_extension.gz` is present, and the v1.5.5
  path returns 404. https://community-extensions.duckdb.org/
- SQLite 3.45.1, the library linked by Python 3.11.15 in this container.
- pyoxigraph 0.5.11 (2026-09-02, MIT OR Apache-2.0); the `Store`, `extend`, `update` and `bulk_extend` docstrings.
  https://pypi.org/project/pyoxigraph/
- rdflib 7.6.0 (2026-02-13, BSD-3-Clause). https://pypi.org/project/rdflib/
- Neo4j Community 2026.09.0: the Maven metadata `org.neo4j:neo4j` (latest 2026.09.0, lastUpdated 2026-09-22)
  and the tarball, whose `LICENSE.txt` is GPL v3.
  https://repo1.maven.org/maven2/org/neo4j/neo4j/maven-metadata.xml ;
  https://dist.neo4j.org/neo4j-community-2026.09.0-unix.tar.gz
- The neo4j Python driver 6.3.1 (2026-09-15, Apache-2.0). https://pypi.org/project/neo4j/
- Neo4j Cypher Manual, quantified path patterns (run here on Cypher 5/25).
  https://neo4j.com/docs/cypher-manual/current/patterns/variable-length-patterns/
- Memgraph 3.13.1, from the direct download links (latest 3.13.1, checked 2026-09-25); `BSL.txt` in the deb.
  https://memgraph.com/docs/getting-started/install-memgraph/direct-download-links
- pymgclient 1.6.0 (2026-07-20, Apache-2.0). https://pypi.org/project/pymgclient/
- FalkorDB: the licence, SSPL v1 ("Server Side Public License VERSION 1, OCTOBER 16, 2018").
  https://raw.githubusercontent.com/FalkorDB/FalkorDB/master/LICENSE.txt ; the docs licence page
  https://docs.falkordb.com/References/license.html
- falkordblite 0.10.0 (2026-05-02; requires Python 3.12 or later; bundles Redis 8.6.2 and the graph module 41803).
  https://pypi.org/project/falkordblite/
- The falkordb client 1.7.1 (2026-08-13). https://pypi.org/project/falkordb/
- Kùzu 0.11.3 (2025-10-10, MIT). https://pypi.org/project/kuzu/ ; the archiving notice is quoted in P2 research
  04 §9.1 (README of `kuzudb/kuzu`, commit `06890e1`).
- LadybugDB 0.20.4 (2026-09-10, MIT): "The database was formerly known as Kuzu".
  https://pypi.org/project/ladybug/
- TypeDB CE 3.13.6, the install page and its download URL.
  https://typedb.com/docs/home/install/ce/ ;
  https://repo.typedb.com/public/public-release/raw/names/typedb-all-linux-x86_64/versions/latest/download
- typedb-driver 3.13.6 (2026-09-21, Apache-2.0). https://pypi.org/project/typedb-driver/
- The TypeQL reference on structs: "Structs are a planned feature and not yet available in TypeDB. Coming soon!"
  https://typedb.com/docs/typeql-reference/expressions/structs/
- typedb/typedb issue #7554, "Feature: Add the Option to Perform Point-in-Time and Temporal Range Queries" (open,
  opened 2025-08-20). https://github.com/typedb/typedb/issues/7554

**Standards status** (as recorded by the KB and P2 research 04, not re-checked here):
- RDF 1.2 Concepts, Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- SPARQL 1.2 Query, Working Draft, 21 September 2026. https://www.w3.org/TR/sparql12-query/
