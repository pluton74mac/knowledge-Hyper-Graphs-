"""The four rules of ``role-convention`` 1.0.0 (DESIGN §4.1), the upstream artefact that layer R checks.

1. Every incidence of a role-carrying edge has ``attrs.role``, one non-empty string; an edge is role-carrying when
   at least one of its incidences has ``attrs.role`` (R001).
2. A node with k roles in one edge appears in k incidence records. The records of one (edge, node) pair may differ
   in ``direction`` and must differ in ``role`` or ``role-position``: an exact repeat of (edge, node, role,
   role-position) is malformed (R002).
3. ``metadata["role-convention"] = "1.0.0"`` declares the convention (R003); ``metadata["role-vocabulary"]`` is
   optional.
4. ``attrs["role-position"]``, an integer >= 1, orders the fillers of one role (R004). As everywhere in the
   package (F10), an integral float such as ``1.0`` is that integer.

The checks read any JSON document without raising; what the vendored schema rejects (layer H) is skipped.
"""
from __future__ import annotations

from typing import Any, Mapping

from ..errors import make_finding
from ._doc import attrs_of, mapping, records
from .profile import ROLE_CONVENTION, id_key

__all__ = ["convention_findings", "role_position"]

Finding = dict[str, str]


def role_position(value: Any) -> int | None:
    """``value`` as a ``role-position`` (an integer >= 1, or an integral float), else None (R004)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    return int(value) if value >= 1 else None


def convention_findings(doc: Any) -> list[Finding]:
    """The R findings of a HIF document: R003 on the declaration, then R001, R004 and R002 per incidence."""
    if not isinstance(doc, Mapping):
        return []
    out: list[Finding] = []
    declared = mapping(doc.get("metadata")).get("role-convention")
    if declared != ROLE_CONVENTION:
        out.append(make_finding("KHG-R003", "/metadata/role-convention",
                                f"role-convention is {declared!r}, not {ROLE_CONVENTION!r}"))
    incidences = list(records(doc, "incidences"))
    carrying = {id_key(inc.get("edge")) for _, inc in incidences if "role" in attrs_of(inc)}
    seen: set[tuple[Any, ...]] = set()
    for j, inc in incidences:
        attrs = attrs_of(inc)
        role = attrs.get("role")
        if id_key(inc.get("edge")) in carrying and not (isinstance(role, str) and role):
            out.append(make_finding("KHG-R001", f"/incidences/{j}/attrs/role",
                                    "an incidence of a role-carrying edge needs one non-empty string role"))
        position: Any = None
        if "role-position" in attrs:
            position = role_position(attrs["role-position"])
            if position is None:
                out.append(make_finding("KHG-R004", f"/incidences/{j}/attrs/role-position",
                                        f"role-position {attrs['role-position']!r} is not an integer >= 1"))
                position = ("invalid", repr(attrs["role-position"]))
        if isinstance(role, str):
            key = (id_key(inc.get("edge")), id_key(inc.get("node")), role, position)
            if key in seen:
                out.append(make_finding("KHG-R002", f"/incidences/{j}",
                                        "an exact repeat of (edge, node, role, role-position)"))
            seen.add(key)
    return out
