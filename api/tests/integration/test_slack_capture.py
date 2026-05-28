"""@api — Slack :ticket: capture (DD-012/013, INV-SLACK-1, INV-ID-2) at the
Gateway. Service-principal only (the bot); requester is the captured message's
author resolved to an OPAQUE id; the capturer is recorded; unmapped Slack users
are refused; capture is rate-limited."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.integration.slack.capture import CaptureRateLimiter, SlackDirectory
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

OKAFOR_EXT = "ext:r.okafor@uni.example.ac"  # the Slack→Keycloak mapping value (PII-bearing)
MAPPING = {"U_OKAFOR": OKAFOR_EXT, "U_AGENT": "agent:dani"}
BOT = "svc:bot"


def _ctx(limit=5):
    fga = FakeOpenFga()
    store = TicketStore()
    comments = CommentStore()
    identity = IdentityDirectory()
    authority = TicketAuthority(fga, agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority, comment_store=comments,
        identity_directory=identity, service_principals={BOT},
        slack_directory=SlackDirectory(MAPPING),
        slack_rate_limiter=CaptureRateLimiter(limit=limit),
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store, comments, fga, identity


def _capture(client, reactor, author, snapshot="thread text", who=BOT):
    return client.post("/slack/capture",
                       json={"reactor": reactor, "author": author, "snapshot": snapshot},
                       headers={"X-Spike-User": who})


def test_capture_is_service_principal_only():
    client, *_ = _ctx()
    assert _capture(client, "U_OKAFOR", "U_OKAFOR", who="agent:dani").status_code == 403
    assert _capture(client, "U_OKAFOR", "U_OKAFOR", who="cust").status_code == 403


def test_reaction_creates_requester_private_draft_with_opaque_requester():
    client, store, comments, _, identity = _ctx()
    r = _capture(client, "U_OKAFOR", "U_OKAFOR").json()
    assert r["action"] == "captured"
    t = store.get(r["ticket"])
    assert t.requester == identity.resolve(OKAFOR_EXT)  # opaque (G6-01)
    assert "@" not in t.requester  # no PII in the stored requester
    assert t.origin == "slack"
    assert t.community_visible is False  # DD-013
    assert [c.body for c in comments.for_ticket(t.id)] == ["thread text"]


def test_capturer_recorded_when_capturing_another_members_message():
    client, store, _, _, identity = _ctx()
    r = _capture(client, "U_AGENT", "U_OKAFOR").json()
    t = store.get(r["ticket"])
    assert t.requester == identity.resolve(OKAFOR_EXT)  # author, opaque
    assert t.captured_by == "agent:dani"  # internal agent kept as-is
    assert t.community_visible is False


def test_unmapped_reactor_is_refused():
    client, store, _, _, _ = _ctx()
    r = _capture(client, "U_GHOST", "U_OKAFOR").json()
    assert r["action"] == "refused" and "resolve" in r["reason"]
    assert store.all() == []


def test_capture_is_rate_limited_per_user():
    client, store, _, _, _ = _ctx(limit=5)
    for _ in range(5):
        assert _capture(client, "U_OKAFOR", "U_OKAFOR").json()["action"] == "captured"
    sixth = _capture(client, "U_OKAFOR", "U_OKAFOR").json()
    assert sixth["action"] == "refused" and sixth["reason"] == "rate limited"
    assert len(store.all()) == 5


def test_link_ticket_requires_visibility():
    client, store, comments, fga, identity = _ctx()
    opaque = identity.resolve(OKAFOR_EXT)
    store.put(Ticket(id="ticket-mine", requester=opaque))
    fga.write(opaque, "requester", "ticket-mine")
    store.put(Ticket(id="ticket-other", requester="ext-someone"))

    ok = client.post("/slack/link-ticket",
                     json={"reactor": "U_OKAFOR", "ticket_id": "ticket-mine", "snapshot": "snap"},
                     headers={"X-Spike-User": BOT}).json()
    assert ok == {"action": "linked", "ticket": "ticket-mine"}
    assert [c.body for c in comments.for_ticket("ticket-mine")] == ["snap"]

    denied = client.post("/slack/link-ticket",
                         json={"reactor": "U_OKAFOR", "ticket_id": "ticket-other", "snapshot": "snap"},
                         headers={"X-Spike-User": BOT}).json()
    assert denied["action"] == "refused"
    assert comments.for_ticket("ticket-other") == []
