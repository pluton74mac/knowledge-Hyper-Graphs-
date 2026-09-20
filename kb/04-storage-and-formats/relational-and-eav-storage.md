---
title: Relational, EAV and Datalog storage for n-ary facts
type: survey
status: draft
tags: [relational, sql, incidence-table, eav, datalog, souffle, logicblox, relationalai, sql-pgq, parquet]
created: 2026-09-20
updated: 2026-09-20
---

# Relational, EAV and Datalog storage for n-ary facts

The relational model has stored n-ary facts since 1970. A row of an n-column table *is* a labelled
n-ary tuple, with roles as column names. Everything the graph world calls "the n-ary problem" is an
artefact of having chosen a binary model first. This note covers the four relational shapes a
knowledge hypergraph can take, what each costs, and where the Datalog engines fit.

Checked 2026-09-20.

## 1. Four shapes

### 1a. Wide n-ary table — one table per relation type

```sql
CREATE TABLE treats_fact (
  fact_id     text PRIMARY KEY,
  treatment   text NOT NULL REFERENCES entity(id),
  condition   text NOT NULL REFERENCES entity(id),
  dosage      text REFERENCES entity(id),
  population  text REFERENCES entity(id),
  confidence  double precision,
  source      text,
  valid_from  date,
  valid_to    date
);
```

- **Best possible query performance.** One row per fact, one index scan per lookup, roles are
  columns so the planner has statistics on them.
- **Rigid.** A new relation type is a new table, i.e. a migration. A KHG with a few hundred
  relation types has a few hundred tables; one built by an open-vocabulary LLM extractor has an
  unbounded number, which makes this shape unusable there (see
  [../03-construction/llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md)).
- Sparse roles waste nothing much in a columnar store, but they do in a row store.

Use when the schema is closed and known: curated biomedical or financial KHGs.

### 1b. Incidence table — the universal shape

```sql
CREATE TABLE fact (
  fact_id    text PRIMARY KEY,
  relation   text NOT NULL,
  arity      int  NOT NULL,
  confidence double precision,
  source     text,
  valid_from date, valid_to date
);
CREATE TABLE incidence (
  fact_id   text NOT NULL REFERENCES fact(fact_id),
  entity_id text NOT NULL REFERENCES entity(id),
  role      text,
  direction text CHECK (direction IN ('head','tail')),
  position  int,
  PRIMARY KEY (fact_id, entity_id, role)
);
CREATE INDEX ON incidence (entity_id, role);
CREATE INDEX ON incidence (fact_id);
```

This is HIF in SQL: `fact` is `edges`, `incidence` is `incidences`, and `entity` is `nodes`. It is
the shape that:

- handles unbounded and open-vocabulary arity with no migrations;
- indexes both directions (entity -> facts, fact -> entities) with two B-trees;
- maps directly to a Parquet file for analysis (`incidence` is already a long table);
- converts to a sparse incidence matrix by a single `GROUP BY`
  ([tensor-and-sparse-representations.md](tensor-and-sparse-representations.md));
- costs one join for "the other participants of this fact" and two for "facts connecting X and Y".

Its weakness is exactly the reified-node weakness in
[property-graph-emulation-patterns.md](property-graph-emulation-patterns.md): every traversal is a
self-join through `incidence`, so k-hop queries are k self-joins, and the optimiser must be given
good statistics or it will pick the wrong join order on high-degree entities.

LightRAG's `PGTableGraphStorage` is a production instance of this idea for the binary case:
"It keeps the entity-relation graph in ordinary tables — JSONB properties plus B-tree indexes —
instead of going through Apache AGE", and the published measurements have it ~28x faster at p50 on
its main query than the Cypher-over-`agtype` path
([LightRAG API server docs](https://github.com/HKUDS/LightRAG/blob/main/docs/LightRAG-API-Server.md),
checked 2026-09-20).

### 1c. EAV / triple table — the degenerate case

```sql
CREATE TABLE triple (subject text, predicate text, object text, graph text);
```

An EAV table is the incidence table with arity fixed at 2 and the role folded into `predicate`. All
RDF stores are elaborations of it (six or more permuted indexes, dictionary-encoded terms). An
n-ary fact needs the relation-instance pattern: one `subject` per fact, one row per role. Which
means an EAV store *is* an incidence table with a worse column layout — the role lives in a column
of the same type as the entity, so you cannot put a different index on it.

Where EAV wins: total schema freedom, and a very mature dictionary-encoding and index-permutation
literature. Where it loses: one row per role means the fact-level attributes (confidence, validity)
either repeat on every row or need their own rows.

### 1d. Document / JSONB column

```sql
CREATE TABLE fact (
  fact_id text PRIMARY KEY,
  relation text,
  members jsonb  -- [{"entity":"drug:metformin","role":"treatment","direction":"tail"}, ...]
);
CREATE INDEX ON fact USING gin (members jsonb_path_ops);
```

One row per fact, members inline. Good locality for "give me this fact"; bad for "give me all facts
where X plays role R" unless the GIN index covers the access pattern. Reasonable as a *serving*
layer over an incidence table, not as the primary index.

## 2. Datomic and the EAV(T) variant

Datomic stores *datoms*: entity, attribute, value, transaction, plus an assert/retract flag. The
transaction component makes the database an accumulating log rather than a mutable state, so every
historical version remains queryable ([Datomic documentation](https://docs.datomic.com/)). For a
KHG this changes the n-ary calculus: because an entity is just an ID that attributes attach to,
creating a "fact entity" with one attribute per role is idiomatic rather than a workaround, and
versioning and provenance come from the transaction dimension instead of from extra columns (see
[versioning-provenance-and-scale.md](versioning-provenance-and-scale.md)). The query language is
Datalog, which makes the self-joins of shape 1b implicit.

## 3. Datalog engines

An n-ary relation is a Datalog predicate. This is the one formalism where "knowledge hypergraph"
needs no encoding at all: `treats(Drug, Disease, Dosage, Population)` is a 4-ary predicate, and
rules over it are first-class.

- **Soufflé** — "The Soufflé language is similar to Datalog (but has terms known as records), and
  is frequently used as a domain-specific language for analysis problems". It compiles Datalog to
  parallel C++ and has "Specialized data structure for relations (PACT'19, PPoPP'19, PMAM'19) with
  optimal index selection (VLDB'18)" and "Recursively defined record types/ADTs"
  ([Soufflé repository README](https://github.com/souffle-lang/souffle), checked 2026-09-20). The
  automatic index selection is the relevant part: given the rules, Soufflé derives which indexes an
  n-ary relation needs — the thing you have to do by hand in shape 1b.
- **LogicBlox** — the commercial system that made the case for Datalog as a database engine:
  [Aref, ten Cate, Green, Kimelfeld, Olteanu, Pasalic, Veldhuizen and Washburn, "Design and
  Implementation of the LogicBlox System", SIGMOD 2015, pp. 1371–1382](https://doi.org/10.1145/2723372.2742796).
  Source of the worst-case-optimal join work (leapfrog triejoin) that later engines adopted.
- **RelationalAI** — the current commercial descendant; its Rel language is a Datalog-family
  language over relations of arbitrary arity, positioned as a "relational knowledge graph"
  ([RelationalAI documentation](https://docs.relational.ai/), checked 2026-09-20).

Why this matters for storage design: **worst-case-optimal joins were invented for exactly the
access pattern a hypergraph query has** — a multiway join over several relations sharing variables,
where any pairwise join order blows up. If your KHG queries look like "find facts where A plays
role R1 and B plays role R2 and the two facts share a participant", a WCOJ engine is the right
shape and a binary graph traversal is the wrong one. Oxigraph's changelog even exposes join-order
information "for consumption by external execution engines (e.g. worst-case-optimal join
executors)" ([Oxigraph CHANGELOG, unreleased section](https://github.com/oxigraph/oxigraph/blob/main/CHANGELOG.md),
checked 2026-09-20).

## 4. SQL/PGQ and GQL

SQL:2023 added Part 16, **SQL/PGQ** (Property Graph Queries), which lets a SQL engine expose
existing tables as a property graph and run graph pattern matching over them; **GQL** was published
as ISO/IEC 39075:2024 on 12 April 2024 as a standalone graph query language
([Graph Query Language, Wikipedia, checked 2026-09-20](https://en.wikipedia.org/wiki/Graph_Query_Language)).

Both standardise the **property graph**: vertices, binary edges, labels, properties. Neither has a
hyperedge or an n-ary edge. So for a knowledge hypergraph, SQL/PGQ is useful in exactly one way: it
lets you keep the incidence table as the system of record and *project* a reified-node property
graph over it for pattern-matching queries, without duplicating the data. That is a genuinely good
architecture — relational storage, graph query surface — and it is the only standards-track answer
currently available to "I want graph queries over n-ary facts".

## 5. Columnar files: Parquet and Arrow

The incidence table wants to be a Parquet file whenever the workload is analytical rather than
transactional:

```
incidence.parquet:  fact_id (dict) | entity_id (dict) | role (dict) | direction (dict) | position (int32)
fact.parquet:       fact_id | relation (dict) | arity (int32) | confidence (double) | source | valid_from | valid_to
entity.parquet:     entity_id | label | type (dict) | ...
```

Dictionary encoding collapses the repeated entity and role strings; predicate pushdown makes
"facts with relation R" a metadata scan; and DuckDB, Polars, pandas and Spark all read it directly
([Apache Parquet documentation](https://parquet.apache.org/docs/),
[Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html)). This is also
the cheapest bridge to the ML stack: `hyperedge_index` for PyTorch Geometric is two columns of the
incidence table
([tensor-and-sparse-representations.md](tensor-and-sparse-representations.md)).

## 6. Decision summary

| Workload | Shape |
|---|---|
| Closed schema, OLTP, known relation types | 1a wide tables |
| Open vocabulary, mixed read/write, one system of record | **1b incidence tables** |
| Standards interop, entailment, per-fact provenance | 1c EAV / RDF store |
| Serving layer, whole-fact reads | 1d JSONB, over 1b |
| Rules, recursion, multiway joins | Datalog (Soufflé / RelationalAI) over 1b |
| Analytics, ML feature extraction, archival | Parquet copies of 1b |
| Graph pattern queries without leaving SQL | 1b + SQL/PGQ projection |

## Sources

- Souffle repository README (checked 2026-09-20). https://github.com/souffle-lang/souffle — project site https://souffle-lang.github.io/
- Aref, M., ten Cate, B., Green, T. J., Kimelfeld, B., Olteanu, D., Pasalic, E., Veldhuizen, T. L. and Washburn, G. (2015). *Design and Implementation of the LogicBlox System*. SIGMOD 2015, pp. 1371–1382. https://doi.org/10.1145/2723372.2742796
- RelationalAI documentation (checked 2026-09-20). https://docs.relational.ai/
- Datomic documentation (checked 2026-09-20). https://docs.datomic.com/
- Wikipedia. *Graph Query Language* — ISO/IEC 39075:2024 published 12 April 2024; SQL/PGQ as Part 16 of SQL:2023 (checked 2026-09-20). https://en.wikipedia.org/wiki/Graph_Query_Language
- LightRAG, `docs/LightRAG-API-Server.md`, "Storage Types Supported" and the `PGTableGraphStorage` measurements (checked 2026-09-20). https://github.com/HKUDS/LightRAG/blob/main/docs/LightRAG-API-Server.md
- Oxigraph `CHANGELOG.md`, unreleased section on join-order variables for worst-case-optimal join executors (checked 2026-09-20). https://github.com/oxigraph/oxigraph/blob/main/CHANGELOG.md
- Apache Parquet documentation. https://parquet.apache.org/docs/
- Apache Arrow columnar format specification. https://arrow.apache.org/docs/format/Columnar.html
- PostgreSQL documentation, `CREATE TABLE` (for the DDL used in the examples). https://www.postgresql.org/docs/current/sql-createtable.html
