"""The layer runner and the layer rule (DESIGN §8.1).

``run`` parses the input (layer J), picks its kind when ``kind="auto"``, then runs the modules of the kind's
pipeline in order (``layers.PIPELINES``) over one ``Context``:

- a J or V error stops the run; with ``stop="first"`` (the G2 harness) the run also stops after the first step
  that reports an error, so the findings are those of the steps up to the first rejecting one;
- ``steps`` restricts the run to some modules (the loaders run ``j v h r p`` or ``j h r``); J always runs;
- a step that raises after an earlier step reported an error is skipped and listed in ``Report.skipped`` (a later
  layer may not read a structure an earlier layer rejected); a step that raises on an input without errors is a
  bug, and the exception propagates.

**The layer rule.** A finding's layer is the letter of its code (a step may emit another layer's code: decoding
emits S016, and the S pass emits D009 without a schema). The first rejecting layer of an input is the earliest
letter, in its kind's pipeline order, among its error findings; letters outside the pipeline rank after it, in
registry order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, TypedDict

from .. import jsonio
from ..errors import make_finding
from ..record import read_container
from ..schema import Schema, load_schema
from . import layers
from .context import Context
from .engines import check_engine
from .layers import KINDS, PIPELINES
from .layers.j import is_path
from .layers.v import detect_kind
from .registry import registry

__all__ = ["STOPS", "Report", "Result", "first_rejecting_layer", "pipeline_letters", "run"]

STOPS = ("all", "first")
#: The kind names of the malformed-case list and the registry, mapped to the API's kinds.
_ALIASES = {"c1": "container", "relation-schema": "schema", "c4": "item"}

Finding = dict[str, str]


class Result(TypedDict):
    """What ``validate`` returns: ``ok`` is true when no finding is an error (warnings and lints never
    invalidate)."""

    ok: bool
    findings: list[Finding]


def pipeline_letters(kind: str | None) -> tuple[str, ...]:
    """The layer letters of a kind's pipeline, in order. The registry's names (``c1``, ``relation-schema``,
    ``c4``) are accepted, and ``json`` (or an unknown kind) is just ``J``."""
    kind = _ALIASES.get(kind or "", kind)
    return layers.letters(kind) if kind in PIPELINES else ("J",)


def first_rejecting_layer(findings: Iterable[Mapping[str, Any]], kind: str | None) -> str | None:
    """The earliest letter, in the kind's pipeline order, among the error findings; None when there is no
    error."""
    order = pipeline_letters(kind)
    order += tuple(letter for letter in registry().layer_order if letter not in order)
    rejecting = {f.get("layer") or str(f.get("code", ""))[4:5] for f in findings if f.get("severity") == "error"}
    return next((letter for letter in order if letter in rejecting), None)


@dataclass
class Report:
    """One run: its kind (None when it could not be told), the engine, the findings in step order, each step's
    findings, the step after which the run stopped early, and the steps skipped after they raised."""

    kind: str | None
    engine: str
    findings: list[Finding] = field(default_factory=list)
    steps: list[tuple[str, list[Finding]]] = field(default_factory=list)
    stopped: str | None = None
    skipped: list[tuple[str, str]] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f["severity"] == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def first_layer(self) -> str | None:
        """The first rejecting layer (the layer rule)."""
        return first_rejecting_layer(self.findings, self.kind)

    @property
    def first_rejecting_step(self) -> str | None:
        """The first step (layer module) that reported an error, or None."""
        return next((name for name, found in self.steps if any(f["severity"] == "error" for f in found)), None)

    def until_first_rejection(self) -> list[Finding]:
        """The findings of the steps up to and including the first step that reported an error: what a run with
        ``stop="first"`` returns (all of them when no step did)."""
        out: list[Finding] = []
        for _, found in self.steps:
            out.extend(found)
            if any(f["severity"] == "error" for f in found):
                break
        return out

    def result(self) -> Result:
        """``{ok, findings}``, as ``validate`` returns it."""
        return {"ok": self.ok, "findings": [dict(f) for f in self.findings]}


# ------------------------------------------------------------------------------------------------ arguments


def _schema_arg(schema: Any) -> Schema | None:
    """The caller's relation-type schema: a ``Schema`` as is; a document or path through ``load_schema`` (J, V
    and M; ``ValidationError`` when it fails, since a bad argument is not a finding on the input)."""
    if schema is None or isinstance(schema, Schema):
        return schema
    return load_schema(schema)


def _texts_arg(doc_texts: Any) -> dict[str, str]:
    """``{doc_id: text}`` from a mapping of texts, a ``khg-doc-texts`` document (``{"texts": {doc_id: {"text":
    ...}}}``) or a path to one."""
    if doc_texts is None:
        return {}
    if is_path(doc_texts):
        doc_texts = jsonio.load(doc_texts)
    if not isinstance(doc_texts, Mapping):
        raise TypeError("doc_texts must map doc ids to texts, or be a khg-doc-texts document or a path to one")
    if isinstance(doc_texts.get("texts"), Mapping):
        doc_texts = doc_texts["texts"]
    out: dict[str, str] = {}
    for doc_id, value in doc_texts.items():
        text = value.get("text") if isinstance(value, Mapping) else value
        if isinstance(doc_id, str) and isinstance(text, str):
            out[doc_id] = text
    return out


def _container_arg(x: Any) -> Mapping[str, Any]:
    if isinstance(x, Mapping):
        return x
    if is_path(x):
        return read_container(x)
    raise TypeError(f"a base is a container or a path to one, not {type(x).__name__}")


def _bases_arg(bases: Any) -> dict[str, Mapping[str, Any]]:
    """Base containers by ``document_id``, from a mapping ``{document_id: container or path}``, one container, or an
    iterable of containers and paths (read with ``record.read_container``)."""
    if bases is None:
        return {}
    if isinstance(bases, Mapping) and not ("header" in bases and "records" in bases):
        return {str(k): _container_arg(v) for k, v in bases.items()}
    if isinstance(bases, Mapping) or is_path(bases):
        bases = [bases]
    out: dict[str, Mapping[str, Any]] = {}
    for b in bases:
        c = _container_arg(b)
        header = c.get("header")
        doc_id = header.get("document_id") if isinstance(header, Mapping) else None
        if isinstance(doc_id, str):
            out[doc_id] = c
    return out


# ------------------------------------------------------------------------------------------------ the run


def _call(report: Report, ctx: Context, name: str) -> list[Finding]:
    try:
        found = list(layers.module(name).run(ctx))
    except Exception as exc:
        if not report.errors:
            raise
        report.skipped.append((name, f"{type(exc).__name__}: {exc}"))
        return []
    report.steps.append((name, found))
    report.findings.extend(found)
    return found


def run(obj_or_path: Any, *, kind: str = "auto", schema: Any = None, doc_texts: Any = None, bases: Any = None,
        engine: str = "jsonschema", stop: str = "all", steps: Iterable[str] | None = None) -> Report:
    """Run the pipeline of ``kind`` on ``obj_or_path`` and return the ``Report``.

    ``obj_or_path`` is a path (``str``, ``os.PathLike`` or a packaged file), raw ``bytes``, or a parsed input: a
    dict, or a list of line dicts for a queue or C4 file (a JSONL container too). ``schema`` is a ``Schema``, a
    schema document or a path; ``doc_texts`` maps doc ids to texts (or is a ``khg-doc-texts`` document or path);
    ``bases`` gives the base containers of a queue. Findings on the input never raise; an unknown ``kind``,
    ``engine``, ``stop`` or step is ``ValueError``, a bad ``schema`` or base ``ValidationError``, and an
    unreadable path ``OSError``.
    """
    if kind != "auto" and kind not in KINDS:
        raise ValueError(f"kind must be auto or one of {', '.join(KINDS)}, not {kind!r}")
    check_engine(engine)
    if stop not in STOPS:
        raise ValueError(f"stop must be one of {', '.join(STOPS)}, not {stop!r}")
    wanted = None if steps is None else set(steps)
    if wanted is not None:
        unknown = sorted(wanted - {s.name for s in layers.LAYERS})
        if unknown:
            raise ValueError(f"unknown layer modules {unknown}")
    ctx = Context(kind=kind, source=obj_or_path, engine=engine, schema=_schema_arg(schema),
                  doc_texts=_texts_arg(doc_texts), bases=_bases_arg(bases))
    report = Report(kind=None if kind == "auto" else kind, engine=engine)
    if _call(report, ctx, "j"):
        report.stopped = "j"
        return report
    if kind == "auto":
        detected = detect_kind(ctx.doc)
        if detected is None:
            found = [make_finding("KHG-V001", "", "cannot tell the kind of this input: no known format, profile or "
                                                 "record kind")]
            report.steps.append(("v", found))
            report.findings.extend(found)
            report.stopped = "v"
            return report
        ctx.kind = report.kind = detected
    if ctx.kind == "container" and isinstance(ctx.doc, list):
        ctx.doc = {"header": ctx.doc[0], "records": ctx.doc[1:]}
    for name in PIPELINES[ctx.kind][1:]:
        if wanted is not None and name not in wanted:
            continue
        found = _call(report, ctx, name)
        if any(f["severity"] == "error" for f in found) and (name == "v" or stop == "first"):
            report.stopped = name
            break
    return report
