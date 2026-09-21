---
title: hyper-base — a knowledge base whose structure is a knowledge hypergraph
type: project
status: idea
started: 2026-09-21
depends_on:
  - kb/02-knowledge-representation/knowledge-hypergraph-schema-design.md
  - kb/03-construction/llm-based-khg-construction.md
  - kb/03-construction/entity-resolution-and-canonicalisation.md
  - kb/07-applications/hierarchical-and-planned-hypergraph-retrieval.md
  - kb/07-applications/temporal-hyperedges-and-editable-agent-memory.md
  - kb/08-history-and-frontier/composed-stack-and-research-bets.md
---

# hyper-base

Lives in its own repository: **[pluton74mac/hyper-base](https://github.com/pluton74mac/hyper-base)**.

## Question or goal

Can a hypergraph-structured store, in which agents contribute facts through an extraction gate and a
linting agent applies supersession rules, fix the failure modes of a flat llm-wiki knowledge base
under iterative multi-agent research? First target: an EEG device spanning medicine, physiology,
physics and electronics, expressed as goal hyperedges with unbound roles.

## Why it matters

It is the first system built on this base. It implements layers B (living store), E (planner and
walker) and G (write-back) of the composed stack, and is candidate project P7 pointed at a research
base, with P2's role-aware HIF as export format.

## Background from the KB

The notes in `depends_on` above. The design document in the other repo cites them by path.

## Log

- 2026-09-21: spec v0 written here, then split into its own repository.

## Results and findings

Tracked in the other repository.
