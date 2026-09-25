"""The conformance runs (DESIGN §4): khg-contracts' own runner on each backend, the EARL reports, and the
inapplicable scenarios listed by flag as fidelity losses (P2 DESIGN §14 ruling 1; PLAN §7).

A backend **passes** when no applicable scenario fails (and none is ``cantTell``); a scenario is inapplicable only
through a flag the backend declares absent, and each one is a fidelity loss.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from khg_contracts.store import ALL_FLAGS, ScenarioClock
from khg_contracts.store import conformance as c2

from .backends import BACKENDS, factory
from .provenance import provenance

__all__ = ["losses", "run", "summarize"]


def losses(report: dict[str, Any]) -> dict[str, list[str]]:
    """The inapplicable scenarios by missing flag (a scenario that needs two missing flags is under both)."""
    out: dict[str, list[str]] = {}
    for a in report["@graph"]:
        r = a["result"]
        if r["outcome"] == "inapplicable":
            for flag in r.get("missing", []):
                out.setdefault(flag, []).append(a["test"]["identifier"])
    return {k: sorted(v) for k, v in sorted(out.items())}


def summarize(name: str, report: dict[str, Any], engine: dict[str, Any]) -> dict[str, Any]:
    """One backend's line of ``summary.json`` (no timings: the first half makes no timing claims)."""
    s = report["summary"]
    return {
        "backend": name, "layout": BACKENDS[name].layout, **engine,
        "declared_flags": report["subject"]["capabilities"],
        "absent_flags": sorted(ALL_FLAGS - set(report["subject"]["capabilities"])),
        "scenarios": s["total"], "applicable": s["total"] - s["inapplicable"], "passed": s["passed"],
        "failed": s["failed"], "cantTell": s["cantTell"], "inapplicable": s["inapplicable"],
        "passes": s["failed"] == 0 and s["cantTell"] == 0,
        "losses_by_flag": losses(report),
        "not_passed": {a["test"]["identifier"]: a["result"].get("info", "")
                       for a in report["@graph"] if a["result"]["outcome"] in ("failed", "cantTell")},
    }


def run(names: Iterable[str], out: Path | None = None, endpoints: dict[str, str] | None = None) -> dict[str, Any]:
    """Run the suite on each backend; write ``<name>.earl.json`` under ``out`` and return the summaries."""
    summaries: dict[str, Any] = {}
    for name in names:
        make = factory(name, (endpoints or {}).get(name))
        probe = make(c2.suite().schema, ScenarioClock())
        try:
            engine = probe.engine()
        finally:
            probe.close()
        report = c2.run(make)
        summaries[name] = summarize(name, report, engine)
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
            c2.write_report(report, out / f"{name}.earl.json")
    return {"provenance": provenance(), "backends": summaries}
