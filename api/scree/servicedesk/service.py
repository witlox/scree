import uuid
from dataclasses import replace

from scree.access.ticket_authority import TicketAuthority
from scree.integration.o365.inbound import InboundEmail

from .comments import CommentStore, TicketComment
from .email_routing import requester_of, route_inbound
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

    def __init__(
        self,
        store: TicketStore,
        authority: TicketAuthority,
        comment_store: CommentStore | None = None,
    ) -> None:
        self._store = store
        self._authority = authority
        self._comments = comment_store

    def create(
        self,
        origin: Origin,
        requester: str,
        space: str = "support/service-desk",
        *,
        email_message_id: str | None = None,
    ) -> Ticket:
        """Create a ticket from any origin, normalized to one record: opaque
        requester (INV-DP-1), status open. Tickets default requester-private even
        from public Slack threads (DD-013)."""
        # DD-013: tickets default requester-private regardless of origin (even a
        # public Slack thread); promotion to community-visible is explicit.
        tid = f"ticket-{uuid.uuid4().hex[:8]}"
        ticket = Ticket(
            id=tid,
            requester=requester,
            space=space,
            status="open",
            origin=origin,
            community_visible=False,
            # email_token lets later replies thread when headers are stripped.
            email_token=f"SCREE-{tid.split('-')[1]}" if origin == "email" else None,
            email_message_id=email_message_id,
        )
        self._store.put(ticket)
        # I-01: grant the requester their viewer relation so they can read it.
        self._authority.grant(requester, "requester", ticket.id)
        return ticket

    def ingest_email(self, email: InboundEmail) -> dict:
        """Normalize an inbound email to the ticket model (multi-origin), threading
        on headers/token but enforcing INV-EMAIL-1: append only for a verified
        sender matching the requester, else quarantine; no match → a new ticket."""
        route = route_inbound(email, self._store.all())
        if route.action == "quarantine":
            # Held for agent review, not attributed (INV-EMAIL-1). A valid outcome,
            # not an error: the mail is accepted but not threaded.
            return {"action": "quarantine", "ticket": route.ticket_id, "reason": route.reason}
        if route.action == "append":
            self._append(route.ticket_id, requester_of(email), email)
            return {"action": "append", "ticket": route.ticket_id}
        ticket = self.create("email", requester_of(email), email_message_id=email.message_id)
        self._append(ticket.id, requester_of(email), email)
        return {"action": "new", "ticket": ticket.id}

    def _append(self, ticket_id: str, author: str, email: InboundEmail) -> None:
        if self._comments is not None:
            self._comments.add(TicketComment(
                ticket_id=ticket_id, author=author, body=email.body,
                source="email", message_id=email.message_id,
            ))

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
