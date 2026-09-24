"""Decompositions and their validation against H as given (DESIGN §3.6, D11).

``Decomposition(bag, cover, children)`` is a frozen tree node: ``bag`` the roles (chi_t), ``cover`` the relations with
their weights (lambda_t; weight 1 for a guard). ``Tree`` is the mutable flat form the lifting code builds.

``validate(h, d, kind=...)`` checks

========  ===========================================================================  ===================
kind      conditions                                                                   width
========  ===========================================================================  ===================
``td``    (1) every edge lies in a bag; (2) the bags holding a role form a subtree     max |chi_t| - 1
``ghd``   TD, plus (3) chi_t is a subset of the union of lambda_t, lambda_t in E(H)    max |lambda_t|
``hd``    GHD, plus (4) the special condition (U lambda_t) & chi(T_t) <= chi_t          max |lambda_t|
``fhd``   TD, plus a cover with sum_{e ∋ v} lambda_t(e) >= 1 on chi_t, exact rationals max sum lambda_t
========  ===========================================================================  ===================

Condition (4) is computed bottom-up (subtree unions as bitsets). Every walk is iterative, so a join tree of
thousands of relations is fine. Certificates serialise as a flat node list (``to_json``): each node with its
``bag``, its ``cover`` (a list of relations for a guard, a mapping to fractions such as ``"1/2"`` for a fractional
cover) and its ``parent`` index.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .hypergraph import Hypergraph

__all__ = ["Decomposition", "Tree", "Validation", "validate", "KINDS", "frac", "frac_str"]

KINDS = ("td", "ghd", "hd", "fhd")
ONE = Fraction(1)


def frac(x: Any) -> Fraction:
    """A Fraction from an int, a Fraction or a string such as ``"3/2"``."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, bool):
        raise TypeError("not a number")
    if isinstance(x, (int, str)):
        return Fraction(x)
    if isinstance(x, float):
        return Fraction(x).limit_denominator(10**6)
    raise TypeError(f"not a fraction: {x!r}")


def frac_str(x: Fraction | int) -> str:
    """``"3/2"``, ``"2"``."""
    return str(Fraction(x))


def _cover(cover: Any) -> tuple[tuple[str, Fraction], ...]:
    if cover is None:
        return ()
    if isinstance(cover, Mapping):
        items = [(str(k), frac(v)) for k, v in cover.items()]
    else:
        items = [(str(k), ONE) for k in cover]
    merged: dict[str, Fraction] = {}
    for k, w in items:
        merged[k] = merged.get(k, Fraction(0)) + w
    return tuple(sorted(merged.items()))


@dataclass(frozen=True, eq=False, repr=False)
class Decomposition:
    """A node of a (tree, generalised hypertree, hypertree or fractional hypertree) decomposition."""

    bag: frozenset = frozenset()
    cover: tuple = ()
    children: tuple = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "bag", frozenset(map(str, self.bag)))
        if not (isinstance(self.cover, tuple) and all(isinstance(c, tuple) and len(c) == 2 for c in self.cover)):
            object.__setattr__(self, "cover", _cover(self.cover))
        object.__setattr__(self, "children", tuple(self.children))

    # ---------------------------------------------------------------- views
    @property
    def guard(self) -> tuple[str, ...]:
        return tuple(k for k, _ in self.cover)

    @property
    def weights(self) -> dict[str, Fraction]:
        return dict(self.cover)

    def walk(self) -> list[tuple[Decomposition, int | None]]:
        """Pre-order ``(node, parent index)``, iteratively."""
        out: list[tuple[Decomposition, int | None]] = []
        stack: list[tuple[Decomposition, int | None]] = [(self, None)]
        while stack:
            node, parent = stack.pop()
            i = len(out)
            out.append((node, parent))
            stack.extend((c, i) for c in reversed(node.children))
        return out

    def __iter__(self) -> Iterator[Decomposition]:
        return (n for n, _ in self.walk())

    def size(self) -> int:
        return len(self.walk())

    def __repr__(self) -> str:
        return f"Decomposition(nodes={self.size()}, root_bag={sorted(self.bag)!r})"

    # ---------------------------------------------------------------- transforms
    def rename(self, roles: Mapping[str, str] | None = None, relations: Mapping[str, str] | None = None
               ) -> Decomposition:
        """The same tree with role and relation names mapped (unmapped names kept)."""
        r = roles or {}
        e = relations or {}
        t = Tree.from_decomposition(self)
        t.bags = [{r.get(v, v) for v in b} for b in t.bags]
        t.covers = [{e.get(k, k): w for k, w in c.items()} for c in t.covers]
        return t.freeze()

    # ---------------------------------------------------------------- JSON
    def to_json(self, *, fractional: bool | None = None) -> dict[str, Any]:
        """``{"nodes": [{"bag", "cover", "parent"}...]}``; covers are lists of names unless a weight is not 1 (or
        ``fractional=True``), then mappings to fraction strings."""
        nodes = self.walk()
        if fractional is None:
            fractional = any(w != 1 for n, _ in nodes for _, w in n.cover)
        out = []
        for n, p in nodes:
            cover: Any = ({k: frac_str(w) for k, w in n.cover} if fractional else [k for k, _ in n.cover])
            out.append({"bag": sorted(n.bag), "cover": cover, "parent": p})
        return {"nodes": out}

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> Decomposition:
        """Read the flat form of ``to_json``, or a nested ``{"bag", "cover", "children"}`` tree."""
        if "nodes" in obj:
            t = Tree()
            for i, n in enumerate(obj["nodes"]):
                t.bags.append(set(n.get("bag", [])))
                t.covers.append(dict(_cover(n.get("cover"))))
                p = n.get("parent")
                t.parent.append(None if p is None else int(p))
            return t.freeze()
        t = Tree()
        stack: list[tuple[Mapping[str, Any], int | None]] = [(obj, None)]
        while stack:
            n, p = stack.pop()
            i = t.add(n.get("bag", []), n.get("cover"), p)
            stack.extend((c, i) for c in (n.get("children") or []))
        return t.freeze()


@dataclass
class Tree:
    """A mutable flat decomposition: parallel lists of bags, covers and parent indices (None for the root)."""

    bags: list[set] = field(default_factory=list)
    covers: list[dict] = field(default_factory=list)
    parent: list[int | None] = field(default_factory=list)

    def add(self, bag: Iterable[str], cover: Any = None, parent: int | None = None) -> int:
        self.bags.append(set(bag))
        self.covers.append(dict(_cover(cover)))
        self.parent.append(parent)
        return len(self.bags) - 1

    def __len__(self) -> int:
        return len(self.bags)

    @classmethod
    def from_decomposition(cls, d: Decomposition) -> Tree:
        t = cls()
        for n, p in d.walk():
            t.bags.append(set(n.bag))
            t.covers.append(dict(n.cover))
            t.parent.append(p)
        return t

    def roots(self) -> list[int]:
        return [i for i, p in enumerate(self.parent) if p is None]

    def freeze(self) -> Decomposition:
        """The frozen tree. Several roots are chained under the first (they share no role in a valid forest).
        An empty tree is one empty node."""
        n = len(self.bags)
        if n == 0:
            return Decomposition()
        parent = list(self.parent)
        roots = [i for i, p in enumerate(parent) if p is None]
        if not roots:
            raise ValueError("a decomposition needs a root")
        for r in roots[1:]:
            parent[r] = roots[0]
        kids: list[list[int]] = [[] for _ in range(n)]
        for i, p in enumerate(parent):
            if p is not None:
                kids[p].append(i)
        # iterative post-order from the root
        order: list[int] = []
        stack = [roots[0]]
        seen = set()
        while stack:
            i = stack.pop()
            if i in seen:
                raise ValueError("the parent links contain a cycle")
            seen.add(i)
            order.append(i)
            stack.extend(kids[i])
        if len(order) != n:
            raise ValueError("the parent links do not form one tree")
        built: dict[int, Decomposition] = {}
        for i in reversed(order):
            built[i] = Decomposition(frozenset(self.bags[i]), tuple(sorted(self.covers[i].items())),
                                     tuple(built.pop(c) for c in kids[i]))
        return built[roots[0]]


@dataclass(frozen=True)
class Validation:
    """The verdict of ``validate``: ``ok`` when every condition of ``kind`` holds; ``failures`` names them."""

    kind: str
    ok: bool
    width: Any
    conditions: dict = field(default_factory=dict)
    failures: tuple = ()
    nodes: int = 0

    def to_json(self) -> dict[str, Any]:
        w = self.width
        return {"kind": self.kind, "ok": self.ok,
                "width": frac_str(w) if isinstance(w, Fraction) else w,
                "conditions": dict(self.conditions), "failures": list(self.failures), "nodes": self.nodes}


def validate(h: Hypergraph, d: Decomposition, *, kind: str) -> Validation:
    """Check ``d`` against ``h`` as given (see the module docstring)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    nodes = d.walk()
    n = len(nodes)
    failures: list[str] = []
    verts = list(h.vertices)
    bit = {v: 1 << i for i, v in enumerate(verts)}
    extra = sorted({v for node, _ in nodes for v in node.bag if v not in bit})
    if extra:
        failures.append(f"bags hold roles not in H: {', '.join(extra[:5])}")
    for v in extra:
        bit[v] = 1 << len(bit)

    def mask(vs: Iterable[str]) -> int:
        m = 0
        for v in vs:
            m |= bit[v]
        return m

    chi = [mask(node.bag) for node, _ in nodes]
    parent = [p for _, p in nodes]
    # (1) every edge lies in a bag
    holders: dict[str, list[int]] = {}
    for i, (node, _) in enumerate(nodes):
        for v in node.bag:
            holders.setdefault(v, []).append(i)
    c1 = True
    for name, e in h.edges:
        em = mask(e)
        rare = min(e, key=lambda v: len(holders.get(v, ())))
        if not any(chi[i] & em == em for i in holders.get(rare, ())):
            c1 = False
            failures.append(f"(1) relation {name} lies in no bag")
            break
    # (2) the bags holding a role form a subtree: exactly one holder whose parent does not hold it
    c2 = True
    for v, hs in holders.items():
        b = bit[v]
        tops = sum(1 for i in hs if parent[i] is None or not chi[parent[i]] & b)
        if tops != 1:
            c2 = False
            failures.append(f"(2) the bags holding {v} are not connected")
            break
    conditions: dict[str, bool] = {"covers": c1, "connected": c2}
    width: Any
    if kind == "td":
        width = max(0, max((len(node.bag) for node, _ in nodes), default=0) - 1)
    elif kind in ("ghd", "hd"):
        c3 = True
        lam: list[int] = []
        for i, (node, _) in enumerate(nodes):
            u = 0
            for k, w in node.cover:
                if k not in h:
                    c3 = False
                    failures.append(f"(3) guard {k} is not a relation of H")
                    continue
                if w != 1:
                    c3 = False
                    failures.append(f"(3) guard {k} has weight {w}, not 1")
                u |= mask(h.edge(k))
            lam.append(u)
            if chi[i] & ~u:
                if c3:
                    failures.append(f"(3) a bag is not covered by its guard ({sorted(node.bag)[:4]}...)")
                c3 = False
        conditions["guarded"] = c3
        width = max((len(node.cover) for node, _ in nodes), default=0)
        if kind == "hd":
            # (4) bottom-up subtree unions
            sub = list(chi)
            for i in range(n - 1, 0, -1):  # pre-order: a parent precedes its children
                p = parent[i]
                if p is not None:
                    sub[p] |= sub[i]
            c4 = all(not (lam[i] & sub[i] & ~chi[i]) for i in range(n))
            if not c4:
                bad = next(i for i in range(n) if lam[i] & sub[i] & ~chi[i])
                failures.append(f"(4) special condition fails at the node with guard {list(nodes[bad][0].guard)}")
            conditions["special"] = c4
    else:  # fhd
        cf = True
        width = Fraction(0)
        for i, (node, _) in enumerate(nodes):
            total = Fraction(0)
            cov: dict[str, Fraction] = {}
            for k, w in node.cover:
                if k not in h:
                    cf = False
                    failures.append(f"(f) cover relation {k} is not a relation of H")
                    continue
                if w < 0:
                    cf = False
                    failures.append(f"(f) negative weight on {k}")
                total += w
                for v in h.edge(k):
                    cov[v] = cov.get(v, Fraction(0)) + w
            width = max(width, total)
            short = [v for v in node.bag if cov.get(v, Fraction(0)) < 1]
            if short:
                if cf:
                    failures.append(f"(f) roles covered below 1: {', '.join(sorted(short)[:5])}")
                cf = False
        conditions["fractional"] = cf
    ok = all(conditions.values()) and not extra
    return Validation(kind=kind, ok=ok, width=width, conditions=conditions, failures=tuple(failures), nodes=n)


def demote(v: Validation) -> str | None:
    """``"ghd"`` when an HD fails only the special condition (a GHD bound, DESIGN §3.6), else None."""
    if v.kind == "hd" and not v.ok and v.conditions.get("special") is False and all(
            ok for c, ok in v.conditions.items() if c != "special"):
        return "ghd"
    return None


def single_node(h: Hypergraph) -> Decomposition:
    """The trivial HD: one node holding every role, guarded by every relation (hw <= |E|)."""
    return Decomposition(frozenset(h.vertices), tuple((n, ONE) for n in sorted(h.names)))


def join_tree_decomposition(h: Hypergraph, links: Sequence[tuple[str, str]]) -> Decomposition:
    """The width-1 HD of an alpha-acyclic H from join-tree links (child, parent): one node per relation, bag = its
    roles, guard = itself."""
    t = Tree()
    idx: dict[str, int] = {}
    for name, e in h.edges:
        idx[name] = t.add(e, [name], None)
    for child, par in links:
        t.parent[idx[child]] = idx[par]
    return t.freeze()
