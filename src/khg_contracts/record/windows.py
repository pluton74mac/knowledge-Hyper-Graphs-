"""Calendars, instants and the precision windows of time literals (DESIGN §2.1, §2.3, §2.6).

- An **instant** is a whole second on the proleptic Gregorian line, held as an int: the Julian day number times
  86400 plus the time of day. It is written ``[+-]YYYY-MM-DDThh:mm:ssZ`` with astronomical years (``+0000`` is
  1 BCE); ``parse_instant`` and ``format_instant`` convert (C011 on anything else).
- A **time literal** is written in Wikibase form ``±YYYY-MM-DDThh:mm:ssZ`` with historical years (no year 0,
  ``-0001`` is 1 BCE), a ``precision`` 0-14 and a ``calendar`` (``gregorian`` or ``julian``). Components below the
  precision are zero, and a written year before 1583 must state its calendar (S006).
- The **window** ``[lo, hi)`` of a time literal is computed in its calendar and mapped to the Gregorian line
  through the Julian day number. Centuries (7) and millennia (6) are ordinal, as Wikidata reads them; decades (8)
  and precisions 5 to 0 floor the astronomical year.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, NamedTuple

from ._common import fail

__all__ = [
    "CALENDARS",
    "DAY",
    "JULIAN_BEFORE",
    "NEG_INF",
    "POS_INF",
    "TimeParts",
    "astronomical_year",
    "days_in_month",
    "format_instant",
    "gregorian_from_jdn",
    "julian_day_number",
    "parse_instant",
    "parse_time",
    "window",
    "window_seconds",
]

CALENDARS = ("gregorian", "julian")
DAY = 86400
#: A time literal whose written year is before 1583 must state its calendar (Wikidata's boundary; S006).
JULIAN_BEFORE = 1583
NEG_INF = float("-inf")
POS_INF = float("inf")

_TIME = re.compile(r"([+-])([0-9]{4,})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z")


class TimeParts(NamedTuple):
    """A parsed time literal: the written (historical) year and the components, with its precision and calendar."""

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    precision: int
    calendar: str


# ------------------------------------------------------------------------------------------------ calendars


def _is_leap(year: int, calendar: str) -> bool:
    if calendar == "julian":
        return year % 4 == 0
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def days_in_month(year: int, month: int, calendar: str = "gregorian") -> int:
    """Days in ``month`` of the astronomical ``year`` in ``calendar``."""
    if month == 2:
        return 29 if _is_leap(year, calendar) else 28
    return 31 if month in (1, 3, 5, 7, 8, 10, 12) else 30


def julian_day_number(year: int, month: int, day: int, calendar: str = "gregorian") -> int:
    """The Julian day number of a date in the proleptic ``calendar`` (astronomical year; floor division, so every
    year works)."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    days = day + (153 * m + 2) // 5 + 365 * y + y // 4
    if calendar == "julian":
        return days - 32083
    return days - y // 100 + y // 400 - 32045


def gregorian_from_jdn(jdn: int) -> tuple[int, int, int]:
    """The proleptic Gregorian date ``(astronomical year, month, day)`` of a Julian day number."""
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def astronomical_year(year: int) -> int:
    """Historical numbering (no year 0; -1 is 1 BCE) to astronomical (0 is 1 BCE)."""
    return year + 1 if year < 0 else year


def _seconds(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0,
             calendar: str = "gregorian") -> int:
    return julian_day_number(year, month, day, calendar) * DAY + hour * 3600 + minute * 60 + second


# ------------------------------------------------------------------------------------------------ instants


def format_instant(t: float) -> str | None:
    """An instant in the ``as_of`` grammar; None for an unbounded side (+/-infinity)."""
    if t in (NEG_INF, POS_INF):
        return None
    jdn, rest = divmod(int(t), DAY)
    year, month, day = gregorian_from_jdn(jdn)
    hour, rest = divmod(rest, 3600)
    minute, second = divmod(rest, 60)
    sign = "-" if year < 0 else "+"
    return f"{sign}{abs(year):04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"


def parse_instant(text: Any) -> int:
    """An ``as_of`` instant ``[+-]YYYY-MM-DDThh:mm:ssZ`` (proleptic Gregorian, astronomical years, UTC, no
    precision or calendar) as seconds; C011 on anything else, including a partial date and ``-0000``."""
    m = _TIME.fullmatch(text) if isinstance(text, str) else None
    if not m:
        raise fail("KHG-C011", f"as_of instant {text!r} is not [+-]YYYY-MM-DDThh:mm:ssZ")
    sign, y, mo, d, hh, mi, ss = m.groups()
    if sign == "-" and int(y) == 0:
        raise fail("KHG-C011", f"as_of instant {text!r}: write year 0 as +0000")
    year = -int(y) if sign == "-" else int(y)
    month, day, hour, minute, second = int(mo), int(d), int(hh), int(mi), int(ss)
    if not (1 <= month <= 12 and 1 <= day <= days_in_month(year, month) and hour < 24 and minute < 60
            and second < 60):
        raise fail("KHG-C011", f"as_of instant {text!r} is not a calendar date-time")
    return _seconds(year, month, day, hour, minute, second)


# ------------------------------------------------------------------------------------------------ time literals


def _precision(value: Any) -> int:
    integral = isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if isinstance(value, bool) or not integral:
        raise fail("KHG-C004", f"precision {value!r} is not an integer 0-14")
    p = int(value)
    if not 0 <= p <= 14:
        raise fail("KHG-C004", f"precision {p} is outside 0-14")
    return p


def parse_time(time: Any, precision: Any, calendar: Any = None) -> TimeParts:
    """Parse and check the Wikibase form of a time literal (DESIGN §2.3).

    C004 for the lexical form, the precision range and the calendar; S006 for year 0, a year before 1583 without a
    calendar, a component set below the precision, and a component or day out of range for its calendar.
    """
    m = _TIME.fullmatch(time) if isinstance(time, str) else None
    if not m:
        raise fail("KHG-C004", f"time {time!r} is not in the form +-YYYY-MM-DDThh:mm:ssZ")
    sign, y, mo, d, hh, mi, ss = m.groups()
    if int(y) == 0:
        raise fail("KHG-S006", f"time {time!r}: year 0 does not exist in historical numbering (1 BCE is -0001)")
    year = -int(y) if sign == "-" else int(y)
    p = _precision(precision)
    if calendar is not None and calendar not in CALENDARS:
        raise fail("KHG-C004", f"calendar {calendar!r} is not gregorian or julian")
    if calendar is None and year < JULIAN_BEFORE:
        raise fail("KHG-S006", f"time {time!r}: a date before {JULIAN_BEFORE} must state its calendar")
    cal = calendar or "gregorian"
    month, day, hour, minute, second = int(mo), int(d), int(hh), int(mi), int(ss)
    # (name, value, the precision from which it is written, its range there; the day's range is the month's)
    for name, value, needed, low, top in (("month", month, 10, 1, 12), ("day", day, 11, 1, 31),
                                          ("hour", hour, 12, 0, 23), ("minute", minute, 13, 0, 59),
                                          ("second", second, 14, 0, 59)):
        if p < needed and value != 0:
            raise fail("KHG-S006", f"time {time!r}: the {name} is set below precision {p}")
        if p >= needed and not low <= value <= top:
            raise fail("KHG-S006", f"time {time!r}: the {name} is out of range")
    if p >= 11 and day > days_in_month(astronomical_year(year), month, cal):
        raise fail("KHG-S006", f"time {time!r}: day {day} does not exist in that {cal} month")
    return TimeParts(year, month, day, hour, minute, second, p, cal)


def _literal(literal: Any) -> Mapping[str, Any]:
    lit = literal.get("literal", literal) if isinstance(literal, Mapping) and len(literal) == 1 else literal
    if not isinstance(lit, Mapping) or lit.get("datatype") != "time":
        raise fail("KHG-C004", "not a time literal")
    return lit


def window_seconds(literal: Mapping[str, Any]) -> tuple[int, int]:
    """``[lo, hi)`` of a time literal as seconds on the proleptic Gregorian line (the §2.3 precision table).

    ``literal`` is the literal object or a value ``{"literal": ...}``.
    """
    lit = _literal(literal)
    t = parse_time(lit.get("time"), lit.get("precision"), lit.get("calendar"))
    cal, p, y = t.calendar, t.precision, t.year
    a = astronomical_year(y)
    if p >= 11:
        unit = {11: DAY, 12: 3600, 13: 60, 14: 1}[p]
        lo = _seconds(a, t.month, t.day, t.hour, t.minute, t.second, cal)
        return lo, lo + unit
    if p == 10:
        nxt = (a + 1, 1) if t.month == 12 else (a, t.month + 1)
        return _seconds(a, t.month, 1, calendar=cal), _seconds(nxt[0], nxt[1], 1, calendar=cal)
    if p == 9:
        return _seconds(a, 1, 1, calendar=cal), _seconds(a + 1, 1, 1, calendar=cal)
    if p in (7, 6):  # ordinal centuries and millennia
        u = 100 if p == 7 else 1000
        if y > 0:
            c = -(-y // u)
            return _seconds(u * c - (u - 1), 1, 1, calendar=cal), _seconds(u * c + 1, 1, 1, calendar=cal)
        n = -y  # years BCE; the ordinal block holds u*c BCE ... u*c - (u - 1) BCE
        c = -(-n // u)
        earliest, latest = u * c, u * c - (u - 1)
        return (_seconds(astronomical_year(-earliest), 1, 1, calendar=cal),
                _seconds(astronomical_year(-latest) + 1, 1, 1, calendar=cal))
    u = 10 ** (9 - p)  # decades (8) and 10**4 ... 10**9 years (5 ... 0): floor on the astronomical year
    b = (a // u) * u
    return _seconds(b, 1, 1, calendar=cal), _seconds(b + u, 1, 1, calendar=cal)


def window(literal: Mapping[str, Any]) -> tuple[str, str]:
    """``(lo, hi)``: the half-open window of a time literal as instants in the §2.1 grammar (C004, S006)."""
    lo, hi = window_seconds(literal)
    return format_instant(lo), format_instant(hi)  # type: ignore[return-value]
