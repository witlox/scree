from .models import Epic


def portfolio(epics: list[Epic]) -> dict:
    """Aggregate an already-authority-filtered set of epics into a portfolio
    rollup. Callers MUST pass only epics the requester may see — totals and counts
    are derived from the input, so a leaked epic would leak via capacity/count
    (INV-AGG, indexer-design step 4)."""
    return {
        "epics": [{"id": e.id, "title": e.title, "capacity": e.capacity} for e in epics],
        "epic_count": len(epics),
        "total_capacity": sum(e.capacity for e in epics),
    }
