---
title: "P2 implementation notes: S4 integration of W5 and W6"
type: project
status: draft
created: 2026-09-23
updated: 2026-09-23
---

# S4: integrating W5 (lifecycle, keys, layer D, `identity`) and W6 (`hif/`, layers H, R, P and decoding)

W5 and W6 ran in parallel on top of S3. This note records what the integration checked and what it changed.
**Nothing was broken**: the suite passed as the two steps left it. Three test assertions and one docstring were
tightened so that they state the combined behaviour (see "Changes made at S4"). Nothing in DESIGN.md,
`design-examples/` or `research/` was edited, and no packaged data changed.

## Result

| Run | Result |
|---|---|
| Full suite as delivered, Python 3.11 dev venv (`[xgi,hnx,fast,dev]`) | 2805 passed, 1 skipped, 17 xfailed |
| Full suite after the S4 changes, same venv | 2805 passed, 1 skipped, 17 xfailed |
| Same, `PYTHONHASHSEED=0` and `4242` | identical counts |
| Directory order reversed (`validate` first, `c1` last); `hif`, then W5's D tests, then `validate`, `c1`, `identity` | identical counts (2287 for the partial run) |
| Python 3.10 and 3.13, core install (`[dev]`, no SciPy), working tree through `PYTHONPATH=src` | 2804 passed, 2 skipped, 17 xfailed |
| Wheel built from the tree, installed in the clean 3.11 wheel venv, suite run from the checkout | 2804 passed, 2 skipped, 17 xfailed |

The skip is D019, the coverage exception of the case list (W8's scenario S-PUT-006). Without SciPy, the SciPy
cross-check of the Hungarian solver is skipped as well. The 17 strict xfails are Q001-Q012 (W9) and I001-I005
(W11a). S3 had 62: the other 45 were the active H (9), R (4), P (15) and D (17, without the D019 exception) codes,
which now pass. There are 2823 tests in all: 1992 from W0-W4 and W11b, 348 from W5 and 483 from W6.

## Did the steps clobber each other?

- **Changed files.** Before S4, the modified and untracked files were exactly the union of the two reports' lists
  (37 paths). S4 then changed `validate/context.py` (a docstring) and three of those files.
- **The one shared file.** `tests/validate/test_cases.py` (W4) is in both lists. W5 changed
  `test_the_c1_bases_have_no_error_and_only_the_designed_warning` (L008 on the C1 bases) and W6 changed
  `test_the_other_bases_pass_the_w4_layers` (the HIF bases). The hunks do not overlap, and both are present.
- **Files of earlier steps.** W5 changed `record/__init__.py` (W3: it exports `keys` and `lifecycle`) and six
  assertions in W4's `test_cases.py`, `test_runner.py` and `test_s_layer.py`, which now include the designed L008
  of §1.4, and D009 for the embedded schema. W6 changed only `test_cases.py`. The layer modules each step filled
  were W4 stubs assigned to that step in the layer table: `h`, `r`, `p` and `d_decode` (owner W6) and
  `d_container` (owner W5).
- **Untouched:** `data/` (and `python -m khg_contracts.data --check` passes), `pyproject.toml`, the root
  `conftest.py`, CI, DESIGN.md, `design-examples/` and `research/`. No build artefacts or caches are untracked.

## Duplicated or conflicting definitions

- **Validator layers.** Only W4's static table registers layers, and neither step changed it or the runner. Two
  modules have the letter D by design (§8.1): `d_decode` decodes, and `d_container` runs the cross-record checks
  after S.
- **Error codes.** `data/error-codes.json` is unchanged. All 112 `KHG-` literals in `src/` are registered and
  active, and no code is built dynamically.
- **D009 is checked in three places, all with the same meaning.** They are `d_container` (a container header's pin,
  and a queue header's), decoding (the HIF metadata's `khg-schema` and `khg-schema-sha256`) and `to_hif` (the
  header against the `schema` argument). All three compare id, version and sha256. In a HIF run `d_container`
  skips the pin (`pin=ctx.kind == "container"`), so decoding owns it. Without any schema, D009 is reported once
  (`Context.relation_schema`), by the first step that asks: `d_decode` in a HIF run.
- **D001 is also checked twice.** Decoding reports a node or edge declared twice; `d_container` reports an id
  declared twice in a container. One HIF file never gets both, because an error while decoding stops C, S and D
  (the layer rule).
- **Equal duplicates, kept.** `hif.profile.HIF_SCHEMA_URL` and `HIF_SCHEMA_SHA256` re-export `data`'s constants.
  `record.keys.POLICIES` equals `schema.builtins.POLICIES`, and `record.lifecycle.STATUSES` equals
  `schema.codegen.STATUSES` (one is a tuple, the other a list).
- **Same name, different meaning.** `RANKS` holds the lifecycle ranks in `record.lifecycle` and the calibration
  rankings in `scorers.completion`. `as_schema` in `hif.encode` accepts a `Schema`, a document or a path and checks
  it through `load_schema`, while `record._common.as_schema` wraps a mapping unchecked. Each is used only inside its
  own subpackage. The RFC 6902 test helpers exist in `tests/validate/conftest.py`, `tests/hif/conftest.py` and
  `tests/c1/test_lifecycle_container.py`, and behave the same on the three operations the case list uses.
- **`ctx.state` keys.** W6 added `"hif_layers"`, which is distinct from W4's `"c1"`, `"schema"`, `"entities"`,
  `"facts"` and `"queue_base"`. W5 reads `"entities"` and `"facts"`, which layer S sets. S keeps the container's
  own record objects, so `d_container` maps findings back to `/records/<i>` by object identity in container runs
  and in HIF runs alike.

## The seam: a HIF run through decoding (W6) into layer D (W5)

- **The fixture.** The HIF run and the C1 run give the same findings at the same paths: S024 at `/records/31` and
  L008 at `/records/29`. The directed slice gives L008 at `/records/27`.
- **Property probe** (scratch, not committed). 2,400 semantic mutations of the fixture container: status, rank,
  `status_ref`, time literals, precisions and calendars, a second holder of a key, redirects, supersession records
  and cycles, `complete`, dropped records, and fact references. For each mutant that passes J, V and C and that
  `to_hif` accepts, the probe compares the S, D and L codes of `validate_container(c)` and `validate_hif(to_hif(c))`.
  All 1,247 comparable containers gave identical codes. 1,220 of them had D or L findings (D010, D011, D012, D016,
  D017, D020, L008). The other mutants split three ways:
  - Decoding refused with D002 (a dropped entity) in 164 mutants. The C1 run has the same D002, and the layer rule
    ends the HIF run there.
  - In 48 mutants a dangling reference exports but does not re-import. An incomplete container with a dangling
    entity (9) or fact (1) reference gets nothing in the C1 run and D002 or P017 in the HIF run. A complete container
    with a dangling fact reference (38) gets D002 in the C1 run and P017 in the HIF run. This is W6's documented
    observation (W6.md, "Dangling references"), not a seam defect.
  - The remaining mutants were rejected by J, V or C before S, so they were not compared.

  Nothing raised and no step was skipped.
- **W6's HIF fuzzer** (`w6_fuzz.py`, scratch) was re-run on the integrated tree, where decoded mutants now reach
  W5's layer D: 27,000 validator runs (3 seeds, both engines, the `hif`, `role-convention` and `auto` kinds, and
  `from_hif`). Nothing raised and no step was skipped.
- **Determinism.** The reports of all 180 cases under both engines, the five bases, and `to_hif` (shared and
  `per_binding`) and `from_hif` on the fixture are byte-identical under `PYTHONHASHSEED` 0, 1, 777 and random.
- **G2 with both steps in.** 158 of the 180 cases are rejected first at their listed layer, with their listed code,
  under both engines. At the first rejecting step each has exactly its recorded codes: J 8, V 2, H 15, R 6, P 24,
  D 30, S 34, C 20, M 19. The other 22 are the Q (17) and I (5) cases, whose layers are still W9 and W11a stubs.

## Changes made at S4

No fix was needed. Each of the four changes removes an allowance that existed only while the other step was not in
the tree:

1. **`tests/c1/test_lifecycle_container.py` (W5), `test_a_hif_run_checks_the_decoded_container`.** Its two
   `pytest.skip` guards ("decoding (W6) is not built", "the fixture does not decode") are now assertions, and the
   decoding step must report nothing on the fixture. A skip on the failure condition would have hidden a broken
   seam.
2. **`tests/hif/test_cases.py` (W6), `test_the_hif_bases_have_no_error`.** `codes <= {...}` is now `==`: the fixture
   gives exactly S024 and L008, and the slice exactly L008.
3. **`tests/validate/test_cases.py` (W4, edited by W6), `test_the_other_bases_pass_the_w4_layers`.** The same
   tightening for the two HIF bases.
4. **`src/khg_contracts/validate/context.py` (W4), module docstring.** The list of `state` keys now names
   `"hif_layers"`. W6 documented the key in `d_decode.py` but, as the owner rule required, did not edit W4's file.

Check: a scratch pytest plugin made layer D skip HIF runs, and 7 tests then failed (all parameters of the three
tests above). Before these changes only (1) would have failed, and it would have been skipped if decoding had broken
as well.

## Other checks

- **Import hygiene.** Importing all 71 modules of the package, including `hif/`, `identity/`, `record.keys` and
  `record.lifecycle`, loads none of xgi, hypernetx, pandas, numpy or SciPy. It does not load jsonschema,
  fastjsonschema or referencing either. W5 and W6 add no module-level caches.
- **Static checks.** `ruff --select F,E9` (target py310) is clean on `src/` and `tests/`. The new code uses no
  Python 3.11-only feature, has no `print` in library code, and makes no network access.
- **Public API (§10.2).** `hif.to_hif(container, schema, *, relations=None, literal_nodes="shared",
  schema_document=False)`, `hif.from_hif(hif, schema=None)` and `identity.relate(a, b, *, schema)`, with the seven
  labels, are all present. `record.keys` and `record.lifecycle` are submodules of `record/` (§10.1).
- **The wheel** contains `hif/` (10 modules), `identity/` (2), `record/keys.py`, `record/lifecycle.py` and all 13
  layer modules, and no caches.

## Carried forward (not integration breakages)

- **W8 `store/`.**
  - `keys.collisions` reports only the incoming facts. The store should also run
    `keys.key_invariant_violations(post, S, keys=touched)` and raise D016 (W5.md, "For the later steps").
  - `export("hif")` goes through `to_hif`, which raises D009 unless the header pins the store's schema.
  - `compare_containers` compares the header's `as_at`, which HIF does not carry (W6.md). Check any scenario that
    round-trips `as_at` through HIF.
- **W9 `queue/`.** `d_container` already reports the queue header's D009, so layer Q must not report it again.
- **W7 `loaders/`.** Use `hif.PROFILE_STEPS`, `hif.canonical_order`, `hif.node_value`, `to_hif` and `from_hif`
  (W6.md, "For the later steps").
- **Design observations from W6, left for a design decision (no change made).** An entity's `recorded_by` is not
  exported (§4.2 against §2.2). A dangling reference in an incomplete container exports but does not re-import (the
  seam probe confirms both directions). The header fields `as_at`, `created_at` and `generator` have no HIF metadata
  key.
- **CI.** The CI `wheel` job still needs W12 (the CLI) and W8 (`memory_factory`), as S3 noted.
