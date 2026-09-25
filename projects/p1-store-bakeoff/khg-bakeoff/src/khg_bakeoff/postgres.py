"""The PostgreSQL adapter (DESIGN §3.1): the incidence tables in PostgreSQL 18 (research 01 §2), client psycopg 3.

``PostgresStore(schema, *, conninfo, database="khg_bakeoff", namespace=None, clock=None, capabilities=None,
store_id="postgres")`` keeps one store in one schema (namespace) of one database. ``namespace=None`` makes a fresh
schema that ``close`` drops (the conformance runs); a named one is kept and reopened. ``conninfo`` names the server
without a database (``"host=127.0.0.1 port=5418 user=postgres"``; ``KHG_BAKEOFF_POSTGRES`` in the tests).

- **Collation.** The database is created with ``LOCALE 'C'`` from ``template0``, so ``ORDER BY id`` and
  ``id > after`` follow code points (research 01 §7: an ICU collation reorders them). Opening refuses a database
  whose collation is not ``C``.
- **Instants** are ``numeric``: exact at any C1 year, ±Infinity for the unbounded sides (ruling 4); no guard.
- **Bulk load** writes its rows with ``COPY … FROM STDIN``, in the load's transaction.
- **The key guard** (research 01 §2.3, ruling 4). ``key_period(relation, key_digest, valid int8range, fact_id)``
  with ``PRIMARY KEY (relation, key_digest, valid WITHOUT OVERLAPS)`` (PostgreSQL 18; ``btree_gist``) holds the
  definite window of every current asserted **preferred** fact on a key (a non-temporal key: all time). Two such
  windows on one key never overlap under D016, so the database states that part of the key invariant itself; the
  rank exceptions and the rest of D016 stay in the shared write path. Instants beyond int8 are clamped into it, which
  can only miss an overlap, never invent one. A trusted load whose data already break the rule (ruling 12 keeps such
  data) leaves the guard off for that store (``key_guard`` is ``"suspended"``), so the load still succeeds.
"""
from __future__ import annotations

import itertools
import os
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from khg_contracts.schema import LIFECYCLE_RELATIONS

from .rows import numeric_instant
from .sql import SQLStore, SQLTable, ddl

__all__ = ["DATABASE", "PostgresDB", "PostgresStore", "PostgresTable", "factory"]

DATABASE = "khg_bakeoff"
_INT8 = 2 ** 63 - 1
_seq = itertools.count(1)


def _q(sql: str) -> str:
    return sql.replace("?", "%s")


class PostgresDB:
    """One psycopg connection in autocommit mode, with explicit transactions, on one schema of the database."""

    as_instant = staticmethod(numeric_instant)

    @staticmethod
    def query_instant(t: int) -> Decimal:
        return Decimal(int(t))

    def __init__(self, conninfo: str, database: str, namespace: str | None):
        import psycopg

        self.psycopg = psycopg
        admin = psycopg.connect(f"{conninfo} dbname=postgres", autocommit=True)
        try:
            if not admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", [database]).fetchone():
                admin.execute(f'CREATE DATABASE "{database}" LOCALE \'C\' ENCODING \'UTF8\' TEMPLATE template0')
        finally:
            admin.close()
        self.con = psycopg.connect(f"{conninfo} dbname={database}", autocommit=True)
        collate, ctype = self.con.execute("SELECT datcollate, datctype FROM pg_database "
                                          "WHERE datname = current_database()").fetchone()
        if (collate, ctype) != ("C", "C"):
            self.con.close()
            raise ValueError(f"database {database!r} has collation {collate}/{ctype}; the store needs C (code-point "
                             "order of ids)")
        self.con.execute("CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public")
        self.owned = namespace is None
        self.namespace = namespace or f"s{os.getpid()}_{next(_seq)}_{os.urandom(3).hex()}"
        self.con.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.namespace}"')
        self.con.execute(f'SET search_path TO "{self.namespace}", public')

    def q(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        cur = self.con.execute(_q(sql), list(params))
        return cur.fetchall() if cur.description is not None else []

    def x(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.con.execute(_q(sql), list(params))

    def insert(self, table: str, rows: Iterable[Mapping[str, Any]]) -> None:
        rows = list(rows)
        if not rows:
            return
        cols = list(rows[0])
        with self.con.cursor() as cur:
            cur.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('%s' for _ in cols)})",
                            [tuple(r[c] for c in cols) for r in rows])

    def bulk_insert(self, table: str, rows: Iterable[Mapping[str, Any]]) -> None:
        """``COPY table FROM STDIN``."""
        rows = list(rows)
        if not rows:
            return
        cols = list(rows[0])
        with self.con.cursor() as cur, cur.copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN") as copy:
            for r in rows:
                copy.write_row(tuple(r[c] for c in cols))

    def put_meta(self, k: str, v: str | None) -> None:
        self.x("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT (k) DO UPDATE SET v = excluded.v", (k, v))

    def begin(self) -> None:
        self.con.execute("BEGIN")

    def commit(self) -> None:
        self.con.execute("COMMIT")

    def rollback(self) -> None:
        if self.con.info.transaction_status != self.psycopg.pq.TransactionStatus.IDLE:
            self.con.execute("ROLLBACK")

    def has_store(self) -> bool:
        return bool(self.q("SELECT 1 FROM information_schema.tables WHERE table_schema = ? AND table_name = 'meta'",
                           (self.namespace,)))

    def create(self) -> None:
        self.begin()
        for stmt in ddl("NUMERIC"):
            self.x(stmt)
        self.x("""CREATE TABLE key_period (relation TEXT NOT NULL, key_digest TEXT NOT NULL, valid int8range NOT NULL,
                  fact_id TEXT NOT NULL, PRIMARY KEY (relation, key_digest, valid WITHOUT OVERLAPS))""")
        self.x("CREATE INDEX key_period_fact ON key_period (fact_id)")
        self.commit()

    def drop(self) -> None:
        self.rollback()
        self.con.execute(f'DROP SCHEMA IF EXISTS "{self.namespace}" CASCADE')

    def close(self) -> None:
        try:
            if self.owned:
                self.drop()
        finally:
            self.con.close()


def _range_bound(x: Any) -> str:
    """One side of an int8range in text form: '' for ±Infinity, else the integer clamped into int8."""
    if x.is_infinite():
        return ""
    return str(max(-_INT8, min(_INT8, int(x))))


class PostgresTable(SQLTable):
    """``SQLTable`` plus the key guard (see the module docstring)."""

    def __init__(self, schema: Any, db: PostgresDB, capabilities: frozenset[str]):
        super().__init__(schema, db)
        self.capabilities = capabilities
        self._guard_rows: list[dict[str, Any]] = []
        self._guard: str | None = None

    @property
    def key_guard(self) -> str:
        if self._guard is None:
            rows = self.db.q("SELECT v FROM meta WHERE k = 'key_guard'")
            self._guard = rows[0][0] if rows else "on"
        return self._guard

    def reset(self) -> None:
        super().reset()
        self._guard_rows.clear()
        self._guard = None

    def guard_row(self, record: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any] | None:
        """The key_period row of a stored fact version, or None when it takes no part in the guard."""
        rel = record.get("relation")
        if "key_constraint" not in self.capabilities or rel in LIFECYCLE_RELATIONS or row["key_digest"] is None:
            return None
        if record.get("status") != "asserted" or record.get("rank") != "preferred":
            return None
        try:
            key = self.schema.key(rel)
        except Exception:  # noqa: BLE001 - an undeclared relation a trusted load kept has no key
            return None
        if not key:
            return None
        if key.get("temporal"):
            if "valid_time" not in self.capabilities:
                return None
            lo, hi = row["s_hi"], row["e_lo"]
            if not lo < hi:
                return None  # no definite validity: never holds on the key
            valid = f"[{_range_bound(lo)},{_range_bound(hi)})"
            if valid.startswith("[,"):
                valid = "(" + valid[1:]
            if _range_bound(lo) != "" and _range_bound(lo) == _range_bound(hi):
                return None  # clamped to an empty range
        else:
            valid = "(,)"
        return {"relation": rel, "key_digest": row["key_digest"], "valid": valid, "fact_id": record["id"]}

    def _added(self, record: Mapping[str, Any], row: Mapping[str, Any]) -> None:
        if record.get("kind") != "hyperedge" or self.key_guard != "on":
            return
        if not (self.bulk and self.bulk_empty):
            self.db.x("DELETE FROM key_period WHERE fact_id = ?", (record["id"],))
        g = self.guard_row(record, row)
        if self.bulk:
            self._guard_rows = [r for r in self._guard_rows if r["fact_id"] != record["id"]]
            if g is not None:
                self._guard_rows.append(g)
        elif g is not None:
            self.db.x("INSERT INTO key_period (relation, key_digest, valid, fact_id) VALUES (?, ?, ?::int8range, ?)",
                      (g["relation"], g["key_digest"], g["valid"], g["fact_id"]))

    def _flushed(self, ids: list[str]) -> None:
        rows, self._guard_rows = self._guard_rows, []
        if not rows or self.key_guard != "on":
            return
        self.db.x("SAVEPOINT key_guard")
        try:
            self.db.bulk_insert("key_period", rows)
        except self.db.psycopg.errors.IntegrityError:
            self.db.x("ROLLBACK TO SAVEPOINT key_guard")
            self.db.x("DELETE FROM key_period")
            self.db.put_meta("key_guard", "suspended")
            self._guard = "suspended"
        self.db.x("RELEASE SAVEPOINT key_guard")


class PostgresStore(SQLStore):
    """A C2 store in PostgreSQL (see the module docstring)."""

    ENGINE = "PostgreSQL"
    KIND = "client-server"
    INT64 = False  # numeric instants

    def __init__(self, schema: Any, *, conninfo: str, database: str = DATABASE, namespace: str | None = None,
                 clock: Any = None, capabilities: Iterable[str] | None = None, store_id: str = "postgres"):
        self.db = PostgresDB(conninfo, database, namespace)
        try:
            reopen = self.db.has_store()
            if not reopen:
                self.db.create()
            super().__init__(schema, table=lambda s: PostgresTable(s, self.db, self.capabilities), clock=clock,
                             capabilities=self.FLAGS if capabilities is None else capabilities, store_id=store_id)
            if reopen:
                self._read_documents()
        except BaseException:
            self.db.close()
            raise

    @property
    def key_guard(self) -> str:
        """``on``, or ``suspended`` after a trusted load whose data break the guarded rule."""
        return self._table.key_guard

    def engine_version(self) -> str:
        return self.db.q("SHOW server_version")[0][0]

    def close(self) -> None:
        self.db.close()


def factory(conninfo: str, database: str = DATABASE) -> Any:
    """A conformance factory: a fresh ``PostgresStore`` (its own schema, dropped by ``close``) per call."""

    def make(schema: Any, clock: Any) -> PostgresStore:
        return PostgresStore(schema, conninfo=conninfo, database=database, clock=clock)

    return make

