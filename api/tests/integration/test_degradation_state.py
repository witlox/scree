"""@api — G-A16 / INV-DEG-1: writes refused during a GitLab outage must leave NO state
behind (never silently dropped *or* half-applied). Strengthens the gate-12 status-only
checks for slack_link and migration with assertions that nothing was created."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.platform.health import Availability
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore


def test_slack_link_during_outage_creates_no_comment():
    store = TicketStore([Ticket(id="t-1", requester="ext-1")])
    comments = CommentStore()
    fga = FakeOpenFga()
    fga.write("ext-1", "requester", "t-1")
    client = TestClient(create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(fga, agents=set()),
        comment_store=comments, service_principals={"svc:bot"},
        availability=Availability(gitlab_up=False), allow_insecure_header_auth=True,
    ))
    resp = client.post("/slack/link-ticket",
                       json={"reactor": "u", "ticket_id": "t-1", "snapshot": "s"},
                       headers={"X-Spike-User": "svc:bot"})
    assert resp.status_code == 503
    assert comments.for_ticket("t-1") == []  # nothing appended


def test_migration_during_outage_creates_no_ticket():
    store = TicketStore()
    client = TestClient(create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), agents=set()),
        comment_store=CommentStore(), service_principals={"svc:mig"},
        availability=Availability(gitlab_up=False), allow_insecure_header_auth=True,
    ))
    item = {"kind": "jira", "old_id": "SUP-1", "title": "t", "content": "c", "marked": True}
    resp = client.post("/migration/run", json={"items": [item]}, headers={"X-Spike-User": "svc:mig"})
    assert resp.status_code == 503
    assert store.all() == []  # no partial migration
