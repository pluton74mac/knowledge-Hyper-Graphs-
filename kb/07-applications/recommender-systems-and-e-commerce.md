---
title: Recommender systems and e-commerce
type: survey
status: draft
tags: [hypergraph, recommendation, collaborative-filtering, session-based, e-commerce, contrastive-learning]
created: 2026-09-20
updated: 2026-09-20
---

# Recommender systems and e-commerce

Recommendation is by volume the largest "hypergraph" literature outside physics — and the one where the
word means something furthest from a knowledge hypergraph. Almost all of it is sense **D** in
[applications-overview](applications-overview.md): the hyperedge is an inductive bias for a neural
model, learned or heuristically constructed, not a stored fact. Read this note as a study of what
hypergraph *structure* buys a learner, and treat transfers to knowledge hypergraphs with care.

## 1. Where the hyperedges come from

Four recurring constructions, in rough order of how "knowledge-like" they are:

| Construction | Hyperedge is | Example |
|---|---|---|
| Session / basket | the set of items in one session or one order | DHCN, HyperRec |
| User neighbourhood | a user plus the items they interacted with (and k-hop expansions) | DHCF |
| Learned / latent | a learnable assignment of nodes to hyperedges | HCCF |
| Knowledge-graph derived | entities related through a KG relation path | KHGRec, HAKG-style models |

Only the fourth is knowledge-bearing. The first three are ways of injecting group structure that a
bipartite user–item graph cannot express.

## 2. The reference systems

**HyperRec** — *Next-item Recommendation with Sequential Hypergraphs*
([Wang, Ding, Hong, Liu, Caverlee, 2020](https://doi.org/10.1145/3397271.3401133), SIGIR 2020,
pp. 1101–1110; [code](https://github.com/wangjlgz/HyperRec)). Builds a *sequence* of hypergraphs, one
per time period, so that item semantics can drift: item correlations defined by short-term user
interactions carry dynamic preference signal that a static graph averages away. This is the
"hypergraph plus time" template that most later sequential models follow.

**DHCF** — *Dual Channel Hypergraph Collaborative Filtering*
([Ji, Feng, Ji, Zhao, Tang, Gao, 2020](https://dl.acm.org/doi/10.1145/3394486.3403253), KDD 2020,
pp. 2020–2029). Models users and items with *separate* hypergraph channels containing explicit hybrid
high-order correlations, joined by a jump hypergraph convolution (JHConv) that preserves the original
representation through propagation. The paper's most transferable finding is the interaction with
sparsity: gains grow as data density falls. That is a plausible general property of higher-order
smoothing and is worth testing in knowledge settings.

**DHCN** — *Self-Supervised Hypergraph Convolutional Networks for Session-based Recommendation*
([Xia, Yin, Yu, Wang, Cui, Zhang, 2021](https://ojs.aaai.org/index.php/AAAI/article/view/16578),
AAAI 2021; [code](https://github.com/xiaxin1998/DHCN)). Each session is a hyperedge; a dual channel
(hypergraph + line graph) is trained with a self-supervised objective that maximises mutual information
between the two views. The ablation reported in the paper is the relevant one: both the hypergraph
modelling and the self-supervised task contribute.

**HCCF** — *Hypergraph Contrastive Collaborative Filtering*
([Xia, Huang, Xu, Zhao, Yin, Huang, 2022](https://arxiv.org/abs/2204.12200), SIGIR 2022). The hyperedges
are **learned**, not given: a hypergraph structure-learning module produces a global view that is
contrasted against the local graph view, targeting over-smoothing and supervision sparsity. HCCF is the
clearest case of the hypergraph as pure inductive bias — there is no claim that the learned hyperedges
correspond to anything in the world.

**KHGRec** — knowledge-enhanced heterogeneous hypergraph recommendation
([Sakong et al., 2024](https://arxiv.org/abs/2407.03665);
[code](https://github.com/viethungvu1998/KHGRec)). Builds a *collaborative knowledge heterogeneous
hypergraph* over both the user–item interaction network and a knowledge graph, with two hypergraph
encoders. Reported average relative improvement of **5.18 %** over state-of-the-art baselines on four
real-world datasets, plus robustness tests under noise, missing data and cold start. A related line,
higher-order knowledge-enhanced recommendation with heterogeneous hypergraph multi-attention, appears
in *Information Sciences* ([2024](https://www.sciencedirect.com/science/article/pii/S002002552401079X)).

## 3. What the recommender evidence does and does not show

**Does show.** Group structure is real and exploitable in interaction data; hypergraph convolution
consistently beats bipartite-graph convolution on the same data; gains are largest where data are
sparse; and combining a hypergraph view with a graph view under a contrastive objective is a reliable
recipe (DHCN, HCCF).

**Does not show.** That n-ary *knowledge* helps. In three of the four constructions above the hyperedge
is derived from interaction logs and could be replaced by any other grouping with similar statistics.
The typical reported margin — a few percent relative on Recall@20 or NDCG@20 — is also inside the range
where benchmark and tuning choices dominate, a well-documented hazard in recommender evaluation.
Only KHGRec's KG-derived channel bears on the knowledge question, and it is a single line of work.

**Transferable ideas for knowledge hypergraphs.** (i) The dual-channel pattern — keep a pairwise view
and a higher-order view and contrast them — is directly applicable to a KHG that also has binary facts.
(ii) Sparsity sensitivity suggests KHG methods should be evaluated on long-tail entities, not averages.
(iii) Learned hyperedges (HCCF) are a caution: if a learned grouping matches a curated n-ary fact set,
the curation may be unnecessary; if it does not, the two should be compared explicitly.

## Sources

- Wang, J., Ding, K., Hong, L., Liu, H., Caverlee, J. *Next-item Recommendation with Sequential Hypergraphs.* SIGIR 2020, pp. 1101–1110. https://doi.org/10.1145/3397271.3401133
- HyperRec code repository, GitHub, checked 2026-09-20. https://github.com/wangjlgz/HyperRec
- Ji, S., Feng, Y., Ji, R., Zhao, X., Tang, W., Gao, Y. *Dual Channel Hypergraph Collaborative Filtering.* KDD 2020, pp. 2020–2029. https://dl.acm.org/doi/10.1145/3394486.3403253
- Xia, X., Yin, H., Yu, J., Wang, Q., Cui, L., Zhang, X. *Self-Supervised Hypergraph Convolutional Networks for Session-based Recommendation.* AAAI 2021. https://ojs.aaai.org/index.php/AAAI/article/view/16578
- DHCN code repository, GitHub, checked 2026-09-20. https://github.com/xiaxin1998/DHCN
- Xia, L., Huang, C., Xu, Y., Zhao, J., Yin, D., Huang, J. X. *Hypergraph Contrastive Collaborative Filtering.* SIGIR 2022; arXiv:2204.12200. https://arxiv.org/abs/2204.12200
- Sakong, D. et al. *Heterogeneous Hypergraph Embedding for Recommendation Systems* (KHGRec). arXiv:2407.03665, 2024. https://arxiv.org/abs/2407.03665
- KHGRec code repository, GitHub, checked 2026-09-20. https://github.com/viethungvu1998/KHGRec
- *Higher-order knowledge-enhanced recommendation with heterogeneous hypergraph multi-attention.* Information Sciences, 2024. https://www.sciencedirect.com/science/article/pii/S002002552401079X
