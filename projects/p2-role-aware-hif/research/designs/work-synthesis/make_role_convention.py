"""Writes <examples>/role-convention/: the five files of the upstream fixture PR (F15, critique UPSTREAM). They use
role-convention 1.0.0 only (no khg keys) and must pass the vendored HIF schema and the R layer (rules 1-4)."""
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) / "role-convention"
OUT.mkdir(parents=True, exist_ok=True)
MD = {"role-convention": "1.0.0"}
I = lambda e, n, role, **kw: {"edge": e, "node": n, **({"direction": kw.pop("direction")} if "direction" in kw else {}),
                              "attrs": {"role": role, **kw}}
FILES = {
    "basic": {"network-type": "undirected",
              "metadata": dict(MD, **{"role-vocabulary": {"buyer": {"label": "buyer"}, "seller": {"label": "seller"},
                                                           "item": {"label": "item sold"}}}),
              "incidences": [I("sale-1", "alice", "buyer"), I("sale-1", "bob", "seller"), I("sale-1", "book-7", "item")]},
    "two-roles": {"network-type": "undirected", "metadata": dict(MD),
                  "incidences": [I("sale-2", "alice", "buyer"), I("sale-2", "alice", "payer"), I("sale-2", "bob", "seller")]},
    "tail-head": {"network-type": "directed", "metadata": dict(MD),
                  "incidences": [I("reg-1", "TP53", "regulator", direction="tail"),
                                 I("reg-1", "TP53", "target", direction="head"),
                                 I("reg-1", "HeLa", "context", direction="tail")]},
    "ordered": {"network-type": "undirected", "metadata": dict(MD),
                "incidences": [I("route-1", "AC", "carrier"), I("route-1", "YYZ", "stop", **{"role-position": 1}),
                               I("route-1", "YUL", "stop", **{"role-position": 2}),
                               I("route-1", "YYZ", "stop", **{"role-position": 3})]},
    "undirected": {"network-type": "undirected", "metadata": dict(MD),
                   "incidences": [I("cause-1", "metformin", "agent", direction="tail"),
                                  I("cause-1", "insulin", "agent", direction="tail"),
                                  I("cause-1", "hypoglycaemia", "effect", direction="head"),
                                  I("marriage-1", "maria", "spouse"), I("marriage-1", "pierre", "spouse")]},
}
for name, doc in FILES.items():
    (OUT / f"{name}.hif.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("role-convention files:", sorted(FILES))
