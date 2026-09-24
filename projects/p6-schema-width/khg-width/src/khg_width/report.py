"""The report of one check (DESIGN §4.2, §4.3): ``Width`` per measure and ``WidthReport``, with JSON and text forms.

Fractions serialise as strings (``"3/2"``, ``"2"``); fhw values are always strings, hw, ghw and tw integers. A
certificate that is the acyclicity join tree is written once, under ``acyclicity.join_tree``, and referenced as
``{"ref": "acyclicity.join_tree"}``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from .acyclicity import Acyclicity
from .decomposition import Decomposition, Validation, frac_str

__all__ = ["Width", "WidthReport", "FORMAT", "MEASURES", "fmt_value"]

FORMAT = "khg-width-report/0.2.0"  # 0.2.0: lower_witness, solver_attempts, the invalid outcome (review F1, F9)
MEASURES = ("hw", "ghw", "fhw", "tw")
KIND_OF = {"hw": "hd", "ghw": "ghd", "fhw": "fhd", "tw": "td"}


def fmt_value(measure: str, x: Any) -> Any:
    if x is None:
        return None
    if measure == "fhw" or isinstance(x, Fraction):
        return frac_str(x)
    return int(x)


@dataclass(frozen=True)
class Width:
    """One measure: ``[lower, upper]`` (``lower_exclusive`` for fhw > 1), the methods, the certificate of the upper
    bound (a decomposition validated on H), its validation and the steps run for this measure."""

    measure: str
    lower: Any
    upper: Any
    lower_exclusive: bool = False
    lower_method: str = ""
    upper_method: str = ""
    certificate: Decomposition | None = None
    validation: Validation | None = None
    steps: tuple = ()
    detail: str = ""
    lower_witness: dict | None = None

    @property
    def exact(self) -> bool:
        return self.upper is not None and not self.lower_exclusive and self.lower == self.upper

    @property
    def value(self) -> Any:
        """The exact value, or None."""
        return self.upper if self.exact else None

    def show(self) -> str:
        """``3`` when exact, else ``[2, 4]`` (``(1, 3/2]`` for an exclusive lower bound)."""
        lo, hi = fmt_value(self.measure, self.lower), fmt_value(self.measure, self.upper)
        if self.exact:
            return str(hi)
        return f"{'(' if self.lower_exclusive else '['}{lo}, {hi}]"

    def to_json(self, join_tree: Decomposition | None = None) -> dict[str, Any]:
        cert: Any = None
        if self.certificate is not None:
            if join_tree is not None and self.certificate is join_tree:
                cert = {"ref": "acyclicity.join_tree", "kind": KIND_OF[self.measure]}
            else:
                cert = {"kind": KIND_OF[self.measure], **self.certificate.to_json(fractional=self.measure == "fhw")}
        return {"measure": self.measure, "lower": fmt_value(self.measure, self.lower),
                "upper": fmt_value(self.measure, self.upper), "lower_exclusive": self.lower_exclusive,
                "exact": self.exact, "lower_method": self.lower_method, "upper_method": self.upper_method,
                "detail": self.detail, "lower_witness": self.lower_witness, "certificate": cert,
                "validation": self.validation.to_json() if self.validation is not None else None,
                "steps": list(self.steps)}


@dataclass(frozen=True)
class WidthReport:
    """The result of ``check``."""

    schema: dict
    slots: tuple
    stats: dict
    acyclicity: Acyclicity
    widths: dict
    reductions: list = field(default_factory=list)
    disagreements: list = field(default_factory=list)
    tools: dict = field(default_factory=dict)
    time_limit: float = 60.0
    solver: str = "auto"
    seed: int = 20260924
    wall_seconds: float = 0.0
    solver_attempts: list = field(default_factory=list)
    solver_budget: dict = field(default_factory=dict)
    format: str = FORMAT

    def to_json(self) -> dict[str, Any]:
        jt = self.acyclicity.join_tree
        return {
            "format": self.format,
            "schema": dict(self.schema),
            "slots": list(self.slots),
            "stats": dict(self.stats),
            "acyclicity": self.acyclicity.to_json(),
            "widths": {m: self.widths[m].to_json(jt) for m in MEASURES if m in self.widths},
            "reductions": list(self.reductions),
            "disagreements": list(self.disagreements),
            "solver_attempts": list(self.solver_attempts),
            "solver_budget": dict(self.solver_budget),
            "tools": dict(self.tools),
            "time_limit": self.time_limit,
            "solver": self.solver,
            "seed": self.seed,
            "wall_seconds": round(self.wall_seconds, 3),
        }

    def text(self) -> str:
        """The human-readable report of DESIGN §4.3."""
        s = self.schema
        sha = (s.get("sha256") or "")
        fsha = s.get("file_sha256")
        head = f"{s.get('id')}/{s.get('version')}  {sha[:13]}…"
        if fsha:
            head += f"  file {fsha[:10]}…"
        lines = [f"schema      {head}  slots {','.join(self.slots)}"]
        a = self.acyclicity
        cls = a.cls if a.first_failed is None else f"{a.cls} ({a.first_failed} fails)"
        lines.append(f"class       {cls}  witness: {_witness_text(a)}")
        for m in MEASURES:
            w = self.widths.get(m)
            if w is None:
                continue
            state = "exact" if w.exact else "bounds"
            lines.append(f"{m:<4} {w.show():<6} {state:<6} {w.detail}")
        if self.reductions:
            lines.append("reductions  " + "; ".join(_reduction_text(r) for r in self.reductions))
        if self.solver_attempts:
            sb = self.solver_budget
            att = ", ".join(f"{a['tool']} k={a['k']}{' flags' if a['flags'] else ''} {a['outcome']}"
                            for a in self.solver_attempts[:8])
            more = f", … ({len(self.solver_attempts)} in all)" if len(self.solver_attempts) > 8 else ""
            lines.append(f"solvers     {att}{more}; {sb.get('used_seconds', 0):.0f} of "
                         f"{sb.get('budget_seconds', 0):.0f} s budget")
        if self.disagreements:
            lines.append(f"disagreements  {len(self.disagreements)} (see --json)")
        st = self.stats
        lines.append(f"size        {st.get('relations')} relations ({st.get('distinct_role_sets')} distinct), "
                     f"{st.get('roles')} roles, rank {st.get('rank')}, max degree {st.get('max_degree')}, "
                     f"BIP {st.get('bip')}, universal {','.join(st.get('universal_roles') or []) or 'none'}")
        return "\n".join(lines)


def _witness_text(a: Acyclicity) -> str:
    w = a.witness
    if w is None:
        return "none (join tree)" if a.cls != "cyclic" else "none"
    if w.kind == "gyo_residue":
        roles = {v for e in w.value for v in e}
        return f"GYO residue, {len(w.value)} relations on {len(roles)} roles"
    if w.kind in ("berge_cycle", "beta_cycle"):
        name = "Berge cycle" if w.kind == "berge_cycle" else "beta-cycle"
        return f"{name} " + "–".join(w.value)
    if w.kind == "gamma_triangle":
        return "gamma-triangle (" + ", ".join(w.value) + ")"
    return f"{w.kind} ({len(w.value)} relations; search budget exhausted)"


def _reduction_text(r: dict) -> str:
    ms = ",".join(r.get("measures", []))
    name = r["reduction"]
    if name == "blocks":
        return f"blocks {r.get('blocks', 0)} [{ms}]"
    if name == "gyo":
        return f"gyo -{r.get('removed_roles', 0)} roles -{r.get('removed_relations', 0)} relations [{ms}]"
    return f"{name} {r.get('removed_roles', 0)} [{ms}]"
