"""The validator: layers J to I, the code registry and the offline engines (DESIGN §8, §10.2).

``validate(obj_or_path, *, kind="auto", schema=None, doc_texts=None, bases=None, engine="jsonschema")`` returns
``{ok, findings: [{code, severity, layer, path, message}]}`` and never raises on bad input. The kinds and their
pipelines:

| Kind | Layers, in order |
|---|---|
| ``record``, ``container`` (C1) | J V C S D |
| ``hif`` (with the profile) | J V H R P D C S (D first decodes; the cross-record D checks run after S) |
| ``role-convention`` | J H R |
| ``schema`` (relation-type schema) | J V M |
| ``queue`` | J V Q C S D (C and S on the payloads) |
| ``item`` (C4) | J V I |

``validate_record``, ``validate_container``, ``validate_hif``, ``validate_queue`` and ``validate_item`` fix the kind.
``ok`` is true when no finding is an error: warnings (S024 with a warning constraint, S003 on candidates, L008)
never invalidate. The layer rule, the registry and the engines are in ``runner``, ``registry`` and ``engines``;
``runner.run`` gives the full ``Report``.
"""
from __future__ import annotations

from typing import Any

from .engines import ENGINES
from .layers import KINDS, PIPELINES
from .registry import Code, Registry, registry
from .runner import Report, Result, first_rejecting_layer, pipeline_letters, run

__all__ = [
    "ENGINES",
    "KINDS",
    "PIPELINES",
    "Code",
    "Registry",
    "Report",
    "Result",
    "first_rejecting_layer",
    "pipeline_letters",
    "registry",
    "run",
    "validate",
    "validate_container",
    "validate_hif",
    "validate_item",
    "validate_queue",
    "validate_record",
]


def validate(obj_or_path: Any, *, kind: str = "auto", schema: Any = None, doc_texts: Any = None, bases: Any = None,
             engine: str = "jsonschema") -> Result:
    """Validate one input through its kind's pipeline; ``{ok, findings}``.

    ``obj_or_path`` is a path, raw ``bytes``, or a parsed input (a dict; a list of line dicts for a queue or C4
    file). ``kind`` is ``auto`` or one of ``record``, ``container``, ``hif``, ``role-convention``, ``schema``,
    ``queue`` and ``item``. ``schema`` is the relation-type schema (a ``Schema``, a document or a path); without it
    a container or HIF file uses the schema it embeds. ``doc_texts`` maps a ``doc_id`` (or a ``doc_sha256``) to the
    document text for the span check (S021), which reads the text an evidence's ``doc_sha256`` hashes; ``bases``
    gives a queue's base containers. ``engine`` is ``jsonschema`` (every violation) or
    ``fastjsonschema`` (the first one).
    """
    return run(obj_or_path, kind=kind, schema=schema, doc_texts=doc_texts, bases=bases, engine=engine).result()


def validate_record(record: Any, *, schema: Any = None, doc_texts: Any = None, bases: Any = None,
                    engine: str = "jsonschema") -> Result:
    """``validate`` with ``kind="record"``: one C1 record (J V C S D)."""
    return validate(record, kind="record", schema=schema, doc_texts=doc_texts, bases=bases, engine=engine)


def validate_container(container: Any, *, schema: Any = None, doc_texts: Any = None, bases: Any = None,
                       engine: str = "jsonschema") -> Result:
    """``validate`` with ``kind="container"``: a C1 container, ``.khg.json`` or ``.khg.jsonl`` (J V C S D)."""
    return validate(container, kind="container", schema=schema, doc_texts=doc_texts, bases=bases, engine=engine)


def validate_hif(hif: Any, *, schema: Any = None, doc_texts: Any = None, bases: Any = None,
                 engine: str = "jsonschema") -> Result:
    """``validate`` with ``kind="hif"``: a HIF file under the ``khg-hif/1.0.0`` profile (J V H R P D C S). A file
    without ``khg-profile`` passes V and is P001."""
    return validate(hif, kind="hif", schema=schema, doc_texts=doc_texts, bases=bases, engine=engine)


def validate_queue(q: Any, *, schema: Any, bases: Any = None, doc_texts: Any = None,
                   engine: str = "jsonschema") -> Result:
    """``validate`` with ``kind="queue"``: a C3 queue file (J V Q C S D). ``schema`` is required; ``bases``
    supplies the base container that the header names (Q012)."""
    return validate(q, kind="queue", schema=schema, doc_texts=doc_texts, bases=bases, engine=engine)


def validate_item(items: Any, *, schema: Any = None, doc_texts: Any = None, bases: Any = None,
                  engine: str = "jsonschema") -> Result:
    """``validate`` with ``kind="item"``: a C4 items file (J V I)."""
    return validate(items, kind="item", schema=schema, doc_texts=doc_texts, bases=bases, engine=engine)
