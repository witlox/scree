"""@api BDD — canonical slack_capture.feature (DD-012/013, INV-ID-2/SLACK-1). The
Slack bot posts to the Gateway as a service principal; user identities ride in the
event. Autocomplete has no Gateway endpoint → bound but xfail'd."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, scenarios, then, when

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto
from scree.gateway.app import create_app
from scree.integration.slack.capture import CaptureRateLimiter, SlackDirectory
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

BOT = "svc:slackbot"
SNAPSHOT = "captured thread content"
OKAFOR = "ext:r.okafor@uni.example.ac"


@pytest.mark.xfail(reason="no Gateway Slack-autocomplete endpoint; link-ticket enforces visibility instead", run=False)
@scenario("slack_capture.feature", "Autocomplete only offers tickets the user may see")
def test_autocomplete_gap():
    pass


scenarios("slack_capture.feature")


@pytest.fixture
def world() -> dict:
    slack_dir = SlackDirectory()
    id_dir = IdentityDirectory()
    fga = FakeOpenFga()
    agents: set[str] = set()
    store = TicketStore()
    comments = CommentStore()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(fga, agents),
        comment_store=comments, ticket_crypto=FernetCrypto(), identity_directory=id_dir,
        slack_directory=slack_dir, slack_rate_limiter=CaptureRateLimiter(),
        service_principals={BOT}, allow_insecure_header_auth=True,
    )
    return {"slack": slack_dir, "id_dir": id_dir, "fga": fga, "agents": agents,
            "store": store, "comments": comments, "client": TestClient(app),
            "author": None, "response": None}


def _capture(world, reactor, author):
    return world["client"].post(
        "/slack/capture", json={"reactor": reactor, "author": author, "snapshot": SNAPSHOT},
        headers={"X-Spike-User": BOT},
    )


@given(parsers.parse('the public community channel "{channel}" exists'))
def channel_exists(world, channel):
    pass


@given(parsers.parse('Slack user "{slack_user}" maps to Keycloak "{identity}"'))
def maps_to(world, slack_user, identity):
    world["slack"]._map[slack_user] = identity
    if identity.startswith("agent:"):
        world["agents"].add(identity)  # an internal agent identity


@given(parsers.parse('Slack user "{slack_user}" maps to no Keycloak identity'))
def maps_to_none(world, slack_user):
    pass  # absence from the directory => resolve() returns None


@given(parsers.parse('a thread in "{channel}" started by "{user}"'))
@given(parsers.parse('a message in "{channel}" authored by "{user}"'))
def authored_by(world, channel, user):
    world["author"] = user


@given(parsers.parse('"{user}" can see ticket "{ticket_id}"'))
def can_see_ticket(world, user, ticket_id):
    oid = world["id_dir"].resolve(world["slack"].resolve(user))
    world["store"].put(Ticket(id=ticket_id, requester=oid))
    world["fga"].write(oid, "requester", ticket_id)


@given(parsers.parse('"{user}" cannot see ticket "{ticket_id}"'))
def cannot_see_ticket(world, user, ticket_id):
    world["store"].put(Ticket(id=ticket_id, requester="someone-else"))


@given(parsers.parse('"{user}" has created {n:d} captures in the last minute'))
def prior_captures(world, user, n):
    for _ in range(n):
        assert _capture(world, user, user).json()["action"] == "captured"


@when(parsers.parse('"{reactor}" adds the ":ticket:" reaction to the thread'))
@when(parsers.parse('"{reactor}" adds the ":ticket:" reaction to a thread'))
@when(parsers.parse('"{reactor}" adds the ":ticket:" reaction to that message'))
@when(parsers.parse('"{reactor}" adds another ":ticket:" reaction'))
def add_reaction(world, reactor):
    world["response"] = _capture(world, reactor, world["author"] or reactor)


@when(parsers.parse('"{reactor}" runs "/link-ticket {short}" in a thread'))
def run_link(world, reactor, short):
    world["response"] = world["client"].post(
        "/slack/link-ticket",
        json={"reactor": reactor, "ticket_id": "ticket-2026-000123", "snapshot": SNAPSHOT},
        headers={"X-Spike-User": BOT},
    )


@then(parsers.parse('a draft ticket is created with requester "{identity}"'))
def draft_created(world, identity):
    body = world["response"].json()
    assert body["action"] == "captured"
    assert body["requester"] == world["id_dir"].resolve(identity)  # opaque, INV-DP-1


@then("the ticket is not community_visible")
@then("the ticket is requester-private")
def not_visible(world):
    assert world["store"].get(world["response"].json()["ticket"]).community_visible is False


@then("the thread content at this moment is captured as a snapshot")
def snapshot_captured(world):
    tid = world["response"].json()["ticket"]
    assert any(c.body == SNAPSHOT for c in world["comments"].for_ticket(tid))


@then("the bot acknowledges in the thread")
def bot_acks(world):
    assert world["response"].json()["action"] == "captured"  # success => the bot acks


@then(parsers.parse('"{identity}" is recorded as the capturer'))
def capturer_recorded(world, identity):
    assert world["response"].json()["captured_by"] == identity


@then(parsers.parse('the thread snapshot is attached to "{ticket_id}"'))
def snapshot_attached(world, ticket_id):
    assert world["response"].json()["action"] == "linked"
    assert any(c.body == SNAPSHOT for c in world["comments"].for_ticket(ticket_id))


@then("the action is refused")
@then("the capture is rate-limited and not created")
def action_refused(world):
    assert world["response"].json()["action"] == "refused"


@then("no ticket is created")
def no_ticket(world):
    assert world["store"].all() == []


@then("the bot explains that identity could not be resolved")
def explains_identity(world):
    assert "identity" in world["response"].json()["reason"].lower()


@then("the bot explains the limit")
def explains_limit(world):
    assert "rate" in world["response"].json()["reason"].lower()
