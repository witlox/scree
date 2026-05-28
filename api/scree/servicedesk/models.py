from dataclasses import dataclass
from typing import Literal

TicketStatus = Literal["open", "resolved", "closed"]


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
