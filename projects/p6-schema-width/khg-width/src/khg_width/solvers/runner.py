"""Running a solver process with a hard time limit: its own process group (session), killed at the limit."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Sequence

__all__ = ["Run", "run"]


@dataclass(frozen=True)
class Run:
    cmd: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    seconds: float
    timed_out: bool


def run(cmd: Sequence[str], timeout: float, *, cwd: str | None = None) -> Run:
    """Run ``cmd``; at ``timeout`` seconds kill its whole process group. Output is decoded as UTF-8 (replace)."""
    t0 = time.monotonic()
    p = subprocess.Popen(list(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                         cwd=cwd, start_new_session=True)
    timed_out = False
    try:
        out, err = p.communicate(timeout=max(0.01, timeout))
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            p.kill()
        out, err = p.communicate()
    return Run(tuple(cmd), None if timed_out else p.returncode, out.decode("utf-8", "replace"),
               err.decode("utf-8", "replace"), time.monotonic() - t0, timed_out)


# ------------------------------------------------------------------------------------------------ one solver call
FLAGS = ("-t", "-h", "-g", "-heuristic", "1")


@dataclass(frozen=True)
class Outcome:
    """One solver call at one k (or ``-exact``): ``outcome`` is ``yes`` (a decomposition claimed correct), ``no``
    (``Correct: false`` with an empty decomposition and no check-failure message: a refutation when unflagged),
    ``invalid`` (``Correct: false`` for a decomposition the tool found but its own check rejected: never a bound),
    ``timeout`` or ``error``. ``tree`` holds the decomposition in the tool's neutral names."""

    tool: str
    cmd: tuple[str, ...]
    k: int | None
    exact_mode: bool
    flags: bool
    outcome: str
    k_reported: int | None
    width: int | None
    scv: bool
    edges_echoed: int | None
    tree: dict | None
    seconds: float
    returncode: int | None
    stdout_tail: str
    stderr_tail: str
    check_failures: tuple = ()

    def to_json(self) -> dict:
        return {"tool": self.tool, "cmd": list(self.cmd), "k": self.k, "exact": self.exact_mode, "flags": self.flags,
                "outcome": self.outcome, "k_reported": self.k_reported, "width": self.width, "scv": self.scv,
                "check_failures": list(self.check_failures), "seconds": round(self.seconds, 3),
                "returncode": self.returncode, "stdout_tail": self.stdout_tail, "stderr_tail": self.stderr_tail}


def call(tool: str, cmd: Sequence[str], *, k: int | None, exact_mode: bool, flags: bool, timeout: float,
         out_file: str | None, out_format: str | None) -> Outcome:
    """Run one solver command and classify its outcome; the tree comes from ``out_file`` (json or gml) when the
    tool wrote it, else from stdout."""
    from .parsers import parse_gml, parse_json, parse_stdout

    r = run(cmd, timeout)
    p = parse_stdout(r.stdout)
    tree = None
    if out_file and os.path.exists(out_file):
        try:
            with open(out_file, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            tree = parse_json(text) if out_format == "json" else parse_gml(text)
        except (OSError, ValueError):
            tree = None
    if tree is None:
        tree = p.tree
    if r.timed_out:
        outcome = "timeout"
    elif r.returncode not in (0, None) or "panic:" in r.stdout + r.stderr or p.correct is None:
        outcome = "error"
    elif p.correct:
        outcome = "yes"
    elif p.tree is None and not p.check_failures:
        outcome = "no"
    else:
        outcome = "invalid"  # F1: a found decomposition that failed the tool's own check is not a refutation
    tail = lambda s: s[-2000:]  # noqa: E731
    return Outcome(tool=tool, cmd=tuple(cmd), k=k, exact_mode=exact_mode, flags=flags, outcome=outcome,
                   k_reported=p.k, width=p.width, scv=p.scv, edges_echoed=p.edges_echoed,
                   tree=tree if outcome in ("yes", "invalid") else None, seconds=r.seconds, returncode=r.returncode,
                   stdout_tail=tail(r.stdout), stderr_tail=tail(r.stderr), check_failures=p.check_failures)
