"""@contract — validates assumption A-5 against a REAL OpenFGA (Testcontainers):
the `viewer` = requester ∪ watcher ∪ assignee model, and that ListObjects/Check
enforce ticket visibility. Skips where testcontainers/Docker is unavailable
(e.g. CI without Docker), so the default suite stays green."""

import time

import httpx
import pytest

pytest.importorskip("testcontainers.core.container")
from testcontainers.core.container import DockerContainer  # noqa: E402

from scree.access.openfga import RealOpenFga  # noqa: E402

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


@pytest.fixture(scope="module")
def openfga_url():
    try:
        container = DockerContainer("openfga/openfga:latest").with_command("run").with_exposed_ports(8080)
        container.start()
    except Exception as exc:  # Docker not available
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
            pytest.fail("OpenFGA did not become healthy in time")
        yield base
    finally:
        container.stop()


def test_listobjects_and_check_enforce_ticket_viewer(openfga_url):
    with httpx.Client(base_url=openfga_url, timeout=15) as cli:
        store_id = cli.post("/stores", json={"name": "scree-contract"}).json()["id"]
        model_id = cli.post(
            f"/stores/{store_id}/authorization-models", json=MODEL
        ).json()["authorization_model_id"]

        tuples = [
            {"user": "user:okafor", "relation": "requester", "object": "ticket:1"},
            {"user": "user:lind", "relation": "requester", "object": "ticket:2"},
            {"user": "user:okafor", "relation": "watcher", "object": "ticket:2"},
            {"user": "user:lind", "relation": "requester", "object": "ticket:3"},
        ]
        cli.post(
            f"/stores/{store_id}/write",
            json={"authorization_model_id": model_id, "writes": {"tuple_keys": tuples}},
        ).raise_for_status()

        # A-5: ListObjects returns exactly the viewer set for the union model.
        objs = cli.post(
            f"/stores/{store_id}/list-objects",
            json={
                "authorization_model_id": model_id,
                "type": "ticket",
                "relation": "viewer",
                "user": "user:okafor",
            },
        ).json()["objects"]
        assert set(objs) == {"ticket:1", "ticket:2"}

        # Check enforces per-ticket (existence-leak-safe denial upstream).
        def allowed(obj: str) -> bool:
            return cli.post(
                f"/stores/{store_id}/check",
                json={
                    "authorization_model_id": model_id,
                    "tuple_key": {"user": "user:okafor", "relation": "viewer", "object": obj},
                },
            ).json()["allowed"]

        assert allowed("ticket:1") is True
        assert allowed("ticket:3") is False


def test_real_purge_user_erases_subject_tuples(openfga_url):
    # AR-05 on the REAL engine: RealOpenFga.purge_user removes the subject's
    # tuples (read+delete), leaving other users untouched.
    with httpx.Client(base_url=openfga_url, timeout=15) as cli:
        store_id = cli.post("/stores", json={"name": "scree-purge"}).json()["id"]
        model_id = cli.post(
            f"/stores/{store_id}/authorization-models", json=MODEL
        ).json()["authorization_model_id"]
        cli.post(
            f"/stores/{store_id}/write",
            json={"authorization_model_id": model_id, "writes": {"tuple_keys": [
                {"user": "user:okafor", "relation": "requester", "object": "ticket:1"},
                {"user": "user:okafor", "relation": "watcher", "object": "ticket:2"},
                {"user": "user:lind", "relation": "requester", "object": "ticket:3"},
            ]}},
        ).raise_for_status()

    fga = RealOpenFga(openfga_url, store_id, model_id)
    assert fga.list_readable("okafor") == {"1", "2"}  # strip_type("ticket:1") -> "1"

    assert fga.purge_user("okafor") == 2
    assert fga.list_readable("okafor") == set()
    assert fga.list_readable("lind") == {"3"}  # other subjects untouched


def test_real_purge_user_paginates_and_batches(openfga_url):
    # G5-01 on the REAL engine: a subject with more tuples than one Read page /
    # one delete batch is fully purged (pagination + batching), not partially.
    n = 120
    with httpx.Client(base_url=openfga_url, timeout=30) as cli:
        store_id = cli.post("/stores", json={"name": "scree-pages"}).json()["id"]
        model_id = cli.post(
            f"/stores/{store_id}/authorization-models", json=MODEL
        ).json()["authorization_model_id"]
        rows = [{"user": "user:heavy", "relation": "requester", "object": f"ticket:{i}"} for i in range(n)]
        for start in range(0, n, 100):  # OpenFGA write cap is 100/call
            cli.post(
                f"/stores/{store_id}/write",
                json={"authorization_model_id": model_id, "writes": {"tuple_keys": rows[start:start + 100]}},
            ).raise_for_status()

    fga = RealOpenFga(openfga_url, store_id, model_id)
    assert len(fga.list_readable("heavy")) == n
    assert fga.purge_user("heavy") == n  # follows pagination + batches the deletes
    assert fga.list_readable("heavy") == set()
