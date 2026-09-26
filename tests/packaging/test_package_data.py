"""W0: the packaged data is present with its hashes (DESIGN §10.1, §10.5): the manifest, the vendored HIF schema
and its licence, strict JSON everywhere, closed schema references, and the counts the design states."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from khg_contracts import data, jsonio

HIF_LICENSE_SHA256 = "sha256:bfec44796db963653bcb367f176b8197ee0aca95b914ddcf638413ed431b2ddd"
TAG = "tag:khg-contracts,2026:schema/"
FILES = data.iter_files()


def test_the_manifest_pins_every_packaged_file():
    assert data.verify() == []
    listed = data.load_json(data.MANIFEST)
    assert listed["algorithm"] == "sha256"
    assert sorted(listed["files"]) == FILES
    assert all(re.fullmatch(r"sha256:[0-9a-f]{64}", h) for h in listed["files"].values())


def test_verify_reports_a_changed_file(monkeypatch):
    real = data.read_bytes

    def fake(rel):
        return b"{}" if rel == "error-codes.json" else real(rel)
    monkeypatch.setattr(data, "read_bytes", fake)
    assert data.verify() == ["changed: error-codes.json"]


def test_the_vendored_hif_schema_is_unchanged():
    raw = data.read_bytes(data.HIF_SCHEMA)
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == data.HIF_SCHEMA_SHA256
    assert data.HIF_SCHEMA_SHA256.endswith("639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196")
    schema = data.hif_schema()
    assert schema["$id"] == data.HIF_SCHEMA_ID
    assert schema["title"] == "Hypergraph Interchange Format"
    assert data.load_json("fixture/fixture.hif.json")["metadata"]["hif-schema-sha256"] == data.HIF_SCHEMA_SHA256
    assert data.load_json("fixture/fixture.hif.json")["metadata"]["hif-schema"] == data.HIF_SCHEMA_URL


def test_the_hif_licence_ships_with_the_notice(repo_root):
    raw = data.read_bytes(data.HIF_LICENSE)
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == HIF_LICENSE_SHA256
    text = raw.decode("utf-8")
    assert text.startswith("MIT License") and "Copyright (c) 2024-2025 HIF development team" in text
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    assert '"src/khg_contracts/data/schemas/HIF-LICENSE.txt"' in pyproject and '"LICENSE"' in pyproject


def test_the_hif_schema_check_refuses_a_changed_copy(monkeypatch):
    real = data.read_bytes
    monkeypatch.setattr(data, "read_bytes", lambda rel: real(rel) + b" " if rel == data.HIF_SCHEMA else real(rel))
    with pytest.raises(RuntimeError, match="the vendored HIF schema hashes to sha256:[0-9a-f]{64}, not"):
        data.hif_schema()


@pytest.mark.parametrize("rel", [f for f in FILES if f.endswith((".json", ".jsonl"))])
def test_every_packaged_json_file_passes_layer_j(rel):
    if rel.endswith(".jsonl"):
        assert len(data.load_jsonl(rel)) >= 1
    else:
        assert isinstance(data.load_json(rel), dict)


def test_the_layout_of_section_10_1():
    by_dir: dict[str, list[str]] = {}
    for f in FILES:
        by_dir.setdefault(f.split("/")[0] if "/" in f else "", []).append(f)
    assert sorted(by_dir[""]) == ["error-codes.json", "malformed-cases.json"]
    assert len(by_dir["fixture"]) == 17 and len(by_dir["role-convention"]) == 5
    assert len(by_dir["sample"]) == 4 and len(by_dir["scenarios"]) == 115
    assert {"schemas/hif_schema_v0.1.0.json", "schemas/HIF-LICENSE.txt", "schemas/khg-record-1.0.0.schema.json",
            "schemas/khg-relation-schema-1.1.0.schema.json", "schemas/khg-hif-1.0.0.schema.json",
            "schemas/khg-c4-items-0.2.0.schema.json", "schemas/khg-c5-io-1.0.0.schema.json"} <= set(by_dir["schemas"])


def _refs(s):
    if isinstance(s, dict):
        for k, v in s.items():
            if k == "$ref" and isinstance(v, str):
                yield v
            else:
                yield from _refs(v)
    elif isinstance(s, list):
        for v in s:
            yield from _refs(v)


def _pointer(doc, fragment):
    for p in [x.replace("~1", "/").replace("~0", "~") for x in fragment.split("/")[1:]]:
        doc = doc[int(p)] if isinstance(doc, list) else doc[p]
    return doc


def test_packaged_schemas_have_unique_ids_and_only_closed_absolute_refs():
    docs = data.schema_documents()
    ours = [i for i in docs if i != data.HIF_SCHEMA_ID]
    assert all(i.startswith(TAG) for i in ours)
    assert len(ours) == len([f for f in FILES if f.endswith(".schema.json")])
    for sid, doc in docs.items():
        for ref in _refs(doc):
            if sid == data.HIF_SCHEMA_ID:
                assert ref.startswith("#/")  # the vendored schema is unchanged and self-contained
                continue
            base, _, fragment = ref.partition("#")
            assert base in docs, f"{sid}: {ref} leaves the packaged schemas"
            _pointer(docs[base], fragment)


def test_the_registry_and_the_case_list_as_the_design_counts_them():
    reg = data.load_json("error-codes.json")
    assert reg["format"] == "khg-codes/1.0.0"
    codes = {c["code"]: c for c in reg["codes"]}
    assert len(codes) == 134
    assert sum(c["status"] == "active" for c in codes.values()) == 128
    assert sorted(c for c, v in codes.items() if v["status"] == "reserved") == \
        ["KHG-D004", "KHG-D006", "KHG-P006", "KHG-P015", "KHG-S008", "KHG-S012"]
    assert len(reg["planned"]) == 31 and not {p["code"] for p in reg["planned"]} & set(codes)
    cases = data.load_json("malformed-cases.json")
    assert cases["format"] == "khg-malformed-cases/1.0.0" and cases["count"] == len(cases["cases"]) == 180
    assert all(codes[c["code"]]["status"] == "active" for c in cases["cases"])
    index = data.load_json("scenarios/index.json")
    ids = sorted(s["id"] for s in index["scenarios"])
    assert len(ids) == 114 and all(f"scenarios/{i}.json" in FILES for i in ids)


def test_codes_named_in_the_package_source_are_active():
    """Reserved codes are never emitted (§8.1) and planned codes are not registered until they ship (§12.2), so every
    code the package source names is an active one. The malformed cases check what they reach; this also covers the
    linter, the store, the loaders, the scorers and migrate (a planned or reserved code passed before)."""
    reg = data.load_json("error-codes.json")
    active = {c["code"] for c in reg["codes"] if c["status"] == "active"}
    src = Path(jsonio.__file__).resolve().parent
    used = {}
    for p in sorted(src.rglob("*.py")):
        for code in re.findall(r"KHG-[A-Z][0-9]{3}", p.read_text(encoding="utf-8")):
            used.setdefault(code, p.name)
    assert used, "the scan found no code at all"
    assert {c: f for c, f in used.items() if c not in active} == {}
