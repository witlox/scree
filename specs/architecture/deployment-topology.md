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
| **Audit store** | append-only (hash-chained / WORM) | INV-ID-3; reads + queries; retention per OQ-HE-005 (AR-10) |

External (not deployed by Scree): GitLab, Keycloak, Vault, O365, Slack.

Cross-cutting: OpenTelemetry sidecar/collector; secrets from Vault (no secrets in
manifests); network policy so only the Gateway egresses to GitLab/Graph/Slack.

## Local dev + CI (Compose + Testcontainers)

- **Compose** brings up the Scree services + local Postgres/OpenFGA/object store
  for one-command local dev.
- **Testcontainers** spins **real disposable** GitLab/Keycloak/Postgres/MailHog
  from within the `@contract` tests (and backs `@e2e`), so CI needs only Docker on
  the runner (`guidelines/bdd.md`, `guidelines/ci.md`).

## Break-glass & disaster recovery (AR-01 / AR-02)

- **Break-glass space.** SOC / incident-response / DR runbooks — including the
  Vault and **Transit-key restore procedures** — live in a client-key (`age`)
  encrypted space, readable **offline from a clone** by the incident team with
  out-of-band keys, independent of GitLab/Gateway/Vault. This is the one place that
  must survive a full-stack outage (it breaks the "to restore Vault you need Vault"
  circular dependency).
- **Tier-1 DR for the non-Git stores.** "Backups are clones" covers only Git. The
  Vault **Transit keys** (loss = mass unrecoverable tickets), the **identity
  directory** (sole PII copy), the **OpenFGA datastore**, and the **index** all
  require backup/restore at least as robust as Git's, **restore-tested**. Transit-
  key backup is tier-1. Residency per OQ-HE-005; full posture is OQ-X-008.

## Open follow-ups

- HA for OpenFGA + its datastore; Gateway autoscaling targets (after OQ-X-006 perf).
- Out-of-band custody + rotation for break-glass `age` keys and Vault Transit keys.
