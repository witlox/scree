from dataclasses import dataclass


@dataclass(frozen=True)
class Doc:
    """A knowledge resource (spike shape; full schema in specs/frontmatter-schemas)."""

    id: str
    title: str
    space: str
    body: str
    schema_version: int = 1  # INV-ST-3; needed to rebuild frontmatter on edit
    created: str | None = None  # derived from Git history (INV-ST-5)
    updated: str | None = None
    path: str | None = None  # location within the Space; folder path = page hierarchy
