"""@api — G-A5 / INV-MIG-4: a migrated ticket gets its OpenFGA requester tuple, so the
imported (opaque) requester can actually read their own ticket. Without the tuple the
migrated identity would have no authority (dangling-authority risk)."""

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

SVC = "svc:migrator"
EMAIL = "r.okafor@uni.example.ac"


@pytest.fixture
def ctx():
    store = TicketStore()
    identity = IdentityDirectory()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), agents=set()),
        comment_store=CommentStore(), identity_directory=identity,
        service_principals={SVC}, allow_insecure_header_auth=True,
    )
    return TestClient(app), identity


def test_migrated_requester_can_read_their_ticket(ctx):
    client, identity = ctx
    item = {"kind": "jira", "old_id": "SUP-9001", "title": "t", "content": "c",
            "marked": True, "reporter": EMAIL}
    assert client.post("/migration/run", json={"items": [item]},
                       headers={"X-Spike-User": SVC}).json()["migrated"] == 1
    resolved = client.get("/migration/resolve/SUP-9001",
                          headers={"X-Spike-User": SVC}).json()["resolved"]

    requester = identity.resolve(EMAIL)  # stable opaque id
    # The requester tuple was written during migration → the opaque requester reads it.
    got = client.get(f"/tickets/{resolved}", headers={"X-Spike-User": requester})
    assert got.status_code == 200
    # And an unrelated customer still cannot.
    assert client.get(f"/tickets/{resolved}",
                      headers={"X-Spike-User": "cust-other"}).status_code == 404
