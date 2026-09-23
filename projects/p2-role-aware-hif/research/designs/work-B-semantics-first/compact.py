import json, sys
def compact(doc):
    lines = ["{"]
    keys = list(doc.keys())
    for k_i, k in enumerate(keys):
        v = doc[k]
        comma = "," if k_i < len(keys) - 1 else ""
        if isinstance(v, list):
            lines.append(f' {json.dumps(k)}: [')
            for i, x in enumerate(v):
                lines.append("  " + json.dumps(x, ensure_ascii=False, separators=(", ", ": ")) + ("," if i < len(v) - 1 else ""))
            lines.append(" ]" + comma)
        elif isinstance(v, dict) and k == "metadata":
            lines.append(f' {json.dumps(k)}: {{')
            items = list(v.items())
            for i, (a, b) in enumerate(items):
                lines.append(f'  {json.dumps(a)}: {json.dumps(b, ensure_ascii=False)}' + ("," if i < len(items) - 1 else ""))
            lines.append(" }" + comma)
        else:
            lines.append(f' {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}{comma}')
    lines.append("}")
    return "\n".join(lines)
for f in sys.argv[1:]:
    d = json.load(open(f))
    t = compact(d)
    assert json.loads(t) == d
    open(f.replace(".json", ".compact.json"), "w").write(t)
    print(f, "->", len(t.splitlines()), "lines")
