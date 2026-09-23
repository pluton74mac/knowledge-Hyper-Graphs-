---
title: Role-aware HIF and the shared contracts
type: project
status: exploring
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

## Results and findings

## Open questions raised
