"""@api BDD — ticket ReBAC read at the Gateway, using the faithful FakeOpenFga
(the @contract tier validates the real engine). Validates AR-04 / INV-ACC-2."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

scenarios("tickets_read.feature")


@pytest.fixture
def world() -> dict:
    return {"tickets": [], "fga": FakeOpenFga(), "agents": set(), "response": None}


@pytest.fixture
def client(world) -> TestClient:
    app = create_app(
        DocStore([]),
        Authority({}),
        ticket_store=TicketStore(world["tickets"]),
        ticket_authority=TicketAuthority(world["fga"], world["agents"]),
        allow_insecure_header_auth=True,
    )
    return TestClient(app)


@given(parsers.parse('ticket "{ticket_id}" requested by "{requester}"'))
def add_ticket(world, ticket_id, requester):
    world["tickets"].append(Ticket(id=ticket_id, requester=requester))
    world["fga"].write(requester, "requester", ticket_id)


@given(parsers.parse('"{user}" is a watcher of "{ticket_id}"'))
def add_watcher(world, user, ticket_id):
    world["fga"].write(user, "watcher", ticket_id)


@given(parsers.parse('"{agent}" is a desk agent'))
def add_agent(world, agent):
    world["agents"].add(agent)


@when(parsers.parse('"{principal}" lists tickets'))
def list_tickets(world, client, principal):
    world["response"] = client.get("/tickets", headers={"X-Spike-User": principal})


@when(parsers.parse('"{principal}" reads ticket "{ticket_id}"'))
def read_ticket(world, client, principal, ticket_id):
    world["response"] = client.get(f"/tickets/{ticket_id}", headers={"X-Spike-User": principal})


@then(parsers.parse('the ticket results include "{ticket_id}"'))
def results_include(world, ticket_id):
    assert ticket_id in [t["id"] for t in world["response"].json()]


@then(parsers.parse('the ticket results exclude "{ticket_id}"'))
def results_exclude(world, ticket_id):
    assert ticket_id not in [t["id"] for t in world["response"].json()]


@then(parsers.parse("the ticket response status is {status:d}"))
def check_status(world, status):
    assert world["response"].status_code == status
