import datetime as dt
from dataclasses import dataclass, field

from scree.access.identity import IdentityDirectory
from scree.access.ticket_authority import TicketAuthority
from scree.servicedesk.quarantine import QuarantineStore

# Disclosed scope: erasure anonymizes (deletes the identity link + relation
# tuples). Ticket/comment bodies in Git are NOT removed — bounded by the GitLab
# substrate (ADR-0006); encryption is the stronger guarantee for sensitive data.
RESIDUAL_NOTE = "ticket/comment bodies remain in Git history (ADR-0006, bounded by substrate)"


@dataclass(frozen=True)
class ErasureReceipt:
    """Durable compliance record of a fulfilled erasure (G5-03)."""

    subject: str
    actor: str | None
    at: str  # ISO-8601 UTC
    identity_removed: bool
    relations_purged: int
    quarantine_purged: int


@dataclass
class ErasureReceiptStore:
    """Append-only erasure receipts for compliance evidence. Spike: in-memory."""

    _items: list[ErasureReceipt] = field(default_factory=list)

    def add(self, receipt: ErasureReceipt) -> None:
        self._items.append(receipt)

    def all(self) -> list[ErasureReceipt]:
        return list(self._items)


class ErasureService:
    """GDPR erasure by anonymization (INV-DP-2, ADR-0006). Erasure deletes the
    identity-directory record — so the opaque requester id on existing tickets
    becomes unresolvable — purges the subject's OpenFGA relation tuples (AR-05),
    and scrubs the subject's PII from the quarantine queue (G5-02). Git is NOT
    rewritten: tickets remain with an orphaned opaque id.

    Crypto-shred of a per-requester encryption key (for encrypted tickets) lands
    with the encryption-at-create slice; this service covers anonymization."""

    def __init__(
        self,
        identity: IdentityDirectory,
        ticket_authority: TicketAuthority,
        quarantine: QuarantineStore | None = None,
        receipts: ErasureReceiptStore | None = None,
        crypto=None,
    ) -> None:
        self._identity = identity
        self._authority = ticket_authority
        self._quarantine = quarantine
        self._receipts = receipts
        self._crypto = crypto

    def erase(self, opaque_id: str, actor: str | None = None) -> dict:
        """Idempotent: erasing an unknown/already-erased id is a no-op success."""
        # G5-02: resolve the email BEFORE deleting the mapping, so we can scrub the
        # quarantine queue (keyed by claimed sender address, not the opaque id).
        email = self._identity.email_for(opaque_id)
        identity_removed = email is not None
        self._identity.erase(opaque_id)
        relations_purged = self._authority.purge_relations(opaque_id)
        quarantine_purged = (
            self._quarantine.purge_sender(email) if (email and self._quarantine) else 0
        )
        if self._crypto is not None:
            self._crypto.destroy(opaque_id)  # crypto-shred: encrypted bodies now unrecoverable
        result = {
            "erased": opaque_id,
            "identity_removed": identity_removed,
            "relations_purged": relations_purged,
            "quarantine_purged": quarantine_purged,
            "crypto_shredded": self._crypto is not None,
            "residual": RESIDUAL_NOTE,
        }
        if self._receipts is not None:  # G5-03: durable compliance receipt
            self._receipts.add(ErasureReceipt(
                subject=opaque_id, actor=actor,
                at=dt.datetime.now(dt.timezone.utc).isoformat(),
                identity_removed=identity_removed, relations_purged=relations_purged,
                quarantine_purged=quarantine_purged,
            ))
        return result
