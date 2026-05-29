"""@api — G-A4 / INV-LC-2: promoting a ticket to community_visible exposes a CURATED
SNAPSHOT frozen at promotion, not the live thread. A private reply added after
promotion must not reach a community-only viewer nor the public KB search; reopening
re-gates to private."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore, TicketComment
from scree.servicedesk.store import TicketStore

AGENT = "agent:dani"


def _ctx():
    store = TicketStore()
    comments = CommentStore()
    authority = TicketAuthority(FakeOpenFga(), agents={AGENT})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority, comment_store=comments,
        allow_insecure_header_auth=True,
    )
    return TestClient(app), comments


def _promoted_ticket(client):
    tid = client.post(
        "/tickets", json={"origin": "web", "body": "original answer"},
        headers={"X-Spike-User": "cust-okafor"},
    ).json()["id"]
    client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers={"X-Spike-User": AGENT})
    client.post(f"/tickets/{tid}/community-visible", headers={"X-Spike-User": AGENT})
    return tid


def test_post_promotion_private_reply_does_not_leak_to_community_viewer():
    client, comments = _ctx()
    tid = _promoted_ticket(client)
    # A private follow-up added AFTER promotion (e.g. an agent's later note).
    comments.add(TicketComment(ticket_id=tid, author=AGENT, body="PRIVATE followup", source="api"))

    # A community-only viewer sees ONLY the frozen snapshot — never the live thread.
    seen = client.get(f"/tickets/{tid}/comments", headers={"X-Spike-User": "cust-stranger"}).json()
    assert seen == [{"author": "cust-okafor", "body": "original answer", "source": "api"}]
    assert all("PRIVATE followup" not in c["body"] for c in seen)

    # A participant (the agent) still sees the live thread including the later reply.
    live = client.get(f"/tickets/{tid}/comments", headers={"X-Spike-User": AGENT}).json()
    assert any(c["body"] == "PRIVATE followup" for c in live)


def test_post_promotion_private_reply_is_not_searchable_in_public_kb():
    client, comments = _ctx()
    tid = _promoted_ticket(client)
    comments.add(TicketComment(ticket_id=tid, author=AGENT, body="PRIVATE followup", source="api"))

    assert client.get("/community/search", params={"q": "PRIVATE"},
                      headers={"X-Spike-User": "cust-stranger"}).json() == []
    # the curated snapshot content is still searchable
    assert client.get("/community/search", params={"q": "original"},
                      headers={"X-Spike-User": "cust-stranger"}).json() == [{"id": tid}]


def test_reopen_re_gates_community_visible_to_private():
    client, _ = _ctx()
    tid = _promoted_ticket(client)
    assert client.get(f"/tickets/{tid}", headers={"X-Spike-User": "cust-stranger"}).status_code == 200
    client.patch(f"/tickets/{tid}", json={"status": "open"}, headers={"X-Spike-User": AGENT})
    # re-gated: no longer visible to a non-participant, snapshot discarded
    assert client.get(f"/tickets/{tid}", headers={"X-Spike-User": "cust-stranger"}).status_code == 404
