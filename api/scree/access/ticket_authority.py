from typing import Protocol

from .openfga import TicketRelations


class _TicketLike(Protocol):
    # Structural type (avoids an access->servicedesk import cycle).
    id: str
    requester: str
    community_visible: bool


class TicketAuthority:
    """Composes ticket authority: OpenFGA `viewer` relations ∪ GitLab desk-repo
    membership (agents) ∪ community_visible (INV-ACC-2/3, AR-04)."""

    def __init__(self, relations: TicketRelations, agents: set[str]) -> None:
        self._relations = relations
        self._agents = agents

    def readable_tickets(self, principal: str, tickets: list[_TicketLike]) -> set[str]:
        if principal in self._agents:
            return {t.id for t in tickets}
        by_relation = self._relations.list_readable(principal)
        # INV-ACC-3: a community_visible ticket is readable by any authenticated principal.
        return {t.id for t in tickets if t.id in by_relation or t.community_visible}

    def can_read(self, principal: str, ticket: _TicketLike) -> bool:
        return (
            principal in self._agents
            or ticket.community_visible
            or self._relations.can_read(principal, ticket.id)
        )

    def is_agent(self, principal: str) -> bool:
        return principal in self._agents

    def can_see_identity(self, principal: str, ticket: _TicketLike) -> bool:
        """Who may see the requester id: agents, the requester themself, or a
        directly related party (requester/watcher/assignee) — NOT a viewer who
        only sees the ticket because it is community_visible (G2-06)."""
        return (
            principal in self._agents
            or principal == ticket.requester
            or self._relations.can_read(principal, ticket.id)
        )

    def grant(self, user: str, relation: str, ticket_id: str) -> None:
        # I-01: on ticket create, grant the requester their viewer relation.
        self._relations.write(user, relation, ticket_id)

    def purge_relations(self, user: str) -> int:
        # GDPR erasure (AR-05): drop all of the subject's relation tuples.
        return self._relations.purge_user(user)
