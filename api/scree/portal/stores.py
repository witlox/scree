from dataclasses import dataclass, field


@dataclass
class PreferenceStore:
    """Per-principal self-service notification preferences (portal v1). Spike:
    in-memory."""

    _prefs: dict[str, str] = field(default_factory=dict)

    def set(self, principal: str, preference: str) -> None:
        self._prefs[principal] = preference

    def get(self, principal: str) -> str | None:
        return self._prefs.get(principal)


@dataclass(frozen=True)
class Attachment:
    ticket_id: str
    filename: str
    object_key: str  # location in object storage (NOT Git, DD: external attachments)


@dataclass
class AttachmentStore:
    """Service-desk attachments live in OBJECT STORAGE, not Git (architecture
    decision: external attachments → object storage). Spike: in-memory map keyed by
    an object key; a real impl is S3/MinIO. Bytes are not committed to any repo."""

    _by_ticket: dict[str, list[Attachment]] = field(default_factory=dict)
    _blobs: dict[str, bytes] = field(default_factory=dict)
    _seq: int = 0

    def put(self, ticket_id: str, filename: str, content: bytes) -> Attachment:
        self._seq += 1
        object_key = f"obj://attachments/{ticket_id}/{self._seq}-{filename}"
        self._blobs[object_key] = content
        att = Attachment(ticket_id=ticket_id, filename=filename, object_key=object_key)
        self._by_ticket.setdefault(ticket_id, []).append(att)
        return att

    def for_ticket(self, ticket_id: str) -> list[Attachment]:
        return list(self._by_ticket.get(ticket_id, []))
