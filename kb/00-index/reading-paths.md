---
title: Reading paths
type: index
status: reviewed
tags: [index, navigation, onboarding]
created: 2026-09-20
updated: 2026-09-20
---

# Reading paths

Six ordered paths through the knowledge base. Times are rough. Every path starts with the same two
notes because they fix the vocabulary everything else depends on.

## Path 0 — The twenty-minute orientation (everyone)

1. [What is a knowledge hypergraph?](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md) — the competing definitions and a comparison table.
2. [Hyper-relational vs n-ary vs hypergraph](../02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md) — the three fact formalisations and when each fits.
3. [Timeline](../08-history-and-frontier/timeline.md) — skim the table.
4. [When to use a knowledge hypergraph, and when not to](../10-comparative-and-critique/when-to-use-and-when-not.md).
5. [Open questions](open-questions.md) — the cross-cutting themes at the top.

## Path 1 — The modeller (half a day)

You need to design a schema for n-ary facts.

1. Path 0.
2. [Hypergraph definitions and variants](../01-foundations/hypergraph-definitions.md) and the [notation cheat sheet](../01-foundations/notation-cheatsheet.md).
3. [Directed and typed hyperedges for knowledge](../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md) — three meanings of "directed".
4. [Knowledge hypergraph schema design](../02-knowledge-representation/knowledge-hypergraph-schema-design.md) — the worked JSON schema and projections.
5. [Wikidata and Freebase data models](../02-knowledge-representation/wikidata-and-freebase-data-models.md) — the largest deployed n-ary knowledge base.
6. [Ontologies and schema languages for n-ary knowledge](../02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md).
7. [Open world, closed world and uncertainty](../02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md).
8. [Formalism comparison matrix](../10-comparative-and-critique/formalism-comparison-matrix.md) and [limitations and failure modes](../10-comparative-and-critique/limitations-and-failure-modes.md).

## Path 2 — The builder (one day)

You need to construct and store a knowledge hypergraph.

1. Path 0.
2. [Construction pipeline overview](../03-construction/construction-pipeline-overview.md).
3. [N-ary relation and event extraction from text](../03-construction/n-ary-relation-extraction-from-text.md) then [LLM-based construction](../03-construction/llm-based-khg-construction.md).
4. [From knowledge graphs to hypergraphs](../03-construction/from-knowledge-graphs-to-hypergraphs.md) if you start from Wikidata, Freebase or tables.
5. [Entity resolution and canonicalisation](../03-construction/entity-resolution-and-canonicalisation.md), [schema induction](../03-construction/schema-induction-and-ontology-alignment.md), [incremental construction](../03-construction/incremental-and-streaming-construction.md).
6. [Evaluating constructed knowledge hypergraphs](../03-construction/evaluation-of-constructed-khgs.md).
7. [File formats overview](../04-storage-and-formats/file-formats-overview.md), [HIF](../04-storage-and-formats/hif-hypergraph-interchange-format.md), [RDF-star and RDF 1.2](../04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md).
8. [Hypergraph databases](../04-storage-and-formats/hypergraph-databases.md), [property-graph emulation](../04-storage-and-formats/property-graph-emulation-patterns.md), [relational and EAV storage](../04-storage-and-formats/relational-and-eav-storage.md).
9. [Format and storage recommendations](../04-storage-and-formats/format-recommendations.md) — the decision guide.
10. [Getting started toolchain](../09-ecosystem/getting-started-toolchain.md) and [software libraries](../09-ecosystem/software-libraries.md).
11. Look at the sample files in `schemas/`.

## Path 3 — The machine-learning researcher (one day)

1. Path 0.
2. [Incidence, matrices, tensors and expansions](../01-foundations/incidence-and-matrix-representations.md) and [random walks and spectral theory](../01-foundations/random-walks-spectral-and-expansion.md).
3. [Benchmarks derived from Freebase and Wikidata](../02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md) and [dataset quality and leakage](../09-ecosystem/dataset-quality-and-leakage-issues.md) — read these before trusting any number.
4. [Knowledge hypergraph embedding models](../05-query-embeddings-reasoning/knowledge-hypergraph-embedding-models.md) and [benchmarks and evaluation protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).
5. [Hypergraph neural networks](../05-query-embeddings-reasoning/hypergraph-neural-networks.md), [inductive and few-shot settings](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md), [temporal and dynamic KHGs](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md).
6. [Tensor and sparse representations](../04-storage-and-formats/tensor-and-sparse-representations.md).
7. [Machine-learning era](../08-history-and-frontier/machine-learning-era.md) and [current frontier directions](../08-history-and-frontier/current-frontier-directions.md).
8. [Hypergraph vs bipartite graph debate](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md) — what a hypergraph model must beat.

## Path 4 — The RAG and agents engineer (half a day)

1. Path 0.
2. [LLM-based construction](../03-construction/llm-based-khg-construction.md).
3. [Retrieval-augmented generation over knowledge hypergraphs](../07-applications/retrieval-augmented-generation.md).
4. [A critical reading of hypergraph-RAG claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md) — read immediately after the previous note.
5. [Vector stores and hybrid storage in hypergraph-RAG systems](../04-storage-and-formats/vector-stores-and-hybrid-storage-for-rag.md).
6. [LLMs and knowledge hypergraphs](../05-query-embeddings-reasoning/llm-and-khg-interaction.md).
7. [AI agents — memory and planning](../07-applications/ai-agents-memory-and-planning.md).
8. [The LLM era, 2023–2026](../08-history-and-frontier/llm-era-2023-2026.md) — the hype-versus-shown ledger.

## Path 5 — The visualiser (half a day)

1. Path 0.
2. [Catalogue of visual encodings](../06-visualization/visual-encodings-catalogue.md).
3. [Visualising knowledge hypergraphs in practice](../06-visualization/knowledge-hypergraph-specific-visualization.md) — the recommended encoding.
4. [Perception and evaluation studies](../06-visualization/perception-and-evaluation-studies.md).
5. [Dynamic and temporal visualisation](../06-visualization/dynamic-and-temporal-hypergraph-visualization.md).
6. [Tools and libraries](../06-visualization/tools-and-libraries.md) then the [cookbook](../06-visualization/visualization-cookbook-for-this-kb.md) and run it.
7. [Hypergraph drawing algorithms](../06-visualization/hypergraph-drawing-algorithms.md) if you need layout theory.

## Path 6 — The historian and strategist (two hours)

1. [Timeline](../08-history-and-frontier/timeline.md), read fully.
2. [Origins](../08-history-and-frontier/origins-hypergraph-theory.md), [knowledge-representation lineage](../08-history-and-frontier/knowledge-representation-lineage.md), [machine-learning era](../08-history-and-frontier/machine-learning-era.md), [LLM era](../08-history-and-frontier/llm-era-2023-2026.md).
3. [Standards convergence](../08-history-and-frontier/standards-convergence.md).
4. [Current frontier directions](../08-history-and-frontier/current-frontier-directions.md).
5. [Open debates](../10-comparative-and-critique/open-debates.md) and [research groups and people](../08-history-and-frontier/research-groups-and-people.md).
6. [Open questions](open-questions.md).

## Sources

Navigation only; each linked note carries its own `## Sources` section.
