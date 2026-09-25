"""Backend 3 via SQL/PGQ: the incidence tables of sql_incidence.py in DuckDB 1.5.4 with the DuckPGQ community
extension, exposed as a property graph (fact versions and nodes as vertices, bindings as edges). Checks which
C2 reads the GRAPH_TABLE syntax expresses. Needs duckdb==1.5.4 (DuckPGQ has no build for 1.5.5, checked
2026-09-25). Writes out/pg-duckpgq.json.
"""
from __future__ import annotations

import os
from typing import Any

import duckdb

from common import close_versions, entity_row, fixture, split, write_out
from khg_contracts.store import MemoryStore, ScenarioClock

EXT_DIR = os.environ.get("DUCKDB_EXT_DIR", "")


def main() -> None:
    container, schema = fixture()
    m = MemoryStore(schema, clock=ScenarioClock())
    m.load(container)
    facts, binds, nodes = [], [], set()
    for rid in m._table.ids():  # noqa: SLF001
        for e in m._table.entries(rid):  # noqa: SLF001
            r = e.record
            nodes.add((r["id"], r["kind"]))
            if r["kind"] == "hyperedge":
                f, bs = split(r, schema)
                facts.append(f)
                binds += [b for b in bs if b["ref"] is not None]
    close_versions(facts)
    con = duckdb.connect()
    if EXT_DIR:
        con.execute(f"SET extension_directory='{EXT_DIR}'")
    con.execute("LOAD duckpgq")
    con.execute("CREATE TABLE node (id VARCHAR PRIMARY KEY, kind VARCHAR)")
    con.execute("CREATE TABLE fact (vk VARCHAR PRIMARY KEY, id VARCHAR, version INTEGER, relation VARCHAR, "
                "status VARCHAR, tx_to BIGINT)")
    con.execute("CREATE TABLE binds (vk VARCHAR, ref VARCHAR, bid VARCHAR, role VARCHAR)")
    con.executemany("INSERT INTO node VALUES (?, ?)", sorted(nodes))
    con.executemany("INSERT INTO fact VALUES (?, ?, ?, ?, ?, ?)",
                    [(f"{f['id']}#{f['version']}", f["id"], f["version"], f["relation"], f["status"], f["tx_to"])
                     for f in facts])
    con.executemany("INSERT INTO binds VALUES (?, ?, ?, ?)",
                    [(f"{b['fact_id']}#{b['version']}", b["ref"], b["bid"], b["role"]) for b in binds])
    out: dict[str, Any] = {"duckdb": duckdb.__version__,
                           "duckpgq": con.execute("SELECT extension_version FROM duckdb_extensions() "
                                                  "WHERE extension_name = 'duckpgq'").fetchone()[0]}
    steps = {
        "create property graph": """
CREATE PROPERTY GRAPH khg
  VERTEX TABLES (node LABEL nd, fact LABEL ver)
  EDGE TABLES (binds SOURCE KEY (vk) REFERENCES fact (vk) DESTINATION KEY (ref) REFERENCES node (id) LABEL binds)""",
        "incident ex:KingOfFrance": """
FROM GRAPH_TABLE (khg MATCH (v:ver)-[b:binds]->(n:nd WHERE n.id = 'ex:KingOfFrance')
  WHERE v.status = 'asserted' AND v.tx_to IS NULL COLUMNS (v.id AS id, b.role AS role)) ORDER BY id""",
        "find agent insulin + metformin (two edges)": """
FROM GRAPH_TABLE (khg MATCH (a:nd WHERE a.id = 'ex:insulin')<-[b1:binds WHERE b1.role = 'agent']-(v:ver)
  -[b2:binds WHERE b2.role = 'agent']->(c:nd WHERE c.id = 'ex:metformin')
  WHERE v.relation = 'co_administration_causes' AND b1.bid <> b2.bid COLUMNS (v.id AS id))""",
        "walk one level (superseded <- khg:supersedes -> superseding)": """
FROM GRAPH_TABLE (khg MATCH (a:nd WHERE a.id = 'f:born-skłodowska-kraków')<-[x:binds WHERE x.role = 'khg:superseded']-
  (s:ver WHERE s.relation = 'khg:supersedes' AND s.status = 'asserted')-[y:binds WHERE y.role = 'khg:superseding']->(b:nd)
  COLUMNS (s.id AS via, b.id AS dst))""",
        "walk as a variable-length path (any shortest, 1..8 BINDS edges, direction ignored)": """
FROM GRAPH_TABLE (khg MATCH p = ANY SHORTEST (a:nd WHERE a.id = 'f:born-skłodowska-kraków')-[e:binds]-{1,8}
  (b:nd WHERE b.id = 'f:born-skłodowska-warszawa') COLUMNS (path_length(p) AS hops))""",
    }
    for label, sql in steps.items():
        try:
            rows = con.execute(sql).fetchall()
            out[label] = {"ok": True, "rows": [list(r) for r in rows] if rows else []}
        except Exception as e:  # noqa: BLE001
            out[label] = {"ok": False, "error": str(e).splitlines()[0][:300]}
        out[label]["sql"] = " ".join(sql.split())
    print({k: (v["ok"], v.get("rows", v.get("error"))) for k, v in out.items() if isinstance(v, dict)})
    write_out("pg-duckpgq", out)


if __name__ == "__main__":
    main()
