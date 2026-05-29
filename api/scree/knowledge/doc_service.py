from pathlib import PurePosixPath

from scree.access.authority import Authority

from .frontmatter import parse  # InvalidFrontmatter propagates to the gateway (422)
from .git_store import GitBackedDocStore


class Forbidden(PermissionError):
    pass


class InvalidPath(ValueError):
    """A write path that escapes the Space (absolute or `..`), G2-01."""


class SpaceMismatch(PermissionError):
    """Frontmatter `space` does not match the Space this writer targets, G2-04."""


def is_safe_relpath(path: str) -> bool:
    """A path that stays inside the Space: relative, no `..`, non-empty (G2-01)."""
    if not path or path.endswith("/"):
        return False
    p = PurePosixPath(path)
    return not p.is_absolute() and ".." not in p.parts and "\x00" not in path


class MRRequired(PermissionError):
    """Direct write to a governed (MR-required) path is refused (INV-GOV-1)."""


class WrongKind(ValueError):
    """The docs endpoint only accepts kind: doc."""


class DuplicateId(ValueError):
    """An id is already used by another path (INV-ST-4 uniqueness)."""


class Conflict(ValueError):
    """Optimistic-concurrency mismatch — the base revision is stale (INV-ST-6)."""


class IdChanged(ValueError):
    """A write tried to change the id of the doc at an existing path (INV-ST-4:
    id is stable once assigned, even on move)."""


def is_governed(path: str, governed_prefixes: set[str]) -> bool:
    return any(path == p or path.startswith(p) for p in governed_prefixes)


class DocService:
    """Doc write path: validate frontmatter, enforce write authority and
    MR-required governed paths, then commit (INV-ST-1/3, INV-GOV-1)."""

    def __init__(
        self,
        store: GitBackedDocStore,
        authority: Authority,
        space: str | None = None,
        governed_prefixes: set[str] | None = None,
    ) -> None:
        self._store = store
        self._authority = authority
        self._space = space  # the Space (GitLab project) this store serves
        self._governed = governed_prefixes or set()

    def write(self, path: str, content: str, author: str, base_rev: str | None = None) -> dict:
        meta = parse(content)  # InvalidFrontmatter -> 422 at the gateway (INV-ST-3)
        if meta.get("kind") != "doc":
            raise WrongKind(meta.get("kind"))  # INV-ST: docs endpoint is doc-only
        # G2-04: the doc's declared Space must match the Space this store serves,
        # so write authority (checked below) governs where the file actually lands.
        if self._space is not None and meta["space"] != self._space:
            raise SpaceMismatch(meta["space"])
        if not is_safe_relpath(path):
            raise InvalidPath(path)  # G2-01: confine writes inside the Space
        if not self._authority.can_write(author, meta["space"]):
            raise Forbidden(author)
        if is_governed(path, self._governed):
            raise MRRequired(path)  # INV-GOV-1: governed paths require an MR
        # INV-ST-4: id is unique — reject if it already belongs to another path.
        existing = self._store.get(meta["id"])
        if existing is not None and existing.path != path:
            raise DuplicateId(meta["id"])
        current_rev = self._store.rev(path)
        if current_rev is not None:
            # INV-ST-4: the id is stable — a write to an existing path may not rename it.
            prior = next((d for d in self._store.all() if d.path == path), None)
            if prior is not None and prior.id != meta["id"]:
                raise IdChanged(path)
            # INV-ST-6: optimistic concurrency on updates to an existing path.
            if base_rev != current_rev:
                raise Conflict(path)
        self._store.write(path, content, author=author, message=f"write {path}")
        return {"id": meta["id"], "path": path, "space": meta["space"], "rev": self._store.rev(path)}
