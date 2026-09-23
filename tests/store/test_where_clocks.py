"""W8: ``Where`` and its defaults (a ruling, DESIGN §6.2), the clocks and transaction timestamps (§2.6, §6.1)."""
from __future__ import annotations

import pytest

from khg_contracts.errors import ValidationError
from khg_contracts.store import (SCENARIO_START, Clock, ScenarioClock, SystemClock, Where, format_timestamp,
                                 parse_timestamp)


def test_the_where_defaults_are_the_ruling():
    w = Where()
    assert (w.status, w.rank, w.visibility, w.kinds) == (frozenset({"asserted"}), frozenset({"preferred", "normal"}),
                                                         frozenset({"visible"}), frozenset({"fact"}))
    assert (w.as_of, w.valid_mode, w.as_at) == (None, "definite", None)
    assert w.as_dict() == {"status": ["asserted"], "rank": ["normal", "preferred"], "visibility": ["visible"],
                           "kinds": ["fact"], "as_of": None, "valid_mode": "definite", "as_at": None}
    assert hash(w) == hash(Where()) and w == Where.of(None) == Where.of({}) and Where.of(w) is w


def test_where_coerces_and_checks_its_fields():
    w = Where.of({"status": ["asserted", "superseded"], "rank": ("normal",), "as_of": "+1700-01-01T00:00:00Z",
                  "valid_mode": "possible", "as_at": "2026-10-01T00:00:00.25Z"})
    assert w.status == frozenset({"asserted", "superseded"}) and w.rank == frozenset({"normal"})
    assert w.as_of_seconds == Where(as_of="+1700-01-01T00:00:00Z").as_of_seconds
    assert w.as_at_micros == parse_timestamp("2026-10-01T00:00:00Z") + 250_000
    with pytest.raises(ValueError):
        Where(status={"assertd"})
    with pytest.raises(ValueError):
        Where(kinds={"rule"})
    with pytest.raises(TypeError):
        Where(status="asserted")
    with pytest.raises(ValueError):
        Where(valid_mode="maybe")
    with pytest.raises(ValidationError) as e:
        Where(as_of="1700")
    assert e.value.codes == ("KHG-C011",)
    with pytest.raises(ValidationError):
        Where(as_at="2026-10-01")
    with pytest.raises(TypeError):
        Where.of({"statuses": ["asserted"]})
    with pytest.raises(TypeError):
        Where.of(["asserted"])


def test_the_scenario_clock():
    c = ScenarioClock()
    assert isinstance(c, Clock) and c.now() == SCENARIO_START == "2026-10-01T00:00:00Z"
    assert c.tick() == "2026-10-01T00:00:01Z" and c.now() == "2026-10-01T00:00:01Z"
    c.set("2026-10-01T00:00:00Z")
    assert c.now() == "2026-10-01T00:00:00Z"
    half = ScenarioClock("2026-10-01T00:00:00Z", 0.5)
    assert half.tick() == "2026-10-01T00:00:00.5Z" and half.tick() == "2026-10-01T00:00:01Z"
    with pytest.raises(ValueError):
        ScenarioClock(step=0)
    assert repr(c) == "ScenarioClock(now='2026-10-01T00:00:00Z', step=1)"


def test_the_system_clock_never_goes_back():
    c = SystemClock()
    assert isinstance(c, Clock)
    first = parse_timestamp(c.now())
    assert first > parse_timestamp("2026-01-01T00:00:00Z")
    ticks = [parse_timestamp(c.tick()) for _ in range(50)]
    assert ticks == sorted(set(ticks)) and ticks[0] > first - 1
    c.set("2999-01-01T00:00:00Z")
    assert c.now() == "2999-01-01T00:00:00Z" and c.tick() == "2999-01-01T00:00:00.000001Z"
    c.set("2000-01-01T00:00:00Z")  # set only pins forward
    assert c.now().startswith("2999-01-01")


def test_timestamps():
    t = parse_timestamp("2026-10-01T00:00:01Z")
    assert format_timestamp(t) == "2026-10-01T00:00:01Z"
    assert format_timestamp(t + 1) == "2026-10-01T00:00:01.000001Z"
    assert format_timestamp(t + 120_000) == "2026-10-01T00:00:01.12Z"
    assert format_timestamp(parse_timestamp("0000-01-01T00:00:00Z")) == "0000-01-01T00:00:00Z"
    with pytest.raises(ValueError):
        format_timestamp(parse_timestamp("0000-01-01T00:00:00Z") - 1)
    with pytest.raises(ValidationError):
        parse_timestamp("2026-10-01T00:00:01+01:00")
