"""The property-graph adapter (DESIGN §3.3): the bipartite layout in Neo4j Community through the official driver
(research 01 §4).

``Neo4jStore(schema, *, uri, auth=None, database="neo4j", namespace=None, clock=None, capabilities=None,
store_id="neo4j")``. Neo4j Community holds one user database, so every node of a store carries the store's
namespace label (``namespace=None``: a fresh one whose nodes ``close`` deletes; the conformance runner opens a second
store while the first is open).

**Layout.** Versions are nodes, so transaction time is kept; bindings point at identity nodes, so a new version of a
nested fact does not orphan its referrers::

    (:Node {id, kind})                                    one per entity id and per fact id
    (:Version {id, version, tx_from, tx_to, kind, relation, rel_kind, status, status_ref, rank, visibility,
               key_digest, s_lo, s_hi, e_lo, e_hi, n_bindings, payload | record, recorded_at, recorded_by})
        -[:VERSION_OF]->(:Node)
    (:Version)-[:BINDS {bid, role, position, direction, value_kind, ref, ident, value_json, extensions}]->(t)
        t = the (:Node) of an entity or fact value | a shared (:Literal {ident}) | a per-binding (:Special {key})
    (:Meta {latest, header, documents})

Range indexes: ``:Version(id)``, ``:Version(relation, key_digest)``, ``:Version(relation)``, ``:Node(id)``,
``:Literal(ident)``, and on the relationship property ``BINDS(role)`` and ``BINDS(role, ident)`` (research 01
§4.2: Neo4j indexes relationship properties). Instants are int64 with the ±2^62 guard (ruling 4).

**Writes.** Each write is one explicit transaction; the table reads through it, so it sees its own writes. Versions
are buffered and written with ``UNWIND`` batches of ``BATCH`` rows when the write ends (or before a read of it). A
load reads the stored versions of the ids it brings in one query per batch (``prefetch``; none on an empty store).
**Reads** fetch the versions of one call in one query (``UNWIND`` of the ids), rebuilt by ``rows.record_of``.
``trips`` counts every query, and the begin and commit of each write.
"""
from __future__ import annotations

import atexit
import contextlib
import itertools
import json
import os
import re
from typing import Any, Iterable, Iterator, Mapping, Sequence

from khg_contracts import jsonio
from khg_contracts.store import Where
from khg_contracts.store.table import Entry, TableStore

from .native import NativeReads
from .rows import (BIND_COLS, FACT_COLS, Pat, binding_rows, entity_row, fact_row, native_binding, query_instant,
                   record_of)
from .shared import AdapterMixin, Trips

__all__ = ["BATCH", "Neo4jStore", "Neo4jTable", "factory", "partition"]

BATCH = 500
_UNSET: Any = object()
_seq = itertools.count(1)
_drivers: dict[tuple[str, Any], Any] = {}
_LABEL = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,60}")
_WRITES = re.compile(r"\b(CREATE|MERGE|SET|DELETE)\b")
INDEXES = [
    "CREATE INDEX khg_version_id IF NOT EXISTS FOR (v:Version) ON (v.id)",
    "CREATE INDEX khg_version_key IF NOT EXISTS FOR (v:Version) ON (v.relation, v.key_digest)",
    "CREATE INDEX khg_version_rel IF NOT EXISTS FOR (v:Version) ON (v.relation)",
    "CREATE INDEX khg_node_id IF NOT EXISTS FOR (n:Node) ON (n.id)",
    "CREATE INDEX khg_literal_ident IF NOT EXISTS FOR (n:Literal) ON (n.ident)",
    "CREATE INDEX khg_binds_role IF NOT EXISTS FOR ()-[e:BINDS]-() ON (e.role)",
    "CREATE INDEX khg_binds_role_ident IF NOT EXISTS FOR ()-[e:BINDS]-() ON (e.role, e.ident)",
]
#: One version with its bindings, as ``properties``: the rows ``rows.record_of`` rebuilds.
_WITH_BINDINGS = ("OPTIONAL MATCH (v)-[e:BINDS]->() WITH v, collect(properties(e)) AS bs ORDER BY v.id, v.version "
                  "RETURN properties(v) AS v, bs")


def driver(uri: str, auth: Any = None) -> Any:
    """One driver per server and credentials, closed at exit."""
    import neo4j

    key = (uri, auth)
    if key not in _drivers:
        _drivers[key] = neo4j.GraphDatabase.driver(uri, auth=auth, notifications_min_severity="OFF")
    return _drivers[key]


@atexit.register
def _close_drivers() -> None:
    for d in _drivers.values():
        with contextlib.suppress(Exception):
            d.close()
    _drivers.clear()


def _clean(d: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _write_query(ns: str, close_previous: bool) -> str:
    """One UNWIND over version rows ``{id, kind, props, nodes, literals, specials}``."""
    close = (f"WITH r, n OPTIONAL MATCH (p:Version:{ns} {{id: r.id}}) WHERE p.tx_to IS NULL "
             "FOREACH (x IN CASE WHEN p IS NULL THEN [] ELSE [p] END | SET x.tx_to = r.props.tx_from) "
             "WITH DISTINCT r, n ") if close_previous else "WITH r, n "
    return (f"UNWIND $rows AS r MERGE (n:Node:{ns} {{id: r.id}}) SET n.kind = r.kind "
            f"{close}"
            f"CREATE (v:Version:{ns}) SET v = r.props CREATE (v)-[:VERSION_OF]->(n) "
            f"FOREACH (b IN r.nodes | MERGE (t:Node:{ns} {{id: b.ref}}) CREATE (v)-[e:BINDS]->(t) SET e = b.props) "
            f"FOREACH (b IN r.literals | MERGE (t:Literal:{ns} {{ident: b.ident}}) "
            f"CREATE (v)-[e:BINDS]->(t) SET e = b.props) "
            f"FOREACH (b IN r.specials | CREATE (t:Special:{ns} {{key: b.key}}) CREATE (v)-[e:BINDS]->(t) "
            f"SET e = b.props)")


def partition(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The buffered rows that close a stored version, and the others, in one pass (review 01, R-15: the list
    membership test it replaces was quadratic)."""
    closing: list[dict[str, Any]] = []
    fresh: list[dict[str, Any]] = []
    for r in rows:
        (closing if r.pop("close", False) else fresh).append(r)
    return closing, fresh


class Neo4jTable:
    """The version table over the graph; inside a write it runs every query in the write's transaction."""

    def __init__(self, schema: Any, store: Neo4jStore):
        self.schema = schema
        self.store = store
        self.ns = store.ns
        self.tx: Any = None
        self.bulk = False
        self.bulk_empty = False
        self._latest: Any = _UNSET
        self._latest_dirty = False
        self._cache: dict[tuple[str, int], Entry] = {}
        self._known: dict[str, list[Entry]] = {}  # prefetched ids: every version, this write's included
        self._held: set[str] = set()  # prefetched ids with a version already written
        self._buf: list[dict[str, Any]] = []
        self._buffered: dict[str, dict[str, Any]] = {}

    def run(self, query: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        """A query over any id: the buffered versions are written first."""
        if self._buf:
            self.flush()
        return self.store.run(query, params, self.tx)

    def run_id(self, rid: str, query: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        """A query about the id ``rid`` only: the buffered versions are written first when one is of ``rid``."""
        if rid in self._buffered:
            self.flush()
        return self.store.run(query, params, self.tx)

    def reset(self) -> None:
        self.tx = None
        self.bulk = False
        self.bulk_empty = False
        self._latest = _UNSET
        self._latest_dirty = False
        self._cache.clear()
        self._known.clear()
        self._held.clear()
        self._buf.clear()
        self._buffered.clear()

    def is_empty(self) -> bool:
        """Whether the store holds no version (one query)."""
        return not self.run(f"MATCH (v:Version:{self.ns}) RETURN 1 AS x LIMIT 1")

    # -- latest
    @property
    def latest(self) -> int | None:
        if self._latest is _UNSET:
            rows = self.store.run(f"MATCH (m:Meta:{self.ns}) RETURN m.latest AS t", None, self.tx)
            self._latest = rows[0]["t"] if rows else None
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
        return bool(self.run_id(rid, f"MATCH (v:Version:{self.ns} {{id: $id}}) RETURN 1 AS x LIMIT 1", {"id": rid}))

    def __len__(self) -> int:
        return self.run(f"MATCH (v:Version:{self.ns}) RETURN count(DISTINCT v.id) AS c")[0]["c"]

    def ids(self) -> list[str]:
        return sorted(r["id"] for r in self.run(f"MATCH (v:Version:{self.ns}) RETURN DISTINCT v.id AS id"))

    # -- prefetch (the optional member; TableStore.load calls it)
    def prefetch(self, records: Iterable[Mapping[str, Any]]) -> None:
        """Read every version of the ids a load brings: one query per ``BATCH`` ids, none on an empty store."""
        ids = sorted({jsonio.nfc(r["id"]) for r in records} - set(self._known))
        for rid in ids:
            self._known[rid] = []
        if not ids or (self.bulk and self.bulk_empty):
            return
        for i in range(0, len(ids), BATCH):
            for r in self.run(f"UNWIND $ids AS i MATCH (v:Version:{self.ns} {{id: i}}) {_WITH_BINDINGS}",
                              {"ids": ids[i:i + BATCH]}):
                v = r["v"]
                self._known[v["id"]].append(Entry(self.store.record(v, r["bs"]), int(v["tx_from"]), self.schema))
        self._held |= {rid for rid in ids if self._known[rid]}

    # -- versions
    def _entries(self, rid: str, cond: str = "", params: Mapping[str, Any] | None = None, order: str = "",
                 limit: str = "") -> list[Entry]:
        rows = self.run_id(rid, f"MATCH (v:Version:{self.ns} {{id: $id}}) WHERE true{cond} WITH v ORDER BY "
                                f"v.version{order}{limit} OPTIONAL MATCH (v)-[e:BINDS]->() WITH v, "
                                "collect(properties(e)) AS bs ORDER BY v.version RETURN properties(v) AS v, bs",
                           {"id": rid, **(params or {})})
        out = []
        for r in rows:
            v = r["v"]
            key = (rid, int(v["version"]))
            e = self._cache.get(key)
            if e is None:
                e = self._cache[key] = Entry(self.store.record(v, r["bs"]), int(v["tx_from"]), self.schema)
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
            es = self._entries(rid, " AND v.tx_from <= $t", {"t": as_at}, " DESC", " LIMIT 1")
        return es[0] if es else None

    def latest_version(self, rid: str) -> int:
        if rid in self._known:
            es = self._known[rid]
            return int(es[-1].record.get("version", len(es))) if es else 0
        rows = self.run_id(rid, f"MATCH (v:Version:{self.ns} {{id: $id}}) RETURN max(v.version) AS m", {"id": rid})
        return int(rows[0]["m"]) if rows and rows[0]["m"] is not None else 0

    def add(self, record: dict[str, Any], t: int) -> Entry:
        rid = record["id"]
        row = self.store.version_row(record, t)
        prev = self._buffered.get(rid)
        if prev is not None:  # the previous version is still in the buffer
            prev["props"]["tx_to"] = t
            row["close"] = False
        elif rid in self._known:
            row["close"] = rid in self._held
        else:
            row["close"] = not (self.bulk and self.bulk_empty)
        self._buf.append(row)
        self._buffered[rid] = row
        self.latest = t if self.latest is None else max(self.latest, t)
        e = Entry(record, t, self.schema)
        self._cache[(rid, int(record["version"]))] = e
        if rid in self._known:
            self._known[rid].append(e)
        return e

    def flush(self) -> None:
        """Write the buffered versions (those that close a stored version first), then the latest time."""
        rows, self._buf = self._buf, []
        self._held |= {rid for rid in self._buffered if rid in self._known}
        self._buffered = {}
        closing, fresh = partition(rows)
        for batch_rows, close in ((closing, True), (fresh, False)):
            for i in range(0, len(batch_rows), BATCH):
                self.store.run(_write_query(self.ns, close), {"rows": batch_rows[i:i + BATCH]}, self.tx)
        if self._latest_dirty:
            self.store.run(f"MERGE (m:Meta:{self.ns}) SET m.latest = $t", {"t": self._latest}, self.tx)
            self._latest_dirty = False

    # -- indexes
    def _ids(self, query: str, params: Mapping[str, Any]) -> set[str]:
        return {r["id"] for r in self.run(query, params)}

    def by_node(self, node: str) -> set[str]:
        return self._ids(f"MATCH (v:Version:{self.ns})-[:BINDS]->(:Node:{self.ns} {{id: $n}}) "
                         "RETURN DISTINCT v.id AS id", {"n": node})

    def by_relation(self, relation: str) -> set[str]:
        return self._ids(f"MATCH (v:Version:{self.ns} {{relation: $r}}) RETURN DISTINCT v.id AS id", {"r": relation})

    def by_key(self, relation: str, digest: str) -> set[str]:
        return self._ids(f"MATCH (v:Version:{self.ns} {{relation: $r, key_digest: $k}}) RETURN DISTINCT v.id AS id",
                         {"r": relation, "k": digest})

    def by_ref(self, lifecycle_id: str) -> set[str]:
        return self._ids(f"MATCH (v:Version:{self.ns} {{status_ref: $s}}) RETURN DISTINCT v.id AS id",
                         {"s": lifecycle_id})

    def __iter__(self) -> Iterator[str]:
        return iter(self.ids())


class Neo4jStore(AdapterMixin, NativeReads, TableStore):
    """A C2 store in Neo4j (see the module docstring)."""

    ENGINE = "Neo4j"
    KIND = "client-server"
    INT64 = True

    def __init__(self, schema: Any, *, uri: str, auth: Any = None, database: str = "neo4j",
                 namespace: str | None = None, clock: Any = None, capabilities: Iterable[str] | None = None,
                 store_id: str = "neo4j"):
        self.trips = Trips()
        self.driver = driver(uri, auth)
        self.database = database
        self._owned = namespace is None
        self.ns = namespace or f"S{os.getpid()}_{next(_seq)}_{os.urandom(3).hex()}"
        if not _LABEL.fullmatch(self.ns):
            raise ValueError(f"namespace is a label of letters, digits and _, not {self.ns!r}")
        for q in INDEXES:
            self.driver.execute_query(q, database_=database)
        super().__init__(schema, table=lambda s: Neo4jTable(s, self), clock=clock,
                         capabilities=self.FLAGS if capabilities is None else capabilities, store_id=store_id)
        self._read_header()

    def engine_version(self) -> str:
        rows = self.run("CALL dbms.components() YIELD name, versions, edition RETURN versions[0] AS v, edition AS e")
        return f"{rows[0]['v']} {rows[0]['e']}" if rows else "?"

    # -- queries (every engine call goes through run, or the begin and commit of transaction)
    def run(self, query: str, params: Mapping[str, Any] | None = None, tx: Any = None) -> list[dict[str, Any]]:
        self.trips.hit("write" if _WRITES.search(query) else "read")
        if tx is not None:
            return [r.data() for r in tx.run(query, dict(params or {}))]
        records, _, _ = self.driver.execute_query(query, dict(params or {}), database_=self.database)
        return [r.data() for r in records]

    def version_row(self, record: Mapping[str, Any], t: int) -> dict[str, Any]:
        """The UNWIND row of one version."""
        if record["kind"] == "entity":
            props = _clean({**entity_row(record, t), "kind": "entity"})
            return {"id": record["id"], "kind": "entity", "props": props, "nodes": [], "literals": [],
                    "specials": []}
        props = _clean({**fact_row(record, self.schema, t), "kind": "fact"})
        nodes, literals, specials = [], [], []
        for b in binding_rows(record):
            bp = _clean({k: b[k] for k in BIND_COLS if k not in ("fact_id", "version")})
            if b["value_kind"] in ("entity", "fact"):
                nodes.append({"ref": b["ref"], "props": bp})
            elif b["value_kind"] == "literal":
                literals.append({"ident": b["ident"], "props": bp})
            else:
                specials.append({"key": f"{record['id']}#{record['version']}#{b['bid']}", "props": bp})
        return {"id": record["id"], "kind": "fact", "props": props, "nodes": nodes, "literals": literals,
                "specials": specials}

    @staticmethod
    def record(v: Mapping[str, Any], bs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        """The record of a version node's properties and its ``BINDS`` properties (``rows.record_of``; Neo4j
        drops null properties, so the columns are filled in)."""
        if v.get("record") is not None:
            return record_of(v)
        return record_of({k: v.get(k) for k in FACT_COLS}, [{k: b.get(k) for k in BIND_COLS} for b in bs if b])

    # -- transactions
    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        table: Neo4jTable = self._table
        session = self.driver.session(database=self.database)
        self.trips.hit("tx")
        tx = session.begin_transaction()
        table.reset()
        table.tx = tx
        try:
            yield
            table.flush()
            self.trips.hit("tx")
            tx.commit()
        except BaseException:
            with contextlib.suppress(Exception):
                tx.rollback()
            raise
        finally:
            table.reset()
            session.close()

    def load(self, container: Any, **kwargs: Any) -> Any:
        """Trusted bulk import: ``TableStore``'s checks over the prefetched ids, the versions in ``UNWIND`` batches,
        the header on the ``:Meta`` node; one transaction."""
        with self.writing():
            table: Neo4jTable = self._table
            table.bulk_empty = table.is_empty()
            table.bulk = True
            try:
                report = TableStore.load(self, container, **kwargs)
                table.flush()
            finally:
                table.bulk = False
            self.run(f"MERGE (m:Meta:{self.ns}) SET m.header = $h, m.documents = $d",
                     {"h": json.dumps(self.kept_header, ensure_ascii=False),
                      "d": json.dumps(self.kept_documents, ensure_ascii=False)}, table.tx)
        return report

    def _read_header(self) -> None:
        rows = self.run(f"MATCH (m:Meta:{self.ns}) RETURN m.header AS h, m.documents AS d")
        if rows and rows[0]["h"] is not None:
            self.kept_header = json.loads(rows[0]["h"])
            self.kept_documents = json.loads(rows[0]["d"] or "[]")

    # -- query parts
    @staticmethod
    def _current(t: int | None, p: dict[str, Any]) -> str:
        if t is None:
            return "v.tx_to IS NULL"
        p["t"] = t
        return "v.tx_from <= $t AND (v.tx_to IS NULL OR v.tx_to > $t)"

    @staticmethod
    def _filters(where: Where, as_of: int | None, p: dict[str, Any]) -> str:
        p.update(st=sorted(where.status), rk=sorted(where.rank), vis=sorted(where.visibility),
                 kinds=sorted(where.kinds))
        out = "v.status IN $st AND v.rank IN $rk AND v.visibility IN $vis AND v.rel_kind IN $kinds"
        if as_of is not None:
            lo, hi = ("s_hi", "e_lo") if where.valid_mode == "definite" else ("s_lo", "e_hi")
            p["asof"] = query_instant(as_of)
            out += f" AND v.{lo} <= $asof AND $asof < v.{hi}"
        return out

    @staticmethod
    def _tail(after: str | None, limit: int | None, p: dict[str, Any]) -> tuple[str, str]:
        cond = ""
        if after is not None:
            cond = " AND v.id > $after"
            p["after"] = after
        return cond, "RETURN DISTINCT v.id AS id ORDER BY id" + (f" LIMIT {int(limit)}" if limit is not None else "")

    # -- native reads
    def _read(self, query: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [self.record(r["v"], r["bs"]) for r in self.run(f"{query} {_WITH_BINDINGS}", params)]

    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
        if not isinstance(id, str):
            return None
        p: dict[str, Any] = {"id": id}
        if version is not None:
            p["ver"] = version
            cond = "v.version = $ver" + (" AND v.tx_from <= $t" if t is not None else "")
            if t is not None:
                p["t"] = t
        else:
            cond = self._current(t, p)
        got = self._read(f"MATCH (v:Version:{self.ns} {{id: $id}}) WHERE {cond}", p)
        return got[0] if got else None

    def _n_versions(self, id: str, t: int | None = None) -> list[dict[str, Any]]:
        if not isinstance(id, str):
            return []
        p: dict[str, Any] = {"id": id}
        cond = "true"
        if t is not None:
            cond, p["t"] = "v.tx_from <= $t", t
        return self._read(f"MATCH (v:Version:{self.ns} {{id: $id}}) WHERE {cond}", p)

    def _n_scan(self, t: int | None, history: bool) -> list[dict[str, Any]]:
        p: dict[str, Any] = {}
        if history:
            cond = "true"
            if t is not None:
                cond, p["t"] = "v.tx_from <= $t", t
        else:
            cond = self._current(t, p)
        return self._read(f"MATCH (v:Version:{self.ns}) WHERE {cond}", p)

    def _n_is_fact(self, id: str) -> bool:
        return bool(self.run(f"MATCH (v:Version:{self.ns} {{id: $id, kind: 'fact'}}) RETURN 1 AS x LIMIT 1",
                             {"id": id}))

    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        wanted = [i for i in ids if isinstance(i, str)]
        by_id: dict[str, dict[str, Any]] = {}
        for i in range(0, len(wanted), BATCH):
            p: dict[str, Any] = {"ids": wanted[i:i + BATCH]}
            for r in self._read(f"UNWIND $ids AS i MATCH (v:Version:{self.ns} {{id: i}}) WHERE {self._current(t, p)}",
                                p):
                by_id[r["id"]] = r
        return [by_id[i] for i in ids if i in by_id]

    def _incident_match(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                        as_of: int | None, p: dict[str, Any]) -> tuple[str, list[str]]:
        p["node"] = node
        conds = [self._current(t, p), self._filters(where, as_of, p)]
        if role is not None:
            conds.append("e.role = $role")
            p["role"] = role
        if relation is not None:
            conds.append("v.relation = $rel")
            p["rel"] = relation
        return f"MATCH (v:Version:{self.ns})-[e:BINDS]->(:Node:{self.ns} {{id: $node}})", conds

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        p: dict[str, Any] = {}
        match, conds = self._incident_match(node, role, relation, where, t, as_of, p)
        cond, tail = self._tail(after, limit, p)
        return [r["id"] for r in self.run(f"{match} WHERE {' AND '.join(conds)}{cond} {tail}", p)]

    def _n_count(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                 as_of: int | None) -> int:
        p: dict[str, Any] = {}
        match, conds = self._incident_match(node, role, relation, where, t, as_of, p)
        return int(self.run(f"{match} WHERE {' AND '.join(conds)} RETURN count(DISTINCT v.id) AS c", p)[0]["c"])

    def _n_find(self, relation: str, pats: list[Pat], match: str, where: Where, t: int | None, as_of: int | None,
                after: str | None, limit: int | None) -> list[str]:
        p: dict[str, Any] = {"rel": relation}
        paths, conds = [f"(v:Version:{self.ns} {{relation: $rel}})"], []
        for i, pat in enumerate(pats, 1):
            paths.append(f"(v)-[b{i}:BINDS]->()")
            conds.append(f"b{i}.role = $r{i}")
            p[f"r{i}"] = pat.role
            if pat.position is not None:
                conds.append(f"b{i}.position = $p{i}")
                p[f"p{i}"] = pat.position
            if pat.kind == "value":
                conds.append(f"b{i}.ident = $i{i}")
                p[f"i{i}"] = pat.ident
            elif pat.kind == "any_unbound":
                conds.append(f"b{i}.value_kind = 'unbound'")
            conds += [f"b{i}.bid <> b{j}.bid" for j in range(1, i)]  # injective: distinct bindings
        conds += [self._current(t, p), self._filters(where, as_of, p)]
        if match == "exact":
            conds.append("v.n_bindings = $n")
            p["n"] = len(pats)
        cond, tail = self._tail(after, limit, p)
        q = f"MATCH {', '.join(paths)} WHERE {' AND '.join(conds)}{cond} {tail}"
        return [r["id"] for r in self.run(q, p)]

    def _n_key(self, relation: str, digest: str, where: Where, t: int | None, as_of: int | None) -> list[str]:
        p: dict[str, Any] = {"rel": relation, "kd": digest}
        q = (f"MATCH (v:Version:{self.ns} {{relation: $rel, key_digest: $kd}}) WHERE {self._current(t, p)} AND "
             f"{self._filters(where, as_of, p)} RETURN v.id AS id ORDER BY id")
        return [r["id"] for r in self.run(q, p)]

    def _n_bound_by(self, relation: str, role: str, idents: Sequence[str], where: Where, t: int | None,
                    as_of: int | None) -> dict[str, list[str]]:
        p: dict[str, Any] = {"rel": relation, "role": role, "idents": list(idents)}
        q = (f"MATCH (v:Version:{self.ns} {{relation: $rel}})-[e:BINDS]->() WHERE e.role = $role AND "
             f"e.ident IN $idents AND {self._current(t, p)} AND {self._filters(where, as_of, p)} "
             "RETURN DISTINCT e.ident AS ident, v.id AS id ORDER BY id")
        out: dict[str, list[str]] = {}
        for r in self.run(q, p):
            out.setdefault(r["ident"], []).append(r["id"])
        return out

    # -- fidelity number 2
    def native_bindings(self, rid: str) -> list[dict[str, Any]] | None:
        """The bindings of the current version of fact ``rid`` from the ``BINDS`` edges and their targets
        (``rows.native_binding``: an entity or fact value is where the edge points, a literal's identity is its
        ``:Literal`` node's; not ``value_json``, not ``payload``)."""
        rows = self.run(f"MATCH (v:Version:{self.ns} {{id: $id, kind: 'fact'}}) WHERE v.tx_to IS NULL "
                        "OPTIONAL MATCH (v)-[e:BINDS]->(t) RETURN properties(e) AS e, t.id AS target, "
                        "t.ident AS literal", {"id": rid})
        if not rows:
            return None
        out = []
        for r in rows:
            if r["e"] is None:
                continue
            e = {k: v for k, v in r["e"].items() if k != "value_json"}
            if e.get("value_kind") in ("entity", "fact"):
                e["ref"] = r["target"]  # the value is where the edge points, not the ref property
            elif e.get("value_kind") == "literal":
                e["ident"] = r["literal"]  # the shared literal node's identity
            out.append(native_binding(e))
        return out

    def close(self) -> None:
        if not self._owned:
            return
        with contextlib.suppress(Exception):
            while self.run(f"MATCH (n:{self.ns}) WITH n LIMIT 10000 DETACH DELETE n RETURN count(*) AS c")[0]["c"]:
                pass


def factory(uri: str, auth: Any = None) -> Any:
    """A conformance factory: a fresh ``Neo4jStore`` (its own namespace label, deleted by ``close``) per call."""

    def make(schema: Any, clock: Any) -> Neo4jStore:
        return Neo4jStore(schema, uri=uri, auth=auth, clock=clock)

    return make
