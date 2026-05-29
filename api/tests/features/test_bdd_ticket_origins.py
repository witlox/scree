"""@api BDD — canonical ticket_origins.feature: every origin normalizes to one
record (the email-threading scenarios are @contract and skip here). The agent-merge
scenario has no Gateway endpoint yet, so it is bound but xfail'd (honest gap)."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, scenarios, then, when

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore


@pytest.mark.xfail(reason="no Gateway ticket-merge endpoint yet (merge is domain-level only)", run=False)
@scenario("ticket_origins.feature", "An agent can merge two tickets that were the same conversation")
def test_merge_gap():
    pass


scenarios("ticket_origins.feature")  # binds the rest; the merge scenario above is excluded


@pytest.fixture
def world() -> dict:
    store = TicketStore()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), set()),
        comment_store=CommentStore(), ticket_crypto=FernetCrypto(),
        allow_insecure_header_auth=True,
    )
    return {"store": store, "client": TestClient(app), "response": None}


@when(parsers.parse('a ticket is created from "{origin}" by "{requester}"'))
def create_from_origin(world, origin, requester):
    world["response"] = world["client"].post(
        "/tickets", json={"origin": origin}, headers={"X-Spike-User": requester}
    )


@then(parsers.parse('a ticket exists with requester "{requester}"'))
def ticket_exists(world, requester):
    assert world["response"].status_code == 200
    assert world["response"].json()["requester"] == requester


@then(parsers.parse('its origin is "{origin}"'))
def origin_is(world, origin):
    assert world["response"].json()["origin"] == origin


@then("it is requester-private by default")
def requester_private(world):
    assert world["response"].json()["community_visible"] is False
