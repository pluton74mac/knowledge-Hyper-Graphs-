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

**Writes.** Each write is one explicit transaction; the table reads through it, so it sees its own writes. A bulk
load writes its versions with ``UNWIND`` batches of ``BATCH`` rows in the load's transaction.
"""
from __future__ import annotations

import atexit
import contextlib
import itertools
import json
import os
import re
from typing import Any, Iterable, Iterator, Mapping, Sequence

from khg_contracts.store import Where
from khg_contracts.store.table import Entry, TableStore

from .native import NativeReads
from .rows import BIND_COLS, FACT_COLS, Pat, assemble, binding_rows, entity_row, fact_row, native_binding, query_instant
from .shared import AdapterMixin

__all__ = ["BATCH", "Neo4jStore", "Neo4jTable", "factory"]

BATCH = 500
_UNSET: Any = object()
_seq = itertools.count(1)
_drivers: dict[tuple[str, Any], Any] = {}
_LABEL = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,60}")
INDEXES = [
    "CREATE INDEX khg_version_id IF NOT EXISTS FOR (v:Version) ON (v.id)",
    "CREATE INDEX khg_version_key IF NOT EXISTS FOR (v:Version) ON (v.relation, v.key_digest)",
    "CREATE INDEX khg_version_rel IF NOT EXISTS FOR (v:Version) ON (v.relation)",
    "CREATE INDEX khg_node_id IF NOT EXISTS FOR (n:Node) ON (n.id)",
    "CREATE INDEX khg_literal_ident IF NOT EXISTS FOR (n:Literal) ON (n.ident)",
    "CREATE INDEX khg_binds_role IF NOT EXISTS FOR ()-[e:BINDS]-() ON (e.role)",
    "CREATE INDEX khg_binds_role_ident IF NOT EXISTS FOR ()-[e:BINDS]-() ON (e.role, e.ident)",
]


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
        self._buf: list[dict[str, Any]] = []
        self._buffered: dict[str, dict[str, Any]] = {}

    def run(self, query: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        if self._buffered:
            self.flush()
        return self.store.run(query, params, self.tx)

    def reset(self) -> None:
        self.tx = None
        self._latest = _UNSET
        self._latest_dirty = False
        self._cache.clear()
        self._buf.clear()
        self._buffered.clear()

    # -- latest
    @property
    def latest(self) -> int | None:
        if self._latest is _UNSET:
            rows = self.run(f"MATCH (m:Meta:{self.ns}) RETURN m.latest AS t")
            self._latest = rows[0]["t"] if rows else None
        return self._latest

    @latest.setter
    def latest(self, t: int | None) -> None:
        self._latest = t
        if self.bulk:
            self._latest_dirty = True
        else:
            self._write_latest()

    def _write_latest(self) -> None:
        self.store.run(f"MERGE (m:Meta:{self.ns}) SET m.latest = $t", {"t": self._latest}, self.tx)
        self._latest_dirty = False

    # -- ids
    def __contains__(self, rid: object) -> bool:
        return isinstance(rid, str) and bool(self.run(f"MATCH (v:Version:{self.ns} {{id: $id}}) RETURN 1 AS x LIMIT 1",
                                                      {"id": rid}))

    def __len__(self) -> int:
        return self.run(f"MATCH (v:Version:{self.ns}) RETURN count(DISTINCT v.id) AS c")[0]["c"]

    def ids(self) -> list[str]:
        return sorted(r["id"] for r in self.run(f"MATCH (v:Version:{self.ns}) RETURN DISTINCT v.id AS id"))

    # -- versions
    def _entries(self, rid: str, cond: str = "", params: Mapping[str, Any] | None = None, order: str = "",
                 limit: str = "") -> list[Entry]:
        rows = self.run(f"MATCH (v:Version:{self.ns} {{id: $id}}) WHERE true{cond} WITH v ORDER BY v.version{order}"
                        f"{limit} OPTIONAL MATCH (v)-[e:BINDS]->() WITH v, collect(properties(e)) AS bs "
                        f"ORDER BY v.version RETURN properties(v) AS v, bs", {"id": rid, **(params or {})})
        out = []
        for r in rows:
            v = r["v"]
            key = (rid, int(v["version"]))
            e = self._cache.get(key)
            if e is None:
                e = self._cache[key] = Entry(self.store.assemble(v, r["bs"]), int(v["tx_from"]), self.schema)
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
            es = self._entries(rid, " AND v.tx_from <= $t", {"t": as_at}, " DESC", " LIMIT 1")
        return es[0] if es else None

    def latest_version(self, rid: str) -> int:
        rows = self.run(f"MATCH (v:Version:{self.ns} {{id: $id}}) RETURN max(v.version) AS m", {"id": rid})
        return int(rows[0]["m"]) if rows and rows[0]["m"] is not None else 0

    def add(self, record: dict[str, Any], t: int) -> Entry:
        rid = record["id"]
        row = self.store.version_row(record, t)
        prev = self._buffered.get(rid)
        if prev is not None:
            prev["props"]["tx_to"] = t
        if self.bulk:
            row["close"] = prev is None and not self.bulk_empty
            self._buf.append(row)
            self._buffered[rid] = row
        else:
            self.store.run(_write_query(self.ns, True), {"rows": [row]}, self.tx)
        self.latest = t if self.latest is None else max(self.latest, t)
        e = Entry(record, t, self.schema)
        self._cache[(rid, int(record["version"]))] = e
        return e

    def flush(self) -> None:
        rows, self._buf = self._buf, []
        self._buffered = {}
        closing = [r for r in rows if r.pop("close", False)]
        fresh = [r for r in rows if r not in closing]
        for batch_rows, close in ((closing, True), (fresh, False)):
            for i in range(0, len(batch_rows), BATCH):
                self.store.run(_write_query(self.ns, close), {"rows": batch_rows[i:i + BATCH]}, self.tx)
        if self._latest_dirty:
            self._write_latest()

    # -- indexes
    def _ids(self, query: str, params: Mapping[str, Any]) -> set[str]:
        return {r["id"] for r in self.run(query, params)}

    def by_node(self, node: str) -> set[str]:
        return self._ids(f"MATCH (v:Version:{self.ns})-[:BINDS]->(:Node:{self.ns} {{id: $n}}) RETURN DISTINCT v.id AS id",
                         {"n": node})

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
        self._read_documents()

    def engine_version(self) -> str:
        rows = self.run("CALL dbms.components() YIELD name, versions, edition RETURN versions[0] AS v, edition AS e")
        return f"{rows[0]['v']} {rows[0]['e']}" if rows else "?"

    # -- queries
    def run(self, query: str, params: Mapping[str, Any] | None = None, tx: Any = None) -> list[dict[str, Any]]:
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
    def assemble(v: Mapping[str, Any], bs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if v.get("kind") == "entity":
            return json.loads(v["record"])
        return assemble({k: v.get(k) for k in FACT_COLS}, [{k: b.get(k) for k in BIND_COLS} for b in bs if b])

    # -- transactions
    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        table: Neo4jTable = self._table
        session = self.driver.session(database=self.database)
        tx = session.begin_transaction()
        table.reset()
        table.tx = tx
        header = (self._header, self._documents)
        try:
            yield
            table.flush()
            tx.commit()
        except BaseException:
            with contextlib.suppress(Exception):
                tx.rollback()
            self._header, self._documents = header
            raise
        finally:
            table.reset()
            session.close()

    def load(self, container: Any, **kwargs: Any) -> Any:
        """Trusted bulk import: ``TableStore``'s checks, the versions in ``UNWIND`` batches, the header on the
        ``:Meta`` node; one transaction."""
        with self.writing():
            table: Neo4jTable = self._table
            table.bulk_empty = len(table) == 0
            table.bulk = True
            try:
                report = TableStore.load(self, container, **kwargs)
                table.flush()
            finally:
                table.bulk = False
            self.run(f"MERGE (m:Meta:{self.ns}) SET m.header = $h, m.documents = $d",
                     {"h": json.dumps(self._header, ensure_ascii=False),
                      "d": json.dumps(self._documents, ensure_ascii=False)}, table.tx)
        return report

    def _read_documents(self) -> None:
        rows = self.run(f"MATCH (m:Meta:{self.ns}) RETURN m.header AS h, m.documents AS d")
        if rows and rows[0]["h"] is not None:
            self._header = json.loads(rows[0]["h"])
            self._documents = json.loads(rows[0]["d"] or "[]")

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
        rows = self.run(f"{query} OPTIONAL MATCH (v)-[e:BINDS]->() WITH v, collect(properties(e)) AS bs "
                        "ORDER BY v.id, v.version RETURN properties(v) AS v, bs", params)
        return [self.assemble(r["v"], r["bs"]) for r in rows]

    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
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
        p: dict[str, Any] = {"id": id}
        cond = "true"
        if t is not None:
            cond, p["t"] = "v.tx_from <= $t", t
        return self._read(f"MATCH (v:Version:{self.ns} {{id: $id}}) WHERE {cond}", p)

    def _n_ids(self, t: int | None) -> list[str]:
        p: dict[str, Any] = {}
        cond = "true" if t is None else "v.tx_from <= $t"
        if t is not None:
            p["t"] = t
        return sorted(r["id"] for r in self.run(f"MATCH (v:Version:{self.ns}) WHERE {cond} RETURN DISTINCT v.id AS id",
                                                p))

    def _n_is_fact(self, id: str) -> bool:
        return bool(self.run(f"MATCH (v:Version:{self.ns} {{id: $id, kind: 'fact'}}) RETURN 1 AS x LIMIT 1",
                             {"id": id}))

    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        if not ids:
            return []
        p: dict[str, Any] = {"ids": list(ids)}
        got = self._read(f"UNWIND $ids AS i MATCH (v:Version:{self.ns} {{id: i}}) WHERE {self._current(t, p)}", p)
        by_id = {r["id"]: r for r in got}
        return [by_id[i] for i in ids if i in by_id]

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        p: dict[str, Any] = {"node": node}
        conds = [self._current(t, p), self._filters(where, as_of, p)]
        if role is not None:
            conds.append("e.role = $role")
            p["role"] = role
        if relation is not None:
            conds.append("v.relation = $rel")
            p["rel"] = relation
        cond, tail = self._tail(after, limit, p)
        q = (f"MATCH (v:Version:{self.ns})-[e:BINDS]->(:Node:{self.ns} {{id: $node}}) "
             f"WHERE {' AND '.join(conds)}{cond} {tail}")
        return [r["id"] for r in self.run(q, p)]

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

    # -- fidelity number 2
    def native_bindings(self, rid: str) -> list[dict[str, Any]] | None:
        """The bindings of the current version of fact ``rid`` from the ``BINDS`` edges and their targets (not
        ``payload``)."""
        rows = self.run(f"MATCH (v:Version:{self.ns} {{id: $id, kind: 'fact'}}) WHERE v.tx_to IS NULL "
                        "OPTIONAL MATCH (v)-[e:BINDS]->(t) RETURN properties(e) AS e, t.id AS target", {"id": rid})
        if not rows:
            return None
        out = []
        for r in rows:
            if r["e"] is None:
                continue
            e = dict(r["e"])
            if e.get("value_kind") in ("entity", "fact"):
                e["ref"] = r["target"]  # the value is where the edge points, not the ref property
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
