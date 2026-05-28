from dataclasses import dataclass, field
from typing import Literal

SourceKind = Literal["jira", "confluence"]


@dataclass(frozen=True)
class SourceItem:
    """An Atlassian item presented to the migration pipeline. `marked` = curated for
    migration by the deadline; unmarked items are archived, not migrated (INV-MIG-3,
    default-archive). `reporter` is the original author/customer (jira)."""

    kind: SourceKind
    old_id: str  # e.g. "SUP-4821" (jira) or "12345" (confluence)
    title: str
    content: str
    marked: bool = False
    reporter: str | None = None  # external customer email (jira); resolved to opaque id
    space: str = "support/service-desk"


class IdMap:
    """Stable old→new ID mapping (INV-MIG-1). Idempotent: a legacy id is recorded
    once and never overwritten (INV-MIG-2). Spike: in-memory."""

    def __init__(self) -> None:
        self._map: dict[str, str] = {}

    def record(self, legacy_id: str, new_id: str) -> None:
        self._map.setdefault(legacy_id, new_id)  # never overwrite an existing mapping

    def resolve(self, legacy_id: str) -> str | None:
        return self._map.get(legacy_id)

    def has(self, legacy_id: str) -> bool:
        return legacy_id in self._map


@dataclass
class ArchiveStore:
    """Read-only archive of non-curated content (INV-MIG-3)."""

    _items: dict[str, SourceItem] = field(default_factory=dict)

    def archive(self, item: SourceItem) -> None:
        self._items.setdefault(item.old_id, item)

    def get(self, old_id: str) -> SourceItem | None:
        return self._items.get(old_id)

    def all(self) -> list[SourceItem]:
        return list(self._items.values())
