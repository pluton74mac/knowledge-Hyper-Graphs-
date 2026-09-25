---
title: Query languages for knowledge hypergraphs
type: survey
status: draft
tags: [query-language, sparql, sparql-1.2, rdf-1.2, typeql, typedb, cypher, gql, gremlin, datalog, metta, hyperon, hypergraphdb, conjunctive-queries, hypertree-decomposition, complexity, reification]
created: 2026-09-20
updated: 2026-09-25
---

# Query languages for knowledge hypergraphs

There is **no standard query language for knowledge hypergraphs**. What exists, as of September 2026, is
four different things that people use instead:

1. **Binary-graph languages with a reification workaround** — SPARQL, Cypher/GQL, Gremlin. The hyperedge
   is encoded as a node; the query language never sees the hyperedge.
2. **Languages whose data model is natively n-ary** — TypeQL, Datalog and its descendants, SQL.
   The n-ary fact is a first-class pattern; what they usually lack is hypergraph-*native* operators
   (s-walks, hyperpaths, incidence traversal).
3. **Statement-annotation languages** — SPARQL 1.2 over RDF 1.2 triple terms. These make the
   *hyper-relational* shape (a triple plus qualifiers) queryable, which is a proper subset of the
   n-ary case.
4. **Metagraph rewriting / programmatic APIs** — MeTTa over the Hyperon Atomspace, the HypergraphDB
   Java API. These are hypergraph-native but are programming interfaces rather than declarative
   query languages with an optimiser.

The formalism you chose in
[what-is-a-knowledge-hypergraph.md](../02-knowledge-representation/what-is-a-knowledge-hypergraph.md)
determines which of these is even expressible; see also
[n-ary-relations-and-reification.md](../02-knowledge-representation/n-ary-relations-and-reification.md)
for the encodings themselves.

---

## 1. SPARQL 1.1: n-ary facts through an intermediate node

SPARQL 1.1 is a query language over triples ([SPARQL 1.1 Query Language, W3C Recommendation,
2013](https://www.w3.org/TR/sparql11-query/)). An n-ary fact must first be reified into an
intermediate resource, and the query then has to enumerate every role explicitly:

```sparql
# "Who studied what, where, for which degree?" — W3C n-ary relation pattern 1
SELECT ?person ?institution ?degree ?major WHERE {
  ?e a :Education ;
     :student     ?person ;
     :institution ?institution ;
     :degree      ?degree ;
     :major       ?major .
}
```

Three consequences follow, and they are the practical reason people look past SPARQL:

- **Arity is hard-coded in the query.** A fact with an extra role is either missed (if the query
  demands all roles) or silently matched (if it does not). There is no "match a hyperedge with
  *at least* these participants" primitive, as TypeQL has (§3).
- **The hyperedge has no identity in the algebra.** `?e` is an ordinary resource; nothing in SPARQL
  knows it stands for one fact.
- **Cost.** Every n-ary fact becomes n triples plus a type triple, so a single hyperedge pattern
  becomes an n-way self-join.

## 2. SPARQL 1.2 and RDF 1.2: triple terms, reifiers, annotations

RDF 1.2 adds a fourth kind of RDF term, the **triple term**, usable in the object position of
another triple; a **reifying triple** has predicate `rdf:reifies` and a triple term as object, and the
subject of that triple is called a **reifier** ([RDF 1.2 Concepts and Abstract Data Model, W3C
Candidate Recommendation, 7 April 2026](https://www.w3.org/TR/rdf12-concepts/)). SPARQL 1.2 adds the
matching syntax; the current draft is a [W3C Working Draft of 13 September
2026](https://www.w3.org/TR/sparql12-query/).

The concrete additions relevant here, taken from the SPARQL 1.2 grammar and examples:

| Construct | Grammar (SPARQL 1.2 draft, rules 110–123) | Meaning |
|---|---|---|
| Triple term | `TripleTerm ::= '<<(' TripleTermSubject Verb TripleTermObject ')>>'` | a triple used as a term |
| `TRIPLE(s,p,o)` | function form of `<<( s p o )>>` | build a triple term from expressions |
| `SUBJECT`/`PREDICATE`/`OBJECT`/`isTRIPLE` | §17.4.6 | destructure / test a triple term |
| Reified triple | `ReifiedTriple ::= '<<' ReifiedTripleSubject Verb ReifiedTripleObject Reifier? '>>'` | a triple plus its reifier |
| Reifier | `Reifier ::= '~' VarOrReifierId?` | names the reifier; "can be IRIs, blank nodes, or variables" |
| Annotation block | `AnnotationBlock ::= '{|' PropertyListNotEmpty '|}'` | attach qualifiers to the preceding triple |
| Version directive | `VERSION "1.2"` | announce use of the new syntax |

The specification's own worked example ([SPARQL 1.2 Query Language, §4.3 and
§17.4.6.1](https://www.w3.org/TR/sparql12-query/)):

```sparql
VERSION "1.2"
PREFIX : <http://example/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s ?date {
  ?s ?p ?o .
  BIND( <<( ?s ?p ?o )>> AS ?tt )
  :myreifier rdf:reifies ?tt .
  :myreifier :tripleAdded ?date .
}
```

A syntactic restriction worth knowing: "A reifier or annotation syntax is only permitted after a
triple when the property position is a simple path (an IRI, the keyword `a`, or a variable), and not
for other path expressions" ([SPARQL 1.2 Query Language, W3C Working Draft, 13 September
2026](https://www.w3.org/TR/sparql12-query/)).

**What this buys a knowledge hypergraph, and what it does not.** It makes the *hyper-relational*
formalisation — a primary triple plus qualifier role-value pairs, as in Wikidata — directly
queryable without hand-rolled reification. It does **not** give you a symmetric n-ary fact: a triple
term still has exactly a subject, a predicate and an object, so a 5-ary fact with no distinguished
head and tail (a purchase with buyer, seller, object, amount, purpose) must still pick an arbitrary
primary pair. This is exactly the distinction the n-ary link-prediction literature draws between the
hyper-relational and hyperedge formalisations; see
[knowledge-hypergraph-embedding-models.md](knowledge-hypergraph-embedding-models.md) §2.

## 3. TypeQL (TypeDB): n-ary patterns as a first-class construct

TypeQL is the query language of TypeDB, whose data model has relation types that "may reference (or
'link') zero or more data instances for each associated role type, called their players of that role"
([TypeQL Reference — Data and query model, TypeDB 3.x docs, checked 20 September
2026](https://typedb.com/docs/typeql-reference/data-model/)). Relations are declared with `relates`
and matched with a tuple of role-player pairs. From the TypeDB Academy ([Lesson 7.2: Relation
patterns, checked 20 September 2026](https://typedb.com/docs/academy/7-understanding-query-patterns/7.2-relation-patterns)):

```typeql
binary-relation (role-1: $a, role-2: $b);
ternary-relation (role-1: $a, role-2: $b, role-3: $c);
n-ary-relation (role-1: $a, role-2: $b, role-3: $c, role-4: $d, ...);
unary-relation (role-1: $a);
```

and, with the relation itself bound to a variable,

```typeql
$r isa binary-relation (role-1: $a, role-2: $b);
# or
$r isa binary-relation, links (role-1: $a, role-2: $b);
```

Two properties matter for knowledge hypergraphs:

- **Partial tuples.** "By default, the tuple representation of a relation represents a relation with
  at least the role players described", so omitting a role widens rather than narrows the match.
  The docs are explicit that the two forms differ semantically: including `destination: $address`
  "will only match instances of delivery where there is a roleplayer of destination, while the
  second form can match instances where there is no destination roleplayer at all"
  ([TypeDB Academy 7.2](https://typedb.com/docs/academy/7-understanding-query-patterns/7.2-relation-patterns)).
  This is the "match a hyperedge with at least these participants" primitive SPARQL lacks.
- **Role-player anonymity.** `$relation links ($review-4);` matches any relation in which a given
  instance plays any role — an incidence query, in hypergraph terms.

```typeql
match
$order isa order;
$courier isa courier;
delivery (deliverer: $courier, delivered: $order);
fetch {
  "order-id": $order.id,
  "courier": $courier.name,
};
```

Nullary relations are not permitted and "Relations without role players will be removed (no
'dangling relations')" ([TypeQL Reference — Data and query
model](https://typedb.com/docs/typeql-reference/data-model/)) — i.e. TypeDB enforces that a
hyperedge is a non-empty vertex set.

## 4. Cypher, openCypher and ISO GQL: binary by construction

GQL is an ISO standard for property graphs: **ISO/IEC 39075:2024, *Information technology —
Database languages — GQL***, published 17 April 2024 ([GQL Standards
site](https://www.gqlstandards.org/)). It builds on openCypher, PGQL, GSQL and G-CORE. The property
graph model underlying it is binary: an edge connects exactly one source and one target vertex. An
n-ary fact therefore becomes an **emulated hyperedge**: a "fact node" with one labelled edge per
participant, i.e. the star expansion of the hyperedge.

```cypher
MATCH (e:Education)-[:STUDENT]->(p),
      (e)-[:INSTITUTION]->(i),
      (e)-[:DEGREE]->(d),
      (e)-[:MAJOR]->(m)
RETURN p, i, d, m
```

The costs are the same three as in §1, plus one more: pattern-matching engines optimise for
path-shaped queries, and a hyperedge pattern is star-shaped, so the plan becomes a multi-way join
around the fact node.

## 5. Gremlin / Apache TinkerPop

TinkerPop's structure is "a directed, binary, attributed multi-graph" ([TinkerPop 3.8.2 Reference
Documentation, checked 20 September 2026](https://tinkerpop.apache.org/docs/current/reference/)).
"Binary" here means each edge has one in-vertex and one out-vertex, so **Gremlin has no hyperedge
primitive**. What it does have is multi-properties (a vertex property key with several values) and
meta-properties (properties on a vertex property), and the documentation itself notes that
"Meta-Property can be perceived as the reified statements in an RDF setting"
([TinkerPop Reference Documentation, §Meta-Property
Access](https://tinkerpop.apache.org/docs/current/reference/)). Meta-properties are enough to
annotate a value but not to relate three or more entities symmetrically; the fact-node emulation of
§4 is the standard approach.

## 6. Datalog and n-ary relations

Datalog's atoms are **n-ary by definition** — a rule body is a conjunction of relational atoms of
arbitrary arity, which is exactly a conjunctive query ([Ceri, Gottlob and Tanca, 1989, *IEEE
TKDE*](https://doi.org/10.1109/69.43410)). A knowledge hypergraph in the "labelled tuple"
formalisation is literally a Datalog extensional database:

```prolog
educated(einstein, uni_zurich, phd, physics).

% a role-projection view
alumnus(P, I) :- educated(P, I, _, _).

% a rule over n-ary facts: same institution and same major implies classmate
classmate(P1, P2) :- educated(P1, I, _, M), educated(P2, I, _, M), P1 \= P2.
```

Datalog gives recursion (hence transitive reachability over hyperedges) and a well-understood
complexity picture, but no hypergraph-native operators and no notion of hyperedge identity unless
you add one as an argument. Rule-based reasoning over n-ary facts is treated separately in
[logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md).

## 7. MeTTa and the Hyperon Atomspace

OpenCog Hyperon's central store is the **Atomspace**, "a metagraph comprised of nodes and links with
complex interlinkage structures", labelled with data "including subgraphs"; MeTTa ("Meta Type Talk")
is its language, "a meta-language with very basic and general facilities for handling symbols,
groundings, variables, types, substitutions and pattern matching", where "each MeTTa program [is]
represented as a subgraph of an Atomspace metagraph, and carries out its business centrally by
querying and rewriting portions of Atomspaces" ([Goertzel et al., *OpenCog Hyperon: A Framework for
AGI at the Human Level and Beyond*, arXiv:2310.18318, 2023](https://arxiv.org/abs/2310.18318)).
Querying is unification-based: a match takes a space, a pattern and a template, unifies the pattern
against the space, and instantiates the template for every binding.

Because Atomspace links are themselves n-ary and can take links as arguments, MeTTa is one of the
few systems where *nested* hyperedges are native rather than encoded. What it lacks is a cost-based
optimiser and an agreed benchmark; treat it as a research substrate. The interpreter's evaluation
model is documented in the [minimal MeTTa
specification](https://github.com/trueagi-io/hyperon-experimental/blob/main/docs/minimal-metta.md)
(hyperon-experimental repository, checked 20 September 2026).

## 8. HypergraphDB: an API, not a language

HypergraphDB is a Java database whose atoms are n-ary, ordered links. Its own wiki is candid:
"Unlike other parts of the HyperGraphDB, the querying system is not yet extensible because we don't
have a robust framework for interpreting and optimizing queries yet"; and "Because there is no query
language for HGDB at the time of this writing […] queries are built up as query conditions, classes
implementing the `HGQueryCondition` interface, and submitted via a call to `HyperGraph.find`"
([HypergraphDB wiki, *Working with Queries and Results*, checked 20 September
2026](https://github.com/hypergraphdb/hypergraphdb/wiki/QueriesAndResults)).

```java
import org.hypergraphdb.HGQuery.hg;

HGQueryCondition cond = hg.and(hg.type(MyLink.class), hg.incident(atom));
HGSearchResult<HGHandle> rs = graph.find(cond);
```

`hg.incident(atom)` is the incidence query — "all links of type `MyLink` that point to `atom`" — and
`hg.and`/`hg.or`/`hg.not` compose conditions; the wiki warns that `not` "can result in inefficient
queries because most of the time it cannot be translated to an index lookup". This is the
hypergraph-native counterpart of §1–§5, and the trade-off is explicit: native incidence traversal,
no declarative optimiser.

## 9. Research languages and proposals

Beyond the deployed systems, the literature contains query formalisms that are hypergraph-native but
not standardised:

- **Complex query answering (CQA) as a learned query language.** StarQE, NQE, SQE and LKHGT answer
  existential first-order queries over hyper-relational graphs and knowledge hypergraphs by
  *embedding* the query rather than executing it; see
  [logical-reasoning-and-rules-over-n-ary-facts.md](logical-reasoning-and-rules-over-n-ary-facts.md).
- **Cardinality estimation for hyper-relational queries** is being studied as its own problem
  ([Teng, Li, Di and Chen, *Cardinality Estimation on Hyper-relational Knowledge Graphs*,
  arXiv:2405.15231, 2024](https://arxiv.org/abs/2405.15231)) — a prerequisite for any future
  cost-based hypergraph optimiser.
- **HypergraphDB's own "Towards a HyperGraph Query Language" notes** remain a sketch (referenced from
  the wiki page above).

## 10. Complexity: what matching a hypergraph pattern costs

### 10.1 Sub-hypergraph isomorphism

Matching a *pattern hypergraph* into a data hypergraph generalises subgraph isomorphism, and
subgraph isomorphism "is a generalization of both the maximum clique problem and the problem of
testing whether a graph contains a Hamiltonian cycle, and is therefore NP-complete"
([Wikipedia, *Subgraph isomorphism problem*, checked 20 September
2026](https://en.wikipedia.org/wiki/Subgraph_isomorphism_problem); the classical source is Cook's
theorem and Garey & Johnson). A 2-uniform hypergraph is a graph, so **sub-hypergraph isomorphism is
NP-hard**, and the usual membership argument puts the decision problem in NP. Practically: any
"find all occurrences of this pattern of n-ary facts" feature is exponential in the pattern, not in
the data, which is why the worst case is tolerable and the *structure* of the pattern is what you
should control.

### 10.2 Conjunctive queries and hypertree decompositions

Every conjunctive query has a hypergraph: vertices are variables, hyperedges are atoms. This is the
bridge between query evaluation and hypergraph theory, and it is where the sharpest results live.

- **Acyclic queries are easy.** Yannakakis's semi-join algorithm evaluates acyclic conjunctive
  queries in polynomial time (Yannakakis, *Algorithms for acyclic database schemes*, VLDB 1981; no open DOI, record verified via OpenAlex).
  Gottlob, Leone and Scarcello showed the Boolean-acyclic case is **LOGCFL-complete**, hence highly
  parallelisable ([Gottlob, Leone and Scarcello, *The complexity of acyclic conjunctive queries*,
  *Journal of the ACM* 48(3), 2001](https://doi.org/10.1145/382780.382783)).
- **Hypertree width generalises acyclicity.** *Hypertree Decompositions and Tractable Queries*
  introduced hypertree width, proved that deciding query width ≤ k is NP-complete (specifically for
  k = 4, answering an open problem of Chekuri and Rajaraman negatively), that hypertree width *is*
  efficiently recognisable for fixed k, and that "Boolean queries of constant hypertree width can be
  efficiently evaluated" ([Gottlob, Leone and Scarcello, arXiv:cs/9812022,
  1998](https://arxiv.org/abs/cs/9812022); journal version *JCSS* 64(3), 2002,
  [doi:10.1006/jcss.2001.1809](https://doi.org/10.1006/jcss.2001.1809)). The survey version is
  [Gottlob, Leone and Scarcello, *Hypertree Decompositions: A Survey*, MFCS 2001](https://doi.org/10.1007/3-540-44683-4_5).
  For fixed k, evaluating a Boolean CQ given a k-width hypertree decomposition is LOGCFL-complete,
  and for non-Boolean queries the answer is computable in time polynomial in the combined size of the
  input and the output relation.
- **Generalized hypertree width** (ghw ≤ hw ≤ 3·ghw + 1; [Grohe and Marx,
  2014](https://arxiv.org/abs/1711.04506), §4, citing Adler, Gottlob and Grohe 2007) is the width
  that indexes the 2026 expressivity hierarchy for hypergraph neural networks in
  [hypergraph-neural-networks.md](hypergraph-neural-networks.md) §3.2. Deciding ghw ≤ k is
  NP-complete for every fixed k ≥ 3 ([Gottlob, Miklós and Schwentick, *Generalized hypertree
  decompositions: NP-hardness and tractable variants*, *Journal of the ACM* 56(6),
  2009](https://doi.org/10.1145/1568318.1568320)) and for k = 2 as well, and so is deciding
  fractional hypertree width ≤ 2; ghw ≤ k becomes tractable under the bounded (multi-)intersection
  property ([Gottlob, Lanzinger, Pichler and Razgon, *Journal of the ACM* 68(5),
  2021](https://arxiv.org/abs/2002.05239), Main Results 1–3). Recognising hw ≤ k, by contrast, is
  polynomial for fixed k (above). (Corrected 2026-09-25: this item had called ghw "the variant used
  most in machine learning today", which no source supports, and its recognition merely "NP-hard";
  [P6](../../projects/p6-schema-width/) research report 01 §1.5.)
- **Output size is governed by fractional edge cover.** The AGM bound gives a tight bound on the
  number of answers of a join in terms of the fractional edge cover number of its hypergraph
  ([Atserias, Grohe and Marx, *Size Bounds and Query Plans for Relational Joins*, FOCS 2008 /
  *SIAM J. Comput.* 42(4), 2013](https://doi.org/10.1137/110859440)). This is the theory behind
  worst-case-optimal join algorithms, and it is the right mental model for "how big can the answer to
  this n-ary pattern be".

### 10.3 What this means for a KHG engine

Three practical corollaries:

1. Keep the *query* hypergraph close to acyclic. A star-shaped hyperedge pattern (one fact node, n
   role edges) is acyclic and therefore cheap; patterns that chain several hyperedges through shared
   entities are where hypertree width starts to bite.
2. Reification can raise the width of the query hypergraph even when the underlying n-ary pattern
   was simple — an argument for native n-ary storage that is independent of expressivity. The
   mechanism is not the number of atoms, since width is not a function of atom count. Reifying
   every n-ary atom (one fact node, one binary atom per role) turns the query hypergraph into its
   incidence graph. A graph is acyclic in every sense exactly when it is a forest
   ([Brault-Baron, 2016](https://arxiv.org/abs/1403.7076), Remark 7), so the reified query is
   acyclic exactly when the n-ary one is **Berge-acyclic**. Width rises when an n-ary atom covered a
   cycle: in P6's probes, a triangle whose three binary atoms are covered by a ternary atom goes
   from hw 1 to hw 2 once reified, and K5 from 3 to 4, while a bare triangle stays at 2
   ([P6 research report 01](../../projects/p6-schema-width/research/01-theory-and-solvers.md) §1.3;
   `probes/out/reification.json`). (Corrected 2026-09-25: the item had put the rise down to
   reification multiplying the atoms.)
3. There is currently no engine that exposes hypertree-decomposition-based planning for
   knowledge-hypergraph workloads. This is an open engineering gap, noted again in the section
   [README](README.md).

## 11. Comparison

| Language / API | Data model | n-ary fact | Hyperedge identity | "At least these participants" | Status (Sept 2026) |
|---|---|---|---|---|---|
| SPARQL 1.1 | RDF triples | via intermediate node | no | no | W3C Rec 2013 |
| SPARQL 1.2 | RDF 1.2 + triple terms | triple + qualifiers | reifier term | partial (annotation blocks) | W3C WD 13 Sep 2026 |
| TypeQL | typed entity-relation-attribute | native, any arity | `$r isa …` | yes (partial tuples) | TypeDB 3.x |
| GQL / openCypher | property graph (binary) | emulated fact node | node | no | ISO/IEC 39075:2024 |
| Gremlin | binary attributed multi-graph | emulated fact node | vertex | no | TinkerPop 3.8.2 |
| Datalog | n-ary relations | native | no (add an argument) | no | classical |
| MeTTa / Atomspace | metagraph, nested links | native, nested | atom handle | pattern-dependent | research |
| HypergraphDB API | ordered n-ary links | native | `HGHandle` | via conditions | 1.3-SNAPSHOT, no query language |

## Open questions raised here

- Can hypertree-decomposition planning be made practical for KHG stores, and what would the cost
  model be over an incidence index rather than a relational one?
- Does SPARQL 1.2's triple-term model compose for *nested* n-ary facts, or only for one level of
  qualification? (The grammar permits `TripleTerm` in object position of a `TripleTerm`, so
  syntactically yes; the semantics of nesting under `rdf:reifies` is the part to check.)
- Is there a useful "hypergraph algebra" (incidence join, s-walk, hyperpath closure) that could be
  added to GQL or SPARQL as an extension rather than a new language?

## Sources

- Seaborne, A., Kellogg, G., Hartig, O., Champin, P.-A. *RDF 1.2 Concepts and Abstract Data Model*. W3C Candidate Recommendation, 7 April 2026. <https://www.w3.org/TR/rdf12-concepts/>
- Seaborne, A. et al. *SPARQL 1.2 Query Language*. W3C Working Draft, 13 September 2026. <https://www.w3.org/TR/sparql12-query/>
- Harris, S., Seaborne, A. (eds.) *SPARQL 1.1 Query Language*. W3C Recommendation, 21 March 2013. <https://www.w3.org/TR/sparql11-query/>
- TypeDB. *TypeQL Reference — Data and query model* (TypeDB 3.x documentation). Checked 20 September 2026. <https://typedb.com/docs/typeql-reference/data-model/>
- TypeDB. *TypeDB Academy, Lesson 7.2: Relation patterns*. Checked 20 September 2026. <https://typedb.com/docs/academy/7-understanding-query-patterns/7.2-relation-patterns>
- GQL Standards Committee. *GQL — ISO/IEC 39075:2024, Information technology — Database languages — GQL*, published 17 April 2024. <https://www.gqlstandards.org/>
- Apache TinkerPop. *TinkerPop 3.8.2 Reference Documentation*. Checked 20 September 2026. <https://tinkerpop.apache.org/docs/current/reference/>
- Ceri, S., Gottlob, G., Tanca, L. "What you always wanted to know about Datalog (and never dared to ask)". *IEEE Transactions on Knowledge and Data Engineering* 1(1), 1989. <https://doi.org/10.1109/69.43410>
- Goertzel, B. et al. *OpenCog Hyperon: A Framework for AGI at the Human Level and Beyond*. arXiv:2310.18318, 2023. <https://arxiv.org/abs/2310.18318>
- trueagi-io. *Minimal MeTTa specification*, hyperon-experimental repository. Checked 20 September 2026. <https://github.com/trueagi-io/hyperon-experimental/blob/main/docs/minimal-metta.md>
- HypergraphDB project. *Working with Queries and Results* (project wiki). Checked 20 September 2026. <https://github.com/hypergraphdb/hypergraphdb/wiki/QueriesAndResults>
- Teng, F., Li, H., Di, S., Chen, L. *Cardinality Estimation on Hyper-relational Knowledge Graphs*. arXiv:2405.15231, 2024. <https://arxiv.org/abs/2405.15231>
- Yannakakis, M. "Algorithms for acyclic database schemes". *VLDB* 1981. No open DOI; bibliographic record verified via OpenAlex (<https://api.openalex.org/works?filter=title.search:Algorithms%20for%20acyclic%20database%20schemes>).
- Gottlob, G., Leone, N., Scarcello, F. "The complexity of acyclic conjunctive queries". *Journal of the ACM* 48(3), 2001. <https://doi.org/10.1145/382780.382783>
- Gottlob, G., Leone, N., Scarcello, F. *Hypertree Decompositions and Tractable Queries*. arXiv:cs/9812022, 1998; *Journal of Computer and System Sciences* 64(3), 2002. <https://arxiv.org/abs/cs/9812022> · <https://doi.org/10.1006/jcss.2001.1809>
- Gottlob, G., Leone, N., Scarcello, F. "Hypertree Decompositions: A Survey". *MFCS 2001*, LNCS 2136. <https://doi.org/10.1007/3-540-44683-4_5>
- Gottlob, G., Miklós, Z., Schwentick, T. "Generalized hypertree decompositions: NP-hardness and tractable variants". *Journal of the ACM* 56(6), 2009 (earlier version PODS 2007). <https://doi.org/10.1145/1568318.1568320>
- Atserias, A., Grohe, M., Marx, D. "Size Bounds and Query Plans for Relational Joins". *FOCS 2008*; *SIAM Journal on Computing* 42(4), 2013. <https://doi.org/10.1137/110859440>
- Gottlob, G., Lanzinger, M., Pichler, R., Razgon, I. "Complexity Analysis of Generalized and Fractional Hypertree Decompositions". *Journal of the ACM* 68(5), 2021; arXiv:2002.05239 (read 2026-09-25). <https://arxiv.org/abs/2002.05239> · <https://doi.org/10.1145/3457374>
- Brault-Baron, J. "Hypergraph Acyclicity Revisited". *ACM Computing Surveys* 49(3), 2016; arXiv:1403.7076. <https://arxiv.org/abs/1403.7076>
- Grohe, M., Marx, D. "Constraint Solving via Fractional Edge Covers". *ACM Transactions on Algorithms* 11(1), article 4, 2014; arXiv:1711.04506 (read 2026-09-25). <https://arxiv.org/abs/1711.04506> · <https://doi.org/10.1145/2636918>
- Project P6, "Schema width survey": research report 01, *Acyclicity degrees, width measures and hypertree-decomposition solvers*, 2026-09-24, §1.3 (reification probe) and §1.5 (corrections applied here). [projects/p6-schema-width/research/01-theory-and-solvers.md](../../projects/p6-schema-width/research/01-theory-and-solvers.md)
- Wikipedia. *Subgraph isomorphism problem*. Checked 20 September 2026. <https://en.wikipedia.org/wiki/Subgraph_isomorphism_problem>
