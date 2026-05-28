# TypeScript Guidelines

## Version & Tooling

- TypeScript 5.x, `strict: true`
- Package manager: `pnpm` (lockfile committed; workspace within the monorepo)
- Lint: `eslint` (zero warnings); Format: `prettier`
- Types: `tsc --noEmit` clean
- Security: `pnpm audit`; Dependabot/Renovate
- Coverage: 50% minimum, 80% target on application logic

## Style

- No `any` without a written justification; narrow `unknown` at boundaries
- API request/response types are **generated** from the gateway OpenAPI spec;
  never hand-write or duplicate them
- Function components + hooks; no class components
- Co-locate state with its use; lift only when genuinely shared
- One API client module attaches auth and is the sole path to the backend

## React / htmx

- Decide rendering per surface (see `coding/typescript.md`); one technology
  owns a given DOM region
- React surfaces are mounted islands; htmx surfaces are server-rendered
  fragments with minimal client JS
- Accessibility is required: WCAG 2.1 AA (labels, roles, keyboard, focus)

## Testing

- `vitest` for unit/component logic
- `playwright` for `@e2e` Gherkin journeys (driven via the BDD harness —
  see `guidelines/bdd.md`)
- Assert rendered/observable behavior, not implementation details
- Markdown round-trip through the editor is asserted explicitly

## Build & Run

- `vite` for build/dev; environment via typed config, no secrets in the bundle
- Container/static build is reproducible from the lockfile

## CI Pipeline

Three-stage (see `guidelines/ci.md`): Build → Validate → Test.

## Patterns

- Server state via a query/cache library; local UI state via hooks
- Authorization is never decided client-side (UX hiding only)
- Explicit error/loading/empty states on every data-driven view
- Regenerate API types on contract change as part of the build
