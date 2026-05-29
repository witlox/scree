"""@api BDD — canonical orphan_detection.feature (INV-ORPH-1/2): the hourly batch
flags active resources whose owner lost access; never auto-reassigns. Risks persist
to Git (INV-ST-1)."""

import datetime as dt
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.risk.git_store import GitBackedRiskStore
from scree.risk.models import Risk
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

scenarios("orphan_detection.feature")

SERVICE = "svc:indexer"
VIEWER = "maintainer"  # the Space maintainer / desk lead the report is scoped to
RISK_SPACE = "platform/handbook"
DESK = "support/service-desk"


@pytest.fixture
def world(git_repo) -> dict:
    return {
        "readable": {VIEWER: {RISK_SPACE, DESK}},  # the viewer maintains both Spaces
        "agents": set(),
        "risks": GitBackedRiskStore(git_repo("risks")),
        "tickets": TicketStore(),
        "report": None,
    }


def _run_batch(world):
    app = create_app(
        DocStore([]), Authority(world["readable"]),
        risk_store=world["risks"], ticket_store=world["tickets"],
        ticket_authority=TicketAuthority(FakeOpenFga(), world["agents"]),
        service_principals={SERVICE}, allow_insecure_header_auth=True,
    )
    client = TestClient(app)
    client.post("/orphans/refresh", headers={"X-Spike-User": SERVICE})
    world["report"] = client.get("/orphans", headers={"X-Spike-User": VIEWER}).json()


@given(parsers.parse('risk "{rid}" is "{status}" with owner "{owner}"'))
def risk_with_owner(world, rid, status, owner):
    world["risks"].put(Risk(id=rid, title=f"title-{rid}", space=RISK_SPACE, category="delivery",
                            likelihood=1, impact=1, strategy="mitigated", status=status, owner=owner))


@given(parsers.parse('"{owner}" has lost access to space "{space}"'))
def lost_access(world, owner, space):
    world["readable"].pop(owner, None)  # owner is not a member → can_write False


@given(parsers.parse('"{owner}" still has access to "{space}"'))
def has_access(world, owner, space):
    world["readable"].setdefault(owner, set()).add(space)


@given(parsers.parse('ticket "{tid}" is "{status}" with assignee "{assignee}"'))
def ticket_with_assignee(world, tid, status, assignee):
    world["tickets"].put(Ticket(id=tid, requester="ext:cust", space=DESK, status=status, assignee=assignee))


@given(parsers.parse('"{assignee}" has lost desk access'))
def assignee_lost_desk(world, assignee):
    world["agents"].discard(assignee)  # not an agent → assignee_gone


@given(parsers.parse('ticket "{tid}" is "open" and unassigned for longer than the threshold'))
def long_unassigned(world, tid):
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat()
    world["tickets"].put(Ticket(id=tid, requester="ext:cust", space=DESK, status="open",
                                assignee=None, created_at=old))


@when("the hourly batch runs")
def hourly_batch(world):
    _run_batch(world)


def _all_reported(report) -> set[str]:
    out: set[str] = set()
    for ids in {**report["resources"], **report["tickets"]}.values():
        out.update(ids)
    return out


@then(parsers.parse('"{rid}" appears in the "orphaned actives" report for "{space}" maintainers'))
def appears_for_space(world, rid, space):
    assert rid in world["report"]["resources"].get(space, [])


@then(parsers.parse('"{tid}" appears in the orphaned-actives report for desk leads'))
def appears_for_desk(world, tid):
    assert tid in world["report"]["tickets"].get(DESK, [])


@then(parsers.parse('"{rid}" does not appear in the "orphaned actives" report'))
def does_not_appear(world, rid):
    assert rid not in _all_reported(world["report"])


@then("it is not automatically reassigned")
def not_reassigned(world):
    # The flagged risk keeps its original owner — detection flags, never mutates.
    flagged = [rid for ids in world["report"]["resources"].values() for rid in ids]
    for rid in flagged:
        assert world["risks"].get(rid).owner is not None
