import re
from dataclasses import dataclass, field
from pathlib import Path


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


# A ticket id is opaque and slash-free (`ticket-...`); reject anything else so an
# attachment can never be written outside its ticket prefix (path-traversal guard).
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class FileAttachmentStore:
    """Durable object-storage-backed attachments. Bytes are written under a root
    directory that stands for the object store (a mounted bucket / MinIO / S3-fuse);
    they are **not** committed to any Git repo (external-attachment decision). A
    drop-in S3/MinIO client can replace the filesystem backend without changing the
    `put`/`for_ticket` interface."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    def _ticket_dir(self, ticket_id: str) -> Path:
        if not _SAFE_ID.match(ticket_id):
            raise ValueError(f"unsafe ticket id: {ticket_id!r}")
        return self._root / ticket_id

    def put(self, ticket_id: str, filename: str, content: bytes) -> Attachment:
        d = self._ticket_dir(ticket_id)
        d.mkdir(parents=True, exist_ok=True)
        seq = len(list(d.glob("*"))) + 1
        safe_name = Path(filename).name  # strip any path components from the upload
        object_key = f"{ticket_id}/{seq:04d}-{safe_name}"
        (self._root / object_key).write_bytes(content)
        return Attachment(ticket_id=ticket_id, filename=safe_name, object_key=object_key)

    def for_ticket(self, ticket_id: str) -> list[Attachment]:
        d = self._ticket_dir(ticket_id)
        if not d.is_dir():
            return []
        out = []
        for f in sorted(d.glob("*")):
            # name is "NNNN-<filename>"; recover the original filename.
            filename = f.name.split("-", 1)[1] if "-" in f.name else f.name
            out.append(Attachment(ticket_id=ticket_id, filename=filename, object_key=f"{ticket_id}/{f.name}"))
        return out
