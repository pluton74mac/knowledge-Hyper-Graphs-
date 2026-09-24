---
title: "P2 implementation notes: review fixes, group b (schema, validate, data)"
type: project
status: draft
created: 2026-09-24
updated: 2026-09-24
---

# Review fixes, group b: `schema/`, `validate/`, `data/`

The review round's CONFIRMED findings for the validator and the schema language, the LOW ones that were cheap and
clearly right, and ruling 7 of the director (DESIGN §14). Scope: `src/khg_contracts/schema/**`, `validate/**`,
`data/**` (regenerated), `tests/schema/**`, `tests/validate/**`, and `design-examples/` through the examples tool.
DESIGN.md was not edited. Nothing was committed.

Every fix has regression tests that fail on the pre-fix tree and pass after it; a few tests beside them pin
behaviour that was already right. They were run both ways by putting a `git archive HEAD src` copy first on
`PYTHONPATH` (the table gives some of the counts).

## What was fixed

| Finding | Fix | Regression tests (fail before / pass after) |
|---|---|---|
| b-validate-01, X-04, b-validate-11 (LOW): RecursionError out of `validate`; the depth rule depended on the input form and the caller's stack | One nesting limit, `MAX_DEPTH = 256`, for objects **and** parsed text (`layers/j.py` scans after parsing; a bracket count skips the scan for shallow texts). `runner._call` turns a `RecursionError` into J001 and stops the run. `schema/checks._plain` became the iterative `json_copy`, and `check_schema` applies the same J001 rule (so `load_schema` of a mapping raises `ValidationError` J001, not `RecursionError`) | `tests/validate/test_nesting.py` (40 of 42 fail before): cases (a)-(f) (record with `derived`, embedded schema, HIF incidence, queue payload, container, C4 trace) run every step at the deepest accepted level and give J001 one level deeper, as objects and as text, under both engines; the review's 500-level objects and 980-level texts give J001; bytes and dict give the same J001 path; the verdict does not change 400 frames deeper; a container at the limit survives `to_hif`, `container_sha256` and the store; the runner's safety net. `tests/schema/test_m_checks.py::test_a_deep_document_is_j001_not_a_recursion_error` |
| b-validate-02: integral floats read as non-integers in layer S | `s._integral` (an int, or an integral float read as its int; None otherwise) for positions (S015), selector offsets (S021, sliced with the ints), `min`/`max` (S003, S004), `precision_min` (S023) and versions (`latest_records`). Layer D reads versions the same way (`d_container._version_key` for D001 keys and paths, `_versioned` copies for `lifecycle.history_problems`) | `tests/validate/test_numbers.py` (10 of 13 fail before): canonically equal float variants of the fixture (route positions, king-14 selectors with the texts, the HIF file's `role-position`, a history container, the reviewer's duplicate `2.0` version) give the int fixture's findings under both engines; a shifted float selector is still S021 |
| b-validate-04: a schema with float cardinalities disabled M010, S003, S004 and S023 | `schema.model.json_copy`: `Schema(doc)` keeps an iterative copy with integral floats within ±(2^53−1) as ints (the digest is unchanged, as canonical JSON already wrote them so). `python_findings` and `check_schema` read the same copy | same file: `Schema(float_doc) == Schema(int_doc)` and its usages hold ints; S003, S004 and S023 (MC113) with the float schema, directly and in a container run; M010 for `min 2.0, max 1.0` under both engines |
| b-validate-03: S023 read only the first literal filler of a datatype | The fillers are a disjunction (§3): a literal passes when any filler of its datatype allows it (`units` absent or listing the unit; `precision_min` absent or at most the precision). S023 names the least `precision_min`, or the union of the units | `tests/validate/test_literal_checks.py`: a unit or precision that a second filler allows; a filler without units allows any unit; MC113 and MC114 as before |
| b-validate-07: a year of more than 4300 digits raised `ValueError` | `_value_findings` reports any `ValueError` or `OverflowError` of the time parse as S006 at `/value/literal`. Group a has since bounded years in `record.parse_time` (16 digits, C004), so the tests accept C004 or S006 at the literal | same file: record, container, C4 trace (I003 with the refusal nested) and queue payload return findings under both engines; a monkeypatched `ValueError` is S006 |
| b-validate-05, F4: `$` in a pattern let a trailing newline through under jsonschema | The generator ends every pattern with `END = "(?!\\n)$"` (`codegen.anchor`, `end_anchors`, run by `build`): the plain end anchor in ECMA-262, and the end of the string in Python's `re`, whose `$` also matches before a final newline; fastjsonschema's `$` to `\Z` rewrite gives `(?!\n)\Z`. The generated schemas were regenerated. The jsonschema registry of `validate/engines.py` holds copies passed through the same `end_anchors` (`_end_anchored`: a no-op on the generated files), so the queue schema, which `queue/codegen.py` generates, is read alike | `tests/validate/test_schema_codes.py`: every generated pattern ends in `END`, and every pattern the jsonschema registry holds; a trailing newline on a document id, an entity id, an amount, a lang tag, an IRI, a `doc_sha256`, an evidence id, the header's schema version, a bid, a relation-schema version (M004; `load_schema` raises) and role id, a HIF node id (P003; `from_hif` raises), a `khg-bid` (P005 first), a C4 `qid` (I003) and a queue `qid` (Q008) is refused with one code by both engines |
| b-validate-06: `{"entitiy": ...}` was C002 under jsonschema and C001 under fastjsonschema | The value definition's map gains `"propertyNames": "KHG-C002"`, so both engines name C002 (as `record._common.value_kind` does) | `test_schema_codes.py::test_a_value_of_an_unknown_kind_is_c002_under_both_engines`; `test_engines.py::test_property_names_carry_one_code_for_both_engines` replaces the skip of `propertyNames` with a check that the parent's code equals the child's at every site |
| b-validate-08: a malformed `khg-*` edge attribute was a C code in the decoded container | The profile's edge `attrs` list the §4.2 attributes with the shapes of their C1 fields (`codegen._edge_attrs`: enums, lexical forms, the fixed shapes of `khg-confidence` and `khg-goal`, `khg-extensions` keys), all P012 by propagation. `khg-evidence` is an array of objects: the content of each evidence object stays layer C's on the decoded container, as a literal node's `khg-literal` does | `test_schema_codes.py`: 23 malformed attributes are P012 at `/edges/13/attrs/<key>`, first layer P, under both engines, and `from_hif` raises P012; well-formed attributes pass |
| b-validate-10: S021 ignored `doc_sha256` | `doc_texts` maps a `doc_id` or a `doc_sha256` to a text. S021 reads the text under the evidence's digest, else the `doc_id` text when it hashes to that digest (`record.text_sha256`, cached); another revision's text is not the evidence's, so the span is not judged. Evidence without a digest reads its `doc_id` text. The queue linter and layer I get the rule through `record_findings` | `tests/validate/test_spans.py`: a newer revision under the same `doc_id` gives no false S021; a two-revision container is valid with any of five text mappings; a shifted selector over the matching revision is still S021; a text under a digest it does not have is ignored |
| X-02: non-string ids and roles raised `TypeError` in the M checks | `isinstance(..., str)` guards on the three set lookups (the parents cycle, the time usages the time model names, the duplicate scale) | `test_m_checks.py`: three new shapes in `test_structurally_broken_documents_give_findings_not_exceptions`; `test_a_non_string_id_is_m015_from_every_entry_point` (`check_schema`, `validate` with the schema kind and auto, `load_schema`, a HIF file's inlined `khg-schema-document` through `validate` and `from_hif`) |
| b-validate-12 (LOW): `kind="auto"` refused a lone header line | `v.lone_header` and `detect_kind`: an object whose `kind` is `header`, `queue-header` or `c4-header` (and that is not a `{header, records}` container) is its file of one line; the runner wraps it as the lines of that file | `test_runner.py::test_auto_reads_a_lone_header_line_as_a_file_of_one_line` (the header line of the queue, C4 and container fixtures as an object, as bytes and as a list); an unhashable `kind` and a container object that also says `kind: header` are told apart |
| Ruling 7 (§14): I004 only for a memory question without `stale_values` or `future_values` | In the C4 draft the memory question's item schema keeps the default I002 (it had `{"default": I002, "required": I004}`), `stale_values` and `future_values` lose their own I004, and the separate `allOf` branch that requires the two arrays keeps I004. The draft is corrected in place (`khg-c4-items/0.1.0`, unreleased) | `test_schema_codes.py::test_i004_is_only_a_memory_question_without_stale_or_future_values`: a missing `stale_values` or `future_values` is I004; a missing `text`, `answerable` or key `role`, and a malformed `stale_values` or `future_values`, are I002, under both engines. No malformed case depended on the old mapping: MC179 removes `stale_values` and stays I004; G2 is green |

Regenerated with the tools: `data/schemas/` (record, relation-schema meta-schema, profile, C4; the C5 schema is
unchanged), `data/manifest.json` (`python -m khg_contracts.data`), and the three mirrored schemas of
`design-examples/schemas/` (`python -m khg_contracts.examples .../design-examples --tests tests`; nothing else
changed there).

## Decisions

- **`MAX_DEPTH` is 256, for every form of input.** W4 set 512 for objects on the premise that the parser refuses
  deeper text; it accepts about 990 levels on 3.11 (fewer from a deep stack, more on 3.13), and the package's
  recursive walkers (`normalize`, `copy.deepcopy`, the decoders, jsonschema's messages) overflow near 490 levels at
  two frames a level. 256 leaves room for the caller's stack; the tests run every kind at the limit on 3.10, 3.11 and
  3.13. The constant and the scan (`nesting_fault`) live in `schema.checks`, which `layers/j.py` imports, because
  `schema` cannot import `validate`. Group a's parallel change to `jsonio` adds `jsonio.MAX_DEPTH = 256` with the
  same semantics; `test_nesting.py` checks that the two agree.
- **A `RecursionError` in a later step is J001 and stops the run**, whatever came before, rather than a skipped step:
  the input is too deep for this process, and later steps would overflow the same way. It is a safety net only.
- **Integral floats are normalised where numbers are compared**, not in layer J: layer J still returns the input's
  numbers as they are, layers S and D read them through `_integral`, and a `Schema` holds ints.
  This is the package's F10 policy (W3, W6); `record.windows._precision` already read precisions this way.
- **End anchors in the generated files first.** Rewriting only the jsonschema registry would leave the packaged
  files lenient for every other Python user and would need the same rewrite in `record/_structure.py`,
  `scorers/_inputs.py` and `schema/checks.py`. `(?!\n)$` fixes the files once for every consumer and means the same
  as `$` under ECMA-262, the regex dialect JSON Schema names. The queue schema is generated by `queue/codegen.py`
  (group e), so its packaged file is unchanged here; the validator's jsonschema registry applies the same anchor to
  every schema it holds, which covers it now and is a no-op once its generator anchors too (request 3).
- **P012 checks the form of each `khg-*` edge attribute, not the C1 rules between fields** (C006, C008, C012), nor
  the content of evidence objects; those stay layer C's on the decoded container, and no G2 case moves.
- **S021 skips a text whose digest is not the evidence's `doc_sha256`**, as if no text were given, rather than
  reporting it: a text of another revision is not wrong, only not the one the selectors count in.
- **`check_schema` now reports J001** for a document nested deeper than `MAX_DEPTH`, beside its J007: it is the J V M
  pipeline on a parsed document, and without it `load_schema` of a pathological mapping overflowed in jsonschema's
  error message.

## Not changed, and why

- The record schema's time and instant patterns still allow any number of year digits (`[0-9]{4,}`). DESIGN sets no
  bound; group a's `record.parse_time` now refuses more than 16 (C004), so a longer year is C004 from the S step
  (another layer's code from the S step, as W4 noted for the time parse). Bounding the patterns too would move it to
  the C step; left to a ruling or to group a's request.
- `record/_common.nfc_deep`, `copy.deepcopy` in `queue/decision.py` and the HIF decoder stay recursive (not group b's
  files); layer J's limit keeps them inside the recursion limit, as the depth tests show for every kind.

## Requests to other groups

1. **CLI tests** (`tests/cli/test_validate.py::test_doc_texts_feed_the_span_check`): it swaps the text of
   `doc:coadmin-note` for another text and expects S021. By b-validate-10 a text that does not hash to the
   evidence's `doc_sha256` is not judged, so the test now fails. Perturb a selector instead, as
   `tests/validate/test_runner.py::test_doc_texts_are_a_mapping_a_doc_texts_document_or_a_path` does (for example
   `f:king-14` e2: `selectors[1]["start"] = 1`, with the packaged `fixture.doc-texts.json`).
2. **Scorer tests** (`tests/scorers/test_memory_layer_i.py::test_the_draft_names_i001_i002_and_i004`, lines
   215-216): by ruling 7 a memory question without `text` is I002; the expected code and the comment pinning the old
   breadth change to I002. W11a.md's observation 2 is superseded by the ruling.
3. **Queue codegen** (`queue/codegen.py`, `tests/queue/test_schema.py`): call `schema.codegen.end_anchors(schema)` in
   `build()` after `propagate`, so the packaged queue schema's 18 patterns end as the generated schemas' do. The
   validator already reads them so (its jsonschema registry anchors every schema), but other users of the packaged
   file with jsonschema would still let a trailing newline through. Then `data/schemas/khg-queue-1.0.0.schema.json`
   and `data/manifest.json` are regenerated (group b owns `data/` and can do it on request).
4. **Record** (`record/lifecycle.history_problems`): it sorts versions with `isinstance(version, int)`, so an
   integral float version sorts as 0. The validator now hands it normalised copies; direct callers would benefit
   from the same `_integral` reading.
5. **Consumers**: `tests/consumers/test_verbatim.py::test_the_copy_is_verbatim[P7]` fails at HEAD already: commit
   f99a8af changed DESIGN §1.3's P7 sequence and `tests/consumers/test_p7.py` was not updated. Not caused by this
   group.

## Full suite

`python -m pytest -q -p no:cacheprovider` from the repository root, on the shared working tree with the other groups'
changes in progress: **3 failed, 5693 passed, 1 skipped**. The three failures are requests 1, 2 and 5 above: two tests
that pin the behaviour b-validate-10 and ruling 7 change (their owners' files), and the P7 verbatim test, which
already fails at HEAD. `tests/schema` and `tests/validate` also pass under Python 3.10 and 3.13.
