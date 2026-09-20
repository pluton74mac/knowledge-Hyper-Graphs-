---
title: The vendor debate on n-ary relations — property graphs, TypeDB, RDF-star
type: comparison
status: draft
tags: [neo4j, typedb, rdf-star, rdf-1.2, property-graph, kuzu, vendor, marketing, fact-check, n-ary, reification]
created: 2026-09-20
updated: 2026-09-20
---

# Property graph vs. TypeDB vs. RDF-star: the n-ary argument, fact-checked

Three camps sell three answers to "how do I record a fact about more than two things?". The
technical content of the disagreement is much smaller than the rhetoric suggests, and most of the
real differences are about **schema enforcement and query ergonomics**, not expressivity. This note
states each camp's position in its own words, then checks the claims.

Background on the mechanisms themselves is in
[../02-knowledge-representation/n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md);
the information-theoretic question is in
[hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md).

---

## 1. The property-graph camp: "reify it as a node, and that's fine"

Neo4j does not claim to support hyperedges and never has. Its documentation is direct: a hyperedge
"is not supported in Neo4j but can be solved by using an intermediary node", and the recommended
model replaces the edge with an event node — "instead of saying Patrick works at company Acme,
Patrick has an **employment event**, which becomes a new node. The employment event holds the
employment start and end dates, and logically relates to the other three nodes"
([Neo4j, Modeling designs](https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/),
checked 2026-09-20).

The community framing has been stable since at least 2013. Mark Needham, then at Neo4j, wrote that
because relationships connect two nodes you must "introduce an extra node which links the match,
player and team together", and argued the constraint is a feature: the intermediate node surfaces a
concept — a player's performance in a match — that was implicit before
([Needham, 22 Oct 2013](https://www.markhneedham.com/blog/2013/10/22/neo4j-modelling-hyper-edges-in-a-property-graph/)).

The standards body agreed with them. GQL became ISO/IEC 39075:2024 on 12 April 2024, and it
standardises the *property graph* model; per its Wikipedia summary it "does not include n-ary
relationships linking more than two entities" ([Wikipedia, Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language),
checked 2026-09-20 — the ISO text is paywalled and was not consulted `[unverified]`). So in 2024 the
graph-database industry ratified the binary edge rather than relaxing it.

**Position in one line:** n-ary facts are events; events are nodes; nodes are cheap.

## 2. The TypeDB camp: "n-ary relations are primitive, and here is a schema to keep them honest"

TypeDB's product page states that "TypeDB data structure can be seen as a hypergraph", that
"Relations can connect any number of entities or attributes (n-ary, not binary)", that
"Construct rich data representations by directly implementing unary, binary, ternary, and n-ary
relations in your conceptual model", and that "Relations are first-class citizens in TypeQL and so
can own attributes and play roles in other relations just like entities"
([TypeDB, Features](https://typedb.com/features), checked 2026-09-20). TypeDB 3 calls its model
PERA — polymorphic entity–relation–attribute.

The current long-form argument is a blog post by Cal Hemsley, 5 March 2026, quoted here verbatim as
rendered on 2026-09-20:

> "The property graph model has this binary constraint baked into its foundations: every edge
> connects exactly two nodes."
> "But for domains where relationships naturally involve more than two participants, it means every
> data model is a compromise."
> "A hypergraph generalizes the graph model by removing the two-node constraint."
> "In a hypergraph, an edge (called a hyperedge) can connect any number of nodes."
> "TypeDB trades off the simplicity of a binary edge for the expressive power of n-ary relations."
> ([Hemsley, 2026](https://typedb.com/blog/the-case-for-a-structured-hypergraph))

The post is unusually fair for vendor content. It concedes: "The graph ecosystem is mature in a way
TypeDB's isn't yet"; "Property graphs are largely schema-optional, which means you can start with a
rough model and let it evolve organically"; and "For teams operating in well-understood territory
with existing graph expertise, that weight counts for something"
([Hemsley, 2026](https://typedb.com/blog/the-case-for-a-structured-hypergraph)).

**Position in one line:** the intermediate node is a workaround the database does not understand;
make the n-ary relation a typed primitive instead.

## 3. The RDF camp: "reification was always there; RDF 1.2 makes it ergonomic"

RDF has had `rdf:Statement` since 1999/2004 and a dedicated n-ary pattern since 2006
([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)). RDF-star, now landing as
RDF 1.2, adds *triple terms*. As of 7 April 2026, RDF 1.2 Concepts and RDF 1.2 Semantics are W3C
Candidate Recommendations ([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)); the Primer
was a Group Note draft of 17 September 2026 ([RDF 1.2 Primer](https://www.w3.org/TR/rdf12-primer/)).

Two sentences from the specs do most of the work:

> "An RDF triple used as the object of another triple is called a triple term."
> ([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/))

> "Triple terms are used to *relate* to propositions, not to state them. This means that we can
> describe statements without implying them."
> ([RDF 1.2 Primer](https://www.w3.org/TR/rdf12-primer/))

**Position in one line:** what you actually want is to annotate statements, and that is now a
first-class RDF construct.

---

## 4. Fact-checking the claims

### Claim A — "Property graphs cannot represent n-ary relations." **Misleading.**

They cannot represent them as a *primitive*. They can represent them exactly, losslessly, with an
intermediate node — which is precisely the incidence (bipartite) encoding of a hyperedge, and the
incidence encoding is a bijection
([Aksoy et al., 2020](https://arxiv.org/abs/1906.11295); see
[hypergraph-vs-bipartite-graph-debate.md](hypergraph-vs-bipartite-graph-debate.md) §1). Hemsley's
own wording is careful — "every data model is a compromise", not "cannot be modelled" — but the
weaker claim is routinely read as the stronger one.

What is genuinely lost in the property-graph encoding is not information but **enforcement**:
nothing in an untyped LPG stops a query from traversing *through* a reified fact node as if it were
an entity, stops a fact node from acquiring a fourth `:ADVISOR` edge when the schema says at most
one, or stops two modellers from choosing different intermediate-node shapes for the same domain.
That is a real cost. It is a typing cost.

### Claim B — "TypeDB is a hypergraph database." **Defensible but imprecise; note the hedge.**

TypeDB's own features page says "can be seen as a hypergraph", not "is a hypergraph"
([TypeDB, Features](https://typedb.com/features), checked 2026-09-20). The hedge is appropriate. A
TypeDB relation binds *named roles* to players; a hypergraph in the classical sense (Berge, and the
whole higher-order network literature) is a family of *unlabelled subsets*. Almost no result from
hypergraph combinatorics — degree sequences, transversals, spectra, `s`-walks, hypergraph modularity
— transfers to a role-labelled relation without extra work, because those results are stated for
set systems. Calling a role-based relational store a hypergraph is closest to Wen et al.'s
formalisation, in which "a multi-fold relation … on N with roles M is a subset of N^M", i.e. an
instance is a function from roles to entities ([Wen et al., 2016](https://www.ijcai.org/Proceedings/16/Papers/188.pdf))
— and Wen et al. introduced that definition *precisely because* they thought the plain set/tuple
definition was inadequate: the algebraic n-ary relation "is incomplete, in the sense that the role of
each coordinate in the cartesian product is not specified".

So the accurate statement is: **TypeDB relations are role-labelled n-ary relation instances; the
hypergraph is an analogy, and the analogy imports none of the mathematics.** For KB purposes this is
definition (a)/role-based in
[../02-knowledge-representation/what-is-a-knowledge-hypergraph.md](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md),
not the Battiston-style hypergraph of higher-order network science.

### Claim C — "First-class relationships eliminate the need for JOINs from SQL." **Marketing.**

Taken from [TypeDB, Features](https://typedb.com/features) (checked 2026-09-20). The join is not
eliminated; it is pre-materialised as adjacency, exactly as in any graph database's index-free
adjacency story. The work moves from query time to write time and to storage. The claim is a
statement about *syntax* (you do not write `JOIN`) dressed as a statement about *cost*. Benchmark
before believing any version of it; TypeDB's own benchmark posts are vendor-run
`[unverified — I did not review TypeDB's published benchmarks in this run]`.

### Claim D — "RDF-star solves the n-ary problem." **False.**

RDF-star/RDF 1.2 adds statements *about a statement*. It does not add a construct for a relation over
k entities. RDF 1.2 Concepts says so in its own text: "Relations that involve more than two entities
can only be indirectly expressed in RDF", with a cross-reference to the 2006 n-ary relations note
([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/), W3C CR, 7 April 2026). Two decades after
the n-ary note, the recommended answer for genuine n-ary relations is still the relation-instance
pattern.

Whether this is a *gap* depends on your fact shape:

| Fact shape | RDF 1.2 handles it | Notes |
|---|---|---|
| Binary fact + provenance/time/confidence | **Yes, well** | This is what triple terms were designed for |
| Binary fact + qualifiers that narrow it (Wikidata style) | Yes | Wikidata's statement model predates and motivated it |
| Symmetric multi-party fact with no natural subject (a purchase: buyer, seller, item, price, date) | **No** — relation-instance pattern required | W3C's own use case 3 ([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)) |
| Fact about a fact about a fact | Yes (nested triple terms) | |

### Claim E — "Hyper-relational is the same as n-ary." **False, and the confusion is load-bearing.**

The StarE authors argued the distinction explicitly:

> "We deem hyper-relational graphs and hypergraphs are conceptually different. As hyperedges contain
> multiple nodes, such hyperedges are closer to n-ary relations r(e1, …, en) with one abstract
> relation. The attribution of entities to the main triple or qualifiers is lost, and qualifying
> relations are not defined. Combining a certain set of main and qualifying relations into one
> abstract rk() would lead to a combinatorial explosion of typed hyperedges since, in principle, any
> relation could be used in a qualifier, and there the amount of qualifiers per fact is not limited."
> ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847))

That combinatorial-explosion argument is the strongest technical case *against* the positional-KHG
model and *for* the RDF-star/Wikidata model, and it is rarely engaged with by the hypergraph side.
See [open-debates.md](open-debates.md) §2.

### Claim F — hierarchies of expressivity in circulation. **Treat with caution.**

A 2026 preprint proposes an "Equivalence Theorem" with a strict ranking SQL < LPG < TypeDB < ATCH
(attributed temporal causal hypergraph), claiming four "mutually entailing" capabilities and a
Lean 4 formalisation ([arXiv:2603.13603](https://arxiv.org/pdf/2603.13603); abstract only consulted
`[unverified]`). Claims of this shape need care: expressivity orderings depend entirely on what is
held fixed (primitive constructs? queries expressible in a fixed language? data complexity?), and a
ranking that places a specific commercial product in the middle of a mathematical hierarchy is a
red flag until the definitions are checked. Recorded here because it is circulating, not because it
is endorsed.

---

## 5. Tooling risk: a concrete 2025 example

Kùzu, a widely recommended embedded property-graph database ("an embedded graph database built for
query speed and scalability", property-graph model, Cypher), was **archived by its owner on
10 October 2025**: "This repository was archived by the owner on Oct 10, 2025. It is now read-only"
([kuzudb/kuzu](https://github.com/kuzudb/kuzu), checked 2026-09-20). Existing releases keep working
and docs moved to a GitHub Pages site, but the project as a maintained upstream ended.

The lesson generalises past any one vendor. When you choose a formalism that only one implementation
supports, you have coupled your data model to a company. RDF and SQL survive their vendors because
the model is standardised and multiply implemented; positional knowledge hypergraphs, TypeQL and
Atomese currently do not have that property. See
[limitations-and-failure-modes.md](limitations-and-failure-modes.md) §11.

---

## 6. What the argument is actually about

Strip the marketing and three genuine differences remain.

1. **Where the role structure lives.** In an LPG it lives in edge *type names* on an intermediate
   node and in the heads of the team. In TypeDB it lives in the schema and is checked. In RDF it
   lives in an ontology and is checked by OWL/SHACL if you run them.
2. **Whether a fact is a first-class citizen.** In RDF 1.2, propositions are addressable but
   deliberately unasserted. In TypeDB, relations can own attributes and play roles. In an LPG a
   reified fact is an ordinary node with no special status.
3. **How much ecosystem you are giving up.** This is the dimension vendors minimise and users feel:
   query-language standardisation, drivers, hiring, BI connectors, hosted offerings, and the odds
   that the project still exists in five years.

**Recommendation for this KB's purposes.** Model n-ary facts as role-typed relation instances. Choose
the store by ecosystem, not by whether its marketing says "hypergraph". If you need schema
enforcement on roles and can accept single-vendor risk, TypeDB is the only mainstream product that
gives it natively. If you need federation, standards and longevity, use RDF with the relation-instance
pattern and RDF 1.2 triple terms for annotations. If you need neither, an LPG with a disciplined
event-node convention is not a compromise worth agonising over — it is the same graph, drawn
differently.

## Sources

- Aksoy, S., Joslyn, C., Ortiz Marrero, C., Praggastis, B., Purvine, E. "Hypernetwork science via high-order hypergraph walks." *EPJ Data Science* 9(1):16, 2020. https://arxiv.org/abs/1906.11295
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. "Message Passing for Hyper-Relational Knowledge Graphs." EMNLP 2020. https://arxiv.org/abs/2009.10847
- Hemsley, C. "Graph databases, complex data, and the case for a structured hypergraph." TypeDB blog, 5 March 2026. https://typedb.com/blog/the-case-for-a-structured-hypergraph (checked 2026-09-20)
- kuzudb/kuzu repository (archived 10 October 2025). https://github.com/kuzudb/kuzu (checked 2026-09-20)
- Needham, M. "Neo4j: Modelling hyper edges in a property graph." 22 October 2013. https://www.markhneedham.com/blog/2013/10/22/neo4j-modelling-hyper-edges-in-a-property-graph/
- Neo4j. "Modeling designs." Neo4j Getting Started documentation. https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/ (checked 2026-09-20)
- Noy, N., Rector, A. (eds.). "Defining N-ary Relations on the Semantic Web." W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- TypeDB. "Features." https://typedb.com/features (checked 2026-09-20)
- "The Equivalence Theorem: First-Class Relationships for Structurally Complete Database Systems." arXiv:2603.13603 (abstract only consulted). https://arxiv.org/pdf/2603.13603
- W3C. "RDF 1.2 Concepts and Abstract Data Model." W3C Candidate Recommendation, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. "RDF 1.2 Primer." W3C Group Note Draft, 17 September 2026. https://www.w3.org/TR/rdf12-primer/
- Wen, J., Li, J., Mao, Y., Chen, S., Zhang, R. "On the Representation and Embedding of Knowledge Bases beyond Binary Relations." IJCAI 2016. https://www.ijcai.org/Proceedings/16/Papers/188.pdf
- Wikipedia. "Graph Query Language." https://en.wikipedia.org/wiki/Graph_Query_Language (checked 2026-09-20)
