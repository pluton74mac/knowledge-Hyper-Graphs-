"""The R03 library cases (c00 = schemas/sample.hif.json, c01-c26) through the revised loaders with validate='none':
load_xgi -> export_xgi -> load_hnx -> export_hnx must reproduce the file (records compared as documents: same
network-type, metadata, node and edge records and incidence records in source order), or be refused with a code.
Writes <examples>/r03-loader-cases.json.  usage: r03_cases.py <examples dir>  (venv-libs)"""
import copy
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))
import khg_synth as K  # noqa: E402
import khg_loaders as L  # noqa: E402
import khg_engines_proto as E  # noqa: E402

EX = Path(sys.argv[1])
CASES = Path(__file__).resolve().parents[2] / "probes" / "lib-cases"
files = [Path(__file__).resolve().parents[5] / "schemas" / "sample.hif.json"] + sorted(CASES.glob("c*.json"))


def norm(d):
    """Structural view: records as multisets per kind; incidences also in order (F10: structural comparison)."""
    return {"network-type": d.get("network-type"), "metadata": d.get("metadata"),
            "nodes": sorted(K.cjson(x) for x in d.get("nodes", [])), "edges": sorted(K.cjson(x) for x in d.get("edges", [])),
            "incidences": [K.cjson(x) for x in d.get("incidences", [])]}


rows = []
with E.no_network():
    for p in files:
        name = "c00-kb-sample" if p.name == "sample.hif.json" else p.stem.replace(".hif", "")
        try:
            doc = K.strict_loads(p.read_text(encoding="utf-8"))
        except K.KHGError as e:
            rows.append({"case": name, "outcome": f"refused {e.code} (strict parse)"})
            continue
        try:
            bx = L.load_xgi(copy.deepcopy(doc), validate="none")
            hx = L.export_xgi(bx)
            bh = L.load_hnx(copy.deepcopy(hx), validate="none")
            hh = L.export_hnx(bh)
            exact = norm(hh) == norm(doc) and norm(hx) == norm(doc)
            diff = [k for k in ("network-type", "metadata", "nodes", "edges", "incidences") if norm(hh)[k] != norm(doc)[k]]
            rows.append({"case": name, "outcome": "exact" if exact else f"differs: {diff}"})
        except L.LoaderError as e:
            rows.append({"case": name, "outcome": f"refused {e.code}"})
        except Exception as e:  # noqa: BLE001
            rows.append({"case": name, "outcome": f"library error {type(e).__name__}: {str(e)[:80]}"})
for r in rows:
    print(f"{r['case']:48} {r['outcome']}")
(EX / "r03-loader-cases.json").write_text(json.dumps({"format": "khg-r03-cases/1.0.0", "rows": rows}, ensure_ascii=False,
                                                     indent=1) + "\n", encoding="utf-8")
