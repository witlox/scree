"""@api/unit — gate-9 fixes: short-TTL caching of token-exchange + membership
(G9-01), fail-loud partial composed-authority config (G9-02)."""

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.cache import TtlCache
from scree.access.gitlab import FakeGitLabAuthority
from scree.access.token_exchange import StaticTokenExchanger
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore


class _DummyAuth:
    pass


class _CountingGitLab(FakeGitLabAuthority):
    def __init__(self, spaces):
        super().__init__(spaces=spaces)
        self.calls = 0

    def readable_spaces(self, token):
        self.calls += 1
        return super().readable_spaces(token)


def test_ttl_cache_basic():
    c: TtlCache[int] = TtlCache(ttl=60.0)
    assert c.get("k") is None
    c.put("k", 7)
    assert c.get("k") == 7


def test_membership_resolution_is_cached_across_requests():
    # G9-01: repeated reads for the same token resolve membership once (short TTL).
    gitlab = _CountingGitLab({"rivera-token": {"platform/handbook"}})
    app = create_app(
        DocStore([Doc(id="doc-a", title="A", space="platform/handbook", body="b")]),
        Authority({}), gitlab_authority=gitlab, allow_insecure_header_auth=True,
    )
    client = TestClient(app)
    for _ in range(3):
        assert client.get("/docs", headers={"X-Spike-User": "rivera-token"}).status_code == 200
    assert gitlab.calls == 1  # resolved once, then served from cache


def test_gitlab_authority_without_token_source_fails_loud():
    # G9-02: gitlab_authority + bearer auth but no token_exchanger → refuse to start.
    with pytest.raises(ValueError, match="token_exchanger"):
        create_app(DocStore([]), Authority({}), gitlab_authority=FakeGitLabAuthority(),
                   authenticator=_DummyAuth())


def test_dev_header_path_allows_gitlab_authority_without_exchanger():
    # The dev opt-in is an accepted token source (header doubles as the GitLab token).
    create_app(DocStore([]), Authority({}), gitlab_authority=FakeGitLabAuthority(),
               token_exchanger=StaticTokenExchanger(), allow_insecure_header_auth=True)
