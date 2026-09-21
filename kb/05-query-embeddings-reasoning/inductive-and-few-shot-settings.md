---
title: Inductive and few-shot link prediction on knowledge hypergraphs
type: survey
status: draft
tags: [inductive, few-shot, zero-shot, unseen-entities, unseen-relations, qblp, hart, metanir, metarh, hancl, hyper, thor, foundation-model, wd20k]
created: 2026-09-20
updated: 2026-09-21
---

# Inductive and few-shot link prediction on knowledge hypergraphs

A transductive model learns one embedding per entity and per relation, and therefore dies the moment
the knowledge base changes — which, for a knowledge base, is constantly. This note covers the three
escapes: **inductive over entities**, **inductive over relations**, and **few-shot**.

Companion to [knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md)
and [benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md). For HYPER's
internals — relation graph, `Enc_PI`, the theorems, cost, pretraining corpora and public artefacts —
see [hyper-foundation-model-anatomy.md](hyper-foundation-model-anatomy.md).

---

## 1. Four settings, precisely

| Setting | Unseen at test time | Typical signal used |
|---|---|---|
| Transductive | nothing | learned embeddings |
| **Node-inductive** (semi-inductive) | entities | entity text, or an inference graph placing the entity in context |
| **Relation-inductive** (fully inductive) | entities *and* relations | structure of relation co-occurrence; positional interaction patterns |
| **Few-shot** | nothing structurally, but a relation has very few instances | a support set of K facts of that relation |

Few-shot and inductive are often confused. The survey draws the line cleanly: "Both few-shot and
inductive settings address unseen elements, but few-shot learning focuses on scenarios with very
limited examples rather than none"
([Wei, Guan, Li, Jin, Guo and Cheng, arXiv:2506.08970, 2025](https://arxiv.org/abs/2506.08970) §3.4.3).

Knowledge hypergraphs raise a fourth dimension that binary KGs do not have: **unseen arity**. A
model pretrained on facts of arity ≤ 5 should be able to score a 7-ary fact. Only HYPER addresses
this explicitly (§3).

## 2. Node-inductive

### QBLP (2021) — text as the bridge

The first inductive model for hyper-relational facts: embeddings for unseen entities are generated
from textual descriptions and auxiliary facts, so the entity needs no trained embedding
([Ali, Berrendorf, Galkin, Thost, Ma, Tresp and Lehmann, *Improving Inductive Link Prediction Using
Hyper-relational Facts*, ISWC 2021](https://doi.org/10.1007/978-3-030-88361-4_5)). The paper also
contributes the **WD20K** family, the standard benchmark for the setting. Its central empirical
claim is the one that justifies hyper-relational modelling at all in this setting: qualifiers give
an unseen entity more context to be described by.

Dataset design (from [Wei et al. 2025](https://arxiv.org/abs/2506.08970) §G.1.3): WD20K(25) provides
"textual descriptions without inference graphs containing unseen entities, requiring the model to
rely solely on text features", whereas WD20K(100) V1 and V2 "provide both textual descriptions and
inference graphs, enabling models to leverage structural information". V1 has more training data
than V2. The number in parentheses is the percentage of hyper-relational facts.

### HART (2025) — subgraph semantics

HART "combines hypergraph GNNs and Transformers with a role-aware mechanism to mine complex subgraph
semantics for inductive prediction" ([Yin, Zhang, Yang and Luo, *Inductive Link Prediction on N-ary
Relational Facts via Semantic Hypergraph Reasoning*, KDD 2025 /
arXiv:2503.20676](https://arxiv.org/abs/2503.20676); description from
[Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.4.2).

### MetaNIR (2025) — meta-learned adaptation

MetaNIR "adopts meta-learning to simulate inductive tasks and generate adaptive embeddings"
([Wei, Guan, Jin, Guo and Cheng, *Inductive link prediction in n-ary knowledge graphs*, COLING
2025](https://arxiv.org/abs/2506.08970)).

### Results

From [Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 11 (MRR / Hits@1 / Hits@10; WD20K
results from Yin et al. 2025, WD-Ext from Wei et al. 2025):

| Method | WD20K(100) V1 | WD20K(100) V2 | WD-Ext |
|---|---|---|---|
| BLP | 0.057 / 0.019 / 0.123 | 0.039 / 0.014 / 0.092 | — |
| CompGCN | 0.104 / 0.057 / 0.183 | 0.025 / 0.007 / 0.053 | — |
| StarE | 0.112 / 0.061 / 0.212 | 0.049 / 0.019 / 0.110 | 0.079 / 0.021 / 0.131 |
| QBLP | 0.107 / 0.039 / 0.245 | 0.066 / 0.034 / 0.120 | — |
| **HART** | **0.385 / 0.294 / 0.522** | **0.258 / 0.176 / 0.468** | — |
| **MetaNIR** | — | — | **0.582 / 0.433 / 0.901** |

Two readings. First, the 3–4× jump from QBLP/StarE to HART is large enough to suggest the earlier
models were barely inductive at all. Second, MetaNIR's WD-Ext numbers are not comparable to the
WD20K column — different dataset, different construction — and the survey does not claim they are.

And from HYPER's own node-inductive table
([Huang, Galkin, Bronstein and Ceylan, ICLR 2026 / arXiv:2506.12362
v3](https://arxiv.org/abs/2506.12362), Table 3; MRR), where the baselines are hypergraph models
rather than hyper-relational ones. **The ULTRA rows below are v3's; the v1 preprint reported very
different ones** — see [hyper-foundation-model-anatomy.md](hyper-foundation-model-anatomy.md) §8:

| Method | JF-IND | WP-IND | MFB-IND |
|---|---|---|---|
| HGNN | 0.102 | 0.072 | 0.121 |
| HyperGCN | 0.099 | 0.075 | 0.118 |
| G-MPNN | 0.219 | 0.177 | 0.124 |
| RD-MPNN | 0.402 | 0.304 | 0.122 |
| HCNet | 0.435 | 0.414 | 0.368 |
| Hyper (end2end) | 0.422 | 0.435 | 0.427 |
| ULTRA‡ (3KG), zero-shot | 0.321 | 0.305 | 0.277 |
| ULTRA‡ (50KG), zero-shot | 0.007 | 0.029 | 0.026 |
| ULTRA‡ (3KG + 2HG), zero-shot | 0.410 | 0.341 | 0.294 |
| Hyper (4HG), zero-shot | 0.403 | 0.375 | **0.497** |
| Hyper (3KG + 2HG), zero-shot | **0.459** | 0.415 | 0.404 |
| ULTRA‡ (3KG + 2HG), fine-tuned | 0.421 | 0.349 | 0.303 |
| Hyper (3KG + 2HG), fine-tuned | 0.463 | **0.446** | 0.455 |

The remarkable row is **zero-shot Hyper (4HG) beating every end-to-end model on MFB-IND (0.497 vs.
0.427)** — pretraining on other hypergraphs beats training on this one.

## 3. Relation-inductive: the foundation-model turn

Until 2025 every model here "explicitly store[d] the trained relation embeddings", so an unseen
relation got a random vector ([Huang et al. 2025](https://arxiv.org/abs/2506.12362) §5.1).

**HYPER** removes that assumption. It encodes relations through a *relation graph* and encodes
argument positions through a shared, compositional **positional interaction encoder**
`Enc_PI : ℕ>0 × ℕ>0 → ℝᵈ`, required to be *extrapolating* (generalise to unseen positions and arities)
and *injective* (distinct position pairs get distinct embeddings), implemented as a two-layer MLP
over concatenated sinusoidal position encodings. The naive alternative — one embedding per position
pair (a, b) — "does not generalize to unseen arities". Benchmarks: JF/MFB/WP/WD × {25, 50, 75, 100}%
unseen relations, following InGram ([Huang et al. 2025](https://arxiv.org/abs/2506.12362) §4.1, §5.2).

Selected MRR from v3 Table 2 (100% unseen relations — the hardest column; again, the ULTRA rows
differ substantially from v1's):

| Method | JF-100 | MFB-100 | WP-100 | WD-100 |
|---|---|---|---|---|
| G-MPNN (end-to-end) | 0.002 | 0.003 | 0.000 | 0.001 |
| HCNet (end-to-end) | 0.028 | 0.082 | 0.003 | 0.007 |
| Hyper (end-to-end) | 0.198 | 0.222 | 0.202 | 0.205 |
| ULTRA‡ (3KG), zero-shot | 0.144 | 0.277 | 0.078 | 0.161 |
| ULTRA‡ (50KG), zero-shot | 0.001 | 0.190 | 0.004 | 0.001 |
| ULTRA‡ (3KG + 2HG), zero-shot | 0.168 | 0.283 | 0.090 | 0.137 |
| Hyper (3KG + 2HG), zero-shot | 0.173 | 0.299 | 0.222 | 0.182 |
| Hyper (3KG + 2HG), fine-tuned | 0.176 | 0.275 | 0.210 | 0.210 |

Three findings the authors draw out, each verifiable from the table:

1. **Node-inductive models collapse on unseen relations.** HCNet goes from 0.435 on JF-IND to 0.028
   on JF-100; G-MPNN is at noise level throughout.
2. **Reification does not rescue KG foundation models.** ULTRA applied to reified hypergraphs is
   consistently behind, because "reified hypergraphs form atypical structures, e.g., tripartite
   graphs with auxiliary edge nodes, which is not commonly seen in pretraining corpora". v3 adds
   that "auxiliary edge nodes increase hop distances, inverse relations are modeled ineffectively,
   and the resulting structures deviate from standard KG pre-training distributions". This is the
   strongest published evidence that **reification is not just lossy but transfer-hostile** —
   including when ULTRA is pretrained on HYPER's own 3KG+2HG mixture, which v3 adds as a baseline
   and HYPER still beats. *Correction:* v1 said ULTRA (50KG) "performs only marginally better than
   the version trained on just 3"; **v3 says it "performs much worse"**. The qualitative claim
   reversed between preprint versions, so treat the size of the gap as active research
   ([hyper-foundation-model-anatomy.md](hyper-foundation-model-anatomy.md) §8).
3. **Pretraining mixture must match arity.** Hyper (4HG) "performs strongly on JF and MFB, both of
   which contain a large proportion of higher-arity relations, [but] struggles on WP, which
   primarily consists of binary edges", while WP benefits from binary-graph pretraining; the mixed
   3KG + 2HG model is best overall.

**THOR** (2026) does the analogous thing for the hyper-relational formalisation, via "relation and
entity foundation graphs, modeling their fundamental inter- and intra-fact interactions in HKGs,
which are agnostic to any specific relations and entities", with two parallel graph encoders and a
Transformer decoder supporting "efficient masked training and fully-inductive inference". Evaluated
on 12 datasets, it reports "66.1%, 55.9%, and 20.4% improvement over the best-performing rule-based,
semi-inductive, and fully-inductive techniques, respectively" ([Yu, Lu and Yang,
arXiv:2602.05424, 2026](https://arxiv.org/abs/2602.05424)).

## 4. Few-shot

**HANCL** (2022) "leverages GNNs and attention mechanisms to enhance entity representations and match
queries to limited support instances"; **MetaRH** (2024) "applies meta-learning to refine relation
representations" ([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §3.4.3;
MetaRH: [Wei, Guan, Jin, Guo and Cheng, *Few-shot Link Prediction on N-ary Facts*, COLING 2024 /
arXiv:2305.06104](https://arxiv.org/abs/2305.06104)).

Results from [Wei et al. 2025](https://arxiv.org/abs/2506.08970), Table 10 (MRR / Hits@1 / Hits@10;
WikiAnimals from Zhang et al. 2022, F-WD50K from Wei et al. 2024):

| Method | WikiAnimals | F-WD50K |
|---|---|---|
| StarE | 0.265 / 0.233 / 0.215 | 0.102 / 0.057 / 0.177 |
| GRAN | 0.253 / 0.199 / 0.221 | 0.126 / 0.077 / 0.222 |
| FSRL (binary few-shot) | 0.236 / 0.201 / 0.230 | — |
| FAAN (binary few-shot) | 0.270 / 0.225 / 0.246 | 0.116 / 0.059 / 0.226 |
| MetaR (binary few-shot) | — | 0.108 / 0.064 / 0.183 |
| **HANCL** | **0.318 / 0.288 / 0.258** | — |
| **MetaRH** | — | **0.192 / 0.109 / 0.340** |

The survey's reading: "traditional few-shot learning methods are insufficient for capturing
knowledge in multi-fact settings, while incorporating qualifier role-value pairs can effectively
enhance reasoning capability". Note also that absolute numbers are *low* — MRR 0.19 on F-WD50K
against 0.40 for HAHE in the transductive setting — so few-shot n-ary link prediction is far from
solved.

Its stated practical weakness is that few-shot approaches "require extensive few-shot tasks for
training, which are difficult to construct in real-world applications"
([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §6.2) — i.e. the meta-learning setup needs a
distribution of tasks that a real, single knowledge base may not provide.

## 5. What is still missing

- **Growing knowledge bases.** The survey: "It is crucial to develop methods for growing NKGs that
  can adaptively learn from new facts while retaining previously acquired knowledge"
  ([Wei et al. 2025](https://arxiv.org/abs/2506.08970) §6.2). Continual learning on hypergraphs is
  essentially untouched.
- **Unseen roles.** HYPER generalises over relations and positions; role *vocabularies* in the
  role-value formalisation are a separate axis.
- **Unseen arity as a measured quantity.** HYPER's `Enc_PI` is designed for it, but no benchmark
  isolates "train on arity ≤ k, test on arity > k".
- **Comparable protocols.** The three tables above use three different corpora and cannot be merged;
  see [benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md) §5.

## Open questions raised here

- Does HYPER's relation-inductive advantage survive when the unseen relation's *role semantics* are
  genuinely novel, rather than a recombination of seen ones?
- Is there a principled reason zero-shot Hyper (4HG) beats end-to-end training on MFB-IND, beyond
  regularisation from a larger pretraining corpus?
- Could a text-based encoder (QBLP's route) and a structure-based foundation model (HYPER's route)
  be combined, and is the gain additive?
- Why are few-shot absolute numbers so much lower than transductive ones — task construction, or
  genuine difficulty?

## Sources

- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs*. arXiv:2506.08970, 2025; EMNLP 2025. <https://arxiv.org/abs/2506.08970>
- Ali, M., Berrendorf, M., Galkin, M., Thost, V., Ma, T., Tresp, V., Lehmann, J. "Improving Inductive Link Prediction Using Hyper-relational Facts". *ISWC 2021*; arXiv:2107.04894. <https://doi.org/10.1007/978-3-030-88361-4_5>
- Yin, G., Zhang, H., Yang, Y., Luo, Y. *Inductive Link Prediction on N-ary Relational Facts via Semantic Hypergraph Reasoning*. KDD 2025; arXiv:2503.20676. <https://arxiv.org/abs/2503.20676>
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. *HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs*. **ICLR 2026** (confirmed 2026-09-21: the OpenReview PDF carries the line "Published as a conference paper at ICLR 2026", <https://openreview.net/pdf?id=YLTQbMoAaX>, and the authors' repository BibTeX gives ICLR 2026); also presented earlier at the NeurIPS 2025 "New Perspectives in Graph Machine Learning" workshop (<https://neurips.cc/virtual/2025/127653>). arXiv:2506.12362, v1 14 Jun 2025, v3 8 May 2026 — **cite v3**, whose baseline numbers differ from v1's. <https://arxiv.org/abs/2506.12362>
- Yu, W., Lu, Y., Yang, D. *THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs*. arXiv:2602.05424, 2026. <https://arxiv.org/abs/2602.05424>
- Wei, J., Guan, S., Jin, X., Guo, J., Cheng, X. *Few-shot Link Prediction on N-ary Facts*. COLING 2024; arXiv:2305.06104. <https://arxiv.org/abs/2305.06104>
- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. *Link Prediction with Relational Hypergraphs* (HCNet). TMLR 2025; arXiv:2402.04062. <https://arxiv.org/abs/2402.04062>
