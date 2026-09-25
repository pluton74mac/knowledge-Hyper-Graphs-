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

## Director's rulings on the build (2026-09-25)

On the four open questions of [IMPLEMENTATION-NOTES.md](IMPLEMENTATION-NOTES.md):

1. **A code for "cannot hold" (Q1).** Not in 1.0. The refusal stays a `ValidationError` without a code, with the
   reason in `info["cannot_hold"]`; a registered code joins the registry in khg-store 1.1 (P2 DESIGN §14, ruling 18,
   following ruling 13).
2. **`on_missing="skip"` (Q2).** Accepted as built: it skips records refused by `cannot_hold` and counts them, and
   each skip is a fidelity loss of that backend (ruling 18).
3. **`khg-recorded-by` on HIF entity nodes (Q3).** No profile change now. The missing store field is a measured loss
   of the HIF format and is reported as such; adding it is a candidate for a `khg-hif` minor version.
4. **TypeDB and slices that are not complete (Q4).** No stub instances: stubs would be emulation, which ruling 8
   excludes. A fact whose player TypeDB does not hold is refused and counted as a TypeDB loss.

## Director's rulings on review 01 (2026-09-25)

[Review 01](review/review-01.md) reproduced every conformance and fidelity result and found 15 defects (3 high, 5
medium, 7 low). All 15 are fixed in this half, each with a regression test. Two need a ruling:

- **R-06, what "native reads" means for timing.** Every adapter pushes filters, `limit` and counting into its engine
  where the engine can express them (`degree` is a native count; TypeDB's `find` matches and limits in TypeQL), and
  fetches the records of one call in a bounded number of queries, never one query per record. The rows returned are
  rebuilt into records by one shared Python function, the same for every backend, so the Python cost is equal across
  rows and the engine part is what differs. HIF is a file format: its reads run on the in-memory index built from the
  file, and its rows are labelled "file, read in memory". DESIGN.md gets a table of round trips per operation and
  adapter.
- **R-07, the public table interface.** The header and documents get public accessors in `khg_contracts.store.table`
  (an addition to ruling 17, still outside C2), and a failed `load` rolls the header back. `MemoryStore` must still
  behave exactly as before; the differential check of review 01 is re-run.

Also before timing: `put` is timed separately from `load` (research D2), and the TypeDB server is cleaned of
leftover databases.

## Log

- 2026-09-25: started (first half: backends and conformance). Pace as P6: one agent per stage, one review round.
- 2026-09-25: research 01 done: every backend probed in the container; rulings above.
- 2026-09-25: first half built. khg-contracts publishes the version-table interface (P2 DESIGN §14 ruling 17).
  [khg-bakeoff](khg-bakeoff/) has six adapters on it: the shared write path, native reads and a native bulk load.
  All six pass khg-contracts' own conformance suite, and the four fidelity numbers are measured on P2's two
  fixtures and on P1's edge-case container ([fixtures/](fixtures/)). [DESIGN](DESIGN.md) records the design and
  [IMPLEMENTATION-NOTES](IMPLEMENTATION-NOTES.md) the decisions and deviations. [start-servers.sh](start-servers.sh)
  starts the pinned servers. The corrections of research 01 §11 are applied: P2 DESIGN §6.5 amendments A1–A4 and
  four notes in `kb/04-storage-and-formats/`. Next: one review round, then the second half on P3a's slice.

## Results and findings

**First half (2026-09-25): conformance and fidelity; no timings.**
- **Sources.** [results/conformance/](results/conformance/) (one EARL report per backend, `summary.md`) and
  [results/fidelity.md](results/fidelity.md) (`fidelity.json`).
- **Versions.** khg-contracts 1.0.0.dev0 at commit `12159f8`, with C1 `khg-record/1.0.0`, C2 `khg-store/1.0.0` and
  the 114-scenario suite `khg-scenario/1.0.0`.
- **Pass rule.** A backend passes when no applicable scenario fails (PLAN §7). Every inapplicable scenario is a
  fidelity loss, listed by flag in `summary.md`.
- **The fidelity columns** (DESIGN §5):
  1. records lost in the round trip, as skipped or silent, on fixture / history / edge;
  2. of the native layer without the record-level copies: bids, then literals as written, kept (fixture);
  3. answers equal to `MemoryStore`'s: 13 hand queries on the fixture, 85 transaction-time checks, 24 edge queries;
  4. inapplicable scenarios.

| Backend | Engine | Kind | Applicable / passed / inapplicable (losses by flag) | 1. Round trip: skipped, silent | 2. Native: bids; literals as written | 3. Answers | Load time | Query latency |
|---|---|---|---|---|---|---|---|---|
| Incidence table | PostgreSQL 18.6 (psycopg 3.3.6) | client–server | 114 / 114 / 0 | 0, 0 / 0, 0 / 0, 0 | 59/59; 20/20 | 13/13, 85/85, 24/24 | second half, after P3a's slice | second half, after P3a's slice |
| Incidence table (control) | SQLite 3.45.1 | embedded | 114 / 114 / 0 | 0, 0 / 0, 0 / 1, 0 | 59/59; 20/20 | 13/13, 85/85, 24/24 | second half | second half |
| Reified RDF, named graph per version | Oxigraph (pyoxigraph 0.5.11) | embedded | 114 / 114 / 0 | 0, 0 / 0, 0 / 1, 0 | 59/59; 20/20 | 13/13, 85/85, 24/24 | second half | second half |
| Bipartite property graph, version nodes | Neo4j Community 2026.09.0 (neo4j 6.3.1) | client–server | 114 / 114 / 0 | 0, 0 / 0, 0 / 1, 0 | 59/59; 20/20 | 13/13, 85/85, 24/24 | second half | second half |
| TypeDB, natural mapping | TypeDB CE 3.13.6 (typedb-driver 3.13.6) | client–server | 70 / 70 / 44 (goals 33, ordered_roles 29, special_values 33, transaction_time 7, history_export 1) | 4, 0 / not loaded / 6, 0 | 0/48; 0/19 | 13/13, –, 24/24 | second half | second half |
| HIF file | khg-contracts `to_hif`/`from_hif` (khg-hif/1.0.0) | embedded | 107 / 107 / 7 (transaction_time 7, history_export 1) | 0, 0 / not loaded / 0, 0 | 59/59; 20/20 | 13/13, –, 23/24 | second half | second half |

**Findings.**
1. **Every backend passes C2's conformance test** under ruling 1. SQLite, PostgreSQL 18.6, Oxigraph and Neo4j apply
   all 114 scenarios and pass them. TypeDB passes the 70 that apply to its natural mapping, and HIF the 107 that
   apply to a snapshot file. Both figures are the ones P2 §6.5 predicted.
2. **No backend loses anything silently.** Every difference in a round trip is a record the store skipped, with its
   reason.
3. **The int64 backends refuse a 16-digit year instead of storing a wrong value.** A C1 time literal with such a
   year puts an instant near 3.2 × 10^23 s. SQLite, Oxigraph, Neo4j and TypeDB each refuse the one record with an
   instant beyond ±(2^62 − 2) s (ruling 4). PostgreSQL's `numeric` holds it and answers `as_of` reads in year
   10^16 correctly.
4. **TypeDB's native layer keeps role–value multisets but no bids, positions, directions, binding extensions or
   literals as written.** The records come back exactly only through the JSON copy of the bindings. On the edge
   container TypeDB also refuses:
   - a multi-typed entity and the fact that binds it (one type per instance);
   - a literal-only fact (a relation type must relate a role, SVL41);
   - the goal, and the ordered and far-future facts, by flag or by instant.
5. **The HIF store loses an entity's `recorded_by`.** The HIF profile's entity node has no `khg-recorded-by`
   (P2 DESIGN §4.2). This affects 22 of 22 fixture entities. `compare_containers` ignores store fields, and no
   scenario reads one after a reload, so only the store-field comparison and one edge query (`get ex:Dual`) show it.
6. **PostgreSQL can state part of the key invariant itself.** A `WITHOUT OVERLAPS` guard over preferred facts is
   sound under D016; the rest of D016 stays in the shared write path.

## Open questions raised

For the director (IMPLEMENTATION-NOTES §7):
- **Q1.** A registered code for "the backend cannot hold this valid record". Today it is a `ValidationError`
  without a code.
- **Q2.** Does `load(on_missing="skip")` cover the records a backend refuses (`cannot_hold`), as P1 reads it?
- **Q3.** Should P2 add `khg-recorded-by` to the HIF profile's entity node (a minor profile version)?
- **Q4.** For P3a slices that are not `complete`: stub player instances in TypeDB, or count those facts as TypeDB
  losses?
