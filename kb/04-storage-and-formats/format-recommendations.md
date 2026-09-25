---
title: Format and storage recommendations for this project
type: howto
status: draft
tags: [recommendation, decision-guide, hif, incidence-table, parquet, rdf, storage-architecture]
created: 2026-09-20
updated: 2026-09-25
---

# Format and storage recommendations

The decision guide for anything built in `projects/`. Everything here is a judgement drawn from the
evidence in the rest of this section; where a recommendation is contested the note says so.
Checked 2026-09-20.

## 1. The short answer

| Purpose | Choice | Why |
|---|---|---|
| **Interchange** — hand a hypergraph to another tool or person | **HIF JSON** | The only cross-library standard with a published schema and multiple independent implementations ([hif-hypergraph-interchange-format.md](hif-hypergraph-interchange-format.md)) |
| **System of record** — the thing that is backed up | **Incidence tables in PostgreSQL** (`fact`, `incidence`, `entity`) | Unbounded arity, roles as a first-class column, no migrations for new relation types, one engine ([relational-and-eav-storage.md](relational-and-eav-storage.md)) |
| **Analysis** — degree distributions, spectra, community detection | **Parquet copy of the incidence table -> SciPy CSR/CSC** | Dictionary encoding, predicate pushdown, direct conversion to **H** ([tensor-and-sparse-representations.md](tensor-and-sparse-representations.md)) |
| **Querying** — pattern matching and traversal | **SQL over the incidence table**, with SQL/PGQ for fixed-length patterns or a materialised reified-node projection when graph patterns are needed | Avoids the Cypher-layer overhead; the reified-node projection is rebuildable ([property-graph-emulation-patterns.md](property-graph-emulation-patterns.md)); SQL/PGQ as implemented today stops at fixed-length patterns (below) |
| **ML** | **`hyperedge_index` derived from the incidence table** | It *is* two columns of the incidence table; no separate ML format is needed |
| **Standards interop / publication** | **RDF 1.2 relation-instance pattern**, exported not stored | Works in every RDF store, no dialect risk, round-trips to HIF ([rdf-star-and-semantic-web-serialisations.md](rdf-star-and-semantic-web-serialisations.md)) |
| **Prototype, single machine, < ~10^6 hyperedges** | **Hypergraph-DB** with `save_as_hif` for checkpoints | Native arity, HIF export, no server ([hypergraph-databases.md](hypergraph-databases.md)) |
| **Typed roles with schema enforcement** | **TypeDB** | The only mainstream engine whose schema language has n-ary relations with typed roles |

**SQL/PGQ over the incidence table, as available today** (corrected 2026-09-25). DuckPGQ, the community extension
for DuckDB 1.5.4, accepted `CREATE PROPERTY GRAPH` over the incidence tables. Its `GRAPH_TABLE` answered the
fixed-length patterns: `incident`, a two-pattern `find` and one level of a supersession walk. It refused a
variable-length path over the bipartite layout (`ANY SHORTEST … {1,8}`: "Non-existent/non-unique vertices
detected"), because path-finding needs edges within one vertex table and the layout's edges run from version to
node. It had no build for DuckDB 1.5.5 (HTTP 404) ([P1 research 01](../../projects/p1-store-bakeoff/research/01-backends.md) §4.3, probe
`duckpgq_probe.py`). A recursive CTE or a native graph engine still does the traversal.

## 2. The one architectural decision that matters

**Keep one system of record and treat everything else as a derived, rebuildable index.**

```
                  incidence tables  (fact / incidence / entity)   <- writes go here only
                          |
      +-------------------+-------------------+-----------------+
      v                   v                   v                 v
  HIF export        Parquet export      graph projection     vector index
 (interchange)      (analysis, ML)     (traversal queries)   (retrieval)
```

Every system surveyed in this section that got into trouble got into it by having two or more
places that could be written independently — a graph file and a vector file with no transaction
between them
([vector-stores-and-hybrid-storage-for-rag.md](vector-stores-and-hybrid-storage-for-rag.md)).

Corollaries:

- Derived stores must be **droppable and rebuildable** from the system of record. If rebuilding the
  vector index means re-running an LLM, the extraction outputs belong in the system of record too.
- Anything that cannot be rebuilt — the raw documents, the extraction outputs, the human
  corrections — is a system of record and needs the same care.

## 3. Rules for the data model

1. **Give every fact a stable opaque ID.** Not the sentence, not a hash of the sentence. Content
   hashes belong on the *extraction event*, not the fact
   ([versioning-provenance-and-scale.md](versioning-provenance-and-scale.md)).
2. **Always store the role.** A hyperedge without roles is a co-occurrence set; useful for network
   analysis, nearly useless for reasoning. Every KHG-labelled system this section examined —
   HyperGraphRAG, Hyper-RAG, LightRAG — drops roles. Do not copy that.
3. **Store `arity` on the fact.** Free, and it makes "how hyper is this hypergraph?" a query rather
   than a job.
4. **Store direction per incidence**, as HIF does, not as a property of the edge. A fact can have
   several heads.
5. **Use PROV-O terms for provenance attributes** rather than ad-hoc keys.
6. **Bitemporal columns by default** (`valid_from`/`valid_to`, `recorded_from`/`recorded_to`);
   promote time to a qualifier-member only when the domain demands it.
7. **Never materialise the clique expansion.**

## 4. What to write when exporting

For [`schemas/`](../../schemas/) and for anything published:

- **HIF** for the hypergraph itself. Put every project-specific convention in
  `metadata`, as [`schemas/sample.hif.json`](../../schemas/sample.hif.json) does — the standard has
  no role vocabulary, so a self-describing file is the best available substitute.
- **RDF 1.2 Turtle** for the semantic-web audience, using the relation-instance pattern as the
  primary form, as [`schemas/sample-n-ary-fact.ttl`](../../schemas/sample-n-ary-fact.ttl) does.
  Include the annotation-syntax and triple-term variants only as documentation of what is possible.
- **Parquet** for anything bigger than a demo.
- **`.hgr`** only as a throwaway input to a partitioner.

Always ship the validation command with the file. For HIF that is a draft-07 JSON Schema
validation against the published schema; for Turtle, a parse with an RDF 1.2-capable parser. Both
sample files in this repository were validated this way on 2026-09-20 (HIF: 0 schema errors;
Turtle: parsed to 32 quads with pyoxigraph 0.5.11).

## 5. What not to do

| Anti-pattern | Why | Where it shows up |
|---|---|---|
| Using the fact's text as its ID | unstable under paraphrase; deduplication becomes a string problem | HyperGraphRAG's `"<hyperedge>" + sentence` keys |
| Pickle as the persistence format for knowledge | not portable, not inspectable, not diffable, unsafe to load | Hyper-RAG's `.hgdb`, DHG's `.pkl`, HypergraphX's pickle mode |
| GraphML as a hypergraph store | the spec has `<hyperedge>` but the common reader raises on it | NetworkX-based pipelines |
| Storing in RDF-star 2021 CG syntax | superseded; RDF 1.2 moved triple terms to object position | anything written before ~2025 |
| One named graph per fact, at scale | graph-count explosion | naive nanopublication imitations |
| A single JSON/GraphML file rewritten on every flush | O(size) per commit | all three RAG systems' defaults |
| Choosing a store because a paper's title says "hypergraph" | says nothing about storage | see [property-graph-emulation-patterns.md](property-graph-emulation-patterns.md) section 3 |

## 6. Decision tree

```
Is the relation vocabulary closed and small?
├─ yes → wide n-ary tables, one per relation type. Fastest queries, needs migrations.
└─ no  → incidence tables.
         │
         Do you need typed roles enforced by the database?
         ├─ yes → TypeDB (accept the closed ecosystem), or CHECK constraints + SHACL-style validation
         └─ no  → PostgreSQL incidence tables
                  │
                  Do you need nesting (facts about facts as structure, not as a pointer)?
                  ├─ yes → RDF 1.2 triple terms (Jena 6.1+ / Oxigraph), or AtomSpace / HypergraphDB
                  └─ no  → stay relational
                           │
                           Is the working set > RAM on one machine?
                           ├─ no  → single Postgres; Hypergraph-DB for in-process analysis
                           └─ yes → shard with km1 hypergraph partitioning via .hgr export,
                                    and re-read versioning-provenance-and-scale.md section 3
```

## 7. Where this guidance is weak

- It recommends a relational system of record for a *hypergraph* project, which will feel wrong to
  anyone expecting a native hypergraph database. The reason is availability, not preference: no
  distributed, transactional, native hypergraph store with a declarative query language was found
  in this pass ([hypergraph-databases.md](hypergraph-databases.md), section 7).
- There is no benchmark comparing native hyperedge storage with reified-node emulation on the same
  knowledge hypergraph, so the query-cost argument in
  [property-graph-emulation-patterns.md](property-graph-emulation-patterns.md) is analytical plus
  one adjacent measurement, not a direct result.
- HIF has exactly one schema version and no version field; standardising on it carries a small
  forward-compatibility risk.

## Sources

This note is a synthesis of the other notes in this section; every factual claim it relies on is
cited there. The sources specific to the validation claims in section 4:

- HIF-standard `schemas/hif_schema.json` (JSON Schema draft-07), validated against [`schemas/sample.hif.json`](../../schemas/sample.hif.json) with Python `jsonschema` 4.26.0 on 2026-09-20: 0 errors. https://github.com/pszufe/HIF-standard
- pyoxigraph 0.5.11 (released 2026-09-02), used to parse [`schemas/sample-n-ary-fact.ttl`](../../schemas/sample-n-ary-fact.ttl) on 2026-09-20: 32 quads, no errors. https://pypi.org/project/pyoxigraph/
- W3C. *PROV-O: The PROV Ontology*, Recommendation 30 April 2013. https://www.w3.org/TR/prov-o/
- W3C. *RDF 1.2 Turtle*, Working Draft 14 September 2026. https://www.w3.org/TR/rdf12-turtle/
- P1 research 01, §4.3 and the probe `duckpgq_probe.py` (run 2026-09-25): DuckPGQ (community extension, DuckDB 1.5.4) over the incidence tables. [P1 research 01](../../projects/p1-store-bakeoff/research/01-backends.md)
