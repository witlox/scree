"""@api BDD — canonical portal.feature: the @api slices (community KB search, self-
service preferences). The @e2e login/submit/reply journeys run in the Playwright tier."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

scenarios("portal.feature")


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


@given(parsers.parse('"{principal}" is authenticated via Keycloak'))
def authenticated(world, principal):
    pass  # header-auth stands in for the verified bearer in this tier


@given(parsers.parse('"{ticket_id}" is resolved and community_visible'))
def resolved_visible(world, ticket_id):
    world["store"].put(Ticket(
        id=ticket_id, requester="ext:owner", status="resolved", community_visible=True,
        community_snapshot=(("agent:dani", "to reset your API key, use the portal", "web"),),
    ))


@given(parsers.parse('"{ticket_id}" is resolved and not community_visible'))
def resolved_not_visible(world, ticket_id):
    world["store"].put(Ticket(id=ticket_id, requester="ext:other", status="resolved", community_visible=False))


@when(parsers.parse('"{principal}" searches the community knowledge base for "{term}"'))
def search_kb(world, principal, term):
    world["response"] = world["client"].get("/community/search", params={"q": term}, headers={"X-Spike-User": principal})


@when(parsers.parse('"{principal}" sets email notifications to "{preference}"'))
def set_prefs(world, principal, preference):
    world["principal"] = principal
    world["response"] = world["client"].put(
        "/portal/preferences", json={"preference": preference}, headers={"X-Spike-User": principal}
    )


@then(parsers.parse('"{ticket_id}" may appear'))
def may_appear(world, ticket_id):
    assert ticket_id in {h["id"] for h in world["response"].json()}


@then(parsers.parse('"{ticket_id}" never appears'))
def never_appears(world, ticket_id):
    assert ticket_id not in {h["id"] for h in world["response"].json()}


@then("the preference is saved and applied to future notifications")
def preference_saved(world):
    saved = world["client"].get("/portal/preferences", headers={"X-Spike-User": world["principal"]}).json()
    assert saved["preference"] == world["response"].json()["preference"]
