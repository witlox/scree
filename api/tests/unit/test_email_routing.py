"""TDD — inbound-email parse (structural only) + threading routing decision.
INV-EMAIL-1: the verdict + aligned sender are trusted out-of-band (G4-01); the
route never threads/attributes an unverified sender (G4-02)."""

from scree.integration.o365.inbound import parse_inbound
from scree.servicedesk.email_routing import EmailRoute, extract_token, route
from scree.servicedesk.models import Ticket

MID = "<CA+abc123@mail.uni.example.ac>"
REQ = "ext-deadbeef0001"
TICKET = Ticket(id="ticket-123", requester=REQ, email_message_id=MID, email_token="SCREE-9")


def test_extract_token():
    assert extract_token("Re: [SCREE-123] export fails") == "SCREE-123"
    assert extract_token("no token here") is None


def test_parse_is_structural_only():
    e = parse_inbound(
        "From: R. Okafor <r.okafor@uni.example.ac>\n"
        "Subject: Re: hi\n"
        f"References: {MID}\n"
        "Authentication-Results: mx.scree; dmarc=pass\n\nhello\n"
    )
    assert e.from_addr == "r.okafor@uni.example.ac"  # claimed, untrusted
    assert e.references == [MID]
    assert "hello" in e.body
    # the verdict is NOT derived from the message anymore
    assert not hasattr(e, "verified")


def test_verified_match_appends():
    assert route(TICKET, verified=True, requester=REQ) == EmailRoute("append", "ticket-123")


def test_verified_no_candidate_is_new():
    assert route(None, verified=True, requester=REQ).action == "new"


def test_mismatched_requester_quarantined():
    assert route(TICKET, verified=True, requester="ext-other").action == "quarantine"


def test_unverified_always_quarantined():
    # Even with a matching candidate, an unverified sender is never threaded (G4-02).
    assert route(TICKET, verified=False, requester=REQ).action == "quarantine"
    # And unverified first contact (no candidate) is quarantined, not a new ticket.
    assert route(None, verified=False, requester=None).action == "quarantine"
