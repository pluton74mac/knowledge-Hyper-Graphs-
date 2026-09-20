---
title: N-ary relations and reification in RDF, RDF-star / RDF 1.2 and property graphs
type: survey
status: draft
tags: [n-ary, reification, rdf, rdf-star, rdf-1.2, named-graphs, singleton-property, property-graph, w3c]
created: 2026-09-19
updated: 2026-09-19
---

# N-ary relations and reification

Binary graph models (RDF triples, labeled property graph edges) cannot state a fact about more
than two things, nor a fact about a fact, without a workaround. Every workaround is a way of
turning a hyperedge into a node plus binary edges. This note catalogues those workarounds in the
order they appeared, with the status of each as of September 2026, and closes with what a
knowledge hypergraph gains by not needing them.

## 1. RDF reification (1999/2004, still in RDF 1.1)

RDF ships a vocabulary for talking about triples: "rdf:Statement is an instance of rdfs:Class. It is
intended to represent the class of RDF statements. An RDF statement is the statement made by a
token of an RDF triple", with rdf:subject, rdf:predicate and rdf:object as its three properties
([RDF Schema 1.1, W3C Recommendation, 2014](https://www.w3.org/TR/rdf-schema/)). Its semantics
is deliberately weak: "A reification of a triple does not entail the triple, and is not entailed by it.
... The reification only says that the triple token exists and what it is about, not that it is true"
([RDF 1.1 Semantics, W3C Recommendation, 2014](https://www.w3.org/TR/rdf11-mt/)).

Costs: four triples per reified statement, and no formal link between the reification and the
asserted triple. Nguyen et al. summarise: "The reification approach requires four additional triples
for representing one statement per document as a resource. This would increase the size of the
data sets by at least four times", and "The lack of formal semantics connecting a statement and
the resource describing it is one of the main drawbacks"
([Nguyen, Bodenreider and Sheth, 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4350149/)).

## 2. The W3C n-ary relations note (2006): the relation-instance pattern

*Defining N-ary Relations on the Semantic Web* is a W3C Working Group Note of 12 April 2006
edited by Natasha Noy and Alan Rector ([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)).
It distinguishes three use cases and two patterns:

- **Use case 1**: the relation needs extra attributes ("Christine has breast tumor with high
  probability").
- **Use case 2**: several aspects of one relation ("Steve's temperature is high but falling").
- **Use case 3**: no distinguished participant (a purchase with buyer, seller, object, amount,
  purpose).
- **Pattern 1**: introduce a class for the relation; each n-ary fact becomes an individual of that
  class with one property per participant. This is the "relation instance" or "intermediate node"
  pattern and is exactly the incidence-graph encoding of a hyperedge.
- **Pattern 2**: use an ordered list (e.g. a flight visiting airports in order) with explicit successor
  links rather than the RDF collection vocabulary.

The note recommends blank nodes for relation instances when identical arguments should be
treated as the same instance, and lists the drawbacks: maintenance burden, the need for subclass
hierarchies to express constraints on role combinations, and the awkwardness of inverses. It also
says explicitly that this pattern is *not* RDF reification: it describes relation instances, not
statements about statements ([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)).
Use case 3 is the case that the hyper-relational formalisation handles badly and the n-ary tuple
formalisation handles well; see
[hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md).

## 3. Named graphs (2005) and RDF 1.1 datasets (2014)

Carroll, Bizer, Hayes and Stickler proposed *named graphs*, sets of triples identified by a URI, as
a mechanism for provenance and trust ([Carroll et al., 2005](https://dl.acm.org/doi/10.1145/1060745.1060835),
WWW 2005; journal version in *Journal of Web Semantics* 3(4), 2005). RDF 1.1 adopted the syntax:
"An RDF dataset is a collection of RDF graphs, and comprises: Exactly one default graph ... Zero
or more named graphs. Each named graph is a pair consisting of an IRI or a blank node (the graph
name), and an RDF graph" ([RDF 1.2 Concepts, 2026](https://www.w3.org/TR/rdf12-concepts/),
carrying forward the RDF 1.1 definition). RDF 1.1 gave named graphs no formal semantics
([Wikipedia, Named graph](https://en.wikipedia.org/wiki/Named_graph)). Serialisations: TriG,
N-Quads, TriX.

Named graphs attach context to a *set* of triples, so they model "this group of facts comes from
source S" well, and "this fact holds from 1980 to 1985" badly unless every fact gets its own graph.
Nanopublications do exactly that: each nanopublication is an assertion graph plus a provenance
graph plus a publication-info graph ([Groth, Gibson and Velterop, 2010](https://dl.acm.org/doi/10.5555/1883685.1883690)).
See [directed-and-typed-hyperedges-for-knowledge.md](directed-and-typed-hyperedges-for-knowledge.md)
for graphs-as-hyperedges.

## 4. Singleton Property (2014)

Nguyen, Bodenreider and Sheth proposed minting one property per statement: "A singleton
property is a property instance representing one specific relationship between two particular
entities under one specific context", linked to its generic property by rdf:singletonPropertyOf,
so that a marriage reported in two sources becomes isMarriedTo#1 and isMarriedTo#2. This needs
one extra triple per statement rather than four, and stays inside RDF/RDFS semantics
([Nguyen, Bodenreider and Sheth, 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4350149/), WWW 2014).
Its cost is an explosion of property IRIs and unfriendliness to SPARQL property paths and to
stores that index by predicate.

## 5. RDF-star (Community Group, 2021) and RDF 1.2 (W3C, 2024–2026)

The RDF-star Community Group's *RDF-star and SPARQL-star* Final Community Group Report of
17 December 2021 (editors Hartig, Champin, Kellogg, Seaborne) introduced the **quoted triple**:
"An RDF-star triple used as the subject or object of another RDF-star triple is called a quoted
triple", with the warning that "RDF-star is not syntactic sugar for standard reification. While the
latter is a vocabulary that fits into the standard RDF model (abstract syntax), RDF-star extends
that model with a new construct, namely quoted triples", and that quoted triples are unique
("wherever << :employee38 :jobTitle "Assistant Designer" >> appears, it always denotes one and
the same thing") ([RDF-star CG report, 2021](https://w3c-cg.github.io/rdf-star/cg-spec/2021-12-17.html)).

The W3C **RDF & SPARQL Working Group** (chairs Adrian Gschwend and Ora Lassila; staff contact
Pierre-Antoine Champin) took this over, with the mission to "update and maintain the set of RDF
and SPARQL related recommendations, extending them with the ability to concisely represent and
query statements about statements"; its charter runs to 30 April 2027
([W3C RDF & SPARQL WG page](https://www.w3.org/groups/wg/rdf-star/), checked 2026-09-19).
The design changed on the way to RDF 1.2:

- **Triple terms**: "An RDF triple used as the object of another triple is called a triple term."
  Triple terms appear only in object position (in the non-generalized model).
- **Reifiers**: "A reifying triple is a triple where the predicate is rdf:reifies and the object is a
  triple term." A reifier "may denote a variety of things that are related to the triple term's
  proposition, such as a statement or belief that the proposition holds", and "One reifier may also
  be used to reify multiple, distinct propositions".
- **Non-assertion**: triple terms are not asserted; "By using non-asserted triple terms ... one can
  make statements about unasserted statements".
- Status: *RDF 1.2 Concepts and Abstract Data Model*, W3C Candidate Recommendation Snapshot,
  7 April 2026 ([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)).

Turtle 1.2 gives the surface syntax: triple terms `<<( s p o )>>`, reifiers `<< s p o ~ :r >>`, and the
annotation form that asserts and reifies at once, e.g. `:alice :name "Alice" ~ :t {| :statedBy :bob |} .`
([RDF 1.2 Turtle, W3C Working Draft, 14 September 2026](https://www.w3.org/TR/rdf12-turtle/)).
SPARQL 1.2 Query (Working Draft, 13 September 2026) supports triple terms in patterns, with a
"1.2-basic" conformance level that excludes nested triple patterns
([SPARQL 1.2 Query](https://www.w3.org/TR/sparql12-query/)).

**Reading for KHG purposes.** A reifier is a node that stands for an *occurrence* of a proposition;
qualifiers hang off the reifier; the same reifier can group several triple terms. This is structurally
a Wikidata statement node (see [wikidata-and-freebase-data-models.md](wikidata-and-freebase-data-models.md))
and structurally a hyperedge whose members are the triple term plus its qualifier values. What RDF 1.2
does *not* give is a first-class n-ary predicate: a purchase(buyer, seller, item, amount) with no
primary pair still needs Pattern 1 of the 2006 note.

## 6. Labeled property graphs

The formal definition of a property graph makes the binary restriction explicit: "ρ : E → (N × N) is a
total function that associates each edge in E with a pair of nodes in N"
([Angles, 2018](https://ceur-ws.org/Vol-2100/paper26.pdf), AMW 2018). Edge properties give a
built-in place for qualifiers on a *binary* edge (start date on an employment edge), which is why
property graphs handle Wikidata-style qualifiers on a triple more directly than RDF 1.1 did. But
three or more participants still need an intermediate node. Neo4j's own modelling guide says so:
"In a mathematical graph, this can be solved with a hyperedge, i.e. a relationship that connects
more than two nodes. This is not supported in Neo4j", and recommends intermediate nodes such as
an "employment event" linking person, company and role
([Neo4j, Modeling designs](https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/),
checked 2026-09-19). The ISO standard GQL (ISO/IEC 39075:2024, published 12 April 2024) is a
property-graph language and inherits the binary edge model
([ISO/IEC 39075:2024](https://www.iso.org/standard/76120.html);
[Wikipedia, Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language)).
TypeDB's n-ary relations are the main commercial counter-proposal; see
[ontologies-and-schemas-for-n-ary-knowledge.md](ontologies-and-schemas-for-n-ary-knowledge.md).

## 7. Cost comparison

| Mechanism | Extra triples/edges per qualified binary fact | Handles n>2 with no primary pair | Formal semantics for the link fact↔metadata | Status (2026-09) |
|---|---|---|---|---|
| RDF reification | 4 ([Nguyen et al., 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4350149/)) | via Pattern 1, not via reification | none: "does not entail the triple" ([RDF 1.1 Semantics](https://www.w3.org/TR/rdf11-mt/)) | Recommendation, legacy |
| N-ary note Pattern 1 | 1 node + n edges | yes | ordinary RDF/OWL semantics on the instance | Note, 2006 |
| Named graphs | 1 graph name per context | groups facts, not participants | none in RDF 1.1 | Recommendation 2014 |
| Singleton property | 1 | no | RDFS semantics | proposal, 2014 |
| RDF-star (CG) | 0 (quoted triple is a term) | no | CG report | superseded by RDF 1.2 |
| RDF 1.2 triple terms + reifiers | 1 (rdf:reifies) plus qualifiers | no | defined in RDF 1.2 Semantics | Candidate Recommendation, April 2026 |
| Property graph edge properties | 0 for binary; intermediate node for n>2 | no | none (GQL is a language standard) | ISO/IEC 39075:2024 |
| Freebase CVT | "more than six facts" for one qualified statement ([Pellissier Tanon et al., 2016](https://dl.acm.org/doi/10.1145/2872427.2874809)) | yes | none | discontinued 2016 |
| Native hyperedge (KHG) | 0 | yes | depends on the model | research / TypeDB / HyperGraphDB |

Pellissier Tanon et al. quantify the inflation: re-encoding Wikidata "as if they were Freebase facts,
i.e., by removing sources, representing statements with qualifiers using CVTs, and adding reverse
properties, this would lead to a number of 110 million facts, i.e. an increase of 167% over the raw
number of statements" ([Pellissier Tanon et al., 2016](https://dl.acm.org/doi/10.1145/2872427.2874809)).

## 8. What a native hypergraph model changes

1. The hyperedge is already an addressable object, so "reification" is free: HyperGraphDB's
   phrase is that the generalised model "automatically reifies every entity expressed in the
   database" ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)).
2. Roles are part of the schema instead of being reconstructed from property names on an
   intermediate node.
3. The remaining open question is the one RDF 1.2 also faced: is a qualifier *part of* the fact or
   *about* the fact? RDF 1.2 chose "about" (non-asserted triple terms, reifiers as occurrences);
   the n-ary tuple model chose "part of". A KHG schema has to pick, or represent both; see
   [knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md).

## Sources

- W3C. *RDF Schema 1.1.* W3C Recommendation, 25 February 2014. https://www.w3.org/TR/rdf-schema/
- W3C. *RDF 1.1 Semantics.* W3C Recommendation, 25 February 2014. https://www.w3.org/TR/rdf11-mt/
- Noy, N., Rector, A. (eds). *Defining N-ary Relations on the Semantic Web.* W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Carroll, J. J., Bizer, C., Hayes, P., Stickler, P. *Named Graphs, Provenance and Trust.* WWW 2005; Journal of Web Semantics 3(4):247–267, 2005. https://dl.acm.org/doi/10.1145/1060745.1060835
- Wikipedia. *Named graph.* https://en.wikipedia.org/wiki/Named_graph
- Groth, P., Gibson, A., Velterop, J. *The anatomy of a nanopublication.* Information Services & Use 30(1-2):51–56, 2010. DOI 10.3233/ISU-2010-0613. https://dl.acm.org/doi/10.5555/1883685.1883690
- Nguyen, V., Bodenreider, O., Sheth, A. *Don't Like RDF Reification? Making Statements about Statements Using Singleton Property.* WWW 2014. https://pmc.ncbi.nlm.nih.gov/articles/PMC4350149/
- Hartig, O., Champin, P.-A., Kellogg, G., Seaborne, A. (eds). *RDF-star and SPARQL-star.* W3C Final Community Group Report, 17 December 2021. https://w3c-cg.github.io/rdf-star/cg-spec/2021-12-17.html
- W3C RDF & SPARQL Working Group. Group page, checked 2026-09-19. https://www.w3.org/groups/wg/rdf-star/
- W3C. *RDF 1.2 Concepts and Abstract Data Model.* Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. *RDF 1.2 Turtle.* Working Draft, 14 September 2026. https://www.w3.org/TR/rdf12-turtle/
- W3C. *SPARQL 1.2 Query Language.* Working Draft, 13 September 2026. https://www.w3.org/TR/sparql12-query/
- Angles, R. *The Property Graph Database Model.* AMW 2018, CEUR-WS Vol. 2100. https://ceur-ws.org/Vol-2100/paper26.pdf
- Neo4j. *Modeling designs* (Getting Started guide), checked 2026-09-19. https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/
- ISO/IEC. *ISO/IEC 39075:2024 Information technology — Database languages — GQL.* 2024. https://www.iso.org/standard/76120.html
- Wikipedia. *Graph Query Language.* https://en.wikipedia.org/wiki/Graph_Query_Language
- Pellissier Tanon, T., Vrandečić, D., Schaffert, S., Steiner, T., Pintscher, L. *From Freebase to Wikidata: The Great Migration.* WWW 2016. https://dl.acm.org/doi/10.1145/2872427.2874809
- Iordanov, B. *HyperGraphDB: A Generalized Graph Database.* WAIM 2010 workshops. https://hypergraphdb.org/docs/hypergraphdb.pdf
