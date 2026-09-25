# P1 round trips per operation (first half)

khg-contracts 1.0.0.dev0 at commit `914b810e8436202cfacbd9153c024dc4a1e11ad2`. Measured, not estimated: each adapter counts the calls it makes to its engine (`khg_bakeoff.trips`; DESIGN §6.1), on P2's gate fixture, one store per backend, the operations in this order. A call is a statement, query, update or bulk call, or the begin or commit of a transaction (SQLite's and Oxigraph's are in-process; the HIF store counts file reads and writes, and answers every read from its in-memory index: "file, read in memory"). `R` marks a refusal (a missing flag). `put` is counted apart from `load` (research 01 D2). No timings.

| Operation | sqlite | postgres | oxigraph | neo4j | typedb | hif |
|---|---|---|---|---|---|---|
| load: the fixture into an empty store (40 records) | 10 | 11 | 4 | 7 | 9 | 1 |
| get: a fact (f:king-14) | 2 | 2 | 1 | 1 | 2 | 0 |
| get: an entity (ex:Paris) | 2 | 2 | 1 | 1 | 3 | 0 |
| get_many: 10 ids | 3 | 3 | 1 | 1 | 3 | 0 |
| history: f:king-14 | 2 | 2 | 1 | 1 | 2 | 0 |
| incident: ex:KingOfFrance (2 answers) | 4 | 4 | 3 | 3 | 4 | 0 |
| incident: ex:KingOfFrance, limit 1 | 4 | 4 | 3 | 3 | 4 | 0 |
| degree: ex:KingOfFrance | 2 | 2 | 2 | 2 | 3 | 0 |
| find: position_held, position KingOfFrance | 3 | 3 | 2 | 2 | 3 | 0 |
| find: position_held, [] (relation scan) | 3 | 3 | 2 | 2 | 3 | 0 |
| find_by_key: position_held, KingOfFrance | 3 | 3 | 2 | 2 | 3 | 0 |
| supersession_walk: f:born-skłodowska-kraków | 6 | 6 | 4 | 4 | 5 | 0 |
| export: khg-json of the store | 3 | 3 | 1 | 1 | 3 | 0 |
| put: one new version (f:king-14) | 34 | 39 | 11 | 26 | 16 | 1 |
| put: two new records (an entity and a fact) | 43 | 45 | 8 | 25 | 15 | 1 |
| load: the fixture again (40 held ids, new versions) | 15 | 17 | 4 | 8 | 11 | 1 |

## Calls by kind

read / write / transaction (file for HIF), per operation and backend:

| Operation | sqlite | postgres | oxigraph | neo4j | typedb | hif |
|---|---|---|---|---|---|---|
| load: the fixture into an empty store (40 records) | 2 / 6 / 2 | 3 / 6 / 2 | 2 / 2 / 0 | 2 / 3 / 2 | 2 / 5 / 2 | 1 |
| get: a fact (f:king-14) | 2 / 0 / 0 | 2 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 1 | 0 |
| get: an entity (ex:Paris) | 2 / 0 / 0 | 2 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 2 / 0 / 1 | 0 |
| get_many: 10 ids | 3 / 0 / 0 | 3 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 2 / 0 / 1 | 0 |
| history: f:king-14 | 2 / 0 / 0 | 2 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 1 | 0 |
| incident: ex:KingOfFrance (2 answers) | 4 / 0 / 0 | 4 / 0 / 0 | 3 / 0 / 0 | 3 / 0 / 0 | 3 / 0 / 1 | 0 |
| incident: ex:KingOfFrance, limit 1 | 4 / 0 / 0 | 4 / 0 / 0 | 3 / 0 / 0 | 3 / 0 / 0 | 3 / 0 / 1 | 0 |
| degree: ex:KingOfFrance | 2 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 1 | 0 |
| find: position_held, position KingOfFrance | 3 / 0 / 0 | 3 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 1 | 0 |
| find: position_held, [] (relation scan) | 3 / 0 / 0 | 3 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 1 | 0 |
| find_by_key: position_held, KingOfFrance | 3 / 0 / 0 | 3 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 0 | 2 / 0 / 1 | 0 |
| supersession_walk: f:born-skłodowska-kraków | 6 / 0 / 0 | 6 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 1 | 0 |
| export: khg-json of the store | 3 / 0 / 0 | 3 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 2 / 0 / 1 | 0 |
| put: one new version (f:king-14) | 28 / 4 / 2 | 29 / 6 / 4 | 10 / 1 / 0 | 22 / 2 / 2 | 12 / 2 / 2 | 1 |
| put: two new records (an entity and a fact) | 35 / 6 / 2 | 36 / 7 / 2 | 7 / 1 / 0 | 21 / 2 / 2 | 10 / 3 / 2 | 1 |
| load: the fixture again (40 held ids, new versions) | 5 / 8 / 2 | 6 / 9 / 2 | 3 / 1 / 0 | 3 / 3 / 2 | 4 / 5 / 2 | 1 |

## Growth with the store

Calls on stores of 40 and 440 records (P2's fixture, then plus 200 people born in `ex:Paris`): the same, or one more per chunk of ids (`CHUNK`, `BATCH`).

| Operation | sqlite | postgres | oxigraph | neo4j | typedb | hif |
|---|---|---|---|---|---|---|
| load, empty store | 10 → 10 | 11 → 11 | 4 → 4 | 7 → 7 | 9 → 11 | 1 → 1 |
| export | 3 → 3 | 3 → 3 | 1 → 1 | 1 → 1 | 3 → 3 | 0 → 0 |
| incident ex:Paris | 2 → 4 | 2 → 4 | 2 → 3 | 2 → 3 | 3 → 5 | 0 → 0 |
| degree ex:Paris | 2 → 2 | 2 → 2 | 2 → 2 | 2 → 2 | 3 → 3 | 0 → 0 |
| get_many, every id | 3 → 3 | 3 → 3 | 1 → 1 | 1 → 1 | 3 → 10 | 0 → 0 |
| load, every id held | 15 → 15 | 17 → 17 | 4 → 4 | 8 → 8 | 11 → 20 | 1 → 1 |
