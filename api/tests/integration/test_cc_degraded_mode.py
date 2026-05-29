"""@api cross-context (INTEGRATOR) — degraded mode under a single GitLab outage: an
authorized read still succeeds from the local clone while EVERY Git-backed write path
across contexts (ticket creation, migration) is refused with a clear 503 and leaves no
state behind. One condition, multiple contexts — the uniform INV-DEG-1 guarantee.

Invariants: INV-DEG-1. Seam: availability → Gateway write guard across servicedesk +
migration; read path unaffected."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.platform.health import Availability
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

SPACE = "platform/handbook"


def test_gitlab_down_reads_succeed_writes_refused_no_state():
    docs = DocStore([Doc(id="doc-a", title="A", space=SPACE, body="hello")])
    store = TicketStore()
    client = TestClient(create_app(
        docs, Authority({"u": {SPACE}}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), agents={"agent:dani"}),
        comment_store=CommentStore(), service_principals={"svc:mig"},
        availability=Availability(gitlab_up=False), allow_insecure_header_auth=True,
    ))

    # Read from the local clone still works during the outage.
    assert {d["id"] for d in client.get("/docs", headers={"X-Spike-User": "u"}).json()} == {"doc-a"}

    # Writes across contexts are refused with a clear 503 — never silently dropped.
    assert client.post("/tickets", json={"origin": "web"}, headers={"X-Spike-User": "u"}).status_code == 503
    assert client.post(
        "/migration/run",
        json={"items": [{"kind": "jira", "old_id": "SUP-1", "title": "t", "content": "c", "marked": True}]},
        headers={"X-Spike-User": "svc:mig"},
    ).status_code == 503

    # ...and nothing was half-applied.
    assert store.all() == []
