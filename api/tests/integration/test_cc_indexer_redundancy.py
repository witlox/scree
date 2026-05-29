"""@api cross-context (INTEGRATOR) — indexer trigger redundancy (#84). A resource
change reaches /search via EITHER trigger: the critical webhook (near-real-time) OR
the batch/manual reindex. Killing one trigger still propagates the change — correctness
never depends on webhook delivery (INV-IX-2). Seam: resource change → indexer triggers
→ index → search query (per-item INV-AGG filter)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.risk.models import Risk
from scree.risk.store import RiskStore

SPACE = "org/risk-portfolio"
SVC = "svc:indexer"
U = "maint"


def _risk(rid, title, category):
    return Risk(id=rid, title=title, space=SPACE, category=category, likelihood=3, impact=3,
                strategy="mitigated", status="open", owner="o")


def _ids(client, q):
    return {h["id"] for h in client.get("/search", params={"q": q}, headers={"X-Spike-User": U}).json()["results"]}


def test_either_trigger_propagates_a_change_to_search():
    risks = RiskStore([
        _risk("risk-wh", "webhook-borne incident", "security"),
        _risk("risk-bt", "batch-borne slippage", "delivery"),
    ])
    client = TestClient(create_app(DocStore([]), Authority({U: {SPACE}}), risk_store=risks,
                                   service_principals={SVC}, allow_insecure_header_auth=True))

    # Webhook path: only risk-wh is pushed via the critical webhook → searchable now.
    client.post("/index/events", json={"risk_id": "risk-wh"}, headers={"X-Spike-User": SVC})
    assert "risk-wh" in _ids(client, "incident")
    # risk-bt had no webhook → not yet indexed (the webhook for it was "missed").
    assert _ids(client, "slippage") == set()

    # Batch trigger catches the missed change — redundancy: data propagates without a
    # webhook (INV-IX-2). Both trigger paths reach the same searchable index.
    client.post("/index/reindex", headers={"X-Spike-User": U})
    assert "risk-bt" in _ids(client, "slippage")
    assert "risk-wh" in _ids(client, "incident")  # still there after the rebuild (idempotent)
