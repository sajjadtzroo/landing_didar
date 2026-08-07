"""Unit tests for request-scoped dependencies. get_client_ip is pure given a
request-like object, so no app/DB needed."""

from types import SimpleNamespace

from app.api.deps import get_client_ip


def _req(xff=None, client_host=None):
    headers = {"x-forwarded-for": xff} if xff else {}
    client = SimpleNamespace(host=client_host) if client_host else None
    return SimpleNamespace(headers=headers, client=client)


def test_client_ip_uses_first_forwarded_hop():
    # Behind a proxy the real client is the first XFF entry, not request.client.
    req = _req(xff="1.2.3.4, 10.0.0.1", client_host="10.0.0.1")
    assert get_client_ip(req) == "1.2.3.4"


def test_client_ip_falls_back_to_peer_when_no_header():
    assert get_client_ip(_req(client_host="9.9.9.9")) == "9.9.9.9"


def test_client_ip_none_when_no_header_and_no_client():
    assert get_client_ip(_req()) is None
