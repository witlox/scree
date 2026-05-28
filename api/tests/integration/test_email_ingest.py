"""@api — inbound email ingestion at the Gateway (POST /tickets/inbound-email):
agent-only, out-of-band verdict (G4-01), verified-before-attribution (G4-02),
opaque requester (G4-03), numeric-token threading (G4-04), quarantine persistence
(G4-05), size cap (G4-06)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.quarantine import QuarantineStore
from scree.servicedesk.store import TicketStore

SENDER = "r.okafor@uni.example.ac"


def _ctx():
    store = TicketStore()
    comments = CommentStore()
    identity = IdentityDirectory()
    quarantine = QuarantineStore()
    authority = TicketAuthority(FakeOpenFga(), agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority, comment_store=comments,
        identity_directory=identity, quarantine_store=quarantine,
        service_principals={"svc:poller"},
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store, comments, identity, quarantine


def _raw(frm, subject, references="", forged_auth=False):
    headers = [f"From: {frm}", f"Subject: {subject}", "Message-ID: <m1@x>"]
    if references:
        headers.append(f"References: {references}")
    if forged_auth:
        headers.append("Authentication-Results: mx.scree; dmarc=pass")  # attacker-forged
    return "\n".join(headers) + "\n\nthe message body\n"


def _post(client, raw, *, verified=False, sender=None, who="svc:poller"):
    body = {"raw": raw, "verified": verified, "sender": sender}
    return client.post("/tickets/inbound-email", json=body, headers={"X-Spike-User": who})


def test_inbound_email_is_service_principal_only():
    # G6-02: a human agent is NOT a service principal and cannot ingest.
    client, *_ = _ctx()
    assert _post(client, _raw(SENDER, "hi"), verified=True, sender=SENDER, who="agent:dani").status_code == 403
    assert _post(client, _raw(SENDER, "hi"), verified=True, sender=SENDER, who="cust").status_code == 403


def test_new_ticket_requester_is_opaque_not_email():
    # G4-03: the stored requester is the directory's opaque id, never the address.
    client, store, comments, identity, _ = _ctx()
    r = _post(client, _raw(SENDER, "help please"), verified=True, sender=SENDER).json()
    assert r["action"] == "new"
    new = store.get(r["ticket"])
    assert new.requester == identity.resolve(SENDER)
    assert "@" not in new.requester  # no PII in the ticket
    assert comments.for_ticket(new.id)


def test_forged_authentication_results_is_ignored():
    # G4-01: a dmarc=pass header inside the raw message does NOT make it verified;
    # the verdict comes from the (trusted) `verified` flag, here False.
    client, store, _, _, quarantine = _ctx()
    r = _post(client, _raw("attacker@evil.example", "help", forged_auth=True), verified=False).json()
    assert r["action"] == "quarantine"
    assert len(store.all()) == 0  # no ticket created from a forged verdict
    assert len(quarantine.all()) == 1  # G4-05: held for review


def test_unverified_first_contact_is_quarantined_not_attributed():
    # G4-02: no verified sender → never a silently-attributed new ticket.
    client, store, _, _, quarantine = _ctx()
    r = _post(client, _raw(SENDER, "help"), verified=False).json()
    assert r["action"] == "quarantine"
    assert store.all() == []
    assert len(quarantine.all()) == 1


def test_numeric_token_threads_real_ticket():
    # G4-04: a header-less reply quoting the adapter-generated token threads.
    client, store, comments, _, _ = _ctx()
    created = _post(client, _raw(SENDER, "new issue"), verified=True, sender=SENDER).json()["ticket"]
    token = store.get(created).email_token
    assert token.split("-")[1].isdigit()  # numeric, matches [SCREE-NNN]
    reply = _post(client, _raw(SENDER, f"Re: [{token}] more info"), verified=True, sender=SENDER).json()
    assert reply == {"action": "append", "ticket": created}
    assert len(store.all()) == 1  # threaded, not duplicated


def test_spoofed_verified_sender_quarantined():
    # A verified but different sender quoting the token → quarantine (INV-EMAIL-1).
    client, store, _, _, quarantine = _ctx()
    created = _post(client, _raw(SENDER, "new"), verified=True, sender=SENDER).json()["ticket"]
    token = store.get(created).email_token
    r = _post(client, _raw("attacker@evil.example", f"Re: [{token}] gimme"),
              verified=True, sender="attacker@evil.example").json()
    assert r["action"] == "quarantine" and r["ticket"] == created
    assert len(quarantine.all()) == 1


def test_oversized_email_rejected():
    # G4-06: bound the inbound payload.
    client, *_ = _ctx()
    huge = _raw(SENDER, "big") + "x" * 1_000_001
    assert _post(client, huge, verified=True, sender=SENDER).status_code == 413


def test_quarantine_review_endpoint_is_agent_only_and_lists_held_mail():
    client, _, _, _, _ = _ctx()
    _post(client, _raw("attacker@evil.example", "help"), verified=False)
    assert client.get("/tickets/quarantine", headers={"X-Spike-User": "cust"}).status_code == 403
    held = client.get("/tickets/quarantine", headers={"X-Spike-User": "agent:dani"}).json()
    assert len(held) == 1 and held[0]["claimed_from"] == "attacker@evil.example"
