"""The C5 scorers ``khg-scorers/1.0.0`` (DESIGN §9): one ``score()`` per ability.

- ``extraction``: C3 queue items (or C1 hyperedges) against ``c4-extraction-doc`` gold; value-first Hungarian
  alignment, strict, core, Arg-I, Arg-C, role accuracy, pooled, pairwise; presets ``hyperred_quintuplet`` and
  ``text2nkg``.
- ``stability``: pairwise Jaccard, core ratio, support histogram, churn, gold partition and Δ_order over runs.
- ``completion``: ``build_queries``, ``FilterIndex``, ``rank_stats`` and ``score`` with the tie conventions, the
  three filters, three averages, calibration (equal-width and equal-mass ECE, Brier) and the presets ``hype``,
  ``stare`` and ``hyper``.
- ``retrieval``: ranking, support, ``binding_coverage@k``, answers, joint and gated scores, abstention and cost.
- ``memory``: memory gold and the memory scorer (step W11a).

Shared parts: ``Bootstrap`` and the percentile bootstrap (``bootstrap``), the pure-Python Hungarian solver with an
optional SciPy backend (``hungarian``), and the calibration measures (``calibration``). Every ``score()`` returns
``{scorer, config, contracts, aggregate, breakdowns, items, bootstrap}``; no scorer calls an LLM. Submodules are
imported on first access, so importing this package loads nothing heavy.
"""
from __future__ import annotations

import importlib
import importlib.util
from types import ModuleType

from .bootstrap import Bootstrap

FORMAT = "khg-scorers/1.0.0"

__all__ = ["FORMAT", "Bootstrap"]

_SUBMODULES = ("bootstrap", "calibration", "completion", "extraction", "hungarian", "memory", "retrieval",
               "stability")


def __getattr__(name: str) -> ModuleType:
    """Import ``khg_contracts.scorers.<name>`` on first access (PEP 562)."""
    if name in _SUBMODULES:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_SUBMODULES))
