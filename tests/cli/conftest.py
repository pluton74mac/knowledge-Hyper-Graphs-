"""Helpers for the CLI tests (DESIGN §10.4, §10.5 ``cli/``).

- ``run_cli(name, *args)`` runs a command in a child process: the console script (``khg-validate``, ...) installed
  with the package, else ``python -m khg_contracts.cli <command>``. The child imports a ``sitecustomize`` that
  blocks sockets, so it runs offline like the tests themselves (``tests/conftest.py``), and its standard streams are
  UTF-8. ``child_env`` is its environment and ``installed_script(name)`` the script it runs.
- ``packaged(rel)`` is a packaged data file on disk (``khg_contracts.data``, through importlib.resources).
- ``v0_sample`` is the v0 input of the migration, which is test data (``tests/migrate/``), not package data.
"""
from __future__ import annotations

import importlib.metadata as md
import os
import shutil
import subprocess
import sys
import sysconfig
from contextlib import ExitStack
from importlib.resources import as_file
from pathlib import Path
from typing import Callable, Iterator

import pytest

from khg_contracts import data

#: console script -> ``python -m khg_contracts.cli`` command
COMMANDS = {"khg-validate": "validate", "khg-convert": "convert", "khg-migrate": "migrate",
            "khg-conformance": "conformance"}
V0_SAMPLE = Path(__file__).resolve().parent.parent / "migrate" / "v0-sample.hif.json"
BLOCKED = "network access is blocked in the khg-contracts CLI tests"

_SITECUSTOMIZE = f'''"""Written by tests/cli/conftest.py: the CLI test children run offline."""
import socket


def _refuse(*args, **kwargs):
    raise OSError({BLOCKED!r})


for _name in ("connect", "connect_ex", "sendto", "sendmsg"):
    if hasattr(socket.socket, _name):
        setattr(socket.socket, _name, _refuse)
for _name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "getnameinfo",
              "create_connection"):
    if hasattr(socket, _name):
        setattr(socket, _name, _refuse)
'''


def installed_script(name: str) -> str | None:
    """The console script ``name`` that was installed with khg-contracts: from the distribution's ``RECORD``, else
    from this interpreter's scripts directory; None when neither has it."""
    try:
        files = md.distribution("khg-contracts").files or []
    except md.PackageNotFoundError:
        files = []
    for f in files:
        if f.name in (name, f"{name}.exe"):
            path = os.path.normpath(f.locate())
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
    dirs = dict.fromkeys(d for d in (sysconfig.get_path("scripts"), os.path.dirname(sys.executable)) if d)
    return shutil.which(name, path=os.pathsep.join(dirs))


def command_line(name: str) -> list[str]:
    """The console script, else the same command through ``python -m khg_contracts.cli``."""
    script = installed_script(name)
    return [script] if script else [sys.executable, "-m", "khg_contracts.cli", COMMANDS[name]]


@pytest.fixture(scope="session")
def child_env(tmp_path_factory) -> dict[str, str]:
    """The environment of the CLI children: sockets blocked through ``sitecustomize``, UTF-8 streams."""
    site = tmp_path_factory.mktemp("cli-site")
    (site / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(site), env.get("PYTHONPATH", "")) if p)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


@pytest.fixture(scope="session")
def run_cli(child_env) -> Callable[..., subprocess.CompletedProcess]:
    """``run_cli("khg-validate", *args, cwd=None, closed_stdout=False)``: the finished child, with text stdout and
    stderr. With ``closed_stdout`` its standard output is a pipe whose reader has gone (``stdout`` is None then)."""

    def run(name: str, *args: object, cwd: Path | None = None,
            closed_stdout: bool = False) -> subprocess.CompletedProcess:
        argv = command_line(name) + [str(a) for a in args]
        if not closed_stdout:
            return subprocess.run(argv, env=child_env, cwd=cwd, capture_output=True, encoding="utf-8", timeout=600)
        reader, writer = os.pipe()
        os.close(reader)
        try:
            return subprocess.run(argv, env=child_env, cwd=cwd, stdout=writer, stderr=subprocess.PIPE,
                                  encoding="utf-8", timeout=600)
        finally:
            os.close(writer)

    return run


@pytest.fixture(scope="session", name="installed_script")
def _installed_script() -> Callable[[str], str | None]:
    """``installed_script("khg-validate")``: the console script the children run, or None (then ``-m``)."""
    return installed_script


@pytest.fixture(scope="session")
def v0_sample() -> Path:
    """The v0 sample (a verbatim copy of the knowledge base's ``schemas/sample.hif.json``)."""
    return V0_SAMPLE


@pytest.fixture(scope="session")
def packaged() -> Iterator[Callable[[str], Path]]:
    """``packaged("fixture/fixture.c1.json")``: the packaged file as a path on disk."""
    with ExitStack() as stack:
        yield lambda rel: Path(stack.enter_context(as_file(data.path(rel))))
