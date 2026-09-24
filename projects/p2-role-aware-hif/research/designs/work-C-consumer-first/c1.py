"""Prototype of the C1 record model for design C (consumer-first). Research code, not the package.

It implements exactly the rules written in design-C-consumer-first.md section 2, so that the JSON
examples in the design are produced and checked by code:
  * canonical JSON and the four identifiers (content_key, core_key, key_digest, event_hash)
  * literal canonical forms and equality
  * arity (arity / core / participants)
  * normalise(): fills slot and direction from the relation-type schema, derives valid_time from
    time-slot bindings, computes arity and keys, sorts bindings and evidence.
"""
from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import re
import unicodedata

RECORD_FORMAT = "khg-record/1.0.0"
SCHEMA_FORMAT = "khg-relation-schema/1.0.0"
SLOTS = ("core", "qualifier", "time", "meta")
COUNTED_SLOTS = ("core", "qualifier", "time")
STATUSES = ("candidate", "asserted", "disputed", "superseded", "retracted", "goal")
RANKS = ("preferred", "normal", "deprecated")
VISIBILITY = ("visible", "suppressed")
DATATYPES = ("string", "lang-string", "integer", "decimal", "boolean", "time", "quantity", "iri")
PRECISIONS = ("millennium", "century", "decade", "year", "month", "day", "second")
SPECIALS = ("somevalue", "novalue", "unbound")

ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}:[^\s<>\"{}|\\^`\x00-\x1f\x7f]{1,256}$")
RESERVED_NS = ("khg-lit", "khg-ref", "hif", "hif-int", "cand")
SYM_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")  # role, relation, entity-type ids
LOCAL_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")         # bid, eid


# ----------------------------------------------------------------------------------------------
# canonical JSON and hashes
# ----------------------------------------------------------------------------------------------

def cjson(obj) -> str:
    """Canonical JSON: sorted keys, no whitespace, UTF-8, NaN forbidden."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_hex(obj) -> str:
    return hashlib.sha256(cjson(obj).encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()


def value_kind(v: dict) -> str:
    for k in ("entity", "literal", "hyperedge", "special"):
        if k in v:
            return k
    raise ValueError(f"not a C1 value: {v!r}")


def _items(bindings, keep):
    out = []
    for b in bindings:
        if keep(b):
            out.append([b["role"], cjson(b["value"]), "" if b.get("position") is None else str(b["position"])])
    return sorted(out)


def content_key(rec: dict) -> str:
    return "sha256:" + sha256_hex({"k": "content", "r": rec["relation"],
                                   "b": _items(rec["bindings"], lambda b: b["slot"] != "meta")})


def core_key(rec: dict) -> str:
    return "sha256:" + sha256_hex({"k": "core", "r": rec["relation"],
                                   "b": _items(rec["bindings"], lambda b: b["slot"] == "core")})


def key_digest(rec: dict, key_roles) -> str | None:
    if not key_roles:
        return None
    return "sha256:" + sha256_hex({"k": "key", "r": rec["relation"],
                                   "b": _items(rec["bindings"], lambda b: b["role"] in key_roles)})


def event_hash(content: str, ev: dict) -> str | None:
    if ev.get("type") != "extracted":
        return None
    pos = sorted([s["start"], s["end"]] for s in ev.get("selectors", []) if s["type"] == "position")
    return "sha256:" + sha256_hex({"k": "event", "content": content,
                                   "doc": ev.get("source", {}).get("doc_sha256"),
                                   "pos": pos, "agent": ev.get("activity", {}).get("agent"),
                                   "model": ev.get("activity", {}).get("model")})


def literal_node_id(lit: dict) -> str:
    return "khg-lit:" + sha256_hex(lit)[:32]


# ----------------------------------------------------------------------------------------------
# literals
# ----------------------------------------------------------------------------------------------

INT_RE = re.compile(r"^-?(0|[1-9][0-9]*)$")
DEC_RE = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?$")
YEAR_RE = r"-?[0-9]{4,}"
TIME_RE = {
    "year": re.compile(rf"^{YEAR_RE}$"),
    "month": re.compile(rf"^{YEAR_RE}-(0[1-9]|1[0-2])$"),
    "day": re.compile(rf"^{YEAR_RE}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"),
    "second": re.compile(rf"^{YEAR_RE}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$"),
}
for _p in ("millennium", "century", "decade"):
    TIME_RE[_p] = TIME_RE["year"]
LANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{1,8})*$")
IRI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s<>\"{}|\\^`]*$")


def literal_errors(lit: dict) -> list[str]:
    """Lexical checks of a canonical literal. Returns a list of error codes (empty if valid)."""
    dt, lx = lit.get("datatype"), lit.get("literal")
    errs = []
    if dt not in DATATYPES:
        return ["R-LIT-DATATYPE"]
    if not isinstance(lx, str) or unicodedata.normalize("NFC", lx) != lx:
        return ["R-LIT-LEXICAL"]
    extra = set(lit) - {"literal", "datatype", "precision", "unit", "lang", "lower", "upper", "calendar"}
    if extra:
        errs.append("R-LIT-FIELD")
    allowed = {"string": set(), "lang-string": {"lang"}, "integer": set(), "decimal": set(),
               "boolean": set(), "time": {"precision", "calendar"}, "quantity": {"unit", "lower", "upper"},
               "iri": set()}[dt]
    if (set(lit) - {"literal", "datatype"}) - allowed:
        errs.append("R-LIT-FIELD")
    if dt == "integer" and (not INT_RE.match(lx) or lx == "-0"):
        errs.append("R-LIT-LEXICAL")
    if dt in ("decimal", "quantity") and (not DEC_RE.match(lx) or lx == "-0"):
        errs.append("R-LIT-LEXICAL")
    if dt == "boolean" and lx not in ("true", "false"):
        errs.append("R-LIT-LEXICAL")
    if dt == "iri" and not IRI_RE.match(lx):
        errs.append("R-LIT-LEXICAL")
    if dt == "lang-string" and not LANG_RE.match(lit.get("lang", "")):
        errs.append("R-LIT-LANG")
    if dt == "time":
        p = lit.get("precision")
        if p not in PRECISIONS:
            errs.append("R-LIT-PRECISION")
        elif not TIME_RE[p].match(lx) or not _valid_date(lx):
            errs.append("R-LIT-LEXICAL")
        if lit.get("calendar", "gregorian") not in ("gregorian", "julian") or lit.get("calendar") == "gregorian":
            errs.append("R-LIT-FIELD")  # canonical form omits the default calendar
    if dt == "quantity":
        if not isinstance(lit.get("unit"), str) or not (lit["unit"] == "1" or ID_RE.match(lit["unit"])):
            errs.append("R-LIT-UNIT")
        for b in ("lower", "upper"):
            if b in lit and not DEC_RE.match(lit[b]):
                errs.append("R-LIT-LEXICAL")
        if not errs:
            from decimal import Decimal
            a = Decimal(lx)
            if "lower" in lit and Decimal(lit["lower"]) > a or "upper" in lit and Decimal(lit["upper"]) < a:
                errs.append("R-LIT-BOUNDS")
    return errs


def _valid_date(lx: str) -> bool:
    m = re.match(r"^(-?[0-9]{4,})(?:-([0-9]{2})(?:-([0-9]{2}))?)?", lx)
    y, mo, d = int(m.group(1)), m.group(2), m.group(3)
    if d is None:
        return True
    mo, d = int(mo), int(d)
    leap = (y % 4 == 0 and y % 100 != 0) or y % 400 == 0
    dim = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
    return 1 <= d <= dim


# ----------------------------------------------------------------------------------------------
# time: valid-time bounds and comparison
# ----------------------------------------------------------------------------------------------

def granularity(t: str) -> str:
    for p in ("second", "day", "month", "year"):
        if TIME_RE[p].match(t):
            return p
    raise ValueError(f"not a time bound: {t!r}")


def lower_instant(t: str) -> tuple:
    """A bound denotes the first instant of its period. Returns a sortable tuple."""
    m = re.match(r"^(-?[0-9]{4,})(?:-([0-9]{2}))?(?:-([0-9]{2}))?(?:T([0-9]{2}):([0-9]{2}):([0-9]{2})Z)?$", t)
    y = int(m.group(1))
    rest = [int(g) if g else d for g, d in zip(m.groups()[1:], (1, 1, 0, 0, 0))]
    return (y, *rest)


def next_period(t: str) -> str:
    g = granularity(t)
    if g == "year":
        y = int(t)
        return f"{y + 1:04d}" if y + 1 >= 0 else f"-{abs(y + 1):04d}"
    if g == "month":
        y, mo = t.rsplit("-", 1)
        y, mo = int(y), int(mo)
        y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
        return f"{y:04d}-{mo:02d}"
    if g == "day":
        d = _dt.date.fromisoformat(t) + _dt.timedelta(days=1)
        return d.isoformat()
    d = _dt.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ") + _dt.timedelta(seconds=1)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def time_bound(lit: dict) -> str | None:
    """Time literal -> valid-time bound string (Gregorian). Coarser than year -> year string."""
    if lit.get("calendar") == "julian":
        return None  # prototype: the package converts Julian day-precision dates (design 2.9)
    return lit["literal"]


# ----------------------------------------------------------------------------------------------
# schema access
# ----------------------------------------------------------------------------------------------

class Schema:
    def __init__(self, doc: dict):
        self.doc = doc
        self.ref = f"{doc['id']}/{doc['version']}"
        self.roles = {r["id"]: r for r in doc["roles"]}
        self.relations = {r["id"]: r for r in doc["relations"]}
        self.usage = {(r["id"], u["role"]): u for r in doc["relations"] for u in r["roles"]}
        self.types = {t["id"]: t for t in doc.get("entity_types", [])}
        self.time_model = doc.get("time_model", {})

    def key_roles(self, relation):
        k = self.relations[relation].get("key")
        return set(k["roles"]) if k else set()

    def type_closure(self, t):
        seen, stack = set(), [t]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack.extend(self.types.get(x, {}).get("parents", []))
        return seen


# ----------------------------------------------------------------------------------------------
# arity and normalisation
# ----------------------------------------------------------------------------------------------

def arity(rec: dict) -> dict:
    counted = [b for b in rec["bindings"]
               if b["slot"] in COUNTED_SLOTS and value_kind(b["value"]) in ("entity", "literal", "hyperedge")
               or (b["slot"] in COUNTED_SLOTS and b["value"].get("special") == "somevalue")]
    distinct = set()
    for b in counted:
        v = b["value"]
        distinct.add(("sv", b["bid"]) if v.get("special") == "somevalue" else cjson(v))
    return {"arity": len(counted),
            "core": sum(1 for b in counted if b["slot"] == "core"),
            "participants": len(distinct)}


def binding_sort_key(b):
    return (b["role"], -1 if b.get("position") is None else b["position"], cjson(b["value"]), b["bid"])


def derive_valid_time(rec: dict, schema: Schema):
    tm = schema.time_model
    by_role = {}
    for b in rec["bindings"]:
        if b["slot"] == "time" and "literal" in b["value"]:
            by_role.setdefault(b["role"], []).append(b["value"])
    frm, to, pt = (by_role.get(tm.get(k)) for k in ("from_role", "to_role", "point_role"))
    if not (frm or to or pt):
        return None
    vt = {}
    if frm:
        vt["from"] = time_bound(frm[0])
    if to:
        vt["to"] = time_bound(to[0])
    if pt and not (frm or to):
        g = pt[0].get("precision")
        if g in ("year", "month", "day", "second"):
            vt = {"from": time_bound(pt[0]), "to": next_period(time_bound(pt[0]))}
    return {k: v for k, v in vt.items() if v is not None} or None


def normalise(rec: dict, schema: Schema) -> dict:
    r = copy.deepcopy(rec)
    if r.get("kind") != "hyperedge":
        return r
    r.setdefault("schema", schema.ref)
    r.setdefault("rank", "normal")
    r.setdefault("visibility", "visible")
    for b in r["bindings"]:
        u = schema.usage[(r["relation"], b["role"])]
        b["slot"] = u["slot"]
        if "direction" in u:
            b["direction"] = u["direction"]
    r["bindings"].sort(key=binding_sort_key)
    vt = derive_valid_time(r, schema)
    if vt is not None:
        given = {k: v for k, v in r.get("valid_time", {}).items() if k != "end_cause"}
        if "valid_time" in r and given != vt:
            raise ValueError(f"{r.get('id')}: valid_time {r['valid_time']} disagrees with time bindings {vt}")
        if "end_cause" in r.get("valid_time", {}):
            vt["end_cause"] = r["valid_time"]["end_cause"]
        r["valid_time"] = vt
    r["arity"] = arity(r)
    keys = {"content": content_key(r), "core": core_key(r)}
    kd = key_digest(r, schema.key_roles(r["relation"]))
    if kd:
        keys["key"] = kd
    r["keys"] = keys
    for ev in r.get("evidence", []):
        eh = event_hash(keys["content"], ev)
        if eh:
            ev["event_hash"] = eh
    if "evidence" in r:
        r["evidence"].sort(key=lambda e: e["eid"])
    return r


def dump_jsonl(records, path):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(cjson(rec) + "\n")


def load_jsonl(path):
    def bad(c):
        raise ValueError(f"non-standard JSON constant {c}")

    def pairs(ps):
        d = {}
        for k, v in ps:
            if k in d:
                raise ValueError(f"duplicate key {k!r}")
            d[k] = v
        return d
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line, parse_constant=bad, object_pairs_hook=pairs))
    return out
