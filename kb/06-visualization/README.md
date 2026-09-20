---
title: 06 — Visualization
type: index
status: draft
tags: [index, visualization, hypergraph, knowledge-hypergraph]
created: 2026-09-20
updated: 2026-09-20
---

# 06 — Visualization

**How hypergraphs and knowledge hypergraphs are drawn, with what algorithms, in what tools, and with
what evidence that anyone can read the result.**

A hyperedge is an arbitrary subset, and a subset has no natural picture. Every hypergraph
visualisation is therefore a design decision, and for a *knowledge* hypergraph the decision is harder
still: an n-ary fact carries a relation type, role-labelled arguments, sometimes a direction, usually
qualifiers, and occasionally other facts nested inside it.

**The section's bottom line.** Draw a knowledge hypergraph as a **role-labelled, typed, directed
incidence (Levi) graph**: entities as circles, facts as squares, roles as link labels, tail/head as
arrowheads. It is lossless, linear in hyperedge size, tractable to lay out, has somewhere to put the
fact's metadata, and is what Wikidata, TypeDB, Neo4j, KGTK, HyperNetX, XGI and HyperGraphRAG all
converge on. Use region encodings only for small curated excerpts, PAOH when facts are time-stamped,
matrices above a hundred facts, and query-driven selection above a thousand. The argument, with its
costs and its one big evidential gap, is in
[knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md).

---

## Notes in this section

| Note | What it answers |
|---|---|
| [visual-encodings-catalogue.md](visual-encodings-catalogue.md) | **What can a hyperedge look like?** The full catalogue of encodings — bipartite/extra-node, clique and star expansions, colour-coded curves, metro maps, radial layouts, Euler diagrams, hull and isocontour overlays, the polygon metaphor, the Zykov representation, subdivision drawings, incidence matrices, UpSet, PAOH, linear and hoop diagrams, storylines, Sankey-like flows, 3D and multilayer — each with a sketch, pros, cons and the paper that proposed it, plus a decision table. |
| [hypergraph-drawing-algorithms.md](hypergraph-drawing-algorithms.md) | **How is the picture computed, and what is provably hard?** Mäkinen's subset/edge standards; three inequivalent planarity notions (Zykov = incidence-graph planarity, linear time; Venn-style and subdivision drawings, NP-complete); the support machinery with a full complexity table; force-directed layouts from Bertault & Eades' PATATE to Arafat & Bressan's four associated graphs and their four aesthetics metrics; Euler-diagram generation; orthogonal/VLSI drawing; bundling; metro-map drawing; point-line incidences. Ends with a hardness summary. |
| [dynamic-and-temporal-hypergraph-visualization.md](dynamic-and-temporal-hypergraph-visualization.md) | **How do you show facts that change over time?** PAOH in depth (encoding, drips, eight vertex orderings, role symbols, 50–500 vertices, the Dart/Canvas implementation, the 9-participant study, and the design options that were tried and rejected); HyperStorylines and its head-to-head win over PAOHVis; Streeb's glyph matrix and Hyper-Matrix; Set Streams and TimeSets; a table of the four distinct meanings of "the hyperedge changed"; and a recommendation. |
| [knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md) | **How is n-ary knowledge actually drawn in practice?** Wikidata's statement block (verified against the live DOM and a real 5-ary fact); TypeDB Studio's entity/relation/attribute shapes with role-labelled edges; Neo4j's intermediate-node pattern and what Bloom can and cannot show; HyperGraphRAG's lossless bipartite storage and its 27k-hyperedge hairball figures; role encodings; directed hyperedges; nesting. Ends with **this KB's recommended encoding and the justification**. |
| [tools-and-libraries.md](tools-and-libraries.md) | **What can I install today?** Tables of native hypergraph libraries (HyperNetX, XGI, hypergraphx, SimpleHypergraphs.jl, HGPolyVis, PAOHVis, MetroSets, HAT-VIS, HyperGodot), general graph libraries used for the bipartite encoding (NetworkX, D3, Sigma.js, Cytoscape.js, Graphviz, Gephi, Tulip, yFiles), knowledge-graph platforms (TypeDB Studio, Neo4j Bloom/NVL, GraphXR, GraphDB, metaphactory, KGTK), R packages (incl. `hyperdraw`, the one real directed-hyperedge renderer), Python set-vis helpers and LaTeX packages — each with language, encodings, interactivity, scale, licence and a version date checked on 2026-09-20. |
| [perception-and-evaluation-studies.md](perception-and-evaluation-studies.md) | **What do we actually know about readability?** The 26-task/3-category taxonomy; the 120-participant abstract set study with its accuracy table (EulerView collapses from 0.86 to 0.16 as sets go from 6 to 8); the overlay studies (LineSets vs Bubble Sets vs KelpFusion); linear diagrams beating Euler; the thin hypergraph-specific evidence (PAOH's 9 participants, HyperStorylines' comparative study); a scalability-ceiling table per encoding; and the honest admission that no study compares bipartite against subset drawings of the same hypergraph. |
| [set-visualization-connection.md](set-visualization-connection.md) | **Why the set-visualisation literature is the same field.** The set-system/hypergraph identity and the vocabulary map; Alsallakh's six categories and 26 tasks; UpSet, Bubble Sets, KelpFusion and LineSets explained for a hypergraph audience (KelpFusion's parameter is literally the dial between the edge and subset standards); a table of when each set technique transfers to a KHG and when it cannot (roles, direction, nesting). |
| [large-scale-and-interactive-exploration.md](large-scale-and-interactive-exploration.md) | **What do you do at 10⁴ facts?** Topological and structure-aware simplification; aggregation (which is closed for hypergraphs, so level-of-detail is safe); a four-level LOD ladder for KHGs; focus+context including PAOH's drips; embedding-based 2D projections of entities *and* of hyperedges; SVG/Canvas/WebGL rendering ceilings; and query-driven exploration — with HyperGraphRAG's k≈60 saturation as evidence that the useful neighbourhood is small. Ends with a concrete five-stage pipeline. |
| [visualization-cookbook-for-this-kb.md](visualization-cookbook-for-this-kb.md) | **Just show me the code.** Six recipes, all executed on 2026-09-20 with the console output reproduced: four HyperNetX encodings; XGI hulls, bipartite and a directed n-ary fact; the recommended encoding by hand; a PAOH-style temporal plot in ~40 lines of matplotlib; a D3 incidence sketch with role labels (tested headlessly under jsdom); and a Mermaid approximation (validated with `mermaid.parse`). Includes the API gotchas found while running them. |

## Reading paths

- **"I need to draw something this afternoon."**
  [visualization-cookbook-for-this-kb.md](visualization-cookbook-for-this-kb.md) →
  [tools-and-libraries.md](tools-and-libraries.md).
- **"I am designing a KHG viewer."**
  [knowledge-hypergraph-specific-visualization.md](knowledge-hypergraph-specific-visualization.md) →
  [large-scale-and-interactive-exploration.md](large-scale-and-interactive-exploration.md) →
  [perception-and-evaluation-studies.md](perception-and-evaluation-studies.md).
- **"I want the theory."**
  [visual-encodings-catalogue.md](visual-encodings-catalogue.md) →
  [hypergraph-drawing-algorithms.md](hypergraph-drawing-algorithms.md) →
  [set-visualization-connection.md](set-visualization-connection.md).
- **"My data has timestamps."**
  [dynamic-and-temporal-hypergraph-visualization.md](dynamic-and-temporal-hypergraph-visualization.md)
  → recipe 4 of the cookbook.

## Ten things this section established

1. Every knowledge-representation system that holds n-ary facts draws them as **fact nodes with
   role-labelled links** — not as regions. The subset standard dominates the academic literature and
   has near-zero adoption in KG tooling.
2. **Everything that demands a nice region structure is NP-complete** (Venn-style drawability,
   subdivision drawings, planar/compact/2-outerplanar supports, minimum path-based supports);
   **everything that goes through the incidence graph is easy** (Zykov planarity is linear time).
3. The only dedicated hypergraph-visualisation survey found **14 approaches in 20 years** of
   TVCG/CGF, of which six support time at all.
4. **Euler diagrams collapse at 6–8 sets** — the best-supported negative result in the field.
5. **Colour cannot carry hyperedge identity** past about a dozen hyperedges.
6. **No study compares a bipartite drawing against a subset drawing of the same hypergraph.** The
   KB's central recommendation rests on argument, not measurement.
7. **PAOH is the reference temporal encoding** and the only published technique with an explicit
   role channel; HyperStorylines beat it on relationship-characterisation tasks.
8. **Aggregation is closed for hypergraphs**, which makes level-of-detail safe in a way it is not for
   most structures.
9. **Query-driven selection is the real scalability answer**, and HyperGraphRAG's retrieval
   saturating at k≈60 hyperedges is evidence the useful neighbourhood is genuinely small.
10. **The tool gap is real**: there is no maintained, interactive, web-native hypergraph viewer with
    first-class roles and directed hyperedges that is not tied to one database.

## Open questions raised by this section

1. **Bipartite vs subset, measured.** A controlled study comparing an incidence drawing against a
   hull/Euler drawing of the same hypergraph, on element-, set- and attribute-based tasks. Nobody has
   run it. It is cheap.
2. **Do role labels help or hurt?** Every KHG system shows roles; no study measures whether readers
   use them, or at what density they become noise.
3. **Are hyperedge-embedding projections useful?** Projecting fact vectors to 2D turns a 10⁴-hyperedge
   problem into a scatter plot, but no published evaluation exists.
4. **What is the benchmark?** There is still "no established benchmark dataset for hypergraph
   visualizations, no established performance metrics" (Fischer et al., 2021). A KHG-flavoured
   benchmark — with roles, direction, time and provenance — would be a contribution in itself.
5. **Does a KHG need its own task taxonomy?** Alsallakh's 26 set tasks do not cover "which role does
   this entity play", "which facts contradict", or "what is this fact's provenance".
6. **Is there a readable encoding for nested facts?** Region nesting fails past 2–3 levels; the
   incidence encoding makes nesting invisible. Nothing in the literature addresses it directly.
7. **No peer-reviewed VR/AR study of hypergraph reading** was found, despite 3D layouts existing
   since 2010.

## Conventions used here

- Encoding names follow [visual-encodings-catalogue.md](visual-encodings-catalogue.md).
- Tool versions and dates are stated with the date they were checked, per
  [../../CONVENTIONS.md](../../CONVENTIONS.md).
- Claims taken from another paper's summary of a third paper say so; claims that could not be
  verified are marked `[unverified]`.
- The section bibliography is [../../sources/by-topic/06-visualization.md](../../sources/by-topic/06-visualization.md).
