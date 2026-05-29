"""@api @security BDD — canonical aggregation_permissions.feature (INV-AGG): an
aggregation/search view never leaks an item the viewer couldn't read directly. The
stale-cache fail-closed scenario describes behavior the system deliberately does NOT
implement within the cache TTL (the documented INV-ACC-5 / INV-DEG-1 tension,
gaps.md G-A2), so it is bound but xfail'd rather than faked."""

import json

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, scenarios, then, when

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.risk.git_store import GitBackedRiskStore
from scree.risk.models import Risk

SERVICE = "svc:indexer"


@pytest.mark.xfail(
    reason="within the cache TTL the Gateway serves last-known grants (INV-DEG-1); "
    "fail-closed only past LAST_KNOWN_MAX_AGE. Documented INV-ACC-5/INV-DEG-1 tension "
    "(gaps.md G-A2); exercised in test_membership_staleness.py + @contract.",
    run=False,
)
@scenario("aggregation_permissions.feature", "Stale permission cache fails closed")
def test_stale_cache_gap():
    pass


scenarios("aggregation_permissions.feature")


@pytest.fixture
def world(git_repo) -> dict:
    return {"readable": {}, "store": GitBackedRiskStore(git_repo("risks")), "response": None}


def _seed_risk(world, rid, space, category="delivery"):
    world["store"].put(Risk(id=rid, title=f"title-{rid}", space=space, category=category,
                            likelihood=1, impact=1, strategy="mitigated"))


def _client(world) -> TestClient:
    app = create_app(DocStore([]), Authority(world["readable"]),
                     risk_store=world["store"], service_principals={SERVICE},
                     allow_insecure_header_auth=True)
    return TestClient(app)


def _ids(response) -> set[str]:
    body = response.json()
    rows = body["results"] if isinstance(body, dict) else body
    return {r["id"] for r in rows}


@given(parsers.parse('the user "{user}" is a member of space "{s1}" and "{s2}"'))
def member_two(world, user, s1, s2):
    world["readable"][user] = {s1, s2}


@given(parsers.parse('the user "{user}" is a member of "{space}" only'))
def member_one(world, user, space):
    world["readable"][user] = {space}


@given(parsers.parse('"{user}" is not a member of "{space}"'))
def not_member(world, user, space):
    world["readable"].setdefault(user, set()).discard(space)


@given(parsers.parse('risk "{rid}" lives in "{space}"'))
def risk_lives(world, rid, space):
    _seed_risk(world, rid, space)


@given(parsers.parse('risk "{rid}" in "{space}" has category "{category}"'))
def risk_category(world, rid, space, category):
    world["store"].put(Risk(id=rid, title="credential exposure", space=space, category=category,
                            likelihood=3, impact=3, strategy="mitigated"))


@when(parsers.parse('"{user}" queries the cross-project risk register'))
def query_register(world, user):
    world["response"] = _client(world).get("/risks", headers={"X-Spike-User": user})


@when(parsers.parse('"{user}" searches all risks for the term "{term}"'))
def search_risks(world, user, term):
    client = _client(world)
    client.post("/index/reindex", headers={"X-Spike-User": SERVICE})  # batch builds the index from Git
    world["response"] = client.get("/search", params={"q": term}, headers={"X-Spike-User": user})


@then(parsers.parse('the results include "{rid}"'))
def results_include(world, rid):
    assert rid in _ids(world["response"])


@then(parsers.parse('the results exclude "{rid}"'))
def results_exclude(world, rid):
    assert rid not in _ids(world["response"])


@then(parsers.parse("the result count is {n:d}"))
def result_count(world, n):
    assert len(_ids(world["response"])) == n


@then(parsers.parse('no title, score, or excerpt of "{rid}" appears anywhere in the response'))
def no_leak(world, rid):
    blob = json.dumps(world["response"].json())
    assert rid not in blob and f"title-{rid}" not in blob
