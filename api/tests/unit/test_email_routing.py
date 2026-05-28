"""TDD — inbound-email parse + threading routing (INV-EMAIL-1): headers/token are
candidates, not authority; append only for a verified sender matching the
requester, else quarantine; no match → new."""

from scree.integration.o365.inbound import parse_inbound
from scree.servicedesk.email_routing import EmailRoute, extract_token, route_inbound
from scree.servicedesk.models import Ticket

MID = "<CA+abc123@mail.uni.example.ac>"
REQ = "ext:r.okafor@uni.example.ac"
TICKET = Ticket(id="ticket-123", requester=REQ, email_message_id=MID, email_token="SCREE-123")


def _email(frm="r.okafor@uni.example.ac", subject="hi", references="", verified=True, in_reply_to=None):
    headers = [f"From: {frm}", f"Subject: {subject}"]
    if references:
        headers.append(f"References: {references}")
    if in_reply_to:
        headers.append(f"In-Reply-To: {in_reply_to}")
    if verified:
        headers.append("Authentication-Results: mx.scree; dmarc=pass header.from=uni.example.ac")
    return parse_inbound("\n".join(headers) + "\n\nbody text\n")


def test_extract_token():
    assert extract_token("Re: [SCREE-123] export fails") == "SCREE-123"
    assert extract_token("no token here") is None


def test_parse_extracts_fields_and_verdict():
    e = parse_inbound(
        "From: R. Okafor <r.okafor@uni.example.ac>\n"
        "Subject: Re: hi\n"
        f"References: {MID}\n"
        "Authentication-Results: mx.scree; dmarc=pass\n\nhello\n"
    )
    assert e.from_addr == "r.okafor@uni.example.ac"
    assert e.references == [MID]
    assert e.verified is True
    assert "hello" in e.body


def test_header_match_appends():
    assert route_inbound(_email(references=MID), [TICKET]) == EmailRoute("append", "ticket-123")


def test_token_fallback_appends():
    e = _email(subject="Re: [SCREE-123] export fails")
    assert route_inbound(e, [TICKET]) == EmailRoute("append", "ticket-123")


def test_no_candidate_is_new():
    assert route_inbound(_email(subject="help please"), [TICKET]).action == "new"


def test_spoofed_sender_quarantined():
    # Matches the token but a different verified sender → quarantine (INV-EMAIL-1).
    e = _email(frm="attacker@evil.example", subject="Re: [SCREE-123] gimme")
    r = route_inbound(e, [TICKET])
    assert r.action == "quarantine" and r.ticket_id == "ticket-123"


def test_unverified_sender_quarantined():
    # Right sender, but no DKIM/DMARC pass → candidates are not authority.
    e = _email(references=MID, verified=False)
    assert route_inbound(e, [TICKET]).action == "quarantine"
