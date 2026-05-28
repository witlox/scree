# ADR-0004: Feature validation via BDD (pytest-bdd + pytest-playwright)

- Status: accepted
- Date: 2026-05-28
- Deciders: build team
- Context phase: ratified ahead of architect phase

## Context and Problem Statement

SEED §9 requires `specs/features/*.feature` (Gherkin) for every capability,
and the diamond workflow uses BDD as the connective tissue between analyst,
implementer, auditor, and integrator. We need a concrete execution strategy
for a Python (FastAPI) backend and a React/TS frontend that integrates heavily
with external systems (GitLab, Keycloak, O365, Slack).

## Decision Drivers

- DD-006: the gateway is the single enforcement point, and the system is
  API-first — the invariants live at the API layer
- DD-008: the aggregation permission invariant is load-bearing and needs dense,
  adversarial coverage
- External-system dependencies must be faithfully represented without making
  the suite slow or flaky
- One BDD harness is better than two for a shared-ownership team

## Considered Options

- `pytest-bdd` vs `behave` for the Python Gherkin runner
- Single-tier vs multi-tier binding (API vs UI)
- A separate Cucumber.js + Playwright harness on the TS side vs one Python
  harness driving both

## Decision Outcome

Chosen option: **`pytest-bdd` + `pytest-playwright`, with tiered binding.**

- `pytest-bdd` reuses the pytest ecosystem the backend already needs; `behave`
  is isolated from it.
- `pytest-playwright` keeps UI step definitions in Python, so there is one BDD
  runner and one step language.
- **Bind the bulk of scenarios at the API/gateway layer (`@api`)** — fast,
  deterministic, and it tests the thing that actually enforces the rules.
  Reserve a thin set of UI journeys for `@e2e` (Playwright). A `@contract`
  tier runs against real disposable GitLab/Keycloak/mail services.

### Consequences

- Good: one harness; fast invariant coverage at the enforcement point; the
  aggregation invariant gets positive *and* negative ("excludes") scenarios.
- Bad: the `@contract` tier needs real services in CI (slower, more infra) and
  is non-negotiable for GitLab-touching paths; stub fidelity for `@api` must be
  audited to prevent green-but-wrong suites.

## Notes

Full conventions in `.claude/guidelines/bdd.md`.
