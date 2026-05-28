"""@api — the Gateway derives the principal from a VERIFIED OIDC bearer token
(I-03 / INV-ID-1), not a plaintext header. Missing/invalid tokens → 401."""

import datetime as dt

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.oidc import OidcAuthenticator
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore

ISSUER = "https://kc.example/realms/scree"
AUD = "scree-gateway"


@pytest.fixture(scope="module")
def keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return priv_pem, pub_pem


def _token(priv_pem, sub):
    now = dt.datetime.now(dt.timezone.utc)
    return jwt.encode(
        {"iss": ISSUER, "aud": AUD, "sub": sub, "preferred_username": "display-name",
         "iat": now, "exp": now + dt.timedelta(minutes=5)},
        priv_pem, algorithm="RS256",
    )


@pytest.fixture
def client(keypair):
    auth = OidcAuthenticator(issuer=ISSUER, audience=AUD, public_key=keypair[1])
    store = DocStore([Doc(id="doc-a", title="A", space="platform/handbook", body="b")])
    # G2-05: authority is keyed on the immutable `sub`.
    authority = Authority({"user-sub-1": {"platform/handbook"}})
    return TestClient(create_app(store, authority, authenticator=auth))


def test_valid_bearer_token_authenticates_and_authorizes(client, keypair):
    token = _token(keypair[0], "user-sub-1")
    resp = client.get("/docs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert {d["id"] for d in resp.json()} == {"doc-a"}


def test_missing_token_is_401(client):
    assert client.get("/docs").status_code == 401


def test_invalid_token_is_401(client):
    assert client.get("/docs", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_plaintext_header_is_ignored_when_authenticator_configured(client):
    # The old spike trust path must NOT work once real auth is on.
    assert client.get("/docs", headers={"X-Spike-User": "rivera"}).status_code == 401
