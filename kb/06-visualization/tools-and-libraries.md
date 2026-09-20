---
title: Tools and libraries for drawing hypergraphs and knowledge hypergraphs
type: tool
status: draft
tags: [hypergraph, visualization, tools, libraries, hypernetx, xgi, hypergraphx, d3, neo4j, typedb]
created: 2026-09-20
updated: 2026-09-20
---

# Tools and libraries for drawing hypergraphs and knowledge hypergraphs

Every version and date in this note was **checked on 2026-09-20**, from PyPI's JSON API, the npm
registry, CRAN's database, CTAN's package API, the Julia General registry, or the project's own
pages. Where a field could not be confirmed it says so. Runnable examples for the top three Python
entries are in [visualization-cookbook-for-this-kb.md](visualization-cookbook-for-this-kb.md).

Encoding abbreviations follow [visual-encodings-catalogue.md](visual-encodings-catalogue.md):
**hull** = padded convex hull / rubber band, **euler** = Euler or Euler-like region,
**bip** = bipartite / incidence / extra-node, **clique** = 2-section projection,
**matrix** = incidence matrix or UpSet, **PAOH** = parallel aggregated ordered hypergraph,
**story** = storyline, **simplex** = filled simplices, **metro** = metro map,
**poly** = polygon metaphor.

---

## 1. Native hypergraph libraries

| Tool | Language | Encodings | Interactivity | Scale (practical) | Licence | Latest version / date checked |
|---|---|---|---|---|---|---|
| **[HyperNetX](https://github.com/pnnl/HyperNetX)** | Python (matplotlib, NetworkX, scipy) | hull (`draw`), bip two-column (`two_column.draw`), euler-ish bip (`draw_bipartite_using_euler`), matrix/UpSet (`draw_incidence_upset`), story (`draw_incidence_storyline`), temporal incidence & line graph | static figures; interactive via `hnxwidget` | tens of hyperedges for hull; hundreds for the matrix view | 3-clause BSD | **2.4.3**, PyPI 2026-07-23 |
| **[hypernetx-widget](https://github.com/pnnl/hypernetx-widget)** (`hnxwidget`) | Python + JavaScript, Jupyter widget | euler (nodes as circles inside hyperedge outlines), bip (hyperedges as squares) | drag, select, hide, collapse, recolour in-notebook | small–medium; demo at <https://pnnl.github.io/hypernetx-widget/> | `[unverified]` — repo carries a Battelle/DOE disclaimer | **0.1.1b3**, PyPI 2023-05-09 (beta; no release since) |
| **[XGI](https://github.com/xgi-org/xgi)** | Python (matplotlib) | hull (`draw(..., hull=True)`), simplex (`draw_simplices`), bip (`draw_bipartite`, incl. **directed** tail→head arrows), multilayer 3D (`draw_multilayer`), node/hyperedge label layers | static; `xgi-panel`-style apps are external | hundreds of nodes before hull clutter | 3-clause BSD | **0.10.2**, PyPI 2026-05-15 |
| **[hypergraphx](https://github.com/HGX-Team/hypergraphx)** (HGX) | Python (matplotlib) | hull (`draw_hypergraph`), clique (`draw_clique`), bip (`draw_bipartite`), simplex (`draw_simplicial`), community overlays (`draw_communities`), motifs, multilayer projection | static | tens–hundreds | BSD-3-Clause | **1.8.0**, PyPI 2026-05-18 |
| **[SimpleHypergraphs.jl](https://github.com/pszufe/SimpleHypergraphs.jl)** | Julia (+ D3 and Python bridges) | hyperedges as sub-graphs (EGAN-style bip) and a convex-hull/Venn-like view | "some limited interactivity" ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)) | low–medium | MIT | **0.4.0**, latest in the Julia General registry |
| **[HAT-VIS](https://doi.org/10.1016/j.softx.2024.101963)** | MATLAB | `[unverified]` | `[unverified]` | `[unverified]` | `[unverified]` (SoftwareX articles are CC-BY; code licence not confirmed) | SoftwareX 28:101963, 2024 |
| **[HyperGodot](https://doi.org/10.1016/j.softx.2025.102315)** | `[unverified]` (name suggests the Godot engine) | `[unverified]` | described as interactive | `[unverified]` | `[unverified]` | SoftwareX 31:102315, 2025 |
| **[HGPolyVis](https://github.com/peterdanieloliver/HGPolyVis)** | C++/desktop (Windows) | poly (primal–dual polygon metaphor) with structure-aware simplification | desktop application | "thousands of hyperedges" ([Oliver, Zhang & Zhang, 2024](https://doi.org/10.1109/TVCG.2023.3326599)) | Apache-2.0 | `[unverified]` release date |
| **[PAOHVis](https://gitlab.inria.fr/aviz/paohvis)** | Dart compiled to JavaScript, HTML Canvas (~5,000 lines) | PAOH | reordering, packing, filtering, time-flow comparison, role symbols | "hundreds of vertices … and thousands of hyperedges" ([Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196)) | `[unverified]` | demo <https://aviz.fr/paohvis/paoh.html>; project page checked 2026-09-20 |
| **[MetroSets](https://metrosets.ac.at)** | web (JavaScript) | metro | highlight, filter sets | ≤ ~10 sets, ~100 elements ([Wallinger et al., 2021](https://doi.org/10.1109/TVCG.2021.3074615)) | `[unverified]` | [Jacobsen et al., 2021](https://doi.org/10.1109/TVCG.2020.3030475); URL `[unverified]` |

---

## 2. General graph libraries used for the bipartite encoding

These have **no hyperedge primitive**. You build the incidence graph yourself (see
[knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md)).

| Tool | Language | What you get | Interactivity | Scale | Licence | Version / date checked |
|---|---|---|---|---|---|---|
| **[NetworkX](https://networkx.org/)** | Python | `networkx.algorithms.bipartite` + `bipartite_layout`, `spring_layout`; the layout engine under HyperNetX and XGI | none (matplotlib output) | 10³–10⁴ nodes before layout cost bites | BSD-3-Clause | **3.6.1**, PyPI 2025-12-08 |
| **[D3](https://d3js.org/)** | JavaScript | `d3-force` with two node classes; full control of shape, arrow and label channels | everything you write | ~10³ nodes in SVG; more with canvas | ISC | **7.9.0**, npm 2024-03-12 |
| **[Sigma.js](https://www.sigmajs.org/)** | JavaScript (WebGL) + graphology | WebGL rendering of large graphs; powers TypeDB Studio's visualiser | pan/zoom/hover/select | 10⁴–10⁵ nodes (WebGL) | MIT | **3.0.3**, npm 2026-04-30 (graphology 0.26.0, npm 2025-01-26) |
| **[Cytoscape.js](https://js.cytoscape.org/)** | JavaScript | compound nodes are described as "a type of hypergraph", **but a node has at most one parent**, so overlapping hyperedges are impossible — use the bipartite encoding instead | rich (selection, layouts, events) | 10³–10⁴ | MIT | **3.34.3**, npm 2026-09-07 |
| **[vis-network](https://visjs.github.io/vis-network/)** | JavaScript | plain node-link; clustering built in | rich | 10³ | Apache-2.0 OR MIT | **10.1.2**, npm 2026-08-19 |
| **[Graphviz](https://graphviz.org/)** | C, DOT language | no hypergraph support in DOT: you emit an edge-node per hyperedge. Used this way by R's `hyperdraw` via Rgraphviz | none (static output) | 10³–10⁴ with `sfdp`/`neato` | EPL-1.0 (`[unverified]` — licence page not fetched) | **16.1.0** listed as current stable on graphviz.org/download |
| **[Gephi](https://gephi.org/)** | Java desktop | no hyperedge type; bipartite encoding with a node attribute; strong layout and filtering | rich desktop GUI | 10⁵ nodes claimed for the layout engine `[unverified]` | GPL | 0.11 announced in beta as of April 2026; **Gephi Lite 1.0** released October 2025 |
| **[Tulip](https://tulip.labri.fr/)** | C++ / Python (`tulip-python`) | implements the Simonetto–Auber–Archambault Euler-like overlapping-set algorithm ([Simonetto et al., 2009](https://doi.org/10.1111/j.1467-8659.2009.01452.x)) | desktop GUI + scripting | 10⁵ nodes claimed historically `[unverified]` | LGPL `[unverified]` | binaries up to **6.0.1** on SourceForge; `tulip-python` **6.0.0**, PyPI 2024-12-09; now "primarily distributed through its source code repository" |
| **[yFiles](https://www.yfiles.com/)** | JS/TS, Java, .NET | commercial layout SDK. yWorks state plainly for the editor: "yEd does not support hyperedges (neither does it support ports at ports)" ([yEd Q&A, 29 Jan 2013](https://yed.yworks.com/support/qa/2306/hyperedge-support-by-yed)) | rich | large, with LOD built in | commercial | `[unverified]` version; hyperedge status per the 2013 statement |

---

## 3. Knowledge-graph platforms

| Tool | What it renders | n-ary handling | Interactivity | Licence | Version / date checked |
|---|---|---|---|---|---|
| **[TypeDB Studio](https://typedb.com/)** | entities as rounded rectangles, relations as **diamonds**, attributes as ovals, **role labels on every edge** | native n-ary relations; a relation can play a role in another relation | search, expand, size-by-connectivity, type inheritance for visual grouping | commercial + community editions `[unverified]` | blog post "Seeing the schema", 7 May 2026; product version `[unverified]` |
| **[Neo4j Bloom](https://neo4j.com/product/bloom/)** | property graph node-link; "high performance, GPU-powered physics and rendering", Perspectives, scene saving, in-place editing | none — you model an intermediate node ([Neo4j modeling designs](https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/)) | rich, near-natural-language search | proprietary, bundled with AuraDB | Bloom user guide "current", checked 2026-09-20 |
| **[Neo4j Visualization Library (NVL)](https://neo4j.com/docs/nvl/current/)** | the renderer under Bloom and Explore | as above | library-level | see package licence file | `@neo4j-nvl/base` **2.0.0**, npm 2026-09-15 |
| **[Neo4j Browser](https://neo4j.com/docs/browser-manual/current/)** | Cypher shell with a node-link result view | as above | basic | open source | bundled with Neo4j |
| **[GraphXR / Kineviz](https://www.kineviz.com/graphxr)** | browser 2D **and 3D** graph, geospatial and time-series views; fuses Neo4j, relational, CSV/JSON and APIs | none native; reified nodes | iterative exploration, analytics (paths, centrality, communities) | commercial (on-prem, private cloud, air-gapped) | product page checked 2026-09-20 |
| **[Ontotext GraphDB](https://graphdb.ontotext.com/)** "Visual graph" | RDF resources as nodes, predicates as edges, expand/collapse from a start resource | RDF reification / RDF-star statements are resources, so they appear as nodes | expand, collapse, filter, graph config | commercial, with a free edition | `[unverified]` — documentation page could not be fetched on 2026-09-20 |
| **[metaphactory](https://www.metaphacts.com/product)** | "interactive graphs, carousels, interactive tables, maps, charts, tree renderings and timelines" | `[unverified]`; standard RDF/OWL/SHACL stack | rich, configurable components | commercial | **6.0**, announced 2026-07-14 |
| **[KGTK](https://github.com/usc-isi-i2/kgtk)** | `visualize-graph` writes a self-contained HTML force-directed view `[unverified]`; the KGTK Browser is a separate app | qualifiers via named edge ids reused in `node1` position, so "edges themselves can be the subject of other edges" ([KGTK specification](https://kgtk.readthedocs.io/en/latest/specification/)) | browser-level | MIT | **1.5.4**, PyPI 2023-06-29 (no release since) |

---

## 4. R

| Package | Source | What it does | Licence | Version / date checked |
|---|---|---|---|---|
| **HyperG** | CRAN | hypergraph data structures in R, built on igraph `[unverified: drawing capability not confirmed]` | GPL (>= 2) | **1.0.0**, published 2021-03-04 |
| **rhype** | CRAN | "Work with Hypergraphs in R" | GPL (>= 3) | **0.3.0**, published 2022-08-06 |
| **hypergraph** | Bioconductor | hypergraph classes incl. `DirectedHyperedge` | `[unverified]` | dependency of `hyperdraw` |
| **hyperdraw** | Bioconductor | the most concrete **directed** hyperedge renderer found: converts a `Hypergraph` into a bipartite `graphBPH`, lays it out with Rgraphviz, draws arrows; `arrowLoc` places arrowheads at the edge-node, the start or the end | GPL (>= 2) | **1.64.0**; vignette dated 28 April 2026; maintainer Paul Murrell |
| **UpSetR** | CRAN | UpSet plots for set intersections | MIT + file LICENSE | **1.4.1**, published 2026-05-25 |
| **ggupset** | CRAN | UpSet-style combination-matrix axis for ggplot2 | GPL-3 | **0.4.1**, published 2025-02-11 |

## 5. Python set-visualisation helpers

| Package | What it does | Licence | Version / date checked |
|---|---|---|---|
| **upsetplot** | "Draw Lex et al.'s UpSet plots with Pandas and Matplotlib" | BSD-3-Clause | **0.9.0**, PyPI 2023-12-31 |
| **matplotlib-venn** | area-proportional 2- and 3-set Venn diagrams | MIT | **1.1.2**, PyPI 2025-02-25 |
| **venn** | Venn diagrams for 2–6 sets | GPLv3 | **0.1.3**, PyPI 2018-09-12 (unmaintained) |

## 6. LaTeX / TikZ

No CTAN package draws hypergraphs as such (CTAN package search for "hypergraph" returned no matches,
checked 2026-09-20). What exists:

| Package | What it does | Licence | Version / date (CTAN) |
|---|---|---|---|
| **[venndiagram](https://ctan.org/pkg/venndiagram)** | "Creating Venn diagrams with TikZ" | LPPL 1.3 | **1.2**, 2018-06-07 |
| **[tikz-network](https://ctan.org/pkg/tikz-network)** | "Draw networks with TikZ" — the practical route: emit the incidence graph, give fact nodes a distinct style | GPL 3+ | **1.1**, 2019-08-15 |
| **[pst-venn](https://ctan.org/pkg/pst-venn)** | Venn sets with PSTricks | `[unverified]` | `[unverified]` |
| **venn** (MetaPost) | Venn diagrams in MetaPost | `[unverified]` | `[unverified]` |

For a subset-standard figure in a paper, plain TikZ works well: place nodes, then
`\draw plot[smooth cycle]` or the `fit` library with rounded corners around each hyperedge's nodes.
For the recommended incidence encoding, `tikz-network` plus two node styles is enough.

---

## 7. Choosing

| You want | Use |
|---|---|
| a quick figure of ≤ 30 facts, in Python | HyperNetX `hnx.draw` or XGI `draw(..., hull=True)` |
| directed n-ary facts (tail → head) | XGI `DiHypergraph` + `draw_bipartite`, or R `hyperdraw` |
| an interactive notebook view | `hnxwidget` (beta; last release 2023) |
| time-stamped facts | PAOHVis, or the matplotlib recipe in the cookbook |
| a production web UI over a KHG | Sigma.js or Cytoscape.js over the incidence graph; TypeDB Studio if the store is TypeDB |
| thousands of hyperedges, desktop | HGPolyVis |
| publication-quality LaTeX | TikZ / tikz-network on the incidence graph |
| set-intersection analytics rather than structure | UpSet (`upsetplot`, `UpSetR`) — see [set-visualization-connection.md](set-visualization-connection.md) |

**Gaps worth naming.** There is no maintained, interactive, web-native hypergraph viewer with
first-class role labels and directed hyperedges: HyperNetX's widget is a 2023 beta, PAOHVis is a
research prototype, and the only polished role-aware viewer (TypeDB Studio) is tied to one database.
Fischer et al.'s observation that there is "no established benchmark dataset for hypergraph
visualizations, no established performance metrics"
([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)) still describes the tool landscape too.

## Sources

- HyperNetX. PyPI metadata (v2.4.3, upload 2026-07-23) and installed source inspected 2026-09-20. https://github.com/pnnl/HyperNetX ; https://pypi.org/project/hypernetx/
- hypernetx-widget / `hnxwidget`. Repository and PyPI metadata (v0.1.1b3, upload 2023-05-09), checked 2026-09-20. https://github.com/pnnl/hypernetx-widget ; demo https://pnnl.github.io/hypernetx-widget/
- XGI. PyPI metadata (v0.10.2, upload 2026-05-15) and installed source `xgi/drawing/draw.py` inspected 2026-09-20. https://github.com/xgi-org/xgi
- hypergraphx (HGX). PyPI metadata (v1.8.0, upload 2026-05-18) and installed `hypergraphx/viz/` inspected 2026-09-20. https://github.com/HGX-Team/hypergraphx
- Antelmi, A., Cordasco, G., Kamiński, B., Prałat, P., Scarano, V., Spagnuolo, C., Szufel, P. "Analyzing, Exploring, and Visualizing Complex Networks via Hypergraphs using SimpleHypergraphs.jl." Internet Mathematics, 2020. https://doi.org/10.24166/im.01.2020 ; registry version 0.4.0, Julia General registry, checked 2026-09-20. https://github.com/pszufe/SimpleHypergraphs.jl
- Czvetkó, T., Abonyi, J. "Version [1.0] - HAT-VIS — A MATLAB-based hypergraph visualization tool." SoftwareX 28:101963, 2024. https://doi.org/10.1016/j.softx.2024.101963
- Ficsor, A., Czvetko, T., Sebestyen, V., Abonyi, J. "HyperGodot: Interactive hypergraph visualization tool." SoftwareX 31:102315, 2025. https://doi.org/10.1016/j.softx.2025.102315
- Oliver, P., Zhang, E., Zhang, Y. "Scalable Hypergraph Visualization." IEEE TVCG 30(1):595–605, 2024. https://doi.org/10.1109/TVCG.2023.3326599 ; HGPolyVis https://github.com/peterdanieloliver/HGPolyVis
- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Analyzing Dynamic Hypergraphs with Parallel Aggregated Ordered Hypergraph Visualization." IEEE TVCG 27(1):1–13, 2021. https://doi.org/10.1109/TVCG.2019.2933196 ; PAOHVis https://www.aviz.fr/Research/paohvis (checked 2026-09-20)
- Jacobsen, B., Wallinger, M., Kobourov, S., Nöllenburg, M. "MetroSets: Visualizing Sets as Metro Maps." IEEE TVCG 27(2):1257–1267, 2021. https://doi.org/10.1109/TVCG.2020.3030475
- Wallinger, M., Jacobsen, B., Kobourov, S., Nöllenburg, M. "On the Readability of Abstract Set Visualizations." IEEE TVCG 27(6):2821–2832, 2021. https://doi.org/10.1109/TVCG.2021.3074615
- NetworkX. PyPI metadata (v3.6.1, upload 2025-12-08), checked 2026-09-20. https://networkx.org/
- D3 (v7.9.0, npm 2024-03-12), Sigma.js (v3.0.3, npm 2026-04-30), graphology (v0.26.0, npm 2025-01-26), Cytoscape.js (v3.34.3, npm 2026-09-07), vis-network (v10.1.2, npm 2026-08-19), `@neo4j-nvl/base` (v2.0.0, npm 2026-09-15). npm registry, checked 2026-09-20.
- Cytoscape.js documentation (compound nodes; a node's parent is single and normally immutable), checked 2026-09-20. https://js.cytoscape.org/
- Graphviz download page (current stable 16.1.0), checked 2026-09-20. https://graphviz.org/download/
- Gephi project site (0.11 beta announced April 2026; Gephi Lite 1.0, October 2025), checked 2026-09-20. https://gephi.org/
- Tulip project site and `tulip-python` PyPI metadata (v6.0.0, upload 2024-12-09), checked 2026-09-20. https://tulip.labri.fr/
- Simonetto, P., Auber, D., Archambault, D. "Fully Automatic Visualisation of Overlapping Sets." Computer Graphics Forum 28(3):967–974, 2009. https://doi.org/10.1111/j.1467-8659.2009.01452.x
- yWorks. "Hyperedge support by yEd", yEd Q&A, 29 January 2013, checked 2026-09-20. https://yed.yworks.com/support/qa/2306/hyperedge-support-by-yed
- TypeDB. "Seeing the schema: TypeDB's approach to graph visualization", 7 May 2026, checked 2026-09-20. https://typedb.com/blog/graph-visualisation-for-hypergraphs
- Neo4j. "About Neo4j Bloom", "Modeling designs" and "Visualize your data in Neo4j", checked 2026-09-20. https://neo4j.com/docs/bloom-user-guide/current/about-bloom/ ; https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/ ; https://neo4j.com/docs/getting-started/graph-visualization/graph-visualization/
- Kineviz GraphXR product page, checked 2026-09-20. https://www.kineviz.com/graphxr
- metaphacts. metaphactory product page (v6.0 announced 2026-07-14), checked 2026-09-20. https://www.metaphacts.com/product
- KGTK. PyPI metadata (v1.5.4, upload 2023-06-29) and file specification, checked 2026-09-20. https://github.com/usc-isi-i2/kgtk ; https://kgtk.readthedocs.io/en/latest/specification/
- CRAN package database (`crandb.r-pkg.org`) for HyperG 1.0.0 (2021-03-04), rhype 0.3.0 (2022-08-06), UpSetR 1.4.1 (2026-05-25), ggupset 0.4.1 (2025-02-11), checked 2026-09-20.
- Murrell, P. hyperdraw 1.64.0, Bioconductor; vignette dated 28 April 2026, checked 2026-09-20. https://www.bioconductor.org/packages/release/bioc/html/hyperdraw.html
- PyPI metadata for `upsetplot` 0.9.0 (2023-12-31), `matplotlib-venn` 1.1.2 (2025-02-25), `venn` 0.1.3 (2018-09-12), checked 2026-09-20.
- CTAN package API for `venndiagram` 1.2 (2018-06-07, LPPL 1.3), `tikz-network` 1.1 (2019-08-15, GPL 3+), `pst-venn`, `venn`; search for "hypergraph" returned no packages. Checked 2026-09-20. https://ctan.org/
- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 short papers. https://arxiv.org/abs/2107.13936
