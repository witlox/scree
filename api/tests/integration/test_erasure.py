"""@api — GDPR erasure (INV-DP-2, ADR-0006, AR-05): erasure deletes the identity
record (the opaque requester id becomes unresolvable) and purges the subject's
OpenFGA tuples; tickets remain (Git not rewritten). Compliance-role only."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.store import TicketStore

SENDER = "r.okafor@uni.example.ac"
DPO = "dpo:alice"


def _ctx():
    fga = FakeOpenFga()
    identity = IdentityDirectory()
    store = TicketStore()
    authority = TicketAuthority(fga, agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority,
        identity_directory=identity, compliance_principals={DPO},
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store, identity, fga


def _ingest(client):
    raw = f"From: {SENDER}\nSubject: help\nMessage-ID: <m1@x>\n\nbody\n"
    body = {"raw": raw, "verified": True, "sender": SENDER}
    return client.post("/tickets/inbound-email", json=body, headers={"X-Spike-User": "agent:dani"}).json()


def test_purge_user_drops_only_that_users_tuples():
    fga = FakeOpenFga()
    fga.write("ext-a", "requester", "ticket-1")
    fga.write("ext-b", "requester", "ticket-2")
    assert fga.purge_user("ext-a") == 1
    assert fga.list_readable("ext-a") == set()
    assert fga.list_readable("ext-b") == {"ticket-2"}


def test_erasure_is_compliance_only():
    client, *_ = _ctx()
    r = _ingest(client)
    assert client.delete(f"/identities/{r['ticket']}", headers={"X-Spike-User": "agent:dani"}).status_code == 403


def test_erasure_anonymizes_identity_and_purges_relations():
    client, store, identity, fga = _ctx()
    created = _ingest(client)
    opaque = identity.resolve(SENDER)  # the stable id minted at ingest

    # Before: identity resolvable, relation present, ticket owned by opaque id.
    assert identity.email_for(opaque) == SENDER
    assert fga.list_readable(opaque) == {created["ticket"]}
    assert store.get(created["ticket"]).requester == opaque

    resp = client.delete(f"/identities/{opaque}", headers={"X-Spike-User": DPO})
    assert resp.status_code == 200
    assert resp.json()["identity_removed"] is True
    assert resp.json()["relations_purged"] == 1

    # After: identity unresolvable, relations gone, ticket REMAINS (Git untouched)
    # but its opaque requester id is now orphaned/unresolvable.
    assert identity.email_for(opaque) is None
    assert fga.list_readable(opaque) == set()
    assert store.get(created["ticket"]) is not None
    assert store.get(created["ticket"]).requester == opaque


def test_erasure_is_idempotent():
    client, _, identity, _ = _ctx()
    created = _ingest(client)
    opaque = identity.resolve(SENDER)
    client.delete(f"/identities/{opaque}", headers={"X-Spike-User": DPO})
    again = client.delete(f"/identities/{opaque}", headers={"X-Spike-User": DPO}).json()
    assert again["identity_removed"] is False
    assert again["relations_purged"] == 0
