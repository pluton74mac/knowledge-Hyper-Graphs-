---
title: Hypergraph neural networks and what they can express
type: survey
status: draft
tags: [hgnn, hypergcn, hnhn, unignn, allset, ed-hnn, hypergraph-transformer, expressivity, clique-expansion, star-expansion, hypertree-width, dhg, topox, pyg, dgl]
created: 2026-09-20
updated: 2026-09-20
---

# Hypergraph neural networks and what they can express

Hypergraph neural networks (HNNs / HGNNs) learn on hypergraphs *without* relation labels: vertices
carry features, hyperedges are unlabelled sets, and the task is node classification, hyperedge
prediction or graph-level regression. Knowledge-hypergraph embedding models
([knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md)) are the
labelled, role-aware cousins of these architectures, and since 2024 the two literatures have started
to converge — HYPER's encoder is an HNN, and the expressivity theory now covers both.

The structural background is in
[hypergraph-definitions.md](../01-foundations/hypergraph-definitions.md).

---

## 1. The design space in one picture

Every HNN makes two choices ([Kim, Lee, Gao, Antelmi, Polato and Shin, *A Survey on Hypergraph Neural
Networks: An In-Depth and Step-By-Step Guide*, KDD 2024 / arXiv:2404.01039](https://arxiv.org/abs/2404.01039), §3):

**(a) How is the hypergraph structure expressed?**

- **Reductive — clique expansion.** Each hyperedge becomes a clique. This "enables the direct
  application of methods developed for graphs, such as spectral filters", but "may result in
  information loss, and the original hypergraph structure may not be precisely recovered after
  transformation". The survey's own counterexample: the hypergraph `{v₁v₂v₃}` and the hypergraph
  `{v₁v₂v₃}, {v₁v₃}, {v₂v₃}` have the same *unweighted* clique expansion — hence "assigning proper
  edge weights is crucial". Typical weighting divides by hyperedge size,
  `a_ij = Σ_{e_k} δ(v_i, v_j, e_k)/|e_k|`.
- **Reductive — adaptive expansion.** Add only some intra-clique edges, chosen per task (HyperGCN,
  AdE).
- **Non-reductive — star expansion.** The bipartite incidence graph between vertices and hyperedges.
  Lossless: "the hyperedges ℰ can be exactly recovered after transformation." Also line expansion
  and tensor representations.

**(b) What messages flow?**

- **Hyperedge-consistent messages** — the same vertex embedding is sent to every incident hyperedge
  (UniGNN, AllSet, ED-HNN).
- **Hyperedge-dependent messages** — a vertex sends a *different* message to each hyperedge it
  belongs to, on the argument that "the role or importance of a node may vary across the hyperedges
  it belongs to" (WHATsNet, MultiSetMixer). This is the unlabelled analogue of the *role* in a
  knowledge hypergraph.

## 2. Chronology

| Model | Year | Venue | Core idea |
|---|---|---|---|
| HGNN | 2019 | AAAI | spectral convolution on the (weighted) clique expansion via the hypergraph Laplacian |
| HyperGCN | 2019 | NeurIPS | replace each hyperedge by a *single* mediator-augmented edge chosen per layer (adaptive expansion) |
| HNHN | 2020 | ICML workshop | give hyperedges their own neurons and nonlinearity; alternate vertex→edge and edge→vertex updates |
| UniGNN | 2021 | IJCAI | one framework unifying GCN/GAT/GIN/GraphSAGE over both graphs and hypergraphs |
| AllSet | 2022 | ICLR | an HNN layer *is* a composition of two learnable **multiset** functions |
| ED-HNN | 2023 | ICLR | provably approximate any continuous equivariant hypergraph diffusion operator |
| HGNN⁺ | 2022 | TPAMI | general hypergraph modelling with hyperedge groups |
| EHNN, HO-Transformer, WHATsNet, PhenomNN, HyperND | 2021–2023 | ECCV / NeurIPS / KDD / ICML | tensor, attention, and diffusion-flavoured variants |

Venues and years from the survey's Table 1 ([Kim et al.
2024](https://arxiv.org/abs/2404.01039)); HNHN's reference there is *"ICML Workshop: Graph
Representation Learning and Beyond"*.

### HGNN (Feng, You, Zhang, Ji and Gao, AAAI 2019)

The first widely used design: build a hypergraph incidence matrix H, form a normalised hypergraph
Laplacian, and run a spectral convolution. Effectively clique expansion with principled weights
([doi:10.1609/aaai.v33i01.33013558](https://doi.org/10.1609/aaai.v33i01.33013558)).

### HyperGCN (Yadati, Nimishakavi, Yadav, Nitin, Louis and Talukdar, NeurIPS 2019)

Instead of expanding a hyperedge into a full clique, pick, per layer, the pair of vertices in the
hyperedge that are furthest apart in the current embedding (plus mediators) and connect those. This
is a *Laplacian for hypergraphs* argument rather than a GNN engineering trick
([arXiv:1809.02589](https://arxiv.org/abs/1809.02589)).

### HNHN (Dong, Sawin and Bengio, 2020)

Hyperedges get their own hidden representations and nonlinearities, and the layer alternates
vertex→hyperedge and hyperedge→vertex updates with degree-based normalisation — i.e. message passing
on the star expansion ([arXiv:2006.12278](https://arxiv.org/abs/2006.12278)).

### UniGNN (Huang and Yang, IJCAI 2021)

Observes that a hypergraph layer is two aggregations — constituent vertices into a hyperedge, then
incident hyperedges into a vertex — and that every standard GNN can be lifted this way. UniGIN, for
instance ([Kim et al. 2024](https://arxiv.org/abs/2404.01039), Eq. 12):

```
q_j^(ℓ)  = Σ_{v_l ∈ e_j} p_l^(ℓ-1)
p_i^(ℓ)  = ( (1+ε) p_i^(ℓ-1) + Σ_{e_l ∈ N_ℰ(v_i)} q_l^(ℓ) ) Θ^(ℓ)
```

([doi:10.24963/ijcai.2021/353](https://doi.org/10.24963/ijcai.2021/353)).

### AllSet (Chien, Pan, Peng and Milenkovic, ICLR 2022)

The conceptual clean-up: an HNN layer is exactly a composition of two **multiset functions**,
one vertex-set→hyperedge and one hyperedge-set→vertex, "that can be efficiently learned for each
task and each dataset". Instantiating them with Deep Sets gives AllDeepSets; with a Set Transformer,
AllSetTransformer ([arXiv:2106.13264](https://arxiv.org/abs/2106.13264); code
<https://github.com/jianhao2016/AllSet>). Most later HNNs are special cases.

### ED-HNN (Wang, Yang, Liu, Wang and Li, ICLR 2023)

Starts from hypergraph **diffusion** rather than from GNNs: the architecture "provably approximates
any continuous equivariant hypergraph diffusion operators that can model a wide range of higher-order
relations", and is implemented by combining star expansions with standard message passing. Reported
uniformly state-of-the-art over nine datasets at publication
([OpenReview](https://openreview.net/pdf?id=RiTjKoscnNd); code
<https://github.com/Graph-COM/ED-HNN>).

### Hypergraph transformers

Two distinct things go by this name: (i) attention *within* a hyperedge over its members
(AllSetTransformer, and in the knowledge setting GRAN and HAHE), and (ii) attention over the whole
hypergraph with structural encodings (HO-Transformer, EHNN). The knowledge-hypergraph literature
arrived at the same architecture independently — GRAN's edge-type-biased attention over a fact's
elements is a hypergraph transformer over a single hyperedge.

## 3. Expressivity

### 3.1 The relational side: HCNets and relational Weisfeiler-Leman

For *labelled, positional* hyperedges — i.e. knowledge hypergraphs — Huang et al. lift conditional
message passing to k-ary relations and characterise the resulting models "via corresponding
relational Weisfeiler-Leman algorithms and also via logical expressiveness"
([Huang, Romero Orth, Barceló, Bronstein and Ceylan, *Link Prediction with Relational Hypergraphs*,
TMLR 2025 / arXiv:2402.04062](https://arxiv.org/abs/2402.04062)). HCNet, the architecture from that
paper, is the encoder HYPER builds on ([Huang, Galkin, Bronstein and Ceylan,
arXiv:2506.12362](https://arxiv.org/abs/2506.12362)).

### 3.2 The unlabelled side: the Width Wall (2026)

The sharpest general result to date. Jiang et al. measure expressivity by **homomorphism densities**
— how often a pattern occurs — and index the achievable invariants by the **generalized hypertree
width** of the pattern, `W_gh(F)`, defined as "the minimum over all tree decompositions of F of the
maximum number of hyperedges of F needed to cover any single bag"
([Jiang, Li, Feng, Zheng, Niu, Ramasubramanian, Alomair, Bushnell and Poovendran, *The
WidthWall: A Strict Expressivity Hierarchy for Hypergraph Neural Networks*, arXiv:2605.13690,
13 May 2026](https://arxiv.org/abs/2605.13690), Definition 3.3; the paper's body renders the title
as "The Width Wall").
Three classes are defined (Definition 3.4): `I_CE` — invariants computable from the clique expansion;
`I_NH^(R)` — those plus hypergraph pattern densities of width ≤ R; `I_all` — all continuous
hypergraph invariants.

> **Theorem 3.6 (strict expressivity hierarchy).** Fix a native-incidence reference class with width
> budget R ≥ 3. For k-uniform hypergraphs with k ≥ 3 on n ≥ max{13, N_CFI^(k)(R)} vertices,
> `I_CE ⊊ I_NH^(R) ⊊ I_all`.
>
> **Theorem 3.7 (infinite hierarchy).** With `H_r` the invariants approximable from patterns of
> generalized hypertree width ≤ r, for every r ≥ 1, k ≥ 3 and n ≥ N_CFI^(k)(r): `H_r ⊊ H_{r+1}`.

The separations are witnessed by Cai–Furer–Immerman constructions. The name comes from Definition
3.5: "Once an architecture exposes only width-r coordinates, no increase in hidden dimension,
readout complexity, or training can recover invariants with W_gh > r." The paper maps 15 HGNN
architectures into the hierarchy and "precisely identifies information lost by clique expansion".

Two things follow that matter for knowledge hypergraphs:

1. **Clique expansion is provably lossy, not just heuristically lossy.** `I_CE ⊊ I_NH^(R)` is
   strict. The survey's informal counterexample (§1) is a special case.
2. **The same parameter — hypertree width — governs both query evaluation and learning.** It
   controls tractable conjunctive-query evaluation
   ([query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md) §10.2) and it indexes
   HGNN expressivity. That is a genuinely unifying observation and, as of September 2026, a very
   recent one. *Caveat: this paper is a 2026 preprint; its theorems had not been independently
   replicated at the time of writing.*

### 3.3 Empirical corroboration from the knowledge side

HYPER's node-inductive table gives an unusually direct comparison of unlabelled HNNs against
relation-aware models on knowledge hypergraphs (MRR;
[Huang et al. 2025](https://arxiv.org/abs/2506.12362), Table 2):

| Model | JF-IND | WP-IND | MFB-IND |
|---|---|---|---|
| HGNN | 0.102 | 0.072 | 0.121 |
| HyperGCN | 0.099 | 0.075 | 0.118 |
| G-MPNN | 0.219 | 0.177 | 0.124 |
| RD-MPNN | 0.402 | 0.304 | 0.122 |
| HCNet | 0.435 | 0.414 | 0.368 |
| Hyper (end2end) | 0.422 | 0.435 | 0.427 |
| Hyper (3KG + 2HG), fine-tuned | **0.463** | **0.446** | 0.455 |

HGNN and HyperGCN "were originally designed for simple hypergraphs and adapted to knowledge
hypergraphs by ignoring relations". The 4× gap between them and relation-aware models is the
quantitative statement that **relation and position labels carry most of the signal** in a knowledge
hypergraph — an HNN alone is not enough.

## 4. Libraries

| Library | Scope | Where |
|---|---|---|
| **DHG (DeepHypergraph)** | PyTorch library for graph *and* hypergraph learning; low- and high-order message passing (vertex↔vertex, vertex↔hyperedge, set↔set), spectral and spatial operators, data/metric/visualisation/AutoML/structure-generator modules | <https://github.com/iMoonLab/DeepHypergraph> · docs <https://deephypergraph.readthedocs.io/> |
| **HyperNetX (HNX)** | Python package for hypergraph analysis and visualisation; the reference implementation of s-line graphs and s-centralities (see [hypergraph-algorithms-for-knowledge.md](hypergraph-algorithms-for-knowledge.md)) | <https://github.com/pnnl/HyperNetX> |
| **TopoNetX / TopoX** | computing on topological domains — hypergraphs, simplicial complexes, cell and combinatorial complexes; higher-order message passing | <https://github.com/pyt-team/TopoNetX> |
| **PyTorch Geometric** | `HypergraphConv` and related layers; most HNN papers ship PyG code | <https://pytorch-geometric.readthedocs.io/> |
| **DGL** | no first-class hypergraph object; hypergraphs are modelled as bipartite/heterogeneous graphs (the star expansion) | <https://www.dgl.ai/> |
| **DHG-Bench** | "the first comprehensive benchmark for HNNs […] 17 state-of-the-art HNN algorithms on 22 diverse datasets spanning node-, edge-, and graph-level tasks, under unified experimental settings" ([arXiv:2508.12244](https://arxiv.org/abs/2508.12244)) | <https://github.com/Coco-Hut/DHG-Bench> |

Repository metadata checked 20 September 2026. The PyG and DGL rows describe capability, not a
quoted statement, and are marked `[unverified]` as to the exact current API surface.

## 5. Relation to knowledge-hypergraph embedding

| | HNN | KHG embedding model |
|---|---|---|
| Hyperedge | unlabelled vertex set | labelled, typed, often positional |
| Vertex input | feature vector | learned embedding (transductive) or text/structure-derived (inductive) |
| Task | node classification, hyperedge prediction | predict a missing element of a fact |
| Position | usually ignored | central (HypE's positional filters, HYPER's `Enc_PI`) |
| Theory | homomorphism densities, hypertree width | relational WL |

The convergence point is **conditional message passing**: HCNet and HYPER pass messages conditioned
on the query, over an incidence structure, with explicit positional encodings — an HNN with roles.

## Open questions raised here

- Does the Width Wall hierarchy transfer verbatim to *relational* hypergraphs, where hyperedges carry
  labels and positions? The two theories (relational WL and hypertree-width densities) have not been
  reconciled in a single statement.
- Can an architecture deliberately climb the hierarchy — e.g. by injecting width-(r+1) pattern counts
  as features — at acceptable cost?
- HGNN and HyperGCN collapse on knowledge hypergraphs (§3.3). Is that entirely the missing relation
  labels, or partly clique expansion? An ablation that adds relation labels to HGNN would separate
  the two.

## Sources

- Kim, S., Lee, S. Y., Gao, Y., Antelmi, A., Polato, M., Shin, K. *A Survey on Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide*. KDD 2024; arXiv:2404.01039, v3. <https://arxiv.org/abs/2404.01039>
- Feng, Y., You, H., Zhang, Z., Ji, R., Gao, Y. "Hypergraph Neural Networks". *AAAI 2019*. <https://doi.org/10.1609/aaai.v33i01.33013558>
- Yadati, N., Nimishakavi, M., Yadav, P., Nitin, V., Louis, A., Talukdar, P. *HyperGCN: A New Method of Training Graph Convolutional Networks on Hypergraphs*. NeurIPS 2019; arXiv:1809.02589. <https://arxiv.org/abs/1809.02589>
- Dong, Y., Sawin, W., Bengio, Y. *HNHN: Hypergraph Networks with Hyperedge Neurons*. ICML 2020 Graph Representation Learning workshop; arXiv:2006.12278. <https://arxiv.org/abs/2006.12278>
- Huang, J., Yang, J. "UniGNN: a Unified Framework for Graph and Hypergraph Neural Networks". *IJCAI 2021*; arXiv:2105.00956. <https://doi.org/10.24963/ijcai.2021/353>
- Chien, E., Pan, C., Peng, J., Milenkovic, O. *You are AllSet: A Multiset Function Framework for Hypergraph Neural Networks*. ICLR 2022; arXiv:2106.13264. <https://arxiv.org/abs/2106.13264>
- Wang, P., Yang, S., Liu, Y., Wang, Z., Li, P. *Equivariant Hypergraph Diffusion Neural Operators*. ICLR 2023. <https://openreview.net/pdf?id=RiTjKoscnNd>
- Gao, Y., Feng, Y., Ji, S., Ji, R. "HGNN⁺: General Hypergraph Neural Networks". *IEEE TPAMI*, 2022. <https://doi.org/10.1109/tpami.2022.3182052>
- Jiang, F., Li, Y., Feng, Y., Zheng, K., Niu, L., Ramasubramanian, B., Alomair, B., Bushnell, L., Poovendran, R. *The WidthWall: A Strict Expressivity Hierarchy for Hypergraph Neural Networks*. arXiv:2605.13690, 13 May 2026. <https://arxiv.org/abs/2605.13690>
- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. *Link Prediction with Relational Hypergraphs*. TMLR 2025; arXiv:2402.04062. <https://arxiv.org/abs/2402.04062>
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. *HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs*. arXiv:2506.12362, 14 Jun 2025. Venue: presented at the NeurIPS 2025 "New Perspectives in Graph Machine Learning" workshop (https://neurips.cc/virtual/2025/127653); the authors' repository states ICLR 2026 (https://github.com/HxyScotthuang/HYPER). Cite it as an arXiv preprint until one of the two is confirmed. <https://arxiv.org/abs/2506.12362>
- iMoonLab. *DeepHypergraph (DHG)*. Repository checked 20 September 2026. <https://github.com/iMoonLab/DeepHypergraph> · <https://deephypergraph.readthedocs.io/>
- Pacific Northwest National Laboratory. *HyperNetX*. Repository checked 20 September 2026. <https://github.com/pnnl/HyperNetX>
- pyt-team. *TopoNetX — Computing on Topological Domains*. Repository checked 20 September 2026. <https://github.com/pyt-team/TopoNetX>
- Li, F., Wang, X., Zhang, W., Zhang, Y., Lin, X. *DHG-Bench: A Comprehensive Benchmark for Deep Hypergraph Learning*. arXiv:2508.12244, 2025. <https://arxiv.org/abs/2508.12244>
