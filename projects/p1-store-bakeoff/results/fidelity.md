# P1 fidelity (first half)

khg-contracts 1.0.0.dev0 at commit `12159f8a1bf5434be085d42b79ae9ff67e6446bd`; khg-record/1.0.0, khg-store/1.0.0. Data sets: P2's `fixture.c1.json` (40 records) and `fixture.history.c1.json` (10 versions), and P1's `fixtures/edge.c1.json` (41 records). The four numbers of research 01 D5 (DESIGN §5); number 3 on the hand queries only (the query set is frozen in the second half). No timings.

**1. Container round trip**: records that differ after `load(on_missing="skip")` → `export`, as skipped/silent, per data set (fixture, history, edge); store fields that differ from `MemoryStore` holding the same records. **2. Native layer** (fixture; edge): bids, literals as written, positions, extensions and role–value multisets kept without the record-level copies. **3. Answers**: same as `MemoryStore` / compared (fixture hand queries; history transaction-time checks; edge queries). **4. Inapplicable scenarios** (losses by flag, from the conformance run).

| Backend | Engine | Kind | 1. Round trip: fixture / history / edge | 1. Store fields | 2. Native: bids, literals, positions, extensions, multisets (fixture; edge) | 3. Answers: fixture / history / edge | 4. Inapplicable |
|---|---|---|---|---|---|---|---|
| sqlite | SQLite 3.45.1 | embedded | 0 skipped, 0 silent / 0 skipped, 0 silent / 1 skipped, 0 silent | 0 | 59/59, 20/20, 3/3, 2/2, 18/18; 42/42, 5/5, 2/2, –, 20/20 | 13/13 / 85/85 / 24/24 | 0 |
| postgres | PostgreSQL 18.6 | client-server | 0 skipped, 0 silent / 0 skipped, 0 silent / 0 skipped, 0 silent | 0 | 59/59, 20/20, 3/3, 2/2, 18/18; 45/45, 6/6, 2/2, –, 21/21 | 13/13 / 85/85 / 24/24 | 0 |
| oxigraph | Oxigraph (pyoxigraph) pyoxigraph 0.5.11 | embedded | 0 skipped, 0 silent / 0 skipped, 0 silent / 1 skipped, 0 silent | 0 | 59/59, 20/20, 3/3, 2/2, 18/18; 42/42, 5/5, 2/2, –, 20/20 | 13/13 / 85/85 / 24/24 | 0 |
| neo4j | Neo4j Community 2026.09.0 community | client-server | 0 skipped, 0 silent / 0 skipped, 0 silent / 1 skipped, 0 silent | 0 | 59/59, 20/20, 3/3, 2/2, 18/18; 42/42, 5/5, 2/2, –, 20/20 | 13/13 / 85/85 / 24/24 | 0 |
| typedb | TypeDB CE TypeDB CE 3.13.6 | client-server | 4 skipped, 0 silent / not loaded (no history_export) / 6 skipped, 0 silent | 0 | 0/48, 0/19, –, 0/2, 14/14; 0/33, –, –, –, 16/16 | 13/13 / – / 24/24 | 44 (goals 33, history_export 1, ordered_roles 29, special_values 33, transaction_time 7) |
| hif | HIF file (khg-contracts to_hif/from_hif) khg-contracts 1.0.0.dev0 (khg-hif/1.0.0) | embedded | 0 skipped, 0 silent / not loaded (no history_export) / 0 skipped, 0 silent | 42 | 59/59, 20/20, 3/3, 2/2, 18/18; 45/45, 6/6, 2/2, –, 21/21 | 13/13 / – / 23/24 | 7 (history_export 1, transaction_time 7) |

## What each backend lost

### sqlite

- edge: `f:far-future` skipped: {"cannot_hold": {"reason": "instant_range", "instants": ["315569520000148668048000", "315569520000148699584000"], "held": "|instant| <= 4611686018427387902 s (2^62 - 2)"}}

### postgres

- nothing.

### oxigraph

- edge: `f:far-future` skipped: {"cannot_hold": {"reason": "instant_range", "instants": ["315569520000148668048000", "315569520000148699584000"], "held": "|instant| <= 4611686018427387902 s (2^62 - 2)"}}

### neo4j

- edge: `f:far-future` skipped: {"cannot_hold": {"reason": "instant_range", "instants": ["315569520000148668048000", "315569520000148699584000"], "held": "|instant| <= 4611686018427387902 s (2^62 - 2)"}}

### typedb

- fixture: `f:born-scribe` skipped: {"missing_flags": ["special_values"]}
- fixture: `f:cat-7` skipped: {"missing_flags": ["special_values"]}
- fixture: `f:route-1` skipped: {"missing_flags": ["ordered_roles"]}
- fixture: `g:who-1774` skipped: {"missing_flags": ["goals"]}
- fixture, native layer: extensions lost on 2: f:coadmin-1 b1, f:reg-1 b3
- fixture, native layer: literal as written lost on 19: f:claim-1 b3, f:king-13 b3, f:king-13 b4, f:king-14 b3, f:king-14 b4, f:married-curie b3, f:married-curie b4, f:pop-łódź-2019 b2, f:pop-łódź-2019 b3, f:pop-łódź-2019-dep b2, f:pop-łódź-2019-dep b3, f:station-東京 b2, f:station-東京 b3, f:station-東京 b4, f:station-東京 b5, f:station-東京 b6, f:station-東京 b7, f:station-東京 b8, f:station-東京 b9
- history: not loaded: CapabilityMissing: history_export (10 versions).
- edge: `ex:Dual` skipped: {"cannot_hold": {"reason": "instance_type", "detail": "a TypeDB instance has exactly one type", "types": ["Place", "Station"]}}
- edge: `f:aliases-twice` skipped: {"missing_flags": ["ordered_roles"]}
- edge: `f:constant-c` skipped: {"cannot_hold": {"reason": "no_role_player", "relation": "measured_constant", "detail": "the relation has no entity or fact role (SVL41)"}}
- edge: `f:dual-profile` skipped: {"references": "a skipped record"}
- edge: `f:far-future` skipped: {"cannot_hold": {"reason": "instant_range", "instants": ["315569520000148668048000", "315569520000148699584000"], "held": "|instant| <= 4611686018427387902 s (2^62 - 2)"}}
- edge: `g:who-what` skipped: {"missing_flags": ["goals"]}

### hif

- fixture: store fields differ from `MemoryStore` on 22 records (recorded_by)
- history: not loaded: CapabilityMissing: history_export (10 versions).
- edge: store fields differ from `MemoryStore` on 20 records (recorded_by)
- edge, answer differs: get ex:Dual (two types)
