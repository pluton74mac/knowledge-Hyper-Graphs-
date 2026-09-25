"""The measured object H(S, sigma) and how a schema file becomes it (DESIGN §2).

- ``read_schema(src)`` reads a ``.json`` file (``load_schema``: layers J, V, M), a ``.json.gz`` file (gunzip, then
  ``jsonio.loads``, then ``load_schema(mapping)``), a mapping or a ``Schema``. It returns the ``Schema`` and the file's
  identity (path, ``file_sha256``). An invalid document raises ``SchemaInvalid`` carrying every finding.
- ``check_slots(slots)`` refuses ``meta`` and a slot set without ``core`` (``UsageError``).
- ``hypergraph(schema, slots=...)`` is ``Hypergraph`` over ``schema_hypergraph(S, slots=sigma)``: vertices are global
  role ids, one named edge per relation (lifecycle relations and relations with no usage in sigma left out).
- ``Hypergraph`` is a *named multi-hypergraph*: Berge is computed on it; alpha, beta, gamma and the widths use its set
  hypergraph (``.distinct()``, the first relation name of each role set in schema order).
- ``Hypergraph.neutral`` gives solver-safe ids (``R<i>`` relations, ``V<j>`` roles) and the HyperBench text.
"""
from __future__ import annotations

import gzip
import hashlib
import os
import zlib
from collections import Counter
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Iterable, Mapping, Sequence

__all__ = ["Hypergraph", "Neutral", "SchemaInvalid", "SchemaSource", "UsageError", "check_slots", "hypergraph",
           "read_schema", "HEADLINE_SLOTS"]

HEADLINE_SLOTS = ("core", "qualifier")
_ALLOWED_SLOTS = ("core", "qualifier", "time")


class UsageError(ValueError):
    """A usage error of the checker (exit 2): bad slots, a bad limit, a missing requested solver."""


class SchemaInvalid(ValueError):
    """The schema document fails layers J, V or M (exit 1). ``findings`` holds every finding."""

    def __init__(self, message: str, findings: Sequence[Mapping[str, Any]]):
        super().__init__(message)
        self.findings = [dict(f) for f in findings]


@dataclass(frozen=True)
class SchemaSource:
    """Where a schema came from: ``path`` and ``file_sha256`` (the hash of the file's bytes) for a file."""

    path: str | None = None
    file_sha256: str | None = None
    compressed: bool = False


def check_slots(slots: Sequence[str] | str) -> tuple[str, ...]:
    """The slot set as a tuple; ``UsageError`` for ``meta``, an unknown slot or a set without ``core``."""
    if isinstance(slots, str):
        slots = tuple(s.strip() for s in slots.split(",") if s.strip())
    out = tuple(dict.fromkeys(slots))
    if "meta" in out:
        raise UsageError("the meta slot is refused: meta bindings (khg:end_cause, P2241, P7452) never enter H")
    bad = [s for s in out if s not in _ALLOWED_SLOTS]
    if bad:
        raise UsageError(f"unknown slot(s) {', '.join(bad)}; choose from core, qualifier, time")
    if "core" not in out:
        raise UsageError("the slot set must contain core")
    return tuple(s for s in _ALLOWED_SLOTS if s in out)


def read_schema(src: Any) -> tuple[Any, SchemaSource]:
    """``(Schema, SchemaSource)`` for a path (``.json`` or ``.json.gz``), a mapping or a ``Schema``.

    Raises ``SchemaInvalid`` (with every finding) for an invalid document and ``OSError`` when the file cannot be
    read (a truncated or corrupt gzip stream is an ``OSError`` too)."""
    from khg_contracts import jsonio
    from khg_contracts.errors import ValidationError
    from khg_contracts.schema import Schema, load_schema

    if isinstance(src, Schema):
        return src, SchemaSource()
    if isinstance(src, Mapping):
        try:
            return load_schema(src), SchemaSource()
        except ValidationError as e:
            raise SchemaInvalid(str(e), e.info.get("findings", [])) from None
    path = os.fspath(src)
    with open(path, "rb") as fh:
        raw = fh.read()
    digest = hashlib.sha256(raw).hexdigest()
    compressed = path.endswith(".gz")
    try:
        if compressed:
            try:
                text = gzip.decompress(raw)
            except (EOFError, zlib.error, gzip.BadGzipFile) as e:
                raise OSError(f"{path}: not a readable gzip file ({e})") from None
            doc = jsonio.loads(text)
            schema = load_schema(doc)
        else:
            schema = load_schema(path)
    except ValidationError as e:
        raise SchemaInvalid(str(e), e.info.get("findings", [])) from None
    return schema, SchemaSource(path=path, file_sha256=digest, compressed=compressed)


@dataclass(frozen=True)
class Neutral:
    """Solver-safe ids: relations ``R<i>`` in edge order, roles ``V<j>`` in sorted order, and the HyperBench text."""

    relations: dict[str, str]
    roles: dict[str, str]
    text: str

    @cached_property
    def relation_names(self) -> dict[str, str]:
        return {v: k for k, v in self.relations.items()}

    @cached_property
    def role_names(self) -> dict[str, str]:
        return {v: k for k, v in self.roles.items()}


@dataclass(frozen=True)
class Hypergraph:
    """A named multi-hypergraph: ``edges`` is a tuple of ``(relation, frozenset(roles))`` in schema order.

    Empty edges are dropped on construction. ``distinct()`` is the set hypergraph (first name per role set);
    ``induced(X)`` is H[X] = {e & X} with empty traces dropped and names kept."""

    edges: tuple[tuple[str, frozenset], ...] = ()
    _index: dict = field(default=None, repr=False, compare=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        cleaned = tuple((str(n), frozenset(map(str, e))) for n, e in self.edges if e)
        names = [n for n, _ in cleaned]
        if len(set(names)) != len(names):
            raise ValueError("relation names must be unique")
        object.__setattr__(self, "edges", cleaned)
        object.__setattr__(self, "_index", dict(cleaned))

    # ---------------------------------------------------------------- construction
    @classmethod
    def from_mapping(cls, m: Mapping[str, Iterable[str]]) -> Hypergraph:
        if "hyperedges" in m and isinstance(m["hyperedges"], Mapping):
            m = m["hyperedges"]
        return cls(tuple((k, frozenset(v)) for k, v in m.items()))

    # ---------------------------------------------------------------- views
    @property
    def names(self) -> tuple[str, ...]:
        return tuple(n for n, _ in self.edges)

    @cached_property
    def vertices(self) -> tuple[str, ...]:
        return tuple(sorted({v for _, e in self.edges for v in e}))

    def edge(self, name: str) -> frozenset:
        return self._index[name]

    def __contains__(self, name: object) -> bool:
        return name in self._index

    def __len__(self) -> int:
        return len(self.edges)

    def is_empty(self) -> bool:
        return not self.edges

    def as_dict(self) -> dict[str, list[str]]:
        return {n: sorted(e) for n, e in self.edges}

    def distinct(self) -> Hypergraph:
        """The set hypergraph: one edge per distinct role set, named after its first relation in schema order."""
        seen: dict[frozenset, str] = {}
        for n, e in self.edges:
            seen.setdefault(e, n)
        if len(seen) == len(self.edges):
            return self
        return Hypergraph(tuple((n, e) for e, n in seen.items()))

    @cached_property
    def duplicate_groups(self) -> list[list[str]]:
        """Relations with the same role set, groups of two or more, in schema order."""
        groups: dict[frozenset, list[str]] = {}
        for n, e in self.edges:
            groups.setdefault(e, []).append(n)
        return [g for g in groups.values() if len(g) > 1]

    def induced(self, keep: Iterable[str]) -> Hypergraph:
        ks = frozenset(keep)
        return Hypergraph(tuple((n, e & ks) for n, e in self.edges if e & ks))

    @cached_property
    def universal_roles(self) -> tuple[str, ...]:
        """Roles in every relation (only when there are two relations or more), sorted."""
        if len(self.edges) < 2:
            return ()
        common = frozenset.intersection(*(e for _, e in self.edges))
        return tuple(sorted(common))

    # ---------------------------------------------------------------- statistics
    @cached_property
    def stats(self) -> dict[str, Any]:
        """Counts, rank, maximum degree and BIP (both without universal roles), duplicate groups, components and the
        universal roles (DESIGN §2.2 step 3)."""
        uni = set(self.universal_roles)
        deg: dict[str, int] = {}
        for _, e in self.edges:
            for v in e:
                deg[v] = deg.get(v, 0) + 1
        dset = self.distinct()
        # BIP: the largest intersection of two distinct edges, universal roles left out. Per edge, count the other
        # edges through the stars of its roles (Counter.update runs in C); memory stays O(edges).
        bip = 0
        star: dict[str, list[int]] = {}
        dedges = [e - uni for _, e in dset.edges]
        for i, e in enumerate(dedges):
            for v in e:
                star.setdefault(v, []).append(i)
        for i, e in enumerate(dedges):
            if len(e) <= bip:
                continue
            c: Counter = Counter()
            for v in e:
                s = star[v]
                if len(s) > 1:
                    c.update(s)
            c.pop(i, None)
            if c:
                bip = max(bip, max(c.values()))
        return {
            "relations": len(self.edges),
            "distinct_role_sets": len(dset.edges),
            "roles": len(deg),
            "incidences": sum(len(e) for _, e in self.edges),
            "rank": max((len(e) for _, e in self.edges), default=0),
            "max_degree": max((d for v, d in deg.items() if v not in uni), default=0),
            "bip": bip,
            "duplicate_groups": self.duplicate_groups,
            "universal_roles": list(self.universal_roles),
            "components": self.components(),
            "components_without_universal": self.components(ignore=uni),
        }

    def components(self, ignore: Iterable[str] = ()) -> int:
        """Connected components (over shared roles), counting a relation left with no role as its own component."""
        skip = set(ignore)
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            root = x
            while parent[root] != root:
                root = parent[root]
            while parent[x] != root:
                parent[x], x = root, parent[x]
            return root

        roots = 0
        isolated = 0
        for _, e in self.edges:
            vs = [v for v in e if v not in skip]
            if not vs:
                isolated += 1
                continue
            for v in vs:
                if v not in parent:
                    parent[v] = v
                    roots += 1
            a = find(vs[0])
            for v in vs[1:]:
                b = find(v)
                if a != b:
                    parent[b] = a
                    roots -= 1
        return roots + isolated

    # ---------------------------------------------------------------- solver ids
    @cached_property
    def neutral(self) -> Neutral:
        rels = {n: f"R{i}" for i, (n, _) in enumerate(self.edges)}
        roles = {v: f"V{j}" for j, v in enumerate(self.vertices)}
        lines = [f"{rels[n]} ({', '.join(roles[v] for v in sorted(e))})" for n, e in self.edges]
        text = "% khg-width: neutral ids (R<i> relations, V<j> roles)\n" + ",\n".join(lines) + ".\n"
        return Neutral(relations=rels, roles=roles, text=text)


def hypergraph(schema: Any, *, slots: Sequence[str] = HEADLINE_SLOTS) -> Hypergraph:
    """H(S, sigma) for a schema (path, mapping or ``Schema``) and a slot set (``meta`` refused, ``core`` required)."""
    from khg_contracts.schema import schema_hypergraph

    sl = check_slots(slots)
    s, _ = read_schema(schema)
    hg = schema_hypergraph(s, slots=sl)
    return Hypergraph.from_mapping(hg["hyperedges"])
