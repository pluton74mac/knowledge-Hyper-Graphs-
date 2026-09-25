"""The SQLite adapter (DESIGN §3.1): the incidence tables in the standard library's ``sqlite3``, the embedded control
row of the bake-off (ruling 1).

``SQLiteStore(schema, *, path=None, clock=None, capabilities=None, store_id="sqlite")`` holds the store in memory
(``path=None``) or in a database file; a file that already holds a store is reopened with its kept header.
Instants are int64 with the ±2^62 guard (ruling 4); ids sort in code-point order (``BINARY`` collation of UTF-8).
Each write is one ``BEGIN`` … ``COMMIT``; a bulk load inserts its rows with ``executemany``.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any, Iterable, Mapping, Sequence

from .rows import instant, query_instant
from .sql import SQLStore, SQLTable, ddl

__all__ = ["SQLiteDB", "SQLiteStore", "factory"]


class SQLiteDB:
    """One ``sqlite3`` connection in autocommit mode, with explicit transactions."""

    as_instant = staticmethod(instant)
    query_instant = staticmethod(query_instant)

    def __init__(self, path: str | os.PathLike | None):
        self.path = ":memory:" if path is None else os.fspath(path)
        self.con = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)

    def q(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        return self.con.execute(sql, tuple(params)).fetchall()

    def x(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.con.execute(sql, tuple(params))

    def insert(self, table: str, rows: Iterable[Mapping[str, Any]]) -> None:
        rows = list(rows)
        if not rows:
            return
        cols = list(rows[0])
        self.con.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                             [tuple(r[c] for c in cols) for r in rows])

    bulk_insert = insert

    def put_meta(self, k: str, v: str | None) -> None:
        self.con.execute("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT (k) DO UPDATE SET v = excluded.v", (k, v))

    def begin(self) -> None:
        self.con.execute("BEGIN")

    def commit(self) -> None:
        self.con.execute("COMMIT")

    def rollback(self) -> None:
        if self.con.in_transaction:
            self.con.execute("ROLLBACK")

    def has_store(self) -> bool:
        return bool(self.q("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"))

    def create(self) -> None:
        self.begin()
        for stmt in ddl("BIGINT"):
            self.x(stmt)
        self.commit()

    def close(self) -> None:
        self.con.close()


class SQLiteStore(SQLStore):
    """A C2 store in SQLite (see the module docstring)."""

    ENGINE = "SQLite"
    KIND = "embedded"
    INT64 = True

    def __init__(self, schema: Any, *, path: str | os.PathLike | None = None, clock: Any = None,
                 capabilities: Iterable[str] | None = None, store_id: str = "sqlite"):
        self.db = SQLiteDB(path)
        reopen = self.db.has_store()
        if not reopen:
            self.db.create()
        super().__init__(schema, table=lambda s: SQLTable(s, self.db), clock=clock,
                         capabilities=self.FLAGS if capabilities is None else capabilities, store_id=store_id)
        if reopen:
            self._read_documents()

    def engine_version(self) -> str:
        return sqlite3.sqlite_version

    def close(self) -> None:
        self.db.close()


def factory(schema: Any, clock: Any) -> SQLiteStore:
    """A fresh in-memory ``SQLiteStore``: the factory for ``conformance.run`` and ``khg-conformance``."""
    return SQLiteStore(schema, clock=clock)
