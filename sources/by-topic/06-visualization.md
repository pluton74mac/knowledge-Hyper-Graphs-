# Sources — 06 Visualization

Bibliography for `kb/06-visualization/`. Compiled 2026-09-20. Grouped by topic; every entry is cited
from at least one note in the section. Entries marked `[unverified]` were identified from a
publisher listing, a search result, a tool page, or another paper's reference list, but the full text
or the specific field was not confirmed during this research run; the bibliographic fields are
reported as found. All DOIs listed under "Papers" were resolved against Crossref on 2026-09-20 unless
marked otherwise.

## Surveys and state-of-the-art reports

- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 (short papers), pp. 81–85. DOI 10.1109/VIS49827.2021.9623305. https://arxiv.org/abs/2107.13936 — *the only dedicated hypergraph-visualisation survey; 14 approaches, five scalability bands.*
- Alsallakh, B., Micallef, L., Aigner, W., Hauser, H., Miksch, S., Rodgers, P. "The State-of-the-Art of Set Visualization." Computer Graphics Forum 35(1):234–260, 2016 (EuroVis STAR version 2014). https://doi.org/10.1111/cgf.12722 — *six categories of representation, 26 tasks in three categories.*
- Rodgers, P. "A survey of Euler diagrams." Journal of Visual Languages & Computing 25(3):134–155, 2014. https://doi.org/10.1016/j.jvlc.2013.08.006
- Beck, F., Burch, M., Diehl, S., Weiskopf, D. "A Taxonomy and Survey of Dynamic Graph Visualization." Computer Graphics Forum 36(1):133–159, 2017. https://doi.org/10.1111/cgf.12791
- Vehlow, C., Beck, F., Weiskopf, D. "Visualizing Group Structures in Graphs: A Survey." Computer Graphics Forum 36(6):201–225, 2017. https://doi.org/10.1111/cgf.12872
- von Landesberger, T., Kuijper, A., Schreck, T., Kohlhammer, J., van Wijk, J. J., Fekete, J.-D., Fellner, D. W. "Visual Analysis of Large Graphs: State-of-the-Art and Future Research Challenges." Computer Graphics Forum 30(6):1719–1749, 2011. https://doi.org/10.1111/j.1467-8659.2011.01898.x
- Sacha, D., Zhang, L., Sedlmair, M., Lee, J. A., Peltonen, J., Weiskopf, D., North, S. C., Keim, D. A. "Visual Interaction with Dimensionality Reduction: A Structured Literature Analysis." IEEE TVCG 23(1):241–250, 2017. https://doi.org/10.1109/TVCG.2016.2598495
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014 — *section 11 covers drawing standards, the Zykov representation and PaintSplash.*

## Foundations of hypergraph drawing

- Mäkinen, E. "How to draw a hypergraph." International Journal of Computer Mathematics 34(3–4):177–185, 1990. https://doi.org/10.1080/00207169008803875 — *the subset/edge standard distinction.*
- Zykov, A. A. "Hypergraphs." Russian Mathematical Surveys 29(6):89–156, 1974. https://doi.org/10.1070/RM1974v029n06ABEH001303
- Bertault, F., Eades, P. "Drawing Hypergraphs in the Subset Standard (Short Demo Paper)." Graph Drawing 2000, LNCS 1984, pp. 164–169, 2001. https://doi.org/10.1007/3-540-44541-2_15 — *the PATATE system; incidence graph with dummy vertices, Euclidean spanning/Steiner trees inside the force loop.*
- Arafat, N. A., Bressan, S. "Hypergraph Drawing by Force-Directed Placement." DEXA 2017, LNCS 10439, pp. 387–394. https://doi.org/10.1007/978-3-319-64471-4_31 ; author copy https://toggled.github.io/naheed/assets/pdf/dexa17.pdf — *complete/cycle/star/wheel associated graphs; the Concavity, Planarity, Coverage and Regularity metrics.*
- Fruchterman, T. M. J., Reingold, E. M. "Graph Drawing by Force-Directed Placement." Software: Practice and Experience 21(11):1129–1164, 1991. https://doi.org/10.1002/spe.4380211102
- Bergmann, R. "Drawing hypergraphs using NURBS curves." Talk slides, University of Lübeck, 25 November 2009. https://ronnybergmann.net/talks/2010-Diplomvortrag.pdf

## Planarity, supports and complexity

- Johnson, D. S., Pollak, H. O. "Hypergraph planarity and the complexity of drawing Venn diagrams." Journal of Graph Theory 11(3):309–325, 1987. https://doi.org/10.1002/jgt.3190110306
- Kaufmann, M., van Kreveld, M., Speckmann, B. "Subdivision Drawings of Hypergraphs." Graph Drawing 2008, LNCS 5417, pp. 396–407, 2009. https://doi.org/10.1007/978-3-642-00219-9_39
- van Bevern, R., Kanj, I., Komusiewicz, C., Niedermeier, R., Sorge, M. "Twins in Subdivision Drawings of Hypergraphs." Graph Drawing 2016, LNCS 9801, pp. 67–80. https://doi.org/10.1007/978-3-319-50106-2_6
- Buchin, K., van Kreveld, M., Meijer, H., Speckmann, B., Verbeek, K. "On Planar Supports for Hypergraphs." Journal of Graph Algorithms and Applications 15(4):533–549, 2011. https://doi.org/10.7155/jgaa.00237
- Brandes, U., Cornelsen, S., Pampel, B., Sallaberry, A. "Path-Based Supports for Hypergraphs." IWOCA 2010, LNCS 6460, pp. 20–33, 2011. https://doi.org/10.1007/978-3-642-19222-7_3 ; journal version Journal of Discrete Algorithms 14:248–261, 2012, https://doi.org/10.1016/j.jda.2011.12.009 ; open copy https://kops.uni-konstanz.de/bitstreams/c1aea7f2-bc74-4f56-a387-6d833cd348a9/download — *the support-complexity landscape in its introduction.*
- Eschbach, T., Günther, W., Becker, B. "Orthogonal Hypergraph Drawing for Improved Visibility." Journal of Graph Algorithms and Applications 10(2):141–157, 2006. https://doi.org/10.7155/jgaa.00122
- Dobler, A., Kobourov, S., Mondal, D., Nöllenburg, M. "Representing Hypergraphs by Point-Line Incidences." Graph Drawing 2024, LNCS, pp. 241–254, 2025. https://doi.org/10.1007/978-3-031-82670-2_18 ; journal version DMTCS 28:3, 2026, https://doi.org/10.46298/dmtcs.15876
- Cornelsen, S., Förster, H., Gupta, S., Kobourov, S., Zink, J. "Hypergraphs as Metro Maps: Drawing Paths with Few Bends in Trees, Cacti, and Plane 4-Graphs." arXiv:2511.22508, 2025. https://arxiv.org/abs/2511.22508

## Euler diagrams and their generation

- Flower, J., Howse, J. "Generating Euler Diagrams." Diagrams 2002, LNAI 2317, pp. 61–75. https://doi.org/10.1007/3-540-46037-3_6
- Verroust, A., Viaud, M.-L. "Ensuring the Drawability of Extended Euler Diagrams for up to 8 Sets." Diagrams 2004, LNAI 2980, pp. 128–141. https://doi.org/10.1007/978-3-540-25931-2_13
- Simonetto, P., Auber, D., Archambault, D. "Fully Automatic Visualisation of Overlapping Sets." Computer Graphics Forum 28(3):967–974, 2009. https://doi.org/10.1111/j.1467-8659.2009.01452.x — *Euler-like diagrams with no undrawable instances; implemented in Tulip.*
- Kehlbeck, R., Görtler, J., Wang, Y., Deussen, O. "SpEuler: Semantics-preserving Euler Diagrams." IEEE TVCG, 2021. DOI 10.1109/TVCG.2021.3114834. https://arxiv.org/abs/2108.03529
- Micallef, L., Rodgers, P. "eulerAPE: Drawing Area-Proportional 3-Venn Diagrams Using Ellipses." PLoS ONE 9(7):e101717, 2014. https://doi.org/10.1371/journal.pone.0101717
- Rodgers, P., Zhang, L., Purchase, H. "Wellformedness Properties in Euler Diagrams: Which Should Be Used?" IEEE TVCG 18(7):1089–1100, 2012. https://doi.org/10.1109/TVCG.2011.143

## Set visualisation techniques

- Lex, A., Gehlenborg, N., Strobelt, H., Vuillemot, R., Pfister, H. "UpSet: Visualization of Intersecting Sets." IEEE TVCG 20(12):1983–1992, 2014. https://doi.org/10.1109/TVCG.2014.2346248
- Collins, C., Penn, G., Carpendale, S. "Bubble Sets: Revealing Set Relations with Isocontours over Existing Visualizations." IEEE TVCG 15(6):1009–1016, 2009. https://doi.org/10.1109/TVCG.2009.122
- Wang, Y., Cheng, D., Wang, Z., Zhang, J., Zhou, L., He, G., Deussen, O. "F2-Bubbles: Faithful Bubble Set Construction and Flexible Editing." IEEE TVCG, 2021. https://doi.org/10.1109/TVCG.2021.3114761
- Dinkla, K., van Kreveld, M., Speckmann, B., Westenberg, M. "Kelp Diagrams: Point Set Membership Visualization." Computer Graphics Forum 31(3):875–884, 2012. https://doi.org/10.1111/j.1467-8659.2012.03080.x
- Meulemans, W., Riche, N. H., Speckmann, B., Alper, B., Dwyer, T. "KelpFusion: A Hybrid Set Visualization Technique." IEEE TVCG 19(11):1846–1858, 2013. https://doi.org/10.1109/TVCG.2013.76
- Alper, B., Riche, N., Ramos, G., Czerwinski, M. "Design Study of LineSets, a Novel Set Visualization Technique." IEEE TVCG 17(12):2259–2267, 2011. https://doi.org/10.1109/TVCG.2011.186
- Alsallakh, B., Aigner, W., Miksch, S., Hauser, H. "Radial Sets: Interactive Visual Analysis of Large Overlapping Sets." IEEE TVCG 19(12):2496–2505, 2013. https://doi.org/10.1109/TVCG.2013.184
- Rodgers, P., Stapleton, G., Chapman, P. "Visualizing Sets with Linear Diagrams." ACM TOCHI 22(6):1–39, 2015. https://doi.org/10.1145/2810012
- Chapman, P., Stapleton, G., Rodgers, P., Micallef, L., Blake, A. "Visualizing Sets: An Empirical Comparison of Diagram Types." Diagrams 2014, LNCS 8578, pp. 146–160. https://doi.org/10.1007/978-3-662-44043-8_18
- Rodgers, P., Chapman, P., Blake, A., Nöllenburg, M., Wallinger, M., Dobler, A. "Hoop Diagrams: A Set Visualization Method." Diagrams 2024, LNCS, pp. 377–392. https://doi.org/10.1007/978-3-031-71291-3_31
- Jacobsen, B., Wallinger, M., Kobourov, S., Nöllenburg, M. "MetroSets: Visualizing Sets as Metro Maps." IEEE TVCG 27(2):1257–1267, 2021. https://doi.org/10.1109/TVCG.2020.3030475
- "SimpleSets: Capturing Categorical Point Patterns with Simple Shapes." arXiv:2407.14433, 2024. https://arxiv.org/abs/2407.14433 `[unverified: authors and venue not confirmed]`
- "Visualizing Uncertainty in Sets." arXiv:2302.11575. https://arxiv.org/abs/2302.11575 `[unverified: authors, venue and year not confirmed]`

## Node-link, polygon and matrix encodings for hypergraphs

- Ouvrard, X., Le Goff, J.-M., Marchand-Maillet, S. "Networks of Collaborations: Hypergraph Modeling and Visualisation." arXiv:1707.00115, 2017. https://arxiv.org/abs/1707.00115 — *the extra-node representation, compared qualitatively and quantitatively with the clique expansion.*
- Paquette, J., Tokuyasu, T. "Hypergraph visualization and enrichment statistics: how the EGAN paradigm facilitates organic discovery from big data." Proc. SPIE 7865, 2011. https://doi.org/10.1117/12.890220
- Kerren, A., Jusufi, I. "A Novel Radial Visualization Approach for Undirected Hypergraphs." EuroVis Short Papers, 2013. https://doi.org/10.2312/PE.EuroVisShort.EuroVisShort2013.025-029
- Di Bartolomeo, S., Pister, A., Buono, P., Plaisant, C., Dunne, C., Fekete, J.-D. "Six Methods for Transforming Layered Hypergraphs to Apply Layered Graph Layout Algorithms." Computer Graphics Forum 41(3), EuroVis 2022. https://doi.org/10.1111/cgf.14538
- Qu, B., Zhang, E., Zhang, Y. "Automatic Polygon Layout for Primal-Dual Visualization of Hypergraphs." IEEE TVCG 28(1):633–642, 2022. https://doi.org/10.1109/TVCG.2021.3114759
- Jin, R., Xiang, Y., Fuhry, D., Dragan, F. F. "Overlapping Matrix Pattern Visualization: A Hypergraph Approach." IEEE ICDM 2008, pp. 313–322. https://doi.org/10.1109/ICDM.2008.102
- Kapec, P. "Visualizing software artifacts using hypergraphs." SCCG 2010. https://doi.org/10.1145/1925059.1925067
- Nafar, M., Azami Zenouzagh, H. "Mixed coordinate Node link Visualization for Co-authorship Hypergraph Networks." arXiv:2310.19640, 2023. https://arxiv.org/abs/2310.19640 `[unverified: no evaluation seen]`

## Dynamic and temporal hypergraph visualisation

- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Analyzing Dynamic Hypergraphs with Parallel Aggregated Ordered Hypergraph Visualization." IEEE TVCG 27(1):1–13, 2021 (online 2019). https://doi.org/10.1109/TVCG.2019.2933196 ; open copy https://inria.hal.science/hal-02264960 — *PAOH: encoding, drips, orderings, role symbols, 9-participant study.*
- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Using Dynamic Hypergraphs to Reveal the Evolution of the Business Network of a 17th Century French Woman Merchant." VIS4DH workshop, IEEE VIS 2018. https://vis4dh.dbvis.de/papers/2018/Using%20Dynamic%20Hypergraphs%20to%20Reveal%20the%20Evolution%20of%20the%20Business%20Network%20of%20a%2017th%20Century%20French%20Woman%20Merchant.pdf
- Peña-Araya, V., Xue, T., Pietriga, E., Amsaleg, L., Bezerianos, A. "HyperStorylines: Interactively untangling dynamic hypergraphs." Information Visualization 21(1):38–62, 2022 (online 2021). https://doi.org/10.1177/14738716211045007
- Fischer, M. T., Arya, D., Streeb, D., Seebacher, D., Keim, D. A., Worring, M. "Visual Analytics for Temporal Hypergraph Model Exploration." IEEE TVCG 27(2):550–560, 2021 (online 2020). https://doi.org/10.1109/TVCG.2020.3030408 ; https://arxiv.org/abs/2008.07299 — *Hyper-Matrix.*
- Streeb, D., Arya, D., Keim, D. A., Worring, M. "Visual Analytics Framework for the Assessment of Temporal Hypergraph Prediction Models." Set Visual Analytics Workshop at IEEE VIS, 2019. `[unverified: catalogued via Fischer et al., 2021; not fetched directly]`
- Agarwal, S., Beck, F. "Set Streams: Visual Exploration of Dynamic Overlapping Sets." Computer Graphics Forum 39(3):383–391, 2020. https://doi.org/10.1111/cgf.13988
- Nguyen, P. H., Xu, K., Walker, R., Wong, B. L. W. "TimeSets: Timeline visualization with set relations." Information Visualization 15(3):253–269, 2016. https://doi.org/10.1177/1473871615605347
- Burch, M., Vehlow, C., Beck, F., Diehl, S., Weiskopf, D. "Parallel Edge Splatting for Scalable Dynamic Graph Visualization." IEEE TVCG 17(12):2344–2353, 2011. https://doi.org/10.1109/TVCG.2011.226
- Bach, B., Pietriga, E., Fekete, J.-D. "GraphDiaries: Animated Transitions and Temporal Navigation for Dynamic Networks." IEEE TVCG 20(5):740–754, 2014. https://doi.org/10.1109/TVCG.2013.254
- Dang, T. N., Pendar, N., Forbes, A. G. "TimeArcs: Visualizing Fluctuations in Dynamic Networks." Computer Graphics Forum 35(3):61–69, 2016. https://doi.org/10.1111/cgf.12882
- Cakmak, E., Schlegel, U., Jäckle, D., Keim, D. A., Schreck, T. "Multiscale Snapshots: Visual Analysis of Temporal Summaries in Dynamic Graphs." IEEE TVCG 27(2):517–527, 2021. https://doi.org/10.1109/TVCG.2020.3030398
- Garro, R., Jusufi, I., Abghari, S., Brage, J. "Exploring Dynamic Hypergraphs for Clustering Analysis of District Heating Data." VINCI 2025. https://doi.org/10.1145/3769534.3769564

## Scale: simplification, aggregation, exploration

- Zhou, Y., Rathore, A., Purvine, E., Wang, B. "Topological Simplifications of Hypergraphs." arXiv:2104.11214, 2021. https://arxiv.org/abs/2104.11214
- Oliver, P., Zhang, E., Zhang, Y. "Scalable Hypergraph Visualization." IEEE TVCG 30(1):595–605, 2024. https://doi.org/10.1109/TVCG.2023.3326599 ; https://arxiv.org/abs/2308.05043
- Oliver, P., Zhang, E., Zhang, Y. "Structure-Aware Simplification for Hypergraph Visualization." IEEE TVCG 31(1):667–676, 2025. https://doi.org/10.1109/TVCG.2024.3456367
- Gisolf, F., Geradts, Z. J. M. H., Worring, M. "Interactive Hypergraph Visual Analytics for Exploring Large and Complex Image Collections." arXiv:2510.20050, 2025. https://arxiv.org/abs/2510.20050
- Xiong, Z., Mu, R., Yang, C., Xie, W., Lu, Q. "How Hypergraph-to-Graph Conversion Affects Cooperative Working Visualization: A Multi-metric Evaluation." CCIS, Springer, 2024, pp. 208–221. https://doi.org/10.1007/978-981-99-9637-7_15

## Bundling

- Holten, D. "Hierarchical Edge Bundles: Visualization of Adjacency Relations in Hierarchical Data." IEEE TVCG 12(5):741–748, 2006. https://doi.org/10.1109/TVCG.2006.147
- Holten, D., van Wijk, J. J. "Force-Directed Edge Bundling for Graph Visualization." Computer Graphics Forum 28(3):983–990, 2009. https://doi.org/10.1111/j.1467-8659.2009.01450.x
- Wallinger, M., Archambault, D., Auber, D., Nöllenburg, M., Peltonen, J. "Edge-Path Bundling: A Less Ambiguous Edge Bundling Approach." IEEE TVCG 28(1):313–323, 2022. https://doi.org/10.1109/TVCG.2021.3114795 ; https://arxiv.org/abs/2108.05467
- Wang, S. H., Lobier, M., Siebenhühner, F., Puoliväli, T., Palva, S., Palva, J. M. "Hyperedge bundling: A practical solution to spurious interactions in MEG/EEG source connectivity analyses." NeuroImage 173:610–622, 2018. https://doi.org/10.1016/j.neuroimage.2018.01.056 ; code https://github.com/palvalab/hyperedges (checked 2026-09-20)

## Evaluation and perception

- Wallinger, M., Jacobsen, B., Kobourov, S., Nöllenburg, M. "On the Readability of Abstract Set Visualizations." IEEE TVCG 27(6):2821–2832, 2021. https://doi.org/10.1109/TVCG.2021.3074615 ; preprint with the accuracy and time tables https://arxiv.org/abs/2101.08155 — *120 participants; EulerView, LineSets, MetroSets; |U|=30/60, |E|=6/8.*
- (Studies by Rodgers et al. on SetNet and by Baimagambetov et al. on SetNet/Bubble Sets/WebCola are reported via the related-work section of Wallinger et al., 2021. `[unverified: not fetched directly]`)

## Knowledge hypergraphs in practice

- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025. https://arxiv.org/abs/2503.21322 ; code https://github.com/LHRLAB/HyperGraphRAG (MIT licence, checked 2026-09-20) — *lossless bipartite storage (Proposition 2); Figure 5 hairballs at up to 26,902 hyperedges; retrieval saturates at k ≈ 60.*
- Ritz, A., Tegge, A. N., Kim, H., Poirel, C. L., Murali, T. M. "Signaling Hypergraphs." Trends in Biotechnology 32(7):356–362, 2014. https://doi.org/10.1016/j.tibtech.2014.04.007
- Hernández, D., Hogan, A., Krötzsch, M. "Reifying RDF: What Works Well With Wikidata?" SSWS workshop, 2015. https://aidanhogan.com/docs/reification-wikidata-rdf-sparql.pdf `[unverified: venue and pagination not confirmed]`
- Alford, M. "The Equivalence Theorem: First-Class Relationships for Structurally Complete Database Systems." arXiv:2603.13603, 2026. https://arxiv.org/abs/2603.13603 `[unverified: preprint, not peer reviewed]`

## Specifications, documentation and product pages (all checked 2026-09-20)

- Wikidata:Data model. https://www.wikidata.org/wiki/Wikidata:Data_model
- Wikidata Help:Statements. https://www.wikidata.org/wiki/Help:Statements
- Wikidata Help:Qualifiers. https://www.wikidata.org/wiki/Help:Qualifiers
- Wikidata item Q80 and `Special:EntityData/Q80.json` — statement structure and rendered `wikibase-statementgroupview` / `-mainsnak` / `-qualifiers` / `-references` / `-rankselector` DOM classes, inspected directly. https://www.wikidata.org/wiki/Q80
- TypeDB. "Seeing the schema: TypeDB's approach to graph visualization." TypeDB blog, 7 May 2026. https://typedb.com/blog/graph-visualisation-for-hypergraphs
- Neo4j. "Modeling designs" (intermediate nodes for n-ary relationships). https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/
- Neo4j. "About Neo4j Bloom." https://neo4j.com/docs/bloom-user-guide/current/about-bloom/
- Neo4j. "Visualize your data in Neo4j." https://neo4j.com/docs/getting-started/graph-visualization/graph-visualization/
- KGTK file specification. https://kgtk.readthedocs.io/en/latest/specification/
- Cytoscape.js documentation (compound nodes; a node has a single, normally immutable parent). https://js.cytoscape.org/
- Graphviz download page (current stable 16.1.0). https://graphviz.org/download/
- Gephi project site (0.11 in beta as of April 2026; Gephi Lite 1.0, October 2025). https://gephi.org/
- Tulip project site. https://tulip.labri.fr/
- yWorks. "Hyperedge support by yEd", yEd Q&A, 29 January 2013. https://yed.yworks.com/support/qa/2306/hyperedge-support-by-yed
- Kineviz GraphXR product page. https://www.kineviz.com/graphxr
- metaphacts. metaphactory product page (v6.0 announced 2026-07-14). https://www.metaphacts.com/product
- PAOHVis project page, Inria Aviz; source https://gitlab.inria.fr/aviz/paohvis ; demo https://aviz.fr/paohvis/paoh.html . https://www.aviz.fr/Research/paohvis
- Murrell, P. "How To use the hyperdraw package." Bioconductor vignette, 28 April 2026. https://www.bioconductor.org/packages/devel/bioc/vignettes/hyperdraw/inst/doc/hyperdraw.pdf ; package page https://www.bioconductor.org/packages/release/bioc/html/hyperdraw.html

## Software (versions and dates checked 2026-09-20)

- HyperNetX 2.4.3, PyPI upload 2026-07-23, 3-clause BSD. Source `hypernetx/drawing/{rubber_band,two_column,draw_bipartite,draw_incidence,draw_storyline}.py` inspected and executed. https://github.com/pnnl/HyperNetX
- hypernetx-widget (`hnxwidget`) 0.1.1b3, PyPI upload 2023-05-09. https://github.com/pnnl/hypernetx-widget ; demo https://pnnl.github.io/hypernetx-widget/
- XGI 0.10.2, PyPI upload 2026-05-15, 3-clause BSD. `xgi/drawing/draw.py` inspected and executed. https://github.com/xgi-org/xgi
- hypergraphx (HGX) 1.8.0, PyPI upload 2026-05-18, BSD-3-Clause. `hypergraphx/viz/` inspected. https://github.com/HGX-Team/hypergraphx
- Antelmi, A., Cordasco, G., Kamiński, B., Prałat, P., Scarano, V., Spagnuolo, C., Szufel, P. "Analyzing, Exploring, and Visualizing Complex Networks via Hypergraphs using SimpleHypergraphs.jl." Internet Mathematics, 2020. https://doi.org/10.24166/im.01.2020 ; package v0.4.0 in the Julia General registry, MIT. https://github.com/pszufe/SimpleHypergraphs.jl
- Czvetkó, T., Abonyi, J. "Version [1.0] - HAT-VIS — A MATLAB-based hypergraph visualization tool." SoftwareX 28:101963, 2024. https://doi.org/10.1016/j.softx.2024.101963
- Ficsor, A., Czvetko, T., Sebestyen, V., Abonyi, J. "HyperGodot: Interactive hypergraph visualization tool." SoftwareX 31:102315, 2025. https://doi.org/10.1016/j.softx.2025.102315
- HGPolyVis (Apache-2.0, Windows desktop). https://github.com/peterdanieloliver/HGPolyVis
- NetworkX 3.6.1, PyPI upload 2025-12-08, BSD-3-Clause. https://networkx.org/
- npm registry: d3 7.9.0 (2024-03-12, ISC); sigma 3.0.3 (2026-04-30, MIT); graphology 0.26.0 (2025-01-26, MIT); cytoscape 3.34.3 (2026-09-07, MIT); vis-network 10.1.2 (2026-08-19, Apache-2.0 OR MIT); `@neo4j-nvl/base` 2.0.0 (2026-09-15). https://www.npmjs.com/
- PyPI: `upsetplot` 0.9.0 (2023-12-31, BSD-3-Clause); `matplotlib-venn` 1.1.2 (2025-02-25, MIT); `venn` 0.1.3 (2018-09-12, GPLv3); `tulip-python` 6.0.0 (2024-12-09); `kgtk` 1.5.4 (2023-06-29, MIT).
- CRAN (`crandb.r-pkg.org`): HyperG 1.0.0 (2021-03-04, GPL >= 2); rhype 0.3.0 (2022-08-06, GPL >= 3); UpSetR 1.4.1 (2026-05-25, MIT); ggupset 0.4.1 (2025-02-11, GPL-3).
- Bioconductor: hyperdraw 1.64.0 (GPL >= 2, maintainer Paul Murrell); hypergraph (dependency).
- CTAN package API: `venndiagram` 1.2 (2018-06-07, LPPL 1.3); `tikz-network` 1.1 (2019-08-15, GPL 3+); `pst-venn`; `venn` (MetaPost). A CTAN search for "hypergraph" returned no packages. https://ctan.org/
- Cookbook execution environment: Python 3.11.15, matplotlib 3.11.2, hypernetx 2.4.3, xgi 0.10.2; Node 22.22.2, d3 7.9.0, jsdom 30.1.0, mermaid 12.0.0. All six recipes in `kb/06-visualization/visualization-cookbook-for-this-kb.md` were executed on 2026-09-20.
