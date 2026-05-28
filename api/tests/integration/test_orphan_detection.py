"""@api — orphan detection (INV-ORPH-1/2). Active risks whose Space is archived or
whose owner lost write access are flagged for maintainers; open tickets whose desk
is archived, whose assignee lost access, or that are unassigned past the threshold
are flagged for that desk's leads. Computed by a batch refresh, served filtered to
the requester's scope; never auto-reassigns."""

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
DESK = "support/service-desk"


def _risk(rid, owner, status="open", space=SPACE):
    return Risk(id=rid, title="t", space=space, category="delivery", likelihood=3,
                impact=3, strategy="mitigated", status=status, owner=owner)


def _detect(risks, tickets, *, readable=None, writable=None, agents=frozenset(), archived=frozenset()):
    return detect_orphans(
        risks, tickets,
        authority=Authority(readable or {}, writable),
        ticket_authority=TicketAuthority(FakeOpenFga(), agents=set(agents)),
        archived_spaces=archived,
    )


# --- unit: detector logic ----------------------------------------------------

def test_active_risk_with_owner_lacking_write_is_flagged():
    assert _detect([_risk("risk-44", "j.tan")], []).resources == {SPACE: ["risk-44"]}


def test_owner_lost_write_only_is_flagged():
    # G7-04: owner keeps read but lost write → can't maintain → orphaned.
    r = _detect([_risk("risk-44", "o")], [], readable={"o": {SPACE}}, writable={})
    assert r.resources == {SPACE: ["risk-44"]}


def test_archived_space_flags_active_risk_even_with_access():
    # G7-01: archived Space orphans an active resource regardless of owner access.
    r = _detect([_risk("risk-44", "o")], [], readable={"o": {SPACE}}, archived={SPACE})
    assert r.resources == {SPACE: ["risk-44"]}


def test_closed_risk_is_not_flagged():
    assert _detect([_risk("risk-9", "j.tan", status="closed")], []).resources == {}


def test_risk_whose_owner_still_maintains_is_not_flagged():
    r = _detect([_risk("risk-44", "rivera")], [], readable={"rivera": {SPACE}})
    assert r.resources == {}


def test_open_ticket_with_departed_assignee_grouped_by_desk():
    t = Ticket(id="ticket-123", requester="ext-1", status="open", assignee="agent:dani", space=DESK)
    assert _detect([], [t]).tickets == {DESK: ["ticket-123"]}


def test_long_unassigned_open_ticket_is_flagged():
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat()
    t = Ticket(id="ticket-200", requester="ext-1", status="open", assignee=None, created_at=old, space=DESK)
    assert _detect([], [t]).tickets == {DESK: ["ticket-200"]}


def test_recent_unassigned_ticket_is_not_flagged():
    fresh = dt.datetime.now(dt.timezone.utc).isoformat()
    t = Ticket(id="ticket-201", requester="ext-1", status="open", assignee=None, created_at=fresh, space=DESK)
    assert _detect([], [t]).tickets == {}


# --- @api: batch refresh + filtered serving ----------------------------------

def _client(risks, tickets, *, readable, agents=frozenset(), archived=None):
    return TestClient(create_app(
        DocStore([]), Authority(readable),
        risk_store=RiskStore(risks),
        ticket_store=TicketStore(tickets),
        ticket_authority=TicketAuthority(FakeOpenFga(), agents=set(agents)),
        service_principals={"svc:batch"}, archived_spaces=set(archived or set()),
        allow_insecure_header_auth=True,
    ))


def _refresh(client):
    return client.post("/orphans/refresh", headers={"X-Spike-User": "svc:batch"})


def test_refresh_is_service_only_and_get_empty_before_refresh():
    client = _client([_risk("risk-44", "j.tan")], [], readable={"maint": {SPACE}})
    assert client.post("/orphans/refresh", headers={"X-Spike-User": "maint"}).status_code == 403
    pre = client.get("/orphans", headers={"X-Spike-User": "maint"}).json()
    assert pre["computed"] is False and pre["resources"] == {}


def test_resources_filtered_to_maintainers():
    client = _client([_risk("risk-44", "j.tan")], [], readable={"maint": {SPACE}})
    assert _refresh(client).json()["refreshed"] is True
    seen = client.get("/orphans", headers={"X-Spike-User": "maint"}).json()
    assert seen["resources"] == {SPACE: ["risk-44"]} and seen["computed"] is True
    assert client.get("/orphans", headers={"X-Spike-User": "stranger"}).json()["resources"] == {}


def test_tickets_scoped_to_desk_maintainer():
    t = Ticket(id="ticket-123", requester="ext-1", status="open", assignee="agent:gone", space=DESK)
    client = _client([], [t], readable={"lead": {DESK}}, agents={"agent:dani"})
    _refresh(client)
    lead = client.get("/orphans", headers={"X-Spike-User": "lead"}).json()
    assert lead["tickets"] == {DESK: ["ticket-123"]}
    assert client.get("/orphans", headers={"X-Spike-User": "cust"}).json()["tickets"] == {}
