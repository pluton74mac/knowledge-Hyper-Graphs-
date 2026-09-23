"""khg-contracts: the shared contracts of the knowledge-hypergraph programme (P2; DESIGN.md).

The subpackages (``record``, ``schema``, ``validate``, ``hif``, ``loaders``, ``store``, ``queue``, ``identity``,
``scorers``, ``migrate``) and modules (``jsonio``, ``errors``, ``examples``, ``cli``) are imported on first attribute
access (PEP 562), so ``import khg_contracts`` stays light and never loads xgi, hypernetx, pandas, numpy or SciPy.
"""
from __future__ import annotations

import importlib
import importlib.util
import pkgutil
from types import MappingProxyType, ModuleType
from typing import Mapping

__version__ = "1.0.0.dev0"

#: Every format id of DESIGN §11.1, and every hash domain, mapped to its version. Stamped into ``StoreInfo`` and into
#: scorer reports so a consumer can record the contracts it used.
CONTRACTS: Mapping[str, str] = MappingProxyType({
    "khg-record": "1.0.0",
    "khg-relation-schema": "1.0.0",
    "khg-hif": "1.0.0",
    "role-convention": "1.0.0",
    "khg-queue": "1.0.0",
    "khg-store": "1.0.0",
    "khg-scenario": "1.0.0",
    "khg-scorers": "1.0.0",
    "khg-c5-io": "1.0.0",
    "khg-c4-items": "0.1.0",
    "khg-render": "1",
    "khg-codes": "1.0.0",
    "khg-malformed-cases": "1.0.0",
    "khg-content-key": "1",
    "khg-core-key": "1",
    "khg-key-digest": "1",
    "khg-event": "1",
    "khg-literal-node": "1",
    "khg-literal-binding": "1",
    "khg-special-node": "1",
    "khg-schema": "1",
    "khg-decision": "1",
    "khg-timed": "1",
})

__all__ = ["CONTRACTS", "__version__"]


def _submodule_names() -> list[str]:
    return sorted(m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith("_"))


def __getattr__(name: str) -> ModuleType:
    """Import ``khg_contracts.<name>`` on first access (PEP 562)."""
    if name.isidentifier() and not name.startswith("_"):
        full = f"{__name__}.{name}"
        if importlib.util.find_spec(full) is not None:
            module = importlib.import_module(full)
            globals()[name] = module
            return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_submodule_names()))
