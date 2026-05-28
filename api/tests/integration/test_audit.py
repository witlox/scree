"""@api — I-08: the Gateway records every action to the append-only audit sink
with the resolved principal (INV-ID-3)."""

from fastapi.testclient import TestClient

from scree.access.audit import AuditSink
from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore


def _client():
    sink = AuditSink()
    store = DocStore([Doc(id="doc-a", title="A", space="platform/handbook", body="b")])
    authority = Authority({"rivera": {"platform/handbook"}})
    return TestClient(create_app(store, authority, audit=sink)), sink


def test_action_is_audited_with_principal():
    client, sink = _client()
    client.get("/docs", headers={"X-Spike-User": "rivera"})
    events = sink.events()
    assert any(e.principal == "rivera" and e.resource == "/docs" and e.result == 200 for e in events)


def test_unauthenticated_request_is_audited():
    client, sink = _client()
    client.get("/docs")  # no identity -> 401
    assert any(e.resource == "/docs" and e.result == 401 for e in sink.events())
