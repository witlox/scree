# Implementation Gate 3 — Adversary Findings

Adversarial pass over the planning slice merged in PR #54
(`scree/planning` + `GET /planning/portfolio`). Primary target: the aggregation
permission invariant (DD-008 / INV-AGG). Scope: `api/scree/planning/**` and the
planning endpoint in `api/scree/gateway/app.py`.

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G3-01: Stale index group-mapping leaks an epic across a group move (INV-AGG under stale object→group binding)
- **Severity:** Medium
- **Category:** Security > aggregation permission invariant (stale-permission cache)
- **Location:** `api/scree/gateway/app.py` (`portfolio_rollup`, ~:184-193); `api/scree/planning/index.py` (`candidates`)
- **Spec reference:** INV-AGG (DD-008); INV-ST-2 (nothing the system *asserts* depends on index-only state); indexer-design aggregation path
- **Description:** The filter is `e.group in planning_authority.readable_groups(principal)`.
  The per-request resolution (AR-08) refreshes the **subject's** current group
  memberships, but the **object's** group comes from `PlanningIndex` — i.e. the
  epic's group *as of the last index refresh*. If an epic is moved between groups
  after the last refresh, the authorization decision uses the stale group. The
  dangerous direction: an epic moved from a group the viewer can read into one
  they cannot still carries the old (readable) group in the index, so it remains
  visible — a viewer sees an epic that, in GitLab right now, lives in a group they
  cannot access. A permission decision is an assertion, so depending on index-only
  state here is in tension with INV-ST-2, not just a data-freshness matter the
  `as_of` marker covers.
- **Evidence:** index has `Epic(id="EPIC-1", group="grp-readable")`; an admin
  moves EPIC-1 to `grp-secret` in GitLab; before the next hourly batch, `rivera`
  (member of `grp-readable`, not `grp-secret`) opens the rollup → EPIC-1 still
  contributes (id/title/capacity) for up to the index interval.
- **Suggested resolution:** Treat object→group as authorization-relevant, not just
  data: (a) re-resolve the epic's *current* group at query time for the visibility
  decision (accepting the per-item cost the rollup otherwise avoids), or (b) fire
  the critical re-index path on epic group moves so the window is near-zero, or
  (c) if neither is affordable, record this as an explicitly accepted bounded-
  staleness risk (cf. A-4) with the window = index cadence and the `as_of` marker
  as the disclosure. Decide deliberately rather than leaving it implicit.

## Finding G3-02: Portfolio rollup is unbounded — full candidate set materialized and filtered per request
- **Severity:** Low
- **Category:** Robustness > resource exhaustion
- **Location:** `api/scree/planning/index.py` (`candidates` returns the whole list); `api/scree/gateway/app.py` (`portfolio_rollup` list-comprehends over all candidates)
- **Spec reference:** indexer-design Performance note (AR-11): "bounded results + cursor pagination" fallback
- **Description:** `candidates()` returns every indexed epic and the endpoint
  filters/aggregates the full set on every request, with no upper bound or
  pagination. AR-11 calls for bounded results + cursor pagination as the fallback
  when an aggregation set is large; that bound is applied to ticket `ListObjects`
  but not to the planning rollup. A very large portfolio (or a hostile/buggy index
  populated with many epics) makes every rollup request O(n) in memory and time.
- **Evidence:** an index with N epics → each `GET /planning/portfolio` builds an
  N-element candidate list and a per-request filtered copy, unbounded in N.
- **Suggested resolution:** Bound the candidate scan (cap + cursor pagination per
  AR-11), or aggregate incrementally; at minimum cap the materialized set and
  expose pagination, since a portfolio view is an obvious target for a large/slow
  response.

## Finding G3-03: Partial planning config silently disables the endpoint; never-indexed staleness served as bare null
- **Severity:** Low
- **Category:** Robustness > degradation correctness / observability
- **Location:** `api/scree/gateway/app.py` (`if planning_index is not None and planning_authority is not None`); `as_of` passthrough
- **Spec reference:** degradation.feature (failures must be visible, not silent); indexer-design `as_of` staleness marker
- **Description:** Two minor degradation gaps. (1) The endpoint is registered only
  when *both* `planning_index` and `planning_authority` are supplied; providing one
  without the other silently yields 404 on the route rather than a clear
  misconfiguration error (same footgun as the ticket wiring, but worth flagging).
  (2) When the index has never been refreshed, `as_of` is `null`; the response
  serves data (or an empty rollup) with `as_of=null` and no explicit "never
  indexed / staleness unknown" signal, so a consumer can't distinguish "fresh-ish
  but unmarked" from "never indexed."
- **Evidence:** `create_app(..., planning_index=idx)` without `planning_authority`
  → `GET /planning/portfolio` 404. A fresh `PlanningIndex()` → `{"as_of": null, ...}`.
- **Suggested resolution:** Fail loudly on partial config (require both or neither,
  mirroring how `create_app` now fails closed on auth), and represent unknown
  staleness explicitly (e.g. `as_of: null` plus a `stale: true`/`never_indexed`
  flag) so the UI can warn instead of silently showing an unmarked view.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G3-01 | Medium | Security/INV-AGG | Stale index group-mapping leaks an epic across a group move |
| G3-02 | Low | Robustness/exhaustion | Unbounded portfolio rollup (no pagination/bound) |
| G3-03 | Low | Robustness/degradation | Partial config silently 404s; never-indexed staleness served as bare null |

**Counts:** 0 critical · 0 high · 1 medium · 2 low — **3 total, all resolved (PR #55).**

**Resolution (2026-05-28):**
- G3-01 — accepted as a bounded-staleness window and made explicit: the rollup
  now discloses `as_of` + `never_indexed`, and a code comment records that the
  window closes when the real GitLab-group authority replaces the stub. The leak
  is not closed in code (the stub has no live object→group source); it is an
  acknowledged, disclosed trade-off pending that follow-up.
- G3-02 — cursor pagination on the returned `epics` list (`limit` 1..500, `cursor`),
  with `epic_count`/`total_capacity` kept as the aggregate over all visible epics.
- G3-03 — `create_app` fails loudly on partial planning config (index XOR
  authority), and the response carries a `never_indexed` flag for unknown staleness.

**Highest-risk area:** G3-01 — the rollup's visibility decision trusts the index's
object→group binding, so a group move opens a bounded INV-AGG leak window. No
`gate:blocking` findings (no critical/high).

**Note (scope, not a finding):** `PlanningAuthority` is a documented spike stub
keyed on a readable-group map; the real GitLab-group-membership backing (analogous
to `GitLabAuthority`) and a `@contract` test vs GitLab CE remain the planning
follow-ups, as recorded on PR #54.
