# Scree — API Contracts (Gateway)

The Gateway is API-first and the single enforcement point (DD-006). Every surface
(web, CLI, Slack adapter, email adapter) calls this API. The OpenAPI spec is
**generated from the `schemas/` Pydantic models** — this file is the architectural
outline the generated spec must satisfy, not a hand-maintained duplicate.

## Conventions

- **Auth:** every request carries a Keycloak OIDC bearer token. The Gateway
  resolves the principal once and injects it (INV-ACC-1). 401 on invalid/expired.
- **Authorization:** enforced per request by `access` (GitLab authority ∪ OpenFGA
  relations). 403 with no resource detail when denied (no existence leak).
- **Errors:** uniform problem responses from one central handler (see
  `error-taxonomy.md`); never leak internal state or secrets.
- **Idempotency:** unsafe writes accept an idempotency key; the Gateway does
  read-modify-write with optimistic concurrency (INV-ST-6).
- **Audit:** every call recorded to the append-only sink (INV-ID-3).
- **Pagination:** cursor-based for list/aggregation endpoints.

## Endpoint groups

| Group | Representative operations | Notes |
|---|---|---|
| **Resources** | `GET/POST/PATCH /docs`, `/risks` | repo-scoped authority; MR-required paths reject direct write (INV-GOV-1) |
| **Tickets** | `POST /tickets` (origin, optional `encrypt`), `GET /tickets/{id}`, `PATCH` (state transition), `POST /tickets/{id}/replies`, `POST /tickets/{id}/watchers`, `POST /tickets/{id}/community-visible` | ReBAC via OpenFGA; `encrypt` is create-time (INV-DP-3); state transitions validated (INV-LC-1) |
| **Aggregation / search** | `GET /search`, `GET /risk-register`, `GET /portfolio` | **per-item filtered** (INV-AGG) via OpenFGA `ListObjects` + GitLab authority; results carry `as-of` staleness marker |
| **Attachments** | `POST /tickets/{id}/attachments` | object storage, not Git (DD-002) |
| **Identity / DSAR** | `GET/PATCH /me`, `POST /admin/erasure/{requester}` | identity directory (INV-DP-1); erasure = anonymize + crypto-shred (INV-DP-2) |
| **Indexing** | `POST /reindex` (manual, rate-limited), webhook receiver | INV-IX-2/3; webhook verifies signature, re-reads from Git (no payload trust) |
| **Admin** | orphan report, audit query | orphaned-actives (INV-ORPH); audit reads are themselves audited |

## Cross-cutting contracts

- **Aggregation endpoints never trust the index for authority** — they filter every
  returned item by the requester's authority at query time (INV-AGG).
- **Write endpoints** commit to Git first; index update is a derived follow-on
  (INV-ST-1, cross-context dual-write note).
- **Encrypted-ticket reads** stream plaintext only to authorized principals
  (Gateway decrypts via Vault Transit); the raw repo is ciphertext.

The concrete OpenAPI document lives at build time (generated); the TS client is
generated from it (no hand-written types — ADR-0003).
