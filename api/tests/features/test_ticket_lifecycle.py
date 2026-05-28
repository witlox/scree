"""@api BDD — ticket lifecycle at the Gateway (INV-LC-1/2)."""

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

scenarios("ticket_lifecycle.feature")


@pytest.fixture
def world() -> dict:
    return {"store": TicketStore(), "fga": FakeOpenFga(), "agents": set(), "response": None}


@pytest.fixture
def client(world) -> TestClient:
    authority = TicketAuthority(world["fga"], world["agents"])
    return TestClient(
        create_app(DocStore([]), Authority({}), ticket_store=world["store"], ticket_authority=authority, allow_insecure_header_auth=True)
    )


@given(parsers.parse('ticket "{ticket_id}" requested by "{requester}" assigned to "{assignee}"'))
def add_ticket(world, ticket_id, requester, assignee):
    world["store"].put(Ticket(id=ticket_id, requester=requester, assignee=assignee))
    world["fga"].write(requester, "requester", ticket_id)


@given(parsers.parse('"{agent}" is a desk agent'))
def add_agent(world, agent):
    world["agents"].add(agent)


@when(parsers.parse('"{principal}" transitions "{ticket_id}" to "{status}"'))
def do_transition(world, client, principal, ticket_id, status):
    world["response"] = client.patch(
        f"/tickets/{ticket_id}", json={"status": status}, headers={"X-Spike-User": principal}
    )


@when(parsers.parse('"{principal}" promotes "{ticket_id}" to community-visible'))
def do_promote(world, client, principal, ticket_id):
    world["response"] = client.post(
        f"/tickets/{ticket_id}/community-visible", headers={"X-Spike-User": principal}
    )


@then(parsers.parse('ticket "{ticket_id}" status is "{status}"'))
def check_status(world, ticket_id, status):
    assert world["store"].get(ticket_id).status == status


@then(parsers.parse("the transition is rejected with {code:d}"))
def transition_rejected(world, code):
    assert world["response"].status_code == code


@then(parsers.parse("the promotion is rejected with {code:d}"))
def promotion_rejected(world, code):
    assert world["response"].status_code == code


@then(parsers.parse('ticket "{ticket_id}" is community-visible'))
def is_visible(world, ticket_id):
    assert world["store"].get(ticket_id).community_visible is True


@then(parsers.parse('ticket "{ticket_id}" is not community-visible'))
def not_visible(world, ticket_id):
    assert world["store"].get(ticket_id).community_visible is False
