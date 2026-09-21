---
title: HYPER anatomy — architecture, theory, cost and lineage of the knowledge-hypergraph foundation model
type: paper-note
status: draft
tags: [hyper, hcnet, hc-mpnn, ultra, kg-icl, nbfnet, astar-net, ingram, foundation-model, inductive, positional-encoding, relation-graph, pretraining, triton, iclr-2026]
created: 2026-09-21
updated: 2026-09-21
---

# HYPER, taken apart

A close reading of **HYPER** ([Huang, Galkin, Bronstein and Ceylan, arXiv:2506.12362
v3, 8 May 2026](https://arxiv.org/abs/2506.12362)) and of its neural substrate **HCNet / HC-MPNN**
([Huang, Romero Orth, Barceló, Bronstein and Ceylan, *Link Prediction with Relational Hypergraphs*,
TMLR 2025 / arXiv:2402.04062](https://arxiv.org/abs/2402.04062)), plus the binary knowledge-graph
foundation-model precursors that HYPER inherits from and competes with.

This note is the mechanism. The *results* live in
[inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md) §2–3; the model's place in
the 2016–2026 chronology is in
[knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) §3; the
expressivity context is in [hypergraph-neural-networks.md](hypergraph-neural-networks.md) §3.

---

## 0. Venue: settled

The knowledge base previously recorded the venue as unresolved ("NeurIPS 2025 workshop vs. ICLR
2026 unconfirmed"). It is resolved. The paper is a **conference paper at ICLR 2026**:

- OpenReview forum `YLTQbMoAaX`, whose PDF carries the header line "Published as a conference paper
  at ICLR 2026" (<https://openreview.net/pdf?id=YLTQbMoAaX>; the OpenReview HTML and API were
  behind a bot challenge when checked on 2026-09-21, so the header line comes from the indexed PDF).
- The authors' repository title and its BibTeX entry both say `booktitle={International Conference
  on Learning Representations}, year={2026}` (<https://github.com/HxyScotthuang/HYPER>, checked
  2026-09-21).
- The arXiv v3 text contains an ICLR ethics statement and a reproducibility statement, which is the
  ICLR camera-ready template.

The NeurIPS 2025 "New Perspectives in Graph Machine Learning" workshop presentation
(<https://neurips.cc/virtual/2025/127653>) is a separate, earlier event, not a conflicting venue.
Cite HYPER as **ICLR 2026**.

**Version matters.** v1 (14 Jun 2025), v2 (13 Feb 2026) and v3 (8 May 2026) differ in their
baseline numbers and in one of the paper's headline conclusions; see §8. Cite v3.

## 1. What the model is for, in one table

The paper's own capability matrix (v3, Table 1) is the clearest statement of the gap HYPER claims to
close. `High-arity` = can represent a k-ary fact natively; `Ind. e` = generalises to unseen
entities; `Ind. r` = generalises to unseen relations.

| Methods | High-arity | Ind. *e* | Ind. *r* |
|---|:--:|:--:|:--:|
| HypE, BoxE | ✓ | ✗ | ✗ |
| NBFNet, A*Net | ✗ | ✓ | ✗ |
| G-MPNN, HCNet | ✓ | ✓ | ✗ |
| ULTRA, KG-ICL | ✗ | ✓ | ✓ |
| **HYPER** | ✓ | ✓ | ✓ |

Read as a claim about the literature this is accurate but generous to itself: the bottom row is a
claim of novelty, not a measured quantity, and the ✗ in the ULTRA/KG-ICL row means "not natively",
not "cannot be made to run" — both *can* be run on a reified hypergraph, which is exactly the
comparison the paper then makes.

## 2. Lineage

Two lines converge.

**The binary line — conditional message passing, then foundation models.**

| Year | Model | Contribution that HYPER uses |
|---|---|---|
| 2020 | GraIL ([Teru et al.](https://arxiv.org/abs/1911.06962)) | node-inductive link prediction by subgraph labelling |
| 2021 | **NBFNet** ([Zhu, Zhang, Xhonneux, Tang, NeurIPS 2021](https://arxiv.org/abs/2106.06935)) | link prediction as a learned generalised Bellman–Ford recursion: representations of a *pair* of nodes, conditioned on the query head and relation. This is "conditional message passing" |
| 2023 | **A\*Net** ([Zhu, Yuan, Galkin, Xhonneux, Zhang, Gazeau, Tang, NeurIPS 2023](https://arxiv.org/abs/2206.04798)) | a learned priority function prunes NBFNet's frontier; competitive while "merely visiting 10% nodes and 10% edges at each iteration" |
| 2023 | **InGram** ([Lee, Chung, Whang, ICML 2023](https://arxiv.org/abs/2305.19987)) | the **relation graph**: a weighted graph over relations with affinity weights, from which embeddings of *new relations* are generated at inference. HYPER's benchmark construction protocol (25/50/75/100% unseen relations) is InGram's |
| 2024 | **ULTRA** ([Galkin, Yuan, Mostafa, Tang, Zhu, ICLR 2024](https://arxiv.org/abs/2310.04562)) | relational representations as a function of *relation interactions*: the four fundamental relations head-to-head, head-to-tail, tail-to-head, tail-to-tail, then two-stage conditional message passing (relation graph, then entity graph) |
| 2024 | **KG-ICL** ([Cui, Sun, Hu, NeurIPS 2024](https://arxiv.org/abs/2410.12288)) | the alternative route to a KGFM: a **prompt graph** centred on a query-related example fact, a unified tokeniser mapping entities and relations to predefined tokens, and two MPNNs (prompt encoding, KG reasoning); evaluated on 43 KGs |
| 2024–25 | TRIX, MOTIF | recursive relation/entity updates provably beyond ULTRA (TRIX); a general KGFM framework with an expressivity theory (MOTIF, [Huang et al. 2025a](https://arxiv.org/abs/2506.12362) as cited in HYPER §2) |

**The n-ary line.** G-MPNN ([Yadati, NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/217eedd1ba8c592db97d0dbe54c7adfc-Abstract.html)) → RD-MPNN
(2023) → **HC-MPNN / HCNet** (TMLR 2025). HYPER = ULTRA's two-stage shape, with HCNet in place of
NBFNet at both stages, and the four fundamental relations replaced by a *function* of position
pairs. **THOR** ([Yu, Lu and Yang, arXiv:2602.05424, 2026](https://arxiv.org/abs/2602.05424)) is the
same idea rebuilt for the hyper-relational (main-triple + qualifiers) formalisation rather than the
positional n-ary one.

A small piece of shared plumbing marks the descent concretely: NBFNet's CUDA `rspmm`
(relational sparse-matrix multiplication) kernel is re-used in ULTRA, re-used again in KG-ICL
(`use_rspmm`, <https://github.com/nju-websoft/KG-ICL>), and reappears in HYPER as a **Triton**
rewrite generalised to arbitrary arity (`hyper/rspmm/triton_rspmm.py`, class
`HyperRelConvSumAggr`; checked 2026-09-21).

## 3. Anatomy

Given a knowledge hypergraph `G = (V, E, R)` with facts `r(u_1, …, u_k)` and a query
`q = (q, ũ, t)` — relation `q`, observed arguments `ũ`, masked position `t` — HYPER runs four
stages.

### 3.1 The relation graph `G_rel`

Nodes are the relations themselves, `V_rel = R`. Edge types are *ordered position pairs*:
`R_rel = {(a,b) : 1 ≤ a,b ≤ k_max}` where `k_max` is the largest observed arity. A directed edge
`(r_1, r_2)` labelled `(i,j)` exists whenever some entity `v` occupies position `i` in an
`r_1`-fact and position `j` in an `r_2`-fact. In the paper's running example, `Montreal` sits at
position 2 of `AtConference(Sasha, Montreal, 2015, EthicalAI, NeurIPS)` and position 3 of
`Research(Bengio, ClimateAI, Montreal, CIFAR)`, giving an edge labelled `(2,3)`.

Construction is by sparse matrix multiplication (v3 Appendix B): build `E_a ∈ ℝ^{n×m}` for each
position `a` (entity × relation incidence at that position), then
`A_{a2b} = spmm(E_aᵀ, E_b) ∈ ℝ^{m×m}` for each of the `k²` pairs. Cost
`O(k² · max_{a,b}{nnz(E_aᵀ)·nnz(E_b)})`, against `O(k²|E|²)` for the naive pairwise enumeration.
The construction is invariant to renaming of relations — this is the first step of the equivariance
proof (§4).

### 3.2 The positional-interaction encoder `Enc_PI`

For knowledge graphs there are exactly four fundamental relations. For hypergraphs there are `mn`
interactions between an `m`-ary and an `n`-ary fact, and no bound on arity. A lookup table per
`(a,b)` therefore cannot work — "such an approach does not generalize to unseen arities". Instead:

```
Enc_PI : ℕ>0 × ℕ>0 → ℝ^d ,    x_{a,b} = MLP([p_a ‖ p_b])
```

with `p_a` the standard sinusoidal encoding — `(p_a)_{2i} = sin(a / 10000^{2i/d})`,
`(p_a)_{2i+1} = cos(a / 10000^{2i/d})` — and MLP a **shared two-layer feedforward network with ReLU**
(2 layers, hidden dimension 64; v3 Table 22). Two requirements are imposed up front: *extrapolation*
(operate on arities never seen) and *injectivity* (distinct pairs get distinct embeddings).

On knowledge graphs the scheme degenerates exactly to ULTRA's four: head-to-tail = `Enc_PI(1,2)`,
head-to-head = `(1,1)`, tail-to-tail = `(2,2)`, tail-to-head = `(2,1)`. That degeneration is the
whole design argument — HYPER is a strict generalisation of the KGFM relation-interaction idea, not
an analogy to it.

### 3.3 Two HCNet passes

Both encoders are HCNets, differing in what they run over and what supplies the message weight.

**Relation encoder** (T = 6 layers, hidden 64). Message passing over `G_rel`, conditioned on the
query relation `q`. Initialisation `h⁽⁰⁾_{r|q}` is an all-one vector for `r = q` and zero for all
other relation nodes — the "generalized target node distinguishability" condition from HC-MPNN. The
message uses the positional-interaction embedding directly as the weight:

```
msg_{r_{a,b}}(·) = ( ⊙_{j≠i} ( α⁽ᵗ⁾ h⁽ᵗ⁾_{e(j)|q} + (1−α⁽ᵗ⁾) p_j ) ) ⊙ x_{a,b}
```

**Entity encoder** (L = 6 layers, hidden 64). A separate HCNet over the original hypergraph `G`.
Initialisation carries both position and the final relation state:
`h⁽⁰⁾_{v|q} = Σ_{i≠t} 1_{v=u_i} · (p_i + h⁽ᵀ⁾_{q|q})`. The message replaces `x_{a,b}` with a
layer-specific 2-layer MLP of the relation encoder's output:

```
msg_r(·) = ( ⊙_{j≠i} ( α⁽ˡ⁾ h⁽ˡ⁾_{e(j)|q} + (1−α⁽ˡ⁾) p_j ) ) ⊙ MLP⁽ˡ⁾( h⁽ᵀ⁾_{ρ(e)|q} )
```

`α` is a **learnable scalar** interpolating, per layer, between a neighbour's current state and the
bare positional encoding of its slot. This is inherited verbatim from HCNet (arXiv:2402.04062 §5.1),
where the same `α⁽ˡ⁾ h + (1−α⁽ˡ⁾) p_j` convex combination appears. Aggregation is summation;
updates are a two-layer MLP over `[state ‖ aggregate]`; layer normalisation and shortcut connections
throughout.

### 3.4 Decoder

A **unary** decoder `Dec : ℝ^{d(L)} → [0,1]`, a two-layer MLP followed by a sigmoid, applied to
`h⁽ᴸ⁾_{v|q}` to score candidate `v` for the masked position `t`. Unary because the conditioning has
already absorbed the other `k−1` arguments: the k-ary scoring problem has been reduced to a node
classification problem *given the query*. This is the structural reason HYPER does not need an
arity-specific scoring head, and therefore the reason a model pretrained on arity ≤ 6 can score an
arity-9 fact at all.

## 4. What is actually proved

Two results, both in v3 Appendix C, and both narrower than the marketing.

**Proposition C.1 (invariance/equivariance).** For a node–relation isomorphism `(π, φ)`, the HYPER
architecture with `T`-layer relation encoder and `L`-layer entity encoder computes a *link
invariant*: `HYPER(G)(q(u_1,…,u_k)) = HYPER(G')(φ(q)(π(u_1),…,π(u_k)))`. The proof is a stage-by-
stage induction: relation-graph construction is invariant under relation renaming; `x_{a,b}` depends
only on `(a,b)`; the two message-passing inductions preserve the isomorphism; the shared unary
decoder finishes it. This is the formal content of "the model does not depend on the names of
entities or relations", which is the precondition for any zero-shot transfer.

**Theorem C.2 (properties of `Enc_PI`)** — the formal version of the informally stated Theorem 4.1.
Assume `d` even and `10^{8/d}` irrational (i.e. `d ∉ {2,4,8}`). Then **there exists a choice of MLP
parameters** such that `Enc_PI` is

1. **injective** on `ℕ>0²`;
2. **bounded** — the range lies in a compact `K ⊂ ℝ^m`, so "even for unseen arity indices `(a,b)`,
   the resulting positional representations remain within the same bounded set as those observed
   during training";
3. **Lipschitz** with `L = C_pos · L_MLP`, `C_pos = sqrt(2 Σ_i ω_i²)`, `ω_i = 10000^{−2i/d}`,
   `L_MLP = ‖W_2‖_2‖W_1‖_2`.

The injectivity argument is elegant: `p_a = p_b` forces `ω_i/ω_{i+1} = k_i/k_{i+1} ∈ ℚ`, but
`ω_i/ω_{i+1} = 10^{−8/d}` is irrational for `d ∉ {2,4,8}`, contradiction. The MLP part then picks
`W_1, b_1` so that ReLU is the identity on `[−1,1]^{2d}`, making the network affine and full-rank.

**Two caveats the paper does not dwell on.**

- Theorem C.2 is **existential**. It says the hypothesis class *contains* an injective, bounded,
  Lipschitz encoder; it does not say the trained one is injective. The construction that proves
  injectivity is a degenerate one — parameters chosen so that the non-linearity never fires. Nothing
  connects the theorem to the learned weights.
- The irrationality condition excludes `d ∈ {2,4,8}` but the implementation uses `d = 64`, so the
  condition is satisfied in practice. Worth stating because it is the kind of side condition that
  disappears when a result is restated second-hand.

Empirically, the ablation is the real evidence for the design: averaged zero-shot MRR over 19
hypergraphs is **0.285 sinusoidal vs. 0.236 all-one, 0.227 magnitude, 0.213 random** (v3 Table 4).
All-one violates injectivity; magnitude violates boundedness; random violates smoothness. The three
failure modes line up with the three properties, which is about as clean an ablation-to-theorem
correspondence as this literature offers.

## 5. Training

- **Partial completeness assumption** ([Galárraga et al. 2013](https://doi.org/10.1145/2488388.2488425)):
  each k-ary fact `q(u_1,…,u_k)` yields training samples by **randomly masking one position**
  `1 ≤ t ≤ k`. Every slot is a prediction target, not just the tail — this is the n-ary
  generalisation of the head/tail split and the reason the unary decoder suffices.
- **Self-adversarial negative sampling** ([Sun et al., RotatE, ICLR 2019](https://arxiv.org/abs/1902.10197)):
  `L(v|q) = −log p(v|q) − Σ_i w_{i,α} log(1 − p(v'_i|q))`, with
  `w_{i,α} = Softmax(log(1 − p(v'_i|q)) / α)`. Adversarial temperature 1; **512 negatives** per
  positive during pretraining, 256 for fine-tuning and end-to-end training; strict negative sampling.
- Edges directly connecting query node pairs are excluded during training to mitigate overfitting.
- **Mixture sampling.** Following ULTRA, each batch is drawn from one pretraining (hyper)graph with
  probability proportional to its number of edges.
- AdamW, lr 5e-4, batch size 32 for pretraining, 30,000 training steps; hidden dimension 64
  everywhere (v3 Table 22).

## 6. Cost, measured

From v3 Table 10 — FB15k-237, batch size 64, so the three models are doing the *same binary* job:

| Model | Parameters | Training (s/batch) | Inference (s/batch) | GPU memory (GB) |
|---|---:|---:|---:|---:|
| ULTRA | 168,705 | 1.19 | 0.066 | 12.87 |
| HCNet | 159,297 | 2.64 | 0.156 | 18.03 |
| **HYPER** | **225,409** | **4.51** | **0.272** | **25.30** |

So, precisely: **1.7× HCNet and 3.8× ULTRA in training time; 1.7× and 4.1× in inference time; 1.4×
and 2.0× in memory.** The common shorthand "≈2× HCNet, ≈4× ULTRA in time *and* memory" is right on
time and roughly double the true memory factor. The ≈2× over HCNet is the paper's own explanation —
"Hyper employs two HCNet encoders, one for relations and one for entities". The gap to ULTRA is
attributed not to the foundation-model machinery but to modelling a KG as a hypergraph at all:
"these differences essentially reduce to the difference between HCNet and NBFNets".

Asymptotically (v3 Appendix F):

- relation graph construction `O(k² · max_{a,b}{nnz(E_aᵀ)·nnz(E_b)})`, plus `O(k²d)` for the
  positional embeddings;
- relation encoder `O(T(|R|²k²d + |R|d²))` — the relation graph has `|E_rel| = O(|R|²k²)` edges;
- entity encoder `O(L(k|E|d + |V|d² + |R|d²))`.

The `|R|²k²` term is the structural cost of the whole approach: **dense in the number of relations
and quadratic in arity**. The conclusion names it as the model's limitation — "the number of
positional interactions grows quadratically with the arity of each hyperedge" — and defers
"scalable approximations" to future work. Nothing in the paper sparsifies `G_rel`.

**The Triton kernel.** Core hypergraph message passing is a custom Triton kernel rather than PyTorch
Geometric's gather/scatter. Instead of materialising all hyperedge messages (`O(k|E|)` memory), it
writes neighbour features directly into their destination locations, giving `O(|V|)` memory. Claimed
effect: "approximately halves the training time and reduces memory consumption by a factor of five
on average" (v3 Appendix D). In the repository this is `hyper/rspmm/triton_rspmm.py`, exposed via
`use_triton` on `HypergraphLayer`; the layer's Python default is `use_triton=False`, but the shipped
pretraining config sets `use_triton: yes` for both encoders (checked 2026-09-21).

**Pretraining budget.** All pretraining on **a single NVIDIA H100 80GB, four days**; everything else
on an A10 24GB, under three hours per fine-tune or end-to-end run. By foundation-model standards
this is a rounding error — which is the honest framing of what "foundation model" means here.

## 7. Pretraining mixtures, and the corpus problem

Mixtures actually trained (v3 Table 13):

| Variant | Corpus |
|---|---|
| 3KG | FB15k-237, WN18RR, CoDEx-M |
| 4KG | + NELL995 |
| 50KG | + 46 further KGs (ULTRA's mixture) |
| 4HG | JF17K, WikiPeople, FB-AUTO, M-FB15K |
| **3KG + 2HG** | FB15k-237, WN18RR, CoDEx-M, JF17K, WikiPeople |

The finding (v3 §5.2, Q4): 4HG is strong on JF and MFB, both arity-heavy, and weak on WP, which is
mostly binary; WP prefers binary pretraining (3KG); **3KG + 2HG is best overall**. Averaged zero-shot
MRR over all 16 new datasets (v3 Table 12): HYPER (3KG+2HG) **0.236**, ULTRA‡ (3KG+2HG) 0.183,
ULTRA‡ (4HG) 0.168, ULTRA‡ (3KG) 0.162, HYPER (3KG) 0.161, HYPER (4KG) = HYPER (50KG) 0.135,
HYPER (4HG) 0.128, **KG-ICL** 0.143 / 0.139 / 0.048 for its 6-, 4- and 5-layer variants,
ULTRA (4KG) 0.078, ULTRA (50KG) 0.040.

Two things follow that the KB should record.

**More graphs does not mean better.** HYPER (50KG) is *worse* than HYPER (3KG) on average
(0.135 vs. 0.161), and ULTRA (50KG) is far worse than ULTRA (3KG) (0.040 vs. 0.162). Scaling the
pretraining corpus in the binary direction actively hurts on hypergraph targets. This is the exact
opposite of what the scaling narrative for foundation models predicts, and it agrees with Hyper-FM's
"domain diversity beats raw size" finding recorded in
[current-frontier-directions.md](../08-history-and-frontier/current-frontier-directions.md) §1.

**There is no corpus to scale to.** The pretraining corpora in v3 Table 16, counted in training
facts: M-FB15K 415,375; WikiPeople 305,725; JF17K 61,104; FB-AUTO 6,778. Adding the three KGs of the
best mixture — FB15k-237 272,115, WN18RR 86,835, CoDEx-M 185,584 — the winning 3KG+2HG checkpoint is
trained on **about 0.91 million facts**. Worse, most of those are binary. Table 16's arity
histograms (which count all splits, not only train) give WikiPeople 44,315 facts of arity ≥ 3 out of
382,229, and JF17K 46,326 out of 102,648 — so the **entire higher-arity signal in the best
pretraining mixture is on the order of ninety thousand facts**. Maximum arities: FB-AUTO 5, M-FB15K
5, JF17K 6, WikiPeople 9. The 4HG mixture is arity-richer (M-FB15K alone contributes 411,273 facts
of arity ≥ 3, overwhelmingly ternary) but narrower in domain, which is precisely the trade-off §5.2
reports.

That is the whole supply. **There is no Common Crawl of n-ary facts.** The complete inventory of
n-ary pretraining corpora available in September 2026 is, as far as this pass could establish: the
four above, WD50K and its 33/66/100 variants (used by HYPER as a *target*, by hashing main relation
and qualifier predicates in canonical order, not as pretraining), the WD20K family, and the temporal
n-ary sets — all of them Freebase or Wikidata derivatives, all under half a million facts, three of
the four Freebase-derived. See
[datasets-and-benchmarks.md](../09-ecosystem/datasets-and-benchmarks.md). Compounding this:
**JF17K, in the best mixture, is the dataset with the documented 44.5% test-into-train leak**
([dataset-quality-and-leakage-issues.md](../09-ecosystem/dataset-quality-and-leakage-issues.md) §1).
HYPER uses JF17K for *pretraining* and evaluates on InGram-style splits derived from it, so the leak
does not translate directly into inflated headline numbers — but the JF-25…JF-100 targets are drawn
from the same source graph as part of the pretraining corpus, and nobody has measured what that is
worth.

## 8. Corrections to the existing notes

The tables currently in [inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md)
and [hypergraph-neural-networks.md](hypergraph-neural-networks.md) §3.3 were taken from **v1**. The
HYPER rows are unchanged in v3. The **ULTRA baseline rows changed drastically**, and with them one
of the paper's conclusions.

| Row | v1 (Tables 1, 2; ULTRA†) | v3 (Tables 2, 3; ULTRA‡) |
|---|---|---|
| node-inductive, ULTRA(50KG): JF-IND / WP-IND / MFB-IND | 0.346 / 0.286 / 0.149 | **0.007 / 0.029 / 0.026** |
| relation-inductive, ULTRA(50KG) at 100%: JF / MFB / WP / WD | 0.111 / 0.262 / 0.065 / 0.150 | **0.001 / 0.190 / 0.004 / 0.001** |
| the conclusion | ULTRA(50KG) "performs only marginally better than the version trained on just 3" | ULTRA(50KG) "performs **much worse** than the version trained on just 3" |

The qualitative claim reverses sign. v3 also **adds** ULTRA‡ (4HG) and ULTRA‡ (3KG+2HG) — ULTRA
pretrained on the *same* mixture as HYPER — which is the fair comparison v1 lacked, and HYPER still
wins: on node-inductive, HYPER (3KG+2HG) fine-tuned 0.463 / 0.446 / 0.455 against ULTRA‡ (3KG+2HG)
fine-tuned 0.421 / 0.349 / 0.303.

Two further labelling changes: table numbers shifted (relation-inductive is now Table 2, node-
inductive Table 3), and the dagger superscripts were reassigned — in v3, `‡` is the position-typed
reification (`r-1`, `r-2`, …) used in the main results, while `†` is a *new* alternative reification
(`hasEntity_i` plus a `hasRelationType` edge to a relation node). v1's `†` corresponds to v3's `‡`.
The paper reports that `†` "adds a two-hop detour" and generally underperforms `‡` once hypergraphs
are in the pretraining mixture, but is more robust and does show a scaling trend with KG-only
pretraining — which is a more nuanced version of the "reification is transfer-hostile" story than
either version's main text gives.

**Assessment.** A baseline moving from 0.346 to 0.007 between preprint versions is a large
correction to make quietly. It may well be a fixed bug — the v3 text describes ULTRA‡ as "volatile
with the relation explosion" under KG-only pretraining, which reads like the diagnosis. But it means
the published ULTRA-on-reified-hypergraphs numbers should be treated as **active research, not
established**, and any KB claim that rests on the *size* of the HYPER–ULTRA gap should be hedged.
The *ordering* (HYPER ahead of reified-ULTRA) is stable across all three versions.

## 9. What HYPER does not do

Worth stating plainly, because "foundation model for knowledge hypergraphs" invites over-reading.

- **No schema invention.** The relation vocabulary of the inference graph is given. HYPER assigns
  representations to unseen relation *symbols* from their positional-interaction footprint; it does
  not propose, name or type new relations.
- **No hyperedge merging or splitting.** The hypergraph is taken as given. HYPER never decides that
  two facts describe the same event, nor that one fact should be two.
- **No arity re-segmentation.** The arity and the argument order of each relation are fixed input.
  The corruption ablation (v3 §5.5) shows the model *depends* on that order: permuting argument
  positions for 50% of the hyperedges of the most frequent test relation makes performance drop
  "dramatically", because "each argument position carries a distinct semantic role (e.g. musical,
  game, song), and Hyper relies on implicitly learning these roles". A model that is this sensitive
  to slot order is not a model that could infer slot order.
- **No text.** No entity descriptions, no relation labels as strings, no language model. Everything
  is structure. This is a clean design but it means HYPER and QBLP-style text-based inductive models
  are solving disjoint halves of the same problem (see
  [inductive-and-few-shot-settings.md](inductive-and-few-shot-settings.md) §2).
- **No advantage on binary graphs.** The conclusion concedes it: "KGFMs, such as ULTRA, generally
  perform better on standard knowledge graph tasks", and closing that gap is listed as future work.
- **No literals, no time, no uncertainty.** Orthogonal axes, handled by other models (HyNT, VITA).

## 10. Public artefacts

All checked **2026-09-21** by direct fetch from `raw.githubusercontent.com`.

| Artefact | Status |
|---|---|
| Code | <https://github.com/HxyScotthuang/HYPER>, MIT. Engine "adapted from the ULTRA PyG implementation" by the authors' own acknowledgement. Python 3.9, PyTorch ≥ 2.1, PyG ≥ 2.4, Triton ≥ 2.1 |
| **Pretrained checkpoints** | **public**, three of them, in `ckpts/`: `HYPER-3KG.pth` (2,833,802 bytes), `HYPER-4HG.pth` (2,834,222), `HYPER-3KG+2HG.pth` (2,833,802). About 2.8 MB each — 225,409 parameters. The README's "2 MB each" is approximately right |
| Datasets | **public and in-repo**: `hypergraph_dataset/<NAME>/train.txt` etc. for the base hypergraphs (JF17K, WikiPeople, FB-AUTO, M-FB15K), the three node-inductive sets (JF-IND, WP-IND, MFB-IND) and the 16 new relation-inductive splits (JF/MFB/WP/WD × 25/50/75/100). Verified by fetching `hypergraph_dataset/JF-100/train.txt` (148,593 bytes) and `hypergraph_dataset/JF-IND/train.txt` (95,639 bytes) |
| Generation scripts | `data_generation/` — `reify_hypergraph.py` (both reification schemes), `generate_dataset.py` (relation splits, two-hop neighbourhood sampling), `val_test.py` (spanning-hypertree validation/test extraction) |
| Pretraining configs | `config/pretrain/pretrain_3KG+2HG.yaml` etc.; `JointDataset` over `[FB15k237, WN18RR, CoDExMedium, Wikipeople, JF17K]`, 6-layer RelHCNet + 6-layer EntityHCNet, both `use_triton: yes` |
| HCNet | separate repository <https://github.com/HxyScotthuang/HC-MPNN>, described as TMLR 2025/05; HCNet inference is also supported inside the HYPER repository |
| KG-ICL | <https://github.com/nju-websoft/KG-ICL>, code and datasets released 2024-10-14 |

This is, by the standards of the n-ary literature audited in
[reproducibility-of-n-ary-link-prediction.md](reproducibility-of-n-ary-link-prediction.md), unusually
complete: weights, data and generation scripts all in one MIT-licensed repository. The one thing not
public is a *pretraining corpus larger than the five datasets already public* — because, per §7, it
does not exist.

## 11. HCNet, the substrate, in its own right

Three facts about HC-MPNN/HCNet that HYPER depends on and that are easy to lose.

1. **HCNet is HC-MPNN's simplest instance**, with a query-dependent diagonal message map
   `Diag(W_r z_q)` (or a query-independent `w_r`), sinusoidal `p_i`, and the `α` mixing above.
   Initialisation `h⁽⁰⁾_{v|q} = Σ_{i≠t} 1_{v=u_i} * (p_i + z_q)` puts every source node at its query
   position and everything else at zero, satisfying *generalized target node distinguishability*.
2. **Expressivity.** HC-MPNNs are characterised by a relational WL test (`hrwl_1` restricted to
   query-respecting initial colourings) and by a logic (HGML); Theorem 5.1 makes HC-MPNNs strictly
   stronger than HR-MPNNs, the strength coming from the query-dependent initialisation, not the
   message function.
3. **No inverse-relation augmentation.** The standard recipe for NBFNet-family models adds a fresh
   symbol `r⁻¹` and the reversed triple for every relation. HCNet does not, and matches NBFNet and
   A*Net anyway — top-3 on 7 of 8 GraIL splits. The paper's claim is sharper than "it works without
   it": "Theorem G.4 implies that all current models based on conditional message passing, including
   NBFNets, **need** inverse relation augmentation to match the expressive power of HCNet", because
   HCNet's positional message passing already distinguishes incoming from outgoing occurrences.
   HYPER inherits this: v3 Appendix E notes that ULTRA is given inverse triples on the KG benchmarks
   and HYPER is not.

## Open questions raised here

- Theorem C.2 is existential. Does a *trained* `Enc_PI` remain injective, and does injectivity
  measurably matter, or is boundedness doing all the work? A measurement of the minimum pairwise
  distance between learned `x_{a,b}` across arities would settle it cheaply.
- `|E_rel| = O(|R|²k²)` is dense in relations. Wikidata has thousands of properties; at |R| = 5,000
  and k = 9 the relation graph has ~2×10⁹ potential edges. What sparsification of `G_rel` preserves
  the transfer result, and does the ULTRA-side literature already have one?
- Why does HYPER (50KG) underperform HYPER (3KG)? Negative transfer from binary-only pretraining is
  visible in both models, but neither paper isolates whether it is a distribution-shift effect or a
  capacity/optimisation one at 30,000 steps.
- HYPER never re-segments arity, and the corruption ablation shows it cannot. Is there any model that
  can decide the argument order of an unseen relation from structure alone, or does that necessarily
  require text?
- The ULTRA baseline moved by a factor of 50 between v1 and v3. Has anyone outside the authors' group
  re-run reified-ULTRA on these 16 datasets?

## Sources

- Huang, X., Galkin, M., Bronstein, M. M., Ceylan, İ. İ. *HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs*. **ICLR 2026**; arXiv:2506.12362 v1 14 Jun 2025, v2 13 Feb 2026, v3 8 May 2026. <https://arxiv.org/abs/2506.12362> · v3 HTML <https://arxiv.org/html/2506.12362v3> · OpenReview <https://openreview.net/pdf?id=YLTQbMoAaX> · code <https://github.com/HxyScotthuang/HYPER>
- Huang, X., Romero Orth, M., Barceló, P., Bronstein, M. M., Ceylan, İ. İ. *Link Prediction with Relational Hypergraphs* (HC-MPNN / HCNet). *Transactions on Machine Learning Research*, 2025 (05/2025); arXiv:2402.04062 v3, 9 Jun 2025. <https://arxiv.org/abs/2402.04062> · code <https://github.com/HxyScotthuang/HC-MPNN>
- Cui, Y., Sun, Z., Hu, W. *A Prompt-Based Knowledge Graph Foundation Model for Universal In-Context Reasoning* (KG-ICL). *NeurIPS 2024*; arXiv:2410.12288. 43 KGs, transductive and inductive. <https://arxiv.org/abs/2410.12288> · code <https://github.com/nju-websoft/KG-ICL>
- Galkin, M., Yuan, X., Mostafa, H., Tang, J., Zhu, Z. *Towards Foundation Models for Knowledge Graph Reasoning* (ULTRA). *ICLR 2024*; arXiv:2310.04562. <https://arxiv.org/abs/2310.04562>
- Lee, J., Chung, C., Whang, J. J. *InGram: Inductive Knowledge Graph Embedding via Relation Graphs*. *ICML 2023*; arXiv:2305.19987. <https://arxiv.org/abs/2305.19987>
- Zhu, Z., Zhang, Z., Xhonneux, L.-P., Tang, J. *Neural Bellman-Ford Networks: A General Graph Neural Network Framework for Link Prediction* (NBFNet). *NeurIPS 2021*; arXiv:2106.06935. <https://arxiv.org/abs/2106.06935>
- Zhu, Z., Yuan, X., Galkin, M., Xhonneux, S., Zhang, M., Gazeau, M., Tang, J. *A\*Net: A Scalable Path-based Reasoning Approach for Knowledge Graphs*. *NeurIPS 2023*; arXiv:2206.04798. <https://arxiv.org/abs/2206.04798>
- Sun, Z., Deng, Z.-H., Nie, J.-Y., Tang, J. *RotatE: Knowledge Graph Embedding by Relational Rotation in Complex Space*. *ICLR 2019*; arXiv:1902.10197. Source of the self-adversarial negative sampling loss. <https://arxiv.org/abs/1902.10197>
- Galárraga, L. A., Teflioudi, C., Hose, K., Suchanek, F. *AMIE: Association Rule Mining under Incomplete Evidence in Ontological Knowledge Bases*. *WWW 2013*. Source of the partial completeness assumption. <https://doi.org/10.1145/2488388.2488425>
- Teru, K. K., Denis, E., Hamilton, W. L. *Inductive Relation Prediction by Subgraph Reasoning* (GraIL). *ICML 2020*; arXiv:1911.06962. <https://arxiv.org/abs/1911.06962>
- Yadati, N. *Neural Message Passing for Multi-Relational Ordered and Recursive Hypergraphs* (G-MPNN). *NeurIPS 2020*. <https://proceedings.neurips.cc/paper/2020/hash/217eedd1ba8c592db97d0dbe54c7adfc-Abstract.html> · code <https://github.com/naganandy/G-MPNN-R>
- Yu, W., Lu, Y., Yang, D. *THOR: Inductive Link Prediction over Hyper-Relational Knowledge Graphs*. arXiv:2602.05424, 5 Feb 2026. <https://arxiv.org/abs/2602.05424>
- HYPER poster, NeurIPS 2025 "New Perspectives in Graph Machine Learning" workshop. <https://neurips.cc/virtual/2025/127653>
- Triton compiler, used for HYPER's `rspmm` kernels. <https://github.com/triton-lang/triton>
