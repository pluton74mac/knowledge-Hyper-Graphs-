"""``v0_sample_to_v1``: the knowledge base's ``schemas/sample.hif.json`` (``v0-sample``) to ``khg-record/1.0.0``
(DESIGN §11.3).

``v0_sample_to_v1(hif) -> Migration(schema, container, report)``. Every choice that fixes a key is pinned:

- **the file** is read, never modified;
- **relations, roles and node types** give a generated schema ``kb-sample`` 1.0.0. Each observed role is a core
  usage, sorted by role id, whose fillers are the observed types. ``min`` is 1 if the role occurs in every edge of
  the relation, else 0; ``max`` is 1 unless the role repeats in an edge, else null. The direction is the observed
  one when all incidences agree;
- **``valid-from``** gives an interval time model (``start_time``, ``end_time``) with time usages of direction
  ``tail``, and the value becomes a ``start_time`` binding at precision 11 (F017);
- **incidences**: one binding per incidence, with bids ``b1``... in canonical binding order;
- **``source``** becomes evidence ``e1`` = ``{type: imported, mode: automatic, source: {doc_id: <the source>}}``;
- **``arity``** is checked against the C1 rule and dropped (F015); a stored arity that disagrees raises D015;
- **``weight``** becomes ``extensions["hif:weight"]``, never confidence (F006);
- **``schema`` and ``conventions``** are replaced by the declaration block (F016). The other metadata keys go to
  ``extensions["hif:metadata"]``; the header's ``document_id`` is ``kb-sample`` and ``complete`` is true.

Beyond the sample, a binding keeps its incidence's direction when the incidences of its role disagree (its usage
then has none), so no direction is lost. The report lists F017, F006 and F015 per edge, in edge order, then F016.

The input is checked first (``_v0``: J, H and the format). The output is checked like any other: the generated
schema by ``load_schema`` (V, M) and the container by ``validate_container`` (V, C, S, D). Every refusal is a
``ValidationError`` with registered codes.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping, NamedTuple

from ..errors import ValidationError, make_finding
from ..hif._doc import attrs_of, mapping, records
from ..hif.profile import METADATA, WEIGHT
from ..record import FORMAT as RECORD_FORMAT
from ..record import arity, binding_sort_key, canonical_container
from ..schema import FORMAT as SCHEMA_FORMAT
from ..schema import Schema, load_schema
from ._v0 import REPLACED_METADATA, read, start_literal

__all__ = ["DOCUMENT_ID", "REPORT_FORMAT", "SCHEMA_ID", "SCHEMA_LABEL", "SCHEMA_VERSION", "V0_SAMPLE", "Migration",
           "generate_schema", "v0_sample_to_v1"]

#: The ``--from`` id of ``khg-migrate`` and the ``from`` of the report.
V0_SAMPLE = "v0-sample"
REPORT_FORMAT = "khg-migration-report/1.0.0"
SCHEMA_ID, SCHEMA_VERSION = "kb-sample", "1.0.0"
SCHEMA_LABEL = "Generated from schemas/sample.hif.json (v0)"
DOCUMENT_ID = "kb-sample"
START, END = "start_time", "end_time"
_TIME_FILLERS = ({"literal": "time"},)


class Migration(NamedTuple):
    """The result: the generated relation-type schema document, the canonical C1 container and the
    ``khg-migration-report/1.0.0`` report ``{format, from, findings}``."""

    schema: dict[str, Any]
    container: dict[str, Any]
    report: dict[str, Any]


def v0_sample_to_v1(hif: Any) -> Migration:
    """Migrate a ``v0-sample`` file (a parsed document, raw bytes or a path) to ``khg-record/1.0.0``.

    Raises ``ValidationError``: J, H and the format's codes on the input (``_v0``), with paths into it; V and M codes
    on the generated schema and V, C, S and D codes on the container, with paths into the document that
    ``info["schema"]`` or ``info["container"]`` holds; D015 when a stored ``arity`` disagrees with the C1 arity.
    """
    doc = read(hif)
    schema_doc = generate_schema(doc)
    try:
        schema = load_schema(schema_doc)
    except ValidationError as e:
        if not e.info.get("findings"):
            raise
        raise _refusal(e.info["findings"], "the generated schema", schema=schema_doc) from None
    container = canonical_container({"header": _header(doc, schema), "records": _records(doc, schema)})
    _check_output(container, schema)
    findings = _edge_findings(doc, container, schema)
    replaced = [k for k in REPLACED_METADATA if k in mapping(doc.get("metadata"))]
    if replaced:
        findings.append({"code": "KHG-F016",
                         "message": f"metadata {' and '.join(replaced)} replaced by the declaration block"})
    return Migration(schema_doc, container, {"format": REPORT_FORMAT, "from": V0_SAMPLE, "findings": findings})


# ------------------------------------------------------------------------------------------------ the schema


def generate_schema(doc: Mapping[str, Any]) -> dict[str, Any]:
    """The relation-type schema of a v0 document that passed the format checks (§11.3), unchecked."""
    relation_of = {e["edge"]: attrs_of(e)["relation"] for _, e in records(doc, "edges")}
    edges_of: dict[str, list[str]] = {}
    for edge, rel in relation_of.items():
        edges_of.setdefault(rel, []).append(edge)
    types = {n["node"]: attrs_of(n)["type"] for _, n in records(doc, "nodes")}
    observed: dict[str, dict[str, list[Mapping[str, Any]]]] = {}
    for _, inc in records(doc, "incidences"):
        observed.setdefault(relation_of[inc["edge"]], {}).setdefault(attrs_of(inc)["role"], []).append(inc)
    timed = {relation_of[e["edge"]] for _, e in records(doc, "edges") if "valid-from" in attrs_of(e)}
    roles: set[str] = set()
    relations = []
    for rel in sorted(observed):
        relation: dict[str, Any] = {"id": rel, "roles": [_usage(role, observed[rel][role], edges_of[rel], types)
                                                         for role in sorted(observed[rel])]}
        roles.update(observed[rel])
        if rel in timed:
            relation["time"] = {"model": "interval", "start": START, "end": END}
            relation["roles"] += [_time_usage(START), _time_usage(END)]
            roles.update((START, END))
        relations.append(relation)
    return {"kind": "relation-schema", "format": SCHEMA_FORMAT, "id": SCHEMA_ID, "version": SCHEMA_VERSION,
            "label": SCHEMA_LABEL, "entity_types": [{"id": t} for t in sorted(set(types.values()))],
            "roles": [{"id": r} for r in sorted(roles)], "relations": relations}


def _usage(role: str, incidences: list[Mapping[str, Any]], relation_edges: list[str],
           types: Mapping[str, str]) -> dict[str, Any]:
    per_edge: dict[str, int] = {}
    for inc in incidences:
        per_edge[inc["edge"]] = per_edge.get(inc["edge"], 0) + 1
    usage: dict[str, Any] = {
        "role": role, "slot": "core", "fillers": [{"entity": sorted({types[inc["node"]] for inc in incidences})}],
        "min": 1 if set(per_edge) == set(relation_edges) else 0,
        "max": None if max(per_edge.values()) > 1 else 1}
    directions = {inc.get("direction") for inc in incidences}
    if len(directions) == 1 and None not in directions:
        usage["direction"] = next(iter(directions))
    return usage


def _time_usage(role: str) -> dict[str, Any]:
    return {"role": role, "slot": "time", "fillers": [dict(f) for f in _TIME_FILLERS], "min": 0, "max": 1,
            "direction": "tail"}


# ------------------------------------------------------------------------------------------------ the container


def _header(doc: Mapping[str, Any], schema: Schema) -> dict[str, Any]:
    header: dict[str, Any] = {"kind": "header", "format": RECORD_FORMAT, "document_id": DOCUMENT_ID,
                              "schema": schema.header, "content": "snapshot", "complete": True}
    kept = {k: copy.deepcopy(v) for k, v in mapping(doc.get("metadata")).items() if k not in REPLACED_METADATA}
    if kept:
        header["extensions"] = {METADATA: kept}
    return header


def _records(doc: Mapping[str, Any], schema: Schema) -> list[dict[str, Any]]:
    """The entities in node order, then the hyperedges in edge order (the caller puts them in canonical order)."""
    out: list[dict[str, Any]] = []
    for _, node in records(doc, "nodes"):
        attrs = attrs_of(node)
        entity: dict[str, Any] = {"kind": "entity", "id": node["node"], "types": [attrs["type"]]}
        if "label" in attrs:
            entity["label"] = attrs["label"]
        out.append(entity)
    incidences: dict[str, list[Mapping[str, Any]]] = {}
    for _, inc in records(doc, "incidences"):
        incidences.setdefault(inc["edge"], []).append(inc)
    for _, edge in records(doc, "edges"):
        out.append(_hyperedge(edge, incidences.get(edge["edge"], []), schema))
    return out


def _hyperedge(edge: Mapping[str, Any], incidences: list[Mapping[str, Any]], schema: Schema) -> dict[str, Any]:
    attrs = attrs_of(edge)
    relation = attrs["relation"]
    bindings = [_binding(inc, relation, schema) for inc in incidences]
    if "valid-from" in attrs:
        bindings.append({"bid": None, "role": START, "value": {"literal": start_literal(attrs["valid-from"])}})
    bindings.sort(key=binding_sort_key)
    for n, b in enumerate(bindings, 1):
        b["bid"] = f"b{n}"
    record: dict[str, Any] = {
        "kind": "hyperedge", "id": edge["edge"], "relation": relation, "status": "asserted", "bindings": bindings,
        "evidence": [{"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": attrs["source"]}}]}
    if "weight" in edge:
        record["extensions"] = {WEIGHT: edge["weight"]}
    return record


def _binding(inc: Mapping[str, Any], relation: str, schema: Schema) -> dict[str, Any]:
    """One binding per incidence; it keeps the incidence's direction only where the usage has none."""
    role = attrs_of(inc)["role"]
    binding: dict[str, Any] = {"bid": None, "role": role, "value": {"entity": inc["node"]}}
    direction = inc.get("direction")
    if direction is not None and schema.usage(relation, role).get("direction") is None:
        binding["direction"] = direction
    return binding


def _check_output(container: dict[str, Any], schema: Schema) -> None:
    """``validate_container`` on the migrated container; each error names the record it is in."""
    from ..validate import validate_container

    result = validate_container(container, schema=schema)
    if result["ok"]:
        return
    recs = container["records"]
    for f in result["findings"]:
        parts = f["path"].split("/")
        if len(parts) > 2 and parts[1] == "records" and parts[2].isdigit() and int(parts[2]) < len(recs):
            f["message"] = f"record {recs[int(parts[2])].get('id')!r}: {f['message']}"
    raise _refusal(result["findings"], "the migrated container", container=container)


def _refusal(findings: list[dict[str, Any]], what: str, **info: Any) -> ValidationError:
    """A ``ValidationError`` on a generated document: the messages say which one, and ``info`` holds it."""
    return ValidationError.from_findings([dict(f, message=f"{what}: {f.get('message', '')}") for f in findings],
                                         **info)


# ------------------------------------------------------------------------------------------------ the report


def _edge_findings(doc: Mapping[str, Any], container: Mapping[str, Any], schema: Schema) -> list[dict[str, Any]]:
    """F017, F006 and F015 per edge, in edge order; D015 (raised) for every stored arity that disagrees."""
    by_id = {r["id"]: r for r in container["records"] if r["kind"] == "hyperedge"}
    out: list[dict[str, Any]] = []
    disagree = []
    for k, edge in records(doc, "edges"):
        eid, attrs = edge["edge"], attrs_of(edge)
        if "valid-from" in attrs:
            out.append({"code": "KHG-F017", "edge": eid, "message": "valid-from became a start_time binding"})
        if "weight" in edge:
            out.append({"code": "KHG-F006", "edge": eid, "message": "weight kept as extensions hif:weight"})
        if "arity" not in attrs:
            continue
        stored, derived = attrs["arity"], arity(by_id[eid], schema)["arity"]
        if isinstance(stored, bool) or not isinstance(stored, (int, float)) or stored != derived:
            disagree.append(make_finding("KHG-D015", f"/edges/{k}/attrs/arity",
                                         f"{eid}: the stored arity {stored!r} disagrees with the C1 arity {derived}"))
        else:
            out.append({"code": "KHG-F015", "edge": eid, "message": f"stored arity {stored} checked and dropped"})
    if disagree:
        raise ValidationError.from_findings(disagree)
    return out
