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
which Oxigraph applies all or nothing. A trusted load into an empty store writes its quads with ``bulk_extend`` (not
transactional: on a failure the store is cleared and its own triples put back), then one ``update`` for the store's
own triples. A load reads the stored versions of the ids it brings in one query per chunk (``prefetch``; none on an
empty store). **Reads** fetch the versions of one call in one query per chunk of ids (``VALUES``), one solution per
binding, rebuilt by ``rows.record_of``. ``trips`` counts every query, update and bulk call.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from typing import Any, Iterable, Iterator, Mapping, Sequence

from khg_contracts import jsonio
from khg_contracts.record.project import KHG_NS, RDF_TYPE, iri_decode, iri_encode, rdf_relation_instance
from khg_contracts.store import Where
from khg_contracts.store.table import Entry, TableStore, VersionTable

from .native import NativeReads
from .rows import Pat, binding_rows, fact_row, native_binding, query_instant, record_of
from .shared import AdapterMixin, Trips

__all__ = ["CHUNK", "OxigraphStore", "OxigraphTable", "factory", "graph_name"]

K = KHG_NS
XSD_INT = "http://www.w3.org/2001/XMLSchema#integer"
STORE = "urn:khg:store"
PREFIX = f"PREFIX khg: <{K}>\n"
#: Ids per ``VALUES`` block.
CHUNK = 500
_UNSET: Any = object()
#: The variables of one version row: the fact row, the entity record, and one binding row.
_ROW = ("?f ?g ?id ?version ?tx_from ?recorded_at ?recorded_by ?record ?relation ?status ?sr ?rank ?visibility "
        "?payload ?bid ?role ?position ?direction ?value_kind ?refnode ?ident ?value_json ?extensions")


def graph_name(id: str, version: int) -> str:
    return f"{iri_encode(id)}/v{version}"


def s(text: str) -> str:
    """A SPARQL string literal."""
    return json.dumps(text, ensure_ascii=False)


def _chunks(items: Sequence[Any], size: int = CHUNK) -> Iterator[list[Any]]:
    for i in range(0, len(items), size):
        yield list(items[i:i + size])


def _versions_query(cond: str, values: Sequence[str] | None) -> str:
    """One solution per binding of every version whose metadata pass ``cond`` (of the ids in ``values``)."""
    vals = "VALUES ?f { " + " ".join(f"<{iri_encode(i)}>" for i in values) + " }" if values is not None else ""
    return (PREFIX + f"SELECT {_ROW} WHERE {{\n  {vals}\n"
            "  ?g khg:versionOf ?f ; khg:version ?version ; khg:txFrom ?tx_from ; khg:recordedAt ?recorded_at ; "
            f"khg:recordedBy ?recorded_by .\n  {cond}\n"
            "  GRAPH ?g {\n    ?f khg:id ?id .\n    OPTIONAL { ?f khg:record ?record }\n"
            "    OPTIONAL { ?f khg:relation ?relation ; khg:status ?status ; khg:rank ?rank ; "
            "khg:visibility ?visibility ; khg:payload ?payload . OPTIONAL { ?f khg:statusRef ?sr } }\n"
            "    OPTIONAL { ?f khg:binding ?b . ?b khg:bid ?bid ; khg:role ?role .\n"
            "      OPTIONAL { ?b khg:position ?position } OPTIONAL { ?b khg:direction ?direction }\n"
            "      OPTIONAL { ?b khg:valueKind ?value_kind } OPTIONAL { ?b khg:value ?refnode }\n"
            "      OPTIONAL { ?b khg:ident ?ident } OPTIONAL { ?b khg:valueJSON ?value_json }\n"
            "      OPTIONAL { ?b khg:extensions ?extensions } }\n  }\n}")


def _assemble(solutions: Iterable[Mapping[str, Any]]) -> list[tuple[str, int, int, dict[str, Any]]]:
    """``(id, version, tx_from, record)`` of each version in ``solutions`` (one per binding), by ``rows.record_of``;
    the columns only are renamed here."""
    versions: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for r in solutions:
        got = versions.get(r["g"])
        if got is None:
            row = {"id": r["id"], "version": r["version"], "tx_from": r["tx_from"], "recorded_at": r["recorded_at"],
                   "recorded_by": r["recorded_by"], "record": r["record"], "relation": r["relation"],
                   "status": r["status"], "status_ref": iri_decode(r["sr"]) if r["sr"] is not None else None,
                   "rank": r["rank"], "visibility": r["visibility"], "payload": r["payload"]}
            got = versions[r["g"]] = (row, [])
        if r["bid"] is not None:
            got[1].append({"bid": r["bid"], "role": r["role"], "position": r["position"],
                           "direction": r["direction"], "value_kind": r["value_kind"],
                           "ref": iri_decode(r["refnode"]) if r["refnode"] is not None else None,
                           "ident": r["ident"], "value_json": r["value_json"], "extensions": r["extensions"]})
    out = [(row["id"], int(row["version"]), int(row["tx_from"]), record_of(row, binds))
           for row, binds in versions.values()]
    out.sort(key=lambda x: (x[0], x[1]))
    return out


class OxigraphTable:
    """The version table over the store, with an overlay for the versions of the write in progress."""

    def __init__(self, schema: Any, owner: OxigraphStore):
        self.schema = schema
        self.owner = owner
        self.overlay = VersionTable(schema)
        self.bulk_empty = False  # set by the store: a load began on an empty store
        self._latest: Any = _UNSET
        self._cache: dict[str, list[Entry]] = {}  # stored versions by id (prefetched or read in this write)

    # -- plumbing
    def reset(self) -> None:
        self.overlay = VersionTable(self.schema)
        self.bulk_empty = False
        self._latest = _UNSET
        self._cache.clear()

    def select(self, query: str) -> Any:
        return self.owner.select(query)

    def is_empty(self) -> bool:
        """Whether the store holds no version (one ``ASK``)."""
        return not self.select(PREFIX + "ASK { ?g khg:versionOf ?x }")

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
        if rid in self.overlay or self._cache.get(rid):
            return True
        if rid in self._cache:
            return False
        return bool(self.select(PREFIX + f"ASK {{ ?g khg:versionOf <{iri_encode(rid)}> }}"))

    def __len__(self) -> int:
        return len(self._stored_ids() | set(self.overlay.ids()))

    def ids(self) -> list[str]:
        return sorted(self._stored_ids() | set(self.overlay.ids()))

    # -- prefetch (the optional member; TableStore.load calls it)
    def prefetch(self, records: Iterable[Mapping[str, Any]]) -> None:
        """Read the stored versions of the ids a load brings: one query per ``CHUNK`` ids, none on an empty
        store."""
        ids = sorted({jsonio.nfc(r["id"]) for r in records} - set(self._cache))
        for rid in ids:
            self._cache[rid] = []
        if not ids or self.bulk_empty:
            return
        for chunk in _chunks(ids):
            for rid, _, t, rec in _assemble(self.select(_versions_query("", chunk))):
                self._cache[rid].append(Entry(rec, t, self.schema))

    # -- versions
    def stored(self, rid: str) -> list[Entry]:
        got = self._cache.get(rid)
        if got is None:
            got = [Entry(rec, t, self.schema) for _, _, t, rec in
                   _assemble(self.select(_versions_query("", [rid])))]
            self._cache[rid] = got
        return got

    def entries(self, rid: str) -> list[Entry]:
        return self.stored(rid) + self.overlay.entries(rid)

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

    ENGINE = "Oxigraph"
    KIND = "embedded"
    INT64 = True

    def __init__(self, schema: Any, *, path: str | os.PathLike | None = None, clock: Any = None,
                 capabilities: Iterable[str] | None = None, store_id: str = "oxigraph"):
        import pyoxigraph

        self.ox = pyoxigraph
        self.trips = Trips()
        self._owned = path is None
        self.path = tempfile.mkdtemp(prefix="khg-oxigraph-", dir=os.environ.get("P1_TMP") or None) \
            if path is None else os.fspath(path)
        self.store = pyoxigraph.Store(self.path)
        super().__init__(schema, table=lambda sch: OxigraphTable(sch, self), clock=clock,
                         capabilities=self.FLAGS if capabilities is None else capabilities, store_id=store_id)
        self._bulk = False
        self._read_header()

    def engine_version(self) -> str:
        return f"{self.ox.__version__} (pyoxigraph)"

    # -- terms, queries and updates (every engine call goes through select, _update or _bulk_write)
    def _term(self, x: Any) -> Any:
        ox = self.ox
        if isinstance(x, dict):
            return ox.Literal(x["literal"], datatype=ox.NamedNode(x["datatype"])) if "datatype" in x else \
                ox.Literal(x["literal"])
        return ox.NamedNode(x)

    def select(self, query: str) -> Any:
        self.trips.hit("read")
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

    def _update(self, text: str) -> None:
        self.trips.hit("write")
        self.store.update(text)

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

    def _quad(self, quad: tuple[str, str, Any, str | None]) -> Any:
        a, b, c, g = quad
        return self.ox.Quad(self._term(a), self._term(b), self._term(c),
                            self._term(g) if g else self.ox.DefaultGraph())

    def _pending_quads(self) -> list[tuple[str, str, Any, str | None]]:
        """The quads of the overlay's versions, with ``txTo`` on every version a later one supersedes."""
        table: OxigraphTable = self._table
        out = []
        for rid in table.overlay.ids():
            stored = table.stored(rid)
            new = table.overlay.entries(rid)
            if stored:
                prev = stored[-1]
                out.append((graph_name(rid, prev.record["version"]), K + "txTo",
                            {"literal": str(new[0].t), "datatype": XSD_INT}, None))
            for i, e in enumerate(new):
                out += self.quads(e.record, e.t, new[i + 1].t if i + 1 < len(new) else None)
        return out

    def _meta_update(self, header: Any, documents: Any, latest: int | None) -> str:
        """The update that replaces the store's own triples: ``(header, documents, latest)``."""
        parts = [f"DELETE WHERE {{ <{STORE}> ?p ?o }}"]
        meta = []
        if latest is not None:
            meta.append((STORE, K + "latest", {"literal": str(latest), "datatype": XSD_INT}, None))
        meta.append((STORE, K + "header", {"literal": json.dumps(header, ensure_ascii=False)}, None))
        meta.append((STORE, K + "documents", {"literal": json.dumps(documents, ensure_ascii=False)}, None))
        parts.append("INSERT DATA { " + " ".join(self._quad_text(q) for q in meta) + " }")
        return " ;\n".join(parts)

    # -- transactions
    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        table: OxigraphTable = self._table
        table.reset()
        before = (self.kept_header, self.kept_documents, table.latest)
        try:
            yield
            quads = self._pending_quads()
            after = (self.kept_header, self.kept_documents, table.latest)
            if self._bulk and table.bulk_empty and quads:
                self._bulk_write(quads, after, before)
            elif quads or after != before:
                body = " ".join(self._quad_text(q) for q in quads)
                self._update(self._meta_update(*after) + (f" ;\nINSERT DATA {{ {body} }}" if body else ""))
        finally:
            table.reset()

    def _bulk_write(self, quads: list[tuple[str, str, Any, str | None]], after: tuple, before: tuple) -> None:
        """``bulk_extend`` into the empty store, then the store's own triples. ``bulk_extend`` is not
        transactional: on a failure the store is cleared and its own triples, as they were, are put back."""
        try:
            self.trips.hit("write")
            self.store.bulk_extend(self._quad(q) for q in quads)
            self._update(self._meta_update(*after))
        except BaseException:
            self.trips.hit("write")
            self.store.clear()
            if before != (None, [], None):
                self._update(self._meta_update(*before))
            raise

    def load(self, container: Any, **kwargs: Any) -> Any:
        """Trusted bulk import: ``TableStore``'s checks over the prefetched ids, then ``bulk_extend`` into an empty
        store (review 01, R-01: the flag holds until the transaction has committed)."""
        self._bulk = True
        try:
            with self.writing():
                self._table.bulk_empty = self._table.is_empty()
                return TableStore.load(self, container, **kwargs)
        finally:
            self._bulk = False

    def _read_header(self) -> None:
        rows = self.select(PREFIX + f"SELECT ?h ?d WHERE {{ <{STORE}> khg:header ?h ; khg:documents ?d }}")
        if rows:
            self.kept_header = json.loads(rows[0]["h"])
            self.kept_documents = json.loads(rows[0]["d"])

    # -- query parts
    @staticmethod
    def _current(t: int | None) -> str:
        if t is None:
            return "?g khg:versionOf ?f . FILTER NOT EXISTS { ?g khg:txTo ?txTo }"
        return (f"?g khg:versionOf ?f ; khg:txFrom ?from . FILTER(?from <= {int(t)}) "
                f"OPTIONAL {{ ?g khg:txTo ?txTo }} FILTER(!BOUND(?txTo) || ?txTo > {int(t)})")

    @staticmethod
    def _open_at(t: int | None) -> str:
        """The condition on ``?g`` (bound by ``_versions_query``) that its version is the one open at ``t``."""
        if t is None:
            return "FILTER NOT EXISTS { ?g khg:txTo ?txTo }"
        return (f"FILTER(?tx_from <= {int(t)}) OPTIONAL {{ ?g khg:txTo ?txTo }} "
                f"FILTER(!BOUND(?txTo) || ?txTo > {int(t)})")

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

    def _where(self, body: str, where: Where, t: int | None, as_of: int | None, after: str | None) -> str:
        cond = f"FILTER(?id > {s(after)})" if after is not None else ""
        return (f"{{\n  {self._current(t)}\n  GRAPH ?g {{\n    {body}\n    {self._filters(where, as_of)}\n    {cond}\n"
                "  }\n}")

    def _ids_where(self, body: str, where: Where, t: int | None, as_of: int | None, after: str | None,
                   limit: int | None) -> list[str]:
        tail = "ORDER BY ?id" + (f" LIMIT {int(limit)}" if limit is not None else "")
        q = PREFIX + f"SELECT DISTINCT ?id WHERE {self._where(body, where, t, as_of, after)} {tail}"
        return [r["id"] for r in self.select(q)]

    # -- native reads
    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        got: dict[str, dict[str, Any]] = {}
        for chunk in _chunks([i for i in ids if isinstance(i, str)]):
            for rid, _, _, rec in _assemble(self.select(_versions_query(self._open_at(t), chunk))):
                got[rid] = rec
        return [got[i] for i in ids if i in got]

    def _n_scan(self, t: int | None, history: bool) -> list[dict[str, Any]]:
        if history:
            cond = "" if t is None else f"FILTER(?tx_from <= {int(t)})"
        else:
            cond = self._open_at(t)
        return [rec for _, _, _, rec in _assemble(self.select(_versions_query(cond, None)))]

    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
        if not isinstance(id, str):
            return None
        if version is None:
            got = self._n_records([id], t)
            return got[0] if got else None
        cond = f"FILTER(?version = {int(version)})" + (f" FILTER(?tx_from <= {int(t)})" if t is not None else "")
        got = _assemble(self.select(_versions_query(cond, [id])))
        return got[-1][3] if got else None

    def _n_versions(self, id: str, t: int | None = None) -> list[dict[str, Any]]:
        if not isinstance(id, str):
            return []
        cond = "" if t is None else f"FILTER(?tx_from <= {int(t)})"
        return [rec for _, _, _, rec in _assemble(self.select(_versions_query(cond, [id])))]

    def _n_is_fact(self, id: str) -> bool:
        return bool(self.select(PREFIX + f"ASK {{ GRAPH ?g {{ <{iri_encode(id)}> a khg:Hyperedge }} }}"))

    @staticmethod
    def _incident_body(node: str, role: str | None, relation: str | None) -> str:
        body = f"?f khg:binding ?b . ?b khg:value <{iri_encode(node)}> ."
        if role is not None:
            body += f" ?b khg:role {s(role)} ."
        if relation is not None:
            body += f" ?f khg:relation {s(relation)} ."
        return body

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        return self._ids_where(self._incident_body(node, role, relation), where, t, as_of, after, limit)

    def _n_count(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                 as_of: int | None) -> int:
        q = PREFIX + (f"SELECT (COUNT(DISTINCT ?id) AS ?n) WHERE "
                      f"{self._where(self._incident_body(node, role, relation), where, t, as_of, None)}")
        return int(self.select(q)[0]["n"])

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

    def _n_bound_by(self, relation: str, role: str, idents: Sequence[str], where: Where, t: int | None,
                    as_of: int | None) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for chunk in _chunks(list(idents)):
            body = (f"?f khg:relation {s(relation)} ; khg:binding ?b . ?b khg:role {s(role)} ; khg:ident ?ident . "
                    "VALUES ?ident { " + " ".join(s(i) for i in chunk) + " }")
            q = PREFIX + f"SELECT DISTINCT ?ident ?id WHERE {self._where(body, where, t, as_of, None)} ORDER BY ?id"
            for r in self.select(q):
                out.setdefault(r["ident"], []).append(r["id"])
        return out

    # -- fidelity number 2
    def native_bindings(self, rid: str) -> list[dict[str, Any]] | None:
        """The bindings of the current version of fact ``rid`` from the binding nodes' structural triples and their
        ``khg:ident`` (``rows.native_binding``; not ``khg:valueJSON``, not ``payload``)."""
        f = iri_encode(rid)
        rows = self.select(PREFIX + f"SELECT ?b ?p ?o WHERE {{ ?g khg:versionOf <{f}> . "
                                    f"FILTER NOT EXISTS {{ ?g khg:txTo ?x }} "
                                    f"GRAPH ?g {{ <{f}> a khg:Hyperedge ; khg:binding ?b . ?b ?p ?o }} }}")
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
                "ident": a.get(K + "ident"), "extensions": a.get(K + "extensions")}))
        return out

    def close(self) -> None:
        with contextlib.suppress(Exception):
            del self.store
        if self._owned:
            shutil.rmtree(self.path, ignore_errors=True)


def factory(schema: Any, clock: Any) -> OxigraphStore:
    """A fresh ``OxigraphStore`` in a temporary directory (removed by ``close``)."""
    return OxigraphStore(schema, clock=clock)
