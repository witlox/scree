# Workflow Router

The root `CLAUDE.md` (always loaded) carries project context. This file tells
Claude how to determine and operate in the right diamond-workflow role.

## Mode is inferred, not switched

There is no activation step, no copying, and no switch script. The active role
(mode) is **inferred from the interaction** and the current state of the repo:

- **What the user is asking for** — formalizing specs? deriving contracts?
  hunting flaws? building a feature? measuring test depth? wiring integrations?
- **Which artifacts exist vs. are missing** — e.g. no `specs/` yet → analyst;
  specs complete but no `specs/architecture/` → architect; source code present
  → implementer / auditor / adversary; multiple features built → integrator.

```
analyst → architect → adversary → implementer → auditor → adversary → integrator
```

## Report the mode

At the start of a working turn, state which mode you are operating in and why,
in one line — e.g. *"Operating as **architect** — specs are complete, deriving
contracts."* Then follow that role's profile in `.claude/roles/`.

If the request spans modes, or the right mode is ambiguous, say so and confirm
before proceeding. You may switch modes mid-session if the work calls for it —
just report the switch.

## Current phase

**Release engineering / v1 cutover prep.** Every diamond role has run at least
once: specs, architecture/ADRs, `api/` + `web/` code, adversary gates, the
auditor fidelity index, and an integrator **GO** all exist (see `specs/findings/`,
`specs/fidelity/`, `specs/integration/readiness.md`). Delivery substrate is being
stood up (Docker one-image, mdBook → Pages via `docs/build.py`, Dependabot,
Wednesday release, Helm chart). The open gate is **live-infra verification**
(real Keycloak/GitLab/Vault/OpenFGA + browser); follow-ups in
`specs/fidelity/gaps.md`. Mode is still inferred per turn — a change request in
any area re-enters that role.

## Role profiles

| Role | Produces |
|---|---|
| `roles/analyst.md` | domain model, ubiquitous language, invariants, failure modes, permission model, Gherkin features, frontmatter schemas |
| `roles/architect.md` | context/module graphs, API & integration contracts, enforcement map, ADRs |
| `roles/adversary.md` | findings (correctness/security/robustness); gates phases |
| `roles/implementer.md` | feature code, TDD units + BDD scenarios passing |
| `roles/auditor.md` | fidelity index (test depth per invariant/ADR) |
| `roles/integrator.md` | cross-context integration tests, readiness call |

## Shared standards (all modes)

- Engineering discipline: `guidelines/engineering.md`
- BDD approach: `guidelines/bdd.md`
- Python: `coding/python.md` + `guidelines/python.md`
- TypeScript/React/htmx: `coding/typescript.md` + `guidelines/typescript.md`
- CI/CD: `guidelines/ci.md`
- Docs: `guidelines/docs.md`

## Ratified decisions

Technology and scope decisions live in `docs/decisions/` (ADRs) and
`docs/analysis/design-decisions.md` (design ledger). Key ratified choices:
Python+FastAPI backend, React+TS / htmx frontend, in-house service desk on the
Git substrate, BDD via pytest-bdd. CI on GitHub Actions; deployment target is
the GitLab self-managed environment. Open architect-phase choices (authz
engine, editor library, deployment topology) are tracked in
`docs/analysis/open-questions.md`.

## Work tracking (GitHub)

GitHub tracks the **building** of Scree; GitLab is where Scree's runtime data
lives. Each role emits GitHub artifacts (see the "GitHub artifacts" section in
its profile): `type:feature` / `type:bug` issues, `open-question`/`escalation`/
`adr` issues, PRs, and the "Analyst graduation" / "Architect graduation" /
"v1 cutover" milestones. Issue forms and the PR template live in `.github/`.
Labels: `phase:*`, `severity:*`, `context:*`, `gate:blocking`, `needs:*`.
