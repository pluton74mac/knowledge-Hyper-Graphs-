"""The four console scripts of DESIGN §10.4: khg-validate, khg-convert, khg-migrate and khg-conformance.

Placeholder entry points from the scaffold step (W0): each exits with 2 until the command lands (W12).
"""
from __future__ import annotations

import sys
from typing import NoReturn, Sequence

__all__ = ["validate_main", "convert_main", "migrate_main", "conformance_main"]


def _not_yet(command: str) -> NoReturn:
    sys.stderr.write(f"{command}: not implemented yet\n")
    raise SystemExit(2)


def validate_main(argv: Sequence[str] | None = None) -> int:
    """``khg-validate PATH ...``: validate a file (§10.4)."""
    _not_yet("khg-validate")


def convert_main(argv: Sequence[str] | None = None) -> int:
    """``khg-convert IN OUT --to ...``: convert between C1 and HIF (§10.4)."""
    _not_yet("khg-convert")


def migrate_main(argv: Sequence[str] | None = None) -> int:
    """``khg-migrate IN OUT --from v0-sample``: migrate the v0 sample (§10.4, §11.3)."""
    _not_yet("khg-migrate")


def conformance_main(argv: Sequence[str] | None = None) -> int:
    """``khg-conformance --factory MODULE:CALLABLE``: run the C2 conformance suite (§10.4)."""
    _not_yet("khg-conformance")
