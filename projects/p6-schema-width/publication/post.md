---
title: "Post draft: how acyclic are knowledge-hypergraph schemas?"
type: project
status: draft
created: 2026-09-25
updated: 2026-09-25
---

<!-- OWNER: the post is yours to publish (PLAN §5). Before publishing: replace every number marked † after the
     P3a-count re-run and remove the marks; fill in the three links; delete this comment. About 380 words. -->

# How acyclic are knowledge-hypergraph schemas?

A schema for n-ary facts, the relation types and the roles each one uses, is itself a hypergraph: roles are the
vertices, relations the hyperedges. Database theory has a scale for such objects, Fagin's degrees of acyclicity, and
for the cyclic ones a measure of how far from acyclic they are, hypertree width. For a schema, the width is that of
one query: the join of every relation on its shared role names. This survey measures both on two real schemas.

**What was measured**

- Wikidata's qualifier schemas: the 1,155 properties that declare which qualifiers they allow, and the 13,608†
  properties in use with the qualifiers actually observed on them.
- The Biolink Model v4.4.5: 103 association classes and their qualifier slots.
- One published naming rule for Wikidata roles, and a control in which every role is private to its relation.

**What came out**

- Every schema whose role names are shared is cyclic. Only private role names make them acyclic, and then trivially.
  The acyclicity class says little here; the width says more.
- Biolink's association schema has hypertree width exactly 2, within the range of real conjunctive queries (99 % of
  HyperBench's non-random queries have width 2 or less).
- Wikidata's cyclic core has 391 to 1,446† relations. Its hypertree width is between 4 and 38 for the declared schema,
  and between 4 and 68† and between 3 and 61† for the observed ones. All 1,113 non-random queries in the HyperBench
  benchmark have width 3 or less.
- The exact Wikidata widths are open: two decomposition solvers did not settle them within 20 minutes per schema.

**What it does not say**

This is the width of joining all relations on shared role names. It is not the cost of ordinary queries over
Wikidata, which join facts on entities; HyperBench, quoting a study of Wikidata's query logs, reports widths of 1 and
2 only.

**Tools and data**

- The note, with the method and the limits: [LINK: arXiv]
- The checker, `khg-width` (MIT): the acyclicity class with a witness, and four widths, each exact or as bounds
  backed by a decomposition checked against the input: [LINK: repository]
- The Wikidata query snapshot, the generated schema files and every report: [LINK: Zenodo DOI]

† These numbers come from third-party usage counts and will be updated from exact counts over the 2026-09-22
Wikidata dump before this post goes out.
