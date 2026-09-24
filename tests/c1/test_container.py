"""W3: container I/O: .khg.json and .khg.jsonl, canonical order, the V and C checks, container_sha256 and RFC 8785
numbers in the written text (DESIGN §2.1, §7, §10.2)."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
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


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
@pytest.mark.parametrize("umask, mode", [(0o022, 0o644), (0o027, 0o640)], ids=["umask-022", "umask-027"])
def test_the_written_file_gets_the_mode_the_umask_allows(tmp_path, umask, mode):
    """S7: as for the CLI's files and ``Queue.create``'s; the temporary file is not mkstemp's, whose mode is 0600."""
    out = tmp_path / "x.khg.jsonl"
    old = os.umask(umask)
    try:
        record.write_container(C1, out)
    finally:
        os.umask(old)
    assert stat.S_IMODE(out.stat().st_mode) == mode
    assert out.read_bytes() == JSONL_BYTES
    assert [p.name for p in tmp_path.iterdir()] == ["x.khg.jsonl"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
@pytest.mark.parametrize("mode", [0o600, 0o640, 0o444], ids=["0600", "0640", "0444"])
def test_an_existing_file_keeps_its_mode(tmp_path, mode):
    """Review integration (CLI-FILE-MODE, group ex's request): replacing a file keeps its mode, as the CLI's outputs
    and shell redirection do; it became 0644 under umask 022. A new file still gets the umask's mode."""
    out = tmp_path / "x.khg.jsonl"
    out.write_bytes(b"old\n")
    out.chmod(mode)
    old = os.umask(0o022)
    try:
        record.write_container(C1, out)
        record.write_container(C1, tmp_path / "new.khg.json")
    finally:
        os.umask(old)
    assert stat.S_IMODE(out.stat().st_mode) == mode and out.read_bytes() == JSONL_BYTES
    assert stat.S_IMODE((tmp_path / "new.khg.json").stat().st_mode) == 0o644
    assert sorted(p.name for p in tmp_path.iterdir()) == ["new.khg.json", "x.khg.jsonl"]


def test_a_failed_rename_keeps_the_old_file_and_leaves_no_temporary_file(tmp_path, monkeypatch):
    out = tmp_path / "x.khg.jsonl"
    out.write_text("old\n", encoding="utf-8")

    def refuse(src, dst):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", refuse)
    with pytest.raises(OSError):
        record.write_container(C1, out)
    assert out.read_text(encoding="utf-8") == "old\n"
    assert [p.name for p in tmp_path.iterdir()] == ["x.khg.jsonl"]


def test_a_history_container_round_trips_in_version_order(tmp_path):
    out = tmp_path / "history.khg.jsonl"
    record.write_container({"header": HISTORY["header"], "records": list(reversed(HISTORY["records"]))}, out)
    assert record.read_container(out) == HISTORY


def test_a_history_whose_carried_evidence_omits_supports_stays_valid_when_written(tmp_path):
    """§2.8.1: writing a history must not change carried evidence. With ``supports`` omitted from e1 in both versions
    of f:king-13 (v2 adds b4), the written v2 keeps e1 on b1-b3; the version rule would call b1-b4 a rewrite."""
    from khg_contracts import validate
    from khg_contracts.schema import load_schema

    schema = load_schema(data.path("fixture/fixture.relation-schema.json"))
    doc = copy.deepcopy(HISTORY)
    for r in doc["records"]:
        if r.get("id") == "f:king-13":
            r["evidence"][0].pop("supports")
    assert validate.validate_container(doc, schema=schema)["ok"]
    king13 = [r for r in doc["records"] if r["id"] == "f:king-13"]
    for name in ("history.khg.jsonl", "history.khg.json"):
        record.write_container(doc, tmp_path / name)
        back = record.read_container(tmp_path / name)
        assert back == HISTORY
        report = validate.validate_container(back, schema=schema)
        assert report["ok"], [f for f in report["findings"] if f["severity"] == "error"]
        assert record.supported_values([r for r in back["records"] if r["id"] == "f:king-13"], "e1") == \
            record.supported_values(king13, "e1")
    assert record.container_sha256(doc) == record.container_sha256(HISTORY)


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
    """DESIGN §14 ruling 4: the suffix alone names the layout, ``.json`` or ``.jsonl``. ``format`` may restate it."""
    record.write_container(C1, tmp_path / "a.khg.jsonl", format="jsonl")
    record.write_container(C1, str(tmp_path / "a.khg.json"), format="json")
    record.write_container(C1, tmp_path / "b.jsonl")
    assert (tmp_path / "a.khg.jsonl").read_bytes() == (tmp_path / "b.jsonl").read_bytes() == JSONL_BYTES
    assert record.read_container(tmp_path / "a.khg.json") == record.read_container(str(tmp_path / "b.jsonl")) == C1
    with pytest.raises(ValueError):
        record.serialize(C1, format="xml")


@pytest.mark.parametrize("name, fmt", [
    ("a.khg.json", "jsonl"),   # a format the suffix does not name (the old rule let an explicit format win)
    ("a.khg.jsonl", "json"),
    ("a.khg.jsonl", "yaml"),
    ("noext", None),           # the old rule wrote any other name as JSONL, which read_container read as JSON
    ("a.txt", None),
    ("a.txt", "jsonl"),
    ("a.khg.JSON", None),
    ("a.jsonl.bak", "jsonl"),
])
def test_write_refuses_a_suffix_that_names_no_layout_or_another_one(tmp_path, name, fmt):
    for container in (C1, {"header": {"format": "khg-record/9.0.0"}, "records": []}):  # the suffix is checked first
        with pytest.raises(ValueError) as e:
            record.write_container(container, tmp_path / name, format=fmt)
        assert type(e.value) is ValueError  # not a ValidationError of the container
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", ["a.txt", "noext", "a.khg.JSONL", "a.json.gz"])
def test_read_refuses_a_suffix_that_names_no_layout(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(JSONL_BYTES)  # what the old writer put into any name but .json
    with pytest.raises(ValueError) as e:
        record.read_container(path)
    assert type(e.value) is ValueError and name in str(e.value)
    with pytest.raises(ValueError) as e:  # before any read: a missing file with such a name is the same error
        record.read_container(tmp_path / ("missing-" + name))
    assert type(e.value) is ValueError


def _deep_container(levels):
    doc = copy.deepcopy(C1)
    value = 1
    for _ in range(levels):
        value = [value]
    next(r for r in doc["records"] if r.get("id") == "f:reg-1").setdefault("extensions", {})["ex:deep"] = value
    return doc


def test_a_container_at_the_nesting_limit_is_written_and_read_back(tmp_path):
    """Layer J accepts at most ``jsonio.MAX_DEPTH`` levels, and the record functions process what it accepts."""
    levels = jsonio.MAX_DEPTH - 4  # under the root, the records, the record and its extensions
    doc = _deep_container(levels)
    for name in ("deep.khg.json", "deep.khg.jsonl"):
        record.write_container(doc, tmp_path / name)
        assert jsonio.canonical(record.read_container(tmp_path / name)) == \
            jsonio.canonical(record.canonical_container(doc))
    (tmp_path / "deeper.khg.json").write_text(json.dumps(_deep_container(levels + 1)), encoding="utf-8")
    err = raises(record.read_container, tmp_path / "deeper.khg.json")
    assert err.codes == ("KHG-J001",) and err.info["findings"][0]["path"].startswith("/records/")


def test_the_canonical_form_and_hash_take_any_depth_in_memory():
    """An object that never went through layer J may nest deeper than the Python stack allows (the recursive
    walkers met RecursionError near 500 levels on Python 3.10 and 3.11). The V and C checks of
    ``write_container`` run jsonschema, whose own walk is not the package's."""
    from khg_contracts.schema import load_schema

    doc = _deep_container(1500)
    reg = next(r for r in doc["records"] if r.get("id") == "f:reg-1")
    assert jsonio.canonical(record.normalize(reg)["extensions"]) == jsonio.canonical(reg["extensions"])
    record.with_derived(reg, load_schema(data.path("fixture/fixture.relation-schema.json")))
    text = record.serialize(doc)
    assert text.count("[" * 1500 + "1" + "]" * 1500) == 1
    assert record.container_sha256(doc) == "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------------------------------------ digests


def test_container_sha256_is_the_hash_of_the_canonical_jsonl_text():
    assert record.container_sha256(C1) == "sha256:" + hashlib.sha256(JSONL_BYTES).hexdigest()
    shuffled = {"header": C1["header"], "records": list(reversed(C1["records"]))}
    assert record.container_sha256(shuffled) == record.container_sha256(C1)


def test_a_lone_surrogate_is_j005_when_writing_and_hashing(tmp_path):
    """A container built in memory may hold one (a parsed one cannot: J005 at parse time); UTF-8 cannot."""
    doc = copy.deepcopy(C1)
    next(r for r in doc["records"] if r.get("id") == "ex:AirCanada")["label"] = "Air Canada \ud800"
    assert record.check_container(doc) == []  # V and C pass
    for fn, args in ((record.write_container, (doc, tmp_path / "x.khg.jsonl")), (record.container_sha256, (doc,))):
        assert raises(fn, *args).codes == ("KHG-J005",)
    assert list(tmp_path.iterdir()) == []
    assert _codes_of_digest(doc) == ("KHG-J005",)


def _codes_of_digest(doc):
    return raises(jsonio.digest, "khg-timed/1", doc).codes


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
