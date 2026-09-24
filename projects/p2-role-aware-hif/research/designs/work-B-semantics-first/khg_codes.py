"""Stable KHG codes for JSON Schema failures (design §8.1): the prototype of khg_contracts/validate/codes.py.

P2-owned schemas carry `x-khg-code` annotations. An annotation is a code (it covers the whole subtree)
or a map from a keyword to a code (`*` = any keyword). The reporter walks from the failing keyword
towards the root and takes the first annotation that applies to the keyword through which the
failure passes. When none applies, the layer's keyword table decides. The vendored HIF schema cannot
be annotated (F2), so layer H uses a table keyed on (keyword, instance path).

`coverage()` proves that every constraint of every P2-owned schema, reached along every path, maps
to a code, and that every constraint of the vendored schema matches a row of the H table."""
import json, re
from pathlib import Path
import jsonschema
from referencing import Registry, Resource

HERE = Path(__file__).parent


def _load(n):
    return json.loads((HERE / n).read_text(encoding="utf-8"))


HIF = _load("hif_schema_v0.1.0.json")
SCHEMAS = {"P": _load("khg-hif-1.0.0.schema.json"), "C": _load("khg-record-1.0.0.schema.json"),
           "M": _load("khg-schema-1.0.0.schema.json"), "Q": _load("khg-queue-1.0.0.schema.json")}
DOCS = {HIF["$id"]: HIF, **{s["$id"]: s for s in SCHEMAS.values()}}
REGISTRY = Registry().with_resource(HIF["$id"], Resource.from_contents(HIF))
VALIDATORS = {"H": jsonschema.Draft7Validator(HIF),
              **{k: jsonschema.Draft7Validator(s, registry=REGISTRY) for k, s in SCHEMAS.items()}}

# (keyword, instance-path regex, code); first match wins; the path is '/'-joined, '' for the root
H_TABLE = [
    ("required", r"", "KHG-H001"),
    ("additionalProperties", r"", "KHG-H002"),
    ("additionalProperties", r"(incidences|nodes|edges)/\d+", "KHG-H003"),
    ("type", r"(incidences|nodes|edges)/\d+/attrs|metadata", "KHG-H004"),
    ("enum", r"incidences/\d+/direction", "KHG-H005"),
    ("required", r"(incidences|nodes|edges)/\d+", "KHG-H006"),
    ("type", r"incidences/\d+/(edge|node)|nodes/\d+/node|edges/\d+/edge", "KHG-H007"),
    ("enum", r"network-type", "KHG-H008"),
    ("type", r".*", "KHG-H009"),
]

KEYWORD_TABLE = {
    "P": {},  # every profile constraint is annotated; coverage() checks it
    "C": {"enum": "KHG-C002", "const": "KHG-C002", "additionalProperties": "KHG-C009", "pattern": "KHG-C011", "*": "KHG-C010"},
    "M": {"*": "KHG-M015"},
    "Q": {"*": "KHG-Q008"},
}

NAMED = ("properties", "patternProperties", "definitions", "dependencies")
INDEXED = ("allOf", "anyOf", "oneOf")
SINGLE = ("additionalProperties", "additionalItems", "contains", "propertyNames", "not", "then", "else", "if")


def h_code(keyword, instance_path):
    for kw, rx, code in H_TABLE:
        if kw == keyword and re.fullmatch(rx, instance_path):
            return code
    return None


def _resolve(ref, base):
    uri, _, frag = ref.partition("#")
    doc = DOCS[uri] if uri else base
    node = doc
    for part in [p for p in frag.split("/") if p]:
        node = node[int(part)] if isinstance(node, list) else node[part.replace("~1", "/").replace("~0", "~")]
    return node, doc


def steps(root, schema_path):
    """[(subschema, keyword, document)] from the root to the failing keyword, following $ref."""
    out, cur, base, segs, i = [], root, root, list(schema_path), 0
    while True:
        while isinstance(cur, dict) and "$ref" in cur:
            out.append((cur, "$ref", base))
            cur, base = _resolve(cur["$ref"], base)
        k = segs[i]; i += 1
        out.append((cur, k, base))
        if i == len(segs):
            return out
        if k in NAMED or k in INDEXED or (k == "items" and isinstance(cur[k], list)):
            cur = cur[k][segs[i]]; i += 1
        elif k == "items" or k in SINGLE:
            cur = cur[k]
        else:
            raise ValueError(f"unexpected schema path segment {k!r} in {list(schema_path)}")


def code_for_steps(layer, st):
    if any(doc is HIF for _, _, doc in st):
        return None  # a failure inside the vendored schema: the caller uses the H table
    for sub, k, _ in reversed(st):
        a = sub.get("x-khg-code") if isinstance(sub, dict) else None
        if a is None:
            continue
        if isinstance(a, str):
            return a
        if k in a:
            return a[k]
        if "*" in a:
            return a["*"]
    table = KEYWORD_TABLE[layer]
    return table.get(st[-1][1], table.get("*"))


def code_for(layer, error):
    path = "/".join(map(str, error.absolute_path))
    if layer == "H":
        return h_code(error.validator, path)
    st = steps(SCHEMAS[layer], error.absolute_schema_path)
    return code_for_steps(layer, st) or h_code(error.validator, path)


def report(layer, instance):
    """All failures of one JSON Schema layer as (code, instance path, keyword, message), most specific first."""
    rows = []
    for e in VALIDATORS[layer].iter_errors(instance):
        rows.append((code_for(layer, e), "/".join(map(str, e.absolute_path)) or "(root)", e.validator, e.message))
    return sorted(rows, key=lambda r: (r[1].count("/") if r[1] != "(root)" else -1, r[1], r[0] or ""))


# ---------------- coverage ----------------
LEAF = {"type", "enum", "const", "required", "pattern", "format", "minimum", "maximum", "exclusiveMinimum",
        "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "minItems", "maxItems", "uniqueItems",
        "minProperties", "maxProperties", "contains", "not", "anyOf", "oneOf"}
# `if` never reports; `version` and `unevaluatedProperties` (in the vendored file) are not draft-07 keywords
IGNORED = {"$schema", "$id", "title", "description", "definitions", "x-khg-code", "default", "examples", "$comment", "if",
           "version", "unevaluatedProperties"}


def _constraints(sub, trail, base, depth=0):
    """Yield (steps, keyword) for every keyword that can fail as a top-level jsonschema error."""
    assert depth < 60, "schema too deep or recursive"
    if not isinstance(sub, dict):
        return
    if "$ref" in sub:
        tgt, doc = _resolve(sub["$ref"], base)
        yield from _constraints(tgt, trail + [(sub, "$ref", base)], doc, depth + 1)
        return
    for k, v in sub.items():
        here = trail + [(sub, k, base)]
        if k in IGNORED:
            continue
        if k in LEAF:
            yield here, k
        elif k in ("properties", "patternProperties"):
            for s in v.values():
                yield from _constraints(s, here, base, depth + 1)
        elif k == "dependencies":
            for name, s in v.items():
                if isinstance(s, list):
                    yield here, k
                else:
                    yield from _constraints(s, here, base, depth + 1)
        elif k == "allOf":
            for s in v:
                yield from _constraints(s, here, base, depth + 1)
        elif k in ("items", "additionalItems"):
            for s in (v if isinstance(v, list) else [v]):
                if s is False:
                    yield here, k
                else:
                    yield from _constraints(s, here, base, depth + 1)
        elif k == "additionalProperties":
            if v is False:
                yield here, k
            else:
                yield from _constraints(v, here, base, depth + 1)
        elif k in ("propertyNames", "then", "else"):
            yield from _constraints(v, here, base, depth + 1)
        else:
            raise ValueError(f"keyword {k!r} not handled by the coverage walk")


def _h_example_path(trail):
    """An instance path that reaches the constraint, e.g. incidences/0/weight."""
    parts = []
    for (sub, k, _), (nxt, _, _) in zip(trail, trail[1:] + [(None, None, None)]):
        if k == "properties":
            parts.append(next(n for n, s in sub["properties"].items() if s is nxt))
        elif k == "items":
            parts.append("0")
    return "/".join(parts)


def coverage():
    """{layer: (constraint count, [uncovered])}. P2-owned schemas: every (path, keyword) gets a code.
    Vendored schema: every constraint matches a row of the H table."""
    out = {}
    for layer, root in SCHEMAS.items():
        n, missing = 0, []
        for trail, kw in _constraints(root, [], root):
            if any(doc is HIF for _, _, doc in trail):
                continue  # the vendored branch of the profile is reported by layer H
            n += 1
            if code_for_steps(layer, trail) is None:
                missing.append(("/".join(str(k) for _, k, _ in trail)))
        out[layer] = (n, missing)
    n, missing = 0, []
    for trail, kw in _constraints(HIF, [], HIF):
        n += 1
        p = _h_example_path(trail)
        if h_code(kw, p) is None:
            missing.append(f"{kw} at {p!r}")
    out["H"] = (n, missing)
    return out


def code_map(layer):
    """(schema location, keyword, code) for every constraint: the table a reviewer reads."""
    root = SCHEMAS[layer]
    rows = []
    for trail, kw in _constraints(root, [], root):
        if any(doc is HIF for _, _, doc in trail):
            continue
        rows.append(("/".join(str(k) for _, k, _ in trail), kw, code_for_steps(layer, trail)))
    return rows


if __name__ == "__main__":
    for layer, (n, missing) in coverage().items():
        print(f"{layer}: {n} constraints, uncovered: {missing if missing else 'none'}")
