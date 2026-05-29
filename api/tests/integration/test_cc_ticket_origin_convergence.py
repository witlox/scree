"""@api cross-context (INTEGRATOR) — a ticket created from each origin (web, API,
inbound email, Slack capture) normalizes to ONE coherent record through the single
Gateway: status open, private (community_visible False), origin tagged, and an OPAQUE
requester for external origins resolved via the SAME identity directory.

Features exercised: ticket_origins, slack_capture, ticket_lifecycle.
Invariants: INV-DP-1 (opaque requester, no PII in Git), INV-EMAIL-1, INV-SLACK-1, INV-ACC-3.
Seam: surface (web/api/email-poller/slack-bot) → Gateway → servicedesk + o365 + slack
+ identity + access(openfga)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.integration.slack.capture import CaptureRateLimiter, SlackDirectory
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

POLLER = "svc:poller"
EMAIL = "r.okafor@uni.example.ac"
SLACK_AUTHOR_EXT = "ext:r.okafor@uni.example.ac"
SLACK_MAP = {"U_OKAFOR": SLACK_AUTHOR_EXT, "U_AGENT": "agent:dani"}


def _ctx():
    store = TicketStore()
    identity = IdentityDirectory()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), agents={"agent:dani"}),
        comment_store=CommentStore(), identity_directory=identity,
        service_principals={POLLER}, slack_directory=SlackDirectory(SLACK_MAP),
        slack_rate_limiter=CaptureRateLimiter(limit=5), allow_insecure_header_auth=True,
    )
    return TestClient(app), store, identity


def test_every_origin_normalizes_to_one_coherent_record():
    client, store, identity = _ctx()

    web = client.post("/tickets", json={"origin": "web"}, headers={"X-Spike-User": "cust-okafor"}).json()
    api = client.post("/tickets", json={"origin": "api"}, headers={"X-Spike-User": "cust-rivera"}).json()
    email = client.post(
        "/tickets/inbound-email",
        json={"raw": "From: r.okafor@uni.example.ac\r\nSubject: help please\r\n\r\nmy thing is broken",
              "verified": True, "sender": EMAIL},
        headers={"X-Spike-User": POLLER},
    ).json()
    slack = client.post(
        "/slack/capture",
        json={"reactor": "U_AGENT", "author": "U_OKAFOR", "snapshot": "thread text"},
        headers={"X-Spike-User": POLLER},
    ).json()

    ids = {"web": web["id"], "api": api["id"], "email": email["ticket"], "slack": slack["ticket"]}
    assert len(set(ids.values())) == 4  # four distinct, coherent records

    for origin, tid in ids.items():
        t = store.get(tid)
        assert t.status == "open", origin
        assert t.community_visible is False, origin  # default-private regardless of origin
        assert t.origin == origin

    # External origins carry an OPAQUE requester (no PII in Git), resolved from the
    # verified sender / Slack-mapped author via the SAME identity directory.
    assert store.get(ids["email"]).requester == identity.resolve(EMAIL)
    assert store.get(ids["slack"]).requester == identity.resolve(SLACK_AUTHOR_EXT)
    for tid in (ids["email"], ids["slack"]):
        assert "@" not in store.get(tid).requester

    # The create-time requester tuple lets the requester read their own ticket.
    assert client.get(f"/tickets/{ids['web']}", headers={"X-Spike-User": "cust-okafor"}).status_code == 200
