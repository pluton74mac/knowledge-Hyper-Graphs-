"""Optional external hypertree-decomposition solvers (DESIGN §3.5, §4.5): BalancedGo (primary, DetK mode) and
log-k-decomp (second opinion). They are never imported or started by ``import khg_width``; ``find_solvers`` only
looks for the binaries."""
from __future__ import annotations

from .discovery import SolverInfo, find_solvers

__all__ = ["SolverInfo", "find_solvers"]
