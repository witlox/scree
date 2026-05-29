"""@api BDD — binds canonical ticket_lifecycle.feature at the Gateway (INV-LC-1/2)."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.audit import AuditSink
from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

scenarios("ticket_lifecycle.feature")

AGENT = "agent:dani"


@pytest.fixture
def world() -> dict:
    store = TicketStore()
    fga = FakeOpenFga()
    audit = AuditSink()
    agents = {AGENT}
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(fga, agents),
        comment_store=CommentStore(), ticket_crypto=FernetCrypto(), audit=audit,
        allow_insecure_header_auth=True,
    )
    return {"store": store, "fga": fga, "audit": audit, "client": TestClient(app), "response": None}


def _set(world, ticket_id, **changes):
    existing = world["store"].get(ticket_id)
    if existing is None:
        existing = Ticket(id=ticket_id, requester="ext:r.okafor@uni.example.ac")
        world["store"].put(existing)
        world["fga"].write(existing.requester, "requester", ticket_id)
    world["store"].put(replace(world["store"].get(ticket_id), **changes))


@given(parsers.parse('ticket "{ticket_id}" has requester "{requester}"'))
def has_requester(world, ticket_id, requester):
    _set(world, ticket_id, requester=requester)
    world["fga"].write(requester, "requester", ticket_id)


@given(parsers.parse('ticket "{ticket_id}" has assignee "{assignee}"'))
def has_assignee(world, ticket_id, assignee):
    _set(world, ticket_id, assignee=assignee)


@given(parsers.parse('ticket "{ticket_id}" is "{status}"'))
def is_status(world, ticket_id, status):
    _set(world, ticket_id, status=status)


@given(parsers.parse('ticket "{ticket_id}" is "{status}" and not community_visible'))
def status_not_visible(world, ticket_id, status):
    _set(world, ticket_id, status=status, community_visible=False)


@given(parsers.parse('ticket "{ticket_id}" is "{status}" and community_visible'))
def status_visible(world, ticket_id, status):
    # Promote legitimately so community_snapshot is set as it would be in production.
    _set(world, ticket_id, status="resolved", community_visible=False)
    world["client"].post(f"/tickets/{ticket_id}/community-visible", headers={"X-Spike-User": AGENT})
    _set(world, ticket_id, status=status)


@when(parsers.parse('"{principal}" transitions it to "{status}"'))
@when(parsers.parse('"{principal}" transitions "{ticket_id}" to "{status}"'))
def transition(world, principal, status, ticket_id="ticket-2026-000123"):
    world["response"] = world["client"].patch(
        f"/tickets/{ticket_id}", json={"status": status}, headers={"X-Spike-User": principal}
    )


@when(parsers.parse('"{principal}" promotes it to community_visible with confirmation'))
@when(parsers.parse('"{principal}" attempts to promote it to community_visible'))
def promote(world, principal, ticket_id="ticket-2026-000123"):
    world["response"] = world["client"].post(
        f"/tickets/{ticket_id}/community-visible", headers={"X-Spike-User": principal}
    )


@then(parsers.parse('the ticket status is "{status}"'))
def check_status(world, status):
    assert world["store"].get("ticket-2026-000123").status == status


@then("the transition is rejected")
@then("the promotion is rejected")
def rejected(world):
    assert world["response"].status_code >= 400


@then(parsers.parse('"{ticket_id}" is community_visible'))
def visible(world, ticket_id):
    assert world["store"].get(ticket_id).community_visible is True


@then(parsers.parse('"{ticket_id}" is no longer community_visible'))
def not_visible(world, ticket_id):
    assert world["store"].get(ticket_id).community_visible is False


@then("a curated snapshot is published, not the live thread")
def snapshot_published(world):
    # The frozen snapshot (INV-LC-2) is set at promotion; later replies are not in it.
    assert world["store"].get("ticket-2026-000123").community_snapshot is not None


@then("the promotion is recorded in the audit trail")
def promotion_audited(world):
    assert any(
        e.resource.endswith("/community-visible") and e.result == 200
        for e in world["audit"].events()
    )
    assert world["audit"].verify()  # INV-ID-3: chain intact


@then("it must be re-promoted to become community-visible again")
def must_re_promote(world):
    # Re-gated: the snapshot was discarded on reopen, so a future promote rebuilds it.
    assert world["store"].get("ticket-2026-000123").community_snapshot is None
