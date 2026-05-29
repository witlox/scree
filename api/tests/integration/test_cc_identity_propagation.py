"""@api cross-context (INTEGRATOR) — identity continuity end-to-end. A human's OIDC
bearer is verified at the Gateway, exchanged (RFC 8693) for a downstream GitLab-scoped
token, and it is the EXCHANGED human token — never the raw bearer, never a Gateway
credential — that resolves authority against GitLab; the audit sink records the human
(sub). This is the seam INV-ID-1 depends on (GitLab audit shows the real actor).

Invariants: INV-ID-1, INV-ID-3. Seam: surface → Gateway(oidc) → token_exchange →
gitlab authority → audit."""

import datetime as dt

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from scree.access.audit import AuditSink
from scree.access.authority import Authority
from scree.access.oidc import OidcAuthenticator
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore

ISSUER = "https://kc.example/realms/scree"
AUD = "scree-gateway"
SPACE = "platform/handbook"
HUMAN_SUB = "uuid-human"


@pytest.fixture(scope="module")
def keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption()),
        priv.public_key().public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo),
    )


def _bearer(priv_pem: bytes) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    return jwt.encode(
        {"iss": ISSUER, "aud": AUD, "sub": HUMAN_SUB, "preferred_username": "rivera",
         "iat": now, "exp": now + dt.timedelta(minutes=5)},
        priv_pem, algorithm="RS256",
    )


class _RecordingExchanger:
    def __init__(self) -> None:
        self.seen: list[tuple[str, str]] = []

    def exchange(self, subject_token: str, audience: str) -> str:
        self.seen.append((subject_token, audience))
        return f"gitlab-token-for:{audience}"


class _RecordingGitLab:
    def __init__(self, grants: dict[str, set[str]]) -> None:
        self._grants = grants
        self.tokens: list[str] = []

    def readable_spaces(self, token: str) -> set[str]:
        self.tokens.append(token)
        return set(self._grants.get(token, set()))

    def readable_groups(self, token: str) -> set[str]:
        self.tokens.append(token)
        return set()


def test_human_identity_propagates_through_exchange_to_gitlab_and_audit(keypair):
    priv, pub = keypair
    bearer = _bearer(priv)
    exchanger = _RecordingExchanger()
    downstream = "gitlab-token-for:gitlab"
    gitlab = _RecordingGitLab({downstream: {SPACE}})
    audit = AuditSink()

    client = TestClient(create_app(
        DocStore([Doc(id="doc-a", title="A", space=SPACE, body="b")]),
        Authority({}),
        authenticator=OidcAuthenticator(issuer=ISSUER, audience=AUD, public_key=pub),
        token_exchanger=exchanger, gitlab_authority=gitlab, audit=audit,
    ))

    resp = client.get("/docs", headers={"Authorization": f"Bearer {bearer}"})
    assert resp.status_code == 200
    assert [d["id"] for d in resp.json()] == ["doc-a"]  # authorized as the human

    # The exchanger received the HUMAN's bearer as subject_token, for the GitLab audience.
    assert exchanger.seen == [(bearer, "gitlab")]
    # GitLab authority was queried ONLY with the exchanged downstream token —
    # never the raw bearer, never a Gateway identity.
    assert gitlab.tokens and all(t == downstream for t in gitlab.tokens)
    assert bearer not in gitlab.tokens
    # The audit sink records the HUMAN principal (sub), not the Gateway (INV-ID-3).
    docs_events = [e for e in audit.events() if e.resource == "/docs"]
    assert docs_events and all(e.principal == HUMAN_SUB for e in docs_events)


def test_no_bearer_is_refused_and_does_not_query_gitlab(keypair):
    _, pub = keypair
    exchanger = _RecordingExchanger()
    gitlab = _RecordingGitLab({})
    client = TestClient(create_app(
        DocStore([]), Authority({}),
        authenticator=OidcAuthenticator(issuer=ISSUER, audience=AUD, public_key=pub),
        token_exchanger=exchanger, gitlab_authority=gitlab,
    ))
    assert client.get("/docs").status_code == 401
    assert exchanger.seen == [] and gitlab.tokens == []  # no identity → no downstream calls
