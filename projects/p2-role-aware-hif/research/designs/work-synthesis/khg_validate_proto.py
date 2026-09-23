"""Prototype of the layered validator of DESIGN §8 (research code, not the package).

validate(obj, kind, ...) runs the layers of one input kind in pipeline order and returns findings
[{code, severity, layer, path, message}]. With stop="first" (the G2 harness), it stops after the first step that
reports an error, which is all the pass rule needs: the first rejecting layer is the earliest letter, in the kind's
pipeline order, among the error findings, and the listed code must be among them.

Kinds and pipelines: c1 J V C S D; hif J V H R P D(decode) C S D; role-convention J H R; relation-schema J V M;
queue J V Q C S D; c4 J V I (embedded C1 findings nested under I003)."""
from __future__ import annotations

import copy
import json
import re
import unicodedata
from pathlib import Path

import khg_synth as K
import khg_engines_proto as E

TAG = "tag:khg-contracts,2026:schema/"
PIPE = {"c1": "JVCSD", "hif": "JVHRPDCS", "role-convention": "JHR", "relation-schema": "JVM", "queue": "JVQCSD",
        "c4": "JVI"}
WARN_CODES = {"KHG-L008"}
LIFECYCLE_ROLE = {"disputed": ("khg:disputes", "khg:disputed"), "superseded": ("khg:supersedes", "khg:superseded"),
                  "retracted": ("khg:retracts", "khg:retracted")}
TRANSITIONS = {("asserted", "superseded"), ("disputed", "superseded"), ("asserted", "disputed"), ("disputed", "disputed"),
               ("asserted", "retracted"), ("disputed", "retracted"), ("goal", "retracted"), ("quoted", "retracted"),
               ("disputed", "asserted"), ("quoted", "asserted"), ("goal", "asserted"), ("superseded", "asserted")}


def F(code, path="", message="", severity=None):
    return {"code": code, "severity": severity or ("warning" if code in WARN_CODES else "error"), "layer": code[4],
            "path": path, "message": message}


def _vid(v):
    """cjson of a value's identity, or None when the value is itself malformed (reported elsewhere)."""
    try:
        return K.cjson(K.value_identity(v))
    except (K.KHGError, KeyError, TypeError, ValueError):
        return None


def errors(fs):
    return [f for f in fs if f["severity"] == "error"]


def first_layer(fs, kind):
    ls = {f["layer"] for f in errors(fs)}
    for letter in PIPE[kind]:
        if letter in ls:
            return letter
    return None


def _ver(fmt, name, major, max_minor):
    m = re.fullmatch(rf"{re.escape(name)}/(\d+)\.(\d+)\.(\d+)", fmt or "")
    return bool(m) and int(m.group(1)) == major and int(m.group(2)) <= max_minor


class Validator:
    def __init__(self, schema_dir, *, engine="jsonschema"):
        self.schemas = E.load_schemas(Path(schema_dir))
        self.engine = engine
        self._cache = {}

    # ------------------------------------------------------------------ JSON Schema through one engine
    def _js(self, root, frag, inst):
        key = (root, frag, self.engine)
        if key not in self._cache:
            self._cache[key] = E.validators(self.schemas, root, frag, engines=(self.engine,))[self.engine]
        return [F(x["code"], x["path"], x["message"]) for x in self._cache[key].findings(inst)]

    # ------------------------------------------------------------------ entry point
    def validate(self, obj, kind, *, schema_doc=None, doc_texts=None, bases=None, stop="first"):
        """obj: a parsed document (dict), a list of JSONL lines (queue, c4), or text for layer J."""
        steps = {"c1": self._c1_steps, "hif": self._hif_steps, "role-convention": self._rc_steps,
                 "relation-schema": self._schema_steps, "queue": self._queue_steps, "c4": self._c4_steps}[kind]
        ctx = {"schema_doc": schema_doc, "doc_texts": doc_texts or {}, "bases": bases or {}}
        out = []
        if isinstance(obj, str):
            try:
                if kind in ("queue", "c4"):
                    obj = [K.strict_loads(line) for line in obj.splitlines() if line.strip()]
                else:
                    obj = K.strict_loads(obj)
            except K.KHGError as e:
                return [F(e.code, "", str(e))]
        for step in steps(obj, ctx):
            fs = step()
            out += fs
            if stop == "first" and errors(fs):
                break
        return out

    # ================================================================== C1
    def _c1_steps(self, doc, ctx):
        state = {}
        return [lambda: self._v_c1(doc), lambda: self._js(TAG + "khg-record/1.0.0", "", doc),
                lambda: self._s_container(doc, ctx, state), lambda: self._d_container(doc, ctx, state)]

    def _v_c1(self, doc):
        fmt = (doc.get("header") or {}).get("format") if isinstance(doc, dict) else None
        return [] if _ver(fmt, "khg-record", 1, 0) else [F("KHG-V001", "/header/format", f"format {fmt!r}")]

    def _schema_for(self, doc, ctx):
        sd = ctx.get("schema_doc")
        if sd is None:
            emb = [r for r in doc["records"] if r.get("kind") == "relation-schema"]
            sd = emb[0] if emb else None
        return K.Schema(sd) if sd is not None else None

    # ------------------------------------------------------------------ S: one record against the relation schema
    def _s_container(self, doc, ctx, state):
        S = self._schema_for(doc, ctx)
        if S is None:
            return [F("KHG-D009", "/header/schema", "no relation-type schema supplied and none embedded")]
        state["S"] = S
        hdr = doc["header"]
        recs = doc["records"]
        latest = {}
        for r in recs:
            if r.get("kind") in ("entity", "hyperedge"):
                if r["id"] not in latest or r.get("version", 0) >= latest[r["id"]].get("version", 0):
                    latest[r["id"]] = r
        ents = {i: r for i, r in latest.items() if r["kind"] == "entity"}
        facts = {i: r for i, r in latest.items() if r["kind"] == "hyperedge"}
        state.update(ents=ents, facts=facts, latest=latest)
        out = []
        for i, r in enumerate(recs):
            base = f"/records/{i}"
            out += self._nfc(r, base)
            if r.get("kind") == "hyperedge":
                out += self.s_record(S, r, ents, facts, ctx["doc_texts"], base)
        return out

    def _nfc(self, r, base):
        out = []

        def chk(v, p):
            if isinstance(v, str) and unicodedata.normalize("NFC", v) != v:
                out.append(F("KHG-S020", p, "not NFC"))
        for f in ("id", "relation", "label", "note", "source_text", "redirect_to", "status_ref"):
            chk(r.get(f), f"{base}/{f}")
        for j, b in enumerate(r.get("bindings", [])):
            chk(b.get("role"), f"{base}/bindings/{j}/role")
            v = b.get("value", {})
            for k in ("entity", "fact"):
                chk(v.get(k), f"{base}/bindings/{j}/value/{k}")
            lit = v.get("literal") or {}
            chk(lit.get("value"), f"{base}/bindings/{j}/value/literal/value")
        return out

    def s_record(self, S, r, ents, facts, doc_texts, base="", *, candidate=False):
        out = []
        rel = r["relation"]
        if rel not in S.rel:
            return [F("KHG-S001", f"{base}/relation", rel)]
        if not r["bindings"]:
            return [F("KHG-S007", f"{base}/bindings")]
        status = r["status"]
        seen_bids, counts, by_role = set(), {}, {}
        for j, b in enumerate(r["bindings"]):
            p = f"{base}/bindings/{j}"
            if b["bid"] in seen_bids:
                out.append(F("KHG-S025", f"{p}/bid", b["bid"]))
            seen_bids.add(b["bid"])
            try:
                u = S.usage(rel, b["role"])
            except K.KHGError as e:
                out.append(F(e.code, f"{p}/role", str(e)))
                continue
            counts[b["role"]] = counts.get(b["role"], 0) + 1
            by_role.setdefault(b["role"], []).append(b)
            out += self._s_value(S, r, u, b, ents, facts, p)
            if "direction" in b and u.get("direction") is not None:
                out.append(F("KHG-S016", f"{p}/direction", f"usage declares {u['direction']}"))
        for u in S.usages(rel):
            n = counts.get(u["role"], 0)
            bs = by_role.get(u["role"], [])
            if n < u.get("min", 0):
                if status == "goal":
                    out.append(F("KHG-S018", base, f"goal omits {u['role']}"))
                else:
                    out.append(F("KHG-S003", base, f"{u['role']} bound {n}, min {u['min']}",
                                 "warning" if candidate or status == "candidate" else None))
            if u.get("max") is not None and n > u["max"]:
                out.append(F("KHG-S004", base, f"{u['role']} bound {n}, max {u['max']}"))
            kinds = [K.vkind(b["value"]) for b in bs]
            if any(K._is_novalue(b["value"]) for b in bs) and n > 1:
                out.append(F("KHG-S013", base, u["role"]))
            if u.get("ordered"):
                pos = sorted(b.get("position", 0) for b in bs)
                if any("position" not in b for b in bs) or pos != list(range(1, n + 1)):
                    out.append(F("KHG-S015", base, f"{u['role']} positions {pos}"))
            else:
                if any("position" in b for b in bs):
                    out.append(F("KHG-S015", base, f"{u['role']} is unordered"))
                ids = [_vid(b["value"]) for b in bs if K.vkind(b["value"]) in ("entity", "literal", "fact")]
                ids = [x for x in ids if x is not None]
                if len(ids) != len(set(ids)) or kinds.count("special") > 1 and \
                        sum(1 for b in bs if b["value"].get("special") == "somevalue") > 1:
                    out.append(F("KHG-S014", base, u["role"]))
        vars_ = [b["value"]["unbound"]["var"] for b in r["bindings"] if K.vkind(b["value"]) == "unbound"]
        if len(vars_) != len(set(vars_)):
            out.append(F("KHG-S019", base))
        if S.kind(rel) != "lifecycle":
            try:
                bb = K.bounds(S, r)
                if bb["s_lo"] >= bb["e_hi"]:
                    out.append(F("KHG-S009", base))
            except K.KHGError:
                pass
        if status == "asserted" and S.kind(rel) != "lifecycle":
            if not [e for e in r.get("evidence", []) if not (e.get("epistemics") or {}).get("negated")]:
                out.append(F("KHG-S011", base))
        scales = {s["id"]: s for s in S.doc.get("confidence_scales", [])}
        confs = [(f"{base}/confidence", r.get("confidence"))] + \
                [(f"{base}/evidence/{k}/confidence", e.get("confidence")) for k, e in enumerate(r.get("evidence", []))]
        for p, c in confs:
            if not c:
                continue
            lo, hi = (0, 1) if c["scale"] == "probability" else \
                (scales[c["scale"]]["min"], scales[c["scale"]]["max"]) if c["scale"] in scales else (None, None)
            if lo is None:
                out.append(F("KHG-S010", p, f"scale {c['scale']} undeclared"))
            elif not lo <= c["value"] <= hi:
                out.append(F("KHG-S010", p, f"{c['value']} outside [{lo}, {hi}]"))
        bids = {b["bid"] for b in r["bindings"]}
        for k, e in enumerate(r.get("evidence", [])):
            if set(e.get("supports", [])) - bids:
                out.append(F("KHG-S022", f"{base}/evidence/{k}/supports"))
            out += self._spans(e, doc_texts, f"{base}/evidence/{k}")
        for c in S.rel[rel].get("constraints", []) or []:
            out += self._constraint(c, by_role, base)
        if S.kind(rel) == "lifecycle" and r.get("reason") not in S.rel[rel]["reasons"]:
            out.append(F("KHG-S026", f"{base}/reason", str(r.get("reason"))))
        return out

    def _s_value(self, S, r, u, b, ents, facts, p):
        v = b["value"]
        k = K.vkind(v)
        fill = u["fillers"]
        if k == "entity":
            opts = [f["entity"] for f in fill if "entity" in f]
            if not opts:
                return [F("KHG-S005", p, "no entity filler")]
            want = [t for o in opts for t in o]
            ent = ents.get(v["entity"])
            if ent is not None and want and not any(S.is_subtype(t, w) for t in ent.get("types", []) for w in want):
                return [F("KHG-S005", p, f"{v['entity']} is not a {want}")]
            return []
        if k == "literal":
            lit = v["literal"]
            opts = [f for f in fill if f.get("literal") == lit.get("datatype")]
            if not opts:
                return [F("KHG-S005", p, f"datatype {lit.get('datatype')} not allowed")]
            out = []
            if lit["datatype"] == "time":
                try:
                    K.parse_time(lit["time"], lit["precision"], lit.get("calendar"))
                except K.KHGError as e:
                    return [F(e.code, f"{p}/value/literal", str(e))]
                pm = opts[0].get("precision_min")
                if pm is not None and lit["precision"] < pm:
                    out.append(F("KHG-S023", p, f"precision {lit['precision']} < {pm}"))
            if lit["datatype"] == "quantity" and opts[0].get("units") and lit["unit"] not in opts[0]["units"]:
                out.append(F("KHG-S023", p, f"unit {lit['unit']} not allowed"))
            return out
        if k == "fact":
            opts = [f["fact"] for f in fill if "fact" in f]
            if not opts:
                return [F("KHG-S005", p, "no fact filler")]
            want = [x for o in opts for x in o]
            tgt = facts.get(v["fact"])
            if tgt is not None and want and tgt["relation"] not in want:
                return [F("KHG-S005", p, f"{v['fact']} is a {tgt['relation']}, not {want}")]
            return []
        if k == "special":
            if not u.get(v["special"], True):
                return [F("KHG-S005", p, f"{v['special']} not allowed")]
        return []

    def _spans(self, e, doc_texts, p):
        sels = e.get("selectors") or []
        doc = (e.get("source") or {}).get("doc_id")
        text = doc_texts.get(doc)
        if not sels or text is None:
            return []
        t = unicodedata.normalize("NFC", text)
        quote = next((s for s in sels if s["type"] == "quote"), None)
        posn = next((s for s in sels if s["type"] == "position"), None)
        out = []
        if posn:
            if not 0 <= posn["start"] < posn["end"] <= len(t):
                out.append(F("KHG-S021", p, "span empty, reversed or outside the text"))
            elif quote and t[posn["start"]:posn["end"]] != quote["exact"]:
                out.append(F("KHG-S021", p, "quote differs from text[start:end]"))
        return out

    def _constraint(self, c, by_role, base):
        vals = {r: [x for x in (_vid(b["value"]) for b in bs) if x is not None] for r, bs in by_role.items()}
        t, roles = c["type"], c["roles"]
        bad = False
        if t == "must_differ":
            bad = len({x for r in roles for x in vals.get(r, [])}) < sum(len(vals.get(r, [])) for r in roles)
        elif t == "must_agree":
            bad = len({x for r in roles for x in vals.get(r, [])}) > 1
        elif t == "requires":
            bad = bool(vals.get(roles[0])) and not all(vals.get(r) for r in roles[1:])
        elif t == "excludes":
            bad = sum(1 for r in roles if vals.get(r)) > 1
        elif t == "at_least_one_of":
            bad = not any(vals.get(r) for r in roles)
        return [F("KHG-S024", base, f"{t} {roles}", "warning" if c.get("severity") == "warning" else None)] if bad else []

    # ------------------------------------------------------------------ D: cross-record, container, history
    def _d_container(self, doc, ctx, state):
        S = state.get("S")
        if S is None:
            return []
        out = []
        hdr, recs = doc["header"], doc["records"]
        if hdr["schema"]["sha256"] != S.sha256() or hdr["schema"]["id"] != S.doc["id"] or \
                hdr["schema"]["version"] != S.doc["version"]:
            out.append(F("KHG-D009", "/header/schema", "schema id, version or sha256 differs"))
        hist = hdr.get("content") == "history"
        seen, kinds = set(), {}
        for i, r in enumerate(recs):
            if r.get("kind") not in ("entity", "hyperedge"):
                continue
            key = (r["id"], r.get("version")) if hist else r["id"]
            if key in seen:
                out.append(F("KHG-D001", f"/records/{i}", f"{r['id']} declared twice"))
            seen.add(key)
            kinds.setdefault(r["id"], set()).add(r["kind"])
            if r.get("kind") == "hyperedge" and r.get("status") == "candidate":
                out.append(F("KHG-D017", f"/records/{i}/status"))
        for i, ks in kinds.items():
            if len(ks) > 1:
                out.append(F("KHG-D007", "", i))
        if hist:
            out += self._d_history(S, hdr, recs)
        latest, ents, facts = state["latest"], state["ents"], state["facts"]
        for i, r in enumerate(recs):
            if r.get("kind") != "hyperedge" or latest.get(r["id"]) is not r:
                continue
            for j, b in enumerate(r["bindings"]):
                v = b["value"]
                k = K.vkind(v)
                p = f"/records/{i}/bindings/{j}/value"
                if k == "entity":
                    e = ents.get(v["entity"])
                    if e is None and hdr.get("complete"):
                        out.append(F("KHG-D002", p, f"entity {v['entity']} absent from a complete document"))
                    elif e is not None and e.get("redirect_to"):
                        out.append(F("KHG-D020", p, f"{v['entity']} redirects to {e['redirect_to']}"))
                if k == "fact" and v["fact"] not in facts and hdr.get("complete"):
                    out.append(F("KHG-D002", p, f"fact {v['fact']} does not resolve"))
            if "derived" in r:
                want = K.derived(S, K.canonical_record(r))
                if K.cjson(r["derived"]) != K.cjson(want):
                    out.append(F("KHG-D015", f"/records/{i}/derived"))
        out += self._d_graph(S, facts)
        snap = list(facts.values())
        for g in K.key_invariant_violations(S, snap):
            out.append(F("KHG-D016", "", f"key invariant: {g}"))
        for pr in K.possible_only_overlaps(S, snap):
            out.append(F("KHG-L008", "", f"possible overlap {pr}"))
        return out

    def _d_graph(self, S, facts):
        out = []
        graph = {i: [b["value"]["fact"] for b in r["bindings"] if K.vkind(b["value"]) == "fact"]
                 for i, r in facts.items() if S.kind(r["relation"]) != "lifecycle"}
        if _cycle(graph):
            out.append(F("KHG-D008", "", "nesting cycle"))
        for i, r in facts.items():
            st = r["status"]
            if st in LIFECYCLE_ROLE:
                rel, role = LIFECYCLE_ROLE[st]
                lc = facts.get(r.get("status_ref"))
                if lc is None or lc["relation"] != rel or lc["status"] != "asserted" or \
                        not any(b["role"] == role and b["value"].get("fact") == i for b in lc["bindings"]):
                    out.append(F("KHG-D010", i, f"status_ref {r.get('status_ref')!r} does not name its {rel} record"))
        sup = {}
        for i, r in facts.items():
            if r["relation"] in ("khg:supersedes", "khg:retracts") and r["status"] == "asserted":
                role = "khg:superseded" if r["relation"] == "khg:supersedes" else "khg:retracted"
                want = "superseded" if r["relation"] == "khg:supersedes" else "retracted"
                for b in r["bindings"]:
                    if b["role"] == role:
                        f = facts.get(b["value"]["fact"])
                        if f is not None and f["status"] != want:
                            out.append(F("KHG-D010", i, f"{b['value']['fact']} is bound as {role} but is {f['status']}"))
            if r["relation"] == "khg:supersedes" and r["status"] == "asserted":
                sing = [facts.get(b["value"]["fact"]) for b in r["bindings"] if b["role"] == "khg:superseding"]
                sed = [facts.get(b["value"]["fact"]) for b in r["bindings"] if b["role"] == "khg:superseded"]
                for a in (x for x in sing if x):
                    sup.setdefault(a["id"], []).extend(x["id"] for x in sed if x)
                    for b in (x for x in sed if x):
                        reason = r.get("reason")
                        if reason == "correction" and (a["relation"] != b["relation"] or
                                                       K.key_digest(S, a) != K.key_digest(S, b)):
                            out.append(F("KHG-D011", i, "correction across relations or key digests"))
                        elif reason == "duplicate" and K.content_key(S, a) != K.content_key(S, b):
                            out.append(F("KHG-D011", i, "duplicate with different content keys"))
                        elif reason == "refinement" and not K.fact_refines(S, a, b):
                            out.append(F("KHG-D011", i, "refinement that does not refine"))
        if _cycle(sup):
            out.append(F("KHG-D012", "", "supersession cycle"))
        return out

    def _d_history(self, S, hdr, recs):
        import khg_store_proto as P
        out = []
        by = {}
        for r in recs:
            if r.get("kind") in ("entity", "hyperedge"):
                by.setdefault(r["id"], []).append(r)
        as_at = P._tx(hdr["as_at"]) if hdr.get("as_at") else None
        store = P.ProtoStore(S)
        for i, vs in sorted(by.items()):
            vs = sorted(vs, key=lambda x: x.get("version", 0))
            if [v.get("version") for v in vs] != list(range(1, len(vs) + 1)):
                out.append(F("KHG-D001", i, "versions are not 1..n"))
            prev = None
            for v in vs:
                t = P._tx(v["recorded_at"])
                if prev is not None and t <= P._tx(prev["recorded_at"]):
                    out.append(F("KHG-D018", i, f"version {v['version']} is not after version {prev['version']}"))
                if as_at is not None and t > as_at:
                    out.append(F("KHG-D018", i, f"version {v['version']} is after the header's as_at"))
                if prev is not None:
                    try:
                        if v["kind"] == "hyperedge" and prev["status"] != v["status"]:
                            if (prev["status"], v["status"]) not in TRANSITIONS:
                                out.append(F("KHG-D014", i, f"{prev['status']} -> {v['status']}"))
                            a, b = dict(prev, status="asserted"), dict(v, status="asserted")
                            for x in (a, b):
                                x.pop("status_ref", None)
                                if prev["status"] == "goal":
                                    x.pop("goal", None)
                            store._version_rule(a, b, allow_novalue_end=True)
                        else:
                            store._version_rule(prev, v, allow_novalue_end=True)
                    except K.KHGError as e:
                        out.append(F(e.code, i, str(e)))
                prev = v
        return out

    # ================================================================== HIF
    def _hif_steps(self, doc, ctx):
        dec = {}
        return [lambda: self._v_hif(doc), lambda: self._h(doc), lambda: self._r(doc),
                lambda: self._p(doc), lambda: self._decode(doc, ctx, dec),
                lambda: self._js(TAG + "khg-record/1.0.0", "", dec["c1"]) if "c1" in dec else [],
                lambda: self._s_container(dec["c1"], dict(ctx, schema_doc=dec["schema"]), dec) if "c1" in dec else [],
                lambda: self._d_container(dec["c1"], ctx, dec) if "c1" in dec else []]

    def _v_hif(self, doc):
        md = doc.get("metadata") if isinstance(doc, dict) and isinstance(doc.get("metadata"), dict) else {}
        out = []
        if "khg-profile" in md and not _ver(md["khg-profile"], "khg-hif", 1, 0):
            out.append(F("KHG-V001", "/metadata/khg-profile", str(md["khg-profile"])))
        if "khg-record" in md and not _ver(md["khg-record"], "khg-record", 1, 0):
            out.append(F("KHG-V001", "/metadata/khg-record", str(md["khg-record"])))
        return out

    def _h(self, doc):
        return self._js(E.HIF_ID, "", doc)

    def _r(self, doc):
        """role-convention 1.0.0: R003 declaration; R001 roles on role-carrying edges; R002 exact duplicates; R004."""
        out = []
        md = doc.get("metadata") or {}
        if md.get("role-convention") != "1.0.0":
            out.append(F("KHG-R003", "/metadata/role-convention", str(md.get("role-convention"))))
        carrying = {i["edge"] for i in doc["incidences"] if "role" in (i.get("attrs") or {})}
        seen = set()
        for j, i in enumerate(doc["incidences"]):
            a = i.get("attrs") or {}
            if i["edge"] in carrying and not (isinstance(a.get("role"), str) and a["role"]):
                out.append(F("KHG-R001", f"/incidences/{j}/attrs/role", "role missing or not a non-empty string"))
            if "role-position" in a and not (isinstance(a["role-position"], int) and not isinstance(a["role-position"], bool)
                                             and a["role-position"] >= 1):
                out.append(F("KHG-R004", f"/incidences/{j}/attrs/role-position"))
            if isinstance(a.get("role"), str):
                key = (json.dumps(i["edge"]), json.dumps(i["node"]), a["role"], json.dumps(a.get("role-position")))
                if key in seen:
                    out.append(F("KHG-R002", f"/incidences/{j}", "exact duplicate (edge, node, role, role-position)"))
                seen.add(key)
        return out

    def _p(self, doc):
        out = [f for f in self._js(TAG + "khg-hif/1.0.0", "", doc) if f["layer"] != "H"]
        md = doc.get("metadata") or {}
        kinds_prefix = {"literal": ("_:lit:", "_:litb:"), "somevalue": ("_:sv:",), "novalue": ("_:nv:",),
                        "unbound": ("_:var:",), "fact-ref": ("_:ref:",)}
        present = {e["edge"] for e in doc.get("edges", [])}
        for j, n in enumerate(doc.get("nodes", [])):
            a = n.get("attrs") or {}
            nid, k = n.get("node"), a.get("khg-kind")
            if not isinstance(nid, str):
                continue
            if k == "entity" and nid.startswith("_:"):
                out.append(F("KHG-P004", f"/nodes/{j}/node", "entity id uses the reserved _: prefix"))
            elif k in kinds_prefix and not nid.startswith(kinds_prefix[k]):
                out.append(F("KHG-P004", f"/nodes/{j}/node", f"{k} node without its prefix"))
            if k == "fact-ref" and a.get("khg-external") and ("khg-slice" not in md or a.get("khg-ref") in present):
                out.append(F("KHG-P017", f"/nodes/{j}", "khg-external outside a slice or naming a present fact"))
        nt = doc.get("network-type")
        incs = doc.get("incidences", [])
        if nt == "directed" and any("direction" not in i for i in incs):
            out.append(F("KHG-P010", "/incidences", "directed document, incidence without direction"))
        if nt != "directed" and incs and all("direction" in i for i in incs):
            out.append(F("KHG-P011", "/network-type", "every incidence has a direction but the file is not directed"))
        seen = set()
        for j, i in enumerate(incs):
            bid = (i.get("attrs") or {}).get("khg-bid")
            if bid is None:
                continue
            if (json.dumps(i["edge"]), bid) in seen:
                out.append(F("KHG-P016", f"/incidences/{j}/attrs/khg-bid", f"{i['edge']} {bid}"))
            seen.add((json.dumps(i["edge"]), bid))
        return out

    def _decode(self, doc, ctx, dec):
        sd = ctx.get("schema_doc")
        try:
            S = K.Schema(sd) if sd is not None else None
            c1 = K.hif_to_c1(doc, S)
        except K.KHGError as e:
            return [F(e.code, "", str(e))]
        dec["c1"] = c1
        dec["schema"] = sd if sd is not None else doc["metadata"]["khg-schema-document"]
        return []

    # ================================================================== role-convention alone
    def _rc_steps(self, doc, ctx):
        return [lambda: self._h(doc), lambda: self._r(doc)]

    # ================================================================== relation-type schema documents (M)
    def _schema_steps(self, doc, ctx):
        return [lambda: [] if _ver(doc.get("format"), "khg-relation-schema", 1, 0) else
                [F("KHG-V001", "/format", str(doc.get("format")))], lambda: self.m_checks(doc)]

    def m_checks(self, doc):
        out = []
        if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", str(doc.get("version", ""))):
            out.append(F("KHG-M004", "/version"))
        types = [t["id"] for t in doc.get("entity_types", [])]
        roles = [r["id"] for r in doc.get("roles", [])]
        rels = [r["id"] for r in doc.get("relations", [])]
        for name, ids in (("entity_types", types), ("roles", roles), ("relations", rels)):
            if len(ids) != len(set(ids)):
                out.append(F("KHG-M013", f"/{name}", "duplicate id"))
            if any(str(i).startswith("khg:") for i in ids):
                out.append(F("KHG-M008", f"/{name}", "reserved khg: namespace"))
        tset = set(types)
        parents = {t["id"]: t.get("parents", []) for t in doc.get("entity_types", [])}
        if any(p not in tset for ps in parents.values() for p in ps) or _cycle(parents):
            out.append(F("KHG-M016", "/entity_types"))
        dt = {"time", "quantity", "string", "lang_string", "boolean", "iri", "geo"}
        dm = doc.get("default_time", {"model": "timeless"})
        for i, r in enumerate(doc.get("relations", [])):
            p = f"/relations/{i}"
            us = r.get("roles", [])
            if r.get("kind", "fact") != "fact":
                out.append(F("KHG-M015", f"{p}/kind", f"relation kind {r.get('kind')!r} (rule relations come in 1.1)"))
            if not us:
                out.append(F("KHG-M001", p))
                continue
            names = [u["role"] for u in us]
            if len(names) != len(set(names)):
                out.append(F("KHG-M002", p))
            byr = {u["role"]: u for u in us}
            for j, u in enumerate(us):
                q = f"{p}/roles/{j}"
                if u["role"] not in roles:
                    out.append(F("KHG-M009", q, u["role"]))
                if u.get("slot") not in ("core", "qualifier", "time", "meta"):
                    out.append(F("KHG-M015", q, "slot"))
                for f in u.get("fillers", []):
                    if "entity" in f and any(t not in tset for t in f["entity"]):
                        out.append(F("KHG-M005", q, "unknown entity type"))
                    if "fact" in f and any(x not in rels for x in f["fact"]):
                        out.append(F("KHG-M005", q, "unknown relation"))
                    if "literal" in f and f["literal"] not in dt:
                        out.append(F("KHG-M006", q, str(f["literal"])))
                if u.get("max") is not None and u["max"] < u.get("min", 0):
                    out.append(F("KHG-M010", q))
                if u.get("complete") and u.get("min", 0) == 0:
                    out.append(F("KHG-M014", q))
            tm = r.get("time", dm)
            if tm.get("model") not in ("interval", "invariant", "timeless"):
                out.append(F("KHG-M007", f"{p}/time", str(tm.get("model"))))
            named = set()
            if tm.get("model") == "interval":
                for end in ("start", "end"):
                    u = byr.get(tm.get(end))
                    named.add(tm.get(end))
                    if u is None or u.get("slot") != "time" or u.get("max") != 1 or u.get("fillers") != [{"literal": "time"}]:
                        out.append(F("KHG-M007", f"{p}/time/{end}", str(tm.get(end))))
            for u in us:
                if u.get("slot") == "time" and u["role"] not in named:
                    out.append(F("KHG-M007", p, f"time usage {u['role']} not named by the time model"))
            k = r.get("key")
            if k:
                for role in k.get("roles", []):
                    if role not in byr or byr[role].get("slot") not in ("core", "qualifier"):
                        out.append(F("KHG-M003", f"{p}/key", role))
                if k.get("temporal") and tm.get("model") != "interval":
                    out.append(F("KHG-M011", f"{p}/key"))
                if k.get("temporal") and k.get("on_collision") == "supersede":
                    out.append(F("KHG-M017", f"{p}/key"))
                if k.get("on_collision", "dispute") not in ("close_older", "supersede", "dispute", "reject"):
                    out.append(F("KHG-M015", f"{p}/key", "on_collision"))
            pr = r.get("primary")
            if pr:
                for x in (pr.get("subject"), pr.get("object")):
                    u = byr.get(x)
                    if u is None or u.get("slot") != "core" or u.get("max") != 1:
                        out.append(F("KHG-M012", f"{p}/primary", str(x)))
            for c in r.get("constraints", []) or []:
                if c.get("severity") not in ("error", "warning"):
                    out.append(F("KHG-M015", f"{p}/constraints", f"severity {c.get('severity')!r}"))
                if c.get("type") not in ("requires", "excludes", "at_least_one_of", "must_differ", "must_agree"):
                    out.append(F("KHG-M015", f"{p}/constraints", f"type {c.get('type')!r}"))
        return out

    # ================================================================== C3 queue files
    def _queue_steps(self, lines, ctx):
        st = {}
        return [lambda: self._v_queue(lines), lambda: self._q(lines, ctx, st),
                lambda: self._q_payload_c(lines), lambda: self._q_payload_s(lines, ctx, st), lambda: self._q_d(lines, ctx, st)]

    def _v_queue(self, lines):
        h = lines[0] if lines else {}
        if h.get("kind") == "queue-header" and not _ver(h.get("format"), "khg-queue", 1, 0):
            return [F("KHG-V001", "/lines/0/format", str(h.get("format")))]
        return []

    def _q(self, lines, ctx, st):
        import khg_store_proto as P
        out = []
        if not lines or lines[0].get("kind") != "queue-header":
            return [F("KHG-Q008", "/lines/0", "queue file without its header line")]
        hdr = lines[0]
        S = K.Schema(ctx["schema_doc"])
        st["S"] = S
        if any(x.get("kind") == "queue-header" for x in lines[1:]):
            out.append(F("KHG-Q008", "", "header repeated"))
        items, state, last = {}, {}, {}
        base_doc = ctx["bases"].get((hdr.get("base") or {}).get("document_id"))
        if hdr.get("base"):
            if base_doc is None or K.container_sha256(base_doc) != hdr["base"]["sha256"]:
                out.append(F("KHG-Q012", "/lines/0/base", "base not supplied or sha256 differs"))
                base_doc = None
        st["base"] = base_doc
        base_ents = {r["id"]: r for r in (base_doc or {}).get("records", []) if r.get("kind") == "entity"}
        st["base_ents"] = base_ents
        qid = hdr.get("queue_id")
        for n, x in enumerate(lines[1:], 1):
            p = f"/lines/{n}"
            if x.get("kind") == "queue-item":
                if x.get("item_kind") != "hyperedge":
                    out.append(F("KHG-Q003", f"{p}/item_kind", str(x.get("item_kind"))))
                    continue
                run = x.get("run") or {}
                if not all(k in run for k in ("run_id", "order_id", "position")) or "submitted_by" not in x or \
                        "doc" not in x or not (x.get("payload") or {}).get("evidence"):
                    out.append(F("KHG-Q001", p, "extraction fields or evidence missing"))
                pl = x.get("payload") or {}
                if pl.get("status") != "candidate" or not re.fullmatch(rf"cand:{re.escape(str(qid))}\.\d+", str(pl.get("id"))):
                    out.append(F("KHG-Q002", f"{p}/payload", "status or id"))
                doc = x.get("doc") or {}
                for k, e in enumerate(pl.get("evidence", [])):
                    if e.get("type") == "extracted" and (e["source"].get("doc_id") != doc.get("doc_id") or
                                                          e["source"].get("doc_sha256") != doc.get("doc_sha256")):
                        out.append(F("KHG-Q009", f"{p}/payload/evidence/{k}"))
                try:
                    probe = dict(pl, status="asserted")
                    want = {"content_key": K.content_key(S, probe), "core_key": K.core_key(S, probe),
                            "key_digest": K.key_digest(S, probe)}
                    if any((x.get("keys") or {}).get(k) != v for k, v in want.items()):
                        out.append(F("KHG-Q010", f"{p}/keys", "keys differ from recomputation"))
                    for k, e in enumerate(pl.get("evidence", [])):
                        if e.get("type") in K.EVENT_TYPES and e.get("event_hash") != K.event_hash(want["content_key"], e):
                            out.append(F("KHG-Q010", f"{p}/payload/evidence/{k}/event_hash", "event_hash differs"))
                except (K.KHGError, KeyError):
                    pass
                ents = {e["id"]: e for e in x.get("entities", [])}
                for b in pl.get("bindings", []):
                    v = b.get("value", {})
                    if "entity" in v and v["entity"] not in ents and v["entity"] not in base_ents:
                        out.append(F("KHG-Q011", f"{p}/payload", f"{v['entity']} unresolved"))
                items[x.get("qid")] = x
                state[x.get("qid")] = "pending"
            elif x.get("kind") == "log-entry":
                act = x.get("action")
                if act not in ("lint", "accept", "reject", "flag", "verdict", "withdraw"):
                    out.append(F("KHG-Q003", f"{p}/action", str(act)))
                    continue
                tgt = x.get("target")
                if tgt not in items or x.get("parent") != last.get(tgt):
                    out.append(F("KHG-Q007", f"{p}/target", str(tgt)))
                    continue
                if act == "lint" and not all(k in x for k in ("rule_set", "findings", "outcome")):
                    out.append(F("KHG-Q004", p))
                cur = state[tgt]
                moves = {"lint": {"pending": {"linted", "needs_review", "rejected"}},
                         "accept": {"linted": {"accepted"}, "needs_review": {"accepted"}},
                         "reject": {s: {"rejected"} for s in ("pending", "linted", "needs_review")},
                         "flag": {s: {"needs_review"} for s in ("pending", "linted")},
                         "verdict": {s: {s} for s in ("pending", "linted", "needs_review", "accepted", "rejected")},
                         "withdraw": {s: {"withdrawn"} for s in ("pending", "linted", "needs_review")}}
                if x.get("state_before") != cur or x.get("state_after") not in moves[act].get(cur, set()):
                    out.append(F("KHG-Q005", p, f"{act}: {x.get('state_before')} -> {x.get('state_after')} from {cur}"))
                else:
                    state[tgt] = x["state_after"]
                last[tgt] = x.get("lid")
            else:
                out.append(F("KHG-Q003", f"{p}/kind", str(x.get("kind"))))
        st["items"] = items
        if not errors(out):
            out += self._replay(lines, S, base_doc)
        return out

    def _replay(self, lines, S, base_doc):
        import khg_store_proto as P
        store = P.ProtoStore(S)
        if base_doc is not None:
            store.load(base_doc, at="2000-01-01T00:00:00Z")
        items = {x["qid"]: x for x in lines if x.get("kind") == "queue-item"}
        out = []
        for n, x in enumerate(lines):
            if x.get("kind") != "log-entry" or x.get("action") != "accept":
                continue
            it = items[x["target"]]
            (aft,) = x["after"]
            rec = copy.deepcopy(it["payload"])
            rec["id"], rec["status"] = aft["id"], "asserted"
            try:
                rc = store.put(list(it.get("entities", [])) + [rec], actor=x["actor"]["id"], at=x["at"])
            except K.KHGError as e:
                out.append(F("KHG-Q006", f"/lines/{n}", f"replay failed: {e}"))
                continue
            got = [r for r in rc["records"] if r[0] == aft["id"]]
            written = [{"id": aft["id"], "version": got[0][1], "record": K.decision_view(store.get(aft["id"]))}]
            if [got[0][0], got[0][1]] != [aft["id"], aft["version"]] or \
                    K.digest("khg-decision/1", written) != x.get("decision_hash"):
                out.append(F("KHG-Q006", f"/lines/{n}/decision_hash", "replay recomputes a different decision"))
        return out

    def _q_payload_c(self, lines):
        out = []
        for n, x in enumerate(lines):
            if x.get("kind") == "queue-item":
                out += [dict(f, path=f"/lines/{n}/payload{f['path']}")
                        for f in self._js(TAG + "khg-record/1.0.0", "/definitions/hyperedge", x.get("payload"))]
        return out

    def _q_payload_s(self, lines, ctx, st):
        S = st["S"]
        out = []
        for n, x in enumerate(lines):
            if x.get("kind") != "queue-item":
                continue
            ents = dict(st["base_ents"])
            ents.update({e["id"]: e for e in x.get("entities", [])})
            out += self.s_record(S, x["payload"], ents, {}, ctx["doc_texts"], f"/lines/{n}/payload", candidate=True)
        return out

    def _q_d(self, lines, ctx, st):
        hdr = lines[0]
        S = st["S"]
        if hdr["schema"]["sha256"] != S.sha256():
            return [F("KHG-D009", "/lines/0/schema")]
        return []

    # ================================================================== C4 items
    def _c4_steps(self, lines, ctx):
        return [lambda: self._v_c4(lines), lambda: self._i(lines, ctx)]

    def _v_c4(self, lines):
        h = lines[0] if lines else {}
        if h.get("kind") == "c4-header" and not _ver(h.get("format"), "khg-c4-items", 0, 1):
            return [F("KHG-V001", "/lines/0/format", str(h.get("format")))]
        return []

    def _i(self, lines, ctx):
        import khg_c5_proto as C5
        out = []
        S = K.Schema(ctx["schema_doc"])
        traces = {}
        for n, x in enumerate(lines):
            fs = self._js(TAG + "khg-c4-items/0.1.0", "", x)
            out += [dict(f, path=f"/lines/{n}{f['path']}") for f in fs]
            if fs:
                continue
            if x["kind"] == "c4-memory-trace":
                traces[x["trace_id"]] = x
            embedded = []
            if x["kind"] == "c4-extraction-doc":
                embedded = x["gold"]
            if x["kind"] == "c4-memory-trace":
                embedded = [r for ev in x["events"] for r in ev.get("put", [])]
            ents = {e["id"]: e for e in x.get("entities", [])}
            facts = {r["id"]: r for r in embedded}
            for r in embedded:
                for f in errors(self.s_record(S, r, ents, facts, ctx["doc_texts"], f"/lines/{n}")):
                    out.append(F("KHG-I003", f["path"], f"{f['code']}: {f['message']}"))
        for n, x in enumerate(lines):
            if x.get("kind") != "c4-memory-question" or errors(out):
                continue
            tr = traces.get(x["trace_id"])
            if tr is None:
                out.append(F("KHG-I003", f"/lines/{n}/trace_id", "trace missing"))
                continue
            try:
                g = C5.derive_memory_gold(tr, x, schema=S)
            except K.KHGError as e:
                out.append(F("KHG-I003", f"/lines/{n}", f"trace replay fails: {e.code} {e}"))
                continue
            for k in ("answer", "stale_values", "future_values", "disputed_values", "answerable"):
                if K.cjson(g[k]) != K.cjson(x[k]):
                    out.append(F("KHG-I005", f"/lines/{n}/{k}", "differs from derive_memory_gold"))
        return out


def _cycle(graph):
    seen, stack = set(), set()

    def dfs(n):
        if n in stack:
            return True
        if n in seen:
            return False
        seen.add(n)
        stack.add(n)
        for m in graph.get(n, []):
            if dfs(m):
                return True
        stack.discard(n)
        return False
    return any(dfs(n) for n in sorted(graph))
