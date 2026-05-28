"""TDD — validates the architected ticket-authority composition (INV-ACC-2, AR-04):
a customer sees only related tickets; an agent sees all (desk membership ∪ relations)."""

from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority

ALL = {"ticket-1", "ticket-2", "ticket-3"}


def _relations() -> FakeOpenFga:
    f = FakeOpenFga()
    f.write("cust-okafor", "requester", "ticket-1")
    f.write("cust-lind", "requester", "ticket-2")
    f.write("cust-okafor", "watcher", "ticket-2")
    f.write("cust-lind", "requester", "ticket-3")
    return f


def test_customer_reads_only_related_tickets():
    auth = TicketAuthority(_relations(), agents=set())
    assert auth.readable_tickets("cust-okafor", ALL) == {"ticket-1", "ticket-2"}
    assert auth.can_read("cust-okafor", "ticket-1") is True
    assert auth.can_read("cust-okafor", "ticket-3") is False


def test_agent_sees_all_desk_tickets():
    # AR-04: agents see all via GitLab desk membership, not per-ticket tuples.
    auth = TicketAuthority(_relations(), agents={"agent:dani"})
    assert auth.readable_tickets("agent:dani", ALL) == ALL
    assert auth.can_read("agent:dani", "ticket-3") is True
