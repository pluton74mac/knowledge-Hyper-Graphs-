"""log-k-decomp (second opinion for hw; MIT). Decompositions come back through ``-gml FILE`` (stdout tree as a
fallback)."""
from __future__ import annotations

import os

from .runner import FLAGS, Outcome, call

__all__ = ["command", "solve"]


def command(binary: str, graph: str, *, k: int | None, exact: bool = False, flags: bool = False, cpu: int = 2,
            gml_out: str | None = None) -> list[str]:
    cmd = [binary, "-graph", graph]
    cmd += ["-exact"] if exact else ["-width", str(k)]
    if flags:
        cmd += list(FLAGS)
    cmd += ["-cpu", str(cpu)]
    if gml_out:
        cmd += ["-gml", gml_out]
    return cmd


def solve(binary: str, graph: str, workdir: str, *, k: int | None, exact: bool = False, flags: bool = False,
          timeout: float, cpu: int = 2) -> Outcome:
    out = os.path.join(workdir, f"logk-{'exact' if exact else k}{'-flags' if flags else ''}.gml")
    if os.path.exists(out):
        os.remove(out)
    return call("logk", command(binary, graph, k=k, exact=exact, flags=flags, cpu=cpu, gml_out=out),
                k=k, exact_mode=exact, flags=flags, timeout=timeout, out_file=out, out_format="gml")
