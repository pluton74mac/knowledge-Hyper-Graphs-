"""The ``v0-sample`` input format and its checks (DESIGN §11.3).

The format is the knowledge base's ``schemas/sample.hif.json``: HIF 0.1 whose records carry the sample's own
conventions, and nothing else.

- metadata: any keys; ``schema`` and ``conventions`` are replaced by the declaration block (F016);
- a node: ``node``, ``attrs.type`` (one entity type) and ``attrs.label`` (optional);
- an edge: ``edge``, ``weight`` (optional), ``attrs.relation``, ``attrs.source``, and the optional ``attrs.arity``
  and ``attrs.valid-from`` (``YYYY-MM-DD``);
- an incidence: ``edge``, ``node``, ``direction`` (optional) and ``attrs.role``.

``read(source)`` parses the input (layer J), checks it against the vendored HIF schema (layer H), then checks the
format. Every refusal carries a registered code and a path into the input:

- P002 for an id that is not a string, P007 for ``asc``, P010 and P011 for the profile's direction rule, P008 for a
  metadata key that cannot pass through to the migrated file (a declaration key, ``default_attrs`` or a ``khg-*``
  key);
- D001 for a node or edge declared twice, D003 and D002 for an incidence naming an undeclared edge or node, S007 for
  an edge without incidences;
- R001 for an incidence without one non-empty string role, R002 for an exact repeat of (edge, node, role);
- C009 for any other member (another ``attrs`` key, ``role-position``, a node or incidence ``weight``): the pinned
  rules give it no place, so it is refused rather than dropped;
- the codes of the C1 field a member becomes: C011 for a node or edge id outside the C1 id grammar, C010 for a
  missing or mistyped ``type``, ``label``, ``relation`` or ``source``, C004 and S006 for a ``valid-from`` that is not
  a date C1 can hold, and S020 for an id, relation, role or type not in NFC.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from ..errors import KHGError, ValidationError, make_finding
from ..hif._doc import attrs_of, mapping, records
from ..hif.profile import DECLARATION_KEYS
from ..jsonio import nfc
from ..record import canonical_literal

__all__ = ["EDGE_ATTRS", "INCIDENCE_ATTRS", "NODE_ATTRS", "REPLACED_METADATA", "findings", "read", "start_literal"]

NODE_ATTRS = ("type", "label")
EDGE_ATTRS = ("relation", "source", "arity", "valid-from")
INCIDENCE_ATTRS = ("role",)
#: The metadata keys the declaration block replaces (F016).
REPLACED_METADATA = ("schema", "conventions")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
#: The C1 id grammar (``khg-record-1.0.0.schema.json``, ``definitions/id``): node and edge ids become record ids.
_C1_ID = re.compile(r"(?!_:)[^\s\x00-\x1f\x7f]{1,512}")

Finding = dict[str, str]


def _path(*parts: Any) -> str:
    """An RFC 6901 pointer."""
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def start_literal(date: str) -> dict[str, Any]:
    """The ``start_time`` literal of a ``valid-from`` date at day precision. The calendar comes with the canonical
    form: gregorian from 1583; an earlier date is S006, as for any C1 time literal without a calendar."""
    return {"datatype": "time", "time": f"+{date}T00:00:00Z", "precision": 11}


def read(source: Any) -> dict[str, Any]:
    """The v0 document from a mapping, raw bytes or a path: layers J and H, then ``findings``. Raises
    ``ValidationError`` with the codes of the first failing stage. The input is never modified."""
    from ..validate.layers import h
    from ..validate.layers.j import parse

    doc, found = parse(source, "hif")
    if not found:
        found = h.findings(doc)
    if not found:
        found = findings(doc)
    if any(f["severity"] == "error" for f in found):
        raise ValidationError.from_findings(found)
    return doc


def findings(doc: Mapping[str, Any]) -> list[Finding]:
    """The format's findings on a document that passed layer H, in document order ([] when it can migrate)."""
    out: list[Finding] = []
    if doc.get("network-type") == "asc":
        out.append(make_finding("KHG-P007", "/network-type", "network-type asc has no C1 reading"))
    for key in mapping(doc.get("metadata")):
        if key in DECLARATION_KEYS or key == "default_attrs" or key.startswith("khg-"):
            out.append(make_finding("KHG-P008", _path("metadata", key), f"metadata {key!r} cannot pass through: it "
                                    "is a declaration key, default_attrs or a khg-* key"))
    nodes = _declared(doc, "nodes", "node", out)
    for j, node in records(doc, "nodes"):
        _node(j, node, out)
    edges = _declared(doc, "edges", "edge", out)
    for k, edge in records(doc, "edges"):
        _edge(k, edge, out)
    _incidences(doc, nodes, edges, out)
    _directions(doc, out)
    return out


def _declared(doc: Mapping[str, Any], key: str, id_key: str, out: list[Finding]) -> dict[str, int]:
    """The declared ids of ``nodes`` or ``edges`` -> their index; P002, C011, S020 and D001 on the way."""
    seen: dict[str, int] = {}
    for j, item in records(doc, key):
        i, path = item.get(id_key), _path(key, j, id_key)
        if not isinstance(i, str):
            out.append(make_finding("KHG-P002", path, f"{id_key} id {i!r} is not a string"))
            continue
        if not _C1_ID.fullmatch(i):
            out.append(make_finding("KHG-C011", path, f"{id_key} id {i[:40]!r} is not a C1 id: 1 to 512 code points "
                                    "without white space or control characters, and no _: prefix"))
        elif nfc(i) != i:
            out.append(make_finding("KHG-S020", path, f"{id_key} id {i!r} is not in Unicode NFC"))
        if i in seen:
            out.append(make_finding("KHG-D001", path, f"{id_key} {i!r} is declared twice"))
        else:
            seen[i] = j
    return seen


def _unknown(item: Mapping[str, Any], known: tuple[str, ...], where: tuple[Any, ...], out: list[Finding]) -> None:
    """C009 for a ``weight`` on a node or an incidence, and for every ``attrs`` key outside ``known``."""
    if "weight" in item and where[0] != "edges":
        out.append(make_finding("KHG-C009", _path(*where, "weight"), "the v0-sample format has no weight here"))
    for key in attrs_of(item):
        if key not in known:
            out.append(make_finding("KHG-C009", _path(*where, "attrs", key),
                                    f"attrs key {key!r} is not part of the v0-sample format"))


def _name(value: Any, path: str, what: str, missing: str, out: list[Finding]) -> bool:
    """True when ``value`` is a non-empty string in NFC; ``missing`` or S020 otherwise."""
    if not (isinstance(value, str) and value):
        out.append(make_finding(missing, path, f"{what} is a non-empty string, not {value!r}"))
        return False
    if nfc(value) != value:
        out.append(make_finding("KHG-S020", path, f"{what} {value!r} is not in Unicode NFC"))
        return False
    return True


def _node(j: int, node: Mapping[str, Any], out: list[Finding]) -> None:
    _unknown(node, NODE_ATTRS, ("nodes", j), out)
    attrs = attrs_of(node)
    _name(attrs.get("type"), _path("nodes", j, "attrs", "type"), "a node's type", "KHG-C010", out)
    if "label" in attrs and not isinstance(attrs["label"], str):
        out.append(make_finding("KHG-C010", _path("nodes", j, "attrs", "label"), "a node's label is a string"))


def _edge(k: int, edge: Mapping[str, Any], out: list[Finding]) -> None:
    _unknown(edge, EDGE_ATTRS, ("edges", k), out)
    attrs = attrs_of(edge)
    _name(attrs.get("relation"), _path("edges", k, "attrs", "relation"), "an edge's relation", "KHG-C010", out)
    source = attrs.get("source")
    if not (isinstance(source, str) and source):
        out.append(make_finding("KHG-C010", _path("edges", k, "attrs", "source"),
                                f"an edge's source (its evidence doc_id) is a non-empty string, not {source!r}"))
    if "valid-from" in attrs:
        _valid_from(attrs["valid-from"], _path("edges", k, "attrs", "valid-from"), out)


def _valid_from(value: Any, path: str, out: list[Finding]) -> None:
    """C004 unless ``value`` is ``YYYY-MM-DD``; else the codes of the time literal it becomes (S006)."""
    if not (isinstance(value, str) and _DATE.fullmatch(value)):
        out.append(make_finding("KHG-C004", path, f"valid-from is an ISO 8601 date YYYY-MM-DD, not {value!r}"))
        return
    try:
        canonical_literal(start_literal(value))
    except KHGError as e:
        out.extend(make_finding(code, path, e.message) for code in e.codes)


def _incidences(doc: Mapping[str, Any], nodes: Mapping[str, int], edges: Mapping[str, int],
                out: list[Finding]) -> None:
    """D003, D002, P002, C009, R001, S020 and R002 per incidence; S007 for an edge without incidences."""
    seen: set[tuple[str, str, Any]] = set()
    used: set[Any] = set()
    for i, inc in records(doc, "incidences"):
        edge, node = inc.get("edge"), inc.get("node")
        used.add(edge)
        for key, value, declared, code in (("edge", edge, edges, "KHG-D003"), ("node", node, nodes, "KHG-D002")):
            if not isinstance(value, str):
                out.append(make_finding("KHG-P002", _path("incidences", i, key), f"{key} id {value!r} is not a string"))
            elif value not in declared:
                out.append(make_finding(code, _path("incidences", i, key), f"{key} {value!r} is not declared"))
        _unknown(inc, INCIDENCE_ATTRS, ("incidences", i), out)
        role = attrs_of(inc).get("role")
        if not _name(role, _path("incidences", i, "attrs", "role"), "an incidence's role", "KHG-R001", out):
            continue
        repeat = (repr(edge), repr(node), role)
        if repeat in seen:
            out.append(make_finding("KHG-R002", _path("incidences", i), "an exact repeat of (edge, node, role)"))
        seen.add(repeat)
    for edge, k in edges.items():
        if edge not in used:
            out.append(make_finding("KHG-S007", _path("edges", k), f"edge {edge!r} has no incidence, so its fact "
                                    "would have no participant"))


def _directions(doc: Mapping[str, Any], out: list[Finding]) -> None:
    """The profile's direction rule: ``directed`` iff every incidence has a direction (P010, P011). The migrated
    file follows the rule, so a v0 file that breaks it would change its network type (``asc`` is P007 already)."""
    incidences = list(records(doc, "incidences"))
    if doc.get("network-type") == "asc":
        return
    if doc.get("network-type") == "directed":
        out.extend(make_finding("KHG-P010", _path("incidences", i), "a directed file with an incidence without "
                                "direction") for i, inc in incidences if "direction" not in inc)
    elif incidences and all("direction" in inc for _, inc in incidences):
        out.append(make_finding("KHG-P011", "/network-type", "every incidence has a direction, so the file is "
                                "directed"))
