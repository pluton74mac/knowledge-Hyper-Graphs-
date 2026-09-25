---
title: Format and store bake-off
type: project
status: prototyping
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

## Director's rulings on research 01 (2026-09-25)

On the ten decisions of [research/01-backends.md](research/01-backends.md) §10:

1. **Backends (D1).** PostgreSQL 18.6, Oxigraph (pyoxigraph 0.5.11), Neo4j Community 2026.09.0, TypeDB CE 3.13.6
   and the HIF file store, plus SQLite 3.45.1 as an embedded control row. LadybugDB stays out of the first half.
2. **Code sharing (D2).** Accepted: `MemoryStore`'s write path over a backend version table, with native reads.
   khg-contracts publishes the version-table interface (a documented public module and a table-backed store base)
   as an additive change: C2 `khg-store/1.0.0` is unchanged, `MemoryStore` behaves exactly as before, and P2's
   full test suite stays green. Recorded as P2 DESIGN §14 ruling 17. Adapters import public names only.
3. **Versions and transaction time (D3).** Accepted as proposed; TypeDB and HIF declare the two flags absent.
4. **Instants (D4).** Accepted: `numeric` in PostgreSQL, an int64 guard at ±2^62 elsewhere, `int8range` for key
   ranges. A refused instant is reported as a fidelity loss through the existing error and report model; any new
   error code needs a director's ruling first.
5. **Fidelity (D5).** The four numbers, and the edge-case container, are the fidelity columns of the gate table.
6. **Query set (D6).** A draft; frozen in the second half, against P3a's slice.
7. **Timing (D7).** Accepted for the second half. The first half makes no timing claims.
8. **TypeDB (D8).** The natural mapping only (70 applicable); no emulation row.
9. **Ablations (D9).** Deferred to the second half.
10. **Reproducibility (D10).** Accepted: `start-servers.sh` with pinned versions and download checksums; engines and
    data outside the repository.

The corrections of §11 (P2 DESIGN §6.5 and four KB notes) are applied with the implementation, cited to the probes.

## Log

- 2026-09-25: started (first half: backends and conformance). Pace as P6: one agent per stage, one review round.
- 2026-09-25: research 01 done: every backend probed in the container; rulings above.

## Results and findings

## Open questions raised
