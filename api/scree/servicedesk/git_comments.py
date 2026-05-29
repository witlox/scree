"""Git-backed ticket-thread persistence (INV-ST-1/2). Comments are append-only
Markdown + YAML frontmatter at `tickets/<ticket_id>/comments/NNNN.md`, ordered by a
zero-padded sequence. Bodies are ciphertext at rest when the ticket is encrypted
(ADR-0005). Each append is a desk-SA commit with the author in an `On-Behalf-Of`
trailer (INV-ID-4)."""

import threading
from pathlib import Path

from .comments import TicketComment
from .git_store import commit_paths, dump_frontmatter, read_frontmatter


class GitBackedCommentStore:
    """Same interface as the in-memory CommentStore; shares the tickets repo with
    GitBackedTicketStore."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._write_lock = threading.Lock()

    def _dir(self, ticket_id: str) -> Path:
        return self._root / "tickets" / ticket_id / "comments"

    def for_ticket(self, ticket_id: str) -> list[TicketComment]:
        d = self._dir(ticket_id)
        if not d.is_dir():
            return []
        out: list[TicketComment] = []
        for md in sorted(d.glob("*.md")):  # zero-padded names sort chronologically
            try:
                meta, body = read_frontmatter(md.read_text())
                if meta.get("kind") != "comment":
                    continue
                out.append(TicketComment(
                    ticket_id=ticket_id, author=meta["author"], body=body,
                    source=meta.get("source", "api"), message_id=meta.get("message_id"),
                    encrypted=bool(meta.get("encrypted", False)),
                ))
            except (ValueError, KeyError, TypeError):
                continue
        return out

    def add(self, comment: TicketComment) -> None:
        with self._write_lock:
            d = self._dir(comment.ticket_id)
            d.mkdir(parents=True, exist_ok=True)
            seq = len(list(d.glob("*.md"))) + 1
            rel = f"tickets/{comment.ticket_id}/comments/{seq:04d}.md"
            fm: dict = {"kind": "comment", "schema_version": 1, "ticket_id": comment.ticket_id,
                        "author": comment.author, "source": comment.source, "encrypted": comment.encrypted}
            if comment.message_id is not None:
                fm["message_id"] = comment.message_id
            (self._root / rel).write_text(dump_frontmatter(fm, comment.body))
            commit_paths(self._root, [rel], message=f"comment on {comment.ticket_id}",
                         on_behalf_of=comment.author)
