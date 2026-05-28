from .models import TicketStatus

# Legal ticket transitions (INV-LC-1): open -> resolved -> closed, with reopen.
LEGAL: set[tuple[str, str]] = {
    ("open", "resolved"),
    ("resolved", "closed"),
    ("resolved", "open"),  # reopen
    ("closed", "open"),  # reopen
}


class IllegalTransition(ValueError):
    """A ticket state transition that is not in the legal set (INV-LC-1)."""


def transition(current: TicketStatus, target: TicketStatus) -> TicketStatus:
    if (current, target) not in LEGAL:
        raise IllegalTransition(f"{current} -> {target}")
    return target
