# Scree — Invariants

Numbered, testable assertions that must always hold. Each cites its source and is
phrased so a test can fail when it is violated. Severity reflects blast radius if
broken. The adversary targets these; the auditor rates enforcement depth.

---

## Storage & truth

- **INV-ST-1** — Git is the source of truth. Every resource mutation is a Git
  commit; no resource state exists only in the index or a cache. *(DD-002)*
- **INV-ST-2** — The index is derived and rebuildable from Git alone. Deleting
  and rebuilding the index changes no answer the system gives. *(DD-002, prior-art §3)*
- **INV-ST-3** — Every resource carries an integer `schema_version` from its
  first commit. *(DD-021)*
- **INV-ST-4** — `id` is stable and unique across the system; it never changes
  once assigned, even on move. *(domain-model)*
- **INV-ST-5** — `created`, `updated`, and audit history are projections of Git
  commit history, never independently authored fields. *(domain-model)*

## References (OQ-A-009 → stable IDs + filtered render)

- **INV-REF-1** — References are stored by stable `id`, not by path or title.
- **INV-REF-2** — "Delete" is a tombstone; Git history is retained. There is no
  destructive erasure of resource history.
- **INV-REF-3** — A reference whose target is missing or **unreadable to the
  viewer** renders as "unavailable" and exposes **no** title, excerpt, or metadata
  of the target. *(upholds INV-AGG)*
- **INV-REF-4** — Deletion or move of a referenced resource is never blocked by
  the existence of references (no hard referential integrity).

## Access & permissions

- **INV-AGG** *(load-bearing)* — For any principal `P` and any aggregation/search/
  portfolio/risk view, the items returned to `P` are a **subset** of the items `P`
  could read by direct access; no title/excerpt/count/score/metadata of an
  unauthorized item is exposed. Filtering is per-item, at query time, every
  request. *(DD-008; see permission-model §6)*
- **INV-ACC-1** — All access is mediated by the Gateway; there is no path to
  resources or the index that bypasses it. Frontend checks are not relied upon for
  authorization. *(DD-006)*
- **INV-ACC-2** — Authority composes as: GitLab repo/group RBAC (docs, risks,
  planning views) ∪ ticket ReBAC (tickets). A request is permitted iff a layer
  grants it. *(DD-007)*
- **INV-ACC-3** — A ticket is readable only by its requester, named watchers, the
  assignee, and agents — unless `community_visible` is set, then by any
  authenticated principal. *(DD-011, DD-013)*
- **INV-ACC-4** — The org tag on an external customer grants no access. *(DD-011)*
- **INV-ACC-5** — A stale permission cache fails closed: when authority is
  uncertain, the item is omitted, never exposed. *(DD-008, OQ-A-011)*

## Identity

- **INV-ID-1** — Actions against GitLab carry the initiating human's identity via
  token exchange; GitLab's audit log shows the human, not the Gateway. *(DD-018)*
- **INV-ID-2** — A Slack-initiated action whose Slack↔Keycloak mapping fails is
  **refused**; the system never proceeds with degraded/anonymous attribution.
  *(DD-012, OQ-A-016)*
- **INV-ID-3** — Every Gateway action is audited with principal, resource, action,
  and result. *(DD-006)*

## Lifecycle (OQ-A-006 confirmed — minimal)

- **INV-LC-1** — A Ticket's state is one of `open`, `resolved`, `closed`; the only
  legal transitions are open→resolved, resolved→closed, and reopen
  (resolved→open, closed→open). *(domain-model)*
- **INV-LC-2** — `community_visible` is orthogonal to ticket state; promoting a
  ticket to community-visible requires an explicit agent action with confirmation.
  *(DD-013)*
- **INV-LC-3** — A Risk's state is one of `open`, `closed`. Transition into
  `closed` occurs only via a merge request on the MR-required path. *(DD-009)*
- **INV-LC-4** — Risk escalation creates a duplicate Risk in an org Space with a
  cross-reference back to the source; it does not move or hide the original.
  *(DD-004)*

## Indexing & triggers

- **INV-IX-1** — A change to a Risk whose `category` is `security` or `compliance`
  triggers the near-real-time webhook; all other changes ride the batch.
  *(DD-005; OQ-A-013, pending OQ-HE-001 ratification)*
- **INV-IX-2** — A missed webhook is caught by the next hourly batch; correctness
  never depends on webhook delivery. *(DD-005)*
- **INV-IX-3** — The manual re-index trigger is authenticated and rate-limited (it
  is otherwise a DoS vector). *(DD-005)*
- **INV-IX-4** — Sensitive risk categories (`security`, `compliance`) are indexed
  separately from the main index. *(DD-008)*

## Orphan handling (OQ-A-005 confirmed)

- **INV-ORPH-1** — An active (non-`closed`) resource whose owner has left the org /
  lost access to its Space, or whose Space is archived, is flagged in the hourly
  batch and surfaced in an "orphaned actives" report to Space maintainers for
  manual reassignment. Orphan detection never auto-reassigns. *(OQ-A-005)*

## Update governance

- **INV-GOV-1** — MR-required paths (compliance-tagged resources, closed risks,
  designated doc paths) cannot be changed by direct commit; enforcement is GitLab
  branch protection + CODEOWNERS. *(DD-009)*

## Degradation

- **INV-DEG-1** — When GitLab is unreachable, reads from a local clone of
  authorized content still succeed; resource/ticket creation is refused with a
  clear error and never silently dropped or queued-as-success. *(DD-003)*
- **INV-DEG-2** — When O365 is unreachable, inbound email-driven ticket creation
  fails visibly; no email is silently lost from the user's perspective. *(DD-019)*

---

Severity guidance for the auditor: INV-AGG, INV-ACC-*, INV-ID-2 are
**critical** — shallow coverage on any of these is a critical finding.
