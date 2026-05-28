# Scree — Permission Model

Principals, resources, actions, and the precise access invariants. The
aggregation invariant (§6) is load-bearing — a leak there is a serious security
failure, so it is stated precisely and is testable.

---

## 1. Principals (OQ-A-004)

| Principal | Identity source | Scope |
|---|---|---|
| **Internal user** | Keycloak; is a GitLab user | Read/write resources per GitLab repo/group membership; may be an agent. |
| **External customer** | Keycloak (external realm); **not** a GitLab user | Own tickets + tickets explicitly shared with them; community-visible content. |
| **Agent** | Internal user with a desk role | Triage/work tickets across the desk; sees ticket queues. |
| **Operator** | Internal user with ops role | Run/observe the system; trigger re-index; no special data-read privilege beyond their GitLab authority. |
| **Service account** | Vault-issued credential | Service-to-service; acts only via the Gateway with propagated user identity where a user initiated the action. |
| **Slack bot (on behalf of)** | Slack event + resolved Keycloak user | Acts as the resolved human; refused if the Slack↔Keycloak mapping fails (no degraded attribution). |

## 2. Single enforcement point (DD-006)

All access goes through the **Gateway**. Web, CLI, Slack, and email integrations
are clients of the same API; none has privileged back-door access to GitLab or
the index. Frontend permission checks are **UX only** — the Gateway is
authoritative and assumes the caller can craft any request.

## 3. Layered authority (DD-007)

- **Coarse (authoritative for docs, risks, planning views):** GitLab repo/group
  RBAC, mapped from Keycloak groups via OIDC claims. A Space is a GitLab project,
  so "can read this doc/risk" reduces to "can read this project."
- **Fine (tickets only):** relationship-based access control (ReBAC) over the
  relations `requester`, `watcher`, `assignee`, `owner`, plus the
  `community_visible` flag.
- **Composition rule:** authority is the **union** of (a) GitLab authority over
  the resource's Space and (b) any ticket ReBAC grant. A request is permitted iff
  at least one layer grants it and none denies it. The two layers never
  silently disagree: tickets are not gated by repo membership (external customers
  have none), and docs/risks are not gated by ReBAC.

## 4. Actions by resource kind

| Resource | read | create | update | transition | delete | kind-specific |
|---|---|---|---|---|---|---|
| **Doc** | Space members | Space writers | Space writers | — | Space maintainers | MR-required on designated paths (DD-009) |
| **Ticket** | requester / watchers / assignee / agents (+ anyone if `community_visible`) | any authenticated principal (incl. external) | assignee / agents | assignee / agents (open↔resolved↔closed) | agents/maintainers | **promote** to `community_visible`: agent, explicit confirm (DD-013); **share**: requester adds a watcher |
| **Risk** | Space members | Space writers | owner / Space writers | owner (open↔closed; **close** MR-required) | Space maintainers | **escalate**: create org-repo duplicate + cross-ref |
| **Aggregation view** | any authenticated principal | — | — | — | — | results filtered per §6 |

## 5. Identity propagation (DD-018)

The Gateway calls GitLab on behalf of the authenticated human via OIDC token
exchange (RFC 8693), so GitLab's audit log records the **real human**, not the
Gateway. Every Gateway action is audited: principal, resource, action, result.

## 6. The aggregation permission invariant (DD-008) — LOAD-BEARING

> **INV-AGG.** For any principal `P`, any aggregation/search/portfolio/risk-register
> view `V`, and any item `I` that appears in `V`'s result returned to `P`, `P` is
> authorized to read `I` at its source. Equivalently: the set of items returned to
> `P` in any aggregation view is a **subset** of the items `P` could read by direct
> access. No title, excerpt, count, score, or any other metadata of an
> unauthorized item is exposed.

**Enforcement.** Aggregation queries hit the (broad) index for performance, then
**filter every item by `P`'s source authority before returning**. The index is
never trusted to be pre-partitioned by permission; filtering is per-item, at query
time, on every request — not only at view load.

**Defenses in depth.**
- Permission cache TTL is short (minutes, not hours) so revocations propagate
  quickly (constraints in §8).
- Sensitive risk categories (`security`, `compliance`) are stored in **separate
  indexes** from the main index — belt-and-suspenders against a filter bug.
- Every aggregation query is audited with `P` and the item IDs returned.
- The test suite carries **negative** scenarios proving exclusion (the
  `Then ... excludes` assertion), not just positive retrieval.

## 7. External customer specifics (DD-011)

External customers are **individuals**. A ticket is visible to its requester,
explicitly named watchers, and agents. The **org tag** is reporting metadata,
**not** a permission boundary in v1 — there is no "see all my institution's
tickets" path. Sharing is per-user, by the requester adding a watcher.

## 8. Permission caching (OQ-A-011 — constraints; architect implements)

- Short TTL (minutes) on cached permission decisions.
- Explicit invalidation on known revocation events where feasible (membership
  change, ticket relation change).
- A stale cache must fail **closed** for INV-AGG purposes: when in doubt, omit
  the item rather than risk exposing it.

## Open questions referenced

OQ-A-011 (permission-cache implementation — architect), OQ-A-016 (Slack↔Keycloak
mapping mechanism), OQ-HE-008 (compliance/audit as consumers of audit/risk data).
The reference-leak concern is resolved by INV-REF-3 (an unreadable referent never
exposes its content via the referencing resource).
