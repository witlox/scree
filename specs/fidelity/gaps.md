# Phase 4 — Gaps, cross-cutting, priority

Ranked by blast radius if the unenforced behavior breaks. Each gap routes to the implementer as a `type:bug` / `phase:auditor` issue (the auditor measures; it does not fix). IDs: **G-A** authz/correctness, **G-B** boundary, **G-C** infra/over-stub, **G-D** cross-cutting.

## Critical / High

### G-A1 — INV-AGG canonical spec is unexecuted; risk + search aggregation under-tested · **severity:high**
`aggregation_permissions.feature` (the load-bearing INV-AGG spec: metadata-leak-in-counts/titles, separate sensitive-category index, stale-cache-fails-closed) has **no `scenarios()` binding** — it is unexecuted prose. Aggregation IS enforced for **planning** (`test_planning.py` `existence_hidden`) and **docs/epics** (`test_composed_authority.py:54,64`) with true negatives. But **risk-register aggregation** is only MODERATE (`test_risk_persistence_api.py:33`, in-memory, asserts id-absence but not count/score/metadata non-leak), and **search-view filtering** has no test at all.
- Action: bind `aggregation_permissions.feature` with executable steps incl. the negative leak cases; add a risk-aggregation test asserting no count/score/title of an unauthorized risk is exposed; add search-endpoint per-item filtering.

### G-B1 — `@contract` tier never runs in CI · **severity:high**
`.github/workflows/ci.yml:21` installs no `testcontainers`; all 12 contract tests skip at collection. Every FAITHFUL boundary rating (OpenFGA, OIDC, Vault) is **unverified in the pipeline**; PARTIAL/DIVERGENT seams are wholly invisible. A stub diverging from a real API would never be caught by CI.
- Action: add a gated job (nightly or `contract`-labelled) that installs `testcontainers` + provisions Docker and runs `pytest -m contract`. Keep it non-blocking on PRs if runtime is a concern, but it must run *somewhere*.

### G-A2 — INV-ACC-5 (fail-closed) vs INV-DEG-1 (last-known) tension, untested · **severity:high**
`app.py:281–282` serves `_last_spaces.get(token, set())` during a GitLab outage so reads survive (G12-01). `_last_spaces` is an unbounded dict with **no TTL** — a user whose GitLab access was revoked just before an outage keeps reading those spaces for the **entire outage window**. INV-ACC-5 says a stale cache "fails closed"; the outage path does the opposite, by design, and neither behavior has a test.
- Action: ratify the trade-off explicitly (cross-reference INV-ACC-5 ↔ INV-DEG-1 in `invariants.md`); bound the staleness (TTL/max-age on `_last_spaces`); add tests pinning the chosen behavior for the revoked-then-outage case.

### G-B2 — Keycloak token-exchange (RFC 8693) has zero contract coverage · **severity:high**
`KeycloakTokenExchanger` (`token_exchange.py:34`) ships real `httpx` code validated only by unit request-shape tests. Token exchange is a feature-flagged Keycloak endpoint with a quirky contract; INV-ID-1 ("GitLab audit shows the human") rests entirely on it. This was explicitly deferred in PR #66.
- Action: add `test_keycloak_token_exchange.py` `@contract` — boot Keycloak with token-exchange enabled, provision a permitted client + target-audience client, mint a subject token, assert `exchange()` returns a downstream token; skip-on-failure so CI stays green.

## Medium

### G-C1 — Risk register & audit sink are in-memory · **severity:medium**
`RiskStore` (`risk/store.py:5`) is a dict; the audit sink (`access/audit.py`) is in-memory. So INV-ST-1 ("every mutation is a commit") is **not** exercised for risks, INV-LC-3 (closed-via-MR) cannot be, and INV-ID-3 "integrity-protected, hash-chained/WORM" is asserted only as append.
- Action: back risks with the Git store (as docs are) or explicitly scope the in-memory store out of INV-ST-1 in the spec; realize the WORM/hash-chain audit sink or mark it a ratified deploy-time gap.

### G-A3 — INV-GOV-1 mechanism untested · **severity:medium**
The real enforcement (GitLab branch protection + CODEOWNERS) is config with **no test**; only the bypassable app-level `MRRequired` → 409 is covered (`test_docs_write.py:54`). A direct `git push` skips the Gateway entirely.
- Action: a config-lint or GitLab `@contract` asserting protected paths reject non-MR pushes.

### G-A4 — INV-LC-2 snapshot fidelity untested · **severity:medium**
Only the `community_visible` boolean is tested. "**Curated snapshot, not the live thread / later private replies/attachments**" and the audit-trail are unasserted — a live-thread leak on promote would pass.
- Action: test that a promoted ticket exposes a frozen snapshot and that later private replies/attachments do not appear in the community view.

### G-A5 — INV-MIG-4 atomicity untested · **severity:medium**
No test asserts a migrated ticket gets its OpenFGA `requester` tuple, and no mid-migration-failure test proves atomic repair. A partial migration (Git written, tuple missing) passes today → dangling/absent authority on imported identities.

### G-A6 — INV-LC-3 (closed-risk via MR) entirely unenforced · **severity:medium**
No test creates or transitions a risk to `closed`. (Compounded by G-C1 — risks aren't on Git, so the MR path can't be exercised.)

### G-A7 — INV-IX-2 / INV-IX-4 unenforced · **severity:medium**
The batch-as-correctness-backstop (INV-IX-2) and separate sensitive-category index (INV-IX-4) have no tests; the webhook is only a returned bool, never dispatched/reconciled.

### G-B3 — GitLab `readable_spaces` pagination untested against real GitLab · **severity:medium**
`test_gitlab_rbac.py` only covers `can_read`; the `_paginate`/`x-next-page` loop (`gitlab.py:34–50`) that backs INV-AGG is never run against real GitLab. A pagination bug silently truncates readable spaces.

### G-B4 — O365/Graph DKIM/DMARC verdict seam unmodeled · **severity:medium**
INV-EMAIL-1 attribution rests on a trusted verdict that is *assumed* (injected param); no Graph poller code or contract confirms it is actually trustworthy.

## Low

- **G-A8 — INV-ST-4** id-immutability & Gateway-allocated per-kind sequence untested (ids author-supplied). · low
- **G-A9 — INV-ST-5** timestamp-projection is non-null-only; no "updated advances on edit" / "authored timestamp rejected". · low
- **G-A10 — INV-ST-6** conflict-*surfacing* clause untested (only stale-rev blocking). · low
- **G-A11 — INV-ENC-3** metadata-only indexing & neutral-title placeholder untested. · low
- **G-A12 — INV-ENC-4 / ADR-0008** client-side `age` break-glass path **unimplemented**, untested. · low (scope question)
- **G-A13 — INV-REF-3/5** reference "unavailable" rendering & `target_id` withholding untested. · low
- **G-A14 — INV-ACC-4** org tag grants no access — no test. · low
- **G-A15 — INV-ID-4** external-write-by-desk-SA / commit-trailer identity — no test. · low
- **G-A16 — INV-DEG-1** slack_link/migration outage refusal asserts 503 status only, not "nothing created". · low
- **G-A17 — INV-ORPH** "never auto-reassign" has no explicit owner/assignee-unchanged assertion. · low
- **G-D1 — ADR-0004** Playwright e2e tier absent; `@e2e`-tagged scenarios (in unbound features) never run. · low
- **G-D2** — 10 of 12 canonical `specs/features/*.feature` files are unexecuted prose (behavior covered by integration tests, but the canonical scenarios drift from what runs). Decide whether `specs/features/` or `api/tests/features/` is authoritative and reconcile. · low

## Cross-cutting summary

- **Tag gates without gated tests:** the `contract` marker is declared but never selected/excluded in CI → inert. The `@e2e` tag has no runner.
- **Orphan / dead specs:** `aggregation_permissions`, `data_protection`, `degradation`, `docs`, `migration`, `orphan_detection`, `portal`, `risk_register`, `slack_capture`, `ticket_origins` `.feature` files have no step bindings.
- **Over-stubs (acceptable but bounding depth):** in-memory `RiskStore`, in-memory audit sink, bool-only webhook "firing".
- **What's genuinely strong** (do not regress): real-`git` doc/Git path, OIDC negative matrix, email verification negatives, erasure completeness, migration idempotency, planning INV-AGG existence-hiding, degradation read-survives/write-refused.

---

## Resolution (2026-05-29, fix/auditor-findings)

Per project policy (fix all findings; severity sets order, not whether) the
backend-tractable gaps were fixed; the rest are flagged with a concrete blocker
(issue stays open). Suite after fixes: **201 @api/unit passed** (+14); the
`@contract` tier collects (+3) and now has a nightly CI job.

**Fixed (14):**
- **G-A2** — last-known membership bounded by `LAST_KNOWN_MAX_AGE`; past the bound the resolver fails closed (INV-ACC-5). `test_membership_staleness.py`. INV-ACC-5↔INV-DEG-1 tension documented in code.
- **G-A4** — `promote_community_visible` freezes a curated snapshot; community-only viewers + the public KB read the snapshot, not the live thread; reopen discards it. `test_community_snapshot.py`. **INV-LC-2 now ENFORCED.**
- **G-A8** — id-immutability guard on doc update (`IdChanged`→409). `test_doc_st_invariants.py`. **INV-ST-4 ENFORCED.**
- **G-A9** — created/updated projection + `updated` advances on edit (controlled-date Git). **INV-ST-5 ENFORCED.**
- **G-A10** — stale write surfaced as Conflict, prior content preserved (never silently merged). **INV-ST-6 surfacing ENFORCED.**
- **G-A11** — encrypted ticket body never enters the public KB index. `test_enc_metadata_only.py`. **INV-ENC-3 ENFORCED.**
- **G-A14** — same-org customer cannot read another's ticket. `test_org_tag_access.py`. **INV-ACC-4 ENFORCED.**
- **G-A16** — outage write-refusal now asserts no comment/ticket created (not just 503). `test_degradation_state.py`.
- **G-A17** — orphan refresh flags but leaves owner/assignee unchanged. `test_orphan_no_reassign.py`.
- **G-A5** — migrated requester can read their ticket (OpenFGA tuple populated). `test_migration_authority.py`. (Mid-failure *atomicity* still relies on idempotent re-run repair — documented.)
- **G-A1** *(partial)* — risk-register no-metadata-leak test added (`test_risk_aggregation_leak.py`). **Search-view filtering + binding `aggregation_permissions.feature` remain open** (no search endpoint yet) → tracked under G-D2.
- **G-B1** — nightly + on-demand `contract-tests` CI job runs `pytest -m contract` with `testcontainers` (`.github/workflows/ci.yml`).
- **G-B2** — `test_keycloak_token_exchange.py` (RFC 8693 against real Keycloak, skip-on-unsupported-config).
- **G-B3** — `test_gitlab_pagination.py` exercises `readable_spaces` across an `x-next-page` boundary (`per_page` made configurable).

**Flagged — open, with blocker:**
- **G-C1** — ✅ **resolved (2026-05-29):** `GitBackedRiskStore` persists risk mutations as Git commits (INV-ST-1) and is rebuildable from Git (INV-ST-2); the `AuditSink` is now hash-chained and tamper-evident with `verify()` (INV-ID-3 integrity, AR-10). The durable WORM *medium* remains a deploy concern; the integrity *mechanism* is in code. Unblocks **G-A6/#83** (close-via-MR now has a Git-backed risk to gate).
- **G-A6** — closed-risk-via-MR: blocked on G-C1 (risks not on Git).
- **G-A15** — external-write desk-SA commit trailer: blocked on ticket Git persistence.
- **G-A3** — INV-GOV-1: real enforcement is GitLab branch protection + CODEOWNERS on the *runtime data repos*, not this build repo; a CODEOWNERS here would enforce nothing. Deploy concern + a CODEOWNERS template is the right artifact.
- **G-A7** — ✅ **resolved (2026-05-29, #84):** real indexer (`indexing/index.py`) with the three triggers — `POST /index/reindex` (batch + manual, rate-limited per INV-IX-3), `POST /index/events` (critical webhook, INV-IX-1, idempotent re-read), and a separate sensitive partition (INV-IX-4); a missed webhook is caught by the next rebuild (INV-IX-2). `GET /search` queries it with the per-item INV-AGG filter. The live GitLab webhook delivery is a deploy concern; the trigger logic + redundancy are tested.
- **G-A13** — INV-REF render layer (unavailable / opaque target_id): needs a reference-resolution feature.
- **G-B4** — ✅ **resolved (2026-05-29, #86):** `integration/o365/poller.py` models the seam — the DKIM/DMARC verdict is read from OUR mail infra's `Authentication-Results` (its `authserv-id`); attacker-embedded A-R (any other authserv-id) is ignored (G4-01), and the poll→ingest flow drives INV-EMAIL-1 (trusted pass → attribute; else quarantine). The live Microsoft Graph delta/subscription fetch is a deploy concern (RealGraphClient); the verdict logic + flow are tested.
- **G-A12** — ADR-0008 client-side `age` break-glass: v1 scope question (ratify before building).
- **G-D1** — Playwright e2e tier: frontend infra (`web/` uses vitest only).
- **G-D2** — reconcile `specs/features/` vs `api/tests/features/` authority + bind the canonical features (incl. `aggregation_permissions.feature`): structural decision.
