---
title: Industry adoption and products
type: survey
status: draft
tags: [hypergraph, n-ary, databases, TypeDB, RDF-star, AtomSpace, HypergraphDB, Wikidata, Palantir, industry]
created: 2026-09-20
updated: 2026-09-20
---

# Industry adoption and products

Which shipping products actually let you store a fact with more than two participants, and how? This
note grades the market rather than describing it. The short answer: **native n-ary storage is a
minority position**, the dominant graph databases are binary, and the largest deployed "n-ary" systems
(Wikidata, Freebase-era Google) got there through statement-level qualifiers or intermediate objects
rather than hyperedges.

Maturity legend: **●** shipping, documented, n-ary is a first-class primitive; **◐** shipping, n-ary
possible through a specific mechanism with caveats; **○** research, dormant, or claim not verified here.

| Product / system | n-ary mechanism | Maturity |
|---|---|---|
| TypeDB | relations with named roles, any arity | ● |
| Wikidata / Wikibase | statements with qualifiers | ● |
| OpenCog AtomSpace | typed s-expression Atoms; Links over Links (metagraph) | ◐ |
| RDF 1.2 / RDF-star stacks | triple terms + `rdf:reifies`; n-ary only indirectly | ◐ |
| Stardog edge properties | RDF-star-like, vendor-deprecated for new projects | ○ |
| Palantir Foundry Ontology | link types are between two object types | ○ (binary) |
| Kobrix HypergraphDB | typed, ordered n-ary links | ○ (dormant) |
| RelationalAI | relational/semantic model on Snowflake; no hypergraph claim found | ○ |

## 1. TypeDB — the explicit hypergraph vendor

TypeDB is the only mainstream database that markets n-ary relations as the core differentiator. Its
feature page states the model directly: "Relations can connect any number of entities or attributes
(n-ary, not binary)", roles may be played more than once in a single relation, and the system is
described as having a "hypergraph structure" in which "Relations are first-class citizens in TypeQL and
so can own attributes and play roles in other relations"
([TypeDB features](https://typedb.com/features), checked 2026-09-20). Schemas are strictly typed with
inheritance for entities, relations and attributes.

Its argument to buyers ([Hemsley, 2026](https://typedb.com/blog/the-case-for-a-structured-hypergraph))
is a worked M&A example: one `deal` relation with `target`, `buyer`, `target-advisor` and
`buyer-advisor` roles instead of an intermediate node and four edges, so that conflict-of-interest
checks fall out of the schema. The claim about the competition is that property graphs "force
compromises" because "many meaningful relationships aren't between two things".

What to keep and what to discount. Keep: relations-owning-attributes and relations-playing-roles
together give nesting plus arity, which is genuinely more than "hyperedge". Discount: this is vendor
material, and "hypergraph" here is a structured, typed, role-labelled relation — closer to an ER
relationship type than to the set-of-vertices hyperedge of
[hypergraph-definitions](../01-foundations/hypergraph-definitions.md).

## 2. Wikidata — the largest deployed n-ary knowledge base

Wikidata is, by volume, the most successful n-ary knowledge base in existence, and it is not a
hypergraph database. A statement has a main snak plus *qualifiers*, *references* and a *rank*, so a fact
like "held position X, from date D1 to date D2, replacing person P" is one statement with several
qualifier snaks. Scale, data model details and the Freebase CVT predecessor are documented in
[wikidata-and-freebase-data-models](../02-knowledge-representation/wikidata-and-freebase-data-models.md).

The lesson for product strategy: qualifiers gave n-ary expressivity without requiring a new storage
engine, at the cost of making every consumer implement statement-reification logic. Nearly all
hyper-relational benchmarks (WD50K and descendants) are carved out of this model, so the field's
implicit definition of "n-ary fact" is Wikidata's.

**Google Knowledge Graph heritage.** Freebase used Compound Value Types — anonymous intermediate
objects — to represent n-ary relations, and Google acquired Freebase in 2010 and folded it towards
Wikidata from 2014. The public Knowledge Graph does not expose an n-ary primitive today.
[unverified: no current public documentation of n-ary modelling inside the Google Knowledge Graph was
found in this research run]

## 3. RDF, RDF-star and the standards position

RDF 1.2 (W3C **Candidate Recommendation Snapshot, 7 April 2026**;
[spec](https://www.w3.org/TR/rdf12-concepts/)) adds **triple terms**: an RDF triple may appear as the
object of another triple, with `rdf:reifies` relating a *reifier* to a triple term, and triple terms may
be asserted or unasserted so one can annotate a statement one does not endorse.

The spec is explicit about the limit that matters here: **"Relations that involve more than two entities
can only be indirectly expressed in RDF"**, pointing to the W3C note *Defining N-ary Relations on the
Semantic Web*. So RDF-star solves *statement annotation*, not *n-ary relations*. Conflating the two is
the most common error in this space; see
[n-ary-relations-and-reification](../02-knowledge-representation/n-ary-relations-and-reification.md).

Vendor reality check: Stardog has supported edge properties since version 7.1, with `<< :s :p :o >>
:since 2010` syntax — but its own documentation now says the feature "is based on early RDF*/SPARQL*
research proposals and does not implement the later RDF 1.2 and SPARQL 1.2 working drafts. It also has
several known performance problems and is not recommended for new Knowledge Graph projects", with
further limits (only subjects may be triples, no nesting, an "abort on conflict" write strategy that is
problematic in a cluster) ([Stardog docs](https://docs.stardog.com/query-stardog/edge-properties),
checked 2026-09-20). Notably, Stardog's docs describe *n-ary relations as the alternative* to edge
properties — relation-as-node plus ordinary triples — which is precisely reification.
[unverified: current RDF-star support status in Ontotext GraphDB, Amazon Neptune, Blazegraph and
Virtuoso was not confirmed in this research run]

## 4. Palantir Foundry — binary by definition

Foundry's Ontology documents three primitives: an **object type** is "the schema definition of a
real-world entity or event"; a **link type** is "the schema definition of a relationship **between two
object types**"; an **action type** is "the schema definition of a set of changes or edits to objects,
property values, and links that a user can take at once"
([Palantir docs](https://palantir.com/docs/foundry/ontology/core-concepts/), checked 2026-09-20).

Link types are therefore binary. Multi-party events are modelled as object types (an *event* object with
several links), i.e. reification by another name — the same pattern as Freebase CVTs. This is worth
recording precisely because Foundry is the most prominent enterprise "ontology" product: the market
leader in enterprise semantic modelling ships a binary link primitive.

## 5. Kobrix HypergraphDB

HyperGraphDB is the long-standing open-source attempt at a general hypergraph store: "a general purpose,
extensible, portable, distributed, embeddable, open-source data storage mechanism", written in Java and
distributed under Apache-2.0 ([hypergraphdb/hypergraphdb](https://github.com/hypergraphdb/hypergraphdb)),
originally from Kobrix Software ([hypergraphdb.org](http://hypergraphdb.org/), copyright notice dated
2010). Its design points — typed, ordered links that may themselves be link targets — are exactly what
a knowledge hypergraph store needs.

Status is the problem. The project site still carries a 2010 copyright, and the repository shows a
little over a thousand commits.
[unverified: the latest release version and date, and the date of the most recent commit, were not
retrievable in this research run] Treat it as a reference design rather than a deployment candidate
until that is checked.

## 6. RelationalAI

RelationalAI is frequently cited in discussions of relational knowledge graphs because a relational
model admits relations of arbitrary arity by construction. As of 2026-09-20 its public site markets a
"decision intelligence platform" and a semantic model over data in Snowflake, with graph, rules-based,
predictive and prescriptive reasoning ([relational.ai](https://relational.ai/)). **No claim about
hypergraphs, n-ary relations or arity appears in that public material.** The arity argument for
relational-model knowledge graphs is sound in principle — an n-ary fact is a row in an n-column
relation — but this research run found no vendor statement making it.

## 7. Where this leaves a practitioner

1. If you need role-labelled n-ary facts with a schema, TypeDB is the only product that offers them as
   a first-class primitive; budget for a smaller ecosystem.
2. If you need statement-level provenance or annotation, that is RDF-star / RDF 1.2 territory, and you
   should read the spec's own warning that n-ary is still indirect.
3. If you are on a property-graph or enterprise-ontology platform, you will reify — either as an event
   object (Palantir-style) or as a CVT-style intermediate node. Do it explicitly and consistently, and
   record the role names, because that is what downstream consumers will need.
4. The largest working example of the qualifier approach is Wikidata; the largest working example of the
   intermediate-object approach was Freebase. Both work. Neither is a hypergraph database.

Related: [finance-legal-and-compliance](finance-legal-and-compliance.md) for the domains where vendors
pitch this hardest, and [ai-agents-memory-and-planning](ai-agents-memory-and-planning.md) for AtomSpace.

## Sources

- TypeDB. *Features*, checked 2026-09-20. https://typedb.com/features
- Hemsley, C. *Graph databases, complex data, and the case for a structured hypergraph.* TypeDB blog, 5 March 2026. https://typedb.com/blog/the-case-for-a-structured-hypergraph
- W3C. *RDF 1.2 Concepts and Abstract Syntax*, Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- Noy, N., Rector, A. (eds). *Defining N-ary Relations on the Semantic Web.* W3C Working Group Note, 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Stardog. *Edge Properties* documentation, checked 2026-09-20. https://docs.stardog.com/query-stardog/edge-properties
- Palantir. *Ontology core concepts* documentation, checked 2026-09-20. https://palantir.com/docs/foundry/ontology/core-concepts/
- HyperGraphDB repository, GitHub, checked 2026-09-20. https://github.com/hypergraphdb/hypergraphdb
- Kobrix Software. *HypergraphDB* project site, checked 2026-09-20. http://hypergraphdb.org/
- OpenCog. *AtomSpace* repository and README, GitHub, checked 2026-09-20. https://github.com/opencog/atomspace
- RelationalAI. Company site, checked 2026-09-20. https://relational.ai/
- Wikidata. *Wikidata:Statistics*, figures dated 31 August 2025. https://www.wikidata.org/wiki/Wikidata:Statistics
