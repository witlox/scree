# Scree — Deployment Topology

Production on Kubernetes; local dev + CI e2e/contract via Docker Compose +
Testcontainers (ADR-0010). This fixes the runtime shape; HA/DR specifics are
follow-ups (OQ-X-008).

## Production (Kubernetes)

Deployed alongside the existing GitLab/Keycloak/Vault/OTel platform.

| Workload | Kind | Notes |
|---|---|---|
| **Gateway** | Deployment (HA, ≥2 replicas) | tier-1; single enforcement point; stateless (state in Git/stores) |
| **Frontend** (knowledge/portal/admin) | Deployment(s) | static + SSR; behind ingress |
| **Slack adapter** | Deployment | client of the Gateway |
| **Email poller** (O365) | Deployment | inbound poll/webhook → Gateway |
| **Indexer batch** | **CronJob** (hourly) | not a CI job (INV-IX) |
| **Critical webhook receiver** | part of Gateway (or small Deployment) | verifies signature, re-reads Git |
| **OpenFGA** | Deployment + its datastore | ticket ReBAC + ListObjects |
| **Identity directory** | Postgres (erasable PII store) | INV-DP-1; backup/residency per OQ-HE-005 |
| **Search/aggregation index** | reuse GitLab Advanced Search / dedicated store | derived, rebuildable |
| **Object storage** | S3-compatible | external attachments |

External (not deployed by Scree): GitLab, Keycloak, Vault, O365, Slack.

Cross-cutting: OpenTelemetry sidecar/collector; secrets from Vault (no secrets in
manifests); network policy so only the Gateway egresses to GitLab/Graph/Slack.

## Local dev + CI (Compose + Testcontainers)

- **Compose** brings up the Scree services + local Postgres/OpenFGA/object store
  for one-command local dev.
- **Testcontainers** spins **real disposable** GitLab/Keycloak/Postgres/MailHog
  from within the `@contract` tests (and backs `@e2e`), so CI needs only Docker on
  the runner (`guidelines/bdd.md`, `guidelines/ci.md`).

## Open follow-ups

- HA for OpenFGA + its datastore; Gateway autoscaling targets (after OQ-X-006 perf).
- Backup + data residency for the identity directory and index (OQ-X-008, OQ-HE-005).
- Where age recipient keys + Vault Transit keys are provisioned/rotated (ADR-0008).
