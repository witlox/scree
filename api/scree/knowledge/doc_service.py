from scree.access.authority import Authority

from .frontmatter import parse  # InvalidFrontmatter propagates to the gateway (422)
from .git_store import GitBackedDocStore


class Forbidden(PermissionError):
    pass


class MRRequired(PermissionError):
    """Direct write to a governed (MR-required) path is refused (INV-GOV-1)."""


class WrongKind(ValueError):
    """The docs endpoint only accepts kind: doc."""


class DuplicateId(ValueError):
    """An id is already used by another path (INV-ST-4 uniqueness)."""


class Conflict(ValueError):
    """Optimistic-concurrency mismatch — the base revision is stale (INV-ST-6)."""


def is_governed(path: str, governed_prefixes: set[str]) -> bool:
    return any(path == p or path.startswith(p) for p in governed_prefixes)


class DocService:
    """Doc write path: validate frontmatter, enforce write authority and
    MR-required governed paths, then commit (INV-ST-1/3, INV-GOV-1)."""

    def __init__(
        self,
        store: GitBackedDocStore,
        authority: Authority,
        governed_prefixes: set[str] | None = None,
    ) -> None:
        self._store = store
        self._authority = authority
        self._governed = governed_prefixes or set()

    def write(self, path: str, content: str, author: str, base_rev: str | None = None) -> dict:
        meta = parse(content)  # InvalidFrontmatter -> 422 at the gateway (INV-ST-3)
        if meta.get("kind") != "doc":
            raise WrongKind(meta.get("kind"))  # INV-ST: docs endpoint is doc-only
        if not self._authority.can_write(author, meta["space"]):
            raise Forbidden(author)
        if is_governed(path, self._governed):
            raise MRRequired(path)  # INV-GOV-1: governed paths require an MR
        # INV-ST-4: id is unique — reject if it already belongs to another path.
        existing = self._store.get(meta["id"])
        if existing is not None and existing.path != path:
            raise DuplicateId(meta["id"])
        # INV-ST-6: optimistic concurrency on updates to an existing path.
        current_rev = self._store.rev(path)
        if current_rev is not None and base_rev != current_rev:
            raise Conflict(path)
        self._store.write(path, content, author=author, message=f"write {path}")
        return {"id": meta["id"], "path": path, "space": meta["space"], "rev": self._store.rev(path)}
