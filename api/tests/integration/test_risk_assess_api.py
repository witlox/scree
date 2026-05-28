"""@api — the /risks/assess endpoint: derived score/severity + INV-IX-1 trigger."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore


def _client() -> TestClient:
    return TestClient(create_app(DocStore([]), Authority({})))


def test_assess_returns_derived_fields_and_category_trigger():
    client = _client()

    # High-score delivery risk: severity critical, but does NOT fire (INV-IX-1).
    delivery = client.post("/risks/assess", json={"category": "delivery", "likelihood": 5, "impact": 4}).json()
    assert delivery["score"] == 20
    assert delivery["severity"] == "critical"
    assert delivery["fires_critical_webhook"] is False

    # Low-score security risk: fires the webhook (category-driven).
    security = client.post("/risks/assess", json={"category": "security", "likelihood": 1, "impact": 1}).json()
    assert security["severity"] == "low"
    assert security["fires_critical_webhook"] is True
