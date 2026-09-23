---
title: "P2 design B: semantics-first contracts (C1, C2, C3, C5) and the HIF roles convention"
type: design
status: proposal (independent design B, for judging and synthesis)
created: 2026-09-23
angle: semantics-first rigour (fact identity, keys, time, lifecycle, supersession, evidence, special values)
evidence: research reports R01-R05 (projects/p2-role-aware-hif/research/) and a working prototype (work-B-semantics-first/)
---

# P2 design B: semantics-first contracts

This design turns the five research reports into one set of contracts for P2. Its angle is semantic
rigour. The format must give P7's identity test list exactly one right answer, P9's instability
measurement well-defined keys, and P11's goal edges a well-formed shape. Every claim marked
**[verified]** was checked by running the prototype in
`/tmp/claude-0/-home-user-knowledge-Hyper-Graphs-/9b58e6a1-1989-5ed1-ae3b-676a337fca40/scratchpad/designs/work-B-semantics-first/`
(`run_all.sh` reruns everything, offline). The prototype is scratch code. It exists to check the
design, not to become the package.

**What the prototype established [verified]:**

| Check | Result |
|---|---|
| Four draft-07 schemas (record, schema language, HIF profile, queue) are valid draft-07 | valid under `jsonschema` 4.26.0 and `fastjsonschema` 2.22.2 |
| Gate fixture (directed, 35 records, 49 bindings) and undirected companion (6 records, 7 bindings) | valid against the record schema and, once exported, against the vendored HIF schema (blob `e2105bb`) and the KHG profile, under both validators |
| Gate chain C1 → HIF → XGI → HIF → HyperNetX → HIF → C1 through the loader sketch, sockets blocked | canonical equality on both fixtures and on the migrated KB sample; HIF incidence, node and edge multisets equal; all 49 (edge, node, direction, role, position, bid) tuples equal |
| Same fixture through the libraries' own HIF functions (library-evidence test) | XGI: 49 → 48 incidences, 0/49 roles kept. HyperNetX: 49 → 47 incidences, all 12 metadata keys lost, second directed generation returns `None` |
| Malformed-case list | 108/108 rejected at the expected layer, with the expected code reported first (MC01–MC103 documents and schemas, MC104–MC108 queue); 5/5 positives accepted |
| Stable codes | every constraint of the four P2 schemas (along every path) and of the vendored HIF schema maps to a code; 28 registry probes report their clause's code; annotating and re-dispatching the schemas changed no verdict on 24,013 documents under either validator |
| Identity classification of R01 §6 cases (and 10 extra edge cases) | 34 pairs plus 3 policy variants, each classified deterministically (§2.19) |
| Smoke test (queue → structural lint → store → export) + 18 store checks + 3 C3 checks + 4 declarative scenarios (17 assertions) | all pass; queue item, log entries and verdict validate against the C3 schema under both validators; the log folds cleanly |

Citations use report number and section: [R01 §6.3], [R03 D2], [R04 M5], [R05 §5.2], [R02 §5 case 11].

---

## 1. Summary and the gate

### 1.1 Summary

1. **A fact is a relation plus a list of role bindings, and its meaning fixes its identity.**
   Every binding has a stable binding id (`bid`), a global role id, one value and, for ordered
   roles, a position. The contract defines a *refinement order* ⊑ on facts: f′ ⊑ f means f′ says
   everything f says and possibly more. Duplicates, refinements, conflicts and distinct facts are all
   defined through ⊑, declared keys and valid-time overlap, so each identity case has exactly one
   classification (§2.16–§2.19).
2. **Four identifiers, four jobs (F6).** `id` is opaque and stable across versions. `content_key` and
   `core_key` are content hashes (full content; core only) for dedup, leak checks and P9 stability.
   `key_digest` hashes the declared key bindings and drives collision and supersession. `event_hash`
   identifies an extraction event on an evidence record.
3. **Time is carried by bindings and read by the schema.** Validity-defining roles (Wikidata P580/P582)
   are bindings in slot class `time`. The relation's declared time model derives the hyperedge's
   `valid_time` (period, since, until, invariant or unstated) from them. Bounds carry precision.
   Temporal reasoning uses a *presumed interval* with a definite core and a possible hull, so a
   year-precision handover is not a conflict (§2.12). Transaction time is the store's `recorded_at`
   on immutable versions.
4. **Four lifecycle axes (F7).** Record status, valid time, editorial rank and visibility are
   separate. A fact that ended in the world keeps status `asserted` and gains an `end_time` binding.
   `superseded` means belief revision only, and always points to a `khg:supersedes` record, which is
   the source of truth (F8).
5. **Versions are immutable and change only by refinement.** A new version of an id must entail the
   old one (⊑). Evidence records are immutable and append-only. Any other change is a new fact plus a
   lifecycle record. This single rule makes as-at queries exact and P7's merges auditable.
6. **Keys declare their collision policy.** `key: {roles, temporal, on_collision}` with policies
   `close_older` (world change), `supersede` (belief revision), `dispute` and `reject` [R04 M3].
   Rank takes part in the key invariant with Wikidata's single-best-value semantics.
7. **One HIF incidence per binding.** A node that plays two roles in one fact appears in two
   incidence records, each with its own `direction`, `role` and `role-position` [R02 §6, R03 D2].
   Roles go in `incidences[].attrs.role` (the paper's own key), declarations in flat `metadata` keys
   (F3). Literals, special values and nested-fact references become typed nodes with reserved `_:`
   ids.
8. **Loaders own the codec (F1).** XGI and HyperNetX objects are built through public constructors,
   with a context bundle for what the library cannot hold. A separate evidence test records what the
   libraries' own HIF functions drop.
9. **The store is policy-free and invariant-checking.** C2 validates, versions, enforces the key
   invariant atomically and answers bitemporal reads. The identity planner turns an incoming candidate
   into a write plan. It lives in the package, is a pure function, and is what P7 tests.
10. **Validation is layered, and every failure has a stable code.** The layers are strict JSON,
    the vendored HIF schema, the KHG profile, decode, the record schema, semantics and cross-record
    checks. All JSON Schemas are draft-07 (F5). Semantics run in Python.

### 1.2 The gate, clause by clause

The gate: *"A record round-trips repo format to HIF to XGI and HyperNetX and back with roles intact;
the validator rejects each malformed case in its test list; a smoke test runs one record through
queue, structural lint, store and export."*

| Clause | Test (in `tests/gate/`) | What it asserts | Prototype evidence |
|---|---|---|---|
| 1a "a record round-trips repo format to HIF" | `test_roundtrip.py::test_c1_hif_c1[fixture]` | `canonical(decode(encode(doc))) == canonical(doc)`; the HIF validates against the vendored schema (blob `e2105bb`) and against `khg-hif/1.0.0` | [verified] `run_gate.py` |
| 1b "to XGI and HyperNetX and back" | `test_roundtrip.py::test_chain[fixture]` runs C1 → HIF → `to_xgi` → `from_xgi` → `to_hnx` → `from_hnx` → C1. Also `test_xgi_only`, `test_hnx_only` | canonical C1 equality; the HIF after each library still validates | [verified] both fixtures, both libraries, both orders |
| 1c "with roles intact" | `test_roundtrip.py::test_roles_intact[fixture]` | multiset equality of (edge, node, direction, role, role-position, bid) over all incidences, including the repeated (edge, node) pairs | [verified] 49/49 and 7/7 tuples |
| 1d (implicit) offline and deterministic | autouse fixture `no_network` blocks `socket.connect`; `test_determinism.py` writes the fixture under 4 `PYTHONHASHSEED` values | no socket use; byte-identical canonical output | sockets blocked in every prototype run |
| 2 "the validator rejects each malformed case in its test list" | `test_malformed.py`, parametrised over `tests/gate/malformed/manifest.json` (MC01–MC108) plus `positive/` | each case is rejected at its expected layer **and** the expected code is among the reported codes; each positive case validates with no violation; `test_codes.py` checks that every schema constraint maps to a code | [verified] 108/108 (first reported code = expected in all 108), 5/5 positives, coverage complete (`run_malformed.py`, `khg_codes.py`) |
| 3 "a smoke test runs one record through queue, structural lint, store and export" | `test_smoke.py` | `f:king-14` is submitted as a candidate. Lint gives `linted`, no violations. Acceptance runs the identity plan (outcome: distinct on the `position_held` key timeline) and `store.put`. The store exports `khg-json` and `hif`, both valid, equal to the fixture after store-assigned fields are dropped. The log holds `submit`, `lint` and `accept`, each with actor and time; `accept` also carries before/after and the plan hash. Replaying the log over the same inputs reproduces the store | [verified] `run_smoke.py` |

"A record" is read as the strongest version that is still honest. The round trip runs on each
fixture as one document (every record kind together), on each fact alone, and on the migrated KB
sample (`schemas/sample.hif.json`, §11.3).

---

## 2. C1 record format (`khg-record/1.0.0`)

### 2.1 Principles

- **P-1 Meaning first.** Each field has a reading, and equality and identity follow from the
  readings, never from serialisation (R05 §2.5 pitfall 3 shows what string comparison does).
- **P-2 One source of truth.** Every piece of information lives in one place. Derived fields (`arity`,
  keys, `valid_time`) are recomputed by the canonicaliser and checked by the validator (`KHG-D015`),
  never trusted.
- **P-3 Open world.** A missing binding, bound or interval means *not stated*. Presumptions (an
  absent end means "presumed ongoing") exist only in query semantics, and they are written down
  (§2.12).
- **P-4 History is data.** Stored versions are immutable (F8). Belief changes are records about
  records, not edits.

### 2.2 The document container

There are two serialisations of the same records.

- **`.khg.json`:** `{"header": {...}, "records": [...]}`, exactly these two keys.
- **`.khg.jsonl`:** line 1 is the header object; each further line is one record. It suits large
  corpora, since HIF cannot stream [R01 PF-28].

Header (JSON Schema `#/definitions/header`):

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `kind` | `"header"` | yes | record discriminator |
| `khg` | `"khg-record/1.0.0"` | yes | format id with semver (PLAN §7) |
| `document_id` | id | yes | stable id of the document |
| `schema` | `{id, version, sha256}` | yes | relation-type schema the records are typed under; `sha256` is `digest("khg-schema/1", schema_doc)` |
| `schema_document` | object | no | inline copy of that schema (self-contained files); must hash to `schema.sha256` |
| `snapshot` | `"current"` \| `"history"` | no (default `current`) | `current`: one version per id; `history`: all versions |
| `as_at` | RFC 3339 UTC | no | transaction time of a store snapshot |
| `complete` | bool | no (default `false`) | `true`: every referenced entity and fact is in the document (enables `KHG-D002`) |
| `created_at`, `generator` | timestamp; `{name, version}` | no | provenance of the file |
| `extensions` | map with namespaced keys (`ns:name`) | no | passthrough; `hif:metadata` keeps foreign HIF metadata |

**Canonical order.** Records are sorted by kind (entity, then fact/rule, goal, meta), then `id`,
then `version`. Bindings are sorted by (role, position, canonical value JSON). Evidence is sorted by
`id`. Object keys are sorted and strings are NFC. Tests compare canonical structures (F10). A
separate byte-determinism test covers the serialiser, because content hashes depend on bytes.

### 2.3 Record kinds

| `kind` | What it is | Statuses | Identity | Bindings |
|---|---|---|---|---|
| `entity` | a node that facts talk about (Wikidata item, local id) | none in v1 (`redirect_to` marks a merged id) | `id` | none |
| `fact` | an n-ary statement about the world | `candidate` (queue only), `asserted`, `disputed`, `superseded`, `retracted`, `quoted` | `id` + versions | values: entity, literal, fact-ref, somevalue, novalue |
| `rule` | a tail → head inference hyperarc [R01 C1-R05] | as `fact` | as `fact` | as `fact`; every binding has a direction; tail ∩ head = ∅ |
| `goal` | an open question for P11: a fact pattern with unbound slots | `open`, `satisfied`, `abandoned` | `id` + versions | as `fact`, plus `unbound` |
| `meta` | a lifecycle record about records: `khg:supersedes`, `khg:retracts`, `khg:disputes`, `khg:fulfils` | `asserted`, `retracted` (undo) | `id` | fact-refs only |

The kinds are the edge-kind marker R01 C1-R05 asks for. Meta records use the same machinery as facts:
bindings, evidence, versions and HIF export. So supersession is a hyperedge about hyperedges, as TMP
§1(d) suggests [R01 D-10, R04 M5], and a store needs nothing new to hold it.

### 2.4 Fields common to fact, rule, goal and meta records

| Field | Type | Req. | Meaning / rule |
|---|---|---|---|
| `id` | id string | yes | opaque, stable across versions, never parsed, never reused [R04 M3.4]. Grammar `^(?!_:)[^\s\x00-\x1f\x7f]{1,512}$`, NFC (`KHG-S020`). Entity and fact ids share one namespace and must differ (`KHG-D007`) |
| `version` | int ≥ 1 | store output | assigned by the store; consecutive per id |
| `recorded_at` | RFC 3339 UTC | store output | transaction start of this version; the version's transaction interval is `[recorded_at, next.recorded_at)`, derived and never stored (versions are immutable) |
| `typed_under` | `"schema-id/semver"` | no (default: header) | schema version the record was typed under [R01 C1-R32] |
| `relation` | vocab id | yes | relation type; built-ins start with `khg:` |
| `status` | enum per kind (§2.13) | yes | record status axis |
| `status_ref` | id | when status is `disputed`, `superseded`, `retracted` or `satisfied` | the meta record that explains the status (index pointer, F8) |
| `rank` | `preferred` \| `normal` \| `deprecated` | no (default `normal`) | editorial rank axis; `deprecated` needs `rank_reason` |
| `rank_reason` | string | if `rank` is `deprecated` | e.g. a Wikidata P2241 reason item id |
| `visibility` | `visible` \| `suppressed` | no (default `visible`) | governance axis; suppressed records are hidden from default reads and exports |
| `bindings` | list of binding (§2.5) | yes | the content |
| `evidence` | list of evidence (§2.14) | fact/rule: ≥ 1 non-negated when `asserted` (`KHG-S011`); meta: ≥ 1 | provenance about the fact, never a role [R01 C1-R35] |
| `confidence` | `{value, scale, scorer?}` | no | derived belief, with its scale (§2.11) |
| `text` | string | no | source sentence or rendering [R01 C1-R22] |
| `goal` | `{brief, owner?, closed_reason?}` | goal only | P11 brief |
| `meta` | `{reason, note?, migration_id?}` | meta only | reason code (enum per meta relation) |
| `derived` | object | canonical output | recomputed: `arity`, `core_arity`, `statement_arity`, `distinct_fillers`, `content_key`, `core_key`, `key_digest`, `valid_time` (goals: `n_bound`, `n_unbound`) |
| `extensions` | namespaced map | no | passthrough; `hif:weight` keeps a foreign HIF weight uninterpreted |

Entity records have `kind`, `id`, `version`, `recorded_at`, `types` (entity type ids),
`label`, `aliases`, `redirect_to` and `extensions`.

### 2.5 Bindings and values

A binding is `{"bid", "role", "value", "position"?, "direction"?, "extensions"?}`.

- `bid` is unique within the record and stable across its versions (`^[A-Za-z0-9_.-]{1,64}$`,
  `KHG-S025`). A refinement that turns `somevalue` into a value keeps the `bid`, and so does binding a
  goal slot. Evidence cites bindings by `bid`, which gives per-binding provenance [R01 C1-R36] and
  binding-event history for P11. Bids are not content: they stay out of every content hash.
- `role` is a global role id (F4). The relation type's usage declaration gives its slot class,
  fillers, cardinality, order and direction (§3).
- `position` (int ≥ 1) is required on bindings of `ordered` roles, forbidden elsewhere, and
  contiguous 1..n (`KHG-S015`).
- `direction` (`tail` \| `head`) is allowed only when the role usage declares none. A declared
  direction is the single source; a contradicting value is `KHG-S016`.

**Value kinds** (a tagged union: exactly one key, `KHG-C001`):

| Value | JSON | Reading |
|---|---|---|
| entity | `{"entity": "Q937"}` | that individual |
| literal | `{"literal": {...}}` | a typed value (table below) |
| fact-ref | `{"fact": "f:born-louis14-paris"}` | the fact (its identity, not a version) as a participant |
| somevalue | `{"special": "somevalue"}` | ∃x: some filler exists, identity unknown (Wikidata "unknown value") |
| novalue | `{"special": "novalue"}` | ¬∃x: the role has no filler (Wikidata "no value") |
| unbound | `{"unbound": {"var": "who", "expect": {...}}}` | goals only (`KHG-C005` elsewhere): a variable to be bound |

**Literals.** Each datatype has one canonical form. Equality means equality of canonical forms. The
refinement ⊑ (§2.16) applies where the table says.

| `datatype` | Fields | Canonical form | Refinement v′ ⊑ v |
|---|---|---|---|
| `time` | `time` `^[+-]\d{4,}-\d\d-\d\dT\d\d:\d\d:\d\dZ$`, `precision` 0–14 (Wikidata codes: 9 year, 10 month, 11 day, …), `calendar` `"gregorian"` | components below the precision are zero (`+2019-00-00T00:00:00Z` at 9); fields in range (`KHG-S006`) | `precision(v′) ≥ precision(v)` and window(v′) ⊆ window(v) (R01 I11) |
| `quantity` | `amount`, `unit` (`"1"` or an entity id), optional `lower` + `upper` | decimal strings `^(\+0|[+-](0\.\d*[1-9]|[1-9]\d*(\.\d*[1-9])?))$`: sign mandatory, no trailing zeros | same unit and [lower′, upper′] ⊆ [lower, upper] (a missing bound means the exact amount) |
| `string` | `value` | NFC | equality only |
| `lang_string` | `value`, `lang` (BCP 47) | NFC value, lower-case tag | equality only |
| `boolean` | `value` | JSON boolean | equality only |
| `iri` | `value` | NFC, no other normalisation | equality only |
| `geo` | `lat`, `lon`, `precision` (decimals), `globe` (entity id) | decimals as above | equality only in v1 |

Units are ids but do not need entity records. Years use astronomical numbering (0000 = 1 BCE).
Julian dates are converted to proleptic Gregorian at import, with the source calendar kept in
evidence. This is P3a's job, and a helper is provided (§14 Q5).

### 2.6 Slot classes

Each role usage declares one slot class [R04 O12]. The class decides how the binding counts.

| Slot | What it is | In `arity` | In `core_key` | In `content_key` | In ⊑ | In P6's hypergraph | Feeds `valid_time` |
|---|---|---|---|---|---|---|---|
| `core` | participants constitutive of the relation | yes | yes | yes | yes | yes | no |
| `qualifier` | circumstances that narrow the fact (monotone [R01 §6.1, SCH §4]) | yes | no | yes | yes | yes | no |
| `time` | the fact's validity bounds (only `time` literals, max 1, named by the relation's time model) | no | no | yes | yes | optional (`slots=` flag) | yes |
| `meta` | statement metadata carried as qualifiers in sources (P1319/P1326 date bounds, P1480 sourcing circumstances…) | no | no | no | no | no | no |

`meta` exists because Wikidata qualifiers are not all roles [R04 M8.2, finding 7]. The probe showed
that `P2241` and `P7452` are allowed on all 17 sampled properties. Counting them would inflate arity
and dominate P6's attribute set. `P2241` and `P7452` themselves become `rank_reason`, not bindings.

### 2.7 Arity (settled)

> **`arity(f)`** = the number of bindings of `f` whose slot is `core` or `qualifier` and whose
> value is an entity, a literal, a fact reference or `somevalue`. Repeated fillers count once per
> binding. `novalue`, `unbound`, `time`-slot and `meta`-slot bindings do not count.

Derived companions, all in `derived`:

- `core_arity`: the same count, restricted to `core`.
- `distinct_fillers`: the number of distinct canonical values among the counted bindings, where
  each `somevalue` counts as distinct. It is R01 D-06's second number: `flies_between(AC, YYZ,
  YYZ)` has arity 3 and 2 distinct fillers.
- `statement_arity` = `arity` + the number of time-slot bindings with a value. It makes counts
  comparable with WD50K-style statistics, which count P580 and P582 as qualifiers [R05 §6].

Why validity bounds are excluded [verified]: an earlier draft of this design counted them. Migrating
the KB's own sample then gave f1 an arity of 5 against the sample's stated 4, because `valid-from`
became a binding (`MIGRATE-E01` in the first migration run). Validity says *when* a fact holds, not
*who takes part*. If it counted, a fact would change arity bin as its dates became known, and P3a's
histogram and every per-arity score would depend on temporal annotation completeness [R01 PF-26,
R05 risk 3]. `statement_arity` keeps the literature comparison available.

### 2.8 Special values: somevalue, novalue, unbound

| | `somevalue` | `novalue` | `unbound` |
|---|---|---|---|
| Reading | ∃x filling the role (unknown) | no filler exists for the role | variable to be bound; no claim |
| Allowed in | fact, rule, goal (usage flag `somevalue`, default true) | fact, rule (usage flag `novalue`, default true) | goal only (`KHG-C005`) |
| Satisfies `min` | yes [R04 M2] | yes (the role is addressed) | in goals, yes |
| Other fillers in the same role | at most one `somevalue` per unordered role (`KHG-S014`); two are logically redundant | must be the only filler (`KHG-S013`) | several, each with a distinct `var` (`KHG-S019`) |
| Counts in arity | yes | no | no (`n_unbound` instead) |
| In content hashes | as the token `{"special":"somevalue"}`. Two facts that differ only in having `somevalue` in the same place are the same proposition (∃x R(a,x) ≡ ∃y R(a,y)) | as its token | goals have no content keys |
| Refines to | any type-correct entity, literal or fact-ref (R01 I12) | only `novalue` | a bound value (in a new goal version) |
| In a key role | makes `key_digest` null: the fact is exempt from collisions | same | goals are exempt |
| HIF node | one node per binding, `_:sv:<32 hex>` | `_:nv:<32 hex>` | `_:var:<32 hex>` |

HIF nodes for special values are *per binding*. Sharing one node would assert that two unknowns
are the same individual.

### 2.9 Nesting: facts about facts

- A `{"fact": id}` value is legal only in a role whose usage lists a `fact` filler, optionally
  restricted to certain relations (`KHG-S005`; this covers R01 V29). The reference is to the fact's
  identity, not a version.
- The reference graph over all non-entity records must be acyclic (`KHG-D008`) [R01 C1-R23]. There
  is no depth limit in C1 (R01 D-11). The gate fixture covers one level of user nesting
  (`f:claim-1` → `f:born-louis14-paris`) and meta references (`m:sup-1` → two facts).
- **`quoted`** is the status of a fact represented but not believed: a claim attributed to someone
  (RDF 1.2's non-asserted triple term) [R01 C1-R44]. A quoted fact needs no evidence of its own; the
  quoting fact carries it. A quoted fact that no fact references gets a lint warning.
- HIF has no nesting (R02 §3). A referenced fact appears as a node `_:ref:<fact id>` with
  `attrs.khg:ref`. The attribute is authoritative; the id is checked against it (`KHG-D005`).
  Nesting is never inferred from equal node and edge ids [R02 rec. 7, case 03].

### 2.10 Direction

The effective direction of a binding is `binding.direction`, else `usage.direction`, else none.
Direction is a property of the role's function in the relation, so it is declared in the schema,
and records normally carry none [R01 C1-R19, D-12]. A `rule` needs a direction on every binding and
must satisfy tail ∩ head = ∅ over values (`KHG-S017`) [R01 C1-R20]. Facts may put one node in
both tail and head, as the HIF paper allows [R02 §3]. Fixture `f:reg-1` does this (TP53 is
regulator/tail and target/head).

### 2.11 Confidence

`{"value": number, "scale": scale-id, "scorer"?: {"name", "version"}}`. The scale is declared in
the schema (`probability` is built in; `bounded` and `ordinal` scales are user-declared). A bare
number is `KHG-C003`; an undeclared scale or an out-of-range value is `KHG-S010` [R01 C1-R49]. There
are two places for it, with different meanings:

- `evidence[].confidence` is the producer's own score for one extraction event (for example an LLM
  score in [0, 10]).
- `fact.confidence` is a derived belief over the evidence, recomputable (INDRA-style, [R04 M6]). It
  is never an identity field, never read from HIF `weight`, and never written to it.

### 2.12 Time

#### 2.12.1 Valid time: carried by bindings, read by the time model

Each relation declares a time model (§3.3). There are three:

- `{"model": "interval", "start": "start_time", "end": "end_time"}`: validity bounds are the
  bindings of those two `time`-slot roles (P580/P582 in Wikidata terms).
- `{"model": "invariant"}`: the fact's truth does not vary with time. This covers event and
  measurement facts whose time is *content*: `award_received … point_in_time 1921`, and
  `population … point_in_time 2019`, where the date is a (key) qualifier.
- `{"model": "unstated"}` (the default): the relation carries no validity.

From these the canonicaliser derives `derived.valid_time`:

| `kind` | When | Interval (before precision) |
|---|---|---|
| `period` | start and end bound to time literals | [start, end) |
| `since` | start only | [start, +∞) presumed ongoing |
| `until` | end only | (−∞, end) |
| `unstated` | neither bound (interval model), or the `unstated` model | presumed (−∞, +∞) for conflict checks; empty known interval for `definite` queries (§2.12.2) |
| `invariant` | invariant model | (−∞, +∞) |

This satisfies both "valid time on the hyperedge with an explicit conjunction" [R01 C1-R46, VITA's
Since/Until/Period/Invariant] and "time as a qualifier stays representable, with a deterministic
mapping" [R01 C1-R47]. There is one source of truth, the bindings. Evidence can cite a date by `bid`.
Extraction scoring treats dates like any other role.

A `somevalue` or `novalue` bound, and an absent bound, are all treated as unbounded in that
direction for interval arithmetic. P3a carries Wikidata's "start time: unknown value" as `somevalue`.
Only the interval reading ignores the difference; the content keeps it.

#### 2.12.2 Precision windows and the presumed interval (the core temporal semantics)

A time literal at precision p denotes a window [lo, hi): the instants it may name. For example,
`+2021-00-00T00:00:00Z/9` is [2021-01-01, 2022-01-01) and `+2021-06-01/11` is [2021-06-01,
2021-06-02). For a fact, write the start window as [s_lo, s_hi) and the end window as [e_lo, e_hi),
with unbounded ends at ∓∞. Then:

- **possible validity** = [s_lo, e_hi): instants at which the fact may hold;
- **definite validity** = [s_hi, e_lo): instants at which it certainly holds;
- two facts **definitely overlap** iff max(s_hi¹, s_hi²) < min(e_lo¹, e_lo²), and **possibly
  overlap** iff the same holds with s_lo and e_hi;
- a fact is malformed iff its possible validity is empty (s_lo ≥ e_hi, `KHG-S009`).

**Two readings of an absent bound, each named.** *Conflict checks* (keys, negation) use the
**presumed** interval above: absent, `somevalue` and `novalue` bounds are unbounded, so an `unstated`
fact is presumed to hold always. Conflict detection is conservative, so two undated claims of the same
key are a dispute (X3). *Queries* in `definite` mode use the **known** interval: the presumed one,
except that an `unstated` fact has an empty known interval. A stated start with no end is still
presumed ongoing, the standard bitemporal default (t_invalid = +∞), so "who is CEO now?" returns the
CEO appointed in 2026. But nothing is known about *when* an undated fact held. `possible` mode
returns undated facts. `invariant` facts hold at every instant under both readings. [verified,
C2-S034; and the prototype store refused to hold an undated `position_held` fact beside a dated one on
the same key, which is X3 at write time.]

**Why this matters [verified, case X1].** CEO X until 2021 (year precision) and CEO Y since 2021
(year): the possible intervals overlap during 2021, but the definite ones do not. Under this rule
it is a consistent succession, not a conflict. Wikidata is full of year-precision handovers, so
without this rule every one of them would become a conflict or need an arbitrary convention.

#### 2.12.3 Transaction time

Each stored version carries `recorded_at`, assigned by the store. It is strictly increasing per
store, with ties broken by a transaction sequence number. `get(id, as_at=τ)` returns the version
with the greatest `recorded_at ≤ τ`. Because versions are immutable and `tx_to` is derived, as-at
reconstruction is exact. Graphiti's in-place `MERGE … SET` shows what goes wrong otherwise
[R04 M4].

#### 2.12.4 Query semantics (as-of × as-at)

A read takes `valid_at` (an instant, or `None` for no valid-time filter) with `valid_mode ∈
{definite, possible}` (default `definite`), and `as_at` (`None` = now). The two compose: first
select the versions current at `as_at`, then filter by `valid_at`. The defaults are
`valid_at=None` and `as_at=now`, documented in C2 (§6.2).

#### 2.12.5 Wikidata time qualifiers

| Wikidata | C1 | Note |
|---|---|---|
| P580 start time / P582 end time | `time`-slot roles named by the interval time model | `somevalue` and `novalue` allowed |
| P585 point in time | `qualifier` role `point_in_time`, typically on `invariant` relations (event and measurement facts), often a key role (`population`) | whether a property's P585 is content or validity is a per-property decision P3a declares in the schema; v1 has no instant time model |
| P1319 earliest date, P1326 latest date, P8554, P8555, P12506 | `meta`-slot roles in v1 (kept, not interpreted) | interval uncertainty bounds are v1.1 [R04 M4] |
| P1534 end cause | `qualifier` role `end_cause` | |
| P2241 reason for deprecated rank / P7452 reason for preferred rank | `rank_reason` | |
| P1480 sourcing circumstances, P5102 nature of statement | `meta`-slot roles | |
| P1810 subject named as, P1932 object named as | evidence quote selector | [R04 M6] |

### 2.13 Lifecycle: four axes, one transition table

| Axis | Field | Values | Changed by |
|---|---|---|---|
| record status | `status` (+ `status_ref`) | fact/rule: `asserted`, `disputed`, `superseded`, `retracted`, `quoted` (+ `candidate` in the queue only); goal: `open`, `satisfied`, `abandoned`; meta: `asserted`, `retracted` | lifecycle records (meta) and queue actions |
| world validity | the time-slot bindings → `derived.valid_time` | intervals as in §2.12 | a new, refining version (adding `end_time` closes a since-interval) |
| editorial rank | `rank`, `rank_reason` | `preferred`, `normal`, `deprecated` | curator action (new version) |
| visibility | `visibility` | `visible`, `suppressed` | governance action (new version) |

**The rule F7 makes precise.** A fact that stopped being true keeps `status: asserted` and gains an
`end_time` binding, optionally with an `end_cause` qualifier. `superseded` means *this record is no
longer the store's account*, and always has a `status_ref` to a `khg:supersedes` record. This
separates stale answers from correct historical answers in the memory scorer (V_old kinds `expired`
vs `retracted`, §9.3) [R04 M5, risk 2].

**Status transitions** (enforced by the store on each new version, `KHG-D014`; [verified]
`proto_store.ALLOWED`):

| Kind | From → to | Requires |
|---|---|---|
| fact/rule | (new) → `asserted` \| `disputed` \| `quoted` | valid record; `disputed` needs a `khg:disputes` record in the same batch |
| fact/rule | `asserted` → `disputed` | `khg:disputes` record naming it |
| fact/rule | `asserted` \| `disputed` → `superseded` | `khg:supersedes` record naming it as `khg:superseded` |
| fact/rule | `asserted` \| `disputed` \| `quoted` → `retracted` | `khg:retracts` record |
| fact/rule | `disputed` → `asserted` | the disputes record retracted, or a curator resolution record |
| fact/rule | `quoted` → `asserted` | independent evidence (endorsement) |
| fact/rule | `superseded` \| `retracted` → `asserted` | the meta record that caused it is itself retracted (undo) |
| fact/rule | same status → same status | content refinement or evidence addition (§2.16) |
| goal | (new) → `open`; `open` → `open` (binding events); `open` → `satisfied` \| `abandoned` | `satisfied` needs a `khg:fulfils` record; `abandoned` needs `goal.closed_reason` |
| meta | (new) → `asserted` → `retracted` | retracting a meta record undoes its effect; the planner's undo batch carries the reverse status transitions of the facts it named |
| queue | `candidate` never enters a store (`KHG-D017`) | F9 |

**Meta relations** (built in, directions declared so meta edges are drawable):

| Relation | Roles | `meta.reason` enum | Constraints |
|---|---|---|---|
| `khg:supersedes` | `khg:superseding` (tail, 1..n), `khg:superseded` (head, 1..n) | `correction`, `duplicate`, `conflation`, `schema_migration`, `other` | `correction`: same relation, and the same `key_digest` if keyed (`KHG-D011`). `duplicate`: the superseding fact ⊑ each superseded one. `conflation`: 1 → n. The supersession graph must be acyclic (`KHG-D012`). Superseded facts must have status `superseded` and point back (`KHG-D010`) |
| `khg:retracts` | `khg:retracted` (head, 1..n) | `withdrawn`, `unsupported`, `other` | targets have status `retracted` |
| `khg:disputes` | `khg:disputed` (head, 2..n) | `key_conflict`, `negation_conflict`, `curator`, `other` | targets have status `disputed` |
| `khg:fulfils` | `khg:fulfilling` (tail, fact 1), `khg:goal` (head, goal 1) | `bound`, `matched_existing` | the fact ⊑ the goal pattern (unbound matches any type-correct value) |

The reason codes follow Wikidata's `P2241` reasons and nanopublication `npx:supersedes` and
`npx:retracts` [R04 M5].

### 2.14 Evidence (F11)

```json
{"id": "e1", "type": "extracted", "mode": "automatic",
 "source": {"doc_id": "doc:route-note", "doc_sha256": "sha256:159bbe0d06e3ce286c6796f8aad3fa7eb52d01132423f10224915b31e9a104ca"},
 "selectors": [{"type": "quote", "exact": "Toronto → Montréal → Toronto", "prefix": "anada flies ", "suffix": " every day."},
               {"type": "position", "start": 19, "end": 47}],
 "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"},
 "supports": ["b1", "b2", "b3", "b4"],
 "event_hash": "sha256:7b645e47a4a25bd764f60cebd029975b9cf78334498e0014f5f6f05b3e57b062"}
```

This example is taken from the canonical fixture [verified]. The source text begins with 🛫
(U+1F6EB), so offset 19 is in code points; in UTF-16 the same position is 20.

| Field | Type | Rule |
|---|---|---|
| `id` | short id | unique within the record, across versions |
| `type` | `curated` \| `imported` \| `extracted` \| `inferred` \| `agent_bound` | mapped to ECO: `curated` → ECO:0000218 manual assertion; `extracted` and `inferred` → ECO:0000203 automatic; `imported` → ECO:0000313 [R04 M6] |
| `mode` | `automatic` \| `manual` \| `semi_automatic` | EARL and ECO assertion method |
| `source` | `{doc_id, doc_sha256?, doc_version?, url?, title?, retrieved_at?, license?}` | `doc_sha256` = SHA-256 of the UTF-8 bytes of the NFC text |
| `selectors` | quote `{exact, prefix?, suffix?}` and position `{start, end}` | Unicode code points, half-open, over NFC text [R04 O8]; `start < end` (`KHG-S021`); if the text is supplied, `exact == text[start:end]` |
| `activity` | `{agent, agent_version?, model?, model_version?, run_id?, prompt_id?, skill_id?, params?}` | required for `extracted` (`KHG-C007`) |
| `inference` | `{rule, from: [ids]}` | required for `inferred` (e.g. `close_older` closures) |
| `supports` | list of bids | canonical form is explicit (the canonicaliser fills in all bids when absent); unknown bid is `KHG-S022` |
| `confidence` | as §2.11 | the producer's score |
| `epistemics` | `{negated?, hypothesis?}` | negated evidence does not count toward `KHG-S011` |
| `reference` | list of `{role, value}` | Wikidata-style reference snaks |
| `recorded_at`, `event_hash` | timestamp; sha256 | `event_hash` is derived (§2.15) |

**Evidence records are immutable and append-only [verified, scenario C2-S012].** A later version
must carry every earlier evidence record byte-for-byte (`KHG-D013`). When a refinement adds a
binding, the new binding gets new evidence; old evidence is never re-pointed. So "what did source X
support?" has one answer across versions.

### 2.15 The four identifiers (F6)

| Identifier | Job | Definition | Stable across |
|---|---|---|---|
| `id` | identity of the fact through its versions | opaque; minted by the producer or store; never derived from text or members [R01 C1-R01] | all versions |
| `content_key` / `core_key` | dedup, leak checks, P9 run-to-run agreement | `digest("khg-content-key/1", {relation, bindings: sorted [role, position, canonical value]})` over non-meta bindings; `core_key` uses core bindings only (domain `khg-core-key/1`) | content (changes when a refinement changes content) |
| `key_digest` | collision and supersession on a declared key | `digest("khg-key-digest/1", {relation, bindings of the key roles})`; `null` if a key role is absent or bound to a special value (an incomplete key cannot identify; LinkML `consider_nulls_inequal`) | versions (it may change only from `null` to a value) |
| `event_hash` | one extraction event | `digest("khg-event/1", {content_key, doc: doc_sha256 or doc_id, selectors, activity minus run_id/seed/params})` | the event: re-extracting the same passage with the same tool and model gives the same hash, whatever the run [R01 C1-R03] |

`digest(domain, payload)` = `"sha256:" + hex(SHA-256(domain + "\n" + canonical_json(payload)))`,
where `canonical_json` gives NFC strings, sorted keys, no whitespace, UTF-8, and no floats (floats
are rejected in hashed payloads; literal numbers are decimal strings). The domain strings carry their
own version (`/1`) and change only with a major format version.

`content_key` and `core_key` are the two granularities of F6's "content/core-key hash". R05 needs
both: stability "on both the full content key and the core key" [R05 §2.2.2].

### 2.16 The refinement order ⊑ and the version identity rule

**Value refinement** v′ ⊑ v: canonical equality; or v = `somevalue` and v′ is a type-correct
entity, literal or fact-ref; or both are `time` literals with precision(v′) ≥ precision(v) and
window(v′) ⊆ window(v); or both are `quantity` literals in the same unit with bounds(v′) ⊆ bounds(v).

**Fact refinement** f′ ⊑ f ("f′ says everything f says"): same relation, and for every role ρ:

- if f has `novalue` for ρ, then f′ has `novalue` for ρ (and nothing else there); f′ may not
  introduce `novalue` where f has fillers;
- if ρ is `ordered`, every binding of f at position k is matched by a binding of f′ at position k
  with v′ ⊑ v; if ρ is `complete`, both have the same positions;
- otherwise there is an injective matching from f's ρ-bindings to f′'s ρ-bindings with v′ ⊑ v
  (bipartite matching); if ρ is `complete`, the counts are equal;
- f′ may bind roles that f leaves unbound, the monotone narrowing of qualifier semantics
  [Xiong et al. via R05 §3.1.2; SCH §4].

`meta` bindings are ignored. Time bindings are compared binding-wise, not by interval containment:
"since 1650" does not refine "since 1643"; that would be a disagreement about the start.
`duplicate` ≡ f′ ⊑ f and f ⊑ f′ ⟺ equal `content_key` [verified, I5 and I8].

**`complete` (a role-usage flag, requires `min ≥ 1`).** It says the bindings list *all* fillers
(closed reading), so adding a filler is not a refinement. Without it, a repeated role reads
"includes" (open reading), as Wikidata qualifiers do. The flag decides R01 case 4a
[verified, C4a-u vs C4a-o]. The linter warns on a repeated core role in a temporally keyed relation
without `complete` (`L-Q-004`).

**Version identity rule (the store enforces it, `KHG-D013`) [verified, S-ID-01, C2-S012].** A new
version of id X must keep X's relation and satisfy content(new) ⊑ content(old), with evidence
append-only. Status, rank, visibility and confidence may change per §2.13. Superseded and retracted
facts are content-frozen. So a version chain is a chain of increasingly specific accounts of *one*
fact. Anything else is a new fact plus a lifecycle record. Goals are the exception: binding an
`unbound` slot keeps the `bid` and adds `agent_bound` evidence, and un-binding needs a reason.

### 2.17 Keys and collision policies

```json
{"key": {"roles": ["position"], "temporal": true, "on_collision": "close_older"}}
```

- `roles`: a set of core or qualifier roles of the relation (not `time` or `meta`, `KHG-M003`).
  These are the *identifying* qualifiers, Wikidata's separators [R04 M3.3].
- `temporal: true`: at most one fact with a given `key_digest` is valid at any instant (SQL:2011
  `WITHOUT OVERLAPS`), tested by **definite overlap** (§2.12.2). `temporal: false`: at most one,
  whatever the time. A temporal key requires an interval time model (`KHG-M011`).
- **Key invariant** (checked on every store write, `KHG-D016`; [verified] MC88, S-KEY-03). For each
  key digest k and each instant t, let M_t be the set of facts with `status: asserted`,
  `rank ≠ deprecated`, `key_digest = k` and definite validity containing t (all such facts, for
  non-temporal keys). Then |M_t| ≤ 1, or M_t holds exactly one `preferred` fact. The second branch
  is Wikidata's single-best-value semantics: ranked alternatives are not conflicts [R04 M3.3].
  Checking the instants where some fact's definite validity starts is sufficient.
- `on_collision`: what the **identity planner** (§2.18) does when an incoming fact would break the
  invariant. The store never applies a policy; it only refuses states that break the invariant.

| Policy | Meaning | Resulting write | Precedent |
|---|---|---|---|
| `close_older` | world change: the earlier state ended when the later began | if both starts are known values, the older start is definitely earlier, and the older fact has no end: a new version of the older fact adds `end_time` := the newer fact's start (evidence type `inferred`, `inference: {rule: "close_older", from: [newer id]}`), and the newer fact is inserted. Otherwise: `dispute` | Graphiti's invalidation, without its in-place overwrite [R04 M4]; Wikidata "outdated → end time" |
| `supersede` | belief revision, last writer wins | `khg:supersedes` (reason `correction`) from the newer (by transaction order) to the older; older → `superseded` | TOKI last-writer-wins [TMP §2]; nanopub `supersedes` |
| `dispute` (default) | both claims kept, neither endorsed | `khg:disputes` (reason `key_conflict`); both → `disputed` | Wikidata advisory violations |
| `reject` | the write is refused | nothing written; `KHG-D016` | SQL constraint |

The default is `dispute` in the planner, and C2 always rejects a state that breaks the invariant.
Together this is R04 O3's "flag in the queue, reject in the store", with the policy made explicit.

### 2.18 The identity classifier (normative)

`relate(n, e, schema) → relation` for an incoming fact n and an existing fact e, both of kind
fact or rule (implemented [verified] as `khg_proto.relate`):

1. different relations → **unrelated**;
2. n ⊑ e and e ⊑ n → **duplicate**;
3. n ⊑ e → **refines** (n is more specific);
4. e ⊑ n → **generalises**;
5. **negation_conflict**: one has `novalue` for ρ, the other binds ρ (including `somevalue`), the
   other's non-ρ, non-time bindings refine the `novalue` fact's, and their validities definitely
   overlap;
6. key declared, both `key_digest`s equal and non-null, and (key non-temporal, or validities
   definitely overlap) → **key_conflict**;
7. key declared, digests equal, no definite overlap → **key_timeline** (distinct facts on one key's
   timeline; a possible overlap alone is an info finding);
8. otherwise → **distinct**.

**Planning against a store** (`identity.plan(candidate, store, schema) → WritePlan`), deterministic:

- Compare n with every stored fact of the same relation that is `asserted`, `disputed` or `quoted`
  and shares `core_key`, `key_digest`, or a candidate refinement match. The store finds these
  through `find` and `by_key`.
- **Merge target.** Exactly one `duplicate` target: append n's evidence to it (a new version with the
  same content). Else exactly one `refines` target: its new version takes n's content, keeps all old
  evidence, and adds n's. Else exactly one `generalises` target: append n's evidence, with `supports`
  mapped to the target's bids. **Two or more targets of the same class are ambiguous**, and the
  outcome is `needs_review`. Example [verified]: an undated marriage against two dated marriages of
  the same couple.
- **Conflicts** are computed on the post-merge state, then resolved by the key's policy or, for
  negation, by `dispute`. Refinement is checked before keys, so a report that closes a tenure refines
  that tenure and does not collide with it.
- If n duplicates or refines a `superseded` or `retracted` fact, the outcome is `needs_review`
  (`L-I-007`). A stale re-extraction must not revive a revised belief. If n matches a `quoted` fact,
  that fact moves to `asserted` with n's evidence.
- Nothing else merges. A merge is always an explicit, logged action with before and after, never a
  key collision [R01 C3-R10; SKL §8].

The store state depends on insertion order when merges happen (the surviving id is the
first stored). The plan is deterministic for each order. The resulting order effect is exactly
what P9 measures (Δ_order, [R05 §2.2.2 S-M7]); content keys are unaffected.

### 2.19 Classification of every R01 identity case [verified: `run_identity.py`]

Notation as in R01 §6. Rows with a computed relation were run through `relate`/`resolve` (34 pairs plus 3 policy variants). The rows for counter-case (i)'s invalid form, 4c, I9 (checked as a fixture), I10, I13, I15 and I16 follow from the same rules but were not run as pairs. The schema column is the declaration that decides the case. Change it and
the answer changes, deterministically.

| Case | Deciding declaration | Existing e | Incoming n | Relation | Outcome under the contract |
|---|---|---|---|---|---|
| **R01 §6.1 case 1 refinement** | `position_held`, interval time model, key {position} temporal | holder LouisXIV, position KingOfFrance (unstated validity) | same + start_time 1643-05-14, end_time 1715-09-01 | refines | e gets a new version with n's bindings and both evidence records (doc1 supports holder and position only). Arity 2 → 2; `valid_time` unstated → period |
| case 1, other order | same | the dated report | the undated report | generalises | n's evidence is appended to e with `supports` = holder, position |
| case 1 counter-case (i) | `treats`: population is a **required core** role | treats(metformin, T2DM) without population | n/a | n/a | invalid as an asserted fact (`KHG-S003`); allowed as a candidate (lint `incomplete`); may be asserted as population = `somevalue` |
| … continued | same | treats(metformin, T2DM, population: somevalue) | …, population: adults | refines | a new version of e (`core_key` changes, id kept) |
| counter-case (ii) | population is a **qualifier** | treats(metformin, T2DM) | + population adults | refines | a new version of e |
| **§6.2 case 2a** | `population`, invariant, key {place, point_in_time} non-temporal | CityX, n1, 2019 | CityX, n2, 2023 | distinct | insert n |
| case 2a with naive key {place} | same, key {place} | same | same | key_conflict | dispute (both `disputed`): the wrong key makes the wrong answer, deterministically |
| **case 2b** | `defeated`, key {event} | winner P, loser Q, event E1 | winner Q, loser P, event E2 | distinct | insert n (roles are in the content key; R01 I7) |
| case 2b without events | `defeated` | defeated(P, Q) | defeated(Q, P) | distinct | insert n |
| **case 2c** | `spouse`, no key | P, Q, [1990, 1995) | P, Q, [2001, ∞) | distinct | insert n. One fact per maximal validity period (R01 D-07 settled): a fact never holds two disjoint periods |
| case 2c keyed | `spouse` key {person} temporal | same | same | key_timeline | distinct facts on one key timeline |
| **§6.3 case 3a** | `chief_executive` key {organisation} temporal `close_older` | O, X, since 2019-01-01 | O, Y, since 2021-06-01 | key_conflict | succession: e gains end_time 2021-06-01 (`inferred` evidence), stays `asserted`; n inserted; **no supersession** (F7) |
| case 3a, policy `supersede` | same, `on_collision: supersede` | same | same | key_conflict | `khg:supersedes` (reason `correction`); e → `superseded` |
| case 3a, policy `dispute` | `on_collision: dispute` | same | same | key_conflict | `khg:disputes`; both `disputed` |
| case 3a, policy `reject` | `on_collision: reject` | same | same | key_conflict | put refused, `KHG-D016` |
| **case 3b** | as 3a | O, X, since 2019-01-01 | O, Y, since 2019-01-01 | key_conflict | dispute: `close_older` does not apply (starts not definitely ordered) |
| **case 3c** | `catalysed_by` (no key needed) | reaction R, catalyst `novalue` | R, catalyst C | negation_conflict | dispute. Arity 1 vs 2: `novalue` does not count |
| **§6.4 case 4a** (option ii) | `committee`, member `complete`, key {body} temporal `close_older` | C, m1..m3, since 2024-01-01 | C, m1..m4, since 2025-03-01 | key_conflict | succession: e closed at 2025-03-01, n inserted (n − 1 bindings copied; option iii, per-binding validity, is v1.1) |
| case 4a, undated, complete | same | C, m1..m3 | C, m1..m4 | key_conflict | dispute (a closed composition changed and the time is unknown) |
| case 4a, undated, **open** member role | member not `complete` | C, m1..m3 | C, m1..m4 | refines | e refined to include m4. The open reading ("includes") makes this right; the lint warns about the ambiguity (`L-Q-004`) |
| **case 4b** | `founding` (open qualifiers) | founder Musk, organisation SpaceX | + point_in_time 2002, location Hawthorne | refines | explicit merge action in the log with both evidence records; never a key collision |
| **case 4c** (erasure) | n/a | n/a | n/a | n/a | not classified in v1. `visibility: suppressed` is representable; tombstoned bindings are v1.1 [R01 D-17, open question 10.6] |
| **I5** paraphrase | any | rel(a: X, b: Y) from sentence 1 | same from sentence 2 | duplicate | one fact, two evidence records (ids are never text) |
| **I6** provenance as a role | a (bad) schema with a `source` qualifier | treats(…, source: doc1) | treats(…, source: doc2) | distinct | as declared. The schema lint flags provenance-like roles (`L-Q-003`); under a correct schema the pair is a duplicate |
| **I7** member-set key | any | rel(a: X, b: Y) | rel(a: Y, b: X) | distinct | roles are part of identity |
| **I8** permuted interchangeable role | `co_authors`, author unordered | A, B, C | C, A, B | duplicate | canonical sort makes the content keys equal |
| **I9** one node in two roles | `flies_between` with must_differ (warning) | n/a | AC, YYZ, YYZ | n/a | valid; arity 3, `distinct_fillers` 2; lint `KHG-S024` warning [verified in the undirected fixture] |
| **I10** entity merge | any | facts on Q1 and on Q2 | after Q2 `redirect_to` Q1 | duplicate | value equality is modulo redirects; merge = `khg:supersedes` (reason `duplicate`), evidence kept per binding; the entity rewrite is a logged action |
| **I11** date precision | `award_received`, invariant | point_in_time 1921 (year) | 1921-05-02 (day) | refines | new version with the day |
| I11, two different days | same | 1921-05-02 | 1921-06-02 | distinct | without a key they are two receipts; with key {recipient, award} a key_conflict |
| **I12** somevalue then a value | `spouse` | P, spouse `somevalue` | P, Q | refines | the witness replaces somevalue; the `bid` is kept |
| **I13** RDF 1.2 reifier occurrences | any | an imported reifier occurrence | another reifier of the same triple term | duplicate | one fact per content, one evidence record per occurrence |
| **I14** same main triple, other qualifiers | `award_received`, no key | E, N, 1921 | E, N, 1922 | distinct | distinct facts, same `core_key`; P3a keeps them in one split group |
| **I15** projection identity | n/a | n/a | n/a | n/a | identity is defined on C1; each projection records its mapping |
| **I16** RDF blank-node instances | any | identical content | identical content | duplicate | keyed by content on import |
| X1 year-precision handover | `chief_executive` | X [2019, 2021) by year | Y since 2021 by year | key_timeline | consistent: only a possible overlap (info) |
| X2 older already ended, overlapping | same | X [2019-01-01, 2023-01-01) | Y since 2021-06-01 | key_conflict | dispute (conflicting reports of when X ended) |
| X3 two undated claims | same | X (no dates) | Y (no dates) | key_conflict | dispute (presumed always valid, so they overlap) |
| X4 backfill | same | Y since 2021-06-01 | X since 2019-01-01 (arrives later) | key_conflict | succession: the *incoming* fact is closed at 2021-06-01 |
| X5 novalue vs somevalue | `catalysed_by` | catalyst `novalue` | catalyst `somevalue` | negation_conflict | dispute |
| X6 ordered complete route, a stop appended | `route`, stop `complete` | [YYZ, YUL] | [YYZ, YUL, YYZ] | distinct | a different route |
| X7 ordered open route, a stop appended | stop not `complete` | [YYZ, YUL] | [YYZ, YUL, YYZ] | refines | new version |
| X8 stops reordered | any | [YYZ, YUL] | [YUL, YYZ] | distinct | order is content |
| X9 undated marriage vs one dated marriage | `spouse` | P, Q [1990, 1995) | P, Q (no dates) | generalises | evidence appended; with two dated marriages the outcome is `needs_review` (ambiguous) |

P7's gate ("every case … is classified as specified") becomes an executable table: these rows are
the seed of `tests/identity/cases.json`, and P7 extends the table.

### 2.20 Goals (for P11)

```json
{"kind": "goal", "id": "g:who-1774", "relation": "position_held", "status": "open",
 "bindings": [{"bid": "b1", "role": "holder", "value": {"unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}},
              {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}},
              {"bid": "b3", "role": "start_time", "value": {"literal": {"datatype": "time", "time": "+1774-05-10T00:00:00Z", "precision": 11}}}],
 "goal": {"brief": "Who became King of France on 10 May 1774?", "owner": "agent:history-desk"}}
```

- A goal is a question, not a claim. It has no content keys and is exempt from keys and from default
  reads (`kinds={"fact"}`).
- Every *required* role of the relation must appear, bound or `unbound` (`KHG-S018`). "The unbound
  roles" is then a well-defined list, which P11's stall report needs. Variables are distinct within
  a goal (`KHG-S019`); variables shared across goals are v1.1.
- Binding a slot is a new goal version: same `bid`, new value, plus an `agent_bound` evidence record
  whose `supports` names that `bid` [R01 C2-R14].
- When every slot is bound, the goal's content is planned like any candidate (§2.18). It may match an
  existing fact. The goal then moves to `satisfied` via `khg:fulfils` (reason `bound` or
  `matched_existing`).
- In HIF each unbound slot is an incidence to a `_:var:` node carrying `khg:unbound`. A goal with no
  bound roles is therefore still a non-empty edge, which settles R01 D-18 and open question 5 of
  R01 §11. TypeDB cannot store a relation with no role players, so P1 either maps placeholders or
  lacks the `goals` capability (§6.7).

### 2.21 A complete canonical record [verified]

`f:king-14` from the canonical fixture, including the derived block (real hashes):

```json
{"kind": "fact", "id": "f:king-14", "relation": "position_held", "status": "asserted", "rank": "normal", "visibility": "visible",
 "bindings": [
  {"bid": "b4", "role": "end_time", "value": {"literal": {"datatype": "time", "time": "+1715-09-01T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
  {"bid": "b1", "role": "holder", "value": {"entity": "ex:LouisXIV"}},
  {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}},
  {"bid": "b5", "role": "replaces", "value": {"entity": "ex:LouisXIII"}},
  {"bid": "b3", "role": "start_time", "value": {"literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}],
 "evidence": [
  {"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:regnal-list"}, "supports": ["b1", "b2", "b3", "b4"]},
  {"id": "e2", "type": "extracted", "mode": "automatic",
   "source": {"doc_id": "doc:louis-bio", "doc_sha256": "sha256:56940b729460cb9a75d5d63ab1f907a502fef80530b4aabff2cd8e9c28a44b2f"},
   "selectors": [{"type": "quote", "exact": "Louis XIV succeeded his father Louis XIII", "prefix": "", "suffix": " as King of "},
                 {"type": "position", "start": 0, "end": 41}],
   "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"},
   "supports": ["b1", "b5"],
   "event_hash": "sha256:852ea9ca3abcc722e33e903dcdab88f5895cef077241fdf339ee1db0aeb55524"}],
 "derived": {"arity": 3, "core_arity": 2, "statement_arity": 5, "distinct_fillers": 3,
  "content_key": "sha256:187ca682671fd4daaa6944fced4e05b7b9198b6bf0b4c29e6bb402d61bf9ecd2",
  "core_key": "sha256:5779b98f13640fbf96488b9834c5ce7e10f02902541882a23c2d43f84f93e916",
  "key_digest": "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96",
  "valid_time": {"kind": "period",
   "start": {"literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}},
   "end": {"literal": {"datatype": "time", "time": "+1715-09-01T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}}}
```

The two evidence records support different bindings: the regnal list supports the tenure, and the
biography sentence supports only the holder and the `replaces` qualifier. This is the gate's
"evidence on a binding" [R01 D-20].

---

## 3. The relation-type schema language (`khg-schema/1.0.0`)

A schema document is JSON, validated by a draft-07 meta-schema (`khg-schema-1.0.0.schema.json`)
and then by Python semantic checks (`KHG-M…`). Its concepts mirror LinkML: global slots with
per-class `slot_usage`, and `unique_keys`. A LinkML export is therefore mechanical. The language adds
what LinkML, SHACL and TypeQL lack: temporal keys with a collision policy, slot classes,
co-occurrence constraints and a semver id [R04 O10, M8.3].

### 3.1 Document fields

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `khg_schema` | `"khg-schema/1.0.0"` | yes | language version |
| `id`, `version` | vocab id; semver | yes | the schema's identity; records cite `id/version` |
| `label`, `description` | string | no | |
| `entity_types` | `[{id, label?, parents?, mappings?}]` | no | a type DAG; `Thing` is the built-in root. An entity matches type T if T is among its types or their ancestors |
| `confidence_scales` | `[{id, kind: probability\|bounded\|ordinal, min?, max?, levels?}]` | no | `probability` [0, 1] is built in |
| `roles` | `[{id, label?, description?, aliases?, mappings?}]` | yes | the **global** role vocabulary (F4). `mappings` example: `{"wikidata": "P580"}` |
| `relations` | `[relation]` | yes | relation types |

Datatypes are the seven built-in ones of §2.5; user datatypes are v1.1. User vocabularies must not
use the `khg:` namespace (`KHG-M008`), which is reserved for the meta relations and their roles.

### 3.2 Relation fields and role usages

| Relation field | Type | Meaning |
|---|---|---|
| `id` | vocab id | relation type id |
| `kind` | `fact` \| `rule` | default `fact` |
| `roles` | `[usage]`, ≥ 1 (`KHG-M001`) | per-relation usage of global roles; each role at most once (`KHG-M002`); each must be in the vocabulary (`KHG-M009`) |
| `primary` | `{subject, object}` | optional, derived triple view (both core roles, `KHG-M012`) [R01 C1-R18] |
| `time` | `{model: interval, start, end}` \| `{model: invariant}` \| `{model: unstated}` | the time model (§2.12); `start`/`end` must be `time`-slot usages (`KHG-M007`) |
| `key` | `{roles, temporal, on_collision}` | §2.17 (`KHG-M003`, `KHG-M011`) |
| `constraints` | `[{type: must_differ\|must_agree\|excludes\|at_least_one_of, roles, severity?}` \| `{type: requires, if, then, severity?}]` | co-occurrence constraints (FrameNet CoreSet/Requires/Excludes, SHACL pair constraints [R04 M1.2]); `severity` is `violation` (default) or `warning` (Wikidata's mandatory/suggestion) |
| `mappings`, `aliases`, `label`, `description` | | external ids (for example the Wikidata property), raw phrases for P9 [R01 C1-R31] |

| Usage field | Type | Meaning |
|---|---|---|
| `role` | role id | the global role |
| `slot` | `core` \| `qualifier` \| `time` \| `meta` | §2.6. A `time` usage must have `max: 1` and one `time` literal filler (meta-schema) |
| `fillers` | `[{entity: [types]} \| {literal: datatype, precision_min?, units?} \| {fact: [relations]}]`, ≥ 1 | a disjunction of allowed filler kinds (VerbNet `logic="or"`); an empty type list means any entity; `{fact: []}` means any fact (nesting) |
| `min`, `max` | int ≥ 0; int ≥ 1 or `null` | within-fact multiplicity (TypeDB `@card` on `relates`) [R04 M1.3]; `max < min` is `KHG-M010`. Across-fact cardinality is the key's job |
| `ordered` | bool | bindings carry positions 1..n |
| `complete` | bool (requires `min ≥ 1`, `KHG-M014`) | closed reading of the filler set (§2.16) |
| `direction` | `tail` \| `head` | default direction of the role's bindings |
| `somevalue`, `novalue` | bool (default `true`) | whether special values are allowed |
| `label`, `aliases` | | local naming, for example "conferring body" (LinkML `slot_usage`) |

**Symmetric and interchangeable roles.** A symmetric relation has one role with `max > 1`, unordered:
`married(spouse: min 2, max 2, complete)`. Identity is then permutation-invariant by construction,
since bindings are sorted canonically (R01 I8 [verified]). Relations written with numbered pairs
(`spouse_1`/`spouse_2`, FrameNet `Entity_1`/`Entity_2`) need a fold rule, which is v1.1 [R04 M1.5].

### 3.3 A complete example [verified]

An excerpt of the gate schema, valid as a standalone document against `khg-schema/1.0.0` and its
semantic checks. It has five relation types: keys (`position_held`, `born_in`), a symmetric role
(`married`), an ordered complete role (`flight_route`) and nesting (`claims` → `born_in`).

```json
{
 "khg_schema": "khg-schema/1.0.0", "id": "p2-gate-excerpt", "version": "1.0.0",
 "entity_types": [{"id": "Agent"}, {"id": "Person", "parents": ["Agent"]}, {"id": "Organisation", "parents": ["Agent"]},
                  {"id": "Position"}, {"id": "Place"}, {"id": "Airline"}, {"id": "Airport"}],
 "confidence_scales": [{"id": "llm-0-10", "kind": "bounded", "min": 0, "max": 10}],
 "roles": [{"id": "holder"}, {"id": "position"}, {"id": "replaces"}, {"id": "spouse"}, {"id": "carrier"}, {"id": "stop"},
           {"id": "person"}, {"id": "birthplace"}, {"id": "claimant"}, {"id": "claim"},
           {"id": "start_time", "label": "start time", "mappings": {"wikidata": "P580"}},
           {"id": "end_time", "label": "end time", "mappings": {"wikidata": "P582"}},
           {"id": "point_in_time", "label": "point in time", "mappings": {"wikidata": "P585"}}],
 "relations": [
  {"id": "position_held", "mappings": {"wikidata": "P39"}, "primary": {"subject": "holder", "object": "position"},
   "time": {"model": "interval", "start": "start_time", "end": "end_time"},
   "key": {"roles": ["position"], "temporal": true, "on_collision": "close_older"},
   "roles": [
    {"role": "holder", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "position", "slot": "core", "fillers": [{"entity": ["Position"]}], "min": 1, "max": 1, "direction": "head"},
    {"role": "start_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"},
    {"role": "end_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"},
    {"role": "replaces", "slot": "qualifier", "fillers": [{"entity": ["Person"]}], "min": 0, "max": null, "direction": "tail"}]},
  {"id": "married", "time": {"model": "interval", "start": "start_time", "end": "end_time"},
   "roles": [
    {"role": "spouse", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 2, "max": 2, "complete": true},
    {"role": "start_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1},
    {"role": "end_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1}]},
  {"id": "flight_route",
   "roles": [
    {"role": "carrier", "slot": "core", "fillers": [{"entity": ["Airline"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "stop", "slot": "core", "fillers": [{"entity": ["Airport"]}], "min": 2, "max": null, "ordered": true, "complete": true, "direction": "head"}]},
  {"id": "born_in", "mappings": {"wikidata": "P19"}, "time": {"model": "invariant"},
   "key": {"roles": ["person"], "temporal": false, "on_collision": "dispute"},
   "roles": [
    {"role": "person", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "birthplace", "slot": "core", "fillers": [{"entity": ["Place"]}], "min": 1, "max": 1, "direction": "head"}]},
  {"id": "claims", "time": {"model": "invariant"},
   "roles": [
    {"role": "claimant", "slot": "core", "fillers": [{"entity": ["Agent"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "claim", "slot": "core", "fillers": [{"fact": ["born_in"]}], "min": 1, "max": 1, "direction": "head", "somevalue": false, "novalue": false},
    {"role": "point_in_time", "slot": "qualifier", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"}]}
 ]
}
```

The full gate schema (11 relations, including literals of every datatype, `population` with a
two-role non-temporal key, and `flies_between` with a `must_differ` warning) is in Appendix A. Its
hash, `sha256:8b2eb975…2b00`, is what the fixture's HIF metadata declares.

### 3.4 How P6 parses a schema into a hypergraph

```python
def schema_hypergraph(schema: SchemaDoc, *, slots: frozenset[str] = frozenset({"core", "qualifier"}),
                      include_builtin: bool = False, scope: Literal["global", "relation"] = "global"
                      ) -> dict[str, frozenset[str]]:
    """Vertices = attributes, hyperedges = relations. Deterministic (sorted keys)."""

def schema_hypergraph_hif(schema: SchemaDoc, **kw) -> dict:
    """The same hypergraph as a plain HIF document (roles are nodes, relations are edges), loadable by P2's XGI loader."""
```

**The attribute rule** [R01 C1-R27]. An attribute is a *global role id*. Relation r becomes the
hyperedge {ρ : ρ is used by r with slot ∈ `slots`}. `meta`-slot roles are never attributes. `time`
roles are included only on request, because they are shared by almost every stateful relation.
`scope="relation"` builds TypeDB-style local attributes (`r:ρ`). Under that scope every schema is
trivially acyclic, which is the control R04 M8.2 shows P6 needs. Built-in `khg:` relations are
excluded unless asked for.

For the gate schema the parse gives, for example, `position_held: {holder, position, replaces}`,
`population: {place, point_in_time, quantity}`, `claims: {claim, claimant, point_in_time}`. The
shared attributes are `carrier` (2 relations) and `point_in_time` (2). A constructed cyclic case for
P6's gate is three relations `a(x, y)`, `b(y, z)`, `c(z, x)` with global roles x, y, z: an α-cyclic
triangle, which the language expresses directly.

The Wikidata constraint mapping P6 and P3a need [R01 C1-R33, R04 M1]:

| Wikidata property constraint | Schema construct |
|---|---|
| allowed qualifiers (Q21510851) | `qualifier` usages (or `meta` for statement metadata) |
| required qualifier (Q21510856) | `min: 1` on that usage |
| property scope (Q53869507) | slot class |
| value-type (Q21510865) / subject-type (Q21503250) constraints | `fillers: [{entity: [...]}]` |
| allowed units (Q21514353) | `fillers: [{literal: quantity, units: [...]}]` |
| single-value (Q19474404) with separators (P4155) | `key: {roles: [subject role + separators], temporal: false, on_collision: dispute}` |
| single-best-value (Q52060874) | the same key; rank decides (§2.17) |
| conflicts-with, item-requires-statement (across statements) | not in v1 (these are across-fact rules) |

### 3.5 What the semantic validator checks

- **Schema documents** (`KHG-M…`): roles unique per relation; usages cite vocabulary roles; key roles
  exist and are not `time` or `meta`; a temporal key needs an interval time model; the time model's
  roles are `time` usages; `primary` names core roles; types and relations named in fillers exist;
  `max ≥ min`; `complete` implies `min ≥ 1`; no `khg:` ids; relation ids unique.
- **Records against a schema** (`KHG-S…`, §8.3): relation declared; roles allowed; `min`/`max`
  (status-dependent: `min` applies to asserted, disputed, superseded, retracted and quoted facts;
  candidates get a lint warning; goals must list required roles, bound or unbound); filler kind, type
  closure, datatype, `precision_min` and units; special-value flags; ordered positions; set
  semantics of unordered roles; `novalue` exclusivity; declared direction; co-occurrence constraints
  at their severity; valid-time non-emptiness; confidence scales; evidence `supports`.

---

## 4. The HIF mapping: the roles convention (P2's external artefact)

### 4.1 Two layers

1. **`hif-roles/1.0.0`: the generic roles convention.** This is the upstream proposal (§12.3) and
   is meaningful for any hypergraph.
   - `metadata["hif-roles-version"] = "1.0.0"` declares it; `metadata["hif-roles-vocabulary"]` may
     name the role vocabulary (a URI or a schema id).
   - Every incidence carries `attrs.role`, a single non-empty string. That is the key of the paper's
     own example `{"role": "PI"}` and of upstream's compliant fixture [R02 §6].
   - `attrs["role-position"]` (integer ≥ 1) orders the fillers of an ordered role.
   - **A node that plays k roles in one edge appears in k incidence records.** Each has its own
     `direction`. Readers must keep every record and must not merge by (edge, node).
2. **`khg-hif/1.0.0`: the KHG profile.** It builds on the roles convention and carries C1 losslessly.
   All its other keys are namespaced `khg:`. Its JSON Schema (`khg-hif-1.0.0.schema.json`) is
   `allOf: [vendored HIF v0.1.0, profile constraints]`, and constrains only `attrs` and `metadata`.
   So profile-valid implies HIF-valid [R02 rec. 2].

### 4.2 The contested choice, settled: one incidence record per binding

| Option | Proposed by | Evidence for | Evidence against |
|---|---|---|---|
| (b) one incidence per (edge, node), `attrs.roles` a list | R01 D-01 / C1-R63 | the HIF paper's formal model makes I ⊆ V×E a set; HyperNetX drops duplicate pairs natively [R01 V-HNX] | HIF `direction` is one value per record, so it cannot put one node in both tail and head (c06) [R03 §8]. Positions, binding ids, per-binding evidence and per-binding validity would need parallel lists. It needs adapter work anyway, since XGI drops every incidence attr [R03 §2.1] |
| (a) one record per binding; (edge, node) may repeat | R02 rec. 4, R03 D2 | the only schema-valid way to express tail + head for one node [R02 §3 inconsistency 2]; an upstream compliant test repeats a pair ("Expect to pass unless uniqueness is enforced"); round-trips exactly through both libraries via the loaders: c05 4/4, c06 3/3 [R03 §7.4] | HNX and XGI hold one cell or membership per pair natively, so the loaders need a side table or a reserved cell key |
| (c) role-keyed object in C1 (`{"role": [values]}`), list in HIF | R04 O2 | cardinality becomes checkable in draft-07 with `minItems`/`maxItems` | needs a generated JSON Schema per relation; role cardinality is a semantic check anyway (F5: role-usage conformance runs in Python); it gives no stable handle on a binding |

**Choice: (a), with C1 bindings as a list of `{bid, role, value, position?, direction?}`**, and the
mapping binding ↔ incidence is 1:1. Reasons:

1. **The binding is the unit of meaning.** Direction, position, provenance and (in v1.1) validity
   belong to one (role, value) pair. One record per binding gives each of them one place. A list of
   roles on one record would need parallel lists and cannot hold two directions.
2. **It covers every adversarial shape [verified].** `f:reg-1` puts TP53 in two roles (tail and
   head). `f:route-1` puts YYZ in one *ordered* role at positions 1 and 3, the same (edge, node,
   role) twice, told apart only by `role-position`. Option (b) would need a list of roles *and* a
   list of positions. Both fixtures round-trip exactly through XGI and HyperNetX.
3. **Stable binding ids.** A `bid` is the handle for evidence `supports`, for goal binding events,
   for the refinement that turns `somevalue` into a value, and for per-incidence governance
   [R01 C1-R36, GOV §6]. Option (c) has none.
4. **HIF alignment.** Option (a) matches the paper's statement that a node may be in both tail and
   head [R02 §3] and upstream's own fixture. It is also the smallest ask upstream: say explicitly
   that pairs may repeat.
5. **Cost is contained.** The loaders already exist and were tested [R03 §7.4]. The validator rejects
   duplicate *fillers* in an unordered role (`KHG-S014`) and duplicate `bid`s (`KHG-S025`), so a
   repeated pair is always meaningful. R01's malformed case V10 (a repeated pair) is therefore a
   **positive** case in this design, and V11 (a role repeated in one list) cannot occur.

### 4.3 C1 → HIF, exactly

**Top level.** `network-type` is `"directed"` iff every binding in the document has an effective
direction; otherwise `"undirected"`. `asc` is never written (`KHG-P007`). There are no other top-level
keys (F3).

**`metadata`: the declaration block.** Flat, dash-case keys (the paper's convention [R02 §3]):

| Key | Value | Req. |
|---|---|---|
| `hif-schema` | `https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json` (commit-pinned) | yes |
| `hif-schema-sha256` | `639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196` (blob `e2105bb`) | yes |
| `hif-schema-doi` | `10.5281/zenodo.17257719` (F2) | no |
| `hif-roles-version` | `"1.0.0"` | yes |
| `hif-roles-vocabulary` | schema id and version, or a URI | no |
| `khg-profile` | `"khg-hif/1.0.0"` | yes |
| `khg-record` | `"khg-record/1.0.0"` | yes |
| `khg-schema`, `khg-schema-sha256` | `"p2-gate/1.0.0"`, `"sha256:…"` | yes |
| `khg-schema-document` | inline relation-type schema (optional; nested) | no |
| `khg-document-id`, `khg-snapshot` (`"current"` only: HIF carries no history), `khg-complete`, `khg-created-at` | from the C1 header | id yes |

Unknown `khg-*` or `hif-*` keys and `default_attrs` are forbidden (`KHG-P008`, `KHG-P014`).
`default_attrs` makes HyperNetX invent attributes [R03 D7]. Other metadata keys pass through, from
C1 `header.extensions["hif:metadata"]`.

**`nodes`.** One record per node, `attrs.khg:kind` required:

| Node kind | Node id | attrs |
|---|---|---|
| `entity` | the entity id (no `_:` prefix) | `khg:kind`, `khg:types`, `khg:label`, `khg:aliases`, `khg:redirect-to`, `khg:extensions` |
| `literal` | `_:lit:` + first 32 hex of `digest("khg-literal-node/1", canonical literal)`, **shared by value** [R01 D-09] | `khg:kind`, `khg:literal` (the canonical literal), `khg:label` (a display string) |
| `somevalue` / `novalue` / `unbound` | `_:sv:` / `_:nv:` / `_:var:` + 32 hex of `digest("khg-special-node/1", [record id, bid])`, **one per binding** | `khg:kind` (+ `khg:unbound` = `{var, expect}`) |
| `fact-ref` | `_:ref:` + the referenced fact id | `khg:kind`, `khg:ref` (authoritative; the id is checked against it) |

Value-shared literal nodes are semantically exact: two facts dated 1643-05-14 do share that value.
In the fixture, `f:king-13`'s end and `f:king-14`'s start are one node. They also create hubs, so
`incident()` is defined on entity and fact ids only, walkers treat literal nodes as terminal, and
R01 open question 2 stays open for P10 to measure.

**`edges`.** One record per fact, rule, goal or meta record (current version), with no record-level
fields except an uninterpreted `weight` passthrough:

| C1 field | HIF `edges[].attrs` key |
|---|---|
| `kind`, `relation`, `status`, `status_ref` | `khg:kind`, `khg:relation`, `khg:status`, `khg:status-ref` |
| `rank`, `rank_reason`, `visibility` | `khg:rank`, `khg:rank-reason`, `khg:visibility` |
| `version`, `recorded_at`, `typed_under` | `khg:version`, `khg:recorded-at`, `khg:typed-under` |
| `evidence` (list, C1 shape) | `khg:evidence` |
| `confidence`, `text`, `goal`, `meta` | `khg:confidence`, `khg:text`, `khg:goal`, `khg:meta` |
| `extensions` (without `hif:weight`) | `khg:extensions` |
| `extensions["hif:weight"]` | record-level `weight` |
| `derived` | **not exported**: recomputed on import, because library edits would make it stale [R03 §5.1: `arity: 4` went stale] |

**`incidences`.** One per binding, in canonical binding order:
`{"edge": record id, "node": value node id, "direction"?: effective direction, "attrs": {"role": role, "khg:bid": bid, "role-position"?: position}}`.
In an undirected document, a binding's direction (if any) goes in `attrs["khg:direction"]`, and
record-level `direction` is absent. In a directed document `khg:direction` is forbidden
(`KHG-P010`). A binding's `extensions["hif:weight"]` becomes the incidence `weight`.

### 4.4 HIF → C1

Validate first (J, H, P). Then decode:

- Node records are unique (`KHG-D001`). Literal, special and ref node ids are recomputed and must
  match (`KHG-D005`).
- Every incidence names a declared node (`KHG-D002`) and a declared edge (`KHG-D003`).
- Each incidence becomes one binding. The value comes from the node's kind (the literal from
  `khg:literal`, the reference from `khg:ref`), and `role`, `bid` and `position` come from `attrs`.
- The HIF direction is checked against the usage's declared direction (`KHG-S016`) and stored on the
  binding only if the usage declares none.
- `khg-schema-sha256` must equal the hash of the schema used (`KHG-D009`).
- Recompute `derived`, then run the C and S/D layers.

### 4.5 Foreign HIF (no `khg-profile`)

`khg_contracts.hif.import_foreign(doc, *, strict=False) -> (C1Document, SchemaDoc, ImportReport)`:

| Input feature | Handling | Report code |
|---|---|---|
| `network-type: asc` | rejected | `KHG-P007` |
| directed file, an incidence without `direction` | strict: rejected; lenient: kept without a direction, so the re-export is undirected | `KHG-P010` / `IMPORT-W03` |
| integer ids | converted to strings; an id that collides with an existing string id (`1` and `"1"`) is an error | `IMPORT-E01` [R02 cases 16, 17, 22] |
| `attrs.role` string (legacy, the KB sample) | the role | none |
| list-valued `attrs.role` or `attrs.roles` | expanded to one binding per role (same node and direction) | `IMPORT-W01` |
| no role on an incidence | role `hif:unlabelled` | `IMPORT-W02` |
| relation | `attrs["khg:relation"]`, else `attrs.relation` (legacy), else `hif:edge` | |
| node `attrs.type`, `attrs.label` (legacy) | entity `types`, `label` | |
| any `weight` | `extensions["hif:weight"]`, never confidence | `IMPORT-I01` |
| `metadata` | `header.extensions["hif:metadata"]` | |
| isolated nodes | entity records | |
| empty edges | facts with no bindings: allowed in foreign imports, flagged, and not assertable until bound | `IMPORT-W04` |

The generated schema gives one relation per relation label and one core usage per observed role,
with `max` set to the maximum observed count. A usage gets a direction only if all its observations
agree. By design, the import round-trips a foreign file exactly (weights and metadata restored) when the
file has no list-valued roles, no unlabelled incidences and no integer ids. Otherwise the report lists
every change. Foreign import was not prototyped beyond the KB sample (§11.3).

### 4.6 The gate fixture in HIF [verified]

The HIF below is `fixture-directed.hif.json`. It was generated by the codec from
`fixture-directed.khg.json` and validated, **with no network access**, by `jsonschema` 4.26.0
(`Draft7Validator`, using the venv at `…/scratchpad/venv-libs`) and by `fastjsonschema` 2.22.2. It
was validated against the vendored `hif_schema_v0.1.0.json` (blob `e2105bb8…`, sha256
`639466b7…2196`, the Zenodo v0.1.2 bytes) and against `khg-hif-1.0.0.schema.json`. It then went
through the gate chain with equality at the C1 and HIF levels. It is shown one record per line and
still parses to the same object.

What it exercises (R01 D-20's adversarial list):

| Item | Where |
|---|---|
| a node in two roles, tail and head | `f:reg-1`: TP53 is `regulator`/tail and `target`/head |
| a repeated role | `f:coadmin-1`: `agent` × 2 |
| an ordered role, including the same node twice | `f:route-1`: `stop` YYZ at positions 1 and 3 |
| typed literals of every datatype, with precision and units | `f:station-東京` (lang_string × 2, string, quantity with unit and bounds, time/day, boolean, iri, geo); `f:pop-łódź-2019` (quantity, time/year); regnal dates |
| a nested reference | `f:claim-1` → `f:born-louis14-paris` (status `quoted`) |
| direction | every incidence (the document is directed) |
| a qualifier | `context`, `replaces`, `point_in_time` |
| evidence on a binding | `f:king-14` e2 supports b1 and b5; `f:coadmin-1` e2 supports b1 and b3 |
| non-ASCII ids | `ex:Łódź`, `ex:東京駅`, `ex:Chronicler_Ødegård`, `f:born-skłodowska-kraków` |
| somevalue / novalue | `f:born-scribe` birthplace; `f:cat-7` catalyst |
| an unbound goal slot | `g:who-1774` holder `?who` |
| a superseded pair | `f:born-skłodowska-kraków` (v2, `superseded`) ← `m:sup-1` (`khg:supersedes`, `correction`) ← `f:born-skłodowska-warszawa` |
| a key timeline | `f:king-13`, `f:king-14` (the same `position`, adjacent periods) |
| code-point offsets over astral text | `f:route-1` e1: the text starts with 🛫 |

```json
{
 "network-type": "directed",
 "metadata": {
  "hif-schema": "https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json",
  "hif-schema-sha256": "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196",
  "hif-schema-doi": "10.5281/zenodo.17257719",
  "hif-roles-version": "1.0.0",
  "hif-roles-vocabulary": "p2-gate/1.0.0",
  "khg-profile": "khg-hif/1.0.0",
  "khg-record": "khg-record/1.0.0",
  "khg-schema": "p2-gate/1.0.0",
  "khg-schema-sha256": "sha256:8b2eb97583f1ef73523a8cb3f074ffe8f2098f46c4e5f43af344475afd822b00",
  "khg-document-id": "p2-gate-fixture-directed",
  "khg-snapshot": "current",
  "khg-complete": true
 },
 "nodes": [
  {"node": "ex:AirCanada", "attrs": {"khg:kind": "entity", "khg:types": ["Airline"], "khg:label": "Air Canada"}},
  {"node": "ex:Chronicler_Ødegård", "attrs": {"khg:kind": "entity", "khg:types": ["Person"], "khg:label": "Ødegård the chronicler"}},
  {"node": "ex:HeLa", "attrs": {"khg:kind": "entity", "khg:types": ["CellLine"], "khg:label": "HeLa"}},
  {"node": "ex:KingOfFrance", "attrs": {"khg:kind": "entity", "khg:types": ["Position"], "khg:label": "King of France"}},
  {"node": "ex:Kraków", "attrs": {"khg:kind": "entity", "khg:types": ["Place"], "khg:label": "Kraków"}},
  {"node": "ex:LouisXIII", "attrs": {"khg:kind": "entity", "khg:types": ["Person"], "khg:label": "Louis XIII"}},
  {"node": "ex:LouisXIV", "attrs": {"khg:kind": "entity", "khg:types": ["Person"], "khg:label": "Louis XIV"}},
  {"node": "ex:Maria_Skłodowska", "attrs": {"khg:kind": "entity", "khg:types": ["Person"], "khg:label": "Maria Skłodowska"}},
  {"node": "ex:Paris", "attrs": {"khg:kind": "entity", "khg:types": ["Place"], "khg:label": "Paris"}},
  {"node": "ex:R-hydrolysis-7", "attrs": {"khg:kind": "entity", "khg:types": ["Reaction"], "khg:label": "hydrolysis reaction 7"}},
  {"node": "ex:TP53", "attrs": {"khg:kind": "entity", "khg:types": ["Gene"], "khg:label": "TP53"}},
  {"node": "ex:Warszawa", "attrs": {"khg:kind": "entity", "khg:types": ["Place"], "khg:label": "Warszawa"}},
  {"node": "ex:YUL", "attrs": {"khg:kind": "entity", "khg:types": ["Airport"], "khg:label": "Montréal–Trudeau"}},
  {"node": "ex:YYZ", "attrs": {"khg:kind": "entity", "khg:types": ["Airport"], "khg:label": "Toronto Pearson"}},
  {"node": "ex:anonymous_scribe", "attrs": {"khg:kind": "entity", "khg:types": ["Person"], "khg:label": "an anonymous scribe"}},
  {"node": "ex:hypoglycaemia", "attrs": {"khg:kind": "entity", "khg:types": ["Outcome"], "khg:label": "hypoglycaemia"}},
  {"node": "ex:insulin", "attrs": {"khg:kind": "entity", "khg:types": ["Drug"], "khg:label": "insulin"}},
  {"node": "ex:metformin", "attrs": {"khg:kind": "entity", "khg:types": ["Drug"], "khg:label": "metformin"}},
  {"node": "ex:Łódź", "attrs": {"khg:kind": "entity", "khg:types": ["Place"], "khg:label": "Łódź"}},
  {"node": "ex:東京駅", "attrs": {"khg:kind": "entity", "khg:types": ["Station"], "khg:label": "Tokyo Station"}},
  {"node": "_:lit:0916b45596fd096b0380304dc60304a9", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "lang_string", "value": "東京駅", "lang": "ja"}, "khg:label": "東京駅@ja"}},
  {"node": "_:lit:1c9ac9fd2f7bb893ec62c50f833b7ff2", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+1914-12-20T00:00:00Z", "precision": 11, "calendar": "gregorian"}, "khg:label": "+1914-12-20T00:00:00Z/11"}},
  {"node": "_:lit:32fd170eaa098b760664b7efbe0e76e3", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "lang_string", "value": "Tokyo Station", "lang": "en"}, "khg:label": "Tokyo Station@en"}},
  {"node": "_:lit:37211654a2f2823c4fad86f490e56819", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "boolean", "value": true}, "khg:label": "true"}},
  {"node": "_:lit:3b18d26dda2204c791d484b77e3760d3", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "geo", "lat": "+35.6812", "lon": "+139.7671", "precision": "+0.0001", "globe": "wd:Q2"}, "khg:label": "+35.6812,+139.7671"}},
  {"node": "_:lit:4d14352c5db021d2b0e70906aaa17a56", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+1610-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}, "khg:label": "+1610-05-14T00:00:00Z/11"}},
  {"node": "_:lit:6d161c6594652b245fb282f351b71116", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z", "precision": 9, "calendar": "gregorian"}, "khg:label": "+2019-00-00T00:00:00Z/9"}},
  {"node": "_:lit:7d51413289245ae6e1aef061972a8a64", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "iri", "value": "https://www.tokyostationcity.com/"}, "khg:label": "https://www.tokyostationcity.com/"}},
  {"node": "_:lit:851d6b4ba33d0b79f18d99559e5db094", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "string", "value": "TYO"}, "khg:label": "TYO"}},
  {"node": "_:lit:86e4637ee45af992a7467d24f2a93a64", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "quantity", "amount": "+679941", "unit": "1"}, "khg:label": "+679941"}},
  {"node": "_:lit:89999fcef774cb586483ef351c89ab9d", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+1715-09-01T00:00:00Z", "precision": 11, "calendar": "gregorian"}, "khg:label": "+1715-09-01T00:00:00Z/11"}},
  {"node": "_:lit:90f05b1fd19dd04d37dc279f0c7cecf1", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+1774-05-10T00:00:00Z", "precision": 11, "calendar": "gregorian"}, "khg:label": "+1774-05-10T00:00:00Z/11"}},
  {"node": "_:lit:bc18b6e20588929fdc83e6b64a293be7", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573", "lower": "+3", "upper": "+4"}, "khg:label": "+3.5 wd:Q11573"}},
  {"node": "_:lit:c2de076c6e50fcaff7c5f3a4c11964c6", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}, "khg:label": "+1643-05-14T00:00:00Z/11"}},
  {"node": "_:lit:ef0ecfad82ca40240062f1f49dd1a6a4", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+1700-00-00T00:00:00Z", "precision": 9, "calendar": "gregorian"}, "khg:label": "+1700-00-00T00:00:00Z/9"}},
  {"node": "_:nv:78311fb3c57188a07d1d2821930e2c3d", "attrs": {"khg:kind": "novalue"}},
  {"node": "_:ref:f:born-louis14-paris", "attrs": {"khg:kind": "fact-ref", "khg:ref": "f:born-louis14-paris"}},
  {"node": "_:ref:f:born-skłodowska-kraków", "attrs": {"khg:kind": "fact-ref", "khg:ref": "f:born-skłodowska-kraków"}},
  {"node": "_:ref:f:born-skłodowska-warszawa", "attrs": {"khg:kind": "fact-ref", "khg:ref": "f:born-skłodowska-warszawa"}},
  {"node": "_:sv:b3d2979870a1d331fa6dd177274b85d9", "attrs": {"khg:kind": "somevalue"}},
  {"node": "_:var:42a7d49f12bd77b91df2c3bdb9d9b045", "attrs": {"khg:kind": "unbound", "khg:unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}}
 ],
 "edges": [
  {"edge": "f:born-louis14-paris", "attrs": {"khg:kind": "fact", "khg:relation": "born_in", "khg:status": "quoted"}},
  {"edge": "f:born-scribe", "attrs": {"khg:kind": "fact", "khg:relation": "born_in", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:scriptorium-notes"}}]}},
  {"edge": "f:born-skłodowska-kraków", "attrs": {"khg:kind": "fact", "khg:relation": "born_in", "khg:status": "superseded", "khg:status-ref": "m:sup-1", "khg:version": 2, "khg:evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:curie-wrong", "doc_sha256": "sha256:685ed4266cfa7fb0429dee59b9feaa3cefde8894ac6556dce24e1894504a7a0d"}, "selectors": [{"type": "quote", "exact": "Maria Skłodowska was born in Kraków", "prefix": "", "suffix": "."}, {"type": "position", "start": 0, "end": 35}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}}]}},
  {"edge": "f:born-skłodowska-warszawa", "attrs": {"khg:kind": "fact", "khg:relation": "born_in", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}}]}},
  {"edge": "f:cat-7", "attrs": {"khg:kind": "fact", "khg:relation": "catalysed_by", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:lab-notebook-7"}}]}},
  {"edge": "f:claim-1", "attrs": {"khg:kind": "fact", "khg:relation": "claims", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:chronicle-1700"}}]}},
  {"edge": "f:coadmin-1", "attrs": {"khg:kind": "fact", "khg:relation": "co_administration_causes", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:coadmin-note", "doc_sha256": "sha256:242a3e2542b83f98e5adfa478e9d7ef5aa909708f7e184e88f51e5b09ff17368"}, "selectors": [{"type": "quote", "exact": "Metformin taken together with insulin can cause hypoglycaemia", "prefix": "", "suffix": "."}, {"type": "position", "start": 0, "end": 61}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "confidence": {"value": 7.5, "scale": "llm-0-10"}}, {"id": "e2", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:insulin-label"}, "supports": ["b1", "b3"]}], "khg:confidence": {"value": 0.9, "scale": "probability", "scorer": {"name": "fixture-belief", "version": "0"}}}},
  {"edge": "f:king-13", "attrs": {"khg:kind": "fact", "khg:relation": "position_held", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:regnal-list"}}]}},
  {"edge": "f:king-14", "attrs": {"khg:kind": "fact", "khg:relation": "position_held", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:regnal-list"}, "supports": ["b1", "b2", "b3", "b4"]}, {"id": "e2", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:louis-bio", "doc_sha256": "sha256:56940b729460cb9a75d5d63ab1f907a502fef80530b4aabff2cd8e9c28a44b2f"}, "selectors": [{"type": "quote", "exact": "Louis XIV succeeded his father Louis XIII", "prefix": "", "suffix": " as King of "}, {"type": "position", "start": 0, "end": 41}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "supports": ["b1", "b5"]}]}},
  {"edge": "f:pop-łódź-2019", "attrs": {"khg:kind": "fact", "khg:relation": "population", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:stat-yearbook-2020"}, "reference": [{"role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2020-00-00T00:00:00Z", "precision": 9}}}]}]}},
  {"edge": "f:reg-1", "attrs": {"khg:kind": "fact", "khg:relation": "regulates", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:review-p53"}}]}},
  {"edge": "f:route-1", "attrs": {"khg:kind": "fact", "khg:relation": "flight_route", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:route-note", "doc_sha256": "sha256:159bbe0d06e3ce286c6796f8aad3fa7eb52d01132423f10224915b31e9a104ca"}, "selectors": [{"type": "quote", "exact": "Toronto → Montréal → Toronto", "prefix": "anada flies ", "suffix": " every day."}, {"type": "position", "start": 19, "end": 47}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}}], "khg:text": "🛫 Air Canada flies Toronto → Montréal → Toronto every day."}},
  {"edge": "f:station-東京", "attrs": {"khg:kind": "fact", "khg:relation": "station_profile", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:station-guide"}}]}},
  {"edge": "g:who-1774", "attrs": {"khg:kind": "goal", "khg:relation": "position_held", "khg:status": "open", "khg:goal": {"brief": "Who became King of France on 10 May 1774?", "owner": "agent:history-desk"}}},
  {"edge": "m:sup-1", "attrs": {"khg:kind": "meta", "khg:relation": "khg:supersedes", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}}], "khg:meta": {"reason": "correction", "note": "birthplace is Warsaw, per the curated biography"}}}
 ],
 "incidences": [
  {"edge": "f:born-louis14-paris", "node": "ex:Paris", "direction": "head", "attrs": {"role": "birthplace", "khg:bid": "b2"}},
  {"edge": "f:born-louis14-paris", "node": "ex:LouisXIV", "direction": "tail", "attrs": {"role": "person", "khg:bid": "b1"}},
  {"edge": "f:born-scribe", "node": "_:sv:b3d2979870a1d331fa6dd177274b85d9", "direction": "head", "attrs": {"role": "birthplace", "khg:bid": "b2"}},
  {"edge": "f:born-scribe", "node": "ex:anonymous_scribe", "direction": "tail", "attrs": {"role": "person", "khg:bid": "b1"}},
  {"edge": "f:born-skłodowska-kraków", "node": "ex:Kraków", "direction": "head", "attrs": {"role": "birthplace", "khg:bid": "b2"}},
  {"edge": "f:born-skłodowska-kraków", "node": "ex:Maria_Skłodowska", "direction": "tail", "attrs": {"role": "person", "khg:bid": "b1"}},
  {"edge": "f:born-skłodowska-warszawa", "node": "ex:Warszawa", "direction": "head", "attrs": {"role": "birthplace", "khg:bid": "b2"}},
  {"edge": "f:born-skłodowska-warszawa", "node": "ex:Maria_Skłodowska", "direction": "tail", "attrs": {"role": "person", "khg:bid": "b1"}},
  {"edge": "f:cat-7", "node": "_:nv:78311fb3c57188a07d1d2821930e2c3d", "direction": "head", "attrs": {"role": "catalyst", "khg:bid": "b2"}},
  {"edge": "f:cat-7", "node": "ex:R-hydrolysis-7", "direction": "tail", "attrs": {"role": "reaction", "khg:bid": "b1"}},
  {"edge": "f:claim-1", "node": "_:ref:f:born-louis14-paris", "direction": "head", "attrs": {"role": "claim", "khg:bid": "b2"}},
  {"edge": "f:claim-1", "node": "ex:Chronicler_Ødegård", "direction": "tail", "attrs": {"role": "claimant", "khg:bid": "b1"}},
  {"edge": "f:claim-1", "node": "_:lit:ef0ecfad82ca40240062f1f49dd1a6a4", "direction": "tail", "attrs": {"role": "point_in_time", "khg:bid": "b3"}},
  {"edge": "f:coadmin-1", "node": "ex:insulin", "direction": "tail", "attrs": {"role": "agent", "khg:bid": "b1"}},
  {"edge": "f:coadmin-1", "node": "ex:metformin", "direction": "tail", "attrs": {"role": "agent", "khg:bid": "b2"}},
  {"edge": "f:coadmin-1", "node": "ex:hypoglycaemia", "direction": "head", "attrs": {"role": "effect", "khg:bid": "b3"}},
  {"edge": "f:king-13", "node": "_:lit:c2de076c6e50fcaff7c5f3a4c11964c6", "direction": "tail", "attrs": {"role": "end_time", "khg:bid": "b4"}},
  {"edge": "f:king-13", "node": "ex:LouisXIII", "direction": "tail", "attrs": {"role": "holder", "khg:bid": "b1"}},
  {"edge": "f:king-13", "node": "ex:KingOfFrance", "direction": "head", "attrs": {"role": "position", "khg:bid": "b2"}},
  {"edge": "f:king-13", "node": "_:lit:4d14352c5db021d2b0e70906aaa17a56", "direction": "tail", "attrs": {"role": "start_time", "khg:bid": "b3"}},
  {"edge": "f:king-14", "node": "_:lit:89999fcef774cb586483ef351c89ab9d", "direction": "tail", "attrs": {"role": "end_time", "khg:bid": "b4"}},
  {"edge": "f:king-14", "node": "ex:LouisXIV", "direction": "tail", "attrs": {"role": "holder", "khg:bid": "b1"}},
  {"edge": "f:king-14", "node": "ex:KingOfFrance", "direction": "head", "attrs": {"role": "position", "khg:bid": "b2"}},
  {"edge": "f:king-14", "node": "ex:LouisXIII", "direction": "tail", "attrs": {"role": "replaces", "khg:bid": "b5"}},
  {"edge": "f:king-14", "node": "_:lit:c2de076c6e50fcaff7c5f3a4c11964c6", "direction": "tail", "attrs": {"role": "start_time", "khg:bid": "b3"}},
  {"edge": "f:pop-łódź-2019", "node": "ex:Łódź", "direction": "tail", "attrs": {"role": "place", "khg:bid": "b1"}},
  {"edge": "f:pop-łódź-2019", "node": "_:lit:6d161c6594652b245fb282f351b71116", "direction": "tail", "attrs": {"role": "point_in_time", "khg:bid": "b3"}},
  {"edge": "f:pop-łódź-2019", "node": "_:lit:86e4637ee45af992a7467d24f2a93a64", "direction": "head", "attrs": {"role": "quantity", "khg:bid": "b2"}},
  {"edge": "f:reg-1", "node": "ex:HeLa", "direction": "tail", "attrs": {"role": "context", "khg:bid": "b1"}},
  {"edge": "f:reg-1", "node": "ex:TP53", "direction": "tail", "attrs": {"role": "regulator", "khg:bid": "b2"}},
  {"edge": "f:reg-1", "node": "ex:TP53", "direction": "head", "attrs": {"role": "target", "khg:bid": "b3"}},
  {"edge": "f:route-1", "node": "ex:AirCanada", "direction": "tail", "attrs": {"role": "carrier", "khg:bid": "b1"}},
  {"edge": "f:route-1", "node": "ex:YYZ", "direction": "head", "attrs": {"role": "stop", "khg:bid": "b2", "role-position": 1}},
  {"edge": "f:route-1", "node": "ex:YUL", "direction": "head", "attrs": {"role": "stop", "khg:bid": "b3", "role-position": 2}},
  {"edge": "f:route-1", "node": "ex:YYZ", "direction": "head", "attrs": {"role": "stop", "khg:bid": "b4", "role-position": 3}},
  {"edge": "f:station-東京", "node": "_:lit:37211654a2f2823c4fad86f490e56819", "direction": "head", "attrs": {"role": "active", "khg:bid": "b7"}},
  {"edge": "f:station-東京", "node": "_:lit:851d6b4ba33d0b79f18d99559e5db094", "direction": "head", "attrs": {"role": "code", "khg:bid": "b4"}},
  {"edge": "f:station-東京", "node": "_:lit:bc18b6e20588929fdc83e6b64a293be7", "direction": "head", "attrs": {"role": "elevation", "khg:bid": "b5"}},
  {"edge": "f:station-東京", "node": "_:lit:7d51413289245ae6e1aef061972a8a64", "direction": "head", "attrs": {"role": "homepage", "khg:bid": "b8"}},
  {"edge": "f:station-東京", "node": "_:lit:3b18d26dda2204c791d484b77e3760d3", "direction": "head", "attrs": {"role": "location", "khg:bid": "b9"}},
  {"edge": "f:station-東京", "node": "_:lit:32fd170eaa098b760664b7efbe0e76e3", "direction": "head", "attrs": {"role": "name", "khg:bid": "b3"}},
  {"edge": "f:station-東京", "node": "_:lit:0916b45596fd096b0380304dc60304a9", "direction": "head", "attrs": {"role": "name", "khg:bid": "b2"}},
  {"edge": "f:station-東京", "node": "_:lit:1c9ac9fd2f7bb893ec62c50f833b7ff2", "direction": "head", "attrs": {"role": "opened", "khg:bid": "b6"}},
  {"edge": "f:station-東京", "node": "ex:東京駅", "direction": "tail", "attrs": {"role": "station", "khg:bid": "b1"}},
  {"edge": "g:who-1774", "node": "_:var:42a7d49f12bd77b91df2c3bdb9d9b045", "direction": "tail", "attrs": {"role": "holder", "khg:bid": "b1"}},
  {"edge": "g:who-1774", "node": "ex:KingOfFrance", "direction": "head", "attrs": {"role": "position", "khg:bid": "b2"}},
  {"edge": "g:who-1774", "node": "_:lit:90f05b1fd19dd04d37dc279f0c7cecf1", "direction": "tail", "attrs": {"role": "start_time", "khg:bid": "b3"}},
  {"edge": "m:sup-1", "node": "_:ref:f:born-skłodowska-kraków", "direction": "head", "attrs": {"role": "khg:superseded", "khg:bid": "b2"}},
  {"edge": "m:sup-1", "node": "_:ref:f:born-skłodowska-warszawa", "direction": "tail", "attrs": {"role": "khg:superseding", "khg:bid": "b1"}}
 ]
}
```

The **undirected companion fixture** covers what a directed document cannot: a symmetric role with no
direction (`married`), and one node in two roles without direction (`flies_between` with origin =
destination = YYZ, a `must_differ` warning, R01 I9). Through XGI this exercises the plain
`Hypergraph` class, where the pair collapses and the side table restores it [verified]:

```json
{
 "network-type": "undirected",
 "metadata": {
  "hif-schema": "https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json",
  "hif-schema-sha256": "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196",
  "hif-schema-doi": "10.5281/zenodo.17257719",
  "hif-roles-version": "1.0.0",
  "hif-roles-vocabulary": "p2-gate/1.0.0",
  "khg-profile": "khg-hif/1.0.0",
  "khg-record": "khg-record/1.0.0",
  "khg-schema": "p2-gate/1.0.0",
  "khg-schema-sha256": "sha256:8b2eb97583f1ef73523a8cb3f074ffe8f2098f46c4e5f43af344475afd822b00",
  "khg-document-id": "p2-gate-fixture-undirected",
  "khg-snapshot": "current",
  "khg-complete": true
 },
 "nodes": [
  {"node": "ex:AirCanada", "attrs": {"khg:kind": "entity", "khg:types": ["Airline"], "khg:label": "Air Canada"}},
  {"node": "ex:Maria_Skłodowska", "attrs": {"khg:kind": "entity", "khg:types": ["Person"], "khg:label": "Maria Skłodowska"}},
  {"node": "ex:Pierre_Curie", "attrs": {"khg:kind": "entity", "khg:types": ["Person"], "khg:label": "Pierre Curie"}},
  {"node": "ex:YYZ", "attrs": {"khg:kind": "entity", "khg:types": ["Airport"], "khg:label": "Toronto Pearson"}},
  {"node": "_:lit:6914a0d25911f31c02d9ab52abfc5380", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+1906-04-19T00:00:00Z", "precision": 11, "calendar": "gregorian"}, "khg:label": "+1906-04-19T00:00:00Z/11"}},
  {"node": "_:lit:b11291e17146f26e1ea99ec83e6d5359", "attrs": {"khg:kind": "literal", "khg:literal": {"datatype": "time", "time": "+1895-07-26T00:00:00Z", "precision": 11, "calendar": "gregorian"}, "khg:label": "+1895-07-26T00:00:00Z/11"}}
 ],
 "edges": [
  {"edge": "f:loop-yyz", "attrs": {"khg:kind": "fact", "khg:relation": "flies_between", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:sightseeing-flight"}}]}},
  {"edge": "f:married-curie", "attrs": {"khg:kind": "fact", "khg:relation": "married", "khg:status": "asserted", "khg:evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}}]}}
 ],
 "incidences": [
  {"edge": "f:loop-yyz", "node": "ex:AirCanada", "attrs": {"role": "carrier", "khg:bid": "b1"}},
  {"edge": "f:loop-yyz", "node": "ex:YYZ", "attrs": {"role": "destination", "khg:bid": "b2"}},
  {"edge": "f:loop-yyz", "node": "ex:YYZ", "attrs": {"role": "origin", "khg:bid": "b3"}},
  {"edge": "f:married-curie", "node": "_:lit:6914a0d25911f31c02d9ab52abfc5380", "attrs": {"role": "end_time", "khg:bid": "b4"}},
  {"edge": "f:married-curie", "node": "ex:Maria_Skłodowska", "attrs": {"role": "spouse", "khg:bid": "b1"}},
  {"edge": "f:married-curie", "node": "ex:Pierre_Curie", "attrs": {"role": "spouse", "khg:bid": "b2"}},
  {"edge": "f:married-curie", "node": "_:lit:b11291e17146f26e1ea99ec83e6d5359", "attrs": {"role": "start_time", "khg:bid": "b3"}}
 ]
}
```

---

## 5. Library loaders (XGI and HyperNetX)

### 5.1 Approach (F1)

The package owns the HIF codec: parse, validate, encode and decode. The library objects are
*projections*, built through public constructors. What a library cannot hold lives in a context
object, bundled with the object so the two cannot be separated. Export reconciles the two
[R03 §7.4, D1, D3]. The loaders never call `xgi.read_hif`/`write_hif`/`from_hif_dict` or
`hnx.from_hif`/`to_hif`, and they never touch the network. The approach was prototyped with
`research/probes/role_loaders_sketch.py`: exact on 24 of R03's 25 accepted cases [R03 §7.4], and on
both gate fixtures and the migrated sample in this design [verified].

### 5.2 API

```python
# khg_contracts/hif/xgi.py   (extra: khg-contracts[xgi], xgi==0.10.2)
@dataclass(frozen=True)
class XGIBundle:
    H: "xgi.Hypergraph | xgi.DiHypergraph"     # DiHypergraph iff network-type == "directed"
    ctx: HIFContext
    def records(self, edge: str, node: str | None = None) -> tuple[IncidenceRecord, ...]: ...   # all records, repeated pairs included
    def role_map(self, edge: str) -> tuple[tuple[str, str, str | None, int | None], ...]: ...  # (node, role, direction, position)
    def check(self) -> LoaderReport: ...        # stale and unlabelled memberships, without exporting

def to_xgi(hif: Mapping, *, validate: bool = True) -> XGIBundle: ...
def from_xgi(bundle: XGIBundle, *, strict: bool = True) -> tuple[dict, LoaderReport]: ...

# khg_contracts/hif/hnx.py   (extra: khg-contracts[hypernetx], hypernetx==2.4.3, pandas<3)
@dataclass(frozen=True)
class HNXBundle:
    H: "hnx.Hypergraph"    # first record of each (edge, node) pair in the cell; records 2..k under attrs["khg:extra-incidences"]
    ctx: HIFContext
    def records(self, edge: str, node: str | None = None) -> tuple[IncidenceRecord, ...]: ...
    def check(self) -> LoaderReport: ...

def to_hnx(hif: Mapping, *, validate: bool = True) -> HNXBundle: ...
def from_hnx(bundle: HNXBundle, *, strict: bool = True) -> tuple[dict, LoaderReport]: ...

# convenience, in khg_contracts/hif/__init__.py
def encode(doc: C1Document, schema: SchemaDoc) -> dict: ...                              # C1 -> HIF (profile)
def decode(hif: Mapping, schema: SchemaDoc) -> C1Document: ...                           # HIF (profile) -> C1
def import_foreign(hif: Mapping, *, strict: bool = False) -> tuple[C1Document, SchemaDoc, ImportReport]: ...

@dataclass(frozen=True)
class LoaderReport:
    stale_records: tuple[IncidenceRecord, ...]           # records whose membership no longer exists
    unlabelled_memberships: tuple[tuple[str, str, str | None], ...]   # memberships with no record
    changed_ids: tuple[tuple[str, str], ...]             # detected renumbering, where it can be mapped back
    warnings: tuple[str, ...]
```

### 5.3 What the context holds

| Item | XGI | HNX | Why |
|---|---|---|---|
| every incidence record (role, bid, position, direction, weight, attrs), keyed by (edge, node, direction) plus an ordinal | yes: the only store of roles | records 2..k of a pair (the first is native in the cell) | XGI has no incidence store; HNX keeps one cell per pair [R03 X1, N3] |
| `network-type` | the class encodes directed/undirected | yes | HNX never reads it [R03 N7] |
| `metadata` | also in `H._net_attr` (via the public setter) | yes | HNX keeps only `name` [R03 N4] |
| whether each weight was present | yes | yes | XGI drops weights; HNX invents `1` [R03 row 9] |
| node and edge declaration order | yes | yes | deterministic output [R03 D11] |
| isolated nodes, empty edges | natively kept | kept in the property stores, exported from there | HNX views hide them [R03 N8] |

### 5.4 Native operations between load and export (R03 D9)

| Library | Safe (identity-preserving, roles follow or are reported) | Unsafe (the loader warns; strict export raises if a check fails) |
|---|---|---|
| XGI | `copy()`; `add_node`; weak `remove_node` (records reported stale); `set_*_attributes` on non-`khg:` keys; `add_edge` (new memberships are unlabelled until labelled through the bundle) | `merge_duplicate_edges` (copies lose attrs), `cleanup` (keeps the largest component, relabels), `convert_labels_to_integers` (overwrites `label`), `H << H2` (renumbers edges: all records stale), `dual`, `xgi.subhypergraph` on a `DiHypergraph` (raises `XGIError`), conversion to `SimplicialComplex` |
| HNX | `clone`, `remove_edges`/`remove_nodes`/`remove_incidences`, `rename` (roles follow the node), `restrict_to_edges`, `dual` (cells follow the pair), `H.incidences[(e, n)].role = …` | `collapse_nodes` and `collapse_nodes_and_edges` (roles move to the wrong participant [R03 §7.4]), `collapse_edges` (weights summed), `restrict_to_nodes` (partial n-ary facts: the strict export then fails `KHG-S003`), `sum` (self wins), `add_incidence` without `direction` in a directed bundle, `add_edge`/`add_node` without incidences (invisible to views) |

### 5.5 Strict mode and determinism

- **Strict** (the default, and what the gate uses). `from_*` raises `LoaderIntegrityError` if there
  are stale records or unlabelled memberships, if a directed incidence has no direction, or if the
  exported document fails the profile or the semantic layer. **Lenient** exports what exists, puts
  every discrepancy in the report, and never re-attaches a record to another pair [R03 §7.1 item 6].
- **Determinism.** Output order follows the context's source order, which is canonical when the
  source came from `encode`. New memberships are appended sorted by (edge, node, direction). The
  output never depends on set iteration: XGI's own writer gave 4 different outputs under 4 hash
  seeds [R03 §4.1]. `test_determinism.py` checks byte identity across `PYTHONHASHSEED` values.

### 5.6 The library-evidence test (material for the upstream issues)

`tests/library_evidence/test_native_hif.py` (pytest marker `library_evidence`, run in CI) takes both
fixtures through `xgi.read_hif` → `xgi.write_hif`, and through `hnx.from_hif` → `hnx.to_hif` →
`hnx.from_hif` → `hnx.to_hif`. For HNX, `hypernetx.hif.requests.get` is patched to return the
vendored schema, so nothing touches the network. It asserts the *documented* losses. If a library
release fixes one, the assertion fails with "behaviour changed: update the upstream issue", rather
than passing silently. It writes `library-evidence.json` for the HIF proposal. On the directed
fixture [verified]:

| Library | Incidences in → out | Roles kept | Other |
|---|---|---|---|
| XGI 0.10.2 `read_hif`/`write_hif` | 49 → 48 (the second YYZ `stop` collapses; TP53's tail and head survive as in/out sets) | 0 of 49 | incidence `attrs` dropped |
| HNX 2.4.3 `from_hif`/`to_hif` | 49 → 47 (both repeated pairs lose their second record) | 47 of 47 remaining | all 12 metadata keys lost; the second directed generation returns `None` (`'nil'` direction) |
| P2 loaders (sketch) | 49 → 49 | 49 of 49 | exact (§1.2) |

---

## 6. C2: the store interface (`khg-store/1.0.0`)

### 6.1 The Protocol

```python
# khg_contracts/store/protocol.py
from typing import Iterator, Literal, Mapping, Protocol, Sequence, TypedDict, runtime_checkable

Record = dict          # a C1 record (entity, fact, rule, goal, meta), JSON-shaped
Value = dict           # a C1 value (entity | literal | fact | special)

class BindingPattern(TypedDict, total=False):
    role: str          # required
    value: Value       # omitted: any value
    position: int      # ordered roles only

@dataclass(frozen=True)
class StoreInfo:
    name: str
    interface_version: str          # "khg-store/1.0.0"
    c1_version: str                 # "khg-record/1.0.0"
    capabilities: frozenset[str]    # see §6.3

@dataclass(frozen=True)
class WriteReceipt:
    tx: int                         # transaction sequence number
    recorded_at: str                # RFC 3339 UTC, assigned to every version written by this call
    records: tuple[tuple[str, int, Literal["created", "versioned", "noop"]], ...]

@dataclass(frozen=True)
class Page:
    items: tuple[Record, ...]
    next_after: str | None          # pass as `after` to continue; None at the end

@dataclass(frozen=True)
class WalkStep:
    from_id: str                    # fact id
    via: str                        # khg:supersedes record id
    reason: str                     # its meta.reason
    to: tuple[str, ...]             # sorted fact ids on the other side

KINDS = frozenset({"fact"}); STATUS = frozenset({"asserted"})
Mode = Literal["definite", "possible"]

@runtime_checkable
class Store(Protocol):
    def info(self) -> StoreInfo: ...

    def put(self, records: Record | Sequence[Record], *, expect: Mapping[str, int] | None = None) -> WriteReceipt:
        """Atomic batch. Each record is a new id (version 1) or the next version of an existing id.
        Raises ValidationError, VersionError (KHG-D013/D014), KeyConflictError (KHG-D016), ConcurrencyError."""

    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> Record | None: ...
    def history(self, id: str) -> Sequence[Record]: ...                                  # capability "history"

    def incident(self, node: str, *, role: str | None = None, relation: str | None = None,
                 kinds: frozenset[str] = KINDS, status: frozenset[str] = STATUS,
                 include_deprecated: bool = False, include_suppressed: bool = False,
                 valid_at: str | None = None, valid_mode: Mode = "definite", as_at: str | None = None,
                 limit: int | None = None, after: str | None = None) -> Page: ...

    def degree(self, node: str, *, role: str | None = None, relation: str | None = None, **filters) -> int: ...

    def find(self, relation: str, pattern: Sequence[BindingPattern], *,
             match: Literal["at_least", "exact"] = "at_least",
             kinds: frozenset[str] = KINDS, status: frozenset[str] = STATUS,
             include_deprecated: bool = False, include_suppressed: bool = False,
             valid_at: str | None = None, valid_mode: Mode = "definite", as_at: str | None = None,
             limit: int | None = None, after: str | None = None) -> Page: ...

    def by_key(self, relation: str, key_bindings: Sequence[BindingPattern], *,
               valid_at: str | None = None, valid_mode: Mode = "definite", as_at: str | None = None,
               status: frozenset[str] = STATUS, include_deprecated: bool = False) -> Sequence[Record]: ...

    def supersession_walk(self, id: str, *, direction: Literal["forward", "backward"] = "forward",
                          as_at: str | None = None, max_steps: int | None = None) -> Sequence[WalkStep]: ...

    def export(self, format: Literal["khg-json", "khg-jsonl", "hif"] = "khg-json", *,
               as_at: str | None = None, history: bool = False) -> dict | Iterator[dict]: ...
```

Errors are `khg_contracts.errors.KHGError` subclasses carrying `.codes` (stable codes, §8.2):
`ValidationError`, `VersionError`, `KeyConflictError`, `ConcurrencyError`, `CapabilityError`.

### 6.2 Semantics

| Operation | Semantics |
|---|---|
| `put` | **All-or-nothing.** For each record: the full validator runs (C, S). A record whose non-store fields equal the current version is a **no-op** (idempotent, C2-R01). Otherwise it becomes `current.version + 1`. The **version identity rule** (§2.16: relation kept, new ⊑ old, evidence append-only, allowed transition per §2.13) raises `VersionError`. Status `candidate` is refused (`KHG-D017`). After staging, the prospective state is checked for references, acyclicity, lifecycle pointers and the **key invariant** (`KHG-D016`). Every version written by one call gets one `recorded_at`. `expect` gives optimistic concurrency: id → the current version the caller saw |
| `get` | the version current at `as_at` (latest `recorded_at ≤ as_at`); `version=` selects one exactly; `None` if the id did not exist then |
| `incident` | every record in which `node` (an entity id or a fact id) fills some role, or `role` if given; **complete** (no sampling) and ordered by id. A fact in which the node fills two roles appears once [verified S-INC-01/02]. Literal nodes are not addressable: use `find` with a literal value |
| `find` | `at_least`: an injective match of the pattern bindings to the record's bindings (same role, canonically equal value, same position if given; a repeated role in the pattern needs distinct bindings) [verified S-FIND-01]. `exact`: at_least, plus the record has no other non-meta bindings. Literal matching is canonical equality (precision matters); matching by refinement is v1.1 |
| `by_key` | facts whose `key_digest` equals the digest of `key_bindings`; ordered by rank (preferred first), then definite start (−∞ first), then id. With `valid_at`: the facts valid then, which by the invariant is 0 or 1 unless ranked alternatives exist. Without it: **the key's timeline** [verified S-KEY-01/02] |
| `supersession_walk` | forward from a superseded fact through `khg:supersedes` records (the `status_ref` index, else incidence on the ref node) to the superseding facts, breadth-first, as believed at `as_at`. The result is a DAG: it branches on conflation and joins on duplicates. It always terminates, because the supersession graph is acyclic (`KHG-D012`) and visited facts are skipped. Backward walks the other way. Retractions end chains; world-time succession is *not* part of the walk (that is `by_key`) |
| `degree` | `len(incident(...))` under the same filters (cheap in indexed stores) [R01 C2-R12] |
| `export` | `khg-json`: a canonical C1 document of the snapshot at `as_at`. `khg-jsonl`: header line plus records; with `history=True`, every version. `hif`: `encode(snapshot)` (current versions only; HIF has no history) |

**Defaults, written down (C2-R07, C2-R13):**

| Parameter | Default | Meaning |
|---|---|---|
| `as_at` | `None` = now | current belief |
| `valid_at` | `None` | no valid-time filter: facts of every validity, ended ones included |
| `valid_mode` | `definite` | when `valid_at` is given: only facts known to hold then (`possible` adds facts that may hold, including `unstated` ones) |
| `kinds` | `{"fact"}` | rules, goals and meta records only on request |
| `status` | `{"asserted"}` | disputed, quoted, superseded and retracted only on request |
| rank / visibility | exclude `deprecated` / exclude `suppressed` | as Wikidata excludes deprecated statements by default [R04 M5] |
| order | ascending id (code-point order of NFC ids) | total and deterministic; stable pagination with `after` |

### 6.3 Capability flags

A conformance scenario needing a capability the store lacks is reported **inapplicable**, never
passed [R04 O13]:

| Flag | Meaning |
|---|---|
| `history` | keeps every version; `history()` and `get(version=…)` |
| `as_at` | transaction-time reconstruction (needs an injectable clock in the test adapter) |
| `valid_time` | `valid_at` filters with definite and possible modes over precision windows |
| `nesting` | fact-valued bindings and `incident` on a fact id |
| `ordered_roles` | positions stored and returned |
| `special_values` | somevalue and novalue |
| `goals` | goal records with unbound slots |
| `literal_fillers` | literal bindings as bindings (not only as attributes) |
| `key_constraint` | the key invariant enforced on `put` |
| `atomic_batch` | `put` of several records is all-or-nothing |
| `pagination` | `limit`/`after` |

### 6.4 The reference in-memory implementation

`khg_contracts.store.memory.MemoryStore(schema, *, clock=None)` keeps `id → [versions]` and indexes
for node → record ids (entity ids and fact refs, per role), (relation, `core_key`),
(relation, `key_digest`), and meta records by referenced fact. It implements every capability.
Validation on `put` is incremental: the staged records, plus whatever shares their keys or
references. The prototype `proto_store.MemoryStore` passed the smoke test, 18 checks and 4
declarative scenarios [verified].

### 6.5 Identity planning sits beside the store

```python
# khg_contracts/identity.py
Relation = Literal["unrelated", "duplicate", "refines", "generalises", "negation_conflict", "key_conflict", "key_timeline", "distinct"]
Outcome = Literal["insert", "merge_duplicate", "refine", "support", "succession", "supersession", "dispute", "reject", "needs_review"]

def refines(a: Record, b: Record, schema: SchemaDoc) -> bool: ...          # a ⊑ b  (§2.16)
def relate(n: Record, e: Record, schema: SchemaDoc) -> Relation: ...        # §2.18
def presumed_interval(f: Record, schema: SchemaDoc) -> Interval: ...        # §2.12.2
@dataclass(frozen=True)
class WritePlan:
    outcome: Outcome
    records: tuple[Record, ...]          # new records and new versions, ready for Store.put
    expect: Mapping[str, int]            # optimistic-concurrency guard
    findings: tuple[Finding, ...]        # identity lints (L-I-*)
def plan(candidate: Record, store: Store, schema: SchemaDoc, *, on_collision: str | None = None) -> WritePlan: ...
```

The store refuses bad states. The planner, a pure function of (candidate, store snapshot, schema),
decides good ones. P7 tests `relate` and `plan` against the identity table (§2.19). P1 needs only the
store.

### 6.6 The conformance suite

**Format:** declarative JSON scenario files [R04 O13], shared unchanged with P1's five backends.
The example below is one of four scenario files run against the prototype store [verified,
`run_scenarios.py`: 17 of 17 assertions pass]:

```json
{
  "khg_scenario": "khg-scenario/1.0.0",
  "id": "C2-S040",
  "title": "a put that leaves two asserted facts on one temporal key with definitely overlapping valid time is refused atomically",
  "requires": ["key_constraint", "atomic_batch", "valid_time"],
  "schema": "p2-gate.schema.json",
  "given": [
    {"at": "2026-10-01T00:00:01Z", "put": ["@fixture:ex:LouisXIII", "@fixture:ex:LouisXIV", "@fixture:ex:KingOfFrance", "@fixture:f:king-13"]}
  ],
  "when": [
    {"op": "put", "args": {"records": [{"@fixture": "f:king-14", "set": {"id": "f:king-14b"},
                                        "set_binding": {"b3": {"literal": {"datatype": "time", "time": "+1640-01-01T00:00:00Z", "precision": 11}}}}]},
     "then": {"error": "KHG-D016"}},
    {"op": "get", "args": {"id": "f:king-14b"}, "then": {"equals": null}},
    {"op": "by_key", "args": {"relation": "position_held", "key_bindings": [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}]},
     "then": {"select": "ids", "equals": ["f:king-13"]}}
  ]
}
```

- `given` runs `put` batches at controlled transaction times. `@fixture:` references and
  `set`/`drop`/`set_binding`/`drop_bindings`/`add_evidence` patches derive records from the gate
  fixture.
- `when` holds operations. Each has `then`: `equals` (optionally after a `select`: `ids`, `status`,
  `receipt`, `valid_time_kind`, `canonical`) or `error` (a code).
- **Runner:** `khg_contracts.store.conformance`, a pytest plugin parametrised over adapters found
  through the entry-point group `khg_contracts.stores`. An adapter is `make_store(schema, clock) ->
  Store`. The runner writes an EARL-shaped report: per scenario, `passed` \| `failed` \|
  `inapplicable` \| `untested` [R04 M9.2].

**v1 scenarios** (the four marked ✓ exist and pass):

| Group | Ids and titles |
|---|---|
| Writes | S001 put/get of every fixture record, canonical equality · S002 identical put is a no-op · S003 one invalid record in a batch writes nothing · S004 candidate refused (`D017`) · S005 validation code surfaced (`S003`) · S006 optimistic-concurrency mismatch |
| Versions | S010 version numbers and `recorded_at` increase · S011 appending evidence gives a new version · ✓ S012 closing an interval is accepted, changing a core binding is refused · S013 changed evidence refused · S014 illegal transition (`retracted → disputed`) refused · S015 superseded content frozen |
| Reads | S020 node in two roles returns the fact once · S021 role filter · S022 default filters hide superseded, quoted, deprecated, suppressed, goals, meta · S023 `incident` on a fact id · S024 order and pagination stable · S025 degree · S026 `find` at_least with a repeated role · S027 `find` exact · S028 `find` by typed literal (precision matters) · S029 goals with unbound slots via `find(kinds={"goal"})` |
| Time | S030 `get(as_at)` reconstructs a version · ✓ S031 as-at before a supersession, and the walk · S032 `valid_at` definite vs possible at year precision · S033 `valid_at` × `as_at` compose · ✓ S034 known vs possible validity (undated, since and period facts; year precision) |
| Keys | ✓ S040 overlapping put refused atomically · S041 key timeline ordered by start · S042 `by_key(valid_at)` gives the current holder · S043 preferred + normal on one key accepted; preferred first · S044 a `close_older` plan applied atomically · S045 a dispute plan applied · S046 second birthplace on a non-temporal key refused |
| Lifecycle | S050 walk branches on conflation · S051 backward walk · S052 retracting a supersession record restores `asserted` · S053 supersession cycle refused (`D012`) |
| Export | S060 `khg-json` equals the input canonically · S061 `hif` validates (vendored + profile) and decodes to equal C1 · S062 export `as_at` · S063 JSONL history holds every version |
| Goals | S070 binding a slot gives a new version with `agent_bound` evidence, same bid · S071 `satisfied` via `khg:fulfils` |
| Determinism | S080 the same puts on two fresh stores give byte-identical exports |

### 6.7 How P1's five backends implement C2

| Backend | Mapping | Lacks in v1 (capabilities reported) | Notes |
|---|---|---|---|
| **Incidence table** (PostgreSQL 18) | `fact_version(fact_id, version, relation, kind, status, rank, visibility, recorded_at, core_key, content_key, key_digest, valid tstzrange, payload jsonb)`; `binding(fact_id, version, bid, role, position, value_kind, entity_id, fact_ref, literal jsonb)`, PK (fact_id, version, bid) [R01 §3, REL §1b]; `current` view | none. The key invariant's plain branch can be native (`EXCLUDE … key_digest WITH =, valid WITH &&` on current asserted non-deprecated rows); the preferred-rank exception is checked in the adapter | `incident` = one probe on `binding(entity_id, role)`; the `key_digest` column is what makes a temporal key enforceable [R04 M3.3]. Definite intervals map to ranges; ±∞ to unbounded ranges |
| **Reified RDF 1.2** (relation-instance pattern) | fact version → IRI; `khg:relation`; one blank node per binding with `khg:role`, `khg:value`, `khg:position`, `khg:bid`; role predicates as sub-properties of `khg:role` so `incident` can tell roles from metadata [R01 §3]; meta records are ordinary instances; versions as distinct IRIs with `khg:recordedAt`. RDF 1.2 reifier or annotation export is a lossy projection via `primary` [R01 C1-R57] | `key_constraint` (SHACL 1.2 `sh:uniqueValuesFor` is non-temporal: adapter check), `atomic_batch` depends on the store (pyoxigraph: yes) | literals carry the C1 literal as a structured node (precision is not an XSD facet); rdflib 7.6 cannot parse RDF 1.2, so use pyoxigraph [R01 §3] |
| **Bipartite property graph** (Neo4j or Kùzu 0.11.3) | `(:Fact {id, version, …})-[:BINDS {role, bid, position}]->(:Entity\|:Literal\|:Special\|:Fact)`; versions as `:FactVersion` nodes linked to a `:Fact` identity node | `key_constraint` (key constraints are non-temporal; adapter check). Kùzu is archived and pinned [R04 M9] | roles in a property (open vocabulary) or relationship types (a fast, closed vocabulary) [PGE §4]; a k-hop fact query is a 2k-hop graph query |
| **TypeDB 3.x** | C1 relation → TypeQL relation; global role ρ → scoped role `r:ρ`; entity fillers → role players; **literal fillers → attributes owned by the relation** (attributes cannot play roles [R04 M2]); fact refs → relations playing roles; versions as relation instances with `version`/`recorded-at` attributes | `ordered_roles` (no native order: position needs an intermediate relation), `special_values` and `goals` (placeholder players, or a relation with no role players is deleted), `literal_fillers` (as owned attributes, so `incident` on a literal is not a role query), `key_constraint` (`@key` only on `owns`) | P1 must report these as mapping gaps, not fidelity losses [R04 risk 5] |
| **HIF** (file-backed in-memory index) | `decode(hif)` → MemoryStore; `export("hif")` writes back | `history` and `as_at` (HIF holds one snapshot) | the reference for fidelity |

---

## 7. C3: queue, verdicts, linter and action log (`khg-queue/1.0.0`, released with C1)

### 7.1 Queue item [verified against `khg-queue-1.0.0.schema.json`, both validators]

```json
{"kind": "queue_item", "khg_queue": "khg-queue/1.0.0", "item_id": "q-000001", "item_kind": "new_fact",
 "payload": {"kind": "fact", "id": "f:king-14", "relation": "position_held", "status": "candidate", "bindings": ["… as §2.21 …"], "evidence": ["…"]},
 "extraction": {"run_id": "smoke-1", "order_id": "o1", "position": 0, "seed": 0,
                "extractor": {"name": "p2-fixture-extractor", "version": "0.0.1"}, "doc": {"doc_id": "doc:louis-bio"}},
 "keys": {"content_key": "sha256:187ca682671fd4daaa6944fced4e05b7b9198b6bf0b4c29e6bb402d61bf9ecd2",
          "core_key": "sha256:5779b98f13640fbf96488b9834c5ce7e10f02902541882a23c2d43f84f93e916",
          "key_digest": "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96"},
 "submitted_at": "2026-10-01T00:00:03Z"}
```

(The `payload` above is abridged for the page. The validated file holds the full candidate record.)

| Field | Req. | Meaning |
|---|---|---|
| `kind`, `khg_queue` | yes | `"queue_item"`, `"khg-queue/1.0.0"` |
| `item_id` | yes | `q-…`, append-only; never reused |
| `item_kind` | yes | `new_fact` (payload: a fact with status `candidate`) · `goal_binding` (target: goal + bid; payload: a value with `agent_bound` evidence) · `merge_proposal` (payload: a candidate; target: the stored fact to refine or support) · `supersession_proposal` (target: the stored fact; payload: the replacement + reason) · `retraction_proposal` (target + reason) [R01 C3-R14, D-18] |
| `payload` | yes | a C1 record, validated in a second step against the bundled `khg-record` `fact` definition (no cross-document `$ref`: `fastjsonschema` cannot resolve one [verified]) |
| `target` | for proposals and bindings | `{store_id, version?, bid?}` |
| `extraction` | yes | `run_id`, `order_id`, `position` (insertion index), `seed`, `temperature`, `extractor {name, version}`, `model {id, version, provider}`, `prompt_id`, `skill_id`, `params`, `doc {doc_id, doc_sha256}` [R01 C3-R02]: everything P9's 3 runs × 2 orders need |
| `keys` | yes | `content_key`, `core_key`, `key_digest`, optional `event_hashes`. P9 stability is set agreement on these [R05 S-M1] |
| `submitted_at` | yes | timestamp |

The payload is a full C1 record (F9), so the linter, the planner and P9's scorer all read one
shape.

### 7.2 Queue states (a fold over the log; items are never edited)

`pending` → `linted` \| `rejected` (a structural violation) → `accepted` (inserted) \| `merged` (a
duplicate, refinement or support of a stored fact) \| `rejected` \| `needs_review`.
`needs_review` → `accepted` \| `merged` \| `rejected`. The submitter may `withdraw` before a decision.
`accepted`, `merged`, `rejected` and `withdrawn` are terminal. A log entry whose `state_before` is not
the fold's current state is `KHG-Q005`.

### 7.3 Verdicts (R04 O9: per candidate × evidence)

```json
{"kind": "verdict", "verdict_id": "v-000001", "item_id": "q-000001", "evidence_id": "e2",
 "content_key": "sha256:187ca682671fd4daaa6944fced4e05b7b9198b6bf0b4c29e6bb402d61bf9ecd2",
 "event_hash": "sha256:852ea9ca3abcc722e33e903dcdab88f5895cef077241fdf339ee1db0aeb55524",
 "label": "correct", "bindings": [{"bid": "b1", "label": "correct"}, {"bid": "b5", "label": "correct"}],
 "curator": {"type": "person", "id": "curator:smoke"}, "at": "2026-10-01T00:01:00Z"}
```

- The unit is a (candidate, evidence) pair, **keyed by `content_key` + `event_hash`**. A verdict
  therefore carries over to a re-extraction of the same passage by the same tool (INDRA keys
  curations by content hashes [R04 M7]).
- `label` ∈ `correct`, `no_relation`, `wrong_relation`, `wrong_role`, `wrong_filler`,
  `span_boundary`, `missing_participant` (R01's "incomplete"), `extra_participant`, `negated`,
  `hypothesis`, `other` (needs `text`).
- `bindings[]` gives per-`bid` labels (`correct`, `wrong_role` + `should_be_role`, `wrong_filler`,
  `extra_participant`). `missing[]` lists absent (role, value) pairs. This is what makes role
  accuracy measurable [R01 C3-R06].
- **Aggregation to a candidate verdict:** `correct` if any pair is `correct` and none is
  `wrong_relation` or `no_relation`. Otherwise the most severe label, in the order `no_relation` >
  `wrong_relation` > `wrong_role` > `wrong_filler` > `missing_participant` > `extra_participant` >
  `span_boundary` > `negated` > `hypothesis` > `other`, with ties broken by earliest `at`.

### 7.4 The linter: rules, ids and severities

**Structural lint** (the gate's "structural lint", store-free) is the validator's C and S layers
run on the candidate, with the relaxations candidates are allowed. Rule ids are the validator codes
themselves, so one registry serves both:

| Rule | Severity on a candidate | Note |
|---|---|---|
| all `KHG-C…` (structure) | violation → `rejected` | |
| `KHG-S001`, `S002`, `S004`, `S005`, `S006`, `S013`–`S016`, `S019`–`S023`, `S025` | violation | |
| `KHG-S003` (required role missing) | **warning**: candidate stays, proposed verdict `missing_participant` | status-dependent [R01 C1-R72] |
| `KHG-S011` (no evidence) | violation (`KHG-Q001`: a candidate needs evidence, a run id and an extractor version [R01 V47]) | |
| `KHG-S024` (co-occurrence constraint) | the schema's severity | |
| `KHG-D017` | not applicable (candidates belong in the queue) | |

**Identity lints** (store-aware; they run in `accept` through `identity.plan`):

| Rule | Severity | Action proposed |
|---|---|---|
| `L-I-001` duplicate of a stored fact | info | `merge` (evidence appended) |
| `L-I-002` refines a stored fact | info | `merge` (new version of the target) |
| `L-I-003` generalises a stored fact | info | `merge` (evidence appended, supports mapped) |
| `L-I-004` ambiguous: ≥ 2 targets of one class | warning | `needs_review` |
| `L-I-005` key conflict | warning | the relation's policy: `propose_supersession` / succession / dispute / reject |
| `L-I-006` negation conflict | warning | dispute |
| `L-I-007` matches a superseded or retracted fact | warning | `needs_review` |
| `L-I-008` only a possible overlap on a temporal key | info | none |

**Quality lints** (non-blocking; R01 C3-R09, R04 M7):

| Rule | What it reports |
|---|---|
| `L-Q-001` | evidence coverage: share of bindings supported by some evidence |
| `L-Q-002` | incomplete key (a key role absent or special): the fact is exempt from collisions |
| `L-Q-003` | a role that looks like provenance (`source`, `reference`, `evidence`, `stated_in`, or mapped to P248/P854): provenance is evidence, not a role (R01 I6) |
| `L-Q-004` | a repeated core role in a temporally keyed relation without `complete`: ambiguous composition semantics (R01 case 4a) |
| `L-Q-005` | arity outlier for the relation (P9 arity distribution) |
| `L-Q-006` | a `quoted` fact that no fact references |
| `L-Q-007` | an `attrs` key named `weight` (HyperNetX promotes it to the record weight [R03 row 11]) |

### 7.5 Action log entry [verified]

Three entries written by the smoke test, all valid against `khg-queue-1.0.0.schema.json` under both
validators:

```json
{"kind": "log_entry", "log_id": "l-000001", "parent_log_id": null, "target": {"item_id": "q-000001"}, "action": "submit", "state_before": null, "state_after": "pending", "actor": {"type": "agent", "id": "p2-fixture-extractor", "version": "0.0.1"}, "at": "2026-10-01T00:00:04Z"}
```
```json
{"kind": "log_entry", "log_id": "l-000002", "parent_log_id": "l-000001", "target": {"item_id": "q-000001"}, "action": "lint", "state_before": "pending", "state_after": "linted", "actor": {"type": "linter", "id": "khg-structural-lint", "version": "1.0.0"}, "at": "2026-10-01T00:00:05Z", "rule_set": {"id": "structural", "version": "1.0.0"}, "findings": [], "outcome": "pass"}
```
```json
{"kind": "log_entry", "log_id": "l-000003", "parent_log_id": "l-000002", "target": {"item_id": "q-000001"}, "action": "accept", "state_before": "linted", "state_after": "accepted", "actor": {"type": "person", "id": "curator:smoke", "version": null}, "at": "2026-10-01T00:00:07Z", "result": {"store_ids": ["f:king-14"], "tx": 3}, "before": null, "after": {"id": "f:king-14", "version": 1}, "plan_hash": "sha256:e5f3862166987cd0eed58b29b165d383d57d39467674020b2589cbafa2e1e32a"}
```

| Field | Meaning (who, what, when, why, before, after) |
|---|---|
| `log_id`, `parent_log_id` | append-only ids; the parent is the previous entry for the same item (MediaWiki `rev_parent_id` [R04 M7]), which makes replay well-defined |
| `target` | `{item_id, store_id?, content_key?}` |
| `action` | `submit`, `lint`, `accept`, `merge`, `reject`, `flag`, `auto_fix`, `propose_merge`, `propose_supersession`, `verdict`, `withdraw` |
| `state_before`, `state_after` | queue states (§7.2) |
| `actor` | `{type: agent\|linter\|person\|system, id, version}`: **who** |
| `mode` | `automatic` \| `manual` \| `semi_automatic` |
| `at` | **when** |
| `rule_set`, `findings[]` (`rule_id`, `rule_version`, `severity`, `path`, `value`, `message`), `outcome` | **what** was found (required on `lint`) |
| `reason` | **why** (required on `reject` and `flag`) |
| `before`, `after` | snapshots (or `{id, version}` references) of what the action changed (required on `accept` and `merge`) |
| `result`, `plan_hash` | store ids, transaction, and `digest("khg-plan/1", write plan)`, so a replay can check that it computed the same plan |

### 7.6 Replay

`queue.replay(items, log, schema, make_store) -> Store` re-runs every `accept` and `merge` in log
order through `identity.plan` and checks each `plan_hash`. A mismatch is `KHG-Q006`. Replay
determinism is what makes P9's order effects measurable rather than noise [R01 C3-R11].

---

## 8. The validator and the malformed-case list

### 8.1 Layers

```python
# khg_contracts/validate/__init__.py
Kind = Literal["auto", "hif", "khg-json", "khg-jsonl", "schema", "queue"]
@dataclass(frozen=True)
class Finding:
    code: str; severity: Literal["violation", "warning", "info"]; layer: str; path: str; message: str
@dataclass(frozen=True)
class Report:
    ok: bool; findings: tuple[Finding, ...]
    def codes(self) -> frozenset[str]: ...
def validate(obj_or_text: str | bytes | Mapping, *, kind: Kind = "auto", schema: SchemaDoc | None = None,
             candidate_ok: bool = False, backend: Literal["jsonschema", "fastjsonschema"] = "jsonschema") -> Report: ...
```

| Layer | Checks | Implementation | Stops later layers? |
|---|---|---|---|
| **J** strict JSON | UTF-8 without BOM; duplicate keys (`object_pairs_hook`); NaN/±Infinity (`parse_constant`); lone surrogates; empty input | stdlib `json` | yes |
| **H** HIF schema | the vendored `hif_schema_v0.1.0.json`, unchanged (F2) | draft-07, all errors | yes |
| **P** KHG profile | `khg-hif-1.0.0.schema.json` = `allOf` [vendored HIF by its absolute https `$id`, resolved from a local registry, never fetched; profile constraints on `attrs` and `metadata`] | draft-07 | yes |
| **D (decode)** | HIF → C1: unique declarations, resolvable incidence ends, structural node ids, schema hash, declared direction | Python | yes |
| **C** record schema | `khg-record-1.0.0.schema.json` (records dispatched by `kind` with `if`/`then`) | draft-07 | yes |
| **S** semantics | the record against the relation-type schema (§3.5) | Python | no: S and D report together |
| **D** cross-record | references, acyclicity, lifecycle pointers, supersession constraints, key invariant, derived fields, versions and transitions (store) | Python | n/a |
| **M** schema documents | `khg-schema-1.0.0.schema.json` + semantic checks (§3.5) | draft-07 + Python | |
| **Q** queue | `khg-queue-1.0.0.schema.json` + payload in a second step + the state fold | draft-07 + Python | |

**Two validators, one set of schemas (F5).** All P2 schemas are draft-07 and run unchanged under
`jsonschema` (all errors, paths, codes: the reporting backend) and `fastjsonschema` (a compiled
yes/no fast path for bulk validation such as P3a's corpus). Both accept every valid artefact in this
design (schemas, fixtures, exports, queue records) and agree on every document of the differential
corpus below [verified]. The 108-case malformed suite runs under `jsonschema`, which reports the
codes [verified]. Two portability rules were learnt from the prototype. First, **no cross-document
`$ref`** except the profile's reference to the vendored HIF schema by its absolute https `$id`:
`fastjsonschema` fails on a `tag:` URI document whose own fragments are then resolved [verified].
Second, **every choice between shapes is dispatched with `if`/`then` on its discriminating key,
never with `oneOf`/`anyOf`**. This covers record `kind`, the value kind (`entity`, `literal`,
`fact`, `special`), literal `datatype`, selector `type`, the goal-binding `unbound`, the schema
filler kind, constraint `type` and the time `model`. A `oneOf` failure is reported at the `oneOf`
itself, so a malformed literal would surface as "value not exactly one kind" (C001) instead of
"literal structure" (C004). Dispatch sends the failure to the subschema that owns it [verified:
MC47–MC56, MC98].

**Stable codes from JSON Schema failures.** P2-owned schemas carry `"x-khg-code"` annotations,
which draft-07 validators ignore. An annotation is either a code, which covers its whole subtree, or
a map from a keyword to a code (`"*"` means any keyword). The reporter follows the error's
`absolute_schema_path` from the root, resolving each `$ref` on the way (jsonschema leaves `$ref`
out of the path). It then reads the annotations from the failing keyword back towards the root and
takes the first one that applies to the keyword through which the failure passes. When none
applies, a per-layer keyword table decides:

- for C: `enum`/`const` → C002, `additionalProperties` → C009, `pattern` → C011, anything else → C010;
- for M: M015;
- for Q: Q008;
- P has no table, because every profile constraint is annotated.

The vendored HIF schema cannot be annotated (F2). H codes therefore come from a table keyed on
(keyword, instance-path pattern) whose last row is H009. Two properties are tested, not assumed:

- **Coverage** (`test_codes.py`): every constraint of every P2-owned schema, along every path that
  reaches it, resolves to a code: 74 occurrences in P, 848 in C, 161 in M and 153 in Q. Each of the
  vendored schema's 28 constraints matches a row of the H table [verified].
- **Neutrality**: annotations and dispatch change no verdict. The differential corpus is the 13
  positive artefacts plus 24,000 seeded mutations of them (deleted keys, retyped values, values of
  other kinds, extra keys). The original and the refactored schemas give the same accept/reject on
  all 24,013 documents under both validators: 0 disagreements [verified].

In the gate manifest each case lists one expected layer and code. The test asserts that the case is
rejected at that layer and that the code is among those reported, since a malformed input may
legitimately raise several (MC28 also raises P011, MC66 also raises S003).

### 8.2 Code registry (v1)

| Codes | Meaning |
|---|---|
| `KHG-J001`–`J005` | not JSON or empty · BOM or invalid UTF-8 · duplicate key · NaN/Infinity · lone surrogate |
| `KHG-H001`–`H009` | no `incidences` · extra top-level key · extra record-level key · `attrs` or `metadata` not an object · `direction` not head/tail · record missing `edge`/`node` · id of the wrong type · `network-type` outside the HIF enum · another member of the wrong JSON type (the document or a record not an object, `incidences`/`nodes`/`edges` not an array, `weight` not a number) |
| `KHG-P001`–`P015` | a required top-level member (`network-type`, `metadata`, `nodes`, `edges`) or metadata declaration missing · non-string id · id grammar · misuse of the reserved `_:` prefix (an entity id using it, or a value node id without it or not matching its kind) · incidence without `attrs`, `role` or `khg:bid`, or a malformed `khg:bid` · `role` not one non-empty string · `network-type` not allowed by the profile (`asc`) · forbidden metadata key (`default_attrs`, an unknown `khg-*`/`hif-*` key) · declaration value malformed or not the pinned one (unpinned `hif-schema`, wrong sha) · directed file: incidence without `direction` (or with `khg:direction`) · non-directed file: record-level `direction`, or `khg:direction` not head/tail · edge without `attrs`, `khg:relation` or `khg:status`, or one of its `khg:` attributes malformed · `khg:kind` missing or unknown, the kind's payload (`khg:literal`, `khg:unbound`, `khg:ref`) missing, or a node without `attrs` · unknown `khg:` attrs key or reserved key `roles` · `role-position` not an integer ≥ 1 |
| `KHG-C001`–`C011` | value not exactly one kind · enum violation · confidence not `{value, scale}` · literal structure (unit, precision range, bounds, lexical pattern) · `unbound` outside a goal · status needs `status_ref` (or an abandoned goal its `closed_reason`) · evidence structure (extracted without source/activity/selectors; inferred without inference; selector) · deprecated without `rank_reason` · unknown field · required field missing, wrong JSON type or out of range · identifier, bid, timestamp, hash, version or extension key not in its lexical form |
| `KHG-S001`–`S025` | relation undeclared · role not allowed · required role missing · `max` exceeded · filler kind/type/datatype or special value not allowed (includes a fact reference where no fact is accepted) · literal lexical/range · no bindings · (S008 merged into S005) · empty valid time · confidence scale undeclared or out of range · asserted fact without supporting evidence · (S012 reserved) · `novalue` with another filler · duplicate filler in an unordered role · positions · direction contradicts the declaration · rule tail ∩ head ≠ ∅ · goal omits a required role · repeated variable · id not NFC · span empty/reversed or quote ≠ text · evidence supports an unknown bid · `precision_min`/units · co-occurrence constraint (schema severity) · duplicate bid |
| `KHG-D001`–`D017` | duplicate declaration or record · unresolved node/entity/fact reference · undeclared edge · (D004 reserved) · structural node id mismatch · (D006 reserved) · an id names an entity and a fact · nesting cycle · schema id, hash or major version unknown · lifecycle pointer inconsistent · supersession constraint by reason · supersession cycle · version not a refinement / evidence mutated · illegal status transition · derived fields mismatch · key invariant · `candidate` outside the queue |
| `KHG-M001`–`M015` | relation with no roles · role used twice · bad key role · version not semver · unknown type or relation in a filler · unknown datatype · bad time model or time-slot declaration (`max` ≠ 1, a filler other than one time literal) · reserved `khg:` id · role not in vocabulary · `max < min` · temporal key without an interval model · `primary` not core · duplicate relation id · `complete` on an optional role · other structural violation of a schema document (missing or unknown field, wrong type, value outside an enum) |
| `KHG-Q001`–`Q008` | candidate lacks an extraction field (run id, order id, position, extractor name and version, source document) · payload status not `candidate` · unknown record kind, item kind or action · lint entry without rule set, findings or outcome · state transition not following the fold (wrong `state_before`, or a move §7.2 does not allow) · replay mismatch · log names a missing item · other structural violation of a queue record |

### 8.3 The malformed-case list (the gate's test list) [verified]

All 108 cases below run in the prototype's layered validator (`run_malformed.py`). Each is
rejected at the layer shown and reports the code shown:
- J codes come from the strict parser;
- H, P, C, M and Q codes come from the §8.1 reporter;
- decode, S, D, M-semantic and fold codes come from the Python checks.

The expected code is also the first one reported in every case. Only MC28 and MC66 report a second
code as well (P011 and S003, both legitimate). Sources name the R01 candidate (V…), the R02 probe
case or the R03 library case.

| Id | Malformed case | Layer | Code |
|---|---|---|---|
| MC01 | zero-byte file (R02 case 34) | J | `KHG-J001` |
| MC02 | not JSON: truncated document | J | `KHG-J001` |
| MC03 | duplicate key inside one attrs object (R02 case 36) | J | `KHG-J003` |
| MC04 | NaN literal (R02 case 35, R03 c22, R01 V19) | J | `KHG-J004` |
| MC05 | lone surrogate escape in a string | J | `KHG-J005` |
| MC06 | no incidences (R01 V01, R02 case 31) | H | `KHG-H001` |
| MC07 | top-level 'version' key (R01 V02, R02 case 04) | H | `KHG-H002` |
| MC08 | top-level 'roles' vocabulary (R02 case 05) | H | `KHG-H002` |
| MC09 | top-level '$schema' (R02 case 06) | H | `KHG-H002` |
| MC10 | record-level 'role' on an incidence (R01 V03, R02 case 11) | H | `KHG-H003` |
| MC11 | record-level 'relation' on an edge (R02 case 13) | H | `KHG-H003` |
| MC12 | record-level 'type' on a node (R02 case 14) | H | `KHG-H003` |
| MC13 | incidence attrs is a string (R02 case 10) | H | `KHG-H004` |
| MC14 | direction 'treatment' (R01 V05, R02 case 12) | H | `KHG-H005` |
| MC15 | incidence without node (R01 V04) | H | `KHG-H006` |
| MC16 | id of type float 1.5 (R02 case 18) | H | `KHG-H007` |
| MC17 | id of type boolean (R02 case 19) | H | `KHG-H007` |
| MC18 | id null (R02 case 20) | H | `KHG-H007` |
| MC19 | network-type 'knowledge-hypergraph' (R02 case 26) | H | `KHG-H008` |
| MC20 | metadata without the khg-profile declaration (R01 V07) | P | `KHG-P001` |
| MC21 | no metadata at all | P | `KHG-P001` |
| MC22 | integer ids (R02 cases 15-17, 22) | P | `KHG-P002` |
| MC23 | empty-string id (R02 case 21) | P | `KHG-P003` |
| MC24 | incidence of a fact without a role (R01 V08) | P | `KHG-P005` |
| MC25 | list-valued role (R01 V09, R02 case 09) | P | `KHG-P006` |
| MC26 | empty role string (R01 V09) | P | `KHG-P006` |
| MC27 | legacy 'roles' key beside 'role' (R01 V20) | P | `KHG-P014` |
| MC28 | network-type 'asc' (R03 D8, c04) | P | `KHG-P007` |
| MC29 | metadata.default_attrs (R03 D7, c20) | P | `KHG-P008` |
| MC30 | directed file, an incidence without direction (R01 V12, R02 case 23, R03 c14) | P | `KHG-P010` |
| MC31 | undirected file carrying record-level direction (R01 V13, R02 cases 24-25) | P | `KHG-P011` |
| MC32 | fact edge without khg:relation (R01 V14) | P | `KHG-P012` |
| MC33 | edge without khg:kind (R01 V40) | P | `KHG-P013` |
| MC34 | unknown khg: key in incidence attrs | P | `KHG-P014` |
| MC35 | literal node whose id lacks the _: prefix | P | `KHG-P004` |
| MC36 | entity node id using the reserved _: prefix | P | `KHG-P004` |
| MC37 | hif-schema pinned to the moving 'main' URL | P | `KHG-P009` |
| MC38 | role-position 0 | P | `KHG-P015` |
| MC39 | node declared twice (R01 V16, R03 c19) | D (decode) | `KHG-D001` |
| MC40 | edge declared twice (R01 V16) | D (decode) | `KHG-D001` |
| MC41 | incidence names an undeclared node (R01 V17, R02 case 28) | D (decode) | `KHG-D002` |
| MC42 | incidence names an undeclared edge (R02 case 29) | D (decode) | `KHG-D003` |
| MC43 | literal node id does not match its value | D (decode) | `KHG-D005` |
| MC44 | schema hash in metadata does not match the schema | D (decode) | `KHG-D009` |
| MC45 | incidence direction contradicts the role's declared direction (R01 V38) | S (at decode) | `KHG-S016` |
| MC46 | fact-ref node pointing to a missing edge (R01 V18) | D | `KHG-D002` |
| MC47 | binding value with two kinds (entity and literal) | C | `KHG-C001` |
| MC48 | status outside the lifecycle enum (R01 V36) | C | `KHG-C002` |
| MC49 | confidence as a bare number (R01 V32) | C | `KHG-C003` |
| MC50 | quantity without unit (R01 V26) | C | `KHG-C004` |
| MC51 | time precision 15 | C | `KHG-C004` |
| MC52 | UNBOUND value in a fact (R01 V34) | C | `KHG-C005` |
| MC53 | status superseded without status_ref (R01 V37) | C | `KHG-C006` |
| MC54 | extracted evidence without selectors and activity (R01 V47, record side) | C | `KHG-C007` |
| MC55 | rank deprecated without rank_reason | C | `KHG-C008` |
| MC56 | span selector with a negative start | C | `KHG-C007` |
| MC57 | record-level key outside the format (e.g. 'weight') | C | `KHG-C009` |
| MC58 | relation not declared (R01 V21) | S | `KHG-S001` |
| MC59 | role not allowed for the relation (R01 V22) | S | `KHG-S002` |
| MC60 | required role missing on an asserted fact (R01 V23) | S | `KHG-S003` |
| MC61 | role bound more often than max (R01 V24) | S | `KHG-S004` |
| MC62 | entity of the wrong type (R01 V25) | S | `KHG-S005` |
| MC63 | literal where an entity is expected (R01 V25) | S | `KHG-S005` |
| MC64 | time literal with month 13 (R01 V26) | S | `KHG-S006` |
| MC65 | day set below year precision (R01 V26) | S | `KHG-S006` |
| MC66 | fact with no bindings (R01 V27) | S | `KHG-S007` |
| MC67 | fact reference in a role that takes no facts (R01 V29) | S | `KHG-S005` |
| MC68 | valid time starts after it ends (R01 V30) | S | `KHG-S009` |
| MC69 | confidence scale not declared (R01 V32) | S | `KHG-S010` |
| MC70 | confidence outside its scale (R01 V32) | S | `KHG-S010` |
| MC71 | asserted fact with no evidence (R01 V33) | S | `KHG-S011` |
| MC72 | novalue and a concrete value in one role (R01 V35) | S | `KHG-S013` |
| MC73 | the same filler twice in an unordered role (set semantics) | S | `KHG-S014` |
| MC74 | ordered role with a gap in positions | S | `KHG-S015` |
| MC75 | position on an unordered role | S | `KHG-S015` |
| MC76 | goal omits a required role instead of leaving it unbound | S | `KHG-S018` |
| MC77 | one unbound variable used twice in a goal | S | `KHG-S019` |
| MC78 | id not in Unicode NFC | S | `KHG-S020` |
| MC79 | evidence supports an unknown binding id | S | `KHG-S022` |
| MC80 | precision below the role's precision_min | S | `KHG-S023` |
| MC81 | unit not allowed for the role | S | `KHG-S023` |
| MC82 | the same binding id twice in one fact | S | `KHG-S025` |
| MC83 | somevalue where the role forbids it | S | `KHG-S005` |
| MC84 | nesting cycle (R01 V28) | D | `KHG-D008` |
| MC85 | status_ref points at a record of the wrong kind (R01 V37) | D | `KHG-D010` |
| MC86 | supersession cycle (R01 V37) | D | `KHG-D012` |
| MC87 | correction between facts of different relations (R01 V37) | D | `KHG-D011` |
| MC88 | two asserted facts, same key binding, overlapping valid time (R01 V42) | D | `KHG-D016` |
| MC89 | stored derived fields disagree with the bindings (R01 V15) | D | `KHG-D015` |
| MC90 | a candidate inside a store document (queue boundary, F9) | D | `KHG-D017` |
| MC91 | entity referenced but not declared in a complete document (R01 V17) | D | `KHG-D002` |
| MC92 | one id names both an entity and a fact | D | `KHG-D007` |
| MC93 | relation with no roles (R01 V43) | M | `KHG-M001` |
| MC94 | a role used twice in one relation (R01 V44) | M | `KHG-M002` |
| MC95 | key names a role the relation does not use (R01 V44) | M | `KHG-M003` |
| MC96 | key built on a time-slot role | M | `KHG-M003` |
| MC97 | schema version not semver (R01 V45) | M | `KHG-M004` |
| MC98 | unknown datatype (R01 V46) | M | `KHG-M006` |
| MC99 | unknown entity type in a filler (R01 V46) | M | `KHG-M005` |
| MC100 | complete: true on an optional role | M | `KHG-M014` |
| MC101 | time model names a role that is not a time slot | M | `KHG-M007` |
| MC102 | user schema declares a relation in the reserved khg: namespace | M | `KHG-M008` |
| MC103 | temporal key on a relation without an interval time model | M | `KHG-M011` |
| MC104 | candidate without `run_id` (R01 V47) | Q | `KHG-Q001` |
| MC105 | candidate payload with status `asserted` | Q | `KHG-Q002` |
| MC106 | unknown `item_kind` (R01 V48) | Q | `KHG-Q003` |
| MC107 | lint log entry without `findings` | Q | `KHG-Q004` |
| MC108 | log entry whose `state_before` does not follow the fold (e.g. `accepted` → `pending`) (R01 V48) | Q | `KHG-Q005` |

MC104–MC107 run against `khg-queue-1.0.0.schema.json`, and MC108 runs through the fold over the log
(`fold_check`: a wrong `state_before`, or a move that §7.2 does not allow) [verified]. Beyond this
list, 28 registry probes exercise every §8.2 clause the list does not already reach (for example
H009, P012, C010, C011, M015, Q008). Each reports its clause's code [verified: `run_code_probes.py`].
Two further cases are **extended**
(not in the gate list, because they need a store or a rule relation): MC109, a replay that differs
from the store (R01 V49, `KHG-Q006`, run in the store tests); and MC110, a rule hyperarc with a node
in both tail and head (R01 V39, `KHG-S017`).

**Positive list** (must validate with no violation): the directed and undirected gate fixtures in
both C1 and HIF; the gate schema; the migrated KB sample (C1 and HIF) [verified]. Also, through
`import_foreign`: R02 cases 01 and 02 and R03 cases c05, c06, c07 and c25. **R01 V10**, two incidence
records for one (edge, node) pair, is a positive case under this design (§4.2). R01 V11 cannot
occur. R01 V31 (a transaction interval ending before it starts) cannot occur, because transaction
intervals are derived.

---

## 9. C5: scorers (`khg-scorers/1.0.0`, released with C1)

### 9.1 Conventions shared by the four scorers [R05 §1]

- **Deterministic, no LLM by default.** LLM judges are adapters with a named judge, a pinned prompt,
  and their numbers reported under the judge's name (D-C5-13, D-C5-16).
- **Canonical values.** Entities match by id, modulo redirects. Literals match per §2.5, with
  `truncate_to_gold` for dates by default [R05 §2.2.1], which is exactly C1's value refinement
  v_pred ⊑ v_gold. `somevalue` and `novalue` match only themselves.
- **Arity bins** come from C1's `derived.arity`, bins `1`, `2`, `3`, `4`, `5+`. Recall is binned by
  gold arity and precision by predicted arity [R05 §1 item 5]. `statement_arity` bins are also
  reported for comparison with the literature.
- **Stamps** on every report: `khg-record`, `khg-scorers`, C4 corpus and question-set versions,
  split, and the config hash (C5-R01).
- **Per-item outputs** keyed by fact id, qid or doc id (P8's join); empty-set flags `no_predictions`,
  `no_gold` and `both_empty`; three averages; a percentile bootstrap with 1,000 resamples, seed 0 and a
  95 % interval, plus a paired bootstrap for comparisons (D-C5-18).
- Assignment uses pure-Python Hungarian matching, with SciPy optional (`[fast]` extra) and a
  brute-force cross-check in tests (D-C5-17).

### 9.2 API

```python
# khg_contracts/scorers/extraction.py
@dataclass(frozen=True)
class ExtractionConfig:
    literal_rule: Literal["truncate_to_gold", "exact"] = "truncate_to_gold"
    use_alternatives: bool = True
    levels: tuple[str, ...] = ("strict", "core", "arg_i", "arg_c", "pooled", "pairwise")   # E-M1..E-M8
    core_from: Literal["core_slot", "key"] = "core_slot"          # E-M2: C1 core_key by default
    averaging: tuple[str, ...] = ("micro_doc", "macro_relation", "macro_arity")
    ign_seen: bool = False                                           # E-M11
    soft: SoftConfig | None = None                                   # E-M12, opt-in only
    bootstrap: BootstrapConfig = BootstrapConfig()
    preset: Literal["hyperred_quintuplet", "text2nkg"] | None = None

def score_extraction(gold: Iterable[GoldDoc], runs: Sequence[Run], schema: SchemaDoc,
                     config: ExtractionConfig = ExtractionConfig()) -> ExtractionReport: ...
def score_stability(runs: Sequence[Run], schema: SchemaDoc, *, keys: tuple[str, ...] = ("content_key", "core_key"),
                    gold: Iterable[GoldDoc] | None = None) -> StabilityReport: ...     # S-M1..S-M7

# khg_contracts/scorers/completion.py
@dataclass(frozen=True)
class CompletionConfig:
    filter: Literal["exact", "monotone", "time_aware"] = "exact"     # monotone = C1 refinement ⊑; time_aware = definite validity at as_of
    also_report: tuple[str, ...] = ("monotone", "time_aware")
    positions: Literal["all_roles", "primary", "core", "qualifiers"] = "all_roles"
    rank: Literal["tie_exact_expectation", "realistic", "optimistic", "pessimistic", "sort_order"] = "tie_exact_expectation"
    denominators: tuple[str, ...] = ("per_task", "per_fact", "macro_arity")
    hits_at: tuple[int, ...] = (1, 3, 10)
    calibration: CalibrationConfig = CalibrationConfig(bins=15, binnings=("equal_width", "equal_mass"), min_bin_queries=100)
    preset: Literal["hype", "stare", "hyper"] | None = None          # replication presets for P3b

def build_queries(facts: Iterable[Record], schema: SchemaDoc, *, positions: str = "all_roles") -> list[CompletionQuery]: ...
def build_filter_index(splits: Mapping[str, Iterable[Record]], schema: SchemaDoc) -> FilterIndex: ...
def rank_stats(scores: Mapping[str, float], target: Value, known: FilterIndex, query: CompletionQuery) -> RankStats: ...
def score_completion(queries: Iterable[CompletionQuery], outputs: Iterable[RankStats],
                     config: CompletionConfig = CompletionConfig()) -> CompletionReport: ...

# khg_contracts/scorers/retrieval.py
@dataclass(frozen=True)
class RetrievalConfig:
    ks: tuple[int, ...] = (1, 3, 5, 10, 20)
    answer_match: Literal["canonical", "text"] = "canonical"
    ndcg_discount: Literal["log2(i+1)"] = "log2(i+1)"
    breakdowns: tuple[str, ...] = ("hops", "required_arity", "source_class")
    budget_curve: tuple[int, ...] | None = (500, 1000, 2000, 4000, 8000)
def score_retrieval(questions: Iterable[RetrievalQuestion], responses: Iterable[RetrievalResponse],
                    facts: Mapping[str, Record] | Store | None = None, config: RetrievalConfig = RetrievalConfig()) -> RetrievalReport: ...

# khg_contracts/scorers/memory.py
@dataclass(frozen=True)
class MemoryConfig:
    text_fallback: Literal["alias_match", "none"] = "alias_match"
    tolerance_default: float | None = None
def derive_memory_gold(trace: MemoryTrace, question: MemoryQuestion, schema: SchemaDoc) -> MemoryGold: ...
def score_memory(questions: Iterable[MemoryQuestion], responses: Iterable[MemoryResponse], traces: Mapping[str, MemoryTrace],
                 schema: SchemaDoc, config: MemoryConfig = MemoryConfig()) -> MemoryReport: ...
```

Headline numbers:

- **P9:** `strict` P/R (E-M1), with `arg_c` (E-M5) beside it; **role accuracy** = E-M6 over one
  value-first Hungarian alignment; stability S-M1, S-M5 and S-M7 on `content_key`, and S-M1 on
  `core_key`.
- **P3b:** preset per model, then tie-exact MRR and macro-over-arity; calibration C-M7 per arity bin.
- **P10 and P4:** `support_success@10`, `mrr@10`, answer EM on canonical ids, the cost block, and
  `binding_coverage@k` across conditions.
- **P7:** strict memory accuracy with the stale rate split into `expired` and `retracted` [R05 §5.2].

### 9.3 The question-set shapes P3a fills (C4 draft, expressed in C1)

All gold content is C1: facts are C1 fact records, values are C1 values, and arities are C1
`derived.arity`. Each item has `kind`, a stable id, `split` and a question-set version (C5-R06).

| Item | Fields (beyond id, split, version) |
|---|---|
| `extraction_doc` | `text` (NFC), `text_sha256`, `annotation {method, exhaustive, annotators}`, `gold` (C1 facts whose evidence has position selectors over `text`), `alternatives {fact_id: [facts]}`, `entity_aliases`, `seen_core_keys` |
| `completion_query` | `fact_id`, `target {bid, role, slot, value}`, `as_of`, `candidate_universe`, `inductive {unseen_context_entities, unseen_relation}`. It references the C1 fact and its masked binding instead of copying the bindings |
| `retrieval_question` | `text`, `template_id`, `answer {mode: single\|set, values}`, `aliases`, `support {sets: [[fact ids]]}` (alternative minimal sets), `required_edge {fact_id, relation, arity, roles_used}`, `hops`, `source_class` (`binary`\|`n-ary`), `as_of`, `answerable`, `provenance {generator, generator_version, verified, verifiers}` |
| `memory_trace` | `schema {id, version, sha256}`, `events: [{step, tx_time, put: [C1 records or new versions], text?}]`. **A trace is a C2 put log.** Assert = put a fact. The world changing = put a new version that adds `end_time`, or a `close_older` plan. Belief revision = put a `khg:supersedes` batch |
| `memory_question` | `trace_id`, `ask_after_step`, `subtype` (`current_value`\|`past_value`\|`change_detection`\|`count_changes`\|`abstention`), `text`, `as_of` (`end_of_trace` \| instant), `as_at` (`after_step` \| instant), `key {relation, key_bindings, target_role}`, `answer {mode, values}`, `stale_values [{value, fact_id, kind: expired\|retracted}]`, `future_values`, `support {current, history}`, `aliases`, `answerable`, `tolerance` |

**The memory gold is computed from the contract, not typed in.** `derive_memory_gold` replays the
trace into a `MemoryStore` and then reads:

- `V_cur` = target-role values of `by_key(key, valid_at=as_of, as_at=τ)`;
- `V_old/expired` = values of facts on the key timeline whose definite validity ended before `as_of`;
- `V_old/retracted` = values of facts that were asserted at some earlier as-at but are superseded or
  retracted at τ;
- `V_fut` = values valid only after `as_of`.

P3a's stored `stale_values` are checked against this (`C5-E001` on disagreement). The distinction
F7 draws, ended versus superseded, therefore reaches the memory scorer mechanically: an `expired`
answer to an as-of-now question is stale, while the same value to an as-of-past question is correct.

### 9.4 Tests shipped with C5 (F14)

| File | Tests | Expected values from |
|---|---|---|
| `tests/scorers/test_extraction_r05.py` | E1–E11 (perfect, no predictions, both empty, arity 3 vs 4, role swap, partial swap, wrong relation, duplicate, 1-vs-2 gold, Hungarian vs greedy, date precision, core vs strict, per-arity recall) | R05 §2.7, recomputed by `research/probes/scorers/c5_reference_cases.py` |
| `tests/scorers/test_stability_r05.py` | S1–S4 (three runs, all empty, order effect, gold partition) | R05 §2.7 |
| `tests/scorers/test_completion_r05.py` | C1–C8 (no ties, filtering, four-way tie with tie-exact E[RR] = 25/48, denominators 0.40/0.55, time-aware filter, monotone filter, ECE 0.13 and Brier 0.1965, ECE by arity) | R05 §3.7 and `c5_reference_cases.out.json` |
| `tests/scorers/test_retrieval_r05.py` | R1–R8 (one support set incl. nDCG 0.650921, alternative sets, answer text, entity set, joint, gated EM, cost percentiles, the substring trap) | R05 §4.7 |
| `tests/scorers/test_memory_r05.py` | M1–M8 (current, stale, hedged, abstention, as-of past, aggregate, ranked efficacy, tolerance) | R05 §5.7 |
| `tests/scorers/test_c1_semantics.py` | M9 `derive_memory_gold` on a close_older trace (expired) and a supersession trace (retracted); E12 the monotone filter equals C1 ⊑; E13 `truncate_to_gold` equals C1 value refinement | this design |

---

## 10. Package layout (F12)

```
pyproject.toml                         # at the repository root; distribution "khg-contracts", import "khg_contracts"
src/khg_contracts/
  __init__.py                          # __version__, public API re-exports
  errors.py                            # KHGError and subclasses; the code registry (codes.json)
  _json.py                             # strict loads, canonical JSON, digest(domain, payload)
  ids.py                               # id grammars, NFC checks, reserved prefixes
  c1/  model.py values.py literals.py timewin.py derived.py canonical.py lifecycle.py
  identity.py                          # refines, relate, presumed_interval, plan, WritePlan
  schema/  lang.py hypergraph.py builtins.json
  schemas/                             # JSON Schemas (draft-07) shipped as package data
    hif_schema_v0.1.0.json  HIF-LICENSE.txt  PROVENANCE.md   # vendored, blob e2105bb, Zenodo 10.5281/zenodo.17257719
    khg-record-1.0.0.schema.json  khg-schema-1.0.0.schema.json  khg-hif-1.0.0.schema.json
    khg-queue-1.0.0.schema.json   khg-scenario-1.0.0.schema.json
  validate/  __init__.py layers.py semantic.py codes.py    # codes.py: x-khg-code reporter, H table, coverage()
  hif/  codec.py foreign.py xgi.py hnx.py context.py
  store/  protocol.py memory.py conformance/ (plugin.py, runner.py, scenarios/*.json)
  queue/  records.py lint.py log.py replay.py
  scorers/  _common.py hungarian.py bootstrap.py extraction.py stability.py completion.py retrieval.py memory.py
  migrate/  v0_sample.py registry.py
  fixtures/  p2-gate.schema.json fixture-directed.khg.json fixture-undirected.khg.json   # also used by the HIF proposal
  cli.py
tests/
  conftest.py                          # autouse no_network fixture; hash-seed helper
  gate/  test_roundtrip.py test_malformed.py test_smoke.py test_determinism.py malformed/ positive/
  c1/ test_literals.py test_timewin.py test_derived.py test_refinement.py
  identity/ test_relate.py cases.json  # the table of §2.19
  hif/ test_codec.py test_foreign.py test_profile_schema.py
  loaders/ test_xgi.py test_hnx.py test_native_ops.py
  library_evidence/ test_native_hif.py # marker library_evidence
  store/ test_conformance.py           # runs every scenario on every registered adapter
  queue/ test_queue.py test_lint.py test_replay.py test_fold.py
  validate/ test_codes.py              # every constraint maps to a code; one probe per §8.2 clause
  scorers/ (§9.4)
```

**Public API** (`khg_contracts`): `load`, `dump` (C1 JSON/JSONL); `validate`; `canonicalise`;
`digest`; `hif.encode`, `hif.decode`, `hif.import_foreign`; `hif.xgi.to_xgi`/`from_xgi`;
`hif.hnx.to_hnx`/`from_hnx`; `schema.load_schema`, `schema.schema_hypergraph`; `identity.refines`,
`relate`, `plan`; `store.Store`, `store.MemoryStore`; `queue.Queue`; `scorers.*`; `migrate.migrate`.

**Dependencies.**

- Core: `jsonschema>=4.18,<5`. It is the reporting validator; its `referencing`/`rpds-py`
  dependency is accepted (F12; R04 notes rpds-py 2026.6 needs Python ≥ 3.11, and pip picks an older
  wheel on 3.10).
- Extras: `xgi = ["xgi==0.10.2"]`; `hypernetx = ["hypernetx==2.4.3", "pandas>=2,<3"]`;
  `fast = ["fastjsonschema>=2.19", "scipy>=1.11"]`; `test = ["pytest>=8", "fastjsonschema>=2.19"]`.
- MIT licence. The vendored HIF schema keeps its MIT notice.

**CLI** (`[project.scripts]`):

- `khg-validate FILE [--kind auto|hif|khg-json|khg-jsonl|schema|queue] [--schema S] [--candidates] [--json]`
  exits 0 when valid, 1 when invalid, 2 on a usage error.
- `khg-convert IN OUT --to hif|khg-json|khg-jsonl [--schema S] [--foreign]`
- `khg-migrate IN OUT [--from v0-sample] [--weight-as-confidence SCALE]`
- `khg-conformance --store module:factory [--report earl.json]`
- `khg-score {extraction,stability,completion,retrieval,memory} --config C …`

**CI.** Three jobs, all offline once installed:

1. Python 3.10 core only: `pip install -e ".[test]" && pytest -q -m "not library_evidence"`, where
   the loader tests skip through `importorskip`.
2. Python 3.11 full: `pip install -e ".[test,xgi,hypernetx,fast]" && pytest -q`.
3. The same as job 2 under `PYTHONHASHSEED=0` and `=1` for `test_determinism.py`.

The gate is job 2's `tests/gate`.

---

## 11. Versioning and migration

### 11.1 Identifiers

| Artefact | Format id (in files) | JSON Schema `$id` | Versioned with |
|---|---|---|---|
| C1 record format | `khg-record/1.0.0` (header `khg`) | `tag:khg-contracts,2026:schema/khg-record/1.0.0` | itself |
| schema language | `khg-schema/1.0.0` | `…/khg-schema/1.0.0` | C1 |
| HIF profile | `khg-hif/1.0.0` (metadata `khg-profile`) | `…/khg-hif/1.0.0` | C1 |
| generic roles convention | `hif-roles` `1.0.0` (metadata `hif-roles-version`) | none (a convention) | independently; minor bumps only |
| C3 | `khg-queue/1.0.0` | `…/khg-queue/1.0.0` | C1 (lockstep, PLAN §7) |
| C2 | `khg-store/1.0.0` (`StoreInfo.interface_version`) | scenarios: `khg-scenario/1.0.0` | its own semver |
| C5 | `khg-scorers/1.0.0` | none | C1 (lockstep) |
| relation-type schemas | `<id>/<semver>` (e.g. `p2-gate/1.0.0`), each record's `typed_under` | none | the schema author |
| hash domains | `khg-content-key/1`, `khg-core-key/1`, `khg-key-digest/1`, `khg-event/1`, `khg-literal-node/1`, `khg-special-node/1`, `khg-schema/1`, `khg-plan/1` | none | change only with a C1 major version |

`tag:` URIs (RFC 4151) are valid identifiers that need no domain. They are never fetched: schemas
resolve from package data. If the programme later hosts schemas, the `$id`s change in a major version.

### 11.2 Semver rules

- **Major:** a previously valid document becomes invalid or changes meaning. This includes any
  change to canonicalisation or a hash domain, since keys change. It ships `migrate/vN_to_vN+1.py`
  and reruns every consumer gate (PLAN §7–§8).
- **Minor:** new optional fields, value kinds, datatypes, enum values, meta relations or capability
  flags. Old documents stay valid with the same meaning. An old reader rejects documents that use
  the new features, by version check (`KHG-D009`), rather than misreading them.
- **Patch:** documentation, bug fixes and new tests, with no schema change.

A reader accepts documents of its own major version whose minor is ≤ its own. A newer minor is
rejected with `KHG-D009` and the message "upgrade khg-contracts".

### 11.3 Migrating the KB's `schemas/sample.hif.json` (v0 → `khg-record/1.0.0`) [verified]

`khg-migrate schemas/sample.hif.json sample.khg.json --from v0-sample` (prototype: `migrate_sample.py`):

| v0 feature | Migration | Report |
|---|---|---|
| `incidences[].attrs.role` (single string) | unchanged, since it is already the convention's key; one binding per incidence, bids `b1…` in canonical order | none |
| `direction` per incidence | a generated usage `direction` where every observation agrees (here all of them) | none |
| `edges[].attrs.relation` | `relation` (C1) / `khg:relation` (HIF) | none |
| `edges[].attrs.arity` | dropped (derived). Stored values checked against C1 arity: f1 4, f2 3, f3 2, all equal | `MIGRATE-I02` |
| `edges[].attrs.source` | an evidence record `{type: imported, mode: automatic, source: {doc_id}}` | none |
| `edges[].attrs.valid-from` (f1) | a `start_time` binding (time, day precision) under a generated interval time model; direction `tail`, chosen by the migration following the sample's own convention | `MIGRATE-W01` |
| `edges[].weight` (0.95, 0.80, 1.0) | `extensions["hif:weight"]`, re-emitted as HIF `weight`, **not** read as confidence (no scale is stated). `--weight-as-confidence probability` converts on request | `MIGRATE-W02` |
| `metadata.conventions`, `metadata.schema` (a moving `main` URL) | replaced by the declaration block (§4.3) | `MIGRATE-I01` |
| `metadata.title`, `description`, `created`, `kb-section` | kept (`header.extensions["hif:metadata"]` ↔ plain metadata keys) | none |
| node `attrs.type`, `attrs.label` | entity `types`, `label`; types collected into the generated schema | none |

Result [verified]: the generated schema and the migrated C1 document validate with no semantic
findings. The HIF export is profile-valid and directed. The gate chain through XGI and HyperNetX
gives canonical equality.

---

## 12. v1 scope, later versions, and the upstream proposals

### 12.1 What v1 contains (F13: the P2 gate plus the Phase 1 consumer gates)

| Consumer gate | What v1 provides |
|---|---|
| **P2** | everything in §1.2 |
| **P3a** (C4 built in C1) | typed literals with precision, units and bounds; `somevalue`/`novalue`; rank + `rank_reason`; Wikidata references as `evidence.reference`; `content_key`/`core_key` (leak check on the core, dedup on the content); the arity definition with `statement_arity`; JSONL; the question-set shapes (§9.3); the time-qualifier mapping (§2.12.5) |
| **P3b** | the completion scorer with presets `hype`/`stare`/`hyper`, tie-exact ranks, three denominators, calibration by arity; **projections** (below) |
| **P1** | C2 Protocol, `MemoryStore`, the conformance suite with capability flags, the backend mapping (§6.7), projections to incidence rows, the RDF relation-instance pattern and a bipartite property graph, and a timing helper `store.bench.time_ops(store, ops)` so every backend is timed the same way [R01 C2-R15] |
| **P6** | the schema language, `schema_hypergraph` (+ HIF export), the Wikidata constraint mapping (§3.4) |
| **P7** | `identity.refines`/`relate`/`plan`, keys and policies, the temporal semantics, supersession and the walk, the identity table as tests, the memory scorer with `derive_memory_gold`, and a text rendering for the flat-store baseline |
| **P9** | the C3 queue, structural and identity lint, verdicts, replay, `event_hash`, the extraction and stability scorers |
| **P10** | complete and deterministic `incident`, `degree`, `find`, time and status filters, the text rendering, the retrieval scorer with the cost block |
| **P5** | labels on entities, relations and roles; the loaders with roles visible (HNX cell properties; XGI `bundle.role_map`) |

**Projections** (`khg_contracts/project.py`, deterministic, each recording its mapping) [R01 C1-R57
to C1-R61]:

- `to_positional(fact, schema, order=None)`: a fixed canonical role order per relation;
- `to_hyper_relational(fact, schema)`: main triple from `primary` plus qualifier pairs; time slots
  are emitted as P580/P582-style qualifiers, which is where `statement_arity` counts;
- `to_role_value(fact)`;
- `to_pairwise(fact, mode="star"|"clique")`, with back-pointers to the fact id (P4);
- `to_incidence_rows(doc)`;
- `to_rdf_relation_instance(doc)`, as triples of strings, with no rdflib dependency;
- `render_text(fact, schema, labels)`: relation label plus `role: label` pairs.

Dropping literals is a projection option only [R01 C1-R11].

### 12.2 Later versions

| Version | Feature | Why later |
|---|---|---|
| 1.1.0 | per-binding validity (an optional `valid` on a binding) for P7's question [07.10] | additive; P7's gate does not need it [R01 C1-R48] |
| 1.1.0 | valid-time uncertainty bounds (P1319/P1326/P8554/P8555/P12506 → `valid_time` bounds) [R04 M4] | v1 keeps them as `meta` bindings |
| 1.1.0 | tombstoned bindings, per-field suppression, erasure operation in C2 [R01 C1-R10, D-17] | governance; [10.6] is open |
| 1.1.0 | fold rules for numbered symmetric roles; variables shared across goals; `find` with refinement matching; user datatypes; quantity unit conversion | not needed by Phase 1 gates |
| 1.1.0 | generators: LinkML, SHACL 1.2 (`sh:uniqueValuesFor`, reifier shapes), TypeQL, SQL DDL [R01 D-15] | SHOULD; P1 can hand-map in v1 |
| 1.1.0 | soft F1 (E-M12, embedding model pinned) and the external adapters: GraphRAG-Bench, LongMemEval KU, LoCoMo in place (D-C5-16) | heavy dependencies; P4 is Phase 2 |
| 1.2.0 | entity-merge operation in C2 and rewrite actions in C3 [R01 C2-R20] | MAY |
| 2.0.0 (only if needed) | Julian calendar and non-Gregorian time natively; an `instant` time model; a HIF v2 record-level `role` (if adopted upstream) | each changes canonical forms or hashes |

### 12.3 The upstream HIF proposal (F15: issue first, v1-compatible)

**Issue title:** "A `role` convention for incidence attributes (no schema change), with compliant
fixtures".

1. **Motivation.** The paper's own example is `{"edge": 1, "node": 3, "attrs": {"role": "PI"}}`
   [R02 §3]. Knowledge hypergraphs need roles. Two producers today will not agree on the key [R01
   PF-03].
2. **The convention (hif-roles 1.0.0).** `attrs.role` is a string on every incidence;
   `attrs["role-position"]` orders fillers; `metadata["hif-roles-version"]` and
   `metadata["hif-roles-vocabulary"]` declare it. One incidence record per role: a node with k
   roles appears k times, each record with its own `direction`. This is what the paper's text already
   allows (a node in both tail and head) and what upstream's compliant fixture
   `duplicated_nodes_edges.json` contains [R02 §3 inconsistency 2].
3. **Two clarifications requested** (README text only): (a) `incidences` may repeat an (edge, node)
   pair, and readers must keep every record; (b) `attrs` must round-trip, so readers keep unknown
   keys [R03 §7.5].
4. **Fixtures (a PR after discussion):** `roles-basic.json`, `roles-two-roles-one-node.json` (c05),
   `roles-tail-and-head.json` (c06), `roles-ordered.json` (the YYZ route), `roles-undirected.json`.
   All are compliant with the current schema. The PR is limited to README text and
   `tests/test_files/HIF-compliant/`, the kind of PR the core team has merged quickly [R02 §8].
5. **Evidence:** the library-evidence JSON (§5.6): what XGI 0.10.2 and HyperNetX 2.4.3 drop today.
6. **Asked for v2, separately** (issues #51, #55): a structural `role` field that generalises
   `direction`, and a data-file version marker (for example a top-level `hif-version`) [R02 §4.1, rec. 8].
7. Cite #21 (the "structural vs attrs" rule the convention respects) and #44 (attribute-first
   extensions).

The P2 gate never depends on the issue's outcome. If upstream prefers a different key, the profile
maps it in a minor version.

### 12.4 Upstream issues for the libraries [R03 §7.5, D12]

One issue per library, with the library-evidence JSON attached; PRs follow once maintainers respond.

- **XGI** (`convert/hif_dict.py`):
  - read and write incidence `attrs` and all `weight` fields (an optional side mapping returned with
    `H`);
  - keep repeated (edge, node) records;
  - raise a clear error on a missing or invalid `direction` in directed files (today: `KeyError`, or
    silent `head`);
  - stop splatting attrs into `add_node`/`add_edge`;
  - write in a deterministic order;
  - copy `_net_attr` in the `SimplicialComplex` conversion.
- **HyperNetX** (`hif.py`, `factory.py`):
  - vendor the schema and allow offline use (issue #171);
  - `raise` the `HyperNetXError`s it constructs;
  - keep all `metadata`, and fix `to_hif(metadata=dict)`, which returns `None`;
  - stop writing `default_attrs.incidences.direction: null`, or stop reading it back;
  - drop `fillna("nil")`;
  - export isolated nodes and empty edges;
  - read `network-type`;
  - keep every record of a repeated pair, or honour `aggregate_by`.

---

## 13. Decisions log

**R01 decisions (D-01 to D-22)**

| # | Choice | Rejected | Evidence |
|---|---|---|---|
| D-01 roles in HIF | key `attrs.role` (single string), **one incidence record per binding**; legacy `role` is the same key | (b) `attrs.roles` list per pair (R01's recommendation); (d) a namespaced role key; (e) an edge-level role map | c06 tail + head needs two records [R03 §8]; the paper's example and upstream's fixture use `role` [R02 §6]; exact round trips [R03 §7.4; verified] |
| D-02 version and pinning | flat metadata keys: pinned `hif-schema` URL, `hif-schema-sha256`, DOI, `hif-roles-version`, `khg-profile`, `khg-schema(-sha256)`; a file-level version as a v2 ask | top-level keys (invalid HIF, R02 cases 04–06); relying on the schema URL | [R02 §4.4, §7] |
| D-03 slot classes | one binding list; slot class per usage: `core`/`qualifier`/`time`/`meta`; derived optional `primary` | two separate lists (core, qualifiers) | [R04 O12, M8.2 probe]; P6 and TypeDB need one list, P3a and P3b need the classes |
| D-04 role scope | global roles with per-relation usage (F4); main-snak naming left to P3a + P6, with R04's evidence that it does not change P6's class | relation-local roles (they trivialise P6) | [R04 M8.2] |
| D-05 identity | four identifiers (F6); content identity at two granularities (`content_key`, `core_key`) | text as id, member set, name + type | [R04 M3.1 INDRA and Wikibase; R05 §2.2.2] |
| D-06 arity | core + qualifier bindings with an entity, literal, fact-ref or somevalue value; `distinct_fillers` and `statement_arity` reported | counting distinct participants; counting validity bounds | prototype: the sample's f1 is arity 4 only if validity is excluded [verified] |
| D-07 validity | hyperedge validity carried by `time`-slot bindings + a declared time model; precision windows; definite/possible; one fact per maximal period; per-binding validity in 1.1 | a separate `valid_time` field as the source; multi-period facts; time only as qualifiers | [R01 C1-R46/47; TMP §7; R04 M4] |
| D-08 status, rank | four axes; per-kind status enums (adds `quoted`; goals `open`/`satisfied`/`abandoned`); the transition table of §2.13 | a single status field; `goal` as a status | [R04 M5; F7] |
| D-09 literals in HIF | inline in C1; in HIF, value-shared literal nodes with hashed ids; `incident` excludes them | one literal node per binding; literals on the incidence | [R01 D-09]; the hub risk is left for P10 to measure |
| D-10 supersession | `khg:supersedes` meta record (source of truth) + `status_ref` pointer; backward walk via incidence on the ref node | a `supersedes` field only; closing intervals only | [R04 O5; F8] |
| D-11 nesting depth | unbounded, acyclic; the gate covers one user level + meta refs | flat; one level only | [R01 D-11] |
| D-12 direction | declared per role usage; a binding carries one only if undeclared; directed HIF iff every binding has one | per-incidence free direction | [R01 D-12; R03 X4] |
| D-13 confidence and weight | `{value, scale}` in C1 (evidence-level and fact-level); HIF `weight` is only a passthrough, never read as confidence | weight = confidence (the sample) | [R03 D6; XGI drops weights, HNX invents 1] |
| D-14 evidence | a list per record with `supports` by bid, ECO-mapped `type`, `mode`, W3C selectors, `activity`; immutable, append-only | a source field on the edge | [R04 M6] |
| D-15 schema syntax | own JSON, LinkML-shaped, draft-07 meta-schema; generators in 1.1 | LinkML, SHACL, TypeQL as the source | [R04 M8.3] |
| D-16 store semantics | at-least default, exact on request; **`valid_at=None` (no filter) by default**, `as_at` now, status `asserted`, order by id, capability flags | "as-of now" by default (R01's recommendation: it would hide ended facts from historical questions) | §6.2; Q1 in §14 |
| D-17 erasure | outside the v1 gate; `visibility: suppressed` in v1; tombstones in 1.1 | deletion | [R01 D-17; GOV] |
| D-18 queue | separate, append-only, C1 candidate payload (F9); five item kinds; a goal with no bound roles is an edge whose incidences point to `_:var:` nodes | slots in edge attrs with no incidences (R01's recommendation) | uniform binding ↔ incidence mapping; goals stay drawable |
| D-19 loaders | build through public constructors; the library functions only in the evidence test (F1) | patching `read_hif`/`from_hif` | [R03 §6] |
| D-20 gate fixture | adversarial, two documents (directed and undirected) | the sample's f1 alone | §4.6 [verified] |
| D-21 extraction matching | strict + core + value-first Hungarian; role accuracy over aligned participants (E-M6); soft F1 in 1.1 | greedy; soft as headline | [R05 §2.2] |
| D-22 v1 scope | §12.1 | everything at once | F13 |

**R03 decisions (D1 to D12)**

| # | Choice | Rejected | Evidence |
|---|---|---|---|
| D1 XGI records | side table bundled with `H` (source of truth); strict mode; no edge-attr mirror in v1 | records in edge attrs (B); a node → roles map (C: it turns integer ids into JSON strings) | [R03 §7.4] |
| D2 multi-role encoding | one record per role (binding) | a list on one record; forbid-and-reify | c05, c06 exact [R03]; the fixture's ordered YYZ [verified] |
| D3 library HIF functions | never in the loaders | wrapping them | F1 |
| D4 missing or invalid direction | reject (`KHG-P010`, `KHG-H005`) | a default of tail or head | XGI `KeyError`; HNX `"nil"` |
| D5 duplicate declarations | reject (`KHG-D001`) before loading | XGI's merge rule, HNX's first-wins | [R03 row 19] |
| D6 weight | passthrough only; the linter warns on an attrs key named `weight` (`L-Q-007`), since HNX promotes it | carrying confidence | [R03 row 11] |
| D7 metadata keys HNX interprets | `default_attrs` forbidden (`KHG-P008`); `name` allowed | allowing | c20 invented a role |
| D8 `asc` | rejected (`KHG-P007`) | loading as a plain hypergraph | c04: 9 → 39 incidences |
| D9 native operations | documented safe and unsafe lists (§5.4); `bundle.check()`; strict export | allowing everything silently | [R03 §5, §7.4] |
| D10 dependencies | extras pinned to xgi 0.10.2 and hypernetx 2.4.3 (pandas < 3); the probe suite reruns when a pin moves | hard dependencies | [R03 §0.1] |
| D11 output order | canonical; structural comparison (F10) plus a byte-determinism test for the serialiser | library order | XGI: 4 seeds, 4 outputs |
| D12 upstream | issues, then PRs; the gate never depends on them | | §12.4 |

**R04 decisions (O1 to O13)**

| # | Choice | Rejected | Evidence |
|---|---|---|---|
| O1 role identity | global with usage; TypeDB scoped roles named `r:ρ` after the global id | local roles | [R04 M1, M8.2] |
| O2 binding shape | **a list of bindings with stable `bid`s** | a role-keyed object of lists | cardinality is semantic anyway (F5); bids give per-binding evidence, goal binding events and refinement continuity; a list maps 1:1 to incidences |
| O3 key declaration | roles + temporal + policy, with definite-overlap semantics, rank-aware invariant (single-best-value), incomplete keys exempt | roles only | [R04 M3.3]; X1 year-precision handover [verified] |
| O4 lifecycle | four axes; `superseded` means belief revision only | a single status | [R04 M5; F7] |
| O5 supersession carrier | meta record + pointer | a field only | F8 |
| O6 versioning | immutable versions **and** refinement-only content changes | in place (Graphiti) | [R04 M4]; C2-S012 [verified] |
| O7 evidence typing | a small ECO-mapped `type` + EARL/ECO `mode` | free text; full ECO ids | [R04 M6] |
| O8 spans | code points, half-open, NFC, `doc_sha256`, quote + position | UTF-16, inclusive ends | F11; the 🛫 test [verified] |
| O9 verdict unit | (candidate, evidence), keyed by `content_key` + `event_hash`, with an aggregation rule | per candidate | [R04 M7] |
| O10 schema syntax | own JSON, LinkML-compatible concepts | LinkML itself (25 dependencies) | [R04 M8.1] |
| O11 dialect | draft-07; `jsonschema` for reports, `fastjsonschema` as the fast path; no cross-document `$ref`; every shape choice dispatched with `if`/`then` on its key; stable codes from `x-khg-code` annotations plus per-layer keyword tables (§8.1) | 2020-12; `oneOf` unions (a failure is reported at the union, so the code is imprecise); codes parsed from validator messages (not stable across versions) | [R04 M8]; the fastjsonschema `tag:` finding; code coverage of every constraint and the 24,013-document differential [verified] |
| O12 slot classes | four; `meta` excluded from arity, keys and P6; `time` excluded from arity (and optional in P6) | two classes | [R04 M8.2]; D-06 |
| O13 conformance | declarative JSON scenarios, adapter registry, EARL-shaped report | code-only tests | [R04 M9.2]; four scenarios run [verified] |

**R05 decisions (D-C5-01 to D-C5-18)**, all adopted as R05 recommends, with these C1 bindings:

| # | Choice (C1-specific note) |
|---|---|
| 01 unit | whole fact (E-M1); bindings under one alignment; quintuplets only as the `hyperred_quintuplet` preset |
| 02 alignment | value-first Hungarian, lexicographic tie-break (E-M3) |
| 03 entities | canonical ids, **modulo C1 redirects**; linking scored separately |
| 04 literals | `truncate_to_gold` = C1 value refinement v_pred ⊑ v_gold; `exact` preset |
| 05 stability | S-M1/S-M4/S-M5/S-M7 on `content_key` and `core_key` (C1's two content hashes) |
| 06 ranks | tie-exact expectation; audit ranks; per-model presets |
| 07 denominators | per task, per fact, macro over C1 arity bins |
| 08 filters | exact; **monotone = C1 ⊑**; time-aware = C1 definite validity at `as_of` |
| 09 calibration | top-1 ECE (15 bins, both binnings) + Brier per arity; the score-to-probability map declared |
| 10 model interface | rank statistics against C5's filter index |
| 11 retrieval units | back-pointers to fact ids; `binding_coverage@k` over C1 bindings |
| 12 support | alternative minimal sets; `support_success` headline |
| 13 answers | structured C1 values plus text |
| 14 memory outcomes | O1–O7; stale split into **expired (valid-time closure) vs retracted (supersession/retraction)**, computed by `derive_memory_gold` from C2 semantics |
| 15 question-set shapes | §9.3, in C1 terms; a memory trace is a C2 put log |
| 16 external adapters | v1.1 (P4 is Phase 2) |
| 17 assignment solver | pure Python, SciPy optional, brute-force cross-check |
| 18 dispersion | K ≥ 3 runs; percentile bootstrap, 1,000 resamples, seed 0; paired bootstrap |

---

## 14. Risks and open questions

### 14.1 Risks

1. **Semantic weight on backends.** P1's stores must honour immutable versions, the key invariant
   and definite-overlap time. *Mitigation:* the store's duties are invariants; the planner and ⊑ are
   shared Python; capability flags let a backend report what it cannot do; the scenarios are the
   same files everywhere.
2. **Presumptions misread data.** "Absent end = ongoing" and "unstated = presumed always" make two
   undated CEO claims a dispute (X3). If P3a's Wikidata subset is mostly undated, disputes may flood
   the review queue. *Mitigation:* both `definite` and `possible` modes are exposed; P7 measures the
   rate; alternative Q6.
3. **The `complete` flag can be forgotten.** Then a changed composition merges as a refinement
   (C4a-o). *Mitigation:* `L-Q-004`; the default is open because Wikidata qualifiers are open.
4. **Order-dependent surviving ids.** After a refinement merge, which id survives depends on arrival
   order (content does not). *Mitigation:* documented; P9's Δ_order captures it; content keys are
   stable.
5. **Literal hubs.** Value-shared literal nodes join unrelated facts in HIF and XGI/HNX graphs.
   *Mitigation:* `incident` excludes literal nodes; walkers treat them as terminal; P10 measures (R01
   open question 2).
6. **One cell per pair in HyperNetX.** Repeated-pair records 2..k ride in a reserved key, so HNX
   algorithms (incidence matrix, degree) count one incidence per pair while C1 counts bindings.
   *Mitigation:* documented; C1 is the source for counts.
7. **Upstream may prefer a list-valued `roles`.** Then files under this convention remain valid HIF
   v1, and the profile would map a list in a minor version. The gate is unaffected.
8. **Hash stability.** A canonicalisation fix after release is a major version. *Mitigation:* byte-
   determinism tests; the fixture's hashes are pinned in tests before 1.0.0.
9. **Wikidata time conventions** (Julian dates, year 0, century labels) can shift windows by a
   calendar gap. *Mitigation:* Gregorian-only v1 with a conversion helper for P3a; risk noted in the
   datasheet.
10. **Design size.** The design is larger than a minimal gate. *Mitigation:* every piece in §12.1
    traces to a Phase 1 gate; everything else is in §12.2.

### 14.2 Open questions for the director

- **Q1 Read default for valid time.** This design uses `valid_at=None` (no filter); R01 D-16
  recommended "as-of now". As-of-now would hide ended facts from P10's walker on historical
  questions. Confirm.
- **Q2 Rank in the key invariant.** Keep the single-best-value rule, or use the simpler "at most one
  asserted, non-deprecated fact per key per instant"? The simpler rule forces P3a to demote
  Wikidata's normal-rank alternatives.
- **Q3 Default planner policy.** `dispute` (this design) or `reject`, when a relation declares no
  `on_collision`? (The meta-schema currently requires `on_collision` on every key.)
- **Q4 Main-snak role naming for Wikidata relations.** Generic `subject`/`value`, or per property?
  R04 M8.2 shows it does not change P6's acyclicity class. P3a and P6 decide before C4 is built.
- **Q5 Calendars.** Gregorian-only v1 with P3a converting at import, keeping the source calendar in
  evidence. Confirm.
- **Q6 Undated facts and temporal keys.** Should `unstated` facts join temporal key checks (presumed
  always valid; X3 → dispute, this design) or be exempt (never conflicting)? P7 should measure
  both.
- **Q7 Schema identifiers.** `tag:khg-contracts,2026:…` now; an https namespace later (a major
  version) if the programme gets a domain.
- **Q8 Goal satisfaction.** A goal stays a goal and links to a (possibly pre-existing) fact through
  `khg:fulfils` (this design), rather than turning into the fact. Confirm with P11.
- **Q9 Per-binding validity** is scheduled for 1.1. Confirm that P7's gate does not need it.
- **Q10 Literal nodes.** Value-shared (this design, R01 D-09) or per binding? Changing it later
  changes HIF node ids: a `khg-hif` major version (C1 is unaffected).

**Objections to the fixed decisions: none.** F1–F15 are consistent with the evidence and were
designed within. Three refinements within them are flagged so the synthesis can see them:

- F6's "content/core-key hash" is realised at two granularities (`content_key`, `core_key`), because
  R05 needs both.
- F10's structural comparison is complemented by a byte-determinism test of the serialiser, because
  content hashes depend on bytes.
- F7's statuses gain `quoted` (non-asserted claims, R01 C1-R44) and goal-specific statuses.

---

## Appendix A. The gate schema (`p2-gate/1.0.0`) [verified]

Valid against `khg-schema-1.0.0.schema.json` (both validators) and its semantic checks.
`digest("khg-schema/1", ·)` = `sha256:8b2eb97583f1ef73523a8cb3f074ffe8f2098f46c4e5f43af344475afd822b00`,
the value declared in the fixtures' HIF metadata. Shown one relation per block; it parses to the
same object.

```json
{
 "khg_schema": "khg-schema/1.0.0",
 "id": "p2-gate",
 "version": "1.0.0",
 "label": "P2 gate fixture schema",
 "entity_types": [{"id": "Agent"}, {"id": "Airline"}, {"id": "Airport"}, {"id": "CellLine"}, {"id": "Chemical"}, {"id": "Drug"}, {"id": "Gene"}, {"id": "Outcome"}, {"id": "Place"}, {"id": "Position"}, {"id": "Reaction"}, {"id": "Station"}, {"id": "Person", "parents": ["Agent"]}, {"id": "Organisation", "parents": ["Agent"]}],
 "confidence_scales": [{"id": "llm-0-10", "kind": "bounded", "min": 0, "max": 10, "description": "self-reported extractor score, not a probability"}],
 "roles": [{"id": "regulator"}, {"id": "target"}, {"id": "context"}, {"id": "agent"}, {"id": "effect"}, {"id": "carrier"}, {"id": "stop"}, {"id": "origin"}, {"id": "destination"}, {"id": "holder"}, {"id": "position"}, {"id": "replaces"}, {"id": "place"}, {"id": "quantity"}, {"id": "person"}, {"id": "birthplace"}, {"id": "reaction"}, {"id": "catalyst"}, {"id": "claimant"}, {"id": "claim"}, {"id": "station"}, {"id": "name"}, {"id": "code"}, {"id": "elevation"}, {"id": "opened"}, {"id": "active"}, {"id": "homepage"}, {"id": "location"}, {"id": "spouse"}, {"id": "start_time", "label": "start time", "mappings": {"wikidata": "P580"}}, {"id": "end_time", "label": "end time", "mappings": {"wikidata": "P582"}}, {"id": "point_in_time", "label": "point in time", "mappings": {"wikidata": "P585"}}],
 "relations": [
  {"id": "regulates", "time": {"model": "invariant"},
   "roles": [
    {"role": "regulator", "slot": "core", "fillers": [{"entity": ["Gene"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "target", "slot": "core", "fillers": [{"entity": ["Gene"]}], "min": 1, "max": 1, "direction": "head"},
    {"role": "context", "slot": "qualifier", "fillers": [{"entity": ["CellLine"]}], "min": 0, "max": 1, "direction": "tail"}
   ]},
  {"id": "co_administration_causes",
   "roles": [
    {"role": "agent", "slot": "core", "fillers": [{"entity": ["Drug"]}], "min": 2, "max": null, "direction": "tail"},
    {"role": "effect", "slot": "core", "fillers": [{"entity": ["Outcome"]}], "min": 1, "max": 1, "direction": "head"}
   ]},
  {"id": "flight_route",
   "roles": [
    {"role": "carrier", "slot": "core", "fillers": [{"entity": ["Airline"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "stop", "slot": "core", "fillers": [{"entity": ["Airport"]}], "min": 2, "max": null, "ordered": true, "complete": true, "direction": "head"}
   ]},
  {"id": "flies_between", "constraints": [{"type": "must_differ", "roles": ["origin", "destination"], "severity": "warning"}],
   "roles": [
    {"role": "carrier", "slot": "core", "fillers": [{"entity": ["Airline"]}], "min": 1, "max": 1},
    {"role": "origin", "slot": "core", "fillers": [{"entity": ["Airport"]}], "min": 1, "max": 1},
    {"role": "destination", "slot": "core", "fillers": [{"entity": ["Airport"]}], "min": 1, "max": 1}
   ]},
  {"id": "position_held", "mappings": {"wikidata": "P39"}, "primary": {"subject": "holder", "object": "position"}, "time": {"model": "interval", "start": "start_time", "end": "end_time"}, "key": {"roles": ["position"], "temporal": true, "on_collision": "close_older"},
   "roles": [
    {"role": "holder", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "position", "slot": "core", "fillers": [{"entity": ["Position"]}], "min": 1, "max": 1, "direction": "head"},
    {"role": "start_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"},
    {"role": "end_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"},
    {"role": "replaces", "slot": "qualifier", "fillers": [{"entity": ["Person"]}], "min": 0, "max": null, "direction": "tail"}
   ]},
  {"id": "married", "time": {"model": "interval", "start": "start_time", "end": "end_time"},
   "roles": [
    {"role": "spouse", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 2, "max": 2, "complete": true},
    {"role": "start_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1},
    {"role": "end_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1}
   ]},
  {"id": "population", "mappings": {"wikidata": "P1082"}, "time": {"model": "invariant"}, "key": {"roles": ["place", "point_in_time"], "temporal": false, "on_collision": "dispute"},
   "roles": [
    {"role": "place", "slot": "core", "fillers": [{"entity": ["Place"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "quantity", "slot": "core", "fillers": [{"literal": "quantity", "units": ["1"]}], "min": 1, "max": 1, "direction": "head"},
    {"role": "point_in_time", "slot": "qualifier", "fillers": [{"literal": "time", "precision_min": 9}], "min": 0, "max": 1, "direction": "tail"}
   ]},
  {"id": "station_profile",
   "roles": [
    {"role": "station", "slot": "core", "fillers": [{"entity": ["Station"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "name", "slot": "qualifier", "fillers": [{"literal": "lang_string"}], "min": 0, "max": null, "direction": "head"},
    {"role": "code", "slot": "qualifier", "fillers": [{"literal": "string"}], "min": 0, "max": 1, "direction": "head"},
    {"role": "elevation", "slot": "qualifier", "fillers": [{"literal": "quantity", "units": ["wd:Q11573"]}], "min": 0, "max": 1, "direction": "head"},
    {"role": "opened", "slot": "qualifier", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "head"},
    {"role": "active", "slot": "qualifier", "fillers": [{"literal": "boolean"}], "min": 0, "max": 1, "direction": "head"},
    {"role": "homepage", "slot": "qualifier", "fillers": [{"literal": "iri"}], "min": 0, "max": 1, "direction": "head"},
    {"role": "location", "slot": "qualifier", "fillers": [{"literal": "geo"}], "min": 0, "max": 1, "direction": "head"}
   ]},
  {"id": "born_in", "mappings": {"wikidata": "P19"}, "time": {"model": "invariant"}, "key": {"roles": ["person"], "temporal": false, "on_collision": "dispute"},
   "roles": [
    {"role": "person", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "birthplace", "slot": "core", "fillers": [{"entity": ["Place"]}], "min": 1, "max": 1, "direction": "head"}
   ]},
  {"id": "claims", "time": {"model": "invariant"},
   "roles": [
    {"role": "claimant", "slot": "core", "fillers": [{"entity": ["Agent"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "claim", "slot": "core", "fillers": [{"fact": ["born_in"]}], "min": 1, "max": 1, "direction": "head", "somevalue": false, "novalue": false},
    {"role": "point_in_time", "slot": "qualifier", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"}
   ]},
  {"id": "catalysed_by",
   "roles": [
    {"role": "reaction", "slot": "core", "fillers": [{"entity": ["Reaction"]}], "min": 1, "max": 1, "direction": "tail"},
    {"role": "catalyst", "slot": "core", "fillers": [{"entity": ["Chemical"]}], "min": 1, "max": null, "direction": "head"}
   ]}
 ]
}
```

## Appendix B. Verification artefacts

All in `/tmp/claude-0/-home-user-knowledge-Hyper-Graphs-/9b58e6a1-1989-5ed1-ae3b-676a337fca40/scratchpad/designs/work-B-semantics-first/`.
`run_all.sh` reruns everything. It uses the venv `…/scratchpad/venv-libs` (xgi 0.10.2, hypernetx
2.4.3, pandas 2.3.3, jsonschema 4.26.0, fastjsonschema 2.22.2), with no network.

| File | Checks | Result |
|---|---|---|
| `khg-record-1.0.0.schema.json`, `khg-schema-1.0.0.schema.json`, `khg-hif-1.0.0.schema.json`, `khg-queue-1.0.0.schema.json` | valid draft-07 (`check_schema`) | pass |
| `run_gate.py` → `gate-output.txt` | fixtures valid (C1 record schema; HIF vendored + profile; both validators); chain C1 → HIF → XGI → HIF → HNX → HIF → C1; XGI-only; HNX-only | ALL OK |
| `run_evidence.py` → `evidence-output.txt` | HIF-level multisets; libraries' native HIF functions | §5.6 numbers |
| `run_malformed.py` → `malformed-output.txt`, `malformed-results.json` | MC01–MC108 (layer and code) + 5 positives + code coverage | 0 failed expectations |
| `khg_codes.py` → `codes-output.txt` | the §8.1 reporter; coverage of every constraint (P 74, C 848, M 161, Q 153 path occurrences; H 28) | none uncovered |
| `run_code_probes.py` → `code-probes-output.txt` | 28 registry probes (§8.2 clauses the gate list does not reach) | 0 mismatches |
| `schema-refactor-check/diff_schemas.py` → `schema-refactor-output.txt` | original (`schema-refactor-check/original/`) vs annotated schemas, 24,013 documents, jsonschema and fastjsonschema | 0 disagreements |
| `run_identity.py` → `identity-output.txt` | §2.19 table | deterministic |
| `migrate_sample.py` → `migrate-output.txt` | §11.3 | valid; chain equal |
| `run_smoke.py` → `smoke-output.txt`, `queue-examples.json` | gate clause 3 + 18 store checks + 3 C3 checks (item, log and verdict under both validators; fold; verdict keys = §7.3) | 21 PASS |
| `run_scenarios.py`, `scenarios/*.json` | 4 declarative C2 scenarios (17 assertions) | all pass |
