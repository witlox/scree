"""@api — inbound email ingestion at the Gateway (POST /tickets/inbound-email):
agent-only, threads on header/token, quarantines spoofed senders (INV-EMAIL-1),
opens a new requester-private ticket when nothing matches."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

MID = "<CA+abc123@mail.uni.example.ac>"
REQ = "ext:r.okafor@uni.example.ac"


def _ctx():
    store = TicketStore([Ticket(
        id="ticket-123", requester=REQ, status="open",
        email_message_id=MID, email_token="SCREE-123",
    )])
    comments = CommentStore()
    authority = TicketAuthority(FakeOpenFga(), agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority, comment_store=comments,
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store, comments


def _raw(frm, subject, references="", verified=True):
    headers = [f"From: {frm}", f"Subject: {subject}"]
    if references:
        headers.append(f"References: {references}")
    if verified:
        headers.append("Authentication-Results: mx.scree; dmarc=pass")
    return "\n".join(headers) + "\n\nthe message body\n"


def _post(client, raw, who="agent:dani"):
    return client.post("/tickets/inbound-email", json={"raw": raw}, headers={"X-Spike-User": who})


def test_inbound_email_is_agent_only():
    client, _, _ = _ctx()
    r = _post(client, _raw("r.okafor@uni.example.ac", "hi"), who="cust-okafor")
    assert r.status_code == 403


def test_header_reply_threads_without_new_ticket():
    client, store, comments = _ctx()
    r = _post(client, _raw("r.okafor@uni.example.ac", "Re: export", references=MID))
    assert r.json() == {"action": "append", "ticket": "ticket-123"}
    assert len(store.all()) == 1  # no duplicate
    assert [c.body for c in comments.for_ticket("ticket-123")] == ["the message body"]


def test_unmatched_email_opens_new_requester_private_ticket():
    client, store, comments = _ctx()
    r = _post(client, _raw("new.person@uni.example.ac", "help please")).json()
    assert r["action"] == "new"
    new = store.get(r["ticket"])
    assert new.origin == "email"
    assert new.requester == "ext:new.person@uni.example.ac"
    assert new.community_visible is False
    assert comments.for_ticket(new.id)  # initial email stored on the thread


def test_spoofed_sender_quarantined_not_appended():
    client, store, comments = _ctx()
    r = _post(client, _raw("attacker@evil.example", "Re: [SCREE-123] gimme")).json()
    assert r["action"] == "quarantine"
    assert r["ticket"] == "ticket-123"
    assert comments.for_ticket("ticket-123") == []  # not appended
    assert len(store.all()) == 1  # not created either
