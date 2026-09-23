"""Helpers shared by the scorers (DESIGN §9.1): P/R/F1 with the empty-set flags, exact arithmetic, averages, arity
bins, maximum matchings, the report shape and its stamps.

Scores are computed with ``fractions.Fraction`` and written as floats at the end, so a hand-checked value such as
25/48 or 13/100 comes out as the nearest double, whatever the order of the inputs.
"""
from __future__ import annotations

import dataclasses
from fractions import Fraction
from typing import Any, Callable, Iterable, Mapping, Sequence, Union

from .. import CONTRACTS
from ..record import arity as _arity
from ..record import arity_bin, content_bindings, value_kind
from ..schema import Schema, load_schema

__all__ = [
    "FLAGS",
    "Number",
    "as_schema",
    "config_dict",
    "fnum",
    "frac",
    "mean",
    "prf",
    "prf_split",
    "report",
    "arity_pair",
    "bins_of",
    "model_arity",
    "count_matching",
    "matching",
    "sort_key",
]

#: The empty-set flags of R05 §1 item 3.
FLAGS = ("no_predictions", "no_gold", "both_empty")
Number = Union[int, Fraction]  # noqa: UP007 (a runtime alias)


def as_schema(schema: Any) -> Schema:
    """A ``Schema`` from a ``Schema``, a schema document or a path (``load_schema`` checks documents)."""
    if schema is None:
        raise ValueError("this scorer needs the relation-type schema (schema=...)")
    return load_schema(schema)


def frac(x: Any) -> Fraction:
    """An exact number: ints and Fractions as they are, floats by their shortest decimal form (0.95 is 19/20)."""
    if isinstance(x, bool):
        raise ValueError(f"a number is expected, not {x!r}")
    if isinstance(x, (int, Fraction)):
        return Fraction(x)
    if isinstance(x, float):
        return Fraction(repr(x))
    raise ValueError(f"a number is expected, not {type(x).__name__}")


def fnum(x: Any) -> Any:
    """A Fraction as a float (the nearest double); None, ints and floats as they are."""
    return float(x) if isinstance(x, Fraction) else x


def mean(values: Sequence[Number]) -> Fraction | None:
    """The exact mean, or None for no values."""
    return Fraction(sum(values, Fraction(0))) / len(values) if values else None


def prf_split(tp_pred: Number, n_pred: int, tp_gold: Number, n_gold: int) -> dict[str, Any]:
    """P = tp_pred/n_pred, R = tp_gold/n_gold and their harmonic mean, with the flags of R05 §1: no predictions
    gives P = 0 (``no_predictions``), no gold gives R = 0 (``no_gold``), both empty give P = R = F1 = 1
    (``both_empty``). Returns exact Fractions."""
    if n_pred == 0 and n_gold == 0:
        one = Fraction(1)
        return {"p": one, "r": one, "f1": one, "flag": "both_empty"}
    p = Fraction(tp_pred) / n_pred if n_pred else Fraction(0)
    r = Fraction(tp_gold) / n_gold if n_gold else Fraction(0)
    f1 = 2 * p * r / (p + r) if p + r else Fraction(0)
    flag = "no_predictions" if n_pred == 0 else "no_gold" if n_gold == 0 else None
    return {"p": p, "r": r, "f1": f1, "flag": flag}


def prf(tp: Number, n_pred: int, n_gold: int) -> dict[str, Any]:
    """``{p, r, f1, tp, n_pred, n_gold, flag}`` as floats (see ``prf_split``)."""
    out = prf_split(tp, n_pred, tp, n_gold)
    return {"p": float(out["p"]), "r": float(out["r"]), "f1": float(out["f1"]), "tp": fnum(tp),
            "n_pred": n_pred, "n_gold": n_gold, "flag": out["flag"]}


def _plain(x: Any) -> Any:
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        return {f.name: _plain(getattr(x, f.name)) for f in dataclasses.fields(x)}
    if isinstance(x, (frozenset, set)):
        return sorted(_plain(v) for v in x)
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, Mapping):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, Fraction):
        return float(x)
    return x


def config_dict(config: Any) -> dict[str, Any]:
    """A scorer configuration as JSON (frozensets become sorted lists)."""
    return _plain(config)


def report(scorer: str, config: Any, *, aggregate: Mapping[str, Any], breakdowns: Mapping[str, Any],
           items: Mapping[str, Any], bootstrap: Any, qsets: Iterable[str] = (),
           schema: Schema | Mapping[str, Any] | None = None, **stamps: Any) -> dict[str, Any]:
    """``{scorer, config, contracts, aggregate, breakdowns, items, bootstrap}`` (DESIGN §9.2). ``config`` holds the
    scorer configuration plus the stamps of §9.1: ``qset`` (the C4 question sets read, sorted) and ``schema``
    (``{id, version, sha256}``)."""
    cfg = config_dict(config)
    cfg["qset"] = sorted(set(qsets))
    if isinstance(schema, Schema):
        cfg["schema"] = schema.header
    else:
        cfg["schema"] = dict(schema) if schema else None
    cfg.update(_plain(stamps))
    return {"scorer": scorer, "config": cfg, "contracts": dict(CONTRACTS), "aggregate": _plain(aggregate),
            "breakdowns": _plain(breakdowns), "items": _plain(items), "bootstrap": _plain(bootstrap)}


# ------------------------------------------------------------------------------------------------ arity


def model_arity(record: Mapping[str, Any], schema: Schema) -> int:
    """The bindings a literal-free projection keeps (DESIGN §2.4, §9.1): the core and qualifier bindings whose value
    is not a literal."""
    return sum(1 for b in content_bindings(record, schema, ("core", "qualifier"))
               if value_kind(b.get("value")) != "literal")


def arity_pair(record: Mapping[str, Any], schema: Schema) -> tuple[int, int]:
    """``(arity, model_arity)`` of a fact (the C1 rule, then the literal-free count)."""
    return _arity(record, schema)["arity"], model_arity(record, schema)


def bins_of(arity: int, m_arity: int) -> dict[str, str]:
    """The arity bin of both arities."""
    return {"arity": arity_bin(arity), "model_arity": arity_bin(m_arity)}


# ------------------------------------------------------------------------------------------------ matchings


def matching(n_from: int, n_to: int, ok: Callable[[int, int], bool]) -> dict[int, int]:
    """A maximum bipartite matching ``{i: j}`` between ``range(n_from)`` and ``range(n_to)`` under ``ok``, by
    augmenting paths in index order (Kuhn's algorithm, with an explicit stack; deterministic)."""
    edges = [[j for j in range(n_to) if ok(i, j)] for i in range(n_from)]
    owner: list[int | None] = [None] * n_to
    for root in range(n_from):
        if not edges[root]:
            continue
        seen = [False] * n_to
        rows, cols, ptrs = [root], [], [0]  # the path: rows, the columns taken between them, next edge per row
        while rows:
            i = rows[-1]
            if ptrs[-1] == len(edges[i]):
                rows.pop()
                ptrs.pop()
                if cols:
                    cols.pop()
                continue
            j = edges[i][ptrs[-1]]
            ptrs[-1] += 1
            if seen[j]:
                continue
            seen[j] = True
            o = owner[j]
            if o is None:  # a free column: flip the path
                for r, c in zip(rows, cols + [j], strict=True):
                    owner[c] = r
                break
            rows.append(o)
            cols.append(j)
            ptrs.append(0)
    return {i: j for j, i in enumerate(owner) if i is not None}


def count_matching(xs: Sequence[Any], ys: Sequence[Any], ok: Callable[[Any, Any], bool],
                   key: Callable[[Any], Any] | None = None) -> int:
    """The size of a maximum 1:1 matching of ``xs`` with ``ys`` under ``ok``. With ``key``, ``ok`` is equality of
    keys and the count is the multiset intersection."""
    if key is not None:
        counts: dict[Any, int] = {}
        for y in ys:
            k = key(y)
            counts[k] = counts.get(k, 0) + 1
        n = 0
        for x in xs:
            k = key(x)
            if counts.get(k, 0) > 0:
                counts[k] -= 1
                n += 1
        return n
    return len(matching(len(xs), len(ys), lambda i, j: ok(xs[i], ys[j])))


def sort_key(value: Any) -> tuple[int, str]:
    """A total order on optional strings (None first): run and order ids may be absent."""
    return (0, "") if value is None else (1, str(value))
