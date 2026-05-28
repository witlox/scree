"""@api — adversary gate-2 gateway identity/audit hardening:
G2-03 fail-closed auth, G2-02 requester bound to principal, G2-10 assess
requires auth, G2-08 5xx is audited."""

import pytest
from fastapi.testclient import TestClient

from scree.access.audit import AuditSink
from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.servicedesk.store import TicketStore


def test_create_app_without_authenticator_fails_closed():
    # G2-03: refuse to start with no authenticator unless dev opt-in is explicit.
    with pytest.raises(ValueError):
        create_app(DocStore([]), Authority({}))


def test_insecure_header_path_requires_explicit_optin():
    # G2-03: with the opt-in, the dev header path works (spike only).
    app = create_app(
        DocStore([Doc(id="d", title="T", space="s", body="b")]),
        Authority({"u": {"s"}}),
        allow_insecure_header_auth=True,
    )
    client = TestClient(app)
    assert client.get("/docs", headers={"X-Spike-User": "u"}).status_code == 200


def _ticket_client():
    fga = FakeOpenFga()
    authority = TicketAuthority(fga, agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=TicketStore(),
        ticket_authority=authority,
        allow_insecure_header_auth=True,
    )
    return TestClient(app)


def test_non_agent_cannot_forge_requester():
    # G2-02: a non-agent posting someone else's requester is refused (403).
    client = _ticket_client()
    resp = client.post(
        "/tickets",
        json={"origin": "web", "requester": "cust-victim"},
        headers={"X-Spike-User": "mallory"},
    )
    assert resp.status_code == 403


def test_requester_defaults_to_authenticated_principal():
    # G2-02: omitting requester binds it to the caller, not an arbitrary id.
    client = _ticket_client()
    resp = client.post("/tickets", json={"origin": "web"}, headers={"X-Spike-User": "cust-okafor"})
    assert resp.status_code == 200
    assert resp.json()["requester"] == "cust-okafor"


def test_agent_may_open_on_behalf_of_requester():
    # G2-02: an agent is allowed to set an explicit on-behalf requester.
    client = _ticket_client()
    resp = client.post(
        "/tickets",
        json={"origin": "email", "requester": "cust-okafor"},
        headers={"X-Spike-User": "agent:dani"},
    )
    assert resp.status_code == 200
    assert resp.json()["requester"] == "cust-okafor"


def test_assess_risk_requires_authentication():
    # G2-10: the assess endpoint is no longer anonymous.
    app = create_app(DocStore([]), Authority({}), allow_insecure_header_auth=True)
    client = TestClient(app)
    body = {"category": "security", "likelihood": 3, "impact": 4}
    assert client.post("/risks/assess", json=body).status_code == 401
    assert client.post("/risks/assess", json=body, headers={"X-Spike-User": "u"}).status_code == 200


def test_server_error_is_audited():
    # G2-08: an unhandled 5xx still produces an audit event.
    sink = AuditSink()

    class Boom(DocStore):
        def all(self):
            raise RuntimeError("kaboom")

    app = create_app(Boom([]), Authority({"u": {"s"}}), audit=sink, allow_insecure_header_auth=True)
    client = TestClient(app, raise_server_exceptions=False)
    client.get("/docs", headers={"X-Spike-User": "u"})
    assert any(e.resource == "/docs" and e.result == 500 for e in sink.events())
