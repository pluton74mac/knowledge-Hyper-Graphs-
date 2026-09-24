"""``StoreBase``: the six derived methods of C2, built on the nine core ones (DESIGN §6.1, §6.2).

A backend subclasses ``StoreBase``, calls ``StoreBase.__init__`` (schema, clock, capabilities, store id) and
implements ``info``, ``put``, ``apply``, ``load``, ``get``, ``history``, ``incident``, ``find`` and
``iter_records``. It then has:

- ``get_many(ids, as_at)``: ``get`` per id, in code-point id order, missing ids left out;
- ``degree(node, ...)``: ``len(incident(node, ...))``;
- ``find_by_key(relation, key, where)``: ``find`` with the key bindings as the pattern, keeping the facts whose
  key digest equals the key's (values compare by identity). ``ValueError`` when ``key`` does not bind exactly the
  key roles (critique CONS-25), or binds one to ``any``; a key with a special value names no key group, so [];
- ``supersession_walk(id, direction, as_at)``: breadth first over the asserted ``khg:supersedes`` records at
  ``as_at`` (found with ``find``); steps ``{depth, via, reason, from, to}`` and ``terminal``, the facts reached
  that have no outgoing asserted supersession, with their status. It branches on conflation and always ends;
- ``export(format, ...)``: from ``iter_records`` and the kept header (``store.export``);
- ``close()``: nothing to release.
"""
from __future__ import annotations

import abc
import re
from typing import Any, Collection, Iterable, Iterator, Literal, Mapping, Sequence

from ..errors import CapabilityMissing, KHGError
from ..record import key_digest
from ..record.lifecycle import RANKS, VISIBILITIES
from ..schema import Schema
from . import export as _export
from .clocks import SystemClock
from .flags import capabilities as _capabilities
from .protocol import Clock, LoadReport, Pattern, Receipt, Record, StoreInfo, Walk
from .where import DEFAULT_WHERE, Where

__all__ = ["StoreBase", "as_schema"]

_STORE_ID = re.compile(r"[^\s\x00-\x1f\x7f]{1,500}")
_SAFE = (KHGError, ValueError, TypeError, KeyError)


def as_schema(schema: Any) -> Schema:
    """A ``Schema`` from a ``Schema`` (as is), a schema document or a path (``load_schema``: J, V and M)."""
    from ..hif.encode import as_schema as _as_schema

    return _as_schema(schema)


class StoreBase(abc.ABC):
    """The derived half of the ``Store`` protocol, and what every backend shares: ``schema`` (a ``Schema``),
    ``clock`` (``SystemClock()`` by default), ``capabilities`` (every flag by default) and ``store_id``."""

    def __init__(self, schema: Any, *, clock: Clock | None = None, capabilities: Iterable[str] | None = None,
                 store_id: str = "store"):
        if not isinstance(store_id, str) or not _STORE_ID.fullmatch(store_id):
            raise ValueError(f"store_id is 1 to 500 characters without white space, not {store_id!r}")
        self.schema = as_schema(schema)
        self.clock = clock if clock is not None else SystemClock()
        self.capabilities = _capabilities(capabilities)
        self.store_id = store_id

    def need(self, flag: str) -> None:
        """Raise ``CapabilityMissing(flag)`` unless the store has ``flag``."""
        if flag not in self.capabilities:
            raise CapabilityMissing(flag, f"the store {self.store_id!r} lacks the capability {flag}")

    def __enter__(self) -> StoreBase:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------------------------------ core (abstract)

    @abc.abstractmethod
    def info(self) -> StoreInfo: ...

    @abc.abstractmethod
    def put(self, records: Record | Sequence[Record], *, actor: str, at: str | None = None,
            expect: Mapping[str, int] | None = None) -> Receipt: ...

    @abc.abstractmethod
    def apply(self, event: Mapping[str, Any], *, actor: str, at: str | None = None) -> Receipt: ...

    @abc.abstractmethod
    def load(self, container: Any, *, header: Mapping[str, Any] | None = None, at: str | None = None,
             on_missing: Literal["raise", "skip"] = "raise") -> LoadReport: ...

    @abc.abstractmethod
    def get(self, id: str, *, as_at: str | None = None, version: int | None = None) -> Record | None: ...

    @abc.abstractmethod
    def history(self, id: str) -> list[Record]: ...

    @abc.abstractmethod
    def incident(self, node: str, *, role: str | None = None, relation: str | None = None, where: Where = DEFAULT_WHERE,
                 limit: int | None = None, after: str | None = None) -> list[Record]: ...

    @abc.abstractmethod
    def find(self, relation: str, pattern: Sequence[Pattern], *, match: Literal["at_least", "exact"] = "at_least",
             where: Where = DEFAULT_WHERE, limit: int | None = None, after: str | None = None) -> list[Record]: ...

    @abc.abstractmethod
    def iter_records(self, *, content: Literal["snapshot", "history"] = "snapshot",
                     as_at: str | None = None) -> Iterator[Record]: ...

    # ------------------------------------------------------------------------------------------ derived

    def get_many(self, ids: Iterable[str], *, as_at: str | None = None) -> dict[str, Record]:
        """``{id: record}`` for the ids the store holds (at ``as_at``), in code-point id order."""
        if isinstance(ids, (str, bytes)):
            raise TypeError("ids is a collection of ids, not a string")
        out = {}
        for rid in dict.fromkeys(ids):
            r = self.get(rid, as_at=as_at)
            if r is not None:
                out[rid] = r
        return dict(sorted(out.items()))

    def degree(self, node: str, *, role: str | None = None, relation: str | None = None,
               where: Where = DEFAULT_WHERE) -> int:
        """The number of hyperedges ``incident`` returns."""
        return len(self.incident(node, role=role, relation=relation, where=where))

    def find_by_key(self, relation: str, key: Sequence[Pattern], *, where: Where = DEFAULT_WHERE) -> list[Record]:
        """The facts of ``relation`` on ``key`` (the key roles bound to values), in id order."""
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
        probe = {"kind": "hyperedge", "id": "_:key", "relation": relation, "status": "asserted",
                 "bindings": [{"bid": f"b{n}", "role": p["role"], "value": p["value"],
                               **({"position": p["position"]} if "position" in p else {})}
                              for n, p in enumerate(patterns, 1)]}
        digest = key_digest(probe, self.schema)
        if digest is None:
            return []
        out = []
        for r in self.find(relation, patterns, match="at_least", where=where):
            try:
                if key_digest(r, self.schema) == digest:
                    out.append(r)
            except _SAFE:
                continue
        return out

    def supersession_walk(self, id: str, *, direction: Literal["forward", "backward"] = "forward",
                          as_at: str | None = None) -> Walk:
        """The supersession chain from ``id``: forward to what superseded it, backward to what it superseded."""
        if direction not in ("forward", "backward"):
            raise ValueError(f"direction is forward or backward, not {direction!r}")
        frm, to = ("khg:superseded", "khg:superseding") if direction == "forward" else \
            ("khg:superseding", "khg:superseded")
        where = Where(status=frozenset({"asserted"}), rank=frozenset(RANKS), visibility=frozenset(VISIBILITIES),
                      kinds=frozenset({"lifecycle"}), as_at=as_at)
        outgoing: dict[str, list[Record]] = {}

        def edges(fact: str) -> list[Record]:
            if fact not in outgoing:
                outgoing[fact] = self.find("khg:supersedes", [{"role": frm, "value": {"fact": fact}}], where=where)
            return outgoing[fact]

        steps: list[dict[str, Any]] = []
        seen, reached, frontier, depth = {id}, [id], [id], 0
        while frontier:
            depth += 1
            following: list[str] = []
            for fact in frontier:
                for s in edges(fact):
                    for b in s.get("bindings", []):
                        value = b.get("value") if isinstance(b, Mapping) else None
                        target = value.get("fact") if isinstance(value, Mapping) else None
                        if b.get("role") != to or not isinstance(target, str):
                            continue
                        steps.append({"depth": depth, "via": s.get("id"), "reason": s.get("reason"), "from": fact,
                                      "to": target})
                        if target not in seen:
                            seen.add(target)
                            reached.append(target)
                            following.append(target)
            frontier = sorted(following)
        terminal = []
        for fact in sorted(reached):
            if not edges(fact):
                r = self.get(fact, as_at=as_at)
                terminal.append({"id": fact, "status": r.get("status") if r is not None else None})
        return {"start": id, "direction": direction, "steps": steps, "terminal": terminal}

    def export(self, format: Literal["khg-json", "khg-jsonl", "hif"] = "khg-jsonl", *,
               content: Literal["snapshot", "history"] = "snapshot", as_at: str | None = None,
               relations: Collection[str] | None = None, header: Mapping[str, Any] | None = None,
               literal_nodes: Literal["shared", "per_binding"] = "shared") -> str | dict[str, Any]:
        """The store as ``khg-json`` (a dict), ``khg-jsonl`` (text) or ``hif`` (a dict), every status included."""
        if format not in _export.FORMATS:
            raise ValueError(f"format is one of {', '.join(_export.FORMATS)}, not {format!r}")
        if content not in _export.CONTENTS:
            raise ValueError(f"content is snapshot or history, not {content!r}")
        if literal_nodes not in _export.LITERAL_NODES:
            raise ValueError(f"literal_nodes is shared or per_binding, not {literal_nodes!r}")
        if format == "hif" and content == "history":
            raise ValueError("HIF holds one version per id: export history as khg-json or khg-jsonl")
        rels = _export.check_relations(relations, self.schema)
        records = list(self.iter_records(content=content, as_at=as_at))
        info = self.info()
        kept = header if header is not None else info.get("header")
        hdr = _export.export_header(kept, records, schema=self.schema, store_id=info["store_id"], content=content,
                                    as_at=as_at)
        return _export.render({"header": hdr, "records": records}, format, self.schema, relations=rels,
                              literal_nodes=literal_nodes)

    def close(self) -> None:  # noqa: B027 - a derived method with nothing to release by default
        """Release the store's resources (nothing to do here)."""
