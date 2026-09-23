"""Identity classification for P7 (non-normative; DESIGN §2.9, §10.2).

``relate(a, b, *, schema)`` returns one of the seven labels of [DB §2.19]: ``duplicate``, ``refines``,
``generalises``, ``distinct``, ``key_conflict``, ``key_timeline`` or ``negation_conflict``. Its tests are DB's 37
rows (``tests/identity/cases.json``); under the §2.6 ruling, X3 and C4a-u are ``key_timeline``.
"""
from __future__ import annotations

from .classifier import LABELS, relate

__all__ = ["LABELS", "relate"]
