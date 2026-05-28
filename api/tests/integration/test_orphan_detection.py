"""@api — orphan detection (INV-ORPH-1/2). Active risks whose owner lost Space
access are flagged for that Space's maintainers; open tickets whose assignee lost
desk access or are unassigned past the threshold are flagged for desk leads.
Detection never auto-reassigns; the report is filtered to the requester's scope."""

import datetime as dt

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.indexing.orphans import detect_orphans
from scree.knowledge.store import DocStore
from scree.risk.models import Risk
from scree.risk.store import RiskStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

SPACE = "platform/handbook"


def _risk(rid, owner, status="open", space=SPACE):
    return Risk(id=rid, title="t", space=space, category="delivery", likelihood=3,
                impact=3, strategy="mitigated", status=status, owner=owner)


# --- unit: detector logic ----------------------------------------------------

def _detect(risks, tickets, readable, agents, **kw):
    return detect_orphans(risks, tickets, authority=Authority(readable),
                          ticket_authority=TicketAuthority(FakeOpenFga(), agents=agents), **kw)


def test_active_risk_with_owner_lacking_access_is_flagged():
    # j.tan owns an open risk but has no readable spaces (lost access).
    report = _detect([_risk("risk-44", "j.tan")], [], readable={}, agents=set())
    assert report.resources == {SPACE: ["risk-44"]}


def test_closed_risk_is_not_flagged():
    report = _detect([_risk("risk-9", "j.tan", status="closed")], [], readable={}, agents=set())
    assert report.resources == {}


def test_risk_whose_owner_still_has_access_is_not_flagged():
    report = _detect([_risk("risk-44", "rivera")], [], readable={"rivera": {SPACE}}, agents=set())
    assert report.resources == {}


def test_open_ticket_with_departed_assignee_is_flagged():
    t = Ticket(id="ticket-123", requester="ext-1", status="open", assignee="agent:dani")
    # agent:dani is no longer in the agents set (lost desk access).
    report = _detect([], [t], readable={}, agents=set())
    assert report.tickets == ["ticket-123"]


def test_long_unassigned_open_ticket_is_flagged():
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat()
    t = Ticket(id="ticket-200", requester="ext-1", status="open", assignee=None, created_at=old)
    report = _detect([], [t], readable={}, agents=set())
    assert report.tickets == ["ticket-200"]


def test_recent_unassigned_ticket_is_not_flagged():
    fresh = dt.datetime.now(dt.timezone.utc).isoformat()
    t = Ticket(id="ticket-201", requester="ext-1", status="open", assignee=None, created_at=fresh)
    report = _detect([], [t], readable={}, agents=set())
    assert report.tickets == []


# --- @api: endpoint filtering ------------------------------------------------

def _client(risks, tickets, readable, agents):
    return TestClient(create_app(
        DocStore([]), Authority(readable),
        risk_store=RiskStore(risks),
        ticket_store=TicketStore(tickets),
        ticket_authority=TicketAuthority(FakeOpenFga(), agents=agents),
        allow_insecure_header_auth=True,
    ))


def test_orphans_endpoint_filters_resources_to_maintainers():
    # maintainer of platform/handbook sees its orphaned risk; a non-maintainer doesn't.
    client = _client([_risk("risk-44", "j.tan")], [], readable={"maint": {SPACE}}, agents=set())
    seen = client.get("/orphans", headers={"X-Spike-User": "maint"}).json()
    assert seen["resources"] == {SPACE: ["risk-44"]}
    other = client.get("/orphans", headers={"X-Spike-User": "stranger"}).json()
    assert other["resources"] == {}


def test_orphans_endpoint_shows_tickets_only_to_desk_leads():
    t = Ticket(id="ticket-123", requester="ext-1", status="open", assignee="agent:gone")
    client = _client([], [t], readable={}, agents={"agent:dani"})
    lead = client.get("/orphans", headers={"X-Spike-User": "agent:dani"}).json()
    assert lead["tickets"] == ["ticket-123"]
    cust = client.get("/orphans", headers={"X-Spike-User": "cust"}).json()
    assert cust["tickets"] == []
