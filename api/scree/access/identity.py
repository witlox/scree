import uuid


class IdentityDirectory:
    """External-customer identity directory (module-graph `access/`): maps an
    email to a stable, OPAQUE requester id. The email (PII) lives here, out of
    Git — only the opaque id is stored on tickets / OpenFGA (INV-DP-1). Erasure
    drops the mapping (the crypto-shred analog of ADR-0006). Spike: in-memory."""

    def __init__(self) -> None:
        self._by_email: dict[str, str] = {}
        self._by_id: dict[str, str] = {}

    def resolve(self, email: str) -> str:
        """Return the stable opaque id for an email, minting one on first sight."""
        key = email.strip().lower()
        oid = self._by_email.get(key)
        if oid is None:
            oid = f"ext-{uuid.uuid4().hex[:12]}"
            self._by_email[key] = oid
            self._by_id[oid] = key
        return oid

    def email_for(self, opaque_id: str) -> str | None:
        """The email behind an opaque id — for agent display only, never Git."""
        return self._by_id.get(opaque_id)

    def erase(self, opaque_id: str) -> None:
        """GDPR erasure: forget the email↔id mapping (INV-DP-2)."""
        email = self._by_id.pop(opaque_id, None)
        if email is not None:
            self._by_email.pop(email, None)
