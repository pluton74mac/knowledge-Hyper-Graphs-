"""P6 probe: run fraSMT (github.com/daajoe/frasmt) under Python 3.11 without editing it.

fraSMT's bundled htd_validate uses ``collections.Iterable``, removed in Python 3.10; this shim restores the alias and
runs ``bin/fhtd`` unchanged. fraSMT also needs clingo, z3 (the ``z3`` executable is passed with ``-s``) and the CPLEX
Python API (``pip install cplex``, IBM's size-limited Community Edition) for its fractional-cover preprocessing.

Usage:  python run_frasmt.py <frasmt-dir> <fhtd args...>
"""
from __future__ import annotations

import collections
import collections.abc
import os
import runpy
import sys

for name in ("Iterable", "Mapping", "MutableMapping", "Sequence"):
    if not hasattr(collections, name):
        setattr(collections, name, getattr(collections.abc, name))

root = os.path.abspath(sys.argv[1])
os.chdir(root)
sys.argv = [os.path.join(root, "bin", "fhtd")] + sys.argv[2:]
runpy.run_path(sys.argv[0], run_name="__main__")
