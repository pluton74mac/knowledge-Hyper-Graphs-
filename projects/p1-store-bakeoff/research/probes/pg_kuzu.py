"""Backend 3, embedded variant: Kùzu 0.11.3 (archived) and LadybugDB (its successor fork), same layout as
pg_cypher.py but with the typed DDL these engines require (node and relationship tables; one BINDS table with
three FROM/TO pairs). Each store is its own in-memory database. Writes out/pg-<engine>.json.

Usage: python pg_kuzu.py [kuzu|ladybug ...]
"""
from __future__ import annotations

import importlib
import json
import sys
import time
from typing import Any

from common import fixture, hand_check, run_read_only, write_out
from pg_cypher import BIND_PROPS, VERSION_PROPS, CypherProbe, clean

DDL = [
    "CREATE NODE TABLE Node(id STRING PRIMARY KEY, kind STRING)",
    "CREATE NODE TABLE Version(vk STRING PRIMARY KEY, id STRING, version INT64, tx_from INT64, tx_to INT64, "
    "recorded_at STRING, recorded_by STRING, kind STRING, relation STRING, rel_kind STRING, status STRING, "
    "status_ref STRING, rank STRING, visibility STRING, key_digest STRING, s_lo INT64, s_hi INT64, e_lo INT64, "
    "e_hi INT64, n_bindings INT64, payload STRING, record STRING)",
    "CREATE NODE TABLE Literal(ident STRING PRIMARY KEY)",
    "CREATE NODE TABLE Special(key STRING PRIMARY KEY)",
    "CREATE NODE TABLE Doc(k INT64 PRIMARY KEY, header STRING, documents STRING)",
    "CREATE REL TABLE VERSION_OF(FROM Version TO Node)",
    "CREATE REL TABLE BINDS(FROM Version TO Node, FROM Version TO Literal, FROM Version TO Special, bid STRING, "
    "role STRING, position INT64, direction STRING, value_kind STRING, ref STRING, ident STRING, value_json STRING, "
    "extensions STRING)",
]
VCOLS = ("id", "version", "tx_from", "tx_to", "recorded_at", "recorded_by", "kind", "relation", "rel_kind", "status",
         "status_ref", "rank", "visibility", "key_digest", "s_lo", "s_hi", "e_lo", "e_hi", "n_bindings", "payload",
         "record")


class Embedded(CypherProbe):
    MODULE = "kuzu"

    def _connect(self) -> None:
        mod = importlib.import_module(self.MODULE)
        self.db = mod.Database()  # in memory
        self.con = mod.Connection(self.db)
        self.ns = ""  # one database per store: no namespace label needed
        for q in DDL:
            self.con.execute(q)

    def _open(self) -> None:
        self._connect()

    def close(self) -> None:
        try:
            self.con.close()
            self.db.close()
        except Exception:  # noqa: BLE001
            pass

    def _run(self, q: str, params: dict | None = None) -> list[dict]:
        q = q.replace(":Version:", ":Version").replace(":Node:", ":Node").replace(":Doc:", ":Doc")
        res = self.con.execute(q, params or {})
        cols = res.get_column_names()
        out = []
        while res.has_next():
            out.append(dict(zip(cols, res.get_next())))
        return out

    def _write(self, entities: list[dict], facts: list[dict], bindings: list[dict]) -> None:
        self.con.execute("CREATE (:Doc {k: 1, header: $h, documents: $d})",
                         {"h": json.dumps(self._header), "d": json.dumps(self._documents)})
        nodes = sorted({(e["id"], "entity") for e in entities} | {(f["id"], "fact") for f in facts})
        for i, k in nodes:
            self.con.execute("CREATE (:Node {id: $id, kind: $kind})", {"id": i, "kind": k})
        for row, kind in [(e, "entity") for e in entities] + [(f, "fact") for f in facts]:
            p = {c: row.get(c) for c in VCOLS}
            p["kind"] = kind
            p["vk"] = f"{row['id']}#{row['version']}"
            sets = ", ".join(f"{c}: ${c}" for c in ("vk",) + VCOLS)
            self.con.execute(f"MATCH (n:Node {{id: $id}}) CREATE (v:Version {{{sets}}})-[:VERSION_OF]->(n)", p)
        for b in bindings:
            p = {c: b.get(c) for c in BIND_PROPS}
            p["vk"] = f"{b['fact_id']}#{b['version']}"
            sets = ", ".join(f"{c}: ${c}" for c in BIND_PROPS)
            if b["value_kind"] in ("entity", "fact"):
                target, create = "MATCH (t:Node {id: $ref})", ""
            elif b["value_kind"] == "literal":
                target, create = "MERGE (t:Literal {ident: $ident})", ""
            else:
                p["key"] = f"{b['fact_id']}#{b['version']}#{b['bid']}"
                target, create = "CREATE (t:Special {key: $key})", ""
            self.con.execute(f"MATCH (v:Version {{vk: $vk}}) {target} {create} CREATE (v)-[:BINDS {{{sets}}}]->(t)", p)

    def _get(self, id: str, t: int | None, version: int | None) -> dict | None:
        p: dict[str, Any] = {"id": id}
        if version is not None:
            p["ver"] = version
            cond = "v.version = $ver" + (" AND v.tx_from <= $t" if t is not None else "")
            if t is not None:
                p["t"] = t
        else:
            cond = self._current(t, p)
        rows = self._run(f"MATCH (v:Version {{id: $id}}) WHERE {cond} RETURN v", p)
        return self._assemble(rows[0]["v"]) if rows else None

    def _assemble(self, v: dict) -> dict:
        from common import assemble

        if v.get("kind") == "entity":
            return json.loads(v["record"])
        bs = self._run("MATCH (v:Version {id: $id, version: $ver})-[e:BINDS]->() RETURN e",
                       {"id": v["id"], "ver": v["version"]})
        return assemble({k: v.get(k) for k in VERSION_PROPS}, [{k: b["e"].get(k) for k in BIND_PROPS} for b in bs])

    def _versions(self, id: str) -> list[dict]:
        rows = self._run("MATCH (v:Version {id: $id}) RETURN v ORDER BY v.version", {"id": id})
        return [self._assemble(r["v"]) for r in rows]


class Kuzu(Embedded):
    NAME, MODULE = "kuzu", "kuzu"


class Ladybug(Embedded):
    NAME, MODULE = "ladybug", "ladybug"


PROBES = {"kuzu": Kuzu, "ladybug": Ladybug}


def main(names: list[str]) -> None:
    for name in names:
        cls = PROBES[name]
        mod = importlib.import_module(cls.MODULE)
        container, schema = fixture()
        store = cls(schema)
        store.load(container)
        result: dict[str, Any] = {"backend": name, "version": getattr(mod, "__version__", "?"),
                                  "native_write_seconds": round(store.write_seconds, 4)}
        result["hand"] = hand_check(store)
        store.find("co_administration_causes", [{"role": "agent", "value": {"entity": "ex:insulin"}},
                                                {"role": "agent", "value": {"entity": "ex:metformin"}}])
        result["find_cypher_example"] = store.last_find
        store.close()
        started = time.perf_counter()
        result["read_only_scenarios"] = run_read_only(lambda s_, c: cls(s_, clock=c))
        result["scenario_seconds"] = round(time.perf_counter() - started, 2)
        print(name, result["version"], result["read_only_scenarios"]["counts"], "export diffs:",
              result["hand"]["export khg-json round trip"]["differences"],
              "hand mismatches:", [k for k, v in result["hand"].items()
                                   if isinstance(v, dict) and (v.get("same_as_reference") is False or "error" in v)],
              "seconds:", result["scenario_seconds"])
        write_out(f"pg-{name}", result)


if __name__ == "__main__":
    main(sys.argv[1:] or list(PROBES))
