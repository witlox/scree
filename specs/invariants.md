# Scree — Invariants

Numbered, testable assertions that must always hold. Each cites its source and is
phrased so a test can fail when it is violated. Severity reflects blast radius if
broken. The adversary targets these; the auditor rates enforcement depth.

---

## Storage & truth

- **INV-ST-1** — Git is the source of truth. Every resource mutation is a Git
  commit; no resource state exists only in the index or a cache. *(DD-002)*
- **INV-ST-2** — The index is derived and rebuildable from Git alone. Deleting
  and rebuilding the index changes no answer the system gives. *(DD-002, prior-art §3)*
- **INV-ST-3** — Every resource carries an integer `schema_version` from its
  first commit. *(DD-021)*
- **INV-ST-4** — `id` is stable and globally unique; it never changes once
  assigned, even on move. Uniqueness is guaranteed by Gateway-side allocation (a
  per-kind sequence), avoiding cross-repo coordination races. *(domain-model, F-08)*
- **INV-ST-5** — `created`, `updated`, and audit history are projections of Git
  commit history, never independently authored fields. *(domain-model)*
- **INV-ST-6** — Resource writes are performed by the Gateway as read-modify-write
  with optimistic concurrency: on a non-fast-forward the write retries against the
  latest revision; irreconcilable structured-field conflicts (e.g. two agents set
  different `status`) are surfaced to the actor, never silently merged.
  *(F-09, FM-15)*

## References (OQ-A-009 → stable IDs + filtered render)

- **INV-REF-1** — References are stored by stable `id`, not by path or title.
- **INV-REF-2** — "Delete" is a tombstone; Git history is retained. There is no
  destructive erasure of resource history. Personal-data erasure (GDPR) is handled
  separately by anonymization, not by rewriting Git history (INV-DP-2).
- **INV-REF-3** — A reference whose target is missing or **unreadable to the
  viewer** renders as "unavailable" and exposes **no** title, excerpt, or metadata
  of the target. *(upholds INV-AGG)*
- **INV-REF-4** — Deletion or move of a referenced resource is never blocked by
  the existence of references (no hard referential integrity).
- **INV-REF-5** — At the Gateway render layer, a reference whose target crosses a
  permission boundary the viewer lacks has its `target_id` withheld/opaque, so the
  referrer does not disclose the *existence* of an unreadable resource. (A raw
  direct clone of a *cleartext* referrer is out of scope of this render rule;
  sensitive cross-references belong on encrypted/sensitive resources.) *(F-14)*

## Access & permissions

- **INV-AGG** *(load-bearing)* — For any principal `P` and any aggregation/search/
  portfolio/risk view, the items returned to `P` are a **subset** of the items `P`
  could read by direct access; no title/excerpt/count/score/metadata of an
  unauthorized item is exposed. Filtering is per-item, at query time, every
  request. *(DD-008; see permission-model §6)*
- **INV-ACC-1** — All access is mediated by the Gateway; there is no path to
  resources or the index that bypasses it. Frontend checks are not relied upon for
  authorization. *(DD-006)* Exception by design: an authorized staff member's
  **offline** read of client-key-encrypted content they already hold keys for
  (INV-ENC-2) occurs outside the Gateway.
- **INV-ACC-2** — Authority composes as: GitLab repo/group RBAC (docs, risks,
  planning views) ∪ ticket ReBAC (tickets). A request is permitted iff a layer
  grants it. *(DD-007)*
- **INV-ACC-3** — A ticket is readable only by its requester, named watchers, the
  assignee, and agents — unless `community_visible` is set, then by any
  authenticated principal. *(DD-011, DD-013)*
- **INV-ACC-4** — The org tag on an external customer grants no access. *(DD-011)*
- **INV-ACC-5** — A stale permission cache fails closed: when authority is
  uncertain, the item is omitted, never exposed. *(DD-008, OQ-A-011)*

## Encryption (selective; ADR-0005)

- **INV-ENC-1** — Encrypted-at-rest content is (a) ticket bodies that are
  sensitivity/compliance-tagged **or** born-encrypted, and (b) designated sensitive
  doc/risk spaces. Other ticket bodies are cleartext in Git. Cleartext exists only
  in authorized memory and the access-controlled index; routing/permission
  metadata stays cleartext.
- **INV-ENC-2** — Internal sensitive content uses client-side recipient keys
  (authorized staff read/grep it **offline**); encrypted external ticket bodies use
  a **per-requester** Gateway-mediated key held in Vault, **never** distributed to
  customers and crypto-shreddable on erasure.
- **INV-ENC-3** — Where the search index holds decrypted sensitive content, the
  index is access-controlled and subject to INV-AGG. Encrypted tickets are indexed
  by **metadata only** (id/status/requester-ref/timestamps); their bodies are not
  full-text indexed.
- **INV-ENC-4** — Revocation for client-key content is rotation-based; a prior
  key-holder may retain access to versions decryptable before rotation (accepted
  for the internal-staff trust model).

## Data protection & erasure (ADR-0006)

- **INV-DP-1** — Customer identity/profile (name, email, org) and the
  requester↔ticket link live in an erasable directory **outside Git**; Git
  frontmatter stores only an **opaque requester id**, never a name or email.
- **INV-DP-2** — GDPR erasure = delete the identity record (**anonymization**): the
  opaque requester id becomes unresolvable; Git history is not rewritten for routine
  erasure. Tagged/born-encrypted ticket bodies are additionally **crypto-shredded**
  (per-requester key destroyed).
- **INV-DP-3** — A ticket is encrypted iff sensitivity/compliance-tagged **or**
  born-encrypted (the create-time encrypt toggle). Encryption is a create-time
  decision and is **not** retroactive over Git history.
- **INV-DP-4** — Scree provides no stronger confidentiality/integrity/erasure
  guarantee than the GitLab substrate plus selective encryption. Residual free-text
  PII in untagged cleartext bodies is handled by manual redaction / rare
  history-rewrite (Atlassian-parity); this bound is documented, not hidden.

## Identity

- **INV-ID-1** — Actions against GitLab carry the initiating human's identity via
  token exchange; GitLab's audit log shows the human, not the Gateway. *(DD-018)*
- **INV-ID-2** — A Slack-initiated action whose Slack↔Keycloak mapping fails is
  **refused**; the system never proceeds with degraded/anonymous attribution.
  *(DD-012, OQ-A-016)*
- **INV-ID-3** — Every Gateway action is audited with principal, resource, action,
  and result, to an append-only, integrity-protected sink (reads and aggregation
  queries included; these are not Git commits). *(DD-006)* Authorized offline
  client-side reads of already-key-held content are not Gateway-audited (accepted
  limitation, ADR-0005).
- **INV-ID-4** — Writes by a principal who is **not** a GitLab user (external
  customers) are committed by the desk service account, with the external identity
  recorded in the commit trailer and the application audit. INV-ID-1 applies only
  to GitLab-user principals. *(F-03)*

## Inbound email (F-02)

- **INV-EMAIL-1** — Inbound email is verified (DKIM/DMARC alignment) before use.
  The `[SCREE-NNN]` token and RFC threading headers are **candidates, not
  authority**: content is appended to a ticket only when the verified sender
  matches the ticket's requester or an authorized participant; otherwise it is
  quarantined for agent review — never silently appended or attributed.

## Slack capture (DD-012, F-11)

- **INV-SLACK-1** — A captured ticket's requester is the captured message's
  **author** (resolved to a Keycloak identity; refused if unmappable, INV-ID-2);
  the capturing user is recorded separately. Capture (emoji/slash) is
  **rate-limited per Slack user** to prevent spam/DoS.

## Lifecycle (OQ-A-006 confirmed — minimal)

- **INV-LC-1** — A Ticket's state is one of `open`, `resolved`, `closed`; the only
  legal transitions are open→resolved, resolved→closed, and reopen
  (resolved→open, closed→open). *(domain-model)*
- **INV-LC-2** — `community_visible` is orthogonal to ticket state but may be set
  **only on a `resolved` ticket**, requires an explicit confirmed agent action, and
  exposes a **curated snapshot** — not the live thread or later private
  replies/attachments. Reopening a community-visible ticket **re-gates it to
  private** until re-promoted. *(DD-013, F-04)*
- **INV-LC-3** — A Risk's state is one of `open`, `closed`. Transition into
  `closed` occurs only via a merge request on the MR-required path. *(DD-009)*
- **INV-LC-4** — Risk escalation creates a duplicate Risk in an org Space with a
  cross-reference back to the source; it does not move or hide the original.
  *(DD-004)*

## Indexing & triggers

- **INV-IX-1** — A change to a Risk whose `category` is `security` or `compliance`
  triggers the near-real-time webhook; all other changes ride the batch.
  *(DD-005; OQ-A-013, pending OQ-HE-001 ratification)*
- **INV-IX-2** — A missed webhook is caught by the next hourly batch; correctness
  never depends on webhook delivery. *(DD-005)*
- **INV-IX-3** — The manual re-index trigger is authenticated and rate-limited (it
  is otherwise a DoS vector). *(DD-005)*
- **INV-IX-4** — Sensitive risk categories (`security`, `compliance`) are indexed
  separately from the main index. *(DD-008)*

## Orphan handling (OQ-A-005 confirmed)

- **INV-ORPH-1** — An active (non-`closed`) resource whose owner has left the org /
  lost access to its Space, or whose Space is archived, is flagged in the hourly
  batch and surfaced in an "orphaned actives" report to Space maintainers for
  manual reassignment. Orphan detection never auto-reassigns. *(OQ-A-005)*
- **INV-ORPH-2** — A ticket is flagged as orphaned for triage when it is `open`
  and either unassigned beyond a threshold or its assignee has lost desk access;
  it is surfaced to desk leads. (The ticket `owner` is the desk, so INV-ORPH-1's
  owner-based rule does not catch this case.) *(F-15)*

## Update governance

- **INV-GOV-1** — MR-required paths (compliance-tagged resources, closed risks,
  designated doc paths) cannot be changed by direct commit; enforcement is GitLab
  branch protection + CODEOWNERS. *(DD-009)*

## Migration (DD-014, F-06)

- **INV-MIG-1** — Every migrated item records a stable old→new ID mapping
  (`SUP-4821` → ticket id; `confluence:12345` → doc id). Any reference to a legacy
  ID resolves through the mapping; no migrated reference becomes a broken link
  post-cutover.
- **INV-MIG-2** — The migration pipeline is idempotent: re-running it creates no
  duplicates and does not alter existing mappings.
- **INV-MIG-3** — Content not curated by the deadline is **not** migrated and
  remains available in the read-only archive. Default is archive; migration is
  opt-in. *(Curation criteria: explicit per-team marking by the deadline — analyst
  proposal; exact deadline and any activity-based pre-filter await OQ-HE-004.)*

## Degradation

- **INV-DEG-1** — When GitLab is unreachable, reads from a local clone of
  authorized content still succeed; resource/ticket creation is refused with a
  clear error and never silently dropped or queued-as-success. *(DD-003)*
- **INV-DEG-2** — When O365 is unreachable, inbound email-driven ticket creation
  fails visibly; no email is silently lost from the user's perspective. *(DD-019)*

---

Severity guidance for the auditor: INV-AGG, INV-ACC-*, INV-ID-2 are
**critical** — shallow coverage on any of these is a critical finding.
