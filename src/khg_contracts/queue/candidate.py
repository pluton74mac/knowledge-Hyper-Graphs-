"""``make_candidate`` (DESIGN §7): a C1 hyperedge as a queue payload.

It sets the id ``cand:<queue_id>.<seq>`` and status ``candidate``, assigns missing bids ``b1``, ``b2``, … in listed
order (the smallest numbers the record does not use), and stamps ``event_hash`` on extracted and inferred evidence
that has none (``khg-event/1`` over the candidate's content key, §2.9; a stored one is never replaced). The result is
in canonical form (``record.normalize``) and carries no store-assigned field (``version``, ``recorded_at``,
``recorded_by``, evidence ``recorded_at``, ``derived``). Nothing is validated: the linter does that.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Mapping

from ..errors import ValidationError, make_finding
from ..record import STORE_FIELDS, normalize, stamp_event_hashes
from ..schema import Schema, load_schema
from .model import cand_id

__all__ = ["make_candidate"]

_BID = re.compile(r"b([1-9][0-9]*)")


def _assign_bids(bindings: list[Any]) -> None:
    used = {int(m.group(1)) for b in bindings if isinstance(b, Mapping) and isinstance(b.get("bid"), str)
            if (m := _BID.fullmatch(b["bid"]))}
    n = 0
    for b in bindings:
        if isinstance(b, dict) and "bid" not in b:
            n += 1
            while n in used:
                n += 1
            b["bid"] = f"b{n}"


def make_candidate(record: Mapping[str, Any], *, queue_id: str, seq: int, schema: Schema | Mapping[str, Any] | str
                   ) -> dict[str, Any]:
    """The candidate payload for ``record`` (a C1 hyperedge) in queue ``queue_id`` with sequence number ``seq``.

    Raises ``ValueError`` for a bad queue id or sequence number, ``ValidationError`` (C002) for a record that is
    not a hyperedge, and the ``record`` errors (S001, S002, C codes) when an event hash must be computed from a
    payload that cannot be read.
    """
    s = load_schema(schema)
    pid = cand_id(queue_id, seq)
    if not isinstance(record, Mapping) or record.get("kind") != "hyperedge":
        kind = record.get("kind") if isinstance(record, Mapping) else type(record).__name__
        raise ValidationError.from_findings([make_finding("KHG-C002", "/kind", f"a candidate is a hyperedge, not "
                                                                                f"{kind!r}")])
    r = copy.deepcopy(dict(record))
    for name in STORE_FIELDS + ("derived",):
        r.pop(name, None)
    evidence = r.get("evidence")
    for e in evidence if isinstance(evidence, list) else []:  # any other evidence is left to the checks (C010)
        if isinstance(e, dict):
            e.pop("recorded_at", None)
    if isinstance(r.get("bindings"), list):
        _assign_bids(r["bindings"])
    r["id"] = pid
    r["status"] = "candidate"
    out = normalize(r, s)
    evidence = out.get("evidence")
    if isinstance(evidence, list) and all(isinstance(e, Mapping) for e in evidence):
        out = stamp_event_hashes(out, s)
    return out
