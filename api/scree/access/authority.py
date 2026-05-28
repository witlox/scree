from scree.knowledge.models import Doc


class Authority:
    """Spike stub for the architected authority composition
    (GitLab repo membership ∪ OpenFGA relations — see permission-enforcement-map).

    For the spike, a principal's authority is the set of Spaces they may read.
    """

    def __init__(
        self,
        readable_spaces: dict[str, set[str]],
        writable_spaces: dict[str, set[str]] | None = None,
    ) -> None:
        self._readable = readable_spaces
        # Write authority defaults to read authority (Space members can write).
        self._writable = writable_spaces if writable_spaces is not None else readable_spaces

    def readable_spaces(self, principal: str) -> set[str]:
        return self._readable.get(principal, set())

    def can_read(self, principal: str, doc: Doc) -> bool:
        # INV-ACC/INV-AGG: authorized iff the doc's Space is in the principal's
        # readable set. (Real impl composes GitLab membership ∪ OpenFGA.)
        return doc.space in self.readable_spaces(principal)

    def can_write(self, principal: str, space: str) -> bool:
        # DD-007: write inherits GitLab project write membership.
        return space in self._writable.get(principal, set())
