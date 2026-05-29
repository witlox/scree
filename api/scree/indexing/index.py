import datetime as dt
from dataclasses import dataclass

from scree.knowledge.models import Doc
from scree.risk.models import Risk
from scree.risk.triggers import fires_critical_webhook


@dataclass(frozen=True)
class IndexEntry:
    id: str
    kind: str  # "doc" | "risk"
    space: str  # for per-request INV-AGG filtering (space membership)
    title: str
    text: str  # searchable text
    sensitive: bool  # security/compliance risk → separate partition (INV-IX-4)


def entry_from_doc(d: Doc) -> IndexEntry:
    return IndexEntry(id=d.id, kind="doc", space=d.space, title=d.title, text=d.body, sensitive=False)


def entry_from_risk(r: Risk) -> IndexEntry:
    # INV-IX-1/IX-4: security/compliance categories are the sensitive, webhook-driven set.
    return IndexEntry(id=r.id, kind="risk", space=r.space, title=r.title, text=r.title,
                      sensitive=fires_critical_webhook(r))


def entries_from(docs: list[Doc], risks: list[Risk]) -> list[IndexEntry]:
    return [entry_from_doc(d) for d in docs] + [entry_from_risk(r) for r in risks]


class Index:
    """Derived search index — rebuildable from Git alone (INV-ST-2); Git is truth.
    Three triggers maintain it (DD-005): the hourly batch and the manual trigger both
    `rebuild()` (full re-read), the critical webhook `upsert()`s one entry. Sensitive
    (security/compliance) entries live in a SEPARATE partition (INV-IX-4). A webhook
    missed/dropped is caught by the next rebuild, so correctness never depends on
    webhook delivery (INV-IX-2); both paths re-read from Git and key by `id`, so they
    are idempotent (no duplicates, fresher Git wins)."""

    def __init__(self) -> None:
        self._main: dict[str, IndexEntry] = {}
        self._sensitive: dict[str, IndexEntry] = {}
        self._as_of: str | None = None

    def upsert(self, entry: IndexEntry) -> None:
        # Drop any prior copy from both partitions first, so a kind/sensitivity change
        # can't leave a stale duplicate; then place it in the right partition.
        self._main.pop(entry.id, None)
        self._sensitive.pop(entry.id, None)
        (self._sensitive if entry.sensitive else self._main)[entry.id] = entry

    def rebuild(self, entries: list[IndexEntry]) -> None:
        self._main.clear()
        self._sensitive.clear()
        for e in entries:
            self.upsert(e)
        self._as_of = dt.datetime.now(dt.timezone.utc).isoformat()

    def as_of(self) -> str | None:
        return self._as_of

    def size(self) -> int:
        return len(self._main) + len(self._sensitive)

    def has(self, entry_id: str) -> bool:
        return entry_id in self._main or entry_id in self._sensitive

    def is_sensitive(self, entry_id: str) -> bool:
        return entry_id in self._sensitive

    def search(self, needle: str, *, include_sensitive: bool) -> list[IndexEntry]:
        """Candidate matches; the Gateway still filters per item by authority (INV-AGG).
        Sensitive entries are only considered when `include_sensitive` (they live in a
        separate partition, INV-IX-4)."""
        pool = list(self._main.values())
        if include_sensitive:
            pool += list(self._sensitive.values())
        n = needle.lower()
        return [e for e in pool if n in e.text.lower() or n in e.title.lower()]
