# ADR-0009: WYSIWYG editor — TipTap

- Status: accepted
- Date: 2026-05-28
- Deciders: build team
- Resolves: OQ-X-002
- Context phase: architect

## Context

The knowledge-management UI needs a WYSIWYG editor with clean markdown
round-tripping for non-technical users (DD-016), supporting tables,
paste-from-Word, accessibility, templates/macros, and (later) draw.io.

## Considered Options

- **TipTap** (ProseMirror) — most mature, React, largest ecosystem, extensible.
- **BlockNote** (ProseMirror) — Notion-style blocks, polished OOTB, smaller
  customization surface.
- **Milkdown** (ProseMirror) — markdown-first, plugin ecosystem, smaller community.

## Decision Outcome

**TipTap.** Most mature and best-supported, first-class React, the strongest
table + extension story for the macros/templates a Confluence replacement needs,
and a markdown round-trip extension. Lowest risk for the largest single piece of
custom UI work (DD-015).

### Consequences

- Good: broad ecosystem, extensibility for macros/templates/draw.io, React fit
  (ADR-0003).
- Bad / accepted: TipTap's internal model is HTML-ish, so **markdown round-trip
  fidelity must be tested explicitly** (already a guarding `@e2e` scenario in
  `docs.feature`); some advanced extensions are paid (core is free).

## Notes

Round-trip fidelity (INV via `docs.feature`) is the acceptance bar; the
docs-frontend spike (PROPOSAL) validates it early.
