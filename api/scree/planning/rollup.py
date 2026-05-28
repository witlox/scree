from .models import Epic


def portfolio(epics: list[Epic], *, limit: int | None = None, cursor: int = 0) -> dict:
    """Aggregate an already-authority-filtered set of epics into a portfolio
    rollup. Callers MUST pass only epics the requester may see — totals and counts
    are derived from the input, so a leaked epic would leak via capacity/count
    (INV-AGG, indexer-design step 4).

    G3-02: the returned `epics` list is a bounded page (cursor pagination, AR-11);
    `epic_count`/`total_capacity` are the aggregate over ALL visible epics so the
    rollup totals stay correct regardless of the page."""
    page = epics[cursor:cursor + limit] if limit is not None else epics[cursor:]
    next_cursor = cursor + limit if (limit is not None and cursor + limit < len(epics)) else None
    return {
        "epics": [{"id": e.id, "title": e.title, "capacity": e.capacity} for e in page],
        "epic_count": len(epics),
        "total_capacity": sum(e.capacity for e in epics),
        "next_cursor": next_cursor,
    }
