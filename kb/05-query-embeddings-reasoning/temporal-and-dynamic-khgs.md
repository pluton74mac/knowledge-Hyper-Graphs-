---
title: Temporal and dynamic knowledge hypergraphs
type: survey
status: draft
tags: [temporal, dynamic, time, ne-net, hypetkg, hynt, numeric-literals, dhgnn, cat-walk, hyper-cores, forecasting, interpolation, extrapolation]
created: 2026-09-20
updated: 2026-09-20
---

# Temporal and dynamic knowledge hypergraphs

Time enters a knowledge hypergraph in three different ways, and conflating them is the main source
of confusion in this corner of the literature:

1. **Time as a role or qualifier** — `{winner: Einstein, award: Nobel Prize, place: Switzerland,
   time: 1921}`. The fact is static; time is one of its arguments.
2. **Time as a validity annotation** — the fact holds during an interval; the hypergraph is a
   sequence of snapshots and the task is forecasting.
3. **Time as structure evolution** — hyperedges appear and disappear; the object of study is the
   dynamics of the hypergraph itself.

The n-ary knowledge-graph literature works on (1) and (2); the hypergraph-learning literature works
on (3). They barely cite each other.

Companions: [knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md),
[benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md).

---

## 1. Why "time as just another role" is not enough

The survey's diagnosis: "many methods either ignore [temporal information] or treat time as a
generic role, blurring the distinction between relational and temporal semantics. Without explicit
temporal modeling, models fail to capture ordering, duration, and the influence of historical
patterns on future facts"
([Wei, Guan, Li, Jin, Guo and Cheng, arXiv:2506.08970, 2025](https://arxiv.org/abs/2506.08970) §3.4.1).

The three things lost are worth naming because they are exactly what an embedding of a timestamp
cannot recover: **ordering** (1921 < 1922 is not encoded by unrelated embeddings), **duration**
(an interval is not a point), and **history** (what happened before conditions what happens next).

## 2. Models

### HyNT (2023) — numbers, including dates, as first-class

HyNT is not billed as a temporal model, but it is the prerequisite for one. It encodes **numeric
literals** in both the primary triple and the qualifiers with a context transformer and a prediction
transformer, motivated by exactly the temporal case: "a number-related qualifier role-value pair
(starting time, 1911) is associated with a triple (J.R.R., educated at, Oxford University)"
([Chung, Lee and Whang, *Representation Learning on Hyper-Relational and Numeric Knowledge Graphs
with Transformers*, KDD 2023](https://doi.org/10.1145/3580305.3599490), arXiv:2305.18256; code
<https://github.com/bdi-lab/HyNT>; description from
[Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.3.3). Every model before it dropped
timestamps as unknown entities.

### NE-Net (2023) — evolution of entities under roles

NE-Net "leverages an entity-role encoder based on a GNN to capture precise entity evolution
representations" ([Hou, Jin, Li, Bai, Guan, Zeng, Guo and Cheng, *Temporal Knowledge Graph Reasoning
Based on N-tuple Modeling*, Findings of EMNLP
2023](https://doi.org/10.18653/v1/2023.findings-emnlp.77)). It contributes the **NWIKI** and
**NICE** datasets. Its structure is the n-ary analogue of the recurrent temporal-KG models: a
per-timestamp encoder plus an evolution mechanism across timestamps.

### HypeTKG (2023/2024) — time-invariant relations help temporal reasoning

HypeTKG's specific contribution is to model "the influence of time-invariant relations on temporal
reasoning" ([Ding, Wu, Wu, Xia and Tresp, *Temporal Fact Reasoning over Hyper-Relational Knowledge
Graphs*, Findings of EMNLP 2024 / arXiv:2307.10219,
2023](https://arxiv.org/abs/2307.10219)). The intuition: facts that never change (a person's
birthplace) are strong evidence when forecasting facts that do. It contributes **Wiki-hy** and
**YAGO-hy**, built by "identifying qualifying role-value pairs from Wikidata within the existing
Wikidata11k and YAGO1830 datasets"
([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §G.1.1).

## 3. Datasets and results

Benchmarks, from [Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 6:

| Dataset | #Entities | #Timestamps | Interval | N (n-ary %) | #Train | #Valid | #Test |
|---|---|---|---|---|---|---|---|
| NWIKI | 17,481 | 205 | 1 year | 81.9% | 108,397 | 14,370 | 15,591 |
| NICE | 10,860 | 4,017 | 24 hours | 97.5% | 368,868 | 5,268 | 46,159 |
| Wiki-hy | 11,140 | 507 | 1 year | 9.5% | 111,252 | 13,900 | 13,926 |
| YAGO-hy | 10,026 | 188 | 1 year | 6.9% | 51,193 | 10,973 | 10,977 |

Note the split in character: NWIKI/NICE are overwhelmingly n-ary (81.9%, 97.5%) at coarse and fine
time granularity respectively; Wiki-hy/YAGO-hy are mostly binary with a qualifier minority. They test
different things and results on them should not be pooled.

Results, from [Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 9 (MRR / Hits@1 / Hits@10;
NWIKI from Hou et al. 2023, Wiki-hy from Ding et al.):

| Method | Family | NWIKI | Wiki-hy |
|---|---|---|---|
| HINGE | n-ary, no time | 0.217 / 0.191 / 0.259 | 0.543 / 0.497 / 0.694 |
| HypE | n-ary, no time | 0.252 / 0.249 / 0.257 | 0.624 / 0.604 / 0.658 |
| DE-SimplE | temporal, binary | 0.138 / 0.108 / 0.191 | 0.351 / 0.218 / 0.640 |
| CEN | temporal, binary | 0.406 / 0.302 / 0.610 | — |
| TiGRN | temporal, binary | 0.611 / 0.506 / 0.811 | — |
| **NE-Net** | temporal, n-ary | **0.720 / 0.668 / 0.802** | — |
| **HypeTKG** | temporal, hyper-relational | — | **0.693 / 0.642 / 0.792** |

The reading the survey gives, and the table supports: **neither ingredient alone is sufficient.**
Temporal-but-binary models (DE-SimplE at 0.138 on NWIKI) and n-ary-but-atemporal models (HypE at
0.252) both lose heavily to models with both (NE-Net at 0.720). "Jointly modeling qualifier
role-value pairs and temporal evolution can significantly enhance predictive capability"
([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §G.3.1).

Caveat: the Wiki-hy column has HypE at 0.624 and HypeTKG at 0.693 — a much smaller margin, consistent
with Wiki-hy being only 9.5% n-ary.

## 4. The other literature: dynamic hypergraph learning

Separately from knowledge bases, a body of work studies hypergraphs whose structure changes.

- **DHGNN** learns the hypergraph structure itself during training rather than fixing it from
  features ([Jiang, Wei, Feng, Cao and Gao, *Dynamic Hypergraph Neural Networks*, IJCAI
  2019](https://doi.org/10.24963/ijcai.2019/366)).
- **CAT-Walk** does inductive hypergraph learning via *set walks* over temporal hypergraphs
  ([Behrouz, Hashemi, Sadeghian and Seltzer, *CAT-Walk: Inductive Hypergraph Learning via Set Walks*,
  NeurIPS 2023 / arXiv:2306.11147](https://arxiv.org/abs/2306.11147)).
- **Hyper-cores** give a structural lens on how temporal hypergraphs evolve
  ([Mancastroppa, Iacopini, Petri and Barrat, *The structural evolution of temporal hypergraphs
  through the lens of hyper-cores*, *EPJ Data Science* 13:50,
  2024](https://arxiv.org/abs/2402.06485)), and the same group provides a generative model of
  time-varying hypergraphs ([Mancastroppa, Cencetti and Barrat, *Emerging Activity Temporal
  Hypergraph*, *Phys. Rev. E* 112, 054305, 2025](https://arxiv.org/abs/2507.01124)).
- **Heterogeneous temporal hypergraph neural networks** extend the encoder side
  ([Liu, Jiao, Gao, Chen and Jin, IJCAI 2025 / arXiv:2506.17312](https://arxiv.org/abs/2506.17312)).
- **Higher-order temporal pattern prediction** ([Liu, Ma and Li, *Neural Predicting Higher-order
  Patterns in Temporal Networks*, arXiv:2106.06039, 2021](https://arxiv.org/abs/2106.06039)).

None of these carry relation or role labels, so they are to temporal KHGs what HGNNs are to
knowledge hypergraphs ([hypergraph-neural-networks.md](hypergraph-neural-networks.md) §3.3): the
right structural machinery, missing the semantics. CAT-Walk's set walks and the s-walks of
[hypergraph-algorithms-for-knowledge.md](hypergraph-algorithms-for-knowledge.md) §1 are close
cousins, and a role-aware temporal set walk looks like an obvious unexplored combination.

## 5. What the field says is missing

The survey's own list: temporal methods "overlook [the] local structure of n-ary facts", and for
growing knowledge bases "it is crucial to develop methods for growing NKGs that can adaptively learn
from new facts while retaining previously acquired knowledge"
([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §6.2). To which this note adds:

- **Intervals, not timestamps.** All four benchmarks discretise time into points. Validity intervals
  — the natural representation for "was CEO from 2011 to 2019" — are absent.
- **Two time dimensions.** Valid time and transaction time (when the KB learned the fact) are
  distinct and both matter for provenance; nothing here models both.
- **No temporal CQA.** Complex query answering over hyper-relational graphs
  ([logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md) §5)
  has no temporal variant that was found for this note. `[unverified — apparent gap]`

## Open questions raised here

- Is "time as a qualifier" ever sufficient, given HyNT's numeric encoding? That is, does an ordered
  numeric encoding of the time qualifier recover most of what a dedicated temporal architecture buys?
- Why is the temporal gain so much larger on NWIKI (81.9% n-ary) than on Wiki-hy (9.5% n-ary) — arity,
  or dataset construction?
- Could CAT-Walk-style temporal set walks be made role-aware and used directly for temporal n-ary
  link prediction?
- What would a benchmark with validity *intervals* rather than timestamps look like, and would
  current models degrade on it?

## Sources

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs*. arXiv:2506.08970, 2025; EMNLP 2025. <https://arxiv.org/abs/2506.08970>
- Chung, C., Lee, J., Whang, J. J. "Representation Learning on Hyper-Relational and Numeric Knowledge Graphs with Transformers" (HyNT). *KDD 2023*; arXiv:2305.18256. <https://doi.org/10.1145/3580305.3599490>
- Hou, Z., Jin, X., Li, Z., Bai, L., Guan, S., Zeng, Y., Guo, J., Cheng, X. "Temporal Knowledge Graph Reasoning Based on N-tuple Modeling" (NE-Net). *Findings of EMNLP 2023*. <https://doi.org/10.18653/v1/2023.findings-emnlp.77>
- Ding, Z., Wu, Jingcheng, Wu, Jingpei, Xia, Y., Tresp, V. *Temporal Fact Reasoning over Hyper-Relational Knowledge Graphs* (HypeTKG). Findings of EMNLP 2024; arXiv:2307.10219. <https://arxiv.org/abs/2307.10219>
- Jiang, J., Wei, Y., Feng, Y., Cao, J., Gao, Y. "Dynamic Hypergraph Neural Networks". *IJCAI 2019*. <https://doi.org/10.24963/ijcai.2019/366>
- Behrouz, A., Hashemi, F., Sadeghian, S., Seltzer, M. *CAT-Walk: Inductive Hypergraph Learning via Set Walks*. NeurIPS 2023; arXiv:2306.11147. <https://arxiv.org/abs/2306.11147>
- Mancastroppa, M., Iacopini, I., Petri, G., Barrat, A. *The structural evolution of temporal hypergraphs through the lens of hyper-cores*. *EPJ Data Science* 13:50, 2024; arXiv:2402.06485. <https://arxiv.org/abs/2402.06485>
- Mancastroppa, M., Cencetti, G., Barrat, A. *Emerging Activity Temporal Hypergraph: a model for generating realistic time-varying hypergraphs*. *Physical Review E* 112, 054305, 2025; arXiv:2507.01124. <https://arxiv.org/abs/2507.01124>
- Liu, H., Jiao, P., Gao, M., Chen, C., Jin, D. *Heterogeneous Temporal Hypergraph Neural Network*. IJCAI 2025; arXiv:2506.17312. <https://arxiv.org/abs/2506.17312>
- Liu, Y., Ma, J., Li, P. *Neural Predicting Higher-order Patterns in Temporal Networks*. arXiv:2106.06039, 2021. <https://arxiv.org/abs/2106.06039>
