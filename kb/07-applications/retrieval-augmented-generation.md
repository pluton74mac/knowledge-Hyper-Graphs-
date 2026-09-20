---
title: Retrieval-augmented generation over knowledge hypergraphs
type: survey
status: draft
tags: [hypergraph, n-ary, RAG, retrieval, LLM, GraphRAG, benchmark, evaluation]
created: 2026-09-20
updated: 2026-09-20
---

# Retrieval-augmented generation over knowledge hypergraphs

Between March 2025 and mid-2026 "hypergraph RAG" went from a single paper to the most active applied
area of knowledge hypergraphs. This note collects the systems, the numbers they report, the costs,
and the reasons to be cautious about the numbers.

The short version: the strongest *published* evidence is that replacing a binary knowledge graph with
a hypergraph index improves answer quality on knowledge-intensive domain QA at a modest extra
construction cost — but almost all of that evidence comes from a small number of groups, on datasets
they built themselves, scored partly by LLM-as-a-judge. The one large independent benchmark of the
*graph*-RAG family found that vanilla chunk RAG is competitive or better on simple questions
([Xiang et al., 2026](https://arxiv.org/abs/2506.05690)).

## 1. What a hyperedge is in these systems

This matters more than it looks, because two different things are called a hyperedge:

- **An extracted n-ary fact.** HyperGraphRAG parses a document into "knowledge fragments", each of
  which becomes a hyperedge carrying a natural-language description plus the set of entities it
  contains — e.g. a hyperedge over *(Hypertensive patient, Male, Serum creatinine 115–133 µmol/L,
  Mild serum creatinine elevation)*. There are **no role labels**: the hyperedge is a text string with
  an entity set, stored as a bipartite graph and embedded in a vector store
  ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)).
- **A grouping device.** Hyper-RAG distinguishes "low-order" (pairwise) from "high-order" correlations
  extracted from the same text ([Feng et al., 2025](https://arxiv.org/abs/2504.08758)); Cog-RAG adds a
  *theme* hypergraph whose hyperedges group chunks by topic, on top of an entity hypergraph
  ([Hu et al., 2026](https://arxiv.org/abs/2511.13201)); OG-RAG's hyperedges are ontology-grounded
  clusters of facts ([Sharma et al., 2024](https://arxiv.org/abs/2412.15235)).

So most hypergraph-RAG systems sit between sense **A** (n-ary fact) and sense **D** (latent grouping) of
the taxonomy in [applications-overview](applications-overview.md). None of the main systems stores a
typed, role-labelled n-ary fact of the kind described in
[what-is-a-knowledge-hypergraph](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md).
That is the single largest gap between the RAG literature and the knowledge-representation literature.

## 2. HyperGraphRAG (NeurIPS 2025)

The reference system. First posted 27 March 2025, v3 21 October 2025, accepted to NeurIPS 2025
([Luo et al., 2025](https://arxiv.org/abs/2503.21322); code at
[LHRLAB/HyperGraphRAG](https://github.com/LHRLAB/HyperGraphRAG)).

**Pipeline.** N-ary relation extraction by an LLM → hyperedges + entities with scores → storage as a
bipartite graph (hyperedge nodes + entity nodes) → two vector bases (one for hyperedges, one for
entities) → at query time, entity retrieval *and* hyperedge retrieval, fused with ordinary chunk
retrieval → generation.

**Setup.** Five domains: Medicine (built from international hypertension guidelines) plus Agriculture,
Computer Science, Legal and Mix taken from UltraDomain as used by LightRAG. Questions are sampled at
one, two and three hops and split into *Binary Source* and *N-ary Source* depending on whether the
supporting knowledge involves more than two entities. Metrics: word-level **F1**, **Retrieval
Similarity (R-S)** against the ground-truth supporting knowledge, and **Generation Evaluation (G-E)**,
an LLM-as-a-judge average over seven dimensions.

**Headline results** (overall F1, from Table 2 of the paper):

| Method | Medicine | Agriculture | CS | Legal | Mix |
|---|---|---|---|---|---|
| NaiveGeneration (no retrieval) | 12.89 | 12.74 | 18.65 | 21.64 | 16.93 |
| StandardRAG (chunks) | 27.90 | 27.43 | 28.93 | 37.34 | 43.20 |
| GraphRAG | 17.60 | 21.28 | 23.33 | 30.11 | 19.27 |
| LightRAG | 12.79 | 18.24 | 22.72 | 31.64 | 27.03 |
| PathRAG | 14.94 | 21.30 | 26.73 | 31.29 | 37.07 |
| HippoRAG2 | 21.34 | 12.63 | 17.34 | 18.53 | 21.53 |
| **HyperGraphRAG** | **35.35** | **33.89** | **31.30** | **43.81** | **48.71** |

Averaged over domains HyperGraphRAG gains **+7.45 F1, +7.62 R-S, +3.69 G-E** over StandardRAG. The
paper's own observation is worth quoting in substance: *the graph-based baselines often underperform
plain chunk RAG*, which the authors attribute to knowledge fragmentation under binary relations. Gains
are larger on Binary Source questions (+8.6 F1 over StandardRAG) than on N-ary Source ones (+5.3),
which is the opposite of what the n-ary story predicts and is not explained in the paper.

**Ablation (Medicine, F1 35.4 for the full system).** Remove entity retrieval → 29.8; remove hyperedge
retrieval → 26.4; remove both → 27.9; remove chunk-retrieval fusion → 29.2; remove everything → 12.9.
Hyperedge retrieval is the single most load-bearing component, but chunk fusion still contributes ~6 F1,
i.e. the hypergraph does not replace text retrieval, it augments it.

**Construction statistics** (entities / hyperedges vs. baselines' entities / relations or communities):

| Domain | Knowledge tokens | GraphRAG entities / communities | LightRAG entities / relations | HyperGraphRAG entities / hyperedges |
|---|---|---|---|---|
| Medicine | 179k | 329 / 256 | 3,725 / 1,304 | 7,675 / 4,818 |
| Agriculture | 382k | 699 / 523 | 5,032 / 3,105 | 16,805 / 16,102 |
| CS | 795k | 1,449 / 930 | 8,967 / 5,632 | 19,913 / 26,902 |
| Legal | 940k | 1,711 / 517 | 5,354 / 6,002 | 11,098 / 18,285 |
| Mix | 122k | 225 / 59 | 2,229 / 940 | 6,201 / 4,356 |

**Cost** (Table 3). Construction: 3.084 s and $0.0063 per 1k tokens, against GraphRAG 9.272 s /
$0.0058, LightRAG and PathRAG 5.168 s / $0.0081, HippoRAG2 2.758 s / $0.0056. Generation: 0.256 s per
query and $3.184 per 1k queries, against StandardRAG 0.147 s / $1.016, GraphRAG 0.221 s / $1.836,
LightRAG 0.359 s / $3.359, PathRAG 0.436 s / $3.496. Retrieval quality saturates around top-k = 60.
So the hypergraph index is roughly **3× the query cost of chunk RAG** and similar to other graph RAGs.

## 3. Hyper-RAG (Nature Communications 2026)

Independent line from a different group, first posted as arXiv 2504.08758 in 2025 and published in
*Nature Communications* in 2026 ([Feng et al., 2025](https://arxiv.org/abs/2504.08758);
[Feng et al., 2026](https://www.nature.com/articles/s41467-026-71411-1); code at
[iMoonLab/Hyper-RAG](https://github.com/iMoonLab/Hyper-RAG)).

The construction extracts entities, *low-order* (pairwise) correlations and *high-order* (multi-entity)
correlations; on the neurology corpus roughly 13,000 low-order and 4,000 high-order correlations were
extracted, i.e. high-order facts are a minority but not a rounding error.

**Corpora.** Nine domain corpora: NeurologyCorp (~1.97M tokens), PathologyCorp (~0.91M), MathCrop
(~3.86M), AgricCorp (~1.99M), FinCorp (~3.83M), PhysiCrop (~2.18M), LegalCrop (~4.96M), ArtCrop
(~3.69M), MixCorp (~0.62M). Six different LLMs were used as the generator.

**Results.** On the neurology corpus, +12.3 % accuracy on average over using the LLM directly, +6.3 %
over GraphRAG and +6.0 % over LightRAG. Under a selection-based (pairwise preference) evaluation across
the nine corpora, +35.5 % over LightRAG overall, with the largest margins on LegalCrop (55.3 %),
AgricCorp (41.3 %) and FinCorp (37.5 %). A **Hyper-RAG-Lite** variant retrieves in ~0.315 s against
~0.723 s for the full system — about twice the speed — and still scores 3.3 % above LightRAG.

The paper's distinctive claim is stability: performance stayed flat as query complexity increased,
whereas the graph baselines degraded.

## 4. HyperRAG (WWW 2026) — and a result that cuts the other way

[Lien et al., 2026](https://arxiv.org/abs/2602.14470) (WWW 2026;
[ACM DOI](https://dl.acm.org/doi/10.1145/3774904.3792710)) build a RAG framework specifically for
*n-ary* hypergraphs, with two retrieval variants: **HyperRetriever**, an MLP scorer over hyperedge
plausibility with directional distance encoding and adaptive thresholding, and **HyperMemory**, which
uses the LLM's own parametric knowledge to guide a beam search (width 3, depth 3) over n-ary facts.

On the closed-domain WikiTopics-CLQA suite (11 topics) HyperRetriever reports MRR 36.94 % and
Hits@10 43.78 %, a 2.95 % and 1.23 % *relative* gain over HyperGraphRAG, best in 9 of 11 domains.
Reducing the n-ary hypergraph to a binary KG drops MRR from 36.45 % to 34.15 %, which is one of the few
direct ablations of *n-ary-ness itself* in this literature.

But on open-domain multi-hop QA (HotpotQA, MuSiQue, 2WikiMultiHopQA) the paper reports **HyperGraphRAG
ahead on exact match** — e.g. 51.00 % vs 42.50 % on HotpotQA, 22.00 % vs 13.50 % on MuSiQue. Whichever
way one reads that, it shows the ranking among hypergraph RAG systems flips with the benchmark.

## 5. Other 2025–2026 systems

- **PRoH** ([Zai et al., 2026](https://arxiv.org/abs/2510.12434), WWW 2026,
  [DOI](https://dl.acm.org/doi/10.1145/3774904.3792611)). Attacks the *static planning* of earlier
  KH-RAG: a context-aware planner sketches the local hypergraph neighbourhood, questions are decomposed
  into a dynamically evolving DAG of subquestions, and an Entity-Weighted-Overlap heuristic ranks
  hyperedge traversals. Reports **+19.73 % F1 and +8.41 % G-E over HyperGraphRAG** on average — the
  largest reported margin over the reference system, and one of the few cross-paper comparisons.
- **Cog-RAG** ([Hu et al., 2026](https://arxiv.org/abs/2511.13201), AAAI 2026,
  [proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/40363)). Dual hypergraph: a *theme*
  hypergraph over chunks plus an *entity* hypergraph, aligned by a top-down "cognitive" retrieval pass.
- **OG-RAG** ([Sharma et al., 2024](https://arxiv.org/abs/2412.15235)). Earlier than HyperGraphRAG and
  often overlooked: documents are mapped to an ontology-grounded hypergraph and retrieval is posed as
  finding a *minimal set of hyperedges* covering the query. Reports +55 % fact recall, +40 % response
  correctness, +27 % fact-based reasoning and 30 % faster attribution across four LLMs, in agriculture,
  healthcare and legal settings. Its ontology grounding is closer to sense A than most successors.
- **OKH-RAG** ([Wu et al., 2026](https://arxiv.org/abs/2604.12185)). Adds *precedence* to hyperedges:
  evidence is retrieved as an ordered interaction trajectory rather than a set, with a learned
  transition model and no explicit temporal annotation. Evaluated on tropical-cyclone and
  port-operation scenarios against permutation-invariant baselines.
- **Hyper-KGGen** ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)). Construction rather than
  retrieval: a coarse-to-fine extractor with a "global skill library" distilled per domain, plus
  **HyperDocRED**, a document-level knowledge-hypergraph extraction benchmark restructured from
  Re-DocRED (50 seed training documents, 100 test documents). Reported micro precision/recall on the
  test split: 0.8024 / 0.4300 for Hyper-KGGen+ versus 0.3828 / 0.1072 for HyperGraphRAG's extractor —
  i.e. the extraction quality of the reference system is itself a major error source.

## 6. The critique: when do graphs (and hypergraphs) pay?

**GraphRAG-Bench** ([Xiang et al., 2026](https://arxiv.org/abs/2506.05690), ICLR 2026;
[repo](https://github.com/GraphRAG-Bench/GraphRAG-Benchmark)) is the most serious independent
evaluation of the family. It builds corpora from medical guidelines (tightly structured) and
pre-20th-century novels (loosely structured), and grades questions at four levels: fact retrieval,
complex reasoning, contextual summarisation, creative generation. Seven systems were tested
(MS-GraphRAG, HippoRAG, HippoRAG2, LightRAG, Fast-GraphRAG, RAPTOR, Lazy-GraphRAG).

Findings that bear directly on hypergraph RAG:

1. **Vanilla RAG matches or beats GraphRAG on simple fact retrieval.** Evidence recall for plain RAG
   was 83.21 % on simple tasks.
2. **Graphs pay on complex reasoning and summarisation**, where GraphRAG recall reached 87.9–90.9 %;
   on medical complex reasoning HippoRAG2 scored 61.98 % accuracy against 58.64 % for plain RAG — a
   real but modest gain.
3. **The token overhead is enormous and highly variable**: ~331,375 tokens per query for MS-GraphRAG in
   global mode, ~100,832 for LightRAG, ~1,008 for HippoRAG2, against ~879 for vanilla RAG.

Note that (3) is per-query *context* cost and is not the same accounting as HyperGraphRAG's dollar
figures in §2, so the two cannot be compared directly — but it does mean "graph RAG is expensive" is
a claim about specific implementations, not about graph indexes in general.

No hypergraph system is in GraphRAG-Bench as of this writing. **The honest position is therefore that
hypergraph RAG has not yet been evaluated by anyone other than its proponents.**

## 7. Honest assessment

What the evidence supports:

- Hypergraph indexes reliably beat *binary* graph RAG indexes in the papers that build both, and the
  gap is large (often 10+ F1 points) rather than marginal.
- Fusing hypergraph retrieval with ordinary chunk retrieval beats either alone (HyperGraphRAG ablation).
- Construction cost is comparable to, and sometimes below, existing graph RAG; query cost is ~2–3× chunk
  RAG. This is a real but not prohibitive tax.
- At least one ablation isolates n-ary-ness: collapsing the hypergraph to binary costs ~2.3 MRR points
  ([Lien et al., 2026](https://arxiv.org/abs/2602.14470)).

What it does not support:

- **Benchmarks are largely self-built.** HyperGraphRAG, Hyper-RAG and Hyper-KGGen each introduce their
  own questions or corpora. Human verification is claimed for HyperGraphRAG's QA pairs, but the
  question generator and the system share an LLM family.
- **LLM-as-a-judge does much of the work.** G-E and Hyper-RAG's selection-based evaluation are both
  LLM-scored. The word-level F1 numbers, which are not, are much lower in absolute terms (30–50).
- **Baseline numbers disagree across papers.** In HyperGraphRAG's tables LightRAG scores *below* plain
  chunk RAG on four of five domains; that is not how LightRAG's own paper reads. Whether this reflects
  tuning, prompt choice or domain, it means cross-paper deltas are not additive.
- **Ranking is benchmark-dependent** (§4), and PRoH's +19.73 % over HyperGraphRAG is measured on
  HyperGraphRAG's own evaluation design.
- **The n-ary claim is weakly tested.** HyperGraphRAG's gains are *larger* on binary-source questions.
  If the hypergraph mainly helps by keeping a sentence's participants together in one retrievable unit,
  that is a chunking/indexing win, not a knowledge-representation win — and it would be reproduced by
  any "keep the whole fact together" baseline, which none of these papers runs.

A sharper, dedicated critique of this literature lives in
[critical-reading-of-hypergraph-rag-claims](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md);
evaluation protocol issues are in
[benchmarks-and-evaluation-protocols](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md).
See [case-studies](case-studies.md) for the numbers gathered in one place and
[ai-agents-memory-and-planning](ai-agents-memory-and-planning.md) for the memory-side descendants.

## Sources

- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., Feng, Y., Kuang, Z., Song, M., Zhu, Y., Luu, A. T. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* NeurIPS 2025; arXiv:2503.21322 (v1 27 Mar 2025, v3 21 Oct 2025). https://arxiv.org/abs/2503.21322
- LHRLAB. *HyperGraphRAG* (official code), GitHub, checked 2026-09-20. https://github.com/LHRLAB/HyperGraphRAG
- Feng, Y., Hu, H., Hou, X., Liu, S., Ying, S., Du, S., Hu, H., Gao, Y. *Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation.* arXiv:2504.08758, 30 Mar 2025; *Nature Communications* 17(1):5778, 27 Apr 2026. https://arxiv.org/abs/2504.08758 ; https://doi.org/10.1038/s41467-026-71411-1
- iMoonLab. *Hyper-RAG* (official code), GitHub, checked 2026-09-20. https://github.com/iMoonLab/Hyper-RAG
- Lien, W.-S., Chan, Y.-K., Hsiao, H.-L., Ruan, B.-K., Chiang, M.-F., Chen, C.-A., Yeh, Y.-R., Shuai, H.-H. *HyperRAG: Reasoning N-ary Facts over Hypergraphs for Retrieval Augmented Generation.* WWW 2026; arXiv:2602.14470, 16 Feb 2026. https://arxiv.org/abs/2602.14470
- Lien, W.-S. et al. *HyperRAG.* Proceedings of the ACM Web Conference 2026. https://dl.acm.org/doi/10.1145/3774904.3792710
- Zai, X., Tan, X., Wang, X., Liu, Q., Xu, X., Zhang, W. *PRoH: Dynamic Planning and Reasoning over Knowledge Hypergraphs for Retrieval-Augmented Generation.* WWW 2026; arXiv:2510.12434. https://arxiv.org/abs/2510.12434
- Zai, X. et al. *PRoH.* Proceedings of the ACM Web Conference 2026. https://dl.acm.org/doi/10.1145/3774904.3792611
- Hu, H., Feng, Y., Li, R., Xue, R., Hou, X., Tian, Z., Gao, Y., Du, S. *Cog-RAG: Cognitive-Inspired Dual-Hypergraph with Theme Alignment Retrieval-Augmented Generation.* AAAI 2026, 40(37):31032–31040; arXiv:2511.13201. https://arxiv.org/abs/2511.13201
- Hu, H. et al. *Cog-RAG.* Proceedings of the AAAI Conference on Artificial Intelligence. https://ojs.aaai.org/index.php/AAAI/article/view/40363
- Sharma, K., Kumar, P., Li, Y. *OG-RAG: Ontology-Grounded Retrieval-Augmented Generation For Large Language Models.* arXiv:2412.15235, 12 Dec 2024. https://arxiv.org/abs/2412.15235
- Wu, K., Kuai, C., Li, Z. et al. *Knowledge Is Not Static: Order-Aware Hypergraph RAG for Language Models.* arXiv:2604.12185, 14 Apr 2026. https://arxiv.org/abs/2604.12185
- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. *Hyper-KGGen: A Skill-Driven Knowledge Extractor for High-Quality Knowledge Hypergraph Generation.* arXiv:2602.19543, 23 Feb 2026. https://arxiv.org/abs/2602.19543
- Xiang, Z., Wu, C., Zhang, Q., Chen, S., Hong, Z., Huang, X., Su, J. *When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation.* ICLR 2026; arXiv:2506.05690 (v3, 22 Feb 2026). https://arxiv.org/abs/2506.05690
- GraphRAG-Bench. *GraphRAG-Benchmark*, GitHub, checked 2026-09-20. https://github.com/GraphRAG-Bench/GraphRAG-Benchmark
