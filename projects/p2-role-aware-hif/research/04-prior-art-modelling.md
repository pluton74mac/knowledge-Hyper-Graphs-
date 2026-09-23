---
title: Prior art for the modelling decisions in C1, C2 and C3
type: survey
status: draft
created: 2026-09-23
---

# Prior art for the modelling decisions in C1, C2 and C3 (P2 research report 04)

This report surveys what existing standards, databases, curation systems and libraries do about the
decisions that contracts C1 (record format), C2 (store interface) and C3 (candidate queue and linter
action log) must take. It is organised by design decision (M1 to M9). Each section says what the
knowledge base (KB) already covers, adds the prior art the KB does not cover, and ends with a
recommendation for the contracts and its rationale. Section numbers of report
[01](01-requirements-from-kb.md) (requirement ids C1-Rnn, decisions D-nn) are used where a finding
bears on them. Report [02](02-hif-standard.md) covers HIF itself, and report
[03](03-library-probes.md) covers how XGI and HyperNetX actually round-trip roles; neither is repeated.

## 0. Method, evidence labels, scope

- **[read]**: primary source fetched on 2026-09-23 with `curl` (or the Wikidata `Special:EntityData`
  and `action=raw` endpoints) and read from the downloaded text. Quotes are copied from that text.
- **[code]**: source code read at the stated version or commit, not executed.
- **[run]**: executed here; the probe is in [probes/prior-art/](probes/prior-art/).
- **[kb]**: stated in a KB note, which carries its own primary source.
- **[derived]**: my inference from the sources cited next to it.
- **[unverified]**: could not be checked.
- **Recommendation**: a proposal for the design stage, not an established result.

Two sources could not be fetched directly: the FrameNet host reset every connection, so the FrameNet
book was read from the Internet Archive copy of `framenet2.icsi.berkeley.edu/docs/r1.7/book.pdf`
(archived 2022-10-26); and the GitHub REST API is not enabled for this session, so repository facts
come from `git clone --filter=blob:none` and `git log` (commit ids given).

**What the KB already covers, and this report does not repeat.** The W3C n-ary note's two patterns
and their costs, schema.org `Role`, FrameNet's local frame elements and frame element groups,
TypeDB's `relates`/`plays`/nesting and write-time checks, SHACL 1.2 reifier shapes, ShEx 2.1's
status, and the comparison table of schema languages
([ontologies-and-schemas](../../../kb/02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md)
§1–§8). The Wikibase data model (snaks, main snak, qualifiers, references, ranks, RDF dump layers)
([wikidata-and-freebase](../../../kb/02-knowledge-representation/wikidata-and-freebase-data-models.md)
§2). Wikidata's required and allowed qualifier constraints, EntitySchemas in ShExC, Ferranti et al.'s
SHACL/SPARQL formalisation, and Gene Ontology evidence codes
([curation](../../../kb/03-construction/curation-crowdsourcing-and-quality.md) §1–§2). PROV-O
qualified terms, nanopublications, Datomic and TerminusDB
([versioning](../../../kb/04-storage-and-formats/versioning-provenance-and-scale.md) §1–§2). Graphiti's
bitemporal edges, TOKI's conflict policies and the key-role-set gap
([temporal-hyperedges](../../../kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md)
§1–§2; [incremental](../../../kb/03-construction/incremental-and-streaming-construction.md) §5).
`somevalue`/`novalue` and "deprecated is not false"
([open-world](../../../kb/02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md)
§3). Property-graph emulation patterns
([pg-emulation](../../../kb/04-storage-and-formats/property-graph-emulation-patterns.md) §1–§4).
RDF 1.2 syntax and rdflib's missing RDF 1.2 support
([rdf-star](../../../kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md);
[software-libraries](../../../kb/09-ecosystem/software-libraries.md) §3).

## Summary of findings

1. **Keys are not new; key semantics are not settled.** A key over a set of role-like attributes is
   declared by Wikidata's single-value constraint with separators (population's key is
   {subject, point in time, determination method, applies to part, applies to work}), OWL 2
   `HasKey`, LinkML `unique_keys`, the new SHACL 1.2 `sh:uniqueValuesFor` and, with validity time,
   SQL:2011 `WITHOUT OVERLAPS` (implemented in PostgreSQL 18). What a collision *means* differs:
   OWL 2 infers that the two individuals are the same, SQL rejects the write, Wikidata reports an
   advisory violation that editors resolve with ranks, and Graphiti invalidates the older edge. C1
   must declare the collision policy along with the key (M3).
2. **Wikidata keeps apart what report 01's case 3a treats as one supersession.** A fact that
   *stopped being true* gets an end time and stays normal rank; a fact that was *superseded or found
   wrong* gets deprecated rank with a reason (`P2241`); nothing sourced is deleted. `end cause`
   (`P1534`) and `reason for deprecated rank` (`P2241`) are the two "why" fields (M5).
3. **Graphiti does not record which edge invalidated which, and updates in place.** In graphiti-core
   0.30.2 contradiction is judged by an LLM prompt, the older edge gets `invalid_at` and
   `expired_at` set, and it is saved with `MERGE ... SET e = $edge_data`. The earlier state of the
   row is not kept as a version, so an as-at query for a time before the invalidation cannot be
   answered exactly [code; derived] (M4, M5).
4. **Three identifiers, not one, is established practice.** Wikibase gives statements opaque ids and
   gives snaks and references content hashes. INDRA keeps a random `uuid`, a *shallow* hash of the
   statement content (evidence excluded) and a *full* hash that includes the evidence. This matches
   report 01's D-05 (opaque id, core content key, event hash) (M3).
5. **TypeDB 3.x cannot hold literal role players or ordered roles.** Attributes "cannot have
   capabilities", so they cannot play roles; ordered role lists and `@distinct` are "not yet
   available"; role types are scoped to their relation (`parentship:parent`); `relates` defaults to
   `@card(0..1)`. This resolves report 01's [unverified] item on literal-valued bindings (M1, M2).
6. **Relation-local roles make P6's measurement trivial.** On 17 Wikidata properties with an
   allowed-qualifiers constraint, the schema hypergraph is α-cyclic under every global naming of
   the main-snak roles, and trivially α- and β-acyclic when roles are scoped to their relation, as
   TypeDB scopes them [run]. The naming of the subject and value roles does not change the outcome.
   Whether roles are global does (M8).
7. **Wikidata qualifiers are not all roles.** The two qualifiers allowed on all 17 sampled properties
   are `reason for deprecated rank` and `reason for preferred rank`. Others describe date
   uncertainty, dispute, support and surface names. These are statement metadata, and a C1 schema
   needs a slot class for them (M1, M8).
8. **Evidence spans need a code-point rule.** The W3C Web Annotation model requires selections "in
   terms of unicode code points ... not in terms of code units", with normalised text, and
   recommends a document State because positions are brittle. SemMedDB documents its argument end
   offset as "the last character position", which reads as an inclusive end (M6).
9. **Curation targets the (fact, evidence) pair.** INDRA's curation question is "Is there support in
   the evidence sentence for the Statement?". Its curation table stores the curated statement's
   content hash, the evidence hash, a tag, free text, the curator, a date, and JSON snapshots of the
   statement and the evidence. The Primary Sources Tool kept an approved / rejected / not-visited
   state per imported statement and a per-user activity log (M7).
10. **Plain JSON Schema draft-07 cannot count repeated roles in a list.** `minContains` and
    `maxContains` exist only from 2019-09, while `fastjsonschema`, which HyperNetX already depends
    on, implements drafts 04, 06 and 07. Keying bindings by role, as Wikibase keys qualifiers by
    property, makes role cardinality checkable with `minItems`/`maxItems` in draft-07 (M8).
11. **Store interfaces agree on a small core and disagree on everything temporal.** Add, get by id,
    incidence of a node, pattern lookup and remove appear everywhere. As-of, as-at and supersession
    appear only in Datomic, SQL:2011 and Graphiti. Conformance suites in the field are either
    parametrised over a registry of implementations with declared traits (rdflib) or data-driven
    manifests with expected results (W3C rdf-tests, openCypher TCK), and they report outcomes that
    include "inapplicable" (EARL) (M9).
12. **Two status updates for the base.** Kùzu announced it is archiving the project (README, commit
    of 2025-10-10). SPARQL 1.2 Query has a newer Working Draft (21 September 2026) than the KB's
    13 September. RDF 1.2 Concepts is still a Candidate Recommendation Snapshot of 7 April 2026.

---

## M1. Role identity, role typing and cardinality

*Decisions served: C1-R12 to R17, R19, R25, R26, R29, R34; D-03, D-04, D-12, D-15.*

**KB baseline.** Roles are either local (FrameNet) or global, RAM measured high reuse across arities,
and the KB recommends global role ids with per-relation usage (SCH §3; report 01 D-04).

### 1.1 Role inventories: local, global, or both

| Inventory | Scope of a role | Typing of fillers | Core/optional distinction | Evidence |
|---|---|---|---|---|
| **FrameNet** (book revised 1 Nov 2016) | Local to a frame; frames related by frame relations | Semantic type per frame element (`semType` in the NLTK reader) | Core, Peripheral, Extra-Thematic; "Core-Unexpressed" as notational shorthand | [read] Ruppenhofer et al. 2016; [code] NLTK `framenet.py` |
| **PropBank** | Numbered arguments local to a roleset ("No consistent generalizations can be made across verbs for the higher-numbered arguments"); modifiers (ArgM) global ("several more general roles that can apply to any verb") | none | numbered args vs ArgM | [read] Palmer, Gildea and Kingsbury 2005 |
| **VerbNet 3.4** | Global thematic roles; the 3.4 XML schema enumerates 42 base role names (104 values counting `?`-prefixed and `_i`/`_j`-indexed variants) | Selectional restrictions per role per class (38 restriction types in the schema; `logic="or"` combinations) | per class | [code] `cu-clear/verbnet` `verbnet3.4/vn_schema-3.xsd`, commit `ae8e9cf` (2023-11-08); `give-13.1.xml` |
| **Wikidata** | Global: every qualifier is a property usable anywhere its scope allows | `value-type constraint` (`Q21510865`), `subject type constraint` (`Q21503250`), `none-of` (`Q52558054`), `allowed units` (`Q21514353`) | `required qualifier` (`Q21510856`) vs `allowed qualifiers` (`Q21510851`); constraint status `mandatory` (`Q21502408`) or `suggestion` (`Q62026391`) | [read] entity JSON, 2026-09-23 |
| **TypeDB 3.x** | Scoped to the relation type: "a scope is required to resolve role type names ambiguity" (`parentship:parent`) | `plays` per player type | `@card` on `relates` | [read] TypeDB docs, `plays`, `relates`, `@card` |
| **LinkML 1.11** | Slots are global; `slot_usage` refines a slot "in the context of the containing class definition", including "local naming (e.g. subject=disease) and local constraints" | `range`, `any_of` | `required`, `minimum_cardinality`, `maximum_cardinality` | [code] `linkml-model` `meta.yaml` |
| **schema.org Role** | Role name is data (`roleName`) | weak | none | [kb] ONT §2 |

Three patterns recur. **Global vocabulary plus per-relation usage** (VerbNet's `THEMROLES` per class,
LinkML's `slot_usage`, Wikidata's per-property qualifier lists) keeps role identity shared and puts
the constraints on the usage. **Hybrid** (PropBank) makes the few participant roles local and the
many circumstance roles global. **Local** (FrameNet, TypeDB) needs a mapping layer to compare
relations: FrameNet's frame relations, TypeDB's `relates ... as` specialisation.

VerbNet's `give-13.1` shows the usage pattern directly: `Agent` restricted to `+animate` or
`+organization`, `Theme` unrestricted, `Recipient` restricted like `Agent`, and a subclass adding
`Asset` [code].

### 1.2 Co-occurrence constraints between roles

FrameNet encodes three relations between frame elements that no KB note records [read, Ruppenhofer et
al. 2016, §3.2.2]:

- **CoreSet**: "presence of any member of the set is sufficient to satisfy a semantic valence of the
  predicator". The example is Source, Path and Goal in motion frames. This is *at least one of*, not
  *all of*.
- **Requires**: "the occurrence of one core FE requires that another core FE occur as well" (in
  Attaching, Item requires Goal).
- **Excludes**: "if one of the FEs in a group of conceptually related FEs shows up, no other FE from
  that group can" (Items excludes Item and Goal).

The Excludes example is FrameNet's device for **symmetric roles**: "an alternation between a
symmetric construal, when a single frame element name is used, and an asymmetric construal, when two
frame elements ... are used" (`Items` vs `Item` + `Goal`; `Entities` vs `Entity_1` + `Entity_2`). The
plural role is the interchangeable one. VerbNet's `_i`/`_j` indexed roles and TypeDB's repeated role
(`relates page @card(0..1000)`) are the same idea in other clothes [read; code].

Wikidata has the across-property counterparts: `item-requires-statement` (`Q21503247`),
`conflicts-with` (`Q21502838`), and, within a statement, `required qualifier` [read]. Its help page
adds a schema well-formedness rule: "If the property also has an allowed qualifiers constraint, all
the required qualifiers must also be listed as permitted qualifiers there" [read, Required
qualifiers help page].

SHACL 1.2 has the pairwise comparisons that report 01's "must differ / must agree" (C1-R34) needs:
`sh:disjoint`, `sh:equals`, `sh:subsetOf` (new in 1.2), `sh:lessThan`, `sh:lessThanOrEquals` [read,
SHACL 1.2 Core WD 2026-09-18].

### 1.3 Two kinds of cardinality

The sources use "cardinality" for two different constraints, and a schema language needs both
[derived]:

- **Within-fact multiplicity**: how many fillers role *r* may have in one hyperedge. TypeDB `relates
  ... @card(N..M)`, SHACL `sh:minCount`/`sh:maxCount` on a relation-instance shape, LinkML slot
  cardinality on a relationship class. TypeDB's default for `relates` is `card(0..1)` and for
  `plays` is `card(0..)` [read]. A repeated role in TypeDB must therefore say so explicitly.
- **Across-fact participation**: how many facts of relation *R* one entity may take part in, in
  role *r*. TypeDB `plays ... @card`, Wikidata's `single-value constraint` (`Q19474404`, "this
  property generally contains a single value per item") and `distinct-values constraint`
  (`Q21502410`) [read]. With separators this becomes a key (M3).

SCH §3's `max` (report 01 C1-R14, C1-R25) is the first kind. Report 01's key role set (C1-R28) is the
second kind with time added.

### 1.4 Direction and scope of use

None of FrameNet, PropBank, VerbNet, Wikidata's qualifiers or TypeDB attaches a direction to a role.
Direction appears where the carrier is binary or explicitly directed: RDF properties, LinkML's
`relational_role` values `SUBJECT`/`OBJECT` (status `testing`), and HIF's `head`/`tail` [code; kb].

Wikidata's **property scope constraint** (`Q53869507`, parameter `P5314`) declares whether a
property may be used "as main value" (`Q54828448`), "as qualifier" (`Q54828449`) or "as reference"
(`Q54828450`) [read]. It is the deployed precedent for a per-role slot-class declaration (C1-R17).
`position held` (`P39`) allows main value and qualifier use, marked mandatory [read].

### 1.5 Recommendation (C1 schema language, role part)

- **Recommendation.** One global role vocabulary. Each relation type lists its role *usages*, and
  each usage carries: role id; filler kinds (entity types as a disjunction, like VerbNet's
  `logic="or"`, or datatypes); within-fact `min`/`max`; `ordered`; slot class; optional default
  direction; and optional local label and aliases. Add relation-level co-occurrence constraints:
  `requires` (A ⇒ B), `excludes` (not both), `at_least_one_of` (FrameNet's CoreSet), and pairwise
  `must_differ` / `must_agree`. Across-fact constraints do not go on the usage; they go in the key
  declaration (M3).
- **Recommendation.** Represent symmetric participation as one role with `max > 1`, unordered, never
  as `role_1`/`role_2`. For imports that use numbered pairs (FrameNet `Entity_1`/`Entity_2`,
  VerbNet `_i`/`_j`), the schema declares a fold rule to the plural role.
- **Rationale.** Global-plus-usage is the one pattern that keeps P6's attributes shared (M8 shows
  what local roles do to P6) while letting constraints differ per relation. It is also what LinkML
  and VerbNet already do, so exports are mechanical. The co-occurrence constraints come from
  FrameNet and Wikidata, where they are needed in practice. Keeping the two cardinalities apart stops
  "max 1 filler per fact" from being mistaken for "one fact per subject".

---

## M2. Literal-valued roles and special values

*Decisions served: C1-R06 to R09, R11, R68; D-09.*

- **Wikibase.** A snak is `value`, `somevalue` or `novalue`, and a main value or a qualifier may be of
  any datatype [kb; read, Wikibase JSON docs]. Time values carry a precision code from 0 (gigayear)
  to 14 (seconds), and codes 12–14 are marked unused. The `before`/`after` uncertainty fields are
  "Currently unused, may be dropped in the future" [read]. For a missing required qualifier, the help
  page says: "If the value is not known, it might make sense to use unknown value" [read]. The
  convention is thus that `somevalue` satisfies a required role [derived].
- **FrameNet null instantiation.** Definite null instantiation (DNI: "the missing element must be
  something that is already understood in the linguistic or discourse context") and indefinite null
  instantiation (INI, "sometimes also referred to as existential") [read]. INI is the linguistic
  counterpart of `somevalue`. DNI is a slot whose filler is recoverable from context, which is
  close to P11's UNBOUND slot but not the same thing [derived].
- **TypeDB 3.x.** "Attributes cannot have capabilities; they are merely typed associations of values
  to objects", and "Two attributes are considered equal if they have the same associate value and
  have the same (origin) type" [read, data model page]. A literal filler therefore cannot be a role
  player. It must be an attribute *owned* by the relation (`relation employment owns salary`).
  `@unique` refuses `double` because "Constraining double attributes by exact value is error-prone
  and as such disallowed" [read].
- **SHACL 1.2.** Literal comparison in `sh:uniqueValuesFor` "needs to be exact, e.g.
  `"04"^^xsd:byte` does not match `"4"^^xsd:integer`" [read].

**Recommendation.** Keep literals inline as typed values in C1, as report 01 D-09 proposes, and
define equality in C1 itself rather than inheriting it from a backend: normalise the lexical form
per datatype, then compare (value, datatype, precision, unit). Keep `somevalue` and `novalue` as
value kinds, and state that `somevalue` satisfies `min ≥ 1`. The TypeDB mapping for P1 is: entity or
hyperedge fillers become role players; literal fillers become owned attributes of the relation.
**Rationale.** TypeDB forces the split, and SHACL shows that a backend may compare RDF terms rather
than values. Without a C1-level rule, round-trip fidelity would depend on the store. Wikibase shows that precision codes are
enough and that uncertainty ranges go unused, so C1 should not add them to literals (M4 handles date
uncertainty separately).

---

## M3. Fact identity, content keys and declared keys

*Decisions served: C1-R01 to R03, R13, R15, R28, R52; C2-R04, R18; D-05, D-07; P7's identity cases.*

**KB baseline.** Opaque id plus content hash of the core (LIM §11), "opaque for the fact,
content-addressed for the extraction event" (VER §1), and the claim that "No n-ary model or schema
language surveyed in this KB declares" a key role set (TMP §1(b)).

### 3.1 Identifiers in deployed systems

| System | Record identity | Content identity | Evidence/event identity | Evidence |
|---|---|---|---|---|
| **Wikibase** | Statement `id`: "An arbitrary identifier for the Statement, which is unique across the repository. No assumptions can and shall be made about the identifier's structure" | Qualifier snaks and references carry a `hash` field | A reference is "a set of Snaks" with its own hash | [read] Wikibase JSON docs |
| **INDRA** (`sorgerlab/indra` @ `7ae3337`, 2026-06-30) | `uuid` (random, per object) | *Shallow* hash of `matches_key`: "differences in source, evidence, and so on are not included" | *Full* hash: equal "if the two Statements came from the same sentences, extracted by the same reader, from the same source"; `Evidence.source_hash` over source API, source id, text or PMID | [code] `statements.py`, `evidence.py` |
| **Graphiti** (graphiti-core 0.30.2) | `uuid4` per edge | none (duplicate judged by LLM) | `episodes`: list of episode ids that mention the edge | [code] `edges.py` |
| **KGTK** | Optional `id` column on edges; "Edges themselves can be attributed by having edges asserted about them" | none | `source` column: "Node or edge provenance" | [read] KGTK file specification |
| **MediaWiki** revisions | `rev_id`, `rev_parent_id` | `rev_sha1` content hash | `rev_actor`, `rev_timestamp`, `rev_comment_id` | [read] Manual:Revision table |

### 3.2 Duplicate policies

- **QuickStatements** (Wikidata's batch tool): "Existing statements with an exact match (property and
  value) will not be added again; however additional references might be added to the statement"
  [read]. Its de facto merge key is (item, property, main value), qualifiers excluded, and a
  duplicate becomes more evidence. Two `population` statements with equal value and different
  `point in time` would collide under this rule [derived].
- **Wikidata's own help** points the other way when a qualifier repeats: "if a person received an
  award more than once, they should have several P166 statements with one P585 qualifier each, not
  one P166 statement with several P585 qualifiers" [read, Single value help page]. A repeated
  time qualifier signals two facts, not one fact with two times.
- **INDRA preassembly**: duplicates share the `matches_key`, "can differ only in their associated
  Evidence objects", and are merged by keeping "the first instance ... and merges the lists of
  Evidence". Refinements are *not* merged but linked: "the more general versions of a given
  statement do not appear at the top level, but instead are listed in the `supports` field of the
  top-level statements" [code, `preassembler/__init__.py`]. This is P7's refinement case (report 01
  §6.1) with a working implementation: keep both, link specific to general.
- **Graphiti**: an LLM prompt returns `duplicate_facts` and `contradicted_facts`. A duplicate appends
  the episode to the existing edge's `episodes`. The prompt's example "Alice works at Acme Corp as a
  software engineer" vs "... as a senior engineer" is labelled "same relationship but updated title —
  contradiction, NOT a duplicate" [code, `prompts/dedupe_edges.py`,
  `utils/maintenance/edge_operations.py`].

### 3.3 Key declarations, and what a collision means

| Mechanism | What is keyed | Temporal? | On collision | Status | Evidence |
|---|---|---|---|---|---|
| Wikidata `single-value constraint` + `separator` (`P4155`) | (item, property) → value, unless separator qualifiers differ. `P4155`: "multiple values are allowed under that constraint if they have different values for this property" | via separators such as `P585` | advisory violation report; editors fix with ranks, splits, or new separators | deployed | [read] |
| Wikidata `single-best-value constraint` (`Q52060874`) | as above, but several values may exist and exactly one "should have preferred rank" | via separators | "edit the previous best statement (which has been superseded by the new one) and set it to normal rank" | deployed | [read] |
| OWL 2 `HasKey` | "no two distinct (named) instances of CE can coincide on the values of all" key properties | no | **identity inference**: the example ontology "entails ... `SameIndividual( a:Peter a:Peter_Griffin )`"; inconsistency only if the two are asserted different | W3C Rec, 11 Dec 2012 | [read] |
| LinkML `unique_keys` | Compound keys over slots, "exact_mappings: owl:hasKey"; `consider_nulls_inequal` switches to SQL NULL semantics | no | validation failure | LinkML 1.11 | [code] `meta.yaml` |
| SHACL 1.2 `sh:uniqueValuesFor` | "the values of one or more specified properties of a value node must be unique within all target nodes of the current shape" | no | validation result | **new** in SHACL 1.2 ("Added the new constraint component sh:uniqueValuesFor, see Issue 661"), Working Draft 2026-09-18 | [read] |
| SQL:2011 temporal key | `PRIMARY KEY (ENo, EPeriod WITHOUT OVERLAPS)`, so that "an employee belongs to exactly one department at any given time" | **yes** (application time, closed-open) | constraint violation | ISO standard (Kulkarni and Michels 2012) | [read] |
| PostgreSQL 18 | `UNIQUE`/`PRIMARY KEY (..., col WITHOUT OVERLAPS)`: "the other columns of the constraint will allow duplicates so long as the duplicates don't overlap ... (This is sometimes called a temporal key ...)"; `FOREIGN KEY (..., PERIOD col)` | yes (range types) | violation, enforced like an `EXCLUDE` constraint | PostgreSQL 18 docs | [read] |
| TypeDB 3.x `@key`, `@unique` | Only on `owns` (one attribute of an entity or relation); `@key` = `@unique` + `@card(1)` | no | write rejected | TypeDB 3.13.6 | [read] |
| Neo4j key constraints | "all properties exist and ... the combined property values are unique" for a label or a relationship type (Enterprise Edition) | no | write rejected | Cypher Manual, current | [read] |
| Graphiti | no declared key; LLM judges "contradiction" | yes | older edge invalidated | graphiti-core 0.30.2 | [code] |

**Refinement of the KB's claim** [derived from the table]. TMP §1(b) is right that no *n-ary KG
model* declares a key role set with validity time. But the pieces exist. Wikidata declares
functional dependencies with identifying qualifiers, advisory only. OWL, LinkML and SHACL 1.2
declare non-temporal compound keys over the properties of a relation-instance node. SQL:2011 and
PostgreSQL 18 declare exactly "at most one row with this key binding at any instant". The gap is
narrower than stated: nobody combines role-level keys, validity time and a declared collision
policy. The finding also sharpens P7's question. The same collision is read as "same fact" (OWL),
"reject" (SQL), "flag and rank" (Wikidata) or "supersede" (Graphiti).

**Identifying vs non-identifying qualifiers.** Wikidata's separators are the only deployed
declaration found of which qualifiers identify a fact (`population`: `P585`, `P459`, `P518`,
`P10663` on the single-value constraint; `P459`, `P585`, `P518` on single-best-value) [read,
`P1082` entity JSON]. All other qualifiers are refinements, which fits the monotonicity reading in
the KB (SCH §4, HyperMono) [kb; derived].

**Using a key in a relational store** [derived]. In an incidence table (`fact`, `role`, `entity`)
the key bindings are spread over several rows, so a `WITHOUT OVERLAPS` constraint cannot see them.
The fact row needs a *key digest* column (a hash of the relation and the canonical key bindings)
plus a validity range: `UNIQUE (relation, key_digest, valid WITHOUT OVERLAPS)`.

### 3.4 Recommendation (C1 identity and keys; C2 key lookup)

- **Recommendation.** Four identifiers, as in report 01 D-05, with the Wikibase/INDRA split as
  precedent. `id` is opaque and never parsed; Wikidata statement GUIDs are imported as a *source
  statement id*, not as C1 ids. `core_key` is a hash of the relation and the canonical core
  bindings. `key_digest` is a hash of the relation and the declared key bindings, present only when
  a key is declared. `event_hash` is per extraction event, like INDRA's full hash.
- **Recommendation.** A key declaration in the relation type: `key: {roles: [...], temporal: true |
  false, on_collision: reject | supersede_older | same_fact | flag}`. Default `flag` in the queue
  (C3) and `reject` in the store (C2-R18). `supersede_older` only on relations that opt in, and only
  through an explicit supersession record (M5). Key roles are the "identifying" qualifiers, so no
  separate flag is needed.
- **Recommendation.** C1 defines canonical equality (normalised literals with precision, unordered
  multisets for unordered roles), so that `core_key`, `key_digest` and SHACL or SQL exports agree.
- **Rationale.** The four collision semantics in the table are all in use and all defensible, so the
  format cannot pick one silently. Making the policy a declared field makes P7's identity test list
  executable and lets P1 compare stores on the same semantics. The digest column is what lets
  PostgreSQL 18 enforce temporal keys natively.

---

## M4. Time: valid time, transaction time, versions

*Decisions served: C1-R46 to R48, R54; C2-R02, R07, R08, R19; D-07.*

**KB baseline.** Bitemporal pair on the hyperedge, half-open intervals, Graphiti's four timestamps,
VITA's `(c, t₁, t₂)`, Datomic's transaction log (TMP §1; INC §5; VER §2).

**SQL:2011** [read, Kulkarni and Michels 2012]. Valid time is an *application-time period*
(`PERIOD FOR EPeriod (EStart, EEnd)`) and transaction time is a *system-versioned* table
(`PERIOD FOR SYSTEM_TIME`, `WITH SYSTEM VERSIONING`). "SQL:2011 has adopted a closed-open period
model". Updates can apply `FOR PORTION OF` a period, which splits rows. Queries use
`FOR SYSTEM_TIME AS OF`. "bitemporal tables" is the paper's term; the standard defines no term for
them. The system-time end of a current row is set to "the highest value of the column's data type"
(the example shows `9999-12-31 23:59:59`).

**Datomic** [read, Datomic docs]. "A datom is an immutable atomic fact that represents the addition
or retraction of a relation between an entity, an attribute, a value, and a transaction", expressed
as `(E, A, V, Tx, Op)`. "Datomic transactions add datoms, never updating or removing them", which
gives "a complete audit trail and the ability to query 'as of' points in time".

**Event sourcing** [read, Fowler 2005]: "Event Sourcing ensures that all changes to application state
are stored as a sequence of events". The capabilities it names are the ones P9 and P7 need:
"Complete Rebuild", "Temporal Query" and "Event Replay" (reverse a wrong past event and replay later
events). The article is marked by its author as a draft that will not be updated.

**Graphiti, as implemented** [code, graphiti-core 0.30.2, commit `16cdf70`, 2026-09-21].
`EntityEdge` has `valid_at` ("when the fact became true"), `invalid_at` ("when the fact stopped being
true"), `created_at`, `expired_at` ("datetime of when the node was invalidated") and `reference_time`.
In `resolve_edge_contradictions`, an older overlapping edge whose `valid_at` precedes the new edge's
gets `invalid_at = new.valid_at` and `expired_at = now`. The edge is saved with
`MERGE (source)-[e:RELATES_TO {uuid: ...}]->(target) SET e = $edge_data`. With the Kùzu backend the
edge is reified as a `RelatesToNode_` node between source and target. **Consequence** [derived]: the
row is overwritten, so an as-at query for a time before `expired_at` sees `invalid_at` already set.
The earlier belief ("valid with no known end") survives only by inference. SQL:2011
system-versioning, Datomic and nanopublications keep the earlier version as a separate immutable
record.

**Wikidata's time vocabulary** [read]. Besides `start time` (`P580`), `end time` (`P582`) and
`point in time` (`P585`), there are uncertainty bounds as qualifiers: `earliest date` (`P1319`),
`latest date` (`P1326`), `latest start date` (`P8555`), `earliest end date` (`P8554`),
`latest end date` (`P12506`), plus `valid in period` (`P1264`) and `end cause` (`P1534`, "used
together with the end date qualifier (P582) to specify the reason for the end"). In the probe
sample, `P1319`, `P1326`, `P8554`, `P8555` and `P585` are each allowed on 15 of 17 properties, and
`P580`, `P582` and `P1534` on 14 [run].

**Recommendation.**

- Half-open intervals for both times. Leave `t_invalid` / `t_expired` *absent* for "no end" instead of
  writing a sentinel such as SQL's maximum timestamp. Adapters for stores that need a sentinel
  convert at the boundary.
- **Stored record versions are immutable.** A change creates a new version (new version id, same
  fact id where identity is kept) and closes the old version's transaction interval. Stores may
  keep a "current" materialisation. Mutating in place, as Graphiti does, is non-conformant for C2.
- Valid-time *uncertainty* is optional and separate from the interval: `valid_from_bounds` and
  `valid_to_bounds` as (earliest, latest) pairs, mapped to and from `P1319`/`P1326`/`P8554`/`P8555`/
  `P12506`. `end_cause` is an optional field on a valid-time closure.
- The mapping from time qualifiers to valid time (report 01 C1-R47) is a declared rule in the schema,
  with `P580`/`P582`/`P585` as the default.
- **Rationale.** SQL:2011 and Datomic show that immutable versions are what make as-at answerable.
  Graphiti's code shows what goes wrong without them. Wikidata shows that date uncertainty is common
  enough in practice to need a place, and that it belongs to the interval, not to a literal's
  precision.

---

## M5. Supersession, deprecation, retraction and merge: the status lifecycle

*Decisions served: C1-R41 to R45; C2-R05, R08, R14, R19, R20; D-08, D-10, D-17.*

**Wikidata's three-way distinction** [read, Help:Deprecation and Help:Ranking, 2026-09-23]:

1. **Outdated but once true.** "If a value becomes out-of-date, for example: population change
   measured by a new census; spouse no longer applies due to divorce; position held no longer applies
   ... after an election — the value should not be deprecated, but instead an end time qualifier
   should be added." Rank stays normal, and `end cause` says why.
2. **Superseded or known wrong.** "Statements in Wikidata should be ranked as deprecated (and not
   removed) if they are: superseded (as opposed to 'outdated' ...); now known to be wrong, but were
   once thought correct." "A deprecated value should always have a `reason for deprecated rank`
   (P2241) qualifier." The reason items include `incorrect value` (`Q41755623`),
   `cannot be confirmed by other sources` (`Q25895909`), `not been able to confirm this claim`
   (`Q21655367`), `conflation` (`Q14946528`), `withdrawn identifier value` (`Q21441764`),
   `person found to be alive` (`Q21124171`), `election result invalidated` (`Q25235916`) and
   `withdrawn award` (`Q24629887`).
3. **Preferred.** The most current or consensus value, with `reason for preferred rank` (`P7452`).
   "For templates and queries, deprecated statements will never be used unless that is specifically
   requested."

Help:Ranking gives the reasons for not deleting: deprecation "allows other users to know not to
re-add the value", and it "provides a mechanism for representing the evolution of theories and
ideas". Separately, `replaced by` (`P1366`) and `replaces` (`P1365`) are *domain* succession between
entities in a role, used as qualifiers on `position held` and allowed on 7 of the 17 sampled
properties [read; run]. They are role bindings, not record lifecycle links.

**Nanopublications** [read, Nanopub-X vocabulary `nanopubx.ttl`]. `npx:retracts` (domain
`foaf:Agent`, range `np:Nanopublication`), `npx:supersedes` and `npx:invalidates` (both
`owl:IrreflexiveObjectProperty` between nanopublications), `npx:approvesOf` and `npx:disapprovesOf`
(agent to nanopublication). `retracts` and `supersedes` were defined in commit `9922656`
(2017-04-11), and the file was last changed 2025-07-11 [code, `peta-pico/ontologies`]. Retraction
and supersession are themselves published as new nanopublications, so the link is a record about a
record.

**PROV-DM** [read, W3C Rec 2013]. "Invalidation ... is the start of the destruction, cessation, or
expiry of an existing entity by an activity"; a revision "is a derivation for which the resulting
entity is a revised version of some original" (`prov:wasRevisionOf`); `prov:wasInvalidatedBy` and
`prov:invalidatedAtTime` exist in PROV-O.

**Merges of entities** [read, Help:Merge]. "Wikidata item IDs are designated as persistent
identifiers. Therefore, merged items should be redirected. Never reuse merged items for other
things." Bots later rewrite statements that point at the redirect. One bot does so 24 hours after the
merge. Mass rewrites can be reverted through edit groups.

**Suppression** [read, MediaWiki Manual:Revision table]. `rev_deleted` is a bitfield
(`DELETED_TEXT = 1`, `DELETED_COMMENT = 2`, `DELETED_USER = 4`, `DELETED_RESTRICTED = 8`), and
"DELETED_RESTRICTED indicates suppression". Hiding is per field and does not delete the revision.
This is the precedent for report 01's suppression tier (C1-R45).

**Graphiti** records no link from the invalidating edge to the invalidated one: a search of
`graphiti_core` for `invalidated_by` or `supersed` finds only prompt text [code].

**Recommendation (four axes, not one status field).**

| Axis | Values | Changed by | Precedent |
|---|---|---|---|
| **Record status** | `candidate` (queue only), `asserted`, `disputed`, `superseded`, `retracted`, `goal` | lifecycle events with actor, time and reason | nanopub `supersedes`/`retracts`; Primary Sources Tool states (M7) |
| **World validity** | valid-time interval plus optional `end_cause` | new version with a closed interval; *not* a status change | Wikidata "outdated → end time"; SQL:2011 application time |
| **Editorial rank** | `preferred`, `normal`, `deprecated`, plus `rank_reason` | curator action | Wikidata ranks, `P2241`, `P7452` |
| **Visibility** | visible, suppressed (per field) | governance action | MediaWiki `rev_deleted` |

- `superseded` means **belief revision** (a newer record replaces this one as the store's account),
  and it always carries a supersession record: superseding id, superseded id, reason code (a small
  vocabulary modelled on the `P2241` reasons: incorrect, unconfirmed, conflation, withdrawn), and
  evidence. A fact that *ended in the world* stays `asserted` with a closed valid-time interval.
  Report 01 case 3a is then an end of validity plus, optionally, a succession binding, not a status
  change. Case 3b (conflicting claims for the same interval) is `disputed`.
- Entity merges produce a redirect record (old id → new id) and never reuse the old id. Rewriting
  bindings is a separate, logged, revertible action (C3).
- **Rationale.** Wikidata runs the largest curated n-ary base and treats "no longer true" and "no
  longer believed" as different operations with different fields. Graphiti conflates them, and so
  would a single `superseded` status. For P7 and C5's memory scorer the difference is the difference
  between a correct historical answer and a stale one (report 01 C5-R19). Nanopublications and PROV
  both model supersession as a record *about* records, which supports report 01's D-10 (a meta
  hyperedge as the source of truth).

---

## M6. Evidence, provenance and confidence

*Decisions served: C1-R35 to R40, R49; C3-R03; D-13, D-14.*

**KB baseline.** Provenance is about the fact, never a role (SCH §5). PROV-O terms, nanopublications'
three graphs, and GO evidence codes (VER §1; CUR §1).

**Evidence records in deployed systems.**

- **INDRA `Evidence`** [code, `evidence.py`]: `source_api`, `source_id`, `pmid`, `text` ("Natural
  language text supporting the statement"), `annotations`, `epistemics` ("A dictionary describing
  various forms of epistemic certainty"), `context`, `text_refs` (DOI, PMID, URL...), `source_hash`,
  and `stmt_tag`.
- **Wikidata references** [read]: a reference is a set of snaks with its own hash. The common
  properties are `stated in` (`P248`), `reference URL` (`P854`), `retrieved` (`P813`),
  `imported from Wikimedia project` (`P143`), `Wikimedia import URL` (`P4656`), `based on heuristic`
  (`P887`, "indicates that the property value is determined based on some heuristic ... to be used as
  source") and `inferred from` (`P3452`). Help:Sources: "Statements that are only supported by
  'imported from Wikimedia project' are not considered sourced statements", and "It is recommended to
  not add a second reference which is explicitly based on the same source". Surface forms have their
  own qualifiers: `subject named as` (`P1810`) and `object named as` (`P1932`, "how the object's
  value was given in the source").
- **SemMedDB** [read, NLM SemMedDB database details page]: `SENTENCE` has `SENT_START_INDEX` and
  `SENT_END_INDEX`. `PREDICATION_AUX` has `SUBJECT_START_INDEX` ("The first character position (in
  document)"), `SUBJECT_END_INDEX` ("The last character position (in document)"), `SUBJECT_SCORE`
  ("The confidence score of the mapping between the subject string and the subject concept"), and the
  same for the object. The page states that the tools "will no longer be maintained as of December
  31, 2024". Releases are named `semmedVER30` and `semmedVER30_A`.
- **Hetionet v1.0** [read, `hetio/hetionet` README and `describe/definitions.json`]: "47,031 nodes of
  11 types and 2,250,197 relationships of 24 types". Every edge carries `source` ("The database from
  which the edge and its properties were gathered"), and a `license` attribute is applied "on a per
  node and per edge basis".

**Evidence and assertion typing.**

- **ECO** (release `2026-07-10`, as loaded in the EBI Ontology Lookup Service on 2026-09-22) [read,
  OLS API]. `manual assertion` (`ECO:0000218`): "could involve human review of computationally
  generated information". `automatic assertion` (`ECO:0000203`): "based on computationally generated
  information that is not reviewed by a person prior to making the assertion". The evidence branches
  are `evidence used in manual assertion` (`ECO:0000352`), `evidence used in automatic assertion`
  (`ECO:0000501`), `computational evidence used in automatic assertion` (`ECO:0007669`),
  `imported information used in automatic assertion` (`ECO:0000313`), `author statement`
  (`ECO:0000204`), `curator inference used in manual assertion` (`ECO:0000305`) and
  `documented statement evidence` (`ECO:0006151`).
- **EARL 1.0** (W3C Working Group Note, 2 Feb 2017) [read]. Assertion `mode` is `earl:automatic`,
  `earl:manual`, `earl:semiAuto`, `earl:undisclosed` or `earl:unknownMode`. This is the same axis as
  ECO's assertion method, from the testing world.

**Confidence as a derived quantity.** INDRA's `SimpleScorer` computes belief from the evidence list and
per-source priors [code, `belief/__init__.py`, `resources/default_belief_probs.json`]. Per source, the
probability of error is `syst[source] + prod(rand for that source's evidence)`. Belief is
`1 - prod(...)` over sources. Negated evidence is scored separately and combined as `pp * (1 - np)`.
The shipped systematic-error priors include 0.05 for readers such as `reach` and `trips`, 0.01 for
curated databases such as `biopax` and `signor`, and 0.1 for `gnbr`. Belief is therefore
recomputable, and it changes whenever evidence or priors change.

**Text-span selectors** [read, W3C Web Annotation Data Model, Rec 23 Feb 2017].
`TextQuoteSelector` has `exact`, `prefix` and `suffix`. `TextPositionSelector` has `start` and `end`,
where "Position 0 would be immediately before the first character" and "the end character is not"
included. "The selection of the text MUST be in terms of unicode code points (the 'character
number'), not in terms of code units." "The text MUST be normalized before recording in the
Annotation." The position selector "is very brittle with regards to changes to the resource", so
"it is RECOMMENDED that a State be additionally used". Selectors can be chained ("Refinement of
Selection"). Motivations include `assessing`, which fits a review verdict.

**Recommendation (evidence record).**

- Fields: `evidence_id`; `evidence_type`, from a small vocabulary mapped to ECO (curated, imported,
  extracted by model, inferred by completion, bound by agent); `assertion_mode` (`automatic`,
  `manual`, `semi_automatic`, mapped to ECO and EARL); a `source` block (document id, version or
  hash, URL, retrieval time, licence); `selectors` (a quote selector *and* a position selector, with
  half-open code-point offsets over NFC-normalised text); `activity` (tool, model, version, run id,
  prompt or skill version); `epistemics` (`negated`, `hypothesis`, as in INDRA); and an optional
  `binding_refs` list for evidence that supports particular bindings.
- Confidence is stored as `{value, scale, scorer, scorer_version}` and treated as derived:
  recomputable from evidence and never an identity field.
- Wikidata-style references import as evidence records. `P143`-only references get a weak
  `imported` type, not a document source. `P887` maps to `automatic`. `P1810` and `P1932` fill the
  quote selector when present.
- **Rationale.** INDRA and Wikidata both keep evidence as a list of structured records per fact and
  treat duplicates as more evidence. The Web Annotation rules settle offset ambiguity: C1 should
  *convert* SemMedDB-style inclusive ends and UTF-16 offsets at import. The ECO/EARL split between
  manual and automatic gives C1-R38 (model-inferred facts must be distinguishable) a standard
  vocabulary. Hetionet shows that licence travels with the edge and must survive integration.

---

## M7. Candidate queue and linter action log (C3)

*Decisions served: C3-R01 to R14; D-18, D-21.*

**Queue precedents.**

- **Primary Sources Tool** (Wikidata; as described in January 2016) [read, Pellissier Tanon et al.
  2016]. It was "a crowd-sourced human curation software solution that displays Freebase statements
  for verification to the Wikidata contributor". Statements were stored "with an additional status field to keep track
  of statements that either already have been approved, rejected, or not yet visited". They were
  grouped in "'datasets' (set of statements from the same origin) and 'uploads' (set of statements
  uploaded at the same time)". The API set state per statement (`POST
  /statements/1?state=approved&user=Alice`). Claims and references were approved separately, and
  "All update activity around statements is logged in an activity log". By January 2016 it had "more
  than a hundred users who performed about 90,000 approval or rejection actions", and "More than 14
  million statements have been uploaded in total".
- **INDRA curation** [code, `doc/tutorials/html_curation.rst`]. The unit is a statement *and* one
  piece of evidence: "Is there support in the evidence sentence for the Statement?" The verdicts are
  `correct` plus error types: entity boundaries, grounding, polarity, no relation, wrong relation
  type, activity vs amount, negative result, hypothesis, agent conditions, modification site, and
  other (with a mandatory description). The INDRA DB `curation` table has `id`, `pa_hash` (foreign
  key to the preassembled statement's `mk_hash`), `source_hash`, `tag`, `text`, `curator`,
  `auth_id`, `source`, `ip`, `date`, `pa_json` and `ev_json` [code, `indralab/indra_db`
  `principal_schema.py`, last changed 2025-02-07]. Curations are keyed by *content hashes*, so they
  survive re-extraction, and they store JSON *snapshots* of what was judged.
- **ORKG templates** [read, ORKG help page "Templates", site version 0.190.0]: templates make
  "research contributions that address the same research problem conform to the same data
  structure", with "accepted values and the cardinality for each field".

**Lint-finding precedents.**

- **SHACL validation results** [read, SHACL 1.2 Core WD]: `sh:focusNode`, `sh:resultPath`,
  `sh:value`, `sh:sourceShape`, `sh:sourceConstraintComponent`, `sh:detail`, `sh:resultMessage` and
  `sh:resultSeverity`. Severities are `sh:Trace` and `sh:Debug` ("not a constraint violation"),
  `sh:Info`, `sh:Warning` and `sh:Violation`.
- **Wikidata constraint metadata** [read]: `constraint status` (mandatory or suggestion),
  `exception to constraint` (`P2303`), `constraint clarification` (`P6607`), and fix hints
  `replacement property` (`P6824`) and `replacement value` (`P9729`). A constraint can thus declare
  its own auto-fix.
- **EARL** [read]: an assertion has `assertedBy`, `subject`, `test`, `result` and `mode`. Outcomes are
  `passed`, `failed`, `cantTell`, `inapplicable` and `untested`.
- **MediaWiki revisions** [read]: id, parent id, actor, timestamp, comment (edit summary), content
  hash and suppression bits. A revision log that reconstructs before and after from parent and child.

**Recommendation (C3).**

- **Queue record.** A C1 payload with status `candidate`. Metadata: dataset, upload or run, and
  insertion position (the Primary Sources Tool's grouping plus report 01 C3-R02). Queue state:
  `pending` → `linted` → `accepted` | `rejected` | `needs_review` | `merged`. The accepted state links
  to the store id. Claims and their evidence records can be judged separately.
- **Verdicts** attach to (candidate, evidence) pairs, as in INDRA, and are keyed by `core_key` and
  `event_hash`, not by queue id, so they carry over to re-extractions. The vocabulary is INDRA's tags
  generalised to roles: `correct`, `no_relation`, `wrong_relation`, `wrong_role`, `wrong_filler`
  (grounding), `span_boundary`, `missing_participant` (the "incomplete" verdict of report 01
  C3-R06), `negated`, `hypothesis`, and `other` with mandatory text. `binding_refs` say which
  bindings were wrong.
- **Linter log entry**: `log_id`, `target` (queue or store id, plus `core_key`), `rule_id` and
  `rule_version` (like `sh:sourceConstraintComponent` and `sh:sourceShape`), `path` (role, like
  `sh:resultPath`), `value`, `severity` (SHACL's five levels), `message`, `action` (`reject`, `flag`,
  `auto_fix`, `propose_merge`, `propose_supersession`), `before` and `after` snapshots (INDRA's
  `pa_json`/`ev_json`), `actor`, `mode` (EARL/ECO), `timestamp`, and `parent_log_id` (MediaWiki's
  parent revision) so that replay is well defined.
- **Rationale.** The Primary Sources Tool is a working precedent for "the machine proposes, people
  judge" at the scale of millions of statements. INDRA shows that verdicts must name the evidence and
  survive re-extraction. SHACL gives a standard shape for a finding, which makes the structural linter
  exportable as a SHACL-like report. Snapshots plus a parent pointer are what the Primary Sources
  Tool's activity log lacked for replay.

---

## M8. The relation-type schema language

*Decisions served: C1-R25 to R34; D-04, D-15; P6's gate.*

### 8.1 Comparison against what C1 must declare

"yes" means native. "enc." means by encoding (relation as class or node). "—" means absent. Versions
checked 2026-09-23.

| Feature | JSON Schema (2020-12 / draft-07) | LinkML 1.11 | SHACL 1.2 (WD) | ShEx 2.1 | TypeQL 3.x | Wikibase constraints | Table Schema v2 |
|---|---|---|---|---|---|---|---|
| Role names | property names | global slots + `slot_usage` | property paths on a relation node (enc.) | triple constraints (enc.) | `relates` (relation-scoped) | global properties; qualifiers per property | fields (per table) |
| Allowed filler types | `type`/`$ref`/`enum` | `range`, `any_of` | `sh:class`, `sh:datatype`, `sh:node` | node constraints | `plays` | value-type, subject-type, one-of, none-of | field `type`, `constraints` |
| Within-fact min/max | `minItems`/`maxItems` on a role-keyed object; list form needs `minContains`/`maxContains` (2019-09+) | `required`, `multivalued`, min/max cardinality | `sh:minCount`/`sh:maxCount`, qualified counts | cardinality on triple constraints | `relates @card` (default `0..1`) | loose; single-value can target qualifiers | `required`; `minLength`/`maxLength` on array fields |
| Keys | `uniqueItems` compares whole items only | `unique_keys` (↔ `owl:hasKey`) | `sh:uniqueValuesFor` (new, WD) | — | `@key`/`@unique` on `owns` only | single-value + separators (advisory) | `primaryKey`, `uniqueKeys`, `foreignKeys` |
| Temporal key | — | — | — | — | — | via separators on time qualifiers | — |
| Direction | field | `relational_role` SUBJECT/OBJECT (testing) | inherent in paths | inherent | — | subject → value | — |
| Symmetric / interchangeable roles | repeated role | `symmetric` (binary slots), `NODE` role | — | — | repeated role with `@card` | symmetric constraint (binary) | — |
| Literal-valued roles | yes | yes | yes | yes | only as owned attributes | yes | yes |
| Co-occurrence (requires / excludes) | `dependencies` (07), `dependentRequired` (2019-09+), `not` | `rules` [unverified in detail] | `sh:and`/`sh:or`/`sh:xone`/`sh:not`, pair constraints | `AND`/`OR`/`NOT` | — | item-requires-statement, conflicts-with (across statements) | — |
| Python validator | `fastjsonschema` 2.22.2 (drafts 04/06/07, **0 deps**, already a HyperNetX dependency); `jsonschema` 4.26.0 (2020-12; `attrs`, `referencing`, `rpds-py`, which needs Python ≥ 3.11 in 2026.6.3) | `linkml` 1.11.1 has 25 core deps; `linkml-runtime` 1.11.1 has 14, incl. rdflib and pydantic | `pyshacl` 0.40.1 (rdflib, owlrl, ...) | `PyShEx` 0.9.0 (9 deps) | needs a TypeDB server (`typedb-driver` 3.13.6) | none; Wikidata checks constraints itself and reports violations, which are advisory [kb, CUR §2] | `frictionless` 5.19.0 (20 deps) |
| P6 can parse it into attribute hyperedges | yes, if roles are keys | yes, with SchemaView for inherited slots | yes, over relation-class shapes | yes (ShExJ is JSON) | via schema queries; roles scoped (see 8.2) | yes (probe below) | yes (tables → hyperedges) |

Sources for the table: JSON Schema specification page ("The current version is 2020-12"),
draft-07 and 2020-12 validation specifications (draft-07 has `contains` and `dependencies` but no
`minContains`/`maxContains`), fastjsonschema README ("implements JSON schema drafts 04, 06, and
07"), PyPI metadata for every package listed, LinkML `meta.yaml`, SHACL 1.2 Core, TypeDB docs,
Wikidata help pages, Data Package v2 Table Schema [read or code, 2026-09-23]; ShEx 2.1 status [kb,
ONT §7].

### 8.2 Probe: what P6 would measure on Wikidata's declared schemas [run]

`probes/prior-art/wikidata_schema_hypergraph_probe.py` fetched 20 frequently qualified properties.
Seventeen have an `allowed qualifiers` constraint; `P2139`, `P361` and `P793` do not. For each of
those 17 the probe built one hyperedge {subject role, main-value role} ∪ allowed qualifiers, under five
namings of the main-snak roles. It then ran GYO reduction (α-acyclicity) and nest-point elimination
(β-acyclicity). The allowed lists are long: 104 qualifiers for `position held`, 80 for `occupation`,
73 for `award received`. Results are in
[wikidata_schema_hypergraph_results.md](probes/prior-art/wikidata_schema_hypergraph_results.md).

| Naming of roles | α-acyclic | β-acyclic | GYO residue (hyperedges / vertices) |
|---|---|---|---|
| A generic `subject`, `value` | no | no | 17 / 126 |
| B `subject`, `value@P` | no | no | 17 / 125 |
| C `subject@P`, `value@P` | no | no | 17 / 124 |
| E `subject`, and the main value's role is `P` itself | no | no | 16 / 129 |
| D every role scoped to its relation (TypeDB-style) | yes (trivially) | yes | 0 / 0 |

Removing the statement-metadata qualifiers, and then also the temporal ones, leaves A, B, C and E
cyclic, with residues of 16 or 17 hyperedges and 103 to 120 vertices.

**Reading** [derived]. (i) Naming the subject and main-value roles generically (A) or per property
(B, C) cannot change α-acyclicity. An attribute shared by *every* relation, or present in only one,
never does: a join tree for the rest remains a join tree. Naming the main value's role after its
property (E) could change it in principle, because that property may be a qualifier elsewhere. In
this sample it did not. So the main-snak naming question in report 01 (D-04, open question 4) does
not decide P6's class. (ii) Global versus relation-local role identity decides everything: under D
the schema is a disjoint union. (iii) The most shared attributes are not roles. `reason for
deprecated rank` (`P2241`) and `reason for preferred rank` (`P7452`) are allowed on all 17
properties, and the date uncertainty qualifiers on 15. P6's measurement must say which qualifier
classes it includes, and whether it measures *allowed* lists (up to 104 qualifiers here) or qualifier
sets *observed* in data. Observed sets were not measured here. Hypertree width was not computed;
that belongs to P6.

### 8.3 Recommendation (schema language)

- **Recommendation.** The C1 schema language is its own small JSON document, validated by a JSON
  Schema meta-schema in **draft-07**, plus a Python semantic validator. Its concepts deliberately
  mirror LinkML: global roles (slots), per-relation usages (`slot_usage`), `unique_keys` for
  non-temporal keys, and relationship classes. A LinkML export is then mechanical, and SHACL 1.2
  (`sh:uniqueValuesFor`, reifier shapes) and TypeQL are generation targets. The language adds what
  none of them has: temporal keys with a collision policy (M3), slot classes `core` / `qualifier` /
  `time` / `meta` (the Wikidata probe shows `meta` is needed), co-occurrence constraints (M1), and a
  semantic version in the schema id.
- **Recommendation.** Bindings in C1 records are an object keyed by role id, each value a list of
  binding objects, with a `position` only on `ordered` roles. This is the shape Wikibase uses for
  qualifiers: a map from property id to a list of snaks, plus `qualifiers-order`. A generated
  per-relation JSON Schema can then check required roles (`required`), allowed roles
  (`additionalProperties: false`), within-fact cardinality (`minItems`/`maxItems`) and filler kinds
  (`items`) in draft-07, and `fastjsonschema` can run it with no new dependency. Keys, time,
  references and acyclicity stay in the semantic validator.
- **Rationale.** Every existing language lacks at least one thing C1 needs (temporal keys, slot
  classes, lightweight Python validation), and the heavy ones (LinkML, SHACL, ShEx) bring rdflib and
  pydantic into what should be a small, offline validator (report 01 C1-R73). Draft-07 matches HIF's
  own schema dialect (report 01, V-HIF) and runs with a zero-dependency validator the gate
  environment already has. The role-keyed shape is what makes draft-07 sufficient.

---

## M9. Store interface (C2) and its conformance suite

*Decisions served: C2-R01 to R20; D-16.*

### 9.1 What stores and libraries offer

| Operation | HyperNetX 2.4.3 | XGI 0.10.2 | HypergraphDB (Java) | rdflib 7.6.0 `Store` | TypeDB 3.x driver | Cypher (Neo4j; Kùzu 0.11.3) | Graphiti 0.30.2 |
|---|---|---|---|---|---|---|---|
| add | `add_edge`, `add_node`, `add_incidence(edge, node, **attr)` | `add_edge(members, idx, **attr)`, `add_node_to_edge` | `add(atom)`, `define(handle, atom)` | `add(triple, context)`, `addN(quads)` | TypeQL `insert` in a write transaction | `CREATE`/`MERGE` | edges saved by `MERGE ... SET` |
| get by id | properties and incidence views | `edges.members(e)`, `edges.attrs` | `get(handle)` | `triples((s, None, None))` | `match` | `MATCH` | `get_by_uuids` |
| incident edges of a node | `nodes.memberships` | `nodes.memberships(n)` | `getIncidenceSet(handle)`: "the set of all `HGLink`s pointing to" the atom | `triples((None, None, o))` | `links` patterns [kb, QL §3] | `MATCH (n)-[r]-()` | by node uuid [unverified in detail] |
| pattern lookup | `restrict_to_edges`/`nodes` | `filterby` | `find(condition)`, `count` | `triples(pattern)`, `triples_choices`, `query` | `match` | `MATCH ... WHERE` | search |
| remove | `remove_edges`, `remove_incidences` | `remove_edge`, `remove_node_from_edge` | `remove(handle, keepIncidentLinks)` | `remove` | `delete` | `DELETE` | `delete_by_uuids` |
| replace / update | property store | `set_edge_attributes` | `replace(handle, atom)`, `update` | remove + add | TypeQL in a transaction | `SET` | in-place `SET` |
| transactions | — | — | [unverified] | `commit`/`rollback` when `transaction_aware` | `TransactionType.READ`/`WRITE`/`SCHEMA`, `commit`, `rollback` | yes [not re-checked here] | — |
| role on membership | cell properties | — (edge-level only) | position in the target tuple (`getTargetAt(i)`) | predicate | role type | relationship type or property | — |
| as-of / as-at | — | — | — | — | — | — | `valid_at`/`invalid_at`/`expired_at` fields |
| capability flags | — | — | — | `context_aware`, `formula_aware`, `transaction_aware`, `graph_aware` | — | — | — |

Evidence: [code] wheel sources for HyperNetX and XGI; `HyperGraph.java` and `HGLink.java`
(`hypergraphdb/hypergraphdb` @ `99485a1`, 2024-09-14); `rdflib/store.py` @ tag `7.6.0`; the
`typedb` package in the `typedb-driver` 3.13.6 wheel; graphiti-core 0.30.2. How XGI and HyperNetX
behave on role-labelled HIF is executed and reported in [03](03-library-probes.md). The Kùzu README
states: "We are archiving the KuzuDB project here ... we have a new release 0.11.3 that bundles many
(but not all) of the extensions" (commit `06890e1`, 2025-10-10).

**The common core** [derived]: add, get by id, incidence of a node, pattern lookup, remove, and a
serialisation. **Nobody offers** key lookup with temporal semantics, a supersession walk, or as-at
reconstruction except the temporal systems (SQL:2011, Datomic, Graphiti in part). Roles on
memberships are native only in HyperNetX (cell properties), TypeDB (role types) and property graphs
(relationship types). HypergraphDB's roles are positions.

### 9.2 How conformance is tested elsewhere

- **rdflib** [code, `test/test_store/test_namespace_binding.py` @ 7.6.0]: a `StoreInfo(name,
  traits)` registry, where traits such as `WRAPPER` and `DISK_BACKED` change setup. A module-scoped
  pytest fixture is parametrised over the registry, and a `make_graph(tmp_path, store_name)` factory
  builds each store. The same test body runs against every store, and the traits say what applies.
- **W3C rdf-tests** [read, `w3c/rdf-tests`, `rdf/rdf12/rdf-turtle/`]: a manifest (`mf:Manifest`,
  `mf:entries`) of typed tests. For RDF 1.2 Turtle there are 41 `rdft:TestTurtlePositiveSyntax`, 33
  `rdft:TestTurtleNegativeSyntax` and 32 `rdft:TestTurtleEval` (each an `mf:action` input and an
  `mf:result` expected output). Implementations report results in EARL, whose outcomes include
  `inapplicable` and `untested`.
- **openCypher TCK** [read, `tck/README.adoc`]: Cucumber `.feature` files that specify "The required
  initial state of the graph", the query with its parameters, "Expected results ... or expected
  errors", and "Expected side effects"; an implementation hooks in "via implementing a small
  interface".

### 9.3 Recommendation (C2)

- **Operations** (report 01 C2-R01 to R06, named after the common core): `put` (a new immutable
  version; idempotent on identical content), `get(id, as_of?, as_at?)`, `incident(node, role?,
  relation?, status?, as_of?, as_at?)`, `find(relation, bindings, match=at_least|exact, as_of?,
  as_at?)` (key lookup is `find` with the declared key roles), `supersession_walk(id, direction)`,
  `lifecycle(event)` (supersede, retract, dispute, rank, suppress, redirect entity: one atomic write
  per event), and `export(format)`. Every read takes as-of and as-at. The defaults are "now" and
  status `asserted`.
- **Capability flags**, as in rdflib: `temporal_valid`, `temporal_tx`, `nesting`,
  `literal_role_players`, `ordered_roles`, `native_keys`, `transactions`. A test that needs a missing
  capability is reported `inapplicable`, never `passed`.
- **Conformance suite**: declarative scenario files (JSON), each with `given` (records and lifecycle
  events), `when` (one operation with arguments and times), `then` (expected canonical result, or an
  error code), and `side_effects` (expected store state), in the style of the openCypher TCK. Three
  test kinds follow the W3C manifests: validator positive, validator negative (report 01's
  malformed-case list), and evaluation (round-trip or operation to expected canonical output). A
  pytest runner is parametrised over a registry of store adapters with capability traits, as in
  rdflib. It writes an EARL-shaped JSON report.
- **Rationale.** Scenario files can be shared with P1 and run unchanged against five backends. The
  W3C split (positive, negative, eval) maps directly onto the P2 gate's validator list and round-trip
  test. Capability flags stop a backend that cannot do as-at, such as an in-place store like
  Graphiti, from silently passing temporal tests.

---

## 10. Corrections and additions for the KB (proposed, not applied)

| KB note | Proposed change | Evidence |
|---|---|---|
| `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md` §1(b) | Qualify "No n-ary model or schema language ... declares one": Wikidata single-value constraints with separators, OWL 2 `HasKey`, LinkML `unique_keys`, SHACL 1.2 `sh:uniqueValuesFor` and SQL:2011/PostgreSQL 18 temporal keys all declare keys. What is missing is the combination with n-ary roles, validity time and a collision policy. | M3 |
| same note, §2 | Graphiti keeps no link from invalidating to invalidated edge, and overwrites the edge row (`MERGE ... SET`) | M4, M5 |
| `kb/04-storage-and-formats/hypergraph-databases.md` (Kùzu row) and notes that list Kùzu | Kùzu announced it is archiving the project; 0.11.3 (2025-10-10) is the final bundled release | M9 |
| `kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md`, `kb/09-ecosystem/standards-bodies-and-specifications.md` | SPARQL 1.2 Query: Working Draft of 21 September 2026 now at `/TR/`. Add "RDF 1.2 Interoperability", Group Note Draft of 23 July 2026, with "basic encoding" of triple terms; and the version labels `1.2`, `1.2-basic`, `1.1` with Basic and Full conformance from RDF 1.2 Concepts | [read] |
| `kb/02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md` §5 | TypeDB 3.x: attributes cannot play roles; ordered role lists "not yet available"; `relates` defaults to `@card(0..1)`; role types are relation-scoped | M1, M2 |
| same note, §3 | FrameNet CoreSet / Requires / Excludes, symmetric construal, null instantiation; PropBank's local numbered args and global ArgM; VerbNet 3.4 role and restriction inventory | M1 |
| `kb/03-construction/curation-crowdsourcing-and-quality.md` | Primary Sources Tool (states, datasets and uploads, activity log, usage in January 2016); INDRA curation tags and curation table; Wikidata property scope and separator constraints | M3, M7 |

## 11. Risks to the P2 gate and to the design

1. **Key semantics left implicit.** If C1 declares key roles without a collision policy, P7, P1 and
   P9 will each pick one of the four semantics in M3. P7's identity test list then has no single
   right answer.
2. **"Superseded" overloaded.** Using one status for "ended in the world" and "replaced as belief"
   (Graphiti's choice) makes C5's stale-answer rate unmeasurable and contradicts Wikidata data that
   P3a will import.
3. **In-place stores pass as bitemporal.** A store that overwrites rows can answer as-of but not
   as-at. Without conformance scenarios that check as-at reconstruction, such a store passes C2.
4. **JSON Schema dialect mismatch.** A C1 schema that relies on `minContains`/`maxContains`
   (2019-09+) will not run under `fastjsonschema` (draft-07), and one written for 2020-12 would make
   `jsonschema`, with its compiled `rpds-py` dependency, a runtime dependency of the package. The
   draft decision and the binding shape have to be taken together.
5. **TypeDB fidelity for P1.** Literal fillers become owned attributes, not role players. Ordered
   roles have no native form. A goal hyperedge with only unbound roles is deleted as a "dangling
   relation". Role types are scoped per relation. A round-trip through TypeDB needs mapping rules for
   all four, or P1 will report fidelity losses that are really mapping gaps.
6. **Offsets.** Code points (Web Annotation, Python `str`), UTF-16 code units (JavaScript) and
   inclusive ends (SemMedDB's "last character position") will misalign P9's strict span matching
   unless C1 fixes one convention and converts at import.
7. **Wikidata qualifiers imported as roles.** If P3a maps every qualifier to a role binding, arity is
   inflated by statement metadata (`P2241` and `P7452` are allowed everywhere) and P6's attribute set
   is dominated by non-roles. The slot class `meta` and a per-property qualifier classification are
   needed before C4 is built.
8. **Standards still moving.** RDF 1.2 syntaxes, SPARQL 1.2 and SHACL 1.2 are Working Drafts, and
   RDF 1.2 Concepts is a Candidate Recommendation. `sh:uniqueValuesFor` and the reifier shapes may
   change. C1's primary RDF mapping should stay on the relation-instance pattern, which is valid as
   `1.2-basic` and readable by RDF 1.1 tools such as rdflib 7.6.0.
9. **Backend churn.** Kùzu announced it is archiving the project, so a P1 property-graph arm built on
   it is pinned to 0.11.3.
10. **LLM-judged identity is not reproducible.** Graphiti's duplicate and contradiction decisions come
    from a prompt, so it cannot serve as P7's reference without declared keys.

## 12. Open design decisions (options and recommendations)

- **O1 Role identity.** Global with usage (LinkML, VerbNet, Wikidata) / relation-local (TypeDB,
  FrameNet) / hybrid (PropBank). *Recommend global with usage*; TypeDB export names scoped roles
  after the global id. The probe shows local roles trivialise P6.
- **O2 Binding shape.** Role-keyed object of lists (Wikibase qualifiers) / list of `{role, value}`
  pairs. *Recommend role-keyed*, for draft-07 checkability. It converts deterministically to HIF's
  one incidence per (edge, node) pair carrying a role list.
- **O3 Key declaration.** Roles only / roles and temporal flag / roles, temporal flag and collision
  policy. *Recommend all three*, with `flag` in the queue and `reject` in the store by default.
- **O4 Lifecycle model.** Single status / status and rank / four axes (status, validity, rank,
  visibility). *Recommend four axes*; `superseded` only for belief revision.
- **O5 Supersession carrier.** Field on the new record / meta-record / both. *Recommend a
  meta-record as the source of truth, with a reason code, plus a field as an index* (nanopub, PROV).
- **O6 Versioning.** In-place with timestamps (Graphiti) / immutable versions (SQL:2011
  system-versioning, Datomic). *Recommend immutable versions*, required by C2 conformance.
- **O7 Evidence typing.** Free text / ECO-mapped `evidence_type` plus `assertion_mode` / full ECO ids.
  *Recommend a small ECO-mapped vocabulary plus mode*, with ECO ids as optional cross-references.
- **O8 Span convention.** Code points, half-open, NFC-normalised, with document hash, quote *and*
  position selectors. *Recommend it*; convert all other conventions at import.
- **O9 Verdict unit.** Per candidate / per (candidate, evidence) pair. *Recommend per pair*, keyed by
  content hashes, with an aggregation rule to a candidate verdict.
- **O10 Schema syntax.** Own JSON, LinkML-shaped / LinkML itself / SHACL. *Recommend own JSON with
  LinkML-compatible concepts and generators*; revisit LinkML if the generators cost more than the
  language.
- **O11 JSON Schema dialect.** Draft-07 with `fastjsonschema` / 2020-12 with `jsonschema`.
  *Recommend draft-07*, matching HIF and needing no new dependency.
- **O12 Slot classes.** `core` / `qualifier` / `time` / `meta`. *Recommend all four*; `meta`
  qualifiers import into record fields (rank reason, dispute, surface form) and are excluded from
  arity and from P6's schema hypergraph.
- **O13 Conformance format.** Code-only tests / declarative scenarios with a runner and EARL-shaped
  report. *Recommend declarative scenarios*, shared with P1.

## Probe

- [probes/prior-art/wikidata_schema_hypergraph_probe.py](probes/prior-art/wikidata_schema_hypergraph_probe.py):
  fetches `Special:EntityData` for 20 properties (1.5 s apart, cached outside the repository), builds
  the schema hypergraph under five role-naming conventions and three qualifier sets, and runs GYO and
  nest-point elimination. The acyclicity functions were checked on textbook cases (path, triangle,
  triangle with a covering edge, 4-cycle with a shared vertex) before use. Outputs:
  [results.md](probes/prior-art/wikidata_schema_hypergraph_results.md) and
  [results.json](probes/prior-art/wikidata_schema_hypergraph_results.json). The classes `meta` and
  `temporal` are this probe's reading of the properties' English descriptions, not a Wikidata
  classification.

## Sources

All web sources were fetched on 2026-09-23 unless stated otherwise.

### Standards and specifications

- W3C. *RDF 1.2 Concepts and Abstract Data Model*. Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. *RDF 1.2 Semantics*. Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-semantics/
- W3C. *RDF 1.2 Turtle*. Working Draft, 14 September 2026. https://www.w3.org/TR/rdf12-turtle/
- W3C. *RDF 1.2 TriG*. Working Draft, 15 September 2026. https://www.w3.org/TR/rdf12-trig/
- W3C. *RDF 1.2 N-Triples*. Working Draft, 23 July 2026. https://www.w3.org/TR/rdf12-n-triples/
- W3C. *RDF 1.2 Interoperability*. Group Note Draft, 23 July 2026. https://www.w3.org/TR/rdf12-interop/
- W3C. *SPARQL 1.2 Query Language*. Working Draft, 21 September 2026. https://www.w3.org/TR/sparql12-query/
- W3C. *SHACL 1.2 Core*. Working Draft, 18 September 2026. https://www.w3.org/TR/shacl12-core/
- W3C. *Shapes Constraint Language (SHACL)*. Recommendation, 20 July 2017 (checked for the absence of `sh:uniqueValuesFor`). https://www.w3.org/TR/shacl/
- W3C. *OWL 2 Web Ontology Language Structural Specification and Functional-Style Syntax (Second Edition)*. Recommendation, 11 December 2012, §9.5 Keys. https://www.w3.org/TR/owl2-syntax/
- W3C. *PROV-DM: The PROV Data Model*. Recommendation, 30 April 2013. https://www.w3.org/TR/prov-dm/
- W3C. *PROV-O: The PROV Ontology*. Recommendation, 30 April 2013. https://www.w3.org/TR/prov-o/
- W3C. *Web Annotation Data Model*. Recommendation, 23 February 2017. https://www.w3.org/TR/annotation-model/
- W3C. *Evaluation and Report Language (EARL) 1.0 Schema*. Working Group Note, 2 February 2017. https://www.w3.org/TR/EARL10-Schema/
- W3C RDF & SPARQL Working Group (manifest creator). *rdf-tests*, RDF 1.2 Turtle manifests (`rdf/rdf12/rdf-turtle/syntax/manifest.ttl`, `.../eval/manifest.ttl`). https://github.com/w3c/rdf-tests
- JSON Schema. *Specification* page ("The current version is 2020-12"). https://json-schema.org/specification
- JSON Schema. *JSON Schema Validation* (draft 2020-12). https://json-schema.org/draft/2020-12/json-schema-validation
- JSON Schema. *JSON Schema Validation* (draft-07, draft-handrews-json-schema-validation-01). https://json-schema.org/draft-07/json-schema-validation.html
- Data Package Working Group. *Table Schema* (Data Package v2, current). https://datapackage.org/standard/table-schema/
- Kulkarni, K. and Michels, J.-E. *Temporal features in SQL:2011*. ACM SIGMOD Record 41(3):34–43, 2012. https://doi.org/10.1145/2380776.2380786 (PDF read: https://sigmodrecord.org/publications/sigmodRecord/1209/pdfs/07.industry.kulkarni.pdf)
- PostgreSQL Global Development Group. *CREATE TABLE*, PostgreSQL 18 documentation. https://www.postgresql.org/docs/current/sql-createtable.html
- Neo4j. *Constraints*, Cypher Manual (current). https://neo4j.com/docs/cypher-manual/current/schema/constraints/

### Wikidata and Wikibase

- Wikimedia. *Wikibase JSON format* (Wikibase documentation, master). https://doc.wikimedia.org/Wikibase/master/php/docs_topics_json.html
- Wikidata. *Help:Property constraints portal* and subpages *Single value*, *Single best value*, *Qualifiers* (allowed qualifiers), *Required qualifiers*, *Property Scope Constraint* (wikitext via `action=raw`). https://www.wikidata.org/wiki/Help:Property_constraints_portal
- Wikidata. *Help:Ranking*. https://www.wikidata.org/wiki/Help:Ranking
- Wikidata. *Help:Deprecation*. https://www.wikidata.org/wiki/Help:Deprecation
- Wikidata. *Help:Sources*. https://www.wikidata.org/wiki/Help:Sources
- Wikidata. *Help:Merge*. https://www.wikidata.org/wiki/Help:Merge
- Wikidata. *Help:QuickStatements*. https://www.wikidata.org/wiki/Help:QuickStatements
- Wikidata entities read through `Special:EntityData` (labels, descriptions, constraint statements): Q21510851, Q21510856, Q19474404, Q52060874, Q21502410, Q21510865, Q21503250, Q21510862, Q21510855, Q21502838, Q21503247, Q21510859, Q52558054, Q52004125, Q21514353, Q25796498, Q54554025, Q53869507, Q54828448, Q54828449, Q54828450, Q21502408, Q62026391, reason items Q25895909, Q126598282, Q21655367, Q14946528, Q115099570, Q41755623, Q21441764, Q21124171, Q25235916, Q24629887, Q35779580; properties P2302, P2306, P4155, P5314, P2316, P2303, P2241, P7452, P1366, P1365, P1534, P580, P582, P585, P248, P854, P813, P143, P887, P3452, P4656, P459, P1480, P518, P10663, P6607, P6824, P9729, P155, P156, P1545, P1319, P1326, P8554, P8555, P12506, P1264, P805, P2868, P5102, P1810, P3680, P3831, P1932, P1310, P1552, and the 20 probe properties. https://www.wikidata.org/wiki/Special:EntityData/
- Pellissier Tanon, T., Vrandečić, D., Schaffert, S., Steiner, T. and Pintscher, L. *From Freebase to Wikidata: The Great Migration*. WWW 2016. https://doi.org/10.1145/2872427.2874809 (PDF read: https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44818.pdf)
- MediaWiki. *Manual:Revision table*. https://www.mediawiki.org/wiki/Manual:Revision_table

### Role inventories and schema languages

- Ruppenhofer, J., Ellsworth, M., Petruck, M. R. L., Johnson, C. R., Baker, C. F. and Scheffczyk, J. *FrameNet II: Extended Theory and Practice*. Revised 1 November 2016. Read from the Internet Archive copy: https://web.archive.org/web/20221026121837id_/https://framenet2.icsi.berkeley.edu/docs/r1.7/book.pdf
- NLTK Project. `nltk/corpus/reader/framenet.py` (branch `develop`). https://github.com/nltk/nltk/blob/develop/nltk/corpus/reader/framenet.py
- Palmer, M., Gildea, D. and Kingsbury, P. *The Proposition Bank: An Annotated Corpus of Semantic Roles*. Computational Linguistics 31(1):71–106, 2005. https://aclanthology.org/J05-1004/
- Kipper, K., Korhonen, A., Ryant, N. and Palmer, M. *A large-scale classification of English verbs*. Language Resources and Evaluation 42(1):21–40, 2008. https://doi.org/10.1007/s10579-007-9048-2
- CU CLEAR. *verbnet* repository, `verbnet3.4/vn_schema-3.xsd` and `verbnet3.4/give-13.1.xml`, commit `ae8e9cf` (2023-11-08). https://github.com/cu-clear/verbnet
- schema.org. *Role* (V30.1). https://schema.org/Role
- TypeDB. *TypeQL reference*: annotations `@card`, `@key`, `@unique`, `@distinct`; statements `relates`, `plays`, `owns`; *Data and query model* (TypeDB 3.x; server tag 3.13.6). https://typedb.com/docs/typeql-reference/annotations/ ; https://typedb.com/docs/typeql-reference/data-model/
- LinkML. *linkml-model* metamodel `linkml_model/model/schema/meta.yaml` (branch `main`); PyPI `linkml` 1.11.1 and `linkml-runtime` 1.11.1 (2026-05-20). https://github.com/linkml/linkml-model
- Ilievski, F., Garijo, D., Chalupsky, H., Divvala, N. T., Yao, Y., Rogers, C. et al. *KGTK: A Toolkit for Large Knowledge Graph Manipulation and Analysis*. arXiv:2006.00088, 2020. https://arxiv.org/abs/2006.00088 ; *KGTK file specification*: https://kgtk.readthedocs.io/en/latest/specification/
- ORKG. *Templates* (help page; site version 0.190.0). https://orkg.org/about/19/Templates

### Evidence, provenance, curation

- Peta-Pico. *Nanopub-X ontology* `nanopubx.ttl` (commit `9922656` of 2017-04-11 defines `npx:retracts` and `npx:supersedes`; last change 2025-07-11). http://purl.org/nanopub/x/ → https://github.com/peta-pico/ontologies
- Nadendla, S., Jackson, R., Munro, J., Quaglia, F., Mészáros, B. et al. *ECO: the Evidence and Conclusion Ontology, an update for 2022*. Nucleic Acids Research 50(D1):D1515–D1521, 2022. https://doi.org/10.1093/nar/gkab1025
- EMBL-EBI. *Ontology Lookup Service*, ECO release 2026-07-10 (loaded 2026-09-22). https://www.ebi.ac.uk/ols4/ontologies/eco
- Gyori, B. M., Bachman, J. A., Subramanian, K., Muhlich, J. L., Galescu, L. and Sorger, P. K. *From word models to executable models of signaling networks using automated assembly*. Molecular Systems Biology 13(11), 2017. https://doi.org/10.15252/msb.20177651
- Bachman, J. A., Gyori, B. M. and Sorger, P. K. *Automated assembly of molecular mechanisms at scale from text mining and curated databases*. Molecular Systems Biology 19(5), 2023. https://doi.org/10.15252/msb.202211325
- INDRA. `sorgerlab/indra` @ `7ae3337` (2026-06-30): `indra/statements/statements.py`, `indra/statements/evidence.py`, `indra/preassembler/__init__.py`, `indra/belief/__init__.py`, `indra/resources/default_belief_probs.json`, `doc/tutorials/html_curation.rst`. https://github.com/sorgerlab/indra
- INDRA DB. `indralab/indra_db`, `indra_db/schemas/principal_schema.py` (last changed 2025-02-07; HEAD `7dc8bf5`, 2026-07-09). https://github.com/indralab/indra_db
- Kilicoglu, H., Shin, D., Fiszman, M., Rosemblat, G. and Rindflesch, T. C. *SemMedDB: a PubMed-scale repository of biomedical semantic predications*. Bioinformatics 28(23):3158–3160, 2012. https://doi.org/10.1093/bioinformatics/bts591
- U.S. National Library of Medicine. *SemMedDB Database Details*. https://lhncbc.nlm.nih.gov/temp/SemRep_SemMedDB_SKR/dbinfo.html
- Himmelstein, D. S., Lizee, A., Hessler, C., Brueggeman, L., Chen, S. L., Hadley, D. et al. *Systematic integration of biomedical knowledge prioritizes drugs for repurposing*. eLife 6:e26726, 2017. https://doi.org/10.7554/eLife.26726 ; `hetio/hetionet` README and `describe/definitions.json`: https://github.com/hetio/hetionet

### Temporal and event-sourced stores, memory systems

- Fowler, M. *Event Sourcing*. martinfowler.com, 12 December 2005. https://martinfowler.com/eaaDev/EventSourcing.html
- Datomic documentation. *Datomic Data Model* and *Datomic Overview*. https://docs.datomic.com/whatis/data-model.html ; https://docs.datomic.com/datomic-overview.html
- Zep. *graphiti* repository, graphiti-core 0.30.2, commit `16cdf70` (2026-09-21): `graphiti_core/edges.py`, `graphiti_core/utils/maintenance/edge_operations.py`, `graphiti_core/prompts/dedupe_edges.py`, `graphiti_core/models/edges/edge_db_queries.py`. https://github.com/getzep/graphiti
- Rasmussen, P., Paliychuk, P., Beauvais, T., Ryan, J. and Chalef, D. *Zep: A Temporal Knowledge Graph Architecture for Agent Memory*. arXiv:2501.13956, 2025 (as cited by the KB). https://arxiv.org/abs/2501.13956

### Stores, libraries and test suites

- RDFLib. `rdflib/store.py` and `test/test_store/test_namespace_binding.py` at tag `7.6.0` (commit `8b32146`, 2026-02-13). https://github.com/RDFLib/rdflib
- HypergraphDB. `core/src/java/org/hypergraphdb/HyperGraph.java`, `HGLink.java` @ `99485a1` (2024-09-14). https://github.com/hypergraphdb/hypergraphdb
- XGI 0.10.2 and HyperNetX 2.4.3 wheels from PyPI (`xgi/core/hypergraph.py`, `xgi/core/views.py`; `hypernetx/classes/hypergraph.py`, `hypernetx/classes/hyp_view.py`). https://pypi.org/project/xgi/0.10.2/ ; https://pypi.org/project/hypernetx/2.4.3/
- TypeDB. `typedb-driver` 3.13.6 wheel (uploaded 2026-09-21), package `typedb`. https://pypi.org/project/typedb-driver/
- Kùzu. README of `kuzudb/kuzu`, commit `06890e1` (2025-10-10); PyPI `kuzu` 0.11.3. https://github.com/kuzudb/kuzu
- openCypher. *The Cypher Technology Compatibility Kit (TCK)*, `tck/README.adoc`. https://github.com/opencypher/openCypher/tree/main/tck
- Python packages' PyPI metadata (version, upload date, dependencies): `jsonschema` 4.26.0, `fastjsonschema` 2.22.2, `jsonschema-rs` 0.57.1, `linkml` 1.11.1, `linkml-runtime` 1.11.1, `pyshacl` 0.40.1, `PyShEx` 0.9.0, `frictionless` 5.19.0, `typedb-driver` 3.13.6, `rdflib` 7.6.0, `pyoxigraph` 0.5.11, `referencing` 0.37.0, `rpds-py` 2026.6.3, `graphiti-core` 0.30.2. https://pypi.org/
- Horejsek, M. *python-fastjsonschema* README. https://github.com/horejsek/python-fastjsonschema

### Knowledge-base notes relied on (this repository)

- `kb/02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md`
- `kb/02-knowledge-representation/wikidata-and-freebase-data-models.md`
- `kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md`
- `kb/02-knowledge-representation/n-ary-relations-and-reification.md`
- `kb/02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md`
- `kb/03-construction/curation-crowdsourcing-and-quality.md`
- `kb/03-construction/incremental-and-streaming-construction.md`
- `kb/04-storage-and-formats/versioning-provenance-and-scale.md`
- `kb/04-storage-and-formats/property-graph-emulation-patterns.md`
- `kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md`
- `kb/04-storage-and-formats/hypergraph-databases.md`
- `kb/05-query-embeddings-reasoning/query-languages-for-hypergraphs.md`
- `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md`
- `kb/09-ecosystem/software-libraries.md`
- `kb/10-comparative-and-critique/limitations-and-failure-modes.md`
- P2 research reports [01](01-requirements-from-kb.md), [02](02-hif-standard.md) and [03](03-library-probes.md)
