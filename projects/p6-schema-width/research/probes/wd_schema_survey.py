"""P6 probe: Wikidata property schemas as khg-relation-schema/1.0.0 documents, under several role namings.

Reads the raw files fetched by wd_fetch.py (datasets/knowledge-bases/wikidata-property-schemas/raw/) and

1. builds per-property tables: datatype, allowed qualifiers (Q21510851/P2306), required qualifiers (Q21510856),
   subject-type (Q21503250) and value-type (Q21510865) classes (P2308) with their relation (P2309), usage counts
   (DeltaBot templates) and observed qualifier usage (SQID, from the 2026-08-10 dump);
2. classes every qualifier as `time` (P580/P582: a relation allowing either gets the interval model with both),
   `meta` (the rule and list below) or `qualifier`;
3. turns each property into one relation of a khg-relation-schema/1.0.0 document under each role-naming variant,
   calls khg_contracts.schema.schema_hypergraph, and measures the hypergraph (alpha-acyclicity by
   khg_contracts.schema.is_alpha_acyclic, size, components). The indexed GYO in hg_measure.py is run as an
   independent cross-check and must return the same residue;
4. writes out/wd-survey.json and out/wd-survey.md next to this file, and the schema documents of the
   recommended variant to datasets/.../processed/ (gitignored), checked with khg_contracts.schema.check_schema.

Run from the repository root with the khg-contracts venv:
    python projects/p6-schema-width/research/probes/wd_schema_survey.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import hg_measure as hm  # noqa: E402
from khg_contracts.schema import check_schema, is_alpha_acyclic, schema_hypergraph  # noqa: E402

DS = ROOT / "datasets" / "knowledge-bases" / "wikidata-property-schemas"
RAW = DS / "raw"
OUT = HERE / "out"
REF_LIMIT = 10**9  # run the reference GYO on every hypergraph (about 1 s at 13,608 hyperedges)

# ---------------------------------------------------------------------------------------------- classification
TIME_BOUNDS = ("P580", "P582")  # start time, end time: the interval model's bounds

# Statement metadata: the qualifier describes the statement as a record (rank, provenance, wording in a source,
# support or dispute, an editorial note) and cannot change what the statement says about the world. P2 DESIGN §2.4
# keeps epistemic modifiers (P5102 nature of statement, P1480 sourcing circumstances) as qualifiers and maps P1534
# to the built-in meta usage khg:end_cause.
META = {
    # rank and special-value bookkeeping (Help:Ranking)
    "P2241": "rank", "P7452": "rank", "P8327": "rank", "P13589": "rank",
    # how the source worded the subject or value
    "P1810": "wording", "P14457": "wording", "P1932": "wording", "P4970": "wording",
    # inline citation: source properties used in the qualifier field (Help:Sources)
    "P813": "citation", "P854": "citation", "P248": "citation", "P1065": "citation", "P2960": "citation",
    "P143": "citation", "P4656": "citation", "P887": "citation", "P3452": "citation", "P1683": "citation",
    "P5017": "citation",
    # support, dispute, the item describing the statement
    "P3680": "support", "P1310": "support", "P805": "support",
    # editorial and display notes
    "P2916": "note", "P6607": "note", "P9570": "note", "P7528": "note",
    # lifecycle: P2 maps it to khg:end_cause
    "P1534": "lifecycle",
}

# Properties left out as relations: they document or constrain other properties (instances of Q19820110
# "Wikidata property for documentation of properties" or Q21504947 "Wikidata property to indicate a constraint"),
# or take arbitrary properties as qualifiers to state membership criteria (Q64846109 "Wikidata property using many
# other properties as qualifiers": P1855 property example, P360 is a list of, P4224 category contains, ...).
EXCLUDE_CLASSES = {"Q19820110", "Q21504947", "Q64846109"}

DATATYPE = {  # Wikibase datatype -> khg filler
    "WikibaseItem": {"entity": ["wd:Item"]}, "WikibaseProperty": {"entity": ["wd:Property"]},
    "WikibaseLexeme": {"entity": ["wd:Lexeme"]}, "WikibaseForm": {"entity": ["wd:Form"]},
    "WikibaseSense": {"entity": ["wd:Sense"]}, "WikibaseEntitySchema": {"entity": ["wd:EntitySchema"]},
    "Time": {"literal": "time"}, "Quantity": {"literal": "quantity"}, "Monolingualtext": {"literal": "lang_string"},
    "Url": {"literal": "iri"}, "GlobeCoordinate": {"literal": "geo"},
}  # everything else (ExternalId, String, CommonsMedia, Math, GeoShape, TabularData, MusicalNotation) -> string
ENTITY_TYPES = ["wd:Item", "wd:Property", "wd:Lexeme", "wd:Form", "wd:Sense", "wd:EntitySchema"]


def pid(u: str) -> str:
    return u.rsplit("/", 1)[-1]


def rows(name: str) -> list[dict]:
    return json.loads((RAW / f"{name}.srj.json").read_text())["results"]["bindings"]


def switch_template(name: str) -> dict[str, int]:
    text = (RAW / f"{name}.wikitext").read_text()
    return {f"P{m.group(1)}": int(m.group(2)) for m in re.finditer(r"^\|(\d+)=(\d+)\s*$", text, re.M)}


def load() -> dict:
    props = {pid(r["p"]["value"]): {"datatype": r["type"]["value"].rsplit("#", 1)[-1],
                                    "label": r.get("label", {}).get("value")} for r in rows("properties")}
    inst = defaultdict(set)
    for r in rows("property_instance_of"):
        inst[pid(r["p"]["value"])].add(pid(r["class"]["value"]))

    def constraint(name: str, param: str) -> tuple[dict, dict, Counter]:
        out: dict[str, set] = defaultdict(set)
        status: dict[str, set] = defaultdict(set)
        ranks = Counter()
        for r in rows(name):
            rank = r["rank"]["value"].rsplit("#", 1)[-1]
            ranks[rank] += 1
            if rank == "DeprecatedRank":
                continue
            p = pid(r["p"]["value"])
            out[p]
            if param in r:
                out[p].add(pid(r[param]["value"]))
            if "status" in r:
                status[p].add(pid(r["status"]["value"]))
        return dict(out), dict(status), ranks

    allowed, allowed_status, allowed_ranks = constraint("allowed_qualifiers", "q")
    novalue = {pid(r["p"]["value"]) for r in rows("allowed_qualifiers") if "novalue" in r
               and not r["rank"]["value"].endswith("DeprecatedRank")}
    required, _, _ = constraint("required_qualifiers", "q")

    def types(name: str) -> dict:
        out: dict[str, dict] = defaultdict(lambda: {"classes": set(), "rel": set()})
        for r in rows(name):
            if r["rank"]["value"].endswith("DeprecatedRank"):
                continue
            p = pid(r["p"]["value"])
            if "class" in r:
                out[p]["classes"].add(pid(r["class"]["value"]))
            if "rel" in r:
                out[p]["rel"].add(pid(r["rel"]["value"]))
        return dict(out)

    qkinds = defaultdict(set)
    for r in rows("qualifier_classes"):
        qkinds[pid(r["p"]["value"])].add(pid(r["kind"]["value"]))
    sqid = json.loads((RAW / "sqid-properties.json").read_text())
    observed = {f"P{k}": {f"P{q}": n for q, n in v.get("qs", {}).items()} for k, v in sqid.items()}
    return {
        "props": props, "inst": dict(inst), "allowed": allowed, "allowed_status": allowed_status,
        "allowed_ranks": allowed_ranks, "novalue": novalue, "required": required,
        "stype": types("subject_type_constraints"), "vtype": types("value_type_constraints"),
        "qkinds": dict(qkinds), "observed": observed,
        "main_uses": switch_template("usage_main_statements"),
        "qual_uses": switch_template("usage_as_qualifier"),
        "ref_uses": switch_template("usage_in_references"),
    }


# ---------------------------------------------------------------------------------------------- namings
def main_roles(variant: str, p: str, D: dict) -> tuple[str, str]:
    """(subject role, value role) of property p under a naming variant."""
    if variant == "a_generic":
        return "subject", "value"
    if variant == "b_local":
        return f"{p}:subject", f"{p}:value"
    if variant == "c_typed":
        st = D["stype"].get(p, {}).get("classes")
        vt = D["vtype"].get(p, {}).get("classes") if D["props"][p]["datatype"] == "WikibaseItem" else None
        s = "subject:" + "|".join(sorted(st)) if st else f"{p}:subject"
        v = "value:" + "|".join(sorted(vt)) if vt else f"{p}:value"
        return s, v
    if variant == "d_property":
        return "subject", p
    if variant == "e_relation_local":
        return f"{p}:subject", f"{p}:value"
    raise ValueError(variant)


VARIANTS = ["a_generic", "b_local", "c_typed", "d_property", "e_relation_local"]


def build_schema(variant: str, table: dict[str, list[str]], D: dict, *, classify: bool = True) -> tuple[dict, dict]:
    """A khg-relation-schema/1.0.0 document with one relation per property in `table` (property -> qualifiers).
    classify=False is the naive import: every qualifier is a `qualifier` usage (no time model, no meta).
    Returns (document, notes)."""
    props = D["props"]
    roles: dict[str, dict] = {}
    relations = []
    notes = Counter()

    def role(rid: str, label: str | None = None, wd: str | None = None) -> str:
        if rid not in roles:
            r = {"id": rid}
            if label:
                r["label"] = label
            if wd:
                r["mappings"] = {"wikidata": wd}
            roles[rid] = r
        return rid

    for p, quals in table.items():
        dt = props.get(p, {}).get("datatype", "String")
        s_id, v_id = main_roles(variant, p, D)
        local = variant == "e_relation_local"
        usages = [
            {"role": role(s_id), "slot": "core", "fillers": [{"entity": ["wd:Item"]}], "min": 1, "max": 1,
             "direction": "tail"},
            {"role": role(v_id, props.get(p, {}).get("label") if v_id == p else None, p if v_id == p else None),
             "slot": "core", "fillers": [DATATYPE.get(dt, {"literal": "string"})], "min": 1, "max": 1,
             "direction": "head"},
        ]
        used = {s_id, v_id}
        qs = sorted(q for q in quals if q in props)
        notes["unknown_qualifier_ids"] += len(quals) - len(qs)
        # P580/P582 are always the interval bounds: a relation that allows (or uses) either gets the interval
        # model with both as time usages (the one not listed is added with min 0)
        interval = classify and any(t in qs for t in TIME_BOUNDS)
        if interval:
            added = [t for t in TIME_BOUNDS if t not in qs]
            notes["time_bound_added"] += len(added)
            qs = sorted(set(qs) | set(TIME_BOUNDS))
        req = D["required"].get(p, set())
        for q in qs:
            if not classify:
                slot = "qualifier"
            elif q in META:
                slot = "meta"
                if q == "P1534" and interval:
                    notes["end_cause_as_builtin"] += 1  # khg:end_cause is built in for interval relations
                    continue
            elif interval and q in TIME_BOUNDS:
                slot = "time"
            else:
                slot = "qualifier"
            rid = f"{p}:{q}" if local else q
            if rid in used:  # the property allowed as its own qualifier while it is also the value role
                notes["self_qualifier_dropped"] += 1
                continue
            used.add(rid)
            qdt = props[q]["datatype"]
            u = {"role": role(rid, props[q]["label"], q), "slot": slot,
                 "fillers": [{"literal": "time"}] if slot == "time" else [DATATYPE.get(qdt, {"literal": "string"})],
                 "min": 1 if (q in req and slot != "time") else 0, "max": 1 if slot == "time" else None}
            usages.append(u)
        rel = {"id": p, "mappings": {"wikidata": p}, "roles": usages}
        if props.get(p, {}).get("label"):
            rel["label"] = props[p]["label"]
        if interval:
            rel["time"] = {"model": "interval", "start": f"{p}:P580" if local else "P580",
                           "end": f"{p}:P582" if local else "P582"}
        relations.append(rel)
    doc = {"kind": "relation-schema", "format": "khg-relation-schema/1.0.0",
           "id": f"wd-{variant}", "version": "0.1.0",
           "label": f"Wikidata property schemas, naming {variant}",
           "entity_types": [{"id": t} for t in ENTITY_TYPES],
           "roles": list(roles.values()), "relations": relations}
    return doc, dict(notes)


def measure(doc: dict, slots: tuple[str, ...]) -> dict:
    hg = schema_hypergraph(doc, slots=slots)
    t0 = time.time()
    ok, residue = hm.alpha(hg)
    ref = None
    if len(hg["hyperedges"]) <= REF_LIMIT:
        ref_ok, ref_res = is_alpha_acyclic(hg)
        ref = ref_ok == ok and sorted(map(sorted, ref_res)) == sorted(map(sorted, residue))
        if not ref:
            raise AssertionError("indexed GYO disagrees with khg_contracts.is_alpha_acyclic")
    st = hm.stats(hg)
    res_vertices = set().union(*residue) if residue else set()
    return {**st, "alpha_acyclic": ok, "residue_edges": len(residue), "residue_vertices": len(res_vertices),
            "reference_checked": ref, "seconds": round(time.time() - t0, 2)}


# ---------------------------------------------------------------------------------------------- tables
def excluded(D: dict) -> set[str]:
    return {p for p in D["props"] if D["inst"].get(p, set()) & EXCLUDE_CLASSES}


def tables(D: dict) -> dict[str, dict[str, list[str]]]:
    props = {p: v for p, v in D["props"].items() if p not in excluded(D)}
    declared = {p: sorted(q) for p, q in D["allowed"].items() if p in props}
    main = D["main_uses"]
    obs_all, obs_robust = {}, {}
    for p in props:
        qs = D["observed"].get(p, {})
        obs_all[p] = sorted(q for q, n in qs.items() if n >= 1 and q in props)
        n_main = main.get(p, 0)
        obs_robust[p] = sorted(q for q, n in qs.items() if q in props and n >= 10 and n >= 0.001 * n_main)
    return {
        "declared": declared,  # properties with a non-deprecated allowed-qualifiers constraint
        "observed_all": {p: q for p, q in obs_all.items() if main.get(p, 0) > 0},
        "observed_robust": {p: q for p, q in obs_robust.items() if main.get(p, 0) > 0},
    }


def describe(D: dict, T: dict) -> dict:
    props = D["props"]
    allowed = T["declared"]
    sizes = [len(v) for v in allowed.values()]
    bins = Counter()
    for n in sizes:
        bins["0" if n == 0 else "1" if n == 1 else "2-3" if n <= 3 else "4-7" if n <= 7 else "8-15" if n <= 15
             else "16-31" if n <= 31 else "32-63" if n <= 63 else "64+"] += 1
    qc = Counter(q for v in allowed.values() for q in v)
    main = D["main_uses"]
    tot_main = sum(main.get(p, 0) for p in props)
    cov = sum(main.get(p, 0) for p in allowed)
    top = sorted(props, key=lambda p: -main.get(p, 0))
    top100 = top[:100]
    top1000 = top[:1000]
    dt_all = Counter(props[p]["datatype"] for p in props)
    dt_aq = Counter(props[p]["datatype"] for p in allowed)
    req = {p: q for p, q in D["required"].items() if p in props}
    stc = {p for p, v in D["stype"].items() if v["classes"]}
    vtc = {p for p, v in D["vtype"].items() if v["classes"]}
    item_props = {p for p in props if props[p]["datatype"] == "WikibaseItem"}
    rel_counter = Counter(r for v in D["stype"].values() for r in v["rel"])
    rel_counter_v = Counter(r for v in D["vtype"].values() for r in v["rel"])
    st_classes = Counter(c for v in D["stype"].values() for c in v["classes"])
    vt_classes = Counter(c for v in D["vtype"].values() for c in v["classes"])
    n_st_classes = Counter(len(v["classes"]) for v in D["stype"].values())
    obs = T["observed_all"]
    with_q = [p for p, q in obs.items() if q]
    ex = excluded(D)
    return {
        "properties": len(props),
        "excluded_as_relations": len(ex),
        "excluded_with_allowed_qualifiers": len(ex & set(D["allowed"])),
        "excluded_examples": sorted(ex, key=lambda p: -len(D["observed"].get(p, {})))[:8],
        "datatypes": dt_all.most_common(),
        "with_allowed_qualifiers": len(allowed),
        "allowed_qualifiers_novalue_only": sum(1 for p in D["novalue"] if not allowed.get(p)),
        "allowed_constraint_statement_ranks": dict(D["allowed_ranks"]),
        "allowed_constraint_status": Counter(s for v in D["allowed_status"].values() for s in v).most_common(),
        "with_allowed_qualifiers_by_datatype": dt_aq.most_common(),
        "allowed_list_size": {"mean": round(statistics.mean(sizes), 2), "median": statistics.median(sizes),
                              "max": max(sizes), "bins": dict(bins)},
        "largest_allowed_lists": [(p, props[p]["label"], len(allowed[p])) for p in
                                  sorted(allowed, key=lambda p: -len(allowed[p]))[:10]],
        "distinct_allowed_qualifiers": len(qc),
        "most_shared_allowed_qualifiers": [(q, props.get(q, {}).get("label"), n) for q, n in qc.most_common(30)],
        "main_statements_total": tot_main,
        "main_statements_covered_by_allowed": cov,
        "top100_by_use_with_allowed": sum(1 for p in top100 if p in allowed),
        "top1000_by_use_with_allowed": sum(1 for p in top1000 if p in allowed),
        "with_required_qualifiers": len(req),
        "required_qualifiers_most_common": [(q, props.get(q, {}).get("label"), n) for q, n in
                                            Counter(q for v in req.values() for q in v).most_common(10)],
        "with_subject_type": len(stc), "subject_type_rel": rel_counter.most_common(),
        "subject_type_classes_per_property": sorted(n_st_classes.items()),
        "subject_type_top_classes": st_classes.most_common(10),
        "item_properties": len(item_props), "item_properties_with_value_type": len(vtc & item_props),
        "value_type_rel": rel_counter_v.most_common(), "value_type_top_classes": vt_classes.most_common(10),
        "observed_properties_with_main_use": len(obs),
        "observed_properties_with_any_qualifier": len(with_q),
        "observed_distinct_qualifiers": len({q for v in obs.values() for q in v}),
        "observed_robust_distinct_qualifiers": len({q for v in T["observed_robust"].values() for q in v}),
        "meta_list": sorted(META),
    }


def compare(D: dict, T: dict, sample: list[str]) -> dict:
    """Declared versus observed qualifier sets."""
    props = D["props"]
    out = {}
    both = [p for p in T["declared"] if p in T["observed_all"]]
    jac = []
    extra_share = []
    for p in both:
        a, o = set(T["declared"][p]), set(T["observed_robust"].get(p, []))
        if a | o:
            jac.append(len(a & o) / len(a | o))
        qs = D["observed"].get(p, {})
        tot = sum(qs.values())
        if tot:
            extra_share.append(sum(n for q, n in qs.items() if q not in a) / tot)
    out["declared_with_usage"] = len(both)
    out["jaccard_declared_vs_robust_median"] = round(statistics.median(jac), 3) if jac else None
    out["share_of_qualifier_snaks_outside_allowed_median"] = round(statistics.median(extra_share), 4) if extra_share else None
    per = {}
    for p in sample:
        a = set(T["declared"].get(p, []))
        qs = D["observed"].get(p, {})
        tot = sum(qs.values())
        robust = set(T["observed_robust"].get(p, []))
        per[p] = {
            "label": props[p]["label"], "allowed": len(a), "observed_distinct": len(qs),
            "observed_robust": len(robust), "allowed_and_robust": len(a & robust),
            "allowed_never_used": len([q for q in a if q not in qs]),
            "robust_not_allowed": sorted(robust - a),
            "snaks_total": tot, "snaks_outside_allowed": sum(n for q, n in qs.items() if q not in a),
            "top_observed": sorted(qs.items(), key=lambda t: -t[1])[:12],
        }
    out["sample"] = per
    return out


def sparql_usage(D: dict, sample: list[str]) -> dict:
    """Live WDQS slices (wd_fetch.py: four slices of 20,000 statements per property, index order) next to the
    allowed list and SQID's dump counts. Counts statements carrying each qualifier."""
    out = {}
    for p in sample:
        g = RAW / f"usage_{p}_statements.srj.json"
        slices = sorted(RAW.glob(f"usage_{p}_slice*.srj.json"))
        if not slices:
            continue
        live: Counter = Counter()
        n_slice_statements = 0
        for f in slices:
            for r in json.loads(f.read_text())["results"]["bindings"]:
                live[pid(r["q"]["value"])] += int(r["statements"]["value"])
        n_slice_statements = 20000 * len(slices)
        n_st = int(json.loads(g.read_text())["results"]["bindings"][0]["statements"]["value"]) if g.exists() else None
        allowed = set(D["allowed"].get(p, []))
        dump = D["observed"].get(p, {})
        main = D["main_uses"].get(p)
        out[p] = {
            "label": D["props"][p]["label"], "statements_live": n_st, "slices": len(slices),
            "slice_statements": n_slice_statements, "allowed": len(allowed),
            "distinct_qualifiers_in_slices": len(live),
            "slice_qualifiers_not_allowed": sorted(q for q in live if q not in allowed),
            "slice_statements_with_not_allowed": sum(n for q, n in live.items() if q not in allowed),
            "allowed_seen_in_slices": len(allowed & set(live)),
            "share_in_slices_vs_dump": [(q, round(n / n_slice_statements, 4),
                                         round(dump.get(q, 0) / main, 4) if main else None)
                                        for q, n in live.most_common(8)],
            "meta_in_slices": sorted(q for q in live if q in META),
        }
    return out


def main() -> int:
    D = load()
    T = tables(D)
    OUT.mkdir(exist_ok=True)
    if "--usage-only" in sys.argv:
        path = OUT / "wd-survey.json"
        result = json.loads(path.read_text())
        result["sparql_usage"] = sparql_usage(D, ["P39", "P69", "P108", "P166", "P54"])
        path.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=list) + "\n")
        return 0
    result = {"describe": describe(D, T)}
    sample = ["P39", "P69", "P108", "P166", "P54"]
    result["declared_vs_observed"] = compare(D, T, sample)
    result["sparql_usage"] = sparql_usage(D, sample)
    # qualifier treatments: naive import (every qualifier a role), P2 slot classes with the time bounds, and P2's
    # default for P6 (core + qualifier: time bounds and meta left out)
    treatments = {"naive": (False, ("core", "qualifier")),
                  "core+qualifier+time": (True, ("core", "qualifier", "time")),
                  "core+qualifier": (True, ("core", "qualifier"))}
    runs = []
    for tname in ["declared", "observed_robust", "observed_all"]:
        for variant in VARIANTS:
            docs = {c: build_schema(variant, T[tname], D, classify=c) for c in (False, True)}
            for sname, (classify, slots) in treatments.items():
                doc, notes = docs[classify]
                m = measure(doc, slots)
                runs.append({"table": tname, "variant": variant, "treatment": sname, **m, "notes": notes})
                print(f"{tname:16} {variant:17} {sname:20} "
                      f"E={m['edges']:5} V={m['vertices']:5} maxE={m['max_edge']:3} comp={m['components']:5} "
                      f"alpha={m['alpha_acyclic']} residue={m['residue_edges']}/{m['residue_vertices']} "
                      f"ref={m['reference_checked']} {m['seconds']}s", file=sys.stderr)
            doc = docs[True][0]
            if variant == "d_property" and tname == "declared":
                proc = DS / "processed"
                proc.mkdir(exist_ok=True)
                path = proc / "wd-declared-d_property.relation-schema.json"
                path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                findings = check_schema(doc)
                result["schema_check_d_property_declared"] = {
                    "path": str(path.relative_to(ROOT)), "relations": len(doc["relations"]),
                    "roles": len(doc["roles"]), "errors": [f for f in findings if f["severity"] == "error"][:10],
                    "n_findings": len(findings)}
    result["runs"] = runs
    (OUT / "wd-survey.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=list) + "\n")
    lines = ["# Wikidata schema hypergraphs under role-naming variants (generated by wd_schema_survey.py)", "",
             "| table | naming | qualifier treatment | edges | vertices | max edge | components | largest comp. | "
             "alpha-acyclic | GYO residue (edges/vertices) | ref. checked |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        lines.append(f"| {r['table']} | {r['variant']} | {r['treatment']} | {r['edges']} | {r['vertices']} "
                     f"| {r['max_edge']} | {r['components']} | {r['largest_component_edges']} | {r['alpha_acyclic']} "
                     f"| {r['residue_edges']}/{r['residue_vertices']} | {r['reference_checked']} |")
    (OUT / "wd-survey.md").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
