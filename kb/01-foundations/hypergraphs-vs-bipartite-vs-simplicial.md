---
title: Hypergraphs vs bipartite graphs, simplicial complexes and combinatorial complexes
type: comparison
status: draft
tags: [hypergraph, bipartite, levi-graph, simplicial-complex, cell-complex, combinatorial-complex, set-system, block-design, topological-deep-learning]
created: 2026-09-20
updated: 2026-09-20
---

# Hypergraphs vs bipartite graphs, simplicial complexes and combinatorial complexes

A recurring objection to hypergraphs is that they are not new: a hypergraph *is* a bipartite graph,
or a special set system, or a degenerate simplicial complex. Each of these identifications is
mathematically correct and practically misleading in a different way. This note states the
correspondences precisely and then says what each one costs.

Related: [hypergraph-definitions.md](hypergraph-definitions.md) for the objects themselves,
[incidence-and-matrix-representations.md](incidence-and-matrix-representations.md) for the
matrix-level version of the same comparisons.

## 1. Hypergraph = bipartite incidence graph (Levi / König graph)

**The correspondence.** Given `H = (V, E)`, add a vertex `v_e` for each hyperedge `e` and join
`v ∈ V` to `v_e` exactly when `v ∈ e`. The result is the **incidence graph**, a bipartite graph
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). It is called the **Levi graph** after
Friedrich Wilhelm Levi, "who wrote about them in 1942"; Wikipedia states the equivalence flatly:
"For every Levi graph, there is an equivalent hypergraph, and vice versa"
([Wikipedia, Levi graph](https://en.wikipedia.org/wiki/Levi_graph)). Zykov calls it the **König
representation** ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Zykov 1974).

Two caveats on the "and vice versa":

- Only bipartite graphs **with no isolated vertex in either part** correspond to hypergraphs with
  non-empty hyperedges, as required by Berge's definition
  ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)).
- The bipartition must be **labelled**. Unlabelled, "the bipartite graph confuses the hypergraph
  with its dual" ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Dörfler & Waller 1980).

**So why not just use bipartite graphs?** Ouvrard assembles the standard replies
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)):

1. *Factorisation.* "A hypergraph is a factorized version of its incidence graph": a hyperedge of
   size `n` is one object; in the incidence graph it is `n` edges plus an extra vertex. The
   hypergraph vertex set is fixed; the incidence graph's vertex set grows with the data.
2. *Set operations.* "Hypergraphs bring the power of sets: operations on sets such as union,
   intersection, complementation or subsets are well defined." On the bipartite side these become
   neighbourhood computations.
3. *Expressive economy.* Zykov's complaint, quoted by Ouvrard, is that statements natural in
   hypergraph language acquire an "artificial and cumbersome character in terms of König
   representation which obscures the point" — his example is the chromatic number.
4. *Problems with no bipartite analogue.* Berge's question of which graphs are representative
   (line) graphs of `r`-uniform hypergraphs has no natural statement about the incidence graph
   ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014), citing Berge 1967/1973).

The honest summary: the bipartite view is **lossless and often the right implementation**; the
hypergraph view is the right *language*. Storage formats for KHGs almost all store incidences
(the bipartite view) while exposing a hypergraph API — see
[incidence-and-matrix-representations.md](incidence-and-matrix-representations.md), Section 6.

There is one place where the distinction is not cosmetic: **Berge acyclicity is defined on the
incidence graph** ("a hypergraph `H` is Berge acyclic when the graph
`G = {{x, e} : x ∈ e and e ∈ H}` is acyclic"), and Brault-Baron argues this makes it "not an actual
hypergraph notion, but rather a multi-hypergraph notion", since the two-copy multiset
`[{x,y}, {x,y}]` is not Berge acyclic while the set `{{x,y}}` is
([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076)). See
[hypergraph-theory-results.md](hypergraph-theory-results.md), Section 5.

## 2. Simplicial complexes: hypergraphs plus downward closure

An **abstract simplicial complex** is "a family of sets that is closed under taking subsets, i.e.,
every subset of a set in the family is also in the family"
([Wikipedia, Abstract simplicial complex](https://en.wikipedia.org/wiki/Abstract_simplicial_complex)).
The containment chain is stated there as

> HYPERGRAPHS = SET-FAMILIES ⊃ INDEPENDENCE-SYSTEMS = ABSTRACT-SIMPLICIAL-COMPLEXES ⊃ MATROIDS

So a simplicial complex is a hypergraph satisfying **downward closure**: if `{a, b, c}` is a
simplex, then `{a, b}`, `{b, c}`, `{a, c}`, `{a}`, `{b}`, `{c}` are simplices too. Equivalently, a
simplicial complex is determined by its maximal faces — the **facets**, which HyperNetX would call
*toplexes* ([HyperNetX glossary](https://hypernetx.readthedocs.io/en/latest/glossary.html)).

**Why the difference matters for data.** Downward closure is a *modelling assumption*: it asserts
that a group interaction implies all its sub-interactions. For a co-authorship record it says a
four-author paper entails the existence of each pair and triple as an interaction, which is false
as a statement about papers. Bick, Gross, Harrington and Schaub develop the comparison across
representations ([Bick et al., 2023](https://arxiv.org/abs/2104.11329)). Zhang, Lucas and
Battiston show the assumption is not dynamically neutral: representing the same higher-order data
as a simplicial complex rather than a hypergraph changes the emergent collective dynamics
(Y. Zhang, M. Lucas, F. Battiston, "Higher-order interactions shape collective dynamics
differently in hypergraphs and simplicial complexes", *Nature Communications* 14:1605, 2023,
https://www.nature.com/articles/s41467-023-37190-9; abstract page redirected to an authentication
endpoint when fetched, bibliographic details from the publisher listing `[unverified]`).

**What the simplicial view buys.** Homology, Hodge theory and high-dimensional expansion are
defined on complexes, not on arbitrary hypergraphs; the boundary operator needs downward closure.
That is why spectral results for hypergraphs and for complexes read so differently
(see [random-walks-spectral-and-expansion.md](random-walks-spectral-and-expansion.md)).
Benson, Abebe, Schaub, Jadbabaie and Kleinberg's *simplicial closure* work sits exactly on the
boundary: they measure empirically how often open groups close into a simplex
([Benson et al., 2018](https://doi.org/10.1073/pnas.1800683115)).

**For knowledge hypergraphs, downward closure is wrong.** `treats(drug, disease, dosage)` does not
entail `treats(drug, disease)` as an independent fact with the same meaning — the projection
changes the claim. A KHG is a hypergraph, not a simplicial complex.

## 3. Cell complexes and combinatorial complexes (Hajij et al., 2022)

Cell complexes add what hypergraphs lack — a **hierarchy** — but impose geometric conditions that
data rarely satisfies. Hajij and co-authors propose a structure that has both set-like freedom and
rank hierarchy.

**Definition (combinatorial complex).** "Let `S` be a non-empty finite set and `P(S)` its power
set. A combinatorial complex (CC) is a tuple `(X, ı)` formed by a set `X ⊂ P(S) \ {∅}` together
with a rank function `ı : X → Z⁺` such that (i) `ı({x}) = 0` for all `x ∈ S`, and (ii) for all
`x, y ∈ X`, if `x ⊊ y` then `ı(x) < ı(y)`"
([Hajij et al., 2022](https://arxiv.org/abs/2206.00606), Definition 1; the version 1 preprint
carried the title *Higher-Order Attention Networks*). Elements of `X` are **cells**; 0-cells are
vertices, 1-cells are edges, and "edges can have more than two nodes".

The paper's own summary of the place of CCs: they "generalize graphs while maintaining certain
desirable properties", they "impose no constraints on the set of relations" the way hypergraphs do
not, and they "permit the construction of hierarchical higher-order relations, analogous to those
found in simplicial and cell complexes"
([Hajij et al., 2022](https://arxiv.org/abs/2206.00606)). Concretely: "CCs generalize hypergraphs.
Indeed, hyperedges in a hypergraph correspond to cells in a CC, where the rank of the higher order
cells is ignored."

**Relevance to KHGs.** The rank function is a cheap, principled way to say *facts about facts*: a
qualified statement can be a cell of higher rank whose sub-cells are the statement's components.
It is a competitor to the recursive-hypergraph route of Section 7 of
[hypergraph-definitions.md](hypergraph-definitions.md), with a weaker requirement (a rank order,
not membership) and correspondingly weaker expressivity.

## 4. Set systems, incidence structures and block designs

- **Set system.** In combinatorics a hypergraph is simply a finite set system
  ([Iordanov, 2010](https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3)); the
  containment chain in Section 2 records the identification.
- **Incidence structure.** The Levi graph construction is stated for incidence structures
  (points and lines) generally, of which hypergraphs are the finite case
  ([Wikipedia, Levi graph](https://en.wikipedia.org/wiki/Levi_graph)).
- **Block designs.** A balanced incomplete block design (BIBD, or 2-design) is "a family of
  k-element subsets of X, called blocks, such that any x in X is contained in r blocks, and any
  pair of distinct points x and y in X is contained in λ blocks", with parameters `(v, b, r, k, λ)`
  and the counting identities `bk = vr` and `λ(v−1) = r(k−1)`
  ([Wikipedia, Block design](https://en.wikipedia.org/wiki/Block_design)). In hypergraph terms a
  BIBD is a `k`-uniform, `r`-regular hypergraph with constant pairwise co-degree `λ`. Fisher's
  inequality, `b ≥ v`, constrains which parameter sets can exist
  ([Wikipedia, Block design](https://en.wikipedia.org/wiki/Block_design)). The same page records
  the matrix statement that "every binary matrix with constant row and column sums is the incidence
  matrix of a regular uniform block design" — designs are, exactly, incidence matrices with
  constant margins.

Design theory is the oldest branch of "hypergraph theory" and the source of much of the extremal
machinery, but it studies hypergraphs of extreme regularity. Knowledge hypergraphs are the
opposite: heavy-tailed degrees, mixed arities, no regularity at all. The design literature is
therefore a source of *techniques*, rarely of *models*, for this KB.

## 5. Summary table

| Structure | Extra condition on `E ⊆ 𝒫(V)` | Gains | Costs |
|---|---|---|---|
| Hypergraph | none | arbitrary group relations | no hierarchy, no canonical matrix |
| Bipartite incidence graph | none (a re-encoding) | ordinary graph algorithms apply | vertex set grows with data; confuses `H` and `H*` if unlabelled |
| Abstract simplicial complex | downward closure | homology, Hodge theory, high-dimensional expansion | asserts sub-interactions exist; wrong for n-ary facts |
| Cell complex | geometric gluing conditions | hierarchy and topology | rarely matched by real data |
| Combinatorial complex | rank function monotone under `⊊` | hierarchy without geometry | rank must be supplied by the modeller |
| Block design (BIBD) | `k`-uniform, `r`-regular, co-degree `λ` | strong counting theory | far too regular for real knowledge bases |

## Sources

- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- Wikipedia. "Levi graph." Accessed 2026-09-20. https://en.wikipedia.org/wiki/Levi_graph
- Wikipedia. "Abstract simplicial complex." Accessed 2026-09-20. https://en.wikipedia.org/wiki/Abstract_simplicial_complex
- Wikipedia. "Block design." Accessed 2026-09-20. https://en.wikipedia.org/wiki/Block_design
- Brault-Baron, J. "Hypergraph Acyclicity Revisited." *ACM Computing Surveys* 49(3), 2016 (arXiv:1403.7076, 2014). https://arxiv.org/abs/1403.7076
- Bick, C., Gross, E., Harrington, H. A., Schaub, M. T. "What are higher-order networks?" *SIAM Review* 65(3):686–731, 2023 (arXiv:2104.11329). https://arxiv.org/abs/2104.11329
- Hajij, M., Zamzmi, G., Papamarkou, T., Miolane, N., Guzmán-Sáenz, A., Ramamurthy, K. N., Birdal, T., Dey, T. K., Mukherjee, S., Samaga, S. N., Livesay, N., Walters, R., Rosen, P., Schaub, M. T. "Topological Deep Learning: Going Beyond Graph Data." arXiv:2206.00606, 2022 (v1 titled *Higher-Order Attention Networks*). https://arxiv.org/abs/2206.00606
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. "Simplicial closure and higher-order link prediction." *PNAS* 115(48):E11221–E11230, 2018. https://doi.org/10.1073/pnas.1800683115
- Zhang, Y., Lucas, M., Battiston, F. "Higher-order interactions shape collective dynamics differently in hypergraphs and simplicial complexes." *Nature Communications* 14:1605, 2023. https://www.nature.com/articles/s41467-023-37190-9 — publisher page redirected to an authentication endpoint when fetched; bibliographic details taken from the publisher listing `[unverified]`.
- HyperNetX documentation. Glossary, accessed 2026-09-20. https://hypernetx.readthedocs.io/en/latest/glossary.html
- Iordanov, B. "HyperGraphDB: A Generalized Graph Database." *WAIM 2010 Workshops*, LNCS 6185, Springer, 2010. https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3
