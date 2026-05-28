from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuarantinedEmail:
    """An inbound email held for agent review (INV-EMAIL-1) — never attributed
    or threaded. Stores the claimed (untrusted) sender for triage; no opaque id
    is minted for an unverified/mismatched sender."""

    claimed_from: str
    subject: str
    body: str
    reason: str
    candidate_ticket: str | None = None


@dataclass
class QuarantineStore:
    """Append-only quarantine queue for agent review. Spike: in-memory."""

    _items: list[QuarantinedEmail] = field(default_factory=list)

    def add(self, item: QuarantinedEmail) -> None:
        self._items.append(item)

    def all(self) -> list[QuarantinedEmail]:
        return list(self._items)
