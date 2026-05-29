"""@api — GET /docs/{id} carries path + rev + schema_version + timestamps, and
/docs/{id}/versions returns Git history (INV-ST-5). These let the editor round-trip an
edit safely (rebuild frontmatter; base_rev for optimistic concurrency, INV-ST-6)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore

SPACE = "platform/handbook"
U = "u"

DOC_A_V2 = """---
id: doc-a
kind: doc
schema_version: 1
title: Alpha
space: platform/handbook
---
Alpha body, revised
"""


def _client(repo):
    git_store = GitBackedDocStore(repo)
    authority = Authority({U: {SPACE}}, {U: {SPACE}})
    app = create_app(git_store, authority, doc_writer=DocService(git_store, authority, space=SPACE),
                     allow_insecure_header_auth=True)
    return TestClient(app)


def test_get_doc_carries_path_rev_and_schema_version(repo):
    client = _client(repo)
    d = client.get("/docs/doc-a", headers={"X-Spike-User": U}).json()
    assert d["id"] == "doc-a"
    assert d["path"] == "docs/a.md"
    assert d["schema_version"] == 1
    assert d["rev"] and len(d["rev"]) >= 7  # real commit sha
    assert d["created"] and d["updated"]


def test_versions_returns_git_history_newest_first(repo):
    client = _client(repo)
    rev = client.get("/docs/doc-a", headers={"X-Spike-User": U}).json()["rev"]
    # Edit the doc (a second commit) using the current rev as base.
    w = client.post("/docs", json={"path": "docs/a.md", "content": DOC_A_V2, "base_rev": rev},
                    headers={"X-Spike-User": U})
    assert w.status_code == 200

    versions = client.get("/docs/doc-a/versions", headers={"X-Spike-User": U}).json()
    assert len(versions) >= 2  # seed commit + the edit
    assert versions[0]["rev"] == w.json()["rev"]  # newest first
    assert all({"rev", "author", "date", "message"} <= set(v) for v in versions)
