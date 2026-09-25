---
title: Schema width survey
type: project
status: prototyping
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
- 2026-09-24: implemented [khg-width](khg-width/) (checker, fixtures, tests, solver build script), the survey
  scripts in [survey/](survey/), the HyperBench manifest and the CI job; the schema files are generated in
  [results/schemas/](results/schemas/). The survey has not run; its compute budget is the director's next call.
  Decisions and deviations: [IMPLEMENTATION-NOTES.md](IMPLEMENTATION-NOTES.md).
- 2026-09-24: the role naming agreed with P3a as [wd-roles r1](wd-roles.md) (three amendments from P3a).
- 2026-09-24: full survey run (15 rows; a 20-minute external-solver budget per row, bisection on k).
- 2026-09-25: one review round: every certificate re-validated by an independent validator, lower bounds
  reproduced, 4,000 random hypergraphs fuzzed against brute force; no wrong number; 9 findings (4 medium, 5 low)
  fixed with regression tests; the 8 affected rows re-run. **Gate met.**

## Results and findings

**Gate (PLAN §4): met on 2026-09-25.** The survey table is [results/survey.md](results/survey.md) (CSV, JSON,
per-row reports with certificates and lower-bound witnesses, figure). The checker `khg-width SCHEMA_FILE`
reports class and width for any `khg-relation-schema/1.0.0` file and flags every constructed cyclic fixture
(`khg-width/tests/`).

| Schema (core + qualifier roles) | Relations | Class | Core (relations) | hw |
|---|---|---|---|---|
| Wikidata, declared allowed-qualifier constraints, wd-roles r1 | 1,155 | α-cyclic | 391 | [4, 38] |
| Wikidata, observed (robust usage), wd-roles r1 | 13,608 | α-cyclic | 748 | [4, 68] |
| Wikidata, observed (all usage), wd-roles r1 | 13,608 | α-cyclic | 1,441 | [3, 61] |
| Wikidata, any of the above with relation-local roles (control) | | Berge-acyclic | 0 | 1 |
| Biolink Model v4.4.5 associations | 103 | α-cyclic | 5 | 2 (exact; ghw = fhw = 2) |
| HyperBench, 1,113 non-random conjunctive queries (baseline, selected to be cyclic) | | | | 1 / 2 / 3 for 673 / 432 / 8 |

**Findings.**
1. **Real knowledge-hypergraph schemas are cyclic once roles are global.** Every Wikidata schema is α-cyclic under
   every naming that shares roles across relations; only relation-local roles make it acyclic, and trivially.
   The acyclicity class therefore does not separate the variants; the width does.
2. **Wikidata's cyclic core is large and its width is at least 3–4.** The universal-join width of the qualifier
   schema is bounded, not settled: the cores are 391–1,446 relations, a size where exact hypertree width is known
   for only a few HyperBench instances. Every upper bound carries a validated decomposition; every lower bound a
   stored witness.
3. **Biolink's association schema is small and exactly width 2**, like most real conjunctive queries.
4. **The number is the width of joining all relations on same-named roles** (DESIGN §2): it bounds the cost of
   the universal join, not of arbitrary queries over the knowledge base.
5. **Declared qualifier lists overstate use** (P39 allows 104 qualifiers; 34 are used robustly), so the survey
   reports declared and observed schemas side by side.

The observed rows use SQID usage counts (dump of 2026-08-10) until P3a's exact counts from the 2026-09-22 dump
replace them; P3a's slice rows are added then (the survey scripts handle both, DESIGN §6.6).

**Publication (PLAN §5): not yet shipped.** The note (outline in DESIGN §8) and a Zenodo deposit of the raw
snapshot and schema files are prepared by the next session step and released by the owner.

## Open questions raised

- The exact hypertree width of the Wikidata cores (solvers decided no k within 20 minutes per row).
- Whether the universal-join width predicts the cost of real Wikidata queries; a query-log study would tell.
- How much of the measured structure is the naming: wd-roles r1 is one defensible choice among several.
