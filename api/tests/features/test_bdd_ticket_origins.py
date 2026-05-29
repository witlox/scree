"""@api BDD — canonical ticket_origins.feature: every origin normalizes to one
record (the email-threading scenarios are @contract and skip here). The agent-merge
scenario has no Gateway endpoint yet, so it is bound but xfail'd (honest gap)."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, scenarios, then, when

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.quarantine import QuarantineStore
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


# --- @contract: inbound email threading (POST /tickets/inbound-email by the poller) ---
POLLER = "svc:poller"
SENDER = "r.okafor@uni.example.ac"


@pytest.fixture
def email_ctx() -> dict:
    store = TicketStore()
    quarantine = QuarantineStore()
    identity = IdentityDirectory()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), {"agent:dani"}),
        comment_store=CommentStore(), ticket_crypto=FernetCrypto(),
        identity_directory=identity, quarantine_store=quarantine,
        service_principals={POLLER}, allow_insecure_header_auth=True,
    )
    return {"store": store, "quarantine": quarantine, "identity": identity, "client": TestClient(app), "response": None}


def _raw(frm: str, subject: str, references: str = "") -> str:
    headers = [f"From: {frm}", f"Subject: {subject}", "Message-ID: <reply@mail>"]
    if references:
        headers.append(f"References: {references}")
    return "\n".join(headers) + "\n\nthe reply body\n"


def _ingest(email_ctx, raw, *, verified, sender):
    return email_ctx["client"].post(
        "/tickets/inbound-email", json={"raw": raw, "verified": verified, "sender": sender},
        headers={"X-Spike-User": POLLER},
    )


@given(parsers.parse('ticket "{ticket_id}" has email Message-ID "{message_id}"'))
def ticket_with_mid(email_ctx, ticket_id, message_id):
    # Requester = the verified sender's opaque id, so the reply threads (route() only
    # appends when the verified sender matches the ticket's requester).
    requester = email_ctx["identity"].resolve(SENDER)
    email_ctx["store"].put(Ticket(id=ticket_id, requester=requester, email_message_id=message_id))


@given(parsers.parse('ticket "{ticket_id}" has email_token "{token}"'))
def ticket_with_token(email_ctx, ticket_id, token):
    requester = email_ctx["identity"].resolve(SENDER)
    email_ctx["store"].put(Ticket(id=ticket_id, requester=requester, email_token=token))


@given(parsers.parse('ticket "{ticket_id}" has requester "{requester}"'))
def ticket_with_requester(email_ctx, ticket_id, requester):
    # Spoof scenario: the inbound is unverified, so route() quarantines regardless.
    email_ctx["store"].put(Ticket(id=ticket_id, requester=email_ctx["identity"].resolve(SENDER), email_token="SCREE-123"))


@when(parsers.parse('an inbound email arrives with References "{references}"'))
def inbound_with_references(email_ctx, references):
    email_ctx["response"] = _ingest(
        email_ctx, _raw("r.okafor@uni.example.ac", "Re: issue", references),
        verified=True, sender="r.okafor@uni.example.ac",
    )


@when(parsers.parse('an inbound email arrives with no References header and subject "{subject}"'))
def inbound_no_references(email_ctx, subject):
    email_ctx["response"] = _ingest(
        email_ctx, _raw("r.okafor@uni.example.ac", subject),
        verified=True, sender="r.okafor@uni.example.ac",
    )


@when(parsers.parse('an inbound email quoting "[{token}]" arrives from unverified sender "{sender}"'))
def inbound_spoofed(email_ctx, token, sender):
    email_ctx["response"] = _ingest(
        email_ctx, _raw(sender, f"Re: [{token}] export fails"), verified=False, sender=sender,
    )


@then(parsers.parse('the email is appended to "{ticket_id}"'))
def email_appended(email_ctx, ticket_id):
    body = email_ctx["response"].json()
    assert body["action"] == "append" and body["ticket"] == ticket_id


@then("no new ticket is created")
def no_new_ticket(email_ctx):
    assert len(email_ctx["store"].all()) == 1  # only the pre-existing ticket


@then("a new ticket is created")
def new_ticket_created(email_ctx):
    assert email_ctx["response"].json()["action"] == "new"


@then(parsers.parse('it is not appended to "{ticket_id}"'))
def not_appended(email_ctx, ticket_id):
    assert email_ctx["response"].json().get("ticket") != ticket_id


@then(parsers.parse('the email is not appended to "{ticket_id}"'))
def not_appended_to(email_ctx, ticket_id):
    assert email_ctx["response"].json()["action"] != "append"


@then("it is quarantined for agent review")
def quarantined(email_ctx):
    assert email_ctx["response"].json()["action"] == "quarantine"
    assert len(email_ctx["quarantine"].all()) == 1
