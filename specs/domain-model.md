# Scree — Domain Model

Layer 1 of the analyst artifacts. Defines bounded contexts, the resource
aggregate, the unit of organization, and entity relationships. State machines
are deliberately minimal (OQ-A-006 confirmed — the org prefers low lifecycle ceremony).

Resolved foundational decisions this model rests on:

- **OQ-A-001** → unified `Resource` core + typed kinds.
- **OQ-A-002** → a Space is a GitLab project/repo.
- **Planning** → an aggregation *view* over GitLab-native objects, not a stored
  kind. Stored kinds are therefore **Doc, Ticket, Risk**.

---

## Bounded contexts

| Context | Responsibility | Depends on |
|---|---|---|
| **Knowledge** | Docs: authoring, hierarchy, rendering, templates | Access, Gateway |
| **Service Desk** | Tickets: lifecycle, relations, multi-origin, visibility | Access, Integration, Gateway |
| **Risk** | Project- and org-level risks; escalation; review cadence | Access, Gateway |
| **Planning** *(view)* | Portfolio/ART aggregation over GitLab epics/iterations | Indexing, Integration |
| **Access** | Identity (Keycloak), permission composition (GitLab RBAC + ticket ReBAC), audit | — |
| **Indexing** | Derived indexes for aggregation/search; batch + manual + critical-webhook | Integration |
| **Integration** | Adapters for GitLab, O365/email, Slack — thin, call the Gateway | — |
| **Migration** | Atlassian → Git pipeline; old→new ID mapping | Knowledge, Service Desk |
| **Gateway** | Single enforcement point; API surface; audit emission | Access |

Dependency direction is acyclic: Integration and Access are leaf-ward; Gateway
mediates; the resource contexts (Knowledge/Service Desk/Risk) sit above; Planning
and Indexing are derived/read-side.

---

## The unified Resource aggregate (OQ-A-001)

Every stored artifact is a `Resource`: a markdown file with YAML frontmatter in
a GitLab repository. The aggregate carries the **cross-cutting core**; each
**kind** specializes lifecycle and kind-specific fields.

### Cross-cutting core (all kinds)

| Field | Meaning |
|---|---|
| `id` | Stable, unique identifier (kind-prefixed, e.g. `risk-2026-001`) |
| `kind` | `doc` \| `ticket` \| `risk` |
| `schema_version` | Integer; present from the first commit (DD-021) |
| `title` | Human-readable title |
| `owner` | Accountable principal (Keycloak identity or group) |
| `status` | Lifecycle state; value set is **kind-defined** |
| `space` | The owning GitLab project (see below) |
| `references` | Outbound links to other resources / GitLab objects |
| `created` / `updated` | Derived from Git history (not author-asserted) |
| `audit` | Git commit history — author, timestamp, content delta |
| `permissions` | **Derived**, not stored: GitLab repo authority (+ ReBAC for tickets) |

`created`, `updated`, and `audit` are **projections of Git**, never independent
fields — Git is the source of truth (DD-002).

**Sensitive content is encrypted at rest** (ADR-0005): private ticket bodies and
designated sensitive doc/risk spaces are stored as ciphertext, with cleartext only
in authorized memory and the access-controlled index. Internal sensitive content
uses client-side keys (offline read preserved for key-holders); external-customer
private tickets use Gateway-mediated keys. Routing/permission metadata stays
cleartext. See INV-ENC-*.

### Kinds

- **Doc** (Knowledge) — has **versions, not states**. No state machine. Lives at
  a doc path within its space's repo. Carries template/type metadata.
- **Ticket** (Service Desk) — has relations (requester, watcher, assignee,
  owner) and a visibility flag (requester-private by default; community-visible
  by explicit promotion — DD-013). State machine: minimal (see below). Fine-grained
  access is ReBAC, not repo membership (DD-007).
- **Risk** (Risk) — carries `category` (delivery/security/compliance/operational/
  strategic), `likelihood`, `impact`, `score`, `strategy` (ROAM or
  Avoid/Transfer/Mitigate/Accept), `review_by`, `severity`. Project-level risks
  live in the project repo at `risks/`; org-level risks live in dedicated repos
  (DD-004). Escalation is **explicit duplication** into an org repo with a
  cross-reference back. State machine: minimal (see below).

---

## Space — the unit of organization (OQ-A-002)

A **Space is a GitLab project (repo)**. Permissions inherit from the project's
GitLab membership (mapped from Keycloak groups via OIDC). GitLab **groups**
provide hierarchy and portfolio grouping above spaces. Org-level risks occupy
**dedicated spaces** (e.g. `org/risk-portfolio`, `org/risk-security`,
`org/risk-compliance`) with their own permission boundaries.

Consequence: no new authorization layer is needed below repo granularity for
docs and risks — GitLab's repo/group model is authoritative for the common case.
Tickets are the exception (ReBAC; see `permission-model.md`).

---

## Planning — a view, not a kind

Planning items are **not stored Resources**. The Planning context produces
**aggregation views** (portfolio/ART rollups: PI commitment, capacity vs load,
dependencies) by referencing GitLab-native epics, iterations, and milestones
through the Indexing context. Scree stores no planning markdown; it adds only the
layer GitLab lacks above group scope. This honors the non-goal of not duplicating
GitLab planning primitives.

---

## Relationships & references

```
Risk ──references──▶ Ticket            (a risk cites mitigating work)
Ticket ─references─▶ Doc               (a ticket cites a KB article)
Planning(view) ─refs─▶ GitLab epic/iteration/milestone
Slack thread ──links──▶ Ticket         (snapshot capture, DD-012)
Risk(project) ─escalates─▶ Risk(org)   (explicit duplication + cross-ref)
```

Reference **integrity constraints** (OQ-A-009, resolved): references are by
stable `id`; "delete" is a tombstone (Git keeps history); an unreadable or
missing target renders "unavailable" with no content leak; deletion/move is not
hard-blocked. See INV-REF-*.

---

## Principals (summary)

Internal user, external customer, agent, operator, service account, and
Slack-bot-acting-on-behalf-of-a-user. Full enumeration, actions, and access
invariants live in `permission-model.md` (OQ-A-004, resolved).

---

## State machines (CONFIRMED — OQ-A-006)

Deliberately minimal — the org prefers low lifecycle ceremony.

**Doc** — none. Versions only (Git history).

**Ticket**:
```
open → resolved → closed
  ▲        │          │
  └─── reopened ◀─────┘
```
`community_visible` is an **orthogonal flag**, not a state (DD-013).

**Risk**:
```
open → closed
```
`category`, `likelihood`, `impact`, `score`, and `severity` are fields that drive
prioritization — they are not states. `strategy` (ROAM) is a field. Transition
**into `closed`** is on an MR-required path (DD-009) to prevent silent revision of
the historical record.

### Critical severity (OQ-A-013 → OQ-HE-001 for ratification)

A Risk is **critical** — and therefore fires the near-real-time indexing webhook
(DD-005) — when its **`category` is `security` or `compliance`**. Critical-ness is
category-driven, not a hand-set severity flag, so it stays disciplined and is not
gameable by mislabeling a field. `score`/`severity` remain independent
prioritization signals.

---

## Decisions recorded

OQ-A-001/002/005/006/009 and the planning-as-view call are **resolved** (see
`docs/analysis/resolved-questions.md`). Principals + access invariants are in
`permission-model.md` (OQ-A-004); schemas in `frontmatter-schemas/` (OQ-A-008).
OQ-A-013 (`category`-driven critical) is an analyst proposal awaiting OQ-HE-001
ratification.
