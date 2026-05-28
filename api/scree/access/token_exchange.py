from typing import Protocol

import httpx

from scree.access.oidc import AuthError

TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange"


class TokenExchanger(Protocol):
    """RFC 8693 token exchange: trade the inbound OIDC subject token for a
    downstream token scoped to another audience (e.g. GitLab), so the Gateway
    acts as the user against GitLab without holding the user's GitLab credential
    (I-03 follow-up; permission-enforcement-map)."""

    def exchange(self, subject_token: str, audience: str) -> str: ...


class StaticTokenExchanger:
    """Dev/@api stand-in: maps an inbound (subject_token, audience) to a downstream
    token deterministically, or via an explicit table. Faithful enough to wire and
    test the exchange flow without a real IdP."""

    def __init__(self, table: dict[tuple[str, str], str] | None = None) -> None:
        self._table = table or {}

    def exchange(self, subject_token: str, audience: str) -> str:
        key = (subject_token, audience)
        if key in self._table:
            return self._table[key]
        return f"downstream:{audience}:{subject_token}"


class KeycloakTokenExchanger:
    """Exchanges via Keycloak's token endpoint (RFC 8693). The Gateway's own client
    authenticates; the inbound user token is the subject_token; `audience` requests
    a token for the target client (e.g. the GitLab client)."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = client or httpx.Client(timeout=10)

    def exchange(self, subject_token: str, audience: str) -> str:
        resp = self._client.post(
            self._token_url,
            data={
                "grant_type": TOKEN_EXCHANGE_GRANT,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "subject_token": subject_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "audience": audience,
            },
        )
        if resp.status_code != 200:
            raise AuthError(f"token exchange failed: {resp.status_code} {resp.text}")
        token = resp.json().get("access_token")
        if not token:
            raise AuthError("token exchange returned no access_token")
        return token
