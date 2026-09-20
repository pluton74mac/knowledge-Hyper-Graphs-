---
title: Incremental, streaming and temporal knowledge hypergraph construction
type: survey
status: draft
tags: [hypergraph, n-ary, construction, incremental, streaming, temporal, versioning, deduplication]
created: 2026-09-20
updated: 2026-09-20
---

# Incremental, streaming and temporal construction

A knowledge hypergraph built once from a fixed corpus is a special case. The general case is a KHG that
keeps receiving documents, has to absorb corrections, and has to say *when* each fact was true and when it
was believed. This note covers stage 9 of the
[construction pipeline](construction-pipeline-overview.md): what changes when construction never stops.

## 1. Four distinct update problems

They are routinely conflated, and only the first is well served by current systems.

| Problem | Question | State of the art |
|---|---|---|
| **Append** | How do I add new documents without rebuilding? | Solved by set union + re-summarisation |
| **Merge / dedup on insert** | Is this hyperedge the one I already have? | Content hashing + name matching; weak |
| **Invalidate / correct** | This fact is now false — what happens to it? | Bi-temporal edge invalidation (agent-memory systems) |
| **Delete / retract** | Remove a source and everything derived from it | Largely unsolved in KHG-RAG systems |

The motivation for all four is cost. LightRAG's analysis of the rebuild alternative: "When a new dataset of
the same size as the legal dataset is introduced, GraphRAG must dismantle its existing community structure
to incorporate new entities and relationships, followed by complete regeneration"
([Guo et al., 2024](https://arxiv.org/abs/2410.05779)).

## 2. Append: union of sets, then re-summarise what moved

The dominant pattern, stated most plainly by LightRAG: for a new document, "the incremental update
algorithm processes it using the same graph-based indexing steps φ as before", and then LightRAG "combines
the new graph data with the original by taking the union of the node sets ... as well as the edge sets"
([Guo et al., 2024](https://arxiv.org/abs/2410.05779)). Two design goals are named: "Seamless Integration of
New Data" (the same φ, so no special path) and "Reducing Computational Overhead" (no rebuild of the index
graph).

GraphRAG added the same capability as a first-class CLI verb. `graphrag update` is documented as "Update an
existing knowledge graph index. Applies a default output configuration (if not provided by config), saving
the new index to the local file system in the `update_output` folder", with indexing methods
`standard-update` and `fast-update` alongside the full-build `standard` and `fast`
([GraphRAG CLI documentation](https://microsoft.github.io/graphrag/cli/), checked 2026-09-20). Writing to a
separate output location rather than in place is the pragmatic answer to "what if the update is wrong".

**Why union is not enough for a hypergraph.** Union of edge sets works because a binary edge is identified
by its endpoints. A hyperedge is identified by a *set* of participants plus a relation, and two extractions
of the same fact frequently differ in arity (one mentions the date, the other does not). Set union then
produces two hyperedges where there should be one. Nothing in the published KHG-RAG systems solves this;
see [entity resolution and canonicalisation](entity-resolution-and-canonicalisation.md) §4.

## 3. Dedup on insert: what the KHG code actually does

HyperGraphRAG's insert path is content-hash idempotence at two levels. Documents are keyed by
`compute_mdhash_id(c.strip(), prefix="doc-")`, filtered against what is already stored
(`filter_keys`), and if nothing is new the run stops with "All docs are already in the storage"; chunks are
then keyed by `compute_mdhash_id(dp["content"], prefix="chunk-")` and filtered the same way
([HyperGraphRAG repository](https://github.com/LHRLAB/HyperGraphRAG), `hypergraphrag/hypergraphrag.py`,
checked 2026-09-20). So re-inserting the same document is free; inserting a *paraphrase* of it duplicates
everything.

At the hyperedge level, `_merge_hyperedges_then_upsert` looks up the existing hyperedge node, sums the
weights of the old and new observations, and unions the `source_id` lists with the `GRAPH_FIELD_SEP`
separator; `_merge_nodes_then_upsert` does the analogous thing for entities, concatenating descriptions and
calling an LLM summariser only when the concatenation exceeds `entity_summary_to_max_tokens`
(`hypergraphrag/operate.py`, checked 2026-09-20). This is a sound incremental design — accumulate evidence,
summarise lazily — with one gap: merging is keyed on the *exact normalised hyperedge string*, so it merges
repeats but not rephrasings.

Deletion is entity-scoped only (`delete_by_entity` / `adelete_by_entity`); there is no "forget this
document and everything derived from it" operation, even though every element carries `source_id`
provenance that would make it computable.

## 4. Hypergraph-specific incremental refinement

Hyper-M2RAG is the clearest hypergraph-native answer to "refine without a global sweep". It observes that
"existing refinement strategies often rely on exhaustive, full-page reconstruction to align cross-modal
information, leading to prohibitive computational redundancy", and introduces "an Anchor-driven Incremental
Refinement mechanism": "Rather than performing a global sweep, our approach identifies boundary-crossing
anchor nodes and reconstructs their local hyper-topology using one-hop neighborhood contexts"
([Chen et al., 2026](https://arxiv.org/abs/2608.16628)). The generalisable idea: after an append, the only
hyperedges that need rebuilding are those incident to nodes whose neighbourhood changed — a locality
argument that is stronger in a hypergraph than in a graph, because one hyperedge already carries the whole
local context.

DIAL-KG makes the loop explicit at the schema level: its third stage is "Schema Evolution, in which new
schemas are induced from validated knowledge to guide subsequent construction cycles, and knowledge from
the current round is incrementally applied to the existing KG", orchestrated by a "Meta-Knowledge Base"
([Bao et al., 2026](https://arxiv.org/abs/2603.20059)). Its middle stage, "Governance Adjudication, which
ensures the fidelity and currency of extracted facts to prevent hallucinations and knowledge staleness", is
the invalidate step of §1 done by adjudication rather than by time.

iText2KG builds incrementality into the extractor itself rather than the merge: four modules — "Document
Distiller, Incremental Entity Extractor, Incremental Relation Extractor, and Graph Integrator and
Visualization" — designed for "incremental, topic-independent KG construction without post-processing"
([Lairgi et al., 2024](https://arxiv.org/abs/2409.03284)).

## 5. Time: two clocks, not one

Any KHG that is updated needs to distinguish *when a fact was true* from *when the system learned it*.
Graphiti, the engine under Zep, is the most explicit published implementation: "the system tracks four
timestamps: t′created and t′expired ... monitor when facts are created or invalidated in the system, while
tvalid and tinvalid ... track the temporal range during which facts held true"
([Rasmussen et al., 2025](https://arxiv.org/abs/2501.13956)). Contradiction handling follows from this:
"When the system identifies temporally overlapping contradictions, it invalidates the affected edges by
setting their tinvalid to the tvalid of the invalidating edge. Following the transactional timeline T′,
Graphiti consistently prioritizes new information when determining edge invalidation." Facts are
invalidated, never deleted — which is what makes the history auditable.

Graphiti also runs entity resolution *on insert*: it embeds each extracted entity name, "performs a
separate full-text search on existing entity names and summaries to identify additional candidate nodes",
and passes "these candidate nodes, together with the episode context ... through an LLM using our entity
resolution prompt". Its store is layered into an "Episode Subgraph" of raw input, a "Semantic Entity
Subgraph" built on it, and a "Community Subgraph" at the top — i.e. raw provenance is kept as a first-class
layer, which is exactly what makes retraction feasible.

ATOM applies the same two-clock idea to construction from text: it decomposes documents into "atomic facts"
— minimal self-contained units — and uses "dual-time modeling" separating observation time from valid time,
merging atomic temporal KGs in parallel; it reports roughly 18% higher exhaustivity, ~33% better stability
and over 90% latency reduction against its baselines
([Lairgi et al., 2026](https://arxiv.org/abs/2510.22590), EACL 2026). Note this is by the iText2KG authors:
the line runs incremental → atomic + temporal.

**The n-ary representation of time is not settled.** In the representation-learning literature the two
temporal extensions of n-ary structures are hyper-relational temporal KGs, which attach a timestamp to the
main quadruple (HypeTKG), and n-ary temporal KGs, which model each fact as
`(predicate, ρ1:e1, …, ρn:en, t)` across time snapshots (NE-Net); the surveying authors conclude that
"temporal extensions for n-ary relational models remain under-explored"
([Lu et al., 2026](https://arxiv.org/abs/2506.05626), IEEE TKDE). For a constructor this is a live choice:
time as a qualifier inside the hyperedge, or time as an index over hypergraph snapshots, or the bi-temporal
four-timestamp record above. They are not interchangeable — only the third supports "what did we believe
last March?".

## 6. Versioning and archives

Incremental construction produces versions whether or not anyone plans for them. The RDF archiving
literature is the mature reference, and its three storage strategies transfer directly to hypergraphs:
independent copies (IC), change-based deltas (CB), and timestamped statements (TB), benchmarked by BEAR
([Fernández et al., 2019](https://doi.org/10.3233/SW-180309), *Semantic Web* 10(2), 247–291). OSTRICH-style
systems mix them; the bidirectional-delta-chain refinement reports on the storage/query trade-off directly
([Taelman et al., 2022](https://doi.org/10.3233/SW-210449), *Semantic Web* 13(4), 705–734).

Two practical notes for a KHG:

- **TB is the natural fit** because a hyperedge already carries per-element metadata (weight, `source_id`);
  adding `valid_from` / `valid_to` / `asserted_from` / `asserted_to` costs four fields per hyperedge and
  gives you §5 for free.
- **CB deltas are awkward** because the unit of change is a *set*. Adding one participant to an existing
  hyperedge is either a modification of one element or a delete-plus-insert of two, and the archive
  literature has no answer for which, because RDF has no such unit. `[unverified]` — I found no published
  hypergraph-archive format or benchmark during this research run.

Wikidata's own answer is full revision history per item plus statement-level `rank` (deprecated statements
are retained rather than removed), which is why studies can use "statements that have been removed and not
added back" and "statements that have been deprecated" as quality signals
([Shenoy et al., 2021](https://arxiv.org/abs/2107.00156)). See
[curation and quality](curation-crowdsourcing-and-quality.md).

## 7. Streaming

True streaming construction — react to a change event rather than to a batch — appears in production
systems rather than in KHG papers. ODKE+ is the clearest published example: an "Extraction Initiator detects
missing or stale facts", the pipeline "supports batch and streaming modes", and the deployment reports
"reducing update lag by 50 days on average"
([Khorshidi et al., 2025](https://arxiv.org/abs/2509.04696)). The architectural lesson is that streaming KB
maintenance is driven by *staleness detection*, not by document arrival: the system asks which facts are
missing or old and goes to find evidence, rather than waiting for a corpus.

No hypergraph-native streaming constructor was found in this research run. The nearest neighbours are
Hyper-M2RAG's local refinement (§4), which is the right primitive, and OKH-RAG, which adds ordering to
hyperedges by inferring "precedence directly from data without requiring explicit temporal supervision"
([Wu et al., 2026](https://arxiv.org/abs/2604.12185)) — relevant because a stream is exactly where
precedence information is available and is usually thrown away.

## 8. Checklist for an incremental KHG (opinion)

1. Content-hash every source unit; make insert idempotent (HyperGraphRAG does this — copy it).
2. Keep `source_id` on every entity, hyperedge and incidence. Without it, retraction and re-indexing are
   impossible.
3. Store four timestamps per hyperedge, not one.
4. Invalidate, never delete, and keep the invalidating hyperedge's id as the reason.
5. After an append, recompute only the neighbourhood of touched nodes (anchor-driven refinement), and
   re-summarise only the communities whose membership changed.
6. Re-induce the schema periodically, and record which schema version a hyperedge was typed under
   (see [schema induction](schema-induction-and-ontology-alignment.md)).

## 9. Open problems

- Merging hyperedges of *different arity* across increments is unsolved and unbenchmarked.
- No published hypergraph archive format or version benchmark (the RDF equivalent, BEAR, is from 2019).
- Deletion/unlearning in LLM-built KHGs: descriptions have been LLM-summarised across sources, so removing
  one source does not cleanly remove its contribution.
- Schema drift across increments (also listed in the schema note).
- No shared benchmark for incremental construction quality — ATOM's "exhaustivity" and "stability" are
  self-defined; see [evaluation](evaluation-of-constructed-khgs.md).

## Sources

- Guo, Z., Xia, L., Yu, Y., Ao, T., Huang, C. "LightRAG: Simple and Fast Retrieval-Augmented Generation." arXiv 2410.05779, 2024 (rev. 2025). https://arxiv.org/abs/2410.05779
- Microsoft. GraphRAG documentation, "CLI" (the `update` command and `standard-update` / `fast-update` methods), checked 2026-09-20. https://microsoft.github.io/graphrag/cli/
- Microsoft. GraphRAG documentation, "Indexing Methods", checked 2026-09-20. https://microsoft.github.io/graphrag/index/methods/
- LHRLAB. HyperGraphRAG repository (`hypergraphrag/hypergraphrag.py`, `hypergraphrag/operate.py`), checked 2026-09-20. https://github.com/LHRLAB/HyperGraphRAG
- Luo, H., E, H., Chen, G., Zheng, Y., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025; arXiv:2503.21322 (v3, 21 October 2025). https://arxiv.org/abs/2503.21322
- Chen, S., Xu, Y., Han, X., Xue, R., Wu, D., Gao, Y., Yan, C., Gao, Y. "Hypergraph-based Multimodal Retrieval-Augmented Generation with Incremental Refinement." ACM MM 2026 / arXiv 2608.16628. https://arxiv.org/abs/2608.16628
- Bao, W., Wang, Y., Gao, R., Leng, F., Bao, Y., Yu, G. "DIAL-KG: Schema-Free Incremental Knowledge Graph Construction via Dynamic Schema Induction and Evolution-Intent Assessment." arXiv 2603.20059, 2026. https://arxiv.org/abs/2603.20059
- Lairgi, Y., Moncla, L., Cazabet, R., Benabdeslem, K., Cléau, P. "iText2KG: Incremental Knowledge Graphs Construction Using Large Language Models." WISE 2024 / arXiv 2409.03284. https://arxiv.org/abs/2409.03284
- Lairgi, Y., Moncla, L., Benabdeslem, K., Cazabet, R., Cléau, P. "ATOM: AdapTive and OptiMized dynamic temporal knowledge graph construction using LLMs." EACL 2026 / arXiv 2510.22590, 2025 (rev. January 2026). https://arxiv.org/abs/2510.22590
- Rasmussen, P., Paliychuk, P., Beauvais, T., Ryan, J., Chalef, D. "Zep: A Temporal Knowledge Graph Architecture for Agent Memory." arXiv 2501.13956, 2025. https://arxiv.org/abs/2501.13956
- Lu, X., Tupikina, L., Alam, M. "Two-dimensional Taxonomy for N-ary Knowledge Representation Learning Methods." IEEE Transactions on Knowledge and Data Engineering (accepted) / arXiv 2506.05626, 2025 (v3, 6 September 2026). https://arxiv.org/abs/2506.05626
- Fernández, J. D., Umbrich, J., Polleres, A., Knuth, M. "Evaluating query and storage strategies for RDF archives." Semantic Web 10(2), 247–291, 2019. https://doi.org/10.3233/SW-180309
- Taelman, R., Mahieu, T., Vanbrabant, M., Verborgh, R. "Optimizing storage of RDF archives using bidirectional delta chains." Semantic Web 13(4), 705–734, 2022. https://doi.org/10.3233/SW-210449
- Shenoy, K., Ilievski, F., Garijo, D., Schwabe, D., Szekely, P. "A Study of the Quality of Wikidata." Journal of Web Semantics, 2021 / arXiv 2107.00156. https://arxiv.org/abs/2107.00156
- Khorshidi, S., Nikfarjam, A., Shankar, S., Sang, Y., et al. "ODKE+: Ontology-Guided Open-Domain Knowledge Extraction with LLMs." arXiv 2509.04696, 2025. https://arxiv.org/abs/2509.04696
- Wu, K., Kuai, C., Li, Z., Jiang, J., et al. "Knowledge Is Not Static: Order-Aware Hypergraph RAG for Language Models." arXiv 2604.12185, 2026. https://arxiv.org/abs/2604.12185
