---
title: Hypergraph and n-ary databases
type: survey
status: draft
tags: [database, hypergraphdb, typedb, atomspace, hyperon, terminusdb, datomic, kuzu, apache-age, storage-engine]
created: 2026-09-20
updated: 2026-09-20
---

# Hypergraph and n-ary databases

Three kinds of system claim to store hyperedges:

1. **Native hypergraph stores** — the storage record *is* a tuple of arbitrary length
   (HyperGraphDB, OpenCog AtomSpace, Hypergraph-DB).
2. **Native n-ary relation stores** — the record is a relation instance with named roles; arity is
   unbounded but the model is relational rather than set-theoretic (TypeDB, and in a different way
   Datomic and RelationalAI).
3. **Property-graph and RDF stores that emulate** — everything else. Covered as a family here and
   in detail in [property-graph-emulation-patterns.md](property-graph-emulation-patterns.md).

All entries checked 2026-09-20.

## 1. HyperGraphDB (Iordanov, 2010)

The reference design for a native hypergraph store, and still the most thorough one.
[Iordanov (2010), "HyperGraphDB: A Generalized Graph Database", LNCS 6185, pp. 25–36 (WAIM 2010 workshops)](https://doi.org/10.1007/978-3-642-16720-1_3).

**Model.** "In the HyperGraphDB data model, the basic representational unit is called an atom. Each
atom has an associated tuple of atoms called its target set. The size of the target set is called
the atom's arity. Atoms of arity 0 are called nodes and atoms of arity > 0 are called links. The
incidence set of an atom x is the set of atoms that have x as a member of their target set." The
target set is a **tuple**, not a set — order is part of the identity, and the paper says this was a
practical choice, not a necessary one: "The use of tuples instead of sets for an atom's target set
is not the only possible choice; both can be supported, but we have focused on the former as the
most practical by far."

Because links are atoms and target sets contain atoms, **a link may target a link**: the model is a
*generalized* hypergraph, and, as the paper puts it, this "automatically reifies every entity
expressed in the database". Nesting is free rather than encoded.

**Storage.** Two layers. The primitive layer is two key-value maps:

```
LinkStore : ID -> List<ID>
DataStore : ID -> List<byte>
```

with IDs being type-4 UUIDs so that "each data peer can make up new IDs without a central
authority". The model layer formalises the layout as

```
AtomID   -> [TypeID, ValueID, TargetID, ..., TargetID]
ValueID  -> List<ID> | List<byte>
```

— that is, one record per atom: type handle, value handle, then the target tuple. Three core
indices support it: `IncidenceIndex` (atom -> links pointing to it), `TypeIndex` (type -> its
instances), `ValueIndex` (value -> atoms carrying it). The underlying store need only be an
efficient key-value index supporting multiple ordered values per key; "the BerkeleyDB storage
system ... is currently being used" (2010).

**Why it matters for a KHG.** This layout is the answer to "how do I index a hypergraph on disk":
one row per hyperedge holding its member handles, plus an inverted incidence index. Every design in
this note is a variation on it. Current release status of the Java implementation is
**[unverified]** — the repository and site are live but no release date was confirmed.

## 2. TypeDB (formerly Grakn) — n-ary relations with named roles

TypeDB is the only mainstream database whose *schema language* has unbounded-arity relations with
typed roles. In TypeQL:

```typeql
relation employment,
  relates employer,
  relates employee;

relation insurance-obligation,
  relates employer,
  relates employee,
  relates insurance;

company plays employment:employer;
```

Relations are "types which define one-or-more associated interface types called roles"; an n-ary
relation is written as a tuple `(role-1: $a, role-2: $b, role-3: $c) isa n-ary-relation`, roles may
be omitted and inferred, and relations may themselves play roles — which gives nesting
([TypeDB documentation](https://typedb.com/docs/core-concepts/typeql/entities-relations-attributes/),
checked 2026-09-20).

In hypergraph terms: a TypeDB relation instance **is** a directed, typed, role-labelled hyperedge,
and the schema constrains which types may occupy which role — exactly the schema layer HIF lacks
(see [hif-hypergraph-interchange-format.md](hif-hypergraph-interchange-format.md), section 9). The
cost is a closed ecosystem: TypeQL is the only query language, and files are `.tql` schema + data
scripts rather than an interchange format.

## 3. OpenCog AtomSpace and Hyperon / MeTTa

"The OpenCog AtomSpace is an in-RAM knowledge representation (KR) database with an associated query
engine and graph-re-writing system. It is a kind of in-RAM generalized hypergraph (metagraph)
database" ([AtomSpace README](https://github.com/opencog/atomspace), checked 2026-09-20).

The storage claim is unusual and worth quoting because it is the opposite of everyone else's:
"**It's not a vertex+edge store**. (Almost?) all graph databases decompose graphs into lists of
vertexes and edges. ... The problem with this storage format is locality." Instead, "the AtomSpace
stores immutable, globally unique, typed s-expressions. ... Each s-expression is called 'an Atom'.
Each Atom is globally unique: there is only one copy, ever, of any given s-expression", with "a
(mutable) key-value database ... attached to each Atom" holding Values.

So the persisted form of an AtomSpace is s-expressions, and the split between immutable structure
(Atoms) and mutable payload (Values) is the same split HyperGraphDB makes between atoms and values.
Persistence and distribution are separate modules: `atomspace-rocks` (RocksDB-backed disk storage)
and `atomspace-cog` (network-distributed storage).

**Hyperon / MeTTa** is the successor language: "an 'Atomese 2' language called MeTTa (Meta Type
Talk)" ([hyperon-experimental README](https://github.com/trueagi-io/hyperon-experimental)), with
programs and data both being MeTTa expressions in a *Space*. For a KHG this is the most
expressive option on the list and the least interoperable: nothing outside the OpenCog world reads
Atomese.

## 4. Hypergraph-DB (2024–2025) — the lightweight native option

A Python library that behaves like an embedded hypergraph database: vertices and hyperedges with
property dicts, degree and neighbour queries, and persistence via `hg.save("x.hgdb")` (pickle) plus
`hg.save_as_hif(...)` / `hg.load_from_hif(...)` for the interchange format. Version 0.3.0 was
uploaded to PyPI on 2025-10-14.

Its README publishes a stress test: on a hypergraph with 1,000,000 vertices and 200,000 hyperedges
it reports 1.75 s to add the vertices, 1.82 s to add the hyperedges, 0.51 s for 400,000 vertex
queries and 2.52 s for 400,000 hyperedge queries, 6.60 s total
([Hypergraph-DB README](https://github.com/iMoonLab/Hypergraph-DB), checked 2026-09-20). These are
in-process Python numbers on the authors' hardware and should be read as an order-of-magnitude
claim, not a benchmark.

It is the graph store behind Hyper-RAG — see
[vector-stores-and-hybrid-storage-for-rag.md](vector-stores-and-hybrid-storage-for-rag.md).

## 5. The emulators

| System | What it really stores | n-ary path | Notes (checked 2026-09-20) |
|---|---|---|---|
| **Neo4j** | labelled property graph, binary relationships | reified node (`(:Fact)-[:ROLE]->(:Entity)`) | No hyperedge type. Cypher; `LOAD CSV` for bulk. The de-facto target of most KHG projects because of tooling, not fit |
| **Amazon Neptune** | RDF quads *or* property graph | RDF reification / relation instance, or reified node | dual-model; same emulation either way |
| **ArangoDB** | JSON documents + edge collections (`_from`, `_to`) | reified document + edge collection | edges are binary documents; multi-model, AQL ([ArangoDB graphs docs](https://docs.arangodb.com/stable/graphs/)) |
| **TigerGraph** | typed vertices and edges, MPP | reified vertex | GSQL; edge types are `FROM`/`TO` pairs ([GSQL schema docs](https://docs.tigergraph.com/gsql-ref/current/ddl-and-loading/defining-a-graph-schema)) |
| **Apache AGE** | property graph *inside PostgreSQL* | reified node | "an extension for PostgreSQL that enables users to leverage a graph database on top of the existing relational databases", openCypher + SQL, PostgreSQL 11–18 ([Apache AGE README](https://github.com/apache/age)) |
| **Kùzu** | embedded property graph, columnar on disk | reified node | "Columnar disk-based storage", "Columnar sparse row-based (CSR) adjacency list/join indices", Cypher; v0.11.3 released 2025-10-10 ([Kùzu README](https://github.com/kuzudb/kuzu)) |
| **SurrealDB** | multi-model records with graph relations | `RELATE` record, which is itself a record with fields | the `RELATE` edge record is a first-class row, so adding a third participant is adding a field — closer to a relation instance than to a graph edge ([SurrealDB graph docs](https://surrealdb.com/docs/surrealdb/models/graph)) |
| **TerminusDB** | JSON/JSON-LD documents in a succinct, immutable, git-like store | JSON-LD relation-instance documents | "a distributed database with a collaboration model — git for data"; commits, diff/patch, push/pull/clone, time-travel queries, WOQL datalog. Version 12 as of the May 2026 README ([TerminusDB README](https://github.com/terminusdb/terminusdb)) |
| **Datomic** | immutable EAV(T) datoms | one entity per fact, attributes as roles | the datom model makes a "fact entity" idiomatic rather than a workaround; see [relational-and-eav-storage.md](relational-and-eav-storage.md) |
| **RelationalAI** | relational knowledge graph over arbitrary-arity relations | **native**: a relation of arity n | a Datalog-family system where n-ary relations are the primitive, not an encoding ([RelationalAI docs](https://docs.relational.ai/)) |
| **AllegroGraph** | RDF quads plus per-triple attributes | RDF reification / relation instance, plus *triple attributes* | attributes are "name/value pairs that can be associated with triples or users", fixed at insert time, serialised in an extended N-Quads format (NQX) with a JSON object per line; RDF-star is implemented internally with a reserved `__quoted__` attribute. AllegroGraph 9.0.3, documentation last updated 20 August 2026 ([Triple Attributes](https://franz.com/agraph/support/documentation/current/triple-attributes.html)) |
| **AnzoGraph** | MPP RDF/SPARQL store with property-graph features | RDF reification / relation instance | positioned as an analytics graph warehouse; native hyperedge support: **[unverified]** |
| **GraphDB / Stardog / Oxigraph / Jena** | RDF | reification, RDF-star, or relation instance | see [rdf-star-and-semantic-web-serialisations.md](rdf-star-and-semantic-web-serialisations.md) for the per-store syntax table |

## 6. Property table

"Native arity" = a single stored record names more than two entities. "Roles" = the record says
what each member is. "Nesting" = a record may be a member of a record.

| System | Native arity | Roles | Nesting | Schema | Query language | Persistence | Status |
|---|---|---|---|---|---|---|---|
| HyperGraphDB | yes (tuple target set) | positional only | **yes** | dynamic type system | HGDB query API, no declarative language | key-value (BerkeleyDB) | 2010 paper; current release **[unverified]** |
| AtomSpace | yes (s-expression links) | positional | **yes** | Atom types | Atomese pattern engine | in-RAM + `atomspace-rocks` | active |
| Hyperon / MeTTa | yes | positional | yes | MeTTa types | MeTTa | Space backends | active, experimental |
| Hypergraph-DB | yes (vertex tuples) | no (property dicts) | no | none | Python API | `.hgdb` pickle, HIF export | 0.3.0, 2025-10-14 |
| TypeDB | yes (relation + roles) | **yes, typed** | yes (relations play roles) | strong | TypeQL | own engine | active |
| RelationalAI | yes (n-ary relations) | by position/column | via relations over relations | typed | Rel (Datalog family) | cloud service | active |
| Datomic | per-entity, not per-record | attribute names | via entity refs | attribute schema | Datalog | immutable log + indexes | active |
| TerminusDB | via JSON-LD documents | property names | nested documents | schema documents | WOQL, GraphQL | succinct immutable layers | v12, 2026 |
| Neo4j / Kùzu / AGE / ArangoDB / TigerGraph / SurrealDB | no | via edge types | no | varies | Cypher / GSQL / AQL / SurrealQL | varies | active |
| RDF stores | no | via role properties | RDF 1.2 triple terms only | RDFS/OWL/SHACL | SPARQL | varies | see the RDF note |

## 7. Research prototypes, 2023–2026

- **HGQL: Supporting Schematic Hypergraphs in GraphQL** — Aruna Bansal, IDEAS '23, pp. 9–16, 5 May 2023, [10.1145/3589462.3589481](https://doi.org/10.1145/3589462.3589481). Puts a schematic hypergraph model behind a GraphQL interface.
- **Compressing Hypergraphs using Suffix Sorting** — Adler, Böttcher and Hartel, [arXiv:2506.05023](https://arxiv.org/abs/2506.05023), 5 June 2025. HyperCSA, a *succinct self-index*: "compression ratios of 26% to 79% of the original file size on real-world hypergraphs" while still answering neighbour queries, "6 to 40 times faster than both standard data structures and other hypergraph compression approaches". The closest thing to a purpose-built on-disk hypergraph index in recent literature.
- **HyDRA: Lossless Hypergraph Summarization via Co-Clustering** — Preti, Anagnostopoulos and Bonchi, [arXiv:2606.18274](https://arxiv.org/abs/2606.18274), 5 June 2026. "the first formal framework for lossless summarization of weighted hypergraphs": supernodes and superhyperedges plus a correction table, "a substantial reduction in storage cost (80–93% in some settings)", and — the storage-relevant part — "the resulting summaries are themselves hypergraphs, they can be queried directly".
- **Labeled Incidence Structures for Native Transformer Modeling of Text, Knowledge Graphs and Hypergraphs** — [arXiv:2609.20278](https://arxiv.org/abs/2609.20278), 29 July 2026. Treats the labelled incidence structure as the common substrate; relevant to whether the incidence table is also the right *model* input.
- **Hyper-RAG** — Feng et al., *Nature Communications* 17, 27 April 2026, [10.1038/s41467-026-71411-1](https://doi.org/10.1038/s41467-026-71411-1) — notable here because it is a peer-reviewed system that chose a native hypergraph store (Hypergraph-DB) over a property graph.

What is *missing* from the 2023–2026 literature, as far as this pass found: a distributed,
transactional, native hypergraph database with a declarative query language. HyperCSA is an index,
HyDRA is a summary, Hypergraph-DB is a single-process library, AtomSpace is in-RAM, HyperGraphDB is
embedded. Recorded as an open question.

## 8. Choosing

Short version, expanded in [format-recommendations.md](format-recommendations.md):

- Need typed roles and schema enforcement -> **TypeDB**.
- Need nesting and symbolic rewriting -> **AtomSpace / MeTTa**, accepting isolation.
- Need a small embedded native hypergraph with HIF export -> **Hypergraph-DB**.
- Need existing ops, tooling and hiring -> a property graph or PostgreSQL with the reified-node
  pattern, and accept the query cost.
- Need per-fact provenance in a standard -> RDF 1.2 in Jena or Oxigraph.

## Sources

- Iordanov, B. (2010). *HyperGraphDB: A Generalized Graph Database*. LNCS 6185, pp. 25–36. https://doi.org/10.1007/978-3-642-16720-1_3 — full text: https://hypergraphdb.org/docs/hypergraphdb.pdf
- HyperGraphDB repository. https://github.com/hypergraphdb/hypergraphdb
- TypeDB. *Entities, relations, attributes* and TypeQL reference (checked 2026-09-20). https://typedb.com/docs/core-concepts/typeql/entities-relations-attributes/
- OpenCog AtomSpace README (checked 2026-09-20). https://github.com/opencog/atomspace
- `atomspace-rocks` (RocksDB persistence) and `atomspace-cog` (distributed storage). https://github.com/opencog/atomspace-rocks , https://github.com/opencog/atomspace-cog
- TrueAGI. *hyperon-experimental* README, MeTTa (checked 2026-09-20). https://github.com/trueagi-io/hyperon-experimental
- Hypergraph-DB README and PyPI metadata (0.3.0, uploaded 2025-10-14). https://github.com/iMoonLab/Hypergraph-DB , https://pypi.org/project/hypergraph-db/
- Apache AGE README (checked 2026-09-20). https://github.com/apache/age
- Kùzu README (v0.11.3, released 2025-10-10). https://github.com/kuzudb/kuzu
- TerminusDB README, "Project Overview (Updated May 2026)" and version 12 notes. https://github.com/terminusdb/terminusdb
- ArangoDB graphs documentation (checked 2026-09-20). https://docs.arangodb.com/stable/graphs/
- TigerGraph. *Defining a graph schema* (GSQL reference, checked 2026-09-20). https://docs.tigergraph.com/gsql-ref/current/ddl-and-loading/defining-a-graph-schema
- SurrealDB. *Graph model* documentation (checked 2026-09-20). https://surrealdb.com/docs/surrealdb/models/graph
- RelationalAI documentation (checked 2026-09-20). https://docs.relational.ai/
- Franz Inc. *Triple Attributes*, AllegroGraph 9.0.3 documentation, last updated 20 August 2026. https://franz.com/agraph/support/documentation/current/triple-attributes.html
- Bansal, A. (2023). *HGQL: Supporting Schematic Hypergraphs in GraphQL*. IDEAS '23, pp. 9–16. https://doi.org/10.1145/3589462.3589481
- Adler, E., Böttcher, S. and Hartel, R. (2025). *Compressing Hypergraphs using Suffix Sorting*. https://arxiv.org/abs/2506.05023
- Preti, G., Anagnostopoulos, A. and Bonchi, F. (2026). *HyDRA: Lossless Hypergraph Summarization via Co-Clustering*. https://arxiv.org/abs/2606.18274
- *Labeled Incidence Structures for Native Transformer Modeling of Text, Knowledge Graphs, and Hypergraphs* (2026). https://arxiv.org/abs/2609.20278
- Feng, Y., Hu, H., Ying, S., Hou, X., Liu, S., Yang, M., Li, J., Du, S., Zheng, N., Hu, H. and Gao, Y. (2026). *Hyper-RAG: combating LLM hallucinations using hypergraph-driven retrieval-augmented generation*. Nature Communications 17, 27 April 2026. https://doi.org/10.1038/s41467-026-71411-1
