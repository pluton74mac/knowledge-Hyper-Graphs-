"""Ruling Q8: the external-solver schedule, on a fixture, with a scripted stand-in for BalancedGo (no binaries
needed). The stand-in answers ``-width k`` like a solver on p6-adler (hw 3): "yes" with a real width-3 HD (in the
neutral ids) for k >= 3, "no" below; a configuration file can make it hang instead, per k and per mode (with or
without the preprocessing flags ``-t -h -g -heuristic 1``). Every call is appended to a call log."""
from __future__ import annotations

import json
import stat
import sys
import time

import pytest

from helpers import FIXTURES
from khg_width import check, validate
from khg_width.acyclicity import classify
from khg_width.check import _Run
from khg_width.decomposition import single_node
from khg_width.exact import hd_search
from khg_width.hypergraph import hypergraph
from khg_width.solvers.discovery import SolverInfo

FAKE = r'''#!{python}
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(here, "fake.json")))
a = sys.argv[1:]
k = int(a[a.index("-width") + 1])
flags = "-t" in a
out = a[a.index("-json") + 1] if "-json" in a else None
with open(os.path.join(here, "calls.log"), "a") as fh:
    fh.write(json.dumps({{"k": k, "flags": flags}}) + "\n")
if k in cfg.get("hang_flags" if flags else "hang_plain", []):
    time.sleep(60)
print("Used algorithm: DetK @")
print("Result ( ran with K = %d )" % k)
if k in cfg.get("invalid_plain" if not flags else "invalid_flags", []):
    # a decomposition BalancedGo found but its own check rejected (review finding F1)
    print(" Bag: {{V0, V1}}\n Cover: {{R0}}\n Children: 1\n [\n Bag: {{V1, V2}}\n Cover: {{R1}}\n ]")
    print("Edge  R2  isn't covered")
    print("Width:  %d" % k)
    print("Correct:  false")
elif k in cfg.get("ghd_flags" if flags else "ghd_plain", []):
    # a GHD that is not an HD, reported as correct with the special-condition warning
    if out:
        with open(out, "w") as fh:
            fh.write(open(os.path.join(here, "ghd.json")).read())
    print("Width:  2")
    print("SCV found!. Not a valid hypertree decomposition!")
    print("Correct:  true")
elif k >= cfg["hw"]:
    if out:
        with open(out, "w") as fh:
            fh.write(open(os.path.join(here, "hd.json")).read())
    print("Width:  %d" % cfg["hw"])
    print("Correct:  true")
else:
    print("Width:  0")
    print("Correct:  false")
'''


def to_balancedgo(d, neutral) -> dict:
    nodes = d.walk()
    out = [{"Bag": [neutral.roles[v] for v in sorted(n.bag)], "Cover": [neutral.relations[g] for g in n.guard],
            "Children": []} for n, _ in nodes]
    for i, (_, p) in enumerate(nodes):
        if p is not None:
            out[p]["Children"].append(out[i])
    return {"Root": out[0]}


@pytest.fixture
def adler(tmp_path):
    h = hypergraph(str(FIXTURES / "p6-adler.relation-schema.json"))
    hd = hd_search(h.distinct(), 3)
    assert validate(h, hd, kind="hd").ok
    (tmp_path / "hd.json").write_text(json.dumps(to_balancedgo(hd, h.distinct().neutral)))
    ghd = check(str(FIXTURES / "p6-adler.relation-schema.json"), solver="python").widths["ghw"].certificate
    assert validate(h, ghd, kind="ghd").ok and not validate(h, ghd, kind="hd").ok  # width 2, fails (4)
    (tmp_path / "ghd.json").write_text(json.dumps(to_balancedgo(ghd, h.distinct().neutral)))
    fake = tmp_path / "BalancedGo"
    fake.write_text(FAKE.format(python=sys.executable))
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    return h, tmp_path


def run(h, tmp, cfg: dict, *, attempt: float = 5.0, budget: float = 60.0, ghw_upper: int | None = None) -> _Run:
    (tmp / "fake.json").write_text(json.dumps({"hw": 3, **cfg}))
    info = SolverInfo(name="balancedgo", path=str(tmp / "BalancedGo"), commit="fake", sha256="0" * 64, how="test")
    r = _Run(h, classify(h), time_limit=60, solver="balancedgo", seed=20260924, tools={"balancedgo": info},
             solver_attempt=attempt, solver_budget=budget)
    if ghw_upper is not None:  # a ghw certificate already in hand (the core's GHD, width 2)
        g = check(str(FIXTURES / "p6-adler.relation-schema.json"), solver="python").widths["ghw"]
        assert g.upper == ghw_upper
        r.b["ghw"].offer_upper(g.upper, "dp", g.certificate, "ghd", g.validation)
    r.b["hw"].raise_lower(2, "cyclic")
    r.offer("hw", single_node(h.distinct()), "trivial")  # [2, 8]: the widest interval
    claims: list = []
    r._bisect(["balancedgo"], "balancedgo", "balancedgo", claims)
    r._resolve(claims)
    return r


def calls(tmp) -> list[tuple[int, bool]]:
    log = tmp / "calls.log"
    return [(c["k"], c["flags"]) for c in map(json.loads, log.read_text().splitlines())] if log.exists() else []


def test_bisection_closes_on_hw(adler):
    """[2, 8] -> k = 5 with preprocessing finds the width-3 HD (upper 3) -> k = 2 with preprocessing says no
    (not a bound) -> k = 2 without says no (lower 3). The confirmation at hw - 1 is not repeated."""
    h, tmp = adler
    r = run(h, tmp, {})
    assert calls(tmp) == [(5, True), (2, True), (2, False)]
    got = [(a["k"], a["flags"], a["outcome"], a["validated_width"], a["used_as"]) for a in r.attempts]
    assert got == [(5, True, "yes", 3, "upper bound 3 (validated HD)"),
                   (2, True, "no", None, "none: a run with preprocessing refutes nothing"),
                   (2, False, "no", None, "lower bound 3")]
    b = r.b["hw"]
    assert (b.lower, b.upper, b.lower_method, b.upper_method) == (3, 3, "refutation:balancedgo", "balancedgo")
    assert validate(h, b.certificate, kind="hd").ok
    assert r.disagreements == []


def test_preprocessed_no_is_not_a_lower_bound(adler):
    """Ruling Q2: when the run without preprocessing cannot decide k = 2, the "no" of the preprocessed run leaves
    the lower bound at 2."""
    h, tmp = adler
    r = run(h, tmp, {"hang_plain": [2]}, attempt=1.0)
    assert calls(tmp) == [(5, True), (2, True), (2, False)]
    assert [a["outcome"] for a in r.attempts] == ["yes", "no", "timeout"]
    assert (r.b["hw"].lower, r.b["hw"].upper) == (2, 3)
    assert not r.b["hw"].exact


def test_undecided_k_moves_up(adler):
    """A k that neither run decides is skipped and the search continues above it."""
    h, tmp = adler
    r = run(h, tmp, {"hw": 4, "hang_flags": [5], "hang_plain": [5]}, attempt=1.0)
    # [2, 8]: k=5 hangs twice -> undecided, next k = (6 + 8) // 2 = 7 -> found (width 3 from hd.json) -> [2, 3]
    assert calls(tmp)[:3] == [(5, True), (5, False), (7, True)]
    assert r.b["hw"].upper == 3


def test_budget_caps_all_attempts(adler):
    """Every attempt stops at the attempt limit, and the row's attempts together stay within the budget."""
    h, tmp = adler
    t0 = time.monotonic()
    r = run(h, tmp, {"hang_flags": list(range(1, 9)), "hang_plain": list(range(1, 9))}, attempt=0.4, budget=1.0)
    wall = time.monotonic() - t0
    total = sum(a["seconds"] for a in r.attempts)
    assert all(a["outcome"] == "timeout" for a in r.attempts)
    assert all(a["limit"] <= 0.4 for a in r.attempts)
    assert 2 <= len(r.attempts) <= 4
    assert total <= 1.0 + 0.15 * len(r.attempts)  # process start and kill overhead
    assert wall < 10
    assert (r.b["hw"].lower, r.b["hw"].upper) == (2, 8)


def test_self_rejected_decomposition_is_not_a_refutation(adler):
    """F1: "Correct: false" with a non-empty tree and the tool's "Edge ... isn't covered" is a decomposition the
    tool found and rejected, not a "no": outcome ``invalid``, logged as a disagreement, never a bound."""
    h, tmp = adler
    r = run(h, tmp, {"invalid_plain": [2]})
    assert calls(tmp) == [(5, True), (2, True), (2, False)]
    last = r.attempts[-1]
    assert (last["k"], last["flags"], last["outcome"], last["validated_width"]) == (2, False, "invalid", None)
    assert last["used_as"].startswith("none")
    assert (r.b["hw"].lower, r.b["hw"].upper) == (2, 3) and not r.b["hw"].exact
    inv = [d for d in r.disagreements if d["kind"] == "solver-invalid"]
    assert len(inv) == 1 and inv[0]["k"] == 2 and inv[0]["check_failures"] == ["Edge  R2  isn't covered"]


def test_demoted_attempt_label_and_hd_repair(adler):
    """F8 and ruling Q11: a yes whose decomposition fails the special condition is demoted; its label says what it
    was used for (here nothing for ghw, which already has a certificate of width 2), and the demoted GHD goes
    through hd-repair, whose validated HD is offered as an hw upper bound."""
    h, tmp = adler
    r = run(h, tmp, {"ghd_flags": [2]}, ghw_upper=2)
    got = [(a["k"], a["flags"], a["outcome"]) for a in r.attempts]
    assert got == [(5, True, "yes"), (2, True, "yes"), (2, False, "no")]
    demoted = r.attempts[1]
    assert demoted["validated_width"] is None
    assert demoted["used_as"].startswith("no ghw bound (demoted HD of width 2; ghw <= 2 already)")
    assert "hd-repair" in demoted["used_as"]
    dem = [d for d in r.disagreements if d["kind"] == "demotion"]
    assert len(dem) == 1 and dem[0]["ghw_bound_used"] is False and dem[0]["repaired_hd_width"] is not None
    assert any(s["method"] == "hd-repair" and "GHD demoted from balancedgo" in s.get("detail", "")
               for s in r.log.steps)
    assert (r.b["hw"].lower, r.b["hw"].upper) == (3, 3)


def test_demoted_ghd_can_lower_ghw_and_hw(adler):
    """Without a ghw certificate in hand, the demoted GHD becomes ghw's upper bound; hd-repair of it lowers hw's
    upper bound when it beats the one in hand (here the trivial width 8)."""
    h, tmp = adler
    r = run(h, tmp, {"hw": 9, "ghd_flags": [5]})  # never finds an HD itself; its k = 5 answer is the GHD
    first = r.attempts[0]
    assert (first["k"], first["flags"], first["outcome"]) == (5, True, "yes")
    assert first["used_as"].startswith("ghw upper bound 2 (demoted HD)")
    assert r.b["ghw"].upper == 2 and r.b["ghw"].upper_method == "balancedgo-demoted"
    assert r.b["hw"].upper < 8 and r.b["hw"].upper_method == "hd-repair:balancedgo-demoted"
    assert validate(h, r.b["hw"].certificate, kind="hd").ok
