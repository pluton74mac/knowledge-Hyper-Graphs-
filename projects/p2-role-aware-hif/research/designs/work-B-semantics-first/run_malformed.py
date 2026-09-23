"""Malformed-case suite (gate clause 2). Every case must be rejected at its expected layer, and its
expected code must be among the codes reported (a malformed input may raise several). JSON Schema
layers report codes through khg_codes (x-khg-code annotations; H table for the vendored schema)."""
import copy, json, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import khg_codes
from khg_proto import Schema, KHGError, strict_loads, hif_to_c1, c1_to_hif, derived, literal_node_id
from khg_semantic import validate_document
from khg_schema_check import validate_schema_doc
from proto_store import fold_check

SD = json.loads((HERE / "p2-gate.schema.json").read_text())
S = Schema(SD)
C1 = json.loads((HERE / "fixture-directed.khg.json").read_text())
HD = json.loads((HERE / "fixture-directed.hif.json").read_text())
QX = json.loads((HERE / "queue-examples.json").read_text())


def schema_layer(layer, inst):
    """(codes, first message) of one JSON Schema layer, or None when it passes."""
    rows = khg_codes.report(layer, inst)
    if not rows:
        return None
    code, path, kw, msg = rows[0]
    return [r[0] for r in rows], f"{path}: {kw}: {msg[:110]}"


def run_hif(obj_or_text):
    try:
        doc = strict_loads(obj_or_text) if isinstance(obj_or_text, str) else obj_or_text
    except KHGError as ex:
        return "J", [ex.code], str(ex)[:120]
    for layer in ("H", "P"):
        r = schema_layer(layer, doc)
        if r:
            return layer, r[0], r[1]
    try:
        c1 = hif_to_c1(doc, S)
    except KHGError as ex:
        return "D(decode)", [ex.code], str(ex)[:120]
    return run_c1(c1)


def run_c1(doc):
    r = schema_layer("C", doc)
    if r:
        return "C", r[0], r[1]
    try:
        errs = [x for x in validate_document(doc, S) if x[1] == "violation"]
    except KHGError as ex:
        return "S", [ex.code], str(ex)[:120]
    if errs:
        return "S/D", [c for c, _, _ in errs], "; ".join(f"{c} {m}" for c, _, m in errs)[:160]
    return None, [], "ACCEPTED"


def run_schema(sd):
    r = schema_layer("M", sd)
    if r:
        return "M(json)", r[0], r[1]
    errs = validate_schema_doc(sd)
    if errs:
        return "M(sem)", [e[0] for e in errs], errs[0][2][:120]
    return None, [], "ACCEPTED"


def run_queue(records):
    """A queue store: items and log entries against khg-queue/1.0.0, then the fold over the log."""
    for x in records:
        r = schema_layer("Q", x)
        if r:
            return "Q", r[0], r[1]
    items = [x for x in records if x["kind"] == "queue_item"]
    log = [x for x in records if x["kind"] == "log_entry"]
    errs = fold_check(items, log)
    if errs:
        return "Q(fold)", [e[0] for e in errs], f"{errs[0][1]}: {errs[0][2]}"
    return None, [], "ACCEPTED"


def hif(f):
    d = copy.deepcopy(HD); f(d); return d


def c1(f):
    d = copy.deepcopy(C1); f(d); return d


def sch(f):
    d = copy.deepcopy(SD); f(d); return d


def rec(d, i):
    return next(r for r in d["records"] if r.get("id") == i)


def inc(d, edge, bid):
    return next(x for x in d["incidences"] if x["edge"] == edge and x["attrs"]["khg:bid"] == bid)


TXT = json.dumps(HD, ensure_ascii=False)
CASES = [
    # --- strict JSON (layer J) ---
    ("MC01", "zero-byte file (R02 case 34)", "hif", ""),
    ("MC02", "not JSON: truncated document", "hif", TXT[:200]),
    ("MC03", "duplicate key inside one attrs object (R02 case 36)", "hif", TXT.replace('"role": "context", "khg:bid"', '"role": "context", "role": "target", "khg:bid"', 1)),
    ("MC04", "NaN literal (R02 case 35, R03 c22, R01 V19)", "hif", TXT.replace('"khg:version": 2', '"khg:version": NaN', 1)),
    ("MC05", "lone surrogate escape in a string", "hif", TXT.replace('"TP53"', '"TP53\\ud800"', 1)),
    # --- vendored HIF schema (layer H) ---
    ("MC06", "no incidences (R01 V01, R02 case 31)", "hif", hif(lambda d: d.pop("incidences"))),
    ("MC07", "top-level 'version' key (R01 V02, R02 case 04)", "hif", hif(lambda d: d.update({"version": "1.0.0"}))),
    ("MC08", "top-level 'roles' vocabulary (R02 case 05)", "hif", hif(lambda d: d.update({"roles": {}}))),
    ("MC09", "top-level '$schema' (R02 case 06)", "hif", hif(lambda d: d.update({"$schema": "x"}))),
    ("MC10", "record-level 'role' on an incidence (R01 V03, R02 case 11)", "hif", hif(lambda d: d["incidences"][0].update({"role": "context"}))),
    ("MC11", "record-level 'relation' on an edge (R02 case 13)", "hif", hif(lambda d: d["edges"][0].update({"relation": "x"}))),
    ("MC12", "record-level 'type' on a node (R02 case 14)", "hif", hif(lambda d: d["nodes"][0].update({"type": "Gene"}))),
    ("MC13", "incidence attrs is a string (R02 case 10)", "hif", hif(lambda d: d["incidences"][0].update({"attrs": "context"}))),
    ("MC14", "direction 'treatment' (R01 V05, R02 case 12)", "hif", hif(lambda d: d["incidences"][0].update({"direction": "treatment"}))),
    ("MC15", "incidence without node (R01 V04)", "hif", hif(lambda d: d["incidences"][0].pop("node"))),
    ("MC16", "id of type float 1.5 (R02 case 18)", "hif", hif(lambda d: d["incidences"][0].update({"node": 1.5}))),
    ("MC17", "id of type boolean (R02 case 19)", "hif", hif(lambda d: d["incidences"][0].update({"node": True}))),
    ("MC18", "id null (R02 case 20)", "hif", hif(lambda d: d["incidences"][0].update({"node": None}))),
    ("MC19", "network-type 'knowledge-hypergraph' (R02 case 26)", "hif", hif(lambda d: d.update({"network-type": "knowledge-hypergraph"}))),
    # --- KHG profile (layer P) ---
    ("MC20", "metadata without the khg-profile declaration (R01 V07)", "hif", hif(lambda d: d["metadata"].pop("khg-profile"))),
    ("MC21", "no metadata at all", "hif", hif(lambda d: d.pop("metadata"))),
    ("MC22", "integer ids (R02 cases 15-17, 22)", "hif", hif(lambda d: [x.update({"edge": 7}) for x in d["incidences"][:1]])),
    ("MC23", "empty-string id (R02 case 21)", "hif", hif(lambda d: d["incidences"][0].update({"node": ""}))),
    ("MC24", "incidence of a fact without a role (R01 V08)", "hif", hif(lambda d: d["incidences"][0]["attrs"].pop("role"))),
    ("MC25", "list-valued role (R01 V09, R02 case 09)", "hif", hif(lambda d: d["incidences"][0]["attrs"].update({"role": ["context", "regulator"]}))),
    ("MC26", "empty role string (R01 V09)", "hif", hif(lambda d: d["incidences"][0]["attrs"].update({"role": ""}))),
    ("MC27", "legacy 'roles' key beside 'role' (R01 V20)", "hif", hif(lambda d: d["incidences"][0]["attrs"].update({"roles": ["target"]}))),
    ("MC28", "network-type 'asc' (R03 D8, c04)", "hif", hif(lambda d: d.update({"network-type": "asc"}))),
    ("MC29", "metadata.default_attrs (R03 D7, c20)", "hif", hif(lambda d: d["metadata"].update({"default_attrs": {}}))),
    ("MC30", "directed file, an incidence without direction (R01 V12, R02 case 23, R03 c14)", "hif", hif(lambda d: d["incidences"][3].pop("direction"))),
    ("MC31", "undirected file carrying record-level direction (R01 V13, R02 cases 24-25)", "hif", hif(lambda d: d.update({"network-type": "undirected"}))),
    ("MC32", "fact edge without khg:relation (R01 V14)", "hif", hif(lambda d: d["edges"][0]["attrs"].pop("khg:relation"))),
    ("MC33", "edge without khg:kind (R01 V40)", "hif", hif(lambda d: d["edges"][0]["attrs"].pop("khg:kind"))),
    ("MC34", "unknown khg: key in incidence attrs", "hif", hif(lambda d: d["incidences"][0]["attrs"].update({"khg:roles": ["x"]}))),
    ("MC35", "literal node whose id lacks the _: prefix", "hif", hif(lambda d: [n.update({"node": "lit-1"}) for n in d["nodes"] if n["attrs"]["khg:kind"] == "literal"][:1])),
    ("MC36", "entity node id using the reserved _: prefix", "hif", hif(lambda d: d["nodes"][0].update({"node": "_:ex"}))),
    ("MC37", "hif-schema pinned to the moving 'main' URL", "hif", hif(lambda d: d["metadata"].update({"hif-schema": "https://raw.githubusercontent.com/HIF-org/HIF-standard/main/schemas/hif_schema.json"}))),
    ("MC38", "role-position 0", "hif", hif(lambda d: [x["attrs"].update({"role-position": 0}) for x in d["incidences"] if "role-position" in x["attrs"]][:1])),
    # --- decode of the profile (layer D, cross-record) ---
    ("MC39", "node declared twice (R01 V16, R03 c19)", "hif", hif(lambda d: d["nodes"].append(copy.deepcopy(d["nodes"][0])))),
    ("MC40", "edge declared twice (R01 V16)", "hif", hif(lambda d: d["edges"].append(copy.deepcopy(d["edges"][0])))),
    ("MC41", "incidence names an undeclared node (R01 V17, R02 case 28)", "hif", hif(lambda d: d["incidences"][0].update({"node": "ex:ghost"}))),
    ("MC42", "incidence names an undeclared edge (R02 case 29)", "hif", hif(lambda d: d["incidences"][0].update({"edge": "f:ghost"}))),
    ("MC43", "literal node id does not match its value", "hif", hif(lambda d: [n["attrs"]["khg:literal"].update({"amount": "+1"}) for n in d["nodes"] if n["attrs"]["khg:kind"] == "literal" and n["attrs"]["khg:literal"]["datatype"] == "quantity"][:1])),
    ("MC44", "schema hash in metadata does not match the schema", "hif", hif(lambda d: d["metadata"].update({"khg-schema-sha256": "sha256:" + "0" * 64}))),
    ("MC45", "incidence direction contradicts the role's declared direction (R01 V38)", "hif", hif(lambda d: inc(d, "f:reg-1", "b3").update({"direction": "tail"}))),
    ("MC46", "fact-ref node pointing to a missing edge (R01 V18)", "hif", hif(lambda d: [[n["attrs"].update({"khg:ref": "f:ghost"}), n.update({"node": "_:ref:f:ghost"})] for n in d["nodes"] if n["node"] == "_:ref:f:born-louis14-paris"] and [x.update({"node": "_:ref:f:ghost"}) for x in d["incidences"] if x["node"] == "_:ref:f:born-louis14-paris"])),
    # --- C1 record structure (layer C) ---
    ("MC47", "binding value with two kinds (entity and literal)", "c1", c1(lambda d: rec(d, "f:reg-1")["bindings"][0]["value"].update({"literal": {"datatype": "string", "value": "x"}}))),
    ("MC48", "status outside the lifecycle enum (R01 V36)", "c1", c1(lambda d: rec(d, "f:reg-1").update({"status": "archived"}))),
    ("MC49", "confidence as a bare number (R01 V32)", "c1", c1(lambda d: rec(d, "f:coadmin-1").update({"confidence": 0.9}))),
    ("MC50", "quantity without unit (R01 V26)", "c1", c1(lambda d: rec(d, "f:pop-łódź-2019")["bindings"][1]["value"]["literal"].pop("unit"))),
    ("MC51", "time precision 15", "c1", c1(lambda d: rec(d, "f:king-13")["bindings"][2]["value"]["literal"].update({"precision": 15}))),
    ("MC52", "UNBOUND value in a fact (R01 V34)", "c1", c1(lambda d: rec(d, "f:reg-1")["bindings"][0].update({"value": {"unbound": {"var": "x"}}}))),
    ("MC53", "status superseded without status_ref (R01 V37)", "c1", c1(lambda d: rec(d, "f:born-skłodowska-kraków").pop("status_ref"))),
    ("MC54", "extracted evidence without selectors and activity (R01 V47, record side)", "c1", c1(lambda d: [rec(d, "f:route-1")["evidence"][0].pop(k) for k in ("selectors", "activity")])),
    ("MC55", "rank deprecated without rank_reason", "c1", c1(lambda d: rec(d, "f:reg-1").update({"rank": "deprecated"}))),
    ("MC56", "span selector with a negative start", "c1", c1(lambda d: rec(d, "f:route-1")["evidence"][0]["selectors"][1].update({"start": -1}))),
    ("MC57", "record-level key outside the format (e.g. 'weight')", "c1", c1(lambda d: rec(d, "f:reg-1").update({"weight": 1.0}))),
    # --- semantics against the relation-type schema (layer S) ---
    ("MC58", "relation not declared (R01 V21)", "c1", c1(lambda d: rec(d, "f:reg-1").update({"relation": "inhibits"}))),
    ("MC59", "role not allowed for the relation (R01 V22)", "c1", c1(lambda d: rec(d, "f:reg-1")["bindings"][0].update({"role": "agent"}))),
    ("MC60", "required role missing on an asserted fact (R01 V23)", "c1", c1(lambda d: rec(d, "f:reg-1")["bindings"].pop(2))),
    ("MC61", "role bound more often than max (R01 V24)", "c1", c1(lambda d: [d["records"].append({"kind": "entity", "id": "ex:MDM2", "types": ["Gene"]}), rec(d, "f:reg-1")["bindings"].append({"bid": "b9", "role": "target", "value": {"entity": "ex:MDM2"}})])),
    ("MC62", "entity of the wrong type (R01 V25)", "c1", c1(lambda d: rec(d, "f:reg-1")["bindings"][1].update({"value": {"entity": "ex:HeLa"}}))),
    ("MC63", "literal where an entity is expected (R01 V25)", "c1", c1(lambda d: rec(d, "f:reg-1")["bindings"][1].update({"value": {"literal": {"datatype": "string", "value": "TP53"}}}))),
    ("MC64", "time literal with month 13 (R01 V26)", "c1", c1(lambda d: rec(d, "f:king-13")["bindings"][2]["value"]["literal"].update({"time": "+1610-13-14T00:00:00Z"}))),
    ("MC65", "day set below year precision (R01 V26)", "c1", c1(lambda d: rec(d, "f:pop-łódź-2019")["bindings"][2]["value"]["literal"].update({"time": "+2019-06-01T00:00:00Z"}))),
    ("MC66", "fact with no bindings (R01 V27)", "c1", c1(lambda d: rec(d, "f:reg-1").update({"bindings": [], "evidence": [{"id": "e1", "type": "curated", "mode": "manual"}]}))),
    ("MC67", "fact reference in a role that takes no facts (R01 V29)", "c1", c1(lambda d: rec(d, "f:reg-1")["bindings"][0].update({"value": {"fact": "f:king-13"}}))),
    ("MC68", "valid time starts after it ends (R01 V30)", "c1", c1(lambda d: rec(d, "f:king-13")["bindings"][3]["value"]["literal"].update({"time": "+1600-01-01T00:00:00Z"}))),
    ("MC69", "confidence scale not declared (R01 V32)", "c1", c1(lambda d: rec(d, "f:coadmin-1").update({"confidence": {"value": 0.9, "scale": "gut-feeling"}}))),
    ("MC70", "confidence outside its scale (R01 V32)", "c1", c1(lambda d: rec(d, "f:coadmin-1").update({"confidence": {"value": 1.4, "scale": "probability"}}))),
    ("MC71", "asserted fact with no evidence (R01 V33)", "c1", c1(lambda d: rec(d, "f:reg-1").update({"evidence": []}))),
    ("MC72", "novalue and a concrete value in one role (R01 V35)", "c1", c1(lambda d: [d["records"].append({"kind": "entity", "id": "ex:Zn", "types": ["Chemical"]}), rec(d, "f:cat-7")["bindings"].append({"bid": "b3", "role": "catalyst", "value": {"entity": "ex:Zn"}})])),
    ("MC73", "the same filler twice in an unordered role (set semantics)", "c1", c1(lambda d: rec(d, "f:coadmin-1")["bindings"][0].update({"value": {"entity": "ex:metformin"}}))),
    ("MC74", "ordered role with a gap in positions", "c1", c1(lambda d: rec(d, "f:route-1")["bindings"][3].update({"position": 5}))),
    ("MC75", "position on an unordered role", "c1", c1(lambda d: rec(d, "f:coadmin-1")["bindings"][0].update({"position": 1}))),
    ("MC76", "goal omits a required role instead of leaving it unbound", "c1", c1(lambda d: rec(d, "g:who-1774")["bindings"].pop(0))),
    ("MC77", "one unbound variable used twice in a goal", "c1", c1(lambda d: rec(d, "g:who-1774")["bindings"].append({"bid": "b4", "role": "replaces", "value": {"unbound": {"var": "who"}}}))),
    ("MC78", "id not in Unicode NFC", "c1", c1(lambda d: [rec(d, "ex:Kraków").update({"id": "ex:Kraków"}), rec(d, "f:born-skłodowska-kraków")["bindings"][1].update({"value": {"entity": "ex:Kraków"}})])),
    ("MC79", "evidence supports an unknown binding id", "c1", c1(lambda d: rec(d, "f:king-14")["evidence"][1].update({"supports": ["b1", "b9"]}))),
    ("MC80", "precision below the role's precision_min", "c1", c1(lambda d: rec(d, "f:pop-łódź-2019")["bindings"][2]["value"]["literal"].update({"time": "+2010-00-00T00:00:00Z", "precision": 8}))),
    ("MC81", "unit not allowed for the role", "c1", c1(lambda d: rec(d, "f:pop-łódź-2019")["bindings"][1]["value"]["literal"].update({"unit": "wd:Q11573"}))),
    ("MC82", "the same binding id twice in one fact", "c1", c1(lambda d: rec(d, "f:reg-1")["bindings"][1].update({"bid": "b1"}))),
    ("MC83", "somevalue where the role forbids it", "c1", c1(lambda d: rec(d, "f:claim-1")["bindings"][1].update({"value": {"special": "somevalue"}}))),
    # --- cross-record checks (layer D) ---
    ("MC84", "nesting cycle (R01 V28)", "c1", c1(lambda d: d["records"].append({"kind": "meta", "id": "m:dis-x", "relation": "khg:disputes", "status": "asserted", "meta": {"reason": "curator"}, "evidence": [{"id": "e1", "type": "curated", "mode": "manual"}], "bindings": [{"bid": "b1", "role": "khg:disputed", "value": {"fact": "m:dis-x"}}, {"bid": "b2", "role": "khg:disputed", "value": {"fact": "f:reg-1"}}]}))),
    ("MC85", "status_ref points at a record of the wrong kind (R01 V37)", "c1", c1(lambda d: rec(d, "f:born-skłodowska-kraków").update({"status_ref": "f:reg-1"}))),
    ("MC86", "supersession cycle (R01 V37)", "c1", c1(lambda d: [rec(d, "f:born-skłodowska-warszawa").update({"status": "superseded", "status_ref": "m:sup-2"}), d["records"].append({"kind": "meta", "id": "m:sup-2", "relation": "khg:supersedes", "status": "asserted", "meta": {"reason": "correction"}, "evidence": [{"id": "e1", "type": "curated", "mode": "manual"}], "bindings": [{"bid": "b1", "role": "khg:superseding", "value": {"fact": "f:born-skłodowska-kraków"}}, {"bid": "b2", "role": "khg:superseded", "value": {"fact": "f:born-skłodowska-warszawa"}}]})])),
    ("MC87", "correction between facts of different relations (R01 V37)", "c1", c1(lambda d: rec(d, "m:sup-1")["bindings"][0].update({"value": {"fact": "f:reg-1"}}))),
    ("MC88", "two asserted facts, same key binding, overlapping valid time (R01 V42)", "c1", c1(lambda d: rec(d, "f:king-14")["bindings"][2]["value"]["literal"].update({"time": "+1640-01-01T00:00:00Z"}))),
    ("MC89", "stored derived fields disagree with the bindings (R01 V15)", "c1", c1(lambda d: rec(d, "f:reg-1").update({"derived": dict(derived(S, rec(d, "f:reg-1")), arity=5)}))),
    ("MC90", "a candidate inside a store document (queue boundary, F9)", "c1", c1(lambda d: rec(d, "f:reg-1").update({"status": "candidate"}))),
    ("MC91", "entity referenced but not declared in a complete document (R01 V17)", "c1", c1(lambda d: d["records"].remove(rec(d, "ex:HeLa")))),
    ("MC92", "one id names both an entity and a fact", "c1", c1(lambda d: rec(d, "ex:Paris").update({"id": "f:reg-1"}) or rec(d, "f:born-louis14-paris")["bindings"][1].update({"value": {"entity": "f:reg-1"}}))),
    # --- relation-type schema documents (layer M) ---
    ("MC93", "relation with no roles (R01 V43)", "schema", sch(lambda d: d["relations"][0].update({"roles": []}))),
    ("MC94", "a role used twice in one relation (R01 V44)", "schema", sch(lambda d: d["relations"][0]["roles"].append(copy.deepcopy(d["relations"][0]["roles"][0])))),
    ("MC95", "key names a role the relation does not use (R01 V44)", "schema", sch(lambda d: next(r for r in d["relations"] if r["id"] == "position_held")["key"].update({"roles": ["office"]}))),
    ("MC96", "key built on a time-slot role", "schema", sch(lambda d: next(r for r in d["relations"] if r["id"] == "position_held")["key"].update({"roles": ["start_time"]}))),
    ("MC97", "schema version not semver (R01 V45)", "schema", sch(lambda d: d.update({"version": "1.0"}))),
    ("MC98", "unknown datatype (R01 V46)", "schema", sch(lambda d: d["relations"][0]["roles"][0].update({"fillers": [{"literal": "date"}]}))),
    ("MC99", "unknown entity type in a filler (R01 V46)", "schema", sch(lambda d: d["relations"][0]["roles"][0].update({"fillers": [{"entity": ["Protein"]}]}))),
    ("MC100", "complete: true on an optional role", "schema", sch(lambda d: d["relations"][0]["roles"][2].update({"complete": True}))),
    ("MC101", "time model names a role that is not a time slot", "schema", sch(lambda d: next(r for r in d["relations"] if r["id"] == "position_held")["time"].update({"start": "replaces"}))),
    ("MC102", "user schema declares a relation in the reserved khg: namespace", "schema", sch(lambda d: d["relations"][0].update({"id": "khg:regulates"}))),
    ("MC103", "temporal key on a relation without an interval time model", "schema", sch(lambda d: next(r for r in d["relations"] if r["id"] == "born_in")["key"].update({"temporal": True}))),
]

def queue(f):
    d = copy.deepcopy([QX["item"]] + QX["log"]); f(d); return d


def item(d):
    return next(x for x in d if x["kind"] == "queue_item")


def entry(d, action):
    return next(x for x in d if x["kind"] == "log_entry" and x["action"] == action)


QUEUE_CASES = [
    ("MC104", "candidate without run_id (R01 V47)", "queue", queue(lambda d: item(d)["extraction"].pop("run_id"))),
    ("MC105", "candidate payload with status asserted", "queue", queue(lambda d: item(d)["payload"].update({"status": "asserted"}))),
    ("MC106", "unknown item_kind (R01 V48)", "queue", queue(lambda d: item(d).update({"item_kind": "new_thing"}))),
    ("MC107", "lint log entry without findings", "queue", queue(lambda d: entry(d, "lint").pop("findings"))),
    ("MC108", "log entry whose state_before does not follow the fold (accepted -> pending) (R01 V48)", "queue",
     queue(lambda d: d.append(dict(copy.deepcopy(entry(d, "lint")), log_id="l-000004", parent_log_id="l-000003")))),
]

POSITIVE = [
    ("OK1", "directed gate fixture (HIF)", "hif", HD),
    ("OK2", "undirected gate fixture (HIF)", "hif", json.loads((HERE / "fixture-undirected.hif.json").read_text())),
    ("OK3", "directed gate fixture (C1)", "c1", C1),
    ("OK4", "gate schema", "schema", SD),
    ("OK5", "queue item and its action log from the smoke test", "queue", [QX["item"]] + QX["log"]),
]

EXPECTED = {
    "MC01": ("J", "KHG-J001"), "MC02": ("J", "KHG-J001"), "MC03": ("J", "KHG-J003"), "MC04": ("J", "KHG-J004"),
    "MC05": ("J", "KHG-J005"), "MC06": ("H", "KHG-H001"), "MC07": ("H", "KHG-H002"), "MC08": ("H", "KHG-H002"),
    "MC09": ("H", "KHG-H002"), "MC10": ("H", "KHG-H003"), "MC11": ("H", "KHG-H003"), "MC12": ("H", "KHG-H003"),
    "MC13": ("H", "KHG-H004"), "MC14": ("H", "KHG-H005"), "MC15": ("H", "KHG-H006"), "MC16": ("H", "KHG-H007"),
    "MC17": ("H", "KHG-H007"), "MC18": ("H", "KHG-H007"), "MC19": ("H", "KHG-H008"), "MC20": ("P", "KHG-P001"),
    "MC21": ("P", "KHG-P001"), "MC22": ("P", "KHG-P002"), "MC23": ("P", "KHG-P003"), "MC24": ("P", "KHG-P005"),
    "MC25": ("P", "KHG-P006"), "MC26": ("P", "KHG-P006"), "MC27": ("P", "KHG-P014"), "MC28": ("P", "KHG-P007"),
    "MC29": ("P", "KHG-P008"), "MC30": ("P", "KHG-P010"), "MC31": ("P", "KHG-P011"), "MC32": ("P", "KHG-P012"),
    "MC33": ("P", "KHG-P013"), "MC34": ("P", "KHG-P014"), "MC35": ("P", "KHG-P004"), "MC36": ("P", "KHG-P004"),
    "MC37": ("P", "KHG-P009"), "MC38": ("P", "KHG-P015"), "MC39": ("D (decode)", "KHG-D001"), "MC40": ("D (decode)", "KHG-D001"),
    "MC41": ("D (decode)", "KHG-D002"), "MC42": ("D (decode)", "KHG-D003"), "MC43": ("D (decode)", "KHG-D005"), "MC44": ("D (decode)", "KHG-D009"),
    "MC45": ("S (at decode)", "KHG-S016"), "MC46": ("D", "KHG-D002"), "MC47": ("C", "KHG-C001"), "MC48": ("C", "KHG-C002"),
    "MC49": ("C", "KHG-C003"), "MC50": ("C", "KHG-C004"), "MC51": ("C", "KHG-C004"), "MC52": ("C", "KHG-C005"),
    "MC53": ("C", "KHG-C006"), "MC54": ("C", "KHG-C007"), "MC55": ("C", "KHG-C008"), "MC56": ("C", "KHG-C007"),
    "MC57": ("C", "KHG-C009"), "MC58": ("S", "KHG-S001"), "MC59": ("S", "KHG-S002"), "MC60": ("S", "KHG-S003"),
    "MC61": ("S", "KHG-S004"), "MC62": ("S", "KHG-S005"), "MC63": ("S", "KHG-S005"), "MC64": ("S", "KHG-S006"),
    "MC65": ("S", "KHG-S006"), "MC66": ("S", "KHG-S007"), "MC67": ("S", "KHG-S005"), "MC68": ("S", "KHG-S009"),
    "MC69": ("S", "KHG-S010"), "MC70": ("S", "KHG-S010"), "MC71": ("S", "KHG-S011"), "MC72": ("S", "KHG-S013"),
    "MC73": ("S", "KHG-S014"), "MC74": ("S", "KHG-S015"), "MC75": ("S", "KHG-S015"), "MC76": ("S", "KHG-S018"),
    "MC77": ("S", "KHG-S019"), "MC78": ("S", "KHG-S020"), "MC79": ("S", "KHG-S022"), "MC80": ("S", "KHG-S023"),
    "MC81": ("S", "KHG-S023"), "MC82": ("S", "KHG-S025"), "MC83": ("S", "KHG-S005"), "MC84": ("D", "KHG-D008"),
    "MC85": ("D", "KHG-D010"), "MC86": ("D", "KHG-D012"), "MC87": ("D", "KHG-D011"), "MC88": ("D", "KHG-D016"),
    "MC89": ("D", "KHG-D015"), "MC90": ("D", "KHG-D017"), "MC91": ("D", "KHG-D002"), "MC92": ("D", "KHG-D007"),
    "MC93": ("M", "KHG-M001"), "MC94": ("M", "KHG-M002"), "MC95": ("M", "KHG-M003"), "MC96": ("M", "KHG-M003"),
    "MC97": ("M", "KHG-M004"), "MC98": ("M", "KHG-M006"), "MC99": ("M", "KHG-M005"), "MC100": ("M", "KHG-M014"),
    "MC101": ("M", "KHG-M007"), "MC102": ("M", "KHG-M008"), "MC103": ("M", "KHG-M011"), "MC104": ("Q", "KHG-Q001"),
    "MC105": ("Q", "KHG-Q002"), "MC106": ("Q", "KHG-Q003"), "MC107": ("Q", "KHG-Q004"), "MC108": ("Q", "KHG-Q005"),
}

# run-layer names -> the layer column of the design's table (§8.3)
FAMILY = {"J": {"J"}, "H": {"H"}, "P": {"P"}, "D(decode)": {"D (decode)", "S (at decode)"}, "C": {"C"},
          "S/D": {"S", "D"}, "S": {"S"}, "M(json)": {"M"}, "M(sem)": {"M"}, "Q": {"Q"}, "Q(fold)": {"Q"}}

if __name__ == "__main__":
    rows, bad = [], 0
    for cid, desc, kind, x in POSITIVE + CASES + QUEUE_CASES:
        run = {"hif": run_hif, "c1": run_c1, "schema": run_schema, "queue": run_queue}[kind]
        layer, codes, msg = run(x)
        if cid.startswith("OK"):
            good, want = layer is None, ("-", "-")
        else:
            want = EXPECTED[cid]
            good = layer is not None and want[0] in FAMILY[layer] and want[1] in codes
        bad += not good
        first = codes[0] if codes else "-"
        rows.append({"id": cid, "description": desc, "layer": layer or "-", "codes": sorted(set(codes)),
                     "expected_layer": want[0], "expected_code": want[1], "ok": good, "first": msg})
        print(f"{'  ' if good else '!!'} {cid:5} {layer or 'accepted':10} {first:9} want {want[1]:9} "
              f"{'+' + str(len(set(codes)) - 1) if len(set(codes)) > 1 else '  '} {desc[:62]:62} | {msg[:110]}")
    n = len(CASES) + len(QUEUE_CASES)
    missing = sorted(set(EXPECTED) - {c[0] for c in CASES + QUEUE_CASES})
    print(f"cases: {n} negative + {len(POSITIVE)} positive; expected codes without a case: {missing or 'none'}")
    cov = khg_codes.coverage()
    print("code coverage (constraints; uncovered):", {k: (v[0], len(v[1])) for k, v in cov.items()})
    bad += sum(len(v[1]) for v in cov.values())
    print("FAILED EXPECTATIONS:", bad)
    json.dump(rows, open(HERE / "malformed-results.json", "w"), ensure_ascii=False, indent=1)
