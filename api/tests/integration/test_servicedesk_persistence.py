"""Service-desk persistence (#131): tickets/comments are Git-backed (INV-ST-1/2)
with an On-Behalf-Of commit trailer (INV-ID-4); the identity directory and
attachments are durable too. Replaces the in-memory-only service-desk stores so
restarts no longer drop tickets / customer identities / attachments."""

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import FileIdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.portal.stores import FileAttachmentStore
from scree.servicedesk.comments import TicketComment
from scree.servicedesk.git_comments import GitBackedCommentStore
from scree.servicedesk.git_store import GitBackedTicketStore
from scree.servicedesk.models import Ticket


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "tickets-repo"
    root.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@scree.test"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return root


def _commits(repo: Path) -> int:
    out = subprocess.run(["git", "-C", str(repo), "rev-list", "--count", "--all"],
                         capture_output=True, text=True).stdout.strip()
    return int(out or "0")


def _last_commit_body(repo: Path, path: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%B", "--", path],
                          capture_output=True, text=True).stdout


# --- GitBackedTicketStore (INV-ST-1/2, INV-ID-4) ---
def test_ticket_commits_and_rebuilds_from_git(repo):
    store = GitBackedTicketStore(repo)
    store.put(Ticket(id="ticket-1", requester="ext-7f3a2b", origin="web",
                     email_message_id="<m1@x>", email_token="SCREE-1"))
    assert _commits(repo) == 1  # INV-ST-1: the mutation is a commit

    fresh = GitBackedTicketStore(repo)  # INV-ST-2: a new instance reads it from Git alone
    t = fresh.get("ticket-1")
    assert t is not None and t.requester == "ext-7f3a2b" and t.origin == "web"
    assert fresh.by_message_id("<m1@x>").id == "ticket-1"
    assert fresh.by_token("SCREE-1").id == "ticket-1"


def test_ticket_commit_carries_on_behalf_of_trailer(repo):
    GitBackedTicketStore(repo).put(Ticket(id="ticket-2", requester="ext-okafor"))
    body = _last_commit_body(repo, "tickets/ticket-2.md")
    assert "On-Behalf-Of: ext-okafor" in body  # INV-ID-4: the human behind the desk-SA write


def test_no_pii_in_ticket_frontmatter(repo):
    GitBackedTicketStore(repo).put(Ticket(id="ticket-3", requester="ext-opaque"))
    raw = (repo / "tickets" / "ticket-3.md").read_text()
    assert "@" not in raw and "ext-opaque" in raw  # opaque id only (INV-DP-1)


# --- GitBackedCommentStore ---
def test_comments_persist_in_order_with_trailer(repo):
    store = GitBackedCommentStore(repo)
    store.add(TicketComment(ticket_id="ticket-9", author="ext-cust", body="first", source="web"))
    store.add(TicketComment(ticket_id="ticket-9", author="agent:dani", body="second", source="web"))
    assert _commits(repo) == 2

    fresh = GitBackedCommentStore(repo).for_ticket("ticket-9")
    assert [c.body for c in fresh] == ["first", "second"]  # order preserved
    assert [c.author for c in fresh] == ["ext-cust", "agent:dani"]
    assert "On-Behalf-Of: agent:dani" in _last_commit_body(repo, "tickets/ticket-9/comments/0002.md")


# --- FileIdentityDirectory (durable, off-Git, INV-DP-1/2) ---
def test_identity_directory_is_durable(tmp_path):
    path = tmp_path / "identity.json"
    d = FileIdentityDirectory(path)
    oid = d.resolve("R.Okafor@uni.example.ac")
    assert FileIdentityDirectory(path).email_for(oid) == "r.okafor@uni.example.ac"  # survives restart

    FileIdentityDirectory(path).erase(oid)
    assert FileIdentityDirectory(path).email_for(oid) is None  # erasure persisted (INV-DP-2)


# --- FileAttachmentStore (object storage, not Git) ---
def test_attachments_persist_to_object_storage(tmp_path):
    root = tmp_path / "objstore"
    store = FileAttachmentStore(root)
    att = store.put("ticket-5", "screenshot.png", b"PNGDATA")
    assert (root / att.object_key).read_bytes() == b"PNGDATA"  # bytes on the object store
    assert not (root / ".git").exists()  # NOT a Git repo

    fresh = FileAttachmentStore(root).for_ticket("ticket-5")
    assert [a.filename for a in fresh] == ["screenshot.png"]


def test_attachment_filename_is_path_safe(tmp_path):
    store = FileAttachmentStore(tmp_path / "obj")
    att = store.put("ticket-6", "../../etc/passwd", b"x")
    assert "/" not in att.object_key.split("/", 1)[1]  # traversal stripped to a bare name


# --- End-to-end: the Gateway persists tickets + replies, rebuildable, with trailers ---
def test_gateway_persists_ticket_and_reply(repo):
    tickets, comments = GitBackedTicketStore(repo), GitBackedCommentStore(repo)
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=tickets, ticket_authority=TicketAuthority(FakeOpenFga(), {"agent:dani"}),
        comment_store=comments, ticket_crypto=FernetCrypto(),
        attachment_store=FileAttachmentStore(repo.parent / "obj"),
        allow_insecure_header_auth=True,
    )
    client = TestClient(app)

    created = client.post("/tickets", json={"origin": "web", "body": "it broke"},
                          headers={"X-Spike-User": "ext-cust"})
    tid = created.json()["id"]
    client.post(f"/tickets/{tid}/comments", json={"body": "any update?"},
                headers={"X-Spike-User": "ext-cust"})

    # Rebuild from Git alone: a fresh process would see the ticket and its thread.
    assert GitBackedTicketStore(repo).get(tid) is not None
    bodies = [c.body for c in GitBackedCommentStore(repo).for_ticket(tid)]
    assert "it broke" in bodies and "any update?" in bodies
    assert "On-Behalf-Of: ext-cust" in _last_commit_body(repo, f"tickets/{tid}.md")
