"""@api — G-A17 / INV-ORPH-1/2: orphan detection FLAGS, it never auto-reassigns. After a
batch refresh the flagged risk's owner (and an orphaned ticket's assignee) is unchanged."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.risk.models import Risk
from scree.risk.store import RiskStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

SPACE = "platform/handbook"
DESK = "support/service-desk"


def test_refresh_flags_but_does_not_reassign():
    risk = Risk(id="risk-44", title="t", space=SPACE, category="delivery",
                likelihood=3, impact=3, strategy="mitigated", status="open", owner="j.tan")
    ticket = Ticket(id="ticket-1", requester="ext-1", status="open",
                    assignee="agent:gone", space=DESK)
    risk_store = RiskStore([risk])
    ticket_store = TicketStore([ticket])
    client = TestClient(create_app(
        DocStore([]), Authority({"maint": {SPACE, DESK}}),
        risk_store=risk_store, ticket_store=ticket_store,
        ticket_authority=TicketAuthority(FakeOpenFga(), agents={"agent:dani"}),
        service_principals={"svc:batch"}, allow_insecure_header_auth=True,
    ))
    client.post("/orphans/refresh", headers={"X-Spike-User": "svc:batch"})
    seen = client.get("/orphans", headers={"X-Spike-User": "maint"}).json()
    assert "risk-44" in seen["resources"].get(SPACE, [])  # flagged

    # ...but the underlying records are untouched (no auto-reassignment).
    assert risk_store.get("risk-44").owner == "j.tan"
    assert ticket_store.get("ticket-1").assignee == "agent:gone"
