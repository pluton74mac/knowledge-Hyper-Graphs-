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
d-store-01 to d-store-07, seven of the nine LOW ones (d-store-09 in part), the director's ruling 4 (DESIGN §14), and
group b's two requests. Nothing in DESIGN.md, `design-examples/`, `data/` or another group's files was edited, and
nothing was committed.

The work was done in two passes. The first pass was interrupted by a usage limit, and the orchestrator's checkpoint
commit 40eab24 holds its edits. The second pass reviewed every edit against the findings, the verifiers' fixes and
DESIGN, re-ran every check below, and added one order test (d-store-06). "Before" means the commit before the review
round, f99a8af.

**How each regression test was checked.** The owned tests ran on a scratch copy of the working tree in which only
this group's 16 changed source files were put back to f99a8af. Other groups' files were left as they are, and the
shared working tree was not touched. There, 57 tests fail, and on the working tree all of them pass. These are the
new or changed tests of every code fix, the ruling and group b's requests. The new tests that pass on the old code do
so by design:
- `test_injective_match_agrees_with_brute_force` is a property check of the new matcher.
- `test_the_largest_years_have_windows_whose_bounds_are_instants` and the 17-digit instant case guard the new year
  bound.
- `test_a_container_with_an_overlong_year_gets_findings_not_an_exception` already passes, because group b's layer S
  turns the old `ValueError` into S006.
- The d-store-06 and d-store-07 tests are test-only findings. Seven mutations of the store show that they catch
  what they are meant to catch (see those rows).

## Ruling 4: container suffixes

- **Reading and writing.** `record.read_container` and `record.write_container` dispatch on the suffix only
  (`record.container.SUFFIXES`). `.json` is one JSON document, `.jsonl` is JSONL, and any other suffix is
  `ValueError`, raised before the file is read or anything is written. The match is case-sensitive, so `.JSON` is
  refused too.
- **`format=`.** `write_container(format=...)` may restate the suffix's layout. A `format` that the suffix does
  not name, or an unknown one, is `ValueError`. With `format=None` the suffix decides, as W3 decided. The old rules,
  that an explicit `format` wins and that every name but `.json` is written as JSONL, are gone.
- **The store.** `MemoryStore.load` of a path reads `.jsonl` through `iter_jsonl` and anything else through
  `read_container`, so a path with another suffix is `ValueError` there too.

Tests: in `tests/c1/test_container.py`, `test_formats_and_suffixes` (rewritten), and the write and read refusals
(eight names for writing and four for reading; the suffix is checked before V and C, and nothing is written). Also
`tests/store/test_load.py::test_load_reads_paths`. The CLI part ("the CLI exits 2") is the CLI's; see request 1.

## Confirmed findings

| Finding | Change | Tests |
|---|---|---|
| a-record-1: an omitted `supports` had three defaults | One rule, §2.8.1's: evidence carried without `supports` supports what it resolved to in the **first version that carries it**, that is, that version's list, else every bid of that version. `normalize`'s default (every bid) now applies only to evidence that a record carries first. Two new helpers in `canonical.py` write the lists out: `record.carried_supports(versions)` and `record.resolve_supports(records)`. They are called in five places. `canonical_container` calls them for `content: history`, and `lifecycle.history_problems` before the pairwise version rule. `MemoryStore.put` fills a new version's omitted lists from the stored version (`_carried`). `MemoryStore.load` does so over the loaded versions of each id, after the version the store holds (`_carry_loaded`). `compare_containers` does so for history containers | `test_canonical.py`: the fixture's history with e1's `supports` dropped canonicalises to the fixture; the helper's rules. `test_container.py`: writing and reading in both layouts gives the fixture, which validates, with the same `supported_values`. `test_lifecycle.py`: the history rule. `test_compare.py`. `test_load.py`: a history load, and a later snapshot load of v2. `test_memory_store.py`: put v1, then v2 without `supports`, is accepted; e1 keeps b1-b3, and a second put is a no-op |
| a-record-2: an integer literal of more than 4300 digits was a plain `ValueError` | `jsonio._int` counts the digits first; 17 or more is J006 (JSON has no leading zeros). `jsonio.number` names a huge int by its bit length, since `str()` of it is itself a `ValueError` | `test_jsonio.py`: 17, 4301 and -5001 digits for `loads` and `loads_lines`; `canonical({"x": 10**5000})`; `validate(bytes)` gives J006 and does not raise |
| a-record-3: a year of more than 4300 digits was a plain `ValueError` | `windows`: a literal's year has 4 to 16 digits (`YEAR_DIGITS`, Wikibase's own bound), and C004 is raised beyond that. An instant's year has 4 to 17 digits (`INSTANT_YEAR_DIGITS`), and C011 is raised beyond that; the upper window bound of the largest literal year is an instant too. `values._YEAR` has the same bound. Messages shorten the text | `test_windows.py`: 17, 4301 and 5000 digits through `window`, `value_identity`, `canonical_value`, `parse_time` and `normalize`; instants and `store.Where(as_of=...)`; the largest years have windows whose bounds parse; `validate_container` gives findings (C004 or S006, whichever layer S reports) instead of raising |
| a-record-4: the depth limit depended on the Python version, and the record walkers overflowed below it | `jsonio.MAX_DEPTH = 256`. `loads` and `loads_lines` give J001 "nesting deeper than 256 levels" at the first value that is too deep. That is the path and message that layer J gives for an object in memory; group b set the same limit there. A bracket count skips the walk for shallow texts, which a JSONL record line usually is. `jsonio.canonical` and `record._common.nfc_deep` keep their recursive fast path and fall back to iterative walkers on `RecursionError`, with the same output. A differential check agrees on 20,000 random documents, errors included. A container that holds itself is `ValueError` | `test_jsonio.py`: the limit and the path; JSONL lines one by one; wide documents; any depth written; a cycle. `test_canonical.py`: normalise 3,000 levels; the two walkers agree; a cycle. `test_container.py`: a container at the limit round-trips in both layouts, and one level deeper is J001; the canonical text and hash of a 1,500-level container. Group b's `tests/validate/test_nesting.py` loads a container at the limit into the store |
| a-record-5: the inverses merged the versions of a history | `rdf_relation_instance` is `ValueError` when a fact id comes twice: the projection has one IRI per fact, and §6.5 needs named graphs per version. `from_incidence_rows` is `ValueError` for rows of several versions of a fact, for rows of one fact that disagree on relation or status, and for a bid given twice. `from_rdf_relation_instance` is `ValueError` for two values of one predicate on a fact or a binding; the same triple twice counts once | `test_project.py`: both refuse the history fixture; its snapshot round-trips through both, with f:reg-1 retracted; disagreeing rows and triples |
| a-record-6: the matcher recursed once per augmenting-path step | `injective_match` keeps its own stack, after a greedy first pass in which each row takes its first free column. It gives the same answers as the recursive search on 5,000 random graphs of up to 25 x 25, and the same as brute force on 400. The all-true 1,500 x 1,500 case takes 0.2 s | `test_refine.py`: staircases of 1,500 rows (true and false); all-true; a 300-row staircase under a recursion limit 60 frames above the caller; `fact_refines` on a 100-reading staircase under a limit 50 frames above it. `test_memory_store.py`: `find` with 150 `any` patterns under a limit 60 frames above the caller |
| d-store-01: S-LIFE-013's history export failed D014 | `lifecycle.COMPOSITE_STEPS = {("superseded", "disputed")}`: between consecutive versions of a fact in a history, that pair is accepted, and the version rule still judges the content. It is the one step that an undo resolved by a dispute writes in one version (§2.7, S-LIFE-013). `TRANSITIONS` is unchanged, so an event still may not dispute a superseded fact (D014) | `test_lifecycle.py`: the Kraków history of v1 asserted, v2 superseded and v3 disputed; `transition_problem` is still D014, and so is another status after superseded. `test_conformance.py::test_every_write_the_scenarios_make_leaves_valid_exports`: after every accepted put, apply or load of the `when` steps of the 114 scenarios, the snapshot and history exports validate. Before the fix, S-LIFE-013 step 2 failed |
| d-store-02: `put` could re-point a disputed fact's `status_ref` | `lifecycle.put_problem`: a `status_ref` other than the current version's is D014, because it is on the belief axis, which only events move. §6.2 puts D014 before record validation, so a new version that drops a disputed fact's `status_ref`, or gives an asserted fact one, is now D014 rather than C006. A new id is judged as before | `test_memory_store.py`: `m:nothing`, a fact id and a dropped pointer are D014, and the store stays at version 2; an unchanged put is a no-op; an editable field still changes; an asserted fact cannot gain a pointer |
| d-store-03: a put or event could give a held evidence id a second record | `lifecycle._evidence_problems` compares the n-th record of an id in the old version with the n-th in the new one. It gives D013 when a new version has more records under an id than the old one, so a legacy duplicate that is kept as it is passes. `_events._append_evidence` gives D013 for an id that the fact holds or that the event gives twice | `test_events.py`: the forged e1 in either order; e1 twice; `add_evidence` with e9 twice. `test_lifecycle.py` |
| d-store-04: undoing two supersessions that share a superseding fact was D001 | `_events._retract` collects each superseding fact once, and skips one that is itself a target | `test_events.py`, for `retract` and `dispute`: the receipt, the status, the lifecycle record binds each fact once, and both exports validate |
| d-store-05: an unhashable evidence id was a `TypeError` | `_append_evidence` looks for clashes among string ids only. Any other id goes on to layer C (C010) | `test_events.py`: a list and an object id (a `TypeError` before), and a number and null (C010 before too), on `add_evidence`, on `transition` to asserted and on `end_validity` |
| d-store-06: the §6.2 check order was untested | Tests only | `test_memory_store.py` has six pair tests: D016 before D018; D008 before D016; D016 before a put's D011 (S-LIFE-014's version plus a born_in collision); D016 before a supersede event's own D011 (added in the second pass); capability before `NotFound` (supersede, dispute, retract, end_validity); D014 and D017 before record validation. Six mutations of the order are each caught by at least one test: `_write_time` first; keys before nesting; supersession constraints before keys; the event's D011 before keys; `NotFound` before capability in `supersede`; record validation before the status rules in `put` |
| d-store-07: the walk's "always ends" was untested | Tests only | `test_base.py`: a supersession cycle that a trusted load keeps (the walk ends in both directions, with terminal `[]`), and a diamond (D is reached twice but walked and listed once). With the review's mutation, the first test hits its 10 s alarm and the second lists D twice |

## LOW findings

| Finding | Outcome |
|---|---|
| a-record-7: a width of 0 dropped a role's fillers silently | Applied. `position_map` requires a width that is a positive integer (`ValueError` otherwise). Tested in `test_project.py` with 0, -1, `True`, 2.5 and `"4"` |
| a-record-8: a lone surrogate made `write_container` and `container_sha256` raise `UnicodeEncodeError` | Applied. Both give `ValidationError` J005, as `jsonio.digest` does, before any file is made; the file is now written as bytes. Tested in `test_container.py` |
| d-store-08: restating the end cause while refining the end was S004/S014 | Applied. `end_validity` reuses the fact's `khg:end_cause` binding, since the usage has max 1. An equal cause adds nothing, and the evidence then supports the end only (§2.8.1: "if one is written"). Another cause replaces the value, and the version rule judges it (D013 unless it refines). Tested in `test_events.py` |
| d-store-09: writes after a trusted load were blamed for a violation that was already there | Applied in part. A violation after the write counts as new only when its facts are not all part of one violation of the same key before it; W8's rule compared exact id tuples. So retracting or deprecating one of three normal facts on a key is accepted. Not changed: a new version of a fact that stays asserted in the violation (`add_evidence`) is still refused, because `keys.collisions` blames an incoming asserted fact that takes part (W5's rule). Changing that is a policy decision. Tested in `test_memory_store.py` |
| d-store-10: a redirect write left values naming the redirected entity (D020) | Not applied: it is a design decision. W8 accepts facts that keep a value written before its entity gained `redirect_to`, so it presumes that stores hold such values. Refusing the redirect instead would make a merge impossible while any fact names the entity, and v1 has no rewriting (§2.2). See request 8 |
| d-store-11: `Timed` sorted set members by their canonical text | Applied. A set of strings is sorted as strings (§6.3: "frozensets as sorted lists"), as `Where.as_dict` does. Mixed members keep the canonical-text order. Tested in `test_timed.py` |
| d-store-12: a declared flag beyond the ten crashed `conformance.run` | Applied. The runner tests the declared flags that are among the ten. The report's subject still lists every declared flag, and `tested_capabilities` lists the ones tested. A caller's own `capabilities=` list is still checked. Tested in `test_conformance.py` |
| d-store-13: event fields are checked before the capability | Not applied. §6.2's order is for the checks of a write. An event whose own fields are malformed is refused before any of them, just as `put` refuses a malformed `actor` or `at` first. Changing this would mean reordering four handlers for a case that no scenario has. See request 8 |
| d-store-14: reads raised `TypeError` on a loaded record with a list status, rank or visibility | Applied. `MemoryStore._passes` lets no filter pass a record whose status, rank, visibility or relation is not a string, which is what `_table` promises for malformed records. Tested in `test_load.py` |

## Group b's requests and other follow-ons

- **Integral float versions** (group b's request; F10). `record_sort_key`, `resolve_supports` and
  `lifecycle.history_problems` read a version `2.0` as 2. So the canonical order, the first carrier of a piece of
  evidence and the history rules agree with the canonical text, which writes `2`. A version such as 1.5 is still
  D001. Tests are in `test_canonical.py` and `test_lifecycle.py`
  (`test_history_versions_that_are_integral_floats_are_their_integers` fails on the old code).
- **`jsonio.MAX_DEPTH`** (group b's request) is 256, equal to `schema.checks.MAX_DEPTH`, and has the same meaning:
  the root is level 1, and J001 is at the first value deeper than 256 levels. `tests/validate/test_nesting.py`
  asserts that the two are equal, and it passes.
- **New public names beside §10.2's:** `jsonio.MAX_DEPTH`, `record.carried_supports`, `record.resolve_supports`,
  `record.windows.YEAR_DIGITS`, `record.windows.INSTANT_YEAR_DIGITS`, `record.container.SUFFIXES` and
  `record.lifecycle.COMPOSITE_STEPS`.
- **W5's evidence rule.** W5 compared evidence across versions with `supports` defaulting to the old version's
  bids. That default now applies only when both lists are omitted in a direct call of `version_problems`. The
  history rule, `put` and `load` resolve omissions to the first carrier's list first.

## Requests to other groups

1. **CLI** (`cli.py`, `tests/cli/`, group ex). Ruling 4 says that the CLI exits 2 for another suffix, but
   `record.read_container` now raises a plain `ValueError` for one:
   - `_argument` (the `--base` files) and `_convert` (reading IN) catch only `OSError` and `ValidationError`, so
     `khg-validate P --base x.txt` and `khg-convert x.txt OUT` end in a traceback. They should exit 2.
   - `khg-convert IN out.txt --to khg-json` and `khg-migrate IN out.txt` write a JSON container under another
     suffix, which `read_container` refuses. They should exit 2 too (`_check_convert_options` checks `.jsonl`
     only).
   - A CLI test for a 5,000-digit integer can now expect `khg-validate` to print a J006 finding and exit 1 (the
     verifier of a-record-2 asked for one).
2. **DESIGN §2.7 and the meaning of D014** (DESIGN owner; `data/error-codes.json` is group b's). Say that a history
   may go from superseded to disputed in one version, which is the step an undo resolved by a dispute writes
   (S-LIFE-013). An event still may not.
3. **DESIGN §2.8.1.** Say that evidence carried without `supports` keeps the list of the first version that carries
   it. The canonical writer, the version rule, `put` and `load` now read it that way.
4. **DESIGN §10.2 and §2.10.**
   - `write_container` and `container_sha256` also raise J005 (for a lone surrogate in a container built in
     memory).
   - The J001 of `jsonio.loads` includes the nesting limit of 256 levels.
   - The projection inverses take one version per fact (`ValueError` otherwise).
   - A width is a positive integer.
   - A put that moves `status_ref` is D014 (§6.2).
5. **Record schema** (group b: `data/schemas/khg-record-1.0.0.schema.json`, `schema/codegen.py`, the manifest,
   `design-examples/`). Bound the year of the time pattern to 16 digits and that of the instant pattern to 17
   (`[0-9]{4,16}`, `[0-9]{4,17}`). Layer C then reports C004 and C011 where the S step reports them now. Group b
   left this for a request from this group.
6. **Validator** (group b, `validate/runner.py`). The `run` docstring lists the errors that arguments raise. A
   `bases` path with a suffix other than `.json` or `.jsonl` now raises `ValueError` from `read_container`, which
   fits "an unknown kind ... is ValueError", but the docstring does not list it.
7. **Registry.** Add a code for evidence ids given twice in a brand-new record (d-store-03's third part). D013
   covers new versions and events, but no code covers a new record; layer S has S025 for bids only.
8. **Director.** Two questions: may a v1 store hold values that name an entity it redirected (d-store-10)? Are
   event fields checked before or after the capability (d-store-13)?

## Observations (not changed)

- **Huge bids.** `end_validity` numbers the next bid with `int()` on the digits of the held bids. A stored bid of
  more than 4,300 digits, which layer C's `^b[1-9][0-9]*$` allows, would raise `ValueError` there.
- **Slow refinement.** `fact_refines` computes `value_refines` for every pair of fillers of a role, which takes
  about 40 s for 1,100 fillers. The recursive matcher computed the same pairs before it overflowed. Caching each
  binding's canonical form and window would make it fast.
- **Deep objects in memory.** `put` and a trusted `load` do not apply layer J, so they accept an object built in
  memory that nests deeper than J's 256 levels (measured up to 1,500). But the reads and exports copy records with
  `copy.deepcopy`, which uses two frames a level. On Python 3.11, `get` and `export` of such a record raise
  `RecursionError` from about 500 levels on (490 works, 600 does not). `write_container`'s C check runs jsonschema,
  which overflows near 1,000 levels. Parsed and validated input stays within 256 levels. A later change could have
  `put` check J's limit (J001) or copy records iteratively.
- **The limit is per document.** A `.khg.json` container holds its records two levels deeper than a `.khg.jsonl`
  line does. A record nested 255 or 256 levels deep is therefore a valid JSONL line, but it makes the JSON layout
  J001.

## Checks

- **Owned tests** (`tests/c1`, `tests/identity`, `tests/store`): 1,115 pass under Python 3.11 (the dev venv), 3.10.20
  and 3.13.12 (the CI venvs, with `PYTHONPATH=src`).
- **Lint and types.** `ruff` (F, E9, E501, W, B; py310; 120 columns) is clean on the owned files. `mypy` (py310)
  reports no error in them that it did not report at f99a8af, and two fewer.
- **Differential checks.** Two checks ran in the second pass:
  - `jsonio._write` against `_write_deep`, and `_nfc_deep` against `_nfc_deep_iterative`, on 20,000 random
    documents, errors included;
  - `injective_match` against the recursive matcher on 5,000 random graphs.
- **Full suite** (the working tree, which includes group c's work in progress): 3 failed, 5,751 passed, 1 skipped.
  The three failures are not this group's, and they fail in the same way when this group's source files are at
  f99a8af:
  - `tests/cli/test_validate.py::test_doc_texts_feed_the_span_check` (b-validate-10, a CLI test to update);
  - `tests/scorers/test_memory_layer_i.py::test_the_draft_names_i001_i002_and_i004` (ruling 7, a scorers test to
    update);
  - `tests/consumers/test_verbatim.py::test_the_copy_is_verbatim[P7]` (it already fails at f99a8af).
