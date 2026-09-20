---
title: Section 05 — Query, embeddings, reasoning
type: index
status: draft
tags: [index, query, embedding, reasoning, learning, section-readme]
created: 2026-09-20
updated: 2026-09-20
---

# 05 — Query, embeddings, reasoning

**How is a knowledge hypergraph queried, embedded, learned on, and reasoned over?**

Sections 02–04 settle what a knowledge hypergraph *is* and how it is built and stored. This section
is about what you can then *do* with it. Ten notes, in three groups.

## Notes

### Querying and reasoning symbolically

| Note | What it covers |
|---|---|
| [query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md) | SPARQL 1.1 and SPARQL 1.2 triple terms, TypeQL n-ary patterns, GQL/openCypher, Gremlin, Datalog, MeTTa/Atomspace, the HypergraphDB API; sub-hypergraph isomorphism, conjunctive queries and hypertree decompositions |
| [logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md) | Horn rules as B-hypergraph reachability, Datalog over n-ary predicates, rule mining, OWL/RDF 1.2 reasoning, complex query answering (StarQE, NQE, SQE, LKHGT) |
| [hypergraph-algorithms-for-knowledge.md](hypergraph-algorithms-for-knowledge.md) | s-walks and s-centralities, random walks and hypergraph PageRank, clustering and modularity, motifs, hyperpaths, transversals, matching, and the complexity of each |

### Learning on knowledge hypergraphs

| Note | What it covers |
|---|---|
| [knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) | The chronological survey 2016–2026: m-TransH, RAE, NaLP, HINGE, NeuInfer, HypE/HSimplE, GETD, StarE, RAM, GRAN, ShrinkE, HyConvE, HyNT, HAHE, HyperMono, HCNet, HYPER, THOR — with a verified-scores table |
| [benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md) | JF17K, WikiPeople, FB-AUTO, M-FB15K, WD50K and the WD20K/Few/Ext families; MRR and Hits@K; the JF17K leakage result; six pitfalls and a reporting checklist |
| [hypergraph-neural-networks.md](hypergraph-neural-networks.md) | HGNN, HyperGCN, HNHN, UniGNN, AllSet, ED-HNN, hypergraph transformers; clique vs. star expansion; the Width Wall expressivity hierarchy; DHG, HyperNetX, TopoX |
| [inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md) | Node-inductive, relation-inductive and few-shot link prediction: QBLP, HART, MetaNIR, HANCL, MetaRH, HYPER, THOR |
| [temporal-and-dynamic-khgs.md](temporal-and-dynamic-khgs.md) | Time as a role vs. time as validity vs. structural evolution: HyNT, NE-Net, HypeTKG; dynamic hypergraph learning |

### Using and trusting the results

| Note | What it covers |
|---|---|
| [llm-and-khg-interaction.md](llm-and-khg-interaction.md) | Text-to-SPARQL / TypeQL, hypergraph RAG (HyperGraphRAG, Hyper-RAG, PRoH, HyperRAG), hypergraph memory, "Hypergraph as Language", and why LLMs still do not do n-ary link prediction |
| [explainability-and-uncertainty.md](explainability-and-uncertainty.md) | HyperMLN, NYLON, calibration, uncertain knowledge bases, and the gaps |

Bibliography for this section: [`sources/by-topic/05-query-embeddings-reasoning.md`](../../sources/by-topic/05-query-embeddings-reasoning.md).

## Reading paths

- **"I need to query one."** → [query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md)
  → [hypergraph-algorithms-for-knowledge.md](hypergraph-algorithms-for-knowledge.md) §9.
- **"I need to complete one."** → [knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md)
  → [benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md)
  → [inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md).
- **"I need an LLM to use one."** → [llm-and-khg-interaction.md](llm-and-khg-interaction.md)
  → [hypergraph-algorithms-for-knowledge.md](hypergraph-algorithms-for-knowledge.md) §1 (s-walks as
  retrieval expansion).
- **"I want the theory."** → [hypergraph-neural-networks.md](hypergraph-neural-networks.md) §3
  → [query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md) §10
  → [logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md) §1.

## Ten findings this section establishes

1. **No standard query language exists.** SPARQL 1.2's triple terms (W3C Working Draft, 13 September
   2026) cover the hyper-relational shape — a triple plus qualifiers — but not the symmetric n-ary
   fact. TypeQL is the only widely deployed language with native n-ary patterns and an "at least
   these participants" semantics.
2. **Hypertree width is the shared parameter** between tractable conjunctive-query evaluation
   (Gottlob, Leone and Scarcello) and hypergraph-neural-network expressivity (the 2026 Width Wall
   hierarchy). Both query planning and learning are bounded by the same structural quantity.
3. **Reification is information-preserving but learning-hostile.** Fatemi et al. state that under
   reification "the binary relations created are equivalent to the original representation and
   reification does not lose information during conversion"; what fails is *learning*, because the
   auxiliary entity introduced per fact has no embedding at test time. The measured cost is large —
   r-SimplE scores JF17K MRR 0.102 against HypE's 0.494 — and KG foundation models applied to
   reified hypergraphs stay behind hypergraph-native ones ("increasing the number of training graphs
   does not close the gap"). *Star-to-clique*, not reification, is the lossy conversion. See
   [../10-comparative-and-critique/limitations-and-failure-modes.md](../10-comparative-and-critique/limitations-and-failure-modes.md) §2.
4. **The three n-ary formalisations make scores incomparable.** Hyperedge-formalisation papers
   predict every position; hyper-relational papers predict the object. Same dataset name, different
   task.
5. **JF17K leaks and WikiPeople is barely hyper-relational.** 44.5% of JF17K test statements share
   their main triple with training; after removing literals, under 3% of WikiPeople statements carry
   any qualifier.
6. **Architectures converged on attention.** Neural methods dominate; HAHE is the best method across
   JF17K, WikiPeople and WD50K in the field's own comparison; spatial-mapping methods are worst.
7. **The remaining gains are structural, not architectural**: qualifier monotonicity (ShrinkE,
   HyperMono), numeric literals (HyNT), noise (NYLON), schema (HyperCL), and transfer (HYPER, THOR).
8. **2025–2026 brought the first foundation models and the first real theory** — HYPER's positional
   interaction encoder generalises across arities; HCNet's relational Weisfeiler-Leman analysis and
   the Width Wall hierarchy say what these models can and cannot distinguish.
9. **Hypergraph RAG is the busiest application line**, with a reference implementation
   (HyperGraphRAG, NeurIPS 2025) and an active critique-and-improve cycle (PRoH at WWW 2026 reports
   +19.73% F1 over it).
10. **Explainability and uncertainty are nearly empty.** One explainability method in ~50; no
    calibration study; no uncertain-KHG benchmark; no counterfactual or hyperpath explanations,
    despite polynomial-delay hyperpath enumeration being available on B-hypergraphs.

## Where this section is thin

- No hands-on measurements: everything here is read from papers, nothing re-run.
- Storage and indexing are out of scope here and belong to section [04](../04-storage-and-formats/).
- Coverage of Chinese-language and industrial systems is likely incomplete.
- Several 2026 preprints are cited (Width Wall, THOR, HyperRAG, Hypergraph as Language); they are
  marked as preprints and their results are not independently replicated.
