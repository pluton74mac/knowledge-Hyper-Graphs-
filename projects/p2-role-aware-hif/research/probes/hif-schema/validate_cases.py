#!/usr/bin/env python3
"""Validate the P2 HIF probe cases (and the KB sample) against every HIF schema snapshot.

Usage:
    python validate_cases.py [--upstream-tests DIR]

Requires: jsonschema (tested 4.26.0), fastjsonschema (tested 2.22.2).
Writes results.json and results.md next to this script.

--upstream-tests DIR points at a checkout's tests/test_files directory of
HIF-org/HIF-standard (HIF-compliant/ and HIF-non-compliant/); when given, the
upstream calibration files are validated too, so the harness can be checked
against upstream's own expectations.
"""
import argparse
import glob
import json
import os
import sys
from importlib.metadata import version as pkg_version

import fastjsonschema
from jsonschema.validators import validator_for

HERE = os.path.dirname(os.path.abspath(__file__))
KB_SAMPLE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "schemas", "sample.hif.json"))

SCHEMAS = [
    # (short label, path, note)
    ("S0 2024-08-05 c58b153", "history/2024-08-05_c58b153_hif_schema.json", "initial list-based draft, superseded"),
    ("S1 2024-08-13 e5c868b", "history/2024-08-13_e5c868b_hif_schema_v0.1.0.json", "first object-record schema; key 'attr'"),
    ("S2 2024-08-21 53a8a93", "history/2024-08-21_53a8a93_hif_schema_v0.1.0.json", "+ top-level additionalProperties:false"),
    ("S3 2024-09-26 7aefda6", "history/2024-09-26_7aefda6_hif_schema_v0.1.0.json", "'attr' renamed 'attrs'"),
    ("S4 2024-10-03 de5f89f", "history/2024-10-03_de5f89f_hif_schema_v0.1.0.json", "+ record-level additionalProperties:false"),
    ("v0.1.0 (HEAD b691a3d)", "hif_schema_v0.1.0.json", "published, version 0.1.0"),
    ("latest (HEAD b691a3d)", "hif_schema.json", "published, version latest"),
]


class StrictJSONError(ValueError):
    pass


def _reject_constant(name):
    raise StrictJSONError(f"non-standard JSON constant {name}")


def _no_duplicate_keys(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise StrictJSONError(f"duplicate object key {k!r}")
        seen.add(k)
    return dict(pairs)


def load(path):
    """Return (doc, lenient_parse_error, strict_json_problem)."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}", "not JSON"
    strict = None
    try:
        json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_no_duplicate_keys)
    except StrictJSONError as e:
        strict = str(e)
    return doc, None, strict


def first_error_jsonschema(validator, doc):
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if not errors:
        return True, ""
    e = errors[0]
    path = "/".join(str(p) for p in e.absolute_path) or "(root)"
    return False, f"{path}: {e.message}"[:160]


def run(case_paths):
    compiled = []
    for label, rel, note in SCHEMAS:
        schema = json.load(open(os.path.join(HERE, rel)))
        cls = validator_for(schema)
        cls.check_schema(schema)
        compiled.append((label, rel, note, cls.__name__, cls(schema), fastjsonschema.compile(schema)))

    results = []
    for path in case_paths:
        doc, parse_err, strict = load(path)
        row = {"case": os.path.relpath(path, HERE), "strict_json_problem": strict, "by_schema": {}}
        for label, rel, note, cls_name, js_val, fjs in compiled:
            if parse_err:
                row["by_schema"][label] = {"jsonschema": "parse-error", "fastjsonschema": "parse-error", "detail": parse_err}
                continue
            ok_js, msg_js = first_error_jsonschema(js_val, doc)
            try:
                fjs(doc)
                ok_f, msg_f = True, ""
            except fastjsonschema.JsonSchemaException as e:
                ok_f, msg_f = False, str(e)[:160]
            row["by_schema"][label] = {
                "jsonschema": "valid" if ok_js else "invalid",
                "fastjsonschema": "valid" if ok_f else "invalid",
                "detail": msg_js or msg_f,
            }
        results.append(row)
    return compiled, results


def to_markdown(compiled, results, title):
    labels = [c[0] for c in compiled]
    out = [f"### {title}", "", "| case | strict JSON | " + " | ".join(labels) + " |", "|---|---|" + "---|" * len(labels)]
    for r in results:
        cells = []
        for lab in labels:
            v = r["by_schema"][lab]
            if v["jsonschema"] == v["fastjsonschema"]:
                cells.append(v["jsonschema"])
            else:
                cells.append(f"js:{v['jsonschema']} / fjs:{v['fastjsonschema']}")
        strict = r["strict_json_problem"] or "ok"
        out.append(f"| `{r['case']}` | {strict} | " + " | ".join(cells) + " |")
    out.append("")
    # first error per case under the published schema
    out.append("First error reported by jsonschema under `latest (HEAD b691a3d)` (empty = valid):")
    out.append("")
    for r in results:
        d = r["by_schema"][labels[-1]]["detail"]
        if d:
            out.append(f"- `{r['case']}`: {d}")
    out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream-tests", default=None)
    args = ap.parse_args()

    case_paths = sorted(glob.glob(os.path.join(HERE, "cases", "*.json")))
    if os.path.exists(KB_SAMPLE):
        case_paths = [KB_SAMPLE] + case_paths
    compiled, results = run(case_paths)
    md = [
        "# HIF probe results",
        "",
        f"jsonschema {pkg_version('jsonschema')} "
        f"(validator class chosen from each schema's $schema: {sorted({c[3] for c in compiled})}), "
        f"fastjsonschema {fastjsonschema.VERSION}, Python {sys.version.split()[0]}.",
        "",
        "Cells read `valid` / `invalid` when both validators agree; otherwise `js:<jsonschema> / fjs:<fastjsonschema>`.",
        "`strict JSON` flags NaN/Infinity literals and duplicate object keys, which Python's json module accepts.",
        "",
        "Schemas:",
        "",
    ]
    for label, rel, note, cls_name, _, _ in compiled:
        md.append(f"- **{label}**: `{rel}` ({note}; {cls_name})")
    md.append("")
    md.append(to_markdown(compiled, results, "P2 cases and the KB sample"))
    payload = {"cases": results}

    if args.upstream_tests:
        up = sorted(glob.glob(os.path.join(args.upstream_tests, "HIF-compliant", "*.json"))) + sorted(
            glob.glob(os.path.join(args.upstream_tests, "HIF-non-compliant", "*.json"))
        )
        _, up_results = run(up)
        for r in up_results:
            r["case"] = "/".join(r["case"].split(os.sep)[-2:])
        md.append(to_markdown(compiled, up_results, "Upstream calibration files (tests/test_files)"))
        payload["upstream_calibration"] = up_results

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(payload, f, indent=1)
        f.write("\n")
    with open(os.path.join(HERE, "results.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
