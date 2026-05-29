"""@api — G-A11 / INV-ENC-3: encrypted ticket bodies are not full-text indexed into the
public KB. An encrypted ticket cannot be promoted, its body is ciphertext at rest, and
its content never appears in community search even when the query matches the plaintext."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.store import TicketStore

AGENT = "agent:dani"
NEEDLE = "confidential-incident-detail"


def _ctx():
    store = TicketStore()
    comments = CommentStore()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), agents={AGENT}),
        comment_store=comments, identity_directory=IdentityDirectory(),
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store, comments


def test_encrypted_ticket_body_never_enters_public_kb_index():
    client, store, comments = _ctx()
    t = client.post("/tickets", json={"origin": "web", "encrypt": True, "body": NEEDLE},
                    headers={"X-Spike-User": "cust"}).json()

    # Ciphertext at rest — the plaintext is not stored (so it cannot be indexed).
    assert store.get(t["id"]).encrypted is True
    assert NEEDLE not in comments.for_ticket(t["id"])[0].body

    # An encrypted ticket cannot be promoted (G11-01), so it is never community_visible.
    client.patch(f"/tickets/{t['id']}", json={"status": "resolved"}, headers={"X-Spike-User": AGENT})
    assert client.post(f"/tickets/{t['id']}/community-visible",
                       headers={"X-Spike-User": AGENT}).status_code == 409

    # Community search never surfaces it, even though the plaintext matches.
    assert client.get("/community/search", params={"q": NEEDLE},
                      headers={"X-Spike-User": "cust-stranger"}).json() == []
