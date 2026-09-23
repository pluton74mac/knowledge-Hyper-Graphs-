"""P3a's call sequence (DESIGN §1.3): statements to C1, question sets as C4.

``p3a_statement_to_c1`` is a tiny stand-in for P3a's Wikidata reader: it maps one statement in Wikibase JSON form
(the fixture's ids stand in for Q-ids) with the §2.6 mapping table: the main snak's property names the relation, the
statement's subject and value fill the relation's ``primary`` roles, P580 and P582 are the interval's time roles,
P1365 (replaces) is a qualifier, and the reference becomes ``imported`` evidence whose ``doc_id`` is the P248 item
and whose ``reference`` holds every snak. The statement below is Louis XIV's reign, so the mapped record must have
the identity of the fixture's ``f:king-14``.

The other free variables: ``records`` holds four facts P3a mapped before (fixture records), ``entities`` the fixture's
entities, ``header`` a snapshot header of the p2-gate schema, and ``train`` and ``test`` the fixture's facts under
the C4 split manifest. ``qset.c4.jsonl`` is the packaged C4 file.
"""
from __future__ import annotations

import copy
from typing import Any

from khg_contracts import jsonio, record, validate

#: P3a's mapping tables for this statement (§2.6): property -> (relation, subject role, value role); qualifiers.
RELATIONS = {"P39": ("position_held", "holder", "position")}
QUALIFIERS = {"P580": "start_time", "P582": "end_time", "P1365": "replaces"}
CALENDARS = {"http://www.wikidata.org/entity/Q1985727": "gregorian",
             "http://www.wikidata.org/entity/Q1985786": "julian"}
EARLIER = ("f:king-13", "f:pop-łódź-2019", "f:pop-łódź-2019-dep", "f:born-skłodowska-warszawa")


def item_snak(prop: str, item: str) -> dict[str, Any]:
    return {"snaktype": "value", "property": prop, "datatype": "wikibase-item",
            "datavalue": {"type": "wikibase-entityid", "value": {"entity-type": "item", "id": item}}}


def time_snak(prop: str, time: str, precision: int = 11) -> dict[str, Any]:
    return {"snaktype": "value", "property": prop, "datatype": "time",
            "datavalue": {"type": "time", "value": {"time": time, "timezone": 0, "before": 0, "after": 0,
                                                    "precision": precision,
                                                    "calendarmodel": "http://www.wikidata.org/entity/Q1985727"}}}


#: Louis XIV held the position King of France from 1643-05-14 to 1715-09-01, replacing Louis XIII.
STATEMENT = {
    "id": "ex:LouisXIV$5b0e7c1a-2f7d-4c55-9d0e-1f3a6b8c9d01", "type": "statement", "rank": "normal",
    "mainsnak": item_snak("P39", "ex:KingOfFrance"),
    "qualifiers": {"P580": [time_snak("P580", "+1643-05-14T00:00:00Z")],
                   "P582": [time_snak("P582", "+1715-09-01T00:00:00Z")],
                   "P1365": [item_snak("P1365", "ex:LouisXIII")]},
    "qualifiers-order": ["P580", "P582", "P1365"],
    "references": [{"hash": "d0c5e1f2", "snaks-order": ["P248", "P813"],
                    "snaks": {"P248": [item_snak("P248", "doc:regnal-list")],
                              "P813": [time_snak("P813", "+2026-09-15T00:00:00Z")]}}],
}


def snak_value(snak: dict[str, Any]) -> dict[str, Any]:
    """A value snak as a C1 value: an item as an entity, a time as a time literal."""
    datavalue = snak["datavalue"]
    if datavalue["type"] == "wikibase-entityid":
        return {"entity": datavalue["value"]["id"]}
    v = datavalue["value"]
    return {"literal": {"datatype": "time", "time": v["time"], "precision": v["precision"],
                        "calendar": CALENDARS[v["calendarmodel"]]}}


def p3a_statement_to_c1(stmt: dict[str, Any]) -> dict[str, Any]:
    """One Wikibase statement as a C1 hyperedge; the statement id ``<subject>$<uuid>`` names the subject."""
    subject = stmt["id"].split("$", 1)[0]
    relation, subject_role, value_role = RELATIONS[stmt["mainsnak"]["property"]]
    bindings = [{"role": subject_role, "value": {"entity": subject}},
                {"role": value_role, "value": snak_value(stmt["mainsnak"])}]
    for prop in stmt["qualifiers-order"]:
        bindings += [{"role": QUALIFIERS[prop], "value": snak_value(s)} for s in stmt["qualifiers"][prop]]
    for n, b in enumerate(bindings, 1):
        b["bid"] = f"b{n}"
    ref = stmt["references"][0]
    snaks = [s for prop in ref["snaks-order"] for s in ref["snaks"][prop]]
    stated_in = next(s["datavalue"]["value"]["id"] for s in snaks if s["property"] == "P248")
    evidence = {"id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": stated_in},
                "reference": [{"role": "wd:" + s["property"], "value": snak_value(s)} for s in snaks]}
    return {"kind": "hyperedge", "id": "wds:" + stmt["id"], "relation": relation, "status": "asserted",
            "bindings": bindings, "evidence": [evidence], "rank": stmt["rank"]}


def test_p3a_sequence(S, by_id, fixture_entities, splits, derived, workdir):
    stmt = copy.deepcopy(STATEMENT)
    records = [by_id[i] for i in EARLIER]
    entities = fixture_entities
    header = {"kind": "header", "format": "khg-record/1.0.0", "document_id": "p3a-slice",
              "schema": {"id": S.id, "version": S.version, "sha256": S.sha256}, "content": "snapshot",
              "complete": True}
    test, train = splits["test"], splits["train"]

    # >>> DESIGN §1.3
    # P3a: statements to C1, question sets as C4
    r = record.normalize(p3a_statement_to_c1(stmt), S)         # canonical form and literal normalisation, no checks
    if validate.validate_record(r, schema=S)["ok"]:
        records.append(r)
    record.write_container({"header": header, "records": entities + records}, "slice.khg.jsonl", format="jsonl")
    assert validate.validate_container("slice.khg.jsonl", schema=S)["ok"]
    dedup = {record.content_key(r, S) for r in records}
    leaks = {record.core_key(r, S) for r in test} & {record.core_key(r, S) for r in train}
    bins = [record.arity(r, S)["arity"] for r in records]      # {arity, core_arity, statement_arity, distinct_fillers}
    assert validate.validate_item("qset.c4.jsonl", schema=S)["ok"]   # I layer; I005 replays memory traces
    # <<< DESIGN §1.3

    # the list comprehensions rebind nothing: r is still the mapped statement, now the last record
    mapped = records[-1]
    assert len(records) == 5 and [x["id"] for x in records[:4]] == list(EARLIER)
    assert mapped["id"] == "wds:ex:LouisXIV$5b0e7c1a-2f7d-4c55-9d0e-1f3a6b8c9d01"
    assert validate.validate_record(mapped, schema=S) == {"ok": True, "findings": []}
    # the mapped statement is the fixture's f:king-14 but for its id and evidence (bids included) ...
    king14 = by_id["f:king-14"]
    assert {k: v for k, v in mapped.items() if k not in ("id", "evidence")} == \
        {k: v for k, v in king14.items() if k not in ("id", "evidence")}
    # ... so it has f:king-14's identity: its three keys and its arity (DESIGN §2.9, §2.4)
    for name, fn in (("content_key", record.content_key), ("core_key", record.core_key),
                     ("key_digest", record.key_digest)):
        assert fn(mapped, S) == derived["f:king-14"][name]
    assert record.arity(mapped, S) == {k: derived["f:king-14"][k]
                                       for k in ("arity", "core_arity", "statement_arity", "distinct_fillers")}
    # normalize filled the evidence's supports and kept every reference snak (§2.8.1, §2.6)
    assert mapped["evidence"] == [{
        "id": "e1", "type": "imported", "mode": "automatic", "source": {"doc_id": "doc:regnal-list"},
        "reference": [{"role": "wd:P248", "value": {"entity": "doc:regnal-list"}},
                      {"role": "wd:P813", "value": {"literal": {"datatype": "time", "time": "+2026-09-15T00:00:00Z",
                                                                "precision": 11, "calendar": "gregorian"}}}],
        "supports": ["b1", "b2", "b3", "b4", "b5"]}]
    # the JSONL container: the header line, then the records in canonical order (entities, then hyperedges by id)
    lines = (workdir / "slice.khg.jsonl").read_text(encoding="utf-8").splitlines()
    assert jsonio.loads(lines[0]) == header and len(lines) == 1 + 22 + 5
    written = record.read_container("slice.khg.jsonl")
    assert [x["id"] for x in written["records"]] == \
        [e["id"] for e in entities] + sorted(x["id"] for x in records)
    # the only finding is the designed warning: f:king-13 and the new reign meet on one day (L008)
    findings = validate.validate_container("slice.khg.jsonl", schema=S)["findings"]
    assert [(f["code"], f["severity"]) for f in findings] == [("KHG-L008", "warning")]
    assert "f:king-13" in findings[0]["message"] and mapped["id"] in findings[0]["message"]
    # dedup, the leak check and the arity bins
    assert dedup == {derived[i]["content_key"] for i in EARLIER + ("f:king-14",)} and len(dedup) == 5
    assert leaks == set()  # the manifest's test and train splits share no core key
    assert bins == [derived[i]["arity"] for i in EARLIER] + [3] == [2, 3, 3, 2, 3]
    assert validate.validate_item("qset.c4.jsonl", schema=S) == {"ok": True, "findings": []}


def test_p3a_leak_check_finds_a_shared_core(S, by_id):
    """The sequence's leak expression finds a fact whose core recurs across splits (§2.9: ``core_key``)."""
    r = record.normalize(p3a_statement_to_c1(copy.deepcopy(STATEMENT)), S)
    later = copy.deepcopy(r)
    later["bindings"] = [b for b in later["bindings"] if b["role"] != "end_time"]  # another reading of the reign
    later["evidence"][0]["supports"] = [b["bid"] for b in later["bindings"]]
    test, train = [later], [by_id["f:king-14"], by_id["f:king-13"]]
    leaks = {record.core_key(r, S) for r in test} & {record.core_key(r, S) for r in train}
    assert leaks == {record.core_key(by_id["f:king-14"], S)}
    assert record.content_key(later, S) != record.content_key(by_id["f:king-14"], S)
