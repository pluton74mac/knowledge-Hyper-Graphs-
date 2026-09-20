---
title: Section 03 — Construction of knowledge hypergraphs
type: survey
status: draft
tags: [hypergraph, n-ary, construction, index]
created: 2026-09-20
updated: 2026-09-20
---

# 03 — Construction

**How is a knowledge hypergraph built?** From text, from tables and databases, from an existing knowledge
graph, by hand, or by a language model — and how do you know the result is any good?

This section covers the whole production path: extraction, identity, schema, storage-facing hyperedge
formation, provenance, quality control, updating, and evaluation. If you only read one note, read
[the pipeline overview](construction-pipeline-overview.md); it is the map that every other note in this
section hangs off.

Prerequisites: [what is a knowledge hypergraph](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md)
for the target object, and [hypergraph definitions](../01-foundations/hypergraph-definitions.md) for the
mathematics.

## The notes

| Note | What it answers |
|---|---|
| [construction-pipeline-overview](construction-pipeline-overview.md) | The nine-stage reference pipeline, why a KHG pipeline differs from a KG pipeline, and indicative costs. |
| [n-ary-relation-extraction-from-text](n-ary-relation-extraction-from-text.md) | How n-ary facts are pulled out of text: closed-schema event extraction, semantic role labelling, open IE, and supervised n-ary extractors. |
| [llm-based-khg-construction](llm-based-khg-construction.md) | What the LLM-based systems (GraphRAG, LightRAG, HyperGraphRAG, Hyper-RAG and their 2026 successors) actually do, prompt by prompt. |
| [from-knowledge-graphs-to-hypergraphs](from-knowledge-graphs-to-hypergraphs.md) | Lifting n-ary facts out of Wikidata qualifiers and Freebase CVTs; how JF17K, WikiPeople, WD50K and FB-AUTO were built. |
| [entity-resolution-and-canonicalisation](entity-resolution-and-canonicalisation.md) | Mention, phrase and fact-level identity: coreference, entity linking, relation canonicalisation, and hyperedge deduplication. |
| [schema-induction-and-ontology-alignment](schema-induction-and-ontology-alignment.md) | Where relation names, role names and arity come from: closed ontologies, open vocabularies, induced schemas, role-signature induction, and alignment onto existing ontologies. |
| [incremental-and-streaming-construction](incremental-and-streaming-construction.md) | Appending, merging, invalidating and deleting; bi-temporal facts; versioning and archives; streaming maintenance. |
| [curation-crowdsourcing-and-quality](curation-crowdsourcing-and-quality.md) | Human curation regimes (Wikidata, Cyc, biocuration), Wikidata property constraints as n-ary validation, quality frameworks, and a proposed metric suite for hyperedges. |
| [evaluation-of-constructed-khgs](evaluation-of-constructed-khgs.md) | Strict and soft n-ary F1, the benchmark datasets, coverage and downstream QA, LLM-as-judge and its biases, stability. |
| [hypergraph-construction-from-data](hypergraph-construction-from-data.md) | Co-occurrence, co-authorship, baskets, tables, relational databases, event logs and feature-kNN — and a five-question test for when such a hypergraph is "knowledge". |
| [multimodal-and-multilingual-construction](multimodal-and-multilingual-construction.md) | Building KHGs from images, video, tables and non-English text: the 2026 multimodal hypergraph-RAG systems, scene hypergraphs, multimedia event extraction, ACE/MEE/MINION as the only multilingual resources — and what does not exist. |
| [human-in-the-loop-annotation-and-cost](human-in-the-loop-annotation-and-cost.md) | The annotation instruments for n-ary facts (HyperRED's rubric, ACE, MEE/MINION, Wikidata qualifiers), inter-annotator agreement and the missing arity study, active learning, and what curation costs from Cyc to $0.0063 per 1k tokens. |

## Reading paths

**I want to build one, from text, this week.**
[pipeline overview](construction-pipeline-overview.md) →
[LLM-based construction](llm-based-khg-construction.md) →
[entity resolution](entity-resolution-and-canonicalisation.md) →
[incremental construction](incremental-and-streaming-construction.md) §8 checklist.

**I have structured data already.**
[hypergraph construction from data](hypergraph-construction-from-data.md) (start with §7, the test) →
[from knowledge graphs to hypergraphs](from-knowledge-graphs-to-hypergraphs.md) →
[schema induction](schema-induction-and-ontology-alignment.md).

**I want to evaluate or critique a constructor.**
[evaluation](evaluation-of-constructed-khgs.md) →
[curation and quality](curation-crowdsourcing-and-quality.md) §5 →
[n-ary relation extraction](n-ary-relation-extraction-from-text.md) §6.

**I care about the research frontier.**
[schema induction](schema-induction-and-ontology-alignment.md) §8,
[incremental construction](incremental-and-streaming-construction.md) §9,
[evaluation](evaluation-of-constructed-khgs.md) §8,
[curation and quality](curation-crowdsourcing-and-quality.md) §6,
[hypergraph construction from data](hypergraph-construction-from-data.md) §8 — the open-problem lists.

## What this section concludes

Five claims that recur across the notes and that a reader should take away:

1. **Extraction is the bottleneck, not representation.** The hypergraph formalism is expressive enough;
   open-schema LLM extraction produces hyperedges that are weaker on identity, relation typing and roles
   than an ordinary well-designed database row.
2. **Roles are the hard part.** Grouping participants into one fact is solved well enough; labelling each
   participant's role, canonicalising role names, and inducing role signatures are not.
3. **Arity is variable and merging is unsolved.** Two extractions of the same fact routinely differ in
   arity, so hyperedge equality is the wrong merge criterion, and no published system handles it.
4. **Provenance is the load-bearing field.** Incremental update, retraction, versioning, quality assessment
   and trust all reduce to having a correct `source_id` on every hyperedge and every incidence.
5. **Evaluation lags badly.** There is one small document-level n-ary benchmark, no arity-stratified
   results anywhere, and no metric for hyperedge structure.

## Conventions

All notes in this section follow [`CONVENTIONS.md`](../../CONVENTIONS.md): YAML front matter, inline
author–year citations linked to the primary source, a `## Sources` section per note, and `[unverified]`
marking anything that could not be confirmed.

The consolidated bibliography for this section is
[`sources/by-topic/03-construction.md`](../../sources/by-topic/03-construction.md).
