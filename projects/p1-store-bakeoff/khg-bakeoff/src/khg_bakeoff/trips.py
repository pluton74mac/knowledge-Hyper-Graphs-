"""Round trips per operation and adapter (DESIGN §6.1; the director's ruling on review 01, R-06): measured, not
estimated.

Every adapter counts the calls it makes to its engine (``shared.Trips``), at the one place it makes them: SQL
statements (SQLite's are in-process calls), SPARQL queries and updates and ``bulk_extend``, Cypher queries, TypeQL
queries, and the begin and commit of each transaction; the HIF store counts its file reads and writes. ``measure``
runs ``OPS`` on P2's gate fixture, one store per backend, and reports the calls of each operation by kind (``read``,
``write``, ``tx``, ``file``). ``put`` is measured apart from ``load`` (research 01 D2). ``scaling`` checks that
the calls of a load into an empty store, of an export and of a read with many answers do not grow with the number of
records.
"""
from __future__ import annotations

import copy
from typing import Any, Callable

from khg_contracts import data
from khg_contracts.schema import load_schema
from khg_contracts.store import ScenarioClock, conformance

from .backends import factory

__all__ = ["OPS", "measure", "scaling", "synthetic"]

KING = {"entity": "ex:KingOfFrance"}
EVIDENCE = {"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:trips"}}
TEN = ["ex:Paris", "ex:LouisXIV", "f:king-13", "f:king-14", "f:reg-1", "f:route-1", "m:sup-1", "ex:TP53",
       "f:claim-1", "ex:nothing"]


def _put_one(s: Any) -> Any:
    return s.put(conformance.suite().resolve({"@": "f:king-14", "set": {"rank": "preferred"}}), actor="t")


def _put_two(s: Any) -> Any:
    person = {"kind": "entity", "id": "ex:Trips", "types": ["Person"], "label": "Trips"}
    fact = {"kind": "hyperedge", "id": "f:born-trips-paris", "relation": "born_in", "status": "asserted",
            "bindings": [{"bid": "b1", "role": "person", "value": {"entity": "ex:Trips"}},
                         {"bid": "b2", "role": "birthplace", "value": {"entity": "ex:Paris"}}],
            "evidence": [EVIDENCE]}
    return s.put([person, fact], actor="t")


#: ``(label, call)``, run in this order on a store that has just loaded the fixture (the first is that load).
OPS: list[tuple[str, Callable[[Any], Any]]] = [
    ("load: the fixture into an empty store (40 records)", lambda s: None),
    ("get: a fact (f:king-14)", lambda s: s.get("f:king-14")),
    ("get: an entity (ex:Paris)", lambda s: s.get("ex:Paris")),
    ("get_many: 10 ids", lambda s: s.get_many(TEN)),
    ("history: f:king-14", lambda s: s.history("f:king-14")),
    ("incident: ex:KingOfFrance (2 answers)", lambda s: s.incident("ex:KingOfFrance")),
    ("incident: ex:KingOfFrance, limit 1", lambda s: s.incident("ex:KingOfFrance", limit=1)),
    ("degree: ex:KingOfFrance", lambda s: s.degree("ex:KingOfFrance")),
    ("find: position_held, position KingOfFrance", lambda s: s.find("position_held", [{"role": "position",
                                                                                         "value": KING}])),
    ("find: position_held, [] (relation scan)", lambda s: s.find("position_held", [])),
    ("find_by_key: position_held, KingOfFrance", lambda s: s.find_by_key("position_held", [{"role": "position",
                                                                                           "value": KING}])),
    ("supersession_walk: f:born-skłodowska-kraków", lambda s: s.supersession_walk("f:born-skłodowska-kraków")),
    ("export: khg-json of the store", lambda s: s.export("khg-json")),
    ("put: one new version (f:king-14)", _put_one),
    ("put: two new records (an entity and a fact)", _put_two),
    ("load: the fixture again (40 held ids, new versions)", None),
]


def _fixture() -> tuple[Any, dict[str, Any]]:
    return (load_schema(data.load_json("fixture/fixture.relation-schema.json")),
            data.load_json("fixture/fixture.c1.json"))


def _calls(store: Any, run: Callable[[], Any]) -> dict[str, Any]:
    store.trips.clear()
    try:
        run()
        error = None
    except Exception as e:  # noqa: BLE001 - a refusal is an answer here (a missing flag, say)
        error = getattr(e, "code", None) or type(e).__name__
    out: dict[str, Any] = {"calls": store.trips.calls(), **{k: store.trips[k] for k in sorted(store.trips)}}
    if error:
        out["refused"] = error
    return out


def measure(name: str, endpoint: str | None = None) -> dict[str, dict[str, Any]]:
    """``{operation: {calls, read, write, tx, file, refused?}}`` of backend ``name`` on the fixture (``OPS``)."""
    schema, fixture = _fixture()
    s = factory(name, endpoint)(schema, ScenarioClock())
    out: dict[str, dict[str, Any]] = {}
    try:
        for label, op in OPS:
            if label.startswith("load: the fixture into"):
                out[label] = _calls(s, lambda: s.load(copy.deepcopy(fixture), on_missing="skip"))
            elif op is None:
                out[label] = _calls(s, lambda: s.load(copy.deepcopy(fixture), on_missing="skip"))
            else:
                out[label] = _calls(s, lambda op=op: op(s))
    finally:
        s.close()
    return out


def synthetic(n: int) -> dict[str, Any]:
    """P2's fixture plus ``n`` people born in ``ex:Paris`` (``n`` entities and ``n`` facts)."""
    doc = copy.deepcopy(_fixture()[1])
    for i in range(n):
        doc["records"].append({"kind": "entity", "id": f"ex:P{i:05d}", "types": ["Person"], "label": f"P{i}"})
        doc["records"].append({"kind": "hyperedge", "id": f"f:born-p{i:05d}", "relation": "born_in",
                               "status": "asserted",
                               "bindings": [{"bid": "b1", "role": "person", "value": {"entity": f"ex:P{i:05d}"}},
                                            {"bid": "b2", "role": "birthplace", "value": {"entity": "ex:Paris"}}],
                               "evidence": [EVIDENCE]})
    return doc


def scaling(name: str, sizes: tuple[int, int] = (0, 200), endpoint: str | None = None) -> dict[str, list[dict]]:
    """The calls of the same operations on stores of two sizes (``synthetic``): a load into an empty store, the
    export, ``incident(ex:Paris)`` (every added fact answers it), ``degree(ex:Paris)``, and a second load of the
    same container (every id held)."""
    schema = _fixture()[0]
    out: dict[str, list[dict[str, Any]]] = {}
    for n in sizes:
        doc = synthetic(n)
        s = factory(name, endpoint)(schema, ScenarioClock())
        try:
            for label, run in (("load, empty store", lambda: s.load(copy.deepcopy(doc), on_missing="skip")),
                               ("export", lambda: s.export("khg-json")),
                               ("incident ex:Paris", lambda: s.incident("ex:Paris")),
                               ("degree ex:Paris", lambda: s.degree("ex:Paris")),
                               ("get_many, every id", lambda: s.get_many([r["id"] for r in doc["records"]])),
                               ("load, every id held", lambda: s.load(copy.deepcopy(doc), on_missing="skip"))):
                out.setdefault(label, []).append({"records": len(doc["records"]), **_calls(s, run)})
        finally:
            s.close()
    return out
