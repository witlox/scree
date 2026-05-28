from scree.access.identity import IdentityDirectory
from scree.access.ticket_authority import TicketAuthority


class ErasureService:
    """GDPR erasure by anonymization (INV-DP-2, ADR-0006). Erasure deletes the
    identity-directory record — so the opaque requester id on existing tickets
    becomes unresolvable — and purges the subject's OpenFGA relation tuples
    (AR-05). Git is NOT rewritten: tickets remain with an orphaned opaque id, in
    line with the "bounded by the GitLab substrate" decision.

    Crypto-shred of a per-requester encryption key (for encrypted tickets) lands
    with the encryption-at-create slice; this service covers anonymization."""

    def __init__(self, identity: IdentityDirectory, ticket_authority: TicketAuthority) -> None:
        self._identity = identity
        self._authority = ticket_authority

    def erase(self, opaque_id: str) -> dict:
        """Idempotent: erasing an unknown/already-erased id is a no-op success."""
        identity_removed = self._identity.email_for(opaque_id) is not None
        self._identity.erase(opaque_id)
        relations_purged = self._authority.purge_relations(opaque_id)
        return {
            "erased": opaque_id,
            "identity_removed": identity_removed,
            "relations_purged": relations_purged,
        }
