"""@api BDD — canonical docs.feature: edits are new Git versions (no status field),
governed paths require an MR. Backed by a real GitBackedDocStore (INV-ST-1/5, INV-GOV-1).
The @e2e WYSIWYG round-trip runs in the Playwright tier."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore

scenarios("docs.feature")

AUTHOR = "platform-team"
SPACE = "platform/handbook"


def _doc(doc_id: str, body: str) -> str:
    return f"---\nid: {doc_id}\nkind: doc\nschema_version: 1\ntitle: Onboarding\nspace: {SPACE}\n---\n{body}\n"


@pytest.fixture
def world(git_repo) -> dict:
    repo = git_repo("docs")
    store = GitBackedDocStore(repo)
    authority = Authority({AUTHOR: {SPACE}})
    doc_writer = DocService(store, authority, governed_prefixes={"policy/"})
    app = create_app(store, authority, doc_writer=doc_writer, allow_insecure_header_auth=True)
    return {"repo": repo, "client": TestClient(app), "doc_id": None, "path": None, "response": None}


@given(parsers.parse('doc "{doc_id}" exists in "{space}"'))
def doc_exists(world, commit_doc, doc_id, space):
    path = f"docs/{doc_id}.md"
    commit_doc(world["repo"], path, doc_id=doc_id, title="Onboarding", space=space, body="original body")
    world["doc_id"], world["path"] = doc_id, path


@given(parsers.parse('doc "{doc_id}" is on an MR-required path'))
def governed_doc(world, doc_id):
    world["doc_id"], world["path"] = doc_id, f"policy/{doc_id}.md"


@when(parsers.parse('"{author}" edits its body and saves'))
def edit_doc(world, author):
    current = world["client"].get(f"/docs/{world['doc_id']}", headers={"X-Spike-User": author}).json()
    world["response"] = world["client"].post(
        "/docs",
        json={"path": world["path"], "content": _doc(world["doc_id"], "edited body"), "base_rev": current["rev"]},
        headers={"X-Spike-User": author},
    )


@when("a direct commit attempts to change it")
def direct_commit(world):
    world["response"] = world["client"].post(
        "/docs",
        json={"path": world["path"], "content": _doc(world["doc_id"], "new body"), "base_rev": None},
        headers={"X-Spike-User": AUTHOR},
    )


@then("a new Git commit records the change with the author and timestamp")
def new_version(world):
    assert world["response"].status_code == 200
    versions = world["client"].get(f"/docs/{world['doc_id']}/versions", headers={"X-Spike-User": AUTHOR}).json()
    assert len(versions) >= 2  # seed + edit
    latest = versions[0]
    assert latest["author"] == AUTHOR and latest["date"]


@then('the doc has no "status" field')
def no_status(world):
    doc = world["client"].get(f"/docs/{world['doc_id']}", headers={"X-Spike-User": AUTHOR}).json()
    assert "status" not in doc  # docs are versioned, not stateful


@then("the commit is rejected by branch protection and CODEOWNERS")
def rejected_governed(world):
    assert world["response"].status_code == 409  # MRRequired (INV-GOV-1)
