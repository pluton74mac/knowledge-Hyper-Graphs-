---
title: Format and store bake-off
type: project
status: exploring
started: 2026-09-25
depends_on: [kb/04-storage-and-formats/format-recommendations.md, kb/04-storage-and-formats/hypergraph-databases.md, kb/04-storage-and-formats/property-graph-emulation-patterns.md, kb/04-storage-and-formats/relational-and-eav-storage.md, kb/04-storage-and-formats/rdf-star-and-semantic-web-serialisations.md, projects/p2-role-aware-hif/DESIGN.md]
---

# Format and store bake-off (P1)

Programme id **P1**, phase 1, kind **finding**. See [../PLAN.md](../PLAN.md).

## Question or goal

Hold the same knowledge hypergraph in five stores (an incidence table, reified RDF 1.2 in the relation-instance
pattern, a bipartite property graph, TypeDB and HIF files), run the same queries on each, and measure round-trip
fidelity, load time and query latency.

## Why it matters

Theme 1 of the [open-questions register](../../kb/00-index/open-questions.md): does a native hyperedge store beat
reified triples and plain relational tables holding the same n-ary facts, on the same workload, with cost and
latency reported ([08.1], [04.2])? No three-way comparison exists. Theme 4 ([04.8], raised by P2): what each
backend loses against the C2 conformance suite.

## Gate (PLAN §4)

Table of five stores by round-trip fidelity, load time and query latency on one query set.

## Consumes

C1 and C2 from P2 (`khg-record/1.0.0`, `khg-store/1.0.0`: the store protocol, capability flags and the
114-scenario conformance suite; [DESIGN §6](../p2-role-aware-hif/DESIGN.md)); a C4 slice from P3a for the
measurement. The conformance ruling (P2 DESIGN §14, ruling 1): a backend passes when no applicable scenario
fails; scenarios made inapplicable by a missing capability are reported as fidelity losses.

## Plan

1. **Now (needs only C1, C2).** Research the five backends as they run in this container (probed, not
   assumed); design the adapters and the fidelity measure; implement each backend behind the C2 protocol; run
   the conformance suite on each; round-trip the P2 fixtures.
2. **When P3a's corpus lands (C4 slice).** Fix the query set from the C2 operations and the corpus, measure load
   time and query latency, and write the table and the technical report.

## Log

- 2026-09-25: started (first half: backends and conformance). Pace as P6: one agent per stage, one review round.

## Results and findings

## Open questions raised
