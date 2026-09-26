"""P2 ruling 22: C1 ``khg-record`` 1.1.0 and the schema language ``khg-relation-schema`` 1.1.0 (DESIGN §2, §3), from
P7's three proposals (P7 DESIGN §7.1 item 7, §8 D4; P7 ruling 4) and P3a's normalisations (P3a DESIGN §4.3,
``notes/c4-change-proposal.md`` part C; P3a ruling 2).

- **Separator key roles** (opt-in per key): ``key.separators`` names core or qualifier roles whose absence hashes as
  its own value, ``[role, null, {"absent": true}]``, as Wikidata's separators (P4155) work, instead of nulling the
  digest. A key without ``separators`` hashes exactly as in 1.0; a present separator hashes as a key role.
  ``find_by_key`` binds the key roles and any of the separators; an omitted separator is absent. M003 as for roles.
- **Non-monotone qualifiers**: ``monotone: false`` on a qualifier usage (P1480, P5102): refinement keeps the role's
  size, as for a complete role, and a new version adds no filler to it (D013). M015 on another slot.
- **``bound_conflict``**, a reason of ``khg:disputes``; a container that holds one is stamped ``khg-record/1.1.0``
  (``record.required_format``), and the store's export does so.
- **``normalize``** writes a decimal given in another writing (``1.50``, ``-0``, ``1.5e3``, a JSON number) in C1's
  canonical form, and zeroes the components of a time literal below its precision. Validation still refuses the
  other writings (C004, S006). Wikidata ids and repeated fillers stay the importer's.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

import khg_contracts
from khg_contracts import data, identity, record, schema as schema_pkg
from khg_contracts.errors import KeyCollision, VersionError
from khg_contracts.record import keys as keyrules
from khg_contracts.scorers import extraction
from khg_contracts.store import MemoryStore, Where
from khg_contracts.validate import ENGINES, engines, run, validate_container, validate_record

SCHEMA = data.load_json("fixture/fixture.relation-schema.json")
FIXTURE = data.load_json("fixture/fixture.c1.json")
BY_ID = {r["id"]: r for r in FIXTURE["records"] if "id" in r}
EVIDENCE = [{"id": "e1", "type": "curated", "mode": "manual", "source": {"doc_id": "doc:test"}}]
LODZ = {"entity": "ex:Łódź"}
KING14_KEY = "sha256:19b896a4c419199eeb0922934472e2ff229771ce0d87bcdf97bc79033ba64a96"  # DESIGN §2.5


def year(y: int) -> dict[str, Any]:
    return {"literal": {"datatype": "time", "time": f"+{y}-00-00T00:00:00Z", "precision": 9, "calendar": "gregorian"}}


def qty(amount: str) -> dict[str, Any]:
    return {"literal": {"datatype": "quantity", "amount": amount, "unit": "1"}}


def schema_with(change) -> dict[str, Any]:
    """The fixture schema, stamped 1.1.0, after ``change(doc)``."""
    doc = copy.deepcopy(SCHEMA)
    doc["format"] = "khg-relation-schema/1.1.0"
    change(doc)
    return doc


def relation(doc: dict[str, Any], rid: str) -> dict[str, Any]:
    return next(r for r in doc["relations"] if r["id"] == rid)


def pop(fid: str, amount: str, when: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    """A ``population`` fact on Łódź; ``when`` is the ``point_in_time``, ``extra`` more (role, value) bindings."""
    bs = [{"bid": "b1", "role": "place", "value": LODZ}, {"bid": "b2", "role": "quantity", "value": qty(amount)}]
    if when is not None:
        bs.append({"bid": "b3", "role": "point_in_time", "value": when})
    for n, (role, value) in enumerate(extra.items(), start=4):
        bs.append({"bid": f"b{n}", "role": role, "value": value})
    return {"kind": "hyperedge", "id": fid, "relation": "population", "status": "asserted", "bindings": bs,
            "evidence": copy.deepcopy(EVIDENCE)}


def entities(*ids: str) -> list[dict[str, Any]]:
    return [copy.deepcopy(BY_ID[i]) for i in ids]


# ------------------------------------------------------------------------------------------------ versions


def test_the_versions():
    c = khg_contracts.CONTRACTS
    assert (c["khg-record"], c["khg-relation-schema"]) == ("1.1.0", "1.1.0")
    assert record.FORMAT == "khg-record/1.0.0" and record.FORMAT_1_1 == "khg-record/1.1.0"
    assert schema_pkg.FORMAT == "khg-relation-schema/1.0.0" and schema_pkg.FORMAT_1_1 == "khg-relation-schema/1.1.0"
    assert engines.RELATION_SCHEMA_ID == "tag:khg-contracts,2026:schema/khg-relation-schema/1.1.0"
    files = data.iter_files()
    assert "schemas/khg-relation-schema-1.1.0.schema.json" in files
    assert "schemas/khg-relation-schema-1.0.0.schema.json" not in files
    assert "schemas/khg-record-1.0.0.schema.json" in files  # the record schema does not change


@pytest.mark.parametrize(("stamp", "ok"), [("khg-record/1.1.0", True), ("khg-record/1.1.3", True),
                                           ("khg-record/1.0.0", True), ("khg-record/1.2.0", False)])
def test_the_container_gate_takes_1_0_and_1_1(stamp, ok):
    c = copy.deepcopy(FIXTURE)
    c["header"]["format"] = stamp
    want = [] if ok else [("KHG-V001", "/header/format")]
    assert [(f["code"], f["path"]) for f in validate_container(c, schema=SCHEMA)["findings"]
            if f["code"].startswith("KHG-V")] == want
    assert (record.check_container(c) == []) is ok


@pytest.mark.parametrize(("stamp", "ok"), [("khg-relation-schema/1.1.0", True), ("khg-relation-schema/1.0.0", True),
                                           ("khg-relation-schema/1.2.0", False)])
def test_the_schema_gate_takes_1_0_and_1_1(stamp, ok):
    doc = dict(SCHEMA, format=stamp)
    assert (schema_pkg.check_schema(doc) == []) is ok


def test_the_other_gates_take_a_1_1_record_stamp():
    hif = data.load_json("fixture/fixture.hif.json")
    hif["metadata"]["khg-record"] = "khg-record/1.1.0"
    assert not [f for f in run(hif, kind="hif", schema=SCHEMA).findings if f["code"] == "KHG-V001"]
    hif["metadata"]["khg-record"] = "khg-record/1.2.0"
    assert [f["path"] for f in run(hif, kind="hif", schema=SCHEMA).findings] == ["/metadata/khg-record"]
    items = data.load_jsonl("fixture/c4-items-0.2.0.jsonl")
    items[0]["record_format"] = "khg-record/1.1.0"
    assert not run(items, kind="item", schema=SCHEMA).findings
    queue = data.load_jsonl("fixture/smoke-queue.khg-queue.jsonl")
    queue[0]["record_format"] = "khg-record/1.1.0"
    assert not [f for f in run(queue, kind="queue", schema=SCHEMA).findings if f["code"] == "KHG-V001"]


def test_writers_stamp_the_lowest_version():
    assert schema_pkg.required_format(SCHEMA) == "khg-relation-schema/1.0.0"
    sep = schema_with(lambda d: relation(d, "population")["key"].update(roles=["place"],
                                                                       separators=["point_in_time"]))
    assert schema_pkg.required_format(sep) == "khg-relation-schema/1.1.0"
    mono = schema_with(lambda d: relation(d, "population")["roles"][2].update(monotone=True))
    assert schema_pkg.required_format(mono) == "khg-relation-schema/1.1.0"  # any 1.1 field
    assert record.required_format(FIXTURE) == record.required_format(FIXTURE["records"]) == "khg-record/1.0.0"
    dispute = {"kind": "hyperedge", "id": "m:d", "relation": "khg:disputes", "status": "asserted",
               "reason": "bound_conflict", "bindings": []}
    assert record.required_format([*FIXTURE["records"], dispute]) == "khg-record/1.1.0"
    assert record.required_format([dict(dispute, reason="key_conflict")]) == "khg-record/1.0.0"


# ------------------------------------------------------------------------------------------------ separators


SEPARATED = schema_with(lambda d: relation(d, "population")["key"].update(roles=["place"],
                                                                         separators=["point_in_time"]))


@pytest.mark.parametrize("engine", ENGINES)
def test_a_key_may_declare_separators(engine):
    assert schema_pkg.check_schema(SEPARATED, engine=engine) == []
    s = schema_pkg.load_schema(SEPARATED)
    assert s.key("population") == {"roles": ["place"], "separators": ["point_in_time"], "temporal": False,
                                    "on_collision": "dispute"}
    assert schema_pkg.load_schema(SCHEMA).key("population") == {  # a 1.0 key has no separators entry
        "roles": ["place", "point_in_time"], "temporal": False, "on_collision": "dispute"}


@pytest.mark.parametrize(("separators", "code", "path"), [
    (["start_time"], "KHG-M003", "/key/separators/0"),     # a time usage
    (["khg:end_cause"], "KHG-M003", "/key/separators/0"),  # the built-in meta usage
    (["person"], "KHG-M003", "/key/separators/0"),         # not used by the relation
    (["holder", "position"], "KHG-M003", "/key/separators/1"),  # also a key role
    ([], "KHG-M015", "/key/separators"),                   # minItems
    (["replaces", "replaces"], "KHG-M015", "/key/separators"),  # uniqueItems
])
def test_a_bad_separator_is_refused(separators, code, path):
    doc = schema_with(lambda d: relation(d, "position_held")["key"].update(separators=separators))
    n = [r["id"] for r in doc["relations"]].index("position_held")
    assert [(f["code"], f["path"]) for f in schema_pkg.check_schema(doc)] == [(code, f"/relations/{n}{path}")]


def test_a_key_without_separators_hashes_as_in_1_0():
    king14 = BY_ID["f:king-14"]
    assert record.key_digest(king14, SCHEMA) == KING14_KEY
    assert record.key_digest(king14, schema_with(lambda d: None)) == KING14_KEY


def test_a_present_separator_hashes_as_a_key_role():
    with_2019 = pop("f:a", "+679941", year(2019))
    assert record.key_digest(with_2019, SEPARATED) == record.key_digest(with_2019, SCHEMA)  # 1.0's {place, pit}


def test_an_absent_separator_hashes_as_its_own_value():
    a, b = pop("f:a", "+679941"), pop("f:b", "+680000")
    assert record.key_digest(a, SCHEMA) is None  # 1.0: a key role absent nulls the digest
    ka = record.key_digest(a, SEPARATED)
    assert ka is not None and ka == record.key_digest(b, SEPARATED)
    assert ka != record.key_digest(pop("f:c", "+679941", year(2019)), SEPARATED)
    assert ka == jsonio_digest([["place", None, {"entity": "ex:Łódź"}], ["point_in_time", None, {"absent": True}]])
    # a special value in a separator is no value to compare: the fact is exempt, as with a key role
    assert record.key_digest(pop("f:d", "+1", {"special": "somevalue"}), SEPARATED) is None
    assert record.key_digest(pop("f:e", "+1", {"special": "novalue"}), SEPARATED) is None


def jsonio_digest(tuples: list[list[Any]]) -> str:
    from khg_contracts import jsonio
    return jsonio.digest("khg-key-digest/1", {"relation": "population", "bindings": sorted(tuples,
                                                                                         key=jsonio.canonical)})


def test_facts_without_the_separator_collide():
    store = MemoryStore(SEPARATED)
    store.put(entities("ex:Łódź"), actor="t")
    store.put([pop("f:a", "+679941")], actor="t")
    with pytest.raises(KeyCollision) as e:
        store.put([pop("f:b", "+680000")], actor="t")
    assert [c["record"] for c in e.value.info["collisions"]] == ["f:b"]
    # the same facts under the 1.0 key are exempt (a key role absent), and a dated fact is another key
    old = MemoryStore(SCHEMA)
    old.put(entities("ex:Łódź"), actor="t")
    old.put([pop("f:a", "+679941"), pop("f:b", "+680000")], actor="t")
    store.put([pop("f:c", "+679941", year(2019)), pop("f:d", "+679941", year(2020))], actor="t")


def test_find_by_key_binds_the_roles_and_any_separators():
    store = MemoryStore(SEPARATED)
    store.put(entities("ex:Łódź"), actor="t")
    store.put([pop("f:a", "+679941"), pop("f:c", "+679941", year(2019)), pop("f:d", "+1", year(2020))], actor="t")
    place = [{"role": "place", "value": LODZ}]
    assert [r["id"] for r in store.find_by_key("population", place)] == ["f:a"]  # the separator absent
    dated = place + [{"role": "point_in_time", "value": year(2019)}]
    assert [r["id"] for r in store.find_by_key("population", dated)] == ["f:c"]
    with pytest.raises(ValueError, match="separators"):
        store.find_by_key("population", place + [{"role": "quantity", "value": qty("+1")}])
    with pytest.raises(ValueError, match=r"binds exactly the key roles \['place'\] and any of the separators"):
        store.find_by_key("population", [{"role": "point_in_time", "value": year(2019)}])
    # a 1.0 key keeps its rule and its message
    with pytest.raises(ValueError, match=r"^find_by_key binds exactly the key roles \['place', 'point_in_time'\]$"):
        MemoryStore(SCHEMA).find_by_key("population", place)


def test_the_core_on_key_roles_counts_the_separators():
    """E-M2 with ``core_roles="key"``: the key identity includes the separators, absent or not."""
    gold = [{"kind": "c4-extraction-doc", "id": "c4:d", "qset": "q", "split": "test", "doc_id": "d", "text": "t",
             "text_sha256": record.text_sha256("t"), "annotation": {"guideline": "g"},
             "gold": [pop("f:g", "+679941", year(2019))], "entities": entities("ex:Łódź")}]
    pred = [dict(pop("f:p", "+679941"), evidence=[{"id": "e1", "type": "curated", "mode": "manual",
                                                    "source": {"doc_id": "d"}}])]
    cfg = extraction.ExtractionConfig(core_roles="key")
    assert extraction.score(gold, pred, schema=SCHEMA, config=cfg)["aggregate"]["core"]["f1"] == 0.0
    assert extraction.score(gold, pred, schema=SEPARATED, config=cfg)["aggregate"]["core"]["f1"] == 0.0
    loose = schema_with(lambda d: relation(d, "population")["key"].update(roles=["place"]))
    assert extraction.score(gold, pred, schema=loose, config=cfg)["aggregate"]["core"]["f1"] == 1.0


# ------------------------------------------------------------------------------------------------ non-monotone


def with_sourcing(monotone: bool | None) -> dict[str, Any]:
    """The fixture schema with a qualifier ``sourcing`` (a string, any number) on ``population``: P1480-like."""
    def change(d: dict[str, Any]) -> None:
        d["roles"].append({"id": "sourcing", "mappings": {"wikidata": "P1480"}})
        usage = {"role": "sourcing", "slot": "qualifier", "fillers": [{"literal": "string"}], "min": 0, "max": None}
        if monotone is not None:
            usage["monotone"] = monotone
        relation(d, "population")["roles"].append(usage)
    doc = schema_with(change)
    if monotone is None:
        doc["format"] = "khg-relation-schema/1.0.0"
    return doc


EPISTEMIC, PLAIN = with_sourcing(False), with_sourcing(None)
CIRCA = {"literal": {"datatype": "string", "value": "circa"}}


def test_monotone_false_is_for_qualifier_usages():
    assert schema_pkg.check_schema(EPISTEMIC) == [] and schema_pkg.check_schema(PLAIN) == []
    doc = schema_with(lambda d: relation(d, "population")["roles"][0].update(monotone=False))  # the core place
    n = [r["id"] for r in doc["relations"]].index("population")
    assert [(f["code"], f["path"]) for f in schema_pkg.check_schema(doc)] == \
        [("KHG-M015", f"/relations/{n}/roles/0/slot")]
    doc = schema_with(lambda d: relation(d, "population")["roles"][2].update(monotone="no"))
    assert [f["code"] for f in schema_pkg.check_schema(doc)] == ["KHG-M015"]


def test_an_epistemic_qualifier_does_not_refine():
    """"c. 2019" does not refine "2019": with the flag, adding or dropping the qualifier makes another claim."""
    plain, circa = pop("f:a", "+679941", year(2019)), pop("f:b", "+679941", year(2019), sourcing=CIRCA)
    assert keyrules.classify(circa, plain, PLAIN) == "refines"  # 1.0: a qualifier added refines
    assert keyrules.classify(circa, plain, EPISTEMIC) == "distinct"
    assert keyrules.classify(plain, circa, EPISTEMIC) == "distinct"
    assert not record.fact_refines(circa, plain, EPISTEMIC) and not record.fact_refines(plain, circa, EPISTEMIC)
    # the same qualifier on both sides: the rest may refine as before
    finer = pop("f:c", "+679941", {"literal": {"datatype": "time", "time": "+2019-06-30T00:00:00Z", "precision": 11,
                                               "calendar": "gregorian"}}, sourcing=CIRCA)
    assert keyrules.classify(finer, circa, EPISTEMIC) == "refines"
    assert identity.relate(circa, plain, schema=PLAIN) == "refines"
    assert identity.relate(circa, plain, schema=EPISTEMIC) == "key_conflict"  # same key, contents disagree


def test_a_new_version_adds_no_epistemic_filler():
    for doc, ok in ((PLAIN, True), (EPISTEMIC, False)):
        store = MemoryStore(doc)
        store.put(entities("ex:Łódź"), actor="t")
        store.put([pop("f:a", "+679941", year(2019))], actor="t")
        again = pop("f:a", "+679941", year(2019), sourcing=CIRCA)
        if ok:
            assert store.put([again], actor="t")["records"] == [("f:a", 2, "versioned")]
        else:
            with pytest.raises(VersionError) as e:
                store.put([again], actor="t")
            assert e.value.codes == ("KHG-D013",) and "non-monotone" in str(e.value)


# ------------------------------------------------------------------------------------------------ bound_conflict


def test_bound_conflict_is_a_reason_of_disputes():
    s = schema_pkg.load_schema(SCHEMA)
    assert s.reasons("khg:disputes") == ["key_conflict", "negation_conflict", "curator", "other", "bound_conflict"]


def test_a_bound_conflict_dispute_is_written_and_exported_as_1_1():
    """P7's D1: one holder restated with other dates is disputed as a bound conflict."""
    store = MemoryStore(SCHEMA)
    store.put(entities("ex:KingOfFrance", "ex:LouisXIII", "ex:LouisXIV"), actor="t")
    king = copy.deepcopy(BY_ID["f:king-14"])
    store.put([king], actor="t")
    assert store.export("khg-json")["header"]["format"] == "khg-record/1.0.0"
    restated = copy.deepcopy(king)
    restated["id"] = "f:king-14-restated"
    next(b for b in restated["bindings"] if b["role"] == "start_time")["value"] = year(1644)
    store.apply({"op": "transition", "targets": ["f:king-14"], "to": "disputed", "records": [restated],
                 "id": "m:dis-bounds", "reason": "bound_conflict", "evidence": copy.deepcopy(EVIDENCE)}, actor="t")
    assert store.get("m:dis-bounds")["reason"] == "bound_conflict"
    out = store.export("khg-json")
    assert out["header"]["format"] == "khg-record/1.1.0"
    assert validate_container(out, schema=SCHEMA) == {"ok": True, "findings": []}
    assert store.info()["record_format"] == "khg-record/1.1.0"


def test_a_1_0_reason_list_would_refuse_it():
    """What a 1.0 reader reports (S026), shown by a schema-free check of the reason against 1.0's list."""
    disputed = [{"bid": f"b{n}", "role": "khg:disputed", "value": {"fact": f}} for n, f in ((1, "f:x"), (2, "f:y"))]
    dispute = {"kind": "hyperedge", "id": "m:d", "relation": "khg:disputes", "status": "asserted",
               "reason": "bound_conflict", "bindings": disputed, "evidence": copy.deepcopy(EVIDENCE)}
    assert validate_record(dispute, schema=SCHEMA) == {"ok": True, "findings": []}
    assert [f["code"] for f in validate_record(dict(dispute, reason="stale"), schema=SCHEMA)["findings"]] == \
        ["KHG-S026"]


# ------------------------------------------------------------------------------------------------ normalize


def lit(value: dict[str, Any]) -> dict[str, Any]:
    r = {"kind": "hyperedge", "id": "f:n", "relation": "station_profile", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "station", "value": {"entity": "ex:東京駅"}},
                      {"bid": "b2", "role": "elevation", "value": {"literal": value}}]}
    return value_of(record.normalize(r), "elevation")["literal"]


def value_of(r: dict[str, Any], role: str) -> dict[str, Any]:
    """The value of a role's one binding (``normalize`` sorts the bindings)."""
    return next(b["value"] for b in r["bindings"] if b["role"] == role)


@pytest.mark.parametrize(("written", "canonical"), [
    ("+1.50", "+1.5"), ("1.5", "+1.5"), ("-0", "+0"), ("-0.00", "+0"), ("+0", "+0"), ("1.5e3", "+1500"),
    ("1E-7", "+0.0000001"), (".5", "+0.5"), ("-007.250", "-7.25"), ("+10", "+10"), ("100.0", "+100"),
    (3, "+3"), (-2.5, "-2.5"), (35.6812, "+35.6812"), (0.1, "+0.1"), (1e21, "+1000000000000000000000"),
])
def test_normalize_writes_a_decimal_in_its_canonical_form(written, canonical):
    q = lit({"datatype": "quantity", "amount": written, "unit": "wd:Q11573", "lower": written, "upper": written})
    assert (q["amount"], q["lower"], q["upper"]) == (canonical, canonical, canonical)
    record.decimal(canonical)  # C004's form


@pytest.mark.parametrize("written", ["abc", "NaN", "Infinity", "1,5", "+", "", " 1.5", "1.5.2", True, None, [1]])
def test_normalize_leaves_what_is_no_decimal_as_written(written):
    assert lit({"datatype": "quantity", "amount": written, "unit": "1"})["amount"] == written


def test_normalize_writes_coordinates_as_canonical_decimals():
    g = lit({"datatype": "geo", "lat": 35.6812, "lon": "139.76710", "precision": 0.0001, "globe": "wd:Q2"})
    assert (g["lat"], g["lon"], g["precision"]) == ("+35.6812", "+139.7671", "+0.0001")


@pytest.mark.parametrize(("written", "precision", "canonical"), [
    ("+1990-01-01T00:00:00Z", 9, "+1990-00-00T00:00:00Z"),
    ("+1990-06-15T12:30:05Z", 10, "+1990-06-00T00:00:00Z"),
    ("+1990-06-15T12:30:05Z", 11, "+1990-06-15T00:00:00Z"),
    ("+1990-06-15T12:30:05Z", 13, "+1990-06-15T12:30:00Z"),
    ("+1990-06-15T12:30:05Z", 14, "+1990-06-15T12:30:05Z"),
    ("+1995-07-04T00:00:00Z", 8, "+1995-00-00T00:00:00Z"),   # the decade: the year is kept
    ("-0044-03-15T00:00:00Z", 7, "-0044-00-00T00:00:00Z"),
    ("+1990-13-45T00:00:00Z", 9, "+1990-00-00T00:00:00Z"),   # below the precision nothing is read
    ("+1990-13-45T00:00:00Z", 10, "+1990-13-00T00:00:00Z"),  # a month 13 at month precision stays S006
    ("1990-01-01", 9, "1990-01-01"), ("+1990-01-01T00:00:00Z", 15, "+1990-01-01T00:00:00Z"),
])
def test_normalize_zeroes_the_components_below_the_precision(written, precision, canonical):
    r = {"kind": "hyperedge", "id": "f:n", "relation": "station_profile", "status": "asserted",
         "bindings": [{"bid": "b1", "role": "station", "value": {"entity": "ex:東京駅"}},
                      {"bid": "b2", "role": "opened", "value": {"literal": {"datatype": "time", "time": written,
                                                                            "precision": precision,
                                                                            "calendar": "julian"}}}]}
    assert value_of(record.normalize(r), "opened")["literal"]["time"] == canonical


def test_the_fixture_is_already_in_canonical_form():
    """No value of the fixture changes: its decimals and times are canonical already."""
    for r in FIXTURE["records"]:
        n = record.normalize(r)
        assert n == record.normalize(n)
        if r.get("kind") == "hyperedge":
            assert sorted(map(str, (b["value"] for b in n["bindings"]))) == \
                sorted(map(str, (b["value"] for b in r["bindings"])))


def test_validation_still_refuses_the_other_writings_and_the_store_normalises():
    """normalize is the producer's step: the validator reads what was written; put and load normalise first, as they
    already did for NFC, the case of a lang tag and the default calendar."""
    raw = pop("f:raw", "679941.0", {"literal": {"datatype": "time", "time": "+2019-01-01T00:00:00Z", "precision": 9,
                                                "calendar": "gregorian"}})
    codes = sorted({f["code"] for f in validate_record(raw, schema=SCHEMA)["findings"]})
    assert codes == ["KHG-C004", "KHG-S006"]
    store = MemoryStore(SCHEMA)
    store.put(entities("ex:Łódź"), actor="t")
    store.put([raw], actor="t")
    held = store.get("f:raw")
    assert {b["role"]: b["value"] for b in held["bindings"]} == {"place": LODZ, "quantity": qty("+679941"),
                                                                 "point_in_time": year(2019)}
    assert validate_record(held, schema=SCHEMA)["ok"]


def test_the_importer_rules_stay_out_of_normalize():
    """P3a's items 4 and 5: an entity URI is not rewritten to a ``wd:`` id, and a repeated filler is kept (S014)."""
    uri = "http://www.wikidata.org/entity/Q11573"
    assert lit({"datatype": "quantity", "amount": "+3", "unit": uri})["unit"] == uri
    twice = copy.deepcopy(BY_ID["f:coadmin-1"])
    twice["bindings"][1]["value"] = {"entity": "ex:insulin"}
    assert len(record.normalize(twice)["bindings"]) == 3
    assert "KHG-S014" in {f["code"] for f in validate_record(twice, schema=SCHEMA)["findings"]}


def test_the_read_of_a_where_is_unchanged():
    """Nothing here changes a read of the fixture (C2 and its scenarios are unchanged)."""
    store = MemoryStore(SCHEMA)
    store.load(FIXTURE)
    assert [r["id"] for r in store.find_by_key("position_held", [{"role": "position",
                                                                  "value": {"entity": "ex:KingOfFrance"}}],
                                               where=Where())] == ["f:king-13", "f:king-14"]
