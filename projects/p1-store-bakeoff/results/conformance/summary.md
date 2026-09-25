# P1 conformance runs (first half)

khg-contracts 1.0.0.dev0 at commit `12159f8a1bf5434be085d42b79ae9ff67e6446bd`; khg-record/1.0.0, khg-store/1.0.0, khg-scenario/1.0.0 (114 scenarios); khg-contracts' own runner (`conformance.run`). A backend passes when no applicable scenario fails (PLAN §7); every inapplicable scenario is a fidelity loss, listed by flag.

| Backend | Engine | Kind | Applicable | Passed | Failed | cantTell | Inapplicable (losses) | Passes |
|---|---|---|---|---|---|---|---|---|
| sqlite | SQLite 3.45.1 | embedded | 114 | 114 | 0 | 0 | 0 | yes |
| postgres | PostgreSQL 18.6 | client-server | 114 | 114 | 0 | 0 | 0 | yes |
| oxigraph | Oxigraph 0.5.11 (pyoxigraph) | embedded | 114 | 114 | 0 | 0 | 0 | yes |
| neo4j | Neo4j 2026.09.0 community | client-server | 114 | 114 | 0 | 0 | 0 | yes |
| typedb | TypeDB CE 3.13.6 | client-server | 70 | 70 | 0 | 0 | 44 | yes |
| hif | HIF file khg-hif/1.0.0 (khg-contracts 1.0.0.dev0 to_hif/from_hif) | embedded | 107 | 107 | 0 | 0 | 7 | yes |

## Losses by flag

- **sqlite**: none.
- **postgres**: none.
- **oxigraph**: none.
- **neo4j**: none.
- **typedb** (flags declared absent: goals, history_export, ordered_roles, special_values, transaction_time):
  - `goals` (33): S-EXP-001, S-EXP-002, S-EXP-003, S-EXP-006, S-EXP-007, S-EXP-011, S-KEY-002, S-KEY-003, S-LIFE-008, S-LIFE-009, S-LIFE-010, S-PUT-007, S-READ-001, S-READ-002, S-READ-003, S-READ-004, S-READ-005, S-READ-006, S-READ-007, S-READ-008, S-READ-009, S-READ-010, S-READ-011, S-READ-012, S-READ-013, S-READ-014, S-READ-015, S-READ-016, S-READ-017, S-READ-018, S-READ-019, S-TIME-001, S-VER-006
  - `history_export` (1): S-EXP-005
  - `ordered_roles` (29): S-EXP-001, S-EXP-002, S-EXP-003, S-EXP-006, S-EXP-007, S-EXP-011, S-KEY-002, S-KEY-003, S-READ-001, S-READ-002, S-READ-003, S-READ-004, S-READ-005, S-READ-006, S-READ-007, S-READ-008, S-READ-009, S-READ-010, S-READ-011, S-READ-012, S-READ-013, S-READ-014, S-READ-015, S-READ-016, S-READ-017, S-READ-018, S-READ-019, S-TIME-001, S-VER-006
  - `special_values` (33): S-EXP-001, S-EXP-002, S-EXP-003, S-EXP-006, S-EXP-007, S-EXP-011, S-KEY-002, S-KEY-003, S-KEY-011, S-READ-001, S-READ-002, S-READ-003, S-READ-004, S-READ-005, S-READ-006, S-READ-007, S-READ-008, S-READ-009, S-READ-010, S-READ-011, S-READ-012, S-READ-013, S-READ-014, S-READ-015, S-READ-016, S-READ-017, S-READ-018, S-READ-019, S-TIME-001, S-TIME-009, S-VER-006, S-VER-007, S-VER-009
  - `transaction_time` (7): S-EXP-004, S-EXP-005, S-EXP-008, S-EXP-010, S-TIME-002, S-TIME-004, S-VER-001
- **hif** (flags declared absent: history_export, transaction_time):
  - `history_export` (1): S-EXP-005
  - `transaction_time` (7): S-EXP-004, S-EXP-005, S-EXP-008, S-EXP-010, S-TIME-002, S-TIME-004, S-VER-001
