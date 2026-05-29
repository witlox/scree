"""@api BDD — canonical risk_register.feature. Risks persist to Git (INV-ST-1/2).
Escalation and close-via-MR have no Gateway endpoint yet → bound but xfail'd."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, scenarios, then, when

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.risk.git_store import GitBackedRiskStore

SPACE = "platform/handbook"
ACTOR = "platform-team-lead"
SERVICE = "svc:indexer"


@pytest.mark.xfail(reason="no Gateway risk-escalation endpoint yet (covered at unit: test_risk_register.py)", run=False)
@scenario("risk_register.feature", "Escalating a project risk creates an org duplicate with a cross-reference")
def test_escalation_gap():
    pass


@pytest.mark.xfail(reason="no Gateway risk-close endpoint; branch protection is a GitLab/deploy mechanism (INV-GOV-1)", run=False)
@scenario("risk_register.feature", "Closing a risk requires a merge request")
def test_close_mr_gap():
    pass


scenarios("risk_register.feature")


def _factors(score: int) -> tuple[int, int]:
    for likelihood in range(1, 6):
        if score % likelihood == 0 and 1 <= score // likelihood <= 5:
            return likelihood, score // likelihood
    raise ValueError(f"no 1-5 factor pair for score {score}")


@pytest.fixture
def world(git_repo) -> dict:
    store = GitBackedRiskStore(git_repo("risks"))
    app = create_app(
        DocStore([]), Authority({ACTOR: {SPACE}}),
        risk_store=store, service_principals={SERVICE},
        allow_insecure_header_auth=True,
    )
    return {"store": store, "client": TestClient(app), "created": {}, "response": None}


def _create(world, user, space, category, likelihood, impact, title="risk"):
    return world["client"].post(
        "/risks",
        json={"title": title, "space": space, "category": category, "likelihood": likelihood, "impact": impact},
        headers={"X-Spike-User": user},
    )


@when(parsers.parse('"{user}" creates risk "{risk_id}" with likelihood {likelihood:d} and impact {impact:d}'))
def create_risk(world, user, risk_id, likelihood, impact):
    world["response"] = _create(world, user, SPACE, "delivery", likelihood, impact)


@given(parsers.parse('risk "{risk_id}" has category "{category}" and score {score:d}'))
def risk_with_score(world, risk_id, category, score):
    likelihood, impact = _factors(score)
    r = _create(world, ACTOR, SPACE, category, likelihood, impact, title=f"title-{risk_id}")
    world["created"][risk_id] = r.json()


@when(parsers.parse('"{risk_id}" is updated'))
def updated(world, risk_id):
    world["response"] = None  # the create response already carries the trigger verdict


@then(parsers.parse("its score is {score:d}"))
def score_is(world, score):
    assert world["response"].json()["score"] == score


@then(parsers.parse('its severity band is "{band}"'))
def severity_is(world, band):
    assert world["response"].json()["severity"] == band


@then(parsers.parse('the near-real-time indexing webhook fires for "{risk_id}"'))
def webhook_fires(world, risk_id):
    assert world["created"][risk_id]["fires_critical_webhook"] is True


@then(parsers.parse('no near-real-time webhook fires for "{risk_id}"'))
def no_webhook(world, risk_id):
    assert world["created"][risk_id]["fires_critical_webhook"] is False


@then(parsers.parse('"{risk_id}" is picked up by the next hourly batch'))
def batch_pickup(world, risk_id):
    # The batch is a full reindex from Git (INV-IX-2): the non-webhook risk still
    # becomes searchable, so correctness never depends on webhook delivery.
    assert world["client"].post("/index/reindex", headers={"X-Spike-User": SERVICE}).status_code == 200
    hits = world["client"].get("/search", params={"q": f"title-{risk_id}"}, headers={"X-Spike-User": ACTOR}).json()
    assert world["created"][risk_id]["id"] in {h["id"] for h in hits["results"]}
