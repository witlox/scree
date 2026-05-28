# Scree — Failure Modes

Enumerated failure modes with severity, blast radius, desired degradation, and
mitigation (OQ-A-012). Severity:

- **SEV-1** — data loss, a security/permission leak, or a core outage.
- **SEV-2** — major degradation; a primary capability is unavailable.
- **SEV-3** — minor or self-recovering.

The guiding rule (DD-003): degrade **gracefully and honestly** — never silently
drop or falsely succeed.

---

| # | Failure | Sev | Blast radius | Desired degradation / mitigation | Invariant |
|---|---|---|---|---|---|
| FM-1 | **GitLab unreachable** | SEV-1 | All writes; aggregation freshness | Local-clone reads of authorized content still serve; writes/ticket creation **refused** with a clear error, never queued-as-success | INV-DEG-1 |
| FM-2 | **O365 / Graph unreachable** | SEV-2 | Inbound + outbound email | Inbound email-driven ticket creation fails visibly; outbound notifications retried with backoff; web/Slack origins unaffected | INV-DEG-2 |
| FM-3 | **Keycloak unreachable** | SEV-1 | All user auth | No new logins; existing valid tokens honored until expiry; Vault outage must not also be required (auth depends only on Keycloak) | INV-ID-1 |
| FM-4 | **Token expired mid-operation** | SEV-3 | One in-flight request | Operation fails cleanly with re-auth prompt; no partial commit left behind | INV-ST-1 |
| FM-5 | **Token-exchange failure** | SEV-2 | Gateway→GitLab calls | Action refused; not retried as the Gateway's own identity (would break audit attribution) | INV-ID-1 |
| FM-6 | **Vault unreachable** | SEV-2 | Service-to-service creds | User login unaffected (not in auth path); service ops degrade; cached creds used within TTL | DD-017 |
| FM-7 | **Slack webhook missed** | SEV-3 | One critical-risk fast path | Next hourly batch catches the change; correctness never depends on webhook delivery | INV-IX-2 |
| FM-8 | **Slack↔Keycloak mapping fails** | SEV-2 | One Slack-initiated action | Action **refused**; never proceeds with degraded/anonymous attribution | INV-ID-2 |
| FM-9 | **Permission cache stale** | SEV-1 | Aggregation views (leak risk) | Short TTL; fail **closed** on uncertainty (omit item); revocation invalidation where feasible | INV-ACC-5, INV-AGG |
| FM-10 | **Scraper misses a critical risk** | SEV-2 | Leadership visibility latency | Webhook + batch redundancy; manual trigger; "last indexed" timestamp surfaced so staleness is visible | INV-IX-1/2 |
| FM-11 | **Indexer crashes mid-batch** | SEV-3 | Index freshness | Batch is idempotent and resumable; partial index never treated as authoritative; rebuild from Git | INV-ST-2 |
| FM-12 | **Index drifts from Git** | SEV-2 | Wrong/partial query results | Periodic full rebuild; index is derived, Git is truth; drift detectable by re-scan | INV-ST-2 |
| FM-13 | **Email parsing/threading failure** | SEV-2 | Misfiled or duplicate tickets | Mature MIME/threading libraries; conservative threading; agent can manually merge/split tickets | OQ-A-014 |
| FM-14 | **Attachment/object-store failure** | SEV-2 | Attachments on external tickets | Ticket text still created; attachment retried; failure surfaced to requester, not silent | DD-002 |
| FM-15 | **Concurrent edit / YAML merge conflict** | SEV-2 | One resource | Last-writer detection; structured-field conflicts surfaced for resolution, never silently merged wrong | INV-ST-1 |
| FM-16 | **Manual re-index abused (DoS)** | SEV-2 | Indexer availability | Authenticated + rate-limited per principal | INV-IX-3 |
| FM-17 | **Spoofed/forged webhook** | SEV-1 | Index integrity, possible leak | Verify webhook signature; reject unsigned/invalid; webhook only triggers re-read from Git (no payload trust) | INV-ST-1 |
| FM-18 | **Migration data infidelity** | SEV-1 | Historical record correctness | Pre-cutover validation gates; old→new ID mapping verified; sampled reconciliation | DD-014, OQ-A-019 |
| FM-19 | **Orphaned active resource undetected** | SEV-3 | Accountability gap | Hourly batch flags owner-lost-access actives to Space maintainers | INV-ORPH-1 |
| FM-20 | **MR-required path bypass attempt** | SEV-1 | Compliance/audit integrity | GitLab branch protection + CODEOWNERS reject direct commits on those paths | INV-GOV-1 |

---

The simultaneous failure of webhook **and** batch **and** manual trigger would be
required for an indexing outage (FM-7/10/11) — three independent paths. The least
resilient operation is **external ticket submission** (needs Gateway + GitLab +
O365 together, FM-1/2/3); this is accepted and documented, not engineered away in
v1 (DD-003).
