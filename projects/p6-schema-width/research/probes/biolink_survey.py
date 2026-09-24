"""P6 probe: Biolink Model association classes as khg-relation-schema/1.0.0 documents; alpha-acyclicity quick check.

Input: out/biolink-associations.json written by biolink_extract.py (Biolink v4.4.5). One relation per concrete
association class (abstract classes are left out: their slots reach the schema through their concrete
descendants). Roles:

- core: `subject`, `object` (named per variant below). `predicate` is not a role: it is the relation type within
  the class's allowed predicates, so it is kept as a label only.
- qualifier: slots under Biolink's `qualifier` grouping slot ("formal"), optionally plus the class-specific
  truth-changing slots listed in biolink_extract.DOMAIN_TRUTH_CHANGING ("domain").
- meta: every other association slot (provenance, scores, denormalised closures, node slots).

Variants: a_generic (Biolink's own global `subject`/`object`), b_local (`<class>:subject`), c_typed
(`subject:<range>` from the class's slot_usage), e_relation_local (every role scoped to its class; the control).

Run from the repository root with the khg-contracts venv:
    python projects/p6-schema-width/research/probes/biolink_survey.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import hg_measure as hm  # noqa: E402
from khg_contracts.schema import check_schema, is_alpha_acyclic, schema_hypergraph  # noqa: E402

VARIANTS = ["a_generic", "b_local", "c_typed", "e_relation_local"]


def snake(name: str) -> str:
    """Biolink's slot CURIE local name: 'object aspect qualifier' -> 'object_aspect_qualifier'."""
    return name.replace(" ", "_")


def camel(name: str) -> str:
    """Biolink's class CURIE local name: 'chemical affects gene association' -> 'ChemicalAffectsGeneAssociation'."""
    return "".join(w[:1].upper() + w[1:] for w in name.split(" "))


def rng(x) -> str:
    return "|".join(camel(v) for v in x) if isinstance(x, list) else camel(str(x))


def core_roles(variant: str, row: dict) -> tuple[str, str]:
    c = camel(row["class"])
    if variant == "a_generic":
        return "subject", "object"
    if variant in ("b_local", "e_relation_local"):
        return f"{c}:subject", f"{c}:object"
    if variant == "c_typed":
        return f"subject:{rng(row['subject_range'])}", f"object:{rng(row['object_range'])}"
    raise ValueError(variant)


def build(variant: str, rows: list[dict], *, domain: bool, meta: bool) -> dict:
    roles: dict[str, dict] = {}
    rels = []
    for row in rows:
        s, o = core_roles(variant, row)
        local = variant == "e_relation_local"
        usages = [{"role": s, "slot": "core", "fillers": [{"entity": ["NamedThing"]}], "min": 1, "max": 1,
                   "direction": "tail"},
                  {"role": o, "slot": "core", "fillers": [{"entity": ["NamedThing"]}], "min": 1, "max": 1,
                   "direction": "head"}]
        extra = [(q, "qualifier") for q in row["qualifiers_formal"]]
        if domain:
            extra += [(q, "qualifier") for q in row["domain_slots"]]
        if meta:
            extra += [(q, "meta") for q in row["meta_slots"]]
        for q, slot in extra:
            usages.append({"role": f"{camel(row['class'])}:{snake(q)}" if local else snake(q), "slot": slot,
                           "fillers": [{"literal": "string"}], "min": 0, "max": None})
        for u in usages:
            roles.setdefault(u["role"], {"id": u["role"]})
        rels.append({"id": camel(row["class"]), "label": row["class"], "roles": usages})
    return {"kind": "relation-schema", "format": "khg-relation-schema/1.0.0", "id": f"biolink-{variant}",
            "version": "0.1.0", "label": f"Biolink Model v4.4.5 association classes, naming {variant}",
            "entity_types": [{"id": "NamedThing"}], "roles": list(roles.values()), "relations": rels}


def main() -> int:
    data = json.loads((HERE / "out" / "biolink-associations.json").read_text())
    rows = [r for r in data["classes"] if not r["abstract"]]
    desc = {
        "source": data["source"], "sha256": data["sha256"],
        "association_classes": len(data["classes"]), "concrete": len(rows),
        "abstract": [r["class"] for r in data["classes"] if r["abstract"]],
        "qualifier_slots_defined": len(data["qualifier_slots_defined"]),
        "qualifier_slots_used": len({q for r in data["classes"] for q in r["qualifiers_formal"]}),
        "qualifiers_per_class": sorted(Counter(len(r["qualifiers_formal"]) for r in rows).items()),
        "most_shared_qualifiers": Counter(q for r in rows for q in r["qualifiers_formal"]).most_common(20),
        "domain_slots_used": Counter(q for r in rows for q in r["domain_slots"]).most_common(),
        "subject_ranges": Counter(rng(r["subject_range"]) for r in rows).most_common(12),
        "object_ranges": Counter(rng(r["object_range"]) for r in rows).most_common(12),
    }
    runs = []
    for variant in VARIANTS:
        for qset, (domain, meta) in {"formal qualifiers": (False, False), "formal + domain": (True, False),
                                     "all slots": (True, True)}.items():
            doc = build(variant, rows, domain=domain, meta=meta)
            errors = [f for f in check_schema(doc) if f["severity"] == "error"]
            slots = ("core", "qualifier", "meta") if meta else ("core", "qualifier")
            hg = schema_hypergraph(doc, slots=slots)
            ok, residue = hm.alpha(hg)
            ref_ok, ref_res = is_alpha_acyclic(hg)
            assert ref_ok == ok and sorted(map(sorted, ref_res)) == sorted(map(sorted, residue))
            st = hm.stats(hg)
            rv = set().union(*residue) if residue else set()
            runs.append({"variant": variant, "qualifiers": qset, "schema_errors": len(errors), **st,
                         "alpha_acyclic": ok, "residue_edges": len(residue), "residue_vertices": len(rv),
                         "residue_sample": sorted(map(sorted, residue))[:3]})
            print(f"{variant:17} {qset:18} E={st['edges']} V={st['vertices']} maxE={st['max_edge']} "
                  f"comp={st['components']} alpha={ok} residue={len(residue)}/{len(rv)} errors={len(errors)}",
                  file=sys.stderr)
    (HERE / "out" / "biolink-survey.json").write_text(json.dumps({"describe": desc, "runs": runs}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
