"""W3: calendars through the Julian day number, as_of instants, and the precision windows of time literals
(DESIGN §2.1, §2.3, §2.6)."""
from __future__ import annotations

import pytest

from khg_contracts import record
from khg_contracts.errors import ValidationError
from khg_contracts.record import windows


def T(time, precision, calendar=None):
    lit = {"datatype": "time", "time": time, "precision": precision}
    if calendar:
        lit["calendar"] = calendar
    return lit


def code(fn, *args):
    with pytest.raises(ValidationError) as exc:
        fn(*args)
    return exc.value.code


# ------------------------------------------------------------------------------------------------ calendars


@pytest.mark.parametrize("date, calendar, jdn", [
    ((2000, 1, 1), "gregorian", 2451545),
    ((1970, 1, 1), "gregorian", 2440588),
    ((1582, 10, 15), "gregorian", 2299161),
    ((1582, 10, 5), "julian", 2299161),       # the day the Gregorian calendar began, in both writings
    ((1582, 10, 4), "julian", 2299160),
    ((-4712, 1, 1), "julian", 0),             # the epoch of the Julian day number (astronomical year)
    ((-4713, 11, 24), "gregorian", 0),
])
def test_julian_day_numbers(date, calendar, jdn):
    assert record.julian_day_number(*date, calendar) == jdn


def test_gregorian_dates_round_trip_through_the_jdn_in_every_era():
    for year in list(range(-5000, 5001, 37)) + [-10 ** 9, -4713, -1, 0, 1, 1582, 1600, 1700, 1900, 10 ** 9]:
        for month in range(1, 13):
            for day in {1, 15, record.windows.days_in_month(year, month)}:
                assert record.gregorian_from_jdn(record.julian_day_number(year, month, day)) == (year, month, day)


@pytest.mark.parametrize("calendar", ["julian", "gregorian"])
@pytest.mark.parametrize("years", [range(-46, -40), range(-2, 3), range(1698, 1702)])
def test_consecutive_days_are_consecutive_numbers(calendar, years):
    jdns = [record.julian_day_number(y, m, d, calendar) for y in years for m in range(1, 13)
            for d in range(1, windows.days_in_month(y, m, calendar) + 1)]
    assert [b - a for a, b in zip(jdns, jdns[1:], strict=False)] == [1] * (len(jdns) - 1)
    assert record.julian_day_number(1700, 2, 29, "julian") + 1 == record.julian_day_number(1700, 3, 1, "julian")


def test_leap_years_differ_between_the_calendars():
    assert windows.days_in_month(1700, 2, "julian") == 29 and windows.days_in_month(1700, 2) == 28
    assert windows.days_in_month(1600, 2) == 29 and windows.days_in_month(2000, 2) == 29
    assert windows.days_in_month(0, 2, "julian") == 29 and windows.days_in_month(-4, 2) == 29  # 1 BCE, 5 BCE


def test_historical_to_astronomical_years():
    assert [record.astronomical_year(y) for y in (-44, -1, 1, 2019)] == [-43, 0, 1, 2019]


# ------------------------------------------------------------------------------------------------ instants


@pytest.mark.parametrize("text", ["+1700-01-01T00:00:00Z", "+0000-12-31T23:59:59Z", "-0043-03-13T12:00:00Z",
                                  "+1600-02-29T00:00:00Z", "+10000-01-01T00:00:00Z", "-1000000-06-15T08:30:00Z"])
def test_instants_parse_and_format_back(text):
    t = record.parse_instant(text)
    assert isinstance(t, int)
    assert record.format_instant(t) == text


def test_instants_are_seconds_on_the_gregorian_line():
    assert record.parse_instant("+2000-01-01T00:00:00Z") == 2451545 * 86400
    assert record.parse_instant("+2000-01-01T00:00:01Z") - record.parse_instant("+1999-12-31T23:59:59Z") == 2
    assert record.format_instant(record.NEG_INF) is None and record.format_instant(record.POS_INF) is None


@pytest.mark.parametrize("text", ["1700", "+1700", "+1700-01-01", "1700-01-01T00:00:00Z", "+1700-01-01T00:00:00",
                                  "-0000-01-01T00:00:00Z", "+1700-02-29T00:00:00Z", "+1700-13-01T00:00:00Z",
                                  "+1700-01-01T24:00:00Z", "+1700-01-01T00:60:00Z", "+170-01-01T00:00:00Z",
                                  "+1700-01-01T00:00:00.5Z", "+١٧٠٠-01-01T00:00:00Z", None, 1700])
def test_partial_or_malformed_instants_are_c011(text):
    assert code(record.parse_instant, text) == "KHG-C011"


# ------------------------------------------------------------------------------------------------ windows


# the checked table of DESIGN §2.3, plus the rows of S-TIME-003, S-TIME-011 and S-TIME-012
WINDOW_TABLE = [
    (T("+1900-00-00T00:00:00Z", 7), ("+1801-01-01T00:00:00Z", "+1901-01-01T00:00:00Z")),  # the 19th century
    (T("+1901-00-00T00:00:00Z", 7), ("+1901-01-01T00:00:00Z", "+2001-01-01T00:00:00Z")),
    (T("+2000-00-00T00:00:00Z", 6), ("+1001-01-01T00:00:00Z", "+2001-01-01T00:00:00Z")),
    (T("+1995-00-00T00:00:00Z", 8), ("+1990-01-01T00:00:00Z", "+2000-01-01T00:00:00Z")),
    (T("-0100-00-00T00:00:00Z", 7, "julian"), ("-0100-12-30T00:00:00Z", "+0000-12-30T00:00:00Z")),  # 1st c. BCE
    (T("-0044-03-15T00:00:00Z", 11, "julian"), ("-0043-03-13T00:00:00Z", "-0043-03-14T00:00:00Z")),
    (T("+1700-00-00T00:00:00Z", 9, "julian"), ("+1700-01-11T00:00:00Z", "+1701-01-12T00:00:00Z")),
    (T("+1643-00-00T00:00:00Z", 9), ("+1643-01-01T00:00:00Z", "+1644-01-01T00:00:00Z")),
    (T("+2025-00-00T00:00:00Z", 8), ("+2020-01-01T00:00:00Z", "+2030-01-01T00:00:00Z")),
    (T("-0049-00-00T00:00:00Z", 9, "julian"), ("-0049-12-30T00:00:00Z", "-0048-12-30T00:00:00Z")),
]


@pytest.mark.parametrize("lit, want", WINDOW_TABLE, ids=[f"{w[0]['time']}/{w[0]['precision']}" for w in WINDOW_TABLE])
def test_the_precision_window_table(lit, want):
    assert record.window(lit) == want
    assert record.window({"literal": lit}) == want


@pytest.mark.parametrize("lit, want", [
    (T("+1700-02-00T00:00:00Z", 10, "julian"), ("+1700-02-11T00:00:00Z", "+1700-03-12T00:00:00Z")),  # 29 Julian days
    (T("+1999-12-00T00:00:00Z", 10), ("+1999-12-01T00:00:00Z", "+2000-01-01T00:00:00Z")),
    (T("+2001-02-03T04:00:00Z", 12), ("+2001-02-03T04:00:00Z", "+2001-02-03T05:00:00Z")),
    (T("+2001-02-03T04:05:00Z", 13), ("+2001-02-03T04:05:00Z", "+2001-02-03T04:06:00Z")),
    (T("+2001-02-03T04:05:06Z", 14), ("+2001-02-03T04:05:06Z", "+2001-02-03T04:05:07Z")),
    (T("+2019-00-00T00:00:00Z", 5), ("+0000-01-01T00:00:00Z", "+10000-01-01T00:00:00Z")),
    (T("-0100-00-00T00:00:00Z", 5, "julian"), ("-10001-10-16T00:00:00Z", "-0001-12-30T00:00:00Z")),
    (T("+13798000000-00-00T00:00:00Z", 0), ("+13000000000-01-01T00:00:00Z", "+14000000000-01-01T00:00:00Z")),
    (T("-0044-00-00T00:00:00Z", 8, "julian"), ("-0051-12-30T00:00:00Z", "-0041-12-30T00:00:00Z")),
    (T("-0500-00-00T00:00:00Z", 6, "julian"), ("-1000-12-23T00:00:00Z", "+0000-12-30T00:00:00Z")),
])
def test_other_precisions(lit, want):
    assert record.window(lit) == want


def test_a_bce_decade_floors_the_astronomical_year():
    # -0044 is astronomical -43; floor(-43 / 10) * 10 = -50: the block is astronomical -50 ... -41
    lo, hi = record.window_seconds(T("-0044-00-00T00:00:00Z", 8, "julian"))
    assert record.julian_day_number(-50, 1, 1, "julian") * 86400 == lo
    assert record.julian_day_number(-40, 1, 1, "julian") * 86400 == hi


def test_julian_1582_10_05_and_gregorian_1582_10_15_are_one_window():
    julian = T("+1582-10-05T00:00:00Z", 11, "julian")
    gregorian = T("+1582-10-15T00:00:00Z", 11, "gregorian")
    assert record.window(julian) == record.window(gregorian) == ("+1582-10-15T00:00:00Z", "+1582-10-16T00:00:00Z")


def test_windows_nest_by_precision():
    day, month, year = T("+1643-05-14T00:00:00Z", 11), T("+1643-05-00T00:00:00Z", 10), T("+1643-00-00T00:00:00Z", 9)
    decade, century = T("+1643-00-00T00:00:00Z", 8), T("+1643-00-00T00:00:00Z", 7)
    spans = [record.window_seconds(x) for x in (day, month, year, decade, century)]
    for inner, outer in zip(spans, spans[1:], strict=False):
        assert outer[0] <= inner[0] and inner[1] <= outer[1] and inner != outer


# ------------------------------------------------------------------------------------------------ refusals


@pytest.mark.parametrize("lit", [
    T("+0000-00-00T00:00:00Z", 9),                  # year 0 does not exist in historical numbering
    T("-0000-00-00T00:00:00Z", 9, "julian"),
    T("+0000-00-00T00:00:00Z", 9, "gregorian"),
    T("+1500-01-01T00:00:00Z", 11),                 # before 1583 without a calendar
    T("+1582-10-15T00:00:00Z", 11),
    T("-0044-03-15T00:00:00Z", 11),
    T("+2019-00-05T00:00:00Z", 9),                  # a day set below year precision
    T("+2001-02-03T00:00:00Z", 10),
    T("+2001-02-03T04:05:00Z", 12),
    T("+1643-13-14T00:00:00Z", 11),                 # month 13
    T("+1643-05-00T00:00:00Z", 11),                 # day 0 at day precision
    T("+1643-00-00T00:00:00Z", 10),                 # month 0 at month precision
    T("+1700-02-29T00:00:00Z", 11, "gregorian"),    # 29 February 1700 exists only in the Julian calendar
    T("+1643-04-31T00:00:00Z", 11),
    T("+2001-02-03T24:00:00Z", 12),
    T("+2001-02-03T00:00:60Z", 14),
], ids=lambda x: f"{x['time']}/{x['precision']}/{x.get('calendar', '-')}")
def test_out_of_range_time_literals_are_s006(lit):
    assert code(record.window, lit) == "KHG-S006"
    assert code(record.value_identity, {"literal": lit}) == "KHG-S006"


def test_the_1583_rule_and_the_julian_leap_day():
    assert record.window(T("+1583-01-01T00:00:00Z", 11))[0] == "+1583-01-01T00:00:00Z"
    assert record.window(T("+1500-01-01T00:00:00Z", 11, "julian"))[0] == "+1500-01-10T00:00:00Z"
    assert record.window(T("+1700-02-29T00:00:00Z", 11, "julian")) == ("+1700-03-11T00:00:00Z",
                                                                       "+1700-03-12T00:00:00Z")


@pytest.mark.parametrize("lit", [
    T("1643-05-14T00:00:00Z", 11),                 # no sign
    T("+1643-05-14", 11),
    T("+1643-05-14T00:00:00Z", 15),                # precision outside 0-14
    T("+1643-05-14T00:00:00Z", -1),
    T("+1643-05-14T00:00:00Z", "11"),
    T("+1643-05-14T00:00:00Z", True),
    T("+1643-05-14T00:00:00Z", 10.5),
    T("+1643-05-14T00:00:00Z", float("nan")),
    T("+1643-05-14T00:00:00Z", float("inf")),
    T("+1643-05-14T00:00:00Z", 11, "islamic"),
    {"datatype": "quantity", "amount": "+1", "unit": "1"},
])
def test_structural_faults_are_c004(lit):
    assert code(record.window, lit) == "KHG-C004"


def test_an_integral_float_precision_is_the_integer():
    assert record.window(T("+1643-05-14T00:00:00Z", 11.0)) == record.window(T("+1643-05-14T00:00:00Z", 11))


def test_parse_time_returns_the_written_parts():
    parts = record.parse_time("-0044-03-15T00:00:00Z", 11, "julian")
    assert parts == record.TimeParts(-44, 3, 15, 0, 0, 0, 11, "julian")
    assert record.parse_time("+2019-00-00T00:00:00Z", 9).calendar == "gregorian"
