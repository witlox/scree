import base64
from typing import Protocol

import httpx
from cryptography.fernet import Fernet, InvalidToken


class DecryptionUnavailable(Exception):
    """The per-requester key is gone (crypto-shredded) or the ciphertext is invalid
    — the plaintext is unrecoverable (INV-DP-2 erasure / ADR-0006)."""


class TicketCrypto(Protocol):
    """Per-requester envelope crypto (ADR-0005/0008, Vault Transit in prod). Erasure
    destroys a requester's key, crypto-shredding everything encrypted under it."""

    def encrypt(self, requester: str, plaintext: str) -> str: ...

    def decrypt(self, requester: str, ciphertext: str) -> str: ...

    def destroy(self, requester: str) -> None: ...


class FernetCrypto:
    """In-memory per-requester Fernet keys for the @api tier (faithful stand-in for
    Vault Transit). `destroy` drops the key so prior ciphertext can't be decrypted."""

    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}

    def _key(self, requester: str) -> bytes:
        if requester not in self._keys:
            self._keys[requester] = Fernet.generate_key()
        return self._keys[requester]

    def encrypt(self, requester: str, plaintext: str) -> str:
        token = Fernet(self._key(requester)).encrypt(plaintext.encode())
        return token.decode()

    def decrypt(self, requester: str, ciphertext: str) -> str:
        key = self._keys.get(requester)
        if key is None:
            raise DecryptionUnavailable(requester)  # crypto-shredded
        try:
            return Fernet(key).decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise DecryptionUnavailable(requester) from exc

    def destroy(self, requester: str) -> None:
        self._keys.pop(requester, None)


class VaultTransitCrypto:
    """Vault Transit-backed per-requester crypto (ADR-0008). A named key per
    requester; encrypt/decrypt via Transit; `destroy` deletes the key (requires the
    key's deletion to be allowed) — the crypto-shred for erasure."""

    def __init__(self, base_url: str, token: str, client: httpx.Client | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=10)
        self._h = {"X-Vault-Token": token}

    def _key_name(self, requester: str) -> str:
        # Vault key names are restricted; encode the opaque requester id safely.
        return "scree-" + base64.urlsafe_b64encode(requester.encode()).decode().rstrip("=")

    def encrypt(self, requester: str, plaintext: str) -> str:
        name = self._key_name(requester)
        self._client.post(f"{self._base}/v1/transit/keys/{name}", headers=self._h)  # idempotent create
        b64 = base64.b64encode(plaintext.encode()).decode()
        resp = self._client.post(
            f"{self._base}/v1/transit/encrypt/{name}", headers=self._h, json={"plaintext": b64}
        )
        resp.raise_for_status()
        return resp.json()["data"]["ciphertext"]

    def decrypt(self, requester: str, ciphertext: str) -> str:
        name = self._key_name(requester)
        resp = self._client.post(
            f"{self._base}/v1/transit/decrypt/{name}", headers=self._h, json={"ciphertext": ciphertext}
        )
        # G8-02: 4xx = key missing (crypto-shredded) or bad ciphertext → permanently
        # unrecoverable. 5xx/transport = transient → let it propagate (retryable), so
        # an outage is never mis-reported as a permanent erasure.
        if 400 <= resp.status_code < 500:
            raise DecryptionUnavailable(requester)
        resp.raise_for_status()
        return base64.b64decode(resp.json()["data"]["plaintext"]).decode()

    def destroy(self, requester: str) -> None:
        name = self._key_name(requester)
        # Allow deletion, then delete the key — crypto-shred.
        self._client.post(
            f"{self._base}/v1/transit/keys/{name}/config",
            headers=self._h, json={"deletion_allowed": True},
        )
        self._client.delete(f"{self._base}/v1/transit/keys/{name}", headers=self._h)
