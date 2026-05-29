"""@api — #102 portal reply: a participant (requester/agent) can post a text reply to
their ticket; a community-only viewer cannot (participant boundary, G11-02); oversized
replies are bounded (G8-03)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

AGENT = "agent:dani"


def _ctx():
    store = TicketStore()
    comments = CommentStore()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), agents={AGENT}),
        comment_store=comments, allow_insecure_header_auth=True,
    )
    return TestClient(app), comments


def _new_ticket(client, who="cust-okafor"):
    return client.post("/tickets", json={"origin": "web", "body": "it broke"}, headers={"X-Spike-User": who}).json()["id"]


def test_requester_can_reply_to_own_ticket():
    client, comments = _ctx()
    tid = _new_ticket(client)
    resp = client.post(f"/tickets/{tid}/comments", json={"body": "any update?"}, headers={"X-Spike-User": "cust-okafor"})
    assert resp.status_code == 200
    assert resp.json() == {"author": "cust-okafor", "body": "any update?", "source": "web"}
    assert [c.body for c in comments.for_ticket(tid)] == ["it broke", "any update?"]


def test_community_only_viewer_cannot_reply():
    client, comments = _ctx()
    tid = _new_ticket(client)
    # promote so a stranger can READ it, but a community-only viewer is not a participant
    client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers={"X-Spike-User": AGENT})
    client.post(f"/tickets/{tid}/community-visible", headers={"X-Spike-User": AGENT})
    resp = client.post(f"/tickets/{tid}/comments", json={"body": "spam"}, headers={"X-Spike-User": "cust-stranger"})
    assert resp.status_code == 404  # participant-or-404 (leak-safe), never appended
    assert all(c.body != "spam" for c in comments.for_ticket(tid))


def test_oversized_reply_rejected():
    client, _ = _ctx()
    tid = _new_ticket(client)
    big = "x" * (1_000_001)
    resp = client.post(f"/tickets/{tid}/comments", json={"body": big}, headers={"X-Spike-User": "cust-okafor"})
    assert resp.status_code == 413
