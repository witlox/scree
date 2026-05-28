"""@contract — OidcAuthenticator against a REAL Keycloak (Testcontainers).

Validates I-03 end-to-end (INV-ID-1): a token minted by a real Keycloak realm is
verified by the Gateway via the live JWKS (signature + iss + aud + exp), the
principal is extracted, and the plaintext X-Spike-User header is ignored once an
authenticator is configured. Skips where Docker/testcontainers is unavailable so
CI stays green."""

import time

import httpx
import jwt
import pytest

pytest.importorskip("testcontainers.core.container")
from testcontainers.core.container import DockerContainer  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from scree.access.authority import Authority  # noqa: E402
from scree.access.oidc import AuthError, OidcAuthenticator  # noqa: E402
from scree.gateway.app import create_app  # noqa: E402
from scree.knowledge.models import Doc  # noqa: E402
from scree.knowledge.store import DocStore  # noqa: E402

pytestmark = pytest.mark.contract

REALM = "scree"
CLIENT_ID = "scree-gateway"
USERNAME = "rivera"
PASSWORD = "pw-rivera"


def _admin_token(base: str) -> str:
    r = httpx.post(
        f"{base}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": "admin", "password": "admin"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _ok(r: httpx.Response) -> httpx.Response:
    if r.status_code >= 400:
        raise AssertionError(f"{r.request.method} {r.request.url} -> {r.status_code}: {r.text}")
    return r


def _provision(base: str) -> None:
    """Create the scree realm, a public direct-grant client, and a user. The
    password is reset with temporary=False so the direct grant isn't blocked by
    an UPDATE_PASSWORD required action."""
    h = {"Authorization": f"Bearer {_admin_token(base)}"}
    with httpx.Client(base_url=base, headers=h, timeout=15) as c:
        _ok(c.post("/admin/realms", json={"realm": REALM, "enabled": True}))
        _ok(c.post(
            f"/admin/realms/{REALM}/clients",
            json={"clientId": CLIENT_ID, "enabled": True, "publicClient": True,
                  "directAccessGrantsEnabled": True, "protocol": "openid-connect",
                  "standardFlowEnabled": False},
        ))
        _ok(c.post(f"/admin/realms/{REALM}/users", json={"username": USERNAME, "enabled": True}))
        uid = _ok(c.get(f"/admin/realms/{REALM}/users", params={"username": USERNAME})).json()[0]["id"]
        # A complete profile + no required actions, else KC's VERIFY_PROFILE action
        # makes the direct grant fail with "Account is not fully set up".
        _ok(c.put(
            f"/admin/realms/{REALM}/users/{uid}",
            json={"enabled": True, "emailVerified": True, "requiredActions": [],
                  "email": f"{USERNAME}@example.com", "firstName": "Rivera", "lastName": "User"},
        ))
        _ok(c.put(
            f"/admin/realms/{REALM}/users/{uid}/reset-password",
            json={"type": "password", "value": PASSWORD, "temporary": False},
        ))


def _id_token(base: str) -> str:
    """A real OIDC id_token for the user (aud=client_id, iss=realm)."""
    r = httpx.post(
        f"{base}/realms/{REALM}/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": CLIENT_ID, "scope": "openid",
              "username": USERNAME, "password": PASSWORD},
        timeout=15,
    )
    return _ok(r).json()["id_token"]


@pytest.fixture(scope="module")
def keycloak():
    try:
        container = (
            DockerContainer("quay.io/keycloak/keycloak:latest")
            .with_command("start-dev")
            .with_env("KEYCLOAK_ADMIN", "admin")
            .with_env("KEYCLOAK_ADMIN_PASSWORD", "admin")
            .with_env("KC_BOOTSTRAP_ADMIN_USERNAME", "admin")
            .with_env("KC_BOOTSTRAP_ADMIN_PASSWORD", "admin")
            .with_exposed_ports(8080)
        )
        container.start()
    except Exception as exc:
        pytest.skip(f"Docker/Keycloak unavailable: {exc}")
    try:
        base = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"
        deadline = time.time() + 180  # Keycloak is slow to boot
        well_known = f"{base}/realms/master/.well-known/openid-configuration"
        while time.time() < deadline:
            try:
                if httpx.get(well_known, timeout=3).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            pytest.fail("Keycloak did not become ready")
        _provision(base)
        yield base
    finally:
        container.stop()


@pytest.fixture(scope="module")
def authenticator(keycloak):
    return OidcAuthenticator(
        issuer=f"{keycloak}/realms/{REALM}",
        audience=CLIENT_ID,
        jwks_url=f"{keycloak}/realms/{REALM}/protocol/openid-connect/certs",
    )


def _sub(token: str) -> str:
    return jwt.decode(token, options={"verify_signature": False})["sub"]


def test_real_token_yields_principal(keycloak, authenticator):
    # G2-05: principal is the immutable `sub`, not preferred_username.
    token = _id_token(keycloak)
    assert authenticator.principal(token) == _sub(token)


def test_garbage_token_rejected(authenticator):
    with pytest.raises(AuthError):
        authenticator.principal("not.a.jwt")


def test_wrong_audience_rejected(keycloak):
    bad = OidcAuthenticator(
        issuer=f"{keycloak}/realms/{REALM}",
        audience="some-other-client",  # token aud=scree-gateway -> mismatch
        jwks_url=f"{keycloak}/realms/{REALM}/protocol/openid-connect/certs",
    )
    with pytest.raises(AuthError):
        bad.principal(_id_token(keycloak))


def test_gateway_accepts_bearer_and_ignores_spike_header(keycloak, authenticator):
    token = _id_token(keycloak)
    store = DocStore([Doc(id="doc-a", title="A", space="platform/handbook", body="b")])
    # G2-05: authority is keyed on the token's immutable `sub`.
    authority = Authority({_sub(token): {"platform/handbook"}})
    client = TestClient(create_app(store, authority, authenticator=authenticator))

    # Real bearer -> 200 and the doc is visible to the subject.
    ok = client.get(
        "/docs",
        headers={"Authorization": f"Bearer {token}", "X-Spike-User": "intruder"},
    )
    assert ok.status_code == 200
    assert [d["id"] for d in ok.json()] == ["doc-a"]

    # No bearer -> 401 even with a forged X-Spike-User (header ignored, INV-ID-1).
    assert client.get("/docs", headers={"X-Spike-User": USERNAME}).status_code == 401
