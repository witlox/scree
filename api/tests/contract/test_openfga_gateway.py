"""@contract — the Gateway's /tickets path against a REAL OpenFGA (Testcontainers).
Validates the end-to-end wiring (Gateway -> RealOpenFga -> OpenFGA), not OpenFGA
in isolation. Skips where Docker/testcontainers is unavailable (CI stays green)."""

import time

import httpx
import pytest

pytest.importorskip("testcontainers.core.container")
from testcontainers.core.container import DockerContainer  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from scree.access.authority import Authority  # noqa: E402
from scree.access.openfga import RealOpenFga  # noqa: E402
from scree.access.ticket_authority import TicketAuthority  # noqa: E402
from scree.gateway.app import create_app  # noqa: E402
from scree.knowledge.store import DocStore  # noqa: E402
from scree.servicedesk.models import Ticket  # noqa: E402
from scree.servicedesk.store import TicketStore  # noqa: E402

pytestmark = pytest.mark.contract

MODEL = {
    "schema_version": "1.1",
    "type_definitions": [
        {"type": "user"},
        {
            "type": "ticket",
            "relations": {
                "requester": {"this": {}},
                "watcher": {"this": {}},
                "assignee": {"this": {}},
                "viewer": {
                    "union": {
                        "child": [
                            {"computedUserset": {"relation": "requester"}},
                            {"computedUserset": {"relation": "watcher"}},
                            {"computedUserset": {"relation": "assignee"}},
                        ]
                    }
                },
            },
            "metadata": {
                "relations": {
                    "requester": {"directly_related_user_types": [{"type": "user"}]},
                    "watcher": {"directly_related_user_types": [{"type": "user"}]},
                    "assignee": {"directly_related_user_types": [{"type": "user"}]},
                }
            },
        },
    ],
}

TUPLES = [
    {"user": "user:cust-okafor", "relation": "requester", "object": "ticket:ticket-1"},
    {"user": "user:cust-lind", "relation": "requester", "object": "ticket:ticket-2"},
    {"user": "user:cust-okafor", "relation": "watcher", "object": "ticket:ticket-2"},
    {"user": "user:cust-lind", "relation": "requester", "object": "ticket:ticket-3"},
]


@pytest.fixture(scope="module")
def fga():
    try:
        container = DockerContainer("openfga/openfga:latest").with_command("run").with_exposed_ports(8080)
        container.start()
    except Exception as exc:
        pytest.skip(f"Docker/OpenFGA unavailable: {exc}")
    try:
        base = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                if httpx.get(f"{base}/healthz", timeout=2).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            pytest.fail("OpenFGA did not become healthy")
        with httpx.Client(base_url=base, timeout=15) as cli:
            store_id = cli.post("/stores", json={"name": "scree-gw"}).json()["id"]
            model_id = cli.post(f"/stores/{store_id}/authorization-models", json=MODEL).json()["authorization_model_id"]
            cli.post(
                f"/stores/{store_id}/write",
                json={"authorization_model_id": model_id, "writes": {"tuple_keys": TUPLES}},
            ).raise_for_status()
        yield base, store_id, model_id
    finally:
        container.stop()


def _client(fga) -> TestClient:
    base, store_id, model_id = fga
    tickets = TicketStore(
        [Ticket(id="ticket-1", requester="cust-okafor"),
         Ticket(id="ticket-2", requester="cust-lind"),
         Ticket(id="ticket-3", requester="cust-lind")]
    )
    authority = TicketAuthority(RealOpenFga(base, store_id, model_id), agents={"agent:dani"})
    app = create_app(DocStore([]), Authority({}), ticket_store=tickets, ticket_authority=authority, allow_insecure_header_auth=True)
    return TestClient(app)


def test_customer_list_filtered_by_real_openfga(fga):
    client = _client(fga)
    resp = client.get("/tickets", headers={"X-Spike-User": "cust-okafor"})
    ids = {t["id"] for t in resp.json()}
    assert ids == {"ticket-1", "ticket-2"}  # via real OpenFGA ListObjects
    assert client.get("/tickets/ticket-3", headers={"X-Spike-User": "cust-okafor"}).status_code == 404


def test_agent_sees_all_via_union(fga):
    client = _client(fga)
    ids = {t["id"] for t in client.get("/tickets", headers={"X-Spike-User": "agent:dani"}).json()}
    assert ids == {"ticket-1", "ticket-2", "ticket-3"}
