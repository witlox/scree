from dataclasses import dataclass


@dataclass(frozen=True)
class Doc:
    """A knowledge resource (spike shape; full schema in specs/frontmatter-schemas)."""

    id: str
    title: str
    space: str
    body: str
