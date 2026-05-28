# Scree — Resolved Questions

Questions from `open-questions.md` that have been resolved, moved here to keep
the active set clean (per the process in `open-questions.md`). Each records the
resolution, date, and link to the governing decision.

---

## OQ-A-021: Ticket substrate — Git vs slot-in OSS helpdesk

*Raised*: 2026-05-28, during stack discussion. Given that the external service
desk is the only component forcing a custom server tier, should tickets be
built in-house on the Git substrate, or should a mature OSS helpdesk (Zammad,
Chatwoot, FreeScout, OTOBO) be slotted in?

*Considerations*: A slot-in satisfies the feature checklist but breaks DD-002
(Git substrate), DD-006 (single enforcement point), and DD-008 (cross-resource
aggregation), reintroduces a second permission model and operational system,
does not remove the aggregation build, and risks open-core lock-in.

**Resolved** (2026-05-28) → **ADR-0001**: build the service desk in-house on
the Git substrate.

---

## OQ-X-003: Backend language

*Original framing*: Rust vs Go, decided by org stack expertise. The candidate
set was expanded to include Python during the build-team discussion.

**Resolved** (2026-05-28) → **ADR-0002**: Python + FastAPI. I/O-bound,
integration-heavy system at modest scale; chosen on library ecosystem fit,
team expertise, and bus factor.

---

## OQ-X-004: Frontend framework (and admin framework)

*Original framing*: choose frontend framework and admin framework by team
expertise, ecosystem maturity, and editor-library integration.

**Resolved** (2026-05-28) → **ADR-0003**: React + TypeScript for interactive
surfaces (editor, portal, admin), htmx + server-rendered HTML for light/read
surfaces. React over Vue for editor/admin ecosystem alignment.

*Still open*: the specific admin-framework library (e.g. Refine.dev) and the
specific WYSIWYG editor library (OQ-X-002) remain architect decisions.

---

**End of resolved questions.**
