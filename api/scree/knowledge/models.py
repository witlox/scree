from dataclasses import dataclass


@dataclass(frozen=True)
class Doc:
    """A knowledge resource (spike shape; full schema in specs/frontmatter-schemas)."""

    id: str
    title: str
    space: str
    body: str
    created: str | None = None  # derived from Git history (INV-ST-5)
    updated: str | None = None
    path: str | None = None  # location within the Space; folder path = page hierarchy
