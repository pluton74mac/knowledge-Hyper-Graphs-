"""``Queue``: a handle on one C3 queue file (DESIGN §7).

A queue file is append-only JSONL, one per (run, order): line 1 is the ``queue-header``, then ``queue-item`` and
``log-entry`` lines in append order, each one canonical JSON object. Items are never edited; an item's state is a
fold over its entries. There is one appender at a time (DESIGN §14 ruling 5), and every actor appends through a
handle. A handle appends under an exclusive lock on the file, and refuses (``ConcurrencyError``) when another handle
holds the lock or when the file changed since the handle last read or wrote it (checked under the lock). ``accept``
holds the lock from that check through its write to the store, so a second appender is refused before the store is
touched. The lock is ``fcntl.flock`` on the queue file where the platform and the file system have it (the system
releases it when the process ends), else the exclusive creation of ``<queue file>.lock``, removed after the append.

- ``Queue.create(path, *, queue_id, schema, base=None, created_at=None)`` writes the header: the schema pin and, with
  a base container, its ``document_id`` and ``record.container_sha256``. An existing file is refused.
- ``Queue.open(path, *, schema, base=None)`` reads a file and checks its structure and fold (layer J, V001, the
  queue schema, Q005, Q007, Q008), its schema pin (D009) and a base given for it (Q012); ``ValidationError``.
- ``submit`` appends an item (qid ``q:<queue_id>.<seq>``) with the keys of its payload read as asserted. It refuses
  an item line that fails the queue schema or the fold; the payload's own checks are the linter's.
- ``accept`` writes the payload, its id replaced and its status asserted, with the item's entities in one ``put``
  at ``at`` (also the entry's ``at``; the store's clock when None). It logs the versions read and written and
  ``decision_hash``. ``reject``, ``flag``, ``verdict`` and ``withdraw`` log the other decisions; ``Linter.lint``
  logs a lint. Every entry is checked against the queue schema and the fold before anything is written.

An actor is a ``{type, id, version?}`` object, or a string, which names a person. A person's entries are ``manual``,
the others ``automatic``. ``at`` defaults to the system clock (RFC 3339 UTC).
"""
from __future__ import annotations

import contextlib
import copy
import os
from typing import Any, Iterable, Iterator, Mapping

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows: the lock is the sidecar file
    fcntl = None  # type: ignore[assignment]

from .. import jsonio
from ..errors import ConcurrencyError, KHGError, ValidationError, make_finding
from ..record import check_container, container_sha256, read_container
from ..schema import Schema, load_schema
from ..store.clocks import SystemClock
from ..validate.layers import c as layer_c
from ..validate.layers.j import is_path
from . import model as M
from .checks import base_findings, cand_findings, item_keys, pin_findings, verdict_findings
from .decision import accepted_record, decision_hash, read_versions, written_versions
from .fold import Fold, check, time_findings
from .lines import dump_line, line_findings, raise_errors
from .model import LogEntry
from .verdicts import complete

__all__ = ["Queue", "as_container"]

Finding = dict[str, str]
#: Stands for the fields an accept computes after its write, while the entry is checked before it.
_PLACEHOLDER = "sha256:" + "0" * 64


def as_container(base: Any) -> dict[str, Any]:
    """A base container from a mapping or a path (``record.read_container``), after layers V and C
    (``ValidationError``)."""
    container = read_container(base) if is_path(base) else base
    if not isinstance(container, Mapping):
        raise TypeError(f"a base is a C1 container or a path to one, not {type(base).__name__}")
    raise_errors(check_container(container))
    return dict(container)


def _actor(actor: Any) -> tuple[dict[str, Any], str]:
    """``({type, id, version?}, mode)``: a string names a person (``manual``); other actors are ``automatic``."""
    if isinstance(actor, str):
        who: dict[str, Any] = {"type": "person", "id": actor}
    elif isinstance(actor, Mapping):
        who = copy.deepcopy(dict(actor))
    else:
        raise TypeError(f"an actor is a string or a {{type, id, version?}} object, not {type(actor).__name__}")
    return who, "manual" if who.get("type") == "person" else "automatic"


def _copy(x: Any) -> Any:
    return copy.deepcopy(dict(x)) if isinstance(x, Mapping) else copy.deepcopy(x)


def _busy(path: str, how: str) -> ConcurrencyError:
    return ConcurrencyError(f"{path} is being appended to through another handle ({how}; one appender at a time)",
                            info={"path": path, "locked": True})


@contextlib.contextmanager
def _exclusive(path: str, fd: int) -> Iterator[None]:
    """Hold the appenders' lock on the queue file ``path`` (open as ``fd``); ``ConcurrencyError`` when another
    handle, in this process or another, holds it."""
    if fcntl is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise _busy(path, "its lock is held") from None
        except OSError:
            pass  # a file system without flock (ENOLCK on some network mounts): the sidecar file below
        else:
            yield  # os.close(fd) releases the lock
            return
    sidecar = path + ".lock"
    try:
        os.close(os.open(sidecar, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
    except FileExistsError:
        raise _busy(path, f"{sidecar} exists; remove it if no appender is running") from None
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.remove(sidecar)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


class Queue:
    """A handle on one queue file; build it with ``Queue.create`` or ``Queue.open``."""

    def __init__(self, path: str, schema: Schema, fold: Fold, *, base: dict[str, Any] | None, size: int,
                 newline: bool = False) -> None:
        self._path = path
        self._schema = schema
        self._fold = fold
        self._base = base
        self._size = size
        self._newline = newline
        self._clock = SystemClock()
        self._fd: int | None = None  # the file, open and locked for appending, while this handle holds the lock

    # ------------------------------------------------------------------------------------------ construction

    @classmethod
    def create(cls, path: str | os.PathLike[str], *, queue_id: str, schema: Any, base: Any = None,
               created_at: str | None = None) -> Queue:
        """Write a new queue file with its header line and return its handle: ``FileExistsError`` when the file
        exists, ``ValueError`` for a bad queue id, ``ValidationError`` for a bad schema, base or ``created_at``."""
        s = load_schema(schema)
        M.check_queue_id(queue_id)
        container = as_container(base) if base is not None else None
        header: dict[str, Any] = {"kind": "queue-header", "format": M.FORMAT, "queue_id": queue_id,
                                  "record_format": M.RECORD_FORMAT, "schema": s.header}
        if container is not None:
            head = container.get("header")
            header["base"] = {"document_id": head.get("document_id") if isinstance(head, Mapping) else None,
                              "sha256": container_sha256(container)}
        header["created_at"] = created_at if created_at is not None else SystemClock().now()
        header = jsonio.loads(jsonio.canonical(header))
        raise_errors(line_findings(header, path="/lines/0") + time_findings(header, "/lines/0"))
        text = dump_line(header).encode("utf-8")
        target = os.fspath(path)
        with open(target, "xb") as fh:
            fh.write(text)
        fold = Fold()
        fold.feed(header, 0)
        return cls(target, s, fold, base=container, size=len(text))

    @classmethod
    def open(cls, path: str | os.PathLike[str], *, schema: Any, base: Any = None) -> Queue:
        """A handle on an existing queue file, after its checks (``ValidationError`` with J, V001 for the header's
        ``format`` or ``record_format``, the queue schema's codes, Q005, Q007, Q008, D009 or Q012). ``base``, when
        given, must be the header's base."""
        s = load_schema(schema)
        target = os.fspath(path)
        with open(target, "rb") as fh:
            raw = fh.read()
        lines = jsonio.loads_lines(raw)
        fold, findings = check(lines)  # V001 alone for a stamp this reader does not accept
        container = as_container(base) if base is not None else None
        if fold.header is not None:
            findings += pin_findings(fold.header, s)
            if container is not None:
                findings += base_findings(fold.header, container)
        raise_errors(findings)
        return cls(target, s, fold, base=container, size=len(raw), newline=not raw.endswith(b"\n"))

    # ------------------------------------------------------------------------------------------ reading

    @property
    def path(self) -> str:
        return self._path

    def __fspath__(self) -> str:
        """The queue file, so a handle is read wherever a path is (``validate_queue``, ``replay``,
        ``queue_items``)."""
        return self._path

    @property
    def queue_id(self) -> str:
        return self._fold.queue_id or ""

    @property
    def header(self) -> dict[str, Any]:
        """A copy of the header line."""
        return copy.deepcopy(self._fold.header or {})

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def base(self) -> dict[str, Any] | None:
        """The base container given to ``create`` or ``open`` (checked against the header), or None."""
        return self._base

    @property
    def qids(self) -> tuple[str, ...]:
        """The items' qids, in append order."""
        return tuple(self._fold.items)

    def state(self, qid: str) -> str:
        """The folded state of item ``qid``."""
        self._known(qid)
        return self._fold.state[qid]

    def item(self, qid: str) -> dict[str, Any]:
        """A copy of item ``qid`` as its line reads."""
        return copy.deepcopy(self._item(qid))

    def __repr__(self) -> str:
        return f"Queue({self._path!r}, queue_id={self.queue_id!r}, items={len(self._fold.items)})"

    # ------------------------------------------------------------------------------------------ appending

    def submit(self, payload: Mapping[str, Any], *, run: Mapping[str, Any], doc: Mapping[str, Any],
               submitted_by: str, entities: Iterable[Mapping[str, Any]] = (), at: str | None = None) -> str:
        """Append a ``hyperedge`` item for ``payload`` (a candidate: see ``make_candidate``) and return its qid.
        ``keys`` are computed from the payload read as asserted; ``entities`` are C1 entity records the payload
        needs, written with it on accept. ``ValidationError`` when the item line would fail the queue schema
        (Q001, Q002, Q008, Q010, the C codes of an entity) or its keys cannot be computed."""
        if not isinstance(payload, Mapping):
            raise ValidationError.from_findings([make_finding("KHG-Q008", "/payload", "a payload is a C1 record")])
        body = copy.deepcopy(dict(payload))
        qid = M.qid(self.queue_id, self._fold.item_seq + 1)
        item: dict[str, Any] = {"kind": "queue-item", "qid": qid, "item_kind": "hyperedge",
                                "submitted_at": at if at is not None else self._now(), "submitted_by": submitted_by,
                                "run": _copy(run), "doc": _copy(doc), "payload": body, "keys": self._keys(body)}
        listed = [_copy(e) for e in entities]
        if listed:
            item["entities"] = listed
        self._append(item, cand_findings(body.get("id"), self.queue_id, f"/lines/{self._fold.lines}"))
        return qid

    def accept(self, qid: str, *, store: Any, id: str, actor: Any, reason: str, at: str | None = None) -> LogEntry:
        """Accept item ``qid``: one ``put`` of its entities and of the payload with ``id`` and status asserted, at
        ``at``; then the entry, with ``before``, ``after`` and ``decision_hash``. The entry is checked first (Q005
        for a move the fold forbids or an open lint error); a store error propagates and nothing is logged. The
        handle holds the appenders' lock from before the ``put`` until the entry is written, so another appender
        is refused (``ConcurrencyError``) before the store is touched."""
        item = self._item(qid)
        who, mode = _actor(actor)
        if not isinstance(id, str) or not id:
            raise ValidationError.from_findings([make_finding("KHG-C010", "/id", "the accepted record's id is a "
                                                                                 "non-empty string")])
        draft = self._entry(qid, "accept", who, mode, at=at, state_after="accepted", reason=reason, before=[],
                            after=[], decision_hash=_PLACEHOLDER)
        raise_errors(self._line_problems(jsonio.loads(jsonio.canonical(draft))))
        with self._appending():
            record = accepted_record(item, id)
            entities = [copy.deepcopy(e) for e in item.get("entities") or []]
            before = read_versions(store, [e.get("id") for e in entities if isinstance(e, Mapping)] + [id])
            receipt = store.put(entities + [record] if entities else record, actor=who["id"], at=at)
            after = written_versions(receipt)
            entry = dict(draft, at=at if at is not None else receipt["at"], before=before, after=after,
                         decision_hash=decision_hash(store, after))
            return self._append(entry)

    def reject(self, qid: str, *, actor: Any, reason: str, at: str | None = None) -> LogEntry:
        """Reject item ``qid`` (from pending, linted or needs_review)."""
        return self._decide(qid, "reject", "rejected", actor, at, reason=reason)

    def flag(self, qid: str, *, actor: Any, reason: str, at: str | None = None) -> LogEntry:
        """Flag item ``qid`` for review (from pending or linted)."""
        return self._decide(qid, "flag", "needs_review", actor, at, reason=reason)

    def withdraw(self, qid: str, *, actor: Any, reason: str, at: str | None = None) -> LogEntry:
        """Withdraw item ``qid`` (from an open state)."""
        return self._decide(qid, "withdraw", "withdrawn", actor, at, reason=reason)

    def verdict(self, qid: str, *, actor: Any, verdict: Mapping[str, Any], at: str | None = None) -> LogEntry:
        """Log a verdict on one (candidate, evidence) pair of item ``qid``; the state is unchanged. ``core_key``
        and ``event_hash`` are filled from the item and the evidence when absent (Q010 when given and wrong);
        ``bindings`` and ``missing`` default to ``[]``."""
        v = complete(verdict, self._item(qid))
        return self._decide(qid, "verdict", self._fold.state[qid], actor, at, verdict=v)

    def _log(self, qid: str, action: str, actor: Mapping[str, Any], mode: str, *, at: str | None,
             state_after: str, **fields: Any) -> LogEntry:
        """Append an entry built from the fold (the linter logs through this)."""
        self._item(qid)
        return self._append(self._entry(qid, action, dict(actor), mode, at=at, state_after=state_after, **fields))

    # ------------------------------------------------------------------------------------------ internals

    def _now(self) -> str:
        now = self._clock.now()
        self._clock.tick()
        return now

    def _known(self, qid: str) -> None:
        if qid not in self._fold.items:
            raise ValidationError.from_findings([make_finding("KHG-Q007", "/target", f"{qid!r} is not an item of "
                                                                                     f"queue {self.queue_id}")])

    def _item(self, qid: str) -> dict[str, Any]:
        self._known(qid)
        return self._fold.items[qid]

    def _keys(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return item_keys(payload, self._schema)
        except ValidationError:
            raise
        except (KHGError, ValueError, TypeError, KeyError, AttributeError) as exc:
            found = layer_c.record_findings(payload, definition="hyperedge", path="/payload")
            if found:
                raise ValidationError.from_findings(found) from exc
            raise ValidationError.from_findings([make_finding("KHG-C010", "/payload", f"the payload's keys cannot "
                                                                                      f"be computed: {exc}")]) from exc

    def _entry(self, qid: str, action: str, who: dict[str, Any], mode: str, *, at: str | None, state_after: str,
               **fields: Any) -> dict[str, Any]:
        entry = {"kind": "log-entry", "lid": M.lid(self.queue_id, self._fold.entry_seq + 1),
                 "parent": self._fold.last[qid], "target": qid, "action": action,
                 "state_before": self._fold.state[qid], "state_after": state_after, "actor": who, "mode": mode,
                 "at": at if at is not None else self._now()}
        entry.update(copy.deepcopy(fields))
        return entry

    def _decide(self, qid: str, action: str, state_after: str, actor: Any, at: str | None,
                **fields: Any) -> LogEntry:
        self._item(qid)
        who, mode = _actor(actor)
        return self._append(self._entry(qid, action, who, mode, at=at, state_after=state_after, **fields))

    def _line_problems(self, line: dict[str, Any]) -> list[Finding]:
        """What appending ``line`` would report: the queue schema, the fold and, for a verdict, Q008 and Q010."""
        n = self._fold.lines
        found = line_findings(line, path=f"/lines/{n}") + time_findings(line, f"/lines/{n}")
        if line.get("kind") == "log-entry":
            found += self._fold.judge_entry(line, n)[0]
            if line.get("action") == "verdict" and line.get("target") in self._fold.items:
                found += verdict_findings(line, self._fold.items[line["target"]], schema=self._schema,
                                          path=f"/lines/{n}")
        return found

    @contextlib.contextmanager
    def _appending(self) -> Iterator[int]:
        """The file, open for appending under the appenders' lock (``ConcurrencyError`` when another handle holds
        it), after the check that it did not change since this handle last read or wrote it. Nested uses within
        this handle share the lock."""
        if self._fd is not None:
            yield self._fd
            return
        fd = os.open(self._path, os.O_WRONLY | os.O_APPEND | getattr(os, "O_BINARY", 0))
        try:
            with _exclusive(self._path, fd):
                self._fd = fd
                try:
                    self._check_unchanged()
                    yield fd
                finally:
                    self._fd = None
        finally:
            os.close(fd)

    def _check_unchanged(self) -> None:
        size = os.fstat(self._fd).st_size if self._fd is not None else os.path.getsize(self._path)
        if size != self._size:
            raise ConcurrencyError(f"{self._path} changed since this handle last read or wrote it (one appender at "
                                   f"a time)", info={"path": self._path, "expected_size": self._size, "size": size})

    def _append(self, line: dict[str, Any], extra: list[Finding] | None = None) -> dict[str, Any]:
        """Check a new line (the queue schema, the fold, ``extra``), append it under the appenders' lock and fold
        it; returns a copy of the line as written."""
        stored = jsonio.loads(jsonio.canonical(line))
        raise_errors(self._line_problems(stored) + list(extra or []))
        with self._appending() as fd:
            data = dump_line(stored).encode("utf-8")
            if self._newline:
                data = b"\n" + data
            _write_all(fd, data)
        self._size += len(data)
        self._newline = False
        self._fold.feed(stored, self._fold.lines)
        return copy.deepcopy(stored)
