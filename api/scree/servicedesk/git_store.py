"""Git-backed ticket persistence (INV-ST-1/2), same interface as the in-memory
TicketStore so the Gateway is unchanged. Tickets are Markdown + YAML frontmatter at
`tickets/<id>.md`; the requester is an opaque id, so no PII enters Git (INV-DP-1).
Every mutation is a commit authored by the desk service account, with the human's
identity in an `On-Behalf-Of` trailer (INV-ID-4)."""

import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import yaml

from scree.knowledge.git_store import GitWriteError

from .models import Ticket

DESK_SA = "scree-desk"


def read_frontmatter(text: str) -> tuple[dict, str]:
    """Split `---\\nYAML\\n---\\nbody` into (meta, body). These files are written by
    us (not external input), so a plain SafeLoad is sufficient."""
    if not text.startswith("---"):
        raise ValueError("missing frontmatter")
    _, raw_meta, body = text.split("---", 2)
    meta = yaml.safe_load(raw_meta) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be a mapping")
    return meta, body.strip("\n")  # round-trips a single-line body without gaining a newline


def dump_frontmatter(meta: dict, body: str = "") -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\n" + (body and body + "\n")


def commit_paths(root: Path, rel_paths: list[str], *, message: str, on_behalf_of: str | None) -> None:
    """Stage paths and commit as the desk SA, recording the human in a trailer
    (INV-ID-4). No-op (no commit) when nothing changed. Shared by the ticket and
    comment stores."""
    subprocess.run(["git", "-C", str(root), "add", "--", *rel_paths], check=True, capture_output=True)
    if subprocess.run(["git", "-C", str(root), "diff", "--cached", "--quiet"]).returncode == 0:
        return
    args = ["git", "-C", str(root), "-c", f"user.name={DESK_SA}", "-c", f"user.email={DESK_SA}@scree",
            "commit", "-m", message]
    if on_behalf_of:
        args += ["-m", f"On-Behalf-Of: {on_behalf_of}"]  # the human behind the desk-SA write
    try:
        subprocess.run(args, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise GitWriteError(exc.stderr.decode(errors="replace") if exc.stderr else str(exc)) from exc


class GitBackedTicketStore:
    """Tickets persisted to a Git working tree; rebuildable from Git (INV-ST-2)."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._dir = self._root / "tickets"
        self._write_lock = threading.Lock()  # serialize commits on this repo (G2-11)

    def _iter(self) -> Iterator[Ticket]:
        if not self._dir.is_dir():
            return
        for md in sorted(self._dir.glob("*.md")):  # top-level only; comments live in tickets/<id>/
            try:
                meta, _ = read_frontmatter(md.read_text())
                if meta.get("kind") != "ticket":
                    continue
                snap = meta.get("community_snapshot")
                yield Ticket(
                    id=meta["id"], requester=meta["requester"],
                    space=meta.get("space", "support/service-desk"),
                    status=meta.get("status", "open"), assignee=meta.get("assignee"),
                    community_visible=bool(meta.get("community_visible", False)),
                    origin=meta.get("origin", "api"), email_token=meta.get("email_token"),
                    email_message_id=meta.get("email_message_id"), captured_by=meta.get("captured_by"),
                    created_at=meta.get("created_at"), encrypted=bool(meta.get("encrypted", False)),
                    community_snapshot=tuple(tuple(c) for c in snap) if snap else None,
                )
            except (ValueError, KeyError, TypeError):
                continue  # quarantine malformed ticket files; never surface them

    def get(self, ticket_id: str) -> Ticket | None:
        return next((t for t in self._iter() if t.id == ticket_id), None)

    def all(self) -> list[Ticket]:
        return list(self._iter())

    def by_message_id(self, message_id: str) -> Ticket | None:
        return next((t for t in self._iter() if t.email_message_id == message_id), None)

    def by_token(self, token: str) -> Ticket | None:
        return next((t for t in self._iter() if t.email_token == token), None)

    def put(self, ticket: Ticket) -> None:
        fm: dict = {
            "id": ticket.id, "kind": "ticket", "schema_version": 1, "requester": ticket.requester,
            "space": ticket.space, "status": ticket.status, "origin": ticket.origin,
            "community_visible": ticket.community_visible, "encrypted": ticket.encrypted,
        }
        for key in ("assignee", "email_token", "email_message_id", "captured_by", "created_at"):
            value = getattr(ticket, key)
            if value is not None:
                fm[key] = value
        if ticket.community_snapshot is not None:
            fm["community_snapshot"] = [list(c) for c in ticket.community_snapshot]
        rel = f"tickets/{ticket.id}.md"
        with self._write_lock:
            target = self._root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(dump_frontmatter(fm))
            commit_paths(self._root, [rel], message=f"ticket {ticket.id}", on_behalf_of=ticket.requester)
