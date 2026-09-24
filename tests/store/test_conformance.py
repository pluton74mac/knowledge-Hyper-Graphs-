"""W8: the 114 conformance scenarios on ``MemoryStore``, the capability-limited runs, the runner's outcomes and the
EARL-shaped report (DESIGN §6.3-§6.5, §14 ruling 1)."""
from __future__ import annotations

import copy
import json
import os
import stat

import pytest

from khg_contracts import validate
from khg_contracts.errors import CapabilityMissing
from khg_contracts.store import ALL_FLAGS, FLAGS, MemoryStore, ScenarioClock, conformance, memory_factory

SUITE = conformance.suite()
IDS = sorted(SUITE.scenarios)
#: TypeDB 3.x lacks ordered roles, special values, goals, transaction time and history export (§6.5).
TYPEDB = ALL_FLAGS - {"ordered_roles", "special_values", "goals", "transaction_time", "history_export"}
RUNS = [(f"without-{f}", ALL_FLAGS - {f}) for f in FLAGS] + [("typedb-like", TYPEDB), ("no-flags", frozenset())]


def limited(flags):
    return lambda schema, clock: MemoryStore(schema, clock=clock, capabilities=flags)


def applicable(flags, ids=IDS):
    return [i for i in ids if set(SUITE.scenarios[i]["requires"]) <= set(flags)]


def outcomes(report):
    return {a["test"]["identifier"]: a["result"] for a in report["@graph"]}


# ------------------------------------------------------------------------------------------------ the suite


def test_the_packaged_suite_matches_its_index():
    index = SUITE.index
    assert index["format"] == "khg-scenario-index/1.0.0" and index["count"] == 114 == len(IDS)
    assert sorted(s["id"] for s in index["scenarios"]) == IDS
    for entry in index["scenarios"]:
        sc = SUITE.scenarios[entry["id"]]
        assert sc["format"] == conformance.SCENARIO_FORMAT == "khg-scenario/1.0.0"
        assert (sc["title"], sc["requires"], sc["precedent"]) == (entry["title"], entry["requires"],
                                                                   entry["precedent"])
        assert sc["requires"] == sorted(set(sc["requires"])) and set(sc["requires"]) <= ALL_FLAGS
        assert sc["schema"] == "fixture.relation-schema.json" and sc["fixture"] == "fixture.c1.json"
    assert index["clock"]["start"] == "2026-10-01T00:00:00Z" and index["clock"]["step_seconds"] == 1


def test_the_groups_of_section_6_4():
    groups: dict[str, list[int]] = {}
    for i in IDS:
        groups.setdefault(i.split("-")[1], [0, 0])[i.endswith("c")] += 1
    assert groups == {"PUT": [10, 0], "VER": [9, 1], "READ": [19, 14], "TIME": [12, 1], "KEY": [19, 2],
                      "LIFE": [14, 0], "EXP": [11, 2]}
    assert sum(core for _, core in groups.values()) == 20


def test_the_core_fixture_leaves_out_the_four_records_that_need_the_core_flags():
    dropped = ["f:born-scribe", "f:cat-7", "f:route-1", "g:who-1774"]
    assert SUITE.core_dropped == dropped
    assert all(i in SUITE.index["references"]["@fixture[core]"] for i in dropped)
    kept = [r["id"] for r in SUITE.core["records"]]
    assert kept == [r["id"] for r in SUITE.fixture["records"] if r["id"] not in dropped]
    assert SUITE.core["header"] == SUITE.fixture["header"]
    core = SUITE.resolve("@fixture[core]")
    core["records"].clear()
    assert len(SUITE.core["records"]) == 36  # resolve hands out copies


def test_references_and_patches_resolve_as_the_index_describes():
    r = SUITE.resolve({"@": "f:king-13", "drop_bindings": ["b4"], "set": {"rank": "preferred"},
                       "set_binding": {"b1": {"entity": "ex:LouisXIV"}}, "add_evidence": [{"id": "e2"}]})
    assert [b["bid"] for b in r["bindings"]] == ["b1", "b2", "b3"] and r["rank"] == "preferred"
    assert r["bindings"][0]["value"] == {"entity": "ex:LouisXIV"}
    assert r["evidence"][0]["supports"] == ["b1", "b2", "b3"] and r["evidence"][1] == {"id": "e2"}
    assert SUITE.resolve("@m:sup-1.evidence") == SUITE.records["m:sup-1"]["evidence"]
    assert len(SUITE.flat(["@entities", "@f:reg-1"])) == 23
    assert SUITE.resolve("@fixture.header")["document_id"] == "p2-gate-fixture"
    with pytest.raises(KeyError):
        SUITE.resolve("@f:nope")


# ------------------------------------------------------------------------------------------------ the full store


@pytest.mark.parametrize("sid", IDS)
def test_every_scenario_passes_on_the_memory_store(sid):
    out = conformance.run_scenario(memory_factory, sid)
    assert (out.outcome, out.info) == ("passed", "")


def test_run_reports_114_passed():
    report = conformance.run(memory_factory)
    assert report["summary"] == {"passed": 114, "failed": 0, "inapplicable": 0, "cantTell": 0, "total": 114}
    assert [a["test"]["identifier"] for a in report["@graph"]] == IDS
    assert report["subject"]["capabilities"] == sorted(ALL_FLAGS) == report["subject"]["tested_capabilities"]
    assert report["subject"]["title"] == "memory" and report["subject"]["@id"] == "store:memory"


# ------------------------------------------------------------------------------------------------ limited stores


@pytest.mark.parametrize("name,flags", RUNS, ids=[n for n, _ in RUNS])
def test_capability_limited_runs_are_only_passed_or_inapplicable(name, flags):
    report = conformance.run(limited(flags))
    results = outcomes(report)
    assert {r["outcome"] for r in results.values()} <= {"passed", "inapplicable"}
    passed = sorted(i for i, r in results.items() if r["outcome"] == "passed")
    assert passed == applicable(flags)
    for i, r in results.items():
        if r["outcome"] == "inapplicable":
            missing = sorted(set(SUITE.scenarios[i]["requires"]) - flags)
            assert r["missing"] == missing and missing and r["info"] == f"needs {', '.join(missing)}"
    assert report["summary"]["passed"] + report["summary"]["inapplicable"] == 114


def test_the_applicable_counts_of_sections_6_3_and_6_5():
    assert len(applicable(TYPEDB)) == 70 and len(applicable(())) == 12 and len(applicable(ALL_FLAGS)) == 114
    by_op = {op: [i for i in IDS if any(st["op"] == op for st in SUITE.scenarios[i]["when"])]
             for op in ("find", "incident", "export")}
    assert {op: (len(applicable(TYPEDB, ids)), len(ids)) for op, ids in by_op.items()} == \
        {"find": (5, 13), "incident": (13, 24), "export": (3, 11)}
    rdf_hif = ALL_FLAGS - {"transaction_time", "history_export"}
    graph = ALL_FLAGS - {"transaction_time"}
    assert len(applicable(rdf_hif)) == len(applicable(graph)) == 107


def test_the_capabilities_argument_tests_a_full_store_as_a_limited_one():
    report = conformance.run(memory_factory, capabilities=TYPEDB)
    assert report["summary"] == {"passed": 70, "failed": 0, "inapplicable": 44, "cantTell": 0, "total": 114}
    assert report["subject"]["capabilities"] == sorted(ALL_FLAGS)
    assert report["subject"]["tested_capabilities"] == sorted(TYPEDB)
    with pytest.raises(ValueError):
        conformance.run(memory_factory, capabilities=["time_travel"])


def test_only_selects_scenarios_by_glob():
    report = conformance.run(memory_factory, only="S-KEY-*")
    assert [a["test"]["identifier"] for a in report["@graph"]] == [i for i in IDS if i.startswith("S-KEY-")]
    assert report["summary"]["passed"] == 21 and report["suite"]["selected"] == 21
    report = conformance.run(memory_factory, only=["S-PUT-00?", "S-EXP-001"])
    assert [a["test"]["identifier"] for a in report["@graph"]] == ["S-EXP-001"] + \
        [f"S-PUT-00{n}" for n in range(1, 10)]
    assert report["suite"] == {"format": "khg-scenario/1.0.0", "scenarios": 114, "selected": 10,
                               "only": ["S-EXP-001", "S-PUT-00?"]}


# ------------------------------------------------------------------------------------------------ the report


def test_the_report_is_earl_shaped():
    report = conformance.run(memory_factory, only="S-READ-00*")
    assert report["@context"]["@vocab"] == "http://www.w3.org/ns/earl#"
    assert report["@context"]["outcome"] == {"@type": "@vocab"}
    assert report["assertor"]["@type"] == ["Assertor", "Software"]
    assert report["subject"] == {
        "@id": "store:memory", "@type": "TestSubject", "title": "memory", "interface_version": "khg-store/1.0.0",
        "record_format": "khg-record/1.0.0", "capabilities": sorted(ALL_FLAGS),
        "tested_capabilities": sorted(ALL_FLAGS), "contracts": report["subject"]["contracts"]}
    assert report["subject"]["contracts"]["khg-store"] == "1.0.0"
    first = report["@graph"][0]
    assert first == {"@type": "Assertion", "assertedBy": "khg-contracts:conformance", "subject": "store:memory",
                     "test": {"@id": "S-READ-001", "@type": "TestCase", "identifier": "S-READ-001",
                              "title": SUITE.scenarios["S-READ-001"]["title"],
                              "requires": SUITE.scenarios["S-READ-001"]["requires"]},
                     "mode": "automatic", "result": {"@type": "TestResult", "outcome": "passed"}}
    assert json.loads(conformance.to_json(report)) == report
    assert conformance.OUTCOMES == ("passed", "failed", "inapplicable", "cantTell")


def test_write_report_writes_the_json_text(tmp_path):
    report = conformance.run(memory_factory, only="S-EXP-00?")
    path = tmp_path / "earl.json"
    conformance.write_report(report, path)
    assert path.read_text(encoding="utf-8") == conformance.to_json(report)
    assert json.loads(path.read_text(encoding="utf-8"))["summary"]["passed"] == 9
    assert [p.name for p in tmp_path.iterdir()] == ["earl.json"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
@pytest.mark.parametrize("umask, mode", [(0o022, 0o644), (0o027, 0o640)], ids=["umask-022", "umask-027"])
def test_the_written_report_gets_the_mode_the_umask_allows(tmp_path, umask, mode):
    """S7: as for ``khg-conformance --report``; the temporary file is not mkstemp's, whose mode is 0600."""
    report = conformance.run(memory_factory, only="S-EXP-001")
    path = tmp_path / "earl.json"
    old = os.umask(umask)
    try:
        conformance.write_report(report, path)
    finally:
        os.umask(old)
    assert stat.S_IMODE(path.stat().st_mode) == mode
    assert path.read_text(encoding="utf-8") == conformance.to_json(report)
    assert [p.name for p in tmp_path.iterdir()] == ["earl.json"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
@pytest.mark.parametrize("mode", [0o600, 0o640, 0o444], ids=["0600", "0640", "0444"])
def test_an_existing_report_keeps_its_mode(tmp_path, mode):
    """Review integration (CLI-FILE-MODE, group ex's request): as ``khg-conformance --report`` now does, replacing a
    report keeps its mode; a new report gets the umask's."""
    report = conformance.run(memory_factory, only="S-EXP-001")
    path = tmp_path / "earl.json"
    path.write_text("{}", encoding="utf-8")
    path.chmod(mode)
    old = os.umask(0o022)
    try:
        conformance.write_report(report, path)
        conformance.write_report(report, tmp_path / "new.json")
    finally:
        os.umask(old)
    assert stat.S_IMODE(path.stat().st_mode) == mode
    assert path.read_text(encoding="utf-8") == conformance.to_json(report)
    assert stat.S_IMODE((tmp_path / "new.json").stat().st_mode) == 0o644
    assert sorted(p.name for p in tmp_path.iterdir()) == ["earl.json", "new.json"]


def test_a_failed_report_write_keeps_the_old_file_and_leaves_no_temporary_file(tmp_path, monkeypatch):
    report = conformance.run(memory_factory, only="S-EXP-001")
    path = tmp_path / "earl.json"
    path.write_text("old\n", encoding="utf-8")

    def refuse(src, dst):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", refuse)
    with pytest.raises(OSError):
        conformance.write_report(report, path)
    assert path.read_text(encoding="utf-8") == "old\n"
    assert [p.name for p in tmp_path.iterdir()] == ["earl.json"]


def test_the_report_is_deterministic():
    a = conformance.to_json(conformance.run(limited(TYPEDB)))
    b = conformance.to_json(conformance.run(limited(TYPEDB)))
    assert a == b


# ------------------------------------------------------------------------------------------------ outcomes


class Lying(MemoryStore):
    """Declares every flag while it lacks some: the runner then runs scenarios the store cannot do."""

    def info(self):
        return dict(super().info(), capabilities=ALL_FLAGS)


@pytest.mark.parametrize("flag", sorted(ALL_FLAGS - {"key_constraint"}))
def test_each_flag_is_enforced_by_the_store(flag):
    """A store that lacks one flag but declares all of them fails some scenario that needs the flag, with the
    ``CapabilityMissing`` of that flag; every scenario that does not need it passes. (A store that declares
    ``atomic_writes`` gets batched given steps, so without it other scenarios fail too.)"""
    factory = (lambda schema, clock: Lying(schema, clock=clock, capabilities=ALL_FLAGS - {flag}))
    results = outcomes(conformance.run(factory))
    needing = [i for i in IDS if flag in SUITE.scenarios[i]["requires"]]
    if flag != "atomic_writes":
        assert all(results[i]["outcome"] == "passed" for i in IDS if i not in needing)
    raised = [i for i in needing if results[i]["outcome"] == "failed"
              and results[i]["info"].startswith(f"the store declares {flag} but raised CapabilityMissing")]
    assert raised


def test_without_the_key_constraint_collisions_go_unnoticed():
    factory = (lambda schema, clock: Lying(schema, clock=clock, capabilities=ALL_FLAGS - {"key_constraint"}))
    out = conformance.run_scenario(factory, "S-KEY-001")
    assert out.outcome == "failed" and "did not raise KHG-D016" in out.info


class NoGet(MemoryStore):
    """Lacks history export and raises it from get: a flag the scenarios that call get do not list."""

    def get(self, id, **kw):
        raise CapabilityMissing("history_export")


def test_an_undeclared_capability_error_is_cant_tell():
    factory = (lambda schema, clock: NoGet(schema, clock=clock, capabilities=ALL_FLAGS - {"history_export"}))
    out = conformance.run_scenario(factory, "S-PUT-001")
    assert out.outcome == "cantTell" and out.missing == ["history_export"]
    assert "does not list in requires" in out.info


class Reversed(MemoryStore):
    def incident(self, node, **kw):
        return list(reversed(super().incident(node, **kw)))


class Crashing(MemoryStore):
    def export(self, *a, **kw):
        raise RuntimeError("disk full")


def test_wrong_results_crashes_and_factory_errors_fail():
    out = conformance.run_scenario(lambda s, c: Reversed(s, clock=c), "S-READ-001")
    assert out.outcome == "failed" and "step 1 (incident): incident ids: got" in out.info
    out = conformance.run_scenario(lambda s, c: Crashing(s, clock=c), "S-EXP-001")
    assert out.outcome == "failed" and "RuntimeError" in out.info and "disk full" in out.info

    def broken(schema, clock):
        raise OSError("no database")
    out = conformance.run_scenario(broken, "S-PUT-001")
    assert out.outcome == "failed" and out.info == "the factory raised OSError: no database"


def test_an_unexpected_error_code_fails():
    sc = copy.deepcopy(SUITE.scenarios["S-PUT-004"])
    sc["when"][0]["then"] = {"error": "KHG-D014"}
    out = conformance.run_scenario(memory_factory, sc)
    assert out.outcome == "failed" and "raised KHG-D017" in out.info and "want KHG-D014" in out.info
    sc["when"][0]["then"] = {"error": "KHG-D017", "info": {"nothing": 1}}
    assert conformance.run_scenario(memory_factory, sc).outcome == "failed"


def test_what_the_runner_does_not_know_is_cant_tell():
    sc = copy.deepcopy(SUITE.scenarios["S-PUT-001"])
    sc["when"][0]["then"] = {"select": "colour", "equals": "blue"}
    out = conformance.run_scenario(memory_factory, sc)
    assert (out.outcome, out.info) == ("cantTell", "unknown projection 'colour'")
    sc["when"][0] = {"op": "teleport", "args": {}, "then": {}}
    assert conformance.run_scenario(memory_factory, sc).outcome == "cantTell"
    sc["when"][0] = {"op": "get", "args": {"id": "f:reg-1", "colour": "blue"}, "then": {}}
    assert conformance.run_scenario(memory_factory, sc).info == "get: unknown arguments ['colour']"


def test_every_scenario_store_exports_valid_documents():
    """After each scenario's given steps, the store's snapshot, history and HIF exports pass the validator: the
    snapshot under jsonschema, the reference engine (the store's own layer C check runs fastjsonschema first)."""
    for sid in IDS:
        s = MemoryStore(SUITE.schema, clock=ScenarioClock())
        conformance.run_given(s, SUITE.scenarios[sid]["given"], SUITE, s.capabilities)
        for content, engine in (("snapshot", "jsonschema"), ("history", "fastjsonschema")):
            report = validate.validate_container(s.export("khg-json", content=content), schema=SUITE.schema,
                                                 engine=engine)
            assert report["ok"], (sid, content, [f for f in report["findings"] if f["severity"] == "error"])
        assert validate.validate_hif(s.export("hif"), schema=SUITE.schema, engine="fastjsonschema")["ok"], sid


def test_every_write_the_scenarios_make_leaves_valid_exports():
    """Not only the given steps: after each accepted put, apply or load of a scenario's ``when`` steps, the snapshot
    and the history export pass the validator. S-LIFE-013's undo resolved by a dispute takes a fact from superseded
    to disputed in one version, which the history rule refused (D014)."""
    from khg_contracts.errors import KHGError

    refused = []
    for sid in IDS:
        s = MemoryStore(SUITE.schema, clock=ScenarioClock())
        conformance.run_given(s, SUITE.scenarios[sid]["given"], SUITE, s.capabilities)
        for n, step in enumerate(SUITE.scenarios[sid]["when"], 1):
            if step["op"] not in ("put", "apply", "load"):
                continue
            try:
                conformance.call(s, step, SUITE)
            except KHGError:
                continue  # a step that expects an error
            for content in ("snapshot", "history"):
                report = validate.validate_container(s.export("khg-json", content=content), schema=SUITE.schema,
                                                     engine="fastjsonschema")
                if not report["ok"]:
                    refused.append((sid, n, content, [f["code"] for f in report["findings"]
                                                      if f["severity"] == "error"]))
    assert refused == []


def test_a_declared_flag_beyond_the_ten_is_not_tested():
    """A backend may declare a flag of its own or of a later version; the v1 suite runs on the ten it knows (the run
    raised ValueError and gave no report)."""
    class Extra(MemoryStore):
        def info(self):
            return dict(super().info(), capabilities=self.capabilities | {"full_text_search"})

    report = conformance.run(lambda schema, clock: Extra(schema, clock=clock), only="S-PUT-00*")
    assert report["summary"]["failed"] == report["summary"]["cantTell"] == 0 and report["summary"]["passed"] == 9
    subject = report["subject"]
    assert "full_text_search" in subject["capabilities"] and "full_text_search" not in subject["tested_capabilities"]
    assert conformance.run_scenario(lambda schema, clock: Extra(schema, clock=clock), "S-PUT-001").outcome == "passed"
    with pytest.raises(ValueError):  # a caller's own list is still checked
        conformance.run(memory_factory, only="S-PUT-001", capabilities=["full_text_search"])
