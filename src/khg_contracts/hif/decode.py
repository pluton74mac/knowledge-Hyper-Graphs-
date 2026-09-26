"""HIF -> C1: decoding and ``from_hif`` (DESIGN §4.3).

``from_hif(hif, schema=None)`` runs layers J, V, H, R and P, then decodes. Without ``schema`` it uses
``metadata["khg-schema-document"]``; without either it raises D009. A file without ``khg-profile`` is P001: foreign
HIF import comes in 1.1. Files stamped ``khg-hif/1.0.0`` and ``khg-hif/1.1.0`` are read alike.

A file that is not complete (``khg-complete`` absent or false; every slice) may name entities and facts it does not
hold (§4.6; ruling 19, ``profile.external_allowed``). An incidence on a node without a node record is then the entity
of that id, and a ``khg-external`` fact reference the fact of its ``khg-ref``; neither gets a record.

Decoding (``decode``) refuses:

- a node or edge declared twice (D001);
- an incidence naming an undeclared edge (D003); an incidence naming an undeclared node (D002) in a complete file,
  or naming an undeclared derived ``_:`` node in any file (``to_hif`` declares every derived node); and a fact
  reference that does not resolve and is not ``khg-external`` in a file that may name what it does not hold (D002);
- an external reference in a complete file that is not a slice (P017);
- a derived node id that does not match its value, its (record id, bid) or its reference (D005);
- a schema id or hash that differs from the declared ones (D009);
- a repeated ``khg-bid`` in one edge (P016);
- in a directed file, an incidence without direction (P010);
- a direction that contradicts the usage's (S016), an undeclared relation (S001) or role (S002), and a malformed
  literal (its C or S codes): the decoder needs the usage and the literal's value.

A direction equal to the usage default is dropped, and an incidence weight, node weight or edge weight becomes
``extensions["hif:weight"]``. A ``role-position`` is read as layer R reads it, so an integral float is its integer
(``2.0`` is ``2``, F10). The header is rebuilt with ``content: "snapshot"``; metadata keys outside the declaration
block go to ``extensions["hif:metadata"]``.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from ..errors import KHGError, ValidationError, make_finding
from ..record import canonical_container, literal_binding_node_id, literal_node_id, ref_node_id, special_node_id
from ..schema import Schema
from ._doc import attrs_of, mapping, records
from .convention import role_position
from .encode import as_schema
from .profile import DECLARATION_KEYS, EDGE_FIELDS, ENTITY_FIELDS, METADATA, WEIGHT, external_allowed, id_key

__all__ = ["PROFILE_STEPS", "decode", "from_hif"]

#: The validator steps ``from_hif`` runs before decoding, and the loaders' ``validate="profile"``.
PROFILE_STEPS = ("j", "v", "h", "r", "p")
_SPECIAL_KINDS = ("somevalue", "novalue", "unbound")

Finding = dict[str, str]


class _Decoder:
    """One decoding pass over a document that passed layers H, R and P."""

    def __init__(self, doc: Mapping[str, Any], schema: Schema):
        self.doc, self.schema = doc, schema
        self.md = mapping(doc.get("metadata"))
        self.directed = doc.get("network-type") == "directed"
        self.external = external_allowed(self.md)  # the file may name entities and facts it does not hold
        self.out: list[Finding] = []
        self.nodes: dict[str, tuple[int, Mapping[str, Any]]] = {}
        self.entities: list[dict[str, Any]] = []
        self.edges: dict[str, tuple[int, dict[str, Any], bool]] = {}
        self.refs: list[tuple[int, str, str]] = []  # (incidence index, fact id, node id)

    def add(self, code: str, path: str, message: str) -> None:
        self.out.append(make_finding(code, path, message))

    # ------------------------------------------------------------------ metadata
    def pin(self) -> None:
        if self.md.get("khg-schema") != self.schema.ref:
            self.add("KHG-D009", "/metadata/khg-schema",
                     f"khg-schema {self.md.get('khg-schema')!r} is not the schema's {self.schema.ref!r}")
        if self.md.get("khg-schema-sha256") != self.schema.sha256:
            self.add("KHG-D009", "/metadata/khg-schema-sha256", "khg-schema-sha256 is not the schema's digest")

    def header(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": "header", "format": self.md.get("khg-record"),
                               "document_id": self.md.get("khg-document-id"), "schema": self.schema.header,
                               "content": "snapshot"}
        if "khg-complete" in self.md:
            out["complete"] = self.md["khg-complete"]
        extra = {k: copy.deepcopy(v) for k, v in self.md.items() if k not in DECLARATION_KEYS}
        if extra:
            out["extensions"] = {METADATA: extra}
        return out

    # ------------------------------------------------------------------ nodes and edges
    def extensions(self, target: dict[str, Any], attrs: Mapping[str, Any], item: Mapping[str, Any],
                   path: str) -> None:
        """``khg-extensions`` plus the record's ``weight`` as ``hif:weight`` into ``target["extensions"]``."""
        ext = attrs.get("khg-extensions")
        if "weight" not in item:
            if "khg-extensions" in attrs:
                target["extensions"] = copy.deepcopy(ext)
            return
        if "khg-extensions" in attrs and not isinstance(ext, Mapping):
            self.add("KHG-C010", f"{path}/attrs/khg-extensions", "khg-extensions is an object")
            return
        merged = copy.deepcopy(dict(ext)) if isinstance(ext, Mapping) else {}
        merged[WEIGHT] = item["weight"]
        target["extensions"] = merged

    def read_nodes(self) -> None:
        for j, node in records(self.doc, "nodes"):
            nid = node.get("node")
            if not isinstance(nid, str):
                continue  # P002
            if nid in self.nodes:
                self.add("KHG-D001", f"/nodes/{j}/node", f"node {nid!r} is declared twice")
                continue
            self.nodes[nid] = (j, node)
            self.node(j, nid, node)

    def node(self, j: int, nid: str, node: Mapping[str, Any]) -> None:
        attrs = attrs_of(node)
        kind = attrs.get("khg-kind")
        if kind == "entity":
            entity: dict[str, Any] = {"kind": "entity", "id": nid}
            for field, key in ENTITY_FIELDS:
                if key in attrs and field != "extensions":
                    entity[field] = copy.deepcopy(attrs[key])
            self.extensions(entity, attrs, node, f"/nodes/{j}")
            self.entities.append(entity)
        elif kind == "literal":
            self.literal_node(j, nid, attrs)
        elif kind == "fact-ref":
            ref = attrs.get("khg-ref")
            if not (isinstance(ref, str) and ref_node_id(ref) == nid):
                self.add("KHG-D005", f"/nodes/{j}/node", f"fact-ref node {nid!r} does not match khg-ref {ref!r}")
            if attrs.get("khg-external") and not self.external:
                self.add("KHG-P017", f"/nodes/{j}/attrs/khg-external", "an external fact reference in a complete file")
        elif kind not in _SPECIAL_KINDS:
            self.add("KHG-P013", f"/nodes/{j}/attrs/khg-kind", f"unknown node kind {kind!r}")

    def literal_node(self, j: int, nid: str, attrs: Mapping[str, Any]) -> None:
        """The literal must be well formed, and a ``_:lit:`` id must be the digest of its value (D005)."""
        literal: Any = attrs.get("khg-literal")
        try:
            want = literal_node_id(literal)
        except (ValueError, TypeError) as e:
            codes = e.codes if isinstance(e, KHGError) and e.codes else ("KHG-C004",)
            for code in codes:
                self.add(code, f"/nodes/{j}/attrs/khg-literal", str(e))
            return
        if nid.startswith("_:lit:") and nid != want:
            self.add("KHG-D005", f"/nodes/{j}/node", f"literal node {nid!r} does not match its value ({want})")

    def read_edges(self) -> None:
        for k, item in records(self.doc, "edges"):
            eid = item.get("edge")
            if not isinstance(eid, str):
                continue  # P002
            if eid in self.edges:
                self.add("KHG-D001", f"/edges/{k}/edge", f"edge {eid!r} is declared twice")
                continue
            attrs = attrs_of(item)
            record: dict[str, Any] = {"kind": "hyperedge", "id": eid}
            for field, key in EDGE_FIELDS:
                if key in attrs and field != "extensions":
                    record[field] = copy.deepcopy(attrs[key])
            self.extensions(record, attrs, item, f"/edges/{k}")
            record["bindings"] = []
            relation = record.get("relation")
            declared = isinstance(relation, str) and self.schema.has_relation(relation)
            if not declared:
                self.add("KHG-S001", f"/edges/{k}/attrs/relation", f"relation {relation!r} is not declared in "
                         f"{self.schema.ref}")
            self.edges[eid] = (k, record, declared)

    # ------------------------------------------------------------------ incidences
    def read_incidences(self) -> None:
        seen: set[tuple[Any, ...]] = set()
        for i, inc in records(self.doc, "incidences"):
            eid, nid = inc.get("edge"), inc.get("node")
            if not isinstance(eid, str) or eid not in self.edges:
                self.add("KHG-D003", f"/incidences/{i}/edge", f"edge {eid!r} is not declared")
                continue
            node = self.nodes.get(nid) if isinstance(nid, str) else None
            if node is None:
                node = self.undeclared(i, nid)
                if node is None:
                    continue
            edge = self.edges[eid]
            attrs = attrs_of(inc)
            bid, role = attrs.get("khg-bid"), attrs.get("role")
            key = (eid, id_key(bid))
            if key in seen:
                self.add("KHG-P016", f"/incidences/{i}/attrs/khg-bid", f"khg-bid {bid!r} is repeated in {eid!r}")
                continue
            seen.add(key)
            value = self.value(i, eid, bid, nid, node[1])
            direction = self.direction(i, edge, role, inc.get("direction"))
            if value is None:
                continue
            binding: dict[str, Any] = {"bid": bid, "role": role, "value": value}
            if "role-position" in attrs:
                position = role_position(attrs["role-position"])  # 2.0 is 2 (F10), as layer R read it
                binding["position"] = position if position is not None else attrs["role-position"]
            if direction is not None:
                binding["direction"] = direction
            self.extensions(binding, attrs, inc, f"/incidences/{i}")
            edge[1]["bindings"].append(binding)

    def undeclared(self, i: int, nid: Any) -> tuple[int, Mapping[str, Any]] | None:
        """The node an incidence names without a node record: in a file that may name what it does not hold, an
        entity the file does not hold (an id without the ``_:`` prefix, since ``to_hif`` declares every derived
        node), read as an entity node without attrs; otherwise D002 and None."""
        if isinstance(nid, str) and self.external and not nid.startswith("_:"):
            return -1, {"node": nid, "attrs": {"khg-kind": "entity"}}
        self.add("KHG-D002", f"/incidences/{i}/node", f"node {nid!r} is not declared")
        return None

    def value(self, i: int, eid: str, bid: Any, nid: str, node: Mapping[str, Any]) -> dict[str, Any] | None:
        """The binding value a node carries; None (with D005 for a derived id of another binding) when it cannot
        be decoded."""
        attrs = attrs_of(node)
        kind = attrs.get("khg-kind")
        if kind == "entity":
            return {"entity": nid}
        if kind == "literal":
            if nid.startswith("_:litb:") and literal_binding_node_id(eid, bid) != nid:
                self.add("KHG-D005", f"/incidences/{i}/node", f"{nid!r} is not the literal node of ({eid}, {bid})")
                return None
            return {"literal": copy.deepcopy(attrs.get("khg-literal"))}
        if kind == "fact-ref":
            ref = attrs.get("khg-ref")
            if not isinstance(ref, str):
                return None  # D005 on the node
            self.refs.append((i, ref, nid))
            return {"fact": ref}
        if kind in _SPECIAL_KINDS:
            if special_node_id(kind, eid, bid) != nid:
                self.add("KHG-D005", f"/incidences/{i}/node", f"{nid!r} is not the {kind} node of ({eid}, {bid})")
                return None
            if kind == "unbound":
                return {"unbound": copy.deepcopy(attrs.get("khg-unbound"))}
            return {"special": kind}
        return None  # P013 on the node

    def direction(self, i: int, edge: tuple[int, dict[str, Any], bool], role: Any, written: Any) -> str | None:
        """The binding's direction: the written one where the usage declares none; None when it equals the usage's
        (dropped) or is absent. P010, S002 and S016 are reported here."""
        if self.directed and written is None:
            self.add("KHG-P010", f"/incidences/{i}", "a directed file with an incidence without direction")
        k, record, declared = edge
        if not declared:
            return written  # S001 on the edge
        try:
            usage = self.schema.usage(record["relation"], role) if isinstance(role, str) else None
        except ValidationError:
            usage = None
        if usage is None:
            self.add("KHG-S002", f"/incidences/{i}/attrs/role",
                     f"role {role!r} is not allowed for {record['relation']!r}")
            return written
        default = usage.get("direction")
        if default is None:
            return written
        if written is not None and written != default:
            self.add("KHG-S016", f"/incidences/{i}/direction",
                     f"direction {written!r} contradicts the usage's {default!r} ({record['relation']}.{role})")
        return None

    def check_references(self) -> None:
        """A fact reference resolves to an edge of the file, or is external in a file that may name what it does
        not hold (D002)."""
        for i, ref, nid in self.refs:
            if ref in self.edges:
                continue
            if not (self.external and attrs_of(self.nodes[nid][1]).get("khg-external")):
                self.add("KHG-D002", f"/incidences/{i}/node", f"fact reference {ref!r} does not resolve")

    def run(self) -> tuple[dict[str, Any] | None, list[Finding]]:
        self.pin()
        self.read_nodes()
        self.read_edges()
        self.read_incidences()
        self.check_references()
        if any(f["severity"] == "error" for f in self.out):
            return None, self.out
        edges = [record for _, record, _ in self.edges.values()]
        return {"header": self.header(), "records": self.entities + edges}, self.out


def decode(hif: Mapping[str, Any], schema: Schema) -> tuple[dict[str, Any] | None, list[Finding]]:
    """Decode a HIF document that passed layers H, R and P into a C1 container, as written: entities in node
    order, then hyperedges in edge order, bindings in incidence order. Returns ``(container, findings)``; the
    container is None when a finding is an error. Never raises on a malformed document."""
    return _Decoder(hif, schema).run()


def from_hif(hif: Any, schema: Any = None) -> dict[str, Any]:
    """The canonical C1 container of a ``khg-hif`` file, 1.0.0 or 1.1.0 (§4.3).

    ``hif`` is a parsed document, raw ``bytes`` or a path; ``schema`` a ``Schema``, a schema document or a path,
    else the file's ``khg-schema-document``. Runs layers J, V, H, R and P, then decoding, and raises
    ``ValidationError`` with the codes of the first failure: D009 when there is no schema at all.
    """
    from ..validate.context import Context
    from ..validate.layers.j import parse
    from ..validate.runner import run

    doc, found = parse(hif, "hif")
    if found:
        raise ValidationError.from_findings(found)
    report = run(doc, kind="hif", steps=PROFILE_STEPS, stop="first")
    if not report.ok:
        raise ValidationError.from_findings(report.findings)
    sch, found = Context(kind="hif", doc=doc, schema=None if schema is None else as_schema(schema)).relation_schema()
    if sch is None:
        raise ValidationError.from_findings(found)
    container, found = decode(doc, sch)
    if container is None:
        raise ValidationError.from_findings(found)
    return canonical_container(container)
