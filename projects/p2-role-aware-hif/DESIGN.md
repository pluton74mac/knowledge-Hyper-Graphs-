---
title: "P2 design: role-aware HIF and the shared contracts C1, C2, C3 and C5"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# P2 design: role-aware HIF and the shared contracts

This is the authoritative design for P2 ([README](README.md); [PLAN §3, §4, §7](../PLAN.md)). It merges three
designs, A standards-first [DA], B semantics-first [DB] and C consumer-first [DC]
([research/designs/](research/designs/)), under the verdicts of three judges: implementer [J-impl], consumers
[J-cons] and standards [J-std]. **B is the base.** §13 lists every ruling, graft and revision decision. Reports
are cited as [R01]–[R05].

**This revision** answers the 87 findings of the four-lens critique (gate and libraries, semantics, consumers,
scope and build). The *Revision log* at the end names every finding and what was done. The *Implementation plan*
gives the module order, the tests of each module and the gate clause it serves.

The director's decisions F1–F15 hold. **Objections to F1–F15: none.** Two notes on scope follow.
- fastjsonschema moves into the core dependencies (§10.3). It is pure Python and has no dependencies, so the core
  stays light, as F12 requires.
- The gate's "same bytes" check compares canonical serialisations, which are structural normal forms, not file
  bytes (F10).

Every machine-readable part is in [design-examples/](design-examples/). The prototypes in
[research/designs/work-synthesis/](research/designs/work-synthesis/) generate and check those files.
`regenerate.sh` rebuilds all 151 files byte-identically and runs both validation modes (§1.4).

## 1. Summary and the gate

### 1.1 The design in brief

- **C1 `khg-record/1.0.0`.** A `.khg.json` or `.khg.jsonl` container holds `entity` and `hyperedge` records.
  - A hyperedge is a relation plus bindings `{bid, role, value, position?, direction?, extensions?}`.
  - Slot classes (core, qualifier, time, meta) come from the relation-type schema.
  - Values: entity, typed literal, fact reference, `somevalue`, `novalue`, and `unbound` in goals.
  - Canonical JSON uses RFC 8785 numbers.
- **Identity and time.**
  - Four identifiers (F6); `event_hash` is stored once, at extraction.
  - Value identity: a time literal is its proleptic-Gregorian window plus its precision. So the Julian and
    Gregorian writings of one day are one value.
  - Wikidata's precision windows: ordinal centuries and millennia, BCE years in historical numbering.
  - Time models `interval`, `invariant` and `timeless` (the default).
  - A normative bound table for literal, `somevalue`, `novalue` and absent bounds, with definite and possible
    readings.
  - Refine-only versions, checked by bid. Four lifecycle axes (F7). Lifecycle records plus a validated
    `status_ref` (F8).
  - A key invariant on the definite windows. It raises `KeyCollision`, whose info gives every collision with its
    policy and, per conflict, a shape, a class and an action.
- **HIF.**
  - `role-convention` 1.0.0 has four rules and its own validator layer R. The `khg-hif/1.0.0` profile adds khg
    bookkeeping on top.
  - One incidence per binding. Derived nodes carry literals, special values and fact references. Native
    directions stay.
  - Binding extensions and weights map onto incidences. Slices are closed.
- **Around C1.**
  - Loaders build library objects with public constructors (F1). XGI keeps its records in a context; HyperNetX
    keeps them in the cells. A strict rule governs export.
  - C2 has 9 core and 6 derived methods, 4 events and 10 capability flags. Header state is kept. The suite has
    114 executable scenarios.
  - C3 is one queue file per (run, order), with `Queue.accept` and `replay(base=…)`.
  - The validator has 11 checking layers (J to I) plus lint (L) and migration (F) codes. It registers 134 codes
    (128 active, 6 reserved); 31 planned codes of later versions are not registered.
  - The G2 list has 180 malformed cases, each checked mechanically.
  - C5 has one `score()` per ability, normative memory gold, the C4 draft `khg-c4-items/0.2.0` (ruling 20) and the
    C5 output schema `khg-c5-io/1.0.0`. All of it is in `khg-contracts` (F12).

### 1.2 The gate, clause by clause

| Clause | Test | Asserts | Evidence now |
|---|---|---|---|
| **G1** round trip with roles intact | `tests/gate/test_roundtrip.py` | See the G1 list below | The revised loader prototype passes every assertion (§1.4). The golden digests are `sha256:1bb3d9e6…75d3` (full) and `sha256:2ad268e1…bee8` (slice); since ruling 19 also `sha256:e17e08f4…aadd` and `sha256:fb12d840…2867` (not complete, and its slice) |
| **G2** each malformed case rejected | `tests/gate/test_malformed.py` | Each of the 180 cases in `malformed-cases.json` passes the rule of §8.2. The harness self-checks run. Code coverage and engine containment hold (§8.1) | All 180 pass in the validator prototype under jsonschema 4.26.0. fastjsonschema 2.22.2's codes are contained in jsonschema's for all 180. No unpatched base has an error finding. Every active code of layers J–I is listed, except D019, which S-PUT-006 covers |
| **G3** smoke: queue, structural lint, store, export | `tests/gate/test_smoke.py` | See the G3 list below | Prototype replay reproduces `sha256:518db0f4…7f29` from `smoke-base.c1.json`. The queue passes the Q layer, and both exports are valid |

**G1 asserts** the following for `fixture.c1.json` and for its directed slice. Since ruling 19 (§14) it asserts them
also for the fixture as a container that is not complete, and for that container's directed slice: the fixture without
`ex:KingOfFrance`, `ex:TP53`, `ex:YYZ` and `f:born-louis14-paris`, which its facts name, and without `complete`
(`tests/gate/g1_chain.py`).

1. The chain runs `to_hif(c, schema)` → `load_xgi` → `export_xgi` → `load_hnx` → `export_hnx` →
   `from_hif(h, schema)`. The first HIF is valid against the vendored schema and the profile, under both engines.
2. The canonical serialisation of every intermediate HIF equals the first HIF's. This covers metadata,
   `network-type`, node, edge and incidence records, weights, extensions and order.
3. `compare_containers(original, final) == []`, headers included.
4. Both export reports are empty: no stale, unlabelled, moved or dropped records.
5. The library objects are right.
   - XGI member sets, and the tail and head sets of a `DiHypergraph`, equal the HIF memberships.
   - In the slice, `ex:TP53` is in both `"in"` and `"out"` of `f:reg-1`.
   - In every HyperNetX cell, the `role` property equals the first record's role, and `khg-extra-incidences`
     holds the rest.
6. Two native edits are reflected: a HyperNetX `rename`, and an XGI membership removal (which raises) followed by
   its re-addition (an identical export).
7. Five child processes run the chain, with `PYTHONHASHSEED` 0–3 and with it unset. Each prints the digests of
   every intermediate document. All five agree, and they equal `tests/gate/golden-sha256.json`.

**G3 asserts** this sequence.

1. `MemoryStore.load(smoke-base)`.
2. `Queue.create(base=smoke-base)`, then `make_candidate`, then `Queue.submit`.
3. `Linter.lint`, which runs the structural rule set.
4. `Queue.accept(qid, store=…, id="f:king-14", actor="curator:smoke", reason=…)`.
5. `export` as khg-json and as HIF. Both are valid.
6. `validate_queue` finds no error.
7. `replay(path, schema=…, factory=store.memory_factory, base=smoke-base)` reproduces `decision_hash`.

### 1.3 Consumer call sequences (acceptance tests)

The sequences below are written against the API of §10.2. `tests/consumers/test_<project>.py` copies them
verbatim and runs them on `MemoryStore` with packaged data [DC §1.4] (graft [J-cons], [J-std]). They are also the
v1 scope filter (§12): a v1 name that no sequence, no gate clause and no consumer row of §12.1 uses is a scope error.

```python
from khg_contracts import hif, identity, loaders, queue, record, schema as sch, store, validate
from khg_contracts.scorers import completion, extraction, memory, retrieval, stability
S = sch.load_schema("p2-gate.relation-schema.json")        # Schema; raises ValidationError (M codes)

# P1: five backends, one conformance suite, timed reads
backend = store.Timed(MyPostgresStore(S))                  # MyPostgresStore implements store.Store
backend.load(record.iter_jsonl("corpus.khg.jsonl"), on_missing="skip")        # LoadReport{records, versions, skipped}
assert store.compare_containers(record.read_container("corpus.khg.jsonl"), backend.export("khg-json")) == []
backend.incident("ex:KingOfFrance", where=store.Where(as_of="+1700-01-01T00:00:00Z"))
backend.find("position_held", [{"role": "holder", "value": {"entity": "ex:LouisXIV"}}])
backend.find_by_key("position_held", [{"role": "position", "value": {"entity": "ex:KingOfFrance"}}])
backend.supersession_walk("f:born-skłodowska-kraków")
report = store.conformance.run(lambda schema, clock: MyPostgresStore(schema, clock=clock))   # EARL-shaped

# P3a: statements to C1, question sets as C4
r = record.normalize(p3a_statement_to_c1(stmt), S)         # canonical form and literal normalisation, no checks
if validate.validate_record(r, schema=S)["ok"]:
    records.append(r)
record.write_container({"header": header, "records": entities + records}, "slice.khg.jsonl", format="jsonl")
assert validate.validate_container("slice.khg.jsonl", schema=S)["ok"]
dedup = {record.content_key(r, S) for r in records}
leaks = {record.core_key(r, S) for r in test} & {record.core_key(r, S) for r in train}
bins = [record.arity(r, S)["arity"] for r in records]      # {arity, core_arity, statement_arity, distinct_fillers}
assert validate.validate_item("qset.c4.jsonl", schema=S)["ok"]   # I layer; I005 replays memory traces

# P3b: link prediction on a literal-free projection
queries = completion.build_queries(test, S, slots=("core", "qualifier"), literal_targets="exclude")
index = completion.FilterIndex.from_records(train, valid, test)
rows = [record.project.positional(f, S, literals="drop", widths={"agent": 4}) for f in train]
outputs = [completion.rank_stats(q, model.scores(q), index, target_prob=p, top1=t) for q, p, t in model_runs]
report = completion.score(queries, outputs, config=completion.CompletionConfig(preset="hype"))

# P5: draw a directed slice
h = hif.to_hif(container, S, relations=["regulates", "position_held"], literal_nodes="per_binding")
b = loaders.load_xgi(h)                                     # a DiHypergraph when every incidence has a direction
b.roles("f:reg-1", "ex:TP53")                               # ['regulator', 'target']

# P6: the schema as a hypergraph
hg = sch.schema_hypergraph(S, slots=("core", "qualifier"))
acyclic, residue = sch.is_alpha_acyclic(hg)

# P7: memory with belief revision
ms = store.MemoryStore(S)
ms.put(entities, actor="p7")
try:
    ms.put(new, actor="p7")
except store.KeyCollision as e:
    for coll in e.info["collisions"]:                       # §2.5: record, policy, conflicts[{id, shape, class, action}]
        for c in coll["conflicts"]:
            old = ms.get_many([c["id"]])[c["id"]]
            baseline = identity.relate(new, old, schema=S)  # P7 may replace this classifier
            if c["action"] == "close_older":
                ms.apply({"op": "end_validity", "target": c["id"], "end": start_literal(new),
                          "evidence": [inferred_close]}, actor="p7")
                ms.put(new, actor="p7")                    # §2.5 close_older: end the older fact, then the put
            elif c["action"] == "dispute":
                ms.apply({"op": "transition", "targets": [c["id"]], "to": "disputed", "records": [new],
                          "id": "m:dis-7", "reason": "key_conflict", "evidence": [ev]}, actor="p7")
current = ms.find_by_key("position_held", key, where=store.Where(as_of="+1700-01-01T00:00:00Z"))
walk = ms.supersession_walk("f:born-skłodowska-kraków")
prompt = [record.render_text(f, labels, schema=S) for f in current]
report = memory.score(questions, responses, traces=traces, schema=S)

# P9: extraction runs into queues, then scoring
q = queue.Queue.create("run-1.o1.khg-queue.jsonl", queue_id="run-1.o1", schema=S, base=entity_base)
cand = queue.make_candidate(fact, queue_id="run-1.o1", seq=1, schema=S)
qid = q.submit(cand, run={"run_id": "run-1", "order_id": "o1", "position": 1},
               doc={"doc_id": d, "doc_sha256": h}, submitted_by="p9-extractor/1.0.0")
queue.Linter(S, entities=entity_base).lint(q, qid)
items = list(queue.queue_items(paths))
extraction.score(gold, items, schema=S)
stability.score(items, schema=S, unit="run")                # a run is (run_id, order_id)

# P10: retrieval over the store, scored with cost
for qn in questions:
    w = store.Where(as_of=qn["where"]["as_of"], valid_mode=qn["where"]["valid_mode"], rank=frozenset(qn["where"]["rank"]))
    facts = [f for a in qn["anchors"] for f in ms.incident(a, where=w)]
    degrees = {a: ms.degree(a, where=w) for a in qn["anchors"]}
    context = [record.render_text(f, labels, schema=S) for f in facts]
retrieval.score(questions, responses, facts=ms.get_many(fact_ids))
```

### 1.4 What was validated, and how

`research/designs/work-synthesis/regenerate.sh <dir>` rebuilds every example and then runs the two validation
modes. The validation is offline: `validate_examples.py` blocks sockets before it imports anything, and so do the
library runners. Two regenerations give identical files, and `design-examples/` equals a fresh regeneration.
- The **schema** mode runs in `venv-hif` with jsonschema 4.26.0 and fastjsonschema 2.22.2.
- The **libs** mode runs in `venv-libs` with xgi 0.10.2, hypernetx 2.4.3 and pandas 2.3.3.

Every check passes. It found:

- **Well-formedness.** All 147 `.json` and 4 `.jsonl` files parse under the strict layer-J rules.
- **HIF against the vendored schema.**
  - The vendored `hif_schema_v0.1.0.json` hashes to `639466b7…2196` (blob e2105bb).
  - Eight HIF files are valid against it under both engines, with closed resolvers: the fixture, its slice, the
    migrated sample and the five role-convention files.
  - A `$ref` to anything that is not packaged fails closed.
- **The draft-07 schemas.** Under both engines:
  - `khg-hif-1.0.0` (the profile, `allOf` the vendored `$id`) accepts the three khg files.
  - `khg-record-1.0.0` accepts six C1 containers and the JSONL lines.
  - `khg-c4-items-0.1.0` accepts `c4-items.jsonl`, whose `tag:` refs point into khg-record.
  - `khg-c5-io-1.0.0` accepts `c5-outputs.jsonl`.
- **The layered validator prototype** finds no error on 20 bases. The fixture's only findings are the two
  designed warnings: S024 (`must_differ` on `f:loop-yyz`) and L008 (the same-day handover of `f:king-13` and
  `f:king-14`).
- **Round trips and variants.**
  - C1 → HIF is deterministic and equals the file; HIF → C1 equals the fixture.
  - The slice decodes with `khg-complete: false`.
  - Per-binding literal nodes and an inlined schema both round-trip. `from_hif` without a schema raises D009.
  - A slice of `claims` alone keeps its external reference.
- **Recomputation.**
  - The derived vectors, the item keys and the stored event hashes equal recomputation.
  - RFC 8785 holds on all 24 finite Appendix B vectors. `max 10` and `max 10.0` give one digest.
  - The precision windows match the Wikidata rules.
  - Julian 1582-10-05 and Gregorian 1582-10-15 have one identity. Year 0, a pre-1583 date without calendar and a
    partial `as_of` are refused.
- **Derived views.** `render_text` has exact output. `project.positional` pads with `khg:none` and refuses an
  unbounded usage. The RDF relation-instance and incidence-row projections round-trip every binding.
- **Schema hypergraphs.** The fixture schema is α-acyclic; the cyclic and Wikidata-shaped schemas are not (GYO).
- **Queue and replay.** Accepting the smoke item writes the fixture's `f:king-14`. Replay from the base
  reproduces the decision hash.
- **Registry and G2.** The registry is consistent, and the full G2 rule holds on all 180 cases (§8.2).
- **Scenarios.**
  - All 114 scenarios pass on the prototype store.
  - With any single flag removed, the results are only passed or inapplicable. The same holds for a TypeDB-like
    set (70 of 114 apply) and for no flags (12 apply).
- **Migration and C5 hand-checks.**
  - The v0 sample migrates to the committed goldens.
  - Memory gold matches the hand-checked values of §9.
  - The calibration values are 13/100, 1/4 against 2/5, and 1/4 and 19/100.
  - `binding_coverage@k` is 2/3 and 1, and the bootstrap is reproducible.
- **Libraries.**
  - The G1 chain holds on both files, including the library-object checks and both native edits.
  - Five role-convention files round-trip through both loaders in source order.
  - The hash-seed children agree with the golden file.
  - The native-operation table behaves as §5 states (20 of 20).
  - R03's cases give 22 of 28 exact; the other 6 are refused by design.

The prototypes are research code, not the package (see Prototype reuse).

## 2. C1 record format (`khg-record/1.0.0`)

### 2.1 Container, canonical JSON and names

A `.khg.json` file is `{"header": {...}, "records": [...]}`. A `.khg.jsonl` file has the header on line 1, then
one record per line, so it streams [R01 PF-28].

**Canonical order.** Embedded `relation-schema` documents come first, then entities by id, then hyperedges by id,
and by version in history files.

**Canonical JSON** is used for hashes, for `.khg.jsonl` and for the gate's digests:
- object keys sorted by code point, no white space, UTF-8 and NFC strings;
- numbers as RFC 8785 serialises them (ECMAScript `Number::toString`). So integral doubles have no fraction
  (`2.0` is `2`), and exponents take the ECMAScript form (`1e-7`, `1e+21`).

Identity payloads never contain a non-integer number, because literal amounts are decimal strings. Comparison is
structural (F10).

| Header field | Req. | Meaning |
|---|---|---|
| `kind`, `format` | yes | `"header"`, `"khg-record/1.0.0"` (V001, §11) |
| `document_id` | yes | an id |
| `schema` | yes | `{id, version, sha256}`, where `sha256 = digest("khg-schema/1", schema document)` (D009) |
| `content` | yes | `snapshot`, or `history` (every version of every id) |
| `as_at` | no | the transaction time of a snapshot, or the upper bound of a history container (D018) |
| `complete` | no | `true` means every entity and every fact that a record references is present (D002) |
| `created_at`, `generator`, `extensions` | no | never compared; `extensions` holds namespaced keys such as `hif:metadata` |

**Vocabulary ids are not references** (critique FIXTURE-VOCAB-REFS). These are:
- a literal's `unit` and `globe`;
- the entries of `rank_reason`;
- a schema's `units` lists.

They are never checked by D002, never become HIF nodes, and are never returned by `incident()` (S-READ-019). The
fixture uses `wd:Q11573`, `wd:Q2` and `wd:Q41755623` this way, and it is `complete: true`.

**Names.**
- **Ids** match `^(?!_:)[^\s\x00-\x1f\x7f]{1,512}$` in NFC (C011, P003, S020).
- The prefixes `ex:`, `f:`, `g:` and `m:` are conventions only.
- Three namespaces are reserved: `_:` (derived HIF nodes), `khg:` (built-in relations and roles, M008) and
  `cand:` (queue payloads).
- A `bid` matches `^b[1-9][0-9]*$`. It is unique in its hyperedge (S025), stable across versions, and never
  hashed. An evidence id matches `^e[1-9][0-9]*$`.
- Timestamps are RFC 3339 UTC (`recorded_at`, `as_at`, queue times).
- **Instants** (`Where.as_of`, the `as_of` of C4 items) are written `[+-]YYYY-MM-DDThh:mm:ssZ`. They lie on the
  proleptic Gregorian line with astronomical years (`+0000` is 1 BCE). They carry no precision and no calendar;
  anything else is C011.
- Hashes are `sha256:` followed by 64 lower-case hex digits.

### 2.2 Records

| Entity field | Req. | Meaning |
|---|---|---|
| `kind`, `id` | yes | `"entity"` |
| `types` | yes | entity types from the schema (fillers accept subtypes) |
| `label`, `aliases` | no | may change between versions |
| `redirect_to` | no | the entity this one was merged into; set once and never changed (§2.9). A value naming it is D020 in v1; rewriting comes in 1.2 |
| `version`, `recorded_at`, `recorded_by` | store | transaction time (§2.6) |
| `extensions` | no | passthrough; `hif:weight` becomes the HIF node weight |

| Hyperedge field | Req. | Meaning |
|---|---|---|
| `kind`, `id` | yes | `"hyperedge"`; `id` is opaque and stable (F6) |
| `relation` | yes | declared in the schema (S001), or a built-in `khg:` lifecycle relation |
| `status` | yes | §2.7 |
| `status_ref` | exactly when the status is `disputed`, `superseded` or `retracted` (C006) | the lifecycle record (§2.7) |
| `bindings` | yes, at least one (S007) | §2.3 |
| `evidence` | asserted facts need supporting evidence (S011) | append-only (§2.8) |
| `rank`, `rank_reason` | default `normal`; a reason list is required with `deprecated` (C008) | `preferred`, `normal` or `deprecated`; `rank_reason` is a list of vocabulary ids. Import writes `["unspecified"]` when the source gives no reason |
| `visibility` | default `visible` | `visible`, `suppressed` |
| `confidence` | no | `{value, scale, scorer?}`: belief, never identity |
| `goal` | status `goal` only (C012) | `{brief, owner?}`; may change while the status is `goal` |
| `reason`, `note` | lifecycle records only; `reason` required there (C012) | `reason` from the relation's list (S026) |
| `source_text` | no | a verbatim source sentence. Renderings are never stored; `render_text` computes them (§2.10) |
| `typed_under` | no | `"<schema id>/<version>"` |
| `version`, `recorded_at`, `recorded_by` | store | transaction time (§2.6) |
| `derived` | no | a cache of §2.4–§2.6 and §2.9. Canonicalisation drops it; when present it must match recomputation (D015) |
| `extensions` | no | namespaced passthrough; `hif:weight` becomes the HIF edge weight |

### 2.3 Bindings, values, literals and the precision windows

A binding is `{bid, role, value, position?, direction?, extensions?}`.
- `position` is an integer ≥ 1. It is required on ordered roles, forbidden elsewhere, and contiguous (S015).
- `direction` (`head` or `tail`) is allowed only where the usage declares none (S016). The effective direction
  is the binding's, else the usage's.
- `extensions` is passthrough. It maps to the incidence's `attrs["khg-extensions"]`, and its `hif:weight` to the
  incidence weight (§4.2).

A value has exactly one key (C001):

| Value | Form |
|---|---|
| entity | `{"entity": id}` |
| literal | `{"literal": {"datatype": ..., ...}}` (inline, typed) |
| fact | `{"fact": id}`: nesting, acyclic (D008) |
| special | `{"special": "somevalue" \| "novalue"}` (the Wikibase snak types [R04 M2]) |
| unbound | `{"unbound": {"var", "expect"?: {"entity_types"?, "datatype"?}}}`: goals only (C005); a variable is used once (S019) |

| `datatype` | Fields (decimals are strings) | Refinement v′ ⊑ v |
|---|---|---|
| `time` | `time` in Wikibase form `±YYYY-MM-DDThh:mm:ssZ` (historical year numbering), `precision` 0–14, `calendar` `gregorian` or `julian`. Components below the precision are zero, year 0 does not exist, and a date whose written year is before 1583 must state its calendar (S006) | v′'s window lies inside v's and v′'s precision is at least v's, whatever the calendars |
| `quantity` | `amount`, `unit` (`"1"` or a vocabulary id), and `lower` and `upper` as a pair (C004); the bounds take part in equality | same unit; narrower bounds inside v's |
| `string`, `iri`, `lang_string` | `value` (NFC), plus `lang` (BCP 47, lower case) for `lang_string` | equality |
| `boolean` | `value` | equality |
| `geo` | `lat`, `lon`, `precision`, `globe` (a vocabulary id) | same globe; finer precision, inside v's cell |

**Value identity** is what equality, hashing, keys and refinement compare (critique CONS-12, SEM-13). A time
literal's identity is `{datatype: "time", window: [lo, hi), precision}`, with the window on the proleptic
Gregorian line. Every other literal is its canonical form. The canonical form keeps the literal as written (the
Julian calendar stays Julian), so the written date is never lost. Julian `1582-10-05` and Gregorian `1582-10-15`
therefore have one identity, and keys, dedup and scoring treat them as one value.

**Precision windows** (normative; critique CONS-01). A time literal with written year y denotes the instants
[lo, hi). The window is computed in the literal's calendar and mapped to the proleptic Gregorian line through the
Julian day number. y is a historical year, and its astronomical year is a = y for y > 0 and a = y + 1 for y < 0.

| `precision` | Unit | Window |
|---|---|---|
| 14, 13, 12, 11 | second, minute, hour, day | that unit |
| 10 | month | that month |
| 9 | year | the calendar year y |
| 8 | decade | floor on a: [10⌊a/10⌋, 10⌊a/10⌋ + 10) |
| 7 | century | ordinal, as Wikidata reads it. For y > 0, c = ⌈y/100⌉ and the years are 100c − 99 … 100c. For y < 0 with n = −y BCE, c = ⌈n/100⌉ and the years are 100c BCE … 100c − 99 BCE |
| 6 | millennium | the same ordinal rule with 1000 |
| 5 … 0 | 10⁴ … 10⁹ years | floor on a, in blocks of 10^(9−p) years |

These windows were checked by the prototype (instants in the §2.1 grammar):

| Literal | Window |
|---|---|
| `+1900/7` | [+1801-01-01, +1901-01-01), the 19th century |
| `+1901/7` | [+1901-01-01, +2001-01-01) |
| `+2000/6` | [+1001-01-01, +2001-01-01) |
| `+1995/8` | [+1990-01-01, +2000-01-01) |
| `−0100/7` Julian | [−0100-12-30, +0000-12-30), the 1st century BCE |
| `−0044-03-15/11` Julian | [−0043-03-13, −0043-03-14) |
| `+1700/9` Julian | [+1700-01-11, +1701-01-12) |

`derived.valid_time` carries the computed instants (§2.6), so P1's backends index them instead of recomputing
them.

### 2.4 Slot classes, arity, special values, goals

| Slot | Holds | Arity | `content_key` | `core_key` | Key roles | P6 hypergraph | Valid time |
|---|---|---|---|---|---|---|---|
| `core` | the participants | yes | yes | yes | yes | yes | no |
| `qualifier` | refinements that change truth conditions (context, point in time, quantity, Wikidata P5102 and P1480) | yes | yes | no | yes | yes | no |
| `time` | the bounds named by the time model | no | yes | no | no (M003) | on request | yes |
| `meta` | bindings that never change truth conditions: surface forms, support and dispute pointers, `khg:end_cause` | no | no | no | no | no | no |

`meta` is only for bindings that do not change what the fact says (critique CONS-16). Epistemic modifiers such as
Wikidata's P5102 (nature of statement) and P1480 (sourcing circumstances) are qualifiers. So "born c. 1643
(presumably)" keeps a different `content_key` from the plain statement.

**Arity** follows B's rule (a ruling). It counts the core and qualifier bindings whose value is an entity, a
literal, a fact or `somevalue`, and a repeated filler counts once per binding. Reported beside it:
- `core_arity`;
- `statement_arity`: arity plus the time bindings that have a value;
- `distinct_fillers`: each `somevalue` counts as distinct.

Bins are `0-1`, `2`, `3`, `4` and `5+`. In the fixture:
- `f:king-14` has arity 3, core arity 2, statement arity 5 and 3 distinct fillers;
- `f:route-1` has arity 4 with 3 distinct fillers;
- `f:station-東京` has arity 9;
- `f:cat-7` has arity 1, since its `novalue` does not count.

A goal reports `n_bound` and `n_unbound` instead. The scorers also report `model_arity`, the bindings a
literal-free projection keeps (§9).

**`somevalue`** counts in arity and hashes as a token. In a key role it makes `key_digest` null, so the fact is
exempt from collisions. It refines to a value and keeps its bid (S-VER-007).

**`novalue`** excludes other fillers of its role (S013). As an end bound it means "still holds" (§2.6).

**Goals** have status `goal`, unbound slots and a `goal` block.
- Binding a slot is a new version with the same bid and `agent_bound` evidence; `bind` in 1.1 is sugar over it.
- `goal.brief` and `goal.owner` may change while the status is `goal`, so a goal can be handed to another agent
  (critique CONS-27).
- A transition asserts the goal once every slot is bound. It drops the `goal` block, which the earlier versions
  keep.
- `khg:fulfils` comes in 1.1.

**Nested claims** that are recorded but not asserted have status `quoted` (`f:born-louis14-paris`, referenced by
`f:claim-1`).

**Confidence** scales are `probability` or declared in the schema (S010). HIF `weight` is never read as
confidence.

### 2.5 Keys and the key invariant

A relation may declare `key: {roles, temporal, on_collision}`.
- The roles must be core or qualifier roles (M003).
- `temporal` needs an interval time model (M011).
- `on_collision` is one of `close_older`, `supersede`, `dispute` (the default) or `reject`. `supersede` on a
  temporal key is M017, because a succession is a world change, not a belief revision (F7).
- **Key literals compare by value identity** (§2.3). Precision takes part, so `2019/9` and `2019-06-30/11` are
  different keys (S-KEY-019); the calendar does not. Refinement never merges key groups. A lint for key literals
  that refine or overlap each other comes in 1.1 (L110).

**Invariant (D016).** Take the facts with status `asserted`, a rank other than `deprecated`, the same relation
and a non-null `key_digest`. At every instant of their *definite* windows (§2.6), or at every instant for a
non-temporal key, at most one of them holds, or exactly one of those holding is `preferred` (Wikidata's
single-best-value).

Undated, end-only and ended-at-an-unknown-time facts have no definite validity. So they never collide on a
temporal key (§2.6; critique SEM-08, CONS-11). A *possible-only* overlap is the warning L008. Store receipts and
`validate_container` report it; the fixture's same-day handover of `f:king-13` and `f:king-14` is one.

**The disputed-key rule** (critique SEM-09). A put that asserts a fact on a key with `disputed` facts raises
`KeyCollision`, with policy `dispute` and those facts as conflicts. For a temporal key this applies when the
windows definitely overlap. The caller joins the dispute with a `transition` to `disputed`. That transition names
the disputed facts and writes the newcomer, and a new `khg:disputes` record binds them all (S-KEY-017).

**`KeyCollision`** (D016) is raised by any write that breaks the invariant or the disputed-key rule. Nothing is
written. Its `info` lists every colliding record of the batch (critique CONS-13, SEM-04, SEM-05). This is the info
that scenario S-KEY-018 raises in the prototype store. The store holds `f:king-13` and `f:born-skłodowska-warszawa`,
and one `put` writes the Kraków birthplace as asserted, together with a copy of `f:king-14` (`f:king-14b`) that
starts on 1 January 1640:

```json
{"collisions": [
  {"record": "f:born-skłodowska-kraków", "relation": "born_in",
   "key_digest": "sha256:951a7bba11cca1f6c84ede16cd78c9502d08b7ab45060ff462b2ba4f0eea045c", "policy": "dispute",
   "conflicts": [{"id": "f:born-skłodowska-warszawa", "in_batch": false, "shape": null, "class": "distinct", "action": "dispute"}]},
  {"record": "f:king-14b", "relation": "position_held",
   "key_digest": "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96", "policy": "close_older",
   "conflicts": [{"id": "f:king-13", "in_batch": false, "shape": "overlap_after_end", "class": "distinct", "action": "dispute"}]}]}
```

- **`shape`** is null for non-temporal keys. For temporal keys, the fact whose start window lies wholly before the
  other's is the earlier one, and the shapes are:
  - `succession`: the earlier fact is the stored one, and it is still holding (its end is absent or `novalue`);
  - `backfill`: the earlier fact is the incoming one, and it is still holding;
  - `overlap_after_end`: the earlier fact has an end, and that end overlaps the later start;
  - `same_start`: neither start window lies before the other.
- **`class`** comes first, from refinement (§2.9): `duplicate` (equal `content_key`), `refines`, `generalises`
  or `distinct`.
- **`action`** is normative:

| Class | Policy | Shape | Action (what the caller does) |
|---|---|---|---|
| `duplicate`, `refines`, `generalises` | any | any | `merge`: write the incoming content as a new version of the stored fact (by bid), or append its evidence. The declared policy does not apply (R01 case 1; C3-R10) |
| `distinct` | `close_older` | `succession` | `close_older`: `end_validity` on the stored fact with `end` := the incoming start literal, then the put (S-KEY-007) |
| `distinct` | `close_older` | `backfill` | `close_incoming`: give the incoming fact `end` := the stored start literal, then put it (S-KEY-015) |
| `distinct` | `close_older` | `same_start`, `overlap_after_end` | `dispute` (S-KEY-014, S-KEY-001) |
| `distinct` | `dispute` | any | `dispute`: a `transition` to `disputed` that includes the new fact |
| `distinct` | `supersede` | (non-temporal keys only) | `supersede`: a `supersede` event with reason `correction` |
| `distinct` | `reject` | any | nothing is written |

A match with a `quoted` fact is not a collision, because quoted facts are not asserted. The 1.1 identity lint
(L007) proposes `quoted` → `asserted` with the candidate's evidence. The store checks invariants and **never
applies a policy** (ruling).

### 2.6 Time

**Valid time.** A relation's time model is one of:
- `{"model": "interval", "start": role, "end": role}`;
- `{"model": "invariant"}`: the fact holds whenever its participants exist;
- `{"model": "timeless"}`: time does not apply, as in a flight route or a catalyst.

The schema's `default_time` is `timeless` (critique SEM-15). Facts of `invariant` and `timeless` relations pass
every `as_of` filter, in both modes, and may carry only non-temporal keys (M011).

**The bound table** (normative; critique SEM-01, SEM-08). For an interval relation, the start binding and the end
binding each give a window:

| Start binding | Start window [s_lo, s_hi) | End binding | End window [e_lo, e_hi) |
|---|---|---|---|
| a literal | its precision window | a literal | its precision window |
| absent or `somevalue` | (−∞, e_hi): started at an unknown time before the end | absent or `novalue` | e_lo = e_hi = +∞: still holds |
| `novalue` | s_lo = s_hi = −∞: held since forever | `somevalue` | [s_lo, +∞): ended at an unknown time after the start |

- **Definite validity** is [s_hi, e_lo). **Possible validity** is [s_lo, e_hi).
- Two facts definitely overlap iff max(s_hi) < min(e_lo), and possibly overlap iff max(s_lo) < min(e_hi).
- An empty possible validity is S009.
- `derived.valid_time` is `{kind, start?, end?, definite: [lo, hi] | null, possible: [lo, hi]}`. It holds instants
  in the §2.1 grammar, with `null` for an unbounded side.
- The kinds are:
  - `period`: both bounds are literals;
  - `since`: the start is a literal and the end is absent or `novalue`;
  - `ended`: the start is a literal and the end is `somevalue`;
  - `until`: the end is a literal and the start is not;
  - `undated`: neither bound is a literal;
  - `invariant` and `timeless`: from the time model.

**What an `as_of` read returns** (critique CONS-04). An `as_of` read at t matches a fact of an interval
relation when s_hi ≤ t < e_lo (a `definite` read, the default) or when s_lo ≤ t < e_hi (a `possible` read), with
the windows of the bound table. Facts of `invariant` and `timeless` relations always match. A read without
`as_of` applies no valid-time filter. For the common cases:

| Fact | `definite` read at t | `possible` read at t |
|---|---|---|
| `period`, `since` | s_hi ≤ t < e_lo | s_lo ≤ t < e_hi |
| `ended` (end `somevalue`) | never | s_lo ≤ t |
| `until` with the start absent or `somevalue` | never | t < e_hi |
| `undated` with the start absent or `somevalue` | never | always |
| any kind with a `novalue` start | the start reads as −∞ (held since forever) | the same |
| `invariant`, `timeless` | always | always |

So a year-precision handover (end 1643, start 1643) is a succession, not a conflict (X1; S-KEY-009). A fact that
ended in the world keeps its status and gains an end binding (F7). `end_validity` may replace a `novalue` end,
which is the one non-refining change allowed (§2.9).

**Transaction time** (critique SEM-14). Every write makes an immutable version (F8; [R04 O6]): `version` 1, 2, …,
with `recorded_at` and `recorded_by`.
- `recorded_at` strictly increases **per store**. A write's time must be after the store's latest, and `at` can
  only pin it forward (D018). One call writes all its records at one time.
- In a history container, each id's versions increase and none is after the header's `as_at` (D018).
- A read at `as_at` sees each id's latest version with `recorded_at` ≤ `as_at`.

| Wikidata | C1 |
|---|---|
| P580, P582 | the time bindings of an interval model. P582 is an inclusive window: `+2021/9` ends inside 2021 |
| P585 | a qualifier, unless the time model names it |
| P1319, P1326, P8554, P8555, P12506 | qualifiers (validity bounds come in 1.1) |
| P5102 (nature of statement), P1480 (sourcing circumstances) | qualifiers (content, §2.4) |
| P1534 (end cause) | `khg:end_cause`, written by `end_validity` (§2.7) |
| `somevalue`, `novalue` | `special`, read as bounds by the bound table |
| calendarmodel Q1985727, Q1985786 | `calendar` `gregorian`, `julian` |
| rank; P2241 (reason for deprecated rank), P7452 (reason for preferred rank) | `rank`; `rank_reason` (a list) |
| references (P248, P854, P813, …) | evidence (§2.8): `source.doc_id` is the P248 item, else the P854 URL, else the dump id; every snak goes into `reference` |

### 2.7 Lifecycle (F7, F8)

There are four axes:
- **belief:** `status`, one of `candidate` (queue only, D017), `asserted`, `disputed`, `superseded`,
  `retracted`, `quoted` or `goal`;
- **world:** valid time;
- **editorial:** `rank`;
- **display:** `visibility`.

| From | To | How | Lifecycle record |
|---|---|---|---|
| new id | `asserted`, `quoted`, `goal` | `put` | none |
| new id, in the `records` of a `supersede` event | `asserted` | `supersede` | bound as superseding in the `khg:supersedes` record |
| new id, in the `records` of a dispute | `disputed` | `transition` | the new `khg:disputes` record |
| `asserted`, `disputed` | `superseded` | `supersede` event | `khg:supersedes` |
| `asserted`, `disputed` | `disputed` | `transition` over at least two facts, new or existing | a new `khg:disputes` |
| `asserted`, `disputed`, `goal`, `quoted` | `retracted` | `transition` | `khg:retracts` |
| `disputed`, `quoted` | `asserted` | `transition`, re-checking the key | none |
| `goal` | `asserted` | `transition` once every slot is bound (C005); drops `goal` | none |
| `superseded`, `disputed` | `asserted` | undo: a `transition` retracting the lifecycle record, re-checking the key | `khg:retracts` on that record |

- **Records carried by events** arrive with status `asserted` and no `status_ref`. The store sets both (critique
  SEM-10).
- **A fact leaving** `disputed`, `superseded` or `retracted` drops its `status_ref` (S-KEY-010, S-LIFE-007).
- **Undo of a keyed `correction`** must say what happens to the superseding facts (critique SEM-19). The event
  sets `resolve_superseding` to `retract` or to `dispute` (the latter with a `dispute_id`), and all of it is one
  atomic event (S-LIFE-013). Without it the restored fact collides (D016).
- **Anything else is D014:** a status change through `put`, a `put` of a lifecycle record, a `put` that creates
  a record in status `disputed`, `superseded` or `retracted`, or an event outside the table.
- **Terminal:** `retracted` is terminal, and `khg:retracts` records cannot themselves be retracted.

| Built-in relation (kind `lifecycle`) | Roles | `reason` | Constraints |
|---|---|---|---|
| `khg:supersedes` | `khg:superseding` (tail, 1..n), `khg:superseded` (head, 1..n) | `correction`, `duplicate`, `refinement`, `conflation`, `schema_migration`, `other` | `correction` keeps the relation and the key digest; `duplicate` needs equal `content_key`; `refinement` needs the superseding fact to refine the superseded one (D011); acyclic (D012) |
| `khg:retracts` | `khg:retracted` (head, 1..n) | `withdrawn`, `unsupported`, `other` | |
| `khg:disputes` | `khg:disputed` (head, 2..n) | `key_conflict`, `negation_conflict`, `curator`, `other` | |

**Where D011 is checked** (critique SEM-11). There are three places:
- **The `supersede` event.** Its superseding facts must be asserted when the event runs (S-LIFE-004). Events
  therefore cannot form a cycle.
- **A `put`** of a new version of a fact bound by an asserted `khg:supersedes` record. The version must keep that
  record's constraint (S-LIFE-014). For example, a refined key literal may not move a `correction` onto another
  key.
- **Containers.** The reason constraints are checked against the current versions of a snapshot.

"Superseding facts asserted" is therefore an event precondition, not a container invariant. A chain A → B → C is
valid, with A and B superseded, and retracting a superseding fact leaves a valid export.

**Pointer rule (D010).**
- A fact that is disputed, superseded or retracted names, in `status_ref`, an asserted lifecycle record of the
  matching relation, which binds it in the matching role.
- Every fact that an asserted `khg:supersedes` record binds as superseded, or that an asserted `khg:retracts`
  record binds, has that status.
- A `khg:disputes` record may outlive its dispute.

The records are the source of truth; the validator checks that the pointers agree with them. Lifecycle records are
excluded from default reads, from arity and from keys.

**`end_validity` and the end cause** (critique SEM-06). `end_validity` records a world change:
- it adds or refines the end binding, or replaces a `novalue` end;
- the status is unchanged;
- an optional `end_cause` (an entity or a string literal) becomes a `khg:end_cause` binding. That meta-slot usage
  is built into every interval relation and maps to Wikidata P1534.

### 2.8 Evidence (F11)

| Field | Req. | Meaning |
|---|---|---|
| `id` | yes | `e1`, `e2`, …; never rewritten (D013) |
| `type`, `mode` | yes | `curated`, `imported`, `extracted`, `inferred` or `agent_bound` [R04 O7]; `manual`, `automatic` or `semi_automatic` |
| `source` | yes | `{doc_id, doc_sha256?, url?, retrieved_at?, version?, licence?}`. For Wikidata imports, `doc_id` is the P248 item, else the P854 URL, else the dump id (critique CONS-17) |
| `selectors` | extracted | `{type: "quote", exact, prefix, suffix}` and `{type: "position", start, end}`: code points, half-open, over the NFC text that `doc_sha256` hashes (S021) |
| `activity` | extracted | `{agent, agent_version, model?, model_version?, prompt_id?, skill_id?, run_id?}` |
| `inference` | inferred | `{rule, from}`. `from` lists fact ids and may be empty only when `rule` is `"model"` and `activity` names `model` and `model_version`; this is the pattern for completer output (critique CONS-29) |
| `supports` | no | the bids supported (S022). §2.8.1 gives the defaults and the resolution rule |
| `confidence`, `epistemics`, `reference` | no | the extractor's score; `{negated?, hypothesis?}`; source reference snaks `[{role, value}]` |
| `recorded_at` | store | when the evidence was appended |
| `event_hash` | extracted and inferred evidence | stored once, at extraction (§2.9); immutable (D013) |

`extracted` evidence needs `doc_sha256`, `activity` and `selectors` (C007). The quote in `f:route-1` follows
U+20BB7, a character outside the Basic Multilingual Plane, so its position 29–57 counts code points; UTF-16 would
give 30–58.

#### 2.8.1 What evidence supports

An evidence record supports the values that its listed bids held **in the first version that carries it**
(critique SEM-21, CONS-19). Readers resolve this through history, so a later refinement of a bound value is never
attributed to earlier evidence (`supported_values` in the prototype). When `supports` is omitted, the canonical
form writes:

| Written by | Default `supports` |
|---|---|
| `put` or an event's `records` | every bid at write time |
| `end_validity` | the end binding, plus the `khg:end_cause` binding if one is written |
| `transition` without a record | `[]`, because the evidence concerns the status change |

### 2.9 Identifiers (F6), hashing, refinement and versions

`digest(domain, payload) = "sha256:" + hex(SHA-256(UTF-8(domain + "\n" + canonical_json(payload))))`

| Id | Definition | Used for |
|---|---|---|
| `id` | opaque, chosen by the writer | references, versions |
| `content_key` | `khg-content-key/1` over `{relation, bindings}`: the core, qualifier and time bindings as `[role, position, value identity]`, sorted | dedup (P3a), stability (P9) |
| `core_key` | the same over the core bindings (`khg-core-key/1`) | leak check, verdict key |
| `key_digest` | `khg-key-digest/1` over `{relation, key bindings}`. It is `null` without a key, when a key role is absent, or when a key role holds a special or unbound value | key index, collisions |
| `event_hash` | `khg-event/1` over `{content_key, doc (doc_sha256, else doc_id), selectors (sorted), activity {agent, agent_version, model, model_version, prompt_id, skill_id}, reference? (sorted), inference?}` | verdicts; the 1.1 lint L009 |

`event_hash` (critique SEM-12, CONS-17):
- It is computed **once, at extraction**, by `make_candidate`. Its input is the candidate payload's
  `content_key`.
- It is stored in the evidence record and never recomputed against the host record. So a later refinement or
  merge does not change it, and D015 does not cover it.
- Only `extracted` and `inferred` evidence has one.
- The `reference` snaks are hashed. So two references of one statement have different event hashes even when
  they share a `doc_id`.
- `Q010` checks it in queue items.

The other domains are `khg-literal-node/1`, `khg-literal-binding/1`, `khg-special-node/1`, `khg-schema/1`,
`khg-decision/1` and `khg-timed/1`.
- Bids, evidence, derived fields, rank, visibility, confidence and text never enter the three keys.
- Time bindings are content. So one couple married over two disjoint periods gives two facts: R01 case 2c, the
  fatal flaw that [J-cons] and [J-std] found in A.
- In the fixture, `f:king-14` has `content_key` `sha256:2706f2b5…d76b`, `core_key` `sha256:5779b98f…e916` and
  `key_digest` `sha256:19b896a4…4a96`. `fixture.with-derived.c1.json` has every value.

**Refinement.**
- For values, v′ ⊑ v holds when their identities are equal, when v is `somevalue` or `unbound` and v′ is an
  entity, literal or fact, or by §2.3. `novalue` refines only `novalue`.
- For facts, f′ ⊑ f holds when both have the same relation and every core, qualifier and time binding of f has a
  refining binding in f′. The binding must have the same role, and the same position for an ordered role, and the
  matching is injective. **Meta bindings are ignored** (critique SEM-20). `complete` roles keep their size.
- Mutual refinement means equal `content_key`, that is, a duplicate.
- `identity.relate(a, b, *, schema)` (non-normative, for P7) returns one of the seven labels of [DB §2.19]:
  `duplicate`, `refines`, `generalises`, `distinct`, `key_conflict`, `key_timeline` or `negation_conflict`. Its
  tests are DB's 37 rows. Under the §2.6 ruling, X3 and C4a-u become `key_timeline`.

**Version rule (D013; ruling).** A new version of a hyperedge must:
- keep the relation;
- keep every binding **by bid**, with the same role and position and a refining value. The only non-refining
  change is `end_validity` replacing a `novalue` end;
- add bindings only where the role is not `complete`;
- keep every earlier evidence record unchanged, `event_hash` included, and may append new ones;
- change only `rank`, `rank_reason`, `visibility`, `confidence`, `source_text` and `extensions` among the other
  fields, plus `goal` while the status is `goal`.

`superseded` and `retracted` facts are frozen.

**Entity versions** (critique CONS-28, S-VER-008):
- `label`, `aliases` and `extensions` may change;
- `types` may only grow;
- `redirect_to` may be set once and never changed.

**Status changes only through events (D014)** (critique SEM-06). Anything else is a new id:
- if the old fact was wrong, `supersede` it (belief revision);
- if it stopped holding, apply `end_validity` to it and put the new fact, with no lifecycle record (F7).

Adding a filler to an already-bound repeated core role of a dated fact means "we learned more". A member who
joined later is `end_validity` plus a new fact, and the 1.1 lint L104 flags such versions. Bids make the check
linear, so [DA]'s S031 floor is not needed.

**Erasing one participant** (R01 case 4c) is unclassified in v1. Its representation, a `{"special": "withheld"}`
value, comes in 1.1 (§12; critique SEM-17).

### 2.10 Derived views (versioned; critique CONS-08, PROJECTIONS, CONS-20)

These are functions of `khg_contracts.record`. Their output formats are part of the contract.

- **`render_text(record, labels, *, schema) -> str`**, format `khg-render/1`. It writes the relation's label,
  then `role: value` groups in parentheses, separated by `; `.
  - Core usages come first, then qualifier usages, each in the relation's usage order. The fillers of one role
    are in canonical binding order, joined by `, `.
  - Values render as follows: an entity as its label (else its id); a literal as its §4.2 label; `somevalue` as
    `some value`; `novalue` as `no value`; `unbound` as `?var`; a nested fact as `[<fact id>]`.
  - Interval relations add ` [start, end)`, with `…` for an absent bound.
  - Meta bindings are omitted.
  - Reports of P7 and P10 stamp `khg-render/1`.
  - Example: `render_text(f:king-14)` is `position_held(holder: Louis XIV; position: King of France; replaces:
    Louis XIII) [+1643-05-14T00:00:00Z/11, +1715-09-01T00:00:00Z/11)`.
- **`project.position_map(schema, relation, *, slots=("core", "qualifier"), literals="node", widths=None)`** and
  **`project.positional(record, schema, *, slots=..., literals="node" | "drop", widths=None) -> tuple`**.
  - The positions are the relation's usages in schema order. A usage with `max` k gives k positions. An unbounded
    usage needs `widths[role]` or raises `ValueError`.
  - Ordered roles fill their positions by `position`; unordered roles fill them in canonical value order. An
    absent optional position is the reserved id `khg:none`.
  - Specials become their `_:sv:` or `_:nv:` ids, and literals their `_:lit:` ids. With `literals="drop"`, usages
    that admit only literals are left out.
  - Lifecycle and goal records are refused.
  - Example: `positional(f:route-1, widths={"stop": 4})` is `("flight_route", "ex:AirCanada", "ex:YYZ", "ex:YUL",
    "ex:YYZ", "khg:none")`.
- **`project.hyper_relational(record, schema) -> dict`** gives `{subject, relation, object, qualifiers}`. The
  subject and object come from the relation's `primary`, and a relation without one raises `ValueError`. Every
  other core, qualifier and time binding becomes a `[role, value id]` qualifier pair, sorted.
- **`project.role_value_set(record, schema, *, slots=...) -> list`** gives the sorted multiset of `[role, value
  id]`.
- **`project.rdf_relation_instance(container) -> list[triple]`** and its inverse. There is one IRI per fact,
  `urn:khg:<id>`, and one per binding, `urn:khg:<id>#<bid>`, with the predicates `khg:relation`, `khg:status`,
  `khg:binding`, `khg:bid`, `khg:role`, `khg:position`, `khg:direction` and `khg:value` (entities and facts) or
  `khg:valueJSON` (other values, as canonical JSON). Ids are percent-encoded outside RFC 3987 `iunreserved` (UTF-8
  octets), so `ex:Łódź` is `urn:khg:ex%3AŁódź`, and the mapping is reversible. The namespace is
  `https://w3id.org/khg/ns#`.
- **`project.incidence_rows(container) -> list[tuple]`** and its inverse give one row per binding:
  `(fact_id, version, relation, status, bid, role, position, direction, value_kind, value)`.
- Both projections round-trip every binding of the fixture: 329 triples and 59 rows. Binding `extensions` and
  evidence are not projected. P1's property-graph and TypeQL mappings are P1's own; §6.5 is informative.

### 2.11 The gate fixture as C1

`design-examples/fixture.c1.json` holds 22 entities and 18 hyperedges in canonical order, without derived fields.
§8.3 maps it to R01 D-20.

```json
{
 "header": {"kind": "header", "format": "khg-record/1.0.0", "document_id": "p2-gate-fixture", "schema": {"id": "p2-gate", "version": "1.0.0", "sha256": "sha256:cadd01cd3d37e09337d2fe70bd5572a32dff4a7d6f4a0ac26845c6c27d0e194d"}, "content": "snapshot", "complete": true, "extensions": {"hif:metadata": {"title": "P2 gate fixture (adversarial)"}}},
 "records": [
  {"kind": "entity", "id": "ex:AirCanada", "types": ["Airline"], "label": "Air Canada"},
  {"kind": "entity", "id": "ex:Chronicler_Ødegård", "types": ["Person"], "label": "Ødegård the chronicler"},
  {"kind": "entity", "id": "ex:HeLa", "types": ["CellLine"], "label": "HeLa"},
  {"kind": "entity", "id": "ex:KingOfFrance", "types": ["Position"], "label": "King of France"},
  {"kind": "entity", "id": "ex:Kraków", "types": ["Place"], "label": "Kraków"},
  {"kind": "entity", "id": "ex:LouisXIII", "types": ["Person"], "label": "Louis XIII"},
  {"kind": "entity", "id": "ex:LouisXIV", "types": ["Person"], "label": "Louis XIV"},
  {"kind": "entity", "id": "ex:Maria_Skłodowska", "types": ["Person"], "label": "Maria Skłodowska"},
  {"kind": "entity", "id": "ex:Mazarin", "types": ["Person"], "label": "Jules Mazarin"},
  {"kind": "entity", "id": "ex:Paris", "types": ["Place"], "label": "Paris"},
  {"kind": "entity", "id": "ex:Pierre_Curie", "types": ["Person"], "label": "Pierre Curie"},
  {"kind": "entity", "id": "ex:R-hydrolysis-7", "types": ["Reaction"], "label": "hydrolysis reaction 7"},
  {"kind": "entity", "id": "ex:TP53", "types": ["Gene"], "label": "TP53", "extensions": {"hif:weight": 3}},
  {"kind": "entity", "id": "ex:Warszawa", "types": ["Place"], "label": "Warszawa"},
  {"kind": "entity", "id": "ex:YUL", "types": ["Airport"], "label": "Montréal–Trudeau"},
  {"kind": "entity", "id": "ex:YYZ", "types": ["Airport"], "label": "Toronto Pearson"},
  {"kind": "entity", "id": "ex:anonymous_scribe", "types": ["Person"], "label": "an anonymous scribe"},
  {"kind": "entity", "id": "ex:hypoglycaemia", "types": ["Outcome"], "label": "hypoglycaemia"},
  {"kind": "entity", "id": "ex:insulin", "types": ["Drug"], "label": "insulin"},
  {"kind": "entity", "id": "ex:metformin", "types": ["Drug"], "label": "metformin"},
  {"kind": "entity", "id": "ex:Łódź", "types": ["Place"], "label": "Łódź"},
  {"kind": "entity", "id": "ex:東京駅", "types": ["Station"], "label": "Tokyo Station"},
  {"kind": "hyperedge", "id": "f:born-louis14-paris", "relation": "born_in", "status": "quoted", "bindings": [{"bid": "b2", "role": "birthplace", "value": {"entity": "ex:Paris"}}, {"bid": "b1", "role": "person", "value": {"entity": "ex:LouisXIV"}}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:born-scribe", "relation": "born_in", "status": "asserted", "bindings": [{"bid": "b2", "role": "birthplace", "value": {"special": "somevalue"}}, {"bid": "b1", "role": "person", "value": {"entity": "ex:anonymous_scribe"}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:scriptorium-notes"}, "supports": ["b1", "b2"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:born-skłodowska-kraków", "relation": "born_in", "status": "superseded", "bindings": [{"bid": "b2", "role": "birthplace", "value": {"entity": "ex:Kraków"}}, {"bid": "b1", "role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}], "status_ref": "m:sup-1", "evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:curie-wrong", "doc_sha256": "sha256:685ed4266cfa7fb0429dee59b9feaa3cefde8894ac6556dce24e1894504a7a0d"}, "selectors": [{"type": "quote", "exact": "Maria Skłodowska was born in Kraków", "prefix": "", "suffix": "."}, {"type": "position", "start": 0, "end": 35}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "event_hash": "sha256:8b599a516787cb80778d875faf091249745d212631ad697a087299bce618a02f", "supports": ["b1", "b2"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:born-skłodowska-warszawa", "relation": "born_in", "status": "asserted", "bindings": [{"bid": "b2", "role": "birthplace", "value": {"entity": "ex:Warszawa"}}, {"bid": "b1", "role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}, "supports": ["b1", "b2"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:cat-7", "relation": "catalysed_by", "status": "asserted", "bindings": [{"bid": "b2", "role": "catalyst", "value": {"special": "novalue"}}, {"bid": "b1", "role": "reaction", "value": {"entity": "ex:R-hydrolysis-7"}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:lab-notebook-7"}, "supports": ["b1", "b2"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:claim-1", "relation": "claims", "status": "asserted", "bindings": [{"bid": "b2", "role": "claim", "value": {"fact": "f:born-louis14-paris"}}, {"bid": "b1", "role": "claimant", "value": {"entity": "ex:Chronicler_Ødegård"}}, {"bid": "b3", "role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+1700-00-00T00:00:00Z", "precision": 9, "calendar": "julian"}}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:chronicle-1700"}, "supports": ["b1", "b2", "b3"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:coadmin-1", "relation": "co_administration_causes", "status": "asserted", "bindings": [{"bid": "b1", "role": "agent", "value": {"entity": "ex:insulin"}, "extensions": {"hif:weight": 0.25}}, {"bid": "b2", "role": "agent", "value": {"entity": "ex:metformin"}}, {"bid": "b3", "role": "effect", "value": {"entity": "ex:hypoglycaemia"}}], "evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:coadmin-note", "doc_sha256": "sha256:242a3e2542b83f98e5adfa478e9d7ef5aa909708f7e184e88f51e5b09ff17368"}, "selectors": [{"type": "quote", "exact": "Metformin taken together with insulin can cause hypoglycaemia", "prefix": "", "suffix": "."}, {"type": "position", "start": 0, "end": 61}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "confidence": {"value": 7.5, "scale": "llm-0-10"}, "event_hash": "sha256:4ee38cb8eca2607e3f5f1a1411160729165f9bbbd5b4d8f5e274934ab5ab1b8a", "supports": ["b1", "b2", "b3"]}, {"id": "e2", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:insulin-label"}, "supports": ["b1", "b3"]}], "confidence": {"value": 0.9, "scale": "probability", "scorer": {"name": "fixture-belief", "version": "0"}}, "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:king-13", "relation": "position_held", "status": "asserted", "bindings": [{"bid": "b4", "role": "end_time", "value": {"literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}, {"bid": "b1", "role": "holder", "value": {"entity": "ex:LouisXIII"}}, {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}}, {"bid": "b3", "role": "start_time", "value": {"literal": {"datatype": "time", "time": "+1610-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:regnal-list"}, "supports": ["b1", "b2", "b3", "b4"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:king-14", "relation": "position_held", "status": "asserted", "bindings": [{"bid": "b4", "role": "end_time", "value": {"literal": {"datatype": "time", "time": "+1715-09-01T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}, {"bid": "b1", "role": "holder", "value": {"entity": "ex:LouisXIV"}}, {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}}, {"bid": "b5", "role": "replaces", "value": {"entity": "ex:LouisXIII"}}, {"bid": "b3", "role": "start_time", "value": {"literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:regnal-list"}, "supports": ["b1", "b2", "b3", "b4"]}, {"id": "e2", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:louis-bio", "doc_sha256": "sha256:56940b729460cb9a75d5d63ab1f907a502fef80530b4aabff2cd8e9c28a44b2f"}, "selectors": [{"type": "quote", "exact": "Louis XIV succeeded his father Louis XIII", "prefix": "", "suffix": " as King of "}, {"type": "position", "start": 0, "end": 41}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "supports": ["b1", "b5"], "event_hash": "sha256:87eaf6a24f9088334f463104155187b658be6cb501f09fd6acfe8641a987b18d"}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:loop-yyz", "relation": "flies_between", "status": "asserted", "bindings": [{"bid": "b1", "role": "carrier", "value": {"entity": "ex:AirCanada"}}, {"bid": "b2", "role": "destination", "value": {"entity": "ex:YYZ"}}, {"bid": "b3", "role": "origin", "value": {"entity": "ex:YYZ"}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:sightseeing-flight"}, "supports": ["b1", "b2", "b3"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:married-curie", "relation": "married", "status": "asserted", "bindings": [{"bid": "b4", "role": "end_time", "value": {"literal": {"datatype": "time", "time": "+1906-04-19T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}, {"bid": "b1", "role": "spouse", "value": {"entity": "ex:Maria_Skłodowska"}}, {"bid": "b2", "role": "spouse", "value": {"entity": "ex:Pierre_Curie"}}, {"bid": "b3", "role": "start_time", "value": {"literal": {"datatype": "time", "time": "+1895-07-26T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}, "supports": ["b1", "b2", "b3", "b4"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:pop-łódź-2019", "relation": "population", "status": "asserted", "bindings": [{"bid": "b1", "role": "place", "value": {"entity": "ex:Łódź"}}, {"bid": "b3", "role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z", "precision": 9, "calendar": "gregorian"}}}, {"bid": "b2", "role": "quantity", "value": {"literal": {"datatype": "quantity", "amount": "+679941", "unit": "1"}}}], "evidence": [{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:stat-yearbook-2020"}, "reference": [{"role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2020-00-00T00:00:00Z", "precision": 9}}}], "supports": ["b1", "b2", "b3"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:pop-łódź-2019-dep", "relation": "population", "status": "asserted", "bindings": [{"bid": "b1", "role": "place", "value": {"entity": "ex:Łódź"}}, {"bid": "b3", "role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z", "precision": 9, "calendar": "gregorian"}}}, {"bid": "b2", "role": "quantity", "value": {"literal": {"datatype": "quantity", "amount": "+685285", "unit": "1"}}}], "rank": "deprecated", "rank_reason": ["wd:Q41755623"], "evidence": [{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:old-estimate"}, "supports": ["b1", "b2", "b3"]}], "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:reg-1", "relation": "regulates", "status": "asserted", "bindings": [{"bid": "b1", "role": "context", "value": {"entity": "ex:HeLa"}}, {"bid": "b2", "role": "regulator", "value": {"entity": "ex:TP53"}}, {"bid": "b3", "role": "target", "value": {"entity": "ex:TP53"}, "extensions": {"ex:curation": {"checked": true, "by": ["curator:a", "curator:b"]}}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:review-p53"}, "supports": ["b1", "b2", "b3"]}], "extensions": {"hif:weight": 0.5}, "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:route-1", "relation": "flight_route", "status": "asserted", "bindings": [{"bid": "b1", "role": "carrier", "value": {"entity": "ex:AirCanada"}}, {"bid": "b2", "role": "stop", "value": {"entity": "ex:YYZ"}, "position": 1}, {"bid": "b3", "role": "stop", "value": {"entity": "ex:YUL"}, "position": 2}, {"bid": "b4", "role": "stop", "value": {"entity": "ex:YYZ"}, "position": 3}], "evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:route-note", "doc_sha256": "sha256:8b395a98af191e8344b7feeb58aa893408f6ff9ae0cb4a2eb91add710f7e94c4"}, "selectors": [{"type": "quote", "exact": "Toronto → Montréal → Toronto", "prefix": "anada flies ", "suffix": " every day."}, {"type": "position", "start": 29, "end": 57}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "event_hash": "sha256:24fd8e742587e8838772bb3b65dac106a564dbeafa258297616717fa32bbfbd9", "supports": ["b1", "b2", "b3", "b4"]}], "source_text": "Note by 𠮷田: Air Canada flies Toronto → Montréal → Toronto every day.", "extensions": {"hif:weight": 2}, "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "f:station-東京", "relation": "station_profile", "status": "asserted", "bindings": [{"bid": "b7", "role": "active", "value": {"literal": {"datatype": "boolean", "value": true}}}, {"bid": "b4", "role": "code", "value": {"literal": {"datatype": "string", "value": "TYO"}}}, {"bid": "b5", "role": "elevation", "value": {"literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573", "lower": "+3", "upper": "+4"}}}, {"bid": "b8", "role": "homepage", "value": {"literal": {"datatype": "iri", "value": "https://www.tokyostationcity.com/"}}}, {"bid": "b9", "role": "location", "value": {"literal": {"datatype": "geo", "lat": "+35.6812", "lon": "+139.7671", "precision": "+0.0001", "globe": "wd:Q2"}}}, {"bid": "b3", "role": "name", "value": {"literal": {"datatype": "lang_string", "value": "Tokyo Station", "lang": "en"}}}, {"bid": "b2", "role": "name", "value": {"literal": {"datatype": "lang_string", "value": "東京駅", "lang": "ja"}}}, {"bid": "b6", "role": "opened", "value": {"literal": {"datatype": "time", "time": "+1914-12-20T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}, {"bid": "b1", "role": "station", "value": {"entity": "ex:東京駅"}}], "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:station-guide"}, "supports": ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "b9"]}], "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "g:who-1774", "relation": "position_held", "status": "goal", "bindings": [{"bid": "b1", "role": "holder", "value": {"unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}}, {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}}, {"bid": "b3", "role": "start_time", "value": {"literal": {"datatype": "time", "time": "+1774-05-10T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}], "goal": {"brief": "Who became King of France on 10 May 1774?", "owner": "agent:history-desk"}, "rank": "normal", "visibility": "visible"},
  {"kind": "hyperedge", "id": "m:sup-1", "relation": "khg:supersedes", "status": "asserted", "bindings": [{"bid": "b2", "role": "khg:superseded", "value": {"fact": "f:born-skłodowska-kraków"}}, {"bid": "b1", "role": "khg:superseding", "value": {"fact": "f:born-skłodowska-warszawa"}}], "reason": "correction", "note": "birthplace is Warsaw, per the curated biography", "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}, "supports": ["b1", "b2"]}], "rank": "normal", "visibility": "visible"}
 ]
}
```

## 3. Relation-type schema language (`khg-relation-schema/1.0.0`)

The schema language is our own JSON, shaped like LinkML [R04 O10, O11] (ruling). The M layer checks it with a
meta-schema and Python checks (M001–M017). A schema can be embedded in a C1 container as a `relation-schema`
record, or inlined in HIF as `khg-schema-document`. HIF references it by id and hash (§4.5).

| Field | Meaning |
|---|---|
| `kind`, `format`, `id`, `version`, `label` | `"relation-schema"`, `"khg-relation-schema/1.0.0"`. The schema is referenced as `"<id>/<version>"`, and the version is semver (M004) |
| `entity_types` | `[{id, parents?}]`, a DAG (M016) |
| `roles` | the **global** role vocabulary (F4): `[{id, label?, aliases?, mappings?}]`. The `khg:` namespace is reserved (M008) |
| `relations` | `[{id, kind?, label?, mappings?, primary?, time?, key?, constraints?, roles}]`. `kind` is `fact` in v1; `rule` comes in 1.1 (M015 before then). `primary {subject, object}` names two core usages with max 1 (M012) |
| `default_time` | the time model of relations that declare none: `{"model": "timeless"}` unless set (§2.6; M007 accepts `interval`, `invariant` and `timeless`) |
| `confidence_scales` | `[{id, kind: "bounded", min, max}]`; `probability` is built in |
| usage `role`, `slot` | a global role id, used once per relation (M002, M009); the slot is `core`, `qualifier`, `time` or `meta`. A time usage must be named by the time model and have max 1 and one time-literal filler (M007) |
| usage `fillers` | a disjunction of `{entity: [types]}`, `{literal: datatype, units?, precision_min?}` and `{fact: [relations]}`. A `fact` filler makes the relation nestable |
| usage `min`, `max`, `ordered`, `complete` | cardinality (`max: null` is unbounded; M010); positions 1..n; a closed filler set (needs min > 0; M014) |
| usage `direction`, `somevalue`, `novalue`, `label` | the default direction; whether the special values are allowed (default true); a local name |
| `key` | `{roles, temporal, on_collision}` (§2.5; M003, M011, M017) |
| `constraints` | `{type ∈ requires, excludes, at_least_one_of, must_differ, must_agree; roles; severity ∈ error, warning}` (S024). Any other severity is M015 |

- A **symmetric** role is one usage with `max > 1` that is not `ordered`, such as `married.spouse`.
- Every relation with an interval time model has the built-in meta usage `khg:end_cause` (§2.7).
- The built-in lifecycle relations of §2.7 are part of every schema.

**Wikidata constraints** map onto the language [DB §3.4]:
- allowed qualifiers become usages;
- required qualifiers become `min: 1`;
- single-value and single-best-value constraints become a key;
- P2241 and P7452 become `rank_reason`.

**The example** is the fixture's schema. It has 11 relations and exercises:
- keys: `position_held` (temporal, `close_older`), and `population` and `born_in` (non-temporal, `dispute`);
- symmetric roles: `married` and `co_administration_causes`;
- an ordered and complete role: `flight_route.stop`;
- nesting: `claims`;
- all seven datatypes: `station_profile`;
- a warning constraint: `flies_between`;
- time models: `interval` for two relations, `invariant` for four, and the default `timeless` for five.

```json
{
 "kind": "relation-schema",
 "format": "khg-relation-schema/1.0.0",
 "id": "p2-gate",
 "version": "1.0.0",
 "label": "P2 gate fixture schema",
 "entity_types": [
  {"id": "Agent"},
  {"id": "Airline"},
  {"id": "Airport"},
  {"id": "CellLine"},
  {"id": "Chemical"},
  {"id": "Drug"},
  {"id": "Gene"},
  {"id": "Outcome"},
  {"id": "Place"},
  {"id": "Position"},
  {"id": "Reaction"},
  {"id": "Station"},
  {"id": "Person", "parents": ["Agent"]},
  {"id": "Organisation", "parents": ["Agent"]}
 ],
 "confidence_scales": [{"id": "llm-0-10", "kind": "bounded", "min": 0, "max": 10}],
 "roles": [
  {"id": "regulator"},
  {"id": "target"},
  {"id": "context"},
  {"id": "agent"},
  {"id": "effect"},
  {"id": "carrier"},
  {"id": "stop"},
  {"id": "origin"},
  {"id": "destination"},
  {"id": "holder"},
  {"id": "position"},
  {"id": "replaces"},
  {"id": "place"},
  {"id": "quantity"},
  {"id": "person"},
  {"id": "birthplace"},
  {"id": "reaction"},
  {"id": "catalyst"},
  {"id": "claimant"},
  {"id": "claim"},
  {"id": "station"},
  {"id": "name"},
  {"id": "code"},
  {"id": "elevation"},
  {"id": "opened"},
  {"id": "active"},
  {"id": "homepage"},
  {"id": "location"},
  {"id": "spouse"},
  {"id": "start_time", "label": "start time", "mappings": {"wikidata": "P580"}},
  {"id": "end_time", "label": "end time", "mappings": {"wikidata": "P582"}},
  {"id": "point_in_time", "label": "point in time", "mappings": {"wikidata": "P585"}}
 ],
 "relations": [
  {"id": "regulates", "time": {"model": "invariant"}, "roles": [{"role": "regulator", "slot": "core", "fillers": [{"entity": ["Gene"]}], "min": 1, "max": 1, "direction": "tail"}, {"role": "target", "slot": "core", "fillers": [{"entity": ["Gene"]}], "min": 1, "max": 1, "direction": "head"}, {"role": "context", "slot": "qualifier", "fillers": [{"entity": ["CellLine"]}], "min": 0, "max": 1, "direction": "tail"}]},
  {"id": "co_administration_causes", "roles": [{"role": "agent", "slot": "core", "fillers": [{"entity": ["Drug"]}], "min": 2, "max": null, "direction": "tail"}, {"role": "effect", "slot": "core", "fillers": [{"entity": ["Outcome"]}], "min": 1, "max": 1, "direction": "head"}]},
  {"id": "flight_route", "roles": [{"role": "carrier", "slot": "core", "fillers": [{"entity": ["Airline"]}], "min": 1, "max": 1, "direction": "tail"}, {"role": "stop", "slot": "core", "fillers": [{"entity": ["Airport"]}], "min": 2, "max": null, "ordered": true, "complete": true, "direction": "head"}]},
  {"id": "flies_between", "constraints": [{"type": "must_differ", "roles": ["origin", "destination"], "severity": "warning"}], "roles": [{"role": "carrier", "slot": "core", "fillers": [{"entity": ["Airline"]}], "min": 1, "max": 1}, {"role": "origin", "slot": "core", "fillers": [{"entity": ["Airport"]}], "min": 1, "max": 1}, {"role": "destination", "slot": "core", "fillers": [{"entity": ["Airport"]}], "min": 1, "max": 1}]},
  {"id": "position_held", "mappings": {"wikidata": "P39"}, "primary": {"subject": "holder", "object": "position"}, "time": {"model": "interval", "start": "start_time", "end": "end_time"}, "key": {"roles": ["position"], "temporal": true, "on_collision": "close_older"}, "roles": [{"role": "holder", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 1, "max": 1, "direction": "tail"}, {"role": "position", "slot": "core", "fillers": [{"entity": ["Position"]}], "min": 1, "max": 1, "direction": "head"}, {"role": "start_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"}, {"role": "end_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"}, {"role": "replaces", "slot": "qualifier", "fillers": [{"entity": ["Person"]}], "min": 0, "max": null, "direction": "tail"}]},
  {"id": "married", "time": {"model": "interval", "start": "start_time", "end": "end_time"}, "roles": [{"role": "spouse", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 2, "max": 2, "complete": true}, {"role": "start_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1}, {"role": "end_time", "slot": "time", "fillers": [{"literal": "time"}], "min": 0, "max": 1}]},
  {"id": "population", "mappings": {"wikidata": "P1082"}, "time": {"model": "invariant"}, "key": {"roles": ["place", "point_in_time"], "temporal": false, "on_collision": "dispute"}, "roles": [{"role": "place", "slot": "core", "fillers": [{"entity": ["Place"]}], "min": 1, "max": 1, "direction": "tail"}, {"role": "quantity", "slot": "core", "fillers": [{"literal": "quantity", "units": ["1"]}], "min": 1, "max": 1, "direction": "head"}, {"role": "point_in_time", "slot": "qualifier", "fillers": [{"literal": "time", "precision_min": 9}], "min": 0, "max": 1, "direction": "tail"}]},
  {"id": "station_profile", "roles": [{"role": "station", "slot": "core", "fillers": [{"entity": ["Station"]}], "min": 1, "max": 1, "direction": "tail"}, {"role": "name", "slot": "qualifier", "fillers": [{"literal": "lang_string"}], "min": 0, "max": null, "direction": "head"}, {"role": "code", "slot": "qualifier", "fillers": [{"literal": "string"}], "min": 0, "max": 1, "direction": "head"}, {"role": "elevation", "slot": "qualifier", "fillers": [{"literal": "quantity", "units": ["wd:Q11573"]}], "min": 0, "max": 1, "direction": "head"}, {"role": "opened", "slot": "qualifier", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "head"}, {"role": "active", "slot": "qualifier", "fillers": [{"literal": "boolean"}], "min": 0, "max": 1, "direction": "head"}, {"role": "homepage", "slot": "qualifier", "fillers": [{"literal": "iri"}], "min": 0, "max": 1, "direction": "head"}, {"role": "location", "slot": "qualifier", "fillers": [{"literal": "geo"}], "min": 0, "max": 1, "direction": "head"}]},
  {"id": "born_in", "mappings": {"wikidata": "P19"}, "time": {"model": "invariant"}, "key": {"roles": ["person"], "temporal": false, "on_collision": "dispute"}, "roles": [{"role": "person", "slot": "core", "fillers": [{"entity": ["Person"]}], "min": 1, "max": 1, "direction": "tail"}, {"role": "birthplace", "slot": "core", "fillers": [{"entity": ["Place"]}], "min": 1, "max": 1, "direction": "head"}]},
  {"id": "claims", "time": {"model": "invariant"}, "roles": [{"role": "claimant", "slot": "core", "fillers": [{"entity": ["Agent"]}], "min": 1, "max": 1, "direction": "tail"}, {"role": "claim", "slot": "core", "fillers": [{"fact": ["born_in"]}], "min": 1, "max": 1, "direction": "head", "somevalue": false, "novalue": false}, {"role": "point_in_time", "slot": "qualifier", "fillers": [{"literal": "time"}], "min": 0, "max": 1, "direction": "tail"}]},
  {"id": "catalysed_by", "roles": [{"role": "reaction", "slot": "core", "fillers": [{"entity": ["Reaction"]}], "min": 1, "max": 1, "direction": "tail"}, {"role": "catalyst", "slot": "core", "fillers": [{"entity": ["Chemical"]}], "min": 1, "max": null, "direction": "head"}]}
 ]
}
```

**P6** calls `schema_hypergraph(schema, slots=("core", "qualifier"))`. It returns sorted
`{"vertices": [roles], "hyperedges": {relation: [roles]}}`. For example, `regulates` maps to
`[context, regulator, target]` and `married` to `[spouse]`.
- A role is **one vertex whatever its slot** in each relation (F4).
- Lifecycle relations never appear. Rule relations will appear when they ship in 1.1.
- Time and meta usages appear only when asked for.

`is_alpha_acyclic(hg)` runs the GYO reduction. Two more schemas ship for P6's gate (critique CONS-26):

| Schema | Core and qualifier slots | Result |
|---|---|---|
| `fixture.relation-schema.json` | 30 vertices, 11 hyperedges | α-acyclic |
| `cyclic.relation-schema.json` | 3 relations whose role sets form a triangle | α-cyclic |
| `wikidata-shaped.relation-schema.json` | 3 relations sharing P580-, P582-, P585- and P1545-style roles | α-cyclic; residue `[replaces, series_ordinal]`, `[point_in_time, series_ordinal]`, `[point_in_time, replaces]` |

**Semantic checks** run in Python (F5): M001–M017 on the schema document, and S001–S026 (S017 in 1.1) on each
record against it.

## 4. HIF mapping: the `roles` convention and the `khg-hif/1.0.0` profile

### 4.1 Two layers and the contested choice

**`role-convention` 1.0.0** is the upstream artefact (F15). Its four rules are valid HIF 0.1 today [DA §4.1]
(ruling):

1. Every incidence of a role-carrying edge has `attrs.role`, one non-empty string. An edge is role-carrying when
   at least one of its incidences has `attrs.role` (R001).
2. A node with k roles in one edge appears in k incidence records. The records of one (edge, node) pair may
   differ in `direction`, and must differ in `role` or in `role-position`. Exact repeats of (edge, node, role,
   role-position) are malformed (R002).
3. `metadata["role-convention"] = "1.0.0"` declares the convention (R003). `metadata["role-vocabulary"]` is
   optional and maps each role to `{label?, ...}`.
4. `attrs["role-position"]`, an integer ≥ 1, orders the fillers of one role (R004). It is now a convention rule,
   not a profile rule (critique UPSTREAM): the fixture PR's `ordered` file needs it, and only it can express a
   route.

**Layer R** checks these four rules and nothing else. `validate(obj, kind="role-convention")` runs J, H and R, so
P2's own tool checks third-party role files and the upstream fixtures.

**`khg-hif/1.0.0`** adds the khg bookkeeping on top of R:
- a draft-07 schema that `allOf`s the vendored schema by its `$id`, resolved offline (§8.1);
- Python P checks.

It uses flat dash-case `khg-*` keys, plus the generic `relation` on edges and `label` on nodes (graft [J-cons],
[J-std]). It never adds top-level or record-level keys (F3).

**One incidence record per binding** (ruling of all three judges; R01 D-01's role list is overruled). HIF gives
each record one `direction`, so tail plus head needs two records:
- the schema accepts repeated pairs [R02 §5 case 02];
- upstream's compliant `duplicated_nodes_edges.json` repeats pairs [R02 §3];
- the loaders round-trip them exactly, which a role list cannot [R03 §8, D2, c06].

The fixture has three repeated pairs: TP53 in `f:reg-1` (tail and head), YYZ in `f:route-1` (positions 1 and 3)
and YYZ in `f:loop-yyz` (origin and destination).

### 4.2 C1 → HIF, exactly

`to_hif(container, schema, *, relations=None, literal_nodes="shared", schema_document=False) -> dict`:

| C1 | HIF |
|---|---|
| header | `metadata` (§4.5). The keys of `extensions["hif:metadata"]` are copied as plain keys |
| entity | node `{node: id, weight?, attrs: {khg-kind: "entity", label, khg-types, khg-aliases?, khg-redirect-to?, khg-version?, khg-recorded-at?, khg-extensions?}}`. `extensions["hif:weight"]` becomes `weight` |
| literal, `literal_nodes="shared"` (default) | node `_:lit:<32 hex of digest("khg-literal-node/1", canonical literal)>`, **shared by value**, with `{khg-kind: "literal", label, khg-literal}` |
| literal, `literal_nodes="per_binding"` | node `_:litb:<32 hex of digest("khg-literal-binding/1", [record id, bid])>`, **one per binding**, with the same attrs (critique CONS-15; for P5's drawings) |
| `somevalue`, `novalue`, `unbound` | node `_:sv:`, `_:nv:` or `_:var:` + `<32 hex of digest("khg-special-node/1", [record id, bid])>`, **one per binding**, with `{khg-kind, khg-unbound?}` |
| fact value | node `_:ref:<fact id>` with `{khg-kind: "fact-ref", khg-ref, khg-external?}`. `khg-ref` is authoritative, and a reference is never inferred from id equality [R02 §11 rec. 7]. A `_:ref:` id may have 518 code points (P003; critique GL-16) |
| hyperedge | edge `{edge: id, weight?, attrs: {relation, khg-status, khg-status-ref?, khg-rank, khg-rank-reason?, khg-visibility, khg-evidence?, khg-confidence?, khg-source-text?, khg-goal?, khg-reason?, khg-note?, khg-typed-under?, khg-version?, khg-recorded-at?, khg-recorded-by?, khg-extensions?}}` |
| binding | incidence `{edge, node, direction?, weight?, attrs: {role, khg-bid, role-position?, khg-extensions?}}`, with the effective direction. The binding's `extensions["hif:weight"]` becomes `weight`, and its other extensions `khg-extensions` (critique GL-07) |

The literal label is `time/precision` (plus ` (Julian)`), the amount plus the unit (plus the bounds), `value@lang`,
`lat,lon`, `true` or `false`, or the value. `schema_document=True` inlines the schema as `khg-schema-document`.

**Order.** Entity nodes by id, then derived nodes by id; edges by id; incidences by edge, then in canonical binding
order (role, position, value).

**`network-type`** is `directed` iff every incidence has a direction. Otherwise it is `undirected`, and the native
directions stay, since HIF allows them in any network type [R02 §5 cases 24–25] (ruling; B's `khg:direction`
rewrite is rejected). `asc` is never written (P007).

**Weight** is never invented and never read as confidence [R03 D6]. The fixture carries four weights, and all
survive every step of G1:
- node `ex:TP53`: 3;
- edge `f:reg-1`: 0.5;
- edge `f:route-1`: 2;
- incidence `f:coadmin-1`/b1: 0.25.

### 4.3 HIF → C1

`from_hif(hif, schema=None) -> dict` runs J, V, H, R and P, then decoding. Without `schema` it uses
`khg-schema-document`. Without either it raises D009.

A file without `khg-profile` is P001. v1 has no foreign fallback; importing such files is 1.1 (§4.4).

Decoding refuses:
- a duplicate node or edge (D001);
- an undeclared edge (D003); an undeclared node (D002) in a complete file, or an undeclared derived `_:` node in any
  file; a fact reference that does not resolve and is not external (D002). In a file that is not complete, an
  undeclared node without the `_:` prefix is an entity the file does not hold (§4.6; ruling 19);
- an external reference in a complete file that is not a slice, or to a fact present in the file (P017);
- a derived id that does not match its value, (record id, bid) or reference (D005);
- a schema id or hash that differs from the declared one (D009);
- a repeated `khg-bid` in one edge (P016);
- in a directed file, an incidence without direction (P010).

A direction equal to the usage default is dropped; one that contradicts it is S016, emitted while decoding (§8.1).
The header is rebuilt with `content: "snapshot"`. Export followed by import gives the same canonical container
(§1.4).

### 4.4 Files that carry the convention but not the profile

- `validate(obj, kind="role-convention")` checks them (J, H, R).
- The loaders accept them with `validate="convention"` and round-trip them in source order (§5). The five
  fixture-PR files do so through both libraries.
- `from_hif` refuses them (P001) in v1.

Importing foreign HIF into C1 comes in 1.1, following [DA §4.6]: integer ids, list-valued roles, missing roles
and relations, key clashes, and a loss report over upstream's compliant fixtures, which will then be vendored. Its
codes F001–F005 and F007–F014 are planned, not registered (§8.1; critique SCOPE-F13).

### 4.5 Metadata declaration block

| Key | Value | Req. |
|---|---|---|
| `role-convention` | `"1.0.0"` | yes (R003) |
| `role-vocabulary` | `{role: {label?, ...}}` | no |
| `hif-schema`, `hif-schema-sha256` | the raw URL pinned at commit `b691a3d…`; `"sha256:639466b7…2196"` | yes (P001; P009 when not the pinned value) |
| `khg-profile`, `khg-record` | `"khg-hif/1.0.0"`, or `"khg-hif/1.1.0"` for a file that names what it does not hold (§4.6); `"khg-record/1.0.0"` | yes (P001; V001 for an unknown version) |
| `khg-schema`, `khg-schema-sha256` | `"<id>/<version>"` and its digest | yes (P001; D009) |
| `khg-document-id` | the header's `document_id` | yes (P001) |
| `khg-literal-nodes` | `"shared"` or `"per_binding"` | yes (P001, P009) |
| `khg-complete` | the header's `complete`; `false` on every slice. A file that is not complete (absent or `false`) may name entities and facts it does not hold (§4.6) | no |
| `khg-slice` | `{relations}` | on slices |
| `khg-schema-document` | the relation-type schema, inlined | no |

`default_attrs` and unknown `khg-*` keys are refused (P008). Any other key passes through and decodes into the
header's `extensions["hif:metadata"]` (`title` in the fixture).

### 4.6 Directed slices and the gate fixture as HIF

A **slice**, `to_hif(c, schema, relations=[...])`, exports three things (critique GL-17, CONS-14):
- the hyperedges of the listed relations;
- the lifecycle record named by the `status_ref` of every kept fact, applied until nothing is added;
- the entities that kept records reference.

A fact reference to a fact outside the slice becomes an external reference node (`khg-external: true`). Every
slice writes `khg-complete: false` and `khg-slice`. A slice of `claims` alone keeps `f:born-louis14-paris` as external
(S-EXP-011).

**What a file does not hold** (ruling 19; `khg-hif/1.1.0`). A container that is not complete (§2.1) may name entities
and facts it does not hold, and so may its slices.
- `to_hif` writes such an entity as the node of its incidences, with no node record, which HIF allows [R02 §5 case
  28]; such a fact is an external reference node.
- Decoding reads an undeclared node without the `_:` prefix as that entity, and accepts an external reference, in any
  file that is not complete (`khg-complete` absent or `false`) or is a slice. Neither gets a record, so the container
  comes back as it was, through XGI and HyperNetX too (G1).
- In a complete file both stay refused (D002, P017). An undeclared derived node is D002 in any file, since `to_hif`
  declares every derived node.
- A file that names an entity without a node record, or holds an external reference outside a slice, is stamped
  `khg-hif/1.1.0`, the lowest version whose features it uses (§11.2). Every other file keeps `khg-hif/1.0.0` and its
  bytes. The reader reads 1.0.x and 1.1.x files by the same rules.

So any valid container, and any slice of it, reloads.

The fixture's **directed slice** keeps the 9 relations whose every usage has a direction. It is directed, with 42
nodes (20 entities, 16 literals, 3 fact references, 3 special nodes), 16 edges and 52 incidences, in
`fixture.directed-slice.hif.json`.

**`fixture.hif.json`** has:
- 46 nodes: 22 entities (one of them, `ex:Mazarin`, isolated), 18 literals, 3 fact references, and one each of
  `somevalue`, `novalue` and `unbound`;
- 18 edges;
- 59 incidences, of which 52 have a direction, with 3 repeated pairs;
- 4 weights, and one binding with nested extensions (`f:reg-1` b3).

It is `undirected` because `married` and `flies_between` declare no direction.

**It was validated against the vendored `hif_schema_v0.1.0.json` with jsonschema 4.26.0 (`Draft7Validator`) and
with fastjsonschema 2.22.2, under closed resolvers with sockets blocked: no errors.** It also passes the
`khg-hif-1.0.0` profile schema and the full layered validator. The validator reports only the two designed
warnings (§1.4).

```json
{
 "network-type": "undirected",
 "metadata": {"role-convention": "1.0.0", "hif-schema": "https://raw.githubusercontent.com/HIF-org/HIF-standard/b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json", "hif-schema-sha256": "sha256:639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196", "khg-profile": "khg-hif/1.0.0", "khg-record": "khg-record/1.0.0", "khg-schema": "p2-gate/1.0.0", "khg-schema-sha256": "sha256:cadd01cd3d37e09337d2fe70bd5572a32dff4a7d6f4a0ac26845c6c27d0e194d", "khg-document-id": "p2-gate-fixture", "khg-literal-nodes": "shared", "khg-complete": true, "title": "P2 gate fixture (adversarial)"},
 "nodes": [
  {"node": "ex:AirCanada", "attrs": {"khg-kind": "entity", "label": "Air Canada", "khg-types": ["Airline"]}},
  {"node": "ex:Chronicler_Ødegård", "attrs": {"khg-kind": "entity", "label": "Ødegård the chronicler", "khg-types": ["Person"]}},
  {"node": "ex:HeLa", "attrs": {"khg-kind": "entity", "label": "HeLa", "khg-types": ["CellLine"]}},
  {"node": "ex:KingOfFrance", "attrs": {"khg-kind": "entity", "label": "King of France", "khg-types": ["Position"]}},
  {"node": "ex:Kraków", "attrs": {"khg-kind": "entity", "label": "Kraków", "khg-types": ["Place"]}},
  {"node": "ex:LouisXIII", "attrs": {"khg-kind": "entity", "label": "Louis XIII", "khg-types": ["Person"]}},
  {"node": "ex:LouisXIV", "attrs": {"khg-kind": "entity", "label": "Louis XIV", "khg-types": ["Person"]}},
  {"node": "ex:Maria_Skłodowska", "attrs": {"khg-kind": "entity", "label": "Maria Skłodowska", "khg-types": ["Person"]}},
  {"node": "ex:Mazarin", "attrs": {"khg-kind": "entity", "label": "Jules Mazarin", "khg-types": ["Person"]}},
  {"node": "ex:Paris", "attrs": {"khg-kind": "entity", "label": "Paris", "khg-types": ["Place"]}},
  {"node": "ex:Pierre_Curie", "attrs": {"khg-kind": "entity", "label": "Pierre Curie", "khg-types": ["Person"]}},
  {"node": "ex:R-hydrolysis-7", "attrs": {"khg-kind": "entity", "label": "hydrolysis reaction 7", "khg-types": ["Reaction"]}},
  {"node": "ex:TP53", "weight": 3, "attrs": {"khg-kind": "entity", "label": "TP53", "khg-types": ["Gene"]}},
  {"node": "ex:Warszawa", "attrs": {"khg-kind": "entity", "label": "Warszawa", "khg-types": ["Place"]}},
  {"node": "ex:YUL", "attrs": {"khg-kind": "entity", "label": "Montréal–Trudeau", "khg-types": ["Airport"]}},
  {"node": "ex:YYZ", "attrs": {"khg-kind": "entity", "label": "Toronto Pearson", "khg-types": ["Airport"]}},
  {"node": "ex:anonymous_scribe", "attrs": {"khg-kind": "entity", "label": "an anonymous scribe", "khg-types": ["Person"]}},
  {"node": "ex:hypoglycaemia", "attrs": {"khg-kind": "entity", "label": "hypoglycaemia", "khg-types": ["Outcome"]}},
  {"node": "ex:insulin", "attrs": {"khg-kind": "entity", "label": "insulin", "khg-types": ["Drug"]}},
  {"node": "ex:metformin", "attrs": {"khg-kind": "entity", "label": "metformin", "khg-types": ["Drug"]}},
  {"node": "ex:Łódź", "attrs": {"khg-kind": "entity", "label": "Łódź", "khg-types": ["Place"]}},
  {"node": "ex:東京駅", "attrs": {"khg-kind": "entity", "label": "Tokyo Station", "khg-types": ["Station"]}},
  {"node": "_:lit:0916b45596fd096b0380304dc60304a9", "attrs": {"khg-kind": "literal", "label": "東京駅@ja", "khg-literal": {"datatype": "lang_string", "value": "東京駅", "lang": "ja"}}},
  {"node": "_:lit:1c9ac9fd2f7bb893ec62c50f833b7ff2", "attrs": {"khg-kind": "literal", "label": "+1914-12-20T00:00:00Z/11", "khg-literal": {"datatype": "time", "time": "+1914-12-20T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
  {"node": "_:lit:32fd170eaa098b760664b7efbe0e76e3", "attrs": {"khg-kind": "literal", "label": "Tokyo Station@en", "khg-literal": {"datatype": "lang_string", "value": "Tokyo Station", "lang": "en"}}},
  {"node": "_:lit:37211654a2f2823c4fad86f490e56819", "attrs": {"khg-kind": "literal", "label": "true", "khg-literal": {"datatype": "boolean", "value": true}}},
  {"node": "_:lit:3b18d26dda2204c791d484b77e3760d3", "attrs": {"khg-kind": "literal", "label": "+35.6812,+139.7671", "khg-literal": {"datatype": "geo", "lat": "+35.6812", "lon": "+139.7671", "precision": "+0.0001", "globe": "wd:Q2"}}},
  {"node": "_:lit:4d14352c5db021d2b0e70906aaa17a56", "attrs": {"khg-kind": "literal", "label": "+1610-05-14T00:00:00Z/11", "khg-literal": {"datatype": "time", "time": "+1610-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
  {"node": "_:lit:6914a0d25911f31c02d9ab52abfc5380", "attrs": {"khg-kind": "literal", "label": "+1906-04-19T00:00:00Z/11", "khg-literal": {"datatype": "time", "time": "+1906-04-19T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
  {"node": "_:lit:6d161c6594652b245fb282f351b71116", "attrs": {"khg-kind": "literal", "label": "+2019-00-00T00:00:00Z/9", "khg-literal": {"datatype": "time", "time": "+2019-00-00T00:00:00Z", "precision": 9, "calendar": "gregorian"}}},
  {"node": "_:lit:7d51413289245ae6e1aef061972a8a64", "attrs": {"khg-kind": "literal", "label": "https://www.tokyostationcity.com/", "khg-literal": {"datatype": "iri", "value": "https://www.tokyostationcity.com/"}}},
  {"node": "_:lit:851d6b4ba33d0b79f18d99559e5db094", "attrs": {"khg-kind": "literal", "label": "TYO", "khg-literal": {"datatype": "string", "value": "TYO"}}},
  {"node": "_:lit:86e4637ee45af992a7467d24f2a93a64", "attrs": {"khg-kind": "literal", "label": "+679941", "khg-literal": {"datatype": "quantity", "amount": "+679941", "unit": "1"}}},
  {"node": "_:lit:89999fcef774cb586483ef351c89ab9d", "attrs": {"khg-kind": "literal", "label": "+1715-09-01T00:00:00Z/11", "khg-literal": {"datatype": "time", "time": "+1715-09-01T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
  {"node": "_:lit:90f05b1fd19dd04d37dc279f0c7cecf1", "attrs": {"khg-kind": "literal", "label": "+1774-05-10T00:00:00Z/11", "khg-literal": {"datatype": "time", "time": "+1774-05-10T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
  {"node": "_:lit:a2cf58543de9d29be31622185c80a5d8", "attrs": {"khg-kind": "literal", "label": "+685285", "khg-literal": {"datatype": "quantity", "amount": "+685285", "unit": "1"}}},
  {"node": "_:lit:b11291e17146f26e1ea99ec83e6d5359", "attrs": {"khg-kind": "literal", "label": "+1895-07-26T00:00:00Z/11", "khg-literal": {"datatype": "time", "time": "+1895-07-26T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
  {"node": "_:lit:bc18b6e20588929fdc83e6b64a293be7", "attrs": {"khg-kind": "literal", "label": "+3.5 wd:Q11573 [+3, +4]", "khg-literal": {"datatype": "quantity", "amount": "+3.5", "unit": "wd:Q11573", "lower": "+3", "upper": "+4"}}},
  {"node": "_:lit:c2de076c6e50fcaff7c5f3a4c11964c6", "attrs": {"khg-kind": "literal", "label": "+1643-05-14T00:00:00Z/11", "khg-literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
  {"node": "_:lit:e230e99ef0e42e4a2882c518bacdd881", "attrs": {"khg-kind": "literal", "label": "+1700-00-00T00:00:00Z/9 (Julian)", "khg-literal": {"datatype": "time", "time": "+1700-00-00T00:00:00Z", "precision": 9, "calendar": "julian"}}},
  {"node": "_:nv:78311fb3c57188a07d1d2821930e2c3d", "attrs": {"khg-kind": "novalue"}},
  {"node": "_:ref:f:born-louis14-paris", "attrs": {"khg-kind": "fact-ref", "khg-ref": "f:born-louis14-paris"}},
  {"node": "_:ref:f:born-skłodowska-kraków", "attrs": {"khg-kind": "fact-ref", "khg-ref": "f:born-skłodowska-kraków"}},
  {"node": "_:ref:f:born-skłodowska-warszawa", "attrs": {"khg-kind": "fact-ref", "khg-ref": "f:born-skłodowska-warszawa"}},
  {"node": "_:sv:b3d2979870a1d331fa6dd177274b85d9", "attrs": {"khg-kind": "somevalue"}},
  {"node": "_:var:42a7d49f12bd77b91df2c3bdb9d9b045", "attrs": {"khg-kind": "unbound", "khg-unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}}
 ],
 "edges": [
  {"edge": "f:born-louis14-paris", "attrs": {"relation": "born_in", "khg-status": "quoted", "khg-rank": "normal", "khg-visibility": "visible"}},
  {"edge": "f:born-scribe", "attrs": {"relation": "born_in", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:scriptorium-notes"}, "supports": ["b1", "b2"]}]}},
  {"edge": "f:born-skłodowska-kraków", "attrs": {"relation": "born_in", "khg-status": "superseded", "khg-status-ref": "m:sup-1", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:curie-wrong", "doc_sha256": "sha256:685ed4266cfa7fb0429dee59b9feaa3cefde8894ac6556dce24e1894504a7a0d"}, "selectors": [{"type": "quote", "exact": "Maria Skłodowska was born in Kraków", "prefix": "", "suffix": "."}, {"type": "position", "start": 0, "end": 35}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "event_hash": "sha256:8b599a516787cb80778d875faf091249745d212631ad697a087299bce618a02f", "supports": ["b1", "b2"]}]}},
  {"edge": "f:born-skłodowska-warszawa", "attrs": {"relation": "born_in", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}, "supports": ["b1", "b2"]}]}},
  {"edge": "f:cat-7", "attrs": {"relation": "catalysed_by", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:lab-notebook-7"}, "supports": ["b1", "b2"]}]}},
  {"edge": "f:claim-1", "attrs": {"relation": "claims", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:chronicle-1700"}, "supports": ["b1", "b2", "b3"]}]}},
  {"edge": "f:coadmin-1", "attrs": {"relation": "co_administration_causes", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:coadmin-note", "doc_sha256": "sha256:242a3e2542b83f98e5adfa478e9d7ef5aa909708f7e184e88f51e5b09ff17368"}, "selectors": [{"type": "quote", "exact": "Metformin taken together with insulin can cause hypoglycaemia", "prefix": "", "suffix": "."}, {"type": "position", "start": 0, "end": 61}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "confidence": {"value": 7.5, "scale": "llm-0-10"}, "event_hash": "sha256:4ee38cb8eca2607e3f5f1a1411160729165f9bbbd5b4d8f5e274934ab5ab1b8a", "supports": ["b1", "b2", "b3"]}, {"id": "e2", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:insulin-label"}, "supports": ["b1", "b3"]}], "khg-confidence": {"value": 0.9, "scale": "probability", "scorer": {"name": "fixture-belief", "version": "0"}}}},
  {"edge": "f:king-13", "attrs": {"relation": "position_held", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:regnal-list"}, "supports": ["b1", "b2", "b3", "b4"]}]}},
  {"edge": "f:king-14", "attrs": {"relation": "position_held", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:regnal-list"}, "supports": ["b1", "b2", "b3", "b4"]}, {"id": "e2", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:louis-bio", "doc_sha256": "sha256:56940b729460cb9a75d5d63ab1f907a502fef80530b4aabff2cd8e9c28a44b2f"}, "selectors": [{"type": "quote", "exact": "Louis XIV succeeded his father Louis XIII", "prefix": "", "suffix": " as King of "}, {"type": "position", "start": 0, "end": 41}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "supports": ["b1", "b5"], "event_hash": "sha256:87eaf6a24f9088334f463104155187b658be6cb501f09fd6acfe8641a987b18d"}]}},
  {"edge": "f:loop-yyz", "attrs": {"relation": "flies_between", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:sightseeing-flight"}, "supports": ["b1", "b2", "b3"]}]}},
  {"edge": "f:married-curie", "attrs": {"relation": "married", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}, "supports": ["b1", "b2", "b3", "b4"]}]}},
  {"edge": "f:pop-łódź-2019", "attrs": {"relation": "population", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:stat-yearbook-2020"}, "reference": [{"role": "point_in_time", "value": {"literal": {"datatype": "time", "time": "+2020-00-00T00:00:00Z", "precision": 9}}}], "supports": ["b1", "b2", "b3"]}]}},
  {"edge": "f:pop-łódź-2019-dep", "attrs": {"relation": "population", "khg-status": "asserted", "khg-rank": "deprecated", "khg-rank-reason": ["wd:Q41755623"], "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:old-estimate"}, "supports": ["b1", "b2", "b3"]}]}},
  {"edge": "f:reg-1", "weight": 0.5, "attrs": {"relation": "regulates", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:review-p53"}, "supports": ["b1", "b2", "b3"]}]}},
  {"edge": "f:route-1", "weight": 2, "attrs": {"relation": "flight_route", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:route-note", "doc_sha256": "sha256:8b395a98af191e8344b7feeb58aa893408f6ff9ae0cb4a2eb91add710f7e94c4"}, "selectors": [{"type": "quote", "exact": "Toronto → Montréal → Toronto", "prefix": "anada flies ", "suffix": " every day."}, {"type": "position", "start": 29, "end": 57}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "event_hash": "sha256:24fd8e742587e8838772bb3b65dac106a564dbeafa258297616717fa32bbfbd9", "supports": ["b1", "b2", "b3", "b4"]}], "khg-source-text": "Note by 𠮷田: Air Canada flies Toronto → Montréal → Toronto every day."}},
  {"edge": "f:station-東京", "attrs": {"relation": "station_profile", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:station-guide"}, "supports": ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "b9"]}]}},
  {"edge": "g:who-1774", "attrs": {"relation": "position_held", "khg-status": "goal", "khg-rank": "normal", "khg-visibility": "visible", "khg-goal": {"brief": "Who became King of France on 10 May 1774?", "owner": "agent:history-desk"}}},
  {"edge": "m:sup-1", "attrs": {"relation": "khg:supersedes", "khg-status": "asserted", "khg-rank": "normal", "khg-visibility": "visible", "khg-evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:biography"}, "supports": ["b1", "b2"]}], "khg-reason": "correction", "khg-note": "birthplace is Warsaw, per the curated biography"}}
 ],
 "incidences": [
  {"edge": "f:born-louis14-paris", "node": "ex:Paris", "direction": "head", "attrs": {"role": "birthplace", "khg-bid": "b2"}},
  {"edge": "f:born-louis14-paris", "node": "ex:LouisXIV", "direction": "tail", "attrs": {"role": "person", "khg-bid": "b1"}},
  {"edge": "f:born-scribe", "node": "_:sv:b3d2979870a1d331fa6dd177274b85d9", "direction": "head", "attrs": {"role": "birthplace", "khg-bid": "b2"}},
  {"edge": "f:born-scribe", "node": "ex:anonymous_scribe", "direction": "tail", "attrs": {"role": "person", "khg-bid": "b1"}},
  {"edge": "f:born-skłodowska-kraków", "node": "ex:Kraków", "direction": "head", "attrs": {"role": "birthplace", "khg-bid": "b2"}},
  {"edge": "f:born-skłodowska-kraków", "node": "ex:Maria_Skłodowska", "direction": "tail", "attrs": {"role": "person", "khg-bid": "b1"}},
  {"edge": "f:born-skłodowska-warszawa", "node": "ex:Warszawa", "direction": "head", "attrs": {"role": "birthplace", "khg-bid": "b2"}},
  {"edge": "f:born-skłodowska-warszawa", "node": "ex:Maria_Skłodowska", "direction": "tail", "attrs": {"role": "person", "khg-bid": "b1"}},
  {"edge": "f:cat-7", "node": "_:nv:78311fb3c57188a07d1d2821930e2c3d", "direction": "head", "attrs": {"role": "catalyst", "khg-bid": "b2"}},
  {"edge": "f:cat-7", "node": "ex:R-hydrolysis-7", "direction": "tail", "attrs": {"role": "reaction", "khg-bid": "b1"}},
  {"edge": "f:claim-1", "node": "_:ref:f:born-louis14-paris", "direction": "head", "attrs": {"role": "claim", "khg-bid": "b2"}},
  {"edge": "f:claim-1", "node": "ex:Chronicler_Ødegård", "direction": "tail", "attrs": {"role": "claimant", "khg-bid": "b1"}},
  {"edge": "f:claim-1", "node": "_:lit:e230e99ef0e42e4a2882c518bacdd881", "direction": "tail", "attrs": {"role": "point_in_time", "khg-bid": "b3"}},
  {"edge": "f:coadmin-1", "node": "ex:insulin", "direction": "tail", "weight": 0.25, "attrs": {"role": "agent", "khg-bid": "b1"}},
  {"edge": "f:coadmin-1", "node": "ex:metformin", "direction": "tail", "attrs": {"role": "agent", "khg-bid": "b2"}},
  {"edge": "f:coadmin-1", "node": "ex:hypoglycaemia", "direction": "head", "attrs": {"role": "effect", "khg-bid": "b3"}},
  {"edge": "f:king-13", "node": "_:lit:c2de076c6e50fcaff7c5f3a4c11964c6", "direction": "tail", "attrs": {"role": "end_time", "khg-bid": "b4"}},
  {"edge": "f:king-13", "node": "ex:LouisXIII", "direction": "tail", "attrs": {"role": "holder", "khg-bid": "b1"}},
  {"edge": "f:king-13", "node": "ex:KingOfFrance", "direction": "head", "attrs": {"role": "position", "khg-bid": "b2"}},
  {"edge": "f:king-13", "node": "_:lit:4d14352c5db021d2b0e70906aaa17a56", "direction": "tail", "attrs": {"role": "start_time", "khg-bid": "b3"}},
  {"edge": "f:king-14", "node": "_:lit:89999fcef774cb586483ef351c89ab9d", "direction": "tail", "attrs": {"role": "end_time", "khg-bid": "b4"}},
  {"edge": "f:king-14", "node": "ex:LouisXIV", "direction": "tail", "attrs": {"role": "holder", "khg-bid": "b1"}},
  {"edge": "f:king-14", "node": "ex:KingOfFrance", "direction": "head", "attrs": {"role": "position", "khg-bid": "b2"}},
  {"edge": "f:king-14", "node": "ex:LouisXIII", "direction": "tail", "attrs": {"role": "replaces", "khg-bid": "b5"}},
  {"edge": "f:king-14", "node": "_:lit:c2de076c6e50fcaff7c5f3a4c11964c6", "direction": "tail", "attrs": {"role": "start_time", "khg-bid": "b3"}},
  {"edge": "f:loop-yyz", "node": "ex:AirCanada", "attrs": {"role": "carrier", "khg-bid": "b1"}},
  {"edge": "f:loop-yyz", "node": "ex:YYZ", "attrs": {"role": "destination", "khg-bid": "b2"}},
  {"edge": "f:loop-yyz", "node": "ex:YYZ", "attrs": {"role": "origin", "khg-bid": "b3"}},
  {"edge": "f:married-curie", "node": "_:lit:6914a0d25911f31c02d9ab52abfc5380", "attrs": {"role": "end_time", "khg-bid": "b4"}},
  {"edge": "f:married-curie", "node": "ex:Maria_Skłodowska", "attrs": {"role": "spouse", "khg-bid": "b1"}},
  {"edge": "f:married-curie", "node": "ex:Pierre_Curie", "attrs": {"role": "spouse", "khg-bid": "b2"}},
  {"edge": "f:married-curie", "node": "_:lit:b11291e17146f26e1ea99ec83e6d5359", "attrs": {"role": "start_time", "khg-bid": "b3"}},
  {"edge": "f:pop-łódź-2019", "node": "ex:Łódź", "direction": "tail", "attrs": {"role": "place", "khg-bid": "b1"}},
  {"edge": "f:pop-łódź-2019", "node": "_:lit:6d161c6594652b245fb282f351b71116", "direction": "tail", "attrs": {"role": "point_in_time", "khg-bid": "b3"}},
  {"edge": "f:pop-łódź-2019", "node": "_:lit:86e4637ee45af992a7467d24f2a93a64", "direction": "head", "attrs": {"role": "quantity", "khg-bid": "b2"}},
  {"edge": "f:pop-łódź-2019-dep", "node": "ex:Łódź", "direction": "tail", "attrs": {"role": "place", "khg-bid": "b1"}},
  {"edge": "f:pop-łódź-2019-dep", "node": "_:lit:6d161c6594652b245fb282f351b71116", "direction": "tail", "attrs": {"role": "point_in_time", "khg-bid": "b3"}},
  {"edge": "f:pop-łódź-2019-dep", "node": "_:lit:a2cf58543de9d29be31622185c80a5d8", "direction": "head", "attrs": {"role": "quantity", "khg-bid": "b2"}},
  {"edge": "f:reg-1", "node": "ex:HeLa", "direction": "tail", "attrs": {"role": "context", "khg-bid": "b1"}},
  {"edge": "f:reg-1", "node": "ex:TP53", "direction": "tail", "attrs": {"role": "regulator", "khg-bid": "b2"}},
  {"edge": "f:reg-1", "node": "ex:TP53", "direction": "head", "attrs": {"role": "target", "khg-bid": "b3", "khg-extensions": {"ex:curation": {"checked": true, "by": ["curator:a", "curator:b"]}}}},
  {"edge": "f:route-1", "node": "ex:AirCanada", "direction": "tail", "attrs": {"role": "carrier", "khg-bid": "b1"}},
  {"edge": "f:route-1", "node": "ex:YYZ", "direction": "head", "attrs": {"role": "stop", "khg-bid": "b2", "role-position": 1}},
  {"edge": "f:route-1", "node": "ex:YUL", "direction": "head", "attrs": {"role": "stop", "khg-bid": "b3", "role-position": 2}},
  {"edge": "f:route-1", "node": "ex:YYZ", "direction": "head", "attrs": {"role": "stop", "khg-bid": "b4", "role-position": 3}},
  {"edge": "f:station-東京", "node": "_:lit:37211654a2f2823c4fad86f490e56819", "direction": "head", "attrs": {"role": "active", "khg-bid": "b7"}},
  {"edge": "f:station-東京", "node": "_:lit:851d6b4ba33d0b79f18d99559e5db094", "direction": "head", "attrs": {"role": "code", "khg-bid": "b4"}},
  {"edge": "f:station-東京", "node": "_:lit:bc18b6e20588929fdc83e6b64a293be7", "direction": "head", "attrs": {"role": "elevation", "khg-bid": "b5"}},
  {"edge": "f:station-東京", "node": "_:lit:7d51413289245ae6e1aef061972a8a64", "direction": "head", "attrs": {"role": "homepage", "khg-bid": "b8"}},
  {"edge": "f:station-東京", "node": "_:lit:3b18d26dda2204c791d484b77e3760d3", "direction": "head", "attrs": {"role": "location", "khg-bid": "b9"}},
  {"edge": "f:station-東京", "node": "_:lit:32fd170eaa098b760664b7efbe0e76e3", "direction": "head", "attrs": {"role": "name", "khg-bid": "b3"}},
  {"edge": "f:station-東京", "node": "_:lit:0916b45596fd096b0380304dc60304a9", "direction": "head", "attrs": {"role": "name", "khg-bid": "b2"}},
  {"edge": "f:station-東京", "node": "_:lit:1c9ac9fd2f7bb893ec62c50f833b7ff2", "direction": "head", "attrs": {"role": "opened", "khg-bid": "b6"}},
  {"edge": "f:station-東京", "node": "ex:東京駅", "direction": "tail", "attrs": {"role": "station", "khg-bid": "b1"}},
  {"edge": "g:who-1774", "node": "_:var:42a7d49f12bd77b91df2c3bdb9d9b045", "direction": "tail", "attrs": {"role": "holder", "khg-bid": "b1"}},
  {"edge": "g:who-1774", "node": "ex:KingOfFrance", "direction": "head", "attrs": {"role": "position", "khg-bid": "b2"}},
  {"edge": "g:who-1774", "node": "_:lit:90f05b1fd19dd04d37dc279f0c7cecf1", "direction": "tail", "attrs": {"role": "start_time", "khg-bid": "b3"}},
  {"edge": "m:sup-1", "node": "_:ref:f:born-skłodowska-kraków", "direction": "head", "attrs": {"role": "khg:superseded", "khg-bid": "b2"}},
  {"edge": "m:sup-1", "node": "_:ref:f:born-skłodowska-warszawa", "direction": "tail", "attrs": {"role": "khg:superseding", "khg-bid": "b1"}}
 ]
}
```

## 5. Library loaders (XGI and HyperNetX)

```python
def load_xgi(hif: Mapping | str | os.PathLike, *,
             validate: Literal["profile", "convention", "none"] = "profile") -> Bundle: ...
def export_xgi(bundle: Bundle, *, strict: bool = True) -> dict: ...
def load_hnx(hif: Mapping | str | os.PathLike, *,
             validate: Literal["profile", "convention", "none"] = "profile") -> Bundle: ...
def export_hnx(bundle: Bundle, *, strict: bool = True) -> dict: ...
def khg_to_xgi(container, schema, **to_hif_kw) -> Bundle: ...        # to_hif, then load_xgi
def xgi_to_khg(bundle, schema, *, strict: bool = True) -> dict: ...  # export_xgi, then from_hif
# khg_to_hnx and hnx_to_khg likewise

class Bundle:
    graph: "xgi.Hypergraph | xgi.DiHypergraph | hnx.Hypergraph"
    context: Context
    report: ExportReport | None                    # set by the last export
    def records(self, edge, node=None) -> tuple[dict, ...]: ...   # full incidence records, in record order
    def roles(self, edge, node) -> list[str]: ...                  # e.g. ['regulator', 'target']
    def derive(self, graph) -> "Bundle": ...       # for copy(), clone(), restrict_to_*(), subhypergraph()
    def label(self, edge, node, *, role, bid=None, direction=None, position=None,
              weight=None, extensions=None) -> None: ...          # a record for a new membership

class ExportReport(TypedDict):
    stale: list; unlabelled: list; moved: list; moved_conflict: list
    dropped_records: list; dropped_nodes: list; dropped_edges: list
```

A `str` is a path. JSON text must be parsed first with `jsonio.loads`.
- **`validate="profile"`** runs J, V, H, R and P. It does not run S or D, which need the relation schema and run
  in `from_hif`.
- **`"convention"`** runs H and R.
- **`"none"`** runs nothing.

In every mode the loaders refuse `asc` files (P007), a directed file with an incidence that lacks direction
(P010), and duplicate node or edge declarations (D001). Undirected files may omit directions (critique GL-14).
The libraries' HIF functions are never called (F1).

**Construction** uses public constructors only [R03 §7].
- **XGI:** `add_node_to_edge`, `add_node`, `add_edge` and `set_*_attributes`. A `DiHypergraph` maps tail to
  `"in"` and head to `"out"`. No metadata is written into XGI network attributes; XGI has no public way to list
  them (critique GL-15).
- **HyperNetX:** the `Hypergraph` constructor, with this call pinned (critique GL-13):
  `hnx.Hypergraph(incidences_df, edge_col="edge", node_col="node", cell_weight_col="weight",
  misc_cell_properties_col="attrs", node_properties=nodes_df, edge_properties=edges_df,
  misc_properties_col="attrs")`. HNX 2.4.3 silently ignores the per-kind `misc_node_properties_col` and
  `misc_edge_properties_col`. Cell properties are written with the public `PropertyStore.set_property`; there is no
  `set_cell_properties`.

**Sources of truth** (critique GL-03).
- **XGI:** the context holds the incidence records, keyed by (edge, `khg-bid`), or by (edge, ordinal) in files
  without the profile. XGI cannot hold incidence attrs or weights.
- **HyperNetX:** the cells hold them.
  - A pair's first record becomes the cell's properties, so native readers see `role`, `khg-bid` and
    `role-position`.
  - Its weight goes in the cell weight column and its direction in the direction column.
  - Records 2..k of the same (edge, node) pair go under the reserved cell key `khg-extra-incidences`.
- **The context, for both libraries,** holds what neither library holds:
  - the metadata (authoritative);
  - the `network-type`;
  - the loaded weights of nodes, edges and incidences, with their JSON number type, so `2` stays `2` (critique
    GL-05);
  - which nodes were isolated and which edges were empty in the loaded file;
  - the declared ids in source order.

**Export reconciles** [R03 §7.4]. The library object decides which memberships exist.
- A **weight** is the library's value only when it differs numerically from the loaded one; otherwise it is the
  context's.
- **Node and edge records** are exported for nodes and edges with an exported incidence, plus those that were
  isolated or empty in the loaded file and still exist (critique GL-08). Others, including derived `_:` nodes
  left without incidences, are dropped and reported.
- **Node and edge attrs** come from the library, so native attribute edits are honoured.

**The strict rule** (critique LOADER-STRICT, GL-03).
- `export_*(strict=True)` raises `LoaderError` (P005) on:
  - an **unlabelled** membership: a new membership without a record. In profile files a record needs `role`
    and `khg-bid`; in other files, a new cell needs a `role`;
  - a **partial fact**: a record whose membership is gone while its edge still exists;
  - a **moved** record whose node map is not injective. A HyperNetX record whose `khg-bid` now sits on another
    node passes only when the old-to-new node map is injective (a rename), and is reported under `moved`; a
    collapse raises.
- Records of edges **removed whole** are dropped and reported, never raised.
- `strict=False` raises nothing: unlabelled memberships and partial records are dropped and reported. They are
  never exported bare.

**Order and determinism** (critique GL-09).
- Profile files are exported in §4.2 order, recomputed from the node attrs.
- Other files keep the source order of their records, and anything new follows, sorted by a typed key (type name,
  value). R03 c12 (ids `1` and `"1"`) round-trips in source order.
- The output never depends on `PYTHONHASHSEED`. G1 checks this in five child processes.

**Native operations**, executed on the fixture with `strict=True` (`native_ops.py`; `native-ops.json`). One test
per row ships as `tests/loaders/test_native_ops.py`.

| Library | Operation | Strict export |
|---|---|---|
| XGI | `copy()`, then `derive` | exact |
| XGI | weak `remove_node("ex:HeLa")` (`f:reg-1` survives) | raises: a partial fact |
| XGI | strong `remove_node("ex:HeLa", strong=True)` (`f:reg-1` removed whole) | exports; 3 records and the orphaned `ex:TP53` dropped and reported |
| XGI | `add_edge` + `set_edge_attributes`, then `label` per member | raises until labelled, then exports |
| XGI | `add_node_to_edge("f:reg-1", "ex:Paris")`, then `label` | raises until labelled, then exports |
| XGI | `remove_node_from_edge` + `add_node_to_edge` (same pair) | exact |
| XGI | `subhypergraph(...)`, then `derive` | exports; removals reported |
| XGI | `subhypergraph` on a `DiHypergraph` | unsupported (XGI raises `XGIError`) |
| XGI | `convert_labels_to_integers`, `dual()`, `cleanup()` (which relabels by default) | raises: ids rewritten, every membership unlabelled |
| HNX | `clone()`, then `derive` | exports; HyperNetX drops the isolated `ex:Mazarin`, which is reported |
| HNX | `restrict_to_edges(...)`, then `derive`; `remove_edges(["f:reg-1"])` | exports; removals reported |
| HNX | `remove_incidences([("f:reg-1", "ex:HeLa")])` | raises: a partial fact |
| HNX | `rename(nodes={"ex:HeLa": "ex:HeLa-cells"})` | exports; one record `moved` (injective) |
| HNX | `add_incidence("f:reg-1", "ex:Paris")`, then `label` | raises until labelled, then exports |
| HNX | `restrict_to_nodes(...)`, then `derive` | raises: partial facts |
| HNX | `collapse_nodes()`, then `derive` | raises |
| HNX | `sum(slice)`, then `derive` | exports; the isolated node is lost and reported |

**R03's library cases** run through the loaders with `validate="none"` (`r03_cases.py`). This is c00 (the KB
sample) plus c01–c26, 28 files.
- 22 round-trip exactly through XGI and HyperNetX, including absent against empty `attrs`, isolated nodes, empty
  edges, weights everywhere and mixed id types.
- 6 are refused by design: c04 `asc` (P007), c14 a directed file missing a direction (P010), c19 duplicate
  declarations (D001), c22 NaN (J004), and c16 and c23 integers beyond 2^53 (J006).

**The library-evidence test** is `tests/evidence/test_library_hif_io.py` (marker `evidence`, not the gate). It runs
the libraries' own HIF functions offline, with HyperNetX's schema download served from the vendored copy. It
writes `library-hif-evidence.json`, which the upstream issues attach.

| File | XGI `read_hif` → `write_hif` | HNX `from_hif` → `to_hif` |
|---|---|---|
| `fixture.hif.json` | `Hypergraph`; 59 → 56 records; 0 of 59 roles kept | `to_hif` returns `None`: `fillna("nil")` breaks mixed-direction files [DC §5.6] |
| directed slice | `DiHypergraph`; 52 → 51; 0 of 52 roles | 52 → 50 records; all 12 metadata keys lost; `default_attrs` added; the second generation is `None` |
| `role-convention/tail-head.hif.json` | 3 → 3; 0 of 3 roles | 3 → 2 (the repeated pair collapsed); `default_attrs` added |
| `role-convention/ordered.hif.json` | 4 → 3 (the repeated pair collapsed); 0 of 4 roles | 4 → 3 |

## 6. C2 store interface (`khg-store/1.0.0`)

The surface comes from [DC §6] (graft [J-cons], [J-std]) and the semantics from [DB §6]. The store checks
invariants and **never applies a policy** (ruling).

### 6.1 Protocol

```python
Record = dict[str, Any]
# a pattern binds one role: {"role": str, "value": Value | {"any": True} | {"any_unbound": True}, "position"?: int}
Pattern = dict[str, Any]

@dataclass(frozen=True)
class Where:
    status: frozenset[str] = frozenset({"asserted"})
    rank: frozenset[str] = frozenset({"preferred", "normal"})
    visibility: frozenset[str] = frozenset({"visible"})
    kinds: frozenset[str] = frozenset({"fact"})      # relation kinds: fact, lifecycle (rule in 1.1)
    as_of: str | None = None       # an instant [+-]YYYY-MM-DDThh:mm:ssZ (C011); None: no valid-time filter
    valid_mode: Literal["definite", "possible"] = "definite"
    as_at: str | None = None       # RFC 3339 transaction time; None: the latest versions

class Clock(Protocol):             # store.SystemClock; store.ScenarioClock(start, step) for the conformance suite
    def now(self) -> str: ...      # RFC 3339 UTC
    def tick(self) -> str: ...     # advance and return the new now()
    def set(self, at: str) -> None: ...

class Store(Protocol):
    # core: a backend implements these nine
    def info(self) -> StoreInfo: ...
    def put(self, records: Record | Sequence[Record], *, actor: str, at: str | None = None,
            expect: Mapping[str, int] | None = None) -> Receipt: ...
    def apply(self, event: Mapping, *, actor: str, at: str | None = None) -> Receipt: ...
    def load(self, container: Mapping | Iterable[Record], *, header: Mapping | None = None,
             at: str | None = None, on_missing: Literal["raise", "skip"] = "raise") -> LoadReport: ...
    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> Record | None: ...
    def history(self, id: str) -> list[Record]: ...
    def incident(self, node: str, *, role: str | None = None, relation: str | None = None,
                 where: Where = Where(), limit: int | None = None, after: str | None = None) -> list[Record]: ...
    def find(self, relation: str, pattern: Sequence[Pattern], *, match: Literal["at_least", "exact"] = "at_least",
             where: Where = Where(), limit: int | None = None, after: str | None = None) -> list[Record]: ...
    def iter_records(self, *, content: Literal["snapshot", "history"] = "snapshot",
                     as_at: str | None = None) -> Iterator[Record]: ...
    # derived: StoreBase implements these six from the core
    def get_many(self, ids: Iterable[str], *, as_at: str | None = None) -> dict[str, Record]: ...
    def degree(self, node: str, *, role: str | None = None, relation: str | None = None,
               where: Where = Where()) -> int: ...
    def find_by_key(self, relation: str, key: Sequence[Pattern], *, where: Where = Where()) -> list[Record]: ...
    def supersession_walk(self, id: str, *, direction: Literal["forward", "backward"] = "forward",
                          as_at: str | None = None) -> Walk: ...
    def export(self, format: Literal["khg-json", "khg-jsonl", "hif"] = "khg-jsonl", *,
               content: Literal["snapshot", "history"] = "snapshot", as_at: str | None = None,
               relations: Collection[str] | None = None, header: Mapping | None = None,
               literal_nodes: Literal["shared", "per_binding"] = "shared") -> str | dict: ...
    def close(self) -> None: ...

class StoreInfo(TypedDict):
    interface_version: str          # "khg-store/1.0.0"
    record_format: str              # "khg-record/1.0.0"
    capabilities: frozenset[str]
    store_id: str
    header: dict | None             # the kept document header (§6.2)
    contracts: dict[str, str]       # khg_contracts.CONTRACTS (§11)
class Receipt(TypedDict): records: list[tuple[str, int, str]]; at: str; warnings: list[dict]
    # records: (id, version, created | versioned | noop), sorted by id; warnings: [{code: "KHG-L008", ids}]
class LoadReport(TypedDict): records: int; versions: int; skipped: list[str]; seconds: float
class Walk(TypedDict): start: str; direction: str; steps: list[dict]; terminal: list[dict]
    # steps: {depth, via, reason, from, to}; terminal: [{id, status}]
```

**Errors** carry `.codes` and `.info`:
- `ValidationError` (layers C and S, and D002, D008, D010 and D020 on writes);
- `KeyCollision` (D016; `info.collisions`, §2.5);
- `VersionError` (D011–D014, D018);
- `ConcurrencyError` (D019);
- `NotFound`;
- `CapabilityMissing(flag)`.

`find_by_key` raises `ValueError` when `key` does not bind exactly the key roles (critique CONS-25).

### 6.2 Semantics, events and header state

**`put`** is all or nothing:
1. It validates every record: the C and S layers, and the references (D002, D020).
2. It classifies each record.
   - A new id becomes version 1 in status `asserted`, `quoted` or `goal`. `candidate` is D017; other statuses and
     lifecycle records are D014.
   - A record whose content equals the current version is a no-op.
   - Any other record becomes a new version under the version rule (D013). A status change is D014.
3. It checks the post-state:
   - nesting cycles (D008);
   - the key invariant and the disputed-key rule (`KeyCollision`);
   - the constraints of any supersession that binds a new version (D011).
4. It writes every record at one `recorded_at`. `at` pins it forward only (D018).

`expect {id: version}` gives optimistic concurrency (D019). The receipt lists possible-overlap warnings (L008).

**`load`** is trusted bulk import (graft [J-cons]).
- It takes a container, or an iterable of records whose first item is the header, so `.khg.jsonl` streams
  [R01 PF-28]. An iterable without a header line needs `header=`.
- It keeps the store fields and checks only V001 and D018, so P1 times the backend, not the validator.
- `on_missing="skip"` loads what the flags allow. It skips the records that need a missing flag, and the records
  that reference skipped ones, and lists them in `LoadReport.skipped` (critique CONS-05).

**Header state** (critique STORE-HEADER).
- `load` keeps the container's header, minus `content` and `as_at`, as the store's document header. `info()`
  returns it.
- `export(header=...)` overrides it.
- A store without a kept header exports `document_id` `"store:<store_id>"`, the schema's reference, and a
  `complete` computed by the D002 rule (S-EXP-009).
- Every backend keeps a one-row metadata table or graph for the header.

**Reads.**
- The defaults are status `{asserted}`, rank `{preferred, normal}`, visibility `{visible}` and kinds `{fact}`,
  with **no valid-time filter** and the latest versions. This is a ruling: R01 D-16's "as of now" would hide
  historical facts.
- `as_at` picks versions; then `as_of` tests their validity with the table of §2.6. `get` ignores `Where`.
- **`incident(node)`** returns each hyperedge where the node (an entity or a fact) is a value, once per fact.
  Literals and vocabulary ids are not nodes.
- **`find` with `at_least`** matches the pattern's (role, position, value) multiset injectively, so two `agent`
  patterns need two `agent` bindings.
  - **`exact`** needs equal multisets.
  - A pattern without `position` matches any position.
  - `{"any": true}` matches any value, and `{"any_unbound": true}` matches unbound slots.
  - `pattern=[]` lists every fact of the relation, paginated (S-READ-018).
- **`find_by_key`** binds exactly the key roles. Values compare by identity (§2.3).
- **Ordering:** every list is in code-point id order, with `limit`/`after` keyset pagination.
- **`degree`** equals `len(incident)`.
- **`iter_records` and `export`** include every status.
- **`supersession_walk`** is breadth-first over asserted `khg:supersedes` records at `as_at`. It returns steps
  `{depth, via, reason, from, to}` and `terminal`: the facts reached that have no outgoing asserted supersession,
  with their status (critique SEM-11). It branches on conflation and always ends.
- **Deletion:** nothing is deleted [R01 D-17].

| Event (`apply`) | Fields | Effect |
|---|---|---|
| `supersede` | `id`, `superseded`, `superseding?`, `records?`, `reason`, `note?`, `evidence` | Writes `records` (asserted) and the `khg:supersedes` record `id`, which binds the superseding facts (existing, then new), then the superseded ones. Each superseded fact gets a version with status `superseded` and `status_ref: id`. The superseded facts must be asserted or disputed, and the superseding facts asserted, with the reason's constraint (D011) |
| `transition` | `targets`, `to`, `id?`, `records?`, `reason?`, `note?`, `evidence`, `resolve_superseding?`, `dispute_id?` | Follows §2.7. **`disputed`:** the targets are asserted or disputed, `records` are written as disputed, and a new `khg:disputes` record `id` binds them all. **`retracted`:** needs `id` (C010) and writes a `khg:retracts` record; a lifecycle target means undo. **`asserted`:** from `disputed`, `quoted` or `goal`; drops `status_ref` and the `goal` block |
| `end_validity` | `target`, `end`, `end_cause?`, `evidence` | Adds or refines the end binding, or replaces a `novalue` end. `end_cause` becomes a `khg:end_cause` binding. The status is unchanged (F7) |
| `add_evidence` | `target`, `evidence` | Appends evidence. Superseded and retracted facts are frozen (D013) |

The checks run in this order: capability, `NotFound`, D014, record validation, references and pointers, D008,
D016 with the disputed-key rule, D011, D012, D018.

### 6.3 Capability flags and the reference store

A missing flag makes the method raise `CapabilityMissing`, and makes the scenarios that need it `inapplicable`,
never `passed` [R04 §9.3].

Without any flag, a store offers entity values, single-record `put`, `get`, `history`, `incident`, `find`,
`find_by_key`, `degree`, snapshot `load` and `export`, and `add_evidence`. It stores lifecycle records, but the
events that write them need `atomic_writes`.

| Flag | Covers |
|---|---|
| `literal_values`, `special_values` | literal bindings compared by value identity; `somevalue` and `novalue` |
| `goals` | status `goal`, `unbound` values and patterns |
| `nesting` | fact values in fact relations; `incident(fact id)` |
| `ordered_roles` | positions |
| `valid_time` | `as_of`, `valid_mode`, `end_validity`, temporal keys |
| `transaction_time` | `as_at`, `get(version=)` |
| `key_constraint` | the key invariant on writes |
| `atomic_writes` | multi-record calls (a batch, `supersede`, a transition that writes a record), all or nothing; without the flag they raise |
| `history_export` | `content="history"` in `iter_records`, `export` and `load` |

**The reference store and helpers.**
- `MemoryStore(schema, *, clock=None, capabilities=None, store_id="memory")` holds a version list per id. It
  indexes node → facts, (relation, key_digest) → facts, and `status_ref`. With `capabilities=None` it has every
  flag; a set of flags limits it, for the capability-limited runs.
- `memory_factory(schema, clock)` returns `MemoryStore(schema, clock=clock)`. It is the factory that
  `conformance.run`, `replay` and `khg-conformance` take for the reference store.
- `StoreBase` derives the six derived methods.
- `Timed(store)` records (method, args digest, ns, result size) for P1. The args digest is
  `digest("khg-timed/1", args)`, with frozensets as sorted lists and `Where` as its field dict.
- `compare_containers(a, b, *, ignore=("version", "recorded_at", "recorded_by"),
  header_ignore=("created_at", "generator"))` returns the structural differences. Headers are compared, and
  records are keyed by id in snapshots and by (id, version) in history containers (critique CONS-05, GL-04).

### 6.4 Conformance suite (`khg-scenario/1.0.0`)

The suite is declarative [R04 O13]. It is 114 files plus `index.json` in `design-examples/conformance-scenarios/`,
packaged under `khg_contracts/data/` (§10). `conformance.run(factory, *, only=None, capabilities=None)` runs them,
and so does the `khg-conformance` CLI. `factory(schema, clock)` returns an empty store. The result is an
EARL-shaped report: `passed`, `failed`, `inapplicable` or `cantTell` per scenario.

| Field | Meaning |
|---|---|
| `requires` | capability flags, computed by the generator. It holds the flags of the operations and assertions under test (`valid_time` for `as_of`, `valid_mode` or `end_validity`; `transaction_time` for `as_at` or `get(version=)`; `history_export`; `atomic_writes` for a multi-record write), plus the data flags of the records written or loaded |
| `given` | `{"put": [...], "at"?}`, `{"apply": event, "at"?}` or `{"load": "@fixture" \| "@fixture[core]"}`. A store without `atomic_writes` gets one call per record |
| `when` | `[{op, args, at?, then}]`, where `then` is `{select, equals}`, `{error, info?}` (info matches as a subset), `{container_equals, ignore}`, `{hif_valid, equals_file, ignore}`, `{reload_equal}` or `{deterministic}` |
| `precedent` | the [DA], [DB] or [DC] scenarios it absorbs, or the critique finding it answers |

Records are referenced as `"@f:reg-1"`, `"@entities"`, `"@fixture"` or `"@fixture[core]"`, or as `{"@": id, set,
drop, set_binding, drop_bindings, add_evidence, set_evidence}`. `@fixture[core]` is the fixture without the four
records that need `ordered_roles`, `special_values` or `goals`. The clock starts at 2026-10-01T00:00:00Z and ticks
1 s per write; a step's `at` sets it. `derived.*` selections are computed by the runner from the returned record,
because `derived` is an optional cache (critique CONS-24).

| Group | Scenarios | Topics |
|---|---|---|
| S-PUT | 10 | idempotence, atomic batches, candidates, codes surfaced, `expect`, unbound, status via put, references, a redirected entity (D020) |
| S-VER | 9 + 1 core | `as_at`, `add_evidence`, refinement versus core change (the Bob-for-Alice probe), evidence immutability, the transition table, `somevalue` refinement, entity versions, `end_validity` on a `novalue` end with `end_cause` |
| S-READ | 19 + 14 core | `incident` order and completeness, two roles on one node, defaults, nesting, pagination, `degree`, `find` modes and patterns, literals and calendars, positions, goals, `novalue`, `get`, `get_many`, timeless relations under `as_of`, empty patterns, vocabulary ids |
| S-TIME | 12 + 1 core | `as_of`, `as_at` with the walk, definite versus possible, undated, `until` and `ended` facts, `end_validity`, Julian dates, centuries, millennia, decades, a BCE Julian date |
| S-KEY | 19 + 2 core | atomic `KeyCollision` with shapes, classes and actions; timelines; preferred beside normal; deprecated facts; `close_older` (succession and backfill); same start; merge; dispute and the disputed-key rule; year handover; undated facts; specials in keys; a batch across two relations; exact key literals |
| S-LIFE | 14 | supersede; backward walk; conflation; superseding facts asserted; retraction; undo; keyed undo resolved by a dispute; goals; a chain A → B → C; D011 on a put |
| S-EXP | 11 + 2 core | round trips with the header; HIF equality; `as_at` and history export; the slice; a closed slice of `claims`; determinism; transaction order across ids; a store's own document id |

The 20 core variants (id suffix `c`) re-run the fixture-loading read and export scenarios on `@fixture[core]`. A
backend without goals, ordered roles or special values then still has its reads checked (critique CONS-05).

The suite absorbs [DA]'s scenarios C2-01…27, [DC]'s 18 and [DB]'s 4 (graft [J-cons], [J-std]).

**Executed** (`run_scenarios.py`):
- All 114 pass on the prototype store.
- With any single flag removed, every scenario is `passed` or `inapplicable`. The same holds with no flag (12
  apply).

### 6.5 How P1's backends implement C2 [DC §6.8]

| Backend | Layout | Flags lacking natively | Scenarios that apply |
|---|---|---|---|
| Incidence table (PostgreSQL 18, SQLite, DuckDB) | `fact_version`, `binding` (typed literal columns plus window columns from `derived.valid_time`), `entity`, a lifecycle index and a one-row `document` table. A database constraint can state only the part of D016 that holds for every legal state: the definite windows of the current, asserted, **preferred** facts on one key never overlap. It is `EXCLUDE USING gist (relation WITH =, key_digest WITH =, int8range(valid_from, valid_to) WITH &&)` over those facts' instants in seconds, or in PostgreSQL 18 `PRIMARY KEY (relation, key_digest, valid WITHOUT OVERLAPS)`; both need `btree_gist` for the text columns. The rest of D016 (a preferred fact beside normal ones, the disputed-key rule) stays in code: over every fact the constraint would refuse legal states. Ids sort in code-point order (collation `C`) (A1) | none | 114 |
| Reified RDF 1.2 (`project.rdf_relation_instance`) | one fact node plus one node per binding, named graphs per version, and the header in the default graph | none with named graphs per version; `transaction_time` and `history_export` without them (A2) | 114 with named graphs per version; 107 without (A2) |
| Bipartite property graph | `(:Fact)-[:BINDS {bid, role, position, direction}]->(...)`, an indexed `key_digest`, and a `(:Document)` node. This layout has no version nodes; `(:Version)-[:VERSION_OF]->(:Node)`, with bindings pointing at identity nodes, keeps transaction time (A3) | none with version nodes; `transaction_time` and `history_export` without them (A3) | 114 with version nodes; 107 without (A3) |
| TypeDB 3.x | relations with scoped role names, literals as owned attributes; P1 owns the mapping rules. A relation left without role players is deleted at commit, a repeated player in one role collapses, bids and positions have no home, and an instance has one type (A4) | `ordered_roles`, `special_values`, `goals`, `transaction_time`, `history_export` | 70 (find 5 of 13, incident 13 of 24, export 3 of 11) |
| HIF | `from_hif` into a `MemoryStore` | `transaction_time`, `history_export` | 107 |

**Amendments from P1 research 01 (2026-09-25).** §6.5 is informative; these four rows were corrected from
[P1 research 01](../p1-store-bakeoff/research/01-backends.md) §11, where every backend was probed in P1's container.
- **A1.** `tstzrange` cannot hold dates before 4713 BC, so the key ranges are `int8range` (or `numrange`) over the
  instants in seconds. PostgreSQL 16 and 18 both refused an overlapping copy of `f:king-14` with the `EXCLUDE` form,
  and 18 with `WITHOUT OVERLAPS`. A PostgreSQL column under an ICU collation sorts ids out of code-point order, so
  the database uses `C` (§2.3, §7; probes `sql_incidence.py`, `ordering_probe.py`).
  - *Corrected after P1's build and review 01 (R-11, R-05).* The constraint covers the current asserted
    **preferred** facts only. Over every asserted fact it refuses legal D016 states, such as a preferred fact
    beside two overlapping normal ones, and code cannot relax a database constraint. The rest of D016 stays in code
    ([P1 IMPLEMENTATION-NOTES §3](../p1-store-bakeoff/IMPLEMENTATION-NOTES.md), the key guard).
  - A write changes the guard rows once, at its end, so a batch that moves `preferred` from one fact to another is
    accepted in any order.
  - Code-point order needs more than a `C` database: an ICU cluster gives a database created with `LOCALE 'C'` the
    ICU provider. P1 puts `COLLATE "C"` on every text column and creates its database with
    `LOCALE_PROVIDER libc`.
- **A2.** With a named graph per version, the RDF layout answered 85 of 85 transaction-time checks and all 46
  read-only scenarios. The row's own layout therefore keeps `transaction_time` and `history_export`, and 107 is the
  count for a layout without named graphs (§3; probe `rdf_relation_instance.py`).
- **A3.** With version nodes pointing at identity nodes, the property-graph layout answered the same 85 checks, so
  114 apply (§4; probe `pg_cypher.py`).
- **A4.** The reasons behind TypeDB's gaps were probed in TypeDB CE 3.13.6 (§5.2, §5.5; probes `typedb_features.py`,
  `typedb_lists.py`, `typedb_probe.py`). The figure 70 stands.
  - *Added after P1's build (review 01, R-11).* A relation type that relates no role cannot even be defined
    (`[SVL41] Non abstract relation type … must relate at least one role`). A literal-only relation therefore has no
    TypeQL form at all, which is stronger than "a relation left without role players is deleted at commit"; its
    facts are refused ([P1 IMPLEMENTATION-NOTES §3, §5](../p1-store-bakeoff/IMPLEMENTATION-NOTES.md)).

P1's adapters since measured 114 of 114 on SQLite, PostgreSQL 18.6, Oxigraph and Neo4j, 70 on TypeDB and 107 on HIF
([P1 results](../p1-store-bakeoff/results/conformance/summary.md)).

## 7. C3 candidate queue and action log (`khg-queue/1.0.0`)

A queue file is append-only JSONL, one per (run, order) (graft [J-cons], [J-std]). There is **one appender at a
time**, and every actor appends through a `Queue` handle (critique CONS-23). An item's state is a fold over the
log; items are never edited (F9). Ids are scoped by the queue: `q:`, `l:` and `cand:<queue_id>.<seq>`.

Line 1 is `{"kind": "queue-header", "format": "khg-queue/1.0.0", "queue_id", "record_format", "schema": {id,
version, sha256}, "base"?: {document_id, sha256}, "created_at"}`. `base` names the container that replay and
lint load first. Its `sha256` is `record.container_sha256`: the plain SHA-256 of the container's canonical
`.khg.jsonl` text (the header line, then the records in canonical order). A mismatch is Q012 (critique
G3-ACCEPT-REPLAY).

| Item field | Req. | Meaning |
|---|---|---|
| `kind`, `qid`, `item_kind` | yes | `"queue-item"`; `hyperedge` in v1. The proposal kinds (`merge_proposal`, `supersession_proposal`, `validity_proposal`) come in 1.1 (Q003) |
| `submitted_at`, `submitted_by` | yes | `"<agent>/<version>"` |
| `run`, `doc` | yes (Q001) | `{run_id, order_id, position, seed?, temperature?, model?, prompt_id?, skill_id?}`; `{doc_id, doc_sha256}`, which the extracted evidence cites (Q009) |
| `payload` | yes | a C1 hyperedge with status `candidate` and id `cand:…` (Q002). Its extracted and inferred evidence carries `event_hash` (§2.9) |
| `keys` | yes | `{content_key, core_key, key_digest}` of the payload read as asserted (Q010) |
| `entities` | no | C1 entity records the payload needs, written with the fact on accept (critique CONS-10) |

**States.** `pending` goes to `linted`, `needs_review` or `rejected`. `linted` goes to `accepted`, `rejected` or
`needs_review`. `needs_review` goes to `accepted` or `rejected`. Any open state can go to `withdrawn`. A wrong
`state_before` is Q005.

| Log entry field | Req. | Meaning |
|---|---|---|
| `kind`, `lid`, `parent`, `target` | yes | `"log-entry"`; the previous entry for the item, or null (Q007); the qid |
| `action`, `state_before`, `state_after` | yes | v1 actions: `lint`, `accept`, `reject`, `flag`, `verdict` (state unchanged) and `withdraw`. `merge` and `auto_fix` come in 1.1 (Q003) |
| `actor`, `mode`, `at` | yes | `{type: agent \| linter \| person \| system, id, version?}`; `automatic`, `manual` or `semi_automatic` |
| `rule_set`, `findings`, `outcome` | on `lint` (Q004) | findings `[{code, severity, path, message}]`; outcome `pass`, `warn` or `fail` |
| `reason` | on `accept`, `reject`, `flag`, `withdraw` | why |
| `before`, `after`, `decision_hash` | on `accept` | `[{id, version}]` read and written, and the hash below |
| `verdict` | on `verdict` | `{evidence_id, core_key, event_hash, label, bindings: [{role, position, value, bid?, label, should_be_role?}], missing, note?}` |

**`decision_hash`** (critique GL-11, CONS-23) is
`digest("khg-decision/1", [{id, version, record: decision_view(v)}])` over the written versions, sorted by id.
`decision_view(v)` is the canonical record without the store-assigned fields: `version`, `recorded_at`,
`recorded_by`, evidence `recorded_at` and `derived`. `event_hash` stays in, because it is content fixed at
extraction (§2.9). The clock therefore never changes the hash.

**Verdicts** are per (candidate, evidence) pair [R04 O9], **keyed by (`core_key`, `event_hash`)** (ruling), so they
carry over to a re-extraction.
- Per-binding labels name a binding by its content tuple (role, position, canonical value), the element that
  `content_key` hashes. The bid is only a hint, because writers assign bids (critique CONS-18).
- The labels are `correct`, `no_relation`, `wrong_relation`, `wrong_role`, `wrong_filler`, `span_boundary`,
  `missing_participant`, `extra_participant`, `negated`, `hypothesis` and `other`. They aggregate as in [DB §7.3].

**The API** (`khg_contracts.queue`):
- `Queue.create(path, *, queue_id, schema, base=None, created_at=None)` and `Queue.open(path, *, schema)`.
- `make_candidate(record, *, queue_id, seq, schema)`. It sets `cand:<queue_id>.<seq>` and status `candidate`,
  assigns missing bids b1… in listed order, and stamps `event_hash`.
- `Queue.submit(payload, *, run, doc, submitted_by, entities=(), at=None) -> qid`, which computes `keys`.
- `Linter(schema, *, store=None, entities=None, doc_texts=None).lint(queue, qid, *, at=None) -> LogEntry`.
- `Queue.accept(qid, *, store, id, actor, reason, at=None) -> LogEntry`.
  - The stored record is the payload with `id` replaced and `status` set to `asserted`. Nothing else changes.
  - It is written in one atomic `put` with the item's `entities`, at `at`, which is also the entry's `at`.
- `Queue.reject`, `flag`, `verdict` and `withdraw`, which take `(qid, *, actor, reason | verdict, at=None)`.
- `replay(path, *, schema, factory, base=None) -> dict`.
  - It builds a fresh store and loads `base`, which must match the header's `base` (Q012).
  - It re-runs every `accept` in log order at its `at`, and checks `after` and `decision_hash` (Q006).
- `queue_items(paths) -> Iterator[dict]`: items with their folded state and verdicts, for the scorers.

**The linter's v1 rule set is `structural`**, which is store-free and is the gate's lint:
- the C and S codes on the payload, with S003 as a warning on candidates;
- Q001–Q003, Q009, Q010 and Q011.

Entities resolve from `item.entities` first, then from `Linter(entities=...)` or the queue's base, then from the
store. S005 runs only on resolved entities, and an unresolved entity is Q011, an error (critique CONS-10). The
identity and quality rule sets (L001–L009, L101–L110) come in 1.1 (critique SCOPE-F13).

**Examples**, validated (§1.4). The item's payload is the fixture's `f:king-14` as a candidate, with its keys
recomputed:

```json
{
 "kind": "queue-item",
 "qid": "q:p2-smoke.000001",
 "item_kind": "hyperedge",
 "submitted_at": "2026-10-01T00:00:03Z",
 "submitted_by": "p2-fixture-extractor/0.0.1",
 "run": {"run_id": "fixture-run-1", "order_id": "o1", "position": 0, "seed": 0, "temperature": 0},
 "doc": {"doc_id": "doc:louis-bio", "doc_sha256": "sha256:56940b729460cb9a75d5d63ab1f907a502fef80530b4aabff2cd8e9c28a44b2f"},
 "payload": {
  "kind": "hyperedge",
  "id": "cand:p2-smoke.000001",
  "relation": "position_held",
  "status": "candidate",
  "bindings": [
   {"bid": "b4", "role": "end_time", "value": {"literal": {"datatype": "time", "time": "+1715-09-01T00:00:00Z", "precision": 11, "calendar": "gregorian"}}},
   {"bid": "b1", "role": "holder", "value": {"entity": "ex:LouisXIV"}},
   {"bid": "b2", "role": "position", "value": {"entity": "ex:KingOfFrance"}},
   {"bid": "b5", "role": "replaces", "value": {"entity": "ex:LouisXIII"}},
   {"bid": "b3", "role": "start_time", "value": {"literal": {"datatype": "time", "time": "+1643-05-14T00:00:00Z", "precision": 11, "calendar": "gregorian"}}}
  ],
  "evidence": [
   {"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:regnal-list"}, "supports": ["b1", "b2", "b3", "b4"]},
   {"id": "e2", "type": "extracted", "mode": "automatic", "source": {"doc_id": "doc:louis-bio", "doc_sha256": "sha256:56940b729460cb9a75d5d63ab1f907a502fef80530b4aabff2cd8e9c28a44b2f"}, "selectors": [{"type": "quote", "exact": "Louis XIV succeeded his father Louis XIII", "prefix": "", "suffix": " as King of "}, {"type": "position", "start": 0, "end": 41}], "activity": {"agent": "p2-fixture-extractor", "agent_version": "0.0.1", "model": "none", "run_id": "fixture-run-1"}, "supports": ["b1", "b5"], "event_hash": "sha256:87eaf6a24f9088334f463104155187b658be6cb501f09fd6acfe8641a987b18d"}
  ],
  "rank": "normal",
  "visibility": "visible"
 },
 "keys": {"content_key": "sha256:2706f2b5162301565965492815a53ac7f16064ea742b03756cadbbafefd9d76b", "core_key": "sha256:5779b98f13640fbf96488b9834c5ce7e10f02902541882a23c2d43f84f93e916", "key_digest": "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96"}
}
```

The accept entry follows a passing lint entry; all four lines are in `smoke-queue.khg-queue.jsonl`, whose header
names `base` `{"document_id": "p2-smoke-base", "sha256": "sha256:f7933d12…cb6a"}`. It writes `f:king-14` version
1, equal to the fixture record:

```json
{
 "kind": "log-entry",
 "lid": "l:p2-smoke.000002",
 "parent": "l:p2-smoke.000001",
 "target": "q:p2-smoke.000001",
 "action": "accept",
 "state_before": "linted",
 "state_after": "accepted",
 "actor": {"type": "person", "id": "curator:smoke"},
 "mode": "manual",
 "at": "2026-10-01T00:00:07Z",
 "reason": "the regnal list and the biography sentence support every binding",
 "before": [],
 "after": [{"id": "f:king-14", "version": 1}],
 "decision_hash": "sha256:518db0f4a88cffe427846b412c99d755945c35816fc3c5e83d31c2ea30807f29"
}
```

## 8. Validator and the malformed-case list

### 8.1 Layers, pipelines and stable codes

| Layer | Checks | Inputs |
|---|---|---|
| J | strict parse: duplicate keys, NaN and ±Infinity, a BOM, lone surrogates, integers beyond ±(2^53−1) [DA §8.1], a top level that is not an object | all |
| V | the version gate: `format` or `khg-profile` selects the schemas | all but role-convention files |
| H | the vendored HIF schema, unchanged (F2) | HIF |
| R | role-convention 1.0.0, rules 1–4 (§4.1) | HIF |
| P | `khg-hif-1.0.0.schema.json` (`allOf` the vendored `$id`) plus Python profile checks | HIF with the profile |
| D | decoding, cross-record, container, history and store rules (Python) | HIF, C1, store |
| C | `khg-record-1.0.0.schema.json` | C1, payloads |
| S | a record against its relation-type schema (Python) | C1, payloads |
| M | the relation-schema meta-schema plus Python checks | schemas |
| Q | the queue structure, the state fold, keys, entity resolution, base and replay | queues |
| I | `khg-c4-items-0.2.0.schema.json` (it reads 0.1.x files too), embedded C1, memory gold | C4 items |
| L, F | lints, which never invalidate a file (v1 ships L008); migration report entries (v1 ships F006 and F015–F017) | |

**Pipelines** (critique GL-02, SEM-03):

| Input kind | Layers, in order |
|---|---|
| C1 container or record | J V C S D |
| HIF with the profile | J V H R P D C S. D first runs as decoding; the cross-record D checks run after S |
| role-convention file | J H R |
| relation-type schema | J V M |
| queue | J V Q C S D (C and S run on the payloads) |
| C4 items | J V I. Embedded C1 findings are reported nested under I003 |

- A finding's **layer is the letter of its code.** A step may emit another layer's code: decoding emits S016, and
  the S pass emits D002.
- The **first rejecting layer** of an input is the earliest letter, in its kind's pipeline order, among its error
  findings.
- A J or V failure stops the run. `validate_hif` on a file without `khg-profile` passes V and reports P001.

`validate(obj_or_path, *, kind="auto", schema=None, doc_texts=None, bases=None, engine="jsonschema") -> {ok,
findings: [{code, severity, layer, path, message}]}` has the wrappers `validate_record`, `validate_container`,
`validate_hif`, `validate_queue` and `validate_item` (§10.2).

**Engines, offline** (critique GL-10, ENGINES). `validate/engines.py` gives both engines closed resolvers. It
never embeds the vendored schema, because one hash-checked copy is simpler.
- **jsonschema:** a `referencing.Registry` preloaded with every packaged schema under its `$id`. The vendored HIF
  schema is under its https `$id` and ours are under `tag:` ids. `retrieve` raises.
- **fastjsonschema:** handlers for `http`, `https` and `tag` that serve only packaged schemas and raise on
  anything else.
- Every `$ref` in a packaged schema is absolute. fastjsonschema cannot join a relative ref against a `tag:` base.
- A test compiles every packaged schema under both engines with sockets blocked. A `$ref` to anything else fails
  closed.

**Stable codes** follow [DB §8.1] (graft [J-impl]):
- Every constraint-bearing subschema carries `x-khg-code`: a code, or a map from keyword to code. The
  generator propagates codes to every constraint, so jsonschema (from `error.schema`) and fastjsonschema (from
  `exception.definition`) both name the code.
- if/then dispatch replaces `oneOf` and `anyOf`.
- An H table keyed on (keyword, instance path) covers the vendored schema, which carries no annotations.
- A coverage test checks that every constraint has a code.

**Engine agreement** is defined on single-fault inputs (critique ENGINES). fastjsonschema stops at its first error,
so on each malformed case it must return exactly one code at the first rejecting step, and that code must be among
jsonschema's. G2 runs with jsonschema, which gives the full report. The prototype checked containment on all 180
cases.

**The registry** is `design-examples/error-codes.json` (`khg-codes/1.0.0`).
- It registers 134 codes. 128 are active; 6 are reserved and never emitted (D004, D006, S008, S012, and P006 and
  P015, which moved to R001 and R004 before 1.0).
- Each code has a layer, a severity, a status, a meaning and the A, B and C codes it merges.
- The file also lists the pipelines and the layer rule.
- 31 **planned** codes of later versions are listed apart and **not registered**, so 1.0 does not freeze them
  (critique SCOPE-F13): S017, L001–L007, L009, L101–L108, L110, and F001–F005 and F007–F014.
- Codes are never reused, and messages are not part of the contract.

### 8.2 The malformed-case list for v1

`design-examples/malformed-cases.json` (`khg-malformed-cases/1.0.0`) holds 180 cases. Each case has:
- `id`, `description`, `layer`, `code`, `kind` and `source`;
- either `input_text` (layer J) or a `base` file plus an RFC 6902 `patch`. Queue and C4 patches address
  `/lines/<n>`;
- optionally a `schema_patch` (RFC 6902 on `fixture.relation-schema.json`; the harness re-stamps the base's schema
  digest so that D009 does not fire), a `doc_text` and an `expect_target`.

`expect_target` pins what each indexed patch path points at in the base: a record id, an incidence as (edge,
bid), a node or edge id, a relation id, or a line's kind and id. A regenerated fixture therefore cannot silently
shift a patch (critique PACKAGE-DATA).

**A case passes** when its first rejecting layer (§8.1) is the listed layer and the listed code is among its error
codes (critique GL-01, GL-02, SEM-02, SEM-03, G2-CASES-NOT-EXECUTABLE). **Harness self-checks:**
- every patch applies;
- the input differs from its base;
- every `expect_target` resolves;
- every unpatched base validates with no error finding.

All of this ran mechanically in the prototype (`make_malformed.py`): 180 of 180 pass, and engine containment holds
on all 180.

| Layer | Cases | Codes | Sources |
|---|---|---|---|
| J / V / H | 8 / 2 / 15 | all | R02 cases 04–06, 10–14, 18–20, 22, 26, 31, 34–36; R01 V01–V05, V19, V41; R03 c22, c23 |
| R | 6 | R001–R004 | R01 V07–V11 (as ruled); rule 4 |
| P | 24 | all 15 active | R01 V07, V12, V14, V20, V40; R02 cases 15–17, 21, 23; R03 D4, D7, D8, c04, c14, c20; §4.5; the 518 boundary (GL-16); CONS-14, CONS-15 |
| D | 30 | 17 of 18 active (D019 is covered by S-PUT-006) | R01 V15–V18, V28, V37, V41, V42, D-09; R02 cases 28–29; R03 c19; SEM-18 cases 1–6; SEM-16; four history-container cases (D013 ×2, D014, D018) |
| C / S | 20 / 34 | all active | R01 V14, V15, V21–V27, V29, V30, V32–V38, V47; R03 c13; F11 spans (`doc_text`); year 0 and the 1583 rule; SEM-18 case 7 |
| M / Q / I | 19 / 17 / 5 | all active / all / all | R01 V43–V49; M015 now carries the old `violation` severity; M017; Q010 now carries the old event-hash case; Q011, Q012; the C4 items of `c4-items.jsonl` |

Store-only rules are not in the list. They are scenarios (S-VER-003/004/005, S-EXP-008 and S-EXP-010), and the
history-container cases cover their codes in files. The rule-relation case of the previous list moved to 1.1 with
rule relations. **All 49 R01 candidates are covered or ruled out:**
- V06 is covered through R02 cases 18–20;
- V10 and V11 are the exact-duplicate case (R002);
- V13 is ruled out, because native directions stay in undirected files (§4.2);
- V31 is D018 (MC139);
- V39 (rule relations) moves to 1.1.

L and F codes are tested by the store receipts and by the migration test.

### 8.3 The adversarial gate fixture (R01 D-20)

- **A node in two roles, including tail and head:** `f:reg-1` (TP53) and `f:loop-yyz` (YYZ).
- **A repeated role:** `agent` in `f:coadmin-1`, `spouse` in `f:married-curie`, `name` in `f:station-東京`.
- **An ordered role:** `f:route-1`, with YYZ at positions 1 and 3.
- **Typed literals:** all seven datatypes and quantity bounds in `f:station-東京`; a year in
  `f:pop-łódź-2019`; a Julian year in `f:claim-1`.
- **A nested reference:** `f:claim-1` points to `f:born-louis14-paris`, which is `quoted`.
- **Direction and qualifiers:** usage directions; the undirected relations `married` and `flies_between`;
  `context`, `replaces` and `point_in_time`.
- **Evidence on a binding:** `f:king-14` e2 supports only b1 and b5.
- **Non-ASCII:** `ex:Łódź`, `ex:東京駅`, `ex:Chronicler_Ødegård`, and a span after an astral-plane character.
- **`somevalue` and `novalue`:** `f:born-scribe` and `f:cat-7`.
- **An unbound goal slot:** `g:who-1774`.
- **A superseded pair:** `f:born-skłodowska-kraków` is superseded by `…-warszawa` via `m:sup-1`.
- **Beyond D-20:**
  - adjacent temporal keys (`f:king-13`, `f:king-14`), which also give the L008 warning;
  - a deprecated alternative with a `rank_reason` list;
  - fact and evidence confidence, and a `must_differ` warning;
  - stored event hashes;
  - **weights** on a node, two edges and an incidence (GL-05);
  - **nested binding extensions** (GL-07);
  - an **isolated entity**, `ex:Mazarin` (GL-08).
- **Companion files:**
  - `fixture.history.c1.json`: two versions of `f:king-13`, and `f:reg-1` retracted by `m:ret-1`;
  - `fixture.doc-texts.json`: the four document texts and their hashes;
  - `smoke-base.c1.json`: the entities, as G3's base.

## 9. C5 scorers (`khg-scorers/1.0.0`), the C4 draft and the output schema

### 9.1 Conventions [R05 §1; DB §9.1]

- **Deterministic by default.** No scorer calls an LLM. LLM judges are named adapters (D-C5-13, D-C5-16).
- **Values match by value identity** (§2.3).
  - Entities match by id, after following `redirect_to` (`record.resolve_redirects`).
  - Literals match under `truncate_to_gold`, which is value refinement (⊑); the preset rule `exact` is value
    identity. Both compare Gregorian windows, whatever the calendars (§2.3). An extractor that cannot know the
    calendar is scored with `calendar="as_written"`, which reads its dates in the gold's calendar (critique
    CONS-12).
  - `somevalue` and `novalue` match only themselves.
- **Empty sets** give the flags `no_predictions`, `no_gold` and `both_empty` [R05 §1 item 3].
- **Three averages.** Micro over the scoring units, macro over relations, and macro over the arity bins
  (§2.4). Recall is binned by gold arity and precision by predicted arity.
  - Every per-arity table is given twice: on `arity` (the C1 rule) and on `model_arity`, the bindings that the
    literal-free projection keeps (critique CONS-06).
- **Per-item outputs** are keyed by stable ids. Each lists `depends_on`, the gold fact ids it rests on, so P8 can
  join the four abilities per fact (critique CONS-07; [R05 §1 item 6]).
- **Stamps.** Every report carries `khg_contracts.CONTRACTS` (§11), the scorer configuration, the C4 `qset`, the
  schema reference, and `khg-render/1` where text was rendered.
- **Dispersion** is a percentile bootstrap: 1,000 resamples, seed 0, 95 % (critique C5-IO). The procedure is
  fixed:
  - `rng = random.Random(seed)`; each resample draws n indices as `int(rng.random() * n)`;
  - the interval is the sorted resample means at positions ⌊0.025·R⌋ and ⌊0.975·R⌋ − 1;
  - the paired bootstrap reuses one index sequence for both systems.
  Python guarantees the sequence of `random()` across versions, but not that of `choices()`. On
  `[0, 1, 1, 0, 1, 1, 1, 0, 1, 1]` the interval is [0.4, 1.0].
- **Hungarian alignment** is pure Python. Ties break by lexicographic fact ids. SciPy (`[fast]`) is optional and
  must give the same assignment.

### 9.2 API

```python
from khg_contracts.scorers import completion, extraction, memory, retrieval, stability

@dataclass(frozen=True)
class Bootstrap:
    resamples: int = 1000; seed: int = 0; alpha: float = 0.05

@dataclass(frozen=True)
class ExtractionConfig:
    preset: Literal["hyperred_quintuplet", "text2nkg"] | None = None
    literal_match: Literal["truncate_to_gold", "exact"] = "truncate_to_gold"
    calendar: Literal["strict", "as_written"] = "strict"   # "as_written": read a predicted date in the gold's calendar
    core_roles: Literal["slot", "key"] = "slot"     # E-M2: core_key equality; "key": the declared key roles
    seen: frozenset[str] = frozenset()               # core keys for the Ign variant (E-M11)
    bootstrap: Bootstrap = Bootstrap()

@dataclass(frozen=True)
class CompletionConfig:
    preset: Literal["hype", "stare", "hyper"] | None = None
    filter: Literal["exact", "monotone", "time_aware"] = "exact"   # the other two are always reported beside it
    rank: Literal["tie_exact", "optimistic", "pessimistic", "realistic", "model"] = "tie_exact"
    hits: tuple[int, ...] = (1, 3, 10)
    ece_bins: int = 15
    min_bin_queries: int = 100                        # per-arity ECE below this count: counts only
    bootstrap: Bootstrap = Bootstrap()

@dataclass(frozen=True)
class RetrievalConfig:
    ks: tuple[int, ...] = (1, 3, 5, 10, 20)
    headline_k: int = 10
    ndcg_discount: Literal["log2", "longmemeval"] = "log2"
    answer_mode: Literal["single", "set", "count"] = "single"   # for questions without their own answer_mode
    bootstrap: Bootstrap = Bootstrap()

@dataclass(frozen=True)
class MemoryConfig:
    mode: Literal["strict", "lenient"] = "strict"
    incorrect_reasons: frozenset[str] = frozenset({"wd:Q41755623"})
    bootstrap: Bootstrap = Bootstrap()

extraction.score(gold, predictions, *, schema, config=ExtractionConfig()) -> dict
    # gold: c4-extraction-doc items; predictions: C3 queue items, or C1 hyperedges carrying their doc id
stability.score(items, *, schema, unit: Literal["run", "run_id"] = "run",
                keys=("content_key", "core_key"), gold=None) -> dict
    # unit "run" is (run_id, order_id); "run_id" pools the orders of a run. Δ_order compares units of the same
    # and of different order_id
completion.build_queries(facts, schema, *, slots=("core", "qualifier"),
                         literal_targets: Literal["exclude", "include"] = "exclude",
                         universe: Literal["entities_of_type", "seen_in_position"] = "entities_of_type") -> list[dict]
    # c4-completion-query items, one per core or qualifier binding; excluded literal targets are counted
completion.FilterIndex.from_records(*splits) -> FilterIndex
completion.rank_stats(query, scores: Mapping[str, float], index, *, universe=None, target_prob=None,
                      top1=None, prob_map=None, model_rank=None) -> dict   # a completion-rank record (§9.4)
completion.score(queries, outputs, *, config=CompletionConfig()) -> dict
retrieval.score(questions, responses, *, facts: Mapping[str, dict] | None = None,
                config=RetrievalConfig()) -> dict       # facts: the gold hyperedges, for binding_coverage@k
memory.derive_memory_gold(trace, question, *, schema,
                          incorrect_reasons=frozenset({"wd:Q41755623"})) -> dict   # §9.5
memory.score(questions, responses, *, traces, schema, config=MemoryConfig()) -> dict
```

Every `score()` returns `{scorer, config, contracts, aggregate, breakdowns, items, bootstrap}`. `items` is keyed by
qid or doc id, and each entry lists `depends_on`. The scorers validate their inputs: C4 items through the I layer
and system outputs against `khg-c5-io-1.0.0`. A malformed input raises `ValidationError`.

### 9.3 Defaults and presets

One `score()` per ability (graft [J-cons], [J-std]).

| Scorer | Defaults | Presets |
|---|---|---|
| extraction | E-M1 strict (the headline); E-M2 core, which is `core_key` equality (critique C5-HANDCHECK); E-M4 Arg-I; E-M5 Arg-C; E-M6 role accuracy; E-M7 pooled with the grouping gap; E-M8 pairwise. Hungarian alignment (E-M3) on values, then bindings. Micro-doc, macro-relation and macro-arity averages | `hyperred_quintuplet`, `text2nkg` |
| stability | S-M1 pairwise Jaccard on both keys; S-M2 core ratio; S-M3 support histogram; S-M4 churn; S-M5 gold partition; S-M7 Δ_order | |
| completion | the `exact` filter, with `monotone` (⊑) and `time_aware` also reported; tie-exact expected ranks (C-M3); per task, per fact and macro-arity; hits@1, 3 and 10; top-1 ECE with 15 bins, equal-width and equal-mass, the reliability table and Brier, per arity bin on both arities | `hype`, `stare`, `hyper` |
| retrieval | k ∈ {1, 3, 5, 10, 20}. Headlines `support_success@10` and `mrr@10`, then hit@k, support_recall@k, r_precision, nDCG@k with log2(i+1), `binding_coverage@k`. **Answers:** EM on value identity, then SQuAD-normalised text EM and token F1; set P, R and F1 in set mode (over the set-mode questions); a question's `answer_mode` (C4 0.2.0) comes before the configuration's, and `count` scores as `single`; joint scores and gated EM; abstention precision and recall. **Cost:** mean, median, p90, p95 and total of every cost field, and answer EM against a cumulative-token budget (critique CONS-07) | |
| memory | strict accuracy (the headline) with lenient beside it; outcomes O1–O7 [R05 §5.2]; the stale rate split into `expired` and `revised`; anachronism, hedge and abstention rates; `support_success@k` against current support | `lenient` |

**Presets.**
- `hype`: all positions, pessimistic ties, the full-tuple filter and the per-task average.
- `hyper`: all positions and pessimistic ties.
- `stare`: subject and object from `primary`, averaged; a `(s, r, quals)` filter; a universe of the entities seen
  as subject or object.
  - Its sort-order ties need the model's own order, which the model supplies as `model_rank` (critique CONS-06).
    Without it the preset uses pessimistic ties and reports `approximated: ["sort_order_ties"]`.
  - StarE's filter keys on the *order* of the qualifiers [R05 §3.5 item 5]. C1 has no qualifier order, so the
    filter compares qualifier sets and always reports `approximated: ["qualifier_order"]`.

### 9.4 System outputs (`khg-c5-io/1.0.0`)

Values are C1 values throughout (critique CONS-07, C5-IO). The schema is
`design-examples/schemas/khg-c5-io-1.0.0.schema.json`.

| Output | `kind` | Fields |
|---|---|---|
| completion | `completion-rank` | `qid`, `n_candidates`, `n_filtered_out`, `n_greater`, `n_equal`; optional `target_prob`, `top1 {value, prob}`, `prob_map`, `model_rank` |
| retrieval | `retrieval-response` | `qid`; `answer {values, text?, abstained}`; `retrieved [{rank, unit_id, unit_kind, hyperedge_ids, bids?}]`; `support_claimed?`; **`cost`** `{prompt_tokens, completion_tokens, llm_calls, retrieval_calls, hyperedges_visited?, retrieval_ms, wall_ms, usd?, price_table?}`, which is required |
| memory | `memory-response` | `qid`, `answer {values, text?, abstained}`, `value_scores? [{value, score}]`, `retrieved?`, `cost?` |
| extraction | C3 queue items | §7 |

`bids` are `[edge, bid]` back-pointers. With them `binding_coverage@k` can tell pair, chunk and hyperedge units
apart. The three example lines of `c5-outputs.jsonl` are validated under both engines (§1.4):

```jsonl
{"kind":"completion-rank","n_candidates":9,"n_equal":1,"n_filtered_out":1,"n_greater":0,"qid":"cq:king-14-holder","target_prob":0.62,"top1":{"prob":0.62,"value":{"entity":"ex:LouisXIV"}}}
{"answer":{"abstained":false,"text":"Louis XIV","values":[{"entity":"ex:LouisXIV"}]},"cost":{"completion_tokens":9,"llm_calls":1,"prompt_tokens":412,"retrieval_calls":1,"retrieval_ms":3.5,"wall_ms":820},"kind":"retrieval-response","qid":"rq:king-1700","retrieved":[{"bids":[["f:king-14","b1"],["f:king-14","b2"],["f:king-14","b3"],["f:king-14","b4"]],"hyperedge_ids":["f:king-14"],"rank":1,"unit_id":"f:king-14","unit_kind":"hyperedge"},{"hyperedge_ids":["f:king-13"],"rank":2,"unit_id":"f:king-13","unit_kind":"hyperedge"}],"support_claimed":["f:king-14"]}
{"answer":{"abstained":false,"text":"Louis XIV","values":[{"entity":"ex:LouisXIV"}]},"kind":"memory-response","qid":"mq:king-1700","value_scores":[{"score":0.9,"value":{"entity":"ex:LouisXIV"}},{"score":0.1,"value":{"entity":"ex:LouisXIII"}}]}
```

### 9.5 Memory gold (normative)

`derive_memory_gold` replays the trace into a fresh `MemoryStore` (graft [J-impl], [J-cons]; critique CONS-03):
- The trace's `entities` are put first, one second before step 1.
- Then each event runs at its `tx_time` with actor `trace:<trace_id>`. A `put` event carries a list of C1
  hyperedges. Belief revision is an `apply` event; a lifecycle record in a `put` is D014.

The question fixes:
- τ, the `tx_time` of `ask_after_step`;
- t, the `where.as_of` instant, or null;
- the key (relation and key bindings) and the target role ρ.

The sets hold ρ-values (critique SEM-07, C5-IO):

| Set | The ρ-values of the facts on the key that… |
|---|---|
| V_cur | `find_by_key` returns under the question's `where` (status, rank, `valid_mode`, `as_of`) at `as_at` τ. If one of them is `preferred`, only the preferred facts count |
| V_old, `expired` | are asserted and not deprecated, and whose possible validity ends at or before t (e_hi ≤ t) |
| V_old, `revised` | were asserted at some τ′ < τ and are `superseded` or `retracted` at τ; and deprecated facts whose `rank_reason` names an "incorrect" reason (default `wd:Q41755623`) |
| V_fut | are asserted and not deprecated, and whose possible validity starts after t (s_lo > t) |
| `disputed` | are `disputed` at τ |

- V_cur is subtracted from every other set. A value that is both `expired` and `revised` is listed as `expired`.
- A fact that ended and was later superseded is `revised`, because `expired` needs an asserted fact.
- `answerable` is false when V_cur is empty and `disputed` is not.
- With `as_of: null` there is no valid-time filter. V_cur is then the current belief, and `expired` and V_fut
  are empty.
- An empty V_cur with nothing disputed is a valid "no current value" gold, for example a definite read inside a
  year-precision handover. P3a computes every item's gold under exactly its stated `where` (critique CONS-04).
- A disagreement between an item's stored gold and the replay is I005.

**Hand-checked on the fixture** (critique C5-HANDCHECK). These are the three memory questions of
`c4-items.jsonl` and ship as tests:

| Trace | Question | V_cur | V_old | V_fut |
|---|---|---|---|---|
| `t:kings`: put `f:king-13`, then `f:king-14` | holder of King of France as of +1700-01-01 | {`ex:LouisXIV`} | {`ex:LouisXIII`: expired} | {} |
| `t:kings` | as of +1620-01-01 | {`ex:LouisXIII`} | {} | {`ex:LouisXIV`} |
| `t:maria`: put `f:born-skłodowska-kraków`, then the `m:sup-1` correction | birthplace, `as_of` null | {`ex:Warszawa`} | {`ex:Kraków`: revised} | {} |

The first of them, as it is stored in `c4-items.jsonl`:

```jsonl
{"answer":{"values":[{"entity":"ex:LouisXIV"}]},"answerable":true,"ask_after_step":2,"disputed_values":[],"future_values":[],"id":"c4:mq-king-1700","key":[{"role":"position","value":{"entity":"ex:KingOfFrance"}}],"kind":"c4-memory-question","qid":"mq:king-1700","qset":"p2-fixture-qset","relation":"position_held","split":"test","stale_values":[{"kind":"expired","value":{"entity":"ex:LouisXIII"}}],"subtype":"current_value","support":["f:king-14"],"target_role":"holder","text":"Who was King of France on 1 January 1700?","trace_id":"t:kings","where":{"as_of":"+1700-01-01T00:00:00Z","rank":["preferred","normal"],"status":["asserted"],"valid_mode":"definite"}}
```

### 9.6 The C4 draft (`khg-c4-items/0.2.0`)

P3a owns C4 and fills it [DC §9.6]. The draft is written in C1 terms (critique CONS-02):
- values, bindings, hyperedges and entities are `$ref`s into `khg-record` 1.0.0;
- hashes are `sha256:`;
- `where.as_of` is an instant (§2.1) or null.

A file is JSONL: a `c4-header` line (`format`, `qset`, `record_format`, `schema {id, version, sha256}`, and
optionally `corpus {id, version, tier?}`, the corpus and tier the set was built on), then items. Every item has
`kind`, `id`, `qset` and `split` (`train`, `valid` or `test`). Version 0.2.0 (ruling 20) added the fields in bold, all
optional.

| `kind` | Required fields beyond the common four; optional ones |
|---|---|
| `c4-extraction-doc` | `doc_id`, `text` (NFC), `text_sha256`, `annotation {guideline, annotators?, adjudicated?}`, `gold` (C1 hyperedges with position selectors); `entities?` (what the gold needs); **`doc_kind?`** (`wiki`, `rendered`); **`source? {url, revision?, licence?, attribution?}`**; **`gold_scope?`** (the relations whose gold was audited complete; without it the gold is complete for every relation); **`mentions?`** (below) |
| `c4-completion-query` | `qid`, `fact_id`, `relation`, `arity`, `model_arity`, `target {bid, role, slot, value}`, `context` (bindings), `candidate_universe {kind: entities_of_type \| list, types?, ids?}`; **`manifest?`** (the id of the split manifest the query belongs to) |
| `c4-retrieval-question` | `qid`, `type` (`single_hop`, `multi_hop`, `temporal`, `comparison`, `aggregation`), `text`, **`anchors`**, `answer {values, text?}`, `support {sets}`, `hops`, `source_class`, `answerable`, **`where {as_of, valid_mode, rank, status}`**; `provenance?` (open: P10's `template`, `pair_hops`, `nary_dependent`, `anchor_degree`); **`answer_mode?`** (`single`, `set`, `count`; a count is one quantity of unit `"1"`, I002 otherwise) |
| `c4-memory-trace` | `trace_id`, `entities` (C1 entities), `events [{step, tx_time, put: [hyperedges] \| apply: event}]` |
| `c4-memory-question` | `qid`, `trace_id`, `ask_after_step`, `subtype` (`current_value`, `past_value`, `future_value`, `abstention`), `text`, `relation`, `key [{role, value}]`, `target_role`, `where`, `answer`, `stale_values [{value, kind: expired \| revised}]` and `future_values` (both mandatory, D-C5-15), `disputed_values`, `support`, `answerable`; `tolerance?` |
| `c4-split-manifest` | `splits {fact id: split}`, which `FilterIndex` reads (critique CONS-06), with the splits `train`, `valid`, `test` and **`inference`** (the facts an inductive model sees at test time); **`scheme?`** (`transductive`, `leak_probe`, `semi_inductive`, `inductive`, `temporal`); **`seed?`**; **`container? {document_id, sha256}`** (the C1 container it splits; `sha256` is `record.container_sha256`); **`probe? {fact id: [leak kinds]}`** (`core_key`, `reversed_pair`, `same_pair_other_relation`, `group`; a probe fact is a test fact); **`lite?`** (the ids of the fixed lite test subset) |

**`mentions`, the candidate table** (P9 DESIGN §3.1, D6): `[{entity, source, spans?, description?}]`, one entry per
entity. `entity` is a C1 entity record. `source` says how it came into the table: `link` (a hyperlink of the text
points to it), `subject` (the page's own subject), `match` (a label or alias occurs in the text) or `distractor` (an
entity of a fitting type that the text does not name). `spans` are `[start, end]` pairs, half-open, in code points of
the NFC text, as position selectors are (§2.8). The table is built from the text, never from the gold: a consumer
offers `mentions` to an extractor, never `entities`, which lists what the gold needs and would leak it.

**Reading and stamping.** Layer V takes `khg-c4-items/0.0.x` to `0.2.x`, and a header `record_format` of a
`khg-record` version the reader takes (V001 otherwise; 0.1.0 required the constant `khg-record/1.0.0`). The 0.2.0
draft schema checks every file the reader takes: 0.2.0 only adds optional fields and values, so a valid 0.1.0 file
stays valid (the reader does not enforce the stamp, as for HIF in ruling 19). Writers stamp the lowest version whose
features a file uses (§11.2): a file with any 0.2.0 field is stamped 0.2.0.

`validate_item` runs J, V and I:
- I001: an unknown kind;
- I002: the draft schema; and, on a line it accepts, a mention span that is empty, reversed or outside the text, an
  entity offered twice in `mentions`, and a probe fact that `splits` does not list as `test`;
- I003: an embedded C1 record or value, with the C, S or D finding nested; and a `gold_scope` relation that is not a
  relation of the schema (S001 nested);
- I004: a missing `stale_values` or `future_values`;
- I005: the memory-gold replay.

`design-examples/c4-items.jsonl` holds one item of each kind, built from the fixture: 10 lines, including two traces
and three memory questions. It is valid under both engines, and its five I cases are in G2 (§8.2). It stays a 0.1.0
file. `c4-items-0.2.0.jsonl` shows the 0.2.0 fields on the fixture (built by `research/probes/c4_0_2_examples.py`): a
header with its corpus; an extraction document with `doc_kind`, `gold_scope` and a candidate table of three matches
and one distractor; a completion query with its manifest; one retrieval question per answer mode, with P10's
provenance extras; and a semi-inductive and a leak-probe manifest.

### 9.7 Tests shipped (F14)

R05's tables ship as `tests/scorers/test_*_r05.py`. Their expected values come from
`research/probes/scorers/c5_reference_cases.py`.
- `tests/scorers/r05.relation-schema.json` maps the abstract tables to C1 (critique C5-HANDCHECK). Relation `r`
  has A and B in the core slot, C, D, E and Q in the qualifier slot, and key {A, B}; relations `s`, `r2` and `r4`
  complete it.
- **Extraction:** E1–E11, E5b and E5c. **E12** is new: `population` with gold +679941 and prediction +685285 at the
  same `point_in_time`. Its core F1 is 0, and 1 under `core_roles="key"`.
- **Stability:** S1–S4.
- **Completion:** C1–C8. C3 gives E[RR] 25/48. C7 gives ECE 13/100 at M = 10 and M = 15, and Brier
  393/2000 = 0.1965. C8's order is fixed as correct = [1, 1, 1, 0, 1, 1, 0, 0, 0, 0], which gives 1/4 and 19/100.
- **Equal-mass bins** (normative): sort by confidence; B = min(M, the number of distinct confidences); for
  i = 1 … B − 1, the i-th cut is the end of the run of equal confidences that contains position ⌈i·n/B⌉; ties are
  never split and empty bins are dropped.
  - C7 under equal mass gives 13/100.
  - **C7b** is new: confidences [0.1, 0.2, 0.3, 0.4] with correct [0, 0, 1, 1] and M = 2. It gives 1/4 with equal
    width and 2/5 with equal mass.
- **Retrieval:** R1–R8 (R1: nDCG 0.650921, and 0.75 for the LongMemEval variant). **R9** is new: gold
  h = r(A: a, B: b, C: c), and units [pair(A, B), pair(A, C)] with bid back-pointers. `binding_coverage@1` is 2/3
  and `@2` is 1.
- **Memory:** M1–M8. **M9** is new: the three replays above.
- **C1-semantics tests:**
  - the monotone filter is ⊑;
  - `truncate_to_gold` is value refinement, and it holds across calendars;
  - the Hungarian solver is checked against brute force on seeded 4×4 matrices;
  - the bootstrap interval is pinned.

## 10. Package layout (F12)

### 10.1 Layout

`pyproject.toml` sits at the repository root. It uses hatchling, names the distribution `khg-contracts`, requires
Python >= 3.10 and is MIT licensed.

```text
pyproject.toml          # license-files: LICENSE and src/khg_contracts/data/schemas/HIF-LICENSE.txt
src/khg_contracts/
  __init__.py           # __version__, CONTRACTS (§11)
  errors.py             # KHGError(.codes, .info) and ValidationError, KeyCollision, VersionError,
                        #   ConcurrencyError, NotFound, CapabilityMissing, LoaderError
  jsonio.py             # layer J (strict parse), canonical JSON with RFC 8785 numbers, digest
  record/               # values, literals and windows, identity, derived, canonical, container I/O, lifecycle,
                        #   keys, evidence, render (render_text), project (the projections of §2.10)
  schema/               # load_schema, Schema, the built-in lifecycle relations, schema_hypergraph, GYO
  validate/             # the layer runner, layers J V H R P D C S M Q I, registry, engines.py (offline resolvers)
  hif/                  # to_hif, from_hif, slices, literal labels
  loaders/              # Bundle, Context, xgi.py, hnx.py, reconcile, ExportReport
  store/                # protocol, Where, clocks, StoreBase, MemoryStore, memory_factory, Timed,
                        #   compare_containers, conformance/ (runner, EARL report)
  queue/                # Queue, make_candidate, the fold, Linter (structural), replay, queue_items
  identity/             # relate (non-normative)
  scorers/              # extraction, stability, completion, retrieval, memory, and shared helpers
  migrate/              # v0_sample_to_v1.py
  examples.py           # python -m khg_contracts.examples DIR writes design-examples/ from data/
  cli.py                # the four console scripts (§10.4)
  data/                 # the single source of packaged files, read with importlib.resources (critique PACKAGE-DATA)
    schemas/            # khg-record-1.0.0, khg-relation-schema-1.0.0, khg-hif-1.0.0, khg-queue-1.0.0,
                        #   khg-c4-items-0.2.0, khg-c5-io-1.0.0 (.schema.json); the vendored
                        #   hif_schema_v0.1.0.json (sha256 639466b7…2196) and its HIF-LICENSE.txt
    error-codes.json, malformed-cases.json
    fixture/            # the fixture set (fixture.*), smoke-base.c1.json, smoke-queue.khg-queue.jsonl,
                        #   queue-item.json, action-log.json, c4-items.jsonl (0.1.0), c4-items-0.2.0.jsonl,
                        #   c5-outputs.jsonl,
                        #   the cyclic and Wikidata-shaped relation schemas
    role-convention/    # the five fixture-PR files
    scenarios/          # index.json and the 114 scenario files
    sample/             # the four migration goldens (§11.3)
tests/                  # see §10.5; conftest.py blocks sockets and defines the markers gate, libs and evidence
```

`design-examples/` is generated from `data/` by `python -m khg_contracts.examples`, and CI checks byte equality
(§10.6). The files that only tests use live under `tests/`: `golden-sha256.json`, `native-ops.json`,
`r03-loader-cases.json`, `r05.relation-schema.json` and `library-hif-evidence.json`.

### 10.2 Public API

The table gives every name that §1.3 and G1–G3 call (critique API-GAPS, CONS-09). Errors carry `.codes` and
`.info`.

| Name | Signature → result | Raises |
|---|---|---|
| `khg_contracts.__version__`, `CONTRACTS` | `str`; `Mapping[str, str]` (§11) | |
| `jsonio.loads`, `jsonio.load` | `(text \| bytes)`, `(path)` → object | `ValidationError` J001–J007 |
| `jsonio.canonical`, `jsonio.digest` | `(obj) -> str`; `(domain, payload) -> "sha256:…"` | |
| `record.read_container` | `(path) -> dict`, from `.khg.json` or `.khg.jsonl` by suffix; any other suffix raises `ValueError` | J, V001 |
| `record.iter_jsonl` | `(path) -> Iterator[dict]`: the header, then records, streamed | J |
| `record.write_container` | `(container, path, *, format="jsonl" \| "json") -> None`: canonical order, after the V and C checks; a path whose suffix is not the one `format` implies (`.json` or `.jsonl`) raises `ValueError` | V001, C |
| `record.normalize` | `(record, schema) -> dict`: canonical form and literal normalisation (NFC, lower-case `lang`, `supports` defaults); no checks | |
| `record.derive` | `(record, schema) -> dict`: the `derived` block (arity family, three keys, `valid_time`) | `ValueError` on an invalid record |
| `record.content_key`, `core_key`, `key_digest`, `arity`, `valid_time` | `(record, schema)` → `str`; `str`; `str \| None`; `{arity, core_arity, statement_arity, distinct_fillers}` or `{n_bound, n_unbound}`; the §2.6 dict | as `derive` |
| `record.value_identity`, `record.window` | `(value) -> dict`; `(time literal) -> (lo, hi)` instants | S006 |
| `record.container_sha256` | `(container) -> "sha256:…"`: the plain SHA-256 of the canonical `.khg.jsonl` text (queue `base`) | |
| `record.resolve_redirects`, `record.supported_values` | `(entity_id, entities) -> str`; `(history, evidence_id) -> {bid: value}` | |
| `record.render_text` | `(record, labels, *, schema) -> str` (`khg-render/1`) | |
| `record.project.*` | `position_map`, `positional`, `hyper_relational`, `role_value_set`, `rdf_relation_instance` and `from_rdf_relation_instance`, `incidence_rows` and `from_incidence_rows` (§2.10) | `ValueError` |
| `schema.load_schema` | `(path \| mapping) -> Schema` (`.id`, `.version`, `.ref`, `.sha256`, `.relation(id)`, `.usage(rel, role)`) | `ValidationError` M |
| `schema.schema_hypergraph`, `schema.is_alpha_acyclic` | `(schema, *, slots=("core", "qualifier")) -> {vertices, hyperedges}`; `(hg) -> (bool, residue)` | |
| `validate.validate` | `(obj_or_path, *, kind="auto", schema=None, doc_texts=None, bases=None, engine="jsonschema") -> {ok, findings}`. Kinds: `record`, `container`, `hif`, `role-convention`, `schema`, `queue`, `item` | never raises on bad input |
| `validate.validate_record`, `validate_container`, `validate_hif`, `validate_queue`, `validate_item` | the kind-fixed wrappers; `validate_queue(q, *, schema, bases=None)` | |
| `hif.to_hif`, `hif.from_hif` | §4.2, §4.3 | `ValidationError` (D009 without a schema) |
| `loaders.*` | `load_xgi`, `export_xgi`, `load_hnx`, `export_hnx`, `khg_to_xgi`, `xgi_to_khg`, `khg_to_hnx`, `hnx_to_khg`, `Bundle` (§5) | `LoaderError` (P005, P007, P010, D001) |
| `store.*` | `Store`, `StoreBase`, `MemoryStore`, `memory_factory(schema, clock)`, `Timed`, `Where`, `SystemClock`, `ScenarioClock`, `compare_containers`, `conformance.run` (§6) | §6.1 errors |
| `queue.*` | `Queue.create`, `open`, `submit`, `accept`, `reject`, `flag`, `verdict`, `withdraw`; `make_candidate`, `Linter`, `replay`, `queue_items` (§7) | Q codes; store errors on accept |
| `identity.relate` | `(a, b, *, schema) -> "duplicate" \| "refines" \| "generalises" \| "distinct" \| "key_conflict" \| "key_timeline" \| "negation_conflict"` | |
| `scorers.*` | §9.2 | `ValidationError` on malformed inputs |
| `migrate.v0_sample_to_v1` | `(hif) -> (schema, container, report)` (§11.3) | `ValidationError` on a stored arity that disagrees |

### 10.3 Dependencies

- **Core:** `jsonschema>=4.18,<5` (4.26.0 probed) and `fastjsonschema>=2.21,<3` (2.22.2 probed; pure Python with no
  dependencies; critique ENGINES).
- **Extras**, pinned to the probed versions (F12):
  - `xgi`: xgi==0.10.2;
  - `hnx`: hypernetx==2.4.3 and pandas>=2.2,<3;
  - `fast`: SciPy, for the Hungarian solver;
  - `dev`: pytest and build.
- **Import hygiene:** importing `khg_contracts` loads none of xgi, hypernetx, pandas, numpy or SciPy. A test checks
  `sys.modules` (critique CI-MATRIX).

### 10.4 Command-line tools

The four v1 commands are declared in `[project.scripts]` (critique CLI-SPEC). Each exits with 0 on success, 1 when
the input fails, and 2 on a usage or I/O error. `khg-queue` and `khg-score` come in 1.1 (critique SCOPE-F13).

| Command | Arguments | Output |
|---|---|---|
| `khg-validate PATH` | `[--kind auto\|record\|container\|hif\|role-convention\|schema\|queue\|item] [--schema P] [--doc-texts P] [--base P …] [--engine jsonschema\|fastjsonschema] [--json]` | the `validate()` result. Exit 1 when there is any error finding |
| `khg-convert IN OUT` | `--to hif\|khg-json\|khg-jsonl [--schema P] [--relations R,…] [--literal-nodes shared\|per_binding] [--schema-document]` | the converted file. Exit 1 on a validation failure |
| `khg-migrate IN OUT` | `--from v0-sample [--schema-out P] [--report P]` | the container, the generated schema and the F report (§11.3) |
| `khg-conformance` | `--factory MODULE:CALLABLE [--only GLOB] [--capabilities FLAGS] [--report PATH]` | the EARL JSON report. Exit 1 when any scenario failed; `inapplicable` is not a failure |

`khg-conformance --factory khg_contracts.store:memory_factory` runs the suite on the reference store. Each command
has one smoke test in `tests/cli/`.

### 10.5 Tests

| Directory | Holds | Serves |
|---|---|---|
| `gate/` | `test_roundtrip.py`, `test_malformed.py`, `test_smoke.py` and `golden-sha256.json` | G1, G2, G3 |
| `c1/` | RFC 8785 vectors, digests, windows and calendars, value identity, refinement, derived equals `fixture.with-derived.c1.json`, the arity table, spans, JSON and JSONL equality, `render_text`, the projections | G1, G2 (C, S) |
| `schema/` | M checks, built-ins, `schema_hypergraph`, GYO on the three schemas | G2 (M), P6 |
| `hif/` | `to_hif` equals the fixture and slice files, decoding, slices, per-binding literals, `schema_document`, R and P checks, the role-convention files | G1, G2 (H, R, P, D) |
| `loaders/` | construction, context, reconcile, the strict rule, one test per native operation, R03 cases c00–c26, HNX constructor keywords | G1 |
| `validate/` | the layer rule, code coverage (reserved codes skipped), single-fault engine containment, offline resolution with sockets blocked | G2 |
| `store/` | the 114 scenarios, the capability-limited runs, `Timed`, `compare_containers`, `load(on_missing=…)` | G3, P1 |
| `queue/` | the fold, `make_candidate`, `submit`, the linter, `accept`, `replay` with a base, the Q cases | G3, G2 (Q) |
| `identity/` | `cases.json`: the 37 rows of [DB §2.19] | P7 |
| `scorers/` | §9.7 and `r05.relation-schema.json` | F14 |
| `migrate/` | the sample goldens, the F codes, the G1 chain on the migrated sample | §11.3 |
| `consumers/` | the §1.3 sequences, verbatim, on `MemoryStore` with packaged data | P1–P10 |
| `cli/`, `packaging/` | one smoke test per command; package data present with its hashes; import hygiene | release |
| `evidence/` | `test_library_hif_io.py` (marker `evidence`), which writes `library-hif-evidence.json` | upstream |

### 10.6 CI

| Job | Python | Install | Runs |
|---|---|---|---|
| `core-3.10` | 3.10 | `.[dev]` | every test. Loader, evidence and G1 tests skip through `pytest.importorskip`; import hygiene is checked |
| `gate-3.11` | 3.11 | `.[xgi,hnx,fast,dev]` | `pytest -m "not evidence"`, including G1–G3. G1 spawns its own hash-seed children, so there is no separate hash-seed step (critique G1-HASHSEED) |
| `core-3.13` | 3.13 | `.[dev]` | the core tests; the library tests skip |
| `wheel` | 3.11 | build, then install the wheel into a clean venv | `khg-conformance` on `MemoryStore`; `khg-validate` on the packaged fixture; package-data hashes |
| `examples` | 3.11 | `.` | `python -m khg_contracts.examples out/`, byte-compared with `design-examples/` |
| `evidence` | 3.11 | `.[xgi,hnx,dev]` | `pytest -m evidence`, offline |

## 11. Versioning and migration

### 11.1 Format ids

| Artefact | Format id | Versioned with |
|---|---|---|
| C1 | `khg-record/1.0.0` | itself |
| schema language, HIF profile | `khg-relation-schema/1.0.0`, `khg-hif/1.1.0` (ruling 19; files that do not use 1.1 are stamped 1.0.0) | C1 |
| upstream convention | `role-convention` 1.0.0 (four rules) | itself; minor versions only |
| C3 | `khg-queue/1.0.0` | C1, in lockstep (PLAN §7) |
| C2 and its scenarios | `khg-store/1.0.0` (`info().interface_version`), `khg-scenario/1.0.0` | their own semver |
| C5, its outputs, the C4 draft | `khg-scorers/1.0.0`, `khg-c5-io/1.0.0`, `khg-c4-items/0.2.0` (ruling 20) | C1; P3a owns C4 |
| derived text | `khg-render/1` | a new number for any change |
| migration report | `khg-migration-report/1.0.0` | `migrate/`; its own semver |
| relation schemas | `<id>/<version>` (`typed_under`) | the author |
| codes, cases, hash domains | `khg-codes/1.0.0`, `khg-malformed-cases/1.0.0`; `khg-content-key/1` and the other domains | codes only grow; domains change only with a C1 major |

`$id`s are `tag:khg-contracts,2026:schema/<name>/<version>` (RFC 4151). They are never fetched.

**`khg_contracts.CONTRACTS`** maps every format id above to its version (critique VERSION-RELEASE). It is stamped
into `StoreInfo` and into every scorer report, so each consumer can record the contracts it used (PLAN §7).

### 11.2 Semver, stamping and releases

The semver rules come from [DC §11.2] (graft [J-std]).
- **Major:** a valid document becomes invalid or changes meaning. This includes:
  - canonicalisation or a hash domain;
  - the arity rule;
  - the precision windows, the bound table or value identity;
  - the `Where` defaults;
  - the transition table.
  A major ships `migrate/vN_to_vN+1.py` and reruns every consumer gate.
- **Minor:** optional additions (fields, datatypes, enum values, lifecycle relations, flags, codes). New `Store`
  methods arrive as `StoreBase`-derived methods or behind a capability flag, so existing backends stay conformant
  (critique CONS-27).
- **Patch:** documentation, fixes and tests.

**Stamping** (critique VERSION-RELEASE). Writers stamp the lowest format version whose features the document uses.
A reader rejects a newer stamp with V001 (MC010). So a 1.1 writer's documents stay readable by 1.0 readers until they
use a 1.1 feature.

**Releases.**
- khg-contracts 1.0.0 goes to PyPI once G1–G3 pass (W14). P2 cuts every release.
- The C4 draft stays 0.x until P3a's first question set is accepted. P3a proposes C4 changes as pull requests
  against `data/schemas/khg-c4-items-*.schema.json`, and P2 releases each change as a minor version.
- The wheel ships the vendored HIF schema with its MIT notice ("Copyright (c) 2024-2025 HIF development team") as
  `HIF-LICENSE.txt`.

### 11.3 Migrating `schemas/sample.hif.json`

`khg-migrate schemas/sample.hif.json sample.khg.json --from v0-sample --schema-out sample.relation-schema.json`
runs `migrate/v0_sample_to_v1.py` [DB §11.3]. Every choice that fixes a key is pinned (critique SAMPLE-MIGRATION).

| Sample feature | Result |
|---|---|
| the file | stays unchanged as the v0 fixture |
| relations, roles, node types | a generated schema `kb-sample` 1.0.0. Each observed role is a core usage, sorted by role id. Its fillers are the observed types. `min` is 1 if the role occurs in every edge of the relation, else 0. `max` is 1 unless the role repeats in an edge, else null. The direction is the observed one when all incidences agree |
| `valid-from` | an interval time model (`start_time`, `end_time`) with generated time usages of direction `tail`. The value becomes a `start_time` binding at precision 11 (F017) |
| incidences | one binding per incidence, with bids b1… in canonical binding order |
| `source` | evidence `e1` = `{type: imported, mode: automatic, source: {doc_id: <the edge's source>}}` |
| `arity` (f1 4, f2 3, f3 2) | checked against the C1 rule and dropped (F015). A mismatch raises |
| `weight` (0.95, 0.8, 1.0) | `extensions["hif:weight"]`, never confidence (F006). Reading it as confidence comes with foreign import in 1.1 |
| `schema`, `conventions` | replaced by the declaration block (F016) |
| `title`, `description`, `created`, `kb-section` | `extensions["hif:metadata"]`. The header's `document_id` is `kb-sample` and `complete` is true |

The goldens are `sample.relation-schema.json`, `sample.khg.json`, `sample.khg.hif.json` and
`sample.migration-report.json` (`khg-migration-report/1.0.0`). They are in `design-examples/` and `data/sample/`, and
W10 commits them next to `schemas/sample.hif.json`. `tests/migrate/test_sample.py` checks the goldens and the
report codes in order, and runs the G1 chain on the migrated sample. The prototype reproduces all four goldens
(§1.4).

## 12. v1 scope, later versions and the upstream proposals

### 12.1 v1 (F13)

v1 is what §1.2 and §1.3 exercise:
- **P2:** C1; `role-convention` with layer R; the profile; the loaders; the validator; C3 with the structural
  linter; the store and export; `khg-migrate` for the v0 sample; four CLIs.
- **P1:** C2; the flags; the 114 scenarios with their core variants; `Timed`; `load(on_missing=…)`; header state;
  `compare_containers`; `rdf_relation_instance` and `incidence_rows`.
- **P3a:** literals and the precision windows; specials; rank and `rank_reason`; keys; the arity family; JSONL; the
  Wikidata mapping (§2.6); the C4 draft with the I layer.
- **P3b:** completion; `project.positional`, `hyper_relational` and `role_value_set`; `model_arity`; the split
  manifest.
- **P5:** slices, per-binding literal nodes and `roles`.
- **P6:** the schema language; `schema_hypergraph` and `is_alpha_acyclic`; the cyclic and Wikidata-shaped schemas.
- **P7:** keys, the bound table, lifecycle, the walk, `identity.relate`, `render_text`, and memory with
  `derive_memory_gold`.
- **P9:** C3 with verdicts and replay; extraction and stability.
- **P10:** the reads, `render_text`, anchors, and retrieval with cost.

### 12.2 Later versions

| Version | Later |
|---|---|
| 1.1 | **Foreign HIF import:** `import_foreign`, F001–F005 and F007–F014, weight read as confidence, and a loss report over vendored upstream fixtures (critique SCOPE-F13) |
| 1.1 | **Linter rule sets:** identity (L001–L007, L009) and quality (L101–L108, L110) |
| 1.1 | **Queue:** the proposal item kinds (`merge_proposal`, `supersession_proposal`, `validity_proposal`), the `merge` and `auto_fix` actions, and the `khg-queue` and `khg-score` CLIs |
| 1.1 | **Records and schemas:** rule relations (`kind: rule`, S017); `khg:fulfils` and a `bind` event (P11); the `withheld` special value (R01 case 4c); per-binding validity; validity bounds (P1319, P1326) |
| 1.1 | **Consumers:** the pairwise projection; the GraphRAG-Bench, LongMemEval and LoCoMo adapters (P4); soft F1 (E-M12); LinkML, SHACL, TypeQL and SQL generators; fold rules for numbered roles |
| 1.2 | entity merge in C2: rewriting values that name a redirected entity (D020 until then), and rewrite actions in C3 [R01 C2-R20] |
| 2.0 | a HIF v2 record-level `role`, if upstream adopts it; any change to canonicalisation or hashes |

Codes of later versions are listed in `error-codes.json` as `planned` and are not registered until they ship
(§8.1).

### 12.3 The upstream HIF proposal (F15)

The issue comes first and asks for nothing that breaks v1 [R02 §11 rec. 8]. Its title is "A `role` convention for
incidence attributes (no schema change), with compliant fixtures". It contains:
- **Motivation, with both precedents** (critique UPSTREAM): the paper's `{"role": "PI"}` (p. 7), and upstream's
  own compliant test `single_incidence_with_attrs.json`, which holds `{"role": "PI", "age": 42}` [R02 §6]. Also
  #44 (attribute-first extensions) and #21 (structural fields against `attrs`).
- **The four rules of `role-convention` 1.0.0** (§4.1), `role-position` included, with the R-layer checks
  R001–R004 as the reference.
- **One question for upstream to settle.** The formal model's incidence set I is a set, yet
  `duplicated_nodes_edges.json` is marked "Expect to pass unless uniqueness is enforced" [R02 §3]. The convention
  needs readers to keep repeated pairs, and asks that the README say so and that readers round-trip `attrs`.
- **A follow-up fixture PR** with the five files of `design-examples/role-convention/`: `basic`, `two-roles`,
  `tail-head`, `ordered` and `undirected`. All five are valid against the vendored schema, pass layer R in CI and
  round-trip through both loaders (§1.4).
- **The evidence** `library-hif-evidence.json`, written by `tests/evidence` (§5).
- **v2 asks** (#51, #55): a record-level `role` and a data-file version marker.

The `khg-*` keys stay out of the issue, and no `hif-*` names are proposed (graft [J-std]). The gate never depends
on the outcome.

### 12.4 Library issues

Each issue attaches `library-hif-evidence.json` [R03 §7.5, D12].
- **XGI:** incidence `attrs` and weights; repeated records; clear direction errors; no splatting of `attrs`;
  deterministic order.
- **HyperNetX:**
  - an offline schema (#171);
  - raise the errors it constructs;
  - keep `metadata`;
  - no `default_attrs` with a null direction;
  - drop `fillna("nil")`;
  - export isolated nodes and empty edges;
  - keep repeated records;
  - `misc_node_properties_col` and `misc_edge_properties_col`, which 2.4.3 silently ignores (critique GL-13);
  - `clone()` and `sum()` losing isolated nodes (§5).

## 13. Decisions log

### 13.1 Contested decisions and rulings

"all" means all three judges.

| Decision (research ids) | Choice | Rejected | Basis |
|---|---|---|---|
| Multi-role encoding (R01 D-01, R04 O2) | one incidence per binding (§4.1) | role lists; role-keyed bindings | all; [R02 §5 case 02], [R03 D2] |
| Binding shape (D-03) | a list of `{bid, role, value, position?, direction?, extensions?}`; the slot comes from the schema | a stored slot | all |
| Arity (D-06) | B's rule, plus core arity, statement arity and distinct fillers | C's count including time | all |
| Slots ([R04 O12]) | core, qualifier, time, meta | A's `valid` lifting | all; [R01 C1-R47] |
| Literals (D-09) | inline in C1; `_:lit:` nodes shared by value by default, per binding on request; per-binding special nodes | C's edge-attr specials; A's lexical precision | all; critique CONS-15 |
| Keys ([R04 O3]) | `on_collision`, default `dispute`; `KeyCollision` lists every collision with policy, shape, class and action | merge; policies applied by the store | all; critique SEM-04, SEM-05, CONS-13 |
| Statuses (D-08, [R04 O4]) | six statuses plus `quoted`; rank and visibility separate | A's missing `disputed` | all |
| Store defaults (D-16) | `at_least`; no valid-time filter without `as_of`; definite mode | "as of now" | all |
| Schema language (D-15, [R04 O10]) | own JSON, LinkML-shaped, draft-07 | LinkML or SHACL itself | all |
| Supersession carrier (D-10, [R04 O5]) | lifecycle record plus validated `status_ref` | C's record kind ([J-impl]) | [J-cons], [J-std]; backends may index lifecycle records |
| Version rule | refine-only (D013), by bid | C's append-anything `put` | [J-cons], [J-std]; S031 not needed |
| Direction in mixed files (D-12) | native; `directed` only when complete | B's rewrite | [J-std]; [R02 §5 cases 24–25] |
| Identity classifier | non-normative `identity.relate` with seven labels | a normative planner | [J-cons], [J-std]; PLAN gives identity to P7 |
| Repository format ([R01 PF-28]) | JSON and JSONL; HIF for interchange | HIF as the repository format | [J-impl] |
| Queue (D-18), verdicts ([R04 O9]) | a file per (run, order); verdicts keyed (`core_key`, `event_hash`), bindings named by content tuple | one stream; `content_key`; bids as binding names | [J-cons], [J-std]; critique CONS-18 |

**Grafts** (each proposed by two or more judges):
- **From C:** the call sequences as tests; `Where`, `load`, `get_many`, `iter_records`, `Timed`,
  `compare_containers` and `StoreBase`; events and `KeyCollision`; the queue organisation, with scorers reading C3
  items; slices and the HNX "nil" finding; flat `khg-*` keys; semver rules; embedded schemas.
- **From A:** the convention and the upstream issue; PYTHONHASHSEED and engine agreement; pointer validation.
  Foreign import follows A in 1.1.
- **From B:** `derive_memory_gold`; the identity table as tests.

**Synthesis decisions** (unchanged by this revision):
- Julian dates are kept as written ([J-cons]), since B's conversion loses the written date. Identity compares
  Gregorian windows (§13.2).
- Extensions pass through, and J006 applies ([J-impl]).
- The version rule is checked by bid, which makes it linear.
- Lifecycle records are written only by events; `load` is trusted, and D012 is also a container check.
- The key invariant is judged per instant, because B's pairwise check refused a preferred fact beside two normal
  ones.
- Non-integer numbers are serialised by RFC 8785.
- All hashes use `sha256:`. There is no `hif-schema-doi` key.
- One mixed fixture plus a slice replaces B's two fixtures.

**Adopted as the reports recommend:** R01 D-02, D-04, D-05, D-07, D-11, D-13, D-14, D-17, D-19–D-22; R03 D1–D12;
R04 O1 and O6–O13; R05 D-C5-01–18.

### 13.2 Decisions of this revision

Each row settles a question that the critique found open. The Revision log names every finding.

| Decision | Choice | Rejected | Basis |
|---|---|---|---|
| Precision windows | Wikidata's: ordinal centuries and millennia, decades by floor, BCE in historical numbering, no year 0, a calendar required before 1583 (§2.3) | flooring every precision on astronomical years | critique CONS-01, CONS-12; Wikidata Help:Dates; Wikibase JSON |
| Time identity | the proleptic-Gregorian window plus the precision, whatever the calendar | the calendar as part of identity | critique CONS-12, SEM-13 |
| Bounds | a normative bound table with definite and possible readings; the key invariant on definite windows; possible-only overlap is L008 | presuming undated facts always valid (the old X3 answer) | critique SEM-01, SEM-08, CONS-11 |
| Default time model | `timeless` (it was `unstated`) | reading unstated relations as intervals | critique SEM-15 |
| Collisions | classes first, then the policy by shape; `supersede` refused on temporal keys (M017); the disputed-key rule | a store-applied policy; an `undated` shape | critique SEM-04, SEM-05, SEM-09 |
| Lifecycle events | event records arrive asserted; leaving a lifecycle status drops `status_ref`; keyed undo resolves the superseding facts | implicit undo | critique SEM-10, SEM-19 |
| D011 | an event precondition, a `put` check on superseding facts, and a container check | a container invariant "superseding facts asserted" | critique SEM-11 |
| `event_hash` | stored once at extraction, for extracted and inferred evidence only, and kept in `decision_hash` | recomputed against the host record | critique SEM-12, GL-11 |
| Layers | a finding's layer is its code's letter; the first rejecting layer is the earliest letter in pipeline order; new layer R | the phase that ran | critique GL-02, SEM-03, UPSTREAM |
| `role-position` | rule 4 of `role-convention` 1.0.0 | a profile-only rule | critique UPSTREAM |
| HyperNetX records | the cell is the source of truth, with `khg-extra-incidences` | the context for both libraries | critique GL-03 |
| Strict export | raise on unlabelled memberships, partial facts and non-injective moves; report whole-edge removals | raise on every stale record | critique LOADER-STRICT |
| Engines | fastjsonschema in core; closed resolvers; agreement defined on single-fault inputs | embedding the vendored schema; equal codes on multi-fault inputs | critique ENGINES, GL-10 |
| Scope | foreign import, the identity and quality linters, rule relations, proposals and two CLIs move to 1.1; their codes are planned, not registered | v1 carrying them | critique SCOPE-F13; F13 |
| Vocabulary ids | units, globes and rank reasons are not references | entity records for them | critique FIXTURE-VOCAB-REFS |
| Redirected entities | refused in v1 (D020); rewriting in 1.2 | a lint | critique SEM-16 |
| Memory gold | the normative table of §9.5, with the kinds `expired` and `revised` and a `disputed` set | one sentence; `retracted` as a kind | critique SEM-07, C5-IO |
| Header state | part of C2 | exports without a document id | critique STORE-HEADER |
| Slices | closed over `status_ref`; external references; `khg-complete: false` | open slices | critique GL-17, CONS-14 |
| Derived views | `render_text` (`khg-render/1`) and the projections of §2.10 in v1 | names only | critique CONS-08, PROJECTIONS, CONS-20 |
| Package data | `data/` is the single source; `design-examples/` is generated from it | copies in tests and examples | critique PACKAGE-DATA |
| Stamping | writers stamp the lowest version whose features they use | stamping the writer's version | critique VERSION-RELEASE |
| `end_cause` | a meta binding `khg:end_cause`, mapped to P1534 | a qualifier, which would change `content_key` on `end_validity` | critique SEM-06 |

## 14. Risks and open questions

**Risks.**
1. **Presumptions can misread data.** The bound table reads an absent end as "still holds" and an absent start as
   unknown. A source that means something else by an absent bound gets other answers. S-TIME-005, S-TIME-008 and
   S-TIME-009 pin the reading.
2. **P1's backends must reproduce the windows, the per-instant key invariant and the version rule.**
   `derived.valid_time` hands them the computed instants, and the S-TIME scenarios at precisions 6, 7 and 8 and
   the BCE Julian date catch divergence. The flags let a backend report what it lacks.
3. **The prototypes are research code.** The package reimplements them module by module (Implementation plan). The
   180 malformed cases, the 114 scenarios, the goldens and the byte-equality check on `design-examples/` are the
   acceptance tests.
4. **The library versions are pinned** (xgi 0.10.2; hypernetx 2.4.3 with pandas<3). HyperNetX silently ignores
   some constructor keywords, and `clone()` drops isolated nodes. The evidence test and the native-operation tests
   flag an upgrade that changes either.
5. **The upstream issue may choose another key or reject repeated pairs.** The profile can map another key in a
   minor version. If upstream rules that incidences are a set, the convention needs a v2 ask, not a v1 change.
6. **C4 is a draft that P3a owns.** Its changes go through P2 releases (§11.2), so P3a's first question set may
   force a quick minor release.
7. **v1 is large:** 15 build steps. The critical path (Implementation plan) puts G1 first and keeps G2 from
   waiting on the scorers.

**Open questions for the director.** These are the questions the evidence cannot settle.
1. **What does "every implementation passes one conformance test" (PLAN §7) mean for backends without some
   flags?** The design reads it as "no scenario fails", with `inapplicable` scenarios reported as fidelity losses.
   On that reading, TypeDB 3.x passes with 70 of 114 scenarios applicable. The alternative makes P1 emulate
   ordered roles, special values, goals and transaction time on TypeDB.
2. **Who owns the PyPI project `khg-contracts` and the GitHub account that files the upstream and library
   issues (W14)?** Trusted publishing needs the repository owner to configure it.
3. **Which Wikidata deprecation reasons mark a revised value in memory gold?** The design counts only
   `wd:Q41755623` ("incorrect value") by default (`MemoryConfig.incorrect_reasons`). P3a and P7 should confirm or
   extend the list before P3a builds the memory set, because I005 replays with the default.

**Director's rulings on the open questions (2026-09-23).**
1. **Conformance.** An implementation passes C2's conformance test when no applicable scenario fails. A scenario
   is inapplicable only because of a capability flag the backend declares absent. P1 reports every inapplicable
   scenario as a fidelity loss in its measurement table. P1 may emulate a missing capability, but it is not
   required to. PLAN §7 now says this.
2. **Publishing.** The repository owner owns the PyPI project `khg-contracts` and files the HIF, XGI and HyperNetX
   issues and the fixture PR from their own account. P2 prepares the wheel, the issue texts, the fixture branch and
   `library-hif-evidence.json`. Nothing is published or filed from a Claude session. W14 ends at "ready for the
   owner".
3. **Deprecation reasons.** The default stays `wd:Q41755623` only. P3a's datasheet reports the distribution of
   deprecation reasons it finds, and P3a and P7 confirm or extend the list before the memory set is built. A change
   is a minor release of the C4 draft.

**Director's rulings on implementation questions (2026-09-24).** Raised by the build steps; see
`impl-notes/`.
4. **Container suffixes.** `read_container` and `write_container` dispatch on the suffix only: `.json` is one
   JSON document, `.jsonl` is JSONL, and any other suffix raises `ValueError` (the CLI exits 2). Before this ruling,
   a container written as `x.txt` could not be read back.
5. **One appender per queue file.** A second appender raises `ConcurrencyError` without a code in v1. A code is a
   1.1 candidate.
6. **Migration report.** `khg-migration-report/1.0.0` is a format id (§11.1) and is listed in `CONTRACTS`.
7. **I004's scope.** I004 means only a memory question without `stale_values` or `future_values`, as the registry
   says. Any other missing required field of a C4 item is I002. The unreleased `khg-c4-items/0.1.0` draft is
   corrected in place.
8. **Memory tolerance and unanswered questions.** A quantity tolerance is `{"amount": d}` on same-unit quantities,
   and a question without a response gets the outcome `missing` (strict 0, lenient 0). Both are v1 defaults that
   P3a confirms or replaces when it builds C4.
9. **Conformance exit status.** `khg-conformance` exits 1 when a scenario is `failed` or `cantTell`; `passed` and
   `inapplicable` exit 0.

**Director's rulings after the code review (2026-09-24).** The review confirmed 54 findings by reproduction and
fixed them (`impl-notes/review-*.md`); these are the questions it left open.
10. **Redirects (d-store-10).** A store never reaches a state whose own export fails validation. A write that sets
    `redirect_to` on an entity is refused with D020 while any record the store holds names that entity. Rewriting
    values to follow a redirect stays in 1.2 (§12.2). A conformance scenario for this refusal is a 1.1 addition,
    so that the v1 suite stays at 114 scenarios.
11. **Event field checks (d-store-13).** An event whose own fields are malformed is refused before the capability
    check and before the §6.2 order, as `put` refuses a malformed `actor` or `at` first.
12. **Violations kept by a trusted load (d-store-09).** A write that leaves such a violation no worse is accepted,
    but `keys.collisions` still blames an incoming asserted fact that takes part in it (W5's rule). P7 revisits this
    in 1.1.
13. **Evidence ids given twice in one new record (d-store-03).** No v1 code covers it: validation accepts such a
    record and the store keeps both evidence records (checked 2026-09-24). A code joins the registry in 1.1;
    until then producers must not repeat an evidence id within a record.
14. **`hif:weight` in C1.** Binding extensions stay passthrough (§2.2, §2.3). `to_hif` refuses a weight that is not a
    finite number with C010, so no invalid weight reaches a HIF file.
15. **Retrieval cut-offs (f-scorers-11).** The top k is the first k units by list position; the declared `rank` is
    a sort key only (W11b). P10 may ask for declared ranks in a minor release.
16. **Rank reasons in the Wikidata mapping (2026-09-24, from P3a).** §2.6 maps P2241 and P7452 to `rank_reason`.
    That holds only when the reason matches the rank: P2241 on a deprecated statement, P7452 on a preferred one.
    A reason on any other rank is kept as a `meta` binding under its property id. Validation is unchanged (C008
    still requires a reason on a deprecated statement). The naming P3a and P6 share is
    [wd-roles r1](../p6-schema-width/wd-roles.md).

**Director's ruling on P1 research 01 (2026-09-25).** Raised by
[P1 research 01](../p1-store-bakeoff/research/01-backends.md) §9 risk 1 and §10 D2.
17. **The version-table interface is public.** `khg_contracts.store.table` publishes the interface of
    `MemoryStore`'s version table (`VersionTableProtocol`, its 13 members `MEMBERS`, `Entry`, `VersionTable`,
    `bound_nodes`) and `TableStore`, the reference store over any version table: the write path of §6.2 and the reads
    of §6.3, with two hooks for a backend. `transaction()` wraps each `put`, `apply` and `load` in one backend
    transaction. `cannot_hold(record)` names a record the backend cannot hold. `put` and `apply` refuse such a
    record after every §6.2 check, and `load` treats it like a record that needs a missing flag. The refusal is a
    `ValidationError` without a code; no new KHG code. `MemoryStore` is `TableStore` over the in-memory
    `VersionTable` and behaves exactly as before. This is an implementation API of khg-contracts **outside the C2
    contract**: `khg-store/1.0.0`, its protocol, flags and 114 scenarios are unchanged, and a store that implements
    `Store` another way needs none of it. P1's adapters build on it and import public names only.

    *Addition to ruling 17 (2026-09-25, the director's ruling on P1 review 01, R-07; and R-02).* Still outside C2,
    still additive; `MemoryStore` behaves exactly as before (review 01's differential check, re-run, is identical).
    - **Header state.** The header `load` keeps and its embedded documents have public accessors on `TableStore`,
      `kept_header` and `kept_documents` (copies; settable when a backend reopens a store). A backend persists them
      inside the write's transaction.
    - **Rollback.** `writing()` restores both when the outermost write fails, so a failed `load` rolls the header
      back. The backend's `transaction()` rolls back the table. The clock is not rolled back; a failed write may
      have moved it forward, which only makes later transaction times later.
    - **An optional table member, `prefetch(records)`** (`store.table.OPTIONAL_MEMBERS`). `load` calls it once with
      the records it is about to check, before its checks read their ids. A backend table can then read those
      ids' versions in a bounded number of queries (none on an empty store) instead of one query per record.
      `VersionTable` does not have it.
18. **Records a backend cannot hold (2026-09-25, from P1).** A valid record that a backend cannot hold (an instant
    beyond its integer range, a relation shape its type system refuses) is refused with a `ValidationError` without
    a code, naming the reason in `info["cannot_hold"]`, as ruling 17 describes. As with ruling 13, a registered code
    joins the registry in 1.1 (a minor addition, §11). `load(..., on_missing="skip")` skips such a record and counts
    it in the `LoadReport` exactly like a record that needs a missing flag; every skip is a fidelity loss of that
    backend. The HIF profile (`khg-hif/1.0.0`) carries no store fields on entity nodes, so a HIF store answers
    `get(entity)` without `khg-recorded-by`; that stays a measured loss of the HIF format in 1.0, and adding it is a
    candidate for a profile minor version.

**Director's ruling on P1's fixes (2026-09-25).** Raised by [P1](../p1-store-bakeoff/README.md) Q5
(IMPLEMENTATION-NOTES §7): the HIF store could not load a slice that is not `complete`. Built 2026-09-26.
19. **A valid C1 container round-trips through HIF, complete or not.** A container that is not complete may name
    entities and facts it does not hold (§2.1), and so may its slices. `to_hif` wrote such an entity as an incidence
    node without a node record, and such a fact as a `khg-external` reference, but `from_hif` refused the file: D002
    for the node, and P017 for an external reference outside a slice. W6 and the S4 integration had recorded the gap
    without a ruling. The ruling makes it part of G1, P2's gate, rather than a P1 skip rule, with the smallest change
    that needs no `khg-hif` major version. What changed (§4.3, §4.5, §4.6;
    [impl-notes/ruling-19.md](impl-notes/ruling-19.md)):
    - **Reading.** In a file that is not complete (`khg-complete` absent or `false`) or is a slice, decoding reads an
      undeclared node without the `_:` prefix as the entity of that id, and P017 accepts an external fact reference.
      In a complete file both stay refused, and an undeclared derived node is D002 in any file.
    - **Writing.** `to_hif` writes the same records as before. It stamps a file `khg-hif/1.1.0` only when the file
      uses the addition (a node without a record, or an external reference outside a slice). Every other file is
      byte-identical and stays `khg-hif/1.0.0` (§11.2). Layer V reads 1.0.x and 1.1.x, both by the 1.1 rules.
    - **G1** runs two more chains: the fixture as a container that is not complete (without `ex:KingOfFrance`,
      `ex:TP53`, `ex:YYZ` and `f:born-louis14-paris`) and its directed slice. `golden-sha256.json` has their digests;
      the two earlier chains' digests are unchanged.

    **Versions.** `khg-hif` goes from 1.0.0 to **1.1.0**, a minor version. The profile's rules change (a P check and
    a decoding refusal), and a 1.0 reader refuses the new files, with V001 once they are stamped. `CONTRACTS["khg-hif"]`
    is 1.1.0. Unchanged: the profile schema, `role-convention` 1.0.0, C1 `khg-record/1.0.0`, C2 `khg-store/1.0.0`
    with its 114 scenarios, and every code; the registry's meanings of D002, P017 and layer P state the new rule.
    khg-contracts goes from 1.0.0.dev0 to **1.0.0.dev1**: 1.0.0 is not released, and its first release includes this.
    P1 can now run its HIF row on such slices. Its one test that pinned the refusal changes with this ruling (impl
    note).

**Director's rulings on the contract requests of the phase-1 designs (2026-09-26).** The director accepted each
request: P3a's (its DESIGN §11 and `notes/c4-change-proposal.md`; P3a rulings 2, 7 and 11), P7's (its DESIGN §7.2 and
§8 D4, D5; P7 rulings 4 and 5) and P9's (its DESIGN §3.8, §8 and §10 D5, D6; P9 rulings 5 and 6), read on the
branches `claude/p3a-corpus`, `claude/p7-identity-memory` and `claude/p9-extraction-gate` on 2026-09-26. They ship
as one minor release of the contracts, khg-contracts 1.0.0.dev2
([impl-notes/contracts-1-1.md](impl-notes/contracts-1-1.md)), built 2026-09-26. Every change is backward compatible: a valid file stays valid, and C2 `khg-store/1.0.0` with its 114
scenarios is unchanged.
20. **C4 `khg-c4-items` 0.2.0 (P3a's proposal, part A; P9's candidate table).** Every change is an optional field
    or a new enum value (§9.6):
    - the header names its corpus (`corpus {id, version, tier?}`), and its `record_format` is any `khg-record`
      version the reader takes (V001), no longer the constant `khg-record/1.0.0`;
    - split manifests admit the split `inference` and carry `scheme`, `seed`, `container {document_id, sha256}`,
      `probe {fact id: [leak kinds]}` and `lite`. A probe fact is a test fact of its manifest (I002);
    - extraction documents carry `doc_kind` (`wiki`, `rendered`), `source {url, revision?, licence?,
      attribution?}` and `gold_scope` as fields (P9 had planned `annotation.gold_scope` and `annotation.kind`, since
      `annotation` is open; the fields replace that), and `mentions`, P9's candidate table: C1 entity records, each
      with how it came into the table (`link`, `subject`, `match`, `distractor`) and its spans. The table is built
      from the text, not from the gold, so offering it does not leak the gold;
    - retrieval questions carry `answer_mode` (`single`, `set`, `count`), which the scorer reads before
      `RetrievalConfig.answer_mode` (which gains `count`); `provenance` stays open for P10's extras. P10's fixture
      questions keep `answer_mode` in `provenance`, which the scorer does not read, until P10 moves it to the field;
    - completion queries name their split manifest (`manifest`).

    The new checks use existing codes: I002 for what one line's schema cannot state (a mention span outside the
    text, an entity offered twice, a probe fact that is not a test fact) and I003 with S001 nested for a
    `gold_scope` relation outside the schema. The reader takes 0.0.x to 0.2.x and checks them by the 0.2.0 schema.
    `c4-items.jsonl` stays 0.1.0 and valid; `c4-items-0.2.0.jsonl` shows the new fields. Not in 0.2.0: C5's
    extraction scorer does not read `gold_scope` (P9 filters before scoring, as its design says). The memory
    changes are ruling 21.

    **Versions.** `khg-c4-items` 0.1.0 → **0.2.0**; its schema file is `khg-c4-items-0.2.0.schema.json` (it replaces
    the 0.1.0 file, which no other project names); `CONTRACTS["khg-c4-items"]` is 0.2.0.

**Clarifications the review made normative.** Each is implemented and tested; the notes give the evidence.
- §2.7 and D014: a history may go from `superseded` to `disputed` in one version (an undone supersession resolved
  by a dispute). An event still may not.
- §2.8.1: evidence carried into a later version without `supports` keeps the `supports` it resolved to in the
  first version that carries it. `normalize`'s default (every bid) applies only to evidence a record carries first.
- §2.3: a time literal's year has at most 16 digits (C004), an instant's at most 17 (C011); an integer literal in
  JSON has at most 16 digits (J006); JSON nests at most 256 levels (J001), in `jsonio` and in the schema checks.
- §2.10: the projection inverses take one version per fact; a `positional` width is a positive integer.
- §5 and §10.2: `Bundle.label` raises R002 for an exact repeat, and P010 in HyperNetX as in XGI. `strict=False`
  exports a collapse across edges and reports it under `moved_conflict`; `strict=True` raises P005.
- §6.2: a `put` that moves `status_ref` is D014.
- §10.2: `write_container` and `container_sha256` raise J005 for a value JSON cannot hold.

## Implementation plan

The package is built in dependency order. Each step lists its tests and the gate clause they serve (critique
BUILD-PLAN). Counts refer to `malformed-cases.json` (§8.2) and the scenario index (§6.4).

| Step | Module | Builds | Tests | Serves |
|---|---|---|---|---|
| W0 | scaffold | `pyproject.toml` (hatchling, extras, scripts, both licence files); `__init__` with `__version__` and `CONTRACTS`; `errors.py`; `data/` seeded from `design-examples/` (the vendored schema, sha256 639466b7…2196); `conftest.py` blocking sockets, with the markers `gate`, `libs` and `evidence`; the CI matrix | `packaging/`: import hygiene; the socket-block self-test; package data present with its hashes | all |
| W1 | `jsonio` | layer J (seven codes), canonical JSON with RFC 8785 numbers, `digest` | the 8 J cases; the 24 finite RFC 8785 vectors; `max 10` and `max 10.0` give one digest; `digest("khg-schema/1", fixture schema)` is `sha256:cadd01cd…194d` | G1, G2 |
| W2 | `schema/` | the meta-schema with `x-khg-code`; M001–M017; the built-in lifecycle relations and `khg:end_cause`; `load_schema`; `schema_hypergraph`; `is_alpha_acyclic` | the 19 M cases; `regulates` → [context, regulator, target] and `married` → [spouse]; the fixture schema α-acyclic; the cyclic and Wikidata-shaped schemas α-cyclic with the stated residue | G2; P6 |
| W3 | `record/` | values and literals; the precision windows (Julian through the JDN); value identity; ⊑; canonical form and `normalize`; `derive` and the accessors; `event_hash`; container I/O; `render_text`; the projections | `fixture.with-derived.c1.json` equals `derive` (`f:king-14`: `2706f2b5…d76b`, `5779b98f…e916`, `19b896a4…4a96`); the §2.3 window table; year 0 and pre-1583 refusals; the span 29–57 in code points; JSON and JSONL equality; the §2.4 arity table; the `render_text` and `positional` examples; 329 triples and 59 rows round-trip | G1, G2 |
| W4 | `validate/` core | the layer runner, the layer rule and pipelines, the registry, `engines.py` (closed resolvers), layers V, C and S | the 2 V, 20 C and 33 C1 S cases; code coverage with reserved codes skipped; single-fault engine containment; offline compilation with sockets blocked | G2 |
| W5 | lifecycle, keys, D checks, `identity` | D002, D007, D008, D010–D018, D020; `KeyCollision` info; L008; `identity.relate` | the 22 container D cases (MC118–MC139); the 37 identity rows of [DB §2.19]; the §2.5 action table | G2; P7 |
| W6 | `hif/` | `to_hif` (literal labels, literal nodes, weights, extensions, closed slices); `from_hif`; the profile schema and P checks; layer R | `to_hif` equals `fixture.hif.json` and the slice file; the round trip; `per_binding` and `schema_document`; the 15 H, 6 R, 24 P and 8 decoding D cases and MC063; the five role-convention files under layer R | G1, G2 |
| W7 | `loaders/` | `Bundle`, `Context`, construction, reconcile, the strict rule, `derive` and `label`, determinism | G1 in full: library objects, both native edits, and five hash-seed children against `golden-sha256.json`; the 20 native-operation rows; R03 c00–c26 (22 exact, 6 refused); the HyperNetX constructor keywords; the evidence test writes `library-hif-evidence.json` | **G1** |
| W8 | `store/` | `Where`, clocks, `StoreBase`, `MemoryStore` (flags, header state, events), export, `Timed`, `compare_containers`, the conformance runner with its EARL report | all 114 scenarios pass; with each flag removed, the TypeDB-like set and no flags, results are only passed or inapplicable; `load(on_missing="skip")` | G3; P1 |
| W9 | `queue/` | queue I/O and schema, the fold, `make_candidate`, `submit`, the structural `Linter`, `accept`, `replay` with a base | G3 in full, with replay reproducing `sha256:518db0f4…7f29`; the 17 Q cases; the regenerated smoke queue equals the committed file | **G3**, G2 |
| W10 | `migrate/` | `v0_sample_to_v1` | the four goldens; the report codes in order; the G1 chain on the migrated sample | C1's migration rule (PLAN §7) |
| W11a | C4 and layer I | `khg-c4-items-0.1.0`, `validate_item`, and `derive_memory_gold` (it reuses `MemoryStore`) | the 5 I cases; the M9 replays | **G2** (closes it) |
| W11b | `scorers/` | extraction (Hungarian), stability, completion (presets, calibration), retrieval, memory scoring, bootstrap, `khg-c5-io` checks | §9.7: the R05 tables through `r05.relation-schema.json`, and E12, C7b, R9 and M9 | F14 |
| W12 | CLI | `khg-validate`, `khg-convert`, `khg-migrate`, `khg-conformance` | one smoke test per command | release |
| W13 | `tests/consumers/` | the §1.3 sequences, verbatim, on `MemoryStore` with packaged data | P1, P3a, P3b, P5, P6, P7, P9 and P10 | consumer gates; the v1 scope filter |
| W14 | release and upstream | the wheel job; PyPI 1.0.0; the HIF issue and the fixture PR; the XGI and HyperNetX issues with `library-hif-evidence.json` | the wheel job | F15; PLAN §5 |

**Critical path.**
- W0 → W1 → W2 → W3 → W6 → W7 gives **G1**.
- W4 → W5 → W8 → W9 gives **G3** (W8 needs W3–W5).
- **G2** closes last, after W4, W5, W6, W9 and W11a. W11a is split from the scorers, so G2 never waits on C5.
- Once W3 is done, W11b (except memory scoring) runs in parallel with W6–W9. W10, W12 and W13 follow their
  dependencies.

## Prototype reuse

The prototypes in `research/designs/work-synthesis/` pass every check of §1.4. Start from the listed files, then
make the listed changes.

| Module | Start from | Change |
|---|---|---|
| `jsonio`, `record/`, `hif/` | `khg_synth.py` (strict JSON, RFC 8785 numbers, windows, identity, derived, `event_hash`, keys, collisions, lifecycle, `c1_to_hif`, `hif_to_c1`, `render_text`, projections) | split into modules; the typed API of §10.2 |
| `schema/`, `data/schemas/` | `khg_synth.Schema` and `schema_problems` (the M checks); `make_schemas.py` (four draft-07 schemas with propagated `x-khg-code` and absolute `$ref`s: record, profile, C4, C5 outputs) | ship the generated schemas as data; add the relation-schema meta-schema (W2) and the queue schema (W9), which the prototype replaces with Python checks, starting from [DB]'s `khg-schema-1.0.0.schema.json` and `khg-queue-1.0.0.schema.json` renamed to §3 and §7; keep the generator as a development tool |
| `validate/` | `khg_validate_proto.py` (layers and the layer rule); `khg_engines_proto.py` (closed resolvers for both engines); `make_registry.py`; `make_malformed.py` (the G2 harness) | read codes and cases from `data/` |
| `loaders/` | `khg_loaders.py` (from `research/probes/role_loaders_sketch.py`); `g1_chain.py`; `native_ops.py`; `r03_cases.py`; `run_evidence.py` | the `Bundle` API; tests from the three runners |
| `store/` | `khg_store_proto.py` (the store, `Where`, the clock, `compare_containers`); `make_scenarios.py` and `run_scenarios.py` | rename `ProtoStore` to `MemoryStore`; add `StoreBase` and the EARL report |
| `queue/` | `build_examples.py` (the smoke queue, candidates, accept, `decision_hash`) | a `Queue` class, the `Linter` and `replay` |
| `identity/` | `khg_synth.relate`; [DB] `run_identity.py` (37 rows) | non-normative only |
| `scorers/` | `khg_c5_proto.py` (memory gold, ECE binnings, bootstrap, binding coverage); `research/probes/scorers/c5_reference_cases.py` (expected values); `build_c4.py` | one `score()` per module |
| `migrate/` | `build_examples.migrate_sample` | a module and the CLI |
| examples and CI | `regenerate.sh`, `build_examples.py`, `build_c4.py`, `make_role_convention.py`, `validate_examples.py` | become `python -m khg_contracts.examples` and tests |

## Sources

**Programme and research inputs:** `projects/PLAN.md`; [R01]–[R05] in `research/` (`01-requirements-from-kb.md`,
`02-hif-standard.md`, `03-library-probes.md`, `04-prior-art-modelling.md`, `05-prior-art-scorers.md`).

**Designs:** [DA], [DB] and [DC] in `research/designs/` (`design-A-standards-first.md`,
`design-B-semantics-first.md`, `design-C-consumer-first.md`), their `work-*/` prototypes, and `work-synthesis/`.

**Primary sources:**
- Coll, M., Joslyn, C. A., Landry, N. W., Lotito, Q. F., Myers, A., Pickard, J., Praggastis, B., Szufel, P.
  (2025). *HIF: The hypergraph interchange format for higher-order networks.* Network Science 13, e21.
  https://doi.org/10.1017/nws.2025.10018 ; arXiv:2507.11520.
- HIF-standard at `b691a3d2ec32100c0229ebe1151e9afad015c356`, `schemas/hif_schema_v0.1.0.json` (blob e2105bb),
  https://github.com/HIF-org/HIF-standard ; release v0.1.2, https://doi.org/10.5281/zenodo.17257719.
- Landry, N. W. et al. (2023). *XGI: A Python package for higher-order interaction networks.* JOSS 8(85), 5162.
  https://doi.org/10.21105/joss.05162 ; xgi 0.10.2 on PyPI.
- HyperNetX 2.4.3, https://github.com/pnnl/HyperNetX/tree/v2.4.3 ; jsonschema 4.26.0 and fastjsonschema 2.22.2
  on PyPI.
- JSON Schema draft-07, https://json-schema.org/draft-07/json-schema-validation.html.
- RFC 8259 (JSON), RFC 8785 (JCS), RFC 6902 (JSON Patch), RFC 3339 (timestamps), RFC 3987 (IRIs), RFC 4151 (`tag:`
  URIs), https://www.rfc-editor.org/.
- W3C: *Web Annotation Data Model* (2017), https://www.w3.org/TR/annotation-model/ ; *EARL 1.0 Schema* (2017),
  https://www.w3.org/TR/EARL10-Schema/ ; *PROV-DM* (2013), https://www.w3.org/TR/prov-dm/.
- Wikimedia, *Wikibase JSON format*, https://doc.wikimedia.org/Wikibase/master/php/docs_topics_json.html ;
  Wikidata, *Help:Dates*, https://www.wikidata.org/wiki/Help:Dates.
- Kulkarni, K., Michels, J.-E. (2012). *Temporal features in SQL:2011.* SIGMOD Record 41(3).
  https://doi.org/10.1145/2380776.2380786.
- LinkML metamodel, https://github.com/linkml/linkml-model ; Nanopub-X ontology (`npx:supersedes`,
  `npx:retracts`), https://github.com/peta-pico/ontologies.

## Revision log

This revision answers the 87 findings of the four-lens critique: 8 blockers, 57 majors and 22 minors. Every
finding was applied. Where a finding offered alternatives, or where part of it was declined, the entry says so, and
§13.2 gives the basis. "Scenario" means a new conformance scenario, and "MC" a malformed case under the new
numbering.

**Gate and libraries**

| Finding | Severity | Done |
|---|---|---|
| GL-01 | blocker | MC115 carries a `schema_patch` that sets the severity to `error`. MC118 carries a `schema_patch` that lets claims take claims, so only D008 fires. The harness re-stamps the schema digest and checks every case against the full rule (§8.2) |
| GL-02 | major | layer = the code's letter; first rejecting layer by pipeline order; decoding emits S016 and the S pass D002; `validate_hif` without `khg-profile` reports P001, and `from_hif` refuses such files (§8.1, §4.3) |
| GL-03 | major | HyperNetX cells are the source of truth, with `khg-extra-incidences`; records keyed by (edge, `khg-bid`); a `moved` class for injective renames; `derive` and `label`; the operation table restated by strict outcome, one test each; XGI `subhypergraph` on a `DiHypergraph` unsupported (§5). No `allow_removals` flag: LOADER-STRICT's rule makes it unnecessary |
| GL-04 | major | G1 asserts the library objects, one native edit per library, metadata and network-type equality at every step, and header comparison in `compare_containers` (§1.2) |
| GL-05 | major | the context keeps loaded weights with their JSON number type; export prefers the library value only when it differs numerically; the fixture carries four weights (§4.2, §5) |
| GL-06 | major | RFC 8785 numbers; all 24 finite Appendix B vectors pass; `max 10` and `10.0` give one digest (§2.1, §1.4) |
| GL-07 | major | binding extensions map to incidence `khg-extensions`, and `hif:weight` to the incidence weight; P014 allows the key; `f:reg-1` b3 has nested extensions (§4.2) |
| GL-08 | major | node and edge records are exported for exported incidences plus loaded isolated nodes and empty edges; derived nodes left without incidences are dropped and reported; `ex:Mazarin` is isolated (§5) |
| GL-09 | major | profile files export in §4.2 order; other files keep source order, with new memberships by typed key; c12 and four seeds tested (§5) |
| GL-10 | major | closed resolvers for both engines, and compilation tested with sockets blocked (§8.1). Embedding the schema in the profile was declined: one hash-checked copy under its `$id` is simpler |
| GL-11 | major | `Queue.accept`; `replay(path, *, schema, factory, base=None)` loads the base first; `decision_hash` over `decision_view`; G3 loads the base (§7, §1.2). `event_hash` stays in the hash, because it is content fixed at extraction (SEM-12). Per-action methods replace a generic `decide` |
| GL-12 | major | typed loader and codec signatures; `validate=` modes; `records`, `roles` and the report; `from_hif` falls back to `khg-schema-document`, else D009 (§5, §4.3). `strict` stays on export only, where it acts |
| GL-13 | minor | the HyperNetX constructor call is pinned; a unit test; the ignored keywords are in the HyperNetX issue (§5, §12.4) |
| GL-14 | minor | the refusal is reworded: directed files only (§5) |
| GL-15 | minor | the context is authoritative for metadata; nothing is written into XGI network attributes (§5) |
| GL-16 | minor | `_:ref:` ids may have 518 code points; boundary case MC036 (§4.2) |
| GL-17 | minor | slices close over `status_ref`; references outside become external nodes (§4.6) |
| GL-18 | minor | G1 spawns five children (seeds 0–3 and unset) against `golden-sha256.json`. The CI matrix follows CI-MATRIX, because the probed numpy, SciPy and rpds-py need Python 3.11 (§1.2, §10.6) |

**Semantics**

| Finding | Severity | Done |
|---|---|---|
| SEM-01 | blocker | the bound table, the kind `ended`, `novalue` ends, and `end_validity` replacing a `novalue` end; S-TIME-009, S-VER-009 (§2.6) |
| SEM-02 | blocker | `schema_patch`, `doc_text` and the C4 base; the four store cases became history-container cases MC136–MC139; the old rule-relation case moved to 1.1; harness self-checks (§8.2) |
| SEM-03 | blocker | resolved with GL-01 and GL-02: MC118 is D008 only, and the layer rule is stated (§8.1, §8.2) |
| SEM-04 | major | shapes `succession`, `backfill`, `same_start` and `overlap_after_end` with a normative action table; M017; S-KEY-014, S-KEY-015 (§2.5). No `undated` shape: undated facts have no definite overlap under the bound table |
| SEM-05 | major | classes first (`merge` for duplicates and refinements), then the policy; quoted matches; S-KEY-016 (§2.5) |
| SEM-06 | major | the sentence is rewritten; `end_validity` takes `end_cause`, a meta binding mapped to P1534; the L104 lint and `validity_proposal` come in 1.1 (§2.7, §2.9, §12.2) |
| SEM-07 | major | the normative memory-gold table (§9.5); M9 tests |
| SEM-08 | major | an absent start is an unknown window; the per-kind read table; S-KEY-012, S-KEY-013, S-TIME-008 (§2.6) |
| SEM-09 | major | the disputed-key rule; disputes may include disputed targets; S-KEY-017 (§2.5) |
| SEM-10 | major | the "new id → disputed" row; event records arrive asserted; leaving drops `status_ref` (§2.7) |
| SEM-11 | major | D011 in three places; `terminal` defined; S-LIFE-012 and S-LIFE-014 (§2.7, §6.2) |
| SEM-12 | major | `event_hash` stored once at extraction, for extracted and inferred evidence, immutable; Q010 checks it (§2.9) |
| SEM-13 | major | key literals compare by value identity; refinement never merges key groups; L110 in 1.1; S-KEY-019 (§2.5) |
| SEM-14 | major | D018 per store, `at` only forward; S-EXP-010 (§2.6) |
| SEM-15 | major | the `timeless` default; S-READ-017 (§2.6) |
| SEM-16 | major | D020 refuses values naming a redirected entity; one shared `resolve_redirects`; S-PUT-010 (§2.2, §9.1) |
| SEM-17 | major | the `withheld` special value is listed for 1.1; case 4c is unclassified in v1 (§2.9, §12.2) |
| SEM-18 | major | seven cases: MC127, MC128, MC129, MC125, MC124, MC120 and MC084. Case 3 became the `novalue`-end overlap (MC129), because undated facts no longer collide |
| SEM-19 | minor | `resolve_superseding` on undo; S-LIFE-013 (§2.7) |
| SEM-20 | minor | the reason `refinement`; `duplicate` needs equal `content_key`; ⊑ ignores meta (§2.7, §2.9) |
| SEM-21 | minor | `supports` defaults per writer (§2.8.1) |

**Consumers**

| Finding | Severity | Done |
|---|---|---|
| CONS-01 | blocker | the normative window table; S-TIME-010 to S-TIME-012; `derived.valid_time` carries the instants (§2.3, §2.6) |
| CONS-02 | blocker | the C4 table in C1 terms, `c4-items.jsonl` with every kind, the draft schema under both engines, and the I cases rebased on it (§9.6) |
| CONS-03 | major | traces carry `entities` and `put: [records]`; `as_of` is an instant or null; actor `trace:<id>`; the question states `valid_mode` (§9.5) |
| CONS-04 | major | the instant grammar (C011); `where` with `valid_mode` and rank in C4 items; the per-kind read table (§2.1, §2.6, §9.6) |
| CONS-05 | major | `requires` computed from the operation, assertions and data; `@fixture[core]` with 20 core variants; `load(on_missing=…)`; `compare_containers(ignore=…)`. A TypeDB-like store now has 70 of 114 applicable (§6.3–§6.5) |
| CONS-06 | major | C's `rank_stats` keywords plus `model_rank`; `build_queries(slots, literal_targets)`; `model_arity`; presets and their approximations; the split manifest (§9.2, §9.3, §9.6) |
| CONS-07 | major | the system-outputs table (`khg-c5-io/1.0.0`); answer, abstention and cost defaults; `depends_on` (§9.1, §9.3, §9.4) |
| CONS-08 | major | the derived views: `render_text` (`khg-render/1`) and the projections; `text` became `source_text` (§2.10) |
| CONS-09 | major | the seven sequences are code against the synthesised API (§1.3), with every call in §10.2 and the four configs in §9.2; a stability run is (run_id, order_id) |
| CONS-10 | major | `entities` on items; the resolution order; Q011; S005 only on resolved entities; `validate_queue` takes the schema (§7). Embedding the schema in the queue header was not needed: the header pins its digest (D009) |
| CONS-11 | major | undated facts give L008 only; S-KEY-013 (§2.5) |
| CONS-12 | major | calendar-independent identity; a calendar required before 1583 (S006); `ExtractionConfig.calendar` (§2.3, §9.2) |
| CONS-13 | major | `info.collisions` lists every colliding record of the batch; S-KEY-018 (§2.5) |
| CONS-14 | major | closed slices, `khg-external`, `khg-complete: false`, P017; S-EXP-011 (§4.6) |
| CONS-15 | major | `literal_nodes="shared" \| "per_binding"` (`_:litb:`), `khg-literal-nodes`, `schema_document` (§4.2, §4.5) |
| CONS-16 | major | `meta` defined; P5102 and P1480 are qualifiers (§2.4, §2.6) |
| CONS-17 | major | the `doc_id` mapping for Wikidata references; `reference` in the `event_hash` payload (§2.8, §2.9) |
| CONS-18 | major | verdict bindings named by content tuple, with the bid as a hint (§7). Canonical bid numbering was not adopted: bids stay writer-assigned |
| CONS-19 | major | supports resolve through history (§2.8.1) |
| CONS-20 | major | `rdf_relation_instance` and `incidence_rows` in v1 with round-trip tests; the property-graph and TypeQL mappings are P1's (§2.10, §6.5) |
| CONS-21 | major | store-only rules left the list; MC115 has a real schema patch; the I cases have a base (§8.2) |
| CONS-22 | minor | `rank_reason` is a list, with `unspecified` on import; P2241 and P7452 map to it (§2.2, §2.6) |
| CONS-23 | minor | one appender through a `Queue` handle; `decision_view` (§7) |
| CONS-24 | minor | the runner computes `derived.*` selections (§6.4) |
| CONS-25 | minor | the pattern grammar; `[]`; optional positions; `ValueError` on a partial key (§6.1, §6.2) |
| CONS-26 | minor | the cyclic and Wikidata-shaped schemas; a role is one vertex (§3) |
| CONS-27 | minor | goal `brief` and `owner` may change; `bind` is sugar; new `Store` methods arrive as derived methods or behind a flag (§2.4, §11.2) |
| CONS-28 | minor | the entity version rule; S-VER-008 (§2.9) |
| CONS-29 | minor | `inference {rule: "model", from: []}` for completer output (§2.8) |

**Scope and build**

| Finding | Severity | Done |
|---|---|---|
| G2-CASES-NOT-EXECUTABLE | blocker | every case is machine-readable; the harness self-checks; `expect_target`; 180 of 180 pass mechanically; D019 is the one coverage exception (S-PUT-006) (§8.2) |
| G3-ACCEPT-REPLAY | blocker | `Queue.accept`; `entities` on items; the header's `base`; `replay(base=…)`; `decision_view`; the G3 sequence rewritten; `sha256:518db0f4…7f29` reproduced (§1.2, §7) |
| STORE-HEADER | major | header state in C2: `StoreInfo.store_id` and `header`, `export(header=…)`, the `store:<id>` default; S-EXP-009; a metadata row per backend (§6) |
| API-GAPS | major | the public API table; the `Clock` protocol; `MemoryStore(capabilities=…)`; streaming `load`; the `Timed` digest; `identity.relate` with seven labels (§10.2, §6.1) |
| PROJECTIONS | major | `positional` with its position map, `hyper_relational` and `role_value_set` in v1 (§2.10) |
| SCOPE-F13 | major | foreign import, the identity and quality lints, rule relations, proposals, `merge` and the two CLIs move to 1.1, and their codes are planned, not registered (§12.2, §8.1). Proposal kinds are not kept as v1 enum values: a 1.0 queue should not carry items no 1.0 tool can accept |
| ENGINES | major | agreement defined on single-fault inputs; closed resolvers; fastjsonschema in core (§8.1, §10.3) |
| G1-HASHSEED | major | the subprocess check against the golden digests; no separate CI hash-seed step (§1.2, §10.6) |
| PACKAGE-DATA | major | `data/` is the single source; `python -m khg_contracts.examples`; byte equality in CI; `expect_target` (§10.1, §8.2) |
| SAMPLE-MIGRATION | major | every rule pinned; four goldens; `migrate/v0_sample_to_v1.py`; `tests/migrate` (§11.3) |
| UPSTREAM | major | `role-position` is rule 4; layer R (R001–R004) and `kind="role-convention"`; the issue cites both precedents and the set-against-repeated-pairs question, and attaches `library-hif-evidence.json` (§4.1, §12.3) |
| C5-HANDCHECK | major | `r05.relation-schema.json`; E-M2 is `core_key` equality, plus E12; C8's order fixed; equal-mass bins defined, plus C7b; memory gold cases; R9 for `binding_coverage@k` (§9.7) |
| C5-IO | major | `khg-c5-io/1.0.0`; `c4-items.jsonl`; the kinds `expired` and `revised` and the `disputed` set; retrieval answer and cost defaults; the bootstrap algorithm (§9) |
| FIXTURE-VOCAB-REFS | major | vocabulary ids are not references; S-READ-019 (§2.1) |
| CI-MATRIX | minor | six CI jobs, with Python 3.10, 3.11 and 3.13, a wheel job and an examples job; the import-hygiene test (§10.6) |
| LOADER-STRICT | minor | the strict rule defined; whole-edge removals reported; one test per operation (§5) |
| CLI-SPEC | minor | four specified commands with exit codes 0, 1 and 2, and one smoke test each (§10.4). `--weight-as-confidence` moves to 1.1 with foreign import |
| VERSION-RELEASE | minor | the stamping rule, `CONTRACTS` stamped into `StoreInfo` and reports, the release plan, and the HIF licence notice in the wheel (§11) |
| BUILD-PLAN | minor | the Implementation plan, with the test directories it names (`identity/`, `schema/`, `migrate/`). The I cases stay in G2, and W11a builds layer I apart from the scorers, so G2 does not wait on C5 |

**Malformed-case renumbering.**
- MC001–MC025 keep their ids.
- The old P, D, C, S, M, Q and I cases moved as follows:

| Old | New |
|---|---|
| MC026 | MC026 (now R003) |
| MC027 | MC032 |
| MC028 | merged into MC026: R003 now rejects first |
| MC029, MC030, MC032 | MC034, MC035, MC037 |
| MC031 | MC027 (R001) |
| MC033, MC034 | MC028, MC029 (R001) |
| MC035–MC049 | MC038–MC043, MC045–MC053 |
| MC050 | MC031 (R004) |
| MC051 | MC030 (R002) |
| MC052–MC059, MC061 | MC054, MC056–MC062, MC064 |
| MC060 | MC063 |
| MC062–MC078 | MC065–MC072, MC074–MC076, MC078–MC083 |
| MC079–MC098 | MC085–MC095, MC098–MC106 |
| MC099 | MC107 |
| MC100–MC106, MC108, MC109 | MC108–MC114, MC116, MC117 |
| MC107 | MC115 (S024), plus MC156 (M015) for the `violation` severity |
| MC110 | dropped: rule relations come in 1.1 |
| MC111 | MC118 |
| MC112–MC115 | MC119, MC121–MC123 |
| MC116 | MC126 |
| MC117, MC119–MC122 | MC130–MC134 |
| MC118 | MC173 (Q010) |
| MC123–MC126 | MC136–MC139 (history containers) |
| MC127–MC142 | MC140–MC147, MC149–MC155, MC157 |
| MC143–MC148, MC150–MC156 | MC159–MC164, MC166–MC172 |
| MC149 | MC165 |
| MC157, MC158 | MC179, MC176 |

The 24 new cases are MC033, MC036, MC044, MC055, MC073, MC077, MC084, MC096, MC097, MC120, MC124, MC125,
MC127–MC129, MC135, MC148, MC156, MC158, MC174, MC175, MC177, MC178 and MC180.
