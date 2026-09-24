"""P6 probe: extract Biolink Model association classes as relation schemas (roles and slot classes).

Fetches biolink-model.yaml at a pinned commit (release tag v4.4.5) into
datasets/knowledge-bases/biolink-model/raw/ (gitignored), records it in MANIFEST.json (tracked), then reads
it with LinkML's SchemaView and writes one row per association class:

    {class, abstract, is_a, mixins, subject_range, object_range, predicate_range,
     qualifiers_formal: [slots under Biolink's `qualifier` grouping slot],
     domain_slots: [other class-specific association slots, classed by this probe],
     meta_slots: [provenance, scores, denormalised and node slots]}

to research/probes/out/biolink-associations.json (small; derived from a CC0 model).

Needs: pyyaml, linkml-runtime (tested with linkml-runtime 1.11.1). Not in khg-contracts' dependencies, so it
runs in its own venv. Run from the repository root:

    python projects/p6-schema-width/research/probes/biolink_extract.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path

from linkml_runtime.utils.schemaview import SchemaView

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DS = ROOT / "datasets" / "knowledge-bases" / "biolink-model"
TAG = "v4.4.5"
COMMIT = "a4180f818e9722c493788c5ff1f047fde64f13a7"
FILES = {
    "biolink-model.yaml": f"https://raw.githubusercontent.com/biolink/biolink-model/{COMMIT}/biolink-model.yaml",
    "attributes.yaml": f"https://raw.githubusercontent.com/biolink/biolink-model/{COMMIT}/attributes.yaml",
    "LICENSE": f"https://raw.githubusercontent.com/biolink/biolink-model/{COMMIT}/LICENSE",
}
UA = "khg-kb-research/0.2 (P6 schema width survey; https://github.com/pluton74mac/knowledge-Hyper-Graphs-)"

# Class-specific association slots that are not under Biolink's `qualifier` slot but restrict what the
# statement says (context, location, quantity, direction, zygosity, stoichiometry, approval state). This is
# this probe's reading of the slot descriptions at v4.4.5, not a Biolink classification.
DOMAIN_TRUTH_CHANGING = {
    "allelic requirement", "associated environmental context", "catalyst qualifier", "clinical approval status",
    "end interbase coordinate", "expression site", "FDA adverse event level", "genome build", "has count",
    "has percentage", "has quotient", "has total", "has zygosity", "interacting molecules category",
    "max research phase", "number of cases", "phase", "phenotypic state", "quantifier qualifier",
    "reaction direction", "reaction side", "start interbase coordinate", "stoichiometry", "strand",
    "treatment outcome",
}
GROUPING = {"qualifier", "qualifiers"}  # Biolink's grouping slot and its generic bag; not roles
CORE = {"subject", "object"}


def fetch() -> dict:
    raw = DS / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    files = []
    for name, url in FILES.items():
        path = raw / name
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as r:
                path.write_bytes(r.read())
        blob = path.read_bytes()
        files.append({"path": f"raw/{name}", "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
                      "source_url": url})
    manifest = {
        "name": "biolink-model",
        "family": "knowledge-bases",
        "source_url": "https://github.com/biolink/biolink-model",
        "source_ref": f"{TAG} (commit {COMMIT}, committed 2026-09-18)",
        "retrieved": dt.date.today().isoformat(),
        "licence": "model: CC0-1.0 (the `license:` field of biolink-model.yaml); repository LICENSE file: "
                   "Apache-2.0; Python package metadata (pyproject.toml): MIT",
        "files": files,
        "notes": "Only the schema file, its local import attributes.yaml and the licence are fetched; the other import, linkml:types, comes with linkml-runtime. Parsed with linkml-runtime SchemaView by "
                 "projects/p6-schema-width/research/probes/biolink_extract.py.",
    }
    (DS / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def rng(slot) -> str | list[str] | None:
    if slot.any_of:
        return sorted(a.range for a in slot.any_of if a.range)
    return slot.range


def main() -> int:
    manifest = fetch()
    sv = SchemaView(str(DS / "raw" / "biolink-model.yaml"))
    classes = sv.all_classes()
    assoc = sorted(sv.class_descendants("association", reflexive=True))
    quals = set(sv.slot_descendants("qualifier", reflexive=False))
    base = set(sv.class_slots("association"))
    rows = []
    for c in assoc:
        cd = classes[c]
        induced = {s.name: s for s in sv.class_induced_slots(c)}
        names = set(sv.class_slots(c))
        q = sorted(names & quals)
        domain = sorted(s for s in names - quals - base - GROUPING if s in DOMAIN_TRUTH_CHANGING)
        meta = sorted(s for s in names - quals - CORE - GROUPING - {"predicate"} if s not in DOMAIN_TRUTH_CHANGING)
        rows.append({
            "class": c, "abstract": bool(cd.abstract), "mixin": bool(cd.mixin), "is_a": cd.is_a,
            "mixins": list(cd.mixins or []),
            "subject_range": rng(induced["subject"]) if "subject" in induced else None,
            "object_range": rng(induced["object"]) if "object" in induced else None,
            "predicate_range": rng(induced["predicate"]) if "predicate" in induced else None,
            "qualifiers_formal": q, "domain_slots": domain, "meta_slots": meta,
        })
    out = {
        "source": manifest["source_ref"], "sha256": manifest["files"][0]["sha256"],
        "extracted": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "qualifier_slots_defined": sorted(quals),
        "base_association_slots": sorted(base),
        "domain_truth_changing": sorted(DOMAIN_TRUTH_CHANGING),
        "classes": rows,
    }
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "biolink-associations.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(rows)} association classes; {len(quals)} qualifier slots defined")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
