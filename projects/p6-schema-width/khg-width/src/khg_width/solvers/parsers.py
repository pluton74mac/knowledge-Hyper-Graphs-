"""Parsers for BalancedGo and log-k-decomp output (R01 §4.3).

- ``parse_stdout``: the summary lines ``Result ( ran with K = k )``, ``Width:  w``, ``Correct:  true|false``, the
  ``SCV found!`` warning (a special-condition violation: the result is at best a GHD), an echoed edge count if a tool
  prints one, and the printed tree (``Bag: {..}`` / ``Cover: {..}`` / ``Children: n`` / ``[`` ... ``]``).
- ``parse_json``: BalancedGo ``-json FILE``: ``{"Root": {"Bag": [...], "Cover": [...], "Children": [...]|null}}``.
- ``parse_gml``: ``-gml FILE``: nodes labelled ``"{cover} {bag}"``, edges from parent to child.

Trees come back as nested ``{"bag", "cover", "children"}`` dicts in the tool's (neutral) names;
``Decomposition.from_json`` and ``rename`` turn them into certificates in H's names.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

__all__ = ["Parsed", "parse_stdout", "parse_json", "parse_gml", "parse_tree_text"]


@dataclass(frozen=True)
class Parsed:
    k: int | None
    width: int | None
    correct: bool | None
    scv: bool
    edges_echoed: int | None
    tree: dict | None
    algorithm: str | None
    check_failures: tuple = ()  # the tool's own check rejected a decomposition it found (not a "no")


#: What BalancedGo's and log-k-decomp's ``Decomp.Correct`` print when a decomposition they found fails their own
#: check (lib/decomp.go at the pinned commits). A "no" (no decomposition of width k) prints none of them: its
#: decomposition is empty and ``Correct`` returns false silently.
CHECK_FAILURES = (
    re.compile(r"^Decomp of different graph"),
    re.compile(r"^Empty Decomp"),
    re.compile(r"Bags not subsets of edge labels"),
    re.compile(r"^Edge .* isn't covered"),
    re.compile(r"^Vertex .* doesn't span connected subtree"),
)


_SET = re.compile(r"\{([^}]*)\}")


def _items(text: str) -> list[str]:
    m = _SET.search(text)
    if not m:
        return []
    return [x.strip() for x in m.group(1).split(",") if x.strip()]


def parse_tree_text(text: str) -> dict | None:
    """The tree a tool prints after ``Result ( ran with K = k )``; None when there is none (or it is empty)."""
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.lstrip().startswith("Result ("))
    except StopIteration:
        start = 0
    root: dict | None = None
    stack: list[list[dict]] = []  # child lists being filled
    last: dict | None = None
    pending_children = False
    for ln in lines[start + 1:]:
        s = ln.strip()
        if s.startswith("Bag:"):
            node = {"bag": _items(s), "cover": [], "children": []}
            if root is None:
                root = node
            elif stack:
                stack[-1].append(node)
            last = node
        elif s.startswith("Cover:") and last is not None:
            last["cover"] = _items(s)
        elif s.startswith("Children:"):
            pending_children = True
        elif s == "[":
            if last is None:
                break
            stack.append(last["children"] if pending_children else [])
            pending_children = False
        elif s == "]":
            if stack:
                stack.pop()
        elif s.startswith("Time") or s.startswith("Width:"):
            break
    if root is None or (not root["bag"] and not root["cover"] and not root["children"]):
        return None
    return root


def parse_stdout(text: str) -> Parsed:
    k = width = echoed = None
    correct = None
    algorithm = None
    for ln in text.splitlines():
        s = ln.strip()
        m = re.match(r"Result \( ran with K = (\d+) \)", s)
        if m:
            k = int(m.group(1))
        m = re.match(r"Width:\s+(-?\d+)", s)
        if m:
            width = int(m.group(1))
        m = re.match(r"Correct:\s+(true|false)", s)
        if m:
            correct = m.group(1) == "true"
        m = re.match(r"Used algorithm:\s*(.*?)\s*(@.*)?$", s)
        if m:
            algorithm = m.group(1)
        m = re.search(r"#hyperedges\"?\s*[:=]\s*(\d+)", s) or re.match(r"(?:Edges|edges|hyperedges):\s*(\d+)$", s)
        if m:
            echoed = int(m.group(1))
    failures = tuple(ln.strip() for ln in text.splitlines() if any(rx.search(ln.strip()) for rx in CHECK_FAILURES))
    return Parsed(k=k, width=width, correct=correct, scv="SCV found!" in text, edges_echoed=echoed,
                  tree=parse_tree_text(text), algorithm=algorithm, check_failures=failures)


def _from_balancedgo(node: dict | None) -> dict | None:
    if node is None:
        return None
    out = {"bag": list(node.get("Bag") or []), "cover": list(node.get("Cover") or []), "children": []}
    stack = [(node, out)]
    while stack:
        src, dst = stack.pop()
        for ch in src.get("Children") or []:
            d = {"bag": list(ch.get("Bag") or []), "cover": list(ch.get("Cover") or []), "children": []}
            dst["children"].append(d)
            stack.append((ch, d))
    return out


def parse_json(text: str) -> dict | None:
    """BalancedGo's ``-json`` decomposition."""
    data: Any = json.loads(text)
    if not isinstance(data, dict):
        return None
    return _from_balancedgo(data.get("Root"))


def parse_gml(text: str) -> dict | None:
    """A ``-gml`` decomposition: labels ``"{cover} {bag}"``; the root is the node that is no edge's target."""
    nodes: dict[str, dict] = {}
    for m in re.finditer(r"node\s*\[\s*id\s+(\S+)\s+label\s+\"([^\"]*)\"", text):
        label = m.group(2)
        sets = _SET.findall(label)
        cover = [x.strip() for x in sets[0].split(",") if x.strip()] if sets else []
        bag = [x.strip() for x in sets[1].split(",") if x.strip()] if len(sets) > 1 else []
        nodes[m.group(1)] = {"bag": bag, "cover": cover, "children": []}
    targets = set()
    for m in re.finditer(r"edge\s*\[\s*source\s+(\S+)\s+target\s+(\S+)", text):
        s, t = m.group(1), m.group(2)
        if s in nodes and t in nodes:
            nodes[s]["children"].append(nodes[t])
            targets.add(t)
    roots = [n for i, n in nodes.items() if i not in targets]
    if len(roots) != 1:
        return None
    return roots[0]
