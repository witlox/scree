import json
import uuid
from pathlib import Path


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


class FileIdentityDirectory(IdentityDirectory):
    """Durable identity directory: the email↔opaque map persists to a JSON file so it
    survives restarts (in-memory would orphan every ticket's requester on restart).

    The file holds PII (emails), so it lives **outside Git** (INV-DP-1) — at a path on
    a private, ideally encrypted-at-rest volume, never in a repo. Erasure rewrites the
    file, dropping the mapping (the GDPR-erase contract, INV-DP-2)."""

    def __init__(self, path: Path | str) -> None:
        super().__init__()
        self._path = Path(path)
        if self._path.exists():
            data = json.loads(self._path.read_text() or "{}")
            self._by_email = dict(data.get("by_email", {}))
            self._by_id = dict(data.get("by_id", {}))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps({"by_email": self._by_email, "by_id": self._by_id}))
        tmp.replace(self._path)  # atomic swap so a crash mid-write can't corrupt the map

    def resolve(self, email: str) -> str:
        before = len(self._by_email)
        oid = super().resolve(email)
        if len(self._by_email) != before:  # a new mapping was minted → persist it
            self._save()
        return oid

    def erase(self, opaque_id: str) -> None:
        super().erase(opaque_id)
        self._save()
