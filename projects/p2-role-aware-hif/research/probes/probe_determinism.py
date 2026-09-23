#!/usr/bin/env python3
"""Is HIF output byte-identical across Python hash seeds? (P2 research, 2026-09-23)

XGI keeps edge members in Python sets, and string hashing is salted per process (PYTHONHASHSEED), so
the order in which it writes incidences and node records can change from run to run. This script
writes schemas/sample.hif.json back out in child processes with different seeds, through
xgi.write_hif, hnx.to_hif, and the two sketch adapters, and compares sha256 of the bytes.

Needs network access for the hnx.to_hif rows (HyperNetX fetches its schema on every call).
Output: out/determinism.json
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from probe_common import OUT_DIR, SAMPLE, dump, env_info  # noqa: E402

SNIPPETS = {
    "xgi.write_hif(xgi.read_hif(sample))": (
        "import xgi, os, sys, tempfile\n"
        "H = xgi.read_hif(sys.argv[1])\n"
        "fd, p = tempfile.mkstemp(suffix='.hif.json'); os.close(fd)\n"
        "xgi.write_hif(H, p)\n"
        "sys.stdout.write(open(p, encoding='utf-8').read()); os.remove(p)\n"),
    "hnx.to_hif(hnx.from_hif(sample), network_type='directed')": (
        "import warnings; warnings.filterwarnings('ignore')\n"
        "import hypernetx as hnx, json, sys\n"
        "H = hnx.from_hif(filename=sys.argv[1])\n"
        "sys.stdout.write(json.dumps(hnx.to_hif(H, network_type='directed')))\n"),
    "sketch from_xgi(to_xgi(sample))": (
        "import json, sys\n"
        f"sys.path.insert(0, {HERE!r})\n"
        "import role_loaders_sketch as rl\n"
        "doc = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "H, ctx = rl.to_xgi(doc)\n"
        "sys.stdout.write(json.dumps(rl.from_xgi(H, ctx), ensure_ascii=False))\n"),
    "sketch from_hnx(to_hnx(sample))": (
        "import warnings; warnings.filterwarnings('ignore')\n"
        "import json, sys\n"
        f"sys.path.insert(0, {HERE!r})\n"
        "import role_loaders_sketch as rl\n"
        "doc = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "H, ctx = rl.to_hnx(doc)\n"
        "sys.stdout.write(json.dumps(rl.from_hnx(H, ctx), ensure_ascii=False))\n"),
}


def main():
    res = {"env": env_info(("xgi", "hypernetx")), "input": "schemas/sample.hif.json", "runs": {}}
    for label, code in SNIPPETS.items():
        hashes = {}
        for seed in ("1", "2", "3", "4"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            p = subprocess.run([sys.executable, "-c", code, SAMPLE], capture_output=True, env=env, timeout=300)
            if p.returncode != 0:
                hashes[seed] = "ERROR " + p.stderr.decode()[-300:]
                continue
            out = p.stdout
            first = [(r["edge"], r["node"]) for r in json.loads(out)["incidences"][:4]]
            hashes[seed] = {"sha256": hashlib.sha256(out).hexdigest(), "first_incidences": first}
        distinct = {v["sha256"] for v in hashes.values() if isinstance(v, dict)}
        res["runs"][label] = {"seeds": hashes, "distinct_outputs": len(distinct)}
        print(f"{label:60s} distinct outputs over 4 seeds: {len(distinct)}")
    dump(res, os.path.join(OUT_DIR, "determinism.json"))


if __name__ == "__main__":
    main()
