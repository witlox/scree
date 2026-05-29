"""@api BDD — canonical data_protection.feature (ADR-0006, INV-DP-*/ENC-*): born-
encrypted tickets, create-time-only encryption, opaque requester. The @contract
erasure/crypto-shred scenarios run in the testcontainers tier."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.access.identity import IdentityDirectory
from scree.access.openfga import FakeOpenFga
from scree.access.ticket_authority import TicketAuthority
from scree.crypto.transit import FernetCrypto, VaultTransitCrypto
from scree.gateway.app import create_app
from scree.knowledge.store import DocStore
from scree.servicedesk.comments import CommentStore
from scree.servicedesk.models import Ticket
from scree.servicedesk.store import TicketStore

scenarios("data_protection.feature")

AGENT = "agent:dani"
DPO = "dpo:alice"
SECRET = "my secret API key is 12345"
VAULT_TOKEN = "root-token-test"


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


# --- @contract: GDPR erasure + crypto-shred against a REAL Vault (testcontainers) ---
@pytest.fixture(scope="module")
def vault_base():
    import time

    import httpx

    pytest.importorskip("testcontainers.core.container")
    from testcontainers.core.container import DockerContainer

    container = None
    try:
        container = (
            DockerContainer("hashicorp/vault:1.15")
            .with_env("VAULT_DEV_ROOT_TOKEN_ID", VAULT_TOKEN)
            .with_env("VAULT_DEV_LISTEN_ADDRESS", "0.0.0.0:8200")
            .with_exposed_ports(8200)
            .with_command("server -dev")
        )
        container.start()
        base = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8200)}"
        h = {"X-Vault-Token": VAULT_TOKEN}
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                if httpx.get(f"{base}/v1/sys/health", timeout=2).status_code in (200, 429):
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            pytest.skip("Vault did not become healthy")
        httpx.post(f"{base}/v1/sys/mounts/transit", headers=h, json={"type": "transit"}, timeout=10)
    except Exception as exc:
        if container is not None:
            try:
                container.stop()
            except Exception:
                pass
        pytest.skip(f"Docker/Vault unavailable: {exc}")
    try:
        yield base
    finally:
        container.stop()


@pytest.fixture
def vworld(vault_base) -> dict:
    store = TicketStore()
    identity = IdentityDirectory()
    app = create_app(
        DocStore([]), Authority({}),
        ticket_store=store, ticket_authority=TicketAuthority(FakeOpenFga(), {AGENT}),
        comment_store=CommentStore(), ticket_crypto=VaultTransitCrypto(vault_base, VAULT_TOKEN),
        identity_directory=identity, compliance_principals={DPO},
        allow_insecure_header_auth=True,
    )
    return {"store": store, "identity": identity, "client": TestClient(app), "oid": None, "erase": None}


@given(parsers.parse('customer "{cust}" owns ticket "{ticket_id}"'))
def owns_ticket(vworld, cust, ticket_id):
    oid = vworld["identity"].resolve(cust)
    vworld["store"].put(Ticket(id=ticket_id, requester=oid))
    vworld["oid"], vworld["plain_ticket"] = oid, ticket_id


@given(parsers.parse('customer "{cust}" owns encrypted ticket "{ticket_id}"'))
def owns_encrypted_ticket(vworld, cust, ticket_id):
    oid = vworld["identity"].resolve(cust)
    created = vworld["client"].post(
        "/tickets", json={"origin": "web", "encrypt": True, "body": SECRET}, headers={"X-Spike-User": oid}
    )
    vworld["oid"], vworld["enc_ticket"] = oid, created.json()["id"]


@when(parsers.parse('a GDPR erasure request for "{cust}" is fulfilled'))
def erasure_fulfilled(vworld, cust):
    vworld["erase"] = vworld["client"].delete(f"/identities/{vworld['oid']}", headers={"X-Spike-User": DPO})


@then(parsers.parse('the identity-directory record for "{cust}" is deleted'))
def identity_deleted(vworld, cust):
    assert vworld["identity"].email_for(vworld["oid"]) is None


@then(parsers.parse('"{ticket_id}" remains but its requester id is unresolvable'))
def ticket_remains_unresolvable(vworld, ticket_id):
    t = vworld["store"].get(ticket_id)
    assert t is not None  # Git not rewritten — the ticket stays
    assert vworld["identity"].email_for(t.requester) is None  # but the opaque id no longer resolves


@then("Git history is not rewritten")
def git_not_rewritten(vworld):
    assert "Git" in vworld["erase"].json()["residual"]


@then("the per-requester key is destroyed")
def key_destroyed(vworld):
    assert vworld["erase"].json()["crypto_shredded"] is True


@then(parsers.parse('the encrypted body of "{ticket_id}" is permanently unrecoverable'))
def body_unrecoverable(vworld, ticket_id):
    comments = vworld["client"].get(
        f"/tickets/{vworld['enc_ticket']}/comments", headers={"X-Spike-User": AGENT}
    ).json()
    assert any("unrecoverable" in c["body"] for c in comments)  # key gone → crypto-shred
