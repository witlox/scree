# Scree — Error Taxonomy

Typed errors raised by domain/integration code, mapped to transport responses by
**one central handler** in the Gateway (not per-endpoint try/except). No secrets
or internal state in any message (INV-ID-3 / security).

## Categories

| Category | Meaning | HTTP | Recoverable? |
|---|---|---|---|
| `AuthnError` | missing/invalid/expired token | 401 | client re-auth |
| `AuthzError` | principal lacks authority | 403 (no resource detail) | no — deny is final |
| `NotFoundOrUnauthorized` | resource absent **or** unreadable (indistinguishable on purpose) | 404 | no — prevents existence leak (INV-AGG/INV-REF-5) |
| `ValidationError` | bad input / schema / illegal state transition | 422 | client fixes input |
| `ConflictError` | optimistic-concurrency / non-fast-forward | 409 | retry (INV-ST-6) |
| `GovernanceError` | direct write to an MR-required path | 409 | use an MR (INV-GOV-1) |
| `DependencyDegraded` | GitLab/O365/Slack/Vault/OpenFGA unavailable | 503 + Retry-After | retry; never silent-success (INV-DEG-*) |
| `RateLimited` | manual reindex / Slack capture over limit | 429 | back off (INV-IX-3, INV-SLACK-1) |
| `EncryptionError` | Transit/SOPS failure | 503 | retry; fail closed, never serve ciphertext as text |
| `InternalError` | unexpected | 500 (opaque) | fatal; logged with trace id |

## Rules

- **Fail closed on authority uncertainty** — `OpenFGA`/cache/Vault uncertainty maps
  to deny/omit, never allow (INV-ACC-5, INV-ENC).
- **`NotFoundOrUnauthorized` collapses "missing" and "forbidden"** so responses
  cannot be used to probe existence of unreadable resources.
- Every error carries a correlation/trace id (OTel) for support without leaking
  internals.
- Degraded-dependency errors are explicit (503) — the client/user always learns
  the operation did **not** succeed (no queued-as-success, INV-DEG-1).
