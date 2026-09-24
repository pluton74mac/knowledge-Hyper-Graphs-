---
title: "P2 implementation notes: S7 integration of W11a and W12"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# S7: integrating W11a (layer I, memory gold and scorer, G2) and W12 (the CLI)

W11a and W12 ran in parallel on top of S6 (`be842e1`). Neither committed. This note records what the integration
checked and what it changed.

**Nothing was broken.** The suite passed as the two steps left it: 5406 passed and 1 skipped. No xfail is left.

S7 made two small changes, both at points that the steps' reports handed to the integrator (see "Changes made at
S7"):
1. `record.write_container` and `store.conformance.write_report` now give their files the permissions the umask
   allows, as the CLI and `Queue.create` do.
2. `khg-convert` names a C4 file "an item file".

Nothing in DESIGN.md, `design-examples/` or `research/` was edited, and no packaged data changed.

## Result

| Run | Result |
|---|---|
| Full suite as delivered, Python 3.11 dev venv (`[xgi,hnx,fast,dev]`) | 5406 passed, 1 skipped |
| Full suite after the S7 changes, same venv | 5413 passed, 1 skipped |
| The two steps' test files and W4's edited file, `PYTHONHASHSEED=0` and `4242` | 1859 passed, 1 skipped (both) |
| gate-3.11 selection `-m "not evidence"`, directories in reverse order (`validate` first, `c1` last) | 5401 passed, 1 skipped, 5 deselected |
| evidence job `-m evidence` | 5 passed, 5402 deselected; the rewritten `library-hif-evidence.json` is unchanged |
| Python 3.10.20 and 3.13.12: fresh venvs with `pip install ".[dev]"` as in CI (no libraries, no SciPy), suite run from the checkout | as delivered 5074 passed, 20 skipped; after S7 5081 passed, 20 skipped (both) |
| sdist and wheel built from the tree after S7; the wheel alone in a clean 3.11 venv | the CI `wheel` job's three steps pass from a neutral directory (below); the suite run from the checkout on the wheel, as delivered: 5074 passed, 20 skipped |
| `python -m khg_contracts.examples OUT --tests tests` (the CI `examples` job) | 151 files; `diff -r` against `design-examples/` is empty |

The CI `wheel` job's three steps, run on the wheel built after S7:
- `python -m khg_contracts.data --check` passes.
- `khg-validate` on the packaged fixture exits 0, with the two designed warnings, S024 and L008.
- `khg-conformance --factory khg_contracts.store:memory_factory --report …` exits 0 with 114 passed.

- **The skip** in the dev venv is D019, the coverage exception of the case list (S-PUT-006 covers it).
- **No xfail is left.** S6 had 5, I001–I005, while layer I was a stub. W11a set `layers/i.py`'s
  `IMPLEMENTED = True`, and the five codes are now detected by their cases MC176–MC180.
- **The 20 skips of the core runs** are those of S6. All of W11a's and W12's tests need neither library, so they run
  there.
  - the nine W7 test modules, each skipped through its module-level `pytest.importorskip`;
  - the nine G1-chain tests of `tests/migrate/test_sample.py`;
  - the SciPy cross-check of the Hungarian solver;
  - D019.
- **The count.** 5407 tests were delivered. That is S6's 4035, plus 1284 from W11a in five files, plus 88 from W12 in
  `tests/cli/`. W11a also replaced one test in W4's `test_coverage.py`.
  - A diff of the collected ids against `be842e1` removes only W4's
    `test_the_stub_modules_name_their_owner_steps`. W11a replaced it with
    `test_no_layer_module_is_a_stub_any_more`. No earlier test was lost.
  - S7 adds 7 tests, for 5414 in all. The id `test_convert.py::test_an_input_of_another_kind_exits_1` becomes its
    `[schema]` and `[c4-items]` parametrisations.

## Did the steps clobber each other?

- **Changed files.** Before S7 there were 17 changed paths: 4 modified files and 13 untracked. They are exactly the
  union of the two reports' lists, and no path is in both.
  - **W11a** changed `validate/layers/i.py` and `scorers/memory.py`, the two stubs that W4 and W11b had left for it.
    It added `tests/gate/test_malformed.py`, the four `tests/scorers/test_memory_*.py` files and `impl-notes/W11a.md`.
    It also changed one file of W4, `tests/validate/test_coverage.py`.
  - **W12** changed `cli.py`, the W0 placeholder. It added `tests/cli/` (a `conftest.py` and five test modules) and
    `impl-notes/W12.md`.
- **Files of earlier steps.** Only W11a changed one: `tests/validate/test_coverage.py` (W4).
  - It removed the stub and xfail machinery: `module_for`, the xfail branch of `_params` and
    `test_the_stub_modules_name_their_owner_steps`.
  - It added `test_no_layer_module_is_a_stub_any_more`: every layer module is implemented, and no docstring names a
    `TODO(`. Both hold. The D019 skip is unchanged.
- **The stubs' signatures are kept.**
  - `derive_memory_gold(trace, question, *, schema, incorrect_reasons)` and
    `score(questions, responses, *, traces, schema, config=MemoryConfig())` are as W11b's stub declared them.
  - `MemoryConfig` keeps its three fields.
  - The four console scripts that W0 declared in `pyproject.toml` point at W12's four mains.
- **Untouched since S6:**
  - `data/`: `error-codes.json`, `malformed-cases.json`, the manifest. `python -m khg_contracts.data --check` passes;
  - `errors.py`, `__init__.py` (`CONTRACTS`), `pyproject.toml`, the root `conftest.py` and CI;
  - the validator's runner, registry and layer table;
  - every other subpackage, except the two writers changed at S7.

## Duplicated or conflicting definitions

- **Validator layers.** Only W11a touches the validator.
  - Layer I fills W4's slot (letter I, owner W11a) in the unchanged layer table. The `item` pipeline is J V I, as W4
    wired it.
  - W12 registers no layer. `khg-validate` calls `validate.run`. `khg-convert` validates IN with the full pipeline of
    its kind.
- **One replay, not two.** Layer I calls `scorers.memory.Replay`, `check_question` and `replay_findings`. So the
  I003 and I005 of `validate_item` and of `memory.score` come from the same checks.
  - Layer I imports `scorers.memory`, which imports `store`.
  - Each of the package's 117 modules still imports first in a fresh interpreter, so there is no import cycle.
- **Error codes.**
  - The registry is unchanged: 134 codes, 128 active and 6 reserved.
  - Every `KHG-` literal in the two steps' sources is registered and active:
    - `memory.py`: C001, C010, I002, I003, I005;
    - `layers/i.py`: D009, I002, I003;
    - `cli.py` has none. It prints the library's findings.
  - I001 and I004 come from the C4 draft's `x-khg-code`.
  - Every code that the new tests name is active.
- **C4 item checks, defined twice.** W11b's `scorers._inputs.c4_findings` runs its own jsonschema validator, and
  W11a's `layers.i.item_findings` runs `validate.engines`. S7 compared them on 369 lines:
  - the fixture's 10 lines;
  - the changed lines of MC176–MC180;
  - three mutations of every top-level key of every fixture line.

  Under jsonschema they give the same findings, up to the order of findings at one path. Under fastjsonschema, layer
  I's codes are a subset of the scorer's, and both are empty together. They were kept apart: W11a.md suggests the
  delegation, and `_inputs.py` is W11b's file.
- **Same name, different meaning.** Each name is used only inside its own module. The CLI reads
  `conformance.OUTCOMES` qualified.

  | Name | In W11a / W12 | Elsewhere |
  |---|---|---|
  | `OUTCOMES` | `scorers.memory`: the outcomes O1–O7 | `store.conformance`: the EARL outcomes; `queue.model`: the lint outcomes |
  | `MODES` | `scorers.memory`: `strict`, `lenient` | `queue.model`: `automatic`, `manual`, `semi_automatic` |
- **Equal duplicates, kept.** `memory.KS` = (1, 3, 5, 10, 20) is the default of `RetrievalConfig.ks`. W11a.md says
  so: `MemoryConfig` has no cut-offs.
- **File writers: the one conflict.**
  - The package has three atomic writers: W12's `cli._write_file`, W3's `record.write_container` and W8's
    `conformance.write_report`. `Queue.create` also creates its file.
  - The CLI's writer and the queue honour the umask. The two library writers used `tempfile.mkstemp`, whose mode
    0600 survived the rename.
  - So the same container or EARL report got 0644 from the command and 0600 from the library. W12 avoided the library
    writers for this reason and handed the point to the integrator. Change 1 aligns them.

## The seams

W12's tests never feed a C4 file to the CLI, so S7 probed the W11a → W12 seam with the installed console scripts.
All runs were on the packaged `c4-items.jsonl` or a copy with one fault.

| Command | Result |
|---|---|
| `khg-validate c4-items.jsonl --schema fixture.relation-schema.json` (auto kind) | `valid (item; 0 errors, 0 warnings)`, exit 0. The same with `--kind item --engine fastjsonschema` and with `--doc-texts fixture.doc-texts.json` |
| without `--schema` | D009 at `/lines/0/schema`, exit 1 |
| with the cyclic schema | D009 (the header pins `p2-gate`), exit 1 |
| MC180's fault on line 6 (a wrong stored `answer`) | I005 at `/lines/6/answer/values`, exit 1. `--json` prints `{ok: false, findings}` |
| a question whose trace is not in the file | I003 at `/lines/7/trace_id`, exit 1 |
| `khg-convert c4-items.jsonl x.hif.json --to hif` | exit 1: "… is an item file: khg-convert reads a C1 container or a khg-hif file" (change 2) |

- **W10 → W12, carried from S6.** W12's open issue 3 is already closed: S6 committed the four goldens next to
  `schemas/sample.hif.json`.
  - S7 reran the §11.3 commands in a scratch directory: `khg-migrate` with `--from v0-sample`, `--schema-out` and
    `--report`, then `khg-convert --to hif`.
  - All four outputs are byte-identical to `schemas/` and to `data/sample/`.
- **The two EARL writers agree.** `khg-conformance --report` and `conformance.write_report` now write the same bytes,
  with the same mode (0644 under umask 022).

## Changes made at S7

1. **The library writers honour the umask.** W12's open issue 1 ("The integrator may align both library writers").
   - **What changed.** `record.write_container` (W3) and `store.conformance.write_report` (W8) now create their
     temporary file with `open(..., "x")` in the target's directory, then `os.replace` it. This is the same code as
     `cli._write_file`.
     - Before, `tempfile.mkstemp`'s mode 0600 survived the rename, so library outputs were owner-only whatever the
       umask.
     - Now they get the mode the umask allows, as the CLI's outputs and `Queue.create`'s file do.
   - **Kept as it was.** Content, atomicity and the cleanup: a failed write or rename removes the temporary file and
     leaves the old target alone. `write_report` now serialises before it creates the temporary file.
   - **Tests.**
     - In `tests/c1/test_container.py` and `tests/store/test_conformance.py`: the mode under umask 022 and 027
       (0644 and 0640), and a failed rename that keeps the old file and leaves no temporary file.
     - Against `be842e1`'s writers, the four mode tests fail (0600), and the two cleanup tests pass.
   - The CLI keeps its own writer. It could now call the library writers, but nothing requires it.
   - W12.md's observation on `mkstemp` and its reason for bypassing `conformance.write_report` describe the tree
     before S7. This note supersedes them. The step's notes are left as the step's record.
2. **`khg-convert` says "an item file".** Given a C4 file, `cli._checked_input` wrote "… is a item file".
   - It now picks the article from the kind's first letter. The other kinds' messages ("a schema file", "a queue
     file", "a record file") are unchanged.
   - W12's `test_an_input_of_another_kind_exits_1` is now parametrised. `[schema]` keeps its expectation, and
     `[c4-items]` runs the packaged C4 file. Both also check that nothing is written.

## Other checks

- **Import hygiene.** Each of the 117 modules was imported first in a fresh interpreter, including `cli`,
  `scorers.memory` and `validate.layers.i`. None loads xgi, hypernetx, pandas, numpy, SciPy, jsonschema,
  fastjsonschema or referencing.
- **Python 3.10.**
  - Neither step uses a 3.11-only feature. `zip(..., strict=True)` in `memory.score` is 3.10, and so is argparse's
    `action="extend"`.
  - The 3.10 runs above confirm this.
  - There is no `print()` in library code. The CLI writes to `sys.stdout` and `sys.stderr`.
- **Static checks.**
  - `ruff --select F,E9` (py310) is clean on `src/` and `tests/`.
  - `ruff` with E, F, W, B and I at 120 columns is clean on every file of the two steps (`cli.py`, `layers/i.py`,
    `scorers/memory.py` and their tests) and on S7's edits, with two exceptions:
    - W11a's known B008 on `config=MemoryConfig()`, the §9.2 signature, written as the other scorers write it;
    - three E731s in W8's `tests/store/test_conformance.py` (lambdas assigned to names), which are older than S7.
  - mypy (py310, `--follow-imports=silent`) is clean on `cli.py`, `scorers/memory.py`, `validate/layers/i.py` and
    S7's two writers.
  - A whole-package mypy run reports 90 errors in 24 files of earlier steps. HEAD `be842e1` reports the same 90. None
    is in W11a's, W12's or S7's code, and mypy is not part of CI.
- **The wheel and the sdist.**
  - The wheel holds `cli.py`, `scorers/memory.py` and `validate/layers/i.py`, and the four console-script entry points.
    It holds no caches.
  - The sdist carries `tests/cli/`, `tests/gate/test_malformed.py`, the four memory test files and
    `tests/migrate/v0-sample.hif.json`, which `tests/cli`'s `v0_sample` fixture reads.

## Carried forward (not integration breakages)

- **Design points for the review, recorded by the steps.** S7 changed none of them.
  - **The C4 draft's I004 is wider than the registry's (W11a).** The packaged `khg-c4-items-0.1.0` maps any missing
    required field of a memory question to I004. The registry means only a missing `stale_values` or
    `future_values`. A fix is a minor release of the C4 draft, which changes `data/` and `design-examples/` (§11.2,
    risk 6).
  - **P3a owns C4 (W11a).** P3a should confirm or replace:
    - the tolerance reading `{"amount": d}` on same-unit quantities;
    - the `missing` outcome for a question without a response.
  - **`incorrect_reasons` (W11a).** The scorer requires the reasons that a set was built with (I005 otherwise).
    `validate_item` replays with the default, as §14 question 3 and ruling 3 state.
  - **§8.1's "exactly one code at the first rejecting step" (W11a).** It holds on the JSON Schema steps. On 11 cases
    the first rejecting step is a Python step, and there both engines report the same several codes. This is a
    wording point for §8.1; no code changes.
  - **Exit statuses (W12).** `cantTell` exits 1, following the director's ruling as the orchestrator passed it; §10.4
    names only `failed`. Argument files that fail validation exit 2.
  - **Additions to §10.2.**
    - W12: `cli.main` and `cli.COMMANDS`.
    - W11a: the shared replay names in `scorers.memory`, and `item_findings` and `embedded_findings` in layer I.
- **The container suffix rules (W12's open issue 2).** `record.read_container` reads any name but `.jsonl` as
  JSON. `record.write_container` writes any name but `.json` as JSONL. So a container written to `x.txt` cannot be
  read back.
  - W3 pins the writer's rule: `test_formats_and_suffixes` writes `noext` as JSONL.
  - §10.2 says "by suffix" for the reader and gives the writer a `format` argument.
  - Aligning the two is therefore a design decision, and S7 left it alone. `khg-convert` and `khg-migrate` avoid the
    gap with their own suffix rules.
- **W11b's `check_items` could delegate to `layers.i.item_findings`.** They agree (see "Duplicated or conflicting
  definitions"). This would be a refactor of W11b's file.
- **W13.**
  - The P3a line `validate.validate_item("qset.c4.jsonl", schema=S)` holds on the packaged C4 file.
  - The P7 line `memory.score(questions, responses, traces=traces, schema=S)` runs on packaged data (W11a's
    `test_memory_score.py`).
  - `tests/cli/conftest.py` shows how to run a child process offline.
- **W14.** The CI `wheel` job's commands pass on the wheel built at S7.
