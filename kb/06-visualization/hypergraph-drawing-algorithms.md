---
title: Hypergraph drawing algorithms and their complexity
type: survey
status: draft
tags: [hypergraph, visualization, graph-drawing, planarity, supports, euler-diagram, force-directed, complexity]
created: 2026-09-20
updated: 2026-09-20
---

# Hypergraph drawing algorithms and their complexity

[visual-encodings-catalogue.md](visual-encodings-catalogue.md) asks *what a hyperedge should look
like*. This note asks *how to compute the picture*, and *what is provably hard*. It covers the two
classical drawing standards, the planarity notions they induce, the support machinery that underlies
most subset-standard algorithms, the force-directed family, Euler-diagram generation, bundling, and
the metro-map metaphor.

Throughout, `H = (V, E)` is a hypergraph, `n = |V|`, `m = |E|`, and the *incidence* (Levi, König)
graph is the bipartite graph `B(H)` on `V ∪ E` with an edge `{v, e}` whenever `v ∈ e`.

---

## 1. The two standards (Mäkinen 1990)

Mäkinen classified hypergraph drawings into two families that still organise the field
([Mäkinen, 1990](https://doi.org/10.1080/00207169008803875)):

| | Vertices | Hyperedges | Typical algorithm |
|---|---|---|---|
| **Subset standard** | points | closed curves enveloping their vertices | position vertices, then compute an envelope (hull, isocontour, Bézier) |
| **Edge standard** | points | smooth curves / trees connecting their vertices | reduce to a graph, run a graph layout, then route |

Arafat and Bressan restate the distinction exactly this way: "In Edge based drawings, hyperedges are
drawn as smooth curves connecting their vertices. In Subset based drawings, hyperedges are drawn as
closed curves enveloping their vertices"
([Arafat & Bressan, 2017](https://doi.org/10.1007/978-3-319-64471-4_31)).

Mäkinen's second contribution is methodological and is why most modern systems look the way they do:
in many cases "the problem of drawing a hypergraph can be reduced to the problem of drawing normal
graphs", particularly in the edge standard ([Mäkinen, 1990](https://doi.org/10.1080/00207169008803875)).
Every algorithm in sections 3–5 below is an instance of that reduction.

Mäkinen also formulated desirable properties of a subset-standard drawing, which later work uses as
its aesthetic starting point ([Arafat & Bressan, 2017](https://doi.org/10.1007/978-3-319-64471-4_31),
citing Mäkinen).

---

## 2. Planarity: three inequivalent notions

Unlike graphs, "planar hypergraph" is not one concept. At least three are in use, and they do not
coincide.

### 2.1 Zykov planarity

Zykov (1974) defined a hypergraph as planar when its vertices can be drawn as points and its
hyperedges as closed curves (equivalently, trees) meeting only at shared vertices
([Zykov, 1974](https://doi.org/10.1070/RM1974v029n06ABEH001303)). The key fact is that this is
decidable in linear time, because:

> A hypergraph is Zykov-planar if and only if its incidence bipartite graph is planar.

(stated as standard background in the subdivision-drawing literature,
[Kaufmann, van Kreveld & Speckmann, 2009](https://doi.org/10.1007/978-3-642-00219-9_39); see also
[Ouvrard, 2020, sect. 11](https://arxiv.org/abs/2002.05014)). So Zykov planarity inherits
Hopcroft–Tarjan linear-time planarity testing on `B(H)`. This is the *cheap* notion, and it is one
more reason the bipartite encoding is the pragmatic default (see
[knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md)).

### 2.2 Vertex planarity / Venn-style drawability (Johnson & Pollak 1987)

Johnson and Pollak asked instead when a hypergraph can be drawn in the *subset* standard as a
Venn-style diagram, and proved the problem NP-complete
([Johnson & Pollak, 1987](https://doi.org/10.1002/jgt.3190110306)). Their paper is the origin of
both the vertex-planar/edge-planar distinction and of the hardness of planar supports (see 2.3).

### 2.3 Subdivision drawings

In a *subdivision drawing* each vertex is a face of a planar subdivision and the faces of every
hyperedge form a connected region; vertex-based Venn diagrams and concrete Euler diagrams are special
cases ([Kaufmann, van Kreveld & Speckmann, 2009](https://doi.org/10.1007/978-3-642-00219-9_39)).
Deciding existence of a subdivision drawing is NP-complete (ibid.). Restricted classes —
hypergraphs forming a hierarchy — admit *compact* subdivision drawings with convex faces (ibid.).
Vertices with identical membership ("twins") can be exploited to speed up the search
([van Bevern et al., 2016](https://doi.org/10.1007/978-3-319-50106-2_6)).

---

## 3. Supports: the combinatorial core of subset-standard drawing

A **support** (host graph) of `H = (V, A)` is a graph `G = (V, E)` such that every hyperedge induces
a *connected* subgraph of `G` ([Brandes, Cornelsen, Pampel & Sallaberry, 2011/2012](https://doi.org/10.1007/978-3-642-19222-7_3)).
Once you have a support with a nice shape, you can draw the support and then thicken each hyperedge's
induced subgraph into a region — which is what Kelp Diagrams, KelpFusion and MetroSets all do.

Brandes et al. summarise the landscape, and add the path-based case (their own contribution):

| Support class asked for | Complexity | Source |
|---|---|---|
| tree support | linear time | Tarjan & Yannakakis, via [Brandes et al., 2011](https://doi.org/10.1007/978-3-642-19222-7_3) |
| path or cycle support | linear time | [Brandes et al., 2011](https://doi.org/10.1007/978-3-642-19222-7_3) |
| tree support with bounded degrees | polynomial | ibid. |
| cactus support | polynomial | ibid. |
| minimum-weight tree support | polynomial | ibid. |
| minimum-edge support, hyperedges closed under intersection | polynomial | ibid. |
| outerplanar support, closed under intersection **and** difference | polynomial | ibid. |
| **planar support** | **NP-complete** | [Johnson & Pollak, 1987](https://doi.org/10.1002/jgt.3190110306), via ibid. |
| **compact support** | **NP-complete** | ibid. |
| **2-outerplanar support** | **NP-complete** | [Brandes et al., 2011](https://doi.org/10.1007/978-3-642-19222-7_3) |
| planar support that is a path, cycle or tree | linear time | [Buchin et al., 2011](https://doi.org/10.7155/jgaa.00237) |
| planar support that is a bounded-degree tree | polynomial | ibid. |

A **path-based support** strengthens "connected" to "contains a Hamiltonian path": `G[h]` must
contain a path through every vertex of `h`. This is exactly the condition that lets you draw each
hyperedge as one metro line. Brandes et al. prove: computing a minimum-edge path-based support is
NP-complete, deciding existence of a *planar* path-based support is NP-complete, but a path-based
*tree* support can be computed in polynomial time when one exists
([Brandes et al., 2011](https://doi.org/10.1007/978-3-642-19222-7_3); journal version
[Journal of Discrete Algorithms 14:248–261, 2012](https://doi.org/10.1016/j.jda.2011.12.009)).

Practical consequence for a knowledge hypergraph: KHG hyperedges (n-ary facts) are *not* closed under
intersection, and the fact hypergraph is rarely planar, so none of the polynomial cases above apply.
Support-based drawing is therefore a poor fit for a general KHG; the incidence graph is not.

---

## 4. Force-directed layouts of the bipartite / associated graph

This is the workhorse for anything larger than a diagram.

### 4.1 Bertault & Eades 2000 — PATATE

The PATATE system applies "a classical force directed method to a dynamic graph, which is deduced,
at a given iteration time, from the hypergraph structure and particular vertex locations"
([Bertault & Eades, 2000](https://doi.org/10.1007/3-540-44541-2_15)). Two of the three underlying
graphs it proposes are the ones still in use today:

1. the **incidence graph with a dummy vertex per hyperedge** (the extra-node/bipartite encoding); and
2. a **minimal Euclidean spanning tree** over the vertices of each hyperedge, recomputed as the
   layout moves — with a variant using a Euclidean **Steiner tree** (ibid.).

The drawing is finished by contouring the tree: the algorithm "constructs a Euclidean Steiner tree
from the position of the vertices in a hyperedge, uses force-directed graph drawing algorithm to get
the location of the vertices and draws a contour around the edges of the tree"
([Arafat & Bressan, 2017](https://doi.org/10.1007/978-3-319-64471-4_31), describing Bertault & Eades).
The essential idea — *recompute the auxiliary graph inside the force loop* — is what makes it a
hypergraph algorithm rather than a graph algorithm with a post-process.

### 4.2 Arafat & Bressan 2017 — a family of associated graphs

Arafat and Bressan systematise the reduction into four **associated graphs**, each yielding one
algorithm ([Arafat & Bressan, 2017](https://doi.org/10.1007/978-3-319-64471-4_31)):

- **complete**: every pair inside a hyperedge is joined (the clique expansion). Strong attraction,
  fewest crossings expected, but cluttered.
- **cycle**: vertices of `Eᵢ` sorted clockwise by current position and joined in a cycle. A subgraph
  of the complete graph, chosen "since the desire to have a sparse drawing with good Coverage and
  Regularity is the driving force".
- **star**: a barycentre vertex `bᵢ` per hyperedge joined to each member — i.e. the bipartite
  encoding with a geometric hub.
- **wheel**: cycle plus barycentre.

Vertices are initialised randomly, circularly (on a circle of radius `k·|Eⱼ|`) or on a grid, then
Fruchterman–Reingold runs, then each hyperedge is enveloped in a closed curve (a convex polygon).

They also give four measurable aesthetics for hypergraph drawings (ibid.):

- **Concavity** — the number of non-convex hyperedge shapes (fewer is better);
- **Planarity** — the number of crossings between *non-adjacent* hyperedges;
- **Coverage** — mean area per vertex of the drawing divided by mean area per vertex of the canvas,
  with 1.0 meaning full use of the canvas;
- **Regularity** — uniformity of vertex distribution over the canvas.

These are, as far as this KB has found, the only published quantitative aesthetics specific to
hypergraph drawing; Fischer et al. note the field still has "no established performance metrics"
([Fischer, Frings, Keim & Seebacher, 2021](https://arxiv.org/abs/2107.13936)).

### 4.3 What the libraries actually do

- HyperNetX `hnx.draw` runs a NetworkX spring layout on the bipartite graph, then pads a
  `scipy.spatial.ConvexHull` per hyperedge (source `hypernetx/drawing/rubber_band.py`, v2.4.3,
  checked 2026-09-20) — i.e. star-associated-graph force layout plus convex envelope, the Arafat–Bressan
  *star* algorithm.
- XGI `xgi.barycenter_spring_layout` places a phantom vertex at each hyperedge's barycentre and
  springs the whole thing, then `draw(..., hull=True)` envelopes it (XGI 0.10.2, checked 2026-09-20).
- hypergraphx `draw_hypergraph` / `draw_clique` / `draw_bipartite` offer the clique and bipartite
  associated graphs explicitly (hypergraphx 1.8.0, checked 2026-09-20).

See [tools-and-libraries.md](tools-and-libraries.md) and
[visualization-cookbook-for-this-kb.md](visualization-cookbook-for-this-kb.md).

---

## 5. Euler-diagram generation

Euler diagrams are the subset standard taken to its logical conclusion: closed curves whose overlap
*regions* carry the semantics. Automatic generation is a field of its own
([Rodgers, 2014](https://doi.org/10.1016/j.jvlc.2013.08.006)).

Milestones relevant here:

- **Flower & Howse, 2002** generate *concrete* Euler diagrams automatically, up to three sets
  ([Flower & Howse, 2002](https://doi.org/10.1007/3-540-46037-3_6)).
- **Verroust & Viaud, 2004** extend drawability guarantees to *extended* Euler diagrams for up to
  eight sets ([Verroust & Viaud, 2004](https://doi.org/10.1007/978-3-540-25931-2_13)).
- **Simonetto, Auber & Archambault, 2009** drop the regional well-formedness constraints entirely and
  generate *Euler-like* diagrams with "no undrawable instances", drawing sets as closed Bézier curves
  ([Simonetto, Auber & Archambault, 2009](https://doi.org/10.1111/j.1467-8659.2009.01452.x)). The
  method "applies a force-directed algorithm that preserves edge-crossing properties on the
  intersection graph of the hypergraph" and "approximates the set boundaries by computing polygons"
  ([Arafat & Bressan, 2017](https://doi.org/10.1007/978-3-319-64471-4_31), describing it). It is
  implemented in Tulip.
- **Kehlbeck, Görtler, Wang & Deussen, 2021 (SpEuler)** produce semantics-preserving, well-formed
  layouts via a planar monotone dual graph ([Kehlbeck et al., 2021](https://arxiv.org/abs/2108.03529)).
- **eulerAPE** draws area-proportional 3-set Venn diagrams with ellipses
  ([Micallef & Rodgers, 2014](https://doi.org/10.1371/journal.pone.0101717)).

Two cautions for KHG use. First, "the Subset based drawings differ from Euler diagrams in that the
former does not impose regional constraints (e.g. not allowing empty zones, allowing exactly two
points of intersections between contours representing sets) as the latter"
([Arafat & Bressan, 2017](https://doi.org/10.1007/978-3-319-64471-4_31)) — if you only need to show
membership, you do not need a real Euler diagram and should not pay its cost. Second, which
well-formedness properties actually help a reader was tested empirically and the answer is *some, not
all* ([Rodgers, Zhang & Purchase, 2012](https://doi.org/10.1109/TVCG.2011.143)); see
[perception-and-evaluation-studies.md](perception-and-evaluation-studies.md).

---

## 6. Orthogonal / layered drawing (the VLSI line)

A separate tradition draws hypergraphs orthogonally, because a circuit *net* is a hyperedge.
Eschbach, Günther and Becker treat the layered case: they prove that optimally assigning the
hyperedges between two layers to tracks is NP-hard, and give an algorithm that "dynamically reorders
the nodes within the layers" rather than routing after placement, reducing hyperedge crossings
([Eschbach, Günther & Becker, 2006](https://doi.org/10.7155/jgaa.00122), JGAA 10(2):141–157).

The modern information-visualisation counterpart is Di Bartolomeo et al., who compare six
transformations from a layered hypergraph to a graph so that Sugiyama-style layered layout applies
(including *split-clique*, *split-path* and *centroid* — the latter being the extra-node encoding
again), and note that split-clique "adds many edges, and the number of edges scales up very fast"
([Di Bartolomeo et al., 2022](https://doi.org/10.1111/cgf.14538)).

---

## 7. Bundling

Two different things are called bundling in this area, and they should not be confused.

1. **Edge bundling as clutter reduction.** Classical graph edge bundling merges edges with similar
   position/direction to cut crossings ([Holten, 2006](https://doi.org/10.1109/TVCG.2006.147);
   [Holten & van Wijk, 2009](https://doi.org/10.1111/j.1467-8659.2009.01450.x)). Applied to the
   *incidence* graph of a hypergraph, the `n` spokes of one hyperedge naturally bundle into a trunk,
   which is visually the Steiner-tree rendering of Bertault & Eades. Edge-Path Bundling is the
   less-ambiguous modern variant ([Wallinger et al., 2022](https://doi.org/10.1109/TVCG.2021.3114795);
   preprint [arXiv:2108.05467](https://arxiv.org/abs/2108.05467)). `[unverified]` This KB found no
   published algorithm that bundles hyperedge spokes *as such*; the practice is to bundle the
   bipartite expansion.
2. **Hyperedge bundling as data reduction.** In neuroimaging, "hyperedge bundling" means grouping
   observed pairwise connections into hyperedges by their adjacency in signal mixing, to separate true
   from spurious interactions — a modelling step whose *output* is then drawn
   ([Wang, Lobier, Siebenhühner, Puoliväli, Palva & Palva, 2018](https://doi.org/10.1016/j.neuroimage.2018.01.056),
   NeuroImage 173:610–622; code at <https://github.com/palvalab/hyperedges>). Same word, different
   operation.

---

## 8. Metro-map drawing

MetroSets turns a set system into a metro map: each hyperedge is a line, each vertex a station
([Jacobsen, Wallinger, Kobourov & Nöllenburg, 2021](https://doi.org/10.1109/TVCG.2020.3030475)). The
pipeline is exactly the support machinery of section 3: compute a path-based support, then lay it out
octilinearly, then draw lines along the Hamiltonian paths. The support step is the one Brandes et al.
characterised; the layout step inherits metro-map layout algorithms.

Bend minimisation on top of a given support has its own complexity: minimising *curve complexity*
(bends per line) is NP-complete even on restricted trees, while minimising *total* bends on trees is
polynomial ([Cornelsen, Förster, Gupta, Kobourov & Zink, 2025](https://arxiv.org/abs/2511.22508)).

Cost: every vertex of a hyperedge must lie on one path, which imposes an order the data may not have,
and the survey flags "enforced octolinearity and unavoidable crossings leading to clutter"
([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)). Benefit: it is the only abstract set
technique that has won a three-way controlled readability study
([Wallinger, Jacobsen, Kobourov & Nöllenburg, 2021](https://doi.org/10.1109/TVCG.2021.3074615)).

---

## 9. Point-line incidence drawings

The most constrained edge-standard variant: vertices are points, each hyperedge is a straight line or
segment through exactly its points. Deciding whether such a representation exists is ∃R-hard for six
of eight problem variants studied
([Dobler, Kobourov, Mondal & Nöllenburg, 2025](https://doi.org/10.1007/978-3-031-82670-2_18); journal
version [DMTCS 28:3, 2026](https://doi.org/10.46298/dmtcs.15876)). Of theoretical interest; not a
practical KHG technique.

---

## 10. Summary of hardness results

| Problem | Status |
|---|---|
| Zykov planarity (incidence graph planar) | linear time |
| Venn-style (vertex-based) drawability | NP-complete ([Johnson & Pollak, 1987](https://doi.org/10.1002/jgt.3190110306)) |
| subdivision drawing existence | NP-complete ([Kaufmann et al., 2009](https://doi.org/10.1007/978-3-642-00219-9_39)) |
| planar / compact / 2-outerplanar support | NP-complete (§3) |
| tree, path, cycle, cactus, bounded-degree-tree support | polynomial (§3) |
| minimum-edge or planar path-based support | NP-complete ([Brandes et al., 2011](https://doi.org/10.1007/978-3-642-19222-7_3)) |
| path-based tree support | polynomial (ibid.) |
| track assignment in layered orthogonal hypergraph drawing | NP-hard ([Eschbach et al., 2006](https://doi.org/10.7155/jgaa.00122)) |
| metro-line curve-complexity minimisation on restricted trees | NP-complete ([Cornelsen et al., 2025](https://arxiv.org/abs/2511.22508)) |
| point-line incidence representability | ∃R-hard (6 of 8 variants) ([Dobler et al., 2025](https://doi.org/10.1007/978-3-031-82670-2_18)) |

The practical reading: **everything that insists on a nice planar region structure is hard;
everything that goes through the incidence graph is easy.** For knowledge hypergraphs, whose facts
overlap heavily and arbitrarily, this settles the default in favour of the bipartite encoding plus a
force-directed or layered graph layout, with region overlays reserved for small curated excerpts.

## Sources

- Mäkinen, E. "How to draw a hypergraph." International Journal of Computer Mathematics 34(3-4):177–185, 1990. https://doi.org/10.1080/00207169008803875
- Zykov, A. A. "Hypergraphs." Russian Mathematical Surveys 29(6):89–156, 1974. https://doi.org/10.1070/RM1974v029n06ABEH001303
- Johnson, D. S., Pollak, H. O. "Hypergraph planarity and the complexity of drawing Venn diagrams." Journal of Graph Theory 11(3):309–325, 1987. https://doi.org/10.1002/jgt.3190110306
- Kaufmann, M., van Kreveld, M., Speckmann, B. "Subdivision Drawings of Hypergraphs." Graph Drawing 2008, LNCS 5417, pp. 396–407, 2009. https://doi.org/10.1007/978-3-642-00219-9_39
- van Bevern, R., Kanj, I., Komusiewicz, C., Niedermeier, R., Sorge, M. "Twins in Subdivision Drawings of Hypergraphs." Graph Drawing 2016, LNCS 9801, pp. 67–80. https://doi.org/10.1007/978-3-319-50106-2_6
- Brandes, U., Cornelsen, S., Pampel, B., Sallaberry, A. "Path-Based Supports for Hypergraphs." IWOCA 2010, LNCS 6460, pp. 20–33, 2011. https://doi.org/10.1007/978-3-642-19222-7_3 ; journal version: Journal of Discrete Algorithms 14:248–261, 2012. https://doi.org/10.1016/j.jda.2011.12.009 ; open copy: https://kops.uni-konstanz.de/bitstreams/c1aea7f2-bc74-4f56-a387-6d833cd348a9/download
- Buchin, K., van Kreveld, M., Meijer, H., Speckmann, B., Verbeek, K. "On Planar Supports for Hypergraphs." Journal of Graph Algorithms and Applications 15(4):533–549, 2011. https://doi.org/10.7155/jgaa.00237
- Bertault, F., Eades, P. "Drawing Hypergraphs in the Subset Standard (Short Demo Paper)." Graph Drawing 2000, LNCS 1984, pp. 164–169, 2001. https://doi.org/10.1007/3-540-44541-2_15
- Arafat, N. A., Bressan, S. "Hypergraph Drawing by Force-Directed Placement." DEXA 2017, LNCS 10439, pp. 387–394. https://doi.org/10.1007/978-3-319-64471-4_31 ; author copy: https://toggled.github.io/naheed/assets/pdf/dexa17.pdf
- Fruchterman, T. M. J., Reingold, E. M. "Graph Drawing by Force-Directed Placement." Software: Practice and Experience 21(11):1129–1164, 1991. https://doi.org/10.1002/spe.4380211102
- Flower, J., Howse, J. "Generating Euler Diagrams." Diagrams 2002, LNAI 2317, pp. 61–75. https://doi.org/10.1007/3-540-46037-3_6
- Verroust, A., Viaud, M.-L. "Ensuring the Drawability of Extended Euler Diagrams for up to 8 Sets." Diagrams 2004, LNAI 2980, pp. 128–141. https://doi.org/10.1007/978-3-540-25931-2_13
- Simonetto, P., Auber, D., Archambault, D. "Fully Automatic Visualisation of Overlapping Sets." Computer Graphics Forum 28(3):967–974, 2009. https://doi.org/10.1111/j.1467-8659.2009.01452.x
- Kehlbeck, R., Görtler, J., Wang, Y., Deussen, O. "SpEuler: Semantics-preserving Euler Diagrams." IEEE TVCG, 2021. DOI 10.1109/TVCG.2021.3114834. https://arxiv.org/abs/2108.03529
- Micallef, L., Rodgers, P. "eulerAPE: Drawing Area-Proportional 3-Venn Diagrams Using Ellipses." PLoS ONE 9(7):e101717, 2014. https://doi.org/10.1371/journal.pone.0101717
- Rodgers, P. "A survey of Euler diagrams." Journal of Visual Languages & Computing 25(3):134–155, 2014. https://doi.org/10.1016/j.jvlc.2013.08.006
- Rodgers, P., Zhang, L., Purchase, H. "Wellformedness Properties in Euler Diagrams: Which Should Be Used?" IEEE TVCG 18(7):1089–1100, 2012. https://doi.org/10.1109/TVCG.2011.143
- Eschbach, T., Günther, W., Becker, B. "Orthogonal Hypergraph Drawing for Improved Visibility." Journal of Graph Algorithms and Applications 10(2):141–157, 2006. https://doi.org/10.7155/jgaa.00122
- Di Bartolomeo, S., Pister, A., Buono, P., Plaisant, C., Dunne, C., Fekete, J.-D. "Six Methods for Transforming Layered Hypergraphs to Apply Layered Graph Layout Algorithms." Computer Graphics Forum 41(3), EuroVis 2022. https://doi.org/10.1111/cgf.14538
- Holten, D. "Hierarchical Edge Bundles: Visualization of Adjacency Relations in Hierarchical Data." IEEE TVCG 12(5):741–748, 2006. https://doi.org/10.1109/TVCG.2006.147
- Holten, D., van Wijk, J. J. "Force-Directed Edge Bundling for Graph Visualization." Computer Graphics Forum 28(3):983–990, 2009. https://doi.org/10.1111/j.1467-8659.2009.01450.x
- Wallinger, M., Archambault, D., Auber, D., Nöllenburg, M., Peltonen, J. "Edge-Path Bundling: A Less Ambiguous Edge Bundling Approach." IEEE TVCG 28(1):313–323, 2022. https://doi.org/10.1109/TVCG.2021.3114795 ; https://arxiv.org/abs/2108.05467
- Wang, S. H., Lobier, M., Siebenhühner, F., Puoliväli, T., Palva, S., Palva, J. M. "Hyperedge bundling: A practical solution to spurious interactions in MEG/EEG source connectivity analyses." NeuroImage 173:610–622, 2018. https://doi.org/10.1016/j.neuroimage.2018.01.056 ; code: https://github.com/palvalab/hyperedges (checked 2026-09-20)
- Jacobsen, B., Wallinger, M., Kobourov, S., Nöllenburg, M. "MetroSets: Visualizing Sets as Metro Maps." IEEE TVCG 27(2):1257–1267, 2021. https://doi.org/10.1109/TVCG.2020.3030475
- Wallinger, M., Jacobsen, B., Kobourov, S., Nöllenburg, M. "On the Readability of Abstract Set Visualizations." IEEE TVCG 27(6):2821–2832, 2021. https://doi.org/10.1109/TVCG.2021.3074615 ; https://arxiv.org/abs/2101.08155
- Cornelsen, S., Förster, H., Gupta, S., Kobourov, S., Zink, J. "Hypergraphs as Metro Maps: Drawing Paths with Few Bends in Trees, Cacti, and Plane 4-Graphs." arXiv:2511.22508, 2025. https://arxiv.org/abs/2511.22508
- Dobler, A., Kobourov, S., Mondal, D., Nöllenburg, M. "Representing Hypergraphs by Point-Line Incidences." Graph Drawing 2024, LNCS, pp. 241–254, 2025. https://doi.org/10.1007/978-3-031-82670-2_18 ; journal version DMTCS 28:3, 2026. https://doi.org/10.46298/dmtcs.15876
- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 short papers, pp. 81–85. DOI 10.1109/VIS49827.2021.9623305. https://arxiv.org/abs/2107.13936
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- HyperNetX 2.4.3 source `hypernetx/drawing/rubber_band.py` (PyPI upload 2026-07-23; inspected 2026-09-20). https://github.com/pnnl/HyperNetX
- XGI 0.10.2 `xgi/drawing/draw.py` and `xgi.barycenter_spring_layout` (PyPI upload 2026-05-15; inspected 2026-09-20). https://github.com/xgi-org/xgi
- hypergraphx 1.8.0 `hypergraphx/viz/` (PyPI upload 2026-05-18; inspected 2026-09-20). https://github.com/HGX-Team/hypergraphx
