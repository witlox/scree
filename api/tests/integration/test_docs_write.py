"""Integration — doc write path against a real git repo: write=commit + version
(INV-ST-1/5), schema validation (INV-ST-3), governed-path refusal (INV-GOV-1),
write authority. Runs in CI (git everywhere)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore

NEW_DOC = """---
id: doc-new
kind: doc
schema_version: 1
title: New Page
space: platform/handbook
---
First version.
"""


def _client(repo):
    store = GitBackedDocStore(repo)
    authority = Authority({"writer": {"platform/handbook"}})
    service = DocService(store, authority, governed_prefixes={"policy/"})
    return TestClient(create_app(store, authority, doc_writer=service, allow_insecure_header_auth=True))


def _post(client, path, content, user="writer", base_rev=None):
    return client.post(
        "/docs",
        json={"path": path, "content": content, "base_rev": base_rev},
        headers={"X-Spike-User": user},
    )


def test_write_creates_version_and_is_readable(repo):
    client = _client(repo)
    r1 = _post(client, "docs/new.md", NEW_DOC)
    assert r1.status_code == 200
    rev = r1.json()["rev"]

    got = client.get("/docs/doc-new", headers={"X-Spike-User": "writer"})
    assert got.status_code == 200
    assert "First version" in got.json()["body"]

    # Writing again (with the current rev) produces a new committed version.
    v2 = NEW_DOC.replace("First version.", "Second version.")
    assert _post(client, "docs/new.md", v2, base_rev=rev).status_code == 200
    assert "Second version" in client.get("/docs/doc-new", headers={"X-Spike-User": "writer"}).json()["body"]


def test_governed_path_rejected(repo):
    # INV-GOV-1: direct write to an MR-required path is refused.
    gov = NEW_DOC.replace("id: doc-new", "id: doc-policy")
    assert _post(client := _client(repo), "policy/security.md", gov).status_code == 409


def test_invalid_frontmatter_rejected(repo):
    bad = NEW_DOC.replace("schema_version: 1\n", "")  # INV-ST-3
    assert _post(_client(repo), "docs/bad2.md", bad).status_code == 422


def test_non_writer_forbidden(repo):
    assert _post(_client(repo), "docs/x.md", NEW_DOC, user="stranger").status_code == 403
