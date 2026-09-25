"""The fidelity measures of the gate table (DESIGN §5; research 01 D5; ruling 5).

For each backend and each data set (P2's ``fixture.c1.json`` and ``fixture.history.c1.json``, and P1's edge-case
container ``fixtures/edge.c1.json``):

1. **Container round trip.** ``load(on_missing="skip")`` → ``export("khg-json")`` (with the container's
   ``content`` and ``as_at``) → ``compare_containers`` against the input: the records that differ, split into those
   the store skipped (a missing flag, or ``cannot_hold``, or a reference to a skipped record, each with its reason)
   and any other difference, which would be a silent loss. ``compare_containers`` ignores the store fields; they are
   compared separately, against ``MemoryStore`` holding the same records.
2. **Structural fidelity of the native layer.** Every held fact's bindings rebuilt from the layout's per-binding
   structure alone (``native_bindings``: rows, triples, edges, role players and owned attributes, incidences),
   without the record-level copies (``payload``, TypeDB's ``khg-bindings``). Per binding: bids, positions,
   directions, extensions and literals as written that survive; per fact: whether the role–value multiset
   survives.
3. **Answer fidelity.** A query set compared with ``MemoryStore``'s answer: ids in order for lists, the record
   for ``get``, steps and terminals for walks, the count for ``degree``; a refusal counts as the same answer when
   the reference refuses alike. The reference is ``MemoryStore`` with the backend's flags, loaded with the same
   container minus the records the backend skipped, so only the queries are compared. The query sets are the 13
   hand queries of research 01 on the fixture, ``EDGE`` on the edge container, and the 85 transaction-time checks
   of research 01 on the history fixture. The full query set (D6) comes in the second half.
4. **Inapplicable scenarios** by flag, from the conformance run (``conformance.losses``).
"""
from __future__ import annotations

import copy
import os
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from khg_contracts import data, jsonio
from khg_contracts.errors import CapabilityMissing, KHGError
from khg_contracts.record import identity_key, normalize, read_container
from khg_contracts.schema import load_schema
from khg_contracts.store import MemoryStore, ScenarioClock, Where, compare_containers, data_flags

from .backends import factory

__all__ = ["DATASETS", "EDGE", "HAND", "answers", "datasets", "measure", "native", "round_trip"]

KING = {"entity": "ex:KingOfFrance"}
#: Research 01's hand queries on the gate fixture (common.py ``HAND``).
HAND: list[tuple[str, str, dict[str, Any]]] = [
    ("get f:king-14", "get", {"id": "f:king-14"}),
    ("incident ex:KingOfFrance", "incident", {"node": "ex:KingOfFrance"}),
    ("incident ex:KingOfFrance as_of 1700", "incident",
     {"node": "ex:KingOfFrance", "where": Where(as_of="+1700-01-01T00:00:00Z")}),
    ("incident ex:TP53 (two roles, once)", "incident", {"node": "ex:TP53"}),
    ("incident f:born-louis14-paris (nesting)", "incident", {"node": "f:born-louis14-paris"}),
    ("find at_least agent insulin + metformin", "find",
     {"relation": "co_administration_causes", "pattern": [
         {"role": "agent", "value": {"entity": "ex:insulin"}},
         {"role": "agent", "value": {"entity": "ex:metformin"}}]}),
    ("find at_least agent insulin twice (injective: none)", "find",
     {"relation": "co_administration_causes", "pattern": [
         {"role": "agent", "value": {"entity": "ex:insulin"}}, {"role": "agent", "value": {"entity": "ex:insulin"}}]}),
    ("find at_least claims point_in_time 1700 (Julian, year)", "find",
     {"relation": "claims", "pattern": [{"role": "point_in_time", "value": {"literal": {
         "datatype": "time", "time": "+1700-00-00T00:00:00Z", "precision": 9, "calendar": "julian"}}}]}),
    ("find at_least flight_route stop YYZ at position 3", "find",
     {"relation": "flight_route", "pattern": [{"role": "stop", "value": {"entity": "ex:YYZ"}, "position": 3}]}),
    ("find_by_key position_held position KingOfFrance", "find_by_key",
     {"relation": "position_held", "key": [{"role": "position", "value": KING}]}),
    ("find_by_key born_in person Maria Skłodowska (all statuses)", "find_by_key",
     {"relation": "born_in", "key": [{"role": "person", "value": {"entity": "ex:Maria_Skłodowska"}}],
      "where": Where(status=frozenset({"asserted", "superseded"}))}),
    ("supersession_walk f:born-skłodowska-kraków", "supersession_walk", {"id": "f:born-skłodowska-kraków"}),
    ("supersession_walk f:born-skłodowska-warszawa backward", "supersession_walk",
     {"id": "f:born-skłodowska-warszawa", "direction": "backward"}),
]
TOKYO = {"literal": {"datatype": "lang_string", "value": "Tokyo Station", "lang": "en"}}
ASTRAL = "ex:\U00020BB7"
#: The queries on the edge-case container, one or more per hazard (fixtures/make_edge.py).
EDGE: list[tuple[str, str, dict[str, Any]]] = [
    ("incident astral node: eight ids in code-point order", "incident", {"node": ASTRAL}),
    ("incident astral node, first page of 3", "incident", {"node": ASTRAL, "limit": 3}),
    ("incident astral node, page after f:ł", "incident", {"node": ASTRAL, "limit": 3, "after": "f:ł"}),
    ("incident astral node, after f:東京", "incident", {"node": ASTRAL, "after": "f:東京"}),
    ("incident full-width node", "incident", {"node": "ex:ｚ"}),
    ("find catalysed_by catalyst astral", "find",
     {"relation": "catalysed_by", "pattern": [{"role": "catalyst", "value": {"entity": ASTRAL}}]}),
    ("degree astral node", "degree", {"node": ASTRAL}),
    ("get f:far-future (16-digit year)", "get", {"id": "f:far-future"}),
    ("incident far-future post as_of year 10000000000000001 (definite)", "incident",
     {"node": "ex:FarFuturePost", "where": Where(as_of="+10000000000000001-01-01T00:00:00Z")}),
    ("incident far-future post inside its start year (possible)", "incident",
     {"node": "ex:FarFuturePost", "where": Where(as_of="+9999999999999999-06-01T00:00:00Z", valid_mode="possible")}),
    ("incident far-future post inside its start year (definite: not yet)", "incident",
     {"node": "ex:FarFuturePost", "where": Where(as_of="+9999999999999999-06-01T00:00:00Z")}),
    ("incident far-future post as_of 2026 (definite)", "incident",
     {"node": "ex:FarFuturePost", "where": Where(as_of="+2026-01-01T00:00:00Z")}),
    ("incident far-future post as_of 2026 (possible)", "incident",
     {"node": "ex:FarFuturePost", "where": Where(as_of="+2026-01-01T00:00:00Z", valid_mode="possible")}),
    ("find alias_list two equal aliases", "find",
     {"relation": "alias_list", "pattern": [{"role": "alias", "value": TOKYO}, {"role": "alias", "value": TOKYO}]}),
    ("find alias_list alias at position 2", "find",
     {"relation": "alias_list", "pattern": [{"role": "alias", "value": TOKYO, "position": 2}]}),
    ("find alias_list three equal aliases (injective: none)", "find",
     {"relation": "alias_list", "pattern": [{"role": "alias", "value": TOKYO}] * 3}),
    ("get ex:Dual (two types)", "get", {"id": "ex:Dual"}),
    ("incident ex:Dual", "incident", {"node": "ex:Dual"}),
    ("find position_held holder any_unbound (goals)", "find",
     {"relation": "position_held", "pattern": [{"role": "holder", "value": {"any_unbound": True}}],
      "where": Where(status=frozenset({"goal"}))}),
    ("find measured_constant, empty pattern (literal-only fact)", "find",
     {"relation": "measured_constant", "pattern": []}),
    ("find measured_constant by value", "find",
     {"relation": "measured_constant", "pattern": [{"role": "constant_value", "value": {"literal": {
         "datatype": "quantity", "amount": "+299792458", "unit": "1"}}}]}),
    ("supersession_walk f:dia-a (diamond)", "supersession_walk", {"id": "f:dia-a"}),
    ("supersession_walk f:dia-d backward (diamond)", "supersession_walk", {"id": "f:dia-d", "direction": "backward"}),
    ("find_by_key born_in ex:Diamond, every status", "find_by_key",
     {"relation": "born_in", "key": [{"role": "person", "value": {"entity": "ex:Diamond"}}],
      "where": Where(status=frozenset({"asserted", "superseded"}))}),
]

FIXTURE_DIR = Path(data.path("fixture/fixture.c1.json")).parent


def _edge_dir() -> Path:
    """``KHG_BAKEOFF_FIXTURES``, else ``projects/p1-store-bakeoff/fixtures`` next to an editable install, else
    ``fixtures`` in or above the working directory."""
    env = os.environ.get("KHG_BAKEOFF_FIXTURES")
    if env:
        return Path(env)
    for d in (Path(__file__).resolve().parents[3] / "fixtures", Path.cwd() / "fixtures",
              Path.cwd().parent / "fixtures"):
        if (d / "edge.c1.json").is_file():
            return d
    raise FileNotFoundError("the edge-case container: set KHG_BAKEOFF_FIXTURES to projects/p1-store-bakeoff/fixtures")


def datasets() -> dict[str, tuple[Path, Path]]:
    """``{name: (container, schema)}``."""
    edge = _edge_dir()
    return {"fixture": (FIXTURE_DIR / "fixture.c1.json", FIXTURE_DIR / "fixture.relation-schema.json"),
            "history": (FIXTURE_DIR / "fixture.history.c1.json", FIXTURE_DIR / "fixture.relation-schema.json"),
            "edge": (edge / "edge.c1.json", edge / "edge.relation-schema.json")}


DATASETS = ("fixture", "history", "edge")


# ------------------------------------------------------------------------------------------------ 1. round trip


def _skip_reasons(store: Any, container: Mapping[str, Any], skipped: Iterable[str]) -> dict[str, Any]:
    """Why each skipped id was skipped: the missing flags, what the backend cannot hold, or a skipped reference."""
    out: dict[str, Any] = {}
    by_id = {r["id"]: r for r in container["records"] if isinstance(r, Mapping) and "id" in r}
    for rid in skipped:
        r = normalize(by_id[rid]) if rid in by_id else {}
        missing = sorted(data_flags(r) - store.capabilities)
        if missing:
            out[rid] = {"missing_flags": missing}
            continue
        why = store.cannot_hold(r) if hasattr(store, "cannot_hold") else None
        out[rid] = {"cannot_hold": why} if why else {"references": "a skipped record"}
    return out


def _export(store: Any, container: Mapping[str, Any]) -> dict[str, Any]:
    head = container["header"]
    content = head.get("content", "snapshot")
    return store.export("khg-json", content=content, as_at=head.get("as_at") if content == "history" else None)


def round_trip(store: Any, container: Mapping[str, Any], report: Mapping[str, Any],
               reference: Any) -> dict[str, Any]:
    """Number 1: the C1 content against the input (store fields ignored, as ``compare_containers`` does by
    default), and the store fields against ``reference`` (``MemoryStore`` holding the same records)."""
    exported = _export(store, container)
    diffs = compare_containers(container, exported)
    records = [d for d in diffs if "id" in d]
    skipped = set(report["skipped"])
    stored = [d for d in compare_containers(_export(reference, container), exported, ignore=()) if "id" in d]
    return {"records_in": len(container["records"]), "records_out": len(exported["records"]),
            "differing": len(records), "skipped": len(skipped),
            "skip_reasons": _skip_reasons(store, container, sorted(skipped)),
            "other_differences": [d["path"] for d in records if d.get("id") not in skipped],
            "header_differences": [d["path"] for d in diffs if "id" not in d],
            "store_field_differences": {d["path"]: d.get("fields") for d in stored}}


# ------------------------------------------------------------------------------------------------ 2. native layer


def _ident(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    if "identity" in value:  # TypeDB keeps a literal's identity only
        return value["identity"]
    if "unbound" in value:
        return "unbound:" + jsonio.canonical(value["unbound"].get("var"))
    try:
        return identity_key(value)
    except (KHGError, ValueError, TypeError, KeyError):
        return None


def native(store: Any, container: Mapping[str, Any], skipped: Iterable[str]) -> dict[str, Any]:
    """Number 2 over the held facts of the container (the latest version of each id)."""
    skipped = set(skipped)
    facts: dict[str, dict[str, Any]] = {}
    for r in container["records"]:
        if isinstance(r, Mapping) and r.get("kind") == "hyperedge" and r["id"] not in skipped:
            facts[r["id"]] = normalize(r)  # the history fixture lists versions oldest first: keep the last
    tally = Counter()
    lost: dict[str, list[str]] = {}
    for rid, src in sorted(facts.items()):
        got = store.native_bindings(rid)
        if got is None:
            continue
        tally["facts"] += 1
        sb = src.get("bindings") or []
        want = sorted((b["role"], _ident(b["value"])) for b in sb)
        if want == sorted((b["role"], _ident(b.get("value"))) for b in got):
            tally["multiset_kept"] += 1
        else:
            lost.setdefault("role-value multiset", []).append(rid)
        by_bid = {b.get("bid"): b for b in got if b.get("bid") is not None}
        pool = [b for b in got]
        for b in sb:
            tally["bindings"] += 1
            n = by_bid.get(b["bid"])
            if n is not None and n.get("role") == b["role"] and _ident(n.get("value")) == _ident(b["value"]):
                tally["bid_kept"] += 1
            else:
                n = next((x for x in pool if x.get("role") == b["role"] and _ident(x.get("value")) ==
                          _ident(b["value"])), None)
                if n is not None:
                    pool.remove(n)
            for field in ("position", "direction", "extensions"):
                if field in b:
                    tally[f"{field}s"] += 1
                    if n is not None and jsonio.canonical(n.get(field)) == jsonio.canonical(b[field]):
                        tally[f"{field}_kept"] += 1
                    else:
                        lost.setdefault(field, []).append(f"{rid} {b['bid']}")
            if "literal" in b["value"]:
                tally["literals"] += 1
                if n is not None and jsonio.canonical(n.get("value")) == jsonio.canonical(b["value"]):
                    tally["literal_as_written_kept"] += 1
                else:
                    lost.setdefault("literal as written", []).append(f"{rid} {b['bid']}")
    out = {k: tally.get(k, 0) for k in ("facts", "multiset_kept", "bindings", "bid_kept", "positions",
                                        "position_kept", "directions", "direction_kept", "extensionss",
                                        "extensions_kept", "literals", "literal_as_written_kept")}
    out["extensions"] = out.pop("extensionss")
    out["lost"] = {k: sorted(v) for k, v in sorted(lost.items())}
    return out


# ------------------------------------------------------------------------------------------------ 3. answers


def _call(store: Any, op: str, args: Mapping[str, Any]) -> Any:
    args = dict(args)
    if op == "get":
        return store.get(args.pop("id"), **args)
    if op == "incident":
        return store.incident(args.pop("node"), **args)
    if op == "degree":
        return store.degree(args.pop("node"), **args)
    if op == "find":
        return store.find(args.pop("relation"), args.pop("pattern"), **args)
    if op == "find_by_key":
        return store.find_by_key(args.pop("relation"), args.pop("key"), **args)
    if op == "supersession_walk":
        return store.supersession_walk(args.pop("id"), **args)
    raise ValueError(op)


def _answer(store: Any, op: str, args: Mapping[str, Any]) -> tuple[str, Any]:
    try:
        result = _call(store, op, args)
    except CapabilityMissing as e:
        return "refused", f"CapabilityMissing {e.flag}"
    except KHGError as e:
        return "refused", e.code or type(e).__name__
    except (ValueError, TypeError) as e:
        return "refused", type(e).__name__
    if isinstance(result, list):
        return "answer", [r.get("id") for r in result]
    if isinstance(result, dict) and "steps" in result:
        return "answer", {"steps": [(s["depth"], s["via"], s["from"], s["to"]) for s in result["steps"]],
                          "terminal": result["terminal"]}
    if isinstance(result, dict) or result is None:
        return "answer", None if result is None else jsonio.canonical(result)
    return "answer", result


def answers(store: Any, reference: Any, queries: Iterable[tuple[str, str, dict[str, Any]]]) -> dict[str, Any]:
    compared, same, refused, differ = 0, 0, 0, {}
    for label, op, args in queries:
        a = _answer(store, op, copy.deepcopy(args))
        b = _answer(reference, op, copy.deepcopy(args))
        compared += 1
        if a == b:
            same += 1
            refused += a[0] == "refused"
        else:
            differ[label] = {"store": a, "reference": b}
    return {"compared": compared, "same": same, "both_refused": refused, "differ": differ}


def history_answers(store: Any, reference: Any, container: Mapping[str, Any]) -> dict[str, Any]:
    """Research 01's transaction-time checks: get(as_at), get(version), history, incident(as_at), exports."""
    times = sorted({r["recorded_at"] for r in container["records"]})
    ids = sorted({r["id"] for r in container["records"]})
    compared, bad = 0, []

    def check(label: str, f: Callable[[Any], Any]) -> None:
        nonlocal compared
        compared += 1
        try:
            a = jsonio.canonical(f(store))
        except KHGError as e:
            a = f"refused {e.code or type(e).__name__}"
        try:
            b = jsonio.canonical(f(reference))
        except KHGError as e:
            b = f"refused {e.code or type(e).__name__}"
        if a != b:
            bad.append(label)

    for t in times:
        for i in ids:
            check(f"get {i} as_at {t}", lambda s, i=i, t=t: s.get(i, as_at=t))
        for node in ("ex:TP53", "ex:KingOfFrance", "ex:LouisXIII"):
            check(f"incident {node} as_at {t}",
                  lambda s, node=node, t=t: [r["id"] for r in s.incident(node, where=Where(as_at=t))])
        check(f"export as_at {t}", lambda s, t=t: s.export("khg-json", as_at=t)["records"])
    for i in ids:
        check(f"history {i}", lambda s, i=i: s.history(i))
        for v in (1, 2):
            check(f"get {i} version {v}", lambda s, i=i, v=v: s.get(i, version=v))
    check("export history", lambda s: s.export("khg-json", content="history")["records"])
    return {"compared": compared, "same": compared - len(bad), "differ": bad}


# ------------------------------------------------------------------------------------------------ the measure


def measure(name: str, endpoint: str | None = None, *, only: Iterable[str] = DATASETS) -> dict[str, Any]:
    """Numbers 1-3 of backend ``name`` on each data set."""
    make = factory(name, endpoint)
    out: dict[str, Any] = {}
    for ds in only:
        container_path, schema_path = datasets()[ds]
        schema = load_schema(schema_path)
        container = read_container(container_path)
        store = make(schema, ScenarioClock())
        try:
            try:
                report = store.load(copy.deepcopy(container), on_missing="skip")
            except CapabilityMissing as e:
                out[ds] = {"loaded": False, "reason": f"CapabilityMissing: {e.flag}",
                           "records_in": len(container["records"])}
                continue
            kept = {"header": container["header"],
                    "records": [r for r in container["records"] if r["id"] not in set(report["skipped"])]}
            reference = MemoryStore(schema, clock=ScenarioClock(), capabilities=store.capabilities)
            reference.load(copy.deepcopy(kept))
            entry: dict[str, Any] = {"loaded": True, "round_trip": round_trip(store, container, report, reference)}
            entry["native"] = native(store, container, report["skipped"])
            if ds == "fixture":
                entry["answers"] = answers(store, reference, HAND)
            elif ds == "edge":
                entry["answers"] = answers(store, reference, EDGE)
            else:
                entry["answers"] = history_answers(store, reference, container)
            out[ds] = entry
        finally:
            store.close()
    return out
