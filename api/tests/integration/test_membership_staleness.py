"""@api — G-A2 / INV-ACC-5 vs INV-DEG-1: last-known membership is served during a
GitLab outage so authorized reads survive (INV-DEG-1), but only within
LAST_KNOWN_MAX_AGE. Past that bound the resolver fails closed (INV-ACC-5) rather than
honoring a possibly-revoked grant for the whole outage. A fake monotonic clock drives
both the short-TTL membership cache and the last-known bound."""

import time

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.gitlab import FakeGitLabAuthority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.platform.health import Availability

SPACE = "platform/handbook"


def test_last_known_membership_is_bounded(monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    gitlab = FakeGitLabAuthority(spaces={"tok": {SPACE}})
    health = Availability()
    docs = DocStore([Doc(id="doc-a", title="A", space=SPACE, body="hello")])
    client = TestClient(create_app(
        docs, Authority({}), gitlab_authority=gitlab, availability=health,
        allow_insecure_header_auth=True,
    ))

    # Warm membership while GitLab is up (records last-known at t=1000).
    assert client.get("/docs", headers={"X-Spike-User": "tok"}).status_code == 200

    health.gitlab_up = False
    # Past the 60s cache TTL but within the 900s last-known bound → served stale-OK.
    clock["t"] = 1000.0 + 120.0
    ids = {d["id"] for d in client.get("/docs", headers={"X-Spike-User": "tok"}).json()}
    assert ids == {"doc-a"}

    # Past the staleness bound → fail closed (do not honor a possibly-revoked grant).
    clock["t"] = 1000.0 + 1000.0
    ids = {d["id"] for d in client.get("/docs", headers={"X-Spike-User": "tok"}).json()}
    assert ids == set()
