import hashlib
import json
from dataclasses import dataclass, field

GENESIS = "0" * 64


def _entry_hash(prev: str, principal: str | None, action: str, resource: str, result: int) -> str:
    """Hash an entry over the previous hash + its fields, forming a tamper-evident
    chain: changing, reordering, or dropping any entry breaks every hash after it."""
    payload = json.dumps([prev, principal, action, resource, result], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    principal: str | None
    action: str  # HTTP method
    resource: str  # request path
    result: int  # status code
    prev_hash: str = GENESIS
    entry_hash: str = ""


@dataclass
class AuditSink:
    """Append-only audit of Gateway actions (INV-ID-3). Entries are hash-chained so
    tampering is detectable (AR-10). Spike: in-memory; a real deployment writes the
    chain to WORM / append-only storage with retention — the integrity *mechanism*
    is here, the durable medium is a deploy concern."""

    _events: list[AuditEvent] = field(default_factory=list)

    def record(self, principal: str | None, action: str, resource: str, result: int) -> None:
        prev = self._events[-1].entry_hash if self._events else GENESIS
        self._events.append(
            AuditEvent(principal, action, resource, result, prev, _entry_hash(prev, principal, action, resource, result))
        )

    def events(self) -> list[AuditEvent]:
        return list(self._events)

    def verify(self) -> bool:
        """True iff the chain is intact (no entry altered, reordered, or removed)."""
        prev = GENESIS
        for e in self._events:
            if e.prev_hash != prev:
                return False
            if e.entry_hash != _entry_hash(prev, e.principal, e.action, e.resource, e.result):
                return False
            prev = e.entry_hash
        return True
