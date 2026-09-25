"""The full 114-scenario suite on every backend this run can reach (DESIGN §4; PLAN §7): no applicable scenario
fails, and a scenario is inapplicable only through a flag the backend declares absent."""
from __future__ import annotations

import pytest

from khg_contracts.store import ALL_FLAGS, conformance

from khg_bakeoff.backends import factory
from khg_bakeoff.conformance import losses

from helpers import backend_params

#: The flags each backend declares absent (ruling 3; research 01 §8), and the scenarios that then apply.
ABSENT = {"sqlite": set(), "postgres": set(), "oxigraph": set(), "neo4j": set(),
          "typedb": {"ordered_roles", "special_values", "goals", "transaction_time", "history_export"},
          "hif": {"transaction_time", "history_export"}}
APPLICABLE = {"sqlite": 114, "postgres": 114, "oxigraph": 114, "neo4j": 114, "typedb": 70, "hif": 107}


@pytest.mark.slow
@pytest.mark.parametrize("name", backend_params())
def test_the_suite_passes(name):
    report = conformance.run(factory(name))
    s = report["summary"]
    bad = {a["test"]["identifier"]: a["result"].get("info") for a in report["@graph"]
           if a["result"]["outcome"] in ("failed", "cantTell")}
    assert s["failed"] == 0 and s["cantTell"] == 0, bad
    assert set(report["subject"]["capabilities"]) == ALL_FLAGS - ABSENT[name]
    assert s["total"] - s["inapplicable"] == s["passed"] == APPLICABLE[name]
    suite = conformance.suite().scenarios
    for a in report["@graph"]:
        if a["result"]["outcome"] == "inapplicable":
            missing = set(a["result"]["missing"])
            assert missing and missing <= ABSENT[name]
            assert missing <= set(suite[a["test"]["identifier"]]["requires"])
    by_flag = losses(report)
    assert set(by_flag) == ABSENT[name]
    assert sum(1 for a in report["@graph"] if a["result"]["outcome"] == "inapplicable") == 114 - APPLICABLE[name]
