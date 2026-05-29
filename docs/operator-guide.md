# Operator Guide

This is the surface for whoever deploys and runs Scree. Scree ships as **one
container image** (`ghcr.io/witlox/scree`): the FastAPI gateway serves the API at
`/api` and the built web app at `/`.

## First run (demo / dev)

The dev profile uses header auth and in-memory stores — no external services:

```bash
docker compose up        # → http://localhost:8000
```

That is `SCREE_DEV=1`. It is for demos and local development only: it trusts an
`X-Spike-User` header and keeps everything in memory. **Never run it in
production.**

## Production deploy

Leave `SCREE_DEV` unset and supply real configuration. Two options:

- **Compose** — copy [`.env.example`](https://github.com/witlox/scree/blob/main/.env.example)
  to `.env`, fill it in, and point the `scree` service at it.
- **Helm** — `charts/scree` deploys the one image. Put non-secret config in
  `values.yaml` (`config:`), and the secrets (`OIDC_CLIENT_SECRET`, `VAULT_TOKEN`)
  in a pre-created Secret referenced by `existingSecret`. Set `dev: false`.

```bash
helm install scree charts/scree \
  --set dev=false --set existingSecret=scree-secrets \
  --set config.OIDC_ISSUER=https://keycloak.example/realms/scree \
  --set config.GITLAB_URL=https://gitlab.example \
  --set config.VAULT_ADDR=https://vault.example \
  --set config.OPENFGA_URL=http://openfga:8080
```

**Fail-closed.** In production the gateway refuses to start if a required value is
missing (it raises at startup rather than degrading silently). Required: the
`OIDC_*` set (Keycloak), `GITLAB_URL`, `VAULT_ADDR`+`VAULT_TOKEN`, and the
`OPENFGA_*` set. See `.env.example` for the annotated list.

## What Scree talks to

| Dependency | Role | Required |
|---|---|---|
| **Keycloak** | identity; OIDC bearer + RFC 8693 token exchange to act as the user against GitLab | yes |
| **GitLab Ultimate** | the substrate — repos (Spaces), membership, planning objects | yes |
| **Vault** (Transit) | per-requester encryption of sensitive tickets; crypto-shred on erasure | yes |
| **OpenFGA** | ticket ReBAC (who-can-see-which-ticket) | yes |
| **O365 / Graph** | inbound email intake (a separate poller posts verified mail to the gateway) | for email |
| **Slack** | one public community channel; `:ticket:` capture | for Slack |
| **Object storage** | external ticket attachments (not Git) | for attachments |

## Data & backups

Scree's primary data is **Markdown + YAML in Git**, so backups are mostly "back up
the repos":

- **Knowledge** lives in the repo at `SCREE_DOCS_REPO` (a Git working clone).
- **Risks** live in the repo at `SCREE_RISKS_REPO`.
- Back up those repositories (or rely on GitLab's own backups of the upstream
  projects they clone). The on-disk index is **derived and rebuildable** from Git;
  you never back it up.
- The **audit log** is hash-chained and tamper-evident; for production, write the
  chain to WORM / append-only storage with retention (the integrity mechanism is
  in the app, the durable medium is your deployment choice).

> **Current limitation (being addressed).** Service-desk records — **tickets,
> comments, the customer identity directory** — and **attachments** are presently
> held **in memory** and do **not** survive a restart. Knowledge and risk are
> Git-backed and durable; the service-desk side is not yet. Treat the service-desk
> deployment as ephemeral until the durable stores (Git-backed tickets/comments,
> durable identity directory, object-storage attachments) land. Do not run
> external customer support on this build in production.

## Migration (big-bang cutover)

The Atlassian migration is a one-shot batch, driven by a **service principal** via
`POST /migration/run`:

- **Marked** items migrate: Jira issues → tickets, Confluence pages → docs, with a
  stable old→new ID mapping so existing references resolve (no broken links).
- **Unmarked** items (not curated by the deadline) go to a read-only archive — not
  migrated.
- The pipeline is **idempotent**: re-running creates no duplicates and leaves the
  mapping unchanged, so a failed run is safe to repeat.

Run it once against staging, validate, then cut over.

## Graceful degradation

- **GitLab unreachable** → authorized **reads** still serve from the local clone
  (bounded by a last-known-membership window), and **writes are refused with a
  clear 503** — never silently dropped. Permissions still hold on the local clone.
- **O365 unreachable** → inbound email creation fails visibly (503), not silently.

These are intentional: availability for reads, honesty for writes.

## Identity & erasure

Identity is Keycloak's; Scree stores only an **opaque id** on tickets and keeps the
email↔opaque mapping out of Git. A **GDPR erasure** (DPO role, `DELETE
/identities/{id}`) deletes the identity record, purges permission tuples, scrubs
quarantine PII, and crypto-shreds encrypted bodies. Git history is not rewritten —
that bound is disclosed in the response and is inherent to the substrate.

## Releases

Images publish to `ghcr.io/witlox/scree`. Releases run **Wednesday evenings, only
when something changed** since the last tag. The version is
`YEAR.ADR-COUNT.COMMIT-COUNT` — the number encodes how many decisions and commits
shaped the release.

## CI tiers (what gates a change)

- `api-tests` — unit + `@api` BDD (in-process, fast).
- `bdd (@api scenarios)` — the canonical features, surfaced as their own check.
- `web-tests` — vitest + typecheck + build.
- `web-e2e (@e2e journeys)` — Playwright against real islands (desktop + mobile).
- `contract-tests` — `@contract` tier against real Keycloak/OpenFGA/Vault via
  testcontainers (runs on every PR; also nightly).

The standing gap the CI cannot prove is **live verification** against a real
browser + Keycloak + GitLab; budget a manual pass before cutover.
