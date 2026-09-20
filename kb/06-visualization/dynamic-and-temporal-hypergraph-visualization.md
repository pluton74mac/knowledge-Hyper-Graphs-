---
title: Dynamic and temporal hypergraph visualization
type: survey
status: draft
tags: [hypergraph, visualization, temporal, dynamic, PAOH, storylines, matrix, set-streams]
created: 2026-09-20
updated: 2026-09-20
---

# Dynamic and temporal hypergraph visualization

Knowledge hypergraph facts carry time: a `treats` fact has an approval date, an `employment` fact a
start and end, a `cited_by` fact a publication year. A *dynamic hypergraph* is a sequence
`{G₁, …, Gₙ}` where `Gᵢ = (V, Hᵢ)` shares a vertex set and varies its hyperedges over time slots —
the definition PAOH inherits from the dynamic-graph survey
([Valdivia, Buono, Plaisant, Dufournaud & Fekete, 2021](https://doi.org/10.1109/TVCG.2019.2933196),
following [Beck, Burch, Diehl & Weiskopf, 2017](https://doi.org/10.1111/cgf.12791)).

The field is young and small. The only dedicated survey found 14 hypergraph-visualisation approaches
in TVCG/IEEE VIS and CGF/EuroVis since 2000, of which **six** support dynamic data at all, and
concludes that "the support for dynamic hypergraphs with many time steps is very limited"
([Fischer, Frings, Keim & Seebacher, 2021](https://arxiv.org/abs/2107.13936)).

---

## 1. The survey's map

Fischer et al. classify by **representation method** — node-link, timeline-based, matrix-based — and
score each approach on scalability (five bands: <10, 10–50, 50–200, 200–1000, >1000 nodes or
hyperedges), static-vs-dynamic, interactivity, tasks, and evaluation
([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

Their headline finding for temporal work:

> node-link-based approaches can only support edge counts ranging from few (Venn diagram) up to
> several dozens … timeline- and matrix-based approaches can support medium- and large-sized
> data-sets with several hundred nodes and hyperedges.

and their verdict: "The three most promising and generic techniques, PAOHvis, Set Streams, and
Hyper-Matrix are also the most recent ones" (ibid.). All three are timeline or matrix techniques.
Node-link is not competitive once time enters.

---

## 2. PAOH / PAOHVis — the reference encoding

**Parallel Aggregated Ordered Hypergraph**
([Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196), IEEE TVCG 27(1):1–13; first
online 2019).

```
                 2019            2020              2021
  Aspirin  ━━━━━━■━━━■━━━━━━━━━━━■━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Headache ━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●━━━━●━━━
  Warfarin ━━━━━━━━━■━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              (each vertical line is one hyperedge in that time slot)
```

- **Encoding.** "PAOH represents vertices as parallel horizontal bars and hyperedges as vertical
  lines, using dots to depict the connections to one or more vertices" (ibid.). Time runs left to
  right in **discrete slots**; inside a slot hyperedges are packed side by side. It is, formally, a
  time-partitioned, transposed incidence matrix drawn as a node-link/matrix hybrid — Fischer et al.
  file it under matrix, the paper itself under timeline.
- **Lineage.** Inspired by BioFabric (vertices as horizontal lines, edges as vertical lines); PAOH
  adds hyperedges, time slots, reordering, packing and interaction (ibid.). An early poster version
  was *Hypenet* (EuroVis 2017 posters) and a first case study appeared at VIS4DH 2018
  ([Valdivia, Buono, Plaisant, Dufournaud & Fekete, 2018](https://vis4dh.dbvis.de/papers/2018/Using%20Dynamic%20Hypergraphs%20to%20Reveal%20the%20Evolution%20of%20the%20Business%20Network%20of%20a%2017th%20Century%20French%20Woman%20Merchant.pdf)).
- **Drips.** Degree-one vertices can be hidden and their existence hinted by "drips, i.e., smaller
  gray dots at the lower end of hyperedges" — a compaction glyph (ibid.).
- **Vertex orderings** (this is where most of the readability lives): Original (by ID), Chronological
  (default; ties broken by degree), Alphabetical, Degree, Group (then chronological within group),
  Reverse Cuthill–McKee (shortens edges), Spectral, Barycenter (ibid.). Orderings are computed with
  `reorder.js`.
- **Edge ordering.** Slots are chronological; within a slot, by the first vertex of the hyperedge, or
  by line length when packing (ibid.).
- **Roles.** "The role of a vertex of a hyperedge can be marked with a symbol", added after a
  historian asked to distinguish primary contractor / secondary / witness (ibid.). This is the one
  published temporal technique with an explicit role channel — directly relevant to KHGs, see
  [knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md).
- **Scale.** Designed for "medium size dynamic hypergraphs (50-500 vertices)"; the implementation
  "can visualize hundreds of vertices (limited by vertical scrolling) and thousands of hyperedges
  (limited by horizontal scrolling)" (ibid.).
- **Implementation.** PAOHVis, about 5,000 lines of Dart compiled to JavaScript, drawing on the HTML
  Canvas API; source at <https://gitlab.inria.fr/aviz/paohvis>, web prototype at
  <https://aviz.fr/paohvis/paoh.html> (ibid.; project page <https://www.aviz.fr/Research/paohvis>,
  checked 2026-09-20).
- **Evaluation.** A formative usability study with **9 participants** on publication data, plus two
  digital-humanities case studies; the study "demonstrates that the technique is easy to learn"
  (ibid.). Formative, not comparative — see
  [perception-and-evaluation-studies.md](perception-and-evaluation-studies.md).
- **Known negative design results** from the same study: alternating hyperedge colours, dashed lines
  and varying line widths were all tried and rejected because participants "found them distracting or
  confusing" (ibid.).

A worked PAOH-style plot you can run is in
[visualization-cookbook-for-this-kb.md](visualization-cookbook-for-this-kb.md) (recipe 4).

---

## 3. HyperStorylines

**HyperStorylines** generalises Storylines to multi-entity, multi-type, time-varying relations
([Peña-Araya, Xue, Pietriga, Amsaleg & Bezerianos, 2022](https://doi.org/10.1177/14738716211045007),
Information Visualization 21(1):38–62; online 2021).

- Entities are lines running left to right through time; "each hyperedge/relationship is represented
  by a rectangle that intersects all the people that are part of it" (ibid.).
- It supports **aggregation and nesting** of entity types — people, locations, companies — which is
  exactly the heterogeneity a KHG has.
- **Evaluation:** a comparative study with tasks inspired by data journalism against **PAOHVis** as
  baseline. HyperStorylines "takes some practice to master" but "performs better for identifying and
  characterizing relationships" and was preferred overall (ibid.).

HyperNetX ships a storyline renderer with the same four marks — nodes as bending lines, hyperedges as
vertical rounded rectangles, incidences as circles, and segments — as
`hnx.draw_incidence_storyline` (HyperNetX 2.4.3, `hypernetx/drawing/draw_storyline.py`, checked
2026-09-20).

**Trade-off vs PAOH.** PAOH quantises time into slots and keeps vertex position fixed forever;
Storylines let lines migrate so that co-participating entities run adjacent, which reads better for
*narrative* but requires crossing minimisation and destroys the stable vertical index that makes PAOH
scannable. Pick PAOH when the analyst needs to look up a known entity; pick Storylines when the
question is "who was involved together, and when".

---

## 4. Matrix-based temporal techniques

### 4.1 Streeb et al. 2019 — glyph matrix

A prototype for temporal hypergraph analysis using a glyph-based matrix view with arrow glyphs per
time frame encoding network changes; scalability limited, and it is the only approach in the survey
that also renders a classic node-link model alongside
(Streeb, Arya, Keim & Worring, 2019, Set Visual Analytics
Workshop at IEEE VIS 2019, as catalogued by [Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

### 4.2 Hyper-Matrix (Fischer et al. 2020/2021)

**Visual Analytics for Temporal Hypergraph Model Exploration**
([Fischer, Arya, Streeb, Seebacher, Keim & Worring, 2021](https://doi.org/10.1109/TVCG.2020.3030408),
IEEE TVCG 27(2):550–560; preprint [arXiv:2008.07299](https://arxiv.org/abs/2008.07299)).

- A **multi-level, matrix-based** representation — the survey describes it as six-level — with
  "drill-down capabilities across multiple levels of semantic zoom, from an overview of model
  predictions down to the content" (ibid.).
- It is not only a view: a **geometric deep learning model** is coupled to the visualisation as "a
  blueprint for problem-specific models", so the analyst's grouping and domain knowledge feed back
  into the prediction (ibid.). This is the only technique in the survey where the visualisation and a
  learned model are co-designed.
- Interactions: matrix reordering, hierarchical grouping, filtering, direct injection of domain
  knowledge into the model ([Fischer et al., 2021 survey](https://arxiv.org/abs/2107.13936)).
- Evaluation: a case study and formative evaluation with law-enforcement experts on real internet
  forum communication data ([Fischer et al., 2021 TVCG](https://doi.org/10.1109/TVCG.2020.3030408)).
- Scale: rated "high" (200–1000) by the survey; the survey also warns that even matrix techniques "do
  not support more than around thousand entities"
  ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

For a KHG whose facts are predicted or scored (link prediction over n-ary facts), Hyper-Matrix is the
closest published design to what is wanted: a matrix of entity×entity affiliation over time layered
on top of a model's output.

---

## 5. Flow and Sankey-like views

### 5.1 Set Streams

Branching and merging streams in a timeline show dynamic set membership; set operations are applied
through queries; scales to "several hundred elements"
([Agarwal & Beck, 2020](https://doi.org/10.1111/cgf.13988), CGF 39(3):383–391). This is the
Sankey/alluvial idiom applied to hyperedges: a stream is a set, a split means members leaving, a
merge means sets uniting. Good for *membership churn*, bad for identifying a specific fact.

### 5.2 TimeSets

Stacked timeline with hyperedges encoded by colour, closest in spirit to KelpFusion; strong case
study and user study; "suffers from poor scalability without aggregating"
([Nguyen, Xu, Walker & Wong, 2016](https://doi.org/10.1177/1473871615605347), Information
Visualization 15(3):253–269; as characterised by
[Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

### 5.3 Other timeline neighbours

TimeArcs ([Dang, Pendar & Forbes, 2016](https://doi.org/10.1111/cgf.12882)) and parallel edge
splatting ([Burch, Vehlow, Beck, Diehl & Weiskopf, 2011](https://doi.org/10.1109/TVCG.2011.226)) are
dynamic-*graph* techniques PAOH positions itself against; GraphDiaries
([Bach, Pietriga & Fekete, 2014](https://doi.org/10.1109/TVCG.2013.254)) is the animated-transition
alternative that Fischer et al. suggest exploring for hypergraphs
([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)). None of them handles hyperedges natively.

---

## 6. Time-varying hyperedges: the modelling choices that precede the picture

Before choosing a view, decide what "the hyperedge changed" means. Four distinct cases, each with a
different visual consequence:

| Case | Example in a KHG | Encoding that works |
|---|---|---|
| Hyperedge **appears / disappears** | a fact is asserted in 2019, retracted in 2021 | PAOH slots; Set Streams |
| Hyperedge **membership changes**, identity persists | a project gains a partner | Storylines (rectangle grows); Set Streams (branch merges) |
| Hyperedge **attribute** changes, membership fixed | a dosage is revised | colour/width on a fixed PAOH line |
| **Vertex** appears/disappears | a new entity enters | all techniques; PAOH shows an empty bar prefix |

PAOH's aggregation into discrete slots is itself a modelling decision: "the stream metaphor has some
benefits but often leads to overlaps, which are avoided in our Parallel Aggregated Ordered Hypergraph
design by aggregating hyperedges in specified time slots"
([Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196)). Choosing the slot granularity
is therefore the single most consequential parameter of a PAOH view.

A useful structural property when you need to shrink a temporal KHG: "when aggregating multiple
vertices, they remain hypergraphs" (ibid.) — aggregation is closed, so level-of-detail can be applied
without leaving the formalism. See
[large-scale-and-interactive-exploration.md](large-scale-and-interactive-exploration.md).

---

## 7. Recent and adjacent work

- **Exploring dynamic hypergraphs for clustering analysis of district heating data**
  ([Garro, Jusufi, Abghari & Brage, 2025](https://doi.org/10.1145/3769534.3769564), VINCI 2025) —
  an applied dynamic-hypergraph analysis, one of the few post-survey additions this KB found.
- **HyperGodot: Interactive hypergraph visualization tool**
  ([Ficsor, Czvetko, Sebestyen & Abonyi, 2025](https://doi.org/10.1016/j.softx.2025.102315),
  SoftwareX 31:102315) and **HAT-VIS**
  ([Czvetkó & Abonyi, 2024](https://doi.org/10.1016/j.softx.2024.101963), SoftwareX 28:101963) —
  two recent tool papers; see [tools-and-libraries.md](tools-and-libraries.md).
  `[unverified]` Abstracts were not retrievable; only title, venue and year are confirmed here.

---

## 8. Recommendation for this KB

For a temporal knowledge hypergraph:

1. **Default to PAOH** with slot granularity chosen from the data's natural period, chronological
   vertex ordering, and role symbols at incidences. It is the only technique that simultaneously
   gives stable entity lookup, explicit hyperedge identity, time, and roles.
2. **Switch to HyperStorylines** when the analytic question is about co-participation narratives
   rather than lookup, accepting the learning cost the authors measured.
3. **Switch to a Hyper-Matrix-style view** above roughly 500 vertices, or whenever a model's
   predictions must be inspected alongside the data.
4. **Do not** animate a node-link hypergraph drawing. No study supports it, and the survey rates
   node-link as the least scalable family even in the static case
   ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).

## Sources

- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Analyzing Dynamic Hypergraphs with Parallel Aggregated Ordered Hypergraph Visualization." IEEE TVCG 27(1):1–13, 2021 (online 2019). https://doi.org/10.1109/TVCG.2019.2933196 ; open copy https://inria.hal.science/hal-02264960
- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Using Dynamic Hypergraphs to Reveal the Evolution of the Business Network of a 17th Century French Woman Merchant." VIS4DH workshop, IEEE VIS 2018. https://vis4dh.dbvis.de/papers/2018/Using%20Dynamic%20Hypergraphs%20to%20Reveal%20the%20Evolution%20of%20the%20Business%20Network%20of%20a%2017th%20Century%20French%20Woman%20Merchant.pdf
- PAOHVis project page, Inria Aviz. https://www.aviz.fr/Research/paohvis (checked 2026-09-20); source https://gitlab.inria.fr/aviz/paohvis ; demo https://aviz.fr/paohvis/paoh.html
- Peña-Araya, V., Xue, T., Pietriga, E., Amsaleg, L., Bezerianos, A. "HyperStorylines: Interactively untangling dynamic hypergraphs." Information Visualization 21(1):38–62, 2022 (online 2021). https://doi.org/10.1177/14738716211045007
- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 short papers, pp. 81–85. DOI 10.1109/VIS49827.2021.9623305. https://arxiv.org/abs/2107.13936
- Fischer, M. T., Arya, D., Streeb, D., Seebacher, D., Keim, D. A., Worring, M. "Visual Analytics for Temporal Hypergraph Model Exploration." IEEE TVCG 27(2):550–560, 2021 (online 2020). https://doi.org/10.1109/TVCG.2020.3030408 ; https://arxiv.org/abs/2008.07299
- Streeb, D., Arya, D., Keim, D. A., Worring, M. "Visual Analytics Framework for the Assessment of Temporal Hypergraph Prediction Models." Set Visual Analytics Workshop at IEEE VIS, 2019. (Catalogued in Fischer et al., 2021: https://arxiv.org/abs/2107.13936)
- Agarwal, S., Beck, F. "Set Streams: Visual Exploration of Dynamic Overlapping Sets." Computer Graphics Forum 39(3):383–391, 2020. https://doi.org/10.1111/cgf.13988
- Nguyen, P. H., Xu, K., Walker, R., Wong, B. L. W. "TimeSets: Timeline visualization with set relations." Information Visualization 15(3):253–269, 2016. https://doi.org/10.1177/1473871615605347
- Beck, F., Burch, M., Diehl, S., Weiskopf, D. "A Taxonomy and Survey of Dynamic Graph Visualization." Computer Graphics Forum 36(1):133–159, 2017. https://doi.org/10.1111/cgf.12791
- Burch, M., Vehlow, C., Beck, F., Diehl, S., Weiskopf, D. "Parallel Edge Splatting for Scalable Dynamic Graph Visualization." IEEE TVCG 17(12):2344–2353, 2011. https://doi.org/10.1109/TVCG.2011.226
- Bach, B., Pietriga, E., Fekete, J.-D. "GraphDiaries: Animated Transitions and Temporal Navigation for Dynamic Networks." IEEE TVCG 20(5):740–754, 2014. https://doi.org/10.1109/TVCG.2013.254
- Dang, T. N., Pendar, N., Forbes, A. G. "TimeArcs: Visualizing Fluctuations in Dynamic Networks." Computer Graphics Forum 35(3):61–69, 2016. https://doi.org/10.1111/cgf.12882
- Vehlow, C., Beck, F., Weiskopf, D. "Visualizing Group Structures in Graphs: A Survey." Computer Graphics Forum 36(6):201–225, 2017. https://doi.org/10.1111/cgf.12872
- Garro, R., Jusufi, I., Abghari, S., Brage, J. "Exploring Dynamic Hypergraphs for Clustering Analysis of District Heating Data." VINCI 2025 (18th Int. Symposium on Visual Information Communication and Interaction). https://doi.org/10.1145/3769534.3769564
- Ficsor, A., Czvetko, T., Sebestyen, V., Abonyi, J. "HyperGodot: Interactive hypergraph visualization tool." SoftwareX 31:102315, 2025. https://doi.org/10.1016/j.softx.2025.102315
- Czvetkó, T., Abonyi, J. "Version [1.0] - HAT-VIS — A MATLAB-based hypergraph visualization tool." SoftwareX 28:101963, 2024. https://doi.org/10.1016/j.softx.2024.101963
- HyperNetX 2.4.3, `hypernetx/drawing/draw_storyline.py` (inspected 2026-09-20). https://github.com/pnnl/HyperNetX
