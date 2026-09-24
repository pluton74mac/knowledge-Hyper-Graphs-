"""W5: ``identity.relate`` against the 37 rows of [DB §2.19] (``cases.json``; DESIGN §2.9, §10.5).

Each row builds a schema holding the deciding relation, two asserted facts (the stored b and the incoming a), and
checks the label, its mirror (``relate(b, a)``), that both facts are valid C1, and the §2.5 action a write of a beside
b collides with. Under the §2.6 ruling, X3 and C4a-u are ``key_timeline`` where DB recorded ``key_conflict``.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from khg_contracts import data, identity, jsonio
from khg_contracts.errors import ValidationError
from khg_contracts.record import keys
from khg_contracts.schema import Schema, load_schema
from khg_contracts.validate import validate_record

TABLE = jsonio.load(Path(__file__).with_name("cases.json"))
CASES = TABLE["cases"]
MIRROR = {"duplicate": "duplicate", "refines": "generalises", "generalises": "refines", "distinct": "distinct",
          "key_conflict": "key_conflict", "key_timeline": "key_timeline", "negation_conflict": "negation_conflict"}
DB_ORDER = ["C1", "C1r", "C1c-i", "C1c-ii", "C2a", "C2a-naive", "C2b", "C2b'", "C2c", "C2c-k", "C3a", "C3b", "C3c",
            "C4a", "C4a-u", "C4a-o", "C4b", "I5", "I6", "I7", "I8", "I11", "I11-x", "I12", "I14", "X1", "X2", "X3",
            "X4", "X5", "X6", "X7", "X8", "X9", "C3a-supersede", "C3a-dispute", "C3a-reject"]


def schema_doc(case: dict) -> dict:
    rel = copy.deepcopy(TABLE["relations"][case["relation"]])
    if case["on_collision"]:
        rel["key"]["on_collision"] = case["on_collision"]
    return {"kind": "relation-schema", "format": "khg-relation-schema/1.0.0", "id": "identity-cases",
            "version": "1.0.0", "roles": [{"id": r} for r in sorted({u["role"] for u in rel["roles"]})],
            "relations": [rel]}


def schema_of(case: dict) -> Schema:
    """The case's schema through load_schema; a row that records an M code is used unchecked after the check."""
    doc = schema_doc(case)
    if case["schema_error"]:
        with pytest.raises(ValidationError) as e:
            load_schema(doc)
        assert case["schema_error"] in e.value.codes
        return Schema(doc)
    return load_schema(doc)


def facts(case: dict) -> tuple[dict, dict]:
    rel = TABLE["relations"][case["relation"]]["id"]

    def fact(fid: str, bindings: list) -> dict:
        return {"kind": "hyperedge", "id": fid, "relation": rel, "status": "asserted",
                "bindings": copy.deepcopy(bindings),
                "evidence": [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": f"doc:{fid}"}}]}

    return fact("f:incoming", case["incoming"]), fact("f:existing", case["existing"])


def test_the_table_holds_dbs_37_rows_in_order():
    assert [c["id"] for c in CASES] == DB_ORDER
    assert set(identity.LABELS) == set(MIRROR) and len(identity.LABELS) == 7
    assert {c["label"] for c in CASES} == set(identity.LABELS)


def test_only_the_rows_the_ruling_names_differ_from_db():
    changed = {c["id"]: (c["db_label"], c["label"]) for c in CASES if c["label"] != c["db_label"]}
    assert changed == {"C4a-u": ("key_conflict", "key_timeline"), "X3": ("key_conflict", "key_timeline")}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_relate_gives_the_label_of_the_row(case):
    s = schema_of(case)
    a, b = facts(case)
    assert identity.relate(a, b, schema=s) == case["label"]
    assert identity.relate(b, a, schema=s) == MIRROR[case["label"]]
    assert identity.relate(a, b, schema=s.doc) == case["label"]  # a schema document is used unchecked


@pytest.mark.parametrize("case", [c for c in CASES if not c["schema_error"]], ids=lambda c: c["id"])
def test_the_facts_of_the_row_are_valid_c1(case):
    s = schema_of(case)
    for f in facts(case):
        assert validate_record(f, schema=s) == {"ok": True, "findings": []}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_the_write_collides_with_the_action_of_the_row(case):
    """A key conflict is what a write raises; its action is the §2.5 table's, as DB's outcome column says (case 3a:
    a succession closes the older fact; X4: a backfill closes the incoming one; 3b and X2: a dispute)."""
    s = schema_of(case)
    a, b = facts(case)
    found = keys.collisions({b["id"]: b}, [a], s)
    if case["action"] is None:
        assert found == [] and case["label"] != "key_conflict"
    else:
        assert case["label"] == "key_conflict"
        [collision] = found
        [conflict] = collision["conflicts"]
        assert (conflict["id"], conflict["class"], conflict["action"]) == ("f:existing", "distinct", case["action"])
        assert collision["policy"] == (case["on_collision"] or TABLE["relations"][case["relation"]]["key"]
                                       ["on_collision"])


def test_the_p7_call_on_the_fixture():
    """§1.3 P7: ``identity.relate(new, old, schema=S)`` on the gate fixture's facts."""
    s = load_schema(data.path("fixture/fixture.relation-schema.json"))
    fix = {r["id"]: r for r in data.load_json("fixture/fixture.c1.json")["records"]}
    krakow = dict(fix["f:born-skłodowska-kraków"], status="asserted")
    assert identity.relate(krakow, fix["f:born-skłodowska-warszawa"], schema=s) == "key_conflict"
    # a same-day handover: the definite windows do not overlap
    assert identity.relate(fix["f:king-14"], fix["f:king-13"], schema=s) == "key_timeline"
    open_ended = copy.deepcopy(fix["f:king-14"])
    open_ended["bindings"] = [x for x in open_ended["bindings"] if x["bid"] != "b4"]
    assert identity.relate(fix["f:king-14"], open_ended, schema=s) == "refines"
    assert identity.relate(open_ended, fix["f:king-14"], schema=s) == "generalises"
    assert identity.relate(fix["f:king-14"], copy.deepcopy(fix["f:king-14"]), schema=s) == "duplicate"
    catalyst = copy.deepcopy(fix["f:cat-7"])
    catalyst["bindings"][0]["value"] = {"entity": "ex:insulin"}
    assert identity.relate(catalyst, fix["f:cat-7"], schema=s) == "negation_conflict"
    assert identity.relate(fix["f:reg-1"], fix["f:king-14"], schema=s) == "distinct"  # two relations
    with pytest.raises(ValueError):
        identity.relate(fix["ex:Paris"], fix["f:king-14"], schema=s)
