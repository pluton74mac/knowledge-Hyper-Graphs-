---
title: "P2 implementation notes: review fixes, group ex (queue, CLI, gate, consumers, packaging)"
type: project
status: draft
created: 2026-09-24
updated: 2026-09-24
---

# Review fixes, group ex: `queue/`, `cli.py`, the gate, consumer and packaging tests

This group owns `src/khg_contracts/queue/**`, `cli.py`, `examples.py`, `errors.py` and `__init__.py`; `tests/queue`,
`tests/cli`, `tests/gate`, `tests/consumers` and `tests/packaging`; `.github/`, `pyproject.toml` and
`upstream/`; and, for the queue schema only, `data/schemas/khg-queue-1.0.0.schema.json`, `data/manifest.json` and
`design-examples/` through the tools. It applied the 13 CONFIRMED findings of its bucket, all 7 LOW ones, the
director's ruling 6, the CLI half of ruling 4, the amended P7 sequence of DESIGN §1.3, and group b's three requests.
DESIGN.md and other groups' files were not edited. Nothing was committed.

No earlier attempt of this group had left edits: the interrupted round's checkpoint (40eab24) touched none of these
paths. Every change below was made in this pass.

**How the regression tests were checked.** A scratch tree held the current working tree with this group's source
files (`queue/*`, `cli.py`, `examples.py`, `errors.py`, `__init__.py`) and the queue schema and manifest put back
to HEAD; the tests ran there with that `src` first on `PYTHONPATH`. 55 tests fail there and pass on the working tree:
every regression test of a source fix. The findings that are test gaps (Q-TEST-BID-HINT, XGM-01, XGM-08, X-07) have
nothing to revert, so their tests were run against the review's mutants instead (see the table).

## Confirmed findings

| Finding | Change | Tests |
|---|---|---|
| Q-REPLAY-YEAR0: an accept at `0000-01-01T00:00:00Z` made `validate_queue`, `replay` and `khg-validate` raise `ValueError` | `replay._load_time` never goes below `_FLOOR` (`0000-01-01T00:00:00Z`), the first instant a queue timestamp names. An accept at that instant then shares it with the base load, which the store reports and the replay turns into Q006 | `test_replay.py::test_an_accept_at_the_first_instant_of_year_0_replays`: the verifier's queue built through the API validates and replays; with a base, Q006 and no exception |
| Q-UNHASHABLE: a list entity id or a list verdict `target` raised `TypeError` from layer Q | `checks._entity_findings` collects string ids only. `Fold.items` is now a `dict` whose `in` is `False` for a value that is not a string. Layer Q (`validate/layers/q.py:85`, group b's file) asks `line.get("target") in fold.items`, so it is fixed without touching that file, and `Queue` asks the same thing. An explicit guard in q.py is requested below; it is optional | `test_q_cases.py::test_values_that_cannot_be_hashed_are_findings_not_type_errors` (both engines): C010 at `/lines/1/entities/0/id`; Q008 and Q007 at `/lines/4/target` for a list or an object target. `test_queue.py::test_a_target_that_is_not_a_qid_is_q007` |
| Q-ITEMS-TYPEERROR: `queue_items` raised `TypeError` while iterating when an event hash was a list | `items._event_hashes` keeps string hashes only (the queue schema leaves the payload to layer C, which reports C010) | `test_items.py::test_an_event_hash_that_is_not_a_string_names_no_event` |
| Q-REPLAY-RECURSION: a deeply nested payload raised `RecursionError` from layer Q | Group b's 256-level J limit now stops `validate` and file-based `replay` first (J001). Remaining here: (1) `read_lines` gives lines passed in memory the same limit before it copies them (`schema.checks.nesting_fault`, J001 at the same path as layer J), so `replay(lines)` agrees with `replay(file)`: J001, not Q006 at 300 levels and `RecursionError` at 500; (2) `replay_accepts` builds the accepted record inside its `try`, and `RecursionError` is one of the failures it reports as Q006 | `test_replay.py::test_lines_in_memory_get_the_nesting_limit_of_a_file` (300 and 600 levels; lines, file and `validate` under both engines agree); `test_a_recursion_error_in_a_replayed_accept_is_q006` (while the record is built, and in the store's `put`) |
| Q-ONE-APPENDER-RACE: two appenders could both pass the size check (the same qid twice, and the file no longer opened), and `accept` wrote the store before its second check | Every append runs under an exclusive, non-blocking lock, and the size check runs under it (`handle._appending`). A busy lock is `ConcurrencyError` with `info["locked"]`. `accept` takes the lock before the store's `put` and holds it until its entry is written, so a second appender is refused before the store is touched. The lock is `fcntl.flock` on the queue file itself. The system releases it when a process dies, and flock locks taken through two opens conflict even in one process. Where there is no `fcntl` (Windows), or `flock` fails on the file system (`ENOLCK` on some network mounts), the lock is the exclusive creation of `<queue>.lock`, removed after the append; a stale one names itself in the error | `test_queue.py`: `test_a_second_appender_during_an_append_is_refused` (flock, the sidecar, and flock failing), `test_a_second_appender_during_an_accept_is_refused_before_the_store_is_written`, `test_a_lock_file_left_behind_is_named`, and `test_two_processes_appending_at_once_leave_one_item` (fork and a barrier, 10 rounds; on the old code both processes appended the same qid by the second round) |
| CLI-MIGRATE-PATHS: an output named twice, or naming IN, silently lost a file with exit 0; a failed write left earlier outputs replaced | `_distinct_outputs`: an output that is another output, or a file the command reads (IN, `--schema`), is a usage error (exit 2), and nothing is written. The samefile check falls back to `realpath`. `_write_files` stages every output in a temporary file first and replaces the targets only when all are written. Applied to `khg-migrate` (OUT, `--schema-out`, `--report` against IN and each other) and `khg-convert` (OUT against IN and `--schema`) | `test_migrate.py::test_an_output_named_twice_or_naming_in_exits_2` (4 cases), `test_a_failed_write_replaces_no_output`; `test_convert.py::test_out_may_not_be_a_file_the_command_reads` |
| CLI-FILE-MODE: replacing an existing output reset its mode to the umask's (a 0600 container became 0644) | `_staged` gives the temporary file the mode of an existing regular file at the target, as shell redirection keeps it; a new file still gets the umask's mode (W12's rule). `record.write_container` and `store.conformance.write_report` share the pattern and are group ad's (request below) | `test_migrate.py::test_an_existing_output_keeps_its_mode` (0600, 0640, 0444; a new report is 0644 under umask 022); `test_conformance.py::test_an_existing_report_keeps_its_mode` |
| Q-RECORD-FORMAT-STAMP: a newer `record_format` in a queue header was Q008 at layer Q, not V001 (§11.2) | `fold.version_findings(header)`: V001 for a `format` other than `khg-queue/1.0.x`, and for a `record_format`, when present, other than `khg-record/1.0.x`; a missing one stays the schema's Q008. `fold.check` runs it first and reads no further, as a V failure stops a validator run. `check` is shared by layer Q, `Queue.open` (its inline format gate is gone), `replay` and `queue_items`, so all four report V001; the review found that `replay` and `queue_items` had no version gate at all. The queue schema's `record_format` pattern is widened to `khg-record/<semver>` (which versions a reader takes is V001's), and the schema was regenerated. In `validate` the V001 still comes from the Q step, with first layer V; gating `record_format` in layer V itself is requested of group b | `test_q_cases.py::test_a_record_format_this_reader_does_not_take_is_v001` (5 stamps; `validate` under both engines, `Queue.open`, `replay`, `queue_items`), `test_a_record_format_of_another_patch_is_read` |
| Q-TEST-BID-HINT: nothing checked that a verdict binding's bid is only a hint (§7) | Tests only | `test_queue.py::test_the_bid_of_a_verdict_binding_is_only_a_hint`, and a new row of `test_q_cases.py::test_verdict_entries_are_checked_against_their_item` (b1's tuple under b5's bid). Both fail under the review's mutant (Q008 for a bid naming another tuple); every other queue test passes under it |
| XGM-01: G2's containment check could not tell that fastjsonschema ran | `test_single_fault_engine_containment` also requires exactly one fastjsonschema error finding at the schema steps H, P, C and I (`SCHEMA_STEPS`; true on all 64 such cases). M and Q add Python checks that can report one fault twice (MC147, MC157, MC164, MC174, MC175), so they keep "one code or the same codes". New `test_the_fastjsonschema_runs_do_not_run_jsonschema`: all 180 cases run again with fastjsonschema while `engines._jsonschema` and the jsonschema meta-schema runner refuse (the runner cache is cleared first), and every report must equal the fastjsonschema one. Schema arguments are loaded before the guard, because `load_schema` checks them with jsonschema by design | Mutations G2-01 (h), G2-02 (p), G2-03 (`if True` in `compile_schema`), G2-04 (c), G2-12 (m) and G2-13 (i), each on a copy of the tree: every one now fails the gate (1, 4, 6, 3, 1 and 1 failures). The review had 1256 passed under each |
| XGM-07, X-01 (and F7, LOW): `test_p7.py` held the P7 sequence from before f99a8af, so `test_verbatim[P7]` failed and `test_p7_sequence_close_older` asserted the superseded outcome | The marked copy gains DESIGN's line `ms.put(new, actor="p7")  # §2.5 close_older: ...` verbatim. `test_p7_sequence_close_older` asserts the §2.5 outcome from the sequence itself: f:king-14 at version 1, asserted, equal to `new`; `current == [f:king-14]`; `prompt == [KING_14_TEXT]`. The manual put after the sequence is gone. The L008 receipt check stays: the test records the receipts of the sequence's own puts (a wrapper on `MemoryStore.put`, filtered to the sequence's store) and asserts that the newcomer's put was `created` with L008 | `test_verbatim.py::test_the_copy_is_verbatim[P7]` (failed at HEAD); against the old block the new assertions fail (`ms.get("f:king-14")` is None) |
| XGM-08: nothing checked that `FilterIndex.from_records` filters the valid split | `tests/scorers/` is group f's, so the test is a P3b companion | `test_p3b.py::test_p3b_filters_the_known_answers_of_every_split` (Warszawa in train, valid or test; `(n_filtered_out, n_greater, n_equal) == (1, 0, 0)`). The review's mutant CM-02 (the valid split skipped) fails the valid case |

## Rulings and requests

- **Ruling 6.** `CONTRACTS["khg-migration-report"] = "1.0.0"`. `test_api.py`: §11.1's table includes it, and
  `test_the_migration_report_is_a_contract` checks `migrate.REPORT_FORMAT` and the packaged report golden against it.
- **Ruling 4, the CLI half.** Group ad's `record.read_container` raises `ValueError` for a suffix other than
  `.json` or `.jsonl`. `_argument` turns it into exit 2 (`--base x.txt`), and so does `_convert` when it reads a
  container IN. A `ValidationError`, which is a `ValueError` too, is still reported as before. A container output is
  checked before anything runs: `khg-migrate` OUT and `khg-convert --to khg-json` OUT must end in `.json` or
  `.jsonl` (`--to khg-jsonl` already required `.jsonl`). Tests:
  `test_validate.py::test_a_base_whose_suffix_is_not_a_container_s_exits_2`,
  `test_convert.py::test_container_files_are_named_by_their_suffix` and
  `test_migrate.py::test_out_is_a_container_file_name`. The CLI checks the phrase "a container file name ends in
  .json", not group ad's exact message. Group ad's third request, a 5,000-digit integer, is
  `test_an_integer_of_5000_digits_is_j006` (J006, exit 1; a guard, since group ad's jsonio fix already gives it).
- **Group b's requests.** (1) `test_doc_texts_feed_the_span_check` now shifts the position selector of f:coadmin-1
  and expects S021 with the texts and none without them. It also pins b-validate-10: a text that does not hash to
  the evidence's digest is not judged. (2) `queue.codegen.build` runs `schema.codegen.end_anchors` after
  `propagate`. All 18 patterns of the packaged queue schema end in `(?!\n)$`
  (`test_schema.py::test_every_pattern_ends_the_text`). (3) The queue schema was regenerated with
  `python -m khg_contracts.queue.codegen src/khg_contracts/data/schemas`. The manifest was regenerated with
  `python -m khg_contracts.data`: only the queue schema's hash changed, and `--check` passes.
  `python -m khg_contracts.examples <scratch> --tests tests` gives a tree byte-identical to `design-examples/`, so
  nothing changed there: the queue schema and the manifest are not mirrored.

## LOW findings

| Finding | Outcome |
|---|---|
| F7 | The same fix as X-01 |
| CLI-EPIPE: a closed stdout gave a `BrokenPipeError` traceback and exit 1 | Applied. `_main` flushes stdout inside its `try`. On `BrokenPipeError` it points stdout at `os.devnull` (so the flush at exit stays quiet), says `cannot write the standard output: Broken pipe` on stderr, and returns 2. Tests: in process (`test_validate.py`, text and JSON) and in children with a closed pipe (`khg-validate`, and `khg-conformance --only 'S-PUT-*'`) |
| Q-TIMESTAMP-CALENDAR: impossible date-times passed the queue schema's digit pattern | Applied. `fold.time_findings` gives Q008 at the field for a `created_at`, `submitted_at` or `at` that has the pattern but that `record.lifecycle.parse_timestamp` (the store's reading) refuses. `check` runs it on every line, and `Queue.create` and every append check it before writing. Note that `parse_timestamp`, and so the store, refuses a leap second (`:60`). Tests: `test_q_cases.py::test_a_time_that_is_no_calendar_date_time_is_q008` (3 values on 4 lines, both engines), `test_queue.py::test_a_time_that_is_no_calendar_date_time_is_refused` |
| X-05: `make_candidate` raised `TypeError` for non-list evidence | Applied. Only list evidence has its `recorded_at` stripped. Anything else comes through unvalidated, as the docstring says, and `submit` refuses it with Q001. Test: `test_candidate.py::test_evidence_that_is_not_a_list_is_left_to_the_checks` |
| X-07: the source scan accepted planned and reserved codes | Applied. `test_codes_named_in_the_package_source_are_active`: every `KHG-` code the package source names is active (all are today). A planned `KHG-L005` added to `queue/linter.py` in a scratch copy fails it |
| X-09: the HIF issue said the libraries do not keep roles, and cited the unread version of record by page | Applied to `upstream/hif-issue.md`: "XGI drops it, and HyperNetX keeps it but collapses repeated pairs"; the Evidence table gains HyperNetX's roles kept (2 of 3, 3 of 4, 50 of 52; `library-hif-evidence.json`); the quote is cited to arXiv:2507.11520v2, p. 7, with the DOI of the version of record, and page numbers are said to be arXiv v2's (research/02 §1) |
| X-06: the XGI and HyperNetX issues stated as settled what the HIF issue asks | Applied to `upstream/xgi-issue.md` point 2 and `upstream/hypernetx-issue.md` point 7: "The HIF schema accepts several records for one (edge, node) pair, and the ... compliant `duplicated_nodes_edges.json` has one; whether the formal model's incidence set allows it is asked in <HIF issue>" (the drafts' own placeholder) |

`upstream/RELEASE.md` also says now that its CI run predates f99a8af, after which `test_verbatim[P7]` failed in the
three test jobs until this round, and that the six jobs must run again on the release commit (X-01).

## Decisions

- **The fold answers `in` for any value.** Layer Q's crash on a list `target` was in group b's file, and group b has
  finished. The fix is in the structure it reads (`Fold.items`), which also covers `Queue`'s own lookups. A list
  qid passed to a `Queue` method is now Q007 (a `ValidationError`) rather than `TypeError`.
- **The version gate is in `fold.check`.** It serves all four readers of a queue file in this group's code. Layer V
  is group b's file, and it gates only `format` for queues. So without a change there, `validate` reports the
  `record_format` V001 from the Q step, with first layer V (the earliest letter), and the payload steps C, S and D
  still run after it. For the smoke queue they add nothing.
- **Refusing IN as an output.** The verifier left refusing IN as optional. `khg-migrate v0.hif.json v0.hif.json`
  replaced the v0 fixture, which §11.3 keeps unchanged. `khg-convert x.khg.json x.khg.json` replaced its own input.
  Both are refused now (exit 2). To rewrite a file in place, write elsewhere and rename.
- **Mode, not ownership.** An existing output keeps its permission bits. Its owner and group are not copied
  (`chown` needs privileges, and the verifier left it optional). A read-only target is still replaced (the
  directory is writable), and it stays read-only.

## Requests to other groups

1. **Group b (`validate/layers/v.py`):** in the queue branch, also give V001 at `/lines/0/record_format` when the
   header has a `record_format` that `gate(..., "khg-record", 1, 0)` refuses, as `queue.fold.version_findings`
   does. The run then stops at step `v`, as §8.1 says a V failure does. The queue schema's pattern no longer
   decides it.
2. **Group b (`validate/layers/q.py`):** optional. At lines 84-85, test `isinstance(line.get("target"), str)`
   before `in fold.items`. `Fold.items` makes this safe already. Also, the module docstring could mention that
   `queue.fold.check` reports V001 for a header stamp.
3. **Group ad (`record/container.py` `write_container`, `store/conformance/report.py` `write_report`):** keep an
   existing regular target's mode, as `cli._staged` does. Stat the target, then `os.chmod(tmp,
   stat.S_IMODE(st.st_mode))` before `os.replace` (CLI-FILE-MODE's verifier named all three writers).
4. **Integration (not a group's file):** `impl-notes/W13-W14.md` decision 3 (the P7 close_older gap, closed by
   f99a8af and this round's test) and its CI-parity table are stale. Re-run the six §10.6 jobs on the integration
   commit.

## Full suite

`python -m pytest -q -p no:cacheprovider` from the repository root with the dev venv: **5847 passed, 1 skipped**
(127.9 s; the same count in an earlier run), with `python -m khg_contracts.data --check` clean. Both runs included
the other groups' edits in the working tree at the time: group f had finished, and group ad was still at work.
