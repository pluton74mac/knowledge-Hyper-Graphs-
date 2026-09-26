---
title: "P2 implementation notes: ruling 19, HIF and containers that are not complete"
type: project
status: draft
created: 2026-09-26
updated: 2026-09-26
---

# Ruling 19: HIF and containers that are not complete

The director's ruling on P1's fixes (2026-09-25, [P1 README](../../p1-store-bakeoff/README.md), point 2): a valid C1
container must round-trip through `to_hif`/`from_hif`. That is P2's gate G1, so the fix belongs to P2, with the
smallest change that needs no `khg-hif` major version, and the case joins G1's tests. The failing case is P1's Q5
([IMPLEMENTATION-NOTES](../../p1-store-bakeoff/IMPLEMENTATION-NOTES.md) §5 and §7): the HIF store could not load a
slice that is not `complete`.

- **Scope:** `src/khg_contracts/hif/`, `validate/layers/v.py`, `store/table.py`, `__init__.py`, `data/error-codes.json`
  and its manifest; `tests/hif`, `tests/gate`, `tests/store`, `tests/packaging`; P2's DESIGN, README,
  `upstream/RELEASE.md` and two mirrored files in `design-examples/`.
- **Not edited:** P1's folder. The one P1 test this changes is proposed as a patch (§6). `kb/` is the director's (§8).
- **Commits:** `e533e4c` (the change), `3f4ab8b` (G1), `ee94d5f` (DESIGN §14, README, release steps,
  `__module__`), and this note with the verification.

## 1. The failure, reproduced

C1 applies D002 only to a `complete` container (DESIGN §2.1), so a container without `complete: true` may name
entities and facts it does not hold. Two cases fail, not one:

| The container names, but does not hold | `to_hif` writes | `from_hif`, `validate_hif` | The loaders (`validate="profile"`) |
|---|---|---|---|
| an entity | its incidences, with the entity id as the node and no node record | D002 "node ... is not declared" | round-trip exactly |
| a fact, outside a slice | a `_:ref:` node with `khg-external: true` | P017 "external fact reference outside a slice" | refuse (P017) |

The first is P1's Q5. The second is the same failure for a fact value; P1 has not met it, because its test container
drops only `ex:Paris`. A P3a slice that keeps a lifecycle record or a nesting fact without its target would.

- A probe on the fixture without four entities (`complete: false`) gave 7 D002 findings, and 5 on its directed
  slice. Both files went through XGI and HyperNetX unchanged, with empty export reports: review fix F6
  ([review-fix-c](review-fix-c.md)) had already made the §4.2 order place an incidence on an undeclared node.
- W6 ([W6](W6.md), "Dangling references outside a slice") and the S4 integration ([integration-S4](integration-S4.md),
  48 mutants) recorded the gap; neither was ruled on.
- **Tests first.** Four tests in `tests/hif/test_from_hif.py` (an entity and a fact, `complete` absent and `false`)
  failed before the change and pass after it.

## 2. Options considered

| | Option | What changes | Why not, or why |
|---|---|---|---|
| **A** | **Read what `to_hif` already writes** (chosen) | decoding and one P check; the stamp | HIF itself allows a node that only incidences name ([R02 §5 case 28](../research/02-hif-standard.md); upstream data does it). The writer's records do not change, the loaders need nothing, and the file carries no invented record for something the container does not describe |
| B | Declare the entity: `{node, attrs: {khg-kind: "entity", khg-external: true}}`, as for facts | the writer, a new attribute, decoding (no entity record for it), the P checks | The same reader change as A, plus a writer change and a node record whose only content is a marker. Symmetric with facts, but larger |
| C | Stub entity records in the file | the writer | Not a round trip: `from_hif` would return entity records the container did not have. P1's build ruling Q4 refused stubs as emulation |
| D | A P1 skip rule (a HIF loss) | P1 only | Ruled out: G1 belongs to P2 |
| E | Refuse at export (D002 in `to_hif`, W6's "stricter reading") | the writer | A valid container would have no HIF form at all |
| F | Fix it inside `khg-hif/1.0.0` as an erratum (unreleased) | the reader only, no version | P1 measured and recorded `khg-hif/1.0.0` with the refusal, which §4.3 specified and the G2 list tests (MC055, MC058). A reader that accepts files the 1.0 rules refuse is the "optional addition" of §11.2, a minor version |

**The fact case is included** (my decision, D1 in the report). It is the same principle, one condition, and a P3a
slice can meet it; leaving it would need a second ruling.

**Why a minor version, and why it is cheap.** The profile's rules change: P017 is a P check, and D002 on an
undeclared node is a decoding refusal of §4.3. A 1.0 reader refuses the new files. §11.2 answers both points: a minor
version for an addition that makes new documents valid, and writers stamp the lowest version whose features a
document uses. So only a file that uses the addition is stamped `khg-hif/1.1.0`, and a 1.0 reader refuses it with
V001 instead of reporting a broken file (D002). Every other file keeps `khg-hif/1.0.0` and its bytes. The fixture,
the slice, the migrated sample, the packaged data, the golden digests of G1's first two chains and every conformance
scenario are unchanged. The profile schema is unchanged too, so its `$id` keeps `khg-hif/1.0.0`.

## 3. The change

- **The rule, once** (`hif.profile.external_allowed(metadata)`): a file may name entities and facts it does not hold
  when `khg-complete` is not `true`, or when it is a slice. "Or a slice" keeps every file 1.0.0 accepted: 1.0.0
  allowed an external reference in any slice, and `to_hif` writes every slice with `khg-complete: false`.
- **Decoding** (`hif.decode`): in such a file an incidence on a node without a record, whose id lacks the `_:` prefix,
  is the entity of that id. It gets no entity record. Refused as before:
  - an undeclared node in a complete file (D002, MC058);
  - an undeclared derived `_:` node in any file (D002): `to_hif` declares every derived node;
  - an unresolved fact reference that is not marked `khg-external` (D002).
- **P017** (`hif.checks`): an external reference in a complete file that is not a slice, or to a fact the file holds.
  It was: outside a slice, or to a fact the file holds.
- **Writing** (`hif.encode._stamp`): the same records; the stamp is `khg-hif/1.1.0` when an incidence names a node
  without a record, or when a file that is not a slice holds an external reference. Otherwise `khg-hif/1.0.0`.
- **Layer V** reads `khg-hif/1.0.x` and `1.1.x`; `1.2.0` is V001 (MC010's `1.9.0` still is). The reader reads every
  accepted file by the 1.1 rules. It does not enforce the stamp: stamps tell older readers what they cannot read.
  The loaders pass the loaded metadata through, and an older `to_hif` stamped these files 1.0.0; a stamp-strict reader
  would refuse both. `hif` exports `PROFILE_1_1` and `external_allowed`.
- **Versions.** `CONTRACTS["khg-hif"]` is `1.1.0`. khg-contracts goes from `1.0.0.dev0` to `1.0.0.dev1`. 1.0.0 is not
  released, so its first release includes this; the new dev number lets P1's provenance (version and commit) tell the
  builds apart. `khg-bakeoff` and `khg-width` pin `>=1.0.0.dev0,<2`, which `1.0.0.dev1` meets.
- **The registry.** The meanings of D002, P017 and layer P say the new rule; the codes are unchanged
  ("messages are not part of the contract"). The manifest and `design-examples/error-codes.json` are regenerated.
- **Also, from P1's deferred items** (§7): `Entry`, `VersionTable` and `bound_nodes` carry `khg_contracts.store.table`
  in `__module__`.

## 4. G1 and the tests

- **G1 runs four chains** (`tests/gate/g1_chain.py`, `chain_inputs`): the fixture and its directed slice, and the
  fixture as a container that is not complete, and that container's directed slice. That container lacks four records
  its facts name, and `complete`:
  - `ex:TP53`: tail and head of `f:reg-1`, a repeated pair, with a weight of 3;
  - `ex:YYZ`: stops 1 and 3 of the ordered `f:route-1`, and both ends of `f:loop-yyz`;
  - `ex:KingOfFrance`: the position of two facts and of the goal;
  - `f:born-louis14-paris`, which `f:claim-1` names, so its reference is external outside a slice.
- **Every G1 assertion runs on all four chains.** Assertion 1 compares the new chains' first HIF with the complete
  counterpart's packaged file, record for record: it is that file minus what the container does not hold, with the
  one reference external and the stamp 1.1.0. The XGI object holds each undeclared node as a member without
  attributes, and the HyperNetX cell of (`f:reg-1`, `ex:TP53`) keeps the second record under `khg-extra-incidences`.
- **Golden digests.** The two new chains are `sha256:e17e08f4…aadd` (not complete) and `sha256:fb12d840…2867` (its
  slice); their HIF is the same document at every step. The first two chains' digests are unchanged.
- **Unit tests** (`tests/hif/test_from_hif.py`, `tests/store/test_table.py`):
  - the stamp: 1.1.0 only when a file uses the addition, for a slice as well;
  - the refusals that stay (D002 in a complete file and for an undeclared `_:` node, P017 in a complete file, an
    unmarked unresolved reference);
  - the version gate: 1.0.x and 1.1.x are read alike, 1.2.0 and 2.0.0 are V001;
  - `__module__`.
- **Against the old code.** With the sources of `26ef293` first on `PYTHONPATH`, the new G1 chains error in their
  fixture (D002, P017), 40 tests; both digest tests fail; the four reproductions fail. The first two chains pass.

## 5. Verification (2026-09-26, the CI jobs of `.github/workflows/ci.yml`, run here)

| Job | How | Result |
|---|---|---|
| core-3.10 | fresh venv, Python 3.10.20, `.[dev]`, `pytest -q` | 5,563 passed, 21 skipped |
| gate-3.11 | the dev venv, Python 3.11.15, `.[xgi,hnx,fast,dev]`, `pytest -q -m "not evidence"` | 5,956 passed, 1 skipped, 5 deselected (5,908 before: +48) |
| core-3.13 | fresh venv, Python 3.13, `.[dev]`, `pytest -q` | 5,563 passed, 21 skipped |
| wheel | `python -m build`; the wheel in a clean 3.11 venv; `khg_contracts.data --check`; `khg-validate` on the packaged fixture; `khg-conformance --factory khg_contracts.store:memory_factory` | builds `1.0.0.dev1`; data check ok; valid (0 errors, the 2 designed warnings); 114 of 114 passed, EARL `hasVersion` 1.0.0.dev1 |
| examples | `python -m khg_contracts.examples out/ --tests tests`, `diff -r` with `design-examples/` | byte-identical (151 files) |
| evidence | `pytest -q -m evidence` | 5 passed; `library-hif-evidence.json` unchanged |
| khg-width | fresh venv, Python 3.10, `. ./projects/p6-schema-width/khg-width[dev]` | (running when this note was first committed; see the next commit) |
| khg-bakeoff | fresh venv, Python 3.10, `. ./projects/p1-store-bakeoff/khg-bakeoff[oxigraph,postgres,dev]`; the import step; `pytest -q` | (running when this note was first committed; see the next commit) |

- **Lint.** ruff (F, E9, E501, W, B at 120 columns, py310) finds nothing new in the changed files. The one E501 in
  `store/table.py` is a docstring table row that was there before.

## 6. P1's test that pinned the refusal

`khg-bakeoff/tests/test_loads.py::test_the_hif_store_cannot_load_a_container_that_is_not_complete` asserted D002. The
load now succeeds, so the test fails, and the khg-bakeoff CI job with it, until P1 changes it. It is P1's file, so
this branch does not touch it. The replacement is [ruling-19-p1-test.patch](ruling-19-p1-test.patch) (`git apply`
from the repository root):

- `test_the_hif_store_loads_a_container_that_is_not_complete` loads the same slice with nothing skipped (39 records);
- the file is stamped 1.1.0, names `ex:Paris` only in an incidence, and exports what `MemoryStore` exports;
- `incident("ex:Paris")` gives the reference's answer.

With the patch applied to a copy of P1's folder, the khg-bakeoff tests pass (§5). P1's README and IMPLEMENTATION-NOTES
also say the HIF row "is not run on such a slice" and describe finding 8 as open; those lines are P1's to update.

## 7. P1's deferred items that touch khg-contracts (proposal)

The director deferred two to P1's second half (P1 README, the rulings on the fixes, item 5; P1 IMPLEMENTATION-NOTES
§8, "Checked, and not changed").

- **`Entry.__module__`: done here.** It was trivial and P2's. `Entry`, `VersionTable` and `bound_nodes` are defined
  in the private `store._table` and published by `store.table`; their `__module__` is now the public module. Only
  reprs and docs change (pickling finds them there too); `MemoryStore` behaves as before, and a test checks it.
- **Public read-check helpers: proposed, not built.** `khg_bakeoff.native.NativeReads` copies four checks, in the same
  order: `_page(limit, after)`, `_need_where`, and the incident and find argument checks (`_check_incident`,
  `_check_find`). They are private in `TableStore` (`memory._page`, `TableStore._need_where`, `_patterns`, and the
  inline checks of `incident`, `degree`, `find` and `find_by_key`). Today conformance and P1's random parity test hold
  the copies equal.
  - **Proposal:** an addition to ruling 17, still outside C2, in 1.0.0.dev2. Publish `TableStore.check_incident(node,
    role, relation, where, limit, after) -> Where` and `TableStore.check_find(relation, pattern, match, where, limit,
    after) -> (patterns, Where)`, which raise exactly what the reads raise now, in their order. `TableStore`'s reads
    call them, and `NativeReads` drops its copies.
  - **Cost:** about 60 lines and their tests. Review 01's differential check must be re-run on `MemoryStore`, since
    the reads' check order is observable.
  - **When:** at the start of P1's second half, if P1 wants to delete the copies. It is not needed for correctness.
- **Rolling the clock back on a failed write** is documented as out of scope (ruling 17's addition), and no scenario
  depends on it; nothing here.

## 8. For the director's base update

- [kb/04-storage-and-formats/hif-hypergraph-interchange-format.md](../../../kb/04-storage-and-formats/hif-hypergraph-interchange-format.md)
  names the profile `khg-hif/1.0.0` (the paragraph on the repository's own files). Proposed addition: "1.1.0 (P2
  ruling 19, 2026-09-26) lets a file that is not complete name entities it does not hold, as incidence nodes without
  a node record, which HIF allows, and facts it does not hold, as external references."
- PLAN §9 lists no `khg-hif` version, and C1 and C2 are unchanged, so no row changes. P1 records the new versions
  through its provenance when it regenerates results.
