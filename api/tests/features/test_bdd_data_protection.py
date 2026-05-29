"""@api BDD — canonical data_protection.feature (ADR-0006, INV-DP-*/ENC-*): born-
encrypted tickets, create-time-only encryption, opaque requester. The @contract
erasure/crypto-shred scenarios run in the testcontainers tier."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

scenarios("data_protection.feature")

AGENT = "agent:dani"
SECRET = "my secret API key is 12345"


@pytest.fixture
def world() -> dict:
    store = TicketStore()
    comments = CommentStore()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), {AGENT}),
        comment_store=comments, ticket_crypto=FernetCrypto(),
        allow_insecure_header_auth=True,
    )
    return {"store": store, "comments": comments, "client": TestClient(app), "ticket_id": None, "response": None}


@given(parsers.parse('"{cust}" submits a ticket with the encrypt option enabled'))
def submit_encrypted(world, cust):
    r = world["client"].post(
        "/tickets", json={"origin": "web", "encrypt": True, "body": SECRET}, headers={"X-Spike-User": cust}
    )
    world["ticket_id"] = r.json()["id"]


@given(parsers.parse('ticket "{ticket_id}" was created cleartext'))
def cleartext_ticket(world, ticket_id):
    world["store"].put(Ticket(id=ticket_id, requester="ext-cleartext", assignee=AGENT, encrypted=False))
    world["ticket_id"] = ticket_id


@given(parsers.parse('ticket "{ticket_id}" exists'))
def ticket_exists(world, ticket_id):
    world["store"].put(Ticket(id=ticket_id, requester="ext-7f3a2b9c"))
    world["ticket_id"] = ticket_id


@when("an agent attempts to encrypt it after the fact")
def attempt_encrypt(world):
    world["response"] = world["client"].post(
        f"/tickets/{world['ticket_id']}/encrypt", headers={"X-Spike-User": AGENT}
    )


@then("the ticket body is stored encrypted at rest")
@then("it is not readable from a raw repo clone")
def stored_encrypted(world):
    stored = world["comments"].for_ticket(world["ticket_id"])
    assert stored and stored[0].encrypted is True
    assert SECRET not in stored[0].body  # ciphertext at rest


@then("an agent opening it via the Gateway sees the decrypted body")
def agent_sees_plaintext(world):
    comments = world["client"].get(
        f"/tickets/{world['ticket_id']}/comments", headers={"X-Spike-User": AGENT}
    ).json()
    assert any(c["body"] == SECRET for c in comments)  # Gateway-mediated decryption


@then("the ticket is indexed by metadata only, not full-text")
def metadata_only(world):
    # The encrypted body never reaches a searchable surface (G11-01 / INV-ENC-3).
    hits = world["client"].get("/community/search", params={"q": "secret"}, headers={"X-Spike-User": AGENT}).json()
    assert world["ticket_id"] not in {h["id"] for h in hits}


@then("they are warned that the prior cleartext remains in Git history")
def warned(world):
    assert world["response"].status_code == 409
    assert "Git history" in world["response"].json()["detail"]


@then("the action does not retroactively protect existing history")
def not_retroactive(world):
    assert world["store"].get(world["ticket_id"]).encrypted is False


@then("its frontmatter `requester` is an opaque id")
@then("no customer name or email appears in the frontmatter")
def opaque_requester(world):
    requester = world["store"].get(world["ticket_id"]).requester
    assert "@" not in requester and requester.startswith("ext")  # opaque id, no PII (INV-DP-1)
