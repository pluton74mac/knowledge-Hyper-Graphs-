"""Write the edge-case container of P1 (research 01 D5; DESIGN §5.2) and its schema, and validate both.

    python make_edge.py [DIR]      # writes edge.relation-schema.json and edge.c1.json (default: next to this file)

The schema is P2's gate-fixture schema (``fixture.relation-schema.json``) under the id ``p1-edge`` with two relations
added: ``measured_constant``, whose roles take literals only (no relation of the fixture schema admits a fact without
an entity), and ``alias_list``, whose ``alias`` role is ordered. Each group of records is aimed at one hazard research
01 found:

| Item | Records | Hazard |
|---|---|---|
| astral and full-width ids | ``ex:𠮷`` bound by eight facts whose ids sort differently by code point, UTF-16 unit and collation (``f:a``, ``f:Z``, ``f:é``, ``f:ł``, ``f:東京``, ``f:ｚ``, ``f:\\ufffd``, ``f:𠮷``); ``ex:ｚ`` | id order and keyset pagination (research 01 §7) |
| a 16-digit-year literal | ``f:far-future``: a ``position_held`` from ``+9999999999999999`` | instants beyond int64 (§7, ruling 4) |
| two equal literals in one role | ``f:aliases-twice``: ``alias`` "Tokyo Station"@en at positions 1 and 2 | owned attributes are sets in TypeDB |
| a multi-typed entity | ``ex:Dual`` (Place and Station), bound by ``f:dual-profile`` | one type per TypeDB instance |
| an all-unbound goal | ``g:who-what``: ``position_held`` with holder and position unbound | a relation without players (TypeDB) |
| a literal-only fact | ``f:constant-c``: ``measured_constant`` | a relation without players (TypeDB) |
| a diamond of supersessions | ``f:dia-a`` → ``f:dia-b``, ``f:dia-c`` (``m:dia-1``, conflation) → ``f:dia-d`` (``m:dia-2``, ``m:dia-3``) | a recursive walk that reaches one fact twice (§2.3) |

Research 01 D5 also listed "one filler repeated in one unordered role" and "two equal literals in one role". Both are
refused by C1 in an unordered role (KHG-S014, "duplicate filler in an unordered role"), so the first is left out (its
ordered form is P2's ``f:route-1``, ``stop`` YYZ at positions 1 and 3) and the second is written in an ordered role.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

from khg_contracts import data, jsonio
from khg_contracts.record import read_container, write_container
from khg_contracts.schema import load_schema
from khg_contracts.validate import validate_container

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "edge.relation-schema.json"
CONTAINER_PATH = HERE / "edge.c1.json"


def schema_doc() -> dict[str, Any]:
    doc = copy.deepcopy(data.load_json("fixture/fixture.relation-schema.json"))
    doc["id"] = "p1-edge"
    doc["version"] = "1.0.0"
    doc["label"] = "P1 edge cases: the P2 gate-fixture schema plus a literal-only relation"
    doc["relations"].append({
        "id": "measured_constant", "label": "measured constant", "time": {"model": "invariant"},
        "roles": [
            {"role": "constant_name", "slot": "core", "fillers": [{"literal": "string"}], "min": 1, "max": 1},
            {"role": "constant_value", "slot": "core", "fillers": [{"literal": "quantity", "units": ["1"]}],
             "min": 1, "max": 1},
        ]})
    doc["relations"].append({
        "id": "alias_list", "label": "ordered aliases",
        "roles": [
            {"role": "aliased", "slot": "core", "fillers": [{"entity": ["Station"]}], "min": 1, "max": 1},
            {"role": "alias", "slot": "qualifier", "fillers": [{"literal": "lang_string"}], "min": 1, "max": None,
             "ordered": True},
        ]})
    for role in ("constant_name", "constant_value", "aliased", "alias"):
        known = [r["id"] if isinstance(r, dict) else r for r in doc.get("roles") or []]
        if isinstance(doc.get("roles"), list) and role not in known:
            example = doc["roles"][0]
            doc["roles"].append({"id": role} if isinstance(example, dict) else role)
    return doc


def ev(n: int = 1, doc: str = "doc:p1-edge") -> list[dict[str, Any]]:
    return [{"id": f"e{n}", "type": "curated", "mode": "manual", "source": {"doc_id": doc}}]


def entity(eid: str, *types: str, label: str | None = None) -> dict[str, Any]:
    r: dict[str, Any] = {"kind": "entity", "id": eid, "types": list(types)}
    if label:
        r["label"] = label
    return r


def fact(fid: str, relation: str, bindings: list[tuple[str, dict[str, Any]]], status: str = "asserted",
         **extra: Any) -> dict[str, Any]:
    r: dict[str, Any] = {"kind": "hyperedge", "id": fid, "relation": relation, "status": status,
                         "bindings": [{"bid": f"b{i}", "role": role, "value": value}
                                      for i, (role, value) in enumerate(bindings, 1)]}
    if status in ("asserted",) and "evidence" not in extra:
        r["evidence"] = ev()
    r.update(extra)
    return r


def E(eid: str) -> dict[str, Any]:
    return {"entity": eid}


def F(fid: str) -> dict[str, Any]:
    return {"fact": fid}


def container(schema: Any) -> dict[str, Any]:
    order_ids = ["f:a", "f:Z", "f:é", "f:ł", "f:東京", "f:ｚ", "f:\ufffd", "f:\U00020BB7"]
    records = [
        entity("ex:\U00020BB7", "Chemical", label="an astral-plane catalyst"),
        entity("ex:ｚ", "Chemical", label="a full-width catalyst"),
        entity("ex:Dual", "Place", "Station", label="a place that is also a station"),
        entity("ex:FarFuturePost", "Position", label="a post held in the far future"),
        entity("ex:Futurist", "Person", label="a far-future office holder"),
        entity("ex:Diamond", "Person", label="a person with a diamond of corrections"),
        entity("ex:KingOfFrance", "Position", label="King of France"),
        entity("ex:Kraków", "Place", label="Kraków"),
        entity("ex:Warszawa", "Place", label="Warszawa"),
        entity("ex:Łódź", "Place", label="Łódź"),
        entity("ex:Paris", "Place", label="Paris"),
        entity("ex:東京駅", "Station", label="Tokyo Station"),
    ]
    records += [entity(f"ex:R-{n}", "Reaction", label=f"reaction {n}") for n in range(1, 9)]
    # 1. astral and full-width ids: eight facts on one astral node, ids in no single simple order
    for n, fid in enumerate(order_ids, 1):
        records.append(fact(fid, "catalysed_by", [("reaction", E(f"ex:R-{n}")), ("catalyst", E("ex:\U00020BB7"))]))
    records.append(fact("f:ｚ-full", "catalysed_by", [("reaction", E("ex:R-1")), ("catalyst", E("ex:ｚ"))]))
    # 2. a 16-digit year in a valid-time bound
    records.append(fact("f:far-future", "position_held", [
        ("holder", E("ex:Futurist")), ("position", E("ex:FarFuturePost")),
        ("start_time", {"literal": {"datatype": "time", "time": "+9999999999999999-00-00T00:00:00Z",
                                    "precision": 9, "calendar": "gregorian"}})]))
    # 3. two equal literals in one (ordered) role
    tokyo = {"literal": {"datatype": "lang_string", "value": "Tokyo Station", "lang": "en"}}
    twice = fact("f:aliases-twice", "alias_list", [
        ("aliased", E("ex:東京駅")), ("alias", tokyo), ("alias", copy.deepcopy(tokyo))])
    twice["bindings"][1]["position"] = 1
    twice["bindings"][2]["position"] = 2
    records.append(twice)
    # 4. a multi-typed entity, bound as a station
    records.append(fact("f:dual-profile", "station_profile", [
        ("station", E("ex:Dual")), ("code", {"literal": {"datatype": "string", "value": "DUA"}})]))
    # 5. an all-unbound goal
    records.append(fact("g:who-what", "position_held", [
        ("holder", {"unbound": {"var": "who", "expect": {"entity_types": ["Person"]}}}),
        ("position", {"unbound": {"var": "what", "expect": {"entity_types": ["Position"]}}})],
        status="goal", goal={"brief": "Who held which post?", "owner": "agent:p1"}))
    # 6. a literal-only fact
    records.append(fact("f:constant-c", "measured_constant", [
        ("constant_name", {"literal": {"datatype": "string", "value": "speed of light in vacuum"}}),
        ("constant_value", {"literal": {"datatype": "quantity", "amount": "+299792458", "unit": "1"}})]))
    # 7. a diamond of supersessions: a -> b, c (conflation); b -> d; c -> d
    for fid, place, status, ref in (("f:dia-a", "ex:Kraków", "superseded", "m:dia-1"),
                                    ("f:dia-b", "ex:Warszawa", "superseded", "m:dia-2"),
                                    ("f:dia-c", "ex:Łódź", "superseded", "m:dia-3"),
                                    ("f:dia-d", "ex:Paris", "asserted", None)):
        extra: dict[str, Any] = {"evidence": ev()}
        if ref:
            extra["status_ref"] = ref
        records.append(fact(fid, "born_in", [("person", E("ex:Diamond")), ("birthplace", E(place))], status=status,
                            **extra))
    records.append(fact("m:dia-1", "khg:supersedes", [("khg:superseding", F("f:dia-b")),
                                                      ("khg:superseding", F("f:dia-c")),
                                                      ("khg:superseded", F("f:dia-a"))],
                        reason="conflation", note="two birth records conflated into one"))
    records.append(fact("m:dia-2", "khg:supersedes", [("khg:superseding", F("f:dia-d")),
                                                      ("khg:superseded", F("f:dia-b"))], reason="correction"))
    records.append(fact("m:dia-3", "khg:supersedes", [("khg:superseding", F("f:dia-d")),
                                                      ("khg:superseded", F("f:dia-c"))], reason="correction"))
    header = {"kind": "header", "format": "khg-record/1.0.0", "document_id": "p1-edge-cases",
              "schema": schema.header, "content": "snapshot", "complete": True}
    return {"header": header, "records": records}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]) if argv else HERE
    schema_path, container_path = out / SCHEMA_PATH.name, out / CONTAINER_PATH.name
    doc = schema_doc()
    schema_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    schema = load_schema(schema_path)
    c = container(schema)
    report = validate_container(c, schema=schema)
    errors = [f for f in report["findings"] if f["severity"] == "error"]
    for f in report["findings"]:
        print(f["severity"], f["code"], f["path"], f["message"][:160])
    if errors:
        return 1
    write_container(c, container_path, format="json")
    again = read_container(container_path)
    print("written:", container_path.name, len(again["records"]), "records;", schema_path.name, schema.sha256)
    print("valid:", validate_container(again, schema=schema)["ok"], jsonio.digest("khg-schema/1", doc) == schema.sha256)
    return 0


if __name__ == "__main__":
    sys.exit(main())
