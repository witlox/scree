import re
from dataclasses import dataclass
from typing import Literal

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


def route(candidate: Ticket | None, *, verified: bool, requester: str | None) -> EmailRoute:
    """Decide where an inbound email goes, given an already-resolved threading
    `candidate` and the TRUSTED (out-of-band) verification verdict + opaque
    `requester`. INV-EMAIL-1: nothing is attributed or threaded unless the sender
    is verified; a matched ticket is appended to only when the verified requester
    matches the ticket's requester — otherwise quarantine. No verified sender at
    all (incl. first contact) → quarantine for agent review, never a silent
    attributed ticket (G4-02)."""
    if not verified:
        return EmailRoute("quarantine", candidate.id if candidate else None,
                          "sender not DKIM/DMARC verified")
    if candidate is None:
        return EmailRoute("new")
    if requester != candidate.requester:
        return EmailRoute("quarantine", candidate.id, "verified sender does not match requester")
    return EmailRoute("append", candidate.id)
