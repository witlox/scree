import re
from dataclasses import dataclass
from typing import Literal

from scree.integration.o365.inbound import InboundEmail

from .models import Ticket

_TOKEN = re.compile(r"\[(SCREE-\d+)\]")

RouteAction = Literal["append", "new", "quarantine"]


@dataclass(frozen=True)
class EmailRoute:
    action: RouteAction
    ticket_id: str | None = None
    reason: str | None = None


def extract_token(subject: str) -> str | None:
    """The `[SCREE-NNN]` threading token from a subject, if present."""
    m = _TOKEN.search(subject or "")
    return m.group(1) if m else None


def requester_of(email: InboundEmail) -> str:
    """The opaque external requester id derived from the verified sender
    (INV-DP-1: the real id resolves via the identity directory, out of Git)."""
    return f"ext:{email.from_addr}"


def _candidate(email: InboundEmail, tickets: list[Ticket]) -> Ticket | None:
    # 1. RFC threading headers (Message-ID in References/In-Reply-To).
    refs = set(email.references)
    if email.in_reply_to:
        refs.add(email.in_reply_to)
    for t in tickets:
        if t.email_message_id and t.email_message_id in refs:
            return t
    # 2. Fallback: the [SCREE-NNN] subject token.
    token = extract_token(email.subject)
    if token:
        for t in tickets:
            if t.email_token == token:
                return t
    return None


def route_inbound(email: InboundEmail, tickets: list[Ticket]) -> EmailRoute:
    """Decide where an inbound email goes. Threading headers and the token are
    candidates, NOT authority (INV-EMAIL-1): a matched ticket is only appended to
    when the sender is verified AND matches the ticket's requester; otherwise the
    mail is quarantined for agent review — never silently appended or attributed."""
    candidate = _candidate(email, tickets)
    if candidate is None:
        return EmailRoute("new")
    if not email.verified:
        return EmailRoute("quarantine", candidate.id, "sender not DKIM/DMARC verified")
    if requester_of(email) != candidate.requester:
        return EmailRoute("quarantine", candidate.id, "verified sender does not match requester")
    return EmailRoute("append", candidate.id)
