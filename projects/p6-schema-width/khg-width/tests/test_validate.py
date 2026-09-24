"""G2: ``validate`` catches each condition's injected violation (DESIGN §3.6), including the special condition on
p6-adler's width-2 GHD, and demotion."""
from __future__ import annotations

from fractions import Fraction

from helpers import FIXTURES
from khg_width import Decomposition, Hypergraph, check, validate
from khg_width.decomposition import Tree, demote

TRI = Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"]})


def node(bag, cover=(), children=()):
    return Decomposition(frozenset(bag), cover, tuple(children))


def good() -> Decomposition:
    # the width-2 HD of the triangle
    return node("abc", {"E1": 1, "E2": 1}, [node("ab", {"E1": 1})])


def test_valid_hd_all_kinds():
    d = good()
    for kind, width in (("td", 2), ("ghd", 2), ("hd", 2), ("fhd", Fraction(2))):
        v = validate(TRI, d, kind=kind)
        assert v.ok and v.width == width and v.failures == (), (kind, v)


def test_condition_1_edge_not_covered():
    d = node("ab", {"E1": 1}, [node("bc", {"E2": 1})])
    v = validate(TRI, d, kind="td")
    assert not v.ok and v.conditions["covers"] is False
    assert any("(1) relation E3" in f for f in v.failures)


def test_condition_2_disconnected():
    d = node("ab", {"E1": 1}, [node("bc", {"E2": 1}, [node("ac", {"E3": 1})])])
    v = validate(TRI, d, kind="td")
    assert not v.ok and v.conditions["connected"] is False
    assert any("(2) the bags holding a" in f for f in v.failures)
    assert v.conditions["covers"] is True


def test_condition_3_guard():
    d = node("abc", {"E1": 1})  # c not covered
    v = validate(TRI, d, kind="ghd")
    assert not v.ok and v.conditions["guarded"] is False
    d2 = node("abc", {"E1": 1, "E9": 1})  # not a relation of H
    v2 = validate(TRI, d2, kind="ghd")
    assert not v2.ok and any("E9 is not a relation of H" in f for f in v2.failures)
    d3 = node("abc", {"E1": Fraction(1, 2), "E2": 1, "E3": 1})  # a fractional guard is not a GHD guard
    v3 = validate(TRI, d3, kind="hd")
    assert not v3.ok and any("weight 1/2" in f for f in v3.failures)


def test_fractional_cover():
    d = node("abc", {"E1": Fraction(1, 2), "E2": Fraction(1, 2), "E3": Fraction(1, 2)})
    v = validate(TRI, d, kind="fhd")
    assert v.ok and v.width == Fraction(3, 2)
    d2 = node("abc", {"E1": Fraction(1, 2), "E2": Fraction(1, 2), "E3": Fraction(1, 3)})
    v2 = validate(TRI, d2, kind="fhd")
    assert not v2.ok and v2.conditions["fractional"] is False
    assert any("covered below 1" in f for f in v2.failures)


def test_unknown_role_in_bag():
    d = node("abcz", {"E1": 1, "E2": 1})
    v = validate(TRI, d, kind="td")
    assert not v.ok and any("not in H" in f for f in v.failures)


def test_special_condition_on_adler():
    """p6-adler has ghw 2 < hw 3: its width-2 GHD must fail condition (4) and be demoted to a GHD bound."""
    rep = check(str(FIXTURES / "p6-adler.relation-schema.json"), solver="python")
    g = rep.widths["ghw"]
    assert g.value == 2 and rep.widths["hw"].value == 3
    from khg_width.hypergraph import hypergraph

    h = hypergraph(str(FIXTURES / "p6-adler.relation-schema.json"))
    assert validate(h, g.certificate, kind="ghd").ok
    v = validate(h, g.certificate, kind="hd")
    assert not v.ok
    assert v.conditions == {"covers": True, "connected": True, "guarded": True, "special": False}
    assert any(f.startswith("(4) special condition fails") for f in v.failures)
    assert demote(v) == "ghd"


def test_special_condition_injected():
    """A GHD of the triangle whose root guard reaches into its subtree beyond its bag."""
    h = Hypergraph.from_mapping({"E1": ["a", "b"], "E2": ["b", "c"], "E3": ["a", "c"], "E4": ["c", "d"]})
    d = node("ab", {"E1": 1, "E4": 1}, [node("abc", {"E1": 1, "E2": 1}, [node("cd", {"E4": 1})])])
    # E4 = {c, d} is a guard of the root; c and d lie below the root and not in its bag
    v = validate(h, d, kind="ghd")
    assert v.ok  # (1)-(3) hold
    v4 = validate(h, d, kind="hd")
    assert not v4.ok and v4.conditions["special"] is False
    assert demote(v4) == "ghd"
    assert demote(validate(h, node("ab", {"E1": 1}), kind="hd")) is None  # not a special-condition failure


def test_tree_roundtrip_and_deep_chain():
    """Walks are iterative: a 5,000-node chain validates and serialises."""
    names = {f"E{i}": [f"v{i}", f"v{i + 1}"] for i in range(5000)}
    h = Hypergraph.from_mapping(names)
    t = Tree()
    parent = None
    for i in range(5000):
        parent = t.add([f"v{i}", f"v{i + 1}"], [f"E{i}"], parent)
    d = t.freeze()
    v = validate(h, d, kind="hd")
    assert v.ok and v.width == 1 and v.nodes == 5000
    j = d.to_json()
    assert len(j["nodes"]) == 5000 and j["nodes"][1]["parent"] == 0
    d2 = Decomposition.from_json(j)
    assert validate(h, d2, kind="hd").ok
    nested = Decomposition.from_json({"bag": ["a", "b"], "cover": ["E1"], "children": [{"bag": ["a", "b", "c"],
                                                                                    "cover": {"E1": "1", "E2": "1"}}]})
    assert validate(TRI, nested, kind="td").ok and nested.size() == 2
