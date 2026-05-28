# Scree — Docs-Frontend Spike: Report & Conclusion

**Status:** CLOSED (2026-05-28). Tracking issue: #32.

## Purpose (per `docs/PROPOSAL.md`)

Calibrate the effort unit and de-risk the highest-uncertainty pieces — the
WYSIWYG editor, its integration with Git-backed storage, and the permission
gateway — before committing to the full build.

## What was built and validated

Seven vertical slices, each TDD/BDD red→green, CI-gated, auto-merged on green:

| PR | Slice | Validated |
|---|---|---|
| #33 | Permission-filtered doc read | INV-AGG; existence-leak-safe 404 |
| #34 | OpenFGA `ListObjects` | A-5 mechanism, against **real OpenFGA** |
| #35 | Git-backed doc store | DD-002, INV-ST-3/5, against **real git** |
| #36 | TipTap markdown round-trip | DD-016 fidelity, headless (vitest+jsdom) |
| #37 | OpenFGA wired into the Gateway | end-to-end authz (Gateway→real OpenFGA) |
| #38 | Folder-tree spaces + per-folder uploads | the editing/storage model |
| #39 | GitLab RBAC (coarse authority) | against **real GitLab CE** |

**Tooling proven:** Python + FastAPI (uv); React + TypeScript + TipTap
(mise + pnpm); tests via pytest-bdd and vitest; the `@contract` tier via Docker
+ Testcontainers (OpenFGA) and a real GitLab CE container. CI (GitHub Actions)
gates both `api-tests` and `web-tests`; branch protection + auto-merge in place.

## Assumptions outcome

- **A-5 (per-item permission filtering):** mechanism validated — OpenFGA
  `ListObjects` ∪ GitLab authority works end-to-end (#34, #37). **Not** load-tested
  at scale → OQ-X-006.
- **A-4 (GitLab Advanced Search permission-filtering):** **NOT validated —
  accepted as a documented risk.** Advanced Search is GitLab **Ultimate** +
  **Elasticsearch**; not reproducible on a free CE container. Validate on a real
  Ultimate environment (staging/UAT) before internal aggregation relies on it;
  fallback is to filter via the derived index instead of Advanced Search.

## Effort calibration

Every slice landed quickly and cleanly, with no architectural surprises — a
**positive signal** for the full-build estimate. The two genuine cost/risk
concentrations are unchanged: the **service desk** (ticket ReBAC + external
identity + email threading, ADR-0001) and the **WYSIWYG editor** polish beyond
the round-trip core (paste-from-Word, tables — an `@e2e`/browser concern).

## Conclusion & recommendation

The architecture's load-bearing invariant (**INV-AGG** via OpenFGA `ListObjects`
∪ GitLab authority) holds **end-to-end against real infrastructure**, the Git
substrate and schema enforcement hold, and the editor round-trips markdown. Every
assumption testable without a paid license is validated.

**Recommend proceeding to the full build**, with two carried items: validate
**A-4** early on a staging Ultimate + Elasticsearch environment, and load-test
the aggregation path (OQ-X-006).
