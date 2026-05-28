# Scree — TypeScript / React / htmx Coding Standards

Extends `.claude/guidelines/typescript.md` with project-specific conventions.
Loaded for: implementer, architect, adversary (frontend review).

## Surfaces and the React/htmx split

Decide the rendering approach **per surface**, and let one technology own a
given DOM region — never both on the same region.

| Surface | Approach |
|---|---|
| Doc reading / light forms / status pages | **htmx + server-rendered HTML** (FastAPI + Jinja2) |
| WYSIWYG doc editor | **React island** (ProseMirror-based editor, library per ADR-0002/OQ-X-002) |
| External customer portal | **React** (login, submit, reply, attach, status) |
| Internal admin / agent queues / dashboards | **React** (data grids, kanban) |

htmx surfaces are server-driven hypermedia: the server returns HTML fragments;
keep client JS minimal. React surfaces are SPA-style islands mounted into
specific roots; they do not take over htmx-owned pages.

## Conventions

- **TypeScript strict mode.** No `any` without a written reason; prefer
  `unknown` + narrowing at boundaries.
- **API types are generated** from the gateway's OpenAPI spec — do not
  hand-write request/response types. Regenerate on contract change.
- **One API client** wraps the gateway; it attaches the OIDC token and is the
  only path to the backend. No `fetch` scattered through components.
- **Authorization is never decided on the client.** UI may hide controls for
  UX, but the gateway is authoritative; assume the user can craft any request.
- **Components**: function components + hooks; co-locate state with use;
  lift only when shared. Keep data-fetching out of deeply nested components.
- **Accessibility is a requirement, not a polish step**: WCAG 2.1 AA. The
  editor and portal are used by non-technical and external users.

## State & data

- Server state via a query/cache library (e.g. TanStack Query); local UI
  state via hooks. Don't mirror server state into a global store.
- The WYSIWYG editor round-trips clean markdown; treat markdown as the wire
  format and assert round-trip fidelity in tests (it is a known risk area).

## Anchoring to the backend

- Ubiquitous-language terms match `specs/ubiquitous-language.md` and the
  generated API types. A `Ticket` is a `Ticket` on both sides.

## Anti-patterns

- Mixing htmx and React control over the same DOM region
- Hand-maintained API types diverging from the OpenAPI source of truth
- Authorization decisions in the client treated as security
- Bypassing the single API client with ad-hoc `fetch`
- Heavy global state stores for what is really server cache
- Inaccessible custom controls (div-buttons, missing labels/roles)
