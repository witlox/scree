import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import yaml

from scree.knowledge.frontmatter import InvalidFrontmatter, parse
from scree.knowledge.git_store import GitWriteError

from .models import Risk


class GitBackedRiskStore:
    """Risks persisted as markdown + YAML frontmatter in a Git working tree (DD-004),
    same interface as the in-memory RiskStore so the Gateway is unchanged. INV-ST-1:
    every risk mutation is a commit. INV-ST-2: the store is rebuildable from Git.
    `score`/`severity` are DERIVED (F-12/F-13) and never written to frontmatter."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._write_lock = threading.Lock()  # serialize commits (G2-11)

    def _iter(self) -> Iterator[Risk]:
        for md_path in sorted(self._root.rglob("*.md")):
            try:
                meta = parse(md_path.read_text())
            except InvalidFrontmatter:
                continue  # quarantine unparseable files; never surface them
            if meta.get("kind") != "risk":
                continue
            try:
                yield Risk(
                    id=meta["id"],
                    title=meta["title"],
                    space=meta["space"],
                    category=meta["category"],
                    likelihood=int(meta["likelihood"]),
                    impact=int(meta["impact"]),
                    strategy=meta["strategy"],
                    status=meta.get("status", "open"),
                    owner=meta.get("owner"),
                    escalated_from=meta.get("escalated_from"),
                )
            except (KeyError, ValueError, TypeError):
                continue  # malformed risk frontmatter is quarantined, not surfaced

    def get(self, risk_id: str) -> Risk | None:
        return next((r for r in self._iter() if r.id == risk_id), None)

    def all(self) -> list[Risk]:
        return list(self._iter())

    def put(self, risk: Risk) -> None:
        """Write the risk file and commit it (INV-ST-1)."""
        fm: dict = {
            "id": risk.id,
            "kind": "risk",
            "schema_version": 1,
            "title": risk.title,
            "space": risk.space,
            "category": risk.category,
            "likelihood": risk.likelihood,
            "impact": risk.impact,
            "strategy": risk.strategy,
            "status": risk.status,
        }
        if risk.owner is not None:
            fm["owner"] = risk.owner
        if risk.escalated_from is not None:
            fm["escalated_from"] = risk.escalated_from
        content = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n"
        rel = f"risks/{risk.id}.md"
        with self._write_lock:
            try:
                target = self._root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
                subprocess.run(
                    ["git", "-C", str(self._root), "add", "--", rel],
                    check=True, capture_output=True,
                )
                if subprocess.run(
                    ["git", "-C", str(self._root), "diff", "--cached", "--quiet", "--", rel]
                ).returncode == 0:
                    return  # no change → no empty commit
                author = risk.owner or "scree"
                subprocess.run(
                    ["git", "-C", str(self._root), "-c", f"user.name={author}",
                     "-c", "user.email=risk@scree", "commit", "-m", f"risk {risk.id}"],
                    check=True, capture_output=True,
                )
            except subprocess.CalledProcessError as exc:
                raise GitWriteError(exc.stderr.decode(errors="replace") if exc.stderr else str(exc)) from exc
