# ADR-0003: Frontend stack — React + TypeScript, htmx for light surfaces

- Status: accepted
- Date: 2026-05-28
- Deciders: build team, head of engineering
- Resolves: OQ-X-004 (framework choice; specific admin library still open)
- Context phase: ratified ahead of architect phase

## Context and Problem Statement

The knowledge-management UI requires a WYSIWYG markdown editor (DD-016), which
is necessarily browser JavaScript/TypeScript. The system has surfaces of very
different weight: read-only doc viewing and simple forms, versus a rich editor,
an external customer portal, and data-grid-heavy internal admin screens.

## Decision Drivers

- The ProseMirror-based editor forces a real client-side JS/TS framework
- Non-technical internal users and external customers — accessibility (WCAG
  2.1 AA) and polish matter
- Admin/agent screens need data grids and kanban
- Read-only/light surfaces should not carry a heavy SPA

## Considered Options

- **All-React SPA**
- **All-htmx / server-rendered**
- **Hybrid: React for interactive surfaces, htmx for light surfaces**
- **Vue** instead of React

## Decision Outcome

Chosen option: **Hybrid — React + TypeScript for interactive surfaces
(WYSIWYG editor, customer portal, admin/agent UIs), htmx + server-rendered
HTML for light/read surfaces (doc reading, simple forms, status pages).**
React over Vue for ecosystem alignment with the editor and admin libraries.

Discipline rule: decide the rendering approach **per surface**, and let one
technology own a given DOM region — never both on the same region.

### Consequences

- Good: the right tool per surface; minimal client JS where it isn't needed;
  accessible, polished experiences where they matter.
- Bad: two frontend paradigms to keep disciplined; the React/htmx boundary
  must be drawn deliberately per surface.

## Open follow-ups (architect)

- Specific WYSIWYG editor library (TipTap vs BlockNote vs Milkdown — OQ-X-002)
- Specific admin framework (e.g. Refine.dev) for internal screens
- API types are generated from the gateway OpenAPI spec (no hand-maintained
  duplicates)
