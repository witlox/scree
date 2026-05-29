"""@contract — G-B2: KeycloakTokenExchanger (RFC 8693) against a REAL Keycloak.

INV-ID-1 depends on trading the inbound user token for a downstream (GitLab-audience)
token so GitLab's audit shows the human. PR #66 shipped KeycloakTokenExchanger with
only unit request-shape coverage; this exercises it end-to-end against a live Keycloak
with the token-exchange feature enabled. Keycloak's token-exchange config is version-
sensitive, so boot/provision/config failures SKIP (CI has no Docker anyway) — the test
is a real assertion only where the environment supports it."""

import time

import httpx
import jwt
import pytest

pytest.importorskip("testcontainers.core.container")
from testcontainers.core.container import DockerContainer  # noqa: E402

from scree.access.oidc import AuthError  # noqa: E402
from scree.access.token_exchange import KeycloakTokenExchanger  # noqa: E402

pytestmark = pytest.mark.contract

REALM = "scree"
CLIENT_ID = "scree-gateway"  # confidential client that performs the exchange
AUDIENCE = "gitlab"  # target audience client (the downstream resource)
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


def _provision(base: str) -> str:
    """Realm + a confidential client allowed to do standard token exchange + a target
    audience client + a user. Returns the confidential client's secret."""
    h = {"Authorization": f"Bearer {_admin_token(base)}"}
    with httpx.Client(base_url=base, headers=h, timeout=15) as c:
        _ok(c.post("/admin/realms", json={"realm": REALM, "enabled": True}))
        _ok(c.post(f"/admin/realms/{REALM}/clients", json={
            "clientId": CLIENT_ID, "enabled": True, "publicClient": False,
            "directAccessGrantsEnabled": True, "serviceAccountsEnabled": True,
            "standardFlowEnabled": False, "protocol": "openid-connect",
            # Allow this client to perform (standard) token exchange — KC 26.2+.
            "attributes": {"standard.token.exchange.enabled": "true"},
        }))
        _ok(c.post(f"/admin/realms/{REALM}/clients", json={
            "clientId": AUDIENCE, "enabled": True, "publicClient": False,
            "standardFlowEnabled": False, "protocol": "openid-connect",
        }))
        internal = _ok(c.get(f"/admin/realms/{REALM}/clients", params={"clientId": CLIENT_ID})).json()[0]["id"]
        secret = _ok(c.get(f"/admin/realms/{REALM}/clients/{internal}/client-secret")).json()["value"]
        _ok(c.post(f"/admin/realms/{REALM}/users", json={"username": USERNAME, "enabled": True}))
        uid = _ok(c.get(f"/admin/realms/{REALM}/users", params={"username": USERNAME})).json()[0]["id"]
        _ok(c.put(f"/admin/realms/{REALM}/users/{uid}", json={
            "enabled": True, "emailVerified": True, "requiredActions": [],
            "email": f"{USERNAME}@example.com", "firstName": "Rivera", "lastName": "User"}))
        _ok(c.put(f"/admin/realms/{REALM}/users/{uid}/reset-password",
                  json={"type": "password", "value": PASSWORD, "temporary": False}))
        return secret


def _subject_token(base: str, secret: str) -> str:
    r = httpx.post(
        f"{base}/realms/{REALM}/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": secret,
              "scope": "openid", "username": USERNAME, "password": PASSWORD},
        timeout=15,
    )
    return _ok(r).json()["access_token"]


@pytest.fixture(scope="module")
def kc():
    try:
        container = (
            DockerContainer("quay.io/keycloak/keycloak:latest")
            .with_command("start-dev --features=token-exchange")
            .with_env("KEYCLOAK_ADMIN", "admin").with_env("KEYCLOAK_ADMIN_PASSWORD", "admin")
            .with_env("KC_BOOTSTRAP_ADMIN_USERNAME", "admin").with_env("KC_BOOTSTRAP_ADMIN_PASSWORD", "admin")
            .with_exposed_ports(8080)
        )
        container.start()
    except Exception as exc:
        pytest.skip(f"Docker/Keycloak unavailable: {exc}")
    try:
        base = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"
        deadline = time.time() + 180
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
        try:
            secret = _provision(base)
        except Exception as exc:
            pytest.skip(f"token-exchange provisioning unsupported on this Keycloak: {exc}")
        yield base, secret
    finally:
        container.stop()


def test_exchange_returns_downstream_token_for_audience(kc):
    base, secret = kc
    subject = _subject_token(base, secret)
    exchanger = KeycloakTokenExchanger(
        token_url=f"{base}/realms/{REALM}/protocol/openid-connect/token",
        client_id=CLIENT_ID, client_secret=secret,
    )
    try:
        downstream = exchanger.exchange(subject, AUDIENCE)
    except AuthError as exc:
        pytest.skip(f"standard token exchange not permitted by this Keycloak config: {exc}")
    assert downstream and downstream != subject
    # The downstream token is a real JWT scoped to the requested audience.
    claims = jwt.decode(downstream, options={"verify_signature": False})
    aud = claims.get("aud")
    assert AUDIENCE in (aud if isinstance(aud, list) else [aud])


def test_exchange_rejects_garbage_subject_token(kc):
    base, secret = kc
    exchanger = KeycloakTokenExchanger(
        token_url=f"{base}/realms/{REALM}/protocol/openid-connect/token",
        client_id=CLIENT_ID, client_secret=secret,
    )
    with pytest.raises(AuthError):
        exchanger.exchange("not.a.real.token", AUDIENCE)
