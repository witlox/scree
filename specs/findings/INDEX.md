# Findings Index

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

## Analyst Gate 1 (2026-05-28) — `analyst-gate-1.md`

| ID | Sev | Area | Finding | Status | Resolution |
|---|---|---|---|---|---|
| F-01 | **Critical** | service-desk / security | Ticket privacy bypassable via direct Git clone | ✅ resolved | ADR-0005 (selective encryption; external tickets Gateway-mediated), INV-ENC-* |
| F-02 | High | email / security | Inbound email unauthenticated; threading forgeable | ✅ resolved | INV-EMAIL-1; ticket_origins.feature quarantine scenario |
| F-03 | High | identity | External-customer writes can't use token exchange | ✅ resolved | INV-ID-4; permission-model §5 |
| F-04 | High | service-desk / privacy | `community_visible` exposure scope undefined | ✅ resolved | INV-LC-2 (curated snapshot, resolved-only, reopen re-gates); ticket_lifecycle.feature |
| F-05 | Medium | audit | Read/query audit storage unspecified | ✅ resolved | INV-ID-3 (append-only, integrity-protected sink) |
| F-06 | Medium | migration | No migration features/invariants/ID-mapping spec | ✅ resolved | migration.feature; INV-MIG-1/2/3 |
| F-07 | Medium | knowledge | Page-level doc permissions silently dropped | ✅ resolved | ADR-0005 (client-key encryption for sensitive spaces); permission-model §9 |
| F-08 | Medium | core | Global `id` uniqueness not allocatable across repos | ✅ resolved | INV-ST-4 (Gateway-allocated per-kind sequence) |
| F-09 | Medium | core / concurrency | Direct-commit conflict resolution unspecified | ✅ resolved | INV-ST-6; cross-context concurrency note |
| F-10 | Medium | planning | Planning-view permission filtering unspecified | ✅ resolved | planning.feature; INV-AGG |
| F-11 | Medium | slack | `:ticket:` reaction enables spam / cross-user capture | ✅ resolved | INV-SLACK-1; slack_capture.feature (rate-limit, author=requester) |
| F-12 | Low | risk schema | `score` both authored and derived | ✅ resolved | risk.md (`score` derived) |
| F-13 | Medium | risk schema | Severity bands illustrative, not normative | ✅ resolved | risk.md (`severity` bands normative & derived) |
| F-14 | Low | references | `target_id` leaks existence of sensitive resource | ✅ resolved | INV-REF-5 |
| F-15 | Medium | service-desk | Orphan policy misses tickets / departed assignees | ✅ resolved | INV-ORPH-2; orphan_detection.feature |

**Counts:** 1 critical · 3 high · 9 medium · 2 low — **15 total, all resolved.**

Per project policy every finding was fixed (severity set order, not whether). The
encryption decision (F-01/F-07) is recorded as **ADR-0005**; its tooling is the
new architect question **OQ-X-009**.

## Architecture Gate 2 (2026-05-28) — `architecture-gate-2.md`

| ID | Sev | Area | Finding | Status |
|---|---|---|---|---|
| AR-01 | **High** | encryption / web | Client-key docs can't be server-rendered (client-key vs SSR) | ✅ resolved | ADR-0008 (Gateway-mediated default; client-key scoped to break-glass) |
| AR-02 | **High** | DR | Non-Git stores (Transit keys, identity dir) lack DR; key loss = mass loss | ✅ resolved | deployment-topology Break-glass & DR; ADR-0008 |
| AR-03 | **High** | core | OpenFGA vs Git source-of-truth for ticket relations ambiguous | ✅ resolved | INV-ST-2 (Git truth, OpenFGA derived/rebuildable); integration-contracts |
| AR-04 | **High** | permissions | Ticket aggregation via ListObjects alone under-grants agents | ✅ resolved | indexer-design + enforcement-map (ListObjects ∪ GitLab membership) |
| AR-05 | Medium | erasure | Erasure doesn't purge OpenFGA tuples | ✅ resolved | INV-DP-2 |
| AR-06 | Medium | privacy | Encrypted-ticket title/metadata cleartext may carry PII | ✅ resolved | INV-ENC-3 (title placeholder); data-structures |
| AR-07 | Medium | availability | Identity directory degraded mode unspecified (SPOF) | ✅ resolved | context-graph degraded-mode table |
| AR-08 | Medium | performance | GitLab per-item authority eval method unspecified (perf/DoS) | ✅ resolved | indexer-design (resolve readable Spaces once) |
| AR-09 | Medium | migration | Migration must populate identity dir + OpenFGA, not just Git | ✅ resolved | INV-MIG-4 |
| AR-10 | Medium | audit | Audit sink store + tamper-evidence + retention not realized | ✅ resolved | INV-ID-3 + deployment-topology Audit store |
| AR-11 | Medium | performance | INV-AGG depends on unvalidated ListObjects perf | ✅ resolved | indexer-design Performance note → OQ-X-006 + spike |
| AR-12 | Low | UX | 404-collapse may confuse users who lost access | ✅ resolved | error-taxonomy (accepted; softer same-Space message) |

**Counts:** 4 high · 7 medium · 1 low — **12 total, all resolved.**

The key-model correction (AR-01, caught by the user) reshaped ADR-0005/0008:
Gateway-mediated (Vault Transit) is the default for encrypted content; client-side
`age` keys are scoped to **break-glass/DR/SOC** content that must be readable
offline when the online stack is down.

## Implementation Gate 1 (2026-05-28) — `impl-gate-1.md`

Adversarial pass over merged code (PRs #33–#44).

| ID | Sev | Finding | Status |
|---|---|---|---|
| I-01 | **High** | Customer can't read the ticket they just created (no requester tuple) | this round |
| I-02 | **High** | `community_visible` grants no read access (INV-ACC-3 unenforced) | this round |
| I-03 | **High** | Identity is an untrusted header; real authz not wired into Gateway | ✅ core: OIDC bearer auth wired (verified JWT → principal; plaintext header ignored when auth on). Keycloak JWKS `@contract` landed (#50, real realm/client/user → live JWKS verification + Gateway bearer path). Remaining follow-ups beyond gate-1: make authenticator mandatory in prod, RFC 8693 token exchange + wire RealOpenFga/GitLabAuthority into default app |
| I-04 | Medium | Re-writing identical doc content crashes (500) | this round |
| I-05 | Medium | Malformed frontmatter → 500 instead of 422 | this round |
| I-06 | Medium | Doc write: no id allocation / uniqueness / kind check (INV-ST-4) | ✅ resolved | #47 (kind check + id uniqueness in DocService) |
| I-07 | Medium | Doc write: no optimistic concurrency (INV-ST-6) | ✅ resolved | #47 (base_rev vs rev → Conflict) |
| I-08 | Medium | No audit anywhere (INV-ID-3) | ✅ resolved | #49 (AuditSink + Gateway audit middleware, principal recorded) |
| I-09 | Medium | Risk register hollow (predicate not wired; no persistence) | ✅ resolved | #48 (RiskStore + critical-webhook trigger wired) |
| I-10 | Low | Per-endpoint error handling, not the central handler | ✅ resolved | #49 (central FastAPI exception handlers from error taxonomy) |

**Counts:** 3 high · 6 medium · 1 low — **10 total, all resolved.** I-03 core
landed; its prod-hardening follow-ups (mandatory authenticator, Keycloak JWKS
`@contract`, RFC 8693) are tracked beyond gate-1.

## Implementation Gate 2 (2026-05-28) — `impl-gate-2.md`

Adversarial pass over the merged custom layer after gate-1 + OIDC/Keycloak (PRs #45–#50).

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G2-01 | **High** | Security/path-traversal | Arbitrary file write via doc-write `path` | ✅ #51 (is_safe_relpath confines writes) |
| G2-02 | **High** | Security/authz | Ticket create trusts client `requester`, ignores principal | ✅ #52 (requester bound to principal; agent-only on-behalf) |
| G2-03 | **High** | Security/identity | Auth default-off; X-Spike-User header trusted (I-03 follow-up) | ✅ #52 (fail-closed; allow_insecure_header_auth opt-in) |
| G2-04 | Medium | Security/authz | Write authority on frontmatter `space`, not `path` | ✅ #51 (DocService space binding; SpaceMismatch) |
| G2-05 | Medium | Security/identity | Principal from mutable `preferred_username` not `sub` | ✅ #52 (principal = sub) |
| G2-06 | Medium | Privacy/aggregation | community_visible views leak opaque `requester` | ✅ #53 (can_see_identity; requester redacted) |
| G2-07 | Medium | Robustness/DoS | YAML frontmatter unbounded (alias bomb, size) | ✅ #51 (no-alias loader + size caps) |
| G2-08 | Medium | Robustness/observability | 5xx bypasses audit middleware | ✅ #52 (audit in finally) |
| G2-09 | Low | Correctness/input | Risk/ticket inputs not range/enum validated | ✅ #53 (Pydantic models; range/enum) |
| G2-10 | Low | Security/identity | `/risks/assess` unauthenticated | ✅ #52 (requires get_principal) |
| G2-11 | Low | Robustness/concurrency | Git `index.lock` races → 500 | ✅ #51 (per-repo write lock; GitWriteError→409) |

**Counts:** 3 high · 5 medium · 3 low — **11 total, all resolved.** G2-01/02/03 were `gate:blocking`.

## Implementation Gate 3 (2026-05-28) — `impl-gate-3.md`

Adversarial pass over the planning slice (PR #54). Primary target: INV-AGG.

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G3-01 | Medium | Security/INV-AGG | Stale index group-mapping leaks an epic across a group move | ✅ #55 (accepted bounded-staleness, disclosed via as_of/never_indexed; closes with real GitLab-group authority) |
| G3-02 | Low | Robustness/exhaustion | Unbounded portfolio rollup (no pagination/bound) | ✅ #55 (cursor pagination, bounded limit; totals over all visible) |
| G3-03 | Low | Robustness/degradation | Partial config silently 404s; never-indexed staleness served as bare null | ✅ #55 (fail-loud partial config; never_indexed signal) |

**Counts:** 1 medium · 2 low — **3 total, all resolved.** No `gate:blocking` (no critical/high).

## Implementation Gate 4 (2026-05-28) — `impl-gate-4.md`

Adversarial pass over the inbound email ingestion slice (PR #56). Primary target: email pipeline + INV-EMAIL-1/INV-DP-1.

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G4-01 | **High** | Security/trust-boundary | Attacker-supplied Authentication-Results trusted → INV-EMAIL-1 bypass | ✅ #57 (verdict out-of-band from trusted poller; raw A-R no longer consulted) |
| G4-02 | Medium | Security/authz | New-ticket path needs no verification → spoofable requester attribution | ✅ #57 (unverified → quarantine; never attributed) |
| G4-03 | Medium | Privacy/data-protection | Requester id minted from raw email address → PII in Git/OpenFGA (INV-DP-1) | ✅ #57 (IdentityDirectory opaque id; email out of Git) |
| G4-04 | Medium | Correctness | Generated email_token (hex) vs matcher (`\d+`) → token threading dead for real tickets | ✅ #57 (numeric SCREE-NNN token) |
| G4-05 | Medium | Robustness/degradation | Quarantine not persisted — "agent review" unimplemented | ✅ #57 (QuarantineStore + agent review endpoint) |
| G4-06 | Medium | Robustness/exhaustion | No size bound on inbound raw email | ✅ #57 (1MB cap → 413) |
| G4-07 | Low | Robustness/performance | O(n) ticket scan per inbound email | ✅ #57 (store-indexed by message-id/token) |

**Counts:** 1 high · 5 medium · 1 low — **7 total, all resolved.** G4-01 was `gate:blocking`.

## Implementation Gate 5 (2026-05-28) — `impl-gate-5.md`

Adversarial pass over the GDPR erasure slice (PR #58). Primary target: erasure completeness (INV-DP-2/AR-05).

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G5-01 | Medium | Security/data-protection | `RealOpenFga.purge_user` incomplete: no Read pagination, no delete batching, ticket-type only | ✅ #59 (paginate Read + batch deletes ≤100; @contract 120-tuple test; type scope documented) |
| G5-02 | Medium | Privacy/data-protection | Erasure doesn't scrub the quarantine queue (retains email + body); mapping deleted before scrub possible | ✅ #59 (email resolved before deletion; QuarantineStore.purge_sender) |
| G5-03 | Low | Robustness/compliance | No durable erasure receipt; residual (Git/comment) scope not disclosed | ✅ #59 (ErasureReceiptStore + GET /identities/erasures; residual in response) |

**Counts:** 2 medium · 1 low — **3 total, all resolved.** No `gate:blocking` (no critical/high).

## Implementation Gate 6 (2026-05-28) — `impl-gate-6.md`

Adversarial pass over the Slack capture slice (PR #60). Primary target: Slack identity/authenticity.

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G6-01 | Medium | Privacy/data-protection | Slack-mapped requester may be PII-bearing (re-introduces G4-03) | ✅ #61 (opaque via IdentityDirectory; agents pass through) |
| G6-02 | Medium | Security/trust-boundary | Slack endpoints trust arbitrary event fields from any agent; no authenticity, over-broad authz | ✅ #61 (dedicated service_principals gate; also email inbound) |
| G6-03 | Low | Robustness | Rate limiter per-process, unbounded, counts attempts not captures | ✅ #61 (count successes; evict stale; shared-state documented) |

**Counts:** 2 medium · 1 low — **3 total, all resolved.** No `gate:blocking`.

## Implementation Gate 7 (2026-05-28) — `impl-gate-7.md`

Adversarial pass over the orphan-detection slice (PR #62). Primary target: INV-ORPH completeness + report scoping.

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G7-01 | Medium | Correctness | Space-archived orphaning unimplemented (INV-ORPH-1 partial) | ✅ #63 (archived_spaces flags active resources/tickets) |
| G7-02 | Medium | Security/aggregation | Orphaned-ticket report not desk-scoped (all agents see all) | ✅ #63 (tickets grouped by desk; filtered by can_write) |
| G7-03 | Medium | Robustness | Recomputed per GET, not batch-cached (perf/DoS + semantic drift) | ✅ #63 (OrphanCache + POST /orphans/refresh batch + as_of) |
| G7-04 | Low | Correctness | Owner-access proxy uses read, misses lost-write-only owners | ✅ #63 (can_write proxy) |

**Counts:** 3 medium · 1 low — **4 total, all resolved.** No `gate:blocking`.

## Implementation Gate 8 (2026-05-28) — `impl-gate-8.md`

Adversarial pass over the encryption-at-create / crypto-shred slice (PR #64). Primary target: crypto durability + shred correctness.

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G8-01 | Medium | Robustness/durability | Ephemeral in-memory crypto is the default → silent unrecoverability without Vault | ✅ #65 (fail-closed: ticket_crypto required unless dev flag) |
| G8-02 | Medium | Correctness | Decryption conflates transient failure with permanent crypto-shred | ✅ #65 (4xx=shredded, 5xx=retryable propagated) |
| G8-03 | Low | Robustness/exhaustion | Comment/ticket body size unbounded | ✅ #65 (1MB cap → 413 on body/snapshot) |

**Counts:** 2 medium · 1 low — **3 total, all resolved.** No `gate:blocking`.

## Implementation Gate 9 (2026-05-28) — `impl-gate-9.md`

Adversarial pass over the token-exchange + composed-authority slice (PR #66). Primary target: per-request resolution path.

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G9-01 | Medium | Robustness/performance | Token-exchange + membership resolved every request, no cross-request cache (AR-08) | ✅ #67 (TtlCache for exchanged token + readable sets) |
| G9-02 | Medium | Robustness/fail-loud | Partial composed-authority config silently yields empty authority | ✅ #67 (gitlab_authority requires a token source) |
| G9-03 | Low | Correctness | readable_spaces counts only membership (under-grant for public Spaces) | ✅ #67 (accepted: member-access Space model, documented) |

**Counts:** 2 medium · 1 low — **3 total, all resolved.** No `gate:blocking`.

## Implementation Gate 10 (2026-05-28) — `impl-gate-10.md`

Adversarial pass over the migration slice (PR #68). Primary target: idempotency durability (INV-MIG-2).

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G10-01 | Medium | Correctness/idempotency | Idempotency keyed on in-memory IdMap → re-run after restart duplicates | ✅ #69 (deterministic id + durable-store existence check) |
| G10-02 | Medium | Correctness/atomicity | Non-atomic migration → mid-item failure duplicates on re-run | ✅ #69 (re-run repairs mapping, no duplicate) |
| G10-03 | Low | Correctness/reporting | Confluence-without-doc_writer counted migrated but archived | ✅ #69 (counted by actual outcome) |

**Counts:** 2 medium · 1 low — **3 total, all resolved.** No `gate:blocking`.

## Implementation Gate 11 (2026-05-28) — `impl-gate-11.md`

Adversarial pass over the portal-backend slice (PR #70). Primary target: public/community surface + external uploads.

| ID | Sev | Category | Finding | Status |
|---|---|---|---|---|
| G11-01 | Medium | Security/confidentiality | Community search decrypts & exposes encrypted-ticket content | ✅ #71 (exclude encrypted from search; refuse promoting encrypted) |
| G11-02 | Medium | Security/authz | Attachment upload on can_read → anyone can attach to a community ticket | ✅ #71 (participant-only via can_see_identity) |
| G11-03 | Low | Security/input | Attachments not type-restricted/scanned (+ unindexed search) | ✅ #71 (executable-extension allowlist; AV/index noted) |

**Counts:** 2 medium · 1 low — **3 total, all resolved.** No `gate:blocking`.
