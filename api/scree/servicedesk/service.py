import uuid
from dataclasses import replace

from scree.access.ticket_authority import TicketAuthority

from .lifecycle import transition
from .models import Origin, Ticket, TicketStatus
from .store import TicketStore


class TicketNotFound(LookupError):
    pass


class Forbidden(PermissionError):
    pass


class NotPromotable(ValueError):
    """community_visible may only be set on a resolved ticket (INV-LC-2)."""


class TicketService:
    """Ticket lifecycle (INV-LC-1/2): transitions, who may perform them, and
    community-visibility rules."""

    def __init__(self, store: TicketStore, authority: TicketAuthority) -> None:
        self._store = store
        self._authority = authority

    def create(self, origin: Origin, requester: str, space: str = "support/service-desk") -> Ticket:
        """Create a ticket from any origin, normalized to one record: opaque
        requester (INV-DP-1), status open. Tickets default requester-private even
        from public Slack threads (DD-013)."""
        # DD-013: tickets default requester-private regardless of origin (even a
        # public Slack thread); promotion to community-visible is explicit.
        ticket = Ticket(
            id=f"ticket-{uuid.uuid4().hex[:8]}",
            requester=requester,
            space=space,
            status="open",
            origin=origin,
            community_visible=False,
        )
        self._store.put(ticket)
        # I-01: grant the requester their viewer relation so they can read it.
        self._authority.grant(requester, "requester", ticket.id)
        return ticket

    def _load(self, ticket_id: str) -> Ticket:
        ticket = self._store.get(ticket_id)
        if ticket is None:
            raise TicketNotFound(ticket_id)
        return ticket

    def _may_work(self, principal: str, ticket: Ticket) -> bool:
        return self._authority.is_agent(principal) or principal == ticket.assignee

    def transition(self, ticket_id: str, target: TicketStatus, principal: str) -> Ticket:
        ticket = self._load(ticket_id)
        if not self._may_work(principal, ticket):
            raise Forbidden(principal)
        new_status = transition(ticket.status, target)
        # Reopening re-gates a community-visible ticket to private (INV-LC-2).
        community_visible = ticket.community_visible and new_status != "open"
        updated = replace(ticket, status=new_status, community_visible=community_visible)
        self._store.put(updated)
        return updated

    def promote_community_visible(self, ticket_id: str, principal: str) -> Ticket:
        ticket = self._load(ticket_id)
        if not self._authority.is_agent(principal):
            raise Forbidden(principal)
        if ticket.status != "resolved":
            raise NotPromotable(ticket_id)  # INV-LC-2: resolved-only
        updated = replace(ticket, community_visible=True)
        self._store.put(updated)
        return updated
