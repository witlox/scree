from .models import Ticket


class TicketStore:
    """In-memory ticket store for the spike."""

    def __init__(self, tickets: list[Ticket] | None = None) -> None:
        self._tickets: dict[str, Ticket] = {t.id: t for t in (tickets or [])}

    def get(self, ticket_id: str) -> Ticket | None:
        return self._tickets.get(ticket_id)

    def all(self) -> list[Ticket]:
        return list(self._tickets.values())

    def put(self, ticket: Ticket) -> None:
        self._tickets[ticket.id] = ticket
