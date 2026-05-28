"""@api — fixes for I-01 (requester reads own created ticket) and I-02
(community_visible grants read to any authenticated principal, INV-ACC-3)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.store import TicketStore


def _client():
    store = TicketStore()
    authority = TicketAuthority(FakeOpenFga(), {"agent:dani"})
    app = create_app(DocStore([]), Authority({}), ticket_store=store, ticket_authority=authority, allow_insecure_header_auth=True)
    return TestClient(app)


def _create(client, requester="cust-okafor", origin="web"):
    return client.post(
        "/tickets", json={"origin": origin, "requester": requester}, headers={"X-Spike-User": requester}
    ).json()["id"]


def test_requester_can_read_own_created_ticket():
    # I-01: create grants the requester the `requester` relation.
    client = _client()
    tid = _create(client)
    got = client.get(f"/tickets/{tid}", headers={"X-Spike-User": "cust-okafor"})
    assert got.status_code == 200


def test_community_visible_ticket_readable_by_other_authenticated():
    # I-02 / INV-ACC-3.
    client = _client()
    tid = _create(client)
    client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers={"X-Spike-User": "agent:dani"})
    client.post(f"/tickets/{tid}/community-visible", headers={"X-Spike-User": "agent:dani"})

    stranger = client.get(f"/tickets/{tid}", headers={"X-Spike-User": "cust-stranger"})
    assert stranger.status_code == 200


def test_private_ticket_not_readable_by_unrelated_user():
    # Negative: a non-community-visible ticket stays private.
    client = _client()
    tid = _create(client)
    stranger = client.get(f"/tickets/{tid}", headers={"X-Spike-User": "cust-stranger"})
    assert stranger.status_code == 404
