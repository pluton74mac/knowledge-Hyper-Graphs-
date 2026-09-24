"""Biolink Model association classes as ``khg-relation-schema/1.0.0`` documents (DESIGN §2.5, §6.2).

Ported from R02's ``biolink_extract.py`` (reading the model with LinkML's ``SchemaView``; ``linkml-runtime`` is
imported lazily, only by ``extract``) and ``biolink_survey.py`` (``build``). One relation per concrete association
class; core ``subject`` and ``object`` (``predicate`` is the relation type, not a role); *formal* qualifiers are the
slots under Biolink's ``qualifier`` grouping slot; *formal + domain* adds the 25 class-specific truth-changing slots of
``DOMAIN_TRUTH_CHANGING`` (R02's reading of the slot descriptions); meta slots are not generated. Biolink has no
interval bounds, so no ``+time`` rows.

Namings: ``global`` (Biolink's own global slot names: ``subject``, ``object``, ``object_aspect_qualifier``) and
``relation-local`` (the control: ``<Class>:subject``, ``<Class>:object``, ``<Class>:<slot>``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

__all__ = ["extract", "schema_from_rows", "build", "schema_id", "QUALIFIER_SETS", "NAMINGS",
           "DOMAIN_TRUTH_CHANGING", "VERSION", "COMMIT", "RAW_FILES"]

VERSION = "v4.4.5"
COMMIT = "a4180f818e9722c493788c5ff1f047fde64f13a7"
RAW_FILES = ("raw/biolink-model.yaml", "raw/attributes.yaml", "raw/LICENSE")
QUALIFIER_SETS = ("formal", "formal-domain")
NAMINGS = ("global", "relation-local")

DOMAIN_TRUTH_CHANGING = frozenset({
    "allelic requirement", "associated environmental context", "catalyst qualifier", "clinical approval status",
    "end interbase coordinate", "expression site", "FDA adverse event level", "genome build", "has count",
    "has percentage", "has quotient", "has total", "has zygosity", "interacting molecules category",
    "max research phase", "number of cases", "phase", "phenotypic state", "quantifier qualifier",
    "reaction direction", "reaction side", "start interbase coordinate", "stoichiometry", "strand",
    "treatment outcome",
})
GROUPING = {"qualifier", "qualifiers"}
CORE = {"subject", "object"}


def _rng(slot: Any) -> Any:
    if slot.any_of:
        return sorted(a.range for a in slot.any_of if a.range)
    return slot.range


def extract(yaml_path: str | Path) -> list[dict]:
    """One row per association class (``association`` and its ``is_a`` descendants), as ``biolink_extract.py``
    writes them: class, abstract, ranges, ``qualifiers_formal``, ``domain_slots``, ``meta_slots``. Needs
    ``linkml-runtime`` (the ``survey`` extra)."""
    from linkml_runtime.utils.schemaview import SchemaView  # lazy: never at import time

    sv = SchemaView(str(yaml_path))
    classes = sv.all_classes()
    assoc = sorted(sv.class_descendants("association", reflexive=True))
    quals = set(sv.slot_descendants("qualifier", reflexive=False))
    base = set(sv.class_slots("association"))
    rows = []
    for c in assoc:
        cd = classes[c]
        induced = {s.name: s for s in sv.class_induced_slots(c)}
        names = set(sv.class_slots(c))
        rows.append({
            "class": c, "abstract": bool(cd.abstract), "mixin": bool(cd.mixin), "is_a": cd.is_a,
            "mixins": list(cd.mixins or []),
            "subject_range": _rng(induced["subject"]) if "subject" in induced else None,
            "object_range": _rng(induced["object"]) if "object" in induced else None,
            "qualifiers_formal": sorted(names & quals),
            "domain_slots": sorted(s for s in names - quals - base - GROUPING if s in DOMAIN_TRUTH_CHANGING),
            "meta_slots": sorted(s for s in names - quals - CORE - GROUPING - {"predicate"}
                                 if s not in DOMAIN_TRUTH_CHANGING),
        })
    return rows


def _snake(name: str) -> str:
    return name.replace(" ", "_")


def _camel(name: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in name.split(" "))


def schema_id(qualifiers: str, naming: str) -> str:
    return f"p6-biolink-{qualifiers}-{naming}"


def schema_from_rows(rows: Sequence[dict], qualifiers: str, naming: str) -> dict:
    """The schema document for the concrete classes of ``rows`` (pure; no linkml needed)."""
    if qualifiers not in QUALIFIER_SETS:
        raise ValueError(f"qualifiers must be one of {QUALIFIER_SETS}")
    if naming not in NAMINGS:
        raise ValueError(f"naming must be one of {NAMINGS}")
    local = naming == "relation-local"
    roles: dict[str, dict] = {}
    rels = []
    for row in sorted((r for r in rows if not r["abstract"]), key=lambda r: _camel(r["class"])):
        c = _camel(row["class"])
        s, o = (f"{c}:subject", f"{c}:object") if local else ("subject", "object")
        usages = [{"role": s, "slot": "core", "fillers": [{"entity": ["NamedThing"]}], "min": 1, "max": 1,
                   "direction": "tail"},
                  {"role": o, "slot": "core", "fillers": [{"entity": ["NamedThing"]}], "min": 1, "max": 1,
                   "direction": "head"}]
        extra = list(row["qualifiers_formal"])
        if qualifiers == "formal-domain":
            extra += list(row["domain_slots"])
        for q in extra:
            usages.append({"role": f"{c}:{_snake(q)}" if local else _snake(q), "slot": "qualifier",
                           "fillers": [{"literal": "string"}], "min": 0, "max": None})
        for u in usages:
            roles.setdefault(u["role"], {"id": u["role"]})
        rels.append({"id": c, "label": row["class"], "roles": usages, "primary": {"subject": s, "object": o}})
    return {"kind": "relation-schema", "format": "khg-relation-schema/1.0.0", "id": schema_id(qualifiers, naming),
            "version": "1.0.0",
            "label": f"Biolink Model {VERSION} (commit {COMMIT[:7]}) concrete association classes; "
                     f"qualifiers {qualifiers.replace('-', ' + ')}; naming {naming}",
            "entity_types": [{"id": "NamedThing"}], "roles": list(roles.values()), "relations": rels}


def build(yaml_path: str | Path, qualifiers: str, naming: str, *, rows: Sequence[dict] | None = None) -> dict:
    """``schema_from_rows(extract(yaml_path), ...)``; pass ``rows`` to reuse one extraction."""
    return schema_from_rows(rows if rows is not None else extract(yaml_path), qualifiers, naming)
