"""Integration — doc write integrity: kind check + id uniqueness (INV-ST-4) and
optimistic concurrency (INV-ST-6)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore

DOC = """---
id: doc-x
kind: doc
schema_version: 1
title: X
space: platform/handbook
---
v1
"""


def _client(repo):
    store = GitBackedDocStore(repo)
    authority = Authority({"writer": {"platform/handbook"}})
    return TestClient(create_app(store, authority, doc_writer=DocService(store, authority)))


def _post(client, path, content, base_rev=None):
    return client.post(
        "/docs", json={"path": path, "content": content, "base_rev": base_rev},
        headers={"X-Spike-User": "writer"},
    )


def test_non_doc_kind_rejected(repo):
    bad_kind = DOC.replace("kind: doc", "kind: ticket")
    assert _post(_client(repo), "docs/x.md", bad_kind).status_code == 422


def test_duplicate_id_at_different_path_rejected(repo):
    client = _client(repo)
    assert _post(client, "docs/x.md", DOC).status_code == 200
    # Same id, different path -> uniqueness violation (INV-ST-4).
    assert _post(client, "docs/elsewhere.md", DOC).status_code == 409


def test_stale_base_rev_is_conflict(repo):
    client = _client(repo)
    assert _post(client, "docs/x.md", DOC).status_code == 200
    # Update an existing path without the current rev -> optimistic-concurrency 409.
    assert _post(client, "docs/x.md", DOC.replace("v1", "v2"), base_rev="deadbeef").status_code == 409
