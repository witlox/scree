from typing import Protocol


class TicketRelations(Protocol):
    """Read side of ticket ReBAC (OpenFGA in prod, ADR-0007). Models the
    `viewer` relation = requester ∪ watcher ∪ assignee."""

    def list_readable(self, user: str) -> set[str]: ...

    def can_read(self, user: str, ticket_id: str) -> bool: ...


class FakeOpenFga:
    """Faithful in-memory stand-in for OpenFGA's `viewer` relation, used by the
    @api tier. The @contract tier validates the real engine matches this
    contract (assumption A-5)."""

    VIEWER_RELATIONS = frozenset({"requester", "watcher", "assignee"})

    def __init__(self) -> None:
        self._tuples: set[tuple[str, str, str]] = set()

    def write(self, user: str, relation: str, ticket_id: str) -> None:
        self._tuples.add((user, relation, ticket_id))

    def list_readable(self, user: str) -> set[str]:
        return {
            t for (u, r, t) in self._tuples
            if u == user and r in self.VIEWER_RELATIONS
        }

    def can_read(self, user: str, ticket_id: str) -> bool:
        return any(
            u == user and r in self.VIEWER_RELATIONS and t == ticket_id
            for (u, r, t) in self._tuples
        )
