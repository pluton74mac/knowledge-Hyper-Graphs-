"""C1 -> role-aware HIF: ``to_hif`` (DESIGN §4.2, §4.5, §4.6).

| C1 | HIF |
|---|---|
| header | ``metadata``: the declaration block, then the keys of ``extensions["hif:metadata"]`` |
| entity | node ``{node: id, weight?, attrs: {khg-kind: "entity", label, khg-types, ...}}`` |
| literal, special, unbound, fact value | a derived node (``hif.nodes``) |
| hyperedge | edge ``{edge: id, weight?, attrs: {relation, khg-status, ...}}`` |
| binding | incidence ``{edge, node, direction?, weight?, attrs: {role, khg-bid, role-position?, khg-extensions?}}`` |

- **Order.** Entity nodes by id, then derived nodes by id; edges by id; incidences by edge, then in canonical
  binding order (role, position, value).
- **Directions.** Every incidence carries its effective direction (the binding's, else the usage's).
  ``network-type`` is ``directed`` iff every incidence has one; otherwise ``undirected``, and the native directions
  stay. ``asc`` is never written.
- **Weights** come only from ``extensions["hif:weight"]`` of entities, hyperedges and bindings; the other
  extensions go to ``khg-extensions``. A weight is never invented and never read as confidence.
"""
from __future__ import annotations

import copy
import math
import os
from typing import Any, Iterable, Mapping

from ..errors import ValidationError, make_finding
from ..record import binding_sort_key, normalize, read_container
from ..schema import Schema, load_schema
from .nodes import value_node
from .profile import (DECLARATION_KEYS, EDGE_FIELDS, ENTITY_FIELDS, HIF_SCHEMA_SHA256, HIF_SCHEMA_URL,
                      LITERAL_NODES, METADATA, PROFILE, ROLE_CONVENTION, WEIGHT, id_ok)
from .slices import select_slice

__all__ = ["as_schema", "effective_direction", "to_hif"]

Finding = dict[str, str]


def _fail(code: str, path: str, message: str) -> ValidationError:
    return ValidationError.from_findings([make_finding(code, path, message)])


def as_schema(schema: Any) -> Schema:
    """A ``Schema`` from a ``Schema`` (as is), a schema document or a path (``load_schema``: J, V and M)."""
    if isinstance(schema, Schema):
        return schema
    if schema is None:
        raise TypeError("a relation-type schema is required")
    return load_schema(schema)


def _as_container(container: Any) -> Mapping[str, Any]:
    if isinstance(container, (str, os.PathLike)) or (hasattr(container, "read_bytes") and hasattr(container, "name")):
        container = read_container(container)
    if not isinstance(container, Mapping):
        raise TypeError(f"a C1 container is a mapping or a path, not {type(container).__name__}")
    header = container.get("header")
    if not isinstance(header, Mapping) or not isinstance(container.get("records"), list):
        raise _fail("KHG-C010", "", "a container is {header: object, records: array}")
    for field in ("format", "document_id"):
        if not isinstance(header.get(field), str):
            raise _fail("KHG-C010", f"/header/{field}", f"the header's {field} is a string")
    return container


def _relations(relations: Iterable[str], schema: Schema) -> list[str]:
    if isinstance(relations, (str, bytes)):
        raise TypeError("relations is a list of relation ids, not a string")
    out = sorted(set(relations))
    for rel in out:
        if not isinstance(rel, str) or not schema.has_relation(rel):
            raise _fail("KHG-S001", "", f"relation {rel!r} of the slice is not declared in {schema.ref}")
    return out


def _check_pin(header: Mapping[str, Any], schema: Schema) -> None:
    """D009 when the header pins another schema than ``schema``."""
    pin = header.get("schema")
    if pin is not None and (not isinstance(pin, Mapping) or
                            (pin.get("id"), pin.get("version"), pin.get("sha256")) !=
                            (schema.id, schema.version, schema.sha256)):
        raise _fail("KHG-D009", "/header/schema", f"the container pins another schema than {schema.ref}")


def _records(container: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The container's entities and hyperedges, normalised and sorted by id. C010 for a record without a string id,
    or a hyperedge without a relation and a list of bindings with string bids and roles; D001 for an entity or a
    hyperedge id declared twice (which also refuses history containers)."""
    out: dict[str, list[dict[str, Any]]] = {"entity": [], "hyperedge": []}
    seen: dict[str, set[str]] = {"entity": set(), "hyperedge": set()}
    for i, r in enumerate(container["records"]):
        if not isinstance(r, Mapping) or r.get("kind") not in ("entity", "hyperedge"):
            continue  # embedded relation-schema records are not exported
        if not isinstance(r.get("id"), str):
            raise _fail("KHG-C010", f"/records/{i}/id", "a record id is a string")
        rec = normalize(r)
        if rec["id"] in seen[rec["kind"]]:
            raise _fail("KHG-D001", f"/records/{i}", f"{rec['id']!r} is declared twice")
        seen[rec["kind"]].add(rec["id"])
        bindings = rec.get("bindings")
        if rec["kind"] == "hyperedge" and (not isinstance(rec.get("relation"), str) or not isinstance(bindings, list)
                                           or not all(_binding_ok(b) for b in bindings)):
            raise _fail("KHG-C010", f"/records/{i}", "a hyperedge has a relation and bindings {bid, role, value}")
        out[rec["kind"]].append(rec)
    return sorted(out["entity"], key=lambda r: r["id"]), sorted(out["hyperedge"], key=lambda r: r["id"])


def _binding_ok(b: Any) -> bool:
    return isinstance(b, Mapping) and isinstance(b.get("bid"), str) and isinstance(b.get("role"), str) and "value" in b


def _weight_ok(w: Any) -> bool:
    """A HIF weight: a finite number, not a boolean (H009 in the HIF file otherwise)."""
    if isinstance(w, bool) or not isinstance(w, (int, float)):
        return False
    return isinstance(w, int) or math.isfinite(w)


def _split(extensions: Any, owner: str) -> tuple[Any, Any]:
    """``(weight, rest)`` of an ``extensions`` object: ``hif:weight`` becomes the weight and the other keys stay in
    ``rest``; ``rest`` is None when nothing else is left (an empty ``extensions`` stays ``{}``). C010 when
    ``extensions`` is not an object, or its ``hif:weight`` is not a finite number (null included), which HIF could
    not carry (``owner`` names the record or binding)."""
    if not isinstance(extensions, Mapping):
        raise _fail("KHG-C010", "", f"{owner}: extensions is an object")
    if WEIGHT in extensions and not _weight_ok(extensions[WEIGHT]):
        shown = repr(extensions[WEIGHT])[:60]
        raise _fail("KHG-C010", "", f"{owner}: extensions[{WEIGHT!r}] is a finite number, not {shown}")
    rest = {k: copy.deepcopy(v) for k, v in extensions.items() if k != WEIGHT}
    keep = rest or WEIGHT not in extensions
    return extensions.get(WEIGHT), (rest if keep else None)


def _attrs(record: Mapping[str, Any], fields: tuple[tuple[str, str], ...], first: Mapping[str, Any]
           ) -> tuple[dict[str, Any], Any]:
    """``(attrs, weight)`` of a node or edge record."""
    attrs = dict(first)
    weight = None
    for field, key in fields:
        if field not in record:
            continue
        if field == "extensions":
            weight, rest = _split(record["extensions"], record["id"])
            if rest is not None:
                attrs[key] = rest
        else:
            attrs[key] = copy.deepcopy(record[field])
    return attrs, weight


def _item(id_key: str, id_value: str, weight: Any, attrs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {id_key: id_value}
    if weight is not None:
        out["weight"] = weight
    out["attrs"] = attrs
    return out


def effective_direction(schema: Schema, relation: str, binding: Mapping[str, Any]) -> str | None:
    """The binding's direction, else its usage's (S001 or S002 when the relation or role is not declared)."""
    usage = schema.usage(relation, binding["role"])
    return binding.get("direction") or usage.get("direction")


def _incidence(edge: str, node: str, binding: Mapping[str, Any], direction: str | None) -> dict[str, Any]:
    attrs: dict[str, Any] = {"role": binding["role"], "khg-bid": binding["bid"]}
    if "position" in binding:
        attrs["role-position"] = binding["position"]
    weight, rest = (None, None)
    if "extensions" in binding:
        weight, rest = _split(binding["extensions"], f"{edge} {binding['bid']}")
    if rest is not None:
        attrs["khg-extensions"] = rest
    out: dict[str, Any] = {"edge": edge, "node": node}
    if direction:
        out["direction"] = direction
    if weight is not None:
        out["weight"] = weight
    out["attrs"] = attrs
    return out


def _metadata(header: Mapping[str, Any], schema: Schema, relations: list[str] | None, literal_nodes: str,
              schema_document: bool) -> dict[str, Any]:
    md: dict[str, Any] = {
        "role-convention": ROLE_CONVENTION,
        "hif-schema": HIF_SCHEMA_URL,
        "hif-schema-sha256": HIF_SCHEMA_SHA256,
        "khg-profile": PROFILE,
        "khg-record": header.get("format"),
        "khg-schema": schema.ref,
        "khg-schema-sha256": schema.sha256,
        "khg-document-id": header.get("document_id"),
        "khg-literal-nodes": literal_nodes,
    }
    if "complete" in header:
        md["khg-complete"] = header["complete"]
    if relations is not None:
        md["khg-slice"] = {"relations": list(relations)}
    if schema_document:
        md["khg-schema-document"] = copy.deepcopy(schema.doc)
    extensions = header.get("extensions")
    extra = extensions.get(METADATA) if isinstance(extensions, Mapping) else None
    for key, value in (extra.items() if isinstance(extra, Mapping) else ()):
        if key in DECLARATION_KEYS or key == "default_attrs" or key.startswith("khg-"):
            raise _fail("KHG-P008", f"/header/extensions/{METADATA}", f"{key!r} cannot pass through to the HIF "
                        "metadata: it is a declaration key, default_attrs or a khg-* key")
        md[key] = copy.deepcopy(value)
    return md


def to_hif(container: Any, schema: Any, *, relations: Iterable[str] | None = None, literal_nodes: str = "shared",
           schema_document: bool = False) -> dict[str, Any]:
    """The role-aware HIF file of a C1 container, under the ``khg-hif/1.0.0`` profile (§4.2).

    ``container`` is a C1 container or a path to one; ``schema`` a ``Schema``, a schema document or a path.
    ``relations`` exports a closed slice of those relations (§4.6). ``literal_nodes`` is ``"shared"`` (one node per
    literal value) or ``"per_binding"`` (one per binding). ``schema_document=True`` inlines the schema as
    ``khg-schema-document``, so ``from_hif`` can run without a schema argument.

    Raises ``ValidationError``: D009 when the header pins another schema, D001 for an id declared twice, S001 or
    S002 for an undeclared relation or role, C codes for a malformed record or value, P003 for an id outside the
    profile's grammar, P008 for a ``hif:metadata`` key that cannot pass through.
    """
    if literal_nodes not in LITERAL_NODES:
        raise ValueError(f"literal_nodes must be one of {', '.join(LITERAL_NODES)}, not {literal_nodes!r}")
    sch = as_schema(schema)
    doc = _as_container(container)
    header = doc["header"]
    _check_pin(header, sch)
    rels = None if relations is None else _relations(relations, sch)
    if rels is not None:
        doc = select_slice(doc, rels)
        header = doc["header"]
    entities, edges = _records(doc)
    present = {r["id"] for r in edges}
    nodes: dict[str, dict[str, Any]] = {}
    for e in entities:
        attrs, weight = _attrs(e, ENTITY_FIELDS, {"khg-kind": "entity"})
        nodes[e["id"]] = _item("node", e["id"], weight, attrs)
    edge_items, incidences = [], []
    directed = True
    for r in edges:
        attrs, weight = _attrs(r, EDGE_FIELDS, {})
        edge_items.append(_item("edge", r["id"], weight, attrs))
        for b in sorted(r["bindings"], key=binding_sort_key):
            direction = effective_direction(sch, r["relation"], b)
            directed = directed and bool(direction)
            node = value_node(r["id"], b, nodes, literal_nodes=literal_nodes, present=present)
            incidences.append(_incidence(r["id"], node, b, direction))
    ordered = [nodes[k] for k in sorted(nodes, key=lambda i: (i.startswith("_:"), i))]
    for i in [n["node"] for n in ordered] + [e["edge"] for e in edge_items]:
        if not id_ok(i):
            raise _fail("KHG-P003", "", f"the id {i[:40]!r} is outside the profile's id grammar")
    return {"network-type": "directed" if directed else "undirected",
            "metadata": _metadata(header, sch, rels, literal_nodes, schema_document),
            "nodes": ordered, "edges": edge_items, "incidences": incidences}
