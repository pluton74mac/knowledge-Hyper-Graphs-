"""Synthesis prototype for DESIGN.md (P2), revised after the critique. Scratch code, not the package.

What it covers (each item names the DESIGN section it prototypes):
- strict JSON (layer J) and canonical JSON with RFC 8785 number serialisation (§2.1, §2.9);
- time literals: Wikidata precision windows 0-14 (ordinal centuries and millennia, BCE in historical numbering,
  no year 0), Julian and Gregorian calendars on the proleptic Gregorian line, and the as_of instant grammar (§2.6);
- value identity (a time literal is its Gregorian window plus its precision), value and fact refinement (§2.3, §2.9);
- the bound table: definite and possible validity for every combination of literal, somevalue, novalue and absent
  bounds; relation time models interval, invariant and timeless (§2.6);
- derived fields, the four identifiers, event_hash stored at extraction (§2.4, §2.9);
- the key invariant, collision shapes, classes and actions, and the disputed-key rule (§2.5);
- the HIF codec: C1 <-> role-aware HIF with binding extensions, weights on nodes, edges and incidences, shared or
  per-binding literal nodes, an inlined schema, and closed slices (§4).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata

# ---------------------------------------------------------------------------------------------
# Errors, strict JSON (layer J)
# ---------------------------------------------------------------------------------------------


class KHGError(ValueError):
    def __init__(self, code, msg, info=None):
        super().__init__(f"{code}: {msg}")
        self.code = code
        self.info = info or {}


MAX_SAFE = 2 ** 53 - 1


def strict_loads(text: str):
    """Layer J: empty input, BOM, duplicate keys, NaN/Infinity, lone surrogates, unsafe integers, non-object top."""
    if text.startswith("﻿"):
        raise KHGError("KHG-J002", "byte-order mark")
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

    def pint(s):
        v = int(s)
        if abs(v) > MAX_SAFE:
            raise KHGError("KHG-J006", f"integer {s} outside +-(2^53-1)")
        return v

    try:
        obj = json.loads(text, object_pairs_hook=pairs, parse_constant=const, parse_int=pint)
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
    if not isinstance(obj, dict):
        raise KHGError("KHG-J007", "top level is not an object")
    return obj


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------------------------------------
# Canonical JSON: code-point key order, no white space, NFC strings, RFC 8785 numbers
# ---------------------------------------------------------------------------------------------


def es_number(x) -> str:
    """ECMAScript Number::toString, which RFC 8785 section 3.2.2.3 prescribes for JSON numbers."""
    if isinstance(x, bool):
        raise TypeError("bool is not a number")
    if isinstance(x, int):
        return str(x)
    if x != x or x in (float("inf"), float("-inf")):
        raise KHGError("KHG-J004", "non-finite number")
    if x == 0:
        return "0"  # also -0
    if x < 0:
        return "-" + es_number(-x)
    r = repr(x)  # shortest round-trip digits, the same digit string ECMAScript selects
    mant, _, exp = r.lower().partition("e")
    exp = int(exp) if exp else 0
    ip, _, fp = mant.partition(".")
    digits = (ip + fp).lstrip("0")
    e = exp - len(fp)  # value = int(digits) * 10**e
    while digits.endswith("0"):
        digits = digits[:-1]
        e += 1
    k = len(digits)
    n = k + e  # value = 0.d1..dk * 10**n
    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + digits
    e1 = n - 1
    sign = "+" if e1 >= 0 else "-"
    return (digits if k == 1 else digits[0] + "." + digits[1:]) + "e" + sign + str(abs(e1))


def _cj(o, out):
    if o is None:
        out.append("null")
    elif o is True:
        out.append("true")
    elif o is False:
        out.append("false")
    elif isinstance(o, (int, float)):
        out.append(es_number(o))
    elif isinstance(o, str):
        out.append(json.dumps(nfc(o), ensure_ascii=False))
    elif isinstance(o, (list, tuple)):
        out.append("[")
        for i, x in enumerate(o):
            if i:
                out.append(",")
            _cj(x, out)
        out.append("]")
    elif isinstance(o, dict):
        items = {}
        for k, v in o.items():
            nk = nfc(k)
            if nk in items:
                raise KHGError("KHG-S020", f"two keys normalise to {nk!r}")
            items[nk] = v
        out.append("{")
        for i, k in enumerate(sorted(items)):  # code-point order
            if i:
                out.append(",")
            out.append(json.dumps(k, ensure_ascii=False))
            out.append(":")
            _cj(items[k], out)
        out.append("}")
    else:
        raise TypeError(f"not JSON: {type(o).__name__}")


def cjson(o) -> str:
    out = []
    _cj(o, out)
    return "".join(out)


def digest(domain: str, payload, n: int | None = None) -> str:
    d = hashlib.sha256((domain + "\n" + cjson(payload)).encode("utf-8")).hexdigest()
    return d[:n] if n else "sha256:" + d


def container_sha256(doc) -> str:
    """sha256 of the canonical .khg.jsonl serialisation (header line, then records in canonical order)."""
    c = canonical_doc(doc)
    text = "".join(cjson(x) + "\n" for x in [c["header"]] + c["records"])
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------
# Calendars, instants and precision windows (DESIGN §2.6)
# ---------------------------------------------------------------------------------------------

TIME_RE = re.compile(r"^([+-])(\d{4,})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$")
INSTANT_RE = TIME_RE
DEC_RE = re.compile(r"^(\+0|[+-](0\.[0-9]*[1-9]|[1-9][0-9]*(\.[0-9]*[1-9])?))$")
NEG_INF = float("-inf")
POS_INF = float("inf")
DAY = 86400
JULIAN_BEFORE = 1583  # a time literal whose written year is before 1583 must state its calendar (Wikidata's boundary)


def _leap(y, cal):
    if cal == "julian":
        return y % 4 == 0
    return (y % 4 == 0 and y % 100 != 0) or y % 400 == 0


def _dim(y, m, cal="gregorian"):
    if m == 2:
        return 29 if _leap(y, cal) else 28
    return 31 if m in (1, 3, 5, 7, 8, 10, 12) else 30


def jdn_gregorian(y, m, d):
    """Julian day number of a proleptic Gregorian date; astronomical year (0 = 1 BCE); floor division throughout."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def jdn_julian(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083


def gregorian_from_jdn(j):
    a = j + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def astro(y_hist):
    """Historical year numbering (no year 0, -1 = 1 BCE) to astronomical (0 = 1 BCE)."""
    return y_hist + 1 if y_hist < 0 else y_hist


def _sec(y_astro, m, d, hh=0, mi=0, ss=0, cal="gregorian"):
    j = jdn_julian(y_astro, m, d) if cal == "julian" else jdn_gregorian(y_astro, m, d)
    return j * DAY + hh * 3600 + mi * 60 + ss


def fmt_instant(t):
    """An instant (seconds on the proleptic Gregorian line) in the as_of grammar; None for an unbounded end."""
    if t in (NEG_INF, POS_INF):
        return None
    t = int(t)
    j, s = divmod(t, DAY)
    y, m, d = gregorian_from_jdn(j)
    hh, rem = divmod(s, 3600)
    mi, ss = divmod(rem, 60)
    sign = "-" if y < 0 else "+"
    return f"{sign}{abs(y):04d}-{m:02d}-{d:02d}T{hh:02d}:{mi:02d}:{ss:02d}Z"


def parse_instant(s):
    """The as_of grammar: a full proleptic-Gregorian date-time, astronomical years, UTC, no precision or calendar."""
    m = INSTANT_RE.match(s or "")
    if not m:
        raise KHGError("KHG-C011", f"as_of instant {s!r} is not [+-]YYYY-MM-DDThh:mm:ssZ")
    sign, Y, M, D, hh, mi, ss = m.groups()
    y = int(Y) * (-1 if sign == "-" else 1)
    if sign == "-" and int(Y) == 0:
        raise KHGError("KHG-C011", "write year 0 as +0000")
    M, D, hh, mi, ss = int(M), int(D), int(hh), int(mi), int(ss)
    if not (1 <= M <= 12 and 1 <= D <= _dim(y, M) and hh < 24 and mi < 60 and ss < 60):
        raise KHGError("KHG-C011", f"as_of instant {s!r} is not a calendar date-time")
    return _sec(y, M, D, hh, mi, ss)


def parse_time(value: str, precision: int, cal: str | None):
    """Wikibase lexical form: sign, historical year (no year 0), components below the precision zero (S006)."""
    m = TIME_RE.match(value)
    if not m:
        raise KHGError("KHG-C004", f"time lexical form {value!r}")
    sign, Y, M, D, hh, mm, ss = m.groups()
    y = int(Y) * (-1 if sign == "-" else 1)
    if int(Y) == 0:
        raise KHGError("KHG-S006", "year 0 does not exist in historical numbering (1 BCE is -0001)")
    M, D, hh, mm, ss = int(M), int(D), int(hh), int(mm), int(ss)
    if not isinstance(precision, int) or not 0 <= precision <= 14:
        raise KHGError("KHG-C004", f"precision {precision}")
    if cal is None and y < JULIAN_BEFORE:
        raise KHGError("KHG-S006", f"a date before {JULIAN_BEFORE} must state its calendar")
    cal = cal or "gregorian"
    need = {"M": precision >= 10, "D": precision >= 11, "h": precision >= 12, "m": precision >= 13, "s": precision >= 14}
    for name, val, ok, rng in (("M", M, need["M"], (1, 12)), ("D", D, need["D"], None), ("h", hh, need["h"], (0, 23)),
                               ("m", mm, need["m"], (0, 59)), ("s", ss, need["s"], (0, 59))):
        if not ok and val != 0:
            raise KHGError("KHG-S006", f"{name} set below precision in {value!r}")
        if ok and rng and not rng[0] <= val <= rng[1]:
            raise KHGError("KHG-S006", f"{name} out of range in {value!r}")
    if need["D"] and not 1 <= D <= _dim(astro(y), M, cal):
        raise KHGError("KHG-S006", f"day out of range in {value!r}")
    return y, M, D, hh, mm, ss


def time_window(lit):
    """[lo, hi): the instants a time literal may denote, as seconds on the proleptic Gregorian line.

    p >= 10: the calendar unit (month, day, hour, minute, second) in the literal's calendar.
    p = 9: the calendar year. p = 8 and p <= 5: blocks of 10**(9-p) years, floored on the astronomical year.
    p = 7 and p = 6: ordinal centuries and millennia (Wikidata: 1801-1900 at p7 is the 19th century); BCE years use
    the same ordinal reading on the historical year (100 BCE is in the 1st century BCE), then become astronomical.
    """
    p = lit["precision"]
    cal = lit.get("calendar")
    y, M, D, hh, mm, ss = parse_time(lit["time"], p, cal)
    cal = cal or "gregorian"
    a = astro(y)
    if p >= 11:
        unit = {11: DAY, 12: 3600, 13: 60, 14: 1}[p]
        lo = _sec(a, M, D, hh if p >= 12 else 0, mm if p >= 13 else 0, ss if p >= 14 else 0, cal)
        return lo, lo + unit
    if p == 10:
        lo = _sec(a, M, 1, cal=cal)
        hi = _sec(a + 1, 1, 1, cal=cal) if M == 12 else _sec(a, M + 1, 1, cal=cal)
        return lo, hi
    if p == 9:
        return _sec(a, 1, 1, cal=cal), _sec(a + 1, 1, 1, cal=cal)
    if p in (7, 6):
        u = 100 if p == 7 else 1000
        if y > 0:
            c = -(-y // u)                      # ordinal: ceil(y / u)
            first, last = u * c - (u - 1), u * c  # historical CE years
            return _sec(first, 1, 1, cal=cal), _sec(last + 1, 1, 1, cal=cal)
        n = -y                                  # years BCE
        c = -(-n // u)
        earliest, latest = u * c, u * c - (u - 1)  # n BCE values
        return _sec(astro(-earliest), 1, 1, cal=cal), _sec(astro(-latest) + 1, 1, 1, cal=cal)
    u = 10 ** (9 - p)                           # p = 8 (decade) and p <= 5
    b = (a // u) * u
    return _sec(b, 1, 1, cal=cal), _sec(b + u, 1, 1, cal=cal)


def canon_literal(lit: dict) -> dict:
    """The literal's canonical *written* form: defaults filled, strings NFC, language tags lower case."""
    lit = copy.deepcopy(lit)
    dt = lit.get("datatype")
    if dt == "time":
        if "calendar" in lit and lit["calendar"] not in ("gregorian", "julian"):
            raise KHGError("KHG-C004", "calendar must be gregorian or julian")
        parse_time(lit["time"], lit["precision"], lit.get("calendar"))
        lit.setdefault("calendar", "gregorian")
    elif dt == "quantity":
        if "unit" not in lit:
            raise KHGError("KHG-C004", "quantity without unit")
        for k in ("amount", "lower", "upper"):
            if k in lit and not (isinstance(lit[k], str) and DEC_RE.match(lit[k])):
                raise KHGError("KHG-C004", f"decimal {lit[k]!r}")
        if ("lower" in lit) != ("upper" in lit):
            raise KHGError("KHG-C004", "bounds come in pairs")
    elif dt in ("string", "iri"):
        lit["value"] = nfc(lit["value"])
    elif dt == "lang_string":
        lit["value"] = nfc(lit["value"])
        lit["lang"] = lit["lang"].lower()
    elif dt == "boolean":
        if not isinstance(lit.get("value"), bool):
            raise KHGError("KHG-C004", "boolean value")
    elif dt == "geo":
        for k in ("lat", "lon", "precision"):
            if not (isinstance(lit.get(k), str) and DEC_RE.match(lit[k])):
                raise KHGError("KHG-C004", f"geo {k}")
    else:
        raise KHGError("KHG-C002", f"datatype {dt!r}")
    return lit


def literal_identity(lit: dict) -> dict:
    """What equality, hashing and refinement compare. A time literal is its Gregorian window plus its precision,
    so the Julian and Gregorian writings of one day are equal; every other literal is its canonical form."""
    c = canon_literal(lit)
    if c["datatype"] != "time":
        return c
    lo, hi = time_window(c)
    return {"datatype": "time", "window": [fmt_instant(lo), fmt_instant(hi)], "precision": c["precision"]}


def lit_label(lit):
    dt = lit["datatype"]
    if dt == "time":
        cal = "" if lit.get("calendar", "gregorian") == "gregorian" else " (Julian)"
        return f'{lit["time"]}/{lit["precision"]}{cal}'
    if dt == "quantity":
        s = lit["amount"] + ("" if lit["unit"] == "1" else " " + lit["unit"])
        return s + (f' [{lit["lower"]}, {lit["upper"]}]' if "lower" in lit else "")
    if dt == "lang_string":
        return f'{lit["value"]}@{lit["lang"]}'
    if dt == "geo":
        return f'{lit["lat"]},{lit["lon"]}'
    return str(lit["value"]).lower() if dt == "boolean" else lit["value"]


# ---------------------------------------------------------------------------------------------
# Schema access (khg-relation-schema/1.0.0)
# ---------------------------------------------------------------------------------------------

BUILTIN = {
    "khg:supersedes": {"id": "khg:supersedes", "kind": "lifecycle",
                       "reasons": ["correction", "duplicate", "refinement", "conflation", "schema_migration", "other"],
                       "roles": [{"role": "khg:superseding", "slot": "core", "fillers": [{"fact": []}], "min": 1,
                                  "max": None, "direction": "tail"},
                                 {"role": "khg:superseded", "slot": "core", "fillers": [{"fact": []}], "min": 1,
                                  "max": None, "direction": "head"}]},
    "khg:retracts": {"id": "khg:retracts", "kind": "lifecycle", "reasons": ["withdrawn", "unsupported", "other"],
                     "roles": [{"role": "khg:retracted", "slot": "core", "fillers": [{"fact": []}], "min": 1,
                                "max": None, "direction": "head"}]},
    "khg:disputes": {"id": "khg:disputes", "kind": "lifecycle",
                     "reasons": ["key_conflict", "negation_conflict", "curator", "other"],
                     "roles": [{"role": "khg:disputed", "slot": "core", "fillers": [{"fact": []}], "min": 2,
                                "max": None, "direction": "head"}]},
}
END_CAUSE = {"role": "khg:end_cause", "slot": "meta", "fillers": [{"entity": []}, {"literal": "string"}],
             "min": 0, "max": 1, "direction": "tail"}


class Schema:
    def __init__(self, doc):
        self.doc = doc
        self.rel = {r["id"]: r for r in doc["relations"]}
        self.rel.update(BUILTIN)
        self.default_time = doc.get("default_time", {"model": "timeless"})
        self.types = {t["id"]: t.get("parents", []) for t in doc.get("entity_types", [])}

    def kind(self, rel):
        return self.rel[rel].get("kind", "fact")

    def usages(self, rel):
        us = list(self.rel[rel]["roles"])
        if self.time_model(rel)["model"] == "interval" and all(u["role"] != "khg:end_cause" for u in us):
            us.append(END_CAUSE)  # built in on every relation with an interval time model (P1534)
        return us

    def usage(self, rel, role):
        if rel not in self.rel:
            raise KHGError("KHG-S001", f"relation {rel!r} not declared")
        for u in self.usages(rel):
            if u["role"] == role:
                return u
        raise KHGError("KHG-S002", f"role {role!r} not allowed for {rel!r}")

    def time_model(self, rel):
        r = self.rel[rel]
        if r.get("kind") == "lifecycle":
            return {"model": "timeless"}
        return r.get("time", self.default_time)

    def key(self, rel):
        return self.rel[rel].get("key")

    def ref(self):
        return f'{self.doc["id"]}/{self.doc["version"]}'

    def sha256(self):
        return digest("khg-schema/1", self.doc)

    def is_subtype(self, t, want):
        seen, stack = set(), [t]
        while stack:
            x = stack.pop()
            if x == want:
                return True
            if x in seen:
                continue
            seen.add(x)
            stack.extend(self.types.get(x, []))
        return False


def schema_problems(doc):
    """A few M-layer checks (prototype): M003, M010, M011, M015 (severity enum), M017 (supersede on a temporal key)."""
    out = []
    for r in doc.get("relations", []):
        usages = {u["role"]: u for u in r.get("roles", [])}
        for c in r.get("constraints", []) or []:
            if c.get("severity") not in ("error", "warning"):
                out.append(("KHG-M015", f"{r['id']}: constraint severity {c.get('severity')!r}"))
        k = r.get("key")
        if k:
            for role in k.get("roles", []):
                if role not in usages or usages[role]["slot"] not in ("core", "qualifier"):
                    out.append(("KHG-M003", f"{r['id']}: key role {role!r}"))
            tm = r.get("time", doc.get("default_time", {"model": "timeless"}))
            if k.get("temporal") and tm.get("model") != "interval":
                out.append(("KHG-M011", f"{r['id']}: temporal key without an interval time model"))
            if k.get("temporal") and k.get("on_collision") == "supersede":
                out.append(("KHG-M017", f"{r['id']}: on_collision supersede on a temporal key"))
        for u in r.get("roles", []):
            if u.get("max") is not None and u["max"] < u.get("min", 0):
                out.append(("KHG-M010", f"{r['id']}.{u['role']}: max < min"))
    return out


# ---------------------------------------------------------------------------------------------
# Values, canonical binding order, value identity and refinement (§2.3, §2.9)
# ---------------------------------------------------------------------------------------------


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


def value_identity(v):
    k = vkind(v)
    if k == "literal":
        return {"literal": literal_identity(v["literal"])}
    return canon_value(v)


def values_equal(a, b):
    return cjson(value_identity(a)) == cjson(value_identity(b))


def eff_dir(schema: Schema, rec, b):
    u = schema.usage(rec["relation"], b["role"])
    return b.get("direction") or u.get("direction")


def bsortkey(b):
    return (b["role"], b.get("position", 0), cjson(canon_value(b["value"])))


def _dec(s):
    from decimal import Decimal
    return Decimal(s)


def value_refines(v2, v1) -> bool:
    """v2 refines v1 (v2 is at least as specific and says nothing v1 excludes)."""
    k1, k2 = vkind(v1), vkind(v2)
    if values_equal(v1, v2):
        return True
    if (k1 == "special" and v1["special"] == "somevalue") or k1 == "unbound":
        return k2 in ("entity", "literal", "fact")
    if k1 != "literal" or k2 != "literal":
        return False
    a, b = canon_literal(v1["literal"]), canon_literal(v2["literal"])
    if a["datatype"] != b["datatype"]:
        return False
    if a["datatype"] == "time":
        lo1, hi1 = time_window(a)
        lo2, hi2 = time_window(b)
        return lo1 <= lo2 and hi2 <= hi1 and b["precision"] >= a["precision"]
    if a["datatype"] == "quantity":
        if a["unit"] != b["unit"]:
            return False
        i1 = (_dec(a.get("lower", a["amount"])), _dec(a.get("upper", a["amount"])))
        i2 = (_dec(b.get("lower", b["amount"])), _dec(b.get("upper", b["amount"])))
        return i1[0] <= i2[0] and i2[1] <= i1[1] and i1 != i2
    if a["datatype"] == "geo":
        if a.get("globe") != b.get("globe") or _dec(b["precision"]) >= _dec(a["precision"]):
            return False
        half = _dec(a["precision"]) / 2
        return abs(_dec(b["lat"]) - _dec(a["lat"])) <= half and abs(_dec(b["lon"]) - _dec(a["lon"])) <= half
    return False


def _match(pairs_ok, n1, n2):
    """Is there an injective map from range(n1) into range(n2) with pairs_ok(i, j)? (small sizes)"""
    used = [False] * n2

    def go(i):
        if i == n1:
            return True
        for j in range(n2):
            if not used[j] and pairs_ok(i, j):
                used[j] = True
                if go(i + 1):
                    return True
                used[j] = False
        return False
    return go(0)


def fact_refines(schema, f2, f1) -> bool:
    """f2 refines f1: same relation; every core, qualifier and time binding of f1 has a refining binding of f2 of the
    same role (and position, for ordered roles), matched injectively; complete roles keep their size; novalue only
    refines novalue. Meta bindings are ignored."""
    if f1["relation"] != f2["relation"]:
        return False
    rel = f1["relation"]
    roles = {}
    for which, f in ((0, f1), (1, f2)):
        for b in f["bindings"]:
            u = schema.usage(rel, b["role"])
            if u["slot"] == "meta":
                continue
            roles.setdefault(b["role"], ([], []))[which].append(b)
    for role, (bs1, bs2) in roles.items():
        u = schema.usage(rel, role)
        nv1 = any(vkind(b["value"]) == "special" and b["value"]["special"] == "novalue" for b in bs1)
        nv2 = any(vkind(b["value"]) == "special" and b["value"]["special"] == "novalue" for b in bs2)
        if nv1 != nv2 and (nv1 or bs1):
            return False
        if u.get("complete") and len(bs1) != len(bs2):
            return False

        def ok(i, j):
            b1, b2 = bs1[i], bs2[j]
            if u.get("ordered") and b1.get("position") != b2.get("position"):
                return False
            return value_refines(b2["value"], b1["value"])
        if not _match(ok, len(bs1), len(bs2)):
            return False
    return True


# ---------------------------------------------------------------------------------------------
# Derived fields and the bound table (§2.4, §2.6, §2.9)
# ---------------------------------------------------------------------------------------------

COUNTED_KINDS = ("entity", "literal", "fact", "special:somevalue")


def _vk(v):
    k = vkind(v)
    return "special:" + v["special"] if k == "special" else k


def slot_of(schema, rec, b):
    return schema.usage(rec["relation"], b["role"])["slot"]


def content_bindings(schema, rec, slots=("core", "qualifier", "time")):
    return [b for b in rec["bindings"] if slot_of(schema, rec, b) in slots]


def binding_tuple(b):
    return [b["role"], b.get("position"), value_identity(b["value"])]


def _bound(rec, role):
    for b in rec["bindings"]:
        if b["role"] == role:
            v = b["value"]
            k = vkind(v)
            if k == "literal":
                return ("literal", time_window(v["literal"]))
            if k == "special":
                return (v["special"], None)
            return ("other", None)
    return ("absent", None)


def bounds(schema, rec):
    """The bound table. Returns kind and the instants s_lo, s_hi, e_lo, e_hi (seconds or +-inf):
    definite validity is [s_hi, e_lo), possible validity is [s_lo, e_hi)."""
    tm = schema.time_model(rec["relation"])
    if tm["model"] in ("invariant", "timeless"):
        return {"kind": tm["model"], "s_lo": NEG_INF, "s_hi": NEG_INF, "e_lo": POS_INF, "e_hi": POS_INF}
    st, sw = _bound(rec, tm["start"])
    et, ew = _bound(rec, tm["end"])
    # end first: a literal window; novalue or absent = still holding (+inf); somevalue = ended at an unknown time
    if et == "literal":
        e_lo, e_hi = ew
    elif et in ("novalue", "absent"):
        e_lo = e_hi = POS_INF
    else:  # somevalue: after the start, unknown when
        e_lo, e_hi = None, POS_INF
    if st == "literal":
        s_lo, s_hi = sw
    elif st == "novalue":  # held since forever
        s_lo = s_hi = NEG_INF
    else:  # absent or somevalue: started at an unknown time before the end
        s_lo, s_hi = NEG_INF, e_hi
    if e_lo is None:
        e_lo = s_lo
    if st == "literal" and et == "literal":
        kind = "period"
    elif st == "literal" and et in ("absent", "novalue"):
        kind = "since"
    elif st == "literal":
        kind = "ended"
    elif et == "literal":
        kind = "until"
    else:
        kind = "undated"
    return {"kind": kind, "s_lo": s_lo, "s_hi": s_hi, "e_lo": e_lo, "e_hi": e_hi}


def _iv(lo, hi):
    return [fmt_instant(lo), fmt_instant(hi)]


def valid_time_view(schema, rec):
    tm = schema.time_model(rec["relation"])
    b = bounds(schema, rec)
    out = {"kind": b["kind"]}
    if tm["model"] == "interval":
        for x in rec["bindings"]:
            if x["role"] == tm["start"]:
                out["start"] = canon_value(x["value"])
            if x["role"] == tm["end"]:
                out["end"] = canon_value(x["value"])
    out["definite"] = _iv(b["s_hi"], b["e_lo"]) if b["s_hi"] < b["e_lo"] else None
    out["possible"] = _iv(b["s_lo"], b["e_hi"])
    return out


def key_digest(schema, rec):
    key = schema.key(rec["relation"])
    if not key:
        return None
    kb = [b for b in rec["bindings"] if b["role"] in key["roles"]]
    if {b["role"] for b in kb} != set(key["roles"]):
        return None  # incomplete key: exempt from collisions
    if any(vkind(b["value"]) not in ("entity", "literal", "fact") for b in kb):
        return None  # special or unbound value in a key role: exempt
    return digest("khg-key-digest/1", {"relation": rec["relation"],
                                       "bindings": sorted((binding_tuple(b) for b in kb), key=cjson)})


def content_key(schema, rec):
    return digest("khg-content-key/1", {"relation": rec["relation"],
                                        "bindings": sorted((binding_tuple(b) for b in content_bindings(schema, rec)),
                                                           key=cjson)})


def core_key(schema, rec):
    return digest("khg-core-key/1", {"relation": rec["relation"],
                                     "bindings": sorted((binding_tuple(b) for b in content_bindings(schema, rec, ("core",))),
                                                        key=cjson)})


EVENT_TYPES = ("extracted", "inferred")


def event_hash(content_key_value, ev):
    """khg-event/1, computed once at extraction over the candidate's content key and stored in the evidence record."""
    act = ev.get("activity", {})
    payload = {
        "content_key": content_key_value,
        "doc": ev["source"].get("doc_sha256") or ev["source"]["doc_id"],
        "selectors": sorted(cjson(x) for x in ev.get("selectors", [])),
        "activity": {k: act[k] for k in ("agent", "agent_version", "model", "model_version", "prompt_id", "skill_id")
                     if k in act},
    }
    if ev.get("reference"):
        payload["reference"] = sorted(cjson(x) for x in ev["reference"])
    if ev.get("inference"):
        payload["inference"] = ev["inference"]
    return digest("khg-event/1", payload)


def stamp_event_hashes(schema, rec):
    """What make_candidate does: event_hash on every extracted or inferred evidence record, from this content key."""
    ck = content_key(schema, rec)
    for e in rec.get("evidence", []):
        if e["type"] in EVENT_TYPES and "event_hash" not in e:
            e["event_hash"] = event_hash(ck, e)
    return rec


def derived(schema, rec):
    if rec["kind"] != "hyperedge":
        return {}
    if rec["status"] == "goal":
        nb = sum(1 for b in rec["bindings"] if vkind(b["value"]) != "unbound")
        return {"n_bound": nb, "n_unbound": len(rec["bindings"]) - nb}
    if schema.kind(rec["relation"]) == "lifecycle":
        return {}
    cb = content_bindings(schema, rec)
    valued = [b for b in cb if _vk(b["value"]) in COUNTED_KINDS]
    counted = [b for b in valued if slot_of(schema, rec, b) in ("core", "qualifier")]
    timed = [b for b in valued if slot_of(schema, rec, b) == "time"]
    core = [b for b in counted if slot_of(schema, rec, b) == "core"]
    distinct, sv = set(), 0
    for b in counted:
        if _vk(b["value"]) == "special:somevalue":
            sv += 1
        else:
            distinct.add(cjson(value_identity(b["value"])))
    return {
        "arity": len(counted),
        "core_arity": len(core),
        "statement_arity": len(counted) + len(timed),
        "distinct_fillers": len(distinct) + sv,
        "content_key": content_key(schema, rec),
        "core_key": core_key(schema, rec),
        "key_digest": key_digest(schema, rec),
        "valid_time": valid_time_view(schema, rec),
    }


# ---------------------------------------------------------------------------------------------
# The key invariant, collision shapes, classes and actions (§2.5)
# ---------------------------------------------------------------------------------------------


def definite_overlap(a, b):
    return max(a["s_hi"], b["s_hi"]) < min(a["e_lo"], b["e_lo"])


def possible_overlap(a, b):
    return max(a["s_lo"], b["s_lo"]) < min(a["e_hi"], b["e_hi"])


def _keyed(schema, records, statuses=("asserted",)):
    by = {}
    for r in records:
        if r.get("kind") != "hyperedge" or r["status"] not in statuses or r.get("rank", "normal") == "deprecated":
            continue
        if schema.kind(r["relation"]) == "lifecycle":
            continue
        k = key_digest(schema, r)
        if k:
            by.setdefault((r["relation"], k), []).append(r)
    return by


def key_invariant_violations(schema, records):
    """KHG-D016 over a set of records: facts with status asserted, rank other than deprecated, same relation and
    non-null key_digest. At every instant of their definite validity (every instant, for a non-temporal key) at most
    one holds, or exactly one of those holding is preferred. Returns the offending groups as sorted id lists."""
    out = []
    for (rel, k), rs in sorted(_keyed(schema, records).items()):
        if not schema.key(rel).get("temporal"):
            groups = [rs]
        else:
            iv = {r["id"]: bounds(schema, r) for r in rs}
            points = sorted({v["s_hi"] for v in iv.values()})
            groups = [[r for r in rs if iv[r["id"]]["s_hi"] <= p < iv[r["id"]]["e_lo"]] for p in points]
        for g in groups:
            if len(g) > 1 and sum(1 for r in g if r.get("rank") == "preferred") != 1:
                ids = sorted(r["id"] for r in g)
                if ids not in out:
                    out.append(ids)
    return out


def possible_only_overlaps(schema, records):
    """Pairs on a temporal key that possibly but not definitely overlap: store warning / lint KHG-L008."""
    out = []
    for (rel, k), rs in sorted(_keyed(schema, records).items()):
        if not schema.key(rel).get("temporal"):
            continue
        iv = {r["id"]: bounds(schema, r) for r in rs}
        ids = sorted(iv)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if possible_overlap(iv[a], iv[b]) and not definite_overlap(iv[a], iv[b]):
                    out.append([a, b])
    return out


def classify(schema, incoming, stored):
    """Class of a conflict, from the normative refinement order: duplicate, refines, generalises or distinct."""
    if content_key(schema, incoming) == content_key(schema, stored):
        return "duplicate"
    if fact_refines(schema, incoming, stored):
        return "refines"
    if fact_refines(schema, stored, incoming):
        return "generalises"
    return "distinct"


def shape(schema, incoming, stored):
    """Temporal-key conflict shapes: succession, backfill, same_start, overlap_after_end (None for non-temporal keys)."""
    if not schema.key(incoming["relation"]).get("temporal"):
        return None
    n, s = bounds(schema, incoming), bounds(schema, stored)
    if s["s_hi"] <= n["s_lo"]:
        earlier, which = s, "stored"
    elif n["s_hi"] <= s["s_lo"]:
        earlier, which = n, "incoming"
    else:
        return "same_start"
    if earlier["e_lo"] == POS_INF:  # the earlier fact is still holding (no end, or end novalue)
        return "succession" if which == "stored" else "backfill"
    return "overlap_after_end"


def action_for(policy, cls, shp):
    if cls in ("duplicate", "refines", "generalises"):
        return "merge"
    if policy == "close_older":
        return {"succession": "close_older", "backfill": "close_incoming"}.get(shp, "dispute")
    return policy


def collisions(schema, state, batch, *, post=None, disputed_rule=True):
    """What a write raises as KeyCollision: for each incoming record that breaks the key invariant (or, for a put,
    asserts a fact on a key that has disputed facts at an overlapping instant), its conflicts with shape, class and
    action. state: {id: current record} before the write; batch: the incoming records; post: the whole state after
    the write (defaults to state overlaid with batch). Returns [] when the write is accepted."""
    if post is not None:
        after = dict(post)
    else:
        after = dict(state)
        for r in batch:
            after[r["id"]] = r
    batch_ids = {r["id"] for r in batch}
    groups = key_invariant_violations(schema, list(after.values()))
    out = []
    for r in sorted(batch, key=lambda x: x["id"]):
        if r.get("kind") != "hyperedge" or r.get("status") != "asserted" or schema.kind(r["relation"]) == "lifecycle":
            continue
        kd = key_digest(schema, r)
        if not kd:
            continue
        key = schema.key(r["relation"])
        conflict_ids = sorted({i for g in groups if r["id"] in g for i in g} - {r["id"]})
        policy = key["on_collision"]
        # SEM-09: a new claim on a key with disputed facts joins the dispute
        disputed = [] if not disputed_rule else \
            [x for x in after.values() if x.get("kind") == "hyperedge" and x.get("status") == "disputed"
             and x["id"] != r["id"] and x["relation"] == r["relation"] and key_digest(schema, x) == kd
             and (not key.get("temporal") or definite_overlap(bounds(schema, r), bounds(schema, x)))]
        if not conflict_ids and not disputed:
            continue
        cs = []
        for cid in conflict_ids:
            other = after[cid]
            cls = classify(schema, r, other)
            shp = shape(schema, r, other)
            cs.append({"id": cid, "in_batch": cid in batch_ids, "shape": shp, "class": cls,
                       "action": action_for(policy, cls, shp)})
        for x in sorted(disputed, key=lambda x: x["id"]):
            cls = classify(schema, r, x)
            cs.append({"id": x["id"], "in_batch": x["id"] in batch_ids, "shape": shape(schema, r, x), "class": cls,
                       "action": "merge" if cls != "distinct" else "dispute"})
        out.append({"record": r["id"], "relation": r["relation"], "key_digest": kd,
                    "policy": "dispute" if disputed and not conflict_ids else policy, "conflicts": cs})
    return out


# ---------------------------------------------------------------------------------------------
# Canonical form of a C1 document (derived fields excluded; event_hash is content since extraction)
# ---------------------------------------------------------------------------------------------

ORDER = {"relation-schema": 0, "entity": 1, "hyperedge": 2}
STORE_FIELDS = ("version", "recorded_at", "recorded_by")


def canonical_record(r):
    r = copy.deepcopy(r)
    r.pop("derived", None)
    if r["kind"] != "hyperedge":
        return r
    r.setdefault("rank", "normal")
    r.setdefault("visibility", "visible")
    for b in r["bindings"]:
        b["value"] = canon_value(b["value"])
    r["bindings"].sort(key=bsortkey)
    ev = r.get("evidence", [])
    for e in ev:
        e.setdefault("supports", sorted(b["bid"] for b in r["bindings"]))
        e["supports"] = sorted(e["supports"])
    if ev:
        ev.sort(key=lambda e: e["id"])
    return r


def decision_view(r):
    """What decision_hash covers: the canonical record without store-assigned fields."""
    r = canonical_record(r)
    for f in STORE_FIELDS:
        r.pop(f, None)
    for e in r.get("evidence", []):
        e.pop("recorded_at", None)
    return r


def canonical_doc(doc):
    recs = sorted((canonical_record(r) for r in doc["records"]),
                  key=lambda r: (ORDER[r["kind"]], r.get("id", ""), r.get("version", 0)))
    return {"header": copy.deepcopy(doc["header"]), "records": recs}


def with_derived(doc, schema):
    """Store/export form: canonical records plus the derived cache."""
    out = canonical_doc(doc)
    for r in out["records"]:
        if r["kind"] != "hyperedge":
            continue
        d = derived(schema, r)
        if d:
            r["derived"] = d
    return out


# ---------------------------------------------------------------------------------------------
# HIF codec: C1 document <-> role-aware HIF (role-convention 1.0.0 + khg-hif/1.0.0)
# ---------------------------------------------------------------------------------------------

HIF_SCHEMA_URL = ("https://raw.githubusercontent.com/HIF-org/HIF-standard/"
                  "b691a3d2ec32100c0229ebe1151e9afad015c356/schemas/hif_schema_v0.1.0.json")
HIF_SCHEMA_SHA256 = "639466b7a10de5a734d231d72422f54a5fce4084cb300869012510124c9b2196"
HIF_SCHEMA_ID = "https://raw.githubusercontent.com/pszufe/HIF_validators/main/schemas/hif_schema_v0.1.0.json"

EDGE_FIELDS = [("relation", "relation"), ("status", "khg-status"), ("status_ref", "khg-status-ref"),
               ("rank", "khg-rank"), ("rank_reason", "khg-rank-reason"), ("visibility", "khg-visibility"),
               ("version", "khg-version"), ("recorded_at", "khg-recorded-at"), ("recorded_by", "khg-recorded-by"),
               ("typed_under", "khg-typed-under"), ("evidence", "khg-evidence"), ("confidence", "khg-confidence"),
               ("source_text", "khg-source-text"), ("goal", "khg-goal"), ("reason", "khg-reason"), ("note", "khg-note"),
               ("extensions", "khg-extensions")]
ENTITY_FIELDS = [("label", "label"), ("types", "khg-types"), ("aliases", "khg-aliases"),
                 ("redirect_to", "khg-redirect-to"), ("version", "khg-version"),
                 ("recorded_at", "khg-recorded-at"), ("extensions", "khg-extensions")]
WEIGHT = "hif:weight"
MAX_ID = 512


def literal_node_id(lit):
    return "_:lit:" + digest("khg-literal-node/1", canon_literal(lit), 32)


def literal_binding_node_id(rec_id, bid):
    return "_:litb:" + digest("khg-literal-binding/1", [rec_id, bid], 32)


def special_node_id(kind, rec_id, bid):
    tag = {"somevalue": "sv", "novalue": "nv", "unbound": "var"}[kind]
    return f"_:{tag}:" + digest("khg-special-node/1", [rec_id, bid], 32)


def ref_node_id(fid):
    return "_:ref:" + fid


def id_ok(i):
    """P003: an id is 1..512 code points without white space or controls; a _:ref: id may be 6 longer."""
    limit = MAX_ID + 6 if i.startswith("_:ref:") else MAX_ID
    return isinstance(i, str) and 1 <= len(i) <= limit and not re.search(r"[\s\x00-\x1f\x7f]", i)


def _split_ext(ext):
    """(weight or None, remaining extensions or None) from an extensions object."""
    if not ext:
        return None, None
    rest = {k: v for k, v in ext.items() if k != WEIGHT}
    return ext.get(WEIGHT), (rest or None)


def value_node(rec, b, nodes, literal_nodes, present):
    v = b["value"]
    k = vkind(v)
    if k == "entity":
        return v["entity"]
    if k == "literal":
        lit = canon_literal(v["literal"])
        nid = literal_node_id(lit) if literal_nodes == "shared" else literal_binding_node_id(rec["id"], b["bid"])
        nodes.setdefault(nid, {"node": nid, "attrs": {"khg-kind": "literal", "label": lit_label(lit),
                                                      "khg-literal": lit}})
        return nid
    if k == "fact":
        nid = ref_node_id(v["fact"])
        a = {"khg-kind": "fact-ref", "khg-ref": v["fact"]}
        if v["fact"] not in present:
            a["khg-external"] = True
        nodes.setdefault(nid, {"node": nid, "attrs": a})
        return nid
    if k == "special":
        nid = special_node_id(v["special"], rec["id"], b["bid"])
        nodes[nid] = {"node": nid, "attrs": {"khg-kind": v["special"]}}
        return nid
    if k == "unbound":
        nid = special_node_id("unbound", rec["id"], b["bid"])
        nodes[nid] = {"node": nid, "attrs": {"khg-kind": "unbound", "khg-unbound": copy.deepcopy(v["unbound"])}}
        return nid
    raise KHGError("KHG-C001", f"value kind {k}")


def select_slice(doc, relations):
    """Slices for P5: the hyperedges of the listed relations; the lifecycle record named by the status_ref of every
    kept fact (closed: the facts that record binds keep their own lifecycle records); and the entities kept records
    reference. Fact references to facts outside the slice stay as external references."""
    recs = doc["records"]
    by_id = {r["id"]: r for r in recs if "id" in r}
    keep = {r["id"] for r in recs if r["kind"] == "hyperedge" and r["relation"] in relations}
    changed = True
    while changed:
        changed = False
        for rid in sorted(keep):
            r = by_id[rid]
            ref = r.get("status_ref")
            if ref and ref in by_id and ref not in keep:
                keep.add(ref)
                changed = True
    ents = set()
    for r in recs:
        if r.get("id") in keep:
            for b in r["bindings"]:
                if vkind(b["value"]) == "entity":
                    ents.add(b["value"]["entity"])
    out = [r for r in recs if r.get("id") in keep or (r["kind"] == "entity" and r["id"] in ents)]
    hdr = copy.deepcopy(doc["header"])
    hdr["complete"] = False
    return {"header": hdr, "records": out}


def c1_to_hif(doc, schema: Schema, *, relations=None, literal_nodes="shared", schema_document=False):
    if literal_nodes not in ("shared", "per_binding"):
        raise ValueError("literal_nodes")
    if relations is not None:
        doc = select_slice(doc, set(relations))
    hdr = doc["header"]
    recs = [canonical_record(r) for r in doc["records"]]
    ents = sorted((r for r in recs if r["kind"] == "entity"), key=lambda r: r["id"])
    edges = sorted((r for r in recs if r["kind"] == "hyperedge"), key=lambda r: (r["id"], r.get("version", 0)))
    present = {r["id"] for r in edges}
    directed = all(eff_dir(schema, r, b) for r in edges for b in r["bindings"])
    nodes = {}
    for e in ents:
        a = {"khg-kind": "entity"}
        rec = {"node": e["id"]}
        for f, k in ENTITY_FIELDS:
            if f in e:
                a[k] = copy.deepcopy(e[f])
        w, rest = _split_ext(a.pop("khg-extensions", None))
        if rest:
            a["khg-extensions"] = rest
        if w is not None:
            rec["weight"] = w
        rec["attrs"] = a
        nodes[e["id"]] = rec
    incidences, erecs = [], []
    for r in edges:
        a = {}
        for f, k in EDGE_FIELDS:
            if f in r:
                a[k] = copy.deepcopy(r[f])
        w, rest = _split_ext(a.pop("khg-extensions", None))
        if rest:
            a["khg-extensions"] = rest
        er = {"edge": r["id"]}
        if w is not None:
            er["weight"] = w
        er["attrs"] = a
        erecs.append(er)
        for b in sorted(r["bindings"], key=bsortkey):
            nid = value_node(r, b, nodes, literal_nodes, present)
            ia = {"role": b["role"], "khg-bid": b["bid"]}
            if "position" in b:
                ia["role-position"] = b["position"]
            bw, brest = _split_ext(b.get("extensions"))
            if brest:
                ia["khg-extensions"] = brest
            inc = {"edge": r["id"], "node": nid}
            d = eff_dir(schema, r, b)
            if d:
                inc["direction"] = d
            if bw is not None:
                inc["weight"] = bw
            inc["attrs"] = ia
            incidences.append(inc)
    md = {
        "role-convention": "1.0.0",
        "hif-schema": HIF_SCHEMA_URL,
        "hif-schema-sha256": "sha256:" + HIF_SCHEMA_SHA256,
        "khg-profile": "khg-hif/1.0.0",
        "khg-record": hdr["format"],
        "khg-schema": schema.ref(),
        "khg-schema-sha256": schema.sha256(),
        "khg-document-id": hdr["document_id"],
        "khg-literal-nodes": literal_nodes,
    }
    if "complete" in hdr:
        md["khg-complete"] = hdr["complete"]
    if relations is not None:
        md["khg-slice"] = {"relations": sorted(relations)}
    if schema_document:
        md["khg-schema-document"] = copy.deepcopy(schema.doc)
    for k, v in (hdr.get("extensions") or {}).get("hif:metadata", {}).items():
        md[k] = copy.deepcopy(v)
    ordered_nodes = [nodes[k] for k in sorted(nodes, key=lambda i: (i.startswith("_:"), i))]
    for n in ordered_nodes:
        if not id_ok(n["node"]):
            raise KHGError("KHG-P003", f"node id {n['node'][:40]!r}... breaks the id grammar")
    return {"network-type": "directed" if directed else "undirected", "metadata": md,
            "nodes": ordered_nodes, "edges": erecs, "incidences": incidences}


PROFILE_MD = {"role-convention", "role-vocabulary", "hif-schema", "hif-schema-sha256", "khg-profile", "khg-record",
              "khg-schema", "khg-schema-sha256", "khg-document-id", "khg-complete", "khg-slice",
              "khg-schema-document", "khg-literal-nodes"}


def hif_to_c1(hif, schema: Schema | None = None):
    md = hif.get("metadata") or {}
    if md.get("role-convention") != "1.0.0":
        raise KHGError("KHG-R003", "role-convention declaration missing or unknown")
    if md.get("khg-profile") != "khg-hif/1.0.0":
        raise KHGError("KHG-P001", "not a khg-hif/1.0.0 document (foreign import comes in 1.1)")
    if schema is None:
        if "khg-schema-document" not in md:
            raise KHGError("KHG-D009", "no relation-type schema supplied and none inlined")
        schema = Schema(md["khg-schema-document"])
    if md.get("khg-schema-sha256") != schema.sha256():
        raise KHGError("KHG-D009", "schema hash mismatch")
    directed = hif.get("network-type") == "directed"
    sliced = "khg-slice" in md
    node = {}
    for n in hif.get("nodes", []):
        if n["node"] in node:
            raise KHGError("KHG-D001", f"duplicate node {n['node']!r}")
        node[n["node"]] = n
    recs = []
    for nid, n in node.items():
        a = n.get("attrs", {})
        kind = a.get("khg-kind")
        if kind is None:
            raise KHGError("KHG-P013", f"node {nid!r} without khg-kind")
        if kind == "entity":
            if nid.startswith("_:"):
                raise KHGError("KHG-P004", f"entity node {nid!r} uses the reserved _: prefix")
            e = {"kind": "entity", "id": nid}
            for f, k in ENTITY_FIELDS:
                if k in a:
                    e[f] = copy.deepcopy(a[k])
            if "weight" in n:
                e.setdefault("extensions", {})[WEIGHT] = n["weight"]
            recs.append(e)
        elif kind == "literal":
            if nid.startswith("_:lit:") and literal_node_id(a["khg-literal"]) != nid:
                raise KHGError("KHG-D005", f"literal node id {nid!r} does not match its value")
        elif kind == "fact-ref":
            if ref_node_id(a["khg-ref"]) != nid:
                raise KHGError("KHG-D005", f"fact-ref node id {nid!r} does not match its ref")
            if a.get("khg-external") and not sliced:
                raise KHGError("KHG-P017", "khg-external outside a slice")
    by_edge = {}
    for er in hif.get("edges", []):
        if er["edge"] in by_edge:
            raise KHGError("KHG-D001", f"duplicate edge {er['edge']!r}")
        r = {"kind": "hyperedge", "id": er["edge"]}
        for f, k in EDGE_FIELDS:
            if k in er.get("attrs", {}):
                r[f] = copy.deepcopy(er["attrs"][k])
        if "weight" in er:
            r.setdefault("extensions", {})[WEIGHT] = er["weight"]
        r["bindings"] = []
        by_edge[er["edge"]] = r
    seen_bids = set()
    for inc in hif["incidences"]:
        r = by_edge.get(inc["edge"])
        if r is None:
            raise KHGError("KHG-D003", f"incidence names undeclared edge {inc['edge']!r}")
        if inc["node"] not in node:
            raise KHGError("KHG-D002", f"incidence names undeclared node {inc['node']!r}")
        a = inc["attrs"]
        if (r["id"], a["khg-bid"]) in seen_bids:
            raise KHGError("KHG-P016", f"repeated khg-bid {a['khg-bid']!r} in {r['id']!r}")
        seen_bids.add((r["id"], a["khg-bid"]))
        na = node[inc["node"]]["attrs"]
        k = na["khg-kind"]
        if k == "entity":
            v = {"entity": inc["node"]}
        elif k == "literal":
            if inc["node"].startswith("_:litb:") and literal_binding_node_id(r["id"], a["khg-bid"]) != inc["node"]:
                raise KHGError("KHG-D005", "per-binding literal node id mismatch")
            v = {"literal": copy.deepcopy(na["khg-literal"])}
        elif k == "fact-ref":
            v = {"fact": na["khg-ref"]}
        elif k in ("somevalue", "novalue"):
            if special_node_id(k, r["id"], a["khg-bid"]) != inc["node"]:
                raise KHGError("KHG-D005", "special node id mismatch")
            v = {"special": k}
        elif k == "unbound":
            if special_node_id("unbound", r["id"], a["khg-bid"]) != inc["node"]:
                raise KHGError("KHG-D005", "unbound node id mismatch")
            v = {"unbound": copy.deepcopy(na["khg-unbound"])}
        else:
            raise KHGError("KHG-P013", f"node kind {k!r}")
        b = {"bid": a["khg-bid"], "role": a["role"], "value": v}
        if "role-position" in a:
            b["position"] = a["role-position"]
        ext = copy.deepcopy(a.get("khg-extensions")) or {}
        if "weight" in inc:
            ext[WEIGHT] = inc["weight"]
        if ext:
            b["extensions"] = ext
        d = inc.get("direction")
        if directed and d is None:
            raise KHGError("KHG-P010", "directed document, incidence without direction")
        declared = schema.usage(r["relation"], a["role"]).get("direction")
        if declared is not None and d is not None and d != declared:
            raise KHGError("KHG-S016", f"direction {d!r} contradicts declared {declared!r}")
        if declared is None and d is not None:
            b["direction"] = d
        r["bindings"].append(b)
    for r in by_edge.values():
        for b in r["bindings"]:
            if vkind(b["value"]) == "fact" and b["value"]["fact"] not in by_edge:
                ext = node[ref_node_id(b["value"]["fact"])]["attrs"].get("khg-external")
                if not (sliced and ext):
                    raise KHGError("KHG-D002", f"fact reference {b['value']['fact']!r} does not resolve")
    recs.extend(by_edge.values())
    sid, sver = md["khg-schema"].rsplit("/", 1)
    hdr = {"kind": "header", "format": md["khg-record"], "document_id": md["khg-document-id"],
           "schema": {"id": sid, "version": sver, "sha256": md["khg-schema-sha256"]}, "content": "snapshot"}
    if "khg-complete" in md:
        hdr["complete"] = md["khg-complete"]
    extra = {k: copy.deepcopy(v) for k, v in md.items() if k not in PROFILE_MD}
    if extra:
        hdr["extensions"] = {"hif:metadata": extra}
    return {"header": hdr, "records": recs}


# ---------------------------------------------------------------------------------------------
# Identity classes (non-normative identity.relate), redirects, support resolution (§2.9, §2.2, §2.8)
# ---------------------------------------------------------------------------------------------

RELATE_LABELS = ("duplicate", "refines", "generalises", "distinct", "key_conflict", "key_timeline", "negation_conflict")


def _is_novalue(v):
    return vkind(v) == "special" and v["special"] == "novalue"


def relate(schema, a, b):
    """How candidate a relates to stored fact b: one of the seven labels of [DB §2.19]."""
    if a["relation"] != b["relation"]:
        return "distinct"
    cls = classify(schema, a, b)
    if cls != "distinct":
        return cls
    # negation conflict: one side says novalue where the other has a filler, the other core bindings agree
    ra, rb = {}, {}
    for f, acc in ((a, ra), (b, rb)):
        for x in content_bindings(schema, f, ("core",)):
            acc.setdefault(x["role"], []).append(x["value"])
    neg = [r for r in set(ra) | set(rb)
           if any(_is_novalue(v) for v in ra.get(r, [])) != any(_is_novalue(v) for v in rb.get(r, []))
           and ra.get(r) and rb.get(r)]
    same_rest = all(sorted(cjson(value_identity(v)) for v in ra.get(r, [])) ==
                    sorted(cjson(value_identity(v)) for v in rb.get(r, [])) for r in set(ra) | set(rb) if r not in neg)
    if neg and same_rest and possible_overlap(bounds(schema, a), bounds(schema, b)):
        return "negation_conflict"
    ka, kb = key_digest(schema, a), key_digest(schema, b)
    if ka and ka == kb:
        key = schema.key(a["relation"])
        if key.get("temporal") and not definite_overlap(bounds(schema, a), bounds(schema, b)):
            return "key_timeline"
        return "key_conflict"
    return "distinct"


def resolve_redirects(entity_id, entities):
    """Follow redirect_to to the surviving entity (cycle-safe); entities: {id: entity record}."""
    seen = []
    cur = entity_id
    while cur in entities and entities[cur].get("redirect_to") and cur not in seen:
        seen.append(cur)
        cur = entities[cur]["redirect_to"]
    return cur


def supported_values(history, evidence_id):
    """CONS-19: the values an evidence record supports are those its bids held in the first version that carries it."""
    for version in sorted(history, key=lambda r: r["version"]):
        ev = next((e for e in version.get("evidence", []) if e["id"] == evidence_id), None)
        if ev is not None:
            bids = ev["supports"] if "supports" in ev else [b["bid"] for b in version["bindings"]]
            return {b["bid"]: canon_value(b["value"]) for b in version["bindings"] if b["bid"] in bids}
    return {}


# ---------------------------------------------------------------------------------------------
# Derived views: render_text (khg-render/1) and projections (§2.10)
# ---------------------------------------------------------------------------------------------

RENDER_VERSION = "khg-render/1"


def _render_value(v, labels):
    k = vkind(v)
    if k == "entity":
        return labels.get(v["entity"], v["entity"])
    if k == "literal":
        return lit_label(canon_literal(v["literal"]))
    if k == "fact":
        return f"[{v['fact']}]"
    if k == "special":
        return {"somevalue": "some value", "novalue": "no value"}[v["special"]]
    return "?" + v["unbound"]["var"]


def render_text(rec, labels, *, schema):
    """khg-render/1: relation label, then 'role: value' groups (core usages, then qualifier usages, in the relation's
    usage order; fillers of one role in canonical binding order, joined by ', '), then the valid time as a
    '[start, end)' suffix for interval relations. Meta bindings are omitted. Nested facts render as [<fact id>]."""
    rel = schema.rel[rec["relation"]]
    rlabel = labels.get(rec["relation"], rel.get("label", rec["relation"]))
    parts = []
    for slot in ("core", "qualifier"):
        for u in schema.usages(rec["relation"]):
            if u["slot"] != slot:
                continue
            bs = sorted((b for b in rec["bindings"] if b["role"] == u["role"]), key=bsortkey)
            if bs:
                role_label = labels.get(u["role"], u.get("label", u["role"]))
                parts.append(f"{role_label}: " + ", ".join(_render_value(b["value"], labels) for b in bs))
    out = f"{rlabel}({'; '.join(parts)})"
    tm = schema.time_model(rec["relation"])
    if tm["model"] == "interval":
        def bound(role):
            b = next((x for x in rec["bindings"] if x["role"] == role), None)
            return "…" if b is None else _render_value(b["value"], labels)
        out += f" [{bound(tm['start'])}, {bound(tm['end'])})"
    return out


NONE_ID = "khg:none"


def _value_id(rec, b, literals):
    v = b["value"]
    k = vkind(v)
    if k in ("entity", "fact"):
        return v[k]
    if k == "literal":
        return literal_node_id(canon_literal(v["literal"])) if literals == "node" else NONE_ID
    if k == "special":
        return special_node_id(v["special"], rec["id"], b["bid"])
    raise ValueError("unbound values have no positional projection")


def position_map(schema, relation, *, slots=("core", "qualifier"), literals="node", widths=None):
    """The positions of a relation: its usages in schema order (slots filtered); a usage with max k gives k positions;
    an unbounded usage needs widths[role]; with literals='drop', usages that admit only literals are left out."""
    out = []
    for u in schema.usages(relation):
        if u["slot"] not in slots:
            continue
        if literals == "drop" and all("literal" in f for f in u["fillers"]):
            continue
        w = u.get("max")
        if w is None:
            w = (widths or {}).get(u["role"])
            if w is None:
                raise ValueError(f"unbounded usage {relation}.{u['role']} needs a width")
        out += [(u["role"], i) for i in range(1, w + 1)]
    return out


def positional(rec, schema, *, slots=("core", "qualifier"), literals="node", widths=None):
    """project.positional: (relation, v1, ..., vn) over position_map; ordered roles fill by position, unordered roles by
    canonical value order; an absent optional position is khg:none; lifecycle and goal records are refused."""
    if rec.get("status") == "goal" or schema.kind(rec["relation"]) == "lifecycle":
        raise ValueError("lifecycle and goal records have no positional projection")
    pm = position_map(schema, rec["relation"], slots=slots, literals=literals, widths=widths)
    by_role = {}
    for b in sorted(rec["bindings"], key=bsortkey):
        by_role.setdefault(b["role"], []).append(b)
    vals = []
    for role, i in pm:
        bs = by_role.get(role, [])
        u = schema.usage(rec["relation"], role)
        if u.get("ordered"):
            b = next((x for x in bs if x.get("position") == i), None)
        else:
            b = bs[i - 1] if i <= len(bs) else None
        vals.append(NONE_ID if b is None else _value_id(rec, b, literals))
    if any(len(by_role.get(r, [])) > sum(1 for x, _ in pm if x == r) for r in by_role
           if schema.usage(rec["relation"], r)["slot"] in slots and any(x == r for x, _ in pm)):
        raise ValueError("more fillers than positions (raise the width)")
    return (rec["relation"], *vals)


def hyper_relational(rec, schema):
    """project.hyper_relational: the main triple from the relation's primary, then (role, value) qualifier pairs
    sorted by (role, value id); every other core or qualifier binding becomes a qualifier pair."""
    prim = schema.rel[rec["relation"]].get("primary")
    if not prim:
        raise ValueError(f"relation {rec['relation']} declares no primary")
    subj = next(b for b in rec["bindings"] if b["role"] == prim["subject"])
    obj = next(b for b in rec["bindings"] if b["role"] == prim["object"])
    quals = sorted((b["role"], _value_id(rec, b, "node")) for b in rec["bindings"]
                   if b is not subj and b is not obj and slot_of(schema, rec, b) in ("core", "qualifier", "time"))
    return {"subject": _value_id(rec, subj, "node"), "relation": rec["relation"], "object": _value_id(rec, obj, "node"),
            "qualifiers": [list(q) for q in quals]}


def role_value_set(rec, schema, *, slots=("core", "qualifier")):
    """project.role_value_set: the sorted multiset of (role, value id) pairs of the chosen slots."""
    return sorted([b["role"], _value_id(rec, b, "node")] for b in rec["bindings"] if slot_of(schema, rec, b) in slots)


# RDF relation-instance projection: one node per fact and one per binding; reversible IRIs (RFC 3987)
KHG_NS = "https://w3id.org/khg/ns#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_IUNRESERVED = re.compile(r"[A-Za-z0-9\-._~]|[^\x00-\x7f]")


def iri_encode(i):
    """urn:khg:<id>, every character outside iunreserved percent-encoded as UTF-8 (RFC 3987 §2.2); reversible."""
    out = []
    for ch in nfc(i):
        if _IUNRESERVED.fullmatch(ch):
            out.append(ch)
        else:
            out.append("".join(f"%{x:02X}" for x in ch.encode("utf-8")))
    return "urn:khg:" + "".join(out)


def iri_decode(iri):
    from urllib.parse import unquote
    assert iri.startswith("urn:khg:")
    return unquote(iri[len("urn:khg:"):], encoding="utf-8", errors="strict")


def _lit(s):
    return {"literal": s}


def rdf_relation_instance(doc):
    """project.rdf_relation_instance: triples (s, p, o); IRIs as strings, literals as {"literal": str}."""
    T = []
    for r in doc["records"]:
        if r["kind"] != "hyperedge":
            continue
        f = iri_encode(r["id"])
        T += [(f, RDF_TYPE, KHG_NS + "Hyperedge"), (f, KHG_NS + "relation", _lit(r["relation"])),
              (f, KHG_NS + "status", _lit(r["status"]))]
        for b in r["bindings"]:
            n = f + "#" + b["bid"]
            T += [(f, KHG_NS + "binding", n), (n, KHG_NS + "bid", _lit(b["bid"])), (n, KHG_NS + "role", _lit(b["role"]))]
            if "position" in b:
                T.append((n, KHG_NS + "position", _lit(str(b["position"]))))
            if "direction" in b:
                T.append((n, KHG_NS + "direction", _lit(b["direction"])))
            v, k = b["value"], vkind(b["value"])
            if k in ("entity", "fact"):
                T.append((n, KHG_NS + "value", iri_encode(v[k])))
                T.append((n, KHG_NS + "valueKind", _lit(k)))
            else:
                T.append((n, KHG_NS + "valueJSON", _lit(cjson(canon_value(v)))))
    return sorted(T, key=lambda t: cjson(list(t)))


def from_rdf_relation_instance(triples):
    """Inverse of rdf_relation_instance for the binding structure: {id: {relation, status, bindings}}."""
    facts, nodes = {}, {}
    for s, p, o in triples:
        if p == RDF_TYPE:
            facts.setdefault(s, {})
        elif p in (KHG_NS + "relation", KHG_NS + "status"):
            facts.setdefault(s, {})[p[len(KHG_NS):]] = o["literal"]
        elif p == KHG_NS + "binding":
            facts.setdefault(s, {}).setdefault("_b", []).append(o)
        else:
            nodes.setdefault(s, {})[p[len(KHG_NS):]] = o
    out = {}
    for f, d in facts.items():
        bs = []
        for n in d.get("_b", []):
            a = nodes[n]
            b = {"bid": a["bid"]["literal"], "role": a["role"]["literal"]}
            if "position" in a:
                b["position"] = int(a["position"]["literal"])
            if "direction" in a:
                b["direction"] = a["direction"]["literal"]
            if "value" in a:
                b["value"] = {a["valueKind"]["literal"]: iri_decode(a["value"])}
            else:
                b["value"] = json.loads(a["valueJSON"]["literal"])
            bs.append(b)
        out[iri_decode(f)] = {"relation": d["relation"], "status": d["status"], "bindings": sorted(bs, key=bsortkey)}
    return out


INCIDENCE_COLUMNS = ("fact_id", "version", "relation", "status", "bid", "role", "position", "direction", "value_kind",
                     "value")


def incidence_rows(doc):
    """project.incidence_rows: one row per binding; value is the id for entity/fact values, else canonical JSON."""
    rows = []
    for r in doc["records"]:
        if r["kind"] != "hyperedge":
            continue
        for b in sorted(r["bindings"], key=bsortkey):
            v, k = b["value"], vkind(b["value"])
            rows.append((r["id"], r.get("version", 1), r["relation"], r["status"], b["bid"], b["role"],
                         b.get("position"), b.get("direction"), k, v[k] if k in ("entity", "fact") else cjson(canon_value(v))))
    return rows


def from_incidence_rows(rows):
    out = {}
    for fid, _ver, rel, st, bid, role, pos, d, k, val in rows:
        f = out.setdefault(fid, {"relation": rel, "status": st, "bindings": []})
        b = {"bid": bid, "role": role, "value": {k: val} if k in ("entity", "fact") else json.loads(val)}
        if pos is not None:
            b["position"] = pos
        if d is not None:
            b["direction"] = d
        f["bindings"].append(b)
    for f in out.values():
        f["bindings"].sort(key=bsortkey)
    return out
