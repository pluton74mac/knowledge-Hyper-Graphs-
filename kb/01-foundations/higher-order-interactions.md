---
title: Higher-order interactions and higher-order networks
type: survey
status: draft
tags: [higher-order, hypergraph, motifs, centrality, contagion, complex-systems, battiston, benson, tudisco-higham]
created: 2026-09-20
updated: 2026-09-20
---

# Higher-order interactions and higher-order networks

Between roughly 2018 and 2023 the complex-systems community reorganised itself around a single
claim: that many systems are badly served by pairwise graphs, and that group interactions need
their own formalism. This note surveys that literature — its two flagship reviews, its structural
measures, its centralities, and its internal critics — and separates what a knowledge hypergraph
can use from what it cannot.

For the underlying structures see [hypergraph-definitions.md](hypergraph-definitions.md) and
[hypergraphs-vs-bipartite-vs-simplicial.md](hypergraphs-vs-bipartite-vs-simplicial.md).

## 1. The two reviews

**Battiston, Cencetti, Iacopini, Latora, Lucas, Patania, Young and Petri (2020).** "Networks
beyond pairwise interactions: Structure and dynamics", *Physics Reports* 874:1–92. The opening
premise: "the complexity of many biological, social and technological systems stems from the
richness of the interactions among their units". It covers representations of higher-order
interactions, structural measures, synthetic generative models, and dynamical processes —
diffusion, spreading, synchronization, evolutionary games
([Battiston et al., 2020](https://arxiv.org/abs/2006.01764)). At 109 pages it is the field's
reference text.

**Bick, Gross, Harrington and Schaub (2023).** "What are higher-order networks?", *SIAM Review*
65(3):686–731. A mathematician's counterpart: it defines the competing formalisms, asks when the
extra structure is warranted, and argues that conventional graph projections are inadequate
([Bick et al., 2023](https://arxiv.org/abs/2104.11329)). Where Battiston et al. survey phenomena,
Bick et al. discipline the vocabulary; this KB follows their definition of a hypergraph
(`ℰ ⊆ 𝒫(𝒱)`, non-empty subsets) in
[hypergraph-definitions.md](hypergraph-definitions.md).

A shorter programmatic statement is Battiston and co-authors' "The physics of higher-order
interactions in complex systems", *Nature Physics* 17(10):1093–1098, 2021 — bibliographic details
from the publisher listing, full text not fetched `[unverified]`
(https://www.nature.com/articles/s41567-021-01371-4).

## 2. Why it is not just re-labelling: the dynamics change

The strongest evidence that higher-order structure is not decoration comes from dynamics.

- **Simplicial contagion.** Iacopini, Petri, Barrat and Latora model social contagion on a
  simplicial complex so that "contagion can occur through interactions in groups of different
  sizes", and find "the emergence of novel phenomena such as a discontinuous transition induced by
  higher-order interactions" (*Nature Communications* 10:2485, 2019; bibliographic details and
  abstract from the publisher listing, full text not fetched `[unverified]`,
  https://www.nature.com/articles/s41467-019-10431-6). A pairwise SIS model on the projected graph
  gives a continuous transition; the group version does not.
- **Representation is not neutral.** Zhang, Lucas and Battiston show that encoding the same
  higher-order data as a hypergraph versus a simplicial complex changes the emergent collective
  dynamics, so "the choice of representation is essential" (*Nature Communications* 14:1605, 2023;
  publisher page redirected to an authentication endpoint when fetched, details from the publisher
  listing `[unverified]`, https://www.nature.com/articles/s41467-023-37190-9).
- **Temporal structure.** Group interactions have their own temporal statistics: "bursty trains of
  rapidly recurring higher-order events"
  ([Cencetti et al., 2021](https://www.nature.com/articles/s41598-021-86469-8)), and groups of
  different sizes carry distinct long-range correlations
  ([Gallo et al., 2024](https://www.nature.com/articles/s41467-024-48578-6)).

## 3. Structural measures

**Higher-order motifs.** Lotito, Musciotto, Montresor and Battiston "introduce the concept of
higher-order motifs, small connected subgraphs where vertices may be linked by interactions of any
order", bound how many such motifs exist as a function of motif size, give an algorithm for
extracting complete higher-order motif profiles from data, and use the profiles to identify
families of hypergraphs with distinct local connectivity
([Lotito et al., 2022](https://www.nature.com/articles/s42005-022-00858-7), *Communications
Physics* 5:79). Motifs are the higher-order analogue of triadic census; the profile is a
fingerprint of a hypergraph's local structure.

**Simplicial closure.** Benson, Abebe, Schaub, Jadbabaie and Kleinberg formalise a temporal
higher-order dataset as `N` timestamped simplices `{(S_i, t_i)}` and study how often an open group
"closes" into a full simplex, using this both descriptively and as a higher-order link-prediction
task ([Benson et al., 2018](https://doi.org/10.1073/pnas.1800683115), *PNAS*
115(48):E11221–E11230). This is the point where the hypergraph and simplicial-complex views meet
empirically rather than by assumption.

## 4. Centralities

Two lines, differing in whether they need uniformity.

**Tensor eigenvector centralities (uniform hypergraphs).** Benson derives three centralities by
choosing different functions `f` and `g` in `f(c_u) = (1/λ) Σ_{(u,v,w) ∈ E} g(c_v, c_w)`
([Benson, 2019](https://arxiv.org/abs/1807.09644)):

| Name | Choice | Equation | Behaviour |
|---|---|---|---|
| **CEC** (clique motif eigenvector centrality) | `f(c)=c`, `g(c_v,c_w)=c_v+c_w` | `W c = λ₁ c`, `W_uv` = number of hyperedges containing `u` and `v` | linear; reduces to eigenvector centrality of the clique/motif adjacency matrix |
| **ZEC** (Z-eigenvector centrality) | `f(c)=c`, `g=c_v c_w` | `T c^{m−1} = λ c` | non-linear; positive solutions exist but may be non-unique and numerically unstable |
| **HEC** (H-eigenvector centrality) | `f(c)=c²`, `g=c_v c_w` | `T c^{m−1} = λ c^{[m−1]}` | non-linear, dimensionally consistent; positive eigenvector unique up to scaling, power method converges |

Benson's own framing of HEC's advantage is dimensional: with ZEC, "if centrality is measured in
some 'unit'", the equation says a unit equals a sum of products of that unit
([Benson, 2019](https://arxiv.org/abs/1807.09644)). CEC is the honest baseline — it is what you get
when you accept the clique expansion.

**Nonlinear node-and-edge centrality (arbitrary hyperedge sizes).** Tudisco and Higham define a
coupled eigenvector model for node centralities *and* hyperedge centralities simultaneously, built
"on the hypergraph incidence matrix and the choice of four nonlinear functions", with existence and
uniqueness results from nonlinear Perron–Frobenius theory
([Tudisco & Higham, 2021](https://doi.org/10.1038/s42005-021-00704-2), *Communications Physics*
4:201; arXiv:2101.06215). This is the more usable of the two for knowledge hypergraphs: no
uniformity requirement, and it ranks facts as well as entities — exactly the duality of
[hypergraph-theory-results.md](hypergraph-theory-results.md), Section 2.

## 5. The internal critique

The field has a standing objection that should be read alongside the reviews.

- **Higher-order Laplacians often are not.** Agarwal, Branson and Belongie showed that the
  hypergraph Laplacians in use reduce to clique or star expansions, and that for `k`-uniform
  hypergraphs the two coincide spectrally; their conclusion was that "graphs lie at the heart of
  this problem" ([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf)).
- **Edge-independent random walks are graph walks.** Chitra and Raphael proved that methods relying
  on such walks "do not utilize higher-order relationships in the data"
  ([Chitra & Raphael, 2019](https://arxiv.org/abs/1905.08287)).
- **But expansion genuinely differs.** Chan, Louis, Tang and Zhang show clique expansion can
  distort cut parameters by `Ω(r)` and that no linear operator can capture hypergraph expansion in
  a Cheeger-like way ([Chan et al., 2018](https://arxiv.org/abs/1605.01483)).

Synthesis: higher-order structure matters for **cuts, expansion, contagion and motifs**; it
frequently does *not* matter for **linear spectral embeddings and edge-independent diffusion**,
where the clique expansion is an honest substitute. A paper claiming higher-order gains should say
which side of that line it is on.

## 6. What a knowledge hypergraph takes from this literature

**Takes:** the motif vocabulary for describing local structure
([Lotito et al., 2022](https://www.nature.com/articles/s42005-022-00858-7)); node-and-edge
centrality for ranking facts as well as entities
([Tudisco & Higham, 2021](https://doi.org/10.1038/s42005-021-00704-2)); higher-order link
prediction as the template for fact prediction
([Benson et al., 2018](https://doi.org/10.1073/pnas.1800683115)); and the discipline of always
comparing against the clique-expansion baseline.

**Leaves:** almost all of it is **unlabelled and untyped**. A hyperedge in this literature is a set
of nodes with a weight and perhaps a timestamp. A knowledge hyperedge has a relation name, ordered
or named roles, a provenance and possibly nested structure. Motif profiles computed without
relation types answer a different question from motif profiles over typed facts, and no paper
surveyed here does the latter. That gap is one of the open questions this section raises.

## Sources

- Battiston, F., Cencetti, G., Iacopini, I., Latora, V., Lucas, M., Patania, A., Young, J.-G., Petri, G. "Networks beyond pairwise interactions: Structure and dynamics." *Physics Reports* 874:1–92, 2020 (arXiv:2006.01764). https://arxiv.org/abs/2006.01764
- Bick, C., Gross, E., Harrington, H. A., Schaub, M. T. "What are higher-order networks?" *SIAM Review* 65(3):686–731, 2023 (arXiv:2104.11329). https://arxiv.org/abs/2104.11329
- Battiston, F., Amico, E., Barrat, A., Bianconi, G., Ferraz de Arruda, G., Franceschiello, B., et al. "The physics of higher-order interactions in complex systems." *Nature Physics* 17(10):1093–1098, 2021. Details from the publisher listing; full text not fetched `[unverified]`. https://www.nature.com/articles/s41567-021-01371-4
- Iacopini, I., Petri, G., Barrat, A., Latora, V. "Simplicial models of social contagion." *Nature Communications* 10:2485, 2019. Details from the publisher listing; full text not fetched `[unverified]`. https://www.nature.com/articles/s41467-019-10431-6
- Zhang, Y., Lucas, M., Battiston, F. "Higher-order interactions shape collective dynamics differently in hypergraphs and simplicial complexes." *Nature Communications* 14:1605, 2023. Publisher page redirected to an authentication endpoint when fetched `[unverified]`. https://www.nature.com/articles/s41467-023-37190-9
- Lotito, Q. F., Musciotto, F., Montresor, A., Battiston, F. "Higher-order motif analysis in hypergraphs." *Communications Physics* 5:79, 2022 (arXiv:2108.03192). https://www.nature.com/articles/s42005-022-00858-7
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. "Simplicial closure and higher-order link prediction." *PNAS* 115(48):E11221–E11230, 2018. https://doi.org/10.1073/pnas.1800683115
- Benson, A. R. "Three Hypergraph Eigenvector Centralities." *SIAM Journal on Mathematics of Data Science* 1(2):293–312, 2019 (arXiv:1807.09644). https://arxiv.org/abs/1807.09644
- Tudisco, F., Higham, D. J. "Node and edge nonlinear eigenvector centrality for hypergraphs." *Communications Physics* 4:201, 2021 (arXiv:2101.06215). https://doi.org/10.1038/s42005-021-00704-2
- Agarwal, S., Branson, K., Belongie, S. "Higher Order Learning with Graphs." *ICML 2006*. https://homes.cs.washington.edu/~sagarwal/holg.pdf
- Chitra, U., Raphael, B. J. "Random Walks on Hypergraphs with Edge-Dependent Vertex Weights." *ICML 2019* (arXiv:1905.08287). https://arxiv.org/abs/1905.08287
- Chan, T-H. H., Louis, A., Tang, Z. G., Zhang, C. "Spectral Properties of Hypergraph Laplacian and Approximation Algorithms." *Journal of the ACM* 65(3), 2018 (arXiv:1605.01483). https://arxiv.org/abs/1605.01483
- Cencetti, G., Battiston, F., Lepri, B., Karsai, M. "Temporal properties of higher-order interactions in social networks." *Scientific Reports* 11, 2021. https://www.nature.com/articles/s41598-021-86469-8
- Gallo, L., Lacasa, L., Latora, V., Battiston, F. "Higher-order correlations reveal complex memory in temporal hypergraphs." *Nature Communications* 15, 2024. https://www.nature.com/articles/s41467-024-48578-6
