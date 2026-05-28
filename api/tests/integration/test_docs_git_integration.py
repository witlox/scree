"""Integration — the spike trifecta minus the editor: Gateway → real Git-backed
store → per-item permission filter (INV-AGG over DD-002 storage)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.git_store import GitBackedDocStore


def test_gateway_filters_git_backed_docs(repo):
    app = create_app(
        GitBackedDocStore(repo),
        Authority({"rivera": {"platform/handbook"}}),
    )
    client = TestClient(app)

    resp = client.get("/docs", headers={"X-Spike-User": "rivera"})
    ids = {d["id"] for d in resp.json()}
    assert ids == {"doc-a"}  # doc-b lives in org/risk-portfolio → excluded (INV-AGG)

    # Existence-leak-safe: the unreadable doc is 404, not 200.
    assert client.get("/docs/doc-b", headers={"X-Spike-User": "rivera"}).status_code == 404
    assert client.get("/docs/doc-a", headers={"X-Spike-User": "rivera"}).status_code == 200
