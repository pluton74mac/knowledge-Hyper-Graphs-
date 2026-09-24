---
title: "P2 implementation notes: S3 integration of W4 and W11b"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# S3: integrating W4 (`validate/` core) and W11b (`scorers/`)

W4 and W11b ran in parallel on top of W3. This note records what the integration checked and what it found.
**No integration fix was needed**: no file in `src/` or `tests/` was changed at this stage. Nothing in DESIGN.md,
`design-examples/` or `research/` was edited.

## Result

| Run | Result |
|---|---|
| Full suite, Python 3.11 dev venv (`[xgi,hnx,fast,dev]`) | 1929 passed, 1 skipped, 62 xfailed |
| Same, `PYTHONHASHSEED=0` and `4242` | identical counts |
| Directory order `scorers, validate, …` and `validate, scorers, …` | identical counts |
| Python 3.10 and 3.13, core install (`[dev]`, no SciPy) | 1928 passed, 2 skipped, 62 xfailed |
| The built wheel in a clean 3.11 venv (`[dev]`), suite run from the checkout | 1928 passed, 2 skipped, 62 xfailed |

The skip is D019, the coverage exception of the case list (W8's scenario S-PUT-006). Without SciPy, the SciPy
cross-check of the Hungarian solver skips too. The 62 strict xfails are the codes whose layer modules are still
stubs (W5, W6, W9, W11a; see [W4.md](W4.md)). 1992 tests in all: 822 from W0-W3, 1028 from W4 and 142 from W11b.

## Did the steps clobber each other?

- **Tracked files.** `git diff` is empty: neither step changed a file of W0-W3 (not `__init__.py`, `errors.py`,
  `data/`, `pyproject.toml`, the root `conftest.py` or `tests/scorers/r05.relation-schema.json`).
- **New files.** Before this note, the 54 untracked files were exactly the two reports' lists (W4: 26, W11b: 28),
  and no path was in both. `scorers/memory.py` (a W11b stub) and `validate/layers/{h,r,p,d_decode,d_container,q,i}.py` (W4 stubs)
  belong to later steps, as the reports say. No build artefacts or caches are untracked.
- **Imports.** Neither package imports the other. Both read the packaged schemas through
  `data.schema_documents()`, which parses fresh copies on each call, so no mutable state is shared between them.

## Duplicated or conflicting definitions

- **Validator layers.** Only W4's static table (`validate/layers/__init__.py`) registers layers. W11b checks layer
  I for its own inputs in `scorers/_inputs.py` (the C4 draft schema); this is not a validator layer. The two agree:
  on the C4 cases MC176 (I001), MC177 (I002) and MC179 (I004), `_inputs.c4_findings` and
  `validate.engines.findings(C4_SCHEMA_ID, …)` give the same single code under both engines, and neither reports
  anything on the base `c4-items.jsonl`. MC178 (I003) and MC180 (I005) need more than the draft schema: W11b raises
  I003 when a scorer reads the embedded gold record, and I005 is W11a's.
- **Error codes.** Neither step changed `data/error-codes.json`. Every `KHG-` code literal in `validate/` and
  `scorers/` is registered and active; the scorers use C010, I002, I003, J007, Q001 and Q003.
- **Codes from schemas.** `validate.engines.code_of` and `scorers._inputs._code` read `x-khg-code` the same way (a
  code, or a keyword map with a `default`). On the packaged `c5-outputs.jsonl` both report nothing, and on an
  output with a required field removed both report C010.
- **Equal duplicates, kept.** `C4_SCHEMA_ID` and `C5_SCHEMA_ID` are defined in both `validate/engines.py` and
  `scorers/_inputs.py`, with the same values (the packaged `$id`s). The package now has four small closed-resolver
  jsonschema runners (`schema/checks.py`, `record/_structure.py`, `scorers/_inputs.py` and the general one,
  `validate/engines.py`). They agree, so they were left alone; merging them is a refactor, not an integration fix.
- **Same name, different meaning.** `scorers._facts.CALENDARS` (the scorer option `strict` or `as_written`) and
  `record.windows.CALENDARS` (the calendar names); `FORMAT` in `scorers` (`khg-scorers/1.0.0`) and in
  `validate.registry` (`khg-codes/1.0.0`); `as_schema` in `record/_common.py` (wraps a mapping unchecked) and in
  `scorers/_common.py` (goes through `load_schema`). Each is used only inside its own subpackage, so they do not
  conflict.

## Other checks

- **Import hygiene.** Importing all 57 modules of the package loads none of xgi, hypernetx, pandas, numpy or SciPy,
  and not jsonschema, fastjsonschema or referencing either (both engines are imported lazily). The Hungarian solver's
  SciPy backend imports numpy and SciPy inside the function.
- **Determinism.** `validate()` gives byte-identical results on all 180 cases under both engines with
  `PYTHONHASHSEED` 0, 1 and 777. W11b's own test covers the scorers.
- **Static checks.** `ruff --select F,E9` (target py310) is clean on `src/` and `tests/`. No Python 3.11-only feature,
  no `print` and no network access in the new code.
- **The wheel** contains all of `validate/` (with `layers/`) and `scorers/`.

## Known gaps (not integration breakages)

- Until W11a fills `validate/layers/i.py`, `validate_item` runs only J and V, so it can accept C4 items that the
  scorers refuse (I001, I002, I004). W11a can then make `scorers._inputs.check_items` delegate to `validate_item`
  (W11b's note) and reuse `validate/engines.py` in place of the scorers' own runner.
- The CI `wheel` job calls `khg-validate` and `khg-conformance`. These are still the W0 placeholders (exit 2) until
  W12 (and W8 for `memory_factory`), so that job cannot pass yet. This was already true before W4 and W11b.
