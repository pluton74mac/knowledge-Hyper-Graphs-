"""W3: container I/O: .khg.json and .khg.jsonl, canonical order, the V and C checks, container_sha256 and RFC 8785
numbers in the written text (DESIGN §2.1, §7, §10.2)."""
from __future__ import annotations

import copy
import hashlib
import struct

import pytest

from khg_contracts import data, jsonio, record
from khg_contracts.errors import ValidationError

C1 = data.load_json("fixture/fixture.c1.json")
JSONL_BYTES = data.read_bytes("fixture/fixture.c1.jsonl")
HISTORY = data.load_json("fixture/fixture.history.c1.json")


def raises(fn, *args, **kwargs):
    with pytest.raises(ValidationError) as exc:
        fn(*args, **kwargs)
    return exc.value


# ------------------------------------------------------------------------------------------------ reading


def test_json_and_jsonl_hold_the_same_container():
    as_json = record.read_container(data.path("fixture/fixture.c1.json"))
    as_jsonl = record.read_container(data.path("fixture/fixture.c1.jsonl"))
    assert as_json == as_jsonl == C1
    assert len(as_json["records"]) == 40
    assert jsonio.canonical(as_json) == jsonio.canonical(as_jsonl)


def test_iter_jsonl_streams_the_header_then_the_records(tmp_path):
    p = tmp_path / "fixture.khg.jsonl"
    p.write_bytes(JSONL_BYTES)
    items = record.iter_jsonl(p)
    assert next(items) == C1["header"]
    assert list(items) == C1["records"]
    assert list(record.iter_jsonl(str(p))) == [C1["header"]] + C1["records"]
    assert list(record.iter_jsonl(data.path("fixture/fixture.c1.jsonl")))[0]["kind"] == "header"


def test_iter_jsonl_reports_layer_j_by_line(tmp_path):
    p = tmp_path / "bad.khg.jsonl"
    p.write_bytes(b'{"kind": "header"}\n\n{"a": 1, "a": 2}\n')
    items = record.iter_jsonl(p)
    assert next(items) == {"kind": "header"}
    with pytest.raises(ValidationError) as exc:
        next(items)
    assert exc.value.codes == ("KHG-J003",)
    assert exc.value.info["findings"][0]["path"] == "/lines/1"
    assert exc.value.info["lineno"] == 3 and exc.value.info["index"] == 1
    p.write_bytes(b"\n\n")
    assert raises(list, record.iter_jsonl(p)).codes == ("KHG-J001",)
    p.write_bytes(b'\xef\xbb\xbf{"kind": "header"}\n')
    assert raises(list, record.iter_jsonl(p)).codes == ("KHG-J002",)
    p.write_bytes(b'[1]\n')
    assert raises(list, record.iter_jsonl(p)).codes == ("KHG-J007",)
    p.write_bytes(b'{"kind": "header"}\n\xff\n')
    assert raises(list, record.iter_jsonl(p)).codes == ("KHG-J002",)


def test_iter_jsonl_and_loads_lines_agree(tmp_path):
    p = tmp_path / "x.khg.jsonl"
    p.write_bytes(b'{"kind": "header"}\n \t\n' + chr(0xA0).encode() + b'\n{"kind": "entity"}\n\n')
    assert list(record.iter_jsonl(p)) == jsonio.load_lines(p) == [{"kind": "header"}, {"kind": "entity"}]


def test_jsonl_lines_end_at_newline_only(tmp_path):
    # U+2028 and U+0085 are line breaks for str.splitlines() but may appear raw inside a JSON string
    note = "a" + chr(0x2028) + "b" + chr(0x85) + "c"
    p = tmp_path / "x.khg.jsonl"
    p.write_bytes(('{"kind": "header", "note": "' + note + '"}\r\n{"kind": "entity"}\r\n').encode("utf-8"))
    assert list(record.iter_jsonl(p)) == [{"kind": "header", "note": note}, {"kind": "entity"}]


def test_read_container_checks_the_version(tmp_path):
    bad = copy.deepcopy(C1)
    bad["header"]["format"] = "khg-record/1.1.0"
    p = tmp_path / "newer.khg.json"
    p.write_text(jsonio.canonical(bad), encoding="utf-8")
    assert raises(record.read_container, p).codes == ("KHG-V001",)
    p = tmp_path / "broken.khg.jsonl"
    p.write_bytes(b'{"kind": "header"')
    assert raises(record.read_container, p).codes == ("KHG-J001",)
    p = tmp_path / "records-only.khg.jsonl"
    p.write_bytes(b'{"kind": "entity", "id": "ex:a", "types": ["Place"]}\n')
    assert raises(record.read_container, p).codes == ("KHG-V001",)


# ------------------------------------------------------------------------------------------------ writing


def test_writing_jsonl_reproduces_the_packaged_file(tmp_path):
    shuffled = {"header": C1["header"], "records": list(reversed(C1["records"]))}
    out = tmp_path / "fixture.khg.jsonl"
    record.write_container(shuffled, out, format="jsonl")
    assert out.read_bytes() == JSONL_BYTES
    assert record.serialize(C1) == JSONL_BYTES.decode("utf-8")


def test_writing_json_and_reading_back(tmp_path):
    out = tmp_path / "fixture.khg.json"
    record.write_container(C1, out)  # the suffix picks JSON
    text = out.read_text(encoding="utf-8")
    lines = text.split("\n")
    assert lines[0] == "{" and lines[1].startswith(' "header": {') and lines[2] == ' "records": ['
    assert [line.strip().rstrip(",") for line in lines[3:43]] == [jsonio.canonical(r) for r in C1["records"]]
    assert lines[43:] == [" ]", "}", ""]
    assert record.read_container(out) == C1
    assert record.serialize({"header": C1["header"], "records": []}, format="json") == \
        '{\n "header": ' + jsonio.canonical(C1["header"]) + ',\n "records": []\n}\n'


def test_write_normalises_records(tmp_path):
    raw = copy.deepcopy(C1)
    for r in raw["records"]:
        if r["kind"] == "hyperedge":
            if r["rank"] == "normal":
                r.pop("rank")  # the defaults are written back
            r.pop("visibility")
            r["bindings"].reverse()
            r["derived"] = {"stale": True}
    out = tmp_path / "x.khg.jsonl"
    record.write_container(raw, out)
    assert out.read_bytes() == JSONL_BYTES


def test_a_history_container_round_trips_in_version_order(tmp_path):
    out = tmp_path / "history.khg.jsonl"
    record.write_container({"header": HISTORY["header"], "records": list(reversed(HISTORY["records"]))}, out)
    assert record.read_container(out) == HISTORY


def test_write_refuses_another_version_and_writes_nothing(tmp_path):
    for fmt in ("khg-record/2.0.0", "khg-record/1.1.0", "khg-record", None):
        bad = copy.deepcopy(C1)
        bad["header"]["format"] = fmt
        out = tmp_path / "x.khg.jsonl"
        assert raises(record.write_container, bad, out).codes == ("KHG-V001",)
        assert not out.exists()
    patch = copy.deepcopy(C1)
    patch["header"]["format"] = "khg-record/1.0.7"
    record.write_container(patch, tmp_path / "patch.khg.jsonl")
    assert record.read_container(tmp_path / "patch.khg.jsonl")["header"]["format"] == "khg-record/1.0.7"


@pytest.mark.parametrize("where, value, code", [
    (("records", 35, "status"), "believed", "KHG-C002"),       # MC066
    (("records", 33, "bindings", 2, "value", "literal", "unit"), None, "KHG-C004"),  # MC068: no unit
    (("records", 30, "bindings", 4, "value", "literal", "precision"), 15, "KHG-C004"),  # MC069
    (("records", 35, "bindings", 0, "bid"), "b 1", "KHG-C011"),  # MC081
    (("records", 35, "colour"), "red", "KHG-C009"),
    (("header", "content"), "delta", "KHG-C002"),
])
def test_write_refuses_structural_faults_with_c_codes(tmp_path, where, value, code):
    bad = copy.deepcopy(C1)
    target = bad
    for step in where[:-1]:
        target = target[step]
    if value is None:
        del target[where[-1]]
    else:
        target[where[-1]] = value
    out = tmp_path / "x.khg.jsonl"
    err = raises(record.write_container, bad, out)
    assert code in err.codes and all(c.startswith("KHG-C") for c in err.codes)
    assert not out.exists()
    assert code in [f["code"] for f in record.check_container(bad)]


def test_check_container_passes_the_packaged_containers():
    for rel in ("fixture/fixture.c1.json", "fixture/fixture.history.c1.json", "fixture/smoke-base.c1.json",
                "fixture/fixture.with-derived.c1.json", "sample/sample.khg.json"):
        assert record.check_container(data.load_json(rel)) == [], rel


def test_formats_and_suffixes(tmp_path):
    record.write_container(C1, tmp_path / "a.khg.json", format="jsonl")  # an explicit format wins
    assert (tmp_path / "a.khg.json").read_bytes() == JSONL_BYTES
    record.write_container(C1, tmp_path / "noext")
    assert (tmp_path / "noext").read_bytes() == JSONL_BYTES
    with pytest.raises(ValueError):
        record.write_container(C1, tmp_path / "b.khg.jsonl", format="yaml")
    with pytest.raises(ValueError):
        record.serialize(C1, format="xml")


# ------------------------------------------------------------------------------------------------ digests


def test_container_sha256_is_the_hash_of_the_canonical_jsonl_text():
    assert record.container_sha256(C1) == "sha256:" + hashlib.sha256(JSONL_BYTES).hexdigest()
    shuffled = {"header": C1["header"], "records": list(reversed(C1["records"]))}
    assert record.container_sha256(shuffled) == record.container_sha256(C1)


def test_container_sha256_of_the_smoke_base_is_the_queue_base():
    base = data.load_json("fixture/smoke-base.c1.json")
    header = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")[0]
    assert header["base"] == {"document_id": "p2-smoke-base", "sha256": record.container_sha256(base)}


RFC8785_VECTORS = [
    ("0000000000000000", "0"), ("8000000000000000", "0"), ("0000000000000001", "5e-324"),
    ("8000000000000001", "-5e-324"), ("7fefffffffffffff", "1.7976931348623157e+308"),
    ("ffefffffffffffff", "-1.7976931348623157e+308"), ("4340000000000000", "9007199254740992"),
    ("c340000000000000", "-9007199254740992"), ("4430000000000000", "295147905179352830000"),
    ("44b52d02c7e14af5", "9.999999999999997e+22"), ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"), ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"), ("444b1ae4d6e2ef50", "1e+21"),
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"), ("3eb0c6f7a0b5ed8d", "0.000001"),
    ("41b3de4355555553", "333333333.3333332"), ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"), ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"), ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),
]


def test_written_containers_use_rfc8785_numbers():
    numbers = [struct.unpack(">d", bytes.fromhex(h))[0] for h, _ in RFC8785_VECTORS]
    doc = copy.deepcopy(C1)
    tp53 = next(r for r in doc["records"] if r.get("id") == "ex:TP53")
    tp53["extensions"]["ex:vectors"] = numbers
    tp53["extensions"]["hif:weight"] = 3.0  # an integral double is written without a fraction
    line = next(x for x in record.serialize(doc).split("\n") if '"ex:TP53"' in x)
    assert '"ex:vectors":[' + ",".join(w for _, w in RFC8785_VECTORS) + "]" in line
    assert '"hif:weight":3}' in line
    assert record.container_sha256(doc) != record.container_sha256(C1)
    doc_int = copy.deepcopy(doc)
    next(r for r in doc_int["records"] if r.get("id") == "ex:TP53")["extensions"]["hif:weight"] = 3
    assert record.container_sha256(doc_int) == record.container_sha256(doc)
