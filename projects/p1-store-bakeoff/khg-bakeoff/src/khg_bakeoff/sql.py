"""The incidence-table layout (DESIGN §3.1; research 01 §2): the version table and the native reads in SQL, shared
by SQLite and PostgreSQL.

    meta(k, v)                                     -- latest transaction time, the kept header and documents
    entity_version(id, version, tx_from, tx_to, recorded_at, recorded_by, record)
    fact_version(id, version, tx_from, tx_to, recorded_at, recorded_by, relation, rel_kind, status, status_ref,
                 rank, visibility, key_digest, s_lo, s_hi, e_lo, e_hi, n_bindings, payload)
    binding(fact_id, version, bid, role, position, direction, value_kind, ref, ident, value_json, extensions)

Versions are immutable rows; a new version sets ``tx_to`` of its predecessor (a system-time period [tx_from, tx_to)
in microseconds, as in SQL:2011 system versioning). A dialect object gives the connection, the placeholder, the
instant column type, the text column type (PostgreSQL: ``COLLATE "C"``), the bulk insert (``executemany`` in
SQLite, ``COPY`` in PostgreSQL) and the batched close of previous versions; it counts every statement it sends
(``trips``).

**Writes** are buffered and written when the write ends, or before any query of the write that reads them: the
rows in bulk, then ``tx_to`` of the versions they close in one statement per chunk. **A load** first reads the
versions of the ids it brings in one query per table and chunk (``prefetch``, the optional member of the version
table): none at all when the store is empty.
"""
from __future__ import annotations

import contextlib
import json
from typing import Any, Iterable, Iterator, Mapping, Sequence

from khg_contracts import jsonio
from khg_contracts.store import Where
from khg_contracts.store.table import Entry, TableStore

from .native import NativeReads
from .rows import BIND_COLS, FACT_COLS, Pat, binding_rows, entity_row, fact_row, native_binding, record_of
from .shared import AdapterMixin

__all__ = ["CHUNK", "SQLStore", "SQLTable", "ddl"]

_UNSET: Any = object()
#: Ids per query when a read or a prefetch names them.
CHUNK = 500
_TABLES = ("entity_version", "fact_version", "binding")


def ddl(instant_type: str, text: str = "TEXT") -> list[str]:
    """The tables and indexes, with the column type of the four instants (BIGINT or NUMERIC) and of every text
    column (PostgreSQL gives ``TEXT COLLATE "C"``, so ids order by code point whatever the database's locale)."""
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


def _chunks(items: Sequence[Any], size: int = CHUNK) -> Iterator[list[Any]]:
    for i in range(0, len(items), size):
        yield list(items[i:i + size])


def _marks(n: int) -> str:
    return ", ".join("?" for _ in range(n))


class SQLTable:
    """The version table over the incidence tables (``store.table.VersionTableProtocol``, with ``prefetch``).

    Inside a write it reads its own uncommitted rows (one connection, one transaction). Rows are buffered and
    written by ``flush``: when the write ends, or before any query that reads the tables. Entries read inside a
    write are cached until the write ends; the ids a load prefetched are answered from memory."""

    def __init__(self, schema: Any, db: Any):
        self.schema = schema
        self.db = db
        self.bulk = False  # a trusted load is in progress (set by the store)
        self.bulk_empty = False  # ... and it began on an empty store
        self._cache: dict[tuple[str, int], Entry] = {}
        self._known: dict[str, list[Entry]] = {}  # prefetched ids: every version, this write's included
        self._held: set[str] = set()  # prefetched ids the store held before this write
        self._latest: Any = _UNSET
        self._latest_dirty = False
        self._buf: dict[str, list[dict[str, Any]]] = {t: [] for t in _TABLES}
        self._buffered: dict[str, dict[str, Any]] = {}  # id -> its newest buffered version row
        self._closes: dict[str, list[tuple[int, str]]] = {"entity_version": [], "fact_version": []}

    # -- helpers
    def pending(self) -> bool:
        return bool(self._buffered or self._closes["entity_version"] or self._closes["fact_version"])

    def q(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        """A query over any id: the buffered rows are written first."""
        if self.pending():
            self.flush(final=False)
        return self.db.q(sql, params)

    def q_id(self, rid: str, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        """A query about the id ``rid`` only: the buffered rows are written first when one is of ``rid``."""
        if rid in self._buffered:
            self.flush(final=False)
        return self.db.q(sql, params)

    def reset(self) -> None:
        """Forget the caches and buffers (after a commit or a rollback)."""
        self._cache.clear()
        self._known.clear()
        self._held.clear()
        self._latest = _UNSET
        self._latest_dirty = False
        for rows in self._buf.values():
            rows.clear()
        self._buffered.clear()
        for closes in self._closes.values():
            closes.clear()

    def is_empty(self) -> bool:
        """Whether the store holds no version (one query)."""
        rows = self.q("SELECT CASE WHEN EXISTS (SELECT 1 FROM fact_version) OR EXISTS (SELECT 1 FROM entity_version) "
                      "THEN 1 ELSE 0 END")
        return not rows[0][0]

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
        self._latest_dirty = True  # written by flush

    # -- ids
    def __contains__(self, rid: object) -> bool:
        if not isinstance(rid, str):
            return False
        if rid in self._known:
            return bool(self._known[rid])
        return bool(self.q_id(rid, "SELECT 1 FROM fact_version WHERE id = ? UNION ALL "
                                   "SELECT 1 FROM entity_version WHERE id = ? LIMIT 1", (rid, rid)))

    def __len__(self) -> int:
        return int(self.q("SELECT count(*) FROM (SELECT id FROM fact_version UNION "
                          "SELECT id FROM entity_version) AS ids")[0][0])

    def ids(self) -> list[str]:
        return sorted(r[0] for r in self.q("SELECT id FROM fact_version UNION SELECT id FROM entity_version"))

    # -- prefetch (the optional member; TableStore.load calls it)
    def prefetch(self, records: Iterable[Mapping[str, Any]]) -> None:
        """Read every version of the ids a load brings: three queries per ``CHUNK`` ids, none on an empty
        store. ``entries``, ``current``, ``entry_at`` and ``latest_version`` then answer them from memory."""
        ids = sorted({jsonio.nfc(r["id"]) for r in records} - set(self._known))
        for rid in ids:
            self._known[rid] = []
        if not ids or (self.bulk and self.bulk_empty):
            return
        for chunk in _chunks(ids):
            facts = [dict(zip(FACT_COLS, row)) for row in self.q(
                f"SELECT {', '.join(FACT_COLS)} FROM fact_version WHERE id IN ({_marks(len(chunk))}) "
                "ORDER BY id, version", chunk)]
            binds: dict[tuple[str, int], list[dict[str, Any]]] = {}
            if facts:
                for row in self.q(f"SELECT {', '.join(BIND_COLS)} FROM binding WHERE fact_id IN "
                                  f"({_marks(len(chunk))})", chunk):
                    b = dict(zip(BIND_COLS, row))
                    binds.setdefault((b["fact_id"], int(b["version"])), []).append(b)
            for f in facts:
                key = (f["id"], int(f["version"]))
                self._known[f["id"]].append(Entry(record_of(f, binds.get(key, [])), int(f["tx_from"]),
                                                  self.schema))
            for rid, version, tx_from, text in self.q(
                    f"SELECT id, version, tx_from, record FROM entity_version WHERE id IN ({_marks(len(chunk))}) "
                    "ORDER BY id, version", chunk):
                self._known[rid].append(Entry(record_of({"record": text}), int(tx_from), self.schema))
        self._held |= {rid for rid in ids if self._known[rid]}

    # -- versions
    def _entries(self, rid: str, cond: str = "", params: Sequence[Any] = (), order: str = "",
                 limit: str = "") -> list[Entry]:
        facts = self.q_id(rid, f"SELECT {', '.join(FACT_COLS)} FROM fact_version WHERE id = ?{cond} "
                               f"ORDER BY version{order}{limit}", (rid, *params))
        if facts:
            out = []
            for row in facts:
                f = dict(zip(FACT_COLS, row))
                key = (rid, int(f["version"]))
                e = self._cache.get(key)
                if e is None:
                    rows = [dict(zip(BIND_COLS, b)) for b in self.q_id(
                        rid, f"SELECT {', '.join(BIND_COLS)} FROM binding WHERE fact_id = ? AND version = ?",
                        (rid, f["version"]))]
                    e = self._cache[key] = Entry(record_of(f, rows), int(f["tx_from"]), self.schema)
                out.append(e)
            return out
        out = []
        for version, tx_from, text in self.q_id(rid, f"SELECT version, tx_from, record FROM entity_version WHERE "
                                                     f"id = ?{cond} ORDER BY version{order}{limit}", (rid, *params)):
            key = (rid, int(version))
            e = self._cache.get(key)
            if e is None:
                e = self._cache[key] = Entry(record_of({"record": text}), int(tx_from), self.schema)
            out.append(e)
        return out

    def entries(self, rid: str) -> list[Entry]:
        if rid in self._known:
            return list(self._known[rid])
        return self._entries(rid)

    def current(self, rid: str) -> dict[str, Any] | None:
        e = self.entry_at(rid)
        return e.record if e is not None else None

    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None:
        if rid in self._known:
            for e in reversed(self._known[rid]):
                if as_at is None or e.t <= as_at:
                    return e
            return None
        if as_at is None:
            es = self._entries(rid, order=" DESC", limit=" LIMIT 1")
        else:
            es = self._entries(rid, " AND tx_from <= ?", (as_at,), " DESC", " LIMIT 1")
        return es[0] if es else None

    def latest_version(self, rid: str) -> int:
        if rid in self._known:
            es = self._known[rid]
            return int(es[-1].record.get("version", len(es))) if es else 0
        rows = self.q_id(rid, "SELECT max(version) FROM fact_version WHERE id = ? UNION ALL "
                              "SELECT max(version) FROM entity_version WHERE id = ?", (rid, rid))
        return max((int(r[0]) for r in rows if r[0] is not None), default=0)

    # -- writes
    def add(self, record: dict[str, Any], t: int) -> Entry:
        rid = record["id"]
        if record["kind"] == "entity":
            table, row = "entity_version", entity_row(record, t)
            binds: list[dict[str, Any]] = []
        else:
            table, row = "fact_version", fact_row(record, self.schema, t, as_instant=self.db.as_instant)
            binds = binding_rows(record)
        prev = self._buffered.get(rid)
        if prev is not None:  # the previous version is still in the buffer
            prev["tx_to"] = t
        elif rid in self._known:
            if rid in self._held:  # a version is already written: close it at the flush
                self._closes[table].append((t, rid))
        elif not (self.bulk and self.bulk_empty):
            self._closes[table].append((t, rid))  # closes nothing when the id is new
        self._buf[table].append(row)
        self._buf["binding"] += binds
        self._buffered[rid] = row
        self._added(record, row)
        self.latest = t if self.latest is None else max(self.latest, t)
        e = Entry(record, t, self.schema)
        self._cache[(rid, int(record["version"]))] = e
        if rid in self._known:
            self._known[rid].append(e)
        return e

    def _added(self, record: Mapping[str, Any], row: Mapping[str, Any]) -> None:
        """A hook after each version is buffered (PostgreSQL buffers its key-guard change here)."""

    def flush(self, final: bool = True) -> None:
        """Write what the write buffered: close the previous versions, then insert the rows in bulk, then the
        latest transaction time. ``final``: the write is ending (the store's flush before its commit, or a load's),
        not a query of the write that needs the rows."""
        buffered, self._buffered = self._buffered, {}
        self._held |= {rid for rid in buffered if rid in self._known}  # written from here on
        for table, closes in self._closes.items():
            if closes:
                self.db.close_versions(table, closes)
                self._closes[table] = []
        for table in _TABLES:
            rows = self._buf[table]
            if rows:
                self.db.bulk_insert(table, rows)
                self._buf[table] = []
        self._flushed(list(buffered), final)
        if self._latest_dirty:
            self.db.put_meta("latest", None if self._latest is None else str(self._latest))
            self._latest_dirty = False

    def _flushed(self, ids: list[str], final: bool) -> None:
        """A hook after the rows are written (PostgreSQL writes its key guard here when ``final``)."""

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
    per write, and the reads in SQL. Subclasses give ``db`` (a dialect object, see ``sqlite.SQLiteDB``)."""

    db: Any

    @property
    def trips(self) -> Any:
        return self.db.trips

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
            raise
        try:
            self.db.commit()
        finally:
            self._table.reset()

    def load(self, container: Any, **kwargs: Any) -> Any:
        """Trusted bulk import (C2 ``load``): ``TableStore``'s checks over the prefetched ids, the rows written in
        bulk, the kept header in ``meta``; one transaction."""
        with self.writing():
            table: SQLTable = self._table
            table.bulk_empty = table.is_empty()
            table.bulk = True
            try:
                report = TableStore.load(self, container, **kwargs)
                table.flush()
            finally:
                table.bulk = False
            self._save_header()
        return report

    def _save_header(self) -> None:
        self.db.put_meta("header", jsonio.canonical(self.kept_header))
        self.db.put_meta("documents", jsonio.canonical(self.kept_documents))

    def _read_header(self) -> None:
        rows = dict(self.db.q("SELECT k, v FROM meta WHERE k IN ('header', 'documents')"))
        self.kept_header = json.loads(rows["header"]) if rows.get("header") else None
        self.kept_documents = json.loads(rows["documents"]) if rows.get("documents") else []

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
            parts.append(f"{alias}.{col} IN ({_marks(len(vs))})")
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

    # -- reading records (rows, then rows.record_of)
    def _fact_rows(self, cond: str, params: Sequence[Any]) -> tuple[list[dict[str, Any]], dict[tuple, list]]:
        """The fact rows ``fv`` that ``cond`` selects, and the binding rows of exactly those versions (two
        queries)."""
        facts = [dict(zip(FACT_COLS, row)) for row in self.db.q(
            f"SELECT {', '.join('fv.' + c for c in FACT_COLS)} FROM fact_version fv WHERE {cond}", params)]
        binds: dict[tuple, list] = {}
        if facts:
            for row in self.db.q(f"SELECT {', '.join('b.' + c for c in BIND_COLS)} FROM binding b JOIN fact_version fv "
                                 f"ON b.fact_id = fv.id AND b.version = fv.version WHERE {cond}", params):
                b = dict(zip(BIND_COLS, row))
                binds.setdefault((b["fact_id"], int(b["version"])), []).append(b)
        return facts, binds

    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        got: dict[str, dict[str, Any]] = {}
        for chunk in _chunks(list(ids)):
            params: list[Any] = list(chunk)
            cond = f"fv.id IN ({_marks(len(chunk))}) AND {self._current('fv', t, params)}"
            facts, binds = self._fact_rows(cond, params)
            for f in facts:
                got[f["id"]] = record_of(f, binds.get((f["id"], int(f["version"])), []))
            rest = [i for i in chunk if i not in got]
            if rest:
                params = list(rest)
                cur = self._current("ev", t, params)
                for rid, text in self.db.q(f"SELECT ev.id, ev.record FROM entity_version ev WHERE ev.id IN "
                                           f"({_marks(len(rest))}) AND {cur}", params):
                    got[rid] = record_of({"record": text})
        return [got[i] for i in ids if i in got]

    def _n_scan(self, t: int | None, history: bool) -> list[dict[str, Any]]:
        params: list[Any] = []
        if history:
            cond = "1 = 1" if t is None else "fv.tx_from <= ?"
            params = [] if t is None else [t]
        else:
            cond = self._current("fv", t, params)
        facts, binds = self._fact_rows(cond, params)
        out = [(f["id"], int(f["version"]), record_of(f, binds.get((f["id"], int(f["version"])), [])))
               for f in facts]
        eparams: list[Any] = []
        if history:
            econd = "1 = 1" if t is None else "ev.tx_from <= ?"
            eparams = [] if t is None else [t]
        else:
            econd = self._current("ev", t, eparams)
        for rid, version, text in self.db.q(f"SELECT ev.id, ev.version, ev.record FROM entity_version ev WHERE {econd}",
                                            eparams):
            out.append((rid, int(version), record_of({"record": text})))
        out.sort(key=lambda x: (x[0], x[1]))
        return [r for _, _, r in out]

    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
        if not isinstance(id, str):
            return None
        if version is None:
            got = self._n_records([id], t)
            return got[0] if got else None
        params: list[Any] = [id, version]
        cond = "fv.id = ? AND fv.version = ?"
        if t is not None:
            cond += " AND fv.tx_from <= ?"
            params.append(t)
        facts, binds = self._fact_rows(cond, params)
        if facts:
            f = facts[0]
            return record_of(f, binds.get((f["id"], int(f["version"])), []))
        rows = self.db.q(f"SELECT record FROM entity_version ev WHERE {cond.replace('fv.', 'ev.')}", params)
        return record_of({"record": rows[0][0]}) if rows else None

    def _n_versions(self, id: str, t: int | None = None) -> list[dict[str, Any]]:
        if not isinstance(id, str):
            return []
        cond, params = ("fv.id = ?", [id]) if t is None else ("fv.id = ? AND fv.tx_from <= ?", [id, t])
        facts, binds = self._fact_rows(cond, params)
        if facts:
            facts.sort(key=lambda f: int(f["version"]))
            return [record_of(f, binds.get((f["id"], int(f["version"])), [])) for f in facts]
        return [record_of({"record": r[0]}) for r in self.db.q(
            f"SELECT ev.record FROM entity_version ev WHERE {cond.replace('fv.', 'ev.')} ORDER BY ev.version", params)]

    def _n_is_fact(self, id: str) -> bool:
        return bool(self.db.q("SELECT 1 FROM fact_version WHERE id = ? LIMIT 1", (id,)))

    def _incident_where(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                        as_of: int | None, params: list[Any]) -> str:
        params.append(node)
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
        return (f"EXISTS (SELECT 1 FROM binding b WHERE b.fact_id = fv.id AND b.version = fv.version AND {sub}) "
                f"AND {cur} AND {filt}{rel}")

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        params: list[Any] = []
        cond = self._incident_where(node, role, relation, where, t, as_of, params)
        page, tail = self._page_sql("fv", after, limit, params)
        return [r[0] for r in self.db.q(f"SELECT fv.id FROM fact_version fv WHERE {cond}{page}{tail}", params)]

    def _n_count(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                 as_of: int | None) -> int:
        params: list[Any] = []
        cond = self._incident_where(node, role, relation, where, t, as_of, params)
        return int(self.db.q(f"SELECT count(*) FROM fact_version fv WHERE {cond}", params)[0][0])

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

    def _n_bound_by(self, relation: str, role: str, idents: Sequence[str], where: Where, t: int | None,
                    as_of: int | None) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for chunk in _chunks(list(idents)):
            params: list[Any] = [relation, role, *chunk]
            cur = self._current("fv", t, params)
            filt = self._filters("fv", where, as_of, params)
            for ident, rid in self.db.q(
                    f"SELECT DISTINCT b.ident, fv.id FROM fact_version fv JOIN binding b ON b.fact_id = fv.id AND "
                    f"b.version = fv.version WHERE fv.relation = ? AND b.role = ? AND b.ident IN "
                    f"({_marks(len(chunk))}) AND {cur} AND {filt} ORDER BY fv.id", params):
                out.setdefault(ident, []).append(rid)
        return out

    # -- fidelity number 2
    def native_bindings(self, rid: str) -> list[dict[str, Any]] | None:
        """The bindings of the current version of fact ``rid`` from the ``binding`` rows' structural columns and
        stored identities (``rows.native_binding``: not ``value_json``, not ``payload``)."""
        rows = self.db.q("SELECT version FROM fact_version WHERE id = ? AND tx_to IS NULL", (rid,))
        if not rows:
            return None
        return [native_binding(dict(zip(BIND_COLS, r))) for r in self.db.q(
            f"SELECT {', '.join(BIND_COLS)} FROM binding WHERE fact_id = ? AND version = ?", (rid, rows[0][0]))]
