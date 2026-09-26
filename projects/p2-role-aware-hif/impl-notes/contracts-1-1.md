---
title: "P2 implementation notes: rulings 20-23, one minor release for the phase-1 contract requests"
type: project
status: draft
created: 2026-09-26
updated: 2026-09-26
---

# Rulings 20–23: one minor release for the phase-1 contract requests

The director accepted four groups of contract changes that the phase-1 designs asked for, to ship as one P2 minor
release after ruling 19: C4 0.2.0 and a `khg-scorers` minor release from P3a ([notes/c4-change-proposal.md][p3a-note],
P3a DESIGN §11, P3a rulings 2, 7, 11), P7's three C1 1.1 proposals (P7 DESIGN §7.2, §8 D4, D5; P7 rulings 4, 5) and
P9's three proposals and its candidate table (P9 DESIGN §3.8, §4, §8, §10 D5, D6; P9 rulings 5, 6). Those designs are
on the branches `claude/p3a-corpus`, `claude/p7-identity-memory` and `claude/p9-extraction-gate`, read on 2026-09-26
(the links below resolve once they merge). This note is the builder's record: the precise design of each item, the tests written first, and what changed. DESIGN §14 holds the
rulings (20 to 23).

- **Scope:** `src/khg_contracts` (schema generator, packaged data and manifest, layers V and I, the scorers), `tests/`,
  P2's DESIGN, README, `upstream/RELEASE.md`, `design-examples/` and one builder script under `research/probes/`.
- **Not edited:** other projects' folders (P3a, P7, P9, P10 and P1 get proposals, §7) and `kb/` (the director's).
- **Rule kept throughout:** every change is backward compatible. A valid file of any earlier version stays valid,
  and C2 `khg-store/1.0.0` with its 114 scenarios does not change.

## 1. C4 `khg-c4-items` 0.2.0 (ruling 20)

**What was asked.** P3a's part A: the split value `inference`; the manifest's `scheme`, `seed`, `container`, `probe`
and `lite`; the header's `corpus`; the extraction document's `doc_kind`, `source` and `gold_scope`; the retrieval
question's `answer_mode`; the completion query's `manifest`. P9's `mentions` (its D6, accepted as P9 ruling 6), and
`gold_scope` and the document kind as fields, not in `annotation` (the director's brief). P10's `provenance` extras
stay in the open `provenance`.

**Design decisions** (mine, recorded here; none changes scope):

| Question | Decision | Why |
|---|---|---|
| The shape of `mentions` | `[{entity: <C1 entity record>, source, spans?: [[start, end]], description?}]`, one entry per entity | P9's companion file has exactly this shape (`khg_extract.docs.load_candidate_tables`), so P9 reads the field without a converter. Embedding the record keeps the table apart from `entities` (the gold's), which is what makes it leak-free |
| `source` values | `link`, `subject`, `match`, `distractor` (required) | P3a builds wiki tables from links, the subject and label matches, and rendered ones from matches plus distractors (P9 §3.1). P9's `table` (no reason) and `minted` (the pipeline's own) are not corpus sources. P9 must add `distractor` to its `SOURCES` (§7) |
| Spans | `[start, end]` pairs, half-open, code points of the NFC text; I002 when empty, reversed or outside the text | the convention of position selectors (§2.8), and of P9's candidates |
| `source` fields | `{url, revision?, licence?, attribution?}`, all strings, closed | P3a's list. `revision` is a string (C1's evidence `source.version` is one too); a Wikipedia revision id is written `"1375387986"` |
| `doc_kind` | an enum `wiki`, `rendered` | P3a's two kinds; a new kind is a minor release |
| `gold_scope` | relation ids, unique; each a relation of the schema (I003, S001 nested); absent means "complete for every relation" | a typo would silently drop P9's in-scope predictions |
| `count` | one quantity literal of unit `"1"`, or none (I002 otherwise, by an if/then in the schema) | P3a's aggregation answers (§7.2 of its design) |
| `probe` | `{fact id: [leak kinds]}` with P3a's four kinds; a probe fact must be `test` in `splits` (I002) | P3a DESIGN §6.2 |
| `container` | `{document_id, sha256}` with `record.container_sha256`, the queue header's `base` convention | one digest convention for "this container" |
| `record_format` | any `khg-record` stamp the reader takes, gated by layer V | 0.1.0's constant `khg-record/1.0.0` would refuse question sets over C1 1.1 records (ruling 22) |
| The schema file | `khg-c4-items-0.2.0.schema.json` replaces the 0.1.0 file; the reader checks 0.0.x to 0.2.x by it | 0.2.0 only adds, so the old file is redundant; no other project names it (checked in the P1, P3a, P7, P9 and P10 worktrees). As ruling 19 reads HIF files, the reader does not enforce the stamp |
| New codes | none: I002 and I003 cover the new checks | the registry's meanings of I002 ("item structure") and I003 ("embedded C1 ... invalid") fit them |

**Not in 0.2.0.** C5's extraction scorer does not read `gold_scope`: P9 filters out-of-scope predictions before
scoring (its DESIGN §5). A scope parameter for `extraction.score` would be a later minor version (D-note in the
report).

**The retrieval scorer.** A question's `answer_mode` comes before `RetrievalConfig.answer_mode`, which is now the
mode of the questions that declare none, and gains `count`. `count` scores as `single` (the first answered value, by
value identity). Each item row names its mode, set metrics are averaged over the set-mode questions only, and
`breakdowns` gains `by_answer_mode`. A report of questions without `answer_mode` under a single-mode configuration is
unchanged but for those two additions.

**Tests first.** `tests/scorers/test_c4_items_0_2.py`, 58 tests, written before the change: **56 failed, 2 passed**
(the two that passed check that the 0.1.0 file stays valid, under each engine). After the change all 58 pass. They
cover the version gate (0.3.0 and a `khg-record/1.9.0` header are V001), every new field (accepted and malformed),
the three I002 checks, the I003 of `gold_scope`, code-point spans after an astral-plane character, `FilterIndex`
with `inference` facts, and the scorer's per-question modes.

**The example file.** `data/fixture/c4-items-0.2.0.jsonl` (8 lines; mirrored to `design-examples/`) is written by
`research/probes/c4_0_2_examples.py` from the gate fixture and is valid under both engines. Its `anchor_degree`
values are computed on the fixture under each question's `where` (King of France as of 1700: one fact).

**Existing tests changed** (each pinned the old version or a count): `test_api` (CONTRACTS), `test_examples` (147
mirrored packaged files, 152 files in `design-examples/`), `test_package_data` (17 fixture files; the schema file
name), `test_codegen` (the generated file name), `test_retrieval` (the new breakdown), `test_runner` (0.2.0 is now
read; 0.3.0 is the stamp that is too new).

## 2. C5 `khg-scorers` 1.1.0 (ruling 21)

### 2.1 `outranked` and the reasons (P3a part B; P7 DESIGN §7.2)

**Definition, as built.** For a question with key K, target role ρ, `where` W and τ, t: the ρ-values of the facts
on K that are asserted, of rank `normal`, and returned by `find_by_key(K)` under `{status: asserted, rank:
preferred|normal, visibility: all, as_of: W.as_of, valid_mode: W.valid_mode, as_at: τ}`, when that read also
returns a `preferred` fact. So "holds at t" is exactly the store's `as_of` semantics (§2.6), and with `as_of` null
every asserted fact holds. V_cur is subtracted; a value already `expired` or `revised` keeps that kind. Visibility
is not a condition, as for `expired` and V_fut.

| Question | Decision | Why |
|---|---|---|
| Which facts may outrank | an asserted `preferred` fact holding at t, of any visibility | P7's "a preferred fact on the key holds at t"; the same reading of "holds" as V_cur |
| Precedence | `expired`, then `revised`, then `outranked` | P3a's "after expired and revised in precedence" |
| The stale rates | `stale_expired_rate`, `stale_revised_rate`, `stale_outranked_rate` | 1.0 computed the revised rate as "stale minus expired", which would count outranked answers as revised |
| Ranked efficacy | outranked values are stale values for CounterFact's ES | ES asks whether the current value outscores the old ones; last year's population is an old one |

**The compatibility path.** Both changes change what `derive_memory_gold` returns, so a 0.1.0 memory set could fail
I005 under a replay with the new rules. Ruling 3 already tied the reason list to minor releases of the C4 draft, so
the rules are versioned with it: `memory.gold_rules(stamp)` gives the 0.1 rules for `khg-c4-items/0.0.x` and 0.1.x
and the 0.2 rules for 0.2.x (and for items without a header); layer I replays each file by its own stamp.
`derive_memory_gold`, `MemoryConfig` and `score` default to the 0.2 rules, as the brief requires ("the I005 replay
must agree" with the default). `score` checks by its configuration, not by the stamp: explicit is simpler, and no
0.1.0 memory set exists outside P2's fixture, whose three questions have the same gold under both rules (a test
checks it). A 0.1 set whose gold depends on the difference is scored with
`MemoryConfig(**memory.gold_rules("khg-c4-items/0.1.0"))`.

### 2.2 The order effect (P9 D5 b)

S-M7 now reports, over the pairs of (run_id, order_id) units: `same_order_diff_run`, `same_run_diff_order` and
`diff_run_diff_order`, each `{n_pairs, mean_jaccard}`; `delta_order` = J(same order, other run) − J(other order,
other run); and, for continuity, 1.0's `n_within_pairs`, `n_between_pairs`, `J_within`, `J_between` and its Δ as
`pooled_delta_order`.

- **Why this Δ.** Model a pair's dissimilarity by what differs. Where a run's two orders share a seed (P9's MLX
  runs at seeds 1-3, or its stub), a same-run pair differs by order alone; a cross-run pair by run and order; a
  same-order pair by run alone. Where runs are independent samples, same-run and cross-run pairs of different
  orders are exchangeable. J(same order, other run) − J(other order, other run) compares pairs that both differ in
  run, so it measures what the order adds in both cases. 1.0 put the same-run pairs into the second term, which in
  the first case makes it too high and Δ negative. `same_run_diff_order` stays visible: in the first case 1 − J is
  the order effect without run noise.
- **Checked on P9's fixture** (P9's khg-extract, copied read-only from its branch, run against this branch's
  khg-contracts): C5 1.1's three classes equal P9's own `paired_order_effect` to the last digit (pair counts and
  means). On the content key, raw output: Δ_order **0** (pooled −61/378); gated output: Δ_order **17/60 = 0.283**
  (pooled 31/135 = 0.230, which P9 DESIGN §7 reports). On the core key: raw 0 (pooled −0.119), gated 0.375 (pooled
  0.321).
- **P2's own P9 sequence** (`tests/consumers/test_p9.py`, three units, run-1 identical in both orders): Δ_order 0
  (1.0: −1/2).

### 2.3 Tests first

`tests/scorers/test_memory_1_1.py` (32 tests) and `tests/scorers/test_stability_order.py` (4 tests), written
before the change: **34 failed, 2 passed** (the two guards whose values hold in both versions: nothing is
outranked without a preferred fact, and a stale value keeps its first kind). After the change all pass. They cover
the ten reasons one by one (and three that stay out), `gold_rules` for each stamp, `outranked` on a non-temporal and
a temporal key (definite and possible reads, before, during and after the overlap), the precedence, the O3 outcome
and the three stale rates, the stamp-dependent replay in layer I under both engines, the packaged 0.1.0 file's gold
under both rules, and four order-effect cases (P9's order-blind case in small, R05's S3, an order effect under run
noise, an empty pair class).

**The example file** gains two traces and two questions (`mq:lodz-2019`: a rounded estimate outranked by the
preferred exact count, beside a deprecated "incorrect value"; `mq:maria-conflation`: a birthplace deprecated as a
conflation), whose gold the builder takes from `derive_memory_gold`. Stamped 0.1.0, both questions fail I005.

**Existing tests changed:** the defaults and signatures (`test_memory_score`, `test_memory_gold`), `hits` gains
`outranked` (`test_memory_r05`, `test_memory_score`), the preferred-only test now also sees the outranked value,
S3's `order_effect` gains the new keys (its Δ stays 2/3), P2's P9 sequence (Δ_order −1/2 → 0, pooled kept), and the
`khg-scorers` stamp (`test_api`, `test_extraction`).

## 3. C1 `khg-record` 1.1.0 and `khg-relation-schema` 1.1.0 (ruling 22)

### 3.1 Separator key roles (P7 D4 a)

| Question | Decision | Why |
|---|---|---|
| Where the opt-in lives | a second list, `key.separators`, beside `key.roles` | a key role keeps its 1.0 meaning (absent: no digest); a separator is a new kind of key member, so a schema says per role which it wants. P7's own words: "a key may name roles whose absence hashes as its own value" |
| What an absent separator hashes as | the tuple `[role, null, {"absent": true}]` in the `khg-key-digest/1` payload | explicit, and no value identity is an object with the key `absent` (value identities are `{entity}`, `{fact}`, `{literal}`, `{special}`, `{unbound}`), so it cannot collide with a present value. The domain stays `khg-key-digest/1`: 1.0 payloads never hold the marker, so no 1.0 digest changes (§11.2 keeps domains for majors) |
| A present separator | hashes as a key role | then `{roles: [a], separators: [b]}` gives a fact with b the same digest as 1.0's `{roles: [a, b]}`: separators generalise key roles |
| `somevalue`, `novalue`, `unbound` in a separator | the digest is null (exempt), as for a key role | an unknown value cannot be compared; `novalue` stays a special value, as for key roles. The conservative choice; a later minor version can hash `novalue` as absent if P3a meets it |
| `find_by_key` | binds every key role and any subset of the separators; an omitted separator is absent | a memory question about the group "subject S, no P518" binds only S. The error message of a key without separators is unchanged |
| `Schema.key(rel)` | gains `"separators"` only when declared | tests and P1's code compare or read the 1.0 dict |
| E-M2 with `core_roles="key"` | the core set is the key roles and the separators | the key's identity; both sides lacking a separator agree |
| M checks | M003: a separator that is not a core or qualifier usage, or is also a key role; the meta-schema: at least one, unique (M015) | the key-role rule applied to the new list |

### 3.2 Non-monotone qualifiers (P7 D4 b)

`monotone: false` on a usage: refinement keeps the role's size, exactly as for a `complete` role, and a new version
may not add a filler to it (D013, "adds a filler to the non-monotone role"). Values inside the role may still refine
(a `somevalue` to a value). Only qualifier usages may say `false` (M015 through the meta-schema: a time bound must
stay refinable by `end_validity`, and a core role that must keep its size is `complete`). The flag's name follows
P7's "non-monotone qualifier"; `monotone: true` is the default and is allowed anywhere. `keys.classify` and
`identity.relate` follow through `fact_refines`; so do D011's `refinement` reason and the completion scorer's
monotone filter.

### 3.3 `bound_conflict` (P7 D4 c)

One more reason in the built-in `khg:disputes` list. It is the only 1.1 feature a container can hold, so
`record.required_format` returns `khg-record/1.1.0` exactly for a `khg:disputes` record with that reason, and the
store's export raises a kept 1.0.x header to 1.1.0 when it exports one.

### 3.4 P3a's five normalisations

| Item | Adopted? | Where | Why |
|---|---|---|---|
| 1. Decimals to C1's form (`+1.50` → `+1.5`, `-0` → `+0`, no exponent) | yes | `canonical_decimal`, applied by `normalize` to quantity amounts and bounds | C004's pattern is the one canonical writing; any producer reading decimals from JSON, CSV or an LLM meets the others, and two writings of one number were two identities |
| 2. Time components below the precision set to zero | yes | `normalize`, time literals | S006 requires it and the window does not read them: `+1990-01-01T00:00:00Z/9` and `+1990-00-00T00:00:00Z/9` are one year. Any producer converting from a date type meets it |
| 3. Coordinates from JSON numbers to decimal strings | yes | `canonical_decimal` on geo `lat`, `lon`, `precision` | the rule of item 1 for another datatype; a float is written by its shortest decimal form (`repr`), which round-trips |
| 4. Wikibase ids to `wd:` ids, unit and globe URIs to vocabulary ids | no | P3a's importer | C1 ids are opaque, so `normalize` cannot know that `http://www.wikidata.org/entity/Q11573` and `wd:Q11573` name one unit: that is a naming convention of one source, its prefix map, not a canonical form |
| 5. A repeated filler (or a second `somevalue`) kept once | no | P3a's importer | it deletes a binding, which evidence may name by its bid (`supports`), and it is a data-cleaning decision about the source (Wikidata's duplicate qualifier snaks); for other producers the validator's S014 is the right signal. P3a saw it 14 times in 780,334 records |

- **Only the lenient path changes.** `canonical_literal(strict=False)`, which `normalize` and the canonical binding
  order use, writes the forms; the strict path, which value identity and the checks use, still refuses the other
  writings (C004, S006), so `validate_*` on a raw file reports them as before (MC094 unchanged). The store's `put`
  and `load` normalise before they check, as they already did for NFC, the default calendar and the case of a
  language tag, so they now accept a `1.50` and store `+1.5`. Nothing they accepted changes.
- **Guards.** A writing that would give more than 1,000 characters (`1e999999`) is left as written; a `float` must be
  finite; a `bool` is not a number; a string must match `[+-]?(digits[.digits]|.digits)([eE][+-]?digits)?` (so ` 1.5`,
  `1,5`, `NaN` and `Infinity` stay as written). A time is rewritten only when it matches the Wikibase form and its
  precision is an integer 0-14.
- **An existing test changed its meaning here:** `test_lenient_canonicalisation_never_raises_and_hides_nothing`
  pinned that the lenient path keeps a JSON-number amount. Item 3 is exactly that change; the test now shows the
  number written as `+3.5` by the lenient path and still refused (C004) by the strict one, and keeps its point with
  a non-decimal amount, which stays as written.

### 3.5 Versions, stamps and gates

- **Stamps.** `record.FORMAT` stays `khg-record/1.0.0` and `schema.FORMAT` `khg-relation-schema/1.0.0`: the stamps of
  documents without 1.1 features, which the sample migration writes (its goldens are byte-identical). `FORMAT_1_1`
  and `required_format` give the 1.1 stamps. `CONTRACTS` names 1.1.0 for both.
- **Gates.** V001 now takes `khg-record/1.0.x` and `1.1.x` in containers (`validate` and `record.check_container`),
  HIF metadata, queue headers (layer V and the fold) and C4 headers; and `khg-relation-schema/1.0.x` and `1.1.x`.
  Tests that used a 1.1 stamp as "too new" now use 1.2.
- **Schema files.** `khg-record-1.0.0.schema.json` is unchanged (nothing in the record schema changes; the reason
  list is S026's, in Python). `khg-relation-schema-1.1.0.schema.json` replaces the 1.0.0 meta-schema.
- **The store.** `StoreInfo.record_format` is `khg-record/1.1.0` (the EARL report says so); exports are stamped by
  their records.

### 3.6 Tests first

`tests/c1/test_record_1_1.py`, 73 tests, written before the change: **49 failed, 24 passed**. The 24 are guards of
what must not change: 1.0 stamps accepted and 1.2 refused, the digest of a key without separators, canonical and
non-decimal inputs kept as written, a precision-14 or malformed time kept, the fixture canonical, the importer's
rules left out, a read of the fixture. After the change all pass. They cover every gate, both `required_format`s,
the six M003/M015 separator cases, the digest of absent, present and special separators (against a hand-built
payload), collisions and `find_by_key` in `MemoryStore`, E-M2 on key roles, the `monotone` flag (M015, refinement
both ways, `relate`, D013 in the store), a `bound_conflict` dispute written, exported as 1.1.0 and valid, and
sixteen decimal writings, eleven non-decimals, coordinates and eleven time cases.

**P1's `NativeReads.find_by_key`** copies `StoreBase`'s role check. With a schema that declares separators it would
refuse a pattern that binds one. The change, for P1's second half (not made here: P1's folder):

```python
roles, separators = set(declared["roles"]), set(declared.get("separators", []))
if not roles <= {p.get("role") for p in patterns} <= roles | separators:
    raise ValueError(f"find_by_key binds exactly the key roles {sorted(roles)}"
                     + (f" and any of the separators {sorted(separators)}" if separators else ""))
```

Its lookup is on the stored key digest, which `record.key_digest` computes, so nothing else changes.

## 4. C3 `khg-queue` 1.1.0 (ruling 23)

### 4.1 The recorded reading (P9 D5 a)

As P9 DESIGN §3.8 defines it, and as the director's words put it ("a queue that correctly rejected a malformed
candidate at lint is valid"): a C or S finding (by its code) on an item line is recorded when the item's folded
state is `rejected` and one of the item's lint entries lists a finding with the same code, at the same path relative
to the item line, as an error. `queue.recorded` builds the map from the fold; `Context.recorded` caches it per run;
layers Q (its C codes on item entities), C and S apply it to their own findings before the runner decides whether
to stop, so `stop="first"` does not stop at a recorded error.

| Question | Decision | Why |
|---|---|---|
| Drop recorded findings, or keep them | keep them, as `info`, with a message naming the lint entry | a reader still sees what was rejected and why (P9 counts them); `info` never invalidates, and a warning would ask for attention a correct queue does not need. An emitting layer may lower a registered severity (the registry says so; S003 on candidates is the precedent) |
| Which items | `rejected` only | the ruling's words; the fold already refuses to accept an item whose lint has an open error (Q005), so such an item ends rejected or withdrawn |
| Which findings | C and S codes only; the lint must have recorded the same code at the same path as an error | P9's rule. An error the lint did not record (say, S021 found with a text the linter did not have) still fails; so does every J, V, Q and D finding |
| Q codes on a rejected payload (Q009, Q011) | not covered | outside the ruling; P9's queues cannot produce them (minted entities travel in `item.entities`). A decision for the director if another producer needs it |
| Queue stamp | files keep `khg-queue/1.0.0` | 1.1 changes no line of the format; an append-only file's header cannot know whether the file will ever hold a rejected malformed candidate, and "stamp the lowest version" (§11.2) then says 1.0.0. A 1.0 reader of such a file reports the payload errors, which is a stricter judgement of what is there, not a misreading |

### 4.2 Q013 (P9 D5 c)

`queue.checks.quote_findings`, called by `Linter._findings` after the other structural checks: for each evidence
record with selectors and no position selector, when the linter has its text (`validate.layers.s.source_text`, the
text S021 reads: the one its `doc_sha256` hashes, else its `doc_id`'s when that one hashes to it), each quote
selector whose `prefix + exact + suffix` (absent parts empty; NFC of the whole) does not occur in the NFC text is
Q013 at `/payload/evidence/<k>/selectors/<j>`, an error.

| Question | Decision | Why |
|---|---|---|
| What to flag | an unlocatable quote, not every quote without a position | P9's defect is that an unlocatable quote passes. A quote alone is a valid W3C TextQuoteSelector and C1 allows it (C007); where it occurs in the text it is locatable |
| Without the text | nothing, as S021 | the linter cannot judge; P9's pipeline passes the texts (`khg_extract.pipeline`, `Linter(schema, store=st, doc_texts=...)`) |
| Error or warning | error | the same failure as S021 (the evidence does not select what it quotes); the candidate is rejected, which is what P9's gate did itself |
| Which code | a new code, Q013 | the registry's rule: a new check gets a new code. Q: it is a check of queue items, beside Q009 (evidence against the item's doc), and the structural rule set's errors are C, S and Q codes. Not an L code: lints advise (info, warning) and the planned L numbers belong to the identity and quality rule sets. Not an S code: layer S runs in every validation with texts, where it would make files valid under 1.0 invalid |
| The validator | does not repeat Q013 | "existing valid files stay valid": a queue linted under 1.0 whose accepted candidate cites an unlocatable quote stays valid. `malformed-cases.json` lists Q013 as a coverage exception, beside D019 |

`khg-lint` 1.1.0 runs the structural rule set 1.1.0. Every new lint entry names both, so the G3 smoke queue's lint
line changes (the packaged golden and its mirror are regenerated; G3 checks that the API writes it byte for byte);
its decision hash is unchanged. `khg-codes` goes to 1.1.0 with Q013 (135 registered, 129 active); the `Registry`
class reads 1.0.x and 1.1.x registries.

### 4.3 Tests first

`tests/queue/test_queue_1_1.py`, 31 tests, written before the change: **15 failed, 16 passed** (the 16 are guards:
1.0 accepted and 1.2 refused, errors that must stay errors, locatable quotes and quotes without a text or with a
position selector, a text of another revision, the validator not repeating Q013, the `Linter` call). After the change
all pass. **Existing tests changed:** the registry counts (`test_registry`, `test_package_data`, `test_coverage`,
`test_malformed`: 124 checked codes, the exceptions D019 and Q013), `CONTRACTS` (`test_api`), the linter's versions
(`test_linter`), `khg-queue/1.1.0` is now read (`test_queue`: the stamp that is too new is 1.2.0), and
`queue.FORMAT` stays the 1.0.0 stamp (`queue/test_api`).

## 5. What consumers change

| Project | Change | Needed when |
|---|---|---|
| P3a | may stamp its sets `khg-c4-items/0.2.0` and use the new fields (`inference` and the manifest fields replace its sidecar `.meta.json`; `mentions`, `gold_scope`, `doc_kind`, `source`, `answer_mode`, `corpus`); memory gold from `derive_memory_gold` now follows the 0.2 rules, so a memory set built with this release is stamped 0.2.0. `normalize` now does its items 1-3 (idempotent with its converter, which may keep them) | W7-W9 |
| P9 | its tests follow rulings 21 and 23: [contracts-1-1-p9-tests.patch](contracts-1-1-p9-tests.patch) (five tests: the order effect's pooled value, the recorded reading, Q013 rejecting run-3's unlocatable quote at lint, `khg-queue` 1.1.0). With it, khg-extract's 22 tests pass against this branch. `khg_extract.docs.SOURCES` must add `distractor` to read C4 `mentions`; `c3_check`'s strict reading now equals the recorded one | before P9 merges the bundle |
| P1 | `khg_bakeoff.native.NativeReads.find_by_key`: the four-line separator change of §3.6, before it holds a schema with separators. Nothing else: its HIF, SQLite, Oxigraph and PostgreSQL paths read keys through `record.key_digest` | P1's second half |
| P7 | the non-monotone flag and separators are declared in schemas; `bound_conflict` is a dispute reason its planner may write (its D1); `outranked` is in the gold its comparison scores | its memory comparison |
| P10 | may move `answer_mode` from `provenance` to the item field; the scorer reads the field, not `provenance` | its next question set |
| P6 | nothing: khg-width reads schemas stamped 1.0.0 or 1.1.0 | |

[p3a-note]: ../../p3a-clean-nary-corpus/notes/c4-change-proposal.md
