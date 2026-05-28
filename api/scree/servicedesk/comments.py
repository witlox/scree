from dataclasses import dataclass

from .models import Origin


@dataclass(frozen=True)
class TicketComment:
    """A message appended to a ticket thread (e.g. an inbound email reply)."""

    ticket_id: str
    author: str  # opaque requester id or agent
    body: str
    source: Origin = "api"
    message_id: str | None = None  # source RFC Message-ID, when from email


class CommentStore:
    """In-memory ticket-thread store for the spike."""

    def __init__(self) -> None:
        self._by_ticket: dict[str, list[TicketComment]] = {}

    def add(self, comment: TicketComment) -> None:
        self._by_ticket.setdefault(comment.ticket_id, []).append(comment)

    def for_ticket(self, ticket_id: str) -> list[TicketComment]:
        return list(self._by_ticket.get(ticket_id, []))
