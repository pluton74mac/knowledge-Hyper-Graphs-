"""Render gate-full.hif.json in the reading layout used by the design (one record per line).

Writes gate-full.hif.pretty.json; assemble.py checks that it parses to the same document as gate-full.hif.json.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def c(o):
    return json.dumps(o, ensure_ascii=False, separators=(", ", ": "))


def k(s):
    return json.dumps(s, ensure_ascii=False)


def items(pad, rows):
    return ",\n".join(pad + r for r in rows)


def schema_doc(s, pad):
    rows = []
    for key, val in s.items():
        if key in ("entity_types", "roles", "relations"):
            rows.append(f"{k(key)}: [\n" + items(pad + " ", [c(x) for x in val]) + f"\n{pad}]")
        else:
            rows.append(f"{k(key)}: {c(val)}")
    return "{\n" + items(pad, rows) + "\n" + pad[:-1] + "}"


def render(doc):
    md = doc["metadata"]
    mrows = []
    for key, val in md.items():
        if key == "roles-vocabulary":
            mrows.append(f"{k(key)}: {{\n" + items("   ", [f"{k(r)}: {c(v)}" for r, v in val.items()]) + "\n  }")
        elif key == "khg-schemas":
            mrows.append(f"{k(key)}: [" + ", ".join(schema_doc(s, "   ") for s in val) + "]")
        else:
            mrows.append(f"{k(key)}: {c(val)}")
    top = [f"{k('network-type')}: {c(doc['network-type'])}", f"{k('metadata')}: {{\n" + items("  ", mrows) + "\n }"]
    for key in ("nodes", "edges", "incidences"):
        top.append(f"{k(key)}: [\n" + items("  ", [c(x) for x in doc[key]]) + "\n ]")
    return "{\n" + items(" ", top) + "\n}"


if __name__ == "__main__":
    with open(os.path.join(HERE, "gate-full.hif.json"), encoding="utf-8") as f:
        doc = json.load(f)
    text = render(doc)
    assert json.loads(text) == doc
    with open(os.path.join(HERE, "gate-full.hif.pretty.json"), "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote gate-full.hif.pretty.json: {text.count(chr(10)) + 1} lines")
