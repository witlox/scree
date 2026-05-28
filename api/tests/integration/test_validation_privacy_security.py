"""@api — adversary gate-2 validation & privacy hardening:
G2-09 risk/ticket input validation, G2-06 requester redaction in
community_visible ticket views."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

AUTH = {"X-Spike-User": "rivera"}


def _risk_client():
    authority = Authority({"rivera": {"platform/handbook"}})
    return TestClient(create_app(DocStore([]), authority, risk_store=__risk_store(),
                                 allow_insecure_header_auth=True))


def __risk_store():
    from scree.risk.store import RiskStore
    return RiskStore()


# --- G2-09: input validation -------------------------------------------------

def test_assess_rejects_out_of_range_score():
    client = _risk_client()
    bad = {"category": "delivery", "likelihood": 1000, "impact": 1000}
    assert client.post("/risks/assess", json=bad, headers=AUTH).status_code == 422


def test_assess_rejects_unknown_category():
    client = _risk_client()
    bad = {"category": "banana", "likelihood": 3, "impact": 3}
    assert client.post("/risks/assess", json=bad, headers=AUTH).status_code == 422


def test_create_risk_rejects_unknown_strategy():
    client = _risk_client()
    bad = {"title": "t", "space": "platform/handbook", "category": "delivery",
           "likelihood": 3, "impact": 3, "strategy": "wishful"}
    assert client.post("/risks", json=bad, headers=AUTH).status_code == 422


def test_create_ticket_rejects_unknown_origin():
    fga = FakeOpenFga()
    app = create_app(DocStore([]), Authority({}), ticket_store=TicketStore(),
                     ticket_authority=TicketAuthority(fga, set()), allow_insecure_header_auth=True)
    client = TestClient(app)
    resp = client.post("/tickets", json={"origin": "carrier-pigeon"}, headers={"X-Spike-User": "u"})
    assert resp.status_code == 422


# --- G2-06: requester redaction ----------------------------------------------

def _ticket_client():
    fga = FakeOpenFga()
    fga.write("cust-okafor", "requester", "ticket-1")
    store = TicketStore([Ticket(id="ticket-1", requester="cust-okafor", community_visible=True)])
    authority = TicketAuthority(fga, agents={"agent:dani"})
    app = create_app(DocStore([]), Authority({}), ticket_store=store,
                     ticket_authority=authority, allow_insecure_header_auth=True)
    return TestClient(app)


def test_community_viewer_does_not_see_requester():
    client = _ticket_client()
    # An unrelated authenticated user can read the community ticket but not who filed it.
    resp = client.get("/tickets/ticket-1", headers={"X-Spike-User": "stranger"})
    assert resp.status_code == 200
    assert resp.json()["requester"] is None


def test_agent_and_requester_see_requester():
    client = _ticket_client()
    for who in ("agent:dani", "cust-okafor"):
        body = client.get("/tickets/ticket-1", headers={"X-Spike-User": who}).json()
        assert body["requester"] == "cust-okafor"


def test_community_viewer_listing_redacts_requester():
    client = _ticket_client()
    rows = client.get("/tickets", headers={"X-Spike-User": "stranger"}).json()
    assert rows == [{"id": "ticket-1", "requester": None}]
