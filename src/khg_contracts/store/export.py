"""Exports of a store (DESIGN §6.2): the header, the container, and the three formats.

- **Header.** The kept document header (``load`` keeps the container's, minus ``content`` and ``as_at``), else the
  one ``export(header=...)`` passes, else a computed one: ``document_id`` ``"store:<store_id>"``, the schema's
  ``{id, version, sha256}`` and ``complete`` by the D002 rule (every entity and fact value resolves among the
  exported records; S-EXP-009). ``content`` and ``as_at`` are always the export's own. The ``format`` is the lowest
  stamp the records need (``record.required_format``): a header that says ``khg-record/1.0.x`` is raised to
  ``khg-record/1.1.0`` when an exported record uses a 1.1 feature (ruling 22), so a 1.0 reader refuses the file with
  V001 rather than misreading it.
- **Formats.** ``khg-json`` is the canonical container (a dict); ``khg-jsonl`` its canonical text, one JSON text
  per line; ``hif`` the role-aware HIF file of ``hif.to_hif``. ``relations`` exports the closed slice of those
  relations (§4.6) in every format. HIF holds snapshots only.
- Records carry their store fields (``version``, ``recorded_at``, ``recorded_by``) and no ``derived`` block (an
  optional cache).
"""
from __future__ import annotations

import copy
from typing import Any, Collection, Iterable, Mapping, Sequence

from ..errors import ValidationError, make_finding
from ..hif import select_slice, to_hif
from ..record import FORMAT_1_1, canonical_container, required_format, serialize
from ..schema import Schema
from ._table import bound_nodes

__all__ = ["CONTENTS", "FORMATS", "LITERAL_NODES", "check_relations", "complete", "default_header", "export_header",
           "render"]

FORMATS = ("khg-json", "khg-jsonl", "hif")
CONTENTS = ("snapshot", "history")
LITERAL_NODES = ("shared", "per_binding")
#: The order of the header fields the export writes first; any other field keeps its place after them.
_HEADER_ORDER = ("kind", "format", "document_id", "schema", "content", "as_at", "complete")


def complete(records: Iterable[Mapping[str, Any]]) -> bool:
    """The D002 rule: every entity value names an exported entity and every fact value an exported hyperedge."""
    recs = [r for r in records if isinstance(r, Mapping)]
    held = {(r.get("kind"), r.get("id")) for r in recs}
    return all(("entity" if kind == "entity" else "hyperedge", target) in held
               for r in recs if r.get("kind") == "hyperedge" for _, kind, target in bound_nodes(r))


def default_header(store_id: str, schema: Schema, records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """The header of a store without a kept header."""
    records = list(records)
    return {"kind": "header", "format": required_format(records), "document_id": f"store:{store_id}",
            "schema": schema.header, "complete": complete(records)}


def export_header(kept: Mapping[str, Any] | None, records: Sequence[Mapping[str, Any]], *, schema: Schema,
                  store_id: str, content: str, as_at: str | None) -> dict[str, Any]:
    """The header of an export: ``kept`` (or the default header) with the export's ``content`` and ``as_at``."""
    base = copy.deepcopy(dict(kept)) if kept is not None else default_header(store_id, schema, records)
    base.pop("content", None)
    base.pop("as_at", None)
    base["content"] = content
    if as_at is not None:
        base["as_at"] = as_at
    if required_format(records) == FORMAT_1_1 and str(base.get("format", "")).startswith("khg-record/1.0."):
        base["format"] = FORMAT_1_1
    first = {k: base[k] for k in _HEADER_ORDER if k in base}
    return {**first, **{k: v for k, v in base.items() if k not in first}}


def check_relations(relations: Collection[str] | None, schema: Schema) -> list[str] | None:
    """The slice's relations, sorted and unique; S001 for an undeclared one."""
    if relations is None:
        return None
    if isinstance(relations, (str, bytes)):
        raise TypeError("relations is a collection of relation ids, not a string")
    out = sorted(set(relations))
    for rel in out:
        if not isinstance(rel, str) or not schema.has_relation(rel):
            raise ValidationError.from_findings([make_finding(
                "KHG-S001", "", f"relation {rel!r} of the slice is not declared in {schema.ref}")])
    return out


def render(container: Mapping[str, Any], format: str, schema: Schema, *, relations: list[str] | None = None,
           literal_nodes: str = "shared") -> str | dict[str, Any]:
    """The container in ``format``; ``relations`` makes it a closed slice."""
    if format == "hif":
        return to_hif(container, schema, relations=relations, literal_nodes=literal_nodes)
    doc = select_slice(container, relations) if relations is not None else container
    if format == "khg-jsonl":
        return serialize(doc, format="jsonl")
    return canonical_container(doc)
