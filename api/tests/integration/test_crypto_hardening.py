"""@api/unit — gate-8 crypto hardening: durable crypto required in prod (G8-01),
transient backend failure is not mistaken for crypto-shred (G8-02), comment/body
size is bounded (G8-03)."""

import base64

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import DecryptionUnavailable, VaultTransitCrypto
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.store import TicketStore


class _DummyAuth:  # non-None authenticator sentinel (passes the auth fail-closed guard)
    pass


def _tickets():
    return TicketStore(), TicketAuthority(FakeOpenFga(), agents={"agent:dani"})


# --- G8-01: durable crypto required in prod ----------------------------------

def test_prod_requires_durable_crypto():
    store, authority = _tickets()
    with pytest.raises(ValueError, match="ticket_crypto"):
        create_app(DocStore([]), Authority({}), ticket_store=store, ticket_authority=authority,
                   authenticator=_DummyAuth())  # no insecure flag, no ticket_crypto


def test_dev_flag_allows_in_memory_crypto():
    store, authority = _tickets()
    # Under the dev opt-in, FernetCrypto is permitted (no exception).
    create_app(DocStore([]), Authority({}), ticket_store=store, ticket_authority=authority,
               allow_insecure_header_auth=True)


# --- G8-02: transient vs permanent -------------------------------------------

class _Resp:
    def __init__(self, status):
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"transient {self.status_code}")

    def json(self):
        return {"data": {"plaintext": base64.b64encode(b"secret").decode()}}


class _Client:
    def __init__(self, status):
        self._status = status

    def post(self, *a, **k):
        return _Resp(self._status)


def test_missing_key_is_permanent_unavailable():
    crypto = VaultTransitCrypto("http://vault", "t", client=_Client(400))
    with pytest.raises(DecryptionUnavailable):
        crypto.decrypt("ext-1", "vault:ct")


def test_transient_failure_is_not_reported_as_shredded():
    crypto = VaultTransitCrypto("http://vault", "t", client=_Client(503))
    with pytest.raises(Exception) as ei:
        crypto.decrypt("ext-1", "vault:ct")
    assert not isinstance(ei.value, DecryptionUnavailable)  # retryable, not "erased"


# --- G8-03: bounded comment/body size ----------------------------------------

def test_oversized_ticket_body_rejected():
    store, authority = _tickets()
    client = TestClient(create_app(DocStore([]), Authority({}), ticket_store=store,
                                   ticket_authority=authority, allow_insecure_header_auth=True))
    big = "x" * 1_000_001
    resp = client.post("/tickets", json={"origin": "web", "body": big}, headers={"X-Spike-User": "cust"})
    assert resp.status_code == 413
