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
        for path in sorted(self._root.rglob("*.md")):
            try:
                meta = parse(path.read_text())
            except InvalidFrontmatter:
                continue  # quarantine invalid files; never index them
            created, updated = self._git_times(path)
            yield Doc(
                id=meta["id"],
                title=meta["title"],
                space=meta["space"],
                body=meta["body"],
                created=created,
                updated=updated,
            )

    def get(self, doc_id: str) -> Doc | None:
        return next((d for d in self._iter_docs() if d.id == doc_id), None)

    def all(self) -> list[Doc]:
        return list(self._iter_docs())

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
