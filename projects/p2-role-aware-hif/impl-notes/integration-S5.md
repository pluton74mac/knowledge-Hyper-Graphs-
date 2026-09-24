---
title: "P2 implementation notes: S5 integration of W7 and W8"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# S5: integrating W7 (`loaders/`, G1) and W8 (`store/`, the conformance suite)

W7 and W8 ran in parallel on top of S4. This note records what the integration checked and what it changed.
**Nothing was broken**: the suite passed as the two steps left it. Two test allowances were removed, because they
existed only while the other step was missing. W7's evidence file is committed with the step, as W7 asked (see
"Changes made at S5"). Nothing in DESIGN.md, `design-examples/` or `research/` was edited. No library code and no
packaged data changed.

## Result

| Run | Result |
|---|---|
| Full suite as delivered, Python 3.11 dev venv (`[xgi,hnx,fast,dev]`) | 3372 passed, 1 skipped, 17 xfailed |
| Full suite after the S5 changes, same venv | 3372 passed, 1 skipped, 17 xfailed |
| Same, `PYTHONHASHSEED=0` and `4242` | identical counts |
| Directory order reversed (`validate` first, `c1` last) | identical counts |
| `gate/`, `loaders/`, `store/` and `evidence/` each alone; then `store`, `loaders`, `gate`, `packaging` in that order | 42, 275, 245 and 5 passed; 739 passed |
| The CI selections: `-m "not evidence"` (gate-3.11) and `-m evidence` (the evidence job) | 3367 passed, 1 skipped, 5 deselected, 17 xfailed; 5 passed, 3385 deselected |
| Python 3.10 and 3.13, core install (`[dev]`: no libraries, no SciPy), working tree through `PYTHONPATH=src` | 3049 passed, 11 skipped, 17 xfailed (both) |
| sdist and wheel built from the tree; the wheel in a clean 3.11 venv; suite run from the checkout | 3049 passed, 11 skipped, 17 xfailed |

The one skip is D019, the coverage exception of the case list (see "Other checks"). The 17 strict xfails are
Q001–Q012 (W9) and I001–I005 (W11a). There are 3390 tests in all:

- 2823 from W0–W6 and W11b;
- 322 from W7: 275 in `loaders/`, 42 in `gate/` and 5 in `evidence/`;
- 245 from W8, in `store/`.

Without the libraries and SciPy (the 3.10, 3.13 and wheel runs), there are 11 skips:

- the nine W7 test modules, each one skip through its module-level `pytest.importorskip`;
- D019;
- the SciPy cross-check of the Hungarian solver.

W8's tests need neither library, so all 245 run there.

## Did the steps clobber each other?

- **Changed files.** Before S5, `git diff` was empty, so neither step changed a tracked file. The 80 untracked files
  were exactly the union of the two reports' lists:
  - W7: 51 files, 28 of them the R03 case copies;
  - W8: 29 files.

  No path was in both lists, and no step changed a file of an earlier step.
- **Copied data.** W7's `tests/evidence/library-hif-evidence.json` is byte-identical to `design-examples/`. The 28
  files in `tests/loaders/r03-cases/` are byte-identical to their sources: `research/probes/lib-cases/` for c01–c26
  and the knowledge base's `schemas/sample.hif.json` for c00.
- **Untouched:**
  - `data/` (`python -m khg_contracts.data --check` passes);
  - `errors.py`, `pyproject.toml`, the root `conftest.py` and CI;
  - the validator's layer table and runner, and the HIF modules.

## Duplicated or conflicting definitions

- **Validator layers.** Neither step registers a layer or runs a validator of its own.
  - W7's `validate=` modes call W4's runner: `hif.PROFILE_STEPS` for `"profile"` and the `role-convention`
    pipeline for `"convention"`. The structural guard of `"none"` reports W6's layer H findings.
  - W8's writes call W4's layer C and S modules. Layer C runs fastjsonschema first and jsonschema to list the
    findings of a refused record, so there is no new jsonschema runner.
  - The conformance runner's `hif_valid` clause calls `validate_hif`.
- **Error codes.**
  - `data/error-codes.json` is unchanged.
  - Every `KHG-` literal is registered and active: 10 codes in `loaders/`, 15 in `store/` and the codes their
    tests expect.
  - The six f-strings that start with `KHG-` are messages. The same code is passed in `codes=`, and
    `KHGError.__str__` does not repeat the prefix. No code is built dynamically.
- **Error classes.**
  - W7's `_input.InputRefused(LoaderError, ValidationError)` is the only new exception that callers see. It is a
    documented deviation (W7.md, "Errors"); its MRO is valid, and it does not affect W8.
  - W8's `Failed` and `Unknown` stay inside the conformance runner.
  - Otherwise both steps raise W0's classes.
- **Defined once.**
  - `compare_containers` is in `store/compare.py`, and G1 calls it.
  - `store.base.as_schema` delegates to `hif.encode.as_schema`, so there is no fifth `as_schema`.
- **Equal duplicates, kept:** `store.export.LITERAL_NODES` equals `hif.profile.LITERAL_NODES`
  (`("shared", "per_binding")`).
- **Same name, different meaning.** Each name is used only inside its own subpackage.

  | Name | One meaning | The other meaning |
  |---|---|---|
  | `Context` | `loaders`: what the libraries do not hold | `validate`: the run context |
  | `record_sort_key` | `loaders.reconcile`: the typed key of new incidence records | `record.canonical`: C1 record order |
  | `FLAGS` | `store`: the ten capability flags | `scorers._common`: the per-item flags |
  | `FORMATS` | `store.export`: the three export formats | `record.container`: `jsonl` and `json` |
  | `KINDS` | `store.where`: the relation kinds | `validate.layers`: the validator kinds |

  The session fixture `schema` is defined in both `tests/loaders/conftest.py` and `tests/store/conftest.py`. The two
  have the same content and are scoped to their directories.
- **Module state.** The only new cache is `store.conformance.suite.suite()`, an `lru_cache` of the packaged suite. It
  is read-only, and `resolve` returns copies. The loaders keep no module state.

## The seam: the store's HIF through the loaders (W8 → W7 → W8)

- **G1 assertion 3 always runs.** It asserts `compare_containers(original, final, ignore=()) == []`, and the same
  with the defaults, for the fixture and the directed slice (change 1).
- **Property probe** (scratch, not committed). The probe took 146 store states:
  - each of the 114 scenarios' stores after its `given` steps;
  - the store again after each of the 32 successful write steps of `when`.

  Each state was exported as HIF four ways, 584 documents in all: `literal_nodes` shared and `per_binding`, each for
  the whole store and for the fixture's directed-slice relations. Each document went through `load_xgi` →
  `export_xgi` → `load_hnx` → `export_hnx` (strict), then `from_hif`, and was then loaded into a fresh `MemoryStore`.
  - **All 584 documents passed.**
    - Both library exports were canonically equal to the store's HIF, and both export reports were empty.
    - `compare_containers` with the default `ignore` found no difference between the store's `khg-json` export,
      sliced the same way, and the decoded container.
    - It found none between the two stores' exports either.
    - Nothing raised.
  - **With `ignore=()`,** 554 of the 584 differ, and only in `recorded_by` on entity records (8,552 differences,
    all of that one kind). §4.2 maps no HIF key for an entity's `recorded_by`. W6 recorded this and S4 carried it
    forward. Fact records keep all three store fields through the chain.
- **Other directions.**
  - The store loads the fixture, and its `khg-json` export compares equal to the file.
  - Its HIF export loads into a `DiHypergraph` for the slice, with `roles("f:reg-1", "ex:TP53") == ["regulator",
    "target"]`.
- **Determinism.**
  - The EARL reports are byte-identical under `PYTHONHASHSEED` 0, 1 and 777, and between the editable install and
    the wheel. This holds for three runs:
    - the full store: 114 passed;
    - the TypeDB-like flag set: 70 passed and 44 inapplicable, as §6.5 says;
    - no flags: 12 passed.

    No run had a failed or `cantTell` scenario.
  - G1's five hash-seed children agree with `golden-sha256.json`.

## Changes made at S5

No fix was needed. Changes 1 and 2 remove allowances that existed only while the other step was missing (as at S4).
Change 3 commits the evidence file, as W7 asked.

1. **`tests/gate/test_roundtrip.py` (W7), `test_3_compare_containers_finds_no_difference`.**
   - The `try: import … except ImportError: pytest.skip("… not built yet (W8)")` guard is now a module-level import
     of `khg_contracts.store.compare_containers`.
   - A broken `store` package would otherwise have skipped G1 assertion 3 instead of failing it.
   - The store needs none of the libraries, so without xgi the core jobs still skip the module through
     `importorskip`.
2. **`tests/packaging/test_examples.py` (W0).** `GENERATED_LATER` is removed.
   - The byte-equality test now needs `write_examples` to find all five test-only files (`missing == []`).
   - The written tree must be exactly the 151 files of `design-examples/`.
   - `test_the_test_only_files_live_under_tests` compares all five files, the evidence file included.
   - Checked: with `tests/evidence/library-hif-evidence.json` moved away, these two tests fail. Before the change,
     they passed without it.
3. **`tests/evidence/library-hif-evidence.json` is committed.** It is byte-identical to `design-examples/`.
   - In CI the gate job deselects the evidence test and the core jobs skip it, so the committed file is what the
     packaging test compares.
   - It also makes the CI `examples` job pass. `python -m khg_contracts.examples out/ --tests tests` now writes 151
     files, and `diff -r` against `design-examples/` is empty. Before this change the evidence file was missing
     from `out/`.

## Other checks

- **Import hygiene.** Importing all 98 modules of the package, the 10 of `loaders/` and the 18 of `store/` included,
  loads none of these:
  - xgi, hypernetx, pandas, numpy or SciPy;
  - jsonschema, fastjsonschema or referencing.

  Without the libraries, `load_xgi` and `load_hnx` raise `ImportError` and name the extra to install.
- **Static checks.**
  - `ruff --select F,E9` (target py310) is clean on `src/` and `tests/`.
  - `ruff` with F, E9, E501, W and B (120 columns) and mypy (py310, `--follow-imports=silent`) are clean on `loaders/`
    and `store/`.
  - mypy reports errors in modules of earlier steps. mypy is not a CI job (§10.6), and S5 left those modules alone.
- **Public API (§5, §6.1, §10.2).**
  - `loaders`: `load_xgi`, `export_xgi`, `load_hnx`, `export_hnx`, `khg_to_xgi`, `xgi_to_khg`, `khg_to_hnx` and
    `hnx_to_khg` with §5's signatures. `Bundle.records`, `roles`, `derive` and `label`, and `ExportReport`'s seven
    keys.
  - `store`: the 15 protocol methods with §6.1's signatures, and `Where()` with the ruling's defaults.
    `MemoryStore(schema, *, clock=None, capabilities=None, store_id="memory")` and `memory_factory(schema, clock)`.
    `compare_containers(a, b, *, ignore=(...), header_ignore=(...))` with §6.3's defaults, and
    `conformance.run(factory, *, only=None, capabilities=None)`.
- **The wheel and the sdist.**
  - The wheel holds `loaders/` (10 modules), `store/` (13) and `store/conformance/` (5), and no caches.
  - The sdist carries the new tests, the 28 R03 cases and the evidence file.
  - In a clean 3.11 venv with only the wheel, `python -m khg_contracts.data --check` passes and
    `conformance.run(memory_factory)` gives 114 passed.
- **The D019 coverage exception.** W4's permanent skip stays, by design (§1.2 G2: "except D019, which S-PUT-006
  covers"). The cover now runs:
  - `tests/store/test_conformance.py::test_every_scenario_passes_on_the_memory_store[S-PUT-006]` expects
    `KHG-D019` from a stale `expect` and passes;
  - `tests/store/test_memory_store.py` checks the code directly.

## Carried forward (not integration breakages)

- **W9 `queue/`.** `replay(factory=store.memory_factory)` must load the base with an `at` before the first accept
  (W8.md). `test_export.py` reproduces `decision_hash` `sha256:518db0f4…7f29` that way. From S4: `d_container`
  already reports the queue header's D009.
- **W10 `migrate/`.** The G1 chain on the migrated sample runs through `khg_to_xgi`, `export_xgi`, `load_hnx`,
  `export_hnx` and `from_hif` (W7.md).
- **W11a.** `derive_memory_gold` uses `MemoryStore` with a `ScenarioClock` (W8.md).
- **W12 CLI.** `khg-conformance` calls `conformance.run`, then `conformance.write_report`, and exits 1 when
  `summary.failed` > 0. W12 must decide whether `cantTell` counts as a failure; §10.4 says only that
  `inapplicable` does not. The CI `wheel` job now waits only on W12, since `memory_factory` exists.
- **W13 consumers.** The P5 sequence needs xgi (`pytest.importorskip("xgi")`). P1, P7 and P10 run as written on
  `MemoryStore`.
- **W14.** Attach `tests/evidence/library-hif-evidence.json`. Add to the HyperNetX issue that `rename` also loses
  the isolated `ex:Mazarin`, as `clone()` and `sum()` do. `native-ops.json` records `dropped_nodes: 1` for `rename`,
  and §5's table mentions only the moved record.
- **Design observations.** These are left for a design decision; S5 made no change for them.
  - An entity's `recorded_by` is not exported to HIF. The seam probe confirms it in 554 of 584 round trips.
  - W7's deviations are recorded in W7.md: `InputRefused` is also a `ValidationError`; `validate="none"` refuses a
    document without the HIF structure, with H codes; `load_hnx` refuses the reserved `khg-extra-incidences` key
    (P014).
  - W8's gap-filling decisions are recorded in W8.md.

  None of them conflicts with the other step.
