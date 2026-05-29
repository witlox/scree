from dataclasses import dataclass
from typing import Literal

TicketStatus = Literal["open", "resolved", "closed"]
Origin = Literal["email", "web", "slack", "api"]


@dataclass(frozen=True)
class Ticket:
    """A service-desk ticket (spike shape). `requester` is an opaque id
    resolved out-of-Git (INV-DP-1)."""

    id: str
    requester: str
    space: str = "support/service-desk"
    status: TicketStatus = "open"
    assignee: str | None = None
    community_visible: bool = False
    origin: Origin = "api"
    email_token: str | None = None  # low-trust threading candidate (INV-EMAIL-1)
    email_message_id: str | None = None  # RFC Message-ID for header threading
    captured_by: str | None = None  # Slack capturer, recorded separately (INV-SLACK-1)
    created_at: str | None = None  # ISO-8601; for unassigned-age orphan check (INV-ORPH-2)
    encrypted: bool = False  # create-time decision; body encrypted at rest (ADR-0005)
    # INV-LC-2: a frozen curated snapshot captured at promote time. Community-only
    # viewers see THIS, never the live thread, so later private replies/attachments
    # do not leak. Cleared on reopen (re-gates to private). Tuple of (author, body, source).
    community_snapshot: tuple[tuple[str, str, str], ...] | None = None
