# Implementation Gate 10 — Adversary Findings

Adversarial pass over the migration slice merged in PR #68 (`migration/`, Gateway
`/migration/run` + `/migration/resolve`). Primary target: idempotency durability
(INV-MIG-2) — does re-running really avoid duplicates under failure/restart?

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G10-01: Idempotency keyed on the in-memory IdMap → re-run after restart duplicates everything
- **Severity:** Medium
- **Category:** Correctness > idempotency durability (INV-MIG-2)
- **Location:** `api/scree/migration/pipeline.py:run` (`if self._idmap.has(key): skip`); `migration/models.py:IdMap` (in-memory)
- **Spec reference:** INV-MIG-2 (re-running creates no duplicates); INV-ST-2 (Git is truth; the index/map is derived)
- **Description:** Idempotency is decided by `IdMap.has(key)`, but the `IdMap` is
  in-memory and dies with the process. A big-bang migration re-run **after a
  restart** (or on another replica) sees an empty map and re-creates **every**
  ticket/doc — duplicating the whole import. The durable substrate (the created
  tickets/docs in Git) should be the idempotency source, not a volatile map.
- **Evidence:** run migration; restart; run again → every issue migrates a second time.
- **Suggested resolution:** Make idempotency derive from durable state: use a
  deterministic new id per legacy id and skip if that target already exists in the
  store (the map becomes a rebuildable cache, per INV-ST-2).

## Finding G10-02: Migration steps aren't atomic → a mid-item failure duplicates on re-run
- **Severity:** Medium
- **Category:** Correctness > atomicity (INV-MIG-4 "atomically")
- **Location:** `api/scree/migration/pipeline.py:_migrate_ticket` (create → add_comment → record, sequential)
- **Spec reference:** INV-MIG-4 (Git + identity + OpenFGA populated atomically); INV-MIG-2
- **Description:** `_migrate_ticket` creates the ticket (and OpenFGA grant), then
  adds the comment, then records the mapping. If anything fails after create but
  before `record`, the ticket exists with no mapping; the next run (mapping absent)
  creates a **second** ticket — a duplicate. Idempotency hinges on the last step
  succeeding, which isn't guaranteed.
- **Evidence:** inject a failure between create and record → re-run produces two
  tickets for one legacy id.
- **Suggested resolution:** Tie creation to a deterministic id and check existence
  first (same fix as G10-01), so a re-run repairs the mapping instead of duplicating;
  longer term, make the multi-store write transactional/compensating.

## Finding G10-03: Confluence item without a doc_writer is counted as migrated but actually archived
- **Severity:** Low
- **Category:** Correctness > reporting accuracy
- **Location:** `api/scree/migration/pipeline.py` (`run` increments `migrated` after `_migrate_doc`, which silently archives when `doc_writer is None`)
- **Spec reference:** INV-MIG-1/3
- **Description:** When no `doc_writer` is configured, `_migrate_doc` archives the
  page and records no mapping, but `run` has already counted it as `migrated`. The
  summary overstates migration, and the item is silently archived with no mapping —
  a later legacy-link resolve 404s though the run reported success.
- **Evidence:** run a confluence item with `doc_writer=None` → summary `migrated:1`
  but `resolve` 404s.
- **Suggested resolution:** Count by actual outcome (migrated vs archived), and make
  a missing doc_writer an explicit, surfaced decision rather than a silent fallback.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G10-01 | Medium | Correctness/idempotency | Idempotency keyed on in-memory IdMap → re-run after restart duplicates everything |
| G10-02 | Medium | Correctness/atomicity | Non-atomic migration → mid-item failure duplicates on re-run |
| G10-03 | Low | Correctness/reporting | Confluence-without-doc_writer counted migrated but archived |

**Counts:** 0 critical · 0 high · 2 medium · 1 low — **3 total.** No `gate:blocking`.

**Highest-risk area:** idempotency durability — both mediums make INV-MIG-2's
no-duplicate guarantee depend on volatile state / step ordering rather than the
durable substrate.

**Resolution (2026-05-28) — all 3 resolved (PR #69):**
- G10-01/02 — migration uses a deterministic ticket id per legacy id and checks the durable store for existence before creating, so a re-run (even with a fresh in-memory IdMap after a restart, or after a mid-item failure) repairs the mapping instead of duplicating. Confluence re-migration catches Conflict/DuplicateId as an idempotent skip.
- G10-03 — outcomes are counted as migrated/archived/skipped by actual result; a missing doc_writer archives (and is counted as archived).
