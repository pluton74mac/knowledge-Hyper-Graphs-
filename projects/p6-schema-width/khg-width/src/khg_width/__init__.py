"""khg-width: the acyclicity class and hypertree widths of khg-relation-schema/1.0.0 files (P6 DESIGN §4).

Public API (DESIGN §4.2)::

    check(schema, *, slots=("core", "qualifier"), time_limit=60.0, solver="auto", seed=20260924) -> WidthReport
    hypergraph(schema, *, slots=("core", "qualifier")) -> Hypergraph
    classify(h, *, budget=200_000) -> Acyclicity
    width(h, measure, *, time_limit=60.0, solver="auto") -> Width
    validate(h, d, *, kind) -> Validation
    find_solvers() -> dict[str, SolverInfo]

The names are bound here, after their submodules load, so that the functions ``check`` and ``hypergraph`` are not
shadowed by the submodules of the same name. Importing the package starts no solver and loads no SciPy, linkml or
matplotlib (those are imported only where they are used).
"""
from __future__ import annotations

__version__ = "0.1.0"

from .acyclicity import Acyclicity, InternalError, Witness, classify  # noqa: E402
from .check import SOLVER_MODES, check, check_hypergraph, width  # noqa: E402
from .decomposition import Decomposition, Validation, validate  # noqa: E402
from .hypergraph import Hypergraph, SchemaInvalid, UsageError, check_slots, hypergraph, read_schema  # noqa: E402
from .report import Width, WidthReport  # noqa: E402
from .solvers import SolverInfo, find_solvers  # noqa: E402

__all__ = ["Acyclicity", "Decomposition", "Hypergraph", "InternalError", "SOLVER_MODES", "SchemaInvalid",
           "SolverInfo", "UsageError", "Validation", "Width", "WidthReport", "Witness", "__version__", "check",
           "check_hypergraph", "check_slots", "classify", "find_solvers", "hypergraph", "read_schema", "validate",
           "width"]
