from dataclasses import dataclass


@dataclass(frozen=True)
class Epic:
    """A GitLab planning object referenced by the rollup (read-only). `group` is
    the GitLab group it lives in — authority over the epic is membership of that
    group (permission-enforcement-map; module-graph planning/)."""

    id: str
    group: str
    title: str
    capacity: int = 0
