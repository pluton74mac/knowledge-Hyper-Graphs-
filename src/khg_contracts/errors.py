"""The exception hierarchy of khg-contracts (DESIGN §6.1, §10.2) and the finding shape of §8.1.

Every error carries ``.codes``, the registered codes it reports (``data/error-codes.json``, e.g. ``"KHG-J003"``), and
``.info``, a dict with the structured details (for example ``info["findings"]`` or, for ``KeyCollision``,
``info["collisions"]``). Messages are not part of the contract; codes are.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

__all__ = [
    "KHGError",
    "ValidationError",
    "KeyCollision",
    "VersionError",
    "ConcurrencyError",
    "NotFound",
    "CapabilityMissing",
    "LoaderError",
    "make_finding",
]


def make_finding(code: str, path: str = "", message: str = "", severity: str = "error") -> dict[str, str]:
    """A finding ``{code, severity, layer, path, message}``; the layer is the letter of the code (§8.1)."""
    return {"code": code, "severity": severity, "layer": _layer(code), "path": path, "message": message}


def _layer(code: str) -> str:
    return code[4] if code.startswith("KHG-") and len(code) > 4 else ""


class KHGError(Exception):
    """Base class: ``codes`` lists the registered codes, in order; ``info`` holds structured details."""

    def __init__(self, message: str = "", *, codes: Iterable[str] = (), info: Mapping[str, Any] | None = None):
        self.codes: tuple[str, ...] = tuple(codes)
        self.info: dict[str, Any] = dict(info or {})
        super().__init__(message)

    @property
    def code(self) -> str | None:
        """The first code, or None."""
        return self.codes[0] if self.codes else None

    @property
    def message(self) -> str:
        return str(self.args[0]) if self.args else ""

    def __str__(self) -> str:
        msg = self.message
        if self.codes and not msg.startswith(self.codes[0]):
            return f"{self.codes[0]}: {msg}" if msg else self.codes[0]
        return msg

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, codes={list(self.codes)!r})"


class ValidationError(KHGError, ValueError):
    """A document, record or argument fails a check (layers J to I, and D002, D008, D010, D020 on writes)."""

    @classmethod
    def from_findings(cls, findings: Iterable[Mapping[str, Any]], message: str | None = None,
                      **info: Any) -> ValidationError:
        """Build the error from findings: ``codes`` are the codes of the error findings, in first-seen order."""
        fs = [dict(f) for f in findings]
        errs = [f for f in fs if f.get("severity", "error") == "error"] or fs
        codes: list[str] = []
        for f in errs:
            if f["code"] not in codes:
                codes.append(f["code"])
        if message is None:
            first = errs[0] if errs else {}
            where = f" at {first['path']}" if first.get("path") else ""
            more = f" (and {len(errs) - 1} more)" if len(errs) > 1 else ""
            message = f"{first.get('code', 'invalid')}{where}: {first.get('message', '')}".rstrip(": ") + more
        return cls(message, codes=codes, info={"findings": fs, **info})


class KeyCollision(KHGError):
    """D016: a write breaks the key invariant or the disputed-key rule; ``info["collisions"]`` lists them (§2.5)."""


class VersionError(KHGError):
    """D011-D014, D018: the version rule, a transition or transaction time is violated."""


class ConcurrencyError(KHGError):
    """D019: an optimistic-concurrency expectation (``expect``) was not met."""


class NotFound(KHGError, LookupError):
    """A record, id or version the call names does not exist."""


class CapabilityMissing(KHGError):
    """The store lacks a capability flag the call needs; ``flag`` names it (§6.3)."""

    def __init__(self, flag: str, message: str = "", *, codes: Iterable[str] = (),
                 info: Mapping[str, Any] | None = None):
        self.flag = flag
        super().__init__(message or f"capability missing: {flag}", codes=codes, info={"flag": flag, **(info or {})})


class LoaderError(KHGError, ValueError):
    """A library loader or export refuses its input (P005, P007, P010, D001; §5)."""
