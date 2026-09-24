---
title: "P2 implementation notes: review fixes, group f (scorers)"
type: project
status: draft
created: 2026-09-24
updated: 2026-09-24
---

# Review fixes, group f: `scorers/`

This group covers the review round's CONFIRMED findings for the C5 scorers. It also takes the LOW ones that were
cheap and clearly right, and fixer b's request for ruling 7.

- **Scope:** `src/khg_contracts/scorers/**` and `tests/scorers/**`.
- **Not edited:** DESIGN.md and the W-step notes. The notes they supersede are listed below.
- **Not committed:** nothing.
- **Earlier attempt:** the interrupted attempt left no edits in these paths, so this work started from HEAD.

**How the fixes were checked:**

- **Before and after.** Each regression test was run against the pre-fix scorers: a copy of the working tree's
  `src` with `git archive HEAD src/khg_contracts/scorers` in place, put first on `PYTHONPATH`.
  - Pre-fix: 27 of the 252 tests in `tests/scorers` fail, all of them new or updated here.
  - After the fixes: all 252 pass.
- **Mutants.** The findings about untested behaviour (f-scorers-09, -10, -14) come with tests that pass on the
  pre-fix tree, which was correct. Each such test was checked on a scratch copy against the verifier's mutants
  instead, and it kills them.

## What was fixed

| Finding | Fix | Regression tests |
|---|---|---|
| f-scorers-01 (high): E-M3's pair weight (N+1)·ν + β is value-first only within one pair; over an alignment, Σβ can outweigh a unit of ν, so qids decided Arg-I, Arg-C and role accuracy | `extraction._alignment` uses w = M·ν + β with M = 1 + min(Σ\|B_p\|, Σ\|B_g\|). Any alignment's Σβ is below M, so the maximum is lexicographic over the document: largest Σν, then largest Σβ, then the id tie-break. The weights stay exact integers for both solver backends | `test_extraction.py`: `test_the_alignment_takes_values_then_bindings_over_the_document` (the review's 4-gold/3-prediction document and the verifier's r4 counterexample, (9, 7) against (10, 2), in every submission order); `test_the_review_document_aligns_the_shared_values`; a seeded brute-force check of (Σν, Σβ) on 80 r4 documents. The R05 values do not change |
| f-scorers-02 (high): text-only gold scored a missing, abstaining or text-less response as None, so these questions dropped out of every answer average | `retrieval._answer`: against a gold text, such a response scores text EM = token P = R = F1 = 0, as a missing value answer does. EM, the joint scores, gated EM, the breakdowns and the bootstrap follow | `test_retrieval.py::test_text_only_gold_scores_a_missing_answer_as_zero`. The four-question set gives EM 0.25 (it gave 1.0), gated EM 0.25 and joint EM 1/3; the missing response claims no support, as with value gold |
| f-scorers-03: the budget curve's denominator left out answerable questions without a response | `_budget(rows)` takes every row. Only responses spend tokens, and the denominator is every answerable question. Input order stays, as W11b recorded it (the verifier did not count it as a defect) | `test_retrieval.py::test_the_budget_curve_counts_every_answerable_question`: 0.25 at 100 %, equal to the answer EM (it was 1.0) |
| f-scorers-04: one entity index pooled every run's records and applied them to gold too | Gold resolves through the gold documents' records only. A prediction resolves through its own queue item's records first, then the gold's (`_facts.item_entities`, a ChainMap; DESIGN §7's order, "item.entities first"). Extraction and stability share it | `test_extraction.py`: `test_an_items_entity_records_resolve_only_its_own_values` (r2 alone and beside r1; stability's J(r1, r2) = 0; run order irrelevant); `test_a_predictions_entity_records_never_rewrite_the_gold`; `test_extraction_and_stability_resolve_entities_alike` |
| f-scorers-05: a `model_rank` outside the tie block was scored at that rank | `completion._rows`: `model_rank` outside [o, p] is C010 at `/<qid>/model_rank`, like the existing `p > size` check | `test_completion.py::test_a_model_rank_outside_the_tie_block_is_c010` (the review's record under `rank="model"`, `stare` and the default; the bounds of a [2, 4] block) |
| f-scorers-06: under a quantity tolerance, an exact current answer became hedged, and an exact stale answer got lenient credit | `memory.classify` matches by identity first. An answered value equal to a value of V_cur, V_old or V_fut matches by identity only, and the tolerance reaches only values that equal none of them. Disputed values are left out of this test, so a disputed value still never changes the outcome (W11a) | `test_memory_r05.py::test_m8_a_tolerance_never_blurs_an_exact_answer` (the 19 → 18 correction: 18 current, 19 stale, 17 current, 20 stale); `test_a_disputed_value_still_never_changes_the_outcome_under_a_tolerance` |
| f-scorers-07: with no unit (K = 0), S-M5 called every gold fact stable | `stability._partition` returns None shares, with `n_gold`, when there is no unit | `test_stability_r05.py::test_without_any_unit_the_gold_partition_is_undefined` |
| f-scorers-08 and X-03: malformed inputs escaped as KeyError, TypeError or a bare ValueError, or were scored; one S006 came out at the path `''` | (1) `_inputs.predictions` runs layer C (`khg-record#/definitions/hyperedge`, as `validate_queue` checks payloads) on every queue payload and bare hyperedge, at `/lines/<n>/payload` or `/lines/<n>`. A goal is C010 at `…/status`. (2) `_facts.prepare` raises `ValidationError` for what it cannot read, with paths relative to the record: C010 for a goal (it was ValueError), S001 first, S007 for no binding, S002, and S015 for positions under layer S's rule. (3) Extraction and stability locate a prediction's error at its line (`_inputs.located`); gold errors are I003 via `embedded_error`. (4) Retrieval: a gold answer value without an identity is I003 at `/questions/<n>/answer/values/<k>` (as memory reports it); a response value gets its code at `/lines/<m>/answer/values/<k>` | `test_io.py`: `test_a_malformed_prediction_is_a_validation_error` (10 faults × queue item and bare hyperedge × both scorers); `test_an_ordered_role_without_a_position_is_s015` (prediction and gold); `test_a_goal_in_the_gold_is_i003`; `test_a_value_without_an_identity_is_located`. The verifiers' `x03_repro.py`, `x03_bare.py` and `v08_malformed.py` now give located `ValidationError`s only |
| f-scorers-09: the `model_arity` tables were never tested where they differ from `arity` | Tests only | `test_completion.py::test_every_per_arity_table_is_given_on_model_arity_too`: macro, `by_arity` and `calibration_by_arity` on both arities, checked bin by bin against the queries. `test_extraction.py::test_the_macro_arity_average_is_given_on_model_arity_too`: arity {p 1, r 5/6, f1 0.9, n 2} against model arity {1, 2/3, 2/3, 3}. They kill all four of the verifier's mutants |
| f-scorers-10: joint EM and nDCG's first-unit rule were never asserted | Tests only | `test_retrieval_r05.py`: `test_r5_joint` adds joint EM 0 (partial support) and 1 (exact support); `test_r9_binding_coverage` asserts nDCG@1 = @2 = @4 = 1. They kill both mutants |
| f-scorers-12 (LOW): set P/R/F1 were computed against the empty value set of a text-only gold | In set mode, set P/R/F1 are left out when the gold has text and no values. A gold that is the empty set, with no text, is still scored as a set (`both_empty`) | `test_retrieval.py::test_set_scores_need_a_gold_value_set` |
| f-scorers-13 (LOW), in part: stability accepted a repeated `doc_id` silently | I002 at `/docs/<n>/doc_id`, as extraction reports it | `test_stability_r05.py::test_a_repeated_doc_id_is_i002_as_in_extraction` |
| f-scorers-14 (LOW): no scorer's bootstrap interval was pinned | Tests only | `test_bootstrap.py::test_every_scorer_reports_the_documented_interval`. It writes out the §9.1 procedure (`random.Random(0)`, `int(rng.random() * n)`, fsum means, ⌊0.025·R⌋ and ⌊0.975·R⌋ − 1). It pins memory `acc_strict` and `acc_lenient`, completion `mrr` and `hits@3`, retrieval `em` and extraction `strict.f1` on each scorer's own per-unit values, and kills the lenient-from-strict, seed-7 and strict-from-Arg-C mutants |
| Fixer b's request (ruling 7) | `test_memory_layer_i.py::test_the_draft_names_i001_i002_and_i004`: a memory question without `text` is I002. The comment now cites ruling 7 | the test itself (it failed on the working tree after fixer b's draft change) |

`tests/scorers/test_io.py::test_extraction_outputs` was also changed:

- Its bare hyperedge now carries valid extracted evidence (with `selectors` and `activity`), and the old incomplete
  evidence is pinned as C007.
- The bad payload value is pinned as layer C reports it: C001 at the value and C004 at its literal (it was C001
  alone, raised later by the value parser).

## Decisions

- **E-M3 is lexicographic over the document** (DESIGN §9.3, "on values, then bindings"; R05 D-C5-02, "value overlap
  with binding tie-break").
  - R05's M = N + 1 is taken as an encoding of that intent: it is exact per pair, but not over the sum that the
    Hungarian solver maximises.
  - M = 1 + min(Σ|B_p|, Σ|B_g|) is the smallest multiplier that is always correct, and it keeps the weights small
    integers.
- **Entities resolve per item, then gold**, as the queue linter resolves them (DESIGN §7).
  - A plain entity record on an item shadows a gold redirect of the same id for that item's own values only. That is
    the §7 order.
  - A run's items do not share records. If run-level sharing is ever wanted, it should be no wider than the run.
- **What a scorer refuses and what it scores.**
  - A structurally malformed prediction is refused. This means layer C, the same check `validate_queue` applies to
    payloads.
  - A prediction the scorer cannot read is refused: S001, S002, S007, S015, and a value without an identity.
  - Other S findings (cardinality, filler types, constraints, spans) leave a fact readable, so it is scored as it is.
    W11b's rule that "every item passed is scored whatever its folded queue state" still holds for candidates the
    linter would reject.
  - S015 follows layer S's full rule (positions 1..n on an ordered role, none on an unordered one), so the scorers
    and `validate_record` agree.
- **Goals are C010** (for a gold goal, I003 with C010 nested). No registered code means "a goal where a fact is
  scored", and C010 ("out of range") is what `predictions` already used for a payload that is not a fact.
- **Bare hyperedges must be valid C1 hyperedges.** Extracted evidence therefore needs `doc_sha256`, `selectors` and
  `activity` (C007). Before this round, a bare hyperedge only needed a `source.doc_id`.
- **The tolerance rule leaves out the disputed set.** The verifier's variant included the disputed set in the
  exactness test. That lets an answer equal to a disputed value lose the tolerance match to V_cur, which changes the
  outcome, and the W11a rule forbids that.
  - When an answer that equals no gold value lies within the tolerance of both a current and a stale value, it is
    still hedged. It is ambiguous, and a nearest-value rule would need a tie rule that DESIGN does not give.

## Not applied

- **f-scorers-11 (LOW): cut-offs by declared `rank` instead of list position.** This conflicts with W11b's recorded
  decision:
  > "Units are read in rank order (input order among equal ranks); hyperedges(L[:k]) is the union of the top-k
  > units' hyperedge_ids"

  The rank is a sort key and the position defines the top k, and `memory._support` does the same. The alternatives
  are to use the declared ranks or to reject ranks other than 1..n (C010). Choosing between them is a contract
  decision for the director or P10, not a fix.
- **f-scorers-13, the path part.** Duplicate ids stay I002 at `/docs/<n>`, `/questions/<n>` or `/queries/<n>`, where
  n is the index among the items the scorer reads. The memory scorer documents that convention (W11a: "Paths are
  `/questions/<n>`, `/traces/<m>` and `/responses/<k>`"), and moving it into `check_items` as `/lines/<n>` would
  change all four scorers. Only the stability gap was closed.
- **f-scorers-03, input-order independence.** It was proposed as optional. The budget curve keeps W11b's input
  order, and the verifier did not count it as a defect.

## Notes superseded

These are recorded here because the W-step notes were not edited.

- **W11b, Extraction, "Alignment (E-M3)".** "N is the largest binding count …, so w = (N+1)·ν + β orders by ν, then
  β" becomes M = 1 + min(Σ|B_p|, Σ|B_g|), with a lexicographic order over the document.
- **W11b, Extraction, first bullet.** "Entity values follow `redirect_to` over the entity records of the gold
  documents and the queue items" now reads per item, then gold; gold uses gold records only.
- **W11b, Retrieval, "Answers".** The rule "Answer metrics average the answerable questions" now also holds for
  text-only gold. The budget curve is "over all answerable questions", as its docstring always said.
- **W11b, Completion, "Ranks".** A `model_rank` outside the tie block is C010 too.
- **W11b, Inputs, extraction outputs.** Payloads and bare hyperedges run layer C, and goals are C010.
- **W11a, "Tolerance".** A quantity within the tolerance matches, unless the answer equals a gold value of V_cur,
  V_old or V_fut exactly.
- **W11a, observation 2** (I004's scope) is superseded by ruling 7, as fixer b noted.

## Checked

- **Full suite:** 5847 passed, 1 skipped in 132.64 s. The dev venv runs Python 3.11 with every extra, and the run
  includes the other fixers' work as it stood then (an earlier run gave 5830 passed).
- **`tests/scorers`:** 252 passed.
- **Other Pythons:** `tests/scorers` and `tests/consumers` give 279 passed and 2 skipped (the SciPy checks) under
  Python 3.10.20 and 3.13.12, with `PYTHONPATH=src`.
- **Lint:** ruff (F, E9, E501, W, B at 120 columns, py310) reports nothing new; the eight B008 are the §9.2
  signatures, as before.
- **Types:** mypy (py310) reports no new error in `scorers/`; its 24 findings are the pre-existing ones.
- **Import hygiene:** unchanged. Layer C is imported inside `_inputs._fact_findings`, because the validator's layer I
  imports the memory scorer.
