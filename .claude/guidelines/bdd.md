# BDD Guidelines

How Scree validates features. The `.feature` files are the executable
contract that flows through the diamond workflow — they are not just tests.

## Toolchain

- **pytest-bdd** — Gherkin features bound to pytest. Primary harness.
- **pytest-playwright** — drives the browser for UI journeys, so step
  definitions stay in Python and there is one BDD runner.
- **respx** — stubs external HTTP (GitLab/Graph/Slack) at the edge for `@api`.
- **Docker + Testcontainers** — for `@contract` (and the backing services
  for `@e2e`), spin up real disposable services (GitLab, Keycloak, Postgres,
  MailHog) from within the tests. CI-agnostic; the runner needs Docker.

## Binding layers (tag every scenario)

| Tag | Binds at | Use for | Volume |
|---|---|---|---|
| `@api` | the gateway (FastAPI `TestClient` / running gateway) | permissions, state machines, aggregation filtering, normalization | **most** |
| `@e2e` | the browser (Playwright) | critical user journeys end-to-end | few |
| `@contract` | real disposable services | proving stubs match reality | targeted |

Rationale: DD-006 makes the gateway the single enforcement point and the
system is API-first, so the invariants live at the API layer. Bind the bulk
of behavior there — it's fast, deterministic, and tests the thing that
actually enforces the rules. Reserve `@e2e` for journeys (customer submits a
ticket via the portal; agent triages; a doc round-trips through the editor).

The same feature file can carry scenarios of different tags; one feature,
multiple binding layers.

## External systems

- `@api` stubs the **external HTTP edge** (`respx`) while *your* gateway logic
  (authz, ReBAC, state machine, normalization) runs for real. Stubs must
  match the real API contract — the auditor rates stub fidelity.
- `@contract` runs the same kind of scenario against **real** GitLab/Keycloak/
  mail containers, managed with **Docker + Testcontainers**. This is
  **non-negotiable for GitLab-touching paths**: over-stubbing lets a suite go
  green while real GitLab behaves differently.

## Where BDD earns its keep on Scree

- **Aggregation permission invariant (DD-008)** — the highest-value coverage.
  Every aggregation/search/portfolio/risk view needs positive *and* negative
  scenarios; the `exclude` line is the leak test:
  ```gherkin
  Given user "rivera" can read risk "risk-2026-001" but not "risk-2026-009"
  When "rivera" queries the cross-project risk register
  Then the results include "risk-2026-001"
  And the results exclude "risk-2026-009"
  ```
- **State machines (tickets/risks/planning)** — `Scenario Outline` with an
  `Examples:` table of legal/illegal transitions and who may perform them.
- **Multi-origin ticket creation** — one feature, a scenario per origin
  (email/web/Slack/API), all asserting the *same normalized ticket*.
- **Editor round-trip** — `@e2e` scenario asserting markdown survives a
  WYSIWYG edit unchanged (a known risk area).

## Conventions

- Concrete values only — real example IDs and users, no placeholders
  (SEED §9 requires this).
- Step definitions in `tests/` mirror feature names; keep steps thin, push
  logic into fixtures/helpers.
- The adversary adds negative/leak scenarios (gate 1). The auditor records
  depth in `specs/fidelity/INDEX.md` (gate 2). The aggregation invariant
  must be ENFORCED, not merely DOCUMENTED.

## Workflow flow

analyst writes features → architect maps each to an enforcement point →
adversary adds negatives → implementer writes steps and makes them pass →
auditor classifies fidelity → integrator runs cross-context scenarios.
