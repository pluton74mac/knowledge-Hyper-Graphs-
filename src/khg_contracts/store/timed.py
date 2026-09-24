"""``Timed(store)``: a timing proxy for P1's measurements (DESIGN §6.3).

Every call of the fifteen ``Store`` methods goes to the wrapped store and adds one entry to ``calls``:

- ``method``;
- ``args``: ``digest("khg-timed/1", args)``, where ``args`` maps each parameter name of the protocol method to its
  value, defaults filled, with frozensets as sorted lists and ``Where`` as its field dict (an iterator argument,
  such as a streamed ``load``, is not consumed: it enters as ``{"$iterable": <type name>}``);
- ``ns``: the wall time of the call in nanoseconds (``time.perf_counter_ns``);
- ``size``: the size of the result (below); and ``error``, the first code (or the class name) when it raised.

``size`` is the number of records a call returned or wrote: a list's length, a ``get_many`` dict's, the records of
a receipt or a ``khg-json`` export, the versions of a ``LoadReport``, the steps of a walk, the edges of a HIF export,
the record lines of a ``khg-jsonl`` export; 1 or 0 for ``get``; the value of ``degree``. ``iter_records`` is
consumed inside the timing and returned as an iterator over the list. Other attributes pass through untimed.
"""
from __future__ import annotations

import inspect
import time
from dataclasses import fields, is_dataclass
from typing import Any, Callable, Iterator, Mapping

from .. import jsonio
from ..errors import KHGError
from .protocol import METHODS, Store
from .where import Where

__all__ = ["Timed", "args_digest", "result_size"]

_SIGNATURES = {name: inspect.signature(getattr(Store, name)) for name in METHODS}


def _jsonable(x: Any) -> Any:
    if isinstance(x, Where):
        return x.as_dict()
    if x is None or isinstance(x, (str, bool, int, float)):
        return x
    if isinstance(x, Mapping):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (set, frozenset)):
        items = [_jsonable(v) for v in x]
        if all(isinstance(v, str) for v in items):  # a set of ids: sorted as strings (§6.3), as Where.as_dict does
            return sorted(items)
        return sorted(items, key=jsonio.canonical)  # mixed members: by canonical text, a total order
    if is_dataclass(x) and not isinstance(x, type):
        return {f.name: _jsonable(getattr(x, f.name)) for f in fields(x)}
    if hasattr(x, "__iter__"):
        return {"$iterable": type(x).__name__}
    return {"$object": type(x).__name__}


def args_digest(method: str, *args: Any, **kwargs: Any) -> str:
    """``digest("khg-timed/1", {parameter: value})`` of a call of the protocol method ``method``."""
    try:
        bound = _SIGNATURES[method].bind(None, *args, **kwargs)
    except TypeError:  # not the protocol's signature: the store will say so; digest the call as given
        payload: dict[str, Any] = {"args": _jsonable(list(args)), "kwargs": _jsonable(kwargs)}
    else:
        bound.apply_defaults()
        payload = {k: _jsonable(v) for k, v in bound.arguments.items() if k != "self"}
    try:
        return jsonio.digest("khg-timed/1", payload)
    except (TypeError, ValueError):
        return jsonio.digest("khg-timed/1", {k: repr(v) for k, v in payload.items()})


def result_size(method: str, result: Any) -> int:
    """The size of a result (see the module docstring)."""
    if result is None:
        return 0
    if method == "degree" and isinstance(result, int):
        return result
    if method == "get":
        return 1
    if isinstance(result, str):
        return max(0, sum(1 for line in result.split("\n") if line) - 1)
    if isinstance(result, (list, tuple)):
        return len(result)
    if isinstance(result, Mapping):
        if isinstance(result.get("records"), list):
            return len(result["records"])
        if isinstance(result.get("versions"), int):
            return result["versions"]
        if isinstance(result.get("steps"), list):
            return len(result["steps"])
        if isinstance(result.get("edges"), list):
            return len(result["edges"])
        return len(result)
    return 1


class Timed:
    """Wraps a store; ``calls`` lists ``{method, args, ns, size, error?}`` per call, in call order."""

    def __init__(self, store: Any):
        self.store = store
        self.calls: list[dict[str, Any]] = []

    def clear(self) -> None:
        """Forget the recorded calls."""
        self.calls.clear()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.store, name)

    def __repr__(self) -> str:
        return f"Timed({self.store!r}, calls={len(self.calls)})"

    def _call(self, method: str, run: Callable[[], Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        entry: dict[str, Any] = {"method": method, "args": args_digest(method, *args, **kwargs)}
        start = time.perf_counter_ns()
        try:
            result = run()
        except Exception as e:
            entry["ns"] = time.perf_counter_ns() - start
            entry["size"] = 0
            entry["error"] = e.code if isinstance(e, KHGError) and e.code else type(e).__name__
            self.calls.append(entry)
            raise
        entry["ns"] = time.perf_counter_ns() - start
        entry["size"] = result_size(method, result)
        self.calls.append(entry)
        return result

    def _timed(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return self._call(method, lambda: getattr(self.store, method)(*args, **kwargs), args, kwargs)

    def iter_records(self, *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
        records = self._call("iter_records", lambda: list(self.store.iter_records(*args, **kwargs)), args, kwargs)
        return iter(records)

    def info(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("info", *args, **kwargs)

    def put(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("put", *args, **kwargs)

    def apply(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("apply", *args, **kwargs)

    def load(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("load", *args, **kwargs)

    def get(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("get", *args, **kwargs)

    def history(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("history", *args, **kwargs)

    def incident(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("incident", *args, **kwargs)

    def find(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("find", *args, **kwargs)

    def get_many(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("get_many", *args, **kwargs)

    def degree(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("degree", *args, **kwargs)

    def find_by_key(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("find_by_key", *args, **kwargs)

    def supersession_walk(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("supersession_walk", *args, **kwargs)

    def export(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("export", *args, **kwargs)

    def close(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("close", *args, **kwargs)
