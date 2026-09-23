"""The text layout of the committed migration goldens (``data/sample/``, DESIGN §11.3).

``dumps(obj, compact=...)`` writes one top-level key per line and, inside the listed arrays, one record per line;
``compact=None`` is plain ``indent=1`` JSON. ``LAYOUT`` gives each golden's arrays, so ``khg-migrate`` can write
files that equal the goldens byte for byte. The layout is a presentation choice: canonical JSON (``jsonio``) is what
digests and comparisons use.
"""
from __future__ import annotations

import json
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional

__all__ = ["LAYOUT", "dumps"]

#: Golden -> the arrays written one record per line (None: plain ``indent=1`` JSON).
LAYOUT: Mapping[str, Optional[tuple[str, ...]]] = MappingProxyType({
    "schema": ("entity_types", "roles", "relations"),
    "container": ("records",),
    "hif": ("nodes", "edges", "incidences"),
    "report": None,
})


def _one_line(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


def dumps(obj: Mapping[str, Any], *, compact: Optional[Iterable[str]] = None) -> str:
    """``obj`` as UTF-8 JSON text ending with a newline, in the goldens' layout (see the module docstring)."""
    if compact is None:
        return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
    arrays = set(compact)
    lines = ["{"]
    keys = list(obj)
    for n, key in enumerate(keys):
        comma = "," if n < len(keys) - 1 else ""
        value = obj[key]
        if key in arrays and isinstance(value, list):
            lines.append(f" {_one_line(key)}: [")
            lines += ["  " + _one_line(x) + ("," if m < len(value) - 1 else "") for m, x in enumerate(value)]
            lines.append(" ]" + comma)
        else:
            lines.append(f" {_one_line(key)}: {_one_line(value)}{comma}")
    lines.append("}")
    return "\n".join(lines) + "\n"
