"""Backend 2, reified RDF in the relation-instance pattern: pyoxigraph (Oxigraph) and rdflib, one SPARQL query set.

Layout. Each version of each record is one named graph ``<urn:khg:<id>/v<n>>`` (``/`` never occurs in an encoded
id, so the name is unambiguous). A hyperedge version's graph holds exactly P2's projection
``record.project.rdf_relation_instance`` of that version (fact IRI, one node per binding, ``khg:relation``,
``khg:status``, ``khg:binding``, ``khg:bid``, ``khg:role``, ``khg:position``, ``khg:direction``, ``khg:value`` /
``khg:valueKind`` or ``khg:valueJSON``) plus the triples the reads filter on:

    <f> khg:id "id" ; khg:rank ; khg:visibility ; khg:relKind ; khg:statusRef <iri> ; khg:keyDigest ;
        khg:sLo khg:sHi khg:eLo khg:eHi (xsd:integer) ; khg:nBindings ; khg:payload "canonical JSON" .
    <f#b> khg:ident "value identity" ; khg:valueKind "literal|special|unbound" ; khg:extensions "JSON" .

The default graph holds the version metadata (``<g> khg:versionOf <f> ; khg:version ; khg:txFrom ; khg:txTo ;
khg:recordedAt ; khg:recordedBy``) and the kept header (``<urn:khg:document> khg:header "JSON"``). No RDF 1.2 triple
term is needed: the pattern is RDF 1.1 plus named graphs (RDF 1.2 "basic").

Usage: python rdf_relation_instance.py [oxigraph|rdflib ...]. Writes out/rdf-<engine>.json.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from common import ReadOnlyProbe, assemble, fixture, hand_check, run_read_only, write_out
from khg_contracts.record.project import KHG_NS, RDF_TYPE, iri_decode, iri_encode, rdf_relation_instance

K = KHG_NS
XSD_INT = "http://www.w3.org/2001/XMLSchema#integer"
DOC = "urn:khg:document"
FLAGS = frozenset({"literal_values", "special_values", "goals", "nesting", "ordered_roles", "valid_time",
                   "transaction_time", "key_constraint", "atomic_writes", "history_export"})
PREFIX = f"PREFIX khg: <{K}>\n"


def graph_name(id: str, version: int) -> str:
    return f"{iri_encode(id)}/v{version}"


def lit(text: Any) -> dict[str, str]:
    return {"literal": str(text)}


def integer(n: int) -> dict[str, str]:
    return {"literal": str(n), "datatype": XSD_INT}


def s(text: str) -> str:
    """A SPARQL string literal."""
    return json.dumps(text, ensure_ascii=False)


class RDFProbe(ReadOnlyProbe):
    FLAGS = FLAGS

    # -- engine hooks: add quads, run a SELECT (rows as dicts of Python str/int/None)
    def _add(self, quads: list[tuple[str, str, Any, str | None]]) -> None: ...
    def _select(self, query: str) -> list[dict[str, Any]]: ...

    def _write(self, entities: list[dict], facts: list[dict], bindings: list[dict]) -> None:
        quads: list[tuple[str, str, Any, str | None]] = [
            (DOC, K + "header", lit(json.dumps(self._header)), None),
            (DOC, K + "documents", lit(json.dumps(self._documents)), None)]
        by_fact: dict[tuple[str, int], list[dict]] = {}
        for b in bindings:
            by_fact.setdefault((b["fact_id"], b["version"]), []).append(b)
        for row, kind in [(e, "entity") for e in entities] + [(f, "fact") for f in facts]:
            g = graph_name(row["id"], row["version"])
            quads += [(g, K + "versionOf", iri_encode(row["id"]), None),
                      (g, K + "version", integer(row["version"]), None),
                      (g, K + "txFrom", integer(row["tx_from"]), None),
                      (g, K + "recordedAt", lit(row["recorded_at"]), None),
                      (g, K + "recordedBy", lit(row["recorded_by"]), None)]
            if row["tx_to"] is not None:
                quads.append((g, K + "txTo", integer(row["tx_to"]), None))
            f = iri_encode(row["id"])
            if kind == "entity":
                quads += [(f, RDF_TYPE, K + "Entity", g), (f, K + "id", lit(row["id"]), g),
                          (f, K + "record", lit(row["record"]), g)]
                continue
            rows = by_fact.get((row["id"], row["version"]), [])
            rec = assemble(row, rows)
            quads += [(a, b, c, g) for a, b, c in rdf_relation_instance({"records": [rec]})]
            quads += [(f, K + "id", lit(row["id"]), g), (f, K + "rank", lit(row["rank"]), g),
                      (f, K + "visibility", lit(row["visibility"]), g), (f, K + "relKind", lit(row["rel_kind"]), g),
                      (f, K + "nBindings", integer(row["n_bindings"]), g), (f, K + "payload", lit(row["payload"]), g)]
            for col, pred in (("s_lo", "sLo"), ("s_hi", "sHi"), ("e_lo", "eLo"), ("e_hi", "eHi")):
                quads.append((f, K + pred, integer(row[col]), g))
            if row["status_ref"] is not None:
                quads.append((f, K + "statusRef", iri_encode(row["status_ref"]), g))
            if row["key_digest"] is not None:
                quads.append((f, K + "keyDigest", lit(row["key_digest"]), g))
            for b in rows:
                n = f + "#" + b["bid"]
                if b["ident"] is not None:
                    quads.append((n, K + "ident", lit(b["ident"]), g))
                if b["value_kind"] not in ("entity", "fact"):
                    quads.append((n, K + "valueKind", lit(b["value_kind"]), g))
                if b["extensions"] is not None:
                    quads.append((n, K + "extensions", lit(b["extensions"]), g))
        self._add(quads)
        self.n_quads = len(quads)

    # -- query parts
    @staticmethod
    def _current(t: int | None) -> str:
        if t is None:
            return "?g khg:versionOf ?f . FILTER NOT EXISTS { ?g khg:txTo ?txTo }"
        return (f"?g khg:versionOf ?f ; khg:txFrom ?from . FILTER(?from <= {t}) "
                f"OPTIONAL {{ ?g khg:txTo ?txTo }} FILTER(!BOUND(?txTo) || ?txTo > {t})")

    @staticmethod
    def _filters(where: Any, as_of: int | None) -> str:
        def one_of(var: str, values: Any) -> str:
            vs = sorted(values)
            return f"FILTER({var} IN ({', '.join(s(v) for v in vs)}))" if vs else "FILTER(false)"

        parts = ["?f khg:status ?st ; khg:rank ?rk ; khg:visibility ?vis ; khg:relKind ?kind ; khg:id ?id .",
                 one_of("?st", where.status), one_of("?rk", where.rank), one_of("?vis", where.visibility),
                 one_of("?kind", where.kinds)]
        if as_of is not None:
            lo, hi = ("khg:sHi", "khg:eLo") if where.valid_mode == "definite" else ("khg:sLo", "khg:eHi")
            parts += [f"?f {lo} ?vlo ; {hi} ?vhi .", f"FILTER(?vlo <= {as_of} && {as_of} < ?vhi)"]
        return "\n    ".join(parts)

    @staticmethod
    def _tail(after: str | None, limit: int | None) -> tuple[str, str]:
        cond = f"FILTER(?id > {s(after)})" if after is not None else ""
        tail = "ORDER BY ?id" + (f" LIMIT {int(limit)}" if limit is not None else "")
        return cond, tail

    def _ids_where(self, body: str, where: Any, t: int | None, as_of: int | None, after: str | None,
                   limit: int | None) -> list[str]:
        cond, tail = self._tail(after, limit)
        q = (PREFIX + f"SELECT DISTINCT ?id WHERE {{\n  {self._current(t)}\n  GRAPH ?g {{\n    {body}\n    "
             f"{self._filters(where, as_of)}\n    {cond}\n  }}\n}} {tail}")
        self.last_sparql = q
        return [r["id"] for r in self._select(q)]

    # -- reads
    def _graph_of(self, id: str, t: int | None, version: int | None) -> str | None:
        f = iri_encode(id)
        if version is not None:
            cond = f"?g khg:version {version} ; khg:txFrom ?from ." + (f" FILTER(?from <= {t})" if t is not None else "")
            q = PREFIX + f"SELECT ?g WHERE {{ ?g khg:versionOf <{f}> . {cond} }}"
        else:
            q = PREFIX + f"SELECT ?g WHERE {{ BIND(<{f}> AS ?f) {self._current(t)} }}"
        rows = self._select(q)
        return rows[0]["g"] if rows else None

    def _record_in(self, g: str) -> dict:
        rows = self._select(PREFIX + f"SELECT ?s ?p ?o WHERE {{ GRAPH <{g}> {{ ?s ?p ?o }} }}")
        meta = {r["p"]: r["o"] for r in self._select(PREFIX + f"SELECT ?p ?o WHERE {{ <{g}> ?p ?o }}")}
        subj: dict[str, dict[str, Any]] = {}
        for r in rows:
            subj.setdefault(r["s"], {})[r["p"]] = r["o"]
        f = g.rsplit("/v", 1)[0]
        top = subj[f]
        if top.get(RDF_TYPE) == K + "Entity":
            return json.loads(top[K + "record"])
        fact = {"id": top[K + "id"], "version": meta[K + "version"], "recorded_at": meta[K + "recordedAt"],
                "recorded_by": meta[K + "recordedBy"], "relation": top[K + "relation"], "status": top[K + "status"],
                "rank": top[K + "rank"], "visibility": top[K + "visibility"], "payload": top[K + "payload"],
                "status_ref": iri_decode(top[K + "statusRef"]) if K + "statusRef" in top else None}
        brs = []
        for n, a in subj.items():
            if n == f:
                continue
            kind = a.get(K + "valueKind")
            brs.append({"bid": a[K + "bid"], "role": a[K + "role"],
                        "position": int(a[K + "position"]) if K + "position" in a else None,
                        "direction": a.get(K + "direction"), "value_kind": kind,
                        "ref": iri_decode(a[K + "value"]) if K + "value" in a else None,
                        "value_json": a.get(K + "valueJSON"), "extensions": a.get(K + "extensions")})
        return assemble(fact, brs)

    def _get(self, id: str, t: int | None, version: int | None) -> dict | None:
        g = self._graph_of(id, t, version)
        return self._record_in(g) if g else None

    def _versions(self, id: str) -> list[dict]:
        rows = self._select(PREFIX + f"SELECT ?g ?v WHERE {{ ?g khg:versionOf <{iri_encode(id)}> ; khg:version ?v }} "
                                     "ORDER BY ?v")
        return [self._record_in(r["g"]) for r in rows]

    def _ids(self, t: int | None) -> list[str]:
        rows = self._select(PREFIX + f"SELECT DISTINCT ?id WHERE {{ {self._current(t)} GRAPH ?g {{ ?f khg:id ?id }} }}")
        return sorted(r["id"] for r in rows)

    def _is_fact(self, id: str) -> bool:
        f = iri_encode(id)
        return bool(self._select(PREFIX + f"SELECT ?g WHERE {{ GRAPH ?g {{ <{f}> a khg:Hyperedge }} }} LIMIT 1"))

    def _incident_ids(self, node, role, relation, where, t, as_of, after, limit) -> list[str]:
        body = f"?f khg:binding ?b . ?b khg:value <{iri_encode(node)}> ."
        if role is not None:
            body += f" ?b khg:role {s(role)} ."
        if relation is not None:
            body += f" ?f khg:relation {s(relation)} ."
        return self._ids_where(body, where, t, as_of, after, limit)

    def _find_ids(self, relation, pats, match, where, t, as_of, after, limit) -> list[str]:
        body = [f"?f khg:relation {s(relation)} ."]
        for i, p in enumerate(pats, 1):
            body.append(f"?f khg:binding ?b{i} . ?b{i} khg:role {s(p.role)} .")
            if p.position is not None:
                body.append(f"?b{i} khg:position {s(str(p.position))} .")
            if p.kind == "value":
                body.append(f"?b{i} khg:ident {s(p.ident)} .")
            elif p.kind == "any_unbound":
                body.append(f"?b{i} khg:valueKind \"unbound\" .")
            body += [f"FILTER(?b{i} != ?b{j})" for j in range(1, i)]
        if match == "exact":
            body.append(f"?f khg:nBindings {len(pats)} .")
        return self._ids_where("\n    ".join(body), where, t, as_of, after, limit)

    def _key_ids(self, relation, digest, where, t, as_of) -> list[str]:
        body = f"?f khg:relation {s(relation)} ; khg:keyDigest {s(digest)} ."
        return self._ids_where(body, where, t, as_of, None, None)

    def native_walk(self, id: str, direction: str = "forward") -> list[list]:
        """Breadth first, one SPARQL query per level: a property path cannot test the role of the binding node
        or the status of the lifecycle record it passes through."""
        frm, to = ("khg:superseded", "khg:superseding") if direction == "forward" else \
            ("khg:superseding", "khg:superseded")
        steps, seen, frontier, depth = [], {id}, [id], 0
        while frontier:
            depth += 1
            nxt = []
            for fact in frontier:
                q = PREFIX + f"""SELECT ?sid ?to WHERE {{
  {self._current(None).replace('?f', '?s')}
  GRAPH ?g {{ ?s khg:relation "khg:supersedes" ; khg:status "asserted" ; khg:id ?sid ;
             khg:binding ?b1, ?b2 . ?b1 khg:role {s(frm)} ; khg:value <{iri_encode(fact)}> .
             ?b2 khg:role {s(to)} ; khg:value ?toIri . BIND(STR(?toIri) AS ?to) }}
}} ORDER BY ?sid ?to"""
                for r in self._select(q):
                    target = iri_decode(r["to"])
                    steps.append([depth, r["sid"], fact, target])
                    if target not in seen:
                        seen.add(target)
                        nxt.append(target)
            frontier = sorted(nxt)
        self.walk_sparql = q
        return steps


class Oxigraph(RDFProbe):
    NAME = "oxigraph"

    def _open(self) -> None:
        import pyoxigraph

        self.ox = pyoxigraph
        self.store = pyoxigraph.Store()  # in memory; Store(path) is the RocksDB-backed on-disk store

    def _term(self, x: Any) -> Any:
        ox = self.ox
        if isinstance(x, dict):
            return ox.Literal(x["literal"], datatype=ox.NamedNode(x["datatype"])) if "datatype" in x else \
                ox.Literal(x["literal"])
        return ox.NamedNode(x)

    def _add(self, quads) -> None:
        ox = self.ox
        self.store.bulk_extend([ox.Quad(ox.NamedNode(a), ox.NamedNode(b), self._term(c),
                                        ox.NamedNode(g) if g else ox.DefaultGraph()) for a, b, c, g in quads])

    def _select(self, query: str) -> list[dict[str, Any]]:
        res = self.store.query(query)
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


class RDFLib(RDFProbe):
    NAME = "rdflib"

    def _open(self) -> None:
        import rdflib

        self.rdflib = rdflib
        self.ds = rdflib.Dataset()

    def _term(self, x: Any) -> Any:
        rl = self.rdflib
        if isinstance(x, dict):
            return rl.Literal(x["literal"], datatype=rl.URIRef(x["datatype"])) if "datatype" in x else \
                rl.Literal(x["literal"])
        return rl.URIRef(x)

    def _add(self, quads) -> None:
        rl = self.rdflib
        for a, b, c, g in quads:
            ctx = self.ds.graph(rl.URIRef(g)) if g else self.ds.default_graph
            ctx.add((rl.URIRef(a), rl.URIRef(b), self._term(c)))

    def _select(self, query: str) -> list[dict[str, Any]]:
        rl = self.rdflib
        res = self.ds.query(query)
        out = []
        for row in res:
            d = {}
            for n in res.vars:
                term = row[n]
                if term is None:
                    d[str(n)] = None
                elif isinstance(term, rl.Literal):
                    d[str(n)] = int(term) if term.datatype is not None and str(term.datatype) == XSD_INT else str(term)
                else:
                    d[str(n)] = str(term)
            out.append(d)
        return out


PROBES = {"oxigraph": Oxigraph, "rdflib": RDFLib}


def main(names: list[str]) -> None:
    import time

    for name in names:
        cls = PROBES[name]
        container, schema = fixture()
        store = cls(schema)
        store.load(container)
        if name == "oxigraph":
            import pyoxigraph
            version = pyoxigraph.__version__
        else:
            import rdflib
            version = rdflib.__version__
        result: dict[str, Any] = {"backend": name, "version": version, "quads": store.n_quads,
                                  "native_write_seconds": round(store.write_seconds, 4)}
        started = time.perf_counter()
        result["hand"] = hand_check(store)
        result["hand_seconds"] = round(time.perf_counter() - started, 3)
        store.find("co_administration_causes", [{"role": "agent", "value": {"entity": "ex:insulin"}},
                                                {"role": "agent", "value": {"entity": "ex:metformin"}}])
        result["find_sparql_example"] = store.last_sparql
        result["walk_sparql_level_query"] = store.walk_sparql
        store.close()
        started = time.perf_counter()
        result["read_only_scenarios"] = run_read_only(lambda s_, c: cls(s_, clock=c))
        result["scenario_seconds"] = round(time.perf_counter() - started, 2)
        print(name, version, result["read_only_scenarios"]["counts"], "export diffs:",
              result["hand"]["export khg-json round trip"]["differences"],
              "hand mismatches:", [k for k, v in result["hand"].items()
                                   if isinstance(v, dict) and (v.get("same_as_reference") is False or "error" in v)],
              "seconds:", result["scenario_seconds"])
        write_out(f"rdf-{name}", result)


if __name__ == "__main__":
    main(sys.argv[1:] or list(PROBES))
