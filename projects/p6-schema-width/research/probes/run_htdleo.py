"""P6 probe: run HtdLEO / htdsmt's ``sat_runner.py`` under a current PySAT.

HtdLEO (Zenodo 10.5281/zenodo.4742100) and its GitHub successor ASchidler/htdsmt import ``Cadical`` from
``pysat.solvers``; PySAT 1.9 no longer exports that name (it has ``Cadical103`` and ``Cadical153``). This shim adds the
alias and then runs the runner unchanged, so no third-party file is edited.

Usage:  python run_htdleo.py <htdleo-or-htdsmt-dir> <sat_runner.py args...>
"""
from __future__ import annotations

import os
import runpy
import sys

import pysat.solvers as ps

if not hasattr(ps, "Cadical"):
    ps.Cadical = getattr(ps, "Cadical153", None) or getattr(ps, "Cadical103")

root = os.path.abspath(sys.argv[1])
sys.path.insert(0, root)
os.chdir(root)
sys.argv = [os.path.join(root, "sat_runner.py")] + sys.argv[2:]
runpy.run_path(sys.argv[0], run_name="__main__")
