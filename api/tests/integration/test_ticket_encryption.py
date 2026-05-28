"""@api — encryption-at-create + crypto-shred (data_protection.feature, ADR-0005/8,
INV-DP-2). An encrypted ticket's body is ciphertext at rest, decrypted only via the
Gateway; encryption is a create-time decision (no retroactive); erasing the customer
crypto-shreds the body."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

DPO = "dpo:alice"
SECRET = "my API key is hunter2"


def _ctx():
    store = TicketStore()
    comments = CommentStore()
    authority = TicketAuthority(FakeOpenFga(), agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority, comment_store=comments,
        identity_directory=IdentityDirectory(), compliance_principals={DPO},
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store, comments


def _create(client, who, encrypt, body=SECRET):
    return client.post("/tickets", json={"origin": "web", "encrypt": encrypt, "body": body},
                       headers={"X-Spike-User": who}).json()


def _comments(client, tid, who="agent:dani"):
    return client.get(f"/tickets/{tid}/comments", headers={"X-Spike-User": who}).json()


def test_encrypted_ticket_body_is_ciphertext_at_rest_but_decrypts_via_gateway():
    client, store, comments = _ctx()
    t = _create(client, "cust", encrypt=True)
    assert store.get(t["id"]).encrypted is True
    stored = comments.for_ticket(t["id"])[0]
    assert stored.encrypted is True
    assert SECRET not in stored.body  # ciphertext at rest — not readable from a raw clone
    # Gateway-mediated decryption returns the plaintext to an authorized agent.
    assert [c["body"] for c in _comments(client, t["id"])] == [SECRET]


def test_cleartext_ticket_stores_plaintext():
    client, store, comments = _ctx()
    t = _create(client, "cust", encrypt=False)
    assert store.get(t["id"]).encrypted is False
    assert comments.for_ticket(t["id"])[0].body == SECRET
    assert [c["body"] for c in _comments(client, t["id"])] == [SECRET]


def test_encryption_is_not_retroactive():
    client, _, _ = _ctx()
    t = _create(client, "cust", encrypt=False)
    resp = client.post(f"/tickets/{t['id']}/encrypt", headers={"X-Spike-User": "agent:dani"})
    assert resp.status_code == 409
    assert "create-time" in resp.json()["detail"]


def test_erasure_crypto_shreds_the_encrypted_body():
    client, store, _ = _ctx()
    t = _create(client, "cust", encrypt=True)
    assert [c["body"] for c in _comments(client, t["id"])] == [SECRET]  # decryptable before erasure

    resp = client.delete("/identities/cust", headers={"X-Spike-User": DPO})
    assert resp.json()["crypto_shredded"] is True

    # After crypto-shred the body is permanently unrecoverable (agent still authorized).
    assert _comments(client, t["id"]) == [{"author": "cust", "body": "[unrecoverable: encryption key erased]", "source": "api"}]
