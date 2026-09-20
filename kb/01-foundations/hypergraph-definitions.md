---
title: Hypergraph definitions and variants
type: concept
status: reviewed
tags: [hypergraph, definitions, directed-hypergraph, k-uniform, multi-hypergraph, ordered-hypergraph, recursive-hypergraph, temporal-hypergraph, attributed-hypergraph]
created: 2026-09-19
updated: 2026-09-20
---

# Hypergraph definitions and variants

A hypergraph is the structure obtained from a graph when an edge is allowed to contain any number
of vertices instead of exactly two. This note fixes the basic definition, then lists the variants
that matter for knowledge hypergraphs (KHG): uniform, directed, oriented, weighted, multi-,
ordered, recursive (nested), attributed and temporal hypergraphs. Where authors disagree on small
points (empty hyperedges, isolated vertices, repeated hyperedges), the disagreement is recorded
rather than hidden, because it shows up later in file formats and libraries.

Notation used across the KB is collected in [notation-cheatsheet.md](notation-cheatsheet.md).

## 1. The basic object

**Definition (undirected hypergraph).** A hypergraph is a pair `H = (V, E)` where `V` is a finite
set of vertices (nodes) and `E` is a family of non-empty subsets of `V`, the hyperedges. In symbols
`E ⊆ 𝒫(V) \ {∅}`. Wikipedia states it as "the pair (X, E) shall be called an undirected hypergraph"
with `E ⊆ 𝒫(X)` ([Wikipedia, Hypergraph](https://en.wikipedia.org/wiki/Hypergraph)); the survey
by Bick, Gross, Harrington and Schaub gives the same definition with `ℰ ⊆ 𝒫(𝒱)` a finite collection
of non-empty subsets ([Bick et al., 2023](https://arxiv.org/abs/2104.11329)); the topological deep
learning framework uses `(S, 𝒳)` with `𝒳 ⊆ 𝒫(S) \ {∅}`
([Hajij et al., 2022](https://arxiv.org/abs/2206.00606)).

A graph is exactly the case in which every hyperedge has two elements: a **2-uniform hypergraph**.

**Where textbooks differ.** Ouvrard's review compares the classical definitions
([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)):

| Author | Empty hyperedge allowed? | Every vertex must lie in a hyperedge? | Notes |
|---|---|---|---|
| Berge (1970/1973) | no | yes (`⋃ e_j = V`) | hyperedges form a *family* `(e_j)`, so repeats are possible |
| Voloshin (2009) | yes | no | hyperedges are any family of subsets; both `V` and `E` may be empty |
| Bretto (2013) | no | no (isolated vertices allowed) | intermediate definition, used by the XGI library |

Berge's books are the classical references: *Graphes et hypergraphes* (Dunod, 1970), translated as
*Graphs and Hypergraphs* (North-Holland, 1973)
([Berge, 1973](https://archive.org/details/graphshypergraph0000berg)), followed by *Hypergraphs:
Combinatorics of Finite Sets* (North-Holland, 1989)
([Berge, 1989](https://archive.org/details/hypergraphscombi0000berg)). Bretto's *Hypergraph
Theory: An Introduction* is the compact modern textbook
([Bretto, 2013](https://link.springer.com/book/10.1007/978-3-319-00080-0)); Voloshin's
*Introduction to Graph and Hypergraph Theory* is the more elementary one
([Voloshin, 2009](https://openlibrary.org/books/OL22666260M/Introduction_to_graph_and_hypergraph_theory)).
Ouvrard notes that Berge introduced hypergraphs "as a means to generalize the graph approach"
in the 1960s and early 1970s ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)); the exact
first appearance of the word is not pinned down in the sources consulted `[unverified]`.

Other standard vocabulary (all from [Ouvrard, 2020](https://arxiv.org/abs/2002.05014) unless
stated):

- **Simple hypergraph**: no hyperedge is contained in another (`e_i ⊆ e_j ⟹ i = j`). A simple
  hypergraph has no repeated hyperedges. Its hyperedges are all *maximal*; HyperNetX calls a
  maximal hyperedge a *toplex*
  ([HyperNetX glossary](https://hypernetx.readthedocs.io/en/latest/glossary.html)).
- **Loop**: a hyperedge of size 1.
- **Linear hypergraph**: simple, and any two hyperedges share at most one vertex.
- **Rank** `r(H) = max |e|`, **anti-rank** `min |e|`; a hypergraph is **k-uniform** when every
  hyperedge has exactly `k` vertices ([Wikipedia, Hypergraph](https://en.wikipedia.org/wiki/Hypergraph)).
- **Degree** of a vertex: number of hyperedges containing it. **Size** of a hyperedge: its
  cardinality. **Star** `H(v)`: the family of hyperedges containing `v`.
- **Set system** is a synonym used in combinatorics: Iordanov writes that hypergraphs "are studied
  in the context of set combinatorics, where they are also called finite set systems"
  ([Iordanov, 2010](https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3)).

## 2. k-uniform hypergraphs

A k-uniform hypergraph has all hyperedges of size `k`; a 3-uniform hypergraph is a collection of
unordered triples ([Wikipedia, Hypergraph](https://en.wikipedia.org/wiki/Hypergraph)). Uniform
hypergraphs are the setting for most extremal combinatorics and for the tensor spectral theory
(the adjacency tensor of a k-uniform hypergraph is an order-`k` tensor; see
[incidence-and-matrix-representations.md](incidence-and-matrix-representations.md)). Block designs
are regular k-uniform hypergraphs (see
[hypergraphs-vs-bipartite-vs-simplicial.md](hypergraphs-vs-bipartite-vs-simplicial.md)).

For KHGs, uniformity is the exception: a knowledge base mixes relations of different arities, so
the general (non-uniform) case is the norm. Many tensor-based methods therefore need a padding or
"uniformisation" step that is not part of the mathematics.

## 3. Directed hypergraphs (Gallo, Longo, Pallottino, Nguyen 1993)

*Directed in sense D2, tail set → head set; for the three incompatible senses of "directed
hypergraph" see [directed and typed hyperedges](../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md) §1.*

The standard definition of a directed hypergraph comes from Gallo, Longo, Pallottino and Nguyen,
who used them to model problems in operations research and computer science: connectivity, paths,
cuts, min–max duality for a subclass, algorithms for visiting a hypergraph and finding optimal
paths, with applications to propositional logic, And–Or graphs, relational databases and
transportation networks ([Gallo et al., 1993](https://doi.org/10.1016/0166-218x(93)90045-p)).

**Definition (directed hypergraph, hyperarc).** A directed hypergraph is a pair `H = (V, E)` in
which every hyperarc is an ordered pair `e = (T(e), H(e))` of a **tail** set `T(e) ⊆ V` and a
**head** set `H(e) ⊆ V`; Wikipedia phrases it as "a set of pairs of subsets of X"
([Wikipedia, Hypergraph](https://en.wikipedia.org/wiki/Hypergraph)). Gil Pons, Ward and Miller
restate Gallo's definitions: a directed hyperedge is "an ordered pair e = (T_e, H_e), where
T_e ⊆ V is the tail of e and H_e ⊆ V \ T_e is its head"
([Gil Pons et al., 2022](https://arxiv.org/abs/2201.04799)).

Gallo et al. single out two special shapes ([Gil Pons et al., 2022](https://arxiv.org/abs/2201.04799),
restating [Gallo et al., 1993](https://doi.org/10.1016/0166-218x(93)90045-p)):

- **B-arc** (backward arc): `|H(e)| = 1` — many tails, one head. A **B-hypergraph** has only B-arcs.
  B-arcs encode Horn clauses `a_1 ∧ … ∧ a_k → b` and functional dependencies.
- **F-arc** (forward arc): `|T(e)| = 1` — one tail, many heads. An **F-hypergraph** has only F-arcs.
- **BF-hypergraph**: every hyperarc is a B-arc or an F-arc.

A **path** from `s` to `d` is a sequence `(v_1 = s, e_1, v_2, e_2, …, e_q, v_{q+1} = d)` with
`s ∈ T(e_1)`, `d ∈ H(e_q)` and `v_i ∈ H(e_{i-1}) ∩ T(e_i)`
([Gil Pons et al., 2022](https://arxiv.org/abs/2201.04799)). Directed hypergraph reachability,
transitive closure and shortest hyperpaths are surveyed by Ausiello and Laura
([Ausiello & Laura, 2017](https://doi.org/10.1016/j.tcs.2016.03.016)); some hyperpath problems
that are linear-time on acyclic B-hypergraphs are NP-hard on F-hypergraphs
([Gil Pons et al., 2022](https://arxiv.org/abs/2201.04799)).

**Implementation note.** XGI's `DiHypergraph` follows this definition: each directed hyperedge is
an ordered pair `(e⁺, e⁻)` of a tail ("senders") and a head ("receivers"), both subsets of `V`
([XGI DiHypergraph docs](https://xgi.readthedocs.io/en/stable/api/core/xgi.core.dihypergraph.DiHypergraph.html)).
The Hypergraph Interchange Format also supports directed hypergraphs
([Coll et al., 2025](https://arxiv.org/abs/2507.11520)).

**Relevance to KHG.** A directed hyperarc is the natural carrier of a rule or an implication
(premises → conclusion) and of a reaction (reactants → products). It is *not* by itself the
natural carrier of an n-ary fact with distinguishable roles (`treats(drug, disease, dosage)`), which
needs the ordered or role-labelled hyperedges of Section 6.

## 4. Oriented hypergraphs

An **oriented hypergraph** is a hypergraph in which each vertex–edge *incidence* carries a sign:
"an oriented hypergraph is a hypergraph where each vertex-edge incidence is given a label of +1 or
−1" ([Reff, 2015](https://arxiv.org/abs/1506.05054)). The notion was developed by Reff and Rusnak
to extend algebraic graph theory (signed graphs, incidence and Laplacian matrices) to hypergraphs
([Reff & Rusnak, 2012](https://doi.org/10.1016/j.laa.2012.06.011); [Rusnak, 2013](https://arxiv.org/abs/1210.0943)).
Orientation is weaker than direction: it signs incidences but does not split a hyperedge into a
tail set and a head set. A directed hypergraph can be encoded as an oriented one by signing tails
−1 and heads +1, which is exactly the directed incidence matrix convention
([Wikipedia, Hypergraph](https://en.wikipedia.org/wiki/Hypergraph)).

## 5. Weighted hypergraphs and multi-hypergraphs

**Weighted.** Zhou, Huang and Schölkopf define a weighted hypergraph `G = (V, E, w)` as a
hypergraph with a positive number `w(e)` attached to each hyperedge; the vertex degree is then
`d(v) = Σ_{e ∋ v} w(e)` and the hyperedge degree is `δ(e) = |e|`
([Zhou et al., 2006](https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html)).
Two refinements appear in the random-walk literature: **edge-dependent vertex weights**
`γ_e(v)`, where a vertex's weight varies from hyperedge to hyperedge
([Chitra & Raphael, 2019](https://proceedings.mlr.press/v97/chitra19a.html)), and separate node
weights `ν(i)` and edge weights `w(e)` in centrality models
([Tudisco & Higham, 2021](https://doi.org/10.1038/s42005-021-00704-2)).

**Multi-hypergraph.** When the hyperedge family may contain the same vertex set more than once
the object is a multi-hypergraph; Ouvrard attributes the multiset view to Chazelle and Friedman
(1988) ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). Berge's use of a *family* `(e_j)`
rather than a set already allows repeats. Software follows the multi-hypergraph convention because
data does: XGI's `Hypergraph` notes that "in this representation, multiedges are allowed"
([XGI Hypergraph docs](https://xgi.readthedocs.io/en/stable/api/core/xgi.core.hypergraph.Hypergraph.html)),
and HyperNetX defines a multihypergraph as allowing "distinct edges to contain the same set of
elements" ([HyperNetX glossary](https://hypernetx.readthedocs.io/en/latest/glossary.html)).
Bick et al. remark that integer weights can be read as "hypergraphs in which certain edges appear
multiple times" ([Bick et al., 2023](https://arxiv.org/abs/2104.11329)). For a KHG this matters
directly: two distinct facts can involve the same entity set (two papers by the same authors,
two doses of the same drug for the same disease), so hyperedges need identities of their own.

## 6. Ordered hyperedges: tuples and roles

A set-valued hyperedge cannot say *who plays which part*. Two ways to add that:

**Ordered (tuple) hyperedges.** A hyperedge is an ordered tuple `(v_1, …, v_k)` rather than a set.
Iordanov describes this as the second way a hyperedge "acquires an orientation": "treating the
edge as a tuple (ordered, with repetition) yields a very powerful representational language"
([Iordanov, 2010](https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3)). In HyperGraphDB
every atom has a *target set* that is in fact a tuple of atoms, and its length is the atom's
arity. Yadati formalises a **multi-relational ordered hypergraph** as a quadruple
`H = (V, E, P, R)`: `E` a multiset of hyperedges `e ⊆ V`, `P = {P_e}` a positional mapping
`P_e : e → {1, …, p}` for each hyperedge, and `R` a relation mapping from (hyperedge, position)
pairs to one of `r` relation types ([Yadati, 2020](#sources)). Knowledge-hypergraph embedding
papers use tuples directly: Fatemi et al. define a world as entities `E`, relations `R` and a set
of tuples `τ`, "each tuple in τ is of the form r(e_1, e_2, …, e_k) where r ∈ R is a relation and
each e_i ∈ E is an entity"; the arity `|r|` is fixed per relation, and "a knowledge hypergraph
consists of a subset of the tuples τ′ ⊆ τ"
([Fatemi et al., 2020](https://doi.org/10.24963/ijcai.2020/303)).

**Role-labelled hyperedges.** Wen et al. define a multi-fold relation `R` with role set `M` as a
subset of `N^M`, that is, a set of functions from roles to entities; an instance
`t : M(R) → N` maps each role (e.g. `ACTOR`, `CHARACTER`, `MOVIE`) to an entity
([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf)). Positions and roles are
interchangeable once a relation fixes an order on its roles; the role view is closer to the
relational database model (see
[n-ary-relations-and-relational-algebra.md](n-ary-relations-and-relational-algebra.md)).

Neither ordered nor role-labelled hyperedges are treated in the classical textbooks; they belong to
the database and knowledge-representation tradition. The Hypergraph Interchange Format lists
"ordered hypergraphs" among extensions being explored, not among the supported core types
([Coll et al., 2025](https://arxiv.org/abs/2507.11520)).

## 7. Recursive (nested) hypergraphs: hyperedges that contain hyperedges

If a hyperedge may contain other hyperedges as members, statements about statements become
first-class: provenance, qualifiers, rules over facts.

**Ubergraphs.** Joslyn and Nowak formalise this as an *ubergraph*: "As hypergraphs generalize
graphs by allowing edges to have more than two vertices, ubergraphs generalize hypergraphs by
allowing edges to contain other edges as vertices." A **depth-k ubergraph** is a pair `(V, E)` with
`V` a set of fundamental vertices and `E ⊆ 𝒫(V)_k` a finite set of uberedges, where `𝒫(V)_k` is
built by iterating the power set `k` times over `V` together with the previously built levels, with
the condition that any non-vertex member of an edge must itself be an edge. "Every hypergraph is a
depth 0 ubergraph" ([Joslyn & Nowak, 2017](https://arxiv.org/abs/1704.05547)). They motivate it by
the "quoting" or "pointing to" of edges that graph systems otherwise achieve by ad hoc reification.

**k-recursive hypergraphs.** Yadati gives an equivalent machine-learning-oriented definition: a
pair `H = (V, E)` with `E ⊆ 2^{V,k} \ ∅` a set of recursive hyperedges, where a traditional
hypergraph is 0-recursive; his example is an academic network in which depth-0 hyperedges are
co-citation sets of documents and depth-1 hyperedges group those by author
([Yadati, 2020](#sources)).

**HyperGraphDB.** Iordanov's database is built on "generalized hypergraphs where hyperedges can
contain other hyperedges", which "automatically reifies every entity expressed in the database".
He notes the set-theoretic cost: once hyperedges may be members of hyperedges, the foundation
axiom no longer holds, and such structures "are isomorphic to general (i.e. allowing cycles)
directed graphs", studied set-theoretically by Aczel; a typed, stratified construction avoids
"dangerous circularity" ([Iordanov, 2010](https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3)).

For KHGs, recursion is how one represents a *qualified* fact (a fact plus a time, a source, a
confidence) without inventing a new node for it. Whether to allow unbounded depth, or only one
level (facts about facts), is a design decision, not a mathematical necessity.

## 8. Attributed hypergraphs

An attributed hypergraph attaches key–value data to vertices, hyperedges and/or incidences. This
is a software convention rather than a textbook notion. XGI stores attributes at three levels:
per node, per hyperedge and for the hypergraph as a whole
([XGI Hypergraph docs](https://xgi.readthedocs.io/en/stable/api/core/xgi.core.hypergraph.Hypergraph.html)).
The Hypergraph Interchange Format stores attributes "associated with nodes, edges, and
incidences" ([Coll et al., 2025](https://arxiv.org/abs/2507.11520)); an *incidence* attribute is
the natural home for a role label (`v` plays role `ρ` in `e`) and for an edge-dependent vertex
weight. HyperNetX's core definition is already incidence-based: a hypergraph is "a tuple of three
sets, H = (V, E, I)" with `I ⊂ E × V`
([HyperNetX glossary](https://hypernetx.readthedocs.io/en/latest/glossary.html)).

## 9. Temporal hypergraphs

A temporal hypergraph is a sequence of hyperedges with timestamps. Benson et al. formalise their
19 datasets as "N timestamped simplices, {(S_i, t_i)}", where "S_i is a set representing the nodes
in the ith simplex" and `t_i ∈ ℝ` is the observation time; a co-authorship dataset is the running
example ([Benson et al., 2018](https://doi.org/10.1073/pnas.1800683115)). Cencetti, Battiston,
Lepri and Karsai study the temporal statistics of such group interactions in face-to-face data and
find "bursty trains of rapidly recurring higher-order events"
([Cencetti et al., 2021](https://www.nature.com/articles/s41598-021-86469-8)); Gallo, Lacasa,
Latora and Battiston use "time-varying hypergraphs" to show that groups of different sizes have
distinct long-range temporal correlations
([Gallo et al., 2024](https://www.nature.com/articles/s41467-024-48578-6)). HIF lists temporal
hypergraphs among the extensions under exploration ([Coll et al., 2025](https://arxiv.org/abs/2507.11520)).

For a KHG the temporal dimension appears in two forms that should not be confused: a *valid time*
attribute of a fact (part of the fact's content) and a *transaction time* (when the fact entered
the base). Both are attributes on the hyperedge in the sense of Section 8.

## 10. How the variants combine

The variants are orthogonal and can be stacked. The working definition of a KHG in this
repository (see the root README) is a hypergraph whose hyperedges are typed, directed or
role-labelled, possibly weighted, timestamped and nested: that is, an attributed, multi-,
recursive hypergraph with ordered (or role-labelled) hyperedges. No single classical text defines
this composite; each layer has its own primary source, which is why this note exists.

| Layer | Formal device | Primary source |
|---|---|---|
| set hyperedge | `e ⊆ V` | Berge 1973; Bretto 2013 |
| direction | `e = (T(e), H(e))` | Gallo et al. 1993 |
| orientation | signed incidences | Reff & Rusnak 2012 |
| weight | `w : E → ℝ_{>0}`; `γ_e(v)` | Zhou et al. 2006; Chitra & Raphael 2019 |
| multiplicity | hyperedge identities | Ouvrard 2020 (after Chazelle & Friedman 1988) |
| order / roles | tuples `r(e_1,…,e_k)`; `t : M(R) → N` | Fatemi et al. 2020; Wen et al. 2016; Yadati 2020 |
| nesting | ubergraph / k-recursive | Joslyn & Nowak 2017; Yadati 2020; Iordanov 2010 |
| attributes | node/edge/incidence key–values | XGI; HIF (Coll et al. 2025) |
| time | `{(S_i, t_i)}` | Benson et al. 2018 |

## Related notes in this section

- [notation-cheatsheet.md](notation-cheatsheet.md) — symbols, conventions, and the clash index.
- [incidence-and-matrix-representations.md](incidence-and-matrix-representations.md) — how these variants are encoded as matrices, tensors and graph expansions.
- [hypergraphs-vs-bipartite-vs-simplicial.md](hypergraphs-vs-bipartite-vs-simplicial.md) — the neighbouring structures and what distinguishes them.
- [hypergraph-theory-results.md](hypergraph-theory-results.md) — duality, transversals, Helly, acyclicity, widths, colouring, cuts.
- [random-walks-spectral-and-expansion.md](random-walks-spectral-and-expansion.md) — the spectral theory of these objects.
- [n-ary-relations-and-relational-algebra.md](n-ary-relations-and-relational-algebra.md) — the database reading of ordered and role-labelled hyperedges.
- [higher-order-interactions.md](higher-order-interactions.md) — the complex-systems literature that uses them.
- Section index: [README.md](README.md).

## Sources

- Berge, C. *Graphs and Hypergraphs*. North-Holland Mathematical Library 6, North-Holland / American Elsevier, 1973 (translation of *Graphes et hypergraphes*, Dunod, 1970). https://archive.org/details/graphshypergraph0000berg
- Berge, C. *Hypergraphs: Combinatorics of Finite Sets*. North-Holland Mathematical Library 45, North-Holland, 1989. https://archive.org/details/hypergraphscombi0000berg
- Bretto, A. *Hypergraph Theory: An Introduction*. Mathematical Engineering, Springer, 2013. https://link.springer.com/book/10.1007/978-3-319-00080-0
- Voloshin, V. I. *Introduction to Graph and Hypergraph Theory*. Nova Science Publishers, 2009. https://openlibrary.org/books/OL22666260M/Introduction_to_graph_and_hypergraph_theory
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- Wikipedia. "Hypergraph." Accessed 2026-09-19. https://en.wikipedia.org/wiki/Hypergraph
- Bick, C., Gross, E., Harrington, H. A., Schaub, M. T. "What are higher-order networks?" *SIAM Review* 65(3):686–731, 2023 (arXiv:2104.11329). https://arxiv.org/abs/2104.11329
- Hajij, M., Zamzmi, G., Papamarkou, T., Miolane, N., Guzmán-Sáenz, A., Ramamurthy, K. N., Birdal, T., Dey, T. K., Mukherjee, S., Samaga, S. N., Livesay, N., Walters, R., Rosen, P., Schaub, M. T. "Topological Deep Learning: Going Beyond Graph Data." arXiv:2206.00606, 2022. https://arxiv.org/abs/2206.00606
- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications." *Discrete Applied Mathematics* 42(2–3):177–201, 1993. https://doi.org/10.1016/0166-218x(93)90045-p
- Ausiello, G., Laura, L. "Directed hypergraphs: Introduction and fundamental algorithms—A survey." *Theoretical Computer Science* 658:293–306, 2017. https://doi.org/10.1016/j.tcs.2016.03.016
- Gil Pons, R., Ward, M., Miller, L. "Finding (s,d)-Hypernetworks in F-Hypergraphs is NP-Hard." arXiv:2201.04799, 2022. https://arxiv.org/abs/2201.04799
- Reff, N., Rusnak, L. J. "An oriented hypergraphic approach to algebraic graph theory." *Linear Algebra and its Applications* 437(9):2262–2270, 2012. https://doi.org/10.1016/j.laa.2012.06.011
- Rusnak, L. J. "Oriented Hypergraphs I: Introduction and Balance." *Electronic Journal of Combinatorics* 20(3), 2013 (arXiv:1210.0943). https://arxiv.org/abs/1210.0943
- Reff, N. "Spectral properties of oriented hypergraphs." *Electronic Journal of Linear Algebra*, 2014 (arXiv:1506.05054). https://arxiv.org/abs/1506.05054
- Zhou, D., Huang, J., Schölkopf, B. "Learning with Hypergraphs: Clustering, Classification, and Embedding." *Advances in Neural Information Processing Systems* 19 (NIPS 2006). https://proceedings.neurips.cc/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html
- Chitra, U., Raphael, B. J. "Random Walks on Hypergraphs with Edge-Dependent Vertex Weights." *ICML 2019*, PMLR 97:1172–1181 (page numbers `[unverified]`). https://proceedings.mlr.press/v97/chitra19a.html
- Tudisco, F., Higham, D. J. "Node and edge nonlinear eigenvector centrality for hypergraphs." *Communications Physics* 4, 2021. https://doi.org/10.1038/s42005-021-00704-2
- Iordanov, B. "HyperGraphDB: A Generalized Graph Database." *WAIM 2010 Workshops*, LNCS 6185, Springer, 2010. https://link.springer.com/chapter/10.1007/978-3-642-16720-1_3
- Yadati, N. "Neural Message Passing for Multi-Relational Ordered and Recursive Hypergraphs." *Advances in Neural Information Processing Systems* 33 (NeurIPS 2020). Proceedings page URL not resolved at time of writing `[unverified]`; series index: https://proceedings.neurips.cc/paper/2020
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." *IJCAI 2020*, pp. 2191–2197. https://doi.org/10.24963/ijcai.2020/303
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases Beyond Binary Relations." *IJCAI 2016*, pp. 1300–1307. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Joslyn, C., Nowak, K. "Ubergraphs: A Definition of a Recursive Hypergraph Structure." arXiv:1704.05547, 2017 (PNNL-26402). https://arxiv.org/abs/1704.05547
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. "HIF: The hypergraph interchange format for higher-order networks." *Network Science* 13:e21, 2025 (arXiv:2507.11520). https://arxiv.org/abs/2507.11520
- XGI documentation. `xgi.core.hypergraph.Hypergraph` and `xgi.core.dihypergraph.DiHypergraph`, stable docs, accessed 2026-09-19. https://xgi.readthedocs.io/en/stable/api/core/xgi.core.hypergraph.Hypergraph.html and https://xgi.readthedocs.io/en/stable/api/core/xgi.core.dihypergraph.DiHypergraph.html
- HyperNetX documentation. Glossary, accessed 2026-09-19. https://hypernetx.readthedocs.io/en/latest/glossary.html
- Benson, A. R., Abebe, R., Schaub, M. T., Jadbabaie, A., Kleinberg, J. "Simplicial closure and higher-order link prediction." *PNAS* 115(48):E11221–E11230, 2018. https://doi.org/10.1073/pnas.1800683115
- Cencetti, G., Battiston, F., Lepri, B., Karsai, M. "Temporal properties of higher-order interactions in social networks." *Scientific Reports* 11, 2021. https://www.nature.com/articles/s41598-021-86469-8
- Gallo, L., Lacasa, L., Latora, V., Battiston, F. "Higher-order correlations reveal complex memory in temporal hypergraphs." *Nature Communications* 15, 2024 (arXiv:2303.09316). https://www.nature.com/articles/s41467-024-48578-6
