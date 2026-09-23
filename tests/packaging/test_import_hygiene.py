"""W0: importing khg_contracts loads none of xgi, hypernetx, pandas, numpy or SciPy (DESIGN §10.3), and the
subpackages are imported lazily on first access."""
from __future__ import annotations

import json
import subprocess
import sys

HEAVY = ("xgi", "hypernetx", "pandas", "numpy", "scipy")


def _run(code: str) -> dict:
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_import_loads_no_heavy_dependency_and_no_subpackage():
    out = _run(
        "import json, sys\n"
        "import khg_contracts\n"
        f"heavy = sorted(m for m in sys.modules if m.split('.')[0] in {HEAVY!r})\n"
        "subs = sorted(m for m in sys.modules if m.startswith('khg_contracts.'))\n"
        "print(json.dumps({'heavy': heavy, 'subs': subs, 'version': khg_contracts.__version__}))\n")
    assert out["heavy"] == []
    assert out["subs"] == []
    assert out["version"] == "1.0.0.dev0"


def test_every_module_imports_without_a_heavy_dependency():
    out = _run(
        "import importlib, json, pkgutil, sys\n"
        "import khg_contracts\n"
        "names = []\n"
        "for m in pkgutil.walk_packages(khg_contracts.__path__, 'khg_contracts.'):\n"
        "    if m.name.rsplit('.', 1)[-1] == '__main__':\n"
        "        continue\n"
        "    importlib.import_module(m.name)\n"
        "    names.append(m.name)\n"
        f"heavy = sorted(m for m in sys.modules if m.split('.')[0] in {HEAVY!r})\n"
        "print(json.dumps({'heavy': heavy, 'names': names}))\n")
    assert out["heavy"] == []
    assert {"khg_contracts.jsonio", "khg_contracts.errors", "khg_contracts.schema.checks",
            "khg_contracts.examples", "khg_contracts.cli", "khg_contracts.data"} <= set(out["names"])


def test_attribute_access_imports_a_subpackage_once():
    out = _run(
        "import json, sys\n"
        "import khg_contracts\n"
        "before = 'khg_contracts.schema' in sys.modules\n"
        "s = khg_contracts.schema\n"
        "print(json.dumps({'before': before, 'after': 'khg_contracts.schema' in sys.modules,\n"
        "                  'same': s is sys.modules['khg_contracts.schema'], 'has': hasattr(s, 'load_schema'),\n"
        "                  'dir': [n for n in ('jsonio', 'schema', 'examples', 'cli', 'data')\n"
        "                          if n in dir(khg_contracts)]}))\n")
    assert out == {"before": False, "after": True, "same": True, "has": True,
                   "dir": ["jsonio", "schema", "examples", "cli", "data"]}
