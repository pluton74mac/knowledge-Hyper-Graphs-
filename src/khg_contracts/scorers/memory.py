"""The memory scorer and memory gold (DESIGN §9.2, §9.3, §9.5): step W11a builds this module.

``derive_memory_gold`` replays a ``c4-memory-trace`` into a fresh ``MemoryStore`` and reads the normative
memory-gold table of §9.5; ``score`` classifies each ``memory-response`` into the outcomes O1–O7 and reports strict
and lenient accuracy, the stale rate split into ``expired`` and ``revised``, and the other rates of §9.3. Until
W11a lands, the configuration is defined and both functions raise ``NotImplementedError``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping

from .bootstrap import Bootstrap

__all__ = ["INCORRECT_REASONS", "MemoryConfig", "derive_memory_gold", "score"]

#: Wikidata's "incorrect value", the default deprecation reason that marks a revised value (§9.5; ruling 3)
INCORRECT_REASONS = frozenset({"wd:Q41755623"})


@dataclass(frozen=True)
class MemoryConfig:
    """The memory scorer's settings (DESIGN §9.2)."""

    mode: Literal["strict", "lenient"] = "strict"
    incorrect_reasons: frozenset[str] = INCORRECT_REASONS
    bootstrap: Bootstrap = Bootstrap()


def derive_memory_gold(trace: Mapping[str, Any], question: Mapping[str, Any], *, schema: Any,
                       incorrect_reasons: frozenset[str] = INCORRECT_REASONS) -> dict[str, Any]:
    """The memory gold of ``question`` replayed from ``trace`` (§9.5); built in step W11a."""
    raise NotImplementedError("derive_memory_gold is built in step W11a (DESIGN, Implementation plan)")


def score(questions: Iterable[Mapping[str, Any]], responses: Iterable[Mapping[str, Any]], *,
          traces: Iterable[Mapping[str, Any]], schema: Any, config: MemoryConfig = MemoryConfig()) -> dict[str, Any]:
    """Score memory responses (§9.3); built in step W11a."""
    raise NotImplementedError("memory.score is built in step W11a (DESIGN, Implementation plan)")
