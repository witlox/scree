"""@api — Atlassian migration (INV-MIG-1/2/3/4). Marked Jira issues → tickets and
Confluence pages → docs with a stable old→new ID mapping; idempotent re-runs; non-
curated content archived not migrated; imported customers get opaque ids."""

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

SVC = "svc:migrator"
SPACE = "platform/handbook"


@pytest.fixture
def ctx(repo):
    store = TicketStore()
    comments = CommentStore()
    identity = IdentityDirectory()
    doc_store = GitBackedDocStore(repo)
    doc_writer = DocService(doc_store, Authority({"migrator": {SPACE}}), space=SPACE)
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), agents=set()),
        comment_store=comments, identity_directory=identity, doc_writer=doc_writer,
        service_principals={SVC}, allow_insecure_header_auth=True,
    )
    return TestClient(app), store, comments, identity, doc_store


def _run(client, items, who=SVC):
    return client.post("/migration/run", json={"items": items}, headers={"X-Spike-User": who})


def _jira(old_id, marked=True, reporter="r.okafor@uni.example.ac"):
    return {"kind": "jira", "old_id": old_id, "title": "t", "content": "issue content",
            "marked": marked, "reporter": reporter}


def test_migration_is_service_only(ctx):
    client, *_ = ctx
    assert _run(client, [_jira("SUP-1")], who="cust").status_code == 403


def test_jira_issue_migrates_to_ticket_with_opaque_requester_and_mapping(ctx):
    client, store, comments, identity, _ = ctx
    summary = _run(client, [_jira("SUP-4821")]).json()
    assert summary["migrated"] == 1
    # Mapping recorded + resolvable (INV-MIG-1).
    resolved = client.get("/migration/resolve/SUP-4821", headers={"X-Spike-User": SVC}).json()["resolved"]
    t = store.get(resolved)
    assert t is not None
    assert "@" not in t.requester  # opaque requester (INV-MIG-4 / INV-DP-1)
    assert t.requester == identity.resolve("r.okafor@uni.example.ac")
    assert [c.body for c in comments.for_ticket(t.id)] == ["issue content"]  # content preserved


def test_rerun_is_idempotent(ctx):
    client, store, *_ = ctx
    _run(client, [_jira("SUP-4821")])
    first = client.get("/migration/resolve/SUP-4821", headers={"X-Spike-User": SVC}).json()["resolved"]
    summary = _run(client, [_jira("SUP-4821")]).json()  # re-run
    assert summary["migrated"] == 0 and summary["skipped"] == 1
    assert len(store.all()) == 1  # no duplicate
    again = client.get("/migration/resolve/SUP-4821", headers={"X-Spike-User": SVC}).json()["resolved"]
    assert again == first  # mapping unchanged


def test_non_curated_content_is_archived_not_migrated(ctx):
    client, store, _, _, _ = ctx
    summary = _run(client, [_jira("SUP-0001", marked=False)]).json()
    assert summary["archived"] == 1 and summary["migrated"] == 0
    assert store.all() == []
    assert client.get("/migration/resolve/SUP-0001", headers={"X-Spike-User": SVC}).status_code == 404


def test_confluence_page_migrates_to_doc_with_mapping(ctx):
    client, _, _, _, doc_store = ctx
    item = {"kind": "confluence", "old_id": "12345", "title": "Onboarding",
            "content": "page body", "marked": True, "space": SPACE}
    assert _run(client, [item]).json()["migrated"] == 1
    resolved = client.get("/migration/resolve/confluence:12345", headers={"X-Spike-User": SVC}).json()["resolved"]
    assert doc_store.get(resolved) is not None  # doc created in Git
