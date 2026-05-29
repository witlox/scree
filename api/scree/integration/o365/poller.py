"""O365 / Microsoft Graph inbound poller — the TRUSTED source of the DKIM/DMARC verdict
that INV-EMAIL-1 attribution depends on (G4-01).

The verdict is read from the `Authentication-Results` header stamped by OUR receiving
mail infrastructure (its `authserv-id`). O365 strips any inbound A-R bearing its own
authserv-id before adding its own, so by the time we fetch a message via Graph, the
only A-R with our authserv-id is the authoritative one. A-R headers an attacker
embedded (any other authserv-id) are ignored. This is what makes the verdict
trustworthy rather than an attacker-controlled assumption.

The live Graph delta/subscription fetch is a deploy concern (RealGraphClient); the
verdict logic and the poll→ingest flow are what's tested here.
"""

import re
from dataclasses import dataclass
from typing import Callable, Protocol

from .inbound import parse_inbound


@dataclass(frozen=True)
class GraphMessage:
    """A message as Microsoft Graph delivers it: the header list (incl. our mail
    infra's Authentication-Results) and the raw RFC822 for structural parsing."""

    headers: list[tuple[str, str]]
    raw: str


class GraphClient(Protocol):
    def fetch_new(self) -> list[GraphMessage]: ...


def _authserv_id(ar_value: str) -> str:
    # The authserv-id is the first token of the A-R, before the first ';'.
    head = ar_value.split(";", 1)[0].strip()
    return head.split()[0] if head else ""


def _result(ar_value: str, method: str) -> str | None:
    m = re.search(rf"\b{re.escape(method)}=([A-Za-z]+)", ar_value)
    return m.group(1).lower() if m else None


def dmarc_pass(headers: list[tuple[str, str]], *, authserv_id: str) -> bool:
    """True iff an Authentication-Results stamped by OUR authserv-id reports dmarc=pass.
    A-R from any other authserv-id (e.g. attacker-embedded) is ignored (G4-01); no
    trusted A-R ⇒ not verified."""
    for name, value in headers:
        if name.lower() != "authentication-results":
            continue
        if _authserv_id(value) != authserv_id:
            continue  # not stamped by our mail infra — untrusted, ignore
        return _result(value, "dmarc") == "pass"
    return False


@dataclass
class GraphPoller:
    """Polls O365 via Graph, computes the trusted verdict per message, and hands each
    to `ingest` (in deploy: POST /tickets/inbound-email; in tests: the TicketService).
    The aligned sender is the message From — trustworthy only BECAUSE DMARC passed on a
    trusted A-R; otherwise the verdict is unverified and the sender is withheld so the
    Gateway quarantines rather than attributes (INV-EMAIL-1)."""

    graph: GraphClient
    ingest: Callable[..., dict]
    authserv_id: str

    def poll_once(self) -> list[dict]:
        results: list[dict] = []
        for msg in self.graph.fetch_new():
            email = parse_inbound(msg.raw)
            verified = dmarc_pass(msg.headers, authserv_id=self.authserv_id)
            sender = email.from_addr if verified else None
            results.append(self.ingest(msg.raw, verified=verified, sender=sender))
        return results
