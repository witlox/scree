"""@api BDD — canonical migration.feature (DD-014): non-curated content archives
rather than migrates; a legacy reference resolves via the mapping (no broken links).
Docs migrate to a Git-backed store. The @contract jira/confluence round-trips run
in the testcontainers tier."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto
from scree.gateway.app import create_app
from scree.knowledge.doc_service import DocService
from scree.knowledge.git_store import GitBackedDocStore
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

scenarios("migration.feature")

MIGRATOR = "svc:migrator"
SPACE = "platform/handbook"


@pytest.fixture
def world(git_repo) -> dict:
    doc_store = GitBackedDocStore(git_repo("docs"))
    # The pipeline writes migrated docs as author "migrator" (not the svc principal).
    doc_writer = DocService(doc_store, Authority({"migrator": {SPACE}}))
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=TicketStore(), ticket_authority=TicketAuthority(FakeOpenFga(), set()),
        comment_store=CommentStore(), ticket_crypto=FernetCrypto(),
        identity_directory=IdentityDirectory(), doc_writer=doc_writer,
        service_principals={MIGRATOR}, allow_insecure_header_auth=True,
    )
    return {"client": TestClient(app), "response": None}


def _run(world, items):
    return world["client"].post("/migration/run", json={"items": items}, headers={"X-Spike-User": MIGRATOR})


@given(parsers.parse('Jira issue "{old_id}" is not marked for migration by the curation deadline'))
def unmarked_issue(world, old_id):
    world["items"] = [{"kind": "jira", "old_id": old_id, "title": "t", "content": "c", "marked": False}]


@given(parsers.parse('doc "{doc_id}" links to legacy URL for Confluence page "{page}"'))
def doc_links_legacy(world, doc_id, page):
    pass  # narrative; the mapping is asserted by the resolve below


@given(parsers.parse('"confluence:{page}" is mapped to "{target}"'))
def confluence_mapped(world, page, target):
    # Establish the mapping the way production does: migrate the (curated) page.
    resp = _run(world, [{"kind": "confluence", "old_id": page, "title": "Onboarding",
                         "content": "body", "marked": True, "space": SPACE}])
    assert resp.json()["migrated"] == 1


@when("the migration pipeline runs")
def pipeline_runs(world):
    world["response"] = _run(world, world["items"])


@when("a user follows the link")
def follow_link(world):
    world["response"] = world["client"].get("/migration/resolve/confluence:12345", headers={"X-Spike-User": "rivera"})


@then(parsers.parse('no ticket is created for "{old_id}"'))
def no_ticket(world):
    assert world["response"].json()["migrated"] == 0


@then(parsers.parse('"{old_id}" remains available in the read-only archive'))
def in_archive(world):
    assert world["response"].json()["archived"] >= 1


@then("they are resolved to the migrated doc, not a broken link")
def resolved(world):
    assert world["response"].status_code == 200
    assert world["response"].json()["resolved"]  # a real target, not a 404
