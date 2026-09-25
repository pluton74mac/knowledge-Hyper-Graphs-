"""Backend 1, the incidence table: SQLite, DuckDB and PostgreSQL (16 and 18) with one schema and one query set.

Layout (one row per version, one row per binding; transaction time as a system-time period [tx_from, tx_to)):

    document(singleton, header, documents)                 -- the kept header (DESIGN §6.2)
    entity_version(id, version, tx_from, tx_to, recorded_at, recorded_by, record)
    fact_version(id, version, tx_from, tx_to, recorded_at, recorded_by, relation, rel_kind, status, status_ref,
                 rank, visibility, key_digest, s_lo, s_hi, e_lo, e_hi, n_bindings, payload)
    binding(fact_id, version, bid, role, position, direction, value_kind, ref, ident, value_json, extensions)

Usage: python sql_incidence.py [sqlite|duckdb|pg16|pg18 ...]   (default: all four; PostgreSQL on 127.0.0.1:5416 and
:5418, user postgres, trust auth). Writes out/sql-<dialect>.json.
"""
from __future__ import annotations

import sys
from typing import Any

from common import ReadOnlyProbe, assemble, fixture, hand_check, history_check, run_read_only, write_out

FLAGS = frozenset({"literal_values", "special_values", "goals", "nesting", "ordered_roles", "valid_time",
                   "transaction_time", "key_constraint", "atomic_writes", "history_export"})

DDL = [
    "CREATE TABLE document (singleton INTEGER PRIMARY KEY, header TEXT, documents TEXT)",
    """CREATE TABLE entity_version (id TEXT NOT NULL, version INTEGER NOT NULL, tx_from BIGINT NOT NULL, tx_to BIGINT,
       recorded_at TEXT NOT NULL, recorded_by TEXT NOT NULL, record TEXT NOT NULL, PRIMARY KEY (id, version))""",
    """CREATE TABLE fact_version (id TEXT NOT NULL, version INTEGER NOT NULL, tx_from BIGINT NOT NULL, tx_to BIGINT,
       recorded_at TEXT NOT NULL, recorded_by TEXT NOT NULL, relation TEXT NOT NULL, rel_kind TEXT NOT NULL,
       status TEXT NOT NULL, status_ref TEXT, rank TEXT NOT NULL, visibility TEXT NOT NULL, key_digest TEXT,
       s_lo BIGINT NOT NULL, s_hi BIGINT NOT NULL, e_lo BIGINT NOT NULL, e_hi BIGINT NOT NULL,
       n_bindings INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY (id, version))""",
    """CREATE TABLE binding (fact_id TEXT NOT NULL, version INTEGER NOT NULL, bid TEXT NOT NULL, role TEXT NOT NULL,
       position INTEGER, direction TEXT, value_kind TEXT NOT NULL, ref TEXT, ident TEXT, value_json TEXT NOT NULL,
       extensions TEXT, PRIMARY KEY (fact_id, version, bid))""",
    "CREATE INDEX binding_ref ON binding (ref, role)",
    "CREATE INDEX binding_ident ON binding (role, ident)",
    "CREATE INDEX fact_key ON fact_version (relation, key_digest)",
    "CREATE INDEX fact_rel ON fact_version (relation, id)",
]
FACT_COLS = ("id", "version", "tx_from", "tx_to", "recorded_at", "recorded_by", "relation", "rel_kind", "status",
             "status_ref", "rank", "visibility", "key_digest", "s_lo", "s_hi", "e_lo", "e_hi", "n_bindings", "payload")
BIND_COLS = ("fact_id", "version", "bid", "role", "position", "direction", "value_kind", "ref", "ident", "value_json",
             "extensions")
ENT_COLS = ("id", "version", "tx_from", "tx_to", "recorded_at", "recorded_by", "record")


class SQLProbe(ReadOnlyProbe):
    FLAGS = FLAGS
    DIALECT = "sqlite"
    P = "?"  # the driver's placeholder

    # -- connection
    def _connect(self) -> Any: ...

    def _open(self) -> None:
        self.con = self._connect()
        cur = self.con.cursor()
        for stmt in DDL:
            cur.execute(stmt)
        self._commit()

    def _commit(self) -> None:
        self.con.commit()

    def _q(self, sql: str, params: list[Any] | tuple = ()) -> list[tuple]:
        cur = self.con.cursor()
        cur.execute(sql.replace("?", self.P), list(params))
        return cur.fetchall()

    def close(self) -> None:
        try:
            self.con.close()
        except Exception:  # noqa: BLE001
            pass

    # -- write
    def _write(self, entities: list[dict], facts: list[dict], bindings: list[dict]) -> None:
        cur = self.con.cursor()
        import json

        cur.execute(f"INSERT INTO document VALUES (1, {self.P}, {self.P})",
                    [json.dumps(self._header), json.dumps(self._documents)])
        for table, cols, rows in (("entity_version", ENT_COLS, entities), ("fact_version", FACT_COLS, facts),
                                  ("binding", BIND_COLS, bindings)):
            if rows:
                marks = ", ".join([self.P] * len(cols))
                cur.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({marks})",
                                [[r[c] for c in cols] for r in rows])
        self._commit()

    # -- helpers
    @staticmethod
    def _current(alias: str, t: int | None, params: list[Any]) -> str:
        if t is None:
            return f"{alias}.tx_to IS NULL"
        params += [t, t]
        return f"{alias}.tx_from <= ? AND ({alias}.tx_to IS NULL OR {alias}.tx_to > ?)"

    @staticmethod
    def _filters(alias: str, where: Any, as_of: int | None, params: list[Any]) -> str:
        parts = []
        for col, values in (("status", where.status), ("rank", where.rank), ("visibility", where.visibility),
                            ("rel_kind", where.kinds)):
            vs = sorted(values)
            if not vs:
                return "1 = 0"
            parts.append(f"{alias}.{col} IN ({', '.join('?' for _ in vs)})")
            params += vs
        if as_of is not None:
            lo, hi = ("s_hi", "e_lo") if where.valid_mode == "definite" else ("s_lo", "e_hi")
            parts.append(f"{alias}.{lo} <= ? AND ? < {alias}.{hi}")
            params += [as_of, as_of]
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

    def _fact(self, id: str, t: int | None, version: int | None) -> dict | None:
        params: list[Any] = [id]
        if version is not None:
            cond = "fv.version = ?"
            params.append(version)
            if t is not None:
                cond += " AND fv.tx_from <= ?"
                params.append(t)
        else:
            cond = self._current("fv", t, params)
        rows = self._q(f"SELECT {', '.join('fv.' + c for c in FACT_COLS)} FROM fact_version fv WHERE fv.id = ? AND "
                       f"{cond}", params)
        return dict(zip(FACT_COLS, rows[0])) if rows else None

    def _bindings(self, id: str, version: int) -> list[dict]:
        rows = self._q(f"SELECT {', '.join(BIND_COLS)} FROM binding WHERE fact_id = ? AND version = ?", [id, version])
        return [dict(zip(BIND_COLS, r)) for r in rows]

    # -- reads
    def _get(self, id: str, t: int | None, version: int | None) -> dict | None:
        import json

        f = self._fact(id, t, version)
        if f is not None:
            return assemble(f, self._bindings(id, f["version"]))
        params: list[Any] = [id]
        if version is not None:
            cond = "version = ?" + (" AND tx_from <= ?" if t is not None else "")
            params += [version] + ([t] if t is not None else [])
        else:
            cond = self._current("entity_version", t, params)
        rows = self._q(f"SELECT record FROM entity_version WHERE id = ? AND {cond}", params)
        return json.loads(rows[0][0]) if rows else None

    def _versions(self, id: str) -> list[dict]:
        import json

        facts = self._q(f"SELECT {', '.join(FACT_COLS)} FROM fact_version WHERE id = ? ORDER BY version", [id])
        if facts:
            return [assemble(dict(zip(FACT_COLS, r)), self._bindings(id, r[1])) for r in facts]
        return [json.loads(r[0]) for r in self._q("SELECT record FROM entity_version WHERE id = ? ORDER BY version",
                                                   [id])]

    def _ids(self, t: int | None) -> list[str]:
        params: list[Any] = []
        a = self._current("e", t, params)
        b = self._current("f", t, params)
        rows = self._q(f"SELECT e.id FROM entity_version e WHERE {a} UNION SELECT f.id FROM fact_version f WHERE {b}",
                       params)
        return sorted(r[0] for r in rows)  # code-point order, whatever the collation

    def _is_fact(self, id: str) -> bool:
        return bool(self._q("SELECT 1 FROM fact_version WHERE id = ? LIMIT 1", [id]))

    def _incident_ids(self, node, role, relation, where, t, as_of, after, limit) -> list[str]:
        params: list[Any] = [node]
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
        cond, tail = self._page_sql("fv", after, limit, params)
        sql = (f"SELECT fv.id FROM fact_version fv WHERE EXISTS (SELECT 1 FROM binding b WHERE b.fact_id = fv.id "
               f"AND b.version = fv.version AND {sub}) AND {cur} AND {filt}{rel}{cond}{tail}")
        self.last_sql = sql
        return [r[0] for r in self._q(sql, params)]

    def _find_ids(self, relation, pats, match, where, t, as_of, after, limit) -> list[str]:
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
        self.last_sql = sql
        return [r[0] for r in self._q(sql, params)]

    def _key_ids(self, relation, digest, where, t, as_of) -> list[str]:
        params: list[Any] = [relation, digest]
        cur = self._current("fv", t, params)
        filt = self._filters("fv", where, as_of, params)
        return [r[0] for r in self._q(f"SELECT fv.id FROM fact_version fv WHERE fv.relation = ? AND fv.key_digest = ? "
                                      f"AND {cur} AND {filt} ORDER BY fv.id", params)]

    WALK = """
WITH RECURSIVE walk(depth, via, frm, dst) AS (
  SELECT 1, s.id, fb.ref, tb.ref
  FROM binding fb
  JOIN fact_version s ON s.id = fb.fact_id AND s.version = fb.version
  JOIN binding tb ON tb.fact_id = s.id AND tb.version = s.version AND tb.role = ?
  WHERE fb.ref = ? AND fb.role = ? AND s.relation = 'khg:supersedes' AND s.status = 'asserted' AND s.tx_to IS NULL
  UNION
  SELECT w.depth + 1, s.id, fb.ref, tb.ref
  FROM walk w
  JOIN binding fb ON fb.ref = w.dst AND fb.role = ?
  JOIN fact_version s ON s.id = fb.fact_id AND s.version = fb.version
  JOIN binding tb ON tb.fact_id = s.id AND tb.version = s.version AND tb.role = ?
  WHERE s.relation = 'khg:supersedes' AND s.status = 'asserted' AND s.tx_to IS NULL AND w.depth < 64
)
SELECT depth, via, frm, dst FROM walk ORDER BY depth, via, dst"""

    def native_walk(self, id: str, direction: str = "forward") -> list[list]:
        frm, to = ("khg:superseded", "khg:superseding") if direction == "forward" else \
            ("khg:superseding", "khg:superseded")
        return [list(r) for r in self._q(self.WALK, [to, id, frm, frm, to])]


class SQLite(SQLProbe):
    NAME = "sqlite"

    def _connect(self) -> Any:
        import sqlite3

        return sqlite3.connect(":memory:")


class DuckDB(SQLProbe):
    NAME = "duckdb"

    def _connect(self) -> Any:
        import duckdb

        return duckdb.connect(":memory:")


class Postgres(SQLProbe):
    NAME = "pg"
    P = "%s"
    PORT = 5418
    counter = 0

    def _connect(self) -> Any:
        import psycopg

        Postgres.counter += 1
        db = f"probe_{self.PORT}_{Postgres.counter}"
        admin = psycopg.connect(f"host=127.0.0.1 port={self.PORT} user=postgres dbname=postgres", autocommit=True)
        admin.execute(f"DROP DATABASE IF EXISTS {db}")
        admin.execute(f"CREATE DATABASE {db} LOCALE 'C' TEMPLATE template0")  # code-point order for ids
        admin.close()
        self._db = db
        return psycopg.connect(f"host=127.0.0.1 port={self.PORT} user=postgres dbname={db}")

    def close(self) -> None:
        import psycopg

        super().close()
        try:
            admin = psycopg.connect(f"host=127.0.0.1 port={self.PORT} user=postgres dbname=postgres",
                                    autocommit=True)
            admin.execute(f"DROP DATABASE IF EXISTS {self._db}")
            admin.close()
        except Exception:  # noqa: BLE001
            pass


class PG16(Postgres):
    NAME, PORT = "pg16", 5416


class PG18(Postgres):
    NAME, PORT = "pg18", 5418


def temporal_key_demo(port: int) -> dict[str, Any]:
    """The key invariant as a database constraint (DESIGN §6.5): PostgreSQL 18 WITHOUT OVERLAPS, and an EXCLUDE
    constraint with btree_gist, over the definite windows of the fixture's position_held facts."""
    import psycopg

    from common import split

    container, schema = fixture()
    recs = {r["id"]: dict(r, version=1, recorded_at="2026-10-01T00:00:00Z", recorded_by="load")
            for r in container["records"] if r.get("relation") == "position_held" and r["status"] == "asserted"}
    out: dict[str, Any] = {}
    con = psycopg.connect(f"host=127.0.0.1 port={port} user=postgres dbname=postgres", autocommit=True)
    for name, ddl in (
            ("without_overlaps", "CREATE TEMP TABLE key_period (relation text, key_digest text, valid int8range, "
                                 "PRIMARY KEY (relation, key_digest, valid WITHOUT OVERLAPS))"),
            ("exclude_gist", "CREATE TEMP TABLE key_period (relation text, key_digest text, valid int8range, "
                             "EXCLUDE USING gist (relation WITH =, key_digest WITH =, valid WITH &&))")):
        try:
            con.execute("DROP TABLE IF EXISTS key_period")
            con.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")  # GiST opclasses for the text key columns
            con.execute(ddl)
        except Exception as e:  # noqa: BLE001
            out[name] = f"refused: {e}".splitlines()[0]
            continue
        rows = []
        for rid in ("f:king-13", "f:king-14"):
            f, _ = split(recs[rid], schema)
            con.execute("INSERT INTO key_period VALUES (%s, %s, int8range(%s, %s))",
                        ["position_held", f["key_digest"], f["s_hi"], f["e_lo"]])
            rows.append(rid)
        clash = dict(recs["f:king-14"], id="f:king-14b")
        clash["bindings"] = [dict(b, value={"literal": {"datatype": "time", "time": "+1640-01-01T00:00:00Z",
                                                        "precision": 11, "calendar": "gregorian"}})
                             if b["role"] == "start_time" else b for b in clash["bindings"]]
        f, _ = split(clash, schema)
        try:
            con.execute("INSERT INTO key_period VALUES (%s, %s, int8range(%s, %s))",
                        ["position_held", f["key_digest"], f["s_hi"], f["e_lo"]])
            out[name] = {"inserted": rows, "king-14b (starts 1640)": "accepted (unexpected)"}
        except Exception as e:  # noqa: BLE001
            out[name] = {"inserted": rows, "king-14b (starts 1640)": str(e).splitlines()[0]}
    con.close()
    return out


PROBES = {"sqlite": SQLite, "duckdb": DuckDB, "pg16": PG16, "pg18": PG18}


def main(names: list[str]) -> None:
    for name in names:
        cls = PROBES[name]
        container, schema = fixture()
        store = cls(schema)
        report = store.load(container)
        result: dict[str, Any] = {"backend": name, "load": {k: report[k] for k in ("records", "versions")},
                                  "native_write_seconds": round(store.write_seconds, 4)}
        if name == "sqlite":
            import sqlite3
            result["version"] = sqlite3.sqlite_version
        elif name == "duckdb":
            import duckdb
            result["version"] = duckdb.__version__
        else:
            result["version"] = store._q("SELECT version()")[0][0]
        result["hand"] = hand_check(store)
        store.find("co_administration_causes", [{"role": "agent", "value": {"entity": "ex:insulin"}},
                                                {"role": "agent", "value": {"entity": "ex:metformin"}}])
        result["find_sql_example"] = " ".join(store.last_sql.split())
        store.close()
        result["transaction_time"] = history_check(lambda s, c: cls(s, clock=c))
        result["read_only_scenarios"] = run_read_only(lambda s, c: cls(s, clock=c))
        if name.startswith("pg"):
            result["temporal_key_constraint"] = temporal_key_demo(cls.PORT)
        print(name, result["read_only_scenarios"]["counts"], "as_at:", result["transaction_time"], "export diffs:",
              result["hand"]["export khg-json round trip"]["differences"],
              "hand mismatches:", [k for k, v in result["hand"].items()
                                   if isinstance(v, dict) and v.get("same_as_reference") is False or "error" in v])
        write_out(f"sql-{name}", result)


if __name__ == "__main__":
    main(sys.argv[1:] or list(PROBES))
