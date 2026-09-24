"""``python -m khg_contracts.examples DIR [--tests TESTS_DIR]``: write ``design-examples/`` from the packaged data.

``data/`` is the single source of the packaged files (DESIGN §10.1); ``design-examples/`` is its mirror, and CI
checks the two byte for byte (§10.6). The mapping is fixed:

- ``data/fixture/*``        -> ``*`` (the fixture set, the smoke base and queue, C4 and C5 files, extra schemas)
- ``data/sample/*``         -> ``*`` (the four migration goldens)
- ``data/error-codes.json``, ``data/malformed-cases.json`` -> the same names
- ``data/schemas/<four>``   -> ``schemas/`` (record, profile, C4, C5; the vendored HIF schema, its licence and the
  relation-schema meta-schema are packaged but not mirrored)
- ``data/role-convention/*`` -> ``role-convention/``; ``data/scenarios/*`` -> ``conformance-scenarios/``

The five files that only tests use live under ``tests/`` (§10.1). With ``--tests`` pointing at a checkout's
``tests/`` directory they are copied too, so the output is the whole of ``design-examples/``.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from . import data

__all__ = ["MIRRORED_SCHEMAS", "TEST_ONLY", "example_map", "write_examples", "main"]

MIRRORED_SCHEMAS = ("khg-c4-items-0.1.0.schema.json", "khg-c5-io-1.0.0.schema.json", "khg-hif-1.0.0.schema.json",
                    "khg-record-1.0.0.schema.json")
#: design-examples name -> path under ``tests/``
TEST_ONLY = {
    "golden-sha256.json": "gate/golden-sha256.json",
    "native-ops.json": "loaders/native-ops.json",
    "r03-loader-cases.json": "loaders/r03-loader-cases.json",
    "r05.relation-schema.json": "scorers/r05.relation-schema.json",
    "library-hif-evidence.json": "evidence/library-hif-evidence.json",
}
_DIRS = (("fixture/", ""), ("sample/", ""), ("role-convention/", "role-convention/"),
         ("scenarios/", "conformance-scenarios/"))
_TOP = ("error-codes.json", "malformed-cases.json")


def example_map() -> dict[str, str]:
    """``design-examples`` path -> packaged data path, for every mirrored file, sorted by example path."""
    out: dict[str, str] = {}
    for rel in data.iter_files():
        target: str | None = None
        if rel in _TOP:
            target = rel
        elif rel.startswith("schemas/") and rel[len("schemas/"):] in MIRRORED_SCHEMAS:
            target = rel
        else:
            for src, dst in _DIRS:
                if rel.startswith(src) and "/" not in rel[len(src):]:
                    target = dst + rel[len(src):]
        if target is not None:
            if target in out:
                raise RuntimeError(f"two packaged files map to {target}: {out[target]} and {rel}")
            out[target] = rel
    return dict(sorted(out.items()))


def write_examples(out_dir: str | Path, *, tests_dir: str | Path | None = None) -> dict[str, list[str]]:
    """Write the mirror into ``out_dir``. Returns ``{"written": [...], "missing": [...]}``: the example paths
    written, and the test-only files that ``tests_dir`` does not have (empty without ``tests_dir``)."""
    out = Path(out_dir)
    written: list[str] = []
    missing: list[str] = []
    for target, rel in example_map().items():
        p = out / target
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data.read_bytes(rel))
        written.append(target)
    if tests_dir is not None:
        tdir = Path(tests_dir)
        for target, rel in TEST_ONLY.items():
            src = tdir / rel
            if src.is_file():
                (out / target).parent.mkdir(parents=True, exist_ok=True)
                (out / target).write_bytes(src.read_bytes())
                written.append(target)
            else:
                missing.append(target)
    return {"written": sorted(written), "missing": missing}


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    tests_dir = None
    if "--tests" in args:
        i = args.index("--tests")
        if i + 1 >= len(args):
            sys.stderr.write("--tests needs a directory\n")
            return 2
        tests_dir = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1 or args[0].startswith("-"):
        sys.stderr.write("usage: python -m khg_contracts.examples DIR [--tests TESTS_DIR]\n")
        return 2
    try:
        result = write_examples(args[0], tests_dir=tests_dir)
    except OSError as e:
        sys.stderr.write(f"cannot write the examples: {e}\n")
        return 2
    sys.stderr.write(f"wrote {len(result['written'])} files into {args[0]}\n")
    for m in result["missing"]:
        sys.stderr.write(f"not found under {tests_dir}: {TEST_ONLY[m]} (for {m})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
