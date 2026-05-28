"""@api BDD — binds planning.feature at the Gateway (TestClient). Validates the
architected aggregation invariant (INV-AGG: a planning rollup never reveals an
epic the viewer couldn't see in GitLab) and the as-of staleness marker."""

import datetime as dt
import json

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.planning.authority import PlanningAuthority
from scree.planning.index import PlanningIndex
from scree.planning.models import Epic

scenarios("planning.feature")

READABLE_CAPACITY = 13
HIDDEN_CAPACITY = 7  # distinct, so a capacity leak would be detectable


@pytest.fixture
def world() -> dict:
    return {"epics": [], "readable": {}, "as_of": None, "response": None}


def _group_for(epic_id: str) -> str:
    return f"grp-{epic_id}"


@given(parsers.parse('epic "{epic_id}" is in a group "{principal}" can read'))
def epic_readable(world, epic_id, principal):
    group = _group_for(epic_id)
    world["epics"].append(Epic(id=epic_id, group=group, title=f"Title {epic_id}", capacity=READABLE_CAPACITY))
    world["readable"].setdefault(principal, set()).add(group)


@given(parsers.parse('epic "{epic_id}" is in a group "{principal}" cannot read'))
def epic_hidden(world, epic_id, principal):
    group = _group_for(epic_id)
    world["epics"].append(Epic(id=epic_id, group=group, title=f"Title {epic_id}", capacity=HIDDEN_CAPACITY))
    world["readable"].setdefault(principal, set())  # principal exists but not in this group


@given(parsers.parse("the planning index was last refreshed {minutes:d} minutes ago"))
def stale_index(world, minutes):
    when_ts = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes)
    world["as_of"] = when_ts.isoformat()


@when(parsers.parse('"{principal}" opens the portfolio rollup'))
def open_rollup(world, principal):
    index = PlanningIndex(world["epics"], last_indexed=world["as_of"])
    app = create_app(
        DocStore([]), Authority({}),
        planning_index=index,
        planning_authority=PlanningAuthority(world["readable"]),
        allow_insecure_header_auth=True,
    )
    world["response"] = TestClient(app).get("/planning/portfolio", headers={"X-Spike-User": principal})


@then(parsers.parse('"{epic_id}" contributes to the rollup'))
def contributes(world, epic_id):
    assert epic_id in [e["id"] for e in world["response"].json()["epics"]]


@then(parsers.parse('"{epic_id}" does not contribute'))
def not_contributes(world, epic_id):
    assert epic_id not in [e["id"] for e in world["response"].json()["epics"]]


@then(parsers.parse('the existence of "{epic_id}" is not revealed (count, title, or capacity)'))
def existence_hidden(world, epic_id):
    body = world["response"].json()
    # title/id: not anywhere in the serialized response
    assert epic_id not in json.dumps(body)
    # count: only the visible epics are counted
    assert body["epic_count"] == len(body["epics"])
    # capacity: totals exclude the hidden epic (visible-only sum)
    assert body["total_capacity"] == READABLE_CAPACITY * body["epic_count"]


@then(parsers.parse('the view shows the "as of" timestamp so staleness is visible'))
def shows_as_of(world):
    assert world["response"].json()["as_of"] is not None
