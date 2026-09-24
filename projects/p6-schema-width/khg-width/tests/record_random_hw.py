"""Record the hypertree width of R01's 400 seeded random hypergraphs, 150 denser ones and R01's named instances with
the external solvers (F2).

    KHG_WIDTH_SOLVERS=<DEST of scripts/build-solvers.sh> python tests/record_random_hw.py

For each hypergraph (its set hypergraph, in the neutral ids khg-width gives the solvers) it runs
``BalancedGo -exact -det`` and ``log-k-decomp -exact``, requires both to report the same K with ``Correct: true``,
and writes ``fixtures/random-hw.json``: the value list in the order of ``helpers.random_set()``, the commands and the
tools' commits and sha256. ``test_widths`` compares khg-width's hw with it, so CI needs no binaries and the truth
does not come from khg-width's own search.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from helpers import SEED, dense_set, named_set, random_set  # noqa: E402
from khg_width import Hypergraph, find_solvers  # noqa: E402
from khg_width.solvers.parsers import parse_stdout  # noqa: E402


def main() -> int:
    tools = find_solvers()
    if not {"balancedgo", "logk"} <= set(tools):
        sys.exit("both BalancedGo and log-k-decomp are needed (scripts/build-solvers.sh)")
    cmds = {"balancedgo": [tools["balancedgo"].path, "-graph", "{graph}", "-exact", "-det"],
            "logk": [tools["logk"].path, "-graph", "{graph}", "-exact"]}
    def record(hypergraphs: list[dict]) -> list[int]:
        values = []
        with tempfile.TemporaryDirectory() as work:
            g = os.path.join(work, "h.hg")
            for i, edges in enumerate(hypergraphs):
                h = Hypergraph.from_mapping(edges).distinct()
                Path(g).write_text(h.neutral.text)
                got = {}
                for tool, cmd in cmds.items():
                    r = subprocess.run([c.format(graph=g) for c in cmd], capture_output=True, text=True, timeout=600)
                    p = parse_stdout(r.stdout)
                    if r.returncode != 0 or p.correct is not True:
                        sys.exit(f"hypergraph {i}: {tool} failed: {r.stdout[-500:]} {r.stderr[-500:]}")
                    got[tool] = p.k
                if got["balancedgo"] != got["logk"]:
                    sys.exit(f"hypergraph {i}: the tools disagree: {got}")
                values.append(got["balancedgo"])
        return values

    named = named_set()
    values = record(random_set())
    dense = record(dense_set())
    named_hw = dict(zip(named, record(list(named.values()))))
    out = {"format": "khg-width-recorded-hw/1", "seed": SEED, "count": len(values),
           "source": "tests/helpers.py random_set() (R01's probe_theory generator); set hypergraphs in neutral ids",
           "commands": {t: " ".join(os.path.basename(c) if j == 0 else c for j, c in enumerate(cmd))
                        for t, cmd in cmds.items()},
           "tools": {t: {"commit": tools[t].commit, "sha256": tools[t].sha256} for t in cmds},
           "hw": values,
           "dense_source": "tests/helpers.py dense_set() (seed 20260925: 150 hypergraphs, 6-9 roles, 8-14 relations)",
           "dense_hw": dense,
           "named_hw": named_hw}
    (HERE / "fixtures" / "random-hw.json").write_text(json.dumps(out, indent=1) + "\n")
    from collections import Counter
    print(len(values), "random:", dict(sorted(Counter(values).items())), "; dense:",
          dict(sorted(Counter(dense).items())), "; named:", named_hw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
