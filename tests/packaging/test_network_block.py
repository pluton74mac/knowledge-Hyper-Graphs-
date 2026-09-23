"""W0: the socket block of tests/conftest.py is active for the whole session (DESIGN §10.5)."""
from __future__ import annotations

import socket
import urllib.error
import urllib.request

import pytest

BLOCKED = "network access is blocked in the khg-contracts tests"


def test_ip_connections_are_refused_before_any_packet():
    with pytest.raises(OSError, match=BLOCKED):
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(OSError, match=BLOCKED):
            s.connect(("127.0.0.1", 9))
        with pytest.raises(OSError, match=BLOCKED):
            s.connect_ex(("127.0.0.1", 9))
    finally:
        s.close()


def test_datagrams_are_refused():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with pytest.raises(OSError, match=BLOCKED):
            s.sendto(b"x", ("127.0.0.1", 9))
    finally:
        s.close()


def test_name_resolution_is_refused():
    with pytest.raises(OSError, match=BLOCKED):
        socket.getaddrinfo("example.org", 443)
    with pytest.raises(OSError, match=BLOCKED):
        socket.gethostbyname("localhost")


def test_urllib_cannot_fetch():
    with pytest.raises(urllib.error.URLError) as exc:
        urllib.request.urlopen("https://raw.githubusercontent.com/HIF-org/HIF-standard/main/README.md", timeout=1)
    assert BLOCKED in str(exc.value.reason)


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="no AF_UNIX on this platform")
def test_local_unix_sockets_still_work():
    a, b = socket.socketpair()
    try:
        a.sendall(b"ping")
        assert b.recv(4) == b"ping"
    finally:
        a.close()
        b.close()
