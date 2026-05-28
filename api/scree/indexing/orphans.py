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
    auto-reassigns. Both maps are keyed by Space: `resources` for that Space's
    maintainers, `tickets` for that desk's leads (G7-02). `as_of` is the batch time."""

    resources: dict[str, list[str]] = field(default_factory=dict)
    tickets: dict[str, list[str]] = field(default_factory=dict)
    as_of: str | None = None


@dataclass
class OrphanCache:
    """Holds the latest batch-computed report (G7-03) so reads don't recompute."""

    report: OrphanReport | None = None


def detect_orphans(
    risks: list[Risk],
    tickets: list[Ticket],
    *,
    authority: Authority,
    ticket_authority: TicketAuthority | None = None,
    archived_spaces: frozenset[str] | set[str] = frozenset(),
    now: dt.datetime | None = None,
    unassigned_threshold: dt.timedelta = DEFAULT_UNASSIGNED_THRESHOLD,
) -> OrphanReport:
    now = now or dt.datetime.now(dt.timezone.utc)
    report = OrphanReport(as_of=now.isoformat())

    # INV-ORPH-1: an active (non-closed) resource is orphaned when its Space is
    # archived OR its owner can no longer MAINTAIN it (lost write, G7-04). Flag for
    # the Space's maintainers; never auto-reassign.
    for r in risks:
        if r.status == "closed" or not r.owner:
            continue
        if r.space in archived_spaces or not authority.can_write(r.owner, r.space):
            report.resources.setdefault(r.space, []).append(r.id)

    # INV-ORPH-2: an open ticket is orphaned when its desk is archived, its assignee
    # lost desk access, or it is unassigned beyond the threshold. Grouped by desk
    # Space so the report can be scoped to that desk's leads (G7-02).
    for t in tickets:
        if t.status != "open":
            continue
        assignee_gone = (
            t.assignee is not None and ticket_authority is not None
            and not ticket_authority.is_agent(t.assignee)
        )
        unassigned_stale = t.assignee is None and _older_than(t.created_at, now, unassigned_threshold)
        if t.space in archived_spaces or assignee_gone or unassigned_stale:
            report.tickets.setdefault(t.space, []).append(t.id)

    return report


def _older_than(created_at: str | None, now: dt.datetime, threshold: dt.timedelta) -> bool:
    if not created_at:
        return False  # unknown age → can't assert orphaned
    return (now - dt.datetime.fromisoformat(created_at)) > threshold
