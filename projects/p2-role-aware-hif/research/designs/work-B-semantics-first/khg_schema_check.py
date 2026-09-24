"""Semantic checks on relation-type schema documents (M* codes)."""
import re
BUILTIN_TYPES = {"Thing"}
DATATYPES = {"time", "quantity", "string", "lang_string", "boolean", "iri", "geo"}

def validate_schema_doc(sd):
    out = []
    err = lambda c, m: out.append((c, "violation", m))
    roles = {r["id"] for r in sd["roles"]}
    types = {t["id"] for t in sd.get("entity_types", [])} | BUILTIN_TYPES
    rel_ids = [r["id"] for r in sd["relations"]]
    for x in list(roles) + rel_ids + [t["id"] for t in sd.get("entity_types", [])]:
        if x.startswith("khg:"):
            err("KHG-M008", f"{x!r} uses the reserved khg: namespace")
    for t in sd.get("entity_types", []):
        for p in t.get("parents", []):
            if p not in types:
                err("KHG-M005", f"type {t['id']!r}: unknown parent {p!r}")
    for r in sd["relations"]:
        seen = set()
        for u in r["roles"]:
            if u["role"] in seen:
                err("KHG-M002", f"{r['id']}: role {u['role']!r} used twice")
            seen.add(u["role"])
            if u["role"] not in roles:
                err("KHG-M009", f"{r['id']}: role {u['role']!r} not in the role vocabulary")
            if u["max"] is not None and u["max"] < u["min"]:
                err("KHG-M010", f"{r['id']}.{u['role']}: max < min")
            for f in u["fillers"]:
                for t in f.get("entity", []):
                    if t not in types:
                        err("KHG-M005", f"{r['id']}.{u['role']}: unknown entity type {t!r}")
                for rr in f.get("fact", []):
                    if rr not in rel_ids:
                        err("KHG-M005", f"{r['id']}.{u['role']}: unknown relation {rr!r} in fact filler")
        usage = {u["role"]: u for u in r["roles"]}
        k = r.get("key")
        if k:
            for kr in k["roles"]:
                if kr not in usage:
                    err("KHG-M003", f"{r['id']}: key role {kr!r} is not a role of the relation")
                elif usage[kr]["slot"] in ("time", "meta"):
                    err("KHG-M003", f"{r['id']}: key role {kr!r} has slot {usage[kr]['slot']!r}")
            if k["temporal"] and (r.get("time") or {}).get("model") != "interval":
                err("KHG-M011", f"{r['id']}: temporal key needs time model 'interval'")
        tm = r.get("time")
        if tm and tm["model"] == "interval":
            for end in ("start", "end"):
                u = usage.get(tm[end])
                if u is None or u["slot"] != "time":
                    err("KHG-M007", f"{r['id']}: time.{end} {tm[end]!r} is not a time-slot role of the relation")
        elif any(u["slot"] == "time" for u in r["roles"]):
            err("KHG-M007", f"{r['id']}: time-slot roles without an interval time model")
        p = r.get("primary")
        if p:
            for x in (p["subject"], p["object"]):
                if x not in usage or usage[x]["slot"] != "core":
                    err("KHG-M012", f"{r['id']}: primary role {x!r} must be a core role of the relation")
    if len(rel_ids) != len(set(rel_ids)):
        err("KHG-M013", "relation id declared twice")
    return out
