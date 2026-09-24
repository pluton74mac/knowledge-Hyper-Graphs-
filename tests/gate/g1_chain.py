"""The G1 hash-seed child (DESIGN §1.2, assertion 7; critique G1-HASHSEED).

Runs C1 -> HIF -> XGI -> HIF -> HyperNetX -> HIF -> C1 for ``fixture.c1.json`` and for its directed slice, and prints
one JSON object: for each file, the digest of the canonical serialisation of every intermediate document
(``hif``, ``after_xgi``, ``after_hnx`` and ``c1``), where a digest is ``"sha256:" + SHA-256(canonical JSON)``.
``tests/gate/test_roundtrip.py`` runs it in five child processes (``PYTHONHASHSEED`` 0-3 and unset) and compares the
output with ``golden-sha256.json``. Sockets are blocked before the package is imported, and the packaged data is
read through importlib.resources.

usage: python tests/gate/g1_chain.py
"""
from __future__ import annotations

import hashlib
import json
import socket
import sys
import warnings


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


def chain_digests() -> dict:
    """The digests of every intermediate document of the G1 chain, for the full fixture and its directed slice."""
    from khg_contracts import data, hif, loaders
    from khg_contracts.schema import load_schema

    c1 = data.load_json("fixture/fixture.c1.json")
    schema = load_schema(data.load_json("fixture/fixture.relation-schema.json"))
    relations = data.load_json("fixture/fixture.directed-slice.hif.json")["metadata"]["khg-slice"]["relations"]
    out = {}
    for name, rels in (("full", None), ("slice", relations)):
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
