from typing import Any

import jwt


class AuthError(Exception):
    """Authentication failed (missing/invalid/expired token)."""


class OidcAuthenticator:
    """Verifies an OIDC bearer JWT (signature, exp, issuer, audience) and extracts
    the principal — the gateway's single authentication point (ADR-0018, INV-ID-1).
    `public_key` is for tests; production passes `jwks_url` (Keycloak)."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str | None = None,
        public_key: Any | None = None,
        algorithms: tuple[str, ...] = ("RS256",),
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._algorithms = list(algorithms)
        self._public_key = public_key
        self._jwks = jwt.PyJWKClient(jwks_url) if jwks_url else None

    def _key(self, token: str) -> Any:
        if self._public_key is not None:
            return self._public_key
        if self._jwks is None:
            raise AuthError("no key source configured")
        return self._jwks.get_signing_key_from_jwt(token).key

    def principal(self, token: str) -> str:
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                self._key(token),
                algorithms=self._algorithms,
                audience=self._audience,
                issuer=self._issuer,
            )
        except Exception as exc:
            raise AuthError(str(exc)) from exc
        principal = claims.get("preferred_username") or claims.get("sub")
        if not principal:
            raise AuthError("no principal claim")
        return str(principal)
