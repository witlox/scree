"""@api — gate-12 fixes: composed-authority reads survive a GitLab outage via
last-known membership (G12-01); slack_link and migration writes are refused during
an outage (G12-02)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.gitlab import FakeGitLabAuthority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore
from scree.platform.health import Availability
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

SPACE = "platform/handbook"


def test_composed_authority_reads_survive_gitlab_outage_via_last_known():
    # A counting GitLab authority so we can prove the outage path serves cached
    # membership without calling GitLab.
    class _Counting(FakeGitLabAuthority):
        def __init__(self):
            super().__init__(spaces={"rivera-token": {SPACE}})
            self.calls = 0

        def readable_spaces(self, token):
            self.calls += 1
            return super().readable_spaces(token)

    gitlab = _Counting()
    health = Availability()
    docs = DocStore([Doc(id="doc-a", title="A", space=SPACE, body="hello")])
    client = TestClient(create_app(
        docs, Authority({}), gitlab_authority=gitlab, availability=health,
        allow_insecure_header_auth=True,
    ))
    # Warm the membership (GitLab up) — this records last-known too.
    assert client.get("/docs", headers={"X-Spike-User": "rivera-token"}).status_code == 200
    health.gitlab_up = False
    gitlab.calls = 0
    # With GitLab down the authorized read still serves (from cache / last-known)
    # and never calls GitLab.
    ids = {d["id"] for d in client.get("/docs", headers={"X-Spike-User": "rivera-token"}).json()}
    assert ids == {"doc-a"}
    assert gitlab.calls == 0


def test_slack_link_refused_during_gitlab_outage():
    store = TicketStore([Ticket(id="t-1", requester="ext-1")])
    fga = FakeOpenFga()
    fga.write("ext-1", "requester", "t-1")
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(fga, agents=set()),
        service_principals={"svc:bot"}, availability=Availability(gitlab_up=False),
        allow_insecure_header_auth=True,
    )
    client = TestClient(app)
    resp = client.post("/slack/link-ticket",
                       json={"reactor": "u", "ticket_id": "t-1", "snapshot": "s"},
                       headers={"X-Spike-User": "svc:bot"})
    assert resp.status_code == 503


def test_migration_refused_during_gitlab_outage():
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=TicketStore(), ticket_authority=TicketAuthority(FakeOpenFga(), agents=set()),
        service_principals={"svc:mig"}, availability=Availability(gitlab_up=False),
        allow_insecure_header_auth=True,
    )
    client = TestClient(app)
    item = {"kind": "jira", "old_id": "SUP-1", "title": "t", "content": "c", "marked": True}
    resp = client.post("/migration/run", json={"items": [item]}, headers={"X-Spike-User": "svc:mig"})
    assert resp.status_code == 503
