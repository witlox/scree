"""@api — Slack :ticket: capture (DD-012/013, INV-SLACK-1, INV-ID-2) at the
Gateway. Bot/agent-only; requester is the captured message's author; the capturer
is recorded; unmapped Slack users are refused; capture is rate-limited."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.integration.slack.capture import CaptureRateLimiter, SlackDirectory
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

OKAFOR = "ext:r.okafor@uni.example.ac"
MAPPING = {"U_OKAFOR": OKAFOR, "U_AGENT": "agent:dani"}


def _ctx(limit=5):
    fga = FakeOpenFga()
    store = TicketStore()
    comments = CommentStore()
    authority = TicketAuthority(fga, agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority, comment_store=comments,
        slack_directory=SlackDirectory(MAPPING),
        slack_rate_limiter=CaptureRateLimiter(limit=limit),
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store, comments, fga


def _capture(client, reactor, author, snapshot="thread text", who="agent:dani"):
    return client.post("/slack/capture",
                       json={"reactor": reactor, "author": author, "snapshot": snapshot},
                       headers={"X-Spike-User": who})


def test_capture_is_bot_only():
    client, *_ = _ctx()
    assert _capture(client, "U_OKAFOR", "U_OKAFOR", who="cust").status_code == 403


def test_reaction_creates_requester_private_draft_from_author():
    client, store, comments, _ = _ctx()
    r = _capture(client, "U_OKAFOR", "U_OKAFOR").json()
    assert r["action"] == "captured"
    t = store.get(r["ticket"])
    assert t.requester == OKAFOR
    assert t.origin == "slack"
    assert t.community_visible is False  # DD-013
    assert [c.body for c in comments.for_ticket(t.id)] == ["thread text"]  # snapshot captured


def test_capturer_recorded_when_capturing_another_members_message():
    # INV-SLACK-1: agent captures Okafor's message → requester=Okafor, capturer=agent.
    client, store, _, _ = _ctx()
    r = _capture(client, "U_AGENT", "U_OKAFOR").json()
    t = store.get(r["ticket"])
    assert t.requester == OKAFOR
    assert t.captured_by == "agent:dani"
    assert t.community_visible is False


def test_unmapped_reactor_is_refused():
    client, store, _, _ = _ctx()
    r = _capture(client, "U_GHOST", "U_OKAFOR").json()
    assert r["action"] == "refused"
    assert "resolve" in r["reason"]
    assert store.all() == []  # no ticket created


def test_capture_is_rate_limited_per_user():
    client, store, _, _ = _ctx(limit=5)
    for _ in range(5):
        assert _capture(client, "U_OKAFOR", "U_OKAFOR").json()["action"] == "captured"
    sixth = _capture(client, "U_OKAFOR", "U_OKAFOR").json()
    assert sixth["action"] == "refused" and sixth["reason"] == "rate limited"
    assert len(store.all()) == 5


def _comments_for(comments, tid):
    return [c.body for c in comments.for_ticket(tid)]


def test_link_ticket_requires_visibility():
    client, store, comments, fga = _ctx()
    # A ticket Okafor can see (requester relation) and one they cannot.
    store.put(Ticket(id="ticket-mine", requester=OKAFOR))
    fga.write(OKAFOR, "requester", "ticket-mine")
    store.put(Ticket(id="ticket-other", requester="ext:someone"))

    ok = client.post("/slack/link-ticket",
                     json={"reactor": "U_OKAFOR", "ticket_id": "ticket-mine", "snapshot": "snap"},
                     headers={"X-Spike-User": "agent:dani"}).json()
    assert ok == {"action": "linked", "ticket": "ticket-mine"}
    assert _comments_for(comments, "ticket-mine") == ["snap"]

    denied = client.post("/slack/link-ticket",
                         json={"reactor": "U_OKAFOR", "ticket_id": "ticket-other", "snapshot": "snap"},
                         headers={"X-Spike-User": "agent:dani"}).json()
    assert denied["action"] == "refused"
    assert _comments_for(comments, "ticket-other") == []
