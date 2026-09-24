---
title: "P2 implementation notes: review fixes, group ad (jsonio, record, identity, store)"
type: project
status: draft
created: 2026-09-24
updated: 2026-09-24
---

# Review fixes, group ad: `jsonio`, `record/`, `identity/`, `store/`

This group owns `src/khg_contracts/jsonio.py`, `record/**`, `identity/**` and `store/**`, with `tests/c1/**`,
`tests/identity/**` and `tests/store/**`. It applied the review's confirmed findings a-record-1 to a-record-6 and
d-store-01 to d-store-07, most of the LOW ones, and the director's ruling 4 (DESIGN §14). Nothing in DESIGN.md,
`design-examples/`, `data/` or another group's files was edited. Nothing was committed.

Every fix has a regression test that fails on the file as it was at HEAD and passes now: each was run both ways,
with the changed source files restored to HEAD for the "before" run. d-store-06 and d-store-07 are test-only
findings; their tests were run against the mutations that the review used (and three more for d-store-06).

## Ruling 4: container suffixes

`record.read_container` and `record.write_container` dispatch on the suffix only (`record.container.SUFFIXES`):
`.json` is one JSON document, `.jsonl` is JSONL, and any other suffix is `ValueError`, raised before the file is read
or anything is written. `write_container(format=...)` may restate the suffix's layout; a `format` that the suffix
does not name (or an unknown one) is `ValueError`. With `format=None` the suffix decides, as W3 decided; the old rule
that an explicit `format` wins, and that every name but `.json` was written as JSONL, is gone. `MemoryStore.load`
of a path reads `.jsonl` through `iter_jsonl` and anything else through `read_container`, so a path with another
suffix is `ValueError` there too.

Tests: `tests/c1/test_container.py` (`test_formats_and_suffixes`, rewritten; the write and read refusals for eight
and four names, the suffix checked before V and C); `tests/store/test_load.py::test_load_reads_paths`.

The CLI part ("the CLI exits 2") is the CLI's; see request 1.

## Confirmed findings

| Finding | Change | Tests |
|---|---|---|
| a-record-1: an omitted `supports` had three defaults | One rule, §2.8.1's: evidence carried without `supports` supports what it resolved to in the **first version that carries it** (that version's list, else every bid of that version); `normalize`'s default (every bid) now applies only to evidence a record carries first. `record.carried_supports(versions)` and `record.resolve_supports(records)` (new, in `canonical.py`) write the lists out. `canonical_container` does so for `content: history`; `lifecycle.history_problems` does so before the pairwise version rule; `MemoryStore.put` fills a new version's omitted lists from the stored version (`_carried`); `MemoryStore.load` does so over the loaded versions of each id, after the version the store holds (`_carry_loaded`); `compare_containers` does so for history containers | `test_canonical.py` (the fixture's history with e1's `supports` dropped canonicalises to the fixture; the helper's rules), `test_container.py` (write and read in both layouts gives the fixture, validates, same `supported_values`), `test_lifecycle.py` (history rule), `test_compare.py`, `test_load.py` (history load; a later snapshot load of v2), `test_memory_store.py` (put v1 then v2 without `supports`: accepted, e1 keeps b1-b3, a second put is a no-op) |
| a-record-2: an integer literal of more than 4300 digits was a plain `ValueError` | `jsonio._int` counts the digits first (17 or more is J006; JSON has no leading zeros); `jsonio.number` names a huge int by its bit length, since `str()` of it is itself a `ValueError` | `test_jsonio.py`: 17, 4301 and -5001 digits for `loads` and `loads_lines`; `canonical({"x": 10**5000})`; `validate(bytes)` gives J006 and does not raise |
| a-record-3: a year of more than 4300 digits was a plain `ValueError` | `windows`: a literal's year has 4 to 16 digits (`YEAR_DIGITS`, Wikibase's own bound; C004 beyond), an instant's 4 to 17 (`INSTANT_YEAR_DIGITS`: the upper window bound of the largest literal year is an instant too; C011 beyond). `values._YEAR` has the same bound. Messages shorten the text | `test_windows.py`: 17, 4301 and 5000 digits through `window`, `value_identity`, `canonical_value`, `parse_time`, `normalize`; instants and `store.Where(as_of=...)`; the largest years have windows whose bounds parse; `validate_container` gives findings (C004 or S006, whichever layer S reports) instead of raising |
| a-record-4: the depth limit depended on the Python version, and the record walkers overflowed below it | `jsonio.MAX_DEPTH = 256`: `loads` and `loads_lines` give J001 "nesting deeper than 256 levels" at the first value too deep, the path and message layer J gives for an object in memory (group b set the same limit there; `tests/validate/test_nesting.py` passes with both). A bracket count skips the walk for shallow texts (a JSONL record line, as a rule). `jsonio.canonical` and `record._common.nfc_deep` keep their recursive fast path and fall back to iterative walkers on `RecursionError`, with the same output (differential check on 3,017 documents); a container that holds itself is `ValueError` | `test_jsonio.py` (the limit, the path, JSONL lines one by one, wide documents, any depth written, a cycle), `test_canonical.py` (normalise 3,000 levels; the two walkers agree; a cycle), `test_container.py` (a container at the limit round-trips in both layouts and one level deeper is J001; the canonical text and hash of a 1,500-level container) |
| a-record-5: the inverses merged the versions of a history | `rdf_relation_instance` is `ValueError` when a fact id comes twice (one IRI per fact; §6.5 needs named graphs per version). `from_incidence_rows` is `ValueError` for rows of several versions of a fact, for rows of one fact that disagree on relation or status, and for a bid given twice. `from_rdf_relation_instance` is `ValueError` for two values of one predicate on a fact or a binding; the same triple twice counts once | `test_project.py`: the history fixture is refused by both; its snapshot round-trips through both (f:reg-1 retracted); disagreeing rows and triples |
| a-record-6: the matcher recursed once per augmenting-path step | `injective_match` keeps its own stack, after a greedy first pass (each row takes its first free column). The same answers on 5,000 random graphs as the recursive search, and on 400 against brute force; the all-true 1,500 x 1,500 case takes 0.2 s | `test_refine.py`: staircases of 1,500 rows (true and false), all-true, a 300-row staircase under a recursion limit 60 frames above the caller, `fact_refines` on a 100-reading staircase under a limit 50 frames above it; `test_memory_store.py`: `find` with 150 `any` patterns under a limit 60 frames above it |
| d-store-01: S-LIFE-013's history export failed D014 | `lifecycle.COMPOSITE_STEPS = {("superseded", "disputed")}`: between consecutive versions of a fact in a history, that pair is accepted. It is the one step that an undo resolved by a dispute writes in one version (§2.7, S-LIFE-013). `TRANSITIONS` is unchanged, so an event still may not dispute a superseded fact (D014) | `test_lifecycle.py` (the Kraków history v1 asserted, v2 superseded, v3 disputed; `transition_problem` still D014; another status after superseded still D014); `test_conformance.py::test_every_write_the_scenarios_make_leaves_valid_exports`: after every accepted put, apply or load of the 114 scenarios' `when` steps, the snapshot and history exports validate (S-LIFE-013 step 2 failed before) |
| d-store-02: `put` could re-point a disputed fact's `status_ref` | `lifecycle.put_problem`: a `status_ref` other than the current version's is D014 (the belief axis, which only events move; §6.2 puts D014 before record validation, so a disputed record without `status_ref` is now D014, not C006) | `test_memory_store.py`: `m:nothing`, a fact id and a dropped pointer are D014 and the store stays at version 2; an unchanged put is a no-op; an editable field still changes; an asserted fact cannot gain one |
| d-store-03: a put or event could give a held evidence id a second record | `lifecycle._evidence_problems` compares the n-th record of an id in the old version with the n-th in the new one, and gives D013 when a new version has more records under an id than the old one (so a legacy duplicate kept as it is passes); `_events._append_evidence` gives D013 for an id the fact holds or that the event gives twice | `test_events.py` (the forged e1 in either order, e1 twice, `add_evidence` with e9 twice), `test_lifecycle.py` |
| d-store-04: undoing two supersessions sharing a superseding fact was D001 | `_events._retract` collects each superseding fact once, and not one that is itself a target | `test_events.py`, for `retract` and `dispute`: the receipt, the status, the lifecycle record binds each fact once, both exports validate |
| d-store-05: an unhashable evidence id was a `TypeError` | `_append_evidence` looks for clashes among string ids only; any other id goes on to layer C (C010) | `test_events.py`: a list and an object id (TypeError before) and a number and null (C010 before too) on `add_evidence`, `transition` to asserted and `end_validity` |
| d-store-06: the §6.2 check order was untested | Tests only | `test_memory_store.py`, five pair tests: D016 before D018; D008 before D016; D016 before D011 (S-LIFE-014's version with a born_in collision); capability before `NotFound` (supersede, dispute, retract, end_validity); D014 and D017 before record validation. They fail on the review's `_commit` mutation (two of them) and on three more mutations (NotFound before capability in `supersede`, validation before the status rules in `put`, supersession constraints before keys), one each |
| d-store-07: the walk's "always ends" was untested | Tests only | `test_base.py`: a supersession cycle that a trusted load keeps (the walk ends, both directions, terminal `[]`), and a diamond (D reached twice, walked and listed once). With the review's mutation the first hits its 10 s alarm and the second lists D twice |

## LOW findings

| Finding | Outcome |
|---|---|
| a-record-7: a width of 0 dropped a role's fillers silently | Applied. `position_map` requires a width that is a positive integer (`ValueError`); `test_project.py` (0, -1, `True`, 2.5, `"4"`) |
| a-record-8: a lone surrogate made `write_container` and `container_sha256` raise `UnicodeEncodeError` | Applied. Both give `ValidationError` J005, as `jsonio.digest` does, before any file is made (the file is now written as bytes); `test_container.py` |
| d-store-08: restating the end cause while refining the end was S004/S014 | Applied. `end_validity` reuses the fact's `khg:end_cause` binding (the usage has max 1): an equal cause adds nothing, and the evidence supports the end only (§2.8.1: "if one is written"); another cause replaces the value, which the version rule refuses (D013); `test_events.py` |
| d-store-09: writes after a trusted load were blamed for a violation that was already there | Applied in part. A violation after the write is new only when its facts are not all part of one violation of the same key before it (W8's rule compared exact id tuples), so retracting or deprecating one of three normal facts on a key is accepted. Not changed: a new version of a fact that stays asserted in the violation (`add_evidence`) is still refused, since `keys.collisions` blames an incoming asserted fact that takes part (W5's rule); changing that is a policy decision. `test_memory_store.py` |
| d-store-10: a redirect write left values naming the redirected entity (D020) | Not applied: a design decision. W8 accepts facts that keep a value written before its entity gained `redirect_to`, so it presumes stores that hold such values; refusing the redirect instead would make a merge impossible while any fact names the entity, and v1 has no rewriting (§2.2). Request 9 |
| d-store-11: `Timed` sorted set members by their canonical text | Applied. A set of strings is sorted as strings (§6.3, as `Where.as_dict` does); mixed members keep the canonical-text order; `test_timed.py` |
| d-store-12: a declared flag beyond the ten crashed `conformance.run` | Applied. The runner tests the declared flags that are among the ten; the report's subject still lists every declared flag and `tested_capabilities` the ones tested. A caller's own `capabilities=` list is still checked; `test_conformance.py` |
| d-store-13: event fields are checked before the capability | Not applied. §6.2's order is for the checks of a write; an event whose own fields are malformed is refused before any of them, as `put` refuses a malformed `actor` or `at` first. Changing it means reordering four handlers for a case with no scenario. Request 9 |
| d-store-14: reads raised `TypeError` on a loaded record with a list status, rank or visibility | Applied. `MemoryStore._passes` lets no filter pass a record whose status, rank, visibility or relation is not a string (what `_table` promises for malformed records); `test_load.py` |

## Follow-ons in this group's files

- **Integral float versions** (group b's request 4, and the F10 rule W3 applied to precisions): `record_sort_key`,
  `resolve_supports` and `lifecycle.history_problems` read a version `2.0` as 2, so the canonical order, the first
  carrier of evidence and the history rules agree with the canonical text, which writes `2`. Tests in
  `test_canonical.py` and `test_lifecycle.py`.
- `jsonio.MAX_DEPTH`, `record.carried_supports`, `record.resolve_supports`, `record.windows.YEAR_DIGITS` and
  `INSTANT_YEAR_DIGITS`, `record.container.SUFFIXES` and `record.lifecycle.COMPOSITE_STEPS` are new public names
  beside §10.2's.

## Requests to other groups

1. **CLI** (`cli.py`, `tests/cli/`). Ruling 4 says the CLI exits 2 for another suffix. `record.read_container` now
   raises a plain `ValueError` for one: `_argument` (the `--base` files) and `_convert` (reading IN) catch only
   `OSError` and `ValidationError`, so they should turn it into exit 2. `khg-migrate` writes JSON for every name but
   `.jsonl`; under the ruling another suffix would exit 2 too. A CLI test for a 5,000-digit integer can now expect
   `khg-validate` to print a J006 finding and exit 1 (a-record-2's verifier asked for it).
2. **DESIGN §2.7 and the D014 meaning** (`data/error-codes.json`): say that a history may go from superseded to
   disputed in one version, the step an undo resolved by a dispute writes (S-LIFE-013); an event still may not.
3. **DESIGN §2.8.1**: say that evidence carried without `supports` keeps the list of the first version that carries
   it; the canonical writer, the version rule, `put` and `load` now read it so.
4. **DESIGN §10.2 and §2.10**: `write_container` and `container_sha256` also raise J005 (a lone surrogate in a
   container built in memory); `jsonio.loads` J001 includes the nesting limit of 256 levels; the projection inverses
   take one version per fact (`ValueError` otherwise); a width is a positive integer.
5. **Record schema** (`data/schemas/khg-record-1.0.0.schema.json`, `schema/codegen.py`, the manifest): optionally
   bound the time pattern's year to 16 digits and the instant pattern's to 17, so that layer C reports C004 and C011
   where layer S reports them now.
6. **Layer J** (`validate/layers/j.py`, group b): it may import `jsonio.MAX_DEPTH`; both are 256 with one meaning,
   and `tests/validate/test_nesting.py` passes with both in place.
7. **Validator** (`validate/runner.py`, group b): `validate(..., bases=path)` with a suffix other than `.json` or
   `.jsonl` now raises `ValueError` from `read_container`, an argument error; a finding would suit
   "never raises on bad input" better if bases count as input.
8. **Registry**: a code for evidence ids given twice in a brand-new record (d-store-03's third part). D013 covers new
   versions and events; no code covers a new record (layer S has S025 for bids only).
9. **Director**: d-store-10 (may a v1 store hold values naming an entity it redirected?) and d-store-13 (event
   fields before or after the capability check).

## Observations (not changed)

- `end_validity` numbers the next bid with `int()` on the digits of the held bids; a stored bid of more than 4,300
  digits, which layer C's `^b[1-9][0-9]*$` allows, would raise `ValueError` there.
- `fact_refines` computes `value_refines` for every pair of fillers of a role: about 40 s for 1,100 fillers. The
  recursive matcher computed the same pairs before it overflowed; caching each binding's canonical form and window
  would make it fast.
- The store copies records with `copy.deepcopy` (two frames a level), and `write_container`'s C check runs
  jsonschema, whose error messages recurse: in-memory records nested beyond about 490 levels still overflow there.
  Layer J's limit of 256 keeps parsed and validated input well inside.
- The nesting limit is per document: a `.khg.json` container holds its records two levels deeper than a `.khg.jsonl`
  line, so a record nested 255 or 256 levels is a valid JSONL line but makes the JSON layout J001.

## Checks

- Owned tests (`tests/c1`, `tests/store`, `tests/identity`): pass under Python 3.11 (dev venv), 3.10.20 and 3.13.12
  (the CI venvs with `PYTHONPATH=src`).
- `ruff` (F, E9, E501, W, B; py310; 120 columns) is clean on the owned files; `mypy` (py310) reports no error in
  them that it did not report at HEAD.
- Full suite, see the result at the end of the fixer's report.
