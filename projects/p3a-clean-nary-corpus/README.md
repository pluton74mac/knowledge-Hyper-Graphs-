---
title: Clean n-ary corpus (P3a)
type: project
status: exploring
started: 2026-09-24
depends_on: [kb/02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md, kb/05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md]
---

# Clean n-ary corpus (P3a)

Programme id **P3a**, phase 0, kind **capability (data)**. See [../PLAN.md](../PLAN.md).

## Question or goal

"Clean n-ary corpus: leak-checked, deduplicated, arity-stratified split from recent Wikidata, with roles and with
question sets for retrieval and memory" ([PLAN §3](../PLAN.md)).

## Gate

"Corpus released with leak-check report, deduplication report, arity histogram, fixed split, question sets"
([PLAN §4](../PLAN.md)).

## Why it matters

P3a hands over contract C4 (gold facts, split, question sets), which P1, P3b, P4, P5, P7, P8, P9 and P10 consume
([PLAN §3, §7](../PLAN.md)); it serves Theme 3 of the
[open-questions register](../../kb/00-index/open-questions.md).

## Background from the KB

- [Benchmarks derived from Freebase and Wikidata](../../kb/02-knowledge-representation/benchmarks-derived-from-freebase-and-wikidata.md)
- [Benchmarks and evaluation protocols](../../kb/05-query-embeddings-reasoning/benchmarks-and-evaluation-protocols.md)

## Plan

The corpus design is not written yet. So far this folder holds only [slice/](slice/), the dump-cutting step: one
streaming pass over the 2026-09-22 Wikidata JSON dump that writes the seed items with their statements verbatim, an
index of every entity, the property entities and the whole-dump statistics the datasheet needs. After the pass, the
same tool writes the per-relation qualifier usage that P6 reads, `qualifier-usage-20260922.json`, into this folder
(SPEC §12).

## Log

- 2026-09-24: dump download started (1.2 MB/s cap, owner's choice); slicer built.
- 2026-09-24: curl's `--retry` truncated the partial download to zero, so the download restarted; `raw/fetch.sh` now
  retries in its own loop, each curl run resuming with `-C -`, and runs uncapped (owner's choice).

## Results and findings

## Open questions raised
