# Fidelity Index

Last checkpoint: 2026-05-29 (**REFRESH** — full-stack)
Status: CHECKPOINT — baseline gaps largely resolved; frontend now measured (`frontend.md`)
Scope: `api/` backend **+ `web/` frontend**. Suite now — **233 @api/unit passed**;
`@contract` tier **7 files** runs nightly/on-demand; **web: 42 passed**.

> The auditor measures; it does not fix. Gaps route to the implementer (see `gaps.md`).
> Detail: Phase 1 depth → `coverage.md` · frontend → `frontend.md` · Phase 2 boundaries
> → `boundaries.md` · Phase 3 enforcement → `enforcement.md` · Phase 4 + priorities → `gaps.md`.

## Refresh checkpoint (2026-05-29) — what changed since the baseline

The baseline's three structural gaps and most of the 24 findings are **resolved**:

1. **`@contract` tier now runs** — a nightly/on-demand CI job runs `pytest -m contract`
   (G-B1); the tier grew to 7 files (added Keycloak token-exchange G-B2 and GitLab
   `readable_spaces` pagination G-B3). Real-boundary drift is now detectable out-of-band.
2. **Risk + audit are no longer in-memory** — `GitBackedRiskStore` (risk mutations are
   commits, INV-ST-1; rebuildable, INV-ST-2) and a **hash-chained** audit sink with
   `verify()` (INV-ID-3 integrity). (#79)
3. **Real indexer** (#84) — three triggers (batch/manual rate-limited + critical webhook),
   separate sensitive partition, batch-catches-missed-webhook redundancy (INV-IX-1/2/3/4),
   and a `GET /search` with the per-item INV-AGG filter.
4. **O365/Graph verdict modeled** (#86) — the DKIM/DMARC verdict is read from our mail
   infra's `Authentication-Results`; attacker-embedded A-R is distrusted (INV-EMAIL-1/G4-01).
5. **Frontend measured + adversary-hardened** — 42 web tests; Frontend Gate 1's 10
   findings (auth race FE-01, etc.) all resolved. See `frontend.md`.

**Still open (none are substantive code gaps):** G-A3 (GitLab branch-protection — deploy
config), G-A6/#83 (closed-risk-via-MR endpoint — now buildable on Git-backed risks, not
yet built), G-A12 (`age` break-glass — v1 scope question), G-A13 (reference-render
feature), G-A15 (commit trailer — blocked on ticket Git persistence), G-D1/#97 (Playwright
e2e), G-D2/#98 (bind canonical features), and the standing **live browser+Keycloak+GitLab
verification** (the top cross-cutting gate — what the mocked tests and nightly-only
contract tier cannot prove).

— The sections below are the **baseline** measurement; the deltas above supersede them. —

## Headline

The fast tiers (unit + `@api`) are **genuinely deep** — faithful in-process fakes, real Git, real JWT/Fernet crypto, real negative/exclusion assertions. The depth problem is not shallow assertions; it is **three structural gaps**:

1. **The `@contract` tier never runs in CI** — 0 of 12 contract tests execute (`.github/workflows/ci.yml:21` installs no `testcontainers`). Every real-boundary fidelity check is dormant. Boundary drift is undetectable in the pipeline.
2. **The canonical `specs/features/*.feature` set is not the executed BDD set.** Only 5 features are bound via `scenarios()` (from a *separate* `api/tests/features/*.feature` copy). 10 of the 12 canonical analyst features — including `aggregation_permissions.feature` (the load-bearing INV-AGG spec) — have **no executable binding**. Their behavior is mostly covered by integration tests, but the canonical scenarios are unexecuted prose.
3. **Risk + audit + token-exchange paths are in-memory / unvalidated against their real substrate.** `RiskStore` is a dict (`risk/store.py:5`), the audit sink is in-memory (not WORM/hash-chain), and `KeycloakTokenExchanger` ships real HTTP code with zero contract coverage.

## Summary — depth by context

| Context / Module | Tier | Dominant depth | Notable gaps | Confidence |
|---|---|---|---|---|
| Knowledge / docs / Git | unit + @api (real `git`) | THOROUGH | id-immutability, timestamp-projection, conflict-surfacing | **High** |
| Access / authority / OIDC | unit + @api (faithful fakes) | THOROUGH | real GitLab union only at dormant @contract | High (fast) / Med (real) |
| Service desk lifecycle | @api (real service) | THOROUGH | snapshot-fidelity of `community_visible` | High |
| Inbound email | unit + @api | THOROUGH | Graph verdict seam unmodeled | High |
| Slack capture | @api | THOROUGH | real Slack API unmodeled | High |
| Encryption / crypto-shred | @api (real Fernet) | THOROUGH | metadata-only indexing (INV-ENC-3), rotation (INV-ENC-4) | High |
| Data protection / erasure | @api | THOROUGH | crypto-shred not in erasure suite | High |
| Migration | unit + @api (real Git) | THOROUGH | atomic OpenFGA tuple population (INV-MIG-4) | High |
| Orphan detection | @api | THOROUGH | no "owner unchanged" assertion | High |
| Degradation | @api | THOROUGH | slack_link/migration refusal is status-only | Med-High |
| Planning / aggregation | @api (strong negative) | THOROUGH | — | High |
| Risk register | @api (**in-memory store**) | MODERATE | no Git persistence; INV-LC-3 absent | **Low-Med** |
| Audit sink | @api (**in-memory**) | MODERATE | no WORM/hash-chain; reads/agg not audited | Low-Med |
| References (INV-REF-*) | — | **NONE** | no reference-render tests | **Low** |

## Boundary fidelity (Phase 2)

| Seam | Fake / stub | Real | @contract | Rating |
|---|---|---|---|---|
| OpenFGA ReBAC | `access/openfga.py:32` | `:65` | `test_openfga_contract.py` (n=120 purge, ListObjects) | **FAITHFUL** |
| OIDC auth | (none; header path) | `access/oidc.py:10` | `test_keycloak_oidc.py` (real JWKS) | **FAITHFUL** |
| Vault Transit crypto | `crypto/transit.py:24` | `:53` | `test_vault_transit.py` (destroy→shred) | **FAITHFUL** (5xx-retryable branch untested) |
| GitLab membership | `access/gitlab.py:63` | `:17` | `test_gitlab_rbac.py` (only `can_read`) | **PARTIAL** (`readable_spaces` pagination untested) |
| Token exchange (RFC 8693) | `token_exchange.py:19` | `:34` | **NONE** | **DIVERGENT** |
| O365 / Graph inbound | `o365/inbound.py` (parser only) | does not exist | **NONE** | **DIVERGENT** |
| Slack capture | `slack/capture.py` (in-mem) | does not exist | **NONE** | **DIVERGENT** |

**All `@contract` tests are inert in CI** (`ci.yml:21` omits `testcontainers`; tests `pytest.importorskip`-skip). The FAITHFUL ratings only hold *when run locally with Docker*.

## Decision / invariant enforcement (Phase 3 — abridged; full table in `enforcement.md`)

Critical invariants (per `specs/invariants.md` severity guidance: INV-AGG, INV-ACC-*, INV-ID-2):

| Invariant | Statement (1-line) | Status |
|---|---|---|
| INV-AGG | Aggregation returns a subset of directly-readable; no metadata leak | **PARTIAL** — ENFORCED for planning/docs (true negatives); risk-register MODERATE; **search + separate-sensitive-index UNENFORCED** |
| INV-ACC-1 | All access Gateway-mediated; no bypass | ENFORCED |
| INV-ACC-2 | Authority = GitLab RBAC ∪ ticket ReBAC | ENFORCED (fakes); real GitLab union at dormant @contract |
| INV-ACC-3 | Ticket readable only by participants / community | ENFORCED |
| INV-ACC-4 | Org tag grants no access | **ENFORCED** (G-A14: `test_org_tag_access.py`) |
| INV-ACC-5 | Stale permission cache fails closed | **ENFORCED (bounded)** — G-A2: last-known bounded by `LAST_KNOWN_MAX_AGE`, fails closed past it; tension with INV-DEG-1 documented |
| INV-ID-1 | GitLab actions carry the human via token exchange | ENFORCED at unit/@api; real exchange **DIVERGENT** (no @contract) |
| INV-ID-2 | Unmappable Slack action refused | ENFORCED |
| INV-ID-3 | Every action audited to integrity-protected sink | **PARTIAL** — writes/5xx audited; reads+agg not; sink in-memory (no WORM/hash-chain) |
| INV-ID-4 | External writes by desk SA, identity in trailer | **UNENFORCED** (no test) |

Highest-blast-radius UNENFORCED across the full set: **INV-GOV-1** (MR-required branch protection — mechanism entirely untested, bypassable by direct push), **INV-LC-3** (closed-risk-via-MR — no test), **INV-IX-2/4** (batch backstop, sensitive separate index — no test), **INV-ST-2** (rebuildable-from-Git — no test).

ADR enforcement: ADR-0005/0006/0007 ENFORCED at fast tier; **ADR-0008 client-side `age` break-glass UNIMPLEMENTED**; ADR-0004 Playwright e2e tier **absent**; ADR-0010 deployment items (WORM audit, health probe, DR) documented-only by design.

## Priority actions

1. **Make the `@contract` tier run in CI** (or a gated nightly) — without it, every FAITHFUL rating is unverified and drift is invisible. Highest leverage. → `gaps.md` G-B1.
2. **Bind `aggregation_permissions.feature` (INV-AGG) to executable steps**, with the metadata-leak / separate-sensitive-index / stale-cache negatives — the load-bearing invariant's canonical spec is unexecuted. → G-A1.
3. **Add the Keycloak token-exchange `@contract`** (RFC 8693) — the one seam shipping real HTTP code with zero real-boundary validation. → G-B2.
4. **Resolve the INV-ACC-5 ↔ INV-DEG-1 tension** (`app.py:281-282` serves stale grants for the whole outage window; `_last_spaces` has no TTL) — ratify the trade-off and add tests for the chosen behavior. → G-A2.
5. **Move risk + audit off in-memory stores** (or explicitly scope them out) so INV-ST-1 / INV-ID-3 integrity are actually exercised. → G-C1.
