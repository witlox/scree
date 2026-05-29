"""@api cross-context (INTEGRATOR) — the load-bearing INV-AGG, checked for CONSISTENCY
across aggregation surfaces. One principal who can read only `platform/handbook` must
see neither an unauthorized doc nor an unauthorized risk — and none of their metadata
(id/title/score) — from EITHER GET /docs or GET /risks. A leak in any one surface is a
cross-context failure even if each context filters "correctly" in isolation.

Invariants: INV-AGG, INV-ACC-1. Seam: query → per-item permission filter (knowledge +
risk) → results."""

import json

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.risk.models import Risk
from scree.risk.store import RiskStore

READABLE = "platform/handbook"
SECRET = "org/secret-portfolio"


def _risk(rid, space, title, likelihood=5, impact=5):
    return Risk(id=rid, title=title, space=space, category="delivery",
                likelihood=likelihood, impact=impact, strategy="mitigated", status="open", owner="o")


def test_unauthorized_item_excluded_from_every_aggregation_surface():
    docs = DocStore([
        Doc(id="doc-ok", title="Readable", space=READABLE, body="x"),
        Doc(id="doc-secret", title="HIDDEN-DOC-TITLE", space=SECRET, body="x"),
    ])
    risks = RiskStore([
        _risk("risk-ok", READABLE, "ok", likelihood=2, impact=2),  # score 4
        _risk("risk-secret", SECRET, "HIDDEN-RISK-TITLE", likelihood=5, impact=5),  # score 25
    ])
    client = TestClient(create_app(
        docs, Authority({"rivera": {READABLE}}), risk_store=risks, allow_insecure_header_auth=True,
    ))

    docs_body = client.get("/docs", headers={"X-Spike-User": "rivera"}).text
    risks_body = client.get("/risks", headers={"X-Spike-User": "rivera"}).text

    # Consistent exclusion: no id/title/score of an unauthorized item in ANY surface.
    for body in (docs_body, risks_body):
        assert "HIDDEN-DOC-TITLE" not in body
        assert "HIDDEN-RISK-TITLE" not in body
        assert "doc-secret" not in body
        assert "risk-secret" not in body
        assert "25" not in body  # the unauthorized risk's derived score (5*5)

    assert {d["id"] for d in json.loads(docs_body)} == {"doc-ok"}
    assert {r["id"] for r in json.loads(risks_body)} == {"risk-ok"}
