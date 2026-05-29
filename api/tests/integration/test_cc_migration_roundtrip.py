"""@api cross-context (INTEGRATOR) — migration round-trip. An Atlassian export is
transformed, committed to Git, and then VISIBLE through the normal read paths with its
old→new ID mapping intact: a Confluence page → doc appears in GET /docs (read from the
same Git store, INV-ST-1/2), and a Jira issue → ticket is readable by its opaque
requester (INV-MIG-1/4, the OpenFGA tuple populated during migration).

Seam: Atlassian export → migration → knowledge(git) + servicedesk + identity + access
→ read endpoints."""

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

SPACE = "platform/handbook"
SVC = "svc:migrator"
EMAIL = "r.okafor@uni.example.ac"


@pytest.fixture
def app_ctx(repo):
    git_store = GitBackedDocStore(repo)  # the SAME store backs reads and migration writes
    identity = IdentityDirectory()
    doc_writer = DocService(git_store, Authority({"migrator": {SPACE}}, {"migrator": {SPACE}}), space=SPACE)
    app = create_app(
        git_store, Authority({"reader": {SPACE}}),
        ticket_store=TicketStore(), ticket_authority=TicketAuthority(FakeOpenFga(), agents=set()),
        comment_store=CommentStore(), identity_directory=identity, doc_writer=doc_writer,
        service_principals={SVC}, allow_insecure_header_auth=True,
    )
    return TestClient(app), identity


def test_export_commits_to_git_and_is_visible_with_mapping(app_ctx):
    client, identity = app_ctx
    items = [
        {"kind": "confluence", "old_id": "12345", "title": "Onboarding",
         "content": "page body", "marked": True, "space": SPACE},
        {"kind": "jira", "old_id": "SUP-77", "title": "t", "content": "issue content",
         "marked": True, "reporter": EMAIL},
    ]
    summary = client.post("/migration/run", json={"items": items}, headers={"X-Spike-User": SVC}).json()
    assert summary["migrated"] == 2

    # Confluence → doc: mapping resolves AND the doc is visible in GET /docs (read from
    # Git, not a side store) — Git commit really did become readable content.
    doc_id = client.get("/migration/resolve/confluence:12345", headers={"X-Spike-User": SVC}).json()["resolved"]
    visible = {d["id"] for d in client.get("/docs", headers={"X-Spike-User": "reader"}).json()}
    assert doc_id in visible

    # Jira → ticket: mapping resolves AND it is readable by the opaque requester
    # (the OpenFGA requester tuple was populated atomically with the Git write, INV-MIG-4).
    ticket_id = client.get("/migration/resolve/SUP-77", headers={"X-Spike-User": SVC}).json()["resolved"]
    requester = identity.resolve(EMAIL)
    assert "@" not in requester
    assert client.get(f"/tickets/{ticket_id}", headers={"X-Spike-User": requester}).status_code == 200
