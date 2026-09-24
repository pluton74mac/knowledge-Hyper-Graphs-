"""Time limits and the step log (DESIGN §3.7).

``--time-limit T`` bounds each *step*: a DP, a clique enumeration, an induced search, an hw-search level, a heuristic
decomposition, or a solver call at one k. Python steps check a cooperative ``Deadline``; solver calls run in their own
process group and are killed at T (``solvers.runner``). Every step is logged as a dict: measure, method, tool, k, limit,
seconds, outcome and an optional detail. The class tests are polynomial and are not steps.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

__all__ = ["Budget", "Deadline", "StepLog", "StepTimeout", "BudgetExhausted"]

T = TypeVar("T")


class StepTimeout(Exception):
    """A cooperative deadline passed."""


class BudgetExhausted(Exception):
    """A step used up its budget of trials (a bound, not a refutation)."""


class Deadline:
    """A cooperative deadline. ``check()`` raises ``StepTimeout`` once ``seconds`` have passed; ``tick()`` calls it
    only every 256th time, for hot loops. ``Deadline(None)`` never expires."""

    __slots__ = ("end", "_n")

    def __init__(self, seconds: float | None):
        self.end = None if seconds is None else time.monotonic() + max(0.0, float(seconds))
        self._n = 0

    def check(self) -> None:
        if self.end is not None and time.monotonic() > self.end:
            raise StepTimeout()

    def tick(self) -> None:
        self._n += 1
        if not self._n & 255:
            self.check()

    def expired(self) -> bool:
        return self.end is not None and time.monotonic() > self.end

    def remaining(self) -> float | None:
        return None if self.end is None else max(0.0, self.end - time.monotonic())


class Budget:
    """A count of trials; ``spend()`` raises ``BudgetExhausted`` past ``limit``."""

    __slots__ = ("limit", "used")

    def __init__(self, limit: int):
        self.limit = limit
        self.used = 0

    def spend(self, n: int = 1) -> None:
        self.used += n
        if self.used > self.limit:
            raise BudgetExhausted()


@dataclass
class StepLog:
    """The steps of one run, in order."""

    steps: list[dict[str, Any]] = field(default_factory=list)

    def run(self, fn: Callable[[Deadline], T], *, measure: str, method: str, limit: float | None,
            tool: str = "python", k: int | None = None, detail: str | None = None) -> tuple[str, T | None]:
        """Run ``fn(deadline)`` as one step. Returns ``(outcome, result)``: outcome ``done`` with the result,
        ``timeout`` or ``budget`` with None. The step is logged either way."""
        t0 = time.monotonic()
        deadline = Deadline(limit)
        outcome, result = "done", None
        try:
            result = fn(deadline)
        except StepTimeout:
            outcome = "timeout"
        except BudgetExhausted:
            outcome = "budget"
        self.add(measure=measure, method=method, tool=tool, k=k, limit=limit, seconds=time.monotonic() - t0,
                 outcome=outcome, detail=detail)
        return outcome, result

    def add(self, *, measure: str, method: str, tool: str = "python", k: int | None = None,
            limit: float | None = None, seconds: float = 0.0, outcome: str = "done", detail: str | None = None) -> None:
        entry: dict[str, Any] = {"measure": measure, "method": method, "tool": tool, "k": k, "limit": limit,
                                 "seconds": round(seconds, 4), "outcome": outcome}
        if detail:
            entry["detail"] = detail
        self.steps.append(entry)

    def for_measure(self, measure: str) -> list[dict[str, Any]]:
        return [s for s in self.steps if s["measure"] == measure]
