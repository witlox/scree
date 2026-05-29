# Integration Readiness — Scree backend spike

Integrator pass: 2026-05-29. Verifies that independently-implemented features work
together across the seams (not individual feature correctness — that is the auditor's
fidelity index, `specs/fidelity/`). Concern is data flow, event chains, shared state,
identity continuity, and end-to-end workflows.

Suite at this pass: **207 @api/unit passed**; `@contract` tier runs nightly/on-demand
(see `.github/workflows/ci.yml`, G-B1).

## Cross-context test manifest

Each test exercises a seam spanning ≥2 contexts. Runnable under `api/tests/integration/`.

| Test (`api/tests/integration/`) | Seam | Features | Invariants |
|---|---|---|---|
| `test_cc_ticket_origin_convergence.py` | surface(web/api/email-poller/slack-bot) → Gateway → servicedesk + o365 + slack + identity + access | ticket_origins, slack_capture, ticket_lifecycle | INV-DP-1, INV-EMAIL-1, INV-SLACK-1, INV-ACC-3 |
| `test_cc_identity_propagation.py` | surface → Gateway(oidc) → token_exchange → gitlab authority → audit | — | INV-ID-1, INV-ID-3 |
| `test_cc_aggregation_consistency.py` | query → per-item filter across knowledge + risk | aggregation_permissions, risk_register | INV-AGG, INV-ACC-1 |
| `test_cc_migration_roundtrip.py` | Atlassian export → migration → knowledge(git) + servicedesk + identity → read endpoints | migration | INV-MIG-1/4, INV-ST-1/2 |
| `test_cc_degraded_mode.py` | availability → write guard across servicedesk + migration; read path | degradation | INV-DEG-1 |

## Graduation checklist

- [x] **Ticket from each origin normalizes to one coherent record** — `test_cc_ticket_origin_convergence`: web/api/email/slack → 4 coherent records (open, private, origin-tagged, opaque external requester via one identity directory).
- [x] **Aggregation/search provably excludes unauthorized items** — `test_cc_aggregation_consistency` (docs + risks, no id/title/score leak) + planning `existence_hidden`. Consistent across surfaces.
- [x] **Identity propagates: GitLab audit shows the human, not the gateway** — `test_cc_identity_propagation`: GitLab authority is queried only with the *exchanged* human token; audit records the `sub`. Real-Keycloak exchange is covered by the nightly `@contract` (G-B2, #78).
- [x] **Degraded mode: GitLab down → reads work, writes refused cleanly** — `test_cc_degraded_mode` + `test_degradation*`.
- [x] **Migration round-trips with ID mapping intact** — `test_cc_migration_roundtrip`: Confluence→doc visible in `GET /docs` (read from Git), Jira→ticket readable by opaque requester, old→new mapping resolves.
- [x] **All cross-context interactions examined** — against `specs/cross-context/interactions.md`; see "Seams examined" below.
- [~] **Indexer redundancy (kill one trigger, data still propagates)** — **N/A in spike.** There is no separate index: reads are live from Git (the source of truth), so a stale/missing index cannot serve wrong data, and the "redundancy" the criterion targets has no machinery to fail. The risk critical-webhook is a returned predicate, not a dispatch. Real batch/webhook/separate-sensitive-index behavior is unbuilt → **#84** (INV-IX-2/4).
- [~] **All cross-context Gherkin scenarios pass** — **no bound cross-context Gherkin exists.** `specs/cross-context/interactions.md` is prose; the canonical `specs/features/*.feature` are largely unbound (auditor G-D2). Cross-context coverage here is the `test_cc_*` pytest suite. Binding the canonical features → **#98**.
- [~] **All integration tests pass** — the `@api` cross-context suite passes (207). The `@contract` tier (real Keycloak/OpenFGA/Vault/GitLab) runs nightly/on-demand, not per-PR (G-B1, #76); GitLab + token-exchange contracts are env/version-gated.

## Seams examined (interaction map in `specs/cross-context/interactions.md`)

| Interaction | Status | Note |
|---|---|---|
| Surface → Gateway (OIDC) → token-exchange → GitLab (identity preserved) | ✅ verified | `test_cc_identity_propagation`; real exchange nightly (#78) |
| Inbound email (O365) → Gateway → ticket; threading via Message-ID | ✅ logic verified | the Graph **verdict source** is a stub (no poller) → **#86** |
| Slack reaction → Gateway → draft ticket; identity refused on unmapped | ✅ verified | real Slack API unmodeled → flagged in fidelity |
| Aggregation/search → per-item filter | ✅ verified | docs+risks+planning; search *endpoint* not built (part of #75/#98) |
| Resource change → batch/manual/webhook → index | ⚠️ unbuilt | no real indexer → **#84** |
| GitLab unreachable → reads ok, writes refused | ✅ verified | `test_cc_degraded_mode` |
| MR-required path → direct commit blocked | ⚠️ app-level only | real enforcement is GitLab branch protection (deploy) → **#80** |
| Migration: export → Git → indexed → visible, mapping intact | ✅ verified | `test_cc_migration_roundtrip` |
| Gateway → object store (attachments) | ✅ verified | in-memory object store; participant-only |

No new integration-specific defects were found beyond the seams already tracked by the
auditor issues (#79, #80, #84, #86, #98). No duplicate issues filed.

## Readiness recommendation — **CONDITIONAL GO**

Every cross-context seam that is *buildable in the backend spike* is wired and green.
The fast tiers are deep and the boundaries that have real twins are contract-tested
(nightly). The spike is internally coherent: data crosses boundaries with correct
transforms, identity survives end-to-end, aggregation filters uniformly, and
degradation holds.

**Readiness is gated on a known, ratified deferral set** (the open auditor issues), which
a real v1 cutover must either build or have the Head of Engineering accept as out-of-v1:

1. **#79 — risk + audit on Git / WORM sink.** Risk register and audit log are in-memory; INV-ST-1 (risk mutations as commits) and INV-ID-3 (tamper-evident sink) are not yet real. *Highest-leverage pre-cutover item.*
2. **#86 — O365/Graph poller.** The DKIM/DMARC verdict that INV-EMAIL-1 attribution rests on is an injected assumption; no real poller exists.
3. **#84 — real indexer.** Batch/webhook/separate-sensitive-index machinery is unbuilt; aggregation currently reads live from Git (correct, but the trigger-redundancy guarantee is untested because it has no implementation).
4. **#76 — `@contract` tier in CI.** Now runs nightly; real-boundary fidelity is verified out-of-band, not on every PR. Acceptable if the nightly is watched.
5. **#80 — INV-GOV-1 branch protection** (deploy-time config on the GitLab data repos), **#97 — Playwright e2e**, **#98 — bind canonical cross-context features**, **#75 — search endpoint**, **#91 — `age` break-glass scope**, **#92 — reference render**, **#94 — external-write commit trailer** (blocked on ticket Git persistence).

**Recommendation:** proceed to a `v1 cutover` readiness review with the Head of Engineering
using this list. Items 1–3 are the substantive build-or-accept decisions; the rest are
deploy/frontend/scope. A readiness tag/release should be cut only after that review (the
`v1 cutover` milestone is the tracking home).
