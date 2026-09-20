---
title: LLMs and knowledge hypergraphs — querying, retrieval, memory
type: survey
status: draft
tags: [llm, rag, hypergraphrag, hyper-rag, hyperrag, proh, hypermem, text-to-sparql, text-to-typeql, retrieval, memory, benchmarks]
created: 2026-09-20
updated: 2026-09-20
---

# LLMs and knowledge hypergraphs — querying, retrieval, memory

Four distinct interactions, often conflated:

1. **LLM writes the query** — natural language to SPARQL / TypeQL / Cypher.
2. **KHG feeds the LLM** — hypergraph-structured retrieval-augmented generation (the busiest line
   of work, 2025–2026).
3. **KHG *is* the LLM's memory** — persistent n-ary state across a conversation or an agent's life.
4. **LLM reasons *about* the hypergraph** — serialisation protocols, benchmarks, and whether an LLM
   can do link prediction on n-ary facts at all.

Construction of the hypergraph itself is a different question, covered in
[llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md) and
[n-ary-relation-extraction-from-text.md](../03-construction/n-ary-relation-extraction-from-text.md).

---

## 1. LLM writes the query

**Text-to-SPARQL** is the mature case. There are benchmarks — Spider4SPARQL adapts the Spider
text-to-SQL benchmark to knowledge graphs ([Kosten, Cudré-Mauroux and Stockinger,
*Spider4SPARQL: A Complex Benchmark for Evaluating Knowledge Graph Question Answering Systems*,
IEEE BigData 2023 / arXiv:2309.16248](https://arxiv.org/abs/2309.16248)) — and evaluations of
neural SPARQL generation ([Diallo, Reyd and Zouaq, *A Comprehensive Evaluation of Neural SPARQL
Query Generation from Natural Language Questions*,
arXiv:2304.07772, 2023](https://arxiv.org/abs/2304.07772)), plus work on the specific failure mode
of hallucinated IRIs ([Sharma, Pal and Zouaq, *Reducing Hallucinations in Language Model-based
SPARQL Query Generation Using Post-Generation Memory Retrieval*, arXiv:2502.13369,
2025](https://arxiv.org/abs/2502.13369)).

Three things change when the target is an n-ary store:

- **The schema is the hard part, not the syntax.** Generating `delivery (deliverer: $c, delivered:
  $o)` requires knowing that `delivery` has those roles. Role names are the equivalent of column
  names in text-to-SQL, and there are far more of them (JF17K: 501 roles; WD50K: 531).
- **TypeQL's partial-tuple semantics is a generation trap.** Omitting a role *widens* the match
  ([query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md) §3), so an LLM that
  drops a role it is unsure about silently returns a superset rather than failing. This is the
  opposite of SQL, where an omitted join narrows nothing and an omitted predicate is visible.
- **No text-to-TypeQL benchmark exists.** As of September 2026 no public benchmark analogous to
  Spider4SPARQL was found for TypeQL or for any n-ary query language. `[unverified — absence of
  evidence]`

SPARQL 1.2's triple terms add new syntax that pre-2026 models have not seen in training; expect
generation quality on `<<( … )>>` and `{| … |}` to lag the rest of the language.

## 2. KHG-augmented generation

The thesis of this whole line: GraphRAG's binary edges lose the fact. "Previous GraphRAG methods are
limited by binary relations where one edge only connects two entities, which cannot well model
n-ary relations among more than two entities" ([Luo, E, Chen, Zheng, Wu, Guo, Lin, Feng, Kuang, Song,
Zhu and Tuan, *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge
Representation*, NeurIPS 2025 / arXiv:2503.21322](https://arxiv.org/abs/2503.21322)).

### The systems, in order

| System | Date | Venue | Core move |
|---|---|---|---|
| **HyperGraphRAG** | Mar 2025 | NeurIPS 2025 | represent n-ary facts as hyperedges; a full pipeline of hypergraph construction + hypergraph retrieval + hypergraph-guided generation |
| **Hyper-RAG** | Mar 2025 | *Nature Communications*, 27 Apr 2026 | hypergraph-driven retrieval aimed specifically at hallucination reduction, evaluated in medicine |
| **Cross-Granularity Hypergraph RAG** | Aug 2025 | arXiv | multi-hop QA across granularities of hyperedge |
| **PRoH** | Oct 2025 | WWW 2026 | dynamic *planning* over the hypergraph rather than static retrieval |
| **HyperGraphPro** | Jan 2026 | arXiv (in progress) | progress-aware RL for structure-guided hypergraph RAG |
| **HyperRAG** | Feb 2026 | WWW 2026 | reasoning over n-ary facts with two retrievers: structural-semantic and memory-guided beam search |

**HyperGraphRAG** (code <https://github.com/LHRLAB/HyperGraphRAG>) is the reference implementation
and the baseline everyone else reports against; experiments span medicine, agriculture, computer
science and law.

**Hyper-RAG** ([Feng, Hu, Hou, Liu, Ying, Du, Hu and Gao, arXiv:2504.08758, 2025;
*Nature Communications*, 2026](https://arxiv.org/abs/2504.08758),
[doi:10.1038/s41467-026-71411-1](https://doi.org/10.1038/s41467-026-71411-1); code
<https://github.com/iMoonLab/Hyper-RAG>) frames the same structure as a hallucination remedy. Its
publication in a general-science venue is itself a signal that the idea has left the graph-ML niche.

**PRoH** is the sharpest critique of the first generation. It names three limitations of KH-based
RAG — "static retrieval planning, non-adaptive retrieval execution, and superficial use of KH
structure and semantics" — and answers with (i) a context-aware planner that sketches the local
hypergraph neighbourhood before planning, (ii) question decomposition into a *dynamically evolving
DAG* of subquestions, and (iii) an Entity-Weighted Overlap-guided path retrieval that "prioritizes
semantically coherent hyperedge traversals". Reported gains over HyperGraphRAG: **+19.73% F1 and
+8.41% Generation Evaluation score on average** ([Zai, Tan, Wang, Liu, Xu and Zhang, *PRoH: Dynamic
Planning and Reasoning over Knowledge Hypergraphs for Retrieval-Augmented Generation*, WWW 2026 /
arXiv:2510.12434](https://arxiv.org/abs/2510.12434)).

**HyperRAG** (2026) argues the structural benefit explicitly: "n-ary hypergraphs encode higher-order
relational facts that capture richer inter-entity dependencies and enable **shallower, more
efficient reasoning paths**", and offers two retrieval variants — *HyperRetriever* (structural-
semantic reasoning over n-ary facts) and *HyperMemory* (language-model memory guiding a beam
search) — evaluated on WikiTopics and open-domain QA ([Lien, Chan, Hsiao, Ruan, Chiang, Chen, Yeh and
Shuai, arXiv:2602.14470, WWW 2026](https://arxiv.org/abs/2602.14470)).

### The retrieval strategies, abstracted

Across these systems the retrieval design space has four axes:

1. **Unit of retrieval** — entity, hyperedge (n-ary fact), hyperedge neighbourhood, or a hyperpath.
2. **Entry point** — vector similarity on entity/hyperedge text, or an LLM-planned entry.
3. **Expansion** — one-hop incidence, s-walk ([hypergraph-algorithms-for-knowledge.md](hypergraph-algorithms-for-knowledge.md)),
   beam search over hyperedges, or DAG-structured subquestion exploration (PRoH).
4. **Stopping** — fixed budget, planner-decided (PRoH), or RL-learned (HyperGraphPro).

The recurring empirical claim — that hyperedges shorten reasoning paths relative to triples — is
plausible and consistently reported, but it has not been isolated from the confound that
hypergraph pipelines also extract *more* facts per document. `[unverified]` as a controlled result.

## 3. KHG as LLM memory

**HyperMem** uses a hypergraph as the memory of a long-running conversation ([Yue, Hu, Sheng, Zhou,
Zhang, Liu, Guo and Deng, *HyperMem: Hypergraph Memory for Long-Term Conversations*, ACL 2026 main /
arXiv:2604.08256](https://arxiv.org/abs/2604.08256)). The fit is natural: a remembered episode is
inherently n-ary (who, what, when, where, with whom, why), and storing it as a hyperedge avoids the
decomposition that makes triple-based memory lose the binding between participants.

The open design question is *forgetting*: hypergraph memory grows monotonically unless there is a
decay or consolidation policy, and none of the current systems specify one.

## 4. LLMs reasoning about hypergraph structure

**Serialisation is the bottleneck.** An LLM reads a sequence; a hypergraph is not one. Three 2025–2026
answers:

- **HyperG** — "current approaches for applying LLMs to structured data fall into two main
  categories: serialization-based and operation-based methods", and both struggle to capture
  structure and handle sparsity ([Huang, Li, Gu, Hu, Li and Xu, *HyperG: Hypergraph-Enhanced LLMs
  for Structured Knowledge*, arXiv:2502.18125, 2025](https://arxiv.org/abs/2502.18125)).
- **Hypergraph as Language** (Hyper-Align) proposes a concrete input protocol: the **Hypergraph
  Incidence Detail Template with Overview (HIDT-O)** serialises high-order structure into a
  fixed-shape hybrid of local incidence detail and overview summary, and a **Hypergraph Incidence
  Projector (HIP)** maps native incidence structure into the LLM token space with explicit
  semantic–structural decoupling and bidirectional vertex↔hyperedge message passing; hypergraph
  tokens and text prompts are fed jointly to a frozen base model, supporting vertex-level and
  hyperedge-level tasks in one QA format. It introduces **HyperAlign-Bench**
  ([Lei, Xie, Ying, Du, Yong, Shi, Tian, Li and Gao, *Hypergraph as Language*, arXiv:2605.21858, 21
  May 2026](https://arxiv.org/abs/2605.21858)).
- **HyperGVL** benchmarks vision-language models on hypergraph understanding and reasoning
  ([arXiv:2604.15648, 2026](https://arxiv.org/abs/2604.15648)).

**LLMs still do not do n-ary link prediction.** As of mid-2025 the field's own survey states: "to
the best of our knowledge, LLMs have not been applied to link prediction in NKGs", citing two
obstacles — "(1) converting structured n-ary facts into formats compatible with LLMs, and (2)
overcoming input length limitations that hinder simultaneous processing of all candidate entities"
([Wei, Guan, Li, Jin, Guo and Cheng, arXiv:2506.08970,
2025](https://arxiv.org/abs/2506.08970) §6.1). The contrast with the RAG line is stark: LLMs are used
*over* knowledge hypergraphs constantly and *inside* the completion task not at all. Obstacle (1) is
exactly what HIDT-O and HIP attack, so the gap may close from that direction.

## 5. What to take from this

- For **answering questions over documents**, hypergraph RAG is now a real option with a reference
  implementation and a critique-and-improve cycle already running (HyperGraphRAG → PRoH → HyperRAG).
- For **querying a curated KHG**, the LLM's job is schema grounding, and the schema — the role
  vocabulary — is what you must surface in the prompt.
- For **completing a KHG**, LLMs are not yet competitive, and the reason is representational, not
  about model capability.

## Open questions raised here

- Is the "shallower reasoning paths" claim real when fact count is held constant?
- What is the right serialisation of an n-ary fact for an LLM — role-labelled JSON, a sentence, or a
  learned projection (HIP)? HyperAlign-Bench is the first instrument for answering this.
- Can an LLM be given a *hyperedge-level* retrieval API (incidence, s-walk, hyperpath) as tools,
  instead of a flat text index?
- What does forgetting look like in a hypergraph memory?
- Does the SPARQL 1.2 triple-term syntax need a dedicated generation benchmark before models can
  write it reliably?

## Sources

- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., Feng, Y., Kuang, Z., Song, M., Zhu, Y., Tuan, L. A. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation*. NeurIPS 2025; arXiv:2503.21322. <https://arxiv.org/abs/2503.21322> · code <https://github.com/LHRLAB/HyperGraphRAG>
- Feng, Y., Hu, H., Hou, X., Liu, S., Ying, S., Du, S., Hu, H., Gao, Y. *Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation*. arXiv:2504.08758, 2025; *Nature Communications*, 27 April 2026. <https://arxiv.org/abs/2504.08758> · <https://doi.org/10.1038/s41467-026-71411-1> · code <https://github.com/iMoonLab/Hyper-RAG>
- Zai, X., Tan, X., Wang, X., Liu, Q., Xu, X., Zhang, W. *PRoH: Dynamic Planning and Reasoning over Knowledge Hypergraphs for Retrieval-Augmented Generation*. The Web Conference 2026; arXiv:2510.12434. <https://arxiv.org/abs/2510.12434>
- Lien, W.-S., Chan, Y.-K., Hsiao, H.-L., Ruan, B.-K., Chiang, M.-F., Chen, C.-A., Yeh, Y.-R., Shuai, H.-H. *HyperRAG: Reasoning N-ary Facts over Hypergraphs for Retrieval Augmented Generation*. The Web Conference 2026; arXiv:2602.14470, 16 February 2026. <https://arxiv.org/abs/2602.14470>
- Park, J., Lee, S., Khan, O. Z., Kim, H. J., Kim, J.-K. *HyperGraphPro: Progress-Aware Reinforcement Learning for Structure-Guided Hypergraph RAG*. arXiv:2601.17755, 2026. <https://arxiv.org/abs/2601.17755>
- Wang, C., Deng, W., Guan, W., Lu, Q., Jiang, N. *Cross-Granularity Hypergraph Retrieval-Augmented Generation for Multi-hop Question Answering*. arXiv:2508.11247, 2025. <https://arxiv.org/abs/2508.11247>
- Yue, J., Hu, C., Sheng, J., Zhou, Z., Zhang, W., Liu, T., Guo, L., Deng, Y. *HyperMem: Hypergraph Memory for Long-Term Conversations*. ACL 2026 main; arXiv:2604.08256. <https://arxiv.org/abs/2604.08256>
- Lei, M., Xie, G., Ying, S., Du, S., Yong, J.-H., Shi, C., Tian, L., Li, S., Gao, Y. *Hypergraph as Language*. arXiv:2605.21858, 21 May 2026 (v2, 15 August 2026). <https://arxiv.org/abs/2605.21858>
- Huang, S., Li, H., Gu, Y., Hu, X., Li, Q., Xu, G. *HyperG: Hypergraph-Enhanced LLMs for Structured Knowledge*. arXiv:2502.18125, 2025. <https://arxiv.org/abs/2502.18125>
- *HyperGVL: Benchmarking and Improving Large Vision-Language Models in Hypergraph Understanding and Reasoning*. arXiv:2604.15648, 2026. <https://arxiv.org/abs/2604.15648>
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs*. arXiv:2506.08970, 2025; EMNLP 2025. <https://arxiv.org/abs/2506.08970>
- Kosten, C., Cudré-Mauroux, P., Stockinger, K. *Spider4SPARQL: A Complex Benchmark for Evaluating Knowledge Graph Question Answering Systems*. IEEE BigData 2023; arXiv:2309.16248. <https://arxiv.org/abs/2309.16248>
- Diallo, P. A. K. K., Reyd, S., Zouaq, A. *A Comprehensive Evaluation of Neural SPARQL Query Generation from Natural Language Questions*. arXiv:2304.07772, 2023. <https://arxiv.org/abs/2304.07772>
- Sharma, A., Pal, C. J., Zouaq, A. *Reducing Hallucinations in Language Model-based SPARQL Query Generation Using Post-Generation Memory Retrieval*. arXiv:2502.13369, 2025. <https://arxiv.org/abs/2502.13369>
