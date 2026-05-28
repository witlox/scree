# ADR-0010: Deployment — Kubernetes (prod) + Compose/Testcontainers (test)

- Status: accepted
- Date: 2026-05-28
- Deciders: build team
- Resolves: OQ-X-007
- Context phase: architect

## Context

Scree is a multi-service custom layer (Gateway, indexer, integration adapters,
frontend, OpenFGA, identity directory, index, object store) alongside an existing
GitLab/Keycloak/Vault/OpenTelemetry stack.

## Decision Outcome

- **Production → Kubernetes**, deployed alongside the existing platform; reuses
  the org's k8s ops and OpenTelemetry; supports HA for the tier-1 Gateway.
- **Local dev + CI e2e/contract tests → Docker Compose + Testcontainers.** The
  BDD `@contract` tier (and the backing services for `@e2e`) spin real disposable
  GitLab/Keycloak/Postgres/MailHog from the tests via Testcontainers; Compose
  gives a one-command local stack. (Matches `guidelines/bdd.md` + `guidelines/ci.md`.)

### Consequences

- Good: prod reuses existing platform + observability; tests run the real
  dependencies without a standing environment; CI is runner-Docker only.
- Bad / accepted: two environment definitions (k8s manifests/Helm + Compose) to
  keep roughly in sync; k8s assumes the org already operates a cluster.

## Open follow-ups (architect/integrator)

- HA specifics for the Gateway and OpenFGA; backup/residency of the identity
  directory and index (relates to OQ-X-008 DR, OQ-HE-005 residency).
- Where the hourly indexer batch runs (k8s CronJob) — not a CI job (INV-IX, ci.md).
