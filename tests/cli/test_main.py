"""W12: the four commands as console scripts and through ``python -m khg_contracts.cli`` (DESIGN §10.4), their help,
and the offline child processes of the CLI tests."""
from __future__ import annotations

import importlib.metadata as md
import json
import subprocess
import sys

import pytest

from khg_contracts import cli, validate

SCRIPTS = {"khg-validate": cli.validate_main, "khg-convert": cli.convert_main, "khg-migrate": cli.migrate_main,
           "khg-conformance": cli.conformance_main}
FAILS = {"khg-validate": "a finding is an error", "khg-convert": "IN fails validation or cannot be converted",
         "khg-migrate": "the migration refuses IN", "khg-conformance": "a scenario is failed or cantTell"}


def test_python_m_runs_a_command(child_env, packaged):
    schema = str(packaged("fixture/fixture.relation-schema.json"))
    r = subprocess.run([sys.executable, "-m", "khg_contracts.cli", "validate", schema, "--json"], env=child_env,
                       capture_output=True, encoding="utf-8", timeout=600)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == validate.validate(schema) == {"ok": True, "findings": []}


def test_the_dispatcher(capsys):
    assert cli.main([]) == 2
    assert capsys.readouterr().err.splitlines() == [
        "usage: python -m khg_contracts.cli {validate,convert,migrate,conformance} [ARGS ...]",
        "khg_contracts.cli: error: a command is required"]
    assert cli.main(["check"]) == 2
    assert capsys.readouterr().err.splitlines()[-1] == "khg_contracts.cli: error: unknown command 'check'"
    assert cli.main(["--help"]) == 0
    assert capsys.readouterr().out.startswith("usage: python -m khg_contracts.cli {validate,convert,migrate,")
    assert cli.main(["migrate", "--help"]) == 0
    assert capsys.readouterr().out.startswith("usage: khg-migrate")


def test_the_dispatcher_and_the_console_scripts_run_the_same_functions():
    eps = {ep.name: ep for ep in md.entry_points(group="console_scripts") if ep.value.startswith("khg_contracts.")}
    assert sorted(eps) == sorted(SCRIPTS)
    for name, ep in eps.items():
        assert ep.load() is SCRIPTS[name] is cli.COMMANDS[name[len("khg-"):]]


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_each_command_has_help_with_its_exit_statuses(name, capsys):
    assert SCRIPTS[name](["--help"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"usage: {name} ")
    assert (f"Exit status: 0 on success, 1 when {FAILS[name]}, 2 on a usage or I/O error."
            in " ".join(out.split()))


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_an_unknown_option_is_a_usage_error(name, capsys):
    assert SCRIPTS[name](["--frobnicate"]) == 2
    err = capsys.readouterr().err
    assert err.startswith(f"usage: {name} ") and f"{name}: error: " in err


def test_the_console_scripts_are_installed(installed_script):
    try:
        md.distribution("khg-contracts")
    except md.PackageNotFoundError:
        pytest.skip("khg-contracts is not installed, so the children run python -m khg_contracts.cli")
    assert all(installed_script(name) for name in SCRIPTS)


def test_the_children_run_offline(child_env):
    """The children's ``sitecustomize`` replaces the socket calls; the check itself opens no connection."""
    code = ("import socket\n"
            "print(socket.create_connection.__name__, socket.socket.connect.__name__)\n"
            "try:\n"
            "    socket.getaddrinfo('localhost', 80)\n"
            "except OSError as e:\n"
            "    print(e)\n")
    r = subprocess.run([sys.executable, "-c", code], env=child_env, capture_output=True, encoding="utf-8",
                       timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "_refuse _refuse\nnetwork access is blocked in the khg-contracts CLI tests\n"
