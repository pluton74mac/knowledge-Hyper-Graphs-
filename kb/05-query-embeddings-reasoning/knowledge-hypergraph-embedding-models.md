---
title: Knowledge hypergraph embedding models, 2016 to 2026
type: survey
status: draft
tags: [embedding, link-prediction, n-ary, hyper-relational, m-transh, rae, nalp, hinge, hype, getd, stare, neuinfer, ram, gran, shrinke, hyconve, hynt, hahe, hypermono, hyper, foundation-model]
created: 2026-09-20
updated: 2026-09-21
---

# Knowledge hypergraph embedding models, 2016 to 2026

Ten years of work on one task: **given an n-ary fact with a hole, score the candidates for the
hole.** This note is the chronological reading of that literature, with the intuition behind each
model, and a table of the scores that could be verified against a primary source.

The field's own census: "nearly 50 methods" between 2016 and 2025
([Wei, Guan, Li, Jin, Guo and Cheng, *A Survey of Link Prediction in N-ary Knowledge Graphs*,
EMNLP 2025 / arXiv:2506.08970](https://arxiv.org/abs/2506.08970)). A second, orthogonal
classification is given by [Lu, Tupikina and Alam, *Two-Dimensional Taxonomy for n-Ary Knowledge
Representation Learning Methods*, IEEE TKDE 2026 / arXiv:2506.05626](https://arxiv.org/abs/2506.05626):
methodology (translation / tensor factorisation / deep neural / logic rule / hyperedge expansion) ×
semantic awareness (position-aware / role-aware / aware-less). Its Table II is reproduced in full,
with counts and two corrections, in
[geometry-and-algebraic-interfaces.md](geometry-and-algebraic-interfaces.md) §4.

Related notes: [benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md)
(what the numbers mean), [hypergraph-neural-networks.md](hypergraph-neural-networks.md) (the
non-knowledge side of the same encoder designs),
[inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md),
[temporal-and-dynamic-khgs.md](temporal-and-dynamic-khgs.md),
[geometry-and-algebraic-interfaces.md](geometry-and-algebraic-interfaces.md) (the hyperbolic family
audited, ReAlE's relational algebra, and the two-axis taxonomy reproduced in full).

---

## 1. The task

A knowledge graph stores triples (h, r, t). A **n-ary knowledge graph (NKG)** stores facts "each of
which may contain more than two entities"; **link prediction in NKGs** is to "predict missing
elements in facts in NKGs based on the existing facts" ([Wei et al.,
2025](https://arxiv.org/abs/2506.08970), Definitions 2 and 3). The motivating statistic, repeated
throughout the literature: in Freebase "over a third of entities are involved in n-ary facts"
([Wen et al., 2016](https://arxiv.org/abs/1604.08642)) and "more than 61% facts are n-ary facts"
([Fatemi et al., IJCAI 2020](https://arxiv.org/abs/1906.00137)), both as cited by
[Wei et al. 2025](https://arxiv.org/abs/2506.08970).

## 2. Three formalisations — and why the scores are not comparable

Every model commits to one of three encodings of the same fact, and this choice, not the
architecture, is the first thing to read off a paper ([Wei et al.,
2025](https://arxiv.org/abs/2506.08970), §2.2):

| Formalisation | Shape | Example | Consequence |
|---|---|---|---|
| **Hyperedge** | `(H, e₁, …, eₙ)` — ordered, fixed arity, position = role | `(educated_with_degree_major, Einstein, Uni. Zurich, PhD, Physics)` | reduces to the triple form for n = 2; arity fixed per relation |
| **Role–value pair** | `{rᵢ : vᵢ}ⁿᵢ₌₁` — unordered, arbitrary arity | `{person: Einstein, institution: Uni. Zurich, degree: PhD, major: Physics}` | flexible; "fails to account for the varying importance or prominence of different entities" |
| **Hyper-relational** | `((h, r, t), {rᵢ : vᵢ}ⁿ⁻²ᵢ₌₁)` — primary triple + qualifiers | `((Einstein, educated, Uni. Zurich), {major: Physics, degree: PhD})` | matches Wikidata; "when there is no clear subject or object […] it is not appropriate" |

Because the three formalisations imply different *prediction tasks* (all positions vs. object only)
and different *filtering* rules, **a number from a hyperedge-formalisation paper and a number from a
hyper-relational paper on the same dataset name are usually not comparable.** The worked example is
JF17K: HypE reports MRR 0.494 predicting every position of the tuple
([Fatemi et al. 2020](https://arxiv.org/abs/1906.00137), Table 1), while StarE reports MRR 0.574
predicting only the object of the primary triple ([Galkin et al., EMNLP
2020](https://arxiv.org/abs/2009.10847), Table 2). Neither is "better". See
[benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md).

## 3. Chronology

### 2016 — m-TransH: translate on a hyperplane, per role

Wen et al. generalise TransH from triples to n-ary facts: each entity is projected onto a
relation-specific hyperplane "according to their corresponding roles", and the fact is scored from
the spatial positions of the projections ([Wen, Li, Mao, Chen and Zhang, *On the representation and
embedding of knowledge bases beyond binary relations*, IJCAI 2016 /
arXiv:1604.08642](https://arxiv.org/abs/1604.08642); description from [Wei et al.
2025](https://arxiv.org/abs/2506.08970) §3.1). This paper also introduces **JF17K**, still the most
used benchmark. Weakness noted by the survey: complexity "grows with the number of missing entities".

### 2018 — RAE: exploit relatedness between co-occurring entities

RAE keeps m-TransH's geometry but adds a *relatedness* term — a learned estimate of how likely two
entities are to co-occur in a fact — and uses it to prune the candidate set, "assuming high
similarity among entities within a fact and only calculating entities with high similarity"
([Zhang, Li, Mei and Mao, *Scalable Instance Reconstruction in Knowledge Bases via Relatedness
Affiliated Embedding*, WWW 2018](https://doi.org/10.1145/3178876.3186017)).

### 2019 — NaLP: a fact is a set of role-value pairs

NaLP drops the fixed positional encoding entirely. A fact becomes a set of role-value pairs; a
convolution extracts per-pair features and a fully connected network aggregates them into a truth
score ([Guan, Jin, Wang and Cheng, *Link Prediction on N-ary Relational Data*, WWW
2019](https://doi.org/10.1145/3308558.3313414)). It also introduces **WikiPeople**. Its limitation,
which the next five years of papers attack: it "treats all pairs equally". t-NaLP adds entity types
and better negative sampling ([Guan et al., *IEEE TKDE*, 2021](https://doi.org/10.1109/tkde.2021.3073483)).

### 2020 — the year the field forked

Four designs appear almost simultaneously, and they define the four branches that still exist.

**HINGE (hyper-relational + CNN).** A fact is a primary triple plus qualifier pairs; a CNN with
min-pooling aggregates triple-qualifier interactions and an MLP scores
([Rosso, Yang and Cudré-Mauroux, *Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for
Link Prediction*, WWW 2020](https://doi.org/10.1145/3366423.3380257)).
Code: <https://github.com/eXascaleInfolab/HINGE_code>.

**NeuInfer (hyper-relational + FCN).** Scores the primary triple *and* its compatibility with each
qualifier separately, then combines — making explicit the claim that qualifiers *restrict* rather
than *define* a fact ([Guan, Jin, Guo, Wang and Cheng, *NeuInfer: Knowledge Inference on N-ary
Facts*, ACL 2020](https://doi.org/10.18653/v1/2020.acl-main.546)).

**HypE / HSimplE (tensor decomposition, hyperedge formalisation).** HSimplE shifts an entity's
embedding by its position in the tuple and combines it with a relation embedding; HypE replaces the
shift with **position-specific convolutional filters**, so an entity's representation genuinely
depends on the role it plays ([Fatemi, Taslakian, Vazquez and Poole, *Knowledge Hypergraphs:
Prediction Beyond Binary Relations*, IJCAI 2020 / arXiv:1906.00137](https://arxiv.org/abs/1906.00137)).
This paper introduces **FB-AUTO** and **M-FB15K** and the reification baseline r-SimplE, whose
collapse (JF17K MRR 0.102 vs. HypE 0.494) is the field's standard argument against decomposing
n-ary facts into triples. Code: <https://github.com/ServiceNow/HypE> and
<https://github.com/baharefatemi/HypE>.

**GETD (tensor decomposition, higher-order).** Generalises Tucker decomposition by reshaping the
core tensor and applying tensor-ring decomposition to control parameter growth
([Liu, Yao and Li, *Generalizing Tensor Decomposition for N-ary Relational Knowledge Bases*, WWW
2020](https://doi.org/10.1145/3366423.3380188); code <https://github.com/liuyuaa/GETD>). Its
limitation, fixed later by S2S: GETD "cannot handle multiple facts of different number of entities
at the same time".

**StarE (message passing, hyper-relational).** A CompGCN-style encoder in which qualifier pairs are
aggregated into a *modified relation representation* before the message is sent, "while keeping the
semantic roles of qualifiers and triples intact"; a Transformer decoder scores candidates
([Galkin, Trivedi, Maheshwari, Usbeck and Lehmann, *Message Passing for Hyper-Relational Knowledge
Graphs*, EMNLP 2020](https://doi.org/10.18653/v1/2020.emnlp-main.596), arXiv:2009.10847). Two
lasting contributions beyond the model: the demonstration that "existing benchmarks […] suffer from
fundamental flaws", and the **WD50K** family. Code: <https://github.com/migalkin/StarE>.

### 2021 — attention arrives; roles get a latent space

**RAM** gives roles their own latent space: role embeddings are linear combinations of shared basis
vectors, and role-specific pattern matrices evaluate entity–role compatibility through a multilinear
score ([Liu, Yao and Li, *Role-Aware Modeling for N-ary Relational Knowledge Bases*, WWW
2021](https://doi.org/10.1145/3442381.3449874)). This is the cleanest answer to NaLP's "all pairs
are equal" problem.

**GRAN** represents each n-ary fact as a small heterogeneous graph over its own elements and runs
fully connected attention with **edge-type-aware biases**, so the model knows whether two elements
are triple-to-triple, triple-to-qualifier, or qualifier-to-qualifier
([Wang, Wang, Lyu and Zhu, *Link Prediction on N-ary Relational Facts: A Graph-based Approach*,
Findings of ACL 2021](https://doi.org/10.18653/v1/2021.findings-acl.35)). It is still, five years
later, the standard strong baseline.

**Hy-Transformer** (HyTransformer) is the minimal-Transformer answer: encode the fact's elements as
a sequence with type-indicating position embeddings and regularisation layers, no graph encoder
([Yu and Yang, *Improving Hyper-Relational Knowledge Graph Completion*,
arXiv:2104.08167, 2021](https://arxiv.org/abs/2104.08167)). Its point is efficiency — it argues the
GNN encoder can be replaced by cheaper regularisation with little loss.

**S2S** partitions embeddings so parameters can be shared across facts of different arity, fixing
GETD's sparsity problem (Di, Yao and Chen, 2021, as described in
[Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.2).

**QBLP** is the first genuinely inductive model here: it builds embeddings for unseen entities from
their textual descriptions and auxiliary facts ([Ali, Berrendorf, Galkin, Thost, Ma, Tresp and
Lehmann, *Improving Inductive Link Prediction Using Hyper-relational Facts*, ISWC
2021](https://doi.org/10.1007/978-3-030-88361-4_5)). See
[inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md).

### 2022 — geometry, queries, and explanations

**StarQE** moves from single facts to *queries*: a GNN (StarE) encoder embeds a hyper-relational
conjunctive query and answers it directly, with the new **WD50K-QE** dataset of "hyper-relational
variants of 7 well-studied query patterns" ([Alivanistos, Berrendorf, Cochez and Galkin, *Query
Embedding on Hyper-relational Knowledge Graphs*, ICLR 2022 /
arXiv:2106.08166](https://arxiv.org/abs/2106.08166); code
<https://github.com/DimitrisAlivas/StarQE>). Treated in
[logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md).

**QUAD** makes StarE's information flow bidirectional between primary triple and qualifiers
([Shomer, Jin, Li, Ma and Liu, *Learning Representations for Hyper-Relational Knowledge Graphs*,
2023](https://doi.org/10.1145/3625007.3627591)).

**Hyperbolic family.** HYPER², PolygonE and WPolygonE+ embed facts in hyperbolic space on the
argument that "the number of related entities grows exponentially along the NKG hierarchy, which
aligns with the superlinear growth in hyperbolic space"; PolygonE treats an n-ary fact as a
*gyro-polygon* and scores by vertex-to-gyrocentroid distance, WPolygonE+ adds learned entity weights
([Yan et al., *Neurocomputing* 2022; AAAI 2022; *KBS* 2022, as summarised by
Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.1). All three are the work of one group and
are now verified against the publishers: HYPER² is
[Yan, Zhang, Sun, Xu, Jin and Li, *Neurocomputing* 492:440–451, 2022](https://arxiv.org/abs/2104.09871)
(preprint arXiv:2104.09871), PolygonE is
[Yan et al., AAAI 2022, 36(4):4308–4317](https://doi.org/10.1609/aaai.v36i4.20351), and the
"WPolygonE+" paper is *Modeling N-ary relational data as gyro-polygons with learnable gyro-centroid*,
[*Knowledge-Based Systems* 251:109164, 2022](https://doi.org/10.1016/j.knosys.2022.109164) — the
`[unverified]` marks on these three can be dropped. The family later gains **H²GNN** (hyperbolic
message passing, 2024) and **GAHE** (multi-curvature, 2025). None of the five reports a
hyperbolicity measurement for any n-ary dataset, and none beats ReAlE's 2021/2023 numbers on the
FB-AUTO/JF17K/M-FB15K protocol: see
[geometry-and-algebraic-interfaces.md](geometry-and-algebraic-interfaces.md) §1 for the audit.

**HyperMLN** is the first explainability-oriented model: a Markov logic network over n-ary facts
coupled to a KHG embedding through variational EM ([Chen, Wang, Wang and Li, *Explainable Link
Prediction in Knowledge Hypergraphs*, CIKM 2022](https://doi.org/10.1145/3511808.3557316)). See
[explainability-and-uncertainty.md](explainability-and-uncertainty.md).

### 2023 — the strongest year

**ShrinkE** gives qualifiers a geometric meaning. The primary triple is a relation-specific
spatial-functional transformation mapping the head to a **query box** containing the answers; each
qualifier *shrinks* the box, and the contracted box must stay inside the original. That containment
is a geometric proof of **qualifier monotonicity**: adding a qualifier can only narrow the answer
set ([Xiong, Nayyeri, Pan and Staab, *Shrinking Embeddings for Hyper-relational Knowledge Graphs*,
ACL 2023](https://doi.org/10.18653/v1/2023.acl-long.743), arXiv:2306.02199; code
<https://github.com/xiongbo010/ShrinkE>). This is the most *semantically* principled model in the
list.

**HyConvE** uses 3D convolution with role-aware and position-aware filters to capture intra-fact
interactions ([Wang, Wang, Li, Chen and Li, *HyConvE: A Novel Embedding Model for Knowledge
Hypergraph Link Prediction with Convolutional Neural Networks*, WWW
2023](https://doi.org/10.1145/3543507.3583256)).

**HyNT** is the first model to treat **numeric literals** as first-class: a context Transformer and a
prediction Transformer encode numeric values in both the primary triple and the qualifiers, instead
of dropping them as every earlier model did ([Chung, Lee and Whang, *Representation Learning on
Hyper-Relational and Numeric Knowledge Graphs with Transformers*, KDD
2023](https://doi.org/10.1145/3580305.3599490), arXiv:2305.18256; code
<https://github.com/bdi-lab/HyNT>). This matters because StarE's own analysis showed WikiPeople is
largely literals.

**HAHE** runs two attention modules — a *global* one over the hypergraph structure and a *local* one
over the fact's element sequence ([Luo, E, Yang, Guo, Sun, Yao, Tang, Wan, Song and Lin, *HAHE:
Hierarchical Attention for Hyper-Relational Knowledge Graphs in Global and Local Level*, ACL
2023](https://doi.org/10.18653/v1/2023.acl-long.450); code <https://github.com/LHRLAB/HAHE>). In the
survey's comparison it is the best method across JF17K, WikiPeople and WD50K
([Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 2).

Also 2023: **HyperFormer** (bidirectional interaction + mixture-of-experts), **MSeaKG** (neural
architecture search over message functions), **DHGE/DHKG** and **HELIOS** (schema and ontology
views), and **s-HINGE** and **EnhancE** (type and neighbourhood enrichment) — all catalogued in
[Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.3.

### 2024 — efficiency, noise, monotone cones

**HyCubE** (3D circular convolution + masked stacking, for efficiency) and **HJE** (learnable
position embeddings on top of HyConvE) push the CNN branch; **HIST** fuses text and structure via
structural soft-prompt tuning ([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.3.2–3.3.3).

**NYLON** extends GRAN to *noisy* NKGs, computing both fact-level and element-level confidence with
a Transformer with learnable edge biases, and using them to drive selective annotation
([Yu, Yang and Yang, *Robust Link Prediction over Noisy Hyper-Relational Knowledge Graphs via Active
Learning*, WWW 2024](https://doi.org/10.1145/3589334.3645686)).

**HyperMono** re-derives ShrinkE's monotonicity with **cone embeddings**: each added qualifier
reduces the cone's angle and hence the answer set, after a neighbour-aggregation step that enriches
entity representations ([Hu, Gutiérrez-Basulto, Xiang, Li and Pan, *HyperMono: A Monotonicity-aware
Approach to Hyper-Relational Knowledge Representation*,
arXiv:2404.09848, 2024](https://arxiv.org/abs/2404.09848); journal version *Information Fusion*,
2026, [doi:10.1016/j.inffus.2026.104643](https://doi.org/10.1016/j.inffus.2026.104643)).

**HyperCL** adds hierarchical ontologies and concept-aware contrastive learning
([Lu, Yu, Jing and Yang, 2024, as cited by Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.3.4).

### 2025–2026 — theory, and the first foundation model

**HCNet / relational hypergraphs.** Huang et al. lift conditional message passing to k-ary
relational hypergraphs and analyse the resulting architectures "via corresponding relational
Weisfeiler-Leman algorithms and also via logical expressiveness" ([Huang, Romero Orth, Barceló,
Bronstein and Ceylan, *Link Prediction with Relational Hypergraphs*, *TMLR* 2025 /
arXiv:2402.04062](https://arxiv.org/abs/2402.04062)). This is the theoretical backbone the earlier
models lacked.

**HYPER** is the first **foundation model** for knowledge hypergraphs: it "can generalize to any
knowledge hypergraph, including novel entities and novel relations", by encoding the entities of
each hyperedge **together with their positions**. Its key device is a *positional interaction
encoder* `Enc_PI : ℕ>0 × ℕ>0 → ℝᵈ` over pairs of argument positions, implemented as a two-layer MLP
over concatenated sinusoidal encodings, chosen to be both **injective** and **extrapolating** — so a
model pretrained on arity ≤ 6 can act on arities it has never seen. For knowledge graphs the scheme
degenerates exactly to the four fundamental relations head-to-head, head-to-tail, tail-to-head,
tail-to-tail. The authors build 16 new inductive datasets and show sinusoidal encoding beats
all-one, random and magnitude encodings (avg. MRR 0.285 vs. 0.236 / 0.213 / 0.227 across 19
hypergraphs) ([Huang, Galkin, Bronstein and Ceylan, *HYPER: A Foundation Model for Inductive Link
Prediction with Knowledge Hypergraphs*, arXiv:2506.12362,
2025](https://arxiv.org/abs/2506.12362); the official implementation at
<https://github.com/HxyScotthuang/HYPER> describes it as ICLR 2026).

**THOR** does the analogous thing for the *hyper-relational* formalisation, learning from "relation
and entity foundation graphs […] which are agnostic to any specific relations and entities", and
reporting 20.4% improvement over the best fully-inductive baseline across 12 datasets
([Yu, Lu and Yang, *THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs*,
arXiv:2602.05424, 2026](https://arxiv.org/abs/2602.05424)).

Other 2025 entries: **HySAE** (semantic-enhanced, efficiency-focused,
[doi:10.1145/3696410.3714549](https://doi.org/10.1145/3696410.3714549)), **HART** (hypergraph GNN +
Transformer for inductive prediction, [Yin, Zhang, Yang and Luo, KDD 2025 /
arXiv:2503.20676](https://arxiv.org/abs/2503.20676)), **MetaNIR** (meta-learned inductive
representations, [Wei, Guan, Jin, Guo and Cheng, COLING 2025](https://arxiv.org/abs/2506.08970)),
and **UniHR** (a unified hierarchical representation for triples, hyper-relational and temporal
facts, [arXiv:2411.07019](https://arxiv.org/abs/2411.07019)).

## 4. Comparison table

Scores are **only** included where they were read from a primary source or from the survey's own
table; each score column names its protocol, and protocols differ between blocks (see §2 and
[benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md)). "—" means the
model was not evaluated on that dataset in the cited source. "Ind.?" = inductive over unseen
entities (E) and/or unseen relations (R).

### 4a. Numbers from [Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 2 — MRR / Hits@1

Their note: data for HypE and S2S come from Di et al. 2021, the rest from Luo et al. 2023 (HAHE).

| Model | Year | Representation | Ind.? | JF17K | WikiPeople | WD50K | Code |
|---|---|---|---|---|---|---|---|
| m-TransH | 2016 | Euclidean projection, hyperedge | no | 0.102 / 0.069 | — | — | — |
| RAE | 2018 | Euclidean + relatedness | no | 0.310 / 0.219 | 0.172 / 0.102 | — | — |
| HypE | 2020 | tensor decomp., positional filters | no | 0.494 / 0.408 | 0.292 / 0.162 | — | [ServiceNow/HypE](https://github.com/ServiceNow/HypE) |
| S2S | 2021 | tensor decomp., shared partitions | no | 0.528 / 0.457 | 0.372 / 0.277 | — | — |
| HINGE | 2020 | CNN, hyper-relational | no | 0.473 / 0.397 | 0.333 / 0.259 | — | [eXascaleInfolab/HINGE_code](https://github.com/eXascaleInfolab/HINGE_code) |
| NeuInfer | 2020 | FCN, hyper-relational | no | 0.517 / 0.436 | 0.350 / 0.282 | 0.232 / 0.164 | — |
| GRAN | 2021 | edge-biased Transformer | no | 0.656 / 0.582 | 0.479 / 0.410 | 0.309 / 0.240 | — |
| HAHE | 2023 | dual (global+local) attention | no | **0.668 / 0.597** | **0.495 / 0.420** | **0.402 / 0.327** | [LHRLAB/HAHE](https://github.com/LHRLAB/HAHE) |

### 4b. Numbers from the models' own papers (different protocols — do not mix with 4a)

| Model | Year | Source & protocol | JF17K | FB-AUTO | M-FB15K | WD50K |
|---|---|---|---|---|---|---|
| r-SimplE (reification baseline) | 2020 | [Fatemi et al.](https://arxiv.org/abs/1906.00137) T.1, all positions, MRR | 0.102 | 0.106 | 0.051 | — |
| m-DistMult | 2020 | same | 0.463 | 0.784 | 0.705 | — |
| m-TransH | 2020 | same (re-run) | 0.444 | 0.728 | 0.623 | — |
| HSimplE | 2020 | same | 0.472 | 0.798 | 0.730 | — |
| HypE | 2020 | same | 0.494 | 0.804 | 0.777 | — |
| G-MPNN | 2020 | [Fatemi et al. 2023](https://www.jmlr.org/papers/v24/22-063.html) T.1, same protocol | 0.501 | — | 0.779 | — |
| ReAlE | 2021/2023 | same | **0.530** | **0.861** | **0.801** | — |
| HINGE | 2020 | [Galkin et al.](https://arxiv.org/abs/2009.10847) T.2–3, object only, MRR | 0.449 | — | — | 0.243 |
| StarE + Transformer | 2020 | same | 0.574 (H) / 0.562 (T) | — | — | 0.308 |
| NaLP-Fix | 2020 | same | 0.245 | — | — | 0.177 |

Corresponding Hits@10 for the HypE block on JF17K / FB-AUTO / M-FB15K: HypE 0.656 / 0.856 / 0.881,
HSimplE 0.645 / 0.855 / 0.859, m-DistMult 0.634 / 0.845 / 0.844, r-SimplE 0.168 / 0.147 / 0.070
([Fatemi et al. 2020](https://arxiv.org/abs/1906.00137), Table 1). ReAlE's Hits@10 on the same three:
0.677 / 0.908 / 0.901 ([Fatemi et al. 2023](https://www.jmlr.org/papers/v24/22-063.html), Table 1).
ReAlE is the strongest verified all-positions result in this KB, and the later hyperbolic and
message-passing models on these datasets (H²GNN: JF17K 0.498, FB-AUTO 0.757) do not reach it — see
[geometry-and-algebraic-interfaces.md](geometry-and-algebraic-interfaces.md) §1.3.

### 4c. Models in the chronology without a score verified here

ShrinkE, HyConvE, HyNT, HyperMono, HyCubE, HJE, NYLON, HIST, HyperFormer, HyperCL, QUAD, HYPER²,
PolygonE, WPolygonE+, HyperMLN, StarQE, HYPER, THOR, HART, MetaNIR, MetaRH, HySAE, UniHR. Their
scores exist in the cited papers but were not re-read against a primary table for this note and are
therefore **`[unverified]` here**. HYPER's and THOR's inductive numbers are given in
[inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md).

## 5. What the ten years actually taught

1. **Do not decompose.** Every paper that measures it finds reification collapses: r-SimplE at
   JF17K MRR 0.102 against HypE's 0.494 ([Fatemi et al. 2020](https://arxiv.org/abs/1906.00137)).
   The sense meant here is *reification-by-decomposition* — replacing the n-ary fact by a dummy entity
   plus binary edges and then learning embeddings over them — not the information-preserving
   statement-as-object sense (RDF reification, RDF 1.2 reifiers, TypeDB relation instances); what
   collapses is the learning, because the auxiliary entities appear in too few facts, not the
   representation, which is equivalent to the original. See
   [../10-comparative-and-critique/limitations-and-failure-modes.md](../10-comparative-and-critique/limitations-and-failure-modes.md) §2.
2. **Roles carry information that position alone does not** (RAM, GRAN), and **qualifiers restrict
   rather than define** (NeuInfer, ShrinkE, HyperMono).
3. **Architecture converged on attention.** Across the survey's comparison "neural network-based
   methods consistently outperform others, with HAHE (GNN-based) achieving the best result across
   all datasets", while "spatial mapping-based methods (m-TransH, RAE) perform worst"
   ([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §4.3).
4. **The remaining gains look structural, not architectural**: monotonicity (ShrinkE, HyperMono),
   literals (HyNT), noise (NYLON), schema (HyperCL, HELIOS), and now transfer (HYPER, THOR).
5. **The field had almost no theory until 2024–2026.** HCNet's relational-WL analysis and the
   generalized-hypertree-width hierarchy in
   [hypergraph-neural-networks.md](hypergraph-neural-networks.md) are the first principled accounts
   of what these encoders can and cannot distinguish.
6. **LLMs had not touched the task as of mid-2025.** The survey states flatly: "to the best of our
   knowledge, LLMs have not been applied to link prediction in NKGs", blaming format conversion and
   input-length limits ([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §6.1). See
   [llm-and-khg-interaction.md](llm-and-khg-interaction.md) for what LLMs *are* being used for.

## Sources

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs*. arXiv:2506.08970, 10 June 2025; EMNLP 2025 main conference, <https://doi.org/10.18653/v1/2025.emnlp-main.1451>. <https://arxiv.org/abs/2506.08970>
- Lu, X., Tupikina, L., Alam, M. *Two-Dimensional Taxonomy for n-Ary Knowledge Representation Learning Methods*. IEEE TKDE, 2026; arXiv:2506.05626. <https://arxiv.org/abs/2506.05626>
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraph Embedding Meets Relational Algebra* (ReAlE). *JMLR* 24(105):1–34, 2023; preprint arXiv:2102.09557. <https://www.jmlr.org/papers/v24/22-063.html>
- Yan, S., Zhang, Z., Sun, X., Xu, G., Jin, L., Li, S. "HYPER²: Hyperbolic embedding for hyper-relational link prediction". *Neurocomputing* 492:440–451, 2022; preprint arXiv:2104.09871. <https://arxiv.org/abs/2104.09871>
- Yan, S., Zhang, Z., Sun, X., Xu, G., Li, S., Liu, Q., Liu, N., Wang, S. "PolygonE: Modeling N-ary Relational Data as Gyro-Polygons in Hyperbolic Space". *AAAI 2022* 36(4):4308–4317. <https://doi.org/10.1609/aaai.v36i4.20351>
- Yan, S., Zhang, Z., Xu, G., Sun, X., Li, S., Wang, S. "Modeling N-ary relational data as gyro-polygons with learnable gyro-centroid". *Knowledge-Based Systems* 251:109164, 2022. <https://doi.org/10.1016/j.knosys.2022.109164>
- Li, M., Shi, X., Qiao, C., Zhang, T., Jin, H. *Hyperbolic Hypergraph Neural Networks for Multi-Relational Knowledge Hypergraph Representation* (H²GNN). arXiv:2412.12158, 11 December 2024. <https://arxiv.org/abs/2412.12158>
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. *On the representation and embedding of knowledge bases beyond binary relations*. IJCAI 2016; arXiv:1604.08642. <https://arxiv.org/abs/1604.08642>
- Zhang, R., Li, J., Mei, J., Mao, Y. "Scalable Instance Reconstruction in Knowledge Bases via Relatedness Affiliated Embedding". *WWW 2018*. <https://doi.org/10.1145/3178876.3186017>
- Guan, S., Jin, X., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data". *WWW 2019*. <https://doi.org/10.1145/3308558.3313414>
- Guan, S., Jin, X., Guo, J., Wang, Y., Cheng, X. "Link Prediction on N-ary Relational Data Based on Relatedness Evaluation". *IEEE TKDE*, 2021. <https://doi.org/10.1109/tkde.2021.3073483>
- Rosso, P., Yang, D., Cudré-Mauroux, P. "Beyond Triplets: Hyper-Relational Knowledge Graph Embedding for Link Prediction". *WWW 2020*. <https://doi.org/10.1145/3366423.3380257>
- Guan, S., Jin, X., Guo, J., Wang, Y., Cheng, X. "NeuInfer: Knowledge Inference on N-ary Facts". *ACL 2020*. <https://doi.org/10.18653/v1/2020.acl-main.546>
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations*. IJCAI 2020; arXiv:1906.00137. <https://arxiv.org/abs/1906.00137>
- Liu, Y., Yao, Q., Li, Y. "Generalizing Tensor Decomposition for N-ary Relational Knowledge Bases". *WWW 2020*. <https://doi.org/10.1145/3366423.3380188>
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs". *EMNLP 2020*; arXiv:2009.10847. <https://doi.org/10.18653/v1/2020.emnlp-main.596> · <https://arxiv.org/abs/2009.10847>
- Liu, Y., Yao, Q., Li, Y. "Role-Aware Modeling for N-ary Relational Knowledge Bases". *WWW 2021*. <https://doi.org/10.1145/3442381.3449874>
- Wang, Q., Wang, H., Lyu, Y., Zhu, Y. "Link Prediction on N-ary Relational Facts: A Graph-based Approach". *Findings of ACL 2021*. <https://doi.org/10.18653/v1/2021.findings-acl.35>
- Yu, D., Yang, Y. *Improving Hyper-Relational Knowledge Graph Completion*. arXiv:2104.08167, 2021. <https://arxiv.org/abs/2104.08167>
- Ali, M., Berrendorf, M., Galkin, M., Thost, V., Ma, T., Tresp, V., Lehmann, J. "Improving Inductive Link Prediction Using Hyper-relational Facts". *ISWC 2021*, LNCS. <https://doi.org/10.1007/978-3-030-88361-4_5>
- Alivanistos, D., Berrendorf, M., Cochez, M., Galkin, M. *Query Embedding on Hyper-relational Knowledge Graphs*. ICLR 2022; arXiv:2106.08166. <https://arxiv.org/abs/2106.08166>
- Shomer, H., Jin, W., Li, J., Ma, Y., Liu, H. "Learning Representations for Hyper-Relational Knowledge Graphs". 2023. <https://doi.org/10.1145/3625007.3627591>
- Chen, Z., Wang, X., Wang, C., Li, J. "Explainable Link Prediction in Knowledge Hypergraphs". *CIKM 2022*. <https://doi.org/10.1145/3511808.3557316>
- Xiong, B., Nayyeri, M., Pan, S., Staab, S. "Shrinking Embeddings for Hyper-relational Knowledge Graphs". *ACL 2023*; arXiv:2306.02199. <https://doi.org/10.18653/v1/2023.acl-long.743>
- Wang, C., Wang, X., Li, Z., Chen, Z., Li, J. "HyConvE: A Novel Embedding Model for Knowledge Hypergraph Link Prediction with Convolutional Neural Networks". *WWW 2023*. <https://doi.org/10.1145/3543507.3583256>
- Chung, C., Lee, J., Whang, J. J. "Representation Learning on Hyper-Relational and Numeric Knowledge Graphs with Transformers". *KDD 2023*; arXiv:2305.18256. <https://doi.org/10.1145/3580305.3599490>
- Luo, H., E, H., Yang, Y., Guo, Y., Sun, M., Yao, T., Tang, Z., Wan, K., Song, M., Lin, W. "HAHE: Hierarchical Attention for Hyper-Relational Knowledge Graphs in Global and Local Level". *ACL 2023*; arXiv:2305.06588. <https://doi.org/10.18653/v1/2023.acl-long.450>
- Yu, W., Yang, J., Yang, D. "Robust Link Prediction over Noisy Hyper-Relational Knowledge Graphs via Active Learning". *WWW 2024*. <https://doi.org/10.1145/3589334.3645686>
- Hu, Z., Gutiérrez-Basulto, V., Xiang, Z., Li, R., Pan, J. Z. *HyperMono: A Monotonicity-aware Approach to Hyper-Relational Knowledge Representation*. arXiv:2404.09848, 2024; *Information Fusion*, 2026. <https://arxiv.org/abs/2404.09848> · <https://doi.org/10.1016/j.inffus.2026.104643>
- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. *Link Prediction with Relational Hypergraphs*. TMLR 2025; arXiv:2402.04062. <https://arxiv.org/abs/2402.04062>
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. *HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs*. arXiv:2506.12362, 14 June 2025. <https://arxiv.org/abs/2506.12362> · code <https://github.com/HxyScotthuang/HYPER>
- Yu, W., Lu, Y., Yang, D. *THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs*. arXiv:2602.05424, 5 February 2026. <https://arxiv.org/abs/2602.05424>
- Yin, G., Zhang, H., Yang, Y., Luo, Y. *Inductive Link Prediction on N-ary Relational Facts via Semantic Hypergraph Reasoning*. KDD 2025; arXiv:2503.20676. <https://arxiv.org/abs/2503.20676>
- Li, Z., Wang, X., Zhao, J., Feng, F., Chen, Z., Li, J. "HySAE: An Efficient Semantic-Enhanced Representation Learning Model for Knowledge Hypergraph Link Prediction". 2025. <https://doi.org/10.1145/3696410.3714549>
- Liu, Z. et al. *UniHR: Hierarchical Representation Learning for Unified Knowledge Graph Link Prediction*. arXiv:2411.07019, 2024. <https://arxiv.org/abs/2411.07019>
