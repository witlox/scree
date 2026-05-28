"""I-04 — re-writing identical doc content must be a clean no-op, not a 500
(git 'nothing to commit')."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore

DOC = """---
id: doc-rw
kind: doc
schema_version: 1
title: Rewrite
space: platform/handbook
---
Same content.
"""


def _client(repo):
    store = GitBackedDocStore(repo)
    authority = Authority({"writer": {"platform/handbook"}})
    return TestClient(create_app(store, authority, doc_writer=DocService(store, authority)))


def test_rewriting_identical_content_is_a_noop(repo):
    client = _client(repo)
    h = {"X-Spike-User": "writer"}
    assert client.post("/docs", json={"path": "docs/rw.md", "content": DOC}, headers=h).status_code == 200
    # Identical second write must not 500.
    assert client.post("/docs", json={"path": "docs/rw.md", "content": DOC}, headers=h).status_code == 200
