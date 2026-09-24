"""Wikidata property schemas as ``khg-relation-schema/1.0.0`` documents under wd-roles r1 (DESIGN §2.4, §2.5, §6.2).

Ported from R02's ``wd_schema_survey.py`` (``load``, ``tables``, ``build_schema``) with the r1 changes:

- rule 5: a self-qualifier is role ``P<id>:qualifier`` (the probe dropped it);
- rule 6: ``time`` is P580/P582 (a relation that allows or uses either gets the interval model, the missing bound
  added with min 0); **6a**: relations P580 and P582 get no time model, their P580/P582 qualifiers are ``qualifier``
  usages and the self one is ``P580:qualifier`` / ``P582:qualifier``; ``meta`` is the 24 listed properties plus
  P2241 and P7452; P1534 is the built-in ``khg:end_cause`` on interval relations and ``meta`` otherwise; everything
  else is ``qualifier``;
- rules 2-3: ``primary {subject: "subject", object: <P>}``;
- rule 8: the 57 properties that document or constrain properties are left out *as relations* (they stay qualifier
  roles where they are used as qualifiers).

Two namings: ``wd-roles-r1`` (headline) and ``relation-local`` (the control: the same slot rules, 6a included, and
every role scoped to its relation: ``P39:subject``, ``P39:value``, ``P39:P580``, ``P131:P131``).

Three tables: ``declared`` (non-deprecated allowed-qualifiers constraints, statements united, "no value" = none),
``observed-robust`` (>= 10 uses and >= 0.1 % of the property's main statements) and ``observed-all`` (>= 1 use). The
counts come from P3a's ``p3a-qualifier-usage/1`` file when given (scope ``dump``: ``all``; ``slice``: ``kept``), else
from SQID's ``qs`` over DeltaBot's main-statement counts (scope ``dump`` only). Unknown qualifier ids are dropped and
counted.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

__all__ = ["rules", "load", "Raw", "read_counts", "Counts", "tables", "build", "schema_id", "TABLES", "NAMINGS",
           "RAW_FILES", "NAMING_VERSION", "ROBUST_MIN_USES", "ROBUST_MIN_SHARE", "crosscheck_p3a"]

TABLES = ("declared", "observed-robust", "observed-all")
NAMINGS = ("wd-roles-r1", "relation-local")
NAMING_VERSION = "wd-roles r1"
ROBUST_MIN_USES = 10
ROBUST_MIN_SHARE = 0.001
P3A_FORMAT = "p3a-qualifier-usage/1"

#: the raw files a generation reads (checked against the manifest first)
RAW_FILES = ("raw/properties.srj.json", "raw/property_instance_of.srj.json", "raw/allowed_qualifiers.srj.json",
             "raw/required_qualifiers.srj.json", "raw/sqid-properties.json", "raw/usage_main_statements.wikitext")

DATATYPE = {  # Wikibase datatype -> khg filler; everything else is a string
    "WikibaseItem": {"entity": ["wd:Item"]}, "WikibaseProperty": {"entity": ["wd:Property"]},
    "WikibaseLexeme": {"entity": ["wd:Lexeme"]}, "WikibaseForm": {"entity": ["wd:Form"]},
    "WikibaseSense": {"entity": ["wd:Sense"]}, "WikibaseEntitySchema": {"entity": ["wd:EntitySchema"]},
    "Time": {"literal": "time"}, "Quantity": {"literal": "quantity"}, "Monolingualtext": {"literal": "lang_string"},
    "Url": {"literal": "iri"}, "GlobeCoordinate": {"literal": "geo"},
}
ENTITY_TYPES = ["wd:Item", "wd:Property", "wd:Lexeme", "wd:Form", "wd:Sense", "wd:EntitySchema"]


def rules() -> dict:
    """The r1 rules as packaged (``khg_width/data/wd-roles-r1.json``)."""
    return json.loads(resources.files("khg_width").joinpath("data/wd-roles-r1.json").read_text(encoding="utf-8"))


def _pid(u: str) -> str:
    return u.rsplit("/", 1)[-1]


def _pnum(p: str) -> tuple[int, str]:
    m = re.match(r"P(\d+)$", p)
    return (int(m.group(1)), p) if m else (10**12, p)


@dataclass
class Raw:
    """The parsed raw files: properties (datatype, label), classes, constraints, SQID qualifier counts and DeltaBot
    main-statement counts."""

    props: dict
    inst: dict
    allowed: dict
    novalue: set
    required: dict
    observed: dict
    main_uses: dict
    allowed_ranks: dict = field(default_factory=dict)


def _rows(raw: Path, name: str) -> list[dict]:
    return json.loads((raw / f"{name}.srj.json").read_text(encoding="utf-8"))["results"]["bindings"]


def _switch_template(raw: Path, name: str) -> dict[str, int]:
    text = (raw / f"{name}.wikitext").read_text(encoding="utf-8")
    return {f"P{m.group(1)}": int(m.group(2)) for m in re.finditer(r"^\|(\d+)=(\d+)\s*$", text, re.M)}


def load(raw_dir: str | Path) -> Raw:
    """Read the raw files of ``datasets/knowledge-bases/wikidata-property-schemas/raw/``."""
    raw = Path(raw_dir)
    props = {_pid(r["p"]["value"]): {"datatype": r["type"]["value"].rsplit("#", 1)[-1],
                                     "label": r.get("label", {}).get("value")} for r in _rows(raw, "properties")}
    inst: dict[str, set] = defaultdict(set)
    for r in _rows(raw, "property_instance_of"):
        inst[_pid(r["p"]["value"])].add(_pid(r["class"]["value"]))

    def constraint(name: str) -> tuple[dict, Counter]:
        out: dict[str, set] = defaultdict(set)
        ranks: Counter = Counter()
        for r in _rows(raw, name):
            rank = r["rank"]["value"].rsplit("#", 1)[-1]
            ranks[rank] += 1
            if rank == "DeprecatedRank":
                continue
            p = _pid(r["p"]["value"])
            out[p]  # a statement with only "no value" still declares the constraint (no qualifiers allowed)
            if "q" in r:
                out[p].add(_pid(r["q"]["value"]))
        return dict(out), ranks

    allowed, ranks = constraint("allowed_qualifiers")
    novalue = {_pid(r["p"]["value"]) for r in _rows(raw, "allowed_qualifiers")
               if "novalue" in r and not r["rank"]["value"].endswith("DeprecatedRank")}
    required, _ = constraint("required_qualifiers")
    sqid = json.loads((raw / "sqid-properties.json").read_text(encoding="utf-8"))
    observed = {f"P{k}": {f"P{q}": int(n) for q, n in v.get("qs", {}).items()} for k, v in sqid.items()}
    return Raw(props=props, inst=dict(inst), allowed=allowed, novalue=novalue, required=required, observed=observed,
               main_uses=_switch_template(raw, "usage_main_statements"), allowed_ranks=dict(ranks))


# ------------------------------------------------------------------------------------------------ P3a counts
@dataclass
class Counts:
    """P3a's counts for one scope: per relation, main statements and statements per qualifier property."""

    scope: str
    date: str | None
    relations: dict  # relation -> {"statements": int, "qualifiers": {qualifier property: statements}}
    source: str
    raw: dict = field(default_factory=dict)


#: the per-relation fields P3a may add beside ``statements`` and ``qualifiers`` (tolerated; ``time_model`` and each
#: qualifier's ``slot`` are cross-checked)
P3A_RELATION_EXTRAS = ("time_model", "left_out_6b", "rank_reason_mismatch", "self_qualified", "arity")


def _p3a_relations(section: Any, where: str) -> Mapping:
    """``section["relations"]``, the relations of ``all`` or ``kept``."""
    if not isinstance(section, Mapping):
        raise ValueError(f"{where} is not an object")
    rels = section.get("relations")
    if not isinstance(rels, Mapping):
        raise ValueError(f"{where} has no relations object")
    return rels


def _p3a_qualifier(role: str) -> str:
    """The qualifier property of an r1 role id: ``P131:qualifier`` -> P131 (the self-qualifier), ``khg:end_cause``
    -> P1534, ``P580`` -> P580."""
    if role.endswith(":qualifier"):
        return role.split(":", 1)[0]
    if role == "khg:end_cause":
        return "P1534"
    return role


def _p3a_date(dump: Any) -> str:
    """``"20260922"`` -> ``"2026-09-22"``."""
    if not (isinstance(dump, str) and re.fullmatch(r"\d{8}", dump)):
        raise ValueError(f"dump must be the dump date as YYYYMMDD, got {dump!r}")
    return f"{dump[:4]}-{dump[4:6]}-{dump[6:]}"


def read_counts(data: Mapping[str, Any] | str | Path, *, scope: str = "dump") -> Counts:
    """Read P3a's ``p3a-qualifier-usage/1`` file (or its parsed content), as the P3a session specified it on
    2026-09-24 (ruling Q9)::

        {"dump": "20260922", "naming": "wd-roles r1",
         "all":  {"relations": {P: rel, ...}, "out_of_scope_relations": {P: rel, ...}},
         "kept": {"relations": {P: rel, ...}, ...},
         "out_of_scope": [P, ...]}
        rel = {"statements": n, "qualifiers": {role: {"statements": n, "snaks": m[, "slot": s]}, ...}
               [, "time_model", "left_out_6b", "rank_reason_mismatch", "self_qualified", "arity"]}

    Scope ``dump`` reads ``all.relations`` (every entity of the dump), scope ``slice`` reads ``kept.relations``
    (items with an English Wikipedia article). Roles are r1 ids: ``P<id>:qualifier`` is the self-qualifier (never
    merged with the main-value role, which is not a qualifier). A ``format`` key, when present, must be
    ``p3a-qualifier-usage/1``; ``naming`` must be ``wd-roles r1`` (else the file is refused). The optional
    per-relation extras are tolerated; ``out_of_scope_relations`` are not relations of any table."""
    if not isinstance(data, Mapping):
        data = json.loads(Path(data).read_text(encoding="utf-8"))
    if "format" in data and data["format"] != P3A_FORMAT:
        raise ValueError(f"not a {P3A_FORMAT} file (format {data.get('format')!r})")
    if data.get("naming") != NAMING_VERSION:
        raise ValueError(f"the counts use naming {data.get('naming')!r}, not {NAMING_VERSION!r}; refused")
    if scope not in ("dump", "slice"):
        raise ValueError("scope must be dump or slice")
    date = _p3a_date(data.get("dump"))
    section = "all" if scope == "dump" else "kept"
    rels = _p3a_relations(data.get(section), section)
    out: dict[str, dict] = {}
    for p, r in rels.items():
        if not isinstance(r, Mapping) or not isinstance(r.get("statements"), int):
            raise ValueError(f"{section}.relations.{p} has no integer statements count")
        qs: dict[str, int] = {}
        for role, c in (r.get("qualifiers") or {}).items():
            if not isinstance(c, Mapping) or not isinstance(c.get("statements"), int):
                raise ValueError(f"{section}.relations.{p}.qualifiers.{role} has no integer statements count")
            if role == p:
                raise ValueError(f"{section}.relations.{p}: qualifier role {role} is the main-value role (rule 5 "
                                 f"names the self-qualifier {p}:qualifier)")
            q = _p3a_qualifier(role)
            qs[q] = qs.get(q, 0) + c["statements"]
        out[p] = {"statements": r["statements"], "qualifiers": qs}
    return Counts(scope=scope, date=date, relations=out, source="p3a", raw=dict(data))


def crosscheck_p3a(counts: Counts, raw: Raw) -> dict:
    """P3a's optional ``time_model`` and per-qualifier ``slot`` fields, its ``out_of_scope`` list and the ids of
    ``all.out_of_scope_relations`` against P6's own r1 classification (DESIGN §2.5)."""
    r1 = rules()
    ex = excluded(raw)
    mism: list[dict] = []
    part = counts.raw.get("all") if counts.scope == "dump" else counts.raw.get("kept")
    rels = part.get("relations", {}) if isinstance(part, Mapping) else {}
    for p, rec in sorted(rels.items(), key=lambda x: _pnum(x[0])):
        if not isinstance(rec, Mapping):
            continue
        quals = set(counts.relations.get(p, {}).get("qualifiers", {}))
        interval = p not in r1["no_time_model_relations"] and bool(quals & set(r1["time_bounds"].values()))
        tm = rec.get("time_model")
        tm_model = tm.get("model") if isinstance(tm, Mapping) else tm
        if "time_model" in rec and (tm_model == "interval") != interval:
            mism.append({"relation": p, "field": "time_model", "p3a": tm, "p6": "interval" if interval else None})
        for role, c in (rec.get("qualifiers") or {}).items():
            if not isinstance(c, Mapping) or "slot" not in c:
                continue
            q = _p3a_qualifier(role)
            mine = _slot(q, p, interval, r1)
            if role == "khg:end_cause" and mine is None:
                continue  # the built-in end cause: P3a's slot for it is its own
            if mine != c["slot"]:
                mism.append({"relation": p, "role": role, "field": "slot", "p3a": c["slot"], "p6": mine})
    oos = set(counts.raw.get("out_of_scope") or [])
    if oos != ex:
        mism.append({"field": "out_of_scope", "only_p3a": sorted(oos - ex, key=_pnum),
                     "only_p6": sorted(ex - oos, key=_pnum)})
    all_part = counts.raw.get("all")
    oos_rel = set((all_part.get("out_of_scope_relations") or {}) if isinstance(all_part, Mapping) else {})
    if oos_rel - ex:
        mism.append({"field": "out_of_scope_relations", "not_excluded_by_p6": sorted(oos_rel - ex, key=_pnum)})
    return {"naming": NAMING_VERSION, "scope": counts.scope, "dump": counts.date, "mismatches": mism}


# ------------------------------------------------------------------------------------------------ tables
def excluded(raw: Raw) -> set[str]:
    """Rule 8: properties that document or constrain properties."""
    classes = set(rules()["exclude_relation_classes"])
    return {p for p in raw.props if raw.inst.get(p, set()) & classes}


def tables(raw: Raw, *, counts: Counts | None = None) -> tuple[dict[str, dict[str, list[str]]], dict]:
    """``{table: {relation: [qualifier properties]}}`` and notes (the count source, dropped unknown ids)."""
    ex = excluded(raw)
    rel_props = {p for p in raw.props if p not in ex}
    notes: Counter = Counter()
    declared: dict[str, list[str]] = {}
    for p, qs in raw.allowed.items():
        if p in rel_props:
            known = sorted((q for q in qs if q in raw.props), key=_pnum)
            notes["declared_unknown_qualifier_ids"] += len(qs) - len(known)
            declared[p] = known
    obs_all: dict[str, list[str]] = {}
    obs_robust: dict[str, list[str]] = {}
    if counts is None:
        uses_of = raw.observed
        main = raw.main_uses
    else:
        uses_of = {p: r["qualifiers"] for p, r in counts.relations.items()}
        main = {p: r["statements"] for p, r in counts.relations.items()}
    for p in sorted(rel_props, key=_pnum):
        n_main = main.get(p, 0)
        if n_main <= 0:
            continue
        qs = uses_of.get(p, {})
        known = {q: n for q, n in qs.items() if q in raw.props}
        notes["observed_unknown_qualifier_ids"] += len(qs) - len(known)
        obs_all[p] = sorted((q for q, n in known.items() if n >= 1), key=_pnum)
        obs_robust[p] = sorted((q for q, n in known.items()
                                if n >= ROBUST_MIN_USES and n >= ROBUST_MIN_SHARE * n_main), key=_pnum)
    return {"declared": declared, "observed-robust": obs_robust, "observed-all": obs_all}, dict(notes)


def _slot(q: str, p: str, interval: bool, r1: dict) -> str | None:
    """The slot of qualifier q on relation p under r1 (None: the built-in khg:end_cause, not declared)."""
    meta = set(r1["meta"]) | set(r1["meta_rank_reasons"])
    if q in meta:
        return "meta"
    if q == r1["end_cause"]["property"]:
        return None if interval else "meta"
    if interval and q in r1["time_bounds"].values():
        return "time"
    return "qualifier"


def schema_id(table: str, naming: str, *, slice_scope: bool = False) -> str:
    return f"p6-wikidata-{table}{'-slice' if slice_scope else ''}-{naming}"


def build(raw_dir: str | Path | None, table: str, naming: str, counts: Counts | None = None, *,
          raw: Raw | None = None, date_label: str = "constraints of 2026-09-24 (WDQS)") -> tuple[dict, dict]:
    """``(document, notes)`` for one table and naming. ``raw`` (from ``load``) avoids re-reading the raw files."""
    if table not in TABLES:
        raise ValueError(f"table must be one of {TABLES}")
    if naming not in NAMINGS:
        raise ValueError(f"naming must be one of {NAMINGS}")
    if counts is not None and table == "declared":
        raise ValueError("the declared table does not depend on counts")
    if raw is None:
        raw = load(raw_dir)  # type: ignore[arg-type]
    r1 = rules()
    tbls, tnotes = tables(raw, counts=counts)
    table_rows = tbls[table]
    local = naming == "relation-local"
    subj, (t_start, t_end) = r1["subject_role"], (r1["time_bounds"]["start"], r1["time_bounds"]["end"])
    no_time = set(r1["no_time_model_relations"])
    props = raw.props
    roles: dict[str, dict] = {}
    relations: list[dict] = []
    notes: Counter = Counter(tnotes)

    def role(rid: str, label: str | None = None, wd: str | None = None) -> str:
        if rid not in roles:
            r: dict[str, Any] = {"id": rid}
            if label:
                r["label"] = label
            if wd:
                r["mappings"] = {"wikidata": wd}
            roles[rid] = r
        return rid

    for p in sorted(table_rows, key=_pnum):
        quals = [q for q in table_rows[p] if q in props]
        dt = props.get(p, {}).get("datatype", "String")
        label = props.get(p, {}).get("label")
        s_id = f"{p}:subject" if local else subj
        v_id = f"{p}:value" if local else p
        interval = p not in no_time and any(q in (t_start, t_end) for q in quals)
        if interval:
            added = [t for t in (t_start, t_end) if t not in quals]
            notes["time_bound_added"] += len(added)
            quals = sorted(set(quals) | {t_start, t_end}, key=_pnum)
        if p in no_time and any(q in (t_start, t_end) for q in quals):
            notes["rule_6a_relations"] += 1
        usages = [
            {"role": role(s_id), "slot": "core", "fillers": [{"entity": ["wd:Item"]}], "min": 1, "max": 1,
             "direction": "tail"},
            {"role": role(v_id, None if local else label, None if local else p), "slot": "core",
             "fillers": [DATATYPE.get(dt, {"literal": "string"})], "min": 1, "max": 1, "direction": "head"},
        ]
        req = raw.required.get(p, set())
        qroles: dict[str, str] = {}
        for q in quals:
            slot = _slot(q, p, interval, r1)
            if slot is None:
                notes["end_cause_as_builtin"] += 1
                continue
            if local:
                rid = f"{p}:{q}"
            elif q == p:
                rid = f"{p}{r1['self_qualifier_suffix']}"
                notes["self_qualifier_roles"] += 1
            else:
                rid = q
            qroles[q] = rid
            qlabel = props[q].get("label")
            if rid.endswith(":qualifier") and qlabel:
                qlabel = f"{qlabel} (as a qualifier of itself)"
            u = {"role": role(rid, None if local else qlabel, None if local else q), "slot": slot,
                 "fillers": [{"literal": "time"}] if slot == "time" else
                 [DATATYPE.get(props[q]["datatype"], {"literal": "string"})],
                 "min": 1 if (q in req and slot != "time") else 0, "max": 1 if slot == "time" else None}
            usages.append(u)
            if q in req:
                notes["required_qualifier_usages"] += 1
            notes[f"slot_{slot}"] += 1
        rel: dict[str, Any] = {"id": p, "mappings": {"wikidata": p}, "roles": usages,
                               "primary": {"subject": s_id, "object": v_id}}
        if label:
            rel["label"] = label
        if interval:
            rel["time"] = {"model": "interval", "start": qroles[t_start], "end": qroles[t_end]}
        relations.append(rel)
    source = "P3a" if counts is not None else "SQID"
    doc = {"kind": "relation-schema", "format": "khg-relation-schema/1.0.0",
           "id": schema_id(table, naming, slice_scope=counts is not None and counts.scope == "slice"),
           "version": "1.0.0",
           "label": f"Wikidata property schemas, table {table}, naming "
                    f"{'relation-local (control, wd-roles r1 slot rules)' if local else NAMING_VERSION}; "
                    f"{date_label}" + ("" if table == "declared" else
                                       f"; counts {source}" + (f" {counts.date}" if counts and counts.date else "")),
           "entity_types": [{"id": t} for t in ENTITY_TYPES], "roles": list(roles.values()),
           "relations": relations}
    notes["relations"] = len(relations)
    notes["roles"] = len(roles)
    notes["excluded_relations"] = len(excluded(raw))
    return doc, dict(notes)
