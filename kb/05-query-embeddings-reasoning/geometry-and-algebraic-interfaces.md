---
title: Geometry and algebraic interfaces for knowledge hypergraphs
type: survey
status: draft
tags: [hyperbolic, lorentz, poincare, h2gnn, hyper2, polygone, gahe, reale, relational-algebra, taxonomy, role-aware, position-aware, semantic-operators, planner]
created: 2026-09-21
updated: 2026-09-21
---

# Geometry and algebraic interfaces for knowledge hypergraphs

Two questions sit underneath the model zoo in
[knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md), and neither is
answered by adding another attention block.

1. **What shape is the space?** Almost every n-ary model embeds into ℝ^d. A small, mostly
   ignored literature argues that knowledge hypergraphs are hierarchical and therefore belong in
   hyperbolic space. Section 1 audits that literature — it is five papers in five years.
2. **What is the interface?** A knowledge hypergraph *is* a set of n-ary relations, so relational
   algebra is its native calculus ([n-ary relations and relational
   algebra](../01-foundations/n-ary-relations-and-relational-algebra.md)). Exactly one embedding
   model was built to respect that calculus — ReAlE. Nothing has picked the idea up, least of all
   the LLM-retrieval systems that would benefit. Sections 2 and 3.

Section 4 reproduces the two-axis taxonomy that organises the whole field and corrects a common
misreading of it.

---

## 1. Hyperbolic and hierarchical geometry for n-ary facts

### 1.1 The argument

Hyperbolic space has exponential volume growth, so a tree of branching factor *b* embeds in it with
low distortion at fixed dimension, which Euclidean space cannot do. The n-ary version of the
argument: entity hierarchies in a knowledge base grow superlinearly along the relation structure, so
the curvature should be negative. Note that this is an **argument by analogy**, not a measurement —
none of the papers below reports a δ-hyperbolicity or Gromov-hyperbolicity statistic for JF17K,
FB-AUTO or WikiPeople, and this KB has found no such measurement anywhere (checked 2026-09-21).
That absence is the single biggest weakness of the family.

### 1.2 The whole literature, verified

Five papers, and four of the five share an author group.

| Model | Authors | Venue | Geometry | Formalisation |
|---|---|---|---|---|
| **HYPER²** | Yan, Zhang, Sun, Xu, Jin, Li | *Neurocomputing* 492:440–451, 2022; preprint [arXiv:2104.09871](https://arxiv.org/abs/2104.09871) (20 Apr 2021) | Poincaré ball; aggregation done **on the tangent space** | hyper-relational (primary triple kept) |
| **PolygonE** | Yan, Zhang, Sun, Xu, Li, Liu, Liu, Wang | *AAAI 2022* 36(4):4308–4317, [DOI 10.1609/aaai.v36i4.20351](https://doi.org/10.1609/aaai.v36i4.20351) | gyrovector space; a fact is a **gyro-polygon**, scored by vertex-to-gyrocentroid geodesic | hyperedge (any arity) |
| **(W)PolygonE+** — "gyro-polygons with learnable gyro-centroid" | Yan, Zhang, Xu, Sun, Li, Wang | *Knowledge-Based Systems* 251:109164, 2022, [DOI 10.1016/j.knosys.2022.109164](https://doi.org/10.1016/j.knosys.2022.109164) | as PolygonE, plus a learned (weighted) gyrocentroid | hyperedge |
| **H²GNN** | Li, Shi, Qiao, Zhang, Jin | [arXiv:2412.12158](https://arxiv.org/abs/2412.12158), 11 Dec 2024 — **preprint only**, v1, no journal-ref or DOI as of 2026-09-21 | Lorentz (hyperboloid) model, centroid by squared Lorentzian distance | hyperedge, position-typed |
| **GAHE** | Cao, Xu, Yang, He, Cao, Huang | *ACM TOMM*, 2025 | **multi-curvature**: Euclidean + hyperbolic + spherical subspaces, position-dependent sub-relations | hyper-relational |

The first three are the "hyperbolic family" already noted in
[knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) §2022; all
three were marked `[unverified]` there because they were cited second-hand through
[Wei et al. 2025](https://arxiv.org/abs/2506.08970). They are now verified against Crossref and the
publishers' own records, and one correction follows: HYPER² is *Neurocomputing* **2022**, volume 492,
pages 440–451, by six authors (Yan, Zhang, Sun, Xu, Jin, Li) — not a separate 2022 Neurocomputing
paper distinct from the arXiv preprint arXiv:2104.09871, which is the same work.

GAHE is new to this KB and is the most interesting of the five conceptually: rather than betting on
one curvature it learns which subspace each qualifier slot lives in. Its claim is that mixed
structural patterns — "chains, rings, and hierarchical patterns" — coexist in one hyper-relational
graph, which is precisely the objection to a globally hyperbolic model
([Lu, Tupikina and Alam, IEEE TKDE 2026](https://arxiv.org/abs/2506.05626) §IV-A2). The full text of
GAHE was not read for this note, so its numbers are `[unverified]` here.

### 1.3 H²GNN in detail — what it does and what the result actually shows

H²GNN is the paper the seed brief pointed at, and it is worth reading carefully because the headline
and the table do not say the same thing.

**Hyper-star message passing.** For an n-ary fact `r(e₁,…,eₙ)` the model instantiates the hyperedge
as a node and connects it to each participating entity through a **position-typed relation**: the
tuple `(Roster, Bucks, Guard, Jrue Holiday)` yields edges labelled `Roster-1`, `Roster-2`,
`Roster-3` ([Li et al. 2024](https://arxiv.org/abs/2412.12158), Figure 1). The result is a two-level
(hyperedge → entity) tree, hence "hyper-star", and message passing runs in two stages: φ₁ aggregates
entity embeddings into the hyperedge embedding, φ₂ updates each entity from the hyperedge embedding,
the hyper-relation embedding and the position embedding, with separate transforms `W_h`, `W_r`,
`W_p`. All aggregation is done in Lorentz space by a squared-Lorentzian-distance centroid, so the
model is closer to "fully hyperbolic" than HYPER², which aggregates on the tangent space.

**The "lossless" claim is asserted, not proved.** The paper describes the expansion as "a lossless
expansion of hyperedges into hierarchies" but gives no theorem and no inverse map; the argument is
the informal one that clique expansion "creates unreal connections" whereas position-typed star
expansion does not. The *proved* information-preserving expansion in this literature is TransEQ's
equivalent transformation with mediator entities and sub-relations
([Liu et al., arXiv:2411.06191](https://arxiv.org/abs/2411.06191)); see
[hypergraph-neural-networks.md](hypergraph-neural-networks.md) on clique vs. star expansion. Read
hyper-star expansion as *star expansion with position-typed incidence*, which is a sensible design
and an old idea, not as a new losslessness result.

**Node classification is on plain hypergraphs, not knowledge hypergraphs.** The node-classification
datasets are the standard co-authorship/co-citation ones — DBLP, Cora (co-authorship and
co-citation), PubMed, Citeseer — which have no relations and no roles. Best accuracies
([Li et al. 2024](https://arxiv.org/abs/2412.12158), Table 2): H²GNN 89.75 ± 0.20 on DBLP against
UniGIN 88.34 ± 0.21 and UniSAGE 88.29 ± 0.22; 62.52 ± 1.48 on Citeseer against UniSAGE 61.27 ± 1.78.
Gains of one to two points on datasets where the standard deviation is one to two points. The
inductive ("evolving hypergraph") table is more convincing — 85.5 ± 0.5 unseen-node accuracy on
PubMed against UniGIN's 83.1 ± 0.4, with UniGCN and UniGAT collapsing to 15–30% on three of four
datasets (Table 3).

**Link prediction is on knowledge hypergraphs, and here is the problem.** H²GNN is used as an
*encoder* with HSimplE, m-TransH or m-DistMult as decoder. With HSimplE
([Li et al. 2024](https://arxiv.org/abs/2412.12158), Tables 4–5):

| | FB-AUTO MRR | FB-AUTO Hits@10 | JF17K MRR | JF17K Hits@10 |
|---|---|---|---|---|
| H²GNN-HSimplE | 0.757 | 0.884 | 0.498 | 0.669 |
| HSimplE alone | 0.692 | 0.825 | 0.451 | 0.633 |
| HypE, **as re-run by H²GNN** | 0.737 | 0.844 | 0.489 | 0.652 |
| HypE, **as reported by its own authors** | **0.804** | 0.856 | 0.494 | 0.656 |
| **ReAlE** (same datasets, same protocol) | **0.861** | **0.908** | **0.530** | **0.677** |

The encoder clearly helps its own decoder (+0.065 MRR on FB-AUTO over bare HSimplE). But the
comparison that supports "outperforms state-of-the-art approaches" uses a HypE run 0.067 MRR below
the number HypE's authors published ([Fatemi et al., IJCAI
2020](https://arxiv.org/abs/1906.00137), Table 1; reproduced in
[knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) §4b), and the
paper never compares against ReAlE, which is by the same group, on the same three datasets, under
the same all-positions protocol, and is 0.104 MRR ahead on FB-AUTO. **On the evidence in the paper,
H²GNN is not state of the art for knowledge-hypergraph link prediction; a 2021 Euclidean model with
no message passing at all is.** This is the reproducibility failure mode catalogued in
[reproducibility-of-n-ary-link-prediction.md](reproducibility-of-n-ary-link-prediction.md), not a
statement about hyperbolic geometry.

**The ablation is the honest part.** Removing the hyperbolic operations (replacing the Lorentz
centroid by Euclidean averaging) costs performance, but removing the position-aware composition
costs "substantial[ly]" more ([Li et al. 2024](https://arxiv.org/abs/2412.12158), §4.4, Figure 6 —
the figure's numbers were not extractable from the HTML, so the magnitudes are `[unverified]`). The
paper's own reading is that in a *knowledge* hypergraph "the diversity in relation types and the
roles of entities in relations" dominates, and hyperbolicity is a second-order effect. That is the
most useful sentence in the paper and it argues against the title.

**Status.** No code repository is named in the paper; arXiv shows one version and no journal
reference as of 2026-09-21; the paper is nonetheless indexed in the TKDE taxonomy below, so it is
not obscure.

### 1.4 The honest summary of the hyperbolic line

- **Established:** hyperbolic embeddings of *hierarchies* are better than Euclidean at low
  dimension. Nobody disputes this outside the n-ary setting.
- **Active research:** whether n-ary knowledge bases are hierarchical enough for it to pay. Five
  papers, three of them from one group, no shared protocol, no curvature measurement.
- **Not established:** that any hyperbolic n-ary model beats the best Euclidean one. The strongest
  published n-ary number on the FB-AUTO/JF17K/M-FB15K triple under the all-positions protocol
  remains ReAlE's (§2.5), and no hyperbolic paper reports against it.

---

## 2. ReAlE: an embedding model with an algebraic interface

### 2.1 Provenance — and a correction

ReAlE was written up as [arXiv:2102.09557](https://arxiv.org/abs/2102.09557) (18 Feb 2021) and
published as **Bahare Fatemi, Perouz Taslakian, David Vazquez, David Poole, "Knowledge Hypergraph
Embedding Meets Relational Algebra", *Journal of Machine Learning Research* 24(105):1–34, 2023**
(<https://www.jmlr.org/papers/v24/22-063.html>), with an ICML 2023 journal-track poster
(<https://icml.cc/virtual/2023/poster/25671>). Existing notes cite only the preprint; the JMLR
reference is the one to use.

**Correction to [machine-learning-era.md](../08-history-and-frontier/machine-learning-era.md) (~line
115) and [glossary.md](../00-index/glossary.md) (~line 1300):** both list the represented primitives
as "renaming, projection, union, selection, join". The paper's list is **renaming, projection, set
union, selection, and set difference** — *set difference, not join*. The distinction is not
cosmetic. Codd's primitive set is {selection, projection, Cartesian product, set union, set
difference} plus rename; ReAlE covers every one of them **except Cartesian product**, and join is
exactly selection composed with Cartesian product. So the one primitive ReAlE does not claim is
precisely the one that makes relational algebra relationally interesting, and the one whose cost is
governed by the AGM bound
([n-ary relations and relational algebra](../01-foundations/n-ary-relations-and-relational-algebra.md)
§4).

### 2.2 The mechanism: windows

ReAlE is a tensor-factorisation model. The embedding dimension *d* is partitioned into `n_w = ⌊d/w⌋`
**windows** of size *w*; elements interact only inside a window; a nonlinearity σ turns each window
into a scalar contribution, and the contributions are summed with a per-relation, per-window bias
`b_r^j` ([Fatemi et al. 2023](https://www.jmlr.org/papers/v24/22-063.html) §4). That is the whole
model — no message passing, no attention. The window size is the sensitive hyperparameter: on JF17K
MRR peaks between w = 2 and w = 4 and falls off at w = 1 (no interaction) and at large w (too much),
which is a clean, small result about how much intra-embedding interaction an n-ary model needs.

### 2.3 Full expressivity, with the exact bound

> **Theorem 1 (Expressivity).** For any ground truth over entities ℰ and relations ℛ containing λ
> true tuples, with α = max_{r∈ℛ}(|r|) the maximum arity, there is a ReAlE model with `n_w = λ`,
> `w = α`, `d = max(αλ, α)` and `σ(x) = 1/(1+exp(−x))` that accurately separates the true tuples
> from the false ones.

So: one window per true tuple, window size equal to the maximum arity. This is the usual form of a
full-expressivity result — it is a *representation* guarantee at a dimension linear in the number of
facts, not a learnability or generalisation guarantee, and it says nothing about what a trained model
at d = 200 does. Read it as ruling out the *opposite* result: **Theorem 2** shows m-TransH, RAE and
NaLP are *not* fully expressive and have structural restrictions on the relations they can represent
(G-MPNN likewise, argued in §2 of the paper).

### 2.4 What "provably represents" means, operation by operation

The five theorems are not all the same strength, and the paper is explicit about why.

| Operation | Rule | Guarantee |
|---|---|---|
| **Renaming** (argument permutation π) | `t(X₁,…,Xₙ) ↔ s(X_{π(1)},…,X_{π(n)})` | **Equality** of scores: `φ(t(x̄)) = φ(s(x_{π(1)},…))`, for arbitrary entity embeddings (Thm 3) |
| **Projection** | `∀X₁…X_m t(X̄) ↔ ∃X_{m+1}…X_n s(X₁,…,X_n)`, m < n | **Inequality**: `φ(t(x₁,…,x_m)) ≥ φ(s(x₁,…,x_n))` (Thm 4) |
| **Selection** (`X_n = c`, or `X_{n−1} = X_n`) | — | Two theorems, Thms 5 and 6; arbitrary `X_p = X_q` reduces to these by first renaming |
| **Set union** | `t(X̄) ↔ s(X̄) ∨ r(X̄)` | **Inequality**: `φ(t(x̄)) ≥ max(φ(s(x̄)), φ(r(x̄)))` (Thm 7) |
| **Set difference** | `t(X̄) ← s(X̄) ∧ ¬r(X̄)` | **Inequality**: `φ(t(x̄)) ≤ min(φ(s(x̄)), f(φ(r(x̄))))`, for a linear relation-complement `f` with `f(σ(x)) = σ(cx)` (Thm 8) |

The inequalities are not sloppiness. The paper's own justification: the score of a union depends on
how dependent the two relations are (if s ⊆ r then t scores as r), "and since we do not know about
such dependence relations in the data, then the best we can hope for is a bound". That is the right
answer, but it means the phrase "provably represents relational algebra" should be read as **the
model can be parametrised so that the induced scores satisfy the algebraic ordering constraints** —
soundness of the ordering, not exactness of the semantics. Only renaming is exact.

The complementary negative result is worth as much: **HypE cannot represent selection** (Thm 9), and
when the embedding size is less than the number of entities — i.e. always — there is *no* embedding
setting under which HypE could (Thm 10). Positional convolution is not enough to express `X_p = X_q`.

### 2.5 The numbers, and why they matter for §1

Same protocol as HypE (all positions of the tuple; see
[benchmarks-and-evaluation-protocols.md](benchmarks-and-evaluation-protocols.md)), from
[Fatemi et al. 2023](https://www.jmlr.org/papers/v24/22-063.html) Table 1:

| Model | JF17K MRR / H@10 | FB-AUTO MRR / H@10 | M-FB15K MRR / H@10 |
|---|---|---|---|
| HypE | 0.494 / 0.656 | 0.804 / 0.856 | 0.777 / 0.881 |
| G-MPNN | 0.501 / 0.660 | — | 0.779 / 0.894 |
| **ReAlE** | **0.530 / 0.677** | **0.861 / 0.908** | **0.801 / 0.901** |

GETD is reported at JF17K MRR 0.151 here because the paper's mixed-arity setting forces an embedding
size under 10 to fit `d^{|r|}` parameters per relation in 16 GB — a memory artefact, not a model
result, and an illustration of why cross-paper numbers need reading. These are the strongest
verified all-positions numbers in this KB, and they are five years old.

---

## 3. The planner–store interface gap

The seed formulation is good enough to keep: **the planner speaks English; the store speaks cosine.**
An LLM agent decomposes a question into sub-goals in natural language; the retrieval layer it calls
takes a string and returns nearest neighbours. Nothing in between speaks the algebra that the data
actually has. ReAlE is the one KHG model whose parameter space was designed to *contain* that
algebra — and nobody has exposed it.

### 3.1 What does exist

**(a) Relational-algebra-shaped operators over tables, implemented by LLM calls.** The closest thing
to a real answer is **semantic operators** — `sem_filter`, `sem_join`, `sem_agg`/group-by,
`sem_topk` — "the first formalism for declarative and general-purpose AI-based transformations based
on natural language specifications (e.g. filtering, sorting, joining or aggregating records using
natural language criteria)", where "each operator opens a rich space for execution plans, similar to
relational operators" ([Patel, Jha, Pan, Gupta, Asawa, Guestrin and Zaharia, *Semantic Operators: A
Declarative Model for Rich, AI-based Data Processing*,
arXiv:2407.11418](https://arxiv.org/abs/2407.11418); implemented in LOTUS,
<https://github.com/lotus-data/lotus>; a version appears in *PVLDB* 18 as "Semantic Operators and
Their Optimization", <https://www.vldb.org/pvldb/vol18/p4171-patel.pdf>). Crucially this is
relational algebra *lifted* to natural-language predicates over rows, with an optimiser and accuracy
guarantees against a "gold algorithm" — not algebra over an embedding store, and not over n-ary
facts. It is the right shape and the wrong substrate.

**(b) Logical operators inside a query-embedding model.** StarQE, NQE, SQE and LKHGT answer
conjunctive / existential-fragment queries over hyper-relational graphs by composing learned
operators — see
[logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md)
and [query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md) §"CQA as a learned
query language". But the operators are internal to the model: the agent hands over a query graph and
receives answers. There is no `project(r, [1,3])` a planner can call, no intermediate relation it can
name, inspect or reuse.

**(c) Graph actions in agentic KG frameworks.** GraphRAG-style and agentic KGQA systems expose
neighbourhood expansion, path retrieval and community/ego-network selection as tools. These are
*topological* operators, not algebraic ones: they have no notion of arity, argument position,
projection or difference.

### 3.2 The gap, stated precisely

As of **2026-09-21**, no system found by this KB exposes relational-algebra primitives over a
knowledge-hypergraph *embedding* store as planner-callable operations. Concretely, nothing offers an
LLM planner a tool surface like:

```
rename(r, π) · project(r, positions) · select(r, position = c | pos_i = pos_j)
union(r, s) · difference(r, s)      → a named intermediate relation, scored, reusable
```

even though ReAlE proves that a single trained embedding can carry all five, and even though the
resulting plans would be the natural target for a text-to-plan model — substantially easier to
generate than SPARQL and substantially more compositional than a similarity search. The pieces exist
in three separate literatures (LOTUS's optimiser, ReAlE's parametrisation, StarQE/NQE's query
encoders) and have never been put in one system.

Two reasons this is more than a feature request:

1. **It changes what an error means.** A cosine-similarity miss is unattributable. A plan of named
   algebraic steps localises the failure to one operator, which is what
   [explainability-and-uncertainty.md](explainability-and-uncertainty.md) needs and does not have.
2. **It is the only route to monotone guarantees at plan level.** ShrinkE gives qualifier
   monotonicity inside one fact; ReAlE's Theorems 4, 7 and 8 give score bounds across relations.
   Together they would let a planner reason about whether adding a step can only narrow an answer
   set — the n-ary analogue of the containment reasoning a query optimiser does for free.

A minimal experiment: train ReAlE on JF17K; expose the five operators as functions returning a
scored candidate set; have an LLM emit operator plans for the WD50K-QE or NQE query patterns; compare
against the end-to-end query-embedding models on the same patterns. Nothing in the literature
reports this.

---

## 4. The two-dimensional taxonomy, verified

[Lu, Tupikina and Alam, *Two-dimensional Taxonomy for N-ary Knowledge Representation Learning
Methods*, IEEE TKDE (accepted; author's accepted manuscript, 20 pages) /
arXiv:2506.05626 v3](https://arxiv.org/abs/2506.05626) — manuscript received 27 June 2025, revised
8 June 2026, accepted 29 August 2026; the authors are at the University of Rouen Normandy, Nokia
Bell Labs Paris and Télécom Paris.

### 4.1 The exact axis labels

- **Methodology axis:** translation-based · tensor factorisation-based · deep neural network-based
  (subdivided FCN / CNN / Transformer / GNN / HNN) · logic rule-based · hyperedge expansion-based.
  The abstract lists five; §IV merges the last two into one bullet ("Logic rules and hyperedge
  expansion-based methods") while Table II keeps them as separate rows.
- **Semantic-awareness axis:** **position-aware · role-aware · aware-less**. Note the third label is
  **"aware-less"**, not "unaware".

The definitions, quoted:

- *Position-aware*: models that "explicitly rely on the position index or relative position of
  entities within an n-ary fact, for example by using position embeddings, slot-specific projection
  matrices, or fixed weights for each position. Here, position serves only as a coarse proxy for
  semantic roles."
- *Role-aware*: models that "explicitly encode semantic roles, such as relation-specific roles,
  qualifier relations, or role-value pairs […] so that the same entity may contribute differently
  when it appears under different roles, and these roles can be shared across different relations."
  **A model that encodes both positions and roles is assigned to this category** — the axis is a
  ladder, not a partition.
- *Aware-less*: models that "do not explicitly encode either positional or role information […]
  treat the entities in a fact as an unordered (or only weakly ordered) collection."

### 4.2 Table II, reproduced

Transcribed from the v3 HTML, 2026-09-21.

| Methodology | Role-aware | Position-aware | Aware-less |
|---|---|---|---|
| Translation-based | — | m-TransH, BoxE | RAE |
| Tensor factorisation-based | RAM | m-CP, HSimplE, HypE, **ReAlE**, GAHE, PosKHG* | r-SimplE, m-DistMult, GETD, S2S |
| Deep NN — FCN | NeuInfer, NaLP, t-NaLP, ShrinkE | — | — |
| Deep NN — CNN | HINGE | HyConvE, LPACN, HJE, HySAE | HyCubE |
| Deep NN — Transformer | GRAN, HyNT, Hy-Transformer, HyperMono, HyperFM | LKHGT | — |
| Deep NN — GNN | StarE, StarQE, QUAD, HAHE, HyperFormer, HypeTKG, NE-Net, HyperCL | MAYPL | — |
| Deep NN — HNN | SDK, RHKH | G-MPNN, **H²GNN**, **HYPER** | KHG-Aclair, Zhang et al., HyperQuery |
| Logic rule-based | HyperMLN | — | — |
| Hyperedge expansion-based | TransEQ | — | — |

\* Table II places **PosKHG** in the position-aware column, but the prose discusses it in §IV-B1,
the *role-aware* tensor-factorisation subsection, and §III describes it as one that "further
incorporates role-aware semantic modelling". Treat that cell as ambiguous; the paper is internally
inconsistent here.

### 4.3 Correction: role-aware is the *largest* class, not the thinnest

Counting Table II: **role-aware ≈ 23 models, position-aware ≈ 17, aware-less ≈ 9** (49 in total,
matching the field's own "nearly 50 methods" census in
[Wei et al. 2025](https://arxiv.org/abs/2506.08970)). The intuition that "position-aware dominates
and role-aware work is thin" is **wrong as a headcount**. What is true is narrower and more
interesting:

- **Role-awareness is concentrated in the neural branch.** 21 of the ~23 role-aware models are deep
  neural, logic-rule or expansion models. The role-aware cells for *translation-based* methods are
  **empty**, and the role-aware tensor cell contains exactly one model (RAM). Geometry and roles have
  barely met.
- **Position-awareness is concentrated where geometry lives.** Every model in this KB's hyperbolic
  family that the survey indexes — H²GNN, GAHE — is position-aware, as are HypE, ReAlE and HYPER.
  Curvature has been paired with argument *indices*, never with named roles.
- **"Role-aware" here means qualifier-aware, not linguistically role-aware.** The category is
  satisfied by any model that gives qualifier relations their own parameters — which is most
  Wikidata-shaped models. Semantic roles in the *linguistic* sense (agent, patient, instrument;
  PropBank/FrameNet role inventories shared across predicates) do not appear in the survey at all,
  and this KB has found no n-ary link-prediction model that uses such an inventory (checked
  2026-09-21). **That** is the thin part, and the seed's intuition survives in this restated form.

### 4.4 What the taxonomy does not cover

Absent from Table II and from the text of v3 (grep of the v3 HTML, 2026-09-21): **HCNet**, **HART**,
**THOR**, **HYPER²**, **PolygonE** and the gyro-centroid follow-up. So the survey indexes the two
*hyperbolic/multi-curvature* models that are also GNN-shaped (H²GNN, GAHE) and misses the three
earlier hyperbolic *scoring-function* models entirely — the "gyro" word does not occur in the paper.
It also misses the relational-Weisfeiler–Leman theory line (HCNet,
[Huang et al., TMLR 2025](https://arxiv.org/abs/2402.04062)) even though it indexes HCNet's successor
HYPER. Two consequences: the taxonomy is a good map of *architectures* and a poor map of
*expressivity theory*; and anyone using it as a completeness check on the hyperbolic literature will
miss three of the five papers in §1.2.

On the frontier models named in the brief: **HYPER** is position-aware / HNN-based, described as
overcoming "the geometric rigidity and limited reasoning depth of H²GNN" by disentangling local
position-aware convolution from global hyperedge attention
([Lu et al. 2026](https://arxiv.org/abs/2506.05626) §IV-A3). **HCNet**, **HART** and **THOR** are
unplaced; on the survey's own definitions HCNet and HART would be role-aware (both parametrise
relation–position pairs / roles explicitly — see
[inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md)), and that placement is
this note's inference, not the survey's.

---

## 5. Has hyperbolic geometry been combined with HYPER-style relation graphs?

**No, as of 2026-09-21.** The search for it:

- arXiv full-text search for `"knowledge hypergraph" AND hyperbolic` returns exactly one paper
  (H²GNN); `"hyper-relational" AND hyperbolic` returns three (H²GNN, HYPER², NestE);
  `"relational hypergraph" AND "foundation model"` returns none (export.arxiv.org API, 2026-09-21).
- The two ingredients are each mature. HYPER's contribution is a **relation graph** — relations are
  embedded from their interaction structure rather than from a fixed vocabulary, which is what makes
  it inductive over *unseen relations*
  ([Huang, Galkin, Bronstein and Ceylan, arXiv:2506.12362](https://arxiv.org/abs/2506.12362); ICLR
  2026 per the authors' repository). Hyperbolic aggregation in the n-ary setting is H²GNN's.
- The nearest existing combination is **binary only**: a geometry-augmented ULTRA-style knowledge
  graph foundation model that replaces ULTRA's single relational transformation with parallel
  algebraic transformations (real, complex, split-complex, dual) under relation-conditioned
  attention ([Xin, Nayyeri, Makki Nayeri and Staab, *Geometric Structural Knowledge Graph Foundation
  Model*, arXiv:2512.22931](https://arxiv.org/abs/2512.22931), 28 Dec 2025) — a relation graph plus
  geometry, but for triples, and the geometries are not hyperbolic. `[unverified]` beyond the
  abstract.

Why the combination is not obviously a good idea, which may be why nobody has done it: a relation
graph is a *learned, shared* structure over the relation vocabulary, and hyperbolic aggregation
assumes a tree-like hierarchy over *entities*. The curvature that suits the entity hierarchy need not
suit the relation graph, which is precisely GAHE's argument for mixing curvatures per subspace. A
principled attempt would therefore need two curvatures, or a product manifold, and a measurement of
each side's hyperbolicity — which, per §1.1, nobody has published for any n-ary dataset.

---

## Open questions raised here

- Is any n-ary benchmark actually hyperbolic? No δ-hyperbolicity or Gromov-hyperbolicity statistic
  has been published for JF17K, FB-AUTO, M-FB15K, WikiPeople or WD50K, so the entire hyperbolic
  family rests on an analogy. This is cheap to settle and would tell the field whether to keep going.
- Would ReAlE's algebraic primitives survive being exposed as planner-callable operators, and would
  an LLM plan over them beat an end-to-end query-embedding model on WD50K-QE / NQE query patterns?
- Does the ReAlE parametrisation extend to Cartesian product (hence join), or is there an
  impossibility result for score-based models analogous to Theorem 10's for HypE and selection?
- Is there any n-ary link-prediction model that uses a *linguistic* role inventory (PropBank,
  FrameNet, VerbNet) rather than dataset-specific role strings, so that roles transfer across
  relations and across datasets?
- Does combining a HYPER-style relation graph with a hyperbolic (or product-manifold) entity space
  help, and does it need two curvatures?
- What happens to the H²GNN result if it is re-run against ReAlE and against HypE at its published
  numbers, on the same splits?

## Sources

- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraph Embedding Meets Relational Algebra" (ReAlE). *Journal of Machine Learning Research* 24(105):1–34, 2023; ICML 2023 journal-track poster; preprint arXiv:2102.09557, 18 February 2021. <https://www.jmlr.org/papers/v24/22-063.html> · <https://arxiv.org/abs/2102.09557> · <https://icml.cc/virtual/2023/poster/25671>
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations" (HypE/HSimplE). *IJCAI 2020*, pp. 2191–2197; arXiv:1906.00137. <https://arxiv.org/abs/1906.00137>
- Li, M., Shi, X., Qiao, C., Zhang, T., Jin, H. "Hyperbolic Hypergraph Neural Networks for Multi-Relational Knowledge Hypergraph Representation" (H²GNN). arXiv:2412.12158, 11 December 2024 (v1; no journal reference or DOI as of 2026-09-21). <https://arxiv.org/abs/2412.12158>
- Yan, S., Zhang, Z., Sun, X., Xu, G., Jin, L., Li, S. "HYPER²: Hyperbolic embedding for hyper-relational link prediction." *Neurocomputing* 492:440–451, 2022, DOI 10.1016/j.neucom.2022.04.026; preprint arXiv:2104.09871, 20 April 2021. <https://arxiv.org/abs/2104.09871>
- Yan, S., Zhang, Z., Sun, X., Xu, G., Li, S., Liu, Q., Liu, N., Wang, S. "PolygonE: Modeling N-ary Relational Data as Gyro-Polygons in Hyperbolic Space." *AAAI 2022*, 36(4):4308–4317. <https://doi.org/10.1609/aaai.v36i4.20351> · PDF <https://cdn.aaai.org/ojs/20351/20351-13-24364-1-2-20220628.pdf>
- Yan, S., Zhang, Z., Xu, G., Sun, X., Li, S., Wang, S. "Modeling N-ary relational data as gyro-polygons with learnable gyro-centroid." *Knowledge-Based Systems* 251:109164, 2022. <https://doi.org/10.1016/j.knosys.2022.109164>
- Cao, Z., Xu, Q., Yang, Z., He, Y., Cao, X., Huang, Q. "GAHE: Geometry-aware embedding for hyper-relational knowledge graph representation." *ACM Transactions on Multimedia Computing, Communications and Applications*, 2025. Bibliographic details via the reference list of Lu et al. 2026; full text not read `[unverified]`.
- Lu, X., Tupikina, L., Alam, M. "Two-dimensional Taxonomy for N-ary Knowledge Representation Learning Methods." *IEEE Transactions on Knowledge and Data Engineering* (accepted 29 August 2026; author's accepted manuscript, 20 pp.); arXiv:2506.05626 v3. <https://arxiv.org/abs/2506.05626> · <https://doi.org/10.1109/TKDE.2026.3731554>
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." EMNLP 2025; arXiv:2506.08970. <https://arxiv.org/abs/2506.08970>
- Patel, L., Jha, S., Pan, M., Gupta, H., Asawa, P., Guestrin, C., Zaharia, M. "Semantic Operators: A Declarative Model for Rich, AI-based Data Processing." arXiv:2407.11418, 2024–2025; *PVLDB* 18 ("Semantic Operators and Their Optimization"). Implemented in LOTUS. <https://arxiv.org/abs/2407.11418> · <https://www.vldb.org/pvldb/vol18/p4171-patel.pdf> · <https://github.com/lotus-data/lotus>
- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. "HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs." arXiv:2506.12362, 14 June 2025; ICLR 2026 per <https://github.com/HxyScotthuang/HYPER>. <https://arxiv.org/abs/2506.12362>
- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. "Link Prediction with Relational Hypergraphs" (HCNet). *TMLR* 2025; arXiv:2402.04062. <https://arxiv.org/abs/2402.04062>
- Liu, Y., Yang, X., Ding, B., Yao, Q., Li, Y. "Generalizing Hyperedge Expansion for Hyper-relational Knowledge Graph Modeling" (TransEQ). arXiv:2411.06191, 9 November 2024. <https://arxiv.org/abs/2411.06191>
- Xin, L., Nayyeri, M., Makki Nayeri, Z., Staab, S. "Geometric Structural Knowledge Graph Foundation Model." arXiv:2512.22931, 28 December 2025. Abstract only `[unverified]`. <https://arxiv.org/abs/2512.22931>
- Codd, E. F. "A relational model of data for large shared data banks." *Communications of the ACM* 13(6):377–387, 1970. <https://dl.acm.org/doi/10.1145/362384.362685>
