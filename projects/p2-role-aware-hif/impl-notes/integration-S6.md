---
title: "P2 implementation notes: S6 integration of W9 and W10"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# S6: integrating W9 (`queue/`, layer Q, G3) and W10 (`migrate/`)

W9 and W10 ran in parallel on top of S5. The orchestrator's checkpoint commit `388c594` holds the files of their
interrupted first attempt; the second pass left its changes uncommitted. This note records what the integration
checked and what it changed.

**Nothing was broken.** The suite passed as the two steps left it: 4025 passed, 5 skipped and 5 xfailed. The one
change is the one W10 handed to the integrator: the four migration goldens are now committed next to
`schemas/sample.hif.json`, as §11.3 requires (see "Changes made at S6"). Nothing in DESIGN.md, `design-examples/` or
`research/` was edited. S6 changed no library code, test or packaged data.

## Result

| Run | Result |
|---|---|
| Full suite as delivered, Python 3.11 dev venv (`[xgi,hnx,fast,dev]`) | 4025 passed, 5 skipped, 5 xfailed |
| Full suite after the S6 change, same venv | 4029 passed, 1 skipped, 5 xfailed |
| `tests/queue`, `tests/migrate`, `gate/test_smoke.py` and W4's two edited files, `PYTHONHASHSEED=0` and `4242` | 754 passed (both) |
| gate-3.11 selection `-m "not evidence"`, directories in reverse order (`validate` first, `c1` last) | 4024 passed, 1 skipped, 5 deselected, 5 xfailed |
| evidence job `-m evidence` | 5 passed, 4030 deselected; the rewritten `library-hif-evidence.json` is unchanged |
| Python 3.10.20 and 3.13.12, core install (`[dev]`: no libraries, no SciPy), working tree through `PYTHONPATH=src` | 3697 passed, 20 skipped, 5 xfailed (both) |
| sdist and wheel built from the tree; the wheel alone in a clean 3.11 venv; suite run from the checkout | 3697 passed, 20 skipped, 5 xfailed |
| `python -m khg_contracts.examples OUT --tests tests` (the CI `examples` job) | 151 files; `diff -r` against `design-examples/` is empty |

- **The skip** in the dev venv is D019, the coverage exception of the case list (S-PUT-006 covers it, see S5).
- **The 5 xfails** are I001–I005: layer I is still a stub until W11a. S5 had 17; Q001–Q012 now pass, because W9
  set `layers/q.py`'s `IMPLEMENTED = True`. The 17 Q cases (MC159–MC175) pass W4's layer-rule and coverage tests.
- **The 20 skips of the core runs:**
  - the nine W7 test modules, each skipped through its module-level `pytest.importorskip`;
  - the nine G1-chain tests of `tests/migrate/test_sample.py`, each skipped through its own `importorskip`;
  - the SciPy cross-check of the Hungarian solver;
  - D019.

  All of W9's tests and the rest of W10's need neither library, so they run there.
- **The count.** There are 4035 tests in all: 3390 at S5, 521 from W9 (512 in `tests/queue/`, 9 in
  `tests/gate/test_smoke.py`), 119 from W10 (`tests/migrate/`), and 5 more parametrisations over the new packaged
  queue schema (4 in `tests/validate/test_engines.py`, 1 in `tests/packaging/test_package_data.py`).
  A diff of the collected ids against `fec5d82` (S5) removes only W4's `test_the_six_packaged_schemas_are_served`,
  which W9 renamed `test_the_seven_packaged_schemas_are_served`. No earlier test was lost.

## Did the steps clobber each other?

- **Changed files.** Before S6, the modified and untracked files were exactly the second-pass files of the two
  reports: 13 modified, 12 untracked. Every file the reports list as "kept" was unchanged since `388c594`. No path
  is in both lists.
  - W9 modified `queue/__init__.py`, `checks.py`, `fold.py`, `handle.py`, `linter.py` and `model.py`,
    `validate/layers/q.py`, `data/manifest.json`, and two W4 test files. It added `tests/queue/` (10 files),
    `tests/gate/test_smoke.py` and `impl-notes/W9.md`.
  - W10 modified `migrate/__init__.py` (a docstring), `tests/migrate/test_sample.py` and `impl-notes/W10.md`.
- **Files of earlier steps.** Only W9 changed any.
  - `tests/validate/test_engines.py` (W4) lists the queue schema as the seventh packaged schema, with layer Q and
    the smoke queue as its good file.
  - `tests/validate/test_s_layer.py` (W4): two queue-payload tests edit the smoke item's payload without updating
    its keys. Now that layer Q is real, it reports errors there, so the tests read their own S and C steps. Their
    inputs are unchanged, and one assertion was added: an unused wrong base gives Q012.
    - Replaying the inputs, layer Q reports Q010 (the keys no longer match the payload).
    - The runs without the header's base also get Q011 and Q012.
    - Q006 does not occur, because the replay runs only when layer Q has no other error.
  - `data/manifest.json` has one new line, the queue schema. `python -m khg_contracts.data` reproduces the
    committed file byte for byte after both steps, so no regeneration was needed.
- **Untouched since S5:**
  - `error-codes.json` and `malformed-cases.json`;
  - `errors.py`, `__init__.py` (`CONTRACTS`), `pyproject.toml`, the root `conftest.py` and CI;
  - the validator's runner, registry and layer table, and every other subpackage.

  Outside `queue/` and `migrate/`, the only source changes since `fec5d82` are W9's: the queue schema, its manifest
  line and `layers/q.py`.

## Duplicated or conflicting definitions

- **Validator layers.** Only W9 touches the validator. Layer Q (`layers/q.py`) calls the fold and checks of
  `queue/`, so `Queue.open`, `Linter` and layer Q share one implementation. W10 registers no layer. It checks its
  output with `load_schema` and `validate_container`.
- **Error codes.**
  - The registry is unchanged.
  - Every `KHG-` literal is registered and active: 16 in `queue/`, 21 in `migrate/` and 1 in `layers/q.py`.
  - No bare code strings are used.
  - W10 never emits the planned codes F011–F014.
- **Hashing, defined once.**
  - `decision_hash` is `jsonio.digest("khg-decision/1", …)` over `record.decision_view`.
  - A queue's `base.sha256` is `record.container_sha256`.
  - Neither step has a second canonicaliser. `migrate/layout.py` uses `json.dumps` only to reproduce the goldens'
    indented layout.
- **Equal duplicates, kept.** `queue.model.RECORD_FORMAT` equals `store.RECORD_FORMAT` (`khg-record/1.0.0`).
- **Same name, different meaning.** Each name is used only inside its own subpackage.

  | Name | In W9 / W10 | Elsewhere |
  |---|---|---|
  | `ACTIONS` | `queue.model`: the log actions | `record.keys`: the key-collision actions |
  | `LABELS` | `queue.model`: the verdict labels | `identity`: the `relate` labels |
  | `OUTCOMES` | `queue.model`: lint outcomes `pass`, `warn`, `fail` | `store.conformance`: EARL outcomes |
  | `SEVERITIES` | `queue.model`: `error`, `warning`, `info`, the registry's three severities | `schema`: the relation-schema constraints' `error`, `warning` |
  | `SCHEMA_ID` | `queue.model`: the queue schema's `$id`; `migrate`: the generated schema `kb-sample` | |
  | `complete` | `queue.verdicts`: a verdict's keys filled in | `store.export` |
  | `build`, `main` | `queue.codegen` (development tool) | `schema.codegen`, `examples`, `store.conformance` |
  | `findings` | `migrate._v0`: the v0 input checks | `validate.engines`, layers H, P and R |

## The seams

Neither step calls the other, so S6 probed the seams with two scratch scripts (not committed).

- **W10 → W9: a queue over the migrated sample.** The sample has a generated schema (`kb-sample` 1.0.0, an
  interval time model) and a base that no queue test uses. For each migrated fact (f1, f2 and f3):
  - the base was the migrated container without that fact;
  - `MemoryStore.load(base)`, `Queue.create(base=…)`, `make_candidate`, `submit`, `Linter.lint` and `accept` ran
    in order;
  - then `validate_queue` with both engines, `replay(factory=store.memory_factory, base=…)`, `queue_items`, and
    `Queue.open(base=…)`.

  All three passed:
  - the lint passed with no finding, and the state is `accepted`;
  - `validate_queue` gives `{ok: true, findings: []}` under both engines;
  - `replay` is ok, with no finding, and reproduces each `decision_hash`;
  - `compare_containers` finds no difference between the store's `khg-json` export and the migrated container.
- **W9 → W11b: the §1.3 P9 sequence on packaged data**, as written except for the run ids. Two queues, `run-1.o1`
  and `run-2.o1`, get `f:king-14` from `doc:louis-bio`, with `run` = `{run_id, order_id, position}` (no seed or
  temperature) and `Linter(S, entities=entity_base)`. Then `queue_items(paths)` feeds `extraction.score` against
  the packaged C4 gold and `stability.score(unit="run")`.
  - The queue ids containing a dot are accepted, and both lints pass.
  - Extraction matches the queued payload to the gold fact: core F1 1.0, with one true positive per run.
  - Stability reports 2 units.

  W13 can copy the sequence verbatim.

## Changes made at S6

1. **The four migration goldens are committed next to `schemas/sample.hif.json`.** These are
   `sample.relation-schema.json`, `sample.khg.json`, `sample.khg.hif.json` and `sample.migration-report.json`.
   - §11.3 says "W10 commits them next to `schemas/sample.hif.json`", but `schemas/` lay outside W10's files.
     W10 recorded this as its deviation 1 and handed the copy to the integrator (W10.md, "For the later steps").
   - They were copied from `src/khg_contracts/data/sample/`. Each is byte-identical to its packaged file and to its
     copy in `design-examples/`. `migrate.dumps` with `migrate.LAYOUT` rewrites each one byte for byte from the
     sample, and W10's tests check that.
   - The four `test_goldens_committed_next_to_the_sample_equal_the_packaged_ones` tests no longer skip, and they
     pass. The suite goes from 4025 passed and 5 skipped to 4029 passed and 1 skipped.
   - The change adds files only. `schemas/sample.hif.json` itself stays unchanged as the v0 fixture (§11.3).
   - The sdist ships `src/` and `tests/` only. There the two tests that read `schemas/` skip, as W10 designed.
   - `kb/04-storage-and-formats/README.md` lists the knowledge base's two worked files in `schemas/`. The goldens
     are P2 test artefacts, so it is left alone.

   The deviation-1 entry in W10.md and its line "The full suite, last run: 6 failed …" describe the tree before S6.
   This note supersedes them. The step's notes are left as the step's record.

## Other checks

- **Import hygiene.** All 116 modules of the package, including the 13 of `queue/` and the 4 of `migrate/`, import
  without loading any of these:
  - xgi, hypernetx, pandas, numpy or SciPy;
  - jsonschema, fastjsonschema or referencing.
- **Python 3.10.** Neither step uses a 3.11-only feature: no `tomllib`, `ExceptionGroup`, `except*`,
  `typing.Self` or `StrEnum`. The 3.10 run above confirms it. There is no `print()` in library code.
- **Static checks.**
  - `ruff --select F,E9` (target py310) is clean on `src/` and `tests/`.
  - `ruff` with F, E9, E501, W and B (120 columns) is clean on `queue/`, `migrate/`, `layers/q.py` and their
    tests.
  - mypy (py310, `--follow-imports=silent`) is clean on those 18 source files.
- **The wheel and the sdist.**
  - The wheel holds `queue/` (13 modules), `migrate/` (4), `validate/layers/q.py`,
    `data/schemas/khg-queue-1.0.0.schema.json` and the four goldens in `data/sample/`. It holds no caches.
  - In a clean 3.11 venv with only the wheel, `python -m khg_contracts.data --check` passes.
  - The sdist carries `tests/queue/`, `tests/migrate/` with `v0-sample.hif.json`, and `tests/gate/test_smoke.py`.
- **Public API (§7, §10.2).**
  - `queue.__all__` is `FORMAT`, `Linter`, `Queue`, `make_candidate`, `queue_items` and `replay`.
  - `migrate.v0_sample_to_v1` is the function and returns `(schema, container, report)`. It unpacks as the
    `Migration` tuple.
  - Both steps' additions beyond §10.2 are listed as deviations in W9.md and W10.md.

## Carried forward (not integration breakages)

- **W11a.** `tests/gate/test_malformed.py` closes G2 (W4.md, W9.md). The Q cases need
  `bases={"p2-smoke-base": smoke-base}` and the fixture schema. `tests/queue/test_q_cases.py` shows the harness.
- **W12 CLI.**
  - `khg-migrate` goes through `migrate.MIGRATIONS` (W10.md "For the later steps"). It can also regenerate the
    goldens committed in change 1.
  - `khg-validate --kind queue --base P` maps to `validate(path, kind="queue", schema=P, bases=[P])`. Without the
    base, a queue whose header names one gets Q012 and Q011 (W9.md).
- **W13.** The P9 sequence runs as written (see "The seams"). No §1.3 sequence calls `migrate`.
- **Design observations.** These are left for a design decision; S6 made no change.
  - `khg-migration-report/1.0.0` is listed in neither §11.1 nor `CONTRACTS` (W10).
  - No code is registered for the one-appender rule, so `Queue` raises `ConcurrencyError` without a code (W9).
  - A payload that fails layer C or S while the log has an accept for it is reported first as Q006, from the
    replay (W9). The prototype does the same, and no G2 case has such a queue.
  - The steps' other deviations are recorded in W9.md and W10.md:
    - W9: `Queue.open(…, base=None)`; `Linter.lint` raises Q012 or D009 before it logs; the public additions.
    - W10: D015 for a stored arity that disagrees; the extra refusals; the API additions; the direction rule.

    None of them conflicts with the other step.
