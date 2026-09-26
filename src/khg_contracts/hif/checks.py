"""The Python checks of the ``khg-hif`` profile, 1.0.0 and 1.1.0 (DESIGN §4.2-§4.6, §8.1).

The draft-07 profile schema (``khg-hif-1.0.0.schema.json``) covers the declaration block, the id types and grammar,
the node kinds and their payloads, the edge and incidence ``attrs``; these checks cover what a schema cannot say:

- P004: an entity id uses the reserved ``_:`` prefix, or a derived node lacks its kind's prefix;
- P017: a ``khg-external`` fact reference in a complete file that is not a slice, or naming a fact the file holds
  (1.0.0 accepted one only in a slice; 1.1.0 in any file that is not complete, ``profile.external_allowed``);
- P010 and P011: the direction rule (``directed`` iff every incidence has a direction);
- P016: two incidence records of one edge share a ``khg-bid``.

They read any JSON document without raising; what the schemas reject is skipped.
"""
from __future__ import annotations

from typing import Any, Mapping

from ..errors import make_finding
from ._doc import attrs_of, mapping, records
from .profile import KIND_PREFIXES, external_allowed, id_key

__all__ = ["profile_findings"]

Finding = dict[str, str]


def _node_findings(doc: Mapping[str, Any], md: Mapping[str, Any]) -> list[Finding]:
    out = []
    present = {e.get("edge") for _, e in records(doc, "edges") if isinstance(e.get("edge"), str)}
    external = external_allowed(md)
    for j, node in records(doc, "nodes"):
        nid, attrs = node.get("node"), attrs_of(node)
        kind = attrs.get("khg-kind")
        if not isinstance(nid, str) or not isinstance(kind, str):
            continue  # P002 and P013 are the schema's
        if kind == "entity" and nid.startswith("_:"):
            out.append(make_finding("KHG-P004", f"/nodes/{j}/node", "an entity id uses the reserved _: prefix"))
        elif kind in KIND_PREFIXES and not nid.startswith(KIND_PREFIXES[kind]):
            out.append(make_finding("KHG-P004", f"/nodes/{j}/node",
                                    f"a {kind} node id starts with {' or '.join(KIND_PREFIXES[kind])}"))
        ref = attrs.get("khg-ref")
        if kind == "fact-ref" and attrs.get("khg-external") and (
                not external or (isinstance(ref, str) and ref in present)):
            out.append(make_finding("KHG-P017", f"/nodes/{j}/attrs/khg-external",
                                    "an external fact reference in a complete file, or to a fact the file holds"))
    return out


def _incidence_findings(doc: Mapping[str, Any]) -> list[Finding]:
    out = []
    incidences = list(records(doc, "incidences"))
    if doc.get("network-type") == "directed":
        out += [make_finding("KHG-P010", f"/incidences/{j}", "a directed file with an incidence without direction")
                for j, inc in incidences if "direction" not in inc]
    elif incidences and all("direction" in inc for _, inc in incidences):
        out.append(make_finding("KHG-P011", "/network-type",
                                "every incidence has a direction, so the file is directed"))
    seen: set[tuple[Any, ...]] = set()
    for j, inc in incidences:
        bid = attrs_of(inc).get("khg-bid")
        if bid is None:
            continue  # P005 is the schema's
        key = (id_key(inc.get("edge")), id_key(bid))
        if key in seen:
            out.append(make_finding("KHG-P016", f"/incidences/{j}/attrs/khg-bid",
                                    f"khg-bid {bid!r} is repeated in edge {inc.get('edge')!r}"))
        seen.add(key)
    return out


def profile_findings(doc: Any) -> list[Finding]:
    """The profile's Python findings on a HIF document: P004 and P017 per node, then P010 or P011, then P016."""
    if not isinstance(doc, Mapping):
        return []
    return _node_findings(doc, mapping(doc.get("metadata"))) + _incidence_findings(doc)
