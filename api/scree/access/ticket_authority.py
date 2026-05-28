from .openfga import TicketRelations


class TicketAuthority:
    """Composes ticket authority per INV-ACC-2 / AR-04: OpenFGA `viewer`
    relations ∪ GitLab desk-repo membership (agents see all desk tickets)."""

    def __init__(self, relations: TicketRelations, agents: set[str]) -> None:
        self._relations = relations
        self._agents = agents

    def readable_tickets(self, principal: str, all_ticket_ids: set[str]) -> set[str]:
        # AR-04 / INV-ACC-2: OpenFGA relations ∪ GitLab desk membership.
        if principal in self._agents:
            return set(all_ticket_ids)
        return self._relations.list_readable(principal)

    def can_read(self, principal: str, ticket_id: str) -> bool:
        return principal in self._agents or self._relations.can_read(principal, ticket_id)

    def is_agent(self, principal: str) -> bool:
        return principal in self._agents
