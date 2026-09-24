"""Clocks and transaction timestamps (DESIGN §2.6, §6.1, §6.4).

A store stamps every write with ``recorded_at``, an RFC 3339 UTC timestamp ``YYYY-MM-DDThh:mm:ss[.ffffff]Z``. The
store asks its clock for ``now()``, writes at that time (or at the ``at`` a call pins forward), then moves the clock
past the write with ``set`` and ``tick``, so ``recorded_at`` strictly increases per store.

- ``SystemClock`` reads the system time in microseconds; ``set`` only pins it forward.
- ``ScenarioClock(start, step)`` is the conformance clock: it starts at 2026-10-01T00:00:00Z and ticks 1 s per
  write; ``set`` moves it anywhere.

Timestamps compare as integer microseconds (``parse_timestamp``); ``format_timestamp`` writes the shortest form
(no fraction for a whole second).
"""
from __future__ import annotations

import time

from ..record import format_instant
from ..record.lifecycle import parse_timestamp

__all__ = ["SCENARIO_START", "ScenarioClock", "SystemClock", "format_timestamp", "parse_timestamp"]

#: Where the conformance clock starts (``index.json``: ``clock.start``).
SCENARIO_START = "2026-10-01T00:00:00Z"
_MICRO = 1_000_000
_EPOCH = parse_timestamp("1970-01-01T00:00:00Z")


def format_timestamp(micros: int) -> str:
    """Microseconds on the instant line as ``YYYY-MM-DDThh:mm:ss[.ffffff]Z``; ``ValueError`` before year 0."""
    seconds, fraction = divmod(int(micros), _MICRO)
    text = format_instant(seconds)
    if text is None or not text.startswith("+"):
        raise ValueError(f"no RFC 3339 timestamp for {micros} microseconds (before year 0)")
    text = text[1:]
    if fraction:
        text = f"{text[:-1]}.{fraction:06d}".rstrip("0") + "Z"
    return text


class SystemClock:
    """The system time, in microseconds, never going backwards: ``tick`` moves it at least one microsecond past
    the last value it gave, and ``set(at)`` pins it forward to ``at`` (a time already passed changes nothing)."""

    def __init__(self) -> None:
        self._floor = 0

    @staticmethod
    def _system() -> int:
        return _EPOCH + time.time_ns() // 1000

    def now(self) -> str:
        return format_timestamp(max(self._system(), self._floor))

    def tick(self) -> str:
        self._floor = max(self._system(), self._floor) + 1
        return format_timestamp(self._floor)

    def set(self, at: str) -> None:
        self._floor = max(self._floor, parse_timestamp(at))

    def __repr__(self) -> str:
        return f"SystemClock(now={self.now()!r})"


class ScenarioClock:
    """A deterministic clock: ``now()`` starts at ``start``, ``tick()`` adds ``step`` seconds, ``set(at)`` moves it
    to ``at``. The conformance suite gives each store ``ScenarioClock()`` (2026-10-01T00:00:00Z, 1 s)."""

    def __init__(self, start: str = SCENARIO_START, step: float = 1) -> None:
        micros = round(step * _MICRO)
        if micros <= 0:
            raise ValueError(f"the step must be positive, not {step!r}")
        self._t = parse_timestamp(start)
        self._step = micros

    def now(self) -> str:
        return format_timestamp(self._t)

    def tick(self) -> str:
        self._t += self._step
        return self.now()

    def set(self, at: str) -> None:
        self._t = parse_timestamp(at)

    def __repr__(self) -> str:
        return f"ScenarioClock(now={self.now()!r}, step={self._step / _MICRO:g})"
