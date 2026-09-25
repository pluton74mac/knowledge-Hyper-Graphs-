"""The RDF adapter (DESIGN §3.2): reified RDF in the relation-instance pattern, one named graph per version, in
Oxigraph through pyoxigraph (research 01 §3).

``OxigraphStore(schema, *, path=None, clock=None, capabilities=None, store_id="oxigraph")`` keeps its RocksDB store
on disk: in a temporary directory that ``close`` removes (``path=None``), or at ``path`` (reopened when it holds a
store).

**Layout.** Each version of each record is one named graph ``<urn:khg:<id>/v<n>>`` (``/`` never occurs in an
encoded id). A hyperedge version's graph holds P2's projection ``record.project.rdf_relation_instance`` of that
version, plus the triples the reads filter on::

    <f> khg:id "id" ; khg:rank ; khg:visibility ; khg:relKind ; khg:statusRef <iri> ; khg:keyDigest ;
        khg:sLo khg:sHi khg:eLo khg:eHi (xsd:integer) ; khg:nBindings ; khg:payload "canonical JSON" .
    <f#b> khg:ident "value identity" ; khg:valueKind "literal|special|unbound" ; khg:extensions "JSON" .

An entity version's graph holds ``<e> a khg:Entity ; khg:id ; khg:record "JSON"``. The default graph holds the
version metadata (``<g> khg:versionOf <f> ; khg:version ; khg:txFrom ; khg:txTo ; khg:recordedAt ;
khg:recordedBy``) and the store's own (``<urn:khg:store> khg:latest ; khg:header ; khg:documents``). No RDF 1.2
triple term is needed. Instants are int64 with the ±2^62 guard (ruling 4): Oxigraph compares ``xsd:integer``
beyond int64 wrongly (research 01 §7).

**Writes.** pyoxigraph has no transaction handle, so a write collects its versions in an in-memory overlay (a
``VersionTable`` the table reads through) and ends with one ``Store.update`` (``DELETE WHERE`` and ``INSERT DATA``),
which Oxigraph applies all or nothing. A trusted load into an empty store uses ``bulk_extend`` (not transactional:
on a failure the store is cleared back to empty), then one ``update`` for the store's own triples.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from typing import Any, Iterable, Iterator, Sequence

from khg_contracts.record.project import KHG_NS, RDF_TYPE, iri_decode, iri_encode, rdf_relation_instance
from khg_contracts.store import Where
from khg_contracts.store.table import Entry, TableStore, VersionTable

from .native import NativeReads
from .rows import Pat, assemble, binding_rows, fact_row, native_binding, query_instant
from .shared import AdapterMixin

__all__ = ["OxigraphStore", "OxigraphTable", "factory", "graph_name"]

K = KHG_NS
XSD_INT = "http://www.w3.org/2001/XMLSchema#integer"
STORE = "urn:khg:store"
PREFIX = f"PREFIX khg: <{K}>\n"
_UNSET: Any = object()


def graph_name(id: str, version: int) -> str:
    return f"{iri_encode(id)}/v{version}"


def s(text: str) -> str:
    """A SPARQL string literal."""
    return json.dumps(text, ensure_ascii=False)


class OxigraphTable:
    """The version table over the store, with an overlay for the versions of the write in progress."""

    def __init__(self, schema: Any, owner: OxigraphStore):
        self.schema = schema
        self.owner = owner
        self.overlay = VersionTable(schema)
        self._latest: Any = _UNSET
        self._cache: dict[str, list[Entry]] = {}

    # -- plumbing
    def reset(self) -> None:
        self.overlay = VersionTable(self.schema)
        self._latest = _UNSET
        self._cache.clear()

    def select(self, query: str) -> list[dict[str, Any]]:
        return self.owner.select(query)

    # -- latest
    @property
    def latest(self) -> int | None:
        if self._latest is _UNSET:
            rows = self.select(PREFIX + f"SELECT ?t WHERE {{ <{STORE}> khg:latest ?t }}")
            self._latest = rows[0]["t"] if rows else None
        return self._latest

    @latest.setter
    def latest(self, t: int | None) -> None:
        self._latest = t

    # -- ids
    def _stored_ids(self) -> set[str]:
        return {r["id"] for r in self.select(PREFIX + "SELECT DISTINCT ?id WHERE { GRAPH ?g { ?x khg:id ?id } }")}

    def __contains__(self, rid: object) -> bool:
        if not isinstance(rid, str):
            return False
        if rid in self.overlay:
            return True
        return bool(self.select(PREFIX + f"ASK {{ ?g khg:versionOf <{iri_encode(rid)}> }}"))

    def __len__(self) -> int:
        return len(self._stored_ids() | set(self.overlay.ids()))

    def ids(self) -> list[str]:
        return sorted(self._stored_ids() | set(self.overlay.ids()))

    # -- versions
    def _stored(self, rid: str) -> list[Entry]:
        got = self._cache.get(rid)
        if got is None:
            got = [Entry(rec, t, self.schema) for rec, t in self.owner.versions_of(rid)]
            self._cache[rid] = got
        return got

    def entries(self, rid: str) -> list[Entry]:
        return self._stored(rid) + self.overlay.entries(rid)

    def current(self, rid: str) -> dict[str, Any] | None:
        es = self.entries(rid)
        return es[-1].record if es else None

    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None:
        for e in reversed(self.entries(rid)):
            if as_at is None or e.t <= as_at:
                return e
        return None

    def latest_version(self, rid: str) -> int:
        es = self.entries(rid)
        return int(es[-1].record.get("version", len(es))) if es else 0

    def add(self, record: dict[str, Any], t: int) -> Entry:
        e = self.overlay.add(record, t)
        self.latest = t if self.latest is None else max(self.latest, t)
        return e

    # -- indexes
    def _ids_of(self, body: str) -> set[str]:
        return {r["id"] for r in self.select(PREFIX + f"SELECT DISTINCT ?id WHERE {{ GRAPH ?g {{ {body} }} }}")}

    def by_node(self, node: str) -> set[str]:
        return self._ids_of(f"?f khg:binding ?b ; khg:id ?id . ?b khg:value <{iri_encode(node)}> .") | \
            self.overlay.by_node(node)

    def by_relation(self, relation: str) -> set[str]:
        return self._ids_of(f"?f khg:relation {s(relation)} ; khg:id ?id .") | self.overlay.by_relation(relation)

    def by_key(self, relation: str, digest: str) -> set[str]:
        return self._ids_of(f"?f khg:relation {s(relation)} ; khg:keyDigest {s(digest)} ; khg:id ?id .") | \
            self.overlay.by_key(relation, digest)

    def by_ref(self, lifecycle_id: str) -> set[str]:
        return self._ids_of(f"?f khg:statusRef <{iri_encode(lifecycle_id)}> ; khg:id ?id .") | \
            self.overlay.by_ref(lifecycle_id)

    def __iter__(self) -> Iterator[str]:
        return iter(self.ids())


class OxigraphStore(AdapterMixin, NativeReads, TableStore):
    """A C2 store in Oxigraph (see the module docstring)."""

    ENGINE = "Oxigraph (pyoxigraph)"
    KIND = "embedded"
    INT64 = True

    def __init__(self, schema: Any, *, path: str | os.PathLike | None = None, clock: Any = None,
                 capabilities: Iterable[str] | None = None, store_id: str = "oxigraph"):
        import pyoxigraph

        self.ox = pyoxigraph
        self._owned = path is None
        self.path = tempfile.mkdtemp(prefix="khg-oxigraph-", dir=os.environ.get("P1_TMP") or None) \
            if path is None else os.fspath(path)
        self.store = pyoxigraph.Store(self.path)
        super().__init__(schema, table=lambda sch: OxigraphTable(sch, self), clock=clock,
                         capabilities=self.FLAGS if capabilities is None else capabilities, store_id=store_id)
        self._bulk = False
        self._read_documents()

    def engine_version(self) -> str:
        return f"pyoxigraph {self.ox.__version__}"

    # -- terms and queries
    def _term(self, x: Any) -> Any:
        ox = self.ox
        if isinstance(x, dict):
            return ox.Literal(x["literal"], datatype=ox.NamedNode(x["datatype"])) if "datatype" in x else \
                ox.Literal(x["literal"])
        return ox.NamedNode(x)

    def select(self, query: str) -> Any:
        res = self.store.query(query)
        if isinstance(res, self.ox.QueryBoolean):
            return bool(res)
        names = [v.value for v in res.variables]
        out = []
        for sol in res:
            row = {}
            for n in names:
                term = sol[n]
                if term is None:
                    row[n] = None
                elif isinstance(term, self.ox.Literal):
                    row[n] = int(term.value) if term.datatype.value == XSD_INT else term.value
                else:
                    row[n] = term.value
            out.append(row)
        return out

    # -- the quads of a version
    def quads(self, record: dict[str, Any], t: int, tx_to: int | None) -> list[tuple[str, str, Any, str | None]]:
        rid, version = record["id"], record["version"]
        g = graph_name(rid, version)
        f = iri_encode(rid)

        def lit(x: Any) -> dict[str, str]:
            return {"literal": str(x)}

        def integer(n: int) -> dict[str, str]:
            return {"literal": str(int(n)), "datatype": XSD_INT}

        out: list[tuple[str, str, Any, str | None]] = [
            (g, K + "versionOf", f, None), (g, K + "version", integer(version), None),
            (g, K + "txFrom", integer(t), None), (g, K + "recordedAt", lit(record["recorded_at"]), None),
            (g, K + "recordedBy", lit(record["recorded_by"]), None)]
        if tx_to is not None:
            out.append((g, K + "txTo", integer(tx_to), None))
        if record["kind"] == "entity":
            return out + [(f, RDF_TYPE, K + "Entity", g), (f, K + "id", lit(rid), g),
                          (f, K + "record", lit(json.dumps(record, ensure_ascii=False, sort_keys=True)), g)]
        row = fact_row(record, self.schema, t)
        out += [(a, b, c, g) for a, b, c in rdf_relation_instance({"records": [record]})]
        out += [(f, K + "id", lit(rid), g), (f, K + "rank", lit(row["rank"]), g),
                (f, K + "visibility", lit(row["visibility"]), g), (f, K + "relKind", lit(row["rel_kind"]), g),
                (f, K + "nBindings", integer(row["n_bindings"]), g), (f, K + "payload", lit(row["payload"]), g)]
        for col, pred in (("s_lo", "sLo"), ("s_hi", "sHi"), ("e_lo", "eLo"), ("e_hi", "eHi")):
            out.append((f, K + pred, integer(row[col]), g))
        if row["status_ref"] is not None:
            out.append((f, K + "statusRef", iri_encode(row["status_ref"]), g))
        if row["key_digest"] is not None:
            out.append((f, K + "keyDigest", lit(row["key_digest"]), g))
        for b in binding_rows(record):
            n = f + "#" + b["bid"]
            if b["ident"] is not None:
                out.append((n, K + "ident", lit(b["ident"]), g))
            if b["value_kind"] not in ("entity", "fact"):
                out.append((n, K + "valueKind", lit(b["value_kind"]), g))
            if b["extensions"] is not None:
                out.append((n, K + "extensions", lit(b["extensions"]), g))
        return out

    def _quad_text(self, quad: tuple[str, str, Any, str | None]) -> str:
        a, b, c, g = quad
        triple = f"{self._term(a)} {self._term(b)} {self._term(c)} ."
        return triple if g is None else f"GRAPH {self._term(g)} {{ {triple} }}"

    def _pending_quads(self) -> list[tuple[str, str, Any, str | None]]:
        """The quads of the overlay's versions, with ``txTo`` on every version a later one supersedes."""
        table: OxigraphTable = self._table
        out = []
        for rid in table.overlay.ids():
            stored = table._stored(rid)
            new = table.overlay.entries(rid)
            if stored:
                prev = stored[-1]
                out.append((graph_name(rid, prev.record["version"]), K + "txTo",
                            {"literal": str(new[0].t), "datatype": XSD_INT}, None))
            for i, e in enumerate(new):
                out += self.quads(e.record, e.t, new[i + 1].t if i + 1 < len(new) else None)
        return out

    def _meta_update(self) -> str:
        table: OxigraphTable = self._table
        parts = [f"DELETE WHERE {{ <{STORE}> ?p ?o }}"]
        meta = []
        if table.latest is not None:
            meta.append((STORE, K + "latest", {"literal": str(table.latest), "datatype": XSD_INT}, None))
        meta.append((STORE, K + "header", {"literal": json.dumps(self._header, ensure_ascii=False)}, None))
        meta.append((STORE, K + "documents", {"literal": json.dumps(self._documents, ensure_ascii=False)}, None))
        parts.append("INSERT DATA { " + " ".join(self._quad_text(q) for q in meta) + " }")
        return " ;\n".join(parts)

    # -- transactions
    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        table: OxigraphTable = self._table
        table.reset()
        header = (self._header, self._documents)
        latest = table.latest
        try:
            yield
            quads = self._pending_quads()
            if self._bulk and not table._stored_ids() and quads:
                ox = self.ox
                try:
                    self.store.bulk_extend([ox.Quad(self._term(a), self._term(b), self._term(c),
                                                    self._term(g) if g else ox.DefaultGraph())
                                            for a, b, c, g in quads])
                    self.store.update(self._meta_update())
                except BaseException:
                    self.store.clear()  # bulk_extend is not transactional: back to the empty store
                    raise
            elif quads or (self._header, self._documents) != header or table.latest != latest:
                body = " ".join(self._quad_text(q) for q in quads)
                update = self._meta_update() + (f" ;\nINSERT DATA {{ {body} }}" if body else "")
                self.store.update(update)
        except BaseException:
            table.reset()
            self._header, self._documents = header
            raise
        table.reset()

    def load(self, container: Any, **kwargs: Any) -> Any:
        """Trusted bulk import: ``TableStore``'s checks, then ``bulk_extend`` into an empty store."""
        with self.writing():
            self._bulk = True
            try:
                return TableStore.load(self, container, **kwargs)
            finally:
                self._bulk = False

    def _read_documents(self) -> None:
        rows = self.select(PREFIX + f"SELECT ?h ?d WHERE {{ <{STORE}> khg:header ?h ; khg:documents ?d }}")
        if rows:
            self._header = json.loads(rows[0]["h"])
            self._documents = json.loads(rows[0]["d"])

    # -- reading versions back
    def versions_of(self, rid: str, t: int | None = None, version: int | None = None,
                    current: bool = False) -> list[tuple[dict[str, Any], int]]:
        """``(record, tx_from)`` of the versions of ``rid``, oldest first: all, those recorded at or before ``t``,
        the one numbered ``version``, or (``current``) the one open at ``t``."""
        f = iri_encode(rid)
        cond = ""
        if version is not None:
            cond += f" FILTER(?v = {int(version)})"
        if t is not None:
            cond += f" FILTER(?from <= {int(t)})"
        if current:
            cond += " OPTIONAL { ?g khg:txTo ?txTo }" + \
                (" FILTER(!BOUND(?txTo))" if t is None else f" FILTER(!BOUND(?txTo) || ?txTo > {int(t)})")
        rows = self.select(PREFIX + f"SELECT ?g ?v ?from ?at ?by ?s ?p ?o WHERE {{ ?g khg:versionOf <{f}> ; "
                                    f"khg:version ?v ; khg:txFrom ?from ; khg:recordedAt ?at ; khg:recordedBy ?by ."
                                    f"{cond} GRAPH ?g {{ ?s ?p ?o }} }}")
        graphs: dict[str, dict[str, Any]] = {}
        for r in rows:
            g = graphs.setdefault(r["g"], {"v": r["v"], "from": r["from"], "rows": []})
            g["rows"].append(r)
        out = []
        for g in sorted(graphs.values(), key=lambda x: x["v"]):
            out.append((self._record(f, g["rows"]), int(g["from"])))
        return out

    @staticmethod
    def _record(f: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        subj: dict[str, dict[str, Any]] = {}
        for r in rows:
            subj.setdefault(r["s"], {})[r["p"]] = r["o"]
        top = subj[f]
        if top.get(RDF_TYPE) == K + "Entity":
            return json.loads(top[K + "record"])
        first = rows[0]
        fact = {"id": top[K + "id"], "version": first["v"], "recorded_at": first["at"],
                "recorded_by": first["by"], "relation": top[K + "relation"], "status": top[K + "status"],
                "rank": top[K + "rank"], "visibility": top[K + "visibility"], "payload": top[K + "payload"],
                "status_ref": iri_decode(top[K + "statusRef"]) if K + "statusRef" in top else None}
        brs = []
        for n, a in subj.items():
            if n == f:
                continue
            brs.append({"bid": a[K + "bid"], "role": a[K + "role"],
                        "position": int(a[K + "position"]) if K + "position" in a else None,
                        "direction": a.get(K + "direction"), "value_kind": a.get(K + "valueKind"),
                        "ref": iri_decode(a[K + "value"]) if K + "value" in a else None,
                        "value_json": a.get(K + "valueJSON"), "extensions": a.get(K + "extensions")})
        return assemble(fact, brs)

    # -- query parts
    @staticmethod
    def _current(t: int | None) -> str:
        if t is None:
            return "?g khg:versionOf ?f . FILTER NOT EXISTS { ?g khg:txTo ?txTo }"
        return (f"?g khg:versionOf ?f ; khg:txFrom ?from . FILTER(?from <= {int(t)}) "
                f"OPTIONAL {{ ?g khg:txTo ?txTo }} FILTER(!BOUND(?txTo) || ?txTo > {int(t)})")

    @staticmethod
    def _filters(where: Where, as_of: int | None) -> str:
        def one_of(var: str, values: Any) -> str:
            vs = sorted(values)
            return f"FILTER({var} IN ({', '.join(s(v) for v in vs)}))" if vs else "FILTER(false)"

        parts = ["?f khg:status ?st ; khg:rank ?rk ; khg:visibility ?vis ; khg:relKind ?kind ; khg:id ?id .",
                 one_of("?st", where.status), one_of("?rk", where.rank), one_of("?vis", where.visibility),
                 one_of("?kind", where.kinds)]
        if as_of is not None:
            t = query_instant(as_of)
            lo, hi = ("khg:sHi", "khg:eLo") if where.valid_mode == "definite" else ("khg:sLo", "khg:eHi")
            parts += [f"?f {lo} ?vlo ; {hi} ?vhi .", f"FILTER(?vlo <= {t} && {t} < ?vhi)"]
        return "\n    ".join(parts)

    def _ids_where(self, body: str, where: Where, t: int | None, as_of: int | None, after: str | None,
                   limit: int | None) -> list[str]:
        cond = f"FILTER(?id > {s(after)})" if after is not None else ""
        tail = "ORDER BY ?id" + (f" LIMIT {int(limit)}" if limit is not None else "")
        q = (PREFIX + f"SELECT DISTINCT ?id WHERE {{\n  {self._current(t)}\n  GRAPH ?g {{\n    {body}\n    "
             f"{self._filters(where, as_of)}\n    {cond}\n  }}\n}} {tail}")
        return [r["id"] for r in self.select(q)]

    # -- native reads
    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
        if not isinstance(id, str):
            return None
        got = self.versions_of(id, t, version, current=version is None)
        return got[-1][0] if got else None

    def _n_versions(self, id: str, t: int | None = None) -> list[dict[str, Any]]:
        return [r for r, _ in self.versions_of(id, t)] if isinstance(id, str) else []

    def _n_ids(self, t: int | None) -> list[str]:
        cond = "" if t is None else f"?g khg:txFrom ?from . FILTER(?from <= {int(t)})"
        rows = self.select(PREFIX + f"SELECT DISTINCT ?id WHERE {{ ?g khg:versionOf ?x . {cond} "
                                    "GRAPH ?g { ?x khg:id ?id } }")
        return sorted(r["id"] for r in rows)

    def _n_is_fact(self, id: str) -> bool:
        return bool(self.select(PREFIX + f"ASK {{ GRAPH ?g {{ <{iri_encode(id)}> a khg:Hyperedge }} }}"))

    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        out = []
        for i in ids:
            got = self.versions_of(i, t, None, current=True)
            if got:
                out.append(got[-1][0])
        return out

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        body = f"?f khg:binding ?b . ?b khg:value <{iri_encode(node)}> ."
        if role is not None:
            body += f" ?b khg:role {s(role)} ."
        if relation is not None:
            body += f" ?f khg:relation {s(relation)} ."
        return self._ids_where(body, where, t, as_of, after, limit)

    def _n_find(self, relation: str, pats: list[Pat], match: str, where: Where, t: int | None, as_of: int | None,
                after: str | None, limit: int | None) -> list[str]:
        body = [f"?f khg:relation {s(relation)} ."]
        for i, p in enumerate(pats, 1):
            body.append(f"?f khg:binding ?b{i} . ?b{i} khg:role {s(p.role)} .")
            if p.position is not None:
                body.append(f"?b{i} khg:position {s(str(p.position))} .")
            if p.kind == "value":
                body.append(f"?b{i} khg:ident {s(p.ident)} .")
            elif p.kind == "any_unbound":
                body.append(f"?b{i} khg:valueKind \"unbound\" .")
            body += [f"FILTER(?b{i} != ?b{j})" for j in range(1, i)]  # injective: distinct binding nodes
        if match == "exact":
            body.append(f"?f khg:nBindings {len(pats)} .")
        return self._ids_where("\n    ".join(body), where, t, as_of, after, limit)

    def _n_key(self, relation: str, digest: str, where: Where, t: int | None, as_of: int | None) -> list[str]:
        body = f"?f khg:relation {s(relation)} ; khg:keyDigest {s(digest)} ."
        return self._ids_where(body, where, t, as_of, None, None)

    # -- fidelity number 2
    def native_bindings(self, rid: str) -> list[dict[str, Any]] | None:
        """The bindings of the current version of fact ``rid`` from the binding nodes' triples (not ``payload``)."""
        f = iri_encode(rid)
        rows = self.select(PREFIX + f"SELECT ?b ?p ?o WHERE {{ ?g khg:versionOf <{f}> . FILTER NOT EXISTS {{ ?g khg:txTo "
                                    f"?x }} GRAPH ?g {{ <{f}> a khg:Hyperedge ; khg:binding ?b . ?b ?p ?o }} }}")
        if not rows and not self._n_is_fact(rid):
            return None
        nodes: dict[str, dict[str, Any]] = {}
        for r in rows:
            nodes.setdefault(r["b"], {})[r["p"]] = r["o"]
        out = []
        for a in nodes.values():
            out.append(native_binding({
                "bid": a.get(K + "bid"), "role": a.get(K + "role"), "position": a.get(K + "position"),
                "direction": a.get(K + "direction"), "value_kind": a.get(K + "valueKind"),
                "ref": iri_decode(a[K + "value"]) if K + "value" in a else None,
                "value_json": a.get(K + "valueJSON"), "extensions": a.get(K + "extensions")}))
        return out

    def close(self) -> None:
        with contextlib.suppress(Exception):
            del self.store
        if self._owned:
            shutil.rmtree(self.path, ignore_errors=True)


def factory(schema: Any, clock: Any) -> OxigraphStore:
    """A fresh ``OxigraphStore`` in a temporary directory (removed by ``close``)."""
    return OxigraphStore(schema, clock=clock)
