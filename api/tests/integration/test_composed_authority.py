"""@api — composed real authority (I-03, G3-01). With a token-exchanger + a GitLab
SpaceAuthority configured, the Gateway exchanges the inbound bearer for a GitLab
token and filters docs/risks/planning by LIVE GitLab membership instead of the
spike stub. Unit-covers the RFC 8693 exchanger request shape."""

import datetime as dt

import httpx
import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.gitlab import FakeGitLabAuthority
from scree.access.token_exchange import KeycloakTokenExchanger, StaticTokenExchanger
from scree.access.oidc import AuthError
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.planning.authority import PlanningAuthority
from scree.planning.index import PlanningIndex
from scree.planning.models import Epic

SPACE = "platform/handbook"
GROUP = "eng"


def _client():
    # Header-auth dev path: X-Spike-User doubles as the GitLab token; the
    # FakeGitLabAuthority maps that token to live memberships.
    docs = DocStore([
        Doc(id="doc-a", title="A", space=SPACE, body="b"),
        Doc(id="doc-b", title="B", space="org/secret", body="b"),
    ])
    index = PlanningIndex(
        [Epic(id="EPIC-1", group=GROUP, title="t", capacity=5),
         Epic(id="EPIC-2", group="locked", title="t", capacity=5)],
        last_indexed=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    gitlab = FakeGitLabAuthority(
        spaces={"rivera-token": {SPACE}},
        groups={"rivera-token": {GROUP}},
    )
    app = create_app(
        docs, Authority({}),  # stub authority is unused once gitlab_authority is set
        risk_store=None,
        planning_index=index, planning_authority=PlanningAuthority({}),
        gitlab_authority=gitlab,
        token_exchanger=StaticTokenExchanger(),  # bearer -> downstream (unused on header path)
        allow_insecure_header_auth=True,
    )
    return TestClient(app)


def test_docs_filtered_by_live_gitlab_membership():
    client = _client()
    # rivera-token is a member of platform/handbook only → sees doc-a, not org/secret.
    ids = {d["id"] for d in client.get("/docs", headers={"X-Spike-User": "rivera-token"}).json()}
    assert ids == {"doc-a"}
    # A token with no memberships sees nothing (and the hidden doc isn't leaked).
    assert client.get("/docs", headers={"X-Spike-User": "nobody-token"}).json() == []
    assert client.get("/docs/doc-b", headers={"X-Spike-User": "rivera-token"}).status_code == 404


def test_planning_filtered_by_live_gitlab_group_membership():
    # G3-01: planning visibility uses LIVE group membership, not a stale index field.
    client = _client()
    body = client.get("/planning/portfolio", headers={"X-Spike-User": "rivera-token"}).json()
    assert [e["id"] for e in body["epics"]] == ["EPIC-1"]  # 'locked' group excluded
    assert body["epic_count"] == 1


# --- unit: RFC 8693 exchanger request shape ----------------------------------

def test_keycloak_exchanger_builds_rfc8693_request():
    captured = {}

    class _Client:
        def post(self, url, data=None):
            captured["url"] = url
            captured["data"] = data
            return httpx.Response(200, json={"access_token": "gitlab-token-xyz"})

    ex = KeycloakTokenExchanger("https://kc/realms/scree/protocol/openid-connect/token",
                                "scree-gateway", "secret", client=_Client())
    out = ex.exchange("inbound-subject-token", "gitlab")
    assert out == "gitlab-token-xyz"
    assert captured["data"]["grant_type"] == "urn:ietf:params:oauth:grant-type:token-exchange"
    assert captured["data"]["subject_token"] == "inbound-subject-token"
    assert captured["data"]["audience"] == "gitlab"


def test_keycloak_exchanger_raises_on_failure():
    class _Client:
        def post(self, url, data=None):
            return httpx.Response(400, text="nope")

    ex = KeycloakTokenExchanger("https://kc/token", "c", "s", client=_Client())
    with pytest.raises(AuthError):
        ex.exchange("t", "gitlab")
