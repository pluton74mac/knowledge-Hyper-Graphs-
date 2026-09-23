"""W2: layer M on relation-type schema documents: the 19 M cases of the G2 list, the V gate, the bases and the
checks beyond the case list (DESIGN §3, §8.1, §8.2)."""
from __future__ import annotations

import copy

import pytest

from khg_contracts import data
from khg_contracts.errors import ValidationError
from khg_contracts.schema import Schema, check_schema, load_schema
from khg_contracts.schema.checks import meta_findings, python_findings

ENGINES = ("jsonschema", "fastjsonschema")
PIPELINE = "JVM"
CASES = data.load_json("malformed-cases.json")
M_CASES = [c for c in CASES["cases"] if c["kind"] == "relation-schema"]
REGISTRY = {c["code"]: c for c in data.load_json("error-codes.json")["codes"]}
BASE = data.load_json("fixture/fixture.relation-schema.json")
BASES = ["fixture/fixture.relation-schema.json", "fixture/cyclic.relation-schema.json",
         "fixture/wikidata-shaped.relation-schema.json", "sample/sample.relation-schema.json"]


def _parts(pointer: str) -> list[str]:
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]


def _resolve(doc, pointer):
    for p in _parts(pointer):
        doc = doc[int(p)] if isinstance(doc, list) else doc[p]
    return doc


def apply_patch(doc, patch):
    """RFC 6902 add, replace and remove (the operations the case list uses)."""
    doc = copy.deepcopy(doc)
    for op in patch:
        parts = _parts(op["path"])
        parent = _resolve(doc, "".join("/" + p.replace("~", "~0").replace("/", "~1") for p in parts[:-1]))
        last = parts[-1]
        if op["op"] == "replace":
            if isinstance(parent, list):
                parent[int(last)] = op["value"]
            else:
                assert last in parent
                parent[last] = op["value"]
        elif op["op"] == "add":
            if isinstance(parent, list) and last == "-":
                parent.append(op["value"])
            elif isinstance(parent, list):
                parent.insert(int(last), op["value"])
            else:
                parent[last] = op["value"]
        elif op["op"] == "remove":
            del parent[int(last) if isinstance(parent, list) else last]
        else:  # pragma: no cover - the list uses only the three operations above
            raise AssertionError(op["op"])
    return doc


def _error_codes(findings):
    return {f["code"] for f in findings if f["severity"] == "error"}


def _first_layer(findings):
    layers = {f["layer"] for f in findings if f["severity"] == "error"}
    return next((letter for letter in PIPELINE if letter in layers), None)


# ------------------------------------------------------------------------------------------------ the M cases


def test_the_list_has_19_m_cases_covering_every_m_code():
    assert len(M_CASES) == 19
    m_codes = sorted(c for c, v in REGISTRY.items() if v["layer"] == "M" and v["status"] == "active")
    assert m_codes == [f"KHG-M{i:03d}" for i in range(1, 18)]
    assert sorted({c["code"] for c in M_CASES}) == m_codes
    assert all(c["layer"] == "M" and c["base"] == "fixture.relation-schema.json" for c in M_CASES)


@pytest.mark.parametrize("case", M_CASES, ids=[c["id"] for c in M_CASES])
def test_m_case_self_checks(case):
    for pointer, want in (case.get("expect_target") or {}).items():
        assert _resolve(BASE, pointer)["id"] == want
    assert apply_patch(BASE, case["patch"]) != BASE


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case", M_CASES, ids=[c["id"] for c in M_CASES])
def test_m_case_is_rejected_first_at_layer_m_with_its_code(case, engine):
    findings = check_schema(apply_patch(BASE, case["patch"]), engine=engine)
    assert _first_layer(findings) == "M"
    assert case["code"] in _error_codes(findings)
    assert _error_codes(findings) == set(case["reported"])


@pytest.mark.parametrize("case", M_CASES, ids=[c["id"] for c in M_CASES])
def test_single_fault_engine_containment(case):
    doc = apply_patch(BASE, case["patch"])
    fast = _error_codes(check_schema(doc, engine="fastjsonschema"))
    full = _error_codes(check_schema(doc, engine="jsonschema"))
    assert len(fast) == 1 and fast <= full


@pytest.mark.parametrize("case", M_CASES, ids=[c["id"] for c in M_CASES])
def test_load_schema_raises_the_case_code(case):
    with pytest.raises(ValidationError) as exc:
        load_schema(apply_patch(BASE, case["patch"]))
    assert case["code"] in exc.value.codes
    assert all(f["layer"] == "M" for f in exc.value.info["findings"])


def test_meta_schema_and_python_checks_split_the_codes():
    """Structure goes to the meta-schema, whole-document rules to Python; no case is reported by both."""
    structural = {"KHG-M001", "KHG-M004", "KHG-M006", "KHG-M014", "KHG-M015"}
    for case in M_CASES:
        doc = apply_patch(BASE, case["patch"])
        meta = {f["code"] for f in meta_findings(doc)}
        py = {f["code"] for f in python_findings(doc)}
        assert not (meta and py), case["id"]
        if case["code"] in structural:
            assert meta == {case["code"]}, case["id"]


# ------------------------------------------------------------------------------------------------ bases and V


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("rel", BASES)
def test_the_packaged_schemas_have_no_finding(rel, engine):
    assert check_schema(data.load_json(rel), engine=engine) == []


def test_load_schema_from_a_path_a_packaged_file_and_a_mapping(tmp_path, examples_dir):
    s1 = load_schema(data.path("fixture/fixture.relation-schema.json"))
    s2 = load_schema(BASE)
    s3 = load_schema(examples_dir / "fixture.relation-schema.json")
    s4 = load_schema(str(examples_dir / "r05.relation-schema.json"))
    assert isinstance(s1, Schema) and s1 == s2 == s3
    assert load_schema(s1) is s1
    assert s1.ref == "p2-gate/1.0.0" and s4.ref == "r05-tables/1.0.0"


@pytest.mark.parametrize("fmt", ["khg-relation-schema/1.1.0", "khg-relation-schema/2.0.0", "khg-relation-schema/1.0",
                                 "khg-schema/1.0.0", None, 1])
def test_version_gate_stops_the_run(fmt):
    doc = copy.deepcopy(BASE)
    doc["relations"][0]["roles"] = []  # an M fault the V failure must hide
    if fmt is None:
        del doc["format"]
    else:
        doc["format"] = fmt
    for engine in ENGINES:
        findings = check_schema(doc, engine=engine)
        assert [(f["code"], f["path"]) for f in findings] == [("KHG-V001", "/format")]


def test_a_newer_patch_version_is_read():
    doc = dict(BASE, format="khg-relation-schema/1.0.7")
    assert check_schema(doc) == []


def test_layer_j_before_v_when_loading_a_file(tmp_path):
    p = tmp_path / "dup.relation-schema.json"
    p.write_bytes(b'{"kind": "relation-schema", "kind": "relation-schema"}')
    with pytest.raises(ValidationError) as exc:
        load_schema(p)
    assert exc.value.codes == ("KHG-J003",)


def test_a_top_level_that_is_not_an_object_is_j007():
    assert [f["code"] for f in check_schema([BASE])] == ["KHG-J007"]


# ------------------------------------------------------------------------------------------------ further M rules


def _codes_after(mutate):
    doc = copy.deepcopy(BASE)
    mutate(doc)
    out = {}
    for engine in ENGINES:
        out[engine] = sorted(_error_codes(check_schema(doc, engine=engine)))
    assert out["fastjsonschema"] == out["jsonschema"] or set(out["fastjsonschema"]) <= set(out["jsonschema"])
    return out["jsonschema"]


def _rel(doc, rid):
    return next(r for r in doc["relations"] if r["id"] == rid)


def _use(doc, rid, role):
    return next(u for u in _rel(doc, rid)["roles"] if u["role"] == role)


@pytest.mark.parametrize("mutate, codes", [
    (lambda d: d["roles"].append({"id": "khg:mine"}), ["KHG-M008"]),
    (lambda d: d["entity_types"].append({"id": "Gene"}), ["KHG-M013"]),
    (lambda d: d["roles"].append({"id": "target"}), ["KHG-M013"]),
    (lambda d: d["entity_types"][0].update(parents=["Nowhere"]), ["KHG-M016"]),
    (lambda d: d["entity_types"][0].update(parents=["Agent"]), ["KHG-M016"]),
    (lambda d: _rel(d, "position_held").update(primary={"subject": "holder", "object": "holder"}), ["KHG-M012"]),
    (lambda d: _rel(d, "position_held").update(primary={"subject": "holder"}), ["KHG-M012"]),
    (lambda d: _rel(d, "married").update(time={"model": "interval", "start": "start_time", "end": "start_time"}),
     ["KHG-M007"]),
    (lambda d: _rel(d, "regulates").update(time={"model": "interval"}), ["KHG-M007"]),
    (lambda d: _rel(d, "regulates").update(time={"model": "invariant", "start": "x"}), ["KHG-M007"]),
    (lambda d: _use(d, "married", "end_time").update(max=2), ["KHG-M007"]),
    (lambda d: _use(d, "married", "end_time").update(fillers=[{"literal": "string"}]), ["KHG-M007"]),
    (lambda d: _use(d, "regulates", "context").update(slot="time"), ["KHG-M007"]),
    (lambda d: d.update(default_time={"model": "interval", "start": "start_time", "end": "end_time"}), ["KHG-M007"]),
    (lambda d: _rel(d, "flies_between")["constraints"][0].update(roles=["origin", "stop"]), ["KHG-M015"]),
    (lambda d: _rel(d, "flies_between")["constraints"][0].update(roles=["origin"]), ["KHG-M015"]),
    (lambda d: _rel(d, "flies_between")["constraints"][0].pop("severity"), ["KHG-M015"]),
    (lambda d: _rel(d, "flies_between")["constraints"][0].update(type="sometimes"), ["KHG-M015"]),
    (lambda d: _use(d, "station_profile", "code")["fillers"][0].update(units=["1"]), ["KHG-M015"]),
    (lambda d: _use(d, "station_profile", "code")["fillers"][0].update(precision_min=9), ["KHG-M015"]),
    (lambda d: _use(d, "claims", "claim")["fillers"][0].update(entity=["Person"]), ["KHG-M015"]),
    (lambda d: _use(d, "claims", "claim").update(fillers=[{}]), ["KHG-M015"]),
    (lambda d: _use(d, "claims", "claim")["fillers"][0].update(fact=["no_such_relation"]), ["KHG-M005"]),
    (lambda d: _use(d, "regulates", "target").update(max=0), ["KHG-M015"]),
    (lambda d: _use(d, "regulates", "target").update(slot="primary"), ["KHG-M015"]),
    (lambda d: _use(d, "regulates", "target").pop("max"), ["KHG-M015"]),
    (lambda d: _rel(d, "regulates").update(kind="rule"), ["KHG-M015"]),
    (lambda d: _rel(d, "regulates").pop("roles"), ["KHG-M001"]),
    (lambda d: _rel(d, "population")["key"].update(on_collision="merge"), ["KHG-M015"]),
    (lambda d: _rel(d, "population")["key"].update(roles=[]), ["KHG-M015"]),
    (lambda d: d["confidence_scales"].append({"id": "probability", "kind": "bounded", "min": 0, "max": 1}),
     ["KHG-M015"]),
    (lambda d: d["confidence_scales"].append(dict(d["confidence_scales"][0])), ["KHG-M015"]),
    (lambda d: d["confidence_scales"][0].update(min=10), ["KHG-M015"]),
    (lambda d: d["confidence_scales"][0].update(kind="ordinal"), ["KHG-M015"]),
    (lambda d: d.update(description="not a schema field"), ["KHG-M015"]),
    (lambda d: d.update(id="p2/gate"), ["KHG-M015"]),
    (lambda d: d.update(kind="schema"), ["KHG-M015"]),
    (lambda d: d.update(version=1), ["KHG-M004"]),
])
def test_rules_beyond_the_case_list(mutate, codes):
    assert _codes_after(mutate) == codes


def test_an_optional_on_collision_and_temporal_are_accepted():
    doc = copy.deepcopy(BASE)
    _rel(doc, "born_in")["key"] = {"roles": ["person"]}
    assert check_schema(doc) == []
    assert Schema(doc).key("born_in") == {"roles": ["person"], "temporal": False, "on_collision": "dispute"}


def test_a_time_filler_with_precision_min_is_still_a_time_usage():
    doc = copy.deepcopy(BASE)
    _use(doc, "married", "start_time")["fillers"] = [{"literal": "time", "precision_min": 11}]
    assert check_schema(doc) == []


@pytest.mark.parametrize("broken", [
    {"relations": "x"},
    {"relations": [1, "two", {"id": 3, "roles": "none"}]},
    {"relations": [{"id": "r", "roles": [1, {"role": 2, "fillers": "x"}], "key": [], "primary": "p",
                    "time": "t", "constraints": {}}]},
    {"entity_types": [{"id": "A", "parents": "B"}, 5], "roles": [{"id": ["x"]}]},
    {"confidence_scales": [{"id": "s", "kind": "bounded", "min": "0", "max": None}]},
])
def test_structurally_broken_documents_give_findings_not_exceptions(broken):
    doc = dict(copy.deepcopy(BASE), **broken)
    for engine in ENGINES:
        findings = check_schema(doc, engine=engine)
        assert findings and all(f["layer"] == "M" for f in findings)
