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
| I-03 | **High** | Identity is an untrusted header; real authz not wired into Gateway | ✅ core: OIDC bearer auth wired (verified JWT → principal; plaintext header ignored when auth on). Follow-ups: make authenticator mandatory in prod, Keycloak JWKS `@contract`, RFC 8693 token exchange + wire RealOpenFga/GitLabAuthority into default app |
| I-04 | Medium | Re-writing identical doc content crashes (500) | this round |
| I-05 | Medium | Malformed frontmatter → 500 instead of 422 | this round |
| I-06 | Medium | Doc write: no id allocation / uniqueness / kind check (INV-ST-4) | later round |
| I-07 | Medium | Doc write: no optimistic concurrency (INV-ST-6) | later round |
| I-08 | Medium | No audit anywhere (INV-ID-3) | later round |
| I-09 | Medium | Risk register hollow (predicate not wired; no persistence) | later round |
| I-10 | Low | Per-endpoint error handling, not the central handler | later round |

**Counts:** 3 high · 6 medium · 1 low — 10 total. Fixing I-01/02/04/05 this round.
