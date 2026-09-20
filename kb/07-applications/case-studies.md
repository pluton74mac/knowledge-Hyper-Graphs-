---
title: Case studies with numbers
type: survey
status: draft
tags: [hypergraph, case-study, evaluation, benchmark, numbers, evidence]
created: 2026-09-20
updated: 2026-09-20
---

# Case studies with numbers

Eight mini case studies, chosen because each reports a concrete figure that can be checked against a
named source, and because together they span the four senses of "hypergraph" in
[applications-overview](applications-overview.md). Each ends with a line on what the number does *not*
show, because the weakest part of this literature is the gap between what is measured and what is
claimed.

---

## 1. Reactome: pairwise projection inflates pathway connectivity

**Setting.** 34 Reactome signalling pathways for influence analysis and 140 non-redundant pathways
benchmarked against 1.4 million STRING protein pairs; the hypergraph has ~19,650 entities and 8,773
hyperedges (15,440 nodes / 8,773 hyperedges after removing small molecules).

**Numbers.** Under a directed *graph* representation ~90 % of nodes reach more than 80 % of the network.
Under compound and bipartite graphs, 30–40 % of node pairs are reachable. Under strict hypergraph
**B-connectivity**, only **5 nodes reach more than 20 others**, and most reach none
([Franzese, Groce, Murali, Ritz, 2019](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007384)).

**What it shows.** The AND semantics of a reaction is load-bearing; the apparent small-world structure of
pathway graphs is substantially an artefact of dropping it.

**What it does not show.** That strict B-connectivity is the biologically correct notion — the authors
introduce B-relaxation distance precisely because reality lies between the extremes.

---

## 2. N-ary QA: decomposing facts into triples costs ~30 accuracy points

**Setting.** WikiPeopleQA, 4,491 QA pairs over an n-ary KG with 557 n-ary relation types, built from
Wikidata-derived WikiPeople.

**Numbers.** Baselines that split n-ary facts into triples via dummy entities scored **10.9 %–24.9 %**
accuracy; fact-tree reasoning that keeps facts intact scored **54.4 %**
([Zhang et al., 2022](https://arxiv.org/abs/2108.08297)).

**What it shows.** The single largest measured penalty for reification-by-decomposition in this KB.

**What it does not show.** A controlled comparison — the intact-fact system also uses a different
reasoning architecture, and the questions are template-generated.

---

## 3. HyperGraphRAG: +7.45 F1 over chunk RAG, and graph RAG *below* chunk RAG

**Setting.** Five domains (Medicine from hypertension guidelines; Agriculture, CS, Legal, Mix from
UltraDomain), six baselines, three metrics.

**Numbers.** Averaged over domains, **+7.45 F1, +7.62 retrieval similarity, +3.69 generation evaluation**
over StandardRAG. Per-domain F1 in Medicine: HyperGraphRAG 35.35, StandardRAG 27.90, HippoRAG2 21.34,
GraphRAG 17.60, PathRAG 14.94, LightRAG 12.79. Ablation in Medicine: removing hyperedge retrieval costs
9 F1 (35.4 → 26.4), removing entity retrieval 5.6, removing chunk fusion 6.2. Construction in the CS
domain: 19,913 entities and **26,902 hyperedges** versus LightRAG's 8,967 entities / 5,632 relations
([Luo et al., 2025](https://arxiv.org/abs/2503.21322)).

**What it shows.** A hypergraph index beats both chunk RAG and four binary graph RAG systems on the
authors' benchmark, and hyperedge retrieval is the largest single contributor.

**What it does not show.** That the gain comes from n-ary *knowledge*: the margin over chunk RAG is
*larger* on binary-source questions (+8.6 F1) than on n-ary-source questions (+5.3), and no
"keep-the-whole-fact-as-a-chunk" baseline is run.

---

## 4. Hyper-RAG: cost of the index, and the price of speed

**Setting.** Nine domain corpora, 0.6M–5.0M tokens each, six different generator LLMs.

**Numbers.** +12.3 % accuracy over direct LLM use on the neurology corpus; +6.3 % over GraphRAG; +6.0 %
over LightRAG. Under selection-based evaluation across the nine corpora, **+35.5 % over LightRAG**
overall, peaking at 55.3 % on the legal corpus. The **Hyper-RAG-Lite** variant retrieves in ~0.315 s
versus ~0.723 s (≈2× faster) and still scores +3.3 % over LightRAG. On the neurology corpus the
extractor produced roughly **13,000 low-order and 4,000 high-order correlations**
([Feng et al., 2025](https://arxiv.org/abs/2504.08758);
[Feng et al., 2026](https://www.nature.com/articles/s41467-026-71411-1)).

**What it shows.** A tunable quality/latency frontier; high-order facts are a real minority (~24 % here)
but not negligible.

**What it does not show.** Independent replication — the evaluation is selection-based (LLM preference)
across corpora the authors assembled.

---

## 5. GraphRAG-Bench: the independent check, and the token bill

**Setting.** Medical guidelines plus pre-20th-century novels; four difficulty levels (fact retrieval,
complex reasoning, contextual summarisation, creative generation); seven graph RAG systems.

**Numbers.** Vanilla RAG reached **83.21 %** evidence recall on simple tasks and matched or beat
GraphRAG there. On complex questions GraphRAG recall reached **87.9–90.9 %**; on medical complex
reasoning HippoRAG2 scored **61.98 %** accuracy against **58.64 %** for vanilla RAG. Per-query token
consumption: **~331,375** (MS-GraphRAG, global mode), **~100,832** (LightRAG), **~1,008** (HippoRAG2),
**~879** (vanilla RAG) ([Xiang et al., 2026](https://arxiv.org/abs/2506.05690)).

**What it shows.** Structure pays only on hard questions, and the accuracy gain (~3 points) can be
accompanied by a 100–380× token bill depending on implementation.

**What it does not show.** Anything about hypergraph RAG specifically — no hypergraph system is in this
benchmark. That absence is itself the finding.

---

## 6. HODDI: higher-order drug events exist at scale; the modelling is unsettled

**Setting.** FDA Adverse Event Reporting System records, 2014–2024, curated as *sets* of co-administered
drugs rather than pairs.

**Numbers.** **109,744 records, 2,506 unique drugs, 4,569 unique side effects**. Hypergraph models
outperformed graph models; a plain multi-layer perceptron outperformed the graph models
([Wang et al., 2025](https://arxiv.org/abs/2502.06274)).

**What it shows.** The higher-order data exists in the real world at a scale worth modelling, and
pairwise resources such as TWOSIDES throw it away.

**What it does not show.** That relational propagation helps — when an MLP on set features beats the
GNNs, the relational baselines were probably weak, and the honest reading is "unsettled".

---

## 7. HIMVH: hypergraphs on fraud, where the labels are real

**Setting.** Six web financial fraud datasets, 15 state-of-the-art baselines.

**Numbers.** Average **+6.42 % AUC, +9.74 % F1, +39.14 % average precision**
([Cui, Zhang, Zhu, Zhang, 2026](https://arxiv.org/abs/2601.11073)).

**What it shows.** The largest gains are in average precision, the metric most sensitive to rare
positives — which is exactly the regime fraud detection operates in — and the labels are ground truth,
not LLM judgements.

**What it does not show.** Anything about role-labelled n-ary facts; these hyperedges are unlabelled
groups (sense B).

---

## 8. Package management: a hypergraph in production, quietly

**Setting.** HyperRes, a formal system for versioned dependency resolution over a hypergraph, with a
three-stage parse → resolve → deploy pipeline and a custom SAT-based solver.

**Numbers.** Translations from **dozens of existing package managers** into the one formalism, enabling
cross-ecosystem resolution ([Gibb et al., 2025](https://arxiv.org/abs/2506.10803), SPLASH 2025).

**What it shows.** Hypergraph modelling deployed for its algebraic properties, not its novelty: a
constraint over a set of admissible versions *is* a hyperedge, and flattening it loses what the solver
needs.

**What it does not show.** Anything about knowledge representation — there are no roles, no qualifiers
and no retrieval here. It is the control case: what it looks like when a hypergraph is the obviously
right model and nobody writes a position paper about it.

---

## Cross-cutting observations

1. **The best-evidenced results are outside the LLM literature** (Reactome, HODDI, fraud, package
   management). The LLM-facing results are the most numerous and the least independently verified.
2. **Effect sizes cluster by evidence type.** Ground-truth-labelled tasks show single-digit percentage
   gains; LLM-judged RAG tasks show double-digit ones. That ordering should be treated as informative
   about the measurement, not about the method.
3. **Only two studies isolate n-ary-ness itself**: the triple-decomposition ablation in WikiPeopleQA
   (case 2) and the binary-reduction ablation in HyperRAG (−2.3 MRR,
   [Lien et al., 2026](https://arxiv.org/abs/2602.14470)). Everything else compares whole systems.
4. **The bipartite-encoding objection applies throughout** — every result above could in principle be
   reproduced on the incidence bipartite graph; see
   [hypergraph-vs-bipartite-graph-debate](../10-comparative-and-critique/hypergraph-vs-bipartite-graph-debate.md).
5. **Nobody reports a negative result about hypergraphs.** In a literature this size that is itself a
   signal about publication practice.

## Sources

- Franzese, N., Groce, A., Murali, T. M., Ritz, A. *Hypergraph-based connectivity measures for signaling pathway topologies.* PLoS Computational Biology 15(10):e1007384, 2019. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007384
- Zhang, Y., Li, P., Liang, H., Jatowt, A., Yang, Z. *Fact-Tree Reasoning for N-ary Question Answering over Knowledge Graphs.* Findings of ACL 2022; arXiv:2108.08297. https://arxiv.org/abs/2108.08297
- Luo, H. et al. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322
- Feng, Y. et al. *Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation.* arXiv:2504.08758, 2025. https://arxiv.org/abs/2504.08758
- Feng, Y. et al. *Hyper-RAG.* Nature Communications, 2026. https://www.nature.com/articles/s41467-026-71411-1
- Xiang, Z., Wu, C., Zhang, Q., Chen, S., Hong, Z., Huang, X., Su, J. *When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation.* ICLR 2026; arXiv:2506.05690. https://arxiv.org/abs/2506.05690
- Wang, Z., Shi, Y., Liu, X., Chen, C., Wen, J., Wang, R. *HODDI: A Dataset of High-Order Drug-Drug Interactions for Computational Pharmacovigilance.* arXiv:2502.06274, 2025. https://arxiv.org/abs/2502.06274
- Cui, R., Zhang, N., Zhu, K., Zhang, Q. *Hippocampus-Inspired Multi-View Hypergraph Learning for Web Finance Fraud.* arXiv:2601.11073, 2026. https://arxiv.org/abs/2601.11073
- Gibb, R. et al. *Solving Package Management via Hypergraph Dependency Resolution.* SPLASH 2025; arXiv:2506.10803. https://arxiv.org/abs/2506.10803
- Lien, W.-S. et al. *HyperRAG: Reasoning N-ary Facts over Hypergraphs for Retrieval Augmented Generation.* WWW 2026; arXiv:2602.14470. https://arxiv.org/abs/2602.14470
