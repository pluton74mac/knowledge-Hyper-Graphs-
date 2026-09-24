"""G2: the external solvers (DESIGN §3.5, §4.5). Tests marked ``solvers`` skip without both binaries
(scripts/build-solvers.sh); the discovery tests use fake binaries and always run."""
from __future__ import annotations

import json
import os
import stat
import time

import pytest

from helpers import FIXTURES, fixture_rows
from khg_width import Hypergraph, check, find_solvers
from khg_width.solvers import balancedgo, logk
from khg_width.solvers.discovery import default_dest

CYCLIC_ROWS = [r for r in fixture_rows() if r["class"] == "cyclic"]


# ------------------------------------------------------------------------------------------------ discovery
def fake_binary(path, text="#!/bin/sh\necho fake\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def test_discovery_order(tmp_path):
    dest = tmp_path / "dest"
    b = fake_binary(dest / "bin" / "BalancedGo")
    import hashlib

    sha = hashlib.sha256(b.read_bytes()).hexdigest()
    (dest / "solvers.json").write_text(json.dumps({"balancedgo": {"commit": "872c662c", "sha256": sha,
                                                                  "describe": "v1.7.2-2-g872c662"}}))
    pathdir = tmp_path / "pathbin"
    fake_binary(pathdir / "log-k-decomp")
    env = {"KHG_WIDTH_SOLVERS": str(dest), "PATH": str(pathdir), "XDG_CACHE_HOME": str(tmp_path / "cache")}
    found = find_solvers(env)
    assert found["balancedgo"].how == "KHG_WIDTH_SOLVERS" and found["balancedgo"].commit == "872c662c"
    assert found["balancedgo"].sha256 == sha
    assert found["logk"].how == "PATH" and found["logk"].commit == "unknown"
    # an explicit variable wins; one that points nowhere means "not found"
    other = fake_binary(tmp_path / "elsewhere" / "BalancedGo")
    env2 = dict(env, KHG_WIDTH_BALANCEDGO=str(other), KHG_WIDTH_LOGK=str(tmp_path / "nothing"))
    found2 = find_solvers(env2)
    assert found2["balancedgo"].how == "env:KHG_WIDTH_BALANCEDGO" and found2["balancedgo"].commit == "unknown"
    assert "logk" not in found2
    # the default DEST
    env3 = {"XDG_CACHE_HOME": str(tmp_path / "xdg"), "PATH": ""}
    fake_binary(default_dest(env3) / "bin" / "log-k-decomp")
    assert find_solvers(env3)["logk"].how == "default"
    # a binary whose sha256 differs from solvers.json does not inherit its commit
    (dest / "solvers.json").write_text(json.dumps({"balancedgo": {"commit": "872c662c", "sha256": "0" * 64}}))
    assert find_solvers(env)["balancedgo"].commit == "unknown"


def test_commands():
    cmd = balancedgo.command("BG", "h.hg", k=3, flags=True, json_out="o.json")
    assert cmd == ["BG", "-graph", "h.hg", "-width", "3", "-det", "-t", "-h", "-g", "-heuristic", "1", "-cpu", "2",
                   "-json", "o.json"]
    assert balancedgo.command("BG", "h.hg", k=None, exact=True)[:5] == ["BG", "-graph", "h.hg", "-exact", "-det"]
    assert logk.command("LK", "h.hg", k=2, gml_out="o.gml") == ["LK", "-graph", "h.hg", "-width", "2", "-cpu", "2",
                                                                 "-gml", "o.gml"]


# ------------------------------------------------------------------------------------------------ live
@pytest.mark.solvers
@pytest.mark.parametrize("row", CYCLIC_ROWS, ids=[f"{r['fixture']}-{r['slots']}" for r in CYCLIC_ROWS])
@pytest.mark.parametrize("solver", ["balancedgo", "logk", "auto"])
def test_tools_agree_with_python(row, solver):
    """Each mode reaches the fixture's hw with no disagreement. ``balancedgo`` and ``logk`` use only their tool;
    ``auto`` lets Python decide the small fixtures and log-k-decomp confirm the refutation at hw - 1."""
    rep = check(row["path"], slots=row["slot_tuple"], solver=solver, time_limit=60)
    hw = rep.widths["hw"]
    want = int(row["hw"])
    assert hw.exact and hw.value == want
    assert rep.disagreements == []
    tools = {a["tool"] for a in rep.solver_attempts}
    allowed = {"auto": {"balancedgo", "logk"}}.get(solver, {solver})
    assert tools and tools <= allowed
    confirm = "logk" if solver == "auto" else solver
    assert any(a["tool"] == confirm and a["k"] == want - 1 and not a["flags"] and a["outcome"] == "no"
               for a in rep.solver_attempts)
    for a in rep.solver_attempts:
        assert set(a) >= {"k", "tool", "flags", "seconds", "outcome", "used_as", "cmd"}
        assert ("-t" in a["cmd"]) == a["flags"] and "-cpu" in a["cmd"]
    assert rep.solver_budget["used_seconds"] <= rep.solver_budget["budget_seconds"]
    assert rep.tools[confirm]["sha256"]


@pytest.mark.solvers
def test_live_bisection_from_the_trivial_bound():
    """p6-qualifier-k5 (hw 3) from [2, 10], the trivial one-node HD: BalancedGo with preprocessing at the midpoint
    6 finds a decomposition that validates on H, and the bisection closes on 3 with a refutation without
    preprocessing at 2 (ruling Q8)."""
    from khg_width.acyclicity import classify
    from khg_width.check import _Run
    from khg_width.decomposition import single_node
    from khg_width.hypergraph import hypergraph

    h = hypergraph(str(FIXTURES / "p6-qualifier-k5.relation-schema.json"))
    r = _Run(h, classify(h), time_limit=60, solver="balancedgo", seed=20260924, tools=find_solvers())
    r.b["hw"].raise_lower(2, "cyclic")
    r.offer("hw", single_node(h.distinct()), "trivial")
    assert r.b["hw"].upper == 10
    claims: list = []
    r._bisect(["balancedgo"], "balancedgo", "balancedgo", claims)
    r._resolve(claims)
    first = r.attempts[0]
    assert (first["k"], first["tool"], first["flags"], first["outcome"]) == (6, "balancedgo", True, "yes")
    assert first["validated_width"] is not None and first["validated_width"] <= 6
    assert r.b["hw"].lower == r.b["hw"].upper == 3
    assert r.b["hw"].lower_method == "refutation:balancedgo"
    assert any(a["k"] == 2 and not a["flags"] and a["outcome"] == "no" and a["used_as"] == "lower bound 3"
               for a in r.attempts)
    assert all(a["k"] < 10 for a in r.attempts)


@pytest.mark.solvers
def test_timeout_kills_the_process(tmp_path):
    """A solver call at one k is killed at its limit (its own process group)."""
    n = 14
    edges = {}
    for r in range(n):
        for c in range(n):
            if c + 1 < n:
                edges[f"h{r}_{c}"] = [f"r{r}c{c}", f"r{r}c{c + 1}"]
            if r + 1 < n:
                edges[f"v{r}_{c}"] = [f"r{r}c{c}", f"r{r + 1}c{c}"]
    h = Hypergraph.from_mapping(edges)
    graph = tmp_path / "grid.hg"
    graph.write_text(h.neutral.text)
    info = find_solvers()["balancedgo"]
    t0 = time.monotonic()
    o = balancedgo.solve(info.path, str(graph), str(tmp_path), k=5, timeout=0.5)
    assert o.outcome == "timeout" and o.tree is None
    assert time.monotonic() - t0 < 5
    assert o.returncode is None


@pytest.mark.solvers
def test_found_from_the_build_script():
    found = find_solvers()
    for tool in ("balancedgo", "logk"):
        info = found[tool]
        assert os.access(info.path, os.X_OK) and len(info.sha256) == 64
        if info.how in ("KHG_WIDTH_SOLVERS", "default"):
            assert info.commit in ("872c662c9f409aeb7386f963d2f16b88523ff4bf",
                                   "5e021dd442b028099c30deecc316a906a49a8cb3")
