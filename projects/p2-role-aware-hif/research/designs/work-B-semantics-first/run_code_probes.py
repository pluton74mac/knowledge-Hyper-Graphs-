"""Registry probes (design §8.2): one input per registry clause that the gate list does not already
exercise; each must report the clause's code. Complements run_malformed.py and khg_codes.coverage()."""
import copy, json, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import khg_codes

HD = json.loads((HERE / "fixture-directed.hif.json").read_text()); C1 = json.loads((HERE / "fixture-directed.khg.json").read_text())
SD = json.loads((HERE / "p2-gate.schema.json").read_text()); QX = json.loads((HERE / "queue-examples.json").read_text())


def codes(layer, x):
    return sorted({r[0] for r in khg_codes.report(layer, x)})


def mut(base, f):
    d = copy.deepcopy(base); f(d); return d


def rec(d, i):
    return next(r for r in d["records"] if r.get("id") == i)


def lit_node(d):
    return next(n for n in d["nodes"] if n["attrs"]["khg:kind"] == "literal")


PROBES = [
    ("P001 no nodes", "P", mut(HD, lambda d: d.pop("nodes")), "KHG-P001"),
    ("P004 value node id without _:", "P", mut(HD, lambda d: lit_node(d).update({"node": "lit-9"})), "KHG-P004"),
    ("P005 incidence without attrs", "P", mut(HD, lambda d: d["incidences"][0].pop("attrs")), "KHG-P005"),
    ("P005 malformed khg:bid", "P", mut(HD, lambda d: d["incidences"][0]["attrs"].update({"khg:bid": "b 1"})), "KHG-P005"),
    ("P008 unknown khg-* metadata key", "P", mut(HD, lambda d: d["metadata"].update({"khg-foo": 1})), "KHG-P008"),
    ("P009 khg-schema-sha256 malformed", "P", mut(HD, lambda d: d["metadata"].update({"khg-schema-sha256": "abc"})), "KHG-P009"),
    ("P012 edge without attrs", "P", mut(HD, lambda d: d["edges"][0].pop("attrs")), "KHG-P012"),
    ("P012 khg:evidence not an array", "P", mut(HD, lambda d: d["edges"][0]["attrs"].update({"khg:evidence": {}})), "KHG-P012"),
    ("P013 node without attrs", "P", mut(HD, lambda d: d["nodes"][0].pop("attrs")), "KHG-P013"),
    ("P013 literal node without khg:literal", "P", mut(HD, lambda d: lit_node(d)["attrs"].pop("khg:literal")), "KHG-P013"),
    ("H004 metadata not an object", "H", mut(HD, lambda d: d.update({"metadata": []})), "KHG-H004"),
    ("H009 weight not a number", "H", mut(HD, lambda d: d["incidences"][0].update({"weight": "1"})), "KHG-H009"),
    ("H009 incidences not an array", "H", mut(HD, lambda d: d.update({"incidences": {}})), "KHG-H009"),
    ("C001 value with an unknown kind key", "C", mut(C1, lambda d: rec(d, "f:reg-1")["bindings"][0].update({"value": {"thing": 1}})), "KHG-C001"),
    ("C004 time literal without precision", "C", mut(C1, lambda d: rec(d, "f:king-14")["bindings"][2]["value"]["literal"].pop("precision")), "KHG-C004"),
    ("C006 abandoned goal without closed_reason", "C", mut(C1, lambda d: next(r for r in d["records"] if r["kind"] == "goal").update({"status": "abandoned"})), "KHG-C006"),
    ("C010 fact without bindings", "C", mut(C1, lambda d: rec(d, "f:reg-1").pop("bindings")), "KHG-C010"),
    ("C010 version 0", "C", mut(C1, lambda d: rec(d, "f:reg-1").update({"version": 0})), "KHG-C010"),
    ("C011 bad extension key", "C", mut(C1, lambda d: rec(d, "f:reg-1").update({"extensions": {"BAD KEY": 1}})), "KHG-C011"),
    ("C011 record id with a space", "C", mut(C1, lambda d: rec(d, "f:reg-1").update({"id": "f reg"})), "KHG-C011"),
    ("M007 time slot with max 2", "M", mut(SD, lambda d: next(u for r in d["relations"] if r["id"] == "position_held" for u in r["roles"] if u["slot"] == "time").update({"max": 2})), "KHG-M007"),
    ("M015 unknown field on a relation", "M", mut(SD, lambda d: d["relations"][0].update({"colour": "red"})), "KHG-M015"),
    ("M015 filler with two kinds", "M", mut(SD, lambda d: d["relations"][0]["roles"][0]["fillers"][0].update({"fact": ["x"]})), "KHG-M015"),
    ("Q001 extraction doc without doc_id", "Q", mut(QX["item"], lambda d: d["extraction"]["doc"].pop("doc_id")), "KHG-Q001"),
    ("Q001 extractor without version", "Q", mut(QX["item"], lambda d: d["extraction"]["extractor"].pop("version")), "KHG-Q001"),
    ("Q003 unknown record kind", "Q", dict(QX["item"], kind="queue_thing"), "KHG-Q003"),
    ("Q004 lint entry without outcome", "Q", mut(QX["log"][1], lambda d: d.pop("outcome")), "KHG-Q004"),
    ("Q008 verdict label unknown", "Q", dict(QX["verdict"], label="meh"), "KHG-Q008"),
]

if __name__ == "__main__":
    bad = 0
    for name, layer, x, want in PROBES:
        got = codes(layer, x)
        bad += want not in got
        print(f"{'  ' if want in got else '!!'} {name:44} {layer} {got}")
    print(f"registry probes: {len(PROBES)}; mismatches: {bad}")
    sys.exit(1 if bad else 0)
