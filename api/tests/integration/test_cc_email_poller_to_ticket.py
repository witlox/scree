"""@api cross-context (INTEGRATOR) — full inbound-email seam (#86 + INV-EMAIL-1):
O365/Graph message → poller (computes the TRUSTED DKIM/DMARC verdict) → Gateway
/tickets/inbound-email (service-principal) → ticket. A trusted dmarc=pass is attributed
to the verified opaque sender; a forged Authentication-Results is distrusted and
quarantined, never attributed (G4-01)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.integration.o365.poller import GraphMessage, GraphPoller
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.quarantine import QuarantineStore
from scree.servicedesk.store import TicketStore

OURS = "mx.scree.example"
POLLER = "svc:poller"
SENDER = "r.okafor@uni.example.ac"


def _raw(from_addr):
    return f"From: {from_addr}\r\nSubject: help\r\nMessage-ID: <m@uni.example.ac>\r\n\r\nbody"


def _ar(authserv, dmarc):
    return ("Authentication-Results", f"{authserv}; dmarc={dmarc} header.from=uni.example.ac")


class _FakeGraph:
    def __init__(self, messages):
        self._messages = messages

    def fetch_new(self):
        return list(self._messages)


def test_graph_poll_to_ticket_through_gateway():
    store = TicketStore()
    quarantine = QuarantineStore()
    client = TestClient(create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), agents=set()),
        comment_store=CommentStore(), identity_directory=IdentityDirectory(),
        quarantine_store=quarantine, service_principals={POLLER}, allow_insecure_header_auth=True,
    ))

    legit = GraphMessage(headers=[_ar(OURS, "pass")], raw=_raw(SENDER))
    forged = GraphMessage(headers=[_ar("evil.attacker.test", "pass")], raw=_raw("spoof@uni.example.ac"))

    def ingest(raw, *, verified, sender):
        return client.post(
            "/tickets/inbound-email",
            json={"raw": raw, "verified": verified, "sender": sender},
            headers={"X-Spike-User": POLLER},
        ).json()

    poller = GraphPoller(graph=_FakeGraph([legit, forged]), ingest=ingest, authserv_id=OURS)
    actions = [r["action"] for r in poller.poll_once()]

    assert actions == ["new", "quarantine"]  # trusted → ticket; forged → quarantine
    assert len(store.all()) == 1 and len(quarantine.all()) == 1
    assert "@" not in store.all()[0].requester  # attributed to an opaque id (INV-DP-1)
