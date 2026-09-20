---
title: The semantic-web hypergraph view — RDF as a hypergraph, and RDF vs property graphs vs hypergraphs
type: concept
status: draft
tags: [rdf, hypergraph, bipartite, incidence-graph, levi-graph, property-graph, gql, rdf-1.2, formal-models]
created: 2026-09-20
updated: 2026-09-20
---

# The semantic-web hypergraph view

There are two quite different claims in circulation, and they are routinely confused:

- **(A) "RDF *is* a hypergraph."** Each triple is an ordered 3-element hyperedge over one universe of
  resources. This is a statement about the *encoding* of RDF, and it is true and useful.
- **(B) "RDF *needs* a hypergraph."** Binary predicates cannot express an n-ary fact, so a KHG is a
  richer model. This is a statement about *expressiveness*, and it is also true — but it is not
  claim (A), and the hyperedges in the two claims have different arities and different members.

This note works through (A) with its primary source, gives the formal comparison of RDF, property
graphs and hypergraphs that (B) needs, and identifies the incidence (Levi) graph as the translation
device that makes all three commensurable. Claim (B)'s practical side is in
[n-ary-relations-and-reification.md](n-ary-relations-and-reification.md).

## 1. Why RDF is not a graph in the ordinary sense

The problem is set out precisely by Hayes and Gutierrez. An RDF graph "is a set of triples and
therefore, by itself, not a graph in the classic sense"
([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf), ISWC 2004).
The specification agrees with the first half: "An RDF graph is a set of RDF triples"
([RDF 1.2 Concepts, W3C Candidate Recommendation Snapshot, 7 April 2026](https://www.w3.org/TR/rdf12-concepts/)),
and adds the caution that "The graph structure of the abstract data model is not a conceptual model.
It is a symbolic, structural basis for such modelling."

The specific breakage is that a predicate can also be a subject or object:

> "the document leaves open how to deal with a statement property (an edge label) which occurs as the
> subject or object of another statement: one could either duplicate resources as nodes and as edge
> labels ..., or allow edges to connect not only to nodes, but also to other edges. Both approaches
> are inconvenient from several points of view: allowing multiple occurrences of resources as labels
> jeopardizes one of the most important aspects of graph visualization, which is the implicit
> assumption that the complete information regarding a node in a graph is obtained by its place in
> the drawing and its incident edges. On the other hand, the essential drawback of the second
> approach is the fact that the resulting construct is not a graph in the standard sense to which we
> could apply well-established techniques from graph theory."
> ([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf))

Their example — an RDFS schema in which `coauthor` appears both as an edge label and as the subject
of `rdfs:subPropertyOf` — is exactly the situation a knowledge hypergraph handles by refusing to
distinguish node from edge label in the first place.

## 2. RDF as a 3-uniform ordered hypergraph

Hayes and Gutierrez's route is short. They recall the definitions:

> "Formally, let V = {v1, ..., vn} be a finite set, the nodes. A hypergraph on V is a pair
> H = (V, E), where E is a family {Ei}i∈I of subsets of V. The members of E are called edges. A
> hypergraph is simple if all edges are distinct. A hypergraph is said to be r-uniform if all edges
> have the cardinality r. An r-uniform hypergraph is said to be ordered if the occurrence of nodes
> in every edge is numbered from 1 to r."
> ([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf))

and then state:

> "**Proposition 1.** Any RDF Graph can be represented by a simple ordered 3-uniform hypergraph:
> every RDF triple corresponds to a hypergraph edge, the nodes being the subject, predicate and
> object in this order. The node set of the hypergraph is the union of all the edges. (Trivial)"
> ([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf))

with a converse "when imposing constraints on the occurrences of blank nodes and literals: blank
nodes may not be predicates and literals may not serve as subjects or predicates" (same source).

Read carefully: the arity is **3**, fixed, and the three positions are subject, predicate, object.
This is a hypergraph of *statements*, not of *facts about many entities*. The predicate is a member
of the hyperedge, not a label on it — the opposite of the labelled-hyperedge convention used by
[Fatemi et al., 2020](https://arxiv.org/abs/1906.00137) and
[Kok and Domingos, 2009](https://icml.cc/Conferences/2009/papers/576.pdf). Mixing the two
conventions is the single most common source of confusion in this area.

## 3. The bipartite incidence graph, and why it is the right intermediate model

The paper's actual proposal is to go one step further, to the incidence graph:

> "RDF Graphs can be represented naturally by hypergraphs, and hypergraphs can be represented
> naturally by bipartite graphs."
> ([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf))

The construction: rows of the incidence matrix are hyperedges, columns are nodes, and "To the
incidence matrix of a hypergraph H = (V, E) corresponds a bipartite incidence graph
B = (NV ∪ NE, E)". For RDF, the incidences are labelled with the roles:

> "In the case of the hypergraph representing an RDF Graph, the nodes of an edge are ordered and we
> label them by S, P, or O to represent the role (subject, predicate, or object) of the information
> resource. ... Thus, the only difference between the graph derived from the incidence matrix of any
> hypergraph and an RDF Graph hypergraph is the fact that each edge has one of three labels."
> ([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf))

**This is the general recipe.** A knowledge hypergraph with named roles is a bipartite graph whose
left side is entities, right side is hyperedges, and whose incidences are labelled with role names.
Every other encoding in this KB is a variant:

| Encoding | What the "statement node" is | What the incidence labels are |
|---|---|---|
| RDF bipartite graph ([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf)) | a triple | S, P, O |
| W3C n-ary Pattern 1 ([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)) | an individual of a relation class | one property per participant |
| Freebase CVT | a mediator object | CVT properties |
| Wikidata `wds:` statement node | a statement | `ps:`, `pq:`, `pr:` |
| RDF 1.2 reifier | an occurrence of a proposition | `rdf:reifies` + qualifier predicates |
| Conceptual graph | a conceptual relation node | numbered arcs |
| Levi graph of a KHG | a hyperedge | role names |

Joslyn and Nowak call the same object a Levi graph and extend it to nesting as the *uber-Levi graph*
([Joslyn and Nowak, 2017](https://arxiv.org/abs/1704.05547)); see
[metagraphs-atomspace-and-hypergraphdb.md](metagraphs-atomspace-and-hypergraphdb.md).

Hayes and Gutierrez's argument for spending the effort is pragmatic: bipartite graphs bring
"algorithms for the visualization of data for humans, a formal framework to prove properties and
specify algorithms, the availability of libraries with generic implementations of graph algorithms,
and of course, techniques and results of graph theory", enabling reductions of RDF problems — diff,
entailment as subgraph isomorphism, minimisation, semantic distance, clustering — to studied graph
problems ([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf)).
The identical argument applies to knowledge hypergraphs and is why most KHG tooling stores the
incidence structure rather than the hyperedges themselves; HyperGraphRAG, for instance, stores its
hypergraph "as a bipartite graph G_B with V_B = V ∪ E_H"
([Luo et al., 2025](https://arxiv.org/abs/2503.21322)).

## 4. Formal comparison: RDF, property graphs, hypergraphs

**RDF (1.2).** "An RDF triple (often simply called 'triple') is a 3-tuple that is defined inductively
as follows: If s is an IRI or a blank node, p is an IRI, and o is an IRI, a blank node, or a literal,
then (s, p, o) is an RDF triple. If s is an IRI or a blank node, p is an IRI, and o is an RDF triple,
then (s, p, o) is an RDF triple." — the second clause is new in 1.2 and introduces triple terms:
"An RDF triple used as the object of another triple is called a triple term"
([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)). Reification is done by a *reifier*: "a
reifying triple is a triple where the predicate is `rdf:reifies` and the object is a triple term"
(same source).

**Property graph.** The binary restriction is in the definition: "ρ : E → (N × N) is a total function
that associates each edge in E with a pair of nodes in N"
([Angles, 2018](https://ceur-ws.org/Vol-2100/paper26.pdf), AMW 2018). There is no agreed formal
model beyond such proposals — Hartig observed that "for the PG model, there does not even exist a
commonly agreed-upon formal definition" and supplied "a formalization of the PG model and ...
well-defined transformations between PGs and RDF"
([Hartig, 2014](https://arxiv.org/abs/1409.3288)). The ISO standard query language GQL
(ISO/IEC 39075:2024) inherits the binary edge ([ISO/IEC 39075:2024](https://www.iso.org/standard/76120.html)),
and schema work continues through PG-Schema, aimed at "the second version of the GQL Standard"
([Angles et al., 2023](https://arxiv.org/abs/2211.10962)).

**Hypergraph.** `H = (V, E)` with `E` a family of subsets of `V`
([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf)); for
knowledge, labelled and ordered: "a multiset of labeled non-empty ordered subsets of V called
hyperedges" ([Kok and Domingos, 2009](https://icml.cc/Conferences/2009/papers/576.pdf)).

### Side by side

| Property | RDF 1.1 | RDF 1.2 | Labelled property graph | Labelled ordered hypergraph (KHG) |
|---|---|---|---|---|
| arity of an assertion | 3 (s, p, o), of which 2 are "participants" | 3, with nesting in object position | 2 participants + properties | any k |
| edge has an identity | no | yes, via a reifier | yes (edge id, system-specific) | yes, if the model gives hyperedges ids |
| attributes on an edge | no (needs reification) | on the reifier | yes, key-value properties | roles and/or qualifiers |
| predicate is also a resource | yes | yes | no (labels are not nodes) | depends: label vs member |
| edge inside an edge | no | object position only | no | yes in metagraph/ubergraph models |
| standardised | W3C Rec 2014 | W3C CR April 2026 | ISO/IEC 39075:2024 (language); no data-model standard | none |
| query language | SPARQL 1.1 | SPARQL 1.2 (WD 2026) | GQL, Cypher | none standard |

### Expressiveness, informally

Every model in this table can *encode* every other, because all of them can encode the incidence
graph. The differences are (i) how many statements one assertion costs, (ii) whether the encoding is
reversible, and (iii) whether tools respect it. The cost table in
[n-ary-relations-and-reification.md](n-ary-relations-and-reification.md) quantifies (i): 4 extra
triples for RDF reification, 1 for the singleton property, 1 node + n edges for the 2006 n-ary
pattern, 0 for a native hyperedge.

## 5. What this means for a knowledge hypergraph project

1. **Do not claim novelty for "RDF is a hypergraph".** It was proved trivial in 2004
   ([Hayes and Gutierrez, 2004](https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf)). The
   interesting claim is about arity and roles, not about hypergraph-ness.
2. **Store the incidence structure.** It is the common denominator of every model in §4, it is what
   the 2004 paper recommends, and it is what HIF standardises for the analysis libraries
   ([Coll et al., 2025](https://doi.org/10.1017/nws.2025.10018)).
3. **Decide whether the relation is a member or a label.** RDF-as-hypergraph makes the predicate a
   member (position P); the KHG literature makes it a label. Both are defensible; a schema must say
   which, or exports will silently disagree about arity (a "ternary" RDF hyperedge is a *binary*
   fact).
4. **RDF 1.2 narrows but does not close the gap.** Triple terms plus reifiers give statement
   identity and annotation, but "What RDF 1.2 does *not* give is a first-class n-ary predicate"
   ([n-ary-relations-and-reification.md](n-ary-relations-and-reification.md)); a purchase with four
   peer participants still needs the 2006 pattern.

## Sources

- Hayes, J., Gutierrez, C. *Bipartite Graphs as Intermediate Model for RDF.* ISWC 2004, LNCS 3298, pp. 47–61. https://users.dcc.uchile.cl/~cgutierr/papers/bipartite.pdf
- W3C. *RDF 1.2 Concepts and Abstract Data Model.* W3C Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- Angles, R. *The Property Graph Database Model.* AMW 2018, CEUR-WS Vol. 2100. https://ceur-ws.org/Vol-2100/paper26.pdf
- Hartig, O. *Reconciliation of RDF\* and Property Graphs.* arXiv:1409.3288, 11 September 2014 (rev. 13 November 2014). https://arxiv.org/abs/1409.3288
- ISO/IEC. *ISO/IEC 39075:2024 Information technology — Database languages — GQL.* 2024. https://www.iso.org/standard/76120.html
- Angles, R., Bonifati, A., Dumbrava, S., Fletcher, G., et al. *PG-Schema: Schemas for Property Graphs.* SIGMOD 2023; arXiv:2211.10962. https://arxiv.org/abs/2211.10962
- Kok, S., Domingos, P. *Learning Markov Logic Network Structure via Hypergraph Lifting.* ICML 2009. https://icml.cc/Conferences/2009/papers/576.pdf
- Fatemi, B., Taslakian, P., Vazquez, D., Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations.* IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Joslyn, C., Nowak, K. *Ubergraphs: A Definition of a Recursive Hypergraph Structure.* arXiv:1704.05547, 2017. https://arxiv.org/abs/1704.05547
- Noy, N., Rector, A. (eds). *Defining N-ary Relations on the Semantic Web.* W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Luo, H., E, H., Chen, G., et al. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21, 2025. https://doi.org/10.1017/nws.2025.10018
