"""W12: ``khg-conformance --factory MODULE:CALLABLE [--only GLOB] [--capabilities FLAGS] [--report PATH]`` (DESIGN
§10.4, §6.4) runs the C2 suite and writes the EARL report. It exits 1 when a scenario is ``failed`` or ``cantTell``
(the director's ruling: ``passed`` and ``inapplicable`` are not failures), and 2 on a usage or I/O error."""
from __future__ import annotations

import json
import os
import stat
import sys
import types

import pytest

from khg_contracts import cli
from khg_contracts.errors import CapabilityMissing
from khg_contracts.store import ALL_FLAGS, MemoryStore, conformance, memory_factory

MODULE = "khg_cli_test_factories"


class Reversed(MemoryStore):
    """Returns incident facts in the wrong order: S-READ-001 fails."""

    def incident(self, node, **kw):
        return list(reversed(super().incident(node, **kw)))


class NoGet(MemoryStore):
    """Lacks ``history_export`` and raises it from ``get``, which S-PUT-001 does not list: cantTell."""

    def get(self, id, **kw):
        raise CapabilityMissing("history_export")


def _broken(schema, clock):
    raise OSError("no database")


@pytest.fixture
def factories(monkeypatch):
    """A module of store factories, importable as ``khg_cli_test_factories``."""
    module = types.ModuleType(MODULE)
    module.reversed_incident = lambda schema, clock: Reversed(schema, clock=clock)
    module.no_get = lambda schema, clock: NoGet(schema, clock=clock, capabilities=ALL_FLAGS - {"history_export"})
    module.no_valid_time = lambda schema, clock: MemoryStore(schema, clock=clock,
                                                             capabilities=ALL_FLAGS - {"valid_time"})
    module.broken = _broken
    module.stores = types.SimpleNamespace(memory=memory_factory)
    module.not_callable = 42
    monkeypatch.setitem(sys.modules, MODULE, module)
    return MODULE


def _summary(report):
    return {k: v for k, v in report["summary"].items() if v}


def test_khg_conformance_smoke(run_cli, tmp_path):
    """The reference store passes all 114 scenarios; the report equals the library's, byte for byte."""
    path = tmp_path / "earl.json"
    r = run_cli("khg-conformance", "--factory", "khg_contracts.store:memory_factory", "--report", path)
    assert r.returncode == 0, r.stderr
    assert path.read_text(encoding="utf-8") == conformance.to_json(conformance.run(memory_factory))
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["summary"] == {"passed": 114, "failed": 0, "inapplicable": 0, "cantTell": 0, "total": 114}
    assert r.stdout == ""
    assert r.stderr == ("khg-conformance: memory: 114 passed, 0 failed, 0 inapplicable, 0 cantTell "
                        "(114 of 114 scenarios)\n")


def test_without_report_the_report_goes_to_stdout(capsys):
    assert cli.conformance_main(["--factory", "khg_contracts.store:memory_factory", "--only", "S-EXP-*"]) == 0
    captured = capsys.readouterr()
    assert captured.out == conformance.to_json(conformance.run(memory_factory, only="S-EXP-*"))
    report = json.loads(captured.out)
    assert report["suite"]["selected"] == 13 and _summary(report) == {"passed": 13, "total": 13}
    assert captured.err == ("khg-conformance: memory: 13 passed, 0 failed, 0 inapplicable, 0 cantTell "
                            "(13 of 114 scenarios)\n")


def test_only_takes_several_globs(tmp_path):
    path = tmp_path / "earl.json"
    assert cli.conformance_main(["--factory", "khg_contracts.store:memory_factory", "--only", "S-KEY-00?",
                                 "--only", "S-PUT-001", "--report", str(path)]) == 0
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["suite"]["only"] == ["S-KEY-00?", "S-PUT-001"]
    assert [a["test"]["identifier"] for a in report["@graph"]] == [f"S-KEY-00{i}" for i in range(1, 10)] + ["S-PUT-001"]


def test_capabilities_limit_the_run_and_inapplicable_is_not_a_failure(tmp_path, capsys):
    path = tmp_path / "earl.json"
    assert cli.conformance_main(["--factory", "khg_contracts.store:memory_factory", "--capabilities", "",
                                 "--report", str(path)]) == 0
    report = json.loads(path.read_text(encoding="utf-8"))
    assert _summary(report) == {"passed": 12, "inapplicable": 102, "total": 114}  # no flags: 12 apply (§6.4)
    assert report["subject"]["tested_capabilities"] == []
    assert capsys.readouterr().err.startswith("khg-conformance: memory: 12 passed, 0 failed, 102 inapplicable, ")
    assert cli.conformance_main(["--factory", "khg_contracts.store:memory_factory", "--capabilities",
                                 " valid_time,literal_values ", "--only", "S-TIME-*", "--report", str(path)]) == 0
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["subject"]["tested_capabilities"] == ["literal_values", "valid_time"]
    assert set(_summary(report)) <= {"passed", "inapplicable", "total"} and report["summary"]["passed"] > 0


def test_a_store_that_declares_a_flag_absent(factories, tmp_path):
    path = tmp_path / "earl.json"
    assert cli.conformance_main(["--factory", f"{factories}:no_valid_time", "--report", str(path)]) == 0
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report == conformance.run(lambda s, c: MemoryStore(s, clock=c, capabilities=ALL_FLAGS - {"valid_time"}))
    assert report["summary"]["inapplicable"] > 0 and report["summary"]["failed"] == 0
    assert all(a["result"]["missing"] == ["valid_time"] for a in report["@graph"]
               if a["result"]["outcome"] == "inapplicable")


def test_a_dotted_callable(factories, capsys):
    assert cli.conformance_main(["--factory", f"{factories}:stores.memory", "--only", "S-PUT-00[12]"]) == 0
    assert _summary(json.loads(capsys.readouterr().out)) == {"passed": 2, "total": 2}


# ------------------------------------------------------------------------------------------------ exit 1


def test_a_failed_scenario_exits_1(factories, tmp_path, capsys):
    path = tmp_path / "earl.json"
    assert cli.conformance_main(["--factory", f"{factories}:reversed_incident", "--only", "S-READ-001",
                                 "--report", str(path)]) == 1
    report = json.loads(path.read_text(encoding="utf-8"))
    assert _summary(report) == {"failed": 1, "total": 1}
    err = capsys.readouterr().err.splitlines()
    assert err[0] == "khg-conformance: memory: 0 passed, 1 failed, 0 inapplicable, 0 cantTell (1 of 114 scenarios)"
    assert err[1] == f"khg-conformance: failed S-READ-001: {report['@graph'][0]['result']['info']}"
    assert "incident ids: got" in err[1]


def test_a_cant_tell_scenario_exits_1(factories, tmp_path, capsys):
    """The director's ruling: cantTell is not a pass, although no scenario failed."""
    path = tmp_path / "earl.json"
    assert cli.conformance_main(["--factory", f"{factories}:no_get", "--only", "S-PUT-001",
                                 "--report", str(path)]) == 1
    report = json.loads(path.read_text(encoding="utf-8"))
    assert _summary(report) == {"cantTell": 1, "total": 1}
    assert report["@graph"][0]["result"]["missing"] == ["history_export"]
    assert capsys.readouterr().err.splitlines()[1].startswith("khg-conformance: cantTell S-PUT-001: the store lacks "
                                                              "history_export")


def test_a_store_that_cannot_be_probed_exits_1(factories, tmp_path, capsys):
    path = tmp_path / "earl.json"
    assert cli.conformance_main(["--factory", f"{factories}:broken", "--report", str(path)]) == 1
    assert capsys.readouterr().err == "khg-conformance: the store could not be probed: OSError: no database\n"
    assert not path.exists()


# ------------------------------------------------------------------------------------------------ exit 2


@pytest.mark.parametrize("spec, message", [
    ("khg_contracts.store", "--factory 'khg_contracts.store' is not MODULE:CALLABLE"),
    (":memory_factory", "--factory ':memory_factory' is not MODULE:CALLABLE"),
    ("khg_contracts.store:", "--factory 'khg_contracts.store:' is not MODULE:CALLABLE"),
    ("khg_contracts.no_such_module:factory", "--factory: cannot import khg_contracts.no_such_module: "
                                             "ModuleNotFoundError: No module named 'khg_contracts.no_such_module'"),
    ("khg_contracts.store:no_such_factory", "--factory: khg_contracts.store has no attribute no_such_factory"),
    (f"{MODULE}:not_callable", f"--factory: {MODULE}:not_callable is not callable"),
])
def test_a_factory_that_cannot_be_loaded_exits_2(factories, capsys, spec, message):
    assert cli.conformance_main(["--factory", spec]) == 2
    captured = capsys.readouterr()
    assert captured.err == f"khg-conformance: {message}\n" and captured.out == ""


@pytest.mark.parametrize("argv, message", [
    ([], "the following arguments are required: --factory"),
    (["--capabilities", "literal_values,colour"], "argument --capabilities: unknown flags colour; the flags are "
                                                  "literal_values, special_values"),
    (["--only", "S-NOPE-*"], "--only S-NOPE-* matches no scenario"),
])
def test_usage_errors_exit_2(capsys, argv, message):
    factory = [] if not argv else ["--factory", "khg_contracts.store:memory_factory"]
    assert cli.conformance_main([*factory, *argv]) == 2
    err = capsys.readouterr().err
    assert err.startswith("usage: khg-conformance") and message in err


def test_an_unwritable_report_exits_2(tmp_path, capsys):
    path = tmp_path / "no-such-dir" / "earl.json"
    assert cli.conformance_main(["--factory", "khg_contracts.store:memory_factory", "--only", "S-PUT-001",
                                 "--report", str(path)]) == 2
    assert capsys.readouterr().err.splitlines()[0] == f"khg-conformance: cannot write {path}: No such file or directory"


@pytest.mark.skipif(sys.platform == "win32", reason="a closed pipe is EPIPE on POSIX")
def test_a_closed_standard_output_exits_2(run_cli):
    """``khg-conformance ... | true``: every scenario passed, but the report could not be written, an I/O error
    (it was a ``BrokenPipeError`` traceback and 1, which reads as a failing store)."""
    r = run_cli("khg-conformance", "--factory", "khg_contracts.store:memory_factory", "--only", "S-PUT-*",
                closed_stdout=True)
    assert r.returncode == 2 and "Traceback" not in r.stderr
    assert r.stderr.endswith("khg-conformance: cannot write the standard output: Broken pipe\n")


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_an_existing_report_keeps_its_mode(tmp_path):
    path = tmp_path / "earl.json"
    path.write_text("{}\n", encoding="utf-8")
    path.chmod(0o600)
    assert cli.conformance_main(["--factory", "khg_contracts.store:memory_factory", "--only", "S-PUT-001",
                                 "--report", str(path)]) == 0
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and json.loads(path.read_text(encoding="utf-8"))["@graph"]
