from dataclasses import dataclass, field
from email import message_from_string
from email.utils import parseaddr


@dataclass(frozen=True)
class InboundEmail:
    """A parsed inbound email. `verified` is the DKIM/DMARC alignment verdict —
    the threading headers/token are candidates, NOT authority (INV-EMAIL-1); the
    servicedesk router decides append/new/quarantine."""

    from_addr: str
    subject: str
    body: str
    message_id: str | None = None
    in_reply_to: str | None = None
    references: list[str] = field(default_factory=list)
    verified: bool = False


def _references(raw: str | None) -> list[str]:
    if not raw:
        return []
    # References/In-Reply-To are whitespace-separated <message-id> tokens.
    return [tok for tok in raw.split() if tok.strip()]


def _dmarc_pass(msg) -> bool:
    """We trust the verdict our ingress MTA records in Authentication-Results
    (the MTA/Graph does the DKIM/DMARC crypto); alignment must be `dmarc=pass`."""
    results = " ".join(msg.get_all("Authentication-Results", [])).lower()
    return "dmarc=pass" in results


def _body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.is_multipart():
                return part.get_payload(decode=True).decode(errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="replace") if payload is not None else (msg.get_payload() or "")


def parse_inbound(raw: str) -> InboundEmail:
    msg = message_from_string(raw)
    return InboundEmail(
        from_addr=parseaddr(msg.get("From", ""))[1].lower(),
        subject=msg.get("Subject", "") or "",
        body=_body(msg).strip(),
        message_id=(msg.get("Message-ID") or "").strip() or None,
        in_reply_to=(msg.get("In-Reply-To") or "").strip() or None,
        references=_references(msg.get("References")),
        verified=_dmarc_pass(msg),
    )
