# General Engineering Guidelines

Language-agnostic discipline. For language specifics see
`guidelines/python.md`, `guidelines/typescript.md`, and the `coding/` files.

## Commits & Branching

- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`,
  `perf:`, `chore:`, `ci:`
- One logical change per commit; reference issue/MR numbers where applicable
- Linear history preferred; merge commits acceptable for MRs
- Pre-commit hooks (lefthook or `pre-commit`) enforce format, lint, type,
  test — never skip with `--no-verify`
- Commits signed where possible (operator-level audit trail)

## Error Handling

- Wrap errors with context as they cross layers; preserve the cause
- Typed errors mapped to the project error taxonomy; map to transport
  (HTTP) responses centrally, not per-endpoint
- Validate external input at system boundaries (email, Slack, web, API,
  frontmatter YAML); trust internal calls
- No silent swallowing — every error handled or propagated
- No secrets in messages, logs, or traces

## Code Organization

- Imports grouped: stdlib → external → internal
- One responsibility per file; keep files under ~500 lines
- Pass dependencies explicitly; no global mutable state
- No import-time side effects

## Testing

**TDD** drives internal logic: red → green → refactor at the unit level.

**BDD** verifies the assembled system: Gherkin scenarios in `specs/features/`,
step definitions in `tests/` (see `guidelines/bdd.md`). The default binding
layer is the API gateway (`@api`); critical journeys bind to the UI (`@e2e`).
Scenarios exercise real integrated code paths — externals are stubbed at the
edge for `@api`, and a `@contract` tier runs against real disposable services
to catch stub/real drift.

Negative and permission scenarios are mandatory wherever authorization
applies. The aggregation permission invariant gets the densest coverage.

## Architecture Decision Records

ADRs in `docs/decisions/` (MADR template). Record context, decision,
consequences. Append-only — supersede with a new ADR, do not edit.
Number sequentially (0001, 0002, …).

## Workflow Phases (diamond)

1. Analyst — domain model, invariants, Gherkin scenarios
2. Architect — interfaces, contracts, ADRs
3. Adversary — challenge completeness, gate 1
4. Implementer — TDD for units, BDD for features
5. Auditor — depth/fidelity classification, gate 2
6. Adversary — second pass on the implementation
7. Integrator — cross-context validation
