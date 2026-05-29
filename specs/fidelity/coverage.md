# Phase 1 — Coverage inventory (depth per test)

Depth scale: NONE · STUB · SHALLOW (status/bool/mock-called) · MODERATE (real values via stubbed externals) · THOROUGH (real/faithful code, actual state) · INTEGRATION (real services).

All `@api` tests run in-process via FastAPI `TestClient` over **faithful** components (real `git`, real `FernetCrypto`, real `IdentityDirectory`/stores, `FakeOpenFga` with real union logic). None are true INTEGRATION — that tier is the dormant `@contract` set (`boundaries.md`).

## Feature-binding map (important structural finding)

Only **5** features are executable; they live in `api/tests/features/` and are bound by `scenarios()`:

| Bound test feature | Step file |
|---|---|
| `ticket_lifecycle.feature` | `test_ticket_lifecycle.py:15` |
| `ticket_create.feature` | `test_ticket_create.py:14` |
| `docs_read.feature` | `test_docs_read.py:13` |
| `planning.feature` | `test_planning.py:19` |
| `tickets_read.feature` | `test_tickets_read.py:16` |

The canonical analyst set `specs/features/` (12 files) is a **different, larger** set. Only `planning` and `ticket_lifecycle` share a name. **Unexecuted as Gherkin:** `aggregation_permissions`, `data_protection`, `degradation`, `docs`, `migration`, `orphan_detection`, `portal`, `risk_register`, `slack_capture`, `ticket_origins`. Their *behavior* is largely covered by integration tests (below), but the canonical scenarios — including `@e2e`-tagged ones — never run.

## Access / authority / identity

- `unit/test_authority.py:12,18` — THOROUGH — `can_read` positive + negative (other space `False`, unknown principal reads nothing). Real `Authority`.
- `unit/test_ticket_authority.py:25,32` — THOROUGH — requester+watcher set = `{ticket-1,ticket-2}`, stranger `can_read False`; agent sees all. Real composition over `FakeOpenFga`.
- `unit/test_openfga_mapping.py:6,11` — MODERATE — id prefix + `strip_type` roundtrip (pure fns).
- `unit/test_oidc.py:44–82` — THOROUGH — real RS256 JWTs: valid→sub, principal=sub-not-username (G2-05), and **5 negatives** (tampered, wrong key, expired, wrong aud, wrong iss).
- `integration/test_oidc_gateway.py:52` — THOROUGH — valid bearer → filtered `{doc-a}`. `:59,:63` — SHALLOW (401 status, acceptable boundary). `:67` — MODERATE — spike header ignored when authenticator on (INV-ACC-1).
- `integration/test_gateway_identity_security.py:18` — MODERATE — no-authenticator → `ValueError` (fail-closed start). `:47` — THOROUGH — non-agent forging requester → 403. `:58,:66` — THOROUGH — requester bound to principal / agent on-behalf. `:87` — THOROUGH — 5xx on `/docs` is audited (INV-ID-3 5xx path). `:24` — SHALLOW (opt-in 200).
- `integration/test_composed_authority.py:54` — THOROUGH — docs filtered by live membership = `{doc-a}`, no-membership → `[]`, hidden doc → 404. `:64` — THOROUGH — epics filtered, `epic_count==1`, locked group excluded (INV-AGG). `:74,:92` — MODERATE — RFC 8693 request shape / 400→AuthError (stubbed httpx).
- `integration/test_composed_authority_hardening.py:37` — THOROUGH — membership cached across 3 requests (`gitlab.calls==1`, AR-08). `:50` — MODERATE — partial config fails loud. `:30` — MODERATE (TtlCache). `:57` — SHALLOW (construction only).
- `integration/test_planning_security.py:34` — THOROUGH — cursor pagination + totals over all-visible (`epic_count==5`, `total_capacity==50`). `:69` — THOROUGH — `never_indexed`/`as_of` signalled. `:52,:60` — MODERATE (422 / fail-loud).
- `integration/test_validation_privacy_security.py:71,79,86` — THOROUGH — community viewer sees `requester is None`, agent/requester see it, listing redacts (G2-06). `:31–50` — MODERATE (422 validation).
- `integration/test_ticket_access_fixes.py:46` — THOROUGH — stranger → 404 on private ticket (no existence leak). `:27,:35` — MODERATE (200 only).
- `features/test_tickets_read.py` / `test_docs_read.py` / `test_planning.py` — THOROUGH — include/exclude steps are real negatives. **`test_planning.py` `existence_hidden` step is the strongest INV-AGG proof**: asserts hidden `epic_id` absent from `json.dumps(body)`, `epic_count == len(readable)`, and capacity excludes the hidden value.

## Service desk: lifecycle / create / email / slack / encryption

- `unit/test_lifecycle.py:12,17` — THOROUGH — all 4 legal transitions; illegal (open→closed, closed→resolved) raise.
- `features/test_ticket_lifecycle.py` (`ticket_lifecycle.feature`) — THOROUGH — resolve→close state check; illegal transition 409 + status unchanged; non-agent 403; promote-unresolved 409; **resolve→promote→reopen asserts `community_visible` flips back to `False`** (INV-LC-2 re-gate, `:77`).
- `features/test_ticket_create.py` — MODERATE — origin normalization checks response JSON (not stored record).
- `unit/test_email_routing.py:14–45` — THOROUGH — token extract; structural-only parse (`not hasattr(e,"verified")`); verified-match→append; mismatch→quarantine; **unverified-always→quarantine** (negative).
- `integration/test_email_ingest.py:58,69,79,88,99` — THOROUGH — opaque requester (no `@`); **forged `dmarc=pass` ignored → quarantine, `store.all()==0`**; unverified first-contact → quarantine; numeric token threads real ticket (no dup); spoofed verified sender → quarantine. `:110` — SHALLOW (413).
- `integration/test_slack_capture.py:53,65,74,81,90` — THOROUGH — requester=author (opaque), capturer recorded separately, **unmapped reactor → refused, `store.all()==[]`** (INV-ID-2), rate-limit (6th refused, 5 stored), link requires visibility.
- `integration/test_ticket_encryption.py:43,54,62,70` — THOROUGH — ciphertext at rest decrypts via Gateway, cleartext stays plain, encrypt-after-create → 409 (create-time only), **erasure crypto-shreds → `[unrecoverable...]`**.
- `integration/test_crypto_hardening.py:29,65,71` — THOROUGH — prod requires durable crypto (`ValueError`); missing key → `DecryptionUnavailable` (permanent); **503 → raised but NOT `DecryptionUnavailable`** (transient ≠ shredded). `:36,:80` — SHALLOW.

## Data protection / migration / orphans / degradation

- `integration/test_erasure.py:58` — THOROUGH — post-erasure: `email_for(opaque) is None`, `list_readable(opaque)==set()` (tuples gone), `store.get(ticket) is not None` (Git intact), `"Git history" in residual`. `:77` — THOROUGH — quarantine PII scrubbed. `:105` — THOROUGH — idempotent re-run (`relations_purged==0`). `:52` — SHALLOW (403). **Crypto-shred not exercised here** (`_ctx` builds no crypto).
- `integration/test_migration.py:53,66,77,85` — THOROUGH — opaque requester + mapping resolves; **re-run `migrated==0, skipped==1, len==1`** (no dup); non-curated archived (resolve 404); Confluence→doc in real Git.
- `integration/test_migration_idempotency.py:28,40` — THOROUGH — **fresh-IdMap restart** (two pipelines, shared store) → no duplicate; deterministic id stable.
- `integration/test_orphan_detection.py:42–116` — THOROUGH — full positive+negative matrix (owner lacking write, read-only-not-write, archived-space override, closed-not-flagged, departed/long-unassigned, desk-scoped, maintainer-filtered). No explicit "owner unchanged" assertion (relies on report being ids-only).
- `integration/test_degradation.py:29,42,54` — THOROUGH — **read served while `gitlab_up=False`** + perms still hold; **ticket create → 503 "unavailable"** (not false success); inbound email → 503 "O365" (INV-DEG-2).
- `integration/test_degradation_hardening.py:21` — THOROUGH — reads survive via last-known (`gitlab.calls==0` during outage). `:51,:68` — SHALLOW — slack_link/migration → 503 **status only** (no "nothing was created" state check).
- `integration/test_portal.py` / `test_portal_hardening.py` — THOROUGH — community search `{ticket-pub}` only, no `requester` leak; attachment `obj://` (object storage); stranger 404; encrypted excluded from search; participant-only attach; `.exe` → 415.

## Storage / docs / risk / indexing

- `integration/test_git_store.py:7,20` — THOROUGH — real `git` repo; valid docs read, invalid (no `schema_version`) quarantined; body parsed. `:12` — MODERATE — timestamps **non-null only** (doesn't assert `updated` advances on edit; INV-ST-5 weak).
- `integration/test_docs_write.py:38,60` — THOROUGH — write→commit→re-read v1/v2 with `base_rev`; stripped `schema_version` → 422. `:54` — MODERATE — governed path → 409 (app-level `MRRequired`, **not** branch protection). `:65` — SHALLOW (403).
- `integration/test_docs_rewrite.py:28` — THOROUGH — identical re-write → 200 (real `git diff --quiet` no-op branch).
- `integration/test_doc_write_integrity.py:40,47` — THOROUGH — duplicate id different path → 409 (INV-ST-4 uniqueness); stale `base_rev` → 409 (INV-ST-6 conflict). **Does not** assert structured-field conflict surfaced (only blocks).
- `integration/test_doc_write_security.py:45,55,62,70` — THOROUGH — path-traversal → 422 (G2-01); alias bomb raises; oversized raises; 6-thread concurrent writes all 200 (lock path). `:49` — MODERATE (loose `in (403,409)`).
- `integration/test_folder_structure.py:7,17` — THOROUGH — nested hierarchy + per-folder attachments exclude `.md`.
- `integration/test_audit.py:20,27` — MODERATE — events captured (`principal`,`resource`,`result`) but **in-memory sink** (not WORM/hash-chain).
- `integration/test_risk_assess_api.py:17` — THOROUGH — derived `score==20`, `severity=="critical"`, `fires_critical_webhook` driven by **category not severity** (INV-IX-1). But **flag only** — no dispatch.
- `integration/test_risk_persistence_api.py:25,33,45` — MODERATE — **in-memory `RiskStore`**; cross-space exclusion (`rid not in other`) but no count/score-leak assertion. `:41` — SHALLOW (403).
- `unit/test_frontmatter.py:20,28` / `test_frontmatter_malformed.py:9` — THOROUGH — parse + reject-missing-schema_version + malformed→typed error (→422 not 500).
- `unit/test_governed_paths.py:8,13` — MODERATE/THOROUGH — prefix match + non-substring guard.
- `unit/test_risk_register.py:14–30` — THOROUGH — security/compliance fire; **high-score delivery does NOT fire** (INV-IX-1); **escalation creates org duplicate with `escalated_from`, original untouched** (INV-LC-4).
- `unit/test_scoring.py:13,17` — THOROUGH — all severity-band boundaries; derived score.

## Notable over-stubbing / shallow spots

- **Risk register is in-memory** (`risk/store.py:5`) — every risk test asserts dict behavior while the invariants claim Git persistence (INV-ST-1). Biggest over-stub.
- **Audit sink is in-memory** (`access/audit.py`) — INV-ID-3 "integrity-protected, hash-chained/WORM" is asserted only as append.
- **Webhook "firing" is a returned bool** — INV-IX-1 verifies the predicate, never an actual near-real-time dispatch.
- **slack_link / migration outage refusal** (`test_degradation_hardening.py:51,68`) assert 503 status but not the "nothing created" state — thin for INV-DEG-1's "never silently dropped".
- Construction-only / 413 / 403 status-only tests are legitimate guard-rails but provide no state depth.
