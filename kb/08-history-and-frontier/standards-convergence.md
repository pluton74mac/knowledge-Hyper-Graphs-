---
title: Standards — RDF 1.2, SPARQL 1.2, GQL, SQL/PGQ, HIF, PG-Schema, and where they fail to meet
type: survey
status: draft
tags: [standards, rdf, sparql, gql, sql-pgq, hif, pg-schema, n-ary, interchange, w3c, iso]
created: 2026-09-20
updated: 2026-09-20
---

# Standards convergence — and non-convergence — on n-ary knowledge

Status date for everything below: **2026-09-20**. Standards move; re-check the stage of any W3C or
ISO document before relying on it.

Four standards bodies and one grass-roots community are, at this moment, each shipping a data model
that touches n-ary knowledge. They are **not** converging on a single model. This note states what
each one actually offers, and where the gaps are.

| Track | Body | Current state (2026-09-20) | Does it express an n-ary fact natively? |
|---|---|---|---|
| RDF 1.2 / SPARQL 1.2 | W3C RDF & SPARQL WG | Concepts + Semantics at **Candidate Recommendation**, 7 Apr 2026; syntaxes and SPARQL 1.2 Query still Working Drafts | **No.** Triple terms annotate a *triple*; n-ary still needs the 2006 reification patterns |
| GQL | ISO/IEC JTC1 SC32 | **ISO/IEC 39075:2024**, published 12 Apr 2024; second edition under way (AWI) | **No.** Property graphs explicitly exclude n-ary relationships |
| SQL/PGQ | ISO/IEC JTC1 SC32 | **ISO/IEC 9075-16:2023**, part of SQL:2023 | **No** for the graph view; **yes** for the underlying tables |
| HIF | community (hypergraph library maintainers) | v1 schema; paper in *Network Science* 13:e21, 2025 | **Yes** for structure; **no** for relation semantics |
| PG-Schema | LDBC / academic | SIGMOD 2023 proposal, input to a future GQL edition | Schema language, not a data model change |

## 1. RDF 1.2 and SPARQL 1.2 — annotation, not arity

### What shipped

The W3C RDF & SPARQL Working Group (successor to the 2022 RDF-star WG charter;
[2022 charter](https://www.w3.org/2022/08/rdf-star-wg-charter/),
[2025 charter](https://www.w3.org/2025/04/rdf-star-wg-charter.html)) published **RDF 1.2 Concepts and
Abstract Data Model** and **RDF 1.2 Semantics** as **Candidate Recommendation Snapshots dated
7 April 2026**, with W3C issuing a call for implementations
([W3C news](https://www.w3.org/news/2026/w3c-invites-implementations-of-rdf-1-2-concepts-and-abstract-data-model-and-rdf-1-2-semantics)).
Editors of Concepts: Olaf Hartig, Pierre-Antoine Champin, Andy Seaborne (Gregg Kellogg until
2025-09-06, in memoriam) ([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)).

The rest of the suite is **still Working Drafts** as of the Working Group publications page checked
on 2026-09-20 ([WG publications](https://www.w3.org/groups/wg/rdf-star/publications/)):

| Document | Stage | Dated |
|---|---|---|
| RDF 1.2 Concepts and Abstract Data Model | Candidate Recommendation Snapshot | 7 Apr 2026 |
| RDF 1.2 Semantics | Candidate Recommendation Snapshot | 7 Apr 2026 |
| RDF 1.2 Schema | Working Draft | 28 Mar 2026 |
| RDF 1.2 N-Triples / N-Quads | Working Draft | 23 Jul 2026 |
| RDF 1.2 Turtle | Working Draft | 14 Sep 2026 |
| RDF 1.2 XML Syntax | Working Draft | 14 Sep 2026 |
| RDF 1.2 TriG | Working Draft | 15 Sep 2026 |
| SPARQL 1.2 Query Language | Working Draft | 13 Sep 2026 |
| RDF 1.2 Primer | Draft Note | 17 Sep 2026 |
| What's New in RDF 1.2 / in SPARQL 1.2 | Draft Notes | 14 Jul 2026 |

So: the *model* is near-final, the *serialisations and the query language are not*. A KHG project
that needs a stable RDF 1.2 Turtle parser or SPARQL 1.2 endpoint in 2026 is building on a moving
target.

### What the model gives you

RDF 1.2 adds **triple terms** and **reifiers**:

> "An RDF triple used as the object of another triple is called a triple term."
> "A reifying triple is a triple where the predicate is `rdf:reifies` and the object is a triple
> term." Its subject, the *reifier*, "denotes a variety of things that are related to the triple
> term's proposition, such as a statement or belief that the proposition holds."
> ([RDF 1.2 Concepts, CR Snapshot, 7 Apr 2026](https://www.w3.org/TR/rdf12-concepts/))

This is a clean standard answer to *annotating a statement* — provenance, certainty, temporal
validity, the Wikidata qualifier pattern. It is **not** an answer to n-ary relations, and the
specification says so: it states that relations involving more than two entities "can only be
indirectly expressed in RDF" and points the reader at the 2006 Working Group Note
([Noy & Rector, 12 Apr 2006](https://www.w3.org/TR/swbp-n-aryRelations/)).

**Consequence for KHGs.** RDF 1.2 covers the *hyper-relational* reading (triple + qualifiers) but
not the *symmetric n-ary tuple* reading. For the latter you are still doing Pattern 1 of the 2006
note — a mediating node per fact — with all the costs catalogued in
[knowledge-representation-lineage.md](knowledge-representation-lineage.md) and
[../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md).

The community precursor, the **RDF-star and SPARQL-star Final Community Group Report** of
17 Dec 2021 ([CG report](https://w3c-cg.github.io/rdf-star/cg-spec/2021-12-17.html)), used *quoted
triples*; RDF 1.2 deliberately changed the design to triple terms plus explicit reifiers. Code and
data written against the 2021 CG semantics are not automatically RDF 1.2 conformant.

## 2. GQL (ISO/IEC 39075:2024) — the first ISO graph language, and binary by definition

The GQL project was approved by ISO/IEC JTC 1 in **September 2019**; **ISO/IEC 39075:2024,
*Information technology — Database languages — GQL*, was published 12 April 2024**
([ISO catalogue entry](https://www.iso.org/standard/76120.html);
[Wikipedia, Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language)). It is the
first new ISO database language since SQL.

Its data model is the property graph: nodes and edges with labels and properties, multigraphs
allowed, mixed directed/undirected allowed. And, as the standard's own model description puts it,
the property graph "does not include n-ary relationships linking more than two entities" (as
reported in the Wikipedia summary of the specification, checked 2026-09-20).

That is the crux of the non-convergence: **the world's first standard graph query language
standardised the binary edge, in 2024, at precisely the moment the research field was moving to
hyperedges.**

Work continues: ISO lists a technical corrigendum and a second-edition work item
([ISO/IEC AWI 39075](https://www.iso.org/standard/89917.html)), and the LDBC "Extended GQL Schema"
(LEX) working group is feeding a richer DDL into a future edition. Whether any of that touches arity
is unknown; no source checked in this run says it does `[unverified]`.

## 3. SQL/PGQ (ISO/IEC 9075-16:2023) — property graph views over n-ary tables

SQL:2023, adopted June 2023, added **Part 16: Property Graph Queries (SQL/PGQ)**, ISO/IEC
9075-16:2023 ([ISO catalogue entry](https://www.iso.org/standard/79473.html), not retrievable
directly in this run — `[unverified]` for the abstract text;
[Wikipedia, SQL:2023](https://en.wikipedia.org/wiki/SQL:2023)). It lets you define a *property graph
view* over existing relational tables and pattern-match on it.

The interesting asymmetry for this knowledge base:

- The **base tables are n-ary already** — that is the relational model, and Fagin's hypergraph view
  of it ([origins-hypergraph-theory.md](origins-hypergraph-theory.md)).
- The **graph view is binary**, because it is a property graph.

So SQL/PGQ is a standardised *flattening*: it projects an n-ary store into a binary query surface.
Practically this is the most deployable route to "hypergraph-ish" querying today — keep facts as
rows, expose a graph view for traversal — and it is why a plain relational database remains a
credible competitor to any KHG store. See [../04-storage-and-formats/relational-and-eav-storage.md](../04-storage-and-formats/relational-and-eav-storage.md).

## 4. HIF — the one standard that is natively higher-order

**HIF, the Hypergraph Interchange Format**, is the exception: a format designed by the maintainers
of the hypergraph libraries themselves, for hypergraphs, with no property-graph legacy.

> Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B.,
> Szufel, P. "HIF: The hypergraph interchange format for higher-order networks." *Network Science*
> **13:e21** (2025), online 11 Dec 2025
> ([DOI 10.1017/nws.2025.10018](https://doi.org/10.1017/nws.2025.10018);
> [arXiv:2507.11520](https://arxiv.org/abs/2507.11520), 15 Jul 2025, revised 30 Jan 2026)

Properties, from the paper and the reference repository
([HIF-standard](https://github.com/HIF-org/HIF-standard); earlier home
[pszufe/HIF-standard](https://github.com/pszufe/HIF-standard)):

- JSON, with a published JSON Schema, unit tests, example datasets and tutorials.
- Supports **undirected hypergraphs, directed hypergraphs, and abstract simplicial complexes**.
- The only required field is **`incidences`** — HIF is incidence-centric, not edge-centric, which is
  the right choice for a format that must round-trip between libraries with different internal
  models. Isolated nodes and empty edges are representable.
- Direction is carried *per incidence* (`"direction"` keyword), not per edge.
- Metadata is allowed at network, node, edge and **incidence** level. Incidence-level metadata is
  what lets you attach a **role** to a participant — the nearest thing in any standard to a
  role-labelled hyperedge.
- Tooling represented: **HypergraphX, HyperNetX, HAT (Python), SimpleHypergraphs.jl, XGI**.

**What HIF does not do.** It is a *structural* interchange format. It has no notion of a relation
type with a signature, no schema language, no entity identity/IRI discipline, no query language, no
semantics for inference, and no provenance model. It will faithfully move a knowledge hypergraph's
*shape* between tools; the meaning has to travel in metadata conventions you invent yourself. A
sample file is in `schemas/sample.hif.json`; the format is treated in detail in
[../04-storage-and-formats/hif-hypergraph-interchange-format.md](../04-storage-and-formats/hif-hypergraph-interchange-format.md).

## 5. PG-Schema — schemas for the binary world

Angles, Bonifati, Dumbrava, Fletcher, Green, Hidders, Li, Libkin, Marsault, Martens, Murlak,
Plantikow et al., "PG-Schema: Schemas for Property Graphs," *Proceedings of the ACM on Management of
Data* 1(2), 13 Jun 2023 ([DOI 10.1145/3589778](https://doi.org/10.1145/3589778);
[arXiv:2211.10962](https://arxiv.org/abs/2211.10962)). Flexible type definitions with
multi-inheritance, plus constraints built on PG-Keys. Explicitly aimed at inspiring GQL's DDL, and
carried forward by the LDBC LEX working group; schema support in the first GQL edition is limited
and a richer DDL is anticipated for the second.

Relevance here is negative but important: it shows the property-graph community investing heavily in
*schema* while leaving *arity* alone. If you need typed roles with cardinality constraints on an
n-ary fact today, the schema languages that give you that are the relational one (SQL DDL) and
TypeDB's, not the graph standards.

## 6. Where the tracks actually meet, and where they do not

**They meet on annotation.** RDF 1.2 reifiers, Wikidata qualifiers, property-graph edge properties
and HIF incidence metadata are all ways of saying "this assertion has extra attributes." This is a
real convergence, and it covers the *hyper-relational* reading of a KHG.

**They do not meet on arity.** No standard in the table above lets you declare a relation of arity 4
with named roles as a first-class thing and query it as such. The three partial answers are:

1. **Reify** (RDF 1.2 + 2006 note patterns): portable, standard, verbose, and it destroys the
   one-fact-one-object correspondence.
2. **Stay relational** (SQL, optionally with a SQL/PGQ view): natively n-ary, fully standardised,
   mature tooling — but no open-world semantics, no IRI-based identity, no graph-native traversal
   over the n-ary structure itself.
3. **Leave the standards** (HIF for interchange; TypeDB, HypergraphDB, or a bespoke store for
   operation): native arity and roles, no standard query language, no interoperability guarantee.

**The missing standard** is a serialisation *and* query language for typed, role-labelled, directed
hyperedges with entity identity — something like "HIF plus a schema plus a query algebra," or
"GQL with n-ary relationships." Nothing in the 2026 pipeline supplies it. This is registered as a
frontier direction in [current-frontier-directions.md](current-frontier-directions.md).

## 7. Practical guidance (opinion, 2026-09)

- If your facts are **triple + qualifiers** and you need interoperability: RDF 1.2's reifier design
  is where the ecosystem is going. Expect churn until the syntax drafts stabilise.
- If your facts are **symmetric n-ary tuples** and you need them to work today: keep them in
  relational tables, export HIF for anything graph-analytic, and do not try to make a triple store
  the system of record.
- If you need **roles with a type system**: TypeDB is the closest production system; see
  [research-groups-and-people.md](research-groups-and-people.md) and
  [../04-storage-and-formats/hypergraph-databases.md](../04-storage-and-formats/hypergraph-databases.md).
- Do not assume any two tools that say "hypergraph" can exchange data. Check HIF support first.

## Sources

- W3C. "RDF 1.2 Concepts and Abstract Data Model." Candidate Recommendation Snapshot, 7 April 2026. Eds. O. Hartig, P.-A. Champin, A. Seaborne. https://www.w3.org/TR/rdf12-concepts/
- W3C. "RDF 1.2 Semantics." Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-semantics/
- W3C RDF & SPARQL Working Group. Publications list (checked 2026-09-20). https://www.w3.org/groups/wg/rdf-star/publications/
- W3C. "W3C Invites Implementations of RDF 1.2 Concepts and Abstract Data Model and RDF 1.2 Semantics." News, 2026. https://www.w3.org/news/2026/w3c-invites-implementations-of-rdf-1-2-concepts-and-abstract-data-model-and-rdf-1-2-semantics
- W3C. "SPARQL 1.2 Query Language." Working Draft, 13 September 2026. https://www.w3.org/TR/sparql12-query/
- W3C. RDF-star Working Group Charter, 2022. https://www.w3.org/2022/08/rdf-star-wg-charter/ ; RDF & SPARQL Working Group Charter, 2025. https://www.w3.org/2025/04/rdf-star-wg-charter.html
- Hartig, O., Champin, P.-A., Kellogg, G., Seaborne, A. (eds.). "RDF-star and SPARQL-star." W3C Final Community Group Report, 17 December 2021. https://w3c-cg.github.io/rdf-star/cg-spec/2021-12-17.html
- Noy, N., Rector, A. (eds.). "Defining N-ary Relations on the Semantic Web." W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- ISO/IEC 39075:2024, *Information technology — Database languages — GQL*, published 12 April 2024. https://www.iso.org/standard/76120.html ; second-edition work item ISO/IEC AWI 39075. https://www.iso.org/standard/89917.html
- Wikipedia. "Graph Query Language" (checked 2026-09-20). https://en.wikipedia.org/wiki/Graph_Query_Language
- ISO/IEC 9075-16:2023, *Information technology — Database languages SQL — Part 16: Property Graph Queries (SQL/PGQ)*. https://www.iso.org/standard/79473.html
- Wikipedia. "SQL:2023." https://en.wikipedia.org/wiki/SQL:2023
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. "HIF: The hypergraph interchange format for higher-order networks." *Network Science* 13:e21, 2025. https://doi.org/10.1017/nws.2025.10018 ; https://arxiv.org/abs/2507.11520
- HIF reference repository. https://github.com/HIF-org/HIF-standard ; https://github.com/pszufe/HIF-standard
- Angles, R., Bonifati, A., Dumbrava, S., Fletcher, G., Green, A., Hidders, J., Li, B., Libkin, L., Marsault, V., Martens, W., Murlak, F., Plantikow, S. et al. "PG-Schema: Schemas for Property Graphs." *Proc. ACM Manag. Data* 1(2), 2023. https://doi.org/10.1145/3589778 ; https://arxiv.org/abs/2211.10962
