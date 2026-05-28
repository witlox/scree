# Implementation Gate 12 — Adversary Findings

Adversarial pass over the degradation slice merged in PR #72 (`platform/health.py`,
Gateway `_require_gitlab` guards). Primary target: does degradation actually hold —
do reads survive a GitLab outage, and are *all* writes refused?

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G12-01: Composed-authority read path needs GitLab → reads don't survive an outage on a cold cache
- **Severity:** Medium
- **Category:** Robustness > degradation correctness (INV-DEG-1)
- **Location:** Gateway `_readable_spaces`/`_readable_groups` (call `gitlab_authority.readable_spaces(token)`)
- **Spec reference:** INV-DEG-1 ("reads from a local clone of authorized content still succeed")
- **Description:** INV-DEG-1 promises authorized **reads** keep working when GitLab
  is down. But with the composed GitLab authority, the read path resolves readable
  Spaces by calling GitLab membership. During an outage that call fails (or, if the
  short-TTL cache has expired, yields nothing) — so `GET /docs` either errors or
  returns empty. The degraded read path only truly works with the spike stub
  authority, not the real one. The authority resolution is itself a GitLab
  dependency on the read path.
- **Evidence:** configure the GitLab authority, let the membership cache expire,
  drop GitLab → authorized reads fail/empty though the content is in the local clone.
- **Suggested resolution:** When GitLab is down, serve readable-space membership
  from the last-known cached value (stale-OK during outage) rather than failing; fall
  back to empty only for users with no cached membership.

## Finding G12-02: Write-guard coverage is incomplete — some writes proceed during a GitLab outage
- **Severity:** Medium
- **Category:** Robustness > degradation correctness (INV-DEG-1 uniformity)
- **Location:** Gateway `slack_link`, `run_migration` (no `_require_gitlab()`)
- **Spec reference:** INV-DEG-1 ("resource/ticket creation is refused … never silently dropped")
- **Description:** `_require_gitlab()` guards ticket/risk/doc creation, transition,
  promote, slack capture and inbound email — but **not** `slack_link` (appends a
  comment) nor `migration/run` (creates tickets/docs in bulk). During a GitLab
  outage those writes still execute (or half-succeed against an unavailable Git),
  violating INV-DEG-1's uniform "writes refused." (Object-storage attachments are
  independent of GitLab and may legitimately proceed.)
- **Evidence:** with `gitlab_up=False`, `POST /slack/link-ticket` and
  `POST /migration/run` are not refused.
- **Suggested resolution:** Apply `_require_gitlab()` to every Git-backed write
  (slack_link, migration); leave object-storage-only writes unguarded.

## Finding G12-03: Availability is a static flag with no health probe
- **Severity:** Low
- **Category:** Robustness > operability
- **Location:** `api/scree/platform/health.py:Availability`
- **Spec reference:** DD-003/DD-019 (degradation)
- **Description:** `Availability` is a plain mutable flag; nothing probes GitLab/O365
  to update it, so in a real deployment degradation never engages unless an external
  actor flips the flag. The mechanism is correct but unwired.
- **Evidence:** GitLab goes down in reality → `gitlab_up` stays `True` → writes are
  attempted against a dead GitLab instead of being refused.
- **Suggested resolution:** Wire a periodic health probe (or circuit breaker on
  GitLab/Graph call failures) that updates `Availability`; documented as a deploy
  concern for now.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G12-01 | Medium | Robustness/degradation | Composed-authority read path needs GitLab → reads fail on a cold cache during an outage |
| G12-02 | Medium | Robustness/degradation | Write-guard incomplete (slack_link, migration) → some writes proceed during an outage |
| G12-03 | Low | Robustness/operability | Availability is a static flag with no health probe |

**Counts:** 0 critical · 0 high · 2 medium · 1 low — **3 total.** No `gate:blocking`.

**Highest-risk area:** degradation correctness — the read path's hidden GitLab
dependency (G12-01) and incomplete write coverage (G12-02) both undercut INV-DEG-1.

**Resolution (2026-05-28) — all 3 resolved (PR #73):**
- G12-01 — during a GitLab outage the readable-space/group resolver serves the last-known membership (stale-OK) instead of calling GitLab, so authorized reads survive.
- G12-02 — _require_gitlab now also guards slack_link and migration/run (all Git-backed writes refused uniformly).
- G12-03 — accepted: Availability must be driven by a health probe / circuit-breaker in deployment; documented on the dataclass.
