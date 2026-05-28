<!-- One feature or slice per PR. -->

## What & why

Closes #

## Scope

- Bounded context:
- Scenarios (and binding tier — `@api` / `@e2e` / `@contract`):

## Definition of Done

- [ ] All Gherkin scenarios pass at the right layer
- [ ] Assigned invariants enforced (per-item permission filtering where aggregation/search is touched)
- [ ] Assigned failure modes handled (degradation, not silent failure)
- [ ] `ruff` + `mypy` clean (Python); `eslint` + `tsc` + `prettier` clean (TS)
- [ ] Public functions / endpoints documented (docstrings / TSDoc)
- [ ] Error and negative paths tested (not just the happy path)
- [ ] No architectural contract modified (or an escalation is filed)
- [ ] Fidelity confidence HIGH (auditor verdict, not self-certified)

## Notes for review

<!-- ADR references, open escalations, and what the adversary/auditor should focus on. -->
