#!/usr/bin/env python3
"""What do xgi.read_hif and hnx.from_hif do with schema-INVALID HIF files? (P2 research, 2026-09-23)

Uses the hand-made cases of the sibling schema probe (hif-schema/cases/, read only). Each case is
validated here with jsonschema against the vendored hif-schema/hif_schema.json; every invalid one is
then given to both readers. Outcomes: loaded (and as what), returned None, or raised (with the
library frame). hnx.from_hif needs network access (it fetches its schema on every call).

Output: out/invalid-inputs.json
"""
import glob
import json
import os
import sys
import traceback
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from probe_common import OUT_DIR, dump, env_info, validate_hif  # noqa: E402

warnings.filterwarnings("ignore")
import xgi  # noqa: E402
import hypernetx as hnx  # noqa: E402

CASES = os.path.join(HERE, "hif-schema", "cases")


def outcome(fn, lib):
    try:
        v = fn()
    except Exception as e:
        tb = [f for f in traceback.extract_tb(e.__traceback__) if f"site-packages/{lib}/" in f.filename]
        where = f"{tb[-1].filename.split('site-packages/')[-1]}:{tb[-1].lineno}" if tb else None
        return f"raised {type(e).__name__}: {str(e)[:90]}" + (f" @ {where}" if where else "")
    if v is None:
        return "returned None"
    return f"loaded as {type(v).__name__}"


def main():
    rows = {}
    for path in sorted(glob.glob(os.path.join(CASES, "*.json"))):
        name = os.path.basename(path)
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except ValueError as e:
            rows[name] = {"parse": f"not JSON: {e}"}
            continue
        errs = validate_hif(doc)
        if not errs:
            continue  # only schema-invalid inputs are of interest here
        rows[name] = {
            "first_schema_error": errs[0],
            "xgi.read_hif": outcome(lambda: xgi.read_hif(path), "xgi"),
            "hnx.from_hif": outcome(lambda: hnx.from_hif(filename=path), "hypernetx"),
        }
        print(f"{name:52s} xgi: {rows[name]['xgi.read_hif'][:60]:60s} hnx: {rows[name]['hnx.from_hif'][:50]}")
    dump({"env": env_info(("xgi", "hypernetx")), "schema": "hif-schema/hif_schema.json", "cases": rows},
         os.path.join(OUT_DIR, "invalid-inputs.json"))


if __name__ == "__main__":
    main()
