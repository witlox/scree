from .models import Epic


class PlanningIndex:
    """Derived, rebuildable index of GitLab planning refs (indexer-design). Git/
    GitLab is truth; this is an optimization. `as_of` is the last refresh time so
    views can surface staleness (INV-IX-2, `last_indexed`)."""

    def __init__(self, epics: list[Epic] | None = None, last_indexed: str | None = None) -> None:
        self._epics = list(epics or [])
        self._last_indexed = last_indexed

    def candidates(self) -> list[Epic]:
        """The broad, unfiltered candidate set; the Gateway filters per request."""
        return list(self._epics)

    def as_of(self) -> str | None:
        return self._last_indexed
