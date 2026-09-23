"""The EARL-shaped report of a conformance run (DESIGN §6.4; W3C *EARL 1.0 Schema*).

One ``Assertion`` per scenario: the assertor (this runner), the subject (the store: its id, interface version and
capabilities), the test (the scenario: id, title, ``requires``) and the result, whose ``outcome`` is ``passed``,
``failed``, ``inapplicable`` or ``cantTell`` (EARL's outcome values), with ``info``. The ``@context`` maps the keys
to the EARL and Dublin Core vocabularies. The report is deterministic: no dates, assertions in scenario id order.
"""
from __future__ import annotations

import contextlib
import json
import os
import secrets
from typing import Any, Iterable, Mapping

from ... import __version__
from .runner import OUTCOMES, Outcome
from .suite import SCENARIO_FORMAT

__all__ = ["CONTEXT", "build", "summary", "to_json", "write_report"]

CONTEXT: dict[str, Any] = {
    "@vocab": "http://www.w3.org/ns/earl#",
    "earl": "http://www.w3.org/ns/earl#",
    "dct": "http://purl.org/dc/terms/",
    "title": "dct:title",
    "identifier": "dct:identifier",
    "hasVersion": "dct:hasVersion",
    "outcome": {"@type": "@vocab"},
    "mode": {"@type": "@vocab"},
}
_ASSERTOR = "khg-contracts:conformance"


def summary(outcomes: Iterable[Outcome]) -> dict[str, int]:
    """The number of scenarios per outcome, and the total."""
    counts = {o: 0 for o in OUTCOMES}
    total = 0
    for o in outcomes:
        counts[o.outcome] += 1
        total += 1
    return {**counts, "total": total}


def build(outcomes: list[Outcome], *, info: Mapping[str, Any], tested: Iterable[str], only: Any = None,
          suite_size: int) -> dict[str, Any]:
    """The report of a run: ``summary`` and one assertion per scenario under ``@graph``."""
    store_id = str(info.get("store_id"))
    subject = {"@id": f"store:{store_id}", "@type": "TestSubject", "title": store_id,
               "interface_version": info.get("interface_version"), "record_format": info.get("record_format"),
               "capabilities": sorted(info.get("capabilities", ())), "tested_capabilities": sorted(tested),
               "contracts": dict(info.get("contracts") or {})}
    assertor = {"@id": _ASSERTOR, "@type": ["Assertor", "Software"], "title": "khg-contracts conformance runner",
                "hasVersion": __version__}
    graph = []
    for o in outcomes:
        result: dict[str, Any] = {"@type": "TestResult", "outcome": o.outcome}
        if o.info:
            result["info"] = o.info
        if o.missing:
            result["missing"] = list(o.missing)
        graph.append({"@type": "Assertion", "assertedBy": _ASSERTOR, "subject": f"store:{store_id}",
                      "test": {"@id": o.id, "@type": "TestCase", "identifier": o.id, "title": o.title,
                               "requires": list(o.requires)},
                      "mode": "automatic", "result": result})
    return {"@context": CONTEXT, "assertor": assertor, "subject": subject,
            "suite": {"format": SCENARIO_FORMAT, "scenarios": suite_size, "selected": len(outcomes),
                      "only": only if only is None or isinstance(only, str) else list(only)},
            "summary": summary(outcomes), "@graph": graph}


def to_json(report: Mapping[str, Any]) -> str:
    """The report as JSON text (UTF-8 characters kept, one space indent, a final newline)."""
    return json.dumps(report, ensure_ascii=False, indent=1) + "\n"


def write_report(report: Mapping[str, Any], path: Any) -> None:
    """Write ``to_json(report)`` to ``path`` (UTF-8), replacing the file atomically; the file gets the permissions
    the umask allows."""
    text = to_json(report)
    target = os.fspath(path)
    # open(..., "x"), not tempfile.mkstemp, whose mode 0600 would survive the rename (as in cli._write_file)
    tmp = os.path.join(os.path.dirname(target) or ".", f".khg-{secrets.token_hex(8)}.tmp")
    fh = open(tmp, "x", encoding="utf-8", newline="\n")
    try:
        with fh:
            fh.write(text)
        os.replace(tmp, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise
