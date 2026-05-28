# Implementation Gate 8 — Adversary Findings

Adversarial pass over the encryption-at-create / crypto-shred slice merged in PR
#64 (`crypto/transit.py`, `servicedesk/service.py` comment crypto, Gateway
`/tickets` encrypt + `/tickets/{id}/comments` + `/tickets/{id}/encrypt`,
`ErasureService` crypto-shred). Primary target: durability/correctness of the
encryption boundary and the shred guarantee.

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G8-01: Ephemeral in-memory crypto is the default → silent unrecoverability without Vault
- **Severity:** Medium
- **Category:** Robustness > durability / default-fragile (cf. G2-03)
- **Location:** Gateway `create_app` (`crypto = ticket_crypto or FernetCrypto()`)
- **Spec reference:** ADR-0005/0008 (Vault Transit is the per-requester key store); INV-DP-2
- **Description:** When no `ticket_crypto` is supplied, the Gateway defaults to
  `FernetCrypto`, whose per-requester keys live **in process memory**. Encryption
  then "works" but the keys are lost on restart and not shared across replicas, so
  **every encrypted ticket becomes permanently undecryptable after a restart** (and
  is unreadable on any other replica) — accidental data loss masquerading as a
  working feature. A deployment that forgets to wire Vault is silently broken, the
  same fail-open-by-omission shape as G2-03 (auth default-off).
- **Evidence:** `create_app(...)` without `ticket_crypto`; create an encrypted
  ticket; restart the process → its body is unrecoverable though it was never erased.
- **Suggested resolution:** Fail closed — require a durable `ticket_crypto` in
  production; only fall back to `FernetCrypto` under the explicit dev/spike flag
  (`allow_insecure_header_auth`), mirroring the auth posture.

## Finding G8-02: Decryption conflates transient backend failure with permanent crypto-shred
- **Severity:** Medium
- **Category:** Correctness > error handling / data-integrity signalling
- **Location:** `api/scree/crypto/transit.py:VaultTransitCrypto.decrypt` (`if resp.status_code >= 400: raise DecryptionUnavailable`); `servicedesk/service.py:read_comments`
- **Spec reference:** INV-DP-2 (erasure is permanent and intentional); failure-modes
- **Description:** `VaultTransitCrypto.decrypt` raises `DecryptionUnavailable` on
  **any** `>= 400`, and `read_comments` turns that into the marker "[unrecoverable:
  encryption key erased]". A **transient** Vault outage (5xx, network blip) is a
  recoverable condition, but it is reported as a permanent erasure — so during a
  Vault hiccup an agent is told the customer's data is gone forever, and may act on
  that. Permanent shred (key missing → 400/404) must be distinguished from transient
  unavailability (5xx) which should surface as a retryable error, not a false
  "erased."
- **Evidence:** point the client at a Vault returning 503 → existing comments show
  the "key erased" marker though nothing was erased.
- **Suggested resolution:** Treat key-not-found/invalid-ciphertext (4xx) as
  `DecryptionUnavailable` (shredded); let 5xx/transport errors propagate as a
  retryable failure (502/503), never the permanent-erasure marker.

## Finding G8-03: Comment / ticket body size is unbounded
- **Severity:** Low
- **Category:** Robustness > resource exhaustion
- **Location:** Gateway `create_ticket` (`body`), `/slack/*` (`snapshot`); `_store_comment`
- **Spec reference:** failure-modes (bound external input); cf. G2-07 (doc cap), G4-06 (email cap)
- **Description:** The doc-write (G2-07) and inbound-email (G4-06) paths are size-
  capped, but the ticket `body` and Slack `snapshot` that become comments have no
  bound. A very large body is stored (and, when encrypted, pushed through the crypto
  backend, which has its own payload limits) — an unbounded memory/cost sink.
- **Evidence:** `POST /tickets {"body": "<50MB>"}` is accepted and stored.
- **Suggested resolution:** Cap comment/body size at the boundary (→413), consistent
  with the doc and email caps.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G8-01 | Medium | Robustness/durability | Ephemeral in-memory crypto is the default → silent unrecoverability without Vault |
| G8-02 | Medium | Correctness | Decryption conflates transient failure with permanent crypto-shred |
| G8-03 | Low | Robustness/exhaustion | Comment/ticket body size unbounded |

**Counts:** 0 critical · 0 high · 2 medium · 1 low — **3 total.** No `gate:blocking`.

**Highest-risk area:** durability/correctness of the crypto boundary — the default
loses keys on restart (G8-01) and a transient outage is mis-reported as permanent
erasure (G8-02).

**Resolution (2026-05-28) — all 3 resolved (PR #65):**
- G8-01 — `create_app` requires a durable `ticket_crypto`; `FernetCrypto` is only
  allowed under the `allow_insecure_header_auth` dev/spike flag (fail-closed).
- G8-02 — `VaultTransitCrypto.decrypt` treats 4xx as `DecryptionUnavailable`
  (shredded/invalid) and lets 5xx/transport errors propagate as retryable.
- G8-03 — ticket `body` and Slack `snapshot` capped at 1MB (→413).
