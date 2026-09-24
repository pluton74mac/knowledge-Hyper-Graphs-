"""Library round trips of the gate fixture through the probe sketch (run with venv-libs: xgi 0.10.2,
hypernetx 2.4.3, pandas 2.3.3). Network access is disabled for the loader runs.

  A. HIF -> XGI -> HIF, HIF -> HNX -> HIF, and the gate chain HIF -> XGI -> HIF -> HNX -> HIF,
     each diffed with probe_common.diff_hif and then folded back to C1 and compared canonically.
  B. idempotence (second round identical)
  C. byte-level determinism of the chain under four PYTHONHASHSEED values (subprocess)
  D. library-evidence preview: what xgi.read_hif/write_hif and hnx.from_hif/to_hif do to the same file
     (HNX's schema fetch is served from the vendored file, so this also runs offline)
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
PROBES = "/home/user/knowledge-Hyper-Graphs-/projects/p2-role-aware-hif/research/probes"
sys.path.insert(0, HERE)
sys.path.insert(0, PROBES)
import proto  # noqa: E402
import role_loaders_sketch as rl  # noqa: E402
from probe_common import diff_hif  # noqa: E402

import requests  # noqa: E402


def offline(*a, **k):
    raise requests.ConnectionError("network disabled for this check")


requests.get = offline
import xgi  # noqa: E402
import hypernetx as hnx  # noqa: E402
from hypernetx import hif as hnx_hif  # noqa: E402

hnx_hif.requests.get = offline


def load(p):
    with open(p, encoding="utf-8") as f:
        return proto.strict_loads(f.read())


schema = proto.Schema(load(os.path.join(HERE, "builtin.schema.json")), load(os.path.join(HERE, "gate-demo.schema.json")))
fixture = load(os.path.join(HERE, "gate-fixture.khg.json"))
hif = load(os.path.join(HERE, "gate-fixture.hif.json"))
canon = proto.canonical_doc(fixture, schema)


def rt(doc, to, frm):
    H, ctx = to(copy.deepcopy(doc))
    out = json.loads(json.dumps(frm(H, ctx), allow_nan=False))
    return out, ctx


def exact(s):
    ok = s["pairs_lost"] == 0 and s["pairs_new"] == 0 and s["pairs_count_changed"] == 0
    ok &= s["weights_added_on_incidences"] == 0 and s["id_type_changes"] == 0
    ok &= s["network_type"].startswith("preserved") and s["metadata"] == "preserved"
    for k in ("nodes", "edges"):
        ok &= not any(s[k][f] for f in ("missing_out", "attrs_not_preserved", "weight_not_preserved", "new_out"))
    for k in ("role_records_kept", "direction_records_kept", "incidence_attrs_records_kept"):
        a, b = s[k].split("/")
        ok &= a == b
    return bool(ok)


def chain(doc):
    x, _ = rt(doc, rl.to_xgi, rl.from_xgi)
    return rt(x, rl.to_hnx, rl.from_hnx)[0]


if len(sys.argv) > 1 and sys.argv[1] == "--chain-bytes":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = chain(hif)
    print(hashlib.sha256(json.dumps(out, ensure_ascii=False).encode()).hexdigest())
    sys.exit(0)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    print("A/B. round trips through the sketch loaders (offline):")
    for name, fn in (("xgi", lambda d: rt(d, rl.to_xgi, rl.from_xgi)[0]),
                     ("hnx", lambda d: rt(d, rl.to_hnx, rl.from_hnx)[0]),
                     ("chain xgi->hnx", chain)):
        out = fn(hif)
        s = diff_hif(hif, out)["summary"]
        c1 = proto.from_hif(out, schema)
        out2 = fn(out)
        print(f"  {name:15} exact={exact(s)} roles={s['role_records_kept']} directions={s['direction_records_kept']} "
              f"incidence-attrs={s['incidence_attrs_records_kept']} records={s['incidence_records']} "
              f"C1-equal={c1 == canon} idempotent={out2 == out}")
        assert exact(s) and c1 == canon and out2 == out

    H, ctx = rl.to_xgi(copy.deepcopy(hif))
    print("  XGI object:", type(H).__name__, "| f3 in/out:", [sorted(x) for x in H.edges.dimembers("f3")],
          "| f5 head set:", sorted(H.edges.dimembers("f5")[1]))
    Hn, _ = rl.to_hnx(copy.deepcopy(hif))
    cells = Hn.incidences.to_dataframe
    print("  HNX cells:", len(cells), "for", len(hif["incidences"]), "incidence records;",
          "cell (f5, ex:YYZ) role:", Hn.get_cell_properties("f5", "ex:YYZ", "role"),
          "| extras riding in that cell:", len(cells.loc[("f5", "ex:YYZ"), "misc_properties"].get(rl.EXTRA, [])))

print("C. determinism of the chain output bytes under PYTHONHASHSEED 0..3:")
digests = set()
for seed in ("0", "1", "2", "3"):
    env = dict(os.environ, PYTHONHASHSEED=seed)
    r = subprocess.run([sys.executable, __file__, "--chain-bytes"], env=env, capture_output=True, text=True)
    digests.add(r.stdout.strip())
print("   distinct outputs:", len(digests), sorted(digests)[0][:16])

print("D. library-evidence preview (the libraries' own HIF functions on the same file):")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    tmp_in = os.path.join(HERE, "_tmp_in.hif.json")
    tmp_out = os.path.join(HERE, "_tmp_xgi_out.hif.json")
    json.dump(hif, open(tmp_in, "w", encoding="utf-8"), ensure_ascii=False)
    try:
        Hx = xgi.read_hif(tmp_in)
        xgi.write_hif(Hx, tmp_out)
        xo = json.load(open(tmp_out, encoding="utf-8"))
        s = diff_hif(hif, xo)["summary"]
        print(f"  xgi.read_hif/write_hif: roles={s['role_records_kept']} records={s['incidence_records']} "
              f"directions={s['direction_records_kept']} metadata={s['metadata']}")
    except Exception as e:
        print("  xgi.read_hif/write_hif raised", type(e).__name__, str(e)[:120])

    HIF_SCHEMA = json.load(open(os.path.join(PROBES, "hif-schema", "hif_schema_v0.1.0.json")))

    class _Resp:
        text = json.dumps(HIF_SCHEMA)

        def json(self):
            return HIF_SCHEMA
    hnx_hif.requests.get = lambda *a, **k: _Resp()   # serve the vendored schema: no network
    Hh = hnx.from_hif(copy.deepcopy(hif))
    if Hh is None:
        print("  hnx.from_hif returned None")
    else:
        ho = hnx.to_hif(Hh, network_type="directed")
        if ho is None:
            print("  hnx.to_hif returned None")
        else:
            s = diff_hif(hif, ho)["summary"]
            print(f"  hnx.from_hif/to_hif: roles={s['role_records_kept']} records={s['incidence_records']} "
                  f"metadata={s['metadata']} metadata_keys_lost={len(s['metadata_keys_lost'])} "
                  f"weights_added={s['weights_added_on_incidences']}")
    for p in (tmp_in, tmp_out):
        if os.path.exists(p):
            os.remove(p)
