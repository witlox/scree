# ADR-0011: Frontend component strategy — TanStack Table + Radix UI (headless), open-source only

- Status: accepted
- Date: 2026-05-29
- Deciders: build team, head of engineering
- Resolves: OQ-X-004 follow-up (specific admin/data-grid library); #106
- Builds on: ADR-0003 (React + TS / htmx hybrid)

## Context and Problem Statement

ADR-0003 chose React for the interactive surfaces and named the WYSIWYG editor and
admin/data-grid needs, but left the specific admin/data-grid library and the shared
component approach open. The internal admin/agent screens need data grids and kanban;
every surface needs accessible (WCAG 2.1 AA) shared components (buttons, fields,
dialogs, menus). A hard constraint from review: **pure open source, no paywalled
features** — avoid libraries whose useful capabilities sit behind a commercial tier.

## Decision Drivers

- WCAG 2.1 AA is a requirement, not a polish step (ADR-0003)
- Pure OSS — no commercial/enterprise feature gating
- Low lock-in; consistent with the foundation (TanStack Query, minimal CSS, islands)
- Mobile + desktop (responsive)

## Considered Options

- **Data grid**: TanStack Table (MIT) · Refine.dev (MIT core, commercial cloud) ·
  AG Grid (community MIT, **enterprise features paid**) · MUI X DataGrid (Pro/Premium paid)
- **Components**: Radix UI (MIT) · Ark UI (MIT) · hand-rolled · Mantine/MUI (heavier, partial paid)

## Decision Outcome

- **Data grid / tables**: **TanStack Table** (headless, MIT — all features free), on the
  existing TanStack Query; **dnd-kit** (MIT) for kanban when needed.
- **Accessible primitives**: **Radix UI** (MIT) for interactive widgets that are hard to
  get right (dialog, menu, tabs, combobox) — it owns focus management, ARIA, and keyboard
  behavior; we style with our design tokens. Trivial controls (button, labeled field)
  are hand-rolled against the tokens.

AG Grid and MUI X were rejected purely on the paywalled-features constraint; Refine and
Ark are fine on license but were not chosen (Refine: heavier/opinionated; Ark: newer,
Radix is more mature).

### Consequences

- Good: everything is MIT with nothing gated; headless = full control over a11y and the
  visual language; minimal lock-in; consistent with the foundation.
- Bad: more bespoke UI code than a batteries-included framework (CRUD/filter/grid wiring
  is ours to write).

## Follow-ups

- Design tokens + the first accessible primitives land with #105.
- TanStack Table / dnd-kit are added when the admin/agent surface (#103) is built.
