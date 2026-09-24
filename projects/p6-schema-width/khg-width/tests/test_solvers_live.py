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
    rep = check(row["path"], slots=row["slot_tuple"], solver=solver, time_limit=60)
    hw = rep.widths["hw"]
    assert hw.exact and hw.value == int(row["hw"])
    assert rep.disagreements == []
    tools = {s["tool"] for s in hw.steps}
    if solver == "auto":
        assert {"balancedgo", "logk"} <= tools  # primary and second opinion
    else:
        assert solver in tools and ({"balancedgo", "logk"} - {solver}).isdisjoint(tools)
    for s in hw.steps:
        assert set(s) >= {"measure", "method", "tool", "k", "limit", "seconds", "outcome"}
    assert rep.tools[solver if solver != "auto" else "balancedgo"]["sha256"]


@pytest.mark.solvers
def test_second_opinion_reruns_k_minus_one():
    rep = check(str(FIXTURES / "p6-qualifier-k5.relation-schema.json"), solver="auto")
    ks = [(s["tool"], s["k"], s["outcome"]) for s in rep.widths["hw"].steps if s["tool"] == "logk"]
    assert ("logk", 3, "yes") in ks and ("logk", 2, "no") in ks


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
