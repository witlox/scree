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

## Analyst phase (2026-05-28)

- **OQ-A-001** — Resource modeling. **Resolved** → unified `Resource` core + typed
  kinds (Doc/Ticket/Risk). `specs/domain-model.md`.
- **OQ-A-002** — Definition of "space". **Resolved** → a Space is a GitLab
  project/repo; groups give hierarchy; org risks in dedicated repos.
  `specs/domain-model.md`.
- **Planning** — **Resolved** → planning items are aggregation *views* over GitLab
  epics/iterations/milestones, not stored resources. `specs/domain-model.md`.
- **OQ-A-005** — Orphan detection. **Resolved** → an active resource whose owner
  lost access / whose Space was archived is flagged in the hourly batch to Space
  maintainers for manual reassignment. INV-ORPH-1.
- **OQ-A-006** — State machines. **Resolved** → minimal: Ticket
  open→resolved→closed (+reopen); Risk open→closed (close is MR-required); Doc has
  versions, no states. `specs/domain-model.md`, INV-LC-*.
- **OQ-A-009** — Reference integrity. **Resolved** → references by stable `id`;
  tombstone, no hard delete; an unreadable/missing target renders "unavailable"
  with no content leak; no hard referential blocking. INV-REF-*.
- **OQ-A-013** — `severity: critical`. **Resolved (analyst proposal)** → a Risk is
  critical when its `category` is `security` or `compliance`; this drives the
  webhook. Awaiting OQ-HE-001 ratification. `specs/domain-model.md`, INV-IX-1.

---

## Architect phase — security/compliance (2026-05-28)

- **OQ-HE-005** — Compliance regime / data-protection posture. **Resolved** →
  **ADR-0006**: bounded-by-GitLab posture; GDPR erasure by **anonymization**
  (customer identity in an erasable directory outside Git; opaque requester id in
  Git); **selective + born-encrypted** ticket bodies (per-requester key,
  crypto-shred on erasure); residual free-text PII handled at Atlassian-parity. No
  heavier regulatory regime named; a sector certification, if later required,
  is a new item. See also ADR-0005 (revised), INV-DP-*.

> **OQ-HE-008** remains **open**: ADR-0006 sets the audit/erasure *baseline*
> (append-only audit sink INV-ID-3, risk register), but whether a dedicated
> compliance/audit team consumes these and imposes further requirements is still
> for the Head of Engineering to confirm.

---

**End of resolved questions.**
