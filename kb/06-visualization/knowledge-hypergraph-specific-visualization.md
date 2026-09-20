---
title: Visualising knowledge hypergraphs in practice
type: survey
status: draft
tags: [knowledge-hypergraph, n-ary, visualization, wikidata, typedb, neo4j, roles, directed-hyperedge, nesting, recommendation]
created: 2026-09-20
updated: 2026-09-20
---

# Visualising knowledge hypergraphs in practice

The hypergraph-drawing literature ([visual-encodings-catalogue.md](visual-encodings-catalogue.md),
[hypergraph-drawing-algorithms.md](hypergraph-drawing-algorithms.md)) mostly treats a hyperedge as a
*bare subset*. A knowledge hypergraph hyperedge is not bare. It is an n-ary fact with:

- a **relation type** (`treats`, `employer`, `interacts_with`);
- **role-labelled** members (`drug`, `condition`, `dose`, `population`) — position is not enough;
- sometimes a **direction** (tail set → head set) for rules and signalling;
- **qualifiers/attributes** (time, confidence, provenance);
- possible **nesting** — a fact that is a member of another fact.

See [../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md)
and [../02-knowledge-representation/what-is-a-knowledge-hypergraph.md](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md)
for the data models. This note surveys how systems that actually hold n-ary knowledge draw it, and
ends with the encoding this KB recommends.

**Pattern across every system below:** none of them draws a closed curve around the members of a
fact. Every one of them materialises the fact as a *node* and labels the links with roles. The
subset standard, which dominates the academic hypergraph-drawing literature, has essentially no
adoption in knowledge-representation tooling.

---

## 1. Wikidata: the statement block

Wikidata's data model reifies every fact into a **statement**: a claim (property + value) plus
**qualifiers**, **references** and a **rank** (preferred / normal / deprecated)
([Wikidata:Data model](https://www.wikidata.org/wiki/Wikidata:Data_model), checked 2026-09-20).
Qualifiers exist precisely to carry the extra arguments of an n-ary fact
([Help:Qualifiers](https://www.wikidata.org/wiki/Help:Qualifiers), checked 2026-09-20).

The item page does not draw a graph at all. It renders a **nested text block**, whose DOM makes the
structure explicit (inspected on `https://www.wikidata.org/wiki/Q80`, 2026-09-20):

```
wikibase-statementgroupview            one group per property  (183 properties on Q80)
└── wikibase-statementview             one per statement       (283 statements on Q80)
    ├── …-rankselector                 rank, as a small icon at the left
    ├── …-mainsnak                     property + value, the headline row
    ├── …-qualifiers                   the extra arguments, indented under the value
    └── …-references                   provenance, collapsed by default
```

A concrete 5-ary fact, from Q80 (Tim Berners-Lee), retrieved from
`Special:EntityData/Q80.json` on 2026-09-20:

```
employer (P108)  →  CERN (Q42944)
    start time (P580)      1980
    end time (P582)        1980
    position held (P39)    …
```

Design lessons this KB takes from Wikidata:

1. **Grouping by relation type first** (statement groups) is what makes 283 facts on one entity
   readable. Any KHG view should group facts by predicate before anything else.
2. **Rank as a first-class visual channel.** Contradictory facts coexist; the UI does not hide them,
   it *ranks* them. A KHG view needs the same, since extraction pipelines produce contradictions (see
   [../03-construction/llm-based-khg-construction.md](../03-construction/llm-based-khg-construction.md)).
3. **Provenance collapsed by default.** References are present but folded; otherwise they dominate.
4. **Indentation is the hyperedge.** The qualifier rows *are* the other arguments of the n-ary fact;
   the visual grammar is containment, not a drawn region.

Why no graph view: Wikidata's RDF export materialises each statement as a `wds:` statement node, so
the "graph" of Wikidata is already the incidence/bipartite graph of its hypergraph. The trade-offs
between that and the alternatives (standard reification, singleton properties, named graphs) were
measured in [Hernández, Hogan & Krötzsch, 2015](https://aidanhogan.com/docs/reification-wikidata-rdf-sparql.pdf)
("Reifying RDF: What Works Well With Wikidata?"), `[unverified]` exact venue and page numbers were
not confirmed from the PDF.

---

## 2. TypeDB Studio: relations as diamonds with role-labelled edges

TypeDB models n-ary relations natively: a relation is a first-class object with named roles, not a
binary edge. Its visualiser follows that model directly
([TypeDB blog, "Seeing the schema: TypeDB's approach to graph visualization", 2026-05-07](https://typedb.com/blog/graph-visualisation-for-hypergraphs)):

- **entities → rounded rectangles** (people, companies, places);
- **relations → diamonds** (employment, following, marriage);
- **attributes → ovals** (usernames, dates, descriptions);
- **every edge carries its role label**, so an n-ary relation reads without guessing.

```
   ┌──────────┐  employee   ◇────────  employer  ┌────────┐
   │  Person  │────────────▶employment◀──────────│ Company│
   └──────────┘             ◇  │                 └────────┘
                               │ role
                            ┌──┴───┐
                            │ Role │
                            └──────┘
```

This is the extra-node encoding with **shape** carrying the node kind and **edge label** carrying the
role. The visualiser is built on Sigma.js with custom shape shaders for the three node kinds
`[unverified: reported in community discussion, not in official docs]`. The tool also offers
size-by-connectivity to surface hubs, and uses type inheritance to organise many relation types
([TypeDB blog, 2026](https://typedb.com/blog/graph-visualisation-for-hypergraphs)).

TypeDB Studio is the closest thing to a purpose-built KHG visualiser in a shipping product.

---

## 3. Neo4j: intermediate nodes, and a visualiser that cannot know better

Neo4j's property-graph model is binary. The official modelling guidance is explicit: an n-ary
relationship "is not supported in Neo4j but can be solved by using an intermediary node"
([Neo4j, Modeling designs](https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/),
checked 2026-09-20). The canonical example is employment: an `Employment` node linking Person,
Company and Role, carrying start/end dates.

Consequences for visualisation:

- In **Neo4j Bloom** (and the `Explore` tool that shares the Neo4j Visualization Library, NVL), the
  intermediate node is drawn like any other node. Nothing in the rendering says "this is a fact, not
  an entity". You must encode that yourself with a label, colour and caption in a Perspective.
  Bloom offers "high performance, GPU-powered physics and rendering", Perspectives, near-natural-language
  search, scene saving and in-place editing
  ([Neo4j Bloom user guide, About Bloom](https://neo4j.com/docs/bloom-user-guide/current/about-bloom/),
  checked 2026-09-20).
- Relationship types on the two hops carry the roles (`:EMPLOYEE`, `:EMPLOYER`), so roles survive —
  but only as edge-type names, not as a distinct channel.
- Neo4j's own visualisation overview lists Bloom (proprietary, bundled with AuraDB), Browser
  (open source), and NVL, the open-source library that powers both
  ([Neo4j, Visualize your data](https://neo4j.com/docs/getting-started/graph-visualization/graph-visualization/),
  checked 2026-09-20). NVL is published on npm as `@neo4j-nvl/base` 2.0.0 (2026-09-15).

A sharper criticism of the pattern, worth recording: reifying a relationship as a node "has no arity
constraint, cannot enforce participation roles, and is indistinguishable from any other node in the
graph" ([Alford, 2026](https://arxiv.org/abs/2603.13603), *The Equivalence Theorem*) `[unverified: preprint, not peer reviewed]`. The visual problem is the modelling problem.

**Practical recipe for Bloom/NVL:** give fact nodes a dedicated label (`:Fact`), a distinct colour
and a square-ish icon, set the caption to the relation type, and hide the fact node's own properties
behind inspect. That recovers most of what TypeDB gives for free.

---

## 4. HyperGraphRAG: bipartite storage, hairball figures

HyperGraphRAG is the clearest recent example of a *built* knowledge hypergraph
([Luo, E, Chen, Zheng, Wu, Guo, Lin et al., 2025](https://arxiv.org/abs/2503.21322), NeurIPS 2025). It is worth reading for two
distinct reasons.

**Storage = the incidence graph.** The paper stores the KHG in "an ordinary graph database
represented as a bipartite graph structure", via the transformation
`Φ : V_B = V ∪ E_H, E_B = {(e_H, v) | e_H ∈ E_H, v ∈ e_H}` — and proves it lossless
(their Proposition 2: "A bipartite graph can losslessly preserve and query a knowledge hypergraph",
with the incidence matrix `M` and the neighbourhood identities that make membership queries
`O(|E_B|)`) ([Luo et al., 2025](https://arxiv.org/abs/2503.21322)). The architecture diagram
(Figure 3) shows exactly the two-kind picture: `Hyperedge_1..4` nodes wired to entity nodes such as
"Systolic BP ≥140 mmHg", "Hypertension", "Stroke". The storage layout *is* the visual encoding.

**Figures = untamed force-directed hairballs.** Figure 5(a)–(e) show "Visualizations of knowledge
hypergraphs constructed in 5 domains" whose scale is reported in Figure 5(f): in computer science,
19,913 entities and 26,902 hyperedges; in medicine, 7,675 entities and 4,818 hyperedges
([Luo et al., 2025](https://arxiv.org/abs/2503.21322)). At that size the figures function as
*texture* — they demonstrate "a more interconnected and expressive network" relative to GraphRAG and
LightRAG (ibid.) and nothing else. This is the honest state of the art for KHG figures in ML papers:
the picture argues density, not structure.

Takeaway: for a KHG at 10⁴ hyperedges, a single global node-link view is a rhetorical device, not an
analysis tool. Use it for a paper figure; use the techniques in
[large-scale-and-interactive-exploration.md](large-scale-and-interactive-exploration.md) for work.

---

## 5. Role-labelled hyperedges

Roles are the feature most hypergraph drawing tools lack outright. Options, ordered by how much they
are actually used:

| Technique | Where roles go | Seen in |
|---|---|---|
| Label on the incidence edge | text next to each spoke | TypeDB Studio; Neo4j via relationship types; RDF `wds:` statement graphs |
| Marker shape at the incidence | glyph where hyperedge meets vertex | PAOH ("the role of a vertex of a hyperedge can be marked with a symbol", [Valdivia et al., 2021](https://doi.org/10.1109/TVCG.2019.2933196)) |
| Ordered position around the fact node | 1st, 2nd, 3rd slot clockwise | polygon metaphor ([Qu, Zhang & Zhang, 2022](https://doi.org/10.1109/TVCG.2021.3114759)) — fragile, since polygon order is otherwise arbitrary |
| Indentation under the main value | qualifier rows | Wikidata statement block |
| Column per role | one column per role in a table | UpSet-like incidence matrices with role-typed cells (no published KHG instance found) `[unverified]` |

Only the first two scale past a handful of facts, and only the first one survives without colour.

---

## 6. Directed hyperedges: tail set → head set

A directed hyperedge `(T, H)` with `T, H ⊆ V` is the natural shape for a rule, a reaction or a
signalling step. Published practice:

- **Signalling hypergraphs** in systems biology are exactly `tail → head` hyperedges
  ([Ritz, Tegge, Kim, Poirel & Murali, 2014](https://doi.org/10.1016/j.tibtech.2014.04.007)).
- **hyperdraw** (R/Bioconductor) is the most concrete drawing tool for them: it converts a
  `Hypergraph` of `DirectedHyperedge` objects into a bipartite `graphBPH` object, lays it out with
  Rgraphviz, and draws arrows. Its `arrowLoc` graph attribute controls whether arrows land at the
  edge-node ("middle"), at the end, or at the start of edges
  ([Murrell, hyperdraw vignette, 28 April 2026](https://www.bioconductor.org/packages/devel/bioc/vignettes/hyperdraw/inst/doc/hyperdraw.pdf)).
  The vignette states the representation plainly: "the nodes are divided into two sets - normal nodes
  and edge-nodes - and all of the edges must connect a normal node to an edge-node … This is referred
  to as a 'bipartite' representation of the hypergraph" (ibid.).
- **XGI** renders a `DiHypergraph` with `draw_bipartite`, drawing arrows *into* the edge marker from
  every tail vertex and *out of* it to every head vertex (XGI 0.10.2, `xgi/drawing/draw.py`: "lines
  going towards the center" for the tail, "lines going out from the center" for the head; verified by
  running the code, 2026-09-20 — recipe 3 in
  [visualization-cookbook-for-this-kb.md](visualization-cookbook-for-this-kb.md)).

```
   Aspirin ──▶┐
              ■ interacts#1 ──▶ BleedingRisk
   Warfarin ─▶┘
      (tail set)                  (head set)
```

The arrowheads on the spokes carry the direction. This costs nothing and composes with role labels:
role on the link text, direction on the arrowhead, relation type on the fact node.

---

## 7. Nested hyperedges

A fact about a fact — `stated_by(treats#1, Study42)`, or a rule whose premise is itself a fact —
needs a hyperedge to contain a hyperedge. In the subset standard this is a nested region, which is
where HyperNetX's rubber-band drawing spends effort: nested hulls are spaced so a containing set
surrounds a contained one (`hypernetx/drawing/rubber_band.py`, v2.4.3, checked 2026-09-20). Nesting
is cheap in region form for two or three levels, and unreadable beyond.

In the incidence encoding, nesting is *free*: a fact node is just a node, so it can be the endpoint
of another incidence edge. This is the same move every serious system makes —

- RDF-star / Wikidata: a statement node is a resource, so it can be a subject;
- KGTK: edges are named with an `id` column and that id is then used in the `node1` position of
  another edge, so that "edges themselves can be the subject of other edges"
  ([KGTK file specification](https://kgtk.readthedocs.io/en/latest/specification/), checked 2026-09-20);
- TypeDB: a relation can play a role in another relation;
- Neo4j: the intermediate node can be the endpoint of further relationships.

Visually, nesting in the incidence encoding costs one extra node kind or one extra visual accent —
draw a second-order fact node with a heavier border, or place it on a second layer. Do **not** try to
nest regions for a KHG.

---

## 8. Recommended encoding for this KB

**Default: a role-labelled, typed, directed incidence (Levi) drawing.**

```
  ┌───────────┐  drug      ┏━━━━━━━━━━┓  condition   ┌──────────┐
  │  Aspirin  │───────────▶┃  treats  ┃─────────────▶│ Headache │
  └───────────┘            ┃  #1      ┃              └──────────┘
                    dose ↗ ┗━━━━━━━━━━┛ ↖ population
             ┌────────┐                   ┌────────┐
             │ 500 mg │                   │ Adults │
             └────────┘                   └────────┘
```

Concretely:

| Channel | Carries | Why |
|---|---|---|
| node **shape** | entity (circle) vs fact (square/diamond) | TypeDB's proven grammar; survives greyscale |
| node **label** on the fact | relation type | matches Wikidata statement-group grouping |
| **link label** | role | the only role channel that scales (§5) |
| **arrowhead** | tail vs head membership | free, composes with roles (§6) |
| node **colour** | entity type | leaves shape free for the entity/fact distinction |
| **border weight** on a fact node | nesting order / provenance strength | §7 |
| position | force-directed on the incidence graph, or layered by predicate | §below |

Justification, point by point:

1. **Losslessness.** The incidence graph is a bijective, lossless encoding of the hypergraph; this is
   proved for the KHG case in [Luo et al., 2025](https://arxiv.org/abs/2503.21322) (Proposition 2) and
   is standard otherwise. Region-based encodings lose hyperedge identity as soon as two regions
   coincide.
2. **Cost.** A hyperedge of size `n` costs `n` links instead of `n(n−1)/2` for the clique expansion
   ([Ouvrard, 2020](https://arxiv.org/abs/2002.05014)), and the extra-node encoding "retain[s] more
   information and induc[es] less clutter", shown qualitatively and quantitatively
   ([Ouvrard, Le Goff & Marchand-Maillet, 2017](https://arxiv.org/abs/1707.00115)).
3. **Algorithmic tractability.** Zykov planarity of the hypergraph is planarity of the incidence
   graph, so it is linear-time testable, whereas every region-based drawability question in
   [hypergraph-drawing-algorithms.md](hypergraph-drawing-algorithms.md) is NP-complete or worse. Every
   graph layout algorithm applies unchanged.
4. **Carrying capacity.** Only the incidence encoding has a place to *put* the relation type,
   qualifiers, provenance, rank and confidence: on the fact node.
5. **Nesting and direction** are free (§6, §7).
6. **Convergent practice.** Wikidata, TypeDB, Neo4j, KGTK, hyperdraw, HyperNetX, XGI, hypergraphx
   and HyperGraphRAG's storage layer all converge on it, for both storage and display.

**The cost, stated honestly.** Membership must be read via a two-hop path rather than seen at a
glance, the drawn node count roughly doubles, and Fischer et al. rate node-link approaches as
supporting only "few (Venn diagram) up to several dozens" of hyperedges before clutter
([Fischer, Frings, Keim & Seebacher, 2021](https://arxiv.org/abs/2107.13936)). So:

**Secondary views, by situation:**

| Situation | View |
|---|---|
| more than ~50 facts on screen | PAOH (if time-stamped) or an incidence matrix / UpSet, grouped by predicate |
| facts over time | PAOH with role symbols; HyperStorylines for co-participation narratives — see [dynamic-and-temporal-hypergraph-visualization.md](dynamic-and-temporal-hypergraph-visualization.md) |
| ≤ 10 facts, communicating membership to a non-technical reader | hull/Euler overlay on top of the same layout |
| 10³–10⁴ facts, exploratory | query-driven subgraph extraction, aggregation, embedding projection — see [large-scale-and-interactive-exploration.md](large-scale-and-interactive-exploration.md) |
| documentation and READMEs | Mermaid flowchart approximation, recipe 5 of [visualization-cookbook-for-this-kb.md](visualization-cookbook-for-this-kb.md) |

## Sources

- Wikidata:Data model. Wikidata, checked 2026-09-20. https://www.wikidata.org/wiki/Wikidata:Data_model
- Help:Statements. Wikidata, checked 2026-09-20. https://www.wikidata.org/wiki/Help:Statements
- Help:Qualifiers. Wikidata, checked 2026-09-20. https://www.wikidata.org/wiki/Help:Qualifiers
- Wikidata item Q80 and `Special:EntityData/Q80.json`, statement structure and rendered DOM classes inspected 2026-09-20. https://www.wikidata.org/wiki/Q80
- Hernández, D., Hogan, A., Krötzsch, M. "Reifying RDF: What Works Well With Wikidata?" (SSWS workshop), 2015. https://aidanhogan.com/docs/reification-wikidata-rdf-sparql.pdf `[unverified: venue and pagination not confirmed]`
- TypeDB. "Seeing the schema: TypeDB's approach to graph visualization." TypeDB blog, 7 May 2026, checked 2026-09-20. https://typedb.com/blog/graph-visualisation-for-hypergraphs
- Neo4j. "Modeling designs" (intermediate nodes for n-ary relationships), Getting Started docs, checked 2026-09-20. https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/
- Neo4j. "About Neo4j Bloom", Bloom user guide, checked 2026-09-20. https://neo4j.com/docs/bloom-user-guide/current/about-bloom/
- Neo4j. "Visualize your data in Neo4j", Getting Started docs, checked 2026-09-20. https://neo4j.com/docs/getting-started/graph-visualization/graph-visualization/
- Neo4j Visualization Library, npm package `@neo4j-nvl/base` v2.0.0, published 2026-09-15 (npm registry, checked 2026-09-20). https://www.npmjs.com/package/@neo4j-nvl/base
- Luo, H., E, H., Chen, G., Zheng, Y., Wu, X., Guo, Y., Lin, Q., et al. "HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation." NeurIPS 2025. https://arxiv.org/abs/2503.21322 ; code https://github.com/LHRLAB/HyperGraphRAG (MIT licence, checked 2026-09-20)
- Valdivia, P., Buono, P., Plaisant, C., Dufournaud, N., Fekete, J.-D. "Analyzing Dynamic Hypergraphs with Parallel Aggregated Ordered Hypergraph Visualization." IEEE TVCG 27(1):1–13, 2021. https://doi.org/10.1109/TVCG.2019.2933196
- Qu, B., Zhang, E., Zhang, Y. "Automatic Polygon Layout for Primal-Dual Visualization of Hypergraphs." IEEE TVCG 28(1):633–642, 2022. https://doi.org/10.1109/TVCG.2021.3114759
- Ritz, A., Tegge, A. N., Kim, H., Poirel, C. L., Murali, T. M. "Signaling Hypergraphs." Trends in Biotechnology 32(7):356–362, 2014. https://doi.org/10.1016/j.tibtech.2014.04.007
- Murrell, P. "How To use the hyperdraw package." Bioconductor vignette, 28 April 2026; package hyperdraw 1.64.0, GPL (>= 2), depends on Rgraphviz and hypergraph. https://www.bioconductor.org/packages/devel/bioc/vignettes/hyperdraw/inst/doc/hyperdraw.pdf ; https://www.bioconductor.org/packages/release/bioc/html/hyperdraw.html (checked 2026-09-20)
- KGTK file specification (edge ids used in `node1` position to state facts about edges), checked 2026-09-20. https://kgtk.readthedocs.io/en/latest/specification/
- Ouvrard, X. "Hypergraphs: an introduction and review." arXiv:2002.05014, 2020. https://arxiv.org/abs/2002.05014
- Ouvrard, X., Le Goff, J.-M., Marchand-Maillet, S. "Networks of Collaborations: Hypergraph Modeling and Visualisation." arXiv:1707.00115, 2017. https://arxiv.org/abs/1707.00115
- Fischer, M. T., Frings, A., Keim, D. A., Seebacher, D. "Towards a Survey on Static and Dynamic Hypergraph Visualizations." IEEE VIS 2021 short papers. https://arxiv.org/abs/2107.13936
- HyperNetX 2.4.3 (`rubber_band.py`, nested hull spacing) and XGI 0.10.2 (`draw.py`, directed bipartite arrows), inspected and executed 2026-09-20. https://github.com/pnnl/HyperNetX ; https://github.com/xgi-org/xgi
- Alford, M. "The Equivalence Theorem: First-Class Relationships for Structurally Complete Database Systems." arXiv:2603.13603, 2026. https://arxiv.org/abs/2603.13603 `[unverified: preprint, not peer reviewed]`
