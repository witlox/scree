"""@api — GDPR erasure (INV-DP-2, ADR-0006, AR-05): erasure deletes the identity
record (opaque requester id becomes unresolvable), purges the subject's OpenFGA
tuples, scrubs the quarantine queue (G5-02), and is recorded as a durable receipt
(G5-03). Tickets remain (Git not rewritten). Compliance-role only."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.quarantine import QuarantineStore
from scree.servicedesk.store import TicketStore

SENDER = "r.okafor@uni.example.ac"
DPO = "dpo:alice"


def _ctx():
    fga = FakeOpenFga()
    identity = IdentityDirectory()
    store = TicketStore()
    quarantine = QuarantineStore()
    authority = TicketAuthority(fga, agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority,
        identity_directory=identity, quarantine_store=quarantine,
        compliance_principals={DPO}, service_principals={"svc:poller"},
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store, identity, fga, quarantine


def _ingest(client, frm=SENDER, verified=True):
    raw = f"From: {frm}\nSubject: help\nMessage-ID: <m1@x>\n\nbody\n"
    body = {"raw": raw, "verified": verified, "sender": frm}
    return client.post("/tickets/inbound-email", json=body, headers={"X-Spike-User": "svc:poller"}).json()


def test_purge_user_drops_only_that_users_tuples():
    fga = FakeOpenFga()
    fga.write("ext-a", "requester", "ticket-1")
    fga.write("ext-b", "requester", "ticket-2")
    assert fga.purge_user("ext-a") == 1
    assert fga.list_readable("ext-a") == set()
    assert fga.list_readable("ext-b") == {"ticket-2"}


def test_erasure_is_compliance_only():
    client, *_ = _ctx()
    created = _ingest(client)
    assert client.delete(f"/identities/{created['ticket']}", headers={"X-Spike-User": "agent:dani"}).status_code == 403


def test_erasure_anonymizes_identity_and_purges_relations():
    client, store, identity, fga, _ = _ctx()
    created = _ingest(client)
    opaque = identity.resolve(SENDER)

    assert identity.email_for(opaque) == SENDER
    assert fga.list_readable(opaque) == {created["ticket"]}

    resp = client.delete(f"/identities/{opaque}", headers={"X-Spike-User": DPO})
    assert resp.status_code == 200
    body = resp.json()
    assert body["identity_removed"] is True and body["relations_purged"] == 1
    assert "Git history" in body["residual"]  # G5-03: residual scope disclosed

    assert identity.email_for(opaque) is None
    assert fga.list_readable(opaque) == set()
    assert store.get(created["ticket"]) is not None  # ticket remains, id orphaned


def test_erasure_scrubs_quarantine_pii():
    # G5-02: an unverified email from the same address leaves PII in quarantine;
    # erasing the customer must scrub it.
    client, _, identity, _, quarantine = _ctx()
    _ingest(client)  # verified → mints the directory mapping for SENDER
    _ingest(client, verified=False)  # unverified → quarantined with claimed_from=SENDER
    assert any(q.claimed_from == SENDER for q in quarantine.all())

    opaque = identity.resolve(SENDER)
    body = client.delete(f"/identities/{opaque}", headers={"X-Spike-User": DPO}).json()
    assert body["quarantine_purged"] == 1
    assert all(q.claimed_from != SENDER for q in quarantine.all())


def test_erasure_writes_durable_receipt():
    # G5-03: a compliance-queryable receipt records who/whom/what.
    client, _, identity, _, _ = _ctx()
    _ingest(client)
    opaque = identity.resolve(SENDER)
    client.delete(f"/identities/{opaque}", headers={"X-Spike-User": DPO})

    assert client.get("/identities/erasures", headers={"X-Spike-User": "cust"}).status_code == 403
    log = client.get("/identities/erasures", headers={"X-Spike-User": DPO}).json()
    assert len(log) == 1
    assert log[0]["subject"] == opaque and log[0]["actor"] == DPO
    assert log[0]["relations_purged"] == 1


def test_erasure_is_idempotent():
    client, _, identity, _, _ = _ctx()
    _ingest(client)
    opaque = identity.resolve(SENDER)
    client.delete(f"/identities/{opaque}", headers={"X-Spike-User": DPO})
    again = client.delete(f"/identities/{opaque}", headers={"X-Spike-User": DPO}).json()
    assert again["identity_removed"] is False and again["relations_purged"] == 0
