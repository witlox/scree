"""@api — graceful degradation (INV-DEG-1/2, DD-003/019). When GitLab is down,
reads from the local clone still serve and permissions still hold, but writes are
refused with a clear 503 — never silently dropped. When O365 is down, inbound
email creation fails visibly."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.platform.health import Availability
from scree.servicedesk.store import TicketStore

SPACE = "platform/handbook"


def _client(health):
    docs = DocStore([Doc(id="doc-onboarding", title="Onboarding", space=SPACE, body="hello")])
    return TestClient(create_app(
        docs, Authority({"rivera": {SPACE}}),
        ticket_store=TicketStore(), ticket_authority=TicketAuthority(FakeOpenFga(), agents=set()),
        availability=health, allow_insecure_header_auth=True,
    ))


def test_reads_from_local_clone_succeed_when_gitlab_down():
    client = _client(Availability(gitlab_up=False))
    # The DocStore is the local clone — authorized reads still render.
    resp = client.get("/docs/doc-onboarding", headers={"X-Spike-User": "rivera"})
    assert resp.status_code == 200 and "hello" in resp.json()["body"]


def test_reads_still_respect_permissions_when_gitlab_down():
    client = _client(Availability(gitlab_up=False))
    # rivera has no access to another space → denied even from the local clone.
    assert client.get("/docs/doc-onboarding", headers={"X-Spike-User": "stranger"}).status_code == 404


def test_ticket_creation_refused_clearly_when_gitlab_down():
    client = _client(Availability(gitlab_up=False))
    resp = client.post("/tickets", json={"origin": "web"}, headers={"X-Spike-User": "ext-okafor"})
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()  # clear error, not a false success


def test_writes_succeed_again_when_gitlab_back_up():
    client = _client(Availability(gitlab_up=True))
    assert client.post("/tickets", json={"origin": "web"}, headers={"X-Spike-User": "ext-okafor"}).status_code == 200


def test_inbound_email_503_when_o365_down_with_service_principal():
    docs = DocStore([])
    app = create_app(
        docs, Authority({}),
        ticket_store=TicketStore(), ticket_authority=TicketAuthority(FakeOpenFga(), agents=set()),
        service_principals={"svc:poller"}, availability=Availability(email_up=False),
        allow_insecure_header_auth=True,
    )
    client = TestClient(app)
    raw = "From: a@x.ac\nSubject: hi\n\nbody\n"
    resp = client.post("/tickets/inbound-email", json={"raw": raw, "verified": True, "sender": "a@x.ac"},
                       headers={"X-Spike-User": "svc:poller"})
    assert resp.status_code == 503 and "O365" in resp.json()["detail"]
