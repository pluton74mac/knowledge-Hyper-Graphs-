---
title: "P2 implementation notes: integration of the review round"
type: project
status: draft
created: 2026-09-24
updated: 2026-09-24
---

# Review round: integrating the five fixer groups

The review round's confirmed findings were fixed by five groups: b (`schema/`, `validate/`, `data/`), ad (`jsonio`,
`record/`, `identity/`, `store/`), c (`hif/`, `loaders/`, `migrate/`), f (`scorers/`) and ex (`queue/`, `cli.py`,
the gate, consumer and packaging tests, `upstream/`). Checkpoint `40eab24` holds group b's work and the first pass of
groups ad and c. The rest was in the working tree, uncommitted. Each group's own notes are `review-fix-<group>.md`.

This note records what the integration checked and changed:
- which cross-group requests were still open, and which of them it applied;
- the one integration breakage it found and fixed;
- the CI parity run.

Nothing in DESIGN.md was edited. The W-step notes that the fixes supersede (W11a, W11b, W13-W14) gained a short
"Superseded in the review round" block at the top; their bodies are unchanged.

## Result

| Run | Result |
|---|---|
| Full suite as delivered by the fixers (dev venv, Python 3.11, every extra) | 5847 passed, 1 skipped (5848 collected) |
| Full suite after the integration | 5876 passed, 1 skipped (5877 collected: 29 new tests) |
| The 29 new tests on the tree as the fixers left it | 26 fail. The 3 that pass pin the behaviour behind a docstring change (request 2 below) |
| `tests/gate` under `PYTHONHASHSEED` 0 and 4242 | 1257 passed (both) |
| The six CI jobs of §10.6 | all pass; see "CI parity" |

- **The skip** is D019, the coverage exception of the case list (S-PUT-006 covers it).
- **The count.** The new tests are:
  - 5 in `tests/validate/test_schema_codes.py`;
  - 13 in `tests/validate/test_runner.py`;
  - 5 in `tests/queue/test_q_cases.py`;
  - 3 in `tests/c1/test_container.py`;
  - 3 in `tests/store/test_conformance.py`.
- **How "fail before" was checked.** A scratch tree was rebuilt from `git archive HEAD` plus the working-tree diff
  saved before any integration edit. The new tests ran on it with that `src` first on `PYTHONPATH`.

## Cross-group requests

### Applied, each with a regression test

| Request | Change | Tests (fail before, pass after) |
|---|---|---|
| 1. Group ad → b: bound the year in the record schema's patterns | `schema.codegen` writes the time literal's year as `[0-9]{4,16}` and the instant's as `[0-9]{4,17}` (`YEAR_DIGITS`, `INSTANT_YEAR_DIGITS`, `TIME_PATTERN`, `INSTANT_PATTERN`). These are `record.windows`' bounds: Wikibase's 16 digits for a literal, and one more for an instant, the upper window bound of the largest literal year. Regenerated with the tools: `data/schemas/khg-record-1.0.0.schema.json` (only these two patterns changed), `data/manifest.json` (`--check` is clean) and the mirror `design-examples/schemas/khg-record-1.0.0.schema.json` (no other file changed). Effects: layer C now reports a 17-digit year as C004 at `.../literal/time`, and the S step's time parse still reports C004 at `.../literal`, as for any other malformed time. A C4 `where.as_of` with an 18-digit year is I002 at the field, like any other malformed `as_of`; before, it was I003 from the replay, with C011 nested | `test_schema_codes.py`: `test_the_record_schema_bounds_a_year_as_record_windows_does`, `test_a_literal_year_beyond_16_digits_is_c004_from_layer_c` (both engines, 17 and 4301 digits), `test_an_as_of_year_beyond_17_digits_is_refused_by_the_item_structure` (both engines) |
| 2. Group ad → b: `validate.run`'s docstring and a base path's suffix | The docstring now says that a base path whose suffix is not `.json` or `.jsonl` is `ValueError` (`record.read_container`, ruling 4). It is an argument error, not a finding | `test_runner.py::test_a_base_path_whose_suffix_is_not_a_containers_is_a_value_error` (`.txt`, `.c1`, `.JSON`; not a `ValidationError`; the same file renamed `.json` passes). It pins behaviour that was already there, so it passes before too |
| 3. Group ex → b: layer V gates a queue header's `record_format` | `layers/v.py` gives V001 at `/lines/0/record_format` for a stamp other than `khg-record/1.0.x`, when the header has one (a missing one stays the queue schema's Q008). The run stops at step v, as §8.1 says. Before, the V001 came from the Q step's `queue.fold.check`, and C, S and D ran after it. `fold.check` keeps its gate for `Queue.open`, `replay` and `queue_items` | `test_runner.py::test_layer_v_gates_the_record_format_of_a_queue_header` (5 stamps × 2 engines: only V001, `stopped == "v"`, steps `j v`; a `1.0.9` stamp passes) |
| 4. Group ex → b (optional): layer Q tests a verdict's `target` | `layers/q.py` checks `isinstance(target, str)` before `in fold.items`, so it no longer relies on `Fold.items` answering `in` for an unhashable value. The module docstring names the header stamp's V001 | `test_q_cases.py::test_layer_q_asks_only_for_string_targets` (the fold's items replaced by a plain dict; a list or object target is Q008 and Q007, not `TypeError`) |
| 5. Group ex → ad: the library writers keep an existing file's mode | `record.write_container` and `store.conformance.write_report` give the temporary file the mode of an existing regular file at the target, as `cli._staged` does since CLI-FILE-MODE. A new file still gets the umask's mode (S7's rule) | `test_container.py::test_an_existing_file_keeps_its_mode` and `test_conformance.py::test_an_existing_report_keeps_its_mode` (0600, 0640, 0444; a new file is 0644 under umask 022) |
| 6. Groups f, b and ex → integration: the superseded W-step notes | `W11b.md`, `W11a.md` and `W13-W14.md` each gain a dated "Superseded in the review round" block at the top: E-M3's multiplier, entity redirects per item, text-only retrieval gold, `model_rank`, extraction outputs (group f); the tolerance rule and observation 2, settled by ruling 7 (groups f and b); decision 3, closed by f99a8af, the old CI-parity table, and the open points that rulings 4, 7 and 9 settle (group ex) | none (notes) |

### Already done by another group

- **Group b's requests.**
  - CLI test for b-validate-10: group ex.
  - The scorer test for ruling 7: group f.
  - The queue schema's end anchors, with the file and the manifest regenerated: group ex.
  - Integral-float versions (F10) and `jsonio.MAX_DEPTH`: group ad.
  - The P7 verbatim test: group ex.
- **Group ad's CLI request** (ruling 4's exit 2, and the 5,000-digit J006 test): group ex.
- **Group c's requests.**
  - `CONTRACTS["khg-migration-report"]` (ruling 6): group ex.
  - The three failing tests it listed: groups ex and f.

### Not applied: for the director or the owners

- **DESIGN and registry texts (group ad 2-4, group c 3).**
  - DESIGN §2.7 and D014's meaning in the registry: a history may go from superseded to disputed in one version
    (`lifecycle.COMPOSITE_STEPS`).
  - DESIGN §2.8.1: carried evidence without `supports` keeps the first carrying version's list.
  - DESIGN §10.2 and §2.10:
    - J005 from `write_container` and `container_sha256`;
    - the 256-level limit in J001;
    - the projection inverses take one version per fact;
    - a width is a positive integer;
    - a put that moves `status_ref` is D014.
  - DESIGN §5 and §10.2: `Bundle.label` raises R002 for an exact repeat, and P010 in HyperNetX too. §5 should also
    say that `strict=False` exports a collapse and reports it.
  - DESIGN §4.2: `hif:weight` is a finite number (C010 from `to_hif`).

  These restate what the code now does, and DESIGN is the director's. The registry meanings follow DESIGN.
- **A new code for evidence ids given twice in a brand-new record** (group ad 7). A new registry code is a design
  decision.
- **Director's questions** (group ad 8):
  - d-store-10: may a v1 store hold values that name an entity it redirected?
  - d-store-13: are event fields checked before or after the capability?
  - The rest of d-store-09, and group c's option to drop cross-edge collapses under `strict=False`, are policy
    choices too.
- **`hif:weight` in the C1 schema** (group c 1, optional). DESIGN §2.2 and §2.3 call `extensions` "passthrough",
  so refusing a non-numeric weight at layer C would change the C1 contract; `to_hif` refuses it with C010 now. If the
  director wants layer C to refuse it, the change is one `properties` entry in `codegen._record`'s `extensions`,
  then the same regeneration as request 1.
- **Research probe** (group f, optional): `research/probes/scorers/c5_reference_cases.py` keeps R05's per-pair
  multiplier. No expected value changes; it is not package code.
- **Group f's not-applied LOW items** stay open, and need decisions:
  - f-scorers-11: cut-offs by declared rank;
  - the path part of f-scorers-13.

## The integration breakage

**A list or object `kind` on a queue line raised `TypeError`.** It came from group ex's Q-TIMESTAMP-CALENDAR fix:
`queue.fold.time_findings` looked the line's `kind` up in a dict. The whole run failed on it, whether through
`validate`, `Queue.open`, `replay` or `queue_items`. At f99a8af the same input gave the schema's Q003.

mypy found it: it was the one error of the tree that f99a8af did not have. The kind is now read only when it is a
string. `test_q_cases.py::test_a_line_kind_that_cannot_be_hashed_is_q003_not_a_type_error` covers it through all four
entry points under both engines. Its 4 cases fail on the delivered tree and pass at f99a8af and now.

Two cosmetic fixes: a docstring line of `queue/replay.py` (group ex) had grown to 162 columns, and a parametrize line
of `tests/validate/test_runner.py` (group b) to 122. Both were rewrapped, so ruff reports nothing the checkpoint did
not.

## Checks beyond the suite

- **Differential crash fuzz.** One value of each packaged input was replaced with one of 12 shapes (a list, an object,
  null, a float, a boolean, `""`, `-1`, a trailing newline, a huge integer, `[]`, `{}` or a deletion):
  - inputs: the container, the history container, the HIF file, the smoke queue, the C4 items and the relation
    schema;
  - 150 paths each, 3 mutations per path, with a fixed seed;
  - each mutant through `validate` under both engines, and the two containers also through `canonical_container`,
    `MemoryStore.load` and the `khg-json` and `hif` exports.

  Of the 6,300 outcomes on the integrated tree, none raises that did not raise at f99a8af. Ten crashes at f99a8af
  no longer happen (the X-02 guards in `schema/checks.py`). The other outcome changes are intended:
  - 8 values with a trailing newline are now refused (b-validate-05);
  - 3 non-numeric `hif:weight` values now give C010 from the HIF export (F3).

  Seven crashes happen on both trees: `MemoryStore.load`, a trusted load, raises `TypeError` in
  `store/flags.data_flags` for a hyperedge whose `relation` is a list or an object. It dates from S5 and is not a
  regression. It is left as an observation: the load's docstring promises C010 or C002 for what it cannot index.
- **ruff** (F, E9, E501, W, B; 120 columns; py310): 11 findings, all known. 8 are B008, the §9.2 signatures. 3 are
  E501, verbatim DESIGN lines in `tests/consumers/`.
- **mypy** (py310): 81 errors against 90 at f99a8af, and none that f99a8af did not have. The one new error of the
  delivered tree was the breakage above.
- **Seams probed with the console scripts:**
  - `khg-convert --to hif` on a container whose `hif:weight` is a string prints C010 and exits 1, and writes
    nothing;
  - `khg-validate` on a 17-digit year prints the two C004 findings and exits 1.

## CI parity

Each job ran in a fresh virtual environment built as `ci.yml` builds it, with non-editable installs from the
checkout (`scratchpad/ci3/`, and `scratchpad/venv-wheel3/` for the wheel). The installed packages were checked to
equal `src/khg_contracts` file by file.

| Job | Python | Result |
|---|---|---|
| `core-3.10` (`.[dev]`, every test) | 3.10.20 | 5519 passed, 21 skipped |
| `gate-3.11` (`.[xgi,hnx,fast,dev]`, `-m "not evidence"`) | 3.11.15 | 5871 passed, 1 skipped, 5 deselected |
| `core-3.13` (`.[dev]`, every test) | 3.13.12 | 5519 passed, 21 skipped |
| `wheel` (`python -m build`; the wheel alone in `scratchpad/venv-wheel3`, run from a neutral directory) | 3.11.15 | `python -m khg_contracts.data --check` passes. `khg-validate` on the packaged fixture exits 0 with the two designed warnings (S024, L008). `khg-conformance --factory khg_contracts.store:memory_factory --report ...` exits 0: 114 passed, 0 failed, 0 inapplicable, 0 cantTell |
| `examples` (`.`, `--tests tests`) | 3.11.15 | 151 files in `scratchpad/ex-out3`; `diff -r` against `design-examples/` is empty |
| `evidence` (`.[xgi,hnx,dev]`, `-m evidence`) | 3.11.15 | 5 passed, 5872 deselected; the rewritten `library-hif-evidence.json` is byte-identical (sha256 `047d5862...15b7`) |

- **The skips** are those of W13's run (checked with `-rs` in core-3.10). The core jobs have 21:
  - the nine library test modules, skipped through `pytest.importorskip`: seven under `tests/loaders/`,
    `tests/gate/test_roundtrip.py` and the evidence test;
  - the nine G1-chain tests of `tests/migrate/test_sample.py`;
  - the SciPy cross-check of the Hungarian solver;
  - D019;
  - P5, which needs xgi.

  The one skip of `gate-3.11` is D019.
- **Against W13's run** (before the review round): 413 more tests pass in the core jobs (5106 then) and 437 more in
  `gate-3.11` (5434 then). The skip and deselection counts are unchanged.
- **`W13-W14.md`'s table** is superseded by this one (its new header block says so). `upstream/RELEASE.md` still asks
  for the six jobs on the release commit itself, which is right: this run is on the integration tree.

## Observations (not changed)

- **The two C004 findings of an overlong year** (one from layer C at `.../time`, one from the S step at the
  literal) are the pattern that any malformed time literal already had, such as a missing sign. The S step does not
  skip a literal that layer C rejected.
- **`MemoryStore.load` and an unhashable `relation`**: see the fuzz above. Fixed since: see the follow-up below.
- **Two files outside the repository.** A misquoted shell line during the CI runs wrote two small logs,
  `/core-3.13.log` and `/gate-3.11.log` (82 bytes each, a "No such file" message). The session's safety check
  refused to delete files at the filesystem root, so they are left for the owner to remove.

## Follow-up: MemoryStore.load on non-string relations (2026-09-24)

This follow-up fixes the fuzz observation above. The same pass applies the director's ruling 10 (d-store-10). It
changes only `store/` and `tests/store/`.

### Relations that are not strings

**The bug.** `MemoryStore.load` raised a raw `TypeError: unhashable type` from `store/flags.data_flags`
(`record.get("relation") in LIFECYCLE_RELATIONS`) for a hyperedge whose `relation` is a list or an object. `put`
crashed the same way: `_need_data` reads the flags of the raw records before validating them.

**The changes.**
- `MemoryStore.load` refuses a hyperedge whose `relation` is not a string with C010 at `/records/<i>/relation`. The
  refusal comes in the loop that already refuses a record without a string id. Nothing is loaded. A number, `null`
  or a missing relation is refused too. They did not crash, but the store indexes hyperedges by relation, and the
  docstring promises C010 or C002 for what `load` cannot index.
- `data_flags` treats a relation as a lifecycle relation only when it is a string
  (`isinstance(relation, str) and relation in LIFECYCLE_RELATIONS`), for callers that pass unvalidated records.
- **`_writes._incoming`** (used by `put` and the records an event carries) refuses a hyperedge whose relation is not
  a string, as it already refused a non-string id. It raises layer C's findings, else C010 at `<where>/relation`.
  Before this, `put` crashed in `record/lifecycle._is_lifecycle` once `data_flags` was fixed, so the `data_flags`
  guard alone was not enough. Layer C reports C010 at `/relation` and a C012 from the schema's lifecycle-field
  conditional. A record whose relation is missing or not a string now gets these C codes before the status rules
  (D014, D017), as a non-string id already did.

**Other shapes probed.** Both packaged containers were loaded with one field of one record replaced (scratch
script `probe_load.py`):
- the containers: `fixture.c1.json` (2,192 loads) and `fixture.history.c1.json` (1,644 loads);
- the records: an entity, a fact, a lifecycle record and a goal;
- the fields: 23 top-level fields; a binding's `value`, `role`, `bid` and `position`; an evidence record's `id`,
  `supports` and `type`; a non-object appended to `bindings` or `evidence`;
- the shapes: a list, an object, an integer, a float, `null`, a boolean, `""` or a deletion;
- the runs: each mutant under `on_missing="raise"` with every flag, and under `"skip"` without `goals`,
  `special_values` and `nesting`.

At HEAD, 20 loads raised a non-KHG exception, all from the relation (12 in c1, 8 in the history). Now none does.
Nothing else crashed: `bindings` that is not a list, a binding that is not an object, `status`, `status_ref` or
`evidence` of the wrong type. Before and after the fix, `load` keeps such records as a trusted load, as
`test_reads_pass_over_a_malformed_record_that_a_load_kept` pins for status, rank and visibility. A bad `version` was
already C010 and a bad `recorded_at` was already C011. No other refusal was added. The same mutations through `put`
(822 writes, `probe_put.py`): 4 `TypeError` at HEAD (the relation), none now.

### Ruling 10: a redirect is refused while a held record names the entity

`WriteMixin._check_references` is shared by `put` and the five events. It now refuses, with D020 at
`/records/<i>/redirect_to`, an entity record of the write that gains `redirect_to` while a record the store holds has
an entity value naming it. "Gains" means the held version has no `redirect_to`, or the entity is new. "Holds" covers
any version and any status. The message names the first such record in id order, its version and its binding
pointer, for example: `ex:Paris: redirect_to is refused while f:born-louis14-paris names ex:Paris (version 1,
/bindings/0/value); values are rewritten in 1.2`.
- **How it finds them.** The table's node index covers every version, so the check reads `by_node(entity)` and
  then those ids' versions.
- **What is not re-checked.** A new version that keeps a held `redirect_to`, such as a label change, is not checked
  again. Changing `redirect_to` is still D013.
- **The validator is looser.** Its container D020 looks at current versions only. The store's rule covers every
  version, as the ruling was relayed.
- **`load` stays trusted.** It can still build a store in which a value names a redirected entity.
- **No conformance scenario was added** (a 1.1 addition, so the suite stays at 114 scenarios). S-VER-008 and
  S-PUT-010 redirect entities that no record names, and still pass.
- **Before the change,** a loaded fixture accepted `ex:Paris` → `redirect_to: ex:Warszawa` as version 2, and the
  store's own `khg-json` export then failed validation with D020. Now the put is refused and the export validates.
- **One existing test changed.** `test_a_redirected_entity_is_refused_only_where_it_is_written` (W8) redirected a
  named entity with a put, which the ruling now refuses. It now builds the same state with a trusted load. It still
  pins W8's rule that D002 and D020 apply to the values a write adds or changes.

### Tests

| Test | Cases | At HEAD | Now |
|---|---|---|---|
| `test_load.py::test_load_refuses_a_hyperedge_whose_relation_is_not_a_string` (f:reg-1, m:sup-1, g:who-1774 × list, object, 7, absent; C010 at the path, nothing loaded, under raise and skip) | 12 | 6 `TypeError`, 6 do not raise | pass |
| `test_load.py::test_data_flags_reads_a_relation_that_is_not_a_string` | 2 | `TypeError` | pass |
| `test_memory_store.py::test_put_refuses_a_relation_that_is_not_a_string` | 2 | `TypeError` | pass |
| `test_memory_store.py::test_a_redirect_is_refused_while_a_held_record_names_the_entity` (path, the named record, a batch refused whole) | 1 | does not raise | pass |
| `test_memory_store.py::test_a_redirect_is_refused_for_a_name_in_any_status_or_version` (a superseded fact; version 1 only) | 1 | does not raise | pass |
| `test_memory_store.py::test_a_redirect_is_accepted_when_no_record_names_the_entity` (a new version, a new record; snapshot and history exports validate) | 1 | pass | pass |

**Each change was checked alone.**
- The load check alone leaves the `data_flags` and `put` cases failing (4).
- The `data_flags` guard alone leaves the 12 load cases and the 2 `put` cases failing. `put` then crashes in
  `record/lifecycle._is_lifecycle`.
- All three changes together pass all 16 relation cases.

**Checks.**
- Full suite (dev venv, Python 3.11, every extra): 5895 passed, 1 skipped. That is 19 more than the 5876 above, all
  of them the new tests.
- ruff (F, E9, E501, W, B; 120 columns; py310) reports nothing on `store/` and `tests/store/`.
- mypy (py310) gives the same error set as HEAD.

**Observation (not changed; outside `store/`).** `record/lifecycle._is_lifecycle` still raises `TypeError` for an
unhashable relation when `put_problem`, `nesting_cycle` or the history step check gets an unvalidated record
directly. The store no longer passes it one.
