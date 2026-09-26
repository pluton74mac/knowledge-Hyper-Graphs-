"""The G1 hash-seed child (DESIGN §1.2, assertion 7; critique G1-HASHSEED), and the inputs of the four G1 chains.

Runs C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1 for ``fixture.c1.json`` and for its directed slice, and for
the fixture as a container that is not complete (``incomplete``, ruling 19) and its directed slice, and prints one
JSON object: for each chain, the digest of the canonical serialisation of every intermediate document (``hif``,
``after_xgi``, ``after_hnx`` and ``c1``), where a digest is ``"sha256:" + SHA-256(canonical JSON)``.
``tests/gate/test_roundtrip.py`` runs it in five child processes (``PYTHONHASHSEED`` 0-3 and unset) and compares the
output with ``golden-sha256.json``; it takes the chains' inputs from ``chain_inputs`` here. Sockets are blocked
before the package is imported, and the packaged data is read through importlib.resources.

usage: python tests/gate/g1_chain.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import socket
import sys
import warnings

#: The G1 chains, in the order of ``golden-sha256.json``.
CHAINS = ("full", "slice", "incomplete", "incomplete-slice")
#: What the ``incomplete`` container does not hold (ruling 19): the fixture without these records and without
#: ``complete``, which leaves valid C1 (only a complete container must hold what it names, D002). ``ex:TP53`` is the
#: tail and the head of ``f:reg-1`` and weighs 3; ``ex:YYZ`` is the first and third stop of ``f:route-1`` and both
#: ends of ``f:loop-yyz``; ``ex:KingOfFrance`` is the position of two facts and of the goal ``g:who-1774``; and
#: ``f:claim-1`` names ``f:born-louis14-paris``, whose reference becomes external.
NOT_HELD = ("ex:KingOfFrance", "ex:TP53", "ex:YYZ", "f:born-louis14-paris")


def _block_network() -> None:
    def refuse(*args, **kwargs):
        raise OSError("network access is blocked in the G1 child")

    for name in ("connect", "connect_ex", "sendto", "sendmsg"):
        if hasattr(socket.socket, name):
            setattr(socket.socket, name, refuse)
    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "create_connection"):
        if hasattr(socket, name):
            setattr(socket, name, refuse)


def digest(doc) -> str:
    """The plain SHA-256 of a document's canonical serialisation."""
    from khg_contracts import jsonio
    return "sha256:" + hashlib.sha256(jsonio.canonical(doc).encode("utf-8")).hexdigest()


def incomplete(c1: dict) -> dict:
    """The fixture as a container that is not complete: without the records ``NOT_HELD`` and without ``complete``."""
    c = copy.deepcopy(c1)
    c["records"] = [r for r in c["records"] if r["id"] not in NOT_HELD]
    del c["header"]["complete"]
    return c


def chain_inputs() -> dict:
    """``{chain: (container, relations)}``: the C1 container ``to_hif`` starts from, and the relations of its slice
    (None for the whole container)."""
    from khg_contracts import data

    c1 = data.load_json("fixture/fixture.c1.json")
    relations = data.load_json("fixture/fixture.directed-slice.hif.json")["metadata"]["khg-slice"]["relations"]
    return {"full": (c1, None), "slice": (c1, relations), "incomplete": (incomplete(c1), None),
            "incomplete-slice": (incomplete(c1), relations)}


def chain_digests() -> dict:
    """The digests of every intermediate document of each G1 chain."""
    from khg_contracts import data, hif, loaders
    from khg_contracts.schema import load_schema

    schema = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
    out = {}
    for name, (c1, rels) in chain_inputs().items():
        h0 = hif.to_hif(c1, schema, relations=rels)
        h1 = loaders.export_xgi(loaders.load_xgi(h0))
        h2 = loaders.export_hnx(loaders.load_hnx(h1))
        back = hif.from_hif(h2, schema)
        out[name] = {"hif": digest(h0), "after_xgi": digest(h1), "after_hnx": digest(h2), "c1": digest(back)}
    return out


def main() -> int:
    _block_network()
    warnings.filterwarnings("ignore")
    sys.stdout.write(json.dumps(chain_digests(), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
