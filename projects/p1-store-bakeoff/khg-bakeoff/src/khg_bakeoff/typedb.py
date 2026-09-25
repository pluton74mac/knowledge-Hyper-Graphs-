"""The TypeDB adapter (DESIGN §3.4): the natural mapping of a relation-type schema to TypeQL, in TypeDB CE 3.x through
typedb-driver (research 01 §5; ruling 8: the natural mapping only).

``TypeDBStore(schema, *, address, username="admin", password="password", database=None, clock=None,
capabilities=None, store_id="typedb")`` keeps one store in one database (``database=None``: a fresh one that
``close`` deletes).

**The mapping** (``TypeQLSchema``; every label is the schema name with each character outside ``[A-Za-z0-9_]``
written as ``-<hex>-``, so the mapping is injective):

- ``entity khg-entity @abstract``; each entity type ``ent-<T>``, ``sub`` its first parent (TypeDB has single
  inheritance), else ``sub khg-entity``. An instance has exactly one type.
- ``relation khg-fact @abstract`` owns the header attributes (``khg-id @key``, status, rank, visibility, relation
  kind, status_ref, key digest, the four instants, the number of bindings, the payload, the store fields and
  ``khg-tx``, the transaction time); each schema relation and each lifecycle relation is ``rel-<R>, sub khg-fact``.
- A usage with entity or fact fillers is a scoped role ``relates role-<r> @card(0..)``; each filler type (and each
  of its subtypes that does not inherit through the first-parent chain) ``plays`` it. ``{"entity": []}`` (any
  entity) is played by ``khg-entity``, ``{"fact": []}`` by ``khg-fact``.
- A usage with literal fillers is an owned attribute ``lit-<r>`` holding the value identity
  (``record.identity_key``), because an attribute cannot play a role (DEX11).
- ``khg-bindings`` keeps the bindings as canonical JSON: bids, positions, directions, binding extensions and the
  literals as written have no other home (role-player edges carry no attributes; lists are "not yet implemented",
  REP254), and a repeated player or an equal literal in one role collapses (owned attributes and players are sets).
  Records are read back from it; ``native_bindings`` rebuilds them without it (fidelity number 2).
- ``entity khg-meta`` holds the latest transaction time, the kept header and the embedded documents.

**Flags.** One instance per id and no reads of an earlier commit (typedb/typedb#7554), so ``transaction_time`` and
``history_export`` are absent; no player for ``somevalue``, ``novalue`` or ``unbound``, so ``special_values`` and
``goals`` are absent; no role-player lists, so ``ordered_roles`` is absent (ruling 3, research 01 §5.5): 70 of the
114 scenarios apply. A new version rewrites its instance in place (attributes by ``update``, players and literals
by ``delete`` and ``insert``), so referrers keep pointing at it.

**What it cannot hold** (``cannot_hold``): an entity with other than one type, or whose type would change; a fact
with no entity or fact binding (TypeDB deletes a relation without players at commit); a special, unbound or
positioned binding; two bindings of one role with one value identity (players and owned attributes are sets); a
relation or type the schema does not declare; and, in a load, a fact whose entity or fact player is neither held nor
brought by the load (build ruling Q4, P2 ruling 18: ``on_missing="skip"`` skips and counts it, and the facts that
nest it; review 01, R-03). The write also refuses a player that is not held, as a guard. Instants are int64 with the
±2^62 guard (ruling 4).

**Writes.** Each write is one TypeDB write transaction; the table reads through it. Versions are buffered and
written before the next read or at commit, entities first and every fact after the facts it binds. New instances
are inserted in batches: ``BATCH`` entities per ``insert``, and ``BATCH`` facts per query as a pipeline of one
``match``–``insert`` per fact, each stage guarded by the count of the one before, so that a fact whose players are
missing fails the whole batch instead of vanishing. A new version of a held instance is rewritten in place (one to
six queries). A load reads the ids it brings, and the types of the players they bind, in one query per ``CHUNK``
ids (``prefetch``; none on an empty store).

**Reads** run in one read transaction per call. Ids are selected in TypeQL with every filter, the injective match
of ``find`` (one binding per role and value identity, so the match is exact), ``after`` and ``limit``, grouped by id
(``reduce … groupby``: ``distinct`` keeps duplicates across disjunction branches in 3.13.6); counts are
``reduce``. The records of one call are fetched in one query per ``CHUNK`` ids and rebuilt by ``rows.record_of``
from the header attributes and ``khg-bindings``. ``trips`` counts every query, and the open and commit of each
transaction.
"""
from __future__ import annotations

import atexit
import contextlib
import itertools
import json
import os
import time
from typing import Any, Iterable, Iterator, Mapping, Sequence

from khg_contracts import jsonio
from khg_contracts.errors import KHGError, ValidationError
from khg_contracts.record import identity_key
from khg_contracts.schema import LIFECYCLE_RELATIONS
from khg_contracts.store import ALL_FLAGS, Where
from khg_contracts.store.base import as_schema
from khg_contracts.store.table import Entry, TableStore, bound_nodes

from .native import NativeReads
from .rows import Pat, binding_rows, fact_row, query_instant, record_of, value_from_identity
from .shared import AdapterMixin, Trips

__all__ = ["BATCH", "CHUNK", "FLAGS", "TypeDBStore", "TypeDBTable", "TypeQLSchema", "factory", "label"]

#: Ids per disjunction when a read or a prefetch names them.
CHUNK = 100
#: New instances per insert query (a pipeline of three stages per fact stays under TypeDB's 1,000 stages).
BATCH = 200

FLAGS = ALL_FLAGS - {"ordered_roles", "special_values", "goals", "transaction_time", "history_export"}
_seq = itertools.count(1)
_drivers: dict[tuple[str, str], Any] = {}
_UNSET: Any = object()

HEADER_ATTRS = [("khg-id", "string"), ("khg-status", "string"), ("khg-rank", "string"), ("khg-visibility", "string"),
                ("khg-rel-kind", "string"), ("khg-status-ref", "string"), ("khg-key-digest", "string"),
                ("khg-s-lo", "integer"), ("khg-s-hi", "integer"), ("khg-e-lo", "integer"), ("khg-e-hi", "integer"),
                ("khg-n-bindings", "integer"), ("khg-payload", "string"), ("khg-bindings", "string"),
                ("khg-version", "integer"), ("khg-tx", "integer"), ("khg-recorded-at", "string"),
                ("khg-recorded-by", "string")]
META_ATTRS = [("khg-record", "string"), ("khg-latest", "integer"), ("khg-header", "string"),
              ("khg-documents", "string")]
#: The fact attributes a new version replaces, and the row column each holds.
FACT_ATTRS = {"khg-status": "status", "khg-rank": "rank", "khg-visibility": "visibility",
              "khg-rel-kind": "rel_kind", "khg-status-ref": "status_ref", "khg-key-digest": "key_digest",
              "khg-s-lo": "s_lo", "khg-s-hi": "s_hi", "khg-e-lo": "e_lo", "khg-e-hi": "e_hi",
              "khg-n-bindings": "n_bindings", "khg-payload": "payload", "khg-version": "version",
              "khg-tx": "tx_from", "khg-recorded-at": "recorded_at", "khg-recorded-by": "recorded_by"}
MANIFEST = ("bid", "role", "position", "direction", "value_kind", "ref", "value_json", "extensions")


#: Seconds between a store's close and the deletion of its database.
GRACE = 5.0
_graveyard: list[tuple[float, Any, str]] = []


def _bury(everything: bool = False) -> None:
    """Delete the databases of closed stores that were closed ``GRACE`` seconds ago (all of them at exit)."""
    now = time.monotonic()
    keep = []
    for closed, drv, name in _graveyard:
        if everything or now - closed >= GRACE:
            with contextlib.suppress(Exception):
                if drv.databases.contains(name):
                    drv.databases.get(name).delete()
        else:
            keep.append((closed, drv, name))
    _graveyard[:] = keep


@atexit.register
def _bury_at_exit() -> None:
    if _graveyard:
        time.sleep(max(0.0, GRACE - (time.monotonic() - max(c for c, _, _ in _graveyard))))
        _bury(everything=True)


def label(prefix: str, name: str) -> str:
    """An injective TypeQL label: ``prefix`` plus ``name`` with every character outside [A-Za-z0-9_] as -<hex>-."""
    return prefix + "".join(c if (c.isascii() and (c.isalnum() or c == "_")) else f"-{ord(c):x}-" for c in name)


def q(text: str) -> str:
    """A TypeQL string literal."""
    return json.dumps(text, ensure_ascii=False)


def _driver(address: str, username: str, password: str) -> Any:
    from typedb.driver import Credentials, DriverOptions, DriverTlsConfig, TypeDB

    key = (address, username)
    if key not in _drivers:
        _drivers[key] = TypeDB.driver(address, Credentials(username, password),
                                      DriverOptions(DriverTlsConfig.disabled()))
    return _drivers[key]


class TypeQLSchema:
    """The TypeQL schema of a relation-type schema (the mapping of the module docstring)."""

    def __init__(self, schema: Any):
        self.schema = schema
        self.entity = {t: label("ent-", t) for t in schema.entity_types}
        self.relations = list(schema.relation_ids()) + [r for r in LIFECYCLE_RELATIONS
                                                        if r not in schema.relation_ids()]
        self.relation = {r: label("rel-", r) for r in self.relations}
        self.players: dict[str, set[str]] = {}   # relation -> roles with entity or fact fillers
        self.literals: dict[str, set[str]] = {}  # relation -> roles with literal fillers
        self.roles_by_name: dict[str, list[str]] = {}
        self.unmapped: dict[str, str] = {}  # relations with no TypeQL form, and why
        parent = {t: (ps[0] if ps else None) for t, ps in schema.entity_types.items()}

        def chain(t: str) -> set[str]:
            out, x = set(), t
            while x is not None and x not in out:
                out.add(x)
                x = parent.get(x)
            return out

        attrs = {name: kind for name, kind in HEADER_ATTRS + META_ATTRS}
        rel_lines, plays = [], set()
        for rel in self.relations:
            usages = schema.usages(rel) if rel not in LIFECYCLE_RELATIONS else LIFECYCLE_RELATIONS[rel]["roles"]
            parts = [f"relation {self.relation[rel]}, sub khg-fact"]
            for u in usages:
                role = self.role(u["role"])
                kinds = {next(iter(f)) for f in u["fillers"]}
                if kinds & {"entity", "fact"}:
                    parts.append(f"relates {role} @card(0..)")
                    self.players.setdefault(rel, set()).add(u["role"])
                    self.roles_by_name.setdefault(u["role"], []).append(rel)
                if "literal" in kinds:
                    attr = self.lit(u["role"])
                    attrs[attr] = "string"
                    parts.append(f"owns {attr} @card(0..)")
                    self.literals.setdefault(rel, set()).add(u["role"])
                for f in u["fillers"]:
                    if "entity" in f:
                        allowed = f["entity"] or [None]
                        for t in allowed:
                            if t is None:
                                plays.add(f"khg-entity plays {self.relation[rel]}:{role}")
                                continue
                            plays.add(f"{self.entity[t]} plays {self.relation[rel]}:{role}")
                            for sub in schema.entity_types:
                                if sub != t and schema.is_subtype(sub, t) and t not in chain(sub):
                                    plays.add(f"{self.entity[sub]} plays {self.relation[rel]}:{role}")
                    if "fact" in f:
                        for r in f["fact"] or [None]:
                            player = "khg-fact" if r is None else self.relation[r]
                            plays.add(f"{player} plays {self.relation[rel]}:{role}")
            if rel not in self.players:
                # no entity or fact role: TypeDB refuses a relation type that relates no role (SVL41), and would
                # delete an instance without players at commit anyway
                self.unmapped[rel] = "the relation has no entity or fact role (SVL41)"
                del self.relation[rel]
                self.literals.pop(rel, None)
                continue
            rel_lines.append("  " + ", ".join(parts) + ";")
        self.relation_of = {v: k for k, v in self.relation.items()}
        lines = ["define"]
        lines += [f"  attribute {a}, value {k};" for a, k in sorted(attrs.items())]
        lines.append("  entity khg-entity @abstract, owns khg-id @key, owns khg-record, owns khg-version, "
                     "owns khg-tx, owns khg-recorded-at, owns khg-recorded-by;")
        owned = ", ".join(f"owns {a}{' @key' if a == 'khg-id' else ''}" for a, _ in HEADER_ATTRS)
        lines.append(f"  relation khg-fact @abstract, {owned};")
        lines.append("  entity khg-meta, owns khg-latest, owns khg-header, owns khg-documents;")
        for t in schema.entity_types:
            p = parent[t]
            lines.append(f"  entity {self.entity[t]}, sub {self.entity[p] if p else 'khg-entity'};")
        lines += rel_lines
        lines += [f"  {p};" for p in sorted(plays)]
        self.text = "\n".join(lines)

    @staticmethod
    def role(name: str) -> str:
        return label("role-", name)

    @staticmethod
    def lit(name: str) -> str:
        return label("lit-", name)


def _chunks(items: Sequence[Any], size: int) -> Iterator[list[Any]]:
    for i in range(0, len(items), size):
        yield list(items[i:i + size])


def _any_of(blocks: Sequence[str]) -> str:
    """A TypeQL disjunction of pattern blocks (one block needs no ``or``)."""
    return " or ".join("{ " + b + " }" for b in blocks) + ";"


class TypeDBTable:
    """The version table over the database: one version per id (the current one)."""

    def __init__(self, schema: Any, store: TypeDBStore):
        self.schema = schema
        self.store = store
        self.tq: TypeQLSchema = store.tq
        self.tx: Any = None
        self.bulk_empty = False  # set by the store: a load began on an empty store
        self.incoming: dict[str, str] | None = None  # during a load: the ids it brings, and their kinds
        self._latest: Any = _UNSET
        self._latest_dirty = False
        self._cache: dict[str, Entry | None] = {}
        self._buf: list[tuple[dict[str, Any], int, dict[str, Any] | None]] = []
        self._types: dict[str, str | None] = {}  # id -> the TypeDB type label of its instance (None: not held)

    def query(self, text: str) -> Any:
        if self._buf:
            self.flush()
        return self.store.query(text, self.tx)

    def reset(self) -> None:
        self.tx = None
        self.bulk_empty = False
        self.incoming = None
        self._latest = _UNSET
        self._latest_dirty = False
        self._cache.clear()
        self._buf.clear()
        self._types.clear()

    def is_empty(self) -> bool:
        """Whether the store holds no instance (one query)."""
        return not self.query("match { $x isa khg-entity; } or { $x isa khg-fact; }; limit 1;")

    # -- latest
    @property
    def latest(self) -> int | None:
        if self._latest is _UNSET:
            rows = self.store.query("match $m isa khg-meta; try { $m has khg-latest $l; }; select $l;", self.tx)
            self._latest = rows[0]["l"] if rows else None
        return self._latest

    @latest.setter
    def latest(self, t: int | None) -> None:
        self._latest = t
        self._latest_dirty = True  # written by flush

    # -- ids
    def __contains__(self, rid: object) -> bool:
        return isinstance(rid, str) and self.entry_at(rid) is not None

    def __len__(self) -> int:
        rows = self.query("match $x has khg-id $i; select $i;")
        return len(rows)

    def ids(self) -> list[str]:
        return sorted(r["i"] for r in self.query("match $x has khg-id $i; select $i;"))

    # -- prefetch (the optional member; TableStore.load calls it)
    def prefetch(self, records: Iterable[Mapping[str, Any]]) -> None:
        """Read the ids a load brings, and the types of the entities and facts they bind that it does not bring:
        two queries per ``CHUNK`` ids, none on an empty store. ``cannot_hold`` then knows what the load brings
        (``incoming``)."""
        incoming: dict[str, str] = {} if self.incoming is None else self.incoming
        refs: set[str] = set()
        for r in records:
            incoming[jsonio.nfc(r["id"])] = r.get("kind")
            if r.get("kind") == "hyperedge":
                refs |= {jsonio.nfc(target) for _, _, target in bound_nodes(r)}
        self.incoming = incoming
        ids = sorted(set(incoming) - set(self._cache))
        others = sorted(refs - set(incoming) - set(self._types))
        if self.bulk_empty:
            self._cache.update(dict.fromkeys(ids))
            self._types.update(dict.fromkeys(others))
            return
        if self._buf:
            self.flush()
        got = self.store.fetch(ids, self.tx)
        for rid in ids:
            if rid in got:
                record, t, ty = got[rid]
                self._cache[rid] = Entry(record, t, self.schema)
                self._types[rid] = ty
            else:
                self._cache[rid] = None
        found = self.store.types_of(others, self.tx)
        for ref in others:
            self._types[ref] = found.get(ref)

    # -- versions
    def entry_at(self, rid: str, as_at: int | None = None) -> Entry | None:
        if not isinstance(rid, str):
            return None
        if rid not in self._cache:  # a buffered version is in the cache; any other is read as written so far
            got = self.store.fetch([rid], self.tx).get(rid)
            self._cache[rid] = None if got is None else Entry(got[0], got[1], self.schema)
            if got is not None:
                self._types[rid] = got[2]
        e = self._cache[rid]
        return None if e is None or (as_at is not None and e.t > as_at) else e

    def entries(self, rid: str) -> list[Entry]:
        e = self.entry_at(rid)
        return [] if e is None else [e]

    def current(self, rid: str) -> dict[str, Any] | None:
        e = self.entry_at(rid)
        return None if e is None else e.record

    def latest_version(self, rid: str) -> int:
        e = self.entry_at(rid)
        return 0 if e is None else int(e.record.get("version", 1))

    def add(self, record: dict[str, Any], t: int) -> Entry:
        rid = record["id"]
        old = self.current(rid)
        latest = self.latest
        self._buf.append((record, t, old))
        e = Entry(record, t, self.schema)
        self._cache[rid] = e
        self._latest = t if latest is None else max(latest, t)
        self._latest_dirty = True
        return e

    def type_of(self, rid: str) -> str | None:
        """The type label of the instance ``rid`` (None when it is not held)."""
        if rid not in self._types:
            self._types[rid] = self.store.types_of([rid], self.tx).get(rid)
        return self._types[rid]

    def flush(self) -> None:
        """Write the buffered versions: entities, then facts after the facts they bind; new instances in batches;
        then the latest time."""
        buf, self._buf = self._buf, []
        if buf:
            pending = {r["id"]: (r, t, old) for r, t, old in buf}
            for rid, (r, _, _) in pending.items():
                self._types[rid] = self.tq.entity[r["types"][0]] if r["kind"] == "entity" else \
                    self.tq.relation[r["relation"]]
            levels = [[rid for rid, (r, _, _) in pending.items() if r["kind"] == "entity"]]
            facts = {rid: v for rid, v in pending.items() if v[0]["kind"] == "hyperedge"}
            done: set[str] = set()
            while facts:
                ready = sorted(rid for rid, (r, _, _) in facts.items()
                               if all(b["ref"] not in facts or b["ref"] == rid or b["ref"] in done
                                      for b in binding_rows(r) if b["value_kind"] == "fact"))
                if not ready:
                    raise ValueError(f"a nesting cycle among {sorted(facts)}")
                levels.append(ready)
                done |= set(ready)
                for rid in ready:
                    del facts[rid]
            for level in levels:
                new = [pending[rid] for rid in level if pending[rid][2] is None]
                for part in _chunks(new, BATCH):
                    self.store.insert_new(part, self.type_of, self.tx)
                held = [pending[rid] for rid in level if pending[rid][2] is not None]
                for part in _chunks(held, BATCH):
                    self.store.update_held(part, self.type_of, self.tx)
        if self._latest_dirty:
            if self._latest is not None:
                self.store.query(f"match $m isa khg-meta; update $m has khg-latest {int(self._latest)};", self.tx)
            self._latest_dirty = False

    # -- indexes (the current versions: the store keeps no other)
    def _ids(self, body: str) -> set[str]:
        return {r["id"] for r in self.query(f"match {body} $f has khg-id $id; select $id;")}

    def by_node(self, node: str) -> set[str]:
        return self._ids(f"$n has khg-id {q(node)}; $f isa khg-fact, links ($n);")

    def by_relation(self, relation: str) -> set[str]:
        if relation not in self.tq.relation:
            return set()
        return self._ids(f"$f isa {self.tq.relation[relation]};")

    def by_key(self, relation: str, digest: str) -> set[str]:
        if relation not in self.tq.relation:
            return set()
        return self._ids(f"$f isa {self.tq.relation[relation]}, has khg-key-digest {q(digest)};")

    def by_ref(self, lifecycle_id: str) -> set[str]:
        return self._ids(f"$f isa khg-fact, has khg-status-ref {q(lifecycle_id)};")

    def __iter__(self) -> Iterator[str]:
        return iter(self.ids())


class TypeDBStore(AdapterMixin, NativeReads, TableStore):
    """A C2 store in TypeDB (see the module docstring)."""

    FLAGS = FLAGS
    ENGINE = "TypeDB"
    KIND = "client-server"
    INT64 = True

    def __init__(self, schema: Any, *, address: str, username: str = "admin", password: str = "password",
                 database: str | None = None, clock: Any = None, capabilities: Iterable[str] | None = None,
                 store_id: str = "typedb"):
        from typedb.driver import TransactionType

        self.TT = TransactionType
        self.trips = Trips()
        self._rtx: Any = None
        self.driver = _driver(address, username, password)
        self._owned = database is None
        self.database = database or f"khg-{os.getpid()}-{next(_seq)}-{os.urandom(3).hex()}"
        self.tq = TypeQLSchema(as_schema(schema))
        fresh = not self.driver.databases.contains(self.database)
        if fresh:
            self.driver.databases.create(self.database)
            with self.driver.transaction(self.database, TransactionType.SCHEMA) as tx:
                tx.query(self.tq.text).resolve()
                tx.commit()
            self.query("insert $m isa khg-meta;", write=True)
        TableStore.__init__(self, schema, table=lambda s: TypeDBTable(s, self), clock=clock,
                            capabilities=self.FLAGS if capabilities is None else capabilities, store_id=store_id)
        if not fresh:
            self._read_header()

    def engine_version(self) -> str:
        with contextlib.suppress(Exception):
            v = str(self.driver.server_version())
            return v[len("TypeDB "):] if v.startswith("TypeDB ") else v
        return "?"

    # -- queries (every engine call goes through query, or the open and commit of a transaction)
    def query(self, text: str, tx: Any = None, *, write: bool = False) -> list[dict[str, Any]]:
        """Run one query in ``tx`` (else in the read transaction of the current read call, else in its own read, or
        write, transaction); concept rows as dicts of values, type labels and concepts, or fetched documents."""
        head = text.lstrip()[:6]
        self.trips.hit("write" if write or head == "insert" or any(
            w in text for w in (" insert ", " update ", " delete ")) else "read")
        if tx is None:
            tx = self._rtx
        if tx is None:
            kind = self.TT.WRITE if write else self.TT.READ
            self.trips.hit("tx")
            with self.driver.transaction(self.database, kind) as own:
                rows = self._rows(own.query(text).resolve())
                if write:
                    self.trips.hit("tx")
                    own.commit()
                return rows
        return self._rows(tx.query(text).resolve())

    @contextlib.contextmanager
    def _reading(self) -> Iterator[None]:
        """One read transaction for every query of one read call."""
        if self._rtx is not None or self._table.tx is not None:
            yield
            return
        self.trips.hit("tx")
        tx = self.driver.transaction(self.database, self.TT.READ)
        self._rtx = tx
        try:
            yield
        finally:
            self._rtx = None
            with contextlib.suppress(Exception):
                tx.close()

    @staticmethod
    def _rows(ans: Any) -> list[dict[str, Any]]:
        if ans.is_concept_documents():
            return list(ans.as_concept_documents())
        if not ans.is_concept_rows():
            return []
        out = []
        for row in ans.as_concept_rows():
            d: dict[str, Any] = {}
            for col in row.column_names():
                c = row.get(col)
                if c is None:
                    d[col] = None
                elif c.is_attribute():
                    d[col] = c.get_value()
                elif c.is_type():
                    d[col] = c.get_label()
                elif c.is_value():
                    d[col] = c.get()
                else:
                    d[col] = c
            out.append(d)
        return out

    # -- reading records (fetched documents, then rows.record_of)
    _FACT_FETCH = "fetch { \"type\": $t, " + ", ".join(f'"{a}": $f.{a}' for a, _ in HEADER_ATTRS) + " };"

    def _fact(self, d: Mapping[str, Any]) -> tuple[dict[str, Any], int, str]:
        label = d["type"]["label"]
        row = {"id": d["khg-id"], "relation": self.tq.relation_of[label], "status": d["khg-status"],
               "status_ref": d["khg-status-ref"], "rank": d["khg-rank"], "visibility": d["khg-visibility"],
               "payload": d["khg-payload"], "version": d["khg-version"], "recorded_at": d["khg-recorded-at"],
               "recorded_by": d["khg-recorded-by"]}
        return record_of(row, json.loads(d["khg-bindings"])), int(d["khg-tx"]), label

    @staticmethod
    def _entity(d: Mapping[str, Any]) -> tuple[dict[str, Any], int, str]:
        return record_of({"record": d["record"]}), int(d["tx"]), d["type"]["label"]

    _ENTITY_FETCH = "fetch { \"type\": $t, \"record\": $f.khg-record, \"tx\": $f.khg-tx };"

    def fetch(self, ids: Sequence[str], tx: Any = None) -> dict[str, tuple[dict[str, Any], int, str]]:
        """``{id: (record, transaction time, type label)}`` of the held ids among ``ids``: facts, then entities for
        the rest, one query each per ``CHUNK`` ids."""
        out: dict[str, tuple[dict[str, Any], int, str]] = {}
        for chunk in _chunks([i for i in ids if isinstance(i, str)], CHUNK):
            for d in self.query("match " + _any_of([f"$f isa khg-fact, has khg-id {q(i)};" for i in chunk])
                                + f" $f isa! $t; {self._FACT_FETCH}", tx):
                rec = self._fact(d)
                out[rec[0]["id"]] = rec
            rest = [i for i in chunk if i not in out]
            if rest:
                docs = self.query("match " + _any_of([f"$f isa khg-entity, has khg-id {q(i)};" for i in rest])
                                  + f" $f isa! $t; {self._ENTITY_FETCH}", tx)
                for d in docs:
                    rec = self._entity(d)
                    out[rec[0]["id"]] = rec
        return out

    def types_of(self, ids: Sequence[str], tx: Any = None) -> dict[str, str]:
        """``{id: type label}`` of the held instances among ``ids``: one query per ``CHUNK`` ids."""
        out: dict[str, str] = {}
        for chunk in _chunks([i for i in ids if isinstance(i, str)], CHUNK):
            for r in self.query("match " + _any_of([f"$x has khg-id {q(i)};" for i in chunk])
                                + " $x isa! $t; $x has khg-id $id; select $id, $t;", tx):
                out[r["id"]] = r["t"]
        return out

    # -- writing versions
    def _fact_values(self, record: Mapping[str, Any], t: int) -> tuple[dict[str, Any], list[dict[str, Any]],
                                                                        dict[str, str]]:
        row = fact_row(record, self.schema, t)
        brs = binding_rows(record)
        manifest = [{k: b[k] for k in MANIFEST if b[k] is not None} for b in brs]
        values: dict[str, str] = {}
        for attr, col in FACT_ATTRS.items():
            v = row[col]
            if v is not None:
                values[attr] = str(int(v)) if isinstance(v, int) else q(v)
        values["khg-bindings"] = q(jsonio.canonical(manifest))
        return row, brs, values

    def _players(self, rid: str, brs: Sequence[Mapping[str, Any]], type_of: Any,
                 prefix: str) -> tuple[list[str], list[tuple[str, str]], dict[str, str]]:
        """The match statements of a fact's players, its (role, ref) pairs and the variable of each ref
        (``$<prefix><n>``); a player that is not held is refused (a guard: ``cannot_hold`` refuses such a fact in a
        load first)."""
        players = [(b["role"], b["ref"]) for b in brs if b["value_kind"] in ("entity", "fact")]
        names = {ref: f"${prefix}{n}" for n, ref in enumerate(sorted({ref for _, ref in players}))}
        match = []
        for ref, name in names.items():
            ty = type_of(ref)
            if ty is None:
                raise ValidationError(f"{rid}: the player {ref} is not held; a TypeDB relation needs its players",
                                      info={"id": rid, "cannot_hold": {"reason": "player_not_held", "player": ref}})
            match.append(f"{name} isa {ty}, has khg-id {q(ref)};")
        return match, players, names

    def insert_new(self, part: Sequence[tuple[dict[str, Any], int, Any]], type_of: Any, tx: Any) -> None:
        """Insert new instances: entities in one ``insert``; facts in one pipeline of guarded ``match``–``insert``
        stages (the last stage's count is 1 exactly when every fact was written)."""
        entities = [(r, t) for r, t, _ in part if r["kind"] == "entity"]
        facts = [(r, t) for r, t, _ in part if r["kind"] != "entity"]
        if entities:
            stmts = []
            for i, (r, t) in enumerate(entities):
                values = [("khg-id", q(r["id"])), ("khg-record", q(jsonio.canonical(dict(r)))),
                          ("khg-version", str(int(r["version"]))), ("khg-tx", str(int(t))),
                          ("khg-recorded-at", q(r["recorded_at"])), ("khg-recorded-by", q(r["recorded_by"]))]
                stmts.append(f"$e{i} isa {self.tq.entity[r['types'][0]]}, "
                             + ", ".join(f"has {a} {v}" for a, v in values) + ";")
            if not self.query("insert " + " ".join(stmts), tx):
                raise RuntimeError(f"TypeDB wrote nothing for {entities[0][0]['id']} …")
        if not facts:
            return
        stages = []
        for i, (r, t) in enumerate(facts):
            rid, rel = r["id"], self.tq.relation[r["relation"]]
            _, brs, values = self._fact_values(r, t)
            match, players, names = self._players(rid, brs, type_of, f"p{i}_")
            links = ", ".join(f"{self.tq.role(role)}: {names[ref]}" for role, ref in players)
            lits = [f"has {self.tq.lit(b['role'])} {q(b['ident'])}" for b in brs if b["value_kind"] == "literal"]
            has = ", ".join([f"has khg-id {q(rid)}"] + [f"has {a} {v}" for a, v in values.items()] + lits)
            guard = f"$c{i - 1} == 1; " if i else ""
            stages.append(f"match {guard}{' '.join(match)} insert $f{i} isa {rel} ({links}), {has}; "
                          f"reduce $c{i} = count;")
        rows = self.query(" ".join(stages), tx)
        if not rows or rows[0].get(f"c{len(facts) - 1}") != 1:
            raise RuntimeError(f"TypeDB wrote nothing for one of {', '.join(r['id'] for r, _ in facts[:3])} …")

    def update_held(self, part: Sequence[tuple[dict[str, Any], int, Any]], type_of: Any, tx: Any) -> None:
        """New versions of held instances, rewritten in place: every attribute by one pipeline of guarded
        ``match``–``update`` stages; an attribute that became empty, and players and literals that changed, by
        ``delete`` and ``insert`` queries of their own (none when they did not change)."""
        stages, relink = [], []
        for i, (r, t, old) in enumerate(part):
            guard = f"$c{i - 1} == 1; " if i else ""
            if r["kind"] == "entity":
                values = [("khg-record", q(jsonio.canonical(dict(r)))), ("khg-version", str(int(r["version"]))),
                          ("khg-tx", str(int(t))), ("khg-recorded-at", q(r["recorded_at"])),
                          ("khg-recorded-by", q(r["recorded_by"]))]
                at = f"$u{i} isa khg-entity, has khg-id {q(r['id'])};"
            else:
                row, _, fact_values = self._fact_values(r, t)
                values = list(fact_values.items())
                rel = self.tq.relation[r["relation"]]
                at = f"$u{i} isa {rel}, has khg-id {q(r['id'])};"
                old_row = fact_row(old, self.schema, t) if old.get("kind") == "hyperedge" else {}
                for attr, col in FACT_ATTRS.items():
                    if row[col] is None and old_row.get(col) is not None:
                        self.query(f"match $f isa {rel}, has khg-id {q(r['id'])}; $f has {attr} $a; "
                                   "delete has $a of $f;", tx)
                relink.append((r, old))
            stages.append(f"match {guard}{at} update " + " ".join(f"$u{i} has {a} {v};" for a, v in values)
                          + f" reduce $c{i} = count;")
        rows = self.query(" ".join(stages), tx)
        if not rows or rows[0].get(f"c{len(part) - 1}") != 1:
            raise RuntimeError(f"TypeDB wrote nothing for one of {', '.join(r['id'] for r, _, _ in part[:3])} …")
        for r, old in relink:
            self._relink(r, old, type_of, tx)

    def _relink(self, record: Mapping[str, Any], old: Mapping[str, Any], type_of: Any, tx: Any) -> None:
        """The players and literals of a new version of a held fact, where they changed."""
        rid, rel = record["id"], self.tq.relation[record["relation"]]
        brs = binding_rows(record)
        players = sorted((b["role"], b["ref"]) for b in brs if b["value_kind"] in ("entity", "fact"))
        literals = sorted((b["role"], b["ident"]) for b in brs if b["value_kind"] == "literal")
        old_brs = binding_rows(old) if old.get("kind") == "hyperedge" else []
        old_players = sorted((b["role"], b["ref"]) for b in old_brs if b["value_kind"] in ("entity", "fact"))
        old_literals = sorted((b["role"], b["ident"]) for b in old_brs if b["value_kind"] == "literal")
        at = f"$f isa {rel}, has khg-id {q(rid)};"
        if players != old_players:
            match, _, var = self._players(rid, brs, type_of, "p")
            for role in sorted({r for r, _ in old_players}):
                self.query(f"match {at} $f links ({self.tq.role(role)}: $p); delete links ({self.tq.role(role)}: $p) "
                           "of $f;", tx)
            if players:
                links = ", ".join(f"{self.tq.role(role)}: {var[ref]}" for role, ref in players)
                self.query(f"match {at} {' '.join(match)} insert $f links ({links});", tx)
        if literals != old_literals:
            for role in sorted({r for r, _ in old_literals}):
                self.query(f"match {at} $f has {self.tq.lit(role)} $a; delete has $a of $f;", tx)
            if literals:
                lits = ", ".join(f"has {self.tq.lit(role)} {q(ident)}" for role, ident in literals)
                self.query(f"match {at} insert $f {lits};", tx)

    # -- what the natural mapping cannot hold
    def _cannot_hold(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        if record.get("kind") == "entity":
            types = record.get("types")
            if not isinstance(types, list) or len(types) != 1:
                return {"reason": "instance_type", "detail": "a TypeDB instance has exactly one type",
                        "types": types}
            if types[0] not in self.tq.entity:
                return {"reason": "undeclared_type", "types": types}
            held = self._table.current(record["id"]) if isinstance(record.get("id"), str) else None
            if held is not None and held.get("kind") == "entity" and held.get("types") != types:
                return {"reason": "type_change", "detail": "a TypeDB instance cannot change its type",
                        "from": held.get("types"), "to": types}
            return None
        if record.get("kind") != "hyperedge":
            return None
        rel = record.get("relation")
        if rel in self.tq.unmapped:
            return {"reason": "no_role_player", "relation": rel, "detail": self.tq.unmapped[rel]}
        if rel not in self.tq.relation:
            return {"reason": "undeclared_relation", "relation": rel}
        bindings = record.get("bindings") or []
        kinds = [next(iter(b["value"])) for b in bindings]
        if not any(k in ("entity", "fact") for k in kinds):
            return {"reason": "no_role_player",
                    "detail": "TypeDB deletes a relation without role players at commit"}
        seen: set[tuple[str, str]] = set()
        for b, k in zip(bindings, kinds):
            if k in ("special", "unbound"):
                return {"reason": "no_player_for_value", "value_kind": k}
            if "position" in b:
                return {"reason": "role_player_list", "detail": "role-player lists are not implemented (REP254)"}
            if k in ("entity", "fact") and b["role"] not in self.tq.players.get(rel, set()):
                return {"reason": "undeclared_role", "role": b["role"]}
            if k == "literal" and b["role"] not in self.tq.literals.get(rel, set()):
                return {"reason": "undeclared_literal_role", "role": b["role"]}
            try:
                pair = (b["role"], identity_key(b["value"]))
            except (KHGError, ValueError, TypeError, KeyError):
                return {"reason": "malformed_value", "role": b["role"]}
            if pair in seen:
                return {"reason": "repeated_value", "role": b["role"],
                        "detail": "a relation holds a role player, or an owned attribute, once per role"}
            seen.add(pair)
        return self._players_held(record)

    def _players_held(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        """In a load: the entity and fact players must be held, or brought by the load (build ruling Q4)."""
        table: TypeDBTable = self._table
        if table.incoming is None:
            return None  # put and apply: D002 has checked that every new value resolves
        for _, kind, ref in bound_nodes(record):
            brought = table.incoming.get(ref)
            if brought is not None:
                ok = brought == ("entity" if kind == "entity" else "hyperedge")
            else:
                ty = table.type_of(ref)
                ok = ty is not None and ty.startswith("ent-" if kind == "entity" else "rel-")
            if not ok:
                return {"reason": "player_not_held", "player": ref,
                        "detail": f"a TypeDB relation needs its players: {kind} {ref} is neither held nor loaded"}
        return None

    # -- transactions
    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        table: TypeDBTable = self._table
        self.trips.hit("tx")
        tx = self.driver.transaction(self.database, self.TT.WRITE)
        table.reset()
        table.tx = tx
        try:
            yield
            table.flush()
            self.trips.hit("tx")
            tx.commit()
        except BaseException:
            with contextlib.suppress(Exception):
                tx.close()
            raise
        finally:
            table.reset()

    def load(self, container: Any, **kwargs: Any) -> Any:
        """Trusted bulk import in one write transaction, over the prefetched ids; the header on ``khg-meta``."""
        with self.writing():
            table: TypeDBTable = self._table
            table.bulk_empty = table.is_empty()
            report = TableStore.load(self, container, **kwargs)
            table.flush()
            self.query(f"match $m isa khg-meta; update $m has khg-header {q(json.dumps(self.kept_header))}; "
                       f"$m has khg-documents {q(json.dumps(self.kept_documents))};", table.tx)
        return report

    def _read_header(self) -> None:
        docs = self.query("match $m isa khg-meta; fetch { \"h\": $m.khg-header, \"d\": $m.khg-documents };")
        if docs and docs[0]["h"] is not None:
            self.kept_header = json.loads(docs[0]["h"])
            self.kept_documents = json.loads(docs[0]["d"] or "[]")

    # -- query parts
    @staticmethod
    def _one_of(var: str, values: Any) -> str:
        vs = sorted(values)
        if not vs:
            return f"{var} == \"-none-\";"
        return " or ".join("{ " + f"{var} == {q(v)};" + " }" for v in vs) + ";"

    def _filters(self, where: Where, as_of: int | None) -> str:
        out = ["$f has khg-id $id, has khg-status $st, has khg-rank $rk, has khg-visibility $vis, "
               "has khg-rel-kind $kind;",
               self._one_of("$st", where.status), self._one_of("$rk", where.rank),
               self._one_of("$vis", where.visibility), self._one_of("$kind", where.kinds)]
        if as_of is not None:
            t = query_instant(as_of)
            lo, hi = ("khg-s-hi", "khg-e-lo") if where.valid_mode == "definite" else ("khg-s-lo", "khg-e-hi")
            out += [f"$f has {lo} $vlo, has {hi} $vhi;", f"$vlo <= {t};", f"$vhi > {t};"]
        return " ".join(out)

    def _match(self, body: str, where: Where, as_of: int | None, after: str | None) -> str:
        text = f"match {body} {self._filters(where, as_of)}"
        if after is not None:
            text += f" $id > {q(after)};"
        return text

    def _ids_where(self, body: str, where: Where, as_of: int | None, after: str | None,
                   limit: int | None) -> list[str]:
        """The ids, grouped (``distinct`` keeps duplicates across disjunction branches in TypeDB 3.13.6), sorted and
        limited in TypeQL."""
        text = self._match(body, where, as_of, after) + " reduce $grouped = count groupby $id; sort $id;"
        if limit is not None:
            text += f" limit {int(limit)};"
        return [r["id"] for r in self.query(text)]

    # -- native reads
    def _n_records(self, ids: Sequence[str], t: int | None) -> list[dict[str, Any]]:
        got = self.fetch(ids)
        return [got[i][0] for i in ids if i in got and (t is None or got[i][1] <= t)]

    def _n_scan(self, t: int | None, history: bool) -> list[dict[str, Any]]:
        got = [self._fact(d) for d in self.query(f"match $f isa khg-fact; $f isa! $t; {self._FACT_FETCH}")]
        got += [self._entity(d) for d in self.query(f"match $f isa khg-entity; $f isa! $t; {self._ENTITY_FETCH}")]
        return [r for r, tx, _ in sorted(got, key=lambda x: x[0]["id"]) if t is None or tx <= t]

    def _n_get(self, id: str, t: int | None, version: int | None) -> dict[str, Any] | None:
        if not isinstance(id, str):
            return None
        got = self.fetch([id]).get(id)
        if got is None or (version is not None and got[0].get("version") != version):
            return None
        return got[0] if t is None or got[1] <= t else None

    def _n_versions(self, id: str, t: int | None = None) -> list[dict[str, Any]]:
        got = self._n_get(id, t, None)
        return [] if got is None else [got]

    def _n_is_fact(self, id: str) -> bool:
        return bool(self.query(f"match $f isa khg-fact, has khg-id {q(id)}; select $f;"))

    def _incident_body(self, node: str, role: str | None, relation: str | None) -> str | None:
        body = f"$n has khg-id {q(node)}; $f isa khg-fact, links ($n);"
        if role is not None:
            rels = [r for r in self.tq.roles_by_name.get(role, []) if relation is None or r == relation]
            if not rels:
                return None
            body += " " + _any_of([f"$f isa {self.tq.relation[r]}, links ({self.tq.role(role)}: $n);" for r in rels])
        elif relation is not None:
            if relation not in self.tq.relation:
                return None
            body += f" $f isa {self.tq.relation[relation]};"
        return body

    def _n_incident(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                    as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        body = self._incident_body(node, role, relation)
        return [] if body is None else self._ids_where(body, where, as_of, after, limit)

    def _n_count(self, node: str, role: str | None, relation: str | None, where: Where, t: int | None,
                 as_of: int | None) -> int:
        body = self._incident_body(node, role, relation)
        if body is None:
            return 0
        rows = self.query(self._match(body, where, as_of, None)
                          + " reduce $grouped = count groupby $id; reduce $total = count;")
        return int(rows[0]["total"]) if rows else 0

    def _n_find(self, relation: str, pats: list[Pat], match: str, where: Where, t: int | None, as_of: int | None,
                after: str | None, limit: int | None) -> list[str]:
        """The injective match in TypeQL. A held fact has one binding per role and value identity
        (``cannot_hold``), so each role's values must be linked players or owned attributes, and each ``any`` in a
        role one more binding of that role: the branches split the ``any`` between players and literals."""
        rel = self.tq.relation.get(relation)
        if rel is None:
            return []
        players, literals = self.tq.players.get(relation, set()), self.tq.literals.get(relation, set())
        by_role: dict[str, dict[str, Any]] = {}
        for p in pats:
            if p.position is not None or p.kind == "any_unbound":
                return []  # ordered_roles and goals are absent: find refused these patterns before
            spec = by_role.setdefault(p.role, {"values": [], "any": 0})
            if p.kind == "any":
                spec["any"] += 1
            else:
                spec["values"].append(p.ident)
        body = [f"$f isa {rel};"]
        n = itertools.count()
        for role, spec in sorted(by_role.items()):
            values = spec["values"]
            if len(set(values)) != len(values):
                return []  # two bindings of one role with one value identity: never held (cannot_hold)
            pvars, lvals = [], []
            for ident in values:
                value = json.loads(ident)
                kind = next(iter(value))
                if kind in ("entity", "fact"):
                    if role not in players:
                        return []
                    v = f"$p{next(n)}"
                    body.append(f"$f links ({self.tq.role(role)}: {v}); {v} isa "
                                f"{'khg-entity' if kind == 'entity' else 'khg-fact'}, has khg-id {q(value[kind])};")
                    pvars.append(v)
                elif kind == "literal":
                    if role not in literals:
                        return []
                    body.append(f"$f has {self.tq.lit(role)} {q(ident)};")
                    lvals.append(ident)
                else:
                    return []  # a special value has no home here (special_values is absent)
            a = spec["any"]
            if a:
                branches = []
                for k in range(a + 1):  # k more players and a - k more literals of this role
                    if (k and role not in players) or (a - k and role not in literals):
                        continue
                    xs = [f"$x{next(n)}" for _ in range(k)]
                    ys = [f"$y{next(n)}" for _ in range(a - k)]
                    parts = []
                    for i, x in enumerate(xs):
                        parts.append(f"$f links ({self.tq.role(role)}: {x});")
                        parts += [f"not {{ {x} is {other}; }};" for other in pvars + xs[:i]]
                    for i, y in enumerate(ys):
                        parts.append(f"$f has {self.tq.lit(role)} {y};")
                        parts += [f"{y} != {q(v)};" for v in lvals] + [f"{y} != {other};" for other in ys[:i]]
                    branches.append(" ".join(parts))
                if not branches:
                    return []
                body.append(branches[0] if len(branches) == 1 else _any_of(branches))
        if match == "exact":
            body.append(f"$f has khg-n-bindings {len(pats)};")
        return self._ids_where(" ".join(body), where, as_of, after, limit)

    def _n_key(self, relation: str, digest: str, where: Where, t: int | None, as_of: int | None) -> list[str]:
        rel = self.tq.relation.get(relation)
        if rel is None:
            return []
        return self._ids_where(f"$f isa {rel}, has khg-key-digest {q(digest)};", where, as_of, None, None)

    def _n_bound_by(self, relation: str, role: str, idents: Sequence[str], where: Where, t: int | None,
                    as_of: int | None) -> dict[str, list[str]]:
        rel = self.tq.relation.get(relation)
        if rel is None or role not in self.tq.players.get(relation, set()):
            return {}
        by_kind: dict[str, dict[str, str]] = {"entity": {}, "fact": {}}
        for ident in idents:
            value = json.loads(ident)
            kind = next(iter(value))
            if kind in by_kind:
                by_kind[kind][value[kind]] = ident
        out: dict[str, list[str]] = {}
        for kind, by_ref in by_kind.items():
            for chunk in _chunks(sorted(by_ref), CHUNK):
                body = (f"$f isa {rel}, links ({self.tq.role(role)}: $p); "
                        + _any_of([f"$p has khg-id {q(r)};" for r in chunk])
                        + f" $p isa {'khg-fact' if kind == 'fact' else 'khg-entity'}, has khg-id $pid;")
                for r in self.query(self._match(body, where, as_of, None)
                                    + " reduce $grouped = count groupby $pid, $id; sort $id;"):
                    out.setdefault(by_ref[r["pid"]], []).append(r["id"])
        return out

    # -- fidelity number 2
    def native_bindings(self, rid: str) -> list[dict[str, Any]] | None:
        """The bindings of fact ``rid`` rebuilt from the native structure alone (role players and owned literal
        attributes, without ``khg-bindings``): role and value for a player; role, the stored identity and the
        value it determines (``rows.value_from_identity``) for a literal; no bid, position, direction or extensions.
        None when ``rid`` is not a held fact."""
        rows = self.query(f"match $f isa khg-fact, has khg-id {q(rid)}; $f isa! $t; select $t;")
        if not rows:
            return None
        rel = self.tq.relation_of[rows[0]["t"]]
        role_of = {self.tq.role(r): r for r in self.tq.players.get(rel, set())}
        out = []
        for r in self.query(f"match $f isa khg-fact, has khg-id {q(rid)}; $f links ($role: $p); "
                            "$p has khg-id $pid; $p isa! $pt; select $role, $pid, $pt;"):
            name = r["role"].split(":")[-1]
            kind = "fact" if r["pt"].startswith("rel-") else "entity"
            value = {kind: r["pid"]}
            out.append({"role": role_of.get(name, name), "value": value, "ident": identity_key(value)})
        lit_of = {self.tq.lit(r): r for r in self.tq.literals.get(rel, set())}
        for r in self.query(f"match $f isa khg-fact, has khg-id {q(rid)}, has $a; $a isa! $at; select $a, $at;"):
            if r["at"] in lit_of:
                b = {"role": lit_of[r["at"]], "ident": r["a"]}
                value = value_from_identity(r["a"])
                if value is not None:
                    b["value"] = value
                out.append(b)
        return out

    def close(self) -> None:
        """A fresh database is deleted later, not now: TypeDB CE 3.13.6 panicked (and stopped) once when a database
        was deleted right after a transaction on it closed ("Cannot get exclusive ownership of inner of
        Arc<QueryCache>", database.rs:527). ``_bury`` deletes it after ``GRACE`` seconds, or at exit."""
        if self._owned:
            _graveyard.append((time.monotonic(), self.driver, self.database))
            _bury()


def factory(address: str, username: str = "admin", password: str = "password") -> Any:
    """A conformance factory: a fresh ``TypeDBStore`` (its own database, deleted by ``close``) per call."""

    def make(schema: Any, clock: Any) -> TypeDBStore:
        return TypeDBStore(schema, address=address, username=username, password=password, clock=clock)

    return make
