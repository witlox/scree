from dataclasses import dataclass

from .models import Origin


@dataclass(frozen=True)
class TicketComment:
    """A message appended to a ticket thread (e.g. an inbound email reply)."""

    ticket_id: str
    author: str  # opaque requester id or agent
    body: str  # ciphertext when `encrypted` (stored at rest); plaintext otherwise
    source: Origin = "api"
    message_id: str | None = None  # source RFC Message-ID, when from email
    encrypted: bool = False  # body is per-requester ciphertext (ADR-0005)


class CommentStore:
    """In-memory ticket-thread store for the spike."""

    def __init__(self) -> None:
        self._by_ticket: dict[str, list[TicketComment]] = {}

    def add(self, comment: TicketComment) -> None:
        self._by_ticket.setdefault(comment.ticket_id, []).append(comment)

    def for_ticket(self, ticket_id: str) -> list[TicketComment]:
        return list(self._by_ticket.get(ticket_id, []))
