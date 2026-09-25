"""The fidelity measures (DESIGN §5) on every backend this run can reach: every loss counted (a skip with its reason,
or a silent loss), answers equal to the reference on every query that does not touch a skipped record, the native
layer as each layout promises, and the edge-case container valid and reproducible (review 01, R-08 to R-10)."""
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
#: The records a backend loses silently: the HIF format has no recorded_by on an entity node (22 and 20 entities).
SILENT = {"hif": {"fixture": 22, "edge": 20}}
#: The answers of the HIF store that differ: the edge query that reads an entity (no recorded_by in HIF).
HIF_ANSWERS = {"fixture": set(), "edge": {"get ex:Dual (two types)"}}
FAR = {"get f:far-future (16-digit year)", "incident far-future post as_of year 10000000000000001 (definite)",
       "incident far-future post inside its start year (possible)"}
#: The queries that touch what a backend skipped or lacks: not compared (R-10).
NOT_COMPARED = {
    "sqlite": {"fixture": set(), "edge": FAR}, "oxigraph": {"fixture": set(), "edge": FAR},
    "neo4j": {"fixture": set(), "edge": FAR}, "postgres": {"fixture": set(), "edge": set()},
    "hif": {"fixture": set(), "edge": set()},
    "typedb": {"fixture": {"find at_least flight_route stop YYZ at position 3"},
               "edge": FAR | {"find alias_list two equal aliases", "find alias_list alias at position 2",
                              "get ex:Dual (two types)", "incident ex:Dual",
                              "find position_held holder any_unbound (goals)",
                              "find measured_constant, empty pattern (literal-only fact)",
                              "find measured_constant by value"}},
}
#: The fixture's literal bindings whose identity is not the literal as written: its eleven time literals.
TIME_LITERALS = ["f:claim-1 b3", "f:king-13 b3", "f:king-13 b4", "f:king-14 b3", "f:king-14 b4",
                 "f:married-curie b3", "f:married-curie b4", "f:pop-łódź-2019 b3", "f:pop-łódź-2019-dep b3",
                 "f:station-東京 b6", "g:who-1774 b3"]


@pytest.fixture(scope="module", params=backend_params())
def measured(request):
    return request.param, measure(request.param)


@pytest.mark.slow
def test_fidelity(measured):
    name, result = measured
    for ds in ("fixture", "edge"):
        e = result[ds]
        rt = e["round_trip"]
        assert sorted(rt["skip_reasons"]) == SKIPS[name][ds]
        assert rt["other_differences"] == [] and rt["header_differences"] == []
        differ = HIF_ANSWERS[ds] if name == "hif" else set()
        assert set(e["answers"]["differ"]) == differ, e["answers"]["differ"]
        for label in differ:  # only recorded_by is missing from the HIF store's entity
            got, want = (json.loads(x[1]) for x in (e["answers"]["differ"][label]["store"],
                                                    e["answers"]["differ"][label]["reference"]))
            assert {k: v for k, v in want.items() if k != "recorded_by"} == got
        n = e["native"]
        if name == "typedb":  # bids, positions and extensions have no native home
            assert n["bid_kept"] == n["extensions_kept"] == n["positions"] == 0
            assert n["multiset_kept"] == n["facts"]
        else:
            assert n["bid_kept"] == n["bindings"] and n["multiset_kept"] == n["facts"]
            assert set(n["lost"]) <= {"literal as written"}
    h = result["history"]
    if name in NO_HISTORY:
        assert h["loaded"] is False and "history_export" in h["reason"]
    else:
        assert h["round_trip"]["differing"] == 0 and h["round_trip"]["header_differences"] == []
        assert h["answers"]["same"] == h["answers"]["compared"] == 85 and h["answers"]["n/a"] == 0


@pytest.mark.slow
def test_r08_number_1_counts_the_silent_loss_of_hifs_entity_recorded_by(measured):
    """R-08: a record whose store fields differ from the reference, with no refusal, is a silent loss."""
    name, result = measured
    for ds in ("fixture", "edge"):
        rt = result[ds]["round_trip"]
        want = SILENT.get(name, {}).get(ds, 0)
        assert rt["silent"] == len(rt["silent_ids"]) == want
        assert rt["differing"] == len(SKIPS[name][ds]) + want
        if name == "hif":  # the profile has no khg-recorded-by on entity nodes (P2 DESIGN §4.2)
            assert len(rt["store_field_differences"]) == want and all(
                f == ["recorded_by"] for f in rt["store_field_differences"].values())
            assert all(i.startswith("ex:") for i in rt["silent_ids"])
        else:
            assert rt["store_field_differences"] == {}


@pytest.mark.slow
def test_r09_number_2_reads_literals_from_the_native_structure_only(measured):
    """R-09: no JSON copy of a value is read; a literal is rebuilt from the stored identity, which gives back every
    literal as written but a time literal (its identity is its window)."""
    name, result = measured
    n = result["fixture"]["native"]
    if name == "hif":  # HIF's literal nodes carry the literal as written
        assert n["literal_as_written_kept"] == n["literals"] == 20 and n["lost"] == {}
        return
    lost = n["lost"].get("literal as written", [])
    want = [x for x in TIME_LITERALS if x.split()[0] not in SKIPS[name]["fixture"]]  # TypeDB skips g:who-1774
    assert n["literals"] == (19 if name == "typedb" else 20)
    assert lost == want and n["literal_as_written_kept"] == n["literals"] - len(want) == 9


@pytest.mark.slow
def test_r10_number_3_leaves_out_the_queries_that_touch_what_was_skipped(measured):
    """R-10: a query whose reference answer changes with the full container and every flag is n/a."""
    name, result = measured
    for ds, queries in (("fixture", HAND), ("edge", EDGE)):
        a = result[ds]["answers"]
        assert set(a["n/a queries"]) == NOT_COMPARED[name][ds] and a["n/a"] == len(NOT_COMPARED[name][ds])
        assert a["compared"] + a["n/a"] == len(queries)
        assert a["same"] + len(a["differ"]) == a["compared"]


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
