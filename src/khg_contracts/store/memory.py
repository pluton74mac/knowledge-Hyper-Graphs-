"""``MemoryStore``: the reference C2 store (DESIGN §6.3), and ``memory_factory`` for the conformance suite;
``TableStore``: the same store over any version table (ruling 17, published by ``store.table``).

``TableStore`` holds its versions in a version table (``store.table.VersionTableProtocol``): a version list per id
and the indexes node -> facts, relation -> facts, (relation, key digest) -> facts and ``status_ref``. Its write path
and its reads use the table only. ``transaction()`` wraps each write (``put``, ``apply``, ``load``) in one backend
transaction, and ``cannot_hold(record)`` names the records a backend cannot hold; neither does anything by default.
The kept header and documents are public (``kept_header``, ``kept_documents``) and are restored when a write fails;
``load`` calls the table's optional ``prefetch(records)`` before its checks read the loaded ids.
``MemoryStore`` is ``TableStore`` over the in-memory ``VersionTable``. With ``capabilities=None`` a store has every
flag; a set of flags limits it (the capability-limited runs): a call that needs a missing flag raises
``CapabilityMissing``.

- **put** is all or nothing (§6.2): a new id becomes version 1 in status asserted, quoted or goal (candidate is
  D017, other statuses and lifecycle records D014); content equal to the current version is a no-op; anything else
  is a new version under the version rule (D013), and a status change is D014. ``expect {id: version}`` gives
  optimistic concurrency (D019). The checks then follow ``_writes``.
- **load** is trusted bulk import: a container, or an iterable whose first item is the header (``header=`` when it
  has none), or a path. It keeps the store fields and checks only V001 and D018; ``on_missing="skip"`` skips the
  records that need a missing flag and those that reference skipped ones. It keeps the header, minus ``content``
  and ``as_at``, and any embedded relation-schema records, which ``iter_records`` and ``export`` give back.
- **Reads** return copies, in code-point id order, with ``limit``/``after`` keyset pagination; ``get`` ignores
  ``Where``; ``incident(node)`` returns each hyperedge that binds the node (an entity or a fact) once.
- **A record the backend cannot hold** (``cannot_hold`` is not None) is refused by ``put`` and ``apply`` after every
  other check, and by ``load`` like a record that needs a missing flag (``on_missing="skip"`` skips it and the
  records that reference it), with a ``ValidationError`` that has no code and ``info["cannot_hold"]``.
"""
from __future__ import annotations

import contextlib
import copy
import itertools
import os
import time
from typing import Any, Callable, Iterable, Iterator, Literal, Mapping, Sequence

from .. import CONTRACTS, jsonio
from ..errors import CapabilityMissing, ConcurrencyError, ValidationError, VersionError
from ..record import (carried_supports, identity_key, injective_match, iter_jsonl, lifecycle, normalize,
                      read_container)
from ..record._structure import version_findings
from ..schema import LIFECYCLE_RELATIONS
from ._events import EventsMixin
from ._table import Entry, VersionTable, bound_nodes
from ._writes import Pending, fail
from .base import StoreBase
from .clocks import format_timestamp, parse_timestamp
from .export import CONTENTS
from .flags import data_flags, pattern_flags, where_flags
from .protocol import (INTERFACE_VERSION, RECORD_FORMAT, Clock, LoadReport, Pattern, Receipt, Record, StoreInfo)
from .where import DEFAULT_WHERE, Where

__all__ = ["MemoryStore", "TableStore", "memory_factory"]

_ANY = object()


def _same(current: Mapping[str, Any], incoming: Mapping[str, Any]) -> bool:
    """Equal content: canonical JSON without the store fields."""
    a = {k: v for k, v in current.items() if k not in ("version", "recorded_at", "recorded_by")}
    try:
        return jsonio.canonical(a) == jsonio.canonical(incoming)
    except (TypeError, ValueError):
        return False


def _page(limit: Any, after: Any) -> None:
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError(f"limit is None or a non-negative integer, not {limit!r}")
    if after is not None and not isinstance(after, str):
        raise TypeError(f"after is None or an id, not {type(after).__name__}")


class TableStore(EventsMixin, StoreBase):
    """Every C2 method over a version table, with capability flags for the limited runs (ruling 17).

    ``table`` is a function of the store's ``Schema`` that returns the version table (``store.table``); None gives
    the in-memory ``VersionTable``. A backend subclass overrides ``transaction()`` to make each write one backend
    transaction, ``cannot_hold(record)`` to refuse what it cannot hold, and any read with a native query.
    """

    def __init__(self, schema: Any, *, table: Callable[[Any], Any] | None = None, clock: Clock | None = None,
                 capabilities: Iterable[str] | None = None, store_id: str = "store"):
        super().__init__(schema, clock=clock, capabilities=capabilities, store_id=store_id)
        self._table = VersionTable(self.schema) if table is None else table(self.schema)
        self._header: dict[str, Any] | None = None
        self._documents: list[dict[str, Any]] = []
        self._writing = 0

    def __repr__(self) -> str:
        return (f"{type(self).__name__}({self.schema.ref!r}, store_id={self.store_id!r}, ids={len(self._table)}, "
                f"capabilities={len(self.capabilities)} of 10)")

    @property
    def table(self) -> Any:
        """The version table."""
        return self._table

    # ------------------------------------------------------------------------------------------ backend hooks

    def transaction(self) -> contextlib.AbstractContextManager[Any]:
        """The context of one write (``put``, ``apply`` or ``load``): a backend begins its transaction on entry,
        commits it when the block ends and rolls it back when the block raises. The default does nothing: the
        in-memory table is written only after every check has passed."""
        return contextlib.nullcontext()

    @contextlib.contextmanager
    def writing(self) -> Iterator[None]:
        """``transaction()`` around a block, re-entrant: only the outermost block opens one, so a subclass can add
        its own work (a header row, say) to the transaction of ``put``, ``apply`` or ``load``. When the outermost
        block raises, the kept header and documents are restored as they were before it (the backend rolls back
        its table); the clock is not rolled back."""
        if self._writing:
            yield
            return
        self._writing += 1
        state = (self._header, self._documents)
        try:
            with self.transaction():
                yield
        except BaseException:
            self._header, self._documents = state
            raise
        finally:
            self._writing -= 1

    # ------------------------------------------------------------------------------------------ header state

    @property
    def kept_header(self) -> dict[str, Any] | None:
        """The header ``load`` kept (the container's, without ``content`` and ``as_at``), as a copy; None before
        any load. A backend persists it with its data and sets it when it reopens a store."""
        return copy.deepcopy(self._header)

    @kept_header.setter
    def kept_header(self, header: Mapping[str, Any] | None) -> None:
        if header is not None and not isinstance(header, Mapping):
            raise TypeError(f"the kept header is a mapping or None, not {type(header).__name__}")
        self._header = None if header is None else copy.deepcopy(dict(header))

    @property
    def kept_documents(self) -> list[dict[str, Any]]:
        """The embedded relation-schema records ``load`` kept, as copies ([] when none)."""
        return copy.deepcopy(self._documents)

    @kept_documents.setter
    def kept_documents(self, documents: Sequence[Mapping[str, Any]]) -> None:
        if isinstance(documents, (str, bytes, Mapping)) or not isinstance(documents, Sequence) or \
                not all(isinstance(d, Mapping) for d in documents):
            raise TypeError("the kept documents are a sequence of mappings")
        self._documents = [copy.deepcopy(dict(d)) for d in documents]

    def cannot_hold(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        """None when the backend can hold ``record`` (a record in canonical form, which may lack its store
        fields); else what it cannot hold, as a dict (``{"reason": ..., ...}``) that becomes
        ``info["cannot_hold"]`` of the refusal. The default holds everything."""
        return None

    def _refusal(self, rid: Any, why: Mapping[str, Any]) -> ValidationError:
        return ValidationError(f"{rid}: the store {self.store_id!r} cannot hold this record ({why.get('reason')})",
                               info={"id": rid, "cannot_hold": dict(why)})

    def _check_held(self, pending: Pending) -> None:
        for r in pending.records():
            why = self.cannot_hold(r)
            if why is not None:
                raise self._refusal(r["id"], why)

    def info(self) -> StoreInfo:
        return {"interface_version": INTERFACE_VERSION, "record_format": RECORD_FORMAT,
                "capabilities": self.capabilities, "store_id": self.store_id,
                "header": copy.deepcopy(self._header), "contracts": dict(CONTRACTS)}

    # ------------------------------------------------------------------------------------------ put

    def put(self, records: Record | Sequence[Record], *, actor: str, at: str | None = None,
            expect: Mapping[str, int] | None = None) -> Receipt:
        """Write one record or a batch, all or nothing (§6.2), in one ``transaction()``."""
        with self.writing():
            return self._put(records, actor=actor, at=at, expect=expect)

    def apply(self, event: Mapping[str, Any], *, actor: str, at: str | None = None) -> Receipt:
        """Apply one event atomically (``_events``), in one ``transaction()``."""
        with self.writing():
            return super().apply(event, actor=actor, at=at)

    def _put(self, records: Record | Sequence[Record], *, actor: str, at: str | None,
             expect: Mapping[str, int] | None) -> Receipt:
        actor = self._actor(actor)
        when = self._at(at)
        if isinstance(records, (str, bytes)):
            raise TypeError("records is a record or a sequence of records, not a string")
        batch = [records] if isinstance(records, Mapping) else list(records)
        if len(batch) > 1:
            self.need("atomic_writes")
        self._need_data(batch)
        if expect:
            self._expect(expect)
        incoming = [self._incoming(self._carried(r), f"/records/{i}") for i, r in enumerate(batch)]
        seen: set[str] = set()
        for rec in incoming:
            if rec["id"] in seen:
                raise fail("KHG-D001", f"{rec['id']} is written twice by one call", "/id")
            seen.add(rec["id"])
        pending, noops, problems = Pending(self._table), [], []
        for rec in incoming:
            current = self._table.current(rec["id"])
            problem = lifecycle.put_problem(rec, current if current and current.get("kind") == "hyperedge" else None)
            if problem is not None:
                problems.append(problem)
            elif current is not None and current.get("kind") == rec["kind"] and _same(current, rec):
                noops.append((rec["id"], current["version"], "noop"))
            else:
                pending.add(rec)
        if problems:
            raise lifecycle.error_for(problems)
        if not pending:
            return {"records": sorted(noops), "at": self.clock.now(), "warnings": []}
        self._validate(pending)
        self._check_versions([(cur, rec) for rec in pending.records()
                              if (cur := self._table.current(rec["id"])) is not None])
        self._check_references(pending)
        return self._commit(pending, actor=actor, at=when, noops=noops, disputed_rule=True)

    def _carried(self, record: Any) -> Any:
        """``record`` with ``supports`` written out on the evidence it carries over from the stored version without
        it: such evidence keeps what it supported where it was first written (§2.8.1), not every bid of the new
        version."""
        rid = record.get("id") if isinstance(record, Mapping) else None
        current = self._table.current(jsonio.nfc(rid)) if isinstance(rid, str) else None
        if current is None or current.get("kind") != "hyperedge":
            return record
        return carried_supports([current, record])[1]

    def _expect(self, expect: Mapping[str, int]) -> None:
        if not isinstance(expect, Mapping):
            raise TypeError("expect maps ids to the versions the caller read")
        found = {rid: self._table.latest_version(rid) for rid in expect}
        stale = sorted(rid for rid, v in expect.items() if found[rid] != v)
        if stale:
            raise ConcurrencyError(f"KHG-D019: {', '.join(stale)} changed since it was read (expected "
                                   f"{', '.join(f'{r} at {expect[r]}' for r in stale)})", codes=["KHG-D019"],
                                   info={"expected": dict(expect), "found": found, "stale": stale})

    # ------------------------------------------------------------------------------------------ load

    def load(self, container: Any, *, header: Mapping[str, Any] | None = None, at: str | None = None,
             on_missing: Literal["raise", "skip"] = "raise") -> LoadReport:
        """Trusted bulk import (§6.2): V001 and D018 (and C010 or C002 for what it cannot index); see the module
        docstring. One ``transaction()``."""
        with self.writing():
            return self._load(container, header=header, at=at, on_missing=on_missing)

    def _load(self, container: Any, *, header: Mapping[str, Any] | None, at: str | None,
              on_missing: str) -> LoadReport:
        started = time.perf_counter()
        if on_missing not in ("raise", "skip"):
            raise ValueError(f"on_missing is raise or skip, not {on_missing!r}")
        when = self._at(at)
        head, rows = self._split(container, header)
        v001 = version_findings({"header": head})
        if v001:
            raise ValidationError.from_findings(v001)
        content = head.get("content", "snapshot")
        if content not in CONTENTS:
            raise fail("KHG-C002", f"header content is snapshot or history, not {content!r}", "/header/content")
        if content == "history":
            self.need("history_export")
        default = self._write_time(when)
        documents, raw = [], []
        for i, r in enumerate(rows):
            if isinstance(r, Mapping) and r.get("kind") == "relation-schema":
                documents.append(copy.deepcopy(dict(r)))
                continue
            if not isinstance(r, Mapping) or r.get("kind") not in ("entity", "hyperedge") or not isinstance(
                    r.get("id"), str):
                raise fail("KHG-C010", "a loaded record is an entity or a hyperedge with a string id",
                           f"/records/{i}")
            if r["kind"] == "hyperedge" and not isinstance(r.get("relation"), str):
                raise fail("KHG-C010", f"{r['id']}: a loaded hyperedge has a string relation",
                           f"/records/{i}/relation")
            raw.append(r)
        prefetch = getattr(self._table, "prefetch", None)
        if prefetch is not None:  # an optional member: the table may read these ids in bulk (store.table)
            prefetch(raw)
        staged = [normalize(r) for r in self._carry_loaded(raw)]
        skipped = self._missing(staged, on_missing)
        kept = [r for r in staged if r["id"] not in skipped]
        timed = self._versions(kept, default, head.get("as_at") if content == "history" else None)
        latest = default
        for r, t in timed:
            self._table.add(r, t)
            latest = max(latest, t)
        self._table.latest = latest if self._table.latest is None else max(self._table.latest, latest)
        self._header = {k: copy.deepcopy(v) for k, v in head.items() if k not in ("content", "as_at")}
        if documents:
            self._documents = documents
        self._advance_clock(latest)
        return {"records": len({r["id"] for r in kept}), "versions": len(kept), "skipped": sorted(skipped),
                "seconds": time.perf_counter() - started}

    def _carry_loaded(self, records: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        """The loaded records, in their order, with ``supports`` written out on evidence that a later version of an
        id carries without it (§2.8.1): the versions of each hyperedge id in the order ``_versions`` gives them
        (numbered ones by number, then the others), after the version the store holds."""
        out = list(records)
        groups: dict[str, list[int]] = {}
        for i, r in enumerate(out):
            if r.get("kind") == "hyperedge":
                groups.setdefault(jsonio.nfc(r["id"]), []).append(i)
        for rid, idx in groups.items():
            current = self._table.current(rid)
            held = [current] if current is not None and current.get("kind") == "hyperedge" else []
            if len(idx) + len(held) < 2:
                continue
            idx = sorted(idx, key=lambda i: (0, out[i]["version"] if type(out[i]["version"]) is int else 0)
                         if "version" in out[i] else (1, 0))
            carried = carried_supports(held + [out[i] for i in idx])[len(held):]
            for i, r in zip(idx, carried, strict=True):
                out[i] = r
        return out

    @staticmethod
    def _split(container: Any, header: Mapping[str, Any] | None) -> tuple[Mapping[str, Any], Iterator[Any]]:
        """(header, records) of a container, a stream whose first item may be the header, or a path."""
        if isinstance(container, (str, os.PathLike)):
            container = iter_jsonl(container) if os.fspath(container).endswith(".jsonl") else \
                read_container(container)
        if isinstance(container, (bytes, bytearray)):
            raise TypeError("load takes a container, an iterable of records or a path, not bytes")
        if isinstance(container, Mapping):
            records = container.get("records")
            if not isinstance(records, list):
                raise fail("KHG-C010", "a container is {header, records}", "/records")
            head, rows = (header if header is not None else container.get("header")), iter(records)
        else:
            rows = iter(container)
            first = next(rows, None)
            if isinstance(first, Mapping) and first.get("kind") == "header":
                head = header if header is not None else first
            else:
                head = header  # type: ignore[assignment]
                rows = rows if first is None else itertools.chain([first], rows)
        if not isinstance(head, Mapping):
            raise fail("KHG-V001", "no header: a stream without a header line needs header=", "/header")
        return head, rows

    def _missing(self, staged: list[dict[str, Any]], on_missing: str) -> set[str]:
        """The ids to skip: those whose records need a missing flag or that the backend cannot hold, then those
        that reference them."""
        drop: set[str] = set()
        for r in staged:
            missing = sorted(data_flags(r) - self.capabilities)
            if missing and on_missing == "raise":
                raise CapabilityMissing(missing[0], f"{r['id']} needs {', '.join(missing)}", info={"id": r["id"]})
            if missing:
                drop.add(r["id"])
                continue
            why = self.cannot_hold(r)
            if why is not None and on_missing == "raise":
                raise self._refusal(r["id"], why)
            if why is not None:
                drop.add(r["id"])
        changed = bool(drop)
        while changed:
            changed = False
            for r in staged:
                if r["id"] in drop or r.get("kind") != "hyperedge":
                    continue
                refs = {target for _, _, target in bound_nodes(r)}
                if isinstance(r.get("status_ref"), str):
                    refs.add(r["status_ref"])
                if refs & drop:
                    drop.add(r["id"])
                    changed = True
        return drop

    def _versions(self, records: list[dict[str, Any]], default: int, as_at: Any) -> list[tuple[dict[str, Any], int]]:
        """Each loaded version with its transaction time: kept store fields, else ``default``; D018 when a version is
        not after the store's latest, not after the previous version of its id, or after a history's ``as_at``."""
        base = self._table.latest
        limit = parse_timestamp(as_at) if as_at is not None else None
        by_id: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            by_id.setdefault(r["id"], []).append(r)
        out = []
        for rid, versions in by_id.items():
            numbered = sorted((r for r in versions if "version" in r),
                              key=lambda r: r["version"] if type(r["version"]) is int else 0)
            prev_v = self._table.latest_version(rid)
            entries = self._table.entries(rid)
            prev_t = entries[-1].t if entries else None
            for r in numbered + [r for r in versions if "version" not in r]:
                v = r.get("version", prev_v + 1)
                if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                    raise fail("KHG-C010", f"{rid}: version is a positive integer", "/version")
                t = parse_timestamp(r["recorded_at"]) if "recorded_at" in r else default
                problem = None
                if v <= prev_v:
                    problem = f"version {v} of {rid} is not after version {prev_v}"
                elif base is not None and t <= base:
                    problem = f"{rid} version {v} is recorded at {format_timestamp(t)}, not after the store's latest"
                elif prev_t is not None and t <= prev_t:
                    problem = f"{rid} version {v} is not recorded after the previous version of its id"
                elif limit is not None and t > limit:
                    problem = f"{rid} version {v} is recorded after the header's as_at {as_at}"
                if problem:
                    raise VersionError(f"KHG-D018: {problem}", codes=["KHG-D018"], info={"id": rid, "version": v})
                r["version"] = v
                r.setdefault("recorded_at", format_timestamp(t))
                r.setdefault("recorded_by", "load")
                prev_v, prev_t = v, t
                out.append((r, t))
        return out

    # ------------------------------------------------------------------------------------------ reads

    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> Record | None:
        """The latest version of ``id`` (at ``as_at``), or ``version``; None when absent. ``Where`` does not
        apply."""
        if as_at is not None or version is not None:
            self.need("transaction_time")
        t = self._at(as_at)
        if version is not None:
            e = next((x for x in self._table.entries(id) if x.record.get("version") == version), None)
            return copy.deepcopy(e.record) if e is not None and (t is None or e.t <= t) else None
        e = self._table.entry_at(id, t)
        return copy.deepcopy(e.record) if e is not None else None

    def history(self, id: str) -> list[Record]:
        """Every version of ``id``, oldest first ([] when absent)."""
        return [copy.deepcopy(e.record) for e in self._table.entries(id)]

    def _need_where(self, where: Where) -> Where:
        where = Where.of(where)
        for flag in sorted(where_flags(where)):
            self.need(flag)
        return where

    @staticmethod
    def _passes(e: Entry, where: Where, as_of: int | None) -> bool:
        r = e.record
        axes = (r.get("status"), r.get("rank", "normal"), r.get("visibility", "visible"), r.get("relation"))
        if r.get("kind") != "hyperedge" or not all(isinstance(x, str) for x in axes):
            return False  # a malformed record that a trusted load kept passes no filter (as _table reads it)
        status, rank, visibility, relation = axes
        if status not in where.status or rank not in where.rank or visibility not in where.visibility:
            return False
        if ("lifecycle" if relation in LIFECYCLE_RELATIONS else "fact") not in where.kinds:
            return False
        if as_of is None:
            return True
        b = e.bounds
        return b is not None and b.holds_at(as_of, where.valid_mode)

    def _select(self, ids: Iterable[str], where: Where, *, after: str | None) -> Iterator[Entry]:
        t, as_of = where.as_at_micros, where.as_of_seconds
        for rid in sorted(ids):
            if after is not None and rid <= after:
                continue
            e = self._table.entry_at(rid, t)
            if e is not None and self._passes(e, where, as_of):
                yield e

    def incident(self, node: str, *, role: str | None = None, relation: str | None = None, where: Where = DEFAULT_WHERE,
                 limit: int | None = None, after: str | None = None) -> list[Record]:
        """The hyperedges that bind ``node`` (an entity or a fact id) as a value, once each; literals and
        vocabulary ids are not nodes."""
        _page(limit, after)
        where = self._need_where(where)
        if relation is not None:
            self.schema.relation(relation)
        held = self._table.current(node) if isinstance(node, str) else None
        if held is not None and held.get("kind") == "hyperedge":
            self.need("nesting")
        out: list[Record] = []
        if limit == 0:
            return out
        for e in self._select(self._table.by_node(node), where, after=after):
            r = e.record
            if relation is not None and r.get("relation") != relation:
                continue
            bindings = r.get("bindings") or []
            if any(target == node and (role is None or bindings[j].get("role") == role)
                   for j, _, target in bound_nodes(r)):
                out.append(r)
                if limit is not None and len(out) >= limit:
                    break
        return copy.deepcopy(out)

    @staticmethod
    def _patterns(pattern: Any) -> list[tuple[str, Any, str, str | None]]:
        """(role, position or _ANY, kind, identity key) per pattern; ``ValueError`` on a malformed one."""
        if isinstance(pattern, (str, bytes, Mapping)) or not isinstance(pattern, Sequence):
            raise TypeError("pattern is a sequence of {role, value, position?}")
        out: list[tuple[str, Any, str, str | None]] = []
        for p in pattern:
            if not isinstance(p, Mapping) or not isinstance(p.get("role"), str) or "value" not in p or \
                    set(p) - {"role", "value", "position"}:
                raise ValueError(f"a pattern is {{role, value, position?}}, not {p!r}")
            position = p.get("position", _ANY)
            if position is not _ANY and (isinstance(position, bool) or not isinstance(position, int) or position < 1):
                raise ValueError(f"a pattern position is a positive integer, not {position!r}")
            value = p["value"]
            if value == {"any": True}:
                out.append((p["role"], position, "any", None))
            elif value == {"any_unbound": True}:
                out.append((p["role"], position, "any_unbound", None))
            else:
                out.append((p["role"], position, "value", identity_key(value)))
        return out

    @staticmethod
    def _matches(prepared: list[tuple[str, Any, str, str | None]], e: Entry, match: str) -> bool:
        bindings = e.record.get("bindings") or []
        if match == "exact" and len(prepared) != len(bindings):
            return False
        idents = e.idents

        def ok(i: int, j: int) -> bool:
            role, position, kind, ident = prepared[i]
            b = bindings[j]
            if b.get("role") != role or (position is not _ANY and b.get("position") != position):
                return False
            unbound = isinstance(b.get("value"), Mapping) and "unbound" in b["value"]
            if kind == "any":
                return True
            if kind == "any_unbound":
                return unbound
            return not unbound and idents[j] is not None and idents[j] == ident

        return injective_match(len(prepared), len(bindings), ok)

    def find(self, relation: str, pattern: Sequence[Pattern], *, match: Literal["at_least", "exact"] = "at_least",
             where: Where = DEFAULT_WHERE, limit: int | None = None, after: str | None = None) -> list[Record]:
        """The facts of ``relation`` whose bindings match ``pattern`` (``at_least``: an injective match of the
        pattern's (role, position, value) multiset; ``exact``: equal multisets)."""
        _page(limit, after)
        if match not in ("at_least", "exact"):
            raise ValueError(f"match is at_least or exact, not {match!r}")
        self.schema.relation(relation)
        prepared = self._patterns(pattern)
        pattern = list(pattern)
        where = self._need_where(where)
        for flag in sorted(pattern_flags(pattern, lifecycle=relation in LIFECYCLE_RELATIONS)):
            self.need(flag)
        candidates = set(self._table.by_relation(relation))
        for p in pattern:
            value = p["value"]
            for kind in ("entity", "fact"):
                if isinstance(value, Mapping) and len(value) == 1 and isinstance(value.get(kind), str):
                    candidates &= self._table.by_node(value[kind])
        out: list[Record] = []
        if limit == 0:
            return out
        for e in self._select(candidates, where, after=after):
            if e.record.get("relation") == relation and self._matches(prepared, e, match):
                out.append(e.record)
                if limit is not None and len(out) >= limit:
                    break
        return copy.deepcopy(out)

    def iter_records(self, *, content: Literal["snapshot", "history"] = "snapshot",
                     as_at: str | None = None) -> Iterator[Record]:
        """Every record of every status: the latest version of each id (at ``as_at``), or every version
        (``history``), in id order; embedded relation-schema records that ``load`` kept come first."""
        if content not in CONTENTS:
            raise ValueError(f"content is snapshot or history, not {content!r}")
        if content == "history":
            self.need("history_export")
        if as_at is not None:
            self.need("transaction_time")
        return self._records(content, self._at(as_at))

    def _records(self, content: str, t: int | None) -> Iterator[Record]:
        for doc in self._documents:
            yield copy.deepcopy(doc)
        for rid in self._table.ids():
            if content == "history":
                for e in self._table.entries(rid):
                    if t is None or e.t <= t:
                        yield copy.deepcopy(e.record)
            else:
                e = self._table.entry_at(rid, t)
                if e is not None:
                    yield copy.deepcopy(e.record)


class MemoryStore(TableStore):
    """The reference store: ``TableStore`` over the in-memory ``VersionTable``."""

    def __init__(self, schema: Any, *, clock: Clock | None = None, capabilities: Iterable[str] | None = None,
                 store_id: str = "memory"):
        super().__init__(schema, clock=clock, capabilities=capabilities, store_id=store_id)


def memory_factory(schema: Any, clock: Clock) -> MemoryStore:
    """``MemoryStore(schema, clock=clock)``: the factory that ``conformance.run``, ``queue.replay`` and
    ``khg-conformance --factory khg_contracts.store:memory_factory`` take for the reference store."""
    return MemoryStore(schema, clock=clock)
