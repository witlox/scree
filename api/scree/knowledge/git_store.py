import subprocess
from pathlib import Path
from collections.abc import Iterator

from .frontmatter import InvalidFrontmatter, parse
from .models import Doc


class GitBackedDocStore:
    """Reads docs as markdown + YAML frontmatter from a Git working tree
    (DD-002). Same interface as the in-memory DocStore, so the Gateway is
    unchanged. created/updated are derived from Git history (INV-ST-5)."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

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
                created=created,
                updated=updated,
                path=str(md_path.relative_to(self._root)),  # folder path = hierarchy
            )

    def write(self, rel_path: str, text: str, *, author: str, message: str) -> None:
        """Write a doc file and commit it (INV-ST-1: every mutation is a commit)."""
        target = self._root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        subprocess.run(["git", "-C", str(self._root), "add", rel_path], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self._root), "-c", f"user.name={author}",
             "-c", f"user.email={author}@scree", "commit", "-m", message],
            check=True, capture_output=True,
        )

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
