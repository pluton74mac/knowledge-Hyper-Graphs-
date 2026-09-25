"""Import hygiene (DESIGN §4.4): importing khg_width loads no SciPy, linkml or matplotlib and starts no solver."""
from __future__ import annotations

import json
import subprocess
import sys

CODE = """
import json, subprocess, sys
calls = []
real = subprocess.Popen
class Spy(real):
    def __init__(self, *a, **k):
        calls.append(a[0] if a else k.get('args'))
        super().__init__(*a, **k)
subprocess.Popen = Spy
import khg_width
from khg_width import check, hypergraph, classify, width, validate, find_solvers
heavy = sorted(m for m in sys.modules if m.split('.')[0] in ('scipy', 'linkml_runtime', 'matplotlib', 'numpy', 'yaml'))
print(json.dumps({'heavy': heavy, 'popen': [str(c) for c in calls],
                  'check_is_function': callable(check) and not hasattr(check, '__path__'),
                  'version': khg_width.__version__,
                  'runner_loaded': 'khg_width.solvers.runner' in sys.modules}))
"""


def test_import_is_light():
    r = subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["heavy"] == []
    assert out["popen"] == []
    assert out["check_is_function"] is True
    assert out["version"] == "0.1.0"
    assert out["runner_loaded"] is False


def test_public_api_names():
    import khg_width

    for name in ("check", "hypergraph", "classify", "width", "validate", "find_solvers", "Hypergraph", "Acyclicity",
                 "Witness", "Width", "WidthReport", "Decomposition", "Validation"):
        assert hasattr(khg_width, name), name
    import khg_width.check  # noqa: F401  (the submodule must not shadow the function)

    assert callable(khg_width.check) and khg_width.check.__name__ == "check"
    assert khg_width.hypergraph.__name__ == "hypergraph"
