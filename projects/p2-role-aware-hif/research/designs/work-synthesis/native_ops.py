"""The native-operation table of DESIGN §5, executed: each XGI and HyperNetX operation is applied to the gate fixture
(the undirected full export, or the directed slice for DiHypergraph operations) and exported with strict=True.
Outcome classes: exact | removals (exports; records of edges removed whole are dropped and reported) | moved (exports;
an injective rename) | needs-label (raises until Bundle.label gives each new membership its record) | raises (partial
fact or non-injective move) | unsupported (the library raises, or ids are rewritten).
usage: native_ops.py <examples dir>  (venv-libs). Prints one line per operation and writes <examples>/native-ops.json."""
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
FULL = json.loads((EX / "fixture.hif.json").read_text(encoding="utf-8"))
SLICE = json.loads((EX / "fixture.directed-slice.hif.json").read_text(encoding="utf-8"))
rows = []


def outcome(bundle, original, expect):
    try:
        out = L.export_xgi(bundle) if bundle.lib == "xgi" else L.export_hnx(bundle)
    except L.LoaderError as e:
        rep = e.report
        why = "partial" if rep.get("stale") else "unlabelled" if rep.get("unlabelled") else "moved to one node"
        return f"raises ({why})", None
    rep = bundle.report
    if K.cjson(out) == K.cjson(original):
        return "exact", out
    if rep["moved"]:
        return "moved", out
    if rep["dropped_records"] or rep["dropped_nodes"] or rep["dropped_edges"]:
        return "removals", out
    return "exports (changed)", out


def run(lib, name, doc, op, expect, relabel=None):
    import xgi  # noqa: F401
    b = (L.load_xgi if lib == "xgi" else L.load_hnx)(copy.deepcopy(doc))
    try:
        b2 = op(b)
    except Exception as e:  # noqa: BLE001
        res, out = f"unsupported ({type(e).__name__})", None
    else:
        res, out = outcome(b2, doc, expect)
        if res.startswith("raises (unlabelled)") and relabel:
            relabel(b2)
            res2, out = outcome(b2, doc, expect)
            res = f"needs-label -> {res2}"
    ok = res.split(" ")[0] == expect.split(" ")[0]
    rows.append({"library": lib, "operation": name, "file": "slice" if doc is SLICE else "full", "expected": expect,
                 "outcome": res, "ok": ok, "report": {k: len(v) for k, v in (b.report or {}).items() if v}})
    print(f"{'PASS' if ok else 'FAIL'} {lib:4} {name:58} {res:40} (expected {expect})")


with E.no_network():
    L.set_schema_dir(EX / "schemas")
    import xgi
    # ---------------------------------------------------------------- XGI
    def x_copy(b):
        return b.derive(b.graph.copy())

    def x_weak(b):
        b.graph.remove_node("ex:HeLa")
        return b

    def x_strong(b):
        b.graph.remove_node("ex:HeLa", strong=True)
        return b

    def x_add_edge(b):
        b.graph.add_edge({"ex:TP53", "ex:HeLa"}, idx="f:new")
        b.graph.set_edge_attributes({"f:new": {"relation": "regulates", "khg-status": "asserted"}})
        return b

    def x_add_edge_label(b):
        b.label("f:new", "ex:TP53", role="regulator", bid="b1", direction="tail")
        b.label("f:new", "ex:HeLa", role="context", bid="b2", direction="tail")

    def x_add_member(b):
        b.graph.add_node_to_edge("f:reg-1", "ex:Paris")
        return b

    def x_add_member_label(b):
        b.label("f:reg-1", "ex:Paris", role="context", bid="b4", direction="tail")

    def x_readd(b):
        b.graph.remove_node_from_edge("f:reg-1", "ex:HeLa")
        b.graph.add_node_to_edge("f:reg-1", "ex:HeLa")
        return b

    def x_sub(b):
        return b.derive(xgi.subhypergraph(b.graph, nodes=[n for n in b.graph.nodes if n != "ex:HeLa"]))

    def x_relabel(b):
        return b.derive(xgi.convert_labels_to_integers(b.graph))

    def x_dual(b):
        return b.derive(b.graph.dual())

    def x_cleanup(b):
        b.graph.cleanup()
        return b

    run("xgi", "copy() then derive", FULL, x_copy, "exact")
    run("xgi", "remove_node('ex:HeLa') (weak: f:reg-1 survives)", FULL, x_weak, "raises (partial)")
    run("xgi", "remove_node('ex:HeLa', strong=True) (f:reg-1 removed whole)", FULL, x_strong, "removals")
    run("xgi", "add_edge + set_edge_attributes, then label", FULL, x_add_edge, "needs-label", x_add_edge_label)
    run("xgi", "add_node_to_edge('f:reg-1', 'ex:Paris'), then label", FULL, x_add_member, "needs-label", x_add_member_label)
    run("xgi", "remove_node_from_edge + add_node_to_edge (same pair)", FULL, x_readd, "exact")
    run("xgi", "subhypergraph(all nodes but ex:HeLa) then derive", FULL, x_sub, "removals")
    run("xgi", "subhypergraph on a DiHypergraph", SLICE, x_sub, "unsupported")
    run("xgi", "convert_labels_to_integers", FULL, x_relabel, "raises (partial)")
    run("xgi", "dual()", FULL, x_dual, "raises (partial)")
    run("xgi", "cleanup() (relabels to integers by default)", FULL, x_cleanup, "raises")

    # ---------------------------------------------------------------- HyperNetX
    def h_clone(b):
        return b.derive(b.graph.clone())

    def h_restrict_edges(b):
        return b.derive(b.graph.restrict_to_edges([e for e in b.graph.edges if e != "f:reg-1"]))

    def h_remove_edges(b):
        b.graph.remove_edges(["f:reg-1"])
        return b

    def h_remove_inc(b):
        b.graph.remove_incidences([("f:reg-1", "ex:HeLa")])
        return b

    def h_rename(b):
        b.graph.rename(nodes={"ex:HeLa": "ex:HeLa-cells"})
        return b

    def h_add_inc(b):
        b.graph.add_incidence("f:reg-1", "ex:Paris", direction="tail")
        return b

    def h_add_inc_label(b):
        b.label("f:reg-1", "ex:Paris", role="context", bid="b4")

    def h_restrict_nodes(b):
        return b.derive(b.graph.restrict_to_nodes([n for n in b.graph.nodes if n != "ex:HeLa"]))

    def h_collapse(b):
        r = b.graph.collapse_nodes()
        return b.derive(r[0] if isinstance(r, tuple) else r)

    def h_sum(b):
        other = L.load_hnx(copy.deepcopy(SLICE))
        return b.derive(b.graph.sum(other.graph))

    run("hnx", "clone() then derive (HyperNetX drops the isolated ex:Mazarin)", FULL, h_clone, "removals")
    run("hnx", "restrict_to_edges(all but f:reg-1) then derive", FULL, h_restrict_edges, "removals")
    run("hnx", "remove_edges(['f:reg-1'])", FULL, h_remove_edges, "removals")
    run("hnx", "remove_incidences([('f:reg-1', 'ex:HeLa')])", FULL, h_remove_inc, "raises (partial)")
    run("hnx", "rename(nodes={'ex:HeLa': 'ex:HeLa-cells'})", FULL, h_rename, "moved")
    run("hnx", "add_incidence('f:reg-1', 'ex:Paris'), then label", FULL, h_add_inc, "needs-label", h_add_inc_label)
    run("hnx", "restrict_to_nodes(all but ex:HeLa) then derive", FULL, h_restrict_nodes, "raises (partial)")
    run("hnx", "collapse_nodes() then derive", FULL, h_collapse, "raises")
    run("hnx", "sum(slice) then derive (the slice is a subset; the isolated node is lost)", FULL, h_sum, "removals")

(EX / "native-ops.json").write_text(json.dumps({"format": "khg-native-ops/1.0.0", "strict": True, "rows": rows},
                                               ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(sum(r["ok"] for r in rows), "of", len(rows), "as expected")
