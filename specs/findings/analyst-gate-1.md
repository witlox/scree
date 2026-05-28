# Adversary — Analyst Gate 1 Findings

Spec-level adversarial pass over the analyst artifacts, gating analyst→architect.
Default stance: skepticism. Per project policy, **every finding is fixed before
graduation** — severity sets order, not whether.

---

## F-01 — Ticket privacy is bypassable via direct Git clone
- **Severity:** Critical
- **Category:** Security > trust boundary / permission bypass
- **Location:** `permission-model.md` §3–4; `domain-model.md` (Ticket); `invariants.md` INV-ACC-1/3, INV-AGG
- **Spec reference:** INV-ACC-1 ("no path bypasses the Gateway"), INV-ACC-3 (ticket visibility)
- **Description:** Tickets are stored as files in a GitLab repo (`support/service-desk`), but per-ticket visibility is enforced by application ReBAC at the Gateway. Anyone with GitLab **repo read** on that project (agents, possibly internal users) can `git clone` and read **every** ticket — including requester-private ones — entirely outside the Gateway. The single-enforcement-point invariant does not hold for ticket privacy.
- **Evidence:** External customer files a private ticket → stored in `support/service-desk` → any Developer-role member of that GitLab project clones the repo and reads it. ReBAC never runs.
- **Suggested resolution (advisory):** May be resolvable by an explicit access **constraint** rather than a storage redesign — options:
  (a) **Constrain the ticket repo's GitLab membership to agents** (who are permitted to see all tickets anyway, DD-013) and route all external/non-agent access through the Gateway only; make this an explicit invariant. Lightest; preserves the model. **Residual:** an agent's direct clone still bypasses Gateway audit (INV-ID-3) and any future per-agent ticket restriction — accept (agents are trusted staff) or restrict tooling.
  (b) **Gateway-only service-account repo** — no human has direct GitLab read; even agents go through the Gateway. Strongest for audit + future per-agent limits; loses clone-and-grep for tickets.
  (c) **Encrypt private ticket bodies at rest** — ciphertext in the repo, Gateway decrypts per ReBAC; adds Vault key management.
  (d) Per-requester repo sharding — rejected at 2–3k customers (DD-007).
  **Needs a user decision.**

## F-02 — Inbound email is unauthenticated and threading is forgeable
- **Severity:** High
- **Category:** Security > input validation / spoofing
- **Location:** `frontmatter-schemas/ticket.md` (`email_token`); `features/ticket_origins.feature`; `failure-modes.md` FM-13
- **Spec reference:** none — missing spec
- **Description:** Threading uses RFC headers and a `[SCREE-NNN]` subject token. Email sender and subject are trivially spoofable, and the token is guessable/sequential. An attacker can inject replies into an arbitrary ticket or impersonate a requester. No invariant addresses inbound sender verification (SPF/DKIM/DMARC) or token unguessability.
- **Evidence:** Attacker emails support with subject `Re: [SCREE-123] …` spoofing the requester's From — content appended to ticket 123, attributed to the requester.
- **Suggested resolution:** Specify inbound verification (DKIM/DMARC alignment), treat the token as low-trust (thread *candidate*, not authority), and require sender↔requester match before appending; otherwise quarantine for agent review.

## F-03 — External-customer writes cannot be attributed via token exchange
- **Severity:** High
- **Category:** Correctness > identity
- **Location:** `invariants.md` INV-ID-1; `permission-model.md` §5
- **Spec reference:** INV-ID-1 (GitLab audit shows the human via RFC 8693)
- **Description:** Token exchange targets GitLab, but external customers are **not** GitLab users. Their ticket writes therefore cannot carry a GitLab identity; INV-ID-1 is unsatisfiable for the most common external action. The spec doesn't define how external-originated writes are attributed in GitLab's audit (service account? on-behalf header?).
- **Evidence:** External customer submits a ticket via the portal → Gateway must write to GitLab → no GitLab identity exists to exchange into.
- **Suggested resolution:** Define a distinct attribution path for non-GitLab principals (e.g., Gateway commits as a desk service account with the external identity recorded in the commit trailer + app audit), and scope INV-ID-1 to GitLab-user principals.

## F-04 — `community_visible` exposure scope is undefined (whole-thread leak)
- **Severity:** High
- **Category:** Security > privacy
- **Location:** `domain-model.md` (Ticket); `features/ticket_lifecycle.feature`, `features/portal.feature`; DD-013
- **Spec reference:** INV-LC-2, INV-ACC-3
- **Description:** Promotion to `community_visible` exposes the ticket, but the spec never says **what**: the whole thread including private replies/attachments added after creation (the precise risk DD-013 names), or a curated snapshot. The `reopen` × `community_visible` interaction is also undefined — new private content could be added to a still-community-visible ticket.
- **Evidence:** A ticket gets a customer's API key pasted in reply #4, is later promoted → key becomes community-visible.
- **Suggested resolution:** Define promotion as exposing a **curated snapshot** (or require redaction confirmation), and forbid `community_visible` while `open`, or re-gate visibility on reopen.

## F-05 — Audit storage for reads/queries is unspecified and not tamper-evident
- **Severity:** Medium
- **Category:** Security > observability/audit
- **Location:** `invariants.md` INV-ID-3, INV-AGG; `permission-model.md` §5–6
- **Spec reference:** INV-ID-3
- **Description:** Git gives tamper-evidence for resource *writes*, but reads and aggregation queries (which INV-AGG says to audit) are not commits. Where these audit records live, and whether they are append-only/tamper-evident, is unspecified.
- **Suggested resolution:** Specify an append-only audit sink for non-Git actions with integrity protection; state retention.

## F-06 — Migration capability has no features, invariants, or ID-mapping spec
- **Severity:** Medium
- **Category:** Correctness > completeness
- **Location:** `features/` (absent); `invariants.md` (absent); `failure-modes.md` FM-18 only
- **Spec reference:** SEED §7 Q8/Q9; DD-014
- **Description:** Migration (Jira→ticket, Confluence→doc) is in v1 scope but has no Gherkin, no invariant on old→new ID-mapping integrity, and no curation criteria spec. Under-specified for graduation.
- **Suggested resolution:** Add migration features (ID mapping preserved, idempotent re-runs, archive of non-curated) and an ID-mapping invariant; or explicitly defer with stakeholder sign-off.

## F-07 — Page-level doc permissions (a named Confluence gap) silently dropped
- **Severity:** Medium
- **Category:** Correctness > scope fidelity
- **Location:** `domain-model.md` (Space); `permission-model.md` §4 (Doc)
- **Spec reference:** prior-art §1 (KM gap: "page-level permissions independent of project membership")
- **Description:** Space=repo gives only repo-level doc permissions. The stated KM requirement of page-level permissions independent of project membership is unmet, without an explicit decision to cut it.
- **Suggested resolution:** Either accept and document the scope cut (a Space is the permission unit; finer doc permissions are out of v1) or specify a mechanism. Needs a user decision.

## F-08 — Global `id` uniqueness asserted but not allocatable across repos
- **Severity:** Medium
- **Category:** Correctness > concurrency/integrity
- **Location:** `invariants.md` INV-ST-4; `frontmatter-schemas/README.md`
- **Description:** INV-ST-4 requires globally unique stable ids, but ids are created independently across many repos; concurrent creation can collide (e.g. two `ticket-2026-000123`). No allocation authority is specified.
- **Suggested resolution:** Define an allocation source (Gateway-issued sequence per kind, or a scheme guaranteeing uniqueness without coordination, e.g. space-prefixing).

## F-09 — Concurrent direct-commit conflict resolution is unspecified
- **Severity:** Medium
- **Category:** Robustness > concurrency
- **Location:** `invariants.md` INV-ST-1; `failure-modes.md` FM-15
- **Description:** Direct-commit-to-main default with many writers produces push races and YAML frontmatter merge conflicts. FM-15 says conflicts are "surfaced for resolution," but no mechanism is specified (last-writer? field-level merge? retry?).
- **Suggested resolution:** Specify the write path (read-modify-write via the Gateway with optimistic concurrency / retry on non-fast-forward) and structured-field conflict handling.

## F-10 — Planning-view permission filtering unspecified; leans on unvalidated assumptions
- **Severity:** Medium
- **Category:** Security > permission / completeness
- **Location:** `domain-model.md` (Planning); `cross-context/interactions.md`; `assumptions.md` A-4/A-5
- **Spec reference:** INV-AGG
- **Description:** Planning aggregates GitLab epics/iterations; INV-AGG must hold, but no feature or spec describes how planning rollups filter objects the viewer can't see, and it depends on unvalidated ★A-4/A-5.
- **Suggested resolution:** Add a planning-view permission feature; have the architect validate A-4/A-5 in the spike.

## F-11 — Slack `:ticket:` reaction enables spam and cross-user content capture
- **Severity:** Medium
- **Category:** Security > abuse / privacy
- **Location:** `features/slack_capture.feature`; DD-012/DD-013
- **Description:** Any community member can react to any message. This permits (a) ticket spam/DoS and (b) capturing another customer's posted content into a ticket. Requester attribution when reacting to someone else's message is also ambiguous.
- **Suggested resolution:** Rate-limit captures per Slack user; define requester as the captured-message author (with consent) or restrict capture to one's own messages / agents; specify spam handling.

## F-12 — Risk `score` is both authored and derived (drift risk)
- **Severity:** Low
- **Category:** Correctness > schema
- **Location:** `frontmatter-schemas/risk.md`
- **Description:** `score` is `required` yet defined as `likelihood × impact` and "validated." Author-set values can drift from the product.
- **Suggested resolution:** Make `score` derived (computed, not authored) or reject on mismatch in validation.

## F-13 — Severity bands are illustrative, not normative
- **Severity:** Medium
- **Category:** Correctness > testability
- **Location:** `frontmatter-schemas/risk.md` (`severity`)
- **Description:** Bands are given as "e.g. 1–4 low…", but the `severity` field and any tests referencing it need fixed thresholds.
- **Suggested resolution:** Fix the bands normatively (and define behavior at boundaries).

## F-14 — Reference `target_id` can leak existence of a sensitive resource
- **Severity:** Low
- **Category:** Security > information disclosure
- **Location:** `invariants.md` INV-REF-1/3; `frontmatter-schemas/README.md`
- **Description:** INV-REF-3 hides an unreadable target's content, but the `target_id` stored in the referrer's frontmatter (readable by anyone who can read the referrer) reveals that such a resource exists.
- **Suggested resolution:** Decide whether reference existence is sensitive; if so, omit/opaque-ize cross-boundary reference ids for unauthorized viewers.

## F-15 — Orphan policy doesn't cover tickets / departed assignees
- **Severity:** Medium
- **Category:** Correctness > completeness
- **Location:** `invariants.md` INV-ORPH-1; `features/orphan_detection.feature`
- **Description:** INV-ORPH-1 keys on `owner` losing access. Tickets have `owner = desk` (never orphan by this rule), yet an unassigned/abandoned open ticket, or one whose **assignee** left, is effectively orphaned and unhandled.
- **Suggested resolution:** Extend orphan detection to tickets (unassigned-open beyond a threshold; assignee departed) or state the ticket case explicitly.

---

## Cross-cutting note

F-01 and F-03 together say the **service-desk storage and identity model** is the
weakest part of the analyst specs — unsurprising, since the desk is the only
component forcing a custom server tier (ADR-0001). Resolving F-01 likely
reshapes how tickets are stored and should be settled before the architect
commits to a storage topology.
