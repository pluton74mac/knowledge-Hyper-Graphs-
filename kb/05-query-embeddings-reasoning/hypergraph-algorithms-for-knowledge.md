---
title: Hypergraph algorithms for knowledge work
type: survey
status: draft
tags: [algorithms, s-walk, s-centrality, clustering, modularity, community-detection, pagerank, random-walk, motifs, matching, hyperpath, transversal, complexity, hypernetx]
created: 2026-09-20
updated: 2026-09-20
---

# Hypergraph algorithms for knowledge work

Most knowledge-hypergraph work is representation learning. This note is the other half: the
**combinatorial and spectral algorithms** that operate on the hypergraph as a structure, what they
give you on a knowledge base, and what they cost. The recurring lesson is that every graph algorithm
has *more than one* hypergraph generalisation, and choosing among them is a modelling decision, not
a detail.

Mathematical background: [hypergraph-definitions.md](../01-foundations/hypergraph-definitions.md).

---

## 1. s-walks: the parameterised generalisation of connectivity

The single most useful idea in hypergraph analytics for knowledge bases. Aksoy et al. observe that
"edge incidence in hypergraphs is quantitative, yielding hypergraph walks with both length **and
width**", and define:

> **Definition 5 (s-walk).** For a positive integer s, an s-walk of length k between hyperedges f
> and g is a sequence f = e_{i₀}, e_{i₁}, …, e_{i_k} = g where for j = 1,…,k, s ≤ |e_{i_{j-1}} ∩
> e_{i_j}| and i_{j-1} ≠ i_j.

"Since in a graph a pair of vertices can belong to at most 1 edge, the usual graph walk … is
equivalent to a 1-walk between hyperedges on the dual. Consequently, the s = 1 case recovers the
usual graph walk and s-walks for s > 1 are only possible on hypergraphs"
([Aksoy, Joslyn, Ortiz Marrero, Praggastis and Purvine, *Hypernetwork science via high-order
hypergraph walks*, *EPJ Data Science* 9, 2020](https://doi.org/10.1140/epjds/s13688-020-00231-0);
arXiv:1906.11295).

Everything else in their framework falls out of this:

- **s-connected components** (Def. 6): C ⊆ E is s-connected if an s-walk exists between all f, g ∈ C;
  maximal such C are s-components. Bounded above by |E_s| where E_s = {e : |e| ≥ s}. For s = 1 the
  edge-based and vertex-based notions coincide, "however, for s ≥ 2, the number of s-connected
  components for H and H* may differ" — duality genuinely splits.
- **s-line graph** L_s(H) (Def. 7): vertices are hyperedges with |e| ≥ s, edges join pairs
  intersecting in ≥ s vertices. "A hypergraph H is s-connected iff L_s(H) is connected." This is the
  *implementation*: compute the s-line graph and run ordinary graph algorithms on it.
- **s-distance** (Prop. 1): the shortest s-walk length is a metric on E_s.
- **s-eccentricity, s-diameter, s-radius, average s-distance, s-closeness centrality** (Def. 8),
  each the graph notion on L_s(H).

### Why this matters for a knowledge hypergraph

Set s = 1 and "related facts" means *shares any entity* — which, on a knowledge base with hub
entities (a country, a year), links nearly everything and is useless. Set s = 2 or 3 and "related"
means *shares at least two or three participants*, which is a far better proxy for topical relatedness
between n-ary facts. **s is a knob for how much co-participation counts as a connection**, and it is
the natural retrieval-expansion parameter for hypergraph RAG
([llm-and-khg-interaction.md](llm-and-khg-interaction.md) §2).

Caveat the authors flag: for some s, H has more than one s-component, so s-distance is infinite for
some pairs and "the s-eccentricity of every edge (and hence s-diameter and s-radius) and mean
s-distance are all infinite". Report per-component, or use harmonic variants.

Reference implementation: **HyperNetX** (<https://github.com/pnnl/HyperNetX>), which the paper's own
figures were produced with.

**Cost.** L_s(H) has |E_s| vertices and requires all pairwise hyperedge intersections — Θ(|E|²)
intersection tests in the naive form. The paper explicitly notes the "computational" limitation of
line graphs. For a large KHG, build L_s lazily from an inverted entity→hyperedge index.

## 2. Random walks, Laplacians, PageRank

There is no single hypergraph random walk. Three that matter:

- **Clique-expansion walk** — walk on the weighted clique expansion. Simple, and the basis of the
  classic hypergraph Laplacian used by HGNN
  ([hypergraph-neural-networks.md](hypergraph-neural-networks.md)). Lossy in the way §1 of that note
  describes.
- **Edge-dependent vertex weights** — Chitra and Raphael show that when a vertex's weight varies by
  hyperedge (i.e. it plays a different *role* in different facts), the random walk is **not**
  equivalent to any walk on the clique expansion ([Chitra and Raphael, *Random Walks on Hypergraphs
  with Edge-Dependent Vertex Weights*, ICML 2019 /
  arXiv:1905.08287](https://arxiv.org/abs/1905.08287)). For a knowledge hypergraph this is exactly
  the case that matters: roles *are* edge-dependent vertex weights.
- **Hypergraph PageRank** — personalised PageRank generalised to hypergraphs and used for local
  clustering ([Takai, Miyauchi, Ikeda and Yoshida, *Hypergraph Clustering Based on PageRank*,
  KDD 2020 / arXiv:2006.08302](https://arxiv.org/abs/2006.08302)). This gives the "important facts
  near this entity" primitive that a KHG retrieval layer wants.

A unifying treatment of hypergraph random walks, the associated Laplacians and the clustering they
induce is [Hayashi, Aksoy, Park and Park, *Hypergraph Random Walks, Laplacians, and Clustering*,
CIKM 2020](https://doi.org/10.1145/3340531.3412034).

## 3. Clustering and community detection

**Hypergraph modularity.** The graph modularity function does not transfer uniquely: one has to
decide when a hyperedge counts as "inside" a community — all its vertices, a majority, at least two?
Each choice gives a different modularity. Kamiński et al. develop this family and a Louvain-style
algorithm over it ([Kamiński, Poulin, Prałat, Szufel and Théberge, *Clustering via hypergraph
modularity*, *PLOS ONE* 14(11), 2019](https://doi.org/10.1371/journal.pone.0224307); extended in
[Kamiński, Misiorek, Prałat and Théberge, *Modularity based community detection in hypergraphs*,
*Journal of Complex Networks*, 2024](https://doi.org/10.1093/comnet/cnae041)).

On a knowledge hypergraph, a community is a **topic**: a set of entities that co-participate in
facts. Because the modularity variant encodes what "participating together" means, the choice is a
domain decision — for n-ary facts with a dominant role (a patient, a company), majority-based
variants behave differently from strict ones.

**Spectral clustering** via the hypergraph Laplacian, and **s-component decomposition** (§1), are the
two cheaper alternatives. s-components are the most interpretable: they are exactly "facts connected
by sharing ≥ s entities".

## 4. Motifs

Higher-order motif analysis counts small patterns of *overlapping hyperedges* — the hypergraph
analogue of triangle counting — and shows these patterns are not predicted by the clique expansion
([Lotito, Musciotto, Montresor and Battiston, *Higher-order motif analysis in hypergraphs*,
*Communications Physics* 5, 2022](https://doi.org/10.1038/s42005-022-00858-7)).

This connects directly to expressivity: the WidthWall result indexes what a hypergraph neural network
can compute by the **generalized hypertree width of the patterns whose densities it can access**
([hypergraph-neural-networks.md](hypergraph-neural-networks.md) §3.2). Motif counting is therefore
not only descriptive statistics — it is the same quantity that bounds learnability.

For a knowledge hypergraph, motifs over *labelled* hyperedges would be schema-level patterns ("an
`employment` fact and an `education` fact sharing a person and an institution"). No motif analysis
over role-labelled hypergraphs was found for this note. `[unverified — appears to be a gap]`

## 5. Hyperpaths in directed hypergraphs

*Directed in sense D2, tail set → head set; for the three incompatible senses of "directed
hypergraph" see [directed and typed hyperedges](../02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md) §1.*

Covered in [logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md)
§1, because in the directed case a hyperpath *is* a proof. The structures:

- **B-arc**: tail is a set, head is a single vertex — a Horn clause.
- **F-arc**: single-vertex tail, set head.
- **BF-hypergraph**: both.

Foundations: [Gallo, Longo, Pallottino and Nguyen, *Directed hypergraphs and applications*, *Discrete
Applied Mathematics* 42(2–3), 1993](https://doi.org/10.1016/0166-218x(93)90045-p); survey
[Ausiello and Laura, *Theoretical Computer Science*, 2016](https://doi.org/10.1016/j.tcs.2016.03.016).

Complexity, from the most recent primary source: "there are no output-polynomial time algorithms for
the enumeration of induced s-t hyperpaths and minimal s-t separators unless P = NP"; s-t hyperpath
enumeration on BF-hypergraphs is at least as hard as minimal transversal enumeration; but "the s-t
hyperpath enumeration for a B-hypergraph can be solved in polynomial delay by backtracking"
([Kurita and Mann, arXiv:2507.07528, 2025](https://arxiv.org/abs/2507.07528)). Shortest-hyperpath
algorithms in the weighted setting, including K-shortest variants, are given by
[Nielsen, Andersen and Pretolani, *Finding the K shortest hyperpaths*, *Computers & Operations
Research* 32(6), 2005](https://doi.org/10.1016/j.cor.2003.11.014).

## 6. Transversals (hitting sets) and monotone dualization

A **transversal** (hitting set) of a hypergraph is a vertex set meeting every hyperedge; the
**minimal transversals** form the *dual* hypergraph. Enumerating them is the classical *monotone
dualization* problem, and whether it admits an output-polynomial algorithm has been open for
decades — the best known bound is quasi-polynomial ([Eiter, Makino and Gottlob, *Computational
aspects of monotone dualization: A brief survey*, *Discrete Applied Mathematics* 156(11),
2008](https://doi.org/10.1016/j.dam.2007.04.017)). Kurita and Mann's 2025 reduction (§5) ties
hyperpath enumeration to it, which is why that problem is considered hard.

Knowledge-base uses: a minimal transversal is a **minimal set of entities whose removal breaks every
fact** in a set — i.e. a minimal explanation, a minimal repair, or a minimal set of facts to verify.
Any feature phrased as "smallest set of things that touches all of these facts" is a transversal
problem and inherits this complexity.

## 7. Matching and covering

Maximum matching in a hypergraph (a set of pairwise disjoint hyperedges) is **set packing**; for
3-uniform hypergraphs it is 3-dimensional matching, one of Karp's original NP-complete problems
([Karp, *Reducibility among Combinatorial Problems*, in *Complexity of Computer Computations*,
1972](https://doi.org/10.1007/978-1-4684-2001-2_9)). Minimum vertex cover of a hypergraph is the
hitting-set problem of §6. So: the two textbook polynomial graph problems both become intractable at
arity ≥ 3. Plan for approximation or for small instances.

## 8. Complexity summary

| Problem | Graph | Hypergraph |
|---|---|---|
| Connected components | O(n + m) | O(n + Σ\|e\|) for s = 1; via L_s(H) for s > 1, with Θ(\|E\|²) intersections to build |
| Shortest path / distance | O(m + n log n) | s-distance = graph distance on L_s(H); weighted directed hyperpaths: see [Nielsen et al. 2005](https://doi.org/10.1016/j.cor.2003.11.014) |
| Enumerate s-t paths | polynomial delay | polynomial delay for B-hypergraphs; not output-polynomial for induced hyperpaths unless P = NP ([Kurita and Mann 2025](https://arxiv.org/abs/2507.07528)) |
| Maximum matching | polynomial | NP-hard for arity ≥ 3 ([Karp 1972](https://doi.org/10.1007/978-1-4684-2001-2_9)) |
| Minimum vertex cover | NP-hard, 2-approximable | hitting set; enumeration of minimal ones is monotone dualization ([Eiter et al. 2008](https://doi.org/10.1016/j.dam.2007.04.017)) |
| Subgraph isomorphism | NP-complete | NP-hard (generalises the graph case); see [query-languages-for-hypergraphs.md](query-languages-for-hypergraphs.md) §10.1 |
| Community detection | modularity, Louvain | hypergraph modularity family; variant choice is a modelling decision ([Kamiński et al. 2019](https://doi.org/10.1371/journal.pone.0224307)) |
| PageRank | power iteration | several definitions; [Takai et al. 2020](https://arxiv.org/abs/2006.08302), [Chitra and Raphael 2019](https://arxiv.org/abs/1905.08287) |

## 9. A practical shortlist for a KHG system

1. **Inverted index entity → hyperedges.** Everything above is built on it.
2. **s-components at s = 1, 2, 3.** Cheap topical decomposition, interpretable, no hyperparameters
   beyond s.
3. **Personalised hypergraph PageRank** from a query's seed entities, for retrieval ranking.
4. **s-closeness** for "which facts are central to this topic".
5. **Keep transversal and matching features bounded** — they are the NP-hard corner.

## Open questions raised here

- What is the right s for knowledge hypergraphs in practice, and does it vary by domain? The
  literature reports s-analytics on co-authorship and biology hypergraphs, not on knowledge bases.
- Do role labels change the s-walk definition usefully — e.g. "s-walk where the shared entities play
  the same role"?
- Is there a motif analysis for role-labelled hypergraphs (§4)?
- Can hypergraph PageRank be made role-aware, in the sense of Chitra and Raphael's edge-dependent
  vertex weights?

## Sources

- Aksoy, S. G., Joslyn, C., Ortiz Marrero, C., Praggastis, B., Purvine, E. "Hypernetwork science via high-order hypergraph walks". *EPJ Data Science* 9, 2020; arXiv:1906.11295. <https://doi.org/10.1140/epjds/s13688-020-00231-0> · <https://arxiv.org/abs/1906.11295>
- Pacific Northwest National Laboratory. *HyperNetX*. Repository checked 20 September 2026. <https://github.com/pnnl/HyperNetX>
- Chitra, U., Raphael, B. J. *Random Walks on Hypergraphs with Edge-Dependent Vertex Weights*. ICML 2019; arXiv:1905.08287. <https://arxiv.org/abs/1905.08287>
- Takai, Y., Miyauchi, A., Ikeda, M., Yoshida, Y. "Hypergraph Clustering Based on PageRank". *KDD 2020*; arXiv:2006.08302. <https://doi.org/10.1145/3394486.3403248> · <https://arxiv.org/abs/2006.08302>
- Hayashi, K., Aksoy, S. G., Park, C. H., Park, H. "Hypergraph Random Walks, Laplacians, and Clustering". *CIKM 2020*. <https://doi.org/10.1145/3340531.3412034>
- Kamiński, B., Poulin, V., Prałat, P., Szufel, P., Théberge, F. "Clustering via hypergraph modularity". *PLOS ONE* 14(11), 2019. <https://doi.org/10.1371/journal.pone.0224307>
- Kamiński, B., Misiorek, P., Prałat, P., Théberge, F. "Modularity based community detection in hypergraphs". *Journal of Complex Networks*, 2024. <https://doi.org/10.1093/comnet/cnae041>
- Lotito, Q. F., Musciotto, F., Montresor, A., Battiston, F. "Higher-order motif analysis in hypergraphs". *Communications Physics* 5, 2022. <https://doi.org/10.1038/s42005-022-00858-7>
- Gallo, G., Longo, G., Pallottino, S., Nguyen, S. "Directed hypergraphs and applications". *Discrete Applied Mathematics* 42(2–3), 1993. <https://doi.org/10.1016/0166-218x(93)90045-p>
- Ausiello, G., Laura, L. "Directed hypergraphs: Introduction and fundamental algorithms — A survey". *Theoretical Computer Science*, 2016. <https://doi.org/10.1016/j.tcs.2016.03.016>
- Nielsen, L. R., Andersen, K. A., Pretolani, D. "Finding the K shortest hyperpaths". *Computers & Operations Research* 32(6), 2005. <https://doi.org/10.1016/j.cor.2003.11.014>
- Kurita, K., Mann, K. *On the Complexity of Hyperpath and Minimal Separator Enumeration in Directed Hypergraphs*. arXiv:2507.07528, 2025. <https://arxiv.org/abs/2507.07528>
- Eiter, T., Makino, K., Gottlob, G. "Computational aspects of monotone dualization: A brief survey". *Discrete Applied Mathematics* 156(11), 2008. <https://doi.org/10.1016/j.dam.2007.04.017>
- Karp, R. M. "Reducibility among Combinatorial Problems". In *Complexity of Computer Computations*, 1972. <https://doi.org/10.1007/978-1-4684-2001-2_9>
