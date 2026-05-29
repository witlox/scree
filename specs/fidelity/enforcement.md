# Phase 3 — Decision & invariant enforcement

Per invariant: is there a test that **fails if it is violated**? ENFORCED (yes, against real/faithful code) · DOCUMENTED (asserted only shallowly, or mechanism is config with no test) · UNENFORCED (no failing test). Critical invariants per `specs/invariants.md`: INV-AGG, INV-ACC-*, INV-ID-2.

## Storage & truth

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-ST-1 | Every mutation is a Git commit | **ENFORCED (docs only)** | `test_docs_write.py:38` real commit. **UNENFORCED for risks/tickets** — `RiskStore`/`TicketStore` are in-memory. |
| INV-ST-2 | Index + OpenFGA rebuildable from Git | **UNENFORCED** | no rebuild/reconcile test. |
| INV-ST-3 | `schema_version` required from first commit | **ENFORCED** | read quarantine `test_git_store.py:7`; write reject `test_docs_write.py:60`; `test_frontmatter.py:28`. |
| INV-ST-4 | `id` stable, globally unique, Gateway-allocated | **PARTIAL** | uniqueness `test_doc_write_integrity.py:40`. id-**immutability** + per-kind **sequence allocation** UNENFORCED (ids author-supplied in frontmatter). |
| INV-ST-5 | created/updated/audit are Git projections | **WEAK** | `test_git_store.py:12` non-null only; no test that `updated` advances on edit or that authored timestamps are rejected. |
| INV-ST-6 | RMW optimistic concurrency; conflicts surfaced | **PARTIAL** | stale-rev → 409 `test_doc_write_integrity.py:47`. Retry + structured-field-conflict-surfacing UNENFORCED. |

## References

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-REF-1 | References by stable id | **UNENFORCED** | no reference-render test in scope. |
| INV-REF-2 | Delete is a tombstone (history retained) | **DOCUMENTED** | erasure keeps Git (`test_erasure.py:58`); no explicit tombstone test. |
| INV-REF-3 | Missing/unreadable ref → "unavailable", no metadata | **UNENFORCED** | no test. |
| INV-REF-4 | Delete/move never blocked by refs | **UNENFORCED** | no test. |
| INV-REF-5 | Cross-boundary ref `target_id` withheld | **UNENFORCED** | no test. |

## Access & permissions

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| **INV-AGG** | Aggregation ⊆ directly-readable; no metadata leak | **PARTIAL** | ENFORCED for planning (`test_planning.py` `existence_hidden` — id/title/count/capacity exclusion) + docs/epics (`test_composed_authority.py:54,64`). Risk-register: MODERATE (`test_risk_persistence_api.py:33`, in-memory, no count/score-leak assertion). **Search view + separate-sensitive-index: UNENFORCED.** `aggregation_permissions.feature` unbound. |
| INV-ACC-1 | All access Gateway-mediated; no bypass | **ENFORCED** | `test_oidc_gateway.py:67`. |
| INV-ACC-2 | Authority = GitLab RBAC ∪ ticket ReBAC | **ENFORCED (fakes)** | `test_ticket_authority.py` + `test_composed_authority.py:54`; real GitLab union only at dormant @contract. |
| INV-ACC-3 | Ticket readable only by participants / community | **ENFORCED** | `test_ticket_access_fixes.py:35,46`. |
| INV-ACC-4 | Org tag grants no access | **UNENFORCED** | no test. |
| INV-ACC-5 | Stale permission cache fails closed | **UNENFORCED + TENSION** | no test; outage path `app.py:281–282` deliberately serves stale grants (last-known) per G12-01 — opposite of fail-closed. See `gaps.md` G-A2. |

## Encryption

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-ENC-1 | Tagged/born-encrypted bodies + sensitive spaces encrypted | **ENFORCED** | `test_ticket_encryption.py:43,54`. |
| INV-ENC-2 | Gateway-mediated (Vault Transit), per-requester key | **ENFORCED** | durable-required `test_crypto_hardening.py:29`; @contract Vault FAITHFUL. |
| INV-ENC-3 | Encrypted tickets indexed by metadata only; neutral title | **DOCUMENTED** | opaque requester asserted; **no test** that bodies are excluded from full-text index or that title is a neutral placeholder. |
| INV-ENC-4 | Client-key revocation is rotation-based | **UNENFORCED** | only destroy/shred tested; client-key/`age` path unimplemented. |

## Data protection & erasure

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-DP-1 | PII outside Git; only opaque requester id in frontmatter | **ENFORCED** | `test_migration.py:61` (`"@" not in requester`), `test_erasure.py`. |
| INV-DP-2 | Erasure = anonymize + crypto-shred + purge all FGA tuples | **ENFORCED (split)** | opaque-unresolvable + tuples-gone `test_erasure.py:72–73`; crypto-shred `test_ticket_encryption.py:76` + @contract `test_vault_transit.py:68`. **Not consolidated** — erasure suite omits crypto. |
| INV-DP-4 | No stronger guarantee than substrate; bound disclosed | **ENFORCED** | `test_erasure.py:70` (`"Git history" in residual`). |

## Identity

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-ID-1 | GitLab actions carry the human via token exchange | **ENFORCED (unit/@api)** | `test_oidc.py` + shape `test_composed_authority.py:74`. Real exchange **DIVERGENT** (no @contract — `boundaries.md` SEAM 4). |
| INV-ID-2 | Unmappable Slack action refused | **ENFORCED** | `test_slack_capture.py:74`. |
| INV-ID-3 | Every action audited to integrity-protected sink | **PARTIAL** | writes + 5xx audited (`test_gateway_identity_security.py:87`, `test_audit.py`). Successful **reads + aggregation queries not asserted**; sink **in-memory** (no WORM/hash-chain). |
| INV-ID-4 | External writes by desk SA, identity in commit trailer | **UNENFORCED** | no test. |

## Inbound email / Slack

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-EMAIL-1 | Verified before use; else quarantine, never attributed | **ENFORCED** | strong negatives `test_email_routing.py:45`, `test_email_ingest.py:69,79,99`. (Verdict *source* is an unmodeled seam — `boundaries.md` SEAM 6.) |
| INV-SLACK-1 | Requester=author (or refused); rate-limited | **ENFORCED** | `test_slack_capture.py:53,65,81`. |

## Lifecycle

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-LC-1 | Ticket states + legal transitions only | **ENFORCED** | `test_lifecycle.py:17` + feature 409. |
| INV-LC-2 | community_visible: resolved-only, curated snapshot, reopen re-gates | **PARTIAL** | flag-flip + resolved-only + **reopen re-gate** ENFORCED (`test_ticket_lifecycle.py:77`). "**Curated snapshot, not live thread / later private replies**" + audit-trail UNENFORCED (only boolean tested). |
| INV-LC-3 | Risk closed only via MR on MR-required path | **UNENFORCED** | no test creates/transitions a closed risk. |
| INV-LC-4 | Escalation = org duplicate + cross-ref, original kept | **ENFORCED** | `test_risk_register.py:30` (unit; no Gateway endpoint test). |

## Indexing & triggers

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-IX-1 | security/compliance risk → webhook; else batch | **ENFORCED (flag)** | `test_risk_register.py:22`, `test_risk_assess_api.py:17` (category-driven, not severity). No actual dispatch; "rides batch" untested. |
| INV-IX-2 | Missed webhook caught by next batch | **UNENFORCED** | no reconciliation test. |
| INV-IX-3 | Manual re-index authenticated + rate-limited | **UNENFORCED** | not found. |
| INV-IX-4 | Sensitive categories indexed separately | **UNENFORCED** | no test. |

## Orphans / governance / migration / degradation

| Inv | Statement | Status | Evidence / gap |
|---|---|---|---|
| INV-ORPH-1/2 | Orphan flagging (resource + ticket); never auto-reassign | **ENFORCED** | full matrix `test_orphan_detection.py`. No explicit "owner/assignee unchanged" assertion. |
| INV-GOV-1 | MR-required paths uneditable by direct commit (branch protection + CODEOWNERS) | **DOCUMENTED** | only app-level `MRRequired` → 409 (`test_docs_write.py:54`), which a direct `git push` bypasses. The actual mechanism (GitLab config) is **untested**. |
| INV-MIG-1 | Stable old→new ID mapping; no broken links | **ENFORCED** | `test_migration.py:53`. |
| INV-MIG-2 | Pipeline idempotent (re-run no dup) | **ENFORCED** | actual re-run `test_migration.py:66` + restart `test_migration_idempotency.py:28`. |
| INV-MIG-3 | Non-curated → archive, not migrated | **ENFORCED** | `test_migration.py:77`. |
| INV-MIG-4 | Atomic populate Git + identity + OpenFGA | **PARTIAL** | Git+identity+mapping asserted; **OpenFGA tuple-for-migrated-ticket not asserted**; mid-failure atomicity untested. |
| INV-DEG-1 | Reads survive GitLab outage; writes refused clearly | **ENFORCED** | served read + refused-create `test_degradation.py:29,42`; last-known path `:hardening:21`. slack_link/migration refusal status-only. |
| INV-DEG-2 | O365 down → inbound email fails visibly | **ENFORCED** | `test_degradation.py:54`. |

## ADR enforcement

| ADR | Status | Note |
|---|---|---|
| 0001 in-house desk on Git substrate | PARTIAL | docs on real Git; tickets/risks in-memory. |
| 0002 backend Python/FastAPI | N/A | meta. |
| 0003 frontend React/htmx | not audited | `web/` (vitest) out of this scope. |
| 0004 BDD pytest-bdd + Playwright | PARTIAL | pytest-bdd for 5 features; **Playwright e2e tier absent** (`@e2e` tags only in unbound features). |
| 0005 selective encryption split-key | ENFORCED (Gateway-mediated half) | client-side half = ADR-0008. |
| 0006 data protection & erasure | ENFORCED | INV-DP-* covered. |
| 0007 authz GitLab RBAC + OpenFGA | ENFORCED (fast tier) | real GitLab union at dormant @contract. |
| 0008 encryption tooling (Vault default, `age` break-glass) | PARTIAL | Vault Transit @contract FAITHFUL; **client-side `age` break-glass UNIMPLEMENTED** (only `FernetCrypto`/`VaultTransitCrypto` exist). |
| 0009 editor Tiptap | not audited | frontend. |
| 0010 deployment topology | DOCUMENTED by design | WORM audit sink, health probe, DR are deploy-time; no app test (accepted G12-03/AR-10). |
