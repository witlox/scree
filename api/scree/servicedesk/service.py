import datetime as dt
import uuid
from dataclasses import replace

from scree.access.identity import IdentityDirectory
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import DecryptionUnavailable, TicketCrypto
from scree.integration.o365.inbound import InboundEmail

from .comments import CommentStore, TicketComment
from .email_routing import extract_token, route
from .lifecycle import transition
from .models import Origin, Ticket, TicketStatus
from .quarantine import QuarantinedEmail, QuarantineStore
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
        *,
        identity: IdentityDirectory | None = None,
        quarantine: QuarantineStore | None = None,
        crypto: TicketCrypto | None = None,
    ) -> None:
        self._store = store
        self._authority = authority
        self._comments = comment_store
        self._identity = identity
        self._quarantine = quarantine
        self._crypto = crypto
        self._email_seq = 0  # G4-04: numeric SCREE-NNN sequence (spike; per-instance)

    def create(
        self,
        origin: Origin,
        requester: str,
        space: str = "support/service-desk",
        *,
        email_message_id: str | None = None,
        encrypted: bool = False,
        ticket_id: str | None = None,
    ) -> Ticket:
        """Create a ticket from any origin, normalized to one record: opaque
        requester (INV-DP-1), status open. Tickets default requester-private even
        from public Slack threads (DD-013). `encrypted` is a create-time decision.
        `ticket_id` lets migration use a DETERMINISTIC id for idempotency (G10-01)."""
        # DD-013: tickets default requester-private regardless of origin (even a
        # public Slack thread); promotion to community-visible is explicit.
        token = None
        if origin == "email":
            # G4-04: numeric token so the [SCREE-NNN] matcher (\d+) actually matches.
            self._email_seq += 1
            token = f"SCREE-{self._email_seq}"
        ticket = Ticket(
            id=ticket_id or f"ticket-{uuid.uuid4().hex[:8]}",
            requester=requester,
            space=space,
            status="open",
            origin=origin,
            community_visible=False,
            email_token=token,  # lets later replies thread when RFC headers are stripped
            email_message_id=email_message_id,
            created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            encrypted=encrypted,
        )
        self._store.put(ticket)
        # I-01: grant the requester their viewer relation so they can read it.
        self._authority.grant(requester, "requester", ticket.id)
        return ticket

    def _candidate(self, email: InboundEmail) -> Ticket | None:
        # G4-07: O(1) threading lookup via store indexes (headers, then token).
        for ref in [email.in_reply_to, *email.references]:
            if ref:
                t = self._store.by_message_id(ref)
                if t is not None:
                    return t
        token = extract_token(email.subject)
        if token:
            return self._store.by_token(token)
        return None

    def ingest_email(self, email: InboundEmail, *, verified: bool, sender: str | None) -> dict:
        """Normalize an inbound email to the ticket model. `verified`/`sender` are
        the TRUSTED out-of-band verdict + aligned sender from the poller (G4-01),
        NOT anything in the raw message. INV-EMAIL-1: nothing is attributed or
        threaded unless verified (G4-02); the sender resolves to an OPAQUE id via
        the identity directory so no PII enters Git (G4-03)."""
        candidate = self._candidate(email)
        requester = self._identity.resolve(sender) if (verified and sender and self._identity) else None
        decision = route(candidate, verified=verified, requester=requester)
        if decision.action == "quarantine":
            self._hold(email, decision)  # G4-05: persist for agent review
            return {"action": "quarantine", "ticket": decision.ticket_id, "reason": decision.reason}
        if decision.action == "append":
            self._append(decision.ticket_id, requester, email)
            return {"action": "append", "ticket": decision.ticket_id}
        ticket = self.create("email", requester, email_message_id=email.message_id)
        self._append(ticket.id, requester, email)
        return {"action": "new", "ticket": ticket.id}

    def _principal_for(self, mapped: str | None) -> str | None:
        """Normalize a Slack-mapped identity to the principal we store. Internal
        agents pass through; external customers resolve to an OPAQUE id via the
        identity directory so no PII enters Git/OpenFGA (G6-01, consistent with the
        email path's G4-03 fix)."""
        if mapped is None:
            return None
        if self._authority.is_agent(mapped):
            return mapped
        return self._identity.resolve(mapped) if self._identity else mapped

    def capture_from_slack(self, reactor: str, author: str, snapshot: str, *, slack_dir, limiter) -> dict:
        """Capture a Slack thread into a requester-private draft (DD-012/DD-013).
        INV-SLACK-1: the requester is the captured message's AUTHOR (resolved to a
        Keycloak identity; refused if unmappable, INV-ID-2); the capturer is
        recorded separately; capture is rate-limited per Slack user."""
        reactor_raw = slack_dir.resolve(reactor)
        if reactor_raw is None:
            return {"action": "refused", "reason": "reactor identity could not be resolved"}
        author_raw = slack_dir.resolve(author)
        if author_raw is None:
            return {"action": "refused", "reason": "author identity could not be resolved"}
        # G6-03: rate-limit only resolvable captures, so the limit counts captures
        # (not failed lookups) per the spec's "5 captures".
        if not limiter.allow(reactor):
            return {"action": "refused", "reason": "rate limited"}
        requester = self._principal_for(author_raw)  # external author -> opaque (G6-01)
        captured_by = self._principal_for(reactor_raw)
        ticket = self.create("slack", requester)  # community_visible=False (DD-013)
        self._store.put(replace(ticket, captured_by=captured_by))  # capturer recorded separately
        self._store_comment(ticket.id, captured_by, snapshot, "slack")
        return {"action": "captured", "ticket": ticket.id,
                "requester": requester, "captured_by": captured_by}

    def link_from_slack(self, reactor: str, ticket_id: str, snapshot: str, *, slack_dir) -> dict:
        """Attach a thread snapshot to an existing ticket — only if the reactor's
        mapped identity may see it (existence-leak-safe refusal otherwise)."""
        reactor_raw = slack_dir.resolve(reactor)
        if reactor_raw is None:
            return {"action": "refused", "reason": "reactor identity could not be resolved"}
        reactor_principal = self._principal_for(reactor_raw)  # opaque for externals (G6-01)
        ticket = self._store.get(ticket_id)
        if ticket is None or not self._authority.can_read(reactor_principal, ticket):
            return {"action": "refused", "reason": "ticket not visible"}
        self._store_comment(ticket_id, reactor_principal, snapshot, "slack")
        return {"action": "linked", "ticket": ticket_id}

    def _hold(self, email: InboundEmail, decision) -> None:
        if self._quarantine is not None:
            self._quarantine.add(QuarantinedEmail(
                claimed_from=email.from_addr, subject=email.subject, body=email.body,
                reason=decision.reason or "quarantined", candidate_ticket=decision.ticket_id,
            ))

    def exists(self, ticket_id: str) -> bool:
        return self._store.get(ticket_id) is not None

    def add_comment(self, ticket_id: str, author: str, body: str, source: str = "api") -> None:
        self._store_comment(ticket_id, author, body, source)

    def _append(self, ticket_id: str, author: str, email: InboundEmail) -> None:
        self._store_comment(ticket_id, author, email.body, "email", message_id=email.message_id)

    def _store_comment(self, ticket_id, author, body, source, message_id=None) -> None:
        """Append a comment, encrypting the body at rest when the ticket is
        encrypted (ADR-0005: per-requester key, Gateway-mediated)."""
        if self._comments is None:
            return
        ticket = self._store.get(ticket_id)
        encrypted = bool(ticket and ticket.encrypted and self._crypto is not None)
        stored = self._crypto.encrypt(ticket.requester, body) if encrypted else body
        self._comments.add(TicketComment(
            ticket_id=ticket_id, author=author, body=stored,
            source=source, message_id=message_id, encrypted=encrypted,
        ))

    def read_comments(self, ticket_id: str) -> list[dict]:
        """Return a ticket's comments, decrypting encrypted bodies via the Gateway.
        A crypto-shredded body is surfaced as an unrecoverable marker, not raw
        ciphertext (INV-DP-2 erasure)."""
        ticket = self._store.get(ticket_id)
        out: list[dict] = []
        for c in (self._comments.for_ticket(ticket_id) if self._comments else []):
            body = c.body
            if c.encrypted and self._crypto is not None and ticket is not None:
                try:
                    body = self._crypto.decrypt(ticket.requester, c.body)
                except DecryptionUnavailable:
                    body = "[unrecoverable: encryption key erased]"
            out.append({"author": c.author, "body": body, "source": c.source})
        return out


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
        if ticket.encrypted:
            # G11-01: an encrypted (sensitive) ticket must not become a public
            # community snapshot — its content would have to be decrypted into the KB.
            raise NotPromotable(ticket_id)
        updated = replace(ticket, community_visible=True)
        self._store.put(updated)
        return updated
