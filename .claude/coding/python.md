# Scree — Python Coding Standards

Extends `.claude/guidelines/python.md` with project-specific conventions.
Loaded for: implementer, architect, adversary (implementation review).

## Project shape

- **API gateway** (FastAPI) — the single permission enforcement point; every
  surface (web, CLI, Slack, email) calls it
- **Indexer** — aggregation/scraper; batch + manual + critical-severity webhook
- **Integration adapters** — GitLab, O365/Graph, Slack; thin, call the gateway,
  hold no privileged back door
- **Permission engine** — composes GitLab RBAC + ticket ReBAC; enforces the
  aggregation invariant
- **Migration** — Atlassian → Git pipeline

The concrete module layout is the architect's output (`specs/architecture/
module-graph.md`). Do not invent it here; conform to it.

## Conventions

- **FastAPI** with dependency-injection for auth/identity, request context,
  and external clients. The authenticated principal is resolved once (from the
  OIDC token) and injected — never re-parsed ad hoc.
- **Pydantic v2** models are the single source of truth for request/response
  and frontmatter schemas. Generate the OpenAPI spec from them; the TS client
  is generated from that OpenAPI — do not hand-maintain types twice.
- **Async** for all I/O (GitLab/Graph/Slack/DB/object store). No blocking calls
  in the request path; use `httpx.AsyncClient`, run CPU-bound work in a pool.
- **Permissions are explicit at the boundary.** Every endpoint states the
  authority it requires; aggregation/search endpoints filter results per-item.
  No endpoint trusts the caller or the frontend for authorization.
- **Git is the source of truth.** Writes commit to Git; the index is derived
  and rebuildable. Never mutate the index as the authoritative store.

## Error handling

- Typed exceptions mapped to a project error taxonomy
  (`specs/architecture/error-taxonomy.md`); the gateway maps them to HTTP
  responses centrally (one exception handler, not per-endpoint try/except).
- Validate external input (email MIME, Slack payloads, web bodies, frontmatter
  YAML) at the boundary; trust internal calls.
- No silent swallowing — every error handled or propagated. No secrets in
  error messages, logs, or traces.

## Identity & secrets

- OIDC token validation and token exchange (RFC 8693) go through one auth
  module; downstream tokens are minimally scoped.
- Service credentials come from Vault, not env/config files. Vault is not in
  the user-facing auth path.

## Observability

- OpenTelemetry traces span the gateway → downstream chain; propagate context.
- Audit every gateway action: principal, resource, action, result.

## Domain language

- Names match `specs/ubiquitous-language.md` exactly. Full names in public
  APIs (`Ticket`, not `Tkt`). New term? Check the spec; if absent, escalate
  to the analyst.

## Anti-patterns

- Authorization logic in the frontend, or duplicated outside the gateway
- An integration service calling GitLab/DB directly to "save a hop"
- Trusting the index over Git, or treating the index as writable truth
- Blocking I/O in async paths
- Hand-written types that duplicate the Pydantic/OpenAPI source of truth
- Catch-all `except Exception: pass`; module-level side effects on import
