#!/usr/bin/env python3
"""What HyperNetX 2.4.3 does with the schema it fetches: accept / reject / silently return None.

Needs hypernetx==2.4.3 and network access to raw.githubusercontent.com (HNX fetches the schema
from hypernetx.hif.schema_url on every call). It checks the schema gate only; whether roles
survive the round trip is a separate question.
"""
import json
import os
import warnings

warnings.filterwarnings("ignore")
import hypernetx as hnx  # noqa: E402
from hypernetx import hif as H  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
print("hypernetx", hnx.__version__, "| schema_url:", H.schema_url)

for case in [
    "01-baseline-role-in-incidence-attrs",
    "04-top-level-version-key",
    "08-metadata-roles-vocabulary",
    "11-incidence-record-level-role-key",
]:
    doc = json.load(open(os.path.join(HERE, "cases", case + ".json")))
    try:
        hg = hnx.from_hif(doc)
        print(f"from_hif({case}) -> {type(hg).__name__}")
    except Exception as e:  # report, do not hide
        print(f"from_hif({case}) raised {type(e).__name__}: {e}")

hg = hnx.from_hif(json.load(open(os.path.join(HERE, "cases", "01-baseline-role-in-incidence-attrs.json"))))
for md in (None, {"khg-profile": "example"}):
    out = hnx.to_hif(hg, metadata=md)
    shown = None if out is None else sorted((out.get("metadata") or {}).keys())
    print(f"to_hif(metadata={'dict' if md else None}) -> {type(out).__name__}; metadata keys: {shown}")
