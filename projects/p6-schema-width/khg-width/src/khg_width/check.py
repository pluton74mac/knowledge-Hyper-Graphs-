"""``check``: class and the four widths of a schema, each exact or bounded, with validated certificates.

The flow (DESIGN §3):

1. read the schema (``.json``, ``.json.gz``, a mapping or a ``Schema``) and build H(S, sigma);
2. classify (uncapped, polynomial);
3. widths. Empty H: all 0. alpha-acyclic H: hw = ghw = fhw = 1 from the join tree. Otherwise:
   - **tw**: universal roles out (+1 each), lonely roles as the simplicial rule, the general simplicial rule, blocks;
     subset DP per block of <= 20 roles, else heuristic orderings plus minor-min-width and induced-DP lower bounds;
   - **ghw, fhw**: the core (GYO, twins, universal roles), blocks; DP per block (<= 20 roles, <= 16 for fhw), else
     heuristic orderings with greedy covers / rho*, clique and induced-DP lower bounds; lifted to H and validated;
   - **hw** on the unreduced H: the trivial one-node HD, the Python normal-form search (<= 60 relations), the external
     solvers' schedule (BalancedGo, log-k-decomp as second opinion), an induced-hd-search lower bound;
   - propagation through the width inequalities.

Every step is limited by ``time_limit`` and logged. No upper bound is reported without a decomposition validated
on H; an HD failing the special condition is demoted to a ghw bound; every disagreement is kept.
"""
from __future__ import annotations

import math
import os
import platform
import tempfile
import time
from fractions import Fraction
from typing import Any, Mapping, Sequence

from . import __version__
from .acyclicity import Acyclicity, InternalError, classify
from .bounds import (INDUCED_ROLES, INDUCED_ROLES_FHW, Bound, clique_bounds, grow_induced, min_degree_order,
                     min_fill_order, minor_min_width, propagate, repair_special)
from .covers import fractional_cover, greedy_cover, rho, rho_star
from .decomposition import Decomposition, Tree, Validation, demote, single_node, validate
from .exact import (DP_LIMIT, DP_LIMIT_FHW, HD_SEARCH_BUDGET, HD_SEARCH_RELATIONS, dp_width, elimination_tree,
                    hd_search, rho_cost, rho_star_cost)
from .hypergraph import HEADLINE_SLOTS, Hypergraph, UsageError, check_slots, read_schema
from .reduce import Core, core, lift_core, lift_tw, primal, tw_reduce
from .report import MEASURES, Width, WidthReport
from .steps import Budget, Deadline, StepLog

__all__ = ["check", "check_hypergraph", "width", "SOLVER_MODES", "K_MAX", "SEED", "DEFAULT_TIME_LIMIT"]

SOLVER_MODES = ("auto", "python", "balancedgo", "logk")
K_MAX = 10
SEED = 20260924
DEFAULT_TIME_LIMIT = 60.0
KIND = {"hw": "hd", "ghw": "ghd", "fhw": "fhd", "tw": "td"}


def _check_limit(time_limit: float) -> float:
    try:
        t = float(time_limit)
    except (TypeError, ValueError):
        raise UsageError(f"bad time limit {time_limit!r}") from None
    if not math.isfinite(t) or t <= 0:
        raise UsageError(f"the time limit must be a positive number of seconds, got {time_limit!r}")
    return t


def _tools_for(solver: str) -> dict:
    if solver not in SOLVER_MODES:
        raise UsageError(f"unknown solver {solver!r}; choose from {', '.join(SOLVER_MODES)}")
    if solver == "python":
        return {}
    from .solvers import find_solvers

    found = find_solvers()
    if solver in ("balancedgo", "logk") and solver not in found:
        raise UsageError(f"the requested solver {solver} was not found (scripts/build-solvers.sh; "
                         f"KHG_WIDTH_SOLVERS, KHG_WIDTH_BALANCEDGO, KHG_WIDTH_LOGK or PATH)")
    return found


# ------------------------------------------------------------------------------------------------ the run
class _Run:
    def __init__(self, h: Hypergraph, acy: Acyclicity, *, time_limit: float, solver: str, seed: int,
                 tools: Mapping[str, Any]):
        self.h = h
        self.d = h.distinct()
        self.acy = acy
        self.T = time_limit
        self.solver = solver
        self.seed = seed
        self.tools = dict(tools)
        self.log = StepLog()
        self.reductions: list[dict] = []
        self.disagreements: list[dict] = []
        self.b: dict[str, Bound] = {m: Bound(m) for m in MEASURES}
        self.core: Core | None = None
        self.tw_td: Decomposition | None = None
        self.detail: dict[str, str] = {m: "" for m in MEASURES}

    # ---------------------------------------------------------------- helpers
    def offer(self, measure: str, d: Decomposition, method: str, *, kind: str | None = None) -> Validation:
        """Validate ``d`` on H as ``kind`` (the measure's own by default) and offer it as an upper bound."""
        kind = kind or KIND[measure]
        v = validate(self.h, d, kind=kind)
        if v.ok:
            self.b[measure].offer_upper(v.width, method, d, kind, v)
        return v

    def step(self, fn, *, measure: str, method: str, k: int | None = None, detail: str | None = None,
             tool: str = "python") -> tuple[str, Any]:
        return self.log.run(fn, measure=measure, method=method, limit=self.T, k=k, detail=detail, tool=tool)

    def finish(self) -> dict[str, Width]:
        out = {}
        for m in MEASURES:
            b = self.b[m]
            if b.upper is not None and b.lower is not None and (b.lower > b.upper or (b.lower == b.upper
                                                                                      and b.lower_exclusive)):
                raise InternalError(f"{m}: lower bound {b.lower} ({b.lower_method}) exceeds the validated upper "
                                    f"bound {b.upper} ({b.upper_method})")
            out[m] = Width(measure=m, lower=b.lower, upper=b.upper, lower_exclusive=b.lower_exclusive,
                           lower_method=b.lower_method, upper_method=b.upper_method or "", certificate=b.certificate,
                           validation=b.validation, steps=tuple(self.log.for_measure(m)),
                           detail=self._detail(m, b))
        return out

    def _detail(self, m: str, b: Bound) -> str:
        extra = self.detail.get(m, "")
        if b.exact:
            base = b.upper_method if b.upper_method == b.lower_method else f"{b.lower_method} = {b.upper_method}"
        else:
            base = f"lower {b.lower_method}, upper {b.upper_method}"
        cert = f"; {KIND[m].upper()} validated" if b.validation is not None and b.validation.ok else ""
        return (base + (f" ({extra})" if extra else "") + cert).strip()

    # ---------------------------------------------------------------- orchestration
    def run(self, measures: Sequence[str] = MEASURES) -> dict[str, Width]:
        h = self.h
        if h.is_empty():
            for m in MEASURES:
                self.b[m].lower = self.b[m].upper = (Fraction(0) if m == "fhw" else 0)
                self.b[m].lower_method = self.b[m].upper_method = "empty"
                self.b[m].certificate = Decomposition()
                self.b[m].validation = validate(h, Decomposition(), kind=KIND[m])
            return self.finish()
        alpha = self.acy.cls != "cyclic"
        if alpha:
            jt = self.acy.join_tree
            for m in ("hw", "ghw", "fhw"):
                v = validate(h, jt, kind=KIND[m])
                if not v.ok or v.width != 1:
                    raise InternalError(f"the join tree is not a width-1 {KIND[m]}: {v.failures}")
                b = self.b[m]
                b.lower = b.upper = Fraction(1) if m == "fhw" else 1
                b.lower_method = b.upper_method = "join-tree"
                b.certificate, b.certificate_kind, b.validation = jt, KIND[m], v
        else:
            self.b["hw"].raise_lower(2, "cyclic")
            self.b["ghw"].raise_lower(2, "cyclic")
            self.b["fhw"].raise_lower(Fraction(1), "cyclic", exclusive=True)
        if "tw" in measures:
            self.tw()
        if not alpha:
            if "ghw" in measures or "fhw" in measures or "hw" in measures:
                self.ghw_fhw(want_fhw="fhw" in measures)
            if "hw" in measures:
                self.hw()
            propagate(self.b, self.convert)
        return self.finish()

    def convert(self, src: Bound, kind: str) -> tuple[Decomposition, Validation] | None:
        if src.certificate is None:
            return None
        v = validate(self.h, src.certificate, kind=kind)
        return (src.certificate, v) if v.ok else None

    # ---------------------------------------------------------------- tw
    def tw(self) -> None:
        h, b = self.h, self.b["tw"]
        b.raise_lower(max(0, h.stats["rank"] - 1), "rank")
        outcome, tr = self.step(lambda dl: tw_reduce(h, deadline=dl), measure="tw", method="simplicial-rule")
        assert tr is not None  # tw_reduce keeps a partial result at the deadline
        self.reductions += [
            {"reduction": "universal", "removed_roles": tr.offset, "measures": ["tw"], "offset": tr.offset},
            {"reduction": "simplicial", "removed_roles": tr.summary["simplicial"], "measures": ["tw"],
             "complete": tr.complete},
            {"reduction": "blocks", "blocks": len(tr.blocks), "measures": ["tw"]},
        ]
        b.raise_lower(tr.lower + tr.offset, "simplicial")
        parts: list[tuple[frozenset, Tree]] = []
        exact_vals: list[int] = []
        all_exact = True
        for blk in sorted(tr.blocks, key=lambda x: (-len(x), sorted(x))):
            verts = sorted(blk)
            adj = {v: tr.adj[v] & blk for v in verts}
            if len(verts) == 1:
                t = Tree()
                t.add(verts, None, None)
                parts.append((blk, t))
                exact_vals.append(0)
                continue
            tree = None
            if len(verts) <= DP_LIMIT:
                outcome, res = self.step(lambda dl: dp_width(verts, adj, lambda m: m.bit_count() - 1, dl),
                                         measure="tw", method="dp", detail=f"block of {len(verts)} roles")
                if outcome == "done":
                    val, order = res
                    tree = elimination_tree(order, adj)
                    exact_vals.append(val)
            if tree is None:
                all_exact = False
                tree = self._heuristic_td(verts, adj, "tw")
                lb = self._tw_block_lower(verts, adj)
                if lb is not None:
                    b.raise_lower(lb[0] + tr.offset, lb[1])
            parts.append((blk, tree))
        d = lift_tw(h, tr, parts)
        v = self.offer("tw", d, "dp" if all_exact else "heuristic")
        if not v.ok:
            raise InternalError(f"the lifted tree decomposition fails validation: {v.failures}")
        self.tw_td = d
        if all_exact:
            b.raise_lower(max([tr.lower] + exact_vals) + tr.offset, "dp", prefer=True)
            self.detail["tw"] = "subset DP after the simplicial rule" + (
                f", +{tr.offset} universal" if tr.offset else "")
        else:
            self.detail["tw"] = "heuristic orderings on blocks over the DP limit"

    def _heuristic_td(self, verts: list[str], adj: dict, measure: str) -> Tree:
        best: tuple[int, Tree] | None = None
        for name, fn in (("min-degree", min_degree_order), ("min-fill", min_fill_order)):
            if name == "min-fill" and len(verts) > 1500:
                continue
            outcome, order = self.step(lambda dl: fn(adj, seed=self.seed, deadline=dl), measure=measure,
                                       method=f"heuristic-{name}", detail=f"block of {len(verts)} roles")
            if outcome != "done":
                continue
            t = elimination_tree(order, adj)
            w = max(len(bg) for bg in t.bags) - 1
            if best is None or w < best[0]:
                best = (w, t)
        if best is None:
            t = Tree()
            t.add(verts, None, None)
            return t
        return best[1]

    def _tw_block_lower(self, verts: list[str], adj: dict) -> tuple[int, str] | None:
        out = None
        outcome, mmw = self.step(lambda dl: minor_min_width(adj, deadline=dl), measure="tw",
                                 method="minor-min-width")
        if outcome == "done":
            out = (mmw, "minor-min-width")
        deg = {v: len(adj[v]) for v in verts}
        x = grow_induced(adj, deg, INDUCED_ROLES)
        sub = {v: adj[v] & x for v in x}
        outcome, res = self.step(lambda dl: dp_width(sorted(x), sub, lambda m: m.bit_count() - 1, dl),
                                 measure="tw", method="induced-dp", detail=f"{len(x)} roles")
        if outcome == "done" and (out is None or res[0] > out[0]):
            out = (res[0], "induced-dp")
        return out

    # ---------------------------------------------------------------- ghw, fhw
    def ghw_fhw(self, *, want_fhw: bool = True) -> None:
        h = self.h
        c = core(h)
        self.core = c
        s = c.summary
        self.reductions[:0] = [
            {"reduction": "gyo", "removed_roles": s["gyo_roles"], "removed_relations": s["gyo_relations"],
             "measures": ["ghw", "fhw"]},
            {"reduction": "twins", "removed_roles": s["twins"], "measures": ["ghw", "fhw"]},
            {"reduction": "universal", "removed_roles": s["universal"], "measures": ["ghw", "fhw"]},
            {"reduction": "blocks", "blocks": s["blocks"], "measures": ["ghw", "fhw"]},
        ]
        gb, fb = self.b["ghw"], self.b["fhw"]
        g_parts: list[tuple[frozenset, Tree]] = []
        f_parts: list[tuple[frozenset, Tree]] = []
        g_vals: list[int] = []
        f_vals: list[Fraction] = []
        g_all = f_all = True
        for blk in sorted(c.blocks, key=lambda x: (-len(x), sorted(x))):
            be = c.block_edges(blk)
            verts = sorted(blk)
            adj = {v: set() for v in verts}
            adj.update({v: n & blk for v, n in primal(be).items()})
            gtree = ftree = None
            if len(verts) <= DP_LIMIT:
                outcome, res = self.step(lambda dl: dp_width(verts, adj, rho_cost(verts, be, dl), dl),
                                         measure="ghw", method="dp", detail=f"block of {len(verts)} roles")
                if outcome == "done":
                    val, order = res
                    gtree = self._covered(elimination_tree(order, adj), be, fractional=False)
                    g_vals.append(val)
            if want_fhw and len(verts) <= DP_LIMIT_FHW:
                outcome, res = self.step(lambda dl: dp_width(verts, adj, rho_star_cost(verts, be, dl), dl),
                                         measure="fhw", method="dp", detail=f"block of {len(verts)} roles")
                if outcome == "done":
                    val, order = res
                    ftree = self._covered(elimination_tree(order, adj), be, fractional=True)
                    f_vals.append(val)
            need_g = gtree is None
            need_f = want_fhw and ftree is None
            if need_g or need_f:
                orders = self._heuristic_orders(verts, adj, "ghw" if need_g else "fhw")
                if need_g:
                    g_all = False
                    gtree = self._best_covered(orders, verts, adj, be, fractional=False)
                if need_f:
                    f_all = False
                    ftree = self._best_covered(orders, verts, adj, be, fractional=True)
                self._block_lower(verts, adj, be, need_g=need_g, need_f=need_f)
            g_parts.append((blk, gtree))
            if ftree is not None:
                f_parts.append((blk, ftree))
        gd = lift_core(h, c, g_parts)
        v = self.offer("ghw", gd, "dp" if g_all else "heuristic")
        if not v.ok:
            raise InternalError(f"the lifted GHD fails validation: {v.failures}")
        vh = validate(h, gd, kind="hd")
        if vh.ok:
            self.b["hw"].offer_upper(vh.width, "ghd-is-hd", gd, "hd", vh)
        else:
            self._repair(gd, "ghd")
        if g_all and g_vals:
            gb.raise_lower(max(g_vals), "dp", prefer=True)
        if want_fhw and f_parts and len(f_parts) == len(g_parts):
            fd = lift_core(h, c, f_parts)
            v = self.offer("fhw", fd, "dp" if f_all else "heuristic")
            if not v.ok:
                raise InternalError(f"the lifted FHD fails validation: {v.failures}")
            if f_all and f_vals:
                fb.raise_lower(max(f_vals), "dp", prefer=True)
        roles = s["core_roles"]
        self.detail["ghw"] = f"core {roles} roles, {s['core_relations']} relations, {s['blocks']} blocks"
        self.detail["fhw"] = self.detail["ghw"]

    def _repair(self, d: Decomposition, source: str) -> None:
        """An hw upper bound from a GHD (or a TD with greedy guards) made to satisfy the special condition."""
        es = dict(self.h.edges)
        hes = list(self.h.edges)

        def build(dl: Deadline) -> tuple[Decomposition, Decomposition]:
            t = Tree.from_decomposition(d)
            for i, bag in enumerate(t.bags):
                dl.tick()
                if not t.covers[i] or any(w != 1 for w in t.covers[i].values()):
                    t.covers[i] = {g: Fraction(1) for g in greedy_cover(frozenset(bag), hes)} if bag else {}
            guarded = t.freeze()  # a GHD: ghw <= tw + 1 with a certificate
            repair_special(es, t.bags, t.covers, t.parent, deadline=dl)
            return guarded, t.freeze()

        outcome, res = self.step(build, measure="hw", method="hd-repair", detail=f"from the {source}")
        if outcome == "done":
            guarded, hd = res
            if source != "ghd":
                vg = validate(self.h, guarded, kind="ghd")
                if vg.ok:
                    self.b["ghw"].offer_upper(vg.width, "tw-covers", guarded, "ghd", vg)
            v = validate(self.h, hd, kind="hd")
            if not v.ok:
                raise InternalError(f"the repaired HD fails validation: {v.failures}")
            self.b["hw"].offer_upper(v.width, "hd-repair", hd, "hd", v)

    def _covered(self, t: Tree, be: list, *, fractional: bool) -> Tree:
        for i, bag in enumerate(t.bags):
            fb = frozenset(bag)
            if fractional:
                fc = rho_star(fb, be) if len(fb) <= 40 else fractional_cover(fb, be)
                t.covers[i] = dict(fc.weights)
            else:
                t.covers[i] = {n: Fraction(1) for n in rho(fb, be)[1]}
        return t

    def _heuristic_orders(self, verts: list[str], adj: dict, measure: str) -> list[list[str]]:
        orders = []
        for name, fn in (("min-degree", min_degree_order), ("min-fill", min_fill_order)):
            if name == "min-fill" and len(verts) > 1500:
                continue
            outcome, order = self.step(lambda dl: fn(adj, seed=self.seed, deadline=dl), measure=measure,
                                       method=f"heuristic-{name}", detail=f"block of {len(verts)} roles")
            if outcome == "done":
                orders.append(order)
        return orders

    def _best_covered(self, orders: list, verts: list[str], adj: dict, be: list, *, fractional: bool) -> Tree:
        measure = "fhw" if fractional else "ghw"
        best: tuple[Any, Tree] | None = None
        for order in orders:
            def build(dl: Deadline, order=order) -> tuple[Any, Tree]:
                t = elimination_tree(order, adj, deadline=dl)
                greedy = []
                for i, bag in enumerate(t.bags):
                    dl.tick()
                    g = greedy_cover(frozenset(bag), be)
                    t.covers[i] = {n: Fraction(1) for n in g}
                    greedy.append(len(g))
                if not fractional:
                    return max(greedy, default=0), t
                # rho* only where it can matter: bags by decreasing greedy value, until greedy <= the max so far
                worst: Any = Fraction(0)
                for i in sorted(range(len(t.bags)), key=lambda j: -greedy[j]):
                    if greedy[i] <= worst:
                        worst = max(worst, Fraction(greedy[i]))
                        continue
                    fc = fractional_cover(frozenset(t.bags[i]), be, deadline=dl)
                    if fc.value < greedy[i]:
                        t.covers[i] = dict(fc.weights)
                        worst = max(worst, fc.value)
                    else:
                        worst = max(worst, Fraction(greedy[i]))
                return worst, t

            outcome, res = self.step(build, measure=measure, method="covers", detail="bags of a heuristic ordering")
            if outcome == "done" and (best is None or res[0] < best[0]):
                best = res
        if best is None:  # the trivial decomposition of the block: one bag
            t = Tree()
            fb = frozenset(verts)
            if fractional:
                t.add(verts, {n: Fraction(1) for n in greedy_cover(fb, be)}, None)
            else:
                t.add(verts, greedy_cover(fb, be), None)
            return t
        return best[1]

    def _block_lower(self, verts: list[str], adj: dict, be: list, *, need_g: bool, need_f: bool) -> None:
        """Clique and induced-DP lower bounds for a block over the DP limit."""
        gb, fb = self.b["ghw"], self.b["fhw"]
        outcome, res = self.step(lambda dl: clique_bounds(adj, be, deadline=dl, want_fhw=need_f),
                                 measure="ghw" if need_g else "fhw", method="clique")
        if res is not None:
            g, f, _, _, seen = res
            if need_g and g:
                gb.raise_lower(g, "clique")
            if need_f and f > 1:
                fb.raise_lower(f, "clique")
        deg = {v: sum(1 for _, e in be if v in e) for v in verts}
        for measure, size, need in (("ghw", INDUCED_ROLES, need_g), ("fhw", INDUCED_ROLES_FHW, need_f)):
            if not need:
                continue
            x = grow_induced(adj, deg, size)
            sub = [(n, e & x) for n, e in be if e & x]
            outcome, val = self.step(lambda dl: _exact_small(sub, measure, dl), measure=measure,
                                     method="induced-dp", detail=f"{len(x)} roles")
            if outcome == "done" and val is not None:
                (gb if measure == "ghw" else fb).raise_lower(val, "induced-dp")

    # ---------------------------------------------------------------- hw
    def hw(self) -> None:
        d, b = self.d, self.b["hw"]
        triv = single_node(d)
        self.offer("hw", triv, "trivial")
        claims: list[dict] = []  # refutations {tool, k, sound} and validated HDs {tool, width}
        py_done = False
        if self.solver in ("auto", "python") and len(d) <= HD_SEARCH_RELATIONS:
            py_done = self._python_hw(claims)
        primary = None
        if self.solver in ("auto", "balancedgo") and "balancedgo" in self.tools:
            primary = "balancedgo"
        elif self.solver in ("auto", "logk") and "logk" in self.tools:
            primary = "logk"
        if primary is not None:
            propagate(self.b, self.convert)  # the solver schedule starts from hw >= ghw's lower bound
            self._solver_hw(primary, claims)
        self._resolve(claims)
        if not b.exact and self.tw_td is not None and self.b["tw"].upper is not None and (
                b.upper is None or self.b["tw"].upper + 1 < b.upper):
            self._repair(self.tw_td, "tree decomposition of tw")
        if not b.exact and not py_done:
            self._induced_hw()
        if not self.detail["hw"]:
            self.detail["hw"] = (f"{len(self.d)} distinct relations: over the Python search limit "
                                 f"({HD_SEARCH_RELATIONS}); no solver" if primary is None else "")

    def _python_hw(self, claims: list[dict]) -> bool:
        b = self.b["hw"]
        answers = []
        k = max(1, int(b.lower))
        while k <= K_MAX and (b.upper is None or k < b.upper):
            budget = Budget(HD_SEARCH_BUDGET)
            outcome, res = self.step(lambda dl: hd_search(self.d, k, budget=budget, deadline=dl),
                                     measure="hw", method="hd-search", k=k)
            if outcome != "done":
                answers.append(f"k={k} {outcome}")
                self.detail["hw"] = "python hd-search on the input: " + ", ".join(answers)
                return False
            if res is None:
                claims.append({"tool": "python", "k": k, "sound": True})
                answers.append(f"k={k} no")
                k += 1
                continue
            v = self.offer("hw", res, "hd-search")
            answers.append(f"k={k} yes")
            if not v.ok:
                self.disagreements.append({"kind": "invalid", "tool": "python", "k": k,
                                           "failures": list(v.failures)})
                return False
            claims.append({"tool": "python", "hd": v.width})
            self._improve_fhw(res, "improve-hd")
            break
        self.detail["hw"] = ("python hd-search on the input: " + ", ".join(answers) if answers else
                             "python hd-search not needed: the bounds met")
        return True

    def _improve_fhw(self, hd: Decomposition, method: str) -> None:
        """fhw <= max rho*(chi_t) over an HD's bags (ImproveHD)."""
        def build(dl: Deadline) -> Decomposition:
            t = Tree.from_decomposition(hd)
            es = list(self.h.edges)
            for i, bag in enumerate(t.bags):
                dl.tick()
                t.covers[i] = dict(fractional_cover(frozenset(bag), es, deadline=dl).weights)
            return t.freeze()

        outcome, fd = self.step(build, measure="fhw", method=method)
        if outcome == "done":
            self.offer("fhw", fd, method)

    def _solver_hw(self, primary: str, claims: list[dict]) -> None:
        from .solvers import balancedgo, logk

        mods = {"balancedgo": balancedgo, "logk": logk}
        d, b = self.d, self.b["hw"]
        neutral = d.neutral
        with tempfile.TemporaryDirectory(prefix="khg-width-") as work:
            graph = os.path.join(work, "h.hg")
            with open(graph, "w", encoding="utf-8") as fh:
                fh.write(neutral.text)

            def call(tool: str, *, k: int | None, exact: bool = False, flags: bool = False, share: float = 1.0):
                o = mods[tool].solve(self.tools[tool].path, graph, work, k=k, exact=exact, flags=flags,
                                     timeout=self.T * share)
                self.log.add(measure="hw", method="exact" if exact else ("flags" if flags else "width"), tool=tool,
                             k=k, limit=round(self.T * share, 3), seconds=o.seconds, outcome=o.outcome,
                             detail=f"k_reported={o.k_reported}")
                return self._take(o, claims)

            k_yes = None
            if len(d) <= HD_SEARCH_RELATIONS:
                k_yes = call(primary, k=None, exact=True)
            else:
                k = max(1, int(b.lower))
                while k <= K_MAX and k_yes is None and (b.upper is None or k < b.upper):
                    got = call(primary, k=k, share=0.25)
                    if got is None and self._last_outcome(claims, primary, k) == "timeout":
                        got = call(primary, k=k, flags=True, share=0.75)
                    if got is not None:
                        k_yes = got
                        break
                    k += 1
            second = "logk" if primary == "balancedgo" and self.solver == "auto" and "logk" in self.tools else None
            if second and k_yes is not None:
                for kk in [k_yes] + ([k_yes - 1] if any(c.get("tool") == primary and c.get("k") == k_yes - 1
                                                        and c.get("sound") for c in claims) else []):
                    if kk < 1:
                        continue
                    got = call(second, k=kk, share=0.25)
                    if got is None and self._last_outcome(claims, second, kk) == "timeout":
                        call(second, k=kk, flags=True, share=0.75)
        tools = ", ".join(sorted({c["tool"] for c in claims if c.get("tool") not in (None, "python")}))
        if tools:
            self.detail["hw"] = (self.detail["hw"] + "; " if self.detail["hw"] else "") + f"solvers: {tools}"

    def _last_outcome(self, claims: list[dict], tool: str, k: int) -> str | None:
        for c in reversed(claims):
            if c.get("tool") == tool and c.get("k") == k and "outcome" in c:
                return c["outcome"]
        return None

    def _take(self, o: Any, claims: list[dict]) -> int | None:
        """Record a solver outcome; returns the validated HD width on a validated 'yes'."""
        d = self.d
        neutral = d.neutral
        entry = {"tool": o.tool, "k": o.k_reported if o.exact_mode else o.k, "outcome": o.outcome,
                 "flags": o.flags, "run": o.to_json()}
        if o.edges_echoed is not None and o.edges_echoed != len(d):
            self.disagreements.append({"kind": "misparse", "tool": o.tool, "edges_echoed": o.edges_echoed,
                                       "edges": len(d), "run": o.to_json()})
            claims.append(entry)
            return None
        if o.outcome == "no":
            entry["sound"] = not o.flags
            if o.exact_mode:
                entry["sound"] = False
            claims.append(entry)
            return None
        if o.outcome != "yes":
            claims.append(entry)
            return None
        if o.exact_mode and o.k_reported and not o.flags:  # -exact: every k below K was refuted unflagged
            for kk in range(1, o.k_reported):
                claims.append({"tool": o.tool, "k": kk, "sound": True, "outcome": "no", "implied_by_exact": True})
        tree = o.tree
        if tree is None:
            self.disagreements.append({"kind": "no-decomposition", "tool": o.tool, "run": o.to_json()})
            claims.append(entry)
            return None
        dec = Decomposition.from_json(tree).rename(neutral.role_names, neutral.relation_names)
        v = validate(self.h, dec, kind="hd")
        if v.ok:
            self.b["hw"].offer_upper(v.width, o.tool, dec, "hd", v)
            entry["hd"] = v.width
            claims.append(entry)
            self._improve_fhw(dec, "improve-hd")
            return v.width
        kind = demote(v)
        if kind == "ghd" or o.scv:
            vg = validate(self.h, dec, kind="ghd")
            if vg.ok:
                self.b["ghw"].offer_upper(vg.width, f"{o.tool}-demoted", dec, "ghd", vg)
            self.disagreements.append({"kind": "demotion", "tool": o.tool, "k": entry["k"], "scv_printed": o.scv,
                                       "failures": list(v.failures), "ghd_ok": vg.ok, "run": o.to_json()})
        else:
            self.disagreements.append({"kind": "invalid", "tool": o.tool, "k": entry["k"],
                                       "failures": list(v.failures), "run": o.to_json()})
        claims.append(entry)
        return None

    def _resolve(self, claims: list[dict]) -> None:
        b = self.b["hw"]
        hds = [c for c in claims if "hd" in c]
        min_hd = min((c["hd"] for c in hds), default=None)
        if b.upper is not None:
            min_hd = b.upper if min_hd is None else min(min_hd, b.upper)
        best = None
        for c in claims:
            if not c.get("sound") or "k" not in c:
                continue
            if min_hd is not None and c["k"] >= min_hd:
                by = next((x for x in hds if x["hd"] <= c["k"]), None)
                self.disagreements.append({"kind": "refutation-contradicted", "tool": c["tool"], "k": c["k"],
                                           "by": by["tool"] if by else b.upper_method, "hd_width": min_hd,
                                           "refutation": c.get("run"), "decomposition": by.get("run") if by else None})
                continue
            if best is None or c["k"] > best["k"] or (c["k"] == best["k"] and c["tool"] == "python"):
                best = c
        if best is not None:
            method = "hd-search" if best["tool"] == "python" else f"refutation:{best['tool']}"
            b.raise_lower(best["k"] + 1, method)
        # solver against solver: a validated HD of width w and a sound refutation at k >= w were logged above;
        # solver yes/no at the same k disagreeing without a validated decomposition are logged here
        by_k: dict[int, dict[str, set]] = {}
        for c in claims:
            if c.get("outcome") in ("yes", "no") and c.get("k") is not None and not c.get("flags"):
                by_k.setdefault(c["k"], {}).setdefault(c["outcome"], set()).add(c["tool"])
        for k, answers in sorted(by_k.items()):
            if "yes" in answers and "no" in answers:
                if not any(dd.get("kind") == "refutation-contradicted" and dd.get("k") == k
                           for dd in self.disagreements):
                    self.disagreements.append({"kind": "yes-no", "k": k, "yes": sorted(answers["yes"]),
                                               "no": sorted(answers["no"])})

    def _induced_hw(self) -> None:
        b = self.b["hw"]
        c = self.core
        pool = c.edges if c is not None and c.edges else dict(self.d.edges)
        adj = primal(pool)
        deg = {v: sum(1 for e in pool.values() if v in e) for v in adj}
        hx = None
        x: frozenset = frozenset()
        for size in range(INDUCED_ROLES, 2, -2):
            x = grow_induced(adj, deg, size)
            hx = self.h.induced(x).distinct()
            if len(hx) <= HD_SEARCH_RELATIONS:
                break
        if hx is None or len(hx) > HD_SEARCH_RELATIONS or not x:
            self.log.add(measure="hw", method="induced-hd-search", outcome="skipped",
                         detail=f"no induced set with <= {HD_SEARCH_RELATIONS} distinct traces")
            return
        k = max(2, int(b.lower))
        while k <= K_MAX:
            budget = Budget(HD_SEARCH_BUDGET)
            outcome, res = self.step(lambda dl: hd_search(hx, k, budget=budget, deadline=dl), measure="hw",
                                     method="induced-hd-search", k=k, detail=f"{len(x)} roles")
            if outcome != "done":
                return
            if res is None:
                b.raise_lower(k + 1, "induced-hd-search")
                k += 1
                continue
            return


def _exact_small(edges: list[tuple[str, frozenset]], measure: str, dl: Deadline) -> Any:
    """Exact ghw or fhw of a small hypergraph (its own core, blocks, DP); 1 when alpha-acyclic."""
    hx = Hypergraph(tuple(edges)).distinct()
    if hx.is_empty():
        return None
    cx = core(hx)
    if not cx.edges:
        return 1 if measure == "ghw" else Fraction(1)
    best: Any = 0
    for blk in cx.blocks:
        be = cx.block_edges(blk)
        verts = sorted(blk)
        adj = {v: set() for v in verts}
        adj.update({v: n & blk for v, n in primal(be).items()})
        cost = rho_cost(verts, be, dl) if measure == "ghw" else rho_star_cost(verts, be, dl)
        val, _ = dp_width(verts, adj, cost, dl)
        best = max(best, val)
    return best


# ------------------------------------------------------------------------------------------------ public API
def _tools_block(tools: Mapping[str, Any]) -> dict[str, Any]:
    try:
        from importlib.metadata import version

        kc = version("khg-contracts")
    except Exception:  # pragma: no cover - metadata missing
        kc = "unknown"
    out: dict[str, Any] = {"khg_width": __version__, "khg_contracts": kc, "python": platform.python_version(),
                           "machine": {"platform": platform.platform(), "processor": platform.processor() or
                                       platform.machine(), "cpus": os.cpu_count()}}
    for name, info in tools.items():
        out[name] = info.to_json()
    return out


def check(schema: Any, *, slots: Sequence[str] = HEADLINE_SLOTS, time_limit: float = DEFAULT_TIME_LIMIT,
          solver: str = "auto", seed: int = SEED) -> WidthReport:
    """Class and widths of a schema file (``.json`` / ``.json.gz``), mapping or ``Schema``.

    Raises ``UsageError`` (bad slots, limit or solver; a requested solver missing), ``SchemaInvalid`` (the document
    fails layers J, V or M) and ``OSError`` (the file cannot be read)."""
    from khg_contracts.schema import schema_hypergraph

    t0 = time.monotonic()
    sl = check_slots(slots)
    limit = _check_limit(time_limit)
    tools = _tools_for(solver)
    s, src = read_schema(schema)
    hg = schema_hypergraph(s, slots=sl)
    h = Hypergraph.from_mapping(hg["hyperedges"])
    acy = classify(h)
    r = _Run(h, acy, time_limit=limit, solver=solver, seed=seed, tools=tools)
    widths = r.run()
    info = {"id": s.id, "version": s.version, "sha256": s.sha256, "file_sha256": src.file_sha256,
            "path": src.path, "label": s.doc.get("label")}
    stats = dict(h.stats)
    c = r.core
    stats["core_roles"] = c.summary["core_roles"] if c is not None else 0
    stats["core_relations"] = c.summary["core_relations"] if c is not None else 0
    return WidthReport(schema=info, slots=sl, stats=stats, acyclicity=acy, widths=widths, reductions=r.reductions,
                       disagreements=r.disagreements, tools=_tools_block(tools), time_limit=limit, solver=solver,
                       seed=seed, wall_seconds=time.monotonic() - t0)


def width(h: Hypergraph, measure: str, *, time_limit: float = DEFAULT_TIME_LIMIT, solver: str = "auto",
          seed: int = SEED) -> Width:
    """One measure of a hypergraph (no cross-measure propagation beyond what that measure's own pipeline uses)."""
    if measure not in MEASURES:
        raise UsageError(f"measure must be one of {', '.join(MEASURES)}")
    limit = _check_limit(time_limit)
    tools = _tools_for(solver)
    r = _Run(h, classify(h), time_limit=limit, solver=solver, seed=seed, tools=tools)
    return r.run(measures=(measure,))[measure]


def check_hypergraph(h: Hypergraph, *, time_limit: float = DEFAULT_TIME_LIMIT, solver: str = "auto",
                     seed: int = SEED) -> tuple[Acyclicity, dict[str, Width], list[dict]]:
    """Class, the four widths (propagated) and the disagreements of a ``Hypergraph`` given directly."""
    limit = _check_limit(time_limit)
    tools = _tools_for(solver)
    acy = classify(h)
    r = _Run(h, acy, time_limit=limit, solver=solver, seed=seed, tools=tools)
    return acy, r.run(), r.disagreements
