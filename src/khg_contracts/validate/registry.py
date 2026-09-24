"""The code registry ``khg-codes/1.0.0`` (DESIGN §8.1), read from the packaged ``data/error-codes.json``.

- It registers 134 codes: 128 are active and 6 are reserved, which are never emitted.
- Each code has a layer (the letter of the code), a severity, a status, a meaning and the codes of designs A, B and
  C that it merges.
- The file also lists the layers, the pipelines per input kind and the layer rule.
- 31 planned codes of later versions are listed apart and are not registered, so 1.0 does not freeze them.

Codes are never reused, and messages are not part of the contract.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterator, Mapping

from .. import data

__all__ = ["CODE_PATTERN", "FILE", "FORMAT", "Code", "Registry", "layer_of", "registry"]

FILE = "error-codes.json"
FORMAT = "khg-codes/1.0.0"
CODE_PATTERN = re.compile(r"KHG-([A-Z])([0-9]{3})")


@dataclass(frozen=True)
class Code:
    """One code of the registry. ``status`` is ``active``, ``reserved`` or, for a code of a later version that is
    not registered, ``planned`` (then ``version`` names the version that will ship it)."""

    code: str
    layer: str
    severity: str
    status: str
    meaning: str
    merges: str = ""
    version: str = ""

    @property
    def active(self) -> bool:
        return self.status == "active"


def layer_of(code: str) -> str:
    """The layer of a code: its letter (``KHG-S004`` -> ``S``); ``ValueError`` for anything else."""
    m = CODE_PATTERN.fullmatch(code) if isinstance(code, str) else None
    if not m:
        raise ValueError(f"{code!r} is not a code: 'KHG-', a layer letter and three digits")
    return m.group(1)


def _letters(pipeline: str) -> tuple[str, ...]:
    """``"J V H R P D C S (D first runs as decoding; ...)"`` -> ``("J", "V", "H", "R", "P", "D", "C", "S")``."""
    return tuple(re.findall(r"\b[A-Z]\b", pipeline.split("(", 1)[0]))


class Registry:
    """The registry document with lookups. ``code in registry`` is true for registered codes (active or reserved),
    never for planned ones."""

    def __init__(self, doc: Mapping[str, Any]):
        if doc.get("format") != FORMAT:
            raise ValueError(f"not a {FORMAT} registry: format {doc.get('format')!r}")
        self.format: str = doc["format"]
        self.rule: str = doc.get("rule", "")
        self.layer_rule: str = doc.get("layer_rule", "")
        self.layers: Mapping[str, str] = MappingProxyType(dict(doc.get("layers", {})))
        self.pipelines: Mapping[str, tuple[str, ...]] = MappingProxyType(
            {name: _letters(text) for name, text in doc.get("pipelines", {}).items()})
        self.pipeline_notes: Mapping[str, str] = MappingProxyType(dict(doc.get("pipelines", {})))
        self._codes: dict[str, Code] = {}
        for c in doc.get("codes", []):
            self._codes[c["code"]] = Code(c["code"], c["layer"], c["severity"], c["status"], c["meaning"],
                                          c.get("merges", ""))
        self._planned: dict[str, Code] = {
            p["code"]: Code(p["code"], p["layer"], p["severity"], "planned", p["meaning"], "", p.get("version", ""))
            for p in doc.get("planned", [])}

    # ------------------------------------------------------------------ lookups
    def __contains__(self, code: object) -> bool:
        return code in self._codes

    def __getitem__(self, code: str) -> Code:
        return self._codes[code]

    def __iter__(self) -> Iterator[str]:
        return iter(self._codes)

    def __len__(self) -> int:
        return len(self._codes)

    def get(self, code: str) -> Code | None:
        """The registered code, or None (planned codes are not registered)."""
        return self._codes.get(code)

    def codes(self, *, layer: str | None = None, status: str | None = None) -> list[Code]:
        """The registered codes in registry order, optionally of one layer and one status."""
        return [c for c in self._codes.values()
                if (layer is None or c.layer == layer) and (status is None or c.status == status)]

    def active(self) -> list[str]:
        """The active codes, in registry order."""
        return [c.code for c in self.codes(status="active")]

    def reserved(self) -> list[str]:
        """The reserved codes (never emitted), in registry order."""
        return [c.code for c in self.codes(status="reserved")]

    def planned(self) -> list[Code]:
        """The planned codes of later versions (not registered), in file order."""
        return list(self._planned.values())

    def is_planned(self, code: str) -> bool:
        return code in self._planned

    def severity(self, code: str) -> str:
        """The registered severity of a code (an emitting layer may lower it, as S003 on candidates)."""
        return self._codes[code].severity

    @property
    def layer_order(self) -> tuple[str, ...]:
        """The layer letters in registry order: J V H R P D C S M Q I L F."""
        return tuple(self.layers)


@functools.cache
def registry() -> Registry:
    """The packaged registry (loaded once)."""
    return Registry(data.load_json(FILE))
