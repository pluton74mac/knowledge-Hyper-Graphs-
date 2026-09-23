"""The projections of C1 facts (DESIGN §2.10). Their output formats are part of the contract.

- ``position_map`` and ``positional``: a fact as a fixed-width tuple over its relation's usages (P3b).
- ``hyper_relational``: ``{subject, relation, object, qualifiers}`` from the relation's ``primary``.
- ``role_value_set``: the sorted multiset of ``[role, value id]``.
- ``rdf_relation_instance`` and ``from_rdf_relation_instance``: one IRI per fact (``urn:khg:<id>``) and one per
  binding (``urn:khg:<id>#<bid>``); ids are percent-encoded outside RFC 3987 ``iunreserved`` (UTF-8 octets).
- ``incidence_rows`` and ``from_incidence_rows``: one row per binding.

A value id is the entity or fact id, the ``_:lit:`` id of a literal (or ``khg:none`` with ``literals="drop"``), or
the per-binding ``_:sv:``/``_:nv:`` id of a special value. Binding ``extensions`` and evidence are not projected.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping
from urllib.parse import unquote

from .. import jsonio
from ._common import SchemaLike, as_schema, bindings, hyperedge, value_kind
from .canonical import binding_sort_key, canonical_container
from .nodes import NONE_ID, literal_node_id, special_node_id
from .values import canonical_value

__all__ = [
    "INCIDENCE_COLUMNS",
    "KHG_NS",
    "NONE_ID",
    "RDF_TYPE",
    "from_incidence_rows",
    "from_rdf_relation_instance",
    "hyper_relational",
    "incidence_rows",
    "iri_decode",
    "iri_encode",
    "position_map",
    "positional",
    "rdf_relation_instance",
    "role_value_set",
]

KHG_NS = "https://w3id.org/khg/ns#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
IRI_PREFIX = "urn:khg:"
INCIDENCE_COLUMNS = ("fact_id", "version", "relation", "status", "bid", "role", "position", "direction",
                     "value_kind", "value")
LITERALS = ("node", "drop")
_ASCII_UNRESERVED = re.compile(r"[A-Za-z0-9._~-]")
#: RFC 3987 ucschar ranges (the non-ASCII part of iunreserved)
_UCSCHAR = ((0xA0, 0xD7FF), (0xF900, 0xFDCF), (0xFDF0, 0xFFEF)) + tuple(
    (p * 0x10000, p * 0x10000 + 0xFFFD) for p in range(1, 14)) + ((0xE1000, 0xEFFFD),)

Triple = tuple[str, str, Any]


# ------------------------------------------------------------------------------------------------ value ids


def _value_id(record: Mapping[str, Any], b: Mapping[str, Any], literals: str) -> str:
    v = b["value"]
    kind = value_kind(v)
    if kind in ("entity", "fact"):
        return v[kind]
    if kind == "literal":
        return literal_node_id(v["literal"]) if literals == "node" else NONE_ID
    if kind == "special":
        return special_node_id(v["special"], record["id"], b["bid"])
    raise ValueError(f"{record.get('id')!r}: an unbound value has no projection")


def _check_literals(literals: str) -> None:
    if literals not in LITERALS:
        raise ValueError(f"literals must be one of {LITERALS}, not {literals!r}")


def _projectable(record: Mapping[str, Any], schema: SchemaLike) -> Any:
    hyperedge(record)
    s = as_schema(schema)
    if record.get("status") == "goal" or s.kind(record.get("relation")) == "lifecycle":
        raise ValueError(f"{record.get('id')!r}: lifecycle and goal records have no projection")
    return s


# ------------------------------------------------------------------------------------------------ positional


def position_map(schema: SchemaLike, relation: str, *, slots: tuple[str, ...] = ("core", "qualifier"),
                 literals: str = "node", widths: Mapping[str, int] | None = None) -> list[tuple[str, int]]:
    """The positions of a relation as ``(role, i)``: its usages in schema order (filtered by ``slots``); a usage with
    max k gives k positions; an unbounded usage takes ``widths[role]`` (``ValueError`` without it). With
    ``literals="drop"`` the usages that admit only literals are left out."""
    _check_literals(literals)
    out: list[tuple[str, int]] = []
    for u in as_schema(schema).usages(relation):
        if u["slot"] not in slots:
            continue
        if literals == "drop" and all("literal" in f for f in u["fillers"]):
            continue
        width = u.get("max")
        if width is None:
            width = (widths or {}).get(u["role"])
            if width is None:
                raise ValueError(f"the unbounded usage {relation}.{u['role']} needs a width (widths={{role: k}})")
        out.extend((u["role"], i) for i in range(1, width + 1))
    return out


def positional(record: Mapping[str, Any], schema: SchemaLike, *, slots: tuple[str, ...] = ("core", "qualifier"),
               literals: str = "node", widths: Mapping[str, int] | None = None) -> tuple[str, ...]:
    """``(relation, v1, ..., vn)`` over ``position_map``: ordered roles fill their positions by ``position``,
    unordered roles in canonical value order; an absent optional position is ``khg:none``. Lifecycle and goal
    records, and more fillers than positions, raise ``ValueError``."""
    s = _projectable(record, schema)
    rel = record["relation"]
    pm = position_map(s, rel, slots=slots, literals=literals, widths=widths)
    width: dict[str, int] = {}
    for role, _ in pm:
        width[role] = width.get(role, 0) + 1
    by_role: dict[str, list[Mapping[str, Any]]] = {}
    for b in sorted(bindings(record), key=binding_sort_key):
        if s.slot(rel, b.get("role")) in slots:
            by_role.setdefault(b["role"], []).append(b)
    for role, bs in by_role.items():
        if role in width and len(bs) > width[role]:
            raise ValueError(f"{record.get('id')!r}: {len(bs)} fillers of {role} but {width[role]} positions "
                             "(raise the width)")
    values = []
    for role, i in pm:
        bs = by_role.get(role, [])
        if s.usage(rel, role).get("ordered"):
            b = next((x for x in bs if x.get("position") == i), None)
        else:
            b = bs[i - 1] if i <= len(bs) else None
        values.append(NONE_ID if b is None else _value_id(record, b, literals))
    return (rel, *values)


# ------------------------------------------------------------------------------------------------ pairs


def hyper_relational(record: Mapping[str, Any], schema: SchemaLike) -> dict[str, Any]:
    """``{subject, relation, object, qualifiers}``: subject and object from the relation's ``primary`` (a relation
    without one raises ``ValueError``); every other core, qualifier and time binding is a ``[role, value id]``
    qualifier pair, sorted."""
    hyperedge(record)
    s = as_schema(schema)
    rel = record["relation"]
    primary = s.relation(rel).get("primary")
    if not primary:
        raise ValueError(f"relation {rel!r} declares no primary")
    bs = bindings(record)

    def only(role: str) -> Mapping[str, Any]:
        found = [b for b in bs if b.get("role") == role]
        if len(found) != 1:
            raise ValueError(f"{record.get('id')!r}: the primary role {role} has {len(found)} bindings, not 1")
        return found[0]

    subj, obj = only(primary["subject"]), only(primary["object"])
    quals = sorted([b["role"], _value_id(record, b, "node")] for b in bs
                   if b is not subj and b is not obj and s.slot(rel, b.get("role")) in ("core", "qualifier", "time"))
    return {"subject": _value_id(record, subj, "node"), "relation": rel,
            "object": _value_id(record, obj, "node"), "qualifiers": quals}


def role_value_set(record: Mapping[str, Any], schema: SchemaLike, *,
                   slots: tuple[str, ...] = ("core", "qualifier")) -> list[list[str]]:
    """The sorted multiset of ``[role, value id]`` over the bindings in ``slots`` (``ValueError`` for an unbound
    value)."""
    hyperedge(record)
    s = as_schema(schema)
    rel = record["relation"]
    return sorted([b["role"], _value_id(record, b, "node")] for b in bindings(record)
                  if s.slot(rel, b.get("role")) in slots)


# ------------------------------------------------------------------------------------------------ RDF


def _iunreserved(ch: str) -> bool:
    if _ASCII_UNRESERVED.fullmatch(ch):
        return True
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _UCSCHAR)


def iri_encode(identifier: str) -> str:
    """``urn:khg:<id>`` with every character outside RFC 3987 ``iunreserved`` percent-encoded as UTF-8 octets, so
    ``ex:Łódź`` is ``urn:khg:ex%3AŁódź``; ``iri_decode`` inverts it."""
    out = []
    for ch in jsonio.nfc(identifier):
        out.append(ch if _iunreserved(ch) else "".join(f"%{x:02X}" for x in ch.encode("utf-8")))
    return IRI_PREFIX + "".join(out)


def iri_decode(iri: str) -> str:
    """The id of a ``urn:khg:`` IRI (``ValueError`` for any other IRI)."""
    if not isinstance(iri, str) or not iri.startswith(IRI_PREFIX):
        raise ValueError(f"{iri!r} is not a urn:khg: IRI")
    return unquote(iri[len(IRI_PREFIX):], encoding="utf-8", errors="strict")


def _lit(text: str) -> dict[str, str]:
    return {"literal": text}


def rdf_relation_instance(container: Mapping[str, Any]) -> list[Triple]:
    """The RDF relation-instance projection of a container's hyperedges: triples ``(s, p, o)`` with IRIs as strings
    and literals as ``{"literal": text}``, sorted by their canonical JSON. Entity and fact values are
    ``khg:value`` IRIs with a ``khg:valueKind``; other values are ``khg:valueJSON`` (canonical JSON)."""
    triples: list[Triple] = []
    for r in container.get("records", []):
        if r.get("kind") != "hyperedge":
            continue
        f = iri_encode(r["id"])
        triples += [(f, RDF_TYPE, KHG_NS + "Hyperedge"), (f, KHG_NS + "relation", _lit(r["relation"])),
                    (f, KHG_NS + "status", _lit(r["status"]))]
        for b in bindings(r):
            n = f + "#" + b["bid"]
            triples += [(f, KHG_NS + "binding", n), (n, KHG_NS + "bid", _lit(b["bid"])),
                        (n, KHG_NS + "role", _lit(b["role"]))]
            if "position" in b:
                triples.append((n, KHG_NS + "position", _lit(jsonio.number(b["position"]))))
            if "direction" in b:
                triples.append((n, KHG_NS + "direction", _lit(b["direction"])))
            v = b["value"]
            kind = value_kind(v)
            if kind in ("entity", "fact"):
                triples += [(n, KHG_NS + "value", iri_encode(v[kind])), (n, KHG_NS + "valueKind", _lit(kind))]
            else:
                triples.append((n, KHG_NS + "valueJSON", _lit(jsonio.canonical(canonical_value(v)))))
    return sorted(triples, key=lambda t: jsonio.canonical(list(t)))


def _structure(facts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    for f in facts.values():
        f["bindings"].sort(key=binding_sort_key)
    return {k: facts[k] for k in sorted(facts)}


def from_rdf_relation_instance(triples: Iterable[Triple]) -> dict[str, dict[str, Any]]:
    """The inverse of ``rdf_relation_instance`` for the binding structure: ``{fact id: {relation, status,
    bindings}}``, bindings in canonical order."""
    facts: dict[str, dict[str, Any]] = {}
    nodes: dict[str, dict[str, Any]] = {}
    links: dict[str, list[str]] = {}
    for s, p, o in triples:
        if p == RDF_TYPE:
            facts.setdefault(s, {})
        elif p in (KHG_NS + "relation", KHG_NS + "status"):
            facts.setdefault(s, {})[p[len(KHG_NS):]] = o["literal"]
        elif p == KHG_NS + "binding":
            links.setdefault(s, []).append(o)
        elif p.startswith(KHG_NS):
            nodes.setdefault(s, {})[p[len(KHG_NS):]] = o
        else:
            raise ValueError(f"unknown predicate {p!r}")
    out: dict[str, dict[str, Any]] = {}
    for f, d in facts.items():
        bs = []
        for n in links.get(f, []):
            a = nodes[n]
            b: dict[str, Any] = {"bid": a["bid"]["literal"], "role": a["role"]["literal"]}
            if "position" in a:
                b["position"] = int(a["position"]["literal"])
            if "direction" in a:
                b["direction"] = a["direction"]["literal"]
            if "value" in a:
                b["value"] = {a["valueKind"]["literal"]: iri_decode(a["value"])}
            else:
                b["value"] = jsonio.loads(a["valueJSON"]["literal"])
            bs.append(b)
        out[iri_decode(f)] = {"relation": d["relation"], "status": d["status"], "bindings": bs}
    return _structure(out)


# ------------------------------------------------------------------------------------------------ incidence rows


def incidence_rows(container: Mapping[str, Any]) -> list[tuple[Any, ...]]:
    """One row per binding, in canonical record and binding order: ``(fact_id, version, relation, status, bid,
    role, position, direction, value_kind, value)``; ``value`` is the id of an entity or fact, else the canonical
    JSON of the value; ``version`` is 1 when the record has none."""
    rows = []
    for r in canonical_container(container)["records"]:
        if r.get("kind") != "hyperedge":
            continue
        for b in bindings(r):
            v = b["value"]
            kind = value_kind(v)
            value = v[kind] if kind in ("entity", "fact") else jsonio.canonical(canonical_value(v))
            rows.append((r["id"], r.get("version", 1), r["relation"], r["status"], b["bid"], b["role"],
                         b.get("position"), b.get("direction"), kind, value))
    return rows


def from_incidence_rows(rows: Iterable[Iterable[Any]]) -> dict[str, dict[str, Any]]:
    """The inverse of ``incidence_rows`` for the binding structure: ``{fact id: {relation, status, bindings}}``."""
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        fid, _version, rel, status, bid, role, pos, direction, kind, value = row
        f = out.setdefault(fid, {"relation": rel, "status": status, "bindings": []})
        b: dict[str, Any] = {"bid": bid, "role": role,
                             "value": {kind: value} if kind in ("entity", "fact") else jsonio.loads(value)}
        if pos is not None:
            b["position"] = pos
        if direction is not None:
            b["direction"] = direction
        f["bindings"].append(b)
    return _structure(out)
