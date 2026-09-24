"""The export report (DESIGN §5): what an export could not carry over from the library object, by class.

- ``stale``: records whose membership is gone while their edge still exists (a partial fact);
- ``unlabelled``: memberships without a record, as ``{edge, node, direction?}``;
- ``moved``: HyperNetX records whose ``khg-bid`` now sits on another node, as ``{edge, bid, from, to}``;
- ``moved_conflict``: moves whose old-to-new node map is not injective (a collapse), and records that repeat a
  ``khg-bid`` another cell already carries, in the same shape;
- ``dropped_records``: records of edges removed whole;
- ``dropped_nodes``, ``dropped_edges``: ids of nodes and edges left without an exported incidence (and not isolated
  or empty in the loaded file), and of loaded isolated nodes and empty edges that no longer exist.

Under ``strict=True`` an export raises ``LoaderError`` (P005) when ``unlabelled``, ``stale`` or ``moved_conflict`` is
not empty; everything else is reported and never raised.
"""
from __future__ import annotations

from typing import Any, TypedDict

__all__ = ["REPORT_KEYS", "STRICT_KEYS", "ExportReport", "new_report", "strict_violations"]


class ExportReport(TypedDict):
    """The report of the last export of a ``Bundle`` (DESIGN §5)."""

    stale: list[dict[str, Any]]
    unlabelled: list[dict[str, Any]]
    moved: list[dict[str, Any]]
    moved_conflict: list[dict[str, Any]]
    dropped_records: list[dict[str, Any]]
    dropped_nodes: list[Any]
    dropped_edges: list[Any]


#: The report's keys, in the order of DESIGN §5.
REPORT_KEYS = ("stale", "unlabelled", "moved", "moved_conflict", "dropped_records", "dropped_nodes", "dropped_edges")
#: The classes a strict export raises on.
STRICT_KEYS = ("unlabelled", "stale", "moved_conflict")


def new_report() -> ExportReport:
    """An empty report."""
    return ExportReport(stale=[], unlabelled=[], moved=[], moved_conflict=[], dropped_records=[], dropped_nodes=[],
                        dropped_edges=[])


def strict_violations(report: ExportReport) -> dict[str, int]:
    """The strict classes that are not empty, with their sizes (``{}`` when a strict export may proceed)."""
    return {k: len(report[k]) for k in STRICT_KEYS if report[k]}  # type: ignore[literal-required]
