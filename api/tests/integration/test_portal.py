"""@api — external customer portal backend (portal.feature). Community KB search
returns only community_visible tickets (never private); self-service notification
preferences; reply attachments stored in object storage, not Git. (The React portal
UI itself is out of scope for this backend spike, ADR-0003.)"""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore, TicketComment
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

CUST = "ext-okafor"


def _ctx():
    # Two resolved tickets: one community_visible, one not.
    store = TicketStore([
        Ticket(id="ticket-pub", requester=CUST, status="resolved", community_visible=True),
        Ticket(id="ticket-priv", requester="ext-other", status="resolved", community_visible=False),
    ])
    comments = CommentStore()
    comments.add(TicketComment(ticket_id="ticket-pub", author="agent:dani", body="how to reset your API key"))
    comments.add(TicketComment(ticket_id="ticket-priv", author="agent:dani", body="secret API key steps"))
    authority = TicketAuthority(FakeOpenFga(), agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority, comment_store=comments,
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store


def test_community_search_returns_only_community_visible():
    client, _ = _ctx()
    hits = client.get("/community/search", params={"q": "API key"},
                      headers={"X-Spike-User": CUST}).json()
    ids = {h["id"] for h in hits}
    assert ids == {"ticket-pub"}  # ticket-priv (not community_visible) NEVER appears
    assert "requester" not in (hits[0] if hits else {})  # requester not disclosed


def test_community_search_excludes_non_matching():
    client, _ = _ctx()
    hits = client.get("/community/search", params={"q": "nonexistent term"},
                      headers={"X-Spike-User": CUST}).json()
    assert hits == []


def test_self_service_notification_preferences_roundtrip():
    client, _ = _ctx()
    assert client.get("/portal/preferences", headers={"X-Spike-User": CUST}).json()["preference"] is None
    put = client.put("/portal/preferences", json={"preference": "on assignment and resolution"},
                     headers={"X-Spike-User": CUST})
    assert put.json()["preference"] == "on assignment and resolution"
    got = client.get("/portal/preferences", headers={"X-Spike-User": CUST}).json()
    assert got["preference"] == "on assignment and resolution"


def test_attachment_stored_in_object_storage_not_git():
    client, _ = _ctx()
    # The requester can attach to their own (community) ticket.
    resp = client.post("/tickets/ticket-pub/attachments",
                       json={"filename": "screenshot.png", "content": "PNGDATA"},
                       headers={"X-Spike-User": CUST})
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "screenshot.png"
    assert body["object_key"].startswith("obj://")  # object storage, not a Git path
    listed = client.get("/tickets/ticket-pub/attachments", headers={"X-Spike-User": CUST}).json()
    assert [a["filename"] for a in listed] == ["screenshot.png"]


def test_attachment_requires_ticket_visibility():
    client, _ = _ctx()
    # A stranger cannot attach to a private ticket they can't see (404, leak-safe).
    resp = client.post("/tickets/ticket-priv/attachments",
                       json={"filename": "x.png", "content": "d"},
                       headers={"X-Spike-User": "stranger"})
    assert resp.status_code == 404
