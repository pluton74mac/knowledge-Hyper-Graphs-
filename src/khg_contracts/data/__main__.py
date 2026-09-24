"""``python -m khg_contracts.data [--check]``: print the data manifest, or check the packaged files against it.

Regenerate the manifest after changing a packaged file:
``python -m khg_contracts.data > src/khg_contracts/data/manifest.json``.
"""
from __future__ import annotations

import sys

from . import _dump_manifest, verify


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--check"]:
        problems = verify()
        for p in problems:
            sys.stderr.write(p + "\n")
        return 1 if problems else 0
    if args:
        sys.stderr.write("usage: python -m khg_contracts.data [--check]\n")
        return 2
    sys.stdout.write(_dump_manifest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
