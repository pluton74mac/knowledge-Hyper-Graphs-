"""``Bundle``: a library object together with the context of the HIF file it came from (DESIGN §5).

- ``graph`` is an ``xgi.Hypergraph``, an ``xgi.DiHypergraph`` or a ``hypernetx.Hypergraph``, built with public
  constructors only; edit it with the library's own operations.
- ``records(edge, node=None)`` gives the full incidence records the bundle carries for live memberships, in record
  order, and ``roles(edge, node)`` their roles (``['regulator', 'target']`` for ``ex:TP53`` in ``f:reg-1``).
- ``derive(graph)`` wraps a copy or restriction of the graph (``copy()``, ``clone()``, ``restrict_to_*()``,
  ``subhypergraph()``) with this bundle's context.
- ``label(edge, node, *, role, ...)`` gives a new membership its record; a strict export refuses a membership
  without one.
- ``report`` is the ``ExportReport`` of the last export, or None.
"""
from __future__ import annotations

import copy
import importlib
from types import ModuleType
from typing import Any, Mapping

from ..errors import LoaderError, make_finding
from ._common import LIBRARIES, library_of
from ._input import bid_ok
from .context import Context
from .report import ExportReport

__all__ = ["Bundle", "make_record"]


def _backend(lib: str) -> ModuleType:
    return importlib.import_module(f"{__package__}.{lib}")


def _refuse(code: str, path: str, message: str) -> LoaderError:
    return LoaderError(f"{code}: {message}", codes=[code], info={"findings": [make_finding(code, path, message)]})


def _position_key(value: Any) -> Any:
    """A ``role-position`` as layer R's R002 key reads it: None when absent, an integral float as its integer (F10),
    and a malformed value as itself."""
    from ..hif.convention import role_position
    if value is None:
        return None
    p = role_position(value)
    return p if p is not None else ("invalid", repr(value))


def make_record(edge: Any, node: Any, *, role: Any, bid: Any = None, direction: Any = None, position: Any = None,
                weight: Any = None, extensions: Any = None, profile: bool = False) -> dict[str, Any]:
    """The incidence record ``label`` adds. Raises ``LoaderError``: P005 for a role that is not a non-empty string,
    or (in a profile file) a missing or malformed ``khg-bid``; H005 for a direction other than head or tail; R004 for
    a ``role-position`` that is not an integer >= 1 (an integral float such as ``4.0`` is that integer, as layer R
    reads it, and is written as the integer); H009 for a weight that is not a number or extensions that are not an
    object."""
    from ..hif.convention import role_position
    if not isinstance(role, str) or not role:
        raise _refuse("KHG-P005", "/attrs/role", "a label needs a role: one non-empty string")
    if profile and not bid_ok(bid):
        raise _refuse("KHG-P005", "/attrs/khg-bid", f"a label in a khg-hif file needs a khg-bid like 'b4', not {bid!r}")
    if direction not in (None, "head", "tail"):
        raise _refuse("KHG-H005", "/direction", f"direction is head or tail, not {direction!r}")
    if position is not None:
        read = role_position(position)
        if read is None:
            raise _refuse("KHG-R004", "/attrs/role-position", f"role-position is an integer >= 1, not {position!r}")
        position = read
    if weight is not None and (not isinstance(weight, (int, float)) or isinstance(weight, bool)):
        raise _refuse("KHG-H009", "/weight", f"weight is a number, not {weight!r}")
    if extensions is not None and not isinstance(extensions, Mapping):
        raise _refuse("KHG-H009", "/attrs/khg-extensions", "extensions is an object")
    attrs: dict[str, Any] = {"role": role}
    if bid is not None:
        attrs["khg-bid"] = bid
    if position is not None:
        attrs["role-position"] = position
    if extensions:
        attrs["khg-extensions"] = copy.deepcopy(dict(extensions))
    record: dict[str, Any] = {"edge": edge, "node": node}
    if direction is not None:
        record["direction"] = direction
    if weight is not None:
        record["weight"] = weight
    record["attrs"] = attrs
    return record


class Bundle:
    """A library object, its loader ``Context`` and the report of its last export (DESIGN §5)."""

    def __init__(self, graph: Any, context: Context, lib: str):
        if lib not in LIBRARIES:
            raise ValueError(f"lib is one of {', '.join(LIBRARIES)}, not {lib!r}")
        found = library_of(graph)
        if found != lib:
            raise TypeError(f"a {lib} bundle needs a {lib} object, not {type(graph).__module__}."
                            f"{type(graph).__name__}")
        self.graph = graph
        self.context = context
        self.lib = lib
        self.report: ExportReport | None = None

    def __repr__(self) -> str:
        return (f"Bundle({type(self.graph).__name__}, lib={self.lib!r}, network_type="
                f"{self.context.network_type!r}, profile={self.context.profile})")

    def records(self, edge: Any, node: Any = None) -> tuple[dict[str, Any], ...]:
        """The full incidence records of ``edge`` (of the pair ``(edge, node)`` when ``node`` is given) that the
        bundle carries for live memberships, in record order: the loaded records in source order, then labels (XGI);
        each cell's record, then its ``khg-extra-incidences`` (HyperNetX). Copies, so editing them changes
        nothing."""
        found = _backend(self.lib).records(self, edge, node)
        return tuple(copy.deepcopy(r) for r in found)

    def roles(self, edge: Any, node: Any) -> list[str]:
        """The roles of ``node`` in ``edge``, in record order."""
        return [r["attrs"]["role"] for r in self.records(edge, node)
                if isinstance(r.get("attrs"), Mapping) and isinstance(r["attrs"].get("role"), str)]

    def derive(self, graph: Any) -> Bundle:
        """A bundle for a copy or restriction of this bundle's graph, with this bundle's context (its labels are
        copied, so labelling one bundle never changes the other)."""
        return Bundle(graph, self.context.derived(), self.lib)

    def label(self, edge: Any, node: Any, *, role: str, bid: str | None = None, direction: str | None = None,
              position: int | None = None, weight: int | float | None = None,
              extensions: Mapping[str, Any] | None = None) -> None:
        """Give the membership ``(edge, node)`` a record: required for a new membership before a strict export.

        In a ``khg-hif`` file the record needs a ``khg-bid`` (``bid``). XGI keeps the record in the context; in a
        directed XGI graph ``direction`` names the membership (tail is ``"in"``, head ``"out"``). HyperNetX writes a
        new cell's record into the cell (``direction`` and ``weight`` into its columns) and adds a further record of
        a labelled pair under ``khg-extra-incidences``. Raises ``LoaderError``: P005 when the membership does not
        exist or the record lacks its role or bid; P016 for a bid another live record of the edge has; R002 for an
        exact repeat of a live record of the pair (the same role and ``role-position``, §4.1 rule 2); P010 in a
        directed file for a record without direction (a directed XGI membership named without it; in HyperNetX a
        further record without it, or a new cell's record when the cell has no direction either); and the codes of
        ``make_record``.
        """
        record = make_record(edge, node, role=role, bid=bid, direction=direction, position=position, weight=weight,
                             extensions=extensions, profile=self.context.profile)
        if self.context.profile and any(r["attrs"].get("khg-bid") == bid for r in self.records(edge)):
            raise _refuse("KHG-P016", "/attrs/khg-bid", f"khg-bid {bid!r} is already used in edge {edge!r}")
        position = record["attrs"].get("role-position")
        key = (role, _position_key(position))
        if any(isinstance(r.get("attrs"), Mapping) and
               (r["attrs"].get("role"), _position_key(r["attrs"].get("role-position"))) == key
               for r in self.records(edge, node)):
            at = "without role-position" if position is None else f"at role-position {position!r}"
            raise _refuse("KHG-R002", "/attrs/role", f"an exact repeat: ({edge!r}, {node!r}) already has a {role!r} "
                          f"record {at}")
        _backend(self.lib).attach(self, record)
