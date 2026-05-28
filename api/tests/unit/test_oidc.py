"""TDD — OIDC token verification (INV-ID-1): a forged/tampered/expired/wrong-aud/
wrong-iss token is rejected; a valid one yields the principal."""

import datetime as dt

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from scree.access.oidc import AuthError, OidcAuthenticator

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


def _token(priv_pem, **overrides) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    claims = {
        "iss": ISSUER, "aud": AUD, "sub": "uuid-1", "preferred_username": "cust-okafor",
        "iat": now, "exp": now + dt.timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(claims, priv_pem, algorithm="RS256")


@pytest.fixture
def auth(keypair):
    return OidcAuthenticator(issuer=ISSUER, audience=AUD, public_key=keypair[1])


def test_valid_token_yields_principal(keypair, auth):
    assert auth.principal(_token(keypair[0])) == "cust-okafor"


def test_tampered_token_rejected(keypair, auth):
    with pytest.raises(AuthError):
        auth.principal(_token(keypair[0]) + "tamper")


def test_token_signed_by_wrong_key_rejected(auth):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    with pytest.raises(AuthError):
        auth.principal(_token(other_pem))


def test_expired_token_rejected(keypair, auth):
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
    with pytest.raises(AuthError):
        auth.principal(_token(keypair[0], exp=past))


def test_wrong_audience_rejected(keypair, auth):
    with pytest.raises(AuthError):
        auth.principal(_token(keypair[0], aud="someone-else"))


def test_wrong_issuer_rejected(keypair, auth):
    with pytest.raises(AuthError):
        auth.principal(_token(keypair[0], iss="https://evil/realms/x"))
