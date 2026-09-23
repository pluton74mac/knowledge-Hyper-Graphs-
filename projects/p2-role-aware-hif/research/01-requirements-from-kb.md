---
title: Requirements for contracts C1, C2, C3 and C5, from the knowledge base and the consuming projects
type: survey
status: draft
tags: [p2, requirements, contracts, record-format, store-interface, queue, linter, scorers, hif, roles, identity]
created: 2026-09-23
updated: 2026-09-23
---

# Requirements for C1, C2, C3 and C5 (P2 research report 01)

This report pulls out of the knowledge base (KB) and the programme plan everything that the shared contracts
of project P2 have to satisfy: C1 (record format), C2 (store interface), C3 (candidate queue and linter
action log) and C5 (scorers). It also covers the `roles` convention on HIF, the validator and the loaders,
because the P2 gate tests them. It feeds the design stage. It proposes no design, but section 9 lists the
decisions the design has to take, with a recommendation for each.

Scope of reading: every note named in the task was read in full on 2026-09-23. The consumers' starting
notes were skimmed where a contract depends on them (listed in the Sources). A few load-bearing facts about
HIF, XGI and HyperNetX were re-checked today against the primary artefacts (section 10).

## 0. How to read this report

**Evidence labels.**

- **KB**: stated in a KB note, which carries its own primary sources.
- **Verified 2026-09-23**: I checked it today against the primary artefact (schema file, library source).
- **Derived**: my inference from arguments the KB makes. It is not stated in the KB as such.
- **Recommendation**: my proposal for the design stage. It is not an established result.

**Requirement levels** (recommendations, in the RFC 2119 sense):

- **MUST**: a consumer's gate or the P2 gate cannot pass without it, or the KB documents a concrete failure
  when it is missing.
- **SHOULD**: the KB recommends it with evidence, but no gate depends on it.
- **MAY**: an option the format should not rule out.

**Source keys.** Pointers are written `KEY §section`. The key-to-path table:

| Key | Path |
|---|---|
| PLAN | `projects/PLAN.md` |
| PRJ | `projects/README.md` |
| P2R | `projects/p2-role-aware-hif/README.md` |
| OQ | `kb/00-index/open-questions.md` (question ids `[NN.k]`) |
| HIF | `kb/04-storage-and-formats/hif-hypergraph-interchange-format.md` |
| FMT | `kb/04-storage-and-formats/format-recommendations.md` (r*n* = rule *n* of §3) |
| VER | `kb/04-storage-and-formats/versioning-provenance-and-scale.md` |
| PGE | `kb/04-storage-and-formats/property-graph-emulation-patterns.md` |
| REL | `kb/04-storage-and-formats/relational-and-eav-storage.md` |
| RDF | `kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md` |
| TEN | `kb/04-storage-and-formats/tensor-and-sparse-representations.md` (skimmed) |
| SCH | `kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md` |
| NRY | `kb/02-knowledge-representation/n-ary-relations-and-reification.md` |
| HRV | `kb/02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md` |
| DIR | `kb/02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md` |
| ONT | `kb/02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md` |
| WDF | `kb/02-knowledge-representation/wikidata-and-freebase-data-models.md` |
| OWA | `kb/02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md` |
| META | `kb/02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md` (skimmed) |
| INC | `kb/03-construction/incremental-and-streaming-construction.md` |
| LLM | `kb/03-construction/llm-based-khg-construction.md` |
| SKL | `kb/03-construction/skill-driven-extraction-and-the-scenario-gap.md` |
| CUR | `kb/03-construction/curation-crowdsourcing-and-quality.md` |
| ER | `kb/03-construction/entity-resolution-and-canonicalisation.md` |
| EVC | `kb/03-construction/evaluation-of-constructed-khgs.md` |
| NXT | `kb/03-construction/n-ary-relation-extraction-from-text.md` (skimmed) |
| HIL | `kb/03-construction/human-in-the-loop-annotation-and-cost.md` (skimmed) |
| SIA | `kb/03-construction/schema-induction-and-ontology-alignment.md` (skimmed) |
| TMP | `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md` |
| AGT | `kb/07-applications/ai-agents-memory-and-planning.md` |
| HPR | `kb/07-applications/hierarchical-and-planned-hypergraph-retrieval.md` |
| BEP | `kb/05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md` |
| QL | `kb/05-query-embeddings-reasoning/query-languages-for-hypergraphs.md` |
| TDK | `kb/05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md` (skimmed) |
| XAI | `kb/05-query-embeddings-reasoning/explainability-and-uncertainty.md` (skimmed) |
| HYP | `kb/05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md` (skimmed) |
| LKI | `kb/05-query-embeddings-reasoning/llm-and-khg-interaction.md` (skimmed) |
| THY | `kb/01-foundations/hypergraph-theory-results.md` |
| RAL | `kb/01-foundations/n-ary-relations-and-relational-algebra.md` (skimmed) |
| DEF | `kb/01-foundations/hypergraph-definitions.md` (skimmed) |
| LIB | `kb/09-ecosystem/software-libraries.md` |
| STD | `kb/09-ecosystem/standards-bodies-and-specifications.md` (§4 read) |
| DQL | `kb/09-ecosystem/dataset-quality-and-leakage-issues.md` (skimmed) |
| LIM | `kb/10-comparative-and-critique/limitations-and-failure-modes.md` |
| GOV | `kb/10-comparative-and-critique/privacy-licensing-and-governance.md` (skimmed) |
| CRH | `kb/10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md` (skimmed) |
| VIS | `kb/06-visualization/knowledge-hypergraph-specific-visualization.md` (skimmed) |
| CST | `kb/08-history-and-frontier/composed-stack-and-research-bets.md` (§3 read) |
| SAMPLE | `schemas/sample.hif.json` |
| TTL | `schemas/sample-n-ary-fact.ttl` |
| V-HIF | Verified 2026-09-23: the four HIF schema URLs and the schema changelog (section 10) |
| V-XGI | Verified 2026-09-23: XGI 0.10.2 wheel, `xgi/convert/hif_dict.py`, read, not executed (section 10) |
| V-HNX | Verified 2026-09-23: HyperNetX 2.4.3 wheel, `hypernetx/hif.py`, `classes/hypergraph.py`, `classes/factory.py`, read, not executed (section 10) |

---

## 1. The consumers and what each one takes from P2

The contracts and their versioning come from PLAN §7. The gates come from PLAN §4.

| Project | What its gate needs | From C1 | From C2 | From C3 | From C5 |
|---|---|---|---|---|---|
| **P2** | A record round-trips repo → HIF → XGI and HyperNetX → back with roles intact. The validator rejects each listed malformed case. A smoke test runs queue → structural lint → store → export. | All of C1, the HIF `roles` convention, the loaders | Reference store and conformance test | Queue and linter log | None |
| **P3a** | Corpus with leak-check report, dedup report, arity histogram, fixed split and question sets. It consumes C1 to produce C4 (PLAN §3), so gold facts, roles and question sets are written in C1 terms. | Faithful Wikidata statements: core and qualifier slots, typed literals with precision and unit, `somevalue`/`novalue`, rank, references. A content key of the core for leak checks and dedup. One arity definition. | Optional (export) | None | The question-set record that it fills |
| **P3b** | Two models replicated within tolerance; calibration by arity | Deterministic positional, hyper-relational and role-value projections; dropping literals as a projection | None | None | Completion scorer: protocol presets, filtered MRR/Hits, per arity, calibration |
| **P1** | Five stores compared on round-trip fidelity, load time and query latency | Canonical form, to measure fidelity. RDF relation-instance and reifier mappings. Incidence-table and property-graph projections. A schema that maps to TypeDB. | C2 works over an incidence table, reified RDF 1.2, a bipartite property graph, TypeDB and HIF. Conformance test. Timing hooks. | None | None |
| **P6** | The checker reports acyclicity class and width for a schema file and flags a constructed cyclic case | A schema language with global role ids that parses into an attribute hypergraph, marks required and optional roles, and can express Wikidata constraints | None | None | None |
| **P7** | Every identity case classified as specified; memory comparison on the superseding-fact question set | Key role sets, core/qualifier slots, valid and transaction time, supersession links, statuses, a text rendering for the flat-store baseline | put/get, lookup by relation and key, supersession walk, as-of/as-at | Merges as logged actions | Memory scorer |
| **P9** | P/R and role accuracy against P3a gold; instability over 3 runs × 2 insertion orders; output validates against C3 | Role constraints (typed skills), canonical content key, evidence spans | None (the queue feeds the store) | Candidate record with run and order metadata, linter log, verdicts | Extraction scorer with role accuracy and stability |
| **P10** | The walker answers the P3a questions; a general LLM and a decision-only model compared on cost, latency and accuracy | Text rendering and labels | Complete, deterministic `incident(node)`; members with roles; degree counts; status and time filters | None | Retrieval scorer with cost and latency |
| **P5** | Study run and reported | Labels for entities, relations and roles; direction; small slices; loaders that make roles visible to XGI and HyperNetX drawing | None | None | None |
| **P4** | Three retrieval conditions on one question set; the GraphRAG-Bench run | Pairwise projection with back-pointers; the source sentence of each hyperedge | Via P10's traverser | None | Retrieval scorer per condition; recall of the required edge; external-benchmark adapter |
| **P8** | One corpus, four scores and their correlation | Completed facts marked as model-inferred, with model provenance | All of the above | None | All four scorers, with per-item output |
| **P11** | The two-discipline case reaches termination; the four-discipline case terminates or produces a stall report naming the unbound roles | Goal edge kind; an UNBOUND value; binding events with evidence and agent; validation that depends on status | Query unbound slots; bind with history; evaluate termination over the store | Binding proposals through the queue | None (the termination criterion belongs to P11) |

---

## 2. C1: record format

### 2.1 Identity and record kinds

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R01 | Every hyperedge has a stable opaque id. The id is not the fact's text, not a hash of the text, and not its member set. | MUST | all; P7, P9, P1 | FMT §3 r1; PGE §4 r3; LIM §11; VER §1 "Signed and content-addressed identifiers" |
| C1-R02 | Every hyperedge also has a deterministic *content key*, computed from the relation and a canonical form of its core role bindings and kept separate from the id. The content key serves dedup, leak checks and run-to-run comparison. | MUST | P3a (dedup, leak check on the main triple), P9 (instability), P7, P1 | LIM §11 mitigation ("a stable surrogate identifier plus a content hash of its core roles"); DQL §10 item 8; EVC §6 |
| C1-R03 | Content hashes identify *extraction events*. Re-extracting the same sentence gives the same event hash and never forks the fact. | SHOULD | P9, P3a | VER §1 ("opaque and stable for the fact, content-addressed for the extraction event"); FMT §3 r1 |
| C1-R04 | Entity ids are opaque, namespaced (a Wikidata item id, or a local prefix) and distinct from labels. All ids are strings. | MUST | P3a, P1 (IRIs), P5, P2 gate | SCH §2; HIF §9 item 3. String-only ids avoid type drift in HIF readers (LIB §1: Hypergraphx re-indexes node ids to integers; V-XGI: XGI casts ids through `nodetype`/`edgetype`). The string-only rule is a Recommendation. |
| C1-R05 | Every hyperedge declares an *edge kind*: n-ary fact over entities; meta fact over hyperedges (context, claim, supersession); rule/inference hyperarc (tail → head); goal. | MUST | P7, P10, P11, P1 | DIR §5 modelling rule ("A store that does not type its edges will eventually mix all three"); HRV §5 (the B-arc row says not to mix rule and fact hyperedges "without a type marker"); RAL §5; PLAN §3 P11 row |

### 2.2 Values: entities, literals, special values

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R06 | A binding's value is a tagged union: entity reference, typed literal, hyperedge reference, or one of the special values below. | MUST | P3a, P1, P7, P11 | SCH §6.2 (`{"entity"}`, `{"literal", "datatype", "precision"}`, `{"hyperedge"}`) |
| C1-R07 | A literal carries a datatype from a declared list, plus precision (for example `year`) and unit where they apply. Equality of literals takes precision into account. | MUST | P3a, P1, P9, C5 | SCH §2 ("a general KHG schema must carry typed literals with units and precision"), §6.1 `datatypes`, §8 pitfall 5 |
| C1-R08 | "No value" (asserted absence, Wikidata `novalue`) and "some value" (asserted existence with an unknown filler, `somevalue`) are values in their own right, distinct from "not recorded". | MUST | P3a, P7 | OWA §3, §8 item 3 ("a KHG schema that lacks it cannot represent 'this reaction has no catalyst'"); WDF §2 |
| C1-R09 | An **UNBOUND** slot is a value kind: an open role waiting to be bound, optionally constrained by an expected type. It is distinct from `somevalue` and legal only on goal hyperedges. | MUST | P11 | PLAN §3 P11 row, §4 P11 gate ("a stall report naming the unbound roles"); PRJ P11 row |
| C1-R10 | A redacted (tombstoned) binding keeps arity and signature conformance but withholds the filler. | MAY | governance, P7 | GOV §4(b); OQ [10.6] |
| C1-R11 | Dropping literals is a projection option, never a storage choice. | SHOULD | P3b, P3a | BEP §5 pitfall 4; SCH §8 pitfall 5 (in WikiPeople "about 13% of statements contain at least one literal") |

### 2.3 Bindings, roles, slot classes and direction

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R12 | A hyperedge has exactly one relation type and a list of bindings `(role, value)`. Every membership in a fact has a role. | MUST | all; P2 gate | FMT §3 r2 ("A hyperedge without roles is a co-occurrence set"); LIM §3 mitigation; SCH §1 |
| C1-R13 | One entity can fill two different roles in the same hyperedge. Both bindings survive every projection that claims to be lossless. | MUST | P3a, P1, P2 gate | LIM §3 (`flies_between(AirCanada, Toronto, Toronto)`); REL §1b (`PRIMARY KEY (fact_id, entity_id, role)`) |
| C1-R14 | A role can be bound several times when its relation type allows it (`max` > 1 or unbounded). The multiplicity survives. | MUST | P3a, P1, P2 gate | SCH §3 (`max`), §6.1 (`together_with`, `"max": null`); SAMPLE edge `f2` (two `agent` incidences) |
| C1-R15 | The fillers of one repeated role are unordered, and identity does not change when they are permuted. The exception is a role declared `ordered`: each of its bindings carries a position. | MUST | P7, P3b, P1 | LIM §3 (symmetric `co_authors(A, B, C)`); SCH §3 (`ordered`); NRY §2 (Pattern 2, ordered lists); REL §1b (`position` column) |
| C1-R16 | Arity has one written definition, stating which bindings count (core only, or core and qualifiers; repeated fillers; special values). It is stored, or derived the same way, everywhere. | MUST | P3a (histogram), P3b, P8, P9 (arity-stratified scores), P1 | FMT §3 r3; PGE §4 r4; EVC §7 item 3; BEP §1 (arity reweights MRR); LIM §1 (three different WikiPeople figures measure three different things) |
| C1-R17 | Each binding is classed *core* or *qualifier*, as the relation type declares. | MUST | P3a, P3b, P1, P7 | SCH §4; HRV §1(3), §5; WDF §2 (one main snak plus qualifier snaks) |
| C1-R18 | A relation type may name an optional `primary` pair (subject role, object role) that defines a triple view. The pair is derived and never required. | SHOULD | P3a (leak check on the main triple), P1 (RDF 1.2 annotation form), P3b (StarE-style input) | SCH §6.1 notes, §8 pitfall 1 ("Keep `primary` optional and derived"); RDF §2b; DQL §10 item 8 |
| C1-R19 | Direction (`tail`/`head`) belongs to a binding and is separate from its role. When a role declares a direction, its bindings inherit it. | MUST | P5 (arrowheads), P2 gate (XGI `DiHypergraph`), P1 | FMT §3 r4 ("Store direction per incidence ... A fact can have several heads"); HIF §2; DIR §1 (three senses of "directed"); SAMPLE (every role maps to one direction) |
| C1-R20 | On a rule hyperarc (tail → head), no node is both tail and head. | SHOULD | P10, P11 | DIR §2 (Gallo et al.: `Tail(a)` and `Head(a)` are disjoint); TEN §1 (the ±1 encoding "cannot express a node that is both head and tail of the same edge") |
| C1-R21 | Entities, relation types and roles have human-readable labels, separate from their ids. | MUST | P5 (role-labelled drawings), P10 (prompts), P7 (flat-store baseline) | VIS §8 (link label = role, fact-node label = relation type); LKI §5 ("the role vocabulary — is what you must surface in the prompt") |
| C1-R22 | A hyperedge can keep the sentence or description it was extracted from, as text that carries provenance. | SHOULD | P4 (whole-sentence chunk condition), P9, P7 | OQ Theme 1 [10.2]; CRH §2.3, §7 item 3; SIA §7 item 1 |

### 2.4 Nesting (facts about facts)

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R23 | A binding can reference another hyperedge. The reference must resolve, and the graph of such references must be acyclic. | MUST | P7 (supersession, disputes), P11, P1 (RDF 1.2 triple terms, TypeDB nested relations) | SCH §6.2 (the `disputed_by` example); META §1 ("The uber-Levi graph is a directed acyclic graph"; cycles "violate the axiom of foundation"), §8 ("Most practical schemas should require acyclicity"); NRY §8 |
| C1-R24 | Each relation type declares whether it is `nestable`, that is, whether a hyperedge id may appear where an entity id is expected. | SHOULD | P1, P7 | SCH §6.1 (`nestable`) |

### 2.5 Relation-type schema language

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R25 | A schema document declares entity types, datatypes, a role vocabulary and relation types. For each role a relation uses, it gives: filler type or datatype, `required`, `max`, `ordered`, slot class (core or qualifier), and optionally a direction. | MUST | P6, P9, P1, P3a | SCH §3 table, §6.1; ONT §9 recommendation 2 ("Declare optional roles, not subclasses") |
| C1-R26 | Roles have *global* identities: one vocabulary, with a usage declaration per relation. Two relation types that use the same role therefore share an attribute. | MUST | P6, P3a, P3b, P5 | SCH §3 "Global vs local role names" (RAM: "over 80% roles in beyond-ternary relations also appear in lower-arity relations", [Liu, Yao and Li, 2021](https://arxiv.org/abs/2104.09780)); ER §3; RAL §2 |
| C1-R27 | The schema parses deterministically into a *schema hypergraph* (vertices = attributes, hyperedges = relation schemas), with the rule for "attribute" written down. It can express a deliberately cyclic schema. | MUST | P6 gate | PLAN §4 P6 gate; RAL §2 (schema hypergraph vs query hypergraph vs instance hypergraph); THY §5–§6 ([Fagin, 1983](https://dl.acm.org/doi/10.1145/2402.322390)) |
| C1-R28 | A relation type can declare a *key role set* `K ⊆ roles(r)`: at most one hyperedge with a given binding of K is valid at any instant. | MUST | P7, P11 | TMP §1(b) ("No n-ary model or schema language surveyed in this KB declares one"), §7 item 2; TDK §5; OQ [05.8] |
| C1-R29 | Variable arity is expressed with optional roles, not by minting one relation per combination of roles. | MUST | P3a, P9, P7 | SCH §3 "Variable arity"; HRV §1(3) (StarE: "combinatorial explosion of typed hyperedges", [Galkin et al., 2020](https://arxiv.org/abs/2009.10847)); LIM §4 (WD50K arity 2–67) |
| C1-R30 | The schema records the confidence scale and the time model: whether validity is carried as a qualifier, as a record field, or both. | SHOULD | P7, P3a, P9 | SCH §6.1 (`confidence_scale`, `time_model`) |
| C1-R31 | Roles and relation types can carry aliases (raw extracted phrases) and external mappings (Wikidata property ids, FrameNet frame elements). | SHOULD | P9, P3a, P6 | SIA §7 item 3; ONT §9 recommendation 1; ER §3 |
| C1-R32 | Schema documents carry an id with a semantic version. Each hyperedge records the schema id and version it was typed under. | MUST | all (PLAN §7), P9 (schema drift) | PLAN §7 C1 row ("Semantic version in the schema id; migration script per major version"); INC §8 item 6; SIA §8 |
| C1-R33 | The schema maps onto write-time constraint languages (TypeQL `relates`/`plays`, SQL constraints, SHACL 1.2 reifier shapes). It can also be built from Wikidata property constraints (required qualifiers, allowed qualifiers, single value, value type). | SHOULD | P1 (TypeDB), P6 (Wikidata schema files) | SCH §7; ONT §5, §7; CUR §2 ([Help:Property constraints portal](https://www.wikidata.org/wiki/Help:Property_constraints_portal)) |
| C1-R34 | A relation can declare "must differ" or "must agree" constraints between roles (for example, origin ≠ destination unless declared otherwise). | MAY | P9 (lint), P3a | THY §7 (mixed hypergraphs carry "must differ" and "must agree" constraints); LIM §3 |

### 2.6 Evidence and provenance

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R35 | Every asserted hyperedge has at least one evidence record. Provenance is *about* the fact and is never a role binding, so two sources of one fact make one fact with two evidence records. | MUST | P9, P3a, P7, P8 | SCH §5 "Design rule", §8 pitfall 2 ("Treating provenance as a role ... makes two records of the same fact into two facts"); INC §8 item 2; CUR §5 metric 1 |
| C1-R36 | Evidence can attach to a single binding as well as to the whole hyperedge. | SHOULD | P9, P11, governance | GOV §6 ("the obligation attaches to the **incidence**"), §8 item 7 ("Make provenance per-incidence"); INC §8 item 2 |
| C1-R37 | Provenance uses PROV-O terms and accepts Wikidata-style reference records (sets of role-value pairs). | SHOULD | P1 (RDF export), P3a | FMT §3 r5; VER §1 ([PROV-O](https://www.w3.org/TR/prov-o/)); SCH §5 |
| C1-R38 | Evidence records an *evidence type* (curated, imported, model-extracted, model-inferred by completion, agent-bound) and the activity that produced it: tool, model and version, run id, prompt or skill version. Machine-completed facts can then be told apart and audited. | MUST | P8 (completer output), P9, P11, P3a | CUR §1 (Gene Ontology evidence codes), §6 ("Bot-authored and LLM-authored facts are not distinguished"); HPR §6 item 4; OQ [10.8] |
| C1-R39 | Text evidence carries a document id, a document version or hash, and character offsets. | SHOULD | P9 (strict matching uses entity bounds), P4 | EVC §1 (the HyperRED rule matches "entity bounds", [Chia et al., 2022](https://arxiv.org/abs/2211.10018)); NXT §5 |
| C1-R40 | Curation verdicts and adjudication traces can be stored as provenance on the hyperedge. | SHOULD | P9, P3a | HIL §8 item 3 |

### 2.7 Status lifecycle, rank and supersession

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R41 | A status lifecycle with at least *candidate, asserted, superseded, retracted, goal*, and a written transition table. History is kept: a fact is invalidated, never deleted. | MUST | P9, P7, P11, P10, P2 smoke test | PLAN §7 C1 row ("status lifecycle"); INC §8 item 4 ("Invalidate, never delete"); TMP §7 item 3 |
| C1-R42 | Supersession is an explicit link from the superseding hyperedge to the superseded one, carrying the evidence that decided it. Closing a validity interval is not enough on its own. | MUST | P7, P8, P11; the C2 supersession walk | TMP §1(d), §7 item 3; INC §8 item 4 ("keep the invalidating hyperedge's id as the reason") |
| C1-R43 | Editorial rank (preferred, normal, deprecated) is a field separate from status and from confidence. Deprecated does not mean false. | SHOULD | P3a, P10 | WDF §2; OWA §3 ("Deprecated ≠ false"); SCH §6.2 (`rank`) |
| C1-R44 | A claim can be recorded without being asserted (a disputed or attributed claim). | SHOULD | P7, P9, P1 | RDF §2c; TTL "Way 2"; NRY §5 (non-asserted triple terms, [RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)) |
| C1-R45 | A *suppression* visibility tier, distinct from deletion. | SHOULD | governance | GOV §5, §8 item 7 |

### 2.8 Time

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R46 | Valid time sits on the hyperedge as a half-open interval `[t_valid, t_invalid)` with `+∞` representable, plus an explicit conjunction (Since, Until, Period, Invariant). Transaction time `[t_created, t_expired)` is kept separately. | MUST | P7 gate, P8, P11 | TMP §1(a), §7 item 1 ("Adopt VITA's `(c, t₁, t₂)` triplet as the surface syntax", [Un et al., 2025](https://arxiv.org/abs/2505.11803)); INC §5 (Graphiti's four timestamps, [Rasmussen et al., 2025](https://arxiv.org/abs/2501.13956)); FMT §3 r6; VER §2a |
| C1-R47 | Time as a qualifier (point in time, start time, end time) stays representable as bindings. The schema's time model states how qualifier times relate to the valid-time field, and the mapping is deterministic. | MUST | P3a, P7 | VER §2a ("Both are defensible. Columns are faster to query; qualifiers are more honest about the model"); SCH §5 ("Conflating them makes temporal queries wrong"); TDK introduction (time as role, as validity, as structure evolution) |
| C1-R48 | Per-binding validity intervals. | MAY | P7 (to test [07.10]), P11 | TMP §1(c) ("Nothing found attaches intervals below hyperedge granularity"); OQ [07.10] |

### 2.9 Confidence, weight and the open world

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R49 | Confidence is stored together with its scale: a probability, an LLM score with its stated range, or none. A bare number is malformed. The HIF `weight` field is never the authoritative carrier of confidence. | MUST | P9, P8, P10, P3b | SCH §5 "Confidence" (three incompatible conventions); OWA §8 item 1; LIM §8; V-XGI (XGI's reader ignores every `weight` field) |
| C1-R50 | Absence of a fact means unknown. Completeness assumptions (which role sets are believed complete for which subjects) are stored as assumptions, never as inferred negative facts. | SHOULD | P3b, P7 | OWA §1, §8 item 2; OQ [02.1] |
| C1-R51 | The format states that a weight on a meta-level record (a qualifier *about* a fact) has no defined semantics, and it implies none. | SHOULD | P8 | OQ [02.5]; OWA §5 caveat ("Reading a hyperedge weight as a confidence is a category error unless the model says otherwise"), §9 |

### 2.10 Canonical form, versioning, migration

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R52 | A canonical serialisation (sorted bindings, normalised literals, string ids) under which semantically equal records compare equal. Round-trip fidelity is tested against it. | MUST | P2 gate, P1, P9 | PLAN §4 (P1 and P2 gates); EVC §6 |
| C1-R53 | A migration script for each major version. The repository's own sample, which uses `incidence.attrs.role` (singular), is the first input to migrate. | MUST | all | PLAN §7; SAMPLE |
| C1-R54 | Changes are append-only events (assert, invalidate, retract) with a defined delta unit, so "what did run N believe?" is a query. | SHOULD | P9, P7 | VER §2b; OQ [03.4]; LIM §11 mitigation |
| C1-R55 | Split membership (train/valid/test) lives in a manifest that maps ids to splits, not inside fact records. | MAY | P3a, P3b | Recommendation. Motivated by PLAN §7 (C4 versioning) and DQL §10 |

### 2.11 Projections and exports

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R56 | Lossless export to role-aware HIF and import back. | MUST | P2 gate, P1, P5 | PLAN §4 P2 gate |
| C1-R57 | A deterministic, lossless projection to the RDF relation-instance pattern. Where a `primary` pair is declared, also a projection to the RDF 1.2 reifier or annotation form, documented as lossy. | MUST | P1 | RDF §2 table (only the relation-instance pattern "round-trips to HIF" directly; the annotation and triple-term forms are "lossy"), §7; FMT §1, §4; [Noy and Rector, 2006](https://www.w3.org/TR/swbp-n-aryRelations/) |
| C1-R58 | Deterministic projections to positional tuples (one fixed canonical role order per relation), to hyper-relational statements (main triple plus qualifier pairs) and to role-value sets. | MUST | P3b, P8 (HYPER input) | SCH §6.3; HYP §9 (permuting argument positions makes HYPER drop "dramatically" because "each argument position carries a distinct semantic role"); BEP §3.2 (WD50K converted "by hashing the main relation and predicates in canonical order") |
| C1-R59 | A deterministic pairwise projection (clique or star) that keeps a pointer back to the source hyperedge. | MUST | P4 | PLAN §3 P4 row; OQ [10.2]; HRV §2 (star-to-clique is irreversible); PGE §1c |
| C1-R60 | Projections to the incidence-table / Parquet layout and to a bipartite property graph, with roles as relationship types or as a property. | SHOULD | P1 | REL §1b, §5; PGE §1a–b, §4 |
| C1-R61 | A canonical text rendering of a hyperedge: relation label plus `role: label` pairs. | SHOULD | P10, P7, P4 | LKI §4 ("Serialisation is the bottleneck"); PLAN §3 P7 row (comparison against a flat vector store) |

### 2.12 The HIF `roles` convention and the loaders

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R62 | Roles live in `incidences[].attrs` under one declared key. The file declares the convention's name and version inside `metadata`, because HIF forbids new record keys and new top-level keys. | MUST | P2 gate, HIF proposal | HIF §3 (`additionalProperties: false` everywhere), §9 item 1; SAMPLE (`metadata.conventions`); V-HIF (schema text) |
| C1-R63 | There is exactly one incidence record per (edge, node) pair, carrying the *list* of roles that node plays. Duplicate pairs are malformed. | MUST | P2 gate | V-HNX (factory docstring: "By default duplicate incidences will be dropped"; the incidence store is indexed on (edge, node)); V-XGI (edges are node sets); LIM §3 |
| C1-R64 | Relation type, edge kind, evidence, time and confidence live in `edges[].attrs`; entity type and label live in `nodes[].attrs`. All of them use declared keys. | MUST | P2 gate, P5, P1 | HIF §5; SAMPLE |
| C1-R65 | The file names the exact HIF schema document it was validated against: a vendored copy plus its hash. | MUST | P2 gate, HIF proposal | STD §4 ("any pipeline should vendor the schema it validates against"); HIF §4; V-HIF |
| C1-R66 | In a file with `network-type: directed`, every incidence has a `direction`. | MUST | P2 gate (XGI) | V-XGI: `from_hif_dict` reads `record["direction"]` unconditionally for directed files. A missing key should therefore raise `KeyError` (inferred from the source, not executed). |
| C1-R67 | A hyperedge that is referenced as a participant also appears as a node record, whose attrs mark it as a reference to that edge id. | SHOULD | P1, P7 | HIF §9 item 2 (no nesting; "no reader will interpret that as structure"); VIS §7 (KGTK uses edge ids as nodes) |
| C1-R68 | Literal fillers appear in HIF as node records marked `literal`, with deterministic ids (decision D-09). | SHOULD | P2 gate, P1 | HIF §2 (an incidence must name a node) |
| C1-R69 | No NaN or Infinity anywhere. Missing values are omitted, never filled with `null` or `"nil"`. | MUST | P2 gate | HIF §7 (XGI's `convert_nans`); V-HNX (`normalize_dataframe` calls `fillna("nil")`) |
| C1-R70 | The role-preserving loaders put roles where each library can hold them, and restore them on export. For HyperNetX, that is incidence ("cell") properties. XGI stores attributes only for nodes, edges and the whole network, so its loader keeps an edge-level map from node to roles. | MUST | P2 gate, P5 | DEF §8 (XGI's three attribute levels); LIB §1; V-XGI (the reader ignores incidence `attrs`); V-HNX (incidence `attrs` are passed as `misc_cell_properties_col`) |

### 2.13 The validator

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C1-R71 | JSON Schemas for records, schema documents, role-aware HIF, queue records and log entries. A semantic validator for cross-record checks (references resolve, types, cardinalities, keys, acyclicity). Every failure has a stable error code, and there is a test list of malformed cases (section 8). | MUST | P2 gate, P9 (C3 validation) | PLAN §4 (P2 and P9 gates); SKL §7 (Hyper-Extract's validator codes HE-T001…HE-T009 are the precedent) |
| C1-R72 | Validation depends on status. Goal hyperedges may leave required roles unbound; candidates may be incomplete; asserted facts may be neither. | MUST | P11, P9 | PLAN §3–§4; QL §3 (TypeDB: "Relations without role players will be removed"); HIF §2 (HIF allows empty edges); SKL §3 (Hyper-KGGen requires ≥ 2 distinct participants) |
| C1-R73 | The validator runs offline and deterministically, against vendored schemas. | MUST | P2 gate, CI | STD §4; V-HNX (HyperNetX fetches its schema over the network on every read and write) |

---

## 3. C2: store interface

PLAN §7 fixes the operations: put, get, incident hyperedges of a node, hyperedges by relation and key,
supersession walk, export. The interface is versioned, and every implementation passes one conformance
test.

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C2-R01 | `put(record)` validates and writes a C1 record. Putting an identical record again is a no-op. | MUST | P9, P7, P11, P2 smoke test | PLAN §7; INC §8 item 1 ("make insert idempotent") |
| C2-R02 | `get(id, as_of?, as_at?)` returns the whole record: bindings with roles, evidence, status, time. | MUST | all | PLAN §7 |
| C2-R03 | `incident(node, role?, relation?, filters)` returns every hyperedge in which the node fills some role (or only the given role), completely and in a deterministic order. | MUST | P10 (code-owned traverser), P1, P4 | PLAN §3 P10 row, §7; PGE §2 (the query "all facts in which metformin plays the treatment role"); THY §2 (every entity query has a dual fact query); QL §3 (TypeQL `links` as an incidence query) |
| C2-R04 | `by_relation_and_key(relation, bindings)` returns the hyperedges of that relation whose bindings *include* the given ones. "At least these" is the default; exact matching is available on request. Called with a declared key, it finds the fact currently valid for that key. | MUST | P7, P1 | PLAN §7; QL §3 (TypeQL partial tuples: "a relation with at least the role players described"); TMP §1(b) |
| C2-R05 | `supersession_walk(id, direction)` returns the chain of superseding (or superseded) hyperedges with the evidence that links them, and always terminates. | MUST | P7, P8, P11 | PLAN §7; TMP §7 item 3 |
| C2-R06 | `export(format)` produces role-aware HIF and canonical C1 JSON. The other projections are SHOULD. | MUST | P2 gate, P1, P5 | PLAN §4, §7 |
| C2-R07 | Queries take an as-of valid time and an as-at transaction time. The two compose, and their defaults are documented. | MUST | P7, P8, P10 | TMP §7 item 4 |
| C2-R08 | Normal updates never delete data physically: supersession and retraction invalidate and keep history. Physical erasure, if offered at all, is a separate, logged operation. | MUST | P7, P9, governance | INC §5 (Graphiti: facts "are invalidated, never deleted"), §8 item 4; GOV §4(b) |
| C2-R09 | The interface can be implemented over a PostgreSQL incidence table, an RDF 1.2 store, a bipartite property graph, TypeDB, and an in-memory index over HIF. An implementation that cannot honour an operation declares that through a capability flag. | MUST | P1 | PLAN §3 P1 row; REL §1b; RDF §2, §6; PGE §1; ONT §5; QL §3 |
| C2-R10 | One conformance suite, passed by every implementation, checks operation semantics, determinism, temporal behaviour, and round-trip fidelity by canonical-form equality (C1-R52). | MUST | P1, P2 | PLAN §7 |
| C2-R11 | Each implementation reports the interface version and the C1 version it implements. | MUST | all | PLAN §7 ("Each project records the contract versions it consumed") |
| C2-R12 | Degree counts per node (optionally per role or relation) are cheap. A hyperedge's member set comes back without a second query. | SHOULD | P10, P4 | HPR §3 (HyperGraphPro's distinctiveness term uses `\|{e ∈ E : v ∈ V_e}\|`), §2 (PRoH's EWO score uses `V(e) ∩ V(e')`) |
| C2-R13 | The default status filter is *asserted*. Candidates stay in the queue (C3). Goals can be queried, including "list the unbound slots". | SHOULD | P9, P11, P10 | PRJ P9 row ("emitting a candidate queue instead of writing to the graph"); PLAN §3 P9 and P11 rows |
| C2-R14 | Binding an UNBOUND slot creates a new version carrying evidence, and keeps the old version. | SHOULD | P11 | PLAN §3 P11 row |
| C2-R15 | A bulk-load path, and hooks that time loading and each query the same way on every backend. | SHOULD | P1 | PLAN §4 P1 gate ("load time and query latency") |
| C2-R16 | Results come in a deterministic total order, with stable pagination. | MUST | P10 (reproducible closed choices), P9 (instability runs), conformance test | Recommendation. Motivated by EVC §6 (stability as a metric) and PLAN §3 P10 row |
| C2-R17 | No store materialises a clique expansion. Derived indexes (vectors, projections) can be dropped and rebuilt from the system of record. | SHOULD | P1, P4 | FMT §2, §3 r7 |
| C2-R18 | The store checks keys. Two currently valid hyperedges with the same key binding and overlapping valid time are reported as a conflict, never silently overwritten. | SHOULD | P7 | TMP §1(b); INC §5 |
| C2-R19 | A superseding put, its supersession link and the invalidation of the old fact happen in one atomic write. | SHOULD | P7, P11 | FMT §2 ("Keep one system of record"); VER §3d item 4 |
| C2-R20 | An entity-merge operation rewrites bindings, keeps binding-level provenance, and is logged. | MAY | P9, P7 | LIM §9 ("a naive merge destroys the record of which extraction produced which binding"); ER §5 item 5 |

**What each backend makes hard.** This is Derived from the KB. P1 measures it; it should not be
designed away.

- **Incidence table.** `incident` is one index probe on `(entity_id, role)`. Literal bindings need either a
  value column or entity rows for literals (REL §1b).
- **RDF 1.2.** `incident` over the relation-instance pattern has to tell role predicates apart from
  metadata predicates (confidence, provenance). The export therefore has to mark role properties, for
  example with a common super-property (Recommendation). The annotation form needs a `primary` pair, and
  rdflib 7.6.0 cannot parse RDF-star or RDF 1.2 triple-term and annotation syntax (LIB §3). The Python
  route is pyoxigraph.
- **Bipartite property graph.** Putting roles on relationship *types* indexes well but needs a small,
  stable role vocabulary. Putting them in a property handles open vocabularies but costs a scan (PGE §4
  r2). A k-hop fact query becomes a 2k-hop graph query (PGE §2).
- **TypeDB.** Roles map to `relates`/`plays`, and nesting maps to relations playing roles (ONT §5). Whether
  literal-valued bindings can be role players, or must become owned attributes, is **[unverified]**. It
  affects both fidelity and the `incident` semantics for literals.
- **HIF.** A single JSON document with no streaming (HIF §9 item 5). Indexes are built in memory.

---

## 4. C3: candidate queue record and linter action log

PLAN §7 versions C3 "with C1". P9 must emit "a candidate queue instead of writing to the graph" (PRJ,
P9 row), and its output must validate against C3 (PLAN §4). The P2 smoke test runs queue → structural
lint → store → export.

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C3-R01 | A candidate record wraps a proposed hyperedge in C1 shape, with status `candidate`. Nothing reaches the store before it is accepted. | MUST | P9, P2 smoke test | PLAN §3 P9 row, §4 P9 gate; HIL §8 item 6 ("the machine proposes, the human judges") |
| C3-R02 | A candidate carries its extraction metadata: extractor and model ids with versions, prompt or skill version, decoding parameters (temperature, seed), run id, document id and version hash, insertion position and permutation id, timestamp. | MUST | P9 (3 runs × 2 orders) | PLAN §4 P9 gate; OQ [03.8]; SKL §4 (K rollouts at temperature T), §8 |
| C3-R03 | A candidate carries its evidence (source text, offsets) and the model's confidence with its scale. | MUST | P9 | EVC §1; SCH §5 |
| C3-R04 | A candidate carries the C1 content key (C1-R02), so candidate sets from different runs and orders can be compared by set agreement. | MUST | P9 | EVC §6 ("report the Jaccard overlap of the resulting hyperedge sets"); OQ [03.8] |
| C3-R05 | The queue lifecycle is pending → linted → accepted, rejected, merged or needs-review. Every transition records its actor and reason. An accepted candidate links to the store id it became. | MUST | P9, P2 smoke test | PLAN §4 P2 gate; HIL §8 |
| C3-R06 | Review verdicts record *partial* correctness: correct; invalid relation (triplet); invalid role or qualifier (right value, wrong role); incomplete (participant missing). They also record which bindings were wrong. | MUST | P9 (role accuracy), P3a | CUR §4 ("curation of a hyperedge should record which participants and which roles were wrong"); HIL §2 (HyperRED's three-way verdict), §8 item 1 (adds "incomplete — participant missing") |
| C3-R07 | The linter action log is append-only. Each entry has: log id, target id, rule id and rule version, severity, finding, action (reject, flag, auto-fix, propose merge), before and after payloads, actor (linter version or person), timestamp. | MUST | P9, P2 smoke test | PLAN §7 C3 row; SKL §7 (validator diagnostic codes as the precedent) |
| C3-R08 | *Structural lint* is the C1 validator plus the schema's role constraints: role inventory, arity signature, required and allowed roles, filler types, cardinalities. | MUST | P9, P2 smoke test | PLAN §3 P9 row ("role constraints"); SKL §9 (none of the extractors surveyed enforces a typed schema algebra); CUR §2 (required and allowed qualifier constraints) |
| C3-R09 | Quality lints, which do not block: provenance coverage, role completeness, role conformance, arity distribution, duplicate-hyperedge (subsumption) rate, evidence-type mix, constraint-violation rate. A subset subsumption becomes a merge *proposal* for review, never an automatic merge. | SHOULD | P9, P3a | CUR §5 metrics 1–7; ER §5 item 4 ("subset subsumption flagged for review rather than applied blindly") |
| C3-R10 | Every merge, including one that changes arity, is an explicit logged action with before and after. No merge happens through a key collision. | MUST | P9, P7 | SKL §8 (Hyper-Extract's `relation_id: '{name}\|{type}'` lets an insertion promote a binary edge "with no conflict raised and no version recorded"); OQ [03.8] |
| C3-R11 | The queue is append-only and replayable. Replaying the log over the same inputs reproduces the same store state, so order dependence can be measured. | SHOULD | P9 | OQ [03.8]; VER §2b |
| C3-R12 | Queue records and log entries declare their C1/C3 version. | MUST | all | PLAN §7 |
| C3-R13 | A candidate records the typed skill or guidance used to extract it (arity signature, role inventory, identity rule). | SHOULD | P9, P11 | OQ [03.9], [08.9]; SKL §4, §10 |
| C3-R14 | Besides whole hyperedges, the queue carries binding proposals for goal slots, merge proposals and supersession proposals. | SHOULD | P11, P7 | Recommendation, from PLAN §3 P11 row and TMP §7 item 3 |

---

## 5. C5: scorers, and the question-set record they read

C5 is owned by P2, with question sets from P3a (PLAN §7). C5 therefore has to fix the *shape* of a
question record that P3a fills.

### 5.1 Across all scorers

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C5-R01 | Every score records the C1 and C5 versions, the corpus (C4) version and split, the question-set version and the scorer configuration. Output is machine-readable. | MUST | all | PLAN §7; BEP §6; DQL §10 item 1 ("Never cite a benchmark by name alone") |
| C5-R02 | Scores are reported per arity bin (2, 3, 4, ≥ 5) beside the aggregate, using C1's arity definition. | MUST | P3b, P8, P9, P4 | EVC §7 item 3 ("No published KHG paper does this"); BEP §5 item 5; LIM §1 mitigation |
| C5-R03 | Per-item results (per fact, per query, per question), keyed by stable ids. | MUST | P8 (correlation between the four abilities) | PLAN §4 P8 gate; CST §3 |
| C5-R04 | Dispersion over seeds or runs, with intervals. | SHOULD | P3b, P4, P9, P10 | BEP §5 item 6; CRH §7 item 5 |
| C5-R05 | Scorers are deterministic and call no LLM by default. An LLM-judged metric is optional, names the judge and its protocol, and never stands alone. | SHOULD | P4, P10, P7 | EVC §5; HPR §6 item 3 ("LLM judging is now two deep"); TMP §6 (LoCoMo strict-judge and LLM-judge numbers are not comparable) |
| C5-R06 | The question-set record has: id, text, type, gold answers (entity ids or literals, with aliases), supporting hyperedge ids, hop count, arity of the required edge, as-of time (memory questions), superseded facts involved, and split. | MUST | P3a (fills it), P10, P4, P7, P8 | PLAN §3 P3a row ("question sets for retrieval and memory"), §7 C5 row; CST §3 items 3–4 |

### 5.2 Extraction

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C5-R07 | Strict n-ary precision, recall and F1: a prediction counts only if the relation, every role and every filler match. Both micro and macro averages. | MUST | P9, P8 | EVC §1 (the HyperRED rule, and Text2NKG's "the entire fact must match the ground facts completely", [Luo et al., 2024](https://arxiv.org/abs/2310.05185)) |
| C5-R08 | **Role accuracy**, defined over matched participants: the share of predicted participants that match a gold participant *and* carry the right role. | MUST | P9 gate | PLAN §4 P9 gate; CUR §4; LIM §8 ("Measure *grouping* accuracy") |
| C5-R09 | A relation-only (triplet-only) score beside the full-fact score. | MUST | P9 | EVC §1 (reporting both "is good practice: it separates 'found the relation' from 'found the roles'") |
| C5-R10 | Soft F1 with global (Hungarian) matching plus a participant-set overlap term, for open-vocabulary output. Greedy matching is not offered. | SHOULD | P9, P8 | EVC §2 ("greedy nearest-neighbour matching ... inflates recall"), §7 item 2; SKL §5 caution 1 |
| C5-R11 | **Stability**: Jaccard agreement of canonical content keys across K runs and across insertion orders. | MUST | P9 gate | EVC §6; OQ [03.8]; PLAN §4 P9 gate |
| C5-R12 | Declared normalisation for literals (date precision, units) and for entity matching (ids or mentions). | SHOULD | P9 | SCH §2; EVC §1 |
| C5-R13 | Arity distribution of predictions against gold, and partial credit when arity differs. | SHOULD | P9 | OQ [03.7]; SKL §3; NXT open problems ("No shared metric handles partial credit for hyperedges that differ in arity") |

### 5.3 Retrieval

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C5-R14 | Exact match and token-level F1 against gold answers, broken down by question type (binary-source vs n-ary-source), hop count and arity of the required edge. | MUST | P10, P4, P8 | EVC §4; HPR §2; CRH §2.3 (HyperGraphRAG's gain is larger on binary-source questions) |
| C5-R15 | Cost and latency per question: prompt and completion tokens, LLM calls, turns, wall-clock time. | MUST | P10 gate, P4 | PLAN §4 P10 gate; HPR §5; CRH §7 item 6 |
| C5-R16 | Recall of the gold supporting hyperedges, by id, to separate retrieval from generation. Similarity between the retrieved text and the construction unit is not used as evidence. | SHOULD | P4, P8 | CST §3 item 3; CRH §2.2, §7 item 2 |
| C5-R17 | An adapter for external question sets (GraphRAG-Bench), whose native metric is reported separately. | SHOULD | P4 | PLAN §4 P4 gate; OQ [07.2] |

### 5.4 Memory

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C5-R18 | Accuracy on the superseding-fact question set, split into as-of-now questions whose answer changed (current value vs superseded value) and as-of-past questions. | MUST | P7 gate, P8 | PLAN §4 P7 gate; TMP §6–§7 (the LongMemEval "knowledge updates" ability, [Wu et al., 2024](https://arxiv.org/abs/2410.10813)); CST §3 item 4 |
| C5-R19 | Stale-answer rate (a superseded fact returned as current) and abstention rate, reported separately. | SHOULD | P7, P8 | TMP §6 (LongMemEval's five abilities include abstention), §7 item 5 |

### 5.5 Completion

| Id | Requirement | Level | Consumers | Source |
|---|---|---|---|---|
| C5-R20 | Filtered MRR and Hits@1/3/10, with the filter set train ∪ valid ∪ test. The corruption universe and the predicted positions (all positions, primary object only, qualifier values) are configurable. | MUST | P3b gate, P8 | BEP §1, §2, §5 items 1–2 |
| C5-R21 | The averaging denominator (per prediction task or per fact) is declared. Per-position and per-arity breakdowns are reported. | MUST | P3b, P8 | BEP §1 (HypE averages "over K = Σ \|r\| prediction tasks, not over test facts", [Fatemi et al., 2020](https://arxiv.org/abs/1906.00137)), §5 item 5 |
| C5-R22 | Calibration by arity: reliability curves and a scalar calibration error per arity bin. | MUST | P3b gate | PLAN §4 P3b gate; XAI "Calibration" and §5 item 3 ("Calibration curves alongside MRR ... stratified by arity"). The choice of scalar metric is a Recommendation; the KB names none. |
| C5-R23 | Protocol presets that reproduce the published evaluation of each replicated model within a stated tolerance. | MUST | P3b gate | PLAN §4 P3b gate; BEP §5 item 1 ("HypE's JF17K MRR 0.494 and StarE's 0.574 are different tasks") |
| C5-R24 | The qualifier-bearing (n-ary) subset is scored separately, with the leak-check result attached. | SHOULD | P3b, P3a | DQL §10 items 3 and 8; BEP §6 |
| C5-R25 | Inductive settings: the inference graph may differ from the training graph (unseen entities and relations). | SHOULD | P8 (the HYPER completer) | BEP §3.2; PLAN §3 note on P8's completer ([Huang, Galkin, Bronstein and Ceylan](https://arxiv.org/abs/2506.12362)) |

---

## 6. Fact identity: the four P7 cases, and the other cases the KB raises

**What is established.** The KB says outright that the question is open: "When `r(a,b)` and `r(a,b,t)`
are extracted from different documents, is the second a refinement, a distinct fact, or a contradiction?
If an arity-4 fact becomes arity-5, is it the same fact? ... No system, format or benchmark has an
opinion" (OQ Theme 4, [03.1] [04.3] [03.4]). Every classification below is therefore **Derived**: it is
what the KB's arguments suggest. P7 specifies the final classification. What P2 owes P7 is that every
fact the classifier needs can be represented in C1.

**Notation.** `rel(role: value, … | qualifier: value, …) valid[from, to)`, where `|` separates core
bindings from qualifier bindings. Ids like `ent:X` are placeholders, not real identifiers.

### 6.1 Case 1: refinement

```
A  position_held(holder: ent:LouisXIV, position: ent:KingOfFrance)                       evidence: doc1
B  position_held(holder: ent:LouisXIV, position: ent:KingOfFrance
                 | start_time: 1643-05-14 (day), end_time: 1715-09-01 (day))             evidence: doc2
```

- **KB argument.** ER §4 uses exactly this pair as "the same statement with different qualifier sets".
  It notes that a subsumption merge "is natural but is not implemented in any system inspected here", and
  ER §5 item 4 says subset subsumption should be "flagged for review rather than applied blindly". Adding
  qualifiers "may only narrow down the answer set, but never enlarge it" (SCH §4, [Hu et al.,
  2024](https://arxiv.org/abs/2404.09848)). HRV §5 gives the rule of thumb: if the fact would still be a
  fact without the extra arguments, it is a triple with qualifiers. The dates are the KB's own (SCH §5,
  quoting Help:Qualifiers).
- **Suggested classification.** Refinement: the same fact. B's extra bindings are qualifiers on identical
  core bindings, so B entails A. The result is one hyperedge carrying B's bindings and *both* evidence
  records, or two hyperedges joined by a `refines` link. Either way it is a merge *proposal* (C3-R09),
  logged as an explicit event (C3-R10).
- **Counter-case.** Take `treats(drug: metformin, condition: T2DM)` against
  `treats(drug: metformin, condition: T2DM, population: adults)`. If `population` is declared a
  *required core* role, the first record is an incomplete candidate (C3 verdict "incomplete"), not a fact
  to merge. If `population` is declared a qualifier, the pair is a refinement. LIM §8 warns that dropping
  the population "may invert the claim's applicability". **The classification depends on the schema.**
- **What C1 must carry.** Slot class per role (C1-R17), `required` (C1-R25), the core content key
  (C1-R02), evidence lists that can be merged (C1-R35), and a merge event (C3-R10).

### 6.2 Case 2: distinct fact

```
(2a) same relation and subject, different key-bearing qualifier
A  population(place: ent:CityX | quantity: n1 (unit: people), point_in_time: 2019 (year))
B  population(place: ent:CityX | quantity: n2 (unit: people), point_in_time: 2023 (year))
   declared key(population) = {place, point_in_time}

(2b) same participants, roles swapped
A  defeated(winner: ent:P, loser: ent:Q | event: ent:E1)
B  defeated(winner: ent:Q, loser: ent:P | event: ent:E2)

(2c) same core bindings, disjoint validity
A  spouse(person: ent:P, spouse: ent:Q)  valid[1990, 1995)
B  spouse(person: ent:P, spouse: ent:Q)  valid[2001, +∞)
```

- **KB argument.** For 2a: population qualified by point in time (P585) and determination method is
  Wikidata's own example (WDF §2). With the declared key, the key bindings differ, so both facts are valid
  and there is no conflict. A naive functional key on (subject, relation) would wrongly treat B as
  superseding A. For 2b: Hyper-RAG keys high-order hyperedges on the vertex tuple, "so paraphrases merge
  but different facts over the same entity set also merge" (ER §4; PGE §3). For 2c: spouse qualified by
  start time and end time is also a Wikidata example (WDF §2), and valid time is an interval on the fact
  (TMP §1(a)).
- **Suggested classification.** All three are distinct facts. 2b shows that identity must include roles,
  not only the participant set. For 2c, merging the two into one interval would assert the gap. That is,
  unless the design allows a set of validity periods on one fact (decision D-07).
- **What C1 must carry.** Key declarations (C1-R28), roles in the content key (C1-R02), and valid time
  (C1-R46).

### 6.3 Case 3: contradiction

```
(3a) key conflict with a later valid-from
A  chief_executive(organisation: ent:O, person: ent:X)  valid[2019-01-01, +∞)  recorded 2019
B  chief_executive(organisation: ent:O, person: ent:Y)  valid[2021-06-01, +∞)  recorded 2021
   declared key(chief_executive) = {organisation}

(3b) the same, but both claim valid[2019-01-01, +∞): a genuine conflict

(3c) explicit negation
A  catalysed_by(reaction: ent:R, catalyst: novalue)
B  catalysed_by(reaction: ent:R, catalyst: ent:C)
```

- **KB argument.** A key role set is what makes contradiction *definable* on an n-ary fact (TMP §1(b)).
  The KB's own illustration is `employment(person: A, employer: B, role: C, salary: D)`: whether a salary
  change is a supersession, a distinct fact, or neither depends on the declared key. Graphiti: "When the
  system identifies temporally overlapping contradictions, it invalidates the affected edges by setting
  their tinvalid to the tvalid of the invalidating edge" and "consistently prioritizes new information"
  (INC §5; [Rasmussen et al., 2025](https://arxiv.org/abs/2501.13956)). TOKI types four production
  policies (last-writer-wins, evidence-weighted merge, await-confirmation, per-rule policy) as operators
  (TMP §2; [Wang, 2026](https://arxiv.org/abs/2606.06240)). Wikidata records unresolved conflicts with
  ranks instead of deleting (ER §4). "This reaction has no catalyst" needs `novalue` (OWA §8 item 3).
- **Suggested classification.** 3a is a key conflict that Graphiti's policy resolves as a *supersession*:
  A gets `t_invalid = 2021-06-01`, A is kept, and a link `supersedes(B → A)` carries the evidence. 3b is a
  *genuine contradiction*: keep both, mark them disputed or rank one deprecated. Resolving it is a policy,
  not a format rule. 3c is a contradiction over the overlapping validity, and it can only be detected if
  `novalue` is representable.
- **What C1 must carry.** Keys (C1-R28), bitemporal time (C1-R46), supersession links with evidence
  (C1-R42), statuses and rank (C1-R41, R43), `novalue` (C1-R08). **What C2 must do:** detect key conflicts
  (C2-R18) and supersede atomically (C2-R19).

### 6.4 Case 4: arity change

```
(4a) the membership of a stored fact changes
A  committee(body: ent:C, member: ent:m1, member: ent:m2, member: ent:m3)  valid[2024-01-01, +∞)
   event: ent:m4 joins on 2025-03-01
   option i   mutate A in place: add member: ent:m4                (history lost unless bindings are logged)
   option ii  close A at 2025-03-01; create A' with four members; A' supersedes A   (n-1 bindings copied)
   option iii add member: ent:m4 to A with its own valid[2025-03-01, +∞)          (per-binding validity)

(4b) silent promotion through a key without participants  ([03.8])
A  "Founding of SpaceX" | founding   participants {Musk, SpaceX}
B  "Founding of SpaceX" | founding   participants {Musk, SpaceX, 2002, Hawthorne}
   Hyper-Extract key '{name}|{type}' is identical, so the records collide and an LLM merger reconciles them

(4c) arity drops through erasure
A  employment(person: ent:P, employer: ent:E, colleague: ent:K, ...)   K asks for erasure
   options: delete A / delete K's incidence / tombstone the binding
```

- **KB argument.** For 4a: "If a committee gains a member, one role-binding changed and the rest did not;
  closing the whole hyperedge and opening a near-copy duplicates n−1 bindings per change. Nothing found
  attaches intervals below hyperedge granularity" (TMP §1(c)). "If a fact of arity 4 becomes a fact of
  arity 5, is it the same fact? ... No system surveyed here has an opinion" (VER §2). The mitigation is "a
  stable surrogate identifier plus a content hash of its core roles; keep an append-only assertion log"
  (LIM §11). For 4b: Hyper-Extract's `relation_id: '{name}|{type}'` leaves participants out of the key,
  so an insertion can promote a binary edge to n-ary "with no conflict raised and no version recorded".
  The alternative key, label plus sorted participants, "makes arity part of identity and so forks instead
  of merging. **Neither convention is right**" (SKL §8; [Hyper-Extract
  repository](https://github.com/yifanfeng97/hyper-extract)). For 4c: GOV §4(b) lists three bad options.
- **Suggested classification.** 4a: the fact keeps its identity when the changed role is repeatable and
  outside the key. It is the same fact in a new version, via option ii (whole-edge validity plus a
  supersession link, implementable today) or option iii (what P7 needs in order to test [07.10]). A change
  to a *key* binding makes a different fact, not a new version. 4b: once roles are added, B reads as
  `founding(founder: Musk, organisation: SpaceX | point_in_time: 2002, location: Hawthorne)`, which is a
  *refinement* of A. It must be an explicit merge event carrying both evidence records, never a key
  collision. 4c: open ([10.6]). C1 must at least be able to represent a tombstoned binding (C1-R10), so
  that the choice stays open.
- **What C1 must carry.** Repeatable roles (C1-R14), keys (C1-R28), supersession (C1-R42), optional
  per-binding validity (C1-R48), tombstones (C1-R10), and merge events (C3-R10).

### 6.5 Other identity cases in the KB

| # | Case | Evidence | What the KB suggests | C1 requirement |
|---|---|---|---|---|
| I5 | Paraphrase under text-as-id: HyperGraphRAG keys hyperedges as `"<hyperedge>" + sentence` | PGE §3; FMT §5 anti-pattern "Using the fact's text as its ID" | The same fact. Dedup by the role-based content key, never by text. | C1-R01, R02 |
| I6 | Provenance used as a role: `treats(…, source: doc1)` vs `treats(…, source: doc2)` | SCH §8 pitfall 2 | One fact with two references | C1-R35 |
| I7 | A member-set key merges different facts (Hyper-RAG `upsert_hyperedge(id_set, …)`) | PGE §3; ER §4 | Distinct facts. The key must include the relation and the roles. | C1-R02 |
| I8 | Permuted fillers of a symmetric role: `co_authors(A, B, C)` vs `co_authors(C, A, B)` | LIM §3 | The same fact. Positional encodings "learn one from the data's accidental ordering". | C1-R15 |
| I9 | One node in two roles: `flies_between(carrier: AC, origin: YYZ, destination: YYZ)` | LIM §3 ("a round trip, a data error, or a collapsed role?") | Legal with named roles. A declared must-differ constraint turns it into a lint finding. | C1-R13, R34 |
| I10 | Entity merge: two entity ids resolve to one, so hyperedges that differed only in those ids become duplicates | ER §5; LIM §9 | Merge them and keep all evidence and binding-level provenance | C2-R20, C3-R10 |
| I11 | Literal precision: `point_in_time: 1921 (year)` vs the same year at day precision | Derived from SCH §6.2 (the `precision` field) | Compatible. The finer value refines the coarser. It is not a contradiction. | C1-R07, R52 |
| I12 | `somevalue` followed by a concrete value: `spouse(P, somevalue)` then `spouse(P, Q)` | Derived from OWA §3 (semantics of `somevalue`) | Refinement: the existential gets a witness | C1-R08 |
| I13 | RDF 1.2 import: "One reifier may also be used to reify multiple, distinct propositions", and a reifier stands for an *occurrence* | NRY §5 | One hyperedge per reifier occurrence. Several reifiers of one triple term are several statements of one proposition; the content key decides merges (Derived). | C1-R02, R57 |
| I14 | Statements that share the main `(s, r, o)` but differ in qualifiers | DQL §10 item 8; LIM §5 ("de-duplicate on the *core* of the fact") | Distinct facts, but they must not straddle train and test | C1-R02, R18 |
| I15 | Relation identity under projection: WD50K becomes a KHG "by hashing the main relation and predicates in canonical order" | BEP §3.2 | One C1 relation maps to many positional relations. Identity lives at the C1 level, and each projection records its mapping. | C1-R58 |
| I16 | Blank-node relation instances: NRY §2 reports that the W3C note recommends blank nodes for relation instances when identical arguments should be treated as the same instance | NRY §2 | On RDF import, blank-node instances are keyed by content (Derived) | C1-R02, R57 |

---

## 7. Pitfalls the record format and the HIF convention must handle

| # | Pitfall | Evidence | What C1 or the HIF convention must do |
|---|---|---|---|
| PF-01 | **HIF has no file-level version, and its schema's identity is not pinned.** | STD §4 and HIF §4 (KB). **V-HIF:** the HIF-org and pszufe `HIF-standard` copies are byte-identical (same MD5). Both say `"version": "latest"`, and their `$id` (`…/HIF_validators/main/schemas/schema.json`) returns HTTP 404. The copy that HyperNetX fetches (`hif_schema_v0.1.0.json`) differs only in `$id` and in saying `"version": "0.1.0"`. The CHANGELOG still lists only "v0.0". That is three version labels for one schema. | Declare the convention's version in `metadata`, vendor the schema and record its hash (C1-R62, R65), and propose a file-level version field upstream (D-02) |
| PF-02 | **No extra keys anywhere:** HIF sets `additionalProperties: false` on the top level and on every record kind | HIF §3; V-HIF | Put every semantic in `attrs` or `metadata` (C1-R62, R64) |
| PF-03 | **Producers disagree on the role key's name.** The KB's own sample uses `attrs.role` (a string), while P2's convention is called `roles`. | HIF §9 item 1 ("Two HIF files from two producers will not agree on the key name"); SAMPLE | One declared key; read `role` as legacy; migration (C1-R53, D-01) |
| PF-04 | **A node playing two roles in one fact** | LIM §3; REL §1b. **V-HNX:** duplicate (edge, node) incidences are dropped by default. **V-XGI:** edges are node sets. | One incidence with a *list* of roles (C1-R13, R63) |
| PF-05 | **Repeated and symmetric roles** | SAMPLE `f2` (two `agent` incidences); LIM §3 (`co_authors`); SCH §6.1 (`together_with`) | Multiset semantics per role, and identity that ignores permutation (C1-R14, R15) |
| PF-06 | **Ordered roles** (a flight visiting airports in order) | NRY §2 (Pattern 2); REL §1b (`position`) | A position per binding when the role is `ordered` (C1-R15) |
| PF-07 | **Nested facts, facts about facts** | HIF §9 item 2 (no nesting). META §1, §8 (acyclicity). ACE forbids events as arguments (NXT §1). Every standard benchmark is flat (META §8). | Hyperedge-reference values, an acyclicity check, a HIF node mirror for referenced edges, and a `nestable` flag (C1-R23, R24, R67) |
| PF-08 | **Qualifiers vs participants** (hyper-relational vs n-ary) | HRV §1–§2 (conversions lose "subject/object attribution, and the monotonicity property"); SCH §4, §8 pitfall 1 ("Electing a primary pair too early"); NRY §8 ("is a qualifier *part of* the fact or *about* the fact?") | Slot class per role, and an optional, derived `primary` (C1-R17, R18) |
| PF-09 | **Literal values vs entities** | SCH §2, §8 pitfall 5; BEP §5 item 4; HIF §2 (an incidence must name a node) | Typed literals inline in C1, deterministic literal nodes in HIF, and literal-dropping only as a projection (C1-R06, R07, R11, R68; D-09) |
| PF-10 | **Directed tail/head vs roles.** "Directed" has three incompatible senses. Rule edges and fact edges must not be mixed without a marker. | DIR §1, §5; HRV §5; HIF §2. **V-XGI:** in directed files, direction is read from every incidence. HyperNetX has no direction model (LIB §1). | Direction derived from role declarations, an edge kind, and `direction` on every incidence of a directed file (C1-R05, R19, R66; D-12) |
| PF-11 | **Weights have no meaning in HIF.** The sample carries confidence in `edges[].weight`. MLN weights are not fact probabilities. | HIF §2–§3; SAMPLE (`f1` weight 0.95); OWA §5 caveat. **V-XGI:** XGI 0.10.2's reader ignores `weight` on incidences, nodes and edges, and its writer emits none. | Confidence goes in `attrs` with its scale. HIF `weight` is at most a documented, derived projection (C1-R49; D-13). |
| PF-12 | **Uncertainty scales are incompatible:** a probability, an LLM score in (0, 10], an editorial rank | SCH §5; OWA §4, §7; LIM §8 | Store `{value, scale}`; keep rank separate (C1-R43, R49) |
| PF-13 | **Open vs closed world** | OWA §1–§3, §8 items 2–3; OQ [02.1] | Absence means unknown; `novalue` and `somevalue` are explicit; completeness assumptions are stored apart from facts (C1-R08, R50) |
| PF-14 | **Erasure.** Three bad options: delete the fact, delete the incidence, or tombstone it. | GOV §4(b), §5, §8 item 7; OQ [10.6] | Do not rule out tombstones or suppression, and keep per-incidence provenance (C1-R10, R36, R45; D-17) |
| PF-15 | **Time conflated.** Time as a qualifier, as validity, and as structural evolution are three different things. | TDK introduction; SCH §5; TMP §1(a) | Separate valid time, transaction time and qualifier time; half-open intervals; `+∞` (C1-R46, R47) |
| PF-16 | **Provenance lost by flattening, or stored as a role** | LIM §9 ("Attaching the citation to each edge over-claims"); SCH §8 pitfall 2 | Evidence on the fact and on each binding, never as a role (C1-R35, R36) |
| PF-17 | **Identifiers with no global meaning, and text used as an id** | HIF §9 item 3; FMT §5; LIB §1 (Hypergraphx re-indexes node ids to integers); V-XGI (ids cast through `nodetype`) | Namespaced string ids (C1-R01, R04) |
| PF-18 | **Fact, context and rule edges mixed together** | DIR §5 | An edge kind (C1-R05) |
| PF-19 | **Empty edges and unbound roles.** HIF allows empty edges; TypeDB removes relations without role players; Hyper-KGGen demands ≥ 2 distinct participants. | HIF §2; QL §3; SKL §3 | Validation that depends on status (C1-R72); a decision on how a goal with no bound roles appears in HIF (D-18) |
| PF-20 | **`network-type` and `direction` are not tied together** by the HIF schema | V-HIF (the schema has no conditional constraint) | A validator rule (V12, V13 in section 8) |
| PF-21 | **Libraries' HIF input/output loses data** | **V-XGI:** incidence `attrs` and all `weight` fields are ignored on read. **V-HNX:** the schema is fetched over the network on every read and write; a validation failure is turned into `HyperNetXError(ex)` without `raise`, so the functions return `None`; `to_hif(metadata=dict)` assigns the result of `dict.update(...)`, which is `None`; missing values become `"nil"`. LIB §1: Hypergraphx re-indexes ids. All of this is from source reading, not executed. | The loaders own the conversion. Validate with vendored schemas. Post-process exports (C1-R70, R73; D-19). |
| PF-22 | **RDF dialects are split.** The 2021 Community Group put quoted triples in subject position; RDF 1.2 allows triple terms only in object position. rdflib 7.6.0 cannot parse RDF-star or RDF 1.2 triple-term syntax. | RDF §1, §6; LIB §3 | The relation-instance pattern is the primary RDF mapping; the reifier form is optional and lossy (C1-R57) |
| PF-23 | **Global vs local role names**, and canonicalisation within a relation | SCH §3; ER §3; HRV §4 (FrameNet's roles are local) | Global ids, per-relation usage declarations, aliases (C1-R26, R31) |
| PF-24 | **Variable arity and the combinatorial explosion** of relation types | SCH §3, §8 pitfall 4; HRV §1(3); LIM §4 | Optional roles (C1-R29) |
| PF-25 | **Schema drift** across incremental runs | INC §8 item 6; SIA §8 | A schema id and version on every record (C1-R32) |
| PF-26 | **Arity is counted in different ways** (entities vs facts vs statements) | LIM §1 (three WikiPeople figures measure three different things); WDF §4 | One written arity definition (C1-R16; D-06) |
| PF-27 | **JSON has no NaN** | HIF §7 (XGI's `convert_nans`); V-HNX (`fillna("nil")`) | No NaN, no placeholders (C1-R69) |
| PF-28 | **HIF is a single document with no streaming** | HIF §9 item 5 | HIF is for interchange only. For large corpora C1 should allow a line-delimited serialisation (Recommendation). |
| PF-29 | **Wikidata ranks are read as truth values** | OWA §3 ("Deprecated ≠ false") | Rank is its own field (C1-R43) |

---

## 8. Candidate malformed cases for the validator

"Core" marks my recommended minimum list for the P2 gate; "extended" marks cases for later. "Status"
marks cases where the verdict depends on the record's status (C1-R72). Layers: **HIF** = the vendored
HIF schema; **conv** = the `roles` convention; **record** = C1 plus the relation-type schema; **schema** =
schema documents; **store** = checks across records that need the store; **queue** = C3.

| Code | Malformed case (minimal form) | Layer | Source | Gate list | Status-dependent |
|---|---|---|---|---|---|
| V01 | No `incidences` key | HIF | HIF §2–§3 | core | no |
| V02 | An extra top-level key (for example `"roles": {…}` next to `metadata`) | HIF | HIF §3, consequence 1 | core | no |
| V03 | Role written at the top level of an incidence (`{"edge":"f1","node":"x","role":"agent"}`) instead of inside `attrs` | HIF | HIF §3, consequence 2 | core | no |
| V04 | An incidence without `node` or without `edge` | HIF | HIF §2 | core | no |
| V05 | `direction` other than `head` or `tail` | HIF | HIF §3 | extended | no |
| V06 | An id of the wrong type (float, null, object) | HIF | HIF §3 (string or integer) | extended | no |
| V07 | The file uses the convention but `metadata` has no convention id or version | conv | HIF §4; STD §4 | core | no |
| V08 | An incidence of a fact edge with no roles | conv | FMT §3 r2 | core | no |
| V09 | `roles` is empty, is not a list, or contains an empty string or a non-string | conv | Derived | core | no |
| V10 | Two incidence records for the same (edge, node) pair | conv | V-HNX (duplicates dropped); LIM §3 | core | no |
| V11 | The same role twice in one incidence's `roles` list | conv | Derived | extended | no |
| V12 | `network-type: directed` but some incidence has no `direction` | conv | V-XGI | core | no |
| V13 | `direction` present while `network-type` is undirected or absent | conv | V-HIF (no conditional in the schema); Derived | extended (reject or warn: a decision) | no |
| V14 | An edge of kind "fact" with no relation in `attrs` | conv | SAMPLE conventions; SCH §1 | core | no |
| V15 | The declared `arity` disagrees with the bindings | conv | FMT §3 r3; Derived | core | no |
| V16 | A duplicate id inside `nodes` or inside `edges` | conv | V-HIF (the schema has no uniqueness constraint); Derived | extended | no |
| V17 | An incidence names a node that has no node record, where the convention requires typed node records | conv | Derived (a decision) | extended | no |
| V18 | A node record marked as an edge reference points to an edge that does not exist | conv | SKL §8 (Hyper-Extract's strict mode: "ALL participants must exist"); HIF §9 item 2 | core | no |
| V19 | NaN, Infinity or a `"nil"` placeholder | conv | HIF §7; V-HNX | extended | no |
| V20 | Legacy `attrs.role` and `attrs.roles` both present and in disagreement | conv | SAMPLE; Derived | extended | no |
| V21 | A relation not declared in the schema | record | SCH §7; ONT §5 (TypeDB checks `relates` at write time) | core | no |
| V22 | A role not allowed for the relation | record | CUR §2 (allowed-qualifiers constraint) | core | no |
| V23 | A required role missing on an asserted fact | record | CUR §2 (required-qualifier constraint); SCH §3 (`required`) | core | yes: allowed on goals and candidates |
| V24 | A role bound more often than its `max` | record | SCH §3; CUR §2 (single-value constraint) | core | no |
| V25 | Filler type mismatch (an entity of the wrong type; a literal where an entity is expected, or the reverse) | record | SCH §3 (`type`); CUR §2 (value-type constraint) | core | no |
| V26 | A literal that does not parse as its datatype, an invalid precision, or a quantity without a unit | record | SCH §2, §6.2 | core | no |
| V27 | A hyperedge with no bindings | record | QL §3 (TypeDB: "no 'dangling relations'") | core | yes: a goal made only of unbound slots needs a decision |
| V28 | A nesting cycle: an edge contains itself, directly or through a chain | record | META §1, §8 | core | no |
| V29 | A hyperedge reference inside a relation not declared `nestable` | record | SCH §6.1 | extended | no |
| V30 | A valid-time interval with start ≥ end, or a conjunction that contradicts its bounds (for example `Since` with a finite end) | record | TMP §1(a), §7 item 1; TDK §2 (VITA) | core | no |
| V31 | A transaction interval that expires before it was created | record | TMP §1(a) | extended | no |
| V32 | A confidence with no scale, or outside its scale's range | record | SCH §5; OWA §8 item 1 | core | no |
| V33 | An asserted fact with no evidence | record | SCH §5; INC §8 item 2 | core | yes: goals may have none |
| V34 | An UNBOUND value outside a goal hyperedge | record | PLAN §3 P11 (Derived) | core | yes |
| V35 | `novalue` and a concrete value for the same role in one hyperedge | record | OWA §3 (Derived) | extended | no |
| V36 | A status outside the lifecycle, or a transition missing from the table | record/log | PLAN §7 C1 row | core | n/a |
| V37 | `supersedes` points to a missing hyperedge, forms a cycle, or links hyperedges whose key bindings differ | record/store | TMP §1(b), §7 item 3 | core | no |
| V38 | A direction that contradicts the role's declared direction | record | SAMPLE (roles map to directions); Derived | extended | no |
| V39 | A node that is both tail and head of a rule hyperarc | record | DIR §2 (Gallo et al.) | extended | no |
| V40 | No edge kind | record | DIR §5 | core | no |
| V41 | An unknown schema id, or a major version with no migration | record | PLAN §7 | core | no |
| V42 | Two currently valid hyperedges with the same key binding and overlapping valid time | store | TMP §1(b) | extended (conformance test) | no |
| V43 | A relation type with no roles | schema | ONT §5 (TypeDB relations need "at least one associated role type") | core | no |
| V44 | A role declared twice in one relation, or a `primary` or `key` that names an undeclared role | schema | SCH §6.1; TMP §7 item 2 | core | no |
| V45 | A schema id without a semantic version | schema | PLAN §7 | core | no |
| V46 | An unknown datatype or entity type | schema | SCH §6.1 | extended | no |
| V47 | A candidate without a run id, an extractor version or evidence | queue | PLAN §4 P9 gate; OQ [03.8] | core | no |
| V48 | A log entry that names a missing candidate, or an action outside the vocabulary | queue | PLAN §7 C3 row | extended | no |
| V49 | A merge that is not in the log (the store's state differs from a replay of the log) | queue/store | SKL §8 | extended | no |

---

## 9. Decisions the design must make

Each decision gives the options the KB offers, which consumers pull which way, and a **Recommendation**
that the design stage can overturn.

**D-01 Where roles live in HIF, and under which key.** Options: (a) `attrs.role`, one string per
incidence (the KB sample); (b) `attrs.roles`, a list on the single incidence of each (edge, node) pair;
(c) one duplicate incidence record per role; (d) a namespaced key such as `khg:roles`; (e) a role map at
edge level. Pulls: the P2 gate rules out (c), because HyperNetX drops duplicate pairs (V-HNX). XGI drops
incidence attrs in any option (V-XGI), so the XGI loader needs a stash whatever is chosen. The HIF
proposal favours a short key without a namespace. P5 wants roles readable as HyperNetX incidence
properties. **Recommendation:** (b), declared in `metadata` with a version. Read (a) as legacy and write
only (b).

**D-02 Declaring the version and pinning the schema.** Options: a `metadata` block; a top-level key (needs
a change to HIF, PF-02); rely on the schema URL (PF-01 shows that fails). **Recommendation:** a `metadata`
block with the convention name, a semver and the hash of the vendored HIF schema. The HIF proposal should
ask for a file-level `version` field, as STD §4 suggests.

**D-03 One slot class or two.** Options (SCH §4): a single class, as in NaLP, RAM and TypeDB; or core plus
qualifiers, as in Wikidata. Pulls: P3a, P3b, P1's RDF annotation export, and P7's refinement rule (which
rests on qualifier monotonicity) want two. P6's symmetric n-ary relations and TypeDB want one.
**Recommendation:** one list of bindings, with a slot class on each role usage in the schema and an
optional derived `primary` pair.

**D-04 Scope of role identity, and naming Wikidata's main-snak roles.** Options: global roles; local roles
(FrameNet); global roles with per-relation usage declarations. Pulls: P6 needs shared attributes. With
relation-local roles every schema hypergraph is a disjoint union of hyperedges and so trivially acyclic
(Derived from RAL §2). RAM's measurement and Wikidata's global qualifier properties favour global roles.
ER §3 warns that roles must also be canonical within a relation. Sub-question: generic `subject`/`value`
roles for main snaks would become two attributes shared by every relation, which changes P6's measurement
(Derived). **Recommendation:** global ids with usage declarations. P3a and P6 must agree on how
main-snak roles are named before C4 is built.

**D-05 Identity and keys.** Options in the KB: text as id (HyperGraphRAG), member set (Hyper-RAG), name
plus type (Hyper-Extract), label plus sorted participants, an opaque id plus a content hash of the core
(LIM §11), and a declared key role set (TMP §7). **Recommendation:** four identifiers with separate jobs.
An opaque `id`. A `core_key`, hashed from the relation and the canonical core bindings with their roles,
for dedup and leak checks. A declared `key`, for supersession. An `event_hash` on extraction events. C1
writes down the canonicalisation rules (literal normalisation, permutation of repeated roles).

**D-06 The arity definition.** Options: count bindings (including qualifiers and repeated fillers); count
distinct participants; count core bindings only; count positions, as HYPER does. Pulls: P3a's histogram
and P3b's per-arity metrics should be comparable with the literature (BEP counts positions k); P9 and
EVC use |e|. **Recommendation:** arity = the number of bindings whose value is an entity, a literal, a
hyperedge or `somevalue`. This agrees with the sample (`f2`: two `agent` bindings plus one `effect`,
arity 3). The sample cannot tell this rule apart from counting distinct participants, though, because its
two agents are different nodes. Report distinct participants as a second number. Settle it with P3a.

**D-07 Granularity of validity, and the time model.** Options: an interval on the hyperedge; intervals on
each binding; time only as a qualifier; timestamps (NE-Net) or intervals (VITA); snapshots. Pulls: P7
needs hyperedge-level validity, and per-binding validity to test [07.10]. P3a brings Wikidata's P580,
P582 and P585 qualifiers. P11 brings binding events. **Recommendation:** hyperedge-level bitemporal
fields are mandatory and per-binding validity is optional. Wikidata time qualifiers stay as bindings *and*
map to valid time through a rule declared in the schema. P3a and P7 fix that rule together, including
whether a point in time is an instant or a precision-wide interval, and whether a fact may hold several
disjoint periods (case 2c).

**D-08 Status, rank and the transition table.** Options: one status field; status, rank and confidence
kept apart; Wikidata's rank alone. **Recommendation:** three separate fields. States: *candidate, asserted,
disputed, superseded, retracted, goal*, with *suppressed* as a visibility tier. Transitions are events
(C1-R54).

**D-09 How literals appear in HIF and in the stores.** Options: literal nodes shared by value; one literal
node per binding; the literal on the incidence (impossible without some placeholder node, since an
incidence must name a node). Pulls: for walkers (P10, P4), value-shared nodes such as a year become hubs
that join unrelated facts (Derived). For P1, fidelity may differ by store (TypeDB attributes are
**[unverified]**). P5 draws literals as nodes. **Recommendation:** in C1, literals stay inline as typed
values. In HIF they become nodes with ids derived deterministically from the value, marked `literal`.
`incident()` leaves literal nodes out unless asked, and walkers treat them as terminal. Revisit if P10
finds a hub effect.

**D-10 How supersession is represented.** Options: a `supersedes` field on the new record; a separate meta
hyperedge that carries the adjudicating evidence (TMP §7 item 3); closing intervals only (Graphiti).
Pulls: P7 wants evidence on the link. P1 finds a field easy on every backend, whereas a meta hyperedge
needs nesting everywhere, and HIF, XGI and HyperNetX do not interpret nesting. **Recommendation:** a meta
hyperedge of relation `supersedes` (roles `superseding` and `superseded`, with evidence) as the source of
truth, plus closing the old fact's intervals. Stores may index it as a pointer. P7 may choose the field
instead if the conformance cost proves too high.

**D-11 How deep nesting goes.** Options: none (flat, as in ACE); one level; unbounded but acyclic (as in
a metagraph). Pulls: P7 and P11 need at least one level. RDF 1.2 allows triple terms only in object
position. TypeDB supports nesting. P5 finds nesting unreadable past two or three levels (VIS §7).
**Recommendation:** unbounded and acyclic in C1, with a `nestable` flag. The conformance test and the gate
cover one level.

**D-12 The direction model.** Options: direction set independently on each incidence; direction derived
from role declarations; no direction. Pulls: XGI's `DiHypergraph` needs a direction on every incidence.
HyperNetX has no direction type (whether direction survives as an incidence property is
**[unverified]**, for the probe report). P5 needs arrowheads. **Recommendation:** roles declare a default
direction. HIF is written as directed only when every binding has one; otherwise it is undirected and the
direction stays in `attrs`.

**D-13 Confidence and weight.** Options: HIF weight = confidence (the sample); `attrs` only; both.
**Recommendation:** `attrs` `{value, scale}` is authoritative. HIF `weight` is an optional projection
documented in `metadata` and never read back, since XGI drops it (V-XGI).

**D-14 How fine-grained evidence is.** Options: a source field on the edge; Wikidata reference records;
PROV-O qualified terms; nanopublication-style assertion, provenance and publication graphs. Pulls: P9
needs spans. P3a needs references and dump revisions. P11 needs evidence for each bound role. P8 needs
completion to be auditable. Governance needs provenance per incidence. **Recommendation:** a list of
evidence records per hyperedge, with PROV-O-named fields and an evidence-type vocabulary in the spirit of
the Gene Ontology codes, plus references to evidence from individual bindings.

**D-15 Syntax of the schema language, and its mappings.** Options: extend the KB's JSON proposal
(SCH §6.1); LinkML (used by SPIRES, LLM §6); TypeQL as the source; SHACL 1.2; YAML templates in the style
of Hyper-Extract. Pulls: P6 needs deterministic parsing. P1 needs TypeQL and SQL. P9 needs typed skills in
prompts. **Recommendation:** a JSON document validated by a JSON Schema, extending SCH §6.1 with `key`,
slot class, `direction`, `nestable`, aliases, external mappings, time model and confidence scale.
Generators for TypeQL, SQL and SHACL are SHOULD.

**D-16 Store semantics in detail.** Options: exact or at-least matching; the default time; whether
superseded facts are included; the result order. **Recommendation:** at-least matching by default with an
exact flag; defaults as-of now and as-at now; *asserted* as the default status; a total order on `id`;
capability flags for each backend.

**D-17 Erasure.** Options: delete the fact, delete the incidence, tombstone the binding, add a suppression
tier. Pulls: governance against P7's need for audit history. **Recommendation:** keep it out of the P2
gate, but make tombstoned bindings and the suppression tier representable so the choice stays open.
[10.6] remains open.

**D-18 Where the queue ends and the store begins, and what the queue holds.** Options: candidates in the
store with status *candidate*; a separate queue (PLAN's P9 row points this way). **Recommendation:** a
separate, append-only queue whose payload is a C1 record with status *candidate*. Item kinds: new
hyperedge, binding proposal, merge proposal, supersession proposal. A goal with no bound slots is written
to HIF as an edge record with its slots in `attrs` and no incidences, which HIF permits.

**D-19 Loader strategy for the gate.** Options: go through each library's own HIF functions
(`xgi.read_hif`/`write_hif`, `hnx.from_hif`/`to_hif`) with pre- and post-processing; or build the
library objects directly from HIF that P2 has already validated. Evidence: XGI's reader drops incidence
attrs, and HyperNetX's input/output needs the network, swallows errors and mishandles `metadata` (PF-21).
**Recommendation:** P2's loaders build XGI and HyperNetX objects directly and restore roles on export.
Separately, the libraries' own HIF readers are tested and whatever they drop is reported. That report is
the evidence for the HIF proposal. The owner should confirm that the gate's "to HIF to XGI and HyperNetX
and back" is met through P2's loaders.

**D-20 What the gate fixture contains.** Options: a minimal record (the sample's `f1`); an adversarial
fixture. **Recommendation:** an adversarial fixture with a node in two roles, a repeated role, an ordered
role, literals of each datatype with precision, a nested reference, direction, a qualifier, evidence on a
binding, non-ASCII ids, `somevalue` and `novalue`, a goal with an unbound slot, and a superseded pair.
Otherwise the round trip passes without testing anything that matters.

**D-21 Matching policy for the extraction scorer.** Options: strict or soft; entity ids or spans; how
role accuracy is defined. **Recommendation:** emit strict, relation-only, and soft Hungarian scores with a
participant Jaccard term. Define role accuracy over matched participants within matched facts. Declare
the normalisation configuration.

**D-22 What v1 of the contracts covers.** Options: everything at once; a v1 core with later minor
versions. **Recommendation:** v1 covers what the P2 gate and the Phase 1 consumer gates need.
Per-binding validity, erasure operations, the SHACL and TypeQL generators and soft F1 can follow in minor
versions, since contracts "are versioned, not frozen" (PLAN §7).

---

## 10. What was verified today, and what is left for the probe report

**Verified 2026-09-23 (V-HIF)**, with `curl` through the session proxy:

- `https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/hif_schema.json`: HTTP 200.
- `https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json`: HTTP 200, with
  the same MD5 as the HIF-org copy.
- `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json`: HTTP
  200. It differs from the two copies above only in `$id` (its own URL) and `"version": "0.1.0"` (the
  others say `"latest"`).
- `https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/schema.json`, the `$id` of the
  HIF-standard copies: HTTP 404.
- `schemas/CHANGELOG.md` on HIF-org still has one entry, "v0.0".
- The schema text: draft-07; `incidences` required; `edge` and `node` typed string or integer;
  `direction` restricted to `head`/`tail`; `attrs` any object; `additionalProperties: false` on the top
  level and on all three record kinds. There is no uniqueness constraint, no referential check between
  `incidences` and `nodes`/`edges`, and no conditional tying `network-type` to `direction`.
- The GitHub API for HIF-org/HIF-standard was not reachable from this session (repository access not
  enabled), so the latest commit date was not re-checked.

**Read 2026-09-23 from the PyPI wheels, not executed:**

- **XGI 0.10.2** (`xgi/convert/hif_dict.py`). `from_hif_dict` takes only `node`, `edge` and, for
  directed files, `direction` from each incidence. From node and edge records it takes only `attrs`.
  Every `weight` field is ignored, and incidence `attrs` are ignored. `to_hif_dict` writes incidences
  without `attrs` or `weight`. It writes node records only for isolated nodes or nodes that have
  attributes, and edge records only for empty edges or edges that have attributes. `metadata` round-trips
  through the network attributes.
- **HyperNetX 2.4.3** (`hypernetx/hif.py`, `classes/hypergraph.py`, `classes/factory.py`). The constant
  `schema_url` points at `hif_schema_v0.1.0.json`, and `requests.get(schema_url)` runs inside both
  `to_hif` and `from_hif`. Validation failures create `HyperNetXError(ex)` without raising it: `from_hif`
  returns `None`, and `to_hif` falls through to `None`. Given a metadata dict, `to_hif` assigns the result
  of `metadata.update(...)`, which is `None`. `normalize_dataframe` ends with `fillna("nil")`. Incidence
  `attrs` go to the constructor as `misc_cell_properties_col="attrs"`, so they are kept as cell
  properties. The constructor's default is `aggregate_by="first"`, and the factory docstring says "By
  default duplicate incidences will be dropped".

**Left for the probe report (P2R plan item 1):** executing all of the above; whether `direction` survives
a round trip through HyperNetX as a cell property; what XGI does with a node that is both tail and head of
one edge; whether HyperNetX reorders or retypes ids; how Hypergraphx behaves (LIB §1 records that it
re-indexes ids). Whether TypeDB literal attributes can play roles is **[unverified]** and belongs to P1's
preparation.

---

## 11. Open questions raised (proposed for the register; not added)

1. **(04)** What is the arity of a hyperedge with repeated role fillers and special values, and does it
   match what the published benchmark statistics count? The answer changes P3a's histogram and every
   arity-stratified score (PF-26, D-06).
2. **(04)** Do literal nodes shared by value create short paths that change walker behaviour and
   hypergraph statistics? (D-09)
3. **(09)** Should a `roles` convention for HIF define what `weight` means, or declare it unspecified?
   (PF-11)
4. **(01)** How should Wikidata's main-snak roles be named so that P6's schema hypergraph is meaningful,
   without creating two hub attributes? (D-04)
5. **(02)** Is a goal with no bound roles a hyperedge at all? TypeDB forbids relations without role
   players, while HIF allows empty edges. (PF-19)

---

## Sources

### Programme and knowledge-base notes (this repository, read 2026-09-23)

- *The programme: eleven projects to move the field*. `projects/PLAN.md`
- *Projects and exploration vectors*. `projects/README.md`
- *Role-aware HIF and the shared contracts*. `projects/p2-role-aware-hif/README.md`
- *Open questions*. `kb/00-index/open-questions.md`
- *HIF — the Hypergraph Interchange Format*. `kb/04-storage-and-formats/hif-hypergraph-interchange-format.md`
- *Format and storage recommendations*. `kb/04-storage-and-formats/format-recommendations.md`
- *Versioning, provenance and scale*. `kb/04-storage-and-formats/versioning-provenance-and-scale.md`
- *Emulating hyperedges in property graphs*. `kb/04-storage-and-formats/property-graph-emulation-patterns.md`
- *Relational, EAV and Datalog storage for n-ary facts*. `kb/04-storage-and-formats/relational-and-eav-storage.md`
- *RDF-star, RDF 1.2 and the semantic-web serialisations*. `kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md`
- *Tensor and sparse representations* (skimmed). `kb/04-storage-and-formats/tensor-and-sparse-representations.md`
- *Knowledge hypergraph schema design*. `kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md`
- *N-ary relations and reification*. `kb/02-knowledge-representation/n-ary-relations-and-reification.md`
- *Hyper-relational vs n-ary vs hypergraph*. `kb/02-knowledge-representation/hyper-relational-vs-n-ary-vs-hypergraph.md`
- *Directed and typed hyperedges for knowledge*. `kb/02-knowledge-representation/directed-and-typed-hyperedges-for-knowledge.md`
- *Ontologies and schemas for n-ary knowledge*. `kb/02-knowledge-representation/ontologies-and-schemas-for-n-ary-knowledge.md`
- *Wikidata and Freebase data models*. `kb/02-knowledge-representation/wikidata-and-freebase-data-models.md`
- *Open world, closed world and uncertainty*. `kb/02-knowledge-representation/open-world-vs-closed-world-and-uncertainty.md`
- *Metagraphs, ubergraphs and hypergraph databases* (skimmed). `kb/02-knowledge-representation/metagraphs-atomspace-and-hypergraphdb.md`
- *Incremental, streaming and temporal construction*. `kb/03-construction/incremental-and-streaming-construction.md`
- *LLM-based knowledge hypergraph construction*. `kb/03-construction/llm-based-khg-construction.md`
- *Skill-driven extraction and the scenario gap*. `kb/03-construction/skill-driven-extraction-and-the-scenario-gap.md`
- *Curation, crowdsourcing and quality control*. `kb/03-construction/curation-crowdsourcing-and-quality.md`
- *Entity resolution, canonicalisation and hyperedge deduplication*. `kb/03-construction/entity-resolution-and-canonicalisation.md`
- *Evaluating constructed knowledge hypergraphs*. `kb/03-construction/evaluation-of-constructed-khgs.md`
- *N-ary relation and event extraction from text* (skimmed). `kb/03-construction/n-ary-relation-extraction-from-text.md`
- *Human-in-the-loop annotation and cost* (skimmed). `kb/03-construction/human-in-the-loop-annotation-and-cost.md`
- *Schema induction and ontology alignment* (skimmed). `kb/03-construction/schema-induction-and-ontology-alignment.md`
- *Time on the hyperedge, and hypergraphs as editable agent memory*. `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md`
- *AI agents — memory and planning over hypergraphs*. `kb/07-applications/ai-agents-memory-and-planning.md`
- *Hierarchical and planned retrieval over knowledge hypergraphs*. `kb/07-applications/hierarchical-and-planned-hypergraph-retrieval.md`
- *Benchmarks and evaluation protocols for n-ary link prediction*. `kb/05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md`
- *Query languages for knowledge hypergraphs*. `kb/05-query-embeddings-reasoning/query-languages-for-hypergraphs.md`
- *Temporal and dynamic knowledge hypergraphs* (skimmed). `kb/05-query-embeddings-reasoning/temporal-and-dynamic-khgs.md`
- *Explainability and uncertainty* (skimmed). `kb/05-query-embeddings-reasoning/explainability-and-uncertainty.md`
- *HYPER foundation model anatomy* (skimmed). `kb/05-query-embeddings-reasoning/hyper-foundation-model-anatomy.md`
- *LLMs and knowledge hypergraphs* (skimmed). `kb/05-query-embeddings-reasoning/llm-and-khg-interaction.md`
- *Classical hypergraph theory results*. `kb/01-foundations/hypergraph-theory-results.md`
- *N-ary relations, relational algebra and the query hypergraph* (skimmed). `kb/01-foundations/n-ary-relations-and-relational-algebra.md`
- *Hypergraph definitions and variants* (skimmed). `kb/01-foundations/hypergraph-definitions.md`
- *Software libraries for hypergraphs and knowledge hypergraphs*. `kb/09-ecosystem/software-libraries.md`
- *Standards bodies and specifications* (§4 read). `kb/09-ecosystem/standards-bodies-and-specifications.md`
- *Dataset quality, leakage and provenance problems* (skimmed). `kb/09-ecosystem/dataset-quality-and-leakage-issues.md`
- *Limitations and failure modes*. `kb/10-comparative-and-critique/limitations-and-failure-modes.md`
- *Privacy, licensing and governance* (skimmed). `kb/10-comparative-and-critique/privacy-licensing-and-governance.md`
- *Critical reading of hypergraph-RAG claims* (skimmed). `kb/10-comparative-and-critique/critical-reading-of-hypergraph-rag-claims.md`
- *Visualising knowledge hypergraphs in practice* (skimmed). `kb/06-visualization/knowledge-hypergraph-specific-visualization.md`
- *The composed stack* (§3 read). `kb/08-history-and-frontier/composed-stack-and-research-bets.md`
- Sample files: `schemas/sample.hif.json`, `schemas/sample-n-ary-fact.ttl`

### Primary artefacts verified on 2026-09-23

- HIF-org. *HIF-standard*, `schemas/hif_schema.json` and `schemas/CHANGELOG.md`, GitHub, fetched 2026-09-23. https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/hif_schema.json ; https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/CHANGELOG.md
- Szufel, P. *HIF-standard* (earlier home), `schemas/hif_schema.json`, GitHub, fetched 2026-09-23. https://raw.githubusercontent.com/pszufe/HIF-standard/main/schemas/hif_schema.json
- Szufel, P. *HIF_validators*, `schemas/hif_schema_v0.1.0.json` (HTTP 200) and `schemas/schema.json` (HTTP 404), GitHub, fetched 2026-09-23. https://github.com/pszufe/HIF_validators
- XGI developers. *xgi* 0.10.2, Python package (wheel from PyPI; `xgi/convert/hif_dict.py` read 2026-09-23). https://pypi.org/project/xgi/0.10.2/ ; https://github.com/xgi-org/xgi
- Pacific Northwest National Laboratory. *HyperNetX* 2.4.3, Python package (wheel from PyPI; `hypernetx/hif.py`, `hypernetx/classes/hypergraph.py`, `hypernetx/classes/factory.py` read 2026-09-23). https://pypi.org/project/hypernetx/2.4.3/ ; https://github.com/pnnl/HyperNetX

### Primary sources cited inline (as cited by the KB notes above)

- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B. and Szufel, P. *HIF: The hypergraph interchange format for higher-order networks*. Network Science 13, e21, 2025. https://doi.org/10.1017/nws.2025.10018
- Noy, N. and Rector, A. (eds). *Defining N-ary Relations on the Semantic Web*. W3C Working Group Note, 12 April 2006. https://www.w3.org/TR/swbp-n-aryRelations/
- W3C. *RDF 1.2 Concepts and Abstract Data Model*. Candidate Recommendation Snapshot, 7 April 2026. https://www.w3.org/TR/rdf12-concepts/
- W3C. *PROV-O: The PROV Ontology*. Recommendation, 30 April 2013. https://www.w3.org/TR/prov-o/
- Wikidata. *Help:Property constraints portal* (checked by the KB 2026-09-20). https://www.wikidata.org/wiki/Help:Property_constraints_portal
- Fagin, R. *Degrees of acyclicity for hypergraphs and relational database schemes*. Journal of the ACM 30(3):514–550, 1983. https://dl.acm.org/doi/10.1145/2402.322390
- Galkin, M., Trivedi, P., Maheshwari, G., Usbeck, R. and Lehmann, J. *Message Passing for Hyper-Relational Knowledge Graphs*. EMNLP 2020; arXiv:2009.10847. https://arxiv.org/abs/2009.10847
- Fatemi, B., Taslakian, P., Vazquez, D. and Poole, D. *Knowledge Hypergraphs: Prediction Beyond Binary Relations*. IJCAI 2020; arXiv:1906.00137. https://arxiv.org/abs/1906.00137
- Liu, Y., Yao, Q. and Li, Y. *Role-Aware Modeling for N-ary Relational Knowledge Bases*. WWW 2021; arXiv:2104.09780. https://arxiv.org/abs/2104.09780
- Hu, Z., Gutiérrez-Basulto, V., Xiang, Z., Li, R. and Pan, J. Z. *HyperMono: A Monotonicity-aware Approach to Hyper-Relational Knowledge Representation*. arXiv:2404.09848, 2024. https://arxiv.org/abs/2404.09848
- Chia, Y. K., Bing, L., Aljunied, S. M., Si, L. and Poria, S. *A Dataset for Hyper-Relational Extraction and a Cube-Filling Approach*. EMNLP 2022; arXiv:2211.10018. https://arxiv.org/abs/2211.10018
- Luo, H., E, H., Yang, Y., Yao, T., et al. *Text2NKG: Fine-Grained N-ary Relation Extraction for N-ary relational Knowledge Graph Construction*. NeurIPS 2024; arXiv:2310.05185. https://arxiv.org/abs/2310.05185
- Feng, Y. *Hyper-Extract* repository (Apache-2.0; commit `395039e`, 2026-09-20, as read by the KB 2026-09-21). https://github.com/yifanfeng97/hyper-extract
- Rasmussen, P., Paliychuk, P., Beauvais, T., Ryan, J. and Chalef, D. *Zep: A Temporal Knowledge Graph Architecture for Agent Memory*. arXiv:2501.13956, 2025. https://arxiv.org/abs/2501.13956
- Wang, Z. *TOKI: A Bitemporal Operator Algebra for Contradiction Resolution in LLM-Agent Persistent Memory*. arXiv:2606.06240, 2026. https://arxiv.org/abs/2606.06240
- Un, C., Lu, Y., Yang, T. and Yang, D. *VITA: Versatile Time Representation Learning for Temporal Hyper-Relational Knowledge Graphs*. arXiv:2505.11803, 2025. https://arxiv.org/abs/2505.11803
- Wu, D., Wang, H., Yu, W., Zhang, Y., Chang, K.-W. and Yu, D. *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory*. ICLR 2025; arXiv:2410.10813. https://arxiv.org/abs/2410.10813
- Huang, X., Galkin, M., Bronstein, M. M. and Ceylan, İ. İ. *HYPER: A Foundation Model for Inductive Link Prediction with Knowledge Hypergraphs*. arXiv:2506.12362, 2025. https://arxiv.org/abs/2506.12362
