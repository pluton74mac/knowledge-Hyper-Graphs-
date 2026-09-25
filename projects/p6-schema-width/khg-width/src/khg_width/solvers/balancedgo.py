"""BalancedGo (primary hw solver, DetK mode ``-det``; MIT). Decompositions come back through ``-json FILE``."""
from __future__ import annotations

import os

from .runner import FLAGS, Outcome, call

__all__ = ["command", "solve"]


def command(binary: str, graph: str, *, k: int | None, exact: bool = False, flags: bool = False, cpu: int = 2,
            json_out: str | None = None) -> list[str]:
    cmd = [binary, "-graph", graph]
    cmd += ["-exact"] if exact else ["-width", str(k)]
    cmd += ["-det"]
    if flags:
        cmd += list(FLAGS)
    cmd += ["-cpu", str(cpu)]
    if json_out:
        cmd += ["-json", json_out]
    return cmd


def solve(binary: str, graph: str, workdir: str, *, k: int | None, exact: bool = False, flags: bool = False,
          timeout: float, cpu: int = 2) -> Outcome:
    out = os.path.join(workdir, f"balancedgo-{'exact' if exact else k}{'-flags' if flags else ''}.json")
    if os.path.exists(out):
        os.remove(out)
    return call("balancedgo", command(binary, graph, k=k, exact=exact, flags=flags, cpu=cpu, json_out=out),
                k=k, exact_mode=exact, flags=flags, timeout=timeout, out_file=out, out_format="json")
