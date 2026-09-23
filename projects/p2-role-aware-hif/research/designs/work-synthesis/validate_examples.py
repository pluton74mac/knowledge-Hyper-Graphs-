"""Validates the design examples, offline (sockets blocked before anything is imported).

usage: validate_examples.py <examples dir> schema   (venv-hif: jsonschema, fastjsonschema)
       validate_examples.py <examples dir> libs     (venv-libs: xgi 0.10.2, hypernetx 2.4.3, pandas, jsonschema)
schema: strict J parse of every example; the vendored HIF schema and the draft schemas under both engines with closed
resolvers; the layered validator on every base; round trips and variants; derived vectors; RFC 8785 and time windows;
projections; queue keys, decision hash and replay; registry, malformed cases (full G2 rule) and scenarios.
libs: the G1 chain with library-object checks and native edits; the hash-seed subprocesses against the golden file;
the native-operation table; the convention-only files through both loaders."""
import copy
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


class _NoNet(socket.socket):
    def connect(self, *a, **k):
        raise OSError("network disabled")


socket.socket = _NoNet
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import khg_synth as K  # noqa: E402

EX = Path(sys.argv[1])
MODE = sys.argv[2] if len(sys.argv) > 2 else "schema"
ok = True
TAG = "tag:khg-contracts,2026:schema/"


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def load(name):
    return K.strict_loads((EX / name).read_text(encoding="utf-8"))


def lines(name):
    return [K.strict_loads(x) for x in (EX / name).read_text(encoding="utf-8").splitlines() if x.strip()]


c1 = load("fixture.c1.json")
schema_doc = load("fixture.relation-schema.json")
S = K.Schema(schema_doc)
hif, sl = load("fixture.hif.json"), load("fixture.directed-slice.hif.json")
TEXTS = {k: v["text"] for k, v in load("fixture.doc-texts.json")["texts"].items()}
SLICE_RELS = sl["metadata"]["khg-slice"]["relations"]

if MODE == "schema":
    import khg_engines_proto as E
    import khg_validate_proto as VP
    import khg_store_proto as P
    import khg_c5_proto as C5
    # ------------------------------------------------------------------ 1. strict JSON everywhere
    jfiles = sorted(p for p in EX.rglob("*.json"))
    bad = []
    for p in jfiles:
        try:
            K.strict_loads(p.read_text(encoding="utf-8"))
        except K.KHGError as e:
            bad.append(f"{p.name}: {e}")
    for p in sorted(EX.rglob("*.jsonl")):
        try:
            [K.strict_loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        except K.KHGError as e:
            bad.append(f"{p.name}: {e}")
    check(f"strict JSON (layer J) on every example: {len(jfiles)} .json and {len(list(EX.rglob('*.jsonl')))} .jsonl files",
          not bad, "; ".join(bad[:3]))
    # ------------------------------------------------------------------ 2. schemas under both engines, offline
    with E.no_network():
        SCH = E.load_schemas(EX / "schemas")
        raw = E.VENDORED.read_bytes()
        check("vendored hif_schema_v0.1.0.json hashes to 639466b7...2196 and equals the declared hif-schema-sha256",
              hashlib.sha256(raw).hexdigest() == K.HIF_SCHEMA_SHA256 ==
              hif["metadata"]["hif-schema-sha256"][7:] == sl["metadata"]["hif-schema-sha256"][7:])
        hifs = {"fixture.hif.json": hif, "fixture.directed-slice.hif.json": sl, "sample.khg.hif.json": load("sample.khg.hif.json")}
        rc = {f"role-convention/{p.name}": K.strict_loads(p.read_text(encoding="utf-8"))
              for p in sorted((EX / "role-convention").glob("*.json"))}
        c1s = {"fixture.c1.json": c1, "fixture.history.c1.json": load("fixture.history.c1.json"),
               "smoke-base.c1.json": load("smoke-base.c1.json"), "sample.khg.json": load("sample.khg.json"),
               "fixture.with-derived.c1.json": load("fixture.with-derived.c1.json")}
        for eng in ("jsonschema", "fastjsonschema"):
            Vh = E.validators(SCH, E.HIF_ID, engines=(eng,))[eng]
            errs = {n: Vh.findings(d) for n, d in list(hifs.items()) + list(rc.items())}
            check(f"[{eng}] {len(errs)} HIF files valid against the vendored schema (closed resolver)",
                  not any(errs.values()), str({k: v[:1] for k, v in errs.items() if v}))
            Vp = E.validators(SCH, TAG + "khg-hif/1.0.0", engines=(eng,))[eng]
            errs = {n: Vp.findings(d) for n, d in hifs.items()}
            check(f"[{eng}] khg-hif profile schema (allOf the vendored $id) accepts the 3 khg-hif files",
                  not any(errs.values()), str({k: v[:1] for k, v in errs.items() if v}))
            Vr = E.validators(SCH, TAG + "khg-record/1.0.0", engines=(eng,))[eng]
            errs = {n: Vr.findings(d) for n, d in c1s.items()}
            Vl = E.validators(SCH, TAG + "khg-record/1.0.0", "/definitions/record", engines=(eng,))[eng]
            jl = lines("fixture.c1.jsonl")
            errs["fixture.c1.jsonl"] = [f for x in jl[1:] for f in Vl.findings(x)]
            check(f"[{eng}] khg-record schema accepts {len(errs)} C1 containers (JSONL lines by #/definitions/record)",
                  not any(errs.values()), str({k: v[:1] for k, v in errs.items() if v}))
            Vc4 = E.validators(SCH, TAG + "khg-c4-items/0.1.0", engines=(eng,))[eng]
            Vio = E.validators(SCH, TAG + "khg-c5-io/1.0.0", engines=(eng,))[eng]
            e4 = [f for x in lines("c4-items.jsonl") for f in Vc4.findings(x)]
            e5 = [f for x in lines("c5-outputs.jsonl") for f in Vio.findings(x)]
            check(f"[{eng}] c4-items.jsonl (tag: refs into khg-record) and c5-outputs.jsonl valid", not e4 and not e5,
                  str((e4[:1], e5[:1])))
            try:
                E.validators(dict(SCH, **{"tag:x": {"$id": "tag:x", "$ref": "https://example.org/x.json"}}), "tag:x",
                             engines=(eng,))[eng].findings({})
                closed = False
            except Exception:  # noqa: BLE001
                closed = True
            check(f"[{eng}] a $ref to anything not packaged fails closed (nothing is fetched)", closed)
            # layered validator on every base
            V = VP.Validator(EX / "schemas", engine=eng)
            base_errs = {}
            for n, d in c1s.items():
                sd = load("sample.relation-schema.json") if n.startswith("sample") else schema_doc
                base_errs[n] = VP.errors(V.validate(d, "c1", schema_doc=sd, doc_texts=TEXTS, stop="all"))
            for n, d in hifs.items():
                sd = load("sample.relation-schema.json") if n.startswith("sample") else schema_doc
                base_errs[n] = VP.errors(V.validate(d, "hif", schema_doc=sd, doc_texts=TEXTS, stop="all"))
            for n in ("fixture", "cyclic", "wikidata-shaped", "r05", "sample"):
                base_errs[f"{n}.relation-schema.json"] = VP.errors(V.validate(load(f"{n}.relation-schema.json"),
                                                                              "relation-schema", stop="all"))
            base_errs["smoke-queue"] = VP.errors(V.validate(lines("smoke-queue.khg-queue.jsonl"), "queue", schema_doc=schema_doc,
                                                            bases={"p2-smoke-base": load("smoke-base.c1.json")}, stop="all"))
            base_errs["c4-items"] = VP.errors(V.validate(lines("c4-items.jsonl"), "c4", schema_doc=schema_doc,
                                                         doc_texts=TEXTS, stop="all"))
            for n, d in rc.items():
                base_errs[n] = VP.errors(V.validate(d, "role-convention", stop="all"))
            check(f"[{eng}] the layered validator reports no error on {len(base_errs)} bases", not any(base_errs.values()),
                  str({k: v[:1] for k, v in base_errs.items() if v}))
            warns = [f["code"] for f in V.validate(c1, "c1", schema_doc=schema_doc, doc_texts=TEXTS, stop="all")]
            check(f"[{eng}] the fixture's only findings are the two designed warnings (S024 must_differ, L008 handover)",
                  sorted(warns) == ["KHG-L008", "KHG-S024"], str(warns))
    # ------------------------------------------------------------------ 3. round trips and variants
    check("fixture.c1.jsonl holds the same header and records as fixture.c1.json",
          lines("fixture.c1.jsonl") == [c1["header"]] + c1["records"])
    check("header schema sha256 = digest('khg-schema/1', schema document)", c1["header"]["schema"]["sha256"] == S.sha256())
    check("fixture is in canonical form", K.cjson(K.canonical_doc(c1)) == K.cjson(c1))
    check("C1 -> HIF is deterministic and equals fixture.hif.json", K.c1_to_hif(c1, S) == hif)
    check("HIF -> C1 equals the fixture (canonical)", K.cjson(K.canonical_doc(K.hif_to_c1(hif, S))) == K.cjson(c1))
    want_sl = K.canonical_doc(K.select_slice(c1, set(SLICE_RELS)))
    check("the directed slice equals to_hif(relations=...) and decodes to the slice (khg-complete false)",
          K.c1_to_hif(c1, S, relations=SLICE_RELS) == sl and sl["metadata"]["khg-complete"] is False and
          K.cjson(K.canonical_doc(K.hif_to_c1(sl, S))) == K.cjson(want_sl))
    pb = K.c1_to_hif(c1, S, literal_nodes="per_binding")
    check("per-binding literal nodes (_:litb:) round-trip; khg-literal-nodes per_binding",
          pb["metadata"]["khg-literal-nodes"] == "per_binding" and
          K.cjson(K.canonical_doc(K.hif_to_c1(pb, S))) == K.cjson(c1) and
          sum(1 for n in pb["nodes"] if n["node"].startswith("_:litb:")) == 20)
    inl = K.c1_to_hif(c1, S, schema_document=True)
    check("an inlined schema (khg-schema-document) lets from_hif run without a schema argument",
          K.cjson(K.canonical_doc(K.hif_to_c1(inl))) == K.cjson(c1))
    try:
        K.hif_to_c1(hif)
        check("from_hif without a schema and without khg-schema-document raises D009", False)
    except K.KHGError as e:
        check("from_hif without a schema and without khg-schema-document raises D009", e.code == "KHG-D009")
    cl = K.c1_to_hif(c1, S, relations=["claims"])
    ext = [n for n in cl["nodes"] if n["attrs"].get("khg-external")]
    check("a slice of claims alone keeps f:born-louis14-paris as an external reference and decodes",
          [n["node"] for n in ext] == ["_:ref:f:born-louis14-paris"] and bool(K.hif_to_c1(cl, S)))
    counts = {n: dict(nodes=len(h["nodes"]), edges=len(h["edges"]), incidences=len(h["incidences"]),
                      with_direction=sum(1 for i in h["incidences"] if "direction" in i),
                      weights=sum(1 for k in ("nodes", "edges", "incidences") for x in h[k] if "weight" in x))
              for n, h in (("full", hif), ("slice", sl))}
    print("counts", json.dumps(counts))
    # ------------------------------------------------------------------ 4. derived vectors, numbers, time
    check("fixture.with-derived.c1.json equals with_derived(fixture)", K.cjson(load("fixture.with-derived.c1.json")) ==
          K.cjson(K.with_derived(c1, S)))
    import struct
    APPB = [("0000000000000000", "0"), ("8000000000000000", "0"), ("0000000000000001", "5e-324"),
            ("8000000000000001", "-5e-324"), ("7fefffffffffffff", "1.7976931348623157e+308"),
            ("ffefffffffffffff", "-1.7976931348623157e+308"), ("4340000000000000", "9007199254740992"),
            ("c340000000000000", "-9007199254740992"), ("4430000000000000", "295147905179352830000"),
            ("44b52d02c7e14af5", "9.999999999999997e+22"), ("44b52d02c7e14af6", "1e+23"),
            ("44b52d02c7e14af7", "1.0000000000000001e+23"), ("444b1ae4d6e2ef4e", "999999999999999700000"),
            ("444b1ae4d6e2ef4f", "999999999999999900000"), ("444b1ae4d6e2ef50", "1e+21"),
            ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"), ("3eb0c6f7a0b5ed8d", "0.000001"),
            ("41b3de4355555553", "333333333.3333332"), ("41b3de4355555554", "333333333.33333325"),
            ("41b3de4355555555", "333333333.3333333"), ("41b3de4355555556", "333333333.3333334"),
            ("41b3de4355555557", "333333333.33333343"), ("becbf647612f3696", "-0.0000033333333333333333"),
            ("43143ff3c1cb0959", "1424953923781206.2")]
    got = [(h, K.es_number(struct.unpack(">d", bytes.fromhex(h))[0]), want) for h, want in APPB]
    check("RFC 8785 Appendix B: all 24 finite number vectors serialise as specified (NaN and Infinity are J004)",
          all(g == w for _, g, w in got), str([x for x in got if x[1] != x[2]]))
    s10 = copy.deepcopy(schema_doc)
    s10["confidence_scales"][0]["max"] = 10.0
    check("max 10 and max 10.0 give the same khg-schema/1 digest", K.Schema(s10).sha256() == S.sha256())
    W = lambda t, p, cal=None: [K.fmt_instant(x) for x in K.time_window({"datatype": "time", "time": t, "precision": p,
                                                                        **({"calendar": cal} if cal else {})})]
    tv = [(("+1900-00-00T00:00:00Z", 7), ["+1801-01-01T00:00:00Z", "+1901-01-01T00:00:00Z"]),
          (("+1901-00-00T00:00:00Z", 7), ["+1901-01-01T00:00:00Z", "+2001-01-01T00:00:00Z"]),
          (("+2000-00-00T00:00:00Z", 6), ["+1001-01-01T00:00:00Z", "+2001-01-01T00:00:00Z"]),
          (("+1995-00-00T00:00:00Z", 8), ["+1990-01-01T00:00:00Z", "+2000-01-01T00:00:00Z"]),
          (("-0100-00-00T00:00:00Z", 7, "julian"), ["-0100-12-30T00:00:00Z", "+0000-12-30T00:00:00Z"]),
          (("-0044-03-15T00:00:00Z", 11, "julian"), ["-0043-03-13T00:00:00Z", "-0043-03-14T00:00:00Z"]),
          (("+1700-00-00T00:00:00Z", 9, "julian"), ["+1700-01-11T00:00:00Z", "+1701-01-12T00:00:00Z"]),
          (("+2019-00-00T00:00:00Z", 9), ["+2019-01-01T00:00:00Z", "+2020-01-01T00:00:00Z"])]
    got = [(a, W(*a)) for a, _ in tv]
    check("precision windows: ordinal centuries and millennia, decades, BCE (historical years), Julian",
          all(W(*a) == w for a, w in tv), str([g for g, (a, w) in zip(got, tv) if g[1] != w]))
    j = K.literal_identity({"datatype": "time", "time": "+1582-10-05T00:00:00Z", "precision": 11, "calendar": "julian"})
    g = K.literal_identity({"datatype": "time", "time": "+1582-10-15T00:00:00Z", "precision": 11, "calendar": "gregorian"})
    check("Julian 1582-10-05 and Gregorian 1582-10-15 have one value identity", j == g)
    refused = []
    for lit in ({"datatype": "time", "time": "+0000-00-00T00:00:00Z", "precision": 9},
                {"datatype": "time", "time": "+1500-01-01T00:00:00Z", "precision": 11}):
        try:
            K.time_window(lit)
        except K.KHGError as e:
            refused.append(e.code)
    check("year 0 and a pre-1583 date without calendar are refused with S006", refused == ["KHG-S006", "KHG-S006"])
    try:
        K.parse_instant("1700")
        check("a partial date is not an as_of instant (C011)", False)
    except K.KHGError as e:
        check("a partial date is not an as_of instant (C011)", e.code == "KHG-C011")
    # the bound table, one fact per row, checked against the definite/possible readings
    k13 = next(r for r in c1["records"] if r.get("id") == "f:king-13")

    def variant(**b):
        r = copy.deepcopy(k13)
        for bid, v in b.items():
            if v is None:
                r["bindings"] = [x for x in r["bindings"] if x["bid"] != bid]
            else:
                next(x for x in r["bindings"] if x["bid"] == bid)["value"] = v
        return K.valid_time_view(S, r)
    rows = {"period": variant(), "since (end absent)": variant(b4=None), "since (end novalue)": variant(b4={"special": "novalue"}),
            "ended (end somevalue)": variant(b4={"special": "somevalue"}), "until (start absent)": variant(b3=None),
            "undated": variant(b3=None, b4=None), "since forever (start novalue)": variant(b3={"special": "novalue"})}
    print("bound table", json.dumps({k: [v["kind"], v["definite"], v["possible"]] for k, v in rows.items()}))
    check("bound table: kinds period, since, since, ended, until, undated; definite empty for ended, until, undated",
          [v["kind"] for v in rows.values()] == ["period", "since", "since", "ended", "until", "undated", "until"] and
          all(rows[k]["definite"] is None for k in ("ended (end somevalue)", "until (start absent)", "undated")))
    # ------------------------------------------------------------------ 5. projections and derived views
    labels = {r["id"]: r["label"] for r in c1["records"] if r["kind"] == "entity"}
    rec = {r["id"]: r for r in c1["records"] if r.get("id")}
    rt = K.render_text(rec["f:king-14"], labels, schema=S)
    check("render_text (khg-render/1) on f:king-14", rt == "position_held(holder: Louis XIV; position: King of France; "
          "replaces: Louis XIII) [+1643-05-14T00:00:00Z/11, +1715-09-01T00:00:00Z/11)", rt)
    pos = K.positional(rec["f:route-1"], S, widths={"stop": 4})
    check("project.positional on f:route-1 with a stop width of 4 pads with khg:none",
          pos == ("flight_route", "ex:AirCanada", "ex:YYZ", "ex:YUL", "ex:YYZ", "khg:none"), str(pos))
    try:
        K.positional(rec["f:route-1"], S)
        check("project.positional refuses an unbounded usage without a width", False)
    except ValueError:
        check("project.positional refuses an unbounded usage without a width", True)
    hr = K.hyper_relational(rec["f:king-14"], S)
    check("project.hyper_relational on f:king-14 (primary holder/position)",
          hr["subject"] == "ex:LouisXIV" and hr["object"] == "ex:KingOfFrance" and len(hr["qualifiers"]) == 3, str(hr))
    rdf = K.rdf_relation_instance(c1)
    back = K.from_rdf_relation_instance(rdf)
    nox = lambda bs: [{k: v for k, v in b.items() if k != "extensions"} for b in bs]
    want = {r["id"]: {"relation": r["relation"], "status": r["status"], "bindings": sorted(nox(r["bindings"]), key=K.bsortkey)}
            for r in c1["records"] if r["kind"] == "hyperedge"}
    check("project.rdf_relation_instance round-trips every binding (urn:khg: IRIs, RFC 3987 percent-encoding)",
          K.cjson(back) == K.cjson(want) and K.iri_decode(K.iri_encode("f:station-東京")) == "f:station-東京",
          f"{len(rdf)} triples; {K.iri_encode('ex:Łódź')}")
    check("project.incidence_rows round-trips every binding", K.cjson(K.from_incidence_rows(K.incidence_rows(c1))) == K.cjson(want),
          f"{len(K.incidence_rows(c1))} rows")
    import build_examples as B
    for nm, sch, cyc in (("fixture", schema_doc, True), ("cyclic", load("cyclic.relation-schema.json"), False),
                         ("wikidata-shaped", load("wikidata-shaped.relation-schema.json"), False)):
        acyc, res = B.gyo_acyclic(B.schema_hypergraph(sch)["hyperedges"])
        check(f"schema_hypergraph({nm}) is alpha-{'acyclic' if cyc else 'cyclic'} (GYO)", acyc == cyc, str(res))
    # ------------------------------------------------------------------ 6. queue, keys, decision hash, replay
    q = lines("smoke-queue.khg-queue.jsonl")
    item, entry = load("queue-item.json"), load("action-log.json")
    check("smoke queue: header, queue-item.json, a lint entry, action-log.json", [x["kind"] for x in q] ==
          ["queue-header", "queue-item", "log-entry", "log-entry"] and q[1] == item and q[3] == entry)
    pay = item["payload"]
    d = K.derived(S, {**pay, "status": "asserted"})
    check("item keys equal recomputation; the extracted evidence's stored event_hash equals khg-event/1 of the payload",
          item["keys"] == {"content_key": d["content_key"], "core_key": d["core_key"], "key_digest": d["key_digest"]} and
          all(e["event_hash"] == K.event_hash(d["content_key"], e) for e in pay["evidence"] if e["type"] == "extracted"))
    stored = dict(copy.deepcopy(pay), id="f:king-14", status="asserted")
    check("accept writes the fixture's f:king-14 (payload with id replaced and status asserted, nothing else)",
          K.canonical_record(stored) == K.canonical_record(rec["f:king-14"]))
    base = load("smoke-base.c1.json")
    st = P.ProtoStore(S)
    st.load(base, at="2000-01-01T00:00:00Z")
    rc_ = st.put(stored, actor=entry["actor"]["id"], at=entry["at"])
    dh = K.digest("khg-decision/1", [{"id": "f:king-14", "version": rc_["records"][0][1],
                                      "record": K.decision_view(st.get("f:king-14"))}])
    check("replay(base=smoke-base) re-runs the accept and reproduces decision_hash", dh == entry["decision_hash"] and
          q[0]["base"]["sha256"] == K.container_sha256(base), dh)
    exp_h = st.export("hif")
    check("the smoke store exports valid HIF (profile) and khg-json", bool(K.hif_to_c1(exp_h, S)) and
          st.export("khg-json")["header"]["document_id"] == "p2-smoke-base")
    # ------------------------------------------------------------------ 7. registry, malformed cases, scenarios
    reg = load("error-codes.json")
    codes = {c["code"]: c for c in reg["codes"]}
    check("error-codes.json: codes unique, KHG-<layer><3 digits>, layer letter matches; planned codes not registered",
          len(codes) == len(reg["codes"]) and all(re.fullmatch(r"KHG-[A-Z]\d{3}", c) and c[4] == v["layer"] for c, v in codes.items())
          and not set(codes) & {p["code"] for p in reg["planned"]},
          f"{len(codes)} registered, {sum(1 for v in codes.values() if v['status'] == 'active')} active, {len(reg['planned'])} planned")
    mc = load("malformed-cases.json")
    check("malformed cases: ids unique, every listed code registered and active",
          len({c["id"] for c in mc["cases"]}) == len(mc["cases"]) and
          all(codes.get(c["code"], {}).get("status") == "active" for c in mc["cases"]), f"{len(mc['cases'])} cases")
    r = subprocess.run([sys.executable, str(HERE / "make_malformed.py"), str(EX)], capture_output=True, text=True)
    last = r.stdout.strip().splitlines()[-3:]
    check("G2 rule, run mechanically on every case (make_malformed.py): no failure, engines agree, every active code covered",
          r.returncode == 0 and last[0] == "failures: 0 []" and last[1] == "engine containment failures: 0 []" and
          last[2] == "active codes not listed by any case: []", " | ".join(last))
    scen = sorted((EX / "conformance-scenarios").glob("S-*.json"))
    used = set()

    def _codes(o):
        if isinstance(o, dict):
            if "error" in o:
                used.add(o["error"])
            for v in o.values():
                _codes(v)
        elif isinstance(o, list):
            for v in o:
                _codes(v)
    sd = [K.strict_loads(p.read_text(encoding="utf-8")) for p in scen]
    _codes(sd)
    idx = load("conformance-scenarios/index.json")
    check("scenarios: khg-scenario/1.0.0, listed in index.json, error codes registered",
          all(x["format"] == "khg-scenario/1.0.0" for x in sd) and [x["id"] for x in sd] == sorted(s_["id"] for s_ in idx["scenarios"])
          and used <= set(codes), f"{len(sd)} scenarios, {len(used)} codes")
    r = subprocess.run([sys.executable, str(HERE / "run_scenarios.py"), str(EX)], capture_output=True, text=True)
    check("every scenario passes on the prototype store (all capabilities)", r.returncode == 0, r.stdout.strip().splitlines()[-1])
    ALL = ["literal_values", "special_values", "goals", "nesting", "ordered_roles", "valid_time", "transaction_time",
           "key_constraint", "atomic_writes", "history_export"]
    res = []
    for f in ALL + ["typedb-like", "none"]:
        caps = {"typedb-like": "literal_values,nesting,valid_time,key_constraint,atomic_writes", "none": ""}.get(
            f, ",".join(x for x in ALL if x != f))
        r = subprocess.run([sys.executable, str(HERE / "run_scenarios.py"), str(EX), "--capabilities", caps],
                           capture_output=True, text=True)
        res.append((f, r.returncode, r.stdout.strip().splitlines()[-1].split(" capabilities")[0]))
    check("capability-limited stores: only passed or inapplicable (each flag removed; TypeDB-like; no flags)",
          all(rc == 0 for _, rc, _ in res), "; ".join(f"-{f}: {o}" for f, _, o in res))
    # ------------------------------------------------------------------ 8. migration and memory gold
    ssch, sdoc, srep = B.migrate_sample(json.loads((HERE.parents[4] / "schemas" / "sample.hif.json").read_text(encoding="utf-8")))
    check("the v0 sample migrates to the committed goldens (schema, container, HIF, report codes)",
          ssch == load("sample.relation-schema.json") and K.cjson(sdoc) == K.cjson(load("sample.khg.json")) and
          K.c1_to_hif(sdoc, K.Schema(ssch)) == load("sample.khg.hif.json") and
          [f["code"] for f in srep] == [f["code"] for f in load("sample.migration-report.json")["findings"]])
    c4 = {x.get("qid") or x.get("trace_id") or x["kind"]: x for x in lines("c4-items.jsonl")}
    gold = {k: (c4[k]["answer"]["values"], c4[k]["stale_values"], c4[k]["future_values"]) for k in
            ("mq:king-1700", "mq:king-1620", "mq:maria-birthplace")}
    E_ = lambda i: {"entity": i}
    check("memory gold (C5-HANDCHECK): 1700 -> LouisXIV, LouisXIII expired; 1620 -> LouisXIII, LouisXIV future; "
          "Maria -> Warszawa, Kraków revised",
          gold == {"mq:king-1700": ([E_("ex:LouisXIV")], [{"value": E_("ex:LouisXIII"), "kind": "expired"}], []),
                   "mq:king-1620": ([E_("ex:LouisXIII")], [], [E_("ex:LouisXIV")]),
                   "mq:maria-birthplace": ([E_("ex:Warszawa")], [{"value": E_("ex:Kraków"), "kind": "revised"}], [])},
          str(gold))
    conf7 = [0.95] * 4 + [0.55] * 4 + [0.15] * 2
    corr7 = [1, 1, 1, 0, 1, 1, 0, 0, 0, 0]
    vals = (C5.ece(conf7, corr7, bins=10), C5.ece(conf7, corr7, bins=15), C5.ece(conf7, corr7, bins=15, binning="equal_mass"),
            C5.ece([0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1], bins=2), C5.ece([0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1], bins=2, binning="equal_mass"),
            C5.ece(conf7[:5], corr7[:5]), C5.ece(conf7[5:], corr7[5:]))
    check("calibration hand values: C7 ECE 13/100 (10 and 15 bins, and equal-mass); C7b 1/4 width vs 2/5 mass; "
          "C8 1/4 and 19/100", vals == (Fraction(13, 100), Fraction(13, 100), Fraction(13, 100), Fraction(1, 4),
                                        Fraction(2, 5), Fraction(1, 4), Fraction(19, 100)), str(vals))
    units = [{"bids": [["h", "b1"], ["h", "b2"]]}, {"bids": [["h", "b1"], ["h", "b3"]]}]
    gb = [("h", "b1"), ("h", "b2"), ("h", "b3")]
    check("binding_coverage@k hand values: @1 = 2/3, @2 = 1", (C5.binding_coverage_at_k(gb, units, 1),
                                                                 C5.binding_coverage_at_k(gb, units, 2)) == (Fraction(2, 3), 1))
    lo, hi = C5.bootstrap_ci([0, 1, 1, 0, 1, 1, 1, 0, 1, 1], resamples=1000, seed=0)
    check("percentile bootstrap (indices int(rng.random() * n), random.Random(0)) is reproducible",
          (lo, hi) == C5.bootstrap_ci([0, 1, 1, 0, 1, 1, 1, 0, 1, 1], resamples=1000, seed=0), f"95% CI {lo}..{hi}")
else:
    import warnings
    warnings.filterwarnings("ignore")
    import xgi
    import khg_engines_proto as E
    import khg_loaders as L
    import khg_store_proto as P
    E_ok = True
    with E.no_network():
        L.set_schema_dir(EX / "schemas")
        for n, h in (("full", hif), ("slice", sl)):
            bx = L.load_xgi(copy.deepcopy(h))
            hx = L.export_xgi(bx)
            bh = L.load_hnx(copy.deepcopy(hx))
            hh = L.export_hnx(bh)
            back = K.hif_to_c1(hh, S)
            want = c1 if n == "full" else K.canonical_doc(K.select_slice(c1, set(SLICE_RELS)))
            check(f"{n}: C1 -> HIF -> XGI ({type(bx.graph).__name__}) -> HIF -> HyperNetX -> HIF -> C1: compare_containers == [] "
                  f"(header included)", P.compare_containers(want, back, ignore=()) == [])
            check(f"{n}: every intermediate HIF is identical to the export (canonical bytes: weights, extensions, metadata, "
                  f"network-type, order)", K.cjson(hx) == K.cjson(h) == K.cjson(hh))
            check(f"{n}: 0 stale, unlabelled, moved or dropped at both exports",
                  not any(bx.report.values()) and not any(bh.report.values()))
            mem = {}
            for i in h["incidences"]:
                mem.setdefault(i["edge"], set()).add((i["node"], i.get("direction")))
            if isinstance(bx.graph, xgi.DiHypergraph):
                okx = all({(nd, "tail") for nd in bx.graph.edges.dimembers(e)[0]} | {(nd, "head") for nd in bx.graph.edges.dimembers(e)[1]}
                          == mem[e] for e in mem)
                tp = bx.graph.edges.dimembers("f:reg-1")
                check("slice: XGI DiHypergraph tail/head sets equal the HIF memberships; ex:TP53 is in both of f:reg-1",
                      okx and "ex:TP53" in tp[0] and "ex:TP53" in tp[1])
            else:
                okx = all(set(bx.graph.edges.members(e)) == {nd for nd, _ in mem[e]} for e in mem)
                check("full: XGI member sets equal the HIF memberships; no metadata was written into XGI", okx)
            first = {}
            for i in h["incidences"]:
                first.setdefault((i["edge"], i["node"]), []).append(i)
            okh = True
            for (e, nd), recs in first.items():
                cp = bh.graph.get_cell_properties(e, nd)
                okh &= cp.get("role") == recs[0]["attrs"]["role"] and \
                    [x["attrs"]["role"] for x in cp.get(L.EXTRA, [])] == [x["attrs"]["role"] for x in recs[1:]]
            check(f"{n}: HyperNetX cells: role = the first record's role; khg-extra-incidences holds the rest", okh)
            check(f"{n}: bundle.roles('f:reg-1', 'ex:TP53') == ['regulator', 'target'] in both libraries",
                  bx.roles("f:reg-1", "ex:TP53") == bh.roles("f:reg-1", "ex:TP53") == ["regulator", "target"])
        # native edits the export must reflect (an echo export fails these)
        b = L.load_hnx(copy.deepcopy(hif))
        b.graph.rename(nodes={"ex:HeLa": "ex:HeLa-cells"})
        out = L.export_hnx(b)
        check("native edit (HyperNetX rename) is reflected: ex:HeLa-cells in nodes and in f:reg-1's context incidence",
              any(nn["node"] == "ex:HeLa-cells" for nn in out["nodes"]) and
              any(i["edge"] == "f:reg-1" and i["node"] == "ex:HeLa-cells" for i in out["incidences"]) and
              b.report["moved"] == [{"edge": "f:reg-1", "bid": "b1", "from": "ex:HeLa", "to": "ex:HeLa-cells"}])
        b = L.load_xgi(copy.deepcopy(hif))
        b.graph.remove_node_from_edge("f:reg-1", "ex:HeLa")
        try:
            L.export_xgi(b)
            check("native edit (XGI membership removed) makes a strict export raise (a partial fact)", False)
        except L.LoaderError:
            check("native edit (XGI membership removed) makes a strict export raise (a partial fact)", True)
        b.graph.add_node_to_edge("f:reg-1", "ex:HeLa")
        check("... and re-adding the membership restores an identical export", K.cjson(L.export_xgi(b)) == K.cjson(hif))
        for p in sorted((EX / "role-convention").glob("*.json")):
            d = K.strict_loads(p.read_text(encoding="utf-8"))
            ox = L.export_xgi(L.load_xgi(copy.deepcopy(d), validate="convention"))
            oh = L.export_hnx(L.load_hnx(copy.deepcopy(ox), validate="convention"))
            check(f"role-convention/{p.name}: XGI and HyperNetX round trips keep every record in source order",
                  K.cjson(ox["incidences"]) == K.cjson(d["incidences"]) == K.cjson(oh["incidences"]))
        c12 = K.strict_loads((HERE.parent.parent / "probes" / "lib-cases" / "c12-mixed-int-str-ids.hif.json").read_text())
        o12 = [L.export_xgi(L.load_xgi(copy.deepcopy(c12), validate="none")) for _ in range(2)]
        check("R03 c12 (ids 1 and '1'): foreign files keep source order; no sort over mixed types",
              K.cjson(o12[0]["incidences"]) == K.cjson(c12["incidences"]) and o12[0] == o12[1])
    # hash seeds: four seeded children plus one unseeded, against the golden file
    digs = []
    for seed in ("0", "1", "2", "3", None):
        env = dict(os.environ)
        env.pop("PYTHONHASHSEED", None)
        if seed is not None:
            env["PYTHONHASHSEED"] = seed
        r = subprocess.run([sys.executable, str(HERE / "g1_chain.py"), str(EX)], env=env, capture_output=True, text=True)
        digs.append(json.loads(r.stdout))
    golden = load("golden-sha256.json")
    check("G1 digests of every intermediate document are equal for PYTHONHASHSEED 0-3 and unset, and equal the golden file",
          all(d == digs[0] for d in digs) and digs[0] == golden["digests"], json.dumps(digs[0]["full"])[:120])
    check("the chain's HIF digests equal the export's own digest at every step",
          all(len({v["hif"], v["after_xgi"], v["after_hnx"]}) == 1 for v in digs[0].values()))
    r = subprocess.run([sys.executable, str(HERE / "r03_cases.py"), str(EX)], capture_output=True, text=True)
    r03 = {x["case"]: x["outcome"] for x in load("r03-loader-cases.json")["rows"]}
    refused = {k: v for k, v in r03.items() if v != "exact"}
    check("R03 cases through the loaders: 22 of 28 exact; asc, a directed file without direction, duplicate declarations, "
          "NaN and unsafe integers refused", r.returncode == 0 and sum(v == "exact" for v in r03.values()) == 22 and
          refused == {"c04-asc": "refused KHG-P007", "c14-directed-missing-direction": "refused KHG-P010",
                      "c16-attr-value-shapes": "refused KHG-J006 (strict parse)", "c19-duplicate-node-edge-records": "refused KHG-D001",
                      "c22-nan-in-attrs": "refused KHG-J004 (strict parse)", "c23-big-int-ids": "refused KHG-J006 (strict parse)"},
          json.dumps(refused))
    r = subprocess.run([sys.executable, str(HERE / "native_ops.py"), str(EX)], capture_output=True, text=True)
    check("the native-operation table behaves as §5 states (strict exports)", r.returncode == 0 and
          r.stdout.strip().splitlines()[-1].startswith("20 of 20"), r.stdout.strip().splitlines()[-1])
print("ALL PASS" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
