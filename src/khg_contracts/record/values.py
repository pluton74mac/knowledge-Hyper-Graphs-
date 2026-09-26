"""Values and typed literals: canonical forms, value identity and literal labels (DESIGN §2.3, §4.2).

- The **canonical form** of a literal keeps it as written: the calendar defaults to ``gregorian`` (the Julian
  calendar stays Julian), strings are NFC and a language tag is lower case. Without the checks (``strict=False``, as
  ``normalize`` writes a record; 1.1, ruling 22) it also writes a decimal given in another writing (``1.50``, ``-0``,
  ``1.5e3``, a JSON number) in C1's form (``canonical_decimal``), and zeroes the components of a time literal below
  its precision, which its window does not read. The checks still refuse those writings (C004, S006).
- **Value identity** is what equality, hashing, keys and refinement compare. A time literal's identity is
  ``{datatype: "time", window: [lo, hi), precision}`` on the proleptic Gregorian line, so the Julian and the
  Gregorian writing of one day are one value; every other literal is its canonical form; an entity or fact is its
  id.
- The **label** of a literal is ``time/precision`` (plus `` (Julian)``), the amount plus the unit (plus the
  bounds), ``value@lang``, ``lat,lon``, ``true``/``false``, or the value.
"""
from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .. import jsonio
from ._common import SPECIALS, fail, nfc_deep, value_kind
from .windows import CALENDARS, JULIAN_BEFORE, YEAR_DIGITS, format_instant, parse_time, window_seconds

__all__ = [
    "DATATYPES",
    "canonical_decimal",
    "canonical_literal",
    "canonical_value",
    "decimal",
    "identity_key",
    "literal_identity",
    "literal_label",
    "value_identity",
    "values_equal",
]

DATATYPES = ("time", "quantity", "string", "lang_string", "boolean", "iri", "geo")
_DECIMAL = re.compile(r"\+0|[+-](0\.[0-9]*[1-9]|[1-9][0-9]*(\.[0-9]*[1-9])?)")
#: A decimal in a looser writing: an optional sign, digits with an optional fraction, an optional exponent.
_LOOSE_DECIMAL = re.compile(r"[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?")
#: The longest canonical decimal ``canonical_decimal`` writes; a writing that would give more is left as it is.
MAX_DECIMAL_CHARS = 1000
#: The fields of each datatype that hold C1 decimals.
DECIMAL_FIELDS = {"quantity": ("amount", "lower", "upper"), "geo": ("lat", "lon", "precision")}
#: A time in Wikibase form, and the precision from which each of month, day, hour, minute and second is written.
_TIME_FORM = re.compile(r"([+-][0-9]{4,%d})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z" % YEAR_DIGITS)
_WRITTEN_FROM = (10, 11, 12, 13, 14)
_YEAR = re.compile(r"([+-])([0-9]{4,%d})-" % YEAR_DIGITS)  # a longer year is C004 (parse_time)


def decimal(text: Any) -> Decimal:
    """A C1 decimal string (``+0``, ``+3.5``, ``-0.25``: signed, no redundant zeros) as a ``Decimal`` (C004)."""
    if not isinstance(text, str) or not _DECIMAL.fullmatch(text):
        raise fail("KHG-C004", f"decimal {text!r} is not a signed decimal string such as +3.5")
    return Decimal(text)


def canonical_decimal(x: Any) -> Any:
    """``x`` in C1's decimal form (``+1.5``, ``-0.25``, ``+0``: a sign, no redundant zeros, no exponent) when it is a
    decimal string in another writing (``1.50``, ``-0``, ``.5``, ``1.5e3``) or a finite JSON number (an int, or a float
    by its shortest decimal writing, ``repr``); anything else, and a writing whose canonical form would exceed
    ``MAX_DECIMAL_CHARS`` characters, is returned as it is. The canonical form of a canonical decimal is itself."""
    if isinstance(x, bool):
        return x
    try:
        if isinstance(x, int):
            d = Decimal(x)
        elif isinstance(x, float):
            if not math.isfinite(x):
                return x
            d = Decimal(repr(x))
        elif isinstance(x, str) and _LOOSE_DECIMAL.fullmatch(x):
            d = Decimal(x)
        else:
            return x
    except (InvalidOperation, ValueError):  # pragma: no cover - the pattern admits only what Decimal reads
        return x
    sign, digits, exponent = d.as_tuple()
    text = "".join(map(str, digits)).lstrip("0")
    if not text:
        return "+0"
    exp = int(exponent)
    size = len(text) + max(exp, 0) if exp >= 0 else max(len(text), -exp) + 1
    if size > MAX_DECIMAL_CHARS:
        return x
    if exp >= 0:
        whole, frac = text + "0" * exp, ""
    elif len(text) > -exp:
        whole, frac = text[:exp], text[exp:]
    else:
        whole, frac = "0", "0" * (-exp - len(text)) + text
    frac = frac.rstrip("0")
    return ("-" if sign else "+") + whole + ("." + frac if frac else "")


def _zero_below_precision(time: Any, precision: Any) -> Any:
    """A Wikibase time with its components below ``precision`` (an int 0-14) set to zero; anything else as it is."""
    m = _TIME_FORM.fullmatch(time) if isinstance(time, str) else None
    if m is None or isinstance(precision, bool) or not isinstance(precision, int) or not 0 <= precision <= 14:
        return time
    year, *parts = m.groups()
    mo, d, hh, mi, ss = (p if precision >= needed else "00" for p, needed in zip(parts, _WRITTEN_FROM, strict=True))
    return f"{year}-{mo}-{d}T{hh}:{mi}:{ss}Z"


def _gregorian_by_default(time: Any) -> bool:
    """True when a literal without calendar may take the default (a written year from 1583 on)."""
    m = _YEAR.match(time) if isinstance(time, str) else None
    return bool(m) and m.group(1) == "+" and int(m.group(2)) >= JULIAN_BEFORE


def _strings(lit: Mapping[str, Any], *names: str) -> None:
    for name in names:
        if not isinstance(lit.get(name), str):
            raise fail("KHG-C004", f"{lit.get('datatype')} literal: {name} must be a string")


def _check(lit: Mapping[str, Any]) -> None:
    dt = lit.get("datatype")
    if dt not in DATATYPES:
        raise fail("KHG-C002", f"datatype {dt!r} is not one of {', '.join(DATATYPES)}")
    if dt == "time":
        if "calendar" in lit and lit["calendar"] not in CALENDARS:
            raise fail("KHG-C004", f"calendar {lit['calendar']!r} is not gregorian or julian")
        parse_time(lit.get("time"), lit.get("precision"), lit.get("calendar"))
    elif dt == "quantity":
        _strings(lit, "unit")
        decimal(lit.get("amount"))
        if ("lower" in lit) != ("upper" in lit):
            raise fail("KHG-C004", "quantity bounds come as a pair: lower and upper")
        for k in ("lower", "upper"):
            if k in lit:
                decimal(lit[k])
    elif dt in ("string", "iri"):
        _strings(lit, "value")
    elif dt == "lang_string":
        _strings(lit, "value", "lang")
    elif dt == "boolean":
        if not isinstance(lit.get("value"), bool):
            raise fail("KHG-C004", "boolean literal: value must be true or false")
    else:  # geo
        _strings(lit, "globe")
        for k in ("lat", "lon", "precision"):
            decimal(lit.get(k))


def canonical_literal(literal: Mapping[str, Any], *, strict: bool = True) -> dict[str, Any]:
    """The canonical written form of a literal (a new dict).

    With ``strict`` (the default) the literal is checked: C002 for an unknown datatype, C004 for its structure, S006
    for a time literal out of range. With ``strict=False`` nothing is checked, a decimal is written in C1's form
    (``canonical_decimal``), the components of a time below its precision are zeroed, and whatever cannot be
    normalised is kept as written (``normalize`` uses this).
    """
    if not isinstance(literal, Mapping):
        if strict:
            raise fail("KHG-C004", f"a literal is an object, not {type(literal).__name__}")
        return nfc_deep(literal)
    out: dict[str, Any] = nfc_deep(literal)
    dt = out.get("datatype")
    if dt == "lang_string" and isinstance(out.get("lang"), str):
        out["lang"] = out["lang"].lower()
    if dt == "time":
        p = out.get("precision")
        if isinstance(p, float) and p.is_integer():
            out["precision"] = int(p)
        if "calendar" not in out and _gregorian_by_default(out.get("time")):
            out["calendar"] = "gregorian"
    if strict:
        _check(out)
        return out
    # normalize's lexical canonical forms (1.1, ruling 22): what the checks above would refuse is written in C1's form
    if dt == "time":
        out["time"] = _zero_below_precision(out.get("time"), out.get("precision"))
    for name in DECIMAL_FIELDS.get(dt, ()):
        if name in out:
            out[name] = canonical_decimal(out[name])
    return out


def literal_identity(literal: Mapping[str, Any]) -> dict[str, Any]:
    """The identity of a literal: ``{datatype: "time", window: [lo, hi], precision}`` for a time literal, else
    its canonical form."""
    c = canonical_literal(literal)
    if c["datatype"] != "time":
        return c
    lo, hi = window_seconds(c)
    return {"datatype": "time", "window": [format_instant(lo), format_instant(hi)], "precision": c["precision"]}


def _id(value: Mapping[str, Any], kind: str) -> str:
    i = value[kind]
    if not isinstance(i, str):
        raise fail("KHG-C010", f"{kind} value: the id must be a string, not {type(i).__name__}")
    return jsonio.nfc(i)


def canonical_value(value: Mapping[str, Any], *, strict: bool = True) -> dict[str, Any]:
    """The canonical form of a value (a new dict): a literal in its canonical written form, ids in NFC.
    ``strict=False`` never raises and keeps what it cannot normalise."""
    try:
        kind = value_kind(value)
        if kind == "literal":
            return {"literal": canonical_literal(value["literal"], strict=strict)}
        if kind in ("entity", "fact"):
            return {kind: _id(value, kind)}
        if kind == "special" and value["special"] not in SPECIALS:
            raise fail("KHG-C002", f"special value {value['special']!r} is not somevalue or novalue")
        if kind == "unbound" and not (isinstance(value["unbound"], Mapping)
                                      and isinstance(value["unbound"].get("var"), str)):
            raise fail("KHG-C010", "an unbound value is {var, expect?}")
    except (ValueError, TypeError, KeyError):
        if strict:
            raise
    return nfc_deep(value)


def value_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    """What equality, hashing, keys and refinement compare (§2.3); raises C001, C002, C004, C010 or S006 on a
    malformed value."""
    if value_kind(value) == "literal":
        return {"literal": literal_identity(value["literal"])}
    return canonical_value(value)


def identity_key(value: Mapping[str, Any]) -> str:
    """The canonical JSON text of a value's identity: equal texts mean one value."""
    return jsonio.canonical(value_identity(value))


def values_equal(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """True when two values have one identity (a Julian and a Gregorian writing of one day are equal)."""
    return identity_key(a) == identity_key(b)


def literal_label(literal: Mapping[str, Any]) -> str:
    """The §4.2 label of a literal, as HIF literal nodes and ``render_text`` write it."""
    lit = canonical_literal(literal)
    dt = lit["datatype"]
    if dt == "time":
        suffix = " (Julian)" if lit["calendar"] == "julian" else ""
        return f"{lit['time']}/{lit['precision']}{suffix}"
    if dt == "quantity":
        text = lit["amount"] + ("" if lit["unit"] == "1" else " " + lit["unit"])
        return text + (f" [{lit['lower']}, {lit['upper']}]" if "lower" in lit else "")
    if dt == "lang_string":
        return f"{lit['value']}@{lit['lang']}"
    if dt == "geo":
        return f"{lit['lat']},{lit['lon']}"
    if dt == "boolean":
        return "true" if lit["value"] else "false"
    return lit["value"]
