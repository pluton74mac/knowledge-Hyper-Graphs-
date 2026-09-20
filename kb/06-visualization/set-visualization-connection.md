---
title: Set visualisation and hypergraph visualisation — the same problem, twice
type: comparison
status: draft
tags: [set-visualization, hypergraph, upset, bubble-sets, kelpfusion, linesets, taxonomy, alsallakh]
created: 2026-09-20
updated: 2026-09-20
---

# Set visualisation and hypergraph visualisation — the same problem, twice

## 1. The identity

A **set system** `(U, E)` is a universe `U` of elements together with a family `E ⊆ 2^U` of subsets.
A **hypergraph** `H = (V, E)` is a vertex set with a family of subsets of it. These are the same
object. Wallinger et al. state it without hedging: "Set systems can also be modeled as hypergraphs,
where `U` is the vertex set and `E` is the set of hyperedges"
([Wallinger, Jacobsen, Kobourov & Nöllenburg, 2021](https://doi.org/10.1109/TVCG.2021.3074615)).
Fischer et al. agree from the other side, treating set visualisations as "a specific representation
of hypergraphs" ([Fischer, Frings, Keim & Seebacher, 2021](https://arxiv.org/abs/2107.13936)).

So the set-visualisation literature — larger, older and far better evaluated than the hypergraph
one — is directly available. Two communities, one problem, different vocabularies:

| Set visualisation | Hypergraph visualisation |
|---|---|
| element | vertex |
| set | hyperedge |
| membership | incidence |
| element/set-membership matrix | incidence matrix |
| set intersection | hyperedge intersection |
| "overlapping sets" | non-partition hypergraph |

**Where the identity breaks.** A set is *only* a subset. A knowledge-hypergraph hyperedge is a typed,
role-labelled, possibly directed, possibly nested, attributed n-ary fact
([knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md)).
Nothing in the set-visualisation literature encodes roles or direction. So set techniques address the
**membership layer** of a KHG and nothing above it. Use them where membership is the question; do not
expect them to carry a fact's semantics.

---

## 2. The Alsallakh taxonomy

The reference survey is
[Alsallakh, Micallef, Aigner, Hauser, Miksch & Rodgers, 2016](https://doi.org/10.1111/cgf.12722)
("The State-of-the-Art of Set Visualization", CGF 35(1):234–260; the EuroVis STAR version is 2014).
It classifies visual representations into **six categories**:

1. **Euler and Venn diagrams** — closed curves, overlap regions carry semantics;
2. **Overlays** — set marks drawn over a pre-existing layout (map, scatter plot, node-link);
3. **Node-link diagrams** — elements and/or sets as nodes, membership as links;
4. **Matrix-based techniques** — element × set incidence, or intersection × set;
5. **Aggregation-based techniques** — sets or intersections summarised into bars, bins, radial slots;
6. **Other / hybrid techniques**.

and it defines a **task taxonomy of 26 tasks in three categories** — element-based, set-based and
attribute-based (see [perception-and-evaluation-studies.md](perception-and-evaluation-studies.md) for
the definitions and examples).

The mapping to [visual-encodings-catalogue.md](visual-encodings-catalogue.md) is almost one to one:
category 1 ≈ the subset standard, category 3 ≈ the bipartite/extra-node encoding, category 4 ≈ the
incidence matrix and PAOH, category 5 ≈ the aggregation strategies in
[large-scale-and-interactive-exploration.md](large-scale-and-interactive-exploration.md). Category 2,
overlays, has **no hypergraph-native counterpart** and is the most transferable idea for KHGs: it
lets a KHG membership layer sit on top of a layout chosen for some other reason — an embedding
projection, a geographic map, a schema diagram.

---

## 3. The four techniques that matter most for a KHG

### 3.1 UpSet — the matrix/aggregation workhorse

UpSet drops the region metaphor entirely: rows are *set intersections*, a combination matrix of dots
shows which sets each intersection belongs to, and aligned bar charts show intersection and set
cardinalities ([Lex, Gehlenborg, Strobelt, Vuillemot & Pfister, 2014](https://doi.org/10.1109/TVCG.2014.2346248),
IEEE TVCG 20(12):1983–1992).

```
  sets →   A  B  C
  ●──●──○   ████████  12     A∩B
  ●──○──●   ████       5     A∩C
  ●──●──●   ██         2     A∩B∩C
```

Why it matters here: it is the **only widely adopted set encoding that scales to dozens of sets**,
because nothing overlaps and nothing needs colour. HyperNetX exposes a hypergraph flavour directly as
`hnx.draw_incidence_upset` (v2.4.3, checked 2026-09-20), and implementations exist as `upsetplot`
(Python) and `UpSetR` / `ggupset` (R) — see [tools-and-libraries.md](tools-and-libraries.md).

**Caution for KHGs.** UpSet's rows are *intersections*, not hyperedges. In a KHG, two facts with the
same argument set are still two distinct facts; UpSet would collapse them. Use a plain incidence
matrix (rows = facts) when fact identity matters, and UpSet when the question really is "which
combinations of entities co-occur".

### 3.2 Bubble Sets — overlays on a fixed layout

Isocontours computed with marching squares around set members, routing around non-members
([Collins, Penn & Carpendale, 2009](https://doi.org/10.1109/TVCG.2009.122), IEEE TVCG 15(6):1009–1016).
The defining property is that **positions are not the algorithm's to choose** — the set marks respect
an existing embedding. F2-Bubbles gives a faster, more faithful construction with interactive editing
([Wang et al., 2021](https://doi.org/10.1109/TVCG.2021.3114761)).

Evaluation is mixed and worth knowing: Bubble Sets lost to LineSets and KelpFusion in two
human-subjects studies, but was the *least inaccurate* system in a quantitative comparison
(§3 of [perception-and-evaluation-studies.md](perception-and-evaluation-studies.md)).

### 3.3 KelpFusion — hull-to-tree interpolation

A hybrid whose single parameter moves the rendering "from the minimal spanning tree to the convex
hull", built on shortest-path graphs
([Meulemans, Riche, Speckmann, Alper & Dwyer, 2013](https://doi.org/10.1109/TVCG.2013.76),
IEEE TVCG 19(11):1846–1858), extending Kelp Diagrams
([Dinkla, van Kreveld, Speckmann & Westenberg, 2012](https://doi.org/10.1111/j.1467-8659.2012.03080.x),
CGF 31(3):875–884). The parameter is exactly the dial between the edge standard (tree) and the subset
standard (hull) of [hypergraph-drawing-algorithms.md](hypergraph-drawing-algorithms.md) — the
cleanest demonstration that the two standards are endpoints of one continuum.

### 3.4 LineSets — one smooth curve per set

Each set is a single smooth curve through its elements
([Alper, Riche, Ramos & Czerwinski, 2011](https://doi.org/10.1109/TVCG.2011.186),
IEEE TVCG 17(12):2259–2267). Minimal ink, and the direct ancestor of the metro-map metaphor: a
LineSets curve is a path through the set's members, i.e. a drawn path-based support. The step from
LineSets to MetroSets is the step from "any curve" to "an octilinear line on a shared support".

### 3.5 Others worth knowing

- **Radial Sets** — aggregation-based interactive analysis of large overlapping sets
  ([Alsallakh, Aigner, Miksch & Hauser, 2013](https://doi.org/10.1109/TVCG.2013.184),
  IEEE TVCG 19(12):2496–2505).
- **Linear diagrams** — each set is a horizontal segment; overlap in x means intersection; backed by
  the strongest empirical design guidance in the field
  ([Rodgers, Stapleton & Chapman, 2015](https://doi.org/10.1145/2810012), ACM TOCHI 22(6):1–39).
- **Hoop diagrams** — a recent circular variant
  ([Rodgers, Chapman, Blake, Nöllenburg, Wallinger & Dobler, 2024](https://doi.org/10.1007/978-3-031-71291-3_31),
  Diagrams 2024, pp. 377–392).
- **SimpleSets** — capturing categorical point patterns with simple shapes
  ([Meulemans et al., 2024](https://arxiv.org/abs/2407.14433)) `[unverified: authors and venue not
  independently confirmed]`.
- **Set uncertainty** — visualising uncertain membership
  ([arXiv:2302.11575](https://arxiv.org/abs/2302.11575)) `[unverified: authors, venue and year not
  confirmed]`; relevant to KHGs, whose extracted facts carry confidence scores.

---

## 4. When set-visualisation techniques apply to a knowledge hypergraph

| KHG situation | Set technique that transfers | Why / caveat |
|---|---|---|
| "Which facts mention entity X?" | incidence matrix, UpSet-style layout grouped by predicate | element-based task; matrix scales |
| "Which entities co-occur across facts?" | UpSet on the entity co-occurrence set system | collapses distinct facts with equal argument sets |
| Membership over an existing layout (embedding projection, map, schema diagram) | **Bubble Sets, Kelp/KelpFusion, LineSets** | the only family designed for fixed positions; this is the strongest transfer |
| ≤ 6 facts in a figure or slide | Euler/Venn | above ~6 sets accuracy collapses ([Wallinger et al., 2021](https://doi.org/10.1109/TVCG.2021.3074615)) |
| Each entity appears in few facts | MetroSets | needs a path-based support; won the only three-way readability study |
| Facts with confidence or provenance weight | Radial Sets, aggregation views, set-uncertainty work | attribute-based tasks; least-studied category |
| Facts with **roles or direction** | *none* | no set technique encodes roles; use the incidence encoding |
| Facts nested inside facts | *none directly* | region nesting breaks down past 2–3 levels; use the incidence encoding |

**Rule of thumb.** Borrow from set visualisation when the question is about *membership and overlap*
and positions are already fixed by something else. Switch back to the hypergraph-native incidence
encoding as soon as the question involves *what a fact says* — its relation type, its roles, its
direction, its provenance.

---

## 5. What the hypergraph community should take from the set community

1. **A task taxonomy.** 26 tasks in three categories exist and are used; hypergraph papers rarely
   state which they support ([Alsallakh et al., 2016](https://doi.org/10.1111/cgf.12722)).
2. **A habit of evaluation.** Every technique in §3 has at least one controlled study; most
   hypergraph techniques have a case study at best
   ([Fischer et al., 2021](https://arxiv.org/abs/2107.13936)).
3. **The overlay idea.** Decoupling "where things are" from "which sets they are in" is the move that
   makes set visualisation composable with any other view. No hypergraph-native technique does this.
4. **Aggregation as a first-class category.** Alsallakh's category 5 is what
   [large-scale-and-interactive-exploration.md](large-scale-and-interactive-exploration.md) needs and
   what the hypergraph literature mostly lacks.

## Sources

- Alsallakh, B., Micallef, L., Aigner, W., Hauser, H., Miksch, S., Rodgers, P. "The State-of-the-Art of Set Visualization." Computer Graphics Forum 35(1):234–260, 2016 (EuroVis STAR version 2014). https://doi.org/10.1111/cgf.12722
- Lex, A., Gehlenborg, N., Strobelt, H., Vuillemot, R., Pfister, H. "UpSet: Visualization of Intersecting Sets." IEEE TVCG 20(12):1983–1992, 2014. https://doi.org/10.1109/TVCG.2014.2346248
- Collins, C., Penn, G., Carpendale, S. "Bubble Sets: Revealing Set Relations with Isocontours over Existing Visualizations." IEEE TVCG 15(6):1009–1016, 2009. https://doi.org/10.1109/TVCG.2009.122
- Wang, Y., Cheng, D., Wang, Z., Zhang, J., Zhou, L., He, G., Deussen, O. "F2-Bubbles: Faithful Bubble Set Construction and Flexible Editing." IEEE TVCG, 2021. https://doi.org/10.1109/TVCG.2021.3114761
- Meulemans, W., Riche, N. H., Speckmann, B., Alper, B., Dwyer, T. "KelpFusion: A Hybrid Set Visualization Technique." IEEE TVCG 19(11):1846–1858, 2013. https://doi.org/10.1109/TVCG.2013.76
- Dinkla, K., van Kreveld, M., Speckmann, B., Westenberg, M. "Kelp Diagrams: Point Set Membership Visualization." Computer Graphics Forum 31(3):875–884, 2012. https://doi.org/10.1111/j.1467-8659.2012.03080.x
- Alper, B., Riche, N., Ramos, G., Czerwinski, M. "Design Study of LineSets, a Novel Set Visualization Technique." IEEE TVCG 17(12):2259–2267, 2011. https://doi.org/10.1109/TVCG.2011.186
- Alsallakh, B., Aigner, W., Miksch, S., Hauser, H. "Radial Sets: Interactive Visual Analysis of Large Overlapping Sets." IEEE TVCG 19(12):2496–2505, 2013. https://doi.org/10.1109/TVCG.2013.184
- Rodgers, P., Stapleton, G., Chapman, P. "Visualizing Sets with Linear Diagrams." ACM TOCHI 22(6):1–39, 2015. https://doi.org/10.1145/2810012
- Rodgers, P., Chapman, P., Blake, A., Nöllenburg, M., Wallinger, M., Dobler, A. "Hoop Diagrams: A Set Visualization Method." Diagrams 2024, LNCS, pp. 377–392. https://doi.org/10.1007/978-3-031-71291-3_31
- Wallinger, M., Jacobsen, B., Kobourov, S., Nöllenburg, M. "On the Readability of Abstract Set Visualizations." IEEE TVCG 27(6):2821–2832, 2021. https://doi.org/10.1109/TVCG.2021.3074615 ; https://arxiv.org/abs/2101.08155
- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 short papers. https://arxiv.org/abs/2107.13936
- "SimpleSets: Capturing Categorical Point Patterns with Simple Shapes." arXiv:2407.14433, 2024. https://arxiv.org/abs/2407.14433 `[unverified]`
- "Visualizing Uncertainty in Sets." arXiv:2302.11575. https://arxiv.org/abs/2302.11575 `[unverified]`
- HyperNetX 2.4.3, `hnx.draw_incidence_upset` (inspected 2026-09-20). https://github.com/pnnl/HyperNetX
