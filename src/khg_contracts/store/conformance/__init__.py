"""The C2 conformance suite (``khg-scenario/1.0.0``; DESIGN §6.4).

``run(factory, *, only=None, capabilities=None)`` runs the 114 packaged scenarios (``data/scenarios/``) and returns
an EARL-shaped report: per scenario ``passed``, ``failed``, ``inapplicable`` or ``cantTell``, and a ``summary``.

- ``factory(schema, clock)`` returns a fresh, empty store (``store.memory_factory`` for the reference store); it is
  called once to read the store's declared capabilities, then once per applicable scenario.
- ``only`` selects scenarios by id glob (``"S-KEY-*"``) or several globs.
- ``capabilities`` tests the store as if it declared only these flags (intersected with what it declares).

An implementation passes when no applicable scenario fails; a scenario is inapplicable only because of a flag the
store declares absent (the director's ruling, §14). ``to_json`` gives the report's text and ``write_report`` writes it
to a file; ``suite()`` gives the scenarios, the fixture and its schema; ``run_scenario`` runs one.
"""
from __future__ import annotations

from typing import Any, Iterable

from .checks import Failed, Unknown
from .report import CONTEXT, build, summary, to_json, write_report
from .runner import ACTOR, OUTCOMES, Outcome, call, run_given, run_scenario, run_suite
from .suite import CORE_FLAGS, SCENARIO_FORMAT, Suite, select, suite

__all__ = [
    "ACTOR",
    "CONTEXT",
    "CORE_FLAGS",
    "OUTCOMES",
    "SCENARIO_FORMAT",
    "Failed",
    "Outcome",
    "Suite",
    "Unknown",
    "build",
    "call",
    "run",
    "run_given",
    "run_scenario",
    "run_suite",
    "select",
    "suite",
    "summary",
    "to_json",
    "write_report",
]


def run(factory: Any, *, only: str | Iterable[str] | None = None,
        capabilities: Iterable[str] | None = None) -> dict[str, Any]:
    """Run the suite on stores from ``factory``; the EARL-shaped report."""
    if isinstance(only, (list, tuple, set, frozenset)):
        only = sorted(only)
    outcomes, info, tested = run_suite(factory, only=only, capabilities=capabilities)
    return build(outcomes, info=info, tested=tested, only=only, suite_size=len(suite().scenarios))
