"""@api BDD — ticket creation normalized across origins (INV-DP-1, DD-013)."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.store import TicketStore

scenarios("ticket_create.feature")


@pytest.fixture
def world() -> dict:
    return {"response": None}


@pytest.fixture
def client() -> TestClient:
    authority = TicketAuthority(FakeOpenFga(), set())
    return TestClient(
        create_app(DocStore([]), Authority({}), ticket_store=TicketStore(), ticket_authority=authority, allow_insecure_header_auth=True)
    )


@when(parsers.parse('"{principal}" creates a ticket from "{origin}"'))
def create(world, client, principal, origin):
    world["response"] = client.post(
        "/tickets", json={"origin": origin, "requester": principal}, headers={"X-Spike-User": principal}
    )


@then(parsers.parse('the created ticket origin is "{origin}"'))
def check_origin(world, origin):
    assert world["response"].json()["origin"] == origin


@then(parsers.parse('the created ticket status is "{status}"'))
def check_status(world, status):
    assert world["response"].json()["status"] == status


@then("the created ticket is requester-private")
def check_private(world):
    assert world["response"].json()["community_visible"] is False


@then(parsers.parse('the created ticket requester is "{requester}"'))
def check_requester(world, requester):
    assert world["response"].json()["requester"] == requester
