---
title: Random walks, spectral theory and expansion on hypergraphs
type: concept
status: draft
tags: [hypergraph, random-walk, spectral, cheeger, expander, laplacian, sparsification, edge-dependent-vertex-weights]
created: 2026-09-20
updated: 2026-09-20
---

# Random walks, spectral theory and expansion on hypergraphs

Spectral graph theory rests on a chain: random walk → Laplacian → eigenvalues → Cheeger inequality
→ partitioning algorithm. On hypergraphs the chain breaks in an instructive place. The naive walk
is *equivalent to a walk on the clique expansion*, and no linear operator can play the Cheeger
role at all. What survives is a non-linear theory with slightly weaker guarantees, plus a separate
topological tradition of high-dimensional expansion.

Matrix definitions are in
[incidence-and-matrix-representations.md](incidence-and-matrix-representations.md); notation in
[notation-cheatsheet.md](notation-cheatsheet.md).

## 1. The natural random walk

Zhou, Huang and Schölkopf define the walk that most later work takes as the baseline: "Given the
current position `u ∈ V`, first choose a hyperedge `e` over all hyperedges incident with `u` with
the probability proportional to `w(e)`, and then choose a vertex `v ∈ e` uniformly at random"
([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)).
Its transition matrix and stationary distribution are

```
p(u, v) = Σ_e  w(e) h(u,e)/d(u) · h(v,e)/δ(e)      P = D_v^{-1} H W D_e^{-1} Hᵀ
π(v)    = d(v) / vol V
```

and the normalized cut criterion is exactly the probability that the walk crosses the cut in the
stationary regime ([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)).

**The collapse.** Chitra and Raphael prove this walk carries no higher-order information: they show
"conditions under which random walks on such hypergraphs are equivalent to random walks on graphs",
and conclude that "current machine learning methods that rely on Laplacians derived from random
walks on hypergraphs with edge-independent vertex weights do not utilize higher-order relationships
in the data" ([Chitra & Raphael, 2019](https://arxiv.org/abs/1905.08287), ICML 2019). This is the
probabilistic counterpart of Agarwal, Branson and Belongie's spectral reduction of hypergraph
Laplacians to clique and star expansions
([Agarwal et al., 2006](https://homes.cs.washington.edu/~sagarwal/holg.pdf)).

**The repair: edge-dependent vertex weights (EDVW).** Give each incidence its own weight `γ_e(v)`,
so a vertex counts differently inside different hyperedges. Chitra and Raphael derive a
random-walk-based Laplacian for this case and bound the mixing time
([Chitra & Raphael, 2019](https://arxiv.org/abs/1905.08287)); Hayashi, Aksoy, Park and Park build
a family of EDVW Laplacians and clustering methods on weighted incidence matrices, reporting
"higher-quality clusters" than existing hypergraph clustering
([Hayashi et al., 2020](https://arxiv.org/abs/2006.16377)).

**Physics-side treatment.** Carletti, Battiston, Cencetti and Fanelli give a statistical-physics
account of random walks on hypergraphs, including hyperedge-size-dependent transition rules
(T. Carletti, F. Battiston, G. Cencetti, D. Fanelli, "Random walks on hypergraphs", *Physical
Review E* 101(2):022308, 2020; bibliographic details from the publisher listing, full text not
fetched `[unverified]`).

**For KHGs.** The practical reading of Chitra–Raphael is blunt: if your hypergraph pipeline uses an
edge-independent walk, you could have used the clique expansion and saved the trouble. Role labels
on incidences (Section 6 of [hypergraph-definitions.md](hypergraph-definitions.md)) are exactly
the data an EDVW walk needs — a subject role and an instrument role should not be equally likely
exits from a fact.

## 2. Expansion and the discrepancy ratio

For an edge-weighted hypergraph, each vertex carries `w_v = Σ_{e ∋ v} w_e`, a set `S` has weight
`w(S) = Σ_{v ∈ S} w_v`, and the cut hyperedges are `∂S = {e : e meets both S and V \ S}`. Then
([Chan et al., 2018](https://arxiv.org/abs/1605.01483)):

```
φ(S) = w(∂S) / w(S)          φ_H = min_{∅ ⊊ S ⊊ V} max{ φ(S), φ(V \ S) }
```

The spectral quantity that shadows it is the **discrepancy ratio**

```
D_w(f) = Σ_{e ∈ E} w_e · max_{u,v ∈ e} (f_u − f_v)²  /  Σ_{u ∈ V} w_u f_u²
```

with `0 ≤ D_w(f) ≤ 2`, and `D_w(χ_S) = φ(S)` for an indicator vector
([Chan et al., 2018](https://arxiv.org/abs/1605.01483)). The `max` over pairs inside a hyperedge is
where linearity dies: for a graph (`|e| = 2`) it is the ordinary Rayleigh quotient of the
normalized Laplacian; for `|e| > 2` it is not a quadratic form.

## 3. The non-linear Laplacian and the hypergraph Cheeger inequality

**Impossibility first.** "In general, one cannot hope to have a linear operator for hypergraphs
whose spectra captures hypergraph expansion in a Cheeger-like manner", because such an operator
would give a polynomial-time `O(√OPT)` bound, while a lower bound of `Ω(√(OPT · log r))` holds,
`r` the largest hyperedge size ([Chan et al., 2018](https://arxiv.org/abs/1605.01483)).

**The operator.** Chan, Louis, Tang and Zhang, and independently Louis, define a Laplacian induced
by a diffusion process in which "within each hyperedge, measure flows from vertices having maximum
weighted measure to those having minimum", with a stochastic version driven by Brownian noise
([Chan et al., 2018](https://arxiv.org/abs/1605.01483);
[Louis, 2015](https://arxiv.org/abs/1408.2425)). The operator is non-linear; it does not require
uniformity; and the Rayleigh quotient `R(x) = ⟨x, Lx⟩/⟨x, x⟩` coincides with the normalized
discrepancy ratio `D(x)`.

**The second eigenvalue.** `γ₂ := min_{0 ≠ x ⊥_W 1} D(x)`; any *procedural minimizer* `x₂`
attaining it satisfies `L x₂ = γ₂ x₂`
([Chan et al., 2018](https://arxiv.org/abs/1605.01483)).

**Hypergraph Cheeger inequality.**

```
γ₂ / 2  ≤  φ_H  ≤  2 √γ₂
```

([Chan et al., 2018](https://arxiv.org/abs/1605.01483), Theorem 3.8). Related consequences from the
same paper:

- **Diameter.** The hop-diameter satisfies `diam(H) = O(log N_w / γ₂)` with
  `N_w = max_u w(V)/w_u`.
- **Mixing.** There is a starting distribution `ϕ₀` with `‖ϕ₀ − ϕ*‖₁ ≥ ½` whose mixing time is
  `Ω((1/γ₂) ln(ϕ*_min/δ))`.
- **Higher order.** The sequence produced by procedural minimizers need not be unique, so
  higher-order Cheeger inequalities are stated via orthogonal minimaximizers `ξ_k` and `ζ_k`, with
  `ξ_k ≤ γ_k ≤ ζ_k ≤ k ξ_k`, and `γ₂ = ζ₂` though possibly `ξ₂ < γ₂`.
- **Computation.** Exact eigenvalues are intractable; there is a polynomial-time algorithm
  computing `γ̂ = O(γ₂ log r)`, and the `O(log r)` factor is optimal under the Small-Set Expansion
  hypothesis ([Chan et al., 2018](https://arxiv.org/abs/1605.01483);
  [Louis, 2015](https://arxiv.org/abs/1408.2425)).

**Why not just expand to a graph?** Because, as Chan et al. note, replacing each hyperedge by a
clique or a low-degree expander can separate min-cut and sparsest-cut "by a factor of `Ω(r)`"
([Chan et al., 2018](https://arxiv.org/abs/1605.01483)). For a KHG whose facts can have a dozen
participants, `r` is not small.

## 4. Sparsification

If the spectrum is what matters, a hypergraph can often be thinned:

- Soma and Yoshida construct, for any undirected or directed hypergraph on `n` vertices, an
  ε-spectral sparsifier with `O(n³ log n / ε²)` hyperarcs in polynomial time, preserving the
  Laplacian quadratic form to within `1 ± ε`
  ([Soma & Yoshida, 2018](https://arxiv.org/abs/1807.04974)).
- Kapralov, Krauthgamer, Tardos and Yoshida improve this to `O*(n)` hyperedges — nearly linear and,
  notably, **independent of the hyperedge rank**
  ([Kapralov et al., 2021](https://arxiv.org/abs/2106.02353)).

This matters for KHGs at scale: spectral summarisation of a very large fact base need not be
proportional to the arities involved.

## 5. Hypergraph expanders: two distinct traditions

The phrase "hypergraph expander" names two largely separate programmes.

**Combinatorial / spectral (uniform hypergraphs).** Conlon, Tidor and Zhao give "a simple
construction of `r`-uniform hypergraph expanders for all `r ≥ 3`", generalising an earlier
3-uniform construction from Cayley graphs; they open by observing that "hypergraph expanders are
hypergraphs with surprising, non-intuitive expansion properties"
([Conlon, Tidor & Zhao, 2020](https://arxiv.org/abs/1809.06342), *Proceedings of the London
Mathematical Society* 121(5):1311–1336).

**Topological (high-dimensional expanders, HDX).** Here the object is a simplicial complex, not an
arbitrary hypergraph, and expansion is coboundary or cosystolic expansion of the Eckmann Laplacian.
Parzanchevski, Rosenthal and Tessler "define a notion of combinatorial expansion for simplicial
complexes of general dimension", prove a Cheeger-type inequality and a high-dimensional expander
mixing lemma, and connect the spectrum to Gromov's geometric overlap
(*Combinatorica* 36:195–227, 2016; arXiv:1207.0638 —
https://arxiv.org/abs/1207.0638, abstract consulted via search listing, full text not fetched
`[unverified]`). Lubotzky's ICM survey is the standard entry point
(A. Lubotzky, "High dimensional expanders", *Proceedings of the ICM 2018*, pp. 705–730 —
https://www.worldscientific.com/doi/10.1142/9789813272880_0027; page range from the publisher
listing, full text not fetched `[unverified]`).

**Why the split matters here.** HDX results need downward closure and therefore do *not* transfer to
general hypergraphs (see
[hypergraphs-vs-bipartite-vs-simplicial.md](hypergraphs-vs-bipartite-vs-simplicial.md)). A
knowledge hypergraph is not a complex, so the Chan–Louis line — non-linear Laplacian, `O(log r)`
approximations — is the relevant one, and HDX should be read as a neighbouring field rather than
an applicable toolkit.

## 6. What this section means for knowledge hypergraphs

1. An edge-independent random walk on a KHG is a walk on its clique expansion; it cannot see
   arities, and any "higher-order" claim made on its basis is suspect
   ([Chitra & Raphael, 2019](https://arxiv.org/abs/1905.08287)).
2. Role- or incidence-weighted walks (EDVW) are the cheapest genuinely higher-order alternative
   ([Chitra & Raphael, 2019](https://arxiv.org/abs/1905.08287);
   [Hayashi et al., 2020](https://arxiv.org/abs/2006.16377)).
3. Spectral partitioning of a KHG has a Cheeger guarantee, but only through a non-linear operator
   and with an `O(log r)` computational loss
   ([Chan et al., 2018](https://arxiv.org/abs/1605.01483)).
4. Spectral summaries can be made nearly linear in `n`, independent of arity
   ([Kapralov et al., 2021](https://arxiv.org/abs/2106.02353)).

## Sources

- Zhou, D., Huang, J., Schölkopf, B. "Learning with Hypergraphs: Clustering, Classification, and Embedding." *NIPS 2006*. https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html
- Chitra, U., Raphael, B. J. "Random Walks on Hypergraphs with Edge-Dependent Vertex Weights." *ICML 2019*, PMLR 97 (arXiv:1905.08287). https://arxiv.org/abs/1905.08287
- Hayashi, K., Aksoy, S. G., Park, C. H., Park, H. "Hypergraph Random Walks, Laplacians, and Clustering." arXiv:2006.16377, 2020. https://arxiv.org/abs/2006.16377
- Agarwal, S., Branson, K., Belongie, S. "Higher Order Learning with Graphs." *ICML 2006*. https://homes.cs.washington.edu/~sagarwal/holg.pdf
- Chan, T-H. H., Louis, A., Tang, Z. G., Zhang, C. "Spectral Properties of Hypergraph Laplacian and Approximation Algorithms." *Journal of the ACM* 65(3), 2018 (arXiv:1605.01483). https://arxiv.org/abs/1605.01483
- Louis, A. "Hypergraph Markov Operators, Eigenvalues and Approximation Algorithms." *STOC 2015*, pp. 713–722 (arXiv:1408.2425). https://arxiv.org/abs/1408.2425
- Soma, T., Yoshida, Y. "Spectral Sparsification of Hypergraphs." arXiv:1807.04974, 2018. https://arxiv.org/abs/1807.04974
- Kapralov, M., Krauthgamer, R., Tardos, J., Yoshida, Y. "Spectral Hypergraph Sparsifiers of Nearly Linear Size." arXiv:2106.02353, 2021. https://arxiv.org/abs/2106.02353
- Conlon, D., Tidor, J., Zhao, Y. "Hypergraph expanders of all uniformities from Cayley graphs." *Proceedings of the London Mathematical Society* 121(5):1311–1336, 2020 (arXiv:1809.06342). https://arxiv.org/abs/1809.06342
- Parzanchevski, O., Rosenthal, R., Tessler, R. J. "Isoperimetric Inequalities in Simplicial Complexes." *Combinatorica* 36:195–227, 2016 (arXiv:1207.0638). Abstract consulted via search listing; full text not fetched `[unverified]`. https://arxiv.org/abs/1207.0638
- Lubotzky, A. "High Dimensional Expanders." *Proceedings of the International Congress of Mathematicians (ICM 2018)*, pp. 705–730. Page range from the publisher listing; full text not fetched `[unverified]`. https://www.worldscientific.com/doi/10.1142/9789813272880_0027
- Carletti, T., Battiston, F., Cencetti, G., Fanelli, D. "Random walks on hypergraphs." *Physical Review E* 101(2):022308, 2020. Bibliographic details from the publisher listing; full text not fetched `[unverified]`. https://doi.org/10.1103/PhysRevE.101.022308
