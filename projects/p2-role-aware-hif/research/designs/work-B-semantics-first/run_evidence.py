"""(1) HIF-level multiset comparison through the sketch loaders; (2) what the libraries' own HIF I/O drops."""
import json, sys, copy, socket, tempfile, collections, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
class _NoNet(socket.socket):
    def connect(self, *a, **k): raise OSError("network disabled")
socket.socket = _NoNet
from khg_proto import cjson
import role_loaders_sketch as sk

def ms(doc, key):
    return collections.Counter(cjson(x) for x in doc.get(key, []))

def roles(doc):
    return collections.Counter((i["edge"], i["node"], i.get("direction"), (i.get("attrs") or {}).get("role"),
                                (i.get("attrs") or {}).get("role-position"), (i.get("attrs") or {}).get("khg:bid")) for i in doc["incidences"])

HIF_SCHEMA = json.loads((HERE / "hif_schema_v0.1.0.json").read_text())
_TEXT = json.dumps(HIF_SCHEMA)
class _Resp:
    text = _TEXT
    status_code = 200
    def json(self): return HIF_SCHEMA

for fx in ("fixture-directed", "fixture-undirected"):
    hif = json.loads((HERE / f"{fx}.hif.json").read_text())
    H, c = sk.to_xgi(copy.deepcopy(hif)); a = sk.from_xgi(H, c)
    G, c2 = sk.to_hnx(copy.deepcopy(a)); b = sk.from_hnx(G, c2)
    print(f"== {fx}: sketch chain HIF->XGI->HIF->HNX->HIF")
    for k in ("incidences", "nodes", "edges"):
        print(f"   {k}: multiset equal = {ms(hif, k) == ms(b, k)}")
    print("   metadata equal =", hif["metadata"] == b["metadata"], "| network-type equal =", hif["network-type"] == b.get("network-type"))
    print("   (edge,node,direction,role,position,bid) tuples equal =", roles(hif) == roles(b), f"({sum(roles(hif).values())} incidences)")
    pairs = collections.Counter((i["edge"], i["node"]) for i in hif["incidences"])
    print("   repeated (edge,node) pairs in source:", {f"{e}|{n}": k for (e, n), k in pairs.items() if k > 1})

    # library-native HIF functions (the 'library evidence' test)
    import xgi
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(hif, f, ensure_ascii=False); path = f.name
    X = xgi.read_hif(path)
    out = tempfile.mktemp(suffix=".json"); xgi.write_hif(X, out)
    xo = json.load(open(out))
    kept = sum(1 for i in xo["incidences"] if (i.get("attrs") or {}).get("role"))
    print(f"   xgi.read_hif/write_hif: incidences {len(hif['incidences'])} -> {len(xo['incidences'])}; records with role kept {kept}/{len(hif['incidences'])}")
    import hypernetx as hnx, hypernetx.hif as hh
    hh.requests.get = lambda url, *a, **k: _Resp()          # offline: vendored schema instead of the network
    try:
        Hn = hnx.from_hif(hif)
        if Hn is None:
            print("   hnx.from_hif: returned None")
        else:
            ho = hnx.to_hif(Hn, network_type=hif["network-type"])
            if ho is None:
                print("   hnx.to_hif: returned None")
            else:
                kept = sum(1 for i in ho["incidences"] if (i.get("attrs") or {}).get("role"))
                lost_md = sorted(set(hif["metadata"]) - set(ho.get("metadata", {})))
                print(f"   hnx.from_hif/to_hif: incidences {len(hif['incidences'])} -> {len(ho['incidences'])}; role records kept {kept}; metadata keys lost {len(lost_md)} of {len(hif['metadata'])}; nodes {len(hif['nodes'])} -> {len(ho.get('nodes', []))}")
                Hn2 = hnx.from_hif(ho)
                ho2 = None if Hn2 is None else hnx.to_hif(Hn2, network_type=hif["network-type"])
                print("   hnx second generation to_hif:", "None" if ho2 is None else f"dict with {len(ho2['incidences'])} incidences")
    except Exception as e:
        print("   hnx native raised:", type(e).__name__, str(e)[:120])
