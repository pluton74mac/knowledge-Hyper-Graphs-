---
title: Comparison matrix — knowledge hypergraphs and fifteen neighbouring formalisms
type: comparison
status: draft
tags: [comparison, rdf, rdf-star, property-graph, hyper-relational, hypergraph, simplicial-complex, combinatorial-complex, bipartite, factor-graph, hypernetwork, conceptual-graph, frames, relational-database, tensor, metagraph, higher-order-networks]
created: 2026-09-20
updated: 2026-09-20
---

# Comparison matrix: KHG vs. neighbouring formalisms

This note places the knowledge hypergraph (KHG) next to fifteen formalisms that overlap with it,
and scores each on eleven dimensions. It is the reference table for the rest of
[this section](README.md).

**How to read it, and what it cannot tell you.** A comparison table flattens a design space, and
flattening is exactly the failure mode this section warns about elsewhere. Three caveats:

1. **Expressivity ratings are about what is *primitive*, not about what is *possible*.** Almost every
   formalism here is Turing-complete in the sense that it can encode any of the others by adding
   auxiliary objects. RDF can encode a 5-ary fact; it just needs a relation-instance node
   ([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)). "No" in the n-ary column
   means "not a primitive of the data model", not "cannot be represented". See
   [../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md).
2. **Maturity ratings are a snapshot (September 2026) and decay fast.** One of the entries below
   (Kùzu) was archived during the period this KB covers.
3. **Rows are not mutually exclusive.** A Wikidata statement is simultaneously a hyper-relational
   fact, a reified RDF structure, and a hyperedge with a distinguished pair of roles. The rows are
   *framings*, and a framing is chosen, not discovered.

Definitions of the terms used in the column headings are in
[glossary-of-confusable-terms.md](glossary-of-confusable-terms.md).

---

## 1. The fifteen formalisms in one sentence each

| # | Formalism | Atomic unit | Canonical source |
|---|---|---|---|
| F1 | **Binary KG / RDF triples** | a triple `(s, p, o)` | [RDF 1.2 Concepts, W3C CR, 7 Apr 2026](https://www.w3.org/TR/rdf12-concepts/) |
| F2 | **Labeled property graph (LPG)** | a directed, typed edge between exactly two nodes, both carrying key–value properties | [ISO/IEC 39075:2024 GQL, published 12 Apr 2024](https://en.wikipedia.org/wiki/Graph_Query_Language) |
| F3 | **RDF-star / RDF 1.2 triple terms; hyper-relational KG** | a triple plus statements *about* that triple (RDF 1.2), or a primary triple plus qualifier pairs (Wikidata / StarE) | [RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/); [Galkin et al., 2020](https://arxiv.org/abs/2009.10847) |
| F4 | **Positional n-ary knowledge hypergraph** | a labelled, ordered tuple `r(e₁,…,e_k)`; position carries the role | [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137) |
| F5 | **Role-based hypergraph (TypeDB-style)** | a typed relation instance binding *named* roles to entities | [Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf); [TypeDB features page](https://typedb.com/features), checked 2026-09-20 |
| F6 | **Simplicial complex** | a simplex (set of k+1 nodes) closed downward under subsets | [Battiston et al., 2020](https://arxiv.org/abs/2006.01764) |
| F7 | **Cell / combinatorial complex** | a cell with an assigned rank, giving a *hierarchy* of higher-order relations | [Hajij et al., 2022](https://arxiv.org/abs/2206.00606) |
| F8 | **Bipartite / factor graph (incidence graph)** | an edge joining an element node to a group/factor node | [Battiston et al., 2020](https://arxiv.org/abs/2006.01764); [Kschischang, Frey, Loeliger, 2001](https://en.wikipedia.org/wiki/Factor_graph) |
| F9 | **Hypernetwork (Johnson)** | a *relational* simplex: an ordered set of vertices together with an explicit relation symbol | [Johnson, 2009/2013](https://link.springer.com/chapter/10.1007/978-3-642-02466-5_35) |
| F10 | **Conceptual graph** | a bipartite graph of concept nodes and n-adic conceptual-relation nodes with numbered arcs | [Sowa, conceptual graph examples](https://www.jfsowa.com/cg/cgexampw.htm) |
| F11 | **Frame / slot system** | a frame with named slots (terminals) filled by values or other frames | [Minsky, 1974, MIT AI Memo 306](https://dspace.mit.edu/handle/1721.1/6089) |
| F12 | **Relational database** | a row in a named relation with named, typed, ordered columns | ISO/IEC 9075 (SQL) |
| F13 | **Tensor** | an entry of an order-3 (or higher) array indexed by entities and a relation | [Nickel, Tresp, Kriegel, 2011](https://icml.cc/Conferences/2011/papers/438_icmlpaper.pdf) |
| F14 | **Metagraph (OpenCog Atomese)** | a typed Link whose ordered outgoing list may contain Nodes *or other Links* | [OpenCog AtomSpace](https://github.com/opencog/atomspace) |
| F15 | **Higher-order network (Battiston school)** | an undirected, unlabelled hyperedge (or simplex) representing a group interaction | [Battiston et al., 2020](https://arxiv.org/abs/2006.01764) |

---

## 2. Expressivity dimensions

Legend: **●** native primitive · **◐** expressible but only via a modelling pattern or auxiliary
object · **○** not expressible without leaving the formalism · **n/a** the question does not apply.

| | F1 RDF | F2 LPG | F3 RDF-star / hyper-rel. | F4 positional KHG | F5 role-based KHG | F6 simplicial | F7 cell/comb. | F8 bipartite/factor | F9 hypernetwork | F10 concept. graph | F11 frames | F12 RDB | F13 tensor | F14 metagraph | F15 HON |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **n-ary expressivity** (a fact over k>2 things is one object) | ○ (relation-instance pattern needed) | ○ (intermediate node needed) | ◐ (a triple + qualifiers; poor when there is no natural subject/object) | ● | ● | ● (as a set, untyped) | ● | ● (as a group node) | ● | ● | ● (slots) | ● (a k-column row) | ◐ (order-3 native; higher arity needs higher-order tensors) | ● | ● (untyped) |
| **Meta-statements** (say something *about* a fact: provenance, confidence, time) | ◐ (rdf:Statement reification, four extra triples) | ◐ (properties on the edge; but only about that one edge) | ● (the designed use case) | ○ (would need a new relation or a second layer) | ◐ (TypeDB: relations can own attributes and play roles) | ○ | ○ | ◐ (attach attributes to the group node) | ◐ | ● (contexts) | ● (slots on slots) | ◐ (extra columns / audit tables) | ○ | ● (Values attached to Atoms) | ○ |
| **Direction** (head/tail, or a distinguished orientation) | ● (s→o) | ● | ● (primary triple directed) | ◐ (order encodes it; Fatemi et al. state KHGs "are directed and labeled") | ● (via role semantics) | ○ | ○ | ◐ (directed bipartite graphs exist) | ◐ | ● (arc numbering) | ◐ | n/a | ◐ (mode asymmetry) | ● (ordered outgoing set) | ○ (usually undirected) |
| **Nesting** (a fact as an argument of another fact) | ◐ (via reification node) | ○ | ● in RDF 1.2 (triple term in object position); ◐ in the Wikidata statement model | ○ | ◐ (TypeDB relations can play roles) | ○ | ○ | ◐ (a group node can join another group) | ◐ | ● (nested contexts) | ● | ◐ (foreign keys to a fact table) | ○ | ● (the defining feature) | ◐ (Battiston et al. note hyperedges may contain hyperedges) |
| **Ordered vs named roles** | fixed triple roles | edge endpoints + labels | primary triple ordered; qualifiers keyed | **ordered positions** | **named roles** | unordered set | unordered per rank | unordered incidences | ordered | numbered arcs | named slots | named, ordered columns | ordered modes | ordered list | unordered set |
| **Schema / typing** | ● RDFS/OWL/SHACL | ◐ optional; GQL adds graph types | ● RDFS/OWL + property constraints | ◐ implicit (fixed arity per relation) | ● strong, inheritance-aware | ○ | ○ | ○ | ◐ | ● (the CG canon) | ● | ● (the strongest) | ○ | ● (Atom type system) | ○ |

**Notes on individual cells.**

- F1/F2 "n-ary ○": RDF 1.2 Concepts states plainly that "Relations that involve more than two entities
  can only be indirectly expressed in RDF", cross-referencing the 2006 n-ary relations note
  ([RDF 1.2 Concepts, W3C CR 7 Apr 2026](https://www.w3.org/TR/rdf12-concepts/)). Neo4j's own
  documentation says of hyperedges: "This is not supported in Neo4j but can be solved by using an
  intermediary node" ([Neo4j, Modeling designs](https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/),
  checked 2026-09-20).
- F3 "n-ary ◐": the hyper-relational framing needs a distinguished subject and object. The 2025
  n-ary KG survey states the caveat directly: "when there is no clear subject (i.e., head entity) or
  object (i.e., tail entity) in the facts, it is not appropriate to use the hyper-relational
  formalization" ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)). This is exactly use case 3
  of the W3C note (a purchase with buyer, seller, object, amount, purpose).
- F4 "direction ◐": Fatemi et al. define a KHG over tuples `r(e₁,…,e_k)` and describe knowledge
  hypergraphs as directed and labeled, in contrast to the undirected hypergraphs of most hypergraph
  learning ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)).
- F6 "n-ary ●, but downward-closed": the simplex forces every subset to exist. Torres et al. call
  the move from hypergraph to simplicial complex "forgetting independent relations", and note that
  "in the hypergraph each hyperedge between a set of nodes arises independently, so that having
  additional hyperedges (or the lack thereof) between subsets of nodes within a larger hyperedge
  indeed supplies more information than the one largest hyperedge"
  ([Torres, Blevins, Bassett, Eliassi-Rad, 2021](http://www.eliassi.org/papers/torres-blevins-sirev-2021.pdf)).
  For knowledge, downward closure is almost always wrong: `married(Alice, Bob, 2011-06-04)` does not
  entail `married(Alice, 2011-06-04)`.
- F7: combinatorial complexes were introduced precisely to combine the two: they
  "generalize and combine useful traits of both hypergraphs and cell complexes", imposing
  "no constraints on the set of relations" while permitting "hierarchical higher-order relations"
  ([Hajij et al., 2022](https://arxiv.org/abs/2206.00606)).
- F13 "n-ary ◐": RESCAL's motivation is that "multiple relations of any order can be expressed
  straightforwardly as a higher-order tensor"
  ([Nickel, Tresp, Kriegel, 2011](https://icml.cc/Conferences/2011/papers/438_icmlpaper.pdf)), but
  the cost is exponential in arity and the tensor is dense in shape even when the data is sparse.
  See [limitations-and-failure-modes.md](limitations-and-failure-modes.md) §3.
- F14: HypergraphDB "automatically reifies every entity expressed in the database", each atom having
  "an associated tuple of atoms called its target set"
  ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)); AtomSpace calls itself
  "a kind of in-RAM generalized hypergraph (metagraph) database"
  ([OpenCog AtomSpace](https://github.com/opencog/atomspace)).

---

## 3. Ecosystem dimensions

Legend: **★★★** mature and standardised · **★★** usable, several implementations · **★** research
code or a single implementation · **–** essentially none.

| | Query language maturity | Tooling / databases | ML support | Visualisation | Standardisation |
|---|---|---|---|---|---|
| **F1 RDF** | ★★★ SPARQL 1.1 (W3C Rec. 2013); SPARQL 1.2 in progress | ★★★ many triple stores | ★★★ KG embeddings, large literature | ★★★ many tools, but binary-only layouts | ★★★ W3C Recommendation |
| **F2 LPG** | ★★★ Cypher, plus ISO/IEC 39075:2024 GQL (12 Apr 2024) | ★★★ largest commercial ecosystem | ★★★ PyG/DGL heterogeneous GNNs | ★★★ | ★★★ ISO standard |
| **F3 RDF-star / hyper-relational** | ★★ SPARQL-star in vendor products; SPARQL 1.2 tracking RDF 1.2 | ★★ several triple stores ship it | ★★ StarE, HINGE, GRAN, HAHE | ★ few tools render qualifiers well | ★★ RDF 1.2 Concepts/Semantics at Candidate Recommendation, 7 Apr 2026 |
| **F4 positional KHG** | ★ none standard; research query engines | ★ research code | ★★ HypE, HSimplE, S2S, and the NKG survey's ~50 methods | ★ | – |
| **F5 role-based KHG (TypeDB)** | ★★ TypeQL, single vendor | ★★ one production database | ★ | ★ | – |
| **F6 simplicial complex** | – (not a query formalism) | ★★ GUDHI, Ripser, TopoX | ★★ simplicial NNs | ★★ TDA plots, persistence diagrams | – |
| **F7 cell / combinatorial complex** | – | ★ TopoX / TopoNetX | ★★ CCNNs ([Hajij et al., 2022](https://arxiv.org/abs/2206.00606)) | ★ | – |
| **F8 bipartite / factor graph** | ★★★ (it is just a graph: any graph query language works) | ★★★ | ★★★ (message passing, sum–product) | ★★ readable but doubles the node count | ★★★ inherits graph standards |
| **F9 hypernetwork (Johnson)** | – | ★ | ★ | ★ | – |
| **F10 conceptual graph** | ★ CGIF / historical | ★ mostly historical | ★ | ★★ (a well-designed notation) | ★ ISO/IEC 24707 Common Logic includes CGIF |
| **F11 frames** | ★ (descendants: OWL, schema.org) | ★★ (as ontology languages) | ★ | ★ | ★★ via successors |
| **F12 relational database** | ★★★ SQL | ★★★ | ★★ (relational/statistical learning; ILP) | ★★ ER diagrams | ★★★ ISO/IEC 9075 |
| **F13 tensor** | – | ★★★ numeric libraries | ★★★ | ★ | ★★ (array formats, not semantics) |
| **F14 metagraph (Atomese)** | ★ Atomese pattern matcher | ★ AtomSpace, HypergraphDB | ★ | ★ | – |
| **F15 higher-order network** | – | ★★ XGI, HyperNetX, HypergraphX, SimpleHypergraphs.jl, HAT | ★★ hypergraph NNs | ★★ PAOH, incidence matrices, Euler-style | ★ HIF, "a standard for higher-order network data to facilitate seamless data exchange between higher-order network libraries" ([HIF-standard repo](https://github.com/pszufe/HIF-standard), published in *Network Science*, 2025) |

**The single most important row is "query language maturity".** Of the fifteen, exactly four have a
standardised query language (RDF/SPARQL, LPG/GQL, RDB/SQL, and — derivatively — bipartite graphs,
which inherit graph query languages because they *are* graphs). No standard query language exists
for any native n-ary hypergraph model. This is the practical reason most production systems that
"need hyperedges" still store bipartite encodings; see
[property-graph-vs-typedb-vs-rdf-star.md](property-graph-vs-typedb-vs-rdf-star.md).

Note also that GQL, the 2024 ISO property-graph standard, "does not include n-ary relationships
linking more than two entities" ([Wikipedia, Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language),
checked 2026-09-20; the ISO text itself is paywalled and was not consulted `[unverified]`). So the
newest graph standard deliberately re-affirmed the binary edge.

---

## 4. Lossless and lossy translations between the formalisms

The rows are not free-floating; several are inter-translatable, and knowing which translations lose
information is more useful than the ratings above.

| From → To | Lossless? | What is lost or assumed |
|---|---|---|
| Hypergraph → bipartite/incidence graph | **Lossless** (a bijection with *bicolored* graphs) | Nothing, if the bicoloring is retained. See [hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md) |
| Hypergraph → simplicial complex | Lossy | "Forgetting independent relations": sub-hyperedges become indistinguishable from implied subsets ([Torres et al., 2021](http://www.eliassi.org/papers/torres-blevins-sirev-2021.pdf)) |
| Hypergraph → graph (2-section / clique expansion) | Lossy | Group identity; "such hypergraph-to-graph reductions are inevitably lossy" ([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295)) |
| Graph → simplicial complex (clique complex) | Adds assumptions | "it is necessary to assume that all nodes within a clique are all together related as a single functional unit" ([Torres et al., 2021](http://www.eliassi.org/papers/torres-blevins-sirev-2021.pdf)) |
| n-ary fact → reified RDF / relation instance | **Lossless as a representation** | Nothing structurally; Fatemi et al. state "the binary relations created are equivalent to the original representation and reification does not lose information during conversion". What breaks is *learning*: the auxiliary entity has no embedding at test time ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)) |
| n-ary fact → star-to-clique (pairwise edges) | **Lossy** | Fatemi et al.'s example: after star-to-clique, "flies between(Air Canada, New York, Los Angeles) might be interpreted as being true … whereas looking at the original hypergraph, it is clear that Air Canada does not fly from New York to Los Angeles" ([Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)) |
| n-ary fact → hyper-relational (triple + qualifiers) | Lossy when no subject/object is natural | The choice of which pair is "primary" is arbitrary and changes query results ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)) |
| Hyper-relational fact → hypergraph | Lossy | "The attribution of entities to the main triple or qualifiers is lost, and qualifying relations are not defined" ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)) |
| KHG → tensor | Lossless in principle | Size: an arity-k relation over n entities needs an order-k tensor |

The last three rows are the substance of the
[hyper-relational vs n-ary debate](open-debates.md#2-hyper-relational-vs-n-ary-which-generalises-which):
each direction is lossy, so neither formalism simply contains the other.

---

## 5. A shorter decision table

If the matrix above is too much, this is the operative summary.

| Your situation | Formalism that fits |
|---|---|
| Facts are genuinely binary; you need standards, federation, reasoning | F1 RDF + OWL |
| Facts are binary; you need speed, developer ergonomics, a big hiring pool | F2 LPG |
| Facts are binary but heavily *annotated* (time, source, confidence) | F3 RDF-star / Wikidata statements |
| Facts have several equal participants with no natural subject | F4 or F5 |
| Participants have names and the schema must be enforced | F5 |
| You care about group co-occurrence structure, not about roles | F15 |
| You care about topology (holes, cycles, persistence) and downward closure is defensible | F6, F7 |
| You are computing marginals or doing message passing | F8 |
| Knowledge is deeply nested (beliefs about beliefs, rules as data) | F14 |
| The data is regular, tabular, and high-volume | F12 |
| You are training an embedding model and arity is small and fixed | F13 |

Worked examples and anti-patterns: [when-to-use-and-when-not.md](when-to-use-and-when-not.md).

## Sources

- Aksoy, S., Joslyn, C., Ortiz Marrero, C., Praggastis, B., Purvine, E. "Hypernetwork science via high-order hypergraph walks." *EPJ Data Science* 9(1):16, 2020. https://arxiv.org/abs/1906.11295
- Battiston, F., Cencetti, G., Iacopini, I., Latora, V., Lucas, M., Patania, A., Young, J.-G., Petri, G. "Networks beyond pairwise interactions: structure and dynamics." *Physics Reports* 874:1–92, 2020. https://arxiv.org/abs/2006.01764
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. "Knowledge Hypergraphs: Prediction Beyond Binary Relations." IJCAI 2020 (arXiv v3, 15 Jul 2020). https://arxiv.org/abs/1906.00137
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020. https://arxiv.org/abs/2009.10847
- Hajij, M., et al. "Topological Deep Learning: Going Beyond Graph Data." arXiv:2206.00606, 2022 (rev. 2023). https://arxiv.org/abs/2206.00606
- HIF-standard repository (Hypergraph Interchange Format), HIF-org / pszufe. https://github.com/pszufe/HIF-standard (checked 2026-09-20); reference paper published in *Network Science*, 2025.
- Iordanov, B. "HyperGraphDB: A Generalized Graph Database." 2010. https://hypergraphdb.org/docs/hypergraphdb.pdf
- Johnson, J. "Hypernetworks of Complex Systems." In *Complex Sciences*, Springer LNICST, 2009. https://link.springer.com/chapter/10.1007/978-3-642-02466-5_35 (abstract-level metadata only consulted)
- Kschischang, F. R., Frey, B. J., Loeliger, H.-A. "Factor Graphs and the Sum-Product Algorithm." *IEEE Transactions on Information Theory* 47(2):498–519, 2001. Summarised via https://en.wikipedia.org/wiki/Factor_graph (checked 2026-09-20)
- Minsky, M. "A Framework for Representing Knowledge." MIT AI Memo 306, June 1974. https://dspace.mit.edu/handle/1721.1/6089
- Neo4j. "Modeling designs." Neo4j Getting Started documentation. https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/ (checked 2026-09-20)
- Nickel, M., Tresp, V., Kriegel, H.-P. "A Three-Way Model for Collective Learning on Multi-Relational Data." ICML 2011. https://icml.cc/Conferences/2011/papers/438_icmlpaper.pdf
- Noy, N., Rector, A. (eds.). "Defining N-ary Relations on the Semantic Web." W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- OpenCog AtomSpace repository. https://github.com/opencog/atomspace (checked 2026-09-19 by `kb/02-knowledge-representation/what-is-a-knowledge-hypergraph.md`)
- Sowa, J. F. "Conceptual graph examples." https://www.jfsowa.com/cg/cgexampw.htm
- Torres, L., Blevins, A. S., Bassett, D. S., Eliassi-Rad, T. "The why, how, and when of representations for complex systems." *SIAM Review* 63(3):435–485, 2021. DOI 10.1137/20M1355896. Preprint: http://www.eliassi.org/papers/torres-blevins-sirev-2021.pdf
- TypeDB. "Features." https://typedb.com/features (checked 2026-09-20)
- W3C. "RDF 1.2 Concepts and Abstract Data Model." W3C Candidate Recommendation, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. "A Survey of Link Prediction in N-ary Knowledge Graphs." arXiv:2506.08970, 10 June 2025. https://arxiv.org/abs/2506.08970
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases beyond Binary Relations." IJCAI 2016. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Wikipedia. "Graph Query Language." https://en.wikipedia.org/wiki/Graph_Query_Language (checked 2026-09-20)
