import subprocess
import threading
from pathlib import Path
from collections.abc import Iterator

from .frontmatter import InvalidFrontmatter, parse
from .models import Doc


class GitWriteError(RuntimeError):
    """A Git write failed (e.g. index.lock contention) — retryable (G2-11)."""


class GitBackedDocStore:
    """Reads docs as markdown + YAML frontmatter from a Git working tree
    (DD-002). Same interface as the in-memory DocStore, so the Gateway is
    unchanged. created/updated are derived from Git history (INV-ST-5)."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        # G2-11: serialize writes to this repo so concurrent commits don't race
        # on Git's index.lock. (Single-process spike; multi-process needs a file lock.)
        self._write_lock = threading.Lock()

    def _iter_docs(self) -> Iterator[Doc]:
        for md_path in sorted(self._root.rglob("*.md")):
            try:
                meta = parse(md_path.read_text())
            except InvalidFrontmatter:
                continue  # quarantine invalid files; never index them
            created, updated = self._git_times(md_path)
            yield Doc(
                id=meta["id"],
                title=meta["title"],
                space=meta["space"],
                body=meta["body"],
                schema_version=meta["schema_version"],
                created=created,
                updated=updated,
                path=str(md_path.relative_to(self._root)),  # folder path = hierarchy
            )

    def write(self, rel_path: str, text: str, *, author: str, message: str) -> None:
        """Write a doc file and commit it (INV-ST-1: every mutation is a commit).
        Serialized per repo (G2-11). Callers must pass a confined relative path
        (DocService.is_safe_relpath); this is a safety net, not the boundary."""
        with self._write_lock:
            try:
                target = self._root / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
                subprocess.run(
                    ["git", "-C", str(self._root), "add", "--", rel_path],
                    check=True, capture_output=True,
                )
                # Skip the commit if content is unchanged (no-op save must not crash).
                if subprocess.run(
                    ["git", "-C", str(self._root), "diff", "--cached", "--quiet", "--", rel_path]
                ).returncode == 0:
                    return
                subprocess.run(
                    ["git", "-C", str(self._root), "-c", f"user.name={author}",
                     "-c", f"user.email={author}@scree", "commit", "-m", message],
                    check=True, capture_output=True,
                )
            except subprocess.CalledProcessError as exc:
                raise GitWriteError(exc.stderr.decode(errors="replace") if exc.stderr else str(exc)) from exc

    def rev(self, rel_path: str) -> str | None:
        """Current revision (last commit sha) for a path, or None if untracked.
        Used for optimistic concurrency (INV-ST-6)."""
        out = subprocess.run(
            ["git", "-C", str(self._root), "log", "-1", "--format=%H", "--", rel_path],
            capture_output=True, text=True,
        ).stdout.strip()
        return out or None

    def history(self, rel_path: str) -> list[dict]:
        """Version history for a path from Git (INV-ST-5: versions are commits, not
        independently authored state). Newest first."""
        out = subprocess.run(
            ["git", "-C", str(self._root), "log",
             "--format=%H%x1f%an%x1f%aI%x1f%s", "--", rel_path],
            capture_output=True, text=True,
        ).stdout.strip()
        versions: list[dict] = []
        for line in out.splitlines():
            sha, author, date, message = line.split("\x1f")
            versions.append({"rev": sha, "author": author, "date": date, "message": message})
        return versions

    def get(self, doc_id: str) -> Doc | None:
        return next((d for d in self._iter_docs() if d.id == doc_id), None)

    def all(self) -> list[Doc]:
        return list(self._iter_docs())

    def attachments(self, doc_id: str) -> list[str]:
        """Per-folder uploads: files colocated with the doc in its folder
        (DD-002: internal attachments live in the doc's folder in Git)."""
        doc = self.get(doc_id)
        if doc is None or doc.path is None:
            return []
        folder = (self._root / doc.path).parent
        return sorted(
            str(p.relative_to(self._root))
            for p in folder.iterdir()
            if p.is_file() and p.suffix != ".md"  # uploads only, not docs
        )

    def _git_times(self, path: Path) -> tuple[str | None, str | None]:
        try:
            out = subprocess.run(
                ["git", "-C", str(self._root), "log", "--format=%aI", "--", str(path)],
                capture_output=True, text=True, check=True,
            ).stdout.split()
        except Exception:
            return (None, None)
        if not out:
            return (None, None)
        return (out[-1], out[0])  # created = first commit, updated = latest
