---
title: hyper-base — a knowledge base whose structure is a knowledge hypergraph
type: project
status: idea
started: 2026-09-21
depends_on:
  - kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md
  - kb/03-construction/llm-based-khg-construction.md
  - kb/03-construction/entity-resolution-and-canonicalisation.md
  - kb/03-construction/incremental-and-streaming-construction.md
  - kb/04-storage-and-formats/hif-hypergraph-interchange-format.md
  - kb/07-applications/hierarchical-and-planned-hypergraph-retrieval.md
  - kb/07-applications/ai-agents-memory-and-planning.md
  - kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md
  - kb/08-history-and-frontier/composed-stack-and-research-bets.md
---

# hyper-base

A knowledge base for research and design work in which **the hypergraph is the source of truth**.
Agents contribute facts, not pages. An extraction pass turns their evidence into candidate
hyperedges, a linting agent admits or rejects them under explicit supersession rules, and a walker
driven by a judgment model retrieves from the accepted graph. Human-readable notes are rendered
views of the graph, never the primary store.

This folder is written to become its own repository (`pluton74mac/hyper-base`). It is self-contained:
nothing in it is imported from the rest of this repo except by link. See
[Extracting to its own repo](#extracting-to-its-own-repo).

## Question or goal

Can a hypergraph-structured store fix the failure modes of a flat "llm-wiki" knowledge base under
iterative multi-agent research, specifically: unlinked pages, repeated facts, one new fact forcing
many page rewrites, and update cost that grows with base size instead of with the size of the change?

## Why it matters

The owner's earlier llm-wiki experiments for iterative research worked up to a size limit, then
degraded for exactly those reasons. The claim under test is that they are all symptoms of one
missing thing, an explicit record of which statements depend on which facts, and that a knowledge
hypergraph provides that record in its shape: retrieval becomes traversal, lint becomes pattern
matching on incidence structure, and update cost becomes local to the changed hyperedge's
neighbourhood.

## Background from the KB

- Schema decisions (roles, keys, provenance, time, confidence):
  `kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md`
- Why extraction is the weak link and must be gated:
  `kb/03-construction/llm-based-khg-construction.md`,
  `kb/03-construction/skill-driven-extraction-and-the-scenario-gap.md`
- Merging the same fact stated twice: `kb/03-construction/entity-resolution-and-canonicalisation.md`
- The two clocks and supersession: `kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md`
- Planned traversal beats naive expansion: `kb/07-applications/hierarchical-and-planned-hypergraph-retrieval.md`
- Where this sits in the frontier stack (layers B, E, G): `kb/08-history-and-frontier/composed-stack-and-research-bets.md`
- Related candidate projects: P7 (agent memory prototype) and P2 (role-aware HIF) in `projects/README.md`

## Documents

| File | What it is |
|---|---|
| [`docs/design.md`](docs/design.md) | The formalised design: model, pipeline, linter, walker, supersession, termination, evaluation, roadmap |
| [`docs/eeg-example.md`](docs/eeg-example.md) | First target: an EEG device spanning medicine, physiology, physics and electronics, worked as goal hyperedges |
| [`docs/decisions.md`](docs/decisions.md) | Decisions made so far and why |
| [`schema/relation-types.yaml`](schema/relation-types.yaml) | Relation types with roles and key roles for the EEG example |
| [`schema/hyperedge.schema.json`](schema/hyperedge.schema.json) | JSON Schema for one hyperedge record |
| [`examples/eeg/`](examples/eeg/) | Goal hyperedges and a few accepted hyperedges in the record format |

## Plan

1. M0 Spec (this folder): model, schema, linter rules v0, walker interface, EEG goal set. Done when the owner signs off.
2. M1 Store and lint: JSONL store, schema validation, structural lint, duplicate and conflict detection, review queue. No agents yet.
3. M2 Ingestion: research-agent brief format, extraction pass, candidate queue, linter with the v0 resolution policy.
4. M3 EEG run: four discipline agents plus one integrator, run until the termination criterion holds or the queue stalls. Measure.
5. M4 Walker: policy-over-traverser retrieval with a general LLM behind the judgment interface, then Jev behind the same interface. Compare.
6. M5 Views: render notes from the graph; compare against an llm-wiki baseline on the same corpus.

## Log

- 2026-09-21: idea formalised from conversation. Repo creation via the GitHub App failed (403), so the project starts here.

## Results and findings

None yet.

## Open questions raised

See `docs/design.md` §12.

## Extracting to its own repo

Once `pluton74mac/hyper-base` exists (empty, no README):

```
git subtree split --prefix=projects/hyper-base -b hyper-base-split
git push git@github.com:pluton74mac/hyper-base.git hyper-base-split:main
```

Then replace this folder with a one-paragraph pointer and keep the row in `projects/README.md`.
