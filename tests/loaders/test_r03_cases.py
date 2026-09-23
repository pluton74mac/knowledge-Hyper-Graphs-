"""W7: R03's library cases through the loaders with ``validate="none"`` (DESIGN §5; ``r03-loader-cases.json``).

The 28 files are c00 (the knowledge base's ``schemas/sample.hif.json``, verbatim) and c01-c26 (with two c21 files),
copied from ``research/probes/lib-cases/`` into ``r03-cases/``. Each runs ``load_xgi`` -> ``export_xgi`` ->
``load_hnx`` -> ``export_hnx``:

- 22 round-trip exactly through both libraries, including absent against empty ``attrs``, isolated nodes, empty
  edges, weights everywhere and mixed id types;
- 6 are refused by design: c04 ``asc`` (P007), c14 a directed file missing a direction (P010), c19 duplicate
  declarations (D001), c22 NaN (J004), and c16 and c23 integers beyond 2^53 (J006).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from khg_contracts import jsonio, loaders
from khg_contracts.errors import LoaderError, ValidationError

xgi = pytest.importorskip("xgi")
hypernetx = pytest.importorskip("hypernetx")

pytestmark = pytest.mark.libs

HERE = Path(__file__).resolve().parent
CASES = HERE / "r03-cases"
TABLE = json.loads((HERE / "r03-loader-cases.json").read_text(encoding="utf-8"))
EXPECTED = {r["case"]: r["outcome"] for r in TABLE["rows"]}
REFUSED = {"c04-asc": "refused KHG-P007", "c14-directed-missing-direction": "refused KHG-P010",
           "c16-attr-value-shapes": "refused KHG-J006 (strict parse)",
           "c19-duplicate-node-edge-records": "refused KHG-D001", "c22-nan-in-attrs": "refused KHG-J004 (strict parse)",
           "c23-big-int-ids": "refused KHG-J006 (strict parse)"}


def _norm(d: dict[str, Any]) -> dict[str, Any]:
    """The structural view of the prototype: node and edge records as multisets, incidences in order."""
    return {"network-type": d.get("network-type"), "metadata": d.get("metadata"),
            "nodes": sorted(jsonio.canonical(x) for x in d.get("nodes", [])),
            "edges": sorted(jsonio.canonical(x) for x in d.get("edges", [])),
            "incidences": [jsonio.canonical(x) for x in d.get("incidences", [])]}


def _outcome(path: Path) -> tuple[str, dict[str, Any] | None]:
    try:
        doc = jsonio.load(path)
    except ValidationError as e:
        return f"refused {e.code} (strict parse)", None
    try:
        hx = loaders.export_xgi(loaders.load_xgi(doc, validate="none"))
        hh = loaders.export_hnx(loaders.load_hnx(hx, validate="none"))
    except LoaderError as e:
        return f"refused {e.code}", None
    exact = _norm(hx) == _norm(doc) and _norm(hh) == _norm(doc)
    return ("exact" if exact else "differs"), {"doc": doc, "xgi": hx, "hnx": hh}


def test_the_case_files_are_those_of_the_table():
    assert TABLE["format"] == "khg-r03-cases/1.0.0"
    names = sorted(p.name[:-len(".hif.json")] for p in CASES.glob("*.hif.json"))
    assert names == sorted(EXPECTED) and len(names) == 28
    assert sum(v == "exact" for v in EXPECTED.values()) == 22
    assert {k: v for k, v in EXPECTED.items() if v != "exact"} == REFUSED


@pytest.mark.parametrize("case", sorted(EXPECTED))
def test_r03_case(case):
    result, docs = _outcome(CASES / f"{case}.hif.json")
    assert result == EXPECTED[case]
    if docs is not None:  # exact: and the canonical serialisation too, key presence included
        assert jsonio.canonical(docs["xgi"]) == jsonio.canonical(docs["doc"])
        assert jsonio.canonical(docs["hnx"]) == jsonio.canonical(docs["doc"])


@pytest.mark.parametrize("case", sorted(k for k, v in REFUSED.items() if "strict parse" in v))
def test_the_loaders_refuse_a_path_under_the_layer_j_rules(case):
    code = REFUSED[case].split()[1]
    for load in (loaders.load_xgi, loaders.load_hnx):
        with pytest.raises(LoaderError) as err:
            load(CASES / f"{case}.hif.json", validate="none")
        assert err.value.code == code and isinstance(err.value, ValidationError)


@pytest.mark.parametrize("case, code", [("c04-asc", "KHG-P007"), ("c14-directed-missing-direction", "KHG-P010"),
                                        ("c19-duplicate-node-edge-records", "KHG-D001")])
def test_the_loader_refusals_hold_through_both_libraries(case, code):
    doc = jsonio.load(CASES / f"{case}.hif.json")
    declared = {**doc, "metadata": {**doc.get("metadata", {}), "role-convention": "1.0.0"}}
    for load in (loaders.load_xgi, loaders.load_hnx):
        for source, mode in ((CASES / f"{case}.hif.json", "none"), (doc, "none"), (declared, "convention")):
            with pytest.raises(LoaderError) as err:
                load(source, validate=mode)
            assert err.value.codes == (code,)
        with pytest.raises(LoaderError) as err:
            load(doc, validate="convention")  # R03's files do not declare the convention
        assert err.value.codes == ("KHG-R003",)


def test_repeated_pairs_keep_every_record():
    for case, n in (("c05-two-roles-same-direction", 4), ("c06-two-roles-different-direction", 3),
                    ("c07-two-roles-undirected", 4)):
        _, docs = _outcome(CASES / f"{case}.hif.json")
        roles = [i["attrs"]["role"] for i in docs["doc"]["incidences"]]
        assert len(roles) == n
        assert [i["attrs"]["role"] for i in docs["xgi"]["incidences"]] == roles
        assert [i["attrs"]["role"] for i in docs["hnx"]["incidences"]] == roles


def test_mixed_integer_and_string_ids_keep_their_types_and_source_order():
    _, docs = _outcome(CASES / "c12-mixed-int-str-ids.hif.json")
    for key in ("xgi", "hnx"):
        assert [(i["edge"], i["node"]) for i in docs[key]["incidences"]] == [(1, 1), (1, "1"), ("1", 1), ("1", "x")]
        assert [n["node"] for n in docs[key]["nodes"]] == [1, "1"]
