"""@api — gate-11 fixes: encrypted tickets can't leak into the community KB
(G11-01); attachment upload is participant-only (G11-02); executable attachments
are rejected (G11-03)."""

from fastapi.testclient import TestClient

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore, TicketComment
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

CUST = "cust-okafor"


def _ctx(tickets=None, comments=None):
    store = TicketStore(tickets or [])
    cstore = CommentStore()
    for c in (comments or []):
        cstore.add(c)
    authority = TicketAuthority(FakeOpenFga(), agents={"agent:dani"})
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=authority, comment_store=cstore,
        allow_insecure_header_auth=True,
    )
    return TestClient(app), store


def test_encrypted_ticket_cannot_be_promoted_to_community():
    # G11-01: promotion of an encrypted ticket is refused (would decrypt into KB).
    client, _ = _ctx()
    tid = client.post("/tickets", json={"origin": "web", "encrypt": True, "body": "secret"},
                      headers={"X-Spike-User": CUST}).json()["id"]
    client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers={"X-Spike-User": "agent:dani"})
    resp = client.post(f"/tickets/{tid}/community-visible", headers={"X-Spike-User": "agent:dani"})
    assert resp.status_code == 409


def test_community_search_skips_encrypted_community_tickets():
    # Defense in depth: even a (hypothetical) encrypted+community ticket is excluded.
    enc = Ticket(id="t-enc", requester=CUST, status="resolved", community_visible=True, encrypted=True)
    plain = Ticket(id="t-plain", requester=CUST, status="resolved", community_visible=True,
                   community_snapshot=(("agent:dani", "reset secret token here", "api"),))
    client, _ = _ctx(
        tickets=[enc, plain],
        comments=[TicketComment(ticket_id="t-plain", author="agent:dani", body="reset secret token here")],
    )
    hits = {h["id"] for h in client.get("/community/search", params={"q": "secret"},
                                        headers={"X-Spike-User": "anyone"}).json()}
    assert hits == {"t-plain"}  # t-enc excluded, never decrypted


def test_attachment_upload_is_participant_only():
    # G11-02: a community reader who is NOT a participant cannot attach.
    pub = Ticket(id="t-pub", requester=CUST, status="resolved", community_visible=True)
    client, _ = _ctx(tickets=[pub])
    stranger = client.post("/tickets/t-pub/attachments", json={"filename": "x.png", "content": "d"},
                          headers={"X-Spike-User": "rando"})
    assert stranger.status_code == 404  # not a participant (leak-safe)
    owner = client.post("/tickets/t-pub/attachments", json={"filename": "x.png", "content": "d"},
                       headers={"X-Spike-User": CUST})
    assert owner.status_code == 200  # the requester may attach


def test_executable_attachment_rejected():
    pub = Ticket(id="t-pub", requester=CUST, status="open")
    client, _ = _ctx(tickets=[pub])
    resp = client.post("/tickets/t-pub/attachments", json={"filename": "payload.exe", "content": "MZ"},
                       headers={"X-Spike-User": CUST})
    assert resp.status_code == 415
