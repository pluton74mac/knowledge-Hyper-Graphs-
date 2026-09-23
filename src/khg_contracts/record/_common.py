"""Helpers shared by the ``record`` modules: value kinds, errors with registered codes, schema coercion."""
from __future__ import annotations

from typing import Any, Mapping, Union

from ..errors import ValidationError, make_finding
from ..jsonio import nfc
from ..schema import Schema

VALUE_KINDS = ("entity", "literal", "fact", "special", "unbound")
SPECIALS = ("somevalue", "novalue")
#: A ``Schema``, or a schema document (wrapped unchecked).
SchemaLike = Union[Schema, Mapping[str, Any]]


def fail(code: str, message: str, path: str = "") -> ValidationError:
    """A ``ValidationError`` carrying one error finding with a registered ``code``."""
    return ValidationError.from_findings([make_finding(code, path, message)])


def nfc_deep(obj: Any) -> Any:
    """A deep copy of a JSON value with every string, and every object key, in NFC. An object whose keys would
    collide under NFC keeps its keys as they are (canonical JSON reports that as S020)."""
    if isinstance(obj, str):
        return nfc(obj)
    if isinstance(obj, Mapping):
        items = [(k, nfc_deep(v)) for k, v in obj.items()]
        keys = [nfc(k) if isinstance(k, str) else k for k, _ in items]
        if len(set(keys)) == len(keys):
            return {k: v for k, (_, v) in zip(keys, items, strict=True)}
        return dict(items)
    if isinstance(obj, (list, tuple)):
        return [nfc_deep(x) for x in obj]
    return obj


def value_kind(value: Any) -> str:
    """The kind of a value: ``entity``, ``literal``, ``fact``, ``special`` or ``unbound`` (C001 otherwise)."""
    if not isinstance(value, Mapping) or len(value) != 1:
        raise fail("KHG-C001", f"a value has exactly one key, not {_describe(value)}")
    (kind,) = value.keys()
    if kind not in VALUE_KINDS:
        raise fail("KHG-C002", f"value kind {kind!r} is not one of {', '.join(VALUE_KINDS)}")
    return kind


def is_special(value: Any, which: str) -> bool:
    """True when ``value`` is ``{"special": which}``."""
    return isinstance(value, Mapping) and len(value) == 1 and value.get("special") == which


def as_schema(schema: SchemaLike) -> Schema:
    """A ``Schema``; a mapping is wrapped unchecked (``load_schema`` checks documents)."""
    if isinstance(schema, Schema):
        return schema
    if isinstance(schema, Mapping):
        return Schema(schema)
    raise TypeError(f"expected a Schema or a schema document, not {type(schema).__name__}")


def hyperedge(record: Any) -> Mapping[str, Any]:
    """``record`` when it is a hyperedge record; ``ValueError`` otherwise."""
    if not isinstance(record, Mapping) or record.get("kind") != "hyperedge":
        kind = record.get("kind") if isinstance(record, Mapping) else type(record).__name__
        raise ValueError(f"expected a hyperedge record, not {kind!r}")
    return record


def bindings(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The bindings of a hyperedge (C010 when they are not a list of objects)."""
    bs = record.get("bindings")
    if not isinstance(bs, list) or not all(isinstance(b, Mapping) for b in bs):
        raise fail("KHG-C010", f"{record.get('id')!r}: bindings must be a list of objects", "/bindings")
    return bs


def _describe(value: Any) -> str:
    if isinstance(value, Mapping):
        return f"{len(value)} keys ({', '.join(sorted(map(str, value)))})" if value else "no key"
    return type(value).__name__
