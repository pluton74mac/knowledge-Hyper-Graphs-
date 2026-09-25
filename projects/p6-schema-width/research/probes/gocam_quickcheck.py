"""P6 probe: quick alpha-acyclicity check of the GO-CAM LinkML schema (the fallback biomedical candidate).

Fetches src/gocam/schema/gocam.yaml from geneontology/gocam-py at tag v0.12.0 into
datasets/knowledge-bases/gocam-schema/raw/ (gitignored), records MANIFEST.json, and treats `Activity` and every
concrete `Association` subclass as a relation whose roles are its slots minus `id`, `type`, `evidence` and
`provenances` (meta). Roles keep GO-CAM's global slot names. Prints the hypergraph and the GYO result.

Needs pyyaml and linkml-runtime (run in the same venv as biolink_extract.py), plus the repository's src/ on the
path for khg_contracts:  PYTHONPATH=src python projects/p6-schema-width/research/probes/gocam_quickcheck.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from linkml_runtime.utils.schemaview import SchemaView

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import hg_measure as hm  # noqa: E402

DS = ROOT / "datasets" / "knowledge-bases" / "gocam-schema"
TAG, COMMIT = "v0.12.0", "e6f824a5cc2d50ad1fa12081bec0ca5c945c5199"
URL = f"https://raw.githubusercontent.com/geneontology/gocam-py/{COMMIT}/src/gocam/schema/gocam.yaml"
META = {"id", "type", "evidence", "provenances"}


def main() -> int:
    raw = DS / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / "gocam.yaml"
    if not path.exists():
        req = urllib.request.Request(URL, headers={"User-Agent": "khg-kb-research/0.2 (P6 schema width survey)"})
        path.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    blob = path.read_bytes()
    (DS / "MANIFEST.json").write_text(json.dumps({
        "name": "gocam-schema", "family": "knowledge-bases",
        "source_url": "https://github.com/geneontology/gocam-py",
        "source_ref": f"{TAG} (commit {COMMIT}, committed 2026-07-27)", "retrieved": dt.date.today().isoformat(),
        "licence": "repository LICENSE: BSD-3-Clause text with the placeholder holder 'Copyright (c) 2024, My Name'; "
                   "the schema file declares no licence [unverified: intended licence]",
        "files": [{"path": "raw/gocam.yaml", "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
                   "source_url": URL}],
        "notes": "Fallback biomedical schema for P6; quick check only."}, indent=1) + "\n")
    sv = SchemaView(str(path))
    rels = {"Activity": sv.class_slots("Activity")}
    for c in sorted(sv.class_descendants("Association", reflexive=False)):
        if not sv.get_class(c).abstract:
            rels[c] = sv.class_slots(c)
    edges = {c: sorted(set(s) - META) for c, s in rels.items()}
    ok, residue = hm.alpha(edges)
    print(json.dumps({"relations": len(edges), "edges": edges, "stats": hm.stats(edges), "alpha_acyclic": ok,
                      "residue": [sorted(e) for e in residue]}, indent=1, default=list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
