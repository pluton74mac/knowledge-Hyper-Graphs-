"""Checks of relation-type schema documents: the version gate (V001) and layer M (M001-M017), and ``load_schema``.

Pipeline ``J V M`` (DESIGN §8.1). The reader takes ``khg-relation-schema/1.0.x`` and ``1.1.x`` (ruling 22: a key's
``separators`` and a usage's ``monotone`` flag) and checks both by the 1.1.0 meta-schema. Writers stamp the lowest
version whose features a document uses (``required_format``). Layer M has two parts:

- the meta-schema ``khg-relation-schema-1.1.0.schema.json`` (structure; its ``x-khg-code`` annotations name M001,
  M004, M006, M007, M012, M014 and, by default, M015, which also covers ``monotone: false`` on a usage that is not a
  qualifier), run by jsonschema or fastjsonschema with a closed resolver;
- Python checks that need the whole document: M002, M003 (key roles and separators), M005, M007 (what the time model
  names), M008, M009, M010, M011, M012 (which usages ``primary`` names), M013, M015 (constraint roles, filler
  options, confidence scales), M016 and M017. They tolerate a structurally broken document; the meta-schema reports
  the structure.
"""
from __future__ import annotations

import functools
import os
import re
from typing import Any, Callable, Mapping

from .. import data, jsonio
from ..errors import ValidationError, make_finding
from .builtins import DATATYPES, DEFAULT_TIME, RESERVED_PREFIX
from .model import Schema, json_copy

__all__ = ["META_SCHEMA", "META_SCHEMA_ID", "FORMAT", "FORMAT_1_1", "MAX_DEPTH", "version_findings", "meta_findings",
           "python_findings", "nesting_fault", "check_schema", "load_schema", "required_format"]

META_SCHEMA = "schemas/khg-relation-schema-1.1.0.schema.json"
META_SCHEMA_ID = "tag:khg-contracts,2026:schema/khg-relation-schema/1.1.0"
#: The stamp of a document without 1.1 features (what the sample migration writes), and the newest this reader takes.
FORMAT = "khg-relation-schema/1.0.0"
FORMAT_1_1 = "khg-relation-schema/1.1.0"
_FORMAT_RE = re.compile(r"khg-relation-schema/(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
_ENGINES = ("jsonschema", "fastjsonschema")
#: The nesting limit of layer J (J001), for parsed text and objects alike: the deepest nesting of objects and arrays
#: in a document. ``validate.layers.j`` and ``check_schema`` apply it; it is well inside what the recursive walkers
#: of the package and of the engines process under Python's default recursion limit (two frames a level).
MAX_DEPTH = 256

Finding = dict[str, str]


def _f(code: str, path: str, message: str) -> Finding:
    return make_finding(code, path, message)


def _pointer(parts: Any) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def _list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else []


def _items(x: Any) -> list[tuple[int, dict[str, Any]]]:
    """(index, item) for the dict items of a list; anything else is left to the meta-schema."""
    return [(i, v) for i, v in enumerate(_list(x)) if isinstance(v, dict)]


# ------------------------------------------------------------------------------------------------ J


def nesting_fault(doc: Any) -> str | None:
    """The JSON pointer of the first object or array of ``doc`` nested deeper than ``MAX_DEPTH`` levels, depth
    first in document order (``doc`` itself is level 1); None when there is none. Mappings, lists and tuples are
    containers. Built without recursion."""
    stack: list[tuple[Any, Any, int]] = [(doc, None, 0)]
    while stack:
        value, link, depth = stack.pop()
        if not isinstance(value, (Mapping, list, tuple)):
            continue
        if depth >= MAX_DEPTH:
            parts: list[Any] = []
            while link is not None:
                link, key = link
                parts.append(key)
            return _pointer(reversed(parts))
        items = value.items() if isinstance(value, Mapping) else enumerate(value)
        stack.extend(reversed([(v, (link, k), depth + 1) for k, v in items
                               if isinstance(v, (Mapping, list, tuple))]))
    return None


# ------------------------------------------------------------------------------------------------ V


def version_findings(doc: Any) -> list[Finding]:
    """V001 unless ``format`` is ``khg-relation-schema/1.0.x`` or ``1.1.x`` (a reader rejects a newer minor or another
    major)."""
    fmt = doc.get("format") if isinstance(doc, Mapping) else None
    m = _FORMAT_RE.fullmatch(fmt) if isinstance(fmt, str) else None
    if m and int(m.group(1)) == 1 and int(m.group(2)) <= 1:
        return []
    return [_f("KHG-V001", "/format", f"format {fmt!r} is not {FORMAT_1_1} (or an earlier minor or a patch of it)")]


def required_format(doc: Mapping[str, Any]) -> str:
    """The lowest ``format`` whose features a schema document uses (§11.2): ``FORMAT_1_1`` when a key declares
    ``separators`` or a usage says ``monotone`` (either value), else ``FORMAT``."""
    for r in _list(doc.get("relations")):
        if isinstance(r, Mapping):
            key = r.get("key")
            if isinstance(key, Mapping) and "separators" in key:
                return FORMAT_1_1
            if any(isinstance(u, Mapping) and "monotone" in u for u in _list(r.get("roles"))):
                return FORMAT_1_1
    return FORMAT


# ------------------------------------------------------------------------------------------------ M: meta-schema


def _code_of(sub: Any, keyword: str) -> str | None:
    c = sub.get("x-khg-code") if isinstance(sub, Mapping) else None
    if isinstance(c, str):
        return c
    if isinstance(c, Mapping):
        return c.get(keyword) or c.get("default")
    return None


class _Closed(LookupError):
    """A ``$ref`` outside the packaged meta-schema: never fetched."""


def _refuse(uri: str) -> Any:
    raise _Closed(f"closed resolver: {uri} is not packaged")


@functools.cache
def _meta_runner(engine: str) -> Callable[[Any], list[Finding]]:
    doc = data.load_json(META_SCHEMA)
    if engine == "jsonschema":
        import jsonschema
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7

        registry = Registry(retrieve=_refuse).with_resource(
            META_SCHEMA_ID, Resource.from_contents(doc, default_specification=DRAFT7))
        validator = jsonschema.Draft7Validator(doc, registry=registry)

        def run_js(instance: Any) -> list[Finding]:
            return [_f(_code_of(e.schema, str(e.validator)) or "KHG-M015", _pointer(e.absolute_path), e.message)
                    for e in validator.iter_errors(instance)]
        return run_js
    if engine == "fastjsonschema":
        import fastjsonschema

        compiled = fastjsonschema.compile(doc, handlers={"tag": _refuse, "http": _refuse, "https": _refuse})

        def run_fast(instance: Any) -> list[Finding]:
            try:
                compiled(instance)
            except fastjsonschema.JsonSchemaValueException as e:
                return [_f(_code_of(e.definition, str(e.rule)) or "KHG-M015", _pointer(_fast_path(e.name)),
                           e.message)]
            return []
        return run_fast
    raise ValueError(f"engine must be one of {_ENGINES}, not {engine!r}")


def _fast_path(name: str) -> list[Any]:
    """fastjsonschema's ``data.relations[3].roles`` -> ``["relations", 3, "roles"]``."""
    rest = name[len("data"):] if name.startswith("data") else name
    return [m.group(1) if m.group(1) is not None else int(m.group(2))
            for m in re.finditer(r"\.([^.\[\]]+)|\[(\d+)\]", rest)]


def meta_findings(doc: Any, *, engine: str = "jsonschema") -> list[Finding]:
    """The meta-schema's findings. jsonschema reports every violation; fastjsonschema stops at the first."""
    return _meta_runner(engine)(doc)


# ------------------------------------------------------------------------------------------------ M: Python


def _cycles(parents: dict[str, list[str]]) -> set[str]:
    """The entity types that lie on a parents cycle (a type reaching itself)."""
    on_cycle: set[str] = set()
    for start in sorted(parents):
        seen: set[str] = set()
        stack = list(parents.get(start, []))
        while stack:
            x = stack.pop()
            if x == start:
                on_cycle.add(start)
                break
            if x in seen:
                continue
            seen.add(x)
            stack.extend(parents.get(x, []))
    return on_cycle


def _ids(doc: dict[str, Any], name: str, out: list[Finding]) -> list[Any]:
    """The ids of one vocabulary list, reporting M013 duplicates and M008 reserved ids."""
    seen: set[Any] = set()
    ids = []
    for i, item in _items(doc.get(name)):
        x = item.get("id")
        if not isinstance(x, str):
            continue
        ids.append(x)
        if x in seen:
            out.append(_f("KHG-M013", f"/{name}/{i}/id", f"duplicate {name} id {x!r}"))
        seen.add(x)
        if x.startswith(RESERVED_PREFIX):
            out.append(_f("KHG-M008", f"/{name}/{i}/id", f"{x!r} uses the reserved khg: namespace"))
    return ids


def _count(x: Any, least: int) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x >= least


def _is_time_usage(u: Any) -> bool:
    """A time usage with max 1 and one time-literal filler (M007)."""
    if not isinstance(u, dict) or u.get("slot") != "time" or u.get("max") != 1:
        return False
    fillers = _list(u.get("fillers"))
    return len(fillers) == 1 and isinstance(fillers[0], dict) and fillers[0].get("literal") == "time"


def _relation_findings(r: dict[str, Any], p: str, types: set[str], roles: set[str], rels: set[str],
                       default_time: Any, out: list[Finding]) -> None:
    usages = _items(r.get("roles"))
    by_role: dict[str, dict[str, Any]] = {}
    for j, u in usages:
        q = f"{p}/roles/{j}"
        role = u.get("role")
        if isinstance(role, str):
            if role in by_role:
                out.append(_f("KHG-M002", f"{q}/role", f"role {role!r} is used twice"))
            else:
                by_role[role] = u
            if role not in roles:
                out.append(_f("KHG-M009", f"{q}/role", f"role {role!r} is not in the schema's role vocabulary"))
        for k, fl in _items(u.get("fillers")):
            fq = f"{q}/fillers/{k}"
            bad_types = [t for t in _list(fl.get("entity")) if isinstance(t, str) and t not in types]
            if bad_types:
                out.append(_f("KHG-M005", f"{fq}/entity", f"unknown entity type {bad_types[0]!r}"))
            bad_rels = [x for x in _list(fl.get("fact")) if isinstance(x, str) and x not in rels]
            if bad_rels:
                out.append(_f("KHG-M005", f"{fq}/fact", f"unknown relation {bad_rels[0]!r}"))
            dt = fl.get("literal")
            if dt in DATATYPES:  # an unknown datatype is the meta-schema's M006
                if "units" in fl and dt != "quantity":
                    out.append(_f("KHG-M015", f"{fq}/units", "units are allowed on quantity fillers only"))
                if "precision_min" in fl and dt != "time":
                    out.append(_f("KHG-M015", f"{fq}/precision_min", "precision_min is allowed on time fillers only"))
        mn, mx = u.get("min"), u.get("max")
        if _count(mn, 0) and _count(mx, 1) and mx < mn:  # a min < 0 or max < 1 is the meta-schema's M015
            out.append(_f("KHG-M010", q, f"max {mx} < min {mn}"))
    # the time model: what it names, and every time usage named
    own = "time" in r
    tm = r.get("time") if own else default_time
    named: set[str] = set()
    if isinstance(tm, dict) and tm.get("model") == "interval":
        for end in ("start", "end"):
            role = tm.get(end)
            if isinstance(role, str):
                named.add(role)
            if not _is_time_usage(by_role.get(role) if isinstance(role, str) else None):
                out.append(_f("KHG-M007", f"{p}/time/{end}" if own else p,
                              f"the time model's {end} {role!r} is not a time usage with max 1 and one time literal"))
        if tm.get("start") == tm.get("end"):
            out.append(_f("KHG-M007", f"{p}/time" if own else p, "the time model's start and end are one role"))
    for j, u in usages:  # a role that is not a string is the meta-schema's M015
        if u.get("slot") == "time" and isinstance(u.get("role"), str) and u["role"] not in named:
            out.append(_f("KHG-M007", f"{p}/roles/{j}", f"time usage {u.get('role')!r} is not named by the time model"))
    # the key
    key = r.get("key")
    if isinstance(key, dict):
        for m, role in enumerate(_list(key.get("roles"))):
            u = by_role.get(role) if isinstance(role, str) else None
            if u is None or u.get("slot") not in ("core", "qualifier"):
                out.append(_f("KHG-M003", f"{p}/key/roles/{m}",
                              f"key role {role!r} is not a core or qualifier usage of the relation"))
        roles = {x for x in _list(key.get("roles")) if isinstance(x, str)}
        for m, role in enumerate(_list(key.get("separators"))):  # 1.1: ruling 22
            u = by_role.get(role) if isinstance(role, str) else None
            if u is None or u.get("slot") not in ("core", "qualifier"):
                out.append(_f("KHG-M003", f"{p}/key/separators/{m}",
                              f"separator {role!r} is not a core or qualifier usage of the relation"))
            elif role in roles:
                out.append(_f("KHG-M003", f"{p}/key/separators/{m}", f"{role!r} is a key role and a separator"))
        if key.get("temporal") is True:
            if not (isinstance(tm, dict) and tm.get("model") == "interval"):
                out.append(_f("KHG-M011", f"{p}/key/temporal", "a temporal key needs an interval time model"))
            if key.get("on_collision") == "supersede":
                out.append(_f("KHG-M017", f"{p}/key/on_collision",
                              "on_collision supersede on a temporal key (a succession is not a belief revision)"))
    # primary
    primary = r.get("primary")
    if isinstance(primary, dict):
        for end in ("subject", "object"):
            role = primary.get(end)
            u = by_role.get(role) if isinstance(role, str) else None
            if u is None or u.get("slot") != "core" or u.get("max") != 1:
                out.append(_f("KHG-M012", f"{p}/primary/{end}",
                              f"primary {end} {role!r} is not a core usage with max 1"))
        if primary.get("subject") is not None and primary.get("subject") == primary.get("object"):
            out.append(_f("KHG-M012", f"{p}/primary", "primary names one usage twice"))
    # constraints
    for c, con in _items(r.get("constraints")):
        for m, role in enumerate(_list(con.get("roles"))):
            if isinstance(role, str) and role not in by_role:
                out.append(_f("KHG-M015", f"{p}/constraints/{c}/roles/{m}",
                              f"constraint role {role!r} is not used by the relation"))


def python_findings(doc: Any) -> list[Finding]:
    """The M checks that need the whole document (see the module docstring). Integral floats are read as ints
    (``json_copy``), so a ``max`` of ``1.0`` below a ``min`` of ``2.0`` is M010 as with integers."""
    if not isinstance(doc, Mapping):
        return []
    return _python_findings(json_copy(doc))


def _python_findings(doc: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    types = set(_ids(doc, "entity_types", out))
    roles = set(_ids(doc, "roles", out))
    rels = set(_ids(doc, "relations", out))
    parents = {t.get("id"): [x for x in _list(t.get("parents")) if isinstance(x, str)]
               for _, t in _items(doc.get("entity_types")) if isinstance(t.get("id"), str)}
    cyc = _cycles(parents)
    for i, t in _items(doc.get("entity_types")):
        for k, x in enumerate(_list(t.get("parents"))):
            if isinstance(x, str) and x not in types:
                out.append(_f("KHG-M016", f"/entity_types/{i}/parents/{k}", f"unknown parent type {x!r}"))
        if isinstance(t.get("id"), str) and t["id"] in cyc:  # an id that is not a string is the meta-schema's
            out.append(_f("KHG-M016", f"/entity_types/{i}/parents",
                          f"entity type {t.get('id')!r} is on a parents cycle"))
    seen_scales: set[str] = set()
    for i, s in _items(doc.get("confidence_scales")):
        sid = s.get("id")
        if sid == "probability":
            out.append(_f("KHG-M015", f"/confidence_scales/{i}/id", "the scale probability is built in"))
        elif isinstance(sid, str) and sid in seen_scales:
            out.append(_f("KHG-M015", f"/confidence_scales/{i}/id", f"duplicate confidence scale {sid!r}"))
        if isinstance(sid, str):
            seen_scales.add(sid)
        lo, hi = s.get("min"), s.get("max")
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and not lo < hi:
            out.append(_f("KHG-M015", f"/confidence_scales/{i}", f"scale min {lo} is not below max {hi}"))
    default_time = doc.get("default_time", DEFAULT_TIME)
    for i, r in _items(doc.get("relations")):
        _relation_findings(r, f"/relations/{i}", types, roles, rels, default_time, out)
    return out


# ------------------------------------------------------------------------------------------------ entry points


def check_schema(doc: Any, *, engine: str = "jsonschema") -> list[Finding]:
    """The findings of the ``J V M`` pipeline on a parsed document: J007 for a non-object and J001 for nesting
    deeper than ``MAX_DEPTH`` levels (either stops the run), else V001 (which stops the run), else the meta-schema's
    findings followed by the Python checks'. [] means valid. Both halves read a plain copy (``json_copy``: mappings
    as dicts, tuples as lists, integral floats as ints, built without recursion)."""
    if not isinstance(doc, Mapping):
        return [_f("KHG-J007", "", f"top level is {type(doc).__name__}, not an object")]
    deep = nesting_fault(doc)
    if deep is not None:
        return [_f("KHG-J001", deep, f"nesting deeper than {MAX_DEPTH} levels")]
    v = version_findings(doc)
    if v:
        return v
    plain = json_copy(doc)
    return meta_findings(plain, engine=engine) + _python_findings(plain)


def load_schema(source: str | os.PathLike[str] | Mapping[str, Any] | Schema) -> Schema:
    """Load a relation-type schema from a path (layers J, V, M) or a mapping (V, M); raise ``ValidationError``.
    A ``Schema`` is returned as it is."""
    if isinstance(source, Schema):
        return source
    if isinstance(source, Mapping):
        doc: Any = source
    else:
        doc = jsonio.load(source)
    findings = check_schema(doc)
    errors = [f for f in findings if f["severity"] == "error"]
    if errors:
        raise ValidationError.from_findings(findings)
    return Schema(doc)
