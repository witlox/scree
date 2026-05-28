# Implementation Gate 7 — Adversary Findings

Adversarial pass over the orphan-detection slice merged in PR #62
(`indexing/orphans.py`, Gateway `GET /orphans`). Primary target: INV-ORPH
completeness + aggregation scoping of the report.

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G7-01: Space-archived orphaning is unimplemented (INV-ORPH-1 partial)
- **Severity:** Medium
- **Category:** Correctness > specification compliance
- **Location:** `api/scree/indexing/orphans.py:detect_orphans`
- **Spec reference:** INV-ORPH-1 ("…or whose **Space is archived**…")
- **Description:** INV-ORPH-1 flags an active resource when its owner left/lost
  access **or its Space is archived**. The detector only implements the
  owner-lost-access branch; it has no notion of archived Spaces, so an active risk
  in an archived Space (whose owner still nominally has access) is never flagged —
  exactly the "Space archived" case the invariant calls out.
- **Evidence:** archive `platform/handbook`; an open risk there with an
  still-permitted owner is absent from the report.
- **Suggested resolution:** Give the detector the set of archived Spaces and flag
  active resources/tickets whose Space is archived, independent of owner access.

## Finding G7-02: Orphaned-ticket report is not desk-scoped — every agent sees all desks' orphans
- **Severity:** Medium
- **Category:** Security > aggregation/authorization scoping
- **Location:** Gateway `GET /orphans` (`tickets = report.tickets if ... is_agent(principal)`)
- **Spec reference:** INV-ORPH-2 ("surfaced to **desk leads**"); INV-AGG (per-scope filtering)
- **Description:** The ticket section of the report is shown to **any** agent
  (`is_agent`), unscoped — every agent sees the orphaned tickets of **every** desk,
  not just the desk(s) they lead. Today there is a single desk so the over-disclosure
  is latent, but the model already carries a per-ticket `space` (the desk); the
  report should be scoped to the desks the requester maintains, like the resource
  section is scoped to maintained Spaces.
- **Evidence:** with two desks, an agent of desk A sees desk B's orphaned ticket ids.
- **Suggested resolution:** Group orphaned tickets by desk Space and filter to desks
  the requester maintains (symmetric with the resource filter), not a flat `is_agent`.

## Finding G7-03: Report recomputed synchronously on every GET, not by the hourly batch
- **Severity:** Medium
- **Category:** Robustness > performance / semantic drift
- **Location:** Gateway `GET /orphans` (calls `detect_orphans` per request)
- **Spec reference:** INV-ORPH-1/feature ("flagged in the **hourly batch**"); indexer-design (batch + manual trigger, resolve-once)
- **Description:** `GET /orphans` runs full detection on every request, re-resolving
  **every** owner's Space access each call. In the real system, owner-access
  resolution is a GitLab membership lookup, so this is O(resources × membership) per
  request — a perf/DoS surface and a semantic drift from the spec's "hourly batch."
- **Evidence:** N owners → N access resolutions per `GET /orphans`, every request.
- **Suggested resolution:** Compute the report in the batch / on a manual refresh
  into a cache; serve the (filtered) cached report with an `as_of` marker.

## Finding G7-04: Owner-access proxy uses read access, missing owners who lost only write
- **Severity:** Low
- **Category:** Correctness > orphan detection accuracy
- **Location:** `api/scree/indexing/orphans.py` (`r.space not in authority.readable_spaces(r.owner)`)
- **Spec reference:** INV-ORPH-1 (owner can no longer steward the resource)
- **Description:** "Owner lost access" is checked via **read** membership. An owner
  who retains read but lost **write** can no longer maintain/steward the resource —
  effectively orphaned — yet is not flagged. The stewardship check should be the
  ability to maintain (write), not merely read.
- **Evidence:** owner downgraded read-only on a Space → their open risk is not flagged.
- **Suggested resolution:** Flag on loss of **write** (`can_write`) rather than read.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G7-01 | Medium | Correctness | Space-archived orphaning unimplemented (INV-ORPH-1 partial) |
| G7-02 | Medium | Security/aggregation | Orphaned-ticket report not desk-scoped (all agents see all) |
| G7-03 | Medium | Robustness | Recomputed per GET, not batch-cached (perf/DoS + semantic drift) |
| G7-04 | Low | Correctness | Owner-access proxy uses read, misses lost-write-only owners |

**Counts:** 0 critical · 0 high · 3 medium · 1 low — **4 total.** No `gate:blocking`.

**Highest-risk area:** completeness + scoping — INV-ORPH-1 is only half-built
(no archived-Space case) and the ticket report isn't scoped to the requester's desk.

**Resolution (2026-05-28) — all 4 resolved (PR #63):**
- G7-01 — `detect_orphans` takes `archived_spaces` and flags active resources/
  tickets whose Space is archived, independent of owner access.
- G7-02 — orphaned tickets are grouped by desk Space and the `GET /orphans`
  endpoint filters both resources and tickets by `can_write` (Space/desk maintainer),
  not a flat `is_agent`.
- G7-03 — a service principal recomputes the report via `POST /orphans/refresh`
  (the batch/manual trigger) into an `OrphanCache`; `GET /orphans` serves the cached
  report with an `as_of` marker and a `computed` flag.
- G7-04 — the owner-stewardship check uses `can_write` (maintain), so an owner who
  lost only write is flagged.
