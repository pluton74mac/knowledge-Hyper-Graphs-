"""Input checks of the scorers (DESIGN §9.2, §9.4, §9.6): a malformed input raises ``ValidationError``.

- **C4 items** run the draft schema ``khg-c4-items-0.1.0`` (layer I): I001 an unknown kind, I002 the item structure,
  I004 a memory question without ``stale_values`` or ``future_values``. A C1 value or record embedded in an item
  that fails its ``khg-record`` definition is reported as I003, with the C finding nested (§8.1). The S checks of
  embedded records run where the scorers read them (``embedded_error``).
- **System outputs** run ``khg-c5-io-1.0.0``; their codes are the schema's (C010, and the C codes of embedded
  values).
- **Extraction outputs** are C3 queue items (``run``, ``doc`` and ``payload``; Q001 without them) or C1 hyperedges
  whose evidence names one document.

Both schemas are run by jsonschema with a closed resolver over the packaged schemas; nothing is fetched.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from .. import data
from ..errors import ValidationError, make_finding

__all__ = ["C4_SCHEMA_ID", "C5_SCHEMA_ID", "Prediction", "c4_findings", "c5_findings", "check_items",
           "check_outputs", "embedded_error", "predictions"]

C4_SCHEMA_ID = "tag:khg-contracts,2026:schema/khg-c4-items/0.1.0"
C5_SCHEMA_ID = "tag:khg-contracts,2026:schema/khg-c5-io/1.0.0"

Finding = dict[str, Any]


def _refuse(uri: str) -> Any:
    raise LookupError(f"closed resolver: {uri} is not packaged")


def _code(schema: Any, keyword: str, default: str) -> str:
    c = schema.get("x-khg-code") if isinstance(schema, Mapping) else None
    if isinstance(c, str):
        return c
    if isinstance(c, Mapping):
        return c.get(keyword) or c.get("default") or default
    return default


def _pointer(parts: Iterable[Any]) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


@functools.cache
def _runner(schema_id: str, default: str) -> Callable[[Any], list[Finding]]:
    import jsonschema
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    docs = data.schema_documents()
    registry = Registry(retrieve=_refuse).with_resources(  # type: ignore[call-arg]
        [(sid, Resource.from_contents(doc, default_specification=DRAFT7)) for sid, doc in sorted(docs.items())])
    validator = jsonschema.Draft7Validator(docs[schema_id], registry=registry)

    def run(instance: Any) -> list[Finding]:
        errors = sorted(validator.iter_errors(instance), key=lambda e: (list(map(str, e.absolute_path)), e.message))
        return [make_finding(_code(e.schema, str(e.validator), default), _pointer(e.absolute_path), e.message)
                for e in errors]
    return run


def _prefixed(findings: list[Finding], prefix: str) -> list[Finding]:
    return [{**f, "path": prefix + f["path"]} for f in findings]


def c5_findings(record: Any, path: str = "") -> list[Finding]:
    """The findings of ``khg-c5-io-1.0.0`` on one system output ([] when it is valid)."""
    if not isinstance(record, Mapping):
        return [make_finding("KHG-J007", path, f"a system output is an object, not {type(record).__name__}")]
    return _prefixed(_runner(C5_SCHEMA_ID, "KHG-C010")(record), path)


def c4_findings(item: Any, path: str = "") -> list[Finding]:
    """The layer-I findings of the draft schema on one C4 item ([] when it is valid). A finding of an embedded C1
    value or record becomes I003 with the original under ``nested``."""
    if not isinstance(item, Mapping):
        return [make_finding("KHG-J007", path, f"a C4 item is an object, not {type(item).__name__}")]
    out = []
    for f in _prefixed(_runner(C4_SCHEMA_ID, "KHG-I002")(item), path):
        if f["code"].startswith("KHG-I"):
            out.append(f)
        else:
            nested = make_finding("KHG-I003", f["path"], f"embedded C1 content: {f['code']}: {f['message']}")
            nested["nested"] = f
            out.append(nested)
    return out


def _raise(findings: list[Finding]) -> None:
    if any(f["severity"] == "error" for f in findings):
        raise ValidationError.from_findings(findings)


def check_items(items: Iterable[Any], *, kinds: tuple[str, ...]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Check C4 items (layer I) and return ``(items of the wanted kinds, c4-header lines)``. Items of the other C4
    kinds are skipped, so a whole C4 file can be passed. Raises ``ValidationError`` on any finding."""
    wanted: list[dict[str, Any]] = []
    headers: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for n, item in enumerate(items):
        fs = c4_findings(item, f"/lines/{n}")
        findings += fs
        if fs:
            continue
        if item["kind"] in kinds:
            wanted.append(dict(item))
        elif item["kind"] == "c4-header":
            headers.append(dict(item))
    _raise(findings)
    return wanted, headers


def embedded_error(error: ValidationError, path: str) -> ValidationError:
    """An error met while reading a record embedded in a C4 item, re-raised as I003 with its findings nested."""
    inner = error.info.get("findings") or [make_finding(c, "", str(error)) for c in error.codes]
    out = []
    for f in inner:
        g = make_finding("KHG-I003", path, f"embedded C1 record: {f.get('code')}: {f.get('message', '')}")
        g["nested"] = dict(f)
        out.append(g)
    return ValidationError.from_findings(out)


def check_outputs(records: Iterable[Any], *, kind: str) -> list[dict[str, Any]]:
    """Check system outputs against ``khg-c5-io-1.0.0`` and their ``kind``; return them as a list."""
    out: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for n, r in enumerate(records):
        path = f"/lines/{n}"
        fs = c5_findings(r, path)
        if not fs and r.get("kind") != kind:
            fs = [make_finding("KHG-C010", path + "/kind", f"this scorer reads {kind} records, not {r.get('kind')}")]
        findings += fs
        if not fs:
            out.append(dict(r))
    _raise(findings)
    return out


# ------------------------------------------------------------------------------------------------ extraction outputs


@dataclass(frozen=True)
class Prediction:
    """One extracted fact: its unit ``(run_id, order_id)``, document, id (qid or record id), the C1 hyperedge and
    the entity records it carries."""

    run_id: str | None
    order_id: str | None
    doc_id: str
    pid: str
    record: Mapping[str, Any]
    entities: tuple[Mapping[str, Any], ...]


def _doc_of_record(record: Mapping[str, Any]) -> str | None:
    evidence = record.get("evidence")
    if not isinstance(evidence, list):
        return None
    ev = [e for e in evidence if isinstance(e, Mapping) and isinstance(e.get("source"), Mapping)]
    for pick in ([e for e in ev if e.get("type") == "extracted"], ev):
        docs = sorted({e["source"].get("doc_id") for e in pick if isinstance(e["source"].get("doc_id"), str)})
        if len(docs) == 1:
            return docs[0]
        if len(docs) > 1:
            return None
    return None


def predictions(items: Iterable[Any]) -> list[Prediction]:
    """Read extraction outputs: C3 queue items (``queue_items`` yields them, with or without their folded state)
    or C1 hyperedges whose evidence names exactly one document (their extracted evidence first). Raises
    ``ValidationError``: Q003 for another kind, Q001 for an item without ``run`` or ``doc``, C010 for a payload that
    is not a hyperedge or a hyperedge without a document."""
    out: list[Prediction] = []
    findings: list[Finding] = []
    for n, x in enumerate(items):
        path = f"/lines/{n}"
        if not isinstance(x, Mapping):
            findings.append(make_finding("KHG-J007", path, f"an output is an object, not {type(x).__name__}"))
            continue
        kind = x.get("kind")
        if kind == "queue-item":
            run, doc, payload = x.get("run"), x.get("doc"), x.get("payload")
            if not (isinstance(run, Mapping) and isinstance(run.get("run_id"), str)
                    and isinstance(run.get("order_id"), str) and isinstance(doc, Mapping)
                    and isinstance(doc.get("doc_id"), str)):
                findings.append(make_finding("KHG-Q001", path, "a queue item needs run {run_id, order_id} and "
                                             "doc {doc_id}"))
                continue
            if not (isinstance(payload, Mapping) and payload.get("kind") == "hyperedge"):
                findings.append(make_finding("KHG-C010", path + "/payload", "the payload is a C1 hyperedge"))
                continue
            ents = x.get("entities") or []
            pid = x.get("qid") if isinstance(x.get("qid"), str) else payload.get("id")
            out.append(Prediction(run["run_id"], run["order_id"], doc["doc_id"], str(pid), payload,
                                  tuple(e for e in ents if isinstance(e, Mapping))))
        elif kind == "hyperedge":
            doc_id = _doc_of_record(x)
            if doc_id is None:
                findings.append(make_finding("KHG-C010", path + "/evidence", "a predicted hyperedge names its "
                                             "document in the source.doc_id of its evidence (exactly one)"))
                continue
            out.append(Prediction(None, None, doc_id, str(x.get("id")), x, ()))
        else:
            findings.append(make_finding("KHG-Q003", path + "/kind", f"an extraction output is a queue-item or a "
                                         f"hyperedge, not {kind!r}"))
    _raise(findings)
    return out
