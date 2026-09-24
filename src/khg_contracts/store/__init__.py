"""The C2 store interface ``khg-store/1.0.0`` (DESIGN §6) and its reference store.

- ``Store``: the protocol, nine core and six derived methods; ``StoreBase`` derives the six from the core.
- ``MemoryStore(schema, *, clock=None, capabilities=None, store_id="memory")``: the reference store, with the ten
  capability flags (``FLAGS``), header state and the four atomic events; ``memory_factory(schema, clock)``.
- ``Where``: the read filter (status ``{asserted}``, rank ``{preferred, normal}``, visibility ``{visible}``, kinds
  ``{fact}``, no valid-time filter, the latest versions).
- ``SystemClock``, ``ScenarioClock``; ``Timed(store)``; ``compare_containers(a, b)``.
- ``conformance.run(factory, *, only=None, capabilities=None)``: the 114 scenarios, as an EARL-shaped report.
- The errors of §6.1: ``ValidationError``, ``KeyCollision``, ``VersionError``, ``ConcurrencyError``, ``NotFound``,
  ``CapabilityMissing``.
"""
from __future__ import annotations

import importlib
from types import ModuleType

from ..errors import CapabilityMissing, ConcurrencyError, KeyCollision, NotFound, ValidationError, VersionError
from .base import StoreBase
from .clocks import SCENARIO_START, ScenarioClock, SystemClock, format_timestamp, parse_timestamp
from .compare import compare_containers
from .flags import ALL_FLAGS, DATA_FLAGS, FLAGS, data_flags
from .memory import MemoryStore, memory_factory
from .protocol import (CORE_METHODS, DERIVED_METHODS, INTERFACE_VERSION, METHODS, RECORD_FORMAT, Clock, LoadReport,
                       Pattern, Receipt, Record, Store, StoreInfo, Walk)
from .timed import Timed
from .where import Where

__all__ = [
    "ALL_FLAGS",
    "CORE_METHODS",
    "DATA_FLAGS",
    "DERIVED_METHODS",
    "FLAGS",
    "INTERFACE_VERSION",
    "METHODS",
    "RECORD_FORMAT",
    "SCENARIO_START",
    "CapabilityMissing",
    "Clock",
    "ConcurrencyError",
    "KeyCollision",
    "LoadReport",
    "MemoryStore",
    "NotFound",
    "Pattern",
    "Receipt",
    "Record",
    "ScenarioClock",
    "Store",
    "StoreBase",
    "StoreInfo",
    "SystemClock",
    "Timed",
    "ValidationError",
    "VersionError",
    "Walk",
    "Where",
    "compare_containers",
    "conformance",
    "data_flags",
    "format_timestamp",
    "memory_factory",
    "parse_timestamp",
]


def __getattr__(name: str) -> ModuleType:
    """``conformance`` is imported on first access, so ``import khg_contracts.store`` stays light."""
    if name == "conformance":
        module = importlib.import_module(f"{__name__}.conformance")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
