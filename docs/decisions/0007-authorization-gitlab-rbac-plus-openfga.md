# ADR-0007: Authorization — GitLab RBAC (coarse) + OpenFGA ReBAC (tickets)

- Status: accepted
- Date: 2026-05-28
- Deciders: build team
- Resolves: OQ-X-001
- Context phase: architect

## Context and Problem Statement

Permissions are layered (DD-007): coarse repo/group authority for docs/risks/
planning, fine-grained relations for service-desk tickets. The fine-grained
engine must model `requester/watcher/assignee/owner` **and** efficiently answer
"which tickets can user U see?" — the primitive the load-bearing aggregation
invariant (INV-AGG) depends on.

## Considered Options

- **OpenFGA** — Zanzibar-style ReBAC; tuple store; `Check` + `ListObjects`.
- **SpiceDB** — mature Zanzibar engine; richer, heavier to operate.
- **OPA** — Rego policy engine (RBAC/ABAC/admission); not a relationship store.
- **Custom relation table** — Postgres + policy module; zero extra service.

## Decision Outcome

**Coarse = GitLab RBAC** (via Keycloak OIDC + token exchange). **Fine = OpenFGA**
for ticket relations. The Gateway composes them (INV-ACC-2): a request is
permitted iff GitLab authority over the resource's Space **or** an OpenFGA
relation grants it.

OpenFGA over the alternatives because it is ReBAC-native for the four relations
**and** its `ListObjects` API directly implements the per-item aggregation filter
INV-AGG needs — turning the highest-risk property into a supported query rather
than hand-rolled filtering. OPA is the wrong category (policy/ABAC, no relationship
store or reverse-index). SpiceDB is heavier than needed. The custom table remains
the fallback if operating OpenFGA proves not worth it.

### Consequences

- Good: INV-AGG backed by `ListObjects`; relations modeled natively; clean scope
  (OpenFGA only knows tickets; GitLab owns the rest).
- Bad / accepted: one more stateful service (OpenFGA + its store) to run; ticket
  relation tuples must be kept in sync with ticket writes (the Gateway owns this).
- Cache + freshness still apply (INV-ACC-5, OQ-A-011): OpenFGA decisions are
  cached with short TTL and fail closed.

## Scope

OpenFGA authorizes **tickets only**. Docs/risks/planning authority is GitLab's.
Encrypted-content *readability* is additionally gated by key possession (ADR-0005/
0006), independent of this engine.
