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
