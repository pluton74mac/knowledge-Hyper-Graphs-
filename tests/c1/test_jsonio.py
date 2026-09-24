"""W1: layer J (strict parse), canonical JSON with RFC 8785 numbers, and digest (DESIGN §2.1, §2.9, §8.1)."""
from __future__ import annotations

import copy
import hashlib
import struct

import pytest

from khg_contracts import data, jsonio
from khg_contracts.errors import ValidationError

J_CASES = [c for c in data.load_json("malformed-cases.json")["cases"] if c["layer"] == "J"]

# RFC 8785 Appendix B: the 24 finite IEEE-754 test vectors (NaN and Infinity are J004)
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
FIXTURE_SCHEMA_SHA256 = "sha256:cadd01cd3d37e09337d2fe70bd5572a32dff4a7d6f4a0ac26845c6c27d0e194d"


def _codes(fn, *args):
    with pytest.raises(ValidationError) as exc:
        fn(*args)
    return exc.value


# ------------------------------------------------------------------------------------------------ layer J


def test_the_list_has_the_eight_j_cases():
    assert len(J_CASES) == 8
    assert sorted({c["code"] for c in J_CASES}) == [f"KHG-J00{i}" for i in range(1, 8)]


@pytest.mark.parametrize("case", J_CASES, ids=[c["id"] for c in J_CASES])
def test_j_case_is_rejected_with_its_code(case):
    err = _codes(jsonio.loads, case["input_text"])
    assert err.codes == (case["code"],)
    assert [f["layer"] for f in err.info["findings"]] == ["J"]
    assert err.info["findings"][0]["severity"] == "error"


@pytest.mark.parametrize("case", J_CASES, ids=[c["id"] for c in J_CASES])
def test_j_case_as_utf8_bytes_gives_the_same_code(case):
    assert _codes(jsonio.loads, case["input_text"].encode("utf-8")).codes == (case["code"],)


@pytest.mark.parametrize("raw, code", [
    (b"", "KHG-J001"),
    (b"  \n\t ", "KHG-J001"),
    (b'{"a": 1} trailing', "KHG-J001"),
    (b'{"a": 1,}', "KHG-J001"),
    (b'{"a": "tab\tinside"}', "KHG-J001"),
    (b'\xef\xbb\xbf{"a": 1}', "KHG-J002"),
    (b'{"a": "\xff"}', "KHG-J002"),
    (b'{"a": "\xed\xa0\x80"}', "KHG-J002"),
    (b'{"a": {"b": 1, "b": 2}}', "KHG-J003"),
    (b'{"a": [Infinity]}', "KHG-J004"),
    (b'{"a": -Infinity}', "KHG-J004"),
    (b'{"a": 1e400}', "KHG-J004"),
    (b'{"a": "\\udc00"}', "KHG-J005"),
    (b'{"\\ud800": 1}', "KHG-J005"),
    (b'{"a": 9007199254740992}', "KHG-J006"),
    (b'{"a": -9007199254740992}', "KHG-J006"),
    (b'"a string"', "KHG-J007"),
    (b"null", "KHG-J007"),
    (b"[{}]", "KHG-J007"),
])
def test_strict_parse_codes(raw, code):
    assert _codes(jsonio.loads, raw).codes == (code,)


@pytest.mark.parametrize("raw, code", [
    (b'{"a": 10000000000000000}', "KHG-J006"),
    (b'{"a": 1' + b"0" * 4300 + b'}', "KHG-J006"),  # beyond int()'s 4300 digits: a plain ValueError before
    (b'{"a": -1' + b"0" * 5000 + b'}', "KHG-J006"),
    (b'{"a": ' + b"[" * 256 + b"1" + b"]" * 256 + b'}', "KHG-J001"),  # 257 levels, one more than MAX_DEPTH
], ids=["17-digits", "4301-digits", "negative-5001-digits", "257-levels"])
def test_strict_parse_codes_of_long_and_deep_documents(raw, code):
    assert _codes(jsonio.loads, raw).codes == (code,)
    assert _codes(jsonio.loads_lines, raw).codes == (code,)


def test_integers_of_any_length_are_j006_on_every_path():
    big = "1" + "0" * 5000
    err = _codes(jsonio.loads_lines, '{"a": 1}\n{"b": ' + big + "}\n")
    assert err.codes == ("KHG-J006",) and err.info["findings"][0]["path"] == "/lines/1"
    assert len(err.info["findings"][0]["message"]) < 200  # the digits are not all repeated
    assert jsonio.loads('{"a": 9007199254740991, "b": -9007199254740991, "c": -0}') == \
        {"a": 2 ** 53 - 1, "b": -(2 ** 53 - 1), "c": 0}
    for x in (2 ** 53, 10 ** 5000, -(10 ** 5000)):  # str() of the last two is itself a ValueError
        assert _codes(jsonio.canonical, {"x": x}).codes == ("KHG-J006",)
    from khg_contracts import validate
    for source in (b'{"header": {"n": ' + big.encode() + b'}, "records": []}', ('{"n": ' + big + "}").encode()):
        report = validate.validate(source, kind="container")
        assert report["ok"] is False and [f["code"] for f in report["findings"]] == ["KHG-J006"]


def test_nesting_is_limited_to_max_depth_levels_whatever_the_python_version():
    """An explicit limit (the parser's own is near 1000 levels on 3.10 and 3.11 and far higher on 3.13); the finding
    points at the first value too deep, as layer J's does for an object in memory."""
    assert jsonio.MAX_DEPTH == 256

    def text(levels):  # levels of nested objects under the key "a"
        return '{"a":' * levels + "1" + "}" * levels

    assert jsonio.loads(text(jsonio.MAX_DEPTH))["a"]["a"]["a"]
    for levels in (jsonio.MAX_DEPTH + 1, 600, 3000):
        err = _codes(jsonio.loads, text(levels))
        assert err.codes == ("KHG-J001",)
        if levels < 900:  # beyond what the parser reaches from the caller's stack the path is the document's
            assert err.info["findings"][0]["path"] == "/a" * jsonio.MAX_DEPTH
            assert err.info["findings"][0]["message"] == f"nesting deeper than {jsonio.MAX_DEPTH} levels"
    err = _codes(jsonio.loads_lines, '{"k": 1}\n{"x~y/z": [[' + "[" * 300 + "]" * 300 + "]]}\n")
    assert err.codes == ("KHG-J001",)
    assert err.info["findings"][0]["path"] == "/lines/1/x~0y~1z" + "/0" * (jsonio.MAX_DEPTH - 1)
    wide = '{"a": [' + ", ".join(["[[]]"] * 400) + "]}"  # many brackets, little depth
    assert len(jsonio.loads(wide)["a"]) == 400


def test_canonical_writes_any_depth_and_refuses_a_cycle():
    deep = 1
    for _ in range(5000):  # deeper than the Python stack: written iteratively, the same text
        deep = [deep, {"k": "e\u0301"}]
    text = jsonio.canonical(deep)
    assert text.startswith("[" * 5000 + "1,{") and text.endswith('{"k":"\u00e9"}]') and len(text) == 5000 * 12 + 1
    shallow = {"b": [1, {"c": None, "a": "x"}], "a": []}
    from khg_contracts.jsonio import _write_deep
    out: list = []
    _write_deep(shallow, out)
    assert "".join(out) == jsonio.canonical(shallow) == '{"a":[],"b":[1,{"a":"x","c":null}]}'
    loop: dict = {"a": []}
    loop["a"].append(loop)
    with pytest.raises(ValueError):
        jsonio.canonical(loop)


def test_raw_lone_surrogate_in_text_is_j005():
    assert _codes(jsonio.loads, '{"a": "x\ud800y"}').codes == ("KHG-J005",)


def test_valid_documents_parse_to_their_values():
    assert jsonio.loads(b'{"a": [1, 2.5, -0, true, null], "b": {"c": "\\ud83d\\ude00"}}') == \
        {"a": [1, 2.5, 0, True, None], "b": {"c": "\U0001F600"}}
    assert jsonio.loads('{"max": 9007199254740991, "min": -9007199254740991}') == \
        {"max": 2 ** 53 - 1, "min": -(2 ** 53 - 1)}
    assert jsonio.loads(' \n{"k": "\u2028"}\n ') == {"k": "\u2028"}


def test_syntax_error_info_carries_the_position():
    err = _codes(jsonio.loads, '{\n "a": }')
    assert err.codes == ("KHG-J001",)
    assert err.info["lineno"] == 2


def test_load_reads_paths_and_packaged_files(tmp_path):
    p = tmp_path / "doc.json"
    p.write_bytes('{"z": 1, "a": "Łódź"}'.encode())
    assert jsonio.load(p) == {"z": 1, "a": "Łódź"}
    assert jsonio.load(str(p)) == {"z": 1, "a": "Łódź"}
    assert jsonio.load(data.path("fixture/fixture.c1.json"))["header"]["document_id"] == "p2-gate-fixture"
    (tmp_path / "dup.json").write_bytes(b'{"a": 1, "a": 1}')
    assert _codes(jsonio.load, tmp_path / "dup.json").codes == ("KHG-J003",)


def test_jsonl_lines_parse_and_equal_the_json_container():
    lines = jsonio.load_lines(data.path("fixture/fixture.c1.jsonl"))
    container = data.load_json("fixture/fixture.c1.json")
    assert lines == [container["header"]] + container["records"]
    assert len(lines) == 41


def test_jsonl_findings_address_the_line():
    err = _codes(jsonio.loads_lines, '{"kind": "a"}\n\n[1]\n')
    assert err.codes == ("KHG-J007",)
    assert err.info["findings"][0]["path"] == "/lines/1"
    assert err.info["index"] == 1 and err.info["lineno"] == 3
    err = _codes(jsonio.loads_lines, b'{"a": 1}\r\n{"a": 1, "a": 2}\r\n')
    assert err.codes == ("KHG-J003",) and err.info["findings"][0]["path"] == "/lines/1"
    assert _codes(jsonio.loads_lines, b"").codes == ("KHG-J001",)
    assert _codes(jsonio.loads_lines, b"\xef\xbb\xbf{}").codes == ("KHG-J002",)


def test_jsonl_splits_on_newline_only():
    # U+2028 and U+0085 are line breaks for str.splitlines() but may appear raw inside a JSON string
    assert jsonio.loads_lines('{"a": "x\u2028y\x85z"}\n{"b": 2}') == [{"a": "x\u2028y\x85z"}, {"b": 2}]


# ------------------------------------------------------------------------------------------------ canonical JSON


@pytest.mark.parametrize("hexbits, want", RFC8785_VECTORS, ids=[w for _, w in RFC8785_VECTORS])
def test_rfc8785_appendix_b_number(hexbits, want):
    x = struct.unpack(">d", bytes.fromhex(hexbits))[0]
    assert jsonio.number(x) == want
    assert jsonio.canonical({"n": x}) == '{"n":' + want + "}"


def test_there_are_24_finite_vectors():
    assert len(RFC8785_VECTORS) == 24


@pytest.mark.parametrize("value, want", [
    (2.0, "2"), (-0.0, "0"), (0, "0"), (100.0, "100"), (0.1, "0.1"), (1e21, "1e+21"), (1e20, "100000000000000000000"),
    (1e-7, "1e-7"), (1.5e-6, "0.0000015"), (123.456, "123.456"), (-2.5, "-2.5"), (7.5, "7.5"),
    (2 ** 53 - 1, "9007199254740991"), (-(2 ** 53 - 1), "-9007199254740991"),
])
def test_number_forms(value, want):
    assert jsonio.number(value) == want


@pytest.mark.parametrize("value, code", [(float("nan"), "KHG-J004"), (float("inf"), "KHG-J004"),
                                         (float("-inf"), "KHG-J004"), (2 ** 53, "KHG-J006")])
def test_numbers_that_have_no_canonical_form(value, code):
    assert _codes(jsonio.canonical, {"x": value}).codes == (code,)


def test_booleans_are_not_numbers():
    with pytest.raises(TypeError):
        jsonio.number(True)
    assert jsonio.canonical([True, False, None, 1]) == "[true,false,null,1]"


def test_canonical_sorts_keys_by_code_point_without_white_space():
    obj = {"b": 1, "a": {"y": [3, {"k": 2.0}], "x": None}, "z": "", "\u00e9": 1, "\ufb01": 2, "\U0001F600": 3, "B": 0}
    # code-point order puts U+FB01 before U+1F600 (RFC 8785's UTF-16 order would not); §2.1 says code points
    assert jsonio.canonical(obj) == \
        '{"B":0,"a":{"x":null,"y":[3,{"k":2}]},"b":1,"z":"","\u00e9":1,"\ufb01":2,"\U0001F600":3}'


def test_canonical_normalises_strings_and_keys_to_nfc():
    decomposed = "Lo\u0301dz\u0301"  # combining acute accents
    assert jsonio.canonical({decomposed: decomposed}) == '{"L\u00f3d\u017a":"L\u00f3d\u017a"}'
    assert jsonio.canonical("e\u0301") == '"\u00e9"'


def test_keys_that_normalise_to_one_key_are_s020():
    assert _codes(jsonio.canonical, {"\u00e9": 1, "e\u0301": 2}).codes == ("KHG-S020",)


def test_canonical_string_escapes():
    assert jsonio.canonical({"s": 'q"b\\n\n\t\x01\x1f\u2028\u007f'}) == \
        '{"s":"q\\"b\\\\n\\n\\t\\u0001\\u001f\u2028\u007f"}'


def test_canonical_accepts_tuples_and_read_only_mappings_and_refuses_other_types():
    from types import MappingProxyType
    assert jsonio.canonical(MappingProxyType({"b": (1, 2), "a": []})) == '{"a":[],"b":[1,2]}'
    with pytest.raises(TypeError):
        jsonio.canonical({"a": {1, 2}})
    with pytest.raises(TypeError):
        jsonio.canonical({1: "non-string key"})


def test_canonical_jsonl_files_are_canonical_line_by_line():
    for rel in ("fixture/fixture.c1.jsonl", "fixture/smoke-queue.khg-queue.jsonl"):
        text = data.read_text(rel)
        lines = text.split("\n")
        assert lines[-1] == ""
        for line in lines[:-1]:
            assert jsonio.canonical(jsonio.loads(line)) == line


def test_canonical_jsonl_text_of_the_smoke_base_hashes_to_the_queue_base():
    base = data.load_json("fixture/smoke-base.c1.json")
    text = "".join(jsonio.canonical(x) + "\n" for x in [base["header"]] + base["records"])
    queue_header = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")[0]
    assert "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest() == queue_header["base"]["sha256"]


# ------------------------------------------------------------------------------------------------ digest


def test_digest_of_the_fixture_schema():
    schema = data.load_json("fixture/fixture.relation-schema.json")
    assert jsonio.digest("khg-schema/1", schema) == FIXTURE_SCHEMA_SHA256
    assert data.load_json("fixture/fixture.c1.json")["header"]["schema"]["sha256"] == FIXTURE_SCHEMA_SHA256


def test_digest_is_the_sha256_of_domain_newline_canonical_json():
    payload = {"relation": "born_in", "bindings": [["person", None, {"entity": "ex:Maria_Sk\u0142odowska"}]]}
    want = hashlib.sha256(("khg-content-key/1\n" + jsonio.canonical(payload)).encode("utf-8")).hexdigest()
    assert jsonio.digest("khg-content-key/1", payload) == "sha256:" + want
    assert jsonio.hexdigest("khg-content-key/1", payload) == want
    assert jsonio.digest("khg-core-key/1", payload) != jsonio.digest("khg-content-key/1", payload)


def test_max_10_and_max_10_point_0_give_one_digest():
    schema = data.load_json("fixture/fixture.relation-schema.json")
    as_float = copy.deepcopy(schema)
    as_float["confidence_scales"][0]["max"] = 10.0
    assert isinstance(schema["confidence_scales"][0]["max"], int)
    assert jsonio.digest("khg-schema/1", as_float) == jsonio.digest("khg-schema/1", schema) == FIXTURE_SCHEMA_SHA256


def test_digest_ignores_key_order_and_normalisation_form():
    a = {"b": "e\u0301", "a": 1.0}
    b = {"a": 1, "b": "\u00e9"}
    assert jsonio.digest("khg-timed/1", a) == jsonio.digest("khg-timed/1", b)


@pytest.mark.parametrize("domain", ["", "two\nlines", None])
def test_bad_domains_are_refused(domain):
    with pytest.raises(ValueError):
        jsonio.digest(domain, {})


def test_a_lone_surrogate_cannot_be_hashed():
    assert _codes(jsonio.digest, "khg-timed/1", {"a": "\ud800"}).codes == ("KHG-J005",)
