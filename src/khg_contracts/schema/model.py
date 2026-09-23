"""``Schema``: a relation-type schema document (``khg-relation-schema/1.0.0``) with its built-in parts (DESIGN §3).

``Schema(doc)`` does not check the document; ``load_schema`` does (layers J, V and M) and returns a ``Schema``.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .. import jsonio
from ..errors import ValidationError, make_finding
from .builtins import DEFAULT_POLICY, DEFAULT_TIME, END_CAUSE, PROBABILITY, lifecycle_relations

__all__ = ["Schema"]


def _missing(code: str, path: str, message: str) -> ValidationError:
    return ValidationError.from_findings([make_finding(code, path, message)])


class Schema:
    """A relation-type schema: the document plus the lifecycle relations and ``khg:end_cause`` built into it.

    ``sha256`` is ``digest("khg-schema/1", document)``, the value C1 headers, HIF metadata and queue headers pin
    (D009). The document is copied on construction; treat ``doc`` as read-only.
    """

    def __init__(self, doc: Mapping[str, Any]):
        self._doc: dict[str, Any] = copy.deepcopy(dict(doc))
        self._sha256 = jsonio.digest("khg-schema/1", self._doc)
        self._user_ids = [r["id"] for r in self._doc.get("relations", [])]
        self._rel: dict[str, dict[str, Any]] = {r["id"]: r for r in self._doc.get("relations", [])}
        self._rel.update(lifecycle_relations())
        self._types: dict[str, list[str]] = {t["id"]: list(t.get("parents", []))
                                             for t in self._doc.get("entity_types", [])}
        self._scales = {s["id"]: s for s in self._doc.get("confidence_scales", [])}
        self._usages: dict[str, dict[str, dict[str, Any]]] = {}
        self._usage_lists: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------ identity
    @property
    def doc(self) -> dict[str, Any]:
        """The schema document as loaded (do not mutate it)."""
        return self._doc

    @property
    def id(self) -> str:
        return self._doc["id"]

    @property
    def version(self) -> str:
        return self._doc["version"]

    @property
    def label(self) -> str | None:
        return self._doc.get("label")

    @property
    def ref(self) -> str:
        """``"<id>/<version>"``, the form ``typed_under`` uses."""
        return f"{self.id}/{self.version}"

    @property
    def sha256(self) -> str:
        """``digest("khg-schema/1", document)``."""
        return self._sha256

    @property
    def header(self) -> dict[str, str]:
        """The ``{id, version, sha256}`` block of a C1 header or a queue header."""
        return {"id": self.id, "version": self.version, "sha256": self.sha256}

    @property
    def default_time(self) -> dict[str, Any]:
        return copy.deepcopy(self._doc.get("default_time", DEFAULT_TIME))

    # ------------------------------------------------------------------ vocabulary
    @property
    def roles(self) -> list[str]:
        """The global role vocabulary (F4), in document order; the built-in ``khg:`` roles are not listed."""
        return [r["id"] for r in self._doc.get("roles", [])]

    @property
    def entity_types(self) -> dict[str, list[str]]:
        """Entity type id -> parent ids."""
        return {t: list(ps) for t, ps in self._types.items()}

    def is_subtype(self, t: str, want: str) -> bool:
        """True when entity type ``t`` is ``want`` or a descendant of it."""
        seen: set[str] = set()
        stack = [t]
        while stack:
            x = stack.pop()
            if x == want:
                return True
            if x in seen:
                continue
            seen.add(x)
            stack.extend(self._types.get(x, []))
        return False

    def confidence_scale(self, scale_id: str) -> dict[str, Any] | None:
        """A declared confidence scale, or the built-in ``probability``; None when undeclared (S010)."""
        if scale_id == "probability":
            return dict(PROBABILITY)
        s = self._scales.get(scale_id)
        return copy.deepcopy(s) if s is not None else None

    # ------------------------------------------------------------------ relations and usages
    def relation_ids(self, *, builtins: bool = False) -> list[str]:
        """The schema's relations in document order; with ``builtins=True`` the lifecycle relations follow."""
        ids = list(self._user_ids)
        if builtins:
            ids += [r for r in lifecycle_relations() if r not in ids]
        return ids

    def has_relation(self, rel: str) -> bool:
        return rel in self._rel

    def relation(self, rel: str) -> dict[str, Any]:
        """The relation declaration (built-ins included; read-only); raises ``ValidationError`` S001 when
        undeclared."""
        try:
            return self._rel[rel]
        except KeyError:
            raise _missing("KHG-S001", "/relation", f"relation {rel!r} is not declared in {self.ref}") from None

    def kind(self, rel: str) -> str:
        """``"fact"`` or ``"lifecycle"``."""
        return self.relation(rel).get("kind", "fact")

    def reasons(self, rel: str) -> list[str]:
        """The reason list of a lifecycle relation (S026); [] for other relations."""
        return list(self.relation(rel).get("reasons", []))

    def time_model(self, rel: str) -> dict[str, Any]:
        """The relation's time model: its own, else the schema's ``default_time`` (``timeless`` unless set)."""
        r = self.relation(rel)
        if r.get("kind") == "lifecycle":
            return dict(DEFAULT_TIME)
        return copy.deepcopy(r.get("time", self._doc.get("default_time", DEFAULT_TIME)))

    def _usage_index(self, rel: str) -> dict[str, dict[str, Any]]:
        index = self._usages.get(rel)
        if index is None:
            us = list(self.relation(rel)["roles"])
            if self.time_model(rel).get("model") == "interval" and all(u["role"] != "khg:end_cause" for u in us):
                us.append(copy.deepcopy(END_CAUSE))
            index = {}
            for u in us:
                index.setdefault(u["role"], u)
            self._usages[rel] = index
            self._usage_lists[rel] = us
        return index

    def usages(self, rel: str) -> list[dict[str, Any]]:
        """The relation's role usages in schema order; an interval relation also gets the built-in
        ``khg:end_cause`` meta usage. The usage dicts are shared: treat them as read-only."""
        self._usage_index(rel)
        return list(self._usage_lists[rel])

    def usage(self, rel: str, role: str) -> dict[str, Any]:
        """The usage of ``role`` in ``rel``; raises ``ValidationError`` S001 (relation) or S002 (role)."""
        u = self._usage_index(rel).get(role)
        if u is None:
            raise _missing("KHG-S002", "/role", f"role {role!r} is not allowed for {rel!r}")
        return u

    def slot(self, rel: str, role: str) -> str:
        """The slot class of ``role`` in ``rel``: core, qualifier, time or meta."""
        return self.usage(rel, role)["slot"]

    def key(self, rel: str) -> dict[str, Any] | None:
        """The relation's key with its defaults filled (``temporal`` false, ``on_collision`` dispute), or None."""
        k = self.relation(rel).get("key")
        if not k:
            return None
        return {"roles": list(k["roles"]), "temporal": bool(k.get("temporal", False)),
                "on_collision": k.get("on_collision", DEFAULT_POLICY)}

    # ------------------------------------------------------------------ comparison
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Schema) and other.sha256 == self.sha256

    def __hash__(self) -> int:
        return hash(self._sha256)

    def __repr__(self) -> str:
        return f"Schema({self._doc.get('id')!r}/{self._doc.get('version')!r}, sha256={self._sha256[:15]}...)"
