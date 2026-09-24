# P2 design A: standards-first minimalism

Design for project P2, "Role-aware HIF and the shared contracts" (C1, C2, C3, C5 and the HIF `roles`
convention). Angle: the smallest, cleanest contract that a HIF maintainer would accept upstream and that a
library author could implement in a day. C1 is kept as close as possible to "a HIF file under a
profile" while still meeting every consumer MUST. Written 2026-09-23 from the five research reports
[R01]–[R05] (read in full), the probe code under `research/probes/`, and the director's fixed decisions
F1–F15, which this design works within. The one objection is to F8, and it is marked (§2.14, §13).

Citations: [R0n §x] is research report n, section x. Requirement ids (C1-R13, C2-R04, …), pitfall ids
(PF-nn), malformed-case candidates (V01–V49) and decisions (D-01–D-22) are R01's. R03's decisions are
D1–D12, R04's are O1–O13 and R05's are D-C5-01–18. A few standards the reports do not cover are used by
name and were not re-verified in this session: RFC 8785 (JSON Canonicalization Scheme), ISO 8601-1 and
ISO 8601-2 (EDTF) date forms, N-Triples/Turtle blank-node labels, and the Wikibase RDF dump's shared
value nodes. Each is marked where it is used.

## 0. What was executed, and where

Every JSON example in this document was generated or checked by code in
`scratchpad/designs/work-A-standards-first/`. One command, `./run_all.sh`, reruns all of it offline:
`venv-hif` has jsonschema 4.26.0 and fastjsonschema 2.22.2; `venv-libs` has xgi 0.10.2, hypernetx 2.4.3
and pandas 2.3.3.

| Check (script) | Result |
|---|---|
| Four draft-07 schemas built from shared definitions (`build_schemas.py`), each checked with `Draft7Validator.check_schema` | valid |
| Gate relation schema and built-in schema against the relation-schema meta-schema (`checks_schema.py`) | valid under both validators |
| Gate fixture (C1) against the C1 document schema | valid under both validators |
| `to_hif(fixture)` against the vendored HIF schema (`hif_schema_v0.1.0.json`, blob `e2105bb`, sha256 `639466b7…`, hash re-checked at run time) and against the KHG HIF profile | valid under both validators; 12 edges, 30 nodes, 34 incidences, 2 repeated (edge, node) pairs |
| `from_hif(to_hif(doc)) == canonical(doc)` and `to_hif` deterministic | true |
| Gate chain through the loader sketch `research/probes/role_loaders_sketch.py`, with network disabled (`checks_libs.py`) | XGI, HNX and HIF→XGI→HIF→HNX→HIF: exact by `probe_common.diff_hif`, roles 34/34, directions 34/34, incidence attrs 34/34, folded back to C1 equal to the original, idempotent |
| The same chain under `PYTHONHASHSEED` 0–3 | 1 distinct output (byte-identical) |
| Library evidence on the same file | `xgi.read_hif`/`write_hif`: roles 0/34, records 34→33, directions 33/34. `hnx.from_hif`/`to_hif` (schema served from the vendored file): roles 32/34, records 34→32, all 6 metadata keys lost, `weight` added on 32 incidences |
| Malformed-case list (`malformed_cases.py`) | 90/90 cases rejected by the assigned layer, and by the assigned code where the check runs in Python; the fixture, both schemas and the queue example pass every layer |
| C2 conformance scenarios on a prototype `MemoryStore` (`store_proto.py`, `scenarios_and_smoke.py`) | 22/22 passed |
| Smoke test: queue → structural lint → accept → store → export | 0 lint violations; C1 export, HIF export (profile), queue stream all valid; HIF export folds back to the C1 export |
| Migration of the KB's `schemas/sample.hif.json` (`migrate_sample.py`) | migrated C1, inferred relation schema and profile HIF all valid; the role strings in HIF are unchanged |
| C4 draft memory-trace shape (§9.6), replayed as C2 `put` batches on the prototype store | as of now → `h2`; as of 2020 → `h1`; as-at before step 2 → `h1` with no `until`; embedded records valid C1 |
| Legacy import of foreign HIF (`legacy_proto.py`) on the KB sample plus R03's 27 library cases | 22 imported with every (edge, node, role, direction) record kept; 1 refused by the NFC rule (c13's decomposed id); 5 refused by design (c04 `asc`, c12 `1` vs `"1"`, c14 missing direction, c19 duplicate declarations, c22 `NaN`) |

The prototypes are evidence that the design is implementable and consistent. They are not the package.

---

## 1. Summary and the gate

**The one idea.** C1 is *folded HIF*. A HIF document has three arrays: `nodes`, `edges` and
`incidences`. A C1 document has two, `nodes` and `edges`, and each edge carries its incidences folded
in as `bindings`. Every name that HIF already has is kept (`node`, `edge`, `direction`, `weight`,
`attrs`). A binding is one HIF incidence with three changes: its `edge` field is dropped, because the
containing edge implies it; its role is lifted out of `attrs`; and its value is written inline. HIF export
unfolds and HIF import folds, one binding to one incidence. The external artefact therefore has three
nested layers, each smaller than the next:

1. **The HIF role convention** (proposed upstream, generic, no schema change). `incidences[].attrs.role`
   is a string. A node that plays several roles in one edge has one incidence record per role. The file
   declares `metadata["role-convention"] = "1.0.0"`.
2. **The KHG profile of HIF**: the roles convention, plus declared keys in `edges[].attrs`
   (`relation`, `status`, `valid`, `evidence`, …) and in `nodes[].attrs`, plus *derived nodes* for
   values that are not entities (literals, `somevalue`/`novalue`/UNBOUND, hyperedge references). One
   draft-07 schema, `allOf` the vendored HIF schema, so a profile-valid file is also HIF-valid.
3. **C1**: the same data model, folded, as a JSON document or JSONL stream. This is what P3a writes, what
   P9 enqueues, what stores `put`, and what C5 scores.

**How small it is.** Two record kinds, node and edge. Supersession and retraction are edges of two
built-in relations, so they need no record kind of their own. One value union: `node`, `literal`, `edge`
or `special`. Five statuses, five literal datatypes, four evidence types, three slot classes, one arity
function. Of the four identifiers F6 requires, one is stored; the other three are computed by one
documented hash rule. C2 has six methods. C3 has one item kind and seven actions. Structural lint *is* the
validator, with the same codes.

**What it costs.** Five things, each argued where it arises:

- Valid time is a field, and Wikidata's start and end qualifiers are lifted into it (§2.13).
- Four items are deferred to 1.1: rule hyperarcs, co-occurrence constraints, an explicit `primary` field
  (v1 derives the pair from direction, §2.19) and the `disputed` status (§12).
- A fact-level confidence is not stored (§2.12).
- C2 takes SQL:2011's default of *no* valid-time filter rather than R01's "as-of now" (§6).
- One objection to F8 (§2.14).

### The gate, clause by clause

| Gate clause (PLAN §4) | Test (in `tests/gate/`) | What it asserts | Shown reachable by |
|---|---|---|---|
| "A record round-trips repo format to HIF to XGI and HyperNetX and back with roles intact" | `test_g1_roundtrip.py` (needs extras `[xgi,hypernetx]`) | Takes the adversarial fixture `tests/fixtures/gate/gate-fixture.khg.json` (§2.18) through `to_hif` → validate (HIF 0.1.0 + profile) → `to_xgi` → `from_xgi` → validate → `to_hnx` → `from_hnx` → validate → `from_hif`, and asserts structural equality with `canonical(fixture)`. Per-record counts must be exact: roles, directions and incidence attrs 34/34; records 34 → 34. Each library is also tested alone; a second round must be identical; `PYTHONHASHSEED` 0–3 must give identical output; sockets are blocked throughout | `checks_libs.py` (§0) |
| "the validator rejects each malformed case in its test list" | `test_g2_malformed.py` | Parametrised over `tests/fixtures/malformed/MANIFEST.json`: 90 cases (§8.3), each one file plus `{id, layer, code}`. The first failing layer must be the listed one and the listed code must be among its findings. The positive fixtures (gate C1, gate HIF, schemas, queue stream) must pass | `malformed_cases.py` (§0) |
| "a smoke test runs one record through queue, structural lint, store and export" | `test_g3_smoke.py` | Enqueues gate edge `f1` as a candidate with its computed keys, lints it (0 violations), accepts it, writes it to `MemoryStore`, exports `khg` and `hif`, validates both exports and the queue stream, and asserts that the exported record has its four roles and folds back unchanged | `scenarios_and_smoke.py` (§0) |

The gate never touches the network, never calls `xgi.read_hif`/`write_hif` or `hnx.from_hif`/`to_hif`
(F1), and does not depend on upstream acceptance (F15).

---

## 2. C1 record format

### 2.1 Folded HIF: where every C1 field lives in HIF

| C1 | HIF (KHG profile) |
|---|---|
| document `metadata` | `metadata`, plus `role-convention`, `hif-schema` and `hif-schema-sha256`, which are written on export and dropped on import |
| node record `{node, types, label, attrs, weight}` | `nodes[]` `{node, weight, attrs: {types, label, …attrs}}` |
| edge record `{edge, relation, status, valid, evidence, rank, visibility, recorded, schema, superseded-by, attrs, weight}` | `edges[]` `{edge, weight, attrs: {relation, status, valid, evidence, rank, visibility, recorded, schema, superseded-by, …attrs}}` |
| binding `{role, <value>, direction, position, evidence, attrs, weight}` inside an edge | one `incidences[]` record `{edge, node, direction, weight, attrs: {role, position, evidence, …attrs}}` |
| value `{"node": id}` | the incidence's `node` is `id` |
| value `{"literal": {...}}` | `node` is a derived id `_:lit:<hash>`; the node record's `attrs.literal` holds the literal |
| value `{"edge": id}` (nesting) | `node` is `_:edge:<id>`; the node record's `attrs.edge` holds `id` |
| value `{"special": k}` | `node` is `_:some:`, `_:none:` or `_:unbound:<role>/<n>/<edge>`; the node record's `attrs.special` holds `k` |
| (derived) | `network-type`: `directed` if every binding has a direction, else `undirected` (§4.5) |

Key names inside `attrs` are the C1 field names, dash-case for multi-word keys, as HIF's own
`network-type` and the paper's advice ("dash case", [R02 §3]) have it. No top-level or record-level key
is added to HIF (F3).

### 2.2 Containers, header and canonical form

- **JSON document** (`*.khg.json`): `{"metadata": {...}, "nodes": [...], "edges": [...]}`. `metadata` and
  `edges` are required; nothing else is allowed at the top level.
- **JSONL stream** (`*.khg.jsonl`): line 1 is `{"metadata": {...}}`, then one node record or edge record
  per line. The kind is recognised by the id key (`node` or `edge`), so there is no `kind` field. This is
  the streaming form HIF lacks [R01 PF-28]; P3a's corpus and store exports use it.
- **Header** (`metadata`): `khg-profile` (required, semver of the C1 format, `1.x.y`), `khg-schema`
  (required, relation-type schema id `<name>/<semver>`), and any other key, carried verbatim. The
  HIF-only keys `role-convention`, `hif-schema` and `hif-schema-sha256` are forbidden here.
- **Canonical form** (F10):
  1. Nodes are sorted by `node`, and edges by (`edge`, `recorded`), in code-point order.
  2. Bindings are sorted by (role, position or −1, value kind in the order node < literal < edge <
     special, JCS of the value).
  3. Evidence is sorted by `id`.
  4. Defaults are omitted: `rank: "normal"`, `visibility: "visible"`, and an edge `schema` equal to the
     header's.
  5. A role's declared direction is materialised on its bindings.
  6. Literal lexical forms and NFC are *enforced*, not normalised silently.

  Equality is JSON-value equality of canonical forms, never byte equality. Files are written UTF-8 with
  sorted keys.

### 2.3 Node record

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `node` | string id | yes | Opaque entity id. It is NFC, has no C0/DEL controls, does not start with `_:`, and is namespaced by convention (`wd:Q937`, `ex:metformin`) [C1-R04]. Node ids and edge ids are **separate namespaces**, as in HIF: the paper builds on "the disjoint union of the nodes V and hyperedges E", and upstream data reuses ids across the two [R02 §3, case 03] |
| `types` | array of type names, unique | no | Entity types, flat. The producer lists every type that applies; subtyping is deferred to 1.1 |
| `label` | string | no | Human-readable label [C1-R21] |
| `attrs` | object | no | Opaque, round-tripped verbatim, never interpreted. It must not use the keys `types`, `label`, `literal`, `special` or `edge` |
| `weight` | number | no | HIF `weight`, carried verbatim. It has no C1 meaning; P2 producers never write it [R03 D6] |

Node records are optional: a binding may name an entity without a node record, which HIF allows too
[R02 case 28]. Type checks run only when the node record has `types` (open world).

### 2.4 Edge record (a fact, a meta-fact, or a goal)

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `edge` | string id | yes | **Identifier 1 of F6**: an opaque, stable fact id. It is never the text, a hash, or the member set [C1-R01] |
| `relation` | name | yes | Relation type, declared in the relation-type schema |
| `status` | `asserted` \| `superseded` \| `retracted` \| `goal` \| `candidate` | yes | Record status (belief axis, §2.14). `candidate` is legal only inside a C3 payload |
| `bindings` | array of binding, ≥ 1 | yes | The role fillers (§2.5) |
| `valid` | `{from?, until?}`, at least one | no | Valid time, half-open `[from, until)` (§2.13) |
| `evidence` | array of evidence | per status | At least one is required when the status is asserted, superseded or retracted [C1-R35]. Optional for goals |
| `rank` | `preferred` \| `normal` \| `deprecated` | no | Editorial rank, Wikidata's; defaults to `normal`. "Deprecated ≠ false" [C1-R43] |
| `visibility` | `visible` \| `suppressed` | no | Governance tier, defaults to `visible` [C1-R45] |
| `recorded` | UTC datetime `YYYY-MM-DDThh:mm:ss(.ffffff)Z` | no in authored input; always in store output | Transaction time of this version (§2.13) |
| `schema` | `<name>/<semver>` | no | The relation-type schema this edge was typed under, when it differs from the header's [C1-R32] |
| `superseded-by` | array of edge ids, ≥ 1 | iff `status` = `superseded` | Index pointer to the superseding facts (F8, §2.14) |
| `attrs` | object | no | Opaque. It must not use the names of the fields above |
| `weight` | number | no | HIF `weight`, verbatim, no meaning |

The **edge kind** [C1-R05] is not a field; the relation type declares it. An edge is a *meta* fact if
any role of its relation accepts hyperedges (§3), otherwise an n-ary *fact*. A *goal* is a status. *Rule*
hyperarcs are deferred to 1.1 (§12). An edge's kind never differs from its relation's, so a per-record
field would only be one more thing to disagree about.

### 2.5 Binding (role filler)

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `role` | name | yes | Global role id (F4) |
| `node` \| `literal` \| `edge` \| `special` | exactly one | yes | The value: an entity id, a typed literal (§2.6), a hyperedge id (nesting, §2.10), or `somevalue` \| `novalue` \| `unbound` (§2.11) [C1-R06] |
| `direction` | `tail` \| `head` | no | HIF direction of this binding [C1-R19]. Inherited from the role's declared direction, and materialised in canonical form |
| `position` | integer ≥ 0 | iff the role is `ordered` | Order among the role's fillers, unique within the role [C1-R15] |
| `evidence` | array of evidence ids, ≥ 1, unique | no | Evidence records of this edge that support this binding in particular [C1-R36] |
| `attrs` | object | no | Opaque; must not use `role`, `position` or `evidence` |
| `weight` | number | no | HIF incidence `weight`, verbatim |

One entity may fill several roles, or the same ordered role at several positions. Every such binding is
kept [C1-R13, C1-R14]. A binding repeated with the same (role, value, position) is malformed (S012).

### 2.6 Literals

A literal is `{"datatype", "value", …}`. `value` is always a *string* in canonical lexical form, as in
RDF. No floats ever enter C1 values or hashes.

| `datatype` | Extra fields | Lexical rule of `value` | Wikidata / XSD counterpart |
|---|---|---|---|
| `string` | — | any NFC string | string, external-id, commonsMedia / `xsd:string` |
| `text` | `lang` (BCP 47, required) | NFC string | monolingualtext / `rdf:langString` |
| `iri` | — | absolute IRI | url / `xsd:anyURI` |
| `quantity` | `unit` (required; entity id, or `"1"` for dimensionless, as in Wikibase), optional `lower`, `upper` | canonical decimal: no `+`, no leading zeros, no trailing fractional zeros, no `-0` | quantity (amount, unit, bounds) / `xsd:decimal` + unit |
| `time` | optional `calendar: "julian"`; absent means proleptic Gregorian | ISO 8601 reduced precision `YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-MM-DDThh:mm:ssZ`, optional leading `-`, and ISO 8601-2 (EDTF) unspecified digits `YYYX` (decade), `YYXX` (century), `YXXX` (millennium) | time; Wikibase precision codes 6–11 and 14 map one-to-one to these forms |

**Precision is carried by the lexical form**, as ISO 8601 reduced precision and EDTF already standardise:
`"1921"` is year precision, `"1921-05"` month, `"192X"` decade. There is no separate `precision` field
to disagree with the value. Wikibase marks codes 12–14 unused [R04 M2]. C1 still keeps second precision
(the full UTC datetime form) for non-Wikidata sources such as event timestamps, but has no hour or minute
precision. Codes 0–5 (coarser than a millennium) are deferred.

**Equality** is JSON equality of the canonical literal, so precision takes part:
`{"datatype":"time","value":"1921"}` ≠ `{"datatype":"time","value":"1921-05-02"}` as values.
Precision-aware *matching* (a finer value refines a coarser one, case I11 [R01 §6.5]) is a scorer rule
(`truncate_to_gold`, §9), not identity. Where the contract uses the word datatype, it means one of these
five. Coordinates and booleans are deferred to 1.1 (§12).

### 2.7 Arity, settled

```
arity(e)        = |{ b ∈ bindings(e) : slot(b) ∈ {core, qualifier}  and  b is not novalue/unbound }|
participants(e) = number of distinct values among those bindings (each somevalue counts as distinct)
```

Each binding counts once: repeated fillers count separately, and a node in two roles counts twice.
`somevalue` counts, because a filler exists. `novalue` does not, because it asserts absence. `unbound`
does not, because it is not yet a filler. `meta` bindings do not count. Valid time does not, because it
is not a binding. This agrees with the KB sample (`f2`: two agents plus one effect gives arity 3) and with
R01 D-06. The library function `khg_contracts.arity(edge, schema)` is the only implementation P3a, P9
and C5 may use. Arity is **never stored**, so a stored `arity` field is malformed (M41, formerly V15).

Fixture values, computed by `checks_schema.py`:

- `f3` (TP53 as regulator and target): arity 3, participants 2.
- `f5` (YYZ at positions 0 and 2): arity 5, participants 4.
- `f6`: arity 3, because `named-as` is a meta binding.
- `f8` (`novalue`) and `g1` (`unbound`): arity 1 each.

### 2.8 Slot classes: `core`, `qualifier`, `meta`

Each role *usage* in the relation schema declares a slot class, following Wikidata's property-scope
precedent [R04 M1 §1.4]. The three classes:

- `core` makes up the fact and its core key [C1-R17].
- `qualifier` adds detail to it; qualifiers can only narrow the answer set [R01 §6.1; SCH §4].
- `meta` is statement metadata: rank reasons, surface forms, dispute notes. It is excluded from arity, from
  content keys and from P6's schema hypergraph [R04 O12, risk 7]. The R04 §8.2 probe found `P2241` and
  `P7452` allowed on all 17 sampled Wikidata properties.

R04 O12 proposed a fourth class, `time`. It is not needed here, because the validity roles (`P580`,
`P582`) are lifted into `valid` (§2.13), so the class would always be empty. Point-in-time roles stay
qualifiers because they are content: `population`'s key includes `point-in-time` [R04 §3.3, R01 §6.2
case 2a].

### 2.9 Direction

Direction belongs to the binding and is separate from the role [C1-R19]. A role usage may declare a
default `direction`. Bindings inherit it, canonical form materialises it, and a contradicting explicit
direction is malformed (S011). A node may be in the tail and the head of one edge through two bindings,
which the HIF paper explicitly allows [R02 §3, p.3–4] and XGI's `DiHypergraph` holds [R03 row 4].

### 2.10 Nesting (facts about facts)

A binding may be `{"role": r, "edge": id}` if the role usage lists the referenced edge's relation in
`edges` (or `"*"`). The reference must resolve in scope: within the document, or within store ∪ batch for
C2 (S013). The graph of edge references must be acyclic (S014) [C1-R23]. Depth is unbounded in C1, and
the conformance suite covers one level [R01 D-11]. In HIF the referenced edge appears as the derived node
`_:edge:<id>` with `attrs.edge = <id>`. It is explicit and never inferred from id equality, because
upstream data reuses node ids as edge ids with no structural meaning [R02 §11.7, case 03].

### 2.11 Special values and UNBOUND

| `special` | Meaning | Counts toward `min`? | Arity | Restrictions |
|---|---|---|---|---|
| `somevalue` | A filler exists but is unknown (Wikidata "unknown value") [C1-R08] | yes (the Wikibase convention [R04 M2]) | counts | Two `somevalue`s are never equal to each other in keys (existential) |
| `novalue` | Asserted absence: "this reaction has no catalyst" [C1-R08, OWA] | the role is satisfied by declared absence | does not count | May not co-occur with another value of the same role (S009) |
| `unbound` | An open slot of a goal, waiting to be bound [C1-R09] | not checked (goals are exempt from `min`) | does not count | Only when `status` is `goal` (S008). The expected type is the role usage's filler types; per-slot narrowing is deferred to P11's version (§12) |

A goal becomes a fact by a new version whose unbound slots are bound and whose status is `asserted`, with
evidence (§2.14; scenario C2-19).

### 2.12 Confidence

Confidence lives **only on evidence records**, as `{"value", "scale"}`:

- `"scale": "probability"`: `value` is in [0, 1].
- `"scale": "score"`: requires `min` < `max`, and `value` is in [min, max] (S021).

A bare number is malformed (M39) [C1-R49]. There is no fact-level confidence field. Producers emit
scores per activity (a P9 extraction, a P8 completion), and belief in a fact is a computation over its
evidence (INDRA's belief scorer [R04 M6]), which consumers declare in C5 configurations. HIF `weight`
never carries confidence and is never read back as confidence [C1-R49, C1-R51; R03 D6].

### 2.13 Time

**Valid time** is a field on the hyperedge: `valid: {"from": t, "until": t}`, half-open. Both bounds use
the `time` lexical forms of §2.6.

- `from` denotes the first instant of its period; `until` (exclusive) the first instant of its period.
- A missing `from` means an unbounded past; a missing `until` means +∞. No sentinel is written [R04 M4].
- A missing `valid` means no temporal restriction is asserted.
- VITA's four forms [C1-R46] are derived, not stored: Since = `from` only; Until = `until` only; Period =
  both; Invariant = no `valid`.
- `as_of(t)` holds iff `from ≤ t < until` under this start-instant reading. A precision-aware
  three-valued reading is deferred (§12).

**Wikidata mapping, deterministic** [C1-R47, D-07]. The schema's `valid-roles` names the global roles
lifted into `valid`, for example `{"from": "start-time", "until": "end-time"}`.

- `P580` (start time) maps to `from` unchanged.
- `P582` (end time) is inclusive in Wikidata, so it maps to `until` = the next period at the same
  precision. Examples: `1715-09-01` (day) gives `1715-09-02`; `2020` (year) gives `2021`. The Wikidata
  projection inverts this.
- `P585` (point in time) stays a qualifier binding.
- Lifted roles may not appear as bindings (S024) or in relation usages (D005).

This meets C1-R47's intent: one deterministic mapping, and no conflation of qualifier time with validity
time [SCH §5]. It deliberately drops its letter: start and end are not *stored* as bindings. They are
re-emitted as qualifier pairs by the hyper-relational projection that P3b uses. Decision log §13 and risk
§14.

**Transaction time** is `recorded` on each stored *version*. The end of a version's transaction interval
is the next version's `recorded`, so it is never written and cannot contradict (formerly V31). `as_at(τ)`
selects the latest version with `recorded ≤ τ`. Stored versions are immutable (F8) [R04 O6].
Per-binding validity [C1-R48, MAY] is deferred to 1.2.

### 2.14 Lifecycle: four axes, transitions, supersession

The four axes of F7 [R04 M5 table]:

| Axis | Field | Values | Changed by |
|---|---|---|---|
| Belief | `status` | `candidate` (queue only), `asserted`, `superseded`, `retracted`, `goal` | lifecycle transitions below |
| World | `valid` | interval | a new version with a different interval. **Not a status change**: a fact that *ended* stays `asserted` (F7; Wikidata "outdated → end time" [R04 M5]) |
| Editorial | `rank` | `preferred`, `normal`, `deprecated` | a curator; a new version |
| Governance | `visibility` | `visible`, `suppressed` | a governance action; a new version |

There is no `disputed` status. Case 3b (two claims for the same interval [R01 §6.3]) is handled the way
Wikidata handles it: both stay asserted, one is ranked `deprecated`, and a key conflict is reported by the
store (§6). A `disputed` status can be added in 1.1 if P7 needs it.

**Transition table** (checked by C2 `put`, code S030):

| From \ to | asserted | goal | superseded | retracted |
|---|---|---|---|---|
| *(new edge)* | yes | yes | no | no |
| asserted | yes (new version: valid, rank, visibility, evidence, attrs) | no | yes, with a `khg:supersedes` record | yes, with a `khg:retracts` record |
| goal | yes, when no `unbound` remains and there is ≥ 1 evidence | yes (binds some slots) | no | yes, with a `khg:retracts` record |
| superseded | no | no | yes (rank or visibility only) | no |
| retracted | no | no | no | yes (visibility only) |

`candidate` becomes `asserted` or `goal` only through a C3 `accept`; the store refuses candidates (S028).
Within one edge id, `relation` and `bindings` are immutable (S031), except that a goal's `unbound` slots
may be bound. A change of participants is a *new* edge, linked by supersession. That is how arity changes
(case 4a option ii) and refinements stay explicit and logged [C3-R10].

**Supersession and retraction are records** (F8) [R04 O5; nanopublications' `npx:supersedes` and
`npx:retracts`]. They are edges of two built-in relations, so they reuse everything: evidence, `recorded`,
HIF export and C2 queries.

- `khg:supersedes`: `khg:superseding` → the new edge, `khg:superseded` → the old edge, and `khg:reason` ∈
  {`correction`, `refinement`, `duplicate`}.
- `khg:retracts`: `khg:retracted` → the edge, and `khg:reason` ∈ {`incorrect`, `unsupported`,
  `withdrawn-by-source`, `other`}. The reasons are modelled on Wikidata's `P2241` items [R04 M5].

`superseded` means **belief revision only**.

Validity rules, all code S022 unless noted:

- An edge with status `superseded` has a `superseded-by` list, and it equals the set of `khg:supersedes`
  records that name it.
- A `khg:supersedes` record may only name an edge whose status is `superseded`.
- A retracted edge needs a `khg:retracts` record.
- Supersession never crosses relations or declared key bindings (S023).
- An edge never supersedes itself.
- The supersession graph is acyclic (it is a nesting graph, S014).

In C2 the three writes form one atomic `put` batch: the new fact, the old fact's `superseded` version and
the record (C2-R19; scenario C2-13).

> **Objection to F8 (designed within it).** The `superseded-by` index field duplicates what the
> `khg:supersedes` records already say. Every C2 backend can find them with
> `find("khg:supersedes", [{"role": "khg:superseded", "edge": X}])`, and every P1 backend supports
> hyperedge-valued fillers [R01 §3, R04 M9]. So the field adds a consistency rule and a malformed case
> (M36, M68) and gains no capability. It is included as specified: optional, derived, and validated for
> agreement. I recommend making it store-internal in 1.1 if no P1 backend reads it.

### 2.15 Evidence

Evidence is a flat record per source [C1-R35–R40, D-14]. It is a sub-record of the edge, not a record
kind.

| Field | Type | Meaning, and the precedent it follows |
|---|---|---|
| `id` | string, unique within the edge | Local id; bindings cite it |
| `type` | `curated` \| `imported` \| `extracted` \| `inferred` | Evidence type [C1-R38]. It maps to ECO's assertion method: `curated` → manual assertion ECO:0000218; `imported` → ECO:0000313 (imported information used in automatic assertion); `extracted`, `inferred` → ECO:0007669 (computational evidence used in automatic assertion) [R04 M6]. Model-produced facts are therefore always distinguishable |
| `source` | string | Document, dataset or item id (PROV `wasDerivedFrom` target) |
| `digest` | `sha256:<64 hex>` | SHA-256 of the source text, NFC, UTF-8 (F11 document hash) |
| `exact`, `prefix`, `suffix` | strings | W3C Web Annotation `TextQuoteSelector` names |
| `start`, `end` | integers | W3C `TextPositionSelector`: **Unicode code points, half-open, over the NFC text** (F11). `start` requires `end`, `digest` and `exact`; `len(exact) = end − start` (S018) |
| `reference` | array of bindings | A Wikidata-style reference (a set of role–value pairs), reusing the binding shape [C1-R37]; for example `stated-in`, `retrieved` |
| `agent`, `version`, `run`, `model`, `prompt`, `params` | strings; `params` an object | The activity: tool or person, its version, run id, model, prompt or skill version, and decoding parameters such as temperature and seed [C1-R38, C3-R02]. `extracted` and `inferred` require `agent`, `version` and `run` (S019) |
| `confidence` | `{value, scale[, min, max]}` | The activity's own score (§2.12) |

Evidence `e2` in the fixture carries a real span. Its source text contains U+1F48A before the span, so
its code-point `start` 196 would be 197 in UTF-16 and 200 in UTF-8 bytes. `make_span.py` checks all
three. Importers convert UTF-16 and inclusive-end offsets (for example SemMedDB's "last character
position") at import [R04 M6, risk 6]. Epistemic flags (negated, hypothesis) are deferred to 1.1.

### 2.16 Identity: the four identifiers of F6

Only the first is stored. The other three are computed by one rule, `"sha256:" + hex(SHA-256(JCS(x)))`,
where JCS is RFC 8785. For the payloads hashed here (ASCII keys, strings, small integers, never a float),
JCS equals Python's `json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` in UTF-8.

| # | Identifier | Definition | Used for | Stored? |
|---|---|---|---|---|
| 1 | `edge` | opaque id | record identity, references, store keys | yes |
| 2 | **content key** `content_key(e, scope)` | hash of `{"relation", "bindings": sorted binding keys}`, where a binding key is `{role, <value>, direction?, position (ordered roles only)}`. `scope="all"` uses core and qualifier bindings; `"core"` uses core only. Meta bindings, valid time, evidence, status and rank never count | dedup (all), leak checks and refinement detection (core), stability S-M1 on both keys [C1-R02, C3-R04] | no; recorded in C3 items and C5 outputs, recomputed by validators (Q003) |
| 3 | **key digest** `key_digest(e)` | hash of `{"relation", "key": sorted binding keys of the declared key roles}`. An absent key role contributes nothing (absent equals absent). A `somevalue` or `unbound` key role gives no digest (never collides) | key lookup, key-conflict detection, supersession consistency (S023) [C1-R28] | no |
| 4 | **event key** `event_key(e, ev)` | hash of `{"content": content_key(e), source, digest, start, end, agent, version, model, prompt}`, absent fields omitted. `run`, `params`, `id` and `confidence` are excluded | re-extracting the same span with the same configuration gives the same event, never a fork [C1-R03]. A second source gives a new event (queue example `q2`, §7.7) | no; recorded in C3 items |

Fixture values, computed by the prototype:

- `f1`: content `sha256:65f4cbe8…`, core `sha256:a8603e53…`, and the event key of `e2` is
  `sha256:b19a0902…`.
- `f10` and `f11` share the key digest `sha256:3b7d0853…`: the same organisation under a temporal key.
  That is why one of them had to be superseded rather than both asserted.

Canonicalisation makes permuted fillers of a repeated role equal (I8) and keeps role swaps distinct (case
2b) [R01 §6]. Storing derived keys would invite disagreement between the stored and the recomputed value,
the same failure the stored `arity` of V15 invites.

### 2.17 Versioning of the record format

Every document header, HIF metadata block, schema document and queue header carries
`khg-profile: "<semver>"`. The JSON Schemas carry `$id`s of the form
`urn:khg-contracts:schema:<name>:<semver>`, and relation-type schemas `<name>/<semver>`. Section 11 gives
the rules.

### 2.18 The gate fixture in C1 (validated)

It covers every item R01 D-20 names:

- a node in two roles, tail and head (`f3`)
- repeated roles (`f2` agent ×2, `f5` stop ×3)
- an ordered role with the same airport twice (`f5`)
- typed literals with precision: quantity with a unit, `time` `"2019"`, `valid.from` `"2019-05"`,
  `string`, and `text@de`
- a nested reference (`f9` → `f1`)
- direction on every binding
- qualifiers
- evidence on a binding (`f1` dosage → `e2`)
- non-ASCII ids (`ex:Zürich`, `ex:羽田`)
- `somevalue` (`f4`) and `novalue` (`f8`)
- an unbound goal slot (`g1`)
- a superseded pair with its record (`f10`, `f11`, `s1`)
- a Wikidata-style reference (`f6`)
- a meta binding (`named-as`)

Validated against the C1 schema under jsonschema and fastjsonschema, and semantically against the schema
in §3.3:

```json
{
 "metadata": {"khg-profile": "1.0.0", "khg-schema": "gate-demo/1.0.0", "title": "P2 gate fixture (adversarial)"},
 "nodes": [
  {"node": "ex:ADA", "types": ["Organisation"], "label": "American Diabetes Association"},
  {"node": "ex:HeLa", "types": ["CellLine"], "label": "HeLa"},
  {"node": "ex:MYC", "types": ["Gene"], "label": "MYC"},
  {"node": "ex:R1", "types": ["Reaction"], "label": "reaction R1"},
  {"node": "ex:R2", "types": ["Reaction"], "label": "reaction R2"},
  {"node": "ex:T2DM", "types": ["Disease"], "label": "type 2 diabetes mellitus"},
  {"node": "ex:TP53", "types": ["Gene"], "label": "TP53"},
  {"node": "ex:YYZ", "types": ["Airport"], "label": "Toronto Pearson"},
  {"node": "ex:Zürich", "types": ["City"], "label": "Zürich"},
  {"node": "ex:acme", "types": ["Organisation"], "label": "Acme"},
  {"node": "ex:adults", "types": ["Population"], "label": "adults"},
  {"node": "ex:air-canada", "types": ["Organisation"], "label": "Air Canada"},
  {"node": "ex:ana", "types": ["Person"], "label": "Ana"},
  {"node": "ex:anna", "types": ["Person"], "label": "Anna"},
  {"node": "ex:hypoglycaemia", "types": ["AdverseEffect"], "label": "hypoglycaemia"},
  {"node": "ex:insulin", "types": ["Drug"], "label": "insulin"},
  {"node": "ex:metformin", "types": ["Drug"], "label": "metformin"},
  {"node": "ex:羽田", "types": ["Airport"], "label": "東京国際空港 (羽田)"}
 ],
 "edges": [
  {"edge": "f1", "relation": "treats", "status": "asserted", "rank": "preferred", "bindings": [{"role": "condition", "node": "ex:T2DM", "direction": "head"}, {"role": "dosage", "literal": {"datatype": "quantity", "value": "500", "unit": "ex:milligram"}, "direction": "tail", "evidence": ["e2"]}, {"role": "population", "node": "ex:adults", "direction": "tail"}, {"role": "treatment", "node": "ex:metformin", "direction": "tail"}], "valid": {"from": "2024-01-01"}, "evidence": [{"id": "e1", "type": "curated", "source": "doc:ada-standards-2024"}, {"id": "e2", "type": "extracted", "source": "doc:pmid-0000001", "digest": "sha256:7dac853671047fe09ef4dd22d52818dfd1a03a3a0b06ca2699b7068675e19a31", "exact": "500 mg metformin", "prefix": "start with ", "suffix": " twice daily", "start": 196, "end": 212, "agent": "extractor-x", "version": "0.3.1", "run": "p9-run-1", "model": "model-y-2026-06", "prompt": "skill:treats/v2", "params": {"temperature": 0.0, "seed": 13}, "confidence": {"value": 0.82, "scale": "probability"}}]},
  {"edge": "f2", "relation": "co-administration-causes", "status": "asserted", "bindings": [{"role": "agent", "node": "ex:insulin", "direction": "tail"}, {"role": "agent", "node": "ex:metformin", "direction": "tail"}, {"role": "effect", "node": "ex:hypoglycaemia", "direction": "head"}], "evidence": [{"id": "e1", "type": "curated", "source": "doc:ada-standards-2024"}]},
  {"edge": "f3", "relation": "regulates", "status": "asserted", "bindings": [{"role": "context", "node": "ex:HeLa", "direction": "tail"}, {"role": "regulator", "node": "ex:TP53", "direction": "tail"}, {"role": "target", "node": "ex:TP53", "direction": "head"}], "evidence": [{"id": "e1", "type": "curated", "source": "doc:review-2021"}]},
  {"edge": "f4", "relation": "regulates", "status": "asserted", "bindings": [{"role": "regulator", "special": "somevalue", "direction": "tail"}, {"role": "target", "node": "ex:MYC", "direction": "head"}], "evidence": [{"id": "e1", "type": "curated", "source": "doc:review-2021"}]},
  {"edge": "f5", "relation": "flight", "status": "asserted", "bindings": [{"role": "carrier", "node": "ex:air-canada", "direction": "tail"}, {"role": "flight-number", "literal": {"datatype": "string", "value": "AC 123"}, "direction": "tail"}, {"role": "stop", "node": "ex:YYZ", "position": 0, "direction": "head"}, {"role": "stop", "node": "ex:羽田", "position": 1, "direction": "head"}, {"role": "stop", "node": "ex:YYZ", "position": 2, "direction": "head"}], "evidence": [{"id": "e1", "type": "imported", "source": "doc:timetable-2026"}]},
  {"edge": "f6", "relation": "population", "status": "asserted", "bindings": [{"role": "count", "literal": {"datatype": "quantity", "value": "421878", "unit": "1"}, "direction": "head"}, {"role": "named-as", "literal": {"datatype": "text", "value": "Zürich", "lang": "de"}, "direction": "tail"}, {"role": "place", "node": "ex:Zürich", "direction": "tail"}, {"role": "point-in-time", "literal": {"datatype": "time", "value": "2019"}, "direction": "tail"}], "evidence": [{"id": "e1", "type": "imported", "reference": [{"role": "retrieved", "literal": {"datatype": "time", "value": "2026-09-20"}}, {"role": "stated-in", "node": "ex:stat-zh-2020"}]}]},
  {"edge": "f8", "relation": "catalysed-by", "status": "asserted", "bindings": [{"role": "catalyst", "special": "novalue", "direction": "head"}, {"role": "reaction", "node": "ex:R1", "direction": "tail"}], "evidence": [{"id": "e1", "type": "curated", "source": "doc:enzyme-db-2025"}]},
  {"edge": "f9", "relation": "asserts", "status": "asserted", "bindings": [{"role": "asserter", "node": "ex:ADA", "direction": "tail"}, {"role": "statement", "edge": "f1", "direction": "head"}], "evidence": [{"id": "e1", "type": "curated", "source": "doc:ada-standards-2024"}]},
  {"edge": "f10", "relation": "chief-executive", "status": "superseded", "superseded-by": ["f11"], "bindings": [{"role": "organisation", "node": "ex:acme", "direction": "tail"}, {"role": "person", "node": "ex:ana", "direction": "head"}], "valid": {"from": "2019-05"}, "evidence": [{"id": "e1", "type": "extracted", "source": "doc:news-1", "agent": "extractor-x", "version": "0.3.1", "run": "p9-run-1"}]},
  {"edge": "f11", "relation": "chief-executive", "status": "asserted", "bindings": [{"role": "organisation", "node": "ex:acme", "direction": "tail"}, {"role": "person", "node": "ex:anna", "direction": "head"}], "valid": {"from": "2019-05"}, "evidence": [{"id": "e1", "type": "curated", "source": "doc:acme-annual-report-2019"}]},
  {"edge": "g1", "relation": "catalysed-by", "status": "goal", "bindings": [{"role": "catalyst", "special": "unbound", "direction": "head"}, {"role": "reaction", "node": "ex:R2", "direction": "tail"}]},
  {"edge": "s1", "relation": "khg:supersedes", "status": "asserted", "bindings": [{"role": "khg:reason", "literal": {"datatype": "string", "value": "correction"}, "direction": "tail"}, {"role": "khg:superseded", "edge": "f10", "direction": "head"}, {"role": "khg:superseding", "edge": "f11", "direction": "tail"}], "evidence": [{"id": "e1", "type": "curated", "source": "doc:acme-annual-report-2019"}]}
 ]
}
```

The C1 document JSON Schema (`khg-document-1.0.0.json`) is in the work directory. It has 17 bundled
definitions: `binding`, `confidence`, `datetime`, `decimal`, `direction`, `edge`, `evidence`, `id`,
`literal`, `metadata`, `name`, `node`, `profileVersion`, `schemaRef`, `status`, `timeValue` and `valid`.
The load-bearing patterns:

```json
"id":        {"type": "string", "minLength": 1, "pattern": "^(?!_:)[^\\u0000-\\u001f\\u007f]+$"},
"name":      {"type": "string", "pattern": "^(?!_:)[^\\s/:\\u0000-\\u001f\\u007f]+(:[^\\s/:\\u0000-\\u001f\\u007f]+)?$"},
"timeValue": {"type": "string", "pattern": "^-?([0-9]{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01])(T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z)?)?)?|[0-9]{3}X|[0-9]{2}XX|[0-9]XXX)$"},
"decimal":   {"type": "string", "pattern": "^(0|-?[1-9][0-9]*|-?(0|[1-9][0-9]*)\\.[0-9]*[1-9])$"},
"binding":   {"…": "…", "oneOf": [{"required": ["node"]}, {"required": ["literal"]}, {"required": ["edge"]}, {"required": ["special"]}]},
"edge":      {"…": "…", "if": {"properties": {"status": {"const": "superseded"}}}, "then": {"required": ["superseded-by"]}, "else": {"not": {"required": ["superseded-by"]}}}
```

Names (roles, relations, types) allow Unicode, because R03's c13 uses `治疗` as a role. They exclude
whitespace, `/` (needed to parse derived ids) and `:` except as one prefix separator. NFC is checked in
layer S, because JSON Schema cannot express it.

### 2.19 Projections in v1 (library functions over C1, `khg_contracts.project`)

| Projection | Function | Rule | Lossless? | Consumers |
|---|---|---|---|---|
| role-aware HIF | `to_hif` / `from_hif` | §4 | yes | P2 gate, P1, P5 |
| hyper-relational statement | `project.hyper_relational(e, schema)` | Main triple = (filler of the relation's unique **core tail** role, relation, filler of its unique **core head** role). That is the `primary` pair [C1-R18], *derived* from declared directions rather than stored, as SCH pitfall 1 asks. All other core and qualifier bindings become (role, value) qualifier pairs. `valid.from` is re-emitted as the `from` valid-role; `valid.until` is re-emitted as the `until` valid-role, converted back to an inclusive end (§2.13). Relations without exactly one core tail and one core head role raise `ProjectionError`; an explicit `primary` field is 1.1 | no: evidence, direction and meta are dropped | P3b (StarE-style input), P3a (leak check on the main triple) |
| positional tuple | `project.positional(e, schema)` | Core roles, then qualifier roles, each sorted by role id. Repeated fillers in canonical binding order (ordered roles by `position`) | no (roles become positions) | P3b (HypE, HYPER), P8 |
| role–value set | `project.role_values(e)` | the multiset {(role, value)} of core and qualifier bindings | no | NaLP/RAM-style models, P3b |
| text | `project.render(e, schema, labels)` | `<relation label>(<role label>: <value label>; …)` in canonical binding order | no | P10 prompts, P7's flat-store baseline [C1-R61] |

All projections take `drop_literals=False`: dropping literals is a projection option, never a storage
choice [C1-R11]. The pairwise (clique or star) projection with back-pointers [C1-R59] is for P4, which is
Phase 2, so it ships in 1.1. The RDF relation-instance, incidence-table and property-graph layouts are
specified in §6.8. Their code lives in P1's adapters, and moves into the package in 1.1 if a second
consumer needs it [C1-R57, C1-R60].

---

## 3. Relation-type schema language

A small JSON document validated by a draft-07 meta-schema (`khg-schema-1.0.0.json`), plus Python checks
(layer D). Its concepts mirror LinkML: global slots, per-class `slot_usage`, and `unique_keys`. A LinkML,
TypeQL, SQL or SHACL generator is therefore mechanical when a consumer needs one (§12) [R04 O10; R01
D-15]. It adds what none of those languages has: temporal keys with a collision policy, slot classes, and
a semver in the id [R04 §8.3].

### 3.1 Document fields

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `khg-schema` | `<name>/<semver>` | yes | Schema id with semantic version [C1-R32, PLAN §7] |
| `khg-profile` | `1.x.y` | yes | Version of this schema language, the same number as the C1 format |
| `label` | string | no | — |
| `types` | object: type name → `{label?, aliases?, mappings?}` | no | Entity types, flat in v1 |
| `roles` | object: role name → `{label?, aliases?, mappings?}` | yes | **The global role vocabulary** (F4) [C1-R26]. `aliases` holds raw extracted phrases; `mappings` holds external ids, for example `{"wikidata": "P585"}` [C1-R31] |
| `valid-roles` | `{from?, until?}` → role names | no | The global roles an importer lifts into `valid` (§2.13) |
| `relations` | object: relation name → relation | yes | Relation types |

A **relation** is `{label?, aliases?, mappings?, roles, key?}`:

- `roles` is an object mapping each role name to a **usage**, with at least one entry [V43].
- `key` is `{roles: [role names], temporal: bool = false, on-collision: "reject" | "flag" | "end-older" |
  "supersede-older" = "flag"}` [R04 O3]. `end-older` requires `temporal: true`.

A **usage** has these fields:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `slot` | `core` \| `qualifier` \| `meta` | required | Slot class (§2.8) [C1-R17] |
| `types` | array of type names | — | Allowed entity types, as a disjunction (VerbNet's `logic="or"` [R04 M1]) |
| `datatypes` | array ⊆ {string, text, iri, quantity, time} | — | Allowed literal datatypes |
| `edges` | array of relation names, or `["*"]` | — | Hyperedge references allowed (nesting). This replaces SCH §6.1's relation-level `nestable` with a per-role, per-target declaration |
| `values` | array of strings | — | Allowed lexical values, a closed list (Wikidata "one-of constraint", SHACL `sh:in`). Requires `datatypes` |
| `min` | integer ≥ 0 | 0 | Within-fact minimum; `min ≥ 1` means required [C1-R25] |
| `max` | integer ≥ 1 or `null` (unbounded) | 1 | Within-fact maximum. The default of 1 matches TypeDB's `relates` default `card(0..1)` [R04 M1 §1.3] |
| `ordered` | boolean | false | Bindings carry `position` [C1-R15] |
| `direction` | `tail` \| `head` | — | Default direction of the role's bindings [C1-R19] |
| `label` | string | — | Local label for this usage (LinkML's "local naming") |

At least one of `types`, `datatypes` or `edges` is required.

**Symmetric and interchangeable roles** use *one* role with `max > 1` and `ordered: false`, never
`role_1`/`role_2` [R04 M1 §1.5]. The fillers are a multiset, and canonical sorting makes identity
invariant under permutation (case I8). A symmetric binary relation is `partner` with `min: 2, max: 2`.
FrameNet- or VerbNet-style numbered pairs are folded to the plural role by the importer. Within-fact
cardinality (`min`/`max`) and across-fact participation (the key) are kept apart, as R04 M1 §1.3 asks.

**Deferred** (§12): co-occurrence constraints (`requires`, `excludes`, `at-least-one-of`,
`must-differ`, `must-agree`) [C1-R34 MAY; R04 M1]; an explicit `primary` pair [C1-R18 SHOULD] (v1
derives it from the unique core tail and head roles, §2.19); type hierarchy; `kind: "rule"`; `extends`.

### 3.2 Key semantics

At most one *asserted* edge per key binding may exist, at any instant if `temporal`, or at all otherwise
[C1-R28]. The key binding is the multiset of the key roles' bindings. An absent key role equals an absent
key role (conservative). An edge with `somevalue` or `unbound` in a key role takes part in no collision.
`on-collision` says what the store does on `put` [R04 M3 §3.3]:

| Policy | Store `put` | Linter (C3) | Precedent |
|---|---|---|---|
| `reject` | raises `KHG-S029` | violation | SQL:2011 / PostgreSQL 18 `WITHOUT OVERLAPS` |
| `flag` (default) | writes; reports the conflict in `PutResult.conflicts` | warning | Wikidata single-value constraint (advisory) |
| `end-older` (temporal keys only) | writes; reports | info, and proposes a candidate new version of the older edge with `valid.until` = the newer `valid.from` | Graphiti invalidation, *without* the in-place overwrite [R04 M4] |
| `supersede-older` | writes; reports | info, and proposes a `khg:supersedes` candidate | Wikidata single-best-value plus deprecation |

The store never rewrites another record as a side effect of `put`. Automatic end or supersession would be
a hidden write, and merges through key collisions are forbidden [C3-R10]. The OWL-style `same_fact`
policy of R04 O3 is dropped for that reason: it would merge on collision.

### 3.3 The complete example: the gate schema (validated against the meta-schema)

It has eight relations:

- `treats` has a non-temporal key.
- `population` has a key that includes a qualifier, with `reject`.
- `chief-executive` has a temporal key with `end-older`.
- `co-administration-causes` has a repeated interchangeable role.
- `flight` has an ordered role.
- `asserts` nests `treats` edges.
- `catalysed-by` hosts the `novalue` fact and the goal.

The roles are global: `population` is both a relation name and a role name used in `treats`, which is
legal because relations and roles live in different maps.

```json
{
  "khg-schema": "gate-demo/1.0.0",
  "khg-profile": "1.0.0",
  "label": "P2 gate fixture schema",
  "types": {
    "Drug": {"label": "drug"}, "Disease": {"label": "disease"}, "Population": {"label": "population"},
    "AdverseEffect": {"label": "adverse effect"}, "Gene": {"label": "gene"}, "CellLine": {"label": "cell line"},
    "Organisation": {"label": "organisation"}, "Person": {"label": "person"}, "Airport": {"label": "airport"},
    "City": {"label": "city"}, "Reaction": {"label": "reaction"}, "Enzyme": {"label": "enzyme"}
  },
  "roles": {
    "treatment": {"label": "treatment"}, "condition": {"label": "condition"}, "dosage": {"label": "dosage"},
    "population": {"label": "population"}, "agent": {"label": "agent"}, "effect": {"label": "effect"},
    "regulator": {"label": "regulator"}, "target": {"label": "target"}, "context": {"label": "context"},
    "carrier": {"label": "carrier"}, "stop": {"label": "stop"}, "flight-number": {"label": "flight number"},
    "place": {"label": "place"},
    "count": {"label": "count", "mappings": {"wikidata": "P1082"}},
    "point-in-time": {"label": "point in time", "mappings": {"wikidata": "P585"}},
    "named-as": {"label": "subject named as", "mappings": {"wikidata": "P1810"}},
    "stated-in": {"label": "stated in", "mappings": {"wikidata": "P248"}},
    "retrieved": {"label": "retrieved", "mappings": {"wikidata": "P813"}},
    "asserter": {"label": "asserter"}, "statement": {"label": "statement"},
    "organisation": {"label": "organisation"}, "person": {"label": "person"},
    "reaction": {"label": "reaction"}, "catalyst": {"label": "catalyst"},
    "start-time": {"label": "start time", "mappings": {"wikidata": "P580"}},
    "end-time": {"label": "end time", "mappings": {"wikidata": "P582"}}
  },
  "valid-roles": {"from": "start-time", "until": "end-time"},
  "relations": {
    "treats": {
      "label": "treats",
      "roles": {
        "treatment": {"slot": "core", "types": ["Drug"], "min": 1, "max": 1, "direction": "tail"},
        "condition": {"slot": "core", "types": ["Disease"], "min": 1, "max": 1, "direction": "head"},
        "dosage": {"slot": "qualifier", "datatypes": ["quantity"], "max": 1, "direction": "tail"},
        "population": {"slot": "qualifier", "types": ["Population"], "max": 1, "direction": "tail"}
      },
      "key": {"roles": ["treatment", "condition", "population"], "temporal": false, "on-collision": "flag"}
    },
    "co-administration-causes": {
      "label": "co-administration causes",
      "roles": {
        "agent": {"slot": "core", "types": ["Drug"], "min": 2, "max": null, "direction": "tail"},
        "effect": {"slot": "core", "types": ["AdverseEffect"], "min": 1, "max": 1, "direction": "head"}
      }
    },
    "regulates": {
      "label": "regulates",
      "roles": {
        "regulator": {"slot": "core", "types": ["Gene"], "min": 1, "max": 1, "direction": "tail"},
        "target": {"slot": "core", "types": ["Gene"], "min": 1, "max": 1, "direction": "head"},
        "context": {"slot": "qualifier", "types": ["CellLine"], "max": 1, "direction": "tail"}
      }
    },
    "flight": {
      "label": "scheduled flight",
      "roles": {
        "carrier": {"slot": "core", "types": ["Organisation"], "min": 1, "max": 1, "direction": "tail"},
        "stop": {"slot": "core", "types": ["Airport"], "min": 2, "max": null, "ordered": true, "direction": "head"},
        "flight-number": {"slot": "qualifier", "datatypes": ["string"], "max": 1, "direction": "tail"}
      }
    },
    "population": {
      "label": "population",
      "roles": {
        "place": {"slot": "core", "types": ["City"], "min": 1, "max": 1, "direction": "tail"},
        "count": {"slot": "core", "datatypes": ["quantity"], "min": 1, "max": 1, "direction": "head"},
        "point-in-time": {"slot": "qualifier", "datatypes": ["time"], "min": 1, "max": 1, "direction": "tail"},
        "named-as": {"slot": "meta", "datatypes": ["text"], "max": 1, "direction": "tail"}
      },
      "key": {"roles": ["place", "point-in-time"], "temporal": false, "on-collision": "reject"}
    },
    "chief-executive": {
      "label": "chief executive officer",
      "roles": {
        "organisation": {"slot": "core", "types": ["Organisation"], "min": 1, "max": 1, "direction": "tail"},
        "person": {"slot": "core", "types": ["Person"], "min": 1, "max": 1, "direction": "head"}
      },
      "key": {"roles": ["organisation"], "temporal": true, "on-collision": "end-older"}
    },
    "asserts": {
      "label": "asserts",
      "roles": {
        "asserter": {"slot": "core", "types": ["Organisation"], "min": 1, "max": 1, "direction": "tail"},
        "statement": {"slot": "core", "edges": ["treats"], "min": 1, "max": 1, "direction": "head"}
      }
    },
    "catalysed-by": {
      "label": "catalysed by",
      "roles": {
        "reaction": {"slot": "core", "types": ["Reaction"], "min": 1, "max": 1, "direction": "tail"},
        "catalyst": {"slot": "core", "types": ["Enzyme"], "min": 1, "max": 1, "direction": "head"}
      }
    }
  }
}
```

The **built-in schema** `khg/1.0.0` is always loaded. The `khg:` prefix is reserved for it (D006). It is
validated against the same meta-schema:

```json
{
  "khg-schema": "khg/1.0.0", "khg-profile": "1.0.0", "label": "Built-in lifecycle relations (always loaded)",
  "types": {},
  "roles": {"khg:superseding": {"label": "superseding fact"}, "khg:superseded": {"label": "superseded fact"},
            "khg:retracted": {"label": "retracted fact"}, "khg:reason": {"label": "reason"}},
  "relations": {
    "khg:supersedes": {"label": "supersedes (belief revision)", "roles": {
      "khg:superseding": {"slot": "core", "edges": ["*"], "min": 1, "max": 1, "direction": "tail"},
      "khg:superseded": {"slot": "core", "edges": ["*"], "min": 1, "max": 1, "direction": "head"},
      "khg:reason": {"slot": "qualifier", "datatypes": ["string"], "values": ["correction", "refinement", "duplicate"], "min": 1, "max": 1, "direction": "tail"}}},
    "khg:retracts": {"label": "retracts (belief withdrawn, no replacement)", "roles": {
      "khg:retracted": {"slot": "core", "edges": ["*"], "min": 1, "max": 1, "direction": "head"},
      "khg:reason": {"slot": "qualifier", "datatypes": ["string"], "values": ["incorrect", "unsupported", "withdrawn-by-source", "other"], "min": 1, "max": 1, "direction": "tail"}}}
  }
}
```

### 3.4 How P6 parses it

```python
schema = khg_contracts.RelationSchema.load("gate-demo.schema.json")      # built-in merged in
schema.hypergraph(slots=("core", "qualifier"), builtin=False) -> dict[str, frozenset[str]]
```

**Rule for "attribute"**: an attribute is a *global role id*. Each relation type becomes the hyperedge of
its role usages whose slot is in `slots`. `meta` is excluded by default, `valid-roles` never appear
(they are never usages), and built-in relations are excluded unless asked for. The output is sorted and
deterministic [C1-R27]. For the gate schema it is:

```
asserts                  {asserter, statement}
catalysed-by             {catalyst, reaction}
chief-executive          {organisation, person}
co-administration-causes {agent, effect}
flight                   {carrier, flight-number, stop}
population               {count, place, point-in-time}
regulates                {context, regulator, target}
treats                   {condition, dosage, population, treatment}
```

GYO reduction of that hypergraph leaves an empty residue, so it is α-acyclic. A deliberately cyclic
schema is three relations `r1 {a, b}`, `r2 {b, c}`, `r3 {c, a}` over global roles `a`, `b`, `c`. GYO
leaves the whole triangle as residue (computed). Adding `r4 {a, b, c}` makes it acyclic again. Both are
two-line schema files, so P6's "constructed cyclic case" is expressible. Because roles are global,
P6's measurement is meaningful: relation-local roles would make every schema a trivially acyclic disjoint
union [R04 §8.2; R01 D-04]. How Wikidata's main-snak roles are named does not change α-acyclicity
[R04 §8.2 reading (i)]. P3a and P6 still have to agree on it before C4 is built.

### 3.5 What the semantic validator checks against a schema

For each edge:

| Check | Code |
|---|---|
| Relation declared | S001 |
| Every role declared for the relation | S002 |
| `min` met, only for asserted, superseded and retracted edges; goals and candidates are exempt [C1-R72] | S003 |
| `max` met | S004 |
| Filler kind allowed: `node` needs `types`, `literal` needs `datatypes`, `edge` needs `edges` | S005 |
| Entity type ∩ allowed types ≠ ∅, when known | S006 |
| Literal in `values`; valid calendar date; quantity within its bounds | S007 |
| `unbound` only on goals | S008 |
| `novalue` exclusive within its role | S009 |
| Ordered roles have unique positions, and unordered roles have none | S010 |
| Direction agrees with the role's declared direction | S011 |
| No duplicate binding | S012 |
| References resolve | S013 |
| No nesting cycles | S014 |
| A referenced edge's relation is allowed | S015 |
| Lifted valid-time roles do not appear as bindings | S024 |

Key conflicts need the store (S029, §6). For a schema document, the meta-schema checks shape (D001) and
Python checks the rest:

| Check | Code |
|---|---|
| Every usage names declared roles, types and relations | D002 |
| Key roles are used by the relation | D003 |
| `min ≤ max` | D004 |
| A valid-time role is not used by any relation | D005 |
| The `khg:` prefix appears only in the built-in schema | D006 |

---

## 4. HIF mapping: the `roles` convention (the external artefact)

### 4.1 The upstream convention: three rules, valid HIF 0.1.0 today

1. **Role.** `incidences[].attrs.role` is a string naming the role the node plays in the edge. This is
   the paper's own example, `{"edge": 1, "node": 3, "attrs": {"role": "PI"}}` [R02 §3, p.7], and the
   upstream compliant fixture `single_incidence_with_attrs.json` [R02 §6].
2. **One record per role.** A node that plays several roles in one edge has one incidence record per
   role. Records of one (edge, node) pair may differ in `direction`, and they must differ in `role` or in
   `attrs.position`. The paper allows a node in both tail and head [R02 §3, p.3–4]. `direction` is
   single-valued, so repeated records are the only schema-valid way to write it, and upstream's own
   compliant test `duplicated_nodes_edges.json` repeats a pair [R02 §3, inconsistency 2].
3. **Declaration.** `metadata["role-convention"] = "1.0.0"`, flat and dash-case as the paper advises
   [R02 §3, p.7]. Optionally `metadata["role-vocabulary"]` holds `{role: label}` or a URL.

Nothing else is required: no schema change, no new key, and no rule about `weight`. R02's cases 01, 02
and 07–09 already show that each of these validates [R02 §5]. The P2 loaders (§5) implement exactly these
three rules, so they can go upstream as reference code.

### 4.2 The KHG profile on top of the convention

| Location | Profile rule | Schema-checked? |
|---|---|---|
| top level | `network-type` ∈ {`directed`, `undirected`}. `asc` is refused, because XGI turns 9 incidences into 39 and drops metadata [R03 D8]. `metadata`, `incidences` and `edges` are required | yes |
| `metadata` | `role-convention`, `khg-profile`, `khg-schema`, `hif-schema` (the exact pinned URL below), `hif-schema-sha256` (the exact hash) are required. `default_attrs` is forbidden, because HyperNetX re-reads it and invents values [R03 row 23, D7]. Other keys are free | yes |
| ids | strings only (F10), non-empty, no controls. `_:` is reserved for derived nodes | yes |
| `incidences[]` | `attrs.role` is required (rule 1). `attrs.position` is an integer ≥ 0. `attrs.evidence` is a list of evidence ids. In a `directed` file every record has `direction` [R03 D4] | yes |
| `nodes[]` | a `_:` node has exactly one of `attrs.literal`, `attrs.special`, `attrs.edge`. An entity node must not use those keys | yes |
| `edges[]` | `attrs.relation` and `attrs.status` are required; the other C1 fields are typed | yes |
| structure | Derived ids match their derivation (P010). No node or edge is declared twice (P011) [R03 D5]. Every incidence's edge has an edge record, and every derived node has a node record (P012). No two records share (edge, node, role, position) (P013) | Python |

The profile schema is `allOf: [{"$ref": <vendored HIF $id>}, <profile constraints>]`, so profile-valid
implies HIF-valid [R02 §11.2]. The `$ref` resolves offline through a registry that maps the HIF schema's
own `$id` to the vendored file (F2). fastjsonschema resolves it through a `handlers={"https": …}` hook.
Both validators agree on every artefact here (§0).

### 4.3 The contested choice: a node that plays two roles in one fact

| Option | Advocate | Can it hold tail and head for one node (c06)? | Per-binding `position` and `evidence`? | Round trip, measured | Upstream fit |
|---|---|---|---|---|---|
| **List-valued roles**: one incidence per (edge, node) carrying `roles: [...]` | R01 D-01, C1-R63 | **no**: `direction` is one value per record [R03 §8] | only as parallel lists | not measured for the gate | a new shape; the paper uses a string |
| **Role-keyed bindings** in C1, converted to a role list in HIF | R04 O2 | no (as above) | yes in C1, lost in HIF | — | as above |
| **One incidence per binding**; repeated (edge, node) pairs allowed | R02 §11.4, R03 D2 (its option a) | **yes** | yes: they are just that record's attrs | R03 sketch: 24/25 cases exact, including c05, c06 and c07. Here: the gate fixture 34/34 through XGI, HNX and the chain (§0) | the paper's own `{"role": "PI"}` string; upstream's compliant duplicate-pair fixture |

**Choice: one incidence per binding.** One more argument settles it. Under F1 the loaders never use the libraries' HIF readers,
so R01's library argument against repeated pairs (HNX drops duplicates, XGI edges are sets) no longer
applies. The sketch keeps extra records in a context table (XGI) or in a reserved cell key (HNX). C1
therefore uses a plain *list* of bindings (one binding, one incidence), not R04's role-keyed object. R04
chose that shape so that draft-07 `minItems`/`maxItems` could count a role's fillers. F5 moves
role-usage conformance into Python, so that benefit is gone, while the list maps one-to-one to
incidences, to SCH §6.2's instance layer and to R05's item shapes. R01's malformed candidate V10 ("two
records for one (edge, node) pair") is therefore *legal* here. What is malformed is an exact duplicate
(M46, P013).

### 4.4 Derived nodes: literals, special values, hyperedge references

An incidence must name a node [R02 §3], so every non-entity value becomes a *derived* node. Its id
starts with the reserved prefix `_:`, as blank-node labels do in N-Triples and Turtle, and its `attrs`
state what it is. Readers use the `attrs`; the id only has to be unique and deterministic.

| Value | Derived id | Node `attrs` | Shared? | Why |
|---|---|---|---|---|
| literal | `_:lit:` + the first 32 hex digits of SHA-256(JCS(literal)) | `{"literal": {...}}` | **shared by value** across edges | A value is the same value everywhere. Wikidata's RDF value nodes are content-hashed and shared the same way (Wikibase RDF dump format; not from R01–R05). Literals are not nodes in C1 or C2, so walkers over the store do not see hubs [R01 D-09] |
| `somevalue` / `novalue` / `unbound` | `_:some:`, `_:none:` or `_:unbound:<role>/<n>/<edge id>`, where n = 0, 1, … among that kind for that role in canonical order | `{"special": "somevalue"}` etc. | **per binding** | Two unknowns are not known to be the same thing (Wikidata RDF also mints a fresh node per `somevalue`: Wikibase RDF dump format, not from R01–R05). Role names contain no `/`, so the id parses from the left |
| hyperedge reference | `_:edge:<edge id>` | `{"edge": "<edge id>"}` | shared per referenced edge | An explicit reference plus a reserved prefix [R02 §11.7]; never inferred from id equality [R02 case 03] |

A goal with only unbound slots still has incidences, to its `_:unbound:` nodes. So there is no special
"edge with no incidences" rule, as R01 D-18 had proposed. Import checks every derived id against its
derivation (P010). For a special node the check is order-independent, because library round trips may
reorder incidences.

### 4.5 `network-type`, `direction`, `weight` and the metadata block

- **`network-type`** is `directed` if *every* binding in the document has a direction, and then every
  incidence carries one. Otherwise it is `undirected`, and bindings that have a direction still carry it
  on their incidence. The paper allows `direction` in any network type [R02 §3, p.8, case 24]. XGI's own
  reader would ignore it there [R03 row 7], but P2's loaders keep it in the context. The rule is
  deterministic, so a C1 document has exactly one HIF form.
- **`weight`** is never written by P2 producers and never invented, and it is never read back as
  confidence. A foreign weight travels verbatim through C1's `weight` fields so that a foreign file's
  round trip stays lossless [R03 D6; C1-R49, C1-R51].
- **Metadata declaration block**. These are the exact keys, flat and dash-case. The first three are
  written on export and dropped on import:

```json
"metadata": {
  "role-convention": "1.0.0",
  "hif-schema": "https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json",
  "hif-schema-sha256": "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196",
  "khg-profile": "1.0.0",
  "khg-schema": "gate-demo/1.0.0"
}
```

  The pin is the commit-pinned URL of blob `e2105bb`, byte-identical to the Zenodo v0.1.2 archive
  (DOI 10.5281/zenodo.17257719), which the paper calls "the stable schema" [R02 §2.2, §4.4]. It is
  **never** the moving `latest` URL, which the KB sample uses (malformed case M20) [R01 PF-01].

### 4.6 Importing a foreign HIF file that lacks the declaration

`from_hif(doc, mode="legacy", source=…)` returns `(c1_document, inferred_schema, report)`:

1. Strict JSON (J), then the vendored HIF schema (H).
2. Refused: `asc` (P006); a directed file with a missing direction (P005); duplicate declarations
   (P011); exact duplicate incidences (P013).
3. **Ids.** Integers become their decimal string, and `1` beside `"1"` in one namespace is refused
   (P003), because the collision would otherwise be silent [R02 cases 16–17]. Node ids and edge ids stay
   in separate namespaces, so a node id equal to an edge id is *not* read as nesting [R02 case 03].
4. **Roles.** `attrs.role` as a string is taken as the role. A list of strings becomes one binding each
   (reported). A missing role becomes the role `member` (reported). `--role-key` reads another key.
5. `edges[].attrs.relation` gives the relation, or `untyped` (reported). `nodes[].attrs.type` (a
   string) gives `types`, and `label` gives `label`. Other attrs are kept verbatim. Keys that collide
   with reserved C1 names are renamed `<key>@hif` (reported). `metadata.default_attrs` is renamed
   `default_attrs@hif`.
6. Every edge becomes `asserted` with the evidence `{"id": "import", "type": "imported", "source":
   <file>}`. That is the honest provenance, and it satisfies the evidence rule.
7. HIF edges with no incidences are reported and not imported: a C1 edge needs at least one binding (V27).
8. An inferred schema: the observed roles become `core` usages with the observed types (the catch-all
   `Thing` when fillers are untyped), the observed maximum (1 or `null`), and the observed direction when
   it is uniform.

**Measured** on the KB sample plus R03's 27 library cases (`legacy_proto.py`). 22 import with every
(edge, node, role, direction) record kept, and their profile exports validate. c13 is refused by the NFC
rule (S027), because it contains a decomposed `é` id on purpose. c04, c12, c14, c19 and c22 are refused
by design (rules above; c22 at layer J).

### 4.7 HIF → C1, exactly

`from_hif` in `strict` mode (the profile is declared) is the inverse of §2.1:

1. Drop the three HIF-only metadata keys.
2. For each non-`_:` node, lift `types` and `label` out of `attrs`.
3. For each edge, lift the reserved `attrs` keys to fields.
4. Group incidences by `edge`. Each becomes a binding: `role`, `position` and `evidence` come out of
   `attrs`; the value comes from the node (an entity id, or the derived node's `literal`, `special` or
   `edge`); `direction` and `weight` are kept.
5. Canonicalise.

Measured: `from_hif(to_hif(doc)) == canonical(doc)` for the gate fixture, and after each library round
trip.

### 4.8 The full HIF of the gate fixture

Validated against the vendored HIF schema (blob `e2105bb`) and against the KHG profile, under both
jsonschema 4.26.0 and fastjsonschema 2.22.2. It has 12 edges, 30 nodes (18 entities, 6 literals, 3
special, 3 edge references) and 34 incidences. The repeated pairs are `f3|ex:TP53` (regulator/tail and
target/head) and `f5|ex:YYZ` (stop at positions 0 and 2).

```json
{
 "network-type": "directed",
 "metadata": {"hif-schema": "https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json", "hif-schema-sha256": "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196", "khg-profile": "1.0.0", "khg-schema": "gate-demo/1.0.0", "role-convention": "1.0.0", "title": "P2 gate fixture (adversarial)"},
 "nodes": [
  {"node": "_:edge:f1", "attrs": {"edge": "f1"}},
  {"node": "_:edge:f10", "attrs": {"edge": "f10"}},
  {"node": "_:edge:f11", "attrs": {"edge": "f11"}},
  {"node": "_:lit:064d40a68985af1aade92e36a9983aa5", "attrs": {"literal": {"datatype": "quantity", "value": "500", "unit": "ex:milligram"}}},
  {"node": "_:lit:44d948adb36138175f25e1f86f5310c0", "attrs": {"literal": {"datatype": "string", "value": "correction"}}},
  {"node": "_:lit:468635dc115f6332da38dd85aa1075d5", "attrs": {"literal": {"datatype": "string", "value": "AC 123"}}},
  {"node": "_:lit:4ac80b8272bc499d3e23a18b9820cc6e", "attrs": {"literal": {"datatype": "quantity", "value": "421878", "unit": "1"}}},
  {"node": "_:lit:777c0802af8ec3d9440fcab5ec58e303", "attrs": {"literal": {"datatype": "text", "value": "Zürich", "lang": "de"}}},
  {"node": "_:lit:c108db3a9415c1d0819e264b9f92f6c8", "attrs": {"literal": {"datatype": "time", "value": "2019"}}},
  {"node": "_:none:catalyst/0/f8", "attrs": {"special": "novalue"}},
  {"node": "_:some:regulator/0/f4", "attrs": {"special": "somevalue"}},
  {"node": "_:unbound:catalyst/0/g1", "attrs": {"special": "unbound"}},
  {"node": "ex:ADA", "attrs": {"types": ["Organisation"], "label": "American Diabetes Association"}},
  {"node": "ex:HeLa", "attrs": {"types": ["CellLine"], "label": "HeLa"}},
  {"node": "ex:MYC", "attrs": {"types": ["Gene"], "label": "MYC"}},
  {"node": "ex:R1", "attrs": {"types": ["Reaction"], "label": "reaction R1"}},
  {"node": "ex:R2", "attrs": {"types": ["Reaction"], "label": "reaction R2"}},
  {"node": "ex:T2DM", "attrs": {"types": ["Disease"], "label": "type 2 diabetes mellitus"}},
  {"node": "ex:TP53", "attrs": {"types": ["Gene"], "label": "TP53"}},
  {"node": "ex:YYZ", "attrs": {"types": ["Airport"], "label": "Toronto Pearson"}},
  {"node": "ex:Zürich", "attrs": {"types": ["City"], "label": "Zürich"}},
  {"node": "ex:acme", "attrs": {"types": ["Organisation"], "label": "Acme"}},
  {"node": "ex:adults", "attrs": {"types": ["Population"], "label": "adults"}},
  {"node": "ex:air-canada", "attrs": {"types": ["Organisation"], "label": "Air Canada"}},
  {"node": "ex:ana", "attrs": {"types": ["Person"], "label": "Ana"}},
  {"node": "ex:anna", "attrs": {"types": ["Person"], "label": "Anna"}},
  {"node": "ex:hypoglycaemia", "attrs": {"types": ["AdverseEffect"], "label": "hypoglycaemia"}},
  {"node": "ex:insulin", "attrs": {"types": ["Drug"], "label": "insulin"}},
  {"node": "ex:metformin", "attrs": {"types": ["Drug"], "label": "metformin"}},
  {"node": "ex:羽田", "attrs": {"types": ["Airport"], "label": "東京国際空港 (羽田)"}}
 ],
 "edges": [
  {"edge": "f1", "attrs": {"relation": "treats", "status": "asserted", "valid": {"from": "2024-01-01"}, "evidence": [{"id": "e1", "type": "curated", "source": "doc:ada-standards-2024"}, {"id": "e2", "type": "extracted", "source": "doc:pmid-0000001", "digest": "sha256:7dac853671047fe09ef4dd22d52818dfd1a03a3a0b06ca2699b7068675e19a31", "exact": "500 mg metformin", "prefix": "start with ", "suffix": " twice daily", "start": 196, "end": 212, "agent": "extractor-x", "version": "0.3.1", "run": "p9-run-1", "model": "model-y-2026-06", "prompt": "skill:treats/v2", "params": {"temperature": 0.0, "seed": 13}, "confidence": {"value": 0.82, "scale": "probability"}}], "rank": "preferred"}},
  {"edge": "f10", "attrs": {"relation": "chief-executive", "status": "superseded", "valid": {"from": "2019-05"}, "evidence": [{"id": "e1", "type": "extracted", "source": "doc:news-1", "agent": "extractor-x", "version": "0.3.1", "run": "p9-run-1"}], "superseded-by": ["f11"]}},
  {"edge": "f11", "attrs": {"relation": "chief-executive", "status": "asserted", "valid": {"from": "2019-05"}, "evidence": [{"id": "e1", "type": "curated", "source": "doc:acme-annual-report-2019"}]}},
  {"edge": "f2", "attrs": {"relation": "co-administration-causes", "status": "asserted", "evidence": [{"id": "e1", "type": "curated", "source": "doc:ada-standards-2024"}]}},
  {"edge": "f3", "attrs": {"relation": "regulates", "status": "asserted", "evidence": [{"id": "e1", "type": "curated", "source": "doc:review-2021"}]}},
  {"edge": "f4", "attrs": {"relation": "regulates", "status": "asserted", "evidence": [{"id": "e1", "type": "curated", "source": "doc:review-2021"}]}},
  {"edge": "f5", "attrs": {"relation": "flight", "status": "asserted", "evidence": [{"id": "e1", "type": "imported", "source": "doc:timetable-2026"}]}},
  {"edge": "f6", "attrs": {"relation": "population", "status": "asserted", "evidence": [{"id": "e1", "type": "imported", "reference": [{"role": "retrieved", "literal": {"datatype": "time", "value": "2026-09-20"}}, {"role": "stated-in", "node": "ex:stat-zh-2020"}]}]}},
  {"edge": "f8", "attrs": {"relation": "catalysed-by", "status": "asserted", "evidence": [{"id": "e1", "type": "curated", "source": "doc:enzyme-db-2025"}]}},
  {"edge": "f9", "attrs": {"relation": "asserts", "status": "asserted", "evidence": [{"id": "e1", "type": "curated", "source": "doc:ada-standards-2024"}]}},
  {"edge": "g1", "attrs": {"relation": "catalysed-by", "status": "goal"}},
  {"edge": "s1", "attrs": {"relation": "khg:supersedes", "status": "asserted", "evidence": [{"id": "e1", "type": "curated", "source": "doc:acme-annual-report-2019"}]}}
 ],
 "incidences": [
  {"edge": "f1", "node": "ex:T2DM", "direction": "head", "attrs": {"role": "condition"}},
  {"edge": "f1", "node": "_:lit:064d40a68985af1aade92e36a9983aa5", "direction": "tail", "attrs": {"role": "dosage", "evidence": ["e2"]}},
  {"edge": "f1", "node": "ex:adults", "direction": "tail", "attrs": {"role": "population"}},
  {"edge": "f1", "node": "ex:metformin", "direction": "tail", "attrs": {"role": "treatment"}},
  {"edge": "f10", "node": "ex:acme", "direction": "tail", "attrs": {"role": "organisation"}},
  {"edge": "f10", "node": "ex:ana", "direction": "head", "attrs": {"role": "person"}},
  {"edge": "f11", "node": "ex:acme", "direction": "tail", "attrs": {"role": "organisation"}},
  {"edge": "f11", "node": "ex:anna", "direction": "head", "attrs": {"role": "person"}},
  {"edge": "f2", "node": "ex:insulin", "direction": "tail", "attrs": {"role": "agent"}},
  {"edge": "f2", "node": "ex:metformin", "direction": "tail", "attrs": {"role": "agent"}},
  {"edge": "f2", "node": "ex:hypoglycaemia", "direction": "head", "attrs": {"role": "effect"}},
  {"edge": "f3", "node": "ex:HeLa", "direction": "tail", "attrs": {"role": "context"}},
  {"edge": "f3", "node": "ex:TP53", "direction": "tail", "attrs": {"role": "regulator"}},
  {"edge": "f3", "node": "ex:TP53", "direction": "head", "attrs": {"role": "target"}},
  {"edge": "f4", "node": "_:some:regulator/0/f4", "direction": "tail", "attrs": {"role": "regulator"}},
  {"edge": "f4", "node": "ex:MYC", "direction": "head", "attrs": {"role": "target"}},
  {"edge": "f5", "node": "ex:air-canada", "direction": "tail", "attrs": {"role": "carrier"}},
  {"edge": "f5", "node": "_:lit:468635dc115f6332da38dd85aa1075d5", "direction": "tail", "attrs": {"role": "flight-number"}},
  {"edge": "f5", "node": "ex:YYZ", "direction": "head", "attrs": {"role": "stop", "position": 0}},
  {"edge": "f5", "node": "ex:羽田", "direction": "head", "attrs": {"role": "stop", "position": 1}},
  {"edge": "f5", "node": "ex:YYZ", "direction": "head", "attrs": {"role": "stop", "position": 2}},
  {"edge": "f6", "node": "_:lit:4ac80b8272bc499d3e23a18b9820cc6e", "direction": "head", "attrs": {"role": "count"}},
  {"edge": "f6", "node": "_:lit:777c0802af8ec3d9440fcab5ec58e303", "direction": "tail", "attrs": {"role": "named-as"}},
  {"edge": "f6", "node": "ex:Zürich", "direction": "tail", "attrs": {"role": "place"}},
  {"edge": "f6", "node": "_:lit:c108db3a9415c1d0819e264b9f92f6c8", "direction": "tail", "attrs": {"role": "point-in-time"}},
  {"edge": "f8", "node": "_:none:catalyst/0/f8", "direction": "head", "attrs": {"role": "catalyst"}},
  {"edge": "f8", "node": "ex:R1", "direction": "tail", "attrs": {"role": "reaction"}},
  {"edge": "f9", "node": "ex:ADA", "direction": "tail", "attrs": {"role": "asserter"}},
  {"edge": "f9", "node": "_:edge:f1", "direction": "head", "attrs": {"role": "statement"}},
  {"edge": "g1", "node": "_:unbound:catalyst/0/g1", "direction": "head", "attrs": {"role": "catalyst"}},
  {"edge": "g1", "node": "ex:R2", "direction": "tail", "attrs": {"role": "reaction"}},
  {"edge": "s1", "node": "_:lit:44d948adb36138175f25e1f86f5310c0", "direction": "tail", "attrs": {"role": "khg:reason"}},
  {"edge": "s1", "node": "_:edge:f10", "direction": "head", "attrs": {"role": "khg:superseded"}},
  {"edge": "s1", "node": "_:edge:f11", "direction": "tail", "attrs": {"role": "khg:superseding"}}
 ]
}
```

---

## 5. Library loaders (XGI and HyperNetX)

The loaders take and return **HIF that follows the role convention** (§4.1). They do not need the KHG
profile, so they are usable, and proposable upstream, for any role-labelled HIF. KHG users call the thin
wrappers `khg_to_xgi(doc, schema)` / `xgi_to_khg(bundle, schema)`, which compose them with
`to_hif`/`from_hif`. The design is the one R03 §7.4 tested and this design re-ran on the gate fixture.
Library objects are built only through public constructors, what the library cannot hold is kept in a
context, and export reconciles the two (F1).

### 5.1 API

```python
# khg_contracts.loaders.xgi   (extra: khg-contracts[xgi], xgi==0.10.2)
# khg_contracts.loaders.hnx   (extra: khg-contracts[hypernetx], hypernetx==2.4.3, pandas<3)
@dataclass
class Context:                          # what the library object cannot hold
    network_type: str                   # "directed" | "undirected"
    metadata: dict                      # the whole block (HNX keeps only `name`; XGI keeps it but loses it on asc)
    incidences: list[dict]              # XGI: every source record, in source order (XGI stores none)
    node_order: list[str]               # declaration order, for deterministic export
    edge_order: list[str]
    weights: dict[tuple[str, str], float]   # ("node" | "edge", id) -> weight, only where the source had one

@dataclass
class ReconcileReport:
    stale: list[dict]                   # records whose membership no longer exists: reported, never re-attached
    unlabelled: list[dict]              # memberships with no record: exported bare, reported

class ReconcileError(ValueError): ...  # raised by strict export when stale or unlabelled is non-empty

@dataclass
class XGIBundle:
    H: "xgi.Hypergraph | xgi.DiHypergraph"
    ctx: Context

    def roles(self, edge: str) -> list[tuple[str, str, str | None]]: ...   # (node, role, direction), for P5's drawings

def to_xgi(hif: dict, *, validate: bool = True) -> XGIBundle
def from_xgi(bundle: XGIBundle, *, strict: bool = True) -> tuple[dict, ReconcileReport]

@dataclass
class HNXBundle:
    H: "hnx.Hypergraph"
    ctx: Context                        # incidences live in the cells; ctx.incidences records weight presence only

def to_hnx(hif: dict, *, validate: bool = True) -> HNXBundle
def from_hnx(bundle: HNXBundle, *, strict: bool = True) -> tuple[dict, ReconcileReport]

# C1-level conveniences
def khg_to_xgi(doc: dict, schema: RelationSchema) -> XGIBundle        # to_xgi(to_hif(doc, schema))
def xgi_to_khg(bundle: XGIBundle, schema: RelationSchema) -> dict     # from_hif(from_xgi(bundle)[0], schema)
def khg_to_hnx(doc: dict, schema: RelationSchema) -> HNXBundle
def hnx_to_khg(bundle: HNXBundle, schema: RelationSchema) -> dict
```

`H` and `ctx` travel together in one bundle, so the two cannot drift apart [R03 D1]. `validate=True`
runs layers J, H and P (profile rules 1–3 of §4.1) before any library call. That refuses `asc` [R03 D8],
a missing or invalid `direction` in a directed file [R03 D4, X4], and duplicate declarations [R03 D5].

### 5.2 What each loader does

**XGI** [R03 §7.1]:

1. Build a `DiHypergraph` if the file is directed, else a `Hypergraph`.
2. Add memberships with `add_node_to_edge(e, n, "in" | "out")`. XGI's `in` is the tail and `out` the
   head.
3. Create nodes and edges with `add_node(i)` and `add_edge(set(), idx=i)`, **never** with `**attrs`. An
   attrs key named `node` or `members` would crash (X5, c21/c26).
4. Set attributes with `set_node_attributes` and `set_edge_attributes`; set metadata as network
   attributes.
5. Keep every incidence record in `ctx.incidences`. This is the source of truth: XGI has no (edge, node)
   slot (X1).

On export, the current memberships are read from `H`. Every context record whose (edge, node, direction)
membership still exists is emitted, *including second and further roles*. Records whose membership is
gone are `stale`, and memberships without a record are `unlabelled`. Nodes and edges are read from `H`'s
attributes, plus the weights and declaration order in `ctx`. `xgi.write_hif` is never called (X3, X8).

**HyperNetX** [R03 §7.2]:

1. Build with the public constructor, `hnx.Hypergraph(DataFrame, edge_col="edge", node_col="node",
   cell_weight_col="weight", misc_cell_properties_col="attrs", node_properties=…, edge_properties=…,
   misc_properties_col="attrs")`. It works offline.
2. The first record of an (edge, node) pair lives natively in the cell, so
   `H.get_cell_properties(e, n, "role")` works for HNX users. Records 2..k ride in the reserved cell
   attribute `khg:extra-incidences`. That key exists only inside the in-memory object and is expanded on
   export, so the extra records follow the cell through `rename`, `dual` and `restrict_*` (N3).

On export, cells come from `H.incidences.to_dataframe`. Nodes and edges come from the property *stores*,
which keep the isolated nodes and empty edges that the views hide (N8). Metadata, `network-type` and
weight presence come from `ctx`. The exporter never writes `"nil"` (N6), never invents `weight: 1` (row
9), and never exports through `get_cell_properties`, which flattens nested attrs (§2.2). `hnx.from_hif`
and `hnx.to_hif` are never called (N1, N2, N4–N9, N11).

### 5.3 Native operations between load and export (documented list, R03 D9)

| | Safe: roles kept, 0 wrong | Reported: records become `stale` | Unsafe: roles move or vanish; strict export raises |
|---|---|---|---|
| **XGI** | `copy()`, weak `remove_node`, `add_edge`, `add_node_to_edge`, `merge_duplicate_edges()`, `set_*_attributes` | strong `remove_node`, `subhypergraph` (undirected; on `DiHypergraph` it raises `XGIError`) | `H << H2` (edge ids renumbered), `convert_labels_to_integers()`, `cleanup()`, `dual()`, conversion to `SimplicialComplex`, `xgi.Hypergraph(DH)` (drops direction) |
| **HNX** | `clone()`, `restrict_to_edges`, `remove_edges`, `remove_nodes`, `remove_incidences`, `rename`, `dual`, `add_incidence` (with `direction` in a directed file), setting cell properties | `restrict_to_nodes` keeps roles but leaves *partial* n-ary facts. Importing back into C1 then reports S003 for missing required roles | `collapse_nodes`, `collapse_nodes_and_edges` (roles moved to the wrong participant [R03 §5.2]), `collapse_edges` (weights summed), `sum` over overlapping pairs (the second role is dropped), `add_edge`/`add_node` without incidences (invisible, dropped) |

Evidence: R03 §5 and the tables of §7.4. Strict mode is the default for the C1-level wrappers.
Non-strict export returns the HIF plus the report, for exploratory use.

### 5.4 Determinism

Both exporters write records in a canonical order: declaration order from `ctx`, then new ids sorted by
typed id. They never rely on set iteration. XGI's own writer changes order with the hash seed, giving
four different outputs for four seeds (X8) [R03 §4.1]. The gate chain gave **one** byte-identical output
across `PYTHONHASHSEED` 0–3 (§0). Tests compare structure, not bytes, anyway (F10) [R03 D11].

### 5.5 The separate library-evidence test

`tests/evidence/test_library_hif_functions.py` has the pytest marker `evidence` and is *not* a gate test
(F1). It runs `xgi.read_hif`/`xgi.write_hif` and `hnx.from_hif`/`hnx.to_hif` on the gate HIF and on R03's
c05 and c06. HyperNetX's schema fetch is monkeypatched to serve the vendored bytes, so the test runs
offline. It writes `evidence/library-hif-report.json` with, per library, roles kept, records in and out,
directions kept, metadata keys lost and weights added. It asserts the *currently known* losses:

- XGI 0.10.2: roles 0/34, records 34 → 33, directions 33/34.
- HNX 2.4.3: roles 32/34, records 34 → 32, 6 metadata keys lost, `weight` added on 32 incidences.

If a library release fixes something, the test fails and the upstream proposal (§12) is updated. The
report file is the evidence table attached to the HIF, XGI and HNX issues.

---

## 6. C2 store interface

### 6.1 Protocol

```python
# khg_contracts.store  (C2 interface version 1.0.0)
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Protocol, Sequence, runtime_checkable

Record = dict[str, Any]                  # canonical C1 node or edge record
Binding = Mapping[str, Any]              # {"role", one of node|literal|edge|special, ["position"]}
Status = Literal["asserted", "superseded", "retracted", "goal"]
CAPABILITIES = frozenset({"as_at", "as_of", "nesting", "literals", "ordered", "special_values", "atomic_batch"})

@dataclass(frozen=True)
class KeyConflict:
    relation: str
    key: str                              # key digest, "sha256:..."
    edges: tuple[str, ...]                # colliding edge ids, sorted
    policy: Literal["flag", "end-older", "supersede-older"]   # "reject" raises instead

@dataclass(frozen=True)
class PutResult:
    recorded: str                         # transaction time of the batch, UTC
    written: tuple[str, ...]              # edge ids that received a new version, sorted
    unchanged: tuple[str, ...]            # edge ids whose content equalled the current version (no-op)
    nodes: tuple[str, ...]                # node ids upserted
    conflicts: tuple[KeyConflict, ...]

@dataclass(frozen=True)
class WalkStep:
    edge: str                             # the fact reached
    via: str                              # the khg:supersedes edge that links it
    reason: Literal["correction", "refinement", "duplicate"]
    depth: int                            # 1 = direct successor (forward) or predecessor (backward)

class StoreError(Exception):
    code: str                             # "KHG-Snnn" (§8.2)

@runtime_checkable
class Store(Protocol):
    interface_version: str                # "1.0.0"
    format_version: str                   # C1 version implemented, "1.0.0"
    capabilities: frozenset[str]          # subset of CAPABILITIES

    def put(self, records: Record | Iterable[Record], *, at: str | None = None) -> PutResult: ...
    def get(self, id: str, *, kind: Literal["edge", "node"] = "edge",
            as_at: str | None = None) -> Record | None: ...
    def incident(self, node: str | None = None, *, edge: str | None = None, role: str | None = None,
                 relation: str | None = None, status: Iterable[Status] = ("asserted",),
                 as_of: str | None = None, as_at: str | None = None,
                 limit: int | None = None, after: str | None = None) -> list[Record]: ...
    def find(self, relation: str, bindings: Sequence[Binding], *,
             match: Literal["at_least", "exact"] = "at_least",
             status: Iterable[Status] = ("asserted",), as_of: str | None = None, as_at: str | None = None,
             limit: int | None = None, after: str | None = None) -> list[Record]: ...
    def supersession_walk(self, id: str, *, direction: Literal["forward", "backward"] = "forward",
                          as_at: str | None = None) -> list[WalkStep]: ...
    def export(self, format: Literal["khg", "hif"] = "khg", *, as_at: str | None = None,
               history: bool = False) -> dict: ...
```

That is six methods, the six operations PLAN §7 names. There are no special lifecycle methods:
supersession, retraction, the end of validity, rank and visibility changes and goal binding are all
ordinary versions and meta-records written by `put` (§2.14). Implementers therefore write a single write
path.

### 6.2 Semantics

**`put(records, at=None)`.** One batch, validated as a whole before anything is written ("validate all,
then write"). With the `atomic_batch` capability, a crash cannot leave half a batch either
[C2-R19]. The steps:

1. Layers P and S run on every record, in the scope of store ∪ batch: references, lifecycle consistency,
   evidence, types (§8).
2. A `candidate` is refused (S028).
3. For an existing edge id, a record whose content (all fields except `recorded`) equals the current
   version is `unchanged`, making `put` idempotent [C2-R01]. Otherwise the transition table (S030) and
   the immutability of `relation` and `bindings` (S031) apply.
4. Key checks run among *current asserted* versions after the batch, using the key digest and, for
   temporal keys, overlapping `valid`. Under `reject` the batch fails with S029. Otherwise it is written
   and the conflicts are returned [C2-R18].
5. Every written version gets `recorded = at` or the store clock. `at` must be later than every
   `recorded` in the store (S032).
6. Node records are upserted without versions in v1. They are descriptions, not facts.

Nothing else changes. `put` never edits a record other than the ones it was given (§3.2), and nothing is
ever deleted physically [C2-R08].

**`get(id, kind="edge", as_at=None)`.** For an edge, the version with the greatest `recorded ≤ as_at`;
`as_at=None` means the latest. For a node, the current node record. `None` if the record is unknown
[C2-R02].

**`incident(node=… | edge=…, role, relation, status, as_of, as_at, limit, after)`.** Exactly one of
`node` or `edge` is given, because node ids and edge ids are separate namespaces. The result is every
edge, current as-at `as_at`, with a binding whose value is that node or edge (and whose role is `role`, if
given), filtered by relation, by status and by valid time. It is **complete** [C2-R03]. Literals are not
nodes, so they never make hubs in `incident`.

**`find(relation, bindings, match)`.** Edges of `relation` whose bindings contain the given bindings as a
multiset. A binding is compared on role, value and position, ignoring direction. With
`match="exact"`, the multisets must be equal. Key lookup is `find` with the key-role bindings [C2-R04].
Same filters.

**Defaults and filters.**

- `as_at=None` means now (the latest belief).
- `as_of=None` means **no valid-time filter**. This is how SQL:2011 behaves: an application-time table
  has no implicit valid-time filter, while a system-versioned table defaults to current rows. R04 M4
  describes both period kinds; the default behaviour is stated from general knowledge of the standard.
  It is a deliberate departure from R01 D-16's "as-of now". A historical KB (Louis XIV's reign) would otherwise vanish from the default
  view, and P7's memory questions pass `as_of` explicitly anyway.
- The status filter defaults to `("asserted",)`, so goals appear only when asked for [C2-R13].
- `rank` and `visibility` are not filtered by default. `suppressed` is filtered only by a governance
  wrapper, deferred.

**Order and pagination.** Results are sorted by edge id in code-point order, which is total and
deterministic. Pagination is by key: `after` is the last id of the previous page, and `limit` is the page
size [C2-R16].

### 6.3 Supersession walk

Breadth-first over the current (as-at) `khg:supersedes` records whose status is `asserted`. `forward`
goes from superseded to superseding (newer), `backward` the other way. Each step is `(edge, via,
reason, depth)`. The order is by depth, then by edge id. A visited set guarantees termination even on
invalid data, although cycles are refused on write (S014, S022) [C2-R05]. Forks, where one fact is
superseded by two, appear as two steps at the same depth. The walk needs no `superseded-by` index: it
reads the records, which is part of why the index is objected to (§2.14).

### 6.4 Export

`export("khg", as_at, history=False)` returns the canonical C1 document of the current versions as-at
`as_at`. With `history=True` it returns every version, each with its `recorded`. `export("hif")` is
`to_hif(export("khg"))` under the profile [C2-R06]. Other projections are library functions over the
export (§2.19), not store methods, which keeps C2 minimal. The pairwise projection and the RDF,
incidence-table and property-graph codecs follow the ownership split of §2.19.

### 6.5 Capability flags

| Flag | A store that lacks it… |
|---|---|
| `as_at` | cannot answer `get` or queries with `as_at` (an in-place store, Graphiti-style [R04 M4]) |
| `as_of` | cannot filter by valid time |
| `nesting` | cannot hold `edge`-valued bindings, so it cannot hold supersession records either |
| `literals` | cannot hold literal bindings |
| `ordered` | cannot keep positions |
| `special_values` | cannot hold `somevalue`, `novalue` or `unbound` |
| `atomic_batch` | cannot guarantee batch atomicity across failures |

A scenario that `requires` a missing flag is reported `inapplicable`, never `passed` [R04 O13; EARL].

### 6.6 Reference implementation

`khg_contracts.store.MemoryStore(schema)` has every capability. It keeps a dict from edge id to its list
of versions sorted by `recorded`, a dict of node records, and two indexes maintained on write: (value
kind, value) → edge ids, and relation → edge ids. `find` is an indexed scan. The simpler prototype in
`store_proto.py` (242 lines, linear scans) passes all 22 scenarios. `khg_contracts.store.HIFStore(path)`
is the same class loaded from a C1 history export or a profile HIF file, which is P1's fifth backend.

### 6.7 Conformance suite

Declarative scenario files in JSON [R04 O13, the openCypher TCK style], shipped as package data under
`khg_contracts/conformance/scenarios/` so that P1 can run them unchanged against five backends. Format:

```json
{"id": "C2-13", "title": "supersession is one batch; the walk follows it forward",
 "requires": ["atomic_batch", "nesting"], "schema": "gate-demo/1.0.0",
 "given": [{"put": ["<18 node records>", "<f10 as asserted>"], "at": "2026-01-01T00:00:00Z"},
           {"put": ["<f11>", "<f10 as superseded, superseded-by [f11]>", "<s1>"], "at": "2026-02-01T00:00:00Z"}],
 "when": {"op": "supersession_walk", "args": {"id": "f10"}},
 "then": {"steps": [{"edge": "f11", "via": "s1", "reason": "correction", "depth": 1}]}}
```

- `then` is one of `ids` (for `incident`/`find`), `record` (for `get`, compared canonically without
  `recorded`), `steps`, `put` (a `PutResult`) or `error` (a KHG code).
- Records are written inline in the real files. The `<…>` placeholders above abbreviate the fixture
  records of §2.18.
- The runner `khg-conformance --store pkg.module:factory` builds a store per scenario by calling
  `factory(schema: RelationSchema) -> Store` with the scenario's schema. `MemoryStore` itself is such a
  factory. It checks `requires` against `capabilities`, and writes an EARL-shaped JSON report: `[{"test",
  "outcome": "passed" | "failed" | "inapplicable", "info", "seconds"}]`.
- The per-operation wall time is the timing hook P1 needs [C2-R15].

**v1 scenarios**. C2-01 to C2-22 were run and passed on the prototype (§0).

| Id | Asserts |
|---|---|
| C2-01 | put then get returns the canonical record |
| C2-02 | identical re-put is a no-op (`unchanged`) |
| C2-03 | a closed valid interval is a new version; `get(as_at=T1)` returns the old one (`as_at`) |
| C2-04 | `incident` is complete and ordered by edge id |
| C2-05 | `incident` role filter |
| C2-06 | the default status filter excludes superseded versions |
| C2-07 | the status filter can include superseded |
| C2-08 | `as_of` filters by valid time; an ended fact stays asserted (F7) |
| C2-09 | `find` at least |
| C2-10 | `find` exact |
| C2-11 | temporal key under `end-older`: conflict reported, nothing rewritten |
| C2-12 | `reject` policy → S029 |
| C2-13 | supersession batch; forward walk |
| C2-14 | backward walk |
| C2-15 | superseded without a record → S022 |
| C2-16 | retracted is terminal → S030 |
| C2-17 | candidate refused → S028 |
| C2-18 | bindings immutable → S031 |
| C2-19 | a goal's unbound slot bound by a new version (`special_values`) |
| C2-20 | pagination by key |
| C2-21 | goals visible only when asked for |
| C2-22 | nesting: `incident(edge="f1")` returns the facts about `f1` |

The implementation adds five before release:

| Id | Asserts |
|---|---|
| C2-23 | `export("hif")` is profile-valid and folds back to `export("khg")` (the smoke test's check) |
| C2-24 | `export(history=True)` holds every version with its `recorded` |
| C2-25 | a non-monotonic `at` → S032 |
| C2-26 | `find` on a temporal key with `as_of` returns the holder at that time |
| C2-27 | retraction without a `khg:retracts` record → S022 |

### 6.8 How the five P1 backends implement C2

| Backend | Layout | `incident` / `find` | Capabilities it lacks natively |
|---|---|---|---|
| **Incidence table** (PostgreSQL 18) | `fact_version(edge, recorded, relation, status, valid tstzrange, rank, visibility, key_digest, content_key, doc jsonb)` plus `binding(edge, recorded, role, kind, node, edge_ref, literal jsonb, position, direction)` [R01 §3; REL §1b] | index on `(kind, node)` and `(kind, edge_ref)`; `find` by `GROUP BY … HAVING` counts. A `reject` temporal key can use `UNIQUE (relation, key_digest, valid WITHOUT OVERLAPS)`, the digest column R04 §3.3 calls for | none |
| **Reified RDF 1.2**, relation-instance pattern (pyoxigraph, since rdflib 7.6.0 has no RDF 1.2 [R01 §3]) | one IRI per edge version, typed by its relation. Role properties are sub-properties of `khg:role`, so `incident` can tell roles from metadata. A binding with a position, a direction or evidence uses a qualified binding node. Quantity and time use value nodes (the Wikidata RDF style). Versions are separate instance IRIs with `recorded` | a SPARQL pattern over role properties | none essential. The annotation (triple-term) form is a lossy export; it uses the direction-derived primary pair of §2.19 [C1-R57] |
| **Bipartite property graph** (Neo4j, or Kùzu 0.11.3, which is archived [R04 M9]) | `(:Fact {edge, recorded, relation, status, …})-[:ROLE {role, position, direction, evidence}]->(:Entity \| :Literal \| :Fact)`. Roles are a property, because the vocabulary is open [R01 §3; PGE §4 r2] | `MATCH (n {id:$x})<-[:ROLE]-(f:Fact)`; a k-hop fact query is 2k graph hops [R01 §3] | none. Literals may be value-shared nodes, as in HIF |
| **TypeDB 3.x** | one relation type per C1 relation. `relates <role>`: role types are relation-scoped, so each is named after its global role id and P6 reads the C1 schema, not TypeQL. Entities play roles; edges play roles (nesting); literals are `owns` attributes, since attributes cannot play roles [R04 M2] | TypeQL `match` over role players and owned attributes | **`ordered`**: ordered role lists are "not yet available" [R04 M1]; emulate with a binding relation carrying a position. **`special_values`**: a relation whose players are all unbound is deleted as dangling [R04 risk 5]; emulate with per-binding sentinel entities. Transaction time needs version entities, since there is none native. Literal fidelity must be checked, because `@unique` refuses `double` |
| **HIF** (`HIFStore`) | a profile HIF, or a C1 history export, indexed in memory | as `MemoryStore` | `as_at` only when loaded from a history export. There is no streaming [R01 PF-28], so use the JSONL C1 form for large data |

---

## 7. C3: candidate queue and action log

### 7.1 One append-only stream

A queue is one JSONL stream (F9) [R01 D-18]. Line 1 is a header `{"metadata": {"khg-profile",
"khg-schema", "queue"}}`. Every later line is either a **queue item** (it has `item` and `payload`) or an
**action-log entry** (it has `log`). Nothing is ever rewritten. The state of an item is a fold over its log
entries, and replaying the stream over the same inputs reproduces the same store state, so order effects
can be measured [C3-R11]. A single stream gives a total order across enqueues and decisions, which two
separate files would not.

### 7.2 Queue item: one kind

| Field | Req. | Meaning |
|---|---|---|
| `item` | yes | Queue item id |
| `at` | yes | Enqueue time, UTC |
| `payload` | yes | **A C1 edge record with `status: "candidate"`** (F9) [C3-R01] |
| `nodes` | no | Node records the payload introduces, such as new entities minted by an extractor |
| `schema` | no | Overrides the header's schema id [C3-R12] |
| `keys` | yes | `{"content", "core", "events": [...]}`: the computed identifiers of §2.16. P9 compares runs by them [C3-R04]; validators recompute them (Q003) |
| `order` | no | `{"permutation", "position"}`: the insertion-order design of P9 [C3-R02] |

There is **one item kind**. A candidate may be a new fact, a new version of a stored edge (for example a
goal with a slot bound), or a meta-fact: a `khg:supersedes` candidate *is* a supersession proposal, and
one with reason `duplicate` *is* a merge proposal [C3-R14]. R01 D-18's four kinds therefore reduce to one.
The extraction metadata of C3-R02 lives where it belongs, in the payload's evidence: `agent`, `version`,
`model`, `prompt`, `params` (temperature and seed), `run`, `source`, `digest` (the document version
hash), plus `order` and `at` on the item.

### 7.3 Decisions and item states

| Action (log) | Effect | Resulting state |
|---|---|---|
| `flag` | a lint finding; no state change | — |
| `fix` | automatic fix: `before`/`after` payloads; later lint runs on `after` | — |
| `verdict` | a review judgement (§7.4); no state change | — |
| `review` | sent to people | `needs-review` |
| `accept` | the store `put`s the payload as `asserted` (or `goal`); `after = {edge, recorded}` | `accepted` (terminal) |
| `merge` | the target edge gets a new version with the payload's evidence appended, deduplicated by event key. Allowed only when the content keys are equal. A refinement (same core, more qualifiers) is *not* a merge: it is accepted and linked by `khg:supersedes` with reason `refinement` | `merged` (terminal) |
| `reject` | none | `rejected` (terminal) |

Two rules: at most one terminal decision per item (Q005), and no `accept` or `merge` while a
`violation` finding is open, that is, not cleared by a later `fix` (Q006) [C3-R05].

### 7.4 Verdict unit

A verdict attaches to a **(candidate, evidence) pair** [R04 O9, INDRA]. The `evidence` field names the
evidence id; if it is absent, the verdict covers the candidate as a whole. A verdict is looked up by the
item's `keys.content` and the event key of that evidence, so it carries over to re-extractions of the
same span [R04 M7]. The vocabulary is INDRA's tags generalised to roles and cut to what C3-R06 and P9 need:

- `correct`
- `no-support` (the span does not support the fact)
- `wrong-relation` (the triplet is wrong)
- `wrong-role` (right value, wrong role)
- `wrong-filler` (grounding)
- `missing-participant` (incomplete)
- `other` (requires `reason`)

`bindings` lists the canonical indexes of the bindings judged wrong. Aggregation to the candidate: it is
`correct` if any evidence verdict is `correct`, and otherwise the multiset of its error verdicts.
`negated`, `hypothesis` and `span-boundary` are deferred with epistemics (§12).

### 7.5 Structural linter

**Structural lint is the validator.** It runs layers J, P and S on the payload *as if its status were
the target status* (`asserted`), with the same codes and severity `violation`. So a candidate missing a
required role cannot be accepted, and one rule set serves `put`, the queue and files [C3-R08]. Five queue
rules are added:

| Rule | Severity | Fires when | Proposal |
|---|---|---|---|
| KHG-L001 duplicate | warning | the content key equals that of a current asserted store edge | `merge` into it |
| KHG-L002 key collision | by policy: `reject` → violation, `flag` → warning, `end-older` / `supersede-older` → info | the key digest collides with a current asserted edge (overlapping `valid` if the key is temporal) | the linter enqueues the proposed candidate: a new version with `valid.until`, or a `khg:supersedes` record |
| KHG-L003 node in several roles | info | one node fills two or more roles in one edge (I9) | — |
| KHG-L004 span missing | warning | `extracted` evidence without `start`/`end`; C5's strict span matching needs them [C1-R39] | — |
| KHG-L005 refinement | info | the core key equals that of an asserted edge but the content key differs (case 1 [R01 §6.1]) | a `khg:supersedes` candidate with reason `refinement`, for review, never applied automatically [C3-R09] |

A rule's version is the linter's version (`actor.version`). The quality rates of C3-R09 are deferred.

### 7.6 Action-log entry

| Field | Req. | Meaning (who / what / when / why / before / after) |
|---|---|---|
| `log` | yes | entry id |
| `at` | yes | **when** |
| `item` | yes | the queue item |
| `actor` | yes | **who**: `{agent, version?}` (`khg-lint` 1.0.0, `person:reviewer-1`, …) |
| `action` | yes | **what**: `flag` \| `fix` \| `verdict` \| `accept` \| `merge` \| `reject` \| `review` |
| `rule`, `severity`, `path`, `message` | flag (`rule` also for fix) | the finding: code, SHACL severity name (`violation`, `warning`, `info`), JSON Pointer into the payload, message [R04 M7] |
| `reason` | reject, review, and verdict `other` | **why** |
| `verdict`, `evidence`, `bindings` | verdict | §7.4 |
| `target` | merge | the store edge merged into |
| `before`, `after` | fix (both); accept and merge (`after`) | snapshots, or `{edge, recorded}` store references |

### 7.7 Example stream (validated against `khg-queue-1.0.0.json` and the Q checks)

The first candidate is accepted. The same fact extracted from a second document has an equal content key
but a new event key, so the linter flags a duplicate and the reviewer merges it as more evidence. That is
"two sources of one fact make one fact with two evidence records" [C1-R35].

```json
{"metadata": {"khg-profile": "1.0.0", "khg-schema": "gate-demo/1.0.0", "queue": "p9-run-1+2"}}
{"item": "q1", "at": "2026-09-23T10:00:00Z", "payload": {"edge": "f1", "relation": "treats", "status": "candidate", "rank": "preferred", "bindings": [{"role": "condition", "node": "ex:T2DM", "direction": "head"}, {"role": "dosage", "literal": {"datatype": "quantity", "value": "500", "unit": "ex:milligram"}, "direction": "tail", "evidence": ["e2"]}, {"role": "population", "node": "ex:adults", "direction": "tail"}, {"role": "treatment", "node": "ex:metformin", "direction": "tail"}], "valid": {"from": "2024-01-01"}, "evidence": [{"id": "e1", "type": "curated", "source": "doc:ada-standards-2024"}, {"id": "e2", "type": "extracted", "source": "doc:pmid-0000001", "digest": "sha256:7dac853671047fe09ef4dd22d52818dfd1a03a3a0b06ca2699b7068675e19a31", "exact": "500 mg metformin", "prefix": "start with ", "suffix": " twice daily", "start": 196, "end": 212, "agent": "extractor-x", "version": "0.3.1", "run": "p9-run-1", "model": "model-y-2026-06", "prompt": "skill:treats/v2", "params": {"temperature": 0.0, "seed": 13}, "confidence": {"value": 0.82, "scale": "probability"}}]}, "keys": {"content": "sha256:65f4cbe8673596a3a1e787cfa01d5f433a71c3eca419aa4072bd769eebd821cd", "core": "sha256:a8603e53b358934dd735bca5060ebf74eb8788869ddd4aee8ce6f4078240f16a", "events": ["sha256:b19a09026fc005bcfbe9e2576d811b8716e38e9d4afc814ecdfdd8ff464bdc04"]}, "order": {"permutation": "order-A", "position": 0}}
{"log": "l1", "at": "2026-09-23T10:05:00Z", "item": "q1", "actor": {"agent": "person:reviewer-1"}, "action": "verdict", "verdict": "correct", "evidence": "e2"}
{"log": "l2", "at": "2026-09-23T10:05:01Z", "item": "q1", "actor": {"agent": "person:reviewer-1"}, "action": "accept", "reason": "span supports every binding", "after": {"edge": "f1", "recorded": "2026-09-23T10:05:01Z"}}
{"item": "q2", "at": "2026-09-23T11:00:00Z", "payload": {"edge": "cand-7", "relation": "treats", "status": "candidate", "bindings": [{"role": "condition", "node": "ex:T2DM", "direction": "head"}, {"role": "dosage", "literal": {"datatype": "quantity", "value": "500", "unit": "ex:milligram"}, "direction": "tail"}, {"role": "population", "node": "ex:adults", "direction": "tail"}, {"role": "treatment", "node": "ex:metformin", "direction": "tail"}], "evidence": [{"id": "e1", "type": "extracted", "source": "doc:pmid-0000002", "digest": "sha256:3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b", "exact": "metformin 500 mg", "start": 88, "end": 104, "agent": "extractor-x", "version": "0.3.1", "run": "p9-run-2", "prompt": "skill:treats/v2", "confidence": {"value": 0.74, "scale": "probability"}}]}, "keys": {"content": "sha256:65f4cbe8673596a3a1e787cfa01d5f433a71c3eca419aa4072bd769eebd821cd", "core": "sha256:a8603e53b358934dd735bca5060ebf74eb8788869ddd4aee8ce6f4078240f16a", "events": ["sha256:6221baab77d3f13d90d3478f93b6459324a3dc9dca750b0b54daeaf28f3ffaf4"]}, "order": {"permutation": "order-B", "position": 3}}
{"log": "l3", "at": "2026-09-23T11:00:01Z", "item": "q2", "actor": {"agent": "khg-lint", "version": "1.0.0"}, "action": "flag", "rule": "KHG-L001", "severity": "warning", "path": "", "message": "content key equals asserted edge f1"}
{"log": "l4", "at": "2026-09-23T11:02:00Z", "item": "q2", "actor": {"agent": "person:reviewer-1"}, "action": "merge", "target": "f1", "reason": "same fact, second source", "after": {"edge": "f1", "recorded": "2026-09-23T11:02:00Z"}}
```

### 7.8 Smoke-test path (gate clause 3)

The test runs these steps, and the prototype passes it (§0):

1. `Queue.enqueue(payload, nodes)` computes `keys`.
2. `lint(item, store)` returns no violations.
3. `decide(item, "accept")` calls `store.put(payload with status asserted)`.
4. `store.export("khg")` and `store.export("hif")` are exported.
5. The HIF export is validated against the profile, the C1 export against the C1 schema, and the queue
   stream against the C3 schema.
6. The test asserts that the exported `f1` has roles {condition, dosage, population, treatment} and that
   the HIF export folds back to the C1 export.

---

## 8. Validator and the malformed-case list

### 8.1 Layers and API

```python
from khg_contracts import validate
report = validate(obj_or_path, *, kind="auto",      # "khg" | "hif" | "schema" | "queue" | "auto"
                  schema=None,                        # RelationSchema; resolved from the header's id if None
                  texts=None,                         # {source id: text}, enables span-vs-text checks (S018)
                  mode="strict")                      # "strict" | "legacy" (HIF without the declaration, §4.6)
report.ok -> bool
report.findings -> list[Finding(code, layer, path, message, severity)]   # path is a JSON Pointer
```

| Layer | What runs | Applies to |
|---|---|---|
| **J** strict JSON | UTF-8; RFC 8259 JSON with no `NaN` or `Infinity` (`parse_constant` raises); no duplicate keys (`object_pairs_hook` raises); no lone surrogates; integers within ±(2^53−1) | every file |
| **H** HIF schema | the vendored `hif_schema_v0.1.0.json`, unchanged (F2) | HIF inputs |
| **P** profile | the draft-07 profile schemas (`khg-document`, `khg-hif-profile`), plus the Python structure checks P010–P013 | C1 documents, profile HIF, queue payloads |
| **S** semantic | Python checks against the relation-type schema (§3.5), lifecycle consistency, evidence, NFC | C1 (HIF is folded first) |
| **D** schema documents | the meta-schema plus D002–D006 | relation-type schemas |
| **Q** queue | the C3 schema plus Q002–Q006 | queue streams |

A document that fails a layer is not checked by later layers, so findings are never cascades of one
root cause. Schema-layer codes are attached to sub-schemas with an `x-khg-code` annotation. Draft-07
says unknown keywords "SHOULD be ignored" [R02 §4.1], and both validators do ignore it. The validator
maps each JSON Schema error to the nearest annotation on its schema path. jsonschema drives the codes.
fastjsonschema, the extra `[fast]`, is an accept/reject fast path that CI proves equivalent on every
fixture (§10). Structural lint (C3) calls the same function (§7.5).

### 8.2 Error codes

| Code | Meaning |
|---|---|
| KHG-J001 | not UTF-8, not JSON, or empty |
| KHG-J002 | duplicate object key |
| KHG-J003 | `NaN` or `Infinity` |
| KHG-J004 | lone surrogate |
| KHG-J005 | integer outside ±(2^53−1) |
| KHG-H001 | HIF `required` violated |
| KHG-H002 | HIF `additionalProperties` (an extra top-level or record-level key) |
| KHG-H003 | HIF `type` |
| KHG-H004 | HIF `enum` |
| KHG-P001 | declaration missing or wrong (`role-convention`, `khg-profile`, `khg-schema`, the `hif-schema` pin and its sha256; for C1, `khg-profile` and `khg-schema`) |
| KHG-P002 | `khg-profile` version not supported by this reader (another major, or a higher minor) |
| KHG-P003 | id rule: not a string, empty, a control character, or the reserved `_:` |
| KHG-P004 | incidence without `attrs.role`, or a role that is not a name |
| KHG-P005 | directed file with an incidence lacking `direction` |
| KHG-P006 | `network-type` absent or `asc` |
| KHG-P007 | `metadata.default_attrs` |
| KHG-P008 | derived node malformed, or an entity node using derived keys |
| KHG-P009 | HIF edge without `relation`/`status` |
| KHG-P010 | derived id does not match its derivation |
| KHG-P011 | node or edge declared twice |
| KHG-P012 | incidence names an undeclared edge or derived node |
| KHG-P013 | duplicate incidence (edge, node, role, position) |
| KHG-P014 | C1 record shape (binding value not exactly one; no bindings; field types) |
| KHG-P015 | literal malformed |
| KHG-P016 | status value, or the status/`superseded-by` coupling |
| KHG-P017 | evidence malformed (selector dependencies, confidence shape, digest form) |
| KHG-P018 | unknown field in a C1 record |
| KHG-P019 | reserved key inside opaque `attrs` |
| KHG-S001 | unknown relation |
| KHG-S002 | role not declared for the relation |
| KHG-S003 | required role missing (asserted, superseded, retracted) |
| KHG-S004 | more than `max` |
| KHG-S005 | filler kind not allowed |
| KHG-S006 | entity type mismatch |
| KHG-S007 | literal not allowed (`values`, calendar date, quantity bounds) |
| KHG-S008 | `unbound` outside a goal |
| KHG-S009 | `novalue` with another value |
| KHG-S010 | position rules |
| KHG-S011 | direction contradicts the declared direction |
| KHG-S012 | duplicate binding |
| KHG-S013 | dangling edge reference |
| KHG-S014 | nesting cycle |
| KHG-S015 | referenced relation not allowed |
| KHG-S016 | evidence missing |
| KHG-S017 | evidence ids duplicated or unknown |
| KHG-S018 | span inconsistent with `exact`, `digest` or the text |
| KHG-S019 | model evidence without `agent`/`version`/`run` |
| KHG-S020 | empty or reversed `valid` |
| KHG-S021 | score confidence outside its range |
| KHG-S022 | lifecycle records inconsistent (`superseded-by` ↔ `khg:supersedes`, `retracted` ↔ `khg:retracts`, self-supersession) |
| KHG-S023 | supersession across relations or key bindings |
| KHG-S024 | lifted valid-time role used as a binding |
| KHG-S025 | schema id not loaded or unsupported |
| KHG-S026 | duplicate node record, or duplicate edge version (same id and `recorded`) |
| KHG-S027 | string not NFC |
| KHG-S028 | candidate outside a queue payload *(store)* |
| KHG-S029 | key conflict under `reject` *(store)* |
| KHG-S030 | transition not in the table *(store)* |
| KHG-S031 | `relation` or `bindings` changed within an edge id *(store)* |
| KHG-S032 | non-monotonic transaction time *(store)* |
| KHG-D001 | meta-schema violation |
| KHG-D002 | undeclared role, type or relation in a usage |
| KHG-D003 | key names a role the relation does not use |
| KHG-D004 | `min > max` |
| KHG-D005 | valid-time role used by a relation |
| KHG-D006 | reserved `khg:` prefix in a domain schema |
| KHG-Q001 | queue line violates the C3 schema |
| KHG-Q002 | stream does not start with exactly one header |
| KHG-Q003 | recorded keys ≠ recomputed keys |
| KHG-Q004 | log entry names an unknown item |
| KHG-Q005 | decision after a terminal decision |
| KHG-Q006 | `accept`/`merge` with an open violation |
| KHG-L001 … L005 | queue lint rules (§7.5) |

Codes are stable across minor versions. A new check gets a new code and never reuses an old one.

### 8.3 The v1 malformed-case list (the gate's test list)

Each case is one file under `tests/fixtures/malformed/`, derived from the gate fixture or its HIF by one
change. "Source" names the research evidence. All 90 were executed (§0), and the first failing layer
matched in each. For Python-checked codes the listed code was also among the findings. Store-scope codes
S028–S032 are exercised by C2 scenarios C2-12, C2-16, C2-17, C2-18 and C2-25 instead.

| Id | Malformed case | Layer | Code | Source |
|---|---|---|---|---|
| M01 | zero-byte file | J | J001 | R02 case 34 |
| M02 | `NaN` in incidence attrs | J | J003 | R02 case 35; R03 c22; R01 V19 |
| M03 | duplicate key inside one `attrs` | J | J002 | R02 case 36 |
| M04 | lone surrogate escape in a label | J | J004 | RFC 8259 §8.2 (derived) |
| M05 | integer id 2^53+1 | J | J005 | R02 case 22; R03 c23 |
| M06 | no `incidences` | H | H001 | R01 V01; R02 case 31 |
| M07 | top-level `version` | H | H002 | R02 case 04 |
| M08 | top-level `roles` vocabulary block | H | H002 | R02 case 05; R01 V02 |
| M09 | top-level `$schema` | H | H002 | R02 case 06 |
| M10 | record-level `role` on an incidence | H | H002 | R02 case 11; R01 V03 |
| M11 | record-level `relation` on an edge | H | H002 | R02 case 13 |
| M12 | record-level `type` on a node | H | H002 | R02 case 14 |
| M13 | incidence `attrs` is a string | H | H003 | R02 case 10 |
| M14 | `direction: "treatment"` | H | H004 | R02 case 12; R01 V05 |
| M15 | `network-type: "knowledge-hypergraph"` | H | H004 | R02 case 26 |
| M16 | id `1.5` | H | H003 | R02 case 18; R01 V06 |
| M17 | id `null` | H | H003 | R02 case 20; R01 V06 |
| M18 | incidence without `node` | H | H001 | R01 V04 |
| M19 | no `role-convention`/`khg-profile` in metadata | P | P001 | R01 V07 |
| M20 | `hif-schema` is the moving `latest` URL, as in the KB sample | P | P001 | R01 PF-01; R02 §10 item 5 |
| M21 | integer ids (valid HIF, not the profile) | P | P003 | R02 cases 15–17; F10 |
| M22 | empty-string id | P | P003 | R02 case 21 |
| M23 | entity id with the reserved `_:` prefix (C1) | P | P003 | §4.4 |
| M24 | incidence without `attrs.role` | P | P004 | R01 V08 |
| M25 | list-valued `role` in profile mode (legacy import accepts it) | P | P004 | R01 V09; §4.3 |
| M26 | directed file, one incidence without `direction` | P | P005 | R01 V12; R02 case 23; R03 c14, D4 |
| M27 | `network-type: "asc"` | P | P006 | R03 c04, D8 |
| M28 | `metadata.default_attrs` | P | P007 | R03 c20, row 23, D7 |
| M29 | derived `_:lit:` node without its `literal` attrs | P | P008 | C1-R68 |
| M30 | HIF edge record without `status` | P | P009 | R01 V14, V40 |
| M31 | binding with both `node` and `literal` | P | P014 | C1-R06 |
| M32 | edge with no bindings | P | P014 | R01 V27 |
| M33 | quantity without `unit` | P | P015 | R01 V26 |
| M34 | time literal `2019-13` | P | P015 | R01 V26 |
| M35 | `text` literal without `lang` | P | P015 | R01 V26 |
| M36 | `status: superseded` without `superseded-by` | P | P016 | F8 |
| M37 | status `disputed` (not in the v1 enum) | P | P016 | R01 V36 |
| M38 | probability confidence 8.2 | P | P017 | R01 V32 |
| M39 | bare-number confidence | P | P017 | R01 V32; C1-R49 |
| M40 | span offsets without `digest` | P | P017 | F11; C1-R39 |
| M41 | stored `arity` field | P | P018 | R01 V15 (arity is never stored) |
| M42 | reserved key `status` inside opaque edge `attrs` | P | P019 | §2.4 |
| M43 | literal node id does not match its value | P | P010 | R01 D-09 |
| M44 | node declared twice | P | P011 | R01 V16; R03 c19, D5 |
| M45 | incidence names an undeclared edge | P | P012 | R02 case 29 |
| M46 | exact duplicate incidence (edge, node, role) | P | P013 | R03 D2 |
| M47 | unknown relation | S | S001 | R01 V21 |
| M48 | role not declared for the relation | S | S002 | R01 V22 |
| M49 | required role missing on an asserted fact | S | S003 | R01 V23 |
| M50 | role bound more often than `max` | S | S004 | R01 V24 |
| M51 | literal where an entity is expected | S | S005 | R01 V25 |
| M52 | entity of the wrong type | S | S006 | R01 V25 |
| M53 | `khg:reason` value `update` (not a belief-revision reason) | S | S007 | F7; §2.14 |
| M54 | `unbound` slot on an asserted fact | S | S008 | R01 V34 |
| M55 | `novalue` and a value for the same role | S | S009 | R01 V35 |
| M56 | ordered role without `position` | S | S010 | C1-R15 |
| M57 | direction contradicts the declared direction | S | S011 | R01 V38 |
| M58 | duplicate binding (same role and value) | S | S012 | C1-R14 |
| M59 | dangling hyperedge reference | S | S013 | R01 V18 |
| M60 | nesting cycle | S | S014 | R01 V28 |
| M61 | reference to an edge of a disallowed relation | S | S015 | R01 V29 |
| M62 | asserted fact without evidence | S | S016 | R01 V33 |
| M63 | binding cites an unknown evidence id | S | S017 | C1-R36 |
| M64 | span `[195, 211)` does not match `exact` in the source text | S | S018 | F11; R04 M6 |
| M65 | extracted evidence without `run` | S | S019 | R01 V47; C1-R38 |
| M66 | `valid` reversed (`from` 2024-01-01, `until` 2023) | S | S020 | R01 V30 |
| M67 | score confidence 11 on a 0–10 scale | S | S021 | R01 V32 |
| M68 | superseded fact with no `khg:supersedes` record | S | S022 | R01 V37; F8 |
| M69 | supersession across different key bindings | S | S023 | R01 V37 |
| M70 | lifted `start-time` used as a binding | S | S024 | §2.13 |
| M71 | unknown schema id | S | S025 | R01 V41 |
| M72 | edge record duplicated (same id, same `recorded`) | S | S026 | R01 V16 |
| M73 | id not in NFC (decomposed `ü`) | S | S027 | R03 c13; F11 |
| M74 | relation with no roles | D | D001 | R01 V43 |
| M75 | schema id without a semantic version | D | D001 | R01 V45 |
| M76 | unknown datatype `float` | D | D001 | R01 V46 |
| M77 | `end-older` on a non-temporal key | D | D001 | R04 M3 |
| M78 | usage names an undeclared type | D | D002 | R01 V46 |
| M79 | key names a role the relation does not use | D | D003 | R01 V44 |
| M80 | `min` > `max` | D | D004 | §3.1 |
| M81 | valid-time role also used in a relation | D | D005 | §2.13 |
| M82 | domain schema uses the reserved `khg:` prefix | D | D006 | §3.3 |
| M83 | queue payload in status `asserted`, not `candidate` | Q | Q001 | C3-R01; F9 |
| M84 | log action `delete` (outside the vocabulary) | Q | Q001 | R01 V48 |
| M85 | recorded `keys.core` differs from the recomputed key | Q | Q003 | C3-R04 |
| M86 | log entry names a missing item | Q | Q004 | R01 V48 |
| M87 | `reject` after `accept` | Q | Q005 | C3-R05 |
| M88 | `accept` while a violation is open | Q | Q006 | C3-R08 |
| M89 | stream does not start with its header line | Q | Q002 | C3-R12 |
| M90 | `khg-profile: "2.0.0"` | P | P002 | PLAN §7 (versioning) |

### 8.4 R01 candidates that are deliberately *not* malformed here, or not in v1

| R01 case | Status here | Why |
|---|---|---|
| V10: two incidence records for one (edge, node) pair | **legal** | one incidence per role (§4.3); only exact duplicates are malformed (M46) |
| V11: the same role twice in one `roles` list | not applicable | there are no role lists |
| V13: `direction` in an undirected file | **legal** | the paper allows it [R02 §3]; a mixed-direction document is written undirected with its directions kept (§4.5) |
| V17: incidence names a node without a node record | legal for entities | HIF allows it [R02 case 28]; derived nodes must be declared (M29, M45 via P012) |
| V20: legacy `role` and `roles` disagree | not applicable | legacy import reads one key (`--role-key`) |
| V31: transaction interval expires before it is created | not representable | the end of a version is derived from the next version (§2.13) |
| V39: node in both tail and head of a rule hyperarc | deferred to 1.1 | with `kind: "rule"` (§12) |
| V42: overlapping key bindings | store scope | C2-11 and C2-12 |
| V49: merge not in the log | deferred to 1.1 | replay-consistency check (§12) |

---

## 9. C5 scorers

**Scope rule for v1.** C5 1.0 contains exactly two things: every metric exercised by R05's unit-test
tables, which ship as tests (F14), and the headline numbers of the Phase-1 gates (P9, P3b, P7, P10).
Nothing else goes in: no LLM judge, no soft F1, no external-benchmark adapters (§12). Scorers are
deterministic, call no LLM, and read and write C1 terms. Values are C1 binding values (`{"node": …}`,
`{"literal": …}`, `{"edge": …}`, `{"special": …}`); arity is C1's `arity()` [R05 §1; C5-R01–R05].

### 9.1 API

```python
from khg_contracts.scorers import (score_extraction, score_completion, score_retrieval, score_memory,
                                   ExtractionConfig, CompletionConfig, RetrievalConfig, MemoryConfig,
                                   FilterIndex, rank_stats, PRESETS)

def score_extraction(gold: Iterable[dict], runs: Sequence[dict], schema: RelationSchema,
                     config: ExtractionConfig = ExtractionConfig()) -> dict
def score_completion(queries: Iterable[dict], outputs: Mapping[str, dict],
                     config: CompletionConfig = CompletionConfig()) -> dict
def score_retrieval(questions: Iterable[dict], responses: Mapping[str, dict],
                    config: RetrievalConfig = RetrievalConfig()) -> dict
def score_memory(questions: Iterable[dict], responses: Mapping[str, dict],
                 config: MemoryConfig = MemoryConfig()) -> dict

class FilterIndex:                                   # the known-answer index of C-M1
    @classmethod
    def build(cls, facts: Iterable[dict], schema: RelationSchema,
              mode: Literal["exact", "monotone", "time_aware"] = "exact") -> "FilterIndex"
    def known(self, query: dict) -> frozenset[str]
def rank_stats(scores: Mapping[str, float], target: str, known: Iterable[str]) -> dict   # model-side helper
PRESETS: dict[str, CompletionConfig]                 # "hype", "stare", "hyper"
```

Inputs are the C4 item shapes of §9.6 as plain dicts. Every output is a dict with:

- `versions`: `{c1, c5, c4_corpus, question_set, split, config_sha256}` [C5-R01]
- `aggregate`
- breakdowns, which always include `by_arity` with bins `2`, `3`, `4`, `5+` [C5-R02]
- `items`: per-item results keyed by stable ids, each listing the gold edge ids it depends on, for P8's
  per-fact join [C5-R03]

Empty-set conventions follow R05 §1 item 3: `no_predictions`, `no_gold` and `both_empty` are flagged. There
are three averages: micro over scoring units, macro over relation types, and macro over arity bins.
Dispersion is a 1,000-resample percentile bootstrap with seed 0, at 95 %, over documents, queries or
questions, and paired for comparisons (D-C5-18). Tie-breaking is lexicographic by id everywhere.

### 9.2 Extraction (P9)

Gold and predictions are deduplicated by content key, and the number removed is reported.

- **Alignment** is one 1:1 Hungarian alignment per document, weighted *value first*:
  `w = (N+1)·ν + β` within the same relation (E-M3). A pure-Python Hungarian solver is cross-checked
  against brute force in tests, and SciPy is used if it is installed (D-C5-17).
- **Metrics**:
  - E-M1 strict P/R/F1
  - E-M2 core P/R/F1, on the core key's bindings
  - E-M4 Arg-I and E-M5 Arg-C (binding F1)
  - **E-M6 role accuracy** = ΣTP_C / ΣTP_I
  - E-M7 pooled and `grouping_gap`
  - E-M8 pairwise projection F1
  - E-M9 participant-set match
  - E-M10 arity profile: recall by gold arity, precision by predicted arity
- **Literal rule**: `truncate_to_gold` by default, `exact` as a preset (§2.6: precision is read from the
  lexical form). Quantities match within `[lower, upper]` if gold has bounds.
- **Stability**, on both the content key and the core key: S-M1 mean pairwise Jaccard, S-M2, S-M3, S-M4
  churn, S-M5 gold partition, S-M6 dispersion, and **S-M7 Δ_order**. Runs carry `run` and `order`, taken
  from the C3 items.
- **P9's gate numbers** are E-M1 ("precision, recall"), with E-M5 beside it, E-M6 ("role accuracy"), and
  S-M1 plus S-M7 over 3 runs × 2 orders (6 within-order and 9 between-order pairs) [R05 §2.4].

### 9.3 Completion (P3b)

- **Filters**: `exact` by default. `monotone` and `time_aware` are reported beside it whenever qualifiers
  or `valid` exist (C-M1). Bindings are compared as sets, never as sequences (D-C5-08).
- **Ranks**: optimistic, pessimistic and realistic, plus the **tie-exact expectation** as the default:
  `E[RR]` and `E[Hits@k]` over the tie block (C-M2, C-M3).
- **MRR, Hits@1/3/10 and MR** are reported with three denominators: per task, per fact and macro over
  arity (C-M4). Breakdowns are by arity, role, slot class, position preset and seen/unseen (C-M5).
  Adjusted metrics are optional (C-M6).
- **Calibration** (P3b's gate) is top-1 correctness against any known-true filler (C-M7). It reports ECE
  with 15 equal-width and 15 equal-mass bins, Brier, and the reliability table, all per arity. Bins with
  fewer than 100 queries are flagged, and their counts reported. Per-candidate Brier is an option (C-M8).
- **Model interface**: rank statistics, not score vectors (D-C5-10): `{qid, n_candidates,
  n_filtered_out, n_greater, n_equal, target_prob, top1: {value, prob}, prob_map}`.
- **Presets** reproduce the originals [R05 §3.4]:
  - `hype`: all positions, pessimistic ties, full-tuple filter, per-task average.
  - `stare`: subject and object averaged, sort-order ties, `(s, r, quals)` filter, WD50K universe
    restricted to entities seen in subject or object position.
  - `hyper`: all positions, pessimistic ties.

### 9.4 Retrieval (P10, later P4)

- Cut-offs k ∈ {1, 3, 5, 10, 20}: `hit@k`, `support_success@k` (a complete alternative support set was
  found; the headline), `support_recall@k`, `mrr@k` (cut-off), `r_precision`, `ndcg@k` (discount
  `log2(i+1)`, named in the output), support P/R/F1/EM against the best-matching set, and
  `binding_coverage@k`, the common scale across hyperedge, pair and chunk units, which serve P4
  (R-M1–R-M8).
- **Answers** (R-M9): EM on canonical ids and typed literals first, then SQuAD-normalised EM and token F1
  on text, with the maximum over aliases; set P/R/F1/EM for `set` mode.
- **Joint and gated scores** (R-M10): joint P, R and F1, and `gated_em` (KILT). Abstention precision and
  recall (R-M11).
- **Cost** (R-M12): prompt and completion tokens, LLM calls, retrieval calls, hyperedges visited,
  retrieval and total milliseconds, and USD with a dated price table. Aggregates are mean, median, p90,
  p95 (nearest rank) and total. That is P10's cost and latency.
- The accuracy-against-token-budget curve is deferred. Character-substring matching is never used (unit
  test R8).

### 9.5 Memory (P7)

Each question fixes a key `(relation, key bindings, target role)`, an `as_of`, an `as_at`, and the value
sets `V_cur`, `V_old` and `V_fut`. The outcomes are O1–O7: `current`, `hedged`, `stale` (split into
`expired`, where valid time ended, and `revised`, where the fact was superseded or retracted),
`anachronistic`, `wrong`, `abstained`, and `correct_abstention`/`hallucinated`. R05's `retracted` bucket
is renamed `revised`, because C1 has two belief-revision statuses and F7 separates both of them from
`expired`.

The metrics are strict accuracy (the headline), lenient accuracy (LongMemEval-compatible), the stale rate
split into expired and revised, the stale share of errors, anachronism, hedge and abstention rates,
abstention precision and recall, optional ranked efficacy (CounterFact ES), `support_success@k` against
*current* support with history recall separate, and a per-item numeric tolerance, 0 by default
(M-M1–M-M8). Text-only systems are mapped by normalised alias match; a system that names both values is
`hedged` (D-C5-13, D-C5-14).

### 9.6 Question-set item shapes (the C4 draft P3a fills)

All ids are stable, and every item carries `split` and `qset_version`. Gold facts are **C1 edge
records**. The trace for memory questions is **a sequence of C2 `put` batches**, so any C2 store can
replay it. The trace below was replayed on the prototype store (§0). `find` for organisation `ex:acme`
returns `h2` as of now and `h1` as of 2020; as-at before step 2 it returns `h1` with no `until`. The
ended fact stays `asserted` (F7).

```json
{"doc_id": "p3a-doc-000017", "split": "test", "qset_version": "p3a-extraction/1.0.0",
 "text": "Albert Einstein received the 1921 Nobel Prize in Physics from the Royal Swedish Academy of Sciences.",
 "text_digest": "sha256:<of the NFC text>", "annotation": {"method": "distant+human", "exhaustive": false, "annotators": 2},
 "gold": [{"edge": "wd:Q937-stmt-1", "relation": "award-received", "status": "asserted",
           "bindings": [{"role": "recipient", "node": "wd:Q937"}, {"role": "award", "node": "wd:Q38104"},
                        {"role": "conferrer", "node": "wd:Q193592"},
                        {"role": "point-in-time", "literal": {"datatype": "time", "value": "1921"}}],
           "evidence": [{"id": "e1", "type": "imported", "source": "p3a-doc-000017", "digest": "sha256:<…>",
                         "exact": "<the sentence>", "start": 0, "end": 99}]}],
 "alternatives": {}, "aliases": {"wd:Q193592": ["Royal Swedish Academy of Sciences"]}, "seen_core_keys": []}

{"qid": "p3a-cq-004211", "split": "test", "qset_version": "p3a-completion/1.0.0", "edge": "wd:Q937-stmt-1",
 "relation": "award-received", "arity": 4,
 "target": {"role": "conferrer", "index": 0, "slot": "core", "value": {"node": "wd:Q193592"}},
 "context": [{"role": "recipient", "node": "wd:Q937"}, {"role": "award", "node": "wd:Q38104"},
             {"role": "point-in-time", "literal": {"datatype": "time", "value": "1921"}}],
 "as_of": null, "candidate_universe": "all_entities", "inductive": {"unseen_context_entities": 0, "unseen_relation": false}}

{"qid": "p3a-rq-000123", "split": "test", "qset_version": "p3a-retrieval/1.0.0", "type": "retrieval_qa",
 "text": "Which organisation awarded Albert Einstein the 1921 Nobel Prize in Physics?",
 "template_id": "award-received/conferrer/v1", "answer": {"mode": "single", "values": [{"node": "wd:Q193592"}]},
 "aliases": {"wd:Q193592": ["Royal Swedish Academy of Sciences", "Kungliga Vetenskapsakademien"]},
 "support": {"sets": [["wd:Q937-stmt-1"]]},
 "required_edge": {"edge": "wd:Q937-stmt-1", "relation": "award-received", "arity": 4,
                   "roles_used": ["recipient", "award", "point-in-time", "conferrer"]},
 "hops": 1, "source_class": "n-ary", "as_of": null, "answerable": true,
 "provenance": {"generator": "template", "generator_version": "1.0.0", "verified": "human", "verifiers": 2}}

{"trace_id": "p3a-mt-0007", "split": "test", "qset_version": "p3a-memory/1.0.0", "schema": "gate-demo/1.0.0",
 "steps": [
  {"step": 1, "at": "2026-01-10T09:00:00Z", "text": "Alice became CEO of Acme in May 2019.",
   "put": [{"edge": "h1", "relation": "chief-executive", "status": "asserted",
            "bindings": [{"role": "organisation", "node": "ex:acme"}, {"role": "person", "node": "ex:alice"}],
            "valid": {"from": "2019-05"}, "evidence": [{"id": "e1", "type": "curated", "source": "trace:p3a-mt-0007#1"}]}]},
  {"step": 2, "at": "2026-02-02T09:00:00Z", "text": "Bob took over as CEO of Acme on 1 January 2026.",
   "put": [{"edge": "h2", "relation": "chief-executive", "status": "asserted",
            "bindings": [{"role": "organisation", "node": "ex:acme"}, {"role": "person", "node": "ex:bob"}],
            "valid": {"from": "2026-01-01"}, "evidence": [{"id": "e1", "type": "curated", "source": "trace:p3a-mt-0007#2"}]},
           {"edge": "h1", "relation": "chief-executive", "status": "asserted",
            "bindings": [{"role": "organisation", "node": "ex:acme"}, {"role": "person", "node": "ex:alice"}],
            "valid": {"from": "2019-05", "until": "2026-01-01"}, "evidence": [{"id": "e1", "type": "curated", "source": "trace:p3a-mt-0007#1"}]}]}]}

{"qid": "p3a-mq-0042", "trace_id": "p3a-mt-0007", "ask_after_step": 2, "subtype": "current_value",
 "text": "Who is the CEO of Acme now?", "as_of": "end_of_trace", "as_at": "after_step",
 "key": {"relation": "chief-executive", "bindings": [{"role": "organisation", "node": "ex:acme"}], "target_role": "person"},
 "answer": {"mode": "single", "values": [{"node": "ex:bob"}]},
 "stale_values": [{"value": {"node": "ex:alice"}, "edge": "h1", "kind": "expired"}], "future_values": [],
 "support": {"current": ["h2"], "history": ["h1"]}, "aliases": {"ex:bob": ["Bob"], "ex:alice": ["Alice"]},
 "answerable": true, "tolerance": null, "keyed_relation_arity": 2, "n_changes_on_key": 1}
```

The response shapes are R05's (§2.6, §3.6, §4.6, §5.6), with values in C1 binding form and `retrieved`
units carrying the `edges` they derive from (back-pointers, D-C5-11). `stale_values[].kind` ∈ {`expired`,
`revised`} and `V_old` are **mandatory** on memory items, because a gold record that stores only the new
value forces an LLM judge [R05 §5.5; D-C5-15]. In the extraction item, `<…>` marks placeholders for the
digest and the sentence; the other four items are complete. R05's `n_supersessions_on_key` is renamed
`n_changes_on_key`, because under F7 the Alice → Bob change above is an end of validity, not a
supersession. The whole field list of R05 §6 is kept. These shapes become C4 only when P3a adopts
them.

### 9.7 Unit-test tables shipped as tests (F14)

All of R05's tables ship, 41 rows, with the hand-computed expected values written into the test files.
A meta-test compares them with R05's probe output (`c5_reference_cases.out.json`, copied into
`tests/c5/`).

| File | Rows | Includes |
|---|---|---|
| `tests/c5/test_extraction_table.py` | E1–E11 (with E5b, E5c), S1–S4 | E4: Arg-C F1 = 6/7, pairwise F1 = 2/3. E6: the nested-loop pitfall TP = 2 is reproduced by a local helper and contrasted with dedup. E8: Hungarian 2/3 vs greedy 0.5. S1: mean J = 2/3, churn 1/3. S3: Δ_order = 2/3 |
| `tests/c5/test_completion_table.py` | C1–C8 | C3: E[RR] = 25/48, E[Hits@1] = 0.25. C4: per task 0.40 vs per fact 0.55. C5: time-aware filter. C6: monotone filter. C7: ECE 0.13, Brier 0.1965. C8: ECE by arity 0.25 / 0.19 |
| `tests/c5/test_retrieval_table.py` | R1–R8 | R1: nDCG `log2(i+1)` 0.650921 vs the LongMemEval variant 0.75. R2: KILT recall 0.5. R3: token F1 4/7. R5: joint F1 0.285714. R8: substring trap = 0 by default |
| `tests/c5/test_memory_table.py` | M1–M8 | M3 hedged: strict 0, lenient 1. M5 anachronistic. M6 aggregate: strict 0.6, stale share 0.75. M8 tolerance |
| `tests/c5/test_hungarian.py` | — | pure-Python Hungarian against brute force on random small matrices, with a fixed seed |

The P2 gate does not exercise C5 [R05 §9 risk 1], so these tables *are* C5's acceptance test.

---

## 10. Package layout

```
pyproject.toml                         # repo root (F12)
src/khg_contracts/
  __init__.py                          # __version__ = "1.0.0"; CONTRACTS; public API re-exports
  _json.py                             # strict load/dump (layer J), JSONL, jcs(), sha()
  errors.py                            # CODES: code -> (layer, message template); Finding
  schema.py                            # RelationSchema: load/merge/validate (D), usage(), hypergraph() (P6)
  record.py                            # canonical(), arity(), participants(), content_key(), key_digest(), event_key()
  validate.py                          # validate(): layers J, H, P, S, D, Q; x-khg-code mapping
  hif.py                               # to_hif(), from_hif(mode=strict|legacy), derived ids, infer_schema()
  project.py                           # hyper_relational(), positional(), role_values(), render() (§2.19)
  loaders/__init__.py                  # lazy imports; khg_to_xgi, xgi_to_khg, khg_to_hnx, hnx_to_khg
  loaders/xgi.py  loaders/hnx.py       # §5
  store/__init__.py  store/protocol.py # Store Protocol, PutResult, KeyConflict, WalkStep, StoreError, CAPABILITIES
  store/memory.py                      # MemoryStore, HIFStore
  conformance/runner.py                # run(factory) -> EARL-shaped report; timing hooks
  conformance/scenarios/C2-*.json      # package data
  queue.py                             # Queue (JSONL stream), enqueue(), lint(), decide(), state(), replay()
  scorers/__init__.py extraction.py completion.py retrieval.py memory.py _hungarian.py _stats.py
  migrate.py                           # migrate(doc, to="1.0.0"); pre-1.0 KB dialect "0" -> 1.0.0
  cli.py                               # console scripts
  schemas/                             # package data
    hif/hif_schema_v0.1.0.json         # vendored, blob e2105bb, sha256 639466b7...; DOI 10.5281/zenodo.17257719
    hif/LICENSE.txt  hif/PROVENANCE.md # upstream MIT licence text; pinned URL, blob, hashes
    khg-document-1.0.0.json  khg-hif-profile-1.0.0.json  khg-schema-1.0.0.json  khg-queue-1.0.0.json
    builtin/khg-1.0.0.json             # khg:supersedes, khg:retracts
tests/
  conftest.py                          # blocks sockets (F1); markers gate, libs, evidence
  gate/test_g1_roundtrip.py  test_g2_malformed.py  test_g3_smoke.py       # clauses 1, 2, 3
  fixtures/gate/  gate-demo.schema.json  gate-fixture.khg.json  gate-fixture.hif.json  doc-pmid-0000001.txt
  fixtures/malformed/  MANIFEST.json  M01...M90.*
  c1/  test_canonical.py test_identity_keys.py test_literals_time.py test_arity.py test_schema_language.py
       test_hif_mapping.py test_legacy_import.py test_migrate_sample.py test_projections.py
  c2/  test_conformance_memorystore.py test_hifstore.py
  c3/  test_queue_replay.py test_lint_rules.py
  c5/  test_extraction_table.py test_completion_table.py test_retrieval_table.py test_memory_table.py
       test_hungarian.py reference_cases.out.json
  loaders/  test_native_ops.py test_determinism.py                          # libs
  evidence/ test_library_hif_functions.py                                   # evidence (not the gate)
```

**Public API** (`khg_contracts`): `load`, `dump`, `load_jsonl`, `dump_jsonl`, `RelationSchema`,
`validate`, `Report`, `Finding`, `canonical`, `arity`, `participants`, `content_key`, `key_digest`,
`event_key`, `to_hif`, `from_hif`, `project`, `migrate`, `CONTRACTS = {"C1": "1.0.0", "C2": "1.0.0", "C3": "1.0.0",
"C5": "1.0.0", "role-convention": "1.0.0"}`. The subpackages are `store`, `queue`, `scorers`, `loaders`
(import on demand) and `conformance`.

**Dependencies** (`pyproject.toml`):

```toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "khg-contracts"
version = "1.0.0"
requires-python = ">=3.10"
license = "MIT"
license-files = ["LICENSE"]
dependencies = ["jsonschema>=4.18,<5"]            # draft-07 + referencing registry (offline $ref)

[project.optional-dependencies]
xgi = ["xgi==0.10.2"]
hypernetx = ["hypernetx==2.4.3", "pandas>=2,<3"]   # HNX 2.4.3 declares pandas<3.0.0 [R03 §0.1]
fast = ["fastjsonschema>=2.19,<3"]
test = ["pytest>=8"]

[project.scripts]
khg-validate = "khg_contracts.cli:validate_main"
khg-convert = "khg_contracts.cli:convert_main"
khg-migrate = "khg_contracts.cli:migrate_main"
khg-conformance = "khg_contracts.cli:conformance_main"

[tool.hatch.build.targets.wheel]
packages = ["src/khg_contracts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["gate: a P2 gate clause", "libs: needs xgi and hypernetx", "evidence: library behaviour, report only"]
```

**CLI**:

- `khg-validate PATH… [--kind auto|khg|hif|schema|queue] [--schema S] [--mode strict|legacy] [--json]`
  exits 0 or 1 and prints findings with codes.
- `khg-convert IN OUT --to hif|khg|khg-jsonl [--schema S] [--legacy --source NAME --role-key role]`.
- `khg-migrate IN OUT [--schema-out S]`.
- `khg-conformance --store module:factory [--report out.json]`.

**CI**, on Python 3.10 (the floor) and 3.12:

```sh
python -m pip install -e ".[test]"                       && python -m pytest -m "not libs and not evidence"   # core, no heavy deps
python -m pip install -e ".[xgi,hypernetx,fast,test]"    && python -m pytest -m "not evidence"                 # gate and everything
python -m pytest -m evidence                                                                                 # report-only job; uploads evidence/library-hif-report.json
khg-validate tests/fixtures/gate/*.json && khg-conformance --store khg_contracts.store:MemoryStore
```

`tests/c1/test_schema_language.py` also validates every positive and negative fixture with *both*
jsonschema and fastjsonschema and asserts that they agree, keeping the schemas portable draft-07 (F5).
The probe suite of R03 is rerun whenever an extra's pin moves [R03 D10].

---

## 11. Versioning and migration

### 11.1 Identifiers

| What | Id | Versioned with |
|---|---|---|
| HIF role convention | `metadata["role-convention"] = "1.0.0"` | independently (upstream artefact) |
| C1 format, KHG HIF profile, C3 stream, C5 item shapes | `khg-profile: "1.0.0"` | together: PLAN §7 versions C3 and C5 "with C1" |
| C2 interface | `Store.interface_version = "1.0.0"`; implementations also state `format_version` [C2-R11] | independently (PLAN §7) |
| relation-type schemas | `khg-schema: "<name>/<semver>"`; built-in `khg/1.0.0` | by their owners (P3a, P9 …) |
| JSON Schemas | `$id = "urn:khg-contracts:schema:<name>:<semver>"`; identifiers, not locations, resolved by the offline registry | with the contract they define |
| package | `khg-contracts` 1.0.0 implements the 1.0.0 contracts; patch releases never change a contract | — |

### 11.2 Semver rules

- **MAJOR**: any conforming 1.x document becomes invalid or changes meaning; the canonical form changes;
  or any hash definition changes (content key, key digest, event key, literal node id). Keys are compared
  across runs and corpora, so a hash change is breaking.
- **MINOR**: additive only. New optional fields, enum values, datatypes, built-in relations, codes,
  scenarios or C5 metrics.
- **PATCH**: no document changes validity.

A reader accepts `khg-profile` with the same major and a minor ≤ its own. Otherwise it fails with
**P002** and an "upgrade khg-contracts" message: explicit, never silent. Closed records
(`additionalProperties: false`, as in HIF) make this necessary.

### 11.3 Migration policy

For each major there is a pure function `migrate_<from>_to_<to>(doc) -> MigrationResult(doc, schema,
report)`, chained by `khg_contracts.migrate(doc, to=…)` and exposed as `khg-migrate`. A major bump ships
its migration and reruns every consumer's gate (PLAN §7, §8). C5 outputs stamp every contract version, so
each project records what it consumed.

### 11.4 Migrating `schemas/sample.hif.json` (the pre-1.0 dialect "0")

Executed by `migrate_sample.py`. The output validates as C1, as a relation schema and as profile HIF.

| Rule | Pre-1.0 (sample) | 1.0.0 |
|---|---|---|
| R1 | `incidences[].attrs.role` (string) | **unchanged**: the convention kept the sample's key. All 9 role strings are identical in the migrated HIF |
| R2 | `edges[].attrs.relation`; `attrs.arity` | `relation`; `arity` dropped, because it is derived (§2.7; `f2` still has arity 3) |
| R3 | `edges[].attrs.source` | an evidence record `{"id": "e1", "type": "curated", "source": …}`. Provenance is not a role, so the domain fact `f3 publishes` keeps its `publication` binding [SCH pitfall 2] |
| R4 | `edges[].weight` (0.95, 0.80, 1.0), which the KB used as confidence [R01 PF-11] | `evidence.confidence = {"value": w, "scale": "score", "min": 0, "max": 1}`. This is a one-off rule for the known pre-1.0 dialect, recorded in the report: "score", not "probability", because nothing says the number is calibrated. `weight` is not kept. The general HIF importer never reads weight as confidence |
| R5 | `edges[].attrs.valid-from` | `valid.from` |
| R6 | `nodes[].attrs.type` (string), `label` | `types: [type]`, `label` |
| R7 | (no status) | `status: "asserted"`; per-incidence `direction` kept on the binding |
| R8 | `metadata.schema` (the moving `latest` URL), `metadata.conventions` | both dropped and replaced by the declaration (`khg-profile`, `khg-schema`, and on HIF export the pinned `hif-schema` with its sha256); `title`, `description`, `created` and `kb-section` kept |
| R9 | no relation-type schema | `kb-sample/1.0.0` inferred: observed types, `max` (`agent` → `null`), directions; every usage is `core` |

The migrated `f1`, in C1:

```json
{"edge": "f1", "relation": "treats", "status": "asserted", "valid": {"from": "2024-01-01"},
 "evidence": [{"id": "e1", "type": "curated", "source": "doc:guideline-2024", "confidence": {"value": 0.95, "scale": "score", "min": 0, "max": 1}}],
 "bindings": [{"role": "condition", "node": "disease:T2DM", "direction": "head"}, {"role": "dosage", "node": "dose:500mg-bid", "direction": "tail"},
              {"role": "population", "node": "pop:adults", "direction": "tail"}, {"role": "treatment", "node": "drug:metformin", "direction": "tail"}]}
```

and its HIF incidences are the sample's own, for example
`{"edge": "f1", "node": "disease:T2DM", "direction": "head", "attrs": {"role": "condition"}}`. The KB's
sample was one metadata block away from following the convention. That is a point for the upstream
proposal.

---

## 12. v1 scope, later versions, and the upstream proposals

### 12.1 What 1.0 gives each Phase-0 and Phase-1 gate (F13)

| Consumer (gate) | In 1.0 | Requirements met |
|---|---|---|
| **P2** | everything in §1's gate table | gate clauses 1–3 |
| **P3a** (corpus, C4) | C1 records with literals carrying precision (ISO 8601 / EDTF forms), units and bounds, `text@lang`, `somevalue`/`novalue`, rank, references (`evidence.reference`), valid time lifted from P580/P582 with inclusive-end conversion, core key (leak check), content key (dedup), one `arity()`, JSONL, the schema language with slot classes and `valid-roles`, the C4 item shapes (§9.6), and the validator and CLI | C1-R02, R06–R08, R16, R17, R29, R37, R43, R46, R47 (intent), R52; C5-R06 |
| **P3b** (replication, calibration) | projections (`hyper_relational`, `positional`, `role_values`, `drop_literals`); completion scorer with presets `hype`/`stare`/`hyper`, tie-exact ranks, three denominators, calibration per arity | C1-R11, R58; C5-R20–R23 |
| **P1** (five stores) | C2 Protocol, `MemoryStore`, `HIFStore`, 27 conformance scenarios with capability flags and timing, the canonical form for fidelity, layout rules for the other four backends (§6.8) | C2-R01–R11, R13, R15, R16, R18, R19 |
| **P6** (schema width) | global roles, `RelationSchema.hypergraph()`, deliberately cyclic schemas expressible | C1-R26, R27 |
| **P7** (identity, memory) | declared keys (temporal flag, collision policy), four lifecycle axes, `khg:supersedes`/`khg:retracts`, immutable versions, `as_of`/`as_at`, supersession walk, memory scorer with expired/revised stale split, text rendering for the flat baseline | C1-R28, R41, R42, R46; C2-R05, R07, R18, R19; C5-R18, R19 |
| **P9** (extraction) | the C3 stream, one item kind, lint = validator plus L001–L005, verdicts per (candidate, evidence), extraction scorer with role accuracy and stability over runs × orders, event keys | C3-R01–R08, R10–R13; C5-R07–R13 |
| **P10** (walker) | complete, deterministic `incident`; status and time filters; `render()`; retrieval scorer with cost and latency | C2-R03, R16; C5-R14–R16 |
| **P5** (reader study) | labels, direction, HNX roles as cell properties, `XGIBundle.roles(edge)` | C1-R19, R21, R70 |

### 12.2 Later versions (each with the version it would land in)

| Item | Version | Needed by | Why not in 1.0 |
|---|---|---|---|
| Relation `kind: "rule"` and tail/head disjointness (V39) | 1.1 | P10 (if rules are walked), P11 | no Phase-1 gate uses rule hyperarcs |
| Co-occurrence constraints `requires`, `excludes`, `at-least-one-of`, `must-differ`, `must-agree` [R04 M1] | 1.1 | P9 lint, P3a | C1-R34 is MAY |
| Explicit `primary` pair | 1.1 | P1 (RDF 1.2 annotation form) for relations without a unique core tail/head pair | 1.0 derives it (§2.19) |
| Status `disputed` | 1.1 if P7 asks | P7 case 3b | rank `deprecated` covers it, as in Wikidata |
| Pairwise projection with back-pointers [C1-R59] | 1.1 | P4 (Phase 2) | — |
| Datatypes `coordinate` and `boolean`; precisions coarser than a millennium; type hierarchy (`parents`) | 1.1 | P3a if its property set needs them | not in the Phase-1 gates |
| Epistemic flags on evidence (`negated`, `hypothesis`); verdicts `span-boundary`, `negated`; quality lints (C3-R09 rates); replay-consistency check (V49) | 1.1 | P9 | SHOULD |
| Entity merge and redirect records [C2-R20]; C2 `versions(id)` | 1.1 | P9, P7 | MAY |
| External benchmark adapters (GraphRAG-Bench pinned by arXiv id and commit, the LongMemEval KU subset, LoCoMo run in place) [D-C5-16]; soft F1 E-M12; accuracy-against-budget curve; HyperRED quintuplet preset | 1.1 | P4, P7 (optional), P8 | not in the unit-test tables |
| Generators: LinkML, TypeQL, SQL DDL, SHACL 1.2 (`sh:uniqueValuesFor`, reifier shapes) | 1.1 | P1 | SHOULD; SHACL 1.2 is still a Working Draft [R04 risk 8] |
| Valid-time uncertainty bounds (P1319/P1326/P8554/P8555/P12506) [R04 M4] | 1.1 | P3a | uncertain dates are not in the Phase-1 gates |
| Evidence type `agent`; per-slot expected types on `unbound`; binding proposals for goals | 1.2 | P11 (Phase 3) | — |
| Per-binding validity [C1-R48]; tombstoned bindings and per-field suppression [C1-R10, R45] | 1.2 | P7's [07.10] test; governance | MAY; [10.6] is open |
| Three-valued, precision-aware `as_of` | 1.2 | P7 | 1.0 uses the start-instant reading (§2.13) |
| Structural `role` on HIF incidences, or a HIF data-file version marker | 2.0 | — | only if HIF v2 adopts them (§12.3); migration maps `attrs.role` → structural `role` |

### 12.3 The upstream HIF proposal (F15): issue first, v1-compatible

**Where.** An issue on `HIF-org/HIF-standard`. It would be the first issue from outside the author group
[R02 §8–9]. It is discussed at the group's meetings or on Discord [R02 §8]. A PR follows only after
agreement, limited to README text plus compliant fixtures, the kind of small PR the maintainers have
accepted within days [R02 §8].

**Title:** *Proposal: a `role` convention for incidence attributes (HIF v1-compatible, no schema change)*

1. **Summary.** The three rules of §4.1:
   - `attrs.role` is a string.
   - A node that plays several roles in one edge has one incidence record per role, and records of a pair
     may differ in `direction`.
   - The file declares `metadata["role-convention"]`, optionally with `metadata["role-vocabulary"]`.
2. **Motivation.** The paper's own example of an incidence attribute is a role (`{"role": "PI"}`, p.7).
   The compliant fixture `single_incidence_with_attrs.json` uses the same key. Knowledge hypergraphs need
   roles to say who does what. Without a shared key, producers diverge [R01 PF-03].
3. **Four fixtures** for `tests/test_files/HIF-compliant/`:
   - (A) a role in `attrs`;
   - (B) one node with two roles in the same direction (c05);
   - (C) one node as tail and head of one edge (c06, the paper p.3–4);
   - (D) the declaration block.
   All four validate against the current schema [R02 §5].
4. **What does not change**: the schema, and the semantics of `weight`, `direction` and `network-type`.
5. **Evidence**: the library-evidence report (§5.5). XGI 0.10.2's reader keeps 0 of 34 roles.
   HyperNetX 2.4.3 keeps 32 of 34, drops the second record of each repeated pair, and drops all metadata
   except `name`. The reference loaders keep 34/34 offline. Links to the P2 package.
6. **Separately, for the v2 discussion** (#51, #55):
   - (a) a structural per-incidence `role` field, generalising `direction`, following the group's rule
     "separate structural information … from metadata" from #21;
   - (b) a data-file version marker, since top-level keys are closed in v1 [R02 §4.1, §10];
   - (c) state explicitly that (edge, node) pairs may repeat and may differ in `direction` [R02 §3,
     inconsistency 2];
   - (d) state that readers keep unknown `attrs` keys on round trip [R03 §7.5].

   Precedent: #44 (temporal presence as attrs first) [R02 §6].
7. **Non-dependency.** P2's gate does not wait on this issue. Upstream has had no commits for six months
   [R02 §8].

### 12.4 Issues for XGI and HyperNetX (from R03's root causes)

**XGI** (`xgi-org/xgi`):

1. `read_hif`/`write_hif` drop incidence `attrs` and every `weight`: roles 0/34 on the P2 fixture (X2,
   X3).
2. A directed file with a missing `direction` raises a bare `KeyError`, and any value other than `tail`
   silently becomes head (X4).
3. `from_hif_dict` splats attrs into `add_node`/`add_edge`, giving a `TypeError` for attrs keys `node`,
   `members` and `idx` (X5; c21, c26).
4. Output order depends on `PYTHONHASHSEED` (X8).
5. `asc` loses network attributes (X7).
6. `subhypergraph` raises on a `DiHypergraph` [R03 §5.1].

**HyperNetX** (`pnnl/HyperNetX`):

1. The schema is fetched over the network on every call; vendor it and allow `validate=False` (N1;
   #171).
2. The `HyperNetXError` it builds is never raised, so the functions return `None` (N2).
3. Metadata other than `name` is dropped (N4), and `to_hif(metadata=dict)` returns `None` (N9).
4. `default_attrs.incidences.direction: null` is re-read as a column default, so HyperNetX cannot read
   its own directed output (N5) [R03 §4.2].
5. Missing values are written as `"nil"` (N6).
6. `network-type` is never read (N7).
7. Isolated nodes and empty edges are dropped on export (N8).
8. Duplicate (edge, node) rows are dropped and `aggregate_by` is unused (N3).
9. Empty `incidences` crash the reader (N11).
10. Files are not closed (N12).

All of these are filed as issues with the evidence report attached, and PRs are offered where they are
small [R03 D12]. The gate depends on none of them.

---

## 13. Decisions log

### 13.1 R01 decisions D-01 to D-22

| Id | Decision | Choice | Rejected | Evidence |
|---|---|---|---|---|
| D-01 | Where roles live in HIF | R01's options (a) and (c) combined: the `attrs.role` string, with one incidence record per role (repeated pairs legal); `role-convention` declaration | (b) `attrs.roles` list per pair (R01's recommendation); (d) namespaced `khg:roles`; (e) an edge-level role map | paper p.7; upstream compliant fixtures [R02 §6]; c06 needs separate records [R03 §8]; F1 removes the library objection; measured 34/34 (§0) |
| D-02 | Version and schema pin | metadata `role-convention`, `khg-profile`, `khg-schema`, `hif-schema` (commit-pinned URL of blob `e2105bb`), `hif-schema-sha256`; a data-file marker requested for v2 | a top-level key (invalid [R02 case 04]); the schema URL alone | three version labels for one schema and a 404 `$id` [R02 §4; PF-01]; F2, F3 |
| D-03 | One slot class or two | one binding list; `core`/`qualifier`/`meta` per usage | a separate `qualifiers` list (SCH §6.2); a single class | qualifier monotonicity [SCH §4]; meta qualifiers dominate [R04 §8.2] |
| D-04 | Role identity | global roles plus usages (F4); main-snak naming left to P3a with P6 | relation-local roles | local roles make P6 trivial; the naming does not change α-acyclicity [R04 §8.2] |
| D-05 | Identity and keys | four identifiers, one stored, one hash rule (JCS + SHA-256) | text as id; member set; name plus type; label plus participants | Wikibase and INDRA [R04 M3]; LIM §11 |
| D-06 | Arity | core and qualifier bindings except `novalue`/`unbound`; `participants` beside it | distinct participants; core only; positions | sample f2 = 3; one function for P3a, P9 and C5 [R05 §9 risk 3] |
| D-07 | Validity granularity and time model | edge `valid` field (ISO/EDTF precision, half-open); P580/P582 lifted with inclusive → exclusive end; P585 stays a binding; per-binding validity in 1.2 | time only as qualifiers; both, with a consistency rule; snapshots | SQL:2011 and Graphiti use columns [R04 M4]; one representation; deviates from C1-R47's letter, not its intent |
| D-08 | Status, rank and transitions | four axes (F7); five statuses; written transition table; no `disputed` | one status; status plus rank | Wikidata's outdated/superseded/preferred [R04 M5]; conflicts handled by rank, as in Wikidata [R04 §3.3] |
| D-09 | Literals in HIF and stores | inline in C1; not nodes in C2; value-shared `_:lit:<hash>` nodes in HIF | one node per binding | Wikidata RDF value nodes; walkers use C2, so no hubs there |
| D-10 | Supersession | `khg:supersedes` edge plus `superseded-by` index (F8, **objected**, §2.14) | field only; closing intervals only | nanopublications and PROV [R04 M5]; Graphiti loses history [R04 M4] |
| D-11 | Nesting depth | unbounded, acyclic; conformance covers one level | none; one level | META §1, §8 |
| D-12 | Direction model | per binding with a role default, materialised; `directed` iff every binding has one | per incidence only; none | paper §3.2 [R02 §3]; XGI `DiHypergraph` holds tail and head [R03 row 4] |
| D-13 | Confidence and weight | confidence on evidence `{value, scale}`; `weight` opaque, never written, never read as confidence | weight = confidence (the sample); both | XGI drops weights, HNX invents 1 and sums on collapse [R03 D6] |
| D-14 | Evidence granularity | flat evidence records: W3C selector names, activity fields, ECO-mapped type, `reference` bindings, per-binding refs by id | a source field only; full nanopublication graphs | INDRA, Wikidata references, W3C Web Annotation [R04 M6] |
| D-15 | Schema-language syntax | own JSON plus a draft-07 meta-schema, LinkML-shaped; generators in 1.1 | LinkML, SHACL or TypeQL as the source | dependency weight and missing temporal keys [R04 §8.1] |
| D-16 | Store semantics | `at_least` default with `exact`; `as_at` defaults to latest; **`as_of` defaults to no filter**; status `asserted`; edge-id order; pagination by key; capability flags | `as_of` = now (R01) | SQL:2011 application time [R04 M4]; historical KBs |
| D-17 | Erasure | out of v1; whole-record `visibility: suppressed` only | delete the fact or the incidence | GOV §4(b); [10.6] open |
| D-18 | Queue | separate append-only stream; one item kind; goals reach HIF via `_:unbound:` nodes | candidates stored with the facts; four item kinds; a goal as an edge without incidences | F9; one uniform binding → incidence rule |
| D-19 | Loader strategy | public constructors plus a context (F1) | the libraries' HIF functions | R03 §3, §4 |
| D-20 | Gate fixture | adversarial, 12 edges (§2.18) | the sample's `f1` | R01 D-20 |
| D-21 | Extraction matching | strict + core + Arg-I/Arg-C + role accuracy under value-first Hungarian alignment; soft F1 in 1.1 | greedy; role-first alignment | R05 §2.5 pitfalls 4–5 |
| D-22 | v1 scope | the P2 gate plus the Phase-1 gates (§12.1) | everything at once | PLAN §7, "versioned, not frozen" |

### 13.2 R03 decisions D1 to D12

| Id | Choice | Rejected | Evidence |
|---|---|---|---|
| D1 XGI side store | A: a context table bundled with `H`; strict export raises on stale or unlabelled records | B: records in edge attrs (survives `<<` but loses records silently); C: a node → roles map (integer ids become strings as JSON keys) | R03 §7.4 operation table |
| D2 multi-role encoding | a: one incidence per role | b: a role list; c: forbid | c06; §4.3 |
| D3 the libraries' HIF functions | never called | patch their results | F1; R03 §3 |
| D4 missing or invalid direction | refused (P005, H004) | default to tail or head | XGI raises `KeyError`; HNX writes `"nil"` |
| D5 duplicate declarations | refused (P011) | merge (XGI) or first wins (HNX) | c19 |
| D6 record-level weight | never invented, carried verbatim, no meaning | carry confidence | R03 rows 9–11 |
| D7 HNX-interpreted metadata | `default_attrs` refused (P007), renamed on legacy import; `name` allowed | allow | c20 |
| D8 `asc` | refused (P006) | allow | c04: 9 → 39 incidences |
| D9 native operations | documented safe, reported and unsafe lists (§5.3); strict mode | allow all | R03 §5 |
| D10 dependencies | extras pinned to the probed versions; probes rerun when a pin moves | hard dependencies | pandas < 3; `DiHypergraph` is experimental |
| D11 output order | canonical order; structural comparison | library order | 4 outputs for 4 hash seeds [R03 §4.1] |
| D12 upstream | issues filed (§12.4); gate independent | none | F15 |

### 13.3 R04 decisions O1 to O13

| Id | Choice | Note |
|---|---|---|
| O1 role identity | global plus usage | as recommended |
| O2 binding shape | **list of bindings**, not role-keyed | deviates. F5 moves cardinality checks to Python, so the draft-07 advantage is gone, while a list maps one-to-one to incidences and to R05's items (§4.3) |
| O3 key declaration | roles, `temporal`, `on-collision` ∈ {reject, flag, end-older, supersede-older}, default `flag` | `same_fact` dropped because it would merge on collision [C3-R10]; the store raises only on `reject` |
| O4 lifecycle model | four axes | no `disputed` in 1.0 (§2.14) |
| O5 supersession carrier | meta-record plus index | F8; the index is objected to |
| O6 versioning | immutable versions; transaction end derived | as recommended |
| O7 evidence typing | four-value `type` mapped to ECO; assertion mode derived from it | a separate `assertion_mode` field would duplicate `type` |
| O8 span convention | code points, half-open, NFC, `digest`, quote and position selectors | F11 |
| O9 verdict unit | (candidate, evidence), keyed by content and event keys | as recommended |
| O10 schema syntax | own JSON, LinkML-shaped | as recommended |
| O11 dialect | draft-07; jsonschema in core, fastjsonschema optional, both checked equal in CI | F5, F12 |
| O12 slot classes | **three** (`core`, `qualifier`, `meta`) | `time` is not needed because validity roles are lifted (§2.8) |
| O13 conformance format | declarative JSON scenarios, EARL-shaped report, capability flags | as recommended |

### 13.4 R05 decisions D-C5-01 to D-C5-18

| Id | Choice |
|---|---|
| D-C5-01 | whole-fact unit for E-M1; bindings under one alignment for Arg-I, Arg-C and role accuracy; HyperRED quintuplets as a 1.1 preset |
| D-C5-02 | value-first Hungarian alignment, lexicographic tie-breaks; pooled scores as the grouping diagnostic |
| D-C5-03 | canonical ids required; linking scored separately; SMATCH-style mapping in 1.1 |
| D-C5-04 | `truncate_to_gold` default, `exact` preset, no partial credit |
| D-C5-05 | mean pairwise Jaccard, churn, gold partition, Δ_order, each on content and core keys |
| D-C5-06 | tie-exact expectation by default; optimistic, pessimistic and realistic as an audit; per-model presets |
| D-C5-07 | per task, per fact and macro over arity; replication headlines per task |
| D-C5-08 | `exact` filter by default; `monotone` and `time_aware` reported beside it; set equality of bindings |
| D-C5-09 | top-1 ECE (15 equal-width and 15 equal-mass bins) plus Brier, per arity, probability map declared |
| D-C5-10 | rank statistics as the model interface |
| D-C5-11 | back-pointers on units; `binding_coverage@k` as the common scale |
| D-C5-12 | alternative support sets; `support_success@k` as the headline; KILT recall only in the 1.1 adapter |
| D-C5-13 | structured answers scored deterministically; LLM judges only through adapters |
| D-C5-14 | O1–O7, strict headline, lenient beside it, stale split into `expired`/`revised` (renamed from `retracted`) |
| D-C5-15 | R05 §6 fields as the C4 draft (§9.6), in C1 terms; `V_old` and `V_fut` mandatory |
| D-C5-16 | external adapters in 1.1, run in place, never vendored (licences [R05 §7]) |
| D-C5-17 | pure-Python Hungarian, brute-force checked; SciPy used if present |
| D-C5-18 | K ≥ 3 runs; percentile bootstrap, 1,000 resamples, seed 0; paired bootstrap for comparisons |

### 13.5 Decisions of this design not asked above

| Decision | Choice | Why |
|---|---|---|
| C1's shape | folded HIF: HIF's names; binding = incidence | the smallest mapping; the upstream story is the same file |
| Node and edge id namespaces | separate, as in HIF | the paper's disjoint union; upstream data reuses ids [R02 case 03]; legacy import would otherwise fail on typical files |
| Derived node ids | `_:` prefix plus explicit attrs; literals content-hashed and shared; specials per binding | N-Triples blank-node convention; Wikidata RDF value and somevalue practice |
| Time precision | carried by ISO 8601 / EDTF lexical forms, not a separate field | the standard forms exist; a precision field could disagree with the value |
| Lifecycle actions | no C2 lifecycle methods; everything is `put` of versions plus meta-records | one write path for implementers |
| Stored keys | none besides `edge` | derived values stored alongside their source disagree (V15) |

---

## 14. Risks and open questions

### 14.1 Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | **Lifting P580/P582 into `valid` deviates from C1-R47's letter**, and P3b's baselines may count start and end as qualifier positions | `hyper_relational()` and `positional()` re-emit them deterministically. P3a reports `arity` and, for WikiPeople-style comparisons, arity plus the number of valid bounds. P3a and P3b confirm before C4 |
| 2 | Wikidata's coarse precisions (7 = century, 8 = decade) may not map one-to-one to EDTF `19XX`/`192X`: Wikibase shows a year at century precision as an ordinal century (1901–2000) [unverified here] | P3a fixes the importer rule; test cases in `test_literals_time.py` |
| 3 | The start-instant `as_of` reading is optimistic for coarse precision ("from 2019" is valid on 2019-03-01) | documented; three-valued comparison in 1.2 if P7's memory questions need it |
| 4 | Value-shared literal nodes create hubs in HIF-level analyses (XGI/HNX statistics, P5 drawings) | C2 and the walkers are unaffected (literals are not nodes); a per-binding literal export option in 1.1 if P5 asks |
| 5 | The redundant `superseded-by` index (F8) can disagree with the records | S022 checks agreement on every write; objection raised |
| 6 | No fact-level confidence: consumers that want one must declare an aggregation | C5 configurations name it; revisit if P10 or P8 needs a stored value |
| 7 | No `disputed` status | P7 case 3b uses rank and key-conflict reports; 1.1 if P7's classification needs a status |
| 8 | jsonschema 4.26 depends on `rpds-py`, whose newest release needs Python ≥ 3.11 [R04 §8.1] | pip resolves an older wheel on 3.10; CI runs 3.10; fastjsonschema (zero dependencies) is the fallback path |
| 9 | XGI's `DiHypergraph` is "experimental"; HNX pins pandas < 3 | extras pinned; the R03 probe suite reruns when a pin moves [R03 D10] |
| 10 | HNX users see the reserved cell key `khg:extra-incidences` | documented in the loader's docstring; it only exists in memory |
| 11 | Upstream HIF is quiet (no commits for six months) | the gate is independent; the convention works without adoption (F15) |
| 12 | Absent key roles compare equal (conservative), so some conflicts may be flagged spuriously for P7 | P7 confirms or overrides in 1.1 (for example with `consider-absent-distinct`) |
| 13 | Legacy import drops empty HIF edges (a C1 edge needs a binding) | reported per file; foreign round trips document it |
| 14 | The reference store validates a batch against the whole store (O(n) in the prototype) | the package validates against indexes restricted to the ids the batch references |
| 15 | TypeDB lacks `ordered` and `special_values` natively | reported as capability gaps (`inapplicable`), not as fidelity loss |

### 14.2 Open questions for the director

1. Accept lifting P580/P582 into `valid`, which meets C1-R47's intent but not its letter? The
   alternative is to keep them as bindings and add a consistency rule with a `time` slot class.
2. F8: keep `superseded-by` in C1, or make it store-internal in 1.1 (the objection)?
3. `as_of` defaults to no filter (SQL:2011), overriding R01 D-16's "as-of now". Agreed?
4. Is `disputed` needed in 1.0 for P7's contradiction cases, or is rank `deprecated` enough until P7
   says otherwise?
5. Who owns the RDF relation-instance, incidence-table and property-graph projections in 1.0: P1's
   adapters (this design), or P2's package?
6. Main-snak role naming, and which Wikidata qualifiers are `meta`: this needs a joint P3a/P6 decision
   before C4 is frozen [R01 D-04; R04 §8.2].
7. Should the upstream issue also propose `role-vocabulary`, or only the three core rules, to keep the
   ask as small as possible?
8. Is dropping a stored fact-level confidence acceptable to P10 and P8?
