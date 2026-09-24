---
title: "P2 implementation notes: review fixes, group c (hif, loaders, migrate)"
type: project
status: draft
created: 2026-09-24
updated: 2026-09-24
---

# Review fixes, group c: `hif/`, `loaders/`, `migrate/`

This group owns `src/khg_contracts/hif/**`, `loaders/**` and `migrate/**`, with `tests/hif/**`, `tests/loaders/**`,
`tests/migrate/**` and `tests/evidence/**`. It applied the review's five confirmed findings (F1, F2, F3, F5, XGM-02)
and its one LOW finding (F6). No finding concerned `migrate/`, and nothing there changed. Nothing in DESIGN.md,
`design-examples/`, `data/` or another group's files was edited. Nothing was committed.

**How the fixes were checked.** Each fix has a regression test that fails before the fix and passes after it. The
"before" runs put a copy of the current `src/` first on `PYTHONPATH`, with `hif/`, `loaders/` and `migrate/` taken
from f99a8af. The other groups' changes stayed in place, so each test isolates this group's fix. XGM-02 asks only
for tests, since the code was already right. Its tests pass on the code and fail under both of the review's mutants
of `hnx.py:221`:

- G1-20 checks only splits;
- G1-12 removes the injectivity condition.

**The interrupted attempt.** An earlier run of this group was stopped by a usage limit. It left the F1 change to
`loaders/reconcile.py` and four F1 tests in `tests/loaders/test_export.py`, and checkpoint 40eab24 preserved both.
They were reviewed and kept:

- the three regression tests fail before the fix and pass after it;
- the guard test passes both ways, as a guard should.

The attempt left no other edits.

## Confirmed findings

| Finding | Change | Tests (fail before, pass after unless marked) |
|---|---|---|
| F1: a profile export kept the loaded `network-type`. With only directed records left, it wrote `undirected` (P011), and the loaders, `from_hif` and `*_to_khg` refused it | `reconcile._network_type` applies the profile's direction rule (§4.2; P010, P011) to the exported records of a profile file. The value is `directed` when every record has a direction. A loaded `directed` becomes `undirected` once a record lacks a direction; an absent or `undirected` value stays. Files without the profile and exports without incidences keep the loaded value | `test_export.py`: `test_a_profile_file_left_with_directed_records_only_exports_as_directed` (both libraries: removes `f:loop-yyz` and `f:married-curie`, then checks no validator error, a reload into a `DiHypergraph`, an identical re-export and `to_hif(from_hif(out)) == out`); `test_a_restriction_to_the_directed_facts_goes_back_to_c1` (XGI `subhypergraph` and HNX `restrict_to_edges`, then `derive`, then `*_to_khg`); `test_a_directed_profile_file_that_loses_a_direction_no_longer_exports_as_directed` (a HyperNetX cell's direction removed natively). Guard, passes both ways: `test_the_loaded_network_type_stays_outside_the_direction_rule` |
| F2(a): HyperNetX `label` accepted a record without direction in a directed file, which the strict export wrote and the loaders then refused (P010) | `hnx.attach` raises P010 when the context is directed and the record has no direction, and either the record goes under `khg-extra-incidences` (the cell has a role) or the new cell has no direction either. `_cell_properties` also returns the cell's direction column. This follows the verifier's caution: a cell added with a direction gives its record that direction | `test_bundle.py::test_no_library_labels_a_record_without_direction_in_a_directed_file` (the `[hnx]` case: a new cell and a further record of a labelled pair; the `[xgi]` case passed before and pins the libraries' agreement). Guard: `test_a_new_hypernetx_cell_gives_its_record_the_cells_direction` |
| F2(b): `label` accepted an exact repeat of (edge, node, role, role-position), which the loaders then refused (R002) | `Bundle.label`, for both libraries, raises R002 after the P016 check when a live record of the pair (`records(edge, node)`) has the same role and role-position. The key is layer R's: `_position_key` reads an integral float as its integer and keeps a malformed value as itself. Direction is not part of the key (§4.1 rule 2) | `test_bundle.py::test_label_refuses_an_exact_repeat_of_a_record_of_the_pair` (tail, head and no direction; position `3.0` against 3; a repeat of an earlier label); `test_another_role_or_role_position_of_a_pair_is_a_record_of_its_own` (YUL at stop 4, TP53 in a third role; the export reloads) |
| F3: `to_hif` copied `extensions["hif:weight"]` without checking it. Non-numbers gave invalid HIF (H009), and null was dropped together with the whole `extensions` object | `encode._split` raises C010 when `hif:weight` is present and is not a finite number: null, a boolean, a string, an array, an object, NaN or an infinity. This covers entities, hyperedges and bindings. Integers of any size and finite floats pass with their JSON type. The path is `""` and the message names the owner, like `_split`'s other C010 | `test_to_hif.py::test_a_hif_weight_that_is_not_a_finite_number_is_c010` (21 cases: 7 values by 3 owners). Guard: `test_a_hif_weight_of_any_json_number_is_written` |
| F5: a `role-position` of `2.0` was read three ways | Decoding stores `convention.role_position(...)`, so `2.0` decodes as 2. `make_record` accepts what `role_position` accepts and writes the integer (4.0 as 4); a value it rejects is still R004. Layer S's part (S015 reading integral floats) is group b's b-validate-02, already in the tree | `test_from_hif.py::test_an_integral_float_role_position_decodes_as_its_integer` (both engines: the decoded binding holds the int 2, `decode` agrees, `validate_container` passes, and `validate_hif` gives the fixture's findings); the 4.0 label in `test_bundle.py::test_another_role_or_role_position_of_a_pair_is_a_record_of_its_own`. Guards: three more R004 cases (2.5, 0.0, `"4"`) in `test_label_refuses_a_record_that_is_not_one` |
| XGM-02: no test isolated the HyperNetX collapse rule, so either mutant passed the gate and the suite | Tests only. The `export_hnx` docstring now describes what `strict=False` does (see Decisions) | `test_export.py::test_a_collapse_across_edges_raises`: `rename({"ex:Paris": "ex:Kraków"})` and `rename({"ex:HeLa": "ex:X", "ex:insulin": "ex:X"})` raise P005 with exactly the moved records in `moved_conflict`. With `strict=False` the report holds the same entries and the records are exported on the new node. Passes on the code and fails under G1-20 and G1-12 (both cases) |

## LOW finding

| Finding | Outcome |
|---|---|
| F6: `incidence_sort_key` read an undeclared node's value as null, so an edit-free loader round trip of `to_hif` for an incomplete container reordered the incidences | Applied. An incidence whose node has no record sorts by `{"entity": node}`. Only entity values can name an undeclared node, because `to_hif` declares every derived node. Tests: `test_order.py::test_an_incidence_of_an_entity_the_file_does_not_declare_sorts_by_its_entity_value` (fixture without `ex:metformin` and without `complete`: `canonical_order(to_hif(c)) == to_hif(c)`, and the key equals the one for a declared entity node); `test_export.py::test_an_edit_free_round_trip_keeps_the_order_of_an_entity_the_file_does_not_declare` (both libraries: the export equals the input, and the report is empty) |

## Decisions

- **F1 changes the value only when the rule requires it.** The verifier's fix writes `undirected` whenever any
  record lacks a direction. That would add a `network-type` key to a profile file that had none. The profile does
  not require the key, and P010/P011 accept a missing key while some incidence lacks a direction. So a loaded value
  that already satisfies the rule is kept, key presence included. Both versions pass the verifier's regression
  tests.
- **A native direction removal follows the rule.** In a directed file, `set_property(cell, "direction", None)`
  now exports `undirected` rather than an invalid `directed` file. The export follows the library (§5), and the
  usage gives the direction back on import.
- **`label` refuses where the export would be refused.** P010 in `label` follows §5 ("in every mode the loaders
  refuse ... P010") and matches XGI. After F1, a HyperNetX record without direction would otherwise flip the file
  to `undirected` silently.
- **Order of `label`'s checks:** first the codes of `make_record` (P005, H005, R004, H009), then P016, then R002,
  then the library's own `attach` (P005 for a missing membership, P010). R002 reads only live records, as P016 does.
- **F3 uses C010**, the registry's "wrong JSON type or out of range". It is raised in `to_hif`, not in layer C:
  - the C1 schema's `extensions` definition constrains key names only;
  - changing it touches a packaged schema, its manifest hash and `design-examples/` (request 1).

  Until then, `validate_container` and `MemoryStore.put` accept such a weight. `MemoryStore.export("hif")` now
  raises C010 where it used to write invalid HIF.
- **XGM-02: `strict=False` keeps exporting a collapse.**
  - The docstring said `strict=False` "drops and reports" a non-injective move. The code exports the moved record
    on its new node and reports it under `moved_conflict`. Only a record repeating a `khg-bid` that another cell
    carries is not exported.
  - W7 records this behaviour ("a record that repeats a khg-bid another cell carries is a moved_conflict too and is
    not exported").
  - DESIGN §5 asks `strict=False` to drop only unlabelled memberships and partial records.
  - Dropping the moved record would turn a collapse into a partial fact.
  - So the docstring was corrected and the code left alone. If the director wants collapses dropped, that is a
    one-line change in `_Reconciled`.

## Observations (not changed)

- **Renaming onto a node already in the same edge.** `rename({"ex:insulin": "ex:metformin"})` with `strict=False`
  exports two `agent` records of `ex:metformin` in `f:coadmin-1`, and `validate_hif` reports R002 for that file.
  The strict export raises as it should. After the rename, HyperNetX 2.4.3 holds two cells for the pair and lists
  each of them twice. The loader keeps one record per `khg-bid` (b1 and b2) and reports the repeats. A later
  decision could drop the moved record there too.
- **Two messages are imprecise for collapses.** The strict refusal says "export with strict=False to drop and
  report them", which is true for unlabelled memberships and partial facts but not for a collapse. The docstring of
  `export_xgi` names a non-injective move, which XGI cannot produce. Both are wording only.
- **W7.md's list of `label` refusals is superseded** by the `label` docstring, which now names R002, and P010 for
  both libraries.

## Requests to other groups

1. **Record schema** (`data/schemas/khg-record-1.0.0.schema.json`, `schema/codegen.py`, the manifest,
   `design-examples/`; group b). This is optional. Give the `extensions` definition `properties: {"hif:weight":
   {"type": "number", "x-khg-code": "KHG-C010"}}`, so that `validate_container` and `MemoryStore.put` refuse the
   weights that `to_hif` now refuses. NaN and infinities cannot come from parsed JSON.
2. **Package root** (`src/khg_contracts/__init__.py`, `tests/packaging/test_api.py`). This is ruling 6, if no one
   has applied it yet:
   - add `"khg-migration-report": "1.0.0"` to `CONTRACTS`;
   - §11.1 lists the format id, and `CONTRACTS` "maps every format id above";
   - `migrate/` already writes the id (`migrate.REPORT_FORMAT`).
3. **DESIGN** (director):
   - §5 and §10.2: `Bundle.label` also raises R002 for an exact repeat, and P010 in HyperNetX too.
   - §4.2: `hif:weight` must be a finite number (C010 from `to_hif`).
   - §5: `strict=False` exports a collapse and reports it under `moved_conflict` (see Decisions).

## Checks

- The owned suites (`tests/hif`, `tests/loaders`, `tests/migrate`, `tests/evidence`) and `tests/gate` pass in the
  dev venv (Python 3.11, xgi 0.10.2, hypernetx 2.4.3).
- The owned suites also pass under Python 3.10.20 and 3.13.12 (the CI venvs with `PYTHONPATH=src`). The loader
  tests skip there without the libraries, as W7 notes.
- The verifier's scratch regression tests for F1-F5 all pass.
- `ruff` (F, E9, E501, W, B; py310; 120 columns) is clean on every changed file.
- `mypy` (py310) on `loaders/` and `hif/` gives output identical to the before tree, and reports nothing in either
  package.
- **Full suite.** Run with `python -m pytest -q -p no:cacheprovider` from the repository root, on the shared
  working tree with the other groups' changes in progress: **3 failed, 5751 passed, 1 skipped**. The same three
  tests fail on the before tree, so none of them comes from this group:
  - `tests/cli/test_validate.py::test_doc_texts_feed_the_span_check` follows from group b's b-validate-10 (the CLI
    tests' owner updates it);
  - `tests/scorers/test_memory_layer_i.py::test_the_draft_names_i001_i002_and_i004` follows from ruling 7 (the
    scorer tests' owner updates it);
  - `tests/consumers/test_verbatim.py::test_the_copy_is_verbatim[P7]` already fails at f99a8af.
