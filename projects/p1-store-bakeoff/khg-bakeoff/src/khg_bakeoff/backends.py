"""The six backends of the bake-off (ruling 1) and how to open them.

| Name | Engine | Kind | Endpoint (environment variable) |
|---|---|---|---|
| ``sqlite`` | SQLite through ``sqlite3`` | embedded | none |
| ``postgres`` | PostgreSQL 18 through psycopg 3 | client–server | ``KHG_BAKEOFF_POSTGRES``: a libpq conninfo without ``dbname`` |
| ``oxigraph`` | Oxigraph through pyoxigraph | embedded | none |
| ``neo4j`` | Neo4j Community through the neo4j driver | client–server | ``KHG_BAKEOFF_NEO4J``: a Bolt URI |
| ``typedb`` | TypeDB CE through typedb-driver | client–server | ``KHG_BAKEOFF_TYPEDB``: host:port (user ``admin``) |
| ``hif`` | one HIF file through khg-contracts | embedded | none |

``factory(name, endpoint=None)`` returns the conformance factory ``(schema, clock) -> store`` of a fresh, empty
store; ``endpoint`` defaults to the environment variable. ``available(name)`` says whether it can run here.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from typing import Any, Callable

__all__ = ["BACKENDS", "Backend", "available", "endpoint", "factory"]


@dataclass(frozen=True)
class Backend:
    name: str
    module: str
    layout: str
    kind: str
    env: str | None  # the environment variable naming the endpoint (None: embedded)
    client: str | None  # the Python module the adapter needs beyond the standard library


BACKENDS: dict[str, Backend] = {
    "sqlite": Backend("sqlite", "khg_bakeoff.sqlite", "incidence table", "embedded", None, None),
    "postgres": Backend("postgres", "khg_bakeoff.postgres", "incidence table", "client-server",
                        "KHG_BAKEOFF_POSTGRES", "psycopg"),
    "oxigraph": Backend("oxigraph", "khg_bakeoff.oxigraph", "reified RDF (named graph per version)", "embedded",
                        None, "pyoxigraph"),
    "neo4j": Backend("neo4j", "khg_bakeoff.neo4j", "bipartite property graph (version nodes)", "client-server",
                     "KHG_BAKEOFF_NEO4J", "neo4j"),
    "typedb": Backend("typedb", "khg_bakeoff.typedb", "TypeDB natural mapping", "client-server",
                      "KHG_BAKEOFF_TYPEDB", "typedb.driver"),
    "hif": Backend("hif", "khg_bakeoff.hif", "HIF file", "embedded", None, None),
}


def endpoint(name: str) -> str | None:
    b = BACKENDS[name]
    return os.environ.get(b.env) if b.env else None


def available(name: str, endpoint_: str | None = None) -> bool:
    """The client module is installed, and a server backend has an endpoint."""
    b = BACKENDS[name]
    if b.client is not None:
        try:
            if importlib.util.find_spec(b.client) is None:
                return False
        except ModuleNotFoundError:
            return False
    return b.env is None or bool(endpoint_ or endpoint(name))


def factory(name: str, endpoint_: str | None = None) -> Callable[[Any, Any], Any]:
    """The conformance factory of backend ``name``."""
    b = BACKENDS[name]
    mod = importlib.import_module(b.module)
    if b.env is None:
        return mod.factory
    where = endpoint_ or endpoint(name)
    if not where:
        raise ValueError(f"backend {name} needs an endpoint: set {b.env}")
    return mod.factory(where)
