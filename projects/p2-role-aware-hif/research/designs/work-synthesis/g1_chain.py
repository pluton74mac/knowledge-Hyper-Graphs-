"""G1 chain, run in a child process per hash seed (G1-HASHSEED): prints the sha256 of the canonical serialisation of
every intermediate document: C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1, for the fixture and its directed slice.
usage: g1_chain.py <examples dir>   (venv-libs)"""
import copy
import hashlib
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
h = lambda o: "sha256:" + hashlib.sha256(K.cjson(o).encode("utf-8")).hexdigest()
out = {}
with E.no_network():
    L.set_schema_dir(EX / "schemas")
    c1 = json.loads((EX / "fixture.c1.json").read_text(encoding="utf-8"))
    S = K.Schema(json.loads((EX / "fixture.relation-schema.json").read_text(encoding="utf-8")))
    for name, rels in (("full", None), ("slice", ["born_in", "catalysed_by", "claims", "co_administration_causes",
                                                   "flight_route", "population", "position_held", "regulates",
                                                   "station_profile"])):
        h0 = K.c1_to_hif(c1, S, relations=rels)
        bx = L.load_xgi(copy.deepcopy(h0))
        h1 = L.export_xgi(bx)
        bh = L.load_hnx(copy.deepcopy(h1))
        h2 = L.export_hnx(bh)
        back = K.hif_to_c1(h2, S)
        out[name] = {"hif": h(h0), "after_xgi": h(h1), "after_hnx": h(h2), "c1": h(K.canonical_doc(back))}
print(json.dumps(out, sort_keys=True))
