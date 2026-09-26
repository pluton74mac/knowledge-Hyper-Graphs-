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

[p3a-note]: ../../p3a-clean-nary-corpus/notes/c4-change-proposal.md
