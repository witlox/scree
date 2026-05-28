# Scree — Frontmatter Schemas

Every Resource is a markdown file whose YAML frontmatter conforms to its kind's
schema. These specs are the analyst's field-level contract; the architect
formalizes them (e.g. Pydantic / JSON Schema) and the same definitions generate
the API and the TS client types.

Field specs live per kind: [`doc.md`](doc.md), [`ticket.md`](ticket.md),
[`risk.md`](risk.md). This file defines the **shared core** and the
**evolution policy**.

---

## Shared core (every kind)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable, unique, kind-prefixed (`doc-…`, `ticket-2026-000123`, `risk-2026-001`). Never changes (INV-ST-4). Allocated by the Gateway (per-kind sequence) to guarantee uniqueness without cross-repo races (F-08). |
| `kind` | enum `doc\|ticket\|risk` | yes | Type discriminator. |
| `schema_version` | int ≥ 1 | yes | Present from first commit (DD-021, INV-ST-3). |
| `title` | string | yes | Human-readable. |
| `owner` | string | yes | Accountable Keycloak principal or group. |
| `status` | enum (kind-defined) | ticket/risk: yes; doc: omit | Docs are versioned, not stateful. |
| `space` | string | yes | Owning GitLab project path. |
| `references` | list of `{type, target_id}` | no | Typed links by stable `id` (INV-REF-1). |
| `tags` | list[string] | no | Free-form labels. |

**Not frontmatter** (derived from Git, never authored): `created`, `updated`,
author, and the full audit history (INV-ST-5).

## Evolution policy (DD-021)

- **`schema_version`** is an integer, bumped when a change is **breaking**
  (removing a field, renaming, retyping, or tightening a constraint). Purely
  **additive** changes (a new optional field) do **not** bump it.
- **Compatibility window:** the validator and indexer accept the current version
  `N` and the previous `N-1`. Files older than `N-1` must be migrated.
- **Migration:** a migration transforms files from `N` to `N+1` as a tooling pass
  that commits to Git (the migration is itself auditable history). During rollout,
  the indexer tolerates mixed versions within the window.
- **Validation points:** (1) the Gateway validates on write; (2) a CI job
  validates changed files; (3) the indexer validates on read and **quarantines**
  (does not index) an invalid file, surfacing it rather than failing silently.

## Conventions

- Names match `specs/ubiquitous-language.md` exactly.
- Enums are closed sets; an unknown value is a validation failure.
- Dates are ISO-8601 (`YYYY-MM-DD`).
- References are by `id`; a dangling/unreadable reference renders "unavailable"
  with no content leak (INV-REF-3); the Gateway also withholds the `target_id` of a
  cross-boundary unreadable referent (INV-REF-5).
