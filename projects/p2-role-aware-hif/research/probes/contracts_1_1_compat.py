"""Compatibility probe for rulings 20-23 (impl-notes/contracts-1-1.md §6): do the packaged files of an earlier build
validate the same under this build?

    python contracts_1_1_compat.py DATA_DIR > out.jsonl

``DATA_DIR`` is a ``src/khg_contracts/data`` directory (for example of ``main`` at 490287f, from ``git archive``).
Every document of it that ``validate`` takes (containers, HIF and role-convention files, relation schemas, the smoke
queue, the C4 items) and every C5 output line is validated with the ``khg_contracts`` that Python imports, with the
directory's own fixture schema, document texts and smoke base. One JSON line per file: its path, kind, ``ok`` and the
sorted ``(code, severity, path)`` of its findings. Running it once with the earlier sources first on ``PYTHONPATH``
and once with this build, and comparing the two outputs, shows whether any earlier file changed its validity or its
findings. Offline; nothing is written but standard output.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import khg_contracts
from khg_contracts import jsonio
from khg_contracts.scorers import _inputs
from khg_contracts.validate import validate

SKIP_DIRS = ("scenarios", "schemas")
SKIP = {"manifest.json", "error-codes.json", "malformed-cases.json", "fixture/queue-item.json",
        "fixture/action-log.json", "sample/sample.migration-report.json", "fixture/fixture.doc-texts.json"}


def kind_of(rel: str) -> str | None:
    name = rel.rsplit("/", 1)[-1]
    if rel.startswith("role-convention/"):
        return "role-convention"
    if name.endswith(".relation-schema.json"):
        return "schema"
    if name.endswith(".khg-queue.jsonl"):
        return "queue"
    if name == "c5-outputs.jsonl":
        return "c5"
    if name.startswith("c4-items") and name.endswith(".jsonl"):
        return "item"
    if name.endswith(".hif.json"):
        return "hif"
    if name.endswith((".c1.json", ".c1.jsonl", ".khg.json")):
        return "container"
    return None


def main(argv: list[str]) -> int:
    root = Path(argv[1])
    fixture_schema = jsonio.load(root / "fixture/fixture.relation-schema.json")
    sample_schema = jsonio.load(root / "sample/sample.relation-schema.json")
    texts = jsonio.load(root / "fixture/fixture.doc-texts.json")
    base = jsonio.load(root / "fixture/smoke-base.c1.json")
    sys.stderr.write(f"khg-contracts {khg_contracts.__version__} from {Path(khg_contracts.__file__).parent}\n")
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel in SKIP or rel.split("/")[0] in SKIP_DIRS or path.suffix not in (".json", ".jsonl"):
            continue
        kind = kind_of(rel)
        if kind is None:
            continue
        if kind == "c5":
            findings = [f for n, line in enumerate(jsonio.loads_lines(path.read_bytes()))
                        for f in _inputs.c5_findings(line, f"/lines/{n}")]
            ok = not any(f["severity"] == "error" for f in findings)
        else:
            schema = sample_schema if rel.startswith("sample/") else fixture_schema
            kw = {} if kind in ("schema", "role-convention") else {"schema": schema, "doc_texts": texts}
            if kind == "queue":
                kw["bases"] = [base]
            if kind in ("hif", "container") and rel.startswith("sample/"):
                kw.pop("doc_texts")
            out = validate(str(path), kind=kind, **kw)
            ok, findings = out["ok"], out["findings"]
        print(json.dumps({"file": rel, "kind": kind, "ok": ok,
                          "findings": sorted([f["code"], f["severity"], f["path"]] for f in findings)},
                         ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
