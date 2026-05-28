"""@api — adversary gate-2 doc-write hardening:
G2-01 path traversal/absolute confinement, G2-04 space↔path binding,
G2-07 YAML alias-bomb + size guard, G2-11 concurrent-write serialization."""

import threading

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.frontmatter import InvalidFrontmatter, parse
from scree.knowledge.git_store import GitBackedDocStore

SPACE = "platform/handbook"
DOC = f"""---
id: doc-x
kind: doc
schema_version: 1
title: X
space: {SPACE}
---
body
"""


def _client(repo):
    store = GitBackedDocStore(repo)
    authority = Authority({"writer": {SPACE}})
    service = DocService(store, authority, space=SPACE)
    return TestClient(create_app(store, authority, doc_writer=service))


def _post(client, path, content=DOC):
    return client.post("/docs", json={"path": path, "content": content},
                       headers={"X-Spike-User": "writer"})


@pytest.mark.parametrize("path", [
    "../../../../tmp/pwned.md",          # G2-01 traversal escape
    "/etc/cron.d/evil",                  # G2-01 absolute escape
    "docs/../../secrets.md",             # G2-01 mid-path traversal
])
def test_path_outside_space_is_rejected(repo, path):
    assert _post(_client(repo), path).status_code == 422


def test_frontmatter_space_must_match_store_space(repo):
    # G2-04: a writer for SPACE can't smuggle a doc declaring a different space.
    other = DOC.replace(f"space: {SPACE}", "space: other/secret")
    assert _post(_client(repo), "docs/x.md", other).status_code in (403, 409)


def test_yaml_alias_bomb_rejected():
    # G2-07: anchors/aliases in frontmatter are refused (anti billion-laughs).
    bomb = "---\na: &a [1, 1]\nb: [*a, *a]\nid: x\nkind: doc\nschema_version: 1\ntitle: t\nspace: s\n---\nx"
    with pytest.raises(InvalidFrontmatter):
        parse(bomb)


def test_oversized_content_rejected():
    # G2-07: unbounded frontmatter/content is refused before parsing. Required
    # keys are present, so only the size guard can reject this.
    huge = DOC + "a" * 2_000_000
    with pytest.raises(InvalidFrontmatter):
        parse(huge)


def test_concurrent_writes_serialize_without_500(repo):
    # G2-11: two concurrent writes to the same repo must not collide on index.lock.
    client = _client(repo)
    results: list[int] = []

    def write(n):
        doc = DOC.replace("id: doc-x", f"id: doc-{n}")
        results.append(_post(client, f"docs/{n}.md", doc).status_code)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(code == 200 for code in results), results
