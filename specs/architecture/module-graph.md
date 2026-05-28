# Scree — Module Graph

Concrete module layout for the monorepo (DD-010). Backend is Python+FastAPI
(ADR-0002); frontend is React+TS / htmx (ADR-0003). Dependencies are acyclic.

## Backend (`api/` — FastAPI)

| Module | Responsibility | Depends on |
|---|---|---|
| `platform/` | config, OpenTelemetry, Vault client, error taxonomy | — (leaf) |
| `schemas/` | Pydantic models: frontmatter + API DTOs (single source of truth; generates OpenAPI → TS client) | platform |
| `crypto/` | SOPS+age (client-key) and Vault Transit (per-requester) wrappers (ADR-0008) | platform |
| `access/` | OIDC validation + token exchange (Keycloak), OpenFGA client (ticket ReBAC), authority composition, **identity directory** (external-customer PII store, erasable — INV-DP-1), audit sink (append-only — INV-ID-3) | platform, schemas |
| `integration/gitlab/` | Git read/write, repo ops, webhooks, Advanced Search | platform, schemas |
| `integration/o365/` | inbound parse (DKIM/DMARC, MIME, threading), outbound (Graph) | platform, schemas |
| `integration/slack/` | events, emoji/slash, snapshot capture | platform, schemas |
| `knowledge/` | docs domain (versions, templates, governed paths) | schemas, access, crypto, integration/gitlab |
| `servicedesk/` | tickets: lifecycle, relations, visibility, multi-origin normalization, encryption hooks | schemas, access, crypto, integration/* |
| `risk/` | risks: scoring, ROAM, category→critical, escalation | schemas, access, integration/gitlab |
| `indexing/` | scraper (batch/manual/critical-webhook), index client, **per-item filtered** aggregation queries | schemas, access, integration/gitlab |
| `planning/` | read-only rollups over GitLab epics/iterations | schemas, access, indexing, integration/gitlab |
| `migration/` | Atlassian→Scree pipeline; old→new ID mapping | schemas, knowledge, servicedesk, integration/* |
| `gateway/` | API surface, request context, authn, **authz composition**, audit emission — the single enforcement point | access + all domain modules |

Rule: domain modules never import each other; cross-domain flows go through the
Gateway. Integration adapters that run as **separate services** (Slack bot, email
poller) call the Gateway HTTP API — they do not import backend modules (DD-006).

## Frontend (`web/` — pnpm workspace)

| Package | Surface | Stack |
|---|---|---|
| `web/knowledge` | doc reading (htmx/SSR) + WYSIWYG editor island (TipTap, ADR-0009) | htmx + React island |
| `web/portal` | external customer portal v1 | React |
| `web/admin` | agent queues, risk register, planning dashboards | React |
| `web/shared` | component library, the **generated** API client (from gateway OpenAPI), auth | React/TS |

No surface talks to GitLab/etc. directly; all go through `web/shared`'s API
client to the Gateway. A DOM region is owned by htmx **or** React, never both
(ADR-0003).

## Other top-level dirs (DD-010)

```
cli/         CLI client (Gateway API client)
deploy/      Helm/k8s manifests (prod) + docker-compose (dev/CI) — ADR-0010
docs/        system documentation (MkDocs)
specs/       analyst + architecture specs
```

## Consistency checks satisfied

- Acyclic: `platform`/`schemas` are leaves; `gateway` is the apex; no domain↔domain
  imports.
- Every bounded context (context-graph) maps to exactly one backend module.
- Single enforcement point: only `gateway` composes authority; adapters are clients.
- One data-model source: `schemas/` → OpenAPI → TS client (no duplicate types).
