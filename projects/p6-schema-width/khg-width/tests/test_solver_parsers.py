"""G2: solver output parsing (DESIGN §3.5, §3.6) on recorded outputs, without the binaries.

Recorded: BalancedGo and log-k-decomp on ``b_triangle`` and ``adler`` (built by scripts/build-solvers.sh at the
pinned commits), and R01's recorded runs ``NewSystem4`` (log-k-decomp with the preprocessing flags, which printed
"SCV found!") and ``bridge_99`` (truncated by R01's probe after the width line).
"""
from __future__ import annotations

import re
from fractions import Fraction

from helpers import FIXTURES, RECORDED
from khg_width import Decomposition, Hypergraph, classify, validate
from khg_width.check import _Run
from khg_width.hypergraph import hypergraph
from khg_width.solvers.parsers import parse_gml, parse_json, parse_stdout
from khg_width.solvers.runner import Outcome

ADLER = str(FIXTURES / "p6-adler.relation-schema.json")


def read(name: str) -> str:
    return (RECORDED / name).read_text(encoding="utf-8")


def shape(tree: dict) -> tuple:
    return (tuple(sorted(tree["bag"])), tuple(sorted(tree["cover"])), tuple(shape(c) for c in tree["children"]))


def test_balancedgo_yes_and_no():
    p = parse_stdout(read("b_triangle.balancedgo.width2.txt"))
    assert (p.k, p.width, p.correct, p.scv, p.algorithm) == (2, 2, True, False, "DetK")
    assert p.tree == {"bag": ["a", "b"], "cover": ["E1"],
                      "children": [{"bag": ["a", "b", "c"], "cover": ["E1", "E2"], "children": []}]}
    assert shape(parse_json(read("b_triangle.balancedgo.json"))) == shape(p.tree)
    q = parse_stdout(read("b_triangle.balancedgo.width1.txt"))
    assert (q.k, q.width, q.correct, q.tree) == (1, 0, False, None)


def test_logk_gml_and_stdout_agree():
    p = parse_stdout(read("adler.logk.width3.txt"))
    g = parse_gml(read("adler.logk.gml"))
    assert (p.k, p.width, p.correct, p.algorithm) == (3, 3, True, "LogKHybrid")
    assert shape(g) == shape(p.tree)
    assert sorted(g["cover"]) == ["E1", "E2", "E7"]
    h = hypergraph(ADLER)
    d = Decomposition.from_json(g)
    v = validate(h, d, kind="hd")
    assert v.ok and v.width == 3


def test_balancedgo_exact_json_validates():
    p = parse_stdout(read("adler.balancedgo.exact.txt"))
    assert p.k == 3 and p.correct is True
    d = Decomposition.from_json(parse_json(read("adler.balancedgo.json")))
    assert d.size() == 7
    v = validate(hypergraph(ADLER), d, kind="hd")
    assert v.ok and v.width == 3


def test_r01_recorded_outputs():
    scv = parse_stdout(read("r01-NewSystem4.logk_width4_flags.txt"))
    assert scv.scv is True and scv.correct is True and scv.width == 4
    br = parse_stdout(read("r01-bridge_99.balgo_detk_width2.txt"))
    # the probe kept the last 40 lines: the summary survives, the tree's head was cut, so no tree is returned
    assert br.width == 2 and br.correct is True and br.tree is None


def run_for(h: Hypergraph) -> _Run:
    return _Run(h, classify(h), time_limit=5.0, solver="python", seed=20260924, tools={})


def outcome(tree: dict | None, *, scv: bool = False, echoed: int | None = None, k: int = 2) -> Outcome:
    return Outcome(tool="balancedgo", cmd=("BalancedGo", "-graph", "h.hg", "-width", str(k), "-det"), k=k,
                   exact_mode=False, flags=False, outcome="yes", k_reported=k, width=k, scv=scv, edges_echoed=echoed,
                   tree=tree, seconds=0.01, returncode=0, stdout_tail="", stderr_tail="")


def to_neutral(h: Hypergraph, d: Decomposition) -> dict:
    n = h.distinct().neutral
    nodes = d.walk()
    trees = [{"bag": [n.roles[v] for v in sorted(x.bag)], "cover": [n.relations[g] for g in x.guard], "children": []}
             for x, _ in nodes]
    for i, (_, p) in enumerate(nodes):
        if p is not None:
            trees[p]["children"].append(trees[i])
    return trees[0]


def test_scv_demotes_to_ghw():
    """A 'yes' whose decomposition fails the special condition (or prints 'SCV found!') is demoted to a ghw bound
    and logged; it never becomes an hw bound."""
    h = hypergraph(ADLER)
    from khg_width import check

    ghd = check(ADLER, solver="python").widths["ghw"].certificate  # width 2, fails (4)
    r = run_for(h)
    claims: list = []
    got = r._take(outcome(to_neutral(h, ghd), scv=True), claims)
    assert got is None  # never an hw bound as it is ...
    assert r.b["ghw"].upper == 2 and r.b["ghw"].upper_method == "balancedgo-demoted"
    # ... but ruling Q11: hd-repair turns it into a validated HD, offered as an hw upper bound
    assert r.b["hw"].upper_method == "hd-repair:balancedgo-demoted"
    assert validate(h, r.b["hw"].certificate, kind="hd").ok and r.b["hw"].upper >= 3
    dem = [d for d in r.disagreements if d["kind"] == "demotion"]
    assert len(dem) == 1 and dem[0]["scv_printed"] is True and dem[0]["ghd_ok"] is True
    assert dem[0]["ghw_bound_used"] is True and dem[0]["hw_bound_used"] is True
    assert any(f.startswith("(4)") for f in dem[0]["failures"])


def test_valid_yes_is_an_hw_bound_and_neutral_ids_roundtrip():
    h = hypergraph(ADLER)
    n = h.distinct().neutral
    # the neutral text names every relation R<i> and role V<j>, and maps back
    edges = dict(re.findall(r"(R\d+) \(([^)]*)\)", n.text))
    assert len(edges) == len(h.distinct())
    back = {n.relation_names[r]: {n.role_names[v.strip()] for v in body.split(",")} for r, body in edges.items()}
    assert back == {k: set(v) for k, v in h.distinct().as_dict().items()}
    assert not set(n.relations.values()) & set(n.roles.values())  # BalancedGo panics on a shared name
    hd = Decomposition.from_json(parse_gml(read("adler.logk.gml")))
    r = run_for(h)
    claims: list = []
    assert r._take(outcome(to_neutral(h, hd), k=3), claims) == 3
    assert r.b["hw"].upper == 3 and r.b["hw"].upper_method == "balancedgo"
    assert r.b["fhw"].upper is not None and r.b["fhw"].upper <= Fraction(3)  # ImproveHD


def test_echoed_edge_count_mismatch_is_an_error():
    h = hypergraph(ADLER)
    r = run_for(h)
    claims: list = []
    assert r._take(outcome({"bag": [], "cover": [], "children": []}, echoed=7), claims) is None
    mis = [d for d in r.disagreements if d["kind"] == "misparse"]
    assert mis and mis[0]["edges_echoed"] == 7 and mis[0]["edges"] == 8
    assert parse_stdout('{"#hyperedges": 7}\nWidth:  1\n').edges_echoed == 7


def test_refutation_contradicted_is_dropped():
    """A sound refutation at k contradicted by a validated HD of width <= k is dropped from the lower bound and
    logged as a disagreement."""
    h = Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"]})
    r = run_for(h)
    r.b["hw"].raise_lower(2, "cyclic")
    hd = Decomposition(frozenset("abc"), {"E1": 1, "E2": 1})
    r.offer("hw", hd, "test")
    claims = [{"tool": "logk", "k": 2, "sound": True, "outcome": "no", "run": {"cmd": ["log-k-decomp"]}},
              {"tool": "python", "hd": 2}]
    r._resolve(claims)
    assert r.b["hw"].lower == 2 and r.b["hw"].lower_method == "cyclic"
    d = [x for x in r.disagreements if x["kind"] == "refutation-contradicted"]
    assert len(d) == 1 and d[0]["tool"] == "logk" and d[0]["k"] == 2 and d[0]["hd_width"] == 2
