---
title: Notation cheat sheet
type: concept
status: draft
tags: [notation, conventions, hypergraph, reference]
created: 2026-09-20
updated: 2026-09-20
---

# Notation cheat sheet

The hypergraph literature reuses the same letters for different things — `H` is both the
hypergraph and its incidence matrix; `r` is a rank, a replication number and a uniformity; `d(v)`
is weighted in one paper and unweighted in the next. This page fixes the conventions used across
this KB and records the clashes so that a citation can be read against its source.

Conventions are chosen to match the most-cited source for each area:
[Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)
for matrices, [Chan et al., 2018](https://arxiv.org/abs/1605.01483) for expansion,
[Benson, 2019](https://arxiv.org/abs/1807.09644) for tensors,
[Gallo et al., 1993](https://doi.org/10.1016/0166-218x(93)90045-p) for direction.

## 1. The hypergraph

| Symbol | Meaning | Source of convention |
|---|---|---|
| `H = (V, E)` | hypergraph: vertex set and hyperedge family | [Bick et al., 2023](https://arxiv.org/abs/2104.11329) |
| `n = \|V\|` | number of vertices | [Benson, 2019](https://arxiv.org/abs/1807.09644) |
| `p = \|E\|` | number of hyperedges (some authors use `m`) | [Ouvrard, 2020](https://arxiv.org/abs/2002.05014) |
| `e`, `e_j` | a hyperedge | Berge convention, via [Ouvrard, 2020](https://arxiv.org/abs/2002.05014) |
| `𝒫(V)` | power set; `E ⊆ 𝒫(V) \ {∅}` | [Hajij et al., 2022](https://arxiv.org/abs/2206.00606) |
| `H(v)` | **star** of `v`: the family of hyperedges containing `v` | [Ouvrard, 2020](https://arxiv.org/abs/2002.05014) |
| `H*` | dual hypergraph | [Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/) |
| `[H]₂` | 2-section / clique expansion (a graph on `V`) | [Ouvrard, 2020](https://arxiv.org/abs/2002.05014) |
| `[H]_I` | intersection / line graph (a graph on `E`) | [Ouvrard, 2020](https://arxiv.org/abs/2002.05014) |
| `r(H)` | **rank**: `max_e \|e\|`; in Chan et al. simply `r = r_max` | [Chan et al., 2018](https://arxiv.org/abs/1605.01483) |
| `r_min` | anti-rank: `min_e \|e\|` | [Chan et al., 2018](https://arxiv.org/abs/1605.01483) |
| `k`-uniform / `m`-uniform | every hyperedge has exactly `k` (resp. `m`) vertices | [Benson, 2019](https://arxiv.org/abs/1807.09644) |

**This KB writes `r` for rank and `k` for uniformity**, and uses `m` only as the tensor order of an
`m`-uniform hypergraph, following Benson.

## 2. Degrees, weights, incidences

| Symbol | Meaning |
|---|---|
| `h(v, e) ∈ {0,1}` | incidence indicator |
| `w(e) > 0` | hyperedge weight |
| `d(v) = Σ_{e} w(e) h(v,e)` | **weighted** vertex degree ([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)) |
| `δ(e) = \|e\|` | hyperedge degree / size |
| `γ_e(v)` | edge-dependent vertex weight (EDVW) ([Chitra & Raphael, 2019](https://arxiv.org/abs/1905.08287)) |
| `ρ(v, e)` | role label on the incidence `(v, e)` — **this KB's own notation**, with no classical source; the Hypergraph Interchange Format's *incidence attributes* are the implementation ([Coll et al., 2025](https://arxiv.org/abs/2507.11520)) |
| `vol S = Σ_{v ∈ S} d(v)` | volume of a vertex set ([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)) |
| `w_v = Σ_{e ∋ v} w_e`, `w(S)` | vertex/set weight in the expansion literature ([Chan et al., 2018](https://arxiv.org/abs/1605.01483)) |

**Clash to watch:** Zhou's `d(v)` is *weighted*; Berge's and Bretto's degree is a *count*. They
coincide only when all `w(e) = 1`.

## 3. Matrices

| Symbol | Shape | Definition |
|---|---|---|
| `H` | `n × p` | incidence matrix, `H_{ve} = h(v, e)` |
| `W` | `p × p` | `diag(w(e))` |
| `D_v` | `n × n` | `diag(d(v))` |
| `D_e` | `p × p` | `diag(δ(e))` |
| `A` | `n × n` | adjacency: `A = H W Hᵀ − D_v` ([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)) |
| `W_uv` | `n × n` | motif/clique adjacency: number of hyperedges containing both `u` and `v` ([Benson, 2019](https://arxiv.org/abs/1807.09644)) |
| `Θ` | `n × n` | `D_v^{-1/2} H W D_e^{-1} Hᵀ D_v^{-1/2}` |
| `Δ = I − Θ` | `n × n` | normalized hypergraph Laplacian ([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)) |
| `P = D_v^{-1} H W D_e^{-1} Hᵀ` | `n × n` | random-walk transition matrix |

**Clash to watch:** the letter `H` is the hypergraph *and* its incidence matrix. This KB writes the
hypergraph as `H = (V, E)` and the matrix as `H` only inside matrix expressions; where confusion is
possible, the matrix is called `B` (for *bipartite incidence*) and said so explicitly.
`W` is also overloaded — hyperedge-weight diagonal matrix (Zhou) versus motif adjacency matrix
(Benson). This KB keeps `W` for weights and writes `M` for the motif adjacency matrix.

## 4. Tensors (uniform hypergraphs only)

| Symbol | Meaning |
|---|---|
| `T` | order-`m`, dimension-`n` symmetric adjacency tensor; `T_{u,v,w} = 1` iff `(u,v,w) ∈ E` for `m = 3` |
| `T c^{m−1}` | vector with `[T c^{m−1}]_i = Σ_{j₂,…,j_m} T_{i,j₂,…,j_m} c_{j₂} ⋯ c_{j_m}` |
| `c^{[k]}` | entry-wise `k`-th power of the vector `c` |
| Z-eigenpair | `T c^{m−1} = λ c` |
| H-eigenpair | `T c^{m−1} = λ c^{[m−1]}` |

All four rows follow [Benson, 2019](https://arxiv.org/abs/1807.09644).

## 5. Direction, order and roles

| Symbol | Meaning | Source |
|---|---|---|
| `e = (T(e), H(e))` | directed hyperarc: tail and head | [Gallo et al., 1993](https://doi.org/10.1016/0166-218x(93)90045-p) |
| B-arc / F-arc | `\|H(e)\| = 1` / `\|T(e)\| = 1` | [Gil Pons et al., 2022](https://arxiv.org/abs/2201.04799) |
| `(e⁺, e⁻)` | XGI's tail ("senders") and head ("receivers") | [XGI DiHypergraph docs](https://xgi.readthedocs.io/en/stable/api/core/xgi.core.dihypergraph.DiHypergraph.html) |
| `r(e₁, …, e_k)` | ordered (tuple) hyperedge; relation `r` of arity `k` | [Fatemi et al., 2020](https://doi.org/10.24963/ijcai.2020/303) |
| `t : M(R) → N` | role-labelled instance: roles to entities | [Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf) |
| `P_e : e → {1,…,p}` | positional mapping of a hyperedge | Yadati, 2020 (NeurIPS 33) |

**This KB's default for a knowledge hyperedge** is the role-labelled form: a hyperedge is a triple
`(id, r, {(ρ, v)})` — an identity, a relation name, and a set of role–entity pairs. This is a
synthesis, not a citation; see [hypergraph-definitions.md](hypergraph-definitions.md), Section 10.

**Arity convention.** Arity counts the **entity participants** of a fact, and the relation is a label
on the hyperedge rather than a member of it — so an RDF triple is a *binary labelled* hyperedge here,
whereas under the 3-uniform encoding of Hayes and Gutierrez it is a *ternary unlabelled* one; see
[../02-knowledge-representation/semantic-web-hypergraph-view.md](../02-knowledge-representation/semantic-web-hypergraph-view.md) §2.

## 6. Cuts, expansion, spectra

| Symbol | Meaning | Source |
|---|---|---|
| `∂S` | cut hyperedges: those meeting both `S` and `V \ S` | [Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html) |
| `vol ∂S = Σ_{e ∈ ∂S} w(e)\|e ∩ S\|\|e ∩ Sᶜ\|/δ(e)` | normalized cut volume | [Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html) |
| `φ(S) = w(∂S)/w(S)`; `φ_H = min_S max{φ(S), φ(V\S)}` | expansion | [Chan et al., 2018](https://arxiv.org/abs/1605.01483) |
| `D_w(f)` | discrepancy ratio (see [random-walks-spectral-and-expansion.md](random-walks-spectral-and-expansion.md)) | [Chan et al., 2018](https://arxiv.org/abs/1605.01483) |
| `γ₂` | second "eigenvalue" of the non-linear Laplacian | [Chan et al., 2018](https://arxiv.org/abs/1605.01483) |
| `λ(e)` | number of blocks a hyperedge touches in a `k`-way partition (connectivity metric) | [Schlag et al., 2021](https://arxiv.org/abs/2106.08696) |

## 7. Widths and acyclicity

| Symbol | Meaning | Source |
|---|---|---|
| α-, β-, γ-acyclic | Fagin's degrees, in increasing generality γ ⊂ β ⊂ α | [Fagin, 1983](https://dl.acm.org/doi/10.1145/2402.322390) |
| Berge-acyclic | incidence graph is a forest; strictly stronger than γ | [Brault-Baron, 2016](https://arxiv.org/abs/1403.7076) |
| `hw(H)`, `ghw(H)`, `fhw(H)` | hypertree, generalized hypertree, fractional hypertree width | [Gottlob et al., 2020](https://arxiv.org/abs/2002.05239) |
| `τ(H)`, `ν(H)` | transversal number, matching number | [Dourado et al., 2009](https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/) |
| `χ(H)` | chromatic number (weak colouring: no monochromatic hyperedge) | [Ouvrard, 2020](https://arxiv.org/abs/2002.05014) |

## 8. Quick clash index

| Symbol | Meaning A | Meaning B |
|---|---|---|
| `H` | the hypergraph | the incidence matrix |
| `H(e)` | head of a directed hyperarc | — (vs `H(v)`, the star of a vertex) |
| `W` | diagonal hyperedge-weight matrix (Zhou) | motif adjacency matrix (Benson) |
| `r` | rank `max\|e\|` (Chan, Ouvrard) | replication number of a block design |
| `m` | number of hyperedges (some authors) | tensor order / uniformity (Benson) |
| `d(v)` | weighted degree (Zhou) | count of incident hyperedges (Berge, Bretto) |
| `δ(e)` | hyperedge size `\|e\|` (Zhou) | — |
| `Δ` | normalized hypergraph Laplacian (Zhou) | — |
| `L` | non-linear diffusion Laplacian (Chan/Louis) | combinatorial Laplacian (Bolla, Rodríguez) |

## Sources

- Zhou, D., Huang, J., Schölkopf, B. "Learning with Hypergraphs: Clustering, Classification, and Embedding." *NIPS 2006*. https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html
- Chan, T-H. H., Louis, A., Tang, Z. G., Zhang, C. "Spectral Properties of Hypergraph Laplacian and Approximation Algorithms." *Journal of the ACM* 65(3), 2018 (arXiv:1605.01483). https://arxiv.org/abs/1605.01483
- Benson, A. R. "Three Hypergraph Eigenvector Centralities." *SIAM Journal on Mathematics of Data Science* 1(2):293–312, 2019 (arXiv:1807.09644). https://arxiv.org/abs/1807.09644
- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications." *Discrete Applied Mathematics* 42(2–3):177–201, 1993. https://doi.org/10.1016/0166-218x(93)90045-p
- Gil Pons, R., Ward, M., Miller, L. "Finding (s,d)-Hypernetworks in F-Hypergraphs is NP-Hard." arXiv:2201.04799, 2022. https://arxiv.org/abs/2201.04799
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- Bick, C., Gross, E., Harrington, H. A., Schaub, M. T. "What are higher-order networks?" *SIAM Review* 65(3):686–731, 2023 (arXiv:2104.11329). https://arxiv.org/abs/2104.11329
- Hajij, M., et al. "Topological Deep Learning: Going Beyond Graph Data." arXiv:2206.00606, 2022. https://arxiv.org/abs/2206.00606
- Dourado, M. C., Protti, F., Szwarcfiter, J. L. "Complexity Aspects of the Helly Property: Graphs and Hypergraphs." *Electronic Journal of Combinatorics*, Dynamic Survey DS17, 2009. https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS17/pdf/
- Fagin, R. "Degrees of acyclicity for hypergraphs and relational database schemes." *Journal of the ACM* 30(3):514–550, 1983. https://dl.acm.org/doi/10.1145/2402.322390
- Brault-Baron, J. "Hypergraph Acyclicity Revisited." *ACM Computing Surveys* 49(3), 2016 (arXiv:1403.7076). https://arxiv.org/abs/1403.7076
- Gottlob, G., Lanzinger, M., Pichler, R., Razgon, I. "Complexity Analysis of Generalized and Fractional Hypertree Decompositions." arXiv:2002.05239, 2020. https://arxiv.org/abs/2002.05239
- Chitra, U., Raphael, B. J. "Random Walks on Hypergraphs with Edge-Dependent Vertex Weights." *ICML 2019* (arXiv:1905.08287). https://arxiv.org/abs/1905.08287
- Schlag, S., Heuer, T., Gottesbüren, L., Akhremtsev, Y., Schulz, C., Sanders, P. "High-Quality Hypergraph Partitioning." arXiv:2106.08696, 2021. https://arxiv.org/abs/2106.08696
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." *IJCAI 2020*, pp. 2191–2197. https://doi.org/10.24963/ijcai.2020/303
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases Beyond Binary Relations." *IJCAI 2016*, pp. 1300–1307. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Yadati, N. "Neural Message Passing for Multi-Relational Ordered and Recursive Hypergraphs." *NeurIPS 33*, 2020. Proceedings page URL not resolved `[unverified]`; series index: https://proceedings.neurips.cc/paper/2020
- Coll, M., et al. "HIF: The hypergraph interchange format for higher-order networks." *Network Science* 13:e21, 2025 (arXiv:2507.11520). https://arxiv.org/abs/2507.11520
- XGI documentation. `xgi.core.dihypergraph.DiHypergraph`, accessed 2026-09-20. https://xgi.readthedocs.io/en/stable/api/core/xgi.core.dihypergraph.DiHypergraph.html
