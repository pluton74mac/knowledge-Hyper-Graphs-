"""Two value-fidelity checks that the conformance suite does not make, on every engine of research 01:

1. **Id order.** C2 lists are in code-point id order. Each engine sorts eight ids (ASCII, Latin-1, Polish, CJK, a
   full-width letter, U+FFFD and the astral U+20BB7 of the fixture's source_text) with its own ORDER BY / sort.
2. **Instant range.** Valid-time windows are integer seconds; a C1 time literal may have a 16-digit year, whose
   window bound is about 3.2e23 s. Each engine stores 2**62, 2**63 - 1 and 315569520000148699584000 as an integer.

Writes out/ordering.json. Servers as in the other probes; engines that are not reachable are reported as such.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from common import OUT, write_out

IDS = ["f:a", "f:Z", "f:é", "f:ł", "f:東京", "f:ｚ", "f:\ufffd", "f:\U00020bb7"]
WANT = sorted(IDS)  # Python sorts str by code point
BIG = [2 ** 62, 2 ** 63 - 1, 315569520000148699584000]


def sqlite() -> tuple[list[str], dict]:
    import sqlite3

    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE t (id TEXT, n INTEGER)")
    con.executemany("INSERT INTO t (id) VALUES (?)", [(i,) for i in IDS])
    order = [r[0] for r in con.execute("SELECT id FROM t ORDER BY id")]
    ints = {}
    for n in BIG:
        try:
            con.execute("INSERT INTO t (n) VALUES (?)", (n,))
            ints[str(n)] = "stored"
        except Exception as e:  # noqa: BLE001
            ints[str(n)] = f"{type(e).__name__}: {e}"[:120]
    return order, ints


def duckdb() -> tuple[list[str], dict]:
    import duckdb as d

    con = d.connect()
    con.execute("CREATE TABLE t (id VARCHAR, n BIGINT, h HUGEINT)")
    con.executemany("INSERT INTO t (id) VALUES (?)", [(i,) for i in IDS])
    order = [r[0] for r in con.execute("SELECT id FROM t ORDER BY id").fetchall()]
    ints = {}
    for n in BIG:
        for col in ("n", "h"):
            try:
                con.execute(f"INSERT INTO t ({col}) VALUES (?)", [n])
                ints[f"{n} as {'BIGINT' if col == 'n' else 'HUGEINT'}"] = "stored"
            except Exception as e:  # noqa: BLE001
                ints[f"{n} as {'BIGINT' if col == 'n' else 'HUGEINT'}"] = f"{type(e).__name__}: {e}"[:120]
    return order, ints


def postgres(port: int, collation: str | None) -> Callable[[], tuple[list[str], dict]]:
    def run() -> tuple[list[str], dict]:
        import psycopg

        con = psycopg.connect(f"host=127.0.0.1 port={port} user=postgres dbname=postgres", autocommit=True)
        coll = f' COLLATE "{collation}"' if collation else ""
        con.execute("DROP TABLE IF EXISTS order_probe")
        con.execute(f"CREATE TABLE order_probe (id text{coll}, n bigint, x numeric)")
        with con.cursor() as cur:
            cur.executemany("INSERT INTO order_probe (id) VALUES (%s)", [(i,) for i in IDS])
        order = [r[0] for r in con.execute("SELECT id FROM order_probe ORDER BY id").fetchall()]
        ints = {}
        for n in BIG:
            for col in ("n", "x"):
                try:
                    con.execute(f"INSERT INTO order_probe ({col}) VALUES (%s)", [n])
                    ints[f"{n} as {'bigint' if col == 'n' else 'numeric'}"] = "stored"
                except Exception as e:  # noqa: BLE001
                    ints[f"{n} as {'bigint' if col == 'n' else 'numeric'}"] = f"{type(e).__name__}: {e}"[:120]
        con.execute("DROP TABLE order_probe")
        return order, ints
    return run


def oxigraph() -> tuple[list[str], dict]:
    import pyoxigraph as ox

    st = ox.Store()
    p = ox.NamedNode("urn:p:id")
    st.extend([ox.Quad(ox.NamedNode(f"urn:x:{n}"), p, ox.Literal(i)) for n, i in enumerate(IDS)])
    order = [s["id"].value for s in st.query("SELECT ?id WHERE { ?s <urn:p:id> ?id } ORDER BY ?id")]
    ints = {}
    for n in BIG:
        lit = ox.Literal(str(n), datatype=ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer"))
        st.add(ox.Quad(ox.NamedNode("urn:n"), ox.NamedNode("urn:p:n"), lit))
        got = [s["x"] for s in st.query(f"SELECT ?x WHERE {{ <urn:n> <urn:p:n> ?x FILTER(?x = {n}) }}")]
        cmp = [s["x"] for s in st.query(f"SELECT ?x WHERE {{ <urn:n> <urn:p:n> ?x FILTER(?x > {n} - 1) }}")]
        ints[str(n)] = f"stored; equality finds it: {bool(got)}; comparison finds it: {bool(cmp)}"
    return order, ints


def rdflib_() -> tuple[list[str], dict]:
    import rdflib

    g = rdflib.Graph()
    for n, i in enumerate(IDS):
        g.add((rdflib.URIRef(f"urn:x:{n}"), rdflib.URIRef("urn:p:id"), rdflib.Literal(i)))
    order = [str(r[0]) for r in g.query("SELECT ?id WHERE { ?s <urn:p:id> ?id } ORDER BY ?id")]
    return order, {"note": "xsd:integer is a Python int: unbounded"}


def cypher_bolt(uri: str, auth: Any) -> Callable[[], tuple[list[str], dict]]:
    def run() -> tuple[list[str], dict]:
        import neo4j

        drv = neo4j.GraphDatabase.driver(uri, auth=auth, notifications_min_severity="OFF")
        with drv.session() as s:
            s.run("MATCH (n:OrderProbe) DETACH DELETE n")
            s.run("UNWIND $ids AS i CREATE (:OrderProbe {id: i})", ids=IDS)
            order = [r["id"] for r in s.run("MATCH (n:OrderProbe) RETURN n.id AS id ORDER BY id")]
            ints = {}
            for n in BIG:
                try:
                    s.run("CREATE (:OrderProbe {n: $n})", n=n).consume()
                    ints[str(n)] = "stored"
                except Exception as e:  # noqa: BLE001
                    ints[str(n)] = f"{type(e).__name__}: {e}"[:120]
            s.run("MATCH (n:OrderProbe) DETACH DELETE n")
        drv.close()
        return order, ints
    return run


def falkordb() -> tuple[list[str], dict]:
    from falkordb import FalkorDB

    g = FalkorDB(host="127.0.0.1", port=6380).select_graph("order_probe")
    g.query("UNWIND $ids AS i CREATE (:OrderProbe {id: i})", {"ids": IDS})
    order = [r[0] for r in g.query("MATCH (n:OrderProbe) RETURN n.id AS id ORDER BY id").result_set]
    ints = {}
    for n in BIG:
        try:
            g.query("CREATE (:OrderProbe {n: $n})", {"n": n})
            back = g.query("MATCH (x:OrderProbe) WHERE x.n IS NOT NULL RETURN max(x.n)").result_set[0][0]
            ints[str(n)] = f"stored; read back {back}"
        except Exception as e:  # noqa: BLE001
            ints[str(n)] = f"{type(e).__name__}: {e}"[:120]
    g.delete()
    return order, ints


def embedded(module: str) -> Callable[[], tuple[list[str], dict]]:
    def run() -> tuple[list[str], dict]:
        import importlib

        m = importlib.import_module(module)
        con = m.Connection(m.Database())
        con.execute("CREATE NODE TABLE P(id STRING PRIMARY KEY, n INT64)")
        for i in IDS:
            con.execute("CREATE (:P {id: $id})", {"id": i})
        res = con.execute("MATCH (p:P) RETURN p.id ORDER BY p.id")
        order = []
        while res.has_next():
            order.append(res.get_next()[0])
        ints = {}
        for k, n in enumerate(BIG):
            try:
                con.execute("CREATE (:P {id: $id, n: $n})", {"id": f"n{k}", "n": n})
                ints[str(n)] = "stored"
            except Exception as e:  # noqa: BLE001
                ints[str(n)] = f"{type(e).__name__}: {e}"[:120]
        return order, ints
    return run


def typedb() -> tuple[list[str], dict]:
    from typedb.driver import Credentials, DriverOptions, DriverTlsConfig, TransactionType, TypeDB

    drv = TypeDB.driver("127.0.0.1:1729", Credentials("admin", "password"), DriverOptions(DriverTlsConfig.disabled()))
    db = "order-probe"
    if drv.databases.contains(db):
        drv.databases.get(db).delete()
    drv.databases.create(db)
    with drv.transaction(db, TransactionType.SCHEMA) as tx:
        tx.query("define attribute pid, value string; attribute n, value integer; entity p, owns pid, owns n;").resolve()
        tx.commit()
    with drv.transaction(db, TransactionType.WRITE) as tx:
        for i in IDS:
            tx.query(f"insert $x isa p, has pid {json.dumps(i, ensure_ascii=False)};").resolve()
        tx.commit()
    with drv.transaction(db, TransactionType.READ) as tx:
        rows = tx.query("match $x isa p, has pid $id; sort $id;").resolve().as_concept_rows()
        order = [r.get("id").get_value() for r in rows]
    ints = {}
    for n in BIG:
        try:
            with drv.transaction(db, TransactionType.WRITE) as tx:
                tx.query(f"insert $x isa p, has n {n};").resolve()
                tx.commit()
            ints[str(n)] = "stored"
        except Exception as e:  # noqa: BLE001
            ints[str(n)] = f"{type(e).__name__}: {' '.join(str(e).split())}"[:160]
    drv.databases.get(db).delete()
    drv.close()
    return order, ints


ENGINES: dict[str, Callable[[], tuple[list[str], dict]]] = {
    "sqlite": sqlite, "duckdb": duckdb,
    "pg18 (database locale C)": postgres(5418, None), "pg18 COLLATE en-x-icu": postgres(5418, "en-x-icu"),
    "oxigraph": oxigraph, "rdflib": rdflib_,
    "neo4j": cypher_bolt("bolt://127.0.0.1:7687", None), "memgraph": cypher_bolt("bolt://127.0.0.1:7688", ("", "")),
    "falkordb": falkordb, "kuzu": embedded("kuzu"), "ladybug": embedded("ladybug"), "typedb": typedb,
}


def main(only: list[str]) -> None:
    """``only``: engine names to run (default all). Kùzu and LadybugDB cannot share one process (after ``import
    kuzu``, ``ladybug.Database()`` fails to find its C API library), so run ladybug on its own; results are merged
    into out/ordering.json."""
    path = OUT / "ordering.json"
    out: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if only and path.exists() else {}
    out.update({"ids": IDS, "code_point_order": WANT, "big_integers": [str(n) for n in BIG]})
    for name, fn in ENGINES.items():
        if only and name not in only:
            continue
        try:
            order, ints = fn()
            out[name] = {"code_point_order": order == WANT, "order": order, "integers": ints}
        except Exception as e:  # noqa: BLE001
            out[name] = {"error": f"{type(e).__name__}: {e}"[:200]}
        print(name, out[name].get("code_point_order", out[name].get("error")),
              "" if out[name].get("code_point_order", True) else out[name]["order"])
    write_out("ordering", out)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
