"""W2: the schema generator reproduces every packaged draft-07 schema byte for byte, and the meta-schema of the
relation-type schema language follows the conventions of §8.1 (codes on every constraint, absolute refs, no
oneOf/anyOf)."""
from __future__ import annotations

import pytest

from khg_contracts import data
from khg_contracts.schema import codegen

GENERATED = sorted(codegen.build_all())
META = data.load_json("schemas/khg-relation-schema-1.0.0.schema.json")
REGISTRY = {c["code"]: c for c in data.load_json("error-codes.json")["codes"]}


def test_the_generator_covers_five_schemas():
    assert GENERATED == ["khg-c4-items-0.1.0.schema.json", "khg-c5-io-1.0.0.schema.json", "khg-hif-1.0.0.schema.json",
                         "khg-record-1.0.0.schema.json", "khg-relation-schema-1.0.0.schema.json"]


@pytest.mark.parametrize("name", GENERATED)
def test_generated_equals_packaged_bytes(name):
    assert codegen.render(codegen.build(name[: -len(".schema.json")])).encode("utf-8") == \
        data.read_bytes(f"schemas/{name}")


def test_write_all_and_the_command(tmp_path):
    paths = codegen.write_all(tmp_path / "out")
    assert sorted(p.name for p in paths) == GENERATED
    assert all(p.read_bytes() == data.read_bytes(f"schemas/{p.name}") for p in paths)
    assert codegen.main([]) == 2
    assert codegen.main([str(tmp_path / "again")]) == 0
    assert sorted(p.name for p in (tmp_path / "again").iterdir()) == GENERATED


def _walk(s, path="#"):
    """Every subschema, following the schema keywords (as ``codegen.propagate`` does)."""
    if not isinstance(s, dict):
        return
    yield path, s
    for k in codegen.CHILD_MAPS:
        for name, v in (s.get(k) or {}).items():
            yield from _walk(v, f"{path}/{k}/{name}")
    for k in codegen.CHILD_ONE:
        if isinstance(s.get(k), dict):
            yield from _walk(s[k], f"{path}/{k}")
    for k in codegen.CHILD_LIST:
        for i, v in enumerate(s.get(k) or []):
            yield from _walk(v, f"{path}/{k}/{i}")


def test_meta_schema_identity():
    assert META["$id"] == "tag:khg-contracts,2026:schema/khg-relation-schema/1.0.0"
    assert META["$schema"] == "http://json-schema.org/draft-07/schema#"


def test_every_constraint_in_the_meta_schema_names_a_registered_m_code():
    codes = set()
    for path, sub in _walk(META):
        if codegen.CONSTRAINT_KEYS & set(sub):
            assert "x-khg-code" in sub, path
        c = sub.get("x-khg-code")
        if c is not None:
            codes |= {c} if isinstance(c, str) else set(c.values())
    assert codes == {"KHG-M001", "KHG-M004", "KHG-M006", "KHG-M007", "KHG-M012", "KHG-M014", "KHG-M015"}
    assert all(REGISTRY[c]["status"] == "active" and REGISTRY[c]["layer"] == "M" for c in codes)


def test_meta_schema_refs_are_absolute_and_resolve_and_it_uses_no_oneof_or_anyof():
    refs = [sub["$ref"] for _, sub in _walk(META) if "$ref" in sub]
    assert refs and all(r.startswith(META["$id"] + "#/definitions/") for r in refs)
    assert all(r.split("/")[-1] in META["definitions"] for r in refs)
    assert not any({"oneOf", "anyOf"} & set(sub) for _, sub in _walk(META))
