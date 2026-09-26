---
title: Role-aware HIF and the shared contracts
type: project
status: prototyping
started: 2026-09-23
depends_on: [kb/04-storage-and-formats/hif-hypergraph-interchange-format.md, kb/09-ecosystem/software-libraries.md, kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md, kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md, kb/03-construction/incremental-and-streaming-construction.md]
---

# Role-aware HIF and the shared contracts (P2)

Programme id **P2**, phase 0, kind **capability**. See [../PLAN.md](../PLAN.md).

## Question or goal

Make roles a first-class part of a hypergraph interchange file, and give every other project in the
programme the contracts it builds on:

- **C1** record format: nodes, hyperedges with roles, evidence, status lifecycle, relation-type
  schema language; a JSON Schema and a validator.
- **C2** store interface: put, get, incident hyperedges of a node, hyperedges by relation and key,
  supersession walk, export; one conformance test that every implementation passes.
- **C3** candidate queue record and linter action log.
- **C5** scorers: extraction, retrieval, memory, completion (question sets come from P3a).
- A `roles` convention on HIF incidence attributes, role-preserving loaders for XGI and HyperNetX,
  and a proposal to the HIF standard.

## Why it matters

Theme 2 of the [open-questions register](../../kb/00-index/open-questions.md): roles are the missing
primitive, and nothing in the stack carries them. Questions [09.5], [10.4], [04.1], [09.2] and, for
the record format, the fact-identity questions of Theme 4 that P7 consumes.

## Gate

A record round-trips repo format to HIF to XGI and HyperNetX and back with roles intact; the
validator rejects each malformed case in its test list; a smoke test runs one record through queue,
structural lint, store and export.

## Background from the KB

- [HIF](../../kb/04-storage-and-formats/hif-hypergraph-interchange-format.md)
- [Software libraries](../../kb/09-ecosystem/software-libraries.md)
- [Knowledge-hypergraph schema design](../../kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md)
- [N-ary relations and reification](../../kb/02-knowledge-representation/n-ary-relations-and-reification.md)
- [Temporal hyperedges and editable agent memory](../../kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md)
- [Incremental and streaming construction](../../kb/03-construction/incremental-and-streaming-construction.md)

## Plan

1. Research: requirements from the KB and the consumers, the HIF specification as published, the
   behaviour of XGI and HyperNetX on role attributes (probed, not assumed), prior art on roles,
   identity, lifecycle and evidence. Reports in [research/](research/).
2. Design: independent designs of the contracts, judged, synthesised into `DESIGN.md`, then
   critiqued adversarially and revised.
3. Implement: the package, the JSON Schema and validator with its malformed-case list, HIF export and
   import, XGI and HyperNetX loaders, a reference store with its conformance test, queue and linter,
   scorers, and the smoke test.
4. Review, run the gate, update the base, prepare the HIF proposal and the package release.

## Log

- 2026-09-23: started. Defaults agreed with the owner: MIT for code, CC BY 4.0 for prose; one shared
  package for all contracts (working name `khg-contracts`); work lands through pull requests.
- 2026-09-23: research done: five reports in [research/](research/). Neither library's own HIF reader or writer
  keeps roles intact (XGI drops them; HyperNetX drops a repeated pair and cannot re-read its own directed output).
  Loaders that build the library objects directly round-trip exactly and offline.
- 2026-09-23: design done: three independent designs ([research/designs/](research/designs/)), three judges
  (B, semantics-first, chosen as base), synthesis, a four-lens critique (8 blockers, 57 majors; 87 findings
  applied, 13 rejected with reasons) and revision into [DESIGN.md](DESIGN.md). Every example in
  [design-examples/](design-examples/) is generated and checked by the synthesis prototype; a rebuild on
  2026-09-23 was byte-identical and every check passed (G1 chain, hash-seed determinism, 180 malformed cases,
  114 store scenarios, smoke replay). Director's rulings on conformance, publishing and deprecation reasons are
  in DESIGN.md §14.
- 2026-09-23 to 2026-09-24: implementation. The package `khg-contracts` was built in eight staged steps (W0–W13)
  with an integration gate after each parallel stage; notes per step in [impl-notes/](impl-notes/).
- 2026-09-24: code review. Eight reviewers (one mutation-testing the gate), one adversarial verifier per
  reviewer, fixers with regression tests, integration: 54 findings confirmed by reproduction and fixed, 6 refuted,
  23 low ones triaged. Director's rulings 4–15 and the clarifications the review made normative are in DESIGN.md
  §14.
- 2026-09-24: **gate passed.** G1, G2 and G3 pass locally and in CI on GitHub (six jobs: Python 3.10, 3.11 gate,
  3.13, wheel, examples, evidence).
- 2026-09-26: ruling 19 (DESIGN §14; P1's Q5): a valid C1 container that is not complete now round-trips through HIF,
  XGI and HyperNetX, and G1 runs two more chains for it. `khg-hif` 1.1.0 for files that name entities or facts they do
  not hold; every other file is unchanged and stays 1.0.0. khg-contracts 1.0.0.dev1. Notes:
  [impl-notes/ruling-19.md](impl-notes/ruling-19.md).

## Results and findings

**Gate (PLAN §4): passed on 2026-09-24.**

| Clause | Test | Result |
|---|---|---|
| G1: a record round-trips repo format → HIF → XGI and HyperNetX → back with roles intact | `tests/gate/test_roundtrip.py` | The full fixture (59 incidence records, a node in two roles, a node that is both tail and head, ordered roles, literals, nesting) and its directed slice come back identical through C1 → HIF → XGI → HIF → HyperNetX → HIF → C1; every intermediate HIF equals the first; the same digests under five hash seeds |
| G2: the validator rejects each malformed case in its test list | `tests/gate/test_malformed.py` | All 180 cases of `data/malformed-cases.json` are rejected at their layer with their code, under both JSON Schema engines |
| G3: one record through queue, structural lint, store and export | `tests/gate/test_smoke.py` | Queue → lint → accept into `MemoryStore` → export as C1 and as HIF, both valid; replay reproduces the decision hash |

The whole suite: 5,876 tests pass on Python 3.11 with all extras; the core tests pass on 3.10 and 3.13; the
reference store passes all 114 conformance scenarios; `python -m khg_contracts.examples` rebuilds the 151 files of
[design-examples/](design-examples/) byte for byte.

**Findings.**
1. **Roles can travel in HIF today, without a schema change.** One incidence record per role binding, with the role
   in `attrs.role`, a repeated (edge, node) pair where a node holds two roles, and a declaration in `metadata`.
   Every file of the convention is valid against the published HIF schema (v0.1.0, blob e2105bb).
2. **Neither library's own HIF reader or writer keeps them.** XGI 0.10.2 drops every incidence attribute and
   weight; HyperNetX 2.4.3 drops the second record of a repeated pair, fetches its schema over the network on every
   call, returns `None` instead of raising, and cannot re-read its own directed output
   ([research/03](research/03-library-probes.md), `tests/evidence/library-hif-evidence.json`).
3. **Loaders that build the library objects through their public constructors keep them**, exactly, offline and
   deterministically, including a node that is both tail and head of one fact.
4. **The HIF standard has no version marker in data files and conflicting version labels**
   ([research/02](research/02-hif-standard.md)); P2 vendors v0.1.0 by hash and declares its profile in `metadata`.
5. **The contracts the programme builds on exist and are tested:** C1 (`khg-record/1.0.0`), the relation-type
   schema language, C2 (`khg-store/1.0.0`, 114 scenarios, capability flags), C3 (`khg-queue/1.0.0` with replay),
   C5 (`khg-scorers/1.0.0`) and the C4 draft (`khg-c4-items/0.1.0`) that P3a owns.

**Publication (PLAN §5): prepared, not yet shipped.** The owner releases it:
- `khg-contracts` 1.0.0 on PyPI: steps in [upstream/RELEASE.md](upstream/RELEASE.md) (the name is free on PyPI and
  TestPyPI, checked 2026-09-23);
- the HIF issue and, after the maintainers answer, the fixture PR: [upstream/hif-issue.md](upstream/hif-issue.md),
  [upstream/hif-fixture-pr.md](upstream/hif-fixture-pr.md);
- the XGI and HyperNetX issues: [upstream/xgi-issue.md](upstream/xgi-issue.md),
  [upstream/hypernetx-issue.md](upstream/hypernetx-issue.md);
- the post.

## Open questions raised

- Will the HIF maintainers accept repeated (edge, node) incidence records? The formal model calls incidences a set;
  the convention needs readers to keep repeats (DESIGN §12.3).
- Entity merges: v1 refuses a redirect while any record names the entity (ruling 10); rewriting is planned for 1.2.
- P3a must confirm the C4 defaults: the memory tolerance rule, the `missing` outcome, and the deprecation reasons
  that count as a revised value (rulings 3 and 8).
- P1 will measure what each backend loses; TypeDB 3.x can apply 70 of the 114 scenarios (DESIGN §14 ruling 1).
