"""@api — risk persistence + permission-filtered listing (I-09, INV-AGG).
Critical-category risks are flagged via the wired trigger (INV-IX-1)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.risk.store import RiskStore


def _client():
    authority = Authority({"rivera": {"platform/handbook"}, "okafor": {"org/risk-portfolio"}})
    return TestClient(create_app(DocStore([]), authority, risk_store=RiskStore()))


def _create(client, user, space, category="delivery", likelihood=3, impact=3):
    return client.post(
        "/risks",
        json={"title": "t", "space": space, "category": category, "likelihood": likelihood, "impact": impact},
        headers={"X-Spike-User": user},
    )


def test_create_persists_and_is_listed_for_space_member():
    client = _client()
    r = _create(client, "rivera", "platform/handbook")
    assert r.status_code == 200
    listed = client.get("/risks", headers={"X-Spike-User": "rivera"}).json()
    assert r.json()["id"] in {x["id"] for x in listed}


def test_listing_excludes_risks_from_other_spaces():
    # INV-AGG over risks.
    client = _client()
    rid = _create(client, "rivera", "platform/handbook").json()["id"]
    other = client.get("/risks", headers={"X-Spike-User": "okafor"}).json()
    assert rid not in {x["id"] for x in other}


def test_create_requires_write_authority():
    assert _create(_client(), "stranger", "platform/handbook").status_code == 403


def test_security_category_flagged_critical():
    client = _client()
    sec = _create(client, "rivera", "platform/handbook", category="security", likelihood=1, impact=1).json()
    assert sec["fires_critical_webhook"] is True
