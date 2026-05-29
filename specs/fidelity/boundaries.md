# Phase 2 — Boundary fidelity

Each external system (GitLab, Keycloak/OIDC, OpenFGA, Vault, O365/Graph, Slack) is stubbed by a `Fake*`/`Static*` class in the fast tiers. A stub that diverges from the real API gives false green. The `@contract` tier (`api/tests/contract/`) boots the real service in a testcontainer to catch drift. Rating: FAITHFUL / PARTIAL / DIVERGENT.

> **The `@contract` tier is dormant in CI.** `.github/workflows/ci.yml:21` installs only `fastapi httpx pytest pytest-bdd pyyaml "pyjwt[crypto]"` and runs `pytest -q` with no marker selection — no `testcontainers`, so all 12 contract tests `pytest.importorskip`-skip at collection; `test_gitlab_rbac.py`/`test_vault_transit.py` are doubly gated on env vars. **0 of 12 contract tests execute in CI.** All FAITHFUL ratings below are conditional on someone running the tier locally with Docker.

## SEAM 1 — OpenFGA ReBAC · FAITHFUL
- Fake: `access/openfga.py:32` (`FakeOpenFga`, models `viewer = requester ∪ watcher ∪ assignee` at `:37`). Real: `:65` (`RealOpenFga`).
- @contract: `test_openfga_contract.py` (union model `:28–46`; **real `purge_user` pagination + ≤100 delete batching at n=120** `:143–162`) + `test_openfga_gateway.py` (e2e Gateway filtering `:106–117`).
- Residual: `FakeOpenFga` never raises (no HTTP error path), but the real error handling is contract-covered. Best-covered seam.

## SEAM 2 — GitLab membership · PARTIAL
- Fake: `access/gitlab.py:63` (`FakeGitLabAuthority`, plain dict lookup, never errors, ignores token validity). Real: `:17` (`GitLabAuthority`, `_paginate` follows `x-next-page` at `:34–50`).
- @contract: `test_gitlab_rbac.py` asserts **only `can_read`** (404-as-deny, member-grant flip `:62–76`). It does **not** exercise `readable_spaces`/`readable_groups` — the pagination loop that actually backs INV-AGG is never run against real GitLab. Doubly gated on `GITLAB_TEST_URL`/`GITLAB_TEST_TOKEN`.
- Residual: a `x-next-page` semantics bug would silently truncate a user's readable spaces → over- or under-exposure, undetected.

## SEAM 3 — OIDC auth · FAITHFUL
- Fake: none (Gateway uses plaintext `X-Spike-User` only when `authenticator=None` and explicitly opted-in). Real: `access/oidc.py:10` (`OidcAuthenticator`, `jwt.decode` verifies sig/iss/aud/exp at `:39–45`).
- @contract: `test_keycloak_oidc.py` against real Keycloak JWKS — principal=`sub` (`:136`), garbage rejected (`:142`), wrong-aud rejected (`:147`), Gateway ignores forged `X-Spike-User` with 401-on-no-bearer (`:157–173`).
- Residual: no exp-specific contract case, but `jwt` enforces exp and the unit tier covers it.

## SEAM 4 — Token exchange (RFC 8693) · DIVERGENT
- Fake: `token_exchange.py:19` (`StaticTokenExchanger`) — returns synthetic `downstream:{aud}:{token}` for **any** input (`:31`), never errors, never enforces client auth. Real: `:34` (`KeycloakTokenExchanger`, real `httpx.post` with `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`, `subject_token_type`, `client_secret`; 4xx→`AuthError` at `:63–67`).
- @contract: **NONE** — no `test_keycloak_token_exchange.py`. Only unit request-shape tests exist.
- Residual: **highest concern** — the one seam shipping real HTTP code with zero real-IdP validation. Keycloak's token-exchange is a feature-flagged/preview endpoint with a quirky response contract; drift (feature off, response shape, audience-client config) is fully undetectable.

## SEAM 5 — Vault Transit crypto · FAITHFUL
- Fake: `crypto/transit.py:24` (`FernetCrypto`, real AEAD). Real: `:53` (`VaultTransitCrypto`; transient-vs-permanent at `:85–87` — 4xx=shredded, 5xx=retryable).
- @contract: `test_vault_transit.py` — real encrypt/decrypt + `vault:` prefix (`:61–65`), crypto-shred (destroy → `DecryptionUnavailable` `:68–75`).
- Residual: the **5xx-retryable branch is not contract-tested** (the critical G8-02 half — needs fault injection). Code path is simple; covered by `test_crypto_hardening.py:71` against a static 503 client.

## SEAM 6 — O365 / Graph inbound email · DIVERGENT
- Stub: `integration/o365/inbound.py` is a **pure stdlib email parser**. Real: **does not exist** — no Microsoft Graph client/poller anywhere in `scree/`. The trusted DKIM/DMARC verdict + aligned sender are *assumed* supplied out-of-band and injected as `verified`/`sender` params (`service.py:102–110`).
- @contract: **NONE**.
- Residual: the trust verdict is the linchpin of INV-EMAIL-1 attribution. The downstream routing is well-tested, but the seam that *produces* the verdict is unmodeled and unverified — if Graph doesn't deliver a trustworthy aligned-sender signal, attribution is forgeable.

## SEAM 7 — Slack capture · DIVERGENT
- Stub: `integration/slack/capture.py` (`SlackDirectory` `:4` = in-mem id→principal map; `CaptureRateLimiter` `:16` = monotonic-clock limiter, single-replica only per G6-03). Real: **does not exist** — no Slack SDK, no webhook signature verification, no real event-payload parsing.
- @contract: **NONE**.
- Residual: lowest current risk (v1 single-channel feature, no real client yet). Future risk: webhook authenticity / signature verification is entirely unmodeled.

## Summary

| Seam | Rating | @contract |
|---|---|---|
| OpenFGA | FAITHFUL | yes (strong) |
| OIDC | FAITHFUL | yes |
| Vault Transit | FAITHFUL | yes (5xx branch missing) |
| GitLab membership | PARTIAL | `can_read` only |
| Token exchange | DIVERGENT | **none** |
| O365/Graph | DIVERGENT | **none** (no real twin) |
| Slack | DIVERGENT | **none** (no real twin) |

**Drift-undetectable seams:** token exchange (real code, no contract), O365/Graph, Slack, and GitLab `readable_spaces` pagination. **Ranked boundary risk:** (1) token exchange, (2) GitLab pagination (backs INV-AGG), (3) Graph DKIM/DMARC verdict (backs INV-EMAIL-1), (4) Vault 5xx branch, (5) Slack.
