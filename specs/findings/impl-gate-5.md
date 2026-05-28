# Implementation Gate 5 — Adversary Findings

Adversarial pass over the GDPR erasure slice merged in PR #58
(`access/erasure.py`, `access/openfga.py:purge_user`, `access/identity.py`,
Gateway `DELETE /identities/{opaque_id}`). Primary target: erasure
**completeness** (INV-DP-2 / AR-05) — does erasure actually remove everything it
claims, on the real engine and across all stores?

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G5-01: `RealOpenFga.purge_user` is incomplete at scale — single Read page, single delete batch, ticket-type only
- **Severity:** Medium
- **Category:** Security/Correctness > data protection (AR-05 / INV-DP-2 incompleteness)
- **Location:** `api/scree/access/openfga.py:117-136` (`purge_user`)
- **Spec reference:** AR-05 (erasure purges OpenFGA tuples); INV-DP-2
- **Description:** Three compounding gaps make purge incomplete on the real engine:
  1. **No pagination.** OpenFGA `Read` is paginated (default ~50 tuples, returns a
     `continuation_token`). `purge_user` reads **one page** and ignores the token,
     so a subject with more relation tuples than one page keeps the remainder.
  2. **No delete batching.** OpenFGA `Write` caps deletes at ~100 tuple_keys per
     call; the code deletes every read key in a **single** call, which 400s past
     the limit (and even then, only covers the one page from gap 1).
  3. **Ticket-type scope only.** The Read filter is hard-coded to `object: "ticket:"`,
     so any future tuples on other object types (spaces, docs, groups) for the same
     subject are never purged — a latent incompleteness as the authz model grows.
  The `@contract` test passed only because it used 2 tuples (< one page), masking
  all three. Net effect: a heavy or multi-type subject is **partially** erased,
  silently — exactly the failure AR-05 exists to prevent.
- **Evidence:** seed a user with 120 `requester`/`watcher` tuples → `purge_user`
  reads ~50, attempts a >100-key delete (or only deletes the first page), and
  leaves the rest; `list_readable` still returns tuples after "erasure."
- **Suggested resolution:** Loop `Read` on `continuation_token` until exhausted;
  chunk deletes to ≤100 per `Write`; iterate the relevant object types (or read
  without a type filter where the engine allows). Add a `@contract` case with
  > 1 page to prevent regression.

## Finding G5-02: Erasure does not scrub the quarantine queue, which retains the subject's email + body
- **Severity:** Medium
- **Category:** Security/Privacy > data protection (erasure completeness)
- **Location:** `api/scree/access/erasure.py` (`ErasureService.erase`); `servicedesk/quarantine.py` (`QuarantinedEmail.claimed_from`/`body`)
- **Spec reference:** INV-DP-1/2 (PII erasable, out of the durable substrate)
- **Description:** Quarantined inbound emails store `claimed_from` (a raw email
  address) and the message `body` — PII — in the `QuarantineStore`. `ErasureService`
  only deletes the identity-directory record and purges OpenFGA tuples; it never
  touches quarantine, so a customer's PII held in the quarantine queue **survives**
  a GDPR erasure. Worse, `erase()` reads `email_for(opaque_id)` and then deletes the
  mapping, discarding the very email needed to find quarantine entries (which are
  keyed by `claimed_from`, not the opaque id) — so even a later scrub can't correlate
  them. Note this is distinct from ticket/Git content (accepted as bounded by the
  substrate); the quarantine queue is a separate, non-Git PII store the erasure model
  silently omits.
- **Evidence:** an unverified email from `alice@x.ac` is quarantined (stores her
  address + body); erasing Alice's opaque id leaves the quarantine entry intact.
- **Suggested resolution:** Give `ErasureService` the quarantine store; resolve
  `email_for(opaque_id)` **before** deleting the mapping and purge quarantine
  entries whose `claimed_from` matches (or hold quarantine for a bounded retention
  and document it). Decide deliberately and record the scope.

## Finding G5-03: Erasure produces no durable compliance receipt and discloses no residual scope
- **Severity:** Low
- **Category:** Robustness > observability / compliance evidence
- **Location:** `api/scree/access/erasure.py` (`erase` return); Gateway `DELETE /identities/{opaque_id}`
- **Spec reference:** INV-ID-3 (audit); data_protection.feature ("Git history is not rewritten")
- **Description:** Erasure is a high-stakes compliance action but leaves only the
  optional, generic request-audit line (principal/path/status — and only if an
  audit sink is wired). There is no durable, queryable **erasure receipt** (who
  erased whom, when, what was purged) for a DPO to evidence compliance. Relatedly,
  the response (`identity_removed`, `relations_purged`) does not disclose what was
  deliberately **not** erased — ticket/comment content remains in Git (bounded by
  substrate, ADR-0006) — so the boundary of the erasure is implicit and a compliance
  officer can't see it.
- **Evidence:** after a successful erase, there is no record beyond an optional
  request log, and no machine-readable statement of residual data.
- **Suggested resolution:** Emit a durable erasure receipt (append-only, like the
  audit sink) capturing actor, subject id, timestamp, and counts; include a
  `residual` note (e.g. "ticket bodies retained in Git history") in the response so
  the scope is explicit.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G5-01 | Medium | Security/data-protection | `RealOpenFga.purge_user` incomplete: no Read pagination, no delete batching, ticket-type only |
| G5-02 | Medium | Privacy/data-protection | Erasure doesn't scrub the quarantine queue (retains email + body); mapping deleted before scrub possible |
| G5-03 | Low | Robustness/compliance | No durable erasure receipt; residual (Git/comment) scope not disclosed |

**Counts:** 0 critical · 0 high · 2 medium · 1 low — **3 total.**

**Highest-risk area:** completeness on the real engine (G5-01) — the fake/contract
test passed with a trivial tuple count, hiding pagination and batch-limit gaps that
leave a heavy subject partially erased. No `gate:blocking` (no critical/high).

**Note (scope, not a finding):** crypto-shred of per-requester encryption keys
remains deferred to the encryption-at-create slice, as recorded on PR #58 — the
`data_protection.feature` crypto-shred scenario is intentionally not yet met.

**Resolution (2026-05-28) — all 3 resolved (PR #59):**
- G5-01 — `RealOpenFga.purge_user` now follows Read pagination
  (`continuation_token`) and batches deletes to ≤100/call; a `@contract` test with
  120 tuples proves full purge on the real engine. The `ticket:` type scope is kept
  deliberately (only object type today) and documented for extension.
- G5-02 — `ErasureService` resolves the email **before** deleting the directory
  mapping and calls `QuarantineStore.purge_sender(email)` to scrub the subject's
  quarantined PII; the count is returned and recorded.
- G5-03 — erasure writes a durable `ErasureReceipt` (actor/subject/timestamp/
  counts) to an append-only store, queryable via compliance-only
  `GET /identities/erasures`; the erase response discloses the residual scope.
