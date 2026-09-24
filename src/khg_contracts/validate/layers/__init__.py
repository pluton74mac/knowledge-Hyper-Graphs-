"""The layer modules of the validator and the pipeline of each input kind (DESIGN §8.1).

The runner finds layers only through this static table. Every layer letter J V H R P D C S M Q I has a module here,
and a pipeline is the list of module names it runs, in order. Layer D has two modules: ``d_decode`` (HIF to C1) and
``d_container`` (cross-record, container, history and queue rules).

A layer module exposes:

- ``LETTER``: the letter of the codes it checks (a module may also emit another layer's code, §8.1);
- ``OWNER``: the build step of the Implementation plan that implements it;
- ``IMPLEMENTED``: False while the module is a stub that returns no findings;
- ``run(ctx) -> list[finding]``, where ``ctx`` is a ``khg_contracts.validate.context.Context``.

Its owner step fills a stub module and sets ``IMPLEMENTED = True``; neither the runner nor this table changes.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import MappingProxyType, ModuleType
from typing import Mapping

__all__ = ["KINDS", "LAYERS", "PIPELINES", "REGISTRY_PIPELINE", "LayerSpec", "implemented", "letters", "module",
           "spec"]


@dataclass(frozen=True)
class LayerSpec:
    """One layer module: its name in this package, its letter, its owner step and what it checks."""

    name: str
    letter: str
    owner: str
    checks: str


LAYERS: tuple[LayerSpec, ...] = (
    LayerSpec("j", "J", "W4", "strict parse (jsonio): duplicate keys, NaN, a BOM, lone surrogates, big integers, "
                              "a top level that is not an object"),
    LayerSpec("v", "V", "W4", "the version gate: format and khg-profile ids select the schemas"),
    LayerSpec("h", "H", "W6", "the vendored HIF schema, unchanged"),
    LayerSpec("r", "R", "W6", "role-convention 1.0.0, rules 1-4"),
    LayerSpec("p", "P", "W6", "khg-hif-1.0.0.schema.json plus the Python profile checks"),
    LayerSpec("d_decode", "D", "W6", "decoding HIF to C1 (D001-D003, D005, D009; S016 while decoding)"),
    LayerSpec("d_container", "D", "W5", "cross-record, container, history and queue rules"),
    LayerSpec("c", "C", "W4", "khg-record-1.0.0.schema.json on containers, records and payloads"),
    LayerSpec("s", "S", "W4", "a record against its relation-type schema"),
    LayerSpec("m", "M", "W4", "the relation-schema meta-schema plus the Python checks (schema/)"),
    LayerSpec("q", "Q", "W9", "queue structure, the state fold, keys, entity resolution, base and replay"),
    LayerSpec("i", "I", "W11a", "khg-c4-items-0.1.0.schema.json, embedded C1 and memory gold"),
)
_BY_NAME = {s.name: s for s in LAYERS}

#: The input kinds of ``validate(kind=...)`` (§10.2); ``"auto"`` picks one of them from the input.
KINDS = ("record", "container", "hif", "role-convention", "schema", "queue", "item")

#: The modules each kind runs, in order (§8.1). The letters, with repeats dropped, are the registry's pipelines.
PIPELINES: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "record": ("j", "v", "c", "s", "d_container"),
    "container": ("j", "v", "c", "s", "d_container"),
    "hif": ("j", "v", "h", "r", "p", "d_decode", "c", "s", "d_container"),
    "role-convention": ("j", "h", "r"),
    "schema": ("j", "v", "m"),
    "queue": ("j", "v", "q", "c", "s", "d_container"),
    "item": ("j", "v", "i"),
})

#: The registry's name for each kind's pipeline (``error-codes.json``, ``pipelines``).
REGISTRY_PIPELINE: Mapping[str, str] = MappingProxyType({
    "record": "c1", "container": "c1", "hif": "hif", "role-convention": "role-convention",
    "schema": "relation-schema", "queue": "queue", "item": "c4",
})


def spec(name: str) -> LayerSpec:
    """The table entry of a layer module; ``KeyError`` for a name the table does not list."""
    return _BY_NAME[name]


def module(name: str) -> ModuleType:
    """The layer module ``name``, imported on first use."""
    return importlib.import_module(f"{__name__}.{spec(name).name}")


def implemented(name: str) -> bool:
    """False while the layer module is a stub its owner step has not filled."""
    return bool(getattr(module(name), "IMPLEMENTED", False))


def letters(kind: str) -> tuple[str, ...]:
    """The layer letters of a kind's pipeline, in order, without repeats (``hif``: J V H R P D C S)."""
    out: list[str] = []
    for name in PIPELINES[kind]:
        letter = spec(name).letter
        if letter not in out:
            out.append(letter)
    return tuple(out)
