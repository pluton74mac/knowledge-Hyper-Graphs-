"""The fidelity measures (DESIGN §5) on every backend this run can reach: no silent loss, answers equal to the
reference, the native layer as each layout promises, and the edge-case container valid and reproducible."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from khg_contracts.record import read_container
from khg_contracts.validate import validate_container

from khg_bakeoff.fidelity import EDGE, HAND, measure

from helpers import FIXTURES, backend_params

#: What each backend skips on each data set (a missing flag or cannot_hold), and whether it loads the history.
SKIPS = {
    "sqlite": {"fixture": [], "edge": ["f:far-future"]},
    "postgres": {"fixture": [], "edge": []},
    "oxigraph": {"fixture": [], "edge": ["f:far-future"]},
    "neo4j": {"fixture": [], "edge": ["f:far-future"]},
    "typedb": {"fixture": ["f:born-scribe", "f:cat-7", "f:route-1", "g:who-1774"],
               "edge": ["ex:Dual", "f:aliases-twice", "f:constant-c", "f:dual-profile", "f:far-future",
                        "g:who-what"]},
    "hif": {"fixture": [], "edge": []},
}
NO_HISTORY = {"typedb", "hif"}
#: The answers of the HIF store that differ: the edge query that reads an entity (no recorded_by in HIF).
HIF_ANSWERS = {"fixture": set(), "edge": {"get ex:Dual (two types)"}}


@pytest.mark.slow
@pytest.mark.parametrize("name", backend_params())
def test_fidelity(name):
    result = measure(name)
    for ds in ("fixture", "edge"):
        e = result[ds]
        rt = e["round_trip"]
        assert sorted(rt["skip_reasons"]) == SKIPS[name][ds]
        assert rt["differing"] == len(SKIPS[name][ds]) and rt["other_differences"] == []
        assert rt["header_differences"] == []
        differ = HIF_ANSWERS[ds] if name == "hif" else set()
        assert set(e["answers"]["differ"]) == differ, e["answers"]["differ"]
        assert e["answers"]["same"] + len(differ) == e["answers"]["compared"] == len(HAND if ds == "fixture" else EDGE)
        for label in differ:  # only recorded_by is missing from the HIF store's entity
            got, want = (json.loads(x[1]) for x in (e["answers"]["differ"][label]["store"],
                                                    e["answers"]["differ"][label]["reference"]))
            assert {k: v for k, v in want.items() if k != "recorded_by"} == got
        n = e["native"]
        if name == "typedb":  # bids, literals as written, positions and extensions have no native home
            assert n["bid_kept"] == n["literal_as_written_kept"] == n["extensions_kept"] == 0
            assert n["multiset_kept"] == n["facts"]
        else:
            assert n["lost"] == {} and n["bid_kept"] == n["bindings"] and n["multiset_kept"] == n["facts"]
        if name == "hif":  # the profile has no khg-recorded-by on entity nodes (P2 DESIGN §4.2)
            assert rt["store_field_differences"] and all(
                f == ["recorded_by"] for f in rt["store_field_differences"].values())
        else:
            assert rt["store_field_differences"] == {}
    h = result["history"]
    if name in NO_HISTORY:
        assert h["loaded"] is False and "history_export" in h["reason"]
    else:
        assert h["round_trip"]["differing"] == 0 and h["round_trip"]["header_differences"] == []
        assert h["answers"]["same"] == h["answers"]["compared"] == 85


def test_the_edge_container_is_valid_and_reproducible(tmp_path):
    from khg_contracts.schema import load_schema

    schema = load_schema(FIXTURES / "edge.relation-schema.json")
    container = read_container(FIXTURES / "edge.c1.json")
    report = validate_container(container, schema=schema)
    assert report["ok"] and report["findings"] == []
    assert container["header"]["schema"] == schema.header and len(container["records"]) == 41
    out = subprocess.run([sys.executable, str(FIXTURES / "make_edge.py"), str(tmp_path)], capture_output=True,
                         text=True, check=True)
    assert "valid: True True" in out.stdout
    for name in ("edge.c1.json", "edge.relation-schema.json"):
        assert (tmp_path / name).read_bytes() == (FIXTURES / name).read_bytes()
