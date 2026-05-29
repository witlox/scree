"""@contract BDD — canonical degradation.feature (INV-DEG-1/2, DD-003). Runs in the
contract tier. No external service is needed — the GitLab outage is simulated via
Availability — but the scenarios are @contract per the analyst tagging, so they execute
alongside the testcontainers-backed contract tests rather than in the fast @api run."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.platform.health import Availability
from scree.servicedesk.store import TicketStore

scenarios("degradation.feature")

SPACE = "platform/handbook"


@pytest.fixture
def world() -> dict:
    docs = DocStore([
        Doc(id="doc-platform-onboarding", title="Onboarding", space=SPACE, body="hello from the local clone"),
        Doc(id="doc-secret", title="Secret", space="org/secret", body="secret"),
    ])
    tickets = TicketStore()
    app = create_app(
        docs, Authority({"rivera": {SPACE}}),
        ticket_store=tickets, ticket_authority=TicketAuthority(FakeOpenFga(), set()),
        availability=Availability(gitlab_up=False),  # GitLab is unreachable
        allow_insecure_header_auth=True,
    )
    return {"tickets": tickets, "client": TestClient(app), "response": None}


@given("GitLab is unreachable")
def gitlab_unreachable(world):
    pass  # encoded in the fixture (Availability(gitlab_up=False))


@given(parsers.parse('a local clone of "{space}" exists for "{user}"'))
def local_clone(world, space, user):
    pass  # the DocStore stands in for the local clone; the user is authorized for it


@when(parsers.parse('"{user}" opens doc "{doc_id}"'))
def open_doc(world, user, doc_id):
    world["response"] = world["client"].get(f"/docs/{doc_id}", headers={"X-Spike-User": user})


@when(parsers.parse('"{user}" submits a new ticket'))
def submit_ticket(world, user):
    world["response"] = world["client"].post("/tickets", json={"origin": "web"}, headers={"X-Spike-User": user})


@when(parsers.parse('"{user}" attempts to read a doc in a space they do not belong to'))
def read_forbidden(world, user):
    world["response"] = world["client"].get("/docs/doc-secret", headers={"X-Spike-User": user})


@then("the doc renders from the local clone")
def doc_renders(world):
    assert world["response"].status_code == 200
    assert "clone" in world["response"].json()["body"]


@then("creation is refused with an error stating GitLab is unavailable")
def creation_refused(world):
    assert world["response"].status_code == 503
    assert "unavailable" in world["response"].json()["detail"].lower()


@then("no ticket is queued as if it had succeeded")
def no_ticket_queued(world):
    assert world["tickets"].all() == []  # terminal refusal — nothing created


@then("access is denied")
def access_denied(world):
    assert world["response"].status_code in (403, 404)  # existence-leak-safe
