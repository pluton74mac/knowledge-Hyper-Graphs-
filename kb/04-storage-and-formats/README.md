---
title: Section 04 — Storage and formats
type: index
status: draft
tags: [storage, formats, serialisation, databases, index]
created: 2026-09-20
updated: 2026-09-20
---

# 04 — Storage and formats

**The question this section answers: how is a knowledge hypergraph actually stored?** File types and
serialisations, databases, relational and tensor layouts, the hybrid stacks that retrieval systems
use, and what to pick.

The short version: there is one credible interchange format (HIF), no credible distributed native
hypergraph database, and every widely deployed system stores hyperedges by emulating them. The
recommendation this section arrives at is to keep an incidence table as the system of record and
treat HIF, Parquet, RDF, graph projections and vector indexes as derived, rebuildable views.

## Notes

| Note | What it covers |
|---|---|
| [file-formats-overview.md](file-formats-overview.md) | Comparison table of every format that can carry a hypergraph or n-ary fact: HIF, library JSONs, `.hgr`, Matrix Market, RDF 1.2 family, JSON-LD, TypeQL, GraphML, GEXF, GML, DOT, CX2, GraphSON, PG, Parquet, HDF5 — with extension, hyperedge support, direction, attributes, nesting, tooling and spec link. Plus the status of the standards landscape. |
| [hif-hypergraph-interchange-format.md](hif-hypergraph-interchange-format.md) | Deep dive on HIF: structure, the draft-07 JSON Schema, versions, a full worked knowledge-hypergraph example, validation, which libraries read and write it, and what it deliberately does not do. |
| [rdf-star-and-semantic-web-serialisations.md](rdf-star-and-semantic-web-serialisations.md) | RDF 1.2 / RDF-star syntax with four encodings of the same n-ary fact, named graphs, JSON-LD, SPARQL 1.2, and a dated support table for Jena, Oxigraph, GraphDB, Stardog, RDF4J, QLever and Blazegraph. |
| [hypergraph-databases.md](hypergraph-databases.md) | HyperGraphDB's storage design in detail, TypeDB's role-typed relations, AtomSpace/Hyperon, Hypergraph-DB, and a property table covering the emulating stores (Neo4j, Kùzu, AGE, ArangoDB, TigerGraph, SurrealDB, TerminusDB, Datomic, AllegroGraph, RelationalAI) plus 2023–2026 research prototypes. |
| [property-graph-emulation-patterns.md](property-graph-emulation-patterns.md) | The four emulation patterns, their query costs in Cypher and Gremlin, and what HyperGraphRAG, Hyper-RAG and LightRAG *actually* store, read from their source. |
| [relational-and-eav-storage.md](relational-and-eav-storage.md) | Wide n-ary tables, incidence tables, EAV, JSONB; Datomic; Datalog engines (Soufflé, LogicBlox, RelationalAI) and worst-case-optimal joins; SQL/PGQ and GQL; Parquet layouts. |
| [tensor-and-sparse-representations.md](tensor-and-sparse-representations.md) | Incidence matrices and their derived operators, why adjacency tensors do not scale, COO/CSR/CSC, PyTorch Geometric's `hyperedge_index`, DHG's internals, and scalability arithmetic. |
| [vector-stores-and-hybrid-storage-for-rag.md](vector-stores-and-hybrid-storage-for-rag.md) | The KV + vector + graph split: exact on-disk file layouts for HyperGraphRAG, Hyper-RAG and LightRAG, what the split costs, and what a better hybrid layout looks like. |
| [versioning-provenance-and-scale.md](versioning-provenance-and-scale.md) | PROV-O and nanopublications, four versioning mechanisms, reference scale numbers (Wikidata, Freebase), compression and summarisation results, and sharding by hypergraph partitioning. |
| [format-recommendations.md](format-recommendations.md) | The decision guide: what to use for interchange, storage, analysis, querying and ML; rules for the data model; anti-patterns; a decision tree; and where this guidance is weak. |

## Sample files

- [`schemas/sample.hif.json`](../../schemas/sample.hif.json) — three n-ary biomedical facts as
  directed, role-labelled hyperedges in HIF. Validated against the published HIF schema with
  `jsonschema` 4.26.0 on 2026-09-20: 0 errors.
- [`schemas/sample-n-ary-fact.ttl`](../../schemas/sample-n-ary-fact.ttl) — the same fact written
  three ways in RDF 1.2 Turtle (annotation syntax, explicit reifier with a triple term, and the
  classic relation-instance pattern). Parsed with pyoxigraph 0.5.11 on 2026-09-20: 32 quads, no
  errors.

## Reading order

1. [file-formats-overview.md](file-formats-overview.md) for the map.
2. [hif-hypergraph-interchange-format.md](hif-hypergraph-interchange-format.md) and
   [rdf-star-and-semantic-web-serialisations.md](rdf-star-and-semantic-web-serialisations.md) for
   the two standards that matter.
3. [property-graph-emulation-patterns.md](property-graph-emulation-patterns.md) for what real
   systems do, which is the most surprising note in the section.
4. [format-recommendations.md](format-recommendations.md) for what to do about it.

## Related sections

- [../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md)
  — the modelling argument behind every encoding here.
- [../02-knowledge-representation/wikidata-and-freebase-data-models.md](../02-knowledge-representation/wikidata-and-freebase-data-models.md)
  — the largest deployed n-ary data models.
- [../03-construction/](../03-construction/) — where the facts come from before they are stored.
- [../01-foundations/hypergraph-definitions.md](../01-foundations/hypergraph-definitions.md) — the
  mathematics the incidence matrix implements.

## Bibliography

All sources cited by this section are collected in
[`sources/by-topic/04-storage-and-formats.md`](../../sources/by-topic/04-storage-and-formats.md).
