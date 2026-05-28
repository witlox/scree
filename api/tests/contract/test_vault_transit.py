"""@contract — VaultTransitCrypto against a REAL Vault (Testcontainers, dev mode):
per-requester encrypt/decrypt round-trips, and `destroy` crypto-shreds so prior
ciphertext is permanently undecryptable (ADR-0008 / INV-DP-2). Skips when
Docker/testcontainers is unavailable so CI stays green."""

import time

import httpx
import pytest

pytest.importorskip("testcontainers.core.container")
from testcontainers.core.container import DockerContainer  # noqa: E402

from scree.crypto.transit import DecryptionUnavailable, VaultTransitCrypto  # noqa: E402

pytestmark = pytest.mark.contract

TOKEN = "root-token-test"


@pytest.fixture(scope="module")
def vault():
    container = None
    try:
        container = (
            DockerContainer("hashicorp/vault:1.15")
            .with_env("VAULT_DEV_ROOT_TOKEN_ID", TOKEN)
            .with_env("VAULT_DEV_LISTEN_ADDRESS", "0.0.0.0:8200")
            .with_exposed_ports(8200)
            .with_command("server -dev")
        )
        container.start()
        base = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8200)}"
        h = {"X-Vault-Token": TOKEN}
        deadline = time.time() + 60
        ready = False
        while time.time() < deadline:
            try:
                if httpx.get(f"{base}/v1/sys/health", timeout=2).status_code in (200, 429):
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            pytest.skip("Vault did not become healthy")
        httpx.post(f"{base}/v1/sys/mounts/transit", headers=h, json={"type": "transit"}, timeout=10)
    except Exception as exc:  # Docker/Vault unavailable or container won't start
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


def test_encrypt_decrypt_roundtrip_and_isolation(vault):
    crypto = VaultTransitCrypto(vault, TOKEN)
    ct = crypto.encrypt("ext-okafor", "the API key")
    assert ct != "the API key" and ct.startswith("vault:")
    assert crypto.decrypt("ext-okafor", ct) == "the API key"


def test_destroy_crypto_shreds_prior_ciphertext(vault):
    crypto = VaultTransitCrypto(vault, TOKEN)
    ct = crypto.encrypt("ext-lind", "sensitive")
    assert crypto.decrypt("ext-lind", ct) == "sensitive"

    crypto.destroy("ext-lind")  # GDPR crypto-shred
    with pytest.raises(DecryptionUnavailable):
        crypto.decrypt("ext-lind", ct)  # key gone → permanently unrecoverable
