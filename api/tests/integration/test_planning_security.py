"""@api — adversary gate-3 planning hardening:
G3-02 cursor pagination on the rollup, G3-03 fail-loud partial config +
never-indexed staleness signal. (G3-01 is an accepted bounded-staleness window,
disclosed via as_of/never_indexed — see impl-gate-3.md.)"""

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.planning.authority import PlanningAuthority
from scree.planning.index import PlanningIndex
from scree.planning.models import Epic

GROUP = "grp-1"


def _client(index, readable=None):
    return TestClient(create_app(
        DocStore([]), Authority({}),
        planning_index=index,
        planning_authority=PlanningAuthority(readable or {"rivera": {GROUP}}),
        allow_insecure_header_auth=True,
    ))


def _epics(n):
    return [Epic(id=f"EPIC-{i}", group=GROUP, title=f"T{i}", capacity=10) for i in range(n)]


# --- G3-02: pagination -------------------------------------------------------

def test_rollup_paginates_with_cursor():
    client = _client(PlanningIndex(_epics(5), last_indexed="2026-05-28T00:00:00+00:00"))
    p1 = client.get("/planning/portfolio?limit=2", headers={"X-Spike-User": "rivera"}).json()
    assert [e["id"] for e in p1["epics"]] == ["EPIC-0", "EPIC-1"]
    assert p1["next_cursor"] == 2
    # totals are over ALL visible epics, not just the page
    assert p1["epic_count"] == 5
    assert p1["total_capacity"] == 50

    p2 = client.get("/planning/portfolio?limit=2&cursor=2", headers={"X-Spike-User": "rivera"}).json()
    assert [e["id"] for e in p2["epics"]] == ["EPIC-2", "EPIC-3"]
    assert p2["next_cursor"] == 4

    p3 = client.get("/planning/portfolio?limit=2&cursor=4", headers={"X-Spike-User": "rivera"}).json()
    assert [e["id"] for e in p3["epics"]] == ["EPIC-4"]
    assert p3["next_cursor"] is None


def test_rollup_limit_is_bounded():
    client = _client(PlanningIndex(_epics(1), last_indexed="t"))
    assert client.get("/planning/portfolio?limit=9999", headers={"X-Spike-User": "rivera"}).status_code == 422
    assert client.get("/planning/portfolio?limit=0", headers={"X-Spike-User": "rivera"}).status_code == 422


# --- G3-03: fail-loud partial config + staleness signal ----------------------

def test_partial_planning_config_fails_loud():
    with pytest.raises(ValueError):
        create_app(DocStore([]), Authority({}),
                   planning_index=PlanningIndex(), allow_insecure_header_auth=True)
    with pytest.raises(ValueError):
        create_app(DocStore([]), Authority({}),
                   planning_authority=PlanningAuthority({}), allow_insecure_header_auth=True)


def test_never_indexed_is_signalled():
    fresh = _client(PlanningIndex())  # no last_indexed
    body = fresh.get("/planning/portfolio", headers={"X-Spike-User": "rivera"}).json()
    assert body["never_indexed"] is True
    assert body["as_of"] is None

    indexed = _client(PlanningIndex(_epics(1), last_indexed="2026-05-28T00:00:00+00:00"))
    body2 = indexed.get("/planning/portfolio", headers={"X-Spike-User": "rivera"}).json()
    assert body2["never_indexed"] is False
    assert body2["as_of"] == "2026-05-28T00:00:00+00:00"
