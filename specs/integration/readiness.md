# Integration Readiness — Scree v1

Integrator pass (refreshed 2026-05-29, after #79 risk/audit-on-Git, #84 indexer, #86
O365 poller, and the full frontend). Verifies that independently-implemented features
work together across the seams — data flow, event chains, shared state, identity
continuity, end-to-end workflows. (Individual-feature depth is the auditor's fidelity
index, `specs/fidelity/`.)

Suite at this pass: **233 @api/unit passed**; the `@contract` tier (real Keycloak/
OpenFGA/Vault/GitLab) runs nightly/on-demand (`.github/workflows/ci.yml`); web: 42.

## Cross-context test manifest

| Test (`api/tests/integration/`) | Seam | Invariants |
|---|---|---|
| `test_cc_ticket_origin_convergence.py` | web/api/email/slack → Gateway → servicedesk + o365 + slack + identity + access | INV-DP-1, INV-EMAIL-1, INV-SLACK-1, INV-ACC-3 |
| `test_cc_identity_propagation.py` | surface → Gateway(oidc) → token-exchange → gitlab authority → audit | INV-ID-1, INV-ID-3 |
| `test_cc_aggregation_consistency.py` | query → per-item filter across knowledge + risk | INV-AGG, INV-ACC-1 |
| `test_cc_migration_roundtrip.py` | Atlassian export → migration → knowledge(git) + servicedesk + identity → read | INV-MIG-1/4, INV-ST-1/2 |
| `test_cc_degraded_mode.py` | availability → write guard across servicedesk + migration; read path | INV-DEG-1 |
| `test_cc_indexer_redundancy.py` | resource change → indexer triggers (webhook OR batch) → index → /search | INV-IX-2, INV-AGG |
| `test_cc_email_poller_to_ticket.py` | O365/Graph → poller (trusted verdict) → Gateway → ticket/quarantine | INV-EMAIL-1, INV-DP-1 |

## Graduation checklist

- [x] **Ticket from each origin normalizes to one coherent record** — `test_cc_ticket_origin_convergence`.
- [x] **Aggregation/search provably excludes unauthorized items** — `test_cc_aggregation_consistency`, planning `existence_hidden`, and `/search` per-item filtered (`test_cc_indexer_redundancy`, `test_indexer`).
- [x] **Identity propagates: GitLab audit shows the human** — `test_cc_identity_propagation`; real-Keycloak exchange nightly `@contract`.
- [x] **Degraded mode: GitLab down → reads work, writes refused** — `test_cc_degraded_mode` + `test_degradation*`.
- [x] **Migration round-trips with ID mapping intact** — `test_cc_migration_roundtrip`.
- [x] **Indexer redundancy (kill one trigger, data still propagates)** — **now satisfied** (#84): `test_cc_indexer_redundancy` — a change reaches `/search` via the critical webhook OR the batch/manual reindex; a missed webhook is caught by the next batch (INV-IX-2); sensitive categories partitioned (INV-IX-4); manual reindex rate-limited (INV-IX-3). Live GitLab webhook *delivery* remains deploy.
- [x] **All cross-context interactions examined** — see "Seams" below.
- [~] **All cross-context Gherkin scenarios pass** — coverage is the `test_cc_*` pytest suite; the canonical `specs/features/*.feature` are largely unbound (auditor G-D2 / #98). Open, low-risk.
- [~] **All integration tests pass** — the `@api` suite passes (233 backend, 42 web). The `@contract` tier runs nightly, not per-PR (#76); GitLab/token-exchange contracts are env/version-gated.

## Seams examined (map in `specs/cross-context/interactions.md`)

| Interaction | Status |
|---|---|
| Surface → Gateway(OIDC) → token-exchange → GitLab (identity preserved) | ✅ `test_cc_identity_propagation`; real exchange nightly |
| Inbound email: O365/Graph → poller (DKIM/DMARC verdict) → Gateway → ticket | ✅ **now modeled** (#86) — forged A-R distrusted/quarantined (`test_cc_email_poller_to_ticket`); live Graph fetch is deploy |
| Slack reaction → Gateway → draft ticket; refused on unmapped identity | ✅ verified; real Slack API unmodeled (flagged) |
| Aggregation/search → per-item filter | ✅ docs+risks+planning + `/search` |
| Resource change → batch/manual/webhook → index → query | ✅ **now built** (#84) `test_cc_indexer_redundancy` |
| Risk mutation → Git commit (rebuildable index/store) | ✅ **now real** (#79) `test_risk_git_store` |
| Audit of every action → tamper-evident sink | ✅ **now hash-chained** (#79) `test_audit_integrity` |
| GitLab unreachable → reads ok, writes refused | ✅ `test_cc_degraded_mode` |
| MR-required path → direct commit blocked | ⚠️ app-level only; real enforcement is GitLab branch protection (deploy) → #80 |
| Migration: export → Git → indexed → visible, mapping intact | ✅ `test_cc_migration_roundtrip` |
| Gateway → object store (attachments) | ✅ in-memory; participant-only |

No new integration defects found this pass.

## Readiness recommendation — **GO (deploy- and scope-conditional)**

Upgraded from the prior CONDITIONAL GO: **the three substantive deferrals are closed.**
- **#79** — risk register + audit are Git-backed / hash-chained (INV-ST-1, INV-ID-3). ✅
- **#84** — real indexer with the three-trigger model + redundancy + sensitive partition (INV-IX-1/2/3/4). ✅
- **#86** — O365/Graph poller models the trusted DKIM/DMARC verdict; forged A-R is distrusted (INV-EMAIL-1, G4-01). ✅

**No substantive code gaps remain.** What's left is genuinely deploy-time, scope, or
out-of-band verification — none require new application logic:

1. **Deploy config** — #80 GitLab branch protection + CODEOWNERS on the runtime data
   repos (can't live in this build repo); the `@contract` nightly must be watched (#76);
   WORM medium / health probe / Graph subscription / GitLab webhook are deploy wiring,
   documented at the seams.
2. **Live verification** — no surface has had a real browser + Keycloak + gateway pass;
   the frontend adversary gate (FE-01) showed why this matters. The top pre-cutover gate.
3. **Scope / small features** — #91 (`age` break-glass: in v1?), #92 (reference render),
   #97 (Playwright e2e), #98 (bind canonical features), #75 (search UI), #94 (commit trailer).

**Recommendation:** the code is ready to take into a `v1 cutover` review. The blocking
pre-cutover gate is **live end-to-end verification** against real Keycloak/GitLab/O365;
the rest is deploy config + scope ratifications. Cut the readiness tag after that
review (the `v1 cutover` milestone is the tracking home).
