from .models import Ticket


class TicketStore:
    """In-memory ticket store for the spike, with threading indexes (G4-07):
    email Message-ID and [SCREE-NNN] token → ticket, for O(1) reply matching."""

    def __init__(self, tickets: list[Ticket] | None = None) -> None:
        self._tickets: dict[str, Ticket] = {}
        self._by_mid: dict[str, str] = {}
        self._by_token: dict[str, str] = {}
        for t in (tickets or []):
            self.put(t)

    def get(self, ticket_id: str) -> Ticket | None:
        return self._tickets.get(ticket_id)

    def all(self) -> list[Ticket]:
        return list(self._tickets.values())

    def put(self, ticket: Ticket) -> None:
        self._tickets[ticket.id] = ticket
        if ticket.email_message_id:
            self._by_mid[ticket.email_message_id] = ticket.id
        if ticket.email_token:
            self._by_token[ticket.email_token] = ticket.id

    def by_message_id(self, message_id: str) -> Ticket | None:
        tid = self._by_mid.get(message_id)
        return self._tickets.get(tid) if tid else None

    def by_token(self, token: str) -> Ticket | None:
        tid = self._by_token.get(token)
        return self._tickets.get(tid) if tid else None
