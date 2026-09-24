"""P6 probe: how far the pure-Python exact DP reaches (wall time of tw, ghw, fhw on the larger instances).

Run:  python probe_dp_limits.py      (writes out/dp_limits.json; needs scipy for fhw)
"""
from __future__ import annotations

import json
import os
import platform
import time

import instances
import p6check as pc

HERE = os.path.dirname(os.path.abspath(__file__))

JOBS = [("c_grid4", "tw"), ("c_grid4", "ghw"), ("c_grid4", "fhw"), ("adler", "fhw"),
        ("grohe_marx_3", "tw"), ("grohe_marx_3", "ghw"), ("c_grid5", "hw"), ("grohe_marx_3", "hw")]


def main() -> None:
    out = {"python": platform.python_version(), "machine": platform.machine(), "runs": []}
    for name, what in JOBS:
        e = pc.normalise(instances.INSTANCES[name][0])
        t = time.time()
        if what == "tw":
            val = pc.treewidth(e, limit=20)[0]
        elif what == "ghw":
            val = pc.ghw(e, limit=20)[0]
        elif what == "fhw":
            val = str(pc.fhw(e, limit=20)[0])
        else:
            k, tree = pc.hw(e, kmax=5)
            val = {"hw": k, "valid": pc.validate_hd(e, tree)}
        row = {"instance": name, "measure": what, "value": val, "seconds": round(time.time() - t, 1),
               "core_vertices": len(set().union(*pc.reduce_core(e).values())) if pc.reduce_core(e) else 0}
        out["runs"].append(row)
        print(row, flush=True)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "out", "dp_limits.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
