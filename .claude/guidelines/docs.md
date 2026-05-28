# Documentation Maintenance

## Required Documentation Per Project

1. **README.md** — purpose, quick-start, architecture overview, license
2. **CONTRIBUTING.md** — dev setup, coding standards, MR process, testing
3. **CLAUDE.md** (root) — project state for AI assistants: phase, scope,
   constraints, conventions
4. **.claude/CLAUDE.md** — workflow router: role routing, mode detection,
   escalations

## Spec Documents (`specs/`)

- `domain-model.md` — entities, value objects, aggregates, state machines
- `ubiquitous-language.md` — domain glossary, kept in sync with code
- `invariants.md` — numbered, testable system invariants
- `assumptions.md` — explicit, falsifiable assumptions
- `failure-modes.md` — failure scenarios with severity and handling
- `permission-model.md` — principals, resources, actions, access invariants
- `features/*.feature` — Gherkin behavioral specs (concrete values)
- `frontmatter-schemas/` — per-resource schemas + the versioning story
- `cross-context/` — integration points between bounded contexts
- `fidelity/INDEX.md` — test depth per invariant (THOROUGH/MODERATE/SHALLOW/NONE)

## Architecture Decision Records

- Stored in `docs/decisions/`, MADR template
- Record context, decision, consequences
- Append-only: supersede with a new ADR, do not edit
- Number sequentially (0001, 0002, …)

## Inline Documentation

- Docstrings (Python) / TSDoc (TypeScript) on every public function,
  endpoint, and exported type
- Module-level docstring stating the module's responsibility
- Comments explain WHY (constraints, invariants), not WHAT
- Comments only where the logic isn't self-evident

## System Documentation Site (`docs/`)

- MkDocs (Material) for the system's own documentation
- `make docs-serve` for local preview
- Published via CI (GitHub Actions) to GitHub Pages on `main`

## Keeping Docs Current

- README/CONTRIBUTING updated as part of any MR that changes setup/build/test
- ADRs written when decisions are made, not retroactively
- Fidelity index updated after every audit sweep
- Stale docs are worse than no docs — delete rather than mislead
