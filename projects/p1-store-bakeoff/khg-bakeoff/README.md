# khg-bakeoff

The C2 store interface (`khg-store/1.0.0`, the contract of [khg-contracts](../../../README.md)) on six backends, and
the conformance and fidelity runs of P1, the format and store bake-off ([DESIGN](../DESIGN.md)). MIT.

| Backend | Layout | Engine (client) | Kind | Flags declared absent |
|---|---|---|---|---|
| `sqlite` | incidence table | SQLite 3.45.1 (`sqlite3`) | embedded | none |
| `postgres` | incidence table, `numeric` instants, key guard | PostgreSQL 18.6 (psycopg 3.3.6) | client–server | none |
| `oxigraph` | reified RDF, a named graph per version | Oxigraph (pyoxigraph 0.5.11), on disk | embedded | none |
| `neo4j` | bipartite property graph, version nodes | Neo4j Community 2026.09.0 (neo4j 6.3.1) | client–server | none |
| `typedb` | TypeDB natural mapping | TypeDB CE 3.13.6 (typedb-driver 3.13.6) | client–server | `ordered_roles`, `special_values`, `goals`, `transaction_time`, `history_export` |
| `hif` | one role-aware HIF file | khg-contracts `to_hif`/`from_hif` | file, read in memory | `transaction_time`, `history_export` |

Every adapter is khg-contracts' `store.table.TableStore` (ruling 17): the reference store's write path over the
backend's own version table, one backend transaction per write, and the reads as native queries (SQL, SPARQL,
Cypher, TypeQL). Each imports public khg-contracts names only. A read pushes its filters, `limit` and counts into
the engine and fetches its records in a bounded number of queries, rebuilt by one shared function
(`rows.record_of`); the HIF store answers from the index it rebuilds from its file. Every adapter counts its engine
calls (`store.trips`).

## Licences

The package is MIT. What it runs against (review 01, R-12):

| Component | Version | Licence |
|---|---|---|
| PostgreSQL (server) | 18.6 | PostgreSQL Licence |
| psycopg (client, with psycopg-binary) | 3.3.6 | LGPL-3.0-only |
| Neo4j Community (server) | 2026.09.0 | GPL v3 |
| neo4j Python driver | 6.3.1 | Apache-2.0 AND Python-2.0 (its package metadata) |
| TypeDB CE (server) | 3.13.6 | MPL 2.0 |
| typedb-driver | 3.13.6 | Apache-2.0 |
| pyoxigraph (Oxigraph, embedded) | 0.5.11 | MIT or Apache-2.0 |
| SQLite (Python's `sqlite3`) | 3.45.1 | public domain |
| khg-contracts | 1.0.0.dev0 | MIT |

The servers are not redistributed: `../start-servers.sh` fetches each from its publisher.

## Install

```bash
pip install .                                                    # khg-contracts, from the repository root
pip install "./projects/p1-store-bakeoff/khg-bakeoff[all,dev]"   # extras: oxigraph, postgres, neo4j, typedb, all, dev
```

The servers are not installed by pip: `../start-servers.sh` fetches, checks and starts PostgreSQL 18.6, Neo4j
Community 2026.09.0 and TypeDB CE 3.13.6 outside the repository.

## Command line

```bash
export KHG_BAKEOFF_POSTGRES="host=127.0.0.1 port=5418 user=postgres"   # libpq conninfo without dbname
export KHG_BAKEOFF_NEO4J=bolt://127.0.0.1:7687
export KHG_BAKEOFF_TYPEDB=127.0.0.1:1729
khg-bakeoff conformance --out ../results/conformance               # EARL reports, summary.json, summary.md
khg-bakeoff fidelity --out ../results --conformance ../results/conformance/summary.json
khg-bakeoff trips --out ../results                                 # roundtrips.json, roundtrips.md
```

Without a backend name each command runs every backend it can reach here (a server backend needs its variable).
`conformance` exits 1 when an applicable scenario fails.

## Python API

```python
from khg_bakeoff.sqlite import SQLiteStore            # SQLiteStore(schema, *, path=None, clock=None, ...)
from khg_bakeoff.postgres import PostgresStore        # PostgresStore(schema, *, conninfo, database="khg_bakeoff", namespace=None, ...)
from khg_bakeoff.oxigraph import OxigraphStore        # OxigraphStore(schema, *, path=None, ...)
from khg_bakeoff.neo4j import Neo4jStore              # Neo4jStore(schema, *, uri, auth=None, namespace=None, ...)
from khg_bakeoff.typedb import TypeDBStore            # TypeDBStore(schema, *, address, database=None, ...)
from khg_bakeoff.hif import HifStore                  # HifStore(schema, *, path=None, ...)
from khg_bakeoff.backends import factory              # factory("sqlite")(schema, clock): a conformance factory
```

Each store is a `khg_contracts.store.Store`. `cannot_hold(record)` says what a backend refuses (an instant beyond
±(2^62 − 2) s in an int64 backend; a multi-typed entity or a fact without players in TypeDB); `native_bindings(id)`
rebuilds a fact's bindings from the layout alone (fidelity number 2).

## Tests

```bash
cd projects/p1-store-bakeoff/khg-bakeoff && python -m pytest -q
```

The embedded backends (SQLite, Oxigraph, HIF) run the full 114-scenario suite; PostgreSQL, Neo4j and TypeDB run
only when their variable names an endpoint, and skip otherwise. `tests/test_offline.py` checks the Neo4j and TypeDB
adapters' pure-Python parts without servers or drivers. Some tests read the project's files (`../README.md`,
`../results/`, `../start-servers.sh`, the CI workflow, P2's DESIGN) and skip outside a repository checkout.
