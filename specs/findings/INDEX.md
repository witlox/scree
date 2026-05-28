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
