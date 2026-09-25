"""Backend 3, the bipartite property graph: Neo4j Community, Memgraph and FalkorDB with one Cypher query set.

Layout (fact nodes and entity nodes, role-labelled edges; versions as nodes so that transaction time is kept):

    (:Node {id, kind})                                   one identity node per entity id and per fact id
    (:Version {id, version, tx_from, tx_to, kind, relation, rel_kind, status, status_ref, rank, visibility,
               key_digest, s_lo, s_hi, e_lo, e_hi, n_bindings, payload | record})-[:VERSION_OF]->(:Node)
    (:Version)-[:BINDS {bid, role, position, direction, value_kind, ref, ident, value_json, extensions}]->(target)
        target = the (:Node) of an entity or fact value; a shared (:Literal {ident}) per literal identity;
                 a (:Special {key}) per binding for somevalue, novalue and unbound
    (:Doc {header, documents})

Every node also carries a per-store namespace label, because Neo4j Community and Memgraph Community hold one user
database and the conformance runner opens a second store while the first is open (reload and determinism checks).

Usage: python pg_cypher.py [neo4j|memgraph|falkordb ...]. Neo4j on bolt://127.0.0.1:7687, Memgraph on :7688,
FalkorDB (redis) on :6380. Writes out/pg-<engine>.json.
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from typing import Any

from common import ReadOnlyProbe, assemble, fixture, hand_check, run_read_only, write_out

FLAGS = frozenset({"literal_values", "special_values", "goals", "nesting", "ordered_roles", "valid_time",
                   "transaction_time", "key_constraint", "atomic_writes", "history_export"})
_ns = itertools.count(1)
VERSION_PROPS = ("id", "version", "tx_from", "tx_to", "recorded_at", "recorded_by", "relation", "rel_kind", "status",
                 "status_ref", "rank", "visibility", "key_digest", "s_lo", "s_hi", "e_lo", "e_hi", "n_bindings",
                 "payload")
BIND_PROPS = ("bid", "role", "position", "direction", "value_kind", "ref", "ident", "value_json", "extensions")


def clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


class CypherProbe(ReadOnlyProbe):
    FLAGS = FLAGS

    def _run(self, q: str, params: dict | None = None) -> list[dict]: ...
    def _connect(self) -> None: ...
    def _indexes(self) -> list[str]: return []

    def _open(self) -> None:
        self.ns = f"S{int(time.time() * 1000) % 10**9}_{next(_ns)}"
        self._connect()
        for q in self._indexes():
            try:
                self._run(q)
            except Exception:  # noqa: BLE001 - an index that exists already
                pass

    def close(self) -> None:
        try:
            self._run(f"MATCH (n:{self.ns}) DETACH DELETE n")
        except Exception:  # noqa: BLE001
            pass

    def _write(self, entities: list[dict], facts: list[dict], bindings: list[dict]) -> None:
        ns = self.ns
        self._run(f"CREATE (:Doc:{ns} {{header: $h, documents: $d}})",
                  {"h": json.dumps(self._header), "d": json.dumps(self._documents)})
        nodes = sorted({(e["id"], "entity") for e in entities} | {(f["id"], "fact") for f in facts})
        self._run(f"UNWIND $rows AS r CREATE (:Node:{ns} {{id: r.id, kind: r.kind}})",
                  {"rows": [{"id": i, "kind": k} for i, k in nodes]})
        vrows = [clean(dict(e, kind="entity")) for e in entities] + \
                [clean({**{k: f[k] for k in VERSION_PROPS}, "kind": "fact"}) for f in facts]
        self._run(f"UNWIND $rows AS r MATCH (n:Node:{ns} {{id: r.id}}) CREATE (v:Version:{ns}) SET v = r "
                  f"CREATE (v)-[:VERSION_OF]->(n)", {"rows": vrows})
        by_kind: dict[str, list[dict]] = {"node": [], "literal": [], "special": []}
        for b in bindings:
            props = clean({k: b[k] for k in BIND_PROPS})
            row = {"fact_id": b["fact_id"], "version": b["version"], "props": props, "ref": b["ref"],
                   "ident": b["ident"], "key": f"{b['fact_id']}#{b['version']}#{b['bid']}"}
            kind = "node" if b["value_kind"] in ("entity", "fact") else \
                "literal" if b["value_kind"] == "literal" else "special"
            by_kind[kind].append(row)
        head = f"UNWIND $rows AS r MATCH (v:Version:{ns} {{id: r.fact_id, version: r.version}}) "
        self._run(head + f"MATCH (t:Node:{ns} {{id: r.ref}}) CREATE (v)-[e:BINDS]->(t) SET e = r.props",
                  {"rows": by_kind["node"]})
        self._run(head + f"MERGE (t:Literal:{ns} {{ident: r.ident}}) CREATE (v)-[e:BINDS]->(t) SET e = r.props",
                  {"rows": by_kind["literal"]})
        self._run(head + f"CREATE (t:Special:{ns} {{key: r.key}}) CREATE (v)-[e:BINDS]->(t) SET e = r.props",
                  {"rows": by_kind["special"]})

    # -- query parts
    @staticmethod
    def _current(t: int | None, p: dict) -> str:
        if t is None:
            return "v.tx_to IS NULL"
        p["t"] = t
        return "v.tx_from <= $t AND (v.tx_to IS NULL OR v.tx_to > $t)"

    @staticmethod
    def _filters(where: Any, as_of: int | None, p: dict) -> str:
        p.update(st=sorted(where.status), rk=sorted(where.rank), vis=sorted(where.visibility),
                 kinds=sorted(where.kinds))
        out = "v.status IN $st AND v.rank IN $rk AND v.visibility IN $vis AND v.rel_kind IN $kinds"
        if as_of is not None:
            lo, hi = ("s_hi", "e_lo") if where.valid_mode == "definite" else ("s_lo", "e_hi")
            p["asof"] = as_of
            out += f" AND v.{lo} <= $asof AND $asof < v.{hi}"
        return out

    @staticmethod
    def _tail(after: str | None, limit: int | None, p: dict) -> tuple[str, str]:
        cond = ""
        if after is not None:
            cond = " AND v.id > $after"
            p["after"] = after
        return cond, "RETURN DISTINCT v.id AS id ORDER BY id" + (f" LIMIT {int(limit)}" if limit is not None else "")

    # -- reads
    def _get(self, id: str, t: int | None, version: int | None) -> dict | None:
        p: dict[str, Any] = {"id": id}
        if version is not None:
            p["ver"] = version
            cond = "v.version = $ver" + (" AND v.tx_from <= $t" if t is not None else "")
            if t is not None:
                p["t"] = t
        else:
            cond = self._current(t, p)
        rows = self._run(f"MATCH (v:Version:{self.ns} {{id: $id}}) WHERE {cond} RETURN properties(v) AS v", p)
        if not rows:
            return None
        return self._assemble(rows[0]["v"])

    def _assemble(self, v: dict) -> dict:
        if v.get("kind") == "entity":
            return json.loads(v["record"])
        bs = self._run(f"MATCH (v:Version:{self.ns} {{id: $id, version: $ver}})-[e:BINDS]->() "
                       "RETURN properties(e) AS e", {"id": v["id"], "ver": v["version"]})
        fact = {k: v.get(k) for k in VERSION_PROPS}
        return assemble(fact, [{k: b["e"].get(k) for k in BIND_PROPS} for b in bs])

    def _versions(self, id: str) -> list[dict]:
        rows = self._run(f"MATCH (v:Version:{self.ns} {{id: $id}}) RETURN properties(v) AS v ORDER BY v.version",
                         {"id": id})
        return [self._assemble(r["v"]) for r in rows]

    def _ids(self, t: int | None) -> list[str]:
        p: dict[str, Any] = {}
        rows = self._run(f"MATCH (v:Version:{self.ns}) WHERE {self._current(t, p)} RETURN DISTINCT v.id AS id", p)
        return sorted(r["id"] for r in rows)

    def _is_fact(self, id: str) -> bool:
        return bool(self._run(f"MATCH (n:Node:{self.ns} {{id: $id, kind: 'fact'}}) RETURN n.id AS id", {"id": id}))

    def _incident_ids(self, node, role, relation, where, t, as_of, after, limit) -> list[str]:
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
        self.last_incident = q
        return [r["id"] for r in self._run(q, p)]

    def _find_ids(self, relation, pats, match, where, t, as_of, after, limit) -> list[str]:
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
            conds += [f"b{i}.bid <> b{j}.bid" for j in range(1, i)]  # injective (explicit for every engine)
        conds += [self._current(t, p), self._filters(where, as_of, p)]
        if match == "exact":
            conds.append("v.n_bindings = $n")
            p["n"] = len(pats)
        cond, tail = self._tail(after, limit, p)
        q = f"MATCH {', '.join(paths)} WHERE {' AND '.join(conds)}{cond} {tail}"
        self.last_find = q
        return [r["id"] for r in self._run(q, p)]

    def _key_ids(self, relation, digest, where, t, as_of) -> list[str]:
        p: dict[str, Any] = {"rel": relation, "kd": digest}
        q = (f"MATCH (v:Version:{self.ns} {{relation: $rel, key_digest: $kd}}) WHERE {self._current(t, p)} AND "
             f"{self._filters(where, as_of, p)} RETURN v.id AS id ORDER BY id")
        return [r["id"] for r in self._run(q, p)]

    def native_walk(self, id: str, direction: str = "forward") -> list[list] | None:
        """Breadth first, one Cypher query per level (Memgraph and FalkorDB have no quantified path patterns);
        Neo4j overrides this with one query."""
        frm, to = ("khg:superseded", "khg:superseding") if direction == "forward" else \
            ("khg:superseding", "khg:superseded")
        steps, seen, frontier, depth = [], {id}, [id], 0
        q = (f"MATCH (:Node:{self.ns} {{id: $fact}})<-[a:BINDS {{role: $frm}}]-(s:Version:{self.ns})"
             f"-[b:BINDS {{role: $to}}]->(n:Node:{self.ns}) WHERE s.relation = 'khg:supersedes' AND "
             "s.status = 'asserted' AND s.tx_to IS NULL RETURN s.id AS via, n.id AS dst ORDER BY via, dst")
        while frontier:
            depth += 1
            nxt = []
            for fact in frontier:
                for r in self._run(q, {"fact": fact, "frm": frm, "to": to}):
                    steps.append([depth, r["via"], fact, r["dst"]])
                    if r["dst"] not in seen:
                        seen.add(r["dst"])
                        nxt.append(r["dst"])
            frontier = sorted(nxt)
        self.walk_cypher = q
        return steps


class BoltProbe(CypherProbe):
    URI = "bolt://127.0.0.1:7687"
    AUTH: Any = None
    _driver = None

    def _connect(self) -> None:
        import neo4j

        if type(self)._driver is None:
            type(self)._driver = neo4j.GraphDatabase.driver(self.URI, auth=self.AUTH, notifications_min_severity="OFF")

    def _run(self, q: str, params: dict | None = None) -> list[dict]:
        with self._driver.session() as session:
            return [r.data() for r in session.run(q, params or {})]


class Neo4j(BoltProbe):
    NAME = "neo4j"

    def _indexes(self) -> list[str]:
        return ["CREATE INDEX version_id IF NOT EXISTS FOR (v:Version) ON (v.id)",
                "CREATE INDEX version_key IF NOT EXISTS FOR (v:Version) ON (v.relation, v.key_digest)",
                "CREATE INDEX node_id IF NOT EXISTS FOR (n:Node) ON (n.id)",
                "CREATE INDEX literal_ident IF NOT EXISTS FOR (n:Literal) ON (n.ident)",
                "CREATE INDEX binds_role IF NOT EXISTS FOR ()-[e:BINDS]-() ON (e.role, e.ident)"]

    def native_walk(self, id: str, direction: str = "forward") -> list[list]:
        """One query: a quantified path pattern (GQL-style, Neo4j 5.9+) repeats the two-hop step
        superseded fact <- lifecycle version -> superseding fact, with the status test inside the group."""
        frm, to = ("khg:superseded", "khg:superseding") if direction == "forward" else \
            ("khg:superseding", "khg:superseded")
        q = (f"MATCH (start:Node:{self.ns} {{id: $id}}) ((a:Node)<-[:BINDS {{role: $frm}}]-(s:Version WHERE "
             f"s.relation = 'khg:supersedes' AND s.status = 'asserted' AND s.tx_to IS NULL)-[:BINDS {{role: $to}}]->"
             f"(b:Node)){{1,64}} RETURN [x IN s | x.id] AS via, [x IN a | x.id] AS frm, [x IN b | x.id] AS dst")
        self.walk_cypher = q
        steps = set()
        for r in self._run(q, {"id": id, "frm": frm, "to": to}):
            for depth, (v, f, d) in enumerate(zip(r["via"], r["frm"], r["dst"]), 1):
                steps.add((depth, v, f, d))
        return [list(x) for x in sorted(steps)]


class Memgraph(BoltProbe):
    NAME = "memgraph"
    URI = "bolt://127.0.0.1:7688"
    AUTH = ("", "")

    def _indexes(self) -> list[str]:
        return ["CREATE INDEX ON :Version(id)", "CREATE INDEX ON :Version(relation, key_digest)",
                "CREATE INDEX ON :Node(id)", "CREATE INDEX ON :Literal(ident)"]


class FalkorDB(CypherProbe):
    NAME = "falkordb"

    def _connect(self) -> None:
        from falkordb import FalkorDB as Client

        self.client = Client(host="127.0.0.1", port=6380)
        self.graph = self.client.select_graph(self.ns)
        for q in ("CREATE INDEX FOR (v:Version) ON (v.id)", "CREATE INDEX FOR (n:Node) ON (n.id)"):
            try:
                self.graph.query(q)
            except Exception:  # noqa: BLE001
                pass

    def _run(self, q: str, params: dict | None = None) -> list[dict]:
        res = self.graph.query(q, params or {})
        names = [h[1] if isinstance(h, (list, tuple)) else h for h in (res.header or [])]
        return [dict(zip(names, row)) for row in res.result_set]

    def close(self) -> None:
        try:
            self.graph.delete()
        except Exception:  # noqa: BLE001
            pass


PROBES = {"neo4j": Neo4j, "memgraph": Memgraph, "falkordb": FalkorDB}


def server_version(name: str, store: CypherProbe) -> str:
    try:
        if name == "neo4j":
            r = store._run("CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition")
            return json.dumps(r)
        if name == "memgraph":
            return json.dumps(store._run("SHOW VERSION"))
        if name == "falkordb":
            import redis

            mods = redis.Redis(host="127.0.0.1", port=6380).execute_command("MODULE", "LIST")
            return json.dumps([{"name": "graph (FalkorDB)", "ver": m[b"ver"]} for m in mods if m[b"name"] == b"graph"])
    except Exception as e:  # noqa: BLE001
        return f"unknown ({e})"
    return "unknown"


def main(names: list[str]) -> None:
    for name in names:
        cls = PROBES[name]
        container, schema = fixture()
        store = cls(schema)
        store.load(container)
        result: dict[str, Any] = {"backend": name, "server": server_version(name, store),
                                  "native_write_seconds": round(store.write_seconds, 4)}
        started = time.perf_counter()
        result["hand"] = hand_check(store)
        result["hand_seconds"] = round(time.perf_counter() - started, 3)
        store.find("co_administration_causes", [{"role": "agent", "value": {"entity": "ex:insulin"}},
                                                {"role": "agent", "value": {"entity": "ex:metformin"}}])
        result["find_cypher_example"] = store.last_find
        store.incident("ex:KingOfFrance")
        result["incident_cypher_example"] = store.last_incident
        result["walk_cypher"] = store.walk_cypher
        counts = store._run(f"MATCH (n:{store.ns}) RETURN count(n) AS nodes")[0]["nodes"]
        edges = store._run(f"MATCH (:{store.ns})-[e]->() RETURN count(e) AS edges")[0]["edges"]
        result["graph_size"] = {"nodes": counts, "edges": edges}
        store.close()
        started = time.perf_counter()
        result["read_only_scenarios"] = run_read_only(lambda s_, c: cls(s_, clock=c))
        result["scenario_seconds"] = round(time.perf_counter() - started, 2)
        print(name, result["server"][:120], result["read_only_scenarios"]["counts"], "export diffs:",
              result["hand"]["export khg-json round trip"]["differences"],
              "hand mismatches:", [k for k, v in result["hand"].items()
                                   if isinstance(v, dict) and (v.get("same_as_reference") is False or "error" in v)],
              "size:", result["graph_size"], "seconds:", result["scenario_seconds"])
        write_out(f"pg-{name}", result)


if __name__ == "__main__":
    main(sys.argv[1:] or list(PROBES))
