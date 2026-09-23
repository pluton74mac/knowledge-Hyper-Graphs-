"""The context one validation run passes from layer to layer (DESIGN §8.1).

``Context`` holds the input, the caller's arguments and ``state``, a dict where a layer leaves results for later
layers of the same run. The keys in use:

- ``"c1"``: the C1 container that layers C, S and D check in a HIF run, set by decoding (``d_decode``);
- ``"schema"``: the relation-type schema of the run, set by ``Context.relation_schema``;
- ``"entities"``, ``"facts"``: the latest entity and hyperedge records of the container by id, set by layer S;
- ``"queue_base"``: the verified base container of a queue, set by ``Context.queue_base``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from ..errors import make_finding
from ..record import container_sha256
from ..schema import Schema, check_schema

__all__ = ["SCHEMA_PATHS", "Context", "prefixed"]

Finding = dict[str, str]

#: Where a kind declares its relation-type schema: the path of a D009 finding when none is available.
SCHEMA_PATHS: Mapping[str, str] = MappingProxyType({
    "record": "", "container": "/header/schema", "hif": "/metadata/khg-schema", "queue": "/lines/0/schema",
    "item": "/lines/0/schema"})


def prefixed(findings: list[Finding], path: str) -> list[Finding]:
    """The findings with ``path`` put before their paths (they are changed in place and returned)."""
    for f in findings:
        f["path"] = path + f["path"]
    return findings


@dataclass
class Context:
    """One run: the input kind, the parsed input (``doc``: a dict, or a list of line dicts for a queue or C4
    file), the engine, the relation-type schema the caller passed, the document texts, the base containers by
    ``document_id``, and ``state``."""

    kind: str
    source: Any = None
    doc: Any = None
    engine: str = "jsonschema"
    schema: Schema | None = None
    doc_texts: Mapping[str, str] = field(default_factory=dict)
    bases: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)

    @property
    def container(self) -> Mapping[str, Any] | None:
        """The C1 container that layers C, S and D check: the input of a container run, the decoded container of a
        HIF run (``state["c1"]``), None for the other kinds."""
        if self.kind == "container":
            return self.doc if isinstance(self.doc, Mapping) else None
        if self.kind == "hif":
            return self.state.get("c1")
        return None

    def relation_schema(self) -> tuple[Schema | None, list[Finding]]:
        """The relation-type schema of the run and the findings of resolving it, which only the first caller gets
        (so they are reported once). The schema is the caller's, else the one the input carries: the first
        embedded ``relation-schema`` record of a container, or a HIF file's ``khg-schema-document``. An embedded
        schema must pass ``check_schema`` (its V and M findings are reported at its path). None, with D009, when
        there is no schema."""
        if "schema" in self.state:
            return self.state["schema"], []
        schema: Schema | None = self.schema
        findings: list[Finding] = []
        if schema is None:
            doc, path = self._carried_schema()
            if doc is not None:
                findings = prefixed(check_schema(doc, engine=self.engine), path)
                if not any(f["severity"] == "error" for f in findings):
                    schema = Schema(doc)
            else:
                findings = [make_finding("KHG-D009", SCHEMA_PATHS.get(self.kind, ""),
                                         "no relation-type schema supplied and none embedded")]
        self.state["schema"] = schema
        return schema, findings

    def _carried_schema(self) -> tuple[Any, str]:
        """The schema document the input carries and its path, or (None, "")."""
        if self.kind == "container" and isinstance(self.doc, Mapping):
            records = self.doc.get("records")
            for i, r in enumerate(records if isinstance(records, list) else []):
                if isinstance(r, Mapping) and r.get("kind") == "relation-schema":
                    return r, f"/records/{i}"
        if self.kind == "hif" and isinstance(self.doc, Mapping):
            md = self.doc.get("metadata")
            if isinstance(md, Mapping) and isinstance(md.get("khg-schema-document"), Mapping):
                return md["khg-schema-document"], "/metadata/khg-schema-document"
        return None, ""

    def queue_base(self) -> Mapping[str, Any] | None:
        """The base container a queue header names, when ``bases`` supplies it under its ``document_id`` and its
        ``record.container_sha256`` equals the header's ``base.sha256``; None otherwise (Q012 is layer Q's)."""
        if "queue_base" in self.state:
            return self.state["queue_base"]
        base = None
        lines = self.doc if isinstance(self.doc, list) else []
        header = lines[0] if lines and isinstance(lines[0], Mapping) else {}
        pin = header.get("base") if header.get("kind") == "queue-header" else None
        if isinstance(pin, Mapping) and isinstance(pin.get("document_id"), str):
            candidate = self.bases.get(pin["document_id"])
            if candidate is not None:
                try:
                    if container_sha256(candidate) == pin.get("sha256"):
                        base = candidate
                except (ValueError, TypeError, KeyError):
                    base = None
        self.state["queue_base"] = base
        return base
