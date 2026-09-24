"""Library-evidence run (tests/evidence/test_library_hif_io.py prototype, marker evidence, not the gate): what the
libraries' OWN HIF functions do with role-aware files, offline (HyperNetX's schema download is served from the vendored
copy). Writes <examples>/library-hif-evidence.json, the file the upstream issues attach.
usage: run_evidence.py <examples dir>   (venv-libs)"""
import copy
import json
import socket
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


class _NoNet(socket.socket):
    def connect(self, *a, **k):
        raise OSError("network disabled")


socket.socket = _NoNet
VENDORED = Path(__file__).resolve().parent.parent.parent / "probes" / "hif-schema" / "hif_schema_v0.1.0.json"
HS = json.loads(VENDORED.read_text())


class _Resp:
    text = json.dumps(HS)
    status_code = 200

    def json(self):
        return HS


EX = Path(sys.argv[1])
import xgi  # noqa: E402
import hypernetx as hnx  # noqa: E402
import hypernetx.hif as hh  # noqa: E402
hh.requests.get = lambda url, *a, **k: _Resp()


def summary(src, out):
    if out is None:
        return None
    roles = sum(1 for i in out["incidences"] if (i.get("attrs") or {}).get("role"))
    w_in = sum(1 for k in ("nodes", "edges", "incidences") for x in src.get(k, []) if "weight" in x)
    return {"incidences": [len(src["incidences"]), len(out["incidences"])], "roles_kept": [roles, len(src["incidences"])],
            "metadata_lost": sorted(set(src.get("metadata", {})) - set(out.get("metadata", {}))),
            "metadata_added": sorted(set(out.get("metadata", {})) - set(src.get("metadata", {}))),
            "weights_in_source": w_in,
            "isolated_nodes_kept": sorted({n["node"] for n in out.get("nodes", [])} &
                                          ({n["node"] for n in src.get("nodes", [])} -
                                           {i["node"] for i in src["incidences"]}))}


rows = []
files = ["fixture.hif.json", "fixture.directed-slice.hif.json", "role-convention/tail-head.hif.json",
         "role-convention/ordered.hif.json"]
for name in files:
    src = json.loads((EX / name).read_text())
    row = {"file": name, "network-type": src.get("network-type")}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(src, f, ensure_ascii=False)
        path = f.name
    try:
        X = xgi.read_hif(path)
        out = tempfile.mktemp(suffix=".json")
        xgi.write_hif(X, out)
        row["xgi"] = {"class": type(X).__name__, **summary(src, json.load(open(out)))}
    except Exception as e:  # noqa: BLE001
        row["xgi"] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    try:
        Hn = hnx.from_hif(copy.deepcopy(src))
        if Hn is None:
            row["hnx"] = {"from_hif": None}
        else:
            ho = hnx.to_hif(Hn, network_type=src.get("network-type", "undirected"))
            r = {"to_hif": None} if ho is None else summary(src, ho)
            if ho is not None:
                H2 = hnx.from_hif(ho)
                r["second_generation"] = None if H2 is None else "dict"
                if H2 is not None:
                    ho2 = hnx.to_hif(H2, network_type=src.get("network-type", "undirected"))
                    r["second_generation"] = None if ho2 is None else len(ho2["incidences"])
            row["hnx"] = r
    except Exception as e:  # noqa: BLE001
        row["hnx"] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))
(EX / "library-hif-evidence.json").write_text(json.dumps(
    {"format": "khg-library-evidence/1.0.0", "xgi": xgi.__version__, "hypernetx": hnx.__version__, "rows": rows},
    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
