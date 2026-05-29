"""@api — #84 real indexer. The derived search index is rebuildable from Git and
maintained by three triggers (DD-005): batch + manual (rebuild) and the critical
webhook (upsert one). Tests the trigger model + invariants:
INV-IX-1 (security/compliance → sensitive/webhook), INV-IX-2 (batch catches a missed
webhook), INV-IX-3 (manual reindex authenticated + rate-limited), INV-IX-4 (sensitive
partition), idempotency, and INV-AGG on /search."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.risk.models import Risk
from scree.risk.store import RiskStore

SPACE_A = "platform/handbook"
SPACE_B = "org/secret-portfolio"
SVC = "svc:indexer"
U = "u"


def _risk(rid, title, space, category):
    return Risk(id=rid, title=title, space=space, category=category, likelihood=3, impact=3,
                strategy="mitigated", status="open", owner="o")


def _ctx(docs=None, risks=None):
    doc_store = DocStore(docs if docs is not None else [
        Doc(id="doc-a", title="Alpha", space=SPACE_A, body="searchable alpha"),
        Doc(id="doc-b", title="Beta", space=SPACE_B, body="searchable beta"),
    ])
    risk_store = RiskStore(risks if risks is not None else [
        _risk("risk-sec", "topic incident", SPACE_A, "security"),
        _risk("risk-del", "topic delivery", SPACE_A, "delivery"),
    ])
    app = create_app(doc_store, Authority({U: {SPACE_A}}), risk_store=risk_store,
                     service_principals={SVC}, allow_insecure_header_auth=True)
    return TestClient(app), risk_store


def _reindex(client, who=U):
    return client.post("/index/reindex", headers={"X-Spike-User": who})


def _search(client, q, who=U):
    return client.get("/search", params={"q": q}, headers={"X-Spike-User": who}).json()


def test_search_is_never_indexed_until_a_reindex():
    client, _ = _ctx()
    out = _search(client, "alpha")
    assert out["never_indexed"] is True and out["results"] == []


def test_search_filters_by_readable_space_inv_agg():
    client, _ = _ctx()
    _reindex(client)
    ids = {h["id"] for h in _search(client, "searchable")["results"]}
    assert ids == {"doc-a"}  # SPACE_B's doc-b excluded — no leak (INV-AGG)


def test_critical_webhook_marks_security_compliance_sensitive():
    # INV-IX-1 / INV-IX-4: security/compliance → sensitive partition; delivery → main.
    client, _ = _ctx()
    assert client.post("/index/events", json={"risk_id": "risk-sec"}, headers={"X-Spike-User": SVC}).json()["sensitive"] is True
    assert client.post("/index/events", json={"risk_id": "risk-del"}, headers={"X-Spike-User": SVC}).json()["sensitive"] is False


def test_index_events_are_service_principal_only():
    client, _ = _ctx()
    assert client.post("/index/events", json={"risk_id": "risk-sec"}, headers={"X-Spike-User": U}).status_code == 403


def test_batch_catches_a_missed_webhook():
    # INV-IX-2: a risk changed without a webhook is absent until the next rebuild.
    client, risk_store = _ctx()
    _reindex(client)
    risk_store.put(_risk("risk-late", "topic late-arrival", SPACE_A, "delivery"))  # no webhook fired
    assert "risk-late" not in {h["id"] for h in _search(client, "late-arrival")["results"]}
    _reindex(client)  # next hourly batch
    assert "risk-late" in {h["id"] for h in _search(client, "late-arrival")["results"]}


def test_webhook_then_batch_is_idempotent_no_duplicates():
    client, _ = _ctx()
    client.post("/index/events", json={"risk_id": "risk-sec"}, headers={"X-Spike-User": SVC})
    client.post("/index/events", json={"risk_id": "risk-sec"}, headers={"X-Spike-User": SVC})  # duplicate
    _reindex(client)  # batch re-reads from Git
    hits = [h for h in _search(client, "incident")["results"] if h["id"] == "risk-sec"]
    assert len(hits) == 1  # keyed by id — no duplicate


def test_manual_reindex_is_rate_limited():
    client, _ = _ctx()
    for _ in range(3):  # limit=3
        assert _reindex(client).status_code == 200
    assert _reindex(client).status_code == 429  # INV-IX-3
