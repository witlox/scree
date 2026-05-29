"""@api — G-A1 / INV-AGG over the risk register: a non-member's listing exposes NO trace
of an unauthorized risk — not its id, title, or score. Stronger than 'id absent': the
whole serialized response must be free of the item's metadata."""

import json

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.risk.store import RiskStore

DISTINCT_TITLE = "ACQUISITION-RUMOUR-RISK"


def _client():
    authority = Authority({"rivera": {"platform/handbook"}, "okafor": {"org/risk-portfolio"}})
    return TestClient(create_app(DocStore([]), authority, risk_store=RiskStore(),
                                 allow_insecure_header_auth=True))


def test_non_member_listing_leaks_no_risk_metadata():
    client = _client()
    created = client.post(
        "/risks",
        json={"title": DISTINCT_TITLE, "space": "platform/handbook",
              "category": "security", "likelihood": 5, "impact": 5},
        headers={"X-Spike-User": "rivera"},
    ).json()
    rid = created["id"]

    body = client.get("/risks", headers={"X-Spike-User": "okafor"}).text
    assert json.loads(body) == []  # other-space member sees none of it
    # No metadata of the unauthorized risk leaks anywhere in the response (id/title/score).
    assert rid not in body
    assert DISTINCT_TITLE not in body
    assert "25" not in body  # derived score (likelihood*impact) must not leak either
