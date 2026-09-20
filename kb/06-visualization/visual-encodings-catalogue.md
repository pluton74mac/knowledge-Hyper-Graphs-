---
title: Catalogue of visual encodings for hypergraphs
type: survey
status: draft
tags: [hypergraph, visualization, visual-encoding, node-link, matrix, euler-diagram, PAOH, set-visualization]
created: 2026-09-19
updated: 2026-09-19
---

# Catalogue of visual encodings for hypergraphs

A hypergraph `H = (V, E)` has hyperedges that are arbitrary subsets of `V`. There is no single
natural drawing of a subset, so every hypergraph visualisation is a *design decision* about
what a hyperedge looks like. This note catalogues the encodings that appear in the literature,
with a sketch, pros and cons, and the papers or tools in which each was proposed or is used.

Two classical axes organise the space:

- **Subset standard vs edge standard** ([Mäkinen, 1990](https://doi.org/10.1080/00207169008803875)):
  in the subset standard the vertices of a hyperedge are drawn as points and the hyperedge as a
  closed envelope around them; in the edge standard hyperedges are drawn as curves/branches that
  connect the vertices. Ouvrard's review adds that the Zykov representation "cannot be totally put
  neither in the edge standard nor in the subset standard"
  ([Ouvrard, 2020, sect. 11](https://arxiv.org/abs/2002.05014)).
- **Representation method** in the only dedicated survey to date: *node-link*, *timeline-based* and
  *matrix-based* approaches ([Fischer, Frings, Keim, Seebacher, 2021](https://arxiv.org/abs/2107.13936),
  IEEE VIS short paper, 14 approaches compared).

Set visualisation is the neighbouring field: a family of sets over one universe *is* a hypergraph,
and the set-visualisation STAR of [Alsallakh et al., 2016](https://doi.org/10.1111/cgf.12722) is the
most complete taxonomy of the subset-standard side. See
[set-visualization-connection.md](set-visualization-connection.md).

---

## 1. Node-link encodings with an explicit hyperedge node (edge standard)

### 1.1 Bipartite / incidence / Levi / König graph ("extra node")

Every hyperedge becomes a node of a second type; an ordinary edge joins it to each member vertex.

```
   v1 ──┐
   v2 ──┼── [e1]        v1 ── [e2] ── v4
   v3 ──┘
```

- Names in the literature: *incidence graph*, *Levi graph*, *König representation* (Zykov 1974,
  as reported by [Ouvrard, 2020](https://arxiv.org/abs/2002.05014)), *extra-node representation*
  ([Ouvrard, Le Goff, Marchand-Maillet, 2017](https://arxiv.org/abs/1707.00115)), *association
  meta-node* in EGAN ([Paquette & Tokuyasu, 2011](https://doi.org/10.1117/12.890220)), *centroid
  methods* in layered layouts ([Di Bartolomeo et al., 2022](https://doi.org/10.1111/cgf.14538)),
  *two-column* / `draw_bipartite` in HyperNetX and XGI (see [tools-and-libraries.md](tools-and-libraries.md)).
- Pros: lossless (the bipartite graph *is* the hypergraph); a hyperedge of size `n` costs `n` edges
  instead of `n(n-1)/2` for the clique expansion ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014));
  the hyperedge node can carry a label, a type, attributes, roles on its links and can itself be a
  member of another hyperedge (nesting). Any graph layout algorithm applies.
  Ouvrard et al. showed qualitatively and quantitatively that it retains more information and
  induces less clutter than the clique expansion ([Ouvrard et al., 2017](https://arxiv.org/abs/1707.00115)).
- Cons: doubles the number of drawn nodes; membership must be read via a two-hop path; hyperedge
  nodes look like data nodes unless shape/colour distinguishes them. Fischer et al. rate node-link
  approaches as supporting only "few (Venn diagram) up to several dozens" of hyperedges
  ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).
- This is the encoding this KB recommends as the *default* for knowledge hypergraphs; see
  [knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md).

### 1.2 Star expansion, clique expansion (2-section), path expansion

Graph *projections* that remove the hyperedge as an object:

```
clique:  v1─v2      star (= 1.1 with an unlabelled hub)      path:  v1─v2─v3
         │╲│
         v3─v4
```

- Clique expansion joins all pairs; it "generates graph with more edges" and loses which cliques were
  hyperedges ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)). Di Bartolomeo et al. call the same
  operations *split-clique* and *split-path* and note that split-clique "adds many edges, and the
  number of edges scales up very fast" ([Di Bartolomeo et al., 2022](https://doi.org/10.1111/cgf.14538)).
- Use only for layout (positions are then reused for hulls), or when the data really are pairwise.
  A multi-metric evaluation of how hypergraph-to-graph conversion affects a cooperative-work
  visualisation is [Xiong et al., 2024](https://doi.org/10.1007/978-981-99-9637-7_15).

### 1.3 Colour- or curve-coded hyperedge lines (edge standard proper)

The hyperedge is one curve/tree passing through or branching to all its vertices; identity is carried
by colour or by a label.

- Subset-standard drawing systems already mixed this in: Bertault and Eades' PATATE combined an
  incidence graph with a dummy vertex at the barycentre with a minimal Euclidean spanning tree
  covering the vertices of each hyperedge ([Bertault & Eades, 2000](https://doi.org/10.1007/3-540-44541-2_15)).
- LineSets draw each set as a single smooth curve through its elements
  ([Alper et al., 2011](https://doi.org/10.1109/TVCG.2011.186)); Kelp Diagrams and KelpFusion use
  shortest-path graphs between hull and line ([Dinkla et al., 2012](https://doi.org/10.1111/j.1467-8659.2012.03080.x);
  [Meulemans et al., 2013](https://doi.org/10.1109/TVCG.2013.76)).
- Point-line incidence drawings are the extreme case: vertices are points and each hyperedge is a
  straight line or segment through its points. Deciding whether such a representation exists is
  ∃R-hard for six of eight problem variants ([Dobler, Kobourov, Mondal, Nöllenburg, 2025](https://doi.org/10.1007/978-3-031-82670-2_18);
  journal version [2026](https://doi.org/10.46298/dmtcs.15876)).
- Pros: compact when hyperedges are few; Cons: colour limits scalability to roughly a dozen
  hyperedges, a known weakness of "traditional representations [that] often use color to distinguish
  between hyperedges" ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

### 1.4 Metro-map metaphor

Each hyperedge is a metro line, each vertex a station; the union of lines is a *path-based support*.

- MetroSets is an online tool for set systems using this metaphor
  ([Jacobsen, Wallinger, Kobourov, Nöllenburg, 2021](https://doi.org/10.1109/TVCG.2020.3030475)); in a
  controlled study it "performs and scales better" than LineSets and EulerView
  ([Wallinger et al., 2021](https://doi.org/10.1109/TVCG.2021.3074615)).
- Theory: minimising bends of metro lines on tree/cactus/plane-4 supports; NP-complete for the
  curve-complexity objective even on restricted trees, polynomial for total bends on trees
  ([Cornelsen, Förster, Gupta, Kobourov, Zink, 2025](https://arxiv.org/abs/2511.22508)).
- Cons noted by the survey: enforced octilinearity and unavoidable crossings on large inputs
  ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)). Every vertex of a hyperedge must lie on
  one path, which forces an ordering that the data may not have.

### 1.5 Radial layouts

Kerren and Jusufi place nodes centrally and draw each hyperedge as a circular dotted line around
them, "thereby eliminating overlaps and slightly increasing the scalability"; evaluated in a small
user study ([Kerren & Jusufi, 2013](https://doi.org/10.2312/PE.EuroVisShort.EuroVisShort2013.025-029),
as summarised by [Fischer et al., 2021](https://arxiv.org/abs/2107.13936)). Radial Sets is the
aggregation-based cousin for large overlapping sets ([Alsallakh et al., 2013](https://doi.org/10.1109/TVCG.2013.184)).
A "mixed coordinate" node-link layout for co-authorship hypergraphs colours node and link classes
([Nafar & Azami Zenouzagh, 2023](https://arxiv.org/abs/2310.19640)) `[unverified: no evaluation seen]`.

---

## 2. Subset-standard (region) encodings

### 2.1 Euler and Venn diagrams

```
  ┌─────────┐
  │ v1  ┌───┼────┐      e1 = {v1,v2}, e2 = {v2,v3}
  │  v2 │   │ v3 │
  └─────┼───┘    │
        └────────┘
```

- Euler diagrams "visually represent containment, intersection and exclusion using closed curves"
  ([Rodgers, 2014](https://doi.org/10.1016/j.jvlc.2013.08.006)). Automatic generation with "no
  undrawable instances" via Bézier curves and textures, implemented in Tulip
  ([Simonetto, Auber, Archambault, 2009](https://doi.org/10.1111/j.1467-8659.2009.01452.x)); semantics-preserving,
  well-formed layouts via a planar monotone dual graph ([Kehlbeck et al., 2021](https://arxiv.org/abs/2108.03529));
  area-proportional 3-set ellipses with eulerAPE ([Micallef & Rodgers, 2014](https://doi.org/10.1371/journal.pone.0101717)).
- Which well-formedness properties matter for readability was tested empirically
  ([Rodgers, Zhang, Purchase, 2012](https://doi.org/10.1109/TVCG.2011.143)).
- Complexity: deciding whether a hypergraph admits a vertex- or hyperedge-based Venn-style diagram is
  NP-complete ([Johnson & Pollak, 1987](https://doi.org/10.1002/jgt.3190110306)); see
  [hypergraph-drawing-algorithms.md](hypergraph-drawing-algorithms.md).
- Pros: matches how people sketch sets on a blackboard ("hyperedge ... drawn as a 'cloud' surrounding
  all its nodes", [Bergmann, 2009 talk](https://ronnybergmann.net/talks/2010-Diplomvortrag.pdf)).
  Cons: many hypergraphs are not drawable without duplication or disconnected regions; colour and
  region count explode beyond ~5–10 hyperedges.

### 2.2 Overlays on a given layout: Bubble Sets, KelpFusion, "rubber band" hulls

When node positions are fixed by some other criterion, sets are drawn as isocontours or hulls over them.

- Bubble Sets compute an implicit surface with marching squares around set members while routing
  around non-members ([Collins, Penn, Carpendale, 2009](https://doi.org/10.1109/TVCG.2009.122));
  F2-Bubbles gives a faster, more faithful construction with interactive editing
  ([Wang et al., 2021](https://doi.org/10.1109/TVCG.2021.3114761)).
- KelpFusion is a hybrid: a single parameter moves the shortest-path graph "from the minimal spanning
  tree to the convex hull"; it beat Bubble Sets in accuracy and time and LineSets in time
  ([Meulemans et al., 2013](https://doi.org/10.1109/TVCG.2013.76)).
- Convex hulls: HyperNetX's default `hnx.draw` ("rubber band") pads a `scipy.spatial.ConvexHull`
  around each hyperedge over a spring layout of the bipartite graph; nested hulls are spaced so a
  containing set surrounds a contained one (source: `hypernetx/drawing/rubber_band.py`, checked
  2026-09-19). XGI's `draw(..., hull=True)` and hypergraphx's `draw_hypergraph` do the same over a
  clique-projection spring layout (sources checked 2026-09-19).
- Pros: cheap, works on any layout, preserves the meaning of position. Cons: hulls of a
  non-convex member set swallow non-members; overlaps become unreadable after a few dozen sets.

### 2.3 Polygon metaphor (primal–dual)

Each hyperedge is a polygon whose corners are its vertices; a 2-edge is a segment, a 1-edge a dot.

```
        v1
       /  \        e1 = {v1,v2,v3} drawn as a triangle
     v2 ── v3 ── v4   e2 = {v3,v4}
```

- Proposed with joint optimisation of the *primal* (entities as points, relations as polygons) and
  *dual* (roles swapped) layouts ([Qu, Zhang, Zhang, 2022](https://doi.org/10.1109/TVCG.2021.3114759)).
- Scaled to "thousands of hyperedges" by iterative atomic simplification and reverse
  refinement, with planarity conditions for the polygon representation
  ([Oliver, Zhang, Zhang, 2024](https://doi.org/10.1109/TVCG.2023.3326599)); structure-aware
  simplification decomposes the bipartite representation into topological blocks, bridges and
  branches so that cycles survive simplification ([Oliver, Zhang, Zhang, 2025](https://doi.org/10.1109/TVCG.2024.3456367)).
  Desktop implementation: HGPolyVis (Apache-2.0, Windows).
- Pros: one shape per hyperedge, no colour needed for identity, dual view is free. Cons: polygons
  self-intersect and overlap for dense data ("excessive self-intersections when the input dataset is
  relatively large", [Oliver et al., 2024](https://arxiv.org/abs/2308.05043)); vertex order around
  the polygon is arbitrary.

### 2.4 Zykov representation and PaintSplash

Zykov (1974) defined a planar hypergraph as one whose vertices are points and hyperedges closed curves
that intersect only near a shared vertex; this equals planarity of the incidence graph. The *Zykov
representation* draws hyperedges "as faces of a subdivision realized by the vertices belonging to the
corresponding hyperedge", obtained by continuously deforming an Euler diagram until just before it
becomes the incidence graph; the intermediate coloured stage Ouvrard names *PaintSplash*
([Ouvrard, 2020, sect. 11.0.3–11.0.4](https://arxiv.org/abs/2002.05014); original
[Zykov, 1974](https://doi.org/10.1070/RM1974v029n06ABEH001303)). It is "intensively used with
simplicial complexes" (ibid.), which is exactly what XGI's `draw_simplices` renders (maximal
simplices as filled faces).

```
  v1●━━━━●v2        e1 = {v1,v2,v3} as a filled face touching its three vertices
     ╲  ▓╱
      ●v3━━━━●v4    e2 = {v3,v4} as a thick segment
```

### 2.5 Subdivision drawings, planar supports

Each vertex is a face of a planar subdivision and every hyperedge's faces form a connected region;
vertex-based Venn diagrams and concrete Euler diagrams are special cases
([Kaufmann, van Kreveld, Speckmann, 2009](https://doi.org/10.1007/978-3-642-00219-9_39)). The
combinatorial core is the *support*: a graph on `V` in which every hyperedge induces a connected
subgraph ([Buchin et al., 2011](https://doi.org/10.7155/jgaa.00237)). Twins (vertices with identical
membership) can be exploited algorithmically ([van Bevern et al., 2016](https://doi.org/10.1007/978-3-319-50106-2_6)).

---

## 3. Matrix and table encodings

### 3.1 Incidence matrix (biadjacency)

Rows = vertices, columns = hyperedges (or vice-versa), a mark where incident.

```
        e1 e2 e3
   v1   ■  ·  ■
   v2   ■  ■  ·
   v3   ·  ■  ■
```

- No overlap, no crossings; readability depends entirely on row/column ordering (seriation).
  The survey finds matrix approaches "feature more scalable techniques to display large correlated
  data-sets" ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).
- Early hypergraph-specific matrix work: overlapping hyperrectangle patterns
  ([Jin et al., 2008](https://doi.org/10.1109/ICDM.2008.102)).
- UpSet is an incidence-matrix layout for *set intersections* with bar charts of intersection sizes
  ([Lex et al., 2014](https://doi.org/10.1109/TVCG.2014.2346248)); HyperNetX exposes a hypergraph
  version as `draw_incidence_upset` (source checked 2026-09-19).
- Hyper-Matrix stacks a multi-level, drill-down matrix with a geometric deep learning model for
  temporal hypergraph models ([Fischer et al., 2020](https://doi.org/10.1109/TVCG.2020.3030408)).

### 3.2 PAOH (Parallel Aggregated Ordered Hypergraph)

```
  time ─────────────────────────▶
  v1  ━━●━━━━━━━━━━●━━━━━━━━━━━━━
  v2  ━━●━━━━━●━━━━●━━━━━━━━━━━━━      each vertical line = one hyperedge,
  v3  ━━━━━━━━●━━━━━━━━━━━●━━━━━━      dots mark its member vertices
  v4  ━━━━━━━━━━━━━━━━━━━━●━━━━━━
```

"PAOH represents vertices as parallel horizontal bars and hyperedges as vertical lines, using dots to
depict the connections to one or more vertices"; designed for dynamic hypergraphs of 50–500 vertices,
evaluated with 9 participants ([Valdivia, Buono, Plaisant, Dufournaud, Fekete, 2021](https://doi.org/10.1109/TVCG.2019.2933196)).
It is a transposed, time-ordered incidence matrix and is *the* reference encoding for temporal KHGs;
see [dynamic-and-temporal-hypergraph-visualization.md](dynamic-and-temporal-hypergraph-visualization.md).

### 3.3 Linear diagrams and hoop diagrams

Linear diagrams draw each set as a horizontal line segment; overlaps in x mean intersection. Seven
crowdsourced studies (1,760 participants) established design principles, and earlier work found them
"superior to prominent set visualization techniques, namely Euler and Venn diagrams"
([Rodgers, Stapleton, Chapman, 2015](https://doi.org/10.1145/2810012);
[Chapman et al., 2014](https://doi.org/10.1007/978-3-662-44043-8_18)). Hoop diagrams are a recent
circular variant ([Rodgers et al., 2024](https://doi.org/10.1007/978-3-031-71291-3_31)).

---

## 4. Timeline and flow encodings

- **Storylines / HyperStorylines**: entities are horizontal lines over time; "each hyperedge/relationship
  is represented by a rectangle that intersects all the people that are part of it"; supports
  aggregation and nesting of entity types; outperformed PAOHVis for identifying and characterising
  relationships in a comparative study ([Peña-Araya et al., 2021/2022](https://doi.org/10.1177/14738716211045007)).
  HyperNetX ships `draw_incidence_storyline` with the same four elements (nodes as bending lines,
  edges as vertical rounded rectangles, incidences as circles, segments) (source checked 2026-09-19).
- **TimeSets**: stacked timeline with hyperedges encoded by colour; beat KelpFusion in accuracy and
  preference ([Nguyen et al., 2015](https://doi.org/10.1177/1473871615605347)).
- **Set Streams**: branching and merging streams (Sankey-like) for dynamic set membership, "several
  hundred elements" ([Agarwal & Beck, 2020](https://doi.org/10.1111/cgf.13988)).
- **Layered hypergraphs**: vertices assigned to layers (e.g., years), hyperedges spanning layers;
  six hypergraph→graph transformations for Sugiyama-style layout
  ([Di Bartolomeo et al., 2022](https://doi.org/10.1111/cgf.14538)).

---

## 5. 3D, multilayer and immersive

- Kapec visualised software artefacts as hypergraphs with a "force-directed 3D layout with spheres and
  directed links" ([Kapec, 2010](https://doi.org/10.1145/1925059.1925067), via
  [Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).
- XGI's `draw_multilayer` places "hyperedges/simplices of different orders on superimposed layers" in 3D
  (docs checked 2026-09-19).
- GraphXR/Kineviz renders property graphs in browser 2D/3D but has no hyperedge primitive (product
  page checked 2026-09-19).
- `[unverified]` We found no peer-reviewed VR/AR study dedicated to hypergraph reading; this is a gap
  (see README open questions).

---

## 6. Choosing an encoding: a quick decision table

| Situation | First choice | Why (evidence) |
|---|---|---|
| ≤ 10 hyperedges, communicate membership | Euler/hull overlay or polygon | subset standard is the "blackboard" convention; Euler-type readability studies exist ([Rodgers et al., 2012](https://doi.org/10.1109/TVCG.2011.143)) |
| Roles, direction, attributes on hyperedges | bipartite / extra node | lossless, `n` links per hyperedge ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)); maps to Neo4j's intermediate-node pattern |
| 50–500 vertices, time-stamped hyperedges | PAOH or HyperStorylines | user studies ([Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196); [Peña-Araya et al., 2022](https://doi.org/10.1177/14738716211045007)) |
| Hundreds+ of hyperedges, static | incidence matrix / UpSet / Hyper-Matrix | matrix approaches scale to "several hundred nodes and hyperedges" ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)) |
| Set systems where each element lies on few sets | MetroSets | best in a 3-system readability study ([Wallinger et al., 2021](https://doi.org/10.1109/TVCG.2021.3074615)) |
| Thousands of hyperedges, exploratory | polygon + structure-aware simplification, or aggregation | ([Oliver et al., 2024](https://doi.org/10.1109/TVCG.2023.3326599); [2025](https://doi.org/10.1109/TVCG.2024.3456367)) |

## Sources

- Mäkinen, E. "How to draw a hypergraph." International Journal of Computer Mathematics 34(3-4):177–185, 1990. https://doi.org/10.1080/00207169008803875
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 (short papers), pp. 81–85. DOI 10.1109/VIS49827.2021.9623305. https://arxiv.org/abs/2107.13936
- Alsallakh, B., Micallef, L., Aigner, W., Hauser, H., Miksch, S., Rodgers, P. "The State-of-the-Art of Set Visualization." Computer Graphics Forum 35(1):234–260, 2016. https://doi.org/10.1111/cgf.12722
- Zykov, A. A. "Hypergraphs." Russian Mathematical Surveys 29(6):89–156, 1974. https://doi.org/10.1070/RM1974v029n06ABEH001303
- Ouvrard, X., Le Goff, J.-M., Marchand-Maillet, S. "Networks of Collaborations: Hypergraph Modeling and Visualisation." arXiv:1707.00115, 2017. https://arxiv.org/abs/1707.00115
- Paquette, J., Tokuyasu, T. "Hypergraph visualization and enrichment statistics: how the EGAN paradigm facilitates organic discovery from big data." Proc. SPIE 7865, 2011. https://doi.org/10.1117/12.890220
- Di Bartolomeo, S., Pister, A., Buono, P., Plaisant, C., Dunne, C., Fekete, J.-D. "Six methods for transforming layered hypergraphs to apply layered graph layout algorithms." Computer Graphics Forum 41(3) (EuroVis 2022). https://doi.org/10.1111/cgf.14538
- Xiong, Z., Mu, R., Yang, C., Xie, W., Lu, Q. "How Hypergraph-to-Graph Conversion Affects Cooperative Working Visualization: A Multi-metric Evaluation." CCIS, Springer, 2024, pp. 208–221. https://doi.org/10.1007/978-981-99-9637-7_15
- Bertault, F., Eades, P. "Drawing Hypergraphs in the Subset Standard (Short Demo Paper)." Graph Drawing 2000, LNCS 1984. https://doi.org/10.1007/3-540-44541-2_15
- Alper, B., Riche, N., Ramos, G., Czerwinski, M. "Design Study of LineSets, a Novel Set Visualization Technique." IEEE TVCG 17(12):2259–2267, 2011. https://doi.org/10.1109/TVCG.2011.186
- Dinkla, K., van Kreveld, M., Speckmann, B., Westenberg, M. "Kelp Diagrams: Point Set Membership Visualization." Computer Graphics Forum 31(3):875–884, 2012. https://doi.org/10.1111/j.1467-8659.2012.03080.x
- Meulemans, W., Riche, N. H., Speckmann, B., Alper, B., Dwyer, T. "KelpFusion: A Hybrid Set Visualization Technique." IEEE TVCG 19(11):1846–1858, 2013. https://doi.org/10.1109/TVCG.2013.76
- Dobler, A., Kobourov, S., Mondal, D., Nöllenburg, M. "Representing Hypergraphs by Point-Line Incidences." Graph Drawing 2024, LNCS, pp. 241–254, 2025. https://doi.org/10.1007/978-3-031-82670-2_18 ; journal version DMTCS 28:3, 2026. https://doi.org/10.46298/dmtcs.15876
- Jacobsen, B., Wallinger, M., Kobourov, S., Nöllenburg, M. "MetroSets: Visualizing Sets as Metro Maps." IEEE TVCG 27(2):1257–1267, 2021. https://doi.org/10.1109/TVCG.2020.3030475
- Wallinger, M., Jacobsen, B., Kobourov, S., Nöllenburg, M. "On the Readability of Abstract Set Visualizations." IEEE TVCG 27(6):2821–2832, 2021. https://doi.org/10.1109/TVCG.2021.3074615
- Cornelsen, S., Förster, H., Gupta, S., Kobourov, S., Zink, J. "Hypergraphs as Metro Maps: Drawing Paths with Few Bends in Trees, Cacti, and Plane 4-Graphs." arXiv:2511.22508, 2025. https://arxiv.org/abs/2511.22508
- Kerren, A., Jusufi, I. "A Novel Radial Visualization Approach for Undirected Hypergraphs." EuroVis Short Papers, 2013. https://doi.org/10.2312/PE.EuroVisShort.EuroVisShort2013.025-029
- Alsallakh, B., Aigner, W., Miksch, S., Hauser, H. "Radial Sets: Interactive Visual Analysis of Large Overlapping Sets." IEEE TVCG 19(12):2496–2505, 2013. https://doi.org/10.1109/TVCG.2013.184
- Nafar, M., Azami Zenouzagh, H. "Mixed coordinate Node link Visualization for Co-authorship Hypergraph Networks." arXiv:2310.19640, 2023. https://arxiv.org/abs/2310.19640
- Rodgers, P. "A survey of Euler diagrams." Journal of Visual Languages & Computing 25(3):134–155, 2014. https://doi.org/10.1016/j.jvlc.2013.08.006
- Simonetto, P., Auber, D., Archambault, D. "Fully Automatic Visualisation of Overlapping Sets." Computer Graphics Forum 28(3):967–974, 2009. https://doi.org/10.1111/j.1467-8659.2009.01452.x
- Kehlbeck, R., Görtler, J., Wang, Y., Deussen, O. "SpEuler: Semantics-preserving Euler Diagrams." IEEE TVCG, 2021. DOI 10.1109/TVCG.2021.3114834. https://arxiv.org/abs/2108.03529
- Micallef, L., Rodgers, P. "eulerAPE: Drawing Area-Proportional 3-Venn Diagrams Using Ellipses." PLoS ONE 9(7):e101717, 2014. https://doi.org/10.1371/journal.pone.0101717
- Rodgers, P., Zhang, L., Purchase, H. "Wellformedness Properties in Euler Diagrams: Which Should Be Used?" IEEE TVCG 18(7):1089–1100, 2012. https://doi.org/10.1109/TVCG.2011.143
- Johnson, D. S., Pollak, H. O. "Hypergraph planarity and the complexity of drawing Venn diagrams." Journal of Graph Theory 11(3):309–325, 1987. https://doi.org/10.1002/jgt.3190110306
- Bergmann, R. "Drawing hypergraphs using NURBS curves." Talk slides, University of Lübeck, 25 Nov 2009. https://ronnybergmann.net/talks/2010-Diplomvortrag.pdf
- Collins, C., Penn, G., Carpendale, S. "Bubble Sets: Revealing Set Relations with Isocontours over Existing Visualizations." IEEE TVCG 15(6):1009–1016, 2009. https://doi.org/10.1109/TVCG.2009.122
- Wang, Y., Cheng, D., Wang, Z., Zhang, J., Zhou, L., He, G., Deussen, O. "F2-Bubbles: Faithful Bubble Set Construction and Flexible Editing." IEEE TVCG, 2021. https://doi.org/10.1109/TVCG.2021.3114761
- HyperNetX drawing sources: `hypernetx/drawing/rubber_band.py`, `two_column.py`, `draw_storyline.py`, `draw_bipartite.py`. https://github.com/pnnl/HyperNetX (checked 2026-09-19)
- XGI drawing sources and docs: `xgi/drawing/draw.py`; https://xgi.readthedocs.io/en/stable/api/drawing/xgi.drawing.draw.html (checked 2026-09-19)
- hypergraphx viz sources: `hypergraphx/viz/`. https://github.com/HGX-Team/hypergraphx (checked 2026-09-19)
- Qu, B., Zhang, E., Zhang, Y. "Automatic Polygon Layout for Primal-Dual Visualization of Hypergraphs." IEEE TVCG 28(1):633–642, 2022. https://doi.org/10.1109/TVCG.2021.3114759
- Oliver, P., Zhang, E., Zhang, Y. "Scalable Hypergraph Visualization." IEEE TVCG 30(1):595–605, 2024. https://doi.org/10.1109/TVCG.2023.3326599 ; https://arxiv.org/abs/2308.05043
- Oliver, P., Zhang, E., Zhang, Y. "Structure-Aware Simplification for Hypergraph Visualization." IEEE TVCG 31(1):667–676, 2025. https://doi.org/10.1109/TVCG.2024.3456367
- HGPolyVis. https://github.com/peterdanieloliver/HGPolyVis (checked 2026-09-19)
- Kaufmann, M., van Kreveld, M., Speckmann, B. "Subdivision Drawings of Hypergraphs." Graph Drawing 2008, LNCS 5417, pp. 396–407, 2009. https://doi.org/10.1007/978-3-642-00219-9_39
- Buchin, K., van Kreveld, M., Meijer, H., Speckmann, B., Verbeek, K. "On Planar Supports for Hypergraphs." Journal of Graph Algorithms and Applications 15(4):533–549, 2011. https://doi.org/10.7155/jgaa.00237
- van Bevern, R., Kanj, I., Komusiewicz, C., Niedermeier, R., Sorge, M. "Twins in Subdivision Drawings of Hypergraphs." Graph Drawing 2016, LNCS, pp. 67–80. https://doi.org/10.1007/978-3-319-50106-2_6
- Jin, R., Xiang, Y., Fuhry, D., Dragan, F. F. "Overlapping Matrix Pattern Visualization: A Hypergraph Approach." IEEE ICDM 2008, pp. 313–322. https://doi.org/10.1109/ICDM.2008.102
- Lex, A., Gehlenborg, N., Strobelt, H., Vuillemot, R., Pfister, H. "UpSet: Visualization of Intersecting Sets." IEEE TVCG 20(12):1983–1992, 2014. https://doi.org/10.1109/TVCG.2014.2346248
- Fischer, M. T., Arya, D., Streeb, D., Seebacher, D., Keim, D. A., Worring, M. "Visual Analytics for Temporal Hypergraph Model Exploration." IEEE TVCG, 2020. https://doi.org/10.1109/TVCG.2020.3030408 ; https://arxiv.org/abs/2008.07299
- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Analyzing Dynamic Hypergraphs with Parallel Aggregated Ordered Hypergraph Visualization." IEEE TVCG 27(1):1–13, 2021. https://doi.org/10.1109/TVCG.2019.2933196
- Rodgers, P., Stapleton, G., Chapman, P. "Visualizing Sets with Linear Diagrams." ACM TOCHI 22(6):1–39, 2015. https://doi.org/10.1145/2810012
- Chapman, P., Stapleton, G., Rodgers, P., Micallef, L., Blake, A. "Visualizing Sets: An Empirical Comparison of Diagram Types." Diagrams 2014, LNCS, pp. 146–160. https://doi.org/10.1007/978-3-662-44043-8_18
- Rodgers, P., Chapman, P., Blake, A., Nöllenburg, M., Wallinger, M., Dobler, A. "Hoop Diagrams: A Set Visualization Method." Diagrams 2024, LNCS, pp. 377–392. https://doi.org/10.1007/978-3-031-71291-3_31
- Peña-Araya, V., Xue, T., Pietriga, E., Amsaleg, L., Bezerianos, A. "HyperStorylines: Interactively untangling dynamic hypergraphs." Information Visualization (online 2021; vol. 2022). https://doi.org/10.1177/14738716211045007
- Nguyen, P. H., Xu, K., Walker, R., Wong, B. L. W. "TimeSets: Timeline visualization with set relations." Information Visualization 15(3):253–269, 2015/2016. https://doi.org/10.1177/1473871615605347
- Agarwal, S., Beck, F. "Set Streams: Visual Exploration of Dynamic Overlapping Sets." Computer Graphics Forum 39(3):383–391, 2020. https://doi.org/10.1111/cgf.13988
- Kapec, P. "Visualizing software artifacts using hypergraphs." SCCG 2010. https://doi.org/10.1145/1925059.1925067
- Kineviz GraphXR product page. https://www.kineviz.com/graphxr (checked 2026-09-19)
