---
title: Large-scale and interactive exploration of knowledge hypergraphs
type: survey
status: draft
tags: [hypergraph, visualization, scalability, level-of-detail, aggregation, simplification, focus-context, embeddings, GPU, query-driven]
created: 2026-09-20
updated: 2026-09-20
---

# Large-scale and interactive exploration of knowledge hypergraphs

Every static encoding in [visual-encodings-catalogue.md](visual-encodings-catalogue.md) runs out
somewhere between a few dozen and a few thousand hyperedges
([perception-and-evaluation-studies.md](perception-and-evaluation-studies.md), §7). A knowledge
hypergraph built by an LLM pipeline is routinely an order of magnitude past that: HyperGraphRAG
reports **26,902 hyperedges over 19,913 entities** for its computer-science corpus alone
([Luo, E, Chen, Zheng, Wu, Guo, Lin et al., 2025](https://arxiv.org/abs/2503.21322)). At that size a
single global picture is a rhetorical device, not an instrument.

This note collects the five strategies that buy scale, and what evidence exists for each.

> Fischer et al.'s assessment is still the baseline: even timeline and matrix representations "do not
> support more than around thousand entities. Solving these issues requires novel ideas like
> extra-nodes, aggregating and subsetting, as well as dense, domain-specific representations"
> ([Fischer, Frings, Keim & Seebacher, 2021](https://arxiv.org/abs/2107.13936)).

---

## 1. Simplification: fewer hyperedges, same structure

The most developed line of work. Reduce the hypergraph *before* drawing, under a guarantee about what
is preserved.

### 1.1 Topological simplification

Two dual operations, defined through line graphs and clique expansions and justified with tools from
topological data analysis ([Zhou, Rathore, Purvine & Wang, 2021](https://arxiv.org/abs/2104.11214)):

- **vertex simplification** — merge vertices "if they belong to almost the same set of hyperedges";
- **hyperedge simplification** — merge hyperedges "if they share almost the same set of vertices".

In KHG terms, vertex simplification merges entities that play the same role across the same facts
(closely related to entity resolution, see
[../03-construction/entity-resolution-and-canonicalisation.md](../03-construction/entity-resolution-and-canonicalisation.md)),
and hyperedge simplification merges near-duplicate facts. Both are *visual* operations here, but both
have data-quality interpretations — which is a warning as much as an opportunity: a simplified
picture can hide exactly the redundancy you wanted to find.

### 1.2 Structure-aware simplification of the polygon layout

The polygon metaphor "often suffers from excessive self-intersections when the input dataset is
relatively large" ([Oliver, Zhang & Zhang, 2024](https://arxiv.org/abs/2308.05043)). Two papers fix
this:

- **Scalable Hypergraph Visualization** — a set of atomic simplification operations applied
  iteratively under an operation-priority measure, with reverse refinement, scaling the polygon
  metaphor to thousands of hyperedges
  ([Oliver, Zhang & Zhang, 2024](https://doi.org/10.1109/TVCG.2023.3326599), IEEE TVCG 30(1):595–605).
- **Structure-Aware Simplification** — decomposes the bipartite representation into topological
  blocks, bridges and branches so that cycles survive simplification rather than being smoothed away
  ([Oliver, Zhang & Zhang, 2025](https://doi.org/10.1109/TVCG.2024.3456367), IEEE TVCG 31(1):667–676).

The second paper matters conceptually beyond its own technique: **it simplifies the bipartite
representation**, not the regions. The incidence graph is the right object to reduce, whatever you
finally draw.

### 1.3 Aggregation is closed

A structural property that makes level-of-detail safe for hypergraphs: "when aggregating multiple
vertices, they remain hypergraphs"
([Valdivia, Buono, Plaisant, Dufournaud & Fekete, 2021](https://doi.org/10.1109/TVCG.2019.2933196)).
You can roll entities up a type hierarchy, or facts up a predicate hierarchy, and the result is still
a hypergraph that every encoding in this section can draw. No other reduction in this note has that
guarantee for free.

---

## 2. Level of detail and semantic zoom

**Hyper-Matrix** is the reference design: a multi-level matrix with "drill-down capabilities across
multiple levels of semantic zoom, from an overview of model predictions down to the content", plus
matrix reordering, hierarchical grouping, and filtering
([Fischer, Arya, Streeb, Seebacher, Keim & Worring, 2021](https://doi.org/10.1109/TVCG.2020.3030408),
IEEE TVCG 27(2):550–560). The survey rates it and Set Streams in the 200–1000 band — the top of what
anything achieves ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

For a KHG the natural LOD ladder, coarsest first:

1. **schema level** — predicate types and entity types only (a few dozen nodes);
2. **aggregated level** — entities rolled up to type or cluster, facts rolled up to predicate,
   hyperedge weights = counts;
3. **neighbourhood level** — the k-hop incidence subgraph around a focus entity or fact;
4. **fact level** — individual facts with roles, arguments, qualifiers and provenance.

Levels 1 and 2 are *drawable*; levels 3 and 4 are *reachable only by query*. This is the practical
architecture, and it is what TypeDB Studio, Neo4j Bloom and GraphDB's visual graph all implement in
their own way ([tools-and-libraries.md](tools-and-libraries.md)).

---

## 3. Focus + context

The general graph literature is the source here: von Landesberger et al.'s state-of-the-art report on
large-graph visual analysis is the standard reference for navigation, aggregation and focus+context
in this size regime
([von Landesberger, Kuijper, Schreck, Kohlhammer, van Wijk, Fekete & Fellner, 2011](https://doi.org/10.1111/j.1467-8659.2011.01898.x),
CGF 30(6):1719–1749).

Hypergraph-specific adaptations that exist:

- **PAOH's drips** — degree-one vertices are hidden and reduced to "smaller gray dots at the lower end
  of hyperedges", so context survives without rows
  ([Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196)).
- **PAOH's hyperedge packing and repeated-edge collapsing** — identical hyperedges in a slot collapse
  into one thicker line up to a maximum width (ibid.).
- **Bubble Sets-style overlays** on a detail view, with the set marks providing the context layer
  ([Collins, Penn & Carpendale, 2009](https://doi.org/10.1109/TVCG.2009.122)) — see
  [set-visualization-connection.md](set-visualization-connection.md).
- **Multiscale Snapshots** for the temporal axis: visual analysis of temporal summaries rather than
  every time step ([Cakmak, Schlegel, Jäckle, Keim & Schreck, 2021](https://doi.org/10.1109/TVCG.2020.3030398),
  IEEE TVCG 27(2):517–527). Fischer et al. explicitly suggest exploring such "novel concepts in
  dynamic networks visualizations beyond animations" for hypergraphs
  ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

---

## 4. Embedding-based projections

Instead of laying out the hypergraph, **embed it and project the embedding**. For a KHG this is
attractive because embeddings already exist: n-ary fact embeddings and hypergraph neural network
representations are a research area in their own right (see
[../05-query-embeddings-reasoning/](../05-query-embeddings-reasoning/) when that section is written),
and retrieval systems compute them anyway — HyperGraphRAG "embed[s] hyperedges and entities using the
same embedding" into separate vector stores ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)).

Two projections are available and they answer different questions:

| Project | Point = | Proximity means | Overlay |
|---|---|---|---|
| entity embedding | an entity | entities appear in similar facts | hull/Bubble Sets per fact or predicate |
| **hyperedge (fact) embedding** | a fact | facts are semantically similar | colour by predicate; link facts sharing an entity |

The second is the *dual* view and is underused. It turns "explore 26,902 hyperedges" into "explore a
scatter plot of 26,902 points", where selection drives a detail panel. Interaction with dimensionality
reduction has its own structured literature
([Sacha, Zhang, Sedlmair, Lee, Peltonen, Weiskopf, North & Keim, 2017](https://doi.org/10.1109/TVCG.2016.2598495),
IEEE TVCG 23(1):241–250), which applies unchanged.

A concrete recent system in this family is the "spatial hypergraph representation" combined with
interactive grids and matrix views for image collections, reported to handle "tens of thousands of
images" ([Gisolf, Geradts & Worring, 2025](https://arxiv.org/abs/2510.20050)).

`[unverified]` This KB found no published study evaluating hyperedge-embedding projections against
hypergraph layouts for any task.

---

## 5. GPU and WebGL rendering

Rendering is rarely the first bottleneck — layout and human reading are — but it sets the ceiling
once the other two are solved.

- **Neo4j Bloom** advertises "high performance, GPU-powered physics and rendering"
  ([Neo4j Bloom user guide](https://neo4j.com/docs/bloom-user-guide/current/about-bloom/), checked
  2026-09-20); the underlying renderer, the Neo4j Visualization Library, is open source
  (`@neo4j-nvl/base` 2.0.0, npm 2026-09-15).
- **Sigma.js** renders with WebGL over graphology and is what TypeDB Studio's visualiser builds on
  (Sigma.js 3.0.3, npm 2026-04-30; see [tools-and-libraries.md](tools-and-libraries.md)).
- **PAOHVis** avoids SVG entirely: about 5,000 lines of Dart compiled to JavaScript drawing on the
  HTML Canvas API, which is what lets it hold thousands of hyperedges
  ([Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196)).
- **Kapec's 3D hypergraph view** is the early GPU-adjacent outlier — a force-directed 3D layout with
  spheres and directed links ([Kapec, 2010](https://doi.org/10.1145/1925059.1925067), as catalogued by
  [Fischer et al., 2021](https://arxiv.org/abs/2107.13936)), rated the most scalable of its
  contemporaries by the survey.

Practical rule: SVG to ~10³ marks, Canvas to ~10⁴–10⁵, WebGL beyond. The incidence encoding costs
`|V| + |E|` marks plus `Σ|e|` links, so a 20,000-hyperedge KHG is a WebGL problem even before layout.

---

## 6. Query-driven exploration — the strategy that actually works for KHGs

Every KHG platform in [tools-and-libraries.md](tools-and-libraries.md) reaches scale the same way:
**do not draw the graph; draw the answer to a query.**

- **HyperGraphRAG** retrieves by vector similarity over entity *and* hyperedge embeddings, then draws
  or feeds only the retrieved n-ary facts. Its own measurements show the retrieval saturates:
  performance "saturates around k = 60" retrieved hyperedges
  ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)). Sixty facts is a drawable subgraph. This is
  the strongest available evidence that query-driven views are not merely a workaround: the useful
  neighbourhood is small.
- **Neo4j Bloom** uses near-natural-language search to define a scene, then expands from it
  ([Neo4j](https://neo4j.com/docs/bloom-user-guide/current/about-bloom/)).
- **TypeDB Studio** starts from a query result and expands by role
  ([TypeDB, 2026](https://typedb.com/blog/graph-visualisation-for-hypergraphs)).
- **GraphDB's visual graph** expands outward from a chosen resource.
- **PAOHVis** filters vertices and hyperedges, then reorders
  ([Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196)).

The design consequence: a KHG viewer's most important component is not its layout engine, it is its
**selection language** — the thing that turns 10⁴ facts into 60.

---

## 7. A concrete pipeline for this KB

```
  KHG (10^4–10^6 facts)
        │
        ├─ [1] schema view          predicate types × entity types        ~10^1 nodes, any encoding
        │
        ├─ [2] fact-embedding map   2D projection of hyperedge vectors    10^4 points, WebGL scatter
        │        └─ brush ──────────────┐
        │                               │
        ├─ [3] query / retrieval  ──────┤   top-k facts (k ≈ 20–60)
        │                               │
        └─ [4] incidence drawing  ◀─────┘   role labels, arrowheads, fact nodes
                 │                          (the recommended encoding)
                 └─ [5] PAOH panel          if the selection is time-stamped
```

Steps 1, 3 and 4 are supported by published practice. Step 2 is the speculative one
(§4, `[unverified]`), and step 5 is the temporal view of
[dynamic-and-temporal-hypergraph-visualization.md](dynamic-and-temporal-hypergraph-visualization.md).

**Open problems in this area**, stated by the survey and still open as far as this KB can tell:
no benchmark dataset for hypergraph visualisation, no established performance metrics, and only a
limited discussion of specific tasks ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

## Sources

- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 short papers, pp. 81–85. https://arxiv.org/abs/2107.13936
- Fischer, M. T., Arya, D., Streeb, D., Seebacher, D., Keim, D. A., Worring, M. "Visual Analytics for Temporal Hypergraph Model Exploration." IEEE TVCG 27(2):550–560, 2021. https://doi.org/10.1109/TVCG.2020.3030408
- Zhou, Y., Rathore, A., Purvine, E., Wang, B. "Topological Simplifications of Hypergraphs." arXiv:2104.11214, 2021. https://arxiv.org/abs/2104.11214
- Oliver, P., Zhang, E., Zhang, Y. "Scalable Hypergraph Visualization." IEEE TVCG 30(1):595–605, 2024. https://doi.org/10.1109/TVCG.2023.3326599 ; https://arxiv.org/abs/2308.05043
- Oliver, P., Zhang, E., Zhang, Y. "Structure-Aware Simplification for Hypergraph Visualization." IEEE TVCG 31(1):667–676, 2025. https://doi.org/10.1109/TVCG.2024.3456367
- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Analyzing Dynamic Hypergraphs with Parallel Aggregated Ordered Hypergraph Visualization." IEEE TVCG 27(1):1–13, 2021. https://doi.org/10.1109/TVCG.2019.2933196
- von Landesberger, T., Kuijper, A., Schreck, T., Kohlhammer, J., van Wijk, J. J., Fekete, J.-D., Fellner, D. W. "Visual Analysis of Large Graphs: State-of-the-Art and Future Research Challenges." Computer Graphics Forum 30(6):1719–1749, 2011. https://doi.org/10.1111/j.1467-8659.2011.01898.x
- Cakmak, E., Schlegel, U., Jäckle, D., Keim, D. A., Schreck, T. "Multiscale Snapshots: Visual Analysis of Temporal Summaries in Dynamic Graphs." IEEE TVCG 27(2):517–527, 2021. https://doi.org/10.1109/TVCG.2020.3030398
- Sacha, D., Zhang, L., Sedlmair, M., Lee, J. A., Peltonen, J., Weiskopf, D., North, S. C., Keim, D. A. "Visual Interaction with Dimensionality Reduction: A Structured Literature Analysis." IEEE TVCG 23(1):241–250, 2017. https://doi.org/10.1109/TVCG.2016.2598495
- Gisolf, F., Geradts, Z. J. M. H., Worring, M. "Interactive Hypergraph Visual Analytics for Exploring Large and Complex Image Collections." arXiv:2510.20050, 2025. https://arxiv.org/abs/2510.20050
- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025. https://arxiv.org/abs/2503.21322
- Collins, C., Penn, G., Carpendale, S. "Bubble Sets: Revealing Set Relations with Isocontours over Existing Visualizations." IEEE TVCG 15(6):1009–1016, 2009. https://doi.org/10.1109/TVCG.2009.122
- Kapec, P. "Visualizing software artifacts using hypergraphs." SCCG 2010. https://doi.org/10.1145/1925059.1925067
- Neo4j. "About Neo4j Bloom", Bloom user guide, checked 2026-09-20. https://neo4j.com/docs/bloom-user-guide/current/about-bloom/
- TypeDB. "Seeing the schema: TypeDB's approach to graph visualization", 7 May 2026, checked 2026-09-20. https://typedb.com/blog/graph-visualisation-for-hypergraphs
- Sigma.js v3.0.3 (npm 2026-04-30) and `@neo4j-nvl/base` v2.0.0 (npm 2026-09-15), npm registry, checked 2026-09-20. https://www.sigmajs.org/
