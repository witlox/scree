"""@api — #86 O365/Graph poller. The DKIM/DMARC verdict is read from OUR mail infra's
Authentication-Results (its authserv-id) — attacker-embedded A-R is ignored (G4-01) —
and drives INV-EMAIL-1: a trusted dmarc=pass attributes the ticket to the verified
sender; anything else is quarantined, never attributed."""

from scree.access.identity import IdentityDirectory
from scree.integration.o365.poller import GraphMessage, GraphPoller, dmarc_pass
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.quarantine import QuarantineStore
from scree.servicedesk.service import TicketService
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.servicedesk.store import TicketStore

OURS = "mx.scree.example"  # our receiving mail infra's authserv-id
SENDER = "r.okafor@uni.example.ac"


def _raw(from_addr=SENDER, subject="help", body="my thing is broken"):
    return f"From: {from_addr}\r\nSubject: {subject}\r\nMessage-ID: <m1@uni.example.ac>\r\n\r\n{body}"


def _ar(authserv, dmarc):
    return ("Authentication-Results", f"{authserv}; dmarc={dmarc} header.from=uni.example.ac; dkim={dmarc} header.d=uni.example.ac")


# --- verdict logic -----------------------------------------------------------

def test_trusted_dmarc_pass_is_verified():
    assert dmarc_pass([_ar(OURS, "pass")], authserv_id=OURS) is True


def test_trusted_dmarc_fail_is_not_verified():
    assert dmarc_pass([_ar(OURS, "fail")], authserv_id=OURS) is False


def test_attacker_embedded_ar_is_ignored():
    # An A-R from a different authserv-id claiming dmarc=pass must NOT be trusted; only
    # our mail infra's verdict counts. Here the attacker's "pass" is ignored and our
    # own "fail" stands.
    headers = [_ar("evil.attacker.test", "pass"), _ar(OURS, "fail")]
    assert dmarc_pass(headers, authserv_id=OURS) is False


def test_no_trusted_ar_is_not_verified():
    assert dmarc_pass([_ar("evil.attacker.test", "pass")], authserv_id=OURS) is False
    assert dmarc_pass([], authserv_id=OURS) is False


# --- poll -> ingest end to end (INV-EMAIL-1) ---------------------------------

class _FakeGraph:
    def __init__(self, messages):
        self._messages = messages

    def fetch_new(self):
        return list(self._messages)


def _service():
    store = TicketStore()
    quarantine = QuarantineStore()
    service = TicketService(
        store, TicketAuthority(FakeOpenFga(), agents=set()),
        comment_store=CommentStore(), identity=IdentityDirectory(), quarantine=quarantine,
    )
    return service, store, quarantine


def test_poll_attributes_a_trusted_message_and_quarantines_a_forged_one():
    service, store, quarantine = _service()
    from scree.integration.o365.inbound import parse_inbound

    legit = GraphMessage(headers=[_ar(OURS, "pass")], raw=_raw())
    forged = GraphMessage(headers=[_ar("evil.attacker.test", "pass")], raw=_raw(from_addr="spoof@uni.example.ac"))
    poller = GraphPoller(
        graph=_FakeGraph([legit, forged]),
        ingest=lambda raw, *, verified, sender: service.ingest_email(parse_inbound(raw), verified=verified, sender=sender),
        authserv_id=OURS,
    )

    actions = [r["action"] for r in poller.poll_once()]
    assert actions == ["new", "quarantine"]
    # exactly the trusted message became a ticket; the forged one is held, not attributed
    assert len(store.all()) == 1
    assert len(quarantine.all()) == 1
    # the attributed requester is the verified sender, resolved to an opaque id (INV-DP-1)
    t = store.all()[0]
    assert t.requester == service._identity.resolve(SENDER) and "@" not in t.requester
