---
title: Versioning, provenance and scale in hypergraph storage
type: survey
status: draft
tags: [provenance, prov-o, nanopublication, versioning, bitemporal, sharding, partitioning, scale, wikidata]
created: 2026-09-20
updated: 2026-09-20
---

# Versioning, provenance and scale

Three storage problems that only appear once a knowledge hypergraph is real: how to say where a
fact came from, how to keep its history, and what to do when it no longer fits on one machine.
The hyperedge helps with the first two and makes the third harder.

Checked 2026-09-20.

## 1. Provenance: the hyperedge is the natural anchor

In a binary knowledge graph, "where did this fact come from?" has no place to live — an edge is not
an object. That is the whole reason reification exists
([../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md)).
In a hypergraph the hyperedge *is* an object with an ID, so provenance is just more attributes on
it. In HIF, `edges[i].attrs`; in the SQL incidence model, columns on the `fact` table; in RDF 1.2,
properties of the reifier.

### PROV-O

The W3C provenance ontology, a **Recommendation of 30 April 2013**
([PROV-O](https://www.w3.org/TR/prov-o/)). Three starting-point classes — `prov:Entity`,
`prov:Activity`, `prov:Agent` — and the relations between them (`prov:wasDerivedFrom`,
`prov:wasGeneratedBy`, `prov:wasAttributedTo`, and so on).

Its **Qualified Terms** are the part that matters here. PROV-O says: "Qualified classes and
properties provide elaborated information about binary relations asserted using Starting Point and
Expanded properties. ... While the relations from the previous two categories are applied as
direct, binary assertions, the terms in this category are used to provide additional attributes of
the binary relations." `prov:qualifiedDerivation`, `prov:qualifiedGeneration`,
`prov:qualifiedAttribution` and friends are therefore **reified hyperedges by another name** — the
n-ary pattern, standardised, in the one W3C vocabulary everyone already imports.

For a KHG: use PROV-O terms as the attribute vocabulary on hyperedges rather than inventing
`source` / `extracted_by` / `confidence` keys. It costs nothing and makes the provenance layer
interoperable even when the fact layer is not.

### Nanopublications

The maximal version of the same idea: every assertion is published as its own citable unit. "A
nanopublication is a small knowledge graph snippet with metadata that is treated as an independent
(scientific) publication", with "three basic elements: **Assertion** ... the main content ... in
the form of an small atomic unit of information; **Provenance** ... how the assertion above came to
be; **Publication Info** ... metadata about the nanopublication as a whole, such as when and by
whom it was created and the license terms" ([nanopub.net](https://nanopub.net/), checked
2026-09-20). They are "implemented in the language RDF" and published "to a decentralized server
network". Each of the three parts is an RDF named graph, so the serialisation is TriG.

The design lesson, independent of whether you adopt the ecosystem: **one fact, one identifier,
three graphs — assertion, how it came to be, and who said so.** A hypergraph gives you the first
for free; the other two are metadata on the same hyperedge ID. The total count of published
nanopublications is **[unverified]** — this pass did not find a figure it could cite.

### Signed and content-addressed identifiers

Nanopublications use trusty URIs (hash-based identifiers). HyperGraphDB uses type-4 UUIDs so "each
data peer can make up new IDs without a central authority"
([Iordanov, 2010](https://doi.org/10.1007/978-3-642-16720-1_3)). HyperGraphRAG uses
`compute_mdhash_id` over the fact text. The trade-off is the same everywhere: content-addressed IDs
deduplicate automatically and change whenever the content changes; opaque IDs are stable but need a
separate deduplication step (see
[../03-construction/entity-resolution-and-canonicalisation.md](../03-construction/entity-resolution-and-canonicalisation.md)).
For a KHG the right answer is usually **opaque and stable for the fact, content-addressed for the
extraction event** — so re-extracting the same sentence produces the same provenance record but
does not fork the fact.

## 2. Versioning

Four mechanisms, in increasing order of cost:

### 2a. Bitemporal columns on the hyperedge

`valid_from` / `valid_to` (when the fact was true in the world) plus `recorded_from` /
`recorded_to` (when the database believed it). Cheap, queryable in plain SQL, and expresses the
two questions that actually get asked. The sample in
[`schemas/sample.hif.json`](../../schemas/sample.hif.json) carries `valid-from` on the fact for
exactly this reason. This is the default recommendation.

Note the modelling subtlety: in a hyper-relational model, time is often a *qualifier* — another
member of the hyperedge — rather than a column. Wikidata does it that way (`start time`, `end time`
as qualifier snaks), which means the hyperedge's own arity encodes its temporal extent; see
[../02-knowledge-representation/wikidata-and-freebase-data-models.md](../02-knowledge-representation/wikidata-and-freebase-data-models.md).
Both are defensible. Columns are faster to query; qualifiers are more honest about the model.

### 2b. Append-only fact log (Datomic style)

Never update; assert and retract. Datomic's datom carries a transaction component, so every
historical state remains queryable and "as of" queries are free
([Datomic documentation](https://docs.datomic.com/)). For a KHG built by repeated LLM extraction
runs this is attractive: each run is a transaction, and "what did run N think?" is a query rather
than an archaeology project.

### 2c. Git-for-data (TerminusDB style)

TerminusDB describes itself as "a distributed database with a collaboration model — git for data",
with "**Revision Control**: Commits for every update", "**Diff**: Differences between commits can
be interpreted as patches between states", "**Push/Pull/Clone**", and "**Time-Travel Queries**:
Query any state of the database at any commit". Version 12 (README updated May 2026) adds
"Range Queries over Succinct Data" and Allen interval algebra for temporal reasoning
([TerminusDB README](https://github.com/terminusdb/terminusdb), checked 2026-09-20).

This is the right shape when the KHG is curated by people who disagree: branches per curator,
merges with conflict detection, and an audit trail that is the storage format rather than a layer
on top.

### 2d. Named graph per version (RDF)

One named graph per snapshot or per change set, with the dataset as the union. Standard, portable,
and expensive: graph count grows without bound and most stores do not optimise for tens of millions
of tiny graphs. Practical mainly at nanopublication granularity, where each unit is *meant* to be
immutable and separately addressable.

### What none of them solve

**Versioning a hyperedge's membership.** If a fact of arity 4 becomes a fact of arity 5, is it the
same fact? Column-based and log-based schemes both make you decide: mutate the hyperedge (history
of its members is lost unless the log records incidences too) or retire it and create a successor
(then every reference has to be rewritten or indirected). No system surveyed here has an opinion.
Recorded as an open question.

## 3. Scale

### 3a. Reference numbers

| Knowledge base | Scale | Source |
|---|---|---|
| Wikidata | 123,411,810 items (figure dated 31 August 2025 on the statistics page, checked 2026-09-20) | [Wikidata:Statistics](https://www.wikidata.org/wiki/Wikidata:Statistics) |
| Wikidata | ~1.65 billion statements, early 2025 | [Wikipedia, Wikidata](https://en.wikipedia.org/wiki/Wikidata) |
| Freebase (at shutdown, 2016) | ~44 million topics, ~2.4 billion facts | [Wikipedia, Freebase](https://en.wikipedia.org/wiki/Freebase_(database)) |
| Freebase (at launch-era description) | >125 million tuples, 4,000 types, 7,000 properties | [Bollacker et al., SIGMOD 2008](https://dl.acm.org/doi/10.1145/1376616.1376746) |
| Hypergraph-DB stress test | 1,000,000 vertices + 200,000 hyperedges in 6.60 s total (add + query, in-process Python) | [Hypergraph-DB README](https://github.com/iMoonLab/Hypergraph-DB) |

The Wikidata numbers are the ones to design against, because Wikidata is a knowledge hypergraph in
all but name: a statement with qualifiers is a hyperedge. 1.65 billion statements, each with a
main value plus qualifiers plus references, is on the order of 10^9–10^10 incidences. Cross-check
against section 6 of
[tensor-and-sparse-representations.md](tensor-and-sparse-representations.md): at ~8–12 bytes per
incidence in a sparse layout, 10^10 incidences is 80–120 GB of pure structure before any labels —
single-machine-possible, single-process-Python impossible.

### 3b. Compression and summarisation

- **HyperCSA** (succinct self-index over hypergraphs): "compression ratios of 26% to 79% of the
  original file size on real-world hypergraphs", scaling "to larger datasets than existing
  approaches", with neighbour queries "6 to 40 times faster than both standard data structures and
  other hypergraph compression approaches"
  ([Adler, Böttcher and Hartel, arXiv:2506.05023, 5 June 2025](https://arxiv.org/abs/2506.05023)).
- **HyDRA** (lossless summarisation): supernodes and superhyperedges plus a correction table, "a
  substantial reduction in storage cost (80–93% in some settings)", and — crucially for storage
  architecture — "the resulting summaries are themselves hypergraphs, they can be queried directly"
  ([Preti, Anagnostopoulos and Bonchi, arXiv:2606.18274, 5 June 2026](https://arxiv.org/abs/2606.18274)).

Both are research artefacts, not products. Neither has a knowledge-hypergraph variant that
preserves roles and labels.

### 3c. Sharding a hypergraph

Sharding a *graph* means minimising cut edges. Sharding a *hypergraph* means minimising cut nets,
and that is a different and harder objective — a hyperedge of size 20 spanning 5 partitions is cut
in a way a binary edge never is. The field has fifty years of tooling for exactly this:

- **Objectives.** The two standard ones are *cut-net* (count the nets crossing a boundary) and
  *connectivity / km1*, described by KaHyPar as "minimizing the sum of the weights of those nets
  that connect more than one block" ([KaHyPar README](https://github.com/kahypar/kahypar)). For a
  distributed KHG, km1 is the right objective: it counts how many extra machines a query touching
  that fact must contact.
- **Tools.** hMETIS, PaToH, KaHyPar, Mt-KaHyPar (shared-memory parallel), Zoltan. All consume the
  `.hgr` format described in
  [file-formats-overview.md](file-formats-overview.md), which carries integer weights and nothing
  else — so the pipeline is: export the incidence structure to `.hgr` with node weights = expected
  access frequency and net weights = query importance, partition, map block IDs back to fact and
  entity IDs.
- **Fixed vertices.** Both hMETIS and KaHyPar support a fix file — one line per vertex, `-1` for
  free or a block ID to pin — which is how you keep an existing shard assignment mostly stable
  across a repartition ([KaHyPar README](https://github.com/kahypar/kahypar);
  [Mt-KaHyPar FileFormats](https://github.com/kahypar/mt-kahypar/blob/master/mt-kahypar/io/docs/FileFormats.md)).

The awkward part is that partition quality decays as the KHG grows, and repartitioning an online
system means moving data. Nothing in the hypergraph-partitioning literature surveyed here addresses
*incremental* repartitioning of a live knowledge base; the streaming partitioners (e.g. FREIGHT,
SEA 2023) are the nearest thing and assume a one-pass stream rather than an evolving store.
**[unverified]** whether any production KHG is sharded with hypergraph partitioning at all — every
deployed system this pass examined runs on one machine or shards by document.

### 3d. What actually breaks first

In order, from the systems examined:

1. **The vector store**, if it is brute-force (NanoVectorDB holds every vector in RAM and scans) —
   see [vector-stores-and-hybrid-storage-for-rag.md](vector-stores-and-hybrid-storage-for-rag.md).
2. **The single-file graph store.** A GraphML or pickle file that is read and rewritten on every
   flush is O(size) per commit.
3. **The clique expansion**, if anything materialises it — quadratic in edge size.
4. **Cross-store consistency**, once writes are concurrent.
5. Only then, the actual incidence count.

## Sources

- W3C. *PROV-O: The PROV Ontology*, Recommendation 30 April 2013 (status line and Qualified Terms section read 2026-09-20). https://www.w3.org/TR/prov-o/
- Nanopublications documentation site (three elements, RDF, decentralized server network), checked 2026-09-20. https://nanopub.net/
- Groth, P., Gibson, A. and Velterop, J. (2010). *The anatomy of a nanopublication*. Information Services and Use 30(1–2). https://dl.acm.org/doi/10.5555/1883685.1883690
- Iordanov, B. (2010). *HyperGraphDB: A Generalized Graph Database* (UUID identifiers, distributed ID creation). https://doi.org/10.1007/978-3-642-16720-1_3
- Datomic documentation (immutable datoms, transaction component, as-of queries), checked 2026-09-20. https://docs.datomic.com/
- TerminusDB README, "Project Overview (Updated May 2026)" and version 12 features, checked 2026-09-20. https://github.com/terminusdb/terminusdb
- Wikidata. *Wikidata:Statistics* (item count, figure dated 31 August 2025; checked 2026-09-20). https://www.wikidata.org/wiki/Wikidata:Statistics
- Wikipedia. *Wikidata* (statement count, early 2025). https://en.wikipedia.org/wiki/Wikidata
- Wikipedia. *Freebase (database)* (topics and facts at shutdown). https://en.wikipedia.org/wiki/Freebase_(database)
- Bollacker, K., Evans, C., Paritosh, P., Sturge, T. and Taylor, J. (2008). *Freebase: a collaboratively created graph database for structuring human knowledge*. SIGMOD 2008. https://dl.acm.org/doi/10.1145/1376616.1376746
- Hypergraph-DB README, performance section, checked 2026-09-20. https://github.com/iMoonLab/Hypergraph-DB
- Adler, E., Böttcher, S. and Hartel, R. (2025). *Compressing Hypergraphs using Suffix Sorting*. arXiv:2506.05023. https://arxiv.org/abs/2506.05023
- Preti, G., Anagnostopoulos, A. and Bonchi, F. (2026). *HyDRA: Lossless Hypergraph Summarization via Co-Clustering*. arXiv:2606.18274. https://arxiv.org/abs/2606.18274
- KaHyPar repository README (objectives, fixed vertices, hMetis format), checked 2026-09-20. https://github.com/kahypar/kahypar
- Mt-KaHyPar, *File Formats* documentation (hMetis format, fix file format), checked 2026-09-20. https://github.com/kahypar/mt-kahypar/blob/master/mt-kahypar/io/docs/FileFormats.md
