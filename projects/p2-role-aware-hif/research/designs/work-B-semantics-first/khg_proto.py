"""Prototype of design B (semantics-first) for P2 contracts. Scratch code, not the package.

Implements enough of C1 to check the design: strict JSON, canonical JSON and hashes, literal
canonicalisation, precision windows and the presumed-interval algebra, derived fields (arity, keys,
valid time), the refinement order, the pairwise identity classifier with collision policies, and the
C1 <-> HIF codec of the roles convention / KHG profile.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

# ----------------------------------------------------------------------------------------------
# Strict JSON, canonical JSON, hashing
# ----------------------------------------------------------------------------------------------


class KHGError(ValueError):
    def __init__(self, code, msg):
        super().__init__(f"{code}: {msg}")
        self.code = code


def strict_loads(text: str):
    if text.strip() == "":
        raise KHGError("KHG-J001", "empty document")

    def pairs(ps):
        d = {}
        for k, v in ps:
            if k in d:
                raise KHGError("KHG-J003", f"duplicate key {k!r}")
            d[k] = v
        return d

    def const(c):
        raise KHGError("KHG-J004", f"non-finite number {c}")

    try:
        obj = json.loads(text, object_pairs_hook=pairs, parse_constant=const)
    except KHGError:
        raise
    except json.JSONDecodeError as e:
        raise KHGError("KHG-J001", f"not JSON: {e}")

    def walk(o):
        if isinstance(o, str):
            try:
                o.encode("utf-8")
            except UnicodeEncodeError:
                raise KHGError("KHG-J005", "lone surrogate in string")
        elif isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(k)
                walk(v)

    walk(obj)
    return obj


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _nfc_all(o, floats):
    if isinstance(o, str):
        return nfc(o)
    if isinstance(o, list):
        return [_nfc_all(x, floats) for x in o]
    if isinstance(o, dict):
        return {nfc(k): _nfc_all(v, floats) for k, v in o.items()}
    if isinstance(o, float) and not floats:
        raise KHGError("KHG-C900", "float inside a hashed payload")
    return o


def cjson(o, floats: bool = True) -> str:
    """Canonical JSON text: NFC strings, sorted keys, no whitespace, UTF-8, no NaN."""
    return json.dumps(_nfc_all(o, floats), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(domain: str, payload, n: int | None = None) -> str:
    d = hashlib.sha256((domain + "\n" + cjson(payload, floats=False)).encode("utf-8")).hexdigest()
    return d[:n] if n else "sha256:" + d


# ----------------------------------------------------------------------------------------------
# Literals
# ----------------------------------------------------------------------------------------------

TIME_RE = re.compile(r"^([+-])(\d{4,})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$")
DEC_RE = re.compile(r"^(\+0|[+-](0\.[0-9]*[1-9]|[1-9][0-9]*(\.[0-9]*[1-9])?))$")
NEG_INF = (float("-inf"),)
POS_INF = (float("inf"),)


def _dim(y, m):
    if m == 2:
        leap = (y % 4 == 0 and y % 100 != 0) or y % 400 == 0
        return 29 if leap else 28
    return 31 if m in (1, 3, 5, 7, 8, 10, 12) else 30


def parse_time(value: str, precision: int):
    m = TIME_RE.match(value)
    if not m:
        raise KHGError("KHG-S006", f"time lexical form {value!r}")
    sign, Y, M, D, hh, mm, ss = m.groups()
    y = int(Y) * (-1 if sign == "-" else 1)
    M, D, hh, mm, ss = int(M), int(D), int(hh), int(mm), int(ss)
    if not 0 <= precision <= 14:
        raise KHGError("KHG-S006", f"precision {precision}")
    # components below precision must be zero (Wikidata convention: 00 month/day)
    need = {"M": precision >= 10, "D": precision >= 11, "h": precision >= 12, "m": precision >= 13, "s": precision >= 14}
    for name, val, ok, rng in (("M", M, need["M"], (1, 12)), ("D", D, need["D"], None), ("h", hh, need["h"], (0, 23)),
                               ("m", mm, need["m"], (0, 59)), ("s", ss, need["s"], (0, 59))):
        if not ok and val != 0 and name in ("h", "m", "s"):
            raise KHGError("KHG-S006", f"{name} set below precision in {value!r}")
        if not ok and name in ("M", "D") and val != 0:
            raise KHGError("KHG-S006", f"{name} set below precision in {value!r}")
        if ok and rng and not rng[0] <= val <= rng[1]:
            raise KHGError("KHG-S006", f"{name} out of range in {value!r}")
    if need["D"] and not 1 <= D <= _dim(y, M):
        raise KHGError("KHG-S006", f"day out of range in {value!r}")
    return y, M, D, hh, mm, ss


def time_window(lit):
    """[lo, hi) of instants the value may denote, as comparable tuples."""
    p = lit["precision"]
    y, M, D, hh, mm, ss = parse_time(lit["time"], p)
    if p <= 9:
        step = 10 ** (9 - p)
        y0 = (y // step) * step
        return (y0, 1, 1, 0, 0, 0), (y0 + step, 1, 1, 0, 0, 0)
    if p == 10:
        lo = (y, M, 1, 0, 0, 0)
        hi = (y + 1, 1, 1, 0, 0, 0) if M == 12 else (y, M + 1, 1, 0, 0, 0)
        return lo, hi
    if p == 11:
        lo = (y, M, D, 0, 0, 0)
        if D < _dim(y, M):
            hi = (y, M, D + 1, 0, 0, 0)
        elif M < 12:
            hi = (y, M + 1, 1, 0, 0, 0)
        else:
            hi = (y + 1, 1, 1, 0, 0, 0)
        return lo, hi
    # hour/minute/second: treat as exact to the unit (sufficient for the prototype)
    lo = (y, M, D, hh, mm if p >= 13 else 0, ss if p >= 14 else 0)
    return lo, lo[:-1] + (lo[-1] + 1,)


def canon_literal(lit: dict) -> dict:
    lit = copy.deepcopy(lit)
    dt = lit["datatype"]
    if dt == "time":
        parse_time(lit["time"], lit["precision"])
        lit.setdefault("calendar", "gregorian")
        if lit["calendar"] != "gregorian":
            raise KHGError("KHG-S006", "v1 accepts gregorian only")
    elif dt == "quantity":
        for k in ("amount", "lower", "upper"):
            if k in lit and not DEC_RE.match(lit[k]):
                raise KHGError("KHG-S006", f"decimal {lit[k]!r}")
        if ("lower" in lit) != ("upper" in lit):
            raise KHGError("KHG-S006", "bounds come in pairs")
    elif dt in ("string", "iri"):
        lit["value"] = nfc(lit["value"])
    elif dt == "lang_string":
        lit["value"] = nfc(lit["value"])
        lit["lang"] = lit["lang"].lower()
    return lit


def lit_label(lit):
    dt = lit["datatype"]
    if dt == "time":
        return f'{lit["time"]}/{lit["precision"]}'
    if dt == "quantity":
        return lit["amount"] + ("" if lit["unit"] == "1" else " " + lit["unit"])
    if dt == "lang_string":
        return f'{lit["value"]}@{lit["lang"]}'
    if dt == "geo":
        return f'{lit["lat"]},{lit["lon"]}'
    return str(lit["value"]).lower() if dt == "boolean" else lit["value"]


# ----------------------------------------------------------------------------------------------
# Schema access
# ----------------------------------------------------------------------------------------------

BUILTIN_META = {
    "khg:supersedes": {"id": "khg:supersedes", "kind": "meta",
                       "roles": [{"role": "khg:superseding", "slot": "core", "fillers": [{"fact": []}], "min": 1, "max": None, "direction": "tail"},
                                 {"role": "khg:superseded", "slot": "core", "fillers": [{"fact": []}], "min": 1, "max": None, "direction": "head"}]},
    "khg:retracts": {"id": "khg:retracts", "kind": "meta",
                     "roles": [{"role": "khg:retracted", "slot": "core", "fillers": [{"fact": []}], "min": 1, "max": None, "direction": "head"}]},
    "khg:disputes": {"id": "khg:disputes", "kind": "meta",
                     "roles": [{"role": "khg:disputed", "slot": "core", "fillers": [{"fact": []}], "min": 2, "max": None, "direction": "head"}]},
    "khg:fulfils": {"id": "khg:fulfils", "kind": "meta",
                    "roles": [{"role": "khg:fulfilling", "slot": "core", "fillers": [{"fact": []}], "min": 1, "max": 1, "direction": "tail"},
                              {"role": "khg:goal", "slot": "core", "fillers": [{"fact": []}], "min": 1, "max": 1, "direction": "head"}]},
}


class Schema:
    def __init__(self, doc):
        self.doc = doc
        self.rel = {r["id"]: r for r in doc["relations"]}
        self.rel.update(BUILTIN_META)
        self.default_time = doc.get("default_time")

    def usage(self, rel, role):
        for u in self.rel[rel]["roles"]:
            if u["role"] == role:
                return u
        raise KHGError("KHG-S002", f"role {role!r} not allowed for {rel!r}")

    def time_model(self, rel):
        r = self.rel[rel]
        tm = r.get("time")
        if tm is None:
            return {"model": "unstated"}
        return tm

    def key(self, rel):
        return self.rel[rel].get("key")

    def sha256(self):
        return digest("khg-schema/1", self.doc)


def vkind(v):
    (k,) = v.keys()
    return k


def canon_value(v):
    k = vkind(v)
    if k == "literal":
        return {"literal": canon_literal(v["literal"])}
    if k in ("entity", "fact"):
        return {k: nfc(v[k])}
    return copy.deepcopy(v)


def eff_dir(schema: Schema, rec, b):
    u = schema.usage(rec["relation"], b["role"])
    return b.get("direction") or u.get("direction")


def bsortkey(b):
    return (b["role"], b.get("position", 0), cjson(canon_value(b["value"])))


# ----------------------------------------------------------------------------------------------
# Derived fields
# ----------------------------------------------------------------------------------------------

COUNTED_KINDS = ("entity", "literal", "fact", "special:somevalue")


def _vk(v):
    k = vkind(v)
    return "special:" + v["special"] if k == "special" else k


def content_bindings(schema, rec, slots=("core", "qualifier", "time")):
    out = []
    for b in rec["bindings"]:
        u = schema.usage(rec["relation"], b["role"])
        if u["slot"] in slots:
            out.append(b)
    return out


def binding_tuple(b):
    return [b["role"], b.get("position"), canon_value(b["value"])]


def presumed_interval(schema, rec):
    """Returns dict with s_lo, s_hi, e_lo, e_hi (tuples) and kind."""
    tm = schema.time_model(rec["relation"])
    if tm["model"] == "invariant":
        return {"kind": "invariant", "s_lo": NEG_INF, "s_hi": NEG_INF, "e_lo": POS_INF, "e_hi": POS_INF}
    s = e = None
    if tm["model"] == "interval":
        for b in rec["bindings"]:
            if b["role"] == tm["start"] and vkind(b["value"]) == "literal":
                s = time_window(b["value"]["literal"])
            if b["role"] == tm["end"] and vkind(b["value"]) == "literal":
                e = time_window(b["value"]["literal"])
    kind = {(True, True): "period", (True, False): "since", (False, True): "until", (False, False): "unstated"}[(s is not None, e is not None)]
    s_lo, s_hi = s if s else (NEG_INF, NEG_INF)
    e_lo, e_hi = e if e else (POS_INF, POS_INF)
    return {"kind": kind, "s_lo": s_lo, "s_hi": s_hi, "e_lo": e_lo, "e_hi": e_hi}


def valid_time_view(schema, rec):
    tm = schema.time_model(rec["relation"])
    iv = presumed_interval(schema, rec)
    out = {"kind": iv["kind"]}
    if tm["model"] == "interval":
        for b in rec["bindings"]:
            if b["role"] == tm["start"]:
                out["start"] = canon_value(b["value"])
            if b["role"] == tm["end"]:
                out["end"] = canon_value(b["value"])
    return out


def key_digest(schema, rec):
    key = schema.key(rec["relation"])
    if not key:
        return None
    kb = [b for b in rec["bindings"] if b["role"] in key["roles"]]
    present = {b["role"] for b in kb}
    if present != set(key["roles"]):
        return None  # incomplete key: exempt
    if any(vkind(b["value"]) not in ("entity", "literal", "fact") for b in kb):
        return None  # special value in a key role: exempt
    return digest("khg-key-digest/1", {"relation": rec["relation"], "bindings": sorted((binding_tuple(b) for b in kb), key=cjson)})


def event_hash(content_key, ev):
    """Same fact, same passage, same tool and model: same event, whatever the run."""
    act = ev.get("activity", {})
    return digest("khg-event/1", {
        "content_key": content_key,
        "doc": ev["source"].get("doc_sha256") or ev["source"]["doc_id"],
        "selectors": sorted((cjson(x) for x in ev.get("selectors", []))),
        "activity": {k: act[k] for k in ("agent", "agent_version", "model", "model_version", "prompt_id", "skill_id") if k in act},
    })


def derived(schema, rec):
    if rec["kind"] in ("fact", "rule"):
        cb = content_bindings(schema, rec)
        slot = lambda b: schema.usage(rec["relation"], b["role"])["slot"]
        valued = [b for b in cb if _vk(b["value"]) in COUNTED_KINDS]
        counted = [b for b in valued if slot(b) in ("core", "qualifier")]   # participants; validity bounds excluded
        timed = [b for b in valued if slot(b) == "time"]
        core = [b for b in counted if slot(b) == "core"]
        distinct = set()
        sv = 0
        for b in counted:
            if _vk(b["value"]) == "special:somevalue":
                sv += 1
            else:
                distinct.add(cjson(canon_value(b["value"])))
        return {
            "arity": len(counted),
            "core_arity": len(core),
            "statement_arity": len(counted) + len(timed),
            "distinct_fillers": len(distinct) + sv,
            "content_key": digest("khg-content-key/1", {"relation": rec["relation"], "bindings": sorted((binding_tuple(b) for b in cb), key=cjson)}),
            "core_key": digest("khg-core-key/1", {"relation": rec["relation"], "bindings": sorted((binding_tuple(b) for b in cb if schema.usage(rec["relation"], b["role"])["slot"] == "core"), key=cjson)}),
            "key_digest": key_digest(schema, rec),
            "valid_time": valid_time_view(schema, rec),
        }
    if rec["kind"] == "goal":
        nb = sum(1 for b in rec["bindings"] if vkind(b["value"]) != "unbound")
        return {"n_bound": nb, "n_unbound": len(rec["bindings"]) - nb}
    return {}


# ----------------------------------------------------------------------------------------------
# Refinement order and identity classification
# ----------------------------------------------------------------------------------------------


def value_refines(v2, v1) -> bool:
    """v2 is at least as specific as v1."""
    c1, c2 = canon_value(v1), canon_value(v2)
    if cjson(c1) == cjson(c2):
        return True
    k1, k2 = _vk(c1), _vk(c2)
    if k1 == "special:somevalue" and k2 in ("entity", "literal", "fact"):
        return True
    if k1 == k2 == "literal":
        l1, l2 = c1["literal"], c2["literal"]
        if l1["datatype"] == l2["datatype"] == "time":
            if l2["precision"] < l1["precision"]:
                return False
            a1, b1 = time_window(l1)
            a2, b2 = time_window(l2)
            return a1 <= a2 and b2 <= b1
        if l1["datatype"] == l2["datatype"] == "quantity" and l1["unit"] == l2["unit"]:
            from decimal import Decimal as Dm
            lo1, hi1 = Dm(l1.get("lower", l1["amount"])), Dm(l1.get("upper", l1["amount"]))
            lo2, hi2 = Dm(l2.get("lower", l2["amount"])), Dm(l2.get("upper", l2["amount"]))
            return lo1 <= lo2 and hi2 <= hi1 and lo1 <= Dm(l2["amount"]) <= hi1
    return False


def _match(left, right, ok):
    """Kuhn's algorithm: can every item of `left` be matched to a distinct item of `right`?"""
    match_r = {}

    def try_(i, seen):
        for j in range(len(right)):
            if j in seen or not ok(right[j], left[i]):
                continue
            seen.add(j)
            if j not in match_r or try_(match_r[j], seen):
                match_r[j] = i
                return True
        return False

    return all(try_(i, set()) for i in range(len(left)))


def fact_refines(schema, f2, f1, exclude_roles=(), slots=("core", "qualifier", "time")) -> bool:
    """f2 is at least as specific as f1 (f2 entails f1)."""
    if f2["relation"] != f1["relation"]:
        return False
    rel = f1["relation"]
    b1 = [b for b in content_bindings(schema, f1, slots) if b["role"] not in exclude_roles]
    b2 = [b for b in content_bindings(schema, f2, slots) if b["role"] not in exclude_roles]
    roles = {b["role"] for b in b1} | {b["role"] for b in b2}
    for role in sorted(roles):
        u = schema.usage(rel, role)
        r1 = [b for b in b1 if b["role"] == role]
        r2 = [b for b in b2 if b["role"] == role]
        nv1 = any(_vk(b["value"]) == "special:novalue" for b in r1)
        nv2 = any(_vk(b["value"]) == "special:novalue" for b in r2)
        if nv1 or nv2:
            if nv1 and not nv2:
                return False  # f2 binds a role f1 declares empty (or omits the novalue): not entailed
            if nv2 and not nv1 and r1:
                return False
            continue
        if not r1:
            continue  # f2 adds a role f1 did not mention: narrowing, allowed
        if u.get("complete") and len(r1) != len(r2):
            return False
        if u.get("ordered"):
            p2 = {b["position"]: b for b in r2}
            for b in r1:
                if b["position"] not in p2 or not value_refines(p2[b["position"]]["value"], b["value"]):
                    return False
            continue
        if not _match(r1, r2, lambda x2, x1: value_refines(x2["value"], x1["value"])):
            return False
    return True


def definite_overlap(a, b):
    return max(a["s_hi"], b["s_hi"]) < min(a["e_lo"], b["e_lo"])


def possible_overlap(a, b):
    return max(a["s_lo"], b["s_lo"]) < min(a["e_hi"], b["e_hi"])


def negation_conflict(schema, x, y):
    for f_nv, g in ((x, y), (y, x)):
        for b in f_nv["bindings"]:
            if _vk(b["value"]) != "special:novalue":
                continue
            rho = b["role"]
            if not any(bb["role"] == rho and _vk(bb["value"]) in ("entity", "literal", "fact", "special:somevalue") for bb in g["bindings"]):
                continue
            if fact_refines(schema, g, f_nv, exclude_roles=(rho,), slots=("core", "qualifier")) and \
                    definite_overlap(presumed_interval(schema, g), presumed_interval(schema, f_nv)):
                return True
    return False


def relate(schema, n, e):
    """Pairwise relation of incoming fact n to existing fact e. Returns (relation, detail)."""
    if n["relation"] != e["relation"]:
        return "unrelated", {}
    r_ne = fact_refines(schema, n, e)
    r_en = fact_refines(schema, e, n)
    if r_ne and r_en:
        return "duplicate", {}
    if r_ne:
        return "refines", {}
    if r_en:
        return "generalises", {}
    if negation_conflict(schema, n, e):
        return "negation_conflict", {}
    key = schema.key(n["relation"])
    if key:
        kn, ke = key_digest(schema, n), key_digest(schema, e)
        if kn is not None and kn == ke:
            iv_n, iv_e = presumed_interval(schema, n), presumed_interval(schema, e)
            if not key.get("temporal", False) or definite_overlap(iv_n, iv_e):
                return "key_conflict", {"policy": key["on_collision"]}
            return "key_timeline", {"possible_overlap": possible_overlap(iv_n, iv_e)}
    return "distinct", {}


def resolve(schema, n, e):
    """Outcome of adding n to a store that holds e (asserted), per the contract."""
    rel, d = relate(schema, n, e)
    if rel == "duplicate":
        return rel, "merge-evidence: n's evidence appended to e (new version of e, same content)"
    if rel == "refines":
        return rel, "refine: e gets a new version with n's content and the union of evidence"
    if rel == "generalises":
        return rel, "support: n's evidence appended to e, supports mapped to e's bindings"
    if rel == "negation_conflict":
        return rel, "dispute: khg:disputes record; both disputed"
    if rel == "key_conflict":
        pol = d["policy"]
        if pol == "close_older":
            iv_n, iv_e = presumed_interval(schema, n), presumed_interval(schema, e)
            known = iv_n["kind"] in ("since", "period") and iv_e["kind"] in ("since", "period")
            if known:
                older, newer = (e, n) if iv_e["s_hi"] <= iv_n["s_lo"] else (n, e) if iv_n["s_hi"] <= iv_e["s_lo"] else (None, None)
                if older is not None and presumed_interval(schema, older)["kind"] == "since":
                    who = "e" if older is e else "n"
                    return rel, f"succession: close {who} (end := start of the other; inferred evidence); status unchanged"
            return rel, "dispute (close_older not applicable: starts unknown/unordered or older already ended)"
        if pol == "supersede":
            return rel, "supersession: e superseded by n (reason correction); khg:supersedes record"
        if pol == "reject":
            return rel, "reject: put refused (KHG-D016)"
        return rel, "dispute: khg:disputes record; both disputed"
    if rel == "key_timeline":
        return rel, "distinct facts on the same key timeline" + (" (possible overlap only: info)" if d["possible_overlap"] else "")
    return rel, "distinct: insert n"


# ----------------------------------------------------------------------------------------------
# HIF codec (C1 document <-> role-aware HIF, KHG profile)
# ----------------------------------------------------------------------------------------------

HIF_SCHEMA_URL = ("https://raw.githubusercontent.com/HIF-org/HIF-standard/"
                  "b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json")
HIF_SCHEMA_SHA256 = "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196"

EDGE_FIELDS = [  # C1 field -> HIF edges[].attrs key
    ("kind", "khg:kind"), ("relation", "khg:relation"), ("status", "khg:status"), ("status_ref", "khg:status-ref"),
    ("rank", "khg:rank"), ("rank_reason", "khg:rank-reason"), ("visibility", "khg:visibility"),
    ("version", "khg:version"), ("recorded_at", "khg:recorded-at"), ("typed_under", "khg:typed-under"),
    ("evidence", "khg:evidence"), ("confidence", "khg:confidence"), ("text", "khg:text"),
    ("goal", "khg:goal"), ("meta", "khg:meta"), ("extensions", "khg:extensions"),
]
ENTITY_FIELDS = [("types", "khg:types"), ("label", "khg:label"), ("aliases", "khg:aliases"),
                 ("redirect_to", "khg:redirect-to"), ("extensions", "khg:extensions")]


def literal_node_id(lit):
    return "_:lit:" + digest("khg-literal-node/1", canon_literal(lit), 32)


def special_node_id(kind, rec_id, bid):
    tag = {"somevalue": "sv", "novalue": "nv", "unbound": "var"}[kind]
    return f"_:{tag}:" + digest("khg-special-node/1", [rec_id, bid], 32)


def ref_node_id(fid):
    return "_:ref:" + fid


def value_node(rec, b, nodes):
    v = b["value"]
    k = vkind(v)
    if k == "entity":
        return v["entity"]
    if k == "literal":
        lit = canon_literal(v["literal"])
        nid = literal_node_id(lit)
        nodes.setdefault(nid, {"node": nid, "attrs": {"khg:kind": "literal", "khg:literal": lit, "khg:label": lit_label(lit)}})
        return nid
    if k == "fact":
        nid = ref_node_id(v["fact"])
        nodes.setdefault(nid, {"node": nid, "attrs": {"khg:kind": "fact-ref", "khg:ref": v["fact"]}})
        return nid
    if k == "special":
        nid = special_node_id(v["special"], rec["id"], b["bid"])
        nodes[nid] = {"node": nid, "attrs": {"khg:kind": v["special"]}}
        return nid
    if k == "unbound":
        nid = special_node_id("unbound", rec["id"], b["bid"])
        nodes[nid] = {"node": nid, "attrs": {"khg:kind": "unbound", "khg:unbound": copy.deepcopy(v["unbound"])}}
        return nid
    raise KHGError("KHG-C001", f"value kind {k}")


def c1_to_hif(doc, schema: Schema):
    hdr = doc["header"]
    recs = doc["records"]
    ents = sorted((r for r in recs if r["kind"] == "entity"), key=lambda r: r["id"])
    edges = sorted((r for r in recs if r["kind"] in ("fact", "meta", "goal", "rule")), key=lambda r: r["id"])
    directed = all(eff_dir(schema, r, b) for r in edges for b in r["bindings"])
    nodes = {}
    for e in ents:
        a = {"khg:kind": "entity"}
        for f, k in ENTITY_FIELDS:
            if f in e:
                a[k] = copy.deepcopy(e[f])
        nodes[e["id"]] = {"node": e["id"], "attrs": a}
    incidences, erecs = [], []
    for r in edges:
        a = {}
        for f, k in EDGE_FIELDS:
            if f in r:
                a[k] = copy.deepcopy(r[f])
        er = {"edge": r["id"], "attrs": a}
        w = (r.get("extensions") or {}).get("hif:weight")
        if w is not None:
            er["weight"] = w
        erecs.append(er)
        for b in sorted(r["bindings"], key=bsortkey):
            nid = value_node(r, b, nodes)
            ia = {"role": b["role"], "khg:bid": b["bid"]}
            if "position" in b:
                ia["role-position"] = b["position"]
            inc = {"edge": r["id"], "node": nid}
            d = eff_dir(schema, r, b)
            if directed:
                inc["direction"] = d
            elif d:
                ia["khg:direction"] = d
            inc["attrs"] = ia
            incidences.append(inc)
    md = {
        "hif-schema": HIF_SCHEMA_URL,
        "hif-schema-sha256": HIF_SCHEMA_SHA256,
        "hif-schema-doi": "10.5281/zenodo.17257719",
        "hif-roles-version": "1.0.0",
        "hif-roles-vocabulary": f'{schema.doc["id"]}/{schema.doc["version"]}',
        "khg-profile": "khg-hif/1.0.0",
        "khg-record": hdr["khg"],
        "khg-schema": f'{schema.doc["id"]}/{schema.doc["version"]}',
        "khg-schema-sha256": schema.sha256(),
        "khg-document-id": hdr["document_id"],
        "khg-snapshot": hdr.get("snapshot", "current"),
        "khg-complete": hdr.get("complete", True),
    }
    ordered_nodes = [nodes[k] for k in sorted(nodes, key=lambda i: (i.startswith("_:"), i))]
    return {"network-type": "directed" if directed else "undirected", "metadata": md,
            "nodes": ordered_nodes, "edges": erecs, "incidences": incidences}


def hif_to_c1(hif, schema: Schema):
    md = hif["metadata"]
    if md.get("khg-profile") != "khg-hif/1.0.0":
        raise KHGError("KHG-P001", "not a khg-hif/1.0.0 document")
    if md.get("khg-schema-sha256") != schema.sha256():
        raise KHGError("KHG-D009", "schema hash mismatch")
    directed = hif.get("network-type") == "directed"
    node = {}
    for n in hif["nodes"]:
        if n["node"] in node:
            raise KHGError("KHG-D001", f"duplicate node {n['node']!r}")
        node[n["node"]] = n.get("attrs", {})
    recs = []
    for nid, a in node.items():
        if a["khg:kind"] == "entity":
            e = {"kind": "entity", "id": nid}
            for f, k in ENTITY_FIELDS:
                if k in a:
                    e[f] = copy.deepcopy(a[k])
            recs.append(e)
        elif a["khg:kind"] == "literal":
            if literal_node_id(a["khg:literal"]) != nid:
                raise KHGError("KHG-D005", f"literal node id {nid!r} does not match its value")
        elif a["khg:kind"] == "fact-ref":
            if ref_node_id(a["khg:ref"]) != nid:
                raise KHGError("KHG-D005", f"fact-ref node id {nid!r} does not match its ref")
    by_edge = {}
    for er in hif["edges"]:
        if er["edge"] in by_edge:
            raise KHGError("KHG-D001", f"duplicate edge {er['edge']!r}")
        r = {"id": er["edge"]}
        for f, k in EDGE_FIELDS:
            if k in er.get("attrs", {}):
                r[f] = copy.deepcopy(er["attrs"][k])
        if "weight" in er:
            r.setdefault("extensions", {})["hif:weight"] = er["weight"]
        r["bindings"] = []
        by_edge[er["edge"]] = r
    for inc in hif["incidences"]:
        r = by_edge.get(inc["edge"])
        if r is None:
            raise KHGError("KHG-D003", f"incidence names undeclared edge {inc['edge']!r}")
        if inc["node"] not in node:
            raise KHGError("KHG-D002", f"incidence names undeclared node {inc['node']!r}")
        a = inc["attrs"]
        na = node[inc["node"]]
        k = na["khg:kind"]
        if k == "entity":
            v = {"entity": inc["node"]}
        elif k == "literal":
            v = {"literal": copy.deepcopy(na["khg:literal"])}
        elif k == "fact-ref":
            v = {"fact": na["khg:ref"]}
        elif k in ("somevalue", "novalue"):
            if special_node_id(k, r["id"], a["khg:bid"]) != inc["node"]:
                raise KHGError("KHG-D005", "special node id mismatch")
            v = {"special": k}
        elif k == "unbound":
            if special_node_id("unbound", r["id"], a["khg:bid"]) != inc["node"]:
                raise KHGError("KHG-D005", "unbound node id mismatch")
            v = {"unbound": copy.deepcopy(na["khg:unbound"])}
        else:
            raise KHGError("KHG-P013", f"node kind {k!r}")
        b = {"bid": a["khg:bid"], "role": a["role"], "value": v}
        if "role-position" in a:
            b["position"] = a["role-position"]
        d = inc.get("direction") if directed else a.get("khg:direction")
        declared = schema.usage(r["relation"], a["role"]).get("direction")
        if declared is not None and d is not None and d != declared:
            raise KHGError("KHG-S016", f"direction {d!r} contradicts declared {declared!r}")
        if declared is None and d is not None:
            b["direction"] = d
        r["bindings"].append(b)
    recs.extend(by_edge.values())
    hdr = {"kind": "header", "khg": md["khg-record"], "document_id": md["khg-document-id"],
           "schema": {"id": md["khg-schema"].rsplit("/", 1)[0], "version": md["khg-schema"].rsplit("/", 1)[1], "sha256": md["khg-schema-sha256"]},
           "snapshot": md.get("khg-snapshot", "current"), "complete": md.get("khg-complete", True)}
    return {"header": hdr, "records": recs}


# ----------------------------------------------------------------------------------------------
# Canonical form of a C1 document (for structural comparison)
# ----------------------------------------------------------------------------------------------


def canonical_doc(doc, schema: Schema):
    recs = []
    for r in doc["records"]:
        r = copy.deepcopy(r)
        if r["kind"] == "entity":
            recs.append(r)
            continue
        r.setdefault("rank", "normal")
        r.setdefault("visibility", "visible")
        for b in r["bindings"]:
            b["value"] = canon_value(b["value"])
        r["bindings"].sort(key=bsortkey)
        for ev in r.get("evidence", []):
            ev.setdefault("supports", sorted(b["bid"] for b in r["bindings"]))
        r.setdefault("evidence", [])
        r["evidence"].sort(key=lambda e: e["id"])
        r["derived"] = derived(schema, r)
        for ev in r["evidence"]:
            if ev["type"] == "extracted" and r["kind"] in ("fact", "rule"):
                ev["event_hash"] = event_hash(r["derived"]["content_key"], ev)
        recs.append(r)
    order = {"entity": 0, "fact": 1, "rule": 1, "goal": 2, "meta": 3}
    recs.sort(key=lambda r: (order[r["kind"]], r["id"], r.get("version", 0)))
    h = {k: v for k, v in doc["header"].items() if k in ("kind", "khg", "document_id", "schema", "snapshot", "complete")}
    return {"header": h, "records": recs}
