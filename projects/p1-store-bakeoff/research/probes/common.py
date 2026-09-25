"""Shared code for the P1 backend probes (research/01-backends.md).

Each probe maps P2's gate fixture into one backend in that backend's natural layout, answers the C2 read
operations with native queries (SQL, SPARQL, Cypher or TypeQL), and runs the conformance scenarios that only load
the fixture and read (46 of the 114) with khg_contracts' own runner. What is backend-agnostic lives here:

- ``fixture()``: the gate fixture container and its schema;
- ``split(record, schema)`` and ``assemble(...)``: a hyperedge version as one fact row plus one row per binding
  (the natural incidence layout; P2 DESIGN §2.10 ``incidence_rows`` plus the columns the reads filter on), and back;
- ``ReadOnlyProbe``: a ``StoreBase`` whose ``load`` stages the container through ``MemoryStore``'s trusted load
  (normalisation, versions, transaction times, header state) and hands the versioned records to the backend. It
  checks capability flags and arguments as ``MemoryStore`` does; ``put`` and ``apply`` are not probed;
- ``READ_ONLY``: the 46 scenario ids; ``run_read_only(factory)`` runs them;
- ``HAND``: the core operations of the brief (get, incident, find at_least, find_by_key, supersession_walk,
  export), and ``hand_check(store, native_walk)`` compares the backend's answers with ``MemoryStore``'s.

Nothing here writes to the repository except ``write_out`` (``probes/out/<name>.json``).
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from khg_contracts import CONTRACTS, jsonio
from khg_contracts.record import (NEG_INF, POS_INF, binding_sort_key, bounds, identity_key, key_digest,
                                  read_container)
from khg_contracts.schema import LIFECYCLE_RELATIONS, load_schema
from khg_contracts.store import MemoryStore, ScenarioClock, StoreBase, Where, compare_containers
from khg_contracts.store.conformance import runner, suite
from khg_contracts.store.flags import pattern_flags, where_flags
from khg_contracts.store.protocol import INTERFACE_VERSION, RECORD_FORMAT

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
FIXTURE_DIR = REPO / "src" / "khg_contracts" / "data" / "fixture"
FIXTURE_PATH = FIXTURE_DIR / "fixture.c1.json"
SCHEMA_PATH = FIXTURE_DIR / "fixture.relation-schema.json"
OUT = HERE / "out"

#: Instants are seconds on the proleptic Gregorian line (khg_contracts.record.windows); +-inf become these
#: sentinels so that every backend can hold them in a 64-bit integer. Years beyond about +-1.4e11 would collide
#: with them (C1 allows 16-digit years); the probes report that as a limit, the fixture never reaches it.
NEG, POS = -(2 ** 62), 2 ** 62
STORE_FIELDS = ("version", "recorded_at", "recorded_by")
HEADER_FIELDS = ("kind", "id", "relation", "status", "status_ref", "rank", "visibility", "bindings") + STORE_FIELDS


def fixture() -> tuple[dict[str, Any], Any]:
    """The gate fixture (``fixture.c1.json``) and its schema (``fixture.relation-schema.json``)."""
    return read_container(FIXTURE_PATH), load_schema(SCHEMA_PATH)


def clamp(x: float | int) -> int:
    if x == NEG_INF:
        return NEG
    if x == POS_INF:
        return POS
    return int(x)


def micros(ts: str) -> int:
    from khg_contracts.store import parse_timestamp

    return parse_timestamp(ts)


# ------------------------------------------------------------------------------------------------ rows


def split(record: Mapping[str, Any], schema: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """A stored hyperedge version as ``(fact row, binding rows)``.

    The fact row holds what the reads filter on (relation, status, rank, visibility, relation kind, key digest,
    the four bound-table instants, the number of bindings), the store fields, ``status_ref`` and ``payload``: the
    canonical JSON of every other field (evidence, confidence, goal, rank_reason, reason, note, source_text,
    typed_under, extensions). A binding row holds bid, role, position, direction, value kind, ``ref`` (the entity
    or fact id), ``ident`` (the value identity, ``record.identity_key``; None for ``unbound``), ``value_json`` (the
    value as written) and the binding's extensions.
    """
    try:
        b = bounds(record, schema)
        s_lo, s_hi, e_lo, e_hi = (clamp(x) for x in (b.s_lo, b.s_hi, b.e_lo, b.e_hi))
    except Exception:  # noqa: BLE001 - a record a trusted load kept but cannot be read passes no as_of filter
        s_lo, s_hi, e_lo, e_hi = POS, POS, NEG, NEG
    try:
        kd = key_digest(record, schema)
    except Exception:  # noqa: BLE001
        kd = None
    rel = record["relation"]
    fact = {
        "id": record["id"], "version": record["version"], "recorded_at": record["recorded_at"],
        "recorded_by": record["recorded_by"], "tx_from": micros(record["recorded_at"]), "tx_to": None,
        "relation": rel, "rel_kind": "lifecycle" if rel in LIFECYCLE_RELATIONS else "fact",
        "status": record["status"], "status_ref": record.get("status_ref"),
        "rank": record.get("rank", "normal"), "visibility": record.get("visibility", "visible"),
        "key_digest": kd, "s_lo": s_lo, "s_hi": s_hi, "e_lo": e_lo, "e_hi": e_hi,
        "n_bindings": len(record.get("bindings") or []),
        "payload": jsonio.canonical({k: v for k, v in record.items() if k not in HEADER_FIELDS}),
    }
    rows = []
    for bnd in record.get("bindings") or []:
        v = bnd["value"]
        (kind,) = v.keys()
        rows.append({
            "fact_id": record["id"], "version": record["version"], "bid": bnd["bid"], "role": bnd["role"],
            "position": bnd.get("position"), "direction": bnd.get("direction"), "value_kind": kind,
            "ref": v[kind] if kind in ("entity", "fact") else None,
            "ident": None if kind == "unbound" else identity_key(v),
            "value_json": jsonio.canonical(v),
            "extensions": jsonio.canonical(bnd["extensions"]) if "extensions" in bnd else None,
        })
    return fact, rows


def assemble(fact: Mapping[str, Any], rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """A hyperedge record from its fact row and binding rows (the inverse of ``split``)."""
    r: dict[str, Any] = {"kind": "hyperedge", "id": fact["id"], "relation": fact["relation"],
                         "status": fact["status"], "rank": fact["rank"], "visibility": fact["visibility"]}
    if fact.get("status_ref") is not None:
        r["status_ref"] = fact["status_ref"]
    r.update(json.loads(fact["payload"]))
    bindings = []
    for row in rows:
        b: dict[str, Any] = {"bid": row["bid"], "role": row["role"]}
        kind = row["value_kind"]
        b["value"] = {kind: row["ref"]} if kind in ("entity", "fact") else json.loads(row["value_json"])
        if row.get("position") is not None:
            b["position"] = int(row["position"])
        if row.get("direction") is not None:
            b["direction"] = row["direction"]
        if row.get("extensions") is not None:
            b["extensions"] = json.loads(row["extensions"])
        bindings.append(b)
    r["bindings"] = sorted(bindings, key=binding_sort_key)
    r["version"] = int(fact["version"])
    r["recorded_at"] = fact["recorded_at"]
    r["recorded_by"] = fact["recorded_by"]
    return r


def entity_row(record: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": record["id"], "version": record["version"], "recorded_at": record["recorded_at"],
            "recorded_by": record["recorded_by"], "tx_from": micros(record["recorded_at"]), "tx_to": None,
            "record": jsonio.canonical(dict(record))}


def close_versions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Set ``tx_to`` of every version to the ``tx_from`` of the next version of its id (system-time periods)."""
    by_id: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_id.setdefault(r["id"], []).append(r)
    for vs in by_id.values():
        vs.sort(key=lambda r: r["version"])
        for a, b in zip(vs, vs[1:]):
            a["tx_to"] = b["tx_from"]
    return rows


# ------------------------------------------------------------------------------------------------ patterns


class Pat:
    """One prepared ``find`` pattern: role, position (None: any), kind (value, any, any_unbound), identity."""

    __slots__ = ("role", "position", "kind", "ident")

    def __init__(self, role: str, position: int | None, kind: str, ident: str | None):
        self.role, self.position, self.kind, self.ident = role, position, kind, ident

    def __repr__(self) -> str:
        return f"Pat({self.role!r}, {self.position!r}, {self.kind!r}, {self.ident!r})"


def prepare(pattern: Any) -> list[Pat]:
    """The prepared patterns; ``TypeError``/``ValueError`` on a malformed one (as ``MemoryStore._patterns``)."""
    if isinstance(pattern, (str, bytes, Mapping)) or not isinstance(pattern, Sequence):
        raise TypeError("pattern is a sequence of {role, value, position?}")
    out = []
    for p in pattern:
        if not isinstance(p, Mapping) or not isinstance(p.get("role"), str) or "value" not in p or \
                set(p) - {"role", "value", "position"}:
            raise ValueError(f"a pattern is {{role, value, position?}}, not {p!r}")
        position = p.get("position")
        if position is not None and (isinstance(position, bool) or not isinstance(position, int) or position < 1):
            raise ValueError(f"a pattern position is a positive integer, not {position!r}")
        v = p["value"]
        if v == {"any": True}:
            out.append(Pat(p["role"], position, "any", None))
        elif v == {"any_unbound": True}:
            out.append(Pat(p["role"], position, "any_unbound", None))
        else:
            out.append(Pat(p["role"], position, "value", identity_key(v)))
    return out


# ------------------------------------------------------------------------------------------------ the probe store


class ReadOnlyProbe(StoreBase):
    """The read half of C2 over one backend. Subclasses implement ``_open``, ``_write(entities, facts, bindings)``,
    ``_get``, ``_versions``, ``_ids``, ``_is_fact``, ``_incident_ids``, ``_find_ids``, ``_key_ids`` and optionally
    ``native_walk``; this class supplies argument checks, flags, the kept header and record assembly."""

    FLAGS: frozenset[str] = frozenset()
    NAME = "probe"

    def __init__(self, schema: Any, *, clock: Any = None, capabilities: Iterable[str] | None = None,
                 store_id: str | None = None):
        super().__init__(schema, clock=clock, capabilities=self.FLAGS if capabilities is None else capabilities,
                         store_id=store_id or self.NAME)
        self._header: dict[str, Any] | None = None
        self._documents: list[dict[str, Any]] = []
        self.write_seconds = 0.0
        self._open()

    # -- backend hooks
    def _open(self) -> None: ...
    def _write(self, entities: list[dict], facts: list[dict], bindings: list[dict]) -> None: ...
    def _get(self, id: str, t: int | None, version: int | None) -> dict | None: ...  # a record or None
    def _versions(self, id: str) -> list[dict]: ...
    def _ids(self, t: int | None) -> list[str]: ...  # every id held at t
    def _is_fact(self, id: str) -> bool: ...
    def _incident_ids(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                      as_of: int | None, after: str | None, limit: int | None) -> list[str]: ...
    def _find_ids(self, relation: str, pats: list[Pat], match: str, where: Where, t: int | None,
                  as_of: int | None, after: str | None, limit: int | None) -> list[str]: ...
    def _key_ids(self, relation: str, digest: str, where: Where, t: int | None, as_of: int | None) -> list[str]: ...

    # -- C2
    def info(self) -> dict[str, Any]:
        return {"interface_version": INTERFACE_VERSION, "record_format": RECORD_FORMAT,
                "capabilities": self.capabilities, "store_id": self.store_id,
                "header": copy.deepcopy(self._header), "contracts": dict(CONTRACTS)}

    def put(self, *a: Any, **k: Any) -> Any:
        raise NotImplementedError("the P1 probes load and read only")

    def apply(self, *a: Any, **k: Any) -> Any:
        raise NotImplementedError("the P1 probes load and read only")

    def load(self, container: Any, *, header: Mapping[str, Any] | None = None, at: str | None = None,
             on_missing: str = "raise") -> dict[str, Any]:
        staging = MemoryStore(self.schema, clock=self.clock, capabilities=self.capabilities, store_id="staging")
        report = staging.load(container, header=header, at=at, on_missing=on_missing)
        self._header = staging.info()["header"]
        self._documents = copy.deepcopy(staging._documents)  # noqa: SLF001 - probe code
        records = [e.record for rid in staging._table.ids() for e in staging._table.entries(rid)]  # noqa: SLF001
        entities, facts, bindings = [], [], []
        for r in records:
            if r["kind"] == "entity":
                entities.append(entity_row(r))
            else:
                f, bs = split(r, self.schema)
                facts.append(f)
                bindings += bs
        started = time.perf_counter()
        self._write(close_versions(entities), close_versions(facts), bindings)
        self.write_seconds = time.perf_counter() - started
        report["seconds"] = self.write_seconds
        return report

    def _t(self, as_at: str | None) -> int | None:
        return None if as_at is None else micros(as_at)

    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> dict | None:
        if as_at is not None or version is not None:
            self.need("transaction_time")
        return self._get(id, self._t(as_at), version)

    def history(self, id: str) -> list[dict]:
        return self._versions(id)

    def _where(self, where: Any) -> Where:
        where = Where.of(where)
        for flag in sorted(where_flags(where)):
            self.need(flag)
        return where

    @staticmethod
    def _page(limit: Any, after: Any) -> None:
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
            raise ValueError(f"limit is None or a non-negative integer, not {limit!r}")
        if after is not None and not isinstance(after, str):
            raise TypeError(f"after is None or an id, not {type(after).__name__}")

    def _records(self, ids: list[str], t: int | None) -> list[dict]:
        out = []
        for i in ids:
            r = self._get(i, t, None)
            if r is not None:
                out.append(r)
        return out

    def incident(self, node: str, *, role: str | None = None, relation: str | None = None,
                 where: Where = Where(), limit: int | None = None, after: str | None = None) -> list[dict]:
        self._page(limit, after)
        where = self._where(where)
        if relation is not None:
            self.schema.relation(relation)
        if isinstance(node, str) and self._is_fact(node):
            self.need("nesting")
        if limit == 0:
            return []
        t = where.as_at_micros
        as_of = None if where.as_of is None else clamp(where.as_of_seconds)
        return self._records(self._incident_ids(node, role, relation, where, t, as_of, after, limit), t)

    def find(self, relation: str, pattern: Sequence[Mapping[str, Any]], *, match: str = "at_least",
             where: Where = Where(), limit: int | None = None, after: str | None = None) -> list[dict]:
        self._page(limit, after)
        if match not in ("at_least", "exact"):
            raise ValueError(f"match is at_least or exact, not {match!r}")
        self.schema.relation(relation)
        pats = prepare(pattern)
        where = self._where(where)
        for flag in sorted(pattern_flags(list(pattern), lifecycle=relation in LIFECYCLE_RELATIONS)):
            self.need(flag)
        if limit == 0:
            return []
        t = where.as_at_micros
        as_of = None if where.as_of is None else clamp(where.as_of_seconds)
        return self._records(self._find_ids(relation, pats, match, where, t, as_of, after, limit), t)

    def find_by_key(self, relation: str, key: Sequence[Mapping[str, Any]], *, where: Where = Where()) -> list[dict]:
        """StoreBase's argument checks, then one native lookup on the indexed key digest."""
        declared = self.schema.key(relation)
        if not declared:
            raise ValueError(f"find_by_key: {relation!r} declares no key")
        if isinstance(key, Mapping) or isinstance(key, (str, bytes)):
            raise TypeError("key is a sequence of patterns {role, value, position?}")
        patterns = list(key)
        for p in patterns:
            value = p.get("value") if isinstance(p, Mapping) else None
            if not isinstance(value, Mapping) or value.get("any") is True or value.get("any_unbound") is True:
                raise ValueError("find_by_key binds each key role to a value")
        if {p.get("role") for p in patterns} != set(declared["roles"]):
            raise ValueError(f"find_by_key binds exactly the key roles {sorted(declared['roles'])}")
        where = self._where(where)
        for flag in sorted(pattern_flags(patterns)):
            self.need(flag)
        probe = {"kind": "hyperedge", "id": "_:key", "relation": relation, "status": "asserted",
                 "bindings": [{"bid": f"b{n}", "role": p["role"], "value": p["value"],
                               **({"position": p["position"]} if "position" in p else {})}
                              for n, p in enumerate(patterns, 1)]}
        digest = key_digest(probe, self.schema)
        if digest is None:
            return []
        t = where.as_at_micros
        as_of = None if where.as_of is None else clamp(where.as_of_seconds)
        return self._records(self._key_ids(relation, digest, where, t, as_of), t)

    def iter_records(self, *, content: str = "snapshot", as_at: str | None = None):
        if content not in ("snapshot", "history"):
            raise ValueError(f"content is snapshot or history, not {content!r}")
        if content == "history":
            self.need("history_export")
        if as_at is not None:
            self.need("transaction_time")
        t = self._t(as_at)
        out = [copy.deepcopy(d) for d in self._documents]
        for i in self._ids(t):
            if content == "history":
                out += [r for r in self._versions(i) if t is None or micros(r["recorded_at"]) <= t]
            else:
                r = self._get(i, t, None)
                if r is not None:
                    out.append(r)
        return iter(out)

    def native_walk(self, id: str, direction: str = "forward") -> list[dict] | None:
        """The walk's steps from one native (recursive) query, or None when the backend has none."""
        return None


# ------------------------------------------------------------------------------------------------ scenarios


def _read_only_ids() -> list[str]:
    s = suite()
    reads = {"get", "get_many", "history", "incident", "degree", "find", "find_by_key", "supersession_walk",
             "export"}
    return [i for i, sc in s.scenarios.items()
            if all("load" in g for g in sc["given"]) and all(w["op"] in reads for w in sc["when"])]


READ_ONLY = _read_only_ids()


def run_read_only(factory: Callable[[Any, Any], Any], capabilities: Iterable[str] | None = None) -> dict[str, Any]:
    """The read-only scenarios on stores from ``factory``: counts per outcome and the failures' info."""
    outcomes, info, tested = runner.run_suite(factory, only=READ_ONLY, capabilities=capabilities)
    counts: dict[str, int] = {}
    for o in outcomes:
        counts[o.outcome] = counts.get(o.outcome, 0) + 1
    return {"selected": len(outcomes), "counts": counts, "tested_flags": sorted(tested),
            "not_passed": {o.id: f"{o.outcome}: {o.info}"[:400] for o in outcomes if o.outcome != "passed"}}


# ------------------------------------------------------------------------------------------------ hand queries

KING = {"entity": "ex:KingOfFrance"}
HAND: list[tuple[str, str, dict[str, Any]]] = [
    ("get f:king-14", "get", {"id": "f:king-14"}),
    ("incident ex:KingOfFrance", "incident", {"node": "ex:KingOfFrance"}),
    ("incident ex:KingOfFrance as_of 1700", "incident",
     {"node": "ex:KingOfFrance", "where": Where(as_of="+1700-01-01T00:00:00Z")}),
    ("incident ex:TP53 (two roles, once)", "incident", {"node": "ex:TP53"}),
    ("incident f:born-louis14-paris (nesting)", "incident", {"node": "f:born-louis14-paris"}),
    ("find at_least agent insulin + metformin", "find",
     {"relation": "co_administration_causes", "pattern": [
         {"role": "agent", "value": {"entity": "ex:insulin"}}, {"role": "agent", "value": {"entity": "ex:metformin"}}]}),
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


def _call(store: Any, op: str, args: dict[str, Any]) -> Any:
    args = dict(args)
    if op == "get":
        return store.get(args.pop("id"), **args)
    if op == "incident":
        return store.incident(args.pop("node"), **args)
    if op == "find":
        return store.find(args.pop("relation"), args.pop("pattern"), **args)
    if op == "find_by_key":
        return store.find_by_key(args.pop("relation"), args.pop("key"), **args)
    if op == "supersession_walk":
        return store.supersession_walk(args.pop("id"), **args)
    raise ValueError(op)


def _summary(result: Any) -> Any:
    if isinstance(result, list):
        return [r.get("id") for r in result]
    if isinstance(result, dict) and "steps" in result:
        return {"steps": [(s["depth"], s["via"], s["from"], s["to"]) for s in result["steps"]],
                "terminal": result["terminal"]}
    return result


def hand_check(store: Any, *, skip: Iterable[str] = ()) -> dict[str, Any]:
    """The HAND operations on ``store`` (loaded with the fixture) against a MemoryStore reference; the export's
    round trip (``compare_containers``); and the native walk against StoreBase's."""
    container, schema = fixture()
    ref = MemoryStore(schema, clock=ScenarioClock())
    ref.load(copy.deepcopy(container))
    out: dict[str, Any] = {}
    skip = set(skip)
    for label, op, args in HAND:
        if label in skip:
            out[label] = {"skipped": True}
            continue
        want = _summary(_call(ref, op, args))
        try:
            got_full = _call(store, op, args)
            got = _summary(got_full)
            same = (got == want) if op != "get" else (compare_containers(
                {"header": container["header"], "records": [ref.get(args["id"])]},
                {"header": container["header"], "records": [got_full]}) == [])
            out[label] = {"same_as_reference": same, "got": got if op != "get" else "record"}
            if not same:
                out[label]["want"] = want
        except Exception as e:  # noqa: BLE001 - the probe reports what the backend cannot do
            out[label] = {"error": f"{type(e).__name__}: {e}"[:300]}
    exported = store.export("khg-json")
    diffs = compare_containers(container, exported)
    out["export khg-json round trip"] = {"differences": len(diffs), "first": diffs[:3]}
    walk = store.native_walk("f:born-skłodowska-kraków")
    if walk is not None:
        ref_steps = sorted((s["depth"], s["via"], s["from"], s["to"])
                           for s in ref.supersession_walk("f:born-skłodowska-kraków")["steps"])
        out["native recursive walk"] = {"steps": walk, "same_as_reference": sorted(map(tuple, walk)) == ref_steps}
    return out


def write_out(name: str, data: Mapping[str, Any]) -> Path:
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------------------------------------------ transaction time

HISTORY_PATH = FIXTURE_DIR / "fixture.history.c1.json"


def history_check(factory: Callable[[Any, Any], Any]) -> dict[str, Any]:
    """Transaction-time reads on the history fixture (10 versions; f:king-13 and f:reg-1 have two each, f:reg-1 v2
    is retracted): get(as_at), get(version), history, incident(as_at) and history/as_at exports, against
    MemoryStore. The read-only scenarios need writes to make versions, so this is the probes' as_at test."""
    container = read_container(HISTORY_PATH)
    _, schema = fixture()
    ref = MemoryStore(schema, clock=ScenarioClock())
    ref.load(copy.deepcopy(container))
    store = factory(schema, ScenarioClock())
    store.load(copy.deepcopy(container))
    times = sorted({r["recorded_at"] for r in container["records"]})
    ids = sorted({r["id"] for r in container["records"]})
    checks, bad = 0, []

    def same(label: str, a: Any, b: Any) -> None:
        nonlocal checks
        checks += 1
        if jsonio.canonical(a) != jsonio.canonical(b):
            bad.append(label)

    for t in times:
        for i in ids:
            same(f"get {i} as_at {t}", store.get(i, as_at=t), ref.get(i, as_at=t))
        for node in ("ex:TP53", "ex:KingOfFrance", "ex:LouisXIII"):
            w = Where(as_at=t)
            same(f"incident {node} as_at {t}", [r["id"] for r in store.incident(node, where=w)],
                 [r["id"] for r in ref.incident(node, where=w)])
        same(f"export as_at {t}", compare_containers(ref.export("khg-json", as_at=t), store.export("khg-json", as_at=t)),
             [])
    for i in ids:
        same(f"history {i}", store.history(i), ref.history(i))
        for v in (1, 2):
            same(f"get {i} version {v}", store.get(i, version=v), ref.get(i, version=v))
    same("export history", compare_containers(ref.export("khg-json", content="history"),
                                              store.export("khg-json", content="history")), [])
    store.close()
    return {"checks": checks, "mismatches": bad}
