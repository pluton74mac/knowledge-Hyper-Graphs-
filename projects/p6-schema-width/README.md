---
title: Schema width survey
type: project
status: exploring
started: 2026-09-24
depends_on: [kb/01-foundations/hypergraph-theory-results.md, kb/01-foundations/n-ary-relations-and-relational-algebra.md, kb/05-query-embeddings-reasoning/query-languages-for-hypergraphs.md, kb/02-knowledge-representation/wikidata-and-freebase-data-models.md, projects/p2-role-aware-hif/DESIGN.md]
---

# Schema width survey (P6)

Programme id **P6**, phase 1, kind **finding + tool**. See [../PLAN.md](../PLAN.md).

## Question or goal

Where do real knowledge-hypergraph schemas fall in Fagin's acyclicity hierarchy, and what is their
hypertree width? Measure it for the Wikidata qualifier schemas and for one biomedical schema, and ship a
checker that reports the acyclicity class and width of any relation-type schema file (P2's
`khg-relation-schema/1.0.0`).

## Why it matters

Question [01.3] of the [open-questions register](../../kb/00-index/open-questions.md) (Theme 5, bridges
between theories): nobody has measured where real KHG schemas sit in the acyclicity hierarchy or what their
hypertree width is, and that number predicts query cost directly. P11 consumes the checker.

## Gate (PLAN §4)

A survey table for the Wikidata qualifier schemas and the biomedical schema; the checker reports class and
width for a given schema file and flags a constructed cyclic case.

## Consumes

C1 from P2 (`khg-relation-schema/1.0.0`; `khg_contracts.schema.schema_hypergraph` and `is_alpha_acyclic`).

## Background from the KB

- [Hypergraph theory results](../../kb/01-foundations/hypergraph-theory-results.md)
- [N-ary relations and relational algebra](../../kb/01-foundations/n-ary-relations-and-relational-algebra.md)
- [Query languages for hypergraphs](../../kb/05-query-embeddings-reasoning/query-languages-for-hypergraphs.md)
- [Wikidata and Freebase data models](../../kb/02-knowledge-representation/wikidata-and-freebase-data-models.md)
- P2 [DESIGN.md](../p2-role-aware-hif/DESIGN.md) §3 (the schema language and how P6 parses it)

## Plan

1. Research: the theory and the available solvers (probed, not assumed); the data sources (Wikidata property
   constraints, a biomedical schema) and how their roles are named. Reports in [research/](research/).
2. Design: the checker, the survey protocol, and the role-naming variants the survey must compare. Agree the
   Wikidata role naming with P3a.
3. Implement the checker and the survey; run it; review once; update the base.

## Log

- 2026-09-24: started, while P3a runs on the owner's Mac. Pace set lower than P2's: fewer parallel designers
  and one review pass.

## Results and findings

## Open questions raised
