"""unit — G-A14 / INV-ACC-4: the org tag on an external customer grants NO access.
Two customers in the same org can read each other's tickets only via an explicit
relation (requester/watcher/assignee/agent) or community_visible — never because they
share an org."""

from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.servicedesk.models import Ticket


def test_same_org_customer_cannot_read_anothers_ticket():
    fga = FakeOpenFga()
    authority = TicketAuthority(fga, agents=set())
    # cust-a and cust-b are both tagged org "uni-acme"; only cust-a is the requester.
    fga.write("cust-a", "requester", "ticket-1")
    ticket = Ticket(id="ticket-1", requester="cust-a")

    assert authority.can_read("cust-a", ticket) is True
    # No relation, not community_visible, same org → no access (INV-ACC-4).
    assert authority.can_read("cust-b", ticket) is False
    assert authority.readable_tickets("cust-b", [ticket]) == set()
