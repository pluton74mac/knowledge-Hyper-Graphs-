---
title: Knowledge hypergraph schema design — entities, relation types, roles, qualifiers, provenance, time, confidence
type: howto
status: draft
tags: [schema, modelling, roles, qualifiers, provenance, prov-o, temporal, confidence, json, typedb, pg-schema, hif]
created: 2026-09-20
updated: 2026-09-20
---

# Knowledge hypergraph schema design

This note is the practical counterpart to
[what-is-a-knowledge-hypergraph.md](what-is-a-knowledge-hypergraph.md): given that you have decided
to store n-ary facts, what does the schema have to say, and what does a concrete serialisation look
like? Seven decisions recur, and every one of them has been made differently by at least two
production systems:

1. **Entity identity** — what is a node, and what is a literal?
2. **Relation type** — is the fact typed by a symbol, and is arity fixed per type?
3. **Roles or positions** — how is an argument identified?
4. **Qualifiers** — is there a second, open-ended slot class that is *about* the fact?
5. **Provenance** — where did the fact come from, and is that part of the fact?
6. **Temporal validity** — when is the fact true, and when was it recorded?
7. **Confidence** — how certain is it, and what does the number mean?

The terminology choices behind (2)–(4) are argued in
[hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md); (7) is
developed in
[open-world-vs-closed-world-and-uncertainty.md](open-world-vs-closed-world-and-uncertainty.md).

## 1. Two layers, and why the schema layer is not optional

Every mature model separates a **schema/ontology layer** (types, roles, constraints) from an
**instance layer** (facts). The pure-mathematics hypergraph formats do not: the Hypergraph
Interchange Format, the community standard shared by HyperNetX, XGI, Hypergraphx,
SimpleHypergraphs.jl and HAT, has exactly three record kinds — `nodes`, `edges` and `incidences` —
where an incidence record carries `"node"`, `"edge"` and optional `"weight"`, `"direction"`
(`"head"` or `"tail"`) and free-form `"attrs"`
([HIF standard](https://github.com/HIF-org/HIF-standard), checked 2026-09-20). The published
specification describes HIF as "a standardized format for storing higher-order network data" that
"supports multiple types of higher-order networks, including undirected hypergraphs, directed
hypergraphs, and abstract simplicial complexes" and "includes support for attributes associated with
nodes, edges, and incidences" ([Coll et al., 2025](https://doi.org/10.1017/nws.2025.10018),
*Network Science* 13, e21).

That is enough to move a hypergraph between analysis libraries and nothing more: there is no
relation type, no role vocabulary, no constraint language. **A knowledge hypergraph needs a role
name on the incidence and a type on the edge**, which in HIF terms means pushing both into `attrs`
and losing all validation. Section 6 gives a schema that keeps them first class.

The contrasting extreme is TypeDB, whose schema language makes roles a declared part of the relation
type: relation types are "required to have at least one associated role type specified with the
keyword `relates`", instances "may reference (or 'link') zero or more data instances for each
associated role type, called their players of that role", and "Relation types can also have
capabilities, i.e. play roles or own attribute types. This, for example, allows the creation of
nested relations (i.e., relations playing roles in other relations)."
([TypeDB, Data and query model](https://typedb.com/docs/typeql-reference/data-model/), TypeDB 3.x,
checked 2026-09-20). Property graphs go the other way: PG-Schema "features PG-Types with flexible
type definitions supporting multi-inheritance, as well as expressive constraints based on the
recently proposed PG-Keys formalism" ([Angles et al., 2023](https://arxiv.org/abs/2211.10962)),
but the underlying edge is still binary.

## 2. Entities, literals and identity

Minimum viable rules, drawn from what the benchmark pipelines actually do:

- **Entities get opaque identifiers**, not labels. Wikidata Q-ids and Freebase mids are the model.
- **Literals are second-class.** Every hyper-relational benchmark drops them: WD50K keeps only
  statements "whose main object and qualifier values correspond to `wikibase:Item`", a step that
  "results in the removal of all literals in object position"
  ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)); WikiPeople's construction removed facts
  with "unknown value" or "no value" elements
  ([WikiPeople repository](https://github.com/gsp2014/WikiPeople), checked 2026-09-20). This is a
  *modelling convenience for embedding models*, not a recommendation: dates and quantities are
  exactly what qualifiers are usually for, so a general KHG schema must carry typed literals with
  units and precision.
- **Hyperedges get identifiers too, or you cannot talk about them.** HypergraphDB's phrasing: the
  generalised model "automatically reifies every entity expressed in the database"
  ([Iordanov, 2010](https://hypergraphdb.org/docs/hypergraphdb.pdf)). If your fact records need
  provenance, confidence or nesting, give each hyperedge a stable id from the start; retrofitting it
  means re-identifying every fact.

## 3. Relation types, roles and cardinality

A role declaration should fix at least:

| Field | Meaning | Precedent |
|---|---|---|
| `role` | name, unique within the relation type (or globally, to allow reuse across arities) | TypeDB `relates`; W3C n-ary Pattern 1 properties; FrameNet frame elements |
| `type` | the class of entity that may fill it | TypeDB `plays`; Wikidata "value-type constraint" |
| `required` | must every instance bind it? | FrameNet *core* FEs; OWL cardinality on the relation-instance class |
| `max` | may it be bound more than once? | TypeDB allows a relation to "be defined to play a role multiple times" |
| `ordered` | does the order of multiple fillers matter? | W3C n-ary note Pattern 2 (ordered lists) |

**Global vs local role names.** RAM's measurement — "over 80% roles in beyond-ternary relations also
appear in lower-arity relations" in WikiPeople
([Liu, Yao and Li, 2021](https://arxiv.org/abs/2104.09780)) — is an argument for a *global* role
vocabulary with local usage declarations, rather than fresh role names per relation type. FrameNet
made the opposite choice ("the role names ... are local to particular conceptual structures
(frames)", [Baker, Fillmore and Lowe, 1998](https://aclanthology.org/P98-1013/)) and pays for it
with a large, partly redundant FE inventory.

**Variable arity.** If the same relation type is observed at several arities, either (a) declare
optional roles, or (b) mint a relation per role combination. Option (b) is what the positional
hyperedge formalisation forces and what StarE warns "would lead to a combinatorial explosion of
typed hyperedges" ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)). Prefer (a).

## 4. Qualifiers: a second slot class, or not?

Two defensible designs:

- **One slot class.** Everything is a role binding. Simple; matches role-value-pair models (NaLP,
  RAM) and TypeDB. You lose the ability to say "this part is the fact, that part restricts it".
- **Two slot classes.** Core roles plus an open-ended qualifier map, as in Wikidata: "There is
  always one main Snak that forms the most important part of the statement" and "there can be zero
  or more additional PropertySnaks that describe the Statement in more detail"
  ([Wikibase/DataModel](https://www.mediawiki.org/wiki/Wikibase/DataModel), checked 2026-09-19).

The schema in §6 uses two slot classes because the monotonicity property only holds for the second
design — "by attaching more qualifier pairs to a main triple, we may only narrow down the answer
set, but never enlarge it" ([Hu et al., 2024](https://arxiv.org/abs/2404.09848)) — and because it
round-trips to Wikidata and to RDF 1.2 reifiers without a lossy decision. A schema that has both
should say, per relation type, which slots are core.

## 5. Provenance, time and confidence

### Provenance

Three levels, in increasing strength:

1. **A source field on the edge.** Cheapest; adequate for a single-pipeline KB.
2. **Wikidata-style reference records**: "ReferenceRecords are intended to store information about
   some source, represented as a set of Snaks"
   ([Wikibase/DataModel](https://www.mediawiki.org/wiki/Wikibase/DataModel)) — i.e. the provenance
   is itself a small set of role-value pairs, and a fact may carry several.
3. **PROV-O qualified pattern.** PROV-O (W3C Recommendation, 30 April 2013) defines
   `prov:Entity` as "A physical, digital, conceptual, or other kind of thing with some fixed
   aspects", `prov:Activity` as "Something that occurs over a period of time and acts upon or with
   entities", and `prov:wasDerivedFrom` as "a transformation of an entity into another, an update of
   an entity resulting in a new one, or the construction of a new entity based on a pre-existing
   entity" ([PROV-O](https://www.w3.org/TR/prov-o/)). Its *qualified pattern* — restating an
   unqualified relation through an intermediate class that can be annotated — is itself the n-ary
   relation-instance pattern of [Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/),
   applied to provenance.

Nanopublications formalise the separation: each is an assertion graph plus a provenance graph plus a
publication-info graph ([Groth, Gibson and Velterop, 2010](https://dl.acm.org/doi/10.5555/1883685.1883690)).

**Design rule.** Provenance is *about* the fact, not part of it. Two facts with identical roles and
different sources are the same fact with two references — which is exactly why Wikidata puts
references on the statement and not in the claim: a claim is "the core part of a statement without
references and ranks" ([Help:Statements](https://www.wikidata.org/wiki/Help:Statements)).

### Temporal validity

Keep two clocks apart:

- **Valid time** — when the fact holds in the world. Wikidata models this with qualifiers: *point in
  time* (P585), *start time* (P580), *end time* (P582), with worked examples such as "Louis XIV
  position held King of France ... start time 14 May 1643 and end time 1 September 1715"
  ([Help:Qualifiers](https://www.wikidata.org/wiki/Help:Qualifiers)).
- **Transaction time** — when your system recorded or last checked it. This belongs with provenance.

A valid-time qualifier is a genuine n-ary argument (it changes which tuples are true); a
transaction-time stamp is metadata. Conflating them makes temporal queries wrong.

### Confidence

Three incompatible conventions are in current use, so the schema must record *which*:

| Convention | Range and meaning | Source |
|---|---|---|
| probability-like score | `s_l ∈ [0,1]`, "confidence score that represents the likelihood of the relation fact to be true" | [Chen et al., 2019](https://arxiv.org/abs/1811.10667) (UKGE), over ConceptNet / NELL / Probase |
| LLM-assigned score | hyperedge `e^score ∈ (0,10]`, entity `v^score ∈ (0,100]` | [Luo et al., 2025](https://arxiv.org/abs/2503.21322) (HyperGraphRAG) |
| editorial rank, **not** a probability | preferred / normal / deprecated | [Help:Ranking](https://www.wikidata.org/wiki/Help:Ranking) |

Store the scale, not just the number. See
[open-world-vs-closed-world-and-uncertainty.md](open-world-vs-closed-world-and-uncertainty.md).

## 6. An example schema, in JSON

The following is this KB's working proposal, not a standard. It is deliberately close to HIF's
node/edge/incidence shape so a KHG can be projected to HIF by dropping the typed fields, and close
to the Wikibase data model so a Wikidata statement maps without a modelling decision.

### 6.1 Schema layer

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "khg-version": "0.1",
  "entity_types": [
    { "id": "Person",       "label": "person" },
    { "id": "Organization", "label": "organisation" },
    { "id": "Award",        "label": "award" },
    { "id": "Place",        "label": "place" }
  ],
  "datatypes": ["string", "integer", "decimal", "date", "time-interval", "quantity", "iri"],
  "roles": [
    { "id": "recipient", "label": "recipient" },
    { "id": "award",     "label": "award" },
    { "id": "conferrer", "label": "conferring body" }
  ],
  "relation_types": [
    {
      "id": "award_received",
      "label": "award received",
      "core_roles": [
        { "role": "recipient", "type": "Person",       "required": true,  "max": 1 },
        { "role": "award",     "type": "Award",        "required": true,  "max": 1 },
        { "role": "conferrer", "type": "Organization", "required": false, "max": 1 }
      ],
      "primary": { "subject_role": "recipient", "object_role": "award" },
      "qualifier_roles": [
        { "role": "point_in_time", "datatype": "date",     "max": 1 },
        { "role": "for_work",      "type": "Thing",        "max": null },
        { "role": "together_with", "type": "Person",       "max": null },
        { "role": "place",         "type": "Place",        "max": 1 }
      ],
      "nestable": true
    }
  ],
  "confidence_scale": { "kind": "probability", "min": 0.0, "max": 1.0 },
  "time_model": { "valid_time": "qualifier", "transaction_time": "provenance" }
}
```

Notes on the choices:

- `core_roles` are the fact; `qualifier_roles` are open-ended restrictions on it. `primary` is
  *optional* and only says which two core roles form a triple view — it lets the same data be read
  as a hyper-relational fact (for Wikidata/RDF export) or as a role-value set (for NaLP/RAM-style
  models) without a second encoding.
- `max: null` means unbounded; `together_with` is the standard Wikidata case of a repeated
  qualifier.
- `nestable` says a hyperedge id may be used where an entity id is expected, which is the
  metagraph/ubergraph move (see
  [metagraphs-atomspace-and-hypergraphdb.md](metagraphs-atomspace-and-hypergraphdb.md)).

### 6.2 Instance layer

```json
{
  "khg-version": "0.1",
  "entities": [
    { "id": "Q937",   "type": "Person",       "label": "Albert Einstein" },
    { "id": "Q38104", "type": "Award",        "label": "Nobel Prize in Physics" },
    { "id": "Q193592","type": "Organization", "label": "Royal Swedish Academy of Sciences" }
  ],
  "hyperedges": [
    {
      "id": "khg:stmt-0001",
      "relation": "award_received",
      "bindings": [
        { "role": "recipient", "value": { "entity": "Q937" } },
        { "role": "award",     "value": { "entity": "Q38104" } },
        { "role": "conferrer", "value": { "entity": "Q193592" } }
      ],
      "qualifiers": [
        { "role": "point_in_time", "value": { "literal": "1921", "datatype": "date",
                                              "precision": "year" } }
      ],
      "confidence": { "value": 0.99, "scale": "probability" },
      "valid_time": { "start": "1921-01-01", "end": null },
      "provenance": [
        {
          "reference": [
            { "role": "stated_in", "value": { "entity": "Q216860" } },
            { "role": "retrieved", "value": { "literal": "2026-09-20", "datatype": "date" } }
          ],
          "derived_by": "wikidata-import-v3",
          "recorded": "2026-09-20T09:14:00Z"
        }
      ],
      "rank": "normal"
    },
    {
      "id": "khg:stmt-0002",
      "relation": "disputed_by",
      "bindings": [
        { "role": "claim",    "value": { "hyperedge": "khg:stmt-0001" } },
        { "role": "disputer", "value": { "entity": "Q42" } }
      ],
      "confidence": { "value": 0.60, "scale": "probability" }
    }
  ]
}
```

`khg:stmt-0002` demonstrates nesting: a hyperedge fills a role of another hyperedge, which is what
RDF 1.2 achieves with a reifier and a triple term, and what TypeDB achieves with a relation playing
a role ([n-ary-relations-and-reification.md](n-ary-relations-and-reification.md)).

### 6.3 Projections

| Target | How |
|---|---|
| Wikidata statement | `primary.subject_role` → item, relation → property, `primary.object_role` → main value, remaining core roles + `qualifiers` → qualifiers, `provenance[].reference` → references, `rank` → rank |
| RDF 1.2 | main triple as a triple term; hyperedge id as the reifier; qualifiers as triples on the reifier |
| positional tuple (HypE/HSimplE input) | fix an order on `core_roles`, drop qualifiers, drop provenance |
| role-value set (NaLP/RAM input) | merge `bindings` and `qualifiers` into one map, drop `primary` |
| HIF | one `edges` record per hyperedge, one `incidences` record per binding, with `role` pushed into `attrs` |

Each projection except the first two is lossy, in the ways tabulated in
[hyper-relational-vs-n-ary-vs-hypergraph.md](hyper-relational-vs-n-ary-vs-hypergraph.md).

## 7. Validation

- **RDF route.** SHACL 1.2 Core (W3C Working Draft, 18 September 2026) adds shapes for RDF 1.2
  reification, including `sh:reifierShape` and `sh:reificationRequired`, and allows `sh:severity`
  and `sh:message` to be attached to a reifier ([SHACL 1.2 Core](https://www.w3.org/TR/shacl12-core/)).
  This is the first standards-track way to constrain qualifier structure.
- **Property-graph route.** PG-Schema ([Angles et al., 2023](https://arxiv.org/abs/2211.10962)),
  anticipating a richer DDL in the second version of the GQL standard.
- **Native route.** TypeDB enforces role declarations at write time: "Connections made between
  instances are checked against the `owns`, `plays`, and `relates` in the schema to ensure they are
  permitted between the instance types"
  ([TypeDB docs](https://typedb.com/docs/core-concepts/typeql/constraining-data/), checked
  2026-09-20).

## 8. Pitfalls

1. **Electing a primary pair too early.** Freebase→Wikidata had to decide "which of the CVT's
   properties should be used as the main value of the statement, with the others being mapped to
   qualifiers" ([Pellissier Tanon et al., 2016](https://dl.acm.org/doi/10.1145/2872427.2874809)).
   Keep `primary` optional and derived.
2. **Treating provenance as a role.** It makes two records of the same fact into two facts.
3. **Unlabelled confidence.** A 0–10 LLM score and a probability are not comparable.
4. **Unbounded qualifier arity, unbounded relation vocabulary.** WD50K contains statements of arity
   2 to 67 ([Wei et al., 2025](https://arxiv.org/abs/2506.08970)); any encoding that mints a
   relation symbol per role combination will not survive that.
5. **Dropping literals.** Convenient for embedding benchmarks, fatal for real queries: in
   WikiPeople "about 13% of statements contain at least one literal" and after removing them "less
   than 3% of the remaining statements contain any qualifier pair"
   ([Galkin et al., 2020](https://arxiv.org/abs/2009.10847)).

## Sources

- HIF-org. *HIF-standard: Hypergraph Interchange Format Schema Definition and Tutorials.* GitHub, checked 2026-09-20. https://github.com/HIF-org/HIF-standard
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P. *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21, 2025. DOI 10.1017/nws.2025.10018. https://doi.org/10.1017/nws.2025.10018
- TypeDB. *Docs > TypeQL Reference > Data and query model* (TypeDB 3.x), checked 2026-09-20. https://typedb.com/docs/typeql-reference/data-model/
- TypeDB. *Docs > Core Concepts > Constraining Data*, checked 2026-09-20. https://typedb.com/docs/core-concepts/typeql/constraining-data/
- Angles, R., Bonifati, A., Dumbrava, S., Fletcher, G., Green, A., Hidders, J., Li, B., Libkin, L., Marsault, V., Martens, W., Murlak, F., Plantikow, S., Savković, O., Schmidt, M., Sequeda, J., Staworko, S., Tomaszuk, D., Voigt, H., Vrgoč, D., Wu, M., Živković, D. *PG-Schema: Schemas for Property Graphs.* Proc. ACM Manag. Data 1(2), SIGMOD 2023; arXiv:2211.10962. https://arxiv.org/abs/2211.10962
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R., Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs.* EMNLP 2020. https://arxiv.org/abs/2009.10847
- Guan, S., Jin, X., Wang, Y., Cheng, X. *WikiPeople: An n-ary relational dataset derived from Wikidata.* GitHub repository, checked 2026-09-20. https://github.com/gsp2014/WikiPeople
- Iordanov, B. *HyperGraphDB: A Generalized Graph Database.* WAIM 2010 workshops. https://hypergraphdb.org/docs/hypergraphdb.pdf
- Liu, Y., Yao, Q., Li, Y. *Role-Aware Modeling for N-ary Relational Knowledge Bases.* WWW 2021. https://arxiv.org/abs/2104.09780
- Baker, C. F., Fillmore, C. J., Lowe, J. B. *The Berkeley FrameNet Project.* COLING-ACL 1998. https://aclanthology.org/P98-1013/
- MediaWiki. *Wikibase/DataModel*, checked 2026-09-19. https://www.mediawiki.org/wiki/Wikibase/DataModel
- Wikidata. *Help:Statements*, last modified 5 June 2025. https://www.wikidata.org/wiki/Help:Statements
- Wikidata. *Help:Qualifiers*, last updated 12 September 2026. https://www.wikidata.org/wiki/Help:Qualifiers
- Wikidata. *Help:Ranking.* https://www.wikidata.org/wiki/Help:Ranking
- Hu, Z., Gutiérrez-Basulto, V., Xiang, Z., Li, R., Pan, J. Z. *HyperMono: A Monotonicity-aware Approach to Hyper-Relational Knowledge Representation.* arXiv:2404.09848, 2024. https://arxiv.org/abs/2404.09848
- W3C. *PROV-O: The PROV Ontology.* W3C Recommendation, 30 April 2013. https://www.w3.org/TR/prov-o/
- Noy, N., Rector, A. (eds). *Defining N-ary Relations on the Semantic Web.* W3C Working Group Note, 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- Groth, P., Gibson, A., Velterop, J. *The anatomy of a nanopublication.* Information Services & Use 30(1-2):51–56, 2010. https://dl.acm.org/doi/10.5555/1883685.1883690
- Chen, X., Chen, M., Shi, W., Sun, Y., Zaniolo, C. *Embedding Uncertain Knowledge Graphs.* AAAI 2019; arXiv:1811.10667. https://arxiv.org/abs/1811.10667
- Luo, H., E, H., Chen, G., et al. *HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation.* NeurIPS 2025; arXiv:2503.21322. https://arxiv.org/abs/2503.21322
- Wei, J., Guan, S., Li, D., Jin, X., Guo, J., Cheng, X. *A Survey of Link Prediction in N-ary Knowledge Graphs.* arXiv:2506.08970, 2025. https://arxiv.org/abs/2506.08970
- Pellissier Tanon, T., Vrandečić, D., Schaffert, S., Steiner, T., Pintscher, L. *From Freebase to Wikidata: The Great Migration.* WWW 2016. https://dl.acm.org/doi/10.1145/2872427.2874809
- W3C. *SHACL 1.2 Core.* W3C Working Draft, 18 September 2026. https://www.w3.org/TR/shacl12-core/
