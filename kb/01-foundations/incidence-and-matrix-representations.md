---
title: Incidence, matrices, tensors and graph expansions
type: concept
status: draft
tags: [hypergraph, incidence-matrix, laplacian, adjacency-tensor, clique-expansion, star-expansion, line-graph, spectral]
created: 2026-09-20
updated: 2026-09-20
---

# Incidence, matrices, tensors and graph expansions

A hypergraph has no single canonical matrix. Chan, Louis, Tang and Zhang state the problem plainly:
"there is no canonical matrix representation of hypergraphs"
([Chan et al., 2018](https://arxiv.org/abs/1605.01483)). What exists instead is a family of
encodings — an incidence matrix, several adjacency matrices, several Laplacians, an adjacency
tensor, and three ways of turning the hypergraph into an ordinary graph. Each encoding is a
*choice*, and each choice throws something away. This note fixes the definitions and says, for
each one, exactly what is lost.

Notation follows [notation-cheatsheet.md](notation-cheatsheet.md); the definitions of the objects
being encoded are in [hypergraph-definitions.md](hypergraph-definitions.md).

## 1. The incidence matrix

For `H = (V, E)` with `|V| = n`, `|E| = p`, the **incidence matrix** `H` is the `n × p` matrix
with `h(v, e) = 1` if `v ∈ e` and `0` otherwise
([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html);
[Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). It is the only representation that is
**lossless for the labelled hypergraph**: `H` and the incidence matrix determine each other up to
the ordering of rows and columns.

With a diagonal hyperedge-weight matrix `W = diag(w(e))`, Zhou, Huang and Schölkopf define the
degrees `d(v) = Σ_{e} w(e) h(v, e)` and `δ(e) = Σ_{v} h(v, e) = |e|`, collected in the diagonal
matrices `D_v` and `D_e` ([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)).

Three structural facts follow immediately:

- **Duality is transposition.** The dual hypergraph `H*` (Section 2 of
  [hypergraph-theory-results.md](hypergraph-theory-results.md)) has incidence matrix `Hᵀ`.
  HyperNetX implements exactly this: "for a hypergraph H = (V, E, I) the dual is H_D = (E, V, Iᵀ)"
  ([HyperNetX glossary](https://hypernetx.readthedocs.io/en/latest/glossary.html)).
- **Multi-hyperedges survive.** Two columns may be identical; the matrix keeps them apart because
  columns have identities. A set-of-sets representation does not.
- **Roles do not survive.** A 0/1 entry records *that* `v` is in `e`, not *which part* `v` plays.
  Ordered or role-labelled hyperedges (Section 6 of
  [hypergraph-definitions.md](hypergraph-definitions.md)) need the entries to carry a label, which
  is what the Hypergraph Interchange Format calls an *incidence attribute*
  ([Coll et al., 2025](https://arxiv.org/abs/2507.11520)). This is the single most important gap
  between the classical matrix theory and knowledge hypergraphs.

## 2. Adjacency matrices

Bretto's adjacency matrix counts co-occurrences: `a_ij = |{e ∈ E : v_i ∈ e ∧ v_j ∈ e}|` for
`i ≠ j` and `a_ii = 0`, which gives `A = H Hᵀ − D_V` with `D_V` the diagonal degree matrix
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), restating Bretto 2013 and Estrada &
Rodríguez-Velázquez 2005). The weighted version is `A_w = H W Hᵀ − D_w`
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), attributing it to Zhou et al.); Zhou, Huang
and Schölkopf give the same formula, `A = H W Hᵀ − D_v`
([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)).

Benson calls the unweighted version the **motif adjacency matrix**: `W_uv` is "the number of
hyperedges containing nodes u and v" ([Benson, 2019](https://arxiv.org/abs/1807.09644)). XGI
exposes both `adjacency_matrix(H)` and `clique_motif_matrix(H)`
([XGI tutorial, accessed 2026-09-20](https://xgi.readthedocs.io/en/stable/api/tutorials/focus_1.html)).

`A` is the adjacency matrix of the **clique expansion** (Section 5). Everything an adjacency
matrix can see about a hypergraph is therefore visible in its clique expansion, and nothing more.

## 3. Laplacians: five constructions and one reduction

Five hypergraph Laplacians appear in the literature. Agarwal, Branson and Belongie showed that the
first four collapse into two graph constructions.

**Chung (1993).** The earliest, a homology-style Laplacian for regular hypergraphs
(F. R. K. Chung, "The Laplacian of a hypergraph", in J. Friedman (ed.), *Expanding graphs*,
DIMACS Series in Discrete Mathematics and Theoretical Computer Science 10, AMS, 1993, pp. 21–36;
bibliographic record taken from the reference list of
[Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf); full text not
consulted `[unverified]`).

**Bolla (1993).** For an unweighted hypergraph, `L_o = D_v − H D_e^{-1} Hᵀ`
([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf), restating M. Bolla,
"Spectra, Euclidean representations and clusterings of hypergraphs", *Discrete Mathematics* 117,
1993).

**Rodríguez (2002, 2003).** Agarwal et al. show it "can similarly be shown to be the unnormalized
Laplacian of the clique expansion of an unweighted graph with every hyperedge weight set to 1"
([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf); the originals are
J. A. Rodríguez, *Linear and Multilinear Algebra* 50:1–14, 2002 and 51:285–297, 2003, not
consulted directly `[unverified]`).

**Zhou, Huang and Schölkopf (2006).** The construction most used in machine learning. They set
`Θ = D_v^{-1/2} H W D_e^{-1} Hᵀ D_v^{-1/2}` and `Δ = I − Θ`, verify that `Δ` is positive
semi-definite with smallest eigenvalue 0 and eigenvector `√d`, and show that for a simple graph
`D_e = 2I`, so `Δ = ½ (I − D_v^{-1/2} A D_v^{-1/2})`, "which coincides with the simple graph
Laplacian up to a factor of 1/2. So we suggestively call `Δ` the hypergraph Laplacian"
([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)).
The same paper derives it as the relaxation of a **normalized hypergraph cut**, with hyperedge
boundary `∂S = {e : e ∩ S ≠ ∅ ∧ e ∩ Sᶜ ≠ ∅}` and
`vol ∂S = Σ_{e ∈ ∂S} w(e) |e ∩ S| |e ∩ Sᶜ| / δ(e)`, explained as treating each hyperedge as a
clique whose sub-edges all carry weight `w(e)/δ(e)`.

**The reduction.** Agarwal, Branson and Belongie prove that these Laplacians "all correspond to
either clique or star expansion of the original hypergraph with the appropriate weighting
function", and tabulate: Bolla → clique + combinatorial Laplacian, Rodríguez → clique +
combinatorial Laplacian, Zhou → star + normalized Laplacian, Gibson → clique + adjacency, Li →
star + adjacency ([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf)).
They further show that **for k-uniform hypergraphs the clique and star constructions are
spectrally identical** — "a surprising and unexpected result as the two graph constructions are
completely different in structure" — and that for non-uniform hypergraphs the only essential
difference is weighting: "the clique expansion gives more weight to evidence from larger edges
than star expansion"
([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf)). Their conclusion is
deliberately deflationary: "while hypergraphs may be an intuitive representation of higher order
similarities, it seems (anecdotally at least) that graphs lie at the heart of this problem."

**Chan–Louis–Tang–Zhang and Louis (2015–2018): the non-linear Laplacian.** The deflationary
conclusion is not the end of the story, because the linear operators above provably *cannot*
capture hypergraph expansion. Chan et al. state: "In general, one cannot hope to have a linear
operator for hypergraphs whose spectra captures hypergraph expansion in a Cheeger-like manner",
because such an operator would give an `O(√OPT)` algorithm, while they prove a `Ω(√(OPT log r))`
lower bound, `r` the largest hyperedge size
([Chan et al., 2018](https://arxiv.org/abs/1605.01483)). They and, independently, Louis define a
**non-linear** Laplacian induced by a diffusion process in which "within each hyperedge, measure
flows from vertices having maximum weighted measure to those having minimum"
([Chan et al., 2018](https://arxiv.org/abs/1605.01483);
[Louis, 2015](https://arxiv.org/abs/1408.2425)). See
[random-walks-spectral-and-expansion.md](random-walks-spectral-and-expansion.md) for the Cheeger
inequality this yields.

## 4. Adjacency tensors

For an **m-uniform** hypergraph the natural object is an order-`m`, dimension-`n` symmetric
hypermatrix ("tensor"): Benson writes `T_{u,v,w} = 1` if `(u, v, w) ∈ E` and `0` otherwise for
`m = 3` ([Benson, 2019](https://arxiv.org/abs/1807.09644)). Tensor spectral theory then replaces
matrix spectral theory: an order-`m` tensor `T` is **irreducible** when no proper subset `S` has
`T_{i, j₂, …, j_m} = 0` for all `i ∈ S` and `j₂, …, j_m ∉ S`, and a strongly connected hypergraph
has an irreducible adjacency tensor
([Benson, 2019](https://arxiv.org/abs/1807.09644), citing Lim 2005 and Qi & Luo 2017).

Two eigen-notions are used, and they differ:

- **Z-eigenpair** (also `ℓ₂`-eigenpair): `T c^{m-1} = λ c`. Perron–Frobenius for tensors gives
  existence of a positive solution but *not* uniqueness — "there can be multiple positive
  Z-eigenvectors, even for the same eigenvalue"
  ([Benson, 2019](https://arxiv.org/abs/1807.09644), citing Chang et al. 2008/2013).
- **H-eigenpair** (`ℓ_k`-eigenpair): `T c^{m-1} = λ c^{[m-1]}`, entry-wise powers. Here the
  positive eigenvector *is* unique up to scaling, and power-method algorithms converge
  ([Benson, 2019](https://arxiv.org/abs/1807.09644)).

Costs and caveats:

- Computing tensor Z-eigenvectors is far harder than matrix eigenvectors, and Benson exhibits a
  3-uniform hypergraph whose ZEC vector is *unstable*
  ([Benson, 2019](https://arxiv.org/abs/1807.09644)).
- **Uniformity is required.** A knowledge hypergraph mixes arities, so a tensor encoding needs a
  padding or uniformisation step that is not part of the mathematics
  (see [hypergraph-definitions.md](hypergraph-definitions.md), Section 2).
- Memory is `O(n^m)` dense; sparse storage is essential. This is a storage question, treated in
  section 04 of this KB.

## 5. The three graph expansions and what each loses

### 5.1 Clique expansion (2-section)

Replace each hyperedge by a clique on its vertices:
`E_x = {(u, v) : u, v ∈ e, e ∈ E}` ([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf),
attributing the construction to Zien, Schlag & Chan 1999). Ouvrard calls the same graph the
**2-section** `[H]₂`: two vertices are joined when some hyperedge contains both
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). The standard weight is
`w_x(u, v) = Σ_{e ∋ u,v} w(e)`, the minimiser of `Σ_e (w_x(u,v) − w(e))²`
([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf)).

**What is lost.** Everything about *which* vertices were grouped together. A hyperedge of size `k`
becomes `k(k−1)/2` edges and cannot be told apart from the union of its sub-hyperedges. The map is
not injective: Wang and Kleinberg identify "two ubiquitous patterns of hyperedges" that cause
irrecoverable loss and prove "the combinatorial impossibility of recovering the lost higher-order
structures" without extra information, before relaxing the problem to a learning task
([Wang & Kleinberg, 2024](https://arxiv.org/abs/2401.08519)). Quantitatively, Chan et al. note that
replacing each hyperedge by a clique or a low-degree expander can separate combinatorial
properties such as min-cut and sparsest-cut "by a factor of `Ω(r)`", so "this approach will not be
useful when `r` is large" ([Chan et al., 2018](https://arxiv.org/abs/1605.01483)). Ouvrard adds a
size argument: the clique expansion has more edges than the incidence graph as soon as `|e| ≥ 4`,
and a hyperedge nested inside another contributes no new edges at all
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)).

### 5.2 Star expansion (incidence / Levi / König graph)

Add a vertex per hyperedge: `V* = V ∪ E`, `E* = {(u, e) : u ∈ e}`
([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf)). This bipartite graph
is the **incidence graph**, also called the König representation
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Zykov 1974) or the Levi graph
([Wikipedia, Levi graph](https://en.wikipedia.org/wiki/Levi_graph)). Standard weighting is
`w*(u, e) = w(e)/δ(e)`
([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf)).

**What is lost.** As a structure, nothing: the correspondence is a bijection, provided the two
sides are labelled. Ouvrard warns of the exception: "a hypergraph and its dual have the same
corresponding bipartite graph: the bipartite graph confuses the hypergraph with its dual"
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Dörfler & Waller 1980). What *is* lost
is convenience: the vertex set changes with the data, set operations are no longer directly
available, and many statements become, in Zykov's words quoted by Ouvrard, "artificial and
cumbersome ... which obscures the point"
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). The full argument is in
[hypergraphs-vs-bipartite-vs-simplicial.md](hypergraphs-vs-bipartite-vs-simplicial.md).

Practical costs: path lengths double (every `v–v'` hop becomes `v–e–v'`), and algorithms that
assume a homogeneous vertex set must be taught that half the vertices are edges.

### 5.3 Line graph (intersection / representative graph)

One vertex per hyperedge, joined when the hyperedges intersect. Ouvrard defines the **intersection
graph** `[H]_I` this way and notes that the line graph is "the 2-section of the dual hypergraph"
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). HyperNetX generalises it to the **s-line
graph**, based on `s`-adjacency (hyperedges sharing at least `s` vertices)
([HyperNetX glossary](https://hypernetx.readthedocs.io/en/latest/glossary.html)).

**What is lost.** The vertices. The line graph records only *that* two hyperedges meet, not in
which vertices nor in how many (unless `s` is varied). Berge already showed the map is not onto:
given a graph `G`, asking whether some hypergraph has `G` as its representative graph is solvable
in general but *not* when `H` is required to be `r`-uniform with a vertex in more than `r` cliques
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Berge 1967/1973).

### 5.4 Summary

| Expansion | Vertex set | Invertible? | Chief loss |
|---|---|---|---|
| Clique / 2-section `[H]₂` | `V` | no | hyperedge identity and size; cuts distorted by up to `Ω(r)` |
| Star / incidence / Levi | `V ∪ E` | yes, if sides labelled | confuses `H` with `H*` if unlabelled; doubles path lengths |
| Line / intersection `[H]_I` | `E` | no | the vertices themselves; not every graph is a line graph of an `r`-uniform `H` |
| Adjacency tensor | `V` | yes for uniform `H` | requires uniformity; `O(n^m)` dense |
| Incidence matrix `H` | `V`, `E` | yes | roles and order on incidences (unless attributed) |

## 6. What software actually stores

- **XGI** exposes `incidence_matrix`, `adjacency_matrix`, `clique_motif_matrix`, and Laplacian
  functions including a normalized hypergraph Laplacian
  ([XGI tutorial, accessed 2026-09-20](https://xgi.readthedocs.io/en/stable/api/tutorials/focus_1.html)).
- **HyperNetX** takes the incidence view as primitive — "a hypergraph is a tuple of three sets,
  H = (V, E, I)" with `I ⊂ E × V` — and builds the incidence matrix, `s`-adjacency matrices,
  `s`-line graphs and the dual from it
  ([HyperNetX glossary](https://hypernetx.readthedocs.io/en/latest/glossary.html)).

For a knowledge hypergraph the practical conclusion is: **store incidences, derive everything
else**. An incidence store keeps hyperedge identity, supports multi-hyperedges, and has a natural
slot for role labels; every matrix, tensor and expansion above is a view over it.

## Sources

- Zhou, D., Huang, J., Schölkopf, B. "Learning with Hypergraphs: Clustering, Classification, and Embedding." *Advances in Neural Information Processing Systems* 19 (NIPS 2006), MIT Press, 2007. https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html
- Agarwal, S., Branson, K., Belongie, S. "Higher Order Learning with Graphs." *Proceedings of the 23rd International Conference on Machine Learning (ICML)*, Pittsburgh, 2006. https://homes.cs.washington.edu/~sagarwal/holg.pdf
- Chan, T-H. H., Louis, A., Tang, Z. G., Zhang, C. "Spectral Properties of Hypergraph Laplacian and Approximation Algorithms." *Journal of the ACM* 65(3), 2018 (arXiv:1605.01483; preliminary version STOC 2015). https://arxiv.org/abs/1605.01483
- Louis, A. "Hypergraph Markov Operators, Eigenvalues and Approximation Algorithms." *Proceedings of the 47th Annual ACM Symposium on Theory of Computing (STOC)*, pp. 713–722, 2015 (arXiv:1408.2425). https://arxiv.org/abs/1408.2425
- Benson, A. R. "Three Hypergraph Eigenvector Centralities." *SIAM Journal on Mathematics of Data Science* 1(2):293–312, 2019 (arXiv:1807.09644). https://arxiv.org/abs/1807.09644
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- Wang, Y., Kleinberg, J. "From Graphs to Hypergraphs: Hypergraph Projection and its Remediation." *ICLR 2024* (arXiv:2401.08519). https://arxiv.org/abs/2401.08519
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. "HIF: The hypergraph interchange format for higher-order networks." *Network Science* 13:e21, 2025 (arXiv:2507.11520). https://arxiv.org/abs/2507.11520
- HyperNetX documentation. Glossary, accessed 2026-09-20. https://hypernetx.readthedocs.io/en/latest/glossary.html
- XGI documentation. "Basic hypergraph functionality" tutorial, stable docs, accessed 2026-09-20. https://xgi.readthedocs.io/en/stable/api/tutorials/focus_1.html
- Wikipedia. "Levi graph." Accessed 2026-09-20. https://en.wikipedia.org/wiki/Levi_graph
- Chung, F. R. K. "The Laplacian of a hypergraph." In J. Friedman (ed.), *Expanding graphs*, DIMACS Series in Discrete Mathematics and Theoretical Computer Science 10, American Mathematical Society, 1993, pp. 21–36. Bibliographic record from the reference list of Agarwal et al. 2006; full text not consulted `[unverified]`.
- Bolla, M. "Spectra, Euclidean representations and clusterings of hypergraphs." *Discrete Mathematics* 117, 1993. Bibliographic record from the reference list of Agarwal et al. 2006; full text not consulted `[unverified]`.
- Rodríguez, J. A. "On the Laplacian eigenvalues and metric parameters of hypergraphs." *Linear and Multilinear Algebra* 50:1–14, 2002; and "On the Laplacian spectrum and walk-regular hypergraphs." *Linear and Multilinear Algebra* 51:285–297, 2003. Records from the reference list of Agarwal et al. 2006; full texts not consulted `[unverified]`.
- Zien, J. Y., Schlag, M. D. F., Chan, P. K. "Multilevel spectral hypergraph partitioning with arbitrary vertex sizes." *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems* 18:1389–1399, 1999. Record from the reference list of Agarwal et al. 2006; full text not consulted `[unverified]`.
