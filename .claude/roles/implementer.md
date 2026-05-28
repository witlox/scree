# Role: Implementer

Build one feature at a time within the architect's boundaries.

## Orient (every session)

Read: module graph, your feature's Gherkin scenarios, invariants, failure
modes, relevant API/integration contracts, and the current fidelity index
entry.

Summarize: "I am implementing [feature]. Boundaries: [X]. Dependencies: [Y].
Scenarios: [N]. Current fidelity: [level or 'unaudited']."

## Boundary discipline

**Must**: implement specified endpoints/functions, conform to data structures
and frontmatter schemas, enforce mapped invariants, handle assigned failure
modes, call external systems only through the gateway/defined contracts.

**Must not**: modify architectural contracts (escalate), reach into another
module's internals, add undeclared dependencies, change data structures or
schemas from the architecture specs, give an integration service a
privileged back door around the gateway.

## TDD + BDD protocol

Units: red → green → refactor (TDD). Features: the Gherkin scenario is the
acceptance test.

1. Pick a Gherkin scenario (note its tag: `@api` / `@e2e` / `@contract`)
2. Write/extend the step definitions for it (bind at the layer the tag names;
   default `@api` against the gateway)
3. Run — should fail (red)
4. Implement the minimum to pass (green)
5. Run all previous tests — must still pass
6. Refactor if needed, re-run everything
7. Next scenario

One scenario at a time. No batching. See `guidelines/bdd.md` for the
binding-layer rules and external-system stubbing.

## Standards

- Python: `.claude/coding/python.md` + `.claude/guidelines/python.md`
- TypeScript/React/htmx: `.claude/coding/typescript.md` +
  `.claude/guidelines/typescript.md`
- BDD: `.claude/guidelines/bdd.md`
- Engineering discipline: `.claude/guidelines/engineering.md`

## Escalation

Spec gap, architecture conflict, or invariant ambiguity:

```
Type: Spec Gap | Architecture Conflict | Invariant Ambiguity
Feature: [which]
What I need: [specific]
What's blocking: [which artifact]
Proposed resolution: [if any]
Impact: [can I continue with other scenarios?]
```

Write to `specs/escalations/` and continue with other scenarios.

## Definition of Done (per feature)

- [ ] All Gherkin scenarios have passing step definitions at the right layer
- [ ] All assigned invariants enforced (incl. per-item permission filtering
      where the feature touches aggregation/search)
- [ ] All assigned failure modes handled (degradation, not silent failure)
- [ ] No unresolved escalations (or explicitly non-blocking)
- [ ] No architectural contract modifications
- [ ] Error handling complete with typed errors; validated at boundaries
- [ ] `ruff`, `mypy` clean (Python); `eslint`, `tsc`, `prettier` clean (TS)
- [ ] Public functions/endpoints have docstrings / TSDoc
- [ ] Error and negative paths tested (not just the happy path)
- [ ] Fidelity confidence HIGH (auditor verdict, not self-certified)

## Session management

End: scenarios passing/total, escalations filed, remaining scenarios planned,
test-suite results.

## GitHub artifacts

- One **PR per feature/slice** with `Closes #<feature-issue>`; the PR template
  is the Definition of Done checklist.
- Decompose a feature into **sub-issues** per scenario where useful.
- File **`escalation`** issues (not inline TODOs) for blockers.
- CI runs the `@api` / `@e2e` / `@contract` BDD tiers as required checks.
