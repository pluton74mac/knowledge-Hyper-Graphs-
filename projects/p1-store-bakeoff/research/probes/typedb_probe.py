"""Backend 4, TypeDB 3.x: the natural mapping of P2's relation-type schema to TypeQL, the fixture loaded into it,
the core reads as TypeQL, a structural fidelity check, and the read-only scenarios under the flags TypeDB can
declare. Needs a TypeDB CE server on 127.0.0.1:1729 (admin/password, TLS off) and typedb-driver 3.13.6.

The mapping (names: every character outside [A-Za-z0-9_-] becomes "-", so khg:supersedes is khg-supersedes):

- ``entity khg-entity @abstract, owns khg-id @key, owns khg-record``; each schema entity type ``sub`` its parent,
  else ``sub khg-entity``. An instance has one type, so a C1 entity with several ``types`` has no native form.
- ``relation khg-fact @abstract`` owns the header attributes (khg-id @key, khg-status, khg-rank, khg-visibility,
  khg-rel-kind, khg-status-ref, khg-key-digest, khg-s-lo/s-hi/e-lo/e-hi, khg-n-bindings, khg-payload,
  khg-bindings); each schema relation and each lifecycle relation ``sub khg-fact``.
- A usage whose fillers include entities or facts is a scoped role ``relates <role> @card(0..)``; the filler
  entity types (and, for fact fillers, the fact relations) ``plays <relation>:<role>``. Every fact plays the
  lifecycle roles.
- A usage whose fillers include literals is an owned attribute ``lit-<role>`` (value string: the literal's value
  identity, ``record.identity_key``), because "attributes cannot have capabilities" (they cannot play roles).
- Special and unbound values have no player: owned attributes ``special-<role>`` and ``unbound-<role>``.
- Bids, positions, directions and binding extensions have no native home (role-player edges carry no
  attributes, and role-player lists are "not yet implemented" in 3.13.6), so the relation also owns
  ``khg-bindings``: the bindings as canonical JSON. ``rebuild_native`` rebuilds records without it to measure what
  the native structure alone loses.

Writes out/typedb.json.
"""
from __future__ import annotations

import copy
import json
import re
import time
from typing import Any

from common import (POS, ReadOnlyProbe, assemble, clamp, fixture, hand_check, run_read_only, split, write_out)
from khg_contracts.record import binding_sort_key, injective_match
from khg_contracts.schema import LIFECYCLE_RELATIONS
from khg_contracts.store import MemoryStore, ScenarioClock, compare_containers

ADDR = "127.0.0.1:1729"
DECLARED = frozenset({"literal_values", "nesting", "valid_time", "key_constraint", "atomic_writes"})
HEADER_ATTRS = [("khg-id", "string"), ("khg-status", "string"), ("khg-rank", "string"),
                ("khg-visibility", "string"), ("khg-rel-kind", "string"), ("khg-status-ref", "string"),
                ("khg-key-digest", "string"), ("khg-s-lo", "integer"), ("khg-s-hi", "integer"),
                ("khg-e-lo", "integer"), ("khg-e-hi", "integer"), ("khg-n-bindings", "integer"),
                ("khg-payload", "string"), ("khg-bindings", "string"), ("khg-version", "integer"),
                ("khg-recorded-at", "string"), ("khg-recorded-by", "string"), ("khg-record", "string")]
LIFECYCLE_ROLES = {"khg:supersedes": ["khg:superseding", "khg:superseded"], "khg:retracts": ["khg:retracted"],
                   "khg:disputes": ["khg:disputed"]}
_db_counter = [0]


def name(x: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", x)


def q(s: str) -> str:
    """A TypeQL string literal."""
    return json.dumps(s, ensure_ascii=False)


def typeql_schema(schema: Any) -> str:
    doc = schema.doc if hasattr(schema, "doc") else schema
    lines = ["define"]
    lines += [f"  attribute {a}, value {t};" for a, t in HEADER_ATTRS]
    lines.append("  entity khg-entity @abstract, owns khg-id @key, owns khg-record;")
    owns = " ".join(f"owns {a}{' @key' if a == 'khg-id' else ''}," for a, _ in HEADER_ATTRS if a != "khg-record")
    lines.append(f"  relation khg-fact @abstract, {owns.rstrip(',')};")
    for et in doc["entity_types"]:
        parents = et.get("parents") or []
        lines.append(f"  entity {name(et['id'])}, sub {name(parents[0]) if parents else 'khg-entity'};")
    subtypes: dict[str, set[str]] = {}
    for et in doc["entity_types"]:
        for p in et.get("parents") or []:
            subtypes.setdefault(p, set()).add(et["id"])
    attrs_needed: set[str] = set()
    plays: list[str] = []
    relations = list(doc["relations"])
    for rel in relations:
        r = name(rel["id"])
        parts = [f"relation {r}, sub khg-fact"]
        for u in rel["roles"]:
            role = name(u["role"])
            kinds = {next(iter(f)) for f in u["fillers"]}
            if kinds & {"entity", "fact"}:
                parts.append(f"relates {role} @card(0..)")
            if "literal" in kinds:
                parts.append(f"owns lit-{role} @card(0..)")
                attrs_needed.add(f"lit-{role}")
            parts += [f"owns special-{role} @card(0..)", f"owns unbound-{role} @card(0..)"]
            attrs_needed |= {f"special-{role}", f"unbound-{role}"}
            for f in u["fillers"]:
                if "entity" in f:
                    for et in f["entity"]:
                        plays.append(f"  {name(et)} plays {r}:{role};")
                if "fact" in f:
                    for fr in f["fact"]:
                        plays.append(f"  {name(fr)} plays {r}:{role};")
        lines.append("  " + ", ".join(parts) + ";")
    for rel, roles in LIFECYCLE_ROLES.items():
        lines.append(f"  relation {name(rel)}, sub khg-fact, " +
                     ", ".join(f"relates {name(x)} @card(0..)" for x in roles) + ";")
        for x in roles:
            plays.append(f"  khg-fact plays {name(rel)}:{name(x)};")
    lines = lines[:1] + [f"  attribute {a}, value string;" for a in sorted(attrs_needed)] + lines[1:]
    return "\n".join(lines + sorted(set(plays)))


class TypeDBProbe(ReadOnlyProbe):
    NAME = "typedb"
    FLAGS = DECLARED
    driver = None

    def _open(self) -> None:
        from typedb.driver import Credentials, DriverOptions, DriverTlsConfig, TransactionType, TypeDB

        self.TT = TransactionType
        if TypeDBProbe.driver is None:
            TypeDBProbe.driver = TypeDB.driver(ADDR, Credentials("admin", "password"),
                                               DriverOptions(DriverTlsConfig.disabled()))
        _db_counter[0] += 1
        self.db = f"probe-{_db_counter[0]}"
        if self.driver.databases.contains(self.db):
            self.driver.databases.get(self.db).delete()
        self.driver.databases.create(self.db)
        self.schema_text = typeql_schema(self.schema)
        self._tx(self.schema_text, "SCHEMA")
        self.roles_by_name: dict[str, list[str]] = {}
        doc = self.schema.doc if hasattr(self.schema, "doc") else self.schema
        for rel in doc["relations"]:
            for u in rel["roles"]:
                if {next(iter(f)) for f in u["fillers"]} & {"entity", "fact"}:
                    self.roles_by_name.setdefault(u["role"], []).append(rel["id"])
        for rel, roles in LIFECYCLE_ROLES.items():
            for x in roles:
                self.roles_by_name.setdefault(x, []).append(rel)

    def close(self) -> None:
        try:
            self.driver.databases.get(self.db).delete()
        except Exception:  # noqa: BLE001
            pass

    def _tx(self, query: str, kind: str = "READ") -> list[dict[str, Any]]:
        with self.driver.transaction(self.db, getattr(self.TT, kind)) as tx:
            ans = tx.query(query).resolve()
            rows = []
            if ans.is_concept_rows():
                for row in ans.as_concept_rows():
                    d = {}
                    for col in row.column_names():
                        c = row.get(col)
                        d[col] = c.get_value() if c is not None and c.is_attribute() else c
                    rows.append(d)
            if kind != "READ":
                tx.commit()
            return rows

    # -- write
    def _write(self, entities: list[dict], facts: list[dict], bindings: list[dict]) -> None:
        if any(e["tx_to"] is not None for e in entities + facts):
            self.need("transaction_time")  # one relation instance per fact: no earlier versions
        statements = []
        for e in entities:
            rec = json.loads(e["record"])
            types = rec.get("types") or []
            if len(types) != 1:
                raise ValueError(f"{e['id']}: an instance has one type, not {types}")
            statements.append(f"insert $e isa {name(types[0])}, has khg-id {q(e['id'])}, "
                              f"has khg-record {q(e['record'])};")
        type_of = {e["id"]: name(json.loads(e["record"])["types"][0]) for e in entities}
        type_of.update({f["id"]: name(f["relation"]) for f in facts})
        by_fact: dict[str, list[dict]] = {}
        for b in bindings:
            by_fact.setdefault(b["fact_id"], []).append(b)
        # nested and lifecycle facts after the facts they bind
        done: set[str] = set()
        todo = {f["id"]: f for f in facts}
        order = []
        while todo:
            ready = [i for i, f in todo.items()
                     if all(b["ref"] in done or b["value_kind"] != "fact" for b in by_fact.get(i, []))]
            if not ready:
                raise ValueError("a nesting cycle")
            for i in sorted(ready):
                order.append(todo.pop(i))
                done.add(i)
        for f in order:
            rel = f["relation"]
            match, players, has = [], [], []
            for n, b in enumerate(by_fact.get(f["id"], [])):
                role = name(b["role"])
                if b["value_kind"] in ("entity", "fact"):
                    match.append(f"$p{n} isa {type_of[b['ref']]}, has khg-id {q(b['ref'])};")
                    players.append(f"{role}: $p{n}")
                elif b["value_kind"] == "literal":
                    has.append(f"has lit-{role} {q(b['ident'])}")
                elif b["value_kind"] == "special":
                    has.append(f"has special-{role} {q(json.loads(b['value_json'])['special'])}")
                else:
                    has.append(f"has unbound-{role} {q(json.loads(b['value_json'])['unbound']['var'])}")
            manifest = [{k: b[k] for k in ("bid", "role", "position", "direction", "value_kind", "ref", "value_json",
                                           "extensions") if b[k] is not None} for b in by_fact.get(f["id"], [])]
            has += [f"has khg-id {q(f['id'])}", f"has khg-status {q(f['status'])}", f"has khg-rank {q(f['rank'])}",
                    f"has khg-visibility {q(f['visibility'])}", f"has khg-rel-kind {q(f['rel_kind'])}",
                    f"has khg-s-lo {f['s_lo']}", f"has khg-s-hi {f['s_hi']}", f"has khg-e-lo {f['e_lo']}",
                    f"has khg-e-hi {f['e_hi']}", f"has khg-n-bindings {f['n_bindings']}",
                    f"has khg-payload {q(f['payload'])}", f"has khg-bindings {q(json.dumps(manifest))}",
                    f"has khg-version {f['version']}", f"has khg-recorded-at {q(f['recorded_at'])}",
                    f"has khg-recorded-by {q(f['recorded_by'])}"]
            if f["status_ref"] is not None:
                has.append(f"has khg-status-ref {q(f['status_ref'])}")
            if f["key_digest"] is not None:
                has.append(f"has khg-key-digest {q(f['key_digest'])}")
            head = ("match " + " ".join(match) + " ") if match else ""
            statements.append(f"{head}insert $f isa {name(rel)} ({', '.join(players)}), {', '.join(has)};")
        self.load_statements = statements
        with self.driver.transaction(self.db, self.TT.WRITE) as tx:  # one transaction: all or nothing
            for s in statements:
                tx.query(s).resolve()
            tx.commit()
        missing = [f["id"] for f in facts if not self._tx(f"match $f isa khg-fact, has khg-id {q(f['id'])};")]
        if missing:
            raise ValueError(f"TypeDB dropped {missing} (a relation without role players is deleted at commit)")

    # -- reads
    ATTRS = ("khg-id", "khg-status", "khg-rank", "khg-visibility", "khg-payload", "khg-bindings", "khg-version",
             "khg-recorded-at", "khg-recorded-by")

    def _fact_row(self, id: str) -> dict | None:
        cols = " ".join(f"has {a} ${a.replace('-', '_')}," for a in self.ATTRS).rstrip(",")
        rows = self._tx(f"match $f isa khg-fact, has khg-id {q(id)}, {cols}; $f isa! $t;")
        if not rows:
            return None
        r = rows[0]
        ref = self._tx(f"match $f isa khg-fact, has khg-id {q(id)}, has khg-status-ref $s;")
        return {"id": id, "relation": None, "status": r["khg_status"], "rank": r["khg_rank"],
                "visibility": r["khg_visibility"], "payload": r["khg_payload"], "bindings": r["khg_bindings"],
                "version": r["khg_version"], "recorded_at": r["khg_recorded_at"], "recorded_by": r["khg_recorded_by"],
                "status_ref": ref[0]["s"] if ref else None, "type": r["t"].get_label()}

    def _relation_of(self, label: str) -> str:
        doc = self.schema.doc if hasattr(self.schema, "doc") else self.schema
        for rel in [x["id"] for x in doc["relations"]] + list(LIFECYCLE_RELATIONS):
            if name(rel) == label:
                return rel
        raise KeyError(label)

    def _get(self, id: str, t: int | None, version: int | None) -> dict | None:
        f = self._fact_row(id)
        if f is not None:
            f["relation"] = self._relation_of(f["type"])
            return assemble(f, json.loads(f["bindings"]))
        rows = self._tx(f"match $e isa khg-entity, has khg-id {q(id)}, has khg-record $r;")
        return json.loads(rows[0]["r"]) if rows else None

    def _versions(self, id: str) -> list[dict]:
        r = self._get(id, None, None)
        return [r] if r else []

    def _ids(self, t: int | None) -> list[str]:
        return sorted(r["id"] for r in self._tx("match $x has khg-id $id;"))

    def _is_fact(self, id: str) -> bool:
        return bool(self._tx(f"match $f isa khg-fact, has khg-id {q(id)};"))

    @staticmethod
    def _one_of(var: str, values: Any) -> str:
        vs = sorted(values)
        if not vs:
            return f"{var} == \"-no-value-\";"
        return " or ".join("{ " + f"{var} == {q(v)};" + " }" for v in vs) + ";"

    def _filters(self, where: Any, as_of: int | None) -> str:
        out = ["$f has khg-id $id, has khg-status $st, has khg-rank $rk, has khg-visibility $vis, "
               "has khg-rel-kind $kind;",
               self._one_of("$st", where.status), self._one_of("$rk", where.rank),
               self._one_of("$vis", where.visibility), self._one_of("$kind", where.kinds)]
        if as_of is not None:
            lo, hi = ("khg-s-hi", "khg-e-lo") if where.valid_mode == "definite" else ("khg-s-lo", "khg-e-hi")
            out += [f"$f has {lo} $vlo, has {hi} $vhi;", f"$vlo <= {as_of};", f"$vhi > {as_of};"]
        return " ".join(out)

    def _run_ids(self, body: str, where: Any, as_of: int | None, after: str | None, limit: int | None) -> list[str]:
        query = f"match {body} {self._filters(where, as_of)}"
        if after is not None:
            query += f" $id > {q(after)};"
        query += " select $id; sort $id;"  # distinct ids: one row per id after select? kept below
        self.last_typeql = query
        ids = []
        for r in self._tx(query):
            if not ids or ids[-1] != r["id"]:
                ids.append(r["id"])
        return ids[:limit] if limit is not None else ids

    def _incident_ids(self, node, role, relation, where, t, as_of, after, limit) -> list[str]:
        body = f"$n has khg-id {q(node)}; $f isa khg-fact, links ($n);"
        branches = []
        if role is not None:
            rels = [r for r in self.roles_by_name.get(role, []) if relation is None or r == relation]
            if not rels:
                return []
            branches = ["{ " + f"$f isa {name(r)}, links ({name(role)}: $n);" + " }" for r in rels]
        elif relation is not None:
            branches = ["{ " + f"$f isa {name(relation)};" + " }"]
        if branches:
            body += " " + " or ".join(branches) + ";"
        return self._run_ids(body, where, as_of, after, limit)

    def _find_ids(self, relation, pats, match, where, t, as_of, after, limit) -> list[str]:
        r = name(relation)
        body = [f"$f isa {r};"]
        for i, p in enumerate(pats, 1):
            role = name(p.role)
            if p.kind == "value":
                v = json.loads(p.ident)
                kind = next(iter(v))
                if kind in ("entity", "fact"):
                    body.append(f"$f links ({role}: $p{i}); $p{i} has khg-id {q(v[kind])};")
                else:
                    body.append(f"$f has lit-{role} {q(p.ident)};")
            elif p.kind == "any":
                has_role = relation in [x for rs in self.roles_by_name.values() for x in rs] and \
                    relation in self.roles_by_name.get(p.role, [])
                opts = [f"{{ $f links ({role}: $a{i}); }}"] if has_role else []
                opts.append(f"{{ $f has lit-{role} $a{i}; }}") if self._owns(relation, f"lit-{role}") else None
                if not opts:
                    return []
                body.append(" or ".join(opts) + ";")
        if match == "exact":
            body.append(f"$f has khg-n-bindings {len(pats)};")
        candidates = self._run_ids(" ".join(body), where, as_of, after, None)
        # the multiset (injective) check on the kept bindings: TypeDB collapses a repeated player or attribute
        out = []
        for i in candidates:
            rec = self._get(i, None, None)
            bs = rec["bindings"]
            from khg_contracts.record import identity_key

            def ok(a: int, b: int) -> bool:
                p, x = pats[a], bs[b]
                if x["role"] != p.role or (p.position is not None and x.get("position") != p.position):
                    return False
                if p.kind == "any":
                    return True
                return "unbound" not in x["value"] and identity_key(x["value"]) == p.ident

            if (match != "exact" or len(pats) == len(bs)) and injective_match(len(pats), len(bs), ok):
                out.append(i)
        return out[:limit] if limit is not None else out

    def _owns(self, relation: str, attr: str) -> bool:
        return f"owns {attr} " in self.schema_text.split(f"relation {name(relation)},", 1)[-1].split(";", 1)[0] + " "

    def _key_ids(self, relation, digest, where, t, as_of) -> list[str]:
        return self._run_ids(f"$f isa {name(relation)}, has khg-key-digest {q(digest)};", where, as_of, None, None)

    def native_walk(self, id: str, direction: str = "forward") -> list[list]:
        """One TypeQL query with a recursive function (TypeDB 3 functions may call themselves)."""
        frm, to = ("khg-superseded", "khg-superseding") if direction == "forward" else \
            ("khg-superseding", "khg-superseded")
        query = f"""with fun reach($x: khg-fact) -> {{ khg-supersedes, khg-fact, khg-fact }}:
  match
    {{ $s isa khg-supersedes, links ({frm}: $a, {to}: $y), has khg-status "asserted"; $a is $x; }} or
    {{ $s0 isa khg-supersedes, links ({frm}: $x, {to}: $m), has khg-status "asserted";
      let $s, $a, $y in reach($m); }};
  return {{ $s, $a, $y }};
match $start isa khg-fact, has khg-id {q(id)};
  let $s, $a, $y in reach($start);
  $s has khg-id $via; $a has khg-id $from; $y has khg-id $to;
select $via, $from, $to;"""
        self.walk_typeql = query
        rows = self._tx(query)
        # depth is not returned by the function; recover it from the chain
        depth = {id: 0}
        steps = []
        pending = [(r["via"], r["from"], r["to"]) for r in rows]
        while pending:
            rest = []
            for via, a, b in pending:
                if a in depth:
                    steps.append([depth[a] + 1, via, a, b])
                    depth.setdefault(b, depth[a] + 1)
                else:
                    rest.append((via, a, b))
            if len(rest) == len(pending):
                break
            pending = rest
        return sorted(steps)


def rebuild_native(store: TypeDBProbe, container: dict) -> dict[str, Any]:
    """Rebuild every hyperedge from the native structure only (role players and owned attributes, no
    khg-bindings manifest), give bids by canonical order, and compare with the fixture."""
    out = copy.deepcopy(container)
    for r in out["records"]:
        if r.get("kind") != "hyperedge":
            continue
        bs = []
        for row in store._tx(f"match $f isa khg-fact, has khg-id {q(r['id'])}; $f links ($role: $p); "
                             "$p has khg-id $pid;"):
            role_label = row["role"].get_label().split(":")[-1]
            role = next(u for u in {b["role"] for b in r["bindings"]} | set(sum(LIFECYCLE_ROLES.values(), []))
                        if name(u) == role_label)
            kind = "fact" if store._is_fact(row["pid"]) else "entity"
            bs.append({"role": role, "value": {kind: row["pid"]}})
        for row in store._tx(f"match $f isa khg-fact, has khg-id {q(r['id'])}, has $a; $a isa! $t;"):
            label = row["t"].get_label()
            for prefix, kind in (("lit-", "literal"), ("special-", "special"), ("unbound-", "unbound")):
                if label.startswith(prefix):
                    role = next(b["role"] for b in r["bindings"] if name(b["role"]) == label[len(prefix):])
                    val = row["a"]
                    # a literal comes back as its identity only (the written form is not stored)
                    value = {"literal-identity": val} if kind == "literal" else {"special": val} \
                        if kind == "special" else {"unbound": {"var": val}}
                    bs.append({"role": role, "value": value})
        bs.sort(key=lambda b: (b["role"], json.dumps(b["value"], sort_keys=True)))
        r["bindings"] = [dict(b, bid=f"b{i}") for i, b in enumerate(bs, 1)]
    diffs = compare_containers(container, out)
    from khg_contracts.record import identity_key

    def multiset(rec: dict) -> list:
        def ident(v: dict) -> str:
            if "literal-identity" in v:
                return v["literal-identity"]
            if "unbound" in v:
                return "unbound:" + v["unbound"]["var"]
            return identity_key(v)

        return sorted([b["role"], ident(b["value"])] for b in rec["bindings"])

    orig = {r["id"]: r for r in container["records"] if r.get("kind") == "hyperedge"}
    rebuilt = {r["id"]: r for r in out["records"] if r.get("kind") == "hyperedge"}
    same_rv = [i for i in orig if multiset(orig[i]) == multiset(rebuilt[i])]
    bindings = [b for r in orig.values() for b in r["bindings"]]
    return {"compare_containers_differences": len(diffs), "hyperedges": len(orig),
            "same_role_value_multiset": len(same_rv),
            "differ_in_role_value_multiset": sorted(set(orig) - set(same_rv)),
            "bindings": len(bindings),
            "lost_per_binding": {
                "bid (regenerated)": len(bindings),
                "position": sum("position" in b for b in bindings),
                "direction": sum("direction" in b for b in bindings),
                "extensions": sum("extensions" in b for b in bindings),
                "literal as written (identity kept)": sum("literal" in b["value"] for b in bindings),
                "unbound expect": sum("unbound" in b["value"] and "expect" in b["value"]["unbound"]
                                      for b in bindings)},
            "examples": diffs[:2]}


def main() -> None:
    container, schema = fixture()
    started = time.perf_counter()
    store = TypeDBProbe(schema, capabilities=DECLARED | {"goals", "special_values", "ordered_roles"})
    result: dict[str, Any] = {"server": "TypeDB CE 3.13.6", "driver": "typedb-driver 3.13.6",
                              "schema_typeql": store.schema_text}
    store.load(container)
    result["load_seconds_incl_schema"] = round(time.perf_counter() - started, 3)
    result["insert_example"] = [s for s in store.load_statements if "f:king-14" in s][0]
    result["hand"] = hand_check(store)
    store.incident("ex:KingOfFrance", where={"as_of": "+1700-01-01T00:00:00Z"})
    result["incident_typeql_example"] = store.last_typeql
    result["walk_typeql"] = store.walk_typeql
    result["native_structure_only_round_trip"] = rebuild_native(store, container)
    store.close()
    started = time.perf_counter()
    result["read_only_scenarios"] = run_read_only(lambda s_, c: TypeDBProbe(s_, clock=c))
    result["scenario_seconds"] = round(time.perf_counter() - started, 2)
    print(result["read_only_scenarios"]["counts"], "export diffs:",
          result["hand"]["export khg-json round trip"]["differences"],
          "native-only:", {k: v for k, v in result["native_structure_only_round_trip"].items() if k != "examples"},
          "hand mismatches:", [k for k, v in result["hand"].items()
                               if isinstance(v, dict) and (v.get("same_as_reference") is False or "error" in v)])
    write_out("typedb", result)


if __name__ == "__main__":
    main()
