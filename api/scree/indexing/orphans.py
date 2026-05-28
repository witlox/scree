import datetime as dt
from dataclasses import dataclass, field

from scree.access.authority import Authority
from scree.access.ticket_authority import TicketAuthority
from scree.risk.models import Risk
from scree.servicedesk.models import Ticket

DEFAULT_UNASSIGNED_THRESHOLD = dt.timedelta(days=7)


@dataclass
class OrphanReport:
    """Result of an orphan-detection pass (INV-ORPH). Flags only — detection never
    auto-reassigns. `resources` is keyed by Space (for that Space's maintainers);
    `tickets` is for desk leads."""

    resources: dict[str, list[str]] = field(default_factory=dict)
    tickets: list[str] = field(default_factory=list)


def detect_orphans(
    risks: list[Risk],
    tickets: list[Ticket],
    *,
    authority: Authority,
    ticket_authority: TicketAuthority,
    now: dt.datetime | None = None,
    unassigned_threshold: dt.timedelta = DEFAULT_UNASSIGNED_THRESHOLD,
) -> OrphanReport:
    now = now or dt.datetime.now(dt.timezone.utc)
    report = OrphanReport()

    # INV-ORPH-1: an active (non-closed) resource whose owner lost access to its
    # Space is flagged for that Space's maintainers. Never auto-reassigned.
    for r in risks:
        if r.status == "closed" or not r.owner:
            continue
        if r.space not in authority.readable_spaces(r.owner):
            report.resources.setdefault(r.space, []).append(r.id)

    # INV-ORPH-2: an open ticket is orphaned when its assignee lost desk access, or
    # it is unassigned beyond the threshold. The ticket owner is the desk, so the
    # owner-rule above doesn't catch it.
    for t in tickets:
        if t.status != "open":
            continue
        if t.assignee is not None:
            if not ticket_authority.is_agent(t.assignee):
                report.tickets.append(t.id)
        elif _older_than(t.created_at, now, unassigned_threshold):
            report.tickets.append(t.id)

    return report


def _older_than(created_at: str | None, now: dt.datetime, threshold: dt.timedelta) -> bool:
    if not created_at:
        return False  # unknown age → can't assert orphaned
    return (now - dt.datetime.fromisoformat(created_at)) > threshold
