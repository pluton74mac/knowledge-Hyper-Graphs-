"""Code sharing, tested: MemoryStore's write path (validation, version rule, references, nesting, keys, supersession,
transaction time, the four events) runs unchanged over a SQLite-backed version table.

``MemoryStore`` keeps every version in ``self._table`` (``store._table.VersionTable``), and its write path
(``_writes.WriteMixin``, ``_events.EventsMixin``) and reads use only this table interface: ``current``,
``entries``, ``entry_at``, ``latest`` (read and set), ``latest_version``, ``add``, ``by_node``, ``by_relation``,
``by_key``, ``by_ref``, ``ids``, ``__contains__`` and ``__len__``. ``SQLiteTable`` implements it on the tables of
sql_incidence.py (plus a node index table), and ``SQLiteTableStore`` is ``MemoryStore`` with that table and one
SQLite transaction per write. The full suite then runs against SQLite. Writes out/table-store-sqlite.json.

These are private modules of khg-contracts 1.0.0.dev0 (``store._table``, ``store._writes``, ``store._events``);
research 01 recommends that P2 publish the table interface before P1 builds on it.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from common import assemble, split, write_out
from khg_contracts.store import MemoryStore, conformance
from khg_contracts.store._table import Entry

DDL = """
CREATE TABLE meta (k TEXT PRIMARY KEY, v INTEGER);
CREATE TABLE version (id TEXT, version INTEGER, t INTEGER, kind TEXT, relation TEXT, key_digest TEXT,
                      status_ref TEXT, fact_row TEXT, record TEXT, PRIMARY KEY (id, version));
CREATE TABLE binding (fact_id TEXT, version INTEGER, bid TEXT, role TEXT, position INTEGER, direction TEXT,
                      value_kind TEXT, ref TEXT, ident TEXT, value_json TEXT, extensions TEXT,
                      PRIMARY KEY (fact_id, version, bid));
CREATE INDEX binding_ref ON binding (ref);
CREATE INDEX version_rel ON version (relation);
CREATE INDEX version_key ON version (relation, key_digest);
CREATE INDEX version_ref ON version (status_ref);
"""
BCOLS = ("fact_id", "version", "bid", "role", "position", "direction", "value_kind", "ref", "ident", "value_json",
         "extensions")


class SQLiteTable:
    """The VersionTable interface over SQLite: hyperedges as a fact row plus binding rows, entities as JSON."""

    def __init__(self, schema: Any):
        self.schema = schema
        self.con = sqlite3.connect(":memory:", isolation_level="DEFERRED")
        self.con.executescript(DDL)
        self.con.commit()
        self._cache: dict[tuple[str, int], Entry] = {}

    # latest: the store's latest transaction time
    @property
    def latest(self) -> int | None:
        row = self.con.execute("SELECT v FROM meta WHERE k = 'latest'").fetchone()
        return row[0] if row else None

    @latest.setter
    def latest(self, t: int | None) -> None:
        self.con.execute("INSERT INTO meta VALUES ('latest', ?) ON CONFLICT (k) DO UPDATE SET v = excluded.v", (t,))

    def __contains__(self, rid: object) -> bool:
        return self.con.execute("SELECT 1 FROM version WHERE id = ? LIMIT 1", (rid,)).fetchone() is not None

    def __len__(self) -> int:
        return self.con.execute("SELECT count(DISTINCT id) FROM version").fetchone()[0]

    def ids(self) -> list[str]:
        return sorted(r[0] for r in self.con.execute("SELECT DISTINCT id FROM version"))

    def _entry(self, rid: str, version: int, t: int, kind: str, fact_row: str | None, record: str | None) -> Entry:
        key = (rid, version)
        e = self._cache.get(key)
        if e is None:
            if kind == "entity":
                rec = json.loads(record)
            else:
                rows = [dict(zip(BCOLS, r)) for r in self.con.execute(
                    f"SELECT {', '.join(BCOLS)} FROM binding WHERE fact_id = ? AND version = ?", (rid, version))]
                rec = assemble(json.loads(fact_row), rows)
            e = self._cache[key] = Entry(rec, t, self.schema)
        return e

    def entries(self, rid: str) -> list[Entry]:
        return [self._entry(*r) for r in self.con.execute(
            "SELECT id, version, t, kind, fact_row, record FROM version WHERE id = ? ORDER BY version", (rid,))]

    def current(self, rid: str) -> dict | None:
        es = self.entries(rid)
        return es[-1].record if es else None

    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None:
        es = self.entries(rid)
        if as_at is None:
            return es[-1] if es else None
        for e in reversed(es):
            if e.t <= as_at:
                return e
        return None

    def latest_version(self, rid: str) -> int:
        row = self.con.execute("SELECT max(version) FROM version WHERE id = ?", (rid,)).fetchone()
        return row[0] or 0

    def add(self, record: dict, t: int) -> Entry:
        if record["kind"] == "entity":
            self.con.execute("INSERT INTO version (id, version, t, kind, record) VALUES (?, ?, ?, 'entity', ?)",
                             (record["id"], record["version"], t, json.dumps(record)))
        else:
            fact, rows = split(record, self.schema)
            self.con.execute("INSERT INTO version VALUES (?, ?, ?, 'hyperedge', ?, ?, ?, ?, NULL)",
                             (record["id"], record["version"], t, record.get("relation"), fact["key_digest"],
                              record.get("status_ref"), json.dumps(fact)))
            self.con.executemany(f"INSERT INTO binding VALUES ({', '.join('?' * len(BCOLS))})",
                                 [[r[c] for c in BCOLS] for r in rows])
        lt = self.latest
        self.latest = t if lt is None else max(lt, t)
        return Entry(record, t, self.schema)

    def by_node(self, node: str) -> set[str]:
        return {r[0] for r in self.con.execute("SELECT DISTINCT fact_id FROM binding WHERE ref = ?", (node,))}

    def by_relation(self, relation: str) -> set[str]:
        return {r[0] for r in self.con.execute("SELECT DISTINCT id FROM version WHERE relation = ?", (relation,))}

    def by_key(self, relation: str, digest: str) -> set[str]:
        return {r[0] for r in self.con.execute(
            "SELECT DISTINCT id FROM version WHERE relation = ? AND key_digest = ?", (relation, digest))}

    def by_ref(self, lifecycle_id: str) -> set[str]:
        return {r[0] for r in self.con.execute("SELECT DISTINCT id FROM version WHERE status_ref = ?",
                                               (lifecycle_id,))}

    def __iter__(self):
        return iter(self.ids())


class SQLiteTableStore(MemoryStore):
    """MemoryStore over SQLiteTable; each write is one SQLite transaction (committed after the checks pass)."""

    def __init__(self, schema: Any, **k: Any):
        super().__init__(schema, store_id="sqlite-table", **k)
        self._table = SQLiteTable(self.schema)

    def _commit(self, *a: Any, **k: Any) -> Any:
        try:
            receipt = super()._commit(*a, **k)
        except BaseException:
            self._table.con.rollback()
            self._table._cache.clear()
            raise
        self._table.con.commit()
        return receipt

    def load(self, *a: Any, **k: Any) -> Any:
        try:
            report = super().load(*a, **k)
        except BaseException:
            self._table.con.rollback()
            self._table._cache.clear()
            raise
        self._table.con.commit()
        return report


def main() -> None:
    started = time.perf_counter()
    report = conformance.run(lambda schema, clock: SQLiteTableStore(schema, clock=clock))
    out = {"store": "MemoryStore write path over SQLiteTable (sqlite3 " + sqlite3.sqlite_version + ")",
           "seconds": round(time.perf_counter() - started, 2), "summary": report["summary"],
           "not_passed": {a["test"]["identifier"]: a["result"].get("info", "")[:300]
                          for a in report["@graph"] if a["result"]["outcome"] not in ("passed", "inapplicable")}}
    print(out["summary"], out["seconds"], list(out["not_passed"])[:10])
    write_out("table-store-sqlite", out)


if __name__ == "__main__":
    main()
