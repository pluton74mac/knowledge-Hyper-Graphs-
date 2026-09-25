"""The incidence-table layout (DESIGN §3.1; research 01 §2): the version table and the native reads in SQL, shared
by SQLite and PostgreSQL.

    meta(k, v)                                     -- latest transaction time, the kept header and documents
    entity_version(id, version, tx_from, tx_to, recorded_at, recorded_by, record)
    fact_version(id, version, tx_from, tx_to, recorded_at, recorded_by, relation, rel_kind, status, status_ref,
                 rank, visibility, key_digest, s_lo, s_hi, e_lo, e_hi, n_bindings, payload)
    binding(fact_id, version, bid, role, position, direction, value_kind, ref, ident, value_json, extensions)

Versions are immutable rows; a new version sets ``tx_to`` of its predecessor (a system-time period [tx_from, tx_to)
in microseconds, as in SQL:2011 system versioning). A dialect object gives the connection, the placeholder, the
instant column type and the bulk insert (``executemany`` in SQLite, ``COPY`` in PostgreSQL).
"""
from __future__ import annotations

import contextlib
import json
from typing import Any, Iterator, Mapping, Sequence

from khg_contracts.store import Where
from khg_contracts.store.table import Entry, TableStore

from .native import NativeReads
from .rows import BIND_COLS, FACT_COLS, Pat, assemble, binding_rows, entity_row, fact_row, native_binding
from .shared import AdapterMixin

__all__ = ["SQLStore", "SQLTable", "ddl"]

_UNSET: Any = object()
_CHUNK = 500


def ddl(instant_type: str, text: str = "TEXT") -> list[str]:
    """The tables and indexes, with the column type of the four instants (BIGINT or NUMERIC)."""
    return [
        f"CREATE TABLE meta (k {text} PRIMARY KEY, v {text})",
        f"""CREATE TABLE entity_version (id {text} NOT NULL, version INTEGER NOT NULL, tx_from BIGINT NOT NULL,
            tx_to BIGINT, recorded_at {text} NOT NULL, recorded_by {text} NOT NULL, record {text} NOT NULL,
            PRIMARY KEY (id, version))""",
        f"""CREATE TABLE fact_version (id {text} NOT NULL, version INTEGER NOT NULL, tx_from BIGINT NOT NULL,
            tx_to BIGINT, recorded_at {text} NOT NULL, recorded_by {text} NOT NULL, relation {text} NOT NULL,
            rel_kind {text} NOT NULL, status {text}, status_ref {text}, rank {text}, visibility {text},
            key_digest {text}, s_lo {instant_type} NOT NULL, s_hi {instant_type} NOT NULL,
            e_lo {instant_type} NOT NULL, e_hi {instant_type} NOT NULL, n_bindings INTEGER NOT NULL,
            payload {text} NOT NULL, PRIMARY KEY (id, version))""",
        f"""CREATE TABLE binding (fact_id {text} NOT NULL, version INTEGER NOT NULL, bid {text} NOT NULL,
            role {text} NOT NULL, position INTEGER, direction {text}, value_kind {text} NOT NULL, ref {text},
            ident {text}, value_json {text} NOT NULL, extensions {text}, PRIMARY KEY (fact_id, version, bid))""",
        "CREATE INDEX binding_ref ON binding (ref, role)",
        "CREATE INDEX binding_ident ON binding (role, ident)",
        "CREATE INDEX fact_key ON fact_version (relation, key_digest)",
        "CREATE INDEX fact_rel ON fact_version (relation, id)",
        "CREATE INDEX fact_ref ON fact_version (status_ref)",
    ]


class SQLTable:
    """The version table over the incidence tables (``store.table.VersionTableProtocol``).

    Inside a write it reads its own uncommitted rows (one connection, one transaction). During a bulk load it
    buffers the rows and writes them with the dialect's bulk insert when the load ends, or before any read that
    needs them. Entries read inside a write are cached until the write ends."""

    def __init__(self, schema: Any, db: Any):
        self.schema = schema
        self.db = db
        self.bulk = False
        self.bulk_empty = False  # set by the store: the bulk load began on an empty store
        self._cache: dict[tuple[str, int], Entry] = {}
        self._latest: Any = _UNSET
        self._latest_dirty = False
        self._buf: dict[str, list[dict[str, Any]]] = {"entity_version": [], "fact_version": [], "binding": []}
        self._buffered: dict[str, dict[str, Any]] = {}  # id -> its newest buffered version row

    # -- helpers
    def q(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        if self._buffered:
            self.flush()
        return self.db.q(sql, params)

    def reset(self) -> None:
        """Forget the caches and buffers (after a commit or a rollback)."""
        self._cache.clear()
        self._latest = _UNSET
        self._latest_dirty = False
        for rows in self._buf.values():
            rows.clear()
        self._buffered.clear()

    # -- latest
    @property
    def latest(self) -> int | None:
        if self._latest is _UNSET:
            rows = self.db.q("SELECT v FROM meta WHERE k = 'latest'")
            self._latest = int(rows[0][0]) if rows and rows[0][0] is not None else None
        return self._latest

    @latest.setter
    def latest(self, t: int | None) -> None:
        self._latest = t
        if self.bulk:
            self._latest_dirty = True
        else:
            self._write_latest()

    def _write_latest(self) -> None:
        self.db.put_meta("latest", None if self._latest is None else str(self._latest))
        self._latest_dirty = False

    # -- ids
    def __contains__(self, rid: object) -> bool:
        if not isinstance(rid, str):
            return False
        return bool(self.q("SELECT 1 FROM fact_version WHERE id = ? UNION ALL "
                           "SELECT 1 FROM entity_version WHERE id = ? LIMIT 1", (rid, rid)))

    def __len__(self) -> int:
        return int(self.q("SELECT count(*) FROM (SELECT id FROM fact_version UNION "
                          "SELECT id FROM entity_version) AS ids")[0][0])

    def ids(self) -> list[str]:
        return sorted(r[0] for r in self.q("SELECT id FROM fact_version UNION SELECT id FROM entity_version"))

    # -- versions
    def _entries(self, rid: str, cond: str = "", params: Sequence[Any] = (), order: str = "",
                 limit: str = "") -> list[Entry]:
        facts = self.q(f"SELECT {', '.join(FACT_COLS)} FROM fact_version WHERE id = ?{cond} ORDER BY version{order}"
                       f"{limit}", (rid, *params))
        if facts:
            out = []
            for row in facts:
                f = dict(zip(FACT_COLS, row))
                key = (rid, int(f["version"]))
                e = self._cache.get(key)
                if e is None:
                    rows = [dict(zip(BIND_COLS, b)) for b in self.q(
                        f"SELECT {', '.join(BIND_COLS)} FROM binding WHERE fact_id = ? AND version = ?",
                        (rid, f["version"]))]
                    e = self._cache[key] = Entry(assemble(f, rows), int(f["tx_from"]), self.schema)
                out.append(e)
            return out
        out = []
        for version, tx_from, text in self.q(f"SELECT version, tx_from, record FROM entity_version WHERE id = ?{cond} "
                                             f"ORDER BY version{order}{limit}", (rid, *params)):
            key = (rid, int(version))
            e = self._cache.get(key)
            if e is None:
                e = self._cache[key] = Entry(json.loads(text), int(tx_from), self.schema)
            out.append(e)
        return out

    def entries(self, rid: str) -> list[Entry]:
        return self._entries(rid)

    def current(self, rid: str) -> dict[str, Any] | None:
        es = self._entries(rid, order=" DESC", limit=" LIMIT 1")
        return es[0].record if es else None

    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None:
        if as_at is None:
            es = self._entries(rid, order=" DESC", limit=" LIMIT 1")
        else:
            es = self._entries(rid, " AND tx_from <= ?", (as_at,), " DESC", " LIMIT 1")
        return es[0] if es else None

    def latest_version(self, rid: str) -> int:
        rows = self.q("SELECT max(version) FROM fact_version WHERE id = ? UNION ALL "
                      "SELECT max(version) FROM entity_version WHERE id = ?", (rid, rid))
        return max((int(r[0]) for r in rows if r[0] is not None), default=0)

    # -- writes
    def add(self, record: dict[str, Any], t: int) -> Entry:
        rid = record["id"]
        if record["kind"] == "entity":
            table, rows = "entity_version", [entity_row(record, t)]
            binds: list[dict[str, Any]] = []
        else:
            table, rows = "fact_version", [fact_row(record, self.schema, t, as_instant=self.db.as_instant)]
            binds = binding_rows(record)
        prev = self._buffered.get(rid)
        if prev is not None:
            prev["tx_to"] = t
        elif not (self.bulk and self.bulk_empty):  # a bulk load into an empty store has no earlier rows
            self.db.x(f"UPDATE {table} SET tx_to = ? WHERE id = ? AND tx_to IS NULL", (t, rid))
        if self.bulk:
            self._buf[table] += rows
            self._buf["binding"] += binds
            self._buffered[rid] = rows[0]
        else:
            self.db.insert(table, rows)
            if binds:
                self.db.insert("binding", binds)
        self._added(record, rows[0])
        self.latest = t if self.latest is None else max(self.latest, t)
        e = Entry(record, t, self.schema)
        self._cache[(rid, int(record["version"]))] = e
        return e

    def _added(self, record: Mapping[str, Any], row: Mapping[str, Any]) -> None:
        """A hook after each version is written (PostgreSQL maintains its key guard here)."""

    def flush(self) -> None:
        """Write the buffered rows of a bulk load (and the latest transaction time)."""
        buffered, self._buffered = self._buffered, {}
        for table in ("entity_version", "fact_version", "binding"):
            rows = self._buf[table]
            if rows:
                self.db.bulk_insert(table, rows)
                rows.clear()
        if buffered:
            self._flushed(list(buffered))
        if self._latest_dirty:
            self._write_latest()

    def _flushed(self, ids: list[str]) -> None:
        """A hook after a bulk load's rows are written."""

    # -- indexes
    def by_node(self, node: str) -> set[str]:
        return {r[0] for r in self.q("SELECT DISTINCT fact_id FROM binding WHERE ref = ?", (node,))}

    def by_relation(self, relation: str) -> set[str]:
        return {r[0] for r in self.q("SELECT DISTINCT id FROM fact_version WHERE relation = ?", (relation,))}

    def by_key(self, relation: str, digest: str) -> set[str]:
        return {r[0] for r in self.q("SELECT DISTINCT id FROM fact_version WHERE relation = ? AND key_digest = ?",
                                     (relation, digest))}

    def by_ref(self, lifecycle_id: str) -> set[str]:
        return {r[0] for r in self.q("SELECT DISTINCT id FROM fact_version WHERE status_ref = ?", (lifecycle_id,))}

    def __iter__(self) -> Iterator[str]:
        return iter(self.ids())


class SQLStore(AdapterMixin, NativeReads, TableStore):
    """A C2 store on the incidence tables: ``TableStore``'s write path over ``SQLTable``, one database transaction
    per write, and the reads in SQL. Subclasses give ``_connect`` (a dialect object, see ``sqlite.SQLiteDB``)."""

    def _open_table(self, db: Any) -> SQLTable:
        return SQLTable(self.schema, db)

    # -- transactions
    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        self.db.begin()
        try:
            yield
            self._table.flush()
        except BaseException:
            self.db.rollback()
            self._table.reset()
            self._restore_documents()
            raise
        self.db.commit()
        self._table.reset()

    def load(self, container: Any, **kwargs: Any) -> Any:
        """Trusted bulk import (C2 ``load``): ``TableStore``'s checks, the rows written in bulk, the kept header in
        ``meta``; one transaction."""
        with self.writing():
            self._table.bulk_empty = len(self._table) == 0
            self._table.bulk = True
            try:
                report = TableStore.load(self, container, **kwargs)
                self._table.flush()
            finally:
                self._table.bulk = False
            self._save_documents()
        return report

    def _save_documents(self) -> None:
        self.db.put_meta("header", json.dumps(self._header, ensure_ascii=False))
        self.db.put_meta("documents", json.dumps(self._documents, ensure_ascii=False))

    def _read_documents(self) -> None:
        rows = dict(self.db.q("SELECT k, v FROM meta WHERE k IN ('header', 'documents')"))
        self._header = json.loads(rows["header"]) if rows.get("header") else None
        self._documents = json.loads(rows["documents"]) if rows.get("documents") else []

    def _restore_documents(self) -> None:
        with contextlib.suppress(Exception):
            self._read_documents()

    # -- the parts of a query
    def _as_of(self, as_of: int | None) -> Any:
        return None if as_of is None else self.db.query_instant(as_of)

    @staticmethod
    def _current(alias: str, t: int | None, params: list[Any]) -> str:
        if t is None:
            return f"{alias}.tx_to IS NULL"
        params += [t, t]
        return f"{alias}.tx_from <= ? AND ({alias}.tx_to IS NULL OR {alias}.tx_to > ?)"

    def _filters(self, alias: str, where: Where, as_of: int | None, params: list[Any]) -> str:
        parts = []
        for col, values in (("status", where.status), ("rank", where.rank), ("visibility", where.visibility),
                            ("rel_kind", where.kinds)):
            vs = sorted(values)
            if not vs:
                return "1 = 0"
            parts.append(f"{alias}.{col} IN ({', '.join('?' for _ in vs)})")
            params += vs
        if as_of is not None:
            lo, hi = ("s_hi", "e_lo") if where.valid_mode == "definite" else ("s_lo", "e_hi")
            parts.append(f"{alias}.{lo} <= ? AND ? < {alias}.{hi}")
            params += [self._as_of(as_of)] * 2
        return " AND ".join(parts)

    @staticmethod
    def _page_sql(alias: str, after: str | None, limit: int | None, params: list[Any]) -> tuple[str, str]:
        cond, tail = "", f" ORDER BY {alias}.id"
        if after is not None:
            cond = f" AND {alias}.id > ?"
            params.append(after)
        if limit is not None:
            tail += f" LIMIT {int(limit)}"
        return cond, tail

    # -- native reads
    def _fact_rows(self, ids: Sequence[str], t: int | None) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for i in range(0, len(ids), _CHUNK):
            chunk = list(ids[i:i + _CHUNK])
            params: list[Any] = list(chunk)
            cur = self._current("fv", t, params)
            for row in self.db.q(f"SELECT {', '.join('fv.' + c for c in FACT_COLS)} FROM fact_version fv WHERE "
                                 f"fv.id IN ({', '.join('?' for _ in chunk)}) AND {cur}", params):
                f = dict(zip(FACT_COLS, row))
                out[f["id"]] = f
        return out

    def _binding_rows(self, keys: Sequence[tuple[str, int]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
        out: dict[tuple[str, int], list[dict[str, Any]]] = {k: [] for k in keys}
        ids = sorted({k[0] for k in keys})
        for i in range(0, len(ids), _CHUNK):
            chunk = ids[i:i + _CHUNK]
            for row in self.db.q(f"SELECT {', '.join(BIND_COLS)} FROM binding WHERE fact_id IN "
                                 f"({', '.join('?' for _ in chunk)})", chunk):
                b = dict(zip(BIND_COLS, row))
                key = (b["fact_id"], int(b["version"]))
                if key in out:
                    out[key].append(b)
        return out

    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        facts = self._fact_rows(ids, t)
        binds = self._binding_rows([(f["id"], int(f["version"])) for f in facts.values()])
        entities: dict[str, dict[str, Any]] = {}
        rest = [i for i in ids if i not in facts]
        for i in range(0, len(rest), _CHUNK):
            chunk = rest[i:i + _CHUNK]
            params: list[Any] = list(chunk)
            cur = self._current("ev", t, params)
            for rid, text in self.db.q(f"SELECT ev.id, ev.record FROM entity_version ev WHERE ev.id IN "
                                       f"({', '.join('?' for _ in chunk)}) AND {cur}", params):
                entities[rid] = json.loads(text)
        out = []
        for i in ids:
            if i in facts:
                f = facts[i]
                out.append(assemble(f, binds[(i, int(f["version"]))]))
            elif i in entities:
                out.append(entities[i])
        return out

    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
        if version is None:
            got = self._n_records([id], t)
            return got[0] if got else None
        cond, params = " AND version = ?", [id, version]
        if t is not None:
            cond += " AND tx_from <= ?"
            params.append(t)
        rows = self.db.q(f"SELECT {', '.join(FACT_COLS)} FROM fact_version WHERE id = ?{cond}", params)
        if rows:
            f = dict(zip(FACT_COLS, rows[0]))
            return assemble(f, self._binding_rows([(id, int(f["version"]))])[(id, int(f["version"]))])
        rows = self.db.q(f"SELECT record FROM entity_version WHERE id = ?{cond}", params)
        return json.loads(rows[0][0]) if rows else None

    def _n_versions(self, id: str, t: int | None = None) -> list[dict[str, Any]]:
        cond, params = ("", [id]) if t is None else (" AND tx_from <= ?", [id, t])
        facts = [dict(zip(FACT_COLS, r)) for r in self.db.q(
            f"SELECT {', '.join(FACT_COLS)} FROM fact_version WHERE id = ?{cond} ORDER BY version", params)]
        if facts:
            binds = self._binding_rows([(id, int(f["version"])) for f in facts])
            return [assemble(f, binds[(id, int(f["version"]))]) for f in facts]
        return [json.loads(r[0]) for r in self.db.q(
            f"SELECT record FROM entity_version WHERE id = ?{cond} ORDER BY version", params)]

    def _n_ids(self, t: int | None) -> list[str]:
        if t is None:
            rows = self.db.q("SELECT id FROM entity_version UNION SELECT id FROM fact_version")
        else:
            rows = self.db.q("SELECT id FROM entity_version WHERE tx_from <= ? UNION "
                             "SELECT id FROM fact_version WHERE tx_from <= ?", (t, t))
        return sorted(r[0] for r in rows)

    def _n_is_fact(self, id: str) -> bool:
        return bool(self.db.q("SELECT 1 FROM fact_version WHERE id = ? LIMIT 1", (id,)))

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        params: list[Any] = [node]
        sub = "b.ref = ?"
        if role is not None:
            sub += " AND b.role = ?"
            params.append(role)
        cur = self._current("fv", t, params)
        filt = self._filters("fv", where, as_of, params)
        rel = ""
        if relation is not None:
            rel = " AND fv.relation = ?"
            params.append(relation)
        cond, tail = self._page_sql("fv", after, limit, params)
        sql = (f"SELECT fv.id FROM fact_version fv WHERE EXISTS (SELECT 1 FROM binding b WHERE b.fact_id = fv.id "
               f"AND b.version = fv.version AND {sub}) AND {cur} AND {filt}{rel}{cond}{tail}")
        return [r[0] for r in self.db.q(sql, params)]

    def _n_find(self, relation: str, pats: list[Pat], match: str, where: Where, t: int | None, as_of: int | None,
                after: str | None, limit: int | None) -> list[str]:
        params: list[Any] = []
        joins = []
        for i, p in enumerate(pats, 1):
            on = [f"b{i}.fact_id = fv.id", f"b{i}.version = fv.version", f"b{i}.role = ?"]
            params.append(p.role)
            if p.position is not None:
                on.append(f"b{i}.position = ?")
                params.append(p.position)
            if p.kind == "value":
                on.append(f"b{i}.ident = ?")
                params.append(p.ident)
            elif p.kind == "any_unbound":
                on.append(f"b{i}.value_kind = 'unbound'")
            on += [f"b{i}.bid <> b{j}.bid" for j in range(1, i)]  # injective: distinct bindings
            joins.append(f"JOIN binding b{i} ON " + " AND ".join(on))
        params.append(relation)
        cur = self._current("fv", t, params)
        filt = self._filters("fv", where, as_of, params)
        exact = ""
        if match == "exact":
            exact = " AND fv.n_bindings = ?"
            params.append(len(pats))
        cond, tail = self._page_sql("fv", after, limit, params)
        sql = (f"SELECT DISTINCT fv.id FROM fact_version fv {' '.join(joins)} WHERE fv.relation = ? AND {cur} AND "
               f"{filt}{exact}{cond}{tail}")
        return [r[0] for r in self.db.q(sql, params)]

    def _n_key(self, relation: str, digest: str, where: Where, t: int | None, as_of: int | None) -> list[str]:
        params: list[Any] = [relation, digest]
        cur = self._current("fv", t, params)
        filt = self._filters("fv", where, as_of, params)
        return [r[0] for r in self.db.q(f"SELECT fv.id FROM fact_version fv WHERE fv.relation = ? AND "
                                        f"fv.key_digest = ? AND {cur} AND {filt} ORDER BY fv.id", params)]

    # -- fidelity number 2
    def native_bindings(self, rid: str) -> list[dict[str, Any]] | None:
        """The bindings of the current version of fact ``rid`` from the ``binding`` rows alone (not ``payload``)."""
        rows = self.db.q("SELECT version FROM fact_version WHERE id = ? AND tx_to IS NULL", (rid,))
        if not rows:
            return None
        return [native_binding(dict(zip(BIND_COLS, r))) for r in self.db.q(
            f"SELECT {', '.join(BIND_COLS)} FROM binding WHERE fact_id = ? AND version = ?", (rid, rows[0][0]))]

