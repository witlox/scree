# CI/CD Guidelines

CI runs on **GitHub Actions** (`.github/workflows/`). The **deployment target
is the GitLab self-managed environment** (the data substrate and runtime the
custom layer integrates with and deploys alongside). Deployment topology is
the architect's decision (OQ-X-007); this file covers the pipeline.

## Pipeline Structure (three-stage)

Every pipeline follows: **Build → Validate → Test**

The repo is a monorepo (Python backend + TS/React frontend). Use path filters
so a job runs only when its part of the tree changes.

### Build Stage

- Backend: build the image (multi-stage, non-root runtime, no dev deps)
- Frontend: `pnpm build` (Vite); regenerate API types from the gateway
  OpenAPI and fail if they drift from what's committed
- Tag images by commit SHA and push to the container registry used by the
  deployment environment
- Artifacts retained 7–30 days

### Validate Stage

- Python: `ruff format --check`, `ruff check`, `mypy --strict`
- TypeScript: `prettier --check`, `eslint`, `tsc --noEmit`
- Lockfile hygiene: `uv lock --check`, `pnpm install --frozen-lockfile`
- Security: CodeQL (Python + JS/TS), Dependabot, `pip-audit`, `pnpm audit`

### Test Stage

Tiered to match `guidelines/bdd.md`:

- **Unit**: `pytest` (backend), `vitest` (frontend)
- **`@api` BDD**: `pytest-bdd` against the gateway with external HTTP stubbed
  (`respx`) — the bulk of behavioral coverage
- **`@e2e`**: Playwright over the running stack
- **`@contract`** and the backing services for `@e2e`: **Docker +
  Testcontainers** spin up real disposable services (GitLab, Keycloak,
  Postgres, MailHog) from within the tests. The runner must have Docker
  available. Non-negotiable for GitLab-touching paths — it catches stub/real
  drift.
- Coverage per tier → merged → threshold enforced (50% min, 80% target)

## Triggers

- Pull requests targeting `main`
- Push to `main`
- Path filters skip irrelevant jobs (`docs/**`, `*.md` don't trigger app tests)

The **hourly indexer batch is not a CI job** — it runs in the deployment
environment (scheduled job / CronJob / in-app scheduler), per DD-005. Manual
and critical-severity-webhook triggers live in the app.

## Caching

- Python: cache the `uv` cache dir keyed on `uv.lock`
- Node: cache the `pnpm` store keyed on `pnpm-lock.yaml`
- Docker layer caching for image builds

## Container Builds

- Multi-stage: builder → slim runtime (distroless or slim-bookworm)
- Non-root user; no build/dev tooling in the final image
- Version/commit injected at build time
- No privileged mode in CI (Testcontainers uses the host Docker daemon)

## Release

- Version from a Git tag or calver (e.g. `2026.1.0`)
- Images published to the deployment registry; a GitHub Release records the
  artifacts and changelog
- Source-code review enforced by GitHub branch protection + CODEOWNERS
- MR-required **content** paths (compliance-tagged resources, closed risks,
  designated docs — DD-009) live in GitLab repos and are enforced there by
  GitLab branch protection + CODEOWNERS
