---
title: The composed stack — how the frontier directions fit together, and the bets they imply
type: survey
status: draft
tags: [frontier, synthesis, stack, foundation-model, extraction, retrieval, agent-memory, temporal, evaluation, research-agenda, run-02]
created: 2026-09-21
updated: 2026-09-21
---

# The composed stack — how the frontier directions fit together, and the bets they imply

[current-frontier-directions.md](current-frontier-directions.md) lists fifteen directions side by
side. This note takes a different cut, produced by the second research pass (2026-09-21): it arranges
the directions as **layers of one system that nobody has built**, asks which layers each published
system actually implements, and ranks the experiments that would tell us whether the layers compose.
Most of it is synthesis and opinion; where it states a result, the result is cited and lives in the
note linked.

The organising claim, which is the through-line of the 2025–2026 literature: the field's question
has moved from *"can we embed n-ary facts?"* (answered, with caveats, by HypE/HSimplE around
2019–2020; see [machine-learning-era.md](machine-learning-era.md)) to *"can one system invent,
store, retrieve, complete and reason over n-ary structure it has never seen, while talking to a
language model and an agent loop?"* That question splits into layers.

---

## 1. The stack

```
documents / tools / sensors / conversations
        │
        ▼
[A] extractor with evolving skills            Hyper-KGGen, Hyper-Extract, HyperGraphRAG's prompt
        │   n-ary facts + roles + time + provenance
        ▼
[B] living knowledge-hypergraph store          bipartite + vector index today; HIF; (future) valid-time index
        │
        ├─► [C] inductive completer             HYPER / HCNet / THOR    (fill the holes extraction left)
        ├─► [D] algebraic view                  ReAlE-style operators   (project, join, rename on facts)
        └─► [E] planner / walker                PRoH, EvoGraph-R1       (decompose, traverse, backtrack)
                    │
                    ▼
[F] LLM generator + agent actions              HyperMem, HyperSkill, DocTrace
                    │
                    └── [G] edits and skills flow back into [A] and [B]
```

Which published system implements which layer (an "x" means the paper builds and evaluates that
layer; "prompt" means it is a fixed prompt or heuristic; "—" means absent):

| System | A extract | B store | C complete | D algebra | E plan/walk | F generate/act | G write-back |
|---|---|---|---|---|---|---|---|
| HyperGraphRAG ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)) | prompt | x (bipartite + 2 vector indexes) | — | — | kNN + expansion | x | — |
| Hyper-RAG ([Feng et al., 2025](https://arxiv.org/abs/2504.08758)) | prompt | x | — | — | kNN, low/high-order | x | — |
| PRoH ([Zai et al., 2026](https://arxiv.org/abs/2510.12434)) | reuses | reuses | — | — | x (planning, DAG, EWO) | x | — |
| Hyper-KGGen ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)) | x (skills) | x | — | — | simple | x (to show A matters) | skills only |
| HYPER ([Huang et al., 2025](https://arxiv.org/abs/2506.12362), ICLR 2026) | — | gold graphs | x | — | — | — | — |
| ReAlE ([Fatemi et al., 2021](https://arxiv.org/abs/2102.09557)) | — | gold graphs | x | x (in embedding space) | — | — | — |
| HyperMem ([Yue et al., 2026](https://arxiv.org/abs/2604.08256)) | prompt | x (topics/episodes/facts) | — | — | retrieval | x | — |
| HyperSkill ([Xu et al., 2026](https://arxiv.org/abs/2608.16114)) | trajectories | x (skills as hyperedges) | — | — | dual-path retrieval | x | x (merge/prune) |
| EvoGraph-R1 ([Lin et al., 2026](https://arxiv.org/abs/2607.12764)) | prompt | x (multimodal) | — | — | x (RL agent) | x | x (GraphEdit) |

Every row implements two or three layers and treats the rest as prompt engineering or as given.
Two cells are empty in every row: nobody runs a completer (C) over an *extracted* store, and nobody
exposes algebra (D) to a planner (E). Those two empty columns are where this note's first two bets
sit (§4).

The layer notes: A is [../03-construction/llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md)
and [../03-construction/skill-driven-extraction-and-the-scenario-gap.md](../03-construction/skill-driven-extraction-and-the-scenario-gap.md);
B is [../04-storage-and-formats/vector-stores-and-hybrid-storage-for-rag.md](../04-storage-and-formats/vector-stores-and-hybrid-storage-for-rag.md);
C is [../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md](../05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md)
and [../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md);
D is [../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md);
E is [../07-applications/hierarchical-and-planned-hypergraph-retrieval.md](../07-applications/hierarchical-and-planned-hypergraph-retrieval.md);
F and G are [../07-applications/ai-agents-memory-and-planning.md](../07-applications/ai-agents-memory-and-planning.md)
and [../07-applications/temporal-hyperedges-and-editable-agent-memory.md](../07-applications/temporal-hyperedges-and-editable-agent-memory.md).

---

## 2. What each layer's own literature has established

Stated as results, each with the note that holds the evidence.

- **Native hypergraph message passing is an inductive bias, not a convenience.** Reifying a
  hypergraph and running a binary KG foundation model on it loses to HYPER, and pretraining that
  model on 50 graphs instead of 3 makes it *worse* (the ICLR 2026 revision reversed the preprint's
  "marginally better"), because reified graphs are tripartite structures the pretraining corpus never
  contained ([Huang et al., 2025](https://arxiv.org/abs/2506.12362) §5.2;
  [inductive-and-few-shot-settings.md](../05-query-embeddings-reasoning/inductive-and-few-shot-settings.md) §3).
  This is the strongest published argument that layer C must be hypergraph-native.
- **Domain diversity beats volume for hypergraph pretraining.** Hyper-FM's scaling law and HYPER's
  mixture ablation (3 KGs + 2 hypergraphs beats 50 KGs) say the same thing in different dialects
  ([Gao et al., 2025](https://arxiv.org/abs/2503.01203); [Huang et al., 2025](https://arxiv.org/abs/2506.12362);
  [current-frontier-directions.md](current-frontier-directions.md) §1). Neither has been replicated
  on an independent corpus (open question [08.2]).
- **How you traverse matters more than that you stored n-ary facts.** PRoH's lift over
  HyperGraphRAG, and its larger lift on 3–6-hop questions, is the first clear evidence that layer E
  is where retrieval quality is decided ([Zai et al., 2026](https://arxiv.org/abs/2510.12434);
  [retrieval-augmented-generation.md](../07-applications/retrieval-augmented-generation.md) §5 and §7,
  which also records that the comparison is on the authors' own benchmark).
- **Extraction quality is the product.** Hyper-KGGen shows downstream answer quality tracking
  extraction quality with a simple retriever held fixed
  ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)); the critical literature independently
  names LLM extraction as the weak link ([current-frontier-directions.md](current-frontier-directions.md) §13).
- **Binary encoding of a fact of arity ≥ 3 is information-lossy; a bipartite store of the
  hypergraph is not.** HyperGraphRAG's propositions ([Luo et al., 2025](https://arxiv.org/abs/2503.21322))
  license hyperedges as *storage*; they say nothing about whether a given corpus has enough
  high-arity facts for it to matter. The engineering question is the arity histogram of *your*
  atomic facts, and the measured histograms are skewed to binary
  ([../10-comparative-and-critique/limitations-and-failure-modes.md](../10-comparative-and-critique/limitations-and-failure-modes.md) §1).
- **Embeddings can implement relational algebra.** ReAlE represents renaming, projection, union,
  selection and set difference in embedding space with a full-expressivity proof
  ([Fatemi et al., 2021](https://arxiv.org/abs/2102.09557)). No retrieval or planning system uses
  it; the planner speaks English and the store answers in cosine similarity.
- **Grouped memory beats per-episode rows, on the authors' benchmarks.** HyperMem, HyperSkill and
  DocTrace agree, and none ablates against "store the whole episode as one chunk"
  ([ai-agents-memory-and-planning.md](../07-applications/ai-agents-memory-and-planning.md) §5).
- **Time is still a slot.** The temporal n-ary models (HyNT, NE-Net, HypeTKG, VITA) treat time as an
  argument or attribute; none carries valid-time on the hyperedge with supersession semantics, and
  the bitemporal model that agent memory already uses for binary facts (Graphiti/Zep,
  [Rasmussen et al., 2025](https://arxiv.org/abs/2501.13956)) has not been lifted to n-ary events
  ([temporal-and-dynamic-khgs.md](../05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md) §5).

---

## 3. Where evaluation is lying

Reported scores mix four abilities that live in different layers, and papers report one or two
while implying the rest:

| Ability | Layer | Where it is measured today | What is wrong with the measurement |
|---|---|---|---|
| 1. Extract the right n-ary fact | A | HyperDocRED ([Huang et al., 2026](https://arxiv.org/abs/2602.19543)) | One dataset, one annotation protocol; no inter-annotator agreement by arity (open question [03.6]) |
| 2. Complete a hole in a gold hypergraph | C | JF17K, WikiPeople, WD50K, HYPER's 16 inductive splits | JF17K leaks 44.5% of test triples ([Galkin et al., 2020](https://aclanthology.org/2020.emnlp-main.596/)); arity skewed to 2; no arity-stratified or calibration results ([../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md](../05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md)) |
| 3. Retrieve a useful event for a question | E | HyperGraphRAG / PRoH / Hyper-RAG domain sets | Corpora are LLM-extracted and LLM-judged; benchmarks self-built; no hypergraph system on GraphRAG-Bench ([../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md](../10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md)) |
| 4. Stay coherent over weeks | F/G | LoCoMo, LongMemEval | LLM-judged; no supersession-specific split reported for hypergraph systems |

The HYPER inductive splits (25/50/75/100% unseen relations, varying arity) are the first
systematic distribution-shift test for ability 2. There is no analogue for abilities 3 and 4. Until
one artefact carries all four, "hypergraphs beat graphs by X%" will keep meaning incompatible things
in different papers. A frontier evaluation suite would be:

1. gold n-ary document extraction (HyperDocRED-style), **plus**
2. inductive completion of the *extracted* graph (HYPER-style splits), **plus**
3. multi-hop questions that require one specific high-arity edge to be present and traversed, with
   that edge ablated (PRoH-style questions, project P4's ablation), **plus**
4. a time-evolving memory trace in which facts are superseded, scored on the superseded facts.

This is candidate project P8 in [../00-index/open-questions.md](../00-index/open-questions.md) Part C.

---

## 4. Seven bets, in the order the author of this note would take them

Opinion, but each bet names the experiment and the layer boundary it tests.

1. **Close the completion–retrieval gap (C × E).** Run PRoH over a hypergraph that HYPER has been
   allowed to complete, on an *extracted* rather than gold graph. If PRoH's lift survives, the
   substrate thesis holds on dirty data; if it collapses, extraction, not planning, is the
   bottleneck. Nobody has run a completer over an extracted store.
2. **Put valid-time on the hyperedge (B).** Not as a slot the language model may or may not notice:
   as an index with supersession semantics, following the bitemporal precedent for binary facts.
   Agent memory will force this regardless; see
   [temporal-hyperedges-and-editable-agent-memory.md](../07-applications/temporal-hyperedges-and-editable-agent-memory.md).
3. **Learn the walk (E).** Entity-weighted overlap is a heuristic. A traversal policy trained with
   answer-level reward over hyperedge sequences would be the NBFNet moment for hypergraph
   retrieval; EvoGraph-R1 is the first system in that direction, in the multimodal setting.
4. **Treat skills as typed hyperedges (A = G).** Hyper-KGGen's extraction skills and HyperSkill's
   procedural skills are the same object, a procedure that binds roles; today both are free text
   with no arity or role constraints.
5. **Pretrain on domain diversity, not dump size (C).** Both foundation-model papers already voted
   this way; the data strategy is many small, structurally different n-ary domains (clinical
   events, contracts, protocols, incident reports, multi-party conversations), not a bigger
   Freebase. No shared n-ary pretraining corpus exists (see the anatomy note).
6. **Role semantics, not slot indices (A, C, D).** Position 3 of one relation is not a universal
   concept; without roles, transfer across schemas is a coincidence of ordering. By headcount the
   two-axis taxonomy has *more* role-aware than position-aware models, but "role-aware" there means
   qualifier-aware, and every geometry or foundation model is position-aware; no model uses a
   linguistic role inventory. The evidence is in
   [geometry-and-algebraic-interfaces.md](../05-query-embeddings-reasoning/geometry-and-algebraic-interfaces.md).
   This is Theme 2 of the open-questions register.
7. **Cost as a first-class metric (all layers).** Dual conditional message passing plus multi-step
   planning does not ship; distilled walkers and approximate relation graphs are the productisation
   research. PRoH reports tokens only for its lightweight variant, HYPER costs 1.7× HCNet and 3.8×
   ULTRA per training batch in time, and no hypergraph-RAG paper plots accuracy against a token
   budget.

---

## 5. What this note changes in the rest of the base

- It adds one theme to the open-questions register: **composition** (do the layers compose, and
  where does quality leak between them?), with questions [08.6]–[08.9].
- It adds candidate project **P8**, the four-ability evaluation suite, and reframes **P7** (agent
  memory prototype) to include valid-time on the hyperedge.
- It does not change any result recorded elsewhere; where it disagrees with a note, the note wins
  and this file should be corrected.

## Open questions raised here

- **[08.6]** Does a planner's lift (PRoH over HyperGraphRAG) survive when the store is an extracted,
  incomplete hypergraph that an inductive completer has filled, rather than a gold or
  extraction-only graph? Layer C has never been run under layer E.
- **[08.7]** Can an embedding that implements relational algebra (ReAlE) serve as the query
  interface for an LLM planner, so that the planner emits operators rather than English, and does
  that beat cosine retrieval on multi-hop questions?
- **[08.8]** Is there a single artefact on which extraction, inductive completion, retrieval and
  long-horizon memory can all be scored, and what does the correlation between the four scores look
  like?
- **[08.9]** Do extraction skills and agent procedural skills unify as typed hyperedges with arity
  and role constraints, and does typing reduce the extraction instability that Hyper-KGGen's
  stability reward is designed to detect?

## Sources

- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., Feng, Y., Kuang, Z., Song, M., Zhu, Y., Luu, A. T. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* NeurIPS 2025; arXiv:2503.21322. <https://arxiv.org/abs/2503.21322>
- Feng, Y., Hu, H., Hou, X., Liu, S., Ying, S., Du, S., Hu, H., Gao, Y. *Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation.* arXiv:2504.08758, 2025; *Nature Communications* 2026. <https://arxiv.org/abs/2504.08758>
- Zai, X., Tan, X., Wang, X., Liu, Q., Xu, X., Zhang, W. *PRoH: Dynamic Planning and Reasoning over Knowledge Hypergraphs for Retrieval-Augmented Generation.* WWW 2026; arXiv:2510.12434. <https://arxiv.org/abs/2510.12434>
- Huang, R., Feng, Y., Xue, R., Ying, S., Yong, J.-H., Shi, C., Du, S., Gao, Y. *Hyper-KGGen: A Skill-Driven Framework for Knowledge Hypergraph Generation* (with HyperDocRED). arXiv:2602.19543, 2026. <https://arxiv.org/abs/2602.19543>
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. *HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs.* arXiv:2506.12362, 2025. <https://arxiv.org/abs/2506.12362>
- Gao, Y., Feng, Y., Liu, S., Han, X., Du, S., Wu, Z., Hu, H. *Hypergraph Foundation Model.* arXiv:2503.01203, 2025; IEEE TPAMI 2026. <https://arxiv.org/abs/2503.01203>
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraph Embedding Meets Relational Algebra.* arXiv:2102.09557, 2021. <https://arxiv.org/abs/2102.09557>
- Yue, J., Hu, C., Sheng, J., Zhou, Z., Zhang, W., Liu, T., Guo, L., Deng, Y. *HyperMem: Hypergraph Memory for Long-Term Conversations.* arXiv:2604.08256, 2026. <https://arxiv.org/abs/2604.08256>
- Xu, R., Yang, T., Huang, W.-C. *HyperSkill: Self-Evolving LLM Agents via Hypergraph-Structured Skill Memory.* arXiv:2608.16114, 2026. <https://arxiv.org/abs/2608.16114>
- Lin, J., Jiang, C., Lin, X., Zhang, R., Zhu, X., Liu, J. et al. *EvoGraph-R1: Self-Evolving Multimodal Knowledge Hypergraphs for Agentic Retrieval.* arXiv:2607.12764, 2026. <https://arxiv.org/abs/2607.12764>
- Rasmussen, P., Paliychuk, P., Beauvais, T., Ryan, J., Chalef, D. *Zep: A Temporal Knowledge Graph Architecture for Agent Memory.* arXiv:2501.13956, 2025. <https://arxiv.org/abs/2501.13956>
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs* (StarE). EMNLP 2020. <https://aclanthology.org/2020.emnlp-main.596/>
- Xiang, Z. et al. *When to use Graphs in RAG* (GraphRAG-Bench). ICLR 2026; arXiv:2506.05690. <https://arxiv.org/abs/2506.05690>
