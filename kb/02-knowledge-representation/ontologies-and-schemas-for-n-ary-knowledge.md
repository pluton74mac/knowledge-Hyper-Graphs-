---
title: Ontologies and schema languages for n-ary knowledge
type: survey
status: draft
tags: [owl, rdfs, w3c, schema-org, role, framenet, common-logic, conceptual-graphs, typedb, pg-schema, shacl, shex]
created: 2026-09-20
updated: 2026-09-20
---

# Ontologies and schemas for n-ary knowledge

A knowledge hypergraph without a schema is a pile of tuples. This note surveys the schema and
ontology languages that can say something about n-ary facts — what each one can constrain, what it
cannot, and what its status is as of September 2026. The order is roughly chronological within three
families: logic-based (Conceptual Graphs, Common Logic), web-standard (RDFS/OWL, the W3C n-ary note,
schema.org, SHACL/ShEx), and database (TypeDB, PG-Schema). Lexical-semantic inventories (FrameNet,
event schemas) sit alongside as *role vocabularies* rather than constraint languages.

The encoding tricks these languages use are catalogued in
[n-ary-relations-and-reification.md](n-ary-relations-and-reification.md); the design decisions a KHG
schema has to make are in
[knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md).

## 1. The web-standard baseline: properties are binary

The W3C statement is unambiguous:

> "In Semantic Web languages, such as RDF and OWL, a property is a *binary* relation: it is used to
> link two individuals or an individual and a value."
> ([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/), W3C Working Group Note,
> 12 April 2006)

Everything else in the RDF/OWL family is built on that. The note's two patterns:

- **Pattern 1 — a class for the relation.** Create "a new class and *n* new properties to represent
  an *n*-ary relation. An instance of the relation linking the *n* individuals is then an instance
  of this class." This is the incidence-graph encoding of a hyperedge, and the pattern behind
  Freebase CVTs, Wikidata statement nodes, PROV-O qualified associations and schema.org Roles.
- **Pattern 2 — an ordered list.** Used when "all but one participant in a relation do not have a
  specific role and essentially form an ordered list", e.g. a flight visiting airports in order,
  "a temporal order among constituents".

The note is candid about Pattern 1's costs: a **maintenance burden**, because expressing
combinations of restrictions requires building "an explicit lattice of classes to represent all the
possible combinations"; awkward **inverses**, since one must be defined "for each of the properties
participating in the n-ary relation (with the proper constraints)"; and the plain fact that the
pattern "limits the use of many OWL constructs"
([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)).

That class lattice is the crux. In a native KHG schema, "this relation may optionally bind roles A
and B, and requires C" is one declaration. In OWL it is a family of subclasses. This is the single
strongest ontology-engineering argument for n-ary relation types with declared optional roles, as
proposed in
[knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md).

**Twenty years on, the note has not been superseded.** RDF 1.2 adds triple terms and reifiers, which
handle *statements about statements* but not first-class n-ary predicates
([RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/), Candidate Recommendation Snapshot,
7 April 2026).

## 2. schema.org Role

schema.org's answer to the same problem is one reusable class:

> "Represents additional information about a relationship or property. For example a Role can be
> used to say that a 'member' role linking some SportsTeam to a player occurred during a particular
> time period."
> ([schema.org Role](https://schema.org/Role), version 30.1, 16 September 2026, checked 2026-09-20)

Its own properties are `roleName`, `startDate` and `endDate`, plus the Thing properties; the
worked example on the page uses an `OrganizationRole` to record that a person played Quarterback for
a team from 1979 to 1992 — information that a bare `member` edge cannot carry. Structurally: a Role
is Pattern 1 with a *generic* relation class, so the role names are data (`roleName`) rather than
schema. That trades validation for convenience, and is why RAM cites W3C and schema.org together as
the origin of "the semantic property of role for n-ary relations"
([Liu, Yao and Li, 2021](https://arxiv.org/abs/2104.09780)).

## 3. Role vocabularies: FrameNet and event schemas

Not constraint languages, but the largest curated inventories of *role names* — the scarce resource
when building a KHG schema.

**FrameNet.** "the role names (called frame elements or FEs) are local to particular conceptual
structures (frames); some of these are quite general, while others are specific to a small family of
lexical items"; the TRANSPORTATION frame "provides MOVERS, MEANS of transportation, and PATHS"
([Baker, Fillmore and Lowe, 1998](https://aclanthology.org/P98-1013/)). FrameNet also records that
one frame surfaces at several arities, as **Frame Element Groups**: "Some combinations of frame
elements, or Frame Element Groups (FEGs), for some real corpus sentences in the DRIVING frame"
(same source). Mapping: frame ≈ relation type, FE ≈ role, FEG ≈ observed arity pattern.

**Event schemas.** The event-KG survey puts the same structure in database terms: "EKG schema
describes the basic concepts that form EKG, including the event types, argument roles, and event
relations. The first two form event schema", and notes that "Event schema can be manually designed,
such as the typical ACE event schema and FrameNet frame", with automatic **event schema induction**
defined as identifying "all event types {tp₀,...,tp_τ} and all argument roles {rl^i₀,...,rl^i_ρ} for
each event type tp_i" ([Guan et al., 2021/2022](https://arxiv.org/abs/2112.15280)). NewsReader adds
the Event and Situation Ontology on top of the Simple Event Model precisely because "SEM does not
distinguish what exact role each participant plays"
([Rospocher et al., 2016](https://doi.org/10.1016/j.websem.2015.12.004)).

The lesson for schema design: **role induction is a real task with real methods**, not something to
improvise per relation.

## 4. Conceptual Graphs and Common Logic

**Conceptual graphs** (Sowa) are bipartite graphs of concept nodes and conceptual relation nodes,
where a relation node may have any number of numbered arcs — "The *between* relation (Betw) is a
triadic relation" ([Sowa, conceptual graph examples](https://www.jfsowa.com/cg/cgexampw.htm);
[Wikipedia, Conceptual graph](https://en.wikipedia.org/wiki/Conceptual_graph)). Because the
bipartite concept/relation graph is the incidence graph of a hypergraph, a conceptual graph *is* a
knowledge hypergraph drawn differently; see
[semantic-web-hypergraph-view.md](semantic-web-hypergraph-view.md).

CGIF, the Conceptual Graph Interchange Format, writes relations in prefix form with any number of
arguments — Sowa's own examples include `(Agnt ?x Bob) (Dest ?x "St. Louis") (Thme ?x ?y)` and a
four-argument actor `(IntegerDivide [Integer: *x] [Integer: 7] | [*u] [*v])` — and provides contexts
and negation, where "A negation is ~ followed by a context"
([Sowa, CGIF](https://www.jfsowa.com/cg/cgif.htm), checked 2026-09-20). Contexts are the CG answer to
scoping and to facts about facts.

**Common Logic** standardises this. "The official standard for conceptual graph syntax and semantics
is the ISO/IEC 24707 standard for Common Logic"; "Annex B of this document defines a grammar for the
Conceptual Graph Interchange Format (CGIF) and defines its semantics by a translation to the
abstract syntax of Common Logic" ([Sowa, CG standard page](https://www.jfsowa.com/cg/cgstand.htm),
checked 2026-09-20). Common Logic is "a framework for a family of logic languages, based on
first-order logic, intended to facilitate the exchange and transmission of knowledge in
computer-based systems", with the three dialects CLIF, CGIF and XCL
([Wikipedia, Common Logic](https://en.wikipedia.org/wiki/Common_Logic)). The current edition is
ISO/IEC 24707:2018, which "specif[ies] an abstract syntax and a model-theoretic (declarative)
semantics for an extension of first-order logic"
([ISO/IEC 24707:2018](https://www.iso.org/standard/66249.html)), superseding the 2007 edition.

Two features matter here:

- **Variable-arity relations.** Common Logic relations are not fixed-arity; the same relation symbol
  may take different numbers of arguments.
- **Sequence markers.** The abstract syntax's undefined terms are "name, sequence marker, and
  title", and sequence markers are what let a sentence quantify over argument *sequences* rather
  than individual arguments ([ISO/IEC 24707:2018](https://www.iso.org/standard/66249.html);
  [Wikipedia, Common Logic](https://en.wikipedia.org/wiki/Common_Logic)).

Sequence markers are, as far as this research run found, the only standardised device for writing a
rule that holds *for every arity* of a relation — exactly what a KHG rule language needs and what
neither SPARQL nor Cypher offers `[unverified]`.

## 5. TypeDB: n-ary relations with declared roles

TypeDB is the main current database whose schema language treats n-ary relations as primitive.

> "Instances of relation types may reference (or 'link') zero or more data instances for each
> associated role type, called their **players** of that role."

Relation types are "required to have at least one associated role type specified with the keyword
`relates`", and

> "Relation types can also have capabilities, i.e. play roles or own attribute types. This, for
> example, allows the creation of nested relations (i.e., relations playing roles in other
> relations)."
> ([TypeDB, Data and query model](https://typedb.com/docs/typeql-reference/data-model/), TypeDB 3.x,
> checked 2026-09-20)

Write-time validation is part of the model: "Connections made between instances are checked against
the `owns`, `plays`, and `relates` in the schema to ensure they are permitted between the instance
types" ([TypeDB, Constraining Data](https://typedb.com/docs/core-concepts/typeql/constraining-data/),
checked 2026-09-20). So TypeDB covers: relation typing, named roles, role-player typing, nesting,
and attributes on relations — the whole checklist of
[knowledge-hypergraph-schema-design.md](knowledge-hypergraph-schema-design.md) except qualifiers as
a *distinct* slot class (a qualifier is just another role) and calibrated confidence.

Its limitations for KHG work are practical rather than conceptual: a single vendor, its own query
language, and no standardised interchange with RDF or property graphs.

## 6. PG-Schema and the property-graph line

Property graphs have edges "associate[d] ... with a pair of nodes"
([Angles, 2018](https://ceur-ws.org/Vol-2100/paper26.pdf)), so schema work there is about node and
edge *types*, not arity. PG-Schema is the reference proposal:

> "Aiming to inspire the development of GQL and enhance the capabilities of graph database systems,
> we propose PG-Schema, a simple yet powerful formalism for specifying property graph schemas. It
> features PG-Types with flexible type definitions supporting multi-inheritance, as well as
> expressive constraints based on the recently proposed PG-Keys formalism."
> ([Angles et al., 2023](https://arxiv.org/abs/2211.10962), SIGMOD 2023 / PACMMOD 1(2))

The paper's own premise is that "despite documented demand, schema support is limited both in
existing systems and in the first version of the GQL Standard", with a richer DDL anticipated in
GQL's second version. For a KHG, PG-Schema is useful as a *target*: it can type the intermediate
node of a reified hyperedge and key it, but it cannot say "this edge has four participants".

## 7. Validating qualifiers: SHACL and ShEx

- **SHACL 1.2 Core** (W3C Working Draft, 18 September 2026) is the first standards-track language
  that can constrain RDF 1.2 reification. It provides `sh:reifierShape` and `sh:reificationRequired`
  for validating reifier nodes, and allows `sh:severity` and `sh:message` to be attached to a
  reifier ([SHACL 1.2 Core](https://www.w3.org/TR/shacl12-core/), checked 2026-09-20). In KHG terms:
  a shape can require that every `award_received` statement carries a `point_in_time` qualifier of
  the right datatype.
- **ShEx** remains at Shape Expressions Language 2.1, a Final Community Group Report of
  8 October 2019, describing "RDF nodes and graph structures"
  ([ShEx 2.1](https://shex.io/shex-semantics/), checked 2026-09-20). That document makes no mention
  of RDF 1.2, RDF-star or triple terms, so qualifier-aware ShEx validation is not available from the
  published specification `[unverified]`.
- **Wikidata property constraints** are the largest deployed qualifier-validation system in
  practice, but they are a MediaWiki extension's convention rather than a standard.

## 8. Comparison

| Language / vocabulary | n-ary natively | named roles | role typing | optional roles / cardinality | qualifiers as a distinct class | nesting | status (2026-09) |
|---|---|---|---|---|---|---|---|
| RDFS / OWL 2 | no (binary properties, [Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)) | via Pattern 1 properties | yes (domain/range) | yes, but needs a class lattice | no | no | W3C Rec |
| W3C n-ary note Pattern 1 | by encoding | yes | yes | via subclasses | no | by chaining | Note, 2006 |
| schema.org Role | by encoding | as data (`roleName`) | weak | no | effectively yes (Role properties) | by chaining | v30.1, 2026-09-16 |
| RDF 1.2 + SHACL 1.2 | no | qualifier predicates | yes (shapes) | yes (shapes) | yes (reifier + annotations) | object position only | CR / WD, 2026 |
| Conceptual Graphs / CGIF | yes (n-adic relation nodes) | numbered arcs | via type hierarchy | via the CG canon | contexts | contexts | tied to ISO/IEC 24707 |
| Common Logic (ISO/IEC 24707:2018) | yes, variable arity | positional | no built-in types | via axioms | no | via quantified sentences | ISO standard |
| TypeDB | yes (`relates`) | yes | yes (`plays`) | yes | no (all roles are roles) | yes | product, TypeDB 3.x |
| PG-Schema / GQL | no | — | yes (node/edge types) | yes (PG-Keys) | edge properties | no | proposal / ISO/IEC 39075:2024 |
| FrameNet / event schemas | yes (as a vocabulary) | yes (FEs, argument roles) | informal | core vs non-core FEs | no | no | lexical resources |

## 9. Recommendations

1. **Use a role vocabulary that already exists** where one fits — FrameNet FEs, ACE/ESO argument
   roles, Wikidata qualifier properties — instead of minting names. Role reuse across arities is
   measurable and high ([Liu et al., 2021](https://arxiv.org/abs/2104.09780)).
2. **Declare optional roles, not subclasses.** The class-lattice problem is the documented failure
   mode of the OWL route ([Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/)).
3. **If you need write-time validation today**, TypeDB is the only listed system that enforces role
   declarations on n-ary relations; for RDF data, SHACL 1.2 Core is the standards-track path and is
   still a Working Draft.
4. **Keep a Common Logic or CGIF export in mind** if the KB will carry rules: it is the only
   standardised syntax found here with variable-arity relations and sequence markers.
5. **Do not expect GQL to solve this.** It is a property-graph language; its edges are binary
   ([ISO/IEC 39075:2024](https://www.iso.org/standard/76120.html)).

## Sources

- Noy, N., Rector, A. (eds). *Defining N-ary Relations on the Semantic Web.* W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- W3C. *RDF 1.2 Concepts and Abstract Data Model.* W3C Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. *SHACL 1.2 Core.* W3C Working Draft, 18 September 2026. https://www.w3.org/TR/shacl12-core/
- Prud'hommeaux, E., Boneva, I., Labra Gayo, J. E., Kellogg, G. (eds). *Shape Expressions Language 2.1.* Final Community Group Report, 8 October 2019. https://shex.io/shex-semantics/
- schema.org. *Role.* Version 30.1, 16 September 2026 (checked 2026-09-20). https://schema.org/Role
- Baker, C. F., Fillmore, C. J., Lowe, J. B. *The Berkeley FrameNet Project.* COLING-ACL 1998. https://aclanthology.org/P98-1013/
- Guan, S., Cheng, X., Bai, L., Zhang, F., Li, Z., Zeng, Y., Jin, X., Guo, J. *What is Event Knowledge Graph: A Survey.* arXiv:2112.15280, 2021 (rev. 2022). https://arxiv.org/abs/2112.15280
- Rospocher, M., van Erp, M., Vossen, P., Fokkens, A., Aldabe, I., Rigau, G., Soroa, A., Ploeger, T., Bogaard, T. *Building event-centric knowledge graphs from news.* Journal of Web Semantics 37–38:132–151, 2016. https://doi.org/10.1016/j.websem.2015.12.004
- Sowa, J. F. *Conceptual Graphs Examples.* jfsowa.com, checked 2026-09-20. https://www.jfsowa.com/cg/cgexampw.htm
- Sowa, J. F. *Conceptual Graph Interchange Format (CGIF).* jfsowa.com, checked 2026-09-20. https://www.jfsowa.com/cg/cgif.htm
- Sowa, J. F. *The CG Standard.* jfsowa.com, checked 2026-09-20. https://www.jfsowa.com/cg/cgstand.htm
- Wikipedia. *Conceptual graph.* https://en.wikipedia.org/wiki/Conceptual_graph
- Wikipedia. *Common Logic.* https://en.wikipedia.org/wiki/Common_Logic
- ISO/IEC. *ISO/IEC 24707:2018 Information technology — Common Logic (CL) — A framework for a family of logic-based languages.* 2018 (superseding ISO/IEC 24707:2007). https://www.iso.org/standard/66249.html
- TypeDB. *Docs > TypeQL Reference > Data and query model* (TypeDB 3.x), checked 2026-09-20. https://typedb.com/docs/typeql-reference/data-model/
- TypeDB. *Docs > Core Concepts > Constraining Data*, checked 2026-09-20. https://typedb.com/docs/core-concepts/typeql/constraining-data/
- Angles, R. *The Property Graph Database Model.* AMW 2018, CEUR-WS Vol. 2100. https://ceur-ws.org/Vol-2100/paper26.pdf
- Angles, R., Bonifati, A., Dumbrava, S., Fletcher, G., Green, A., Hidders, J., Li, B., Libkin, L., Marsault, V., Martens, W., Murlak, F., Plantikow, S., Savković, O., Schmidt, M., Sequeda, J., Staworko, S., Tomaszuk, D., Voigt, H., Vrgoč, D., Wu, M., Živković, D. *PG-Schema: Schemas for Property Graphs.* Proc. ACM Manag. Data 1(2), Article 198, SIGMOD 2023; arXiv:2211.10962. https://arxiv.org/abs/2211.10962
- ISO/IEC. *ISO/IEC 39075:2024 Information technology — Database languages — GQL.* 2024. https://www.iso.org/standard/76120.html
- Liu, Y., Yao, Q., Li, Y. *Role-Aware Modeling for N-ary Relational Knowledge Bases.* WWW 2021; arXiv:2104.09780. https://arxiv.org/abs/2104.09780
